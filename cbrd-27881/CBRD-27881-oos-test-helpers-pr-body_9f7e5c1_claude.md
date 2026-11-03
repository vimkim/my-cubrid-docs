https://jira.cubrid.org/browse/CBRD-27883

## Purpose

- 상위 작업 CBRD-27881은 `feature/oos-merge`의 OOS 코드에서 정리할 부분을 찾아, 동작을 바꾸지 않는 작은 PR로 나누어 정리하는 작업입니다.
- 이 PR은 OOS 단위 테스트의 공용 helper를 정리합니다. 테스트 코드만 바꾸며, 엔진 코드와 테스트 동작은 바뀌지 않습니다.
- AS-IS: 같은 helper 묶음(`namespace test_oos_utils`)이 `test_oos_common.hpp`와 `test_oos_server_common.hpp`에 따로 들어 있습니다. 두 복사본은 이미 함수 순서, 중괄호, 주석이 서로 달라졌습니다.
- TO-BE: helper는 `test_oos_utils.hpp` 한 곳에만 있고, 두 공용 header가 이 파일을 include합니다.

## Implementation

- `unit_tests/oos/sql/test_oos_sql_common.hpp`에서 호출하는 곳이 없는 `exec_sql_commit`, `run_vacuum`을 지웁니다. `run_vacuum`만 쓰던 `vacuum.h` include도 지웁니다.
- helper 9개를 새 `unit_tests/oos/test_oos_utils.hpp`로 옮깁니다. 두 복사본을 token 단위로 비교했더니, 한쪽 `return {};`에 중괄호가 있는지만 달랐습니다. 중괄호가 있는 쪽을 옮겼습니다.
- `.cpp` 파일과 CMake 파일은 바꾸지 않습니다. 모든 호출부는 계속 `test_oos_utils::`를 붙여 부릅니다.

## Remarks

- 변경 규모는 4개 파일, 165줄 추가, 272줄 삭제입니다. 추가된 줄은 대부분 옮긴 코드이며, `git diff --color-moved`로 확인할 수 있습니다.
- `UNIT_TEST_OOS=ON` debug 빌드에서 바뀐 header를 쓰는 테스트 파일 28개를 ccache 없이 다시 컴파일했고, 경고와 오류가 없었습니다.
- OOS 관련 ctest 44개(`ctest -R 'oos|test_byte_span_writer'`)가 변경 전후 모두 통과했습니다. GitHub CI는 OOS 단위 테스트를 빌드하지 않으므로 로컬 실행 결과를 적었습니다. 마지막 수정은 header 주석 두 줄이어서 빌드만 다시 확인했습니다.
- 진행 중인 #8128, #8299는 이 PR이 바꾼 header를 고치지 않습니다. 두 PR을 이 브랜치에 적용한 상태에서도 OOS 테스트 파일이 모두 컴파일되는 것을 확인했습니다.
