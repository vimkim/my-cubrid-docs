# OOS Performance Test Plan

## 1. Purpose

This plan measures the OOS tradeoff fairly. It answers two questions together:

1. Does separating a 4KB-plus payload improve a full scan that reads only small columns?
2. What are the read, write, update, and space-reclamation costs introduced by OOS?

The presentation should show both sides. Do not publish a performance claim until these measurements are collected.

## 2. Comparison Contract

| Item | Rule |
| --- | --- |
| Baseline | `/home/vimkim/gh/cb/develop` at its recorded commit |
| OOS | `/home/vimkim/gh/cb/CBRD-27006-oos-recdes-locality` at its recorded commit |
| Build | `build_preset_release_gcc` from each worktree; do not compare a debug build |
| Server configuration | Same `cubrid.conf`, page size, buffer-pool size, CPU governor, storage device, and database volume options |
| Data | Same schema, row count, and values. `BIT VARYING` is used to avoid the VARCHAR compression path. |
| Repetitions | Five valid paired runs per branch and scenario. Randomize which branch runs first in each pair. Report the median and every raw value. |
| Cache state | Measure cold and warm separately; never average them together. |
| Result format | `develop`, `OOS`, delta %, plus the measurement environment and commit IDs. |

The workload uses a 4KB `BIT VARYING` payload. With the row header and small columns, it exceeds the current OOS gate (`DB_PAGESIZE/4`) on a 16KB-page database. On the OOS branch, that payload is eligible for largest-first demotion; the exact same SQL remains valid on `develop`.

## 3. Per-Branch Environment

Run one branch at a time. The default service port makes two concurrently running local servers unsafe unless ports are explicitly separated. In each worktree, first run `just build`; it installs the selected release build to that worktree's configured `$CUBRID` prefix. The `build_preset_release_gcc` directory alone is not a runnable server home.

```bash
# Run this in either worktree after `just build`.
# Use the installed prefix configured by the worktree. Do not point CUBRID at
# build_preset_release_gcc, which contains build artifacts rather than a full install.
: "${CUBRID:?source the worktree environment or set the installed CUBRID prefix}"
export CUBRID_DATABASES="${CUBRID_DATABASES:-$CUBRID/databases}"
export PATH="$CUBRID/bin:$PATH"

csql --version
cubrid createdb --db-volume-size=2G --log-volume-size=2G perf_oos en_US.utf8 \
  -F "$CUBRID_DATABASES/perf_oos"
cubrid server start perf_oos
```

Use a fresh database for each branch. Record the output of `csql --version`, `git rev-parse HEAD`, the effective `cubrid.conf`, CPU model, RAM, kernel, filesystem, and storage device in the result folder.

## 4. Shared Schema and Data

Load the same data on both branches through [`oos-performance-setup.sql`](oos-performance-setup.sql). Start at `N = 100000` rows (about 400MB of payload) and reduce only when storage capacity requires it. The actual `N` must be printed with every result.

```sql
DROP TABLE IF EXISTS perf_oos;

CREATE TABLE perf_oos (
  id       INT PRIMARY KEY,
  hot_col  INT NOT NULL,
  payload  BIT VARYING
);

INSERT INTO perf_oos
SELECT LEVEL,
       MOD (LEVEL, 1000),
       REPEAT (X'0123456789ABCDEF', 512)
  FROM db_root
CONNECT BY LEVEL <= 100000;
COMMIT;

SELECT COUNT(*) AS rows_loaded,
       MIN (BIT_LENGTH (payload)) AS min_payload_bits,
       MAX (BIT_LENGTH (payload)) AS max_payload_bits
  FROM perf_oos;
```

Execute the setup with:

```bash
csql -u dba -p '' perf_oos -i oos-performance-setup.sql -o setup.out
```

The validation query must report `100000` rows and `32768` bits for both minimum and maximum payload lengths before a run is accepted.

## 5. Scenarios

### S1. Narrow full scan - primary value proposition

```sql
SELECT SUM(hot_col) FROM perf_oos;
```

