# CBRD-28061

Rolling back an allocation that reused the first partial file-table page leaves that table page with the new page's contents.

Related PRs: [CUBRID/cubrid#8616](https://github.com/CUBRID/cubrid/pull/8616) (engine), CUBRID/cubrid-testcases-private-ex#4996 (shell TC `cbrd_28061`).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr8616-review.md](pr8616-review.md) | Code review of PR #8616 at head `7ef2e11`: recovery safety facts, CI/TC evidence, approval recommendation | 2026-11-23 | 2026-11-23 | Decide whether to approve PR #8616 |
