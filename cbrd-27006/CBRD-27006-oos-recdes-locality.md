# [CBRD-27006] OOS recdes locality

- JIRA: https://jira.cubrid.org/browse/CBRD-27006
- Parent: https://jira.cubrid.org/browse/CBRD-26583
- PR: https://github.com/CUBRID/cubrid/pull/7391
- Target branch: `feat/oos`
- Code branch: `CBRD-27006-oos-recdes-locality`
- Current PR HEAD: `8d053f641564ebac389ea40a4f5a7efe079693c7`
- Last checked: 2026-07-06

> Source line numbers in this document are based on PR HEAD
> `8d053f641564ebac389ea40a4f5a7efe079693c7`. They are meant for review
> navigation and may drift after another rebase.

## Purpose

CBRD-27006은 하나의 heap record (`RECDES`) 안에서 demotion 된 여러 OOS 값을 가능한 한 같은 OOS page에 배치하고, 읽을 때도 같은 head page에 있는 OOS 값을 한 번의 page fix로 처리하도록 개선한다.

AS-IS:

- `heap_attrinfo_insert_to_oos()` 가 OOS 대상 컬럼마다 `oos_insert()` 를 호출했다.
- 각 `oos_insert()` 는 bestspace 탐색과 `pgbuf_fix` 를 독립 수행했다.
- 같은 heap record에서 나온 OOS 값들이 여러 OOS page로 흩어질 수 있었다.
- lazy Resolve와 record-level Expand 모두 OOS OID마다 `oos_read()` 를 따로 호출했다.

TO-BE:

- heap attribute order대로 OOS 대상 값을 모아 `oos_insert_many()` 로 batch insert 한다.
- single-chunk OOS 값들은 page capacity 안에서 greedy run으로 묶고, run 하나는 한 OOS page에 들어가는 placement unit으로 다룬다.
- multi-chunk 값은 기존 chain insert를 유지하되, single-chunk 값과 섞여도 publication order를 보존한다.
- read path는 `oos_read_many()` 로 head page가 같은 요청들을 group하여 처리한다.
- lazy Resolve는 요청된 OOS 값이 2개 이상일 때만 batched path를 탄다. non-OOS projection과 single-OOS projection은 scalar path를 유지한다.

이 PR은 on-disk OOS format, OOS OID sharing policy, replication log format을 바꾸지 않는다. OOS OID는 여전히 값 하나당 하나이고, multi-chunk chain 구조도 그대로 유지한다.

## Scope Invariants

- OOS inline slot layout은 그대로 `[OID (8B) | full_length (8B bigint)]` 이다.
- `oos_insert_many()` 는 request order를 logical attribute order로 취급하고, 각 request의 `oid_out` 에 head OOS OID를 채운다.
- single-chunk batch는 전체 batch가 한 page에 들어갈 때만 기존 page를 재사용한다. 맞지 않으면 batch를 쪼개어 흩뿌리지 않고 fresh page를 할당한다.
- multi-chunk 값은 기존 `oos_insert_across_pages()` reverse insert와 dummy boundary marker를 유지한다.
- public OOS insert API가 replication용 OOS OID publication을 직접 수행한다. caller는 중복 push하지 않는다.
- lazy Resolve batching은 `requested OOS count >= 2` 일 때만 수행한다.
- scalar OOS read는 `IO_MAX_PAGE_SIZE` stack scratch fast path를 유지한다.

## New Public API And Types

### `oos_insert_request`

Location: `src/storage/oos_file.hpp:45-49`

```cpp
struct oos_insert_request
{
  oos_buffer src;
  OID *oid_out;
};
```

- `src`: caller-owned OOS payload byte span. OOS layer reads from it only during the call.
- `oid_out`: result pointer. Insert success writes the head OOS OID here.
- Contract: `src.data() != nullptr`, `src.size() > 0`, `src.size() <= INT_MAX`, `oid_out != NULL`.
- The request does not own memory. `heap_attrinfo_insert_to_oos()` owns and frees serialized payload buffers after `oos_insert_many()` returns.

