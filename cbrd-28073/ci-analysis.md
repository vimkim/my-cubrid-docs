# CI 분석: PR #8514, run 43263461440 (shell, sql)

## 요약

- 분석 범위는 `test_shell`과 `test_sql`이다. 사용자 요청에 따라 `test_sql_by_cci`는 뺐다. `test_medium`은 통과했다.
- shell 실패 6건과 sql 실패 1건은 모두 serial이나 OOS와 관계없는 테스트다.
- 7건 모두 같은 base(`feature/oos-merge` `c02f897268`)를 쓰는 PR #8434의 run 43284032595에서도 똑같이 실패했다. #8434는 serial 코드를 바꾸지 않는다.
- 원인은 testcase와 engine branch가 서로 맞지 않는 것으로 추정한다. 이 PR이 원인일 가능성은 낮다.
- 제약이 있다. `feature/oos-merge` base 커밋에는 CI 기록이 없어서 정식 merge-base 비교는 못 했다. `test_sql`은 collector 무결성 검사에 걸려 검증된 요약이 없다. 그래서 sql 결과는 원본 JUnit에서 직접 읽었다.

## 대상

| 항목 | 값 |
| --- | --- |
| PR | https://github.com/CUBRID/cubrid/pull/8514 |
| head | `31c72e8342cb05fc60860d7fcec2da60e2e0b9ab` |
| base | `feature/oos-merge` `c02f897268b03526c1b4dd0359220f924d58b810` (merge-base와 같음) |
| run | https://github.com/CUBRID/cubrid/actions/runs/43263461440 attempt 1 |
| 수집 | 2026-11-13T05:24:58Z, `cubrid-ci 0.2.0 (5141d5bf05ed)` |
| testcase revision (sql) | cubrid-testcases `4cb13426b7b9` |
| 비교 대상 | PR #8434 head `b049fa155c90`, run https://github.com/CUBRID/cubrid/actions/runs/43284032595 |

## Suite 상태

| Suite | CI 결과 | 수집 상태 | 개수 |
| --- | --- | --- | --- |
| test_medium | pass | validated | 실패 없음 |
| test_shell | fail | validated | 3592개 중 통과 3556, failure 5, error 1, skip 30 |
| test_sql | fail | collection_failed | shard 09에서 535개 중 1개 실패 (원본 `summary_info`와 JUnit) |

`test_sql` 수집 실패 원인은 collector가 남긴 진단이다. shard 01의 JUnit이 `summary_info`보다 17개 적다(통과 3548 대 3531). 빠진 17개는 모두 `sql/_05_plcsql/.../cbrd-27556`, `cbrd-27584`, `cbrd-27633` 아래의 통과한 케이스다. PR #8434의 run에서도 같은 진단이 나왔다. 실패 판정에는 영향이 없는 CI 결과 파일 문제로 본다.

## 실패 목록

| Suite | Testcase | 결과 | 현상 | #8434 | PR 관련성 | 확신 |
| --- | --- | --- | --- | --- | --- | --- |
| shell | `shell/_06_issues/_26_2h/cbrd_25862_cms/cases/cbrd_25862_cms.sh` | failure | CMS `dbmtuserlogin`이 권한 조회 SQL 오류를 반환 | 같음 | unlikely | 높음 |
| shell | `shell/_06_issues/_26_2h/cbrd_26850/cases/cbrd_26850.sh` | failure | CMS `loaddb` 오류 메시지가 기대와 다름 | 같음 | unlikely | 높음 |
| shell | `shell/_06_issues/_26_2h/cbrd_26861/cases/cbrd_26861.sh` | failure | CMS 비동기 `backupdb`의 task status와 uuid가 기대와 다름 | 같음 | unlikely | 높음 |
| shell | `shell/_06_issues/_26_2h/cbrd_26915/cases/cbrd_26915.sh` | failure | CMS `compactdb`의 class 목록 입력이 무시됨 | 같음 | unlikely | 높음 |
| shell | `shell/_06_issues/_26_2h/cbrd_26916/cases/cbrd_26916.sh` | error | CMS autoexecquery 검증이 없고 `aj_execquery_get_exec_time` (`src/cm_autojob.cpp:1204`)에서 core | 같음 | unlikely | 높음 |
| shell | `shell/_40_guava/cbrd_27236_merge/cases/cbrd_27236_merge.sh` | failure | 병렬 index build sort의 merge 단계 로그가 기대와 다름 | 같음 | unlikely | 중간 |
| sql | `sql/_33_elderberry/cbrd_24042/cbrd_24182/cases/r_outer_join.sql` | failure | outer join 질의 계획이 `inner join`이 아니라 `cross join`과 sargs로 나옴 | 같음 | unlikely | 높음 |

