# PR8128 SQL 수리 검증 기록

작성·갱신: 2026-10-13, Asia/Seoul. Work item 332.

Engine PR8128의 partition HA replication assertion을 수리했다. 대상 SQL 14개는 최종 커밋의 새 DB 독립 실행, 원래 72-case 순서와 단일 CI에서 모두 통과했다. 전체 CI는 shell 7개 실패로 FAILURE다. 합의된 제외 규칙과 기존 정답·assertion은 보존했다. Work item 332의 필수 SQL 수리·검증과 terminal 보고를 완료하고 다음 인간 지시를 기다린다.

## 수리 원인과 변경

기준 Engine `a5da823b2a84e95b4b22d48abe4a3f9fd601c176`의 partition key UPDATE는 destination INSERT 후 source DELETE를 수행한다. Destination에서 OOS insert LSA를 소비한 뒤, source의 index DELETE도 같은 `thread_p->oos_oids`를 따라 `RVREPL_OOS_INSERT`를 발행하여 빈 큐 assertion에 도달했다.

계측한 최소 재현의 같은 transaction에서 다음 전이를 관측했다. 식별자를 제외한 신호만 옮겼다.

```text
destination INSERT: is_insert=1, oids=1, queue=1
OOS consume: rcvindex=138 (RVREPL_OOS_INSERT), queue=1
source DELETE: is_insert=0, action=FOR_MOVE, oids=1, queue=0
OOS consume: rcvindex=138, queue=0 -> assertion
```

수리 커밋은 `1ef86a7efa34002e971b1b30bcf5d451e9db441b`이다. `src/transaction/locator_sr.c`의 해당 post-image 복제 루프를 `is_insert && heap_recdes_contains_oos(recdes)`로 제한했다. DELETE의 primary-key replication과 `repl_log_insert`의 큐 assertion은 유지한다. 가설 패치 후 source DELETE의 `queue=0` 진입은 남지만 OOS consume 호출은 사라졌고, UPDATE 및 독립 payload digest가 정답과 일치했다. 두 임시 계측 지점은 최종 source에서 제거했다.

원래 partition SQL과 그 정답을 regression seam으로 사용했다. Locator/primary-key/HA 경로를 실행하지 않는 queue 단위 모형 테스트를 새로 추가하지 않았다. SQL/answer 파일은 수정하지 않았다.

## 재현과 전후 대조

Native invocation은 `TESTKIT_NATIVE=sql TESTKIT_CONTAIN=1 testkit sql -c <copied sql.conf>`이다. 재현 wrapper와 모든 명령·출력은 `/home/vimkim/tmp/oos-sql-repair-332/run-sql.sh` 및 각 attempt의 `driver.py`, `command.json`, `run.log`에 보존한다. Native artifact 검증은 공유 `testkit-focused.py verify --suite sql`로 수행했다. Process exit 0만으로 통과를 판단하지 않았다.

| 실행 | Attempt | 실제 결과 |
| --- | --- | --- |
| 원래 partition, unpatched Debug | `/home/vimkim/tmp/s332-p01` | 0 pass / 1 fail; UPDATE `-21019`, `repl_log_insert` crash; runner exit 0 / verifier 1 / cleanup 0 |
| Fresh routing 대조 | `/home/vimkim/tmp/s332-r01` | 1/1 pass; golden 및 cleanup 통과 |
| 최소 OOS partition move, 반복 | `/home/vimkim/tmp/s332-m01`, `s332-m02` | UPDATE `-21019`; verifier 1, cleanup 0 |
| 이동 없음 / inline / PK 없음 / HA off | `s332-c-no-move`, `s332-c-inline02`, `s332-c-no-pk`, `s332-c-ha-off` | 각각 1/1 golden·artifact·cleanup pass |
| 최소 재현, 두 지점 계측 | `/home/vimkim/tmp/s332-probe01` | 위의 destination 소비 후 source 재소비를 관측; fail |
| 최소 재현, guard와 같은 계측 | `/home/vimkim/tmp/s332-fprobe01` | 1/1 pass; source DELETE가 OOS consume을 호출하지 않음 |
| 원래 partition → routing → schema → constraints | `/home/vimkim/tmp/s332-fpseq` | 4/4 golden·artifact pass, cleanup 0; crash report 없음 |
| 원래 72-case, unpatched Debug | `/home/vimkim/tmp/s332-b72` | 69 pass / 3 fail; partition, schema, constraints |

