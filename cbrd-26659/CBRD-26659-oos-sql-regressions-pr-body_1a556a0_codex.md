https://jira.cubrid.org/browse/CBRD-26659

## Purpose

- 큰 값을 행 밖에 저장하는 OOS(Out-of-row Overflow Storage)의 SQL 회귀 검증을 추가합니다.
- AS-IS: 현재 브랜치에는 이번에 검토한 값 복사, 경계값, DML 및 읽기 경로 검증 집합이 없습니다.
- TO-BE: 입력값에서 미리 계산한 기대값으로 논리 결과를 비교하고, 알려진 실패 재현은 별도로 구분합니다.

## Implementation

- `sql/_36_guava/cbrd_26659/`에 SQL/answer 17쌍을 추가합니다.
- 표현 경계, 여러 속성, 값 복사, UPDATE/DELETE, 트랜잭션, 제약조건, 트리거 및 읽기 경로를 검증합니다.
- 스키마/저장 정책, 파티션 라우팅 및 외부 LOB 복사도 포함합니다. 전체 값과 독립적으로 계산한 해시를 비교합니다.
- 실제 출력으로 기대값을 만들지 않고, 사전에 검토한 입력·행·트랜잭션 모델을 사용합니다.
- Bot 초기화 커밋을 유지하고 기존 testcase 통합 브랜치를 `tc/pr-8128`에 합쳤습니다.

## Remarks

- 2026-10-08 로컬 native `cubrid-testkit`: 선별 SQL 16/16 통과, 실패/skip 0, 전체 88.52초. Engine `fb567a6`, OptDebug, JDBC, 16 KiB 설정에서 확인했습니다.
- Native 검증 리비전은 `c94961578dc43bfe05a74591d52dff30d44a43d3`입니다. 16개 실제 결과가 검토한 answer와 바이트 단위로 일치합니다. 준비·빌드·검증 비용은 실행 시간과 별도로 기록했습니다.
- 이 PR의 준비된 head는 `1a556a0752073aaad573bf87d53f3eb75f398138`이며 전체 Git tree가 위 원본과 같습니다. 검증 대상 32개 입력의 파일/커밋 해시도 일치합니다. 새 head에서 native 실행을 반복하거나 회사 CI를 실행한 결과는 아닙니다.
- 17개 중 `cbrd_26659_oos_partition.sql`은 알려진 파티션 이동 실패 재현용이며 위 통과 집합에 포함되지 않습니다. 전체 발견 집합의 통과를 주장하지 않습니다.
- SQL 결과는 논리 검증입니다. 실제 OOS 파일/청크 관찰은 별도 private shell PR의 해당 fixture만 검증합니다. HA와 내부 제어 경로의 미검증 범위는 유지합니다.
- 연결된 engine PR: [CUBRID/cubrid#8128](https://github.com/CUBRID/cubrid/pull/8128).
