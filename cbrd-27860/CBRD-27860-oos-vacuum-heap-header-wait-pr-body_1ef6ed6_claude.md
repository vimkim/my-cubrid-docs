https://jira.cubrid.org/browse/CBRD-27860

## Purpose

- OOS 값(행 밖에 저장한 큰 컬럼 값)이 있는 행을 vacuum하는 중에 같은 테이블의 INSERT가 새 heap 페이지를 만들면, 둘이 서로를 기다려 INSERT가 페이지 래치 대기 한도(기본 300초)까지 멈춘 뒤 실패하는 문제를 고칩니다.
- AS-IS: vacuum은 처리 중인 heap 페이지를 잡은 채 OOS 파일 ID를 읽으려고 heap 헤더를 무조건 기다립니다. 새 페이지를 만드는 INSERT는 heap 헤더를 먼저 잡고 마지막 heap 페이지를 기다립니다. vacuum이 그 페이지를 잡고 있으면 서로를 기다리며, 페이지 래치에는 교착 탐지가 없습니다.
- TO-BE: vacuum은 heap 헤더를 바로 잡지 못하면 잡고 있던 heap 페이지를 놓은 뒤 헤더를 기다리고, 페이지를 다시 잡아 레코드부터 다시 읽습니다.

## Implementation

- `heap_oos_find_vfid_nowait`를 추가합니다. heap 헤더를 조건부로 한 번만 시도하고 기다리지 않습니다. `heap_oos_find_vfid`는 서명과 "false는 실제 오류" 계약을 유지하며, 두 함수가 본문을 공유합니다.
- `vacuum_heap_prepare_record`의 `REC_HOME`과 `REC_RELOCATION` 경로가 새 helper `vacuum_heap_prepare_oos_vfid`를 부릅니다. 헤더가 바쁘면 forward 페이지와 home 페이지를 놓고, 페이지 없이 헤더를 기다려 조회한 뒤 home을 다시 잡고 `retry_prepare`로 돌아갑니다. home의 변경은 놓기 전에 로그에 남깁니다. 같은 함수의 `REC_BIGONE`이 overflow 파일 ID를 찾을 때 쓰는 방식과 같습니다.
- 재시작은 레코드당 한 번입니다. 기다린 조회의 답을 최종으로 쓰므로, 헤더 읽기가 계속 실패해도 페이지를 놓고 다시 잡는 일을 반복하지 않습니다.
- `test_oos_real_vacuum_server`에 실제 vacuum worker로 이 순환을 확인하는 테스트를 추가합니다. 테스트 스레드가 헤더를 잡은 동안 vacuum worker가 헤더를 기다리면, 마지막 페이지가 비어 있는지와 `heap_alloc_new_pages`가 끝나는지를 확인합니다.

## Remarks

- PR 7990의 [hornetmj 리뷰 R2](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4399323155)에 대응합니다. 리뷰에서 언급된 #8235는 다른 대기 순환([CBRD-27723](https://jira.cubrid.org/browse/CBRD-27723))을 고치며 이 경로를 바꾸지 않습니다.
- 수정 전 소스에서 새 테스트가 실패했습니다. vacuum이 헤더를 기다리는 동안 마지막 페이지를 잡고 있었습니다. 같은 순서에서 실제 `heap_alloc_new_pages`는 약 316초 기다린 뒤 `ER_PAGE_LATCH_TIMEDOUT`을 받았고, debug 빌드는 `pgbuf_timed_sleep`의 assertion으로 종료했습니다.
- 수정 후 새 테스트가 통과했고, debug 빌드에서 구성된 `ctest` 44개가 모두 통과했습니다. R5 수정(#8348)을 함께 적용한 빌드에서도 44개가 통과했습니다.
- 경합이 없으면 조건부 시도가 바로 성공하므로 페이지를 놓지 않습니다. home이나 forward가 heap 헤더 페이지 자체이면 같은 스레드의 재고정이 허용되어 해제 경로를 타지 않습니다.
- `REC_RELOCATION` 경로의 경합, release 빌드, SQL로 실행하는 INSERT·DELETE·vacuum 부하는 실행하지 않았습니다. 두 경로는 같은 helper를 쓰며, 차이는 forward 페이지를 놓는 것뿐입니다. 재현 절차는 JIRA에 있습니다.
