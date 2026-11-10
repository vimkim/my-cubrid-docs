# Sidecar lifecycle model

This TLA+ model checks the value lifecycle and reader safety of the Sidecar design in [`../../design.md`](../../design.md) (revision of 2026-11-04, Gate 1 approved), against the engine behavior the design relies on at CUBRID `develop` `e64a04a79` (`/home/vimkim/gh/cb/sidecar`). It replaces the Python interleaving check `/home/vimkim/gh/my-cubrid-docs/.scratch/sidecar/interrogate/revise/retry_rule.py`. A separate model covers recovery, undo and latching (`../recovery/`).

On 2026-11-09 the model gained the rules added after that run: the lock fallback of 5.6 (c), and the P1c rules for lazy reads in 5.6 (a) and I-6 (no lazy read in a statement that calls a routine, and the trid backstop). Their actions map to the code on branch `sidecar` at `407ecead8`, in the same worktree. The store cursor rule of I-7 is checked in the latch model (`../recovery/`, finding 4 there).

## Run

```sh
python3 run.py              # every run; TLC output goes to a new directory under $TMPDIR
python3 run.py NAME ...     # selected runs, by cfg name
```

It needs `java` on PATH and `~/.cache/tlaplus/tla2tools-1.7.4.jar` (TLC 2.19). It prints one line per run with PASS or FAIL, the invariant that failed, the distinct and generated state counts and the time, then OK or UNEXPECTED against the expectation table in `run.py`. It exits 1 if any result is unexpected. The 38 runs took 671 s on 2026-11-09 (measured, 32 workers), and no single run took more than 62 s. After P3 868 round 2 the 44 runs took 785 s on 2026-11-11, all as expected (measured, 32 workers). With several workers TLC does not always report the shortest counterexample; the paths below come from `/statechart`, which uses one worker. The paths of the 2026-11-09 variants come from one-worker runs, with two writers and three statements for the lazy variants.

## Properties

Each property has its own run on the design, and the broken variants below show each one failing.

| Property | It says | The harm when it breaks |
|---|---|---|
| `NoDanglingRef` | Every value a reader returns is exactly the value its returned version names, a protected reader never finds its store record absent, and no writer stamps a store record that is absent or already stamped. | A query returns another row's or another version's bytes as this row's value, or fails with `ER_SIDECAR_DANGLING_REF`. |
| `NoLostRow` | An unprotected reader (committed, dirty or no snapshot) reports the row absent only if the row had no committed live version at some moment of its call. | A copy-area fetch, `btree_load` or the replica's `xlocator_repl_force` skips a live row. |
| `NoOrphan` | After every transaction ends and vacuum quiesces, every live store record is named by exactly one current version, and the current version's ref resolves to its own value. | Store space leaks forever, or a row's value is gone after vacuum. |
| `OneOwner` | I-2, checked whenever no writer holds the row lock. A live unstamped store record is named by exactly one (row, attribute) in the current version, every version in the row's log chain that names a live record names a record of this row, and the current live version names a live unstamped record. | `sidecar_verify_class` reports an orphan or a shared record, and a later stamp or vacuum removes a value that another row still names. |
| `StoreIdentity` | A slot that holds a live record holds the value that every version of the row naming that slot expects (5.6, "Store identity"). | The section 5.6 argument "a present record is the right one" no longer holds, so reader safety needs some other protection. |
| `Bounded` | An unprotected reader's retry loop ends within `MaxRetry` retries (design: 3), or the lock fallback reads the row. | The fetch fails with `ER_SIDECAR_RESOLVE_RETRY` on a row that exists. |
| `NoLazyAfterTranEnd` | A protected reader never fails with `ER_SIDECAR_LAZY_AFTER_TRAN_END`. | A statement fails where `develop` returns the value from the record it holds, which the P1c coordinator ruled a user-visible regression (review R2). |
| `RetryNeedsCommit` | Each retry is paid for by a distinct transaction that stamped a store record and committed during the fetch. | Retries would come from something other than concurrent commits, and no bound would follow from the write rate. |
| `HeapPathNoRetry` | A dirty or no-snapshot reader, which resolves under the hot latch, never retries (5.6 c, "No retry runs on this path"). | The heap-path half of the 5.6 (c) proof is wrong, and those readers can fail or loop where the design says they cannot. |

## What the model contains

One hot row with one large column. Each version of the row names at most one store slot and the value it expects there (`ref`, `val`), or holds its value inline. The model has these parts.

