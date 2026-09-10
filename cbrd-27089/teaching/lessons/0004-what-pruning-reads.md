# Lesson 0004: Full-record interface, single-attribute dependency

Status: source-backed explanation introduced; alternative remains unimplemented and unmeasured. Source revision b871ea386d2c5419b7abae07dda58b9b7f36377a. No engine edits or experiments.

## What the current function does

In [partition_find_partition_for_record](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/partition.c#L3467):

1. Initializes its own attribute cache for **one** attribute (`1, &pinfo->attr_id`), not the whole row's attribute set.
2. Binds that cache to the partition expression via partition_set_cache_info_for_expr.
3. Saves the serialized record's representation ID and temporarily installs the root representation ID.
4. Reads the requested attribute from RECDES into that cache and restores the original representation ID.
5. Evaluates the partition expression with fetch_peek_dbval.
6. Uses the expression result with partition_prune_db_val; NULL uses PO_IS_NULL. Requires exactly one matching partition or returns an error.
7. Returns the selected class OID and heap HFID. If the class changes, updates the record's representation ID to that of the selected partition.
8. Clears its temporary attribute values.

The routing decision depends on the partition expression's result, not unrelated payload columns. The function nevertheless uses record metadata and modifies the record representation ID: it is not a pure value-to-partition function today.

## A concrete alternative shape (proposal)

Finalize routing attribute → evaluate the existing partition expression → select class/HFID/representation → serialize the row and write OOS into the selected heap's file.

The [expression-cache helper](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/partition.c#L3010) already binds a DB_VALUE into a partition expression in other pruning paths. This is evidence for feasibility investigation, not a ready-made replacement write API. Preserve temporary binding lifetimes and cleanup.

## Why not simply read the caller's current attrinfo?

The write transformation first [fills uninitialized attributes](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13354); heap_attrinfo_set_uninitialized may read old values and includes LOB-related side effects. Transformation also applies pending INCR/DECR assignments; its second-pass guard prevents applying them twice. A new route-before-serialization interface must receive the effective new partition-key value, preserving type semantics and statement evaluation timing. Reusing the whole initializer blindly is not a proven side-effect-free preparation phase.

Also preserve root/child representation handling, explicit-partition validation, NULL/error semantics, and UPDATE destination changes. Existing serialization helpers do not automatically become correct merely by passing a different class ID.

## Performance boundary

Avoiding a full inline record could avoid serialization/copying of unrelated large values for OOS-producing writes. This is a hypothesis, not a benchmark result; non-OOS writes already retain the first record in this PR. Final OOS payload serialization and heap-row serialization still remain necessary.

## Check

A row's partition key is 9, but a pending operation will increment it to 10. What goes wrong if early routing reads 9 before that operation is applied? Which value must both routing and final serialization agree on?
