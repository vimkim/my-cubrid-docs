# CBRD-26668 / PR #6986 — Two Caveats Explained: Rollback Reclaim & Latch Inversion

- **Date:** 2026-06-15
- **Context:** A prior review of this PR flagged two "critical" concerns — (1) vacuum reclaiming the OOS of a row that **rollback** later resurrects, and (2) a **latch-ordering inversion** in `heap_oos_find_vfid`. This document re-verifies both against the current code (`oos-vacuum` @ `c062dce8f`) and explains each in detail.
- **Bottom line:** caveat (1) is **safe by design — NOT a bug**; caveat (2) is a **real, confirmed deadlock hazard**.

---

## Caveat 1 — "Does vacuum delete the OOS of a row that rollback brings back?" → NO (safe by design)

### The worry (in plain terms)
The forward-walk path reclaims old OOS chunks by reading the **undo log image** (how a row looked *before* an UPDATE). It does **not** re-open the live heap page to double-check, the way the REMOVE path does with `mvcc_satisfies_vacuum`. So the question was:

> If a transaction UPDATEs a row and then **rolls back**, the old row image becomes the live row again. If vacuum had already deleted that old image's OOS chunks, the resurrected row would point at freed/garbage OOS. Can that happen?

This is a fair question — the forward-walk really does work off the undo image with no on-page recheck. The reason it is still safe is **when** vacuum is allowed to touch that log record.

### Why it cannot happen — the visibility threshold gate
Vacuum never processes arbitrary log records. It only processes a log block once the block's **entire MVCCID range is strictly below the global "oldest visible" MVCCID** — i.e. only fully-committed work that no current or future snapshot can see.

Two layers enforce this:

1. **Block-eligibility gate** — `vacuum.c:3248` (`is_cursor_entry_ready_to_vacuum`):
   ```c
   if (m_cursor.get_current_entry ().newest_mvccid >= m_oldest_visible_mvccid)
     {
       // still visible -> cannot be vacuumed yet
       return false;
     }
   ```
   A block is dispatched to a worker only if its `newest_mvccid < oldest_visible`.

2. **Per-record assertion** inside `vacuum_process_log_block` — `vacuum.c:3538`: every record's `mvccid` must strictly precede the freshly re-read `threshold_mvccid` (the global oldest visible), or the server fatals. The forward-walk reclaim calls (`vacuum.c:3577`, `:3712`) run only *after* this gate.

### Why the gate also excludes rollbacks — the abort ordering
"Oldest visible" is the **lowest still-active MVCCID** across all transactions (`compute_oldest_visible_mvccid`, `mvcc_table.cpp:355`). A transaction's MVCCID leaves the active set only in `logtb_complete_mvcc`. The key is the **order** in which abort does its work — `log_abort_local`, `log_manager.c:5304-5317`:

```c
log_rollback (thread_p, tdes, NULL);          // 5304: physically restore the pre-image as the live row
...
logtb_complete_mvcc (thread_p, tdes, false);  // 5317: ONLY NOW drop MVCCID from the active set
```

Rollback **finishes restoring the old row** *before* the MVCCID is retired. So for the entire window in which the pre-image could become live again, the aborting transaction's MVCCID is **still active**, which keeps `oldest_visible ≤ that MVCCID`. That block therefore fails the `vacuum.c:3248` gate and is **never handed to a vacuum worker**. By the time vacuum can legally read an `RVHF_UPDATE_NOTIFY_VACUUM` / `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` record, the writing transaction has **committed**, and the old version it superseded is genuinely dead and unreachable.

### Edge cases checked
- **Savepoint / partial rollback:** only `complete_sub_mvcc` runs for sub-operations; the main transaction's MVCCID stays active until full commit/abort, so `oldest_visible` stays pinned. (And a rolled-back UPDATE re-logs a compensating image, so the original record no longer describes the live row anyway.)
- **Crash during rollback:** recovery completes undo before normal MVCC activity resumes; `complete_mvcc` for the aborted txn is never reached until rollback finishes, so its MVCCID is never prematurely treated as vacuumable.

### Conclusion
The forward-walk path's lack of an on-page `mvcc_satisfies_vacuum` re-check is **intentional and correct**: the visibility-threshold gate already guarantees the pre-image is committed-and-dead. The REMOVE path needs that re-check only because it operates on a *live* slot that concurrent activity can still touch; the forward-walk operates on an already-superseded, committed image. **No fix needed.** (This is worth a one-line comment at the forward-walk call site so the next reader doesn't re-raise it.)

