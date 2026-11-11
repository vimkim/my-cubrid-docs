# PR 8348 CI 분석: head 2253759 (feature/oos-merge 최신 merge 후)

PR 브랜치에 `feature/oos-merge` 최신을 merge하고 TC 브랜치를 맞춘 뒤 돌린 CI의 실패가 이 PR 때문인지 판단한다. 분석일은 2026-11-11, Asia/Seoul이다. 앞 snapshot은 [ci-analysis-00b421e.md](ci-analysis-00b421e.md)에 있다.

**수집기 판정은 경고(warning)이다.** `test_sql`의 수집이 head와 merge-base 모두에서 무결성 검사로 실패했다. 그래서 `test_sql` 내용은 수집기가 검증하지 않은 원본(CI 산출물 서버의 JUnit과 CTP 결과)에서 읽었다. 아래 결론은 그 한계 안에서만 유효하다.

## 요약

| Suite | GitHub 상태 | 수집 상태 | 집계 | merge-base와 비교 | 판단 |
| --- | --- | --- | --- | --- | --- |
| `test_medium` | SUCCESS | validated | 975 계획, 975 통과 | - | 실패 없음 |
| `test_shell` | FAILURE | validated | 3,580 계획, 3,550 실행, 3,546 통과, 실패 3, 오류 1, skip 30 | 4건 모두 base에도 있음 | 이 PR 원인 아님 (높음) |
| `test_sql` | FAILURE | collection_failed | 원본 JUnit: shard 09에서 12건 | base 공통 2건, head만 10건 | head만의 10건은 서버 crash 1번과 그 여파. PR 관련성 `unlikely` (중간) |
| `test_sql_by_cci` | FAILURE | validated | 17,771 계획, 17,733 통과, 실패 38 | 38건 목록이 base와 같음 | 알려진 이슈. 이 PR 원인 아님 |

