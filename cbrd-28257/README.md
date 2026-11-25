# CBRD-28257

[TDE] Unwritten NULL fixed-length fields of system catalog rows keep old server memory, so plaintext of encrypted tables can reach the disk.

- JIRA: <https://jira.cubrid.org/browse/CBRD-28257>
- Engine PR: [CUBRID/cubrid#8693](https://github.com/CUBRID/cubrid/pull/8693)
- TC PRs: [cubrid-testcases-private-ex#5098](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5098), [cubrid-testcases#4400](https://github.com/CUBRID/cubrid-testcases/pull/4400) (draft, empty)
- Related: the develop CI failure record is in [../cbrd-28073/jira-comment-cbrd-28257-develop-ci.md](../cbrd-28073/jira-comment-cbrd-28257-develop-ci.md)

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [code-review-pr8693.md](code-review-pr8693.md) | Code review of PR #8693 at head `2a3d8b5147`: verdict, safety facts, TC replay on head and base, separate pre-existing leak paths | 2026-11-25 | 2026-11-25 | Review requested for PR #8693 and its TC PRs |
| [code-review-pr8693-coverage.md](code-review-pr8693-coverage.md) | Coverage table of the PR #8693 review | 2026-11-25 | 2026-11-25 | Coverage evidence for the review report |
