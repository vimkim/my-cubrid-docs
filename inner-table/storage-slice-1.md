# Inner Table storage, slice 1

This plan covers the first engine slice of POC phase 2 (`storage`) in the
[POC plan](poc-plan.md). It is written for the implementer and the POC reviewer.
It was written on 2026-11-10 and updated on 2026-11-11 to match the code, against branch `inner-table` of the CUBRID
checkout `/home/vimkim/gh/cb/inner-table`, on top of baseline
`e64a04a79a5842827a124b3f8313516d0da2594c`. Source lines below refer to that
checkout. No code for this slice exists yet.

## Goal and exit predicate

Large VARCHAR values of an opted-in table are stored as rows of a chunk class.
The parent record holds a small reference instead. Clients, index-key builders
and server decoders see only ordinary complete records.

The slice passes when `accept.py --case storage-1` reports VERIFIED. That
command runs the same fixed SQL script against an opted-in table and an
ordinary oracle table. For each query, the canonical results must be equal. The
script also checks that the parent row holds a reference and that the chunk rows
exist. It covers these values:

- NULL, empty, 1 byte, threshold minus 1, threshold, threshold plus 1;
- multibyte strings;
- 64 KiB and 1 MiB values;
- for each value, INSERT, SELECT, an UPDATE of another column, an UPDATE of
  the large value, an UPDATE to a short value, DELETE, and ROLLBACK of each.

A negative control must make the checker fail: a wrong expected value, and a
chunk row deleted behind the engine's back. The second must be an error, never
NULL and never a partial value.

## Deviations from the design, accepted for this slice only

| Design | Slice 1 | Closed by |
| --- | --- | --- |
| Hidden chunk class owned by the parent | A visible companion class `<table>__inner (ck BIGINT PRIMARY KEY, chunk BIT VARYING)`, created by ordinary DDL in the test script. The key `ck` is `value_id << 20 | ord`. The server finds the class by name. | phase 5 (`transport`: drop, truncate, DDL) |
| Per-column opt-in | Hidden server parameter `inner_table_threshold` (bytes, 0 = off). A table is opted in when its companion class exists. Every VARCHAR column at or over the threshold is moved. | later slice |
| WAL-reserved ValueId counter per relation generation | An in-memory counter per companion class, seeded on first use from the largest key in its index. A rollback leaves gaps, as the design allows. After a restart an ID can be used again. That is safe for MVCC reads, because no snapshot survives a restart. | phase 3 (`recovery`) review |
| Keep the reference when the value is unchanged | Kept only when `locator_update_force` gets an attribute list that leaves the column out. Otherwise the old chunks are retired and new ones are written. | later slice |
| Projection without chunk reads | Every record fetch on the server expands references. | phase 10 (`projection`) |
| HA, CDC, flashback, TDE, loaddb multi-insert | Not handled. The parent's replication log holds references. | phases 6 to 8 |

The companion class is ordinary user data in this slice. Replicating it, or
unloading it separately, gives wrong results. The test databases are disposable
and have no HA.

## Reference format

The reference reuses the existing large-string prefix. A VARCHAR of 255 bytes
or more is written as byte `0xFF`, then int32 `compressed_len`, then int32
`decompressed_len`, then the payload
(`src/object/object_primitive.c:14648`). A reference uses
`compressed_len = -1`, then int32 `decompressed_len`, int64 `value_id`, int32
`total_len` (the byte length of the original encoding) and int32
`chunk_count`, padded to 28 bytes. The chunks hold the original encoding bytes,
so expansion restores the record byte for byte.

Only the expander may read a reference. Every other reader of the `0xFF` form
gets expanded records. The implementation must list each `0xFF` reader and
show that it never sees `-1`: `or_get_varchar_compression_lengths`
(`src/base/object_representation.h:2193`), `mr_readval_string_internal`, the
string compare functions, and `src/loaddb/load_object.c:156`. A debug assertion
at those readers rejects `-1`.

## Hook points

Write path. All user-row DML on the server goes through three functions in
`src/transaction/locator_sr.c`:

- `locator_insert_force` (4913). Before `heap_insert_logical` (5040), insert
  the chunks and build the rewritten record. The heap gets the rewritten record.
  `locator_add_or_remove_index` (5159) still gets the complete record.
- `locator_update_force` (5372). It does the same for the new record. It also
  MVCC-deletes the chunks of each old reference that the new record does not
  keep. `locator_update_index` (5950) gets complete old and new records.
- `locator_delete_force_internal` (6264). It MVCC-deletes the chunks of every
  reference in the old record. Index removal (6442) gets the complete old record.

Client force (`xlocator_force`, 7277), XASL DML (`locator_attribute_info_force`,
7613), the HA applier, and loaddb with per-row force all reach these
functions. `locator_multi_insert_force` (14144) does not. In this slice it
fails with an error for opted-in tables.

Chunk writes use `locator_attribute_info_force` on the companion class with its
own `HEAP_CACHE_ATTRINFO` and scan cache. The companion class has no companion
class, so the recursion stops after one level. The chunk rows are written by
the same transaction, inside the same statement, so rollback, savepoints and
restart undo treat them like the parent row. The chunks are written before the
parent row. On any error, the statement rolls back.

Read path. Expand references where a record leaves the heap layer:
`heap_get_visible_version_internal` (`src/storage/heap_file.c:26979`),
`heap_get_last_version` (27197), `heap_next_internal` (7553) and the
`heap_prev` variants (20528, 20554). The expander copies into the caller's
buffer and returns `S_DOESNT_FIT` when the buffer is too small, as these callers
already handle. It finds each chunk with `btree_find_unique_visible`, a new
lookup that takes the caller's snapshot and no lock. `xbtree_find_unique` would
S-lock every chunk, so a reader would wait for a writer that retires it. It reads the chunk with `heap_get_visible_version` under the
caller's snapshot, so an old snapshot reads old chunks. It checks every
ordinal from 0 to `chunk_count - 1`, and that the total length is exactly
`total_len`. A missing or malformed chunk is an error.

A record whose version comes from a WAL undo image also passes through
`heap_get_visible_version_internal`. It gets the same expansion.

Policy cache. A map in `src/storage/inner_table.cpp`, keyed by class OID,
holds the opt-in decision and the companion's class OID, HFID and index. It is
filled on first use and cleared by `heap_classrepr_decache`. With the
parameter at 0, a fetch or force call does one integer test. With the parameter
on, every call also takes a mutex for the map lookup. Phase 11 measures that
cost.

Vacuum needs no change. Chunk rows are ordinary MVCC rows. Their MVCC DELETE
makes them dead for later snapshots, and vacuum removes them after the
visibility horizon.

## Order of work

1. Build `contrib/benchmarks/inner_table/accept.py` with the `storage-1` case
   and its negative controls. Run it on the unmodified engine, where the opted-in
   table is ordinary. The value comparison then passes, and the reference check
   fails. The control shows the checker can tell the two apart.
2. Add the parameter and the `OR_CLASSREP` cache.
3. Add the reference codec and the expander, with the debug assertions. Add a
   unit test for encode and decode of the reference.
4. Add the INSERT hook, then DELETE, then UPDATE. Run `storage-1` after each.
5. Run `just test` and a focused SQL regression run on the unchanged engine
   paths. Phase 11 owns the throughput budget, so this slice records no
   performance claim.

Each step is a local commit on `inner-table`. Nothing is pushed.
