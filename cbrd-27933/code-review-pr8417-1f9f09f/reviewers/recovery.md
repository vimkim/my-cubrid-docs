# Recovery/vacuum review: PR #8417 (CBRD-27933)

- Pinned: base d52b1889e907, head 1f9f09f36239 (verified `git rev-parse HEAD` in review-8417/src). Patch: review-8417/pr.patch.
- Coverage: complete (source-only, so evidence is level 2 or 3). I ran no build, server or ctest, as the coordinator owns runtime checks. No probes were written.
- Inspected: vacuum.c `vacuum_heap` (1553), `vacuum_heap_page` (1676), `vacuum_heap_prepare_record` (2047), `vacuum_heap_prepare_oos_vfid` (2352), `vacuum_heap_record` (2584), `vacuum_heap_page_log_and_reset` (2859), `vacuum_process_log_block` (3548, end at about 3918), `vacuum_finished_block_vacuum` (4060), `vacuum_data_mark_finished` (4967), `vacuum_data_load_and_recover` (4526), the RVVAC_DATA_FINISHED_BLOCKS redo (about 5360), `vacuum_min_log_pageid_to_keep` (6079), dropped-files cleanup (6877), `vacuum_data::update` (8449), `vacuum_job_cursor::force_data_update` (8710), master `execute` (3287) and `xvacuum` SA (992). In vacuum_oos.cpp, all of the file. In heap_file.c, `heap_oos_find_vfid_internal` (13237) and `heap_vacuum_all_objects` (about 26584). Also the design document my-cubrid-docs/cbrd-27933/fix-decisions.md.

## Shared challenge question (answered independently)

**(a) Can a heap record be removed while its OOS value is not reclaimed?** Not through the new paths (level 3).
- Removal with OOS happens only in `vacuum_heap_record`. There, `has_oos` requires `!VFID_ISNULL(oos_vfid)`. Slot removal and `vacuum_heap_oos_delete_within_sysop` run in one sysop. On an OOS delete error, `log_sysop_abort` restores the slot.
- After the patch, `oos_vfid` can be NULL for an OOS record only when a lookup succeeded and the heap header has no OOS file. That is the logical-defect case. It now reaches `vacuum_oos_report_missing_oos_file`, which asserts in debug builds; release builds keep the old bounded leak, by design (decision 1).
- A failed lookup now always returns an error. `ASSERT_ERROR_AND_SET` turns a missing er into ER_FAILED, and a worker converts it to -1393. The record is not touched.
- In the RELOCATION and HOME retry after a wait (`oos_header_waited`), `oos_vfid` is already set for the heap, so skipping the second lookup is safe.

**(b) Can an OOS value that is still referenced be reclaimed?** No new exposure (level 3).
- A re-run repeats two kinds of work:
  - The forward-walk deletes. `oos_delete` uses the identity stamp and does nothing on an already freed or reused chain (vacuum_oos.cpp, comment in `vacuum_forward_walk_oos_delete_atomic`, CBRD-26950).
  - REMOVE on already vacuumed slots. A slot that is gone reads as REC_MARKDELETED or is skipped. A slot that was reused holds a new record, and `mvcc_satisfies_vacuum` against the fresh threshold removes that record, with its own OOS, only if it is truly dead.
- Neither path frees an OOS value that a live record references.

**(c) Can a log block be marked fully vacuumed while an object in it was skipped?** Not through the deferral (level 3).
- `vacuum_heap` returns non-zero whenever `deferred` is set: it returns -1393 itself, or keeps a later OOM or shutdown error through `er_stack_pop_and_keep_error`.
- `vacuum_process_log_block` then jumps to `end` with `vacuum_complete=false`. `vacuum_finished_block_vacuum` calls `set_interrupted`, and the master's `vacuum_data_mark_finished` sets the entry to interrupted. Only the VACUUMED flag (`set_vacuumed`) lets `index_unvacuumed` move past an entry.
- The durable state sequence:
  1. On-disk entry: available or in progress (the in-progress state is not logged).
  2. Partial heap work, durable through WAL: bulk-vacuumed slots and committed per-record sysops.
  3. The master logs RVVAC_DATA_FINISHED_BLOCKS with the interrupted flag.
  4. A crash at any point re-runs the block, either from the unlogged available or in-progress state (`vacuum_data_load_and_recover` turns in-progress into interrupted) or from the logged interrupted state.
- No crash point produces VACUUMED.
- Pre-existing exception, not introduced by this PR: in release builds, a `vacuum_heap_record` error (for example an OOS delete error, after which the sysop aborts) reaches `assert_release(false); continue` in `vacuum_heap_page`. The block is then marked complete with that record still there. The record and its OOS both remain, so nothing dangles, but they are garbage forever. See P2.

## Assigned invariants

1. **Re-run is full and idempotent.** Holds (level 3).
   - Other heaps were committed in the first run, and a re-run repeats their work idempotently as in (b). The B-tree vacuum done during the log walk also repeats; that is pre-existing interrupted-block behaviour.
   - `was_interrupted=true` routes the re-run through `pgbuf_fix_if_not_deallocated`.
   - A deallocated page can be reused only by the same file, because file sectors go back to disk only when the file is destroyed, and vacuum skips dropped files. So the reuse case is the same as slot reuse.
