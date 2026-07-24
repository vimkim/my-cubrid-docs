# CLOSURE-PASS-3 — CBRD-26847 OOS raw-RECDES audit: first-of-two clean-pass check

- Agent: closure pass 3 (independent; re-derived every count and mapping from source,
  did not trust pass-1/pass-2 conclusions on faith)
- source anchor: `6816023df4ed910687523ab4d34bf667ab32b9cd` (READ-ONLY, unmodified — `git rev-parse HEAD` verified)
- Inventory under test: `AUDIT-INVENTORY.tsv` — 261 data rows (262 lines incl. header); F-044..F-048 present and verified.
- Method: for every sweep, the enclosing function of each site was re-computed from source with a
  backward scanner (C funcs at col 0, C++ `Class::method` allowing ≤4-space indent), then mapped to an
  inventory row by function symbol against `AUDIT-INVENTORY.tsv`. Strict bias: any site whose enclosing
  function is absent from the inventory is flagged, even when provably benign.

---

## Search ledger

### S1 — policy-constant occurrences, call-arg vs non-call

```text
검색 목적: HEAP_RECDES_(CONSUME|DONT_CONSUME)_RAW_BYTES 전체 occurrence 재계수 + call-arg 분리
명령: rg -n --glob '*.{c,cc,cpp,h,hpp}' 'HEAP_RECDES_(CONSUME|DONT_CONSUME)_RAW_BYTES' src unit_tests
raw: 92 lines (29 CONSUME + 64 DONT = 93 tokens; heap_file.h:372 carries BOTH constants)
non-call (8 lines): CONSUME 4 = heap_file.h:363(comment),:367(enum),:372(macro),heap_file.c:26218(local bool);
  DONT 5 = heap_file.h:368(enum),:372(macro),heap_oos.cpp:362(comparison),heap_file.c:8176(comment),:8205(comment)
call-argument: 25 CONSUME + 59 DONT = 84  (matches plan baseline and pass-1/pass-2 exactly)
NEW: 0 (25/59 split reconciled arithmetically from the raw token counts)
```

### S2 — 84 call-arg sites → inventory row (enclosing function symbol)

```text
검색 목적: 84개 call-argument site 전부가 inventory 행에 매핑되는지 (enclosing function 재산출 후 symbol match)
방법: 각 site의 enclosing function을 소스 역스캔으로 재계산 → 67개 distinct 함수 → AUDIT-INVENTORY.tsv에 존재 확인
distinct enclosing functions: 67   total sites: 84
included-in-inventory: 84/84 (67/67 함수 전부 inventory 존재)
  heap_file.c wrappers/probes: heap_next_1page(F-014) heap_first(F-012) heap_last(F-013) heap_dump(F-016)
    heap_next_record_info(F-017) heap_prev_record_info(F-018) heap_get_class_record(F-019)
    heap_scanrange_to_following(F-020/021) heap_scanrange_to_prior(F-022/023) heap_scanrange_next(F-024/025)
    heap_scanrange_prev(F-044) heap_scanrange_first(F-045) heap_scanrange_last(F-046) heap_is_object_not_null(F-047);
  locator_sr.c: locator_initialize/lock_and_return_object/all_reference_lockset/attribute_info_force/
    update_force/delete_force_internal/delete_lob_force/repl_prepare_force/mvcc_reeval_scan_filters/
    check_* family/redistribute_partition_data + x-prefixed xlocator_fetch_all/does_exist/check_fk_validity/
    lock_and_fetch_all/remove_class_from_index (F-1xx / R-2xx);
  catalog_class.c catcls_*, system_catalog.c catalog_check_consistency/catalog_dump, serial.c
    (x)serial_*(F-21x/R-502), sp_code.cpp sp_get_code_attr(R-503), lock_manager.c lock_dump_resource(R-507),
    connection_support.cpp css_make_access_status_exist_user(X-522), histogram_sampler_sr.cpp
    x{histogram,stats}_*(F-031/032), dblink find_row_by_gtrid_bqual + dblink_global_tran_scan_for_recovery(F-028/214/215),
    btree_load.c btree_sort_get_next/online_index_builder(F-033/X-503), compactdb(_sr) process_value/process_object/
    update_indexes(F-311/313,R-404/407), load_server_loader server_class_installer::locate_class_for_all_users(F-316/317),
    px leaf_slot_walker::process_oid(F-030), scan_manager scan_next_heap_scan/scan_next_index_lookup_heap(F-034..038,204/205),
    query_executor qexec_execute_{delete,update,obj_fetch,selupd_list,duplicate_key_update}(F-2xx).
NEW (call-arg site with NO inventory row): 0
```

### S3 — 7 policy-API caller sweep (literal + variable-policy propagation)

