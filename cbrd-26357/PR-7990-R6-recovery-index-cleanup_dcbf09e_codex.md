# PR 7990 R6 복구 인덱스 정리

미사용 예약 로그 항목을 develop에 고정하기 전에 제거한다. 이 문서는 R6 작성자와 리뷰어를 위한 변경·호환성·검증 기록이다. 기준 엔진의 실제 항목은 유지하며, 로그 번호가 바뀌므로 저장 형식 번호도 올린다. 분석일은 2026-10-30, Asia/Seoul이다.

## 기준과 근거

- 리뷰는 [hornetmj R6](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409612618)이다.
- 기준 소스는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`이다. 수정 source는 `eac70c7e740d55b4623b46bb84797e8214dcdcc4`, task branch는 `CBRD-27841-remove-unused-oos-recovery-index`이다. 초기 이름은 `review/pr7990-hornet-r6`이었다.
- 이슈는 [CBRD-27841](https://jira.cubrid.org/browse/CBRD-27841)이며 OOS M2의 Sub-task로 발급·재조회했다. Open, unassigned이고 CBRD-27230과 relates 관계다.
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
- [x] 수정 전 debug 빌드를 구성·설치하고 기존 동작을 확인한다.
- [x] 기존 형식 거부 테스트를 현재 값, 0, 이전 nonzero 값과 미래 값으로 확장한다.
- [x] 미사용 항목 제거와 형식 번호 변경을 적용한다.
- [x] 새 debug 빌드의 시작 검사, 집중 CTest와 실제 crash redo를 확인한다.
- [x] OOS 행의 commit·rollback·재시작 후 값과 `checkdb`를 확인한다.
- [x] 변경 범위, 검증 한계와 재현 가능한 명령을 검토한 뒤 커밋한다.
- [x] 별도 issue/PR 검토 자료를 준비한다.
- [x] 검토한 PR 본문과 게시 작업을 승인받고 별도 회사 draft PR을 만든다. PR 8347로 게시하고 전체 CI 한 번의 시작을 확인했다.
- [ ] 회사 CI 결과와 팀 리뷰를 받은 뒤 source PR을 반영한다.

## 수행한 검증

검증은 새 `debug_gcc` 설치와 독립 registry에서 진행했다. 기존 DB를 선택하지 않고 CTest fixture가 자기 DB를 생성·정리했다. workenv 초기화 후 CMake를 다시 구성하여 registry 경로가 테스트 구성에 반영되게 했다.

| 검사 | 결과 | 범위 |
| --- | --- | --- |
| 수정 전 집중 CTest | 10/10 통과 | fixture 6개, shell 검사 1개, GoogleTest 바이너리 3개 |
| 수정 후 같은 CTest | 10/10 통과 | 트랜잭션 8개, 재시작·crash redo 2개, TDE 분류 3개 |
| 현재·다른 형식 열기 | 현재 2는 성공, 0·1·3은 정상 거부 | csql, checkdb, emergency patch, 복원 후 열기, fixture 삭제 |
| 실제 빌드의 복구 테이블 | 시작 검사 진입과 140·141 항목 확인 | GDB에서 `rv_check_rvfuns`, `RV_fun[140]`, `RV_fun[141]` 관측 |
| 별도 `r6verify` DB | 결과 1·1·0·0 | 총 행 1개, commit한 30000바이트 값 1개, 삭제한 행 0개, rollback한 행 0개 |
| `checkdb -S` | exit 0 | 위 DB를 별도 프로세스로 다시 연 뒤 실행 |
| 정적·독립 검토 | 차단 결함 없음 | 전체 실제 항목 142개와 유지된 handler 행, endian 인코딩, fixture 소유·복원 확인 |

집중 CTest 선택식은 다음과 같다. 빌드·설치 및 빈 전용 registry 선택 후 실행한다.

```sh
ctest --test-dir "$CUBRID_BUILD_DIR" \
  -R '^(test_oos_storage_format_guard|test_oos_sql_crash_recovery|test_oos_tde_gate|test_oos_sql_txn)$' \
  --output-on-failure --verbose
```

별도 DB에서는 `VARCHAR(40000) STORAGE FORCE_OUTLINE` 열에 20000·22000자 값을 INSERT하고 commit했다. 첫 행을 30000자 값으로 바꾸고 두 번째 행을 삭제해 commit했다. 다음 프로세스에서 첫 행을 바꾸고 세 번째 행을 INSERT한 뒤 rollback했다. 다시 연 프로세스의 SELECT와 `checkdb -S`가 위 표의 결과를 확인했다. 검증 DB와 SQL·로그는 로컬 증거 디렉터리에 보존했다.

첫 GDB 시도는 command 인자에 SQL을 넘기는 인용 처리 때문에 올바른 DB를 열지 못했다. SQL 입력 파일과 debugger의 startup-shell 비활성화로 관측 방법을 고친 뒤 시작 검사와 실제 테이블을 확인했다. 이를 엔진 실패 또는 통과 증거로 섞지 않는다.

## 커밋과 검증 출처

1. `00dedf3fb`는 형식 거부 테스트를 먼저 확장한다. 엔진은 기준 revision 1과 같다. 이 상태에서 10/10 통과했다.
2. `eac70c7e7`는 미사용 항목과 분류를 제거하고 번호와 형식을 바꾼다. 원래 빌드한 commit `cac4d38e2`에서 test 주석 한 줄만 지운 amend이며, 네 엔진 파일은 완전히 같다. 최종 script로 수정 후 10/10을 실행했다.

주석 검토에서 기존 동작을 설명하던 test 주석 한 줄을 삭제했고, 저장된 형식 번호의 의미를 설명하는 revision 2 항목은 유지했다. correctness 검토에서는 차단 결함을 찾지 못했다.

## 검증 한계와 다음 단계

release, 별도 HA replica 재생, 변경된 두 번호를 실제 발생시키는 MVCC relocation 통합 실행은 하지 않았다. SA crash redo와 실제 빌드의 배열 검사를 이 경로들의 end-to-end 검증으로 표시하지 않는다. R5의 오류 경로도 이 작업의 실행 범위가 아니다.

[검토한 PR 본문](../cbrd-27841/CBRD-27841-recovery-index-cleanup-pr-body_eac70c7_codex.md) 그대로 [회사 draft PR 8347](https://github.com/CUBRID/cubrid/pull/8347)을 만들었다. source는 개인 fork의 승인한 commit에 push했고, 담당자·base·본문을 재조회했다. [전체 CI 41048233875](https://github.com/CUBRID/cubrid/actions/runs/41048233875)의 다섯 상태가 같은 실행으로 연결되는 것을 확인했다. CI 완료와 팀 리뷰는 대기 중이다. [게시 맥락](../cbrd-27841/CBRD-27841-recovery-index-cleanup-pr-context_eac70c7_codex.md)에 실제 작업 결과를 기록한다.
