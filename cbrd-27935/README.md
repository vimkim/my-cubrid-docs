# CBRD-27935

Keep the vacuumed forward page fixed until the relocation sysop ends.

Related PRs: [CUBRID/cubrid#8531](https://github.com/CUBRID/cubrid/pull/8531) (engine, author `hornetmj`).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr-body.md](pr-body.md) | Validation-only draft PR body isolating CBRD-27935 from CBRD-27936 | 2026-11-12 | 2026-11-12 | Prepare validation draft PR for CI isolation |
| [pr-context.md](pr-context.md) | Context and source commit metadata for the validation draft PR | 2026-11-12 | 2026-11-12 | Record validation draft PR parameters |
| [pr8531-review.md](pr8531-review.md) | Code review of PR #8531 at head `d26383d2df`: no confirmed findings, runtime replay (base vs head), TLA+ model check, and safety facts | 2026-11-24 | 2026-11-24 | Review PR #8531 vacuum forward-page latch hold and record approval evidence |
| [pr8531-coverage.md](pr8531-coverage.md) | Invariant, path, and dual-reviewer shared-challenge coverage matrix for PR #8531 | 2026-11-24 | 2026-11-24 | Track latch, recovery, and TLA+ model coverage for PR #8531 |
