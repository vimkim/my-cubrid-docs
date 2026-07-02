# PR #7383 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7383](https://github.com/CUBRID/cubrid/pull/7383)
**제목:** [CBRD-26792] Fix OOS error logging and error codes
**작성자:** vimkim
**HEAD SHA:** `8aa05b62b`
**리뷰 일시:** 2026-07-02

> **TL;DR** (작성자 확인 필요): 정합성 측면에서 머지 가능한 상태다. 다만 신규 에러 코드 이름/범위가 JIRA(CBRD-26792) 계획과 어긋나므로(계획 `ER_HEAP_OOS_RECORD_CORRUPTED`/`ER_HEAP_OOS_FILE_MISSING` -> 실제 `ER_HEAP_OOS_CORRUPTED_RECORD`/`ER_HEAP_OOS_INVALID_ARGUMENT`), 의도가 맞는지 확인이 필요하다.

## Summary

- **변경 요약**: OOS(큰 컬럼 값을 별도 페이지에 저장) 손상/인자 오류에 전용 에러 코드 2개를 추가하고, `oos_error`/`oos_warn`을 서버 에러 로그(`_er_log_debug`)로 라우팅. `ER_GENERIC_ERROR` 덮어쓰기 제거.
- **주요 이슈**: 없음 (정합성 버그 미발견)
- **확인 필요 사항**: 신규 에러 코드 이름/범위의 JIRA 계획 대비 차이

---

## Findings

### Questions for the author
- `src/base/error_code.h:1774` — JIRA CBRD-26792은 신규 코드를 `ER_HEAP_OOS_RECORD_CORRUPTED`와 `ER_HEAP_OOS_FILE_MISSING`로 명시했으나, PR은 `ER_HEAP_OOS_CORRUPTED_RECORD`(어순 반전)와 `ER_HEAP_OOS_INVALID_ARGUMENT`(계획에 없던 코드)를 추가함. `FILE_MISSING`은 JIRA가 목표한 vacuum HAS_OOS/OOS VFID(OOS 저장 파일 식별자) 불일치 경로용인데, PR Remarks가 그 hard abort를 "그대로 두었다"고 밝힘. 즉 이번 PR은 sub-task의 부분 구현. -> `FILE_MISSING`은 후속 PR 예정인지, `INVALID_ARGUMENT`는 의도적으로 추가한 다섯 번째 계열인지 확인 필요. (기능 버그 아님, 명명 일관성 이슈)

### Non-blocking (should consider)
- `src/storage/oos_log.hpp:148` — `oos_error`/`oos_warn`가 이제 `_er_log_debug`(CUBRID 서버 에러 로그 파일에 바로 기록하는 내부 helper)를 직접 호출하므로 `assert (er_Hasalready_initiated)`(error manager 초기화 여부 검사)에 대한 의존이 생김. 기존 self-contained 파일/stderr 로거에는 없던 결합. 현재 OOS 호출 지점은 모두 `er_init` 이후이므로 도달 불가한 latent coupling으로 판단하나, 부팅 극초기/셧다운 teardown 경로에서 호출되면 debug 빌드는 abort하고 release 빌드는 조용히 drop함. 근거: `_er_log_debug` -> `error_manager.c:2010 assert (er_Hasalready_initiated)`.

## JIRA Context
CBRD-26792(sub-task, "release 오류 경로를 CUBRID 에러 시스템에 맞춘다")의 목표는 (1) `oos_error`/`oos_warn`를 CUBRID 에러 경로로, (2) OOS 무결성 실패의 `ER_GENERIC_ERROR`/`ER_FAILED`를 전용 코드로 교체, (3) vacuum 불일치를 `logpb_fatal_error`(치명 오류 시 서버 강제 종료) hard fail로. PR은 (1)(2)를 구현하고 (3)은 명시적으로 범위 밖(temporary abort 유지). 위 Questions의 명명/범위 차이 외에는 티켓 의도에 부합.

## Existing Comments
`_er_log_debug`는 검증 로직상 정합성 문제는 없으나, greptile 봇이 3건의 P2를 남겼고 작성자 답변이 없음(참고용, 대부분 표기/데드코드 성격):

| path:line | 요지 |
|-----------|------|
| `oos_log.hpp:149` | `_er_log_debug`가 `DEBUG ***` NOTIFY 헤더를 붙여 ERROR 레벨 OOS 메시지가 로그에서 "DEBUG"로 표시됨 (구조화 에러 코드는 별도로 정상 기록되므로 가시성 손실은 아님) |
| `oos_file.cpp:1065` | 런타임 가드 이후의 `assert (src.data()!=nullptr)`/`assert (src.size()>0)`는 dead code |
| `oos_log.hpp:148` | `_er_log_debug`가 헤더에 `line`을 찍고 포맷 `%d`에도 `line`을 넘겨 한 엔트리에 줄 번호 이중 출력 |
