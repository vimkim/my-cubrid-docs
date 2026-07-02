# PR #7383 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7383](https://github.com/CUBRID/cubrid/pull/7383)
**제목:** [CBRD-26792] Fix OOS error logging and error codes
**작성자:** vimkim
**HEAD SHA:** `8aa05b62bd43d6c3d5776915bbd4efdedb860c0e`
**리뷰 일시:** 2026-07-02

> **TL;DR** (Non-blocking): 새 OOS (큰 가변 길이 컬럼을 별도 파일에 저장하는 기능) 에러 코드가 기본 콜스택 덤프 대상에 등록되지 않아 내부 손상 경로의 진단 정보가 줄어듭니다. 빌드와 OOS 테스트는 통과했지만 error-log cleanup 목적상 보완을 권장합니다.

## Summary

- **변경 요약**: OOS 오류/경고를 서버 에러 로그로 보내고 OOS 전용 에러 코드를 추가
- **주요 이슈**: 새 OOS 에러 코드가 기본 콜스택 덤프 대상에서 누락
- **확인 필요 사항**: 없음

---

## Findings

### Non-blocking (should consider)
- `src/base/error_code.h:1774` - `ER_HEAP_OOS_CORRUPTED_RECORD` 와 `ER_HEAP_OOS_INVALID_ARGUMENT` 가 추가됐지만 `src/base/system_parameter.c:5673` 의 `call_stack_dump_error_codes` (기본 콜스택 덤프 대상 에러 목록)는 기존 `ER_HEAP_OOS_BAD_INLINE_HEADER` 만 포함하므로, OOS (큰 가변 길이 컬럼을 별도 파일에 저장하는 기능) 내부 손상/잘못된 인자 경로가 기존 `ER_GENERIC_ERROR` 때 받던 기본 콜스택을 잃습니다.

```c
#define ER_HEAP_OOS_CORRUPTED_RECORD                -1378
#define ER_HEAP_OOS_INVALID_ARGUMENT                -1379
```

## JIRA Context

CBRD-26792 는 OOS 서버 에러 로그 사용, OOS 전용 에러 코드 분리, debug-only 로그 분리를 요구합니다. PR은 그 범위에 맞지만, 새 내부 에러 코드가 기본 콜스택 덤프 목록에 빠져 error-log cleanup의 진단성 측면이 약해집니다.

## Existing Comments

| User | File | Line | Summary |
|---|---|---:|---|
| greptile-apps[bot] | `src/storage/oos_log.hpp` | 149 | `_er_log_debug` 경로 때문에 `oos_error` 메시지가 서버 에러 로그에서 `DEBUG ***` 로 표시된다는 지적 |
| greptile-apps[bot] | `src/storage/oos_file.cpp` | 1065 | 런타임 가드 뒤의 `assert` 두 개가 debug 빌드에서도 실행되지 않는다는 지적 |
| greptile-apps[bot] | `src/storage/oos_log.hpp` | 148 | `_er_log_debug` 헤더와 OOS 포맷 문자열이 같은 줄 번호를 중복 출력한다는 지적 |
