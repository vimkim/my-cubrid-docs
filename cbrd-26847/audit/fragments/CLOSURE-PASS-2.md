# CLOSURE-PASS-2 — CBRD-26847 OOS raw-RECDES audit: independent no-new-path re-check

- Agent: closure pass 2 (independent of pass 1; did not accept pass-1 conclusions on faith)
- source anchor: `6816023df4ed910687523ab4d34bf667ab32b9cd` (READ-ONLY, unmodified)
- Inventory under test: `AUDIT-INVENTORY.tsv` — 260 data rows (261 lines incl. header), F-044..F-047 present.
- Method: re-derived every enclosing function from source with a backward scanner, matched each
  policy call-argument site to an inventory row by `file:line` first and function-symbol fallback
  second, then independently swept the 7 policy APIs, the fixed-policy wrappers, the OOS chokepoints,
  and the RECDES file universe. Strict bias: an uncovered caller is flagged even when provably
  NO_BODY / dead / OOS-incapable.

---

## Search ledger

### S1 — policy-constant occurrences, call-arg vs non-call

```text
검색 목적: HEAP_RECDES_(CONSUME|DONT_CONSUME)_RAW_BYTES 전체 occurrence 재계수 + call-arg 분리
명령: rg -n --glob '*.{c,cc,cpp,h,hpp}' 'HEAP_RECDES_(CONSUME|DONT_CONSUME)_RAW_BYTES' src unit_tests
raw: 92 lines (heap_file.h:372 carries BOTH constants -> 93 token occurrences: 29 CONSUME + 64 DONT)
non-call (8 lines): CONSUME 4 = heap_file.h:363(comment),:367(enum),:372(macro),heap_file.c:26218(local bool);
  DONT 5 = heap_file.h:368(enum),:372(macro),heap_oos.cpp:362(comparison),heap_file.c:8176(comment),:8205(comment)
call-argument: 25 CONSUME + 59 DONT = 84  (matches pass-1 / plan baseline exactly)
NEW: 0 (count reconfirmed independently)
```

### S2 — 84 call-arg sites -> inventory row (file:line then function-symbol)

```text
검색 목적: 84개 call-arg site가 전부 inventory 행에 매핑되는지 (line 우선, 함수-심볼 fallback)
방법: 각 site의 enclosing function을 소스에서 역스캔으로 재산출 -> file:line exact match -> 실패 시 함수명 fallback
exact file:line match (evidence 컬럼): 44/84
function-symbol fallback: 40/84 (locator_sr.c 25 + heap_file.c 15) — 전부 매칭.
  사유: inventory evidence가 호출 시작 라인(예: locator_sr.c:2340)을 인용하는데
  정책 상수는 그 몇 줄 뒤 continuation 라인(2341)에 위치. 함수 심볼은 동일.
  예: 303 locator_initialize=F-101, 2341 locator_lock_and_return_object=F-103,
      2913 xlocator_fetch_all=F-104, 5793/5799/5942 locator_update_force=F-109/110/111,
      6945 locator_repl_prepare_force=F-114, 13831 locator_mvcc_reeval_scan_filters=F-126,
      8100 heap_next_1page=F-014, 8677/8656 heap_scanrange_prev=F-044, 8721=F-045, 8766=F-046,
      8977 heap_is_object_not_null=F-047, 15625 heap_dump=F-016, 20039/20089 record_info=F-017/018.
included-in-inventory: 84/84
NEW (call-arg site with NO inventory row): 0
```

Distinct enclosing functions confirmed present in inventory (grep of AUDIT-INVENTORY.tsv):
`locate_class_for_all_users`(F-316/317), `dblink_global_tran_scan_for_recovery`(F-215),
`find_row_by_gtrid_bqual`(F-028/214), `scan_next_index_lookup_heap`(F-204/205),
`catalog_check_consistency`/`catalog_dump`(F-307/308), `catcls_*`, `serial.c`(R-502/F-21x),
`sp_get_code_attr`(R-503), `lock_dump_resource`(R-507), `leaf_slot_walker`(px, →fwd-query) — all matched.
NB: F-215 (dblink_global_tran_scan_for_recovery:515) shows the pass-1 concern about dblink was
unfounded — the inventory carries a dedicated F-2xx row for the second dblink site; the older
F-029 evidence (dblink_global_tran_update_state) is stale (that function has no heap fetch) but
the *site* is covered by F-215.

### S3 — fixed-policy wrapper caller sweep (by symbol)

