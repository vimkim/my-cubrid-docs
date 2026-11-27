# Code review — CUBRID/cubrid#8674 + cubrid-testcases-private-ex#5070 (CBRD-28200)

**Goal.** Check "[CBRD-28200] Keep the unique statistics of a prepared transaction across a restart" in depth. Scope:
- Whether 2PC unique-statistics deltas survive a crash and restart, applied exactly once.
- Invariants of log redo/undo, checkpoint and recovery.
- Locking and concurrency edge cases, and resource and error handling.
- Whether TC PR #5070 tests the prepared-transaction restart scenario adequately.

**Most consequential result.** The engine change has no confirmed defect (verified at initial snapshot `aff1baed6394` and re-verified on delta snapshot `681ee7ac4ba8`).
- **Exactly-once:** two reviewers on different models independently concluded that a commit decision applies each delta exactly once at every crash point. The only exception is a TM rollback after an interrupted commit, which violates the protocol and which the PR documents.
- **The new TC catches the bug.** It passes on the PR head (both `aff1baed` and `681ee7ac4b`), fails on the base as the bug predicts, and passed in the PR's CI (`45339799450` and `45852709587`). It needs an engine built with `SUPPORT_XA=true`.

| Item | Value |
|---|---|
| Engine PR | https://github.com/CUBRID/cubrid/pull/8674 (author hornetmj; reviewers lht1199, vimkim) |
| Current snapshot (2026-11-27 KST) | base `435b0b70059a3fb650fc18f148db4930a345ba04` / head `681ee7ac4ba89b340c77fa67de14ff5a4059e3c7` / merge-base `435b0b70059a3fb650fc18f148db4930a345ba04` |
| Current comparison | `git diff 435b0b70059a3fb650fc18f148db4930a345ba04 681ee7ac4ba89b340c77fa67de14ff5a4059e3c7` (sha256 `f1932f2dc33e0c13a7b7bebd4451e80fcde30bd4aa7261676a2d50410f6fddc7`); 7 files under `src/transaction/` (`log_2pc.c`, `log_impl.h`, `log_manager.c`, `log_recovery.c`, `log_tran_table.c`, `recovery.c`, `recovery.h`), +451/−11 |
| Prior snapshot (2026-11-26 KST) | base `051a19c358fd13bef2cdd4110f5e4443e81c5757` / head `aff1baed6394b547cca4739c09d3672de97a4b90` (sha256 `76521de4…8ea66f`), +447/−11 |
| TC PR | cubrid-testcases-private-ex#5070 (private), current base `7278dbc47e545eaa6adcd0ac8dec526585491978`, head `053fbe5820b01bf7abb7f13bbb6da196cbd392c6` (prior head `c82181e2d880044defbceec1a3809060de09c957`); 2 new shell testcase files (+400) |
| Public TC PR | cubrid-testcases#4372, no changed files |

## Verdict and follow-up