최소 재현은 한 행 CREATE/INSERT, partition 경계를 넘는 PK UPDATE, 독립적으로 계산한 payload 길이·digest 검증으로 줄였다. 이동/PK/OOS payload/HA 조건을 각각 없앤 대조에서 증상이 사라졌다. 최초 setup의 locale 생성과 HA slot 시작은 약 40초 이상의 고정 비용이며, 최소 SQL 실행 자체는 약 0.1초였다. Locale 생성 결과만 다음 disposable install에 재사용하여 반복 setup을 줄였고 fresh DB 계약은 유지했다.

`s332-c-inline`의 최초 임시 대조 답안은 BIT의 SQL MD5를 binary bytes에 계산해 digest 비교가 실패했다. UPDATE 자체는 성공했다. Lowercase hex 문자열에 대한 독립 MD5 계산으로 임시 답안을 바로잡은 `s332-c-inline02`가 통과했다. 이 임시 답안 오류와 corrected attempt를 모두 보존하며 원본 golden은 변경하지 않았다.

## Runtime identity와 비교 한계

- 최종 Engine/source/install: `1ef86a7efa34002e971b1b30bcf5d451e9db441b`; `cubrid_rel`은 `11.5.0.2639-1ef86a7`, 64-bit Debug. Configure preset `debug_gcc`, CMake build type `Debug`.
- Local public TC: `1dec9d147547d8d404b6705b742e6e6fa0a58b98`, branch `tc/pr-8128`. CI의 이전 public TC `1a556a0752073aaad573bf87d53f3eb75f398138`와 SQL/answer/fixture 내용은 동일하고 그 이후 변경은 README뿐이다.
- Private TC: `a2054f965a20241b87dc9577585ccc8a8cb6ab97`, 변경하지 않음.
- Native testkit: binary SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`, `cubrid-testkit dev`. Go build metadata revision `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`, modified build. Installed runner를 사용했고 설치·업데이트하지 않았다.
- Backend: native sqlsuite의 JDBC/CQT executor, `test_default.xml`, JDK `1.8.0_462`. JDBC jar SHA-256 `97407928aa3d31dd6cae0039136814177ec28e1aa2cb1c161c8001d8fb54c8d7`.
- CTP assets: retained reference `/home/vimkim/tmp/oos-shell-conversion-20261012/final14-a03/CTP`; 원 기록 revision `9c62858b10005d721546cc007be260844033b9e9`와 기존 local asset 변경을 identity에 보존했다. Legacy CTP runner를 실행하지 않았다.
- Server/HA sections `ha_mode=yes`; requested charset `en_US`, actual native createdb charset `en_US.utf8`; page/log page 16K, disposable basic DB. Backend의 version-based charset 적용과 containment의 private namespace를 구분한다.
- 실행마다 copied install/CTP/HOME/registry와 retained expected-case manifest를 사용했다. 기존 `/home/vimkim/tmp/oos-developer-regressions-20261008/validation.lock` 아래 직렬 실행했다. 모든 검증된 attempt는 native process/owned DB/registry와 configuration cleanup을 통과했다.
- Host install, `.env`, workenv state와 CCI version 파일을 빌드 전 보존하고 빌드 후 복원했다. Host DB를 실행하거나 install selection을 변경하지 않았다.

Local Debug/native runtime을 CI-equivalent라고 부르지 않는다. 최신 CI run38245729674는 57/72 pass와 43–57번의 15 연속 실패를 기록했다. Native unpatched 순서 실행은 69/72 pass이며, 서버 crash 뒤 JDBC가 일부 회복했다. Native의 schema 후반 `-190` 및 constraints의 `-1385`는 각각 fresh DB에서 원래 정답을 통과했다. 모든 CI 실패를 native에서 같은 방식으로 재현했다고 주장하지 않으며, 14개 각각의 최종 CI 판정을 확인한다.

기준 Engine의 fresh 독립 검증도 14/14 통과했다 (`before-verified14.json`). 수리 커밋과 기존 baseline batch의 시점이 겹쳐 5개 attempt는 revision mismatch로 시작 전 차단됐다. 이를 TC 실패로 계산하지 않았다. 검사를 우회하지 않고 같은 checkout을 잠시 `a5da823`으로 전환하여 새 `s332-bretry-01`–`05`에서 검증한 뒤 원래 task branch/commit으로 복원했다. 차단된 attempt와 보완 attempt는 모두 보존했다.

## 최종 새 DB 독립 검증

아래 14행은 모두 최종 Engine `1ef86a7`, public TC `1dec9d1`, 위 native runner/JDBC/HA identity를 사용한다. 각 attempt의 `preflight.log`, `identities.json`, `expected-cases.txt`, `result-dir.txt`, `verify.log`, copied `.result`, XML, `cleanup.json`/`cleanup.exit`가 실제 판정 근거다. Golden 전체 비교 통과로 본래 assertion 도달을 확인했다.

| Target case | Fresh DB attempt | Golden / artifact / cleanup | 원래 72-case / CI |
| --- | --- | --- | --- |
| `cbrd_26659_oos_partition_routing.sql` | `/home/vimkim/tmp/s332-final-01` | PASS / 1 success, 0 fail / 0 | 원래 순서 PASS; CI PASS (run38271660063, shard09) |
| `cbrd_26659_oos_representation.sql` | `/home/vimkim/tmp/s332-final-02` | PASS / 1 success, 0 fail / 0 | 원래 순서 PASS; CI PASS (run38271660063, shard09) |
| `cbrd_26659_oos_schema.sql` | `/home/vimkim/tmp/s332-final-03` | PASS / 1 success, 0 fail / 0 | 원래 순서 PASS; CI PASS (run38271660063, shard09) |
| `cbrd_26659_oos_sql01_insert_select.sql` | `/home/vimkim/tmp/s332-final-04` | PASS / 1 success, 0 fail / 0 | 원래 순서 PASS; CI PASS (run38271660063, shard09) |
| `cbrd_26659_oos_sql04_delete.sql` | `/home/vimkim/tmp/s332-final-05` | PASS / 1 success, 0 fail / 0 | 원래 순서 PASS; CI PASS (run38271660063, shard09) |
| `cbrd_26659_oos_sql04_update.sql` | `/home/vimkim/tmp/s332-final-06` | PASS / 1 success, 0 fail / 0 | 원래 순서 PASS; CI PASS (run38271660063, shard09) |
| `cbrd_26659_oos_sql05_bigone.sql` | `/home/vimkim/tmp/s332-final-07` | PASS / 1 success, 0 fail / 0 | 원래 순서 PASS; CI PASS (run38271660063, shard09) |
| `cbrd_26659_oos_sql05_constraints.sql` | `/home/vimkim/tmp/s332-final-08` | PASS / 1 success, 0 fail / 0 | 원래 순서 PASS; CI PASS (run38271660063, shard09) |
| `cbrd_26659_oos_sql05_transactions.sql` | `/home/vimkim/tmp/s332-final-09` | PASS / 1 success, 0 fail / 0 | 원래 순서 PASS; CI PASS (run38271660063, shard09) |
| `cbrd_26659_oos_sql06_triggers.sql` | `/home/vimkim/tmp/s332-final-10` | PASS / 1 success, 0 fail / 0 | 원래 순서 PASS; CI PASS (run38271660063, shard09) |
| `cbrd_26659_oos_sql07_read_paths.sql` | `/home/vimkim/tmp/s332-final-11` | PASS / 1 success, 0 fail / 0 | 원래 순서 PASS; CI PASS (run38271660063, shard09) |
| `cbrd_26659_oos_sql09_lob_copy.sql` | `/home/vimkim/tmp/s332-final-12` | PASS / 1 success, 0 fail / 0 | 원래 순서 PASS; CI PASS (run38271660063, shard09) |
| `cbrd_26659_oos_sql09_lob_maxcols.sql` | `/home/vimkim/tmp/s332-final-13` | PASS / 1 success, 0 fail / 0 | 원래 순서 PASS; CI PASS (run38271660063, shard09) |
| `cbrd_26659_oos_storage_policy.sql` | `/home/vimkim/tmp/s332-final-14` | PASS / 1 success, 0 fail / 0 | 원래 순서 PASS; CI PASS (run38271660063, shard09) |

## 원래 72-case 순서 검증

`/home/vimkim/tmp/s332-f72`: **72 success / 0 fail**, runner exit 0, verifier 0, cleanup 0; 617.50초. Latest CI shard에서 추출한 72개 실제 순서를 `original72.txt`에 보존했다. 이 순서는 native lexical discovery와 동일하다. Expected manifest와 실제 로그의 72개 identity·순서가 일치하고, complete XML의 case set·각 verdict도 일치한다. XML의 내부 배열 순서는 실행 순서로 해석하지 않았다. 대상 14개는 각각 44–57번에서 PASS였다 (`final72-verified-targets14.json`). Excluded full partition도 43번에서 원래 logical golden을 통과했다. Cases/answers와 fixtures를 복사한 실제 selection을 사용하며 expected-case list로 임의 순서를 주입하지 않았다.

## CMake 검사

`/home/vimkim/tmp/oos-sql-repair-332/ctest-final`: **35/35 pass**, exit 0, 165.18초. Live build/test interface `just ctest`로 수행했다. Generated CTest fixture의 hardcoded install/registry 경로만 disposable copy로 바꾸고 실행 후 모두 byte-for-byte 복원했다 (`generated-fixtures-restored.json`). 기존 host DB와 registry를 CTest fixture로 사용하지 않았다.

## 게시 전 리뷰와 CI

Engine 비교 기준은 `a5da823b2a84e95b4b22d48abe4a3f9fd601c176`, Spec은 [합의된 계획](plan.md)이다. 최종 local 검증 후 독립 agent 두 개로 `code-review`를 수행했다. **Standards 0건 / Spec 0건**이다. Standards는 개인 정책·유효한 subdirectory 지침·CONTRIBUTING·문서 index 기준과 smell baseline을 확인했다. Spec은 각 fresh DB 생성/단일 case XML/verifier/cleanup, 복사 SQL·answer·fixture 해시, 원래 72개 실제 순서와 complete XML identity/verdict, 최소 계측 전후 경로를 확인했다. 문서의 runtime 차이와 제외 범위도 유지하며 게시 전 준비를 충족한다고 판단했다.

Engine `1ef86a7efa34002e971b1b30bcf5d451e9db441b`과 public TC README `d7bec2fdeb6a19573300e1a624e03e0b87eb9e96`를 각각 PR head branch에 게시했다. Private TC는 `a2054f965a20241b87dc9577585ccc8a8cb6ab97` 그대로다. TC baseline ancestry 검사를 두 repository에서 통과한 뒤 [단일 `/run all` receipt](https://github.com/CUBRID/cubrid/pull/8128#issuecomment-6127511688)를 남겼다. 다섯 gha-ci context가 같은 [run38271660063, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/38271660063)을 가리키는 pickup을 확인했다. 이 실행은 2026-10-13 02:32:56 KST에 **FAILURE**로 종료했다. 사용자 요청에 따라 후반 상태 확인은 10분 간격으로 수행했다. 추가 수정·push·CI trigger/rerun은 하지 않았다.

### Terminal counts와 provenance

| Suite | Planned / tests | Run | Passed | Failures | Errors | Skipped | Unrun | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SQL | 17488 | 17488 | 17488 | 0 | 0 | 0 | 0 | PASS |
| Shell | 3307 | 3277 | 3270 | 7 | 0 | 30 | 0 | FAIL |
| Medium | 975 | 975 | 975 | 0 | 0 | 0 | 0 | PASS |

Release와 Debug build context 모두 SUCCESS다. 세 suite의 모든 shard가 Engine `1ef86a7`, build mode `debug`, build run38271660063/attempt1, namespace `pr`을 보고했다. SQL/medium은 public TC `d7bec2f`, shell은 private TC `a2054f9`, 모두 branch `tc/pr-8128`이다. SQL/answer/fixture 내용은 local qualification 때와 같고 public README만 추가 게시했다. Shell의 30 skipped와 0 unrun을 별도로 기록하며 skipped를 실행 통과로 세지 않는다.

`cubrid-ci collect 8128 --commit 1ef86a7efa34002e971b1b30bcf5d451e9db441b --wait --json`은 exit 0으로 세 suite의 complete evidence를 수집했다. 이는 수집 성공이며 전체 CI 성공을 뜻하지 않는다. Command-result/manifest v2, matching observation request/result v1, suite-summary/raw-index/failure v2 schema를 검증했다. Request/result의 identity, exact SHA·run/attempt, manifest 일치, 모든 raw 파일의 길이·SHA-256, summary digest, count reconciliation, failure metadata/message/diff 존재를 확인했다. GitHub `collect` job의 `Guard 3 of 3, and the summary` 단계도 FAILURE였다. 이 guard는 failed count가 양수이면 실패시키므로 수집한 shell 7 fail과 일치한다.

Retained bundle: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/1ef86a7efa34002e971b1b30bcf5d451e9db441b`. Matching observation은 `observations/20261012T173334.412317894Z-2803200-0`이다. 검증 명령은 `/usr/bin/python3 /home/vimkim/tmp/oos-sql-repair-332/validate-ci.py`, 결과는 같은 root의 `validated-terminal.json`이다.

