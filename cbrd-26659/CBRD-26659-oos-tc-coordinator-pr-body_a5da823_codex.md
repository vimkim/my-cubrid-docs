https://jira.cubrid.org/browse/CBRD-26659

## Purpose

- OOS(Out-of-row Overflow Storage, 큰 값을 행 밖에 저장하는 방식)의 SQL/shell 회귀 testcase를 리뷰할 PR을 준비합니다.
- AS-IS: 로컬 testcase 통합 브랜치에는 이번 작업용 `tc/pr-N` 브랜치와 연결된 engine PR이 없습니다.
- TO-BE: `feature/oos-merge`를 대상으로 하는 이 PR의 번호로 public/private testcase PR을 연결합니다.

## Implementation

- `feature/oos-merge`의 `fb567a629cdb390fff920542173fa36f454c74a0`에서 빈 커밋 하나를 추가했습니다. Engine 파일 변경은 없습니다.
- TC Branch Sync가 두 testcase 저장소에 `tc/pr-N` 브랜치와 draft PR을 만들면, 준비한 testcase 변경을 해당 브랜치에 통합하고 동료 리뷰를 받습니다.
- SQL 원본은 `c94961578dc43bfe05a74591d52dff30d44a43d3`, shell 원본은 `f5fc1fa815fbc6eec71135f506e377c0b1096da3`입니다.

## Remarks

- 2026-10-08 native `cubrid-testkit`, OptDebug, 16 KiB 설정에서 선별 SQL 16/16(88.52초), shell 14/14(316.41초)가 통과했습니다. 실행 시간은 suite별로 측정했습니다.
- 위 결과는 기존 engine `fb567a6`와 각 testcase 원본 리비전의 로컬 검증입니다. 새 PR head의 빌드나 회사 CI 결과는 아직 없습니다.
- 전체 변경에는 위 통과 집합 밖의 SQL 1개와 shell 4개 실패·검증 미완료 재현용 testcase도 포함됩니다. 전체 CI 실행 전에 처리 범위를 정해야 합니다.
- 실제 기대값, artifact 판정과 소유 자원 정리 증거는 각 testcase PR에서 설명합니다. Engine 수정, JIRA 게시 및 testcase PR merge는 이 작업에 포함하지 않습니다.
