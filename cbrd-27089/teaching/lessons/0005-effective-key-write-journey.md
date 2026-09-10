# One INSERT, one moving UPDATE: choose the owner before building the row

Learning target: explain why source identity, destination OOS ownership and final row placement are separate responsibilities. Source: local committed delta `b871ea386...213ce80f5`, not a CBRD-27237 fix. This is a source walkthrough, not a new experiment.

Assume RANGE(id): p0 contains id < 10, p1 contains id >= 10. Their heaps are H0/H1, with lazily created OOS files OOS0/OOS1. Use a sufficiently large uncompressed payload so the real serializer chooses OOS. Names H0/OOS0 are teaching labels, not actual identifiers.

## INSERT: id = 9, payload = A

At `locator_attribute_info_force`, assignments are held in `attr_info`: a cache of attribute values, states and class representation metadata. It is not the final disk record. `old_recdes` is absent for this INSERT.

1. `partition_prune_insert_by_attrinfo` asks the heap module for the effective key. The assigned 9 is cloned, normalized through the scalar disk codec and supplied to the existing partition evaluator. The unrelated large payload is not serialized for this decision.
2. The chosen child is p0. `write_destination` retains p0's class OID; the routing wrapper also returns its heap identifier. This selection does not yet insert the row.
3. `locator_allocate_copy_area_by_attr_info_internal(..., &write_destination, ..., true)` performs owner-aware normal first-pass preparation. The heap helper supplies the destination only as the OOS owner; source cache identity is preserved. The payload becomes a chain in OOS0, and the full row image contains its inline stub.
4. `locator_insert_force_internal` routes the actual serialized record again. Its result must equal p0. Existing representation handling, locks, caches and index/heap insertion then place the row in H0.

The first full-row transformation remains; the preliminary full inline row does not. Scalar key serialization, final OOS payload serialization, copyarea storage and real buffer-growth retries remain.

## UPDATE: id = 9 → 12, payload A → B

1. The existing locator path obtains or accepts the old record and passes it as `old_recdes`. The source class is the current physical child p0; this is still where the old row belongs.
2. `partition_prune_update_by_attrinfo` prepares the assigned key 12 and selects p1. Reading other unchanged values later still needs the old record and source metadata, so do not overwrite `attr_info->class_oid` with p1.
3. The owner-aware first pass builds the new row and writes its new OOS value chain into OOS1. An unchanged OOS payload would also be freshly serialized under the current no-chain-reuse implementation; moving UPDATE does not authorize borrowing p0's chain.
4. `locator_update_force` routes the completed record, checks p1 agrees with the early owner, refreshes actual source class/heap information and executes the existing cross-partition movement path. This optimization does not replace movement or index maintenance.

Old chain A does **not** become deletable merely because B was prepared. In SERVER mode, previous versions and rollback may still require it. SA eager cleanup differs; the known CBRD-27237 failure means post-rollback vacuum safety is not established on this revision.

## The important contract

Early routing answers: **which heap must own any OOS values created during preparation?** Final routing answers: **where does the serialized record belong, with existing validation and representation handling?**

If the answers disagree, fail through normal transactional error handling. Do not redirect already-written chains or change the source cache to hide the mismatch.

Defaults and increments explain why the input is called an *effective* key, not simply `attr_info`'s current value. Next: omitted INSERT uses its default; unchanged UPDATE reads its supplied old record; pending INCR/DECR is simulated on the temporary key without consuming the real mutation. We will trace these branches after the checkpoint.

## Checkpoint

During the 9 → 12 UPDATE, early routing chooses p1. Why must the code **not** change the source cache's class identity to p1, even though the new OOS values belong there? If final routing chooses a different child, what should happen to the write?

Answer before opening the HTML explanation. Coverage is not recorded as mastery until you explain the consequences.

## Primary source reading

Read these from local commit `213ce80f5`, in order:

- `src/transaction/locator_sr.c:7767`: early routing, one owner-aware preparation, final INSERT/UPDATE force.
- `src/storage/heap_file.c:12117`: `heap_attrinfo_get_effective_key` branches and temporary ownership.
- `src/storage/heap_file.c:12928`: owner-aware **first pass**, with increments-already-applied false.
- `src/transaction/locator_sr.c:4990` and `:6014`: final record route and agreement guards.
- `src/query/partition.c:3618`: root-representation decode, restoration and destination representation patch.

Compare the [original PR locator path](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L7711): only OOS-producing writes rebuild; non-OOS rows reuse their initial row image. Do not claim the old version always transforms twice or the new version is proven faster.

See [HTML lesson](0005-effective-key-write-journey.html), [quick reference](../reference/effective-key-routing.html), and [reviewed source handoff](../../design/blocked-handoff-213ce80f5-codex.md). Ask the agent about any unclear step.
