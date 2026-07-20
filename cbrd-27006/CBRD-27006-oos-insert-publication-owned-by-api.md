# [CBRD-27006] OOS insert publication is owned by public OOS insert APIs

## Purpose

OOS insert publication means registering successful OOS insert results while master-side replication tracking is active. Its transient state is the ordered pairing of `thread_p->oos_oids` and `tdes->oos_insert_lsa_queue`: public OOS insert APIs append the OID entries, while OOS WAL processing conditionally enqueues their corresponding LSAs. Before CBRD-27006, OID publication responsibility could be split between OOS insert helpers and their callers, which became fragile once scalar insert and batch insert had to share one contract.

- AS-IS: A caller could receive an OOS OID from `oos_insert()` and then push it into `thread_p->oos_oids` itself.
- TO-BE: Public OOS insert APIs publish OOS OIDs themselves. The logical heap OOS insert-preparation boundary resets publication state before its first fallible preparation step, and callers do not push returned OIDs again.

## Implementation

`oos_insert()` appends the returned head OOS OID on success. `oos_insert_many()` appends each request result in logical request order. With master-side replication tracking active, OOS WAL processing independently appends the corresponding LSAs to `tdes->oos_insert_lsa_queue`; downstream replication logging consumes one matching LSA for each OID entry. With tracking disabled, no LSA is enqueued and the OID-only state is not called a complete publication pair. For multi-chunk values, the existing dummy marker and head OID behavior is preserved when tracking is active, so replication can still distinguish a boundary marker from the real head OID.

This contract is important for mixed single-chunk and multi-chunk rows. Dummy markers and real head OIDs must stay in attribute order because `locator_fixup_oos_oids_in_recdes()` consumes `thread_p->oos_oids` while walking the replicated heap record's OOS-marked attributes.

The scalar caller in `src/transaction/locator_sr.c` no longer pushes the returned OID itself. The public OOS header exposes `oos_insert()` and `oos_insert_many()`, but does not need a caller-side publication helper.

## Publication-state lifetime

For the heap-record transformation path, one logical OOS insert preparation begins at `heap_attrinfo_insert_to_oos()`. That boundary owns exactly one start reset through an OOS-owned helper, before temporary-vector reservation, attribute serialization, class heap lookup, OOS VFID lookup or creation, and `oos_insert_many()`.

The strict start-reset helper owns transaction-descriptor lookup and clears both `thread_p->oos_oids` and `tdes->oos_insert_lsa_queue`. It resolves the descriptor before changing either container, so a missing `LOG_TDES` leaves both untouched and returns failure instead of reporting a half-reset. Consequently, `heap_oos_insert_serialized_values()` only owns class/OOS-file lookup and insertion; it must not perform a redundant late reset. This makes allocation, serialization, class lookup, and OOS-file lookup failures observe publication state that was already cleared at the logical-operation boundary.

Start reset and partial-failure cleanup are different contracts:

- Start reset discards state left by a previous logical operation before the current operation can fail.
- `oos_insert_many()` validates every request before installing a `scope_exit` partial-failure guard. From the first physical insert onward, any error return lets the guard run no-throw, best-effort cleanup. With a resolvable `LOG_TDES`, it clears both OID/LSA sides. Without one, it clears the accessible worker-local OID side, does not guess another transaction's LSA queue, and preserves the original insertion error. Complete success calls `release()` so the publication survives. The transaction must still abort so WAL undo can remove partially inserted OOS chunk records.
- `oos_insert()` has the same validation-before-guard and `std::bad_alloc` conversion contract at its scalar public boundary. A successful log-applier scalar call releases its guard so OIDs can accumulate across consecutive OOS items. A scalar failure leaves the guard armed, clears the pending accumulator, and requires the caller to abort that OOS-plus-heap-row group.
- Successful publication is not cleared at function exit. It remains available until the existing replication consumer uses it.

The `scope_exit` guards do not replace start reset. Each public API installs its guard after its own validation, where physical insertion can begin publishing current-operation state. The logical heap boundary still resets previous-operation state before vector reservation and serialization. This keeps the two cleanup responsibilities explicit and avoids broadening validation-error behavior before any current publication is possible.

