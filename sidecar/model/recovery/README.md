# Sidecar recovery, undo safety and latch order in TLA+

This directory checks the Sidecar design (`../../design.md`, Gate 1 approved on 2026-11-04) for three things before any engine code exists: crash recovery keeps each row whole, every undo that Sidecar can start finds its slot and its bytes, and the latch order cannot deadlock. A separate model in `../lifecycle/` checks the value lifecycle and reader safety. This is a design model, not a verify skill. Each model action names the design section and the `develop` line at `e64a04a79` (worktree `/home/vimkim/gh/cb/sidecar`) that it stands for.

Last modified: 2026-11-04, Asia/Seoul.

## Run it

```bash
python3 run.py
```

`run.py` runs every configuration in `cfg/` with Java on `PATH` and `~/.cache/tlaplus/tla2tools-1.7.4.jar` (`TLA2TOOLS_JAR` overrides it). It prints one line per run with `PASS` or `FAIL`, the distinct state count, the time, and the expected result, then the steps of every counterexample in design words. TLC output goes to a new directory under the system temp directory, and `run.py` prints its path. `--only TEXT` runs the configurations whose name contains `TEXT`. The exit status is 0 when every run matches its expectation, 1 when one does not, and 2 when TLC cannot run.

The 35 runs take about 2.5 minutes of wall time on this 80-core host (143 s measured on 2026-11-04), at 8 TLC workers per run and 10 runs at a time. The largest run has 2.9 million distinct states.

| File | What it is |
| --- | --- |
| `SidecarRecovery.tla` | Crash recovery and undo. Properties `UndoFindsEmptySlot`, `UndoFindsRoom`, `AtomicRow`. |
| `SidecarLatch.tla` | Page latch waits. Property `NoDeadlock`. |
| `cfg/*.cfg` | One configuration per property and variant. The first lines name the spec, the expected result and the purpose. |
| `run.py` | Runs every configuration and checks the result against its expectation. |

## Properties

| Property | Promise | Harm if broken |
| --- | --- | --- |
| `UndoFindsEmptySlot` | Every undo finds its slot as it needs it: empty for an undo that re-inserts a record (`spage_insert_for_recovery`), and holding the undoer's own record for an undo that rewrites it in place (`spage_update`, `heap_rv_mvcc_undo_delete`). | A re-insert writes over a committed row (a debug build stops on the assertion), and a rewrite of a missing record stops restart in `logpb_fatal_error`. |
| `UndoFindsRoom` | Every undo that grows a record back finds enough free bytes on its page. | Restart recovery or rollback stops in `logpb_fatal_error` (`transaction/log_recovery.c:337`), so the server cannot start. |
| `AtomicRow` | After restart recovery, and once vacuum has removed every store record with a committed DELID, a committed row's hot record exists and every store record it names is present, no other store record of that row is live, and every other committed transaction's record is intact. | A committed row loses a large value, or an uncommitted or dropped value stays in the store forever. |
| `NoDeadlock` | No reachable state has a cycle of page latch waits. | Threads hang on page latches; CUBRID has no latch deadlock detector. |

## What the models contain

**`SidecarRecovery.tla`.** One hot page `hp` and two store pages `s1` and `s2`. A store record takes 2 units of bytes, a hot record with a ref takes 1, and a hot record with an inline large value takes 2. A transaction can also put a record on a page that the heap allocates when no modeled page has room. The actors are these.

- T, the row's transaction, runs one flow of design section 6 and then commits, rolls back, or rolls back its statement and commits. The flows are INSERT, UPDATE of a value that already has a ref (`UPD_REF`), UPDATE that moves a previously inline value out (`UPD_EXT`), and DELETE. T writes the store first and then the hot record, holding one page latch per step and none between steps (I-7). A DELID stamp either fits in place or relocates the store record (`RVHF_INSERT_NEWHOME` plus `RVHF_MVCC_DELETE_MODIFY_HOME`).
- One store vacuum worker removes a dead store record `w` with a committed DELID. `w` is `REC_HOME` (bulk, redo only), `REC_RELOCATION` (REL sysop) or `REC_BIGONE` (BIG sysop, which can abort when `heap_ovf_delete` fails). Vacuum also removes T's stamped value once vacuum may see T's DELID.
- One other transaction inserts one record of 1 or 2 units on any page and commits. It stands for another row's store or hot record.
- One crash at any point, then restart undo of the losers and of an open vacuum sysop in reverse LSA order.

