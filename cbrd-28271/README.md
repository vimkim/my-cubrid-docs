# CBRD-28271

Documents for JIRA [CBRD-28271](https://jira.cubrid.org/browse/CBRD-28271): a NEXT VALUE that fails because the serial row no longer fits its page leaves a redo-only record, and restart recovery then cannot apply it. PR [CUBRID/cubrid#8736](https://github.com/CUBRID/cubrid/pull/8736), engine branch `CBRD-28271`, head `fd7d071ed5`, base `develop` `bfb59bdd13`; TC PR [CUBRID/cubrid-testcases-private-ex#5146](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5146).

Last modified: 2026-11-25 (Asia/Seoul).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr-body.md](pr-body.md) | PR body (Korean) for the fix at head `fd7d071ed5` against `develop` | 2026-11-25 | 2026-11-25 | Draft PR for the CBRD-28271 fix |
| [pr-context.md](pr-context.md) | Draft context: source commit, base, TC commit, verification evidence, proposed operations | 2026-11-25 | 2026-11-25 | Resume and publication bookkeeping |
| [ci-analysis.md](ci-analysis.md) | Warning-mode CI analysis of run 45567167574 at head `fd7d071ed5`: `test_sql` evidence failed integrity, three `test_sql_by_cci` optimizer/trace diffs | 2026-11-25 | 2026-11-25 | CI failure analysis after `/run all` |