### `oos_read_request`

Location: `src/storage/oos_file.hpp:51-55`

```cpp
struct oos_read_request
{
  OID oid;
  oos_buffer dest;
};
```

- `oid`: head OOS OID stored in heap record inline slot.
- `dest`: caller-owned destination buffer sized from inline `full_length`.
- Contract: `oid` must not be NULL, `dest.data() != nullptr`, `dest.size() > 0`, `dest.size() <= INT_MAX`.
- `oos_read_many()` fills exactly `dest.size()` bytes or reports corruption/error.

### `oos_insert_many()`

Declaration: `src/storage/oos_file.hpp:101-102`

Implementation: `src/storage/oos_file.cpp:1208-1275`

Purpose:

- Insert multiple OOS payloads in logical order.
- Keep adjacent single-chunk payloads together when they fit one OOS page.
- Preserve mixed single-chunk and multi-chunk publication order.

Line-by-line behavior:

| Lines | Behavior |
|---|---|
| `1211-1212` | Unit-test counters record call count and request count. |
| `1214-1223` | Validate every request before doing any insert: non-null source, positive size, `INT_MAX` bound, non-null `oid_out`. |
| `1226` | Read the current single-page max chunk size from `oos_get_max_chunk_size_within_page()`. |
| `1227` | Compute page payload capacity as aligned `spage_max_record_size()`. |
| `1228-1231` | Define `required_space(request)` as aligned payload length plus `OOS_RECORD_HEADER_SIZE`. |
| `1233-1235` | Iterate requests with `pos`; order is never sorted or reordered. |
| `1238-1247` | If current request is larger than one OOS page chunk, use existing `oos_insert_across_pages()`, copy the returned head OID to `oid_out`, publish that OID, then advance one request. |
| `1251-1261` | For single-chunk values, greedily extend the batch while the next single-chunk request still fits the same page. The additional request cost includes one `SPAGE_SLOT_SIZE` plus aligned record body. |
| `1263-1265` | Insert the selected single-page run with `oos_insert_single_page_batch()`, then move `pos` to `batch_end`. |
| `1268-1271` | On any error after partial publication, clear transient OOS insert publication state and return the error. |
| `1275` | Return `NO_ERROR` after all requests are inserted. |

Important detail:

- The greedy run is a placement unit, not just a loop optimization. If `oos_find_best_page()` cannot find or reuse one page for that whole run, the allocation path gives the run a fresh page.

### `oos_read_many()`

Declaration: `src/storage/oos_file.hpp:106`

Implementation: `src/storage/oos_file.cpp:1639-1766`

Purpose:

- Resolve several OOS head OIDs while reducing repeated page fixes.
- Requests sharing `(volid,pageid)` are read under one read latch.
- Multi-chunk continuations are read after the shared head page is unfixed.

Line-by-line behavior:

| Lines | Behavior |
|---|---|
| `1645-1650` | Local continuation record remembers request pointer, next chunk OID, and head payload bytes already copied. |
| `1652-1653` | Unit-test counters record call count and request count. |
| `1655-1664` | Validate every request: non-null OID, non-null destination, positive size, `INT_MAX` bound. |
| `1667-1670` | Allocate `done[]` and a continuation vector inside a narrow `std::bad_alloc` boundary. |
| `1672-1677` | Iterate original request order and skip requests already handled by an earlier page group. |
| `1679-1683` | Pick the first unhandled request's head VPID and fix that OOS page with read latch. |
| `1684-1689` | Propagate page-fix failure. |
| `1690-1693` | Ensure the fixed page is always unfixed before moving to continuations. |
| `1695` | Count one grouped head page. |
| `1697-1706` | Scan remaining requests in original order and process only those whose head VPID matches the fixed page. Mark each as done and count a read value under the fixed page. |
| `1708-1715` | Read the head chunk from the already-fixed page and validate that it is a real head chunk with the expected total length. |
| `1716-1719` | Stop on read/header error. |
| `1721-1724` | If this is a multi-chunk value, remember the continuation instead of reading the chain while the grouped page remains fixed. |
| `1725-1731` | For single-chunk values, require the writer to be full. Otherwise report corruption. |
| `1735-1756` | After the grouped page is unfixed, continue every multi-chunk chain with existing `oos_read_across_pages()`, using a writer over the remaining destination subspan. |
| `1759-1764` | Convert STL allocation failure to `ER_OUT_OF_VIRTUAL_MEMORY`. |
| `1766` | Return `NO_ERROR` after all groups and continuations are complete. |

