# CBRD-27259 CI analysis: run 42865557030

- PR: https://github.com/CUBRID/cubrid/pull/8416 (base `feature/oos-merge`)
- Head: `89496263eb8abfc7e80098004371c03c5aab8376` (merge of base `50619ce53` plus the loader unit test fix)
- Run: https://github.com/CUBRID/cubrid/actions/runs/42865557030, attempt 1
- Testcases: `cubrid-testcases` `02e98026b` (`tc/pr-8416`), `cubrid-testcases-private-ex` `011410ce1` (`tc/pr-8416`)
- Observed: 2026-11-11 (Asia/Seoul)
- Collector: `cubrid-ci 0.2.0 (8f24902a757a, release)`

## Result

The run failed. One failure is caused by this PR. One is caused by the base. The SQL server crash and one shell recovery failure are not attributed. They did not reproduce locally.

| Failure | Relation to this PR | Confidence |
| --- | --- | --- |
| shell `cbrd_27381_standalone` case 5 | direct | high |
| shell `cbrd_27571` cases 2-5 | unlikely (also on base) | high |
| SQL shards 09 and 03: server fatal `log_fetch_from_archive` | unknown | low |
| shell `cbrd_27120_recovery` case 6 | unknown, PR code path unlikely | low |
| SQL `r_outer_join` (shard 09) | unlikely (also on base) | high |
| `test_sql_by_cci` shards | known issue | high |

## Evidence limits

This is a warning-level report for the collector evidence. `cubrid-ci collect` failed with exit 5: `invalid remote JSON from cubrid-pr-status --json --history 0: invalid type: null, expected a string at line 224 column 26`. `cubrid-ci verify` returned exit 3 with observation `unvalidated`. The collector bundle supports no regression or root-cause conclusion.

The attributions below use separately labeled read-only fallback evidence:

- GitHub job logs fetched with `gh api --allow-escape-sequences repos/CUBRID/cubrid/actions/jobs/<id>/logs`.
- The run's failure evidence on the CI artifact server under `runs/42865557030/<suite>/shard/<n>/`: `build.read`, `tc.read`, `tc.list`, `test-results/*.xml`, `artifacts/feedback.log`, and the SQL `ctp_log.tgz`. The server `.err` files and cores are not in the retained evidence.
- The merge-base baseline from `cubrid-ci collect-base`: target `feature/oos-merge` at `50619ce53`, which is also the merge base. Its `test_shell` summary (run 42819814597) is validated. Its `test_sql` is `collection_failed` (run 42785110884), so SQL base comparisons use that run's job logs only.

## Suite states

| Suite | State | Failed shards |
| --- | --- | --- |
| build (release, debug) | success | none |
| test_medium | success | none |
| test_sql | failure | 09 and 03 cancelled at the 2-hour job limit after a server fatal |
| test_shell | failure | 05, 32, 40 |
| test_sql_by_cci | failure | 03-07, 09 (known issue) |

## Failure analysis

### 1. `cbrd_27381_standalone` case 5: direct

Observed. Case 5 failed with `wide keys: the rows failed: ERROR: The record cannot be stored because its size (50040 bytes) exceeds the maximum record size (16236 bytes) ...`. That is message 1396 (`ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`). The case creates `r_w (id int, b bit(400000))` and inserts 50,000-byte fixed `BIT` values (`shell/_40_guava/cbrd_27381_standalone/cases/cbrd_27381_standalone.sh` lines 200-223 at `011410ce1`). The base shell run passed this case.

Inference. The PR now rejects every user-class row that would become `REC_BIGONE`. A fixed `BIT(400000)` column cannot move to OOS, so the row is rejected. The behavior is intended. The testcase came in with the base merge (testcase commit `5bae5fcea`, CBRD-27381).

Falsifier. A local run of case 5 that inserts the rows without error.

Next action. Change the testcase on `tc/pr-8416` and keep its purpose, which is index keys wider than the 64K sort buffer. One option follows the earlier SQL fixes: declare `b bit varying(400000)` and insert `cast (... as bit(400000))`. The row then moves the value to OOS, and the index key stays 50,000 bytes. A local run must confirm that the index build still takes the wide-key path.

### 2. `cbrd_27571`: also on base

Observed. `cub_server` failed the assertion at `log_append_compensate_internal` (`log_manager.c:3214`) with `rcvindex=RVDK_LINK_PERM_VOLEXT` during restart recovery. The validated base shell summary (run 42819814597) lists this testcase as its only error.

Inference. The testcase came in with the base merge (private testcase commit `c8e675d18`). Its engine fix is CUBRID PR #8284 (CBRD-27571), which is not merged.

Falsifier. A base run that passes this testcase without PR #8284.

Next action. None for this PR. It fails on every `feature/oos-merge` head until PR #8284 merges.

### 3. SQL server fatal `log_fetch_from_archive`: unknown

Observed.

