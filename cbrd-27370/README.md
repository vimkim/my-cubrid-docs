# CBRD-27370

[CBRD-27370](https://jira.cubrid.org/browse/CBRD-27370): `[PGBUF] [Regression] Ordinary nested READ-to-WRITE fix resets BCB fix count and desynchronizes holder debt`.

Related PRs:
- Engine: `CUBRID/cubrid#8776` (`CBRD-27370-read-write-fix-count` -> `develop`)
- Public TC: `CUBRID/cubrid-testcases#4499` (`tc/pr-8776`, draft, 0 changed files)
- Private TC: `CUBRID/cubrid-testcases-private-ex#5194` (`tc/pr-8776`, draft, 0 changed files)

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [CBRD-27370-claim-verification-report_5f3a30d_claude.md](CBRD-27370-claim-verification-report_5f3a30d_claude.md) | Baseline verification of the `fcnt = 1` regression on `develop` (`5f3a30d09`) | 2026-09-04 | 2026-09-04 | Verify CBRD-27370 issue claims before fix |
| [pr8776-review.md](pr8776-review.md) | Code review of `CUBRID/cubrid#8776` (`0e29ef5cc4`) and linked TC PRs (`no-confirmed-findings` / `APPROVE`) | 2026-11-27 | 2026-11-27 | Document PR #8776 review findings and verification |