Important detail:

- The function deliberately keeps only one OOS page fixed at a time. Multi-chunk tails are read after the head page scope ends, matching scalar `oos_read()` latch behavior.

## New Static Helpers In `oos_file.cpp`

### `oos_publish_oos_oid()`

Location: `src/storage/oos_file.cpp:1072-1076`

- Pushes a successfully inserted head OOS OID to `thread_p->oos_oids`.
- This localizes publication responsibility inside public OOS insert APIs.
- `oos_insert()` calls it on scalar success at `1122-1125`.
- `oos_insert_many()` calls it after multi-chunk insert at `1242-1246`.
- `oos_insert_single_page_batch()` calls it for every single-chunk request at `1187-1188`.

### `oos_clear_insert_publication_state()`

Location: `src/storage/oos_file.cpp:1078-1089`

- Clears `thread_p->oos_oids`.
- Looks up the current transaction descriptor and clears `tdes->oos_insert_lsa_queue` if the descriptor exists.
- Used by `oos_insert_many()` on error after partial publication (`1268-1271`).
- This prevents a caller from later consuming stale OOS OID publication state after a failed batch insert.

### `oos_insert_single_page_batch()`

Location: `src/storage/oos_file.cpp:1131-1205`

Purpose:

- Insert one already-selected single-page batch into one OOS page.
- The caller has computed `needed_space` for the whole batch.

Line-by-line behavior:

| Lines | Behavior |
|---|---|
| `1139-1144` | Find/fix one best page with enough space for the whole batch. Failure is propagated. |
| `1146-1148` | Keep `page_ptr` and remember whether the page was empty for debug counters. |
| `1150-1154` | Iterate requests in original order and build a normal head `OOS_RECORD_HEADER` for each single-chunk value. |
| `1156-1162` | Allocate and fill an `OOS_RECDES` by prepending the OOS header. |
| `1164-1167` | Ensure the temporary OOS recdes data area is freed. |
| `1169-1176` | Insert one OOS record into the fixed page. Any unexpected slotted-page failure returns `ER_GENERIC_ERROR`. |
| `1178-1185` | Build the result OID from fixed page VPID plus assigned slotid and store it through `request.oid_out`. |
| `1187` | Log the insert with existing physical OOS insert WAL record. |
| `1188` | Publish the OID for replication metadata. |
| `1191-1192` | Update bestspace hint once after the whole batch, using the remaining page free space. |
| `1194-1203` | Update unit-test counters for batch count, values per fixed page, and fresh/reused page classification. |
| `1205` | Return success. |

### `oos_read_chunk_in_page()`

Location: `src/storage/oos_file.cpp:1461-1500`

- Reads one OOS chunk from a page that is already fixed by the caller.
- Calls `spage_get_record(..., PEEK)` with the request slot.
- Verifies the slot is at least `OOS_RECORD_HEADER_SIZE`.
- Copies `OOS_RECORD_HEADER` to `header_out`.
- Appends payload bytes to the caller's `byte_span_writer`.
- Reports `ER_HEAP_OOS_CORRUPTED_RECORD` if the slot is too small or payload overflows the destination.

This helper removes duplicate code between scalar `oos_read()` and grouped `oos_read_many()`.

### `oos_check_head_header()`

Location: `src/storage/oos_file.cpp:1570-1593`

- Verifies the inline OOS OID points to a head chunk (`chunk_index == 0`).
- Verifies `header.total_data_length == expected_length`.
- Converts either mismatch to `ER_HEAP_OOS_CORRUPTED_RECORD`.

