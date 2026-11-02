https://jira.cubrid.org/browse/CBRD-27841

## Purpose

- PR 7990의 [hornetmj 리뷰 R6](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409612618)에 따라 로그를 기록하는 코드가 없는 복구 항목을 제거합니다.

## Implementation

- `RVOOS_NOTIFY_VACUUM`의 enum, 빈 `RV_fun[]` 항목과 MVCC·logical-log 분류 조건을 제거했습니다.
- 뒤의 `RVREPL_DUMMY_OOS_RECORD`와 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`을 140·141로 정리했습니다. 기존 처리 함수는 유지합니다.
- 진행 중인 미출시 OOS 개발 변경으로 다루어 `DISK_STORAGE_FORMAT_REVISION`은 기존 값 1을 유지합니다. 디스크 호환성 수준도 11.5를 유지합니다.
- 형식 검사 테스트는 DB에 기록된 현재 revision을 읽습니다. 현재 값 1에서는 0·2의 거부, 현재 형식 복원 후 열기와 fixture 정리를 확인합니다.

## Remarks

- 인덱스 정리 당시 debug 빌드의 수정 전후 집중 CTest가 각각 10/10 통과했습니다. revision 1을 복원한 이번 변경은 debug 빌드·설치와 형식 검사 CTest 3/3을 다시 확인했습니다.
- 앞선 인덱스 정리 검증에서 시작 검사와 140·141의 복구 함수 연결을 디버거로 확인했습니다. 별도 DB에서 OOS 값의 commit·rollback·재개방 후 결과와 `checkdb -S`를 확인했습니다.
- 번호 변경 전 개발 DB·로그의 재사용 호환성은 보장하지 않습니다. 이번 변경은 이를 revision 값으로 구분하지 않습니다.
- release, 별도 HA replica 재생, 변경된 두 번호를 발생시키는 MVCC relocation 통합 실행은 로컬 검증에 포함하지 않았습니다. 새 head의 전체 CI 결과는 확인 대기입니다.
- CBRD-27230의 실제 commit 알림 기능은 별도 미구현 범위로 유지합니다.
