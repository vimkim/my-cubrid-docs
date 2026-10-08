# PR7925 / 28b65d18a CI 수집 중단 보고서

작성: 2026-10-08, Asia/Seoul. 대상은 [PR #7925](https://github.com/CUBRID/cubrid/pull/7925)의 과거 HEAD `28b65d18a9302b17d49281e06cb4621b86e9f24d`이며, 현재 게시 HEAD `b755678cd9a3ab465215228d5664f7f1edf24846`의 결과 보고서가 아니다.

**과거 HEAD의 수집 결과, manifest, terminal observation이 없어 SQL·medium·shell testcase 결과를 검증할 수 없다. 이 보고서는 회귀 여부나 실패 원인을 결론 내리지 않는다.** `report_mode.py`의 판정은 `warning`, 비교 허용 범위는 `none`이다.

## 확인된 실행과 수집 상태

2026-10-08 14:12:26 KST에 게시한 [단일 `/run all` 요청](https://github.com/CUBRID/cubrid/pull/7925#issuecomment-6052795241)은 [gha-ci run 37731214428](https://github.com/CUBRID/cubrid/actions/runs/37731214428), attempt 1을 시작했다. 당시 저장한 status와 pickup 기록은 다섯 gha-ci context가 위 HEAD에 연결되었음을 보여준다. 이후 Actions 실행은 `completed / failure`로 끝났고, 마지막 업데이트는 2026-10-08 15:37:32 KST다.

| Suite | GitHub context에서 관찰한 상태 | 검증한 summary / testcase 수 |
| --- | --- | --- |
| test_medium | FAILURE | 없음 / 알 수 없음 |
| test_sql | SUCCESS | 없음 / 알 수 없음 |
| test_shell | FAILURE | 없음 / 알 수 없음 |

Debug와 Release build context는 모두 SUCCESS였다. 위 표는 GitHub 상태 관찰이며, 수집·검증한 testcase 판정과 구별한다. 사용자 설명에 따르면 medium 편차는 bestspace에 따른 출력 순서 차이이고, 사용자가 TC에 `ORDER BY`를 추가할 예정이다. 이번 수집에는 그 설명을 독립적으로 검증할 testcase message나 diff가 없다.

기존 `cubrid-ci collect --commit 28b65d18a... --wait --poll-interval 45s --json` 프로세스는 14:49 KST handoff에서 살아 있었으나, 후속 확인에서 해당 PID 981607과 부모 PID 981604가 사라졌다. `result.json`과 `collect.stderr`는 각각 0 byte이고 `collect-exit.txt`도 없다. 해당 commit의 evidence 디렉터리와 관찰 파일도 확인되지 않았다. 종료 시점과 원인은 알 수 없으며, 이를 CI provider·suite·testcase 실패로 해석할 근거는 없다. 같은 HEAD의 수집이나 CI를 다시 실행하지 않았다.

## Acquisition / binary 증거 한계

Terminal observation의 acquisition ledger가 없어서 각 suite의 shard를 `retained`, `failed`, `not_attempted`로 검증해 나열할 수 없다. 요청한 세 suite 모두 수집 진행 범위는 **unknown**이며, 파일 부재만으로 shard 다운로드 실패나 미실행을 판정하지 않는다.

Binary collection은 요청하지 않았다. 검증 가능한 binary-budget ledger도 없으므로 binary의 존재, provider 보존 상태나 다운로드 예산 소진 여부를 판단하지 않는다. 구조화된 collector diagnostic 역시 반환되지 않았다.

## 독립적으로 검증된 baseline

이 과거 HEAD에 대해 별도로 완료한 `collect-base`는 target `feature/oos-merge`의 tip과 유일한 merge-base를 모두 `fb567a629cdb390fff920542173fa36f454c74a0`으로 기록했다. 관계 확인 시각은 2026-10-08 14:13:23.905685493 KST다. [Baseline run 36570256001](https://github.com/CUBRID/cubrid/actions/runs/36570256001), attempt 1의 기록은 다음과 같다.

| Suite | Passed | Failures | Errors | Skipped | Unrun |
| --- | ---: | ---: | ---: | ---: | ---: |
| test_medium | 975 | 0 | 0 | 0 | 0 |
| test_sql | 17,471 | 0 | 0 | 0 | 0 |
| test_shell | 3,254 | 5 | 0 | 30 | 0 |

Baseline의 schema v3 command/manifest, observation v2, summary·failure schema, 수량 정합성과 raw 파일 780개의 길이·SHA-256 검증은 통과했다. Suite가 사용한 Debug Engine은 위 merge-base이며, 생산 build는 run 36570061594 attempt 1이다. Public TC는 `bdba62aee0faec05abdd861518824c69b6c1b3c5`, private TC는 `c4b9d482fbd491a68510b2552df2c3cac91911fc`, CTP는 `4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb`다.

이 독립 baseline은 과거 HEAD의 누락된 inventory를 보완하지 못한다. Head의 실패 path·signature·runtime 입력을 검증하지 못했으므로 `also_observed_on_base`, `additional_on_head`, `uncomparable`, `base_only` 수량이나 원인 귀속을 작성하지 않는다.

## 다음 작업과 증거 위치

사용자는 이후 최신 PR7927 변경 반영, push, 새 전체 CI 실행 및 모니터링을 명시적으로 요청했다. PR7927의 `f3144ab4b72fc2bf73f115c9da1cf193c756457a` 변경을 포함한 새 HEAD `b755678cd9a3ab465215228d5664f7f1edf24846`를 push하고, 17:08:17 KST에 [새 요청](https://github.com/CUBRID/cubrid/pull/7925#issuecomment-6055595318)을 한 번 게시했다. 다섯 context가 [새 run 37747856853](https://github.com/CUBRID/cubrid/actions/runs/37747856853)에 연결되었다. 새 실행의 판정은 별도 evidence 수집·검증 후 보고해야 하며, 이 문서의 과거 실행 결과를 대체하지 않는다.

우선 새 HEAD의 terminal evidence를 확보하고 독립 baseline과 비교한다. Medium TC의 `ORDER BY`는 사용자 후속 작업이며, PR7927 shared integration과 최종 partition acceptance는 계속 pending이다. 수집 누락이나 알려진 TC 순서 문제만으로 merge readiness를 완료 처리하지 않는다. 이 보고서를 위해 engine/TC 수정, 재현 실행, 추가 GitHub 댓글, CI 재실행을 하지 않았다.

| 증거 | 위치 / 용도 |
| --- | --- |
| 과거 수집 scratch | `/home/vimkim/tmp/pr7925-ci-28b65d1.euCYhf` |
| 과거 HEAD identity / 요청 | 위 디렉터리의 `status.json`, `receipt.json` 및 check/comment snapshot |
| 누락된 collector 반환 | 위 디렉터리의 빈 `result.json`, `collect.stderr`; exit 파일 없음 |
| Warning 판정 | `assessment-interrupted.json`, `report-mode-interrupted.json` |
| 검증한 baseline | `base-result.json`, `base-result-validation.json`, `base-result-manifest.json`, `base-junit-coverage.json`, `base-testcase-inputs.json` |
| Baseline observation | `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/fb567a629cdb390fff920542173fa36f454c74a0/observations/20261008T051527.443319443Z-981925-0` |
| 새 HEAD 모니터링 | `/home/vimkim/tmp/pr7925-ci-b755678cd.4zpT1X`; user systemd unit `cubrid-ci-pr7925-b755678cd-20261008.service` |
| Collector | `cubrid-ci 0.2.0 (16d7252122d1, release)` |

`gh pr checks --required`는 당시 “no required checks reported”를 반환했다. 이는 live 설정 관찰이며 Release·SQL·medium·shell이라는 skill의 안정된 CI 요건을 면제하지 않는다. Raw downloads·자동 생성 inventory·수집 script는 문서 저장소 밖에 보존한다.
