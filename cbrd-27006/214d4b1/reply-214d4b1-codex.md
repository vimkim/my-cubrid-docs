# Reply to review on 214d4b1

## Summary

I agree with the main readability concern. The current patch fixed the previous boundary problem by keeping
`heap_attrvalue_read()` and `heap_attrvalue_transform_to_dbvalue()` static in `heap_file.c`, but the result still
leaks the grouped-OOS mode into the scalar attribute reader through `prefetched_oos`.

My preferred follow-up is to remove the `prefetched_oos` parameter and make grouped lazy OOS Resolve an explicit
helper beside the scalar loop. `heap_file.c` should own attribute-to-`DB_VALUE` orchestration; `heap_oos.cpp` should
own OOS file operations and record-level OOS helpers.

## 1. Why was `prefetched_oos` introduced?

`prefetched_oos` is a per-attribute escape hatch for the grouped lazy Resolve path.

The grouped path first calls `heap_oos_read_grouped_payloads()`, which parses the requested OOS inline references and
fetches several OOS payloads with one `oos_read_many()` call. After that, each payload still has to be transformed into
the corresponding `DB_VALUE` using the same heap attribute conversion rules as the scalar path.

Since the two conversion helpers must stay static in `heap_file.c`, I passed the already-fetched raw payload back into
`heap_attrvalue_read()`:

```c
heap_attrvalue_read (recdes, &attr_info->values[i], attr_info, grouped ? &oos_raws[i] : NULL);
```

When `prefetched_oos` carries data, `heap_attrvalue_read()` skips the normal scalar lookup and `oos_read()` call, then
directly transforms the preloaded serialized bytes with COPY semantics.

So the parameter is not needed for correctness of ordinary reads. It is only there to consume the result of
`oos_read_many()` without exporting or duplicating the DB_VALUE conversion logic.

## 2. What happens if we remove it?

If we simply delete `prefetched_oos` and keep the rest of the code shape, grouped lazy Resolve becomes useless:

- `heap_oos_read_grouped_payloads()` still allocates buffers and calls `oos_read_many()`;
- the loop then calls the scalar `heap_attrvalue_read()`;
- each OOS attribute is read again through scalar `oos_read()`;
- the grouped buffers are freed without contributing to the final `DB_VALUE`.

If we remove both `prefetched_oos` and the grouped prefetch call, correctness stays intact because the scalar path still
works. But CBRD-27006 loses the lazy Resolve locality improvement for multi-OOS projections.

To remove it without losing the optimization, the grouped branch has to transform the prefetched payload explicitly in
`heap_file.c`:

```c
if (grouped && oos_raws[i].data != NULL)
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

That is clearer because `heap_attrvalue_read()` remains the scalar reader.

## 3. Alternatives for the read path

### Alternative A: keep the current shape

Keep `prefetched_oos`, maybe rename it to `grouped_oos_raw`.

This is the smallest code change, but I do not recommend it. It keeps two execution modes hidden inside a function whose
name reads like the scalar path.

### Alternative B: explicit branch in `heap_attrinfo_read_dbvalues_internal()`

Remove the parameter from `heap_attrvalue_read()` and branch in the loop:

- OOS payload present: call `heap_attrvalue_transform_to_dbvalue()`;
- otherwise: call scalar `heap_attrvalue_read()`.

This is better than the current code and keeps both helper functions static. The downside is that the loop still mixes
dispatch, OOS buffer ownership, and scalar fallback in one place.

### Alternative C: split scalar and grouped helpers

This is my recommended redesign.

Suggested shape:

```c
static int heap_attrinfo_read_dbvalues_scalar (RECDES *recdes, HEAP_CACHE_ATTRINFO *attr_info);
static int heap_attrinfo_read_dbvalues_grouped_oos (THREAD_ENTRY *thread_p, RECDES *recdes,
                                                    HEAP_CACHE_ATTRINFO *attr_info);
static int heap_attrinfo_read_dbvalues_from_recdes (THREAD_ENTRY *thread_p, RECDES *recdes,
                                                    HEAP_CACHE_ATTRINFO *attr_info);
