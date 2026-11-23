# PR #8529 code review — CBRD-27987

Goal: review [CUBRID/cubrid#8529](https://github.com/CUBRID/cubrid/pull/8529) ("Record the commit-with-postpone record start, not its body, as the transaction tail in restart analysis").

**Result:** no confirmed defect. With this change, restart analysis records the `LOG_COMMIT_WITH_POSTPONE` record start (C) as `tail_lsa` and `tran_start_postpone_lsa`, which is the value the runtime records. Every consumer of those values was traced and behaves the same or better. Media recovery (restoredb) now gives a commit-with-postpone record the same state as restart recovery, so a transaction whose commit was decided is no longer rolled back. Both reviewers independently found one residual risk that the PR's Remarks already acknowledge. If a pre-fix binary's recovery is interrupted during its first logical postpone and the database is then restarted with the fixed binary, that restart can fail every time (R-1, source-only). It needs a decision from the owner (a small guard or a release note). It does not block merge.

## Snapshot

| Item | Value |
| --- | --- |
| Repository / PR | CUBRID/cubrid #8529, author hornetmj, base `develop` |
| Base | `505c07dde1c279ccd758cc7ef5e6d40697da59fc` |
| Head | `b4b478a7f8ef50023868a23fc13d734ce7a909c5` |
| Merge base | `505c07dde1c279ccd758cc7ef5e6d40697da59fc` |
| Comparison | `git diff 505c07dde1c279ccd758cc7ef5e6d40697da59fc b4b478a7f8ef50023868a23fc13d734ce7a909c5` |
| Patch SHA-256 | `b9585318570c0fdb8f418dca3c8c16c91bd8afa73b47a84df1ff7e7915caf3db` |
| Snapshot | 2026-11-23 15:11 KST |
| Changed paths | `src/transaction/log_recovery.c` (+14 / −13), function `log_rv_analysis_commit_with_postpone` only. No renames, deletions, submodules, or binaries |
| Develop drift | `develop` at `dae48c05e` changes no lines related to commit-with-postpone in `log_recovery.c` since the base |

## Verdict and follow-up

- **Verdict:** `no-confirmed-findings`
- **Follow-up review required:** no. R-1 and R-2 below are source-only risks. Neither is a regression for logs written by the runtime or by the fixed binary, and the PR author already describes both as accepted trade-offs. Only the owner decision on R-1 (code guard or release note) remains open, and it can be made before or after merge.
- **Merge prerequisites outside code review:** the reviewer approvals required by the gate (lht1199 has already approved), then close the empty TC draft PRs (cubrid-testcases #4195 and cubrid-testcases-private-ex #4903, 0 files each) and rerun `TC Merge Gate / Check TC PRs`.

## Confirmed findings

None.

## What changed

1. **Restart analysis records the record start.** [log_recovery.c:1321-1322](https://github.com/CUBRID/cubrid/blob/b4b478a7f8ef50023868a23fc13d734ce7a909c5/src/transaction/log_recovery.c#L1321-L1322) assigns `record_header_lsa` instead of `log_lsa`. Earlier in the function, `log_lsa` was advanced past the header to the body, which is C+32, or a position on the next page when the record straddles a page boundary. The runtime sets `tran_start_postpone_lsa = start_lsa` in `prior_lsa_start_append` ([log_append.cpp:1529](https://github.com/CUBRID/cubrid/blob/b4b478a7f8ef50023868a23fc13d734ce7a909c5/src/transaction/log_append.cpp#L1529)). The obsolete variant and the handlers for run-postpone, sysop-end, and undo-redo records also record the record start, so the fixed value matches the existing convention.
2. **Media recovery assigns the state.** Before the change, the `is_media_crash` branch truncated the log when the record was past `stop_at` and otherwise assigned no state at all. This was the shape introduced by 29624f2b7 (CBRD-24378). The stop branch now returns early ([:1304-1308](https://github.com/CUBRID/cubrid/blob/b4b478a7f8ef50023868a23fc13d734ce7a909c5/src/transaction/log_recovery.c#L1304-L1308)), and every other path sets `TRAN_UNACTIVE_COMMITTED_WITH_POSTPONE`. This is the same shape as `log_rv_analysis_complete`.

## Safety facts and effects outside the diff

| # | Fact | Pinned location (head) | Owner | Level |
| --- | --- | --- | --- | --- |
| S1 | Analysis now records the same value C as the runtime | log_append.cpp:1529, :1678 (`prev_tranlsa = tail_lsa`); log_recovery.c:1321 | R1, R2 | 2 (the author also measured it with gdb: before 872\|2608 vs 872\|2640, after equal) |
| S2 | For logs written by the runtime or the fixed binary, the backward walk in `log_recovery_abort_interrupted_sysop` ends exactly at C. A `log_rollback` with upto = C stops before reading C | log_recovery.c:4275; log_manager.c:7994 | R1, R2, coordinator | 3 |
| S3 | The debug asserts `LSA_LE (tran_start_postpone_lsa, lastparent_lsa)` now hold. Under the old value (C+32 compared with a lastparent of C) they failed, which is the assert reported in the issue | log_recovery.c:1754, :4433 | R1, R2 | 3 |
| S4 | No postpone is skipped or repeated. `posp_nxlsa` is unchanged, and no record starts inside (C, C+32], so moving the forward-scan bound from C+32 to C admits the same records | log_recovery.c:1324, :6153; log_manager.c:8506 | R1, R2 | 3 |
| S5 | Checkpoints taken during recovery save and restore a pair that matches the chain the same tdes wrote | log_page_buffer.c:7262, :7282; log_recovery.c:1970-1975 | R1 | 3 |
| S6 | The WAL flush calls on `tran_start_postpone_lsa` are unaffected, because during recovery `nxio_lsa` is already past the record at C | log_manager.c:8831-8833; oos_file.cpp:4070-4072 | R1, R2 | 3 |
| S7 | The early return in the stop branch is equivalent to the old fall-through. The caller reads only `*did_incom_recovery` and then breaks, so the NULL `log_lsa->pageid` is never used | log_recovery.c:1304-1308, :3046-3053 | R2 | 3 |
| S8 | Media recovery that passes C without stopping now reaches the same decision as restart recovery. Before the change, a log that ended after C rolled back a committed DROP TABLE, and a following `LOG_RUN_POSTPONE` left the state guessed with `tran_start_postpone_lsa` NULL, which breaks the assert at :4485 | log_recovery.c:1111-1165, :4485 | R2 | 3 (the author ran it: before 3/3 fail, after 3/3 pass) |
| S9 | HA is not affected. applylogdb does not use the analysis `tail_lsa` or `tran_start_postpone_lsa`. Replication items are appended with `LOG_COMMIT` after the postpones, and recovery appends a plain `LOG_COMMIT` | log_applier.c:7363, :7377; log_manager.c:5411, :5435 | R2 | 2-3 |
| S10 | No concurrency change. Analysis runs in one thread, and the runtime sets the value under `prior_lsa_mutex` | log_append.cpp:1525-1529 | R1 | 2 |

## Unverified risks

### R-1 (P3 if confirmed; source-only, level 3): a pre-fix recovery that was interrupted cannot be finished by the fixed binary

Both reviewers found this independently, and the coordinator rechecked the source path.

1. A crash leaves C as the transaction's last durable record.
2. A **pre-fix** binary restarts. Its analysis sets `tail_lsa` = C+32. The first postpone it runs is a logical run-postpone sysop (for example `RVFL_DEALLOC`), so the first record inside that sysop gets `prev_tranlsa` = C+32 ([log_append.cpp:1678](https://github.com/CUBRID/cubrid/blob/b4b478a7f8ef50023868a23fc13d734ce7a909c5/src/transaction/log_append.cpp#L1678)).
3. A second crash or fail-stop happens before that sysop ends. One example is `oos_reclaim_fail_stop` (oos_file.cpp:4050-4080), which fail-stops inside a run-postpone sysop.
4. The **fixed** binary restarts with `tran_start_postpone_lsa` = C. In [log_recovery.c:4275-4283](https://github.com/CUBRID/cubrid/blob/b4b478a7f8ef50023868a23fc13d734ce7a909c5/src/transaction/log_recovery.c#L4275-L4283) the walk reaches C+32, which is greater than C, and reads a "header" at that position. The bytes there are the commit record's body followed by the next header.
   - Debug build: `assert (logrec_head.trid == tdes->trid)` fires.
   - Release build: `log_rollback` also reads past C+32 (log_manager.c:7994-8013) and reaches `default:`, which calls `ER_LOG_PAGE_CORRUPTED` and `logpb_fatal_error` (:8220-8228).
   - Either way the restart fails on every retry. The old binary can still restart the database.

The PR's Remarks describe this case ("the position can be read as a record header"), but the outcome is a permanent fatal restart with the new binary, which is more severe than that wording suggests. Upgrading the binary after recovery fails is a plausible operator reaction, which makes the precondition less unlikely. **Cheapest decisive check:** build base and head in debug. Stop after `log_append_commit_postpone` for a transaction whose first postpone is `RVFL_DEALLOC`, flush, and kill -9. Restart with base under gdb, break after the first record inside the first postpone sysop, flush, and kill -9. Restart with head and expect the assert at :4283. As a control, restart with base. **Fix direction (optional):** in the abort walk, treat a link that lands strictly inside the start-postpone record (C < link < that record's `forw_lsa`) as reaching the start. Alternatively, document that a recovery the old binary left unfinished must be completed with the old binary.

### R-2 (behavior change, accepted in the PR): restoredb in the window between commit-with-postpone and the no-logging index barrier

A replay that ends between C and the `RVBT_NO_LOGGING_INDEX_DURABLE` run-postpone of a no-logging index build (CBRD-27071) now commits the transaction. Finishing its postpones then calls `log_recovery_refuse_no_logging_index_replay` ([log_recovery.c:3460](https://github.com/CUBRID/cubrid/blob/b4b478a7f8ef50023868a23fc13d734ce7a909c5/src/transaction/log_recovery.c#L3460), :3491-3496), which fatal-stops. Before the change, the transaction rolled back and the restore succeeded. The new behavior matches the refusal function's contract ("a build that never committed leaves no marker and the replay undoes it") and its message offers a way out (`-d T` earlier than C). The PR Remarks state this and say it was not executed. Owner: author. Check: run a no-logging-index loaddb, kill after `log_append_commit_postpone`, and run restoredb on both base and head.

### Notes (not regressions)

- **Pre-existing, reduced by this PR:** old logs where a pre-fix recovery completed still contain C+32 `prev_tranlsa` links, and backward log readers (flashback.c:889, :1043; log_applier.c:4879, :4960, :5500) could misread them. The PR stops producing new ones.
- **Media broken-page reset:** if the page after C cannot be fetched during media recovery, the reset (log_recovery.c:2681-2730) erases C while the transaction stays committed-with-postpone, so the transaction now commits. This matches the existing behavior for an erased `LOG_COMMIT` (:1592-1598).
- **Test gap:** the PR's `restoredb -d` test (Verification 3) uses a T before C, so it exercises only the unchanged stop branch. Two cases are not covered by tests: C's time ≤ T < `LOG_COMMIT`'s time, and a stop triggered by another transaction's record. Source tracing (S8) supports both.

## Coverage

| Path / invariant | Primary | Second | Evidence | Result |
| --- | --- | --- | --- | --- |
| `log_rv_analysis_commit_with_postpone` control flow, early return, obsolete variant, GNU indent | R2 (sonnet) | coordinator | source + GNU indent 2.2.11 `-l120 -lc120` gives zero diff on the head file | clear |
| Consumers of `tail_lsa` / `tran_start_postpone_lsa` (sysop_end, finish_sysop_postpone, finish_postpone, abort_interrupted_sysop, rollback, checkpoint, WAL flush) | R1 (opus) | R2 | source, level 3 | clear for runtime and fixed-binary logs; R-1 for pre-fix logs |
| Media recovery semantics (`stop_at`, run_postpone, complete, resetlog, no-logging index refusal) | R2 | R1 | source, level 3 | clear; R-2 behavior change |
| HA / log readers | R2 | — | source, level 2-3 | not affected |
| Concurrency | R1 | — | single-threaded analysis | N/A |
| Storage / performance | — | — | no I/O or hot-path change | N/A |
| **Shared question Q1:** can any path read a header off a record boundary, or skip or repeat a postpone, now that the LSA is the record start (including pre-fix logs)? | R1 (opus) | R2 (sonnet) | both answered independently | Both: no for runtime and fixed-binary logs; yes for pre-fix interrupted recovery (R-1) |

### Checks run

| Check | Revision | Result |
| --- | --- | --- |
| GNU indent 2.2.11 `-l120 -lc120` on `log_recovery.c` (R2) | head | pass (zero diff; a deliberately mangled line was detected) |
| `cubrid-static-check base head` | base..head | not run: the worktree had no `compile_commands.json` |
| CI `gha-ci` build (debug/release), test_medium, test_sql, test_sql_by_cci, test_shell, cppcheck, code-style, pr-style, license | head `b4b478a7f` | pass |
| CI `TC Merge Gate / Check TC PRs` | head | fail. Expected: the empty TC draft PRs are still open |
| Author's gdb-based measurements and restoredb runs (Jira attachments, 11-16 versions) | `505c07dde` / `b4b478a7f` | reported by the author: Verification 1 and 4 fail before and pass after; Verification 3 passes. The coordinator did not rerun them |

Not run by this review: any server or restoredb execution, the R-1 cross-version probe, and the R-2 no-logging restore probe.

## Budget

Bounded mode with no hard cap enforced and no usage telemetry. Two reviewer agents ran for about 25 minutes each: R1 recovery/concurrency on opus, and R2 systems/media/HA on sonnet. Both stayed within their targets. Neither could write its report file, so each returned it inline and the coordinator saved it. There were no retries and no extra agents. Coordinator usage was not measured.
