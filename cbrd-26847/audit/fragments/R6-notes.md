# R6-notes — CBRD-26847 reverse audit: RECDES exclusion ledger (non-heap-instance populations)

- Agent: `rev-exclude`
- source anchor: `6816023df4ed910687523ab4d34bf667ab32b9cd`
- Scope: sweep the whole server source for RECDES populations, classify every NON-heap-instance
  population as an X-row (EXCLUDED, provenance-based rationale), and record every file's bucket so
  no population is silently skipped. Genuine heap-instance images that surfaced and are off the
  forward agents' beaten path are recorded as R-rows and cross-noted.
- Output: `fragments/R6.tsv` — 34 rows (23 X-rows X-501..X-524 with X-511 promoted to R-511; 11 R-rows R-501..R-511).

> **NEVER modified the read-only source tree.** All writes are to this docs area only.

---

## Load-bearing invariants confirmed first-hand

1. **OOS demotion has exactly one site.** `heap_attrinfo_determine_disk_layout`
   (`src/storage/heap_file.c:12095`) is the only code that sets `has_oos` / builds OOS inline stubs,
   and it is called only from `heap_attrinfo_transform_to_disk_internal` (`heap_file.c:13033`), the
   server-side dbvalue→disk transform for **instance** records built from a `HEAP_CACHE_ATTRINFO`.
   Any record that does not pass through this function cannot acquire OOS inline stubs. This is the
   backbone of every "OOS-free by construction" exclusion rationale below.

2. **OOS + REC_BIGONE is rejected at write time.** `heap_file.c:13059-13064`:
   `if (unlikely (has_oos && heap_is_big_length ((int) inline_size_after_oos))) er_set (... ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE ...); return S_ERROR;`
   — fired *after* demotion and *before* `heap_attrinfo_insert_to_oos`, so no orphan OOS chains are
   written on rejection. Error code `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE = -1379` (`src/base/error_code.h:1776`).
   Consequence: a `REC_BIGONE` overflow body can never contain OOS inline stubs (see R-511 / ambiguity below).
   (Spec note: OOS-CONTEXT.md §1 cites this code as `-1375`; the checked-out source uses `-1379`.
   Recorded as a stale-spec observation, not a conformance gap.)

---

## Search ledger

```text
검색 목적: 전체 서버 소스에서 RECDES 사용 파일 전수 확보 (누락 없는 closure 기준점)
source anchor: 6816023df
명령: rg -l '\bRECDES\b' src | sort
raw candidate 수: 82 파일
included: 82 (전부 bucket 배정 — 아래 file→bucket 표)
excluded: 0 (모든 파일 분류됨)
duplicate: 0
pending: 0
새로 발견한 symbol/alias: OOS_RECDES(alias of RECDES, oos_file.hpp:38), oos_record_header(oos_file.hpp:26),
  CATALOG_RECORD.recdes, SORT_REC, OOS_HDR_STATS, heap_recdes_compute_oos_flag_debug
다음 검색어: 각 exclusion family 별 population site 확인 (아래 블록들)
```

```text
검색 목적: OOS demotion 유일 site 및 OOS+bigone 거부 지점 확정
source anchor: 6816023df
명령: rg -n 'ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE|heap_attrinfo_determine_disk_layout|heap_get_bigone_content|heap_is_big_length' src/storage/heap_file.c
raw candidate 수: demotion 정의 1 + 호출 1, 거부 1, bigone 다수
included: heap_file.c:12095(demotion 정의), :13033(유일 호출), :13059-13064(OOS+bigone 거부), :20172(bigone content), error_code.h:1776(-1379)
excluded: 그 외 heap_is_big_length 호출은 일반 bigone 경로 (OOS 무관)
duplicate: 0
pending: 0
새로 발견한 symbol: ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE=-1379 (OOS-CONTEXT는 -1375로 stale)
```