---

## Caveat 2 — Latch-ordering inversion in `heap_oos_find_vfid` → CONFIRMED (real deadlock hazard)

### The rule being broken
CUBRID fixes pages in a fixed rank order to avoid deadlock: the heap **header page ranks before data pages** (`PGBUF_ORDERED_HEAP_HDR` < `PGBUF_ORDERED_HEAP_NORMAL`). Normal code takes the header **first**, then descends to data pages — e.g. the insert path `heap_stats_find_best_page` (`heap_file.c:3582`) fixes the header (write) via `pgbuf_ordered_fix`, then goes to data pages.

### What the new code does instead
`heap_oos_find_vfid` (`heap_file.c:12177`) fixes the heap **header** page **unconditionally**:
```c
mode = (docreate == true ? PGBUF_LATCH_WRITE : PGBUF_LATCH_READ);
addr_hdr.pgptr = pgbuf_fix (thread_p, &vpid, OLD_PAGE, mode, PGBUF_UNCONDITIONAL_LATCH);
```
and its signature has **no** conditional-latch parameter, so a caller cannot ask it to back off. It is called **after** the caller has already write-latched heap **data** pages:

| Caller | Data page held (W) | Header fixed here |
|---|---|---|
| `heap_delete_relocation` | `forward_page_watcher_p` | `heap_file.c:22770` |
| `heap_delete_home` | `home_page_watcher_p` | `heap_file.c:23116` |
| `heap_update_relocation` | `forward_page_watcher_p` | `heap_file.c:23550` |
| `heap_update_home` | `home_page_watcher_p` | `heap_file.c:24037` |
| `vacuum_heap_prepare_record` (REC_RELOCATION) | `home_page` + `forward_page` | `vacuum.c:2086` |
| `vacuum_heap_prepare_record` (REC_HOME) | `home_page` | `vacuum.c:2202` |

The eager helper runs **server-side too** — `heap_oos_delete_unreferenced`'s `!is_mvcc_op` gate fires for MVCC-disabled catalog classes (its own comment, `heap_oos.cpp:411`), so this is not SA-mode-only.

### The concrete deadlock
Because the header ranks *before* data pages, holding a data page and then unconditionally waiting on the header inverts the canonical order:

- **Thread A** (INSERT via `heap_stats_find_best_page`): holds the **header** (W), waits for **data page X**.
- **Thread B** (eager OOS delete, or vacuum OOS prepare): holds **data page X** (W via home/forward watcher), then `heap_oos_find_vfid` issues an **unconditional** wait on the **header**.

A waits for X (held by B); B waits for the header (held by A) → classic AB/BA deadlock.

### The project's own evidence this is unsafe
- The sibling lookup `heap_ovf_find_vfid` reads the **same** header page but **accepts a `PGBUF_LATCH_CONDITION` parameter** (`heap_file.c:6474`).
- The **REC_BIGONE branch in the very same `vacuum_heap_prepare_record`** uses the correct pattern (`vacuum.c:2106-2135`): try a **conditional** latch; on failure, release the home page, re-fix unconditionally, and `goto retry_prepare`.

The new OOS sites simply skip that dance.

### Fix
Give `heap_oos_find_vfid` a `PGBUF_LATCH_CONDITION` parameter (mirroring `heap_ovf_find_vfid`) and, at each call site, use the conditional-latch + release-and-retry pattern the REC_BIGONE / overflow paths already use:
1. try `heap_oos_find_vfid(..., PGBUF_CONDITIONAL_LATCH)`;
2. on conditional-latch failure, release the held data page(s), retry with `PGBUF_UNCONDITIONAL_LATCH`, re-fix the data page(s), and restart the operation.

This preserves the global header→data order and removes the inversion. Until fixed, the hazard is a low-probability but real deadlock between concurrent inserts/updates and OOS reclamation on the same heap.

---

## Summary table

| Caveat | Verdict | Why |
|---|---|---|
| Rollback resurrects a row whose OOS vacuum already freed | ✅ **Safe (not a bug)** | Visibility-threshold gate (`vacuum.c:3248/3538`) + abort ordering (`log_manager.c:5304` before `:5317`) keep an abortable txn's MVCCID active, so its block is never vacuumed |
| `heap_oos_find_vfid` unconditional header fix under held data latches | 🟠 **Confirmed deadlock hazard** | Inverts header→data order; sibling `heap_ovf_find_vfid` + REC_BIGONE path use conditional+retry, the new OOS sites don't |
