[Start here: short English guide](start-here.en.md) · [먼저 읽기: 한국어 안내](start-here.ko.html)

# PR #7600 — route the row before choosing its OOS owner

## Reading map

This guide explains the committed diff at `479cd960ec04196c92bf9789b1fc340af9046c2c` against base and merge-base `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` (`feat/oos`). It covers 10 files, 2,003 additions, 101 deletions and 63 diff hunks. The source checkout has an existing CCI dependency difference and untracked learning materials; those are not part of the committed diff.

Start with the ownership example, follow the effective key through routing and transformation, then use the annotated diff to answer questions about individual changes. The four-view walkthrough is a presentation aid; the visual diff page and its English Markdown contain the detailed explanations.

Evidence labels matter. **Source** means the pinned code directly supports a statement. **Historical execution** means an earlier recorded run, with its own revision and environment. **Rationale** means either a documented decision or an explicitly identified inference. **Open** means the available evidence does not establish the result. No engine tests were executed to create these pages; browser checks validate the artifacts, not database behavior.

## The failure that motivates the change

An OOS-backed attribute stores a small inline stub in the heap record and its serialized value in an OOS value chain. A heap has at most one OOS file; the heap header records its VFID. The partition root and each child have distinct heap identities. Correctness therefore requires the OOS file chosen during transformation to belong to the heap that ultimately receives the record.

The old locator order was **transform the row → route the record → insert into the selected child**. Transformation could already call `heap_attrinfo_insert_to_oos` using `attr_info->class_oid`. On a root-targeted INSERT that identity is the root. The later partition decision could put a record containing OOS inline stubs into `p0` while its value chains remained in the root's OOS file. [Source: base locator](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7695).

```sql
CREATE TABLE t_oos_show_part (
  id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE
) PARTITION BY RANGE (id) (
  PARTITION p0 VALUES LESS THAN (10),
  PARTITION p1 VALUES LESS THAN MAXVALUE
);
INSERT INTO t_oos_show_part VALUES (1, REPEAT(X'EE', 64));
COMMIT;
SELECT data_col = CAST(REPEAT(X'EE', 64) AS BIT VARYING)
  FROM t_oos_show_part WHERE id = 1;
SHOW ALL HEAP OOS OF t_oos_show_part;
```

The logical comparison is insufficient: reads can follow the head OOS OID in the stub. The physical assertion is root: no OOS file / zero chunks; `p0`: OOS file / one chunk; `p1`: no OOS file / zero chunks. This is the oracle encoded by `PartitionedForceOutlineStoresOosInPrunedHeap`, not a fresh execution claim. The 64-byte forced value exposes the bug even below the ordinary record-size trigger. [Source: test](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L437).

