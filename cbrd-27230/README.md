# CBRD-27230 OOS chain reuse on UPDATE

Related PR: [CUBRID/cubrid#8559](https://github.com/CUBRID/cubrid/pull/8559) (head branch `CBRD-27230-oos-update-dedup`, base `feature/oos-merge`).

- Created: 2026-11-18
- Last modified: 2026-11-18

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [design-a-prime-detail.md](design-a-prime-detail.md) | Detailed design of chain reuse on top of A', with TLA+ results | 2026-11-16 | 2026-11-16 | Fix the design before implementation |
| [pr-body.md](pr-body.md) | PR #8559 description | 2026-11-16 | 2026-11-18 | Publish the PR |
| [pr-context.md](pr-context.md) | Context gathered for the PR draft | 2026-11-16 | 2026-11-16 | Prepare the PR body |
| [ci-analysis.md](ci-analysis.md) | CI analysis of PR #8559 | 2026-11-17 | 2026-11-18 | Explain CI failures |
| [perf/report.md](perf/report.md) | Performance measurement of chain reuse | 2026-11-16 | 2026-11-16 | Quantify the gain |
| [review-miss-analysis.md](review-miss-analysis.md) | Why the checks missed the reuse-marker must_flush split, and methods to find this bug class before review | 2026-11-18 | 2026-11-18 | Answer how to find such bugs ourselves |
| [wayfinder/map.md](wayfinder/map.md) | Early research map and its tickets and findings | 2026-08-13 | 2026-08-13 | Plan the investigation |
| [wayfinder/findings/T2-oos-replication-replay-under-chain-reuse.md](wayfinder/findings/T2-oos-replication-replay-under-chain-reuse.md) | How OOS replication replays and why reuse needs a marker | 2026-08-13 | 2026-08-13 | Research replication under reuse |
