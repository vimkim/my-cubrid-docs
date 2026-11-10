# PR #8299 CI 분석: head 855f220 (feature/oos-merge 50619ce53 merge 후)

PR [#8299](https://github.com/CUBRID/cubrid/pull/8299) (CBRD-27785, base `feature/oos-merge`)에 base 최신을 merge한 뒤 돌린 전체 CI의 실패가 이 PR 때문인지 판단한다.
분석일은 2026-11-11, Asia/Seoul이다. 대상 run은 [42801815682, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/42801815682)이다.

> **수집기 판정은 경고(warning)이다.** `test_sql`은 shard 03이 2시간 제한에 걸려 취소되어 job 단위 실패(`job_level_failure`)로 남았고, 수집기가 검증한 suite 결과가 없다. merge-base 쪽 `test_sql`도 수집기 무결성 검사로 실패했다. 그래서 `report_mode.py`는 `warning`, `regression_conclusions_allowed: false`를 냈다.
> 아래의 case 단위 비교는 관찰한 증거를 정리한 것이다. 수집기 gate가 허용한 회귀 결론이 아니다. `test_sql` 내용은 수집기가 검증하지 않은 원본(GitHub job log, CI 산출물 서버의 JUnit과 `ctp_log.tgz`)에서 읽었다.

## 요약

| Suite | GitHub 상태 | 수집 상태 | 집계 | merge-base와 비교 | 판단 |
| --- | --- | --- | --- | --- | --- |
| `test_medium` | SUCCESS | validated | 975 계획, 975 통과 | - | 실패 없음 |
| `test_shell` | FAILURE | validated | 3,580 계획, 3,550 실행, 3,546 통과, 실패 3, 오류 1, skip 30 | 4건 모두 같은 testcase tree의 base run에서 같은 증상 | 이 PR 원인 아님 (`unlikely`, 높음) |
| `test_sql` | FAILURE | job_level_failure | 원본: shard 09 실패 2건, shard 03 취소(2,881건 중 2,178번째에서 서버 종료 뒤 남은 case 전부 연결 실패) | shard 09 2건은 base 공통. shard 03 서버 종료는 head에서만 관찰 | 09는 base 공통. 03은 원인 미확인, PR 관련성 `unlikely` (낮음~중간) |
| `test_sql_by_cci` | FAILURE | validated | 17,771 계획, 17,733 통과, 실패 38 | 38건 경로와 diff 파일이 base와 byte 단위로 같음 | 알려진 이슈. 이 PR 원인 아님 |

`github-actions: code-style` 실패(GNU indent, `src/storage/heap_file.h`)는 이 분석 범위 밖이다.

가장 먼저 할 일: `test_sql` shard 03을 다시 돌려 `cbrd_27732_merge.sql` 중 서버 종료(`LOG FATAL ERROR: log_fetch_from_archive`)가 다시 나는지 본다. 예: `/run rerun 42801815682`. `test_sql`은 머지 조건이고, 이 실패만 head에서만 관찰됐다. CI 실행은 사람의 승인 뒤 별도 workflow로 한다.

## 대상과 증거 범위

- head: `855f220d532e222f2a266a0883c94a40bed3a388`. 이전 PR head `4c3c8d791`과 base `50619ce53`의 merge이다. base 대비 PR 변경 source는 `src/storage/heap_file.c`, `heap_file.h`, `heap_oos.cpp`, `heap_oos.hpp`, `oos_file.cpp`, `src/transaction/locator_sr.c`의 6개 파일이다(나머지는 unit test와 `contrib/benchmarks`).
- merge-base: `50619ce53ef7b0e6bc8b468b2065ae7da4ef592f`. target tip과 같다. `collect-base` 관찰 시각 `2026-11-10T17:32:59Z`, baseline 판정 `partial_exact`.
- head 빌드: `11.5.0.2943-855f220` (debug는 optdebug). 모든 shard의 `build.sha`가 head와 같고 producing run은 42801815682이다.
- testcase revision:
  - public(`test_medium`, `test_sql`, `test_sql_by_cci`): `0c492316a32ed6ca7403b2fb2ba73dc7be17d500` (`tc/pr-8299`). tree `477ca9744`는 `feature/oos-merge`의 `b53a7984c`와 같다.
  - private(`test_shell`): `1a6d1616cabb1d3249a98a8a59e599523629ec48` (`tc/pr-8299`). tree `ab2f3bc67`는 `e56dfa32a`와 같다. 원격 `feature/oos-merge`의 현재 tip `8ef4f6278`(2026-11-10T12:52Z)은 포함하지 않는다. `tc/pr-8299`는 그보다 앞선 10:44Z에 갱신됐다.
- 수집기: `cubrid-ci 0.2.0 (8f24902a757a, release)`. `cubrid-tcc 0.3.0`.
- head 증거: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8299/855f220d532e222f2a266a0883c94a40bed3a388/`, observation `20261110T172330.562643487Z-3465866-0` (outcome `incomplete`).
- merge-base 증거: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/50619ce53ef7b0e6bc8b468b2065ae7da4ef592f/`, observation `20261110T173403.291735374Z-4158209-0`.

### 수집 ledger

| Suite | shard 상태 | 진단 |
| --- | --- | --- |
| `test_medium` | 00 retained | - |
| `test_shell` | 00~49 retained | - |
| `test_sql` | 00~02, 04~06, 08, 09 retained. 03, 07 failed | 03: `summary_info` 404 (job 취소). 07: `summary_info` 응답 decode 오류(226,225 byte 소비). Actions의 `shard sql 07` job은 success이다. |
| `test_sql_by_cci` | 00~09 retained | - |

binary budget은 512 MiB 중 0 byte를 썼다.

## 실패 목록

| Suite | Testcase | head 결과 | 증상 | base 분류 | PR 관련성 | 신뢰도 |
| --- | --- | --- | --- | --- | --- | --- |
| `test_shell` | `shell/_06_issues/_14_2h/bug_bts_15529/cases/bug_bts_15529.sh` | failure (shard 15) | `call_stack_dump_activation_list` 기본값의 OOS 오류 번호가 answer와 다름 | `also_observed_on_base` (run 42785110884, 같은 tree) | `unlikely` | 높음 |
| `test_shell` | `shell/_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh` | failure (shard 38) | 같음 | `also_observed_on_base` (같음) | `unlikely` | 높음 |
| `test_shell` | `shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh` | failure (shard 39) | 같음 | `also_observed_on_base` (같음) | `unlikely` | 높음 |
| `test_shell` | `shell/_06_issues/_26_2h/cbrd_27571/cases/cbrd_27571.sh` | error (shard 33) | 재시작 복구가 `log_append_compensate_internal` (`log_manager.c:3214`)에서 assertion | `also_observed_on_base` (run 42785110884와 42819814597) | `unlikely` | 높음 |
| `test_sql` (미검증 원본) | `sql/_33_elderberry/cbrd_24042/cbrd_24182/cases/r_outer_join.sql` | failure (shard 09) | unexpected result | 원본 비교상 base 공통 (수집기 기준 `uncomparable`) | `unlikely` | 높음 |
| `test_sql` (미검증 원본) | `sql/_36_guava/cbrd_27762/cases/cbrd_27762.sql` | failure (shard 09) | unexpected result | 원본 비교상 base 공통 (수집기 기준 `uncomparable`) | `unlikely` | 높음 |
| `test_sql` (미검증 원본) | `sql/_13_issues/_26_2h/cases/cbrd_27732_merge.sql`과 shard 03의 이후 case | NOK 뒤 shard 취소 | INSERT…SELECT 중 `LOG FATAL ERROR: log_fetch_from_archive`. 재시작 때 `basic_lgar000` 없음 | 원본 비교상 head에서만 (수집기 기준 `uncomparable`) | `unlikely` | 낮음~중간 |
| `test_sql_by_cci` | 38건 (merge-base 목록과 같음) | failure | develop 공통 CCI 출력 차이 | `also_observed_on_base` (38/38 diff 파일 byte 동일) | 알려진 이슈 | 높음 |

집계 대조:

- 수집기 검증 suite(`test_shell` 4, `test_sql_by_cci` 38)의 head 실패 42건은 모두 base에서도 관찰됐다. head에만 있는 것은 0건이다.
- `test_sql`은 수집기 기준으로 모두 `uncomparable`이다. 원본 기준으로는 shard 09의 2건이 base 공통이고, shard 03의 서버 종료 1건이 head에만 있다.
- base에만 있는 실패(`base_only`): 검증된 suite에서 0건이다. base 선택 shell run 42819814597의 실패는 `cbrd_27571.sh` 1건으로 head에도 있다.

## 원인 분석

### 1. shell answer 3건: TC branch가 OOS 오류 번호 재변경을 받지 못함

관찰:

- 세 case 모두 `call_stack_dump_activation_list` 기본값 출력만 다르다. head 엔진은 `-50,-1395,-1397,-1398`을 출력하고, 시험에 쓴 answer는 `-50,-1387,-1389,-1390`을 갖고 있다(head raw JUnit에서 두 패턴이 각 12번 나온다).
- `1a6d1616c`와 원격 `feature/oos-merge` tip `8ef4f6278`의 차이는 이 세 case의 answer 5개뿐이다: `bug_bts_9836/cases/log2.answer`, `log3.answer`, `bug_bts_14120/cases/bug_bts_14120_1.answer`, `bug_bts_15529/cases/test.answer`, `testdebug.answer`. `8ef4f6278`은 "[CBRD-26357] Renumber OOS diagnostic defaults after develop merge"이다.
- base run 42785110884(private TC `e56dfa32a`, head와 같은 tree)에서 세 case가 같은 증상으로 실패한다. 시각, `time=`, 주소, host를 지운 diff 파일은 head와 같다.
- `8ef4f6278`로 다시 돌린 base shell run 42819814597에서는 세 case가 통과한다.

추론: develop merge 때 OOS 오류 번호를 -1395..-1401로 옮겼는데, `tc/pr-8299`는 answer 수정 commit `8ef4f6278`이 `feature/oos-merge`에 올라오기 전에 갱신됐다. 엔진 결함이나 PR 변경 때문이 아니다.

반증 조건: private `tc/pr-8299`에 `8ef4f6278`을 merge한 뒤에도 세 case가 head에서 실패하면 이 판단은 틀리다.

다음 작업: private 저장소의 `tc/pr-8299`에 `origin/feature/oos-merge`(`8ef4f6278`)를 merge해 push한다. 이 TC 변경은 별도 승인 뒤 진행한다. 그 뒤 `test_shell`을 다시 돌린다.

### 2. shell `cbrd_27571.sh`: base 공통 복구 assertion

관찰: head와 base 모두 서버 재시작 복구가 `log_recovery_undo` → `log_rv_undo_record` → `log_append_compensate` → `log_append_compensate_internal` (`log_manager.c:3214`) `Assertion 'false'`로 멈춘다. 뒤따르는 NOK 4줄(`db27571_x003 still remains`, `checkdb failed`, `could not add db27571_x003 again`, core 발견)도 같다. base는 run 42785110884와 shell 재실행 run 42819814597 두 번 모두 실패한다. 이전 분석([cbrd-oos-sql-by-cci/report.md](../cbrd-oos-sql-by-cci/report.md))은 develop 대상 PR run(#8409, #8168)에서도 같은 assertion을 기록했다.

추론: develop에서 들어온 기존 결함이다. 이 PR은 log와 recovery 코드를 바꾸지 않는다.

반증 조건: 같은 testcase가 base 엔진에서 통과하고 head 엔진에서만 실패하는 비교가 나오면 다시 본다.

다음 작업: 이 PR 밖에서 develop 쪽 후속으로 다룬다. 다만 `test_shell`이 머지 조건이므로 이 case가 머지를 막는다는 점은 남는다.

### 3. sql shard 09 2건: base 공통 결과 차이

관찰(미검증 원본): head와 base shard 09의 JUnit은 모두 524건 중 실패 2건이다. 두 case의 실패 메시지는 GitHub testcase URL 안의 TC SHA(`0c492316a` 대 `b53a7984c`)만 다르다. 두 TC는 같은 tree이다. 산출물 서버의 `sql/collect/failed.list`도 두 run에서 같은 두 줄이다.

추론: base에서 이미 실패하는 결과 차이이다. 이전 분석은 같은 두 case가 develop 대상 PR #8168 run에서도 실패한다고 기록했다. 이 PR 원인이 아니다.

반증 조건: 수집기가 검증한 base `test_sql`에서 이 두 case가 통과하면 다시 본다.

### 4. sql shard 03: `cbrd_27732_merge.sql` 중 서버 종료와 2시간 정지

관찰(미검증 원본, job log `129784970284`과 shard 03 `ctp_log.tgz`):

- shard 03은 2,881건 중 2,177번째 `cbrd_27732.sql`까지 통과했다. 2,178번째 `cbrd_27732_merge.sql` 시작 1.5초 뒤인 15:09:31Z에 서버가 `LOG FATAL ERROR: log_fetch_from_archive`로 종료했다.
- 이 case의 `.result`를 보면 `drop`, `create`, insert 7개(2, 2048, 2048, 4096, 8192, 16384, 32768행)가 끝났다. 그 뒤 8번째 `insert into t_chain select id + 65536, ... from t_chain where v > 0`부터 모든 문장이 `Error:-677`이다. 서버는 이 INSERT…SELECT 중에 종료했다.
- 이후 재시작은 매번 `Unable to mount disk volume ".../basic_lgar000".... No such file or directory`와 같은 fatal로 실패했다. CTP가 case마다 약 3분씩 재시작을 시도해 2,212번째 case까지 진행했고, job은 17:00:03Z에 취소됐다.
- `java.io.IOException: No space left on device`가 15:11:10Z부터 2,772번 나온다. 첫 서버 종료(15:09:31Z) 전에는 공간 부족 메시지가 log에 없다.
- 서버 error log(`basic_20261111_0000.err`)는 산출물에 없다. 첫 종료의 직접 원인은 log에 없다.
- base run 42785110884의 shard 03(runner `cubrid-arc-586zc-runner-fsfq4`)과 같은 base의 PR #8348 run 42788743110 shard 03은 같은 분할에서 같은 case를 같은 순번(2,178/2,881)에 실행해 7초 만에 통과했다. head는 runner `cubrid-arc-586zc-runner-8rdzc`이다.
- PR diff(`50619ce53..855f220d5`)에는 log, archive, vacuum, recovery 코드가 없다. `locator_sr.c` 변경은 UPDATE 경로의 `heap_pending_record` 소유권이다. `heap_oos.cpp` 변경은 OOS 분리 기준 크기와 inline 참조 판정이다. 이 case의 행은 `int, int, varchar(200)`이고 pad는 SHA-256 hex 64자라 OOS 분리 기준보다 훨씬 작다.

추론:

- 실행 중 archive를 읽어야 하는 쪽은 vacuum이나 rollback이다. 그런데 archive 0이 없었다. archive를 만들지 못했거나 지워졌다는 뜻이다. 그 뒤 계속 나온 공간 부족은 runner 디스크가 이미 부족했을 가능성을 보여 준다. 하지만 첫 종료보다 앞선 공간 부족 기록은 없다. 이 가능성은 확인하지 않았다.
- PR 변경 중 이 경로와 이어지는 것을 찾지 못했다. 그래서 PR 관련성은 `unlikely`로 둔다. 한 번만 관찰했고, error log가 없으며, 재현하지 않았으므로 신뢰도는 낮음~중간이다. INSERT…SELECT가 PR이 바꾼 heap scan 경로를 지난다는 점은 남는 의심이다.
- 다른 shard의 결과에는 이 서버 종료의 영향이 없다. 각 shard는 따로 서버를 띄운다.

모르는 것: 첫 fatal의 직접 원인, 그 시점 runner의 디스크 여유, 재발 빈도, `cubrid-tcc`의 이 case 이력(index가 2026-10-27까지만 있어 `UNKNOWN`).

반증 조건:

- 같은 head로 shard 03을 다시 돌려 같은 case에서 다시 `log_fetch_from_archive`가 나고, base 엔진은 여러 번 통과하면 PR 관련성을 `plausible`로 올린다.
- 다시 돌려 통과하고 다른 runner나 다른 PR에서 같은 fatal이 보이면 infra 또는 기존 결함으로 본다.

다음 작업: `/run rerun 42801815682`로 `test_sql`을 다시 돌린다(승인 필요). 재발하면 `cubrid-test-sql-run`으로 `sql/_13_issues/_26_2h/cases/cbrd_27732_merge.sql`을 head와 base 엔진에서 반복 실행하고, 서버 error log와 `lgar` 생성·삭제 기록을 남긴다.

### 5. `test_sql_by_cci` 38건: 알려진 이슈

`cubrid-common`의 Known CI issues 목록에 있는 "`sql_by_cci` job fails on every branch" 항목(만료 2026-12-09)에 해당한다. head 38건의 경로 목록이 merge-base run 42785110884의 38건과 같다. 38건 모두 수집기가 뽑은 diff 파일이 byte 단위로 같다. 두 run의 testcase tree도 같다. 규칙에 따라 원인 분석은 하지 않는다.

## merge-base 비교

| 항목 | head | merge-base |
| --- | --- | --- |
| Engine | `855f220d5` | `50619ce53` (target `feature/oos-merge` tip과 같음) |
| medium, sql_by_cci run | 42801815682 / 1 | 42785110884 / 1 |
| shell run | 42801815682 / 1 | 수집기 선택: 42819814597 / 1 (shell만 다시 돌린 run). 보조: 42785110884 / 1 (`collect-commit --run-id`로 받음, shell summary `validated`) |
| sql run | 42801815682 / 1 (`job_level_failure`) | 42785110884 / 1 (`collection_failed`: shard 01 JUnit에서 PL/CSQL 6건 누락) |
| public TC | `0c492316a` (tree `477ca9744`) | `b53a7984c` (tree `477ca9744`) |
| private TC | `1a6d1616c` (tree `ab2f3bc67`) | 42819814597: `8ef4f6278`. 42785110884: `e56dfa32a` (tree `ab2f3bc67`) |

- 수집기가 선택한 base shell run 42819814597은 answer 5개가 다른 TC로 돌았다. 그래서 bug_bts 세 case는 그 run과 비교할 수 없다(`uncomparable`). 같은 tree인 run 42785110884와 비교해 `also_observed_on_base`로 분류했다.
- `test_sql`은 양쪽 모두 수집기 summary가 없다. 비교는 산출물 서버의 JUnit, `failed.list`, job log를 직접 읽어 했다.
- 같은 base 위의 다른 PR #8348 run 42788743110은 shard 09에서 `lock_unlock_all` assertion을 냈다([cbrd-27858/ci-analysis-2253759.md](../cbrd-27858/ci-analysis-2253759.md)). 이번 head의 shard 09에는 그 crash가 없다. shard 03의 fatal과도 증상이 다르다.

## testcase 이력

`cubrid-tcc 0.3.0`로 조회했다. index discovery가 2026-10-27T12:20Z까지만 있어 상태가 `STALE`이다.

| Testcase | Chronicle 상태 | flakiness |
| --- | --- | --- |
| `bug_bts_15529.sh`, `bug_bts_9836.sh`, `bug_bts_14120.sh` | `PASSING` (오류 번호를 바꾸기 전 기간) | `UNKNOWN` |
| `cbrd_27571.sh` | `NOT_INDEXED` | `UNKNOWN` |
| `cbrd_27732_merge.sql`, `r_outer_join.sql` | `UNKNOWN` | `UNKNOWN` |
| `cbrd_27762.sql` | `NOT_INDEXED` | `UNKNOWN` |
| `test_sql_by_cci` 38건 | Chronicle이 이 suite를 index하지 않음 | - |

index를 새로 받지 않았다. 이번 결론에 필요한 비교는 같은 base의 exact run에서 얻었다. 이력은 분류를 바꾸지 않는다.

## 우선순위

1. `test_sql`을 다시 돌려 shard 03의 `cbrd_27732_merge.sql` 서버 종료가 재발하는지 본다(`/run rerun 42801815682`, 승인 필요). head에서만 관찰된 유일한 실패이다.
2. private `tc/pr-8299`에 `feature/oos-merge`의 `8ef4f6278`을 merge해 shell answer 3건을 없앤다(TC push 승인 필요). 1번의 CI 재실행 전에 하면 한 번에 확인할 수 있다.
3. `cbrd_27571.sh` 복구 assertion과 sql shard 09의 2건은 base와 develop에도 있다. 이 PR의 원인은 아니지만 머지 조건을 막으므로 feature/develop 쪽 후속으로 추적한다.
4. `test_sql_by_cci` 38건은 알려진 이슈로 둔다.
5. 수집기 쪽: base `test_sql` shard 01 JUnit 누락(PL/CSQL 6건)과 head shard 07 응답 decode 오류는 수집기·CI 결과 기록 문제로 따로 다룬다.

## 증거 파일

- head 수집기 bundle: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8299/855f220d532e222f2a266a0883c94a40bed3a388/providers/github-actions/runs/42801815682/attempts/1/{test_medium,test_shell,test_sql_by_cci}/summary.json`
- base 수집기 bundle: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/50619ce53ef7b0e6bc8b468b2065ae7da4ef592f/providers/github-actions/runs/{42785110884,42819814597}/attempts/1/`
- 미검증 원본(CI 산출물 서버): `runs/42801815682/sql/shard/03/artifacts/ctp_log.tgz`, `runs/42801815682/sql/shard/09/test-results/linux_sql_64bit_optdebug.xml`, `runs/42801815682/sql/collect/failed.list`, `runs/42785110884/sql/shard/09/test-results/linux_sql_64bit_optdebug.xml`, `runs/42785110884/sql/collect/failed.list`
- 미검증 원본(GitHub job log): head `shard sql 03` job 129784970284, `shard sql 09` job 129784970246. base `shard sql 03` job 129728275262. PR #8348 `shard sql 03` job 129740512531.
