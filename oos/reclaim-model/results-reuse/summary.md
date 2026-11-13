# OOS chain reuse checks (CBRD-27230)

- OosChainReuse sha256 `acf940a2837dc578625a2a53f7388daa53af971a856640dbe848316d1c393afd`
- tla2tools sha256 `936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88`
- safety bounds: Txns={"T1", "T2"}, Readers={"R1"}, Slots={1, 2, 3, 4}, MaxStmts=2, MaxStamp=6, MaxNotes=8
- liveness bounds: Txns={"T1", "T2"}, Readers={"R1"}, Slots={1, 2, 3}, MaxStmts=1, MaxStamp=5, MaxNotes=4

| Setting | Property | Kind | Bounds | Result | Expected | Distinct states |
| --- | --- | --- | --- | --- | --- | --- |
| design | NeededChainsLive | safety | safety | PASS | PASS | 9649400 |
| design | NoWrongDelete | safety | safety | PASS | PASS | 9649400 |
| design | NotifyOnlyForCommittedDrop | safety | safety | PASS | PASS | 9649400 |
| design | GarbageReclaimed | liveness | liveness | PASS | PASS | 189483 |
| publish_before_commit | NeededChainsLive | safety | safety | FAIL | FAIL | 634 |
| publish_before_commit | NoWrongDelete | safety | safety | PASS | PASS | 1226378 |
| publish_before_commit | NotifyOnlyForCommittedDrop | safety | safety | FAIL | FAIL | 214 |
| publish_before_commit | GarbageReclaimed | liveness | liveness | PASS | PASS | 48627 |
| no_horizon | NeededChainsLive | safety | safety | FAIL | FAIL | 1214 |
| no_horizon | NoWrongDelete | safety | safety | PASS | PASS | 10507208 |
| no_horizon | NotifyOnlyForCommittedDrop | safety | safety | PASS | PASS | 10507208 |
| no_horizon | GarbageReclaimed | liveness | liveness | PASS | PASS | 208487 |
| no_cancel | NeededChainsLive | safety | liveness | FAIL | FAIL | 769 |
| no_cancel | NoWrongDelete | safety | liveness | PASS | PASS | 3754692 |
| no_cancel | NotifyOnlyForCommittedDrop | safety | liveness | FAIL | FAIL | 352 |
| undo_image_drop | NeededChainsLive | safety | safety | FAIL | FAIL | 461 |
| undo_image_drop | NoWrongDelete | safety | safety | PASS | PASS | 100366842 |
| undo_image_drop | NotifyOnlyForCommittedDrop | safety | safety | FAIL | FAIL | 180 |
| undo_image_drop | GarbageReclaimed | liveness | liveness | PASS | PASS | 930228 |
| no_identity | NeededChainsLive | safety | safety | FAIL | FAIL | 32543 |
| no_identity | NoWrongDelete | safety | safety | FAIL | FAIL | 35013 |
| no_identity | NotifyOnlyForCommittedDrop | safety | safety | PASS | PASS | 13962878 |
| no_identity | GarbageReclaimed | liveness | liveness | PASS | PASS | 241215 |
| no_rerun | NeededChainsLive | safety | safety | PASS | PASS | 3558440 |
| no_rerun | NoWrongDelete | safety | safety | PASS | PASS | 3558440 |
| no_rerun | NotifyOnlyForCommittedDrop | safety | safety | PASS | PASS | 3558440 |
| no_rerun | GarbageReclaimed | liveness | liveness | FAIL | FAIL | 7569 |
| restamp | NeededChainsLive | safety | safety | FAIL | FAIL | 2 |
| restamp | NoWrongDelete | safety | safety | PASS | PASS | 586184 |
| restamp | NotifyOnlyForCommittedDrop | safety | safety | PASS | PASS | 586184 |
| restamp | GarbageReclaimed | liveness | liveness | FAIL | FAIL | 5355 |
| snapshot_source | NeededChainsLive | safety | safety | FAIL | FAIL | 439 |
| snapshot_source | NoWrongDelete | safety | safety | PASS | PASS | 62001044 |
| snapshot_source | NotifyOnlyForCommittedDrop | safety | safety | FAIL | FAIL | 217 |
| snapshot_source | GarbageReclaimed | liveness | liveness | PASS | PASS | 352083 |
| undo_frees_reused | NeededChainsLive | safety | safety | FAIL | FAIL | 36 |
| undo_frees_reused | NoWrongDelete | safety | safety | PASS | PASS | 103122262 |
| undo_frees_reused | NotifyOnlyForCommittedDrop | safety | safety | PASS | PASS | 103122262 |
| undo_frees_reused | GarbageReclaimed | liveness | liveness | PASS | PASS | 865830 |
| design | WitnessSharedChainReclaimed | witness | safety | FAIL | FAIL | 346 |
| design | WitnessSnapshotHoldsReclaim | witness | safety | FAIL | FAIL | 435 |
| design | WitnessDuplicateNotify | witness | safety | FAIL | FAIL | 1048 |
| design | WitnessCrashInPostponeThenReclaim | witness | safety | FAIL | FAIL | 15716 |
| design | WitnessPartialRollbackThenCommit | witness | safety | FAIL | FAIL | 3661 |

