# CBRD-26659 과거 shell 실패 61개 분류와 첫 대표 재현

작성·갱신일은 2026-10-30, 시간대는 Asia/Seoul이다. 개발·QA 담당자가 비활성 shell의 재현 순서와 남은 원인 분석 범위를 정하도록 작성했다. 범위는 과거 FAIL 61개의 증상 분류와 첫 대표 1개의 현재 native 실행이다.

**61개 모두의 원본 경로·리비전·실패 근거를 대조했다. 43개 기록에서 경로가 명시된 shell 파일 누락, 5개에서 `CUBRID_TMP` 미정의 오류를 관측했다. 첫 대표 `show_contract`는 원문 그대로 현재 native 1 PASS·0 FAIL·0 SKIP이다. 나머지 60개는 이번에 실행하지 않았다.** 파일 누락이나 환경변수 오류가 함께 있다는 이유로 다른 assertion 실패도 같은 원인이라고 단정하지 않는다.

기존 [체크리스트](CBRD-26659-todo-checklist_20261029_codex.md)의 첫 shell 분류 단위다. SQL 3개 복구와 shell_heavy 38개 이관은 앞선 작업이다. 이번에는 TC·엔진 수정, 재활성화, push, CI 재실행, PR 상태 변경·병합·종료를 하지 않았다.

## 리비전과 분류 방법