```text
검색 목적: 고정정책 wrapper의 caller 전수 -> 전부 row/bucket 커버되는지 (7-API sweep가 놓치는 층)
명령: rg -n '\b<wrapper>\s*\(' src  (heap_first/last, heap_{next,prev}_record_info, heap_get_class_record,
  heap_scanrange_{to_following,to_prior,next,prev,first,last}, heap_does_exist, heap_is_object_not_null, heap_get_record_info)
heap_first callers(6): tde:588(F-026) boot_sr:310(F-027) dblink:212(F-028) dblink:444(F-029)
  heap_file.c:8357(heap_scanrange_to_following, F-020/012 bucket, positioning) + heap_file.c:17809 => XHEAP (아래)
heap_last: heap_scanrange_to_prior:8468(F-013) only
heap_{next,prev}_record_info: scan_manager 5934/5951 (F-037/038)
heap_get_class_record callers(34): 크로스파일=F-042 enumerated; heap_file.c-internal 다수
  (heap_classrepr_get_from_record, heap_classrepr_dump[_all], heap_get_class_subclasses,
   heap_get_class_info_from_record, heap_get_class_name_alloc_if_diff, build_auto_increment_serial_name)
   -> 개별 row 없음, 그러나 F-042 "other heap_get_class_record callers" 버킷이 범주로 커버
   (class record는 invariant B/X-519로 OOS-incapable). btree.c:21582는 주석, 21593만 실제(F-041).
heap_scanrange_{prev,first,last}: caller=def뿐 -> 컴파일 caller 없음(dead, F-044/045/046 재확인)
heap_scanrange_{to_following,to_prior,next}: scan_manager 5053/5057/5916 (F-034/035/036)
heap_does_exist callers(11): 전부 존재-체크(NO_BODY, recdes 내부 NULL); F-015가 NO_BODY wrapper로
  범주 커버, caller가 body byte를 소비할 수 없음.
heap_is_object_not_null: query_evaluator.c:2218 (F-047)
heap_get_record_info: heap_next_internal 내부(7609/7850) (F-011)
NEW (uncovered caller): 1 -> xheap_has_instance (see NEW-PATHS)
```

### S4 — OOS-consumption chokepoint caller sweep

```text
검색 목적: OOS 소비 choke point의 caller 전수가 row/bucket 커버되는지
명령: rg -n '\b<fn>\s*\(' src  (7 chokepoints) + enclosing 재산출
heap_record_replace_oos_oids <- heap_get_record_data_when_all_ready(F-006),
  heap_get_visible_version_internal(F-005), heap_oos_build_record(heap_oos plumbing/F-001)
heap_attrvalue_read_oos_inline <- heap_attrvalue_point_variable/transform_to_dbvalue/get_var_offset_entry
  (attr-layer Resolve, F-006/F-201 mechanism); bridge_* = unit_tests
oos_read <- heap_attrvalue_read_oos_inline(attr layer), heap_oos_build_record(Expand)
heap_recdes_get_oos_oids <- heap_oos_delete_unreferenced, vacuum_forward_walk_reclaim_oos,
  vacuum_heap_oos_delete_within_sysop (vacuum/OOS-internal -> rev-cdc / heap_oos bucket)
heap_recdes_contains_oos <- heap_delete_home/relocation, heap_update_home/relocation (heap WRITE -> fwd-heap),
  heap_scan_get_visible_version_impl (F-004 fast-path 정확히 이 predicate 사용),
  heap_attrinfo_read_dbvalues_with_oos_prefetch (attr-layer, inventory 1건), locator_add_or_remove_index_internal(R-202),
  locator_update_index(F2 attr-layer), vacuum_* (rev-cdc), xlocator_repl_force(R-220),
  heap_oos_read_grouped_payloads/heap_recdes_get_oos_oids/heap_record_replace_oos_oids (OOS internal)
locator_fixup_oos_oids_in_recdes <- xlocator_repl_force(R-220/221); bridge_* = unit_tests
locator_oos_insert_force <- xlocator_repl_force(R-220/222)
NEW: 0 (전 caller가 row 또는 exclusion/plumbing bucket에 귀속)
```

### S5 — RECDES file universe vs R6 file->bucket table

```text
검색 목적: RECDES-bearing 파일 전수가 R6 표(82 files)와 일치하는지
명령: rg -l '\bRECDES\b' src  (glob 무제한 및 {c,cc,cpp,h,hpp} — 둘 다 82)
actual RECDES files: 82
R6 표에서 추출한 distinct 경로: 83 (그중 src/base/error_code.h 는 invariant 산문에서 -1379 인용용 언급이지
  RECDES 파일 아님 -> 추출 아티팩트)
comm -23 (actual - R6표) = ∅  => R6 표에 빠진 RECDES 파일 0
comm -13 (R6표 - actual) = {error_code.h}  => 산문 참조 1건(무해)
missing-from-table: 0
NEW: 0
```

