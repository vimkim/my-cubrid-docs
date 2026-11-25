# Review manifest — CUBRID/cubrid#8715

| Field | Value |
| --- | --- |
| Repository | CUBRID/cubrid (engine), CUBRID/cubrid-testcases-private-ex (TC #5119), CUBRID/cubrid-testcases (draft #4422, 0 files) |
| Request | Review PR #8715 and companion TC PR #5119 with `cubrid-code-review`; publish report, post Korean summary; no formal review, no CI trigger |
| Comparison | PR: `git diff 8e052e99c508141dbdd6dc338b65e437e31d756a d6bd5db6abd400cd48c4c09de190c488c4214003` |
| Base / head / merge base | `8e052e99c508141dbdd6dc338b65e437e31d756a` / `d6bd5db6abd400cd48c4c09de190c488c4214003` / `8e052e99c508141dbdd6dc338b65e437e31d756a` |
| Patch | 1 file, +3/-1, `src/transaction/boot_sr.c`; sha256 `3b08d42731bd7613a03fb101eb7b90ad1a9661803708cd389270c01ccffcd7b2` |
| TC #5119 | `tc/pr-8715` head `f0714e9ebdcf34af1ef607dad671b5cd571f055e`, base develop `07af85a51694bbb11df2a04a5f76d9762b15c768`; 2 added files |
| Snapshot time | 2026-11-25 (Asia/Seoul) |
| Policy | `/home/vimkim/my-cubrid/CUBRID.md`, cubrid-common workflow policy, testcase lifecycle |
| Specification | JIRA CBRD-28307 (PR body used as intent); no separate design spec |
| Budget mode | Bounded (no user absolute budget). Per reviewer target ~40 tool calls; envelope 2 reviewers + coordinator replay (build + 1 focused shell TC). No hard cap enforced. |
| Agents | R1 Systems+Concurrency: opus, effort xhigh. R2 Storage+Recovery+HA+TC: sonnet, effort xhigh (pstack `interrogate reviewers` pool: opus, sonnet) |
| Verification ownership | Coordinator: build, contained native shell testkit run, line-level recheck |
