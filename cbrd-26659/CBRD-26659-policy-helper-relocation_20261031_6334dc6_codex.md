# CBRD-26659 공용 policy helper 이동과 shard 선별 후 검증

작성일은 2026-10-31, Asia/Seoul이다. QA 담당자와 TC 리뷰어가 공용 checker의 배치 수리와 실제 TC 검증 범위를 구분할 수 있도록 작성했다. 대상은 [Engine PR #8128](https://github.com/CUBRID/cubrid/pull/8128), [일반 TC PR #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365), [heavy TC PR #4627](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4627)이다.

**`policy_ddl.sh`를 개별 TC의 `cases` 밖으로 옮기고 일반 호출자 7곳과 heavy 복사본 1곳을 함께 수정했다. 실제 선별 코드로 수정 전 helper 삭제와 수정 후 보존을 확인했다. 선별 후 입력을 사용한 원문 대표 TC는 전체 native 명령까지 1 PASS다.** 앞선 실행은 TC assertion이 성공이어도 전체 명령이 timeout되어 미완료로 보존한다. 이 종료 지연의 원인은 아직 미확정이다.

[이전 조사](CBRD-26659-policy-helper-pruning_20261030_e3589ae_codex.md)의 역사적 원인 추론을 현재 수리 결과와 구분한다. 이번 단위는 [체크리스트](CBRD-26659-todo-checklist_20261029_codex.md)의 helper 이동·호출자 수정·대표 검증까지다. 나머지 38개 실행과 비활성 TC 재활성화는 포함하지 않았다.

## 변경한 계약과 고정 리비전

| 대상 | 이전 리비전 | 현재 리비전·상태 |
| --- | --- | --- |
| Engine `vimkim/cubrid` | `e3589ae42d42b04eb020e1ae43e165b01d31b12a` | 변경 없음. 로컬 producer는 optdebug이며 기존 CCI/JDBC 수정 보존 |
| 일반 TC `CUBRID/cubrid-testcases-private-ex:tc/pr-8128` | `a229e1978abc4cc6c280783703c03f75524c0f05` | [`6334dc6cd74683ca6ba10439372a21bd36b453d3`](https://github.com/CUBRID/cubrid-testcases-private-ex/commit/6334dc6cd74683ca6ba10439372a21bd36b453d3) push·실제 원격 ref 일치 확인 |
| Heavy TC `vimkim/cubrid-testcases-private-ex:tc/pr-8128` | `631e3fd3cbc202cec45b56ae6cec7e4f1c86e2f1` | [`81e60724a30431282c08ae1f677bf8cefb3d95d7`](https://github.com/vimkim/cubrid-testcases-private-ex/commit/81e60724a30431282c08ae1f677bf8cefb3d95d7) push·실제 원격 ref 일치 확인 |
| 파일 선별 소스 `CUBRID/cubridci` | `155c265eb6e3deef49ce828e6f2b5846d3a9abf5` | 수정하지 않은 `docker/ci/docker-entrypoint.sh`의 `keep case` 실행 |
| Native testkit | 설치 바이너리 SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a` | 두 실제 실행에서 동일. metadata `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`, `vcs.modified=true`; 정확한 build-time 소스 대응은 미인증 |
| Local CTP 자산 | `9c62858b10005d721546cc007be260844033b9e9`, 기존 수정이 있는 checkout | `fixed01`에 복사한 snapshot을 `fixed02`에도 파일 단위로 대조해 사용 |
| Public TC | `b038c424b6a8d078671132e2369040493a5fc1f6` | 이번 변경 없음. CI 계획에서도 이 리비전 확인 |

Checker는 `bash policy_ddl.sh LOG NAME=POLICY...`로 실행한다. 비어 있지 않은 `SHOW CREATE TABLE` 결과의 한 행·한 DDL을 확인하고, 호출자가 독립적으로 지정한 열과 `DEFAULT|FORCE_OUTLINE|PREFER_INLINE`을 비교한다. `DEFAULT`는 명시적 STORAGE 절이 없어야 하며, 다른 policy는 해당 절이 정확히 하나여야 한다. 성공하면 열별 policy JSON을 출력한다. 오류 처리, 인자 순서, 로그 경로, soft/fatal 판정은 유지했다.

두 suite 모두 `_40_guava/cbrd_26659_schema_policy/cases/policy_ddl.sh`를 `_40_guava/oos_common/policy_ddl.sh`로 이동했다. 각 suite의 prefix는 `shell`과 `shell_heavy`다. Checker는 1,493바이트·mode `100644`·SHA-256 `99bb263ae729f3f02745f88601b86653813d136476af007c2417fae6aedd024c`로 원본과 동일하며 Git도 100% rename으로 판정했다. 이전 경로는 삭제했고 fallback이나 호환용 복사본은 추가하지 않았다.

일반 TC의 다음 7곳에서 helper 경로 문자열만 바꿨다. 아래 경로는 `shell/_40_guava/` 기준이다. TC의 `cases`를 CWD로 유지해 기존 상대 로그 경로도 유지한다.

| 호출자 | 변경한 Bash 인자 |
| --- | --- |
| `cbrd_26659_schema_policy/cases/cbrd_26659_schema_policy.sh` | `policy_ddl.sh` → `../../oos_common/policy_ddl.sh` |
| `cbrd_26659_policy_contract/cases/policy_controller.sh` | `../../cbrd_26659_schema_policy/cases/policy_ddl.sh` → `../../oos_common/policy_ddl.sh` |
| `cbrd_26659_partition_lifecycle_common/controller.sh` | 같은 상대 경로 변경 |
| `cbrd_26659_partition_lifecycle_common/lifecycle.sh` | 같은 상대 경로 변경 |
| `oos_common/oos08_controller.sh` | 같은 상대 경로 변경 |
| `oos_coverage_gaps/controller.sh` | 같은 상대 경로 변경 |
| `oos_utility/policy_roundtrip.sh` | `$here/../cbrd_26659_schema_policy/cases/policy_ddl.sh` → `$here/../oos_common/policy_ddl.sh` |

Heavy 복사본의 `shell_heavy/_40_guava/oos_coverage_gaps/controller.sh`도 같은 경로 변경을 적용했다. `oos_common/README.md`에 날짜와 이동 내용을 덧붙였다. 최초 이관의 `pr8128-transfer.tsv`는 `631e3fd` 시점의 경로·해시 기록으로 그대로 보존했다. 현재 변경의 검증은 새 relocation 스크립트가 담당한다.

일반 활성 OOS 진입점 31개와 heavy 진입점 38개의 집합은 그대로다. 모든 비활성 입력·답안·manifest도 유지했다. Heavy branch의 기존 일반 `shell` tree는 수정하지 않았다. Source Engine, public TC, PR 본문, JIRA는 변경하지 않았고 TC PR 병합·종료·branch 삭제도 하지 않았다.

## 실제 파일 선별의 수정 전·후 대조

사용한 [`keep_cases` 소스](https://github.com/CUBRID/cubridci/blob/155c265eb6e3deef49ce828e6f2b5846d3a9abf5/docker/ci/docker-entrypoint.sh#L1045-L1070)는 선택된 진입점의 부모 `cases`만 남기고 다른 최외곽 `cases`를 삭제한다. Shell 의존 관계를 추적하지 않는다. 새 helper의 소유 디렉터리 `oos_common`은 `cases` 밖이어서 이 규칙으로 삭제되지 않는다.

수정 전에 새 검증 스크립트의 기본 보존 검사를 실행했다. Helper는 선별 전 존재했지만 실제 `keep case` 실행 후 사라져 `regular current controller helper missing after keep`로 exit 1을 반환했다. 같은 기본 검사를 코드 변경 뒤 다시 실행해 exit 0을 확인했다. 기대하는 성공을 바꾸는 옵션은 사용하지 않았다.

| 파일시스템 입력 | 선택 목록 | helper 선별 전 | helper 선별 후 |
| --- | --- | --- | --- |
| 일반 원본 `a229e19` | 과거 shard 13의 원본 72개 경로 목록 | 존재 | 누락 |
| 일반 수정 `6334dc6` | 같은 목록 | 존재 | 새 공용 위치에 존재 |
| Heavy 원본 `631e3fd` | 대표 `gap_recreate` 한 개의 생성한 집중 선택 목록 | 존재 | 누락 |
| Heavy 수정 `81e6072` | 같은 집중 선택 목록 | 존재 | 새 공용 위치에 존재 |

원본 shard 목록은 SHA-256 `91ced695f3703410067a2a9bb89bb7475bd389c5bb2436e25dde8c922ff825be`, entrypoint는 `55965b9c36c67c4f4330b7954202ea292eb617b9139f9bfa46a6f27d283557d2`로 대조했다. 원래 schema-policy 소유 TC는 선택 목록에 없다. 대조마다 별도 scratch fixture를 만들었다.

일반 fixture는 CTAS 대표와 공용 의존 파일만 투영한 뒤 원본 목록을 적용한 것이다. 72개 TC 전체를 재현한 실행은 아니다. 현재 대표의 실제 의존 디렉터리는 `oos_coverage_gaps`, `oos_utility`, `oos_common`, `oos_native`다. 다른 TC의 `cases`를 편의상 남기지 않았다. 선별 후 남은 53개 파일의 bytes·mode를 원본, native 복사본, 게시한 TC commit과 각각 대조했다.

이 실험은 확보한 이미지 소스의 삭제 동작과 현재 배치 수리를 검증한다. 과거 worker 이미지 digest·실제 entrypoint가 없다는 이전 조사 한계는 유지한다. 역사적 39개 전부의 원인이 확정됐다는 뜻은 아니다.

## 선별 후 원문 대표의 두 실제 실행

선택한 경로는 `shell/_40_guava/cbrd_26659_gap_ctas_cs/cases/cbrd_26659_gap_ctas_cs.sh`다. 저장소의 `disabled/failing/` 아래 `.disabled` 원문을 scratch에서만 복원했다. Checker·controller의 이번 경로 변경 외에 TC assertion이나 기대값은 바꾸지 않았다.

| 시도 | TC 결과·검사 | XML TC 구간 | 전체 native 명령 | 최종 판정 |
| --- | --- | --- | --- | --- |
| `fixed01` | 1 success·0 fail·0 skip, TC 27 OK·controller 26 PASS | 53.792초 | 130.157초, exit -9·verifier 1 | **미완료 timeout**. 성공 결과 파일만으로 PASS 처리하지 않음 |
| `fixed02` | 1 success·0 fail·0 skip, TC 27 OK·controller 26 PASS | 38.287초 | 40.879초, exit 0·verifier 0 | **현재 대표 1 PASS**. 첫 timeout 원인은 미확정 |

두 실행 모두 실제 `source.policy` JSON은 `{"payload":"DEFAULT"}`, `ctas.policy`는 `{"payload":"FORCE_OUTLINE"}`다. 26개 controller 검사와 TC 최종 완료 검사까지 포함한 27개 assertion을 구분했다. 소유 파일 관측·값·flag·source DROP·checkdb·정리 검사도 유지했다.

매번 CUBRID·CTP·HOME·registry·TMPDIR·native cache·slot root를 분리했다. Producer는 `/home/vimkim/temp/oos-tc-runtime-20261028/engine/CUBRID`이며 source/install commit 일치와 containment preflight를 통과했다. Runtime 6개 fingerprint와 native 바이너리는 두 실행에서 동일하다. `fixed02`는 `fixed01`의 CTP 자산 snapshot도 복사·대조해 환경 차이를 줄였다. `CUBRID_TMP`는 준비 wrapper가 명시적으로 공급했다.

실제 실행은 `TESTKIT_NATIVE=shell`, `TESTKIT_CONTAIN=1`, `testkit shell`을 사용했다. 1 slot·`scenario_disk=on`·정확히 1개 expected case를 설정했고 업데이트·재시도·continuation·case patch를 껐다. CTP는 자산 제공용이며 legacy runner로 대체하지 않았다.

```sh
timeout --signal=TERM --kill-after=10s 120s \
  /home/vimkim/.local/bin/testkit shell -c ATTEMPT/conf/shell.conf
```

Native config에도 TC timeout 120초를 지정했다. 외부 120초는 명령 시작부터 runner 준비·TC·정상 정리까지 포함한다. 추가 10초는 종료 유예다. Runtime 복사는 그 전에 끝냈다. Verifier에는 각 실행의 실제 종료값 -9와 0을 전달했다.

`fixed01`의 TC는 성공 결과를 남긴 뒤 `TEST COMPLETE`·`TEST END`를 출력했지만 명령이 끝나지 않았다. 제한 후 소유 프로세스와 관측한 namespace holder는 0개였다. 별도 진단 `fixed02`는 같은 53개 입력·config·선택한 환경을 사용해 정상 종료했다. 정확한 TEST END의 monotonic 시각을 polling 사이에 놓쳐 `test_end_seen_seconds=null`로 기록했다. 따라서 이 실행의 완료 후 대기 시간을 계산하지 않았다. Strace는 실행하지 않았다.

진단 중 정상 종료 직전 outer testkit이 자기 namespace init을 기다리는 PID·generation·pidfd 관계를 관측했다. 이는 testkit 소스 `5f6411`의 `internal/contain/contain.go:106`의 `cmd.Wait()`와 `:315`의 init `Wait4` 경계에 부합한다. Stall을 재현한 구간을 관측하지 못해 첫 timeout의 원인 확정은 불가능하다. Kernel stack은 권한 제한으로 읽지 못했고, polling은 scheduling에 영향을 줄 수 있다. 선택한 환경 외의 ambient 환경도 완전히 snapshot하지 않았다. 엔진 수정 효과나 성능 개선을 주장하지 않는다.

`fixed02`의 두 종료 후 scan에서 시도 소유 프로세스, 관측 namespace holder, 시도 경로의 host mount·UNIX socket은 각각 0개였다. 정리 신호는 보내지 않았다. 일부 unrelated host 프로세스의 읽기 권한 오류는 별도 기록했다. 관측한 시도 범위의 정리 근거이며 호스트 전체 IPC가 비었다는 뜻은 아니다.

## TC 게시와 한 번의 CI

두 TC PR의 실제 head repository와 `tc/pr-8128` ref를 확인한 뒤 일반 `6334dc6`은 CUBRID 저장소로, heavy `81e6072`는 vimkim fork로 push했다. 실제 원격 SHA도 대조했다. TC PR은 사람이 검토·병합하는 흐름을 유지했다.

기존 지침에 따라 TC push 후 [명령 댓글 6539887410](https://github.com/CUBRID/cubrid/pull/8128#issuecomment-6539887410)로 `/run all`을 정확히 한 번 게시했다. 두 TC branch의 feature baseline 포함 검사는 PASS였다. 기존 같은 Engine의 [run 41031622190](https://github.com/CUBRID/cubrid/actions/runs/41031622190)은 종료 상태였고, 새 실행을 취소할 활성 run이나 새 `/run` 댓글은 없었다. `testtools` override는 사용하지 않았다.

새 [CI 41175186516](https://github.com/CUBRID/cubrid/actions/runs/41175186516), attempt 1의 5개 gha context 연결을 확인했다. Plan job `124461306959` 로그 470·482행은 public TC `b038c424`와 private TC `6334dc6`을 실제 checkout한 근거다. 테스트 Engine은 `e3589ae`, workflow 실행 head는 별도 `ef4e7e812416d1c5533838ca4a1527d315c20946`다. Heavy suite는 일반 gha-ci의 suite 선택에 들어 있지 않아 이 CI에 heavy 실행 credit을 주지 않는다.

GitHub run 결론은 **SUCCESS**다. Build debug·release와 shell·SQL·medium의 5개 gha context가 모두 같은 새 run을 가리키며 SUCCESS인 것을 종료 뒤 다시 확인했다. GitHub job 기준으로 72개 중 71 success·1 skipped다. 이는 testcase PASS·SKIP 건수 집계와 구분한다.

| gha context | 종료 상태 |
| --- | --- |
| `gha-ci: build (debug)` | SUCCESS |
| `gha-ci: build (release)` | SUCCESS |
| `gha-ci: test_medium` | SUCCESS |
| `gha-ci: test_shell` | SUCCESS |
| `gha-ci: test_sql` | SUCCESS |

`gh pr checks --required`는 이 branch에 required check가 보고되지 않았다는 stderr와 exit 1·빈 JSON 출력을 반환했다. 그 관측을 성공으로 바꾸지 않았다. 전체 checks와 stable gha 5개 context를 별도로 대조했다. 전체 check view에는 TC Merge Gate context가 표시되지 않았다. [Public TC PR #3688](https://github.com/CUBRID/cubrid-testcases/pull/3688), 일반 TC PR #4365, heavy PR #4627은 모두 OPEN이다. Public·heavy는 draft를 유지하고 있으며 사람의 검토·병합은 후속으로 남긴다. Gate 통과 여부는 미확인으로 유지한다.

CI 종료 뒤 추가 TC 수정·push·재실행은 하지 않았다. GitHub status와 독립적인 전체 SQL 증거 정합성은 구분한다. 이전 SQL 집계 3,533/3,531건 문제와 전체 PASS 미인증 상태를 이번 helper 수리만으로 완료하지 않는다.

## 남은 범위

그룹 39개 중 이번에 다시 검증한 고유 TC는 1개다. 나머지 38개는 현재 실행하지 않았다. 앞선 `show_contract`와 합해도 서로 다른 준비·실행 문맥의 고유 2개이며, 과거 shell 61개 중 59개는 현재 검증이 남았다. 이번 대표의 heavy 복원과 나머지 사례의 실행 위치는 후속 분류에서 결정한다. Heavy 38개의 전체 재실행도 이번에는 하지 않았다.

다른 교차 TC 의존성은 별도 후속 항목이다. 일반 `oos_common/oos08_controller.sh:86`, `cbrd_26659_partition_lifecycle_common/controller.sh:86`, `cbrd_26659_show_contract/cases/show_controller.sh:79`의 `policy_metadata.sh` 경로와 `oos_common/oos_crash.sh:200,258`의 `tde_observe.sh`는 다른 TC의 `cases` 아래를 참조한다. Schema와 partition rejection, show, encrypted crash 경로에서 필요한 의존성을 실제 호출 기준으로 다시 확인해야 한다. CTAS 대표는 이 파일들을 사용하지 않는다. 함수 정의만 있고 해당 scenario에서 호출하지 않는 경우도 구분한다.

원래 종료 지연, 이전 CI 41031622190의 `cbrd_25977-16` 원인 미확정·SQL 집계 정합성, 기존 장시간 3개, HA 실패·엔진 후속, QA의 heavy 실행 경로·주기, 사람의 TC PR 리뷰·병합도 남아 있다. 이번 경로 수리나 한 대표 PASS로 CBRD-26659 전체를 완료하지 않는다.

## 재검증과 보존 자료

[배치·선별 검증](tools/verify-policy-helper-relocation.py)은 고정 원본과 현재 TC를 비교하고, 실제 entrypoint의 `keep case`를 새 scratch fixture에만 실행한다. [Native 결과 검증](tools/verify-policy-relocated-native.py)은 두 시도를 따로 유지하며 실제 종료값·53개 입력과 게시 commit·runtime 6개·config·환경·XML·27/26 검사·policy JSON·정리 근거를 대조한다. 보고서의 결론을 재현하는 데 필요해 두 스크립트를 보존한다.

```sh
python3 cbrd-26659/tools/verify-policy-helper-relocation.py \
  --regular /home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8128 \
  --heavy /home/vimkim/gh/cubrid-testcases-private-ex/CBRD-26659-oos-shell-heavy \
  --artifacts /home/vimkim/temp/cbrd-26659-policy-helper-fix-20261031
python3 cbrd-26659/tools/verify-policy-relocated-native.py \
  --artifacts /home/vimkim/temp/cbrd-26659-policy-helper-fix-20261031 \
  --regular /home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8128 \
  --engine /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover \
  --producer /home/vimkim/temp/oos-tc-runtime-20261028/engine/CUBRID \
  --tc-commit 6334dc6cd74683ca6ba10439372a21bd36b453d3
```

Scratch root는 `/home/vimkim/temp/cbrd-26659-policy-helper-fix-20261031`이다. `before-parent.log`·`.exit`·`.json`, `after-parent.json`·`after-commit-proof.log`, `native-proof-parent.json`, `tc-local-commits.json`·`tc-publication.json`, `fixed01/`·`fixed02/`, `ci-trigger/receipt.json`·`pickup.json`, `ci-status/`, `teardown.md`·`how.md`, append-only `decisions.tsv`를 Git 밖에 보존한다. 실패한 첫 실행과 잘못 작성해 AST 검사에서 중단한 observer 초안 `run-native-v1.py`도 남겼다. 초안의 문법 오류는 실제 실행 전에 고쳤으며 추가 native 실행은 없었다. Raw log·생성 JSON·snapshot·runtime·중간 초안은 문서 commit에 넣지 않는다.
