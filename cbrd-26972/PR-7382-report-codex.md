# PR #7382 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7382](https://github.com/CUBRID/cubrid/pull/7382)
**제목:** [CBRD-26972] Add SHOW HEAP OOS diagnostics
**작성자:** vimkim
**HEAD SHA:** `93612cdff175e71d209785a19971bdae9625aa19`
**리뷰 일시:** 2026-07-02

> **TL;DR** (Non-blocking): OOS (큰 variable column 값을 heap 밖 전용 파일에 저장하는 기능) 진단 SHOW 경로와 테스트는 빌드/단위 테스트를 통과했다. 다만 `SHOWSTMT_TYPE` (SHOW 문 종류 enum) 값을 중간에 끼워 넣어 기존 SHOW 타입의 직렬화 숫자가 밀리므로, 새 값은 enum 끝에 append 해야 한다.

## Summary

- **변경 요약**: `SHOW HEAP OOS OF <class>` / `SHOW ALL HEAP OOS OF <class>` 문법, metadata, scan dispatch, OOS 통계 출력, SQL 단위 테스트를 추가
- **주요 이슈**: `src/storage/storage_common.h:953` enum 값 삽입 위치
- **확인 필요 사항**: 없음

---

## Findings

### Non-blocking (should consider)

- `src/storage/storage_common.h:953` - `SHOWSTMT_TYPE` 새 값을 기존 `SHOWSTMT_INDEX_*` 앞에 추가해 XASL (서버 실행 계획 직렬화 형식)에서 `show_type` 정수 ID가 밀린다; `src/query/xasl_to_stream.c:4962`가 값을 그대로 pack 하고 `src/query/stream_to_xasl.c:5226`이 그대로 unpack하므로 enum 주석대로 끝에 append 해야 기존 SHOW 타입의 직렬화 ID를 안정적으로 유지할 수 있다.

```c
  SHOWSTMT_HEAP_CAPACITY,
  SHOWSTMT_ALL_HEAP_CAPACITY,
  SHOWSTMT_HEAP_OOS,
  SHOWSTMT_ALL_HEAP_OOS,
  SHOWSTMT_INDEX_HEADER,
```

## JIRA Context

CBRD-26972 는 OOS SHOW 진단을 추가하는 Minor Sub-task이고 parent는 CBRD-26583. 본 PR은 SQL에서 heap에 연결된 OOS file (OOS 전용 저장 파일) 상태를 확인하게 하는 티켓 범위 안에 있다.
