# Code Review — CUBRID/cubrid#8761 + Linked TC PRs (CBRD-27800)

**Goal.** Review `[CBRD-27800] Keep the HA applylogdb from reusing the record buffer of an item it has not flushed` and its linked testcase PRs (`cubrid-testcases-private-ex#5173`, `cubrid-testcases#4482`). Scope:
- `la_recdes_pool` / `LA_RECDES_EXTRA` buffer lifecycle, ownership, OOM/error handling, LIFO return, and reset/release boundaries.
- Edge cases across OOS multi-chunk rebuilds, large records, >200-item bulk flushes, retryable errors, and failover/restart recovery.
- Whether the linked TC PRs reproduce the failure mode and verify the fix.

**Most consequential result.** **Changes required (`CHANGES_REQUESTED`).** While the core `LA_RECDES_POOL` / `LA_RECDES_EXTRA` buffer-exclusivity mechanism isolates unflushed buffers past 200 items cleanly under normal execution (verified via a real-code `log_applier.c` probe under Valgrind), commit `83bfa2dbff` (`db_find_class()` now setting `error`) exposes **two confirmed retry-state defects** (`F-01` P1 silent multi-chunk OOS truncation, `F-02` P2 premature OOS flush split causing server abort/restart) in `src/transaction/log_applier.c`. Both were reproduced against the pinned implementation. Both linked TC PRs are also currently empty (`changedFiles=0`).

| Item | Value |
|---|---|
| Engine PR | https://github.com/CUBRID/cubrid/pull/8761 (`OPEN`, non-draft, author `H2SU`) |
| Base / Head / Merge-Base | `1832399bec50eb7ad44f2a019d573f8468726d0e` / `83bfa2dbff7beb27d0b880956a970cf86a1f5e37` / `a5819390d35000481e6899bf4910bbf0828dd241` |
| Comparison | `git diff a5819390d35000481e6899bf4910bbf0828dd241 83bfa2dbff7beb27d0b880956a970cf86a1f5e37` (sha256 `37d3777bb87190ed65410054c2f41c590b5a0f0f645e067a1bc5ddc61a25a95b`); `src/transaction/log_applier.c` (`+178/-20`) |
| Linked Private TC PR | `cubrid-testcases-private-ex#5173` (private, `DRAFT`, `tc/pr-8761`, base `dc81c782723f7faa8378a50deaa69bbb4ad49549`, head `e1ec6fbc61828eb979b97bd512bcac34920ebd57`, `changedFiles=0`) |
| Linked Public TC PR | https://github.com/CUBRID/cubrid-testcases/pull/4482 (`DRAFT`, `tc/pr-8761`, base `ddd4004605e2436f5099ff27f0fc0ec36515c18f`, head `6aa6ab1e9ce691da60f38526729ee3328ad3c988`, `changedFiles=0`) |
| Snapshot | `2026-11-26 18:15 KST` (rechecked at `2026-11-27 12:48 KST`: PR moved to base `6f5ac7a9f95244b21b32ed0034d4ddef3464943a` / head `9bee33929dcf8c558fb90141f0ec7be7fc55c599` via `Merge branch 'develop' into CBRD-27800`; TC PRs rebased to `d605a34c86bad159c2a0c3f9c9bb0f20b55abd59` and `67a6662e816df030ceef9146230936a2c824da52`, both still `changedFiles=0`) |

> **PR Movement / Delta-Review Notice (`2026-11-27 12:48 KST`):** After this review snapshot (`83bfa2dbff`) completed, `CUBRID/cubrid#8761` merged `develop` into `CBRD-27800` at head `9bee33929dcf8c558fb90141f0ec7be7fc55c599` (base `6f5ac7a9f95244b21b32ed0034d4ddef3464943a`), and both linked TC PRs rebased (`changedFiles=0`). All findings below remain tied to the original reviewed snapshot `a5819390d3..83bfa2dbff`; a delta review covering `83bfa2dbff..9bee33929d` and any follow-up fixes is required.

---

## Verdict and Follow-up

- **Verdict:** `changes-required` (GitHub review recommendation: **`CHANGES_REQUESTED`**)
- **Follow-up review required:** `yes` — `F-01` and `F-02` require fixes and delta re-verification, plus TC PR additions and live two-node HA end-to-end verification.

---

## Confirmed Findings

