# CI Failure Analysis: PR #7925 at `fe1a918`

## Executive Summary

The approved Python dependency repair is published and verified by successful CircleCI release/debug builds. Medium passed 975/975. SQL completed with 17,443 successes and 16 failures out of 17,459 tests. Shell has not executed: download-build 154540 remains unstarted and shell 154541 is blocked behind it. **Full CI acceptance remains open.**

All 16 SQL failure messages are byte-identical to PR #7927's retained failures at testcase revision `b10727db4b9fd1b52aed49330634a3395d532048`. That prior investigation independently reproduced these failures on our shared baseline `f4299ac0c`. This strongly supports baseline attribution; it does not make the failed SQL suite green, and it is not a new local reproduction of PR #7925.

## Publication

- Engine commit: [`fe1a918f9a31e8586e8160da4f7341978514538b`](https://github.com/vimkim/cubrid/commit/fe1a918f9a31e8586e8160da4f7341978514538b), one-file CMake change. Reviewed patch SHA-256 `2cc8484da25a6f2dfcc094336245c676e3dfca48df81c01e977766bcaf8d2304` matched before commit. Python regression assertions unchanged.
- Expanded report: [published revision](https://github.com/vimkim/my-cubrid-docs/blob/453f22daf1fc17e0dbf311be37d2ef6f6ac63f3b/cbrd-27424/CBRD-27424-sa-workspace-oos_e24b458_codex.md), docs commit `453f22daf1fc17e0dbf311be37d2ef6f6ac63f3b`; only approved report changed.
- PR #7925 body updated and read back exactly, including pinned report link and historical 28/28 versus latest 27/28 plus unchanged CLI rerun (12 scenarios, 60.74 seconds).
- One authorized [`/run all` comment](https://github.com/CUBRID/cubrid/pull/7925#issuecomment-5631980552), 2026-09-11T08:55:35Z. Head verified before and after. [Pipeline 37077](https://app.circleci.com/pipelines/github/CUBRID/cubrid/37077), workflow `38d3650d-a5f2-4d44-a12a-d9715f9727f2`, matches the exact published engine SHA.
- No additional fixes, testcase changes, pushes, or trigger comments. The separate pre-existing workspace LOB-creation defect remains outside this PR.

## CI Snapshot

| Suite/check | State | Job | Tests | Success | Failure | Error / unknown | Notes |
|---|---|---|---:|---:|---:|---|---|
| Release build | success | [154542](https://circleci.com/gh/CUBRID/cubrid/154542) | — | — | — | — | Triggered workflow |
| Debug build | success | [154537](https://circleci.com/gh/CUBRID/cubrid/154537) | — | — | — | — | Triggered workflow |
| Push-started release/debug | success | [154535](https://circleci.com/gh/CUBRID/cubrid/154535), [154536](https://circleci.com/gh/CUBRID/cubrid/154536) | — | — | — | — | Same head, separate workflow |
| test_medium | success | [154539](https://circleci.com/gh/CUBRID/cubrid/154539) | 975 | 975 | 0 | 0 / 0 | No skipped cases |
| test_sql | failed | [154538](https://circleci.com/gh/CUBRID/cubrid/154538) | 17,459 | 17,443 | 16 | 0 / 0 | Failures inventoried below |
| download-build | not_running | [154540](https://circleci.com/gh/CUBRID/cubrid/154540) | — | — | — | — | No start time; queue cause unknown |
| test_shell | blocked | [154541](https://circleci.com/gh/CUBRID/cubrid/154541) | — | — | — | — | Depends on download-build success |
| GitHub checks | success | [Actions 34581515941](https://github.com/CUBRID/cubrid/actions/runs/34581515941) | 5 checks | 5 | 0 | — | license, pr-style, code-style, cppcheck, memory-monitor-check |

## Evidence Scope

Current engine head is `fe1a918f9a31e8586e8160da4f7341978514538b`; baseline is `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`; PR base is `feat/oos`. CircleCI job and pipeline metadata and GitHub PR head establish exact-head identity. Actions run metadata links to the same head; event is pull_request, attempt 1. A synthetic merge checkout was not independently reconstructed for this report.

Collector: `cubrid-ci 0.1.0 (3e9502f72350, release)`, pinned suite collection with text artifacts and testcase sources. Durable root: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27424/fe1a918/`. Timestamped read-only API snapshots are under `api-monitor`; publication, partial-result history and signature comparisons under `api-publication`. Final collection validated: 127 bounded text artifacts (123,573,016 bytes), five failed-action logs and 32 testcase/answer source files. All 32 downloaded source files match their pinned local Git objects byte-for-byte. SQL reports no skipped, error or unknown results. All 16 current failure messages match the retained prior messages exactly.

The local SQL repository `/home/vimkim/gh/tc/cubrid-testcases` is clean at `b4e774d1f4dfe728960b095ae211b96825a19485`, with canonical CUBRID/cubrid-testcases remote. It contains the exact CI testcase commit `b10727db4b9fd1b52aed49330634a3395d532048`; case and answer contents were read from that commit, not the newer worktree. Each failure message pins this revision. No testcase branch was changed. Shell's testcase revision is unknown because it has not run; unset local CTP variables were not silently assigned an unrelated checkout.

`feat/oos` branch metadata reports protected=false, enforcement off and empty required checks; branch rules are empty. No GitHub-enforced status requirement was found. The user's requested runtime verification still requires shell execution and an explicit disposition for SQL failures.

## Failure Inventory

Each SQL failure appears once. Categories total 13 plan/trace + 2 OOS size-limit + 1 catalog = 16.

| Test | Result | Category | Observed signature | Attribution / confidence |
|---|---|---|---|---|
| `sql/_33_elderberry/cbrd_24042/cbrd_24182/cases/dnf.sql` | failure | Plan/trace expectations | Join, index, order or trace differs | Baseline-related / high |
| `sql/_33_elderberry/cbrd_24011/cases/nullable_outer_join.sql` | failure | Plan/trace expectations | Join, index, order or trace differs | Baseline-related / high |
| `sql/_33_elderberry/cbrd_24011/cases/on_cond.sql` | failure | Plan/trace expectations | Join, index, order or trace differs | Baseline-related / high |
| `sql/_13_issues/_14_1h/cases/bug_bts_10516.sql` | failure | OOS size-limit expectations | INSERT returns -1382; later queries see zero rows | Baseline-related / high |
| `sql/_13_issues/_14_1h/cases/bug_bts_13199.sql` | failure | Plan/trace expectations | Join, index, order or trace differs | Baseline-related / high |
| `sql/_13_issues/_14_1h/cases/bug_bts_13884.sql` | failure | Plan/trace expectations | Join, index, order or trace differs | Baseline-related / high |
| `sql/_13_issues/_14_1h/cases/bug_bts_6494.sql` | failure | Plan/trace expectations | Join, index, order or trace differs | Baseline-related / high |
| `sql/_13_issues/_23_1h/cases/cbrd_24843_1.sql` | failure | Plan/trace expectations | Join, index, order or trace differs | Baseline-related / high |
| `sql/_13_issues/_23_1h/cases/cbrd_24906_1.sql` | failure | Plan/trace expectations | Join, index, order or trace differs | Baseline-related / high |
| `sql/_13_issues/_23_1h/cases/cbrd_24906_2.sql` | failure | Plan/trace expectations | Join, index, order or trace differs | Baseline-related / high |
| `sql/_35_fig_cake/cbrd_24044/cbrd_25214/cases/cbrd_25214.sql` | failure | Plan/trace expectations | Join, index, order or trace differs | Baseline-related / high |
| `sql/_35_fig_cake/cbrd_25382/cases/cbrd_25382_1.sql` | failure | Plan/trace expectations | Join, index, order or trace differs | Baseline-related / high |
| `sql/_15_fbo/_02_qa_test/cases/fbo_ddl02.sql` | failure | OOS size-limit expectations | INSERT returns -1382; later queries see zero rows | Baseline-related / high |
| `sql/_05_plcsql/_01_testspec/_05_bug_fix/cases/19_user_cursor_system_view.sql` | failure | Catalog-count expectations | DBA/INFORMATION_SCHEMA counts one below expected | Baseline-related / high |
| `sql/_36_guava/cbrd_26599/cases/cbrd_26599.sql` | failure | Plan/trace expectations | Join, index, order or trace differs | Baseline-related / high |
| `sql/_22_news_service_mysql_compatibility/_03_hint_rewriting/cases/_09_join_1.sql` | failure | Plan/trace expectations | Join, index, order or trace differs | Baseline-related / high |

## Root-Cause Analysis

### Plan/trace expectations — 13 cases

Observed mismatches concern join algorithm/order, index selection or query trace structure; `cbrd_24843_1` additionally has unordered row-order differences. Current messages exactly match the prior run at the same testcase revision. Existing paired baseline/candidate results from PR #7927 reproduce the same signature classes on f4299ac0c.

Inference: baseline/testcase expectation differences are unlikely to have been introduced by this CMake dependency change or this PR's SA force hook. No optimizer edit is present. This is not proof that all plans are optimal or that answer files should be replaced. Falsifier: a PR #7925-only difference under identical baseline/candidate inputs and settings. Next action, if separately approved: investigate intended OOS testcase selection and validate per-test plan contracts before proposing any change.

### OOS size-limit expectations — 2 cases

`bug_bts_10516` and `fbo_ddl02` expect insertion of a large many-LOB row; actual results return -1382 and later operations see zero rows. The baseline investigation reproduces the same rejection and identifies `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`. This is distinct from the separate workspace external-LOB creation defect excluded from CBRD-27424. Do not silently fix either issue here or weaken INSERT/state assertions.

### Catalog-count expectations — 1 case

`19_user_cursor_system_view` expects DBA/INFORMATION_SCHEMA counts one above actual. Exact failure messages match the prior baseline-reproduced case. The missing catalog definition is not diagnosed by this comparison. Compare intended engine/catalog versions before proposing any expected-count update.

### Strength and limits of the baseline comparison

The prior [analysis](../cbrd-27089/ci_analysis_report_be7c01a_codex.md) and [machine-readable paired verification](../cbrd-27089/ci-fix/pr-7927/local-verification.json) identify baseline f4299ac0c and testcase b10727db. I checked that all 16 current cases have baseline failure records, byte-identical prior baseline/candidate result records, nonempty retained local diffs, and byte-identical current/prior remote failure messages. Current case/answer Git-object hashes and message comparisons are saved in `api-publication/final-baseline-comparison.json`.

These are reused, validated baseline observations from another PR; no new local paired CTP execution of fe1a918 was performed. This supports attribution, not a waiver of failed CI.

## Recommended Actions

1. Accept the Python dependency failure as repaired: release/debug builds now pass; normal CI intentionally omits the optional Python CLI test, whose assertions and enabled execution were verified locally.
2. Review whether the 16 baseline-matching SQL failures should be accepted outside this focused repair. Any testcase-selection/answer/engine change or additional push requires a concrete proposal and renewed user approval. No such repair is currently proposed as necessary.
3. Keep shell monitoring open. The existing trigger has created both download-build and shell jobs. An operator may need to inspect the unstarted prerequisite's runner/queue, but the API evidence does not identify the queue cause. Do not post a duplicate trigger.

## Evidence and Limitations

Publication is complete; runtime acceptance is not. SQL remains failed, shell is not a pass, and no PR-wide green claim is made. Preserve the original local disk-exhaustion attempt and the successful unchanged CLI rerun separately from historical 28/28. This follow-up report is local and uncommitted; publishing it would be an additional docs push requiring approval.

Snapshot reviewed at 2026-09-11 09:38 UTC. Shell prerequisite remains unstarted; monitoring evidence is retained separately as it changes.

Follow-up 09:41 UTC: workflow/head revalidated, shell still unstarted. The pinned workflow instantiates `build-debug-node` under the name `download-build`, using executor `cubrid-build-node` and self-hosted resource class `cubrid/ramdisk` ([configuration](https://github.com/CUBRID/cubrid/blob/fe1a918f9a31e8586e8160da4f7341978514538b/.circleci/config.yml#L691)). An operator should inspect that queue/runner assignment. API evidence does not prove runner outage or authorize configuration changes.
