https://jira.cubrid.org/browse/CBRD-27841

## Purpose

- 복구 로그는 처리 함수를 숫자(recovery index)로 저장합니다. `feature/oos-merge`가 develop에 병합되면 이 번호가 로그 형식으로 굳습니다.
- #7990 리뷰 [r4409612618](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409612618)은 로그를 기록하는 코드가 없는 복구 인덱스를 병합 전에 지워 달라고 요청했습니다.
- AS-IS: `RVREPL_OOS_DELETE`(140)는 enum, `RV_fun[]`의 덤프 전용 항목, TDE 분류 한 줄에만 있습니다. 이 번호로 로그를 쓰는 코드와 log applier의 처리 코드가 없습니다.
- TO-BE: 이 인덱스를 지우고, 뒤의 OOS 인덱스를 하나씩 당깁니다.

## Implementation

- `src/transaction/recovery.h`, `src/transaction/recovery.c`, `src/storage/tde.h`에서 `RVREPL_OOS_DELETE`를 지웁니다.
- `RV_fun[]`은 번호를 배열 위치로 쓰므로 뒤 번호를 당깁니다.
  - `RVOOS_NOTIFY_VACUUM` 141 → 140, `RVREPL_DUMMY_OOS_RECORD` 142 → 141
  - `RVOOS_RECLAIM_POSTPONE` 143 → 142, `RVOOS_UPDATE_DROP_POSTPONE`(`RV_LAST_LOGID`) 144 → 143
- 139 이하와 develop의 번호는 그대로입니다. 다른 코드는 모두 이름으로 비교하므로 더 바꿀 곳이 없습니다.
- `RVOOS_NOTIFY_VACUUM`은 유지합니다. #8434부터 UPDATE commit의 postpone이 이 번호로 로그를 쓰고, vacuum이 소비합니다([r4613840763](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4613840763)).

## Remarks

- 호환성: 이전 `feature/oos-merge` 빌드로 만든 DB는 다시 만들어야 합니다. ADR-0008 결정대로 `DISK_STORAGE_FORMAT_REVISION`은 1로 둡니다.
- 검증(debug 빌드). 순서 검사와 CTest는 이 PR의 head에서, 강제 종료 검사는 rebase 전의 같은 패치(base `71993ddb63`)에서 했습니다.
  - 설치한 `libcubrid.so`와 `libcubridsa.so`에서 `RV_fun[]` 144개 항목이 모두 `recv_index == i`이고, 항목 수가 `RV_LAST_LOGID + 1`입니다.
  - 설정한 CTest: 66/66 통과.
  - OOS UPDATE·DELETE를 커밋하고 다른 UPDATE·INSERT는 커밋하지 않은 채 서버를 `kill -9`로 종료한 뒤 재시작했습니다. 데이터가 커밋 상태와 같았습니다. vacuum이 재시작 뒤 `RVOOS_NOTIFY_VACUUM` 200개를 소비해 UPDATE의 옛 OOS chain 400개를 회수했고, DELETE의 chain도 모두 회수했습니다. `checkdb`도 통과했습니다.
  - HA 복제 smoke test는 하지 않았습니다. `RVREPL_OOS_INSERT`(139)는 번호가 그대로이고, `RVREPL_DUMMY_OOS_RECORD`는 복제 코드가 이름으로만 처리합니다.
- 테스트케이스 변경은 없습니다. 두 TC 저장소에 이 번호를 숫자로 쓰는 기대값이 없습니다.
- #8559(CBRD-27230)는 `RVREPL_OOS_REUSE = 145`를 더합니다. 이 PR 뒤에는 144로 바꾸고, `RV_LAST_LOGID` 줄과 `tde.h` 마지막 줄의 rebase 충돌을 풀어야 합니다.
- 이전 시도 #8347은 당시 쓰이지 않던 `RVOOS_NOTIFY_VACUUM`을 지웠고, 병합 없이 닫혔습니다.
- 검증 절차와 결과: [verification.md](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27841/verification.md)
