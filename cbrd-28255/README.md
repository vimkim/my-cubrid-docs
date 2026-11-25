# CBRD-28255

A multi-column index key built from a record written before `ALTER TABLE ... ADD COLUMN ... DEFAULT` (or with many small columns) can overflow the key buffer sized from `recdes->length`: crash or wrong key in index builds, DML, FK actions and checkdb.

- Engine PR: [CUBRID/cubrid#8711](https://github.com/CUBRID/cubrid/pull/8711) (author lht1199)
- TC PRs: [cubrid-testcases#4418](https://github.com/CUBRID/cubrid-testcases/pull/4418), [cubrid-testcases-private-ex#5114](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5114) (`tc/pr-8711`)
- Related: CBRD-28254 (OOS size estimate in the same loop)

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [code-review-pr8711-bf5618f/report.md](code-review-pr8711-bf5618f/report.md) | Code review of PR #8711 and TC #4418/#5114 at head bf5618f627: verdict, safety facts, runtime probes | 2026-11-25 | 2026-11-25 | Requested review of the key buffer size fix |
| [code-review-pr8711-bf5618f/coverage.md](code-review-pr8711-bf5618f/coverage.md) | Coverage table per path and invariant | 2026-11-25 | 2026-11-25 | Review coverage record |
| [code-review-pr8711-bf5618f/manifest.md](code-review-pr8711-bf5618f/manifest.md) | Pinned SHAs, budget, agents | 2026-11-25 | 2026-11-25 | Review identity record |
| [code-review-pr8711-bf5618f/reviewers/r1-systems-storage.md](code-review-pr8711-bf5618f/reviewers/r1-systems-storage.md) | Systems + storage reviewer report (bound soundness) | 2026-11-25 | 2026-11-25 | Reviewer evidence |
| [code-review-pr8711-bf5618f/reviewers/r2-callers-or-buf.md](code-review-pr8711-bf5618f/reviewers/r2-callers-or-buf.md) | Independent bound check, callers, `or_init`, N/A domains | 2026-11-25 | 2026-11-25 | Reviewer evidence |
| [code-review-pr8711-bf5618f/reviewers/r3-tc.md](code-review-pr8711-bf5618f/reviewers/r3-tc.md) | TC PR review | 2026-11-25 | 2026-11-25 | Reviewer evidence |