head 실패 7건 중 #8434에서도 나온 것은 7건, head에만 나온 것은 0건이다. #8434에만 나온 실패는 shell `shell/_06_issues/_11_2h/bug_bts_6279/cases/bug_bts_6279.sh` 하나다. sql 실패는 두 run이 똑같다.

## 원인 분석

### CMS testcase 5건

- 관찰. 5건 모두 cubrid-testcases-private-ex 커밋 `0dc80d4eb` "[CBRD-27601] re-add CMS testcases for CUBRID/cubrid#8403"으로 들어온 케이스다. CUBRID/cubrid#8403은 cubridmanager submodule을 올리는 develop PR이고, merge 커밋 `0afeab0196`는 base `c02f897268`에 없다(`git merge-base --is-ancestor`로 확인).
- 추론. testcase는 새 CMS 동작을 기대하지만 `feature/oos-merge` engine에는 그 CMS가 아직 없다.
- 반증 조건. #8403이 들어간 engine에서도 같은 5건이 실패하면 이 추론은 틀리다.
- 다음 행동. 이 PR에서는 할 일이 없다. `feature/oos-merge`가 develop을 받아들이면 풀릴 것으로 본다.

### `cbrd_27236_merge.sh`

- 관찰. 케이스는 `90f15f0c8`(2026-11-11)에서 추가됐다. engine 쪽 CBRD-27236 커밋 `4255a337dd`는 base에 있다. 실패 내용은 index build sort의 merge 로그 문구와 횟수다. serial 코드와 관계없다.
- 추론. testcase가 develop의 다른 후속 변경을 기대하는 것으로 보인다. 정확히 어떤 변경인지는 확인하지 못했다.
- 반증 조건. 같은 base의 다른 PR에서 이 케이스가 통과하면 다시 봐야 한다. 현재 #8434도 실패한다.
- 다음 행동. 이 PR에서는 할 일이 없다. 필요하면 CBRD-27236 담당자에게 확인한다.

### `r_outer_join.sql`

- 관찰. engine 쪽 CBRD-27762 (`b9825700a4`, #8409, 2026-11-12)은 base에 있다. testcase 쪽에서는 CBRD-27762 answer를 2026-11-10에 바꿨다가 2026-11-11에 되돌렸다(`e3e7bce0d`). run이 쓴 testcase `4cb13426b7b9`는 되돌린 뒤의 옛 answer를 가진다.
- 추론. engine은 새 계획을 내고 answer는 옛 계획을 기대한다.
- 반증 조건. CBRD-27762가 없는 engine에서도 같은 차이가 나면 이 추론은 틀리다.
- 다음 행동. 이 PR에서는 할 일이 없다. CBRD-27762 담당자가 answer를 다시 맞춰야 한다.

## Base 비교

- `cubrid-ci collect-base`는 exit 3, baseline `unavailable`이었다. target tip과 merge-base가 모두 `c02f897268`이고, 이 커밋에는 gha-ci 기록이 없다.
- 대신 같은 base를 쓰는 PR #8434의 run 43284032595와 비교했다. 이 run은 이 PR의 run보다 약 2시간 뒤에 시작했다. 두 PR의 변경 코드는 겹치지 않는다. 이것은 정식 merge-base 비교가 아니므로 보조 근거로만 쓴다.
- PR #8493 (run 43196616205, 2026-11-12T10:01Z)은 shell과 sql을 통과했다. 이 run은 위 testcase들이 PR testcase branch에 들어오기 전의 것으로 추정한다. 확인하지는 않았다.

## Testcase 이력

`cubrid-tcc status`는 7건 모두 `NOT_INDEXED`였다. 로컬 이력 인덱스는 2026-11-11에 마지막으로 동기화됐고, 이 케이스들은 그 뒤에 추가됐다. 이력으로는 판단하지 않았다.

## 다음 행동

1. 이 PR의 코드 수정은 필요 없다고 본다.
2. 7건은 이 PR과 별개의 기존 실패로 남는다. CI 요구 조건을 면제하지는 않는다. `feature/oos-merge`의 testcase 동기화 또는 develop 반영으로 다뤄야 한다.
3. `test_sql` 수집 무결성 문제(shard 01 JUnit 17개 누락)는 collector나 CI 결과 파일 쪽 후속 과제다.

## 근거 파일

- head 근거: `cubrid-ci` 데이터 디렉터리의 `pr-8514/31c72e8342cb05fc60860d7fcec2da60e2e0b9ab/`
- 비교 근거: 같은 디렉터리의 `pr-8434/b049fa155c900f43a7c2116c1076c8da498af35a/`
- sql 실패 원본: `test_sql/raw/shards/09/linux_sql_64bit_optdebug.xml`, `summary_info`