Scalar `oos_read()` uses it at `1609-1617`, and `oos_read_many()` uses it at `1711-1715`.

### `bridge_oos_debug_counters_reset()` / `bridge_oos_debug_counters_get()`

Locations:

- `src/storage/oos_file.hpp:140-153`
- `src/storage/oos_file.cpp:2537-2547`

Purpose:

- Test-only instrumentation under `CUBRID_UNIT_TEST_ENABLED`.
- Counters prove that insert batching and read grouping actually happen, and that non-OOS/single-OOS lazy Resolve does not call `oos_read_many()`.

Tracked counters:

- `insert_many_calls`
- `insert_many_requests`
- `single_page_batch_count`
- `insert_reused_pages`
- `insert_fresh_pages`
- `insert_values_per_fixed_page`
- `read_many_calls`
- `read_many_requests`
- `read_many_grouped_head_pages`
- `read_values_per_fixed_page`

## `oos_file.cpp` Refactor Map

### Header publication moved into public insert API

Changed behavior:

- Before: caller could receive an OID from `oos_insert()` and push it to `thread_p->oos_oids`.
- After: public insert APIs publish their own successful head OIDs.

Code-by-code:

| Lines | Refactor |
|---|---|
| `1072-1076` | New local publication helper pushes one OID. |
| `1091-1129` | Existing `oos_insert()` now publishes on success. |
| `1293-1299` | Multi-chunk replication comment was updated: public insert API, not immediate heap caller, pushes the real head OID after `oos_insert_across_pages()` returns. |
| deleted in PR diff | Old exported `oos_push_oos_oid()` was removed from `oos_file.cpp`; no current source line remains for it. |
| `oos_file.hpp:140-154` | The old `extern "C" oos_push_oos_oid()` declaration is gone; the current unit-test-only section contains only debug counters. |

### Scalar read keeps existing behavior but shares helpers

Code-by-code:

| Lines | Refactor |
|---|---|
| `1461-1500` | Slot read and payload append moved into `oos_read_chunk_in_page()`. |
| `1504-1522` | `oos_read_within_page()` now only fixes/unfixes the page and delegates the actual slot read. |
| `1570-1593` | Head-chunk validation moved into `oos_check_head_header()`. |
| `1599-1637` | `oos_read()` now calls `oos_read_within_page()` and then `oos_check_head_header()`, preserving scalar multi-chunk continuation and final length check. |

## `heap_file.c` New Helpers And Refactors

### `heap_attrvalue_get_vot_entry()`

Location: `src/storage/heap_file.c:10482-10511`

Purpose:

- Read the raw variable offset table entry for one variable attribute.
- Return the entry including flag bits (`OR_VAR_BIT_OOS`) so callers can test `OR_IS_OOS()`.

Line-by-line behavior:

| Lines | Behavior |
|---|---|
| `10490-10492` | Read offset-size encoding from the record header. |
| `10494-10507` | Dispatch `OR_BYTE_SIZE`, `OR_SHORT_SIZE`, `OR_INT_SIZE` and read the VOT entry with the matching macro. |
| `10508-10510` | Return `false` for corrupt/unknown offset size without setting an error. Caller decides how to report it. |

Used by:

- `heap_attrvalue_point_variable()` at `10655`.
- `heap_attrvalue_oos_inline_ptr()` at `10854`.

### `heap_attrvalue_parse_oos_inline()`

Location: `src/storage/heap_file.c:10513-10553`

Purpose:

- Validate and parse the inline OOS header `[OID | full_length]`.
- Share the scalar read and batched read parsing rule.

Line-by-line behavior:

| Lines | Behavior |
|---|---|
| `10527-10529` | Initialize outputs to NULL OID and zero length before any error path. |
| `10531-10532` | Build an `OR_BUF` over the inline pointer up to `recdes->data + recdes->length`. |
| `10534-10539` | Case 1: reject inline region shorter than `OR_OID_SIZE + OR_BIGINT_SIZE`. |
| `10541-10542` | Read OID and bigint length. |
| `10544-10550` | Cases 2 and 3: reject read failure, NULL OID, non-positive length, and length above `INT_MAX`. |
| `10552` | Return `NO_ERROR` with parsed OID and length. |

