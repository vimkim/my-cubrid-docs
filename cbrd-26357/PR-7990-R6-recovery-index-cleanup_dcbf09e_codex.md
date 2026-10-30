# PR 7990 R6 복구 인덱스 정리

미사용 예약 로그 항목을 develop에 고정하기 전에 제거한다. R5와 다른 작업 브랜치에서 진행하며, 이 문서는 검토 결과와 실행한 검증을 구분한다.

## 기준과 근거

- 리뷰는 [hornetmj R6](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409612618)이다.
- 기준 소스는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`이다. source task branch는 `review/pr7990-hornet-r6`이다.
- authoritative OOS context는 2026-10-27 버전이며 SHA256은 `6300aa1fa6ffb54033b9c7f7ea959466e9d88f0530e1ab0d7178b4459d4fcf63`이다. ADR-0006은 호환되지 않는 미출시 형식 변경 때 저장 형식 번호를 올리도록 한다.
- 전체 source 검색에서 `RVOOS_NOTIFY_VACUUM`은 선언, 빈 `RV_fun` 항목, MVCC 분류, logical-log 분류와 관련 주석에만 있다. 로그 생산자는 없다.

## 결정

| 대상 | 변경 | 이유 |
| --- | --- | --- |
| `RVOOS_NOTIFY_VACUUM` | enum, 빈 함수 테이블 항목과 두 분류 조건 제거 | 실행할 로그가 없는 예약 항목이다. |
| `RVREPL_DUMMY_OOS_RECORD` | 141에서 140으로 이동 | 배열 위치와 복구 번호를 일치시킨다. |
| `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` | 142에서 141로 이동 | 마지막 실제 항목으로 유지한다. |
| `RV_LAST_LOGID` | 마지막 실제 항목의 alias 유지 | 별도 숫자 중복을 추가하지 않는다. |
| `DISK_STORAGE_FORMAT_REVISION` | 1에서 2로 변경 | 기존 141·142 로그를 새로운 의미나 배열 범위로 잘못 읽기 전에 거부한다. |

디스크 호환성 수준 11.5는 유지한다. 새 번호를 사용하는 검증 DB는 새로 만든다. 저장 형식 검사는 로컬 DB를 여는 경계에서 수행하므로, 이 변경으로 서로 다른 빌드 간 HA 로그 호환성을 입증했다고 표시하지 않는다.

명세의 CBRD-27230은 실제 commit-conditional OOS 알림을 요구하지만 현재 예약 항목은 그 구현이 아니다. 이번 제거로 해당 구현 공백을 완료 또는 취소한 것으로 표시하지 않는다.

## 검증 체크리스트

- [x] 리뷰, source inventory, positional `RV_fun` 계약과 호환성 정책을 확인한다.
- [ ] 수정 전 debug 빌드를 구성·설치하고 기존 동작을 확인한다.
- [ ] 기존 형식 거부 테스트를 현재 값, 0, 이전 nonzero 값과 미래 값으로 확장한다.
- [ ] 미사용 항목 제거와 형식 번호 변경을 적용한다.
- [ ] 새 debug 빌드의 시작 검사, 집중 CTest와 실제 crash redo를 확인한다.
- [ ] OOS 행의 commit·rollback·재시작 후 값과 `checkdb`를 확인한다.
- [ ] 변경 범위, 검증 한계와 재현 가능한 명령을 검토한 뒤 커밋한다.
- [ ] 별도 issue/PR 검토 자료를 준비한다. 게시와 source merge는 해당 승인 절차를 따른다.

아직 수정 후 실행 결과는 없다. 리뷰어의 실행 결과를 이 작업의 검증으로 세지 않는다.
