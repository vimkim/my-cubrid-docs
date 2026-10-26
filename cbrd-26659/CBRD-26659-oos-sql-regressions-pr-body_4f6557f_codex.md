https://jira.cubrid.org/browse/CBRD-26659

## Purpose

- 큰 값을 행 밖에 저장하는 OOS(Out-of-row Overflow Storage)의 SQL 회귀 검증을 보완합니다.
- AS-IS: 기존 SQL 사례만으로는 OOS 기능별 정상 결과와 알려진 실패 재현을 함께 관리하기 어렵습니다.
- TO-BE: 독립적인 기대값으로 논리 결과를 비교하고, 활성 사례와 비활성 실패 사례를 명시합니다.

## Implementation

- SQL/answer 28쌍을 제공합니다. `sql/_36_guava/cbrd_26659/`의 25쌍을 실행하고, 실패한 3쌍을 `disabled/failing/sql/`에 보존합니다.
- 저장 정책 문법·오류, 전체 값의 읽기·복사·집합 연산, 기본 DML과 MERGE/REPLACE/중복 키 UPDATE를 검증합니다.
- 제약조건·트리거·트랜잭션, 스키마·파티션, 외부 LOB, 큰 PK/UNIQUE·FK 및 저장 경계를 포함합니다.
- 입력·행·트랜잭션 모델에서 기대값을 정합니다. 비활성화 과정에서 SQL 본문과 answer 내용은 바꾸지 않았습니다.
- 비활성 사례와 복원 방법은 [실행 선택 목록](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/disabled/README.md)에 기록합니다. `.sql.disabled` 파일은 정규 SQL 발견 대상에서 제외됩니다.

## Remarks

- 현재 TC head는 `4f6557f`, 검증 Engine은 `c4c4f5c5`입니다.
- [CI 40324320840](https://github.com/CUBRID/cubrid/actions/runs/40324320840)에서 SQL·medium 상태는 PASS입니다. 이 run 전체는 별도 shell 실패 2건으로 FAIL입니다.
- SQL 결과는 값·오류·트랜잭션의 논리 검증입니다. 실제 저장 레코드의 OOS 사용 플래그인 `HAS_OOS`와 파일 소유권은 각 shell fixture의 증거 범위에서 확인합니다.
- 비활성 실패는 FAIL로 유지하며 통과 커버리지로 계산하지 않습니다. 전체 Work456의 필수 항목별 독립 검증은 아직 완료되지 않았습니다.
- 성능 비교와 HA(Work463)는 계속 보류합니다.
- 연결: [Engine PR #8128](https://github.com/CUBRID/cubrid/pull/8128), [Shell TC PR #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365).
