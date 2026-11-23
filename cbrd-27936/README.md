# CBRD-27936

Restart recovery can fail when `log_commit_local` releases a no-postpone transaction's saved space before its commit log. Related PRs: CUBRID/cubrid#8532 (hornetmj, the fix under review), and an earlier validation-only draft PR prepared from `vimkim/cubrid` branch `cbrd-27936-validate`.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr-body.md](pr-body.md) | Body of the validation-only draft PR | 2026-11-12 | 2026-11-12 | Draft the validation PR description |
| [pr-context.md](pr-context.md) | Source revision and evidence for the validation draft PR | 2026-11-12 | 2026-11-12 | Record the evidence behind the validation PR |
| [code-review-pr8532-bd9a0af/report.md](code-review-pr8532-bd9a0af/report.md) | Code review of PR #8532 at head bd9a0afc7b (verdict no-confirmed-findings, approve; base repro 2/2 fail, head 3/3 pass; TLA+ commit-window finding removed) | 2026-11-23 | 2026-11-23 | Decide vimkim's approval of PR #8532 |
| [code-review-pr8532-bd9a0af/coverage.md](code-review-pr8532-bd9a0af/coverage.md) | Coverage table for the PR #8532 review | 2026-11-23 | 2026-11-23 | Show that every hunk and risk had an owner |
| [code-review-pr8532-bd9a0af/reviewers/r1-recovery-ha.md](code-review-pr8532-bd9a0af/reviewers/r1-recovery-ha.md) | Recovery and HA reviewer report with WAL, prefix, checkpoint and 2PC safety facts | 2026-11-23 | 2026-11-23 | Substantiate the review's recovery claims |
| [code-review-pr8532-bd9a0af/reviewers/r2-systems-concurrency.md](code-review-pr8532-bd9a0af/reviewers/r2-systems-concurrency.md) | Systems, concurrency and storage reviewer report with lock, ownership and window-cost analysis | 2026-11-23 | 2026-11-23 | Substantiate the review's concurrency claims |
