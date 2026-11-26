# Code review — CUBRID/cubrid#8674 + cubrid-testcases-private-ex#5070 (CBRD-28200)

**Goal.** Check "[CBRD-28200] Keep the unique statistics of a prepared transaction across a restart" in depth. Scope:
- Whether 2PC unique-statistics deltas survive a crash and restart, applied exactly once.
- Invariants of log redo/undo, checkpoint and recovery.
- Locking and concurrency edge cases, and resource and error handling.
- Whether TC PR #5070 tests the prepared-transaction restart scenario adequately.

**Most consequential result.** The engine change has no confirmed defect.
- **Exactly-once:** two reviewers on different models (opus, sonnet) independently concluded that a commit decision applies each delta exactly once at every crash point. The only exception is a TM rollback after an interrupted commit, which violates the protocol and which the PR documents.
- **The new TC catches the bug.** It passes on the PR head, fails on the base as the bug predicts, and passed in the PR's CI. It needs an engine built with `SUPPORT_XA=true`.

| Item | Value |
|---|---|
| Engine PR | https://github.com/CUBRID/cubrid/pull/8674 (author hornetmj; reviewers lht1199, vimkim) |
| base / head / merge-base | `051a19c358fd13bef2cdd4110f5e4443e81c5757` / `aff1baed6394b547cca4739c09d3672de97a4b90` / `051a19c358fd13bef2cdd4110f5e4443e81c5757` |
| Comparison | `git diff 051a19c358fd13bef2cdd4110f5e4443e81c5757 aff1baed6394b547cca4739c09d3672de97a4b90` (sha256 `76521de4…8ea66f`); 7 files under `src/transaction/` (`log_2pc.c`, `log_impl.h`, `log_manager.c`, `log_recovery.c`, `log_tran_table.c`, `recovery.c`, `recovery.h`), +447/−11 |
| TC PR | cubrid-testcases-private-ex#5070 (private), base `074ee8eea5b336b8df846f6ccad5dc89a60d789f`, head `c82181e2d880044defbceec1a3809060de09c957`; 2 new files under `shell/_06_issues/_26_2h/cbrd_28200/cases/` (+396) |
| Public TC PR | cubrid-testcases#4372, no changed files |
| Snapshot | 2026-11-26 KST. Base and head rechecked before publication: unchanged |

## Verdict and follow-up

- **Verdict: `no-confirmed-findings`.** Recommendation: **APPROVE**, with the non-blocking comments below.
- **Follow-up review required: no.** All suggestions are optional. A code or TC change in response needs a delta review.
- **Merge-gate note:** the PR is not vimkim's, so merging belongs to the author. The TC Merge Gate is still open (both TC PRs open).

## What changed

- **Prepare:** `log_2pc_prepare_global_tran` calls the new `logtb_tran_log_unique_stats_for_2pc`. It packs the transaction's unique-statistics hash into a new redo-only, pageless record, `RVBT_2PC_UNIQUE_STATS` (rcvindex 146). The record is appended directly before `LOG_2PC_PREPARE` and before the shared locks are released. If the append fails, the prepare fails.
- **Restart:** the new `log_recovery_2pc_restore_unique_stats` runs at the end of `log_recovery_redo` for each in-doubt (`TRAN_UNACTIVE_2PC_PREPARE`) transaction:
  - It walks `prev_tranlsa` from `tail_lsa` back to the `LOG_2PC_PREPARE` record.
  - It rebuilds the hash from the 146 record just before it.
  - It zeroes the indexes whose `RVBT_LOG_GLOBAL_UNIQUE_STATS_COMMIT` the interrupted commit already logged, because redo already applied those.
- **Commit after prepare:** the new `LOG_ISTRAN_LOGGABLE` lets `TRAN_UNACTIVE_2PC_PREPARE` and `TRAN_UNACTIVE_2PC_COMMIT_DECISION` log at the four undo/redo append gates in `log_manager.c`. In those states, `logtb_update_global_unique_stats_by_delta` writes the stats-commit record redo-only. Before the fix, a prepared transaction's commit dropped that record (problem 2 in the PR).

## Safety facts

