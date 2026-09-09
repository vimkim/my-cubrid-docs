# PR #7600: remove full-row routing probes without changing OOS ownership

Status: research recommendation, not an accepted design or implementation authorization.

Source revision: `b871ea386d2c5419b7abae07dda58b9b7f36377a`; research date: 2026-09-08. Source root: `/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos`. No engine edits, builds, benchmarks, or database experiments were performed for this report. Links below pin implementation claims to that revision; line numbers also locate the corresponding local files.

Normative context was read from the clean `cubrid-oos-context` revision `f6543de680b91ae357466b72a983f982892859cd` (the context header says last updated 2026-08-28). Its accepted future work is not treated as implemented in the pinned PR head. `OOS-CONTEXT.md` SHA-256: `d7d3259d647bb2ed0ee9b45f336863266573fcbac952e21ad1b40e21fa55cbaf`.

## Recommendation

Investigate and specify **a narrow effective-partition-key adapter plus value-based partition selection**, retaining the existing final record transformer and downstream force paths. Do not first refactor all attribute preparation or move LOB management. This is the smallest coherent candidate because selection reads one attribute, whereas full transformation performs unrelated, stateful operations. Feasibility depends on proving that the adapter produces the same routing value as serializing and reading that attribute. [Selection][select] [Transformation][transform]

Proposed shape:

```text
Effective partition-key value, computed without mutating pending assignments
    → existing partition-expression evaluation and matching semantics
    → destination class for OOS
    → one normal full-row transform, with destination override
    → existing locator force, partition validation, representation patching,
      subclass locking, scan-cache selection, and UPDATE movement
```

“One transform” means one full-row transformation invocation, not zero serialization: OOS payloads still need serialization, buffer growth can still retry column writing, and a small key-only serialization round trip may be necessary for faithful domain semantics. The expected reduction is elimination of the temporary **whole inline row**, not elimination of `attrinfo`, the final copy area, or all data copies. [Copy-area allocation][copyarea] [OOS serialization][oos-write]

Do not reuse `heap_attrinfo_transform_to_disk_oos_class()` unchanged for this flow: its name hides a **second-pass-only** contract, and it hardcodes `increments_already_applied=true`. With clone-only key preparation, that would suppress the real pending increments. Add an explicit destination-aware **first-pass** entry point or equivalent internal mode, with the increment flag false. Preserve the probe entry points still used for duplicate-key work. [Transform wrappers][wrappers] [Duplicate-key probes][duplicate]

## 1. What the PR currently does

For partitioned writes in `locator_attribute_info_force`, the PR builds an OOS-suppressed inline record. If `would_demote_oos` is false, that image is retained. If true, it prunes, frees the probe copy area, then builds the final record using the selected partition class as OOS owner. Nonpartitioned writes take the ordinary transformation. Therefore the PR does **not** perform two full builds for every partitioned row. [Locator write orchestration][force]

`FORCE_OUTLINE` participates in the suppression verdict even below the ordinary size gate. The source at this revision still uses `DB_PAGESIZE / 4` for ordinary demotion; that is an implementation conformance gap against the normative physical four-record target, not a reason to redefine the target in this work. Do not mix a threshold-policy change into routing optimization. [Layout implementation][layout] [Normative specification][spec]

The final `locator_insert_force` / `locator_update_force` calls prune **again**. That is not just redundant arithmetic: surrounding code performs subclass locking, chooses partition scan caches and function-index predicates, or moves an updated row across heaps. The preliminary selected HFID is not passed through as a replacement for those operations. [Insert force][insert-force] [Update force][update-force]

## 2. Value-preparation contract

### Explicit assignments and coercion

`heap_attrinfo_set` initializes the destination domain, checks exact domain compatibility, uses the type's `setval` for compatible input, or `tp_value_auto_cast_with_precision_check` otherwise, then marks the slot `HEAP_WRITTEN_ATTRVALUE`. Thus many conversions have already occurred before force. Nevertheless, a raw cached value must not be presumed identical to the post-serialization value for every type: the current selector reads through the type's `data_readval`, using representation domain metadata. [Assignment][set] [Attribute decode][read]

There is concrete evidence of post-assignment normalization: `mr_writeval_char_internal` pads CHAR(N) to precision before compression and mutates the DB_VALUE; the corresponding reader reconstructs the value using domain metadata. This makes a raw-value bypass a proof obligation, not an obviously equivalent shortcut. The variable writer also contains AUTO_INCREMENT NUMERIC precision handling, but NUMERIC is not in the parser's partition-key whitelist at this revision and is not a reason to broaden the adapter into all-type preparation. [CHAR writer/reader][char] [Variable writer][variable] [Legal key types][key-types]

