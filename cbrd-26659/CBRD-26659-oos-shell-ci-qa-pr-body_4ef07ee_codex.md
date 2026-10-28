https://jira.cubrid.org/browse/CBRD-26659

## Purpose

- 큰 값을 행 밖에 저장하는 OOS(Out-of-row Overflow Storage)의 저장 상태, 복구·정리와 HA 복제를 shell 회귀로 검증합니다.
- AS-IS: SQL 결과만으로는 실제 저장 상태, 파일 소유권, 복구·복제 결과를 충분히 확인하기 어렵습니다.
- TO-BE: 전체 값과 저장 상태를 함께 확인하고, 일반 CI의 대표 TC와 실패·장시간 사례를 구분해 관리합니다.

## Implementation

- 기존 [133개 OOS 목록](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/4ef07ee34219a7dce7e5c5d84a2f6c6031b10ec3/disabled/oos-pr8128-inventory.tsv)은 활성 69개·비활성 64개입니다. 이후 HA 활성 4개·비활성 결함 재현 2개를 더해 현재 총 **139개: 활성 73개·비활성 66개**입니다.
- OOS 사용 플래그 `HAS_OOS`, 전체 값, 파일·청크 소유권과 읽기·DML·제약·트랜잭션·스키마·LOB·큰 키를 확인합니다. JDBC, 복구·스냅샷·회수·유틸리티·암호화 검사도 포함합니다.
- HA 정상 복제, 장애 전환·복귀와 많은 OOS 값의 sync/async 복제를 추가했습니다. HA 엔진 결함 [CBRD-27800](https://jira.cubrid.org/browse/CBRD-27800)·[CBRD-27801](https://jira.cubrid.org/browse/CBRD-27801)의 재현 2개는 처음부터 비활성입니다.
- C++17·Bash/jq helper로 사례별 DB·파일·프로세스의 소유권과 정리를 확인합니다. OOS 실행용 Python helper는 요구하지 않습니다.
- 기존 비활성 64개는 관측 FAIL 61개와 개별 60초 초과 8개 중 중복 5개를 제외한 수입니다. 원본 기대값·assertion을 유지해 `disabled/failing/`·`disabled/long_running/`에 보존했습니다. [비활성 목록과 HA 추가 기록](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/4ef07ee34219a7dce7e5c5d84a2f6c6031b10ec3/disabled/README.md)을 참조합니다.

## Remarks

- [전체 CI 40643373124](https://github.com/CUBRID/cubrid/actions/runs/40643373124)는 Engine `e3589ae`·private TC `479035a`에서 build·medium·SQL·shell 모두 SUCCESS입니다. 최신 `4ef07ee`는 이후 HA helper 설명 주석만 수정했으며, 그 HEAD에서 새 CI를 수행한 결과는 아닙니다.
- PR #7990 본문의 [추가 TC 전 전체 성공 CI](https://github.com/CUBRID/cubrid/actions/runs/40349442612)와 비교하면 **전체 47분 14초→57분 00초(+9분 46초)**, **test_shell 38분 10초→50분 37초(+12분 27초)**입니다. Shell 계획 수는 3,490→3,563개(+73), shard 수는 50개로 같습니다.
- Suite 시간은 병렬 shard의 첫 시작부터 마지막 종료까지입니다. 이번 shell shard의 시작은 약 15분에 걸쳐 분산됐고 누적 수행 시간 증가는 약 3.1%입니다. 57분을 머지 후 고정 비용으로 단정하지 않습니다.
- **QA 검토:** 값 손상·복구·소유권 등 핵심 회귀를 잡는 TC를 우선합니다. 활성 TC도 중복 검사와 수행 비용을 검토해 일반 CI에 유지할 사례를 선별·통합할 필요가 있습니다.
- **비활성 실패:** Engine·TC·환경 중 원인을 규명하고 수정한 뒤, 올바른 기대값으로 PASS와 자원 정리를 확인해 재활성화합니다. 비활성화는 결함 해결이나 PASS가 아닙니다.
- **개별 1분 초과:** 유용한 사례는 QA와 `shell-heavy` 등 장시간 suite의 위치·주기·실행 조건을 협의해 이전합니다. 실패도 겹치는 5개는 원인 수정과 PASS 확인을 먼저 합니다. 장시간 TC 이전은 아직 수행하지 않았습니다.
- 활성 선택의 CI 성공이 비활성 사례나 요구사항 전체의 독립 검증 완료를 뜻하지는 않습니다. 성능 비교는 별도 후속 작업입니다.
- 연결: [Engine PR #8128](https://github.com/CUBRID/cubrid/pull/8128), [SQL TC PR #3688](https://github.com/CUBRID/cubrid-testcases/pull/3688).