대상 14개는 complete SQL JUnit의 shard **09**에 각각 정확히 한 번 존재하며 모두 failure/error/skipped가 없는 **PASS**다. 원래 72개 identity도 같은 shard에서 각각 한 번 존재하고 **72/72 PASS**다. 이는 실패 목록에 없다는 추정이 아니라 실제 positive testcase records를 검증한 결과다. 실행 순서의 증거는 앞 절의 native `s332-f72` manifest·actual log이며, JUnit 배열 순서를 실행 순서로 해석하지 않는다. CI XML은 bundle의 `providers/github-actions/runs/38271660063/attempts/1/test_sql/raw/shards/09/linux_sql_64bit.xml`에 보존한다.

### 제외·추가 실패와 TC Merge Gate

합의된 shell 제외 5개는 이번에도 모두 FAIL이다. Full partition은 logical JUnit PASS이며 기존 제외 분류와 별도 physical defect 상태를 유지한다.

| Shell case basename | 이번 실제 관측 | 판정 |
| --- | --- | --- |
| `cbrd_27064.sh` | Delete 700건과 update 2400건의 extractor `rc=-10`, target count 0 | 합의된 기존 CDC 제외 유지 |
| `cbrd_26659_partition_owner.sh` | Destination ownership mismatch, retained CBRD-27089 | 합의된 예상 실패 제외 유지 |
| `cbrd_26659_snapshots_reclaim.sh` | Snapshot/reclaim controller exit 1 | 합의된 예상 실패 제외 유지; 이번 underlying page-return 원인은 재진단하지 않음 |
| `cbrd_26659_utility_sa_physical.sh` | Source values/schema/checkdb와 LOB transfer는 OK, utility controller status 1 | 합의된 예상 실패 제외 유지; 이번 underlying destination placement 원인은 재진단하지 않음 |
| `cbrd_27237_rollback_vacuum.sh` | Rollback-after-vacuum pre-image controller exit 1 | 합의된 예상 실패 제외 유지; 이번 underlying corruption 원인은 재진단하지 않음 |
| `cbrd_27075.sh` | Subcheck 1 NOK; 4K·8K `EXTRACT_ERR=1`, 16K는 0; total corruption 0 | 추가 관측된 기존 CDC 실패. Base run36570256001도 subcheck 1과 extraction errors를 보고했고 ADR-0005의 deferred gap이다. 실행과 올바른 기대를 유지하며 SQL14 수리와 구분 |
| `hide_cubrid_replay.sh` | Subcheck 6 NOK, `qa8.answer` mismatch | 추가 잔여 실패, 원인 미확정. Base의 subcheck 7 / `qa9.answer`, 이전 full head의 `qa9`·`qa10`과 signature가 달라 동일 baseline 원인으로 제외하지 않음 |

