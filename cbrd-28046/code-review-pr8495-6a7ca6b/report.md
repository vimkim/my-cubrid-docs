# Code review: CUBRID/cubrid#8495 (CBRD-28046)

**Goal.** Check that a commit with postpone actions can wait for one log flush instead of two without losing durability or atomicity.

**Most consequential result.** No confirmed defect. The guard for `RVHF_LOB_REMOVE_DIR` closes the one data-loss path that a plain flush removal opens; a crash test reproduces the loss without the guard and shows the fix. A known LOB data-loss defect, CBRD-27964 (an old LOB file is deleted without a log record before the commit is durable), keeps its window open longer for a transaction with postpone actions (R-1); it is fixed in CBRD-27964, not here.

## Verdict and follow-up

- **Verdict:** `incomplete`. No confirmed findings; R-3 is a new reachable combination without execution evidence.
- **Follow-up review required:** yes. Run the R-3 check before merge. R-1 is tracked in CBRD-27964 and R-2 is pre-existing; neither blocks this PR.

Revision 2026-11-11: R-1 was restated after reading CBRD-27964 (see below).

## Snapshot

| Item | Value |
|---|---|
| PR | https://github.com/CUBRID/cubrid/pull/8495 |
| Base (develop) | `2d1513a8afe6c843388e916fcdf34483b78a2051` |
| Merge base | `2d1513a8afe6c843388e916fcdf34483b78a2051` |
| Head | `6a7ca6b4a89e5dd96bfea81b9f6655893641b9a7` |
| Comparison | `git diff 2d1513a8afe6c843388e916fcdf34483b78a2051 6a7ca6b4a89e5dd96bfea81b9f6655893641b9a7` (patch sha256 `6d30317c5ef1383d0c6f9f57ec0aaa9819d53621b2e6a1761c8d059e33daf12d`) |
| Changed paths | `src/transaction/log_manager.c` (`log_append_commit_postpone`), `src/storage/heap_file.c` (`heap_rv_lob_remove_dir`) |

## Confirmed findings

None.

## Changed behavior and safety facts

