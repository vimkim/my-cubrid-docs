https://jira.cubrid.org/browse/CBRD-28379

## Purpose

- 조건부 페이지 latch 요청(`PGBUF_CONDITIONAL_LATCH`, 바로 얻지 못하면 기다리지 않고 포기하는 요청)이 거절될 때 BCB(버퍼 프레임)에 "대기자 있음" 표시(`waiter_exists`)를 남깁니다. latch를 쥔 스레드는 페이지를 놓을 때 이 표시를 보고, 프레임을 LRU 목록에 넣는 처리를 건너뜁니다.
- AS-IS: 막 할당하거나 디스크에서 읽은 페이지(VOID 영역)의 프레임이 어느 LRU 목록에도 속하지 않게 됩니다. 그런 프레임은 flush도 재사용도 되지 않습니다. 같은 표시 때문에 다른 스레드의 READ 요청도 불필요하게 막힙니다. 동시 OOS INSERT에서는 이 때문에 버퍼 풀이 고갈되었습니다(CBRD-28378).
- TO-BE: 거절된 조건부 요청은 latch 상태를 바꾸지 않습니다. 페이지를 놓으면 프레임은 항상 LRU 목록으로 돌아갑니다.

## Implementation

- `pgbuf_latch_bcb_upon_fix ()`: 대기열에 들어가는 무조건 요청만 `waiter_exists` 를 세웁니다. 비보유자의 요청과 READ→WRITE 승격 요청 모두 같습니다. 거절된 조건부 요청은 CBRD-26425 이전처럼 아무 흔적도 남기지 않습니다.
- `pgbuf_unlatch_bcb_upon_unfix ()`: 대기자 때문에 LRU 배치를 건너뛰었는데 깨우기 뒤에 아무도 latch를 받지 못한 경우를 처리합니다. 대기자가 모두 시간 초과나 interrupt로 포기한 경우입니다. 이때 VOID 영역 프레임을 대기자 없는 경우와 같은 방법으로 LRU에 넣습니다.
- `unit_tests/oos/test_pgbuf_conditional_latch_server.cpp`: 서버를 프로세스 안에서 부팅하는 회귀 테스트 4개를 추가합니다. OOS 서버 테스트의 부팅 코드와 DB fixture를 재사용합니다.

## Remarks

- 새 테스트 4개는 develop `ca39c2c6a4` 에서 모두 실패하고, 이 변경에서 모두 통과합니다(`ctest -R test_pgbuf_conditional_latch_server`).
- 버퍼 16MB에서 10개 세션이 200KB OOS 값을 40건씩 INSERT하는 재현으로 비교했습니다. develop debug 빌드는 라운드마다 1024개 프레임 중 57–167개를 LRU 밖에 남겼습니다. 이 변경에서는 10라운드 모두 0개였습니다.
- 설정된 ctest 75개 중 74개가 통과했습니다. `test_oos_real_vacuum_latch_timeout_retry` 는 장비 부하가 높을 때(load 약 229) 시간 초과로 1회 실패했습니다. 부하가 낮아진 뒤 3회 재실행했고 모두 통과했습니다.
- 리뷰 포인트: 두 번째 변경(모든 대기자가 포기한 경우의 배치)에 닿는 테스트는 없습니다. 대기자를 `pgbuf_timed_sleep ()` 안에서 멈출 hook이 없기 때문입니다.
- OOS 쪽 원인(채우기 전의 새 페이지를 빈 페이지로 알림)은 CBRD-28378에서 따로 다룹니다.
