https://jira.cubrid.org/browse/CBRD-27886

## Purpose

- 상위 작업 CBRD-27881은 `feature/oos-merge`의 OOS 코드에서 정리할 부분을 찾아, 동작을 바꾸지 않는 작은 PR로 나누어 정리하는 작업입니다.
- 이 PR은 heap을 삭제하는 두 함수에 복사된 OOS 파일 정리 코드를 하나로 합칩니다.
- AS-IS: `xheap_destroy`와 `xheap_destroy_newly_created`에 같은 18줄 블록이 따로 있습니다. 이 블록은 `heap_oos_find_vfid`로 heap의 OOS 파일을 찾고 `oos_remove_file`로 지웁니다.
- TO-BE: 블록은 `heap_oos_remove_file` 한 곳에 있고, 두 함수가 이 함수를 부릅니다.

## Implementation

- 새 static 함수 `heap_oos_remove_file`에 원래 블록을 그대로 옮깁니다. 두 `ASSERT_ERROR` 위치도 같습니다.
- 두 호출부는 helper가 에러를 반환하면 그 에러를 그대로 반환합니다. 다른 파일 삭제 단계와의 순서는 바뀌지 않습니다.

## Remarks

- 변경 규모는 `src/storage/heap_file.c` 한 파일, 41줄 추가, 38줄 삭제입니다.
- 동작 차이가 하나 있습니다. heap header 페이지가 손상되어 `heap_oos_find_vfid`가 에러 없이 실패하는 경우입니다. 이전 코드는 heap 파일과 OOS 파일을 모두 남긴 채 `NO_ERROR`를 반환했습니다. 이 PR에서는 heap 파일을 정리하고 OOS 파일만 남깁니다. 정상 경로와 debug 빌드(같은 `ASSERT_ERROR`에서 멈춤)의 동작은 같습니다.
- `UNIT_TEST_OOS=ON` debug 빌드에서 OOS 관련 ctest 44개가 변경 전후 모두 통과했습니다.
- 기존 OOS 테스트는 `xheap_destroy_newly_created` 쪽에 닿지 않습니다. 그래서 `DONT_REUSE_OID` 테이블에 OOS 값을 넣고 DROP해, gdb로 이 경로가 helper를 부르는 것과 `cubrid diagdb -d 1`에서 OOS 파일이 사라지는 것을 확인했습니다.
- 진행 중인 #8350, #8299, #8369와 겹치는 hunk가 없습니다.
