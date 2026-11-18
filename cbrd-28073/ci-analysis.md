# CI 분석: PR #8514 (run 43263461440, run 44245545024)

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

## 재수집: 2026-11-18, 4개 suite (`test_sql_by_cci` 포함)

> **경고.** 이번 수집은 검증이 끝나지 않았다(`observation: incomplete`, `report_mode: warning`). `test_sql`과 `test_sql_by_cci`에 검증된 요약이 없다. 이 절은 회귀 여부나 원인에 대한 결론을 내리지 않는다. 위의 2026-11-13 원인 분석은 그때의 관찰로 남겨 두며, 이번 수집으로 새로 뒷받침되지는 않는다.

### 대상

| 항목 | 값 |
| --- | --- |
| PR | https://github.com/CUBRID/cubrid/pull/8514 (Draft) |
| head | `31c72e8342cb05fc60860d7fcec2da60e2e0b9ab` (2026-11-13과 같음) |
| run | https://github.com/CUBRID/cubrid/actions/runs/43263461440 attempt 1 (2026-11-13과 같음) |
| 요청 suite | `test_medium`, `test_shell`, `test_sql`, `test_sql_by_cci` |
| 수집 | 2026-11-18T04:44:23Z, `cubrid-ci 0.2.0 (961fc3e59494, release)`, collect exit 4, verify exit 3 |
| observation | `pr-8514/31c72e8342cb05fc60860d7fcec2da60e2e0b9ab/observations/20261118T044048.330838596Z-2539929-0` |
| verify 판정 | identity `established`, manifest `validated`, requested summaries `partial` |
| testcase revision | shell: cubrid-testcases-private-ex `c56abd2aaddb` (`tc/pr-8514`), sql_by_cci: cubrid-testcases `4cb13426b7b9` (`tc/pr-8514`) |

### Suite 상태

| Suite | CI 결과 | 수집 상태 | 검증된 개수 |
| --- | --- | --- | --- |
| test_medium | pass | completed, summary `validated` | 975개 모두 통과 |
| test_shell | fail | completed, summary `validated` | 3592개 중 통과 3556, failure 5, error 1, skip 30 |
| test_sql | fail | `collection_failed` | 없음 |
| test_sql_by_cci | fail | `job_level_failure` | 없음 |

검증된 shell 실패 6건은 2026-11-13 목록의 shell 6건과 testcase 경로가 같다(`cbrd_25862_cms`, `cbrd_26850`, `cbrd_26861`, `cbrd_26915`, `cbrd_26916`(error), `cbrd_27236_merge`).

### 수집 기록과 진단

- `test_sql`: shard 00–09 원본은 모두 `retained`다. collector가 무결성 오류를 냈다. shard 01 JUnit이 `summary_info`보다 17개 적다(통과 3548 대 3531). 빠진 17개는 `sql/_05_plcsql/_01_testspec/_05_bug_fix/` 아래 `cbrd-27556`, `cbrd-27584`, `cbrd-27633`, `cbrd-27634`, `cbrd-27742`의 케이스다. 2026-11-13 수집과 같은 진단이다.
- `test_sql_by_cci`: shard 00–08 원본은 `retained`, shard 09는 `failed`(stage `junit`, 소비 0 byte)다. 진단은 "shard 09 has no test_sql_by_cci JUnit XML"이다. 보관된 job 메타데이터에서 shard 09 job의 conclusion은 `cancelled`이고, shard 메타데이터의 `test_rc`는 비어 있다. shard 03, 04, 05, 06, 07 job은 `failure`다. shard 09 job 로그는 수집 중 120초 시간 초과로 받지 못했다.
- 보관된 `test_sql_by_cci/raw/collect/failed.list`에는 shard 03–07의 20개 경로가 있다. 이 목록은 검증된 요약이 아니므로 판정으로 쓰지 않았다. 경로 이름에 `serial`이나 `oos`는 없다.
- binary budget: 536870912 byte 중 0 byte 사용. binary 부족으로 빠진 근거는 없다.

### Base 비교

