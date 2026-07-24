# CLOSURE-PASS-1 — CBRD-26847 OOS raw-RECDES audit: no-new-path check

- Agent: closure pass 1
- source anchor: `6816023df4ed910687523ab4d34bf667ab32b9cd` (READ-ONLY, unmodified)
- Method: re-ran seed searches, matched every policy call-argument site and every
  policy-API caller to an inventory row *by file+function symbol* (not line), expanded the
  fragment "new symbols" lists, diffed the R6 file→bucket table against the live RECDES file
  set, and swept unit_tests. Strict bias: a call-argument site with no inventory row is
  flagged even when it is provably benign (DONT_CONSUME / dead code).

---

## Search ledger

### S1 — policy-constant occurrence count (baseline re-verify)

```text
검색 목적: HEAP_RECDES_(CONSUME|DONT_CONSUME)_RAW_BYTES 전체 occurrence + call-argument 분리
명령: rg -n --glob '*.{c,cc,cpp,h,hpp}' 'HEAP_RECDES_(CONSUME|DONT_CONSUME)_RAW_BYTES' src unit_tests
raw: 29 CONSUME + 64 DONT = 93 occurrences
non-call (excluded): CONSUME 4 = heap_file.h:363(comment), :367(enum def), :372(validity macro),
  heap_file.c:26218(local bool comparison `expand_oos = policy==CONSUME`);
  DONT 5 = heap_file.h:368(enum def), :372(macro), heap_oos.cpp:362(comparison),
  heap_file.c:8176(comment), :8205(comment)
call-argument: 25 CONSUME + 59 DONT = 84  (matches plan baseline 25/59)
duplicate: 0 / pending: 0
NEW: 0 (count confirmed)
```

### S2 — every call-argument site → inventory row (match by file+function symbol)

```text
검색 목적: 84개 call-argument site 전부가 어떤 inventory 행 evidence에 존재하는지 확인
방법: 각 site의 enclosing function 산출(python heuristic) → AUDIT-INVENTORY.tsv grep(function name)
included-in-inventory: 80/84 사이트 (아래 함수들 전부 F-/R- 행 존재)
  heap_file.c: heap_next_1page(F-014) heap_first(F-012) heap_last(F-013)
    heap_scanrange_to_following(F-020/021) heap_scanrange_to_prior(F-022/023)
    heap_scanrange_next(F-024/025) heap_dump(F-016) heap_next_record_info(F-017)
    heap_prev_record_info(F-018) heap_get_class_record(F-019);
  locator_sr.c 26사이트 → F-101..129 / R-2xx (전부 존재);
  serial(F-211..213) sp_code(F-315) catalog_class(catcls_* R-508/F-039..042)
    system_catalog(X-514) scan_manager(F-034..038 등) query_executor(F-2xx)
    btree_load(F-033/X-503) histogram(F-031/032) dblink(F-028/029) connection(X-522)
    lock_manager(F-318/R-507) compactdb(±sr)(F-311/313, R-404/407)
    load_server_loader(F-317) px_scan walker(F-030 이웃 :456 DONT).
excluded-bucket: 0
duplicate: 0
NEW (call-argument site with NO inventory row): 5 lines / 4 functions — NEW-PATHS 아래 참조
```

### S3 — 7 policy-API caller sweep (variable-policy callers 포함)

```text
검색 목적: literal-constant sweep가 놓치는, 전파 정책(변수)로 API를 호출하는 caller 포착
명령: rg -n '\b<api>\s*\(' src (7 API: heap_next, heap_prev, heap_get_visible_version,
  heap_scan_get_visible_version, locator_lock_and_get_object[_with_evaluation], locator_get_object)
raw: 93 textual caller sites
included-in-inventory: 92 — 전 enclosing function이 (a) S2의 84-site 함수, 또는
  (b) API 내부 정의/플럼빙 [heap_next/heap_prev/heap_get_visible_version def,
  heap_get_visible_version_from_log(F-007), heap_get_record_info(F-011/017/018),
  locator_lock_and_get_object_internal(F-127/128/129), locator_*_with_evaluation/get_object def],
  또는 (c) S2 함수의 추가 라인(locator_delete_force_internal:6260, heap_get_last_version:26639 F-008,
  heap_get_visible_version_internal:26466 F-005).
excluded-bucket: 0
duplicate: 다수(같은 함수의 복수 호출 라인)
NEW: 0 — 유일한 미매칭 scan_next_index_scan(scan_manager.c:6437)은 주석
  ("...fetch them via heap_get_visible_version ().")의 false-positive. 실제 호출 아님.
```

### S4 — new-symbol expansion (fragments/*-notes.md)

