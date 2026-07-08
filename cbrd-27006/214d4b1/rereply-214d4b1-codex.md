# Rereply to `my-review-214d4b1.md` - CBRD-27006 OOS read/insert path

## Summary

I agree with the readability concern. The current patch fixed the earlier boundary issue by keeping
`heap_attrvalue_read()` and `heap_attrvalue_transform_to_dbvalue()` static in `heap_file.c`, but the
new `prefetched_oos` parameter makes `heap_attrvalue_read()` carry two modes: scalar attribute read
and grouped-OOS materialization.

My preferred follow-up is to remove `prefetched_oos` from `heap_attrvalue_read()` and make grouped
lazy OOS Resolve explicit in the `heap_attrinfo_read_dbvalues` path. `heap_file.c` should keep
attribute-to-`DB_VALUE` orchestration and heap serialization. `heap_oos.cpp` should keep OOS file
operations, inline OOS reference parsing helpers, and batched OOS I/O.

## 1. Why was `prefetched_oos` introduced?

`prefetched_oos` was introduced as a hand-off channel for the grouped lazy Resolve path.

The grouped path does this first:

```text
heap_oos_read_grouped_payloads()
  -> find requested OOS-marked attributes
  -> parse each inline [OOS OID | full_length] reference
  -> allocate raw buffers
  -> call one oos_read_many()
```

After that, those raw serialized bytes still have to become `DB_VALUE`s using the same conversion
rules as the scalar attribute path. That conversion is in `heap_attrvalue_transform_to_dbvalue()`,
which intentionally remains `static` in `heap_file.c`.

So the current patch passes the already-fetched raw payload back into `heap_attrvalue_read()`:

```c
heap_attrvalue_read (recdes, &attr_info->values[i], attr_info, grouped ? &oos_raws[i] : NULL);
```

When `prefetched_oos` has data, `heap_attrvalue_read()` skips the scalar OOS lookup/read and directly
calls `heap_attrvalue_transform_to_dbvalue()` with COPY semantics.

That means the parameter is not needed for ordinary read correctness. It exists only so the result of
`oos_read_many()` can be consumed without exporting or duplicating the `DB_VALUE` conversion logic.

## 2. What happens if we remove it?

If we only delete the parameter and keep the current loop shape, the grouped read becomes useless:

- `heap_oos_read_grouped_payloads()` still allocates buffers and calls `oos_read_many()`.
- The loop then calls scalar `heap_attrvalue_read()`.
- Each OOS attribute is read again through scalar `oos_read()`.
- The grouped buffers are freed without contributing to the final `DB_VALUE`.

If we remove both the parameter and the grouped prefetch, correctness still holds because the scalar
path works, but CBRD-27006 loses the read-side locality improvement for multi-OOS projections.

The better removal is different: keep the transform static in `heap_file.c`, but move grouped
materialization out of `heap_attrvalue_read()` and into an explicit grouped helper beside the scalar
loop:

```c
if (oos_raws[i].data != NULL)
  {
    ret = heap_attrvalue_transform_to_dbvalue (&attr_info->values[i],
                                               attr_info->values[i].read_attrepr,
                                               &oos_raws[i], true);
  }
else
  {
    ret = heap_attrvalue_read (recdes, &attr_info->values[i], attr_info);
  }
```

That keeps both conversion helpers static and restores `heap_attrvalue_read()` to a scalar-only API.

## 3. Read-path alternatives

### Alternative A: keep the current shape, but clean it up

Keep `prefetched_oos`, maybe rename it to `grouped_oos_raw`, and remove the redundant `grouped` /
`handled` bool.

`heap_oos_read_grouped_payloads()` only resizes `oos_raws` when grouped Resolve applies. Otherwise
the vector stays empty. So `oos_raws.empty()` already carries the same signal as `grouped`, and
`raws[i].data == NULL` already means "not OOS here, use the scalar reader."

That would reduce this:

```c
ret = heap_attrvalue_read (recdes, &attr_info->values[i], attr_info,
                           grouped ? &oos_raws[i] : NULL);
```