### Missing INSERT values and unchanged UPDATE values

`heap_attrinfo_set_uninitialized` recaches the old record representation when present and fills each `HEAP_UNINIT_ATTRVALUE` slot with `heap_attrvalue_read`. With no old record, the latter reads representation defaults; with an old record it reads that version, falling back to defaults when an attribute did not exist in the old representation. It also sets `inst_chn` from the old record, or `-1` for insert. This is more than filling SQL assignment slots. [Preparation][prepare] [Read/default selection][read]

An unchanged OOS-backed attribute is resolved by the attribute reader when required. This optimization must not introduce OOS-chain reuse across record versions; that is separate accepted future work with different vacuum/replication prerequisites in the normative context. Avoid claiming that eliminating the inline row also eliminates unchanged-value OOS reads. [Read][read] [Normative UPDATE design][spec]

Dynamic defaults are not all representation constants: the executor explicitly distinguishes per-row SYS_GUID/UUID defaults from per-statement preparation. Consume already-evaluated assignments where present; do not reevaluate a dynamic default in the adapter. [Executor defaults][defaults]

For narrow routing, an uninitialized key needs an owned value read from the appropriate old representation/default. `heap_attrinfo_access` alone is insufficient: it errors on an uninitialized slot. Use existing reading machinery through a carefully scoped cache/helper, rather than calling the full preparation routine purely to obtain one key. [Access contract][access] [Read][read]

### INCR / DECR are not ordinary UPDATE expressions

The fixed-column writer applies `qdata_increment_dbval` when `do_increment != 0`; a set of processed attribute indexes prevents repeat application after buffer-growth retry. The variable-column writer rejects nonzero `do_increment`. `qdata_increment_dbval` supports SHORT, INTEGER, and BIGINT and resets overflow/underflow results to zero. Do not replace it with generic SQL addition or assume NUMERIC support. [Fixed writer][fixed] [Variable writer][variable] [Increment semantics][increment]

The probe mutates the actual cached fixed values. Its second-pass wrapper pre-marks pending increments as already processed. In the proposed adapter, clone the key and use the same increment operation on that clone; leave the original pending assignment intact so the real first-pass transformer applies it exactly once. This is a proposal, not implemented behavior. NULL handling and the exact domain seen by the helper require differential tests. [Wrappers][wrappers] [Transformation][transform]

Ordinary `UPDATE SET id = id + 1` and the dedicated `INCR()/DECR()` path require distinct tests: exercising one does not prove the other. `qexec_execute_increment` clears an all-attribute cache, sets `do_increment`, then calls locator force, so the adapter must handle an uninitialized key with a pending increment. [Increment caller][increment-caller]

### LOB side effects: preparation is not pure

For a written BLOB/CLOB slot, `heap_attrinfo_set_uninitialized` saves the new value, reads/deletes the old ELO, restores the assignment, and leaves it written. During inline or OOS-value serialization, a written LOB with `LOB_FLAG_INCLUDE_LOB` is copied with a class/heap-derived prefix, its locator is replaced, and state becomes `HEAP_WRITTEN_LOB_ATTRVALUE`. That state prevents repeat copy during buffer retry and prevents re-entering the old-written-LOB branch on the second transform. [Preparation][prepare] [OOS serialization][oos-write] [Variable writer][variable]

Consequences:

- The probe writes no OOS chains, but it is **not side-effect-free**.
- Calling full preparation early and then calling the normal transformer can repeat old-LOB processing unless its state contract changes.
- A broad “prepare everything once” split must explicitly own old-LOB deletion, new-LOB copying, locator size drift, and failure state—not merely move one function call.
- OOS destination override does not change `attr_info->class_oid`: LOB metadata/prefix currently uses that original class while OOS file lookup uses the override. Do not silently retarget LOB metadata by overwriting the cache's class identity. [OOS serialization][oos-write]

BLOB/CLOB locator bytes remain eligible for OOS; the external LOB payload is a separate subsystem. Excluding them to simplify this refactor would contradict accepted ADR-0002. [LOB ADR][lob-adr]

## 3. Partition-selection contract

`partition_find_partition_for_record` starts a cache for exactly one attribute identified by the partition expression, binds that cache to the expression, substitutes the root representation ID temporarily, reads the key, restores the original ID, evaluates the expression with `fetch_peek_dbval`, and matches via `partition_prune_db_val`. NULL uses `PO_IS_NULL`; non-NULL uses `PO_EQ`. Exactly one partition must match; otherwise the function preserves the appropriate partition/error outcome. [Selection][select]

