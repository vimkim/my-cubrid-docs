# CBRD-27014 OOS Performance Results

## Scope and Verdict

This report contains only the completed, valid warm measurements for S1-S4. Each scenario has five runs on `develop` and the OOS branch. `OOS delta` is `(OOS median / develop median - 1) * 100`; lower elapsed time is better.

| Scenario | develop median (range) | OOS median (range) | OOS delta | Result |
| --- | ---: | ---: | ---: | --- |
| S1 narrow `SUM(hot_col)` scan | 0.09 s (0.08-0.09) | 0.10 s (0.10-0.11) | +11.1% | No measured narrow-scan improvement in this warm workload. |
| S2 payload equality scan | 0.21 s (0.20-0.23) | 0.45 s (0.44-0.48) | +114.3% | OOS payload access was materially slower. |
| S3 100,000-row bulk INSERT | 30.35 s (29.74-30.60) | 30.60 s (30.30-31.37) | +0.8% | Essentially neutral within this shared-host run. |
| S4 update only `hot_col` | 1.99 s (1.93-2.17) | 2.68 s (2.66-2.73) | +34.7% | OOS was slower and consumed more permanent data space. |

The results do **not** support a performance-speedup statement for S1 on this host and dataset. They do show the corresponding payload-read and small-column-update costs. A dedicated-host cold/warm experiment with query-level counters is required before making a storage-I/O locality claim.

## Test Contract

| Item | Value |
| --- | --- |
| Baseline | `/home/vimkim/gh/cb/develop` at `e3b1bf014ac37fcf3b72b9816a245ff23d9a5e1f` |
| OOS branch | `/home/vimkim/gh/cb/CBRD-27006-oos-recdes-locality` at `3173d3bd5a9c615a17fb9425c2e1c2fee1095474` |
| Build | `just build` completed in both worktrees; GCC `RelWithDebInfo` release install; `csql` 11.5.0 |
| Database | Fresh `perf27014` database per S3/S4 run; 16 KiB DB/log pages; 2 GiB initial data and log volumes |
| Server config | `data_buffer_size=512M`, `log_buffer_size=256M`; private port 15230 only during the runs, then restored |
| Dataset | 100,000 rows; `id INT`, `hot_col INT`, `payload BIT VARYING`; payload is 32,768 bits (4 KiB) of identical bytes |
| Cache state | Warm only: one warm-up was discarded before S1/S2, then five runs. No OS page-cache clearing was performed. |
| Host | Linux 5.14.0-570.30.1.el9_6.x86_64; 2 x 20-core / 80-logical-CPU Intel Xeon Gold 5218R; 125 GiB RAM; `/home` on XFS (`/dev/mapper/rl-home`) |

The comparison was sequential rather than randomized by branch pair, because one isolated CUBRID server was operated at a time. The host was not dedicated: other users' CUBRID/CTP processes were observed during the measurements. These conditions make the elapsed-time numbers useful as an observed comparison, but not as a publishable isolated benchmark.

## Raw Elapsed Times

All values are seconds, sorted within each five-run set.

| Scenario | develop raw values | OOS raw values |
| --- | --- | --- |
| S1 | 0.08, 0.09, 0.09, 0.09, 0.09 | 0.10, 0.10, 0.10, 0.10, 0.11 |
| S2 | 0.20, 0.21, 0.21, 0.22, 0.23 | 0.44, 0.44, 0.45, 0.47, 0.48 |
| S3 | 29.74, 30.19, 30.35, 30.43, 30.60 | 30.30, 30.37, 30.60, 31.15, 31.37 |
| S4 | 1.93, 1.96, 1.99, 2.06, 2.17 | 2.66, 2.67, 2.68, 2.69, 2.73 |

S3 median throughput was 3,294.9 rows/s on `develop` and 3,268.0 rows/s on OOS. S4 median throughput was 50,251.3 rows/s on `develop` and 37,313.4 rows/s on OOS.

## Correctness

All reported S1-S4 runs passed their validation checks.