**`SidecarLatch.tla`.** Pages: the hot header `HH`, hot pages `H1` and `H2`, and store pages `S1` and `S2`. Each thread runs a fixed sequence of fixes and unfixes. The model applies plain fixes, ordered fixes with conditional latches and the unfix and refix of later pages, and the page buffer's grant rule for readers behind waiting writers. It explores both orders of the two heap files. The design threads are a reader, the large-column UPDATE writer with its plan read and store writes, store vacuum (REL), the store-creation sysop, and a stock hot UPDATE that relocates its row.

## Mapping from model to design and code

Lines are under `src/` at `e64a04a79`.

| Model action | Design | Code |
| --- | --- | --- |
| `TStoreInsert` | 6 INSERT step 5, UPDATE step 5; I-1, I-7 | `heap_insert_logical` on the store, `storage/heap_file.c:24649`, `RVHF_MVCC_INSERT`; free bytes for an active transaction exclude saved space, `spage_has_enough_total_space`, `storage/slotted_page.c:4610-4629`; only `REC_DELETED_WILL_REUSE` slots are handed out, `:1286` |
| `TStampInPlace` | 6 UPDATE step 5, DELETE step 2; I-4 | `heap_delete_home` `storage/heap_file.c:23257`, `RVHF_MVCC_DELETE_REC_HOME` `:23511`, `heap_update_physical` `:23531` |
| `TStampNewhome` | 6 UPDATE step 5 (the DELID does not fit); I-1; 15 item 776 | `spage_is_updatable` fails `:23411`, `heap_insert_newhome` `:23450`, `RVHF_INSERT_NEWHOME` `:22461` |
| `TStampModifyHome` | same | `heap_mvcc_log_home_change_on_delete` `:23486`, `RVHF_MVCC_DELETE_MODIFY_HOME` with the whole old record as undo `:20741`; `spage_update` shrinks the home slot and saves the freed bytes, `storage/slotted_page.c:2527`, `:2579-2580` |
| `THotInsert` | 6 INSERT step 7 | hot `RVHF_MVCC_INSERT` in `heap_insert_logical` |
| `THotUpdate` | 6 UPDATE step 6 | `heap_update_home` `storage/heap_file.c:24215`, `RVHF_UPDATE_NOTIFY_VACUUM` `:24256`, `heap_log_update_physical` `:24377`, `heap_update_physical` `:24398`, which saves the bytes a shrink frees |
| `THotDelete` | 6 DELETE step 3 | hot `RVHF_MVCC_DELETE_REC_HOME` |
| `TCompleteMvcc` | 5.6, when vacuum may remove a store record | `logtb_complete_mvcc` `transaction/log_manager.c:5255`; `mvcctable::complete_mvcc` keeps the MVCCID in the transaction's lowest visible slot until `LOG_COMMIT`, `transaction/mvcc_table.cpp:492-506` |
| `TCommitWithPostpone` | none | `log_tran_do_postpone` `log_manager.c:5272`, `log_append_commit_postpone` `:4461` |
| `TFreeSaved` | 15 item 776 | `spage_free_saved_spaces` `log_manager.c:5278`; `Fix776` moves it after the commit record |
| `TCommitRecord` | none | `log_append_commit_log` `:5296`, `:5300`; `log_change_tran_as_completed` `:5309` |
| `TAbortStart`, `TUndo`, `TUndoDone` | 6 Rollback | `log_abort_local` `:5356`: `TRAN_UNACTIVE_ABORTED` `:5360`, `log_rollback` `:5371`, `spage_free_saved_spaces` `:5379` |
| `TStmtRollbackStart`, `TUndo`, `TUndoDone` | 6 Statement rollback | `log_abort_partial` `:5637` runs `log_sysop_abort` `:4115`, which sets `TRAN_UNACTIVE_ABORTED` around `log_rollback` `:4142-4147` |
| `UndoRec`, insert | 6 Rollback step 3 | `heap_rv_undo_insert` `storage/heap_file.c:17501`, `spage_delete_for_recovery` `storage/slotted_page.c:2148-2172` |
| `UndoRec`, stamp and hot DELID | 6 Rollback step 2 | `heap_rv_mvcc_undo_delete` `storage/heap_file.c:17625`; a missing record returns `ER_FAILED` `:17638-17642` |
| `UndoRec`, MODIFY_HOME and hot update | 6 Rollback steps 1 and 2; 15 item 776 | `heap_rv_undo_update` `:17943`, `heap_update_physical` returns `ER_FAILED` on `SP_DOESNT_FIT` `:24459-24479` |
| `UndoRec`, vacuum record | 15 item 775 | `vacuum_rv_undo_vacuum_heap_record` `query/vacuum.c:7563`, `heap_rv_redo_insert` `storage/heap_file.c:17286`, `spage_insert_for_recovery` `storage/slotted_page.c:1933` (assertion `:1969`) |
| a failed undo | none | `log_rv_undo_record` `transaction/log_recovery.c:173`, `logpb_fatal_error` `:337` |
| `VacuumFixPages` | 6 Vacuum, relocated store records | `vacuum_heap_page`, `vacuum_heap_prepare_record` fixes the forward page in VPID order, `query/vacuum.c:1995-2040` |
| `VacuumSysopStart`, `VacuumHomeSlot` | 6 Vacuum; I-5 | `log_sysop_start` `:2387`; `spage_vacuum_slot (..., reusable)` `:2398`, `reusable` false for `FILE_HEAP` `:2568`; REL and BIG home logs `:2423`, `:2456` |
| `VacuumForwardSlot` | 6 Vacuum; 15 item 775 | `spage_vacuum_slot (forward_page, ..., true)` `:2428`, log `:2436`, `pgbuf_set_dirty (..., FREE)` `:2439` before `log_sysop_commit` `:2442`; `Fix775` keeps the page until after the commit |
| `OvfDelete`, `OvfDeleteFails`, `VacuumAbortUndo` | 6 Vacuum, BIGONE store records | `heap_ovf_delete` `:2464`, `log_sysop_abort` `:2468` |
| `VacuumSysopCommit`, `VacuumReturn` | 6 Vacuum | `log_sysop_commit` `:2442`, `:2474`; `vacuum_heap_page_log_and_reset` `:1915` |
| `VacuumRemoveV` | 6 Vacuum, `REC_HOME` store records; I-5 | bulk removal `:2392-2398`; `mvcc_satisfies_vacuum` `transaction/mvcc.c:321`; job readiness `query/vacuum.c:3133` |
| `InsertRow`, `InsertCommit` | 15 item 775, store inserts from any transaction | `heap_insert_logical`, `spage_find_free_slot`, `spage_has_enough_total_space` |
| `Crash`, `RecoveryUndo`, `RecoveryDone` | 6 Crash recovery | `log_recovery_undo` `transaction/log_recovery.c:4585`; saved space is ignored in crash recovery, `storage/slotted_page.c:500`, `:718-725` |
| latch `reader` | 6 Wide scan step 2; I-7 | `scan_batch_next_page` `query/scan_manager.c:7848`: header first `:7862`, next page fixed before the old one is released `:7909-7911`; plain store fix (I-7) |
| latch `writer` | 6 UPDATE that assigns a large column; 5.3 `sidecar_plan_update` | plan read under the hot latch, `heap_unfix_watchers` `storage/heap_file.c:21234`, store writes, hot write |
| latch `svacuum` | 6 Vacuum, REL | `query/vacuum.c:1995-2040` |
| latch `creator` | 6 INSERT step 4; I-7 | the `heap_ovf_find_vfid` pattern, plain X fix of the header, `storage/heap_file.c:6062`, `:6079` |
| latch `hotreloc` | none (stock) | `heap_fix_header_page` `:21428-21450`, called at `:24313`, then `heap_insert_newhome` |
| latch `multirow` | 6 Multi-row insert; interrogation finding 1d | `locator_multi_insert_force` `transaction/locator_sr.c:14144`, batch page held with a watcher `:14235` |
| latch `Arrive`, `Serve` | none | `pgbuf_ordered_fix_release` `storage/page_buffer.c:12444`: conditional latch when other pages are held `:12511-12520`, plain fixes skipped `:12635`, only pages that sort after the request are unfixed `:12792`, order `:12364-12418`; a read request waits behind waiters, `pgbuf_latch_bcb_upon_fix` `:6371`, `:6449-6470` |