2. **The interrupted state survives a restart.** Holds (level 2). The interrupted flag is logged with RVVAC_DATA_FINISHED_BLOCKS and replayed at about 5360. If a crash happens before that, the entry is still not vacuumed on disk, and load turns in-progress into interrupted. The in-memory `m_retry_blockid` is lost on restart, but `set_on_vacuum_data_start` starts the cursor at the first block, which is at or before the interrupted block.
3. **Objects before the failure are complete, objects after it are untouched, and the skip stays inside one heap.** Holds (level 3).
   - `vacuum_heap_prepare_oos_vfid` calls `vacuum_heap_page_log_and_reset(..., false, true)` before the waiting lookup. That logs the pending bulk slots of the same page and unfixes the page. Earlier OOS records committed their own sysops, and earlier pages finished.
   - The skip loop advances only while `VFID_EQ(page_ptr->vfid, vfid)`, starting after the current page group. The objects are sorted by VFID first.
4. **Sysop boundaries and page fixes.** Hold (level 3). -1393 can be raised only in the prepare phase. At that point no sysop is open, because a sysop exists only inside `vacuum_heap_record`. The forward page and home page are unfixed before the wait, and the error return happens before the home page is fixed again. `vacuum_heap_page` jumps to `end` with `home_page == NULL`, and in server mode `pgbuf_unfix_all` runs at block end.
5. **Oldest-visible MVCCID and archive retention.** Hold (level 2).
   - An interrupted entry blocks `index_unvacuumed`. As a result, `keep_from_log_pageid` (`vacuum_min_log_pageid_to_keep`) keeps the block's log.
   - `oldest_unvacuumed_mvccid`, taken from the first entry, stays low. That keeps the dropped-files entries the re-run needs (6877) and keeps `vacuum_is_mvccid_vacuumed` conservative.
   - The re-run uses a fresh, higher threshold, which is safe.

## Candidate findings (none blocking)

- **R1 (low): emptied OOS pages are not reclaimed on the failing page.** vacuum.c `vacuum_heap_page` `end:`, `if (error_code == NO_ERROR && !oos_emptied_pages.empty ())`.
  - What happens: earlier OOS-bearing records on the same page that commit their deletes before a later record on that page defers leave their emptied OOS pages unreclaimed. The re-run cannot collect them again because those records are gone, so the pages wait for the growth-gate sweep.
  - Scope: pre-existing for OOM and interrupt errors; deferral makes it more frequent. This is a space issue only, not a lost value.
  - Fix direction: reclaim the emptied pages even when the error is -1393. The pages belong to committed sysops; the -1393 path holds no page latch and `helper.oos_vfid` is set when the list is non-empty.
  - Evidence level 2.
- **R2 (low, design question): a lookup that keeps failing pins the block forever.** Cause: a persistent I/O error or a corrupted heap header page.
  - Effect: the block never completes. `index_unvacuumed`, `keep_from_log_pageid` and `oldest_unvacuumed_mvccid` stop moving, so log archives and dropped-files entries grow without bound. The block re-runs about once a second and writes an error log line each time. Before this change the cost was one leaked value.
  - Design status: fix-decisions.md "남은 일" left open how far to give up on a failing block. The PR never gives up. That is acceptable for correctness, but the decision should be stated, with an operator signal or a cap on the log volume.
  - Evidence level 2.
- **R3 (low, pre-existing, more frequent): a deferred single-object page can stay HEAP_PAGE_VACUUM_ONCE forever.** vacuum.c about 1925, condition `(ONCE && !was_interrupted) || (NONE && was_interrupted)`.
  - What happens: a page whose only object is deferred keeps the ONCE status. The re-run uses `was_interrupted=true`, so ONCE never becomes NONE, and vacuum can never deallocate the page. The page is still reusable through best space.
  - Evidence level 2.

## Pre-existing defects (reported separately; not introduced)

- **P1.** In release builds, the generic error path in `vacuum_heap` does `er_clear(); error_code = NO_ERROR; continue;` without advancing `page_ptr`. A persistent non-OOM error therefore retries the same page forever. The PR removes the OOS-lookup source of this spin; the old comment in vacuum_oos.cpp described it.
- **P2.** In release builds, `vacuum_heap_page` does `assert_release(false); continue` after a `vacuum_heap_record` error, and the block can then be marked complete with that object not vacuumed (see (c)).
- **Behaviour change, safe direction.** A non-worker caller, `heap_vacuum_all_objects`, now gets the raw lookup error instead of a silent leak.
- **SA mode.** `xvacuum` stops at the first -1393 and leaves the block interrupted. For the partial block it sets `does_block_need_vacuum` and `interrupted_partial_blockid`. This is consistent; boot_sr.c:2673 ignores the result.

## Rejected hypotheses

- **The retry throttle could lose an interrupted block.** Rejected. `m_retry_blockid` keeps the minimum until the timer passes, and `readjust` cannot pass an unvacuumed entry.
- **The skip could cross into another heap through a mixed-VFID page group.** Rejected. Even if a reused page's group mixes VFIDs, everything skipped is covered by the interrupted block.
- **The `er_stack` handling could leave the wrong errid for the finished-block assert.** Rejected. `er_stack_pop` restores -1393, and a later error is kept with `pop_and_keep`.

## Unresolved items and next checks (coordinator)

- No restart test covers an interrupted -1393 block (crash after the first run, then a server restart). Cheapest decisive check: a fault-injection case like `HomeRowOosReclaimedAfterHeaderLookupFailure`, plus a server restart before the re-run, then check the reclaimed OOS and the vacuum data.
- No test covers same-page partial progress (objects before the failure on the same page, then a re-run). Its idempotence rests on the source argument above.
