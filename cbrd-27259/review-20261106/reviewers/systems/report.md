# Systems reviewer report (opus)

The harness blocked the subagent from writing this file, so the coordinator saved the reviewer's final message here. Raw output is in this directory and in `probe/`.

## Pinned identity
- Head: 9ae07b9491b1393841ecb0f3579752a598bf68ec. Merge base: d52b1889e907abcf84190ec504dde3bc93de260d.
- The checkout is clean.
- The patch sha256 is e7ffb902....
- `libcubridsa` (20:38:58) is newer than the newest changed source file (20:38:31).

## Invariants
- **I1.** The report preserves the caller's error state (level 3). The push/pop is redundant with `er_set_internal`'s notification isolation (`error_manager.c:1438,1542`) but correct.
- **I2.** The message arguments are in the right order and count (level 5). The log shows "class 0|202|53 needs 17056 bytes ... (16236 bytes)".
- **I3.** The error codes and both catalogs are consistent (level 4/5).
- **I4.** The report uses the same estimate as the -1388 guard. The two are mutually exclusive and both run before any OOS insert (level 3, boundary 5).
- **I5.** No FORCE_INLINE value is ever selected for OOS (level 4).
- **I6.** A record with OOS values that would need REC_BIGONE is rejected with -1388 and leaves no orphan chain. A record without OOS values is stored and reported (level 4/5).
- **I7.** The policy flag is a single bit (level 2-3).
- **I8.** The SA and SERVER build guards are consistent (level 2-3). Only SA was executed.
- **I9.** The default `error_log_level` is NOTIFICATION, so the report is logged by default (level 5).

## Commands
- `test_oos_sql_storage`: 43 passed.
- csql SA probes `probe/s*.sql`, the per-statement table in the hand-back, and `per_statement.txt`.
- Window probe: `probe/win_*` and `window.txt`.
- Volume probe: `perf.out`. It inserts 3000 rows and logs 6000 reports of about 550 B each. The insert took 2.15/1.32 s with logging and 0.79/0.83 s without. This is an indicative debug SA run only.

## Candidate findings (reproduced)
- **SYS-1 (P3).** The report fires during record layout, not at the heap write. The extra layouts happen in:
  - REPLACE duplicate removal (`query_executor.c:12661`).
  - ODKU lookup (`query_executor.c:12887`).
  - MVCC re-evaluation (`locator_sr.c:14002`). This one is source-only.

  Observed results:
  - REPLACE gives 2 reports per stored row.
  - ODKU with a new key gives 2.
  - ODKU with a duplicate key whose stored row is 8 bits gives 1.
  - A failed duplicate INSERT gives 1.
- **SYS-2 (P4).** The 16-byte MVCC slack in the estimate means rows whose real length is in (Max-16, Max] are reported but stay REC_HOME. This conforms to the spec; only the wording is wrong.
- **SYS-3 (P3, design).** There is one unthrottled log write per qualifying row, under the global `er_Log_file_mutex`. It fires without any opt-in for large fixed-length columns and wide tables.

## Pre-existing
- **OLD-1.** Offline SA compactdb bypasses the layout (`compactdb.c:656-710`).
- **OLD-2.** The cubrid-cci `base_error_code.h` lacks all OOS codes.

## Q1
- No path traced places a FORCE_INLINE value in OOS.
- No wrong accept or reject was found on any path that lays out OOS.
- HA apply (`xlocator_repl_force`) stores the master's image as is.

## Coverage
Complete for the assigned scope. Only SA debug was run.