Used by:

- Scalar `heap_attrvalue_read_oos_inline()` at `10578-10585`.
- Batched lazy Resolve preparation at `10902-10912`.

### `heap_attrvalue_oos_inline_ptr()`

Location: `src/storage/heap_file.c:10828-10860`

Purpose:

- Probe whether one requested attribute is an inline-OOS variable value in the current record.
- Return the inline OOS header pointer only for requested attributes that would actually need OOS Resolve.

Line-by-line behavior:

| Lines | Behavior |
|---|---|
| `10842-10845` | Ignore duplicate-key pseudo attributes. |
| `10847-10852` | Ignore missing record, missing representation, shared/class attrs, fixed attrs, and NULL variable attrs. |
| `10854-10857` | Read VOT entry and return NULL if the attr is not OOS or offset-size is invalid. |
| `10859` | Return pointer to inline OOS header inside recdes. |

Important detail:

- Invalid offset size is treated as "not batched" by the probe. If the scalar path later reads the attribute, it reports `ER_GENERIC_ERROR` from `heap_attrvalue_point_variable()`. This preserves scalar error ownership.

### `heap_attrinfo_read_dbvalues_batched_oos()`

Location: `src/storage/heap_file.c:10862-10944`

Purpose:

- Resolve requested OOS attributes for one record with one `oos_read_many()` call, then transform OOS raw buffers and scalar-read the remaining requested attributes.
- The dispatcher calls this only when at least two requested attrs are OOS.

Line-by-line behavior:

| Lines | Behavior |
|---|---|
| `10873-10877` | Prepare vectors for per-attribute raw buffers and OOS read requests. |
| `10879-10889` | Allocate vector capacity/slots; convert `std::bad_alloc` to `ER_OUT_OF_VIRTUAL_MEMORY`. |
| `10891-10900` | Walk requested attributes and skip non-OOS attrs. |
| `10902` | Parse inline OOS header with the shared parser. |
| `10903-10907` | Allocate exact destination buffer for the OOS value. |
| `10908-10913` | Fill `raws[i]` length and append one `oos_read_request`. Request order follows requested attribute order. |
| `10916-10919` | Resolve all prepared OOS requests with `oos_read_many()`. |
| `10921-10928` | For OOS attrs, transform the raw OOS bytes to `DB_VALUE` with COPY semantics. |
| `10929-10932` | For non-OOS attrs, call the scalar `heap_attrvalue_read()` path. |
| `10935-10941` | Free every allocated raw buffer on success or error. |
| `10943` | Return final error/success. |

Trade-off:

- This path holds all requested OOS raw buffers until transformation finishes. It is intentionally gated to `>= 2` requested OOS values so the allocation cost is paid only when page-fix batching can help.

### `heap_attrinfo_read_dbvalues_internal()`

Location: `src/storage/heap_file.c:10946-10986`

Purpose:

- Central dispatch for both public attribute-read entry points.
- Avoid duplicated scalar loops in `heap_attrinfo_read_dbvalues()` and `heap_attrinfo_read_dbvalues_without_oid()`.

Line-by-line behavior:

| Lines | Behavior |
|---|---|
| `10959` | Only consider batching when the record exists and has `OR_MVCC_FLAG_HAS_OOS`. |
| `10961-10969` | Count requested OOS attributes with `heap_attrvalue_oos_inline_ptr()`, stopping after 2. |
| `10970-10973` | If at least two requested OOS attrs are present, call the batched wrapper. |
| `10976-10983` | Otherwise run the existing scalar per-attribute `heap_attrvalue_read()` loop. |
| `10985` | Return success after scalar loop. |

Dispatch rule:

```text
requested OOS values = 0 -> scalar path
requested OOS values = 1 -> scalar path, stack scratch fast path preserved
requested OOS values >= 2 -> batched path with oos_read_many()
```

