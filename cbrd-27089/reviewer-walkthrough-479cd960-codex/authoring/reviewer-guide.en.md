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