to this:

```c
RECDES *prefetched = oos_raws.empty () ? NULL : &oos_raws[i];
ret = heap_attrvalue_read (recdes, &attr_info->values[i], attr_info, prefetched);
```

This is the smallest diff, but I do not recommend it as the final shape. It still leaves grouped-OOS
state hidden inside a function whose name reads like the scalar attribute reader.

### Alternative B: explicit branch in the shared read loop

Remove `prefetched_oos` from `heap_attrvalue_read()` and branch in
`heap_attrinfo_read_dbvalues_internal()`:

- OOS raw exists: call `heap_attrvalue_transform_to_dbvalue()`.
- Otherwise: call scalar `heap_attrvalue_read()`.

This keeps both helper functions static and is clearer than the current parameter. The downside is
that the loop still mixes grouped dispatch, OOS buffer ownership, and scalar fallback in one body.

### Alternative C: split scalar and grouped helpers

This is my recommended redesign.

Suggested shape:

```c
static int heap_attrinfo_read_dbvalues_scalar (RECDES *recdes,
                                               HEAP_CACHE_ATTRINFO *attr_info);
static int heap_attrinfo_read_dbvalues_grouped_oos (THREAD_ENTRY *thread_p, RECDES *recdes,
                                                    HEAP_CACHE_ATTRINFO *attr_info);
static int heap_attrinfo_read_dbvalues_from_recdes (THREAD_ENTRY *thread_p, RECDES *recdes,
                                                    HEAP_CACHE_ATTRINFO *attr_info);
```

The dispatcher keeps the current gate:

```text
requested OOS values = 0 -> scalar path
requested OOS values = 1 -> scalar path, preserving the stack scratch fast path
requested OOS values >= 2 -> grouped path with oos_read_many()
```

Then `heap_attrvalue_read()` returns to the scalar signature:

```c
heap_attrvalue_read (recdes, value, attr_info);
```

The grouped helper owns the grouped case end-to-end: prepare raw OOS buffers, call `oos_read_many()`,
transform OOS raws, read non-OOS attributes through the scalar reader, and free all temporary buffers.

### Alternatives I would not choose now

Moving `heap_attrvalue_transform_to_dbvalue()` to `heap_oos.cpp` would remove the parameter too, but
it reopens the boundary that the last commits intentionally closed. `heap_oos.cpp` should not own
heap attribute-to-`DB_VALUE` conversion.

Stashing prefetched bytes on `HEAP_ATTRVALUE` is also worse. It adds transient buffer lifetime state
to a widely used struct just for this grouped read path.

## 4. The awkward loop

Agreed, this line is too dense:

```c
ret = heap_attrvalue_read (recdes, &attr_info->values[i], attr_info, grouped ? &oos_raws[i] : NULL);
```

It hides a control-flow split and makes `heap_attrvalue_read()` look like it owns grouped prefetch
state.

The preferred fix is Alternative C above: split scalar and grouped read helpers and make
`heap_attrvalue_read()` scalar-only again. If we want the smallest cleanup before that redesign,
Alternative A is acceptable: drop `handled` / `grouped` and derive grouped state from
`oos_raws.empty()`.

## 5. Is `heap_attrinfo_read_dbvalues_internal()` still needed?

Yes. The separation is still load-bearing.

This PR added `_internal` because both public entry points need the same post-recache read operation:

- `heap_attrinfo_read_dbvalues()` performs the `inst_oid`-gated representation check and updates
  `inst_chn` / `inst_oid` after a successful read.
- `heap_attrinfo_read_dbvalues_without_oid()` skips that instance-cache update and has its own caller.

Before the shared helper, both entry points had their own copy of the per-attribute read loop. With
grouped OOS Resolve, duplicating that loop would also duplicate the prefetch / read / cleanup
sequence. So merging `_internal` back into `heap_attrinfo_read_dbvalues()` would either lose
`_without_oid` coverage or reintroduce duplicated grouped logic.

I agree the name `_internal` is not very informative. In the read-path redesign, I would rename it to
describe the operation:

