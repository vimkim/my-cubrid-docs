# S04 cbrd_26354 — 합의된 첫 재현 배치 결과

2026-09-29. Work item 218. 사용자와 [실행 계약](reproduction/spec.md)을 합의한 뒤 별도 worktree 두 개에서 빌드하고, pristine 한 쌍과 observation 두 쌍을 순차 실행했다. 승인된 6회가 종료됐다. 엔진 수정, tracked testcase/answer 수정, develop 병합, 추가 실행 및 공개 게시를 수행하지 않았다.

**Feature는 QA에 보관된 case 16/18의 실제 cardinality 11/99986을 각각 3회 재현했다. 그러나 동일한 로컬 testcase에서 exact develop도 두 기대값을 모두 충족하지 못했다. 따라서 이 결과만으로 두 실패를 OOS 고유 회귀로 귀속할 수 없다.** Native 결과 검증에는 별도의 집계·XML 증거 한계가 있다.

## Cardinality 관측

| 대상 | 원본 기대값 | 보관된 feature QA 실제값 | 로컬 feature, 3/3회 | 로컬 develop, 3/3회 |
|---|---:|---:|---:|---:|
| Case 16: ORDERED NO_USE_HASH, t2가 driving side, LIMIT 10,1 | 55 | 11 | 11 | 11 |
| Case 18: NO_USE_HASH, LIMIT 200000 | 200000 | 99986 | 99986 | 100000 |

각 값은 `idx-join (inner join)` 계획의 원본 비교 대상 top-level `card`다. Cost 숫자의 masking 폭과 구별했다. 원본 테스트의 optimization level 514는 계획만 생성하므로 이 숫자를 실제 반환 행수로 해석하지 않는다. [원본 triage](triage-expectations_1ec35f8_codex.md), [매뉴얼](/home/vimkim/gh/cubrid-manual/en/sql/tuning.rst:169).

Feature는 선택한 두 숫자에 대해 정확한 QA symptom을 재현했다. Develop의 case 18은 같은 assertion 실패지만 QA actual 99986과 다른 100000이다. QA develop의 완료 결과에서 이 실패가 없었다는 기존 분류와 로컬 결과의 차이는 그대로 남긴다. 실제 QA corpus/helper SHA가 불명하므로 로컬 비교를 완전한 QA 환경 재현이라고 부르지 않는다.

## 실행 및 전체 subcase 결과

| Attempt | 모드 | Case 16 | Case 18 | 원본 subcase OK/NOK | 기록된 실행 시간(초) |
|---|---|---:|---:|---|---:|
| 01-feature | pristine | 11 | 99986 | 3 / 17 | 56.332 |
| 01-develop | pristine | 11 | 100000 | 7 / 13 | 30.688 |
| 02-feature | observation | 11 | 99986 | 3 / 17 | 31.361 |
| 02-develop | observation | 11 | 100000 | 7 / 13 | 31.253 |
| 03-feature | observation | 11 | 99986 | 3 / 17 | 32.989 |
| 03-develop | observation | 11 | 100000 | 7 / 13 | 31.448 |

모든 attempt의 `test_local.log`에 1–20 원본 비교가 순서대로 각각 한 번 기록됐다. 각 revision의 pristine/observation에서 전체 subcase verdict 벡터도 같았다. Feature OK는 13,14,15; develop OK는 6,7,13,14,15,17,19이며 나머지는 NOK다. 6,7,17,19의 로컬 verdict 차이는 추가 관측이며 이번 배치에서 원인을 진단하지 않았다. 전체 벡터와 binary hash는 [summary.json](reproduction/evidence/summary.json)에 보존했다.

## 데이터 및 통계 대조

Observation 4회 모두 원본 comparison 20 이후, 원본 cleanup 이전에 별도 read-only CSQL 진단이 종료 코드 0으로 완료됐다. 통계를 먼저 수집하고 optimization level 1에서 실제 데이터를 조회했다. 통계를 갱신하지 않았다.

| 항목 | 네 observation에서 확인한 값 |
|---|---|
| t1 실제 행수 | 100000 |
| t1 실제 NDV, col1–7 | 100000,100000,10,4,2,100,500 |
| t1 non-null count, 모든 열 | 각 100000 |
| t2 실제 행수 / 두 열 NDV / non-null count | 모두 500 |
| t1 저장 통계 heap objects / pages | 100000 / 461 |
| t2 저장 통계 heap objects / pages | 500 / 5 |
| t1 저장 NDV, col1–7 | 99298,99298,10,4,2,100,500 |
| t2 저장 NDV | 500,500 |

실제 행수·NDV·NULL 검사는 사전에 setup SQL로 정한 기준을 모두 충족했다. 저장된 col1/col2 NDV 99298과 실제 NDV 100000은 구별해야 한다. 이 차이를 데이터 손실이나 실패 원인으로 판정하지 않았다. 이 진단은 setup 검증이며 원본 20개 query 각각의 논리적 반환 결과를 검증한 것은 아니다.

