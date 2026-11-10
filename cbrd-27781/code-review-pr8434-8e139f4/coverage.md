# Coverage: CUBRID/cubrid#8434 at 8e139f4db

Base / merge base `95ff126a8464179a2fab3092b6f56468528ab954`, head `8e139f4dbb2635058032d0b9dafd5f624c726754`. Delta since the previous review (`3e8072f56`, rebased as `c255c7c3b`): 14 files.

| Path group | Primary seat (model) | Invariants | Evidence | Result | Remaining |
| --- | --- | --- | --- | --- | --- |
| `src/query/vacuum.c` (notification-only blocks, rebuild floor, CBRD-27953 deferral, block end state) | concurrency (opus), recovery (opus) | a deferred or interrupted block is never marked vacuumed; error stack balanced; rerun is safe | level 3 (both seats, plus systems for Q2) | cleared | none |
| `src/query/vacuum_oos.cpp/.hpp` | systems (sonnet) | error translation, fail-stop, deferral list | level 3 | P3 risk U-3 | none |
| `src/storage/oos_file.cpp/.hpp`: reclaim intents, postpones, fail-stop, RVOOS_DELETE, RVOOS_INSERT undo (8-byte VFID) | recovery (opus), systems (sonnet) | run once after commit, discard on abort, rerun converges, no undo into a reused slot | level 3; TLA+ model (level 4 for its abstraction); coordinator crash probe (level 5 for restart undo) | cleared; U-4 | CLR-redo variant of the crash probe (optional) |
| `src/storage/oos_file.cpp`: emptied-page set, growth lock through `file_alloc`, laps, sweep (CBRD-27925) | storage (sonnet), concurrency (opus) | no page freed while live or undo-targeted; no permanent leak; no latch cycle | level 3 (two seats) | cleared; U-1, U-2, U-5 | throughput measurement S-2 |
| `src/storage/heap_file.c`, `heap_oos.cpp/.hpp` | concurrency (opus), systems (sonnet) | latch order on the eager path; payload construction | level 2-3 (spot check of heap callers) | P-1 already tracked (CBRD-28012); serial-path latency question R1 | trace remaining heap callers that hold a page latch while transforming a record |
| `src/storage/page_buffer.c` | storage (sonnet) | comment-only change | level 2 | cleared | none |
| `src/storage/tde.h` | systems (sonnet) | removed include or tag | level 2 | cleared | none |
| `src/transaction/log_append.*`, `log_manager.*`, `log_recovery.c`, `recovery.*`, `mvcc.h` | recovery (opus) | notification appended with explicit MVCCID; restart-safe vacuum info; `log_do_postpone` LSA_LE; RV_fun table | level 3 for the delta; prior review for the rest | cleared; U-4 | full-PR line-by-line re-derivation of postpone machinery not repeated (covered by the previous review at `3e8072f56`) |
| `src/transaction/log_applier.c`; replication, CDC, log dump consumers | ha (sonnet) | applier skips the new undo image; slave reclaims on its own; R8 not widened | level 2-3 | cleared; U-4 | optional HA smoke test |
| `unit_tests/oos/*` | each owning seat; systems for harness | tests can fail; hooks reset | level 2 plus coordinator ctest 54/54 | gaps U-6 | tests for the growth lock through `file_alloc` |

## Shared challenge questions

| Question | Seat A | Seat B | Result |
| --- | --- | --- | --- |
| Q1: can a page in the emptied-page set be deallocated or reused while an undo still needs it or a chunk on it is live? | recovery (opus): no. No undo reinserts into an OOS page; RVOOS_INSERT undo only deletes; reclaim re-tests empty + PAGE_OOS under the header WRITE latch and a page WRITE fix. | storage (sonnet): no, by the same guards, found independently. | Agreed at level 3. Restart undo of an RVOOS_INSERT loser executed by the coordinator probe (level 5 for that path). |
| Q2: after ER_VACUUM_OOS_LOOKUP_DEFERRED, can any exit of `vacuum_process_log_block` mark the block vacuumed, lose, or double-run a reclaim? | concurrency (opus): no. `vacuum_complete` is set only after the `oos_deferred` check; error stack balanced; skipped heaps imply a recorded deferral; rerun skips reclaimed chains by identity stamp. | systems (sonnet): no, same argument, found independently. | Agreed at level 3. |

## Not applicable

None. Every role had changed code in scope.
