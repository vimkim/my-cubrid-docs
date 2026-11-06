# Coverage: PR 8434 at 3e8072f56 (run 1, coordinator only)

Superseded by the specialist coverage table in [report.md](report.md) (run 2). Kept as the run-1 record.

All roles were covered by the coordinator in one session. No specialist agents ran (see manifest: budget gate). No row has execution evidence. Evidence levels follow the reviewer contract (2 = source locations, 3 = complete path argument).

| Path group | Role | Invariant checked | Evidence | Result | Remaining action |
|---|---|---|---|---|---|
| src/transaction/log_manager.c (log_do_postpone LSA_LE) | Recovery | A postpone at a nested sysop's last-parent LSA belongs to the outer level and must run. Ranges that start at a LOG_SAVEPOINT or a prior SYSOP_END stay correct. | L3: log_manager.c:8428-8446, nested-top build at 8261-8263, log_abort_partial at 5742 (lastparent = the LOG_SAVEPOINT record), and the record scan with end inclusive | Cleared within source scope | None required |
| log_append.cpp/.hpp, log_manager.c/.h (explicit MVCCID append) | Recovery + Concurrency | Vacuum data entries keep a non-decreasing oldest_visible_mvccid. Every unvacuumed MVCC record has an mvccid >= oldest_unvacuumed_mvccid. | L3: log_append.cpp:1351-1381, vacuum.c:5555-5562, 7392-7397, 8384-8423, 6798 | **Unverified risk R1** | Debug stress (see report) |
| mvcc.h, recovery.c/.h, tde.h, log_recovery.c, log_applier.c | Systems + HA | The rcvindex table stays contiguous. Undo of a notify is a no-op in both rollback and restart undo. The TDE list drops the removed index. The applier header initializer matches the 32B header. | L2 | Cleared | None |
| src/storage/oos_file.cpp/.hpp (reclaimer, intent, postpone handlers, fail-stop) | Recovery + Concurrency + Storage | Tail-first delete with link stamps converges on rerun. Concurrent same-chain reclaimers never delete a reused slot. Deletes are redo-only. Interrupt checks are disabled during the commit postpone. | L3: oos_file.cpp:3182-3230, 3252-3340, 3360-3480, 3732-3990 | Cleared within source scope | The fail-stop restart loop is accepted by policy (ADR-0008 decision 3) |
| src/storage/heap_file.c, heap_oos.cpp/.hpp | Concurrency + Recovery | MVCC UPDATE logs the drop postpone. Rollback, savepoint rollback, and statement rollback discard it (sysop-abort range). The non-MVCC path postpones to unit commit. No heap header fix happens under a held heap data page. | L2-L3 | Cleared within source scope | Non-MVCC intent inside a logical-undo sysop keeps the pre-existing semantics (see report note) |
| src/query/vacuum.c, vacuum_oos.cpp/.hpp | Concurrency + Storage | REMOVE intent and heap slot removal share one sysop. The emptied-page sink is thread_local. The notify consumer copies undo data before page fixes. Dropped-heap skip. | L2-L3 | Cleared, except for the R1 dependency (dropped-file cleanup) | See R1 |
| unit_tests/oos/* (14 files) | Coordinator | Tests match the new contract | Read via the PR body claim (49/49 debug ctest) only. Not rerun. | Not verified | Optional rerun |

Shared challenge questions: none could be assigned because no second seat was launched. Missing independent challenge: R1 and the postpone-rerun/crash interleavings were not independently reviewed.
HA: not applicable beyond the applier header initializer. Notify and reclaim postpones are local physical and vacuum work. Replication of OOS values uses the RVREPL_* records, which this PR does not change.
