# Coverage

| Subsystem / invariant | Primary | Paths | Verification |
|---|---|---|---|
| Commit-with-postpone durability, recovery analysis/redo/finish_postpone, checkpoint, archive lifetime | recovery | log_manager.c, log_recovery.c, log_page_buffer.c, log_append.cpp | source path argument; crash scenario states |
| LOB dir guard: flush semantics (logpb_flush_log_for_wal), tran_start_postpone_lsa validity at runtime and in recovery | recovery (shared with systems) | heap_file.c, log_page_buffer.c, log_append.cpp, locator_sr.c | source + coordinator gdb crash test |
| Q1 shared: non-WAL effects in the commit window | recovery, ha | all log_append_postpone sites, log_commit_local | independent answers |
| HA replication, CDC, flashback, copylog/applier, 2PC/XA, async commit, group commit, SA_MODE | ha | log_manager.c, log_2pc.c, log_page_buffer.c, replication/CDC code | source |
| Thread context of heap_rv_lob_remove_dir (transaction, vacuum, recovery, parallel redo), LOG_CS reentrancy/deadlock, latches held during postpone | systems | heap_file.c, log_manager.c, log_postpone_cache.cpp | source |
| Visibility of postpone effects to concurrent transactions before LOG_COMMIT_WITH_POSTPONE is durable (freed pages/sectors/slots reused) | systems | file_manager.c, disk_manager.c, heap_file.c | source schedule |
| Performance: flushes per commit, group commit interplay | systems | log_page_buffer.c | prior measurement (fdatasync 6006->3006 on OOS base) |

## Results

| Row | Reviewer (model) | Result | Remaining action |
|---|---|---|---|
| Commit-with-postpone durability, recovery, checkpoint, archive | recovery (opus) | Safe at level 3; DROP crash test level 4 | R-3 runtime check (optional) |
| LOB dir guard | recovery (opus), systems (sonnet) | Correct in all caller contexts; level 5 crash test with negative control | none |
| Q1 shared | recovery (opus), HA (sonnet), independent | No other direct non-WAL postpone; indirect LOB delete R-1 (recovery only), restated as CBRD-27964 | tracked in CBRD-27964 |
| HA, CDC, flashback, 2PC, async, SA_MODE | HA (sonnet) | No defect, level 3; 2PC participant path partially traced | 2PC participant crash test (not run) |
| Thread context, LOG_CS, latches, compile | systems (sonnet) | No defect; heap_file.c compiles in SA and SERVER modes | none |
| Reuse before CWP is durable | systems (sonnet) | Logged reuse safe; no-redo index build C1 disproven by coordinator (level 3) | none |
| Performance | systems (sonnet) | One group-commit wait per postpone commit | develop benchmark not run |
| Pre-existing `nxio_lsa` wait comparison | systems, recovery | R-2, base identical | instrumented check |