| # | Fact | Evidence | Level |
|---|---|---|---|
| F1 | No record of the transaction is appended between 146 and `LOG_2PC_PREPARE`: the lock release logs nothing, and the prepare is not inside a system operation. The restore finds 146 as the `prev_tranlsa` of the prepare record. | Source (`log_2pc.c` prepare path) | 3 |
| F2 | The restore pass runs after parallel redo has joined (`log_recovery.c:4467`), so the global statistics already contain every redone stats-commit record. | Source | 3 |
| F3 | Every zeroed index already has its delta in the global statistics, either replayed by redo or written to the B-tree root header by a checkpoint. The zero set comes from walking the log chain and does not depend on the redo start point. | Source, crash-point table below | 3 |
| F4 | Archive retention adds no new risk. The walk reads a subset of the log that `log_recovery_2pc_restore_prev_versions` and `log_2pc_recovery_analysis_info` already read. A page that cannot be read stops restart, as elsewhere in recovery. | Source | 3 |
| F5 | The statistics chunks and the `mht` come from global allocations, not per-thread private heaps. So the hash the recovery thread builds can be freed by the worker that later decides the branch. The pack buffer is the only `db_private_alloc`, and it is freed in the same function. | Source | 2 |
| F6 | Pack/unpack: 40-byte entries, big-endian, with zeroed padding. A standalone probe with the real `OR_*` macros round-trips 1000 entries, and its 13 validation edge cases (negative count, `INT_MAX`, short length) behave correctly. `log_rv_get_unzip_log_data` resizes and decompresses records larger than `IO_PAGESIZE`. | Probe + source | 4 |
| F7 | `RV_fun` has 147 entries with entry *i* = rcvindex *i*. Inside the same version, nothing indexes the table with 146 except redo. Its redo function is a no-op. Rollback, restart undo, vacuum, the HA applier, copylogdb, CDC and flashback ignore the record or compare against other specific rcvindex values. | Script over source + source | 3–4 |
| F8 | On a protocol-following path, the widened gates newly log only two record types: `RVBT_LOG_GLOBAL_UNIQUE_STATS_COMMIT` (redo-only, `log_tran_table.c:5775`) and `RVES_NOTIFY_VACUUM` (`vacuum.c:8411`, no-op undo). Neither is consumed wrongly. Replication and supplemental (CDC) logging do not consult the transaction state. | Source, two independent reviewers | 3 |
| F9 | If 146 cannot be appended, the prepare returns before the lock release. The transaction stays ACTIVE and the client gets an error. | Source | 3 |

### Shared challenge questions

**SQ1, exactly-once.** Answered independently by the recovery reviewer (opus) and the 2PC-state reviewer (sonnet), with the same conclusion:

| Crash point | Restart does | Commit by TM | Rollback by TM |
|---|---|---|---|
| Before 146 or the prepare record is durable | transaction undone | n/a | consistent |
| Prepare durable (± checkpoint after it) | in doubt; restore S, nothing zeroed | applies S once | applies none |
| After k of n stats-commit records (± checkpoints between them) | in doubt; redo applies k; restore S; zero those k | applies n−k: once in total | **k deltas remain** (documented limitation) |
| All n stats-commit records, no `LOG_COMMIT` | in doubt; zero all n | applies nothing more, writes `LOG_COMMIT` | all n remain |
| `LOG_COMMIT` durable | transaction finished by redo | n/a | n/a |
| Second restart, or a crash in the resumed commit | same walk; zero set is the union | correct | as above |

At base the trade-off was the opposite: a rollback stayed consistent, but a commit after restart lost every delta.

**SQ2, widened logging gate.** Answered independently by the 2PC-state reviewer (sonnet) and the HA/storage reviewer (opus): no wrongly consumed record on a protocol-following path (F8). Two secondary effects:
- Statements sent on an already-prepared branch, if CAS/JDBC lets them through, are now logged. Before the PR they were silently dropped. Not traced; low.
- `RVES_NOTIFY_VACUUM` now reaches the log on a 2PC commit without a restart. This fixes a leak: the deleted LOB files of a 2PC commit were never removed before.

## Confirmed findings

None.

## Non-blocking comments

