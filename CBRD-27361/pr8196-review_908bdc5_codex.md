# PR 8196 build and implementation review

Date: 2026-10-21 (Asia/Seoul). Audience: CUBRID engine reviewers.

The debug build succeeds, but this revision needs changes before approval. A NUMERIC NULL query reproduces an uninitialized read. Static review also finds unsafe parallel-merge allocation handling, a runtime-filter error path, and missing enable/disable control. Existing regression success does not cover these findings.

## Revision and environment

| Item | Pinned value |
| --- | --- |
| Source | [CUBRID/cubrid PR 8196](https://github.com/CUBRID/cubrid/pull/8196) |
| Issue | [CBRD-27361](https://jira.cubrid.org/browse/CBRD-27361), fetched on the analysis date |
| PR head repository and branch | `soheejung-cs/cubrid`, `CBRD-27361` |
| Reviewed commit | `908bdc5af67a752fd168b71cdf2c6f140520861d` |
| PR base and merge-base | `develop`, `c966fabc6b4c8ac86aa4b5abb0a4cbefae01bf5b` |
| Source checkout and branch | `/home/vimkim/gh/cb/review-CBRD-27361-pr-8196`, `review-CBRD-27361-pr-8196` |
| Creation | `cubrid-pr-review-worktree https://github.com/CUBRID/cubrid/pull/8196 --prepare` |
| Build | Linux x86_64, GCC 11.5.0, `debug_gcc`, CUBRID `11.5.0.2736-908bdc5` |
| Installation | `/home/vimkim/.cub/install/review-CBRD-27361-pr-8196/debug_gcc` |
| Local source modifications | No engine edits or instrumentation patches |
| Review comparison | 33 commits including two develop merges, 36 files, 14,669 insertions and 3,590 deletions |

The comparison was fixed before the two independent Standards and Spec reviews:

```bash
git diff c966fabc6b4c8ac86aa4b5abb0a4cbefae01bf5b...908bdc5af67a752fd168b71cdf2c6f140520861d
git log c966fabc6b4c8ac86aa4b5abb0a4cbefae01bf5b..908bdc5af67a752fd168b71cdf2c6f140520861d --oneline
```

## Execution contracts

[heap_page_collect_visible](https://github.com/CUBRID/cubrid/blob/908bdc5af67a752fd168b71cdf2c6f140520861d/src/storage/heap_file.c#L8196) collects visible records while their page remains fixed. The chunk stores PEEK pointers. A relocated, overflow, or log-version record sends the current chunk and remaining page through the row path.

[expr_batch_run](https://github.com/CUBRID/cubrid/blob/908bdc5af67a752fd168b71cdf2c6f140520861d/src/query/expr_batch.c#L3958) evaluates column arrays and the selection vector. Its fallback contract requires replay to preserve semantics. Consumers must copy retained records or finish using page pointers before the producer releases the page. The [filter iterator](https://github.com/CUBRID/cubrid/blob/908bdc5af67a752fd168b71cdf2c6f140520861d/src/query/scan_manager.c#L8522) copies surviving records before returning rows to nested execution.

The [GROUP BY cache](https://github.com/CUBRID/cubrid/blob/908bdc5af67a752fd168b71cdf2c6f140520861d/src/query/query_executor.c#L11658) stores pointers into the live aggregate table. Every eviction must invalidate those pointers before slab reuse. A [runtime filter](https://github.com/CUBRID/cubrid/blob/908bdc5af67a752fd168b71cdf2c6f140520861d/src/query/query_hash_join.c#L4859) must contain every eligible build key before it can reject probe rows.

## Standards

The review used personal CUBRID policies, `CONTRIBUTING.md`, `src/AGENTS.md`, and the query/storage instructions. The personal policy permits throwing STL operations only with local exception translation. Tool-enforced formatting issues were excluded.

1. **P1 — Unhandled worker allocation and exception boundary.** [query_executor.c:7005–7008](https://github.com/CUBRID/cubrid/blob/908bdc5af67a752fd168b71cdf2c6f140520861d/src/query/query_executor.c#L7005) directly submits `new parallel_query::callable_task(...)`. Personal `CUBRID.md` requires local translation of STL exceptions into CUBRID errors. The constructor stores the capture in [std::function](https://github.com/CUBRID/cubrid/blob/908bdc5af67a752fd168b71cdf2c6f140520861d/src/query/parallel/px_callable_task.hpp#L84), which can allocate and throw. The wrapped server `new` can also return NULL. Neither failure has a local path that joins submitted workers and releases the merge state. Allocate and check tasks separately, and translate construction failures after joining submitted work. **Static finding; allocation failure was not injected.**

2. **P2 — Scan failure publishes a partial runtime filter.** [query_hash_join.c:4935–4971](https://github.com/CUBRID/cubrid/blob/908bdc5af67a752fd168b71cdf2c6f140520861d/src/query/query_hash_join.c#L4935) uses `while (qfile_scan_list_next (...) == S_SUCCESS)` and publishes the filter after any loop termination. It does not distinguish `S_ERROR` from `S_END`. This conflicts with the C error model in `src/AGENTS.md`. An incomplete exact key set is unsafe for rejecting probe rows. Capture the terminal scan code and propagate failure before installing the filter. **Static error-path finding; no temp-file fault was injected.**

3. **P1 — Allocation-failure cleanup indexes a NULL array.** [query_executor.c:7034–7039](https://github.com/CUBRID/cubrid/blob/908bdc5af67a752fd168b71cdf2c6f140520861d/src/query/query_executor.c#L7034) guards only `px->out_rows`. If its allocation succeeds but `out_partials` fails at line 6970, cleanup still evaluates `px->out_partials[w]`. The error path can crash instead of returning the allocation error. Guard each array independently. **Static finding, independently confirming [existing Greptile feedback](https://github.com/CUBRID/cubrid/pull/8196#discussion_r4322136755).**

No additional Fowler smell warranted a finding. Typed-loop repetition serves the optimization, and documented repository conventions take precedence over general refactoring heuristics.

## Spec

These findings use the fetched JIRA description. The issue's design attachment was not examined, so requirements asserted here are limited to the description and PR body.

1. **Missing required on/off control.** JIRA requires “hidden 파라미터로 on/off” before merge. Eligible scans activate in [query_executor.c:12735](https://github.com/CUBRID/cubrid/blob/908bdc5af67a752fd168b71cdf2c6f140520861d/src/query/query_executor.c#L12735) and [px_scan_task.cpp:473](https://github.com/CUBRID/cubrid/blob/908bdc5af67a752fd168b71cdf2c6f140520861d/src/query/parallel/px_scan/px_scan_task.cpp#L473). [scan_manager.c:8196](https://github.com/CUBRID/cubrid/blob/908bdc5af67a752fd168b71cdf2c6f140520861d/src/query/scan_manager.c#L8196) checks eligibility without an enable parameter. The diff adds no parameter definition. **Source-proven requirement gap.**

2. **Concurrent UPDATE/vacuum acceptance evidence is missing.** JIRA requires “UPDATE/vacuum 병행 동시성 퍼저”, including the PEEK retry path. The PR describes two-session RR reproductions. The added [shell testcase](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8ee3462cad783b167b9e90fb8ff5ef4a3aa551a2/shell/_06_issues/_26_2h/cbrd_27361/cases/cbrd_27361.sh#L53) runs sequential result and coverage sessions at lines 53 and 66. It supplies no concurrent updater/vacuum launcher. **Acceptance evidence gap; this does not establish a concurrency failure or exclude external fuzz work.**

3. **Broader scope needs explicit acceptance.** JIRA initially specifies “병렬 스캔 워커 루프 1곳”, fixed-width filter/rest columns, and unchanged behavior for ineligible string-filter queries. It also describes later phases for aggregation and serial execution. This PR includes serial activation, string leaves, spill merging, slabs, and join runtime filters. The author documents the expansion. **Confirm acceptance of the combined phases and additional features, or use the proposed review split. Expansion alone is not a defect.**

4. **Performance completion remains partial.** JIRA requires “성능 수치(전/후) JIRA 기록”. The fetched issue contains no measurements. The PR supplies benchmark tables but explicitly says they predate the current fixes and develop merges. **Record current-head measurements and the comparison revision in JIRA. This is an evidence gap.**

## Existing feedback verification

The Standards cleanup finding above duplicates an existing comment. The following checks distinguish additional confirmed feedback from an unresolved reproduction question.

| Existing comment | Verification at the reviewed commit | Consequence |
| --- | --- | --- |
| [NULL NUMERIC cell](https://github.com/CUBRID/cubrid/pull/8196#discussion_r4322136772) | **Reproduced under Valgrind.** `eb_cell_num()` returns zero without writing `nv` for NULL; `eb_raw_kid()` reads `nv.is_negative` and `nv.coefficient` before checking `got`. | Undefined behavior on ordinary NULL data. The observed query still returned the expected row. |
| [Evicted GROUP BY cache entries](https://github.com/CUBRID/cubrid/pull/8196#discussion_r4322136746) | **Confirmed by source reasoning.** Removing a cache slot shifts colliding entries at lines 11827–11828. The eviction loop keeps using the original `note_slot` array at lines 11908–11913. A second evicted group can move and escape invalidation. | A later cache hit can use an evicted or reused aggregate value. No wrong-result SQL reproduction was obtained in this review. |
| [Repeated predicate side effects](https://github.com/CUBRID/cubrid/pull/8196#discussion_r4322136765) | Residual predicates can execute before whole-chunk fallback at `expr_batch.c:3676–3680`. A serial/long-string probe consumed four sequence values for four rows and did **not** reproduce repetition. | Keep this as a targeted validation question. A reachable effectful predicate and fallback order must be demonstrated before claiming a reproduced defect. |

## Build and runtime verification

The following local steps completed through the prepared worktree interface:

```bash
direnv exec . just configure
direnv exec . just build
direnv exec . just test
direnv exec . just install
```

Configuration, compilation, linking, and installation passed. `just test` exited zero but printed `No tests were found!!!`. **Zero configured CTest tests ran.** The preset's OOS/SPAGE/page-buffer options do not establish test coverage for this revision.

An isolated host environment was initialized explicitly after installation. Standalone SQL returned the expected results for numeric aggregation, a NULL numeric filter, and a long-string fallback candidate. GDB reached `eb_raw_kid()` through `expr_batch_run()` and `qexec_batch_scan_chain()`, establishing that the numeric probe entered the new path.

The first smoke script tried a server-only `parallelism=0` setting and received an error in standalone mode. Its `SHOW TRACE` results were NULL. Those lines are not validation evidence. The later projection-only memory probe contained neither setting nor trace statements.

### Reproduce the NUMERIC NULL read

Use a new, isolated database with this build. Run [the setup SQL](repro/null-numeric-setup.sql) once, then [the probe SQL](repro/null-numeric-probe.sql):

```sql
create table review_null_first (n integer, x numeric(18,2));
insert into review_null_first values (1,null),(2,1.25);
commit;

select n from review_null_first where x < 10;
```

Run the probe separately under Memcheck:

```bash
valgrind --tool=memcheck --track-origins=yes --leak-check=no \
  --error-exitcode=77 --log-file=null-numeric-valgrind.log \
  csql -S -u dba -i null-numeric-probe.sql testdb
```

Observed result: one row, `n = 2`. Memcheck exited **77**, with **one error from one context**:

```text
Conditional jump or move depends on uninitialised value(s)
  at eb_raw_kid (...) (expr_batch.c:3471)
  by eb_filter (...) (expr_batch.c:3654)
  by expr_batch_run (...) (expr_batch.c:3997)
Uninitialised value was created by a stack allocation
  at eb_raw_kid (...) (expr_batch.c:3430)
ERROR SUMMARY: 1 errors from 1 contexts
```

The earlier aggregate probe also reported serialization warnings. Those were not attributed to this PR and are excluded from the finding count. The projection-only probe isolates the new batch warning.

Raw local evidence remains under `build_preset_debug_gcc/` in the source worktree: `build.log`, `ctest-review.log`, `install-review.log`, `review-null-gdb.log`, `review-null-projection-valgrind.log`, and `review-null-projection-result.log`. The two retained SQL files are necessary to reproduce the finding. Raw logs and intermediate probes remain local.

## CI and review disposition

At head `908bdc5af`, the [CUBRID CI run](https://github.com/CUBRID/cubrid/actions/runs/39374265629) reports passed debug/release builds and SQL, medium, and shell suites. The [TC Merge Gate](https://github.com/CUBRID/cubrid/actions/runs/39380404935/job/118487988070) remains failed. Its linked testcase PRs are [public 3791](https://github.com/CUBRID/cubrid-testcases/pull/3791) and [private 4469](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4469). CI evidence is reported for the PR head, even though the issue-comment workflow's own revision is the develop commit.

Resolve the confirmed defects and agree the feature controls and accepted scope before approval. Then verify fixes with focused cases for NULL numeric cells, colliding cache entries under eviction, and allocation/list-scan failures. Require the specified concurrency evidence and current-head performance measurements. Complete the remaining review through the author's six proposed slices.

This review did not rerun full SQL/medium/shell suites, measure performance, inject parallel allocation or temp-file failures, or run the concurrency fuzzer. It made no source fixes, remote review submissions, pushes, CI triggers, or merges.

Standards: **3 findings**, worst **P1** in parallel allocation/cleanup. Spec: **4 findings or acceptance questions**, with the missing enable/disable control the clearest implementation gap. Existing-feedback verification additionally confirms the NUMERIC NULL read at runtime and the cache invalidation defect by source reasoning.