- Writers are transactions. Each takes an MVCCID (`Begin`) and later the row X lock (`LockRow`), and writers may lock in an order other than their MVCCID order. Each runs up to `MaxOps` statements of kind INSERT, LARGE (assign a new external value), INLINE (assign a value small enough to be inline), SMALL (KEEP) and DELETE, then commits, rolls back, or rolls back its last statement and continues.
- Each statement is the sequence of atomic steps of its section 6 flow. A store insert, a stamp and a hot write are separate steps, and every rollback undoes one log record per step in reverse order.
- Hot vacuum and store vacuum each remove a record whose own DELID precedes the vacuum threshold. The threshold is the lowest active MVCCID and every registered lowest visible MVCCID.
- The store is non-reuse. A vacuumed slot becomes `REC_MARKDELETED`. Insert undo frees a slot for reuse, as `spage_delete_for_recovery` does in any heap. Another row's INSERT can take a freed slot.
- One reader runs one fetch, of a class chosen from `ReaderClasses`: a snapshot reader (heap or undo log), a row-lock holder, or an unprotected reader with the committed, dirty or no snapshot that expands under the hot latch with the retry rule and its bound.
- Lock fallback. A committed reader that finds a store record absent after `MaxRetry` retries takes the row S lock, waits while a writer holds the row lock, reads the last version, reports the row absent if a committed transaction deleted it, and otherwise resolves it before it releases the lock.
- Lazy reads across a commit (`RoutineCommit`). A snapshot reader or a row-lock holder may run a statement that calls a routine. Such a reader either expands at the fetch (`NoLazyWithRoutine`) or keeps the version lazy. While it holds a lazy version, the routine may COMMIT. The commit drops the reader's registered lowest visible MVCCID, releases its row lock and changes its trid. The later decode then fails with `ER_SIDECAR_LAZY_AFTER_TRAN_END` when the trid check applies (`TridCheck`), and dereferences otherwise. With `OtherKeep`, another keep of the same thread may replace the lazy note before the decode, and the trid check then does not apply, as in the code.

## Results

Measured on 2026-11-09 with `python3 run.py` (32 TLC workers, TLC 2.19 on Java 8, an 80-core host shared with other jobs). Every result matched its expectation in `run.py`. The 38 runs took 671 s wall, and the longest single run took 62 s (measured). Every design and PASS count of the 30 runs from 2026-11-04 is unchanged, so the new variables add no state where their switches are off. A FAIL count is where TLC stopped, and it varies a little between runs.

| Run | Result | Distinct states | Time |
|---|---|---|---|
| `design_NoDanglingRef` | PASS | 4,686,531 | 50 s |
| `design_NoLostRow` | PASS | 2,912,498 | 31 s |
| `design_Bounded` | PASS | 2,912,498 | 30 s |
| `design_RetryNeedsCommit` | PASS | 2,912,498 | 31 s |
| `design_HeapPathNoRetry` | PASS | 1,751,866 | 20 s |
| `design_NoOrphan` | PASS | 214,853 | 7 s |
| `design_OneOwner` | PASS | 214,853 | 8 s |
| `design_StoreIdentity` | PASS | 214,853 | 8 s |
| `bound_1_two_commits` | FAIL `Bounded` | 1,018,433 | 14 s |
| `bound_3_four_commits` | FAIL `Bounded` | 330,271 | 14 s |
| `broken_no_retry` | FAIL `NoLostRow` | 52,231 | 4 s |
| `broken_no_dead_row_test` | FAIL `Bounded` | 335,235 | 8 s |
| `broken_reuse_no_pin` | FAIL `NoDanglingRef` | 22,663 | 3 s |
| `broken_reuse_pin_after` | FAIL `NoDanglingRef` | 172,316 | 6 s |
| `broken_delete_no_stamp` | FAIL `NoOrphan` | 868 | 1 s |
| `broken_delete_no_stamp_OneOwner` | FAIL `OneOwner` | 448 | 1 s |
| `broken_stamp_after_hot_readers` | PASS | 4,707,276 | 48 s |
| `broken_stamp_after_hot_store` | PASS | 215,379 | 7 s |
| `broken_vacuum_uncommitted` | FAIL `NoDanglingRef` | 12,093 | 3 s |
| `broken_resolve_after_latch` | FAIL `NoDanglingRef` | 9,298 | 2 s |
| `broken_resolve_after_latch_RetryNeedsCommit` | FAIL `RetryNeedsCommit` | 5,081 | 2 s |
| `broken_resolve_after_latch_HeapPathNoRetry` | FAIL `HeapPathNoRetry` | 3,704 | 2 s |
| `broken_snapshot_unregistered` | FAIL `NoDanglingRef` | 33,326 | 3 s |
| `later_reuse_pin_before_NoDanglingRef` | PASS | 5,394,191 | 54 s |
| `later_reuse_pin_before_NoLostRow` | PASS | 3,477,520 | 38 s |
| `later_reuse_pin_before_Bounded` | PASS | 3,477,520 | 48 s |
| `later_reuse_pin_before_NoOrphan` | PASS | 238,634 | 10 s |
| `later_reuse_pin_before_OneOwner` | FAIL `OneOwner` | 2,589 | 4 s |
| `later_reuse_pin_before_StoreIdentity` | FAIL `StoreIdentity` | 1,113 | 4 s |
| `later_reuse_pin_before_no_dead_row` | FAIL `NoDanglingRef` | 19,993 | 6 s |
| `fallback_two_commits` | PASS | 1,375,715 | 37 s |
| `fallback_four_commits` | PASS | 331,558 | 28 s |
| `broken_fallback_no_lock` | FAIL `NoDanglingRef` | 25,310 | 7 s |
| `lazy_design` | PASS | 4,092,289 | 57 s |
| `broken_lazy_across_commit` | FAIL `NoDanglingRef` | 114,375 | 6 s |
| `lazy_backstop_only_NoDanglingRef` | PASS | 4,801,135 | 62 s |
| `lazy_backstop_only_NoLazyAfterTranEnd` | FAIL `NoLazyAfterTranEnd` | 5,395 | 2 s |
| `lazy_backstop_other_keep` | PASS (FAIL `NoDanglingRef`, 189,198 states, before P3 868) | 7,156,831 | 68 s |
| `lazy_backstop_other_keep_NoLazy` | FAIL `NoLazyAfterTranEnd` | 4,607 | 2 s |
| `broken_backstop_latest_only` | FAIL `NoDanglingRef` | 226,889 | 7 s |
| `lazy_earlier_keep` | PASS | 2,647,626 | 33 s |
| `broken_first_keep_per_request` | FAIL `NoLazyAfterTranEnd` | 3,250 | 2 s |
| `lazy_backstop_other_keep_earlier` | PASS | 7,156,831 | 73 s |
| `broken_first_keep_any_scan_end` | FAIL `NoDanglingRef` | 259,185 | 7 s |