**재실행(run 42850100191) 결과:** crash는 재발하지 않았고, head에만 있는 실패는 없다. 남은 실패는 모두 merge-base 공통이다. 자세한 내용은 [재실행 결과](#재실행-결과-run-42850100191)에 있다.

## 대상과 증거 범위

- head: `225375922881fb0f61cc311458078264961eef79`. `feature/oos-merge` `50619ce53ef7b0e6bc8b468b2065ae7da4ef592f`와 파일 차이는 `src/query/vacuum.c` 하나뿐이다.
- merge-base: `50619ce53ef7b0e6bc8b468b2065ae7da4ef592f`(target tip과 같음, 관찰 `2026-11-10T15:37:40Z`).
- head 실행: [42788743110, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/42788743110). 빌드 버전 `11.5.0.2924-2253759`.
- merge-base 실행: [42785110884, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/42785110884)(PR 7990 실행). baseline 판정 `partial_exact`. 수집기는 base `test_shell`을 `running`으로 보고했지만 GitHub의 실행은 `completed / failure`이다. base shell 실패 목록은 산출물 서버의 JUnit에서 읽었다(미검증 원본).
- 수집기: `cubrid-ci 0.2.0 (8f24902a757a, release)`. head observation은 `incomplete`, `report_mode.py`는 `warning`.
- testcase revision: shell `99c246a49fb573a09b0efdcd7bc882c2901c6028`, medium·sql_by_cci는 `8ee04a454f7c75d3293353158907f3e267ed0f54`(모두 `tc/pr-8348`, feature 최신과 같은 tree). sql은 수집 실패로 revision을 검증하지 못했다.

## test_sql 수집 오류

수집기 진단: `shard 01 JUnit omits 6 testcases that summary_info reports (summary_info 3537/0/0, JUnit 3531/0/0)`. 빠진 6건은 `sql/_05_plcsql/_01_testspec/_05_bug_fix/` 아래 cbrd-27556, cbrd-27584, cbrd-27742 케이스이다. shard 01 자체는 실패가 0건이다. 앞 두 snapshot과 merge-base에서도 같은 종류의 오류가 났다. CI 결과 기록 쪽 문제이고, 이 PR과 무관하다.

## 실패 목록

### test_shell (4건, 모두 base 공통)

| Testcase | head shard | base shard | 증상 |
| --- | --- | --- | --- |
| `shell/_06_issues/_26_2h/cbrd_27571/cases/cbrd_27571.sh` | 19 (error) | 47 (error) | 볼륨 추가 중 서버를 죽인 뒤 재시작 복구가 `log_append_compensate_internal`(`log_manager.c:3214`, `RVDK_LINK_PERM_VOLEXT`)에서 assertion으로 종료 |
| `shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh` | 23 | 14 | 파라미터 출력의 `call_stack_dump_activation_list` 값이 answer와 다름 |
| `shell/_06_issues/_14_2h/bug_bts_15529/cases/bug_bts_15529.sh` | 32 | 08 | 같은 `call_stack_dump_activation_list` 차이 |
| `shell/_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh` | 49 | 40 | 같은 `call_stack_dump_activation_list` 차이 |

- 관찰: 4건 모두 merge-base 실행에서 같은 증상으로 실패했다. cbrd_27571은 base에서도 같은 함수, 같은 줄, 같은 recovery index로 core가 났다.
- 추론: feature/oos-merge에 develop을 merge하면서 생긴 문제이다. `call_stack_dump_activation_list` 차이는 기본값이나 오류 번호가 바뀐 데 answer가 따라가지 않은 것으로 보인다(11/09 feature 커밋 "Renumber OOS record-size errors after develop merge"와 시기가 맞지만 확인하지 않았다). 이 PR과 관련이 없다(`unlikely`, 높음).
- 다음 작업: 이 PR이 아니라 feature/oos-merge 쪽 후속으로 다룬다.

### test_sql (shard 09, 12건, 미검증 원본)

| Testcase | 결과 | base | 증상 |
| --- | --- | --- | --- |
| `sql/_33_elderberry/cbrd_24042/cbrd_24182/cases/r_outer_join.sql` | failure | 공통 | unexpected result |
| `sql/_36_guava/cbrd_27762/cases/cbrd_27762.sql` | failure | 공통 | unexpected result |
| `sql/_36_guava/cbrd_27515/cases/2_01_result_node_work.sql` | error | head만 | core file found: `cub_server`가 commit 중 `lock_unlock_all`에서 assertion으로 종료 |
| `sql/_36_guava/cbrd_27515/cases/` `2_02`, `3_02`, `3_03`, `3_04`, `4_01` (5건) | failure | head만 | crash 직후 실행. 결과가 `Error:-581`(`ER_DB_NO_MODIFICATIONS`), `-494` |
| `sql/_36_guava/cbrd_27516/cases/` `01`~`04` (4건) | failure | head만 | crash 직후 실행. 결과가 `Error:-581` |

#### crash 1번과 그 여파

- 관찰:
  - CTP 결과(`ctp_log.tgz`)의 `2_01_result_node_work.err`에 core 분석이 있다. 스택은 `sqmgr_execute_query` → `xtran_server_commit` → `log_commit_local` → `lock_unlock_all`(`lock_manager.c:10942`) → `__assert_fail`이다. `lock_manager.c` 10942행은 head 소스에서 `lock_free_entry`의 `lk_entry_pool_count` 범위 assertion 바로 앞이다. inline된 `lock_free_entry`의 assertion으로 보이지만, 빌드 산출물로 확인하지는 않았다.
  - 결과 파일 시각: `2_01` 22:13:19, 나머지 9건은 22:13:24~26에 끝났다. 9건은 모두 crash 뒤 서버가 다시 뜨는 동안 실행됐다.
  - merge-base 실행은 같은 testcase(같은 tree)를 모두 통과했다. `cubrid-tcc`에는 이 케이스들의 이력이 아직 없다(`NOT_INDEXED`).
- 추론: 실패 10건의 원인은 lock manager assertion 1번이다. 이 PR은 vacuum이 forward 페이지를 bestspace에 공개하는 시점만 바꾼다. 트랜잭션의 lock entry pool과 이어지는 경로는 찾지 못했다. 그래서 PR 관련성은 `unlikely`로 본다. 신뢰도는 중간이다. 한 번만 관찰했고, 재현하지 않았다.
- 모르는 것: assertion의 정확한 조건, 재발 빈도.
- 반증 조건: 같은 head로 다시 돌려 또 crash가 나고, 같은 testcase를 merge-base 엔진으로 돌리면 통과하면 이 판단을 다시 본다.
- 다음 작업: `/run rerun 42788743110`으로 다시 돌린다. 재발하면 `cubrid-test-sql-run`으로 `sql/_36_guava/cbrd_27515`를 로컬에서 반복 실행한다.

### test_sql_by_cci (38건, base 목록과 같음)

`cubrid-common`의 Known CI issues 목록에 있는 "`sql_by_cci` job fails on every branch" 항목(2026-12-09까지 유효)에 해당한다. merge-base 실행의 실패 38건과 testcase 경로 목록이 한 건도 다르지 않다. 규칙에 따라 원인 분석은 하지 않는다.

## 이전 snapshot과 비교

- 앞 실행(head `00b421e`)의 shell `bug_bts_5492` 실패는 이번에 나오지 않았다. 일시적인 실패로 본다.
- sql_by_cci는 57건에서 38건으로 줄었다. TC를 feature 최신으로 맞추면서 `answer_cci`가 갱신된 영향으로 보인다(확인하지 않음).

## 재실행 결과 (run 42850100191)

`/run rerun 42788743110`으로 2026-11-10T15:59:17Z에 같은 head(`2253759`)로 다시 돌렸다. 지난 실행의 실패 케이스와 TC 변경으로 영향받는 케이스만 다시 실행했다. private `tc/pr-8348`은 `06abbce75`(answer 번호 수정 커밋 `8ef4f6278` 포함)였다. 결과는 CI 산출물 서버의 JUnit 원본으로 읽었고, 수집기로 검증하지는 않았다.

| Suite | 실행 | 실패 | 판단 |
|---|---|---|---|
| test_medium | 975건 유지 | 0 | PASS |
| test_shell | 4건 | 1건 `cbrd_27571` | base 공통. CBRD-27571(Develop) |
| test_sql | 402건 | 2건 `r_outer_join`, `cbrd_27762` | 둘 다 base 공통 |
| test_sql_by_cci | 8167건 | 38건 | base 목록과 같음. Known CI issue |

- answer를 고친 shell 3건(`bug_bts_9836`, `bug_bts_14120`, `bug_bts_15529`)은 통과했다.
- `cbrd_27515` 12건은 모두 통과했고 `lock_unlock_all` assertion crash는 재발하지 않았다. 일시적 실패로 보고 로컬 재현은 하지 않는다. 다시 나오면 이 판단을 다시 본다.
- 결론: head에만 있는 실패는 없다. `test_shell`, `test_sql`이 빨간 것은 merge-base에서도 나는 기존 실패 때문이다.

## 우선순위

1. ~~`/run rerun 42788743110`~~ 완료(run 42850100191). crash 재발 없음.
2. shell `cbrd_27571`은 feature/oos-merge에도 있다(CBRD-27571). answer 3건은 `8ef4f6278`로 해결됐다. 이 PR을 막는 원인이 아니지만 `test_shell`이 머지 조건이라 feature 쪽 수정이 필요하다.
3. `test_sql` 수집 오류(shard 01 JUnit 누락)는 수집기 쪽 문제로 따로 다룬다.

## 증거 파일

- head 증거: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8348/225375922881fb0f61cc311458078264961eef79/`
- merge-base 증거: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/50619ce53ef7b0e6bc8b468b2065ae7da4ef592f/`
- 미검증 원본(CI 산출물 서버): `runs/42788743110/sql/shard/09/test-results/linux_sql_64bit_optdebug.xml`, `runs/42788743110/sql/shard/09/artifacts/ctp_log.tgz`, `runs/42785110884/sql/shard/09/test-results/linux_sql_64bit_optdebug.xml`, `runs/42785110884/shell/shard/{08,14,40,47}/test-results/linux_shell_64bit_optdebug.xml`
