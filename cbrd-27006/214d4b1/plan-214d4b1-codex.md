# Plan for `my-review-214d4b1.md` - CBRD-27006 OOS read/insert cleanup

## Position

Implement the stronger end-state from `rereply-214d4b1-codex.md`, with the `oos_column_plan`
refactor included in the same pass.

The intended ownership boundary stays unchanged:

- `heap_file.c` owns attribute read orchestration, `DB_VALUE` conversion, and heap record
  serialization.
- `heap_oos.cpp` owns OOS inline-reference parsing helpers, OOS file lookup, and batched OOS I/O.
- `heap_attrvalue_read()` and `heap_attrvalue_transform_to_dbvalue()` remain `static` in
  `heap_file.c`.

The plan deliberately does not move `heap_attrvalue_transform_to_dbvalue()` into `heap_oos.cpp`.
That would remove the current hand-off, but it would reopen the boundary that the latest commits
closed.

## Phase 1: Read Path Shape

Goal: remove `prefetched_oos` from `heap_attrvalue_read()` and make grouped lazy OOS Resolve explicit
in the shared read path.

1. Restore `heap_attrvalue_read()` to the scalar-only signature:

   ```c
   static int heap_attrvalue_read (RECDES *recdes, HEAP_ATTRVALUE *value,
                                   HEAP_CACHE_ATTRINFO *attr_info);
   ```

2. Update all scalar callers that currently pass `NULL`.

3. Remove the early grouped-payload branch from `heap_attrvalue_read()`. After this change it should
   only perform scalar attribute reads, including scalar OOS Resolve through
   `heap_attrvalue_point_variable()` / `heap_attrvalue_read_oos_inline()`.

4. Rename `heap_attrinfo_read_dbvalues_internal()` to:

   ```c
   heap_attrinfo_read_dbvalues_from_recdes()
   ```

   It remains load-bearing because both `heap_attrinfo_read_dbvalues()` and
   `heap_attrinfo_read_dbvalues_without_oid()` need the same post-recache read loop.

5. Split the read implementation into helpers:

   ```c
   static int heap_attrinfo_read_dbvalues_scalar (RECDES *recdes,
                                                  HEAP_CACHE_ATTRINFO *attr_info);
   static int heap_attrinfo_read_dbvalues_grouped_oos (RECDES *recdes,
                                                       HEAP_CACHE_ATTRINFO *attr_info,
                                                       std::vector<RECDES> *oos_raws);
   static int heap_attrinfo_read_dbvalues_from_recdes (THREAD_ENTRY *thread_p, RECDES *recdes,
                                                       HEAP_CACHE_ATTRINFO *attr_info);
   ```

6. Keep the current dispatch rule:

   ```text
   requested OOS values = 0 -> scalar path
   requested OOS values = 1 -> scalar path, preserving the stack scratch fast path
   requested OOS values >= 2 -> grouped path with oos_read_many()
   ```

   The existing `heap_oos_read_grouped_payloads()` already implements this gate by leaving `raws`
   empty when grouped Resolve does not apply.

7. Remove the redundant `handled` / `grouped` bool from `heap_oos_read_grouped_payloads()`.

   New contract:

   ```c
   extern int heap_oos_read_grouped_payloads (THREAD_ENTRY *thread_p, RECDES *recdes,
       HEAP_CACHE_ATTRINFO *attr_info, std::vector<RECDES> &raws);
   ```

   `raws.empty()` means grouped Resolve did not apply. A non-empty `raws` vector has one slot per
   requested attribute; `raws[i].data == NULL` means attribute `i` should use the scalar reader.

8. Implement `heap_attrinfo_read_dbvalues_from_recdes()` with this shape:

   ```text
   call heap_oos_read_grouped_payloads()
   if error:
     free partial grouped payloads
     return error
   if oos_raws.empty():
     return heap_attrinfo_read_dbvalues_scalar()
   else:
     loop through attributes:
       if oos_raws[i].data != NULL:
         heap_attrvalue_transform_to_dbvalue(..., &oos_raws[i], true)
       else:
         heap_attrvalue_read(...)
     free grouped payloads
     return status
   ```

   Cleanup must happen on every grouped path, including partial-allocation or `oos_read_many()`
   failures.

## Phase 2: Write Path Plan Struct

Goal: replace the three parallel OOS output vectors with one per-attribute plan object.

Current state:

```c
std::vector<bool> oos_columns;
std::vector<OID> oos_oids;
std::vector<DB_BIGINT> oos_lengths;
```

These three vectors are coupled by attribute index across:

- `heap_attrinfo_determine_disk_layout()`
- `heap_attrinfo_insert_to_oos()`
- `heap_attrinfo_transform_columns_to_disk()`

Introduce a local heap-file write-plan struct:

```c
struct heap_oos_column_plan
{
  bool selected = false;
  OID oid = OID_INITIALIZER;
  DB_BIGINT length = 0;
};
```

Then use:

```c
std::vector<heap_oos_column_plan> oos_plan (attr_info->num_values);
```

Implementation steps:

1. Define `heap_oos_column_plan` near the OOS write-layout helpers in `heap_file.c`.

