https://jira.cubrid.org/browse/CBRD-26659

## Purpose

- OOS(Out-of-row Overflow Storage, 큰 값을 행 밖에 저장하는 방식)의 SQL·shell 회귀 검증을 보완합니다.
- AS-IS: 논리 결과만으로는 실제 저장 상태, 값의 소유권, 장애 후 복구를 충분히 확인하기 어렵습니다.
- TO-BE: 대표 동작과 저장 상태를 함께 검증하고, 일반 CI에 유지할 사례를 QA와 선별합니다.

## Implementation

- Public [TC PR #3688](https://github.com/CUBRID/cubrid-testcases/pull/3688)에 SQL/answer 28쌍을 제공합니다. 25쌍이 활성이고 실패 3쌍은 비활성 상태로 보존합니다.
- Private [TC PR #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365)의 일반 CI 대상은 OOS shell 69개입니다. 실패·장시간 비활성 66개와 HA 분류로 제외한 4개는 기록과 함께 보존합니다.
- 실제 HA 복제·장애 전환·sync/async TC는 전용 저장소의 [draft PR #1666](https://github.com/CUBRID/cubrid-testcases-private/pull/1666)으로 분리했습니다(활성 4개·결함 재현 비활성 2개).
- Engine에는 저장 경계, 읽기·버퍼 수명, 소유권·회수·복구를 확인하는 C++ 단위 테스트와 테스트 전용 진입점을 보완했습니다.

## Remarks

- 신규 TC 추가 전 [#7990 전체 CI 40738391553](https://github.com/CUBRID/cubrid/actions/runs/40738391553)는 **44분 10초**였습니다. Engine `dcbf09e`, public TC `70db22a`, private TC `75a0202`의 결과입니다.
- 추가 후·HA 제외 [#8128 전체 CI 40692318846](https://github.com/CUBRID/cubrid/actions/runs/40692318846)는 **42분 28초**였습니다. Engine `e3589ae`, public TC `45e21ad`, private TC `02d0239`의 결과입니다.

| 항목 | 추가 TC 전 | 추가 TC 포함·HA 제외 | 차이 |
| --- | ---: | ---: | ---: |
| 전체 경과 | 44분 10초 | 42분 28초 | −1분 42초 |
| test_medium | 3분 04초 | 3분 17초 | +13초 |
| test_sql | 14분 03초 | 13분 41초 | −22초 |
| test_shell | 40분 56초 | 39분 36초 | −1분 20초 |

- 두 실행 모두 **FAILURE**입니다. Build·SQL·medium은 성공했고, shell에서 각각 `parameter_combine`(#7990), `temp_enc_06`(#8128) 1건이 실패했습니다. 계획한 TC의 미실행 누락은 없고 양쪽 shell SKIP은 30개입니다.
- 계획 수는 shell 3,490→3,559개, SQL 17,630→17,655개이며 medium은 양쪽 모두 975개입니다. 양쪽 모두 CTP `ef6712a`, build 재사용, shell/SQL/medium 50/10/1 shard 조건입니다. Suite 시간은 첫 shard 시작부터 마지막 종료까지이며 병렬 실행하므로 합산하지 않습니다.
- Engine 리비전과 실패 케이스가 다른 각 1회 관측입니다. 시간 감소를 TC 추가나 HA 분리의 효과로 단정하지 않습니다. Shell 누적 shard 시간은 42분 50초(+2.6%) 늘었습니다.
- **QA 검토:** 결함 검출 가치가 큰 대표 TC를 우선하고 중복 검사와 수행 비용을 함께 검토해 선별·통합합니다. 현재 활성 사례도 검토 대상입니다.
- **비활성 실패 TC:** 원인을 규명하고 올바른 기대값을 유지해 수정한 뒤, PASS와 자원 정리를 확인하고 재활성화합니다. 비활성화는 결함 해결이나 PASS가 아닙니다.
- **장시간 TC:** `shell_heavy` 이전은 아직 적용하지 않았습니다. 20초는 히스토그램에 따른 QA 검토용 잠정 기준입니다. 유용한 사례의 위치·주기·조건을 정하고, 실패도 겹치는 사례는 수정·PASS 확인 후 이전합니다.
