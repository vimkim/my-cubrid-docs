# CBRD-26086

Remove temporary volumes by scanning their directory at server start and stop.

Related PRs: [CUBRID/cubrid#8539](https://github.com/CUBRID/cubrid/pull/8539) (engine, author `hornetmj`).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr8539-review.md](pr8539-review.md) | Code review of PR #8539 at head `101106d2ee`: confirmed P3 defect `F1`, safety facts, verification results, and unverified risks | 2026-11-24 | 2026-11-24 | Review PR #8539 temp-volume directory cleanup and record changes-required evidence |
| [pr8539-coverage.md](pr8539-coverage.md) | Path, invariant, and shared-challenge coverage matrix for PR #8539 at `101106d2ee` | 2026-11-24 | 2026-11-24 | Track reviewer ownership and invariant verification for PR #8539 |
| [pr8539-handoff.md](pr8539-handoff.md) | Follow-up delta review scope and reproduction commands for PR #8539 after `F1` fixes | 2026-11-24 | 2026-11-24 | Hand off delta verification of `F1` and `SS-2` for the next PR head |