2. Change forward declarations and definitions:

   ```c
   heap_attrinfo_determine_disk_layout (...,
                                        std::vector<heap_oos_column_plan> *oos_plan,
                                        bool *has_oos,
                                        size_t *inline_size_after_oos_ptr);

   heap_attrinfo_insert_to_oos (...,
                                std::vector<heap_oos_column_plan> *oos_plan);

   heap_attrinfo_transform_columns_to_disk (...,
                                            std::vector<heap_oos_column_plan> *oos_plan,
                                            ...);
   ```

3. In `heap_attrinfo_determine_disk_layout()`, replace:

   ```c
   (*oos_columns)[cand.attr_index] = true;
   ```

   with:

   ```c
   (*oos_plan)[cand.attr_index].selected = true;
   ```

   Keep `has_oos` as a separate output for now. It is already used by header generation and the
   OOS+bigone rejection gate, and keeping it avoids a noisy secondary scan.

4. In `heap_attrinfo_insert_to_oos()`, read `plan.selected`, fill `plan.length`, and pass
   `&plan.oid` as the `oos_insert_request` destination.

5. In `heap_attrinfo_transform_columns_to_disk()`, replace the parallel access:

   ```c
   (*oos_columns)[i], &(*oos_oids)[i], (*oos_lengths)[i]
   ```

   with:

   ```c
   plan.selected, &plan.oid, plan.length
   ```

   Keep the assertion equivalent:

   ```c
   assert (!plan.selected || !OID_ISNULL (&plan.oid));
   ```

6. Do not change the OOS write semantics. This refactor must preserve:

   - largest-first OOS demotion
   - fresh OOS OID allocation for each selected column
   - OOS+bigone rejection before any OOS record is written
   - 16-byte inline OOS stub layout `[OID | full_length]`

## Phase 3: Write Path Helper Split

Goal: keep `heap_attrinfo_insert_to_oos()` in `heap_file.c`, but make it read as orchestration.

Add local helpers:

```c
static SCAN_CODE heap_attrinfo_serialize_oos_value (THREAD_ENTRY *thread_p,
                                                    HEAP_CACHE_ATTRINFO *attr_info,
                                                    int index,
                                                    int lob_create_flag,
                                                    RECDES *payload);

static SCAN_CODE heap_attrinfo_prepare_oos_insert_requests (THREAD_ENTRY *thread_p,
                                                            HEAP_CACHE_ATTRINFO *attr_info,
                                                            int lob_create_flag,
                                                            std::vector<heap_oos_column_plan> *oos_plan,
                                                            std::vector<RECDES> *payloads,
                                                            std::vector<oos_insert_request> *requests);

static void heap_attrinfo_free_oos_payloads (std::vector<RECDES> *payloads);
```

Expected orchestration:

```text
reserve payload/request vectors
prepare serialized payloads and request spans
call heap_oos_insert_serialized_values()
free payload buffers
return S_SUCCESS/S_ERROR
```

Ownership detail:

- `payloads` owns the `RECDES::data` allocations created by `heap_attrinfo_dbvalue_to_recdes()`.
- `requests` only borrows spans into those payload buffers.
- cleanup frees `payloads`, not a local copy of `requests[i].src.data()`.

This removes the misleading current cleanup pattern where `free_and_init()` nulls only a local
`char *request_data`.

## Phase 4: Comments and Contracts

Update comments to match the new shape:

- `heap_attrvalue_read()` comment should describe scalar attribute read only.
- `heap_oos_read_grouped_payloads()` comment should no longer say the payloads are consumed by
  `heap_attrvalue_read()` or controlled by `handled`.
- `heap_attrinfo_read_dbvalues_from_recdes()` should say it is the shared read loop used by both
  public DB_VALUE read entry points.
- `heap_attrinfo_insert_to_oos()` should continue to explain why heap serialization stays in
  `heap_file.c`.

## Phase 5: Verification

Local verification:

```bash
just build
just build-test
```

Targeted OOS tests to run after the build:

```text
test_oos
test_oos_server
test_oos_sql_crud
```

Pay special attention to the CBRD-27006 dispatch test:

```text
OosSqlCrud.Cbrd27006ReadDispatchBatchesOnlyMultiOosProjections
```

Expected behavioral checks:

- 0 requested OOS values: scalar path
- 1 requested OOS value: scalar path
- 2+ requested OOS values: grouped path calls `oos_read_many()`
- `oos_debug_counters` semantics are unchanged
- OOS insert path still writes all selected OOS values and records their OOS OIDs
- rollback/update tests still prove old OOS OIDs remain valid until vacuum

## Non-Goals

- Do not move `heap_attrvalue_transform_to_dbvalue()` to `heap_oos.cpp`.
- Do not implement OOS OID reuse or deduplication.
- Do not add OOS PEEK mode.
- Do not change demotion thresholds or largest-first policy.
- Do not change OOS record format or inline stub format.

## Risk Notes

- The read-path cleanup is low to medium risk because it changes helper boundaries but should not
  alter dispatch semantics.
- The `oos_column_plan` refactor is medium risk because it touches the full write-layout chain.
  Keep it mechanical and behavior-preserving.
- The write helper split is low risk if payload ownership stays explicit and cleanup is centralized.
- The highest-risk mistake would be losing the grouped-read cleanup on error or leaving an OOS
  selected column with a NULL OOS OID before `heap_attrinfo_transform_columns_to_disk()`.