| 구분 | 정확한 범위 |
| --- | --- |
| 과거 Engine | `c4c4f5c5ed55fb0130c72bb261061ec441662554`, debug |
| 과거 A | [run 40311481032](https://github.com/CUBRID/cubrid/actions/runs/40311481032), attempt 1, TC `10a8fc82d34cd2c54c2caa403886e3528852d6fe`, manifest가 선택한 FAIL 59개 |
| 과거 B | [run 40324320840](https://github.com/CUBRID/cubrid/actions/runs/40324320840), attempt 1, TC `10fb4b63f741a4cc231f37b8184b80839f9d452b`, `qualified_reuse`·`cbrd_27237_rollback_vacuum` FAIL 2개 |
| 현재 TC | `CUBRID/cubrid-testcases-private-ex:tc/pr-8128`, `a229e1978abc4cc6c280783703c03f75524c0f05`, [PR #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365) |
| 현재 대표 Engine | `e3589ae42d42b04eb020e1ae43e165b01d31b12a`, 설치 `11.5.0.2793-e3589ae`, optdebug |

A에는 OOS FAIL 60개가 있지만 manifest는 중복 사례의 더 늦은 B 관측을 선택한다. 따라서 이 표는 하나의 61개 실행 결과가 아니다. `disabled/oos-pr8128.tsv` 64행 중 FAIL 61행과 장시간 PASS 3행을 분리했다. 각 행의 현재 비활성 파일과 과거 Git 객체의 SHA-256이 manifest와 일치한다. 장시간 PASS 3개는 이번 실패 집계에 포함하지 않는다.

보존된 두 shell suite summary·raw index·failure metadata의 schema를 검증했다. Run마다 raw index 616개 파일의 크기·hash, summary hash, 해당 shard의 Engine·TC, 선택한 failure message와 JUnit failure 본문을 대조했다. 추출 diff의 NOK 행도 indexed JUnit 본문에 존재한다. 이는 보존한 자료의 내부 정합성 검증이며 독립된 제공자 서명이나 새 CI 실행이 아니다. 현재 상위 manifest는 후속 SQL 수집 상태를 담으므로, 그것으로 과거 shell bundle을 새로 인증했다고 주장하지 않는다.

분류는 명시적인 shell 오류, 독립된 JSON FAIL, 구체 NOK assertion, 마지막으로 포괄 controller 실패를 순서대로 선택한다. 한 TC는 대표 증상 그룹 하나에만 속하며 총합은 61이다. 모든 NOK·JSON FAIL·shell 오류는 별도 목록에 보존한다. 이 우선순위는 인과 순서가 아니다. 예를 들어 `gap_ctas_cs`의 `source.policy`·`ctas.policy` 실패와 `policy_ddl.sh` 누락을 모두 남기고, 대표 증상은 파일 누락으로 분류했다.

## 관측한 증상과 다음 분석

| 그룹 | 대표 증상 | 개수 | 해석과 남은 분석 |
| --- | --- | ---: | --- |
| G01 | 파일 누락 `cbrd_26659_schema_policy/cases/policy_ddl.sh` | 39 | 해당 경로가 없다는 실제 오류다. CI 배치·정리·선행 TC 영향과 다른 assertion의 관계는 미확정이다. |
| G02 | 미정의 환경변수 접근 | 5 | 5개 모두 당시 shell의 미정의 변수 오류가 남는다. 첫 대표만 현재 native PASS다. 나머지 4개는 미실행이다. |
| G03 | churn/storage controller 실패 | 5 | controller exit만 있어 내부 최초 실패 지점을 추가로 수집해야 한다. |
| G04 | 저장 stub 보존 assertion | 2 | 실제 JSON FAIL phase를 확인했다. 저장 동작과 기대값 중 원인은 아직 구분하지 않았다. |
| G05 | record 경계 controller 실패 | 2 | controller exit만으로 경계 계산·TC 기대값·엔진 원인을 판정하지 않는다. |
| G06 | 현재 record flag assertion | 1 | 구체 assertion은 식별했으나 engine·TC 원인은 미확정이다. |
| G07 | 경로가 없는 파일 누락 오류 | 1 | 오류만으로 대상 경로나 누락 주체를 확정하지 않는다. |
| G08 | vacuum 뒤 pre-image controller 실패 | 1 | 실제 값·상태와 실패 명령은 추가 재현이 필요하다. |
| G09 | snapshot/reclaim controller 실패 | 1 | 실제 회수 상태·검사값과 실패 명령은 추가 재현이 필요하다. |
| G10 | 파일 누락 `cbrd_26659_crash_committed/cases/cbrd_26659_crash_committed.sh` | 1 | 해당 경로가 없다는 실제 오류다. CI 배치·정리·선행 TC 영향과 다른 assertion의 관계는 미확정이다. |
| G11 | 파일 누락 `cbrd_26659_crash_undo/cases/cbrd_26659_crash_undo.sh` | 1 | 해당 경로가 없다는 실제 오류다. CI 배치·정리·선행 TC 영향과 다른 assertion의 관계는 미확정이다. |
| G12 | 파일 누락 `cbrd_26659_policy_contract/cases/policy_metadata.sh` | 1 | 해당 경로가 없다는 실제 오류다. CI 배치·정리·선행 TC 영향과 다른 assertion의 관계는 미확정이다. |
| G13 | 파일 누락 `cbrd_26659_tde_wal/cases/tde_observe.sh` | 1 | 해당 경로가 없다는 실제 오류다. CI 배치·정리·선행 TC 영향과 다른 assertion의 관계는 미확정이다. |

파일 이름이 명시되지 않은 누락 오류 1개는 위 43개에 포함하지 않는다. 그룹은 원인 분류의 출발점이다. 확인된 엔진 결함 수나 현재 FAIL 수가 아니다. 특히 controller exit만 남은 그룹은 내부 명령·값·상태 로그를 다시 확보해야 한다.

## 첫 대표 show_contract의 실제 결과

`CUBRID_TMP` 미정의 그룹 5개 중 `cbrd_26659_show_contract`를 선택했다. 과거 로그가 실패 위치를 명시하고 입력·의존 경로가 작아 환경 전제와 엔진 검사를 구분하기 쉽기 때문이다. 가장 큰 39개 그룹의 해결을 대신하는 대표는 아니다.

과거 A의 shard 19 message 103행은 `show_controller.sh: line 15: CUBRID_TMP: unbound variable`다. 당시 [controller](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_show_contract/cases/show_controller.sh#L15)는 `set -u` 상태에서 그 변수를 읽는다. 같은 controller·직접 참조 helper는 현재 TC와 바이트가 같다. 이 오류는 당시 shell 프로세스의 미정의 변수 접근을 보여 준다. 환경변수 제공 계약과 TC의 환경 전제 중 어느 쪽을 바꿔야 하는지는 아직 판단하지 않았다.

원래 비활성 entry를 disposable corpus의 원래 `shell/.../cases/*.sh` 경로로 복사했다. `show_contract`, `policy_contract`, `oos_common`, `oos_native`의 파일을 포함한 총 53개 입력의 bytes·mode를 현재 TC Git 객체와 대조했다. 원본 TC checkout은 그대로 두고 `scenario_disk=on` overlay에서 실행했다. 원본 assertion·helper·300초 내부 timeout은 수정하지 않았다. 첫 대표 실행은 `show01` 한 번이다.

| 실제 관측 | 결과 |
| --- | --- |
| native 결과 | 1 PASS·0 FAIL·0 SKIP, total·executed 각 1 |
| 실행·완료 목록 | expected·dispatch ALL·FIN이 같은 1개 |
| assertion | 8개 모두 OK, framework 설정 복원 포함 |
| controller journal | `mixed_records`, `stable_stats`, `targets`, `arguments`, `permissions`, `preserved`, `owned_cleanup` 7개 모두 PASS |
| 종료 코드 | runner·focused verifier 모두 0, controller 0 |
| 시간 | native JUnit TC 29.081974451초, entry timing 약 28.212초, 전체 명령 45.572395958초 |
| 실제 환경 | 보존된 `show.identity.log`에 attempt-local `CUBRID_TMP`가 있음 |
| 정리 | 관측한 전용 PID·IPC·mount·user namespace가 있었고, 종료 후 해당 설치 프로세스·관측 namespace holder는 모두 0 |

시간은 서로 다른 구간의 기록이다. 성능 비교가 아니다. 현재 native 환경에서 원래 검사를 끝까지 실행해 PASS했지만, 과거 CI와 Engine·runner·환경이 함께 다르다. 따라서 과거 실패의 원인이 엔진 수정으로 해결됐다고 귀속하지 않는다. 같은 그룹의 다른 4개도 PASS했다고 간주하지 않는다. 현재 이 TC는 원래 저장소에서 여전히 비활성이다.

### 120초 제한의 범위

실행 명령은 다음 형태다. Native runner에는 별도로 `testcase_timeout_in_secs=120`도 설정했다.

```sh
TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 timeout --signal=TERM --kill-after=10s 120s \
  testkit shell -c <attempt>/conf/shell.conf
```

120초는 복사와 preflight 이후 단일 native 명령의 시작부터 잰다. Runner 준비·TC·정상 정리를 모두 포함하므로 TC만의 120초보다 보수적인 제한이다. 추가 10초는 종료 유예이며 TC 예산을 늘리는 시간이 아니다. 이 실행은 45.6초에 정상 종료했으므로 실제 timeout 중단 동작을 시험하지 않았다.

검토한 testkit 소스 `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`의 `internal/runner/shellsuite/monitor.go:108`에는 기본 2분의 추가 유예가 있다. 또한 `worker.go:445`의 `[TESTCASE]` 출력은 완료 전까지 버퍼링되며, file feedback의 `CaseStart`는 비어 있다. 따라서 그 로그를 실시간 시작 신호로 사용하지 않고 별도 invocation 제한을 뒀다. 설치 testkit SHA-256은 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`다. 빌드 metadata는 같은 리비전과 `vcs.modified=true`이며 소스와 바이너리의 완전한 대응은 인증하지 않는다.

실제 포함 실행은 disposable CUBRID·CTP·HOME·registry·TMPDIR·slot root와 수정하지 않은 corpus 입력을 사용했다. CTP 자산은 부모 HEAD `9c62858b10005d721546cc007be260844033b9e9`의 기존 수정이 있는 checkout을 복사했다. Source/install commit mismatch 예외는 쓰지 않았다. 원래 소스의 CCI/JDBC 수정은 보존했다. 정리 관측은 이 실행의 설치 경로와 수집한 namespace 식별자에 한정하며 호스트 전체 IPC가 비었다는 뜻이 아니다.

## 재검증과 보존 자료

원본 CI bundle은 `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/c4c4f5c5ed55fb0130c72bb261061ec441662554/providers/github-actions/runs/`에 있다. 각 run의 `attempts/1/test_shell/failures/<stable_id>/message.txt`와 `raw/shards/<shard>/test-shell.xml`을 사용했다. 행별 정확한 파일·행 번호, 전체 assertion, 별도 원인 미확정 상태는 아래 스크립트가 출력하는 JSON에 담긴다.

이번 작업 자료는 `/home/vimkim/temp/cbrd-26659-shell61-20261030`에 있다. `inventory.json`은 과거 분류 snapshot이고, 현재 대표의 결과는 `representative-proof.json`과 `show01/`에 따로 보존한다. 분류 JSON의 `current_reproduction=not_run`은 분류 시점의 값이며 뒤따른 대표 실행 결과를 덮어쓰지 않는다. 원본 로그·생성 JSON·runtime 복사본·실행 wrapper는 Git 밖에 둔다.

[분류 스크립트](tools/classify-shell-failures.py)는 고정된 원본을 읽어 61개를 재구성한다. [대표 검증 스크립트](tools/verify-shell-representative.py)는 재실행 없이 실제 입력·native 결과·journal·환경·정리 자료를 대조한다. 보고서의 원본 근거를 재검증하는 데 필요하므로 두 스크립트를 보존한다.

```sh
/usr/bin/python3 cbrd-26659/tools/classify-shell-failures.py \
  --testcases /home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8128 \
  --evidence-root /home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/c4c4f5c5ed55fb0130c72bb261061ec441662554/providers/github-actions/runs \
  --output /home/vimkim/temp/cbrd-26659-shell61-20261030/inventory-recheck.json

python3 cbrd-26659/tools/verify-shell-representative.py \
  --attempt /home/vimkim/temp/cbrd-26659-shell61-20261030/show01 \
  --testcases /home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8128 \
  --engine /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover \
  --producer /home/vimkim/temp/oos-tc-runtime-20261028/engine/CUBRID
```

부모의 실제 재검증에서도 분류 JSON은 동일했고 SHA-256은 `1e5c58351a016f6a79d7c7af7f0d33473933c8247346b85446953333ab9b2366`이다. 대표 검증도 같은 PASS·53개 보존·정리 0개 결과다.

## 사례별 목록

TC 링크는 각 행의 과거 리비전에 고정한다. A/B는 위의 서로 다른 실행을 가리킨다. `NOK`는 첫 구체 assertion을 우선 표시하며 그룹을 정한 shell 오류와 인과 순서를 같다고 가정하지 않는다. 긴 신호 문구는 표에서 축약했다. 모든 행의 engine·TC·run·shard·assertion·원본/비활성 경로는 원본 manifest와 검증 JSON에 있다. 현재 PASS 1개 외 60개는 원인 확정과 현재 실행이 남아 있다.

| 번호 | TC | 관측 | 그룹 | 구체 실패 신호 | 현재 확인 |
| ---: | --- | --- | --- | --- | --- |
| 1 | [alt_stub_duplicate](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_alt_stub_duplicate/cases/cbrd_26659_alt_stub_duplicate.sh) | A·shard 28 | G04 | `cbrd_26659_alt_stub_duplicate-6 : NOK retained_whole_stub` | 미실행 |
| 2 | [alt_stub_merge](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_alt_stub_merge/cases/cbrd_26659_alt_stub_merge.sh) | A·shard 44 | G04 | `cbrd_26659_alt_stub_merge-6 : NOK retained_whole_stub` | 미실행 |
| 3 | [churn_abort_retry](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_churn_abort_retry/cases/cbrd_26659_churn_abort_retry.sh) | A·shard 19 | G03 | `cbrd_26659_churn_abort_retry-1 : NOK abortretry: intended churn/storage assertions failed (controller...` | 미실행 |
| 4 | [churn_insert_delete](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_churn_insert_delete/cases/cbrd_26659_churn_insert_delete.sh) | A·shard 02 | G03 | `cbrd_26659_churn_insert_delete-1 : NOK id: intended churn/storage assertions failed (controller exit 1)` | 미실행 |
| 5 | [churn_insert_update_delete](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_churn_insert_update_delete/cases/cbrd_26659_churn_insert_update_delete.sh) | A·shard 26 | G03 | `cbrd_26659_churn_insert_update_delete-1 : NOK iud: intended churn/storage assertions failed (controll...` | 미실행 |
| 6 | [churn_restart](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_churn_restart/cases/cbrd_26659_churn_restart.sh) | A·shard 45 | G03 | `cbrd_26659_churn_restart-1 : NOK restart: intended churn/storage assertions failed (controller exit 1)` | 미실행 |
| 7 | [gap_compact_sa_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_gap_compact_sa_cs/cases/cbrd_26659_gap_compact_sa_cs.sh) | A·shard 06 | G06 | `cbrd_26659_gap_compact_sa_cs-7 : NOK materialized.current_record_flags` | 미실행 |
| 8 | [gap_ctas_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_gap_ctas_cs/cases/cbrd_26659_gap_ctas_cs.sh) | A·shard 13 | G01 | `cbrd_26659_gap_ctas_cs-4 : NOK source.policy` | 미실행 |
| 9 | [gap_ctas_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_gap_ctas_sc/cases/cbrd_26659_gap_ctas_sc.sh) | A·shard 32 | G01 | `cbrd_26659_gap_ctas_sc-4 : NOK source.policy` | 미실행 |
| 10 | [gap_load_cs_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_gap_load_cs_cs/cases/cbrd_26659_gap_load_cs_cs.sh) | A·shard 38 | G01 | `cbrd_26659_gap_load_cs_cs-4 : NOK source.policy` | 미실행 |
| 11 | [gap_load_cs_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_gap_load_cs_sc/cases/cbrd_26659_gap_load_cs_sc.sh) | A·shard 34 | G01 | `cbrd_26659_gap_load_cs_sc-4 : NOK source.policy` | 미실행 |
| 12 | [gap_load_sa_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_gap_load_sa_cs/cases/cbrd_26659_gap_load_sa_cs.sh) | A·shard 48 | G01 | `cbrd_26659_gap_load_sa_cs-4 : NOK source.policy` | 미실행 |
| 13 | [gap_load_sa_nolog_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_gap_load_sa_nolog_cs/cases/cbrd_26659_gap_load_sa_nolog_cs.sh) | A·shard 34 | G01 | `cbrd_26659_gap_load_sa_nolog_cs-4 : NOK source.policy` | 미실행 |
| 14 | [gap_load_sa_nolog_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_gap_load_sa_nolog_sc/cases/cbrd_26659_gap_load_sa_nolog_sc.sh) | A·shard 33 | G01 | `cbrd_26659_gap_load_sa_nolog_sc-4 : NOK source.policy` | 미실행 |
| 15 | [gap_load_sa_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_gap_load_sa_sc/cases/cbrd_26659_gap_load_sa_sc.sh) | A·shard 35 | G01 | `cbrd_26659_gap_load_sa_sc-4 : NOK source.policy` | 미실행 |
| 16 | [gap_replace_select_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_gap_replace_select_cs/cases/cbrd_26659_gap_replace_select_cs.sh) | A·shard 16 | G01 | `cbrd_26659_gap_replace_select_cs-4 : NOK source.policy` | 미실행 |
| 17 | [gap_replace_select_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_gap_replace_select_sc/cases/cbrd_26659_gap_replace_select_sc.sh) | A·shard 45 | G01 | `cbrd_26659_gap_replace_select_sc-4 : NOK source.policy` | 미실행 |
| 18 | [gap_unload_sa_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_gap_unload_sa_cs/cases/cbrd_26659_gap_unload_sa_cs.sh) | A·shard 20 | G01 | `cbrd_26659_gap_unload_sa_cs-4 : NOK source.policy` | 미실행 |
| 19 | [gap_unload_sa_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_gap_unload_sa_sc/cases/cbrd_26659_gap_unload_sa_sc.sh) | A·shard 29 | G01 | `cbrd_26659_gap_unload_sa_sc-4 : NOK source.policy` | 미실행 |
| 20 | [notify_abort](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_notify_abort/cases/cbrd_26659_notify_abort.sh) | A·shard 19 | G02 | `cbrd_26659_notify_abort-1 : NOK controller incomplete: ../../oos_common/oos15_notify.sh: line 28: CUB...` | 미실행 |
| 21 | [notify_commit](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_notify_commit/cases/cbrd_26659_notify_commit.sh) | A·shard 20 | G02 | `cbrd_26659_notify_commit-1 : NOK controller incomplete: ../../oos_common/oos15_notify.sh: line 28: CU...` | 미실행 |
| 22 | [notify_nodrop](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_notify_nodrop/cases/cbrd_26659_notify_nodrop.sh) | A·shard 14 | G02 | `cbrd_26659_notify_nodrop-1 : NOK controller incomplete: ../../oos_common/oos15_notify.sh: line 28: CU...` | 미실행 |
| 23 | [partition_add_drop_list](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_partition_add_drop_list/cases/cbrd_26659_partition_add_drop_list.sh) | A·shard 16 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 24 | [partition_add_drop_range](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_partition_add_drop_range/cases/cbrd_26659_partition_add_drop_range.sh) | A·shard 11 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 25 | [partition_hash_coalesce](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_partition_hash_coalesce/cases/cbrd_26659_partition_hash_coalesce.sh) | A·shard 10 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 26 | [partition_hash_resize](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_partition_hash_resize/cases/cbrd_26659_partition_hash_resize.sh) | A·shard 19 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 27 | [partition_move](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_partition_move/cases/cbrd_26659_partition_move.sh) | A·shard 29 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 28 | [partition_partition_rejection](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_partition_partition_rejection/cases/cbrd_26659_partition_partition_rejection.sh) | A·shard 01 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 29 | [partition_promote_list](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_partition_promote_list/cases/cbrd_26659_partition_promote_list.sh) | A·shard 32 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 30 | [partition_promote_range](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_partition_promote_range/cases/cbrd_26659_partition_promote_range.sh) | A·shard 12 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 31 | [partition_remove](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_partition_remove/cases/cbrd_26659_partition_remove.sh) | A·shard 40 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 32 | [partition_reorganize_list](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_partition_reorganize_list/cases/cbrd_26659_partition_reorganize_list.sh) | A·shard 21 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 33 | [partition_reorganize_list_merge](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_partition_reorganize_list_merge/cases/cbrd_26659_partition_reorganize_list_merge.sh) | A·shard 28 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 34 | [partition_reorganize_range](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_partition_reorganize_range/cases/cbrd_26659_partition_reorganize_range.sh) | A·shard 08 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 35 | [partition_reorganize_range_merge](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_partition_reorganize_range_merge/cases/cbrd_26659_partition_reorganize_range_merge.sh) | A·shard 07 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 36 | [partition_repartition](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_partition_repartition/cases/cbrd_26659_partition_repartition.sh) | A·shard 42 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 37 | [partition_route_hash](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_partition_route_hash/cases/cbrd_26659_partition_route_hash.sh) | A·shard 44 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 38 | [partition_route_list](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_partition_route_list/cases/cbrd_26659_partition_route_list.sh) | A·shard 46 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 39 | [partition_route_range](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_partition_route_range/cases/cbrd_26659_partition_route_range.sh) | A·shard 47 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 40 | [policy_contract](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_policy_contract/cases/cbrd_26659_policy_contract.sh) | A·shard 09 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 41 | [qualified_reuse](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10fb4b63f741a4cc231f37b8184b80839f9d452b/shell/_40_guava/cbrd_26659_qualified_reuse/cases/cbrd_26659_qualified_reuse.sh) | B·shard 37 | G03 | `cbrd_26659_qualified_reuse-1 : NOK qualified: intended churn/storage assertions failed (controller ex...` | 미실행 |
| 42 | [record_target0](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_record_target0/cases/cbrd_26659_record_target0.sh) | A·shard 39 | G05 | `cbrd_26659_record_target0-1 : NOK record boundary assertion failed: ../../oos_record_boundaries/contr...` | 미실행 |
| 43 | [record_target10](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_record_target10/cases/cbrd_26659_record_target10.sh) | A·shard 21 | G05 | `cbrd_26659_record_target10-1 : NOK record boundary assertion failed: ../../oos_record_boundaries/cont...` | 미실행 |
| 44 | [schema_attributes_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_schema_attributes_cs/cases/cbrd_26659_schema_attributes_cs.sh) | A·shard 14 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 45 | [schema_attributes_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_schema_attributes_sa/cases/cbrd_26659_schema_attributes_sa.sh) | A·shard 04 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 46 | [schema_rewrites_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_schema_rewrites_cs/cases/cbrd_26659_schema_rewrites_cs.sh) | A·shard 35 | G01 | `bash: ../../cbrd_26659_schema_policy/cases/policy_ddl.sh: No such file or directory` | 미실행 |
| 47 | [schema_rewrites_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_schema_rewrites_sa/cases/cbrd_26659_schema_rewrites_sa.sh) | A·shard 31 | G12 | `bash: ../../cbrd_26659_policy_contract/cases/policy_metadata.sh: No such file or directory` | 미실행 |
| 48 | [serialized_chunks](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_serialized_chunks/cases/cbrd_26659_serialized_chunks.sh) | A·shard 43 | G07 | `ERROR: No such file or directory` | 미실행 |
| 49 | [show_contract](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_show_contract/cases/cbrd_26659_show_contract.sh) | A·shard 19 | G02 | `show_controller.sh: line 15: CUBRID_TMP: unbound variable` | native PASS |
| 50 | [show_partitions](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_show_partitions/cases/cbrd_26659_show_partitions.sh) | A·shard 02 | G02 | `partition_controller.sh: line 15: CUBRID_TMP: unbound variable` | 미실행 |
| 51 | [snapshots_reclaim](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_snapshots_reclaim/cases/cbrd_26659_snapshots_reclaim.sh) | A·shard 10 | G09 | `cbrd_26659_snapshots_reclaim-1 : NOK snapshot/reclaim controller failed (controller exit 1); retain o...` | 미실행 |
| 52 | [tde_crash_committed](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_tde_crash_committed/cases/cbrd_26659_tde_crash_committed.sh) | A·shard 02 | G10 | `cbrd_26659_tde_crash_committed.sh: line 5: ../../cbrd_26659_crash_committed/cases/cbrd_26659_crash_co...` | 미실행 |
| 53 | [tde_crash_undo](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_tde_crash_undo/cases/cbrd_26659_tde_crash_undo.sh) | A·shard 10 | G11 | `cbrd_26659_tde_crash_undo.sh: line 5: ../../cbrd_26659_crash_undo/cases/cbrd_26659_crash_undo.sh: No ...` | 미실행 |
| 54 | [tde_storage](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_tde_storage/cases/cbrd_26659_tde_storage.sh) | A·shard 34 | G13 | `bash: ../../cbrd_26659_tde_wal/cases/tde_observe.sh: No such file or directory` | 미실행 |
| 55 | [utility_compact_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_utility_compact_cs/cases/cbrd_26659_utility_compact_cs.sh) | A·shard 45 | G01 | `bash: /home/cubrid-testcases-private-ex/shell/_40_guava/oos_utility/../cbrd_26659_schema_policy/cases...` | 미실행 |
| 56 | [utility_compact_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_utility_compact_sa/cases/cbrd_26659_utility_compact_sa.sh) | A·shard 28 | G01 | `bash: /home/cubrid-testcases-private-ex/shell/_40_guava/oos_utility/../cbrd_26659_schema_policy/cases...` | 미실행 |
| 57 | [utility_policy_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_utility_policy_cs/cases/cbrd_26659_utility_policy_cs.sh) | A·shard 19 | G01 | `bash: /home/cubrid-testcases-private-ex/shell/_40_guava/oos_utility/../cbrd_26659_schema_policy/cases...` | 미실행 |
| 58 | [utility_policy_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_utility_policy_sa/cases/cbrd_26659_utility_policy_sa.sh) | A·shard 34 | G01 | `bash: /home/cubrid-testcases-private-ex/shell/_40_guava/oos_utility/../cbrd_26659_schema_policy/cases...` | 미실행 |
| 59 | [utility_policy_sa_nolog](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_utility_policy_sa_nolog/cases/cbrd_26659_utility_policy_sa_nolog.sh) | A·shard 30 | G01 | `bash: /home/cubrid-testcases-private-ex/shell/_40_guava/oos_utility/../cbrd_26659_schema_policy/cases...` | 미실행 |
| 60 | [utility_policy_unload_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10a8fc82d34cd2c54c2caa403886e3528852d6fe/shell/_40_guava/cbrd_26659_utility_policy_unload_sa/cases/cbrd_26659_utility_policy_unload_sa.sh) | A·shard 39 | G01 | `bash: /home/cubrid-testcases-private-ex/shell/_40_guava/oos_utility/../cbrd_26659_schema_policy/cases...` | 미실행 |
| 61 | [cbrd_27237_rollback_vacuum](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/10fb4b63f741a4cc231f37b8184b80839f9d452b/shell/_40_guava/cbrd_27237_rollback_vacuum/cases/cbrd_27237_rollback_vacuum.sh) | B·shard 22 | G08 | `cbrd_27237_rollback_vacuum-1 : NOK rollback-after-vacuum intended pre-image failed (controller exit 1...` | 미실행 |

## 완료한 단위와 남은 작업

이번 단위는 61개 증상 분류와 첫 대표 1개 실행을 마쳤다. 61개의 엔진·TC·환경 원인을 모두 확정한 것이 아니다. 다음 후보는 가장 큰 39개 `policy_ddl.sh` 누락 그룹의 대표 한 개다. 과거 helper가 Git에는 존재했는지, CI에서 배치·정리 또는 선행 실행으로 없어졌는지와 구체 policy assertion을 구분해야 한다.

`CUBRID_TMP` 그룹의 나머지 4개, 다른 56개 및 원래 장시간 PASS 3개의 현재 검증도 남아 있다. TC 재활성화와 일반/heavy 실행 위치 결정은 실제 검증과 리뷰 후 별도 진행한다. 기존 CI 41031622190의 `cbrd_25977-16` 실패와 SQL 전체 집계 문제를 이 대표 PASS로 해제하지 않는다. HA·전체 커버리지·실제 TC 리뷰와 병합을 포함한 CBRD-26659/Work456은 미완료다.
