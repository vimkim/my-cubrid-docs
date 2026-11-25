# CBRD-28317

Documents for JIRA [CBRD-28317](https://jira.cubrid.org/browse/CBRD-28317): `re2/re2.h` turns off GCC's `-Wmissing-field-initializers` for every translation unit that includes it, and the Clang optimized build still fails in three places. PR [CUBRID/cubrid#8730](https://github.com/CUBRID/cubrid/pull/8730) (author InChiJun), head `9b0a11e189`, base `develop` `714ae28b7f`; depends on [CUBRID/cubrid#8678](https://github.com/CUBRID/cubrid/pull/8678) (CBRD-28261). TC PRs [cubrid-testcases#4438](https://github.com/CUBRID/cubrid-testcases/pull/4438), [cubrid-testcases-private-ex#5137](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5137) (no changes).

Last modified: 2026-11-25 (Asia/Seoul).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [code-review-pr8730.md](code-review-pr8730.md) | Code review of PR #8730 at `9b0a11e189`: verdict, F1 (OOS unit test build break exposed by the pragma scoping), merge preconditions, safety evidence, CI triage | 2026-11-25 | 2026-11-25 | Review requested for PR #8730 and its TC PRs |
