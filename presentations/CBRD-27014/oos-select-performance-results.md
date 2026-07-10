# CBRD-27014 OOS SELECT Performance Results

## Executive Summary

The revised benchmark validates OOS's narrow-read advantage under the two storage layouts requested in [`review-41a2e4e.md`](review-41a2e4e.md): an ordinary 14.5 KiB heap record on `develop`, and a 22 KiB `REC_BIGONE` overflow record on `develop`. The OOS branch reduces both layouts to approximately 4 KiB heap records by demoting only the large variable columns.

The strongest result is the overflow baseline. For full scans that read only `id`, OOS reduced median wall time by **60-82%** and query-trace time by **66-84%**. Against the 14.5 KiB ordinary heap baseline, the same queries improved by **31-53%** wall time and **36-55%** trace time.

Random non-covering range reads also improved, but the benefit depended on cache state and baseline layout:

- versus ordinary heap: **26% faster restart-only**, but only **6% faster warm**;
- versus `REC_BIGONE`: **35% faster restart-only** and **29% faster warm**.

This is not a universal SELECT speedup. OOS wins when compact heap records reduce pages fetched or physically read. When an index-driven workload still performs one scattered heap lookup per row and the OOS heap plus index does not fit comfortably in the 512 MiB buffer, the page-density advantage can shrink substantially.

The read benefit also has a space cost in this dataset: permanent data usage was **5,847 MiB on OOS versus 4,806 MiB on develop**, an increase of 1,041 MiB (21.7%).

## Acceptance Result

The full run passed the automated acceptance gate.

| Item | Result |
| --- | --- |
| Run | `20260710-205439-27006-n100000-r5` |
| Machine audit | **PASS** |
| Measured runs | 120 branch-runs: 2 branches × 2 cache states × 2 layouts × 3 queries × 5 repetitions |
| SQL errors | 0 non-empty setup or measured error files |
| Correctness | Q1 sums, Q2 row counts/checksums, and Q3 row counts/checksums matched on both branches |
| Plans | Q1/Q2 table scan; Q3 named non-covering index scan followed by heap lookup |
| Parallelism | Disabled with `PARALLEL(0)` and `NO_PARALLEL_HEAP_SCAN` |
| Restart-only I/O | Every develop repetition recorded non-zero query-trace physical reads |

The machine-generated audit and all per-run values are under [`performance-results/select-v2/20260710-205439-27006-n100000-r5/`](performance-results/select-v2/20260710-205439-27006-n100000-r5/). The database volume files are reproducible scratch artifacts and are excluded from version control.

## Test Contract

| Item | Value |
| --- | --- |
| Baseline | `develop` at `e3b1bf014ac37fcf3b72b9816a245ff23d9a5e1f` |
| OOS | `CBRD-27006-oos-recdes-locality` at `3173d3bd5a9c615a17fb9425c2e1c2fee1095474` |
| Build | GCC `RelWithDebInfo` release installs rebuilt with the local ccache-backed build workflow before measurement |
| Database | Separate `perf27014d` and `perf27014o` databases; 16 KiB data/log pages; 8 GiB initial permanent volume |
| Buffer | `data_buffer_size=512M` on both branches |
| Rows | 100,000 per layout |
| Repetitions | Five paired repetitions; develop/OOS order alternated by repetition |
| Cache states | `restart-only` and `warm`; no true-cold claim |
| Host | 2 × 20-core / 80-logical-CPU Intel Xeon Gold 5218R; 125 GiB RAM; XFS on `/dev/mapper/rl-home` |
| Host isolation | Shared host; `db25350_ddl` and `cdclatdb` servers remained running throughout |
| Run window | 2026-07-10 20:54-21:11 KST; load average approximately 1.8-2.7 |

The branches used unique database names under the existing CUBRID master. Their queries were not run simultaneously. This avoided database-name races without stopping unrelated CUBRID servers.

## Validated Storage Layouts

### Layout A: ordinary heap baseline

The logical payload contains three 1,300-byte inline-target values and two demotion-target values of 5,300 and 5,200 bytes.

| Branch | Average heap record | Heap pages | Overflow records | Live OOS records | Observed layout |
| --- | ---: | ---: | ---: | ---: | --- |
| develop | 14,480 B | 100,000 | 0 | 0 | One ordinary heap record per page |
| OOS | 3,996 B | 33,334 | 0 | 200,000 | Two large columns demoted; about three heap records per page |

### Layout B: whole-record overflow baseline