The all-or-nothing paired guarantee applies to strict start reset, not to failure cleanup. Failure cleanup runs only after another error already requires the transaction path to stop, so it must not overwrite that error or pretend it safely identified an LSA queue when `LOG_TDES` is unavailable.

This ownership applies specifically to the heap-record transformation path. A genuinely independent entry point may own its own start reset, but it must define a separate logical-operation boundary rather than duplicate clearing inside this path.

## Replication-apply OID accumulation is not publication state

On the slave apply path, consecutive `LC_FLUSH_INSERT_OOS` items produce slave-local real head OOS OIDs that the following heap-row item uses to replace master-side placeholders. This is replication-apply OID accumulation, not master-side OID/LSA publication: the slave does not generate another OOS replication stream, so there is no paired LSA side.

`xlocator_repl_force()` owns the accumulator boundary. It clears once at group entry, retains OIDs across consecutive OOS items, consumes them at the following heap row, and then clears. `locator_oos_insert_force()` must not reset per item. The heap-row fixup must require exact OID cardinality, and any OOS-item failure invalidates the pending group rather than allowing the heap row to continue with an incomplete accumulator.

`oos_insert()` is the scalar public exception boundary used by `locator_oos_insert_force()`. It catches `std::bad_alloc` from physical/publication work, converts it to `ER_OUT_OF_VIRTUAL_MEMORY`, and never lets a C++ allocation exception escape into locator/log apply. This failure cleanup is not the master-side strict start reset: success preserves intentional apply accumulation, while failure invalidates the pending group.

## Verification ownership

The change includes a focused `.sql` testcase and `.answer` in the CUBRID testcase repository as required implementation artifacts. CTP owns conversion of that source to `.test`; the generated `.test` and master/slave dumps are retained as execution evidence rather than committed as hand-maintained sources. The case drives an ACTIVE master and STANDBY slave through mixed single-chunk/multi-chunk OOS INSERT, a second row that checks apply-accumulator reset between groups, and mixed OOS UPDATE. CTP's replicated flag barrier owns synchronization; the testcase does not use a guessed sleep. Generated `$HC_CHECK_FOR_DML` work compares complete logical rows without accepting a `.master.slave1.diff_1` exception.

This real HA test proves the end-to-end replication and slave-local OOS fixup path. Focused SERVER_MODE tests separately prove master OID/LSA pairing and malformed apply-group rejection because SQL cannot directly observe publication queues or safely manufacture insufficient/extra accumulated OIDs.

The two-node HA run is a mandatory completion gate. If the environment or package is unavailable, the change remains incomplete; local CTests, SERVER_MODE tests, and ordinary SQL regression cannot waive the missing copylogdb/applylogdb evidence.

The focused gate ends after the ACTIVE master changes are visible and byte-equal on the STANDBY slave. It does not promote the slave: failover would add heartbeat, role-transition, broker-routing, and recovery concerns that do not strengthen evidence for the replication-apply accumulator defect. Promotion coverage belongs to a separate HA role-transition testcase.

OOS VFID lookup/create failure is also mandatory negative coverage. A `CUBRID_UNIT_TEST_ENABLED` one-shot hook fires in the heap OOS insertion wrapper after real class lookup and immediately before `heap_oos_find_vfid(..., true)`. It is scoped there rather than inside the shared VFID helper, automatically disarms, and proves the logical-start reset preceded the VFID boundary. Difficulty reproducing a physical file-creation failure is not grounds to omit this test.

## Remarks

Reviewer focus:

- Confirm that each logical OOS attribute publishes exactly one real head OID, with the existing dummy marker only for multi-chunk replication boundaries.
- Confirm that the logical heap OOS insert-preparation boundary clears both publication containers before its first fallible preparation step and that no downstream helper redundantly clears successful state.
- Confirm that batch failure clears partial publication and scalar failure invalidates the pending apply accumulator, with neither API leaking `std::bad_alloc`.
- Confirm that the committed SQL testcase passes its normal `.answer`, that CTP's generated HA testcase passes without a diff allowance, core, or fatal log, and that negative cardinality cases remain covered below SQL level.
