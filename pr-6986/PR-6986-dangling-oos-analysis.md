# PR #6986 — SERVER_MODE Vacuum Dangling OOS Analysis

**Question:** Will vacuum clean up OOS values without dangling in all SERVER_MODE scenarios?

**Answer:** **No.** There is at least one concrete, common scenario that leaks old OOS records, plus one pattern introduced by the recent strict-mode refactor that can livelock a vacuum worker.

---

## 1. How vacuum decides what to do (`mvcc_satisfies_vacuum`)

`src/transaction/mvcc.c:321-374` classifies each record into one of three states based on `oldest_mvccid`:

| Result | Condition | Vacuum action |
|--------|-----------|---------------|
| `VACUUM_RECORD_CANNOT_VACUUM` | INSID or DELID not yet all-visible | skip |
| `VACUUM_RECORD_DELETE_INSID_PREV_VER` | INSID all-visible, **DELID not set or not yet all-visible** | `vacuum_heap_record_insid_and_prev_version` |
| `VACUUM_RECORD_REMOVE` | **DELID all-visible** | `vacuum_heap_record` |

**The asymmetry:** only the `DELETE_INSID_PREV_VER` path walks the `prev_version_lsa` chain (via `vacuum_cleanup_prev_version_oos`, `vacuum.c:2246`). The `REMOVE` path only cleans the OOS on the *current* record (`vacuum.c:2705`, `vacuum.c:2762`).

---

## 2. ❌ P1 — Dangling OOS: UPDATE → DELETE when INSID and DELID become visible at the same vacuum pass

### Setup

```sql
UPDATE t SET oos_col = 'NEW' WHERE id = 1;   -- creates OOS_B, heap v2 with prev_version_lsa → undo(v1, OOS_A)
DELETE FROM t WHERE id = 1;                   -- stamps DELID on v2
COMMIT;
```

If there is no long-running reader straddling the two statements, **INSID (UPDATE) and DELID (DELETE) become all-visible at the same time**. The very next vacuum pass sees:

- `MVCC_IS_HEADER_DELID_VALID == true`
- `MVCC_IS_REC_DELETED_SINCE_MVCCID == false` (DELID older than `oldest_mvccid`)

→ `mvcc_satisfies_vacuum` returns `VACUUM_RECORD_REMOVE` (mvcc.c:372).

### What runs

`vacuum_heap_record` (vacuum.c:2614). It:

1. Calls `spage_vacuum_slot` on the home (and forward) page.
2. If `has_oos`, calls `vacuum_heap_oos_delete` on `helper->record` — **the *current* record only** (OOS_B).
3. Commits the sysop.

**It never walks `helper->mvcc_header.prev_version_lsa`.** The only function that does (`vacuum_cleanup_prev_version_oos`) is reachable exclusively from `vacuum_heap_record_insid_and_prev_version` at line 2246.

### Result

- OOS_B: deleted ✅
- OOS_A (in undo log referenced by prev_version_lsa): **orphaned** ❌
- The `prev_version_lsa` is destroyed along with the heap slot, so there is no future chance to recover OOS_A.

### Why this is common

No long reader is needed. A single session running `UPDATE … ; DELETE …` and committing is enough — a textbook workflow. The leak scales linearly with UPDATE churn before the DELETE:

```sql
UPDATE t SET c = 'v1' WHERE id = 1;  -- OOS_v1 → chain
UPDATE t SET c = 'v2' WHERE id = 1;  -- OOS_v2 → chain
UPDATE t SET c = 'v3' WHERE id = 1;  -- OOS_v3 → chain
DELETE FROM t WHERE id = 1;          -- OOS_v4 (from UPDATE cascading before delete? or just current)
```

If vacuum doesn't process any `DELETE_INSID_PREV_VER` passes between these statements, only the *last* OOS is reaped; OOS_v1, OOS_v2, OOS_v3 all leak.

### Fix options

