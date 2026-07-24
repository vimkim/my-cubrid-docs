# F4 — Forward audit notes (storage/misc explicit policy sites)

Scope: fwd-misc. Read-only tree `/home/vimkim/gh/cb/CBRD-26847-oos-visible-version` @ HEAD 6816023df.
Rows F-301..F-319 in F4.tsv. All 19 assigned sites verified against source (line numbers matched exactly).

## Normative basis

- Policy enum `HEAP_RECDES_CONSUMPTION_POLICY` (src/storage/heap_file.h:363-369): CONSUME_RAW_BYTES => record-level Expand (`heap_record_replace_oos_oids`); DONT => stored form preserved, attribute layer Resolves.
- Expand is opt-in (ADR-0003). `expand_oos = (policy == HEAP_RECDES_CONSUME_RAW_BYTES)` at heap_file.c:26218. Applied only through `heap_get_record_data_when_all_ready` (heap_file.c:7460,7482) and the from-log path (heap_file.c:26444). BOTH are guarded by `context->recdes_p != NULL` (heap_file.c:26464; explicit compactdb comment at heap_file.c:26443).
- Attribute layer is OOS-aware: `heap_attrinfo_read_dbvalues` (heap_file.c:10909) -> `heap_attrvalue_read` (heap_file.c:10571) -> dispatch to `heap_attrvalue_read_oos_inline` (heap_file.c:10479) -> oos_read, gated on the VOT OOS bit. This underpins every RESOLVE verdict.

## Search ledger

### 검색 1 — explicit policy call sites in scope files
- 목적: locate the exact policy constant usages at the assigned line numbers.
- 명령: `grep -nE "HEAP_RECDES_CONSUME_RAW_BYTES|HEAP_RECDES_DONT_CONSUME_RAW_BYTES|expand_oos" <9 scope files>`
- raw candidate 수: 19 (all assigned lines present, verbatim match).
- included: all 19 (F-301..F-319).
- excluded: none.
- duplicate: none.
- pending: none.

### 검색 2 — CONSUME consumer tracing (are raw bytes truly consumed?)
- 목적: for each CONSUME site, find terminal consumer and confirm raw-byte need.
- 명령: read enclosing functions; grep `catcls_get_or_value_from_record` (OR_BUF), `or_chn`, `heap_attrinfo_read_dbvalues`, `or_mvcc_get_header`.
- 결과:
  - catcls_delete/update_instance/update_class_stats (4014/4180/4504): genuine OR_BUF full-record parse via `or_init(buf,record->data,record->length)` (catalog_class.c:3629) -> EXPAND CORRECT. Exactly the 3 catcls sites in the ADR-0003 census 5-genuine list.
  - sp_code.cpp:91, load_server_loader.cpp:247, lock_manager.c:5644, compactdb.c:566, compactdb_sr.c:110: CONSUME but consumer is attribute-layer / MVCC-header-only / NULL-recdes existence -> OVER_EXPAND (5 sites).

### 검색 3 — DONT consumer tracing (is stored form actually safe?)
- 목적: confirm each DONT site consumes via attr layer / header / OID only.
- 명령: read enclosing functions + trace locator_update_index, locator_attribute_info_force -> transform_to_disk.
- 결과: all 8 explicit DONT sites (F-304,305,306,307,308,309,310,312,314,316,319) resolve through the attribute layer, MVCC header, the OID, or discard the body. All CORRECT.

## Verdict tally (19 rows)
- CORRECT: 14 (F-301..310, F-312, F-314, F-316, F-319)
- OVER_EXPAND: 5 (F-311, F-313, F-315, F-317, F-318)
- BUG / CONTRACT_GAP / FOLLOWUP: 0