## Bounds and assumptions

- One row and its transaction T, one other inserting transaction, one dead store record `w`, one store vacuum worker, one crash.
- At the start, `hp` has 0 free units, and `s1` and `s2` each have 0 or 2. T logs no postpone, except in the `path776-postpone` run.
- Bytes are abstract units. A DELID costs 0 units. A stamp may relocate whenever a page has room for the moved record. The code relocates only when the 8-byte DELID does not fit, which unmodeled bytes on `s1` can always arrange.
- Every log record is durable when written, as in `cubrid-verify-heap-slot-undo`. A crash that keeps a shorter durable prefix is the same as an earlier crash, and the model crashes at every point.
- An undo runs as `TRAN_UNACTIVE_ABORTED` or in crash recovery, so its room test is `total_free`. An active transaction's insert subtracts all saved space on the page. Saved space is lost in a crash.
- A failed undo stops the run (`logpb_fatal_error`), except a re-insert over a live record, which a release build performs.
- The latch model has 5 pages and 4 to 6 threads with fixed programs. Waiters are served in arrival order, readers together.

## Results

Every run matched its expectation (`python3 run.py`, exit 0, 2026-11-04). Counts are distinct states. A PASS count is the whole state space and repeats exactly. A FAIL count is where TLC stopped, and it varies a little between runs with the timing of the TLC workers. The counterexamples are the shortest ones, rechecked with one TLC worker.