On success it returns the partition OID/HFID and, when source and destination classes differ, patches the record representation ID to the destination's ID. The source explicitly relies on partition layouts being identical except for those bits; this is not a general superclass-to-subclass conversion rule. [Selection][select]

INSERT and UPDATE wrappers additionally own context loading/reuse/cleanup, explicit-partition validation, and superclass reporting. UPDATE discovers the root from the source partition when no context is provided; the root holds no user rows. A new value route must preserve these wrapper semantics rather than exposing only the low-level match function and losing validation. [Insert/update wrappers][prune-wrappers]

`partition_set_cache_dbvalp_for_attribute` already binds a `DB_VALUE` to all attribute references in an expression, including arithmetic/function operands. Its comment states that partition expressions contain one column. It clears `cache_slot`; a new call path must restore or rebind cached expression pointers before the temporary value is freed, especially when the same context is subsequently used for record-based pruning. This helper is evidence of a reusable mechanism, not a public write-routing API ready to call. [Expression binding][binding]

The parser permits INTEGER/BIGINT/SMALLINT, DATE/TIME/TIMESTAMP variants/DATETIME variants, and CHAR/VARCHAR for the partition column and expression result. BLOB/CLOB are excluded, supporting a narrow adapter with no LOB-key lifecycle. CHAR/VARCHAR keys can themselves be large and OOS-backed; key-only does not mean constant-size or free. [Legal key types][key-types]

### Why retain the downstream route initially?

The existing second route supplies the final representation patch and surrounding lock/cache/movement behavior. Retaining it reduces the first change's scope. Do not pass `DB_NOT_PARTITIONED_CLASS` merely because an early route succeeded: that would bypass more than selection. If later eliminating the second route is desirable, pass an explicit validated routing result into a separately reviewed force contract. [Insert force][insert-force] [Update force][update-force]

For early value routing, return at least destination class/HFID and required context/root information. Keep source cache identity separate from destination OOS identity. The final first-pass transform can retain source representation construction, followed by the existing final route's representation-ID patch. Early and final destinations must agree; disagreement is a correctness failure, not permission to redirect OOS after its chains have already been written. [Header construction][header] [Selection][select]

## 4. Error and resource boundaries

| Resource/state | Current owner and cleanup | Refactor obligation |
|---|---|---|
| Probe/final copy area | Locator allocates; frees probe after preliminary pruning and final area after force | Remove only unnecessary probe; preserve final lifetime |
| Grown record buffer | `record_descriptor` may release allocated data; locator copies into a larger copy area | Account for allocation-failure ownership explicitly |
| Temporary routing DB_VALUE | New proposed adapter | Own/clear clone; do not leave expression cache pointing at freed data |
| Pruning context | Wrappers retain successful supplied contexts, clear owned/error contexts | Preserve ownership and error behavior |
| OOS payload buffers | `heap_attrinfo_insert_to_oos` collects and frees payloads on cleanup | Preserve cleanup on serialization and insert failures |
| OOS publication state | `heap_oos_begin_insert_publication` resets thread OIDs and transaction LSA queue together | Reset once before fallible OOS serialization, not during a key-only route |
| Persistent OOS writes | Existing logged insert path and enclosing transaction/error handling | Never mistake freeing a copy area or vector for rollback of stored chains |

Sources: [Copy-area lifecycle][copyarea], [force cleanup][force], [context cleanup][prune-wrappers], [payload cleanup][oos-write], [publication reset and insertion][publication].

The OOS+big-record rejection occurs after layout selection but before OOS insertion. Preserve that gate. In a one-pass destination-aware transform, pending increments still occur during fixed-column writing, after OOS insertion, as in the original ordinary transform; this differs from the PR probe's earlier application. Error cases must prove transaction cleanup, not assume the successful-row comparison settles failure semantics. [Transformation][transform]

Read-only inspection also found a preexisting-looking cleanup hazard: after `release_buffer`, failure to allocate the replacement copy area returns before `free(allocated_data)`. This report does not establish its introduction history or a runtime leak. Keep it a separate finding and ensure new code does not inherit/expand the ownership hole. [Copy-area allocation][copyarea]

## 5. Alternatives