```text
검색 목적: b-tree / sort / list / overflow family RECDES provenance (X-501..X-510)
source anchor: 6816023df
명령: btree.c/btree_load.c/list_file.c/external_sort.c/extendible_hash.c/overflow_file.c 정독 (Explore)
raw candidate 수: 6개 subsystem
included(excluded family): X-501 btree leaf key, X-502 btree overflow OID, X-503 btree_load build key,
  X-504 qfile sort key, X-505 qfile list tuple, X-506 sort run tuple, X-507 sort long overflow,
  X-508 ehash bucket, X-509 ehash long-key overflow, X-510 generic overflow body
included(heap-instance, cross-note): R-501 btree_load base-table heap scan (heap_next/heap_next_1page → heap_attrinfo_read_dbvalues)
duplicate: 0 / pending: 0
새로 발견한 symbol: btree_read_record(btree.c:4258), qfile_make_sort_key(list_file.c:3510),
  sort_spage_get_record(external_sort.c:647), overflow_get_nbytes(overflow_file.c:751)
```

```text
검색 목적: OOS storage / catalog-file / 물리 slotted-page / 버퍼 plumbing (X-512..X-518)
source anchor: 6816023df
명령: oos_file.cpp/oos_util.cpp/system_catalog.c/catalog_class.c/slotted_page.c/record_descriptor.cpp/storage_common.c/file_manager.c/tde.c 정독
included(excluded): X-512 OOS chunk record, X-513 OOS_HDR_STATS, X-514 catalog disk repr,
  X-515 spage generic, X-516 record_descriptor container, X-517 recdes buffer plumbing, X-518 file layer,
  X-524 oos_util debug auditor
included(heap-instance, cross-note): R-508 catcls catalog-CLASS instances(OOS-free by construction),
  R-509 TDE keyinfo(OOS-free), R-511 bigone body(OOS-free by rejection invariant)
duplicate: 0 / pending: 0
새로 발견한 symbol: oos_prepend_header(oos_file.cpp:1097), catalog_put_record_into_page(system_catalog.c:1086),
  catcls_put_or_value_into_record(catalog_class.c:3518), spage_get_record_data(slotted_page.c:3851)
```

```text
검색 목적: class/schema serialization + client + 기타 서버 heap-instance reader (X-519..X-524, R-502..R-510)
source anchor: 6816023df
명령: transform_cl.c/object_representation*.c/work_space.c/serial.c/dblink_global_tran_catalog.c/
  histogram_sampler_sr.cpp/lock_manager.c/boot_sr.c/sp_code.cpp/connection_support.cpp 정독 + 정책 토큰 확인
included(excluded): X-519 class/schema disk record(client tf_class_to_disk, demotion 미경유),
  X-520 OR_BUF generic primitives, X-521 or_pack_recdes network pack, X-522 css byte buffer,
  X-523 client workspace passthrough
included(heap-instance, cross-note): R-502 serial(_db_serial), R-503 sp_code(_db_stored_procedure_code),
  R-504 histogram sampler, R-505 dblink catalog, R-506 connection auth scan, R-507 lock_manager diag,
  R-510 boot_Db_parm
duplicate: 0 / pending: 0
새로 발견한 symbol: tf_class_to_disk(transform_cl.c:4546), tf_mem_to_disk(transform_cl.c:781, instance, client),
  or_pack_recdes(object_representation.c:1764)
finding: R6-F1(serial), R6-F2(sp_code), R6-F3(lock_manager diag) — CONSUME_RAW_BYTES over-Expand 의심 (아래)
```

---

## Complete file → bucket closure table (all 82 files)

Buckets: `X-###`/`R-###` = handled in R6.tsv; `→agent` = heap-instance population owned by another
agent's scope (cross-noted, not re-audited here). `.h/.hpp decl` = declaration/typedef only, no
population; folded into the sibling `.c/.cpp` row.

