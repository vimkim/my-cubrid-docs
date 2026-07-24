# FINDINGS — CBRD-26847

source anchor: `6816023df4ed910687523ab4d34bf667ab32b9cd` (조사·판정 시점, 수정 전)

## 요약

| 구분 | 수 |
|---|---|
| inventory 행 | 256 (forward 109, reverse 147) |
| BUG (stub 노출 / physical 오염) | **0** |
| OVER_EXPAND | 25행 → **16개 distinct source 사이트** |
| FOLLOWUP (별도 이슈 필요) | 5행 → 후속 항목 FU-01~FU-05 |
| TBD | 0 |

핵심 결론: **stub이 논리 소비자에게 노출되는 경로(P1)와 physical image가 잘못 materialize되는
경로(P0)는 0건이다.** WAL/undo/redo는 구조적으로 fetch 정책과 분리되어 있고(HEAP_GET_CONTEXT
vs HEAP_OPERATION_CONTEXT), 모든 server→client 채널은 Expand를 거치며, replication은
stub 보존 + replica-side OID fixup으로 동작한다. 발견된 결함은 전부 "필요 없는 곳에서 Expand"
(P2/P3)와 설계 후속 항목이다.

## P2 — 불필요한 record-level Expand (본 이슈에서 수정)

수정 원칙: 소비자가 attribute layer / header/CHN / no-body이면
`HEAP_RECDES_CONSUME_RAW_BYTES` → `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`.

| finding | 사이트 (symbol, 수정 전 line) | 근거 (inventory) |
|---|---|---|
| FIND-01 | `heap_scanrange_next` 첫 object fetch — heap_file.c:8579 | F-024, F-036: 소비자는 scan_manager.c:5916→eval_data_filter (attr layer). 같은 함수의 fallback/일반 branch는 DONT. grouped scan block 시작마다 불필요 Expand |
| FIND-02 | `heap_scanrange_to_following` heap_file.c:8370, `heap_scanrange_to_prior` heap_file.c:8481 | F-020, F-022: local recdes를 버리는 위치 지정 fetch. 유일 caller(scan_manager.c:5053/5057)는 start_oid=NULL 전달로 해당 branch 자체가 dead. 정리 차원 |
| FIND-04 | `locator_update_force` old record fetch — locator_sr.c:5799, 5942 | F-110, F-111: 소비자는 or_mvcc_get_header + locator_update_index→heap_attrinfo_read_dbvalues (모두 OOS-aware). sibling branch 5793은 DONT로 이미 올바름. **부가 위험**: 대용량 multi-chunk OOS old record를 고정 크기 area로 Expand하다 S_DOESNT_FIT grow-retry 없이 실패할 수 있는 경로 — Expand 제거로 함께 해소 |
| FIND-05 | `locator_delete_lob_force` — locator_sr.c:6581 | F-113: 소비자 heap_attrinfo_delete_lob (attr layer, heap_file.c:11063 heap_attrvalue_read) |
| FIND-06 | `locator_repl_prepare_force` old record fetch — locator_sr.c:6945 | F-114, R-223, R-314: 유일 소비 or_chn (header). replica-side 불필요 Expand |
| FIND-07 | `locator_mvcc_reeval_scan_filters` — locator_sr.c:13831 | F-126: 소비자 attr layer (MVCC 재평가) |
| FIND-08 | serial 3개 사이트 — serial.c:234 (`xserial_get_current_value_internal`), :511 (`serial_update_cur_val_of_serial`), :648 (`xserial_get_next_value_internal`) | F-211~F-213, R-502: 소비 전부 attr layer. update 경로의 old recdes도 heap_attrinfo_set_uninitialized→heap_attrvalue_read(OOS-aware, heap_file.c:11948/11962)로만 읽음 — 직접 재검증함 |
| FIND-09 | `sp_get_code_attr` — sp_code.cpp:91 | F-315, R-503: 소비 heap_attrinfo_read_dbvalues 단일 속성. SP code payload는 OOS 대상이 되는 대표적 대용량 값 → 실효 이득 큼 |
| FIND-10 | `server_class_installer::locate_class_for_all_users` — load_server_loader.cpp:247 | F-317, R-408: 소비 attr layer (db_user.name) |
| FIND-11 | `lock_dump_resource` — lock_manager.c:5644 | F-318, R-507: 소비 or_mvcc_get_header (MVCC header만; HAS_OOS는 header 크기에 무영향) |

