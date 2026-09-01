# CI Failure Analysis: PR #7617 at `bd0766d`

## Executive Summary

The exact PR-head snapshot is not green: `test_medium` passed all 975 tests, `test_sql` failed 14 of 17,457 tests, and `test_shell` was not available. There are no `error` or `unknown` test results.

The 14 SQL failures form five signatures. Two tests expose an OOS feature-branch compatibility problem for a row containing many LOB locators; the server rejects the 18,036-byte record with `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`. The other 12 failures are error-code, numeric-rendering, or query-plan-output differences. Exact source inspection shows no behavioral connection between these signatures and PR #7617's empty-page reclamation paths, so no source or answer-file change is recommended in this PR. This is a scope attribution, not a claim that the failures are acceptable: the SQL baseline and missing shell result remain merge/QA warnings.

## CI Snapshot

| Suite | State | CircleCI job | Tests | Failures | Errors | Unknown | Warning |
|---|---|---:|---:|---:|---:|---:|---|
| `test_medium` | passed | [151290](https://circleci.com/gh/CUBRID/cubrid/151290) | 975 | 0 | 0 | 0 | — |
| `test_sql` | failed | [151293](https://circleci.com/gh/CUBRID/cubrid/151293) | 17,457 | 14 | 0 | 0 | Five failure signatures require feature-branch baseline follow-up. |
| `test_shell` | unavailable | — | — | — | — | — | No exact-head shell result was present; no pass/fail conclusion is possible. |

The prerequisite [release build 151287](https://circleci.com/gh/CUBRID/cubrid/151287), [debug build 151289](https://circleci.com/gh/CUBRID/cubrid/151289), and [download-build 151291](https://circleci.com/gh/CUBRID/cubrid/151291) all passed.

## Evidence Scope

- PR: [CUBRID/cubrid#7617](https://github.com/CUBRID/cubrid/pull/7617)
- Exact source commit: `bd0766dbb8e7e1d5f1f6f87824aa8819233991e9`
- Base branch: `feat/oos`; merge-base: `140fc5ef640760f1664854f713348df008a43ca0`
- Collection time: `2026-09-01T11:36:39.749412682Z`
- Collector: `cubrid-ci 0.1.0 (3e9502f72350, release)`
- Durable evidence: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26786/bd0766d/`
- SQL testcase revision: `3e619db57b44dff8dd3870c71f2314beded281a0`
- SQL text artifacts: 77 files, 102,945,039 bytes; exact testcase/answer sources were downloaded for all 14 failures.

The local CUBRID checkout matches the tested commit before the review fixes. Attribution uses the exact PR diff (`140fc5ef6...bd0766dbb`) and the collected logs. Local uncommitted review fixes are not part of this CI snapshot.

## Failure Inventory

| Test | Result | Observed signature | Category | PR relation | Confidence |
|---|---|---|---|---|---|
| `sql/_13_issues/_14_1h/cases/bug_bts_10516.sql` | failure | Wide all-types insert rejected; server reports record 18,036 > 16,236 after OOS demotion. | Wide LOB row | unlikely | high |
| `sql/_15_fbo/_02_qa_test/cases/fbo_ddl02.sql` | failure | Same insert and server error as `bug_bts_10516`; later statements see zero rows. | Wide LOB row | unlikely | high |
| `sql/_13_issues/_21_2h/cases/cbrd_23816.sql` | failure | Trace says `gather: row by row`, expected `mergeable list`. | Parallel-plan trace | unlikely | high |
| `sql/_13_issues/_24_1h/cases/cbrd_25361.sql` | failure | Same parallel gather trace difference. | Parallel-plan trace | unlikely | high |
| `sql/_36_guava/cbrd_25447/cases/cbrd_25447.sql` | failure | Same parallel gather trace difference. | Parallel-plan trace | unlikely | high |
| `sql/_36_guava/cbrd_26571/cases/cbrd_26571.sql` | failure | One scan changes from `noscan ... agl` to `heap`. | Access-plan trace | unlikely | high |
| `sql/_13_issues/_12_1h/cases/bug_bts_6460.sql` | failure | Integer division overflow is `Error:-458`, expected `Error:-731`. | Error-code baseline | unlikely | high |
| `sql/_26_features_920/issue_11087_median/cases/11087.sql` | failure | Integral median values render without `.0`/scientific notation. | Numeric rendering | unlikely | high |
| `sql/_26_features_920/issue_11087_median/cases/11087_7.sql` | failure | `1.0`, `2.0` render as `1`, `2`. | Numeric rendering | unlikely | high |
| `sql/_27_banana_qa/issue_11088_percentile_cont/_01_aggregate_function/cases/_00_from_dev.sql` | failure | `1.23456789E8` renders as `123456789`. | Numeric rendering | unlikely | high |
| `sql/_27_banana_qa/issue_11088_percentile_cont/_01_aggregate_function/cases/_02_numeric2.sql` | failure | Integral percentile values lose `.0`. | Numeric rendering | unlikely | high |
| `sql/_27_banana_qa/issue_11088_percentile_cont/_01_aggregate_function/cases/_09_ps.sql` | failure | Integral percentile values lose `.0`. | Numeric rendering | unlikely | high |
| `sql/_27_banana_qa/issue_11088_percentile_cont/_02_analytic_function/cases/p_cont_bit_lob.sql` | failure | Integral percentile values lose `.0`; LOB data itself matches. | Numeric rendering | unlikely | high |
| `sql/_27_banana_qa/issue_11088_percentile_cont/_02_analytic_function/cases/p_cont_partition_hash.sql` | failure | `4.0` renders as `4`. | Numeric rendering | unlikely | high |

## Root-Cause Analysis

### Wide LOB row rejection (2 tests)

**Observed:** Both tests submit the same all-column-types row. The server log records `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE (-1381)` at `heap_file.c`, stating that the 18,036-byte record still exceeds the 16,236-byte maximum after eligible variable-length columns were moved to OOS. The remaining test output is cascading fallout from the failed initial insert.

**Inferred:** This is an OOS feature-branch compatibility gap, but not an empty-page-reclaim regression. Across PR #7617, `src/storage/heap_oos.cpp` changes only an explanatory comment; the record sizing, candidate selection, and demotion logic are unchanged. Reclamation runs after committed deletion or immediately before OOS file growth, while this failure occurs while forming the first oversized heap record.

**Falsifier:** A reproduction showing that the insert succeeds at merge-base `140fc5ef6` with the same testcase and configuration would invalidate the attribution and require a PR-level bisect.

**Next action:** Track the wide-row behavior against the OOS feature branch and decide whether many LOB locators must remain supported, be demoted differently, or have an explicit compatibility limitation. Do not update the answer files to expect rejection without that product decision.

### Parallel-plan trace drift (3 tests)

**Observed:** Expected `gather: mergeable list`; actual output is `gather: row by row` in otherwise matching trace fragments.

**Inferred:** PR #7617 changes storage reclamation and vacuum/OOS bookkeeping, not parallel query execution, optimizer selection, or trace formatting. The relation is therefore unlikely.

**Falsifier:** A changed call path from an OOS/file-manager hunk into parallel plan construction, or a merge-base comparison isolating the difference to this PR, would invalidate the conclusion.

**Next action:** Compare the intended parallel-query baseline on `feat/oos` before changing trace answer files.

### Access-plan trace drift (1 test)

**Observed:** `cbrd_26571.sql` expects a `noscan` access using `agl: pk_tb_id`; the exact snapshot reports a heap scan.

**Inferred:** No optimizer, query executor, or adaptive group lookup code is changed by the PR. An empty-page reclamation path cannot influence compile-time access-plan selection for this testcase.

**Falsifier:** A deterministic exact-commit reproduction whose plan flips when only PR #7617 is reverted would disprove the inference.

**Next action:** Validate the expected `feat/oos` optimizer baseline independently.

### Error-code baseline drift (1 test)

**Observed:** Five integer-division overflow statements return `-458` instead of expected `-731`.

**Inferred:** The PR neither changes arithmetic evaluation nor renumbers these error codes. The relation is unlikely.

**Falsifier:** A PR hunk affecting the corresponding arithmetic error path or error mapping would require reclassification.

**Next action:** Confirm the intended error code on the base branch, then update implementation or testcase expectation in the owning change.

### Numeric rendering drift (7 tests)

**Observed:** Result values remain numerically equal, but integral `MEDIAN`/`PERCENTILE_CONT` values render without a decimal suffix or scientific notation.

**Inferred:** The diff has no changes to aggregate typing, numeric domains, serialization, CSQL display formatting, or client conversion. `p_cont_bit_lob.sql` includes LOB columns, but its LOB values match; only the independent percentile column differs.

**Falsifier:** Type metadata from an exact reproduction showing that OOS storage changes the aggregate result domain would disprove this conclusion.

**Next action:** Establish the intended numeric display/type baseline before any answer-file update.

## Recommended Actions

1. Do not modify PR #7617 for these 14 SQL failures; record them as feature-branch baseline follow-up, as agreed during review.
2. Before merging the feature branch, resolve or explicitly accept the two wide-row OOS compatibility failures and the 12 baseline expectation differences.
3. Obtain an exact-head `test_shell` result; its current absence is a verification gap, not a pass.
4. Re-run the exact-head CI after the local review fixes are committed to the PR, because this snapshot predates those fixes.

## Evidence and Limitations

The analysis inspected the exact manifest and suite summaries; all 14 `metadata.json`, `message.txt`, and `diff.txt` records; artifact/source indexes; exact testcase and answer sources; and targeted server logs for the wide-row failures. Counts reconcile to 14 failures, 0 errors, and 0 unknown results.

`test_shell` was missing from the exact snapshot. No shell behavior or crash/restart/concurrent CTP acceptance scenario can be inferred from the passing medium suite. The report does not claim that feature-branch baseline failures are harmless, and it does not recommend answer-file churn without an intended-behavior decision.