| File | Bucket | Note |
|------|--------|------|
| src/storage/btree.c | X-501, X-502 | b-tree leaf/non-leaf key records + overflow OID-list records |
| src/storage/btree.h | X-501 decl | |
| src/storage/btree_load.c | X-503 + R-501 | build-side key records (X-503); base-table heap scan for key extraction (R-501, heap-instance) |
| src/storage/btree_load.h | X-503 decl | |
| src/query/list_file.c | X-504, X-505 | qfile sort-key + qfile list-file tuple |
| src/query/list_file.h | X-504 decl | |
| src/storage/external_sort.c | X-506, X-507 | sort run tuple + long-record overflow spill |
| src/storage/external_sort.h | X-506 decl | |
| src/storage/extendible_hash.c | X-508, X-509 | ehash bucket record + long-key overflow |
| src/storage/overflow_file.c | X-510 | generic multipage overflow store |
| src/storage/overflow_file.h | X-510 decl | |
| src/storage/oos_file.cpp | X-512, X-513 | OOS chunk records + OOS_HDR_STATS bestspace header |
| src/storage/oos_file.hpp | X-512 decl | OOS_RECDES alias, oos_record_header struct |
| src/storage/oos_util.cpp | X-524 | debug-only HAS_OOS recompute (no population) |
| src/storage/oos_util.hpp | X-524 decl | |
| src/storage/system_catalog.c | X-514 | CT catalog-file disk-representation records |
| src/storage/system_catalog.h | X-514 decl | |
| src/storage/slotted_page.c | X-515 | generic physical slotted-page record ops |
| src/storage/slotted_page.h | X-515 decl | |
| src/storage/record_descriptor.cpp | X-516 | generic C++ RECDES container |
| src/storage/record_descriptor.hpp | X-516 decl | |
| src/storage/storage_common.c | X-517 | RECDES buffer alloc/attach plumbing |
| src/storage/storage_common.h | X-517 decl | |
| src/storage/file_manager.c | X-518 | physical file layer; one class-record read for validity |
| src/object/transform_cl.c | X-519 | client tf_class_to_disk (class/schema); tf_mem_to_disk (instance, client-side, cross-note fwd-locator) |
| src/object/transform_cl.h | X-519 decl | |
| src/object/object_representation.c | X-520, X-521 | generic OR primitives + or_pack_recdes network pack |
| src/base/object_representation.h | X-520 | generic OR macros/decl |
| src/base/object_representation_sr.c | X-520 | orc_* class-record introspection over caller RECDES |
| src/base/object_representation_sr.h | X-520 decl | |
| src/connection/connection_support.cpp | X-522 + R-506 | css byte buffers (not recdes); auth-class heap scan (R-506) |
| src/object/work_space.c | X-523 | client WS_MOP recdes passthrough |
| src/object/work_space.h | X-523 decl | |
| src/storage/catalog_class.c | R-508 | catalog-CLASS instances; OOS-free by construction (hand OR-serialization) |
| src/storage/catalog_class.h | R-508 decl | |
| src/storage/tde.c | R-509 | TDE keyinfo heap record; OOS-free (hand-built fixed struct) |
| src/transaction/boot_sr.c | R-510 | boot_Db_parm root record; OOS-free (hand-built fixed struct) |
| src/query/serial.c | R-502 | _db_serial instance read (CONSUME over-Expand suspect, R6-F1) |
| src/sp/sp_code.cpp | R-503 | _db_stored_procedure_code instance read (CONSUME over-Expand suspect, R6-F2) |
| src/optimizer/histogram/histogram_sampler_sr.cpp | R-504 | stats sampler heap scans (DONT_CONSUME, conforms) |
| src/query/dblink_global_tran_catalog.c | R-505 | dblink global-tran catalog heap reads (DONT_CONSUME, conforms) |
| src/transaction/lock_manager.c | R-507 | diagnostic MVCC-header read (CONSUME over-Expand suspect, R6-F3) |
| src/storage/heap_file.c | →fwd-heap (+R-511) | heap instance transform/fetch; heap_get_bigone_content (R-511) lives here |
| src/storage/heap_file.h | →fwd-heap | |
| src/storage/heap_oos.cpp | →fwd-heap | heap_record_replace_oos_oids (Expand) |
| src/storage/heap_oos.hpp | →fwd-heap | |
| src/transaction/locator_sr.c | →fwd-locator | server locator fetch / LC_COPYAREA |
| src/transaction/locator_sr.h | →fwd-locator | |
| src/transaction/locator_cl.c | →fwd-locator | client locator |
| src/transaction/locator.h | →fwd-locator | |
| src/communication/network_interface_cl.h | →fwd-locator | client net iface decl |
| src/query/scan_manager.c | →fwd-query | heap/list/index scan managers |
| src/query/query_executor.c | →fwd-query | |
| src/query/query_evaluator.c | →fwd-query | |
| src/query/query_evaluator.h | →fwd-query | |
| src/query/query_opfunc.c | →fwd-query | |
| src/query/query_hash_scan.c | →fwd-query | |
| src/query/query_aggregate.hpp | →fwd-query | |
| src/query/partition.c | →fwd-query | |
| src/query/partition_sr.h | →fwd-query | |
| src/query/parallel/px_scan/index/px_scan_index_leaf_page_dispatcher.cpp | →fwd-query | parallel index scan |
| src/query/parallel/px_scan/index/px_scan_index_leaf_slot_walker.cpp | →fwd-query | btree leaf key (X-501-like) + heap fetch DONT_CONSUME (:456) |
| src/query/parallel/px_scan/index/px_scan_index_leaf_slot_walker.hpp | →fwd-query | |
| src/query/parallel/px_scan/index/px_scan_index_overflow_drain_fsm.cpp | →fwd-query | btree overflow OID drain |
| src/query/parallel/px_scan/px_scan_slot_iterator.hpp | →fwd-query | |
| src/query/vacuum.c | →rev-cdc | vacuum / OOS cleanup |
| src/query/vacuum.h | →rev-cdc | |
| src/query/vacuum_oos.cpp | →rev-cdc | OOS vacuum forward-walk |
| src/query/vacuum_oos.hpp | →rev-cdc | |
| src/transaction/flashback.c | →rev-cdc | flashback log scan |
| src/transaction/log_manager.c | →rev-wal | WAL append/undo/redo recdes |
| src/transaction/log_manager.h | →rev-wal | |
| src/transaction/log_recovery.c | →rev-wal | recovery redo recdes |
| src/transaction/log_recovery.h | →rev-wal | |
| src/transaction/log_tran_table.c | →rev-wal | |
| src/transaction/log_applier.c | →rev-repl | replication apply |
| src/executables/compactdb.c | →rev-util | compactdb utility |
| src/executables/unload_object.c | →rev-util | unloaddb |
| src/loaddb/load_object.c | →rev-util | loaddb (OOS-blind — see OOS-CONTEXT §3 CBRD-26948) |
| src/loaddb/load_object.h | →rev-util | |
| src/loaddb/load_server_loader.cpp | →rev-util | server-side loader |
| src/storage/compactdb_sr.c | →rev-util | server compactdb |