```text
검색 목적: literal sweep가 놓치는 전파(변수) 정책 caller까지 7 API의 모든 call site 포착
명령: rg -n '\b<api>\s*\(' src --glob '*.{c,cc,cpp}'  (heap_next, heap_prev, heap_get_visible_version,
  heap_scan_get_visible_version, locator_lock_and_get_object[_with_evaluation], locator_get_object)
distinct enclosing functions across all 7 APIs: 68
included-in-inventory: 68/68 — S2의 함수 집합 + API 자체(정의/내부 재귀 = plumbing)
  전부 존재. variable-policy plumbing(heap_get_visible_version_internal, heap_get_last_version,
  heap_next/prev_internal, locator_lock_and_get_object_internal)은 API-name 버킷에 귀속되며 전부 inventory.
NEW (uncovered enclosing function): 0
```

### S4 — fixed-policy wrapper / probe caller sweep

```text
검색 목적: 고정정책 wrapper·probe의 caller 전수가 row/bucket 커버되는지
명령: rg -n '\b<fn>\s*\(' src  (heap_first, heap_last, heap_next_record_info, heap_prev_record_info,
  heap_get_class_record, heap_scanrange_{to_following,to_prior,next,prev,first,last}, heap_does_exist,
  heap_is_object_not_null, xheap_has_instance)
heap_first callers(6 non-def): tde.c:588(F-026) boot_sr.c:310(F-027) dblink:212 find_row_by_gtrid_bqual(F-028)
  dblink:444 dblink_global_tran_scan_for_recovery(F-215) heap_file.c:8357 heap_scanrange_to_following(F-020)
  heap_file.c:17809 xheap_has_instance(F-048) — 전부 커버
heap_last: heap_file.c:8468 heap_scanrange_to_prior(F-022) only — 커버
heap_next_record_info/heap_prev_record_info: scan_manager.c:5934/5951 scan_next_heap_scan(F-037/038) — 커버
heap_get_class_record: 84-site 내부 caller(F-019) + 23 cross-file caller = 전부 CLASS record consumer
  (invariant B: class record는 client tf_class_to_disk 산출, OOS-incapable) → F-042 버킷 커버
heap_scanrange_{to_following,to_prior,next}: scan_manager 5053/5057/5916(F-034/035/036) — 커버
heap_scanrange_{prev,first,last}: caller = 정의뿐, 컴파일 caller 없음(#if ENABLE_UNUSED_FUNCTION 死코드) → F-044/045/046 재확인
heap_does_exist callers(11 non-def): 전부 bool 존재-체크(recdes 미노출, NO_BODY) → F-015 버킷 상속, byte 소비 불가
heap_is_object_not_null: query_evaluator.c:2218(F-047) — 커버
xheap_has_instance: network_interface_sr.cpp:8542 / network_interface_cl.c:1902 (int만 반송) → F-048 — 커버
NEW (uncovered caller): 0 (pass-1의 F-047, pass-2의 F-048가 이 스윕의 유일 gap을 이미 메움 — 재확인)
```

### S5 — OOS-consumption chokepoint caller sweep

```text
검색 목적: OOS 소비/식별 choke point 7종의 caller 전수가 row/bucket 커버되는지
명령: rg -n '\b<fn>\s*\(' src unit_tests
heap_record_replace_oos_oids (CONSUME/Expand terminal) <- heap_file.c:7460,7482,26444
  (heap_get_record_data_when_all_ready F-006 / heap_get_visible_version_internal F-005) — 커버
heap_attrvalue_read_oos_inline <- heap_file.c:10479,27857 (attr-layer Resolve, F-006/F-201) — 커버
oos_read <- heap_file.c:10419 (heap_attrvalue_read_oos_inline 내부); unit_tests = test subject — 커버
heap_recdes_get_oos_oids <- heap_oos.cpp:710/730(내부), vacuum_oos.cpp:286/404(vacuum→rev-cdc); unit_tests — 커버
heap_recdes_contains_oos (bool predicate) <- heap_file.c write/fast-path(fwd-heap), vacuum_oos/vacuum.c(rev-cdc),
  locator_sr.c:7091/8150/8941(write→R-202/R-220 등), load_server_loader:718(producer F-316/317), heap_oos.cpp(내부) — 커버
locator_fixup_oos_oids_in_recdes <- locator_sr.c:7093 xlocator_repl_force(R-221) + 14269(내부 wrapper) — 커버
locator_oos_insert_force <- locator_sr.c:7103 xlocator_repl_force(R-220/222); unit_tests — 커버
NEW: 0 (전 production caller가 row/bucket에 귀속; unit_tests는 test subject로 정당 제외)
```

### S6 — RECDES file census vs R6 file→bucket table

