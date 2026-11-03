https://jira.cubrid.org/browse/CBRD-27882

## Purpose

- 상위 작업 CBRD-27881은 `feature/oos-merge`의 OOS 코드에서 정리할 부분을 찾아, 동작을 바꾸지 않는 작은 PR로 나누어 정리하는 작업입니다.
- 이 PR은 그 첫 단위입니다. 더 이상 쓰이지 않는 코드를 지워서, 코드를 읽는 사람이 의미 없는 인자와 매크로를 해석하지 않아도 되게 합니다.
- 동작은 바뀌지 않습니다.

## Implementation

- `OOS_STATS_PREV_BEST_INDEX` 매크로를 지웁니다. 저장소 전체에 이 매크로를 쓰는 곳이 없습니다.
- 테스트용 함수 `bridge_oos_vpid_init_new`와 `unit_tests/oos/test_oos.cpp`에 있던 그 선언을 지웁니다. 이 함수를 부르는 테스트가 없습니다. 같은 파일에서 이미 지워진 다른 bridge 함수를 설명하던 주석 한 줄도 지웁니다.
- `oos_stats_update`의 `prev_freespace` 인자를 지웁니다. 유일한 호출부인 `oos_delete_chain`은 항상 0을 넘겼습니다. 그래서 조건을 `freespace > 0`으로 씁니다.
- `oos_stats_find_page_in_bestspace`에서 `pgbuf_unfix_and_init` 바로 뒤의 `*out_pgptr = NULL;`을 지웁니다. 이 매크로가 이미 포인터를 `NULL`로 바꿉니다.

## Remarks

- 변경 규모는 3개 파일, 3줄 추가, 14줄 삭제입니다.
- `UNIT_TEST_OOS=ON` debug 빌드에서 OOS 관련 ctest 44개(`ctest -R 'oos|test_byte_span_writer'`)가 모두 통과했습니다. 마지막 수정은 주석 한 줄 삭제여서 `test_oos`만 다시 실행했고, 통과했습니다.
- 변경 전 코드에서도 저장 계층 OOS ctest 15개가 같은 결과로 통과했습니다.
- GitHub CI는 OOS 단위 테스트를 실행하지 않습니다. 그래서 단위 테스트 결과는 로컬 실행 결과를 적었습니다.
- 진행 중인 #8330, #8299도 `oos_file.cpp`를 고치지만 겹치는 hunk는 없습니다. 두 PR의 diff가 이 브랜치에 그대로 적용되는 것을 `git apply --check`로 확인했습니다.