추가 두 항목의 전체 경로와 역사적 비교는 [추적 표](README.md)에 기록했다. 이번 run의 per-case evidence는 위 bundle의 `providers/github-actions/runs/38271660063/attempts/1/test_shell/failures/` 아래 metadata/message/diff다. 비교 결과는 `/home/vimkim/tmp/oos-sql-repair-332/additional-failure-comparison.json`이다. SQL 대상 잔여 실패는 **0**이며 shell 잔여를 이 수리의 완료나 전체 CI green으로 바꾸지 않는다.

[Public TC #3688](https://github.com/CUBRID/cubrid-testcases/pull/3688)와 [private TC #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365)는 둘 다 **OPEN draft**이고 base는 `feature/oos-merge`다. 개인 정책에 따른 **TC Merge Gate는 미해제**이며 인간의 merge 또는 close가 필요하다. Live PR checks에는 이름이 `TC Merge Gate`인 context가 없었고 `gh pr checks --required`도 `no required checks reported`(exit 1)를 반환했다. 이 관측을 정책상 merge 허용으로 해석하지 않는다. TC PR merge/close나 branch 삭제는 수행하지 않았다.

## 보존된 제외 항목

Full partition은 기존 제외 판정을 유지한다. 이번 수리는 14개 정상화에 필요한 공통 crash 원인을 수리했으며 destination physical ownership 등 별도 partition 결함의 해결을 주장하지 않는다. Full partition의 logical golden pass는 별도 실행 결과로 기록한다. 기존 다섯 shell 제외 항목의 답안·discovery·실행 정책은 바꾸지 않았고 최종 CI의 실제 결과를 따로 기록한다.

Raw 증거는 `/home/vimkim/tmp/oos-sql-repair-332`와 각 `s332-*` attempt에 보존한다. 최신 CI의 역사적 receipt/run identity와 이전 문서 main의 사용자 변경도 보존한다.