| Option | Benefit | Cost/risk | Recommendation |
|---|---|---|---|
| Retain current full inline probe | Uses existing record semantics; minimal new interfaces | Copies/serializes large unrelated payloads before final build on OOS rows | Valid baseline/fallback, not proven performance bottleneck |
| Direct use of raw `attrinfo` DB_VALUE | Small apparent patch | Wrong for uninitialized keys, pending increments, or post-write domain differences | Reject naive form |
| Effective-key adapter + shared value matcher | Removes full-row probe; keeps LOB/value write lifecycle localized | Must prove key equivalence and temporary cache lifetime | Preferred candidate for specification |
| Full preparation/serialization split | More explicit global lifecycle; possible reusable planning API | Broadly changes side-effect timing, retry state, flags, and error ordering | Defer unless key adapter cannot be made coherent |
| Key-only synthetic full `RECDES` | Reuses existing selector verbatim | Fake missing payloads/header offsets and layout can become another fragile format adapter | Prefer a scalar value interface; small scalar round-trip is different |
| Shared OOS file across partitions | Could avoid destination-dependent OOS placement | Changes accepted per-heap lifecycle/vacuum ownership | Out of scope; not needed to remove serialization work |

These are engineering judgments inferred from the contracts above, not benchmark results or accepted ADRs. The normative file-per-heap rule is independent of how routing inputs are represented. [Specification][spec]

### Smallest proposed implementation boundary

1. In the partition module, factor expression evaluation plus match/result handling so record-based and value-based callers share behavior. Reuse, rather than duplicate, context loading and explicit-partition checks.
2. In the heap attribute layer, provide a narrow owned effective-key operation: honor slot state and old/default representation, clone, apply pending integer increment to the clone, and normalize to the value the stored record would expose. If needed, serialize/read only this scalar using existing type routines. This adapter must not perform LOB deletion/copy or OOS insertion.
3. Add destination-aware **first-pass** transformation semantics, distinct from the existing “probe already ran” wrapper. Keep `attr_info->class_oid` unchanged.
4. In `locator_attribute_info_force`, route first and invoke the final transform once with the OOS destination. Keep existing final force and pruning for the first implementation.
5. Keep REPLACE/ODKU probe callers unchanged initially: they exist for duplicate-key/index work, not solely partition routing. A separate analysis must justify replacing their record inputs. [Duplicate probes][duplicate]

A supported-type fast path with the existing probe as fallback is an acceptable staged option only if fallback conditions are explicit, testable, and measured. Do not advertise removal for all partitioned rows if coverage is partial. Prefer complete support for legal partition keys if it can remain small; legal-type/collation closure is an open specification gate.

## 6. Unresolved risks and decision gates

1. **Type equivalence:** prove equality with serialized-record routing for the parser's legal key types/expressions, including CHAR padding, collation, integer widths, date/time variants, and NULL. A scalar round-trip is a conservative candidate, not yet proven sufficient for every allowed domain. AUTO_INCREMENT NUMERIC remains a non-key serialization regression concern, not a legal-key support requirement at this revision.
2. **Slot states:** verify actual INSERT/UPDATE callers' cache state, including any lazy slot, absent attribute, old representation, defaults already evaluated upstream, and generated/serial values. Do not evaluate dynamic defaults twice; consume the effective upstream assignment where present.
3. **Side-effect ordering:** early invalid-partition failure may now occur before unrelated LOB processing or invalid non-key values. Decide whether preserving specific error precedence is required; in all cases failures must leave no durable partial effects.
4. **Repeated pruning:** prove initial/final destination agreement, context cache rebinding, and representation handling for root insert, direct partition insert, same-partition update, and moved update.
5. **Caller modes:** inventory force/update-in-place and retry paths before extending the optimization beyond the currently scoped locator path. No claim is made here that every SQL write or replication path enters it.
6. **Performance:** large inline probe elimination should reduce copied bytes/peak memory, but no elapsed-time, contention, or throughput gain has been measured. Early routing plus retained final pruning means **two route evaluations even for non-OOS rows**, where this PR only performs one. Small rows can regress. Any cheap “needs early route” gate must itself have a proven value/layout-preparation contract; do not reintroduce the full probe disguised as a gate. Final pruning may also resolve an OOS-backed string key. [Current conditional route][force] [Attribute read][read]

## 7. Test-first and measurement plan (not executed)

First lock down observable semantics and ownership against this revision. The existing `PartitionedForceOutlineStoresOosInPrunedHeap` is a useful ownership regression, but it is not evidence for key mutation, migration, or server MVCC. [Existing ownership regression][test]