### `heap_attrvalue_read_oos_inline()` refactor

Location: `src/storage/heap_file.c:10555-10623`

Changed code:

| Lines | Refactor |
|---|---|
| `10578-10585` | Inline OOS header parsing moved to `heap_attrvalue_parse_oos_inline()`. |
| `10587-10603` | Existing stack scratch / heap allocation behavior remains. Values up to `IO_MAX_PAGE_SIZE` still avoid heap allocation. |
| `10605-10618` | Existing scalar `oos_read()` call and error cleanup remain. |
| `10620-10622` | Length and ownership outputs are set as before. |

### `heap_attrvalue_point_variable()` refactor

Location: `src/storage/heap_file.c:10639-10685`

Changed code:

| Lines | Refactor |
|---|---|
| `10655-10660` | Duplicated offset-size switch replaced by `heap_attrvalue_get_vot_entry()`. |
| `10662-10667` | OOS flag check remains; OOS values route to scalar inline read. |
| `10668-10682` | Non-OOS variable length handling remains unchanged. |

### `heap_attrinfo_read_dbvalues()` and `_without_oid()` refactor

Locations:

- `src/storage/heap_file.c:11182-11238`
- `src/storage/heap_file.c:11240-11286`

Changed code:

- Both public entry points still perform representation recache first.
- Both now call `heap_attrinfo_read_dbvalues_internal()` instead of duplicating a for-loop over `heap_attrvalue_read()`.
- Instance cache update in `heap_attrinfo_read_dbvalues()` remains after successful read.
- Error exit behavior remains unchanged.

### `heap_attrinfo_dbvalue_to_recdes()` refactor

Location: `src/storage/heap_file.c:12552-12638`

Changed code:

| Lines | Refactor |
|---|---|
| `12620-12624` | When serialized DB_VALUE length exceeds current `recdes->area_size`, allocate an exact-size buffer. |
| `12625-12629` | New allocation failure check sets `ER_OUT_OF_VIRTUAL_MEMORY` and returns `S_ERROR`. |
| `12632-12635` | Serialization into `recdes->data` remains unchanged. |

Reason:

- The new insert batching path initializes per-OOS-value `RECDES` with `data == NULL` and `area_size == 0`, so allocation failure must be explicit.

### `heap_attrinfo_insert_to_oos()` refactor

Location: `src/storage/heap_file.c:12640-12734`

Purpose:

- Replace per-column scalar `oos_insert()` with one logical-order `oos_insert_many()` call.
- Keep serialized payload buffers stable until batch placement is decided and inserted.

Line-by-line behavior:

| Lines | Behavior |
|---|---|
| `12646-12652` | Local state now includes OOS VFID, transaction descriptor, request vector, and final `scan_code`. |
| `12654-12661` | Find class heap info and create/find OOS file as before. |
| `12663-12670` | Resolve current transaction descriptor, reporting fatal tran-index error if missing. |
| `12672-12673` | Clear OOS insert LSA queue and thread OOS OID vector before starting the OOS write. |
| `12675-12684` | Reserve request vector capacity; convert vector allocation failure to `ER_OUT_OF_VIRTUAL_MEMORY`. |
| `12686-12695` | Walk attributes in `attr_info->values[]` order and skip non-OOS-selected columns. |
| `12697-12698` | Assert selected columns are real variable DB_VALUEs. |
| `12700-12704` | Serialize the DB_VALUE into an exact-size `RECDES`. |
| `12706-12711` | Reject impossible empty/null serialized payloads and free any transient buffer. |
| `12713` | Record payload length in `oos_lengths[i]`; this length is written into the heap inline OOS header later. |
| `12714-12715` | Append `oos_insert_request` with payload span and destination `&(*oos_oids)[i]`. |
| `12718-12723` | If at least one request exists, call `oos_insert_many()` once. |
| `12725` | Mark success after batch insert succeeds. |
| `12727-12732` | Free every serialized payload buffer on all paths. |
| `12733` | Return `S_SUCCESS` or `S_ERROR`. |