| Effect | Safety fact | Source | Evidence |
|---|---|---|---|
| A commit no longer waits for `LOG_COMMIT_WITH_POSTPONE` (CWP) to be durable before it runs postpone actions. | The log reaches disk as an LSA prefix, and a data page reaches disk only after its log (WAL). Every logged postpone effect has an LSA after CWP, so a durable effect implies a durable CWP. | [log_manager.c](https://github.com/CUBRID/cubrid/blob/6a7ca6b4a89e5dd96bfea81b9f6655893641b9a7/src/transaction/log_manager.c#L4462-L4480), `logpb_need_wal` in log_page_buffer.c | Level 4: 24 SIGKILLs during a 300-table DROP commit; 0 partial commits, 0 lost acknowledged commits, `checkdb` passed 24/24 (19 rolled back, 5 committed). |
| Crash before CWP is durable: the transaction is undone; the client had no acknowledgement. | The client reply still waits for the `LOG_COMMIT` flush (`log_change_tran_as_completed`). | log_manager.c | Level 3 (all three reviewers); level 4 for the DROP workload above. |
| `log_do_postpone` reads postpone records that may not be flushed. | `logpb_fetch_page` appends the prior list under LOG_CS before reading. | log_page_buffer.c:1791-1805 | Level 3. |
| Checkpoint taken while postpones run. | The end-checkpoint record follows CWP and is flushed before `hdr.chkpt_lsa` moves. | log_page_buffer.c checkpoint | Level 3 (recovery). |
| `RVHF_LOB_REMOVE_DIR` removes LOB files from the file system during postpone. | The new guard flushes the log up to `tran_start_postpone_lsa` (CWP start) with `logpb_flush_log_for_wal`, which drains the prior list and fsyncs, before the unlink. In undo, recovery, or a system tdes the LSA is NULL or already durable and nothing flushes. | [heap_file.c](https://github.com/CUBRID/cubrid/blob/6a7ca6b4a89e5dd96bfea81b9f6655893641b9a7/src/storage/heap_file.c#L28680-L28690), log_append.cpp:1496 | Level 5: gdb stop after `fileio_lob_remove_matching_dir` returns, then SIGKILL. With the guard the table is dropped after restart. Without the guard the table and 5 rows come back with every `BLOB_LENGTH` NULL. |
| HA, CDC, flashback | Replication records and `LOG_COMMIT` are appended together after the postpone run; copylogdb ships flushed pages only; CDC and flashback do not read CWP. The CBRD-20019 window narrows; CBRD-28034 ordering is unchanged. | log_manager.c `log_append_repl_info_and_commit_log` | Level 3 (HA). |
| 2PC | `log_append_commit_postpone` has one caller (`log_tran_do_postpone` from `log_commit_local`); the 2PC decision is force-flushed before the local commit. | log_2pc.c | Level 3 (HA). The participant path was not traced by the recovery reviewer. |
| `log_async_commit=yes` | The removed flush did not wait under async commit, so the state "postpones ran, CWP not durable" already existed there. The LOB guard now protects LOB removal under async commit too. | log_page_buffer.c `logpb_flush_pages` | Level 3. |
| SA_MODE | `logpb_flush_pages` flushes directly; one direct flush per postpone commit is saved; heap_file.c compiles in SA and SERVER modes. | | Level 4 for compilation (debug compile of heap_file.c, both modes, 0 warnings). |
| Performance | One group-commit wait per postpone commit instead of two. LOB DDL still pays two flushes. | | Measured on the CBRD-27781 base with the same one-line removal: `fdatasync` 6006 to 3006 for 3000 single-row OOS UPDATE commits (see CBRD-28046). Not measured on develop. |

## Unverified risks

| ID | Risk | Attribution | Owner | Decisive check |
|---|---|---|---|---|
| R-1 | The reviewer's first scenario was vacuum deleting `RVES_NOTIFY_VACUUM` LOB files (vacuum.c:3572) before the commit is durable. CBRD-27964 executed that path and showed it cannot cause loss: those files were created by the same transaction, so no row points to them after a rollback. The real loss path is CBRD-27964 itself: `tx_lob_locator_clear` deletes a LOB file committed by an earlier transaction with `es_delete_file` and no log (transaction_transient.cpp:452) before the commit record. A crash before the commit is durable leaves the row with the old locator and no file. | Pre-existing (CBRD-27964, Confirmed). The delete happens before CWP, so this PR does not cause it, but for a transaction with postpone actions the window now lasts until the LOG_COMMIT flush instead of the CWP flush (source argument, not executed). | CBRD-27964 | Fix in CBRD-27964; when its delete waits for a durable commit, this window disappears. |
| R-2 | `logpb_flush_pages` waits while `nxio_lsa < flush_lsa` (log_page_buffer.c:4144), but `logpb_need_wal` uses `<=`. When the log was fully flushed just before a commit record was appended, `nxio_lsa` can equal that record's start and the commit may return before the record is durable. | Pre-existing, base identical. This PR now relies on the same wait for the only durability barrier of a postpone commit. | systems, recovery | Instrumented run that records `nxio_lsa` and the commit start LSA at return. |
| R-3 | `file_destroy` discards the file's dirty pages (`pgbuf_discard_pages_of_sectors`, file_manager.c:4201). If CWP is then lost, the transaction is undone and the file returns with possibly older disk pages. The source argument says redo replays the discarded changes because the redo start cannot pass CWP. | New reachable combination. | recovery | `FI_TEST_FILE_MANAGER_DESTROY_HOLD` plus a checkpoint, then crash and `checkdb`. The 24-kill DROP test covers this path without a forced checkpoint. |

## Dropped candidates

- systems C1 (no-logging index build reuses sectors freed by a postpone before CWP is durable): disproven by source. The first write of a no-redo page goes through `pgbuf_flush_with_wal` with the page's allocation LSA, which follows the sector release and therefore CWP (btree_load.c:2649-2690). Level 3.
- HA note "LOG_CS_ENTER inside a postpone action is unsafe for a future caller that holds a page latch": no current caller holds a latch (`RVHF_LOB_REMOVE_DIR` is a manual logical postpone with a NULL page). Kept as a maintenance note.
- Duplicate: three reviewers independently raised the page-discard question; merged into R-3. Two raised the `nxio_lsa` comparison; merged into R-2.

## Coverage and verification

See [coverage.md](coverage.md). Shared question Q1 (any non-WAL effect in the commit window besides `RVHF_LOB_REMOVE_DIR`): recovery (opus) and HA (sonnet) answered independently. Both found none among direct postpone actions; recovery added the indirect vacuum path R-1.

Checks run by the coordinator:

| Check | Revision / config | Result |
|---|---|---|
| [`../test/postpone_crash.sh`](../test/postpone_crash.sh) 24 iterations, NTAB=300, kill 3-80 ms after the last DROP | head, release_gcc | pass (see [`../test/postpone-crash-results.csv`](../test/postpone-crash-results.csv)) |
| [`../test/lob_crash.sh`](../test/lob_crash.sh) (gdb `finish` then kill) | head, release_gcc | table dropped, 0 LOB files, `checkdb` 0 |
| Same, guard removed | head with heap_file.c reverted, release_gcc | table back, 5 rows, `BLOB_LENGTH` NULL: data loss |
| Same, kill at function entry | head, release_gcc | table dropped; 5 LOB files remain after recovery (not compared with base) |
| Release and debug builds | head | pass |
| gha-ci `/run all` | head | running at report time (run 43020466468) |

Not run: ctest, debug-build crash tests (CBRD-27987 asserts first), 2PC participant crash test, the R-2/R-3 checks. R-1 relies on the executed analysis in CBRD-27964.

## Budget

Bounded mode, no hard cap enforced. Three reviewers with a target of about 40 tool calls each: recovery 36, HA 41, systems 35 (reported by the harness). Coordinator replay used the crash scripts above. Per-agent token usage is reported by the harness only as totals; no allowance telemetry was available.
