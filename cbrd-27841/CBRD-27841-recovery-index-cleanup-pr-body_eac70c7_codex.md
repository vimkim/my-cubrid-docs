https://jira.cubrid.org/browse/CBRD-27841

## Purpose

- PR 7990의 [hornetmj 리뷰 R6](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409612618)에 따라 로그를 기록하는 코드가 없는 복구 항목을 제거합니다.

## Implementation

- `RVOOS_NOTIFY_VACUUM`의 enum, 빈 `RV_fun[]` 항목과 MVCC·logical-log 분류 조건을 제거했습니다.
- 뒤의 `RVREPL_DUMMY_OOS_RECORD`와 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`을 140·141로 정리했습니다. 기존 처리 함수는 유지합니다.
- 기존 개발 DB의 로그를 바뀐 번호로 읽지 않도록 `DISK_STORAGE_FORMAT_REVISION`을 1에서 2로 올렸습니다. 디스크 호환성 수준 11.5는 유지하며, 이전 개발 DB는 다시 만들어야 합니다.
- 형식 검사 테스트가 0, 이전 nonzero 형식과 미래 형식의 거부, 현재 형식 복원 후 열기와 fixture 정리를 확인하도록 확장했습니다.

## Remarks

- debug 빌드에서 수정 전후 집중 CTest가 각각 10/10 통과했습니다. fixture 6개, 형식 검사 shell 테스트 1개, GoogleTest 13개가 있는 바이너리 3개로 구성됩니다.
- 실제 빌드의 시작 검사와 140·141의 복구 함수 연결을 디버거로 확인했습니다. 별도 DB에서 OOS 값의 commit·rollback·재개방 후 결과와 `checkdb -S`가 정상입니다.
- release, 별도 HA replica 재생, 변경된 두 번호를 발생시키는 MVCC relocation 통합 실행은 이번 로컬 검증에 포함하지 않았습니다.
- CBRD-27230의 실제 commit 알림 기능은 별도 미구현 범위로 유지합니다.
