# CBRD-27194

Page buffer single-mutex lifecycle: initialize and destroy each non-array mutex of `pgbuf_Pool` exactly once on every init and final path.

- Engine PR: [CUBRID/cubrid#8780](https://github.com/CUBRID/cubrid/pull/8780)
- Linked testcase PR: CUBRID/cubrid-testcases-private-ex#5198 (private repository)

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [code-review.md](code-review.md) | Code review of #8780 at head `a2a9414d97`: verdict, safety facts, runtime verification, non-blocking suggestions | 2026-11-27 | 2026-11-27 | Publish the cubrid-code-review result linked from the PR comment |