- `cubrid-ci collect-base`는 exit 3, baseline `unavailable`이었다. GitHub가 기록한 PR base는 여전히 `c02f897268`이고, 이 커밋에는 CI 기록이 없다(4개 suite 모두 `not_observed`, 후보 run 없음).
- 관찰. `feature/oos-merge`의 현재 tip은 `3e541fcf6723` "[CBRD-26357] Merge develop into OOS integration"(2026-11-17)이다. `c02f897268`보다 48커밋 앞선다. 위 원인 분석에서 언급한 engine 커밋 `0afeab0196`(#8403, CMS), `b9825700a4`(CBRD-27762), `4255a337dd`(CBRD-27236)은 모두 이 tip에 들어 있다(`git merge-base --is-ancestor`로 확인).
- 이 사실만으로는 실패가 풀린다고 판단할 수 없다. 새 base에서 CI를 돌려야 확인된다.

### Testcase 이력

검증된 head 근거가 완전하지 않아 이번에는 이력 조회와 `cubrid-tcr` 확인을 하지 않았다.

### 모르는 것

- `test_sql`과 `test_sql_by_cci`의 검증된 실패 목록과 각 실패의 내용.
- `test_sql_by_cci` shard 09가 취소된 이유.
- 이 PR의 변경(`src/query/serial.c`, `src/storage/heap_file.c`)이 sql_by_cci 실패와 관계가 있는지.

### 다음 행동

1. PR branch를 `feature/oos-merge` 현재 tip `3e541fcf6723`으로 rebase하고 CI를 한 번 다시 돌린다. 새 base에는 2026-11-13에 원인으로 추정한 develop 변경이 모두 들어 있다. rebase, push, CI 실행은 별도로 승인받아야 한다.
2. 새 run이 끝나면 4개 suite를 다시 수집한다. `test_sql_by_cci`가 다시 shard 취소나 JUnit 누락으로 끝나면 같은 run을 다시 돌려 검증된 요약을 얻는다.
3. `test_sql` shard 01 JUnit 17개 누락은 collector 또는 CI 결과 파일 쪽 후속 과제로 남긴다.

### 근거 파일 (2026-11-18)

- head observation: `cubrid-ci` 데이터 디렉터리의 `github-actions/CUBRID-cubrid/pr-8514/31c72e8342cb05fc60860d7fcec2da60e2e0b9ab/observations/20261118T044048.330838596Z-2539929-0/result.json`
- 검증된 요약: 같은 head 디렉터리의 `providers/github-actions/runs/43263461440/attempts/1/test_medium/summary.json`, `.../test_shell/summary.json`
- sql_by_cci 원본: `.../test_sql_by_cci/raw/github/jobs.json`, `.../test_sql_by_cci/raw/shards/09/build.read`, `.../test_sql_by_cci/raw/collect/failed.list`

## 리베이스 후 재실행: 2026-11-18, head `3960d1b215`, run 44245545024

> **경고.** 이번 수집도 검증이 끝나지 않았다(`observation: incomplete`, `report_mode: warning`). `test_sql`에 검증된 요약이 없고, merge base에 CI 기록이 없어 base 비교를 못 했다. 그래서 이 절은 회귀 여부나 원인을 결론으로 내리지 않는다. 아래의 "관찰"은 근거 파일에서 직접 확인한 사실이고, "추론"은 반증 조건과 함께 적은 가설이다.

### 요약

- PR branch를 `feature/oos-merge` `3e541fcf6723`으로 rebase하고 CI를 다시 돌렸다. 검증된 실패는 shell 1건(`cbrd_27780`)과 sql_by_cci 2건(`cbrd_28011`, `cbrd_26722_list`)이다. 이전 head의 shell 실패 6건(CMS 5건, `cbrd_27236_merge`)은 이번에는 나오지 않았다.
- sql_by_cci 2건은 둘 다 `show trace` 출력에 `(oos time: ?, fetch: ?, ioread: ?)`가 없어서 생긴 diff다. 기대 결과는 testcase 커밋 `5c357c764bd8`(TC PR #4148, CBRD-28011)이 넣었다. 이 기능의 engine PR #8491은 아직 열려 있다.
- shell `cbrd_27780`은 serial을 쓰지 않는 TDE 테스트다. 같은 base 위의 PR #8434도 같은 항목(3번, 5번)에서 두 번 실패했다.
- test_sql과 test_sql_by_cci의 shard 09 실패는 CBRD-28058(page 366 archive fatal로 server가 멈추는 현상)과 증상이 다르다. 이번 shard 09는 JUnit을 남기고 정상 종료했고, 실패는 `cbrd_26722_list`의 출력 diff 1건이다.

### 대상

| 항목 | 값 |
| --- | --- |
| PR | https://github.com/CUBRID/cubrid/pull/8514 (Draft) |
| head | `3960d1b215083378370c04574fa2ea74867ede0c` |
| base | `feature/oos-merge` `3e541fcf6723cd81867700659d695af8a5bc1439` (merge base와 같음) |
| run | https://github.com/CUBRID/cubrid/actions/runs/44245545024 attempt 1 (`/run all`, 2026-11-18T05:37:28Z) |
| 요청 suite | `test_medium`, `test_shell`, `test_sql`, `test_sql_by_cci` |
| 수집 | 2026-11-18T07:29:44Z, `cubrid-ci 0.2.0 (00205d576de0, release)`, collect exit 4, verify exit 3 |
| observation | `pr-8514/3960d1b215083378370c04574fa2ea74867ede0c/observations/20261118T072931.449540683Z-1920046-0` |
| verify 판정 | identity `established`, observation `incomplete`, manifest `validated`, requested summaries `partial` |
| testcase revision | shell: cubrid-testcases-private-ex `f57990437295` (`tc/pr-8514`), sql/sql_by_cci: cubrid-testcases `ab26d4f20a52` (`tc/pr-8514`) |
| engine 빌드 | 모든 shard의 `build.read`가 `sha=3960d1b215…`이다. shell/sql은 debug, sql_by_cci는 release |

`tc/pr-8514`는 rebase 직후 두 testcase 저장소에서 `feature/oos-merge`를 merge해 맞췄다(public `ab26d4f20`, private `f57990437`). 그 결과 TC PR #4148(2026-11-18T05:23:04Z 머지)의 변경이 이번 run에 들어갔다.

### Suite 상태

| Suite | CI 결과 | 수집 상태 | 검증된 개수 |
| --- | --- | --- | --- |
| test_medium | pass | completed, summary `validated` | 975개 모두 통과 |
| test_shell | fail | completed, summary `validated` | 3624개 중 통과 3593, failure 1, error 0, skip 30 |
| test_sql | fail | `collection_failed` | 없음 |
| test_sql_by_cci | fail | completed, summary `validated` | 17823개 중 통과 17821, failure 2, error 0 |

### 실패 목록

| Suite | Testcase | shard | 증상 | base 비교 | `cubrid-tcr` | PR 관련성 |
| --- | --- | --- | --- | --- | --- | --- |
| test_shell | `shell/_06_issues/_26_2h/cbrd_27780/cases/cbrd_27780.sh` | 19 | NOK 3: "vacuum did not deallocate the pages: heap 0 rows, 5 -> 4 pages; overflow 0 rows, 1 -> 1 pages", NOK 5: "s2_enc has 85 pages for 4096 buffers" | uncomparable | `no_match` | unlikely, 신뢰도 중간 |
| test_sql_by_cci | `sql/_13_issues/_26_2h/cases/cbrd_28011.sql` | 03 | `show trace`에 `(oos time: …)` 없음 | uncomparable | `no_match` | unlikely, 신뢰도 높음 |
| test_sql_by_cci | `sql/_36_guava/cbrd_26722/cases/cbrd_26722_list.sql` | 09 | `show trace`의 `t_wide` scan에 `(oos time: …)` 없음 | uncomparable | `no_match` | unlikely, 신뢰도 높음 |

- 개수: head 실패 3건, base에서도 관찰 0건, head에만 있음 0건, 비교 불가 3건, base에만 있음 0건.
- 검증되지 않은 참고: `test_sql/raw/collect/failed.list`에는 shard 03 `cbrd_28011.sql`과 shard 09 `cbrd_26722_list.sql` 두 줄만 있다. sql_by_cci와 같은 두 testcase다. 이 목록은 검증된 요약이 아니라서 판정에 쓰지 않았다.

### 원인 가설

#### TC가 engine보다 앞섬: `cbrd_28011`, `cbrd_26722_list`

- 관찰. 두 testcase의 기대 결과는 커밋 `5c357c764bd8` "[CBRD-28011] Draft: TC changes for PR CUBRID/cubrid#8491 (#4148)"에서 왔다. 이 커밋은 `cbrd_28011.sql`과 `cbrd_28011.answer`를 추가하고 `cbrd_26722_list.answer`의 `t_wide` scan 4줄에 `(oos time: ?, fetch: ?, ioread: ?)`를 붙였다. 실패 diff는 정확히 이 부분이다.
- 관찰. engine PR #8491 "[CBRD-28011] Show OOS reads separately in SQL trace"는 `feature/oos-merge`로 아직 머지되지 않았다(OPEN). `git log --grep=28011 origin/feature/oos-merge` 결과도 비어 있다. 그래서 이 run의 engine은 trace에 OOS 통계를 출력하지 않는다.
- 관찰. 이 PR의 변경은 `src/query/serial.c` 1곳과 `src/storage/heap_file.c`의 `keep_form` 경로다. trace 출력 코드는 건드리지 않는다.
- 추론. 두 실패는 testcase 기준선이 engine 기준선보다 먼저 나간 결과다. 이 PR이 원인이 아니다. `feature/oos-merge` 위에서 최신 TC로 맞춘 다른 PR도 #8491이 머지되기 전에는 같은 2건이 실패할 것이다.
- 반증 조건. #8491 없이 `feature/oos-merge` `3e541fcf6723`과 TC `5c357c764bd8`로 돌렸을 때 두 testcase가 통과하면 이 가설은 틀렸다.
- 다음 행동. #8491을 먼저 머지하거나, TC PR #4148이 TC `feature/oos-merge`에 먼저 들어간 것을 TC 담당자와 정리한다. 이 PR에서 고칠 것은 없다.

#### OOS 저장 형태와 맞지 않는 TDE testcase: `cbrd_27780`

- 관찰. 실패 항목은 3번(scenario 1, vacuum 뒤 heap과 overflow page가 줄지 않음)과 5번(scenario 2, `s2_enc`가 buffer 4096개보다 적은 85 page)이다. 나머지 12개 항목과 checkdb는 OK다.
- 관찰. testcase는 `--db-page-size=4K`로 DB를 만들고 `char(2000)`, `varchar(20000)` 행으로 heap과 overflow page 수를 센다(`cbrd_27780.sh` 185, 201–214행, revision `f57990437295`). testcase는 2026-11-17에 추가됐다(`ca8f7672c`, TC PR #4737). engine 수정 `6fa7524098`(#8402)은 `feature/oos-merge`와 이 head에 모두 들어 있다.
- 관찰. 같은 base `3e541fcf6723`을 포함하는 PR #8434 head `ca1c1176fc`도 run 44081723670과 44236902717에서 같은 3번, 5번 항목으로 실패했다. 5번 메시지는 "s2_enc has 85 pages for 4096 buffers"로 글자까지 같다. #8434는 serial 코드를 바꾸지 않는다.
- 관찰. testcase는 serial이나 AUTO_INCREMENT를 쓰지 않는다(`serial|auto_increment|next_value` 검색 결과 없음).
- 추론. OOS branch에서는 4K page에서 `char(2000)` 값과 `varchar(20000)` 값이 OOS로 나간다. 그래서 heap과 overflow page 수가 develop 기준의 기대와 다르다. 이 PR이 원인일 가능성은 낮다.
- 반증 조건. 이 PR 없이 `feature/oos-merge` `3e541fcf6723`에서 `cbrd_27780.sh`가 통과하면 이 가설은 틀렸다.
- 다음 행동. OOS branch용 testcase 기대값을 정리할지 TC 쪽 후속 과제로 넘긴다. 로컬 확인은 `cubrid-test-shell-run`으로 base와 head에서 각각 한 번 돌리면 된다.

### PR 변경 범위

- `heap_attrinfo_determine_disk_layout`과 `heap_attrinfo_transform_to_disk_internal`에 기본값이 꺼진 인자(`keep_form`)가 추가됐다. 인자가 꺼져 있으면 기존 분기와 같은 코드를 탄다(`else if` 체인과 OOS demotion 조건이 그대로다).
- `keep_form`을 켜는 호출자는 `heap_attrinfo_transform_to_disk_keep_form` 하나이고, 이를 부르는 곳은 `serial_update_serial_object`(`src/query/serial.c`) 하나다.
- 위 실패 3건은 모두 serial NEXT VALUE를 거치지 않는다.

### Base 비교

- `cubrid-ci collect-base`는 exit 3, baseline `unavailable`이었다. merge base `3e541fcf6723`에는 exact-commit status나 check run이 없다(4개 suite 모두 `not_observed`, 후보 run 0개). 그래서 모든 실패가 "비교 불가"다.
- 참고(정식 baseline 아님). PR #8434 head `ca1c1176fc`는 `3e541fcf6723`을 포함한다. 그 run 44081723670의 test_sql_by_cci는 17822개 모두 통과했다. 이 run의 testcase revision은 TC PR #4148 이전이다. shell은 위의 `cbrd_27780` 외에 4건이 더 실패했다.

### 수집 기록과 진단

- 원본 보관: test_medium shard 1개, test_shell 50개, test_sql 10개, test_sql_by_cci 10개 모두 `retained`다.
- `test_sql`: collector 무결성 오류다. shard 01 JUnit이 `summary_info`보다 19개 적다(통과 3551 대 3532). 빠진 19개는 `sql/_05_plcsql/_01_testspec/_05_bug_fix/` 아래 `cbrd-27500`, `cbrd-27556`, `cbrd-27584`, `cbrd-27633`, `cbrd-27634`, `cbrd-27742`, `cbrd-27927`의 케이스다.
- 관찰. 같은 "shard 01 JUnit omits N testcases" 진단이 로컬 `cubrid-ci` 데이터의 develop 커밋(`666bb10ae6`, `67220b7e23` 등)과 다른 PR(#8299, #8348, #8416, #8434, #8494, #8495, #8504, #8510, #8559, #8565)에서도 나온다. 이 PR과 관계없는 기존 현상이다.
- binary budget: 536870912 byte 중 0 byte 사용.

### Testcase 이력

head 근거가 완전하지 않아 정식 이력 분석(section 3b)은 하지 않았다. known-issue 확인(`cubrid-tcr check`)만 했다.

- 세 실패 모두 known-issue 규칙과 맞지 않았다(`no_match`, engine `3960d1b215`, engine repo `/home/vimkim/gh/cb/develop`).
- `cubrid-tcr`가 이력이 오래됐다고 알려서, 안내한 범위(`cubrid-tcc sync-data --since 2026-11-17 --until 2026-11-18 --suite shell|sql --revisit-limit 0`)를 한 번씩 돌렸다. 둘 다 500초 제한에 걸려 끝나지 못했다(exit 124). 다시 돌리지 않았다.
- `cbrd_27780.sh`, `cbrd_28011.sql`: 인덱스에 기록이 없다(`NOT_INDEXED`). 두 testcase 모두 2026-11-17 이후에 추가됐다. 기록이 없다고 실패한 적이 없다는 뜻은 아니다.
- `cbrd_26722_list.sql`: 인덱스에 실패 1건, 통과 45건이 있다. 실패는 2026-10-27 PR #8243(develop), run 40432417387 shard 09, engine `a63c875b2c`, 서명 미상이다. 그때는 TC 커밋 `5c357c764bd8` 이전이라 이번 증상과 같은 원인이라고 볼 근거가 없다.
- 이력은 위 가설을 바꾸지 않는다. base 비교를 대신하지도 않는다.

### 모르는 것

- `test_sql`의 검증된 실패 목록. 검증되지 않은 `failed.list`는 sql_by_cci와 같은 2건만 가리킨다.
- `cbrd_27780`이 `feature/oos-merge` base 자체에서도 실패하는지. 지금은 다른 PR의 결과로만 추정한다.

### 다음 행동

1. `cbrd_28011`과 `cbrd_26722_list`: engine PR #8491 머지 순서를 TC PR #4148과 맞춘다. #8491이 머지되면 이 PR을 다시 rebase하거나, 그 전까지는 두 실패를 기존 문제로 기록한다.
2. `cbrd_27780`: base와 head에서 로컬로 한 번씩 돌려 위 가설을 확인한다. OOS branch용 기대값 수정은 TC 쪽 후속 과제로 넘긴다.
3. `test_sql` shard 01 JUnit 누락은 collector 또는 CI 결과 파일 쪽 후속 과제로 남긴다. 이 문제 때문에 test_sql은 계속 `collection_failed`로 나온다.
4. 이 PR은 serial 관련 회귀를 보이지 않는다. 다만 위 세 suite가 실패로 남아 있어 merge 조건은 아직 채우지 못한다.

### 근거 파일 (2026-11-18, head `3960d1b215`)

- head observation: `cubrid-ci` 데이터 디렉터리의 `github-actions/CUBRID-cubrid/pr-8514/3960d1b215083378370c04574fa2ea74867ede0c/observations/20261118T072931.449540683Z-1920046-0/result.json`
- 검증된 요약: 같은 head 디렉터리의 `providers/github-actions/runs/44245545024/attempts/1/test_medium/summary.json`, `.../test_shell/summary.json`, `.../test_sql_by_cci/summary.json`
- 실패 내용: `.../test_shell/failures/shell_06_issues_26_2h_cbrd_27780_cases_cbrd_27780_sh-9b5694291f/`, `.../test_sql_by_cci/failures/sql_13_issues_26_2h_cases_cbrd_28011_sql-c80a37695c/`, `.../test_sql_by_cci/failures/sql_36_guava_cbrd_26722_cases_cbrd_26722_list_sql-827acbff8f/`
- test_sql 원본: `.../test_sql/raw/collect/failed.list`, `.../test_sql/raw/shards/01/summary_info`
- baseline 시도: `github-actions/CUBRID-cubrid/commits/3e541fcf6723cd81867700659d695af8a5bc1439/`
- 참고 비교: `github-actions/CUBRID-cubrid/pr-8434/ca1c1176fca69825fc870b0e9d81d80cb5e59d77/providers/github-actions/runs/44081723670/`, `.../runs/44236902717/`
