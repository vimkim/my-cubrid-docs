# CBRD-26659 policy helper 누락 39개 그룹 조사

작성일은 2026-10-30, Asia/Seoul이다. 대상은 [Engine PR #8128](https://github.com/CUBRID/cubrid/pull/8128)과 [private-ex TC PR #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365)의 과거 shell 실패다. QA 담당자와 TC 리뷰어가 helper 누락, 실제 policy 불일치, 실행 종료 지연을 구분할 수 있도록 조사했다.

**다른 TC의 `cases/` 아래에 둔 공용 helper가 shard 선별에서 삭제되는 소스 동작을 재현했다. 과거 CI 실패의 유력한 설명이지만, 당시 이미지의 실제 entrypoint를 확보하지 못해 역사적 원인 확정은 보류한다.** 원문 대표 `gap_ctas_cs`는 현재 환경에서 한 번 정상 종료했다. 그 앞 실행은 testcase 결과가 성공이어도 전체 명령이 timeout되어 미완료로 보존한다. 나머지 38개는 현재 실행하지 않았다.

이번 범위는 [61개 분류 보고서](CBRD-26659-shell61-classification_20261030_e3589ae_codex.md)의 가장 큰 공통 증상 그룹과 대표 재현이다. TC·엔진 수리나 재활성화, PR·JIRA 변경, CI 재실행은 포함하지 않았다. [체크리스트](CBRD-26659-todo-checklist_20261029_codex.md)에 완료한 조사와 남은 검증을 구분했다.

## 근거의 리비전

| 구분 | 고정한 입력 | 적용 범위 |
| --- | --- | --- |
| 과거 실행 | [run 40311481032](https://github.com/CUBRID/cubrid/actions/runs/40311481032), attempt 1 | helper 누락 39개, 30개 shard의 보존된 JUnit·오류 자료 |
| 과거 테스트 Engine | `c4c4f5c5ed55fb0130c72bb261061ec441662554`, debug | 테스트 대상이며 workflow 리비전과 다름 |
| 실제 workflow | `CUBRID/cubrid` `4781495f01523a3ecc5891e3377ad62cf876a1cd`, `.github/workflows/gha-ci.yml` | run metadata의 `develop`, `issue_comment` 실행 |
| 과거 TC | `CUBRID/cubrid-testcases-private-ex` `10a8fc82d34cd2c54c2caa403886e3528852d6fe` | helper와 대표·controller 원본, shard 계획 |
| 과거 CTP | `7dc9f4192bb96988d1bab78df3e45df88628b814` | 원래 job에 기록된 실행 디렉터리·정리 코드 |
| 이미지 소스 | `CUBRID/cubridci` `155c265eb6e3deef49ce828e6f2b5846d3a9abf5`, `docker/ci/docker-entrypoint.sh` | 삭제 규칙 재현에 사용한 소스. 당시 이미지와의 동일성은 미인증 |
| 현재 Engine | `e3589ae42d42b04eb020e1ae43e165b01d31b12a`, optdebug, `11.5.0.2793-e3589ae` | 현재 원문 대표 재현. 기존 CCI/JDBC 수정 보존 |
| 현재 TC | `a229e1978abc4cc6c280783703c03f75524c0f05` | clean checkout에서 원문 진입점과 의존 파일 56개를 복사 |
| 현재 native testkit | 설치 바이너리 SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a` | metadata `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`, `vcs.modified=true`. 소스와 바이너리의 완전한 대응은 미인증 |

39개는 모두 같은 과거 run·attempt·TC에서 `policy_ddl.sh: No such file or directory`를 관측한 사례다. 기존 inventory SHA-256은 `1e5c58351a016f6a79d7c7af7f0d33473933c8247346b85446953333ab9b2366`이다. 현재 상위 수집 manifest를 새로 완전 인증한 결과가 아니라, 기존에 보존·대조한 해당 run의 원본 자료를 사용한 조사다.

## Helper의 역할과 삭제 경로

`policy_ddl.sh`는 호출자가 독립적으로 지정한 열별 policy와 `SHOW CREATE TABLE` 출력을 비교한다. `DEFAULT`이면 명시적 STORAGE 절이 없어야 하고, 다른 policy이면 해당 STORAGE 절이 정확히 하나여야 한다. 성공 시 확인한 열과 policy를 JSON으로 출력한다. 따라서 helper 실행 자체가 실패하면 그 경로의 policy 검사를 완료할 수 없다.

과거·현재 TC 모두 `shell/_40_guava/cbrd_26659_schema_policy/cases/policy_ddl.sh`가 Git에 있다. 두 파일은 1,493바이트이며 SHA-256 `99bb263ae729f3f02745f88601b86653813d136476af007c2417fae6aedd024c`로 같다. helper가 원래 저장소에 없었다는 설명은 배제된다.

대표의 실행 경로는 다음과 같다.

1. 과거 CTP의 `CTP/shell/src/com/navercorp/cubridqa/shell/main/Test.java:124`와 `:285`는 testcase의 `cases` 디렉터리를 실행 디렉터리로 정하고 그곳에서 shell을 실행한다.
2. 과거 TC `10a8fc8`의 `shell/_40_guava/cbrd_26659_gap_ctas_cs/cases/cbrd_26659_gap_ctas_cs.sh:10`은 현재 디렉터리를 유지한 채 공용 controller를 호출한다.
3. `shell/_40_guava/oos_coverage_gaps/controller.sh:53`은 `../../cbrd_26659_schema_policy/cases/policy_ddl.sh`를 실행한다. 완전한 tree에서는 이 상대 경로가 기존 helper를 가리킨다.

삭제 취약점은 공용 helper의 소유 위치와 shard 선별 계약의 충돌이다. 실제 [workflow의 선별 단계](https://github.com/CUBRID/cubrid/blob/4781495f01523a3ecc5891e3377ad62cf876a1cd/.github/workflows/gha-ci.yml#L1225-L1303)는 계획의 TC 리비전을 맞춘 뒤 `/entrypoint.sh keep "$unit" "$TC_DIR/$SUITE" "$PLAN_DIR/shards/$IDX.list"`를 실행한다. 원본 계획은 `unit=case`, 50개 shard다.

조사한 이미지 소스의 [`keep_cases`](https://github.com/CUBRID/cubridci/blob/155c265eb6e3deef49ce828e6f2b5846d3a9abf5/docker/ci/docker-entrypoint.sh#L1045-L1070)는 최외곽 `cases` 디렉터리를 찾고, 목록에 든 진입점의 부모 디렉터리만 남긴다. 나머지 `cases`는 `rm -rf`로 삭제하며 shell의 의존 관계는 읽지 않는다. `policy_ddl.sh` 자체는 canonical TC 진입점이 아니어서 독립 선별되지 않는다. 반면 `oos_coverage_gaps/controller.sh`는 `cases` 밖에 있어 이 삭제 규칙에서 살아남는다.

원본 shard 13 목록은 72개 경로다. 22행에 대표 TC가 있고 `cbrd_26659_schema_policy/cases/`의 진입점은 없다. 목록 SHA-256은 `91ced695f3703410067a2a9bb89bb7475bd389c5bb2436e25dde8c922ff825be`이다. 이 목록과 과거 TC의 실제 파일 4개로 독립 scratch fixture를 만들고, 수정하지 않은 이미지 소스의 `keep`만 실행했다. DB나 TC는 실행하지 않았다.

| 파일시스템 대조 | keep 종료값 | 대표 진입점 | 공용 controller | policy helper·소유 TC |
| --- | --- | --- | --- | --- |
| 원래 shard 13 목록 | 0 | 유지 | 유지 | 삭제 |
| 같은 목록에 schema_policy 진입점 추가 | 0 | 유지 | 유지 | 유지 |

두 대조 모두 상대 경로가 가리키는 위치를 확인했다. 대조군은 삭제 규칙의 조건을 검증하기 위한 것이며, 다른 TC를 같은 shard에 묶는 방안을 수리안으로 채택한 것은 아니다.

실제 [shard 13 job](https://github.com/CUBRID/cubrid/actions/runs/40311481032/job/121534251605)의 `Keep only my share`는 11:29:00~11:29:01 UTC에 성공했다. 원본 job log 551행에 명령이 있고, 704·782행에는 `delete_testcase_after_each_execution_yn=false`가 있다. CTP `Test.java:211`·`:549`의 실행 후 정리는 이 옵션이 켜졌을 때 현재 `cases/*`를 삭제하는 별도 경로다. 이 worker는 그 옵션을 켜지 않았다. 과거 누락을 선행 TC의 실행 후 정리 탓으로 확정할 근거는 없다.

**입증한 것은 해당 소스와 원본 shard 입력이 helper를 삭제한다는 사실이다.** 당시 workflow는 [가변 이미지 tag](https://github.com/CUBRID/cubrid/blob/4781495f01523a3ecc5891e3377ad62cf876a1cd/.github/workflows/gha-ci.yml#L1174-L1175) `cubridci/cubridci:test_rl8.10`을 사용했다. 실제 이미지 digest·`/entrypoint.sh` 원본·삭제 직후 snapshot은 확보하지 못했다. 소스의 Git 날짜만으로 그 공백을 메울 수 없다. 따라서 과거 대표의 선별 시 helper 삭제는 **강한 추론**이며 39개 모두의 확정 원인은 아니다.

39개가 실행된 JUnit 집합은 30개 shard에 걸친다. helper를 소유한 canonical `schema_policy` TC는 shard 31에서만 관측됐고, 39개 중 같은 실행 집합을 공유한 것은 0개다. 이는 삭제 설명과 부합한다. 다만 전체 30개 shard의 원래 선별 목록을 모두 확보한 것은 아니므로 JUnit 집합을 정확한 shard 입력으로 바꾸어 부르지 않는다.

## 대표의 과거 실패와 현재 세 시도

대표 원본 경로는 `shell/_40_guava/cbrd_26659_gap_ctas_cs/cases/cbrd_26659_gap_ctas_cs.sh`다. 과거 35.715초의 실패에서는 `source.policy` 4번, `ctas.policy` 9번, controller status 26번, 최종 27번이 NOK였다. 원본 message 35·41행에는 helper 실행 오류가 있다. 값·플래그·owner·drop·checkdb·정리 검사에는 OK가 있었다. 이 근거로 엔진의 policy 구현 결함을 확정할 수 없다.

현재 재현은 비활성 원문을 disposable corpus의 원래 경로로 복원했다. assertion·기대값·helper를 바꾸지 않았다. 관련 디렉터리 7개의 파일 56개에 대해 원본 Git·복사본의 bytes와 mode를 대조했다. `CUBRID_TMP`는 준비 wrapper가 명시적으로 제공했다. testkit이 독자적으로 주입했다는 검증이 아니다.

| 시도 | TC 결과 | XML TC 시간 | 전체 native 명령 | 최종 판정 |
| --- | --- | --- | --- | --- |
| `ctas01` | 준비 중 원문 복원 대상의 빈 `cases` 부모를 만들지 못함 | 없음 | preflight·native 실행 전 `FileNotFoundError` | 준비 실패. TC 판정 없음 |
| `ctas02` | 1 success·0 fail·0 skip, TC assertion 27 OK·controller 26 PASS | 57.039초 | 130.013초, exit -9·verifier 1 | **미완료 timeout**. 성공 결과 파일만으로 전체 PASS 처리하지 않음 |
| `ctas03` | 1 success·0 fail·0 skip, TC assertion 27 OK·controller 26 PASS | 43.424초 | 56.908초, exit 0·verifier 0 | **현재 대표 1 PASS**. 종료 지연 재현 안 됨 |

`ctas01`의 실패한 준비 코드와 부분 복사본은 보존했다. 다음 시도에서는 복원할 부모 디렉터리를 먼저 만드는 준비 코드만 고쳤다. 원본 TC 파일이 Git에 없어서 생긴 실패가 아니다.

두 실제 실행은 `source.policy`의 `{"payload":"DEFAULT"}`와 `ctas.policy`의 `{"payload":"FORCE_OUTLINE"}`를 남겼다. 26개 controller 검사는 모두 PASS다. TC의 최종 완료 검사까지 포함하면 assertion은 27개다. controller 검사와 TC assertion은 서로 다른 수다. XML·summary·실제 진입점·전체 명령 종료값을 함께 대조했다.

현재 projection 56개를 과거 TC와 비교하면 40개 동일, 11개 다름, 5개는 과거에 없다. policy helper 자체는 동일하지만 다른 공용 helper는 바뀌었다. Engine·runner·환경도 과거와 달라졌으므로 현재 PASS를 특정 엔진 수정의 효과로 귀속하지 않는다.

실제 명령은 아래 형태다. Native config에도 `testcase_timeout_in_secs=120`을 설정했다.

```sh
timeout --signal=TERM --kill-after=10s 120s \
  /home/vimkim/.local/bin/testkit shell -c ATTEMPT/conf/shell.conf
```

120초는 전체 native 명령 시작부터 runner 준비·TC·정상 정리를 포함한다. 추가 10초는 종료 유예다. 준비용 runtime 복사는 그 전에 끝냈다. Native 자체의 추가 유예·버퍼링된 `[TESTCASE]` 출력 때문에 TC 시작 로그에 의존하지 않고 외부 제한을 적용했다. `ctas02`에서 제한 만료 후 실제 강제 종료를 관측했다. 이후 0인 것처럼 종료값을 바꾸어 verifier에 전달하지 않았다.

매 시도에서 CUBRID·CTP·HOME·registry·TMPDIR·native cache·slot root를 분리했다. Producer는 `/home/vimkim/temp/oos-tc-runtime-20261028/engine/CUBRID`다. Source/install 리비전 일치 preflight와 containment 가용성을 통과했다. CTP 자산은 기존 수정이 있는 `9c62858b10005d721546cc007be260844033b9e9` checkout의 복사본이다. 재시도·답안 갱신·case patch는 사용하지 않았다. 두 실제 실행 뒤 시도 소유 프로세스와 관측한 private namespace의 잔류 holder는 각각 0개였다. 호스트 전체 IPC가 비었다는 뜻은 아니다.

## 완료 후 대기의 관측 범위

`ctas02`는 `TEST COMPLETE`·`[SHELL] TEST END` 뒤에도 명령이 끝나지 않았다. 기존 observer는 PID generation과 namespace를 기록했지만 당시 대기를 설명할 argv·마지막 생존 시점은 충분히 수집하지 않았다. 결과 파일의 성공과 명령 미완료를 분리하고 한 번의 추가 진단 실행 `ctas03`을 했다.

실행 전에 세 가설을 기록했다. 포함된 자식 프로세스가 남아 init 종료를 지연하는 경우, testkit만 남아 Go 정리를 기다리는 경우, 바깥 launcher가 잘못된 자식을 기다리는 경우다. `ctas03`의 완료 후 snapshot에는 실제 TC worker가 이미 사라지고 namespace init·slot keeper·그 `sleep`이 남아 있었다. 이 실행의 그 구간에는 CUBRID 엔진 프로세스가 관측되지 않았다.

전체 명령 시작 후 51.308초에 TEST END를 읽었고 54.452초에 PID generation을 대조한 바깥 testkit에 짧게 strace를 붙였다. `waitid(P_PIDFD, 7<pid:1888930>, ...)`가 자기 namespace init의 status 0을 받고 정상 종료하는 경로를 관측했다. trace의 2.446170초는 attach 이후 구간이며 전체 대기 시간은 아니다. 종료 신호나 강제 stack dump는 보내지 않았다.

이 경계는 testkit 소스 `5f6411`의 `internal/contain/contain.go:106`의 `cmd.Wait()`, `slot.go:52`의 keeper, `slot.go:271`의 `Namespace.Close`와 부합한다. 설치 바이너리와 소스의 완전한 동일성 인증을 대체하지는 않는다.

Keeper의 sleep은 약 46.927~56.281초 snapshot에서 D 상태였다. 종료 중인 프로세스의 `/proc/.../ns/ipc` 접근 실패로 묶인 metadata 읽기가 중단되어, 해당 시점의 wchan·kernel stack·fd를 확보하지 못했다. 구체적인 kernel wait 원인은 미확정이다. strace는 scheduling에 영향을 줄 수 있고 선택한 환경 외의 ambient 환경도 완전히 snapshot하지 않았다.

첫 가설은 이번 정상 대기와 양립하지만 이전 timeout의 원인은 입증하지 못했다. 두 번째 가설의 ‘testkit만 남는다’는 예측은 이번 관측과 달랐다. 세 번째 가설도 자기 init을 기다린 trace로 지지되지 않았다. **원래 `ctas02` timeout은 재현되지 않았고 원인은 여전히 미확정이다.** 정상 종료한 관측을 이전 실패의 인과 증거로 승격하지 않는다.

## 다음 작업과 완료 범위

이번 조사는 공용 helper의 배치 취약점과 대표 한 개의 현재 결과를 확보했다. 이 그룹 38개, 과거 shell 전체 61개 중 59개는 현재 native 검증이 남아 있다. 앞선 `show_contract`와 이번 대표는 서로 다른 준비·실행 문맥의 개별 PASS이며 하나의 suite 전체 PASS가 아니다. `ctas02` 미완료도 별도 후속 항목으로 남긴다.

가장 직접적인 수리 후보는 공용 helper를 개별 TC의 `cases` 밖으로 옮기고 모든 호출자를 함께 바꾸는 것이다. 이후 실제 shard 선별을 거친 입력으로 대표를 검증하고 나머지 38개를 순차 실행해야 한다. 이것은 **후속 제안**이며 이번에는 구현하지 않았다. 원래 이미지의 digest·entrypoint 또는 선별 직후 snapshot 확보는 역사적 원인 확정에 필요한 별도 근거다.

일반 CI 제외·heavy 이관 38개, SQL 복원 3개는 이전 작업 상태를 유지한다. 최신 CI의 `cbrd_25977-16` 실패, SQL 전체 집계 정합성, 기존 장시간 3개, HA 실패·엔진 후속, QA의 heavy 실행 경로와 사람의 TC PR 리뷰·병합은 여전히 남아 있다. 이번 대표 PASS로 해당 항목을 완료하지 않는다.

## 재검증과 보존 자료

새 실행 없이 다음 두 스크립트로 근거를 다시 대조할 수 있다. [선별 재현 스크립트](tools/verify-policy-helper-pruning.py)는 원본 목록·job·Git·39개 JUnit 집합과 실제 삭제/보존 대조를 확인한다. [시도 판정 스크립트](tools/verify-policy-native-attempts.py)는 세 시도의 분리, 원문·runtime·config·policy 결과·27/26 검사·실제 종료값·정리를 확인한다. 보고서의 핵심 결론을 재현하는 데 필요해 두 파일을 Git에 보존한다.

```sh
python3 cbrd-26659/tools/verify-policy-helper-pruning.py \
  --artifacts /home/vimkim/temp/cbrd-26659-policy39-20261030 \
  --testcases /home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8128 \
  --image-source /home/vimkim/gh/cubrid-dockerfiles-cubridci \
  --engine-source /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover
python3 cbrd-26659/tools/verify-policy-native-attempts.py \
  --artifacts /home/vimkim/temp/cbrd-26659-policy39-20261030 \
  --testcases /home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8128 \
  --engine /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover \
  --producer /home/vimkim/temp/oos-tc-runtime-20261028/engine/CUBRID
```

원본 CI root는 `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/c4c4f5c5ed55fb0130c72bb261061ec441662554/providers/github-actions/runs/40311481032/attempts/1/test_shell`이다. `failures/<stable_id>/message.txt`·`diff.txt`와 `raw/shards/<shard>/test-shell.xml`을 연결한다. 사례별 정확한 경로와 행은 기존 61개 보고서 및 scratch `group-snapshot.json`에 남아 있다.

새 scratch root는 `/home/vimkim/temp/cbrd-26659-policy39-20261030`이다. `pruning-proof-final.json`·`native-attempts-proof-parent.json`은 부모가 재검사한 결과다. `namespaced-ci-probe/13.list`·`shard-13-job.log`·원본 entrypoint, `ctas01`~`ctas03`의 입력·명령·exit·summary·XML·case log·관측·strace, 준비/실행 코드와 append-only `decisions.tsv`를 Git 밖에 보존한다. 원본 이미지 소스 SHA-256은 `55965b9c36c67c4f4330b7954202ea292eb617b9139f9bfa46a6f27d283557d2`, job log는 `72c5187762b4ab6f5a55da9d3254659dfcd704c1c094762de75cf5a003fd984c`다. 원본 다운로드·생성 inventory·runtime 복사본은 이 문서의 Git 변경에 넣지 않는다.

## 39개 사례 목록

모든 원래 경로는 `shell/_40_guava/<아래 이름>/cases/<아래 이름>.sh`다. 현재 보존 경로는 `disabled/failing/` 아래 같은 경로에 `.disabled`를 붙인 것이다. 아래 NOK 번호는 과거 관측이며, 현재 FAIL이나 같은 원인 확정을 뜻하지 않는다. 첫 행만 이번 현재 대표로 실행했다.

| TC 이름 | 과거 shard | 과거 NOK 번호 | 현재 검증 |
| --- | --- | --- | --- |
| `cbrd_26659_gap_ctas_cs` | 13 | 4, 9, 26, 27 | ctas02 미완료, ctas03 PASS |
| `cbrd_26659_gap_ctas_sc` | 32 | 4, 9, 26, 27 | 미실행 |
| `cbrd_26659_gap_load_cs_cs` | 38 | 4, 14, 31, 32 | 미실행 |
| `cbrd_26659_gap_load_cs_sc` | 34 | 4, 14, 31, 32 | 미실행 |
| `cbrd_26659_gap_load_sa_cs` | 48 | 4, 14, 31, 32 | 미실행 |
| `cbrd_26659_gap_load_sa_nolog_cs` | 34 | 4, 14, 31, 32 | 미실행 |
| `cbrd_26659_gap_load_sa_nolog_sc` | 33 | 4, 14, 31, 32 | 미실행 |
| `cbrd_26659_gap_load_sa_sc` | 35 | 4, 14, 31, 32 | 미실행 |
| `cbrd_26659_gap_replace_select_cs` | 16 | 4, 9, 26, 27 | 미실행 |
| `cbrd_26659_gap_replace_select_sc` | 45 | 4, 9, 26, 27 | 미실행 |
| `cbrd_26659_gap_unload_sa_cs` | 20 | 4, 14, 31, 32 | 미실행 |
| `cbrd_26659_gap_unload_sa_sc` | 29 | 4, 14, 31, 32 | 미실행 |
| `cbrd_26659_partition_add_drop_list` | 16 | 1 | 미실행 |
| `cbrd_26659_partition_add_drop_range` | 11 | 1 | 미실행 |
| `cbrd_26659_partition_hash_coalesce` | 10 | 1 | 미실행 |
| `cbrd_26659_partition_hash_resize` | 19 | 1 | 미실행 |
| `cbrd_26659_partition_move` | 29 | 1 | 미실행 |
| `cbrd_26659_partition_partition_rejection` | 01 | 1 | 미실행 |
| `cbrd_26659_partition_promote_list` | 32 | 1 | 미실행 |
| `cbrd_26659_partition_promote_range` | 12 | 1 | 미실행 |
| `cbrd_26659_partition_remove` | 40 | 1 | 미실행 |
| `cbrd_26659_partition_reorganize_list` | 21 | 1 | 미실행 |
| `cbrd_26659_partition_reorganize_list_merge` | 28 | 1 | 미실행 |
| `cbrd_26659_partition_reorganize_range` | 08 | 1 | 미실행 |
| `cbrd_26659_partition_reorganize_range_merge` | 07 | 1 | 미실행 |
| `cbrd_26659_partition_repartition` | 42 | 1 | 미실행 |
| `cbrd_26659_partition_route_hash` | 44 | 1 | 미실행 |
| `cbrd_26659_partition_route_list` | 46 | 1 | 미실행 |
| `cbrd_26659_partition_route_range` | 47 | 1 | 미실행 |
| `cbrd_26659_policy_contract` | 09 | 1 | 미실행 |
| `cbrd_26659_schema_attributes_cs` | 14 | 1 | 미실행 |
| `cbrd_26659_schema_attributes_sa` | 04 | 1 | 미실행 |
| `cbrd_26659_schema_rewrites_cs` | 35 | 1 | 미실행 |
| `cbrd_26659_utility_compact_cs` | 45 | 9, 10 | 미실행 |
| `cbrd_26659_utility_compact_sa` | 28 | 9, 10 | 미실행 |
| `cbrd_26659_utility_policy_cs` | 19 | 9, 10 | 미실행 |
| `cbrd_26659_utility_policy_sa` | 34 | 9, 10 | 미실행 |
| `cbrd_26659_utility_policy_sa_nolog` | 30 | 9, 10 | 미실행 |
| `cbrd_26659_utility_policy_unload_sa` | 39 | 9, 10 | 미실행 |
