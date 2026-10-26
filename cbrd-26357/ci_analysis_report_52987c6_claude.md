# CI Snapshot Warning: PR #7990 at `52987c6`

## Decision boundary

**This snapshot supports no regression conclusion and no root-cause conclusion.**
The single exact-head collection selected rerun `40334404336`.
All three requested suites were `running` at collection time, so the collector exited `3`.
The analyzer gate (`report_mode.py`) returned `mode: warning` and `comparison_scope: none`, both before and after the baseline assessment.

This report also records separately validated evidence that the collector retained for the same exact head.
That evidence is run `40323508581` attempt 1, `test_shell` only.
The sections about that run give observations, a baseline comparison, testcase history, and **provisional hypotheses**.
The hypotheses are inferences with falsifiers. They are not regression or root-cause conclusions of this snapshot.

- Question: are the three `test_shell` failures of run `40323508581` caused by the PR head, or are they test or environment instability?
- Intended reader: the PR #7990 author and the agent that handles the rerun.
- Analysis date: 2026-10-26, Asia/Seoul.

## Identity

| Field | Value |
|---|---|
| Repository | `CUBRID/cubrid` |
| Pull request | [#7990 — [CBRD-26357] Add out-of-row overflow storage](https://github.com/CUBRID/cubrid/pull/7990), `feature/oos-merge` → `develop` |
| Exact head | `52987c654b6f04734cad01c11c80c7f30358b33c` |
| Status snapshot | `cubrid-ci status`, fetched `2026-10-26T13:52:56Z` |
| Collection | `cubrid-ci collect … --commit 52987c65…`, collected `2026-10-26T13:53:21.357Z`, exit `3` |
| Collector | `cubrid-ci 0.2.0 (9536bd3c2867, release)`. Schema source `/home/vimkim/gh/cubrid-ci/schema` is clean at the same commit. |
| History tool | `cubrid-tcc 0.3.0` |
| Merge base | `c1dfe7e8719d254d61b33fc513d704f4f4f0a8b2`. The `develop` tip was `4781495f…` at `2026-10-26T13:56:43Z`. The PR does not contain a newer `develop` merge. |
| Previous PR head | `5a65b28073f322bde6407e1754c0d27691de8f89` (11 commits before this head) |

## Current snapshot

### Suite state

| Suite | Collection state | CI status | Run | Attempt | Validated counts |
|---|---|---|---:|---:|---|
| `test_medium` | `running` | `PENDING` (13:52:35Z) | [40334404336](https://github.com/CUBRID/cubrid/actions/runs/40334404336) | 1 | Not available |
| `test_sql` | `running` | `PENDING` (13:52:37Z) | [40334404336](https://github.com/CUBRID/cubrid/actions/runs/40334404336) | 1 | Not available |
| `test_shell` | `running` | `PENDING` (13:52:36Z) | [40334404336](https://github.com/CUBRID/cubrid/actions/runs/40334404336) | 1 | Not available |

### Observation validation

- **Observed:** observation `20261026T135320.772199222Z-355615-0` has `request.json` and `result.json`. Both validate against the v1 observation schemas. The IDs match.
- **Observed:** the request identifies `CUBRID/cubrid`, PR 7990, and the pinned head. It requests all three suites without binaries.
- **Observed:** `result.json.command` is equal to the saved collector result. The root `manifest.json` is equal to the same result. Both validate against the v2 schemas.
- **Observed:** the outcome is `incomplete`. The acquisition ledger is empty. The binary budget used 0 of 536870912 bytes. The command has no error records.
- **Not available:** a suite summary, a testcase revision, or failure text for run `40334404336`. No suite verdict comes from this snapshot.

### Context after the snapshot (unvalidated)

At `2026-10-26T14:01Z`, a read-only `gh run view` call reported run `40334404336` as `completed` with conclusion `success` (11 jobs `success`, 1 job `skipped`).
The collector did not collect or validate this result.
This report does not use it for any classification.

## Retained evidence: run 40323508581 attempt 1, `test_shell`

### Validation

The collector retained an earlier observation for the same head: `20261026T133639.640157573Z-269289-0`.
It requested `test_shell` only. Its outcome is `complete`.
This report validated it independently:

- The request, result, and embedded command result validate against their schemas (observation v1, command-result v2).
- `summary.json` validates against `suite-summary-v2`. `raw/index.json` validates against `raw-evidence-index-v2`.
- All 616 indexed raw files match their declared size and SHA-256. The summary digest matches the index.
- All three `failures/<stable_id>/metadata.json` files validate against `failure-v2`. Each declared `message.txt` and `diff.txt` exists.
- Counts reconcile: tests 3484 = 3451 passed + 3 failures + 0 errors + 30 skipped. Planned 3484 = 3454 run + 0 unrun + 30 skipped.
- All 50 shards have one Engine identity and one testcase identity:
  - Engine `52987c654b6f…`, `debug`, namespace `pr`, built by run `40323462920` attempt 1.
  - Testcases `cubrid-testcases-private-ex` `tc/pr-7990` at `dd12b36a249e48a63725113af59ed4b013c3894a`.

The root manifest now describes the later `running` collection. The retained observation's embedded command is the record of the earlier result.

### Failure inventory

| # | Full testcase path | Shard | Result | Observed signature | Baseline class | Category (provisional) | PR relation (provisional) | Confidence |
|---|---|---:|---|---|---|---|---|---|
| F1 | `shell/_06_issues/_12_2h/bug_bts_7456_1/cases/bug_bts_7456_1.sh` | 43 | failure | `Locks Check Test 4 Failed, 1, 0` instead of `Succeeded`. Tests 1–3, 5, and 6 succeed. | `additional_on_head` | timing-sensitive test | unlikely | medium |
| F2 | `shell/_35_cherry/issue_21654_server_side_loaddb/syntax/cases/syntax.sh` | 21 | failure | `syntax-3` only: `line 99: syntax error at "abc97"` is absent. `1 object(s) failed` instead of `2`. | `additional_on_head` | loaddb status-poll race | unlikely | medium |
| F3 | `shell/_36_damson/cbrd_23608_tde/temp_enc_06/cases/temp_enc_06.sh` | 40 | failure | One `TDE: qmgr_process_query(): includes_tde_class = 1` line instead of two | `additional_on_head` | test harness: error-log minute boundary | unlikely | high |

Reconciliation: 3 head failures, 0 errors. 0 `also_observed_on_base`, 3 `additional_on_head`, 0 `uncomparable`, 0 `base_only` in `test_shell`.
The baseline classes apply to this retained execution only. The gate does not permit regression conclusions from them.

## Baseline comparison

### Acquisition

`cubrid-ci collect-base https://github.com/CUBRID/cubrid/pull/7990 --json` exited `4`.

| Field | Value |
|---|---|
| Observation | `20261026T135747.342525805Z-434544-0`, outcome `incomplete`. Request and result validate against the v2 observation schemas. The IDs match. |
| Selection | `exact_commit_links`: all paginated exact-commit statuses and check runs. No repository-wide workflow scan. |
| Identity checks | `.selection.commit == .commit == .selection.baseline.merge_base == c1dfe7e8…`. The PR number is 7990. The baseline head SHA is equal to the pinned head. The request selection is equal to the command selection. The manifest is equal to the result. Command-result v3 and manifest v3 validate. |
| Run | [39979262220](https://github.com/CUBRID/cubrid/actions/runs/39979262220) attempt 1, `workflow_dispatch` "dispatch all c1dfe7e8…", created `2026-10-23T15:33:15Z`, conclusion `success` |
| `test_shell` | `completed` and validated. 3486 tests = 3456 passed + 0 failures + 0 errors + 30 skipped. 616 raw files match size and digest. |
| `test_medium` | `completed` and validated. 975 of 975 passed. |
| `test_sql` | `collection_failed`. Integrity diagnostic: `result identity mismatch: shard 01 workflow result and JUnit counts disagree`. |
| Baseline state | `partial_exact`. Only the validated `test_shell` and `test_medium` suites are eligible for comparison. |

All 50 baseline `test_shell` shards record Engine `c1dfe7e8…` `debug`, namespace `develop`, built by run `39919677226`.
They record testcases `develop` at `c79be6f9cacc62108fcf755337f0f1321331b0a4`.

### Per-case comparison

| Case | Base shard | Base result | Head shard | Head result |
|---|---:|---|---:|---|
| F1 `bug_bts_7456_1.sh` | 34 | pass (57.038 s) | 43 | failure (56.838 s) |
| F2 `syntax.sh` | 36 | pass (31.794 s) | 21 | failure (30.402 s) |
| F3 `temp_enc_06.sh` | 46 | pass (11.737 s) | 40 | failure (11.623 s) |

Each case appears exactly once on each side. The base JUnit records have no `failure`, `error`, or `skipped` child.

Input equality:

- The head testcase SHA `dd12b36a` and the base testcase SHA `c79be6f9` are different. `c79be6f9` is an ancestor of `dd12b36a`.
- The Git tree of each affected case directory is identical at both SHAs:
  - `bug_bts_7456_1`: `faa41092ef1d…`
  - `syntax`: `b10cd66d40a8…`
  - `temp_enc_06`: `4e799303293e…`
- The CTP shell helpers (`init.sh`, `compare_result_between_files`) are not in this repository. Their version is unknown on both sides.

Configuration differences: build namespace (`pr` against `develop`), runner pods, and wall-clock times. Both sides use `debug` builds.
The comparison uses one execution on each side. For timing-sensitive cases, one base pass and one head fail are weak evidence of a regression.

## Analysis by failure

Each subsection separates observations, inferences, unknowns, the falsifier, and the next action.
Source references use `52987c654` unless they name another commit.

### F1 — `bug_bts_7456_1`: Locks Check Test 4

**Observed (testcase at `dd12b36a`).**
`bug_bts_7456_1.sh` sets `insert_execution_mode=31` and starts the server. Then it runs `locks_check.sh` and compares its output with `answer/i1.a`.
Test 4 does these steps:

1. It creates `t1(id1 int)` with the non-unique index `idx`.
2. Session 0 inserts one row and keeps its transaction open for 7 s.
3. After 1 s, sessions 1 and 2 each insert 50 rows with the same key and commit.
4. After `sleep 5`, the script calls `get_process_status` for each background PID. The test passes only if both sessions finished.

`get_process_status` counts the lines of `ps -u $user x | grep -v grep | grep $1`. `$1` is the PID number, so the match is a substring match on the whole `ps` line.

**Observed (CI run).**
The output is `Locks Check Test 4 Failed, 1, 0`. Thus the check found session 1 still in the `ps` list and did not find session 2.
The case started at 21:52:05 KST and ended at 21:53:01 KST (56.8 s). The base duration was 57.0 s.
The server error-log check found no `Internal Error` (`internal_err=0`).
The build identifies as `11.5.0.2769-52987c6`, `64 optdebug build`.

**Observed (head-only source delta, `5a65b2807..52987c654`).**

- `locator_delete_force_internal` moves heap deletion after index work only outside `SERVER_MODE`. This case runs in client-server mode and Test 4 deletes no rows.
- The `locator_update_index` change applies to primary-key updates with foreign-key children. `t1` has no primary key.
- The `heap_midxkey_get_value` change applies to multi-column keys. `idx` has one column.
- The `vacuum.c` changes apply to interrupted jobs, `ER_OUT_OF_VIRTUAL_MEMORY`, standalone shutdown, and a boot-time partial-block hint.
- `log_applier.c` is the HA log applier. This case does not use HA.
- PR-wide, `lock_manager.c` changes only `lock_dump_resource`.

**Inference.**
A lock-wait regression on the uncommitted key would block sessions 1 and 2 in the same way, and the result would be `Failed, 1, 1`.
The observed `1, 0` is asymmetric. It agrees better with two mechanisms:

- Session 1 took more than about 4 s to start, insert, and commit on a loaded runner with a debug build.
- The substring `grep` matched a different process line, such as a PID that contains the session 1 PID as a substring.

No head-only change is on the Test 4 insert path.
PR relation: **unlikely**. Confidence: **medium**. The test has two plausible non-engine mechanisms. This report did not observe either one directly.

**Unknowns.** The PIDs, the `ps` output, and the per-session timings were not retained. The run did not retain the server error log.

**Falsifier.** Repeated `Failed, 1, 1` results would make a PR-caused lock regression plausible. So would a lock wait for the uncommitted key in lock dumps on `52987c65` but not on `c1dfe7e8`.

**Next action.** Read the validated rerun result for this exact case on the same build. If the case fails again, compare `lockdb` output during Test 4 on the head and base builds.

### F2 — `issue_21654_server_side_loaddb/syntax`: `syntax-3`

**Observed (testcase at `dd12b36a`).**
`syntax-3` loads `objects3` with server-side `cubrid loaddb -C`. Line 99 of `objects3` is `97 abc97`, with an unquoted string.
`load3.answer` expects these two error lines, then `Total 0 object(s) inserted, 2 object(s) failed.`:

- `Line 99:Missing attribute values.  Expected 2, found 1.`
- `line 99: syntax error at "abc97"`

The CI log has only the first error line, then `1 object(s) failed`. Subcases 1, 2, and 4–7 are `OK`.

**Observed (source at `52987c654`).**

1. `server_object_loader::process_line` sets `ER_LDR_MISSING_ATTRIBUTES` and calls `on_syntax_failure` (`src/loaddb/load_server_loader.cpp`).
2. `on_syntax_failure` calls `log_error_message (…, fail = true)`. That function calls `session::on_error`, which does `rows_failed++` and appends the message. Then it calls `session::fail ()`, which sets the session state to failed (`src/loaddb/load_error_handler.cpp`, `src/loaddb/load_session.cpp:395–427`).
3. The parser then reports `LOADDB_MSG_SYNTAX_ERR` through `on_error` with `fail = false`. This adds the second message and the second `rows_failed` (`src/loaddb/load_grammar.yy:801`).
4. The client polling loop in `src/loaddb/load_db.c` stops when `status.is_load_failed ()` is true. It prints `last_stat.rows_committed` and `last_stat.rows_failed` from the statistics that it fetched.

**Inference.**
The session becomes "failed" between the first and the second error.
If the client fetches status in that interval, it stops polling. It then prints exactly one message and `1 object(s) failed`.
This matches the observed signature exactly. The result depends on the timing of the worker thread relative to the client poll.
The head-only delta does not change any loaddb file. PR-wide, the PR changes `load_server_loader.cpp`, `load_server_loader.hpp`, and `load_object.c`. The previous head `5a65b2807` has the same merge base and identical `src/loaddb` content. The case passed there (see the history below).
PR relation: **unlikely**. Confidence: **medium**. The race explains the signature, but this report did not reproduce it.

**Unknowns.** The poll interval and the scheduling of the worker thread in this execution. Whether the race occurs on `develop` builds at a comparable rate.

**Falsifier.** Repeated `1 object(s) failed` results on `52987c65` with zero occurrences on `c1dfe7e8` under the same load would point to a PR-caused change in timing or ordering. So would a head-only change in the order of `fail ()` and the parser error report.

**Next action.** Read the validated rerun result. If it fails again, run the case several times on the head and base builds and compare the failure rates.

### F3 — `cbrd_23608_tde/temp_enc_06`: one TDE line missing

**Observed (testcase at `dd12b36a`).**
On debug builds, `temp_enc_06.sh` sets `er_log_tde=yes`. Then it does these steps:

1. It starts the server, runs `select * from ttt_enc` once, and stops the server.
2. It sets `max_plan_cache_entries=0`.
3. It starts the server, runs the same query again, and stops the server.

It then runs `grep "TDE:"` on `$CUBRID/log/server/${db_name}_latest.err` only. `result.answer` expects two `includes_tde_class = 1` lines, one for each server session.

**Observed (CI run).**
The case started at 22:14:53 KST and ended at 22:15:03 KST.
The final `grep 'Internal Error'` command lists two server error logs:

- `db23608_tmpenc06_20261026_2214.err`
- `db23608_tmpenc06_20261026_2215.err`

`result.log` has one TDE line.

**Observed (source at `52987c654`).**
The server error-log name contains the minute: `%s_%04d%02d%02d_%02d%02d.err` (`src/base/system_parameter.c:6328`).
`er_file_open` opens an existing file of the same name with `r+` and seeks to the end. Thus a restart in the same minute appends to the same file (`src/base/error_manager.c:999–1038`).
`er_file_create_link_to_current_log_file` re-creates `<db>_latest.err` so that it points to the current file (`src/base/error_manager.c:1091–1117`).

**Inference.**
The first server session ran in minute 22:14 and the second session ran in minute 22:15.
`_latest.err` therefore pointed only at the `2215` file, which contains only the second query's line.
The test passes only when both server starts occur in the same minute.
This mechanism is in the testcase, not in the head-only delta.
The history below has 12 earlier failures with the same signature and the same log pattern. One of them is on a `develop` Engine without OOS changes.
PR relation: **unlikely**. Confidence: **high**.

**Unknowns.** The `2214` file was not retained, so this report did not read the first TDE line directly.

**Falsifier.** The `2214` file has no `includes_tde_class` line. Or the case fails on this head with both server starts in one minute.

**Next action.** Treat this as a testcase defect for separate follow-up. A fix is to grep all `${db_name}_*.err` files or to use one error log. Testcase edits need their own authorized workflow.

## Testcase history

History comes from `cubrid-tcc 0.3.0` with the local index `/home/vimkim/.local/share/cubrid-tc-chronicle`.
History is context. It does not change the inventory or the baseline classes above.

### Query scope and refresh

1. Before the refresh, `status` reported freshness `STALE`. Discovery reached `2026-10-19T06:05Z`, and the last observation was `2026-10-23T11:15Z`.
2. One bounded refresh ran: `sync-data --since 2026-10-19T00:00:00Z --until 2026-10-26T13:30:00Z --suite shell --revisit-limit 0 --request-budget 1500`.
3. This report stopped the refresh after 198 run collections because the walk was slow. The refresh started at run `39824917722` and reached run `39626667063`. It wrote no result JSON. `coverage` for the window reports complete discovery of 1031 runs, with 763 runs not yet collected. Run `40323508581` is one of the missing runs.
4. `explain --run 40323508581` returned `target_failure_not_indexed` for all three cases, before the refresh and during it. The final coverage report lists the run as missing. Thus the history below uses other occurrences only.
5. This report ran `history --suite shell` without a date window. All retained observations are `debug` builds.

### Results

| Case | Retained outcomes | Earliest / latest ordered | PR #7990 occurrences | `develop` testcase branch |
|---|---|---|---|---|
| F1 `bug_bts_7456_1.sh` | 187 PASS, 0 FAIL | 2026-10-14 / 2026-10-23 | 2 PASS (`1a8c7057`, `5a65b280`) | 22 PASS |
| F2 `syntax.sh` | 186 PASS, 0 FAIL | 2026-10-14 / 2026-10-23 | 2 PASS (`1a8c7057`, `5a65b280`) | 22 PASS |
| F3 `temp_enc_06.sh` | 180 PASS, 12 FAIL (`SEEN_BEFORE`) | 2026-10-14 / 2026-10-23 | 2 PASS (`1a8c7057`, `5a65b280`) | 21 PASS, 1 FAIL |

Each row also has 6 unordered observations without a completion time.
The retained observations span 176 or more Engine commits and 90 or more pull requests.

### F3 earlier failures

| Execution | Run | Completed (UTC) | Engine | Testcase branch @ SHA | Server logs in the failure text | Test start (KST) |
|---|---|---|---|---|---|---|
| 4016 | 38507118405 | 2026-10-14 04:11 | `fa8de5f4bd` | `tc/pr-8154` @ `b7d4a144a4` | `_1306`, `_1307` | 13:06:55 |
| 5725 | 38546416117 | 2026-10-14 11:01 | `1010768943` | `tc/pr-8145` @ `a15b41f169` | `_1957`, `_1958` | 19:57:54 |
| 6680 | 38669998908 | 2026-10-15 02:51 | `77fbbaca05` | `tc/pr-8084` @ `165dd78b9c` | `_1148`, `_1149` | 11:48:54 |
| 9768 | 38833462825 | 2026-10-16 02:25 | `15e276839d` | `tc/pr-7955` @ `555ed16048` | `_1122`, `_1123` | 11:22:54 |
| 8381 | 38860947648 | 2026-10-16 07:03 | `9736e3874c` | `tc/pr-8190` @ `3d41753a66` | `_1600`, `_1601` | 16:00:53 |
| 11797 | 39179585833 | 2026-10-19 01:08 | `213d785793` | `tc/pr-7758` @ `6fbd370642` | `_0959`, `_1000` | 09:59:54 |
| 11523 | 39186756827 | 2026-10-19 02:21 | `a1d281dcb6` | `tc/pr-7160` @ `e7e1f592a2` | `_1119`, `_1120` | 11:19:54 |
| 10968 | 39200485430 | 2026-10-19 05:19 | `9d5560e289` | `tc/pr-8090` @ `fa03ff23e5` | `_1417`, `_1418` | 14:17:53 |
| 14819 | 39705706863 | 2026-10-22 01:30 | `97ab8e0dc4` | `tc/pr-8207` @ `bc2eb45435` | `_1029`, `_1030` | 10:29:54 |
| 14917 | 39701775791 | 2026-10-22 01:41 | `5dd9e8c4f5` | `tc/pr-8229` @ `8f24d41641` | `_1034`, `_1035` | 10:34:53 |
| 13270 | 39772519128 | 2026-10-22 13:18 | `1dfb3947cd` | `tc/pr-7925` @ `7509f5caa7` | `_2214`, `_2215` | 22:14:54 |
| 12596 | 39805840161 | 2026-10-22 17:36 | `d9b1636f0e` | `develop` @ `b8f5aad161` | `_0231`, `_0232` | 02:31:54 |

- **Observed:** all 12 retained JUnit texts (read with `cubrid-tcc evidence --file test-results/test-shell.xml`, hash-verified) show the same diff as the current failure. The answer has a second `includes_tde_class = 1` line that `result.log` does not have.
- **Observed:** each failure text names two error logs in consecutive minutes. Each test started 53–55 seconds into a minute. The current failure follows the same pattern: start 22:14:53, logs `_2214` and `_2215`.
- **Observed:** execution 12596 is a `workflow_dispatch` run on `develop` with the `develop` testcase branch. Its Engine `d9b1636f0ee1…` (#8188, CBRD-27651) is a `develop` commit and an ancestor of the merge base `c1dfe7e8`. Thus that Engine does not contain the PR #7990 changes.
- **Observed:** for 11 of the 12 failures, the `temp_enc_06` directory tree at the recorded testcase SHA is `4e799303293e…`. This is the same tree as the head and the baseline. The local repository does not contain testcase object `a15b41f169`.
- **Inference:** the failure rate is about 6 percent (12 of 192). This rate is consistent with a minute-boundary window of a few seconds between the two server starts.
- **Tool assessment:** `cubrid-tcc` reports flakiness `UNKNOWN` (`comparison_context_unknown`, `insufficient_comparable_executions`). The tool did not find independent PASS and FAIL observations with equal recorded context. The instability claim above comes from the identical signature, the log-file evidence, the `develop` occurrence, and the source mechanism.

### F1 and F2

The index has no earlier failure of F1 or F2 in its retained scope.
This is absence of evidence in an incomplete scope, not proof that the cases are stable.
The PR #7990 passes include the previous head `5a65b28073f3`. The caller reports that all three cases also passed in every locally collected PR #7990 run before this head. This report did not check those runs.
`cubrid-tcc` reports flakiness `UNKNOWN` for both cases.

### Coverage limits

- The current occurrence (run `40323508581`) is not indexed.
- The refresh window (2026-10-19 to 2026-10-26 13:30 UTC) is partly indexed: 763 of 1031 enumerated runs are missing, and 101 shards are missing. Earlier failures of F1 or F2 in the missing runs are possible.
- The index records no attempt or job identity for many observations (`attempt_unresolved`).

## Head-only delta against the previous head

`git diff --stat 5a65b2807..52987c654` changes 14 files.
The Engine source files are:

- `src/query/vacuum.c`
- `src/query/vacuum_oos.cpp`
- `src/storage/heap_file.c`
- `src/transaction/locator_sr.c`
- `src/transaction/log_applier.c`

The other files are OOS unit tests, scripts, and CMake files.
F1–F3 use these operations: client-server inserts into a single-column index, server-side loaddb error reporting, and TDE trace logging across two server restarts.
The F1 subsection lists the reasons why each Engine change is outside those paths.
Each Engine change applies to one of these conditions:

- standalone mode
- a primary-key update with foreign-key children
- a multi-column key
- out-of-memory handling
- interrupted vacuum jobs
- the HA applier

The vacuum boot hint (`interrupted_partial_blockid`) can mark one consumed block as interrupted in server mode. No observed signature involves vacuum.

## Addendum: rerun `40334404336` outcome

Added 2026-10-26 after the rerun finished. This addendum does not change the decision boundary above, which covers the collector snapshot.

**The required collection did not validate the rerun.**
The new `cubrid-ci collect 7990 --commit 52987c654b6f04734cad01c11c80c7f30358b33c` (Action 1) exited `4`, with all three suites `collection_failed`:
- `test_sql` and `test_medium`: `integrity/malformed: plan.tsv is empty`. The rerun carried both suites forward without planning any cases for them.
- `test_shell`: `unavailable: shard acquisition stopped after another mandatory shard failed`.

These failures limit the collector for rerun-shaped runs. They are not CI verdicts.

**GitHub job-log observation (raw, not collector-validated):**
- The PR's required gha-ci statuses for `52987c654b6f04734cad01c11c80c7f30358b33c` all report `SUCCESS` from run `40334404336`: `build (release)`, `test_shell`, `test_sql` and `test_medium`.
- Shell shard job `121612848221` (`shard shell 00`) logs `SHA: 52987c654b6f04734cad01c11c80c7f30358b33c`.
- It ran exactly the three failed cases, each with `[OK]`:
  - `shell/_06_issues/_12_2h/bug_bts_7456_1/cases/bug_bts_7456_1.sh`
  - `shell/_35_cherry/issue_21654_server_side_loaddb/syntax/cases/syntax.sh`
  - `shell/_36_damson/cbrd_23608_tde/temp_enc_06/cases/temp_enc_06.sh`
- Its summary line is `assigned 3 / run 3 / failed 0 / skipped 0`.

**What this changes:**
- **F1 and F2** now each have a FAIL (run `40323508581`) and a PASS (run `40334404336`) on the same Engine build `52987c65`, with no source or testcase change in between. This is the pair Action 1 required for a flakiness claim. Together with their history (0 failures in 186–187 earlier runs) and the falsifier analysis above, F1 and F2 are best classified as intermittent test or environment failures, PR relation `unlikely`.
- **F3** passed on the same build and keeps its separate testcase-defect mechanism.
- **Formal limit:** under this skill's gate, a full classification still needs a collector-validated bundle. The pass/fail pair above comes from raw job logs.

**Updated actions:**
1. Treat the PR7990 gha-ci merge gate for `52987c654` as satisfied by run `40334404336`. Keep this report's flakiness classification provisional until a collector release validates rerun-shaped runs.
2. Report the collector limitation (an empty `plan.tsv` for carried-forward suites under `/run rerun`) to `cubrid-ci` as a follow-up.
3. Keep F3 (`temp_enc_06` only searching `_latest.err`) as separate testcase-defect follow-up in `cubrid-testcases-private-ex`.

## Unknowns

- The validated verdict of rerun `40334404336`.
- Final `test_sql` and `test_medium` verdicts for this head from a validated collection. The caller reported both as `SUCCESS` in run `40323508581`. This report did not collect those suites for that run.
- The baseline `test_sql` verdict. Its collection failed the integrity check.
- The CTP helper version on each side.
- The process IDs and timings for F1, and the client poll timing for F2.

## Actions

1. **Highest priority:** after rerun `40334404336` is terminal, run one new `cubrid-ci collect` for the same exact head. Validate the observation. Check that the three exact cases ran on Engine `52987c65` and record their verdicts.
   - If all three cases pass on Engine `52987c65`, F1 and F2 have a comparable PASS and FAIL pair. A flakiness claim needs that pair. F3 has a testcase mechanism with source and log evidence.
   - If a case fails with the same signature again, do the next action in its subsection.
2. Record F3 as a testcase defect in `cubrid-testcases-private-ex` for separate follow-up. It does not waive the CI requirement for this PR.
3. Do not treat this warning report as a stale-result substitute for the new collection.

## Evidence files

| Evidence | Path |
|---|---|
| Head bundle (both observations) | `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7990/52987c654b6f04734cad01c11c80c7f30358b33c/` |
| Current observation | `observations/20261026T135320.772199222Z-355615-0/` |
| Retained observation | `observations/20261026T133639.640157573Z-269289-0/` |
| Retained `test_shell` summary | `providers/github-actions/runs/40323508581/attempts/1/test_shell/summary.json` |
| F1 evidence | `…/test_shell/failures/shell_06_issues_12_2h_bug_bts_7456_1_cases_bug_bts_7456_1_sh-936ab61fa6/` |
| F2 evidence | `…/test_shell/failures/shell_35_cherry_issue_21654_server_side_loaddb_syntax_cases_syntax_sh-a4dbc0eefb/` |
| F3 evidence | `…/test_shell/failures/shell_36_damson_cbrd_23608_tde_temp_enc_06_cases_temp_enc_06_sh-c0ae49871a/` |
| Baseline bundle | `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/c1dfe7e8719d254d61b33fc513d704f4f4f0a8b2/` |
| Baseline observation | `observations/20261026T135747.342525805Z-434544-0/` |
| Baseline `test_shell` summary | `providers/github-actions/runs/39979262220/attempts/1/test_shell/summary.json` |
| Schemas | `/home/vimkim/gh/cubrid-ci/schema/` at `9536bd3c2867` |
| Testcase source | `/home/vimkim/gh/cubrid-testcases-private-ex/develop`, read with `git show <sha>:<path>` |

This report includes no credentials, authorization headers, signed evidence-server URLs, or binary artifacts.