The logical payload contains the same three inline-target values and three demotion-target values of 7,000, 6,000, and 5,000 bytes.

| Branch | Average heap record | Heap/overflow pages reported | Overflow records | Live OOS records | Observed layout |
| --- | ---: | ---: | ---: | ---: | --- |
| develop | 22,016 B | 200,083 | 100,000 | 0 | Every row stored as `REC_BIGONE` |
| OOS | 4,020 B | 33,334 heap pages | 0 | 300,000 | Three large columns demoted; no OOS-plus-bigone coexistence |

The OOS branch reported 100,001 physical OOS pages for Layout A and 200,001 for Layout B. Only the live-record and physical-page fields are used here; the `Logical data size` values printed by `;oos_stats` were inconsistent with the known payload sizes and are not used as evidence.

## Query Matrix

Each query used:

```sql
/*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */
```

| Query | SQL shape | Purpose |
| --- | --- | --- |
| Q1 | `SELECT SUM(id)` | Server-side narrow full scan without result-transfer volume |
| Q2 | `SELECT id` | Narrow full scan including serialization and transfer of all 100,000 IDs |
| Q3 | `SELECT hot_col WHERE lookup_key BETWEEN ...` | 1,000 fixed-order, non-overlapping 100-key ranges; randomized physical row order; non-covering heap lookup |

`id` is deliberately not indexed. `lookup_key` is a deterministic permutation of insertion order and has a separate index; `hot_col` is not in that index. The accepted Q3 plan therefore reads the index and then fetches the non-OOS `hot_col` from scattered heap records.

No measured query references a demoted `cold_*` column. CUBRID does not expose a direct per-query `oos_read()` counter in this setup, so the absence of OOS payload access is established by projection, the lazy attribute-read design, and the accepted plans rather than claimed as a measured zero counter.

## Primary Results

OOS delta is `(OOS / develop - 1) × 100`; negative is faster.

### Restart-only

These runs restart the database server before every repetition, clearing the CUBRID buffer pool but not the host OS page cache.

| Baseline layout | Query | develop median (range) | OOS median (range) | Wall delta | Trace delta | develop → OOS fetches | develop → OOS ioreads |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 14.5 KiB heap | Q1 `SUM(id)` | 0.93 s (0.87-0.97) | 0.61 s (0.52-0.61) | **-34.4%** | -35.9% | 100,005 → 33,339 | 100,001 → 33,335 |
| 14.5 KiB heap | Q2 all IDs | 1.10 s (1.04-1.16) | 0.76 s (0.57-0.76) | **-30.9%** | -38.0% | 100,305 → 33,639 | 100,007 → 33,335 |
| 14.5 KiB heap | Q3 random ranges | 7.61 s (4.70-8.66) | 5.63 s (3.35-6.21) | **-26.0%** | -40.9% | 103,256 → 103,256 | 100,274 → 37,979 |
| 22 KiB overflow | Q1 `SUM(id)` | 1.69 s (1.63-1.72) | 0.57 s (0.56-0.62) | **-66.3%** | -67.1% | 300,088 → 33,339 | 200,084 → 33,335 |
| 22 KiB overflow | Q2 all IDs | 1.81 s (1.57-1.95) | 0.73 s (0.70-0.75) | **-59.7%** | -65.9% | 300,388 → 33,639 | 200,093 → 33,335 |
| 22 KiB overflow | Q3 random ranges | 9.10 s (5.62-9.32) | 5.93 s (4.20-6.54) | **-34.8%** | -65.2% | 403,256 → 103,256 | 200,903 → 37,979 |

### Warm steady-state

Each exact workload received one discarded warm-up, followed by five measurements without restarting either database. Because each dataset is larger than the 512 MiB database buffer, `warm` means steady-state repeated access, not that every page fits in memory.

