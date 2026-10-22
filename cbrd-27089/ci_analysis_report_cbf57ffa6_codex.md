# PR #7927 통합 후 CI 증거 경고 보고서 — cbf57ffa6

작성일: 2026-10-22, Asia/Seoul. 대상 독자: PR 작성자와 병합 검토자. 관련 작업: work-tracker #488.

## 확인 결과와 판정 경계

[PR #7927](https://github.com/CUBRID/cubrid/pull/7927)의 통합 head `cbf57ffa6b7850574e089df4c0c4a917d5b653c5`에서 실패한 shell testcase 6개를 정확한 merge base와 비교하는 것이 요청된 목표다.

**이번 전체 suite 수집은 불완전하다. SQL shard 01에서 workflow 결과와 JUnit 집계가 달라 collector가 무결성 오류로 종료했다. 이 스냅샷은 회귀·비회귀 또는 근본 원인 결론을 지원하지 않는다.** 보고서에는 독립 검증을 통과한 medium·shell 증거와 수집 장애만 기록한다. SQL의 GitHub 성공 상태는 검증된 전체 suite 통과 판정과 구별한다.

`cubrid-ci-analyze/scripts/report_mode.py`의 실행 결과는 `mode: warning`, `regression_conclusions_allowed: false`, `comparison_scope: none`이다. 따라서 shell 실패의 베이스 공유 여부, head 추가 여부, PR 인과관계를 판정하지 않았다. Chronicle 이력 조회도 완전한 head 수집 이후 단계이므로 이번에는 수행하지 않았다.

## 고정된 실행과 수집 식별

| 항목 | 확인된 값 |
| --- | --- |
| 소스 저장소 | `CUBRID/cubrid` |
| PR / head 저장소 | #7927 / `vimkim/cubrid` |
| head 브랜치 → 대상 브랜치 | `feat/oos-deferred-write` → `feature/oos-merge` |
| 분석 대상 Engine | `cbf57ffa6b7850574e089df4c0c4a917d5b653c5` |
| CI 실행 | [39730029005, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/39730029005/attempts/1) |
| 상태 스냅샷 | `2026-10-22T07:27:22+00:00` |
| head collection 시각 | `2026-10-22T07:28:19.405591821Z` |
| collector | `cubrid-ci 0.2.0 (9536bd3c2867, release)` |
| 수집 결과 | exit `4`, `ok: false`, observation `incomplete` |
| head observation | `20261022T072754.698937901Z-2928199-0` |
| 요청 범위 | `test_medium`, `test_sql`, `test_shell` 전부 |
| 검증된 medium 입력 | public testcase `2bb3f96b622e479a85fd07304c2f8a2d3a669763`, `tc/pr-7927` |
| 검증된 shell 입력 | private testcase `fbc2ad8e9816d65b5f0a5ff777a9de479abce5bd`, `tc/pr-7927` |

`gh-pr-info`와 보완 PR 조회에서 head가 인계와 동일함을 확인했다. head 저장소와 ref는 위 표와 같다. 완료된 두 suite의 모든 shard는 동일한 Engine SHA, Debug build, producing run `39730029005` / attempt `1`을 기록한다.

수집 명령은 각각 한 번만 실행했다. CI를 기다리는 `--wait`는 사용하지 않았다.

```bash
cubrid-ci status https://github.com/CUBRID/cubrid/pull/7927 --json
cubrid-ci collect https://github.com/CUBRID/cubrid/pull/7927 \
  --commit cbf57ffa6b7850574e089df4c0c4a917d5b653c5 --json
cubrid-ci collect-base https://github.com/CUBRID/cubrid/pull/7927 --json
```

## Suite 상태

세 suite 모두 위의 동일한 CI run / attempt에서 선택됐다. 아래 수치는 검증된 summary가 있는 suite에만 기입했다.

| Suite | collector 상태 | GitHub 상태 | 검증 verdict | Planned / Tests | Run | Passed | Failure | Error | Skipped | Unrun |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `test_medium` | `completed` | SUCCESS | PASS | 975 | 975 | 975 | 0 | 0 | 0 | 0 |
| `test_sql` | `collection_failed` | SUCCESS | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 |
| `test_shell` | `completed` | FAILURE | FAIL | 3476 | 3446 | 3440 | 6 | 0 | 30 | 0 |

집계는 `975 = 975 + 0 + 0 + 0`, `3476 = 3440 + 6 + 0 + 30` 및 `3476 = 3446 + 0 + 30`으로 일치한다. SQL 전체 집계는 보존 raw 파일에서 추산해 대체하지 않았다. 상태 스냅샷에서 debug/release 빌드와 정적 검사들은 SUCCESS이며 `Check TC PRs`는 `not_observed`다. 자동 gate가 관측되지 않았다는 사실은 개인 CUBRID 지침의 TC 선행 처리 요구를 해제하지 않는다.

## 수집 장부와 구조화된 진단

head observation의 acquisition 장부는 다음과 같다. 구간 표기는 해당 구간의 **각 shard 전부**를 뜻한다.

| Suite | Shard | retained | failed | not_attempted | 해석 |
| --- | --- | ---: | ---: | ---: | --- |
| medium | 00 | 1 | 0 | 0 | 원본 획득과 summary 검증 완료 |
| shell | 00–49 | 50 | 0 | 0 | 원본 획득과 summary 검증 완료 |
| SQL | 00–09 | 10 | 0 | 0 | 원본은 보존됐지만 suite summary 정합성 검증 실패 |

`retained`는 해당 shard의 raw 응답 집합이 보존됐다는 뜻이다. SQL 10개 shard에 테스트 통과 verdict를 부여하는 근거는 아니다. 다운로드 실패 shard나 미시도 shard로 바꿔 해석하지 않는다.

| 진단 필드 | 값 |
| --- | --- |
| suite | `test_sql` |
| kind | `integrity` |
| diagnostic | `identity_or_integrity` |
| message | `result identity mismatch: shard 01 workflow result and JUnit counts disagree` |
| 실패 지점 | 수집된 workflow 결과와 JUnit 집계의 정합성 검사 |
| 실패 응답 endpoint / consumed bytes | 이번 진단에 제공되지 않음. acquisition 장부에는 실패 응답이 없음 |

보존된 SQL shard 01 raw 파일에서는 `shard.done`과 `plan.tsv`가 배정 수 `3533`을 기록하고, `linux_sql_64bit.xml`의 tests 속성과 `summary_info` 머리말은 `3531`을 기록한다. 이는 검사 대상 파일을 찾기 위한 raw 관측이다. 누락·중복 testcase의 정체, 누락이 발생한 단계, Engine 또는 runner의 원인은 아직 확인하지 않았다. 배정 수 차이만으로 collector가 비교한 모든 카운터의 의미를 대체할 수 없다.

## 독립 검증을 통과한 완료 증거

head command-result/manifest v2와 일치하는 observation request/result v1을 스키마 검증했다. observation은 유일하게 선택됐고 command 전체가 저장 결과와 일치한다. 저장소, PR 번호·URL, full head SHA, 요청한 세 suite, 옵션, suite 상태, 오류 목록을 대조했다.

완료된 medium·shell에 대해서는 다음을 확인했다.

- summary v2, raw index v2, 실패 metadata v2 스키마.
- summary와 manifest의 run/attempt, shard별 Engine 및 testcase SHA.
- summary SHA-256과 raw 파일 **644개**의 길이·SHA-256: medium 28개, shell 616개.
- 증거 경로의 suite 내부 포함 여부, 선언된 message/diff 파일의 존재.
- summary 실패·오류 수와 metadata 수의 일치, 중복 stable ID 부재, 집계식.
- 인계의 초기 실패 목록과 검증된 shell inventory의 전체 경로·shard 일치.

검증된 실패 6개는 아래와 같다. 각 행의 result는 `failure`이며 error는 없다. 이것은 완료된 shell 증거의 목록이며 원인 분류표가 아니다. head 원인 판정 6건과 baseline-only 실패 수는 모두 미확인으로 남긴다.

| 전체 testcase 경로 | Shard | CI job |
| --- | ---: | --- |
| `shell/_40_guava/cbrd_26354/cases/cbrd_26354.sh` | 23 | [119671848561](https://github.com/CUBRID/cubrid/actions/runs/39730029005/job/119671848561) |
| `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | 25 | [119671848525](https://github.com/CUBRID/cubrid/actions/runs/39730029005/job/119671848525) |
| `shell/_38_fig/cbrd_24916_check_index_ovfps/cases/cbrd_24916_check_index_ovfps.sh` | 30 | [119671848517](https://github.com/CUBRID/cubrid/actions/runs/39730029005/job/119671848517) |
| `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | 32 | [119671848509](https://github.com/CUBRID/cubrid/actions/runs/39730029005/job/119671848509) |
| `shell/_06_issues/_25_1h/cbrd_24741/04_stress_concurrency_ha/cases/04_stress_concurrency_ha.sh` | 39 | [119671848494](https://github.com/CUBRID/cubrid/actions/runs/39730029005/job/119671848494) |
| `shell/_06_issues/_14_2h/bug_bts_15529/cases/bug_bts_15529.sh` | 48 | [119671848580](https://github.com/CUBRID/cubrid/actions/runs/39730029005/job/119671848580) |

각 행은 `test_shell/summary.json`의 같은 경로·shard와 대응한다. 여섯 건 모두 message와 추출된 diff가 존재함을 확인했다. 이번 warning 범위에서는 메시지의 인과 해석, testcase 코드 분석, core 분석, 과거 실패와의 증상 비교를 수행하지 않았다. 과거 head의 문서나 PR #7990 분석은 이번 실패의 판정 근거로 옮겨 쓰지 않았다.

## 베이스 획득 상태

`collect-base`를 한 번 실행했다. PR/target 식별 request는 보존됐지만 ancestry fetch가 진행 중인 상태에서 로컬 조회를 의도적으로 종료했다. 이미 head의 무결성 오류와 warning gate가 확정돼 이번 invocation에서 인과 분석을 진행할 수 없었기 때문이다. 원격 CI는 취소하지 않았다. 이 종료를 provider 장애나 베이스 테스트 실패로 해석하지 않는다.

| 식별 또는 획득 항목 | 결과 |
| --- | --- |
| 보존 request의 PR / head | #7927 / `cbf57ffa6b7850574e089df4c0c4a917d5b653c5` |
| 보존 request의 target | `feature/oos-merge` / `1a8c7057623d92205dbc1324ec43e3cc40fc4cd2` |
| target 관측 시각 | `2026-10-22T07:29:29.651753844Z` |
| exact merge base | 미확정. target tip을 merge base로 대체하지 않음 |
| baseline command 종료 | exit `3`, `kind: unavailable`, `diagnostic: unavailable` |
| CLI 오류 | `Git fetch failed (signal: 15 (SIGTERM)); merge-base history unresolved` |
| 실제 종료 경위 | agent가 이 invocation의 로컬 Git fetch 자식 프로세스만 SIGTERM으로 종료 |
| baseline manifest v3 / observation v2 | 생성되지 않음. 검증된 baseline bundle 없음 |
| run/attempt 발견 범위·선택 / testcase revision / 설정 / shard coverage | 미확인. exact-base suite 수집 단계에 도달하지 못함 |
| report-mode baseline 입력 | `unavailable` |

보존 request는 `/home/vimkim/.local/share/cubrid-ci-data/baseline-resolutions/resolution-MfpDPu/request.json`이다. head SHA가 고정 스냅샷과 같다는 request 관측만 남기며, 이를 observation-v2 검증 완료로 취급하지 않는다. 베이스 각 suite의 획득·테스트 상태는 미확인이다. `not_observed`, FAIL, PASS로 임의 분류하지 않았다. 변경되지 않은 testcase 파일·helper·fixture, 동일 설정, 같은 증상 또는 base-only 실패 수에 대한 비교도 수행하지 않았다. 베이스 부재를 head 회귀의 근거로 쓰지 않는다.

## 바이너리와 보존 범위

`--include-binaries`는 요청하지 않았다. head observation의 binary budget은 configured `536870912` bytes, consumed `0`, remaining `536870912`이며 artifact 항목은 없다. 따라서 core·실행 바이너리를 내려받거나 검증하지 않았다. 이번 미수집은 예산 소진이나 provider에서 파일이 없다는 증거가 아니다.

소스와 두 testcase worktree·index는 변경하지 않았다. 기존 `cubrid-cci` 내부 수정 및 `cubrid-jdbc` gitlink 차이를 보존했다. 소스·testcase 수정, 로컬 재현, CI 재실행, 외부 댓글, push, PR·TC merge/close를 수행하지 않았다. 보고서는 문서 저장소의 별도 브랜치에만 로컬 커밋한다.

## 다음 작업과 필요한 증거

1. 현재 run의 SQL shard 01에서 workflow 결과, 전체 상태 목록, JUnit testcase identity를 대조해 집계 차이를 설명한다. 보존 raw 파일에서 시작하고, 누락 결과를 임의 생성하거나 collector 검증을 완화하지 않는다.
2. 세 suite를 포함한 검증된 terminal 수집을 얻을 수 있는지 판정한다. 이 보고서는 같은 head 명령을 반복해 스냅샷을 개선하지 않았다. 도구·runner·artifact 보정이 필요하면 별도 작업으로 수행한다. 이 경고 보고서 자체는 소스·testcase 수정 또는 CI 재실행 요청이 아니다.
3. 완전한 head evidence와 유효한 exact-base evidence를 확보한 뒤 실패 6개의 전체 경로, 실제 메시지·diff·stack, testcase/helper/config 입력을 비교한다. 그때 각 건의 공유 증상·추가 증상·비교 불가를 판정하고 Chronicle 이력을 별도로 검토한다.
4. 검증 전까지 PR 회귀, 베이스의 동일 실패, flaky, 병합 가능 판정을 보류한다. TC PR 선행 처리와 전체 CI 요구는 별도로 남는다.

## 증거 위치

분석 보조 파일 루트 `R`:

```text
/mnt/nvme/data-5/tmp/pr7927-ci-analysis-20261022.fsMpdu
```

collector head 증거 루트 `H`:

```text
/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/cbf57ffa6b7850574e089df4c0c4a917d5b653c5
```

| 파일 | 용도 |
| --- | --- |
| `R/status.json`, `R/head-result.json`, `R/head-exit.txt` | 한 번의 상태 스냅샷과 원본 수집 결과 |
| `R/head-manifest.json`, `R/head-observation-request.json`, `R/head-observation-result.json` | 이번 invocation과 일치하는 manifest·observation 보존 사본 |
| `R/validate_bundle.py`, `R/head-validation.json` | 스키마·digest·경로·집계 검증 절차와 결과 |
| `R/assessment.json`, `R/head-report-mode.json`, `R/final-report-mode.json` | report-mode 입력과 허용 범위 |
| `R/base-result.json`, `R/base-exit.txt`, `R/base-stderr.log` | 한 번의 베이스 획득 결과 |
| `R/base-resolution-request.json`, `R/base-local-interruption.json` | 베이스의 보존 PR/target request와 로컬 종료 사유 |
| `H/observations/20261022T072754.698937901Z-2928199-0/` | 원본 append-only head observation |
| `H/providers/github-actions/runs/39730029005/attempts/1/test_medium/` | 검증된 medium summary·raw |
| `H/providers/github-actions/runs/39730029005/attempts/1/test_shell/` | 검증된 shell summary·실패 metadata·message·diff·raw |
| `H/providers/github-actions/runs/39730029005/attempts/1/test_sql/raw/` | SQL 장애의 보존 raw. 유효한 SQL summary는 없음 |

검증 실행은 시스템 Python의 `jsonschema` 환경을 사용했다.

```bash
/usr/bin/python3 R/validate_bundle.py R head
python3 /home/vimkim/.agents/skills/cubrid-ci-analyze/scripts/report_mode.py R/assessment.json
```

`R`은 위 실제 경로로 치환한다. 도구 소유 raw, 수집 사본, 검증 스크립트·중간 JSON은 문서 Git 이력에 포함하지 않는다.
