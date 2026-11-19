# CBRD-28065

A client could receive COMMIT success for a transaction that recovery rolled back after a kill -9, because `logpb_flush_pages` treated `nxio_lsa == flush_lsa` as durable. Fix on develop with backports to release/11.4, release/11.3 and release/10.2.

PRs (draft, created 2026-11-19): develop [CUBRID/cubrid#8642](https://github.com/CUBRID/cubrid/pull/8642), 11.4 [#8643](https://github.com/CUBRID/cubrid/pull/8643), 11.3 [#8644](https://github.com/CUBRID/cubrid/pull/8644), 10.2 [#8645](https://github.com/CUBRID/cubrid/pull/8645). Regression TC branch: `tc/pr-8642`.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [verification.md](verification.md) | Cause, caller audit, why the wait ends, reproduction and latency results for all lines | 2026-11-19 | 2026-11-19 | Evidence linked from every PR body |
| [pr-body.md](pr-body.md) | develop PR body | 2026-11-19 | 2026-11-19 | Draft PR description for develop |
| [pr-context.md](pr-context.md) | develop PR metadata, proposed operations, static check disposition | 2026-11-19 | 2026-11-19 | Resume and publish the develop draft |
| [pr-body-11.4.md](pr-body-11.4.md) | release/11.4 backport PR body | 2026-11-19 | 2026-11-19 | Draft PR description for 11.4 Patch 8 |
| [pr-context-11.4.md](pr-context-11.4.md) | release/11.4 PR metadata and required edits | 2026-11-19 | 2026-11-19 | Resume and publish the 11.4 draft |
| [pr-body-11.3.md](pr-body-11.3.md) | release/11.3 backport PR body | 2026-11-19 | 2026-11-19 | Draft PR description for 11.3 Patch 7 |
| [pr-context-11.3.md](pr-context-11.3.md) | release/11.3 PR metadata, required edits, local build notes | 2026-11-19 | 2026-11-19 | Resume and publish the 11.3 draft |
| [pr-body-10.2.md](pr-body-10.2.md) | release/10.2 backport PR body | 2026-11-19 | 2026-11-19 | Draft PR description for 10.2 Patch 20 |
| [pr-context-10.2.md](pr-context-10.2.md) | release/10.2 PR metadata, required edits, local build notes | 2026-11-19 | 2026-11-19 | Resume and publish the 10.2 draft |

The `test/` directory holds the reproduction, 2PC, latency and caller-audit scripts that `verification.md` describes.