```text
검색 목적: 각 fragment의 신규 symbol이 도입하는 caller/path가 전부 커버되는지
대상 symbol(주요): heap_get_record_data_when_all_ready, heap_get_referenced_by, cdc_get_recdes,
  cdc_make_dml_loginfo, la_get_recdes, la_disk_to_obj, la_rebuild_oos_recdes, la_apply_oos_insert_log,
  la_apply_dummy_oos_log, locator_oos_insert_force, locator_fixup_oos_oids_in_recdes,
  heap_recdes_contains_oos, heap_recdes_get_oos_oids, or_get_classrep, desc_disk_to_obj,
  heap_record_replace_oos_oids, heap_attrvalue_read_oos_inline, oos_read, or_get_classrep
included-in-inventory / excluded-bucket (caller enclosing function → row/bucket):
  heap_get_record_data_when_all_ready → heap_get_visible_version_internal(F-005),
    heap_get_last_version(F-008), locator_lock_and_get_object_with_evaluation(F-127) — 커버
  heap_get_referenced_by → locator_all_reference_lockset(F-105/S2) — 커버
  cdc_get_recdes / cdc_make_dml_loginfo → log_manager.c + flashback.c → R2(rev-cdc) — 커버
  la_get_recdes(R-210) la_disk_to_obj(R-211/212) la_rebuild_oos_recdes(R-215)
    la_apply_oos_insert_log(R-214) la_apply_dummy_oos_log(R-217) → R3(rev-repl) — 커버
  locator_oos_insert_force(R-222) locator_fixup_oos_oids_in_recdes(R-221) → caller
    xlocator_repl_force(R-220) — 커버
  heap_recdes_contains_oos / heap_recdes_get_oos_oids → callers 전부 커버:
    write-path heap_delete_relocation/heap_delete_home(heap write, →fwd-heap bucket),
    locator_add_or_remove_index_internal(R-202)/locator_update_index(F2 attr-layer),
    vacuum_forward_walk_reclaim_oos/vacuum_heap_record(→rev-cdc),
    load_server_loader finish_line(F-316/317 loader; producer-side OOS predicate, not a fetch consumer)
  or_get_classrep → heap_file.c:2002 + object_representation_sr.c → class-rep family(F-039..042) — 커버
  desc_disk_to_obj → unload_object.c/compactdb.c → rev-util(R-401..403, FU-04) — 커버
  heap_record_replace_oos_oids(F-001/006/007), heap_attrvalue_read_oos_inline / oos_read
    (terminal Resolve mechanism, F-006 choke point) — 커버
NEW: 0
```

### S5 — R6 file→bucket closure re-verify

```text
검색 목적: RECDES-bearing 파일 전수가 R6 file→bucket 표에 있는지
명령: rg -l '\bRECDES\b' src  (glob 무제한 및 {c,cc,cpp,h,hpp} 둘 다)
raw: 82 파일 (두 방식 동일)
included: 82/82 — comm -23 (actual − R6표) = ∅
missing-from-table: 0
NEW: 0
```

### S6 — unit_tests sweep

```text
검색 목적: unit_tests의 정책/OOS fetch path 존재 여부
명령: rg -n 'HEAP_RECDES_(CONSUME|DONT_CONSUME)_RAW_BYTES' unit_tests ; rg -ln 'oos_read|...' unit_tests
정책 상수(call arg): 0 (unit_tests에 정책 fetch 호출 없음 → inventory 제외 정당)
존재하는 것: unit_tests/oos/*.{cpp,hpp} 12개 — OOS 서브시스템 단위테스트(oos_read, heap_recdes_contains_oos,
  bridge_locator_fixup_oos_oids_in_recdes 등을 test subject로 사용). production fetch path 아님.
NEW: 0
```

---

## NEW-PATHS

Five DONT_CONSUME call-argument lines across four functions carry the policy constant at HEAD
but have **no inventory row** (matched by file+function). All are `DONT_CONSUME_RAW_BYTES`
(no Expand → no stub exposure, no physical materialize) so none is a P0/P1 correctness risk;
they are **inventory-completeness gaps**, not bugs. Listed because the closure criterion is
"every call-argument site appears in some inventory row".

1. `src/storage/heap_file.c:8655` and `:8676` — `heap_scanrange_prev` → `heap_prev(..., HEAP_RECDES_DONT_CONSUME_RAW_BYTES)`.
   DEAD CODE: enclosed in `#if defined (ENABLE_UNUSED_FUNCTION)` (heap_file.c:8618–8777);
   only a header declaration (heap_file.h:463), no compiled caller. Not covered by F-020..025
   (which cover only the live to_following/to_prior/next).
2. `src/storage/heap_file.c:8721` — `heap_scanrange_first` → `heap_next(..., DONT_CONSUME)`.
   DEAD CODE (same ENABLE_UNUSED_FUNCTION block); header decl heap_file.h:465 only, no caller.
3. `src/storage/heap_file.c:8766` — `heap_scanrange_last` → `heap_prev(..., DONT_CONSUME)`.
   DEAD CODE (same block); header decl heap_file.h:467 only, no caller.
4. `src/storage/heap_file.c:8977` — `heap_is_object_not_null` → `heap_get_visible_version(..., recdes=NULL, PEEK, DONT_CONSUME)`.
   LIVE. Sole caller `src/query/query_evaluator.c:2218`. A NULL-recdes existence/not-deleted
   probe — behaviourally identical to `heap_does_exist` (which IS inventoried as F-015), but the
   forward audit did not create an analogous row for it. Zero risk (recdes NULL, DONT_CONSUME),
   but strictly an uncovered live call-argument site.

Recommendation for the forward owner (fwd-heap): add a wrapper/no-body row for
`heap_is_object_not_null` (mirror F-015) and a dead-code note row for the three
ENABLE_UNUSED_FUNCTION `heap_scanrange_{prev,first,last}` sites, so the "all 84 call arguments
have an F-row" claim in SEARCH-LEDGER.md is literally true. No source change required.

---

## Confirmations (no gap)

- Call-argument total = 25 CONSUME + 59 DONT = 84, exactly matching baseline.
- 80/84 call sites and all 92 real API-caller sites map to an inventory row or API-plumbing row.
- All fragment "new symbols" resolve their callers to existing rows/buckets.
- R6 file→bucket table = complete (82/82 RECDES-bearing files, 0 missing).
- unit_tests contain OOS subsystem tests but 0 fetch-policy call sites (legitimately excluded).
- The only API-caller sweep anomaly (scan_manager.c:6437) is a comment, not a call.

## Verdict

PASS-1: 5 new call-argument sites (4 functions) uncovered — all DONT_CONSUME, 3 dead-code +
1 live NULL-recdes existence probe; 0 correctness (P0/P1) new paths.