| Baseline layout | Query | develop median (range) | OOS median (range) | Wall delta | Trace delta | develop → OOS fetches | develop → OOS ioreads |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14.5 KiB heap | Q1 `SUM(id)` | 0.57 s (0.41-0.58) | 0.27 s (0.24-0.29) | **-52.6%** | -54.1% | 100,001 → 33,335 | 99,992 → 33,326 |
| 14.5 KiB heap | Q2 all IDs | 0.72 s (0.61-0.73) | 0.39 s (0.34-0.44) | **-45.8%** | -55.4% | 100,289 → 33,623 | 99,983 → 33,317 |
| 14.5 KiB heap | Q3 random ranges | 6.30 s (4.30-6.56) | 5.91 s (5.82-6.28) | **-6.2%** | -7.1% | 103,252 → 103,252 | 101,225 → 101,173 |
| 22 KiB overflow | Q1 `SUM(id)` | 0.91 s (0.86-1.13) | 0.16 s (0.11-0.17) | **-82.4%** | -84.2% | 300,084 → 33,335 | 167,598 → 931 |
| 22 KiB overflow | Q2 all IDs | 0.91 s (0.74-1.18) | 0.35 s (0.35-0.36) | **-61.5%** | -76.9% | 300,372 → 33,623 | 167,589 → 925 |
| 22 KiB overflow | Q3 random ranges | 7.59 s (7.37-8.29) | 5.38 s (4.96-5.51) | **-29.1%** | -78.9% | 403,252 → 103,252 | 168,159 → 2,917 |

## Interpretation

### Why full scans improve

For Layout A, OOS packs approximately three heap records per page instead of one. Q1 fetches fell from about 100,000 to 33,000, explaining the 34-53% wall-time reduction.

For Layout B, `develop` must fetch the heap record plus its overflow chain. Q1/Q2 fetches fell from about 300,000 to 33,000 on OOS, explaining the larger 60-82% wall-time reduction.

Q2 gains are generally smaller than Q1 trace gains because both branches still serialize and transfer 100,000 IDs to `csql`.

### Why random-range gains vary

Q3 performs 100,000 non-covering index-to-heap lookups. Against Layout A, the total page-fetch count is identical because both branches perform one lookup per returned row. OOS helps only when denser pages remain reusable in the buffer: restart-only ioreads fell by 62%, but in the warm steady-state series both branches recorded about 101,000 ioreads and the wall-time gain narrowed to 6%.

Against Layout B, OOS additionally removes the overflow-chain traversal. Total fetches fell from 403,000 to 103,000, so the advantage remained material in both cache states.

### Space and write-side tradeoff

The two-table database used 5,847 MiB of permanent data on OOS and 4,806 MiB on develop. The OOS representation was 1,041 MiB larger because compact heap records coexist with separate slotted OOS pages and their page/slot overhead. This report therefore supports a read-locality benefit, not a blanket storage-efficiency claim.

The initial two-table load took 110.29 seconds on develop and 104.90 seconds on OOS. The loads were sequential on a shared host and were not repeated as paired write benchmarks, so this difference is recorded for traceability but not interpreted as an INSERT performance result.

## Limitations

1. The host was shared. Two unrelated CUBRID servers remained active, and load average varied during the 17-minute run.
2. No privileged OS-cache clearing was available. `restart-only` is not called cold, and warm results do not imply that the full dataset fits in the CUBRID buffer.
3. Restart-only Q3 raw times vary substantially as the OS cache evolves. Query trace counters and medians are more informative than any single elapsed value.
4. The OOS target is CBRD-27006, not the current `feat/oos` tip. The result measures the branch requested for continuity with the earlier reviewed benchmark.
5. The workload reads only inline columns. The controlled Q4/Q5 payload-read extension is reported in [`oos-select-worstcase-results.md`](oos-select-worstcase-results.md); UPDATE and INSERT remain in the earlier exploratory [`oos-performance-results.md`](oos-performance-results.md).
6. The anomalous `;oos_stats` logical-size fields were excluded. Live record counts, physical pages, `SHOW HEAP CAPACITY`, query results, and SQL trace were internally consistent.

## Reproduction and Evidence

- Reviewable DDL/DML: [`oos-select-performance-workload.sql`](oos-select-performance-workload.sql)
- Test plan: [`oos-performance-test-plan.md`](oos-performance-test-plan.md)
- Paired runner: [`performance-results/run_oos_select_v2.sh`](performance-results/run_oos_select_v2.sh)
- Machine analyzer: [`performance-results/analyze_oos_select_v2.mjs`](performance-results/analyze_oos_select_v2.mjs)
- Machine summary: [`performance-results/select-v2/20260710-205439-27006-n100000-r5/analysis.md`](performance-results/select-v2/20260710-205439-27006-n100000-r5/analysis.md)
- Structured summary and every raw run: [`performance-results/select-v2/20260710-205439-27006-n100000-r5/analysis.json`](performance-results/select-v2/20260710-205439-27006-n100000-r5/analysis.json)

Pilot runs and the first aborted full-load attempt are excluded from all reported values. Only the run with the machine `PASS` marker and final `completed.txt` is reported.