## Broken variants

Each variant changes one rule of the design. The paths are TLC's shortest counterexamples, told by `/statechart` with one worker on the variant's own cfg and shortened here by merging a transaction's begin, lock and statement start into its first step. "Slot" means a store record's OID.

**No retry** (`broken_no_retry`) fails `NoLostRow` in 16 steps. This is the case the retry rule exists for.

1. T1 inserts the row with value 1 in slot 1 and commits.
2. T2 stamps DELID 2 on slot 1 and writes a version that holds its new value inline.
3. A committed-snapshot reader finds the current version too new and reads T1's version from the undo log. It names slot 1.
4. T2 commits, and store vacuum removes slot 1.
5. The reader finds slot 1 absent and reports the row absent, while T2's committed version is live.

**Reuse store, no pin** (`broken_reuse_no_pin`) fails `NoDanglingRef` in 14 steps.

1. T1 inserts the row with value 1 in slot 1, deletes it in the same transaction, stamping slot 1 and the hot record, and commits.
2. Store vacuum removes slot 1, and the reuse store frees the slot.
3. Another row's INSERT puts its value into slot 1.
4. A reader with no snapshot reads the deleted hot record under the hot latch, resolves slot 1 and returns the other row's value as this row's.

**Reuse store, pin after the visibility decision** (`broken_reuse_pin_after`) fails `NoDanglingRef` in 18 steps. This is interrogation finding 4a.

1. T1 inserts the row with value 1 in slot 1 and commits.
2. T2 stamps slot 1 and writes a version with an inline value.
3. A committed-snapshot reader reads T1's version from the undo log. It names slot 1.
4. T2 commits. Vacuum removes slot 1, and another row's INSERT takes the slot.
5. The reader pins the lowest active MVCCID, now 3, which no longer covers T2, and returns the other row's value.

**DELETE skips the stamp** (`broken_delete_no_stamp`) fails `NoOrphan` in 9 steps, and `broken_delete_no_stamp_OneOwner` fails `OneOwner`.

1. T1 inserts the row with value 1 in slot 1.
2. T1 deletes the row with DELID on the hot record only, and commits.
3. Hot vacuum removes the row. Slot 1 stays live with no DELID and no row names it, so no vacuum ever removes it.

**Vacuum removes on an uncommitted DELID** (`broken_vacuum_uncommitted`) fails `NoDanglingRef` for a snapshot reader in 14 steps.

1. T1 inserts the row with value 1 in slot 1 and commits.
2. T2 stamps DELID 2 on slot 1 and is still active.
3. Store vacuum removes slot 1.
4. A snapshot reader registers, reads T1's current version from the heap and finds slot 1 absent (`ER_SIDECAR_DANGLING_REF`).

**Unprotected reader resolves after releasing the hot latch** (`broken_resolve_after_latch`) fails `NoDanglingRef` in 12 steps. Two companion runs fail as well. When the rollback frees slot 1 and no other row takes it, the reader finds the slot absent and retries. That breaks `HeapPathNoRetry` (`broken_resolve_after_latch_HeapPathNoRetry`), and since no commit paid for the retry it also breaks `RetryNeedsCommit` (`broken_resolve_after_latch_RetryNeedsCommit`).

1. T1 inserts the row with value 1 in slot 1 and starts to roll back.
2. A dirty-snapshot reader reads T1's version and releases the hot latch before it resolves.
3. T1's undo removes the hot record, then deletes its store record and frees slot 1 for reuse. Insert undo frees the slot even in a non-reuse heap (`storage/slotted_page.c:2148-2172`).
4. Another row's INSERT takes slot 1, and the reader returns that row's value.

This is the one exception in 5.6, "Why a present record is the right one". Resolving under the hot latch is what closes it.

**Snapshot not registered** (`broken_snapshot_unregistered`) fails `NoDanglingRef` in 16 steps.

1. T1 inserts the row with value 1 in slot 1 and commits.
2. T2 stamps slot 1 and writes a version with an inline value.
3. A reader builds a snapshot that uses `mvcc_satisfies_snapshot` but is not the transaction's registered one.
4. T2 commits, and vacuum removes slot 1, because no registration holds the threshold back.
5. The reader reads T1's version from the undo log and finds slot 1 absent.

This is why 5.6 (a) compares the snapshot with the transaction's registered snapshot and not only `snapshot_fnc` (11, change 4).

**Retry without the committed-DELID test** (`broken_no_dead_row_test`) fails `Bounded` in 19 steps.

