# CBRD-28379

Documents for JIRA [CBRD-28379](https://jira.cubrid.org/browse/CBRD-28379): a refused conditional page latch request (`PGBUF_CONDITIONAL_LATCH`) left `waiter_exists` set, and VOID zone BCBs were left out of every LRU list. Engine branch `CBRD-28379` on `develop` `ca39c2c6a4`, head `5c213aaac6`, PR [#8753](https://github.com/CUBRID/cubrid/pull/8753) (draft). Follow-up: CBRD-28389 (review F7). Related: CBRD-28378 (OOS side), CBRD-28163, CBRD-26425.

Last modified: 2026-11-27 (Asia/Seoul).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [verification-report.md](verification-report.md) | Root cause, fix rationale, before/after unit test and OOS reproduction results, ctest and static checks, review dispositions (Korean) at `5c213aaac6` | 2026-11-25 | 2026-11-25 | Record the evidence for the fix |
| [pr-body.md](pr-body.md) | Draft PR body (Korean) for `CUBRID/cubrid` `CBRD-28379` → `develop` | 2026-11-25 | 2026-11-25 | Draft PR for human review |
| [pr-context.md](pr-context.md) | Draft context: source commit, proposed operations, user decisions, execution record (PR #8753, CI run 45615415274, CBRD-28389) | 2026-11-25 | 2026-11-25 | Resume and publication bookkeeping |
| [review-findings.md](review-findings.md) | Independent read-only review of `11b40319ee`: no blocker, findings F1–F7 | 2026-11-25 | 2026-11-25 | Independent concurrency and edge-case review |
| [ci-analysis.md](ci-analysis.md) | Warning CI analysis (Korean) of PR #8753 run 45615415274 at `5c213aaac6`: 5 failing testcases, all also failing without this change (develop regression `cbrd_27744_sa`, TC/engine lag `cbrd_28117`, develop SQL answers); `test_sql` collection integrity failure; no baseline | 2026-11-26 | 2026-11-26 | Record the CI verdict and failure attribution |
| [ci-analysis-45790040980.md](ci-analysis-45790040980.md) | Full CI analysis (Korean) of PR #8753 run 45790040980 at `c9666e0e91`, `test_shell` scope: `cbrd_25637_recovery` also fails on merge base `0eec910fc1` (waits for engine PR #8725 / CBRD-28361); `issue_10753_charset_conversion` is TC/engine lag (CBRD-28289 answer change needs `6f5ac7a9f9`); validated exact baseline | 2026-11-27 | 2026-11-27 | Explain the two remaining shell failures after the rebase |
