https://jira.cubrid.org/browse/CBRD-27933

## Purpose

- vacuum(지운 데이터를 나중에 정리하는 작업)이 삭제된 행의 OOS 값(행 밖에 따로 저장한 큰 컬럼 값)을 영구히 남기는 결함을 고칩니다. PR #8350 리뷰에서 지적된 문제입니다.
- AS-IS: heap 헤더 조회가 실패하면(latch timeout, 헤더 페이지 읽기 오류) `vacuum_oos_find_vfid_for_heap_record` 가 오류를 지우고 OOS 파일 없이 진행합니다. vacuum은 heap 슬롯만 지우고 OOS 값은 남기며, 로그 블록은 complete로 끝납니다.
- TO-BE: 조회 실패는 오류로 올라갑니다. 그 로그 블록은 `interrupted` 로 남고, 나중에 다시 실행될 때 슬롯과 OOS 값이 함께 회수됩니다.

## Implementation

- 새 오류 코드 `ER_VACUUM_OOS_LOOKUP_DEFERRED` (-1393)를 추가합니다. vacuum worker의 조회 실패만 이 코드로 바꿉니다. ALTER가 쓰는 `heap_vacuum_all_objects` 는 원래 오류를 그대로 받습니다.
- `vacuum_heap` 은 처음 생긴 -1393을 오류 스택에 보관하고, 블록의 다른 heap은 끝까지 처리합니다. 실패한 heap의 남은 객체는 그 실행에서 건너뛰므로, 헤더는 실행마다 한 번만 기다립니다. OOM, 셧다운, 그 밖의 오류는 지금과 같습니다.
- `vacuum_finished_block_vacuum` 과 `vacuum_check_shutdown_interruption` 의 debug assert가 -1393을 허용합니다.
- vacuum master는 interrupted 블록을 실패 뒤 1초에 한 번까지만 다시 실행합니다(`vacuum_job_cursor::force_data_update`). 바로 실패하는 오류가 블록을 master 주기(10ms)마다 다시 실행하지 않게 합니다.
- "OOS 플래그는 있는데 heap에 OOS 파일이 없는" 경우는 논리 결함입니다. debug는 assert로 멈추고, release는 로그를 남깁니다.
- debug 전용 장애 주입 `FI_TEST_VACUUM_OOS_HEADER_WAIT_TIMEOUT` (700000)를 추가합니다. 헤더가 잡혀 있으면 대기 조회를 latch timeout 오류로 바로 실패시킵니다. debug에서는 실제 timeout이 `pgbuf_timed_sleep` 의 assert에서 멈추기 때문입니다.

## Remarks

- 테스트는 `unit_tests/oos/test_oos_real_vacuum_server.cpp` 의 `OosRealVacuumHeaderHeld` 입니다. 테스트 스레드가 heap 헤더를 잡아 조회를 실패시킵니다. ctest `test_oos_real_vacuum_latch_timeout` 과 `test_oos_real_vacuum_latch_timeout_shutdown` 이 latch timeout 2초, vacuum worker 1개, 장애 주입 700000으로 돌립니다.
  - 수정 전 release: HOME, RELOCATION, 셧다운 세 경우 모두 OOS 값이 남고 블록이 complete로 끝났습니다.
  - 수정 후 release와 debug: 헤더가 풀리면 OOS 값이 회수되고, 셧다운 중이면 블록이 interrupted로 남습니다. 헤더를 잡고 있는 동안에도 다른 heap의 행과 같은 블록의 다른 heap 행은 vacuum됩니다. 실패한 heap은 실행마다 조회를 한 번만 하고, 재실행 간격은 1초 이상입니다.
  - debug OOS ctest 50개가 모두 통과했습니다.
- 조회가 계속 실패하면 그 블록이 회수될 때까지 로그 아카이브와 oldest unvacuumed MVCCID가 묶입니다. 포기하면 다시 누수가 되므로 한도를 두지 않았습니다.
- forward walk(`vacuum_forward_walk_reclaim_oos`)의 같은 조회 실패는 범위 밖이며 [CBRD-27953](https://jira.cubrid.org/browse/CBRD-27953)에서 다룹니다.
- 설계 결정과 측정은 [fix-decisions.md](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27933/fix-decisions.md)에 있습니다.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_019AXjyFPwr7pjtMB58s6dvB