Heap objects/pages, 저장 NDV, B-tree cardinality는 네 관측에서 같았다. **저장 통계 전체가 동일하지는 않다.** 일부 인덱스의 물리 페이지 수가 달랐다. 앞선 진행 설명에서 통계가 같다고 표현한 범위를 여기서 바로잡는다.

| 인덱스, total/leaf pages | 02-feature | 02-develop | 03-feature | 03-develop |
|---|---|---|---|---|
| t1 idx | 213/211 | 211/209 | 213/211 | 210/208 |
| t2 idx | 3/1 | 4/2 | 4/2 | 4/2 |

이 차이를 통제하거나 인과적으로 검증하는 후속 실험은 수행하지 않았다. [Feature 진단](reproduction/evidence/02-feature-data-stats.log), [develop 진단](reproduction/evidence/02-develop-data-stats.log), [마지막 develop 진단](reproduction/evidence/03-develop-data-stats.log).

## Native runner 증거와 한계

명시적으로 native shell runner와 containment를 사용했다. 각 attempt에서 exact target만 dispatch/completed 파일에 한 줄씩 기록됐고, 원본 subcase 20개 및 testcase failure가 로그에 남았다. 그러나 다음 두 문제 때문에 합의한 focused helper의 완전한 artifact 검증을 통과했다고 주장하지 않는다.

1. 기존 `LINUX_NOT_SUPPORTED` macro 제외 정책을 유지한 전체 corpus discovery가 선택 목록 밖의 21개 skip을 집계했다. 모든 attempt에서 `Total=22, Executed=1, Success=0, Fail=1, Skip=21`이다. Focused helper는 `total case count is 22, expected 1`로 종료 코드 1을 반환했다. 제외 정책이나 검증 조건을 바꾸지 않았다.
2. 6개 `test-shell.xml` 모두 UTF-8 선언과 맞지 않는 바이트를 포함해 XML parser가 invalid token으로 거부했다. 해당 바이트는 failure CDATA의 shell trace 내 normalization 문자열 부근에 있다. 원본 XML은 보정하지 않고 보존했다. Decoded excerpt의 대상 failure 기록은 확인했지만 정상 JUnit 파싱 증거로 취급하지 않는다.

Native process exit는 모두 0이었다. 이것을 testcase PASS로 해석하지 않았다. 원본 verdict는 모두 NOK이고, observation의 별도 symptom oracle도 두 card mismatch를 검출하여 종료 코드 1이었다. 데이터 진단의 PASS가 testcase NOK 또는 native proof gap을 덮지 않는다. [첫 native 검증 로그](/home/vimkim/tmp/oos-qa-reproduction-1ec35f8/01-feature/verify.log), [마지막 native 집계](/home/vimkim/tmp/oos-qa-reproduction-1ec35f8/03-develop/CTP/result/shell/current_runtime_logs/test_status.data).

[check_symptom.py](/home/vimkim/tmp/oos-qa-reproduction-1ec35f8/check_symptom.py)는 실제 데이터 setup 기준과 원래 기대 card 55/200000을 독립적으로 확인한다. 원본 answer를 복사해 사용한 [offline checker control](/home/vimkim/tmp/oos-qa-reproduction-1ec35f8/checker-controls/expected-oracle/README.txt)은 checker 자체의 기대 입력 검증이다. 엔진 실행이나 testcase PASS를 뜻하지 않는다. 원본 answer와 실제 attempt는 수정하지 않았다.

## 빌드·자산 provenance

| 항목 | Feature | Develop |
|---|---|---|
| Engine HEAD | `1ec35f86c5e43b9ca86d81e202c68899f8ce4f21` | `e1c3db19800a0170942cec8b23cac4705efbb6e3` |
| Worktree | `/home/vimkim/gh/cb/oos-qa-feature-1ec35f8` | `/home/vimkim/gh/cb/oos-qa-develop-e1c3db1` |
| Source install | `/home/vimkim/.cub/install/oos-qa-feature-1ec35f8/debug_gcc` | `/home/vimkim/.cub/install/oos-qa-develop-e1c3db1/debug_gcc` |
| CCI submodule pin | `bd86063a5bd481f0e22bf07c8a76bf736f86443a` | `79d0888c26a2543d31f53eb7b6c9738db110fff4` |

