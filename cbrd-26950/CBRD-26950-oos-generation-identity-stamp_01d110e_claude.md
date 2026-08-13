# [CBRD-26950] Verify OOS chain identity before vacuum delete — 상세 설명

- JIRA: https://jira.cubrid.org/browse/CBRD-26950
- 대상 커밋: `01d110e8a` (base: `feat/oos` + `origin/develop` 머지 `07fef9d48`)
- 작성: 2026-08-12, Claude Code

## Purpose

vacuum 이 재사용된 OOS 슬롯의 살아있는 데이터를 삭제하는 문제를 막는다. OOS (Out-of-row Storage — heap 의 큰 가변 컬럼을 별도 파일 페이지로 빼서 저장하는 방식) 에서 UPDATE 의 이전 값 체인은 undo image (변경 전 행 모습을 로그에 찍어둔 불변 스냅샷) 에만 참조가 남고, vacuum 의 forward-walk 가 나중에 그 참조를 따라 청크를 회수한다.

- **AS-IS**: 회수 직전 확인은 `oos_chunk_exists()` 의 슬롯 점유 여부 하나뿐이다. OOS OID 는 물리 주소 `(volid, pageid, slotid)` 라 슬롯이 재할당되면 같은 OID 가 남의 청크를 가리키는데, 이를 구분할 신원 정보가 청크에 없다. 완주하지 못한 vacuum 블록은 `start_lsa` 가 전진하지 않아 재시작 후 처음부터 재주행되고, 1차 pass 가 비운 슬롯을 그 사이 다른 살아있는 행이 재사용했다면 2차 pass 가 그 데이터를 지운다. 스톡 debug 빌드에서 소스 수정 없이 3회 실행 3회 모두 발현했다 (판독 불가 행 163~293건, 상세는 JIRA 본문).
- **TO-BE**: 청크를 INSERT 할 때 페이지 단위 카운터에서 4바이트 generation 을 발급해 청크 헤더와 heap 의 OOS inline stub 양쪽에 기록하고, `oos_delete` 가 삭제 전에 둘을 등가 비교한다. 불일치(슬롯 재사용)나 부재(이미 회수됨)는 에러 없는 no-op 이므로, 블록 재시도가 살아있는 체인을 파괴할 수 없다.

## Implementation

### 온디스크 변경 (feat/oos 미출시 — 마이그레이션 불필요)

| 대상 | AS-IS | TO-BE |
|------|-------|-------|
| OOS 데이터 페이지 | 청크 레코드만 있는 slotted page | slot 0 에 `OOS_PAGE_HEADER` 레코드 신설 — `uint32 generation_counter` 보관 |
| 청크 헤더 `oos_record_header` | 16B | 20B (+`generation` 4B) |
| OOS inline stub (`OR_OOS_INLINE_SIZE`) | 16B (head OID 8B + full length 8B) | 20B (+기대 generation 4B) |
| 삭제 조건 | 슬롯 점유 여부 | generation 등가 비교, 불일치/부재 시 no-op |

### 발급 경로 — `src/storage/oos_file.cpp`

- `oos_vpid_init_new_data_page()` (신설): 데이터 페이지 초기화 시 slot 0 에 카운터 0 짜리 헤더 레코드를 심고 `RVOOS_NEWPAGE` 하나로 로깅한다. 파일 헤더 페이지(sticky first page)는 기존 `oos_vpid_init_new()` 를 그대로 쓰며 slot 0 에 `OOS_HDR_STATS` 를 유지한다.
- `oos_insert_record_in_fixed_page()`: 이미 잡고 있는 W-latch 아래에서 카운터+1 을 발급해 청크 헤더에 스탬프하고, `spage_insert` 성공 후에만 카운터를 커밋한다 (실패한 insert 는 값을 소모하지 않는다). 카운터 갱신의 내구성은 청크 자신의 `RVOOS_INSERT` 로그가 담당한다.
- `oos_insert` / `oos_insert_many` / `oos_insert_across_pages`: head 청크의 generation 을 out-param 으로 반환한다 (`oos_insert_request` 에 `generation_out` 추가). 멀티청크 체인은 청크마다 발급받고 stub 에는 head 의 값이 실린다.
- 페이지당 용량: slot 0 헤더 레코드 몫(정렬된 레코드 8B + 슬롯 4B)을 뺀 `oos_get_data_page_capacity()` 를 신설하고 `oos_get_max_chunk_size_within_page()` 가 이를 따른다.

### 검증 경로

- `oos_delete(thread_p, vfid, oid, expected_generation)`: 신설 probe `oos_chain_head_matches()` 가 head 청크의 저장 generation 과 기대값을 비교한다. 페이지 dealloc / 슬롯 부재 / generation 불일치는 모두 no-op (NO_ERROR), 실제 I/O 오류만 전파. 기존 존재 여부 probe `oos_chunk_exists()` 는 삭제했다.
- `heap_recdes_get_oos_refs()` (`src/storage/heap_file.c`, 구 `heap_recdes_get_oos_oids`): stub 에서 `(head OID, generation)` 쌍 (`oos_chain_ref`) 을 추출한다. 호출자 셋 모두 전환 — vacuum forward-walk (`vacuum_forward_walk_oos_delete_atomic`), REMOVE 경로 (`vacuum_heap_oos_delete_within_sysop`), eager 정리 (`heap_oos_delete_unreferenced`).
- stub 기록: `heap_oos_column_plan` 에 generation 을 담아 `or_put_int` 로 직렬화 (`heap_file.c` 변환 경로). 파싱 측 경계 검사(`heap_oos_parse_inline_ref`, midxkey 크기 검증)는 20B 기준으로 갱신.

