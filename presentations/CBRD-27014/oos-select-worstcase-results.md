# CBRD-27014 OOS SELECT Payload-Read Results

## Executive Summary

This extension measures the downside boundary of the controlled select-v2
benchmark: reading one known-demoted column (Q4), and reading every logical
column (Q5). It uses the same 14.5 KiB ordinary-heap and 22 KiB `REC_BIGONE`
baseline layouts, commits, 512 MiB buffer, 100,000 rows, cache states, and five
paired repetitions as the narrow-read test.

Against the 14.5 KiB ordinary heap baseline, OOS was slower when one demoted
column was read: **+13.6% restart-only** and **+7.7% warm** median wall time.
The compact heap no longer avoided payload I/O; it added an OOS access path,
raising median fetches from 100,005 to 133,339 restart-only. When every logical
column was read, OOS was **+7.6% restart-only** and effectively equal warm
(-0.6%).

Against the 22 KiB whole-record overflow baseline, reading one OOS column was
still faster because OOS avoided the develop-side overflow chain: **-26.8%
restart-only** and **-23.9% warm**. Reading every logical column removed nearly
all of that advantage: **-0.8% restart-only** and **-6.1% warm**.

The result is workload- and baseline-dependent. Accessing OOS payload can be a
regression relative to an ordinary in-heap record, but it can still beat a
`REC_BIGONE` baseline when only part of the payload is needed. Once every
column is needed, OOS and whole-record overflow are near parity in this test.

## Acceptance Result

| Item | Result |
| --- | --- |
| Run | `20260710-215418-27006-n100000-r5` |
| Machine audit | **PASS** |
| Measured executions | 80: 2 branches × 2 cache states × 2 layouts × 2 queries × 5 repetitions |
| SQL errors | 0 non-empty setup or measured error files |
| Correctness | Q4 returned 100,000; Q5 returned 10,050,150,000 in every run |
| Plans | Q4/Q5 serial table scans on both branches |
| OOS access evidence | OOS fetches exceeded compact-heap pages by approximately 100,000 or more |
| Restart-only I/O | Every develop repetition recorded non-zero query-trace physical reads |

Raw evidence and the generated machine summary are under
[`performance-results/select-worstcase/20260710-215418-27006-n100000-r5/`](performance-results/select-worstcase/20260710-215418-27006-n100000-r5/).
Database volumes were reproducible scratch artifacts and are excluded.

## Query Contract

Both queries used:

```sql
/*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */
```

| Query | Shape | What it forces |
| --- | --- | --- |
| Q4 | `COUNT(*) WHERE cold_1 = <exact BIT value>` | Resolve and compare one known-demoted column per row |
| Q5 | `SUM(scalars + CASE WHEN every payload = exact value ...)` | Read every scalar and validate every inline/OOS payload while returning one checksum |

Content equality is used instead of `DISK_SIZE()`: the OOS OID stores the full
logical length, so a size-only expression is not strong proof that the payload
was read. Q5 is a server-side all-logical-column read, chosen to avoid writing
1.4-2.2 GB of result data per pass. It is not an internal raw-recdes
`LC_COPYAREA`/unloaddb Expand benchmark.

## Primary Results

OOS delta is `(OOS / develop - 1) × 100`; positive is slower.

### Restart-only

| Baseline layout | Query | develop median (range) | OOS median (range) | Wall delta | Trace delta | develop → OOS fetches | develop → OOS ioreads |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 14.5 KiB heap | Q4 one OOS column | 1.40 s (1.38-1.50) | 1.59 s (1.56-1.68) | **+13.6%** | +13.4% | 100,005 → 133,339 | 100,001 → 133,335 |
| 14.5 KiB heap | Q5 all logical columns | 2.24 s (2.23-2.39) | 2.41 s (2.31-2.43) | **+7.6%** | +7.8% | 100,005 → 133,339 | 100,001 → 133,335 |
| 22 KiB overflow | Q4 one OOS column | 2.28 s (2.20-2.53) | 1.67 s (1.49-1.78) | **-26.8%** | -26.9% | 300,088 → 133,339 | 200,084 → 133,335 |
| 22 KiB overflow | Q5 all logical columns | 3.56 s (3.55-3.85) | 3.53 s (3.41-3.75) | **-0.8%** | -0.9% | 300,088 → 233,339 | 200,084 → 233,335 |