- **Verdict: `no-confirmed-findings`.** Recommendation: **APPROVE** (both engine PR #8674 at `681ee7ac4ba8` and TC PR #5070 at `053fbe5820b0`), with the remaining non-blocking comments below.
- **Follow-up review required: no.** All remaining suggestions are optional.
- **Merge-gate note:** the PR is not vimkim's, so merging belongs to the author. The TC Merge Gate is still open (both TC PRs open).

## Delta re-review (2026-11-27 KST, `aff1baed6394` -> `681ee7ac4ba8` / TC `c82181e2d880` -> `053fbe5820b0`)

Since the initial review at `aff1baed6394`, the engine PR added commit `a117284fae1148a60dffe552d98e56f6054f1d44` and merged `develop` (`681ee7ac4ba89b340c77fa67de14ff5a4059e3c7`), and the private TC PR added `8f19dbd985ef58f5e340e93c614281bce243c47c` and merged `develop` (`053fbe5820b01bf7abb7f13bbb6da196cbd392c6`).

- **What changed in the engine delta (`a117284fae11`):**
  - `src/transaction/log_2pc.c`: snapshots `stats_lsa = tdes->tail_lsa` under `#if !defined (NDEBUG)` immediately after `logtb_tran_log_unique_stats_for_2pc` succeeds and asserts `LSA_EQ (&tdes->tail_lsa, &stats_lsa)` immediately before `prior_lsa_next_record` appends `LOG_2PC_PREPARE` (resolves **N4**).
  - `src/transaction/log_recovery.c`: `log_recovery_2pc_read_redo_data` takes target `rcvindex` and `bool *found`, resets `*found = false`, and returns `NO_ERROR` early when `redo.data.rcvindex != rcvindex` without decompressing/copying unrelated `LOG_REDO_DATA` payloads; adds `er_log_debug` on non-fatal restore failure and aligns error-handling comments.
  - `src/transaction/recovery.c`, `log_tran_table.c`, `log_impl.h`: removes `logtb_rv_redo_2pc_unique_stats` and reuses `log_rv_outside_noop_redo` in `RV_fun[146]`; updates comments on `LOG_ISTRAN_LOGGABLE` and nested 2PC.
- **Independent delta verification (`SQ-Delta`):** Two independent reviewers confirmed (source + script, levels 3–4) that:
  - `log_2pc.c` cannot violate the `stats_lsa` adjacency assert on any path (`count == 0`, `count > 0`, `CCI_XA` or `!CCI_XA` nested 2PC, lock demotion/alloc); `#if !defined(NDEBUG)` builds cleanly under `-O2 -DNDEBUG -Werror`.
  - `log_recovery_2pc_read_redo_data` preserves `log_reader` page/LSA synchronization across iterations (`set_lsa_and_fetch_page`) and cannot misread or skip matching records on crash-interrupted chains.
  - `log_rv_outside_noop_redo` has no pointer-identity checks anywhere in `src/`, runs synchronously in parallel redo (`VPID_ISNULL` -> `log_rv_need_sync_redo == true`), and is ignored/dumped safely by rollback, undo, vacuum, HA applier, `copylogdb`, `flashback`, and `diagdb`.
- **`develop` merge audit (`681ee7ac4ba8`):** `git show --cc` is empty (zero conflict drift). None of the 10 `develop` commits touching `src/transaction/` (`051a19c358..435b0b7005`, including `CBRD-27936`, `CBRD-26305`, `CBRD-28021`) adversely interact with 2PC prepare, unique stats restoration, or `LOG_ISTRAN_LOGGABLE`.
- **TC PR #5070 delta (`8f19dbd985ef` + `053fbe5820b0`) & PR compatibility wording:**
  - The TC helper now accepts an optional error code and `case3` waits for checkpoint completion (`-978`, `ER_LOG_CHECKPOINT_FINISHED`, logged and flushed after `LOG_CS_EXIT`) instead of checkpoint start (`-977`), resolving **T1**. `case2` also adds a guard confirming no checkpoint ran during the decision/check window before killing the server. Merge `053fbe5820b0` is clean with zero extraneous files.
  - PR #8674's `## Remarks` compatibility section and footnote `²` now accurately state the redo-range crash rule for downgrading to an older `release` binary after an abnormal stop vs. clean-shutdown downgrade safety, resolving **N2**.
- **Delta checks run (`681ee7ac4ba8` + TC `053fbe5820b0`):**
  - `cubrid-static-check`: 0 new cppcheck, 0 new clang-tidy, 0 new CPD clones; lizard CCN 17 on `log_recovery_2pc_restore_tran_unique_stats` (complexity only).
  - Debug `configure-build-and-install` (`SUPPORT_XA=true`): `BUILD_RC=0`, 0 warnings in the 7 changed files.
  - Release `-O2 -DNDEBUG -Wall -Werror` (`SERVER_MODE` & `SA_MODE`) recompile of the 5 changed `.c` files: 0 errors, 0 warnings.
  - GNU `indent -l120 -lc120` on the 7 changed files: 0 diff lines.
  - `RV_fun` index ↔ enum check: 147 entries (0..146), 0 mismatches.
  - Native focused shell run of the `cbrd_28200` TC (`SUPPORT_XA=true`): `RUNNER_EXIT=0`, `testkit-focused.py verify` passed (`total=1, success=1, fail=0`), **OK 25 / NOK 0** in 125s.
  - CI `gha-ci` run `45852709587`: builds, static checks, `test_medium`, `test_sql`, `test_sql_by_cci` all `SUCCESS`; the `cbrd_28200` shell case ran on shard 49 against `681ee7ac4ba8` + TC `053fbe5820b0` and **PASSED (`[OK]`)**; all 30 `test_shell` failures match base `develop` `435b0b70059a` (run `45848718864`) one-for-one (`PR - Base = []`, `Base - PR = []`).
- **Additional pre-existing defensive-hygiene notes (non-blocking, P3):**
  - `D1` (`log_tran_table.c:4117-4121`): `logtb_rv_2pc_restore_unique_stats` executes `OR_GET_INT (datap)` before checking `length < OR_INT_SIZE`. `log_zip_alloc (IO_PAGESIZE)` prevents heap OOB for the sole current caller, and `count` is discarded on short length, but reordering the check first avoids reading uninitialized heap bytes on a corrupt `< 4`-byte record.
  - `D2` (`log_recovery.c:3674`): `OR_GET_BTID (zip->log_data, &btid)` assumes `zip->data_length >= OR_BTID_ALIGNED_SIZE` (guaranteed on valid records; `IO_PAGESIZE`-backed buffer prevents heap OOB).

## What changed (architecture, from initial review `aff1baed6394`)

- **Prepare:** `log_2pc_prepare_global_tran` calls the new `logtb_tran_log_unique_stats_for_2pc`. It packs the transaction's unique-statistics hash into a new redo-only, pageless record, `RVBT_2PC_UNIQUE_STATS` (rcvindex 146). The record is appended directly before `LOG_2PC_PREPARE` and before the shared locks are released. If the append fails, the prepare fails.
- **Restart:** the new `log_recovery_2pc_restore_unique_stats` runs at the end of `log_recovery_redo` for each in-doubt (`TRAN_UNACTIVE_2PC_PREPARE`) transaction:
  - It walks `prev_tranlsa` from `tail_lsa` back to the `LOG_2PC_PREPARE` record.
  - It rebuilds the hash from the 146 record just before it (skipping data decompression on non-matching records in `681ee7ac4b`).
  - It zeroes the indexes whose `RVBT_LOG_GLOBAL_UNIQUE_STATS_COMMIT` the interrupted commit already logged, because redo already applied those.
- **Commit after prepare:** the new `LOG_ISTRAN_LOGGABLE` lets `TRAN_UNACTIVE_2PC_PREPARE` and `TRAN_UNACTIVE_2PC_COMMIT_DECISION` log at the four undo/redo append gates in `log_manager.c`. In those states, `logtb_update_global_unique_stats_by_delta` writes the stats-commit record redo-only. Before the fix, a prepared transaction's commit dropped that record (problem 2 in the PR).

## Safety facts

| # | Fact | Evidence | Level |
|---|---|---|---|
| F1 | No record of the transaction is appended between 146 and `LOG_2PC_PREPARE`: the lock release logs nothing, and the prepare is not inside a system operation. The restore finds 146 as the `prev_tranlsa` of the prepare record, now enforced by a debug `LSA_EQ` assert in `log_2pc.c`. | Source (`log_2pc.c`, `lock_manager.c`, `log_append.cpp`) | 3 |
| F2 | The restore pass runs after parallel redo has joined (`log_recovery.c`), so the global statistics already contain every redone stats-commit record. | Source | 3 |
| F3 | Every zeroed index already has its delta in the global statistics, either replayed by redo or written to the B-tree root header by a checkpoint. The zero set comes from walking the log chain and does not depend on the redo start point. | Source, crash-point table below | 3 |
| F4 | Archive retention adds no new risk. The walk reads a subset of the log that `log_recovery_2pc_restore_prev_versions` and `log_2pc_recovery_analysis_info` already read. A page that cannot be read or unzipped stops restart, as elsewhere in recovery. | Source | 3 |
| F5 | The statistics chunks and the `mht` come from global allocations, not per-thread private heaps. So the hash the recovery thread builds can be freed by the worker that later decides the branch. The pack buffer is the only `db_private_alloc`, and it is freed in the same function. | Source | 2 |
| F6 | Pack/unpack: 40-byte entries, big-endian, with zeroed padding. A standalone probe with the real `OR_*` macros round-trips 1000 entries, and its 13 validation edge cases (negative count, `INT_MAX`, short length) behave correctly. `log_rv_get_unzip_log_data` resizes and decompresses records larger than `IO_PAGESIZE`. | Probe + source | 4 |
| F7 | `RV_fun` has 147 entries with entry *i* = rcvindex *i*. Inside the same version, nothing indexes the table with 146 except redo. Its redo function is `log_rv_outside_noop_redo` (no-op, no pointer-identity checks). Rollback, restart undo, vacuum, the HA applier, copylogdb, CDC and flashback ignore the record or compare against other specific rcvindex values. | Script over source + source | 3–4 |
| F8 | On a protocol-following path, the widened gates newly log only two record types: `RVBT_LOG_GLOBAL_UNIQUE_STATS_COMMIT` (redo-only, `log_tran_table.c`) and `RVES_NOTIFY_VACUUM` (`vacuum.c`, no-op undo). Neither is consumed wrongly. Replication and supplemental (CDC) logging do not consult the transaction state. | Source, two independent reviewers | 3 |
| F9 | If 146 cannot be appended, the prepare returns before the lock release. The transaction stays ACTIVE and the client gets an error. | Source | 3 |

### Shared challenge questions

**SQ1, exactly-once (prior snapshot `aff1bae`).** Answered independently by the recovery reviewer and the 2PC-state reviewer, with the same conclusion:

| Crash point | Restart does | Commit by TM | Rollback by TM |
|---|---|---|---|
| Before 146 or the prepare record is durable | transaction undone | n/a | consistent |
| Prepare durable (± checkpoint after it) | in doubt; restore S, nothing zeroed | applies S once | applies none |
| After k of n stats-commit records (± checkpoints between them) | in doubt; redo applies k; restore S; zero those k | applies n−k: once in total | **k deltas remain** (documented limitation) |
| All n stats-commit records, no `LOG_COMMIT` | in doubt; zero all n | applies nothing more, writes `LOG_COMMIT` | all n remain |
| `LOG_COMMIT` durable | transaction finished by redo | n/a | n/a |
| Second restart, or a crash in the resumed commit | same walk; zero set is the union | correct | as above |

At base the trade-off was the opposite: a rollback stayed consistent, but a commit after restart lost every delta.

**SQ2, widened logging gate (prior snapshot `aff1bae`).** Answered independently by two reviewers: no wrongly consumed record on a protocol-following path (F8). Secondary effects: statements sent on an already-prepared branch (if CAS/JDBC allowed them) would now be logged (untraced, low), and `RVES_NOTIFY_VACUUM` now reaches the log on a 2PC commit without restart (fixing a deleted-LOB leak).

**SQ-Delta, `a117284fae11` + merge `681ee7ac4ba8`.** Answered independently by two reviewers: the `log_2pc.c` adjacency assert, `log_recovery_2pc_read_redo_data` early return, and `log_rv_outside_noop_redo` reuse preserve all prepare, recovery, parallel redo, HA, `copylogdb`, `flashback`, and log-dump invariants.

## Confirmed findings

None.

## Non-blocking comments

| ID | Priority | Status | Comment |
|---|---|---|---|
| N1 | P3, documented | Open (documented) | **Rollback after a crashed commit.** If the commit was interrupted after some stats-commit records became durable, a TM rollback leaves those k′ values while the rows roll back (statistics 601, heap 600). Optional fix: on abort of a restored in-doubt transaction, log compensating absolute values for the zeroed indexes. |
| N2 | P3, documentation | **Resolved** | **Compatibility wording.** PR #8674 `## Remarks -> 호환성` and footnote `²` now accurately describe the redo-range crash condition vs. clean-shutdown safety. |
| N3 | P3 | Open | Indexes with zero deltas and `deleted` indexes are still packed into 146. A read-only XA branch with a non-empty hash also writes the record. Consider skipping zero entries. |
| N4 | P3 | **Resolved (`a117284`)** | Producer adjacency rule (`146` is immediately before `LOG_2PC_PREPARE`) is now enforced by debug assert in `log_2pc.c`. |
| N5 | P3, pre-existing pattern | Open (comment updated) | The commit-side `log_append_redo_data2` still drops the stats-commit record silently on OOM. `new char[]` in `log_rv_get_unzip_log_data` is unguarded and reachable from the restore pass (fatal on failure, now noted in `log_recovery.c` comment). |
| D1 | P3, pre-existing hygiene | Open | In `logtb_rv_2pc_restore_unique_stats`, check `length < OR_INT_SIZE` before `OR_GET_INT (datap)` so a corrupted `< 4`-byte record never reads uninitialized heap bytes from `zip->log_data`. |
| D2 | P3, pre-existing hygiene | Open | In `log_recovery_2pc_restore_tran_unique_stats`, `OR_GET_BTID (zip->log_data, &btid)` assumes `zip->data_length >= OR_BTID_ALIGNED_SIZE` (guaranteed on valid records; `IO_PAGESIZE`-backed buffer prevents heap OOB). |

## TC PR #5070

The private TC adds an XA prepared-transaction restart shell test modeled on the neighbouring 2PC case `cbrd_28166`.
- **Setup:** PK + UNIQUE tables of 600 rows each.
- **Branches:** each XA branch prepares over JDBC XA and is decided through `xa_recover()`. Branches cover a commit before any kill, an INSERT (plus concurrent insert before decision), a DELETE, savepoint rollback inside a branch, and a rollback decision.
- **Scenarios:** a single kill (`case1`), two kills before the decision plus a kill after commit (`case2`), and a completed checkpoint between prepare and kill (`case3`).
- **What it compares:** at each stage, the unconditional `COUNT(*)` (served from unique statistics) against the heap count and the expected count (`after restart`, `after decision`, `after another kill`, `after clean restart`), followed by `checkdb -S`, zero `ER_FAILED_ASSERTION`, and zero core files.
- **Problem 2 is covered:** commit without a restart, then a kill before a checkpoint, with a checkpoint-count guard failing the case if a checkpoint slipped in.

**Execution.** Runs use the native testkit focused shell workflow (`SUPPORT_XA=true`):

| Run | Engine / TC | Result |
|---|---|---|
| CI gha-ci run `45852709587`, shell shard 49 | head `681ee7a` / TC `053fbe58` | `cbrd_28200` **OK** |
| Local native testkit, debug + `SUPPORT_XA=true` | head `681ee7a` / TC `053fbe58` | **OK 25 / NOK 0** (125s, verify `total=1, success=1, fail=0`) |
| CI gha-ci run `45339799450`, shell shard 05 | prior head `aff1bae` / TC `c82181e` | `cbrd_28200` **OK** (~118 s) |
| Local native testkit, debug + `SUPPORT_XA=true` | prior head `aff1bae` / TC `c82181e` | **OK 25 / NOK 0**, verify PASS |
| Local native testkit, debug + `SUPPORT_XA=true` | prior base `051a19c` / TC `c82181e` | **OK 11 / NOK 14** (demonstrates the bug) |

**Build-configuration note.** A preset build without `SUPPORT_XA` leaves `CCI_XA` undefined, causing decisions on an open preparing connection to fail with `ER_LOG_2PC_UNKNOWN_GTID` (−107). CI and `build.sh` default to `SUPPORT_XA=true` (`-DCCI_XA`).

**TC comments (non-blocking).**

| ID | Priority | Status | Comment |
|---|---|---|---|
| T1 | P3, TC defect | **Resolved (`8f19dbd`)** | `case3` now waits for checkpoint completion (`-978`) rather than start (`-977`); `case2` adds a guard checking no checkpoint ran between decision and kill. |
| T2 | P3, coverage | Open | `COUNT(*)` observes only the PK index's object count. The UNIQUE index, null count and key count are checked only by the final `checkdb -S`. |
| T3 | P2, coverage (manual by author) | Open | Not automated in the TC: a 146 record spanning a log page or compressed, and a commit interrupted after a stats-commit record (verified manually by the author with fault injection and strace). |
| T4 | P3, coverage | Open | NULL keys, and branches whose net statistics change is zero. |
| T5 | info | Open | Requires a `CCI_XA` (`SUPPORT_XA=true`) engine build and CTP `wait_until`. |

## Unverified risks

| ID | Priority | Risk | Next check |
|---|---|---|---|
| U1 | P3 | **A restored BTID whose index is gone.** An online unique-index build can be rolled back at restart while a prepared transaction still has that index in its restored hash (`logtb_complete_mvcc` asserts in debug on commit; rollback path iterates restored entries). Attribute: no-restart variant pre-existing; restart variant new. Evidence: source only, level 2. | Online unique index + XA branch + kill during the build, then commit and rollback. Hardening: validate restored BTIDs or skip on failure. |
| U2 | — | Author-measured scenarios not independently replayed in this review: delay injection between stats-commit record and `LOG_COMMIT`, compressed/page-spanning 146 records read from archives, and old/new binary compatibility. | Optional |

## Pre-existing defect (separate issue, not caused by this PR)

- **P-1 (P2, source argument, not reproduced): a checkpoint can save a just-prepared participant as ACTIVE.** `log_2pc_prepare_global_tran` appends `LOG_2PC_PREPARE` (`log_2pc.c:1590`) and sets `tdes->state = TRAN_UNACTIVE_2PC_PREPARE` afterwards outside `prior_lsa_mutex` (`log_2pc.c:1602`). The same pattern exists for `LOG_2PC_COMMIT_DECISION` (`log_2pc.c:1949-1953`). Recommend a separate JIRA issue after a gdb probe.

## Checks run (consolidated)

| Check | Result |
|---|---|
| `cubrid-static-check` (`435b0b7005..681ee7ac4b`) | 0 cppcheck, 0 clang-tidy, 0 CPD clones; lizard CCN 17 on `log_recovery_2pc_restore_tran_unique_stats` |
| Debug build of head `681ee7ac4b` (`SUPPORT_XA=true`) | Success (`BUILD_RC=0`), 0 warnings in the 7 changed files |
| Release-flag recompile (`-O2 -DNDEBUG -Wall -Werror`), server and SA, of changed `.c` files (`681ee7ac4b`) | 0 warnings, 0 errors |
| GNU `indent` (`-l120 -lc120`) on the 7 files (`681ee7ac4b`) | 0 diff lines |
| `RV_fun` index ↔ enum script (`681ee7ac4b`) | 147 entries (0..146), 0 mismatches |
| Pack/unpack probe with real `OR_*` macros (`aff1bae`, unchanged format in `681ee7ac4b`) | Pass (1000 entries + 13 edge cases) |
| Native focused shell TC `cbrd_28200` (`SUPPORT_XA=true`) | Head `681ee7a` / TC `053fbe58`: **OK 25/25** (125s, verify PASS); prior head `aff1bae`: **OK 25/25**; prior base `051a19c`: **OK 11 / NOK 14** |
| PR CI (`gha-ci 45852709587`, head `681ee7ac4b` / TC `053fbe58`) | Builds, static checks, `test_medium`, `test_sql`, `test_sql_by_cci` all pass; `cbrd_28200` OK on shell shard 49; 30 `test_shell` failures match base `develop` `435b0b70059a` identically |

Not run: gdb crash-point injection, the U1 probe, old-binary restart, `diagdb -d 8` on a 146 record, UBSan.

## Coverage and method

- **Initial review (`aff1bae`, 2026-11-26):** Five specialist reviewers (recovery, 2PC state/concurrency, systems/C++, HA/storage/perf, TC adequacy) + build/TC worker; bounded mode.
- **Delta re-review (`681ee7ac4b`, 2026-11-27):** Two specialist reviewers (`rev-rec`, `rev-tc`) covering engine delta `a117284`, `develop` merge `681ee7ac4b`, TC delta `8f19dbd` + `053fbe58`, CI run `45852709587`, and independent `SQ-Delta`, plus a shell build/test worker (`build`); bounded mode without a hard cap. Account-wide usage cannot be attributed to individual agents.
