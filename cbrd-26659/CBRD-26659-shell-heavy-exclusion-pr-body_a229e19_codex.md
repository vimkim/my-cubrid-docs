https://jira.cubrid.org/browse/CBRD-26659

## Purpose

- 큰 값을 행 밖에 저장하는 OOS(Out-of-row Overflow Storage)의 저장 상태, 복구·정리와 HA 복제를 shell 회귀로 검증합니다.
- AS-IS: SQL 결과만으로는 실제 저장 상태, 파일 소유권, 복구·복제 결과를 충분히 확인하기 어렵습니다.
- TO-BE: 전체 값과 저장 상태를 함께 확인하고, 일반 CI의 대표 TC와 실패·장시간 사례를 구분해 관리합니다.

## Implementation

- 현재 139개 OOS 진입점은 일반 CI 활성 31개, heavy 분류로 제외한 38개, 기존 비활성 66개, HA 분류로 제외한 4개입니다.
- PASS한 20초 초과 비HA 38개를 `disabled/heavy`로 옮기고 원본 경로·hash·mode·관측 근거를 남겼습니다. 별도 `shell_heavy` PR에 같은 TC와 공용 의존 파일을 전달합니다.
- OOS 사용 플래그 `HAS_OOS`, 전체 값, 파일·청크 소유권과 읽기·DML·제약·트랜잭션·스키마·LOB·큰 키를 확인합니다. JDBC, 복구·스냅샷·회수·유틸리티·암호화 검사도 포함합니다.
- HA 활성 4개·비활성 재현 2개는 전용 [draft PR #1666](https://github.com/CUBRID/cubrid-testcases-private/pull/1666)으로 분리했습니다. 재현 2개는 기존 위치에도 보존합니다.
- 기존 비활성 66개는 과거 FAIL 61개, 60초 초과 PASS 3개, HA 엔진 결함 재현 2개입니다. 기대값·assertion과 과거 133개 inventory는 유지했습니다.
- C++17·Bash/jq helper와 기존 fixture를 보존하여 남은 일반 TC와 비활성 재현의 상대 경로를 유지합니다. OOS 실행용 Python helper는 요구하지 않습니다.

## Remarks

- 제외 전 [전체 CI 40692318846](https://github.com/CUBRID/cubrid/actions/runs/40692318846)은 Engine `e3589ae`·private TC `02d0239`의 결과입니다. Build·SQL·medium은 성공했고, shell은 기존 `temp_enc_06` 1건 실패로 전체 FAILURE입니다.
- 이번 일반 31개 선택의 전체 CI는 게시 후 1회 실행합니다. 이전 CI 결과를 이번 제외 커밋의 PASS로 간주하지 않습니다.
- 이관한 heavy의 native 전체 실행은 **38 PASS·0 FAIL·0 SKIP**입니다. TC당 120초 제한으로 직렬 실행했고 모두 제한 안에 끝났습니다.
- QA 검토에서 일반·heavy의 대표 TC와 실행 주기를 정합니다. 실패 원인 분석·장시간 TC 분할·기존 비활성 PASS 3개 처리는 별도 후속 작업입니다.
- 연결한 [Engine PR #8128](https://github.com/CUBRID/cubrid/pull/8128)과 [SQL PR #3688](https://github.com/CUBRID/cubrid-testcases/pull/3688)은 별도로 유지합니다.
