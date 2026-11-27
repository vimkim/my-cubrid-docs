# CBRD-28274

Partition redistribution (REORGANIZE, COALESCE, REMOVE PARTITIONING) after ADD/DROP COLUMN moves rows of an older representation with the wrong layout on release/11.4.

- JIRA: <https://jira.cubrid.org/browse/CBRD-28274>
- Engine PR: [CUBRID/cubrid#8690](https://github.com/CUBRID/cubrid/pull/8690) (release/11.4, hornetmj)
- TC PRs: [cubrid-testcases#4397](https://github.com/CUBRID/cubrid-testcases/pull/4397) (release/11.4), [#4371](https://github.com/CUBRID/cubrid-testcases/pull/4371) (develop), [#4387](https://github.com/CUBRID/cubrid-testcases/pull/4387) (closed, duplicate of #4371)

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr-8690-review.md](pr-8690-review.md) | Code review of #8690 at `46e71173c0` with TC PR analysis: crash-redo finding F1, safety facts, backport comparison with develop, verification | 2026-11-26 | 2026-11-26 | Record the review evidence and verdict |
| [pr-8690-delta-review.md](pr-8690-delta-review.md) | Delta re-review of #8690 at `182431bea7`: F1 fix, INSID flag clearing, CBRD-28107 delid fix on release/11.4, crash-restart and TC verification, APPROVE verdict | 2026-11-27 | 2026-11-27 | Record the re-review evidence and verdict after the author's fix |