두 빌드 모두 같은 호스트에서 live prepare/configure/build workflow로 완료됐다. Preset `debug_gcc`, GCC/G++ 11.5.0, Debug, `-O0 -ggdb3 -fno-omit-frame-pointer`와 추가 warning flags가 일치했다. CMakeCache/compile_commands/build/install 기록을 [builds](/home/vimkim/tmp/oos-qa-reproduction-1ec35f8/builds)에 보존했다. `UNIT_TESTS=OFF`; `UNIT_TEST_OOS=ON`은 feature에서 BOOL option이고 develop에서는 UNINITIALIZED entry다. CTest는 실행하지 않았다. CCI build가 생성한 `win/cci_version.h` 변경만 dedicated worktree의 submodule dirt로 남았고 diff를 보존했다. 엔진 수정을 수행한 것은 아니다.

Supporting private testcase corpus는 `1274a4d6462a3d5ae5daeb004e042f89496991d8`이며 종료 시에도 clean이었다. CTP asset HEAD는 `9c62858b10005d721546cc007be260844033b9e9`; 기존 local modifications를 그대로 snapshot하여 양쪽에 공통 사용하고 원본 자산을 수정하지 않았다. 실제 QA 배포 corpus/helper SHA는 여전히 unknown이다.

Native testkit은 `cubrid-testkit dev`, SHA256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`였다. Go build metadata에는 vcs revision `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`, modified=true가 기록됐다. [Metadata](reproduction/evidence/testkit-go-build.txt).

각 attempt는 installation/CTP/HOME을 별도 복사하고 CUBRID 내부에 빈 database registry를 만들어 사용했다. Sequential, one slot, retry=0, timeout=1200초, scenario_disk=on, testcase update/continuation=false였다. Path를 치환한 기본 shell config는 6회 일치했다. 네 observation의 testcase copy overlay/helper diff/data probe SQL/effective cubrid.conf hash는 각각 일치했다. 진단 helper는 원본 비교를 호출하고 원본 반환값을 유지했다. 모든 runtime은 `TESTKIT_NATIVE=shell`, `TESTKIT_CONTAIN=1`이었다.

Attempt manifest에는 source/installed commit 검증, binary hashes, resolved paths, config hash, 명령 및 exit status가 있다. Revision별 binary hash가 반복 간 일치했다. Orchestration에는 로그 보존 위치, 복사된 과거 결과 분리, 별도 symptom checker 연결 등의 변경이 있었다. Observation 네 manifest에는 해당 script hash가 기록됐으나 첫 pristine 두 manifest에는 당시 orchestration hash가 기록되지 않았다. 이 provenance 누락도 남긴다. 원본 testcase SQL/answer는 변경하지 않았다. [현재 orchestrator](/home/vimkim/tmp/oos-qa-reproduction-1ec35f8/run_attempt.py), [artifact cross-check](/home/vimkim/tmp/oos-qa-reproduction-1ec35f8/summarize.py), [활성 결과 파일 hashes](/home/vimkim/tmp/oos-qa-reproduction-1ec35f8/active-evidence-sha256.json), [post-batch host capture](/home/vimkim/tmp/oos-qa-reproduction-1ec35f8/host-provenance.json).

## R01 및 후속 판단 경계

R01은 증거 확인만 수행했다. Original vacuum core 574686 및 reader core 575361의 listing/stack 관련 기존 raw page는 남아 있으나 core memory, matching QA executable/libraries, 같은 시점 DB/volumes/WAL, 정확한 corpus/grammar/seed/generated workload가 확보되지 않았다. QA archive 접근 경로도 확립되지 않았다. Core 링크는 issue-report endpoint여서 호출하지 않았고 RQG runtime도 시작하지 않았다. [Acquisition manifest](reproduction/evidence/rqg-acquisition-manifest.json).

S04의 선택 symptom은 반복해서 관측됐지만, OOS causal diagnosis와 answer 정당성 판단은 미완이다. 다음 판단에는 실제 QA testcase/helper/config identity를 확정해 로컬 develop도 실패하는 차이를 설명하는 증거가 필요하다. Native 집계/XML 문제도 별도 증거 품질 이슈로 남는다. 이번 배치에서 answers를 갱신하거나 엔진 원인을 단정하지 않았다.

모든 원본·관측 attempt와 copied installation/CTP를 `/home/vimkim/tmp/oos-qa-reproduction-1ec35f8/`에 유지한다. Testcase의 원래 DB cleanup은 유지했으므로 consistent DB/WAL snapshot이 있는 것은 아니다. Cleanup은 수행하지 않았다.

## Publication bundle

이 문서 묶음에는 원래 QA 분석·triage 문서, [handoff](reproduction/handoff.md), [재현 계약](reproduction/spec.md), [결정 기록](reproduction/review.md), [조사 용어](reproduction/CONTEXT.md), compact 실행 집계와 네 데이터·통계 진단 로그가 포함된다. 위 `/home/vimkim/...` 절대 경로 링크는 별도로 보존한 로컬 원본 증거이며 Git 저장소에 포함한 파일을 뜻하지 않는다. Copied installation/CTP, raw QA archives, core/DB/WAL은 게시하지 않았다.