## Findings (real work items)
- F4-FIND-01 (F-315, sp_code.cpp:91 `sp_get_code_attr`): CONSUME on _db_stored_procedure_code but sole consumer is the attribute layer (`heap_attrinfo_read_dbvalues` + `heap_attrinfo_access`). SP-code payloads are large -> OOS-capable, and ADR-0003 explicitly names SP-code fetch as a hot path that must NOT always Expand. Eager Expand resolves every OOS attr to read one. Recommend revert to DONT. HIGHEST-VALUE finding in this fragment.
- F4-FIND-02 (F-317, load_server_loader.cpp:247 `server_class_installer::locate_class_for_all_users`): CONSUME on db_user but only consumer is attr-layer read of the `name` attribute. Recommend DONT. (Note F-316 at :243 is the OID-cursor heap_next whose body is discarded — correctly DONT.)
- F4-FIND-03 (F-318, lock_manager.c:5644 `lock_dump_resource`): CONSUME but only consumer is `or_mvcc_get_header` (MVCC header) for a diagnostic lock dump. HAS_OOS does not affect header size, so Expand yields zero header benefit while forcing extra oos_read I/O on every OOS-backed instance dumped. Recommend DONT.
- F4-FIND-04 (F-311 compactdb.c:566 + F-313 compactdb_sr.c:110, both `process_value`): CONSUME with `recdes=NULL` existence/class-oid probes. Expand is guarded off (recdes_p==NULL), so functionally inert/harmless today — but the policy label is misleading. Cosmetic: set to DONT for clarity. LOW priority.

All five OVER_EXPAND sites are consistent with the ADR-0003 census claim that ~17 of ~22 `_expand_oos`/CONSUME sites were mechanically migrated and should revert to the cheap fetch.

## Newly discovered symbols / aliases / callbacks (for reverse audit)
- `catcls_get_or_value_from_record` (catalog_class.c:3598) — raw-byte OR_BUF whole-record parser (`or_init` at :3629). A genuine raw-RECDES consumer; any fetch feeding it needs Expand.
- `or_class_name` (object_representation.c:237) — reads variable-attr-0 (class name) RAW via `OR_VAR_OFFSET(record->data,0)`; used debug-only in system_catalog.c:4722/5034. Safe today only because class objects are built by `tf_class_to_disk` (transform_cl.c:4546), NOT the instance demotion path, so root/class-object records are NOT OOS-capable. Reverse-audit flag if class objects ever gain OOS.
- `or_get_attrname` (used at connection_support.cpp:2409) — raw variable-area read of attribute names from a CLASS-OBJECT recdes (separate earlier fetch, not the :2472 site). Class objects not OOS-capable; note for reverse audit completeness.
- `heap_attrinfo_set_uninitialized` (heap_file.c:13021, called from transform_to_disk_internal) — resolves UNCHANGED attributes from `old_recdes` via `heap_attrvalue_read` (attribute layer). This makes update rebuild paths (locator_attribute_info_force / locator_update_index) OOS-safe under DONT. Confirmed by OOS-CONTEXT Optimization Idea A.
- `heap_attrinfo_generate_key` (heap_file.c:14063) — index key extractor; internally calls `heap_attrinfo_read_dbvalues` (heap_file.c:14078,14098). OOS-safe. Relevant to btree_load and any index-build fetch.
- `locator_allocate_copy_area_by_attr_info` (locator_sr.c:7468) -> `heap_attrinfo_transform_to_disk[_except_lob]` (heap_file.c:12514/12535). Rebuilds records from attr_info dbvalues; old_recdes only supplies uninitialized-attr source (attr-layer). OOS-safe wrapper.
- `heap_get_record_data_when_all_ready` (heap_file.c:7427) — the single choke point where Expand is invoked; dereferences `recdes_p->data`, so NULL-recdes callers never reach it (existence-check pattern).

## Ambiguities / caveats
- oos_capable for catalog compat classes (_db_charset, _db_collation, ha apply-info) marked "unlikely" — values are tiny and almost never exceed the ~4,060B demotion target, but the verdict does not depend on it: the attribute layer resolves regardless, so DONT is correct by contract.
- Root/class-object records (F-307/F-308): judged NOT OOS-capable because their disk image is produced by the class transformer (`tf_class_to_disk`), which does not run the `heap_attrinfo_determine_disk_layout` demotion. If OOS ever extends to class objects, the debug-only `or_class_name` raw read would need re-evaluation (noted, not a current bug).
- No site in this fragment re-inserts raw fetched bytes into a heap, byte-compares records, or ships them in an LC_COPYAREA directly from the audited fetch — so no BUG (missing-Expand leak) among the 19. The known mirror-hazard (xlocator_fetch_all -> unloaddb/compactdb, CBRD-26948) is a DIFFERENT fetch (the LC_COPYAREA path in compactdb_sr process_class:441 via desc_disk_to_attr_info, which itself uses the attr layer) and is outside these explicit-policy line numbers.
