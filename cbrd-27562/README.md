# CBRD-27562

Do not start a system operation for temporary sector reservation or temporary volume growth.

Related PRs: [CUBRID/cubrid#8537](https://github.com/CUBRID/cubrid/pull/8537) (engine, author `hornetmj`).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr8537-review.md](pr8537-review.md) | Code review of PR #8537 at head `e863def787`: no confirmed findings, crash/abort/parallel-sort probes, safety facts, and CI summary | 2026-11-24 | 2026-11-24 | Review PR #8537 temp sysop removal and record approval evidence |
| [pr8537-coverage.md](pr8537-coverage.md) | Path, invariant, and dual shared-challenge coverage matrix for PR #8537 at `e863def787` | 2026-11-24 | 2026-11-24 | Track recovery, concurrency, and HA invariant verification for PR #8537 |
