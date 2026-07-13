# PR #7391 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7391](https://github.com/CUBRID/cubrid/pull/7391)
**제목:** [CBRD-27006] Improve OOS recdes locality
**작성자:** vimkim
**HEAD SHA:** `3173d3bd5a9c615a17fb9425c2e1c2fee1095474`
**리뷰 일시:** 2026-07-13

> **TL;DR** (Non-blocking): OOS (큰 가변 길이 값을 heap record 밖의 별도 file에 저장하는 방식) locality 변경에서 correctness regression은 발견하지 못했다. 머지 전 가독성을 높이려면 single-page OOS batch (한 heap record의 값을 한 OOS page에 배치하는 단위)의 record insert 중복, grouped read API의 과도한 cardinality 노출, parser 이동 후 남은 Case 번호 기반 ownership 주석을 정리할 수 있다.

## Summary

- **변경 요약**: 같은 heap record의 single-chunk OOS 값(한 OOS page에 들어가는 값)을 batch로 배치하고 같은 head page (OOS chain의 첫 chunk가 있는 page) read를 묶음.
- **주요 이슈**: 머지 차단 이슈 없음; 코드 중복 1건, API/dispatch 단순화 1건, 주석 정리 2건.
- **확인 필요 사항**: 없음.

---

## Findings

### Non-blocking (should consider)

- `src/storage/oos_file.cpp:1180` - `oos_insert_single_page_batch()`가 `oos_prepend_header`, `spage_insert`, OID 조립, physical WAL (write-ahead logging) 기록을 `oos_insert_within_page()`의 `src/storage/oos_file.cpp:1442`와 반복하므로, 이미 fix된 page (buffer pool에서 latch를 잡은 page)에 record 하나를 넣는 primitive를 추출하고 scalar/batch 경로가 공유하면 두 경로의 error/WAL 동작이 함께 유지된다.
- `src/storage/heap_file.c:10874` - caller는 grouped Resolve (여러 OOS 값을 page별로 묶어 읽는 경로)의 적용 여부만 필요한데 helper의 정확한 `requested_oos_count`까지 전달받으므로, count는 request reserve를 위해 helper 안에 두고 `grouped_applied` boolean/enum만 반환하면 explicit dispatch 결정은 보존하면서 parameter, assert, `src/storage/heap_oos.hpp:72`의 장문 계약을 줄일 수 있다.
- `src/storage/heap_file.c:10546` - inline reference parsing을 `heap_oos_parse_inline_ref()`로 이동한 뒤에도 함수와 두 caller가 `Case 1-5` 번호로 ownership을 설명하고 `src/storage/heap_file.c:10602`의 read 실패에서 이미 해제한 buffer를 owned로 표시하므로, 실패는 항상 `raw->data == NULL`/`oos_owned_buffer == false`, 성공만 true로 통일하면 no-op cleanup 분기와 이동에 취약한 Case 주석을 제거할 수 있다.
- `unit_tests/oos/sql/test_oos_sql_crud.cpp:219` - `CBRD-27006 follow-up`은 작성 시점에만 의미가 있고 test 이름이 ticket과 dispatch 조건을 이미 설명하므로, prefix를 제거하고 "2개 이상이면 grouped path, 0/1개이면 scalar path"라는 영속적인 invariant만 남기는 편이 낫다.

## JIRA Context

CBRD-27006은 하나의 heap record에 속한 OOS 값을 page 단위로 모아 insert/read page fix 횟수를 줄이는 작업이며, PR은 OOS OID 공유나 disk/WAL format을 바꾸지 않는 범위와 일치한다.

## Verification

- `codex review --base origin/feat/oos` 완료: actionable correctness regression 없음.
- 로컬 release build 성공.
- OOS ctest 23/23 통과.
