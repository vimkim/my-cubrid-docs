https://jira.cubrid.org/browse/CBRD-27781

## Purpose

- OOS chunk 삭제를 되돌릴 수 있는 상태로 두면 sysop abort나 재시작 undo가 다른 트랜잭션이 이미 가져간 slot 위에 옛 chunk를 다시 씁니다(CBRD-27781). UPDATE의 undo image를 따라가는 forward-walk는 rollback된 UPDATE의 살아 있는 chain도 지웁니다(CBRD-27237).
- AS-IS: vacuum REMOVE와 eager 정리는 sysop 또는 트랜잭션 안에서 `RVOOS_DELETE`(전체 레코드 undo)로 chunk를 지우고, UPDATE가 버린 chain은 forward-walk가 commit 여부를 모른 채 지웁니다. LSA reclaim gate가 빈 페이지 반환을 미룹니다.
- TO-BE: chain 삭제를 결정한 단위가 commit한 뒤에만 postpone으로 회수하고, chunk는 redo-only로 tail부터 head 순서로 지웁니다. UPDATE는 commit 후 postpone이 명시적 MVCCID로 `RVOOS_NOTIFY_VACUUM`을 남기고(A'), vacuum이 오래된 snapshot이 끝난 뒤 회수합니다. 승인된 설계는 ADR-0008(2026-11-05 수락)입니다.

## Implementation

- **회수 의도(reclaim intent)**: `RVOOS_RECLAIM_POSTPONE`(142). vacuum REMOVE는 heap slot 제거와 같은 sysop에 의도를 기록하고 `log_sysop_commit`의 postpone에서 회수합니다. SA/non-MVCC eager 정리는 DML 때 의도만 기록하고 commit에서 회수합니다. abort(문장·savepoint·트랜잭션·sysop)는 의도를 버립니다.
- **UPDATE 알림(A')**: MVCC UPDATE는 버린 chain을 `RVOOS_UPDATE_DROP_POSTPONE`(143)으로 기록합니다. commit 후 postpone이 UPDATE의 MVCCID로 `RVOOS_NOTIFY_VACUUM`(140, MVCC undo record)을 남기며, 이를 위해 `log_append_mvcc_undo_data_with_mvccid`와 `prior_lsa_alloc_and_copy_crumbs`의 명시적 MVCCID 인자를 추가했습니다. vacuum은 그 MVCCID가 모든 snapshot보다 오래됐을 때 알림을 처리합니다. UPDATE는 heap data page를 잡은 채 heap header를 고정하지 않도록 HFID만 기록하고, OOS 파일은 vacuum이 찾습니다.
- **회수기**: `oos_delete`가 head stamp와 각 링크의 next-chunk stamp를 확인하며 연결된 prefix를 읽고, tail부터 head 순서로 redo-only `RVOOS_DELETE`(137, undo 없음)를 남깁니다. 중단 후 재실행은 남은 prefix를 끝내고, 재사용된 slot으로 이어진 링크는 따라가지 않습니다. chunk header는 32B(next-chunk identity stamp 추가)입니다.
- **오류 정책(fail-stop)**: commit된 의도의 회수가 실패하면 완료로 처리하지 않고 서버를 멈춥니다(`logpb_fatal_error`). 재시작 복구가 durable postpone을 다시 실행합니다. postpone 실행 중에는 interrupt 검사를 끕니다. vacuum의 알림 소비는 shutdown interrupt만 block을 미완료로 남기고, 그 밖의 오류는 fail-stop합니다.
- **제거**: forward-walk(`vacuum_forward_walk_reclaim_oos`)와 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`(relocation forward 삭제는 develop과 같은 `RVHF_DELETE`), LSA reclaim gate.
- **빈 페이지 fast path**: REMOVE의 sysop commit과 알림 소비가 비운 페이지를 `oos_reclaim_empty_pages`로 넘깁니다(heap page를 놓은 뒤). eager 회수가 비운 페이지는 growth-gate sweep이 반환합니다(ADR-0009).
- `log_do_postpone` 수정(별도 커밋): commit된 중첩 sysop 범위는 그 last parent(sysop 바로 앞 레코드)부터 시작하는데, 탐색 시작이 정확히 그 LSA이면 범위 안으로 보고 건너뛰었습니다. postpone cache가 넘친 commit과 재시작 복구에서, sysop 바로 앞에 기록된 postpone이 실행되지 않았습니다. bulk UPDATE의 첫 drop postpone 뒤에 OOS page 할당 sysop이 오면 알림이 빠져 chain 하나가 누수됐습니다(수정 전 3000행 release 실행 7회 중 5회, 수정 후 4회 모두 0). 같은 비교가 develop에도 있습니다.
- **vacuum block 정보**(별도 커밋 2개): 알림은 commit의 `logtb_complete_mvcc` 뒤에 기록되므로 그 MVCCID가 block의 oldest visible MVCCID보다 오래될 수 있습니다. 알림은 block의 oldest를 낮추지 않고(block 간 oldest 순서 유지), 알림만 든 block은 newest < oldest를 허용합니다. 재시작 복구가 남은 drop postpone을 다시 실행하며 남기는 알림은 log 연결과 block 플래그만 갱신하고, vacuum 부팅 때 `vacuum_recover_lost_block_data`가 log에서 block 정보를 다시 만듭니다(알림이 가장 최근 기록이면 마지막 vacuum data 항목의 oldest를 하한으로 사용). commit 시 회수는 lock_timeout 0인 트랜잭션에서도 page latch를 기다립니다(`pgbuf_force_latch_wait`).
- 형식 변경은 병합 전 변경이라 `DISK_STORAGE_FORMAT_REVISION`은 1로 둡니다(ADR-0008 decision 6). 이전 빌드로 만든 DB는 다시 만들어야 합니다.

## Remarks

- 검증: debug_gcc OOS ctest 52/52 통과(`2e32517bb`; 공용 장비 부하로 60초 제한에 걸린 `test_oos_identity_stamp`·`test_oos_server`는 단독 실행으로 각각 33/33·38/38 통과). `3e8072f56`의 gha-ci는 전부 통과했습니다.
  - 신규 `test_oos_reclaim`: redo-only라 바깥 abort가 재사용된 slot에 쓰지 않음(CBRD-27781 형태), 부분 회수 후 재실행 완료, 재사용 slot으로의 링크 미추적, abort된 의도 폐기, fail-stop.
  - 신규 real-vacuum 테스트: rollback·savepoint rollback된 UPDATE의 chain이 vacuum 뒤에도 남음(CBRD-27237), commit된 UPDATE의 빈 페이지 fast path 반환. 기존 old-snapshot 테스트도 A' 경로로 통과.
  - 신규 SQL crash 테스트: commit 회수 실패 → fail-stop → 재시작 복구 중 재실패 → 다음 재시작에서 회수 완료.
  - 신규 SERVER 모드 crash 테스트 `test_oos_server_crash_recovery`: UPDATE commit이 drop postpone 4개 중 2개 뒤에 멈춤 → 재시작 복구가 나머지를 다시 실행 → vacuum이 버린 chain만 회수. 신규 real-vacuum 테스트 2개: block oldest보다 오래된 알림이 block 순서를 지킴, 알림만 든 block이 만들어지고 처리됨. 세 테스트 모두 해당 수정 전 코드에서는 debug assert로 실패함을 확인했습니다.
  - 이전 의미(삭제 abort 복원, LSA gate 유예, DML 시점 eager 삭제)를 가정한 기존 테스트는 새 계약으로 고쳤습니다. 한 트랜잭션 안에서는 옛 chain과 새 chain이 commit까지 함께 남습니다.
- TLA+ conformance(`cubrid-verify-vacuum-slot-undo` 갱신본): OOS chunk undo 성질은 공허하게 통과(undo 가능한 chunk 삭제 없음), 신규 `OosReclaimDeletesOnlyItsChain`·`OosReclaimFinishesChain` 통과, 각 성질의 실패 변형 확인. 모델 범위 안의 결과이며 코드 전체의 증명은 아닙니다.
- 성능(ADR-0008 decision 7, release, 3000행·6 KB 값·UPDATE 3회, 3회 반복 중앙값): UPDATE churn 로그 114.8 → 66.2 MB(−42%), 버린 값 하나당 회수 로그 약 6.1 → 0.71 KB, DELETE drain 로그 16.5 → 2.8 MB, churn 뒤 OOS 페이지 3539 → 1502, DELETE 뒤 3539 → 1. INSERT·UPDATE 지연은 부하가 큰 공용 장비라 범위가 겹쳐 판단하지 못했습니다(재측정 필요). 방법과 한계: https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27781/perf.md
- 코드 리뷰(전문 리뷰어 5명, 소스 판독): 지적된 R1–R5·R9·R10은 이 PR에서 고쳤고, 남은 항목과 판단은 보고서에 있습니다: https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27781/code-review-pr8434-3e8072f/report.md
- 범위 밖: heap forward slot 보호(CBRD-27858)는 별도 수정입니다. CBRD-27925의 READ latch 힌트 소실은 남습니다. develop에도 있는 debug 전용 복구 analysis assert(`tran_start_postpone_lsa`)를 발견해 따로 기록했습니다: https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27781/recovery-analysis-assert.md