```

Dispatch rule stays the same:

```text
requested OOS values = 0 -> scalar path
requested OOS values = 1 -> scalar path, preserving the stack scratch fast path
requested OOS values >= 2 -> grouped path with oos_read_many()
```

`heap_attrvalue_read()` returns to the old scalar signature:

```c
heap_attrvalue_read (recdes, value, attr_info);
```

The grouped helper handles only the grouped case: prepare raw OOS buffers, call `oos_read_many()`, transform OOS raws,
read non-OOS attributes through the scalar reader, and free every temporary buffer.

## 4. The awkward loop

Agreed. This line is too dense:

```c
ret = heap_attrvalue_read (recdes, &attr_info->values[i], attr_info, grouped ? &oos_raws[i] : NULL);
```

It hides a control-flow split and makes `heap_attrvalue_read()` look like it owns grouped prefetch state. I plan to
replace it with Alternative C above. If we want the smallest immediate cleanup, Alternative B is acceptable, but it is
still less readable than separate scalar and grouped helpers.

## 5. Is `heap_attrinfo_read_dbvalues_internal()` still needed?

There is still a reason to share a helper: both public entry points call the same read loop after representation recache.

- `heap_attrinfo_read_dbvalues()` also updates `inst_chn` and `inst_oid` after a successful read.
- `heap_attrinfo_read_dbvalues_without_oid()` skips that instance-cache update.

So the common post-recache read operation is still shared. However, the name `_internal` is not informative anymore.
As part of the redesign, I would rename it to describe the operation, for example:

```c
heap_attrinfo_read_dbvalues_from_recdes()
```

That helper would only dispatch between scalar and grouped-OOS read helpers.

## 6. Why is `heap_attrinfo_insert_to_oos()` still in `heap_file.c`?

The remaining part in `heap_file.c` is not the OOS file operation. It is heap attribute serialization.

It calls `heap_attrinfo_dbvalue_to_recdes()`, which shares the same DB_VALUE-to-disk conversion behavior as the inline
record writer. That includes the BLOB/CLOB ELO locator copy step and DB_VALUE state handling. Moving the whole function
to `heap_oos.cpp` would either export heap serialization internals or duplicate heap attribute conversion rules there.

The OOS-specific side has already been moved to `heap_oos_insert_serialized_values()`:

- class OOS file lookup;
- transaction descriptor validation;
- OOS insert publication-state reset;
- `oos_insert_many()`.

So the current boundary is:

```text
heap_file.c  -> choose OOS attributes and serialize DB_VALUEs into stable RECDES buffers
heap_oos.cpp -> insert already-serialized payloads into the OOS file
```

I think that ownership split is correct, but the readability of the remaining `heap_attrinfo_insert_to_oos()` can be
improved.

## 7. Write-path readability redesign

I would split the function into small local helpers while keeping serialization in `heap_file.c`:

```c
static SCAN_CODE heap_attrinfo_serialize_oos_value (..., int index, RECDES *payload);
static SCAN_CODE heap_attrinfo_prepare_oos_insert_requests (...,
                                                            std::vector<RECDES> *payloads,
                                                            std::vector<oos_insert_request> *requests);
static void heap_attrinfo_free_oos_payloads (std::vector<RECDES> *payloads);
```

Then `heap_attrinfo_insert_to_oos()` becomes an orchestration function:

```text
reserve payload/request vectors
prepare serialized payloads and request spans
call heap_oos_insert_serialized_values()
cleanup payload buffers
return S_SUCCESS/S_ERROR
```

This keeps `heap_oos.cpp` free of heap attribute serialization details, while making the insert path easier to read and
review.

## Future plan

1. Remove `prefetched_oos` from `heap_attrvalue_read()` and restore its scalar-only signature.
2. Split the read path into:
   - `heap_attrinfo_read_dbvalues_scalar()`;
   - `heap_attrinfo_read_dbvalues_grouped_oos()`;
   - `heap_attrinfo_read_dbvalues_from_recdes()` dispatcher.
3. Keep the current batching gate: grouped lazy Resolve only when at least two requested attributes are OOS values.
4. Keep `heap_attrvalue_transform_to_dbvalue()` and `heap_attrvalue_read()` static in `heap_file.c`.
5. Rework `heap_attrinfo_insert_to_oos()` into serialization, request preparation, and cleanup helpers.
6. Keep OOS file insertion in `heap_oos_insert_serialized_values()`.
7. Verify with the CBRD-27006 OOS SQL dispatch tests, OOS unit tests, `just build`, and `just build-test`.

## Questions

1. Should I implement the read-path redesign now in this PR, or keep this as a documented follow-up after the current
   review round?
2. For the write path, do you prefer a narrow readability split inside `heap_file.c`, or do you want a stronger boundary
   where `heap_oos.cpp` receives a higher-level serialized-payload container?