- Shard 09 crashed during `sql/_36_guava/cbrd_27478/cases/cbrd_27478.sql` (case 411 of 524), 11 minutes after the database was created.
- Shard 03 crashed during `sql/_13_issues/_26_2h/cases/cbrd_27732_merge.sql` (case 2178 of 2881), 9 minutes after it was created.
- Both printed `LOG FATAL ERROR: log_fetch_from_archive`. Each restart then failed with `Unable to mount disk volume "/home/CUBRID/databases/basic/basic_lgar000"`. Each remaining case timed out after 3 minutes.
- The base SQL run (42785110884) showed no fatal in any shard. Its shard 09 ran `cbrd_27478` and failed only `r_outer_join` and `cbrd_27762`.
- The earlier PR run 42770278025 (PR on the previous base) showed no fatal.
- Locally, a native testkit run of shard 09's directories (`_33_elderberry`, `_34_fig`, `_35_fig_cake`, `_36_guava`) at the head build completed with no fatal. It failed only `r_outer_join` and `cbrd_27762`, the same two cases as the base shard 09. The attempt is `/home/vimkim/tk/r9`. No `basic_lgar000` was created locally.

Inference. A server needed an archived log page after the active log had wrapped and the archive was gone (`log_max_archives = 0` in the CTP configuration). Only the combination of this PR and the new base showed it, in one run. Two shards crashing alike makes chance less likely, but one run does not separate a defect from an environment effect. The local run never wrapped the log, so it could not test the trigger.

Unknowns. The server `.err` files (`basic_20261111_0246.err`, `basic_20261111_0244.err`) are not retained. Which reader needed the archived page (vacuum, rollback, or another reader) is unknown.

Falsifier. A rerun of `test_sql` on the same head with no fatal in any shard makes a deterministic PR defect unlikely.

Next action. Rerun `test_sql` once on this head. If the fatal returns, reproduce it locally with a small log volume so the log wraps, keep the server `.err`, and find the reader.

### 4. `cbrd_27120_recovery` case 6: unknown

Observed. Case 6 printed `shard_count=1 recovery: ts [4000] -> [2000], tu must be empty but holds [0], undo transactions=[10]`. Table `ts` had 4000 committed rows before the server was killed and 2000 after recovery. The base shell run passed this testcase. The history store shows 6 passes and no failures through 2026-11-02, and its data is stale. Locally at the head build, case 6 passed 3 of 3 times (`/home/vimkim/tk/q1`-`q3`). Case 5 failed locally all 3 times with `kill landed in the abort=[missed]`, which is a local timing miss.

Inference. The CI symptom is loss of committed rows after crash recovery. The rows are `varchar(200)` rows far below a page, so the PR's record-size rejection does not apply to them. The PR's other code paths for such rows are not shown to change. This is a low-confidence, single-occurrence result.

Falsifier. A repeat of the case 6 failure on the base build would clear the PR. A repeat only on the head build would implicate it.

Next action. Watch this testcase in the next run. If it fails again, run it repeatedly on both the base and head builds and keep the server `.err`.

### 5. `r_outer_join`: also on base

Observed. `sql/_33_elderberry/cbrd_24042/cbrd_24182/cases/r_outer_join.sql` failed in head shard 09, in base shard 09, and locally.

Next action. None for this PR.

## Testcase history

`cubrid-tcc 0.3.0` data was last synchronized on 2026-11-02 and is stale. `cbrd_27120_recovery` had 6 passes in 6 runs. `cbrd_27381_standalone` is not indexed. History does not change the classifications above.

## Actions

1. Fix `cbrd_27381_standalone` case 5 on the private `tc/pr-8416` branch (direct).
2. Rerun `test_sql` on head `89496263e` to check the `log_fetch_from_archive` fatal.
3. Watch `cbrd_27120_recovery` case 6 in the next shell run.
4. Fix the `cubrid-ci collect` failure on the `null` field in the `cubrid-pr-status` JSON. It also failed for the previous head `6d6a01ef4`.

## Evidence files

- Job logs (in `/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-CBRD-27259-storage-force-inline/a6601308-f83e-4321-b1c9-7c2fa4bf1fc7/scratchpad`): `sql09.log`, `sql03.log`, `shell05.log`, `shell32.log`, `shell40.log`, and base job logs `base-<job>.log`.
- Artifact server copies: `/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-CBRD-27259-storage-force-inline/a6601308-f83e-4321-b1c9-7c2fa4bf1fc7/scratchpad/ev/`.
- Collector outputs: `/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-CBRD-27259-storage-force-inline/a6601308-f83e-4321-b1c9-7c2fa4bf1fc7/scratchpad/cia/` (`status.json`, `result.json`, `verify.json`, `base-result.json`, `base-verify.json`).
- Local runs: `/home/vimkim/tk/r9` (SQL shard 09 directories), `/home/vimkim/tk/q1`-`q3` (`cbrd_27120_recovery`).