| Scenario | Required result | Observed result |
| --- | --- | --- |
| Initial load | 100,000 rows; min/max payload 32,768 bits; `SUM(hot_col)=49,950,000` | Matched on both branches. |
| S1 | `SUM(hot_col)=49,950,000` | Matched in all 10 measured runs. |
| S2 | `COUNT(*)=100,000` | Matched in all 10 measured runs. |
| S3 | 100,000 rows; min/max payload 32,768 bits | Matched in all 10 fresh-load runs. |
| S4 | 100,000 rows; `SUM(hot_col)=50,050,000`; payload lengths unchanged | Matched in all 10 update runs. |

The original S2 expression compared `BIT VARYING` with `VARCHAR` and was rejected by CUBRID. Before collecting the accepted values, the plan and runner were corrected to:

```sql
WHERE payload = CAST (REPEAT (X'0123456789ABCDEF', 512) AS BIT VARYING)
```

No elapsed time from the rejected SQL is included in this report.

## I/O and Space Evidence

`cubrid statdump -c` snapshots before and after every run are retained. The table below shows median delta values in the raw snapshots, in the order `data_page_fetches / data_page_ioreads / data_page_iowrites / log_page_iowrites`.

| Scenario | develop statdump median delta | OOS statdump median delta |
| --- | --- | --- |
| S1 | 0 / 0 / 0 / 0 in every run | 0 / 0 / 0 / 0 in every run |
| S2 | 0 / 0 / 0 / 0 in every run | 0 / 0 / 0 / 0 in every run |
| S3 | 1,369 / 168 / 0 / 0 | 5,317 / 0 / 0 / 0 |
| S4 | 385 / 0 / 0 / 0 | 1,201 / 71 / 0 / 0 |

The S1/S2 zero snapshots mean these `statdump` counters cannot explain the read elapsed-time result. The S3/S4 values also vary substantially and show no synchronous log writes, so they must not be treated as physical-device I/O totals. They are included for traceability only; the raw before/after files are the source of record.

`spacedb` reports the following permanent-data usage after a representative fresh run:

| Phase | develop | OOS | Observation |
| --- | ---: | ---: | --- |
| S3 after INSERT | 597 MiB | 603 MiB | OOS was 6 MiB higher. |
| S4 before UPDATE | 597 MiB | 603 MiB | Fresh datasets. |
| S4 after UPDATE | 597 MiB | 1,128 MiB | OOS grew by 525 MiB after updating only `hot_col`; it was 531 MiB above `develop` after the operation. |

The created database files are preallocated, so their file-size totals remain about 6.78 GB and are not a useful logical-space comparison. `spacedb` used-size is the relevant recorded value here.

## S5 Status

S5 delete-vacuum-reinsert is explicitly **out of scope and discarded** at the user's direction. No lifecycle, vacuum completion, reclaimed-space, or reuse conclusion is made.

Raw partial S5 evidence remains under `performance-results/oos/s5-delete-vacuum-reinsert/` and the OOS `runner.log`:

- An initial attempt was discarded when `;oos_stats` was incorrectly passed through `csql -c` and parsed as SQL.
- A second attempt reached pre-delete OOS stats and DELETE, but stopped at an invalid vacuum-filler `CHAR()` expression before vacuum completion.
- A third fresh attempt was intentionally stopped when the scope was narrowed to S1-S4.

## Raw Evidence Layout

- Runner and command transcript: `performance-results/run_oos_performance.sh`, `performance-results/develop/runner.log`, `performance-results/oos/runner.log`
- Environment, active configuration, commit, and host capture: `performance-results/{develop,oos}/environment/`
- S1 raw `csql`, `time`, and `statdump`: `performance-results/{develop,oos}/s1-narrow-scan-warm/run-*/`
- S2 raw `csql`, `time`, and `statdump`: `performance-results/{develop,oos}/s2-payload-access-warm/run-*/`
- S3 raw `csql`, `time`, `statdump`, validation, and `spacedb`: `performance-results/{develop,oos}/s3-bulk-insert/run-*/`
- S4 raw `csql`, `time`, `statdump`, validation, and `spacedb`: `performance-results/{develop,oos}/s4-small-column-update/run-*/`

## Follow-up Measurement Requirements

1. Repeat S1/S2 on an otherwise idle host, pin the CPU/governor where permitted, randomize branch order, and collect query-level execution statistics that are non-zero for the measured SELECT.
2. Add separately labelled restart-only and cold measurements; do not call a server restart alone a cold-cache run.
3. Re-run S5 only when its lifecycle scope is restored, using a tested vacuum progression procedure and explicit completion predicate.