| Configuration | `UndoFindsEmptySlot` | `UndoFindsRoom` | `AtomicRow` |
| --- | --- | --- | --- |
| Design with the 775 and 776 fixes (`design-fixed`) | PASS 2,638,568 | PASS 2,638,568 | PASS 2,638,568 |
| Design without 775 (`design-no775`) | FAIL 161,488 | FAIL 160,212 | FAIL 450,198 |
| Design without 776 (`design-no776`) | PASS 2,724,811 | FAIL 202,095 | PASS 2,724,811 |
| Design without either fix (`design-develop`) | FAIL 166,749 | FAIL 166,469 | FAIL 467,189 |

`AtomicRow` passes without 776 only because the failed undo stops restart before any row is judged.

| Latch configuration | `NoDeadlock` |
| --- | --- |
| Design (`latch-design`) | PASS 560,576 |

### Which Sidecar paths need which fix

| Run | Property | Result | What it shows |
| --- | --- | --- | --- |
| `path776-INSERT` | `UndoFindsRoom` | PASS 342,324 | INSERT saves no bytes, so it does not need 776. |
| `path776-UPD_REF` | `UndoFindsRoom` | FAIL 204,214 | A stamp that relocates the old value needs 776. |
| `path776-DELETE` | `UndoFindsRoom` | FAIL 101,373 | Same, for DELETE. |
| `path776-UPD_EXT` | `UndoFindsRoom` | FAIL 26,822 | An UPDATE that moves an inline value out shrinks the hot record and needs 776 (finding 1). |
| `path776-stamp-in-place` | `UndoFindsRoom` | PASS 695,564 | UPDATE and DELETE whose stamps all fit in place do not need 776. |
| `path776-postpone` | `UndoFindsRoom` | PASS 2,916,999 | A transaction that logged a postpone is safe without 776, because `LOG_COMMIT_WITH_POSTPONE` is flushed first. |
| `path775-REC_HOME` | both | PASS 226,197 | Bulk removal of a store record is redo only. |
| `path775-REC_BIGONE` | both | PASS 1,133,862 | The BIG sysop keeps the home page to its commit, and the non-reuse store never hands out the home slot. |
| `path775-REC_RELOCATION` | `UndoFindsEmptySlot`, `UndoFindsRoom` | FAIL 58,468, FAIL 54,636 | The REL sysop on a store record that a stamp relocated needs 775. |
| `path775-sidecar-writes-only` | `UndoFindsEmptySlot` | FAIL 23,967 | With no other transaction, Sidecar's own store insert takes the freed forward slot, so 775 matters for Sidecar's writes alone. |

### Broken variants

| Variant | Property | Result |
| --- | --- | --- |
| Hot write before the store writes (`broken-hot-first`) | all three | PASS 2,297,098 each. The write order protects readers (design 5.6, the lifecycle model), not recovery. A transaction's records are undone together and redone together, so their order does not change the recovered row. |
| No DELID stamp on the dropped value (`broken-skip-stamp`) | `AtomicRow` | FAIL 96,124 |
| Vacuum before the deleter's `LOG_COMMIT` (`broken-vacuum-before-commit`, the `complete_mvcc` guard removed) | `UndoFindsEmptySlot` | FAIL 136,265 |
| 775 removed, 776 removed | see the first table | FAIL |
| Multi-row insert creates the store with its batch page latched (`latch-multirow-under-latch`) | `NoDeadlock` | FAIL 8,125 |
| Multi-row insert writes an existing store with its batch page latched (`latch-multirow-store-write`) | `NoDeadlock` | FAIL 372,186 |
| Reader latches store, then hot (`latch-reader-store-first`) | `NoDeadlock` | FAIL 8,409 |
| Store cursor fixes the next store page before releasing the previous one (`latch-cursor-two-pages`) | `NoDeadlock` | FAIL 3,790 (finding 2) |

## Findings

