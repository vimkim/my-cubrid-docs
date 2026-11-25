# CBRD-28307

Server shutdown with an open CDC session can wake a freed page flush daemon: `xboot_shutdown_server` destroyed the page buffer daemons before the CDC producer.

- Engine PR: [CUBRID/cubrid#8715](https://github.com/CUBRID/cubrid/pull/8715) (author hornetmj)
- TC PR: [CUBRID/cubrid-testcases-private-ex#5119](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5119) (`tc/pr-8715`); public [cubrid-testcases#4422](https://github.com/CUBRID/cubrid-testcases/pull/4422) is an empty draft
- Related: CBRD-28341 (log checkpoint daemon residual window)

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [code-review-pr8715-d6bd5db/report.md](code-review-pr8715-d6bd5db/report.md) | Code review of PR #8715 and TC #5119 at head d6bd5db6ab: verdict, safety facts, TC run | 2026-11-25 | 2026-11-25 | Requested review of the shutdown reorder |
| [code-review-pr8715-d6bd5db/coverage.md](code-review-pr8715-d6bd5db/coverage.md) | Coverage table per path and invariant | 2026-11-25 | 2026-11-25 | Review coverage record |
| [code-review-pr8715-d6bd5db/manifest.md](code-review-pr8715-d6bd5db/manifest.md) | Pinned SHAs, budget, agents | 2026-11-25 | 2026-11-25 | Review identity record |
| [code-review-pr8715-d6bd5db/reviewers/r1-systems-concurrency.md](code-review-pr8715-d6bd5db/reviewers/r1-systems-concurrency.md) | Systems + concurrency reviewer report | 2026-11-25 | 2026-11-25 | Reviewer evidence |
| [code-review-pr8715-d6bd5db/reviewers/r2-storage-recovery-ha-tc.md](code-review-pr8715-d6bd5db/reviewers/r2-storage-recovery-ha-tc.md) | Storage, recovery, HA and TC reviewer report | 2026-11-25 | 2026-11-25 | Reviewer evidence |
