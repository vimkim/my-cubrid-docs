# Sidecar code-level check (A7)

This directory checks the Sidecar POC code on branch `sidecar`, not the design text. `check.py` reads the engine source, finds the shape that each model assumes, and runs the TLA+ model checker TLC on three small models. The design models in `../lifecycle/` and `../recovery/` check the design. This check asks whether the code that was written keeps the same rules: the order of the store writes and the hot write in `sidecar_apply_plan`, the release-and-relocate step, the store read of a relocated store record, the committed fetch with its retry and lock fallback, and the store cursor's page holds.

The verify skill `cubrid-verify-sidecar-code` (in `my-cubrid-formal-verification-skills`) tells an agent when to run it and how to read a result. Read every result, failing or passing, with the `/statechart` skill on the `<Module>.tla` and `<Property>.cfg` of that run's folder.

Last modified: 2026-11-11, Asia/Seoul. Sync commit `ac714e909e` on branch `sidecar` (the store-read fix `b1267b2055` cherry-picked after the A4 test hooks; `check.py` exits 0 there, measured).

## Run

From the Sidecar worktree:

```bash
python3 /home/vimkim/gh/my-cubrid-docs/sidecar/model/code/check.py
```

- `--rev <commit>` checks a commit instead of the work tree, and `--repo <path>` another checkout. A directory that is not a Git checkout works too, for a scratch copy of `src/`. It then skips the comparison with the sync commit.
- `--set KEY=VALUE` tries a shape that the code does not have, for example `--set fwd_slot_reuse=no`. The output marks it `HYPOTHETICAL`. Keys and values are in `SHAPE_DOMAINS` in `check.py`.
- `--only TEXT` runs the properties whose name contains `TEXT`.
- It needs Python 3 and Java 8 or later. TLA+ tools 1.7.4 are read from `~/.cache/tlaplus/` and downloaded with a SHA-256 check if missing (`TLA2TOOLS_JAR` overrides).
- A run takes about 9 minutes of wall time and 85 CPU minutes (measured on 2026-11-11 at `b1267b2055`, 4 parallel TLC runs of 8 workers each, on a host with load about 120); `AbsentOnlyIfRemoved` with eight free forward slots is most of it.

Exit status: `0` all pass or only known findings; `1` a new finding or a hypothetical failure; `2` out of sync or a tool error; `3` as `0`, but covered code changed since the sync commit.

| Result | Meaning |
| --- | --- |
| `PASS` | No order of steps in the model breaks the property, with the causes in `with` removed. |
| `KNOWN FINDING <id>` | The property fails, the code has the finding's shape (`when` in `known_findings.json`), and the counterexample contains the finding's actions in order (`signature`). The script then removes the cause (`neutralize`) and runs again. |
| `NEW FINDING` | A failure that no known finding explains. The numbered steps are a counterexample in the code's words. |
| `OUT OF SYNC` | The code lost a shape that a model needs. Update the model first. |
| `MODEL OR TOOL ERROR` | TLC failed. Read the `.out` file the script names. |

## Properties

| Model | Property | Plain statement | Harm if broken |
| --- | --- | --- | --- |
| `SidecarStoreRead` | `ReadReturnsOwnValue` | The bytes that a store read returns for a ref are that ref's value. | A query returns another row's value with no error. |
| `SidecarStoreRead` | `AbsentOnlyIfRemoved` | A store read reports a record absent only if vacuum removed it. | A protected reader or a lock holder fails with `ER_SIDECAR_DANGLING_REF` for a live row. |
| `SidecarRowWrite` | `LatchedReaderFinds` | A dirty or NULL-snapshot reader that holds the hot page finds every store record that the version it reads names. | The reader fails with `ER_SIDECAR_DANGLING_REF`. |
| `SidecarRowWrite` | `StoreMatchesRow` | When every writer is done, the store records with no DELID are exactly the ones the current version names. | An orphan store record that vacuum never removes, or a dropped value that stays live. |
| `SidecarRowWrite` | `FetchNoLostRow` | A committed fetch reports the row missing only after a DELETE of it committed. | `xlocator_fetch` reports a live row as deleted. |
| `SidecarRowWrite` | `FetchNoError` | A committed fetch never ends in an error, also when its retries run out. | `xlocator_fetch` fails with `ER_SIDECAR_RESOLVE_RETRY` or `ER_SIDECAR_DANGLING_REF` for a live row. |
| `SidecarCodeLatch` | `NoDeadlock` | No reachable state has a cycle of page latch waits. | Threads hang; CUBRID has no latch deadlock detector. |

