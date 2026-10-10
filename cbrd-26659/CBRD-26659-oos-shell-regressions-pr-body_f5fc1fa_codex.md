https://jira.cubrid.org/browse/CBRD-26659

## Purpose

- 큰 값을 행 밖에 저장하는 OOS(Out-of-row Overflow Storage)의 물리 상태와 자원 수명을 shell 회귀로 검증합니다.
- AS-IS: 논리 결과만으로는 실제 OOS 파일 소유권, 크래시 복구 및 정리 결과를 확인하기 어렵습니다.
- TO-BE: 긍정적인 파일/청크 관찰과 독립적인 값 모델을 함께 확인하고, 실패·미검증 범위를 따로 남깁니다.

## Implementation

- `shell/_40_guava/`에 18개 testcase 진입점과 관찰·생명주기·복구·스냅샷·utility 보조 코드를 추가합니다.
- 소유 파일 DROP, 표현/DML/트랜잭션/읽기/스키마/LOB, 실제 SIGKILL 후 commit 복구와 미완료 트랜잭션 undo를 검증합니다.
- 실제 세션 스냅샷, utility/backup round trip 및 lazy TDE 파일 소유권과 OOS WAL 분류를 확인합니다.
- 다섯 진입점은 공통 `oos_common/oos_lifecycle.sh`를 사용합니다. 기존 등록·경로를 거부하고, 생성 시도·디렉터리 inode·등록 경로가 일치할 때만 정리합니다. 명령과 종료 대기는 제한 시간을 갖습니다.

## Remarks

- 2026-10-08 로컬 native `cubrid-testkit`: 선별 shell 14/14 통과, 실패/skip 0, 전체 316.41초. Engine `fb567a6`, OptDebug, 16 KiB와 각 case의 SA/CS 설정을 기록했습니다.
- 검증된 testcase 리비전은 `f5fc1fa815fbc6eec71135f506e377c0b1096da3`입니다. 336개 assertion, 941개 필수 artifact, 독립적인 원시 결과 재검증 및 소유 자원/설정 정리 gate가 통과했습니다.
- 소유권 제어 105/105와 실제 timeout/KILL/reap 제어 5/5도 통과했습니다. stub 제어에는 native DB 검증 실적을 부여하지 않습니다.
- 나머지 4개(`partition_owner`, `snapshots_reclaim`, `cbrd_27237_rollback_vacuum`, `utility_sa_physical`)는 실패 또는 검증 미완료 재현용이며 선별 통과 집합에서 제외했습니다. 전체 발견 집합이나 회사 CI의 통과를 주장하지 않습니다.
- 페이지 반환/반복 churn, rollback-vacuum 시도에서 누락된 실행 코드 식별, 기존 파일 NONE→AES 적용, ciphertext 및 HA/내부 제어는 실패·부분·미검증 상태를 유지합니다. 기존 CDC 기대값과 활성 상태는 변경하지 않습니다.
- SQL companion은 실제 SQL 실행의 물리 상태를 관찰한 증거가 아닙니다. 각 shell fixture의 증거 범위만 인정하며, 생명주기 helper는 직렬화된 격리 실행을 전제로 합니다.