| ID | Priority | Comment |
|---|---|---|
| N1 | P3, documented | **Rollback after a crashed commit.** If the commit was interrupted after some stats-commit records became durable, a TM rollback leaves those k′ values while the rows roll back (statistics 601, heap 600). The PR documents this. Optional fix: on abort of a restored in-doubt transaction, log compensating absolute values for the zeroed indexes. |
| N2 | P3, documentation | **Compatibility wording.** The PR's compatibility text suggests that only an in-doubt transaction at downgrade time matters. In fact, any XA prepare that touched a unique index since the last checkpoint puts a 146 record in the redo range, even after its branch committed. So an older **release** binary crashes on the first restart after an abnormal stop of the new binary. Suggested wording: "after an abnormal stop of the new binary, do not start an older binary". This is the same class as rcvindex 145 (#8460). |
| N3 | P3 | Indexes with zero deltas and `deleted` indexes are still packed into 146. A read-only XA branch with a non-empty hash also writes the record. Consider skipping zero entries. |
| N4 | P3 | The adjacency rule (146 is exactly the record before the prepare record) exists only as a comment. Consider an assert at the producer. |
| N5 | P3, pre-existing pattern | The commit-side `log_append_redo_data2` still drops the stats-commit record silently on OOM. `new char[]` in `log_rv_get_unzip_log_data` is unguarded and is now also reachable from the restore pass. |

## TC PR #5070

The TC adds a shell case `cbrd_28200` and a small JDBC XA client, following the pattern of the neighbouring 2PC case `cbrd_28166`.
- **Setup:** PK + UNIQUE tables of 600 rows each.
- **Branches:** each XA branch prepares and is decided through `xa_recover()`. Branches cover a commit before any kill, an INSERT, a DELETE, savepoint rollback inside a branch, and a rollback decision.
- **Scenarios:** a single kill (case1), two kills before the decision (case2), and a checkpoint between prepare and kill (case3).
- **What it compares:** at each stage, the unconditional `COUNT(*)` (served from unique statistics) against the heap count and the expected count. Stages: after restart, after the decision, after another kill, after a clean restart.
- **Final checks:** `checkdb -S`, no assertion, no core.
- **Problem 2 is covered:** commit without a restart, then a kill before a checkpoint. A guard fails the case if a checkpoint slipped in.

**Execution.** All runs use the native testkit focused shell workflow at TC head `c82181e`:

| Run | Engine | Result |
|---|---|---|
| CI gha-ci run 45339799450, shell shard 05 | head `aff1bae` | `cbrd_28200` OK (~118 s) |
| Local, debug + `SUPPORT_XA=true` | head `aff1bae` | **OK 25 / NOK 0**, verify PASS |
| Local, debug + `SUPPORT_XA=true` | base `051a19c` | **OK 11 / NOK 14** |

On the base, the NOK checks show the bug exactly:
- After each commit decision and after a clean restart, the statistics count stays at the value before the branch while the heap count moves (600 vs 601 for inserts, 600 vs 599 for the delete).
- The branch committed before the kill loses its change across the kill (problem 2).
- `checkdb -S` reports the inconsistency.
- The rollback branch and every "before decision" check pass on both builds.

**Build-configuration note.** A first local attempt used a CMake preset build without `SUPPORT_XA`, so `CCI_XA` was undefined. Head and base both stopped at the first decision with `ER_LOG_2PC_UNKNOWN_GTID` (−107). The cause:
- Without `CCI_XA`, `log_2pc_attach_global_tran` attaches only to prepared *loose ends*. It cannot attach to a branch whose preparing connection is still open, which this TC needs.
- With `CCI_XA` it promotes the prepared transaction and attaches.
- CI and `build.sh` default to `SUPPORT_XA=true` (`build.sh` → `CMakeLists.txt` adds `-DCCI_XA`).
- The PR has no `CCI_XA` conditionals. Still, restart behaviour in a non-`CCI_XA` build is not covered by this TC, and that configuration uses different 2PC recovery paths.

**TC comments (non-blocking).**

| ID | Priority | Comment |
|---|---|---|
| T1 | P3, TC defect | case3 waits for a checkpoint to *start* (`-977` in the server log), not to finish (`-978`), before the kill. A kill during the checkpoint loses some coverage but cannot cause a false failure. |
| T2 | P3, coverage | `COUNT(*)` observes only the PK index's object count. The UNIQUE index, null count and key count are checked only by the final `checkdb -S`. Nothing positively shows that `COUNT(*)` is answered from statistics. |
| T3 | P2, coverage (manual by the author) | Not in the TC: a 146 record that spans a log page or is compressed, and a commit interrupted after a stats-commit record. The second needs an engine fault hook. The author measured both with test-only commits (PR body). They were not replayed in this review. |
| T4 | P3, coverage | NULL keys, and branches whose net statistics change is zero. |
| T5 | info | The case needs a `CCI_XA` engine build (see above). The CTP it runs on must provide `wait_until`. |