- **Question:** when the payload is not requested, does OOS reduce heap page work?
- **Measure:** elapsed time, `Num_data_page_fetches`, `Num_data_page_ioreads`, buffer hit ratio.
- **Correctness check:** the result must be identical between branches.
- **Expected direction:** this is the only scenario where an improvement is hypothesized. The presentation must show the measured result, not this hypothesis.

### S2. Payload access - read cost

```sql
SELECT COUNT(*)
  FROM perf_oos
 WHERE payload = CAST (REPEAT (X'0123456789ABCDEF', 512) AS BIT VARYING);
```

- **Question:** what does lazy OOS read cost when every payload is used?
- **Measure:** elapsed time, data-page fetches/ioreads, client/server CPU if available.
- **Correctness check:** both branches return `100000`.
- **Interpretation:** this is a cost measurement, not a failure condition. It prevents presenting S1 without the corresponding payload-read cost.

### S3. Bulk INSERT - write-path cost

On a fresh database, time the shared `INSERT INTO ... SELECT ... CONNECT BY ...` statement from Section 4, excluding `createdb` time.

- **Question:** how much do demotion, OOS file writes, and WAL add to the initial load?
- **Measure:** elapsed time, rows/s, `Num_data_page_iowrites`, `Num_log_page_iowrites`, and final database size.
- **Correctness check:** row count and payload bit length match Section 4.

### S4. UPDATE only a small column - current OOS update cost

```sql
UPDATE perf_oos
   SET hot_col = hot_col + 1;
COMMIT;

SELECT SUM(hot_col) FROM perf_oos;
```

- **Question:** what is the cost of updating a small value in a record that also owns an OOS payload?
- **Measure:** elapsed time, rows/s, data-page I/O, log-page I/O, and database-size growth before vacuum.
- **Correctness check:** the final sum is the S1 sum plus `N`.
- **Interpretation:** the current design writes new OOS values during update; this test quantifies that known cost without hiding it.

## 6. Measuring Each Run

For every query or DML statement, collect a cumulative statdump before and after, and retain the raw files. Derive deltas from those two snapshots.

```bash
mkdir -p results/$CASE/$BRANCH/$RUN

cubrid statdump -c perf_oos > results/$CASE/$BRANCH/$RUN/stat-before.txt
/usr/bin/time -f 'elapsed_s=%e\nmax_rss_kb=%M' \
  csql -u dba -p '' perf_oos -c "$SQL" \
  > results/$CASE/$BRANCH/$RUN/csql.out \
  2> results/$CASE/$BRANCH/$RUN/time.txt
cubrid statdump -c perf_oos > results/$CASE/$BRANCH/$RUN/stat-after.txt
```

Extract at least these counters from the raw statdump pair:

- `Num_data_page_fetches`
- `Num_data_page_ioreads`
- `Num_data_page_iowrites`
- `Num_log_page_iowrites`
- `Data_page_buffer_hit_ratio`

For S3-S4, also save `cubrid spacedb perf_oos` output before and after the phase. Keep the command output even when a summary spreadsheet is produced.

## 7. Cold and Warm Discipline

### Warm runs

1. Load the database once.
2. Execute the scenario once as a warm-up and discard its result.
3. Execute five measured runs without changing the data except where the scenario explicitly changes it.

### Cold runs

1. Stop the database server.
2. Clear the database buffer pool by restarting the server.
3. Clear the OS page cache only on an otherwise idle dedicated host and only under the host's approved privileged procedure.
4. Run one measured scenario immediately after server start; recreate the database or reload the scenario state before the next cold repetition.

If OS cache clearing is unavailable, label the result **restart-only**, not **cold**. A restart by itself does not prove storage reads reached the device cache boundary.

## 8. Presentation Output

For each of S1-S4, use one grouped bar chart with `develop` and `OOS` bars.

Every chart needs these labels:

- `N`, payload size, CUBRID commit, release build, page size, buffer-pool size
- cache state (`cold`, `restart-only`, or `warm`)
- median of five runs and the raw-value range
- the counter used to explain elapsed time

The summary slide should state only: **S1 measures OOS value; S2-S4 measure OOS cost.** It must not promise a speedup before data is collected.
