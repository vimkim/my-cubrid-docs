# OOS SELECT Performance Test Plan

## 1. Purpose

This plan replaces the earlier broad warm-only comparison with a controlled SELECT benchmark that exposes both the advantage and the cost boundary of OOS.

The primary question is: when a query reads only inline columns, how much heap and overflow I/O does OOS avoid? The comparison uses two deliberately different baseline layouts:

1. A logical record of about 14.5 KiB that remains an ordinary heap record on `develop`, but is reduced to about 4 KiB in the OOS branch.
2. A logical record above 16 KiB that becomes a `REC_BIGONE` overflow record on `develop`, but is reduced to about 4 KiB in the OOS branch.

The exact DDL, load DML, validation SQL, and measured SELECT statements are maintained in [`oos-select-performance-workload.sql`](oos-select-performance-workload.sql). Review that file before implementing or running the benchmark.

The previous S1-S4 results remain exploratory evidence for OOS payload-read, INSERT, and UPDATE costs. They are not the primary evidence for narrow-read performance.

## 2. Comparison Contract

| Item | Rule |
| --- | --- |
| Baseline | `/home/vimkim/gh/cb/develop` at a recorded commit |
| OOS | The selected OOS worktree at a recorded commit |
| Build | Release-equivalent builds with identical compiler and optimization settings; do not compare a debug build with a release build |
| Database | Fresh database per branch; 16 KiB database and log pages |
| Server configuration | Same effective `cubrid.conf`, buffer size, volume options, CPU governor, storage device, and server port policy |
| Data | Execute the same workload SQL on both branches; use `BIT VARYING` so the payload size is deterministic and not changed by VARCHAR compression |
| Row count | Start with 100,000 rows per layout; the develop-side heap/overflow working set must be at least twice the configured data buffer |
| Repetitions | At least five valid paired runs per layout, query, and cache state; randomize which branch runs first in each pair |
| Result format | Report both branches, delta percentage, median, full raw range, commits, environment, storage layout, plan, and I/O evidence |

No performance conclusion is accepted unless the storage-layout, execution-plan, correctness, and cache-state gates below all pass.

## 3. Workload Shape

### 3.1 Layout A: ordinary heap record on develop

Table `perf_heap_14500` contains:

- three 1,300-byte variable columns intended to remain inline;
- two larger variable columns of 5,300 and 5,200 bytes;
- `id`, `lookup_key`, and `hot_col` integer columns.

The logical payload is 14,400 bytes before record metadata. On `develop`, the record must remain an ordinary heap record. On the OOS branch, largest-first demotion should move the 5,300-byte and 5,200-byte columns to OOS, leaving approximately 3,900 bytes plus the record header and two 16-byte OOS OIDs in the heap.

### 3.2 Layout B: overflow record on develop

Table `perf_overflow_22000` contains:

- the same three 1,300-byte inline-target columns;
- three larger variable columns of 7,000, 6,000, and 5,000 bytes;
- `id`, `lookup_key`, and `hot_col` integer columns.

The logical payload is 21,900 bytes before record metadata. On `develop`, it must be stored as a `REC_BIGONE` overflow record. On the OOS branch, largest-first demotion should move all three larger columns to OOS, again leaving approximately 3,900 bytes plus metadata in the heap. This does not test OOS-plus-bigone coexistence: the post-demotion OOS record must fit in the heap.

### 3.3 Randomized lookup order

`id` deliberately has no index so `SUM(id)` and `SELECT id` cannot become covering-index scans. A separate index is created on `lookup_key`.

`lookup_key` is a deterministic permutation of insertion order. The cast avoids overflowing a 32-bit intermediate:

```sql
MOD (CAST (id - 1 AS BIGINT) * 48271, 100000) + 1
```

The multiplier is coprime with 100,000, so each lookup key is unique while adjacent key ranges map to scattered heap records. The range query projects `hot_col`, which is not part of the lookup index, forcing heap fetches without resolving any OOS column.

## 4. Storage-Layout Acceptance Gate

Validate the layout before collecting timing data. A run is rejected if any check fails.

