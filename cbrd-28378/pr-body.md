https://jira.cubrid.org/browse/CBRD-28378

## Purpose

- 여러 세션이 큰 값을 동시에 INSERT하면 OOS 페이지의 버퍼 프레임이 어느 LRU 목록에도 속하지 않은 채 버려지고, 버퍼 풀이 고갈되어 INSERT가 300초씩 멈춘다(QA shell_long `bug_3627`).
- AS-IS: OOS INSERT가 아직 채우는 중이라 latch를 쥔 페이지를 빈 공간 후보(bestspace hint)로 알린다. 다른 INSERT는 그 페이지에 조건부 latch를 반복해서 요청하다 거절되고, 이 거절이 프레임을 LRU 밖에 남긴다.
- TO-BE: hint는 다른 스레드가 쥐고 있지 않은 페이지만 가리킨다. 동시 INSERT가 서로의 페이지를 노리지 않는다.

## Implementation

- `oos_find_best_page ()`: 새로 할당한 빈 페이지를 hint에 올리지 않는다. 기존 hint에서 가져간 페이지는 hash와 헤더 `best[]` 에서 hint를 회수한다.
- `oos_insert_within_page ()`, `oos_insert_single_page_batch ()`, `oos_delete_chain ()`: 남은 빈 공간을 latch 아래에서 재고, latch를 놓은 뒤에 공개한다.
- `oos_stats_find_page_in_bestspace ()`: 바쁜 hash 후보는 lookup마다 한 번만 시도하고 건너뛴다. 지금은 파일의 첫 hint만 다시 읽어 바쁜 페이지 하나를 최대 100번 노린다.
- 로그, 복구, reclaim 절차는 바뀌지 않는다. bestspace hint는 로그를 남기지 않는 메모리 캐시다.

## Remarks

- 재현(`data_buffer_size=16m`, 10세션이 200KB 값을 40행씩 INSERT): 수정 전에는 400행 중 94행에서 10세션이 모두 멈추고, 1024개 프레임 중 946개가 LRU 밖에 남았다. 수정 후에는 400행이 0.6초에 끝나고 남은 프레임은 0개다. 2000행도 7.2초에 오류 없이 끝났다.
- 동시 INSERT에서 페이지 공유는 그대로다(6KB 값 3000개가 1501페이지, 페이지당 최대 개수).
- `unit_tests/oos/test_oos_bestspace.cpp` 에 테스트 3개를 추가했다. OOS 단위 테스트 74개가 ctest에서 모두 통과했다.
- page buffer 쪽 결함(거절된 조건부 요청이 대기자 표시를 남김)은 CBRD-28379에서 따로 고친다. OOS의 다른 드문 조건부 fix 경로도 그 수정이 필요하다.
- 상세 검증 보고서: https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-28378/verification.md