### 복구 — `src/transaction/recovery.h/.c`

- `RVOOS_NEWPAGE` (=140) 신설: redo 는 페이지 타입 + slotted page 초기화 + slot 0 헤더 레코드 재삽입 (`oos_rv_redo_newpage`, heap 의 `RVHF_NEWPAGE` 패턴). undo 는 `pgbuf_rv_new_page_undo`.
- `oos_rv_redo_insert()`: slot 0 이 아닌 삽입(=청크)의 redo 시 청크에 스탬프된 generation 으로 페이지 카운터를 **단조 증가**(MAX) 재생한다. 이 함수는 `RVOOS_DELETE` 의 undo (롤백 복원) 로도 실행되므로, 대입이 아닌 MAX 여야 카운터가 퇴행해 같은 generation 을 재발급하는 일이 없다.

### 복제 (HA)

- `thread_p->oos_oids` 발급 결과 publication 이 `(OID, generation)` 쌍 (`oos_published_ref`, `src/thread/thread_entry.hpp`) 으로 확장됐다. slave 적용 시 `locator_fixup_oos_oids_in_recdes` (`src/transaction/locator_sr.c`) 가 복제된 heap 레코드의 stub 에서 OID 와 함께 generation 도 slave 로컬 발급값으로 다시 쓴다 — 스토리지를 다시 읽지 않는 순수 바이트 fixup 이다. 이 갱신이 빠지면 slave stub 이 master generation 을 갖게 되어 slave vacuum 회수가 전부 no-op(영구 누수)이 된다.
- `log_applier.c` 의 청크 재조립 헤더는 transient 라 generation 0 으로 무방 (slave 측 `oos_insert` 가 자체 발급).

### 파생 변경

- `OR_OOS_INLINE_SIZE` 16→20 (`src/base/object_representation.h`) 에 따라 demotion 수익성 경계가 `>16B` 에서 `>20B` 로 이동 (상수 참조라 코드 변경 없음). 경계 SQL 테스트의 페이로드를 18자(20B, inline 유지)/19자(24B, OOS 이관)로 조정.
- 단위 테스트: stub 직렬화 라운드트립에 generation 추가, 테스트 전용 `oos_delete_current_generation()` 헬퍼 (head 청크의 현재 generation 을 읽어 삭제 — 프로덕션 경로는 stub 의 기대값을 쓰므로 테스트 전용), 합성 heap recdes 빌더의 stub 에 실제 generation 스탬프, `oos_get_generation()` 진단 API 신설.
- `oos_get_stats_by_vfid` 통계 walk 와 `spage_collect_statistics` 기반 sync 스캔은 slot 0 을 건너뛰어 순수 청크 수를 센다 (heap 페이지와 같은 관례가 됨).

## Remarks

- **리뷰 포인트 1 — 카운터 단조성**: `oos_rv_redo_insert` 의 MAX 재생과 "발급은 반드시 페이지 카운터에서" 규칙이 정확성 불변식의 전부다. 발급 지점(`oos_insert_record_in_fixed_page`)과 대조 지점(`oos_chain_head_matches`) 두 곳만 보면 검증이 끝나도록 설계했다.
- **리뷰 포인트 2 — no-op 계약의 범위**: eager 경로와 REMOVE 경로는 원래 부재 시 하드 에러였으나 이제 no-op 이다. 잘못 삭제(데이터 손실) 대신 잘못 스킵(관측 가능한 누수) 쪽으로 실패 방향을 통일했고, debug 빌드의 oos.log 에 스킵 사유가 남는다.
- **리뷰 포인트 3 — 복제 fixup**: `locator_fixup_oos_oids_in_recdes` 의 generation 재기록이 publication 쌍에 의존한다. publication 을 비우는 경로(트랜잭션 시작, 오류 정리)는 기존 `.clear()` 그대로라 추가 동기화 지점이 없다.
- **제한**: 온디스크 포맷 변경이므로 기존 feat/oos 테스트 DB 는 재생성해야 한다 (recovery rcvindex 추가 포함, `recovery.h` 의 기존 주석 정책과 동일).
- 후속: 같은 "삭제 전 신원 대조" 계약을 OOS 빈 페이지 회수(CBRD-26786)와 flashback retention(CBRD-26847 FU-01)이 재사용할 수 있다. OOS-CONTEXT 명세 문서의 stub 크기·수익성 기준·청크 헤더 레이아웃 갱신은 별도 커밋으로 진행한다.

### Test Plan

- 단위 테스트: `ctest` OOS 스위트 25/25 통과 (debug_gcc). 갱신 항목 — stub 20B 라운드트립, generation 추출, 경계(18자/19자) 이관 판정, 재현/이중삭제 no-op 경로.
- 재현 회귀: JIRA 첨부 `cbrd-26950-poc.sh` (수정 전 3/3 발현, 판독 불가 행 163~293건) 를 수정 후 실행 — 두 pass 재삭제 OOS OID 0건, 판독 불가 행 0건, 대조군 무손상. 살아있는 체인 수(`SHOW HEAP OOS`)가 기대값 21,956 (UPDATE 후 R1 20,000 + 커밋된 R3 1,956) 과 정확히 일치해 정당한 회수(누수 없음)도 함께 확인했다.
