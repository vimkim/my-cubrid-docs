# PR #7382 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7382](https://github.com/CUBRID/cubrid/pull/7382)
**제목:** [CBRD-26972] Add SHOW HEAP OOS diagnostics
**작성자:** vimkim
**HEAD SHA:** `93612cdff175e71d209785a19971bdae9625aa19`
**리뷰 일시:** 2026-07-02

> **TL;DR** (Non-blocking): OOS (큰 컬럼 값을 heap 밖 별도 파일에 저장하는 방식) 파일 통계를 SQL로 조회하는 진단 전용 PR. 정확성/메모리/동시성 문제는 없고, 신규 파일 라이선스 헤더 표기 하나만 사소하게 불일치. 머지 가능.

## Summary

- **변경 요약**: `SHOW HEAP OOS OF <class>` / `SHOW ALL HEAP OOS OF <class>` 문법과 scan 함수 `heap_oos_next_scan`을 추가해 heap에 연결된 OOS 파일의 통계(페이지 수, 레코드 수, 물리/미사용 바이트 등)를 조회
- **주요 이슈**: 없음 (진단 SQL 추가만, 저장/MVCC/vacuum/recovery 동작 불변)
- **확인 필요 사항**: 없음

---

## Findings

### Non-blocking (should consider)
- `src/storage/heap_show_scan_context.hpp:2` — 신규 파일인데 `Copyright 2008 Search Solution Corporation` + `2016 CUBRID` 두 줄 헤더를 사용. 같은 PR의 다른 신규 파일 `test_oos_sql_show.cpp:3`은 CUBRID 단독(`2016`) 헤더를 쓰므로 PR 내부에서 불일치. 신규 CUBRID 파일 관례는 `apache_src2.txt`(CUBRID 단독)이며, 이 struct는 `heap_file.c`에서 옮겨온 것이라 원본의 2008 헤더가 딸려온 것으로 보임. CI 라이선스 체크는 두 변형을 모두 통과시키므로 머지를 막지는 않음.

## JIRA Context
CBRD-26972 는 OOS 도입 후 heap 본체 통계와 OOS 외부 저장 통계를 SQL 수준에서 분리해 볼 수 있는 진단 스펙 확정이 목표. 본 PR은 그 스펙을 `SHOW HEAP OOS` 로 구현했고 티켓 의도 범위 안.

## Notes (검증했으나 지적 아님)
- `heap_oos_next_scan` 의 14개 `db_make_*` 호출은 `metadata_of_heap_oos` 의 14개 컬럼 정의와 순서/타입이 일치하고 `assert (idx == out_cnt)` 로 방어됨. `classname` 은 모든 경로에서 `free_and_init`, 페이지 fix/unfix 는 하위 헬퍼가 자체 관리하므로 핀 누수 없음.
- `heap_oos_find_vfid` 계약(false=실오류만, true+NULL vfid=OOS 파일 없음)을 정확히 사용. OOS 파일 없는 heap은 `Has_oos_file=0`, VFID 컬럼 `NULL` 로 정상 표기.
- `OOS` 는 `unreserved=1` 키워드로 등록하고 `identifier` 생성 규칙에 추가 -> `oos` 이름의 기존 객체가 깨지지 않음.
- `SHOWSTMT_TYPE` enum 값을 heap 그룹 중간에 삽입해 뒤 값(`INDEX_*` 등)이 한 칸씩 밀림. 이 값은 XASL(실행 계획) 스트림에 `or_pack_int` 로 담겨 client->server 로 전송될 뿐 디스크(카탈로그)에 영속되지 않고, CUBRID 는 client/server 버전 일치를 요구하므로 혼합 버전에서만 문제. 기존 show type 추가도 모두 그룹 중간 삽입 방식이라 본 PR 도입 결함 아님.
- Greptile P2 코멘트(no-OOS 케이스의 `Oos_page_size` 미검증)는 작성자가 이미 답변 후 `HeapWithoutOosReportsZeroStats` 테스트에 `EXPECT_EQ (int_val, DB_PAGESIZE)` 로 반영 완료.
