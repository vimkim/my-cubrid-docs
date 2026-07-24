# CLOSURE-PASS-4 — CBRD-26847 OOS raw-RECDES audit: second-of-two clean-pass check

- Agent: closure pass 4 (independent; every count, enclosing-function mapping and file-census
  re-derived from source. Prior passes' METHOD reused, their conclusions NOT trusted on faith).
- Date: 2026-07-24
- Source anchor: `6816023df4ed910687523ab4d34bf667ab32b9cd` (READ-ONLY, unmodified — `git rev-parse HEAD` verified).
- Inventory under test: `AUDIT-INVENTORY.tsv` — 261 data rows (262 lines incl. header); F-044..F-048 present and verified.
- Method: for every call site the enclosing function was recomputed from source with a backward
  scanner (C funcs at col 0; C++ `Class::method` allowing ≤6-space indent), then matched to an
  inventory row by function symbol. Strict bias: any site whose enclosing function is absent from
  the inventory is flagged, even when provably benign. Every anomaly thrown up by the heuristic was
  chased to source before dismissal (nothing waved through).

---

## Search ledger

### S1 — policy-constant occurrences, call-arg vs non-call

```text
목적: HEAP_RECDES_(CONSUME|DONT_CONSUME)_RAW_BYTES 전체 occurrence 재계수 + call-arg 분리
명령: rg -n  --glob '*.{c,cc,cpp,h,hpp}' 'HEAP_RECDES_(CONSUME|DONT_CONSUME)_RAW_BYTES' src unit_tests
raw lines: 92
tokens: CONSUME 29 + DONT 64 = 93  (heap_file.h:372 macro line carries BOTH constants -> 93 tokens / 92 lines)
non-call CONSUME (4): heap_file.h:363 (TODO comment), :367 (enum), :372 (macro), heap_file.c:26218 (local bool `expand_oos`)
non-call DONT  (5): heap_file.h:368 (enum), :372 (macro), heap_oos.cpp:362 (comparison), heap_file.c:8176 (comment), :8205 (comment)
call-argument: 25 CONSUME + 59 DONT = 84
NEW: 0  (25/59/84 identical to plan baseline and passes 1-3)
```

### S2 — 84 call-arg sites -> inventory row (enclosing-function symbol)

```text
목적: 84 call-argument site 전부가 inventory 행에 매핑되는지 (enclosing function 재산출 후 symbol match)
방법: 8개 non-call 라인 제외 -> 84 site -> 각 enclosing function 소스 역산 -> AUDIT-INVENTORY.tsv grep 확인
call-arg sites: 84
distinct enclosing functions: 67
included-in-inventory: 67/67 (자동 grep 확인, MISSING 0)
  heap_file.c wrappers/probes: heap_first(F-012) heap_last(F-013) heap_dump(F-016) heap_next_1page(F-014)
    heap_next_record_info(F-017) heap_prev_record_info(F-018) heap_get_class_record(F-019)
    heap_is_object_not_null(F-047) heap_scanrange_to_following(F-020/021) heap_scanrange_to_prior(F-022/023)
    heap_scanrange_next(F-024/025) heap_scanrange_prev(F-044) heap_scanrange_first(F-045) heap_scanrange_last(F-046);
  locator_sr.c: locator_initialize(F-101) check_class_names(F-102) lock_and_return_object(F-103)
    all_reference_lockset(F-105) check_primary_key_delete/update(F-107/108) delete_force_internal(F-112)
    delete_lob_force(F-113) repl_prepare_force(F-114) attribute_info_force(F-115/116)
    check_btree_entries(F-118) check_unique_btree_entries(F-119) check_all_entries_of_all_btrees(F-120)
    update_force(F-109/110/111) mvcc_reeval_scan_filters(F-126) redistribute_partition_data(F-125)
    xlocator_does_exist(F-106) xlocator_remove_class_from_index(F-117) xlocator_check_fk_validity(F-121)
    xlocator_fetch_all(F-104) xlocator_lock_and_fetch_all(F-122/123/124);
  storage/query/misc: catcls_delete/update_instance/update_class_stats(F-301/302/303)
    catcls_get_server_compat_info/db_collation/apply_info(F-304/305/306) catalog_check_consistency/dump(F-307/308)
    btree_sort_get_next(F-309) online_index_builder(F-310) process_value(F-311/313) process_object(F-314)
    update_indexes(F-312) sp_get_code_attr(F-315) locate_class_for_all_users(F-316/317)
    css_make_access_status_exist_user(F-319) lock_dump_resource(F-318)
    xserial_get_current/next_value_internal + serial_update_cur_val_of_serial(F-211/212/213)
    find_row_by_gtrid_bqual(F-214) dblink_global_tran_scan_for_recovery(F-215)
    leaf_slot_walker::process_oid(F-216) xhistogram_build_multi_by_fullscan_reservoir(F-217)
    xstats_collect_ndv_by_fullscan_reservoir(F-218)
    scan_next_heap_scan(F-201/202/203) scan_next_index_lookup_heap(F-204/205)
    qexec_execute_update/delete/duplicate_key_update/obj_fetch/selupd_list(F-206..210).
NEW (call-arg site with NO inventory row): 0
```

### S3 — 7 policy-API caller sweep (literal + variable-policy propagation)

```text
목적: literal sweep가 놓치는 전파(변수) 정책 caller까지 7 API의 모든 call site 포착
명령: rg -n --glob '*.{c,cc,cpp}' '\b<api>\s*\(' src  (heap_next, heap_prev, heap_get_visible_version,
  heap_scan_get_visible_version, locator_lock_and_get_object[_with_evaluation], locator_get_object)
distinct enclosing functions (comment false-positive 제거 후): S2의 67 함수(이 API를 직접 호출하는 부분집합)
  + plumbing(heap_get_record_info, heap_get_visible_version_from_log, locator_lock_and_get_object_internal)
  + API self/wrapper 정의(heap_next F-009, heap_prev F-010, heap_get_visible_version F-003,
    heap_scan_get_visible_version F-004, locator_get_object F-128, locator_lock_and_get_object F-129,
    locator_lock_and_get_object_with_evaluation F-127) — 전부 inventory.
heuristic false-positive 1건 추적: scan_next_index_scan(scan_manager.c:6406-6704).
  실제 API 호출 없음 — 유일 매치는 라인~6437 주석 "...via heap_get_visible_version ()." (호출 아님).
  6807/6861의 실제 호출은 scan_next_index_lookup_heap(6785, F-204/F-205) 소속. -> 미커버 caller 아님.
NEW (uncovered enclosing function): 0
```

### S4 — fixed-policy wrapper / probe caller sweep

```text
목적: 고정정책 wrapper·probe의 caller 전수가 row/bucket 커버되는지
명령: rg -n --glob '*.{c,cc,cpp}' '\b<fn>\s*\(' src
heap_first callers(6): boot_get_db_parm(F-027) dblink_global_tran_scan_for_recovery(F-215/029)
  find_row_by_gtrid_bqual(F-028/214) heap_scanrange_to_following(F-020) tde_get_keyinfo(F-026)
  xheap_has_instance(F-048) — 전부 커버
heap_last: heap_scanrange_to_prior(F-022) only — 커버
heap_next_record_info / heap_prev_record_info: scan_next_heap_scan(F-037/038) — 커버
heap_scanrange_{to_following,to_prior}: scan_next_scan_block(F-034/035); heap_scanrange_next: scan_next_heap_scan(F-036) — 커버
heap_scanrange_{prev,first,last}: caller 0 (dead #if ENABLE_UNUSED_FUNCTION) -> F-044/045/046 재확인
heap_get_class_record callers(32 distinct fns): 전부 CLASS-object reader (btree_scan_for_show_index_header,
  build_auto_increment_serial_name, catalog_get_*, catcls_*, css_make_access_status_exist_user,
  file_is_valid_heap_file, heap_class*/heap_get_class_*/heap_get_partition_attributes, locator_check_*,
  locator_guess_sub_classes, locator_update_force, or_get_hierarchy_helper, qdata_get_estimated_heap_stat,
  qexec_execute_build_columns/indexes, serial_load_attribute_info_of_db_serial,
  server_class_installer::register_class_with_attributes, sp_load_sp_code_attribute_info, xboot_checkdb_table).
  invariant B (class records = client tf_class_to_disk 산출, OOS-incapable) -> 전부 F-019/F-042 버킷 커버.
heap_does_exist: signature `bool heap_does_exist(THREAD_ENTRY*, OID*, const OID*)` — RECDES 파라미터 자체가 없음.
  구조적으로 어떤 caller도 record body를 소비 불가 (NO_BODY). 10 callers 전부 F-015 버킷 상속.
heap_is_object_not_null: caller eval_pred_comp1 (query_evaluator.c) -> F-047; body 미노출.
xheap_has_instance: 호출 site 2건뿐 — network_interface_sr.cpp:8542(enclosing shf_has_instance) /
  network_interface_cl.c:1902(enclosing heap_has_instance); 둘 다 int만 반송 -> F-048. (F-048 evidence와 일치)
NEW (uncovered caller): 0
```

### S5 — OOS-consumption chokepoint caller sweep

```text
목적: OOS 소비/식별 choke point 7종의 caller 전수가 row/bucket 커버되는지
명령: rg -n --glob '*.{c,cc,cpp}' '\b<fn>\s*\(' src unit_tests
heap_record_replace_oos_oids <- heap_get_record_data_when_all_ready(F-006 @7460,7482),
  heap_get_visible_version_internal(F-005 @26444) — 커버
heap_attrvalue_read_oos_inline <- heap_attrvalue_point_variable(heap_file.c:10479, attr-layer Resolve F-006/F-201);
  heap_file.c:694 = static 전방선언(호출 아님); bridge_heap_attrvalue_read_oos_inline(:27857) = 문서화된
  unit-test seam (see unit_tests/oos/test_oos.cpp) — 정당 제외
oos_read <- heap_attrvalue_read_oos_inline(heap_file.c:10419); test_oos.cpp:764 = test subject — 커버
heap_recdes_get_oos_oids <- heap_oos_delete_unreferenced(R-021..024), vacuum_forward_walk_reclaim_oos(R-017),
  vacuum_heap_oos_delete_within_sysop(R-018); unit_tests = subject — 커버
heap_recdes_contains_oos <- heap_update_home/relocation(R-021/022), heap_delete_home/relocation(R-023/024),
  heap_scan_get_visible_version_impl(F-004 fast-path), heap_recdes_get_oos_oids(R-020 self-guard),
  heap_record_replace_oos_oids(internal), heap_attrinfo_read_dbvalues_with_oos_prefetch(attr-layer R-103),
  heap_oos_read_grouped_payloads(internal OOS helper), locator_add_or_remove_index_internal(R-202),
  locator_update_index(R-203), xlocator_repl_force(R-220/308), server_object_loader::finish_line(F-316/317, R-311),
  vacuum_heap_record(R-018/019), vacuum_forward_walk_reclaim_oos(R-017), vacuum_oos_find_vfid_for_heap_record(R-019);
  test_oos_vacuum_server.cpp = subject — 전부 커버
locator_fixup_oos_oids_in_recdes <- xlocator_repl_force(R-221/308 @7093); locator_sr.c:238 = 전방선언;
  bridge_locator_fixup_oos_oids_in_recdes(:14269) = #if defined(CUBRID_UNIT_TEST_ENABLED) test bridge — 정당 제외
locator_oos_insert_force <- xlocator_repl_force(R-222/309 @7103); test_oos_server.cpp = subject — 커버
NEW: 0 (전 production caller가 row/bucket에 귀속; 전방선언/test bridge/unit_tests 정당 제외)
```

### S6 — RECDES file census vs R6 file->bucket table

```text
목적: RECDES-bearing 파일 전수가 R6-notes.md 표에 있는지
명령: rg -l '\bRECDES\b' src
actual RECDES files: 82
R6-notes.md distinct src 경로: 83 (확장자 정규식 cpp|hpp|cc|c|h 우선순위 교정 후)
comm -23 (actual - R6표) = ∅   -> R6 표에서 빠진 RECDES 파일 0
comm -13 (R6표 - actual) = {src/base/error_code.h}  -> 산문 참조 1건(ER -1379 인용, RECDES 파일 아님, 무해)
missing-from-table: 0
주의: 1차 추출에서 정규식 alternation(c|cc|cpp)이 .cpp/.hpp를 .c/.h로 절단해 21건 허위 불일치가 발생 -> 확장자
  우선순위 교정 후 소멸(동일 파일). pass-3 결과와 완전 일치.
NEW: 0
```

### S7 — new-symbol probe (heap-instance byte consumer not in inventory)

```text
목적: policy 상수/7 API/wrapper/chokepoint 밖에서 heap-instance record byte를 소비할 신규 진입점
방법 (a): 헤더 signature에 HEAP_RECDES_CONSUMPTION_POLICY를 지닌 함수 전수 열거
  완전 집합: heap_next(F-009) heap_prev(F-010) heap_get_visible_version(F-003)
  heap_scan_get_visible_version(F-004) heap_init_get_context 세터(F-002, HEAP_GET_CONTEXT 경유
  heap_get_last_version F-008 소비) locator_lock_and_get_object(F-129)
  locator_lock_and_get_object_with_evaluation(F-127) locator_get_object(F-128) — 전부 inventory.
  (heap_next_1page/heap_next_record_info는 policy enum 미보유 = 고정정책 wrapper, F-014/017 커버)
방법 (b): policy 없는 body-returning getter 점검
  heap_get_class_oid -> class_oid만 반송(RECDES 없음) — non-consumer
  heap_get_mvcc_header -> MVCC_REC_HEADER만 반송(로컬 peek, body 미노출) — non-consumer
  heap_get_class_record -> class record(invariant B, F-019/042) — instance-byte consumer 아님
  heap_get_bigone_content -> REC_BIGONE(F-043 EXCLUDED, OOS 불가)
방법 (c): raw variable-area/OOS-stub 파싱 primitive(OR_IS_OOS / OR_VAR_BIT_OOS) enclosing 전수 열거
  heap_attrvalue_point_variable(attr-layer Resolve dispatch, F-006/F-201) / heap_recdes_get_oos_oids(R-020) /
  la_get_current(R-216) / locator_fixup_oos_oids_in_recdes(R-221) / heap_recdes_compute_oos_flag_debug(X-524) /
  heap_oos.cpp 내부 헬퍼(compute_layout/find_attr_inline_ref/read_values = heap_record_replace_oos_oids 기계) /
  heap_midxkey_get_oos_extra_size(attr-layer midxkey 크기 헬퍼, F-309/F-121/R-501 key 추출 경유) — 전부 귀속.
백스톱: S6가 82개 RECDES-bearing 파일 전수를 R6 버킷 표에 귀속 -> RECDES를 다루는 파일 중 미할당 0.
plausible OOS-capable heap-instance-byte consumer (신규, inventory 밖): 0
NEW: 0
```

---

## NEW-PATHS

None. Every sweep resolved to 0 uncovered sites/callers.

Two heuristic anomalies surfaced and were chased to source (both benign, no new path):

- **S3 `scan_next_index_scan`** appeared as a would-be 7-API caller. Source shows the only match in its
  body (scan_manager.c 6406-6704) is a prose comment "...via `heap_get_visible_version ()`." at ~line 6437;
  the actual fetch calls at 6807/6861 belong to `scan_next_index_lookup_heap` (F-204/F-205). Not a caller.
- **S5 `heap_file.c:694` / `locator_sr.c:238`** are static forward declarations; the two `bridge_*`
  functions are unit-test seams (`bridge_heap_attrvalue_read_oos_inline` documented as a test seam;
  `bridge_locator_fixup_oos_oids_in_recdes` under `#if defined(CUBRID_UNIT_TEST_ENABLED)`). Legitimately excluded.

The gaps closed by earlier passes were re-verified present and accurate at HEAD 6816023df:

- **F-047** `heap_is_object_not_null` — NO_BODY existence probe (recdes=NULL), sole caller
  query_evaluator.c `eval_pred_comp1`; mirrors F-015. Row present, evidence correct.
- **F-048** `xheap_has_instance` — NO_BODY existence probe; callers network_interface_{sr.cpp:8542,cl.c:1902}
  ship an int only. Row present, evidence correct.
- **F-044/045/046** the three dead `heap_scanrange_{prev,first,last}` sites (`#if defined(ENABLE_UNUSED_FUNCTION)`,
  heap_file.c:8618-8777, 0 compiled callers). Rows present, evidence correct.

## Confirmations (independent, re-derived from source at 6816023df)

- Policy-constant call-argument total = 25 CONSUME + 59 DONT = 84 (S1).
- 84/84 call-arg sites map to an inventory row; 67 distinct functions, 0 missing (grep-verified) (S2).
- All 7-policy-API caller enclosing functions (literal + variable propagation) are inventoried; the single
  heuristic false positive (scan_next_index_scan) is a comment, not a call (S3).
- All fixed-policy wrapper/probe callers resolve to rows/buckets, incl. F-044..F-048; heap_does_exist is
  structurally NO_BODY (no RECDES param); 0 uncovered (S4).
- All 7 OOS chokepoints' production callers resolve to rows/buckets; forward declarations, `#if`-guarded
  bridges, and unit_tests legitimately excluded (S5).
- RECDES file universe = 82 files, fully contained in the R6 table; only extra table entry is error_code.h
  prose. First-pass extension-regex artifact identified and neutralized (S6).
- The complete policy-bearing API set, the non-body getters, and every raw OOS-stub parse primitive
  introduce no uncovered heap-instance byte consumer (S7).

## Verdict

PASS-4: 0 new paths.

This is the SECOND of two consecutive clean passes (PASS-3 = 0, PASS-4 = 0). The inventory
(261 data rows, F-044..F-048 included) is complete against all seven sweeps; nothing remains uncovered.
The raw-RECDES OOS-consumption audit is closed.
