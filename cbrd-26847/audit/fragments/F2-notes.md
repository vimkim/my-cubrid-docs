# F2 notes — forward audit of src/transaction/locator_sr.c (+ locator_sr.h)

Scope: CBRD-26847 OOS raw-RECDES consumption policy. Repo (read-only): /home/vimkim/gh/cb/CBRD-26847-oos-visible-version @ 6816023df.
Rows: F-101 .. F-129 in F2.tsv (26 explicit policy sites + 3 policy-parameter getters).

Policy enum: HEAP_RECDES_CONSUMPTION_POLICY (heap_file.h:363-372).
- CONSUME_RAW_BYTES => record-level Expand (heap_record_replace_oos_oids) before caller consumes raw bytes.
- DONT_CONSUME_RAW_BYTES => stored form preserved; attribute layer Resolves per attribute.

## Search ledger

### 검색 목적: enumerate all policy call sites in locator_sr.c
- 명령: `grep -n "HEAP_RECDES_CONSUME_RAW_BYTES|HEAP_RECDES_DONT_CONSUME_RAW_BYTES|HEAP_RECDES_CONSUMPTION_POLICY" src/transaction/locator_sr.c`
- raw candidate 수: 30 hits (26 explicit call-site uses + 3 getter signatures + 1 enum ref line not counted)
- included: all 26 explicit sites (303,1976,2341,2913,3500,3966,4448,4804,5793,5799,5942,6284,6581,6945,7615,7635,9160,9615,10070,10784,11969,12126,12151,12167,13066,13831) + 3 getters (13319,13463,13577)
- excluded: enum definition heap_file.h:364-368 (definition, not a site)
- duplicate: none
- pending: none (all 26 line hints from the task verified and matched)

### 검색 목적: enumerate callers of the 3 policy-parameter getters repo-wide
- 명령: `rg -n '\b(locator_lock_and_get_object|locator_lock_and_get_object_with_evaluation|locator_get_object)\s*\(' src/ | grep -v _internal`
- raw candidate 수: 18 (incl. defs + header prototypes)
- included: 5 cross-file caller sites + 7 in-file caller sites (see cross-file list below)
- excluded: prototypes in locator_sr.h:116/120/126, definitions/doc comments in locator_sr.c
- duplicate: none
- pending: cross-file callers audited by other agents (listed below)

### 검색 목적: determine whether class/catalog records can carry OOS stubs (or_class_name/or_class_hfid safety)
- 명령: `rg -n 'tf_class_to_disk|class_to_disk' object/*.c; rg -n 'heap_attrinfo_transform_to_disk' -tc | grep -v heap_file.c`
- 결과: class objects serialized by object/transform_cl.c:4546 tf_class_to_disk -> class_to_disk (OR_BUF), which does NOT call heap_attrinfo_determine_disk_layout. OOS demotion happens ONLY inside heap_attrinfo_transform_to_disk_internal (heap_file.c:12998 -> 13033 determine_disk_layout). => class-catalog records are never OOS-backed.
- included: producer fact used for F-101/F-102/F-120 EXCLUDED verdicts and F-112 class-branch.
- pending: reverse-audit producer confirmation (F-201 area).

### 검색 목적: verify attribute-layer read is OOS-aware (Resolve)
- 명령: `rg -n 'heap_attrvalue_read|heap_attrvalue_read_oos_inline|OR_IS_OOS' storage/heap_file.c`
- 결과: heap_file.c:10476-10479 — heap_attrvalue_read dispatches to heap_attrvalue_read_oos_inline when OR_IS_OOS(offset). Therefore heap_attrinfo_read_dbvalues / heap_attrinfo_set_uninitialized / heap_attrvalue_get_key / heap_attrinfo_generate_key / heap_attrinfo_delete_lob all Resolve OOS. Basis for every RESOLVE row.