Important detail:

- This code intentionally serializes all selected OOS values before inserting any of them. That gives `oos_insert_many()` stable request spans and preserves attribute order, but it increases peak memory versus the old per-column insert/free path.

## `heap_oos.cpp` Refactor

### `heap_oos_read_blobs()`

Location: `src/storage/heap_oos.cpp:122-185`

Purpose:

- Record-level OOS Expand needs every OOS value in the recdes.
- It now prepares all OOS read requests first and calls `oos_read_many()` once.

Line-by-line behavior:

| Lines | Behavior |
|---|---|
| `131` | New request vector for grouped OOS reads. |
| `133-138` | Iterate variable attributes and skip non-OOS VOT entries. |
| `140-147` | Validate inline OOS slot stays inside the source recdes. |
| `149-168` | Parse inline OID and full length, preserving existing corruption checks. |
| `171` | Resize per-attribute `state->oos_blobs[i]` destination buffer. |
| `172-175` | Append one `oos_read_request`. |
| `178-185` | If requests exist, resolve all of them through `oos_read_many()`. |

Effect:

- Expand still materializes every OOS value, but head pages shared by those OOS OIDs are fixed once per group instead of once per OID.

## `locator_sr.c` Refactor

### `locator_oos_insert_force()`

Location: `src/transaction/locator_sr.c:5276-5335`

Changed code:

- The replication apply scalar caller still finds/creates the OOS file and calls `oos_insert()`.
- The old caller-side `oos_push_oos_oid(thread_p, &oos_oid)` call was removed after the `oos_insert()` call.
- Reason: `oos_insert()` now publishes the returned OID itself on success. Keeping the caller push would duplicate publication and corrupt OOS replication metadata ordering.

## Test Additions

### Server OOS unit tests

File: `unit_tests/oos/test_oos_server.cpp`

Added helpers:

- `clear_oos_insert_publication_state_for_test()` (`42-53`): test-local copy of publication state clear.
- `build_insert_requests()` (`55-69`): builds payload spans and OID output slots.
- `assert_read_many_payloads()` (`71-92`): reads a request vector with `oos_read_many()` and compares payloads.

New/updated CBRD-27006 tests:

| Test | Lines | Coverage |
|---|---:|---|
| `OosInsertManyKeepsSinglePageLocalityAndReadManyGroupsHeadPage` | `162-203` | Three single-chunk values land on one page; grouped read uses one head page. |
| `OosInsertManyReusesOnlyPageThatFitsWholeBatch` | `205-239` | Existing page is reused only when it fits the whole batch. |
| `OosInsertManyAllocatesFreshPageInsteadOfScatteringBatch` | `241-284` | If candidate pages cannot fit the whole batch, values go to a fresh shared page rather than being scattered. |
| `OosInsertManySplitsOversizedSingleChunkRun` | `286-318` | Greedy run splits when total single-chunk values exceed one page. |
| `OosInsertManyPreservesMixedSingleAndMultiChunkPublicationOrder` | `320-367` | Single/multi/single payload sequence publishes OIDs in logical order, allowing the multi-chunk dummy marker. |

### SQL CRUD tests

File: `unit_tests/oos/sql/test_oos_sql_crud.cpp`

New/updated CBRD-27006 tests:

| Test | Lines | Coverage |
|---|---:|---|
| `Cbrd27006MultiOosColumnSelectsAndUpdate` | `131-180` | Multiple OOS columns can be selected and updated correctly. |
| `Cbrd27006MixedSingleChunkAndMultiChunkRow` | `182-217` | One row can mix single-chunk and multi-chunk OOS values. |
| `Cbrd27006ReadDispatchBatchesOnlyMultiOosProjections` | `219-266` | Non-OOS projection and single-OOS projection do not call `oos_read_many()`; two requested OOS values do. |

## Review-Focused Code Paths

### Insert locality path