### S6 — new-symbol probe (plausible heap-instance byte consumers not in inventory/notes)

```text
검색 목적: S1-S5 중 마주친, heap-instance record byte를 소비할 법한데 inventory/notes에 없는 신규 심볼
후보:
  xheap_has_instance -> heap_first (NO_BODY 존재체크, recdes.data=NULL, 결과 byte 미소비) => NEW-PATHS
  heap_classrepr_*/heap_get_class_{subclasses,info_from_record,name_*}/build_auto_increment_serial_name
    -> heap_get_class_record(class record) 소비. class record는 invariant B로 OOS-incapable.
       F-042 버킷이 범주 커버. NOT a heap-instance-byte consumer.
  heap_oos_read_grouped_payloads -> heap_oos.cpp 내부 Expand/prefetch mechanism (chokepoint 하류). 진입점 아님.
plausible OOS-capable instance-byte consumer (신규): 0
```

---

## NEW-PATHS

**One uncovered caller** surfaced that pass-1 and the inventory do not carry, found via the
independent wrapper-caller sweep (S3):

1. `src/storage/heap_file.c:17809` — `xheap_has_instance` -> `heap_first(..., recdes.data=NULL, PEEK)`.
   **LIVE**, but **NO_BODY**: the RECDES is declared with `recdes.data = NULL`, the record body is
   never read, and only the scan code (`S_ERROR` / `S_DOESNT_EXIST` / `S_END` / else) is inspected to
   return 0/1. Behaviourally identical to `heap_does_exist` (F-015) and `heap_is_object_not_null`
   (F-047), which ARE inventoried; the forward audit's F-012 enumeration of `heap_first` callers
   (F-026..F-029) omitted it. `heap_first` hardcodes `DONT_CONSUME_RAW_BYTES`, so **zero OOS exposure,
   no Expand, no stub materialization**. This is an inventory-completeness gap, not a correctness
   (P0/P1) path.

Recommendation for fwd-heap (source unchanged): add a NO_BODY wrapper-caller row for
`xheap_has_instance` mirroring F-015 / F-047, so the "all `heap_first` callers rowed" claim is
literally true.

### Non-gaps explicitly cleared (strict callouts)

- **heap_get_class_record heap_file.c-internal callers** (`heap_classrepr_get_from_record`,
  `heap_classrepr_dump`, `heap_classrepr_dump_all`, `heap_get_class_subclasses`,
  `heap_get_class_info_from_record`, `heap_get_class_name_alloc_if_diff`,
  `build_auto_increment_serial_name`) are not individually rowed but are **bucket-covered by F-042**
  ("other heap_get_class_record callers"): every one consumes a *class* record, which is OOS-incapable
  by invariant B (client `tf_class_to_disk`, never through `heap_attrinfo_determine_disk_layout`).
  Not a new path.
- **heap_does_exist's 11 callers** are all NO_BODY existence checks inheriting F-015's classification;
  none can consume record bytes.
- **dblink second site** (dblink_global_tran_scan_for_recovery:515) is covered by F-215; the stale
  F-029 evidence is a documentation nit, not an uncovered site.
- **heap_recdes_contains_oos write-path callers** (heap_delete/update_home/relocation) are
  bucket-covered by fwd-heap (heap_file.c -> fwd-heap in R6 table).

---

## Confirmations (independent, not inherited from pass 1)

- Call-argument total = 25 CONSUME + 59 DONT = 84, re-derived from source.
- 84/84 call-arg sites map to an inventory row (44 by exact file:line, 40 by function symbol).
- All 7-policy-API callers (S2/sweep) and all fixed-policy-wrapper callers (S3) resolve to a row or
  bucket, except the single NO_BODY `xheap_has_instance` omission.
- All 7 OOS chokepoints' callers resolve to rows/buckets (S4): 0 uncovered.
- RECDES file universe = 82 files, fully contained in the R6 table (S5): 0 missing.
- F-044..F-047 (pass-1 additions) verified present and correctly describing the
  ENABLE_UNUSED_FUNCTION dead-code trio + the heap_is_object_not_null NO_BODY probe.
- No OOS-capable heap-instance byte consumer exists outside the inventory (S6).

## Verdict

PASS-2: 1 new path — `xheap_has_instance` (heap_file.c:17809, `heap_first` NO_BODY existence probe,
DONT_CONSUME, zero OOS exposure); 0 correctness (P0/P1) new paths. Inventory-completeness gap only,
mirroring F-015 / F-047.