## Verdict tally (29 rows)
- CORRECT: 21  (F-103,104,105,106,107,108,109,112,115,116,117,118,119,121,122,123,124,125,127,128,129)
- OVER_EXPAND: 5  (F-110,111,113,114,126)
- EXCLUDED: 3  (F-101,102,120 — class-catalog scans, not OOS-capable)
- BUG: 0 | CONTRACT_GAP: 0 | FOLLOWUP: 0

No hard BUG found: no DONT_CONSUME site was found feeding a raw-byte consumer, and no genuine raw-byte consumer was found without Expand.

## Suspected findings (OVER_EXPAND — CONSUME where the consumer only uses the attribute layer / header)

- **F-202 (HIGH) — locator_update_force sites 5799 & 5942** ship CONSUME (Expand) for the OLD record, but the sole consumers are `or_mvcc_get_header` (header) and `locator_update_index` -> `heap_attrinfo_read_dbvalues` (attribute-layer Resolve, heap_file.c:8518). The sibling need_locking branch at 5793 correctly uses DONT_CONSUME — the three are inconsistent. Beyond wasted oos_read I/O, eager Expand of a large multi-chunk OOS old record into the fixed `DB_PAGESIZE*2` scan-cache area can return S_DOESNT_FIT; update_force does NOT grow-and-retry here (5807 falls through to ER_FAILED), so this can spuriously fail UPDATE of a row with a large OOS-backed value. Recommend reverting both to DONT_CONSUME.
- **F-203 (LOW) — locator_delete_lob_force site 6581**: CONSUME, but consumer `heap_attrinfo_delete_lob` reads via `heap_attrvalue_read` (Resolve) + `or_rep_id` (header). LOB locators are OOS-eligible (ADR-0002) but the attr layer already resolves them; Expand is redundant. Low severity (locator payload is small). Revert to DONT_CONSUME.
- **F-204 (LOW/MED) — locator_repl_prepare_force site 6945**: CONSUME on a PEEK fetch whose ONLY consumer is `or_chn(old_recdes)` (6960) — a header field. Expand materializes the entire (possibly multi-chunk) record just to read the CHN. Revert to DONT_CONSUME.
- **F-205 (LOW) — locator_mvcc_reeval_scan_filters site 13831**: CONSUME, but consumers are `heap_attrinfo_read_dbvalues` (13847) and `locator_mvcc_reevaluate_filters` (13868) — attribute layer. Revert to DONT_CONSUME.

### Confirmed-correct notable sites
- **F-104 xlocator_fetch_all (2913)**: currently CONSUME. The OOS-CONTEXT census (dated) flagged this as CBRD-26948 (OPEN): after Expand became opt-in, xlocator_fetch_all stopped expanding and re-leaked OIDs to unloaddb/compactdb (load_object.c is OOS-blind). **Current HEAD code CONSUMEs**, i.e. it fixes that leak. Reconcile with CBRD-26948 ticket status (may be fixed-but-open). Flagged as finding F-201 for the reverse/ticket reconciliation, verdict itself CORRECT.
- **F-103 locator_lock_and_return_object (2341)**: CBRD-27029 client-ship path; explicit comment + S_DOESNT_FIT negative-length grow-retry contract. CORRECT (verify the retry loop in xlocator_fetch on the reverse pass).
- **F-125 redistribute_partition_data (13066)**: CONSUME is mandatory — record is re-inserted via locator_insert_force into a DIFFERENT partition heap; source OOS OIDs point to the source heap's OOS file and must be materialized so the target re-demotes into its own OOS file. census-confirmed genuine Expand.
- **F-123/F-124 xlocator_lock_and_fetch_all (12151/12167)**: genuine client-ship Expand; S_DOESNT_FIT handled via retry_current_oid (12154-12158). F-122 (12126) is a pre-lock OID probe whose body is discarded (re-fetched at 12151) — DONT_CONSUME correct (NO_BODY).

## Cross-file callers of the 3 getters (FOR OTHER AGENTS to audit their policy choice)
- locator_lock_and_get_object (F-129):
  - src/storage/compactdb_sr.c:215 — compactdb object fetch (CHECK: compactdb re-inserts/ships? likely needs scrutiny)