1. Execute the logical-size and value checks in the workload SQL on both branches.
2. Record heap-page, overflow-page, and OOS-page counts after the load.
3. On `develop`, capture record-level diagnostic evidence showing:
   - `perf_heap_14500` uses ordinary heap records and no overflow records;
   - `perf_overflow_22000` uses `REC_BIGONE` overflow records.
4. On the OOS branch, capture OOS statistics and record-level diagnostic evidence showing:
   - Layout A demotes the two large columns;
   - Layout B demotes the three large columns;
   - both post-demotion records remain normal heap records near, but not above, the 4 KiB target;
   - the three 1,300-byte columns and `hot_col` remain inline.
5. Record the actual page counts and average rows per heap page. Do not substitute calculated sizes for observed storage evidence.

If record metadata pushes Layout A into overflow on `develop`, reduce only the 5,200-byte column in 128-byte steps until the ordinary-heap condition is satisfied. If post-demotion size exceeds 4 KiB, reduce the three inline-target columns equally. Apply the finalized values unchanged to both branches and update the workload SQL before any accepted run.

## 5. SELECT Matrix

Run all three queries against both layouts, producing six principal comparisons per branch.

Every measured SELECT starts with:

```sql
/*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */
```

`NO_PARALLEL_HEAP_SCAN` is the documented CUBRID hint. `HEAP_NO_PARALLEL_SCAN` is not used. `PARALLEL(0)` disables general parallel query execution, while `NO_PARALLEL_HEAP_SCAN` makes the heap-scan requirement explicit and takes precedence if parallel settings change.

### Q1. Aggregate all IDs

```sql
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */ SUM(id)
  FROM <table>;
```

This is the cleanest server-side narrow full scan. It measures heap/overflow work without row-transfer volume dominating elapsed time.

### Q2. Return all IDs

```sql
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */ id
  FROM <table>;
```

Run through the same `csql` options on both branches and redirect results to a file. Report:

- server execution time from query trace;
- end-to-end wall time including result serialization and transfer;
- result row count and checksum.

This prevents client-output cost from being mistaken for storage-engine cost.

### Q3. Random non-covering range reads

```sql
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */ hot_col
  FROM <table>
 WHERE lookup_key BETWEEN <range_start> AND <range_end>;
```

Use a checked-in, fixed-seed permutation of the 1,000 non-overlapping 100-key ranges that cover lookup keys 1 through 100,000. Execute the list in one `csql` session to avoid measuring process startup once per range. The list and order must be identical across branches, and no range may repeat within one measured pass.

The accepted execution plan must use `ix_heap_14500_lookup` or `ix_overflow_22000_lookup` and then fetch `hot_col` from the heap. Reject any run that uses a sequential scan or a covering-index-only plan. No query may reference `inline_1` through `inline_3` or any `cold_*` column.

### 5.4 Payload-read extension (Q4/Q5)

Run this extension as a separate suite against the same two layouts, commits,
cache states, buffer size, and five-pair protocol. It answers the inverse of
Q1-Q3: what happens once the query must access demoted data?

- **Q4, one OOS column:** count rows whose `cold_1` value equals the exact
  loaded `BIT VARYING` constant. Content equality is intentional: a size-only
  expression may use the full length stored in the OOS OID without reading the
  payload.
- **Q5, all logical columns:** aggregate `id`, `lookup_key`, and `hot_col` plus
  a `CASE` that compares every payload column with its exact loaded value. This
  is the server-side equivalent of an all-column projection for storage access,
  while avoiding 1.4-2.2 GB of client output per pass.

Both queries must remain serial table scans. Q4 must return 100,000. Q5 must
return 10,050,150,000. On OOS, query-trace fetches must exceed the compact-heap
page count by approximately one OOS access per row; Q5 fetches must not be below
Q4. The content checksum, rather than a one-counter-per-column assumption, is
the proof that every Q5 payload value was accessed: multiple OOS records may be
served from the same page access path.

Run with:

