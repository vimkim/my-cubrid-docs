https://jira.cubrid.org/browse/CBRD-28377

## Purpose

- vacuum이 UPDATE가 버린 OOS chain을 회수하다 빈 버퍼 프레임을 300초 동안 얻지 못하면(-1123) 서버가 `LOG FATAL ERROR` 로 멈췄습니다(QA shell_long `bug_3627`).
- 이 경로는 로그 블록을 완료로 표시하지 않으면 vacuum이 블록을 다시 처리하고, OOS 회수기는 다시 실행하면 남은 chain을 끝까지 지웁니다(OOS-ADR-0008). 서버를 멈출 필요가 없습니다.
- AS-IS: `RVOOS_NOTIFY_VACUUM` 회수 중 page fix가 시간 초과로 실패하면 서버가 멈춥니다.
- TO-BE: 일시적 오류에서는 블록을 나중에 다시 처리하고 chain을 끝까지 회수합니다. 그 밖의 오류는 지금처럼 서버를 멈춥니다.

## Implementation

- `oos_reclaim_notified_chains ()`: `defer_transient` 인자를 추가했습니다. 켜져 있으면 page latch·버퍼 프레임 대기 시간 초과와 메모리 부족에서 새 오류 `ER_VACUUM_OOS_RECLAIM_DEFERRED` 를 돌려줍니다. 이 오류들은 page fix 단계에서만 생기고, chunk 삭제를 로그에 남긴 뒤에는 생기지 않습니다.
- `vacuum_oos_reclaim_notified_chains ()`: vacuum worker일 때만 미루기를 켜고, 같은 실행에서 그 heap의 다음 알림은 기다리지 않고 넘깁니다.
- `vacuum_process_log_block ()`: 새 오류를 `ER_VACUUM_OOS_LOOKUP_DEFERRED`(CBRD-27933)와 같이 처리합니다. 블록의 나머지는 처리하고 블록은 완료로 표시하지 않습니다.
- 커밋 postpone 경로(`oos_rv_reclaim_on_postpone ()`)는 미룰 곳이 없어 fail-stop을 유지합니다.
- 오류 코드 -1423 메시지(en_US, ko_KR)와 debug 전용 fault injection 1000000을 추가했습니다.

## Remarks

- 새 시험 `test_oos_real_vacuum_reclaim_fault`: 실제 vacuum worker에서 tail chunk를 지운 뒤 -1123과 page latch 시간 초과를 주입합니다. 수정 전에는 fail-stop이 일어나고, 수정 후에는 블록을 미룬 뒤 다시 처리해 chain을 모두 회수합니다. 다른 오류는 여전히 서버를 멈춥니다.
- debug 서버 시험: 실행 중 fault injection을 켜고 UPDATE하면 수정 전에는 서버가 `LOG FATAL ERROR` 로 멈췄습니다. 수정 후에는 서버가 계속 돌고, fault injection을 끈 뒤 버린 chain이 모두 회수되었습니다.
- REMOVE(DELETE된 행의 마지막 버전 제거) 경로의 postpone은 같은 -1123에서 여전히 멈춥니다. 정책 결정이 필요해 이 PR 범위에서 뺐습니다.
- 지속되는 일시적 오류는 블록을 약 1초마다 다시 시도합니다. 재시도 상한과 back-off는 CBRD-28276에서 함께 봅니다.
