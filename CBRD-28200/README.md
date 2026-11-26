# CBRD-28200

An XA (2PC) participant that prepared, crashed and restarted must still apply its unique-index statistics exactly once when it commits. A prepared transaction's commit must also log its statistics commit records.

Related PRs: [CUBRID/cubrid#8674](https://github.com/CUBRID/cubrid/pull/8674) (engine, author `hornetmj`); TC PR cubrid-testcases-private-ex#5070 (private); cubrid-testcases#4372 (no changes).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr8674-review.md](pr8674-review.md) | Code review of PR #8674 at head `aff1baed63`: no confirmed findings, exactly-once crash-point analysis, safety facts, head/base TC runs (head OK 25/25, base NOK 14), non-blocking suggestions, a pre-existing 2PC checkpoint window | 2026-11-26 | 2026-11-26 | Review PR #8674 and its TC PR and decide approval |
