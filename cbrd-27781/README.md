# CBRD-27781

Documents for JIRA [CBRD-27781](https://jira.cubrid.org/browse/CBRD-27781) (OOS chunk undo writes over a reused slot) and the companion [CBRD-27237](https://jira.cubrid.org/browse/CBRD-27237) (forward-walk deletes the chain of a rolled-back UPDATE), implemented together under ADR-0008. No PR exists yet; the engine branch is `CBRD-27781-postpone-commit` (`62d0b35b6`, `3e8072f56`) over `feature/oos-merge` `d52b1889e`.

Last modified: 2026-11-05 (Asia/Seoul).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr-body.md](pr-body.md) | Draft PR body (Korean) | 2026-11-05 | 2026-11-05 | Review before a draft PR is created |
| [pr-context.md](pr-context.md) | Draft context: source commit, base, proposed operations | 2026-11-05 | 2026-11-05 | Resume and publication bookkeeping |
| [perf.md](perf.md) | Release measurement for ADR-0008 decision 7: log bytes, OOS file size, latency, method and limits | 2026-11-05 | 2026-11-05 | Decision 7 requires measured improvement |
| [recovery-analysis-assert.md](recovery-analysis-assert.md) | A debug-only restart-recovery analysis assert found during the work, also on develop | 2026-11-05 | 2026-11-05 | Separate issue candidate, out of this change's scope |

[bench/](bench/) holds the benchmark scripts and the raw CSV that `perf.md` summarizes, so the numbers can be rerun.
