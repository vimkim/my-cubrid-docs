# 공용 metadata helper 이동과 선별 후 SHOW 검증

작성·갱신일은 2026-11-02, Asia/Seoul이다. Work662의 독자는 CBRD-26659 TC 작성자와 리뷰어다. [Engine PR #8128](https://github.com/CUBRID/cubrid/pull/8128), [일반 TC PR #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365)와 연결된다.

## 결론과 범위

질문은 metadata 소비자만 선별해도 `policy_metadata.sh`가 남으며 원래 계약을 유지하는지다. 일반 TC에서 helper를 `oos_common`으로 옮기고 네 호출 인자를 바꿨다. Parser 출력·종료 상태는 독립 기대값 17개와 이전 버전에 대해 일치했다. 실제 CI 선별 함수를 사용한 같은 기본 검증 명령은 수정 전 교차 소비자 네 곳에서 실패했고 수정 후 통과했다. 선별 후 입력 64개로 실행한 원문 SHOW 대표는 1 PASS·0 FAIL·0 SKIP이다.

일반 TC 커밋 [`41eae6a9c30f98434521c44476aa27e768e3332b`](https://github.com/CUBRID/cubrid-testcases-private-ex/commit/41eae6a9c30f98434521c44476aa27e768e3332b)을 정규 `tc/pr-8128` head에 게시했다. 이후 [전체 CI 41394321292](https://github.com/CUBRID/cubrid/actions/runs/41394321292)를 한 번 요청했다. 종료 판정은 아래 CI 절에 기록한다.

Schema·partition의 native 실행, TDE helper·AWK 이동, 비활성 TC 재활성화는 이번 범위에 포함하지 않는다. 앞선 native 두 시도의 준비 환경 NOK를 보존한다. SHOW는 이전에 검증한 같은 대표이므로 과거 shell 61개의 서로 다른 현재 검증 수를 늘리지 않는다. 나머지 59개, 그중 policy helper 그룹 38개와 기존 종료 지연 조사는 남는다.

## 기준과 변경

| 대상 | 커밋·상태 | 이번 변경 |
| --- | --- | --- |
| Engine `vimkim/cubrid`, `CBRD-26659-oos-testcases-handover` | `e3589ae42d42b04eb020e1ae43e165b01d31b12a`, PR base `feature/oos-merge` | 없음. 기존 `cubrid-cci`·`cubrid-jdbc` 변경 유지 |
| 일반 `CUBRID/cubrid-testcases-private-ex`, `tc/pr-8128` | `6334dc6cd74683ca6ba10439372a21bd36b453d3` → `41eae6a9c30f98434521c44476aa27e768e3332b` | Helper 이동 하나·호출 인자 네 곳 |
| Public `CUBRID/cubrid-testcases`, `tc/pr-8128` | `b038c424b6a8d078671132e2369040493a5fc1f6` | 없음 |
| Heavy `vimkim/cubrid-testcases-private-ex`, remote `tc/pr-8128`, PR #4627 | `81e60724a30431282c08ae1f677bf8cefb3d95d7` | 없음 |
| 선별 함수 소스 `cubrid-dockerfiles-cubridci` | `155c265eb6e3deef49ce828e6f2b5846d3a9abf5`, `docker/ci/docker-entrypoint.sh` | 고정 bytes를 복사 fixture에 실행 |

다음 경로는 일반 TC의 `shell/_40_guava` 기준이다. Helper는 기존 `cbrd_26659_policy_contract/cases/policy_metadata.sh`에서 [`oos_common/policy_metadata.sh`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/41eae6a9c30f98434521c44476aa27e768e3332b/shell/_40_guava/oos_common/policy_metadata.sh)로 이동했다. 내용 525바이트, Git mode `100644`, SHA-256 `1d5df9878f4b3a5048b5458171043e513a69a4454e3744b448284b322d5ea048`은 그대로다.

| 호출자 | 수정 위치 | 새 인자 |
| --- | --- | --- |
| [`oos_common/oos08_controller.sh`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/41eae6a9c30f98434521c44476aa27e768e3332b/shell/_40_guava/oos_common/oos08_controller.sh#L86) | `ddl_snapshot` | `../../oos_common/policy_metadata.sh` |
| [`cbrd_26659_show_contract/cases/show_controller.sh`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/41eae6a9c30f98434521c44476aa27e768e3332b/shell/_40_guava/cbrd_26659_show_contract/cases/show_controller.sh#L79) | `metadata` | 같은 인자 |
| [`cbrd_26659_policy_contract/cases/policy_controller.sh`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/41eae6a9c30f98434521c44476aa27e768e3332b/shell/_40_guava/cbrd_26659_policy_contract/cases/policy_controller.sh#L62) | 기존 owner의 `metadata` | 같은 인자 |
| [`cbrd_26659_partition_lifecycle_common/controller.sh`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/41eae6a9c30f98434521c44476aa27e768e3332b/shell/_40_guava/cbrd_26659_partition_lifecycle_common/controller.sh#L86) | `ddl_snapshot` | 같은 인자 |

Controller는 CSQL 출력 파일을 helper에 전달하고, helper가 내보낸 완전한 DDL JSON 문자열을 snapshot 비교에 쓴다. 인자가 잘못됐거나 CSQL 오류·DDL 행 부재·복수 후보가 있으면 실패해야 한다. CLI, parser, assertion, 원래 진입점 bytes·mode와 활성·비활성 선택은 유지했다. 일반 OOS 활성 31개와 heavy 38개 선택도 유지한다. 공용 helper를 특정 TC의 `cases` 밖에 두어 owner가 shard에서 빠져도 소비자의 의존 파일이 남게 했다.

## Parser와 실제 선별 검증

[검증기](tools/verify-policy-metadata-relocation.py)는 기존 커밋과 현재 파일을 비교하고, 고정된 실제 CI 함수의 `keep case`를 복사 fixture에서 실행한다. 원래 비활성 진입점은 scratch에서만 원문 그대로 투영한다. [이전 감사](CBRD-26659-helper-dependency-audit_20261031_6334dc6_codex.md)의 리비전 한계와 이번 실행 근거를 구분한다.

독립 parser fixture 17개는 완전한 인용 DDL과 줄바꿈, CSQL 보고 텍스트, 인자·파일 누락·빈 파일, ERROR/FATAL 변형, 행·DDL 후보 개수, 잘못된 인용·접두사를 다룬다. 성공의 완전한 stdout·exit 0과 거부 입력의 nonzero 기대값을 먼저 고정한다. 이전·현재 parser의 stdout·stderr·정확한 exit도 서로 비교한다. 두 버전의 동치성만 검사하지 않는다.

실제 선별은 각 최종 gate마다 9회다. Schema SA·CS, partition rejection, SHOW의 owner 제외 4회와 owner 포함 대조 4회, policy owner 단독 1회다. Controller가 전달하는 helper 인자를 읽고 해당 `cases` 작업 경로에서 해석한다. 정의만 존재하는 미호출 lifecycle 분기에 native 실행 credit을 주지 않는다.

| Gate | 관측 결과 |
| --- | --- |
| 최종 수정 전 | 기본 생존 검증 exit 1. 교차 소비자 네 곳의 helper 삭제 검출. Parser 기대값 17개 통과·owner 포함 대조 정상 |
| 수정 후 | 같은 명령·같은 검증기 SHA-256으로 exit 0. 선별 9회와 parser 17개 통과 |
| TC 커밋 후 | `41eae6a9c`에서 재실행 exit 0. 이동과 네 인자 외 변경 없음 |

수정 전·후·커밋 후 검증기 SHA-256은 `da2facdf4cc14abb3dcb53399e5e559f46b5820f9a5421175caf55813533b044`다. 초기 초안의 동일한 삭제 실패 기록도 보존한다. 최종 수정 전 실행에 앞서 커밋 이후 replay를 허용하는 provenance guard와 이동 양쪽을 보는 diff 처리를 바로잡았다. 생존 기대값이나 parser 기대값은 완화하지 않았다. 초안과 최종 gate의 별도 실행을 하나로 합산하지 않는다. 이 선별·합성 parser 횟수는 DB testcase PASS 수가 아니다.

문서 저장소 루트에서 다음처럼 재실행한다. `--artifacts`에는 원본 TC 밖의 새 산출물 경로를 전달한다.

```bash
mkdir -p /home/vimkim/temp/cbrd-26659-metadata-replay
python3 cbrd-26659/tools/verify-policy-metadata-relocation.py \
  --regular /home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8128 \
  --ci-source /home/vimkim/gh/cubrid-dockerfiles-cubridci \
  --artifacts /home/vimkim/temp/cbrd-26659-metadata-replay
```

## 원문 SHOW 대표의 native 결과

대표는 `shell/_40_guava/cbrd_26659_show_contract/cases/cbrd_26659_show_contract.sh`다. 원래 `disabled/failing/.../cbrd_26659_show_contract.sh.disabled`에서만 scratch에 투영했다. SHA-256 `632ad5def8ba41eb8173ffea71d0df0ed64006c7270d3a1599bda4adf532ff9f`, mode `0755`와 assertion을 유지했다. Owner를 제외한 실제 선별 결과 64개 파일 전부를 실행 corpus에 복사하고, 소스·복사본·최종 TC 커밋의 bytes·mode를 대조했다. `policy_contract/cases`는 실행 corpus에 없다.

Host 기본 debug 설치는 source `e3589ae`와 installed `1ef86a7` 불일치로 실행 전에 거부했다. Mismatch 예외를 사용하지 않았다. 보존된 `/home/vimkim/temp/oos-tc-runtime-20261028/engine/CUBRID`의 optdebug runtime을 시도별로 복사했다. 실행 바이너리 5개와 `libcascci.so`의 6개 hash를 producer·실행 복사본과 대조했다. 기존 성공 SHOW snapshot과 같은 runtime bytes다. 이 일치만으로 전체 source provenance를 인증하지 않는다.

Native testkit `/home/vimkim/.local/bin/testkit`의 SHA-256은 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`다. Build metadata는 vcs `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`, `vcs.modified=true`다. CTP는 기존 작업 변경이 있는 로컬 asset checkout에서 시도별로 복사했다. Legacy CTP runner를 호출하지 않았다. Binary hash·실제 case 환경과 결과를 근거로 삼으며, 수정된 도구 source와 binary의 완전한 대응은 주장하지 않는다.

각 시도는 별도 CUBRID·CTP·HOME·tmp·native cache·slot 경로, fresh DB registry를 썼다. 복사되어 온 registry·결과는 별도 이름으로 보존했다. `TESTKIT_NATIVE=shell`, `TESTKIT_CONTAIN=1`, slot 1개, `scenario_disk=on`, retry 0, continue·answer update 없음, case patch 없음이다. Testcase와 전체 native 명령에 120초를 설정했고 전체 명령의 TERM 뒤 10초 종료 유예를 뒀다. 원문 controller 내부의 기존 300초 설정은 수정하지 않았다.

| 시도 | 실제 결과 | 판정과 다음 setup 선택 |
| --- | --- | --- |
| `native01` | Runner exit 0, artifact verifier exit 1, 1 NOK. 전체 명령 50.751초 | Metadata 호출 전 DB readiness 실패. 최초 UNIX socket bind EINVAL 뒤 reconnect·descriptor 고갈. 준비 실패를 보존하고 경로 길이 probe 수행 |
| `native02` | Runner exit 0, artifact verifier exit 1, 1 NOK. 전체 명령 53.264초 | 부모의 짧은 `CUBRID_TMP`가 실제 case에 전달된다는 전제를 반증. Retained identity는 긴 `$CUBRID/tmp`를 가리킴 |
| `native03` | Runner·focused verifier·commit 입력 검증 exit 0. 1 PASS·0 FAIL·0 SKIP. 전체 명령 34.521초 | 짧은 물리 install root 사용. 원문 assertion 8개 OK, controller journal 7개 PASS, controller exit 0, owned cleanup 1, framework config 복원 assertion OK |

시간은 제한 안에 실제 명령이 종료했는지 확인하는 관측값이다. 성능 비교나 속도 개선 수치가 아니다. Runner exit 0만으로 앞선 두 시도를 PASS로 취급하지 않는다.

### 준비 환경 오류의 구분

`probe-socket-path.py`는 DB를 띄우지 않고 같은 C bind 구성으로 경로 길이만 대조했다. 최초 111바이트 pathname은 원래 길이를 반영한 sockaddr 길이 114로 bind에 전달되어 errno 22를 냈다. 짧은 102바이트 대조는 성공했고 probe socket을 제거했다. Engine `e3589ae`의 [`filesys_temp.cpp:112`](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/base/filesys_temp.cpp#L112), [`master_connector.cpp:451`](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/connection/master_connector.cpp#L451), [`tcp.c:893`](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/connection/tcp.c#L893)가 temp 경로 선택·이름 조합·bind 길이의 근거다.

두 번째 retained `show.identity.log`는 runner가 부모의 별도 tmp 대신 `$CUBRID/tmp`를 선택했음을 보인다. 따라서 세 번째는 전체 install root를 줄였다. 실제 root는 `/home/vimkim/temp/w662-meueefsg/native03`이며, canonical 산출물의 `native03` symlink가 이 경로를 가리킨다. Symlink만 짧게 만드는 방식이 아니다. 동일한 TC 64개·runtime bytes를 유지했고 실제 case의 tmp를 검증했다. Engine 코드나 testcase 기대값은 수정하지 않았다.

`native03/setup-before-native.json`은 실행 전 빈 registry, 보존한 원본 registry 파일과 hash, 예상 tmp와 7자리 PID의 socket 경로 길이를 기록한다. 최초 시도는 preparation 실행과 초기 `registry=absent` 로그가 fresh registry 근거이며 전용 실행 전 inventory가 없다. 사후에 실행 전 증거를 만들어 넣지 않았다.

### 결과 자료와 정리

[Native 검증기](tools/verify-policy-metadata-native.py)는 입력 64개, 예상·실제 dispatch와 finish 목록, status와 JUnit의 정확한 1 PASS, 종료 상태와 관측 시간을 검증한다. 실제 assertion 행은 줄 시작으로 고정해 xtrace의 echo 중복을 세지 않는다. Controller의 완전한 DDL JSON 출력 33개는 모두 before·final과 같다.

Case-log 수집은 독립 `.json`·`.before` 파일을 보존하지 않는다. DDL은 retained `show.controller.log`의 `EVIDENCE=...ddl.json` 완전한 출력으로 검증했다. Config 복원은 원문 assertion 8과 controller 정리 결과가 근거다. 해당 파일들이 따로 보존됐다고 가정한 검증기 초안 두 실패는 산출물 관측 오류로 남겼다. 이를 고치기 위해 testcase assertion을 바꾸거나 native를 다시 실행하지 않았다.

세 시도 모두 1초 간격의 두 read-only residue scan을 보존한다. 관측한 owned process·namespace holder, 실행 경로 아래 host mount·UNIX socket 잔류가 없다. 첫 두 시도의 case 자체 `owned_cleanup=0`과 외부 containment 정리 결과를 구분한다. 별도 부모 cleanup signal은 보내지 않았다. 모든 host IPC 객체의 부재를 인증하는 검사는 아니다.

다음 명령은 보존된 세 번째 결과를 읽으며 native 실행을 시작하지 않는다.

```bash
python3 cbrd-26659/tools/verify-policy-metadata-native.py \
  --attempt /home/vimkim/temp/cbrd-26659-policy-metadata-relocation-20261102/native03 \
  --regular /home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8128 \
  --engine /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover \
  --producer /home/vimkim/temp/oos-tc-runtime-20261028/engine/CUBRID \
  --tc-commit 41eae6a9c30f98434521c44476aa27e768e3332b
```

## TC 게시와 CI

`bash -n`으로 이동 helper와 네 controller를 확인했고 `git diff --check`를 통과했다. 커밋은 helper 100% rename과 인자 네 줄 변경만 포함한다. 정규 TC checkout은 커밋 뒤 clean이다. Push 뒤 원격 `refs/heads/tc/pr-8128`와 PR #4365 head가 모두 `41eae6a9c`임을 확인했다. TC PR을 merge·close하거나 branch를 삭제하지 않았다.

Feature baseline ancestry 검사는 public·private 둘 다 PASS였다. 진행 중 같은 PR CI와 새 `/run` 요청이 없는지 다시 확인한 뒤 [`/run all` 댓글](https://github.com/CUBRID/cubrid/pull/8128#issuecomment-6569836762)을 정확히 한 번 게시했다. Engine head가 같아도 새 TC push 뒤 한 번 CI를 실행한다는 사용자 지침과 승인한 Work662 범위를 적용했다. Testtools override는 없다.

CI plan 실제 checkout은 Engine `e3589ae42d42b04eb020e1ae43e165b01d31b12a`, public `b038c424b6a8d078671132e2369040493a5fc1f6`, private `41eae6a9c30f98434521c44476aa27e768e3332b`다. CTP는 `CUBRID/cubrid-testtools` develop `1c6b224d6f48eea01b8b4efa9f64f2521c40f2fd`다. Issue-comment workflow 자체의 `head_sha`는 develop `1684945ed05fdd37be55a706390d976c24ef3f9b`로 Engine 테스트 대상과 구분한다.

**CI 종료 기록은 대기 중이다.** 새 실행의 build debug·release, shell·SQL·medium 다섯 context pickup을 확인했다. 종료 후 run과 context 결과를 대조해 이 문단을 갱신한다. CI 종료 뒤에는 추가 TC·source 수정, push 또는 rerun을 하지 않는다.

TC Merge Gate는 현재 check 목록에 표시되지 않는다. `gh pr checks --required`의 “no required checks reported”도 해당 CLI 조회 결과일 뿐 required rule 부재나 Gate PASS 근거가 아니다. Public #3688·private #4365의 실제 리뷰·병합은 사람의 후속 작업이다. 이번 CI가 성공하더라도 기존 SQL 3,533/3,531건 집계 정합성 미인증, heavy 정기 실행 경로와 비활성 TC 전체 검증은 별도로 남는다.

## 보존 자료와 후속 작업

Raw 산출물의 canonical root는 `/home/vimkim/temp/cbrd-26659-policy-metadata-relocation-20261102`다. 다음 자료는 Git에 넣지 않고 해당 root에 보존한다.

| 자료 | 용도 |
| --- | --- |
| `baseline.json`, `authorization.json`, `decisions.tsv` | 원래 head·변경·승인 범위와 append-only 의사결정 기록 |
| `before-parent.json`, `after-parent.json`, `postcommit-proof.log`, `metadata-relocation-*/result.json` | 같은 생존 gate의 전후 차이, parser 기대값·전체 inventory |
| `proof-script-v1.py`, `proof-script-v1.json`, `before-gate.log` | 초기 proof 초안과 수정 전 실패 보존 |
| `host-preflight.log`, `testkit-build-metadata.log`, `native01-result.json`부터 `native03-result.json`, 각 attempt | 설치 선택, 시도별 입력·환경·log·verdict·정리 |
| `probe-socket-path.py`, `socket-path-probe.json`, `native03-path.json` | UNIX socket 길이 대조와 짧은 물리 경로 선택 |
| `native-proof-v1.*`, `native-proof-v2.*`, `native-proof-parent.json` | 관측 오류의 보존과 최종 commit 대응 검증 |
| `tc-commit.json`, `tc-committed.patch`, `tc-publication.json`, `tc-push.log` | 검토한 변경과 게시 head 대응 |
| `ci-preflight`, `ci-trigger`, `ci-status` | Baseline 검사, 단일 게시 receipt, CI plan·종료 근거 |

Git에 남기는 지원 파일은 parser·실제 선별을 재검증하는 `verify-policy-metadata-relocation.py`와 retained native 결과·최종 TC commit 대응을 검사하는 `verify-policy-metadata-native.py` 두 개다. 첫 local docs 커밋 이후 보강한 native 검증은 실제 runtime tmp와 retained 자료 형식을 반영한다. Report·checklist·README와 함께 결과를 재검토하는 도구이므로 보존한다. Raw log·inventory·실험 실행 wrapper는 선택하지 않았다.

다음 수리 단위는 [Work654 감사](CBRD-26659-helper-dependency-audit_20261031_6334dc6_codex.md)에 따른 일반·heavy TDE helper와 AWK의 공용 이동이다. JSON source와 모든 호출 경로, AES 분기와 비활성 wrapper의 별도 sibling 의존성을 포함해 먼저 범위를 확정해야 한다. Metadata 소비자의 나머지 native 실행·재활성화와 전체 Work456 완료는 후속 검토로 남는다. Docs main 통합·게시·task worktree 정리는 로컬 결과 검토 뒤 별도 승인을 받는다.