Vacuum starts from the heap being reclaimed and asks for that heap's OOS VFID. In this revision, `vacuum_oos_find_vfid_for_heap_record` contains an explicit `abort()` when a HAS_OOS record's heap has no OOS file. Its surrounding prose discusses a graceful skip, but the executable code aborts first. Removing that diagnostic would not repair ownership. [Source: vacuum](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/vacuum_oos.cpp#L401).

## Vocabulary and revision boundaries

| Name | Meaning in this review |
|---|---|
| Source class | Identity used to interpret assignments, old representations and existing LOB preparation. It must remain available during a moving UPDATE. |
| Destination class | Partition selected for the new row; used to select the OOS owner. |
| HFID / VFID / OID | Heap identifier / logical file identifier / object address. They answer different ownership and addressing questions. |
| Effective key | Owned copy equivalent to the partition key the normal row serializer will store, including applicable default, old value, pending increment and scalar codec effects. |
| Resolve | Reading an OOS-backed attribute's logical value. It may perform I/O. Early routing is not an I/O-free promise. |
| Probe image | Fully inline temporary record used for key extraction. OOS suppression prevents OOS writes; it does not suppress every DB_VALUE or LOB side effect. |
| HAS_OOS | Record metadata indicating OOS inline stubs; it does not by itself prove correct physical ownership. |

The checked-out `OR_OOS_INLINE_SIZE` is `OR_OID_SIZE + OR_BIGINT_SIZE`, or 16 bytes. The normative OOS context describes an accepted 24-byte identity-stamp design associated with a separate change. PR #7600 does not introduce that layout. Do not transfer newer specification details into this source walkthrough. [Source: inline size](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/base/object_representation.h#L466).

## The current end-to-end path

`locator_attribute_info_force` first obtains the supplied/locked old record for UPDATE. It then routes partitioned INSERT/UPDATE through `partition_prune_insert_by_attrinfo` or `partition_prune_update_by_attrinfo`. Only after successful selection does it perform a normal first-pass full-row transform with `write_destination` as the OOS owner. Finally, the normal force path routes the serialized record again, validates the destination and performs heap/index work. Nonpartitioned calls retain normal transformation. [Source: orchestration](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7655).

There are **two routing evaluations but one full-row transformation** on this main path, subject to the transformer's existing buffer-growth retries. This is different from the older full-inline-probe plus full-row-rebuild implementation described in the PR body and JIRA text. The accepted effective-key ADR explains the reason: remove redundant whole-row work while keeping the stateful LOB preparation boundary intact. The scope includes all supported partition-key types on this path rather than a hidden type-based fallback. [Decision: ADR](https://github.com/vimkim/my-cubrid-docs/blob/08870b103aea34148f08bb9e5d9d9c496d4a4e11/docs/adr/0001-pr7600-effective-key-routing.md).

## Preparing the effective key, line by line

The central new helper is `heap_attrinfo_get_effective_key`. Its output is initially NULL and owned by the caller. It does not prepare the entire row. [Source: helper](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12115).

| Lines in heap_file.c | Operation and necessity |
|---|---|
| 12119–12137 | Declare the prepared DB_VALUE, aligned 64-byte scratch storage and optional allocation; require a NULL output and locate the source slot. This makes ownership and cleanup explicit. |
| 12138–12153 | If the slot is uninitialized and an old record is available, create an independent one-key reader, read the supplied old representation, clone the result and end the temporary reader. An unchanged UPDATE key must come from the old row, not the current default. |
| 12154–12164 | For an omitted INSERT key, shallow-copy attribute metadata but initialize a separate DB_VALUE; use the existing default reader and clone the result. This leaves the assignment slot uninitialized for the real transform. |
| 12165–12172 | Otherwise clone the assigned/read value, then check errors before continuing. No ownership is borrowed into the final key. |
| 12173–12180 | Apply a pending increment to the owned prepared copy. The real source slot still carries its original value and pending operation. Repeated routing cannot consume the increment. |
| 12181–12185 | Preserve NULL directly; partition evaluation handles NULL with its existing NULL-specific operation. |
| 12187–12203 | Obtain the scalar codec from the attribute domain, size the prepared value, reject invalid sizes and allocate only when it exceeds the scratch capacity. The scratch buffer is a small-key allocation optimization, not a row-size limit. |
| 12204–12211 | Write then read the scalar using the domain and copy semantics. This reproduces stored-value effects such as CHAR padding on the owned copy; simply cloning the pre-storage value is insufficient. |
| 12213–12224 | Clear the prepared value, free optional storage and clear a partially produced output on failure. The caller receives either an owned usable key or a cleared error result. |

Tests compare candidate routing with an independent reference attrinfo transformed through the retained inline probe. Separate values are essential because the reference path can initialize and mutate its own assignments.

## Binding and evaluating the partition expression

`partition_start_key_attrinfo` initializes the pruning context's one-key attrinfo once and binds the expression to that stable slot. `partition_find_partition_for_attrinfo` clears a prior value before filling the slot; a duplicate-key probe may have left a value in the same context. It marks the slot readable, obtains the effective key, evaluates the expression, copies destination OID/HFID on success, and clears the temporary values on exit. The expression binding itself survives successful context reuse. [Source: context and key binding](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3548).

`partition_find_partition_for_expr` is extracted from the old record router. Both routes use the same expression evaluation, NULL handling and partition matching. It requires exactly one result and returns a borrowed `OR_PARTITION` owned by the context. Record decoding and representation rewriting remain in `partition_find_partition_for_record`; the new key route does neither. This separation explains the deleted lines: most were moved into the record adapter, not removed from final routing. [Source: evaluator](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3479).

Shared INSERT/UPDATE internals retain the existing context-lifetime and explicit-partition validation contracts. A root-targeted update can move across children, while a statement explicitly targeting a child must reject a key outside that child. UPDATE without a supplied context discovers the partition root from the source child; a supplied UPDATE context is expected to be loaded. [Source: shared wrappers](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3698).

## Selecting the OOS owner without changing source identity

`heap_attrinfo_transform_to_disk_with_oos_owner` invokes the common transformer with a destination OID, no suppression output, and `increments_already_applied=false`. The transformer still initializes the source row, plans demotion, rejects unsupported OOS-plus-bigone records before OOS writes, serializes OOS payloads, and builds the final record. [Source: owner wrapper](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12927).

Only the call to `heap_oos_insert_serialized_values` substitutes the destination class for the source class. That existing helper resolves class → HFID → OOS VFID and calls `oos_insert_many`. Payload serialization and LOB locator handling still use source attrinfo. This distinction is why assigning `attr_info->class_oid = destination` would be a broader semantic change. [Source: owner substitution](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12885), [unchanged storage boundary](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_oos.cpp#L631).

For a moving UPDATE, final record routing patches the representation ID for the destination. `locator_update_force` retains/reacquires the actual source identity and calls `locator_move_record` only if the source and destination differ. The existing move helper inserts the destination record first and then deletes the source record. Transactional error handling must cover partial progress. [Source: move](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5402).

## Why final routing and its agreement check remain

Early routing chooses where OOS values may be written. Final routing remains responsible for the serialized record, representation patching, partition validation and integration with existing force behavior. INSERT and UPDATE now receive an optional `expected_class_oid`; after final pruning, a different selected OID causes `ER_GENERIC_ERROR` before the subsequent destination heap/index mutation. Silently redirecting a record after its OOS chains were written would recreate the ownership error. [Source: INSERT check](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L4996), [UPDATE check](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6021).

This is an error propagation boundary, not an immediate local rollback routine. OOS writes can already exist; cleanup depends on the existing statement/transaction rollback machinery. The SQL failure tests explicitly abort before inspecting restored physical counts. They demonstrate that tested abort path, not every possible caller's automatic statement rollback. Legacy callers pass NULL and retain their prior behavior.

## Probes, forced outline, increments and LOBs

REPLACE and ON DUPLICATE KEY UPDATE create temporary records for unique-key searches. Those records are never inserted. Passing a non-NULL `probe_would_demote_oos` pointer selects suppression mode; the pointer's presence matters even when its initial Boolean value is false. The probe can report would-demote while leaving `has_oos=false` and all values inline. [Source: duplicate probes](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L11955).

Suppression must cover both demotion entry points. FORCE_OUTLINE is handled before the ordinary size-triggered candidate loop. The new check sets the verdict and continues without selecting a column; the ordinary path returns the fully inline size before demotion. Covering only the ordinary path leaks chains for small forced values. [Source: forced policy](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12469).

The old second-pass `heap_attrinfo_transform_to_disk_oos_class` API remains: it premarks pending increments as already applied. Current main writes use the first-pass owner wrapper instead. The retained probe is still useful for duplicate lookup and independent test reference routing. A source scan found no production call supplying a non-NULL owner to the public copy-area wrapper; its rebuild branch is retained API/state rather than the active main path. This matches an optional cleanup suggestion in the existing review.

On the main path, early key preparation changes only its copy; the normal fixed-column writer performs the real INCR/DECR once and remembers it across buffer retries. Existing LOB writers use `HEAP_WRITTEN_LOB_ATTRVALUE` to avoid duplicate ELO copies. OOS suppression is not a universal side-effect-free contract: the probe still uses those normal writers and the caller's LOB flag. REPLACE excludes LOB copying, while the ODKU probe retains INCLUDE_LOB. [Source: increment guard](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L13131), [LOB preparation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12692).

## Tests, confidence and open acceptance

The SQL file adds 28 tests to four existing tests. The appendix explains each test's setup, discriminating observation and limit. Direct routing tests use `scoped_sa_server` so server interfaces use the correct allocation context in standalone execution. The test timeout becomes 300 seconds because injected failures and rejection cases collect diagnostic stacks in debug builds; this is not evidence of a performance improvement.

The previously published review records **32/32 SQL tests passing at 988a4d2**, with a local CCI mismatch. HEAD 479cd960 changes the vacuum test file by retaining the rollback regression with a `DISABLED_` prefix; the SQL and production source files are unchanged from that reviewed parent. This is useful provenance, not a fresh exact-environment certification. [Historical execution](https://github.com/vimkim/my-cubrid-docs/blob/08870b103aea34148f08bb9e5d9d9c496d4a4e11/cbrd-27089/review-988a4d2-codex/verification.md).

The disabled test creates a committed original value and a separate committed-delete witness, performs an UPDATE then rollback, confirms the original before vacuum, waits until the witness proves actual vacuum progress, and rereads the original. Historical execution failed at the final readback. The witness prevents a daemon wakeup from masquerading as successful reclamation. The test is lower-layer and not partition-specific. The existing review relates it to CBRD-27237; the vacuum implementation is unchanged by this PR. Disabling it preserves a reproducer but does not close the lifecycle gate. [Source: disabled regression](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/test_oos_real_vacuum_server.cpp#L828).

The fetched PR discussion contains six CI trigger comments and one substantive review summary, with no inline comments or top-level review records. That summary leaves three acceptance gates open: full SERVER_MODE lifecycle coverage, control-workload performance acceptance, and final integrated evidence. No fresh CI conclusion is claimed here. [Existing review](https://github.com/CUBRID/cubrid/pull/7600#issuecomment-5599750448).

**Review recommendation:** explain the routing/ownership mechanism using the evidence here, and keep acceptance conditional on those open gates. Neither a useful presentation nor a passing standalone suite establishes complete MVCC, vacuum, crash, concurrency or performance safety. The accepted ADR also allows error precedence to differ for multiply-invalid statements; single-failure behavior and cleanup remain obligations.

## Questions to rehearse

1. Why could SELECT return the right value while vacuum aborts? Contrast OID-based reading with heap-based file discovery.
2. Why isn't a raw assignment DB_VALUE sufficient for routing? Explain omitted/default and CHAR codec cases.
3. Why clone the key before applying INCR? Predict what a second routing call would do if it mutated the source.
4. Why preserve the source class during a move? Trace old representation and LOB preparation separately from OOS destination selection.
5. Why route again after serializing? Explain final representation patching and the disagreement guard.
6. Does returning an error reclaim every OOS chunk immediately? Identify the caller/transaction rollback dependency.
7. Why does a 64-byte forced value matter? Locate the policy loop that precedes the ordinary size gate.
8. Which tests prove physical owner placement? Explain why logical row counts alone are weak.
9. What does the disabled vacuum test prove today? Its code specifies the oracle; its disabled state proves no runtime success.
10. What is the performance trade-off? Whole-row probe work is removed, scalar preparation and duplicate final routing remain, and measured acceptance is unresolved.

## Added SQL test catalog

These are source-level test contracts. The recorded 32/32 result is historical, not a run performed for this report.

### T01 — PartitionedForceOutlineStoresOosInPrunedHeap

[Source 437–504](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L437). Force a 64-byte value; verify value equality and root/p0/p1 ownership (0/1/0 chunks). Small forced data isolates policy from the ordinary size gate.

### T02 — PartitionRangeBoundaryAndNullOwnership

[Source 506–529](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L506). Alternate keys 10, 9, 11 and NULL in one INSERT; assert both boundary placement and per-child two-chunk totals. Reused routing state must not leak between rows.

### T03 — PartitionListExpressionAndFailedBatchOwnership

[Source 531–565](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L531). Route ABS(id) over LIST partitions, fail a batch after a valid first row, explicitly abort, then insert again. Check original values, ownership and successful recovery of reusable state.

### T04 — PartitionHashNullOwnership

[Source 567–587](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L567). Exercise HASH with repeated keys and NULL; verify known p0/p1 placements and owner counts. This tests the existing hash rule for the chosen integers, not a general hash formula.

### T05 — PartitionRangeExpressionValidationAndMovement

[Source 589–630](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L589). Use RANGE(id+1), reject a missing destination and explicit-child mismatch for INSERT/UPDATE, then perform a root-targeted move. Error codes and unchanged pre-error data discriminate the contracts.

### T06 — PartitionListRejectsNullWithoutDestination

[Source 632–655](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L632). A LIST with no NULL destination rejects NULL before publishing any OOS file; a subsequent valid write creates only p1's file.

### T07 — PartitionUpdatePreservesDuplicateProbesAndNonKeyIncrement

[Source 657–675](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L657). Combine non-key INCR, ODKU moving id=11 to 9 and REPLACE. Assert final values and no root OOS file. This does not enumerate every probe-side child orphan or SERVER_MODE lifecycle case.

### T08 — PartitionUpdateStringDomains

[Source 677–699](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L677). Update case-insensitive VARCHAR keys and compressed expression keys across a length boundary. Check the logical key and owner, with only forced payload OOS in the DEFAULT-policy compressed-key case.

### T09 — PartitionUpdateLegalKeysAndNullMovement

[Source 701–746](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L701). Loop 13 supported key specifications through default INSERT, unchanged-key UPDATE, NULL movement, reassignment and rollback. Explicit padded CHAR bounds distinguish stored-domain behavior.

### T10 — PartitionUpdateOldOosKeyAndRepresentation

[Source 748–772](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L748). Use an OOS-backed string key, add a schema column, update payload then move key and abort. Check inherited default and multi-payload preservation across representation change.

### T11 — PartitionUpdateLobLifecycle

[Source 774–795](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L774). Move a row containing inline CLOB and forced BLOB locator, then change both LOBs and abort. Read external LOB contents and count two OOS chunks at destination; locator storage is distinct from external payload storage.

### T12 — PartitionUpdateDedicatedIncrementsAndArithmetic

[Source 797–844](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L797). Test INCR/DECR and ordinary arithmetic for SMALLINT/INT/BIGINT, including extrema where the dedicated increment behavior resets to zero. Ensure the same key used for routing is eventually stored.

### T13 — EffectiveUpdateRouteUsesMissingHistoricalKeyDefault

[Source 846–913](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L846). Construct old serialized bytes before adding the key, then route an unchanged UPDATE using the missing-attribute default. Compare with an independent inline reference; no actual heap row is installed, isolating representation decoding from ALTER redistribution.

### T14 — EffectiveUpdateRoutePreservesOldKeyAndPendingIncrement

[Source 915–1000](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L915). Prepare old key 10 and test unchanged, pending +1, pending -1 and assigned 9. Assert source state/representation/increment remain unchanged after repeated routing, then assert the real transform applies once and final OID/HFID agrees.

### T15 — PartitionPreparationFailuresRollBackAndAllowNextWrite

[Source 1002–1068](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1002). Inject failures after one publication, after publication reset, before VFID lookup and during OID publication allocation, for INSERT and moving UPDATE. Disarm hooks, abort, check committed values/counts and retry successfully. Multi-chunk payload prevents a single small batch hiding partial progress.

### T16 — PartitionLobPreparationAndIndexFailuresPreserveCommittedValues

[Source 1070–1111](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1070). Fail LOB preparation before VFID lookup and fail a moving update on a unique key, with/without new LOB assignments. Abort and verify committed LOB contents and OOS counts, then prove a new write works.

### T17 — EffectiveKeyCodecFailureClearsOutputAndPreservesAssignment

[Source 1113–1203](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1113). Swap in a failing scalar codec on private attribute/domain copies only. Fail write and partial read; expect a NULL output and unchanged source assignment, restore the codec and retry. It avoids mutating cached shared schema.

### T18 — EffectiveRoutingFailurePreservesAssignmentsAndPublication

[Source 1205–1272](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1205). Seed OID/LSA publication containers and alternate valid/missing destinations in one pruning context. Assert routing preserves source assignments and both markers; reset test markers on exit. These are preparation-state assertions, not durability tests.

### T19 — EffectiveInsertRoutePreservesOmittedAssignments

[Source 1274–1340](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1274). Route an omitted CHAR default before any full transform; all candidate slots remain uninitialized and NULL. A separate reference transform must select the same expected child and HFID, without any OOS files.

### T20 — EffectiveInsertRoutePreservesAssignedChar

[Source 1342–1417](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1342). Assign an unpadded CHAR value and snapshot its bytes/state. Early routing must match a separately serialized reference while preserving those original bytes and the untouched payload slot.

### T21 — EffectiveInsertRouteLegalKeyDefaults

[Source 1419–1496](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1419). Compare effective INSERT routing with an independent serialized reference across 13 default key types. Check source slots stay uninitialized and no root/child OOS publication occurs.

### T22 — PartitionInsertLegalKeySqlMatrix

[Source 1498–1546](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1498). Execute assigned, NULL and omitted/default INSERTs across 13 types using HASH. Validate logical data, per-child row/chunk correspondence, and print literal partition results for a separate reference run; this test alone is not that separate run.

### T23 — PartitionInsertOwnsExternalKeyAndMultiplePayloads

[Source 1548–1573](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1548). Insert an externalized expression key plus forced small and ordinary large VARBIT payloads into both children. Three single-chunk values per row make the expected physical count exactly three per child.

### T24 — PartitionInsertRetainsBigoneRejectionBeforeOos

[Source 1575–1593](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1575). Force OOS beside BIT(140000), expect the exact bigone rejection and zero OOS files after abort, then prove the non-OOS whole-record overflow case remains valid with NULL payload.

### T25 — PartitionInsertGeneratedKeysAndDomainConversion

[Source 1595–1611](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1595). AUTO_INCREMENT produces 9 then 10 across a range boundary; string input '11' is converted to integer. Check values and owner counts 1/2 in the children.

### T26 — PartitionInsertDynamicDefault

[Source 1613–1630](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1613). A CURRENT_DATE default is compared against an explicit CURRENT_DATE captured in the same INSERT. Assert logical equality and physical ownership rather than hard-coding today's date or hash destination.

### T27 — PartitionInsertUsesColumnCollation

[Source 1632–1647](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1632). Mix 'BETA', 'AlPhA' and 'beta' with utf8_en_ci LIST partitions. Case-insensitive routing must preserve payload identity and per-child chunk totals.

### T28 — PartitionInsertCompressedExpressionKey

[Source 1649–1664](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1649). Use forced compressed VARCHAR expression keys at lengths 2999/3000, plus forced payloads. Assert both value equality and two OOS chunks in each selected child.


## Complete annotated diff

Each H-number corresponds to one unified diff hunk, with its old/new source intervals. Deleted lines are included. Rationale is grounded in the linked code and accepted decision; this is not an assertion of private author intent.

### H01 — Declare routing seams

[src/query/partition.c old:155 / new:155](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R155)

Declare the extracted evaluator, stable-key initializer and shared INSERT implementation before use. These are internal seams; the public entry points are declared separately in partition_sr.h.

```diff
@@ -155,6 +155,13 @@ static MATCH_STATUS partition_prune_list (PRUNING_CONTEXT * pinfo, const DB_VALU
 					  PRUNING_BITSET * pruned);
 static MATCH_STATUS partition_prune_hash (PRUNING_CONTEXT * pinfo, const DB_VALUE * val, const PRUNING_OP op,
 					  PRUNING_BITSET * pruned);
+static int partition_find_partition_for_expr (THREAD_ENTRY * thread_p, PRUNING_CONTEXT * pinfo, const OID * class_oid,
+					      OR_PARTITION ** partition);
+static int partition_start_key_attrinfo (THREAD_ENTRY * thread_p, PRUNING_CONTEXT * pinfo);
+static int partition_prune_insert_internal (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES * recdes,
+					    HEAP_CACHE_ATTRINFO * attr_info, PRUNING_CONTEXT * pcontext,
+					    int pruning_type, OID * pruned_class_oid, HFID * pruned_hfid,
+					    OID * superclass_oid);
 static int partition_find_partition_for_record (PRUNING_CONTEXT * pinfo, const OID * class_oid, RECDES * recdes,
 						OID * partition_oid, HFID * partition_hfid);
 #if defined (ENABLE_UNUSED_FUNCTION)
```

### H02 — Separate evaluation from record decoding

[src/query/partition.c old:3454 / new:3461](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3461)

Rename the core to partition_find_partition_for_expr, accept an explicit thread and borrowed destination output, and remove decoding from this function. Decoding is relocated to the record adapter in H05. The evaluator can now consume either an effective key or a decoded record key without duplicating partition semantics.

```diff
@@ -3454,64 +3461,42 @@ error_exit:
 }
 
 /*
- * partition_find_partition_for_record () - find the partition in which a
- *					    record should be placed
+ * partition_find_partition_for_expr () - evaluate the bound partition expression
+ *                                       and find its single destination
  * return : error code or NO_ERROR
- * pinfo (in)	  : pruning context
- * class_oid (in) : OID of the root class
- * recdes (in)	  : record descriptor
- * partition_oid (in/out) : OID of the partition in which the record fits
- * partition_hfid (in/out): HFID of the partition in which the record fits
+ * thread_p (in) : thread entry from the pruning context
+ * pinfo (in/out) : loaded pruning context with a bound, readable key value
+ * class_oid (in) : class OID used for expression evaluation
+ * partition (out) : borrowed destination, valid until the context is cleared;
+ *                   written only on success
+ *
+ * The caller owns the bound attributes and their values, and supplies the
+ * evaluation instance OID in pinfo->attr_info.inst_oid. Evaluation may populate
+ * expression caches; it does not transfer ownership or clear values. Record
+ * decoding, representation changes and explicit-partition validation belong
+ * to callers.
  */
 static int
-partition_find_partition_for_record (PRUNING_CONTEXT * pinfo, const OID * class_oid, RECDES * recdes,
-				     OID * partition_oid, HFID * partition_hfid)
+partition_find_partition_for_expr (THREAD_ENTRY * thread_p, PRUNING_CONTEXT * pinfo, const OID * class_oid,
+				   OR_PARTITION ** partition)
 {
   PRUNING_BITSET pruned;
   PRUNING_BITSET_ITERATOR it;
-  bool clear_dbvalues = false;
   DB_VALUE *result = NULL;
   MATCH_STATUS status = MATCH_NOT_FOUND;
   int error = NO_ERROR, count = 0, pos;
   PRUNING_OP op = PO_EQ;
-  REPR_ID repr_id = NULL_REPRID;
 
-  assert (partition_oid != NULL);
-  assert (partition_hfid != NULL);
+  assert (partition != NULL);
 
   pruningset_init (&pruned, PARTITIONS_COUNT (pinfo));
 
-  if (pinfo->is_attr_info_inited == false)
-    {
-      error = heap_attrinfo_start (pinfo->thread_p, &pinfo->root_oid, 1, &pinfo->attr_id, &pinfo->attr_info);
-      if (error != NO_ERROR)
-	{
-	  goto cleanup;
-	}
-
-      partition_set_cache_info_for_expr (pinfo->partition_pred->func_regu, pinfo->attr_id, &pinfo->attr_info);
-      pinfo->is_attr_info_inited = true;
-    }
-
-  /* set root representation id to the recdes so that we can read the value as belonging to the partitioned table */
-  repr_id = or_rep_id (recdes);
-  or_set_rep_id (recdes, pinfo->root_repr_id);
-
-  error = heap_attrinfo_read_dbvalues (pinfo->thread_p, &pinfo->attr_info.inst_oid, recdes, &pinfo->attr_info);
-
-  or_set_rep_id (recdes, repr_id);
-  if (error != NO_ERROR)
-    {
-      goto cleanup;
-    }
-  clear_dbvalues = true;
-
   error =
-    fetch_peek_dbval (pinfo->thread_p, pinfo->partition_pred->func_regu, NULL, (OID *) class_oid,
+    fetch_peek_dbval (thread_p, pinfo->partition_pred->func_regu, NULL, (OID *) class_oid,
 		      &pinfo->attr_info.inst_oid, NULL, &result);
   if (error != NO_ERROR)
     {
-      goto cleanup;
+      return error;
     }
 
   assert (result != NULL);
```

### H03 — Return missing-partition errors directly

[src/query/partition.c old:3527 / new:3512](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3512)

The evaluator no longer owns temporary record DB_VALUE cleanup. Return ER_PARTITION_NOT_EXIST directly on failed matching; the adapter that owns the key handles cleanup.

```diff
@@ -3527,8 +3512,7 @@ partition_find_partition_for_record (PRUNING_CONTEXT * pinfo, const OID * class_
   if (status != MATCH_OK)
     {
       er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_PARTITION_NOT_EXIST, 0);
-      error = ER_PARTITION_NOT_EXIST;
-      goto cleanup;
+      return ER_PARTITION_NOT_EXIST;
     }
 
   if (count != 1)
```

### H04 — Preserve the non-single-result error

[src/query/partition.c old:3546 / new:3530](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3530)

Keep the original no-destination/internal-error choice, replacing a cleanup jump with a direct return. This does not relax the requirement for exactly one destination.

```diff
@@ -3546,7 +3530,7 @@ partition_find_partition_for_record (PRUNING_CONTEXT * pinfo, const OID * class_
 	  /* This is an internal *error (allocation, etc). Error was set by the calls above, just set *error code */
 	  error = pinfo->error_code;
 	}
-      goto cleanup;
+      return error;
     }
 
   pruningset_iterator_init (&pruned, &it);
```

### H05 — Stable key slot and two adapters

[src/query/partition.c old:3554 / new:3538](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3538)

Return the context-owned OR_PARTITION, then add a reusable one-key slot and the attrinfo adapter. Clear stale key values before evaluation, mark the slot readable, prepare only the owned effective key, copy OID/HFID only after success and clear it on exit. Reintroduce the old record adapter: decode under root representation, restore the original ID, evaluate using the shared core, and retain destination representation patching.

```diff
@@ -3554,8 +3538,121 @@ partition_find_partition_for_record (PRUNING_CONTEXT * pinfo, const OID * class_
   pos = pruningset_iterator_next (&it);
   assert_release (pos >= 0);
 
-  COPY_OID (partition_oid, &pinfo->partitions[pos + 1].class_oid);
-  HFID_COPY (partition_hfid, &pinfo->partitions[pos + 1].class_hfid);
+  *partition = &pinfo->partitions[pos + 1];
+  return NO_ERROR;
+}
+
+/*
+ * partition_start_key_attrinfo () - bind the expression to the context-owned key slot
+ */
+static int
+partition_start_key_attrinfo (THREAD_ENTRY * thread_p, PRUNING_CONTEXT * pinfo)
+{
+  int error;
+
+  if (!pinfo->is_attr_info_inited)
+    {
+      error = heap_attrinfo_start (thread_p, &pinfo->root_oid, 1, &pinfo->attr_id, &pinfo->attr_info);
+      if (error != NO_ERROR)
+	{
+	  return error;
+	}
+      partition_set_cache_info_for_expr (pinfo->partition_pred->func_regu, pinfo->attr_id, &pinfo->attr_info);
+      pinfo->is_attr_info_inited = true;
+    }
+  return NO_ERROR;
+}
+
+/*
+ * partition_find_partition_for_attrinfo () - route one effective key without preparing the source row
+ */
+static int
+partition_find_partition_for_attrinfo (THREAD_ENTRY * thread_p, PRUNING_CONTEXT * pcontext, const OID * class_oid,
+				       HEAP_CACHE_ATTRINFO * attr_info, RECDES * old_recdes,
+				       OID * pruned_class_oid, HFID * pruned_hfid)
+{
+  int error = partition_start_key_attrinfo (thread_p, pcontext);
+  if (error != NO_ERROR)
+    {
+      return error;
+    }
+
+  /* Expression bindings must use the existing stable slot, not a stack DB_VALUE. */
+  HEAP_ATTRVALUE *key = &pcontext->attr_info.values[0];
+  OR_PARTITION *partition = NULL;
+  assert (pcontext->attr_info.num_values == 1 && key->attrid == pcontext->attr_id);
+  /* A duplicate-key index probe can leave its key in this same context. Retain the slot/bindings,
+   * but release that previous value before preparing this write's key. Source assignments are separate. */
+  assert (attr_info != &pcontext->attr_info);
+  error = heap_attrinfo_clear_dbvalues (&pcontext->attr_info);
+  if (error != NO_ERROR)
+    {
+      return error;
+    }
+  key->state = HEAP_READ_ATTRVALUE;
+  error = heap_attrinfo_get_effective_key (thread_p, attr_info, pcontext->attr_id, old_recdes, &key->dbvalue);
+  if (error == NO_ERROR)
+    {
+      error = partition_find_partition_for_expr (thread_p, pcontext, class_oid, &partition);
+    }
+  if (error == NO_ERROR)
+    {
+      COPY_OID (pruned_class_oid, &partition->class_oid);
+      HFID_COPY (pruned_hfid, &partition->class_hfid);
+    }
+  heap_attrinfo_clear_dbvalues (&pcontext->attr_info);
+  return error;
+}
+
+/*
+ * partition_find_partition_for_record () - find the partition in which a
+ *                                        record should be placed
+ * return : error code or NO_ERROR
+ * pinfo (in)     : pruning context
+ * class_oid (in) : OID of the root class or the source partition
+ * recdes (in)    : record descriptor
+ * partition_oid (in/out) : OID of the partition in which the record fits
+ * partition_hfid (in/out): HFID of the partition in which the record fits
+ */
+static int
+partition_find_partition_for_record (PRUNING_CONTEXT * pinfo, const OID * class_oid, RECDES * recdes,
+				     OID * partition_oid, HFID * partition_hfid)
+{
+  bool clear_dbvalues = false;
+  int error = NO_ERROR;
+  REPR_ID repr_id = NULL_REPRID;
+  OR_PARTITION *partition = NULL;
+
+  assert (partition_oid != NULL);
+  assert (partition_hfid != NULL);
+
+  error = partition_start_key_attrinfo (pinfo->thread_p, pinfo);
+  if (error != NO_ERROR)
+    {
+      goto cleanup;
+    }
+
+  /* set root representation id to the recdes so that we can read the value as belonging to the partitioned table */
+  repr_id = or_rep_id (recdes);
+  or_set_rep_id (recdes, pinfo->root_repr_id);
+
+  error = heap_attrinfo_read_dbvalues (pinfo->thread_p, &pinfo->attr_info.inst_oid, recdes, &pinfo->attr_info);
+
+  or_set_rep_id (recdes, repr_id);
+  if (error != NO_ERROR)
+    {
+      goto cleanup;
+    }
+  clear_dbvalues = true;
+
+  error = partition_find_partition_for_expr (pinfo->thread_p, pinfo, class_oid, &partition);
+  if (error != NO_ERROR)
+    {
+      goto cleanup;
+    }
+
+  COPY_OID (partition_oid, &partition->class_oid);
+  HFID_COPY (partition_hfid, &partition->class_hfid);
 
   if (!OID_EQ (class_oid, partition_oid))
     {
```

### H06 — Use the returned partition representation

[src/query/partition.c old:3566 / new:3663](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3663)

Read rep_id from the returned partition instead of indexing with the evaluator's old local pos. The same selected descriptor supplies destination OID, HFID and representation ID.

```diff
@@ -3566,7 +3663,7 @@ partition_find_partition_for_record (PRUNING_CONTEXT * pinfo, const OID * class_
        * will be exactly the same. Because of this, we can take a shortcut here and only update the bits from the
        * representation id */
 
-      repr_id = pinfo->partitions[pos + 1].rep_id;
+      repr_id = partition->rep_id;
       error = or_set_rep_id (recdes, repr_id);
     }
 
```

### H07 — Document the dual INSERT input

[src/query/partition.c old:3580 / new:3677](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3677)

Rename the internal documentation and describe attr_info as an optional alternative to recdes. Remove the stale scan_cache parameter description because this internal function does not take it.

```diff
@@ -3580,12 +3677,12 @@ cleanup:
 }
 
 /*
- * partition_prune_insert () - perform pruning for insert
+ * partition_prune_insert_internal () - shared context and validation contract for INSERT routing
  * return : error code or NO_ERROR
  * thread_p (in)  : thread entry
  * class_oid (in) : OID of the root class
  * recdes (in)	  : Record describing the new object
- * scan_cache (in): Heap scan cache
+ * attr_info (in): source INSERT assignments, or NULL to route recdes instead
  * pcontext (in)  : pruning context
  * pruning_type (in) : pruning type
  * pruned_class_oid (in/out) : partition to insert into
```

### H08 — Share INSERT context management

[src/query/partition.c old:3601 / new:3698](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3698)

Make the implementation private and accept both recdes and attr_info. Public wrappers choose one; context loading, validation and cleanup remain shared.

```diff
@@ -3601,10 +3698,10 @@ cleanup:
  * partition_init_pruning_context) and pass it to this function for each
  * insert operation in the query.
  */
-int
-partition_prune_insert (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES * recdes, HEAP_SCANCACHE * scan_cache,
-			PRUNING_CONTEXT * pcontext, int pruning_type, OID * pruned_class_oid, HFID * pruned_hfid,
-			OID * superclass_oid)
+static int
+partition_prune_insert_internal (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES * recdes,
+				 HEAP_CACHE_ATTRINFO * attr_info, PRUNING_CONTEXT * pcontext, int pruning_type,
+				 OID * pruned_class_oid, HFID * pruned_hfid, OID * superclass_oid)
 {
   PRUNING_CONTEXT pinfo;
   bool keep_pruning_context = false;
```

### H09 — Select the INSERT input adapter

[src/query/partition.c old:3657 / new:3754](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3754)

A non-NULL attr_info routes a key with old_recdes=NULL; otherwise use the record adapter. Both feed the same later explicit-partition validation and cleanup path.

```diff
@@ -3657,7 +3754,15 @@ partition_prune_insert (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES *
       goto cleanup;
     }
 
-  error = partition_find_partition_for_record (pcontext, class_oid, recdes, pruned_class_oid, pruned_hfid);
+  if (attr_info != NULL)
+    {
+      error = partition_find_partition_for_attrinfo (thread_p, pcontext, class_oid, attr_info, NULL,
+						     pruned_class_oid, pruned_hfid);
+    }
+  else
+    {
+      error = partition_find_partition_for_record (pcontext, class_oid, recdes, pruned_class_oid, pruned_hfid);
+    }
   if (error != NO_ERROR)
     {
       goto cleanup;
```

### H10 — Preserve public INSERT and expose early routing

[src/query/partition.c old:3689 / new:3794](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3794)

The original signature becomes a wrapper passing NULL attrinfo. The new by_attrinfo wrapper passes NULL recdes and asserts assignments exist. UPDATE documentation is also revised to distinguish supplied old row from final new row.

```diff
@@ -3689,11 +3794,41 @@ cleanup:
 }
 
 /*
- * partition_prune_update () - perform pruning on update statements
+ * partition_prune_insert () - route an already serialized INSERT record
+ */
+int
+partition_prune_insert (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES * recdes, HEAP_SCANCACHE * scan_cache,
+			PRUNING_CONTEXT * pcontext, int pruning_type, OID * pruned_class_oid, HFID * pruned_hfid,
+			OID * superclass_oid)
+{
+  return partition_prune_insert_internal (thread_p, class_oid, recdes, NULL, pcontext, pruning_type,
+					  pruned_class_oid, pruned_hfid, superclass_oid);
+}
+
+/*
+ * partition_prune_insert_by_attrinfo () - route an INSERT without changing its assignments
+ *
+ * Context ownership, explicit-partition validation and outputs match partition_prune_insert.
+ * The key is owned by the routing context and cleared before returning; source assignments,
+ * LOB objects, OOS publication and the record representation are untouched.
+ */
+int
+partition_prune_insert_by_attrinfo (THREAD_ENTRY * thread_p, const OID * class_oid, HEAP_CACHE_ATTRINFO * attr_info,
+				    PRUNING_CONTEXT * pcontext, int pruning_type, OID * pruned_class_oid,
+				    HFID * pruned_hfid, OID * superclass_oid)
+{
+  assert (attr_info != NULL);
+  return partition_prune_insert_internal (thread_p, class_oid, NULL, attr_info, pcontext, pruning_type,
+					  pruned_class_oid, pruned_hfid, superclass_oid);
+}
+
+/*
+ * partition_prune_update_internal () - shared context and validation contract for UPDATE routing
  * return : error code or NO_ERROR
  * thread_p (in)  : thread entry
  * class_oid (in) : OID of the root class
- * recdes (in)	  : Record describing the new object
+ * recdes (in)	  : new record for record routing, supplied old record for attribute routing
+ * attr_info (in): source UPDATE assignments, or NULL to route the new record
  * pcontext (in)  : pruning context
  * pruning_type (in) : pruning type
  * pruned_class_oid (in/out) : partition to insert into
```

### H11 — Share UPDATE context management

[src/query/partition.c old:3708 / new:3843](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3843)

Add optional attrinfo to a private UPDATE internal. Source-child to root discovery and the caller-owned context requirements remain in this common implementation.

```diff
@@ -3708,9 +3843,10 @@ cleanup:
  * caller should initialize a PRUNING_CONTEXT object (by calling
  * partition_init_pruning_context) and pass it to this function.
  */
-int
-partition_prune_update (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES * recdes, PRUNING_CONTEXT * pcontext,
-			int pruning_type, OID * pruned_class_oid, HFID * pruned_hfid, OID * superclass_oid)
+static int
+partition_prune_update_internal (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES * recdes,
+				 HEAP_CACHE_ATTRINFO * attr_info, PRUNING_CONTEXT * pcontext,
+				 int pruning_type, OID * pruned_class_oid, HFID * pruned_hfid, OID * superclass_oid)
 {
   PRUNING_CONTEXT pinfo;
   int error = NO_ERROR;
```

### H12 — Select the UPDATE input adapter

[src/query/partition.c old:3790 / new:3926](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3926)

In attrinfo mode, recdes is the supplied old row used for an unchanged key; in record mode it is the already serialized new row. Preserving this distinction avoids substituting current defaults for historical values.

```diff
@@ -3790,7 +3926,15 @@ partition_prune_update (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES *
       goto cleanup;
     }
 
-  error = partition_find_partition_for_record (pcontext, class_oid, recdes, pruned_class_oid, pruned_hfid);
+  if (attr_info != NULL)
+    {
+      error = partition_find_partition_for_attrinfo (thread_p, pcontext, class_oid, attr_info, recdes,
+						     pruned_class_oid, pruned_hfid);
+    }
+  else
+    {
+      error = partition_find_partition_for_record (pcontext, class_oid, recdes, pruned_class_oid, pruned_hfid);
+    }
   if (error != NO_ERROR)
     {
       goto cleanup;
```

### H13 — Expose early UPDATE without changing final route

[src/query/partition.c old:3823 / new:3967](https://github.com/CUBRID/cubrid/pull/7600/files#diff-46f188b77e6527d920b050934f1a39f2d606d402d0a573a5221aa7b79f5aac24R3967)

Keep the original UPDATE wrapper passing NULL attrinfo. Add by_attrinfo with explicit old_recdes. Both reuse validation and context lifetime; only the source of the key differs.

```diff
@@ -3823,6 +3967,30 @@ cleanup:
   return error;
 }
 
+/*
+ * partition_prune_update () - retain final record routing and representation patching
+ */
+int
+partition_prune_update (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES * recdes, PRUNING_CONTEXT * pcontext,
+			int pruning_type, OID * pruned_class_oid, HFID * pruned_hfid, OID * superclass_oid)
+{
+  return partition_prune_update_internal (thread_p, class_oid, recdes, NULL, pcontext, pruning_type,
+					  pruned_class_oid, pruned_hfid, superclass_oid);
+}
+
+/*
+ * partition_prune_update_by_attrinfo () - route assignments and the supplied old row without changing either
+ */
+int
+partition_prune_update_by_attrinfo (THREAD_ENTRY * thread_p, const OID * class_oid, HEAP_CACHE_ATTRINFO * attr_info,
+				    RECDES * old_recdes, PRUNING_CONTEXT * pcontext, int pruning_type,
+				    OID * pruned_class_oid, HFID * pruned_hfid, OID * superclass_oid)
+{
+  assert (attr_info != NULL);
+  return partition_prune_update_internal (thread_p, class_oid, old_recdes, attr_info, pcontext, pruning_type,
+					  pruned_class_oid, pruned_hfid, superclass_oid);
+}
+
 /*
  * partition_get_scancache () - get scan_cache for a partition
  * return : cached object or NULL
```

### H14 — Declare the early-routing APIs

[src/query/partition_sr.h old:119 / new:119](https://github.com/CUBRID/cubrid/pull/7600/files#diff-867d8cafbd04828c54bbe2f2bb3b25eaef8781ac2fb5fd4648c5139a2f5de245R119)

Expose INSERT and UPDATE by_attrinfo entry points to locator code; UPDATE includes the supplied old record. OID/HFID and optional superclass outputs match the existing routing interfaces.

```diff
@@ -119,6 +119,16 @@ extern int partition_prune_update (THREAD_ENTRY * thread_p, const OID * class_oi
 				   PRUNING_CONTEXT * pcontext, int pruning_type, OID * pruned_class_oid,
 				   HFID * pruned_hfid, OID * superclass_oid);
 
+extern int partition_prune_insert_by_attrinfo (THREAD_ENTRY * thread_p, const OID * class_oid,
+					       HEAP_CACHE_ATTRINFO * attr_info, PRUNING_CONTEXT * pcontext,
+					       int pruning_type, OID * pruned_class_oid, HFID * pruned_hfid,
+					       OID * superclass_oid);
+
+extern int partition_prune_update_by_attrinfo (THREAD_ENTRY * thread_p, const OID * class_oid,
+					       HEAP_CACHE_ATTRINFO * attr_info, RECDES * old_recdes,
+					       PRUNING_CONTEXT * pcontext, int pruning_type, OID * pruned_class_oid,
+					       HFID * pruned_hfid, OID * superclass_oid);
+
 extern int partition_prune_unique_btid (PRUNING_CONTEXT * pcontext, DB_VALUE * key, OID * class_oid, HFID * class_hfid,
 					BTID * btid);
 
```

### H15 — REPLACE probe mode storage

[src/query/query_executor.c old:11937 / new:11937](https://github.com/CUBRID/cubrid/pull/7600/files#diff-9bedce9f6f01d1dd366be206555b8f76561e570ccaba901b4cdda27cdc231768R11937)

Add a local Boolean whose address selects suppression. False is an initial verdict, not a request to disable suppression.

```diff
@@ -11937,6 +11937,7 @@ qexec_remove_duplicates_for_replace (THREAD_ENTRY * thread_p, HEAP_SCANCACHE * s
   OID class_oid, pruned_oid;
   BTID btid;
   bool is_global_index;
+  bool probe_would_demote_oos = false;
   HFID class_hfid, pruned_hfid;
   int local_op_type = SINGLE_ROW_DELETE;
   HEAP_SCANCACHE *local_scan_cache = NULL;
```

### H16 — Suppress REPLACE probe publication

[src/query/query_executor.c old:11951 / new:11952](https://github.com/CUBRID/cubrid/pull/7600/files#diff-9bedce9f6f01d1dd366be206555b8f76561e570ccaba901b4cdda27cdc231768R11952)

Pass NULL owner and a non-NULL verdict pointer when building the duplicate-search image. Preserve EXCLUDE_LOB. The image is never installed, so it must not create OOS chains.

```diff
@@ -11951,7 +11952,11 @@ qexec_remove_duplicates_for_replace (THREAD_ENTRY * thread_p, HEAP_SCANCACHE * s
       goto error_exit;
     }
 
-  copyarea = locator_allocate_copy_area_by_attr_info (thread_p, attr_info, NULL, &new_recdes, -1, LOB_FLAG_EXCLUDE_LOB);
+  /* This record image is only probed for duplicate keys, never inserted: suppress OOS demotion so
+   * no OOS value chain is written (and later orphaned) for it. */
+  copyarea =
+    locator_allocate_copy_area_by_attr_info (thread_p, attr_info, NULL, &new_recdes, -1, LOB_FLAG_EXCLUDE_LOB, NULL,
+					     &probe_would_demote_oos);
   if (copyarea == NULL)
     {
       goto error_exit;
```

### H17 — ODKU probe mode storage

[src/query/query_executor.c old:12170 / new:12175](https://github.com/CUBRID/cubrid/pull/7600/files#diff-9bedce9f6f01d1dd366be206555b8f76561e570ccaba901b4cdda27cdc231768R12175)

Add the corresponding verdict storage for duplicate-key UPDATE lookup. Mode is selected by pointer presence; the caller does not need the reported value afterward.

```diff
@@ -12170,6 +12175,7 @@ qexec_oid_of_duplicate_key_update (THREAD_ENTRY * thread_p, HEAP_SCANCACHE ** pr
   OID class_oid;
   HFID class_hfid;
   bool is_global_index = false;
+  bool probe_would_demote_oos = false;
   int local_op_type = SINGLE_ROW_UPDATE;
   BTREE_SEARCH r;
 
```

### H18 — Suppress ODKU probe publication

[src/query/query_executor.c old:12189 / new:12195](https://github.com/CUBRID/cubrid/pull/7600/files#diff-9bedce9f6f01d1dd366be206555b8f76561e570ccaba901b4cdda27cdc231768R12195)

Build the duplicate-key lookup image through suppression while retaining INCLUDE_LOB. This prevents OOS publication for the temporary image; it is not a promise of zero LOB preparation effects.

```diff
@@ -12189,7 +12195,11 @@ qexec_oid_of_duplicate_key_update (THREAD_ENTRY * thread_p, HEAP_SCANCACHE ** pr
       goto error_exit;
     }
 
-  copyarea = locator_allocate_copy_area_by_attr_info (thread_p, attr_info, NULL, &recdes, -1, LOB_FLAG_INCLUDE_LOB);
+  /* This record image is only probed for unique-index duplicates, never inserted: suppress OOS
+   * demotion so no OOS value chain is written (and later orphaned) for it. */
+  copyarea =
+    locator_allocate_copy_area_by_attr_info (thread_p, attr_info, NULL, &recdes, -1, LOB_FLAG_INCLUDE_LOB, NULL,
+					     &probe_would_demote_oos);
   if (copyarea == NULL)
     {
       goto error_exit;
```

### H19 — Extend layout planning contract

[src/storage/heap_file.c old:694 / new:694](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R694)

Thread suppress_oos and would_demote_oos through the private layout planner declaration. Actual placement and hypothetical demotion are distinct outputs.

```diff
@@ -694,9 +694,10 @@ struct heap_oos_column_plan
   DB_BIGINT length = 0;
 };
 static int heap_attrinfo_determine_disk_layout (HEAP_CACHE_ATTRINFO * attr_info, bool is_mvcc_class,
-						size_t * offset_size_ptr,
+						bool suppress_oos, size_t * offset_size_ptr,
 						std::vector<heap_oos_column_plan> * oos_plan,
-						bool * has_oos, size_t * inline_size_after_oos_ptr);
+						bool * has_oos, bool * would_demote_oos,
+						size_t * inline_size_after_oos_ptr);
 // *INDENT-ON*
 
 static void heap_attrvalue_point_fixed (RECDES * recdes, HEAP_CACHE_ATTRINFO * attr_info, OR_ATTRIBUTE * attrepr,
```

### H20 — Extend the common transform contract

[src/storage/heap_file.c old:782 / new:783](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R783)

Add destination owner, optional suppression output and second-pass increment state. Wrappers set these deliberately; default behavior must remain the normal first pass.

```diff
@@ -782,7 +783,8 @@ static SCAN_CODE heap_attrinfo_transform_columns_to_disk (THREAD_ENTRY * thread_
 
 static SCAN_CODE heap_attrinfo_transform_to_disk_internal (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
 							   RECDES * old_recdes, record_descriptor * new_recdes,
-							   int lob_create_flag);
+							   int lob_create_flag, const OID * oos_class_oid,
+							   bool * would_demote_oos, bool increments_already_applied);
 
 static int heap_update_statistics (THREAD_ENTRY * thread_p, const HFID * hfid, HEAP_HDR_STATS * heap_hdr,
 				   PGBUF_WATCHER * header_watcher);
```

### H21 — Compute an owned effective key

[src/storage/heap_file.c old:12095 / new:12097](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12097)

Read an unchanged UPDATE key with an independent reader of the supplied old row; read omitted INSERT defaults on copied metadata; otherwise clone the source. Apply pending increments only to the copy, preserve NULL, then size/write/read with the domain codec. Use aligned scratch for small values and owned allocation for larger ones. Every failure clears a partial output. The guide's block table explains the branches; direct tests compare reference routing and assert source preservation.

```diff
@@ -12095,6 +12097,132 @@ exit_on_error:
   return (ret == NO_ERROR && (ret = er_errid ()) == NO_ERROR) ? ER_FAILED : ret;
 }
 
+/*
+ * heap_attrinfo_get_effective_key () - obtain the stored-value equivalent of a write's partition key
+ *   return: NO_ERROR or an error code
+ *   attr_info(in): source assignments; never initialized or otherwise modified here
+ *   attrid(in): a schema-validated partition-key attribute
+ *   old_recdes(in): the write path's old row, or NULL for INSERT
+ *   key(out): owned value, initially NULL; caller clears it
+ *
+ * Only the key is prepared. Omitted values use the same representation default
+ * reader as a normal INSERT. Unchanged UPDATE keys use an independent one-key
+ * reader of the supplied old representation. Pending increments affect only
+ * the owned key; the normal row transformer still applies the real mutation.
+ * The scalar codec operates on an owned copy because sizing/writing may
+ * normalize CHAR padding or cache string compression.
+ * No row image, LOB lifecycle operation, or OOS publication is performed.
+ */
+int
+heap_attrinfo_get_effective_key (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, ATTR_ID attrid,
+				 RECDES * old_recdes, DB_VALUE * key)
+{
+  HEAP_ATTRVALUE *value;
+  HEAP_ATTRVALUE omitted;
+  DB_VALUE prepared;
+  const PR_TYPE *pr_type;
+  OR_BUF buf;
+  char scratch[64 + MAX_ALIGNMENT];
+  char *data = PTR_ALIGN (scratch, MAX_ALIGNMENT);
+  char *allocated = NULL;
+  int length;
+  int error = NO_ERROR;
+
+  assert (DB_IS_NULL (key));
+  db_make_null (&prepared);
+  value = heap_attrvalue_locate (attrid, attr_info);
+  if (value == NULL)
+    {
+      return er_errid () != NO_ERROR ? er_errid () : ER_FAILED;
+    }
+  if (value->state == HEAP_UNINIT_ATTRVALUE && old_recdes != NULL && old_recdes->data != NULL)
+    {
+      HEAP_CACHE_ATTRINFO old_key;
+
+      error = heap_attrinfo_start (thread_p, &attr_info->class_oid, 1, &attrid, &old_key);
+      if (error != NO_ERROR)
+	{
+	  goto cleanup;
+	}
+      error = heap_attrinfo_read_dbvalues_without_oid (thread_p, old_recdes, &old_key);
+      if (error == NO_ERROR)
+	{
+	  error = pr_clone_value (&old_key.values[0].dbvalue, &prepared);
+	}
+      heap_attrinfo_end (thread_p, &old_key);
+    }
+  else if (value->state == HEAP_UNINIT_ATTRVALUE)
+    {
+      omitted = *value;
+      db_make_null (&omitted.dbvalue);
+      error = heap_attrvalue_read (NULL, &omitted, attr_info);
+      if (error == NO_ERROR)
+	{
+	  error = pr_clone_value (&omitted.dbvalue, &prepared);
+	}
+      pr_clear_value (&omitted.dbvalue);
+    }
+  else
+    {
+      error = pr_clone_value (&value->dbvalue, &prepared);
+    }
+  if (error != NO_ERROR)
+    {
+      goto cleanup;
+    }
+  if (value->do_increment != 0)
+    {
+      error = qdata_increment_dbval (&prepared, &prepared, value->do_increment);
+      if (error != NO_ERROR)
+	{
+	  goto cleanup;
+	}
+    }
+  if (DB_IS_NULL (&prepared))
+    {
+      error = pr_clone_value (&prepared, key);
+      goto cleanup;
+    }
+
+  pr_type = value->last_attrepr->domain->type;
+  length = pr_type->get_disk_size_of_value (&prepared);
+  if (length <= 0)
+    {
+      error = er_errid () != NO_ERROR ? er_errid () : ER_FAILED;
+      goto cleanup;
+    }
+  if (length > 64)
+    {
+      allocated = (char *) db_private_alloc (thread_p, length);
+      if (allocated == NULL)
+	{
+	  error = ER_OUT_OF_VIRTUAL_MEMORY;
+	  goto cleanup;
+	}
+      data = allocated;
+    }
+  or_init (&buf, data, length);
+  error = pr_type->data_writeval (&buf, &prepared);
+  if (error == NO_ERROR)
+    {
+      length = CAST_BUFLEN (buf.ptr - data);
+      or_init (&buf, data, length);
+      error = pr_type->data_readval (&buf, key, value->last_attrepr->domain, length, true, NULL, 0);
+    }
+
+cleanup:
+  pr_clear_value (&prepared);
+  if (allocated != NULL)
+    {
+      db_private_free_and_init (thread_p, allocated);
+    }
+  if (error != NO_ERROR)
+    {
+      pr_clear_value (key);
+    }
+  return error;
+}
+
 /*
  * heap_attrinfo_set_uninitialized () - Read unitialized attributes
  *   return: NO_ERROR
```

### H22 — Document suppression outputs

[src/storage/heap_file.c old:12297 / new:12425](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12425)

Document that suppression retains inline values and that would_demote is hypothetical. has_oos continues to describe the actual emitted layout.

```diff
@@ -12297,9 +12425,11 @@ heap_attrinfo_get_record_header_size (HEAP_CACHE_ATTRINFO * attr_info, int paylo
  *   return: NO_ERROR, or error code
  *   attr_info(in/out): The attribute information structure
  *   is_mvcc_class(in): true, if MVCC class
+ *   suppress_oos(in): true to keep every column inline even when the record exceeds the OOS trigger
  *   offset_size_ptr(out): offset size
  *   oos_plan(out): selected columns are demoted to OOS
  *   has_oos(out): true if any column is demoted to OOS
+ *   would_demote_oos(out): with suppress_oos, true if a normal layout would have demoted a column
  *   inline_size_after_oos_ptr(out): inline heap record size after OOS demotion
  *
  * Note: Choose the OOS layout and compute the inline heap record size. This size is not the logical
```

### H23 — Implement the extended planner signature

[src/storage/heap_file.c old:12307 / new:12437](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12437)

Keep declaration, definition and caller consistent. Passing the mode separately allows layout decisions to avoid selecting any OOS plan entry.

```diff
@@ -12307,9 +12437,10 @@ heap_attrinfo_get_record_header_size (HEAP_CACHE_ATTRINFO * attr_info, int paylo
  */
 // *INDENT-OFF*
 static int
-heap_attrinfo_determine_disk_layout (HEAP_CACHE_ATTRINFO * attr_info, bool is_mvcc_class, size_t * offset_size_ptr,
+heap_attrinfo_determine_disk_layout (HEAP_CACHE_ATTRINFO * attr_info, bool is_mvcc_class, bool suppress_oos,
+					     size_t * offset_size_ptr,
 					     std::vector<heap_oos_column_plan> * oos_plan, bool * has_oos,
-					     size_t * inline_size_after_oos_ptr)
+					     bool * would_demote_oos, size_t * inline_size_after_oos_ptr)
 // *INDENT-ON*
 {
 // *INDENT-OFF*
```

### H24 — Reset the per-call verdict

[src/storage/heap_file.c old:12320 / new:12451](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12451)

Initialize has_oos false and clear a supplied would-demote output before scanning columns. A reused Boolean must not inherit the previous row's verdict.

```diff
@@ -12320,6 +12451,10 @@ heap_attrinfo_determine_disk_layout (HEAP_CACHE_ATTRINFO * attr_info, bool is_mv
   int i;
 
   *has_oos = false;
+  if (would_demote_oos != NULL)
+    {
+      *would_demote_oos = false;
+    }
 
   /* calcuate the entire size of columns */
   payload_size = heap_attrinfo_get_record_payload_size (attr_info, &column_size);
```

### H25 — Suppress the forced policy before selection

[src/storage/heap_file.c old:12334 / new:12469](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12469)

FORCE_OUTLINE runs before the ordinary size gate. Under suppression set would-demote and continue before plan.selected, payload subtraction and has_oos updates. This is the small-forced-value regression's decisive branch.

```diff
@@ -12334,6 +12469,15 @@ heap_attrinfo_determine_disk_layout (HEAP_CACHE_ATTRINFO * attr_info, bool is_mv
 	  && attr_info->values[i].last_attrepr->oos_storage == OR_ATTRIBUTE_OOS_STORAGE_FORCE_OUTLINE
 	  && !db_value_is_null (&attr_info->values[i].dbvalue) && column_size[i] > OR_OOS_INLINE_SIZE)
 	{
+	  if (suppress_oos)
+	    {
+	      if (would_demote_oos != NULL)
+		{
+		  *would_demote_oos = true;
+		}
+	      continue;
+	    }
+
 	  (*oos_plan)[i].selected = true;
 	  payload_size -= column_size[i];
 	  payload_size += OR_OOS_INLINE_SIZE;
```

### H26 — Suppress ordinary demotion

[src/storage/heap_file.c old:12369 / new:12513](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12513)

After discovering ordinary eligible candidates, report whether candidates exist and return the fully inline size without sorting/selecting/demoting them. The fully inline temporary image can be larger than a heap slot.

```diff
@@ -12369,6 +12513,19 @@ heap_attrinfo_determine_disk_layout (HEAP_CACHE_ATTRINFO * attr_info, bool is_mv
 	    }
 	}
 
+      if (suppress_oos)
+	{
+	  /* The caller only wants a fully-inline image plus the demotion verdict (e.g. to route a
+	   * partitioned write before the target heap of its OOS value chains is known). */
+	  if (would_demote_oos != NULL && !oos_candidates.empty ())
+	    {
+	      *would_demote_oos = true;
+	    }
+
+	  *inline_size_after_oos_ptr = header_size + payload_size;
+	  return NO_ERROR;
+	}
+
       // *INDENT-OFF*
       /* Demote order: columns flagged STORAGE PREFER_INLINE sink to the tail and are externalized
        * only as a last resort; within each priority class, largest first. The idx-descending
```

### H27 — Add explicit OOS owner at insertion boundary

[src/storage/heap_file.c old:12680 / new:12837](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12837)

Extend heap_attrinfo_insert_to_oos with an optional class OID and document per-heap ownership. Retain source attrinfo for payload and LOB preparation.

```diff
@@ -12680,11 +12837,15 @@ static std::atomic<bool> heap_Test_fail_after_oos_publication_reset { false };
  * the BLOB/CLOB ELO-locator copy step, with the inline record writer. This logical heap boundary
  * begins OOS insert publication before any fallible preparation; heap_oos.cpp owns the paired-reset
  * internals, OOS file lookup, and the batched OOS insert call.
+ *
+ * oos_class_oid designates the class whose heap receives the OOS value chains; NULL means
+ * attr_info->class_oid. A partitioned write must pass the pruned partition class, because the
+ * value chains must live in the OOS file of the heap that stores the record (CBRD-27089).
  */
 // *INDENT-OFF*
 static SCAN_CODE
 heap_attrinfo_insert_to_oos (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, int lob_create_flag,
-			     std::vector<heap_oos_column_plan> * oos_plan)
+			     const OID * oos_class_oid, std::vector<heap_oos_column_plan> * oos_plan)
 // *INDENT-ON*
 
 {
```

### H28 — Apply the selected owner

[src/storage/heap_file.c old:12724 / new:12885](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12885)

Pass the override to heap_oos_insert_serialized_values, falling back to attrinfo class for legacy callers. This is where early destination selection becomes a different physical OOS file.

```diff
@@ -12724,7 +12885,7 @@ heap_attrinfo_insert_to_oos (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr
       goto cleanup;
     }
 
-  if (heap_oos_insert_serialized_values (thread_p, &attr_info->class_oid,
+  if (heap_oos_insert_serialized_values (thread_p, oos_class_oid != NULL ? oos_class_oid : &attr_info->class_oid,
 					 cubbase::span < oos_insert_request > (requests.data (), requests.size ()))
       != S_SUCCESS)
     {
```

### H29 — Separate transform modes explicitly

[src/storage/heap_file.c old:12755 / new:12916](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12916)

Normal wrapper uses NULL owner/NULL verdict/false. Owner-aware first pass uses owner/NULL/false. Probe uses NULL/verdict/false. Retained second pass uses owner/NULL/true. The final true skips increments already applied by an earlier probe; it must not be used for the new main path's first transform.

```diff
@@ -12755,7 +12916,61 @@ SCAN_CODE
 heap_attrinfo_transform_to_disk (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, RECDES * old_recdes,
 				 record_descriptor * new_recdes)
 {
-  return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, LOB_FLAG_INCLUDE_LOB);
+  return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, LOB_FLAG_INCLUDE_LOB,
+						   NULL, NULL, false);
+}
+
+/*
+ * heap_attrinfo_transform_to_disk_with_oos_owner () - normal first-pass transformation with a destination OOS heap
+ *
+ * Source representation and assignment identity stay in attr_info. Only OOS ownership is overridden;
+ * value preparation, LOB handling and pending increments use the normal first-pass contract.
+ */
+SCAN_CODE
+heap_attrinfo_transform_to_disk_with_oos_owner (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
+						RECDES * old_recdes, record_descriptor * new_recdes,
+						int lob_create_flag, const OID * oos_class_oid)
+{
+  assert (oos_class_oid != NULL);
+  return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, lob_create_flag,
+						   oos_class_oid, NULL, false);
+}
+
+/*
+ * heap_attrinfo_transform_to_disk_probe_oos () - Transform to disk with OOS demotion suppressed.
+ *
+ *   would_demote_oos(out): true if a normal transform would have demoted at least one column
+ *
+ * Note: Every column stays inline, so the resulting recdes can be larger than a slotted-page
+ * record allows; it is meant for record routing and key extraction, not for direct insertion.
+ * No OOS value chain is written. Side effects on attr_info (LOB copy, INCR/DECR application)
+ * still happen exactly once, so a subsequent heap_attrinfo_transform_to_disk_oos_class call
+ * completes the write without repeating them.
+ */
+SCAN_CODE
+heap_attrinfo_transform_to_disk_probe_oos (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
+					   RECDES * old_recdes, record_descriptor * new_recdes, int lob_create_flag,
+					   bool * would_demote_oos)
+{
+  return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, lob_create_flag,
+						   NULL, would_demote_oos, false);
+}
+
+/*
+ * heap_attrinfo_transform_to_disk_oos_class () - Transform to disk, writing OOS value chains to the
+ *                                                heap of oos_class_oid instead of attr_info->class_oid.
+ *
+ * Note: This is the second pass of a two-pass partitioned write; it assumes
+ * heap_attrinfo_transform_to_disk_probe_oos already ran on the same attr_info, so pending
+ * INCR/DECR assignments were already applied and are not applied again here.
+ */
+SCAN_CODE
+heap_attrinfo_transform_to_disk_oos_class (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
+					   RECDES * old_recdes, record_descriptor * new_recdes, int lob_create_flag,
+					   const OID * oos_class_oid)
+{
+  return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, lob_create_flag,
+						   oos_class_oid, NULL, true);
 }
 
 /*
```

### H30 — Preserve non-LOB normal transformation

[src/storage/heap_file.c old:12775 / new:12990](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R12990)

The except_lob wrapper supplies EXCLUDE_LOB with default owner, no suppression and first-pass increment behavior. This signature adaptation retains the existing contract.

```diff
@@ -12775,7 +12990,8 @@ SCAN_CODE
 heap_attrinfo_transform_to_disk_except_lob (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
 					    RECDES * old_recdes, record_descriptor * new_recdes)
 {
-  return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, LOB_FLAG_EXCLUDE_LOB);
+  return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, LOB_FLAG_EXCLUDE_LOB,
+						   NULL, NULL, false);
 }
 
 /*
```

### H31 — Document and receive transform modes

[src/storage/heap_file.c old:13232 / new:13448](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R13448)

Document pointer-presence suppression, destination override and the retained second-pass flag in the common transformer. The definition matches the updated declaration.

```diff
@@ -13232,12 +13448,17 @@ heap_attrinfo_transform_columns_to_disk (THREAD_ENTRY * thread_p, HEAP_CACHE_ATT
  *   old_recdes(in): where the object's disk format is deposited
  *   new_recdes(in):
  *   lob_create_flag(in):
+ *   oos_class_oid(in): class whose heap receives the OOS value chains; NULL means attr_info->class_oid
+ *   would_demote_oos(out): non-NULL suppresses OOS demotion and reports whether it would have happened
+ *   increments_already_applied(in): true if a previous probe pass already applied INCR/DECR assignments
  *
  * Note: Transform the object represented by attr_info to disk format
  */
 static SCAN_CODE
 heap_attrinfo_transform_to_disk_internal (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
-					  RECDES * old_recdes, record_descriptor * new_recdes, int lob_create_flag)
+					  RECDES * old_recdes, record_descriptor * new_recdes, int lob_create_flag,
+					  const OID * oos_class_oid, bool * would_demote_oos,
+					  bool increments_already_applied)
 {
   OR_BUF buf;
   size_t inline_size_after_oos, mvcc_extra;
```

### H32 — Derive suppression from the pointer

[src/storage/heap_file.c old:13245 / new:13466](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R13466)

Compute suppress_oos from would_demote_oos != NULL. Add an index variable for the retained second-pass premark loop; it is not the early key routing algorithm.

```diff
@@ -13245,6 +13466,8 @@ heap_attrinfo_transform_to_disk_internal (THREAD_ENTRY * thread_p, HEAP_CACHE_AT
   SCAN_CODE status;
   bool is_mvcc_class, is_update;
   bool has_oos;
+  bool suppress_oos = would_demote_oos != NULL;
+  int i;
   // *INDENT-OFF*
   std::vector<heap_oos_column_plan> oos_plan (attr_info->num_values);
   std::set<int> incremented_attrids;
```

### H33 — Retain second-pass increment protection

[src/storage/heap_file.c old:13258 / new:13481](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R13481)

When increments_already_applied is true, prefill the same set consulted by the fixed-column writer. Current owner-aware main writes pass false; buffer-retry protection in the normal writer remains independently necessary.

```diff
@@ -13258,6 +13481,19 @@ heap_attrinfo_transform_to_disk_internal (THREAD_ENTRY * thread_p, HEAP_CACHE_AT
       return S_ERROR;
     }
 
+  if (increments_already_applied)
+    {
+      /* a probe pass already applied the pending INCR/DECR assignments to the dbvalues; pre-mark
+       * them so the column writer below does not apply them a second time */
+      for (i = 0; i < attr_info->num_values; i++)
+	{
+	  if (attr_info->values[i].do_increment != 0)
+	    {
+	      incremented_attrids.insert (i);
+	    }
+	}
+    }
+
   /* get any of the values that have not been set/read */
   if (heap_attrinfo_set_uninitialized (thread_p, &attr_info->inst_oid, old_recdes, attr_info) != NO_ERROR)
     {
```

### H34 — Forward mode into layout planning

[src/storage/heap_file.c old:13271 / new:13507](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R13507)

Pass suppression and verdict to the planner while retaining actual has_oos and inline-size outputs. Later OOS writing is controlled by the actual has_oos result.

```diff
@@ -13271,8 +13507,8 @@ heap_attrinfo_transform_to_disk_internal (THREAD_ENTRY * thread_p, HEAP_CACHE_AT
   is_mvcc_class = !mvcc_is_mvcc_disabled_class (&(attr_info->class_oid));
 
   /* determine the layout and the size */
-  if (heap_attrinfo_determine_disk_layout (attr_info, is_mvcc_class, &offset_size, &oos_plan, &has_oos,
-					   &inline_size_after_oos) != NO_ERROR)
+  if (heap_attrinfo_determine_disk_layout (attr_info, is_mvcc_class, suppress_oos, &offset_size, &oos_plan, &has_oos,
+					   would_demote_oos, &inline_size_after_oos) != NO_ERROR)
     {
       return S_ERROR;
     }
```

### H35 — Forward owner into OOS publication

[src/storage/heap_file.c old:13307 / new:13543](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R13543)

The transform sends oos_class_oid to the OOS insertion boundary only after the existing bigone rejection. This propagates the destination selected by locator without rewriting attrinfo identity.

```diff
@@ -13307,7 +13543,7 @@ heap_attrinfo_transform_to_disk_internal (THREAD_ENTRY * thread_p, HEAP_CACHE_AT
   if (has_oos)
     {
       /* insert big columns to OOS */
-      status = heap_attrinfo_insert_to_oos (thread_p, attr_info, lob_create_flag, &oos_plan);
+      status = heap_attrinfo_insert_to_oos (thread_p, attr_info, lob_create_flag, oos_class_oid, &oos_plan);
       if (status != S_SUCCESS)
 	{
 	  return S_ERROR;
```

### H36 — Keep unit-test bridge default ownership

[src/storage/heap_file.c old:28431 / new:28667](https://github.com/CUBRID/cubrid/pull/7600/files#diff-86bbecbbdf80125cc10e0d00b46f94b13fe8f79247048ccf9598bd9e2bc39d10R28667)

Supply NULL for the new owner parameter in the pre-existing bridge. Its synthetic attrinfo class continues to determine ownership.

```diff
@@ -28431,6 +28667,6 @@ bridge_heap_attrinfo_insert_to_oos (THREAD_ENTRY * thread_p, const OID * class_o
 
   COPY_OID (&attr_info.class_oid, class_oid);
   attr_info.num_values = 0;
-  return heap_attrinfo_insert_to_oos (thread_p, &attr_info, LOB_FLAG_INCLUDE_LOB, &oos_plan);
+  return heap_attrinfo_insert_to_oos (thread_p, &attr_info, LOB_FLAG_INCLUDE_LOB, NULL, &oos_plan);
 }
 #endif /* CUBRID_UNIT_TEST_ENABLED */
```

### H37 — Expose key and transform APIs

[src/storage/heap_file.h old:503 / new:503](https://github.com/CUBRID/cubrid/pull/7600/files#diff-97b72d043d15b8fe701fcee25ec78c565308941aa7e3d2bf0fbb37664fafa9d3R503)

Declare the effective-key helper plus owner-first-pass, probe and retained rebuild wrappers. Old transformer declarations remain. This is an internal engine header change, not a client protocol change.

```diff
@@ -503,10 +503,22 @@ extern int heap_attrinfo_delete_lob (THREAD_ENTRY * thread_p, RECDES * recdes, H
 extern DB_VALUE *heap_attrinfo_access (ATTR_ID attrid, HEAP_CACHE_ATTRINFO * attr_info);
 extern int heap_attrinfo_set (const OID * inst_oid, ATTR_ID attrid, DB_VALUE * attr_val,
 			      HEAP_CACHE_ATTRINFO * attr_info);
+extern int heap_attrinfo_get_effective_key (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, ATTR_ID attrid,
+					    RECDES * old_recdes, DB_VALUE * key);
 extern SCAN_CODE heap_attrinfo_transform_to_disk (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
 						  RECDES * old_recdes, record_descriptor * new_recdes);
+extern SCAN_CODE heap_attrinfo_transform_to_disk_with_oos_owner (THREAD_ENTRY * thread_p,
+								 HEAP_CACHE_ATTRINFO * attr_info, RECDES * old_recdes,
+								 record_descriptor * new_recdes, int lob_create_flag,
+								 const OID * oos_class_oid);
 extern SCAN_CODE heap_attrinfo_transform_to_disk_except_lob (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
 							     RECDES * old_recdes, record_descriptor * new_recdes);
+extern SCAN_CODE heap_attrinfo_transform_to_disk_probe_oos (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
+							    RECDES * old_recdes, record_descriptor * new_recdes,
+							    int lob_create_flag, bool * would_demote_oos);
+extern SCAN_CODE heap_attrinfo_transform_to_disk_oos_class (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
+							    RECDES * old_recdes, record_descriptor * new_recdes,
+							    int lob_create_flag, const OID * oos_class_oid);
 
 extern DB_VALUE *heap_attrinfo_generate_key (THREAD_ENTRY * thread_p, int n_atts, int *att_ids, int *atts_prefix_length,
 					     HEAP_CACHE_ATTRINFO * attr_info, RECDES * recdes, DB_VALUE * dbvalue,
```

### H38 — Declare UPDATE's expected owner

[src/transaction/locator_sr.c old:152 / new:152](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R152)

Extend the private locator_update_force declaration with an optional expected destination. Each caller must explicitly say whether it has an early decision to validate.

```diff
@@ -152,7 +152,7 @@ static int locator_update_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * cla
 				 HEAP_SCANCACHE * scan_cache, int *force_count, bool not_check_fk,
 				 REPL_INFO_TYPE repl_info_type, int pruning_type, PRUNING_CONTEXT * pcontext,
 				 MVCC_REEV_DATA * mvcc_reev_data, UPDATE_INPLACE_STYLE force_in_place,
-				 bool need_locking);
+				 bool need_locking, const OID * expected_class_oid);
 static int locator_move_record (THREAD_ENTRY * thread_p, HFID * old_hfid, OID * old_class_oid, OID * obj_oid,
 				OID * new_class_oid, HFID * new_class_hfid, RECDES * recdes,
 				HEAP_SCANCACHE * scan_cache, int op_type, int has_index, int *force_count,
```

### H39 — Name the INSERT implementation

[src/transaction/locator_sr.c old:4924 / new:4924](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R4924)

Rename the comment to match the new private internal function. Behavior is provided by the surrounding signature and agreement-check changes.

```diff
@@ -4924,7 +4924,7 @@ error3:
 }
 
 /*
- * locator_insert_force () - Insert the given object on this heap
+ * locator_insert_force_internal () - Insert the given object on this heap
  *
  * return: NO_ERROR if all OK, ER_ status otherwise
  *
```

### H40 — Introduce private INSERT with expected destination

[src/transaction/locator_sr.c old:4944 / new:4944](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R4944)

Add expected_class_oid while keeping the old public API via H42. This avoids forcing unrelated callers to create an early destination.

```diff
@@ -4944,16 +4944,17 @@ error3:
  *   pcontext(in): partition pruning context
  *   func_preds(in): cached function index expressions
  *   force_in_place:
+ *   expected_class_oid(in): optional early destination; final routing must agree before inserting
  *
  * Note: The given object is inserted on this heap and all appropriate
  *              index entries are inserted.
  */
-int
-locator_insert_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid, OID * oid, RECDES * recdes, int has_index,
-		      int op_type, HEAP_SCANCACHE * scan_cache, int *force_count, int pruning_type,
-		      PRUNING_CONTEXT * pcontext, FUNC_PRED_UNPACK_INFO * func_preds,
-		      UPDATE_INPLACE_STYLE force_in_place, PGBUF_WATCHER * home_hint_p, bool has_BU_lock,
-		      bool dont_check_fk, bool use_bulk_logging)
+static int
+locator_insert_force_internal (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid, OID * oid, RECDES * recdes,
+			       int has_index, int op_type, HEAP_SCANCACHE * scan_cache, int *force_count,
+			       int pruning_type, PRUNING_CONTEXT * pcontext, FUNC_PRED_UNPACK_INFO * func_preds,
+			       UPDATE_INPLACE_STYLE force_in_place, PGBUF_WATCHER * home_hint_p, bool has_BU_lock,
+			       bool dont_check_fk, bool use_bulk_logging, const OID * expected_class_oid)
 {
 #if 0				/* TODO - dead code; do not delete me */
   OID rep_dir = { NULL_PAGEID, NULL_SLOTID, NULL_VOLID };
```

### H41 — Reject INSERT destination disagreement

[src/transaction/locator_sr.c old:4992 / new:4993](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R4993)

After final record pruning succeeds, compare against the early owner. On mismatch return ER_GENERIC_ERROR through existing error handling before the following subclass/heap insertion path. Do not silently redirect already-prepared OOS chains.

```diff
@@ -4992,6 +4993,14 @@ locator_insert_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid, OID
 	{
 	  goto error2;
 	}
+      if (expected_class_oid != NULL && !OID_EQ (expected_class_oid, &real_class_oid))
+	{
+	  /* OOS chains may already belong to the early destination. Never redirect them to another heap.
+	   * Return through the ordinary statement-error path so logged OOS inserts are rolled back. */
+	  er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_GENERIC_ERROR, 0);
+	  error_code = ER_GENERIC_ERROR;
+	  goto error2;
+	}
       if (!OID_ISNULL (&superclass_oid))
 	{
 	  granted = lock_subclass (thread_p, &real_class_oid, &superclass_oid, IX_LOCK, LK_UNCOND_LOCK);
```

### H42 — Preserve legacy INSERT callers

[src/transaction/locator_sr.c old:5283 / new:5292](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R5292)

The original public locator_insert_force forwards all existing arguments plus NULL expected owner. Only the main attribute write invokes the private guarded variant directly.

```diff
@@ -5283,6 +5292,21 @@ error2:
   return error_code;
 }
 
+/*
+ * locator_insert_force () - retain the existing force interface for callers without an early destination
+ */
+int
+locator_insert_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid, OID * oid, RECDES * recdes, int has_index,
+		      int op_type, HEAP_SCANCACHE * scan_cache, int *force_count, int pruning_type,
+		      PRUNING_CONTEXT * pcontext, FUNC_PRED_UNPACK_INFO * func_preds,
+		      UPDATE_INPLACE_STYLE force_in_place, PGBUF_WATCHER * home_hint_p, bool has_BU_lock,
+		      bool dont_check_fk, bool use_bulk_logging)
+{
+  return locator_insert_force_internal (thread_p, hfid, class_oid, oid, recdes, has_index, op_type, scan_cache,
+					force_count, pruning_type, pcontext, func_preds, force_in_place, home_hint_p,
+					has_BU_lock, dont_check_fk, use_bulk_logging, NULL);
+}
+
 int
 locator_oos_insert_force (THREAD_ENTRY * thread_p, OID * class_oid, RECDES * recdes)
 {
```

### H43 — Document UPDATE agreement

[src/transaction/locator_sr.c old:5457 / new:5481](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R5481)

Document that the optional early class must agree with final routing before the subsequent row heap/index mutation. This is a comparison contract, not a transaction-abort implementation.

```diff
@@ -5457,6 +5481,7 @@ locator_move_record (THREAD_ENTRY * thread_p, HFID * old_hfid, OID * old_class_o
  *			 and the update style will be decided in this function.
  *			 Otherwise the update of the instance will be made in
  *			 place and according to provided style.
+ *   expected_class_oid(in): optional early destination; final routing must agree before heap/index mutation
  *
  * Note: The given object is updated on this heap and all appropriate
  *              index entries are updated.
```

### H44 — Receive UPDATE agreement input

[src/transaction/locator_sr.c old:5466 / new:5491](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R5491)

Extend the private definition to receive expected_class_oid. H45 consumes it after final routing; unrelated callers pass NULL.

```diff
@@ -5466,7 +5491,7 @@ locator_update_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid, OID
 		      RECDES * recdes, int has_index, ATTR_ID * att_id, int n_att_id, int op_type,
 		      HEAP_SCANCACHE * scan_cache, int *force_count, bool not_check_fk, REPL_INFO_TYPE repl_info_type,
 		      int pruning_type, PRUNING_CONTEXT * pcontext, MVCC_REEV_DATA * mvcc_reev_data,
-		      UPDATE_INPLACE_STYLE force_in_place, bool need_locking)
+		      UPDATE_INPLACE_STYLE force_in_place, bool need_locking, const OID * expected_class_oid)
 {
   OID rep_dir = { NULL_PAGEID, NULL_SLOTID, NULL_VOLID };
   char *rep_dir_offset;
```

### H45 — Reject UPDATE destination disagreement

[src/transaction/locator_sr.c old:5993 / new:6018](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R6018)

Compare final class with the early OOS owner before source-class reidentification and partition movement. Failure follows existing error cleanup; logged OOS work depends on the caller's rollback path.

```diff
@@ -5993,6 +6018,14 @@ locator_update_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid, OID
 	      goto error;
 	    }
 
+	  /* Final record routing must agree with the heap chosen for OOS preparation. */
+	  if (expected_class_oid != NULL && !OID_EQ (&real_class_oid, expected_class_oid))
+	    {
+	      er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_GENERIC_ERROR, 0);
+	      error_code = ER_GENERIC_ERROR;
+	      goto error;
+	    }
+
 	  /* make sure we use the correct class oid - we could be dealing with a classoid resulted from a unique btid
 	   * pruning */
 	  if (heap_get_class_oid (thread_p, oid, class_oid) != S_SUCCESS)
```

### H46 — Adapt multi-update force

[src/transaction/locator_sr.c old:6749 / new:6782](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R6782)

Append NULL expected class to the existing nonpartitioned multi-update caller. It has no early attrinfo routing result to certify.

```diff
@@ -6749,7 +6782,7 @@ locator_force_for_multi_update (THREAD_ENTRY * thread_p, LC_COPYAREA * force_are
 	  error_code =
 	    locator_update_force (thread_p, &obj->hfid, &obj->class_oid, &obj->oid, NULL, &recdes,
 				  has_index, NULL, 0, MULTI_ROW_UPDATE, &scan_cache, &force_count, false, repl_info,
-				  DB_NOT_PARTITIONED_CLASS, NULL, NULL, UPDATE_INPLACE_NONE, true);
+				  DB_NOT_PARTITIONED_CLASS, NULL, NULL, UPDATE_INPLACE_NONE, true, NULL);
 	  if (error_code != NO_ERROR)
 	    {
 	      /*
```

### H47 — Adapt replication force

[src/transaction/locator_sr.c old:7139 / new:7172](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7172)

Append NULL to replication's existing record-based UPDATE call. This does not introduce effective-key preparation into the replication path.

```diff
@@ -7139,7 +7172,8 @@ xlocator_repl_force (THREAD_ENTRY * thread_p, LC_COPYAREA * force_area, LC_COPYA
 	      error_code =
 		locator_update_force (thread_p, &obj->hfid, &obj->class_oid, &obj->oid, NULL, &recdes, has_index,
 				      NULL, 0, SINGLE_ROW_UPDATE, force_scancache, &force_count, false,
-				      REPL_INFO_TYPE_RBR_NORMAL, pruning_type, NULL, NULL, UPDATE_INPLACE_NONE, true);
+				      REPL_INFO_TYPE_RBR_NORMAL, pruning_type, NULL, NULL, UPDATE_INPLACE_NONE, true,
+				      NULL);
 
 	      if (error_code == NO_ERROR)
 		{
```

### H48 — Adapt generic force

[src/transaction/locator_sr.c old:7349 / new:7383](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7383)

Append NULL to xlocator_force's existing UPDATE call. Preserve behavior for callers that already supply serialized records.

```diff
@@ -7349,7 +7383,7 @@ xlocator_force (THREAD_ENTRY * thread_p, LC_COPYAREA * force_area, int num_ignor
 	  error_code =
 	    locator_update_force (thread_p, &obj->hfid, &obj->class_oid, &obj->oid, NULL, &recdes,
 				  has_index, NULL, 0, SINGLE_ROW_UPDATE, force_scancache, &force_count, false,
-				  REPL_INFO_TYPE_RBR_NORMAL, pruning_type, NULL, NULL, UPDATE_INPLACE_NONE, true);
+				  REPL_INFO_TYPE_RBR_NORMAL, pruning_type, NULL, NULL, UPDATE_INPLACE_NONE, true, NULL);
 
 	  if (error_code == NO_ERROR)
 	    {
```

### H49 — Name the internal copy-area builder

[src/transaction/locator_sr.c old:7461 / new:7495](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7495)

Rename the implementation comment; the public wrapper is reintroduced below. Allocation ownership stays with the existing copy-area API.

```diff
@@ -7461,7 +7495,7 @@ error:
 }
 
 /*
- * locator_allocate_copy_area_by_attr_info () - Transforms attribute
+ * locator_allocate_copy_area_by_attr_info_internal () - Transforms attribute
  *              information into a disk representation and allocates a
  *              LC_COPYAREA big enough to fit the representation
  *
```

### H50 — Add first-pass owner mode

[src/transaction/locator_sr.c old:7475 / new:7509](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7509)

Private builder receives owner, probe verdict and oos_first_pass. This extra private flag distinguishes a real first transform from the retained owner-after-probe rebuild contract.

```diff
@@ -7475,12 +7509,21 @@ error:
  *   copyarea_length_hint(in): An estimated size for the LC_COPYAREA or -1 if
  *                             an estimated size is not known.
  *   lob_create_flag(in) :
+ *   oos_class_oid(in): class whose heap receives the OOS value chains; NULL means
+ *                      attr_info->class_oid. A partitioned write passes the pruned partition.
+ *   probe_would_demote_oos(out): when non-NULL, suppress OOS demotion (build a fully-inline
+ *                                image, write no OOS value chain) and report whether a normal
+ *                                transform would have demoted a column.
+ *   oos_first_pass(in): use normal preparation with the selected OOS owner, without a preceding probe
  *
  * Note: The allocated should be freed by using locator_free_copy_area ()
  */
-LC_COPYAREA *
-locator_allocate_copy_area_by_attr_info (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, RECDES * old_recdes,
-					 RECDES * new_recdes, const int copyarea_length_hint, int lob_create_flag)
+static LC_COPYAREA *
+locator_allocate_copy_area_by_attr_info_internal (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
+						  RECDES * old_recdes, RECDES * new_recdes,
+						  const int copyarea_length_hint, int lob_create_flag,
+						  const OID * oos_class_oid, bool * probe_would_demote_oos,
+						  bool oos_first_pass)
 {
   LC_COPYAREA *copyarea = NULL;
   int copyarea_length = copyarea_length_hint <= 0 ? DB_PAGESIZE : copyarea_length_hint;
```

### H51 — Dispatch copy-area transformation

[src/transaction/locator_sr.c old:7504 / new:7547](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7547)

Priority is owner-first-pass, probe, retained owner-rebuild, except-LOB, normal. The first branch asserts owner exists and no probe output is present. Existing buffer growth and copy-area release behavior remain below; mode selection does not itself perform rollback.

```diff
@@ -7504,7 +7547,23 @@ locator_allocate_copy_area_by_attr_info (THREAD_ENTRY * thread_p, HEAP_CACHE_ATT
   new_recdes->data = copyarea->mem;
   new_recdes->area_size = copyarea->length;
 
-  if (lob_create_flag == LOB_FLAG_EXCLUDE_LOB)
+  if (oos_first_pass)
+    {
+      assert (oos_class_oid != NULL && probe_would_demote_oos == NULL);
+      scan = heap_attrinfo_transform_to_disk_with_oos_owner (thread_p, attr_info, old_recdes, &build_record,
+							     lob_create_flag, oos_class_oid);
+    }
+  else if (probe_would_demote_oos != NULL)
+    {
+      scan = heap_attrinfo_transform_to_disk_probe_oos (thread_p, attr_info, old_recdes, &build_record,
+							lob_create_flag, probe_would_demote_oos);
+    }
+  else if (oos_class_oid != NULL)
+    {
+      scan = heap_attrinfo_transform_to_disk_oos_class (thread_p, attr_info, old_recdes, &build_record,
+							lob_create_flag, oos_class_oid);
+    }
+  else if (lob_create_flag == LOB_FLAG_EXCLUDE_LOB)
     {
       scan = heap_attrinfo_transform_to_disk_except_lob (thread_p, attr_info, old_recdes, &build_record);
     }
```

### H52 — Expose normal/probe/rebuild wrapper

[src/transaction/locator_sr.c old:7545 / new:7604](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7604)

The public builder forwards its expanded arguments with oos_first_pass=false. New main writes deliberately bypass it for the private first-pass owner mode.

```diff
@@ -7545,6 +7604,19 @@ locator_allocate_copy_area_by_attr_info (THREAD_ENTRY * thread_p, HEAP_CACHE_ATT
   return copyarea;
 }
 
+/*
+ * locator_allocate_copy_area_by_attr_info () - preserve the existing normal/probe/rebuild interface
+ */
+LC_COPYAREA *
+locator_allocate_copy_area_by_attr_info (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, RECDES * old_recdes,
+					 RECDES * new_recdes, const int copyarea_length_hint, int lob_create_flag,
+					 const OID * oos_class_oid, bool * probe_would_demote_oos)
+{
+  return locator_allocate_copy_area_by_attr_info_internal (thread_p, attr_info, old_recdes, new_recdes,
+							   copyarea_length_hint, lob_create_flag, oos_class_oid,
+							   probe_would_demote_oos, false);
+}
+
 /*
  * locator_attribute_info_force () - Force an object represented by attribute
  *                                   information structure
```

### H53 — Keep destination independent

[src/transaction/locator_sr.c old:7595 / new:7667](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7667)

Initialize write_destination to NULL so nonpartitioned calls naturally have no expected destination. Preserve the existing local source class/HFID copies.

```diff
@@ -7595,6 +7667,7 @@ locator_attribute_info_force (THREAD_ENTRY * thread_p, const HFID * hfid, OID *
   int error_code = NO_ERROR;
   HFID class_hfid;
   OID class_oid;
+  OID write_destination = OID_INITIALIZER;
   MVCC_SNAPSHOT *saved_mvcc_snapshot = NULL;
 
   /*
```

### H54 — Route before the first full transform

[src/transaction/locator_sr.c old:7692 / new:7765](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7765)

For partitioned writes initialize fallback destination identifiers, select INSERT or UPDATE key routing, and stop on error. Then build the row once with INCLUDE_LOB, selected owner and oos_first_pass=true. Leave source class untouched for final validation and movement. Nonpartitioned writes explicitly request the default modes.

```diff
@@ -7692,9 +7765,40 @@ locator_attribute_info_force (THREAD_ENTRY * thread_p, const HFID * hfid, OID *
     case LC_FLUSH_INSERT:
     case LC_FLUSH_INSERT_PRUNE:
     case LC_FLUSH_INSERT_PRUNE_VERIFY:
-      copyarea =
-	locator_allocate_copy_area_by_attr_info (thread_p, attr_info, old_recdes, &new_recdes, -1,
-						 LOB_FLAG_INCLUDE_LOB);
+      if (pruning_type != DB_NOT_PARTITIONED_CLASS)
+	{
+	  HFID pruned_hfid;
+
+	  COPY_OID (&write_destination, &class_oid);
+	  HFID_COPY (&pruned_hfid, &class_hfid);
+	  if (LC_IS_FLUSH_INSERT (operation))
+	    {
+	      error_code = partition_prune_insert_by_attrinfo (thread_p, &class_oid, attr_info, pcontext, pruning_type,
+							       &write_destination, &pruned_hfid, NULL);
+	    }
+	  else
+	    {
+	      assert (LC_IS_FLUSH_UPDATE (operation));
+	      error_code = partition_prune_update_by_attrinfo (thread_p, &class_oid, attr_info, old_recdes, pcontext,
+							       pruning_type, &write_destination, &pruned_hfid, NULL);
+	    }
+	  if (error_code != NO_ERROR)
+	    {
+	      break;
+	    }
+
+	  /* Prepare the full row once, writing OOS values to the selected heap. Keep the source class
+	   * unchanged: final force still performs routing, validation, representation patching and movement. */
+	  copyarea = locator_allocate_copy_area_by_attr_info_internal (thread_p, attr_info, old_recdes, &new_recdes, -1,
+								       LOB_FLAG_INCLUDE_LOB, &write_destination, NULL,
+								       true);
+	}
+      else
+	{
+	  copyarea =
+	    locator_allocate_copy_area_by_attr_info (thread_p, attr_info, old_recdes, &new_recdes, -1,
+						     LOB_FLAG_INCLUDE_LOB, NULL, NULL);
+	}
       if (copyarea == NULL)
 	{
 	  error_code = ER_FAILED;
```

### H55 — Carry expected owner into INSERT force

[src/transaction/locator_sr.c old:7705 / new:7809](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7809)

Call the private INSERT variant and pass the selected destination unless NULL. Existing default use_bulk_logging=false is now explicit along with the other unchanged flags.

```diff
@@ -7705,9 +7809,10 @@ locator_attribute_info_force (THREAD_ENTRY * thread_p, const HFID * hfid, OID *
       if (LC_IS_FLUSH_INSERT (operation))
 	{
 	  error_code =
-	    locator_insert_force (thread_p, &class_hfid, &class_oid, oid, &new_recdes, true, op_type, scan_cache,
-				  force_count, pruning_type, pcontext, func_preds, UPDATE_INPLACE_NONE, NULL, false,
-				  false);
+	    locator_insert_force_internal (thread_p, &class_hfid, &class_oid, oid, &new_recdes, true, op_type,
+					   scan_cache, force_count, pruning_type, pcontext, func_preds,
+					   UPDATE_INPLACE_NONE, NULL, false, false, false,
+					   OID_ISNULL (&write_destination) ? NULL : &write_destination);
 	}
       else
 	{
```

### H56 — Carry expected owner into UPDATE force

[src/transaction/locator_sr.c old:7725 / new:7830](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R7830)

Pass the same selected destination into final UPDATE. An unchanged key and a moving key both require agreement with the OOS owner chosen before transformation.

```diff
@@ -7725,7 +7830,8 @@ locator_attribute_info_force (THREAD_ENTRY * thread_p, const HFID * hfid, OID *
 	  error_code =
 	    locator_update_force (thread_p, &class_hfid, &class_oid, oid, old_recdes, &new_recdes, has_index,
 				  att_id, n_att_id, op_type, scan_cache, force_count, not_check_fk, repl_info,
-				  pruning_type, pcontext, mvcc_reev_data, force_update_inplace, need_locking);
+				  pruning_type, pcontext, mvcc_reev_data, force_update_inplace, need_locking,
+				  OID_ISNULL (&write_destination) ? NULL : &write_destination);
 	  if (error_code != NO_ERROR)
 	    {
 	      ASSERT_ERROR ();
```

### H57 — Retain reevaluation defaults

[src/transaction/locator_sr.c old:13781 / new:13887](https://github.com/CUBRID/cubrid/pull/7600/files#diff-ec3d8025f8499bd30088bfbed87d31b183b63f1a59807b539239e26e80b78ea4R13887)

The MVCC reevaluation copy-area call adds NULL owner and NULL probe output. This is signature adaptation, not evidence that all concurrent reevaluation paths have been validated by the new standalone tests.

```diff
@@ -13781,7 +13887,7 @@ locator_mvcc_reev_cond_assigns (THREAD_ENTRY * thread_p, OID * class_oid, const
 	}
       mvcc_reev_data->copyarea =
 	locator_allocate_copy_area_by_attr_info (thread_p, mvcc_reev_data->curr_attrinfo, recdes,
-						 mvcc_reev_data->new_recdes, -1, LOB_FLAG_INCLUDE_LOB);
+						 mvcc_reev_data->new_recdes, -1, LOB_FLAG_INCLUDE_LOB, NULL, NULL);
       if (mvcc_reev_data->copyarea == NULL)
 	{
 	  ev_res = V_ERROR;
```

### H58 — Update the copy-area declaration

[src/transaction/locator_sr.h old:83 / new:83](https://github.com/CUBRID/cubrid/pull/7600/files#diff-5195f47502d54541ddfe3f6dc3c658a3c8ea02c5cf39348d8775a4f46c7099d7R83)

Expose the added owner and suppression output parameters consistently with all callers. The private first-pass flag is deliberately not part of this public engine declaration.

```diff
@@ -83,7 +83,8 @@ extern int locator_attribute_info_force (THREAD_ENTRY * thread_p, const HFID * h
 					 bool need_locking);
 extern LC_COPYAREA *locator_allocate_copy_area_by_attr_info (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info,
 							     RECDES * old_recdes, RECDES * new_recdes,
-							     const int copyarea_length_hint, int lob_create_flag);
+							     const int copyarea_length_hint, int lob_create_flag,
+							     const OID * oos_class_oid, bool * probe_would_demote_oos);
 extern int locator_other_insert_delete (THREAD_ENTRY * thread_p, HFID * hfid, OID * oid, BTID * btid,
 					bool btid_dup_key_locked, HFID * newhfid, OID * newoid,
 					HEAP_CACHE_ATTRINFO * attr_info, HEAP_SCANCACHE * scan_cache, int *force_count,
```

### H59 — Allow diagnostic-heavy test execution

[unit_tests/oos/sql/CMakeLists.txt old:54 / new:54](https://github.com/CUBRID/cubrid/pull/7600/files#diff-3275cf29164ab3fd22b8f905a3bf3fb643804e52b44926cf725e5897598cf408R54)

Override only test_oos_sql_show's timeout to 300 seconds. Fault injection and routing errors collect debug stacks; fixture requirements and serial execution are unchanged.

```diff
@@ -54,3 +54,6 @@ set_tests_properties(
   test_oos_sql_visible_version
   PROPERTIES FIXTURES_REQUIRED OOS_DB RUN_SERIAL TRUE TIMEOUT 30
 )
+
+# Routing rejection and injected cleanup failures collect diagnostic stacks in debug builds.
+set_tests_properties(test_oos_sql_show PROPERTIES TIMEOUT 300)
```

### H60 — Provide direct-interface test infrastructure

[unit_tests/oos/sql/test_oos_sql_show.cpp old:21 / new:21](https://github.com/CUBRID/cubrid/pull/7600/files#diff-7fdae0e381b6e45764169b71c10fbf166556914aac1c9afb4e4ba9aab483aa38R21)

Include routing, locator, OOS, logging, record and primitive APIs plus string support. Declare existing failure hooks. scoped_sa_server increments/decrements db_on_server around direct server calls so SA allocation follows server conventions; it does not start a SERVER_MODE process.

```diff
@@ -21,11 +21,36 @@
  */
 
 #include <algorithm>
+#include <string>
 
+#include "partition_sr.h"
+#include "locator_sr.h"
+#include "heap_oos.hpp"
+#include "log_impl.h"
+#include "record_descriptor.hpp"
+#include "object_primitive.h"
 #include "test_oos_sql_common.hpp"
 
+// Direct server interfaces in SA must use server allocation, just like network_interface_cl.c.
+extern unsigned int db_on_server;
+void bridge_heap_attrinfo_fail_after_oos_publication_reset_once ();
+void bridge_heap_attrinfo_disarm_publication_reset_failure ();
+
 namespace
 {
+  class scoped_sa_server
+  {
+    public:
+      scoped_sa_server ()
+      {
+	db_on_server++;
+      }
+      ~scoped_sa_server ()
+      {
+	db_on_server--;
+      }
+  };
+
   enum show_heap_oos_column
   {
     COL_TABLE_NAME = 0,
```

### H61 — Assert logical values and physical owners

[unit_tests/oos/sql/test_oos_sql_show.cpp old:154 / new:179](https://github.com/CUBRID/cubrid/pull/7600/files#diff-7fdae0e381b6e45764169b71c10fbf166556914aac1c9afb4e4ba9aab483aa38R179)

Add string extraction with DB_VALUE cleanup, schema-prefix removal, count queries and exact OOS file/chunk expectations. The physical helper checks a single row and closes its query result. Distinct logical and physical oracles catch the original bug that successful SELECT missed.

```diff
@@ -154,6 +179,64 @@ namespace
     db_value_clear (&val);
     return rc;
   }
+
+  static int
+  get_string_column (DB_QUERY_RESULT *result, int column, std::string *out_val)
+  {
+    DB_VALUE val;
+    int rc;
+
+    db_make_null (&val);
+    rc = db_query_get_tuple_value (result, column, &val);
+    if (rc == NO_ERROR)
+      {
+	const char *str = db_get_string (&val);
+	if (str == nullptr)
+	  {
+	    rc = ER_FAILED;
+	  }
+	else
+	  {
+	    *out_val = str;
+	  }
+      }
+
+    db_value_clear (&val);
+    return rc;
+  }
+
+  static std::string
+  unqualified_table_name (const std::string &table_name)
+  {
+    std::string::size_type separator = table_name.rfind ('.');
+    return separator == std::string::npos ? table_name : table_name.substr (separator + 1);
+  }
+
+  static void
+  expect_sql_count (const char *sql, int expected)
+  {
+    SCOPED_TRACE (sql);
+    int count = -1;
+    ASSERT_EQ (fetch_single_int (sql, &count), NO_ERROR);
+    EXPECT_EQ (count, expected);
+  }
+
+  static void
+  expect_oos_records (const char *table, int has_file, int expected_records)
+  {
+    SCOPED_TRACE (table);
+    std::string sql = std::string ("SHOW HEAP OOS OF ") + table;
+    DB_QUERY_RESULT *result = nullptr;
+    ASSERT_EQ (show_heap_oos_query (sql.c_str (), &result), NO_ERROR);
+    int actual_has_file = -1;
+    int actual_records = -1;
+    EXPECT_EQ (get_int_column (result, COL_HAS_OOS_FILE, &actual_has_file), NO_ERROR);
+    EXPECT_EQ (get_int_column (result, COL_OOS_NUM_RECS, &actual_records), NO_ERROR);
+    EXPECT_EQ (actual_has_file, has_file);
+    EXPECT_EQ (actual_records, expected_records);
+    EXPECT_EQ (db_query_next_tuple (result), DB_CURSOR_END);
+    db_query_end (result);
+  }
 }
 
 class OosSqlShow : public ::testing::Test
```

### H62 — Add 28 discriminating SQL tests

[unit_tests/oos/sql/test_oos_sql_show.cpp old:351 / new:434](https://github.com/CUBRID/cubrid/pull/7600/files#diff-7fdae0e381b6e45764169b71c10fbf166556914aac1c9afb4e4ba9aab483aa38R434)

This large hunk contains 28 new tests, not one undifferentiated fixture. The test catalog below links each exact function and explains its distinguishing assertions, reference independence and limits. Four earlier SHOW tests remain unchanged.

```diff
@@ -351,6 +434,1235 @@ TEST_F (OosSqlShow, ShowAllHeapOosReportsPartitionRows)
   db_query_end (result);
 }
 
+TEST_F (OosSqlShow, PartitionedForceOutlineStoresOosInPrunedHeap)
+{
+  int rc = exec_sql ("CREATE TABLE t_oos_show_part ("
+		     "id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		     "PARTITION BY RANGE (id) ("
+		     "PARTITION p0 VALUES LESS THAN (10), "
+		     "PARTITION p1 VALUES LESS THAN MAXVALUE)");
+  ASSERT_GE (rc, 0);
+  rc = exec_sql ("INSERT INTO t_oos_show_part VALUES (1, REPEAT(X'EE', 64))");
+  ASSERT_GE (rc, 0);
+  db_commit_transaction ();
+
+  int value_matches = 0;
+  rc = fetch_single_int ("SELECT data_col = CAST(REPEAT(X'EE', 64) AS BIT VARYING) "
+			 "FROM t_oos_show_part WHERE id = 1", &value_matches);
+  ASSERT_EQ (rc, NO_ERROR);
+  EXPECT_EQ (value_matches, 1);
+
+  DB_QUERY_RESULT *result = nullptr;
+  rc = show_heap_oos_query ("SHOW ALL HEAP OOS OF t_oos_show_part", &result);
+  ASSERT_EQ (rc, NO_ERROR);
+  ASSERT_NE (result, nullptr);
+
+  bool saw_root = false;
+  bool saw_p0 = false;
+  bool saw_p1 = false;
+  do
+    {
+      std::string table_name;
+      int has_oos = -1;
+      int num_recs = -1;
+
+      rc = get_string_column (result, COL_TABLE_NAME, &table_name);
+      ASSERT_EQ (rc, NO_ERROR);
+      rc = get_int_column (result, COL_HAS_OOS_FILE, &has_oos);
+      ASSERT_EQ (rc, NO_ERROR);
+      rc = get_int_column (result, COL_OOS_NUM_RECS, &num_recs);
+      ASSERT_EQ (rc, NO_ERROR);
+
+      table_name = unqualified_table_name (table_name);
+      if (table_name == "t_oos_show_part")
+	{
+	  saw_root = true;
+	  EXPECT_EQ (has_oos, 0);
+	  EXPECT_EQ (num_recs, 0);
+	}
+      else if (table_name == "t_oos_show_part__p__p0")
+	{
+	  saw_p0 = true;
+	  EXPECT_EQ (has_oos, 1);
+	  EXPECT_EQ (num_recs, 1);
+	}
+      else if (table_name == "t_oos_show_part__p__p1")
+	{
+	  saw_p1 = true;
+	  EXPECT_EQ (has_oos, 0);
+	  EXPECT_EQ (num_recs, 0);
+	}
+    }
+  while ((rc = db_query_next_tuple (result)) == DB_CURSOR_SUCCESS);
+
+  EXPECT_EQ (rc, DB_CURSOR_END);
+  EXPECT_TRUE (saw_root);
+  EXPECT_TRUE (saw_p0);
+  EXPECT_TRUE (saw_p1);
+
+  db_query_end (result);
+}
+
+TEST_F (OosSqlShow, PartitionRangeBoundaryAndNullOwnership)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part ("
+		       "id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY RANGE (id) ("
+		       "PARTITION p0 VALUES LESS THAN (10), "
+		       "PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  // Alternating destinations and NULL in one statement exercise reusable routing state.
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "(10, REPEAT(X'AA', 64)), (9, REPEAT(X'BB', 64)), "
+		       "(11, REPEAT(X'CC', 64)), (NULL, REPEAT(X'DD', 64))"), 4);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 4);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE "
+		    "(id = 9 AND data_col = CAST(REPEAT(X'BB', 64) AS BIT VARYING)) OR "
+		    "(id IS NULL AND data_col = CAST(REPEAT(X'DD', 64) AS BIT VARYING))", 2);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+		    "(id = 10 AND data_col = CAST(REPEAT(X'AA', 64) AS BIT VARYING)) OR "
+		    "(id = 11 AND data_col = CAST(REPEAT(X'CC', 64) AS BIT VARYING))", 2);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+}
+
+TEST_F (OosSqlShow, PartitionListExpressionAndFailedBatchOwnership)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part ("
+		       "id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY LIST (ABS(id)) ("
+		       "PARTITION p0 VALUES IN (1, 3), "
+		       "PARTITION p1 VALUES IN (2, NULL))"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "(-1, REPEAT(X'AA', 64)), (-2, REPEAT(X'BB', 64)), "
+		       "(-3, REPEAT(X'CC', 64)), (NULL, REPEAT(X'DD', 64))"), 4);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+
+  // A valid first row followed by a missing destination must leave no durable partial write.
+  EXPECT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "(-1, REPEAT(X'EE', 64)), (4, REPEAT(X'FF', 64))"), ER_PARTITION_NOT_EXIST);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 4);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES (-2, REPEAT(X'EE', 64))"), 1);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 5);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE "
+		    "(id = -1 AND data_col = CAST(REPEAT(X'AA', 64) AS BIT VARYING)) OR "
+		    "(id = -3 AND data_col = CAST(REPEAT(X'CC', 64) AS BIT VARYING))", 2);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+		    "(id = -2 AND data_col = CAST(REPEAT(X'BB', 64) AS BIT VARYING)) OR "
+		    "(id IS NULL AND data_col = CAST(REPEAT(X'DD', 64) AS BIT VARYING)) OR "
+		    "(id = -2 AND data_col = CAST(REPEAT(X'EE', 64) AS BIT VARYING))", 3);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 3);
+}
+
+TEST_F (OosSqlShow, PartitionHashNullOwnership)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part ("
+		       "id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY HASH (id) PARTITIONS 2"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "(1, REPEAT(X'AA', 64)), (0, REPEAT(X'BB', 64)), "
+		       "(1, REPEAT(X'CC', 64)), (NULL, REPEAT(X'DD', 64))"), 4);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 4);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE "
+		    "(id = 0 AND data_col = CAST(REPEAT(X'BB', 64) AS BIT VARYING)) OR "
+		    "(id IS NULL AND data_col = CAST(REPEAT(X'DD', 64) AS BIT VARYING))", 2);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+		    "(id = 1 AND data_col = CAST(REPEAT(X'AA', 64) AS BIT VARYING)) OR "
+		    "(id = 1 AND data_col = CAST(REPEAT(X'CC', 64) AS BIT VARYING))", 2);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+}
+
+TEST_F (OosSqlShow, PartitionRangeExpressionValidationAndMovement)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part ("
+		       "id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY RANGE (id + 1) ("
+		       "PARTITION p0 VALUES LESS THAN (10), "
+		       "PARTITION p1 VALUES LESS THAN (20))"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part__p__p0 VALUES (8, REPEAT(X'AA', 64))"), 1);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES (9, REPEAT(X'BB', 64))"), 1);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+
+  EXPECT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES (19, REPEAT(X'CC', 64))"), ER_PARTITION_NOT_EXIST);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+  EXPECT_EQ (exec_sql ("INSERT INTO t_oos_show_part__p__p0 VALUES (9, REPEAT(X'CC', 64))"),
+	     ER_INVALID_DATA_FOR_PARTITION);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+  EXPECT_EQ (exec_sql ("UPDATE t_oos_show_part__p__p0 SET id = 9"), ER_INVALID_DATA_FOR_PARTITION);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+  EXPECT_EQ (exec_sql ("UPDATE t_oos_show_part SET id = 19 WHERE id = 8"), ER_PARTITION_NOT_EXIST);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 2);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE "
+		    "id = 8 AND data_col = CAST(REPEAT(X'AA', 64) AS BIT VARYING)", 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+		    "id = 9 AND data_col = CAST(REPEAT(X'BB', 64) AS BIT VARYING)", 1);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 1);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 1);
+
+  // Root-targeted UPDATE may move a row; the sibling row stays in its existing heap.
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET id = id + 1"), 2);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 2);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0", 0);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+		    "(id = 9 AND data_col = CAST(REPEAT(X'AA', 64) AS BIT VARYING)) OR "
+		    "(id = 10 AND data_col = CAST(REPEAT(X'BB', 64) AS BIT VARYING))", 2);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+}
+
+TEST_F (OosSqlShow, PartitionListRejectsNullWithoutDestination)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part ("
+		       "id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY LIST (id) ("
+		       "PARTITION p0 VALUES IN (1), PARTITION p1 VALUES IN (2))"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  EXPECT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES (NULL, REPEAT(X'AA', 64))"),
+	     ER_PARTITION_NOT_EXIST);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 0);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES (2, REPEAT(X'BB', 64))"), 1);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+		    "id = 2 AND data_col = CAST(REPEAT(X'BB', 64) AS BIT VARYING)", 1);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 1);
+}
+
+TEST_F (OosSqlShow, PartitionUpdatePreservesDuplicateProbesAndNonKeyIncrement)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT PRIMARY KEY, counter INT DEFAULT 0, "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY RANGE(id) "
+		       "(PARTITION p0 VALUES LESS THAN(10), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES(11,0,REPEAT(X'AA',64))"), 1);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  ASSERT_EQ (exec_sql ("SELECT INCR(counter) FROM t_oos_show_part WHERE id=11"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=11 AND counter=1", 1);
+  ASSERT_GE (exec_sql ("INSERT INTO t_oos_show_part VALUES(11,0,REPEAT(X'BB',64)) "
+		       "ON DUPLICATE KEY UPDATE id=9,data_col=REPEAT(X'CC',64)"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id=9 AND counter=1 "
+		    "AND data_col=CAST(REPEAT(X'CC',64) AS BIT VARYING)", 1);
+  ASSERT_GE (exec_sql ("REPLACE INTO t_oos_show_part VALUES(9,2,REPEAT(X'DD',64))"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id=9 AND counter=2 "
+		    "AND data_col=CAST(REPEAT(X'DD',64) AS BIT VARYING)", 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 1);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+}
+
+TEST_F (OosSqlShow, PartitionUpdateStringDomains)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id VARCHAR(128) COLLATE utf8_en_ci, "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY LIST(id) "
+		       "(PARTITION p0 VALUES IN('alpha'), PARTITION p1 VALUES IN('beta'))"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES('ALPHA',REPEAT(X'AA',64))"), 1);
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET data_col=REPEAT(X'BB',64)"), 1);
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET id='BETA'"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id='beta'", 1);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 1);
+  ASSERT_GE (exec_sql ("DROP TABLE t_oos_show_part"), 0);
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id VARCHAR(4000), "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY RANGE(CHAR_LENGTH(id)) "
+		       "(PARTITION p0 VALUES LESS THAN(3000), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES(REPEAT('a',2999),REPEAT(X'AA',64))"), 1);
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET data_col=REPEAT(X'BB',64)"), 1);
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET id=REPEAT('b',3000)"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=REPEAT('b',3000) "
+		    "AND data_col=CAST(REPEAT(X'BB',64) AS BIT VARYING)", 1);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  // The compressed DEFAULT-policy key remains inline; only the forced VARBIT owns an OOS chunk.
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 1);
+}
+
+TEST_F (OosSqlShow, PartitionUpdateLegalKeysAndNullMovement)
+{
+  const char *columns[] =
+  {
+    "SMALLINT DEFAULT 11", "INTEGER DEFAULT 11", "BIGINT DEFAULT 2147483648",
+    "DATE DEFAULT DATE '2024-02-29'", "TIME DEFAULT TIME '12:34:56'",
+    "TIMESTAMP DEFAULT TIMESTAMP '2024-02-29 12:34:56'",
+    "TIMESTAMPTZ DEFAULT TIMESTAMPTZ '2024-02-29 12:34:56 +09:00'",
+    "TIMESTAMPLTZ DEFAULT TIMESTAMPLTZ '2024-02-29 12:34:56 +09:00'",
+    "DATETIME DEFAULT DATETIME '2024-02-29 12:34:56.789'",
+    "DATETIMETZ DEFAULT DATETIMETZ '2024-02-29 12:34:56.789 +09:00'",
+    "DATETIMELTZ DEFAULT DATETIMELTZ '2024-02-29 12:34:56.789 +09:00'",
+    "CHAR(8) DEFAULT 'b'", "VARCHAR(128) DEFAULT '한글 partition key'"
+  };
+  for (const char *column : columns)
+    {
+      SCOPED_TRACE (column);
+      ASSERT_GE (exec_sql ("DROP TABLE IF EXISTS t_oos_show_part"), 0);
+      std::string spec = column;
+      std::string bound = spec.substr (spec.find (" DEFAULT ") + 9);
+      if (spec.find ("CHAR(8)") == 0)
+	{
+	  bound = "'b       '";
+	}
+      std::string ddl = std::string ("CREATE TABLE t_oos_show_part (id ") + column
+			+ ", data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY LIST(id) "
+			+ "(PARTITION p0 VALUES IN (" + bound + "), PARTITION p1 VALUES IN(NULL))";
+      ASSERT_GE (exec_sql (ddl.c_str ()), 0);
+      ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part(data_col) VALUES(REPEAT(X'AA',64))"), 1);
+      ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+      ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET data_col=REPEAT(X'BB',64)"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE "
+			"id IS NOT NULL AND data_col=CAST(REPEAT(X'BB',64) AS BIT VARYING)", 1);
+      ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET id=NULL"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+			"id IS NULL AND data_col=CAST(REPEAT(X'BB',64) AS BIT VARYING)", 1);
+      expect_oos_records ("t_oos_show_part", 0, 0);
+      expect_oos_records ("t_oos_show_part__p__p1", 1, 1);
+      std::string assignment = std::string ("UPDATE t_oos_show_part SET id=") + bound;
+      ASSERT_EQ (exec_sql (assignment.c_str ()), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id IS NOT NULL", 1);
+      ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE "
+			"data_col=CAST(REPEAT(X'AA',64) AS BIT VARYING)", 1);
+    }
+}
+
+TEST_F (OosSqlShow, PartitionUpdateOldOosKeyAndRepresentation)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id VARCHAR(128) STORAGE FORCE_OUTLINE, "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE, big_col BIT VARYING) "
+		       "PARTITION BY RANGE(LOWER(SUBSTRING(id,1,1))) "
+		       "(PARTITION p0 VALUES LESS THAN('b'), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "('A123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-', "
+		       "REPEAT(X'AA',64), REPEAT(X'BB',6000))"), 1);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  ASSERT_GE (exec_sql ("ALTER TABLE t_oos_show_part ADD COLUMN added INT DEFAULT 77"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET data_col=REPEAT(X'CC',64)"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE added=77 "
+		    "AND data_col=CAST(REPEAT(X'CC',64) AS BIT VARYING)", 1);
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part "
+		       "SET id='B123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-'"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE added=77 "
+		    "AND big_col=CAST(REPEAT(X'BB',6000) AS BIT VARYING)", 1);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 3);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE added=77 "
+		    "AND data_col=CAST(REPEAT(X'AA',64) AS BIT VARYING)", 1);
+}
+
+TEST_F (OosSqlShow, PartitionUpdateLobLifecycle)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE, "
+		       "text_lob CLOB, binary_lob BLOB STORAGE FORCE_OUTLINE) PARTITION BY RANGE(id) "
+		       "(PARTITION p0 VALUES LESS THAN(10), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "(9,REPEAT(X'AA',64),CHAR_TO_CLOB('old text'),BIT_TO_BLOB(X'AABB'))"), 1);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET id=id+1"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE CLOB_TO_CHAR(text_lob)='old text' "
+		    "AND BLOB_TO_BIT(binary_lob)=X'AABB'", 1);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  // One forced VARBIT and one forced BLOB locator; the ordinary CLOB locator stays inline.
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+  ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET text_lob=CHAR_TO_CLOB('new text'), "
+		       "binary_lob=BIT_TO_BLOB(X'CCDD')"), 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE CLOB_TO_CHAR(text_lob)='new text' "
+		    "AND BLOB_TO_BIT(binary_lob)=X'CCDD'", 1);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE CLOB_TO_CHAR(text_lob)='old text' "
+		    "AND BLOB_TO_BIT(binary_lob)=X'AABB'", 1);
+}
+
+TEST_F (OosSqlShow, PartitionUpdateDedicatedIncrementsAndArithmetic)
+{
+  struct integer_case
+  {
+    const char *type;
+    const char *maximum;
+    const char *minimum;
+  };
+  const integer_case cases[] =
+  {
+    { "SMALLINT", "32767", "-32768" },
+    { "INTEGER", "2147483647", "-2147483648" },
+    { "BIGINT", "9223372036854775807", "-9223372036854775808" }
+  };
+  for (const auto &key : cases)
+    {
+      SCOPED_TRACE (key.type);
+      ASSERT_GE (exec_sql ("DROP TABLE IF EXISTS t_oos_show_part"), 0);
+      std::string ddl = std::string ("CREATE TABLE t_oos_show_part (id ") + key.type
+			+ ", data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY RANGE(id) "
+			+ "(PARTITION p0 VALUES LESS THAN(10), PARTITION p1 VALUES LESS THAN MAXVALUE)";
+      ASSERT_GE (exec_sql (ddl.c_str ()), 0);
+      ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES (9,REPEAT(X'AA',64))"), 1);
+      ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+      ASSERT_EQ (exec_sql ("SELECT INCR(id) FROM t_oos_show_part WHERE id=9"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=10 "
+			"AND data_col=CAST(REPEAT(X'AA',64) AS BIT VARYING)", 1);
+      expect_oos_records ("t_oos_show_part", 0, 0);
+      expect_oos_records ("t_oos_show_part__p__p1", 1, 1);
+      ASSERT_EQ (exec_sql ("SELECT DECR(id) FROM t_oos_show_part WHERE id=10"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id=9", 1);
+      ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET id=id+1"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=10", 1);
+      ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET data_col=REPEAT(X'BB',64)"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=10 "
+			"AND data_col=CAST(REPEAT(X'BB',64) AS BIT VARYING)", 1);
+      std::string set_max = std::string ("UPDATE t_oos_show_part SET id=") + key.maximum;
+      ASSERT_EQ (exec_sql (set_max.c_str ()), 1);
+      ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+      ASSERT_EQ (exec_sql ("SELECT INCR(id) FROM t_oos_show_part"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id=0", 1);
+      std::string set_min = std::string ("UPDATE t_oos_show_part SET id=") + key.minimum;
+      ASSERT_EQ (exec_sql (set_min.c_str ()), 1);
+      ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+      ASSERT_EQ (exec_sql ("SELECT DECR(id) FROM t_oos_show_part"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id=0", 1);
+    }
+}
+
+TEST_F (OosSqlShow, EffectiveUpdateRouteUsesMissingHistoricalKeyDefault)
+{
+  // Retain a real serialized representation from before this class acquired its partition key.
+  // No heap row is installed: this isolates the supplied-old-record contract from ALTER redistribution.
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (data_col INT DEFAULT 42)"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  OID root_oid = *db_identifier (db_find_class ("t_oos_show_part"));
+  std::string historical_bytes;
+  RECDES historical = RECDES_INITIALIZER;
+  REPR_ID historical_repr;
+  {
+    scoped_sa_server server_scope;
+    THREAD_ENTRY *thread_p = thread_get_thread_entry_info ();
+    HEAP_CACHE_ATTRINFO old_values;
+    ASSERT_EQ (heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &old_values), NO_ERROR);
+    historical_repr = old_values.last_classrepr->id;
+    record_descriptor old_record (cubmem::CSTYLE_BLOCK_ALLOCATOR);
+    bool demote = false;
+    EXPECT_EQ (heap_attrinfo_transform_to_disk_probe_oos (thread_p, &old_values, NULL, &old_record,
+	       LOB_FLAG_INCLUDE_LOB, &demote), S_SUCCESS);
+    historical = old_record.get_recdes ();
+    historical_bytes.assign (historical.data, historical.length);
+    heap_attrinfo_end (thread_p, &old_values);
+  }
+  ASSERT_GE (exec_sql ("ALTER TABLE t_oos_show_part ADD COLUMN id INT DEFAULT 11"), 0);
+  ASSERT_GE (exec_sql ("ALTER TABLE t_oos_show_part PARTITION BY RANGE(id) "
+		       "(PARTITION p0 VALUES LESS THAN(10), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  OID expected = *db_identifier (db_find_class ("t_oos_show_part__p__p1"));
+  historical.data = &historical_bytes[0];
+  historical.area_size = historical.length;
+  {
+    scoped_sa_server server_scope;
+    THREAD_ENTRY *thread_p = thread_get_thread_entry_info ();
+    HEAP_CACHE_ATTRINFO candidate, reference;
+    ASSERT_EQ (heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &candidate), NO_ERROR);
+    ASSERT_EQ (heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &reference), NO_ERROR);
+    EXPECT_NE (candidate.last_classrepr->id, historical_repr);
+    PRUNING_CONTEXT context;
+    ASSERT_EQ (partition_load_pruning_context (thread_p, &root_oid, DB_PARTITIONED_CLASS, &context), NO_ERROR);
+    OID selected = OID_INITIALIZER, reference_oid = OID_INITIALIZER;
+    HFID selected_hfid, reference_hfid;
+    int error = partition_prune_update_by_attrinfo (thread_p, &root_oid, &candidate, &historical, &context,
+		DB_PARTITIONED_CLASS, &selected, &selected_hfid, NULL);
+    EXPECT_EQ (error, NO_ERROR);
+    if (error == NO_ERROR)
+      {
+	EXPECT_TRUE (OID_EQ (&selected, &expected));
+	for (int i = 0; i < candidate.num_values; i++)
+	  {
+	    EXPECT_EQ (candidate.values[i].state, HEAP_UNINIT_ATTRVALUE);
+	    EXPECT_TRUE (DB_IS_NULL (&candidate.values[i].dbvalue));
+	  }
+	record_descriptor record (cubmem::CSTYLE_BLOCK_ALLOCATOR);
+	bool demote = false;
+	EXPECT_EQ (heap_attrinfo_transform_to_disk_probe_oos (thread_p, &reference, &historical, &record,
+		   LOB_FLAG_INCLUDE_LOB, &demote), S_SUCCESS);
+	RECDES reference_recdes = record.get_recdes ();
+	EXPECT_EQ (partition_prune_update (thread_p, &root_oid, &reference_recdes, &context, DB_PARTITIONED_CLASS,
+					   &reference_oid, &reference_hfid, NULL), NO_ERROR);
+	EXPECT_TRUE (OID_EQ (&selected, &reference_oid));
+	EXPECT_TRUE (HFID_EQ (&selected_hfid, &reference_hfid));
+	partition_clear_pruning_context (&context);
+      }
+    heap_attrinfo_end (thread_p, &reference);
+    heap_attrinfo_end (thread_p, &candidate);
+  }
+}
+
+TEST_F (OosSqlShow, EffectiveUpdateRoutePreservesOldKeyAndPendingIncrement)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT DEFAULT 2, data_col BIT VARYING "
+		       "STORAGE FORCE_OUTLINE) PARTITION BY RANGE (id) "
+		       "(PARTITION p0 VALUES LESS THAN (10), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  DB_OBJECT *child = db_find_class ("t_oos_show_part__p__p1");
+  ASSERT_NE (child, nullptr);
+  OID child_oid = *db_identifier (child);
+  ATTR_ID id = db_attribute_id (db_get_attribute (child, "id"));
+  OID p0_oid = *db_identifier (db_find_class ("t_oos_show_part__p__p0"));
+  {
+    scoped_sa_server server_scope;
+    THREAD_ENTRY *thread_p = thread_get_thread_entry_info ();
+    HEAP_CACHE_ATTRINFO old_values;
+    ASSERT_EQ (heap_attrinfo_start (thread_p, &child_oid, -1, NULL, &old_values), NO_ERROR);
+    DB_VALUE old_key;
+    db_make_int (&old_key, 10);
+    EXPECT_EQ (heap_attrinfo_set (NULL, id, &old_key, &old_values), NO_ERROR);
+    record_descriptor old_record (cubmem::CSTYLE_BLOCK_ALLOCATOR);
+    bool demote = false;
+    EXPECT_EQ (heap_attrinfo_transform_to_disk_probe_oos (thread_p, &old_values, NULL, &old_record,
+	       LOB_FLAG_INCLUDE_LOB, &demote), S_SUCCESS);
+    RECDES old_recdes = old_record.get_recdes ();
+    // Unchanged, pending INCR, pending DECR, and an already evaluated ordinary assignment.
+    for (int mode = 0; mode < 4; mode++)
+      {
+	SCOPED_TRACE (mode);
+	HEAP_CACHE_ATTRINFO candidate;
+	EXPECT_EQ (heap_attrinfo_start (thread_p, &child_oid, -1, NULL, &candidate), NO_ERROR);
+	HEAP_ATTRVALUE *key = heap_attrvalue_locate (id, &candidate);
+	key->do_increment = mode == 1 ? 1 : mode == 2 ? -1 : 0;
+	if (mode == 3)
+	  {
+	    DB_VALUE assigned;
+	    db_make_int (&assigned, 9);
+	    EXPECT_EQ (heap_attrinfo_set (NULL, id, &assigned, &candidate), NO_ERROR);
+	  }
+	const auto state = key->state;
+	auto *read_repr = candidate.read_classrepr;
+	OID selected = OID_INITIALIZER;
+	HFID selected_hfid;
+	int error = partition_prune_update_by_attrinfo (thread_p, &child_oid, &candidate, &old_recdes, NULL,
+		    DB_PARTITIONED_CLASS, &selected, &selected_hfid, NULL);
+	EXPECT_EQ (error, NO_ERROR);
+	if (error == NO_ERROR)
+	  {
+	    EXPECT_TRUE (OID_EQ (&selected, mode < 2 ? &child_oid : &p0_oid));
+	  }
+	EXPECT_EQ (candidate.read_classrepr, read_repr);
+	EXPECT_EQ (key->state, state);
+	EXPECT_EQ (key->do_increment, mode == 1 ? 1 : mode == 2 ? -1 : 0);
+	if (mode == 3)
+	  {
+	    EXPECT_EQ (db_get_int (&key->dbvalue), 9);
+	  }
+	else
+	  {
+	    EXPECT_TRUE (DB_IS_NULL (&key->dbvalue));
+	  }
+	if (error == NO_ERROR)
+	  {
+	    // Repeating selection must not consume the pending operation. The first real transform must.
+	    EXPECT_EQ (partition_prune_update_by_attrinfo (thread_p, &child_oid, &candidate, &old_recdes, NULL,
+		       DB_PARTITIONED_CLASS, &selected, &selected_hfid, NULL), NO_ERROR);
+	    record_descriptor actual_record (cubmem::CSTYLE_BLOCK_ALLOCATOR);
+	    EXPECT_EQ (heap_attrinfo_transform_to_disk_with_oos_owner (thread_p, &candidate, &old_recdes,
+		       &actual_record, LOB_FLAG_INCLUDE_LOB,
+		       &selected), S_SUCCESS);
+	    EXPECT_EQ (db_get_int (&key->dbvalue), mode == 0 ? 10 : mode == 1 ? 11 : 9);
+	    OID final_oid = OID_INITIALIZER;
+	    HFID final_hfid;
+	    RECDES actual = actual_record.get_recdes ();
+	    EXPECT_EQ (partition_prune_update (thread_p, &child_oid, &actual, NULL, DB_PARTITIONED_CLASS,
+					       &final_oid, &final_hfid, NULL), NO_ERROR);
+	    EXPECT_TRUE (OID_EQ (&selected, &final_oid));
+	    EXPECT_TRUE (HFID_EQ (&selected_hfid, &final_hfid));
+	  }
+	heap_attrinfo_end (thread_p, &candidate);
+      }
+    heap_attrinfo_end (thread_p, &old_values);
+  }
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+}
+
+TEST_F (OosSqlShow, PartitionPreparationFailuresRollBackAndAllowNextWrite)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT, "
+		       "a BIT VARYING STORAGE FORCE_OUTLINE, b BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY RANGE (id) (PARTITION p0 VALUES LESS THAN (10), "
+		       "PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_GE (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "(1, REPEAT(X'AA',64), REPEAT(X'BB',64)), "
+		       "(11, REPEAT(X'AA',64), REPEAT(X'BB',64))"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+
+  for (bool update :
+       {
+	       false, true
+       })
+    {
+      for (int failure = 0; failure < 4; failure++)
+	{
+	  SCOPED_TRACE (failure);
+	  SCOPED_TRACE (update ? "moving UPDATE" : "INSERT");
+	  // A multi-chunk second value prevents both values publishing in one small-page batch.
+	  if (failure == 0)
+	    {
+	      oos_test_fail_insert_many_after_publications (1);
+	    }
+	  else if (failure == 1)
+	    {
+	      bridge_heap_attrinfo_fail_after_oos_publication_reset_once ();
+	    }
+	  else if (failure == 2)
+	    {
+	      heap_oos_test_fail_before_vfid_lookup_once ();
+	    }
+	  else
+	    {
+	      oos_test_throw_bad_alloc_on_next_oid_publication ();
+	    }
+	  int error = exec_sql (update
+				? "UPDATE t_oos_show_part SET id=12, a=REPEAT(X'CC',64), "
+				"b=REPEAT(X'DD',20000) WHERE id=1"
+				: "INSERT INTO t_oos_show_part VALUES (12, REPEAT(X'CC',64), REPEAT(X'DD',20000))");
+	  oos_test_disarm_insert_publication_failures ();
+	  bridge_heap_attrinfo_disarm_publication_reset_failure ();
+	  heap_oos_test_disarm_fail_before_vfid_lookup ();
+	  EXPECT_EQ (error, failure == 3 ? ER_OUT_OF_VIRTUAL_MEMORY : ER_GENERIC_ERROR);
+	  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+
+	  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part WHERE id IN (1,11) "
+			    "AND a=CAST(REPEAT(X'AA',64) AS BIT VARYING) "
+			    "AND b=CAST(REPEAT(X'BB',64) AS BIT VARYING)", 2);
+	  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part WHERE id=12", 0);
+	  expect_oos_records ("t_oos_show_part", 0, 0);
+	  expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
+	  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+
+	  ASSERT_GE (exec_sql ("INSERT INTO t_oos_show_part VALUES (12, REPEAT(X'CC',64), REPEAT(X'DD',64))"), 0);
+	  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=12 "
+			    "AND a=CAST(REPEAT(X'CC',64) AS BIT VARYING) "
+			    "AND b=CAST(REPEAT(X'DD',64) AS BIT VARYING)", 1);
+	  expect_oos_records ("t_oos_show_part__p__p1", 1, 4);
+	  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+	  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+	}
+    }
+}
+
+TEST_F (OosSqlShow, PartitionLobPreparationAndIndexFailuresPreserveCommittedValues)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT PRIMARY KEY, "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE, text_lob CLOB, "
+		       "binary_lob BLOB STORAGE FORCE_OUTLINE) PARTITION BY RANGE(id) "
+		       "(PARTITION p0 VALUES LESS THAN(10), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "(1,REPEAT(X'AA',64),CHAR_TO_CLOB('old text'),BIT_TO_BLOB(X'AABB')), "
+		       "(11,REPEAT(X'AA',64),CHAR_TO_CLOB('old text'),BIT_TO_BLOB(X'AABB'))"), 2);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+
+  for (int failure = 0; failure < 3; failure++)
+    {
+      SCOPED_TRACE (failure);
+      if (failure == 0)
+	{
+	  // Fail after OOS payload preparation, which copies the written BLOB locator.
+	  heap_oos_test_fail_before_vfid_lookup_once ();
+	}
+      int error = exec_sql (failure == 0
+			    ? "UPDATE t_oos_show_part SET id=12, text_lob=CHAR_TO_CLOB('new text'), "
+			    "binary_lob=BIT_TO_BLOB(X'CCDD') WHERE id=1"
+			    : failure == 1
+			    ? "UPDATE t_oos_show_part SET id=11, text_lob=CHAR_TO_CLOB('new text'), "
+			    "binary_lob=BIT_TO_BLOB(X'CCDD') WHERE id=1"
+			    : "UPDATE t_oos_show_part SET id=11 WHERE id=1");
+      heap_oos_test_disarm_fail_before_vfid_lookup ();
+      EXPECT_EQ (error, failure == 0 ? ER_GENERIC_ERROR : ER_BTREE_UNIQUE_FAILED);
+      ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part WHERE id IN (1,11) "
+			"AND CLOB_TO_CHAR(text_lob)='old text' AND BLOB_TO_BIT(binary_lob)=X'AABB'", 2);
+      expect_oos_records ("t_oos_show_part", 0, 0);
+      expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
+      expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+      ASSERT_EQ (exec_sql ("UPDATE t_oos_show_part SET id=12, text_lob=CHAR_TO_CLOB('next text'), "
+			   "binary_lob=BIT_TO_BLOB(X'EEFF') WHERE id=1"), 1);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=12 "
+			"AND CLOB_TO_CHAR(text_lob)='next text' AND BLOB_TO_BIT(binary_lob)=X'EEFF'", 1);
+      expect_oos_records ("t_oos_show_part__p__p1", 1, 4);
+      ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+    }
+}
+
+TEST_F (OosSqlShow, EffectiveKeyCodecFailureClearsOutputAndPreservesAssignment)
+{
+  // Fault only the codec on a private attribute/domain copy; never mutate cached schema metadata.
+  class failing_codec : public PR_TYPE
+  {
+    public:
+      failing_codec (const PR_TYPE &original, bool fail_read) : PR_TYPE (original)
+      {
+	if (fail_read)
+	  {
+	    f_data_readval = [] (struct or_buf *, DB_VALUE *out, TP_DOMAIN *, int, bool, char *, int)
+	    {
+	      DB_VALUE partial;
+	      db_make_string (&partial, "partially decoded key");
+	      pr_clone_value (&partial, out);
+	      return ER_FAILED;
+	    };
+	  }
+	else
+	  {
+	    f_data_writeval = [] (struct or_buf *, DB_VALUE *)
+	    {
+	      return ER_FAILED;
+	    };
+	  }
+      }
+  };
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id VARCHAR(512), data_col INT) "
+		       "PARTITION BY RANGE(LENGTH(id)) (PARTITION p0 VALUES LESS THAN(10), "
+		       "PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  DB_OBJECT *root = db_find_class ("t_oos_show_part");
+  ASSERT_NE (root, nullptr);
+  OID root_oid = *db_identifier (root);
+  DB_ATTRIBUTE *attribute = db_get_attribute (root, "id");
+  ASSERT_NE (attribute, nullptr);
+  ATTR_ID key_id = db_attribute_id (attribute);
+  std::string text;
+  unsigned int random = 12345;
+  for (int i = 0; i < 300; i++)
+    {
+      random = random * 1664525U + 1013904223U;
+      text.push_back ('!' + ((random >> 16) % 90));
+    }
+  {
+    scoped_sa_server server_scope;
+    THREAD_ENTRY *thread_p = thread_get_thread_entry_info ();
+    HEAP_CACHE_ATTRINFO cache;
+    ASSERT_EQ (heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &cache), NO_ERROR);
+    DB_VALUE assigned;
+    db_make_string (&assigned, text.c_str ());
+    EXPECT_EQ (heap_attrinfo_set (NULL, key_id, &assigned, &cache), NO_ERROR);
+    HEAP_ATTRVALUE *slot = heap_attrvalue_locate (key_id, &cache);
+    OR_ATTRIBUTE *original = slot->last_attrepr;
+    for (bool fail_read :
+	 {
+		 false, true
+	 })
+      {
+	OR_ATTRIBUTE local_attribute {};
+	local_attribute.id = original->id;
+	local_attribute.type = original->type;
+	local_attribute.is_fixed = original->is_fixed;
+	TP_DOMAIN local_domain = *original->domain;
+	failing_codec codec (*original->domain->type, fail_read);
+	local_domain.type = &codec;
+	local_attribute.domain = &local_domain;
+	slot->last_attrepr = &local_attribute;
+	DB_VALUE key;
+	db_make_null (&key);
+	int error = heap_attrinfo_get_effective_key (thread_p, &cache, key_id, NULL, &key);
+	slot->last_attrepr = original;
+	EXPECT_EQ (error, ER_FAILED);
+	EXPECT_TRUE (DB_IS_NULL (&key));
+	pr_clear_value (&key);
+	EXPECT_EQ (slot->state, HEAP_WRITTEN_ATTRVALUE);
+	EXPECT_EQ (std::string (db_get_string (&slot->dbvalue), db_get_string_size (&slot->dbvalue)), text);
+	db_make_null (&key);
+	EXPECT_EQ (heap_attrinfo_get_effective_key (thread_p, &cache, key_id, NULL, &key), NO_ERROR);
+	if (!DB_IS_NULL (&key))
+	  {
+	    EXPECT_EQ (std::string (db_get_string (&key), db_get_string_size (&key)), text);
+	  }
+	pr_clear_value (&key);
+      }
+    heap_attrinfo_end (thread_p, &cache);
+  }
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+}
+
+TEST_F (OosSqlShow, EffectiveRoutingFailurePreservesAssignmentsAndPublication)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY RANGE (id) (PARTITION p0 VALUES LESS THAN (10), "
+		       "PARTITION p1 VALUES LESS THAN (20))"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  DB_OBJECT *root = db_find_class ("t_oos_show_part");
+  ASSERT_NE (root, nullptr);
+  OID root_oid = *db_identifier (root);
+  ATTR_ID key_id = db_attribute_id (db_get_attribute (root, "id"));
+  ATTR_ID payload_id = db_attribute_id (db_get_attribute (root, "data_col"));
+  OID p0_oid = *db_identifier (db_find_class ("t_oos_show_part__p__p0"));
+  OID p1_oid = *db_identifier (db_find_class ("t_oos_show_part__p__p1"));
+  {
+    scoped_sa_server server_scope;
+    THREAD_ENTRY *thread_p = thread_get_thread_entry_info ();
+    HEAP_CACHE_ATTRINFO cache;
+    ASSERT_EQ (heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &cache), NO_ERROR);
+    PRUNING_CONTEXT context;
+    partition_init_pruning_context (&context);
+    LOG_TDES *tdes = LOG_FIND_TDES (LOG_FIND_THREAD_TRAN_INDEX (thread_p));
+    ASSERT_NE (tdes, nullptr);
+    const LOG_LSA marker { 876543, 123 };
+    thread_p->oos_oids.clear ();
+    tdes->oos_insert_lsa_queue.clear ();
+    thread_p->oos_oids.push_back (root_oid);
+    tdes->oos_insert_lsa_queue.push (marker);
+    for (int input :
+	 {
+		 11, 21, 1, 21, 11
+	 })
+      {
+	DB_VALUE assigned;
+	db_make_int (&assigned, input);
+	EXPECT_EQ (heap_attrinfo_set (NULL, key_id, &assigned, &cache), NO_ERROR);
+	OID destination = OID_INITIALIZER;
+	HFID hfid;
+	int error = partition_prune_insert_by_attrinfo (thread_p, &root_oid, &cache, &context,
+		    DB_PARTITIONED_CLASS, &destination, &hfid, NULL);
+	EXPECT_EQ (error, input == 21 ? ER_PARTITION_NOT_EXIST : NO_ERROR);
+	if (error == NO_ERROR)
+	  {
+	    EXPECT_TRUE (OID_EQ (&destination, input < 10 ? &p0_oid : &p1_oid));
+	  }
+	EXPECT_EQ (db_get_int (&heap_attrvalue_locate (key_id, &cache)->dbvalue), input);
+	EXPECT_EQ (heap_attrvalue_locate (key_id, &cache)->state, HEAP_WRITTEN_ATTRVALUE);
+	EXPECT_EQ (heap_attrvalue_locate (payload_id, &cache)->state, HEAP_UNINIT_ATTRVALUE);
+	EXPECT_EQ (thread_p->oos_oids.size (), 1U);
+	if (!thread_p->oos_oids.empty ())
+	  {
+	    EXPECT_TRUE (OID_EQ (&thread_p->oos_oids.front (), &root_oid));
+	  }
+	EXPECT_EQ (tdes->oos_insert_lsa_queue.size (), 1U);
+	if (!tdes->oos_insert_lsa_queue.is_empty ())
+	  {
+	    EXPECT_TRUE (LSA_EQ (&tdes->oos_insert_lsa_queue.front (), &marker));
+	  }
+	er_clear ();
+      }
+    EXPECT_EQ (heap_oos_begin_insert_publication (thread_p), S_SUCCESS);
+    partition_clear_pruning_context (&context);
+    heap_attrinfo_end (thread_p, &cache);
+  }
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 0);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+}
+
+TEST_F (OosSqlShow, EffectiveInsertRoutePreservesOmittedAssignments)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part ("
+		       "id INT DEFAULT 11, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY RANGE (id) (PARTITION p0 VALUES LESS THAN (10), "
+		       "PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  DB_OBJECT *root = db_find_class ("t_oos_show_part");
+  ASSERT_NE (root, nullptr);
+  OID root_oid = *db_identifier (root);
+  DB_OBJECT *child = db_find_class ("t_oos_show_part__p__p1");
+  ASSERT_NE (child, nullptr);
+  OID expected_oid = *db_identifier (child);
+  {
+    scoped_sa_server server_scope;
+    THREAD_ENTRY *thread_p = thread_get_thread_entry_info ();
+    HEAP_CACHE_ATTRINFO candidate;
+    HEAP_CACHE_ATTRINFO reference;
+    ASSERT_EQ (heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &candidate), NO_ERROR);
+    int reference_error = heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &reference);
+    if (reference_error != NO_ERROR)
+      {
+	heap_attrinfo_end (thread_p, &candidate);
+	FAIL () << reference_error;
+      }
+
+    OID selected_oid = OID_INITIALIZER, reference_oid = OID_INITIALIZER;
+    HFID selected_hfid, reference_hfid;
+    int error = partition_prune_insert_by_attrinfo (thread_p, &root_oid, &candidate, NULL, DB_PARTITIONED_CLASS,
+		&selected_oid, &selected_hfid, NULL);
+    EXPECT_EQ (error, NO_ERROR);
+    if (error == NO_ERROR)
+      {
+	EXPECT_TRUE (OID_EQ (&selected_oid, &expected_oid));
+      }
+    for (int i = 0; i < candidate.num_values; i++)
+      {
+	EXPECT_EQ (candidate.values[i].state, HEAP_UNINIT_ATTRVALUE);
+	EXPECT_TRUE (DB_IS_NULL (&candidate.values[i].dbvalue));
+      }
+
+    // The reference owns separate values: the inline probe may initialize and mutate them.
+    record_descriptor record (cubmem::CSTYLE_BLOCK_ALLOCATOR);
+    bool would_demote = false;
+    SCAN_CODE scan = heap_attrinfo_transform_to_disk_probe_oos (thread_p, &reference, NULL, &record,
+		     LOB_FLAG_INCLUDE_LOB, &would_demote);
+    EXPECT_EQ (scan, S_SUCCESS);
+    if (scan == S_SUCCESS)
+      {
+	RECDES recdes = record.get_recdes ();
+	EXPECT_EQ (partition_prune_insert (thread_p, &root_oid, &recdes, NULL, NULL, DB_PARTITIONED_CLASS,
+					   &reference_oid, &reference_hfid, NULL), NO_ERROR);
+	EXPECT_TRUE (OID_EQ (&reference_oid, &expected_oid));
+	if (error == NO_ERROR)
+	  {
+	    EXPECT_TRUE (OID_EQ (&selected_oid, &reference_oid));
+	    EXPECT_TRUE (HFID_EQ (&selected_hfid, &reference_hfid));
+	  }
+      }
+    heap_attrinfo_end (thread_p, &reference);
+    heap_attrinfo_end (thread_p, &candidate);
+  }
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 0);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+}
+
+TEST_F (OosSqlShow, EffectiveInsertRoutePreservesAssignedChar)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part ("
+		       "id CHAR(8), data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY LIST (id) (PARTITION p0 VALUES IN ('a       '), "
+		       "PARTITION p1 VALUES IN ('b       '))"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  DB_OBJECT *root = db_find_class ("t_oos_show_part");
+  ASSERT_NE (root, nullptr);
+  OID root_oid = *db_identifier (root);
+  DB_ATTRIBUTE *key_attribute = db_get_attribute (root, "id");
+  ASSERT_NE (key_attribute, nullptr);
+  ATTR_ID key_id = db_attribute_id (key_attribute);
+  DB_OBJECT *child = db_find_class ("t_oos_show_part__p__p1");
+  ASSERT_NE (child, nullptr);
+  OID expected_oid = *db_identifier (child);
+  {
+    scoped_sa_server server_scope;
+    THREAD_ENTRY *thread_p = thread_get_thread_entry_info ();
+    HEAP_CACHE_ATTRINFO candidate;
+    HEAP_CACHE_ATTRINFO reference;
+    ASSERT_EQ (heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &candidate), NO_ERROR);
+    int error = heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &reference);
+    if (error != NO_ERROR)
+      {
+	heap_attrinfo_end (thread_p, &candidate);
+	FAIL () << error;
+      }
+    DB_VALUE assigned;
+    db_make_string (&assigned, "b");
+    EXPECT_EQ (heap_attrinfo_set (NULL, key_id, &assigned, &candidate), NO_ERROR);
+    EXPECT_EQ (heap_attrinfo_set (NULL, key_id, &assigned, &reference), NO_ERROR);
+    int key_index = candidate.values[0].attrid == key_id ? 0 : 1;
+    const HEAP_ATTRVALUE &source = candidate.values[key_index];
+    int source_size = db_get_string_size (&source.dbvalue);
+    std::string source_bytes (db_get_string (&source.dbvalue), source_size);
+    auto source_state = source.state;
+
+    OID selected_oid = OID_INITIALIZER, reference_oid = OID_INITIALIZER;
+    HFID selected_hfid, reference_hfid;
+    error = partition_prune_insert_by_attrinfo (thread_p, &root_oid, &candidate, NULL, DB_PARTITIONED_CLASS,
+	    &selected_oid, &selected_hfid, NULL);
+    EXPECT_EQ (error, NO_ERROR);
+    if (error == NO_ERROR)
+      {
+	EXPECT_TRUE (OID_EQ (&selected_oid, &expected_oid));
+      }
+    EXPECT_EQ (source.state, source_state);
+    EXPECT_EQ (db_get_string_size (&source.dbvalue), source_size);
+    EXPECT_EQ (std::string (db_get_string (&source.dbvalue), db_get_string_size (&source.dbvalue)), source_bytes);
+    EXPECT_EQ (candidate.values[1 - key_index].state, HEAP_UNINIT_ATTRVALUE);
+
+    record_descriptor record (cubmem::CSTYLE_BLOCK_ALLOCATOR);
+    bool would_demote = false;
+    SCAN_CODE scan = heap_attrinfo_transform_to_disk_probe_oos (thread_p, &reference, NULL, &record,
+		     LOB_FLAG_INCLUDE_LOB, &would_demote);
+    EXPECT_EQ (scan, S_SUCCESS);
+    if (scan == S_SUCCESS)
+      {
+	RECDES recdes = record.get_recdes ();
+	EXPECT_EQ (partition_prune_insert (thread_p, &root_oid, &recdes, NULL, NULL, DB_PARTITIONED_CLASS,
+					   &reference_oid, &reference_hfid, NULL), NO_ERROR);
+	EXPECT_TRUE (OID_EQ (&reference_oid, &expected_oid));
+	if (error == NO_ERROR)
+	  {
+	    EXPECT_TRUE (OID_EQ (&selected_oid, &reference_oid));
+	    EXPECT_TRUE (HFID_EQ (&selected_hfid, &reference_hfid));
+	  }
+      }
+    heap_attrinfo_end (thread_p, &reference);
+    heap_attrinfo_end (thread_p, &candidate);
+  }
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+}
+
+TEST_F (OosSqlShow, EffectiveInsertRouteLegalKeyDefaults)
+{
+  const char *columns[] =
+  {
+    "SMALLINT DEFAULT 11", "INTEGER DEFAULT 11", "BIGINT DEFAULT 2147483648",
+    "DATE DEFAULT DATE '2024-02-29'", "TIME DEFAULT TIME '12:34:56'",
+    "TIMESTAMP DEFAULT TIMESTAMP '2024-02-29 12:34:56'",
+    "TIMESTAMPTZ DEFAULT TIMESTAMPTZ '2024-02-29 12:34:56 +09:00'",
+    "TIMESTAMPLTZ DEFAULT TIMESTAMPLTZ '2024-02-29 12:34:56 +09:00'",
+    "DATETIME DEFAULT DATETIME '2024-02-29 12:34:56.789'",
+    "DATETIMETZ DEFAULT DATETIMETZ '2024-02-29 12:34:56.789 +09:00'",
+    "DATETIMELTZ DEFAULT DATETIMELTZ '2024-02-29 12:34:56.789 +09:00'",
+    "CHAR(8) DEFAULT 'b'", "VARCHAR(128) DEFAULT '한글 partition key'"
+  };
+  for (const char *column : columns)
+    {
+      SCOPED_TRACE (column);
+      ASSERT_GE (exec_sql ("DROP TABLE IF EXISTS t_oos_show_part"), 0);
+      std::string column_spec = column;
+      std::string bound = column_spec.substr (column_spec.find (" DEFAULT ") + 9);
+      if (column_spec.find ("CHAR(8)") == 0)
+	{
+	  bound = "'b       '";
+	}
+      std::string ddl = std::string ("CREATE TABLE t_oos_show_part (id ") + column
+			+ ", data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY LIST (id) ("
+			+ "PARTITION p0 VALUES IN (" + bound + "), PARTITION p1 VALUES IN (NULL))";
+      ASSERT_GE (exec_sql (ddl.c_str ()), 0);
+      ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+      DB_OBJECT *root = db_find_class ("t_oos_show_part");
+      ASSERT_NE (root, nullptr);
+      OID root_oid = *db_identifier (root);
+      {
+	scoped_sa_server server_scope;
+	THREAD_ENTRY *thread_p = thread_get_thread_entry_info ();
+	HEAP_CACHE_ATTRINFO candidate;
+	HEAP_CACHE_ATTRINFO reference;
+	ASSERT_EQ (heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &candidate), NO_ERROR);
+	int error = heap_attrinfo_start (thread_p, &root_oid, -1, NULL, &reference);
+	if (error != NO_ERROR)
+	  {
+	    heap_attrinfo_end (thread_p, &candidate);
+	    FAIL () << error;
+	  }
+	OID selected_oid = OID_INITIALIZER, reference_oid = OID_INITIALIZER;
+	HFID selected_hfid, reference_hfid;
+	error = partition_prune_insert_by_attrinfo (thread_p, &root_oid, &candidate, NULL, DB_PARTITIONED_CLASS,
+		&selected_oid, &selected_hfid, NULL);
+	EXPECT_EQ (error, NO_ERROR);
+	for (int i = 0; i < candidate.num_values; i++)
+	  {
+	    EXPECT_EQ (candidate.values[i].state, HEAP_UNINIT_ATTRVALUE);
+	    EXPECT_TRUE (DB_IS_NULL (&candidate.values[i].dbvalue));
+	  }
+	record_descriptor record (cubmem::CSTYLE_BLOCK_ALLOCATOR);
+	bool would_demote = false;
+	SCAN_CODE scan = heap_attrinfo_transform_to_disk_probe_oos (thread_p, &reference, NULL, &record,
+			 LOB_FLAG_INCLUDE_LOB, &would_demote);
+	EXPECT_EQ (scan, S_SUCCESS);
+	if (scan == S_SUCCESS)
+	  {
+	    RECDES recdes = record.get_recdes ();
+	    EXPECT_EQ (partition_prune_insert (thread_p, &root_oid, &recdes, NULL, NULL, DB_PARTITIONED_CLASS,
+					       &reference_oid, &reference_hfid, NULL), NO_ERROR);
+	    if (error == NO_ERROR)
+	      {
+		EXPECT_TRUE (OID_EQ (&selected_oid, &reference_oid));
+		EXPECT_TRUE (HFID_EQ (&selected_hfid, &reference_hfid));
+	      }
+	  }
+	heap_attrinfo_end (thread_p, &reference);
+	heap_attrinfo_end (thread_p, &candidate);
+      }
+      expect_oos_records ("t_oos_show_part", 0, 0);
+      expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+      expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+    }
+}
+
+TEST_F (OosSqlShow, PartitionInsertLegalKeySqlMatrix)
+{
+  struct key_case
+  {
+    const char *type;
+    const char *value;
+  };
+  const key_case cases[] =
+  {
+    { "SMALLINT", "11" }, { "INTEGER", "11" }, { "BIGINT", "2147483648" },
+    { "DATE", "DATE '2024-02-29'" }, { "TIME", "TIME '12:34:56'" },
+    { "TIMESTAMP", "TIMESTAMP '2024-02-29 12:34:56'" },
+    { "TIMESTAMPTZ", "TIMESTAMPTZ '2024-02-29 12:34:56 +09:00'" },
+    { "TIMESTAMPLTZ", "TIMESTAMPLTZ '2024-02-29 12:34:56 +09:00'" },
+    { "DATETIME", "DATETIME '2024-02-29 12:34:56.789'" },
+    { "DATETIMETZ", "DATETIMETZ '2024-02-29 12:34:56.789 +09:00'" },
+    { "DATETIMELTZ", "DATETIMELTZ '2024-02-29 12:34:56.789 +09:00'" },
+    { "CHAR(8)", "'b'" }, { "VARCHAR(128)", "'한글 partition key'" }
+  };
+  for (const key_case &key : cases)
+    {
+      SCOPED_TRACE (key.type);
+      ASSERT_GE (exec_sql ("DROP TABLE IF EXISTS t_oos_show_part"), 0);
+      std::string ddl = std::string ("CREATE TABLE t_oos_show_part (id ") + key.type + " DEFAULT " + key.value
+			+ ", data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY HASH (id) PARTITIONS 2";
+      ASSERT_GE (exec_sql (ddl.c_str ()), 0);
+      std::string insert = std::string ("INSERT INTO t_oos_show_part VALUES (") + key.value
+			   + ", REPEAT(X'AA', 64)), (NULL, REPEAT(X'BB', 64)), (" + key.value
+			   + ", REPEAT(X'CC', 64))";
+      ASSERT_EQ (exec_sql (insert.c_str ()), 3);
+      ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part (data_col) VALUES (REPEAT(X'DD', 64))"), 1);
+      ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+      std::string matching = std::string ("SELECT COUNT(*) FROM t_oos_show_part WHERE id = CAST(") + key.value
+			     + " AS " + key.type + ") AND data_col IN (CAST(REPEAT(X'AA', 64) AS BIT VARYING), "
+			     + "CAST(REPEAT(X'CC', 64) AS BIT VARYING), CAST(REPEAT(X'DD', 64) AS BIT VARYING))";
+      expect_sql_count (matching.c_str (), 3);
+      expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id IS NULL "
+			"AND data_col = CAST(REPEAT(X'BB', 64) AS BIT VARYING)", 1);
+      int p0_count = -1, p1_count = -1;
+      ASSERT_EQ (fetch_single_int ("SELECT COUNT(*) FROM t_oos_show_part__p__p0", &p0_count), NO_ERROR);
+      ASSERT_EQ (fetch_single_int ("SELECT COUNT(*) FROM t_oos_show_part__p__p1", &p1_count), NO_ERROR);
+      EXPECT_EQ (p0_count + p1_count, 4);
+      // Retain literal partition observations for the independent pinned-library run.
+      printf ("LEGAL_KEY %s p0=%d p1=%d\n", key.type, p0_count, p1_count);
+      expect_oos_records ("t_oos_show_part", 0, 0);
+      expect_oos_records ("t_oos_show_part__p__p0", p0_count > 0 ? 1 : 0, p0_count);
+      expect_oos_records ("t_oos_show_part__p__p1", p1_count > 0 ? 1 : 0, p1_count);
+    }
+}
+
+TEST_F (OosSqlShow, PartitionInsertOwnsExternalKeyAndMultiplePayloads)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part ("
+		       "id VARCHAR(128) STORAGE FORCE_OUTLINE, "
+		       "small_col BIT VARYING STORAGE FORCE_OUTLINE, large_col BIT VARYING) "
+		       "PARTITION BY RANGE (LOWER(SUBSTRING(id, 1, 1))) ("
+		       "PARTITION p0 VALUES LESS THAN ('b'), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES "
+		       "('A123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-', "
+		       "REPEAT(X'AA',64), REPEAT(X'BB',6000)), "
+		       "('B123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-', "
+		       "REPEAT(X'CC',64), REPEAT(X'DD',6000))"), 2);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE "
+		    "id = 'A123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-' AND "
+		    "small_col = CAST(REPEAT(X'AA',64) AS BIT VARYING) AND "
+		    "large_col = CAST(REPEAT(X'BB',6000) AS BIT VARYING)", 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+		    "id = 'B123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-' AND "
+		    "small_col = CAST(REPEAT(X'CC',64) AS BIT VARYING) AND "
+		    "large_col = CAST(REPEAT(X'DD',6000) AS BIT VARYING)", 1);
+  // The key and both payloads each fit one OOS chunk; the ordinary VARBIT cannot be compressed.
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 3);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 3);
+}
+
+TEST_F (OosSqlShow, PartitionInsertRetainsBigoneRejectionBeforeOos)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT, fixed_col BIT(140000), "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY RANGE(id) ("
+		       "PARTITION p0 VALUES LESS THAN(10), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  EXPECT_LT (exec_sql ("INSERT INTO t_oos_show_part VALUES(11,B'1',REPEAT(X'AA',64))"), 0);
+  EXPECT_EQ (er_errid (), ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE);
+  ASSERT_EQ (db_abort_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part", 0);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+  // Without an OOS value the existing whole-record overflow path remains supported.
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES(11,B'1',NULL)"), 1);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=11 AND data_col IS NULL", 1);
+  expect_oos_records ("t_oos_show_part__p__p1", 0, 0);
+}
+
+TEST_F (OosSqlShow, PartitionInsertGeneratedKeysAndDomainConversion)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id INT AUTO_INCREMENT(9,1), "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY RANGE(id) ("
+		       "PARTITION p0 VALUES LESS THAN(10), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part(data_col) VALUES(REPEAT(X'AA',64)),(REPEAT(X'BB',64))"), 2);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES('11',REPEAT(X'CC',64))"), 1);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE "
+		    "id=9 AND data_col=CAST(REPEAT(X'AA',64) AS BIT VARYING)", 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE "
+		    "(id=10 AND data_col=CAST(REPEAT(X'BB',64) AS BIT VARYING)) OR "
+		    "(id=11 AND data_col=CAST(REPEAT(X'CC',64) AS BIT VARYING))", 2);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 1);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+}
+
+TEST_F (OosSqlShow, PartitionInsertDynamicDefault)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id DATE DEFAULT CURRENT_DATE, "
+		       "expected_date DATE, data_col BIT VARYING STORAGE FORCE_OUTLINE) "
+		       "PARTITION BY HASH(id) PARTITIONS 2"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part(expected_date,data_col) VALUES"
+		       "(CURRENT_DATE,REPEAT(X'AA',64)),(CURRENT_DATE,REPEAT(X'BB',64))"), 2);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part WHERE id=expected_date AND "
+		    "data_col IN (CAST(REPEAT(X'AA',64) AS BIT VARYING),CAST(REPEAT(X'BB',64) AS BIT VARYING))", 2);
+  int p0_count = -1, p1_count = -1;
+  ASSERT_EQ (fetch_single_int ("SELECT COUNT(*) FROM t_oos_show_part__p__p0", &p0_count), NO_ERROR);
+  ASSERT_EQ (fetch_single_int ("SELECT COUNT(*) FROM t_oos_show_part__p__p1", &p1_count), NO_ERROR);
+  EXPECT_EQ (p0_count + p1_count, 2);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", p0_count > 0 ? 1 : 0, p0_count);
+  expect_oos_records ("t_oos_show_part__p__p1", p1_count > 0 ? 1 : 0, p1_count);
+}
+
+TEST_F (OosSqlShow, PartitionInsertUsesColumnCollation)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id VARCHAR(20) COLLATE utf8_en_ci, "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY LIST(id) ("
+		       "PARTITION p0 VALUES IN('alpha'), PARTITION p1 VALUES IN('beta'))"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES('BETA',REPEAT(X'AA',64)),"
+		       "('AlPhA',REPEAT(X'BB',64)),('beta',REPEAT(X'CC',64))"), 3);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id='alpha' AND "
+		    "data_col=CAST(REPEAT(X'BB',64) AS BIT VARYING)", 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id='beta' AND "
+		    "data_col IN (CAST(REPEAT(X'AA',64) AS BIT VARYING),CAST(REPEAT(X'CC',64) AS BIT VARYING))", 2);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 1);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+}
+
+TEST_F (OosSqlShow, PartitionInsertCompressedExpressionKey)
+{
+  ASSERT_GE (exec_sql ("CREATE TABLE t_oos_show_part (id VARCHAR(4096) STORAGE FORCE_OUTLINE, "
+		       "data_col BIT VARYING STORAGE FORCE_OUTLINE) PARTITION BY RANGE(CHAR_LENGTH(id)) ("
+		       "PARTITION p0 VALUES LESS THAN(3000), PARTITION p1 VALUES LESS THAN MAXVALUE)"), 0);
+  ASSERT_EQ (exec_sql ("INSERT INTO t_oos_show_part VALUES(REPEAT('b',3000),REPEAT(X'AA',64)),"
+		       "(REPEAT('a',2999),REPEAT(X'BB',64))"), 2);
+  ASSERT_EQ (db_commit_transaction (), NO_ERROR);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p0 WHERE id=REPEAT('a',2999) "
+		    "AND data_col=CAST(REPEAT(X'BB',64) AS BIT VARYING)", 1);
+  expect_sql_count ("SELECT COUNT(*) FROM t_oos_show_part__p__p1 WHERE id=REPEAT('b',3000) "
+		    "AND data_col=CAST(REPEAT(X'AA',64) AS BIT VARYING)", 1);
+  expect_oos_records ("t_oos_show_part", 0, 0);
+  expect_oos_records ("t_oos_show_part__p__p0", 1, 2);
+  expect_oos_records ("t_oos_show_part__p__p1", 1, 2);
+}
+
 int
 main (int argc, char **argv)
 {
```

### H63 — Preserve the unresolved real-vacuum regression

[unit_tests/oos/test_oos_real_vacuum_server.cpp old:825 / new:825](https://github.com/CUBRID/cubrid/pull/7600/files#diff-e2892f2dbab3c1bae4d87c4fa1b9f7d0cdc5463a2fa1ba9ee94983c13c26b0eeR825)

Add a DISABLED_ test: committed original and independent witness, replacement update and abort, successful pre-vacuum original read, committed witness delete, observed vacuum progress, then original readback. Allocate the witness before reclaimable versions to avoid aliasing a recycled OOS slot. Historical final readback fails; DISABLED_ keeps it out of normal runs pending CBRD-27237. This is not a partition-specific test or a passing lifecycle result.

```diff
@@ -825,6 +825,50 @@ TEST_F (OosRealVacuum, ReVacuumAfterDrainIsIdempotent)
   expect_oos_gone (oos_oid, "drained OOS after re-vacuum");
 }
 
+/* A rolled-back replacement does not supersede the committed version. A
+ * separate committed delete witnesses real vacuum progress before readback;
+ * waking a daemon or freeing the replacement buffer alone proves nothing. */
+/* TODO (CBRD-27237): Remove DISABLED_ after the rollback/vacuum fix lands and
+ * this regression passes with real vacuum progress. */
+TEST_F (OosRealVacuum, DISABLED_RolledBackUpdateKeepsCommittedOosAfterVacuum)
+{
+  const std::string original (4096, 'a');
+  OID heap_oid, original_oid;
+  insert_row_with_oos (original, heap_oid, original_oid);
+
+  /* Allocate the progress witness before creating any reclaimable version,
+   * so a recycled OOS slot cannot alias the original OID in this test. */
+  OID witness_heap_oid, witness_oos_oid;
+  insert_row_with_oos (std::string (4096, 'w'), witness_heap_oid, witness_oos_oid);
+
+  RECDES replacement {};
+  ASSERT_EQ (test_oos_utils::from_string_into_recdes (std::string (4096, 'b'), replacement), NO_ERROR);
+  test_oos_utils::auto_freed_recdes_ptr defer_replacement (&replacement, recdes_free_data_area);
+  OID replacement_oid = OID_INITIALIZER;
+  ASSERT_EQ (test_oos_utils::oos_insert_from_recdes (thread_p, oos_vfid, replacement, replacement_oid), NO_ERROR);
+
+  RECDES new_heap_rec {};
+  ASSERT_EQ (build_heap_recdes_with_oos ({replacement_oid}, { (INT64) replacement.length}, new_heap_rec), NO_ERROR);
+  test_oos_utils::auto_freed_recdes_ptr defer_heap (&new_heap_rec, recdes_free_data_area);
+  ASSERT_EQ (heap_update_mvcc (hfid, class_oid, scan_cache, heap_oid, new_heap_rec), NO_ERROR);
+  ASSERT_EQ (xtran_server_abort (thread_p), TRAN_UNACTIVE_ABORTED);
+
+  RECDES before_vacuum {};
+  ASSERT_EQ (test_oos_utils::oos_read_with_alloc (thread_p, original_oid, before_vacuum), NO_ERROR);
+  test_oos_utils::auto_freed_recdes_ptr defer_before (&before_vacuum, recdes_free_data_area);
+  ASSERT_EQ (std::string (before_vacuum.data, before_vacuum.length - 1), original);
+
+  delete_row_and_close_block (witness_heap_oid);
+  ASSERT_TRUE (wait_for_vacuum ([this, &witness_oos_oid] { return oos_unreadable (witness_oos_oid); }, 60))
+      << "committed-delete witness did not establish vacuum progress";
+
+  RECDES after_vacuum {};
+  ASSERT_EQ (test_oos_utils::oos_read_with_alloc (thread_p, original_oid, after_vacuum), NO_ERROR)
+      << "rolled-back UPDATE must not make the committed OOS value reclaimable";
+  test_oos_utils::auto_freed_recdes_ptr defer_after (&after_vacuum, recdes_free_data_area);
+  EXPECT_EQ (std::string (after_vacuum.data, after_vacuum.length - 1), original);
+}
+
 int
 main (int argc, char **argv)
 {
```
