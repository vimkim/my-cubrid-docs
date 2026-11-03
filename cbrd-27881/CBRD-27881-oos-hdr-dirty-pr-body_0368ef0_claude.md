https://jira.cubrid.org/browse/CBRD-27885

## Purpose

- 상위 작업 CBRD-27881은 `feature/oos-merge`의 OOS 코드에서 정리할 부분을 찾아, 동작을 바꾸지 않는 작은 PR로 나누어 정리하는 작업입니다.
- 이 PR은 `oos_file.cpp`에서 네 번 반복되는 코드를 helper 하나로 바꿉니다. 동작은 바뀌지 않습니다.
- AS-IS: OOS 파일 헤더 페이지의 bestspace 힌트(빈 공간이 많은 페이지 정보)를 갱신한 뒤, WAL 로그 없이 페이지를 dirty로 표시하는 여섯 줄이 네 곳에 그대로 들어 있습니다.
- TO-BE: 여섯 줄은 `oos_hdr_page_set_dirty_unlogged` 한 곳에 있습니다. "힌트는 WAL이 필요 없다"는 이유도 그곳에 한 번만 적습니다.

## Implementation

- `oos_hdr_page_set_dirty_unlogged`를 추가하고, `oos_stats_update`, `oos_try_reclaim_page_internal`, `oos_find_best_page`의 두 곳에서 호출합니다.
- 각 호출부 뒤의 `pgbuf_unfix_and_init`는 호출부에 그대로 둡니다. `log_skip_logging` 호출도 그대로 둡니다.
- 같은 이유만 반복하던 호출부 주석은 지웁니다.

## Remarks

- 변경 규모는 `src/storage/oos_file.cpp` 한 파일, 16줄 추가, 27줄 삭제입니다.
- `UNIT_TEST_OOS=ON` debug 빌드에서 OOS 관련 ctest 44개가 변경 전후 모두 통과했습니다. 마지막 수정은 주석 한 줄 삭제여서 빌드만 다시 확인했습니다.
- gdb로 확인하니 네 곳 중 세 곳은 기존 테스트가 실행합니다. `oos_find_best_page`의 sync-scan 직전 한 곳은 어떤 OOS 테스트도 실행하지 않아서, 조건을 강제로 바꿔 실행을 확인했습니다. 이 지점에 테스트가 닿지 않는 이유는 CBRD-27881에 별도 결함 후보로 기록했습니다.
- 진행 중인 #8330, #8299, #8367과 겹치는 hunk가 없습니다. 세 PR을 모두 적용한 상태에서도 컴파일됩니다.
