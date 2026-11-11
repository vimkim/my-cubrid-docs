# CBRD-27780

Related PRs are [Engine PR 8402](https://github.com/CUBRID/cubrid/pull/8402) and [testcase PR 4737](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4737).

The reviews below retain the exact source snapshots from 2026-11-11. The engine review requires follow-up execution. The testcase review confirms one P3 scanner defect.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [review.md](review.md) | Pinned engine review and recovery risks | 2026-11-11 | 2026-11-11 | Assess deallocation, page reuse, and rollback safety |
| [coverage.md](coverage.md) | Engine review coverage and remaining checks | 2026-11-11 | 2026-11-11 | Record the evidence for each changed path |
| [handoff.md](handoff.md) | Engine recovery follow-up | 2026-11-11 | 2026-11-11 | Resume integrated verification of the open recovery risks |
| [testcase-review.md](testcase-review.md) | Testcase review and confirmed P3 scanner finding | 2026-11-11 | 2026-11-11 | Assess the regression test and its oracles |
| [testcase-coverage.md](testcase-coverage.md) | Testcase coverage and execution limits | 2026-11-11 | 2026-11-11 | Keep scanner, reuse, and redo evidence distinct |
| [testcase-handoff.md](testcase-handoff.md) | Testcase follow-up and required native runs | 2026-11-11 | 2026-11-11 | Resume the unverified recovery and page-reuse checks |

The [scanner replay](evidence/scanner-replay.sh) supports the confirmed testcase finding. It extracts the pinned private-repository functions and uses disposable local files.