## Counterexamples

### publish_before_commit breaks NeededChainsLive

1. T1: UPDATE assigns no OOS attribute; the postpone names nothing
2. T1: UPDATE assigns c1; the postpone names the dropped chains
3. T1: the commit hook appends RVOOS_NOTIFY_VACUUM before the commit record (flushed)
4. crash; recovery undoes active transactions and reruns unfinished postpones
5. vacuum: consumes notification 1 and reclaims its chains (redo-only)

### publish_before_commit breaks NotifyOnlyForCommittedDrop

1. T1: UPDATE assigns c1; the postpone names the dropped chains
2. T1: UPDATE assigns no OOS attribute; the postpone names nothing
3. T1: the commit hook appends RVOOS_NOTIFY_VACUUM before the commit record (flushed)
4. crash; recovery undoes active transactions and reruns unfinished postpones

### no_horizon breaks NeededChainsLive

1. T1: UPDATE assigns c1; the postpone names the dropped chains
2. T1: UPDATE assigns no OOS attribute; the postpone names nothing
3. R1 takes a snapshot
4. T1: logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE is flushed
5. T1: a postpone appends RVOOS_NOTIFY_VACUUM under the UPDATE's MVCCID (durable)
6. vacuum: consumes notification 1 and reclaims its chains (redo-only)

### no_cancel breaks NeededChainsLive

1. T1: UPDATE assigns c1; the postpone names the dropped chains
2. T1: a statement rollback undoes its newest statement; its postpone stays
3. T1: logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE is flushed
4. T1: a postpone appends RVOOS_NOTIFY_VACUUM under the UPDATE's MVCCID (durable)
5. vacuum: consumes notification 1 and reclaims its chains (redo-only)

### no_cancel breaks NotifyOnlyForCommittedDrop

1. T1: UPDATE assigns c1; the postpone names the dropped chains
2. T1: a statement rollback undoes its newest statement; its postpone stays
3. T1: logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE is flushed
4. T1: a postpone appends RVOOS_NOTIFY_VACUUM under the UPDATE's MVCCID (durable)

### undo_image_drop breaks NeededChainsLive

1. T1: UPDATE assigns no OOS attribute; the postpone names the dropped chains
2. T1: UPDATE assigns no OOS attribute; the postpone names the dropped chains
3. T1: logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE is flushed
4. T1: a postpone appends RVOOS_NOTIFY_VACUUM under the UPDATE's MVCCID (durable)
5. vacuum: consumes notification 1 and reclaims its chains (redo-only)

### undo_image_drop breaks NotifyOnlyForCommittedDrop

1. T1: UPDATE assigns no OOS attribute; the postpone names the dropped chains
2. T1: UPDATE assigns no OOS attribute; the postpone names the dropped chains
3. T1: logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE is flushed
4. T1: a postpone appends RVOOS_NOTIFY_VACUUM under the UPDATE's MVCCID (durable)

### no_identity breaks NeededChainsLive

1. T1: UPDATE assigns c1; the postpone names the dropped chains
2. T1: UPDATE assigns no OOS attribute; the postpone names nothing
3. T1: logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE is flushed
4. T1: a postpone appends RVOOS_NOTIFY_VACUUM under the UPDATE's MVCCID (durable)
5. T1: the postpone is marked run (durable)
6. vacuum: consumes notification 1 and reclaims its chains (redo-only)
7. crash; recovery undoes active transactions and reruns unfinished postpones
8. T1: LOG_COMMIT; the row lock is released
9. T2: UPDATE assigns c1; the postpone names the dropped chains
10. vacuum: consumes notification 1 and reclaims its chains (redo-only)

### no_identity breaks NoWrongDelete

1. T1: UPDATE assigns c1; the postpone names the dropped chains
2. T1: logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE is flushed
3. T1: a postpone appends RVOOS_NOTIFY_VACUUM under the UPDATE's MVCCID (durable)
4. T1: the postpone is marked run (durable)
5. vacuum: consumes notification 1 and reclaims its chains (redo-only)
6. crash; recovery undoes active transactions and reruns unfinished postpones
7. T1: LOG_COMMIT; the row lock is released
8. T2: UPDATE assigns c1; the postpone names the dropped chains
9. vacuum: consumes notification 1 and reclaims its chains (redo-only)

