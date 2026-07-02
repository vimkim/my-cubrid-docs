# PR #7391 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7391](https://github.com/CUBRID/cubrid/pull/7391)
**제목:** [CBRD-27006] Improve OOS recdes locality
**작성자:** vimkim
**HEAD SHA:** `56e22c15c4ae024c141035b62db9dfb6d17acf6c`
**리뷰 일시:** 2026-07-02

> **TL;DR** (Non-blocking): batch 공간 계산, OOS OID publication 순서 (복제 로그와 OID의 attribute-order 페어링), 에러 경로의 버퍼/페이지 해제를 모두 추적했고 머지를 막을 결함은 없다. 남는 이슈는 두 가지다: batched read가 기존 stack-scratch fast path를 잃어 OOS 값마다 malloc/free가 발생하고, inline OOS header 파싱/검증 로직이 3벌로 복제되어 scalar 경로와 어긋날 위험이 있다.

## Summary

- **변경 요약**: 한 heap record의 single-chunk OOS (큰 가변 길이 컬럼 값을 record 밖 OOS file에 저장하는 방식) 값들을 같은 OOS page에 batch 삽입하고 (`oos_insert_many`), 읽기도 head page별로 묶어 (`oos_read_many`) page fix (buffer pool에 page를 고정하는 `pgbuf_fix`) 횟수를 줄인다. OOS OID publication은 public insert API가 직접 수행하도록 정리.
- **주요 이슈**: read hot path의 per-value heap 할당 회귀, inline OOS header 파싱 3중 복제.
- **확인 필요 사항**: 새로 도입된 `try/catch (std::bad_alloc)` 이 no-exceptions 규칙과 충돌하는지 (아래 Questions).

---

## Findings

### Non-blocking (should consider)

- `src/storage/heap_file.c:10907` — `heap_attrvalue_prepare_batched_oos_read` 는 값 크기와 무관하게 항상 `recdes_allocate_data_area` (heap 할당) 를 사용한다. 기존 scalar 경로 `heap_attrvalue_read_oos_inline` 은 16KB (IO_MAX_PAGE_SIZE) 이하 값을 stack scratch 버퍼로 읽어 heap 할당이 0이었다. -> OOS record를 읽는 모든 row에서 OOS 컬럼 수만큼 malloc/free가 추가되어, page fix 절감으로 얻은 이득을 allocator 비용으로 일부 되갚는다.

- `src/storage/heap_file.c:11230` — batched 경로 진입 조건이 `heap_recdes_contains_oos (recdes)` (record 자체의 OOS 보유 여부) 라서, 요청된 attribute에 OOS가 하나도 없어도 `num_values` 크기 vector 2개 할당 + 전체 prepare pass를 수행한다 (requests가 비어 `oos_read_many` 는 호출되지 않으므로 정합성 문제는 없음). 비-OOS 컬럼만 SELECT하는 흔한 쿼리에서 row당 불필요한 비용. 요청 attribute 중 OOS가 있는지 먼저 확인하고 진입하면 해소된다.

- peak memory: read는 한 row의 모든 OOS 값 버퍼를 DB_VALUE 변환 전까지 동시에 유지하고 (`heap_file.c:10947` 의 prepare 루프), insert는 OOS 컬럼마다 직렬화 값 전체를 `pending` 에 malloc+memcpy 한다 (`heap_file.c:12774`). OOS 컬럼이 1개인 insert는 batching 이득 없이 전체 값 복사 비용만 추가된다. insert 쪽 trade-off는 상세 문서에 명시되어 있으나 read 쪽 동시 유지분은 미기재 -> 단일 OOS 컬럼일 때 기존 scalar 경로로 우회하는 fast path를 고려.

- 중복 구현 drift 위험 1: `heap_file.c:10861` 의 offset-table switch와 inline header 파싱 (OID + bigint 읽기, null/범위 검증) 은 각각 `heap_attrvalue_point_variable`, `heap_attrvalue_read_oos_inline` 에 이미 있는 로직의 복사본이다. inline OOS header 검증 규칙이 3곳에 존재하게 되어, 이후 형식/검증 변경 시 한 곳을 놓치면 scalar read와 batched read가 같은 record를 다르게 판정한다.

- 중복 구현 drift 위험 2: `src/storage/oos_file.cpp:1666` `oos_read_head_from_fixed_page` 는 `oos_read_within_page` 의 본문 + scalar `oos_read` 의 head 검증 블록 (chunk_index==0, total_data_length 일치) 과 거의 동일하다. page를 caller가 fix한다는 차이만 있으므로, 공용 helper로 합치거나 scalar 경로가 새 helper를 쓰도록 정리 가능.

- publication-state clear가 3벌 존재: `heap_file.c:12793` (inline), `oos_file.cpp:1081` `oos_clear_insert_publication_state` (static이라 heap에서 호출 불가), `test_oos_server.cpp:43` (test 복사본). clear할 필드가 늘어나면 세 곳이 어긋난다. helper를 public으로 노출하고 test는 bridge 함수로 쓰는 쪽을 권장.

- 소소한 정리: batched/legacy dispatch if/else 블록이 `heap_attrinfo_read_dbvalues` (11230) 와 `_without_oid` (11304) 에 동일하게 복붙되어 있고, `heap_file.c:10941` 의 zero-init 루프는 `resize()` 가 이미 원소를 0으로 초기화하고 prepare 함수 초입에서 다시 초기화하므로 중복이라 삭제 가능.

### Questions for the author

- `heap_file.c:10934,12736`, `oos_file.cpp:1867` 의 `try/catch (std::bad_alloc)` 은 CLAUDE.md의 "Never use C++ exceptions in engine code" 규칙과 충돌한다. base의 `heap_oos.cpp` 에 같은 패턴 선례가 있으나 이 두 파일에는 이 PR이 처음 도입 — feat/oos에서 합의된 관례인지, 아니면 `std::nothrow` 계열로 정리할지 확인 필요.

## JIRA Context

CBRD-27006 ([OOS] [M2] improve recdes locality, parent CBRD-26583). Ticket 본문은 비어 있으나 PR/연결 문서가 범위를 정의: 단일 record 내 OOS placement/read locality 개선, on-disk format과 OOS OID 정책 불변. 구현은 이 범위와 일치한다. 리뷰에서 별도 검증한 사항 두 가지. batch 공간 계산은 정확하다 — bestspace (OOS page 여유 공간 힌트 캐시) 재확인에 쓰는 `spage_max_space_for_new_record` 가 slot 1개 몫을 이미 차감하므로 record N개 + slot N개가 정확히 확보된다. 복제 방출 루프 (`locator_sr.c:8142,8945`) 는 `heap_recdes_contains_oos` guard와 삽입 전 clear 계약 덕분에 실패가 남긴 잔존 publication state를 소비할 수 없다 — 실패 시 partial state를 남기던 기존 코드보다 오히려 안전해졌다.