1. T1 inserts the row, deletes it in the same transaction, stamping slot 1 and the hot record, and commits.
2. Store vacuum removes slot 1 before hot vacuum removes the row.
3. A reader with no snapshot reads the deleted hot record, finds slot 1 absent and retries.
4. Every re-read finds the same record, so after three retries the fetch fails with `ER_SIDECAR_RESOLVE_RETRY`.

**Retry bound without the lock fallback** (`bound_1_two_commits`, bound 1, `LockFallback = FALSE`) fails `Bounded` in 26 steps.

1. T1 inserts the row with value 1 in slot 1 and commits.
2. T2 inserts value 2 in slot 2, stamps slot 1 and writes a version naming slot 2. T3 takes an MVCCID.
3. A committed-snapshot reader reads T1's version from the undo log.
4. T2 commits. T3 stamps slot 2 and writes an inline version. Vacuum removes slot 1.
5. The reader retries and reads T2's version from the undo log, because T3 is active.
6. T3 commits and vacuum removes slot 2. The reader has no retry left.

**Design retry bound without the lock fallback** (`bound_3_four_commits`, bound 3, `LockFallback = FALSE`) fails `Bounded` in 47 steps. The path comes from the run's own TLC trace, because a one-worker search of this cfg is slow. Five writers run one statement each, INSERT or LARGE, without rollback.

1. T1 inserts the row with value 1 in slot 1 and commits. T2 inserts value 2 in slot 2, stamps slot 1 and writes its version.
2. A committed-snapshot reader reads T1's version from the undo log.
3. T2 commits. T3 inserts value 3, stamps slot 2 and writes its version, and vacuum removes slot 1. The reader finds slot 1 absent, retries and reads T2's version from the undo log, because T3 is active.
4. T3 and then T4 repeat step 3. Each commits after the next writer has written its version, vacuum removes the record the reader holds, and the reader retries and reads the next older version from the undo log.
5. After its third retry the reader holds T4's version. T5 commits and vacuum removes slot 4, so the fetch fails with `ER_SIDECAR_RESOLVE_RETRY` although the row is live.

**Lock fallback** (`fallback_two_commits`, `fallback_four_commits`) passes `NoDanglingRef`, `NoLostRow` and `Bounded` on the same two shapes. The paths above now end in `sidecar_fetch_locked`. The S lock waits until no writer holds the row, every stamp needs the row X lock, and so the store records the last version names stay present until the reader releases the lock. Lifecycle finding 1 no longer fails.

**Lock fallback without the S lock** (`broken_fallback_no_lock`, bound 1, four writers) fails `NoDanglingRef` in 39 steps.

1. T1 inserts the row with value 1 in slot 1 and commits. T2 inserts value 2 in slot 2, stamps slot 1 and writes its version.
2. A committed-snapshot reader reads T1's version from the undo log. T2 commits. T3 inserts value 3 in slot 3, stamps slot 2 and writes its version. Vacuum removes slot 1.
3. The reader retries and reads T2's version from the undo log. T3 commits. T4 inserts value 4 in slot 4 and stamps slot 3. Vacuum removes slot 2.
4. The reader has no retry left and takes the fallback, but without the lock. It reads the last version, T3's, which names slot 3.
5. T4 writes its version and commits, and vacuum removes slot 3. The reader finds slot 3 absent (`ER_SIDECAR_DANGLING_REF`).

The S lock is what makes the fallback's read safe. It is not only a way to stop retrying.

**Lazy read across a routine's COMMIT** (`broken_lazy_across_commit`: `NoLazyWithRoutine = FALSE`, `TridCheck = FALSE`) fails `NoDanglingRef` in 18 steps. This is P1c review R2.

1. T1 inserts the row with value 1 in slot 1 and commits.
2. T2 stamps slot 1 and writes a version with an inline value.
3. A repeatable-read reader registers its snapshot. Its statement calls a routine. T2 commits.
4. The reader reads T1's version from the undo log and keeps it lazy. It names slot 1.
5. The routine commits the reader's transaction, which resets its registered lowest visible MVCCID. Vacuum removes slot 1.
6. The reader decodes the column and finds slot 1 absent (`ER_SIDECAR_DANGLING_REF`).

**The design rules for lazy reads** (`lazy_design`) pass `NoDanglingRef` and `NoLazyAfterTranEnd` for snapshot readers and row-lock holders whose statement may call a committing routine, with the lazy note replaceable. A statement with a routine call reads expanded at the fetch, so no lazy version lives across the commit, and the trid check never fires.

**Only the trid backstop** (`lazy_backstop_only_*`: `NoLazyWithRoutine = FALSE`, standing for a routine call the mark misses) passes `NoDanglingRef` but fails `NoLazyAfterTranEnd` in 11 steps.

1. T1 inserts the row with value 1 in slot 1 and commits.
2. A reader whose statement calls a routine reads T1's version and keeps it lazy.
3. The routine commits.
4. The reader decodes the column. The trid differs, so it fails with `ER_SIDECAR_LAZY_AFTER_TRAN_END` and reads nothing.

The backstop turns a wrong read into an error, which is why E22's mark, not the check, is the fix.