## Results at the sync commit

Measured on 2026-11-11 at `b1267b2055`. Counts are distinct states.

| Property | Bounds | Result |
| --- | --- | --- |
| `ReadReturnsOwnValue` | A stamped up to 2 times and B once, each in place or relocated, rollback, commit, vacuum; three free forward slots | `PASS` 9,577 |
| `AbsentOnlyIfRemoved` | A stamped and rolled back up to 8 times (the old `SIDECAR_REREAD_BOUND`), eight free forward slots | `PASS` 24,842,792 (4 min) |
| `LatchedReaderFinds` | 3 writers, each UPDATE or DELETE, each commit or rollback; store vacuum | `PASS` 372,627 |
| `StoreMatchesRow` | as above | `PASS` 372,627 |
| `FetchNoLostRow` | as above, with one committed fetch | `PASS` 372,627 |
| `FetchNoError` | as above | `PASS` 372,627 |
| `FetchNoError` | 4 UPDATEs at the code's bound of 3: the retries run out and the lock fallback reads | `PASS` 3,095,797 |
| `FetchNoError` | the bound reduced to 1 with 4 UPDATEs: the fallback, then a second visible read | `PASS` 2,962,537 |
| `NoDeadlock` | a cursor scan over two hot pages with a routine call and values on both store pages, a large-column UPDATE, store vacuum of a relocated store record, the routine's worker | `PASS` 84,284 |

At `0026f92098`, before the fix, the two store read properties failed as the findings below; the other seven results were the same.

## Findings

Both findings were fixed by `b1267b2055` and are no longer in `known_findings.json`. Both were replayed on a debug server before the fix and pass after it (measured; scripts and outputs in `.scratch/sidecar/p3-storeread/replay/`). The replay fills a store page with in-place stamps until under 8 B are free, so the next stamp relocates, and holds the reader between its page fixes with the debug fault injections 700020 and 700021.

**1. A store read could return another store record's value** (`store-read-forward-aba`, property `ReadReturnsOwnValue`). `sidecar_read_store_record_at` read a relocated store record A in three fixes and rechecked only that A's home still forwarded to the same slot F. The undo of a newhome insert (`heap_rv_undo_insert`, `spage_delete_for_recovery`) and store vacuum of a relocated record (`vacuum_heap_record`) made F reusable, so between the fixes A's stamp could roll back, a stamp of B could relocate B into F, the read could copy B, B could leave F and a new stamp of A could relocate A into F again. The recheck matched and B's value came back as A's. Replay before the fix: the read of row 1 returned row 2's value, with no error, in two runs.

**2. The reread bound could be exhausted for a live record** (`store-read-reread-bound`, property `AbsentOnlyIfRemoved`). Each relocate-and-rollback of A during the read cost one of `SIDECAR_REREAD_BOUND` (8) rounds, after which the read reported A absent. Replay before the fix: after 8 such writers a protected reader got `ER_SIDECAR_DANGLING_REF` for live row 1.

**The fix.** A store slot holds one store record in its life. On a store page, `heap_rv_undo_insert` deletes the slot with `spage_delete`, which leaves it `REC_MARKDELETED`, and `vacuum_heap_record` vacuums the forward slot without reuse, as store vacuum already did for home slots. A `REC_NEWHOME` record in the slot a home forwarded to is then that home's record, so the read returns it with no second home fix. A forward slot without it lost the record to a rollback or vacuum, which both change the home first, so the read starts over with no bound; each further round needs another writer that stamps and rolls back A. A home that forwards again to the slot that held nothing is a broken store, and the read reports it absent. The model shows that the non-reuse store is what makes both properties hold: with `fwd_slot_reuse=yes` and the new read both fail, and a bound on the new read fails `AbsentOnlyIfRemoved` again.

## What each model action stands for

Lines are at the sync commit `0026f92098`.

