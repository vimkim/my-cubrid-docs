# CI Failure Analysis: PR #7927 at `be7c01a`

## Executive Summary

**Acceptance remains open.** SQL has 16 failures and medium has 3; all **19 failure cases reproduce independently on baseline `f4299ac0c`**, and all 19 local baseline/candidate actual-result files are byte-identical. No introduced failure is identified in this available snapshot. This is not a remote pass: shell has not executed, and branch-protection required-check visibility is unavailable.

## CI Snapshot

| Suite/check | State | Job | Tests | Success | Failure | Error / unknown | Warning |
|---|---|---|---:|---:|---:|---|---|
| test_medium | failed | [154504](https://circleci.com/gh/CUBRID/cubrid/154504) | 975 | 972 | 3 | 0 / 0 | Baseline reproduces all 3 |
| test_sql | failed | [154502](https://circleci.com/gh/CUBRID/cubrid/154502) | 17,459 | 17,443 | 16 | 0 / 0 | Baseline reproduces all 16 |
| test_shell | blocked | [154506](https://circleci.com/gh/CUBRID/cubrid/154506) | — | — | — | — | Prerequisite [154505](https://circleci.com/gh/CUBRID/cubrid/154505) not_running, no start time |
| release / debug build | success | [154503](https://circleci.com/gh/CUBRID/cubrid/154503) / [154501](https://circleci.com/gh/CUBRID/cubrid/154501) | — | — | — | — | Both completed |
| GitHub static checks | success | [Actions34576869752](https://github.com/CUBRID/cubrid/actions/runs/34576869752) | 5 checks | 5 | 0 | — | license, pr-style, code-style, cppcheck, memory-monitor-check |

Neither runtime suite reports skipped tests. A failed suite stays failed despite baseline attribution; it has not been relabeled unavailable. The shell job is independently blocked, rather than a failed run relabeled to satisfy acceptance.

## Evidence Scope

- PR: https://github.com/CUBRID/cubrid/pull/7927.
- Engine: `be7c01a6d2d05d461cb1e5b6e0127c15ffb1950b`; baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`.
- Collected 2026-09-11, using `cubrid-ci 0.1.0 (3e9502f72350, release)` with text artifacts and testcase sources. Collection does not wait for CI or post a trigger.
- SQL/medium testcase repository: `CUBRID/cubrid-testcases`, revision `b10727db4b9fd1b52aed49330634a3395d532048`. SQL checkout logs for all ten nodes select `develop`; 38 downloaded failing case/answer files match the isolated exact-revision checkout byte-for-byte. Medium per-file source records establish the same revision.
- Shell testcase revision: **unknown**, since its prerequisite/checkout has not run. Never substitute the SQL revision or a local shell HEAD.
- CircleCI workflow `6b1c5387-312d-476e-8d8c-2e876edeb77d`, pipeline `1e3677db-e1df-435e-8c29-e872cb9ad5d8`; pipeline VCS and SQL/medium/prerequisite job metadata match the full engine SHA.
- Actions run34576869752, attempt1, event `pull_request`: run/check metadata link to the pinned head. Checkout logs prove synthetic merge `5f262e378a43b68bc5b41b4d0478515d7d6d8fc1`, merging that head into baseline `f4299ac0c`; the static checks tested this merge checkout, not an assumed byte-identical source tree.
- Durable collector bundle: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/be7c01a/`. Separate API bundle: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/be7c01a-api-20260911/` (GitHub checks/statuses, checkout logs, pipeline/workflow/prerequisite metadata).

## Failure Inventory

Each remote failure occurs once below. SQL and medium have zero error/unknown records. Root-cause categories total 3 + 2 + 1 + 13 = 19.

| Suite | Test | Result | Observed signature | Category | Attribution / confidence | Evidence |
|---|---|---|---|---|---|---|
| test_medium | `medium/_02_xtests/cases/to_char_order_by.sql` | failure | Same rows, different order without ORDER BY | Unordered output (3) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/medium/_02_xtests/cases/to_char_order_by.diff) |
| test_medium | `medium/_02_xtests/cases/to_number_order_by.sql` | failure | Same rows, different order without ORDER BY | Unordered output (3) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/medium/_02_xtests/cases/to_number_order_by.diff) |
| test_medium | `medium/_02_xtests/cases/to_timestamp_order_by.sql` | failure | Same rows, different order without ORDER BY | Unordered output (3) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/medium/_02_xtests/cases/to_timestamp_order_by.diff) |
| test_sql | `sql/_33_elderberry/cbrd_24011/cases/nullable_outer_join.sql` | failure | Join/index/trace differs | Plan/trace expectations (13) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/sql/_33_elderberry/cbrd_24011/cases/nullable_outer_join.diff) |
| test_sql | `sql/_33_elderberry/cbrd_24011/cases/on_cond.sql` | failure | Join/index/trace differs | Plan/trace expectations (13) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/sql/_33_elderberry/cbrd_24011/cases/on_cond.diff) |
| test_sql | `sql/_33_elderberry/cbrd_24042/cbrd_24182/cases/dnf.sql` | failure | Join/index/trace differs | Plan/trace expectations (13) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/sql/_33_elderberry/cbrd_24042/cbrd_24182/cases/dnf.diff) |
| test_sql | `sql/_13_issues/_23_1h/cases/cbrd_24843_1.sql` | failure | Join/index/trace differs; unordered rows also differ | Plan/trace expectations (13) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/sql/_13_issues/_23_1h/cases/cbrd_24843_1.diff) |
| test_sql | `sql/_13_issues/_23_1h/cases/cbrd_24906_1.sql` | failure | Join/index/trace differs | Plan/trace expectations (13) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/sql/_13_issues/_23_1h/cases/cbrd_24906_1.diff) |
| test_sql | `sql/_13_issues/_23_1h/cases/cbrd_24906_2.sql` | failure | Join/index/trace differs | Plan/trace expectations (13) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/sql/_13_issues/_23_1h/cases/cbrd_24906_2.diff) |
| test_sql | `sql/_13_issues/_14_1h/cases/bug_bts_10516.sql` | failure | Expected INSERT success; actual Error:-1382, then zero rows | OOS bigone expectations (2) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/sql/_13_issues/_14_1h/cases/bug_bts_10516.diff) |
| test_sql | `sql/_13_issues/_14_1h/cases/bug_bts_13199.sql` | failure | Join/index/trace differs | Plan/trace expectations (13) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/sql/_13_issues/_14_1h/cases/bug_bts_13199.diff) |
| test_sql | `sql/_13_issues/_14_1h/cases/bug_bts_13884.sql` | failure | Join/index/trace differs | Plan/trace expectations (13) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/sql/_13_issues/_14_1h/cases/bug_bts_13884.diff) |
| test_sql | `sql/_13_issues/_14_1h/cases/bug_bts_6494.sql` | failure | Join/index/trace differs | Plan/trace expectations (13) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/sql/_13_issues/_14_1h/cases/bug_bts_6494.diff) |
| test_sql | `sql/_35_fig_cake/cbrd_24044/cbrd_25214/cases/cbrd_25214.sql` | failure | Join/index/trace differs | Plan/trace expectations (13) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/sql/_35_fig_cake/cbrd_24044/cbrd_25214/cases/cbrd_25214.diff) |
| test_sql | `sql/_35_fig_cake/cbrd_25382/cases/cbrd_25382_1.sql` | failure | Join/index/trace differs | Plan/trace expectations (13) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/sql/_35_fig_cake/cbrd_25382/cases/cbrd_25382_1.diff) |
| test_sql | `sql/_36_guava/cbrd_26599/cases/cbrd_26599.sql` | failure | Join/index/trace differs | Plan/trace expectations (13) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/sql/_36_guava/cbrd_26599/cases/cbrd_26599.diff) |
| test_sql | `sql/_05_plcsql/_01_testspec/_05_bug_fix/cases/19_user_cursor_system_view.sql` | failure | DBA/INFORMATION_SCHEMA counts lower by one | Catalog expectations (1) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/sql/_05_plcsql/_01_testspec/_05_bug_fix/cases/19_user_cursor_system_view.diff) |
| test_sql | `sql/_15_fbo/_02_qa_test/cases/fbo_ddl02.sql` | failure | Expected INSERT success; actual Error:-1382, then zero rows | OOS bigone expectations (2) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/sql/_15_fbo/_02_qa_test/cases/fbo_ddl02.diff) |
| test_sql | `sql/_22_news_service_mysql_compatibility/_03_hint_rewriting/cases/_09_join_1.sql` | failure | Join/index/trace differs | Plan/trace expectations (13) | Reproduced baseline; unlikely introduced / high | [Paired diff](ci-fix/pr-7927/be7c01a-20260911/diffs/sql/_22_news_service_mysql_compatibility/_03_hint_rewriting/cases/_09_join_1.diff) |

## Root-Cause Analysis

### Unordered output — 3 medium cases

Observed: `to_char_order_by`, `to_number_order_by` and `to_timestamp_order_by` disagree only on the unqualified SELECT's row order. Their explicit ORDER BY checks do not appear in the remote failure diffs. Both local builds fail these exact testcase/answer bytes with identical outputs. The local permutation differs from CI's permutation; the reproduced signature is an order-sensitive expectation for an unordered query, not identical remote output bytes.

Inference: brittle testcase expectations, not evidence of changed conversion values. Confidence is high for baseline reproduction; a changed value, duplicate/missing row, or failure of an explicitly ordered query would falsify this attribution. Any testcase repair should preserve conversion and explicit-order assertions and remove only the unsupported unordered-order assumption, through the testcase project's review process.

### OOS bigone expectations — 2 SQL cases

Observed: `bug_bts_10516` and `fbo_ddl02` expect a successful large many-LOB row insert. Both baseline and candidate return `Error:-1382` and subsequent operations see zero rows. The pinned engine's `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` is -1382. These are the existing unsupported OOS-plus-bigone boundary, not a newly introduced deferred-write failure. The current develop testcase answers expect ordinary INSERT success; this is not merely the older -1381/-1382 answer-number mismatch.

The previous [baseline CI report](../cbrd-26357/ci_analysis_report_f4299ac_codex.md) describes an OOS-specific testcase branch, but its earlier testcase revision is not the revision consumed by this PR. Next: select/review compatible testcase coverage for the OOS branch, preserving rejection and follow-on state assertions. A baseline success with these same test bytes and configuration would falsify the current attribution. No answer files or testcase branches were changed here.

### Catalog expectations — 1 SQL case

Observed: `19_user_cursor_system_view` has DBA/INFORMATION_SCHEMA expected counts one above actual; e.g. 549/300 versus 548/299. Both local builds produce identical results and fail the same expectations. This proves the discrepancy predates the replacement. The exact missing catalog definition is not diagnosed by this comparison.

Next: compare catalog definitions against the testcase's intended engine baseline before changing any expected count. A candidate-only missing catalog object would falsify the baseline attribution. Do not infer that a count adjustment is automatically correct.

### Plan/trace expectations — 13 SQL cases

Observed: the inventory's 13 cases disagree on join choice, index choice, join order or trace structure; `cbrd_24843_1` also exposes changed unordered output order. Identical local actual results reproduce on both builds, with the same signature classes as remote CI. Examples include hash versus nested-loop joins, `bug_bts_6494`'s merge plan, and alternate indexes in `_09_join_1`.

This supports high-confidence baseline attribution, not proof that every plan is optimal or every develop expectation is obsolete. The exact optimizer cause of each expected-plan change remains unproven. Next: validate testcase/engine compatibility and intended plan contracts before selecting OOS-specific expectations. Candidate-only output or plan differences under identical inputs would require reopening attribution.

## Local Verification

[Machine-readable identity, per-case comparisons and file hashes](ci-fix/pr-7927/local-verification.json) retain all 19 paired results and diffs. SQL summaries: [baseline](ci-fix/pr-7927/be7c01a-20260911/baseline-sql-summary.xml), [candidate](ci-fix/pr-7927/be7c01a-20260911/candidate-sql-summary.xml); medium summaries: [baseline](ci-fix/pr-7927/be7c01a-20260911/baseline-medium-summary.xml), [candidate](ci-fix/pr-7927/be7c01a-20260911/candidate-medium-summary.xml).

Rebuilt both exact engine checkouts with their GCC Debug configurations; retained binary/library hashes are printed in the attempt logs. CTP JDBC uses fresh databases, isolated network/PID/IPC/mount namespaces and temporary socket storage. Both runs use the same immutable testcase checkout, category configuration, matching medium dataset, and explicit selection of the 19 failed tests. Testcase auto-update is disabled. Existing generated locale data is reused; this is a focused local Debug reproduction, not an identical cloud machine image.

Commands are `bash <attempt-root>/enter.sh baseline sql`, `candidate sql`, `baseline medium`, and `candidate medium`; the retained local runner lives at `/home/vimkim/.cache/codex/pr7927-be7c01a/enter.sh`. CTP process exits were zero despite NOK results: XML and exact executed counts, not exit codes, establish **16/16 failures per SQL run and 3/3 per medium run**. No assertions were weakened and no baseline failure was converted into a pass.

The final configured CTest rerun passed **27/27 in 137.15 seconds** ([log](ci-fix/pr-7927/be7c01a-20260911/full-suite.log)). This does not change the failed CTP results or supply shell evidence.

## Acceptance and Remaining Prerequisites

The published [producer/resource matrix](CBRD-27089-deferred-write_be7c01a_codex.md) remains the local evidence boundary. These remote results do not invalidate the paired memory measurements or add vacuum/no-logging-durability/heartbeat-failover coverage. No engine repair is justified by the available baseline-equivalent failures. The parent specification, map and ticket22 stay open.

1. PR author/CI operator: allow `download-build`154505 on `cubrid/ramdisk` to execute successfully; then collect shell154506, its actual testcase revision, counts and failures. Its queue cause is unknown; an unstarted job is not evidence that a specific runner is offline. Existing [run-all comment](https://github.com/CUBRID/cubrid/pull/7927#issuecomment-5631371023) already requested this work. No duplicate trigger was posted.
2. PR author/test maintainers: assess the reproduced baseline expectations against the intended OOS testcase branch. Creating/pushing a new testcase branch or rerunning CI is separate work; none occurred here.
3. Repository maintainer: establish required-check applicability. GitHub branch-protection required-status-check lookup returned HTTP404, so required-check completeness is not proven.
4. Reconcile all required terminal evidence with the producer/resource matrix before closing V21-CI/V21-ACCEPT. Any later engine change needs an explicit evidence identity update; the documentation-only follow-up does not assert remote verification of a new head.

## Evidence and Limitations

Reviewed manifests, both suite summaries, all 19 failure metadata/messages/diffs, raw result counts, log/artifact/source indexes, checkout logs, exact testcase bytes, local paired XML/results/diffs, baseline source error constants and existing OOS reports. No binary core downloads. No conclusion about unexecuted shell cases, vacuum convergence, no-logging durability, multi-node heartbeat failover, release throughput or exhaustive concurrency is added. Local baseline reproduction is evidence for attribution, not a waiver of failed remote checks.
