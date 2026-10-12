# PR8128 SQL 수리 검증 기록

작성·갱신: 2026-10-13, Asia/Seoul. Work item 332.

Engine PR8128의 partition HA replication assertion을 수리했다. 대상 SQL 14개는 최종 커밋의 새 DB 독립 실행에서 모두 통과했다. 원래 72-case 순서 검증과 한 번의 CI qualification은 진행 중이며, 완료 결과를 아래에 추가한다. 합의된 제외 규칙과 기존 정답·assertion은 보존했다.

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
| `cbrd_26659_oos_partition_routing.sql` | `/home/vimkim/tmp/s332-final-01` | PASS / 1 success, 0 fail / 0 | 진행 중 |
| `cbrd_26659_oos_representation.sql` | `/home/vimkim/tmp/s332-final-02` | PASS / 1 success, 0 fail / 0 | 진행 중 |
| `cbrd_26659_oos_schema.sql` | `/home/vimkim/tmp/s332-final-03` | PASS / 1 success, 0 fail / 0 | 진행 중 |
| `cbrd_26659_oos_sql01_insert_select.sql` | `/home/vimkim/tmp/s332-final-04` | PASS / 1 success, 0 fail / 0 | 진행 중 |
| `cbrd_26659_oos_sql04_delete.sql` | `/home/vimkim/tmp/s332-final-05` | PASS / 1 success, 0 fail / 0 | 진행 중 |
| `cbrd_26659_oos_sql04_update.sql` | `/home/vimkim/tmp/s332-final-06` | PASS / 1 success, 0 fail / 0 | 진행 중 |
| `cbrd_26659_oos_sql05_bigone.sql` | `/home/vimkim/tmp/s332-final-07` | PASS / 1 success, 0 fail / 0 | 진행 중 |
| `cbrd_26659_oos_sql05_constraints.sql` | `/home/vimkim/tmp/s332-final-08` | PASS / 1 success, 0 fail / 0 | 진행 중 |
| `cbrd_26659_oos_sql05_transactions.sql` | `/home/vimkim/tmp/s332-final-09` | PASS / 1 success, 0 fail / 0 | 진행 중 |
| `cbrd_26659_oos_sql06_triggers.sql` | `/home/vimkim/tmp/s332-final-10` | PASS / 1 success, 0 fail / 0 | 진행 중 |
| `cbrd_26659_oos_sql07_read_paths.sql` | `/home/vimkim/tmp/s332-final-11` | PASS / 1 success, 0 fail / 0 | 진행 중 |
| `cbrd_26659_oos_sql09_lob_copy.sql` | `/home/vimkim/tmp/s332-final-12` | PASS / 1 success, 0 fail / 0 | 진행 중 |
| `cbrd_26659_oos_sql09_lob_maxcols.sql` | `/home/vimkim/tmp/s332-final-13` | PASS / 1 success, 0 fail / 0 | 진행 중 |
| `cbrd_26659_oos_storage_policy.sql` | `/home/vimkim/tmp/s332-final-14` | PASS / 1 success, 0 fail / 0 | 진행 중 |

## 원래 72-case 순서 검증

진행 중: `/home/vimkim/tmp/s332-f72`. Latest CI shard에서 추출한 72개 실제 순서를 `original72.txt`에 보존했다. 이 순서는 native lexical discovery와 동일함을 확인했다. Cases/answers와 fixtures를 복사한 실제 selection을 사용하며 expected-case list로 임의 순서를 주입하지 않았다.

## CMake 검사

`/home/vimkim/tmp/oos-sql-repair-332/ctest-final`: **35/35 pass**, exit 0, 165.18초. Live build/test interface `just ctest`로 수행했다. Generated CTest fixture의 hardcoded install/registry 경로만 disposable copy로 바꾸고 실행 후 모두 byte-for-byte 복원했다 (`generated-fixtures-restored.json`). 기존 host DB와 registry를 CTest fixture로 사용하지 않았다.

## 게시 전 리뷰와 CI

Engine 비교 기준은 `a5da823b2a84e95b4b22d48abe4a3f9fd601c176`, Spec은 [합의된 계획](/home/vimkim/gh/my-cubrid-docs/cbrd-26659/ci-repair/plan.md)이다. Standards/Spec 두 축 code-review는 최종 local 검증 이후 진행한다. Public TC README만 scoped 기록을 게시하고 private TC는 변경하지 않는다. Engine head가 변경되므로 한 번의 `/run all`을 실행한 뒤 terminal 결과를 기록한다. 현재는 게시와 CI trigger 전이다.

## 보존된 제외 항목

Full partition은 기존 제외 판정을 유지한다. 이번 수리는 14개 정상화에 필요한 공통 crash 원인을 수리했으며 destination physical ownership 등 별도 partition 결함의 해결을 주장하지 않는다. Full partition의 logical golden pass는 별도 실행 결과로 기록한다. 기존 다섯 shell 제외 항목의 답안·discovery·실행 정책은 바꾸지 않았고 최종 CI의 실제 결과를 따로 기록한다.

Raw 증거는 `/home/vimkim/tmp/oos-sql-repair-332`와 각 `s332-*` attempt에 보존한다. 최신 CI의 역사적 receipt/run identity와 이전 문서 main의 사용자 변경도 보존한다.