### F-01 (`P1`, PR-exposed): Retryable failure in `la_apply_oos_insert_log()` clears `apply->need_oos_rebuild` before retry, silently storing only the tail chunk
- **Location:** [`src/transaction/log_applier.c#L6497-L6611`](https://github.com/CUBRID/cubrid/blob/83bfa2dbff7beb27d0b880956a970cf86a1f5e37/src/transaction/log_applier.c#L6497-L6611) (`la_apply_oos_insert_log`) and [`#L7316-L7325`](https://github.com/CUBRID/cubrid/blob/83bfa2dbff7beb27d0b880956a970cf86a1f5e37/src/transaction/log_applier.c#L7316-L7325) (`la_apply_repl_log`).
- **Preconditions & Actors:** Master replicates a multi-chunk OOS value (`RVREPL_DUMMY_OOS_RECORD` followed by `RVREPL_OOS_INSERT` pointing at `tail_chunk_lsa`). On the slave, `la_apply_oos_insert_log()` fails with a retryable error (`la_retry_on_error()`, e.g., `ER_PAGE_LATCH_TIMEDOUT`, `ER_LK_DEADLOCK_CYCLE_DETECTED`, or an error in `ha_applylogdb_retry_error_list`) inside `db_find_class()` (`:6506`, newly returning `er_errid()` in commit `83bfa2dbff`), `la_rebuild_oos_recdes()`, or `la_repl_add_object()`.
- **Violated Invariant:** Multi-chunk `RVREPL_OOS_INSERT` must reconstruct the full OOS payload from all chunks before queuing the `WS_REPL_OBJ`; retry must preserve `apply->need_oos_rebuild`.
- **Source Argument:** `la_apply_oos_insert_log()` snapshots `bool rebuild_oos = apply->need_oos_rebuild;` at `:6497`, then unconditionally executes `if (rebuild_oos) { apply->need_oos_rebuild = false; }` in `end:` (`:6608-6611`) even when `error != NO_ERROR`. When `la_apply_repl_log()` retries the same item (`:7324`), `apply->need_oos_rebuild` is `false`. Attempt 2 enters the single-chunk `else` branch (`:6533-6562`), reads only `item->target_lsa` (the tail chunk, which is itself an `RVOOS_INSERT` / `REC_HOME` record), passes `:6564-6578`, and queues only the tail chunk's bytes instead of `total_data_length`. Reading the row on the slave later fails with `ER_HEAP_OOS_CORRUPTED_RECORD` or silently yields truncated data.
- **PR Attribution:** Clearing `need_oos_rebuild` in `end:` is pre-existing on `la_rebuild_oos_recdes()` / `la_repl_add_object()`; commit `83bfa2dbff` (`:6510`) newly made `db_find_class() == NULL` return `er_errid()` instead of `NO_ERROR`, exposing `db_find_class()` retryable failures to this path.
- **Verification (Real-Code Probe 2):** Compiled a C++ harness including unmodified `src/transaction/log_applier.c` and linking `libcubridcs.so` with `--wrap` fault injection (`ER_PAGE_LATCH_TIMEDOUT` once on `db_find_class()` for a 2-chunk 2000B OOS record: 500B tail + 1500B head). Expected queued `WS_REPL_OBJ` `recdes->length == 2032` (`OOS_RECORD_HEADER_SIZE + 2000`); actual output: `PROBE 2 RESULT: expected recdes->length=2032, actual recdes->length=532 (tail-chunk only=532)`. **Evidence Level: 4.**
- **Fix Direction:** Clear `apply->need_oos_rebuild = false` only on `error == NO_ERROR` (or when `la_apply_repl_log()` retires the item on a non-retryable error without `LA_IS_RESTART_ERROR`).

### F-02 (`P2`, PR-exposed): Retryable failure while `pending_oos_flush == true` clears `pending_oos_flush`, splitting OOS items from their heap row at `num_unflushed >= 200`
- **Location:** [`src/transaction/log_applier.c#L5900-L5906`](https://github.com/CUBRID/cubrid/blob/83bfa2dbff7beb27d0b880956a970cf86a1f5e37/src/transaction/log_applier.c#L5900-L5906), [`#L6619`](https://github.com/CUBRID/cubrid/blob/83bfa2dbff7beb27d0b880956a970cf86a1f5e37/src/transaction/log_applier.c#L6619), [`#L6685`](https://github.com/CUBRID/cubrid/blob/83bfa2dbff7beb27d0b880956a970cf86a1f5e37/src/transaction/log_applier.c#L6685), [`#L6808`](https://github.com/CUBRID/cubrid/blob/83bfa2dbff7beb27d0b880956a970cf86a1f5e37/src/transaction/log_applier.c#L6808); [`src/transaction/locator_sr.c#L9430-L9436`](https://github.com/CUBRID/cubrid/blob/83bfa2dbff7beb27d0b880956a970cf86a1f5e37/src/transaction/locator_sr.c#L9430-L9436).
- **Preconditions & Actors:** `la_Info.num_unflushed >= LA_MAX_UNFLUSHED_REPL_ITEMS` (200) and `la_Info.pending_oos_flush == true`. The next item (`RVREPL_OOS_INSERT`, `RVREPL_OOS_REUSE`, or owning heap `RVREPL_DATA_INSERT`) fails once with a retryable error in `db_find_class()` (newly returning `er_errid()` in `83bfa2dbff`) or `la_repl_add_object()`.
- **Violated Invariant:** `la_Info.pending_oos_flush` must stay `true` until the owning heap record is added (or the incomplete OOS group is discarded), so `la_flush_repl_items(false)` never flushes OOS items without their owning heap row.
- **Source Argument:** `la_apply_oos_insert_log:6619`, `la_apply_oos_reuse_log:6685`, and `la_apply_insert_log:6808` unconditionally clear `la_Info.pending_oos_flush = false;` in `if (error != NO_ERROR)` before `la_apply_repl_log()` retries via `la_retry_on_error()` (`:7316-7325`). On retry, `la_flush_repl_items(false)` (`:5900-5907`) sees `pending_oos_flush == false && num_unflushed >= 200` and flushes the queued OOS items without the heap row to `xlocator_repl_force()`, aborting at `if (row_topop_active)` (`locator_sr.c:9430`) with `ER_LC_FAILED_TO_FLUSH_REPL_ITEMS`.
- **Verification (Real-Code Probe 3):** With `num_unflushed = 200`, `pending_oos_flush = true` (ending in `LC_FLUSH_INSERT_OOS`), and 1 transient `ER_PAGE_LATCH_TIMEDOUT` in `db_find_class()` on the owning `RVREPL_DATA_INSERT`, the wrapped `locator_repl_flush_all()` fired on attempt 2 with `num_objs=200, last_op=6 (LC_FLUSH_INSERT_OOS)` before `RVREPL_DATA_INSERT` was added. **Evidence Level: 4.**
- **Fix Direction:** Preserve `la_Info.pending_oos_flush` across retryable failures (`la_retry_on_error()`).

### F-03 (`P3`, PR-introduced latent pool invariant break): `la_realloc_recdes_data()` OOM nulls `recdes->data` before `la_return_recdes_to_pool()`
- **Location:** [`src/transaction/log_applier.c#L2438-L2580`](https://github.com/CUBRID/cubrid/blob/83bfa2dbff7beb27d0b880956a970cf86a1f5e37/src/transaction/log_applier.c#L2438-L2580).
- **Source Argument & Containment:** On OOM at `:2446`, `la_realloc_recdes_data()` sets `recdes->data = NULL` while leaving `recdes->area_size == db_page_size` (or old `> db_page_size` after `free_and_init` at `:2443`). Returning that pool slot via `la_return_recdes_to_pool()` breaks the pool slot invariant (`assert(recdes->data != NULL)` at `:2487`). In live `applylogdb`, this is currently contained because `ER_OUT_OF_VIRTUAL_MEMORY` propagates via `LA_IS_RESTART_ERROR` (`:7287, :7715, :10067`) to `la_shutdown()` before `la_assign_recdes_from_pool()` is called again.
- **Verification (Real-Code Probe 4):** Confirmed `r->data == NULL` and `r->area_size == 16384` after `la_realloc_recdes_data()` OOM, and confirmed a subsequent `la_assign_recdes_from_pool()` in a forked child aborts at `log_applier.c:2487` (`SIGABRT`). **Evidence Level: 4** (contained in live `applylogdb` at **Level 3**).
- **Fix Direction:** Allocate into a temporary pointer in `la_realloc_recdes_data()` so `recdes->data` is preserved on `malloc` failure.

---

## Safety Facts and Effects Outside the Diff

| # | Safety Fact | Source Locations | Evidence Level | Tested / Conditions |
|---|---|---|---|---|
| S1 | **Unflushed buffer exclusivity (core fix):** `num_assigned` prevents pool wrap-around reuse past `200`, allocating `LA_RECDES_EXTRA` buffers freed only in `la_release_recdes_pool()` after `ws_clear_all_repl_objs()`. | `log_applier.c:2478-2534, 2588-2600, 5896, 6008-6009` | **4** (`Probe 1` + Valgrind) | 250 consecutive buffers (200 pool + 50 extra), `la_realloc_recdes_data` (>16KiB), `la_return_recdes_to_pool` (extra head + pool wrap-around), `la_release_recdes_pool()`, page-size reinit, `0` leaks. |
| S2 | **`LA_RECDES_EXTRA` alignment & realloc pairing:** `sizeof(LA_RECDES_EXTRA) == 32`; `(char *)(extra + 1)` is 16B-aligned with `area_size == db_page_size`, so `la_realloc_recdes_data()` and `la_free_extra_recdes()` free `recdes.data` iff `area_size > db_page_size`. | `log_applier.c:408-413, 2440, 2513-2549` | **4** (`Probe 1` + Valgrind) | Normal and resized extras freed with 0 Valgrind errors. |
| S3 | **Client-to-server >200-item batch compatibility:** `ws_repl`, `locator_repl_mflush`, `locator_mflush_grow_copy_area`, `slocator_repl_force`, `xlocator_repl_force`, and `locator_fixup_oos_oids_in_recdes` have no 200-item hard cap (bounded by copy-area max `INT_MAX - db_network_page_size()`). | `locator_cl.c:3899-3930, 7034-7179`, `locator_sr.c:9154-9450, 17057-17179`, `network_interface_sr.cpp:1342-1375` | **3** (source trace) | Live 2-node HA stress test not executed. |
| S4 | **Slotted MVCC expansion headroom:** Non-overflow `RVHF_INSERT` records leave >80B under `db_page_size`, so <=24B MVCC room insertion in `la_get_recdes()` cannot overflow pool or `LA_RECDES_EXTRA` tail buffers. | `log_applier.c:4474-4525, 5797-5843`, `heap_file.c:3967-3969`, `slotted_page.c:842-845` | **3** (source trace) | Source trace only. |
| S5 | **OOM restart boundary (`LOG_COMMIT` / `LOG_SYSOP_END`):** With default `commit_on_shutdown=false`, `LA_IS_RESTART_ERROR` exits `la_apply_repl_log` and `la_log_record_process` without updating `committed_rep_lsa` / `committed_lsa` / `_db_ha_apply_info`, runs `la_shutdown()`, and exits (`EXIT_FAILURE`) for `cub_master` respawn. | `log_applier.c:7287, 7715, 10067`, `util_cs.c:3568, 3590`, `boot_cl.c:1672`, `master_heartbeat.c:4138` | **3** (source trace) | Pre-existing caveat if `commit_on_shutdown=yes`; remaining `LA_IS_FLUSH_ERROR` sites noted in `U1`. |
| S6 | **Failover / role change / `la_shutdown` cleanup:** `la_shutdown()` calls `ws_clear_all_repl_objs()` before `la_clear_recdes_pool()` (`la_release_recdes_pool()`), resetting `num_unflushed`, `pending_oos_flush`, and `extras`. | `log_applier.c:7947, 7995, 8586-8595, 9860` | **3** (source trace) | Source trace only. |

---

## Verification & Coverage Limits

- **Build & Static Analysis (`83bfa2dbff`, `debug_gcc`):**
  - Full CMake `debug_gcc` build succeeded (`1774/1774` targets, 0 compiler warnings on `src/transaction/log_applier.c`).
  - `cubrid-static-check` (`a5819390d3..83bfa2dbff`): 0 new cppcheck, PMD CPD, or complexity flags; `clang-tidy` exited incomplete due to missing `re2/re2.h` in `src/query/string_regex.hpp:27`.
  - `test_oos_sql_log_cache`: 4/4 passed.
  - Real-code `log_applier.c` probe under Valgrind (`--leak-check=full --error-exitcode=42 --trace-children=no`): `0` memory errors, `0` leaked bytes (`Probe 1` verified 250-buffer isolation/cleanup; `Probes 2–4` confirmed `F-01`, `F-02`, and `F-03`).
- **Concurrency:** Marked Not Applicable because `applylogdb` executes log application on a single main thread (`sig_interrupt` sets shutdown flags; `sigusr1` dump does not access `la_recdes_pool`).
- **Coverage limits:** Live two-node HA cluster replication (including async mode, small-transaction accumulation >200 items, single-row >200 OOS columns, and OOM restart) was not executed in this single-host review.

---

## Linked Testcase PRs (`cubrid-testcases-private-ex#5173` & `cubrid-testcases#4482`)

- **Status:** Both `cubrid-testcases-private-ex#5173` and `cubrid-testcases#4482` are empty draft PRs (`changedFiles=0`, containing only bot branch-initialization commits on `tc/pr-8761`).
- **Assessment:** Neither PR currently reproduces the failure mode or verifies the fix. A separate historical branch in the private testcase repository contains a disabled flush-boundary shell test that sets up a two-node synchronous HA pair, inserts 120 rows with four OOS-capable columns each (crossing the 200-item pool boundary twice), and compares every row individually across master and slave; however, that test is not yet enabled on `develop` or in `#5173`. Additional coverage is also needed for retryable errors (`F-01`, `F-02`), single-row >200 OOS columns, >200 items accumulated across small transactions, `UPDATE` with OOS reuse, and `ha_copy_sync_mode=async`.

---

## Unverified Risks, Pre-existing Issues, and Dropped Candidates

### Unverified Risks (Source-Only, Level 3)
1. **`U1` — Incomplete `LA_IS_RESTART_ERROR` replacement in `la_apply_log_file()` (`P2`):** Commit `83bfa2dbff` left `LA_IS_FLUSH_ERROR` at `src/transaction/log_applier.c:9861`, `:10110`, and `:10136`. If `la_commit_transaction()` inside `la_log_commit()` returns `ER_OUT_OF_VIRTUAL_MEMORY`, `:10110` drops it and `:9861` drops it after overwriting `la_Info.committed_lsa = final_lsa` (`:9852`). Replace `LA_IS_FLUSH_ERROR` with `LA_IS_RESTART_ERROR` at those three sites.
2. **`U2` — `la_apply_update_log()` vs `pending_oos_flush` & orphaned OOS items on permanent skip (`P3`):** `la_apply_update_log()` (`:6345-6352`) never clears `pending_oos_flush` on error; on a non-retryable skip after OOS items (including `db_find_class() == NULL`), `m_Repl_objs` retains orphaned OOS items while `pending_oos_flush` stays `true`, causing cross-row OOS attachment or `xlocator_repl_force` abort loops (the same orphaned-OOS hazard exists for permanent skips in `insert`/`oos_insert`).

### Pre-existing Issues (Outside PR Verdict)
- `la_init_recdes_pool()` (`log_applier.c:2622-2634`) leaks `area` if `recdes_arr` allocation fails; `la_apply_log_file()` (`:9701-9747`) returns without calling `la_clear_recdes_pool()` after `:9682`.
- `util_cs.c:3590-3594` does not retry `ER_OUT_OF_VIRTUAL_MEMORY` in-process (same as `ER_LC_FAILED_TO_FLUSH_REPL_ITEMS`), relying on `cub_master` heartbeat respawn.
- `locator_repl_mflush` (`src/transaction/locator_cl.c:7084`) grows `copy_area` linearly instead of geometrically when `pending_oos_item == true`, giving quadratic copy cost for very wide >200-OOS rows, and leaks a dequeued `repl_obj` on mid-loop error returns (`:7071, :7089, :7097`) or can overwrite an earlier `ER_LC_PARTIALLY_FAILED_TO_FLUSH` (`:7094`).

### Dropped / Disproven Candidates
- **`la_get_recdes()` unchecked error (Disproven):** `src/transaction/log_applier.c:5747-5762` immediately returns `error` (or `ER_FAILED`) when `error != NO_ERROR || logs == NULL`, before reaching `:5764-5843`.
- **`snprintf(..., item->class_name)` NULL in `la_apply_repl_log:7291` (Cleared):** `la_need_filter_out()` (`:9251`) already accesses `item->class_name` prior to item execution; statement replication defaults empty class names to `"-"`.