- locator_lock_and_get_object_with_evaluation (F-127):
  - src/query/query_executor.c:14555
  - src/query/scan_manager.c:6041
  - src/query/scan_manager.c:6861
- locator_get_object (F-128):
  - src/query/query_executor.c:13856
(In-file callers already covered: 2340->F-103, 3965->F-106, 4446->F-107, 4802->F-108, 5790->F-109, 6282->F-112, 7634->F-116.)

## New symbols / aliases discovered (for the reverse audit)
Consumers that read a heap RECDES via the ATTRIBUTE LAYER (OOS-safe Resolve; a DONT_CONSUME/preserve consumer):
- `locator_update_index` (locator_sr.c:8389) -> `heap_attrinfo_read_dbvalues` (8513/8518) — old+new key extraction for index maintenance.
- `locator_add_or_remove_index` / `_for_moving` / `_internal` (locator_sr.c:7804/7834/7869) -> `heap_attrinfo_read_dbvalues` (7945), `heap_attrvalue_get_key` (7991), `locator_eval_filter_predicate` (7976).
- `heap_attrinfo_generate_key` (used by F-121 xlocator_check_fk_validity).
- `heap_attrinfo_delete_lob` (heap_file.c:11024) -> `heap_attrvalue_read` (11063) + `or_rep_id` (11040).
- `locator_allocate_copy_area_by_attr_info` (locator_sr.c:7467) -> `heap_attrinfo_transform_to_disk[_except_lob]` (7495/7499) -> `heap_attrinfo_set_uninitialized` (heap_file.c:11902) -> `heap_attrvalue_read` (11948) — the UPDATE record rebuild; reads unchanged attrs OOS-aware.
- `locator_mvcc_reevaluate_filters` (consumer at F-126).

Consumers that read RAW record bytes (genuine Expand / a CONSUME consumer):
- `heap_get_referenced_by` (F-105) — extracts referenced OIDs from raw record; verify raw OR parse on reverse pass.
- LC_COPYAREA packers: `LC_RECDES_IN_COPYAREA` + `LC_NEXT_ONEOBJ_PTR_IN_COPYAREA` loop (xlocator_fetch_all 2906-2931, xlocator_lock_and_fetch_all 12109-12189, locator_lock_and_return_object via `locator_return_object_assign`) — ship raw bytes to CS client.
- `locator_insert_force` (F-125) — re-inserts raw record into another heap file.

Header/fixed-field-only readers (STORED_SAFE): `or_chn` (F-114), `or_mvcc_get_header` (F-109/110/111 header part), `or_rep_id`, `or_class_hfid` (F-120), `or_class_name` (F-101/102, class objects only).

Class-object serializer (NOT OOS-capable producer): `tf_class_to_disk` / `class_to_disk` (object/transform_cl.c:4546/3871).

Other transform_to_disk callers outside locator_sr.c (reverse-audit producers): `loaddb/load_server_loader.cpp:706`, `query/serial.c:955`.

## Ambiguities / caveats
- F-101/F-102/F-120 EXCLUDED verdict rests on the producer fact that root/_db_class objects never pass through heap_attrinfo_determine_disk_layout. If a future change routes class-object writes through the generic attr transform, `or_class_name`/`or_class_hfid` on DONT_CONSUME becomes a latent bug. Recommend the reverse audit confirm this producer boundary (folded into F-201 note).
- Aside (NOT in scope, noticed while reading): heap_attrinfo_determine_disk_layout (heap_file.c:12117/12148) still gates on raw `DB_PAGESIZE / 4`, not `heap_oos_inline_target_size()` (the CBRD-27057 four-record physical target, 4,060B). This is a demotion-gate conformance gap, unrelated to recdes consumption policy — forwarded to whoever owns CBRD-27057, not counted as an F2 finding.
- Getters F-127/128/129 are pure PROPAGATE; their correctness is entirely the caller's policy choice. In-file callers judged in their own rows; cross-file callers listed above for other agents.
