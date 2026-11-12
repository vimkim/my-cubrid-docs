# CBRD-27937

Related PRs are [Engine PR 8454](https://github.com/CUBRID/cubrid/pull/8454) and [TC PR 4803](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4803).

Both reviews pin the same engine snapshot. The 2026-11-11 review ended incomplete. The 2026-11-12 review adds the TC and runtime checks and finds no confirmed defect; it records two pre-existing leaks for new issues.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [review.md](review.md) | Pinned log-encryption review and unverified risks | 2026-11-11 | 2026-11-11 | Assess PR 8454 before relying on its confidentiality guarantee |
| [coverage.md](coverage.md) | Changed-path coverage and evidence limits | 2026-11-11 | 2026-11-11 | Keep inspected paths and remaining checks visible |
| [handoff.md](handoff.md) | Focused follow-up for log persistence and recovery | 2026-11-11 | 2026-11-11 | Resume unfinished verification at the recorded revisions |
| [review-with-tc.md](review-with-tc.md) | Engine and TC review with pre/post-fix runs, recovery probe and residual leaks | 2026-11-12 | 2026-11-12 | Verify the fix and its TC by execution and resolve the earlier follow-up |
| [review-with-tc-coverage.md](review-with-tc-coverage.md) | Coverage table for the 2026-11-12 review | 2026-11-12 | 2026-11-12 | Keep owners and evidence levels per path visible |
