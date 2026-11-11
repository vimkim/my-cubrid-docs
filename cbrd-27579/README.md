# CBRD-27579: TCL, DDL, and DML in stored routines called inside SQL statements or triggers

[CBRD-27579](https://jira.cubrid.org/browse/CBRD-27579) (Correct Error, status Develop; relates to CBRD-27603, CBRD-27591, CBRD-27614). No PR is linked here yet. Source evidence: develop `e64a04a79`; the fix was not yet in develop `38c931e7d`.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [comment-develop-repro.md](comment-develop-repro.md) | Korean comment, posted as [comment 4778317](https://jira.cubrid.org/browse/CBRD-27579?focusedCommentId=4778317#comment-4778317) on 2026-11-11: the smallest SA-mode repro (`select cf () from db_root` with a PL/CSQL function that COMMITs or ROLLBACKs) on develop `e64a04a79`. Debug `csql -S` stops on `pgbuf_unfix_all` assert, release `csql -S` segfaults, CS works. gdb stack and the held heap-scan page | 2026-11-11 | 2026-11-11 | Add develop SA evidence to the existing issue instead of filing a duplicate |