| Test family | Discriminating check |
|---|---|
| Range/list/hash and expression keys | Value route equals record route; chosen child/root/unselected OOS ownership |
| Boundary/default/NULL/coercion | Correct partition and same final value; missing-partition and explicit-partition error behavior |
| Key unchanged UPDATE | Obtain old/default value correctly without changing assignment state |
| Key-changing UPDATE | Row moves to destination heap; new chains belong there; old version stays valid as required |
| Dedicated INCR/DECR | Partition-boundary crossing, overflow-to-zero, all integer types; original increment applied once |
| Ordinary arithmetic UPDATE | Test separately from dedicated pending increments |
| LOBs | Written and unchanged LOBs, inline and demoted locators, growth retries, failures after routing and during write; no duplicate copy/delete |
| FORCE_OUTLINE and ordinary OOS | Small forced values, large VARBIT payload, multiple candidates, non-OOS control, OOS+big-record rejection |
| Reused pruning context | Alternate value and record routes across many rows; no stale pointers or previous-row values |
| Error cleanup | Invalid route before write; OOS preparation/insertion failure; final heap/index error; rollback and subsequent valid write |
| Server/MVCC | Concurrent old-version reader, moved update rollback, vacuum/recovery behavior under a separate SERVER_MODE harness |
| REPLACE/ODKU/nonpartitioned | Preserve unaffected duplicate-probe semantics and ordinary write path |

The SQL OOS fixture is SA_MODE; passing it alone cannot prove MVCC/vacuum/server concurrency. Use existing test mechanisms in each appropriate build mode, after implementation approval. [SA fixture][fixture]

Reuse existing publication-state failure tests (`OosLogicalPreparationFailureSeesCleanPublicationState`, `OosClassLookupFailureSeesCleanPublicationState`, `OosVfidLookupFailureSeesCleanPublicationState`, and `OosInsertManyPartialPublicationFailureClearsBothSides`). Add a routing-only assertion that no OOS publication/write occurs. Retain transaction rollback checks rather than inventing ad hoc manual deletion of partially inserted chains. [Existing failure tests][failure-tests]

For performance, compare the pinned baseline and candidate with identical builds/settings/workload distributions. Collect full-row transformation count, retry count, temporary buffer allocation bytes/peak, copied bytes, OOS payload serialization bytes, OOS insertion count, routing invocations, and elapsed/CPU time. Include small inline rows, small FORCE_OUTLINE rows, large uncompressed VARBIT payloads, and updates with unchanged large attributes. Verify logical values and owner VFIDs while measuring; report variance and the workloads that regress. Instrumentation and experiments require the user's next approval.

Acceptance should combine: no ownership/semantic regressions, no full inline probe on the claimed optimized paths, preserved failure cleanup, and a measured cost profile. “Fewer lines” or “one function invocation” alone is insufficient.

## Next decision

Choose whether to specify the narrow effective-key route first (recommended), or retain the PR unchanged pending a baseline benchmark. A broad preparation split should be chosen only with evidence that the narrow boundary cannot preserve semantics cleanly. Implementation, tests, and experiments remain gated on user approval.

## Research verification

The primary agent independently checked the selector, first/second-pass transform contracts, INCR caller and arithmetic semantics, CHAR codec, parser type restrictions, final force routing, and existing ownership/publication test surfaces. All 30 reference definitions resolve; pinned source paths and cited line ranges were checked against the local Git objects. No engine or unit-test files changed. These are source/document checks, not runtime validation of the proposed design. Work-tracker item: 71.

[select]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/partition.c#L3467-L3580
[prune-wrappers]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/partition.c#L3605-L3825
[binding]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/partition.c#L3010-L3048
[force]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L7711-L7828
[copyarea]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L7491-L7574
[insert-force]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L4950-L5050
[update-force]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L5979-L6050
[set]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12009-L12098
[prepare]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12119-L12223
[read]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L10580-L10702
[access]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L11442-L11464
[layout]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12310-L12430
[oos-write]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12549-L12775
[wrappers]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12790-L12852
[header]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12871-L12949
[fixed]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12966-L13039
[variable]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13061-L13209
[transform]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13316-L13464
[increment]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/query_opfunc.c#L2911-L2970
[publication]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_oos.cpp#L601-L667
[duplicate]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/query_executor.c#L11940-L12204
[test]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/unit_tests/oos/sql/test_oos_sql_show.cpp#L387
[fixture]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/unit_tests/oos/sql/test_oos_sql_common.hpp#L20
[failure-tests]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/unit_tests/oos/test_oos_server.cpp#L389-L470
[key-types]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/parser/semantic_check.c#L6095-L6175
[char]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/object/object_primitive.c#L12175-L12380
[defaults]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/query_executor.c#L13365-L13373
[increment-caller]: https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/query_executor.c#L14471-L14540
[spec]: /home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md
[lob-adr]: /home/vimkim/gh/cubrid-oos-context/docs/adr/0002-oos-lob-locator-demotion.md
