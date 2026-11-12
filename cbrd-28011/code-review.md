# Code review: PR #8491 (CBRD-28011), OOS share in SQL trace

Goal: an independent, evidence-backed review of [CUBRID/cubrid#8491](https://github.com/CUBRID/cubrid/pull/8491). The PR adds `(oos time, fetch, ioread)` to a scan's SQL trace. These figures are meant to be the OOS part of the scan's own `time`, `fetch` and `ioread`.

**Result.** No confirmed defect. On every path that executed, the OOS counts were a part of the scan's counts. Two reviewers independently found one source-only risk: in a parallel heap scan whose gather mode is `row by row`, `oos time` is not structurally bounded by the scan's `time` (R-1). Four replays did not reproduce it. Its impact is limited to trace display.

| Item | Value |
|---|---|
| Verdict | `no-confirmed-findings` |
| Follow-up review required | no (R-1 and the parallel index scan replay are optional evidence, not merge prerequisites) |
| Repository | CUBRID/cubrid, PR #8491, base `feature/oos-merge` |
| Base / merge base | `67220b7e230ff1587ba5940001d72e10477a1fc4` (same commit) |
| Head | `a4fec6f8e26a36834c3dde4df0ed0af5ecc6d914` |
| Comparison | `git diff 67220b7e230ff1587ba5940001d72e10477a1fc4 a4fec6f8e26a36834c3dde4df0ed0af5ecc6d914` |
| Patch | 11 files, +150/-7, sha256 `0301d2340f1e071910f671b5eeb0f63e8048592056e2895151636cee32c05976` |
| TC | CUBRID/cubrid-testcases#4148 (`51f346fa5`, `ca705aa21`) |
| Review date | 2026-11-12 (Asia/Seoul) |

## What changed

- [`oos_read_trace_scope`](https://github.com/CUBRID/cubrid/blob/a4fec6f8e26a36834c3dde4df0ed0af5ecc6d914/src/storage/oos_file.cpp#L2779) wraps `oos_read` and `oos_read_many` (lines 2831 and 2901). It runs only while the thread traces. It adds the thread's page-fix count, I/O-read count and elapsed time to `thread_entry::oos_read_stats`. That accumulator is never reset; only differences are read from it.
- Each scan trace window already takes fetch and ioread differences. It now also takes the `oos_read_stats` difference through [`scan_add_oos_read_stats`](https://github.com/CUBRID/cubrid/blob/a4fec6f8e26a36834c3dde4df0ed0af5ecc6d914/src/query/scan_manager.c#L8937). The windows are:
  - serial `scan_next_scan_local` (`scan_manager.c:5275`, and partitions at `:5283`),
  - the page batch (`query_executor.c:14252`, `:14261`),
  - each parallel worker's window (`px_scan_task.cpp:728`).
- The OOS figures are aggregated in three places:
  - **Parallel workers.** Page counts are summed and the longest worker's time is added (`px_scan_trace_handler.cpp:38`, `:119`, `:134`).
  - **Partitions.** The partition figures are overwritten (`:288`), the same way fetch and ioread already are.
  - **Clone merge.** Page counts are summed and the time is the maximum, matching `elapsed_scan` (`xasl_iteration.cpp:89`).
- Output appears only when `oos_reads.fetches > 0`: text at `scan_manager.c:9292`, JSON `"oos"` at `:9089`.

Recovery, WAL, page layout, replication and protocol are unaffected. The change adds no log record, no persistent byte and no client-visible field beyond the trace string.

## Confirmed findings

None.

## Safety facts

| ID | Fact | Owner | Evidence | Level |
|---|---|---|---|---|
| S1 | Every OOS value read in a scan goes through `oos_read` or `oos_read_many`. The two do not call each other, so the scopes never nest. | A, B, coordinator | Callers are `heap_oos_value_ref.cpp:122` and `heap_oos.cpp:403`, `:813`. A grep of `oos_file.cpp` shows no nested call. | 3 |
| S2 | OOS values are read eagerly, inside the scan's trace window. | A, coordinator | `heap_attrinfo_read_dbvalues` in `heap_file.c`. Runtime: an index lookup that returns 5 rows of an OOS column counted 35 OOS fetches, and a derived-table source counted 14000. | 5 |
| S3 | `oos_read_stats` is written and read only by its owning thread. Workers hand their figures over by value under `m_stats_mutex`. | B | A grep of every use. The finalize order is `add_trace` before `write_finalize`, and the leader merges after `wait_workers()`. | 3 |
| S4 | With trace on, the per-thread counters are live, and the OOS scope reads the same counters as the scan window. So OOS fetch is at most the scan's fetch, and OOS ioread at most its ioread. | A, B | The `perfmon_add_at_offset` condition is `is_watching \|\| on_trace`. Workers inherit `on_trace` (`px_task_manager.hpp:95`). | 3, plus runtime below |
| S5 | Worker OOS reaches the scan exactly once. It is not also caught by the leader's own window, because `merge_stats` runs from end, reset or close, outside `next()`, and `m_merged` guards it. | B, A | Source path. Runtime: serial and parallel runs report the same 42000 OOS fetches. | 5 |
| S6 | The timeval arithmetic handles borrow and carry, and per-window differences add up to the total. | A, replayed by coordinator | Probe `probe_add_oos` against the pinned release `libcubridsa.so` printed `whole=2500001 us parts=2500001 us fetches=10 ioreads=4 fails=0`, rc 0. The coordinator reran it with the same output; `ninja -n` shows that build is current. | 4 |
| S7 | Every changed file compiles in SERVER, SA and CS modes with `-Wall -Wextra -Werror`, and `scan_manager.h` is included only by server and SA units. | A | 15 file and mode pairs compiled with rc 0. CI builds also passed (run 43168853861). | 4 |
| S8 | OOS time stays within the scan's time for serial, batch, partition, clone merge, and the parallel `mergeable list` and `buildvalue` gathers. In those gathers the leader blocks in `read()` until every worker finishes. | A, B | Source, plus the runtime table below. | 5 |

### Runtime evidence

All runs used the debug build of the pinned head. Its `libcubrid.so` `.text` section is byte-identical to the current build output, the source tree is clean, and `ninja -n` reports nothing to rebuild. Each run used a dedicated database. `t` and `tp` hold 2000 rows each, with about 9.6 KB OOS values. `tw` and `twp` hold 6000 rows each, with 1.5 KB in-row padding so the heap exceeds the 256-page parallel threshold. Time is in ms.

| Path | Scan fetch / oos fetch | Scan ioread / oos ioread | Scan time / oos time |
|---|---|---|---|
| Serial heap, cold (`t`) | 14056 / 14000 | 2013 / 2000 | 73 / 55 |
| Serial index lookup (`t`, 2000 rows) | 46020 / 14000 | 3 / 0 | 100 / 27 |
| Serial heap, partitions p1 + p2 (`tp`, cold) | 7024 + 7024 / 7000 + 7000 | 1005 + 1005 / 1000 + 1000 | 39 + 39 / 29 + 29 |
| NL inner index scan into a partitioned table | 1950 / 350 | 27 / 27 | 5 / 1 |
| Serial heap (`tw`) | 44684 / 42000 | 5755 / 5327 | 176 / 114 |
| Parallel 4, `buildvalue` (`tw`) | 44684 / 42000 | 5757 / 5329 | 53 / 34 |
| Parallel 4, `mergeable list` with top-N sort (`tw`) | 44708 / 42000 | 5757 / 5329 | 69 / 43 |
| Parallel 4, partitioned (`twp`), p1 + p2 | 7456 + 37228 / 7000 + 35000 | 1113 + 5516 / 1000 + 5000 | 30 + 49 / 19 + 32 |
| Parallel UNION, 2 branches (clone merge) | 44684 / 42000 and 44684 / 42000 | 5263 / 4727 and 6120 / 5508 | 61 / 40 and 89 / 61 |
| Parallel 4, `row by row` (stored function in the select list), 3 runs | 68620 / 42000 | 9342 / 4537 | 200..232 / 43..53 |
| Same, leader slowed to 557 s by a PL loop | 68620 / 42000 | 10728 / 6000 | 379 / 47 |

The JSON output carried the same `"oos"` values for the scan and for each partition.

## Unverified risks

### R-1: `oos time` can exceed the scan's `time` in a `row by row` parallel heap scan

Reviewers A (opus) and B (sonnet) found this independently. Both proposed P3.

- **Where.** `trace_handler::merge_stats` adds the longest worker's OOS time to `scan_stats->oos_reads.elapsed` ([`px_scan_trace_handler.cpp:134`](https://github.com/CUBRID/cubrid/blob/a4fec6f8e26a36834c3dde4df0ed0af5ecc6d914/src/query/parallel/px_scan/px_scan_trace_handler.cpp#L134)). The partition path does the same (`:216`, `:252`, `:288`). The scan's `time` is only the leader's time inside its own scan window.
- **Argument.** With `XASL_SNAPSHOT` gather (`gather: row by row`), workers write to unbounded per-worker list files. The leader waits only when no row is ready. If workers finish early while the leader spends its time outside its window, the leader's window time can be smaller than the longest worker's OOS time. In the `mergeable list` and `buildvalue` gathers, the leader blocks until all workers finish, so the bound holds there. Index scans never use `row by row`.
- **Replay.** Not reproduced. The bound held in all four `row by row` runs above. Even with a 557 s leader, the leader's in-window list reads (379 ms) exceeded the workers' whole run (82..119 ms). A violation would need worker OOS time larger than the leader's list-read time. Many OOS chunks per row with a small output row is the likely shape. That was not built within this budget.
- **Impact.** Trace display only. A tuning user could read an OOS time larger than the scan time. OOS fetch and ioread are unaffected.
- **Cheapest decisive check.** Use a parallel-eligible table with about 200 KB OOS values per row and a non-`PARALLEL_ENABLE` stored function in the select list. Compare `oos time` with the scan's `heap time`.
- **Fix direction, if wanted.** Either clamp the printed scan-level `oos time` to `elapsed_scan`, or report the workers' OOS time on the `parallel workers` line, or document that for a parallel scan it is the longest worker's time.

### Observation, not a defect

`accumulative_trace_storage::m_stats[i].oos_reads` is copied on the first `add_stats` (`px_scan_trace_handler.cpp:215`), but the later branch never accumulates it. No code reads it today, because the per-worker line does not print OOS. Dropping the field from the per-worker copy, or accumulating it, would keep it from misleading a future reader. Both reviewers noted this.

### Accepted, by design

- OOS reads outside every scan window are counted in no scan, and neither are their page fixes. Examples are DML old-record reads, OBJFETCH and triggers. Fetch already behaves the same way.
- When a parallel scan runs inside an outer serial scan's window, the outer scan's fetch includes the workers' fetches (through `perfmon_add_values_to_local`), but its OOS figure does not. OOS remains at most fetch. Reviewer A traced this at level 2; it is not reproduced.

## Coverage

| Path | Owner | Invariant | Result |
|---|---|---|---|
| `src/storage/oos_file.cpp` | A | scope lifetime, read-path coverage, trace-off cost | complete; source, compile and runtime |
| `src/thread/thread_entry.{hpp,cpp}` | A, B | init order, ownership, reuse across pooled workers | complete; source |
| `src/query/scan_manager.{c,h}` | A | window deltas, output format, header inclusion | complete; probe and runtime |
| `src/query/query_executor.c` | A | batch and row-path windows disjoint | complete; source and runtime |
| `src/query/parallel/px_scan/px_scan_task.{cpp,hpp}` | B | worker window covers OOS reads | complete; source and runtime |
| `src/query/parallel/px_scan/px_scan_trace_handler.{cpp,hpp}` | B | merge once, partition overwrite, time bound | complete; R-1 open |
| `src/xasl/xasl_iteration.cpp` | B | clone merge keeps oos within the scan's figures | complete; source and parallel UNION runtime |
| Shared question: can OOS figures exceed, detach from, or be counted twice against the scan's figures? | A and B, independently | | both: counts hold on all paths; time open only for `row by row` (R-1) |
| Recovery | n/a | the change adds no log record, page write or undo/redo | |
| HA | n/a | the change is server-local trace state, with nothing shipped in log or replication | |

**Gaps.**
- A parallel index scan did not engage under the default index threshold (32 index pages) with the test tables. It shares the worker window and `add_trace` with the parallel heap scan, which ran; the PR author reports a manual check.
- The TC (`cbrd_28011`) masks every number, so it checks only whether the `oos` group appears, not the bound.
- Trace-off overhead was judged from the code (one branch per OOS value read) and not benchmarked.

**CI.** Run [43168853861](https://github.com/CUBRID/cubrid/actions/runs/43168853861): builds, `test_sql`, `test_shell` and `test_medium` succeeded. `test_sql_by_cci` failed; per the requester it is optional and was not analyzed.

## Dropped candidates

- **Reviewer A:** 9 hypotheses rejected with source evidence. They were lazy decode, batch and row-path double count, `merge_stats` inside its own window, counters off under trace, cross-thread writes, the header reaching client units, a time overrun in list or buildvalue gather, trace-off cost, and nested scopes.
- **Reviewer B:** 9 rejected. They were a leader double count, a partition overwrite dropping worker OOS, aliasing in `add_workers_oos_reads`, races on `m_stats`, `m_stats_last` and `m_merged`, stale `on_trace` on pooled workers, thread-entry init order, mixed serial and parallel partitions, hash and merge join workers, and missed reads.
- **Duplicates:** A-1 and B-1 merged into R-1; A-2 and B-2 merged into the observation.

## Budget

- **Mode.** Bounded, with no explicit absolute budget. No hard cap was enforced; targets only.
- **Agents.** 2 reviewers plus the coordinator, with no retries.
  - Reviewer A: about 15 min, 87 tool uses, about 276k subagent tokens.
  - Reviewer B: about 14 min, 86 tool uses, about 310k subagent tokens.
  - Both stayed within their 45-minute targets.
- **Coordinator.** Usage was not measured. Its work was runtime replay: about 15 trace queries, plus one replay that timed out at 900 s and one 9-minute replay with a slow leader.