## Unverified risks

| ID | Priority | Risk | Next check |
|---|---|---|---|
| U1 | P3 | **A restored BTID whose index is gone.** An online unique-index build can be rolled back at restart while a prepared transaction still has that index in its restored hash. ¹ Ordinary DROP INDEX cannot run while the branch is in doubt, because its retained lock conflicts. | Online unique index + XA branch + kill during the build, then commit and rollback. Hardening: validate restored BTIDs (as `btree_rv_undo_global_unique_stats_commit` does with `disk_is_page_sector_reserved`) or skip on failure. |
| U2 | — | The author's measurements back these claims; this review did not replay them: delay injection between the stats-commit record and `LOG_COMMIT`, compressed or page-spanning records read from archives, and old/new binary compatibility. | Optional |

¹ What U1 does:
- **On commit:** the statistics-entry load fails, `mht_map_no_key` stops, and `logtb_complete_mvcc` asserts (`log_tran_table.c:4804`). Release silently skips the remaining indexes.
- **On TM rollback:** the online-index rollback path (`log_update_global_btid_online_index_stats`, `log_manager.c:11173`) now sees the restored entries.
- **Attribution:** the no-restart variant already exists at base. The restart variant is new, because restart used to empty the hash.
- **Evidence:** source only, level 2.

## Pre-existing defect (separate issue, not caused by this PR)

- **P-1 (P2, source argument, not reproduced): a checkpoint can save a just-prepared participant as ACTIVE.**
  - `log_2pc_prepare_global_tran` appends `LOG_2PC_PREPARE` (`log_2pc.c:1590`) and sets `tdes->state = TRAN_UNACTIVE_2PC_PREPARE` afterwards, outside `prior_lsa_mutex` (`log_2pc.c:1602`).
  - A checkpoint whose transaction-table snapshot falls in that window saves the transaction as `TRAN_ACTIVE`.
  - Restart analysis sees the prepare record and then the end-of-checkpoint record. The end-of-checkpoint handler resets the transaction to unilaterally aborted, and undo rolls back a branch that already answered "prepared".
  - The same pattern exists for `LOG_2PC_COMMIT_DECISION` (`log_2pc.c:1949-1953`).
  - Fix direction: set the 2PC state at append time under the mutex, as `commit_abort_lsa` does.
  - Recommend a separate JIRA issue after a gdb probe.

## Checks run

| Check | Result |
|---|---|
| Debug build of head (`aff1bae`) | Success. 0 warnings in the 7 changed files |
| Release-flag recompile (`-O2 -DNDEBUG`), server and SA, of the changed transaction files | 0 warnings |
| GNU indent (`-l120 -lc120`) on the 7 files | no diff |
| Pack/unpack probe with real `OR_*` macros | pass |
| `RV_fun` index ↔ enum script | 147 entries, consistent |
| TC `cbrd_28200`, native testkit, `SUPPORT_XA=true` | head OK 25/25 (verify PASS); base NOK 14 / OK 11 |
| PR CI (gha-ci 45339799450) | `cbrd_28200` OK. Shell shard 15 failed on `cbrd_28061`, which the PR body attributes to its base (not re-verified) |

Not run: gdb crash-point injection, the U1 probe, the old-binary restart, `diagdb -d 8` on a 146 record, UBSan (library unavailable on the host).

## Coverage and method

Five specialist reviewers worked on pinned sources:
- recovery (opus)
- 2PC state machine and concurrency (sonnet)
- systems / C++ (sonnet)
- HA, storage and performance (opus)
- TC adequacy (sonnet)

Every changed path had a primary owner. Each reviewer reported complete coverage of its assignment at source level. SQ1 and SQ2 were each answered by two reviewers on different models. A separate worker ran the TC and the builds. Hypotheses rejected with source evidence include:
- the new record disturbing rollback or restart undo traversal: rollback and undo skip `LOG_REDO_DATA`
- checkpoint races on the restored hash: no other thread reads another transaction's hash
- cross-thread frees: global allocations

Budget: bounded mode without a hard cap. Each reviewer finished in about 15–19 minutes. Account-wide usage cannot be attributed to individual agents.
