# CBRD-27987

Restart analysis recorded a commit-with-postpone transaction's tail at the record body instead of the record start, and restoredb did not record that transaction's state.

Related PRs: [CUBRID/cubrid#8529](https://github.com/CUBRID/cubrid/pull/8529) (engine, author hornetmj).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr8529-review.md](pr8529-review.md) | Code review of PR #8529 at head `b4b478a`: recovery safety facts, cross-version risk R-1, restoredb behavior change R-2 | 2026-11-23 | 2026-11-23 | Review PR #8529 |
