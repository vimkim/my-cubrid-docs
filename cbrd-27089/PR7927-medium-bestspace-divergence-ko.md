# PR7927 medium 순서 차이: bestspace와 재사용 힙 상태가 유력한 원인

작성: 2026-10-08 KST. 대상: [CUBRID/cubrid PR7927](https://github.com/CUBRID/cubrid/pull/7927). 실험 수행일: 2026-10-07 KST.

## 현재 판단

PR7927의 세 medium 실패는 **재사용 힙의 bestspace 상태와 삽입 페이지 후보 선택에 따른 물리적 배치 차이로 보인다.** 세 대상의 원래 순차 스캔 계획은 같다. 삽입 경계까지 계측한 `to_number_order_by` 와 `to_timestamp_order_by` 는 같은 행을 같은 순서와 같은 바이트로 삽입했지만, 행이 들어가는 페이지와 슬롯이 달라져 정렬 없는 조회의 출력 순서가 달라졌다. 대상 직전에 힙 재사용을 끄면 세 테스트 모두 리비전 간 순서 차이가 사라진다.

따라서 현재 증상을 bestspace 관련 순서 차이로 정리하는 것이 타당하다. 다만 **bestspace 구현 자체의 결함을 확정한 것은 아니다.** 선행 SQL이 남긴 재사용 힙의 슬롯·빈 공간 이력이 먼저 달라진 것인지, 같은 상태에서 bestspace 후보 선택이 달라진 것인지는 아직 구분하지 않았다. PR 변경이 그 이력을 처음 갈라놓는 지점도 미확정이다.

이 보고서는 기존 로컬 실험을 해석한 문서이며 새 실험 결과를 추가하지 않는다. 자세한 실행 계약, 명령, 원문 출력과 검증은 [로컬 진단 보고서](medium-local-diagnosis/report.md)에 보존되어 있다.

## 비교 조건과 재현 결과

| 항목 | 고정 입력 |
| --- | --- |
| PR head | `f3144ab4b72fc2bf73f115c9da1cf193c756457a` |
| base | `fb567a629cdb390fff920542173fa36f454c74a0` |
| public testcase | `f5e610d91efdeaa9fcf089f47bf4a89c103a4a93` |
| 실행 | native cubrid-testkit, 직렬 실행, 매 실행 새 DB와 격리된 install/CTP/HOME |
| 반복 대조 | 같은 JDBC, cached locale 바이트 및 실행 중 설정 |
| CI 대조 | [run 37616249409](https://github.com/CUBRID/cubrid/actions/runs/37616249409)의 세 medium 순서 차이 |

| workload | head | base | 관찰 |
| --- | --- | --- | --- |
| 전체 `_02_xtests` 444개 | 444 PASS | 444 PASS | 이전 로컬 PASS 재확인 |
| 전체 `_01_fixed` 114개 → 전체 `_02_xtests` 444개 | 555 PASS / 3 FAIL | 558 PASS | CI와 같은 세 순서 차이 |
| 위 558개를 새 DB에서 반복, locale 바이트도 통일 | 555 PASS / 3 FAIL | 558 PASS | 같은 differential 재현 |

이전 로컬 실행과 CI의 차이는 누락된 선행 114개 workload를 복원하면서 설명되었다. Runner exit 0을 PASS로 간주하지 않고, 기대 목록·실행 순서·개별 result·summary/JUnit 집계·종료 표식을 대조했다. 원래 전체 558개 반복에서 head의 CI 순서와 base의 기존 답안 순서는 각각 2/2회 관찰되었다. 이는 CI 전체 975개를 로컬에서 다시 검증한 결과는 아니다.

## bestspace 관련 배치 차이를 지지하는 관찰

| 관찰 | 해석 |
| --- | --- |
| 원래 변환 SELECT 계획이 양쪽 모두 `sscan` 이며 바이트까지 동일 | 계획 변경으로 출력 순서가 바뀌었다는 설명을 지지하지 않음 |
| `to_number_order_by` 와 `to_timestamp_order_by` 의 삽입 호출 순서가 동일 | 이 두 대상의 클라이언트 삽입 순서 차이로 설명되지 않음 |
| 위 두 대상의 행별 저장 바이트가 동일하며 길이는 각각 24/40바이트 | 대상 행의 직렬화·저장 길이 차이로 설명되지 않음 |
| 같은 값이 서로 다른 페이지·슬롯에 저장됨 | 물리적 배치 차이가 raw 출력 순서와 대응함 |
| 대상 직전에 `dont_reuse_heap_file=yes` 를 적용하면 양쪽 모두 입력 순서 `1,2,3,4,5` | 재사용 힙 이력이 현재 리비전 간 차이에 필요하다는 통제 근거 |
| 변환값 multiset 및 명시적 ASC/DESC 결과는 기존 답안과 일치 | 관찰한 실패 범위는 정렬 없는 출력 순서 차이 |

전체 558개에서의 raw 출력 순서는 다음과 같다. timestamp는 날짜의 일(day)을 비교했다.

| 대상 | base | head |
| --- | --- | --- |
| `to_char_order_by` | `3,5,1,2,4` | `4,1,2,3,5` |
| `to_number_order_by` | `3,5,1,2,4` | `4,1,2,3,5` |
| `to_timestamp_order_by` | `2,5,1,3,4` | `3,5,1,2,4` |

`to_number_order_by` 의 페이지·슬롯 관찰을 값별로 정리하면 다음과 같다. 두 페이지를 순차 스캔할 때 위 raw 순서가 나오는 배치다.

| 삽입값 | base: 페이지 / 슬롯 | head: 페이지 / 슬롯 |
| --- | --- | --- |
| 1 | 21516 / 52 | 21644 / 50 |
| 2 | 21516 / 53 | 21644 / 51 |
| 3 | 21515 / 64 | 21644 / 52 |
| 4 | 21516 / 54 | 21643 / 65 |
| 5 | 21515 / 65 | 21644 / 53 |

볼륨은 모두 0이다. 페이지 번호 절댓값이 다른 것만으로 원인을 판정하지 않았다. 핵심은 같은 값이 앞·뒤 페이지와 슬롯에 배치되는 대응이 달라지고, 그 차이가 실제 출력 순서를 설명한다는 점이다. OID 관찰 query와 GDB 삽입 경계 관찰 모두 원래 선택한 순서 증상이 유지되는지 확인했다. 계측이 전체 실행 상태에 무영향이라는 주장까지 하지는 않는다.

## 소스에서 연결되는 경로

고정 head의 일반 힙 경로를 확인했다. 여기서 말하는 bestspace는 **heap의 삽입 페이지 선택**이며 OOS 파일의 bestspace 결함을 특정한 표현은 아니다.

1. [heap_create_internal](https://github.com/CUBRID/cubrid/blob/f3144ab4b72fc2bf73f115c9da1cf193c756457a/src/storage/heap_file.c#L4869)은 힙 재사용이 켜져 있으면 `file_tracker_reuse_heap` 으로 삭제 표시된 힙을 찾고, 기존 bestspace 객체를 제거한 뒤 `heap_reuse` 를 수행한다.
2. [heap_reuse](https://github.com/CUBRID/cubrid/blob/f3144ab4b72fc2bf73f115c9da1cf193c756457a/src/storage/heap_file.c#L5229)는 일반 힙에서 기존 슬롯을 유지하면서 레코드를 삭제한다. 이후 [페이지별 빈 공간으로 bestspace 후보를 다시 구성](https://github.com/CUBRID/cubrid/blob/f3144ab4b72fc2bf73f115c9da1cf193c756457a/src/storage/heap_file.c#L5310)한다. 앞선 슬롯 이력은 뒤의 삽입에서 사용할 수 있는 공간과 슬롯 배치에 영향을 줄 수 있다.
3. [heap_find_bestpage](https://github.com/CUBRID/cubrid/blob/f3144ab4b72fc2bf73f115c9da1cf193c756457a/src/storage/heap_file.c#L4735)는 필요하면 bestspace를 동기화하고, 요청 크기와 `is_newrec` 를 넘겨 삽입할 페이지를 선택한다.

이 경로는 힙 재사용 통제 실험과 관찰된 페이지 배치를 설명하는 근거다. 특정 후보의 빈 공간이나 bestspace 선택 내부 상태를 실제로 대조한 trace는 아직 없으므로, 소스 경로를 확인했다는 사실과 원인을 확정했다는 판단을 구분한다.

## 판정 범위와 남은 사항

현재 관찰한 세 실패는 **bestspace 후보 선택 또는 그 입력인 재사용 힙 상태에 따른 정렬 없는 출력 순서 차이**가 유력하다. 이 세 결과에서 변환값 손실·오류나 명시적 정렬 결과의 차이는 관찰하지 않았다. 이를 데이터 무결성이나 모든 PR 동작의 정상성을 검증한 것으로 확대하지 않는다.

축소 입력에서도 주의가 필요하다. `3277.sql` 하나만 선행하거나 fixed 앞 14/28/57개만 남기면 base도 head와 같은 순서를 보인다. 따라서 이 축소들은 최소 head/base differential이 아니며, base에서도 힙 이력에 따라 해당 순서가 나올 수 있다는 반례다.

원인 확정이 필요하면 전체 558개를 유지한 채 target 생성 전 `heap_reuse` 완료 시점의 슬롯·빈 공간·후보와 `heap_find_bestpage` 의 요청·선택 페이지를 짝지어 비교해야 한다. 상태가 먼저 다르면 선행 SQL과 파일 생명주기로, 상태와 요청이 같은데 선택만 다르면 bestspace 후보·캐시 선택으로 조사 범위를 좁힐 수 있다.

이번 보고서는 세 medium 실패의 잠정 원인 분류를 공유하는 데 목적이 있다. 엔진 수정, 답안 변경 또는 `dont_reuse_heap_file` 의 운영 적용을 제안하지 않는다. 해당 파라미터 실험은 양쪽을 기존 답안과 다른 `1,2,3,4,5` 로 바꾸므로 testcase PASS를 만든 실험도 아니다. shell 실패는 이 문서의 분석 범위에 포함하지 않는다.

근거: [전체 로컬 진단](medium-local-diagnosis/report.md), [원래 계획 비교](medium-local-diagnosis/evidence/plan-comparison.json), [삽입 바이트·OID 대조](medium-local-diagnosis/evidence/target-insert-observations.json), [시도별 입력과 ordered 검증](medium-local-diagnosis/evidence/attempts.json). 원문과 설정은 기존 보존 자료를 그대로 참조했다.
