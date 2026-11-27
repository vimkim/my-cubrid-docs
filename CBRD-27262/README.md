# CBRD-27262

[PGBUF] Restore the BCB state when a flush fails after the TDE or DWB preparation step.

- Jira: [CBRD-27262](http://jira.cubrid.org/browse/CBRD-27262), a sub-task of CBRD-27193 (page buffer epic)
- Engine PR: [CUBRID/cubrid#8786](https://github.com/CUBRID/cubrid/pull/8786)
- TC PRs: [cubrid-testcases#4507](https://github.com/CUBRID/cubrid-testcases/pull/4507) and private testcase repository #5203. Both are drafts with no changes.

## Documents

- [pr8786-review.md](pr8786-review.md): code review at head `7a7a48ac1a0a`, verdict no-confirmed-findings, with two non-blocking P3 risks.