Every file appears exactly once (with `+` when a file legitimately carries two provenances, e.g.
btree_load.c and connection_support.cpp). No file was silently skipped.

---

## Ambiguities and reasoning (required call-outs)

### A. Overflow / REC_BIGONE (R-511) — heap-instance image, but OOS-free by invariant

`heap_get_bigone_content` (`heap_file.c:20172` → `heap_ovf_get` → `overflow_get`) *does*
reassemble a **heap instance record body** into a RECDES — this is genuinely a heap-instance image,
so it is an R-row, not an X-row. However it is **OOS-incapable** because OOS + `REC_BIGONE` is
rejected at write time (`heap_file.c:13059-13064`, `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`, before any OOS
chain is written). A record carrying OOS stubs can therefore never reach `REC_BIGONE` storage, so a
bigone body read back can never contain stubs → no Expand is ever required → classification
`STORED_SAFE` / `PRESERVE_PHYSICAL`, `oos_capable=no`. The *generic* multipage overflow store
(`overflow_file.c`, X-510) is separately excluded as a physical, caller-agnostic layer (also used by
btree overflow OID lists, ehash long keys, and FILE_TEMP sort spills).

### B. Class / schema records (X-519) — cannot contain OOS stubs

Class/schema objects are serialized on the **client** by `tf_class_to_disk` (`transform_cl.c:4546`,
via `root_to_disk`/`class_to_disk`) into a pre-formed disk RECDES and shipped raw to the server for
insertion. They never pass through `heap_attrinfo_transform_to_disk_internal` /
`heap_attrinfo_determine_disk_layout` — the sole OOS demotion site (invariant 1). The only `OOS`
token in `transform_cl.c` is a read-path comment at :628. Therefore class records **cannot** acquire
OOS inline stubs: `oos_capable=no`, EXCLUDED. (`tf_mem_to_disk`, :781, is the client-side *instance*
serializer; it builds the MVCC-headed instance image but the OOS demotion still happens server-side on
re-transform — cross-noted to fwd-locator, not claimed here.)

