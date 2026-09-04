# CI Failure Analysis: PR #7600 at `b871ea3`

## Executive Summary

CircleCI prerequisite builds and `test_medium` pass for exact source commit `b871ea386d2c5419b7abae07dda58b9b7f36377a`. Medium reports 975/975 successful tests. `test_sql` reports 17,384 successes and 60 answer/actual failures, with no errors or unknown results. None of the 60 failures is attributable to the CBRD-27089 diff: 30 already occur on validated feat/oos PR #7588 at the same testcase revision, and the other 30 exercise result formatting or optimizer behavior outside this PR's OOS write-routing paths. `test_shell` is still unavailable, so no shell conclusion is possible.

## CI Snapshot

| Suite | State | CircleCI job | Tests | Failures | Errors | Unknown | Warning |
|---|---|---:|---:|---:|---:|---:|---|
| `test_medium` | pass | [152363](https://circleci.com/gh/CUBRID/cubrid/152363) | 975 | 0 | 0 | 0 | none |
| `test_sql` | fail | [152364](https://circleci.com/gh/CUBRID/cubrid/152364) | 17,444 | 60 | 0 | 0 | all failures are answer/actual diffs |
| `test_shell` | unavailable | N/A | N/A | N/A | N/A | N/A | status missing or pending; shell may remain invisible while queued |

Prerequisites:

| Check | Result | CircleCI job |
|---|---|---|
| `ci/circleci: build` | pass | [152359](https://circleci.com/gh/CUBRID/cubrid/152359) |
| `ci/circleci: build_debug` | pass | [152362](https://circleci.com/gh/CUBRID/cubrid/152362) |

## Evidence Scope

- PR: https://github.com/CUBRID/cubrid/pull/7600
- Exact commit: `b871ea386d2c5419b7abae07dda58b9b7f36377a`
- Snapshot time: `2026-09-04T11:48:36Z`
- Collector: `cubrid-ci 0.1.0 (3e9502f72350, release)`
- Evidence: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/b871ea3`
- Testcase revision: `479cd5fbf74edc28a522f9762eb8c433f7104125`
- Collection mode: text artifacts with testcase sources. SQL downloaded 254 text artifacts (216,732,494 bytes) and all 120 referenced testcase/answer sources; medium had no failure artifacts.
- Historical comparison: PR #7588, commit `d9590749d9008ccfa237d89177e44533760f7337`, SQL job [146972](https://circleci.com/gh/CUBRID/cubrid/146972), same testcase revision. This is baseline evidence only, not the current result.

## Failure Inventory

Medium has 975 successes and no failure, error, skipped, or unknown testcase result. SQL has 60 failures and no error or unknown result. Each SQL failure appears exactly once below.

| Test | Observed signature | Category | PR relation | Confidence |
|---|---|---|---|---|
| `sql/_01_object/_03_virtual_class/_001_basic/cases/1079.sql` | identifier/error-code drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_01_object/_02_class/_001_basic/cases/1079.sql` | identifier/error-code drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_23_apricot_qa/_01_sql_extension3/_02_new_sql_types/_01_enum/cases/_18_adhoc_multiple.sql` | identifier/error-code drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_33_elderberry/cbrd_24011/cases/inst_num.sql` | derived-column alias drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_34_fig/cbrd_24042/cbrd_24258/cases/cbrd_24258.sql` | derived-column alias drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_34_fig/cbrd_24252/cases/cbrd_24252_31.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_13_issues/_25_1h/cases/cbrd_25801.sql` | derived-column alias drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_13_issues/_11_2h/cases/bug_bts_5861_2.sql` | optimizer plan drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_13_issues/_14_1h/cases/bug_bts_10516.sql` | OOS big-record error-code drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_13_issues/_14_1h/cases/bug_bts_12943.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_13_issues/_14_1h/cases/bug_bts_13158.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_13_issues/_14_1h/cases/bug_bts_13199.sql` | optimizer plan drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_13_issues/_12_2h/cases/bug_bts_8537.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_13_issues/_15_1h/cases/bug_bts_14002.sql` | optimizer plan drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_13_issues/_13_2h/cases/bug_bts_11008.sql` | identifier/error-code drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_13_issues/_13_2h/cases/bug_bts_11842.sql` | identifier/error-code drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_13_issues/_20_2h/cases/cbrd_21452.sql` | derived-column alias drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_13_issues/_20_2h/cases/cbrd_23665.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_13_issues/_17_1h/cases/cbrd_20857.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_13_issues/_17_1h/cases/cbrd_20865.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_13_issues/_23_1h/cases/cbrd_24843_4.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_13_issues/_23_1h/cases/cbrd_24906_1.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_13_issues/_23_1h/cases/cbrd_24906_2.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_13_issues/_23_1h/cases/cbrd_24906_3.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_13_issues/_21_2h/cases/cbrd_23816.sql` | answer/actual result drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_13_issues/_21_2h/cases/cbrd_24013.sql` | optimizer plan drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_13_issues/_11_1h/cases/bug_bts_4563_3.sql` | optimizer plan drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_13_issues/_24_1h/cases/cbrd_25098.sql` | optimizer plan drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_13_issues/_24_1h/cases/cbrd_25361.sql` | answer/actual result drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_13_issues/_12_1h/cases/bug_bts_6460.sql` | answer/actual result drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_26_features_920/issue_11087_median/cases/11087.sql` | numeric rendering drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_26_features_920/issue_11087_median/cases/11087_7.sql` | answer/actual result drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_14_mysql_compatibility_2/_04_table_related/_02_alter_change_column/_07_auto_incr/cases/1072.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_35_fig_cake/cbrd_24044/cbrd_25214/cases/cbrd_25214.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_35_fig_cake/cbrd_24044/cbrd_26419/cases/cbrd_26419.sql` | optimizer plan drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_35_fig_cake/cbrd_25748/cases/cbrd_25748.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_35_fig_cake/cbrd_25382/cases/cbrd_25382_1.sql` | optimizer plan drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_36_guava/cbrd_26104/cases/cbrd_26104.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_36_guava/cbrd_25776/cases/cbrd_25776.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_36_guava/cbrd_26522/cases/cbrd_26522.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_36_guava/cbrd_26258/cases/join_orderby_skip.sql` | optimizer plan drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_36_guava/cbrd_26258/cases/single_orderby_skip.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_36_guava/cbrd_25447/cases/cbrd_25447.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_36_guava/cbrd_26599/cases/cbrd_26599.sql` | optimizer plan drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_15_fbo/_02_qa_test/cases/fbo_ddl02.sql` | OOS big-record error-code drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_27_banana_qa/issue_11088_percentile_cont/_01_aggregate_function/cases/_00_from_dev.sql` | numeric rendering drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_27_banana_qa/issue_11088_percentile_cont/_01_aggregate_function/cases/_02_numeric2.sql` | answer/actual result drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_27_banana_qa/issue_11088_percentile_cont/_01_aggregate_function/cases/_09_ps.sql` | answer/actual result drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_27_banana_qa/issue_11088_percentile_cont/_02_analytic_function/cases/p_cont_bit_lob.sql` | answer/actual result drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_27_banana_qa/issue_11088_percentile_cont/_02_analytic_function/cases/p_cont_partition_hash.sql` | answer/actual result drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_05_plcsql/_01_testspec/_05_bug_fix/cases/19_user_cursor_system_view.sql` | answer/actual result drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_28_features_930/issue_13133_hash_query_profile/cases/hash_agg_query_profile.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_17_sql_extension2/_02_full_test/_03_alter_table/_01_alter_change/cases/alter_change_026.sql` | answer/actual result drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_18_index_enhancement_qa/_01_acceptance_test/cases/_01_covering_index_01.sql` | optimizer plan drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_08_javasp/cases/412-1.sql` | identifier/error-code drift | Historical feat/oos baseline | Unlikely | High |
| `sql/_19_apricot/_03_index_skip_scan/cases/_02_iss_4000.sql` | optimizer plan drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_19_apricot/_03_index_skip_scan/cases/_03_iss_700000.sql` | optimizer plan drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_19_apricot/_03_index_skip_scan/cases/_07_iss_4000_with_null.sql` | optimizer plan drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_19_apricot/_03_index_skip_scan/cases/_08_iss_700000_with_null.sql` | optimizer plan drift | Current branch/testcase drift | Unlikely | Medium-high |
| `sql/_31_cherry/issue_22162_more_json_functions/cases/json_table_group_concat.sql` | derived-column alias drift | Current branch/testcase drift | Unlikely | Medium-high |

## Root-Cause Analysis

### Historical feat/oos baseline drift (30 tests)

**Observed:** PR #7588 SQL job 146972 used the same testcase revision and failed exactly 30 tests. All 30 names are a subset of the current 60; 24 have byte-identical normalized diffs. The remaining six keep the same test-level mismatch while the actual value changes with later feat/oos history. The two OOS-aware cases, `bug_bts_10516.sql` and `fbo_ddl02.sql`, are in this historical set: their expected OOS+big-record error is `-1379`, while old feat/oos returned `-1380` and the current head returns `-1381`.

**Inferred:** These 30 failures predate the CBRD-27089 FORCE_OUTLINE fix and are unrelated to it. The error-number movement is consistent with branch-level error-code additions rather than OOS ownership behavior.

**Falsifier:** A validated pre-CBRD-27089 build at the same branch revision producing different results for any of these 30 would require reclassification. No such contradiction appears in the available bundles.

### Current branch/testcase result drift (30 tests)

**Observed:** The other 30 diffs cover derived-column aliases (`ca`/column names becoming `a_?`), optimizer plan choices (join order and index-skip scan becoming sequential scan), numeric rendering (`123456789` becoming `1.23456789E8`), and other answer-output changes. None of their downloaded testcase sources mentions OOS, `STORAGE FORCE_OUTLINE`, or `SHOW HEAP OOS`.

The CBRD-27089 diff from `origin/feat/oos` changes OOS record transformation and ownership routing in `heap_file.c`, `locator_sr.c`, and duplicate-key probe construction in `query_executor.c`; it does not change identifier limits, numeric formatting, SELECT optimizer rules, or testcase answers.

**Inferred:** These are also unlikely to be caused by this PR. The narrowest explanation is that current feat/oos behavior has moved beyond testcase revision `479cd5f` in several unrelated result/optimizer areas. Confidence is medium-high rather than high because no exact SQL run for bare base commit `2940b1cfb` is available.

**Falsifier:** Run one representative current-only case on both `2940b1cfb` and `b871ea3`. A failure only on `b871ea3` would connect that signature to this PR and require local diagnosis.

### Server-log fatal entry

**Observed:** Each node's `unittestdb` log contains a fatal `ER_LOG_UNKNOWN_TRANINDEX` from `heap_oos_begin_insert_publication`. Its stack is the intentional unit test `OosPublicationBeginMissingTdesLeavesBothSidesUntouched`; it is not a server crash during a failed SQL testcase. No collected log contains the CBRD-27089 signature `vacuum_oos_find_vfid_for_heap_record`, a HAS_OOS/VFID abort, or a new core-dump event.

## Recommended Actions

1. Do not change CBRD-27089 source or SQL answer files based on these 60 failures; current evidence classifies all as unlikely PR regressions.
2. If a green SQL status is required, compare a representative current-only case on bare `origin/feat/oos` and the PR head, then coordinate branch/testcase answer alignment separately.
3. Keep the existing `/run all` shell queue position. Refresh `test_shell` against the same full SHA when its status becomes available; do not post a duplicate trigger.

## Evidence and Limitations

The current medium and SQL results come from the exact PR head. The PR #7588 bundle is used only as an explicitly labeled baseline and was validated by PR URL, full commit, job number, base branch, and identical testcase revision.

All 60 current SQL failures, their extracted diffs, targeted logs, artifact index, and downloaded source index were inspected. The report does not claim the unavailable shell suite passed, failed, or is unrelated. Absence of a GitHub shell status while queued does not show that shell was omitted.
