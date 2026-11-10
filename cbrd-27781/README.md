# CBRD-27781

Documents for JIRA [CBRD-27781](https://jira.cubrid.org/browse/CBRD-27781) (OOS chunk undo writes over a reused slot) and the companion [CBRD-27237](https://jira.cubrid.org/browse/CBRD-27237) (forward-walk deletes the chain of a rolled-back UPDATE), implemented together under ADR-0008. PR: CUBRID/cubrid#8434; the engine branch is `CBRD-27781-postpone-commit` (`8e139f4db`) over `feature/oos-merge` `95ff126a8`.

Last modified: 2026-11-10 (Asia/Seoul).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr-body.md](pr-body.md) | Draft PR body (Korean) | 2026-11-05 | 2026-11-05 | Review before a draft PR is created |
| [pr-context.md](pr-context.md) | Draft context: source commit, base, proposed operations | 2026-11-05 | 2026-11-05 | Resume and publication bookkeeping |
| [perf.md](perf.md) | Release measurement for ADR-0008 decision 7: log bytes, OOS file size, latency, method and limits | 2026-11-05 | 2026-11-05 | Decision 7 requires measured improvement |
| [perf-latency-handoff.md](perf-latency-handoff.md) | Handoff (Korean) for remeasuring INSERT/UPDATE latency on a quiet machine: commits, build, run, judgment, where results go | 2026-11-06 | 2026-11-06 | Decision 7 latency condition is still undecided |
| [recovery-analysis-assert.md](recovery-analysis-assert.md) | A debug-only restart-recovery analysis assert found during the work, also on develop | 2026-11-05 | 2026-11-05 | Separate issue candidate, out of this change's scope |
| [ci-analysis-sql-by-cci.md](ci-analysis-sql-by-cci.md) | CI analysis of the 57 `test_sql_by_cci` failures at head `8e139f4db` (run 42603737999): identical on unrelated `feature/oos-merge` PR #8348, PR relation unlikely | 2026-11-10 | 2026-11-10 | Decide whether the only red gha-ci suite of PR #8434 comes from the PR |
| [jira-drafts/CBRD-27981-null-snapshot-reader-link-stamp.md](jira-drafts/CBRD-27981-null-snapshot-reader-link-stamp.md) | JIRA issue [CBRD-27981](https://jira.cubrid.org/browse/CBRD-27981) (Korean, registered 2026-11-06 as a Sub-task of CBRD-26978) for review item R7: whether OOS readers without a snapshot can race a tail-first reclaim; suggested type Task (investigation first) | 2026-11-06 | 2026-11-06 | Separate issue for an open PR #8434 review item |
| [jira-drafts/CBRD-28012-eager-oos-heap-header-latch-order.md](jira-drafts/CBRD-28012-eager-oos-heap-header-latch-order.md) | JIRA issue [CBRD-28012](https://jira.cubrid.org/browse/CBRD-28012) (Korean, registered 2026-11-10 as a Sub-task of CBRD-26978) for pre-existing P-1: non-MVCC heap UPDATE/DELETE waits for the heap header while holding heap data pages; revisions pinned to base `95ff126a8` and head `8e139f4db` | 2026-11-06 | 2026-11-10 | Separate issue for a pre-existing problem found in the PR #8434 review |
| [jira-drafts/CBRD-27982-reused-heap-vfid-notification-skip.md](jira-drafts/CBRD-27982-reused-heap-vfid-notification-skip.md) | JIRA issue [CBRD-27982](https://jira.cubrid.org/browse/CBRD-27982) (Korean, registered 2026-11-06 as a Sub-task of CBRD-26978) for pre-existing P-2: vacuum skips an UPDATE's OOS reclaim on a reused FILE_HEAP file when the UPDATE's MVCCID predates the drop; suggested type Correct Error | 2026-11-06 | 2026-11-06 | Separate issue for a pre-existing problem found in the PR #8434 review |

[bench/](bench/) holds the benchmark scripts and the raw CSV that `perf.md` summarizes, so the numbers can be rerun.
