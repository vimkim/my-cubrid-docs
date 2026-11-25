# CBRD-27969

Documents for JIRA [CBRD-27969](https://jira.cubrid.org/browse/CBRD-27969). The C API lookups by a unique value (`db_find_unique ()`, `db_find_multi_unique ()` and their forms) send the B-tree a key whose shape differs from the index they search. A debug server asserts in `btree_compare_key ()`. PR [CUBRID/cubrid#8694](https://github.com/CUBRID/cubrid/pull/8694) (author YeunjunLee), head `abf044abcd`, base `develop` `e23905d89a`. TC PRs [cubrid-testcases-private-ex#5099](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5099) (new shell TC `cbrd_27969`) and [cubrid-testcases#4401](https://github.com/CUBRID/cubrid-testcases/pull/4401) (no changes).

Last modified: 2026-11-25 (Asia/Seoul).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [code-review-pr8694.md](code-review-pr8694.md) | Code review of PR #8694 at `abf044abcd`: verdict, F1 (prefix index gives a wrong row in a one-attribute `db_find_multi_unique`), safety evidence, TC #5099 runs on head and base, CI state, approval readiness | 2026-11-25 | 2026-11-25 | Review requested for PR #8694 and its TC PRs |
