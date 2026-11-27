# CBRD-26249

Add `delvoldb` to delete an empty last permanent volume in stand-alone mode.

Related PRs: [CUBRID/cubrid#8544](https://github.com/CUBRID/cubrid/pull/8544) (engine, author `hornetmj`), [CUBRID/cubrid-testcases#4210](https://github.com/CUBRID/cubrid-testcases/pull/4210), and [CUBRID/cubrid-testcases-private-ex#4918](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4918).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr8544-delta-review.md](pr8544-delta-review.md) | Delta re-review of PR #8544 at head `8fe6fdcb379a` (verified `F1`–`F3`, `U-R2`, `develop` merges, and linked TC PRs; `no-confirmed-findings`) | 2026-11-27 | 2026-11-27 | Verify fixes for `F1`–`F3` and `develop` merges on PR #8544 |
| [pr8544-review.md](pr8544-review.md) | Code review of PR #8544 at head `e54b7611e68a`: confirmed defects `F1` (P2), `F2` (P3), `F3` (P3), rebase conflicts, safety facts, and verification results | 2026-11-24 | 2026-11-24 | Review PR #8544 stand-alone `delvoldb` and record changes-required evidence |
| [pr8544-coverage.md](pr8544-coverage.md) | Path, cross-domain risk, and dual shared-challenge coverage matrix for PR #8544 | 2026-11-24 | 2026-11-24 | Track 5-specialist coverage and adjudicated disagreements for PR #8544 |
| [pr8544-handoff.md](pr8544-handoff.md) | Follow-up delta review scope, rebase renumbering items, and probe commands for PR #8544 | 2026-11-24 | 2026-11-24 | Hand off delta verification of `F1`–`F3` and rebase changes for the next head |
