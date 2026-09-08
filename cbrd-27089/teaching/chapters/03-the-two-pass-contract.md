# 3. Build a probe, choose the partition, then store the value

Transformation has two jobs that used to run together: produce bytes usable by downstream code, and create the out-of-row values referenced by those bytes. Partition selection needs the first job before the destination is known. The PR introduces a mode that prepares a fully-inline record while reporting whether an ordinary transform would choose OOS. [C-015]

## Trace the example from SQL execution

The SQL executor evaluates values into attribute information and calls `locator_attribute_info_force` for the write. For INSERT, `old_recdes` is null. For UPDATE, the function first obtains the old row representation and deliberately falls through to the shared transformation code. The `[[fallthrough]]` explains why code under the INSERT case labels also handles UPDATE. [C-016]

With a partitioned operation, the new branch does the following:

1. Initialize `would_demote_oos=false` and pass its address to the allocator. The address selects suppression mode. The initial false value is not what enables suppression.
2. Build a fully-inline probe. For our forced-outline value, the planner reports true but leaves the plan unselected and `has_oos=false`.
3. If the copy area exists and demotion is needed, initialize output identifiers and call insert or update pruning with the probe bytes.
4. Free the probe copy area, clear its pointer and descriptor fields, and check the pruning error.
5. On success, build the final image with `&pruned_class_oid` and a null probe output. OOS creation now uses p0 as owner.
6. Continue into the existing `locator_insert_force` or `locator_update_force` path, then release the final copy area. [C-016]

## A second pruning still happens

The new early pruning does not replace the lower locator's existing pruning. The lower insert locator prunes again, selects the appropriate scan cache, obtains the subclass lock and forms a heap insert context from the final class/HFID. It then calls `heap_insert_logical`. The UPDATE path may call `locator_move_record` if the final destination differs from the row's current class. [C-017]

The early outputs `pruned_hfid` and `superclass_oid` satisfy the pruning API; the final transform specifically consumes `pruned_class_oid`. The PR does not overwrite the outer class/HFID with these early outputs. The lower locator continues to own actual write routing, locking and representation adjustment. [C-016] [C-017]

A useful invariant is agreement between early and final routing. Both operate on the same logical values, even though the final bytes can contain stubs. The partition reader uses the attribute layer to obtain a logical key. Probe increments have already been applied before early routing, and final serialization avoids applying them again. These facts support agreement; exhaustive agreement under every concurrent schema change is beyond the single regression. [C-018]

## What pruning actually reads

`partition_find_partition_for_record` initializes an attribute cache for the partition key, temporarily changes the record's representation ID to the root representation, reads key values and restores the original ID. It evaluates the partition expression, searches matching partitions and requires exactly one match. It copies the chosen class OID and HFID to outputs. If the class changed, it adjusts the record representation ID to the child's representation. [C-019]

Existing partition code can therefore consume the probe before storage. The final image still needs lower-level routing because the early probe whose representation was adjusted is freed. [C-019] [C-016]

## The mode table is the API

| Call | Owner override | Verdict pointer | Increments already applied | Result |
|---|---|---|---|---|
| Ordinary | Null | Null | False | Normal policy; owner from attribute info |
| Probe | Null | Non-null | False | Inline image; report demotion; apply attribute effects |
| Final owner | Selected class | Null | True | Normal policy; selected owner; skip repeated increments |
| Except-LOB | Null | Null | False | Ordinary policy with existing excluded-LOB behavior |

At the allocator boundary dispatch order is probe pointer first, owner pointer second, then LOB mode. If both pointers were non-null, probe wins. Intended changed callers pass only the meaningful pointer. The public probe wrapper does not assert a non-null verdict pointer: passing null would fail to select suppression internally. The final wrapper assumes a successful probe on the same attribute state. These are caller obligations, not compiler-enforced mode types. [C-008] [C-015]

## Paths that do less work

For a nonpartitioned class both pointers are null and the previous ordinary transform is selected. For a partitioned record whose probe reports no demotion, the probe copy area is retained and passed into the ordinary lower locator. There is no second transform; normal routing still occurs downstream. An oversized record with no eligible OOS attribute can also report no demotion—record size alone is not the verdict. [C-016] [C-020]

## Prediction questions

1. How many transforms and pruning calls occur for our forced-outline INSERT?
2. What happens when a partitioned probe returns false?
3. Why free the probe before constructing the final image?
4. If an UPDATE changes `id=1` to `id=20`, which heap should receive the new chain?
5. Why would passing null as the probe verdict pointer be dangerous?