1. **Call `vacuum_cleanup_prev_version_oos` from `vacuum_heap_record` too**, guarded by `MVCC_IS_HEADER_PREV_VERSION_VALID`. Cheapest change; requires handling the sysop interaction since the chain walk does its own logged `oos_delete`s outside the vacuum sysop.
2. **Split the vacuum into two passes** when prev_version chain is present: first INSID_PREV_VER on the chain, then REMOVE on the current record. More invasive.
3. **Avoid the scenario by making UPDATE eagerly delete old OOS in MVCC mode too**, with reader-side recovery via undo (CBRD-26609's original M1 design). But this contradicts the current MVCC-preserves-old-OOS design.

Option 1 is the minimal fix.

---

## 3. ⚠ P2 — Retry livelock on partial prev_version cleanup failure (introduced by the strict refactor)

### Scenario

`vacuum_cleanup_prev_version_oos` (vacuum.c:2415) walks the chain and calls `oos_delete` for each OOS OID found in each prev version. Each `oos_delete` is an independent logged operation (no enclosing sysop around the whole chain walk).

Say a chain has `{OOS_A, OOS_B, OOS_C}` (from three prev versions). On pass 1:

1. Delete OOS_A → succeeds (logged, committed).
2. Delete OOS_B → fails (e.g., page fix failure, or already-deleted due to recovery-replayed partial work).
3. Strict handler: `goto cleanup` → return error.
4. Caller `vacuum_heap_record_insid_and_prev_version` propagates → vacuum aborts this record. **`prev_version_lsa` is NOT cleared.**

On pass 2, vacuum re-reads the same record, same chain. It re-walks and:

1. Delete OOS_A → **fails** because OOS_A's slot no longer exists. The `spage_get_record` in `oos_delete_chain` returns `S_DOESNT_EXIST` → `ASSERT_ERROR_AND_SET` → error.
2. Strict handler: return error.

**This record is now permanently unvacuumable** until some external intervention. The old best-effort impl avoided this by continuing past per-OOS failures.

### Why it wasn't a problem in best-effort mode

Best-effort logged a warning and proceeded. On partial failure, the remaining chain still got traversed and `prev_version_lsa` was eventually cleared. Leaky but not stuck.

### Fix options

1. **Wrap the chain walk in a sysop.** `log_sysop_start` at entry, `log_sysop_commit` at normal exit, `log_sysop_abort` on error. Makes the whole walk atomic — either all OOS deletes or none. Retry is safe.
2. **Make `oos_delete` tolerate already-deleted slots.** Return `NO_ERROR` on `S_DOESNT_EXIST` with an `er_log_debug` trace. Semantically weaker but cheapest.
3. **Persist a per-chain "cleanup progress" marker** somewhere. Over-engineered.

Option 1 is correct; option 2 is a fine fallback. **This is a regression from the best-effort removal** and should be addressed before merging.

---

## 4. ⚠ P3 — `REC_BIGONE + OOS` coexistence assumption is unenforced

The PR description claims:

> REC_BIGONE은 OOS 처리 불필요 (OOS가 레코드를 작게 유지하므로 overflow 레코드에 OOS 플래그 설정 불가)

But no assertion enforces this invariant. The REMOVE path for `REC_BIGONE` at vacuum.c:2720-2750 does **not** call `vacuum_heap_oos_delete`:

```c
case REC_BIGONE:
  ...
  heap_ovf_delete (...);   // deletes overflow chain
  log_sysop_commit (...);  // no OOS cleanup
  break;
```

If the invariant is ever violated — e.g., by an UPDATE path that grows a record past the REC_HOME threshold while OOS columns are still present — OOS records bound to a `REC_BIGONE` heap record would leak silently.

### Fix

Either:

- Add `assert (!heap_recdes_contains_oos (...))` to the `REC_BIGONE` branch in both `vacuum_heap_record` and `vacuum_heap_prepare_record`, so violations fail loud in debug.
- Or explicitly handle OOS in the `REC_BIGONE` branch (mirrors REC_RELOCATION).

I recommend the assert — if the invariant truly holds, the assert has zero cost and catches regressions.

---

## 5. Scenarios that are clean

For completeness, these paths cleanly handle OOS with no dangling:

| Scenario | Path | OOS cleanup |
|----------|------|-------------|
| INSERT + DELETE + vacuum | `VACUUM_RECORD_REMOVE` → `vacuum_heap_record` | Current OOS cleaned, no prev chain exists ✅ |
| INSERT + UPDATE + vacuum (INSID pass first) | `VACUUM_RECORD_DELETE_INSID_PREV_VER` → walks chain, clears prev_version_lsa | Old OOS cleaned ✅ |
| INSERT + UPDATE + rollback | heap undo restores v1; `oos_insert` for OOS_B is undone | OOS_A preserved, OOS_B rolled back ✅ |
| Crash mid-vacuum sysop (REC_HOME+OOS or REC_RELOCATION+OOS) | Recovery undoes everything in the open sysop | Atomic ✅ |
| REC_RELOCATION + OOS (REMOVE path) | vacuum.c:2659-2718, OOS cleanup inside sysop | Current OOS cleaned ✅ (same chain-leak concern as REC_HOME) |

---

## 6. Summary

| Severity | Finding | Where |
|----------|---------|-------|
| **P1** | UPDATE → DELETE commits → vacuum REMOVE path leaks prev_version OOS | `vacuum_heap_record` doesn't walk prev chain |
| **P2** | Strict refactor can livelock vacuum on partial chain cleanup failure | `vacuum_cleanup_prev_version_oos` has no enclosing sysop |
| **P3** | `REC_BIGONE` + OOS invariant unenforced | `vacuum_heap_record` REC_BIGONE branch has no OOS handling or assert |

The short answer to your question: **vacuum does not guarantee no-dangling OOS in all SERVER_MODE scenarios.** The most impactful fix is **call `vacuum_cleanup_prev_version_oos` from the `REMOVE` path too** (P1), with the chain walk wrapped in a sysop (P2). The `REC_BIGONE` assert (P3) is a low-effort invariant hardening.
