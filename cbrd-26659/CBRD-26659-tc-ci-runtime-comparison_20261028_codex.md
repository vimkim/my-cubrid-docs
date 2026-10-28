# CBRD-26659: OOS TC 추가 전후의 CI 시간과 QA 선별 방향

작성·확인: 2026-10-28 (Asia/Seoul). 대상: Engine PR [#8128](https://github.com/CUBRID/cubrid/pull/8128), public TC PR [#3688](https://github.com/CUBRID/cubrid-testcases/pull/3688), private TC PR [#4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365). 독자: 개발·QA 담당자.

## 확인한 결과

추가 TC를 포함한 [run40643373124](https://github.com/CUBRID/cubrid/actions/runs/40643373124)의 전체 경과 시간은 **57분 00초**다. `feature/oos-merge → develop` PR [#7990](https://github.com/CUBRID/cubrid/pull/7990) 본문에 연결된 전체 성공 실행은 **47분 14초**이므로, 관측 차이는 **+9분 46초, +20.7%**다. 두 실행 모두 medium 1개·SQL 10개·shell 50개 shard로 수행했다. Shard는 suite를 나누어 병렬 실행하는 단위다.

이 수치는 동일 환경에서 TC 추가만 바꾼 실험의 결과가 아니다. Engine·CTP 리비전과 build 재사용 여부가 다르고, 이번 shell shard의 시작 시각은 15분 06초에 걸쳐 분산됐다. 따라서 **47분→57분을 관측 차이로 설명하되, 머지 후 항상 10분 증가한다고 단정하지 않는다.** 일반 CI에 어떤 TC를 유지할지는 결함 검출 가치와 수행 비용을 함께 검토한다.

PR #7990의 현재 HEAD에 연결된 최신 성공 실행은 전체 실행이 아니라 미실행 shell 699개를 처리한 재실행이다. 그 원본 전체 실행은 61분 42초였으며, shell shard 10개가 실패했다. 비교 기준을 아래와 같이 구분한다.

## 실행 선택과 검증 리비전

모두 attempt 1이다. 시각은 KST이며 전체 시간은 Actions API의 `updated_at - run_started_at`으로 계산했다. 네 실행의 `updated_at`은 마지막 status job 종료의 1~2초 뒤다.

| 용도 | 실행 | 실제 Engine SHA | 시작 → 종료(KST) | 전체 시간 | 관측 상태·범위 |
| --- | --- | --- | --- | ---: | --- |
| PR #7990 본문의 전체 성공 기준 | [40349442612](https://github.com/CUBRID/cubrid/actions/runs/40349442612) | `5a70787feea9e0488222af7e3a0249cc431562ca` | 10-27 00:27:10 → 01:14:24 | 47분 14초 | SUCCESS, 전체 61 shard |
| PR #7990 현재 HEAD의 원본 전체 실행 | [40464422209](https://github.com/CUBRID/cubrid/actions/runs/40464422209) | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` | 10-27 15:59:53 → 17:01:35 | 61분 42초 | FAILURE, shell 40 SUCCESS·10 FAILURE |
| PR #7990 현재 HEAD의 최신 성공 실행 | [40471760533](https://github.com/CUBRID/cubrid/actions/runs/40471760533) | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` | 10-27 17:11:09 → 17:45:16 | 34분 07초 | SUCCESS, shell 699개·12 shard만 재실행 |
| 추가 TC를 포함한 전체 실행 | [40643373124](https://github.com/CUBRID/cubrid/actions/runs/40643373124) | `e3589ae42d42b04eb020e1ae43e165b01d31b12a` | 10-28 15:21:42 → 16:18:42 | 57분 00초 | SUCCESS, 전체 61 shard |

`issue_comment`로 실행한 workflow이므로 Actions run의 `head_sha`는 시험한 Engine SHA와 다르다. 위 SHA는 각 gate의 `resolved` 출력과 debug build 로그의 `SHA`로 확인했다. Source checkout은 `e3589ae`이며, 문서 작성 중 source·TC 파일을 변경하지 않았다.

| 입력 | PR #7990의 세 실행 | 추가 TC 전체 실행 |
| --- | --- | --- |
| Public TC | `70db22a1c99dbbaa27fa1438c8967effdfcad551`, `tc/pr-7990` | `45e21ad799d82ebadc04a93c7d2f69517d53bf39`, `tc/pr-8128` |
| Private TC | `75a02020e19be4bfc64e47f7c7a3d5c2b02d7676`, `tc/pr-7990` | `479035a45f06545db1974e1369e88000fb98a89a`, `tc/pr-8128` |
| CTP | `7dc9f4192bb96988d1bab78df3e45df88628b814` | `ef6712ab450a9c8a6b5bf41d605b1683bd60a3a2` |
| Debug build | 본문 기준 실행은 새 build, 현재 HEAD의 두 실행은 재사용 | 재사용 |

TC·CTP 입력은 각 plan의 checkout 로그와 `split.meta`에서 확인했다. [추가 TC plan](https://github.com/CUBRID/cubrid/actions/runs/40643373124/job/122666783348), [본문 기준 plan](https://github.com/CUBRID/cubrid/actions/runs/40349442612/job/121668101749), [현재 HEAD 전체 plan](https://github.com/CUBRID/cubrid/actions/runs/40464422209/job/122056672356), [재실행 plan](https://github.com/CUBRID/cubrid/actions/runs/40471760533/job/122080786818).

작성 중 private TC HEAD는 `4ef07ee34219a7dce7e5c5d84a2f6c6031b10ec3`으로 전진했다. 시험한 `479035a45` 이후의 한 커밋은 `oos_ha_checks.sh`의 설명 주석만 수정했다. 57분 기록의 입력은 계속 `479035a45`이며, 이를 새로운 HEAD에서 다시 측정한 시간으로 표시하지 않는다.

## PR 본문의 전체 성공 실행 대비 변화

Suite 시간은 workflow 요약의 **`shard span (first start to last end)`**와 같은 계산이다. 각 shard가 기록한 `stamps/1/shard-<suite>-<NN>.tsv`에서 가장 이른 `start`와 가장 늦은 `end`의 차이다. 준비·입력 정렬·CTP·결과 게시가 포함되며, shard 사이의 시작 시각 차이도 반영된다. Actions job 전체 시간이나 개별 TC 시간과는 구분한다. Suite들은 병렬 실행되므로 세 시간을 더해 전체 시간을 계산하지 않는다.

| 항목 | TC 추가 전: 40349442612 | 추가 TC 포함: 40643373124 | 변화 | 변화율 |
| --- | ---: | ---: | ---: | ---: |
| **전체 경과 시간** | **47분 14초** | **57분 00초** | **+9분 46초** | **+20.7%** |
| `test_medium` | 3분 01초 | 3분 24초 | +23초 | +12.7% |
| `test_sql` | 15분 04초 | 17분 24초 | +2분 20초 | +15.5% |
| `test_shell` | 38분 10초 | 50분 37초 | +12분 27초 | +32.6% |

Workflow 내부의 `total (run start to collect)`는 collect 도중 계산하므로 전체 완료보다 짧다. 그 값은 기준 실행 46분 52초(`2812s`), 추가 TC 실행 56분 39초(`3399s`)이며 차이는 +9분 47초다. 57분 00초와 모순되는 값이 아니다. 근거: [기준 collect](https://github.com/CUBRID/cubrid/actions/runs/40349442612/job/121692067024), [추가 TC collect](https://github.com/CUBRID/cubrid/actions/runs/40643373124/job/122684818057).

| Suite | 기준 계획 TC 수 | 추가 TC 포함 계획 수 | 차이 | shard 수 |
| --- | ---: | ---: | ---: | ---: |
| `test_medium` | 975 | 975 | 0 | 1 → 1 |
| `test_sql` | 17,630 | 17,655 | +25 | 10 → 10 |
| `test_shell` | 3,490 | 3,563 | +73 | 50 → 50 |

계획 수는 `split.meta`의 `total`이다. 비활성 TC를 포함한 보유 수나 PASS 수를 뜻하지 않는다. Medium은 TC 수 증가 없이 23초 늘었으므로, 모든 시간 차이를 신규 TC 수에 직접 대응시킬 수 없다.

## PR #7990 현재 HEAD와 비교하면

최신 성공 실행은 `/run rerun 40464422209`다. Plan에 `rerun_unrun=699`, `rerun_failed=0`, `rerun_changed=0`이 기록돼 있다. Medium·SQL은 계획 0개, shell만 699개다. Medium·SQL의 기존 PASS를 유지한 것이며, 34분 07초를 새 전체 실행 시간으로 사용할 수 없다.

| 항목 | 현재 HEAD 전체 실행: 40464422209 | 추가 TC 포함: 40643373124 | 변화 |
| --- | ---: | ---: | ---: |
| 전체 경과 시간 | 61분 42초 | 57분 00초 | −4분 42초(−7.6%) |
| `test_medium` span | 2분 59초 | 3분 24초 | +25초 |
| `test_sql` span | 14분 32초 | 17분 24초 | +2분 52초 |
| `test_shell` span | 49분 14초 | 50분 37초 | +1분 23초 |

원본 전체 실행은 shell 699개가 미실행으로 남았으므로 동일한 완료 범위의 성능 기준이 아니다. 재실행의 shell span은 30분 26초이며, 12 shard로 해당 699개를 처리했다. 두 실행 시간을 더하면 사용자가 기다린 전체 처리 비용에는 참고가 되지만, 한 번의 정상 전체 실행 시간으로 해석할 수 없다.

## 수행 비용과 shard 시작 시각

아래 누적 시간은 모든 shard의 `end - start`를 더한 값이다. 병렬 실행 자원의 점유 시간에 가까운 지표이며 CPU 시간은 아니다.

| Suite | 기준 누적 시간 | 추가 TC 누적 시간 | 변화 |
| --- | ---: | ---: | ---: |
| `test_medium` | 3분 01초 | 3분 24초 | +23초(+12.7%) |
| `test_sql` | 55분 10초 | 57분 48초 | +2분 38초(+4.8%) |
| `test_shell` | 27시간 55분 08초 | 28시간 46분 46초 | +51분 38초(+3.1%) |

순수 `Run CTP` step의 shell 누적 시간도 27시간 45분 08초→28시간 36분 13초로 +3.1%다. 반면 shell span은 +32.6%다. 기준 실행의 shell shard 시작 시각 분산은 **2분 13초**, 추가 TC 실행은 **15분 06초**다. 가장 긴 단일 shell shard 시간은 오히려 **36분 50초→35분 41초**로 줄었다. 추가 TC 실행에서 마지막에 끝난 것은 [shell shard22](https://github.com/CUBRID/cubrid/actions/runs/40643373124/job/122667129786)다.

관측상 이번 전체 완료 시간에는 shell shard의 늦은 시작이 크게 반영됐다. 구체적인 runner 공급량·autoscaler·다른 실행과의 자원 경쟁 원인은 이 자료만으로 확정하지 않는다. 동일 Engine·CTP·실행 조건으로 기존 TC와 추가 TC를 번갈아 측정하지 않았으므로, 신규 TC만의 인과적 비용은 미확정이다.

## QA와 검토할 TC 선별·후속 처리

1. **일반 CI의 대표 TC 선별:** 값 손상, 저장 상태, 트랜잭션·복구·소유권 등 중요한 회귀를 잡는 사례를 우선한다. 60초 이내의 활성 TC도 중복 검사 여부, 결함 검출 가치, 유지 비용을 검토해 통합·선별한다. 이 보고서 작성으로 실제 TC를 추가 비활성화하지는 않았다.
2. **실패 사례:** 현재 비활성 상태를 유지하고, Engine·TC·실행 환경 중 어느 원인인지 규명한다. 올바른 기대값을 유지한 수정 후 재현·정상 실행·자원 정리를 검증하고 재활성화한다. 비활성화는 결함 해결이나 PASS가 아니다.
3. **개별 60초 초과 사례:** 가치 있는 사례는 QA와 `shell-heavy` 등 별도 장시간 suite의 실행 위치·주기·조건을 협의한 뒤 이전한다. 이동 후 실제 발견·실행·판정·정리를 확인한다. 구체적인 저장소 경로나 실행 주기는 아직 합의하지 않았다.
4. **실패와 장시간이 겹치는 사례:** 원인 규명·수정을 먼저 수행하고, 통과를 확인한 뒤 적합한 실행 위치로 이전한다.

Public TC는 SQL 28쌍 중 활성 25·비활성 실패 3쌍이다. Private TC의 기존 목록은 133개 중 활성 69·비활성 64개이며, FAIL 61개와 60초 초과 8개의 중복 5개를 제외한 수다. 이후 HA 활성 4개·처음부터 비활성인 결함 재현 2개가 더해져 **현재 shell 보유량은 139개, 활성 73개, 비활성 66개**다. 기존 133개 inventory의 모수를 새 139개와 혼동하지 않는다.

근거: [public 비활성 목록](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/disabled/README.md), [private 비활성 목록과 추가 HA 사례](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/4ef07ee34219a7dce7e5c5d84a2f6c6031b10ec3/disabled/README.md). QA와의 협의·TC 선별·이전·실패 수정은 후속 작업이며 이번에는 PR body 초안에 관리 방침을 기록한다.

## 계산과 근거 확인

- `cubrid-ci 0.2.0 (dd290e9f7b9b, release)`의 `status`를 한 번 사용해 PR #7990의 현재 suite status가 run40471760533을 가리키는지 확인했다. PR 본문은 별도의 run40349442612를 가리켰다.
- `cubrid-ci`에는 임의로 지정한 run 사이의 시간 비교 명령이 없다. 따라서 별도 읽기 전용 API 증거를 수집했다. 실패 분석용 collector bundle이나 exact merge-base 비교로 표시하지 않는다.
- GitHub connector의 jobs 결과에는 timestamp가 없고 첫 페이지만 제공하므로, GitHub REST API의 attempt별 jobs를 `gh api --paginate --slurp`로 읽었다. 네 실행의 job 수는 각각 72·72·23·72이며 각 API `total_count`와 일치한다.
- 각 run의 Artifacts에서 `stamps/1/*.tsv`와 세 suite의 `plan/split.meta`를 수집했다. 총 219개, 9,726바이트다. 계획 shard 수와 stamp 수, 모든 start/end, 원본 digest, API step 시간과 비교 계산을 확인했다. Raw JSON·로그·stamp·검산 자료는 Git 밖에 보존했다.
- Suite span과 workflow 내부 total의 계산은 [workflow 리비전 d737878](https://github.com/CUBRID/cubrid/blob/d7378784f3d41208cb8d8f28d8d846298a3ef35a/.github/workflows/gha-ci.yml#L1417)의 `Wall clock`을 따랐다. 기준 실행의 [workflow 리비전 4781495](https://github.com/CUBRID/cubrid/blob/4781495f01523a3ecc5891e3377ad62cf876a1cd/.github/workflows/gha-ci.yml#L1416)도 같은 span 계산을 사용한다.

재계산할 때는 `gh api repos/CUBRID/cubrid/actions/runs/<run>`과 `gh api --paginate --slurp 'repos/CUBRID/cubrid/actions/runs/<run>/attempts/1/jobs?per_page=100'`를 읽고, 해당 run의 Artifacts에서 위 stamp와 plan을 확인한다. 시간 분석에 필요한 provenance·계획·timestamp를 확인한 범위이며, 전체 testcase 결과의 schema 검증·실패 원인 분석·새 CI 실행은 수행하지 않았다.
