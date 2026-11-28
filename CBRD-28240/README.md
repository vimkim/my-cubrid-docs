# CBRD-28240

Speed up the fetch of unloaddb: read heaps in file order with read-ahead, fetch over several connections on one snapshot, and write several object files.

- Engine PR: [CUBRID/cubrid#8677](https://github.com/CUBRID/cubrid/pull/8677) (author ctshim, base `develop`)

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [ci-analysis.md](ci-analysis.md) | Attribution of run 46011518777 attempt-1 failures (cbrd_28181 via CCI, apis_1125 shell) at head `fafffbbab98a` | 2026-11-28 | 2026-11-28 | Decide whether the two rerun-passing failures are PR bugs, develop bugs, or flaky testcases |
