# CI Analysis: PR #7927 at `34a9072` (CBRD-27089)

- **PR**: [CUBRID/cubrid#7927](https://github.com/CUBRID/cubrid/pull/7927), `[CBRD-27089] Defer OOS writes until destination heap selection`
- **Commit**: `34a9072a19fdd5baf420273992c136119e719503` (the review-fix head, following the [two-axis review](code_review_290aa50_opus.md))
- **Analyst**: Claude Opus 5.5 (AI-assisted). The analysis is read-only: no reproduction was run and no source was edited.
- **Date**: 2026-09-23

## 1. Executive summary

All three suites finished and all three failed, with 20 testcase failures (medium 3, SQL 3, shell 14). The trigger was `/run all`, posted 2026-09-23T08:23:09Z.

**None of the 20 is attributed to this PR with more than low plausibility.** They fall into four groups:

| Group | Tests | Cause | PR relation | Confidence |
|---|---|---|---|---|
| A. Testcase branch behind develop's CBRD-26459 answer updates | 7 | Engine commit `9ee8bac8b` (upgradedb and system-metadata versioning, arrived through the develop merge `b8f3c4807`) changes the log header, the `cubrid` usage text and parser errors. `tc/pr-7927` lacks the matching testcase updates. | unlikely | high (6), medium (1) |
| B. Failures seen before this change | 10 | Earlier report reproduced them on the parent, or they also fail on base run `7008beee0` | unlikely | medium–high |
| C. Environment or timing, one observation each | 3 | Timing-dependent kill check; one extra temp-volume extension; an assertion core in temp-file destroy | unlikely | low–medium |
| D. `tc/pr-7927` lacks `tc/pr-7990`'s OOS expectation update `8be3e498c` | overlaps B (2 SQL) | Answers for `bug_bts_10516` and `fbo_ddl02` differ between the two testcase branches | unlikely | medium |

**The intended-rejection failure `partition_tbls.sh` from the `512b361` report now passes.** The shell run used the updated testcase commit `4bff89b6a`.

**Decision boundary.** This snapshot supports "no PR-introduced regression identified". It does **not** prove absence:

- Group C are single observations.
- The core in `bug_bts_6938` is a real assertion failure, even though it sits in code the PR does not touch.

## 2. CI snapshot

All three suites come from GitHub Actions `gha-ci`, [run 35836821909](https://github.com/CUBRID/cubrid/actions/runs/35836821909), attempt 1.

| Suite | State | Verdict | Planned | Run | Unrun | Passed | Failures | Errors | Skipped |
|---|---|---|---|---|---|---|---|---|---|
| test_medium | completed | FAILURE | 975 | 975 | 0 | 972 | 3 | 0 | 0 |
| test_sql | completed | FAILURE | 17466 | 17466 | 0 | 17463 | 3 | 0 | 0 |
| test_shell | completed | FAILURE | 3286 | 3256 | 0 | 3242 | 14 | 0 | 30 |

For each suite, tests = passed + failures + errors + skipped, planned = run + unrun + skipped, and the number of failure records equals failures + errors.

## 3. Evidence scope

- **Collector**: `cubrid-ci 0.2.0 (31bd609fda78, release)`. The collection exit code was 0, all three suites are `completed`, and the error list is empty. Collected at 2026-09-23T09:04:14Z.
- **Evidence directory**: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503`
- **Testcase revisions**:
  - SQL and medium: `cubrid-testcases` `tc/pr-7927@996eefacee79`
  - Shell: `cubrid-testcases-private-ex` `tc/pr-7927@4bff89b6a`
- **Validation**:
  - The command result, the manifest, the three summaries and all 20 failure metadata files validate against the v2 schemas.
  - Identity is consistent: repository, PR, commit, output directory, and run/attempt for each suite.
  - Every declared message and diff file exists.
  - `raw/index.json` validates against the schema committed at collector commit `31bd609`. It does **not** validate against the working tree of `~/gh/cubrid-ci/schema`, because an uncommitted edit there adds a required `summary_sha256` field that release 0.2.0 does not emit.
  - This is a skew between the schema working tree and the collector version, not an evidence defect. It is recorded here as a limitation.
- **Comparison points**:
  - Base-branch run on PR #7990 at `7008beee0`, an ancestor of merge base `b8f3c4807` that is 16 commits earlier, using testcases `tc/pr-7990@8be3e498c`. That run had medium 0, SQL 0 and shell 3 failures (`cbrd_27064`, `cbrd_27075`, `bug_bts_13242`).
  - The prior classification in [ci_analysis_report_512b361_codex.md](ci_analysis_report_512b361_codex.md).
- **Limitations**:
  - `7008beee0` predates the develop merge, so it is not an exact parent for this commit.
  - No parent re-run was made at `b8f3c4807` with `tc/pr-7927` testcases.
  - Group C was not reproduced.

## 4. Failure inventory

| # | Suite | Testcase | Observed signature | Group | PR relation | Confidence |
|---|---|---|---|---|---|---|
| 1 | medium | `_02_xtests/cases/to_char_order_by.sql` | A SELECT without ORDER BY returns a different row permutation | B | unlikely | medium |
| 2 | medium | `_02_xtests/cases/to_number_order_by.sql` | same | B | unlikely | medium |
| 3 | medium | `_02_xtests/cases/to_timestamp_order_by.sql` | same | B | unlikely | medium |
| 4 | sql | `_13_issues/_14_1h/cases/bug_bts_10516.sql` | Differs from the answer; the answer differs between `tc/pr-7990`, `tc/pr-7927` and develop | B/D | unlikely | medium |
| 5 | sql | `_15_fbo/_02_qa_test/cases/fbo_ddl02.sql` | Differs from the answer; the answer differs between `tc/pr-7990`, `tc/pr-7927` and develop | B/D | unlikely | medium |
| 6 | sql | `_33_elderberry/cbrd_23844/cbrd_24337/cases/cbrd_24337.sql` | `create table _db_class` returns `Error:-493` (ER_PT_SYNTAX); the answer expects `-494` | A | unlikely | medium |
| 7 | shell | `_32_features_930/.../_01_basic_log/cases/_01_basic_log.sh` | Log header output has the new `System_metadata_version` row | A | unlikely | high |
| 8 | shell | `_32_features_930/.../_02_relative_path/_01_csql/cases/_01_csql.sh` | same | A | unlikely | high |
| 9 | shell | `_32_features_930/.../_03_absolute_path/_01_self_log/cases/_01_self_log.sh` | same | A | unlikely | high |
| 10 | shell | `_06_issues/_25_1h/cbrd_25478/cases/cbrd_25478.sh` | `System_metadata_version` row (4 blocks) | A | unlikely | high |
| 11 | shell | `_06_issues/_15_1h/bug_bts_16378/cases/bug_bts_16378.sh` | `System_metadata_version` row | A | unlikely | high |
| 12 | shell | `_06_issues/_15_1h/bug_bts_15912/cases/bug_bts_15912.sh` | `cubrid` usage lists the new `upgradedb` utility | A | unlikely | high |
| 13 | shell | `_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | Also fails on base `7008beee0` | B | unlikely | high |
| 14 | shell | `_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | Also fails on base `7008beee0` | B | unlikely | high |
| 15 | shell | `_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh` | Reproduced on the parent in the `512b361` report | B | unlikely | medium |
| 16 | shell | `_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh` | Reproduced on the parent in the `512b361` report | B | unlikely | medium |
| 17 | shell | `_39_fig_cake/.../cbrd_25080/cases/cbrd_25080.sh` | Reproduced on the parent in the `512b361` report | B | unlikely | medium |
| 18 | shell | `_06_issues/_18_1h/bug_bts_14305/cases/bug_bts_14305.sh` | Check 1 NOK: the csql session interrupted by `kill 1` did not record an abort message | C | unlikely | low |
| 19 | shell | `_28_features_844/issue_11202_temp_volume_create/cases/...sh` | One extra `DISK_EXTEND` event pair for TEMPORARY_VOLUME | C | unlikely | low |
| 20 | shell | `_06_issues/_12_2h/bug_bts_6938/cases/bug_bts_6938.sh` | **cub_server core**: `assert_release (false)` at `file_manager.c:4321` in `file_destroy`, reached from `file_temp_retire` via `qmgr_free_query_temp_file` in `xqmgr_execute_query` | C | unlikely | medium |

## 5. Root-cause analysis

### A. Testcase branch behind develop's CBRD-26459 updates (7 tests: #6–#12)

- **Observed**
  - Engine commit `9ee8bac8b` ([CBRD-26459] upgradedb, #7773) is an ancestor of the merge base `b8f3c4807`. It is not an ancestor of `7008beee0`.
  - At `34a9072a1`, the new log-header field is defined at `src/parser/show_meta.c:174` and printed at `src/transaction/log_manager.c:6348`.
  - `9ee8bac8b` changes `src/base/error_code.h`, the message catalogs and two parser files.
  - In the private testcases, `origin/develop` has `53cb2cca5` ([CBRD-26459] #3964), and its `_01_basic_log` answer contains `System_metadata_version`. `tc/pr-7927@4bff89b6a` does not contain `origin/develop`.
  - In the public testcases, the `origin/develop` answer for `cbrd_24337` expects `Error:-493`.
  - The PR diff (`origin/feature/oos-merge...34a9072a1`) touches no file under `src/parser` or `src/object`.
- **Inference**: these seven failures come from the develop merge, not from deferred OOS writes. The testcase branches were forked before the matching answer updates reached develop.
- **Unknowns**: whether `bug_bts_15912`'s develop answer lists `upgradedb` under the same path (the develop answer check at this path found no match), and why the `-493` parser behaviour exists.
- **Falsifier**: the same seven tests failing on `b8f3c4807` with develop-synced testcases, or passing on it with `tc/pr-7927`.
- **Next action**: sync `tc/pr-7927` in both testcase repositories with their `origin/develop`, then re-run CI.

### B. Failures seen before this change (10 tests: #1–#5, #13–#17)

- **Observed**
  - `cbrd_27064` and `cbrd_27075` also fail on base `7008beee0`.
  - The other eight are listed in the `512b361` report as reproduced on the parent `38093ea85`.
  - Medium tests #1–#3 differ only in the row order of a SELECT without ORDER BY. For example, the answer's `3,5,1,2,4` versus the actual `4,1,2,3,5` in `to_char_order_by.sql`. That order depends on where the suite's shared database has free heap space.
  - The medium `.sql` and `.answer` files are byte-identical between `tc/pr-7990@8be3e498c` and `tc/pr-7927@996eeface`, yet base `7008beee0` passed them.
- **Inference**: these are dependent on environment, database state or testcase branch, and not specific to this PR. The medium order depends on the pages allocated by earlier tests in the same shard. So a PR that changes record sizes or placement could shift it, but the parent reproduction argues against a PR-only cause.
- **Unknowns**: medium has no exact-parent comparison at `b8f3c4807` using the same shard layout.
- **Falsifier**: medium #1–#3 passing on `b8f3c4807` in the same shard with `tc/pr-7927`. That would make a PR placement effect plausible.
- **Next action**: optional. Run a parent CI (`b8f3c4807`, `tc/pr-7927`) if medium ordering must be excluded.

### C. Environment or timing, one observation each (3 tests: #18–#20)

- **Observed**
  - `bug_bts_14305` depends on `sleep 2` timing between a 200k-statement csql client and `kill 1`.
  - `issue_11202` differs by one temp-volume extension event pair.
  - `bug_bts_6938` hit `assert_release (false)` in `file_destroy`: `disk_unreserve_ordered_sectors` failed while retiring a query temp file (`is_temp=true`). The test runs 100 CAS clients against a 20 MB volume and then force-kills the Java client.
  - The PR changes neither `file_manager.c` nor `query_manager.c`.
  - `bug_bts_6938` was previously recorded as a GitHub Actions-only flake on another PR (`cbrd-26357/ci_analysis_report_2940b1c_claude.md`), but that run had no core.
- **Inference**
  - #18 and #19 are timing or environment noise.
  - #20 is a real assertion core in temp-file teardown under interruption. It is most likely a pre-existing defect or a runner-resource issue, unrelated to OOS heap writes. Query temp files are not heap OOS files.
- **Unknowns**: the failing return code of `disk_unreserve_ordered_sectors`; whether the core is in the uploaded artifacts (the core path was on the runner, `/home/ERROR_BACKUP/AUTO_11.5.0.2632-34a9072_20260923_173859`).
- **Falsifier**: `bug_bts_6938` cores reproducibly on `34a9072a1` but not on `b8f3c4807` under the same shard conditions.
- **Next action**: re-run `bug_bts_6938` locally with `cubrid-test-shell-run` on `34a9072a1` and on the parent. If it reproduces on both, file it separately against temp-file teardown.

### D. Missing OOS expectation update from `tc/pr-7990` (overlaps #4, #5)

- **Observed**: `tc/pr-7990` contains `8be3e498c` ("[CBRD-26939] Update OOS merge regression expectations"), which `tc/pr-7927@996eeface` lacks. The answers for `bug_bts_10516` and `fbo_ddl02` differ across the three branches.
- **Inference**: once `tc/pr-7927` inherits the feature-branch testcase updates, the two SQL failures likely go away, as they did on base.
- **Falsifier**: the tests still failing after `tc/pr-7927` is rebased onto `tc/pr-7990` or `feature/oos-merge`.
- **Next action**: bring `8be3e498c` into `tc/pr-7927` together with the develop sync from group A.

## 6. Prioritized actions

1. **Sync `tc/pr-7927`** in both testcase repositories with `origin/develop` (CBRD-26459 answers) and with the feature branch's OOS expectation commit `8be3e498c`. Then re-run `/run all`. This is expected to clear 7–9 of the 20 failures.
2. **Check whether `bug_bts_6938` reproduces**, on `34a9072a1` and on the parent `b8f3c4807`, using the focused shell runner. Open a separate issue if it reproduces on the parent.
3. Optionally, run a parent CI at `b8f3c4807` with `tc/pr-7927` testcases to close the medium-order and remaining group B questions exactly.

## 7. Evidence files

Paths are relative to the evidence directory, under `providers/github-actions/runs/35836821909/attempts/1/`:

- `manifest.json` (at the directory root)
- `test_medium/summary.json`, `test_sql/summary.json`, `test_shell/summary.json`
- `*/raw/index.json`
- `*/failures/<stable_id>/{metadata.json,message.txt,diff.txt}` for all 20 failures; the diff was extracted for each
- Base comparison: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7990/7008beee0f145c5c5a4a6274e57bee7791f8f162/`

## 8. Follow-up

Action 1 was carried out on 2026-09-23:

- `cubrid-testcases-private-ex` `tc/pr-7927`: merged `origin/develop` as `527ebeafb`. No conflicts. The partition_tbls / bug_bts_11093 changes from `4bff89b6a` were kept.
- `cubrid-testcases` `tc/pr-7927`: merged `origin/develop` as `10d3f5a06`. No conflicts. Cherry-picked `8be3e498c` as `ca8d15a4c`. The tip checks out: `cbrd_24337.answer` expects `Error:-493`, and `bug_bts_10516.answer` and `fbo_ddl02.answer` match `8be3e498c`.
- CI was re-triggered with `/run all` at 2026-09-23T09:20:58Z on head `34a9072a1`: https://github.com/CUBRID/cubrid/pull/7927#issuecomment-5792263699