### C. Catalog-CLASS instances (R-508) and other hand-serialized heap rows (R-509, R-510) — OOS-free by construction

`_db_class`/`_db_attribute`/… **instances** are built by `catcls_put_or_value_into_record`
(`catalog_class.c:3518`: `or_init` on the record buffer + `catcls_put_or_value_into_buffer`) and stored
via `heap_update_logical` — they are hand OR-serialized and **bypass** the attrinfo→disk demotion path,
so they never get OOS stubs. Same construction pattern for the TDE keyinfo heap (`tde.c:202-210`, a
fixed `[repid_and_flag | TDE_KEYINFO]` REC_HOME buffer) and the root `boot_Db_parm` record
(`boot_sr.c:5054`, REC_HOME struct). All three are genuine heap instances (hence R-rows) but
`oos_capable=no`; classification `STORED_SAFE`/`PRESERVE_PHYSICAL`. Followup R-508 asks fwd-heap to
confirm that catalog system-classes are *intentionally* excluded from OOS demotion.

### D. `spage_get_record` / `record_descriptor` / OR primitives are provenance-neutral

X-515 (`slotted_page.c:3851 spage_get_record_data`), X-516 (`record_descriptor.cpp`), X-517
(`storage_common.c` buffer helpers), and X-520 (`object_representation*` / `orc_*`) are all
page-/record-kind-agnostic. They populate whatever the caller's page slot or buffer holds. They are
excluded as physical/generic layers; their OOS relevance is entirely determined by the caller (heap
instance callers are covered by fwd-heap/fwd-query).

---

## Findings (over-Expand suspects — perf, not correctness; handed to forward agents)

These heap-instance readers use `HEAP_RECDES_CONSUME_RAW_BYTES` (Expand ON) but then consume the
record only through the attribute layer (`heap_attrinfo_read_dbvalues`) or a fixed-position header
read — neither of which requires Expand. Expanding eagerly is not *wrong* (values still resolve
correctly) but it forces a full record reconstruction where the cheap DONT_CONSUME fetch would let the
attribute layer resolve OOS lazily per column. This mirrors the OOS-CONTEXT §3 census pattern
("~17 mechanically migrated sites should revert to the cheap fetch"). **Not adjudicated here** — the
forward agents own the final policy call; recorded as candidate over-Expand only.

- **R6-F1** — `src/query/serial.c:233/510/647`: `_db_serial` read with `CONSUME_RAW_BYTES`, consumed
  via `heap_attrinfo_read_dbvalues`. Values are tiny in practice, so the leak/perf impact is minimal,
  but DONT_CONSUME is the correct policy. → fwd-misc.
- **R6-F2** — `src/sp/sp_code.cpp:90`: `_db_stored_procedure_code` read with `CONSUME_RAW_BYTES`,
  single-attr read via attribute layer. The SP code/source attribute is exactly the kind of large
  value that OOS demotes, so this one materially over-Expands. → fwd-misc.
- **R6-F3** — `src/transaction/lock_manager.c:5642`: lock-timeout diagnostic reads with
  `CONSUME_RAW_BYTES` then only `or_mvcc_get_header` (the fixed-position MVCC header, which precedes
  the variable area / OOS stubs). Header-only reads never need Expand. Diagnostic path, low impact. → fwd-misc.

CONFORMS (correct DONT_CONSUME / attribute-layer) heap-instance readers found: R-501 (btree_load),
R-504 (histogram), R-505 (dblink), R-506 (connection).
