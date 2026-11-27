# CBRD-28200

An XA (2PC) participant that prepared, crashed and restarted must still apply its unique-index statistics exactly once when it commits. A prepared transaction's commit must also log its statistics commit records.

Related PRs: [CUBRID/cubrid#8674](https://github.com/CUBRID/cubrid/pull/8674) (engine, author `hornetmj`); TC PR cubrid-testcases-private-ex#5070 (private); cubrid-testcases#4372 (no changes).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr8674-review.md](pr8674-review.md) | Code review of PR #8674 through head `681ee7ac4b` (prior snapshot `aff1baed63` + delta `a117284fae` / merge `681ee7ac4b` + TC `053fbe5820`): no confirmed findings, exactly-once crash-point analysis, safety facts, head/base TC runs (head OK 25/25), CI parity, resolved `N2`/`N4`/`T1`, pre-existing 2PC checkpoint window | 2026-11-26 | 2026-11-27 | Review PR #8674 and its TC PR and decide approval |
