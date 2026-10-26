https://jira.cubrid.org/browse/CBRD-26659

## Purpose

- 큰 값을 행 밖에 저장하는 OOS(Out-of-row Overflow Storage)의 저장 상태와 자원 수명을 shell 회귀로 검증합니다.
- AS-IS: 논리 결과만으로는 저장 레코드의 상태, 파일 소유권, 복구와 정리 결과를 확인하기 어렵습니다.
- TO-BE: 전체 값 모델과 물리 관찰을 함께 확인하고, 실패·장시간 사례를 별도로 보존합니다.

## Implementation

- [전체 133개 OOS 진입점 목록](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/oos-pr8128-inventory.tsv)을 제공합니다. 현재 69개를 실행하고 64개를 비활성화합니다. 다른 티켓 ID의 `cbrd_27237_rollback_vacuum`도 포함합니다.
- 저장 레코드의 OOS 사용 플래그인 `HAS_OOS`의 설정·해제, 전체 값, 파일·청크 소유권을 관찰하는 공통 helper를 추가합니다.
- 읽기·DML·제약·트리거·트랜잭션, 스키마·파티션·LOB·큰 키를 독립적인 값 모델과 연결합니다.
- JDBC 저장 정책과 복구·스냅샷·회수·유틸리티, TDE(투명 데이터 암호화)의 파일·로그 관찰을 포함합니다.
- 공통 helper로 사례별 DB·등록 정보·파일·프로세스의 소유권, 명령 제한 시간과 정리 결과를 확인합니다.
- `oos_native/`의 C++17 helper와 Bash/jq를 사용합니다. OOS 사례 실행에 Python helper를 요구하지 않습니다.
- [비활성 목록](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/README.md)은 관측 FAIL 61개와 60초 초과 8개를 포함합니다. 중복 5개를 제외한 64개를 `disabled/failing/`과 `disabled/long_running/`에 보존하고 `.sh.disabled` 접미사를 붙입니다. 각 기록에 CI run·TC revision·원본 해시를 남깁니다.

## Remarks

- 현재 TC head는 `8486abd`, 검증 Engine은 `c4c4f5c5`입니다.
- [Shell-only CI 40335925801](https://github.com/CUBRID/cubrid/actions/runs/40335925801)은 PASS입니다. 전체 shell 집계는 3,523 PASS / 0 FAIL / 30 SKIP이며 실행 누락은 없습니다.
- 활성 OOS 69개는 모두 PASS이며 실패·skip은 없습니다. 비활성 64개는 실행 대상에서 제외됐습니다. 이 run에서 활성 OOS의 최대 시간은 45.180초입니다.
- 비활성화 과정에서 본문·assertion·기대값을 바꾸지 않았습니다. 비활성 FAIL을 통과 커버리지로 계산하지 않으며 전체 Work456의 필수 항목별 독립 검증은 아직 완료되지 않았습니다.
- 성능 비교와 HA(Work463)는 계속 보류합니다.
- 연결: [Engine PR #8128](https://github.com/CUBRID/cubrid/pull/8128), [SQL TC PR #3688](https://github.com/CUBRID/cubrid-testcases/pull/3688).
