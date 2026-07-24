# FOLLOWUPS — CBRD-26847

source anchor: `6816023df4ed910687523ab4d34bf667ab32b9cd`

본 이슈에서 처리하지 않고 별도 이슈로 분리해야 하는 항목. 각 항목은 inventory 행과
`finding_id`/followup 열로 연결된다. 분리하더라도 해당 경로의 inventory 행은 유지한다.

## FU-01 — flashback의 old OOS value chain retention 부재 (P1급 위험, 설계 필요)

- **영향 경로**: `flashback_make_loginfo` → `cdc_get_recdes`(undo image) →
  `cdc_make_dml_loginfo` → attr layer Resolve → `oos_read`(old head OOS OID).
  Inventory: R-105, R-106, R-107, R-110.
- **문제**: old version의 OOS value chain은 vacuum이 old heap-record version을 회수할 때
  `oos_delete` 된다(불변식 2/3). flashback은 과거 구간을 읽으므로 chain이 이미 회수됐을 수
  있다 → `oos_read` 실패(ER_HEAP_OOS_CORRUPTED_RECORD류). 나아가 CBRD-26950(vacuum slot 재사용)과
  결합하면 재사용된 slot의 **다른 live row 값**을 silent하게 읽을 수 있다.
- **임시 안전성**: CDC는 최근 구간 중심이라 노출이 작고, 오독은 CBRD-26950 수정으로 상당 부분
  차단된다(occupied-vs-mine 구분). 실패(에러)는 남는다.
- **필요한 결정**: flashback 지원 구간 내 OOS chain retention(pin) 계약 또는 flashback의
  명시적 에러 계약(값 미복원 표시) 중 택일. WAL에 old value를 싣는 대안은 undo 비대화로 기각된
  이력이 있음(불변식 2).
- **추천 테스트**: OOS-backed row UPDATE → vacuum 완료 대기 → 해당 구간 flashback →
  값/에러 동작 확인. multi-chunk 값 포함.

## FU-02 — OOS replication log 발행 위치 refactoring (알려진 항목)

- **영향 경로**: `locator_add_or_remove_index_internal` (locator_sr.c:8150-8168) 내
  `RVREPL_OOS_INSERT`/`RVREPL_DUMMY_OOS_RECORD` 발행 (tdes->oos_insert_lsa_queue 소비).
  Inventory: R-202.
- **문제**: PK index 유지 경로에 OOS replication log 발행이 위치 — 정확성 문제는 없으나
  index 없는/PK 없는 경로와의 결합, 유지보수성 문제. OOS-CONTEXT의 기존 refactoring 항목과 동일.
- **필요한 결정**: 발행 지점을 attrinfo force(값 직렬화 시점)로 이동하는 설계(Heesoo 안,
  OOS-CONTEXT Optimization B)와의 통합 여부.

## FU-03 — Expand-후-raw-reinsert 경로는 re-demote하지 않음 (제품 결정 필요)

- **영향 경로**: `redistribute_partition_data`(R-307), `catcls_*` 재삽입(R-312),
  offline compactdb `disk_update_instance` → `heap_update_logical`(R-313).
- **현상**: CONSUME으로 Expand한 record를 raw로 재삽입하면 demotion 지점
  (`heap_attrinfo_determine_disk_layout`)을 통과하지 않아 OOS backing을 잃고 inline 또는
  non-OOS `REC_BIGONE`이 된다. 데이터는 안전(Expand가 HAS_OOS를 clear하고 VOT를 stub-free로
  재작성, chain aliasing 없음 — heap_oos.cpp:282).
- **필요한 결정**: partition 이동/offline compact 후에도 OOS 배치를 유지할지(raw-reinsert에
  demotion 삽입 or attrinfo 경유로 전환), 아니면 현 동작(스토리지 형태 변화 허용)을 계약으로
  명문화할지.
- **추천 테스트**: OOS-backed row가 있는 partition redistribute / offline compactdb 후
  값 동등성 + 저장 형태(HAS_OOS, DISK_SIZE) 관찰.

## FU-04 — client 터미널 parser의 OOS-blind 방어선 부재 (P3, 관찰성)

- **영향 경로**: `desc_disk_to_obj`/`get_desc_current` (load_object.c) 등 client parser.
  Inventory: R-401~R-403.
- **문제**: server-side Expand가 유일한 방어선. upstream 정책이 퇴행하면(과거 CBRD-26948처럼)
  parser는 stub 16B를 값으로 해석한다. parser에 HAS_OOS/IS_OOS 감지 시 명시적 에러를 내는
  방어 코드 추가 검토.

## FU-05 — class-record 경로의 stub-불가 provenance를 방어적 계약으로 격상 (P3)

- **영향 경로**: `heap_get_class_record`(DONT 고정) 및 raw `or_get_classrep` parser callers.
  Inventory: F-019, F-039~F-042.
- **문제**: class record가 stub을 가질 수 없음은 "작성 경로가 demotion을 우회한다"는 provenance
  논증이다. 미래에 server-side class-record 작성 경로가 생기면 무증상 파손 가능. class-record
  write 경로 또는 `heap_get_class_record`에 HAS_OOS assert/주석 추가 검토.
  (본 이슈에서 주석 보강까지는 수행 가능 — Phase 4에서 판단.)

## 문서 후속 (이슈 아님)

- OOS-CONTEXT.md 갱신: CBRD-26948 상태(이 HEAD에서 해소), CDC/flashback "missing feature" 항목을
  FU-01(retention)로 대체, rejection error code -1379 표기 교정, ADR-0003 census 수치의
  CBRD-27029 이후 무효화 주석.
- CBRD-26948 JIRA 상태 재확인(코드상 해소 — 담당자 확인 필요).
