# CBRD-27020 — private TC PR #3810 코드 리뷰

검토 질문은 추가된 shell 테스트가 `SHOW INDEX CAPACITY`의 병렬·직렬 결과를 같은 물리적 상태에서 비교하는가이다. 대상 독자는 테스트 작성자와 PR 리뷰어다. **규약 검토에서는 지적사항이 없었고, 요구사항 검토에서는 vacuum 완료를 보장하지 않은 채 기준값을 수집하는 P2 문제 1건을 확인했다.**

이 보고서는 테스트 구현의 소스 검토와 보조 함수의 모의 실행 결과를 기록한다. 실제 DB에서 해당 테스트의 NOK를 재현한 결과는 포함하지 않는다.

## 검토 범위와 리비전

| 항목 | 값 |
| --- | --- |
| 검토일 | 2026-10-26 (Asia/Seoul) |
| 이슈 | [CBRD-27020](https://jira.cubrid.org/browse/CBRD-27020) |
| 대상 PR | [CUBRID/cubrid-testcases-private-ex #3810](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/3810) |
| 대상 브랜치 | `tc/pr-7604` → `develop` |
| 테스트 head | `a0b8a69222b16b1157300ad5be16e3d8ab71e097` |
| 테스트 base | `fa3b719c0799b4b1ea3313355a71f6f8fdba3372` |
| 변경 범위 | `shell/_40_guava/cbrd_27020/27020_01/cases/27020_01.sh` 추가, 404줄 |
| 관련 엔진 PR | [CUBRID/cubrid #7604](https://github.com/CUBRID/cubrid/pull/7604) |
| 동작을 확인한 엔진 리비전 | `ef1ba1cf4851bfd3cf110e253d6ba89db3dbc1be` |
| 확인한 실행 경로 | 서버 모드(CS)의 병렬·직렬 경로와 독립 실행 모드(SA)의 시작 시 vacuum |
| 수정·계측 여부 | 테스트와 엔진 소스 변경 없음. 보조 함수만 임시 환경에서 모의 실행 |

2026-09-23의 [엔진 PR 리뷰](code_review_14811499_codex.md)는 `14811499`에 대한 별도 기록이다. 그 보고서의 과거 지적사항을 이번 엔진 head에 대한 결론으로 재사용하지 않았다. 아래 vacuum 경로는 위에 명시한 `ef1ba1cf` 소스에서 확인했다.

## 테스트의 역할과 비교 전제

테스트는 높이 3인 인덱스, overflow OID 페이지가 있는 인덱스, 루트 자식 수로 worker 수가 제한되는 인덱스, unique 인덱스 및 직렬 fallback용 인덱스를 구성한다. 서버가 보유한 병렬 파라미터와 트리 형태를 검사한 뒤 다음 결과를 파일 전체로 비교한다.

| 캡처 | 실행 조건 | 확인하려는 성질 |
| --- | --- | --- |
| `parallel_8a.log` | 서버, `parallelism=8` 요청 | 최초 병렬 기준값 |
| `serial_sa.log` | 서버 중지 후 `csql -S` | SA 직렬 경로와의 일치 |
| `parallel_8b.log` | SA 실행 후 서버 재시작 | SA와 재시작 전후 상태 유지 |
| `serial_cs.log` | 서버 재시작, `parallelism=0` | CS 직렬 경로와의 일치 |
| `parallel_3.log` | 서버 재시작, `parallelism=3` | worker 분배 조건을 바꿔도 결과 일치 |

핵심 전제는 각 캡처 사이에 인덱스의 물리적 상태가 유지되는 것이다. INSERT만 수행해도 vacuum이 삽입 MVCCID를 제거하면 레코드 길이와 여유 공간 통계가 달라질 수 있다. SQL에서 보이는 행이 같다는 사실만으로 물리적 통계의 불변성이 보장되지는 않는다.

## 규약 검토: 지적사항 없음

적용 가능한 작업 지침과 주변 shell 테스트 관례를 검토했다. 수정이 필요한 문서화된 규약 위반이나 유의미한 코드 냄새는 찾지 못했다. 아래 문제는 규약 위반이 아니라 비교 전제를 만족시키지 못하는 기능상 문제로 분류했다.

## 요구사항 검토: P2 — 첫 기준값을 수집하기 전에 vacuum을 완료해야 함

**위치:** [`wait_until_stable()`, 194–203줄](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/a0b8a69222b16b1157300ad5be16e3d8ab71e097/shell/_40_guava/cbrd_27020/27020_01/cases/27020_01.sh#L194-L203). 이 함수는 [302–303줄](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/a0b8a69222b16b1157300ad5be16e3d8ab71e097/shell/_40_guava/cbrd_27020/27020_01/cases/27020_01.sh#L300-L303)에서 호출되며, 이후 [366–375줄](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/a0b8a69222b16b1157300ad5be16e3d8ab71e097/shell/_40_guava/cbrd_27020/27020_01/cases/27020_01.sh#L364-L375)의 병렬·SA 캡처가 이 전제에 의존한다.

### 요구사항과 현재 구현의 차이

테스트 설명은 같은 데이터를 다섯 번 읽어 비교하고, `wait_until_stable`이 INSERT 이후의 vacuum을 기다린다고 명시한다. 그러나 실제 종료 조건은 **2초 간격으로 수집한 출력 두 개가 같은가**이다. 아직 처리되지 않은 vacuum 작업이 없는지는 검사하지 않는다.

두 출력이 같아도 vacuum이 완료되지 않았을 수 있다. 특히 서버 모드는 로그 끝에 너무 가까운 작업을 처리하지 않고 뒤로 미룬다. 따라서 물리적 통계가 한동안 고정된 상태와 vacuum이 완료된 상태를 구분해야 한다.

### 엔진 소스에서 확인한 동작

| 구분 | 소스 근거 | 확인한 동작 |
| --- | --- | --- |
| 서버 vacuum의 보류 조건 | [`vacuum.c:3118–3146`](https://github.com/CUBRID/cubrid/blob/ef1ba1cf4851bfd3cf110e253d6ba89db3dbc1be/src/query/vacuum.c#L3118-L3146) | MVCC 가시성 조건을 만족하지 않거나 로그 끝에 너무 가까운 블록이면 작업 시작을 보류한다. |
| 일반 CSQL의 클라이언트 유형 | [`csql.c:3276–3294`](https://github.com/CUBRID/cubrid/blob/ef1ba1cf4851bfd3cf110e253d6ba89db3dbc1be/src/executables/csql.c#L3276-L3294) | 별도 skip 옵션이 없으면 `DB_CLIENT_TYPE_CSQL`을 선택한다. 테스트의 `csql -S` 호출에는 skip 옵션이 없다. |
| SA의 skip 판단 | [`boot_sr.c:3236–3245`](https://github.com/CUBRID/cubrid/blob/ef1ba1cf4851bfd3cf110e253d6ba89db3dbc1be/src/transaction/boot_sr.c#L3236-L3245) | skip 전용 CSQL 유형에만 `skip_vacuum=true`를 설정한다. |
| SA 시작 시 vacuum | [`boot_sr.c:2657–2666`](https://github.com/CUBRID/cubrid/blob/ef1ba1cf4851bfd3cf110e253d6ba89db3dbc1be/src/transaction/boot_sr.c#L2657-L2666) | 일반 SA 시작 경로에서 `xvacuum()`을 호출한다. |
| 마지막 부분 블록 처리 | [`vacuum.c:1070–1084`](https://github.com/CUBRID/cubrid/blob/ef1ba1cf4851bfd3cf110e253d6ba89db3dbc1be/src/query/vacuum.c#L1070-L1084) | SA vacuum은 로그 헤더에 남은 마지막 부분 블록도 처리한다. |

### 정상 엔진에서도 NOK가 가능한 순서

1. INSERT 후 서버에 처리되지 않은 vacuum 작업이 남는다.
2. 작업이 보류되거나 실행이 늦어져 2초 간격의 출력 두 개가 같다. 대기 함수가 성공으로 종료한다.
3. `parallel_8a.log`에 vacuum 완료 전의 물리적 통계가 저장된다.
4. 서버를 중지하고 `csql -S`로 접속한다. SA 시작 시 남은 vacuum 작업을 처리하므로 `serial_sa.log`는 다른 물리적 상태를 읽을 수 있다.
5. 레코드 길이·여유 공간 등의 차이로 파일 비교가 실패한다. 테스트는 이를 병렬·직렬 결과 불일치로 보고하지만, 실제 원인은 캡처 사이에 달라진 물리적 상태다.

이 경로는 소스에 근거한 실패 가능성이다. 해당 데이터셋에서 실제로 어떤 블록이 남고 어떤 통계가 바뀌는지는 DB 실행으로 확인하지 않았다.

### 권고 수정

데이터 적재 후 서버를 중지하고, 종료 코드를 확인하는 `cubrid vacuumdb -S "$dbname"`를 실행해 vacuum을 완료한다. 그 뒤 서버를 다시 시작하고 첫 병렬 기준값을 수집한다. 이렇게 하면 SA 비교의 시작 시점에 남은 INSERT vacuum이 개입할 여지를 제거할 수 있다.

주변의 물리 상태 검증 테스트도 서버 중지 → SA vacuum → 서버 시작 순서를 사용한다. 예시는 [`cbrd_27401.sh:189–194`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/a0b8a69222b16b1157300ad5be16e3d8ab71e097/shell/_40_guava/cbrd_27401/cases/cbrd_27401.sh#L189-L194)와 [`cbrd_24094.sh:157–163`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/a0b8a69222b16b1157300ad5be16e3d8ab71e097/shell/_40_guava/cbrd_24094/cases/cbrd_24094.sh#L157-L163)다.

수정 후에는 같은 엔진 리비전에서 해당 shell 테스트를 실행해 인덱스 형태 검사와 다섯 캡처의 일치 여부를 확인해야 한다.

## 수행한 검증과 한계

테스트 저장소의 위 head에서 다음 검사를 수행했고 모두 통과했다.

```bash
bash -n shell/_40_guava/cbrd_27020/27020_01/cases/27020_01.sh
git diff --check fa3b719c0799b4b1ea3313355a71f6f8fdba3372...a0b8a69222b16b1157300ad5be16e3d8ab71e097
```

보조 함수 검증에서는 원본 `wait_until_stable`과 당시 CUBRID/cubrid-testtools `develop`의 `wait_until`을 임시 디렉터리에서 로드했다. DB 명령 대신 `show_capacity`가 순서대로 `A, A, B`를 기록하도록 구성했다. A와 B에는 각각 `dba.t1`로 시작하는 유효한 모의 결과 행을 넣고 여유 공간 값만 다르게 했다. 실제 2초 대기는 유지했다.

관측 결과는 다음과 같다.

```text
wait_until_stable status=0 after captures=2
next capture differs after helper declared stability
simulation_exit=0
```

이 모의 실행은 함수가 처음 같은 두 출력에서 종료하며 이후 상태 변경을 배제하지 못한다는 점만 확인한다. 실제 vacuum 스케줄, 엔진 오류, 전체 테스트 실행 결과를 재현하거나 증명하지 않는다.

실제 DB 실행·엔진 빌드·회귀 테스트는 수행하지 않았다. 테스트 및 엔진 소스는 수정하지 않았다. 검토 결과는 **규약 0건, 요구사항 P2 1건**이며, 병렬 집계 엔진 자체의 오류를 새로 확인한 것은 아니다.