```text
검색 목적: RECDES-bearing 파일 전수가 R6-notes.md 표에 있는지
명령: rg -l '\bRECDES\b' src  (glob 무제한 및 {c,cc,cpp,h,hpp} — 둘 다 82)
actual RECDES files: 82
R6 표 distinct 경로: 83
comm -23 (actual − R6표) = ∅  → R6 표에서 빠진 RECDES 파일 0
comm -13 (R6표 − actual) = {src/base/error_code.h}  → 산문 참조 1건(-1379 인용, RECDES 파일 아님, 무해)
missing-from-table: 0
NEW: 0
```

### S7 — new-symbol probe (plausible heap-instance byte consumer not in inventory)

```text
검색 목적: policy 상수/7 API/wrapper/chokepoint 밖에서 heap-instance record byte를 소비할 법한 신규 진입점
방법: heap_file.h + locator_sr.h에서 RECDES_CONSUMPTION_POLICY를 signature에 지닌 함수 전수 열거,
  그리고 정책 없이 record body를 반환하는 public getter 점검
정책-bearing public/plumbing 집합 (완전): heap_next, heap_prev, heap_get_visible_version,
  heap_scan_get_visible_version, heap_get_last_version(HEAP_GET_CONTEXT 경유), + 내부
  (heap_next_internal, heap_scan_get_visible_version_impl, heap_get_visible_version_internal,
   heap_get_record_data_when_all_ready, heap_init_get_context 세터), locator_lock_and_get_object[_with_evaluation],
   locator_get_object(+internal). heap_get_last_version callers(4): compactdb process_value(F-313),
   locator_sr.c:7616(R-220), :13199(locator internal F-127..129), heap_file.c:26852(내부) — 전부 커버.
정책 없는 record getter 점검:
  heap_get_class_oid → class_oid만 반송(body 아님) — non-consumer
  heap_get_mvcc_header → MVCC_REC_HEADER 구조체만 반송(로컬 peek_recdes 사용, body byte 미노출);
    유일 cross-file caller locator_sr.c:13221(locator internal F-127..129) — OOS byte 소비 불가, non-consumer
  heap_get_class_record → class record(invariant B, F-042/019) — instance-byte consumer 아님
plausible OOS-capable heap-instance-byte consumer (신규, inventory 밖): 0
백스톱: S6가 82개 RECDES-bearing 파일 전수를 R6 버킷 표에 귀속시켰으므로, RECDES를 다루는 어떤 파일도
  미할당 상태가 아님 — 신규 소비자 존재 여지 없음.
NEW: 0
```

---

## NEW-PATHS

None. Every sweep resolved to 0 uncovered sites/callers.

The two gaps found by earlier passes are now inventoried and were re-verified present and accurate:

- **F-047** `heap_is_object_not_null` (heap_file.c:8977 → `heap_get_visible_version(recdes=NULL,DONT)`;
  sole caller query_evaluator.c:2218) — NO_BODY existence probe, mirrors F-015. Row present, evidence correct.
- **F-048** `xheap_has_instance` (heap_file.c:17809 → `heap_first(recdes.data=NULL,PEEK)`; callers
  network_interface_sr.cpp:8542 / network_interface_cl.c:1902 ship an int) — NO_BODY existence probe,
  mirrors F-015/F-047. Row present, evidence correct.
- **F-044/045/046** the three `heap_scanrange_{prev,first,last}` dead-code sites
  (`#if defined(ENABLE_UNUSED_FUNCTION)` block, heap_file.c:8618–8777, no compiled caller). Rows present,
  evidence correct.

## Confirmations (independent, re-derived from source at 6816023df)

- Policy-constant call-argument total = 25 CONSUME + 59 DONT = 84 (S1).
- 84/84 call-arg sites map to an inventory row via enclosing-function symbol; 67 distinct functions, 0 missing (S2).
- All 68 enclosing functions of the 7-policy-API call sites (literal + variable propagation) are inventoried (S3).
- All fixed-policy wrapper/probe callers resolve to rows/buckets, including F-044..F-048 (S4); 0 uncovered.
- All 7 OOS chokepoints' production callers resolve to rows/buckets; unit_tests legitimately excluded (S5).
- RECDES file universe = 82 files, fully contained in the R6 table; only extra table entry is error_code.h prose (S6).
- The complete policy-bearing API set plus the two non-body getters (heap_get_class_oid, heap_get_mvcc_header)
  introduce no uncovered heap-instance byte consumer (S7).

## Verdict

PASS-3: 0 new paths.

This is the FIRST of two consecutive clean passes. Inventory (261 data rows, F-044..F-048 included)
is complete against all seven sweeps; nothing remains uncovered.