```c
heap_attrinfo_read_dbvalues_from_recdes()
```

That helper would dispatch between the scalar and grouped-OOS helpers.

## 6. Why is `heap_attrinfo_insert_to_oos()` in `heap_file.c`?

Because the remaining work in that function is heap attribute serialization, not OOS file insertion.

For each selected OOS column, it calls `heap_attrinfo_dbvalue_to_recdes()`. That function is static in
`heap_file.c` and shares the same `DB_VALUE`-to-disk behavior as the inline record writer, including
the BLOB/CLOB ELO locator copy step.

The OOS-specific insertion side has already moved to `heap_oos_insert_serialized_values()`:

- class OOS file lookup
- transaction descriptor validation
- OOS insert publication-state reset
- `oos_insert_many()`

So the current ownership split is:

```text
heap_file.c  -> choose OOS attributes and serialize DB_VALUEs into stable RECDES payloads
heap_oos.cpp -> insert already-serialized payloads into the OOS file
```

Moving `heap_attrinfo_insert_to_oos()` wholesale into `heap_oos.cpp` would require exporting or
duplicating heap serialization internals. I do not think that is a better boundary.

## 7. Write-path readability redesign

I would keep serialization in `heap_file.c`, but split the function locally.

Suggested local helpers:

```c
static SCAN_CODE heap_attrinfo_serialize_oos_value (..., int index, RECDES *payload);
static SCAN_CODE heap_attrinfo_prepare_oos_insert_requests (...,
                                                            std::vector<RECDES> *payloads,
                                                            std::vector<oos_insert_request> *requests);
static void heap_attrinfo_free_oos_payloads (std::vector<RECDES> *payloads);
```

Then `heap_attrinfo_insert_to_oos()` becomes orchestration:

```text
reserve payload/request vectors
prepare serialized payloads and request spans
call heap_oos_insert_serialized_values()
cleanup payload buffers
return S_SUCCESS/S_ERROR
```

There is one larger readability issue I would keep separate: the three parallel vectors
`oos_columns`, `oos_oids`, and `oos_lengths`. A single `oos_column_plan` struct like this would be
clearer:

```c
struct oos_column_plan
{
  bool selected;
  OID oid;
  DB_BIGINT length;
};
```

But those vectors are produced in `heap_attrinfo_determine_disk_layout()` and consumed later in
`heap_attrinfo_transform_columns_to_disk()`, so that is a cross-function refactor. I would not bundle
it with the local readability split unless we decide to spend the extra review budget.

Minor cleanup: the current cleanup loop calls `free_and_init()` on a local copy of
`requests[i].src.data()`. It frees the allocation correctly, but it does not null the vector slot.
Since the vector is discarded immediately this is safe, but a dedicated payload vector plus
`heap_attrinfo_free_oos_payloads()` would make ownership easier to read.

## Future plan

1. Remove `prefetched_oos` from `heap_attrvalue_read()` and restore the scalar-only signature.
2. Split the read path into scalar, grouped-OOS, and `from_recdes` dispatcher helpers.
3. Keep the current batching gate: grouped lazy Resolve only when at least two requested attributes
   are OOS values.
4. Keep `heap_attrvalue_transform_to_dbvalue()` and `heap_attrvalue_read()` static in `heap_file.c`.
5. Keep `heap_attrinfo_read_dbvalues()` and `heap_attrinfo_read_dbvalues_without_oid()` as public
   wrappers over the shared `from_recdes` helper.
6. Rework `heap_attrinfo_insert_to_oos()` into serialization, request preparation, and cleanup
   helpers inside `heap_file.c`.
7. Keep OOS file insertion in `heap_oos_insert_serialized_values()`.
8. Defer the parallel-vector to `oos_column_plan` refactor unless we explicitly choose the larger
   cleanup.

Verification after implementation: `just build`, `just build-test`, `test_oos` SA tests,
`test_oos_server`, and `test_oos_sql_crud`, especially the CBRD-27006 dispatch test that asserts the
`>= 2` OOS projection path uses `oos_read_many()`.