**1. The 776 window also covers the UPDATE that moves an inline value out.** Design section 15 says that 776 reaches Sidecar only through a DELID stamp that relocates a store record, and its "Order" paragraph defers 776 past the POC because such relocation is rare at unfill 512. The model shows a common path. The shortest counterexample (`path776-UPD_EXT`) is this.

1. T inserts the new value into the store (`RVHF_MVCC_INSERT`).
2. T writes the hot record with a ref where the value was inline (`RVHF_UPDATE_NOTIFY_VACUUM`). `spage_update` shrinks the record and saves the freed bytes for T (`storage/slotted_page.c:2579-2580`).
3. T commits. `log_commit_local` runs `logtb_complete_mvcc`, then `spage_free_saved_spaces` (`transaction/log_manager.c:5278`) before `LOG_COMMIT` (`:5296`).
4. Another transaction inserts a record into those bytes on the hot page and commits, which flushes the log.
5. The server crashes before T appends `LOG_COMMIT`.
6. Restart undo of T's `RVHF_UPDATE_NOTIFY_VACUUM` needs the bytes back. `spage_update` returns `SP_DOESNT_FIT`, and `log_rv_undo_record` calls `logpb_fatal_error`.

Under AUTO, every UPDATE that pushes a row over the 4,060 B target and externalizes a value that the old version held inline takes this path, and the hot record shrinks by kilobytes. `develop` has the same window for any shrinking UPDATE, which `cubrid-verify-heap-slot-undo` leaves out (it does not model update undo). The 776 fix, freeing saved space after the commit record, removes both. The A3 kill points ("right after `COMMIT` returns") do not reach this window, because it closes before `COMMIT` returns.

**2. The store cursor must release a store page before it fixes another.** I-7 says that nobody fixes a hot page while holding a store page. It does not say that a reader or `sidecar_plan_update` holds at most one store page, and 6 Wide scan step 2 says the cursor "keeps the last store page". The hot scan itself fixes the next page before it releases the old one (`query/scan_manager.c:7909-7911`). A store cursor written the same way deadlocks with store vacuum in two threads (`latch-cursor-two-pages`).

1. Store vacuum write-latches store page `S1`, the home of a relocated store record.
2. A reader read-latches hot page `H1`.
3. The reader read-latches store page `S2` with a plain fix.
4. Vacuum asks for `S2`, the forward page. `S2` sorts after `S1`, so vacuum keeps `S1` and waits (`query/vacuum.c:1995-2003`).
5. The reader asks for `S1` with a plain fix while it holds `S2`, and waits for vacuum.

The same holds for `sidecar_plan_update` when it compares two kept values on two store pages under the hot latch. I-7 needs the rule that a plain-fixed store page is released before any other store page is fixed.

**3. The multi-row insert rule holds, and for a second reason.** Design 6 Multi-row insert keeps policy records out of the latched batch page. The model confirms that the batch page must not be held across store creation (a scan holds `HH` and waits for the batch page while the creator holds the batch page and waits for `HH`). It also shows that a store write alone under the batch page deadlocks when the store's header page sorts before the hot heap's. The batch page is held with a watcher (`transaction/locator_sr.c:14235`), so the ordered fix of a store page unfixes the batch page and fixes it again after the store page. That is store-then-hot order, against a writer that holds the hot page and plain-fixes the store page in its plan read.

## What the models do not cover

- Reader safety, MVCC visibility and the retry rule. The lifecycle model in `../lifecycle/` covers them.
- Hot heap vacuum and hot relocation. They are `develop` behavior that Sidecar does not change, and `cubrid-verify-heap-slot-undo` covers the hot heap's own slot undo. A hot record that a DELID or an UPDATE relocates has the same 776 shape as finding 1.
- The store-creation sysop's crash undo, the compatibility-level flush inside it, and the store header page. I-7 says that nobody fixes a store header page while holding a store data page, but the stock stamp of a store record within 8 B of `heap_Maxslotted_reclength` (design 5.1) calls `heap_ovf_insert` with the store home page held (`storage/heap_file.c:23435`), which plain-fixes the store header (`:6174`, `:6079`). I found no thread that holds the store header while it waits for a store data page, but neither model includes that page.
- Overflow pages: BIGONE store inserts and stamps, `RVFL_ALLOC`, and postponed page deallocation.
- Several values per row, several rows, several writers, repeated crashes, nested sysops, SA mode, HA replication, CDC, and TDE (item 774).
- Locks, file manager and disk manager latches, log latches, and the `LK_FORCE_ZERO_WAIT` page scans in `bestspace`.

A pass covers these models under these bounds, not the engine.
