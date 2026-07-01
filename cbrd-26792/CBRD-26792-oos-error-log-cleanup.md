## Purpose

CBRD-26792는 OOS (큰 컬럼 값을 따로 떼어 다른 페이지에 저장하는 방식) 진단 로그와 에러 코드를 정리하는 작업이다.
JIRA에는 서버 에러 로그 사용, OOS 전용 에러 코드 검토, 디버깅 로그 분리가 요구 사항으로 적혀 있다.

기존 `oos_error`와 `oos_warn`은 `$CUBRID/log/oos.log`와 선택적인 `stderr` 출력에 의존했다.
서버 프로세스에서 직접 `stderr`를 쓰면 운영 로그 흐름과 어긋나고, QA가 보통 확인하는 서버 에러 로그에서도 놓치기 쉽다.
또 일부 OOS 손상 감지 경로가 `ER_GENERIC_ERROR`를 반환해서, 호출자가 실제 문제가 잘못된 인자인지 저장된 OOS 메타데이터 손상인지 구분하기 어려웠다.

이 변경의 목적은 항상 보여야 하는 OOS 경고와 오류를 서버 에러 로그로 보내고, 데이터 손상과 잘못된 호출 인자를 별도 에러 코드로 드러내는 것이다.
디버깅용 trace/debug/info 로그는 debug build 전용으로 남겨서 개발 중 상세 추적은 유지한다.

## Implementation

`src/storage/oos_log.hpp`에서 OOS 로그 sink를 둘로 나누었다.
`oos_error`와 `oos_warn`은 새 `oos_log_server_internal`을 통해 `_er_log_debug`로 기록한다.
이 경로는 release build에서도 살아 있고 서버 에러 로그에 남는다.
`oos_trace`, `oos_debug`, `oos_info`는 debug build에서만 `oos_log_debug_internal`을 사용하며, 기존처럼 `$CUBRID/log/oos.log`로 기록한다.

OOS logger가 직접 `stderr`로 쓰던 보조 출력과 `CUBRID_OOS_LOG_STDERR` 제어는 제거했다.
이 변경은 `oos_log.hpp`의 logger 동작만 대상으로 한다.
`src/storage/heap_file.c`의 OOS+REC_BIGONE temporary hard abort는 의도적으로 그대로 두었다.
여기서 `REC_BIGONE`은 레코드 전체가 heap page에 들어가지 않아 overflow page로 넘어가는 형식이다.
`src/query/vacuum_oos.cpp`의 vacuum invariant hard abort도 그대로 둔다.

`src/base/error_code.h`에 `ER_HEAP_OOS_CORRUPTED_RECORD`와 `ER_HEAP_OOS_INVALID_ARGUMENT`를 추가하고 `ER_LAST_ERROR`를 뒤로 이동했다.
`msg/en_US.utf8/cubrid.msg`와 `msg/ko_KR.utf8/cubrid.msg`에는 두 에러 메시지를 추가했다.

`src/storage/oos_file.cpp`는 OOS 파일 내부에서 발견한 손상된 레코드 메타데이터를 `ER_HEAP_OOS_CORRUPTED_RECORD`로 반환하도록 정리했다.
여기서 OOS slot은 OOS 파일 page 안의 개별 저장 위치이고, chunk는 큰 값을 여러 page에 나눠 저장할 때의 조각이다.
대상은 OOS slot이 header보다 작은 경우, chunk가 caller buffer를 넘는 경우, chain header의 chunk index나 전체 길이가 기대값과 다른 경우, empty chunk, non-head chunk read, inline 길이와 header 길이 불일치, 최종 written length 불일치, delete chain의 잘못된 record length, `oos_get_length`의 짧은 record 방어 경로다.
`oos_insert`는 `nullptr`, 0 byte, `INT_MAX` 초과 크기 입력을 먼저 검사하고 `ER_HEAP_OOS_INVALID_ARGUMENT`를 반환한다.
이 검사를 debug `assert`보다 앞에 두어 debug build에서도 실제 방어 경로를 테스트할 수 있게 했다.

`src/storage/heap_oos.cpp`는 inline OOS slot 자체가 잘못된 경우 `ER_GENERIC_ERROR` 대신 기존 OOS inline header 에러인 `ER_HEAP_OOS_BAD_INLINE_HEADER`를 반환한다.
inline OOS slot은 heap record 안에 남아 있는 작은 metadata 영역이며, 실제 OOS 값의 OID와 전체 길이를 담는다.
`oos_read` 실패는 새 generic error로 덮어쓰지 않고 하위 OOS 함수가 설정한 에러를 그대로 반환한다.
그래서 손상 원인이 `oos_file.cpp`에서 감지되면 상위 heap OOS read 경로에서도 같은 에러 코드가 유지된다.

`unit_tests/oos/test_oos.cpp`에는 `OosInsertRejectsInvalidSource`를 추가했다.
이 테스트는 null/zero-length source가 `ER_HEAP_OOS_INVALID_ARGUMENT`로 거절되는지 확인한다.
기존 caller length mismatch 테스트는 `ER_HEAP_OOS_CORRUPTED_RECORD`를 기대하도록 바꾸었다.
`unit_tests/oos/test_oos_common.hpp`의 주석은 OOS error/warn 로그가 서버 에러 로그를 사용한다는 현재 동작에 맞게 수정했다.

## Remarks

리뷰에서는 먼저 `src/storage/oos_log.hpp`의 macro별 sink 분리가 의도대로인지 확인하면 된다.
`oos_error`와 `oos_warn`은 항상 서버 에러 로그로 가고, debug-only 로그만 OOS 전용 파일로 간다.

두 번째로 볼 부분은 `src/storage/oos_file.cpp`의 에러 코드 매핑이다.
이 PR은 하위 storage/page 함수 실패를 새 에러로 바꾸지 않는다.
OOS 계층이 직접 판단한 잘못된 인자와 OOS 레코드 메타데이터 손상만 새 OOS 전용 에러로 표현한다.

temporary hard abort 제거는 이 PR 범위가 아니다.
`heap_file.c`의 OOS+REC_BIGONE hard abort와 `vacuum_oos.cpp`의 missing OOS VFID invariant hard abort는 현재 branch 정책에 맞춰 그대로 둔다.
`VFID`는 OOS file을 가리키는 volume/file identifier다.

### Test Plan

공백 오류 검사를 통과했다.
debug build와 install이 성공했다.
OOS CTest suite는 23개 중 23개가 통과했다.