**The backstop with a replaced note** (`lazy_backstop_other_keep`: the mark missed and `OtherKeep = TRUE`) failed `NoDanglingRef` in 19 steps (finding 5). With `FirstKeepTrid` (P3 868) it passes, and the same run checked for `NoLazyAfterTranEnd` shows the decode fails with the backstop error. `broken_backstop_latest_only` sets `FirstKeepTrid = FALSE` and fails `NoDanglingRef`.

**When the first keep is forgotten** (P3 868 round 2, measured 2026-11-11). `rfirst` is the first keep the trid check uses for a ref outside the latest note: none, a keep of an ended earlier transaction (`stale`), the reader's own transaction (`own`), or a keep made after the routine's COMMIT (`late`). `EarlierKeep` lets an ended scan of the same thread have kept a record in an earlier transaction with no request end since, as in SA_MODE. `FirstKeepReset` picks the rule. The design, `"noscan"`, forgets the first keep when the thread's last scan that kept ends. `lazy_earlier_keep` (no routine commit, another keep, an earlier keep) passes `NoLazyAfterTranEnd`. `broken_first_keep_per_request` forgets it only at the request's end, as `6ec8d66eb` did, and fails `NoLazyAfterTranEnd`: a valid read fails with the backstop error. `broken_first_keep_any_scan_end` forgets it when the other scan ends while the reader's scan is open, and fails `NoDanglingRef`. `lazy_backstop_other_keep_earlier` passes `NoDanglingRef`.

1. Steps 1 to 5 of `broken_lazy_across_commit`. The reader holds T1's version lazy, the routine commits, and vacuum removes slot 1.
2. Another keep on the same thread replaces the lazy note.
3. The reader decodes the column. Its ref is outside the latest note, so `sidecar_resolve_slot` does not compare the trid. It reads slot 1 and finds it absent (`ER_SIDECAR_DANGLING_REF`).

**Stamp after the hot write** (`broken_stamp_after_hot_readers`, `broken_stamp_after_hot_store`) passes every property. UPDATE and DELETE write the hot version first and stamp the dropped record afterwards, inside the same transaction. The row X lock keeps other writers out, and vacuum waits for the stamper's commit either way, so no reader and no store state can tell the two orders apart. The "before the hot write" half of I-4 is therefore not what keeps readers safe. The order still matters to section 7.1 as written (inferred from its text, not checked). The module restores the replication LSAs after its last store write and before the hot write, so that the hot write is the last capture, and a stamp that relocates its record logs `RVHF_INSERT_NEWHOME`, which sets `repl_update_lsa`. A stamp after the hot write would need its own save and restore that keeps the hot write's `repl_update_lsa`. This model does not cover replication or recovery.

**Later optimization: reuse store with a pin before the visibility decision** (`later_reuse_pin_before_*`). The reader properties pass: `NoDanglingRef` (all five reader classes), `NoLostRow` and `Bounded`. `NoOrphan` passes too. `OneOwner` and `StoreIdentity` fail, in 11 steps.

1. T1 inserts the row with value 1 in slot 1, then in the same transaction stamps slot 1 and writes a version with an inline value, and commits.
2. Store vacuum removes slot 1, and the reuse store frees the slot.
3. Another row's INSERT puts its value into slot 1. T1's first version, still in the row's undo log chain, names slot 1 and expects value 1.

No reader can reach that old version once vacuum has passed it, so this hurts no reader in the model. But I-2 ("plus older versions of the same row in the log") and the 5.6 store-identity argument ("a store OID names at most one value") are false for a reuse store, so reader safety there rests on the pin alone. `later_reuse_pin_before_no_dead_row` shows that the pin also needs the first draft's dead-row rule. It fails `NoDanglingRef` in 14 steps.

1. T1 inserts the row with value 1 in slot 1, deletes it in the same transaction and commits.
2. Store vacuum removes slot 1, the slot is freed, and another row's INSERT takes it.
3. A reader with no snapshot pins the lowest active MVCCID, now 2, reads the deleted hot record under the hot latch and returns the other row's value.

The pin protects only stamps at or after it. A row deleted before the pin can already have lost its store record, so the reader must treat a version whose DELID precedes the pin as dead without resolving it.

## Findings

No property fails on the design within the bounds. Every broken variant fails the property it guards, except stamping after the hot write (finding 3). These points remain.

**1. The retry bound of three holds only while at most three stamping commits meet one fetch. Resolved by the lock fallback (2026-11-09).** `fallback_four_commits` passes on the path below, and `fallback_two_commits` passes with bound 1 against every statement kind and rollback. The fallback can wait for the row's writer, where `develop`'s committed fetch never waits. The model has no fairness, so it does not show that the wait ends. `RetryNeedsCommit` passes, so every retry is paid for by a distinct transaction that stamped one of the row's store records and committed during the fetch, and vacuum removed that record inside the same window. Within the bounds nothing else causes a retry on the design. A committed-snapshot fetch therefore exceeds the bound only when four such transactions commit on the same row during that one fetch, and `bound_3_four_commits` shows that path. The fetch then fails with `ER_SIDECAR_RESOLVE_RETRY` on a live row. Section 5.6 (c) and section 12 call the bound a guess and leave it to P3. The model states the condition that P3's stress run must provoke: a row under a stream of large-column UPDATEs or DELETEs, each committed and vacuumed while one committed-snapshot fetch is open. Dirty and no-snapshot readers never retry on the design, because they resolve under the hot latch.