```text
heap_attrinfo_insert_to_oos()
  -> serialize selected OOS DB_VALUEs into stable RECDES buffers
  -> build oos_insert_request[] in attr_info order
  -> oos_insert_many()
       -> multi-chunk value: oos_insert_across_pages()
       -> single-chunk run: oos_insert_single_page_batch()
            -> oos_find_best_page(needed_space for whole batch)
            -> spage_insert each request into same fixed page
            -> log each OOS record
            -> publish each OID
            -> update bestspace once
```

Review points:

- `requests` order must match logical attribute order.
- `needed_space` must represent the whole single-page batch, not one value.
- A reused page is valid only if the entire run fits.
- Partial publication is cleared on error.

### Lazy Resolve path

```text
heap_attrinfo_read_dbvalues()
  -> heap_attrinfo_read_dbvalues_internal()
       -> count requested inline-OOS attrs up to 2
       -> 0 or 1 OOS request: scalar heap_attrvalue_read()
       -> >=2 OOS requests: heap_attrinfo_read_dbvalues_batched_oos()
            -> parse inline OOS headers
            -> allocate destination buffers
            -> oos_read_many()
            -> transform OOS raws to DB_VALUE
            -> scalar-read non-OOS attrs
            -> free raw buffers
```

Review points:

- A record having `HAS_OOS` is not enough to batch. Requested attrs must include at least two OOS values.
- Scalar single-OOS reads keep the stack scratch optimization.
- Batched read must not read unrelated OOS columns that were not requested.

### Record-level Expand path

```text
heap_record_replace_oos_oids()
  -> heap_oos_read_blobs()
       -> collect every OOS inline header
       -> oos_read_many()
       -> rebuild expanded record
```

Review points:

- Expand consumes raw recdes bytes, so it still needs every OOS value.
- Grouped read is safe because `oos_read_many()` handles multi-chunk continuation after unfixing the shared head page.

## Trade-offs And Limits

- Insert peak memory increases for wide OOS rows because all selected OOS values are serialized before `oos_insert_many()` runs.
- Batched lazy Resolve holds all requested OOS raw buffers until DB_VALUE conversion completes. The latest PR update reduces the impact by dispatching only when at least two requested OOS values exist.
- `std::bad_alloc` catches are used as narrow STL allocation boundaries for `std::vector` operations and converted to CUBRID error codes. They are not used for normal control flow.
- Test helper `clear_oos_insert_publication_state_for_test()` duplicates the production clear logic because the production helper is static. If more fields join OOS publication state, tests and production must be updated together or a bridge/helper should be exposed.
- This PR does not implement OOS OID reuse, deduplication, PEEK mode for OOS reads, multi-column combined OOS records, continuation-page locality, or a replication log format change.

## Verification Notes

PR comments reported the following local verification after the first follow-up:

- debug build completed
- OOS SQL suite passed `7/7`
- `ctest` passed `23/23`

The latest PR update adds/keeps the dispatch proof in
`OosSqlCrud.Cbrd27006ReadDispatchBatchesOnlyMultiOosProjections`, where:

- selecting only `small_col` on an OOS record leaves `read_many_calls == 0`
- selecting only `c1` leaves `read_many_calls == 0`
- selecting `c1 + c2` increments `read_many_calls == 1`, `read_many_requests == 2`, and `read_many_grouped_head_pages == 1`

## PR Body Summary

For PR body/public reviewer context, this is the compact version:

- Add `oos_insert_many()` and `oos_read_many()` to improve per-record OOS page locality.
- Batch single-chunk OOS inserts by logical attribute order and keep one single-page run on one OOS page.
- Keep multi-chunk chain format and replication boundary behavior unchanged.
- Move OOS insert publication into public insert APIs.
- Batch OOS reads by head page for record-level Expand and multi-OOS lazy Resolve.
- Dispatch lazy Resolve batching only when at least two requested attrs are OOS, preserving scalar fast paths for non-OOS and single-OOS projections.
- Add unit and SQL tests for locality, grouped read, mixed single/multi-chunk rows, publication order, and dispatch gating.
