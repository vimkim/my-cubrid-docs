# CBRD-26659 현황보고

기준일은 2026-10-29이며 시간대는 Asia/Seoul이다. 개발·QA 담당자가 OOS 회귀 TC의 현재 상태와 후속 처리 범위를 검토하기 위한 보고다.

[CBRD-26659](https://jira.cubrid.org/browse/CBRD-26659)의 SQL·shell TC를 작성하여 관련 PR에 게시했고, HA 복제 TC는 전용 저장소의 draft PR로 분리했다. **남은 작업은 실패 TC의 원인 분석, 통과한 장시간 TC의 `shell_heavy` 이관, 2분 안에 끝나지 않는 TC의 분할 또는 결함 여부 판단이다.** TC PR의 검토·병합도 남아 있다.

## 1. PR과 실행 대상 현황

| 대상 | PR 상태 | 현재 구성 |
| --- | --- | --- |
| [Engine PR #8128](https://github.com/CUBRID/cubrid/pull/8128) | OPEN, Ready for review | OOS C++ 테스트와 테스트 지원 코드를 포함한다. Base는 `feature/oos-merge`다. |
| [공개 SQL PR #3688](https://github.com/CUBRID/cubrid-testcases/pull/3688) | OPEN, Ready for review | SQL·answer 28쌍 중 활성 25쌍, 비활성 실패 3쌍이다. |
| [비공개 shell PR #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365) | OPEN, Ready for review | 139개 진입점 중 일반 CI 활성 69개, 기존 비활성 66개, HA 분류로 일반 CI에서 제외한 4개다. |
| [HA 전용 PR #1666](https://github.com/CUBRID/cubrid-testcases-private/pull/1666) | OPEN, Draft | `HA/shell/_40_guava`에 활성 4개와 비활성 결함 재현 2개를 게시했다. Base는 `develop`이다. |

비공개 shell의 비활성 66개는 과거 실패 61개, 통과했지만 오래 걸린 3개, 이후 추가한 HA 결함 재현 2개다. HA 결함 재현 2개는 전용 HA PR에도 보존되어 있으므로 서로 다른 TC로 중복 집계하지 않는다. 공개·비공개 shell PR의 제목에는 `Draft`가 남아 있지만 실제 draft 상태는 해제되어 있다.

PR #4365 본문의 활성 73개는 HA 4개를 제외하기 전 집계다. 현재 실행 선택은 [비활성·HA 분류 기록][private-readme]에 적힌 일반 CI 69개를 기준으로 한다.

## 2. 최신 CI와 HA 검증 결과

Engine PR #8128의 [최신 전체 CI 40692318846](https://github.com/CUBRID/cubrid/actions/runs/40692318846)은 **FAILURE**다. Build·SQL·medium은 성공했고, shell은 3,528 PASS·1 FAIL·30 SKIP이다. 실패한 `temp_enc_06`은 이번 OOS TC가 아닌 기존 TDE TC다. 이 실행에서는 계획한 TC의 미실행 누락이 없었다. [최신 CI 입력과 집계](CBRD-26659-oos-ci-runtime-refresh-20261029-pr-context_e3589ae_codex.md)에 상세 근거가 있다.

HA 전용 PR의 최종 native 실행은 **2 PASS·2 FAIL·0 SKIP**이다. 과거 일반 CI에서 HA 4개가 통과한 결과와 전용 위치의 최종 native 결과를 구분한다.

| HA TC | 최종 native 결과 | 확인한 내용 |
| --- | --- | --- |
| `cbrd_26659_ha_async` | PASS | 해당 실행에서 통과했다. |
| `cbrd_26659_ha_failover` | PASS | 해당 실행에서 통과했다. |
| `cbrd_26659_ha_queue` | FAIL | 동시 트랜잭션 이후 master의 barrier UPDATE 연결이 실패했다. 근본 원인은 미확정이다. |
| `cbrd_26659_ha_replication` | FAIL | master의 `key.locate`·`key.rekey` 연결이 실패했고 이후 기대값 비교도 실패했다. 근본 원인은 미확정이다. |

반복 실행에서는 결과가 달랐으며, 전용 다중 호스트 HA job은 아직 실행하지 않았다. 위 연결 실패를 아래 두 엔진 결함과 같은 원인으로 확정하지 않는다. [HA 이전·검증 기록](CBRD-26659-oos-ha-suite-pr-context_ae2bcec_codex.md)에 실행별 결과와 한계를 보존했다.

## 3. 실패 TC 현황

비활성 목록에는 **과거 CI에서 실패한 SQL 3개와 shell 61개**가 있다. 이 목록은 현재 리비전에서 다시 확인한 실패 목록이 아니라 재현·분석 대상이다. 대부분은 FAIL 판정만 정리되어 있고, 엔진·TC·실행 환경 중 어디에서 문제가 시작됐는지 아직 분류하지 못했다.

### 3.1. 공개 SQL 실패 3개

| TC | 과거 결과 | 원인 분석 상태 |
| --- | --- | --- |
| `cbrd_26659_oos_record_boundaries` | FAIL | 미완료 |
| `cbrd_26659_oos_sql05_bigone` | FAIL | 미완료 |
| `cbrd_26659_oos_sql09_lob_maxcols` | FAIL | 미완료 |

[SQL 비활성 목록][public-manifest]은 원본 경로·실행 시간·비활성 사유·원본 hash를 보존한다. 관측은 Engine `c4c4f5c5`의 [CI 40311481032](https://github.com/CUBRID/cubrid/actions/runs/40311481032)에 해당한다.

### 3.2. 비공개 shell 실패 61개

전체 이름과 원본 경로는 [shell 비활성 목록][private-manifest]에서 확인할 수 있다. 61개 중 56개는 과거 60초 이하에서 실패했고, 5개는 60초를 넘겨 실패했다. 아래 5개는 단순 장시간 TC로 옮기기 전에 실패 원인을 먼저 분석해야 한다.

| 실패와 장시간이 겹치는 TC | 과거 실행 시간 |
| --- | ---: |
| `cbrd_26659_churn_abort_retry` | 83.614초 |
| `cbrd_26659_churn_insert_delete` | 83.570초 |
| `cbrd_26659_churn_insert_update_delete` | 90.506초 |
| `cbrd_26659_churn_restart` | 94.797초 |
| `cbrd_26659_schema_rewrites_sa` | 94.311초 |

이 집계는 [CI 40311481032](https://github.com/CUBRID/cubrid/actions/runs/40311481032)와 [CI 40324320840](https://github.com/CUBRID/cubrid/actions/runs/40324320840)의 관측을 사례별로 보존한 것이다. 서로 다른 TC 리비전의 결과를 하나의 전체 실행으로 합치지 않는다. 비활성화할 때 TC 본문·assertion·기대값은 바꾸지 않았다. [집계 범위와 리비전][private-readme]에 상세 조건이 있다.

### 3.3. 원인을 확인한 HA 엔진 결함 2개

| 비활성 재현 TC | 확인한 엔진 결함 | 후속 이슈 |
| --- | --- | --- |
| `cbrd_26659_ha_flush_boundary` | applylogdb가 미반영 항목의 record buffer를 재사용하여 replica의 OOS 값이 손상된다. | [CBRD-27800](https://jira.cubrid.org/browse/CBRD-27800) |
| `cbrd_26659_ha_composite_key` | 복합 기본 키 테이블에서 OOS 값이 있는 행을 UPDATE하면 replica의 applylogdb가 assertion으로 종료한다. | [CBRD-27801](https://jira.cubrid.org/browse/CBRD-27801) |

두 결함은 Engine `e3589ae`에서 재현했다. [HA 결함 재현·원인 기록](ci-replan/ha-queue.md)에 근거가 있다. 이 진단을 나머지 비활성 실패 TC에 일괄 적용하지 않는다.

## 4. 통과한 장시간 TC와 shell_heavy 이관

현재 일반 CI의 비HA OOS shell 69개는 [CI 40643373124](https://github.com/CUBRID/cubrid/actions/runs/40643373124)에서 모두 통과했다. 해당 실행의 개별 시간을 20초 기준으로 나누면 다음과 같다.

| 분류 | TC 수 | 처리 방향 |
| --- | ---: | --- |
| 20초 이하 PASS | 31개 | 일반 shell 유지 대상으로 검토한다. |
| 20초 초과 PASS | 38개 | 별도 `shell_heavy` PR의 이관 후보로 검토한다. |

38개의 관측 시간은 21.218초부터 53.566초까지다. **아직 일반 shell에 남아 있으며, 별도 heavy PR 생성과 실제 이전은 미완료다.** 20초 기준의 후보 선정은 한 번의 CI 관측에 기반하므로 경계 부근의 사례는 재실행에서 분류가 달라질 수 있다. [개별 실행 시간 분포와 측정 조건](CBRD-26659-tc-runtime-histogram_20261028_codex.md)에 근거가 있다.

기존 비활성 목록에도 FAIL 없이 장시간만으로 제외한 PASS TC 3개가 있다. 당시 비활성 기준은 20초가 아니라 60초 초과였다.

| 비활성 PASS TC | 과거 실행 시간 | 후속 처리 |
| --- | ---: | --- |
| `cbrd_26659_schema_sa` | 81.389초 | 현재 리비전에서 PASS를 확인하고 heavy 이관을 검토한다. |
| `cbrd_26659_dml_transitions` | 101.085초 | 현재 리비전에서 PASS를 확인하고 heavy 이관을 검토한다. |
| `cbrd_26659_large_keys` | 381.773초 | 2분 초과 구간을 분석하여 분할 여부와 실행 위치를 정한다. |

38개 활성 후보와 위 3개는 서로 다른 실행 시점의 결과다. 이관 전에는 대상 리비전, 올바른 기대값, PASS 판정과 자원 정리를 함께 확인한다.

## 5. 2분 초과 TC 분석 현황

과거 shell 133개 [전체 목록][private-inventory]에서 120초를 넘긴 것은 `cbrd_26659_large_keys` 1개이며, 최종 결과는 PASS였다. 이 기록은 오래 실행된 뒤 통과했다는 관측이다. 현재 리비전에서의 재현이나 시간 소비 원인까지 확인한 결과는 아니다.

**모든 재현·분석 대상 TC에 2분 제한을 적용한 검증은 아직 수행하지 않았다.** HA native 실행의 testcase timeout은 1,200초였다. HA 내부의 120초 복제·상태 전환 대기 제한을 TC 전체의 2분 제한으로 해석하지 않는다.

후속 실행에서는 준비·본문·정상 정리를 포함한 TC 전체에 120초 제한을 적용한다. 제한에 도달하면 마지막 진행 단계, 실행 중인 명령과 프로세스, 서버 오류 로그를 확보하고 강제 정리 결과를 별도로 기록한다. 분석 결과는 다음과 같이 구분한다.

| 분석 결과 | 처리 방향 |
| --- | --- |
| 정상적으로 진행하지만 여러 검사를 묶어 오래 걸림 | 독립 실행 가능한 단위로 분할하고 각 TC의 PASS를 확인한다. |
| 검증 특성상 긴 대기나 큰 작업량이 필요함 | 필요성과 실행 주기를 설명하고 heavy suite에서 검토한다. |
| 엔진의 crash·교착·무한 대기·값 손상 | 재현 근거와 엔진 후속 이슈를 연결한다. |
| TC의 잘못된 대기·프로세스 관리·환경 의존 | TC 또는 실행 지원 코드를 수정하고 재검증한다. |
| 확보한 로그로 원인을 판단할 수 없음 | 원인 미확정으로 유지하고 추가 관측을 설계한다. |

120초 초과만으로 엔진 결함이나 TC 분할 필요성을 확정하지 않는다.

## 6. 남은 작업과 완료 조건

1. 과거 실패 SQL 3개·shell 61개와 원인 미확정 HA 실패를 현재 리비전에서 재현한다. 최초 실패 지점과 엔진·TC·환경 원인을 사례별로 정리한다.
2. 2분 안에 끝나지 않는 TC의 진행 상태를 분석한다. 정상 장시간 실행, 분할 대상, 엔진 결함, TC 결함을 구분한다.
3. 통과한 20초 초과 TC를 별도 `shell_heavy` PR로 전달한다. 기존 비활성 PASS 3개도 현재 결과와 분할 필요성을 확인한 뒤 포함 여부를 정한다.
4. 분석 결과에 맞춰 PR #4365의 오래된 집계와 JIRA 현황을 갱신한다. TC별 실행 위치·주기와 실패 후속 이슈를 QA·리뷰어에게 전달한다.
5. 각 TC 저장소에서 검토·승인과 병합 근거를 남긴다. TC PR 병합·종료는 담당 리뷰어가 처리한다.

실패를 비활성화한 상태와 활성 선택의 CI 통과만으로 이슈를 완료 처리하지 않는다. 실패 원인·후속 조치, 장시간 TC의 실행 경로, QA·동료 리뷰 및 실제 TC PR 병합 결과가 남아 있다.

## 7. 확인 기준과 근거

| 저장소 | 확인한 head | Branch | Base |
| --- | --- | --- | --- |
| `vimkim/cubrid`의 Engine PR | [`e3589ae42d42b04eb020e1ae43e165b01d31b12a`](https://github.com/CUBRID/cubrid/commit/e3589ae42d42b04eb020e1ae43e165b01d31b12a) | `CBRD-26659-oos-testcases-handover` | `feature/oos-merge` |
| `CUBRID/cubrid-testcases` | [`45e21ad799d82ebadc04a93c7d2f69517d53bf39`](https://github.com/CUBRID/cubrid-testcases/commit/45e21ad799d82ebadc04a93c7d2f69517d53bf39) | `tc/pr-8128` | `feature/oos-merge` |
| `CUBRID/cubrid-testcases-private-ex` | [`02d023932b8aa39b2807cc6a77d72f3d58e231d6`](https://github.com/CUBRID/cubrid-testcases-private-ex/commit/02d023932b8aa39b2807cc6a77d72f3d58e231d6) | `tc/pr-8128` | `feature/oos-merge` |
| `CUBRID/cubrid-testcases-private` | [`ae2bcec1f6a68fb76e90c0a9d50fec4b3463ca51`](https://github.com/CUBRID/cubrid-testcases-private/commit/ae2bcec1f6a68fb76e90c0a9d50fec4b3463ca51) | `tc/pr-8128` | `develop` |

실행 시간 분포는 Engine `e3589ae`·public TC `45e21ad`·private-ex TC `479035a45f06545db1974e1369e88000fb98a89a`의 CI 40643373124 관측이다. HA native 결과는 Engine `e3589ae` optdebug의 실행이며, 전용 위치에서 수행한 최종 결과와 과거 일반 CI 결과를 구분한다.

2026-10-29에 PR 상태·head와 실제 실행 선택을 대조하고, 저장된 TC 목록과 HA native 판정을 확인했다. 이번 현황 확인에서는 TC를 재실행하거나 변경하지 않았다.

[public-manifest]: https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/disabled/oos-pr8128.tsv
[private-readme]: https://github.com/CUBRID/cubrid-testcases-private-ex/blob/02d023932b8aa39b2807cc6a77d72f3d58e231d6/disabled/README.md
[private-manifest]: https://github.com/CUBRID/cubrid-testcases-private-ex/blob/02d023932b8aa39b2807cc6a77d72f3d58e231d6/disabled/oos-pr8128.tsv
[private-inventory]: https://github.com/CUBRID/cubrid-testcases-private-ex/blob/02d023932b8aa39b2807cc6a77d72f3d58e231d6/disabled/oos-pr8128-inventory.tsv