**2. The 5.6 (c) log-path argument misses one case, though its conclusion holds.** The text says the stamper "wrote the first version after V that dropped s" and the retry reads a current version that "does not name s". A DELETE breaks that sentence. The shortest path, found with a scratch invariant that counted only UPDATE stamps, has 18 steps.

1. T1 inserts the row with value 1 in slot 1 and commits.
2. T2 updates small columns only (KEEP), so its version still names slot 1, then deletes the row in the same transaction, stamping slot 1 and the hot record.
3. A committed-snapshot reader finds T2's version too new and reads T1's version from the undo log.
4. T2 commits, and vacuum removes slot 1.
5. The reader retries. The current version still names slot 1, but its DELID is committed, so `mvcc_satisfies_committed` returns TOO_OLD and the reader reports the row absent, which is correct.

The argument should say that the current version either no longer names `s` or carries the stamper's committed DELID. The retry count in finding 1 counts DELETE commits for this reason.

**3. The order half of I-4 is not load-bearing for reader safety.** Stamping after the hot write passes every property here (see the variant above). I-4 states the order without a reason. As far as this model can tell, the reason lives in section 7.1's replication-LSA capture and in the crash cases of section 6, which the recovery model checks. Saying so in I-4 would keep a later change from dropping or keeping the order for the wrong reason.

**4. The documented later optimization is safe for readers in the model, but it needs I-2 and section 5.6 restated.** With the reuse store and the pin before the visibility decision, plus the dead-row rule, no reader returns a wrong value, loses a live row or exhausts its retries. Old versions in a row's undo log chain do name slots that later hold another row's value, so I-2 must count only versions a reader can still reach, and the 5.6 "store identity" step no longer holds. Without the dead-row rule the pin alone fails (`later_reuse_pin_before_no_dead_row`), which matches section 13's "plus the first draft's dead-row rule".

**5. The trid backstop covers only the thread's latest lazy keep.** `sidecar_Lazy` is one record per thread (`storage/sidecar.cpp:1967`), and every keep replaces it (`sidecar_lazy_note`, `:1988-2003`). `sidecar_resolve_slot` compares the trid only for a ref inside that latest range (`:2504`). A ref kept earlier is dereferenced without the check (`lazy_backstop_other_keep`). On the design this is harmless, because a statement with a routine call keeps nothing lazy (`lazy_design` passes). It matters only when the routine mark misses a call, which is the one case the backstop exists for. An earlier keep is decoded after a later one on the same thread (inferred from code, P3 868): a filter iterator driving a join hands out each copied row and reads its values after the inner scan kept its row (`scan_batch_iter_next`). Fixed by `sidecar_Lazy_first_trid` (rule `FirstKeepTrid`). The lock holder's lazy read of an UPDATE's old record (`HEAP_SIDECAR_LAZY_LOCKED`, `storage/sidecar.cpp:2274-2283`) records no note at all (inferred from reading). Its read and decode run inside `locator_attribute_info_force` with no routine call between them (inferred, not checked).

## Mapping from model to design and code

Paths are under `src/` at `e64a04a79`. "New" means Sidecar code that does not exist yet.

| Model action or definition | Design | Engine behavior it relies on |
|---|---|---|
| `Begin` | A transaction's MVCCID, taken at its first write, possibly on another row before it locks this one | `transaction/log_tran_table.c:4204-4221`, `transaction/mvcc_table.cpp:566` |
| `LockRow` | The row X lock serializes every store write for the row (6, UPDATE step 1; 5.6 b) | `transaction/locator_sr.c:13451` |
| `StartOp` | The plan reads the old record under the hot latch and lists the dropped ref (5.3, 6 UPDATE step 4) | `storage/heap_file.c:25191-25218` |
| `StoreInsert` | Store insert before the hot write (I-1, I-7; 6 INSERT step 5, UPDATE step 5) | `heap_insert_logical`, `storage/heap_file.c:24649`; slot choice `storage/slotted_page.c:1286` |
| `Stamp` | Unlink by stamp before the hot write (I-4; 6 UPDATE step 5, DELETE step 2) | `heap_delete_logical`, `storage/heap_file.c:24880` |
| `HotInsert`, `HotUpdate`, `HotDelete` | The hot write under the hot page X latch (6 INSERT step 7, UPDATE step 6, DELETE step 3) | `storage/heap_file.c:24649`, `:25087`, `:24880`; prev_version chain `:27093` |
| `Commit` | The writer ends its MVCCID and releases the row lock | `transaction/mvcc_table.cpp:465`, `transaction/log_manager.c:5255`, `:5305` |
| `Abort`, `UndoStep`, `UndoEnd` | Rollback in reverse LSA order (6 Rollback); the MVCCID ends only after the undo | `transaction/log_manager.c:5371`, `:5384`, `:5387`; `heap_rv_undo_insert` `storage/heap_file.c:17501` through `storage/slotted_page.c:2148-2172`; `heap_rv_mvcc_undo_delete` `storage/heap_file.c:17625` |
| `PartialRollback`, `PartialEnd` | Statement rollback (6 Statement rollback, CBRD-27237 sequence) | `log_abort_partial`, `transaction/log_manager.c:5637` |
| `ForeignInsert` | Another row's store insert takes a freed slot | `storage/slotted_page.c:1286` |
| `StoreVacuum`, `HotVacuum` | Two vacuum streams, each from its own DELID, neither reads a ref (I-5; 6 Vacuum) | `mvcc_satisfies_vacuum` `transaction/mvcc.c:321`; `spage_vacuum_slot` `query/vacuum.c:2398` with `reusable` from the file type `:2568`; `storage/slotted_page.c:4853-4860`; empty store pages stay `query/vacuum.c:1853` |
| `Threshold`, `LowestActive` | When vacuum may remove a store record (5.6) | `compute_oldest_visible_mvccid` `transaction/mvcc_table.cpp:355`; job gate `query/vacuum.c:3129-3156` |
| `RStart` for `snap` | The snapshot reader registers its lowest visible MVCCID (5.6 a) | `transaction/mvcc_table.cpp:251-285`, `:332` |
| `SnapRead` | Snapshot read from the heap or the undo log (5.6 a; 6 Old-version snapshot read) | `mvcc_satisfies_snapshot` `transaction/mvcc.c:156`; `storage/heap_file.c:27039-27047`, `:26693` |
| `PResolve`, `PRelease` | Lazy dereference by a protected reader (`sidecar_read_value`, `ER_SIDECAR_DANGLING_REF`) | New |
| `LockAcquire`, `LockRead` | Row-lock holder reads the last version (5.6 b) | `heap_get_last_version` `storage/heap_file.c:27197`; `transaction/locator_sr.c:13116`, `:13206-13256` |
| `URead` | Unprotected reads under the hot latch (5.6 c). The committed reader takes an older version from the undo log when the current one is too new, and the log walk may release the hot page | `mvcc_satisfies_dirty` `transaction/mvcc.c:516-620`; `mvcc_satisfies_committed` `:642-675`; `storage/heap_file.c:26774-26781` |
| `UResolve` | `sidecar_on_fetch` and the retry rule (5.6 c) | New |
| `UPin`, `Pin = "before"` | The first draft's horizon pin and dead-row rule (11 change 1; 13) | New |