## P3 — 무해하나 계약 표기가 틀린 사이트 (본 이슈에서 수정)

| finding | 사이트 | 근거 |
|---|---|---|
| FIND-12 | `process_value` existence probe — compactdb.c:566, compactdb_sr.c:110 | F-311/F-313, R-404/R-407: recdes=NULL이라 Expand는 heap_file.c:26441-26445 guard로 실행 자체가 안 됨(inert). 소비 계약상 DONT가 맞으므로 표기 교정 |
| FIND-03 (재판정) | `heap_get_class_record` (DONT 고정) + raw `or_get_classrep` parser callers | F-019, F-039~F-042: class record는 tf_class_to_disk(client 직렬화)+raw locator force로만 쓰여 demotion 지점(heap_attrinfo_determine_disk_layout)을 통과하지 않음 → stub 불가능(provenance) → 현행 DONT+raw parse는 CORRECT. F1의 CONTRACT_GAP 제기는 F2(F-101/102/120)·F4·R6(X-519/R-508) 증거로 기각. 방어적 주석/guard는 FU-05 |

## FOLLOWUP — 별도 이슈로 분리 (FOLLOWUPS.md 상세)

| id | 내용 | inventory |
|---|---|---|
| FU-01 | flashback이 vacuum이 이미 회수한 old OOS value chain을 oos_read할 수 있음 — retention/pin 계약 부재. CBRD-26950 slot 재사용과 결합 시 다른 row 값 silent 오독 가능성 | R-105~R-107, R-110 |
| FU-02 | OOS replication log 발행이 PK index 유지 경로(locator_add_or_remove_index_internal, locator_sr.c:8150-8168)에 위치 — 알려진 refactoring 항목 | R-202 |
| FU-03 | Expand-후-raw-reinsert 경로는 re-demote하지 않음: redistribute_partition_data, catcls_*, offline compactdb(disk_update_instance→heap_update_logical). 데이터 안전(HAS_OOS clear, stub-free VOT)하지만 OOS backing 상실 → inline/REC_BIGONE화. 제품 결정 필요 | R-307, R-312, R-313 |
| FU-04 | client 터미널 parser(desc_disk_to_obj, load_object.c)는 OOS-blind — 안전성이 전적으로 upstream Expand에 의존, 방어적 검사 없음 | R-401~R-403 |
| FU-05 | class-record 경로의 stub-불가는 provenance 논증 — write 경로에 방어적 HAS_OOS assert/주석 추가 검토 | F-019, F-039~F-042 |

## 문서/스펙 정합성 노트 (코드 결함 아님)

- OOS-CONTEXT.md(2026-07-13)의 "CBRD-26948 OPEN / xlocator_fetch_all stub 누출"은 이 HEAD에서
  사실이 아님 — locator_sr.c:2913 CONSUME으로 Expand됨. census의 "~22 _expand_oos 호출처" 서술도
  CBRD-27029 이전 역사적 서술. 컨텍스트 갱신 필요.
- OOS-CONTEXT.md의 "CDC flashback OOS-stub Resolve 미구현" 항목은 stale — CDC/flashback 모두
  attr layer로 Resolve함 (R2). 실제 남은 문제는 FU-01(retention)이다.
- OOS-CONTEXT.md §1의 rejection error code -1375 표기는 source(-1379, error_code.h:1776)와 불일치.
- demotion gate가 여전히 `DB_PAGESIZE/4` (heap_file.c:12117) — CBRD-27057(4,060B target)은 이
  worktree에 미반영. 본 이슈 범위 밖, CBRD-27057에서 추적.

## 판정 원칙 기록

- COPY/PEEK는 판정에 사용하지 않음. "이 class에 OOS 속성 없음" 단독 근거 불인정 — class record
  계열만 provenance(작성 경로가 demotion을 통과 불가) 논증으로 stored-safe 인정.
- 모든 RESOLVE 판정의 공통 근거: heap_attrvalue_read가 OR_IS_OOS에서
  heap_attrvalue_read_oos_inline→oos_read로 분기 (heap_file.c:10476-10479, 직접 재검증).