```bash
SELECT_V2_SUITE=worst bash performance-results/run_oos_select_v2.sh 27006 100000 5
```

The resulting report is [`oos-select-worstcase-results.md`](oos-select-worstcase-results.md).

## 6. Execution-Plan and Correctness Gate

Capture and retain the compiled plan and SQL trace for every distinct layout/query pair.

- Q1 and Q2 must scan the heap and must not use the `lookup_key` index.
- Q3 must use the named lookup index and perform non-covering heap fetches.
- Every plan must show serial execution. If a parallel heap scan appears, reject the run.
- The plans must be equivalent between branches apart from storage behavior introduced by OOS.
- No measured query may resolve or expand an OOS column.

Required results for `N = 100000`:

| Query | Correctness result |
| --- | --- |
| Q1 | `SUM(id) = 5000050000` |
| Q2 | 100,000 IDs; same checksum on both branches |
| Q3 | 100 rows per range; identical aggregate row count and checksum for the complete range list |

Run correctness validation outside the timed interval when it would add work not present in the measured query.

## 7. Cache and I/O Discipline

### 7.1 Warm measurements

1. Load and validate the database once.
2. Run the exact query workload once as an unmeasured warm-up.
3. Run at least five measured repetitions without changing data.
4. Record whether each layout fits in the configured database buffer after OOS demotion.

### 7.2 Restart-only measurements

Restart the CUBRID server before each repetition but do not claim the OS page cache is cold. Label these results `restart-only`.

### 7.3 Cold measurements

Call a run `cold` only when both the CUBRID buffer pool and the relevant OS page cache have been cleared using the host's approved procedure on an otherwise idle test host. Run exactly one measured workload after each cold preparation.

If approved OS cache clearing is unavailable, omit the cold series rather than relabeling restart-only results.

### 7.4 Demonstrating physical reads

The Q3 range set is accepted only if query-level trace or verified server counters show non-zero physical data-page reads on the develop branch. Increase the range count or reduce the data-buffer size equally on both branches if the first pilot does not create measurable I/O. Do not use elapsed time alone as proof of I/O avoidance.

## 8. Measurement Procedure

For every accepted run, retain:

- query text and generated range list;
- compiled plan and SQL trace;
- end-to-end elapsed time, user CPU, system CPU, and maximum RSS;
- query-level heap/overflow/OOS page fetches and physical reads;
- cumulative `statdump` snapshots before and after, as supporting evidence only;
- database-space and file-page summaries;
- result row count/checksum;
- effective server configuration, CUBRID version, commit, host, CPU, memory, filesystem, and storage device.

The earlier benchmark produced zero `statdump` deltas for SELECT. Therefore, cumulative snapshots alone are not an acceptance metric. Use query-level trace/counters that demonstrably change during the measured SELECT; otherwise mark the I/O result unavailable.

Use at least five paired repetitions. Randomize branch order within each pair and report the median, minimum, maximum, and every raw value. Never average warm, restart-only, and cold results together.

## 9. Reporting

The primary result table has one row per layout/query/cache-state combination:

| Baseline layout | Query | Cache state | develop median | OOS median | Delta | Heap fetches | Overflow fetches | OOS reads | Physical reads |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ordinary heap (~14.5 KiB) | Q1/Q2/Q3 | warm/restart-only/cold | TBD | TBD | TBD | TBD | TBD | 0 expected | TBD |
| `REC_BIGONE` overflow (>16 KiB) | Q1/Q2/Q3 | warm/restart-only/cold | TBD | TBD | TBD | TBD | TBD | 0 expected | TBD |

Presentation conclusions must distinguish:

1. OOS versus an ordinary wide heap record for narrow reads.
2. OOS versus a whole-record overflow chain for narrow reads.
3. Server storage time versus client transfer time for `SELECT id`.
4. The benefit of avoiding OOS reads from the separately measured cost of accessing OOS payloads.

Keep the existing payload-read, INSERT, and UPDATE results as the disadvantage/trade-off section. Do not present only the favorable SELECT cases, and do not claim an improvement when the page/I/O evidence does not explain the elapsed result.