### Warm steady-state

| Baseline layout | Query | develop median (range) | OOS median (range) | Wall delta | Trace delta | develop → OOS fetches | develop → OOS ioreads |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 14.5 KiB heap | Q4 one OOS column | 0.91 s (0.87-1.08) | 0.98 s (0.95-1.14) | **+7.7%** | +8.0% | 100,001 → 133,335 | 99,992 → 133,326 |
| 14.5 KiB heap | Q5 all logical columns | 1.76 s (1.70-1.96) | 1.75 s (1.69-1.97) | **-0.6%** | 0.0% | 100,001 → 133,335 | 99,974 → 133,308 |
| 22 KiB overflow | Q4 one OOS column | 1.59 s (1.39-1.62) | 1.21 s (1.05-1.26) | **-23.9%** | -24.4% | 300,084 → 133,335 | 167,392 → 114,648 |
| 22 KiB overflow | Q5 all logical columns | 2.95 s (2.70-3.03) | 2.77 s (2.55-2.78) | **-6.1%** | -5.9% | 300,084 → 233,335 | 167,385 → 200,642 |

## Interpretation

### Ordinary heap baseline: payload access can regress

Develop reads one wide heap record per page. OOS first scans the compact heap
and then resolves demoted data. Q4 therefore increases restart-only fetches and
physical reads by about one third, matching the 13-14% elapsed/trace regression.
This is the clearest measured OOS downside in the extension.

Q5 is less punitive than a simple sum of per-column page reads would predict.
The loaded OOS records have page locality, and the content checksum proves all
payload comparisons were evaluated even though the aggregate trace counter is
not a one-increment-per-logical-column counter. The result is a modest
restart-only regression and warm parity, not a universal whole-row slowdown.

### Whole-record overflow baseline: partial payload still favors OOS

Develop must traverse the `REC_BIGONE` representation even when Q4 needs only
one large column. OOS fetches fall from about 300,000 to 133,000 and wall time
falls by 24-27%.

When Q5 needs every value, OOS fetches rise to about 233,000 and the advantage
collapses to near parity. Restart-only OOS physical reads are actually higher
(233,335 versus 200,084), while elapsed time differs by less than 1%. The warm
series retains a small 6% advantage, but it is not comparable to the 60-82%
narrow-read gain.

## Limitations

1. The host was shared, and OS page cache was not cleared. `restart-only` is not cold.
2. Q5 forces all logical values through SQL expressions but does not benchmark client transfer or raw-recdes eager Expand.
3. Query trace exposes aggregate fetch/read totals, not a dedicated `oos_read()` counter or a per-column breakdown.
4. Results compare CBRD-27006 at `3173d3bd` with develop at `e3b1bf01`, matching select-v2 rather than current `feat/oos` tip.

## Reproduction

```bash
SELECT_V2_SUITE=worst bash performance-results/run_oos_select_v2.sh 27006 100000 5
```

- Workload: [`oos-select-performance-workload.sql`](oos-select-performance-workload.sql)
- Plan: [`oos-performance-test-plan.md`](oos-performance-test-plan.md)
- Runner: [`performance-results/run_oos_select_v2.sh`](performance-results/run_oos_select_v2.sh)
- Analyzer: [`performance-results/analyze_oos_select_worstcase.mjs`](performance-results/analyze_oos_select_worstcase.mjs)
- Machine summary: [`performance-results/select-worstcase/20260710-215418-27006-n100000-r5/analysis.md`](performance-results/select-worstcase/20260710-215418-27006-n100000-r5/analysis.md)
