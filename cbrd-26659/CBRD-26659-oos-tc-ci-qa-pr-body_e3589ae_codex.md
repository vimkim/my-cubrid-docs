https://jira.cubrid.org/browse/CBRD-26659

## Purpose

- OOS(Out-of-row Overflow Storage, 큰 값을 행 밖에 저장하는 방식)의 SQL·shell 회귀 검증을 보완합니다.
- AS-IS: 논리 결과만으로는 실제 저장 상태, 값의 소유권, 장애 후 복구를 충분히 확인하기 어렵습니다.
- TO-BE: 대표 동작과 저장 상태를 함께 검증하고, 일반 CI에 유지할 사례를 QA와 선별합니다.

## Implementation

- Public [TC PR #3688](https://github.com/CUBRID/cubrid-testcases/pull/3688)에 SQL/answer 28쌍을 제공합니다. 25쌍이 활성이고 실패 3쌍은 비활성 상태로 보존합니다.
- Private [TC PR #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365)에 OOS shell 139개를 제공합니다. 활성 73개·비활성 66개이며 HA 복제·장애 전환과 sync/async 검증을 포함합니다.
- Engine에는 저장 경계, 읽기·버퍼 수명, 소유권·회수·복구를 확인하는 C++ 단위 테스트와 테스트 전용 진입점을 보완했습니다.

## Remarks

- [전체 CI 40643373124](https://github.com/CUBRID/cubrid/actions/runs/40643373124)는 build·medium·SQL·shell 모두 SUCCESS이며 **57분 00초**가 걸렸습니다. Engine `e3589ae`, public TC `45e21ad`, private TC `479035a`의 결과입니다.
- 추가 TC가 없는 PR #7990 본문의 [전체 성공 CI 40349442612](https://github.com/CUBRID/cubrid/actions/runs/40349442612)는 **47분 14초**였습니다. 관측 차이는 **+9분 46초(+20.7%)**이며 suite별 변화는 아래와 같습니다. Suite 시간은 병렬 shard의 첫 시작부터 마지막 종료까지입니다.

| 항목 | 추가 TC 전 | 추가 TC 포함 | 차이 |
| --- | ---: | ---: | ---: |
| 전체 경과 | 47분 14초 | 57분 00초 | +9분 46초 |
| test_medium | 3분 01초 | 3분 24초 | +23초 |
| test_sql | 15분 04초 | 17분 24초 | +2분 20초 |
| test_shell | 38분 10초 | 50분 37초 | +12분 27초 |

- 실행 환경·리비전이 다르고 이번 shell shard는 15분에 걸쳐 분산 시작했습니다. 위 차이는 관측값이며 머지 후 고정 증가량은 아닙니다. PR #7990의 현재 최신 성공 실행은 shell 일부 재실행이어서 전체 실행 기준으로 사용하지 않았습니다.
- **QA 검토:** CI 시간을 고려해 결함 검출 가치가 큰 대표 TC를 우선하고, 중복되거나 비용 대비 효과가 낮은 사례를 선별·통합할 필요가 있습니다. 현재 활성 사례도 이 검토 대상입니다.
- **비활성 실패 TC:** 원인을 규명하고 올바른 기대값을 유지해 수정한 뒤, PASS와 자원 정리를 확인하고 재활성화합니다. 비활성화는 결함 해결이나 PASS를 뜻하지 않습니다.
- **개별 1분 초과 TC:** 기록된 장시간 사례는 이미 비활성화했습니다. 유용한 사례는 QA와 `shell-heavy` 등 별도 장시간 suite의 위치·주기·실행 조건을 정해 이전합니다. 실패도 겹치는 사례는 수정·PASS 확인이 먼저입니다.
- Private TC 최신 `4ef07ee`는 위 CI 이후 HA helper의 설명 주석을 수정한 리비전입니다. TC 선별·장시간 suite 이전과 비활성 실패 수정은 후속 작업입니다.