### no_rerun breaks GarbageReclaimed

1. R1 takes a snapshot
2. T1: UPDATE assigns c1; the postpone names the dropped chains
3. T1: a statement rollback undoes its newest statement and cancels its postpone
4. T1: UPDATE assigns c2; the postpone names the dropped chains
5. T1: logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE is flushed
6. crash; recovery undoes active transactions and reruns unfinished postpones
7. T1: LOG_COMMIT; the row lock is released

### restamp breaks NeededChainsLive

1. T1: UPDATE assigns no OOS attribute; the postpone names the dropped chains

### restamp breaks GarbageReclaimed

1. T2: UPDATE assigns no OOS attribute; the postpone names the dropped chains
2. T2: a statement rollback undoes its newest statement and cancels its postpone
3. crash; recovery undoes active transactions and reruns unfinished postpones
4. T1: DELETE sets the delete MVCCID; the chains stay for older snapshots
5. T1 rolls back; its postpones are discarded

### snapshot_source breaks NeededChainsLive

1. T1: UPDATE assigns c1; the postpone names the dropped chains
2. T1: UPDATE assigns no OOS attribute; the postpone names the dropped chains
3. T1: logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE is flushed
4. T1: a postpone appends RVOOS_NOTIFY_VACUUM under the UPDATE's MVCCID (durable)
5. vacuum: consumes notification 1 and reclaims its chains (redo-only)

### snapshot_source breaks NotifyOnlyForCommittedDrop

1. T1: UPDATE assigns c1; the postpone names the dropped chains
2. T1: UPDATE assigns no OOS attribute; the postpone names the dropped chains
3. T1: logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE is flushed
4. T1: a postpone appends RVOOS_NOTIFY_VACUUM under the UPDATE's MVCCID (durable)

### undo_frees_reused breaks NeededChainsLive

1. T1: UPDATE assigns no OOS attribute; the postpone names nothing
2. T1: UPDATE assigns c1; the postpone names the dropped chains
3. T1: a statement rollback undoes its newest statement and cancels its postpone

### design reaches WitnessSharedChainReclaimed

1. T1: UPDATE assigns no OOS attribute; the postpone names nothing
2. T1: UPDATE assigns c1; the postpone names the dropped chains
3. T1: logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE is flushed
4. T1: a postpone appends RVOOS_NOTIFY_VACUUM under the UPDATE's MVCCID (durable)
5. vacuum: consumes notification 1 and reclaims its chains (redo-only)

### design reaches WitnessSnapshotHoldsReclaim

1. T1: UPDATE assigns no OOS attribute; the postpone names nothing
2. T1: UPDATE assigns c1; the postpone names the dropped chains
3. R1 takes a snapshot
4. T1: logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE is flushed
5. T1: a postpone appends RVOOS_NOTIFY_VACUUM under the UPDATE's MVCCID (durable)

### design reaches WitnessDuplicateNotify

1. T1: UPDATE assigns c1; the postpone names the dropped chains
2. T1: UPDATE assigns no OOS attribute; the postpone names nothing
3. T1: logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE is flushed
4. T1: a postpone appends RVOOS_NOTIFY_VACUUM under the UPDATE's MVCCID (durable)
5. crash; recovery undoes active transactions and reruns unfinished postpones
6. T1: a postpone appends RVOOS_NOTIFY_VACUUM under the UPDATE's MVCCID (durable)

### design reaches WitnessCrashInPostponeThenReclaim

1. T1: UPDATE assigns no OOS attribute; the postpone names nothing
2. T1: UPDATE assigns c1; the postpone names the dropped chains
3. T1: logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE is flushed
4. crash; recovery undoes active transactions and reruns unfinished postpones
5. T1: a postpone appends RVOOS_NOTIFY_VACUUM under the UPDATE's MVCCID (durable)
6. T1: the postpone is marked run (durable)
7. vacuum: consumes notification 1 and reclaims its chains (redo-only)
8. vacuum: marks the block done
9. T1: LOG_COMMIT; the row lock is released

### design reaches WitnessPartialRollbackThenCommit

1. T1: UPDATE assigns no OOS attribute; the postpone names nothing
2. T1: UPDATE assigns c1; the postpone names the dropped chains
3. T1: a statement rollback undoes its newest statement and cancels its postpone
4. T1: UPDATE assigns c1; the postpone names the dropped chains
5. T1: logtb_complete_mvcc, then LOG_COMMIT_WITH_POSTPONE is flushed
6. T1: a postpone appends RVOOS_NOTIFY_VACUUM under the UPDATE's MVCCID (durable)
7. T1: the postpone is marked run (durable)
8. T1: LOG_COMMIT; the row lock is released

