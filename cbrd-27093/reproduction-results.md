# CBRD-27093 Reproduction Results

- Issue: <http://jira.cubrid.org/browse/CBRD-27093>
- Reproduced: 2026-07-23 (Asia/Seoul)
- Source branch: `develop`
- Source commit: `4cfc8370edc030fb69433702428916f1c90dc780`
- Test build: CUBRID 11.5.0 (`11.5.0.2349-4cfc837`, 64-bit Linux release build)
- Script: [`how-to-reproduce.sh`](./how-to-reproduce.sh)

## Test Purpose

Verify whether the permanent base data volume is synchronized by
`fsync`/`fdatasync` when a workload is followed by an explicit checkpoint.
The DWB-enabled run is the positive control for the DWB-disabled run.

## Procedure

The script performs the following:

1. Recreates `testdb` once.
2. Starts the same database with `double_write_buffer_size=0`.
3. Attaches `strace` before loading 100,000 rows and running `;checkpoint`.
4. Stops and waits for `strace`, then counts synchronization calls by exact
   file path.
5. Restarts the same database with `double_write_buffer_size=2097152` and
   repeats the workload and trace.
6. Compares synchronization calls for the permanent base volume
   `$CUBRID_DATABASES/testdb/testdb`.

Run:

```bash
./how-to-reproduce.sh
```

Requirements:

- `cubrid`, `csql`, `ini.sh`, `pgrep`, and `strace` must be available.
- The user must be allowed to attach `strace` to `cub_server`.
- The script deletes and recreates the database named `testdb`.
- The script leaves `double_write_buffer_size=2097152` in `cubrid.conf` and
  leaves `testdb` stopped after completion.

## Result

| Case | Effective DWB size | Permanent base volume syncs | Outcome |
|---|---:|---:|---|
| DWB off | `0` | **0** | Bug reproduced |
| DWB on | `2097152` | **1** | Positive control passed |

Terminal summary:

```text
=== CBRD-27093 result ===
DWB off permanent base volume sync count: 0
DWB on  permanent base volume sync count: 1
DWB off trace: /tmp/cbrd-27093.dwb-off.trace
DWB on  trace: /tmp/cbrd-27093.dwb-on.trace
REPRODUCED: DWB-off checkpoint did not synchronize the permanent base volume
```

Observed DWB-off synchronization targets:

```text
9  testdb_lgat
3  testdb_lgar_t
2  testdb directory
1  testdb_t32766
0  testdb              # permanent base volume
```

Observed DWB-on synchronization included:

```text
1  testdb              # permanent base volume
7  testdb_dwb          # DWB volume
6  testdb_x001         # permanent extension volume
```

Counts other than the asserted base-volume count may vary with background
thread scheduling. The important comparison is zero calls for the exact base
volume path with DWB disabled versus at least one with DWB enabled.

## Interpretation

The DWB-enabled positive control proves that the tracer was attached while
data-volume synchronization occurred. With DWB disabled, active/archive logs,
the temporary volume, and the database directory were synchronized, but the
permanent base data volume was not.

This reproduces CBRD-27093 on commit `4cfc8370e`: a successful checkpoint does
not synchronize permanent data volumes when DWB is disabled.

## Runtime Artifacts

The raw traces were written outside the documentation repository:

- `/tmp/cbrd-27093.dwb-off.trace`
- `/tmp/cbrd-27093.dwb-on.trace`

They are temporary host-local artifacts and are overwritten by the next run.
