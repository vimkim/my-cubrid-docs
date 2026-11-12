https://jira.cubrid.org/browse/CBRD-28067

## Purpose

- OOS 개발자가 개별 ctest 결과를 1분 안에 받고, 독립적인 workspace 테스트를 병렬로 실행하도록 합니다.
- AS-IS: 일부 묶음이 수분씩 걸리고 시간 제한이 없거나 제각각입니다.
- TO-BE: 모든 OOS 항목에 60초 이하의 제한을 요구하고, 쓰기 경로를 분리한 workspace 묶음의 동시 실행을 허용합니다.

## Implementation

- gtest 필터와 동시 INSERT 라운드를 나눕니다. 케이스와 전체 입력 작업량을 유지합니다.
- 헤더 조회 실패와 무관한 행의 회수를 모두 관찰하면 대기를 끝냅니다. 오류 코드·메시지 검사는 유지하며 오류 스택의 함수·소스 위치를 찾는 반복 비용을 줄입니다.
- workspace마다 DB·설정·로그·임시 경로를 분리합니다. 공유 DB를 쓰는 테스트와 준비·정리는 직렬로 유지합니다.
- CMake configure에서 `TIMEOUT` 누락, 0, 60초 초과를 거부합니다. `src/` 변경은 없습니다.

## Remarks

- GCC Debug의 전체 OOS 62개 항목이 `-j 1`, `-j 2`, `-j 6`에서 모두 통과했습니다. 420개 gtest 케이스는 각각 한 항목에 속합니다.
- 최장 항목은 기준 174.32초에서 최종 직렬 24.96초였습니다. 부하가 큰 실행에서도 최장 45.26초로 제한 안에 끝났습니다.
- workspace 여섯 묶음의 5회 반복과 쓰기 경로 추적을 통과했습니다. CI는 실행하지 않았습니다.
- [전체 항목·케이스 시간표와 검증 결과](https://github.com/vimkim/my-cubrid-docs/blob/main/CBRD-28067/verification.md)
