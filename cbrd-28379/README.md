# CBRD-28379

Documents for JIRA [CBRD-28379](https://jira.cubrid.org/browse/CBRD-28379): a refused conditional page latch request (`PGBUF_CONDITIONAL_LATCH`) left `waiter_exists` set, and VOID zone BCBs were left out of every LRU list. Engine branch `CBRD-28379` on `develop` `ca39c2c6a4`, local head `5c213aaac6` (not yet pushed; no PR yet). Related: CBRD-28378 (OOS side), CBRD-28163, CBRD-26425.

Last modified: 2026-11-25 (Asia/Seoul).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [verification-report.md](verification-report.md) | Root cause, fix rationale, before/after unit test and OOS reproduction results, ctest and static checks, review dispositions (Korean) at `5c213aaac6` | 2026-11-25 | 2026-11-25 | Record the evidence for the fix |
| [pr-body.md](pr-body.md) | Draft PR body (Korean) for `CUBRID/cubrid` `CBRD-28379` → `develop` | 2026-11-25 | 2026-11-25 | Draft PR for human review |
| [pr-context.md](pr-context.md) | Draft context: source commit, proposed operations, user decisions | 2026-11-25 | 2026-11-25 | Resume and publication bookkeeping |
| [review-findings.md](review-findings.md) | Independent read-only review of `11b40319ee`: no blocker, findings F1–F7 | 2026-11-25 | 2026-11-25 | Independent concurrency and edge-case review |