| Model action | Code |
| --- | --- |
| `SidecarStoreRead` `R1`, `R2` | `sidecar_read_store_record_at` (`storage/sidecar.cpp:700`): unbounded loop `:706`, home fix and type test, REC_HOME copy, absent when the home forwards to the slot that missed `:751`, forward fix and REC_NEWHOME copy returned `:765-772`, the missed slot kept `:778`. `R3`, `R3Skip` and a nonzero `RereadBound` model the code before the fix and broken variants |
| `StampInPlace`, `StampNewHome`, `StampHome` | `sidecar_stamp_values` (`sidecar.cpp:1562`) calls `heap_delete_logical`, then `heap_delete_home` (`storage/heap_file.c:23876`): `spage_is_updatable` or `REC_NEWHOME` and `heap_insert_newhome` (`:24068`) with the home page held, then the home becomes REC_RELOCATION |
| `Rollback`, `UndoStep` | `log_abort_local`, `log_rollback` in reverse LSA order; the newhome insert's undo `heap_rv_undo_insert` (`heap_file.c:17985`), which leaves a store slot `REC_MARKDELETED` with `spage_delete` (`:17999`) and other slots reusable with `spage_delete_for_recovery` |
| `VacuumHome`, `VacuumForward` | `vacuum_heap_record` (`query/vacuum.c:2375`): forward slot vacuumed without reuse on a store page `:2432`, forward page kept until `log_sysop_commit` and unfixed `:2450` (775), so one step |
| `SidecarRowWrite` `WLock` | the row's X lock that the locator takes before `heap_update_logical` and `heap_delete_logical` (assumed, not read from the code) |
| `WPlan` | `heap_get_record_location` after `relocate:` (`heap_file.c:25917`, `:25664`), then `heap_sidecar_plan` (`:25173`) under the hot latch: `sidecar_plan_update_body` (`sidecar.cpp:1198`) or `sidecar_plan_delete_body` (`:1438`) |
| `WInsert` | `heap_unfix_watchers` (`heap_file.c:25964`, `:25700`), `sidecar_apply_plan` (`sidecar.cpp:1710`), `sidecar_insert_values` (`:1492`, called `:1660`) |
| `WStamp` | `sidecar_stamp_values` (`sidecar.cpp:1562`, called `:1669`) |
| `WRelocate` | `goto relocate` (`heap_file.c:25971`, `:25706`); the plan hook returns at once on `SIDECAR_PLAN_APPLIED` (`sidecar.cpp:1202`, `:1441`), set at `:1704` |
| `WHot` | the hot write after relocate: `heap_update_home`, `heap_update_relocation` or `heap_update_bigone` (`heap_file.c:26026` and the next cases), `heap_delete_home`, `heap_delete_relocation` or `heap_delete_bigone` (`:25737` and the next cases); for INSERT, `sidecar_apply_plan` (`:25378`) precedes `heap_get_insert_location_with_lock` (`:25445`) |
| `WCommit`, `WAbort`, `WUndo`, `WAbortEnd` | `log_commit_local`; `log_abort_local` with undo in reverse LSA order (a store insert's undo removes the record, a stamp's undo clears the DELID, the hot write's undo restores the old version) |
| `Vacuum` | store vacuum removes a store record once its stamper committed |
| `L1`, `L2` | `SIDECAR_READER_LATCHED` (`sidecar_classify`): `heap_get_visible_version_internal` ends in `heap_sidecar_fetch_exit` (`heap_file.c:27850`) with the hot page still fixed; `sidecar_on_fetch_body` (`sidecar.cpp:2360`) reads each ref; `sidecar_on_absent` (`:2315`) |
| `C1`, `C2` | `xlocator_fetch` with the committed snapshot: heap path under the hot latch, log path from the log; `sidecar_on_absent`: committed DELID test `:2320`, `S_SIDECAR_RETRY` `:2331`, `S_SIDECAR_LOCK_NEEDED` `:2343`; the reread in `heap_sidecar_fetch_exit` |
| `F1`, `F2` | `locator_lock_and_return_object` (`transaction/locator_sr.c:2327`, call `:2345`) calls `sidecar_fetch_locked` (`sidecar.cpp:2473`): S lock `:2481`, `heap_get_last_version` `:2488` (`heap_file.c:27997`, `sidecar_on_fetch` as `SIDECAR_READER_HOLDER`), committed-snapshot test, default branch to `heap_get_visible_version`, unlock `:2525` |
| `SidecarCodeLatch` reader program | the store cursor: kept page `sidecar_lazy_note` (`sidecar.cpp:2061`); release before a routine call `cubpl::executor::execute` (`sp/pl_executor.cpp:288`); before a hot fix `heap_scan_pb_latch_and_fetch` (`heap_file.c:1058`), `heap_prepare_object_page` (`:28082`), `scan_batch_next_page` (`query/scan_manager.c:7902`); before the next store page `sidecar_cursor_unfix` in `sidecar_cursor_read_value` (`sidecar.cpp:2261-2262`); last resort in `pgbuf_fix_release` (`storage/page_buffer.c:2235-2246`) |
| `SidecarCodeLatch` writer and worker programs | `heap_update_logical` as above; `sidecar_apply_plan_body` refuses a store write with a page held (`sidecar.cpp:1604`) |
| `SidecarCodeLatch` latch rules | copied from `../recovery/SidecarLatch.tla`: `pgbuf_ordered_fix_release` conditional latch and refix order, `pgbuf_latch_bcb_upon_fix` grant order |

## Shape keys

`check.py` prints each key with the line that decides it. A key that the code no longer shows at all, for example a missing call, stops the run with `OUT OF SYNC`. A key that the code shows in its other form runs the model with that form.

| Key | Code value | Model constant |
| --- | --- | --- |
| `home_recheck`, `fwd_type_check`, `reread_bound` | `on_miss`, yes, `none` (before the fix: `always`, yes, 8) | `HomeRecheck`, `FwdTypeCheck`, `RereadBound` (0 for none) |
| `fwd_slot_reuse` | no: `heap_rv_undo_insert` and `vacuum_heap_record` keep a freed store slot (before the fix: yes) | `FwdSlotReuse` |
| `vacuum_fwd_held` | yes (775) | `VacuumAtomic` |
| `stamp_relocates` | yes | required; without it the store read model does not apply |
| `write_order` | `store_then_hot` | `WriteOrder` |
| `plan_once` | yes | `PlanOnce` |
| `row_lock` | yes (assumed) | `RowLock` |
| `retry_bound`, `on_absent`, `delid_test` | 3, `retry`, yes | `RetryBound`, `OnAbsent`, `DelidTest` |
| `fallback`, `fallback_lock` | yes, `s_lock_around_read` | `Fallback`, `FallbackLock` |
| `rel_before_call`, `rel_before_hot_fix`, `rel_before_store_fix`, `fix_guard`, `apply_no_page` | all yes | `RelBeforeCall`, `RelBeforeHotFix`, `RelBeforeStoreFix`, `FixGuard`, `ApplyNoPage` |
| `model.stamp_cycles` | `reread_bound` | `MaxStampsA` of `AbsentOnlyIfRemoved`, 8 when the code has no bound, with as many free forward slots (`FwdSlots`); a model bound, not code |

## Evidence that the check can fail

| Variant | Property | Result (measured 2026-11-11) |
| --- | --- | --- |
| `--set fwd_slot_reuse=yes` | `ReadReturnsOwnValue`, `AbsentOnlyIfRemoved` | both fail (1,076 and 16,419) |
| `--set reread_bound=3` | `AbsentOnlyIfRemoved` | fails (21,607); `ReadReturnsOwnValue` passes (9,865). `reread_bound=8` with 8 cycles did not finish in 25 min |
| `--set home_recheck=always --set fwd_slot_reuse=yes --set reread_bound=3`, the code before the fix | `ReadReturnsOwnValue`, `AbsentOnlyIfRemoved` | both fail (10,997 and 34,414) |
| `--set home_recheck=no` | `ReadReturnsOwnValue` | passes (11,221): with a non-reuse store the home recheck is not needed, which is why the fix drops it |
| `WriteOrder = "hot_then_store"` | `LatchedReaderFinds` | fails (465) |
| `PlanOnce = FALSE` | `StoreMatchesRow` | fails (4,551) |
| `RowLock = FALSE` | `StoreMatchesRow` | fails (20,717) |
| `DelidTest = FALSE` | `LatchedReaderFinds` | fails (1,845) |
| `OnAbsent = "doesnt_exist"` | `FetchNoLostRow` | fails (3,893) |
| `Fallback = FALSE`, bound 1 | `FetchNoError` | fails (13,637) |
| `FallbackLock = "none"`, bound 1, 4 UPDATEs | `FetchNoError` | fails (3,058,656) |
| `RelBeforeCall = FALSE` | `NoDeadlock` | fails (2,515) |
| `RelBeforeHotFix` and `FixGuard` FALSE | `NoDeadlock` | fails (51,615) |
| `RelBeforeStoreFix` and `FixGuard` FALSE | `NoDeadlock` | fails (40,465) |
| `ApplyNoPage = FALSE` | `NoDeadlock` | fails (13,387) |
| Scratch copy of `src/` at `41d7901ce3` with four edits: the APPLIED early return removed from `sidecar_plan_update_body`; `lock_object` removed from `sidecar_fetch_locked`; the home recheck of `sidecar_read_store_record_at` replaced by a return; `sidecar_cursor_release` removed from `cubpl::executor::execute` | `ReadReturnsOwnValue`, `AbsentOnlyIfRemoved`, `StoreMatchesRow`, `FetchNoError` (bound 1), `NoDeadlock` | each `NEW FINDING`, exit 1 |
| The same copy without the edits (`--rev 41d7901ce3`) | all | exit 0, the results above |

The `FetchNoError` run at the code's bound of 3 does not catch a fallback without the S lock: the second visible read would need 4 more commits than the model's 4 writers. The bound-1 run catches it.

## Scope and assumptions

Verified: every interleaving of the steps above, under the bounds in the results table.

Assumptions:

- Each model step is one page latch in the code. A stamp holds the home page from its newhome insert to the home change. Store vacuum of a relocated record is one step because 775 keeps the forward page until the sysop ends. With `vacuum_fwd_held=no` the model splits it.
- Two store records of one class can have the same attribute and length, so `sidecar_store_value` does not tell them apart.
- Writers take the row's X lock before the heap call, and C's S lock waits for it. The lock manager is not read from the code.
- Store vacuum removes a store record only after its stamper committed. The recovery model checks the commit-record guard (`broken-vacuum-before-commit`).
- One large column per row, so a version names one store record.
- Every log record is durable when written. Crashes are in the recovery model, not here.

Not covered: crash and restart (see `../recovery/` and the A3 kill tests), REC_BIGONE store records, the lazy read and its trid backstop (`../lifecycle/`), parallel scans and the page batch, several large columns, INSERT's store creation, the latch order of locks, file and disk manager latches, replication, and liveness of the fallback's lock wait. `row_lock` is assumed.

## Update the verification when a change is intended

1. If only line numbers moved, `check.py` reads them, and nothing needs an update.
2. If the code has a new shape (`OUT OF SYNC`, or a new step in a covered function), change the model and `extract_shape` in `check.py` together. Keep each action one latch step of the code, with names from the code.
3. Show that each changed property can still fail: a `--set` value or a scratch copy of `src/` that breaks it.
4. Update `known_findings.json` when a finding is fixed, reported (`ticket`), or accepted.
5. Move `sync-commit` forward only after you have read the covered functions at the new commit and confirmed that the models describe them. For finer help, use `/maintain-formal-verification-skill`.

<!-- coverage:begin -->
```text
sync-commit: ac714e909e922cf2f962041bb60e898fbe91e0c0
covers:
  src/storage/sidecar.cpp: sidecar_read_store_record_at, sidecar_apply_plan, sidecar_apply_plan_body, sidecar_insert_values, sidecar_stamp_values, sidecar_plan_update_body, sidecar_plan_delete_body, sidecar_on_absent, sidecar_on_fetch_body, sidecar_fetch_locked, sidecar_cursor_read_value, sidecar_cursor_unfix, sidecar_cursor_release, sidecar_lazy_note
  src/storage/heap_file.c: heap_update_logical, heap_delete_logical, heap_insert_logical, heap_sidecar_plan, heap_sidecar_fetch_exit, heap_get_last_version, heap_delete_home, heap_scan_pb_latch_and_fetch, heap_prepare_object_page, heap_rv_undo_insert
  src/storage/slotted_page.c: spage_delete_for_recovery
  src/query/vacuum.c: vacuum_heap_record
  src/query/scan_manager.c: scan_batch_next_page
  src/transaction/locator_sr.c: locator_lock_and_return_object
  src/storage/page_buffer.c: pgbuf_fix_release
```
<!-- coverage:end -->