The rows below map to branch `sidecar` at `407ecead8`.

| Model action or definition | Design | Code at `407ecead8` |
|---|---|---|
| `UResolve`, retry and exhaustion | 5.6 (c), retry rule | `sidecar_on_absent` `storage/sidecar.cpp:2214-2247`, `SIDECAR_RETRY_BOUND` `:364`; past the bound a committed snapshot returns `S_SIDECAR_LOCK_NEEDED` `:2238-2244` |
| `UResolve` to `LockAcquire` with `rfb` | 5.6 (c), lock fallback; I-6 | `xlocator_fetch` path, `locator_get_object` then `sidecar_fetch_locked` `transaction/locator_sr.c:2345-2349` |
| `LockAcquire` (`rfb`) | 5.6 (c), lock fallback | `lock_object (..., S_LOCK, LK_UNCOND_LOCK)` `storage/sidecar.cpp:2381` |
| `LockRead`, `PResolve` (`rfb`) | 5.6 (b) | `heap_get_last_version` `:2387`, `mvcc_satisfies_committed` on its header `:2400-2421`; `TOO_OLD_FOR_SNAPSHOT` gives `S_DOESNT_EXIST` |
| `PRelease` (`rfb`) | 5.6 (c), "releases the lock when the fetch ends" | `lock_unlock_object` unless the lock was held before `:2425-2428` |
| `RStart` with `rrout` | 5.6 (a), no lazy read in a statement that calls a routine; I-6 | `XASL_HAS_ROUTINE_CALL` from the unpacker (E23); `qexec_execute_query` sets `sidecar_no_lazy` `query/query_executor.c:22720-22721`, restores it `:22907` |
| `Keep` | 5.6 (a); P1c E2, E22 | `scan_start_scan` opts in only without the mark `query/scan_manager.c:4063`, `:4167`; `sidecar_keep_lazy` `storage/sidecar.cpp:2008-2015` notes the trid `:2001` |
| `RCommit` | 5.6 (a), "Protection ends with the transaction" | a routine's COMMIT: `log_complete` replaces `LOG_TDES.trid`; `reset_transaction_lowest_active` `transaction/log_manager.c:5841`, `:6128` |
| `RReplaceNote` | none | `sidecar_Lazy` is one per thread `storage/sidecar.cpp:1967`; `sidecar_lazy_note` overwrites it `:1988-2003` |
| `PResolve` with `TridCheck` | 5.6 (a), the trid backstop; I-6 | `sidecar_resolve_slot` `storage/sidecar.cpp:2504-2511`, `ER_SIDECAR_LAZY_AFTER_TRAN_END` `base/error_code.h:1803` |

Design switches in each cfg select the broken variants. `LockFallback`, `FallbackLocks`, `NoLazyWithRoutine` and `TridCheck` are design rules, TRUE on the design. `RoutineCommit` and `OtherKeep` are scenario switches that let the reader's statement commit through a routine and let another keep replace the lazy note. `StoreReuse` makes vacuum leave a store slot free for reuse (`FILE_HEAP_REUSE_SLOTS`). `Pin` adds the horizon pin before or after the visibility decision. `Retry`, `DeadRowTest`, `DeleteStamps`, `StampFirst`, `ResolveUnderLatch` and `SnapRegister` turn off one rule each. `VacuumUncommitted` lets store vacuum remove a record whose DELID writer is still active.

