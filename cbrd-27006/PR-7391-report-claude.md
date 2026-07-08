# PR #7391 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7391](https://github.com/CUBRID/cubrid/pull/7391)
**제목:** [CBRD-27006] Improve OOS recdes locality
**작성자:** vimkim
**HEAD SHA:** `fb42a24638266509c60a352b54d7ff9d0372919a`
**리뷰 일시:** 2026-07-08 (이전 보고서 head `56e22c15c` 이후 반영 커밋 포함 재리뷰)

> **TL;DR** (Blocking): 이번 head에서 추가된 OOS (큰 가변 길이 컬럼 값을 heap record 밖에 저장하는 방식) debug counter가 기본 빌드의 cub_server에 컴파일되고, 여러 worker thread가 비-atomic `+=` 로 같은 전역을 증가시켜 data race가 된다. counter를 atomic으로 바꾸거나 서버 빌드에서 제외하는 한 가지만 고치면 머지 가능. 이전 리뷰 지적 사항은 모두 반영 확인.

## Summary

- **변경 요약**: 한 record의 single-chunk OOS 값들을 같은 OOS page에 batch 삽입 (`oos_insert_many`) 하고 head page별로 묶어 읽어 (`oos_read_many`) `pgbuf_fix` (buffer pool page 고정) 횟수를 줄인다. OOS OID publication (복제 로그용 OID 기록) 은 public insert API가 직접 수행.
- **주요 이슈**: `oos_Debug_counters` 비-atomic 전역 counter가 SERVER_MODE (서버 프로세스 빌드) 기본 빌드에 포함되어 data race.
- **확인 필요 사항**: 없음.

---

## Findings

### Blocking (must fix)

- `src/storage/oos_file.cpp:138` — 새 debug counter 전역 `oos_Debug_counters` 가 production insert/read 경로에서 비-atomic `+=` (`OOS_COUNTER_ADD/INC`, line 139) 로 증가한다 (`oos_insert_single_page_batch:1194`, `oos_insert_many:1211`, `oos_read_many:1652`). 가드인 `CUBRID_UNIT_TEST_ENABLED` 는 전역 `add_compile_definitions` (CMakeLists.txt:773) 로 붙고 `UNIT_TEST_OOS` 옵션 기본값이 ON (CMakeLists.txt:74) 이라, 이 counter는 cub_server (cubrid/CMakeLists.txt:525 에 oos_file.cpp 포함) 에도 항상 컴파일된다. -> 동시 DML/SELECT worker thread들이 같은 전역에 무동기 write 하는 data race (C++ 표준상 undefined behavior, ThreadSanitizer 검출 대상). 실질 피해는 counter 값 손실에 그치지만 수정이 한 줄 수준: 필드를 `std::atomic<unsigned long long>` 으로 바꾸거나, counter 증가 코드를 unit-test 전용 빌드로 한정.

### Non-blocking (should consider)

- `src/storage/oos_file.cpp:1157` — `oos_insert_single_page_batch` 의 루프 본문이 `oos_insert_within_page` (1416-1448) 의 chunk 기록 본문 (`oos_prepend_header`, `scope_exit` 버퍼 해제, `spage_insert` 검사, OID 조립, `oos_log_insert_physical`) 과 로그 문자열만 다른 복사본이다. single-chunk 기록/로깅 방식이 바뀌면 두 곳을 같이 고쳐야 한다 -> "이미 fix된 page에 chunk 1개 삽입" helper로 합칠 수 있다.
- `src/storage/heap_file.c:10837` — batched read 진입을 판정하는 probe `heap_attrvalue_oos_inline_ptr` 의 skip 조건 (dedup-key attr (내부 예약 컬럼), shared/class attr, `is_fixed`, 변수 컬럼 NULL) 이 scalar reader `heap_attrvalue_read` 의 조건을 손으로 복제한 것이다. 현재 두 경로가 동일하게 판정함은 확인했으나, 이후 scalar 쪽에만 skip 조건이 추가되면 probe가 과대 판정해 같은 record를 scalar와 batched가 다른 값으로 읽는 silent divergence가 될 수 있다 -> 공용 predicate 함수로 묶는 것을 권장.
- `src/storage/oos_file.cpp:1227` — `page_capacity` 가 `oos_get_max_chunk_size_within_page` (2216) 내부 식 `DB_ALIGN_BELOW (spage_max_record_size (), OOS_ALIGNMENT)` 을 그대로 재계산한다. `max_chunk_size + (int) sizeof (OOS_RECORD_HEADER)` 로 유도하면 2215의 `spage_max_record_size` TODO가 수정될 때 두 값이 어긋날 일이 없다.

## JIRA Context

CBRD-27006 ([OOS] [M2] improve recdes locality, parent CBRD-26583). 구현은 티켓 범위 (record 내 OOS placement/read locality 개선, on-disk format 불변) 와 일치한다. 이전 보고서의 지적 -- resize 중복 초기화, publication clear 시점, inline header 파싱 중복, single-OOS read fast path 상실 -- 은 `1a278e978` / `885c1630a` 와 read dispatch 커밋 (OOS 값 2개 이상 요청 시에만 batched 경로) 으로 모두 반영되었음을 코드로 확인했다. 이번 재리뷰에서 추가로 검증하고 문제 없음을 확인한 사항: (1) OOS 컬럼은 demotion (큰 값을 record 밖으로 내리는 결정) 조건상 16B (`OR_OOS_INLINE_SIZE`) 초과가 보장되어 (heap_file.c:12401), 빈 RECDES (record descriptor, 값 직렬화 버퍼) 전달로 인한 NULL 버퍼 기록은 도달 불가; (2) `oos_read_many` 의 multi-chunk continuation이 `oos_read_across_pages` 에 넘기는 길이 인자 (전체 길이) 는 scalar `oos_read` 와 동일한 계약이고 header 검증에만 쓰인다; (3) `locator_oos_insert_force` 의 `oos_push_oos_oid` 제거는 `oos_insert` 내부 publication으로 대체되어 정확히 1회 기록이 유지된다.
