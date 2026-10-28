https://jira.cubrid.org/browse/CBRD-26659

## Purpose

- 큰 값을 행 밖에 저장하는 OOS(Out-of-row Overflow Storage)의 SQL 회귀 검증을 보완합니다.
- AS-IS: 기존 SQL 사례만으로는 OOS의 값·오류·트랜잭션 결과와 알려진 실패를 함께 관리하기 어렵습니다.
- TO-BE: 독립적인 기대값으로 결과를 비교하고, 일반 CI의 대표 사례와 비활성 실패를 구분합니다.

## Implementation

- SQL/answer 28쌍 중 `sql/_36_guava/cbrd_26659/`의 25쌍을 실행하고 실패 3쌍은 `disabled/failing/sql/`에 보존합니다.
- 저장 정책 문법·오류, 읽기·복사·집합 연산, DML·제약·트리거·트랜잭션, 스키마·파티션·LOB·큰 키·저장 경계를 검증합니다.
- 입력·행·트랜잭션 모델에서 기대값을 정합니다. 비활성화할 때 SQL 본문과 answer를 바꾸지 않았습니다.
- 비활성 사례와 복원 방법은 [실행 선택 목록](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/disabled/README.md)에 기록했습니다.

## Remarks

- TC `45e21ad`·Engine `e3589ae`의 [전체 CI 40643373124](https://github.com/CUBRID/cubrid/actions/runs/40643373124)에서 build·medium·SQL·shell 상태가 모두 SUCCESS입니다. 전체는 **57분 00초**입니다.
- PR #7990 본문의 [추가 TC 전 전체 성공 CI](https://github.com/CUBRID/cubrid/actions/runs/40349442612)와 비교하면 **전체 47분 14초→57분 00초(+9분 46초)**, **test_sql 15분 04초→17분 24초(+2분 20초)**입니다. SQL 계획 수는 17,630→17,655개(+25)이며 shard 수는 10개로 같습니다.
- Suite 시간은 병렬 shard의 첫 시작부터 마지막 종료까지입니다. 리비전·실행 환경·시작 지연도 달라, 위 차이를 이 SQL 25개의 순수 추가 비용으로 단정하지 않습니다.
- **QA 검토:** 결함 검출 가치와 중복 검사를 확인해 일반 CI에 유지할 대표 SQL을 선별·통합합니다. SQL은 논리 결과를 검증하며 실제 저장 상태·파일 소유권은 연결된 shell TC에서 확인합니다.
- **비활성 실패 3쌍:** 원인 규명과 수정 후 원래 기대값으로 PASS를 확인하고 정규 실행에 복원해야 합니다. 비활성 실패는 통과 커버리지에 포함하지 않습니다.
- 기록된 OOS SQL 중 개별 1분 초과 사례는 없습니다. 연결된 shell의 유용한 장시간 사례는 QA와 `shell-heavy` 등 별도 suite 편입을 협의합니다. 선별·이전·실패 수정은 후속 작업입니다.
- 활성 선택의 CI 성공이 비활성 사례나 요구사항 전체의 독립 검증 완료를 뜻하지는 않습니다. 성능 비교는 별도 후속 작업입니다.
- 연결: [Engine PR #8128](https://github.com/CUBRID/cubrid/pull/8128), [Shell TC PR #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365).