## Bounds and assumptions

The design runs use these bounds. The cfg files state them.

- Three writer transactions, at most two statements each and four in all.
- At most three values for the row (each INSERT, LARGE and INLINE makes one) and four store slots.
- One insert by another row, into a freed slot.
- One reader with one fetch, and the design's retry bound of three.
- Symmetry over writer names. Reader runs stop exploring a behavior once the reader is done (`CONSTRAINT ReaderOpen`), because its result is final there.

Under these bounds a fetch can meet at most two commits that stamp a store record, so `design_Bounded` cannot reach the bound of three. `bound_3_four_commits` and `fallback_four_commits` (five writers, one statement each, INSERT and LARGE only, no rollback, the committed reader) check the design bound itself. `fallback_two_commits` uses the design bounds with bound 1, so the fallback meets every statement kind, rollback and statement rollback. `broken_fallback_no_lock` uses four writers, one statement each, INSERT and LARGE only, and bound 1, because the fallback's own read needs a fourth stamping writer to go wrong.

The lazy runs (`lazy_*`, `broken_lazy_across_commit`) use the design bounds with the snapshot and row-lock reader classes. The reader's one fetch may call one committing routine between its fetch and its decode.

The model rests on these assumptions. Each one either matches the code or only adds behaviors.

1. One reader per run is enough. A second reader only adds a hot latch hold, a row lock hold or a registered MVCCID, and each of these only disables writer or vacuum steps. So whatever one reader sees beside a second reader, it can also see alone. For the same reason, `NoOrphan`, `OneOwner` and `StoreIdentity` run with no reader, since readers change no row or store state.
2. Vacuum may remove any eligible record at any time, using the current threshold. Real vacuum works from log blocks with a threshold it computed earlier. The threshold never decreases, because a new registration takes the current lowest active MVCCID (`transaction/mvcc_table.cpp:251-285`), so real removals are a subset of the modeled ones.
3. A step is atomic: one store insert, one stamp, one hot write, one undo record, one store read. Page latches inside a step are not modeled. The hot latch is modeled where a reader holds it across steps. An unprotected heap-path reader holds it from its read to its resolve (5.6 c). The committed reader's log path may keep or release it. Protected readers never hold it across steps, which is the worst case for a lazy dereference. Hot writes, hot undo and hot vacuum wait for it. Store steps never need it.
4. A snapshot reader picks its visible version in one step, at any time after it built its snapshot. MVCCIDs grow with `Begin`, and `Begin` may come long before `LockRow`, so the row's lock order can differ from MVCCID order, as with lazily assigned MVCCIDs.
5. The writer stamps the ref it listed in its plan. The plan step is atomic and holds the row X lock, so the old record cannot change under it.
6. The log keeps every old version, and the current version's prev_version chain is always readable. Hot vacuum of a deleted row removes the row and its chain.
7. The row has one identity. INSERT runs only while the row has never had a committed insert.

## Not covered

- Crash and restart, the undo of a relocation that a stamp causes, the develop windows 774, 775 and 776, and latching inside a step. The recovery model in `../recovery/` covers these.
- More than one large column. A DELETE that names several store records stamps each of them with the same step, one after another.
- `REC_RELOCATION` and `REC_BIGONE` records, and the release-and-relocate step of UPDATE and DELETE (12, open item).
- Replication (7.1). The KEEP meaning on the replica, `sidecar_localize_replicated`, the fresh-value list and the applier splice run on a replica's own store and never dereference a master ref (I-8), so they are outside this model.
- CDC and flashback, deferred in the POC (Q4).
- Partition moves and `sidecar_inline_kept`, the I-3 checks of kept refs, and the equal-length compare of fully inline UPDATE images. The model has the two outcomes of that compare, KEEP and LARGE, as statements.
- Sub-transaction MVCCIDs of `SELECT ... INCR` (`query/query_executor.c:20198`), which commit before their parent. They update numeric columns only, so they would be KEEP updates.
- SA mode, MVCC-disabled classes, bulk load, the page batch, `heap_prefetch` and copy-area asserts. The store cursor is in the latch model (`../recovery/`).
- A routine's COMMIT before the fetch or between two rows, a snapshot rebuilt by a nested READ COMMITTED statement (P1c E13), parallel workers that read the leader's mark (E24), the batch's page and copy keeps (E14, E25), and the UPDATE's locked old-record read (`HEAP_SIDECAR_LAZY_LOCKED`). The lazy runs have one fetch with one commit between it and its decode.
- Whether the lock fallback's wait ends. Without fairness, a writer that never commits keeps the reader waiting.
- Liveness beyond the retry bound. The model has no fairness, so it does not show that a writer or vacuum eventually runs.
- Larger counts than the bounds above.

## Keeping it in step

Last confirmed against `design.md` of 2026-11-04 and `develop` `e64a04a79`. The lock fallback and lazy-read actions were confirmed against `design.md` of 2026-11-09 (5.5, 5.6) and branch `sidecar` at `407ecead8`. Recheck the model when a change touches sections 5.5, 5.6 or 6 of the design, the retry rule, the store's slot policy, or any engine line in the mapping table. Move this line forward only after rereading those sections and lines.
