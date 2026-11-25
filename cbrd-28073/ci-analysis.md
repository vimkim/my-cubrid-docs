# CI 분석: PR #8514 (run 43263461440, run 44245545024, run 44522105929, run 44705649588, run 45132951323, run 45385469421)

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

## 리뷰 수정 후 재실행: 2026-11-19, head `8e9d71fda0`, run 44522105929

> **경고.** 이번 수집도 전체 검증이 끝나지 않았다(`observation: incomplete`, `report_mode: warning`). `test_sql`이 이전과 같은 collector 무결성 오류로 검증된 요약을 갖지 못했다. 그래서 이 절은 회귀나 원인을 결론으로 내리지 않는다. shell, medium, sql_by_cci의 요약은 검증됐고, merge base의 검증된 요약과 비교했다.

### 요약

- 검증된 실패는 shell 2건이다. `bug_bts_8907.sh`(shard 05)와 `cbrd_27780.sh`(shard 06)다. medium(975개)과 sql_by_cci(17836개)는 모두 통과했다. test_sql은 CI 결과가 SUCCESS지만 collector가 검증하지 못했다.
- merge base `8c478d8559`(PR #7990 head)의 run 44511473106에서는 두 testcase가 통과했다. 두 testcase 파일은 head와 base의 testcase revision 사이에서 바뀌지 않았다. 그래서 두 건 모두 "head에만 있음"이다. 다만 head와 base 모두 한 번씩만 실행됐다.
- `bug_bts_8907`은 server를 재시작하는 동안 CCI 재연결을 보는 타이밍 테스트다. develop PR 3건을 포함해 2026-11-16~17에 5번 실패한 기록이 있다. serial을 쓰지 않는다. 이 PR과 관련될 가능성은 낮다(신뢰도 중간).
- `cbrd_27780`은 TDE 테스트다. 2026-11-18의 TC 수정(`ecbd54bbd`, `s1_heap`을 `STORAGE FORCE_INLINE`으로 바꿈) 뒤로 실패 항목이 바뀌었다. 이번에는 2번과 4번에서 암호화 테이블 `s1_heap`의 marker `S1HEAP`가 data volume에서 평문으로 1번 발견됐다. 이 PR과 관련될 가능성은 낮지만 head에서만 관찰됐으므로 확인이 필요하다(신뢰도 낮음).

### 대상

| 항목 | 값 |
| --- | --- |
| PR | https://github.com/CUBRID/cubrid/pull/8514 |
| head | `8e9d71fda07687ca5c5c28af92d869658a527dec` |
| base | `feature/oos-merge` `8c478d8559905330bc1a60a05dbebb273b07a16c` (merge base와 같음) |
| run | https://github.com/CUBRID/cubrid/actions/runs/44522105929 attempt 1 (`/run all`) |
| 요청 suite | `test_medium`, `test_shell`, `test_sql`, `test_sql_by_cci` (head에 `gha-ci: test_sql_by_cci` status가 있음) |
| 수집 | 2026-11-19T16:15:24Z, `cubrid-ci 0.2.0 (00205d576de0, release)`, collect exit 4, verify exit 3 |
| head observation | `pr-8514/8e9d71fda07687ca5c5c28af92d869658a527dec/observations/20261119T161517.228527912Z-2121289-0` |
| verify 판정 | identity `established`, observation `incomplete`, manifest `validated`, requested summaries `partial` |
| testcase revision | shell: cubrid-testcases-private-ex `b4fac751338a` (`tc/pr-8514`), sql_by_cci: cubrid-testcases `1a02bb474db8` (`tc/pr-8514`) |
| engine 빌드 | shell shard 05, 06의 `build.read`가 `sha=8e9d71fda0`, debug |

### Suite 상태

| Suite | CI 결과 | 수집 상태 | head (tests/pass/fail/error/skip) | base run 44511473106 |
| --- | --- | --- | --- | --- |
| test_medium | pass | completed, `validated` | 975/975/0/0/0 | 975/975/0/0/0 |
| test_shell | fail | completed, `validated` | 3652/3620/2/0/30 | 3652/3622/0/0/30 |
| test_sql | pass | `collection_failed` | 없음 | `collection_failed` |
| test_sql_by_cci | pass | completed, `validated` | 17836/17836/0/0/0 | 17836/17836/0/0/0 |

### 실패 목록

| Suite | Testcase | shard | 증상 | base 비교 | `cubrid-tcr` | PR 관련성 |
| --- | --- | --- | --- | --- | --- | --- |
| test_shell | `shell/_06_issues/_12_2h/bug_bts_8907/cases/bug_bts_8907.sh` | 05 | NOK 2: server 재시작 뒤 `cci_execute fail: -224`, 이어서 `cci_prepare fail: -224`가 반복되고 다시 연결되지 않음 | additional_on_head | `no_match` | unlikely, 신뢰도 중간 |
| test_shell | `shell/_06_issues/_26_2h/cbrd_27780/cases/cbrd_27780.sh` | 06 | NOK 2, NOK 4: "found in plaintext in the data volumes: S1HEAP=1" | additional_on_head | `no_match` | unlikely, 신뢰도 낮음 |

- 개수: head 실패 2건, base에서도 관찰 0건, head에만 있음 2건, 비교 불가 0건, base에만 있음 0건. test_sql은 양쪽 모두 검증된 요약이 없어 비교하지 않았다.

### 원인 가설

#### 재시작 타이밍 테스트: `bug_bts_8907`

- 관찰. testcase는 CCI 프로그램이 1초마다 `insert into t1 values(1)`을 실행하는 동안 server를 내렸다가 다시 올린다. 그런 다음 `-677` 오류 뒤에 다시 `prepared`가 나오는지 본다(`bug_bts_8907.sh` 35–51행, revision `b4fac751338a`). 이번에는 `-224` 오류가 났고 다시 연결되지 않았다.
- 관찰. testcase는 serial, AUTO_INCREMENT, OOS 열을 쓰지 않는다. 테이블은 `t1 (code int)` 하나다.
- 관찰. Chronicle 기록으로 이 testcase는 통과 480번, 실패 5번이다. 실패는 2026-11-16~17에 있었고, base가 develop인 PR #8561, #8513, #8489와 `feature/oos-merge` PR #8416, PR이 없는 run 1건이다. engine revision이 서로 다르다. 보관된 이전 실패에는 NOK 내용이 없어서 증상이 같은지는 확인하지 못했다.
- 추론. 다른 branch에서도 실패한 server 재시작 타이밍 문제다. 이 PR이 원인이 아니다.
- 반증 조건. head에서 이 testcase를 여러 번 실행해 계속 실패하고, base에서는 계속 통과하면 이 가설은 틀렸다.
- 다음 행동. shard 05를 다시 실행한다. 다시 실패하면 로컬에서 head와 base로 각각 반복 실행한다.

#### 암호화 테이블 marker의 평문 1건: `cbrd_27780`

- 관찰. 실패 항목은 2번("scenario 1: rows written")과 4번("scenario 1: pages deallocated")이다. 두 항목 모두 `S1HEAP=1`이다. 나머지 12개 항목과 checkdb는 OK다. `S1IDX`와 `S1OVF`는 발견되지 않았다.
- 관찰. 행은 `lpad('S1HEAP' || rownum, 2000, 'S1HEAP')`이다. 그래서 평문 heap page 1개에는 marker가 수백 번 나온다. 이번에 나온 1번은 page 전체가 아닌 작은 조각으로 보인다. 조각이 어디에 있는지는 확인하지 못했다(`count_plain`은 개수만 센다).
- 관찰. `s1_heap`을 `char(2000) storage force_inline`으로 바꾼 TC 커밋 `ecbd54bbd`(2026-11-18)는 head testcase revision `b4fac751338a`와 base testcase revision `509b01669b3f`에 모두 들어 있다. 두 revision 사이에서 testcase 디렉터리는 같다. base(`8c478d8559`)는 이 testcase를 통과했다. 이전 head(`3960d1b215`, run 44245545024)의 실패 항목(3번, 5번)은 이 TC 수정 전의 것이고 증상도 다르다.
- 관찰. 이 PR이 바꾸는 engine 코드는 `serial.c`의 두 호출과 `heap_file.c`의 `keep_form` 경로다. `keep_form`은 기본값이 꺼져 있고, 켜는 호출자는 serial 경로뿐이다. testcase는 serial을 쓰지 않는다.
- 추론. 평문 조각 1개는 page flush나 재사용 시점에 따라 달라지는 잔여 데이터일 가능성이 있다. 이 PR이 원인일 가능성은 낮다. 그러나 head 1번 실패, base 1번 통과뿐이어서 우연인지 결정적인지 구분하지 못한다.
- 반증 조건. 로컬에서 같은 testcase를 head로 여러 번 실행해 매번 `S1HEAP=1`이 나오고 base에서는 나오지 않으면, 이 PR의 변경이 관련된 것이다.
- 다음 행동. shard 06을 다시 실행한다. 로컬에서는 `cubrid-test-shell-run`으로 head와 base에서 각각 여러 번 실행한다. 다시 나오면 marker가 들어 있는 volume offset과 page 종류를 찾는다.

### Base 비교

- 첫 `cubrid-ci collect-base`는 GitHub API 오류(run 44511473106 jobs 조회, HTTP 502)로 exit 5였다. 일시적 원격 오류라서 한 번 다시 실행했다. 두 번째 결과는 exit 4, baseline `partial_exact`다.
- baseline: target `feature/oos-merge` `8c478d8559`, merge base `8c478d8559`, PR #7990 run 44511473106 attempt 1, observation `commits/8c478d8559905330bc1a60a05dbebb273b07a16c/observations/20261119T161838.201167644Z-2439113-0`.
- medium, shell, sql_by_cci는 base 요약이 검증됐다. test_sql은 head와 같은 무결성 오류로 `collection_failed`다.
- testcase revision: shell head `b4fac751338a`, base `509b01669b3f`. 두 실패 testcase의 디렉터리는 두 revision 사이에서 차이가 없다(`git diff --stat` 결과 없음). sql_by_cci head `1a02bb474db8`, base `5720a6a24b1a`.
- 두 run은 engine만 다르다(PR 커밋 5개). 각 testcase를 한 번씩 실행한 결과라서, base 통과가 head 실패의 원인을 정하지는 않는다.

### 수집 기록과 진단

- `test_sql`: 이전 run과 같은 collector 무결성 오류다. shard 01 JUnit이 `summary_info`보다 19개 적다(3557 대 3538). 빠진 testcase는 `sql/_05_plcsql/_01_testspec/_05_bug_fix/` 아래 케이스다. base run에서도 같다. 이 PR과 관계없는 기존 현상이다.
- binary budget: 536870912 byte 중 0 byte 사용.

### Testcase 이력

- `cubrid-tcc 0.3.0`. 이번 run(44522105929)과 PR #8632 run 44506831955의 shell을 `--revisit-limit 0`으로 sync했다.
- `bug_bts_8907.sh`: `SEEN_BEFORE`. 실패 occurrence는 38602(run 43831255516, PR #8416, engine `fba87586b8`), 37132(run 43897556424, engine `4b73a5f832`), 36243(run 43999554179, PR #8561, engine `2d42421a8f`), 35649(run 44013281521, PR #8513, engine `185118dde4`), 35530(run 44017820660, PR #8489, engine `3fe5c5c662`)이다. testcase revision과 engine revision이 모두 달라서 flaky라고 단정할 조건(같은 revision에서 통과와 실패)은 채우지 못한다.
- `cbrd_27780.sh`: `UNKNOWN_HISTORY` (`never_observed`, shell 마지막 sync 2026-11-18T11:28:20Z). shell 근거에는 실패만 남으므로 통과 기록이 없는 것은 안정성에 대해 아무것도 말하지 않는다.
- `cubrid-tcr check`: 두 건 모두 `no_match`다.

### 모르는 것

- `cbrd_27780`의 `S1HEAP` 조각이 들어 있는 volume, page 종류, 반복 여부.
- `bug_bts_8907`의 이전 실패가 같은 `-224` 증상이었는지.
- test_sql의 검증된 실패 목록. CI 결과는 SUCCESS다.

### 다음 행동

1. 실패한 shell shard 05, 06만 다시 실행한다(`cubrid-ci-trigger`, 실패 shard만).
2. `cbrd_27780`이 다시 실패하면 로컬에서 head와 base로 반복 실행하고 marker 위치를 찾는다. 결과에 따라 engine 이슈 또는 TC 수정으로 나눈다.
3. test_sql shard 01 JUnit 누락은 이전과 같이 collector 또는 CI 결과 파일 쪽 후속 과제다.

### 근거 파일 (2026-11-19, head `8e9d71fda0`)

- head observation: `cubrid-ci` 데이터 디렉터리의 `github-actions/CUBRID-cubrid/pr-8514/8e9d71fda07687ca5c5c28af92d869658a527dec/observations/20261119T161517.228527912Z-2121289-0/result.json`
- 검증된 요약: 같은 head 디렉터리의 `providers/github-actions/runs/44522105929/attempts/1/{test_medium,test_shell,test_sql_by_cci}/summary.json`
- 실패 내용: `.../test_shell/failures/shell_06_issues_12_2h_bug_bts_8907_cases_bug_bts_8907_sh-0e7a776ddd/`, `.../test_shell/failures/shell_06_issues_26_2h_cbrd_27780_cases_cbrd_27780_sh-9b5694291f/`
- baseline: `github-actions/CUBRID-cubrid/commits/8c478d8559905330bc1a60a05dbebb273b07a16c/providers/github-actions/runs/44511473106/attempts/1/`

## develop 위 재실행: 2026-11-20, head `b6de23c3f9`, run 44705649588

> **경고.** `test_sql`은 이전 run들과 같은 collector 무결성 오류로 검증된 요약이 없다(CI 결과는 SUCCESS). develop tip `030b650ff7`에는 test suite를 돌린 CI run이 없어서(push run은 빌드만 함) `collect-base`가 `not_observed`였다. 대신 같은 시기 develop을 base로 하는 다른 PR의 run과, 로컬 head/base 실행으로 비교했다.

### 요약

- 검증된 실패는 shell 2건이다. `cbrd_27780.sh`(shard 31)와 `cbrd_27863.sh`(shard 00)다. medium(975개)과 sql_by_cci(17848개)는 모두 통과했다.
- 두 건 모두 이 PR과 관계없다(신뢰도 높음). serial을 건드리지 않는 develop PR #8528, #8664에서 `cbrd_27780`이 같은 메시지(`S1HEAP=1`)로 실패했다. `cbrd_27863`은 #8528, #8613, #8641, #8664 run 6개에서 모두 같은 값(`REQUESTS_OF_ONE_CONNECTION=10`)으로 실패했다.
- 로컬에서 `cbrd_27863`은 head `b6de23c3f9`와 base `030b650ff7` 모두 `REQUESTS_OF_ONE_CONNECTION=10`으로 실패했다. CI와 같다.
- 로컬에서 `cbrd_27780`은 head와 base 모두 같은 항목(3번 vacuum, 7번 kill)이 실패했고 `S1HEAP` 평문은 재현되지 않았다. head와 base의 결과가 같으므로 이 PR과의 차이는 보이지 않는다.
- 지난 run 44522105929의 `cbrd_27780` 실패도 같은 원인으로 본다. 그때 "head에만 있음"이었던 것은 base(`feature/oos-merge`)가 한 번 통과한 결과였다.

### 대상

| 항목 | 값 |
| --- | --- |
| PR | https://github.com/CUBRID/cubrid/pull/8514 |
| head | `b6de23c3f927f408d0c642a717a64eae45b923f7` (develop `030b650ff7` 위로 rebase, 커밋 5개 `git range-diff` 동일) |
| base | `develop` `030b650ff7bfaab62e05bdf35d79a19b40568aea` (merge base와 같음, #8662 빌드 수정 포함) |
| run | https://github.com/CUBRID/cubrid/actions/runs/44705649588 attempt 1 (`/run all`, 2026-11-20T08:49:41Z) |
| testcase revision | cubrid-testcases-private-ex `6be2ee8f2` (`tc/pr-8514`), cubrid-testcases `903d902b8` (`tc/pr-8514`), 둘 다 TC develop 최신을 포함(`cubrid-pr-tc-base-check` PASS) |
| 수집 | `cubrid-ci 0.2.0 (00205d576de0, release)`, collect exit 4(test_sql 무결성), collect-base exit 3(`not_observed`) |

### Suite 상태

| Suite | CI 결과 | 수집 상태 | head (tests/pass/fail/error/skip) |
| --- | --- | --- | --- |
| test_medium | pass | completed | 975/975/0/0/0 |
| test_shell | fail | completed | 3659/3627/2/0/30 |
| test_sql | pass | `collection_failed` (shard 01 JUnit 19개 누락, 이전과 같음) | 없음 |
| test_sql_by_cci | pass | completed | 17848/17848/0/0/0 |

### 실패 목록

| Testcase | shard | 증상 | 다른 develop PR | 로컬 head / base | PR 관련성 |
| --- | --- | --- | --- | --- | --- |
| `shell/_06_issues/_26_2h/cbrd_27780/cases/cbrd_27780.sh` | 31 | NOK 2, NOK 4: "found in plaintext in the data volumes: S1HEAP=1" | #8528 run 44705951222, 44713351787; #8664 run 44701074949에서 같은 메시지 | 둘 다 NOK 3, 7 (같음), `S1HEAP` 재현 안 됨 | 없음, 신뢰도 높음 |
| `shell/_06_issues/_26_2h/cbrd_27863/cases/cbrd_27863.sh` | 00 | NOK 1: `REQUESTS_OF_ONE_CONNECTION=10` (기준 1~8) | #8528 run 44705951222, 44713351787; #8613 run 44706214451; #8641 run 44664225458, 44702880730; #8664 run 44701074949에서 같은 값 | 둘 다 NOK 1, 값 10 (같음) | 없음, 신뢰도 높음 |

### 원인 가설

#### `cbrd_27863`: dba 로그인 1회의 server 요청 수

- 관찰. testcase는 CAS가 server 연결을 유지한 상태에서 dba 로그인 1회가 보내는 server 요청이 8개 이하인지 본다. 엔진 수정 `6057fbf0d9`(#8447)는 develop에 있고, TC `9f6f1a7fe`(#4793)는 2026-11-20에 TC develop에 들어왔다.
- 관찰. develop PR 4개와 이 PR, 로컬 base `030b650ff7`이 모두 10을 낸다.
- 추론. 엔진 수정이 들어간 뒤 develop에 들어온 다른 변경이 로그인 요청을 2개 늘렸거나, TC 기준이 CI 환경과 맞지 않는다. 이 PR은 로그인 경로를 바꾸지 않는다.
- 원인(2026-11-20 확인). TC 기준(8)을 정한 뒤 develop에 들어온 CBRD-27445(#8337)가 로그인마다 password challenge와 response 요청을 하나씩 더 보낸다. 상한을 10으로 올리는 TC 수정 [cubrid-testcases-private-ex#5056](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5056)이 열려 있다.
- 다음 행동. #5056 머지 뒤 `tc/pr-8514`를 TC develop과 맞추고 `/run rerun 44705649588`을 올린다.

#### `cbrd_27780`: 암호화 테이블 marker의 평문 1건

- 관찰. 같은 메시지가 serial을 건드리지 않는 develop PR 2개에서 나왔다.
- 관찰. 이 PR의 변경은 `keep_form` 플래그로 막혀 있고, 플래그를 켜는 호출은 `serial.c`의 `serial_update_serial_object`와 `serial_row_write_keep_value`뿐이다. 다른 호출에서는 develop과 같은 코드가 실행된다. testcase는 serial과 AUTO_INCREMENT를 쓰지 않는다.
- 관찰. 로컬 containment 실행에서는 3번(vacuum 뒤 page 수를 읽지 못함)과 7번(kill 뒤 server가 남아 있음)이 head와 base에서 똑같이 실패했다. 로컬 환경 차이로 보이며, 2번과 4번은 OK였다.
- 추론. CI 환경에서 develop 전반에 나타나는 TC 또는 엔진 문제다. 이 PR이 원인이 아니다.
- 원인(2026-11-20 확인). CBRD-28257(Confirmed): 시스템 카탈로그 행의 NULL 고정 길이 필드에 서버 메모리의 이전 내용이 남아 암호화 테이블 값 조각이 평문으로 기록된다. 간헐적이다. develop CI 발생 기록을 CBRD-28257에 코멘트로 남겼다([comment 4778883](https://jira.cubrid.org/browse/CBRD-28257?focusedCommentId=4778883)).
- 다음 행동. rerun에서 다시 실패하면 CBRD-28257을 근거로 merge 담당에게 waiver를 요청한다.

### 로컬 재현 기록

| attempt | engine | testcase | 결과 |
| --- | --- | --- | --- |
| `~/tk/p8514h1` | head `b6de23c3f9` | `cbrd_27780` | NOK 3, 7 |
| `~/tk/p8514h2` | head `b6de23c3f9` | `cbrd_27863` | 결론 없음: install에 JDBC jar가 없어 `No suitable driver` |
| `~/tk/p8514h3` | head `b6de23c3f9` (`cubrid-jdbc` submodule 초기화 후 재설치) | `cbrd_27863` | NOK 1, `REQUESTS_OF_ONE_CONNECTION=10` |
| `~/tk/p8514b1` | base `030b650ff7` | `cbrd_27780` | NOK 3, 7 |
| `~/tk/p8514b2` | base `030b650ff7` | `cbrd_27863` | NOK 1, `REQUESTS_OF_ONE_CONNECTION=10` |

- 모두 `cubrid-testkit` native shell, `TESTKIT_CONTAIN=1`, 한 slot, testcase checkout `6be2ee8f2`(dirty 없음). 각 attempt의 `verify.log`, `run.log`, `CTP/result/shell/current_runtime_logs/`를 남겼다.

### 다음 행동

1. 이 PR에서 고칠 것은 없다. 남은 실패 2건은 develop 공통이다.
2. 머지 판단에는 required context(`build (release)`, `test_shell`, `test_sql`, `test_medium`)가 필요하다. `test_shell`이 develop 공통 실패로 FAILURE이므로, 이 실패를 알려진 문제로 받아들일지는 리뷰어와 merge 담당이 정한다.
3. test_sql shard 01 JUnit 누락은 collector 또는 CI 결과 파일 쪽 후속 과제다(이전과 같음).

### 근거 파일 (2026-11-20, head `b6de23c3f9`)

- head 요약: `cubrid-ci` 데이터 디렉터리의 `github-actions/CUBRID-cubrid/pr-8514/b6de23c3f927f408d0c642a717a64eae45b923f7/providers/github-actions/runs/44705649588/attempts/1/{test_medium,test_shell,test_sql_by_cci}/summary.json`
- 실패 내용: 같은 디렉터리의 `test_shell/failures/shell_06_issues_26_2h_cbrd_27780_cases_cbrd_27780_sh-9b5694291f/`, `test_shell/failures/shell_06_issues_26_2h_cbrd_27863_cases_cbrd_27863_sh-d03fb7d9ea/`
- 다른 PR 근거: `github-actions/CUBRID-cubrid/pr-{8528,8613,8641,8664}/<head>/providers/github-actions/runs/<run>/attempts/1/test_shell/failures/`

## ASSERT_EQ·shell TC 추가 후 재실행: 2026-11-24, head `8e2f18dcb6`, run 45132951323

> **경고.** 이번 수집은 전체 검증이 끝나지 않았다(`report_mode: warning`, `observation: incomplete`, `requested_summaries: partial`, `baseline: partial_exact`, `regression_conclusions_allowed: false`, `comparison_scope: none`). `test_sql`이 head와 exact merge-base 모두에서 기존 shard 01 JUnit 19건 누락 무결성 오류로 `collection_failed`여서 검증된 요약이 없다(양쪽 모두 CI 상태는 `SUCCESS`). 따라서 이 절은 전체 회귀 결론을 내리지 않으며, 검증된 3개 suite(`test_medium`, `test_shell`, `test_sql_by_cci`)에 한정된 관찰과 merge-base 대조를 기록한다.

### 요약

- 검증된 3개 suite에서 head 실패는 총 3건(`test_shell` 1건 `cbrd_28061.sh`, `test_sql_by_cci` 2건 `cbrd_28202.sql`, `cbrd_27752.sql`)이며 error는 0건이다. `test_medium`(975/975)과 `gha-ci: build (debug)`/`gha-ci: build (release)`는 통과했고, `test_sql`은 CI `SUCCESS`이나 collector 검증이 미완료다.
- 3건 모두 exact merge-base `30eb0c4b8b`의 검증된 run [45204880813](https://github.com/CUBRID/cubrid/actions/runs/45204880813) attempt 1에서 **동일한 실패 시그니처(`diff.txt` 바이트 완전 일치)**로 재현된 `also_observed_on_base` 실패다(`additional_on_head` 0건, `uncomparable` 0건, `base_only` 0건).
- 세 실패 모두 이미 각 testcase 저장소 `develop`에 수정 PR이 머지되었다.
  - `cbrd_28061.sh` → [CUBRID/cubrid-testcases-private-ex#5102](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5102) (커밋 `f726b044d2`, `STORAGE FORCE_INLINE` 적용, `2026-11-24T08:34:05Z` 머지)
  - `cbrd_28202.sql` → [CUBRID/cubrid-testcases#4405](https://github.com/CUBRID/cubrid-testcases/pull/4405) (커밋 `ffe8f3b5bf`, `autocommit off;`를 헤더 주석 앞으로 이동, `2026-11-24T02:54:45Z` 머지)
  - `cbrd_27752.sql` → [CUBRID/cubrid-testcases#4406](https://github.com/CUBRID/cubrid-testcases/pull/4406) (커밋 `2eb52eb3f3`, `autocommit off;`를 헤더 주석 앞으로 이동, `2026-11-24T02:55:40Z` 머지)
- 이번 PR이 private TC PR [#4877](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4877)로 추가한 `shell/_06_issues/_26_2h/cbrd_28073/cases/cbrd_28073.sh`는 shard 09에서 실행되어 통과(16.490s)했고, 기존 간헐 실패였던 `cbrd_27780.sh`(CBRD-28257)도 shard 11에서 통과(42.237s)했다.
- `TC Merge Gate / Check TC PRs` 실패(run [45132831393](https://github.com/CUBRID/cubrid/actions/runs/45132831393/job/137552037079))는 TC PR [#4173](https://github.com/CUBRID/cubrid-testcases/pull/4173)/[#4877](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4877)을 격리 유지를 위해 열어 둔 상태이므로 회귀 실패가 아니며 최종 병합 핸드오프로 보류한다.
- **다음 행동 핵심**: TC 수정(`#5102`, `#4405`, `#4406`)을 받기 위해 `tc/pr-8514`를 최신 TC `develop`과 동기화하면, `30eb0c4b8b` 이후 엔진 `develop`에 머지된 16개 커밋에 대응하는 새 TC들도 함께 들어온다. 특히 그중 **PR #8460 (`44e9290f38`, CBRD-27744)**이 `src/query/serial.c`(+789/-163)를 크게 변경하고 `serial_repl_prepare` 위 헬퍼에 새 `heap_attrinfo_transform_to_disk` 호출을 추가했으므로, 단순 TC 동기화+재실행보다 최신 `develop` 위로 리베이스하면서 해당 호출의 `keep_form` 적용 필요성을 먼저 점검한 뒤 승인 하에 push·TC 동기화·`/run all`을 진행하는 것이 안전하다.

### 대상

| 항목 | 값 |
| --- | --- |
| PR | https://github.com/CUBRID/cubrid/pull/8514 (`OPEN`, non-draft) |
| head | `8e2f18dcb6fde008c137ffec19233cb4de235613` (로컬 브랜치 `CBRD-28073-serial-nextval-keep-form`, base `30eb0c4b8b` 위 커밋 6개: `e641371cde`, `c22d949de8`, `22bc063206`, `6428ad07f4`, `7303688cc5`, `8e2f18dcb6`) |
| base / merge-base | `develop` `30eb0c4b8bf12c09697977c325918df8bbd2acb6` (merge-base와 일치) |
| head run | https://github.com/CUBRID/cubrid/actions/runs/45132951323 attempt 1 (`issue_comment`, 2026-11-23T07:41:34Z ~ 11:23:07Z) |
| base run | https://github.com/CUBRID/cubrid/actions/runs/45204880813 attempt 1 (`workflow_dispatch`, `dispatch all 30eb0c4b8bf12c09697977c325918df8bbd2acb6`, 2026-11-23T15:24:31Z ~ 17:29:55Z; build producer run `45131748657` attempt 1, `sha=30eb0c4b8b`) |
| 요청 suite | `test_medium`, `test_sql`, `test_shell`, `test_sql_by_cci` (head에 `gha-ci: test_sql_by_cci` status 존재) |
| 수집 / 검증 | head `2026-11-24T08:34:25Z` (`collect` exit 4, `verify` exit 3), base `2026-11-24T08:35:34Z` (`collect-base` exit 4, `verify` exit 3), `cubrid-ci 0.2.0 (00205d576de0, release)` |
| head observation | `pr-8514/8e2f18dcb6fde008c137ffec19233cb4de235613/observations/20261124T083413.018220767Z-2581844-0` |
| base observation | `commits/30eb0c4b8bf12c09697977c325918df8bbd2acb6/observations/20261124T083534.157598311Z-2627235-0` |
| verify / report_mode | identity `established`, observation `incomplete`, manifest `validated`, requested summaries `partial`, baseline `partial_exact` → `report_mode: warning` |
| testcase revision (head) | shell: `cubrid-testcases-private-ex` `023a5ec33d342641c05a53a85f1db6c353535aef` (`tc/pr-8514`), medium/sql_by_cci: `cubrid-testcases` `aaa0ac947c2ee400f8a08296b0844405d6385b36` (`tc/pr-8514`) |
| testcase revision (base) | shell: `cubrid-testcases-private-ex` `913bb726d41ee48a703bd438629036cf8d415688` (`develop`), medium/sql_by_cci: `cubrid-testcases` `98b4755b9e028312065edbb84f904e0e13d3aae6` (`develop`) |
| engine build provenance | head 모든 shard `build.sha=8e2f18dcb6...` (`run_id=45132951323`, attempt 1; medium/shell debug, sql_by_cci release); base 모든 shard `build.sha=30eb0c4b8b...` (`run_id=45131748657`, attempt 1; medium/shell debug, sql_by_cci release) |

### Suite 상태

| Suite | head CI 결과 | head 수집 상태 | head (tests/pass/fail/err/skip) | base run 45204880813 |
| --- | --- | --- | --- | --- |
| `test_medium` | `SUCCESS` | `completed` (`validated`) | 975 / 975 / 0 / 0 / 0 (`planned=975`, `run=975`) | `SUCCESS` / `completed` (`validated`) / 975 / 975 / 0 / 0 / 0 |
| `test_shell` | `FAILURE` | `completed` (`validated`) | 3675 / 3644 / 1 / 0 / 30 (`planned=3675`, `run=3645`) | `FAILURE` / `completed` (`validated`) / 3674 / 3643 / 1 / 0 / 30 (`planned=3674`, `run=3644`) |
| `test_sql` | `SUCCESS` | `collection_failed` (요약 없음) | 없음 (raw `failed.list` 0바이트, 미검증) | `SUCCESS` / `collection_failed` (요약 없음) |
| `test_sql_by_cci` | `FAILURE` | `completed` (`validated`) | 17864 / 17862 / 2 / 0 / 0 (`planned=17864`, `run=17864`) | `FAILURE` / `completed` (`validated`) / 17864 / 17862 / 2 / 0 / 0 |

- 기타 PR 체크 (수집 suite 외): `gha-ci: build (debug)`, `gha-ci: build (release)`, `license`, `pr-style`, `code-style`, `cppcheck`, `memory-monitor-check`는 모두 `SUCCESS`이며 `Re-check stale verdicts`는 `SKIPPED`다. `TC Merge Gate / Check TC PRs`는 run [45132831393](https://github.com/CUBRID/cubrid/actions/runs/45132831393/job/137552037079)에서 `FAILURE`("TC Merge Gate FAILED — TC changes are not on TC develop yet")를 보고했으나, 이는 TC PR `#4173`/`#4877`을 격리 유지를 위해 열어 둔 상태이므로 회귀 실패가 아니며 최종 병합 핸드오프로 보류한다.
- `test_shell`의 head/base +1 차이는 이번 PR의 동반 TC PR `#4877`이 추가한 `shell/_06_issues/_26_2h/cbrd_28073/cases/cbrd_28073.sh`이며 shard 09에서 `16.490s`로 통과했다. 이전 run에서 반복 실패하던 `shell/_06_issues/_26_2h/cbrd_27780/cases/cbrd_27780.sh`(CBRD-28257)도 이번 head shard 11에서 `42.237s`로 통과했다.

### 실패 목록

| Suite | Testcase | shard (head / base) | 결과 | 관찰 시그니처 | base 비교 | 분류 / `cubrid-tcr` | PR 관련성 (확신) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `test_shell` | `shell/_06_issues/_26_2h/cbrd_28061/cases/cbrd_28061.sh` | 29 / 12 | `failure` | `cbrd_28061-1 : NOK setup: h1 holds 11520 rows in 237 pages, expected 11520 rows in more than 11520 pages` | `also_observed_on_base` | TC/OOS 기대값 불일치 (`no_match`) | `unlikely` (높음) |
| `test_sql_by_cci` | `sql/_13_issues/_26_2h/cases/cbrd_28202.sql` | 03 / 03 | `failure` | 첫 문장(`/** ... */` 뒤 `autocommit off;`)에서 `0` 대신 `Error:-493`, 이후 statement block 불일치 (`.answer` 대조, head/base `diff.txt` 바이트 일치) | `also_observed_on_base` | CCI 러너 지시어 위치 (`known_job`: `sql-by-cci-every-branch`) | `unlikely` (높음) |
| `test_sql_by_cci` | `sql/_36_guava/cbrd_27752/cases/cbrd_27752.sql` | 09 / 09 | `failure` | 첫 문장(`/** ... */` 뒤 `autocommit off;`)에서 `0` 대신 `Error:-493`, 이후 statement block 불일치 (`.answer` 대조, head/base `diff.txt` 바이트 일치) | `also_observed_on_base` | CCI 러너 지시어 위치 (`known_job`: `sql-by-cci-every-branch`) | `unlikely` (높음) |

- **개수 정합성**: head 검증 실패 3건 (`test_shell` 1 + `test_sql_by_cci` 2, error 0) = `also_observed_on_base` 3 + `additional_on_head` 0 + `uncomparable` 0. `base_only`는 0건이다(`test_sql`은 양쪽 모두 `collection_failed`로 비교 제외).

### 원인 분석

#### 그룹 1: `cbrd_28061.sh` — OOS 적용 후 heap 페이지 수 기대값 불일치 (`test_shell`)

- **관찰.**
  - head (`8e2f18dcb6`, shard 29)와 exact merge-base (`30eb0c4b8b`, run `45204880813`, shard 12) 모두 동일한 실패 메시지 `cbrd_28061-1 : NOK setup: h1 holds 11520 rows in 237 pages, expected 11520 rows in more than 11520 pages`와 동일한 `diff.txt`를 냈다.
  - testcase 파일 `shell/_06_issues/_26_2h/cbrd_28061/cases/cbrd_28061.sh`는 head(`023a5ec33d34`)와 base(`913bb726d41e`) 사이에서 `git diff --stat` 차이가 0이다.
  - `cbrd_28061.sh`는 4K page DB(`enable_string_compression=no`)에 11,520행이 각각 1페이지씩 차지하도록 의도한 테스트로, serial/AUTO_INCREMENT를 쓰지 않는다.
  - PR #8514는 `src/query/serial.c`(2개 호출), `src/storage/heap_file.c`/`heap_file.h`(`keep_form` 인자·`heap_attrinfo_transform_to_disk_keep_form`), `unit_tests/oos/`만 수정하며 일반 user heap의 `keep_form=false` 경로를 바꾸지 않는다.
  - [CUBRID/cubrid-testcases-private-ex#5102](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5102)(`[CBRD-28061] Keep each row of cbrd_28061 in one heap page with STORAGE FORCE_INLINE`, 커밋 `f726b044d2`)가 `2026-11-24T08:34:05Z`에 TC `develop`으로 머지되었다.
- **추론.** OOS 도입 후 `cbrd_28061.sh`의 긴 문자열 행이 OOS로 빠져 11,520행이 237개 heap 페이지만 차지했기 때문에 setup 검사가 실패한 것이며, 이미 `#5102`로 해결되었다. PR #8514와는 무관하다(`unlikely`, 확신 높음).
- **모르는 것.** `#5102`가 반영된 TC `develop` 위에서 본 PR의 head가 `cbrd_28061.sh`를 실제로 통과하는지는 아직 실행해 보지 않아 미확인이다.
- **반증 조건.** `#5102` 커밋 `f726b044d2`를 포함한 `tc/pr-8514`로 재실행했을 때 head에서만 `cbrd_28061.sh`가 실패하고 `develop`에서는 통과하면 이 판정은 틀린다.
- **다음 행동.** 최신 `develop` 리베이스(또는 TC 동기화) 시 `#5102`를 반영해 재실행으로 통과를 확인한다.

#### 그룹 2: `cbrd_28202.sql`, `cbrd_27752.sql` — `test_sql_by_cci`에서 블록 주석 뒤 `autocommit off;` 파싱 실패

- **관찰.**
  - 두 케이스 모두 `.answer_cci`가 없고 `.answer`를 기대 출력으로 사용한다(`message.txt`의 `** Expected :`로 확인).
  - head (`8e2f18dcb6`)와 exact merge-base (`30eb0c4b8b`) 모두 첫 문장(`/** ... */` 블록 주석 바로 뒤의 `autocommit off;`)에서 `0` 대신 `Error:-493`이 발생해 이후 statement block 전체가 어긋났으며, `diff.txt`가 head와 base에서 바이트 단위로 완전히 일치한다(`IDENTICAL`).
  - public TC 저장소에서 head(`aaa0ac947c2e`)와 base(`98b4755b9e02`) 사이에 두 파일과 `.answer`의 차이가 0이다.
  - CSQL을 쓰는 `test_sql`은 head와 base 모두 `SUCCESS`였다.
  - [CUBRID/cubrid-testcases#4405](https://github.com/CUBRID/cubrid-testcases/pull/4405)(커밋 `ffe8f3b5bf`, `2026-11-24T02:54:45Z` 머지)와 [CUBRID/cubrid-testcases#4406](https://github.com/CUBRID/cubrid-testcases/pull/4406)(커밋 `2eb52eb3f3`, `2026-11-24T02:55:40Z` 머지)이 `autocommit off;`를 헤더 주석 블록 앞으로 옮겨 수정했다.
  - `cubrid-tcr check`는 두 건 모두 활성 job 규칙 `sql-by-cci-every-branch`(만료 `2026-12-09`, 남은 일수 15일)에 의해 `known_job`으로 판정했다.
- **추론.** `test_sql_by_cci` 실행기가 선행 `/** ... */` 주석 블록 뒤의 `autocommit off;` 지시어를 일반 SQL로 서버에 보내 `-493` 구문 오류를 일으킨 기존 TC 작성 위치 문제이며, `#4405`/`#4406`으로 이미 TC `develop`에서 수정되었다. PR #8514와는 무관하다(`unlikely`, 확신 높음).
- **모르는 것.** `#4405`, `#4406` 반영 후 이 head에서 두 케이스가 통과하는지, 그리고 `test_sql`의 미검증 raw 결과에 다른 특이사항이 없는지는 검증된 요약이 없어 미확인이다.
- **반증 조건.** `#4405`/`#4406` 이후의 TC에서도 head가 `cbrd_28202.sql` 또는 `cbrd_27752.sql`에서 실패하고 base가 통과하면 이 판정은 틀린다.
- **다음 행동.** 최신 TC `develop` 동기화 시 `#4405`/`#4406`을 받아 재실행으로 통과를 확인한다. `test_sql_by_cci`는 opt-in 체크이나 head에 status가 이미 붙어 있으므로 함께 확인한다.

### Base 비교

- **Pinned identities**: head `8e2f18dcb6fde008c137ffec19233cb4de235613`, target `develop` tip(수집 시점 `30eb0c4b8bf12c09697977c325918df8bbd2acb6`), exact merge-base `30eb0c4b8bf12c09697977c325918df8bbd2acb6` (일치).
- **Discovery coverage**: `all paginated exact-commit statuses and check runs; no repository-wide workflow scan`.
- **Selected runs**: head `45132951323` attempt 1 vs base `45204880813` attempt 1 (`workflow_dispatch`, build producer run `45131748657` attempt 1, `sha=30eb0c4b8b`).
- **TC revision 대조**:
  - private (`cubrid-testcases-private-ex`): head `023a5ec33d342641c05a53a85f1db6c353535aef` (`tc/pr-8514`) vs base `913bb726d41ee48a703bd438629036cf8d415688` (`develop`). 차이 파일은 `shell/_06_issues/_26_2h/cbrd_28073/cases/cbrd_28073.sh`(+173줄) 1건뿐이며 `cbrd_28061` 디렉터리 diff는 없다.
  - public (`cubrid-testcases`): head `aaa0ac947c2ee400f8a08296b0844405d6385b36` (`tc/pr-8514`) vs base `98b4755b9e028312065edbb84f904e0e13d3aae6` (`develop`). 파일 차이 0건이며 `cbrd_28202`, `cbrd_27752`와 `.answer` diff는 없다.
- **설정 및 한계**: 양쪽 모두 `test_medium`·`test_shell`은 debug, `test_sql_by_cci`는 release 빌드로 실행되었다. `test_sql`은 양쪽 모두 `collection_failed`여서 비교할 수 없으며, head와 base 각각 1회 실행 결과다.

### 수집 기록과 진단

- **Acquisition ledger**: head와 base 모두 `test_medium` 1/1, `test_shell` 50/50, `test_sql` 10/10, `test_sql_by_cci` 10/10 shard가 모두 `retained`다(`failed` 0, `not_attempted` 0).
- **Binary budget**: head와 base 모두 `configured_bytes: 536870912`, `consumed_bytes: 0`.
- **`test_sql` 진단**: head와 base 모두 shard 01에서 JUnit이 `summary_info`보다 19개 적다(`summary_info 3557/0/0` 대 `JUnit 3538/0/0`). 누락된 19건은 모두 `sql/_05_plcsql/_01_testspec/_05_bug_fix/` 아래 `cbrd-27500`, `cbrd-27556`, `cbrd-27584`, `cbrd-27633`, `cbrd-27634`, `cbrd-27742`, `cbrd-27927` 케이스로, 이전 run들 및 develop base와 완전히 동일한 기존 문제다.

### Testcase 이력

- 도구 버전: `cubrid-tcc 0.3.0`, `cubrid-tcr 0.1.0`.
- `cubrid-tcc sync-data --run 45132951323 --suite test_shell --revisit-limit 0 --json` 1회 실행 결과: `observations: 0`, `unavailable_files: 1`, `missing_remaining: 2980`.
- `cbrd_28061.sh`: Chronicle `history_result`는 `UNKNOWN_HISTORY` (`not_indexed`, `not_indexed_reason: never_observed`, `suite_last_sync: 2026-11-18T11:28:20Z`). `cubrid-tcr show`가 안내한 날짜 구간 sync(`--since 2026-11-10T08:43:20Z --until 2026-11-24T08:37:53Z --suite shell`)와 `missing_runs: 2980` 갭은 명령 시간 제한상 실행하지 않고 기록으로 남긴다. shell 근거는 실패만 남으므로 통과 기록이 없는 것은 안정성 근거가 아니다. `cubrid-tcr check` 판정은 `no_match`다.
- `cbrd_28202.sql`, `cbrd_27752.sql`: `test_sql_by_cci`는 Chronicle 미수집 suite(`UNSUPPORTED_SUITE` / `suite_not_collected`)이므로 이력 조회가 불가하다. `cubrid-tcr check` 판정은 두 건 모두 `known_job` (`sql-by-cci-every-branch`, 만료일 `2026-12-09`)이다.

### 모르는 것

- TC 수정(`#5102`, `#4405`, `#4406`)이 반영된 최신 TC `develop` 위에서 본 PR의 head가 4개 suite를 모두 통과하는지 여부.
- `test_sql`의 검증된 요약 내용(shard 01 JUnit 19건 누락으로 `collection_failed`).
- `30eb0c4b8b` 이후 `develop`에 머지된 PR `#8460` (`44e9290f38`, CBRD-27744)이 `src/query/serial.c`의 `serial_repl_prepare` 위 헬퍼에 새로 추가한 `heap_attrinfo_transform_to_disk` 호출이 `_db_serial`의 `keep_form` 불변식과 충돌하는지 여부.

### 다음 행동

1. **엔진 코드 선점검 + 리베이스 권장**: `30eb0c4b8b` 이후 `develop`에 16개 커밋(최신 `e3bbe664b5`까지)이 들어왔고, 특히 `#8460`(`44e9290f38`)이 `src/query/serial.c`를 크게 수정하며 `heap_attrinfo_transform_to_disk`를 새로 호출한다. 단순 TC 동기화 시 새 엔진용 TC도 함께 들어오므로, 사용자 승인 후 `CBRD-28073-serial-nextval-keep-form`을 최신 `develop` 위로 리베이스하고 `#8460` 상호작용을 점검한 뒤 `vk` force-push, 양쪽 `tc/pr-8514` 최신화/push, `/run all` 재실행을 진행하는 것이 안전하다.
2. **동반 private TC PR [#4877](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4877) 정비 (승인 후)**: 현재 Draft이고 `No enlisted reviewers`로 BLOCKED다. `cbrd_28073.sh`(+173줄)가 run `45132951323`에서 통과했으므로 사용자 승인 후 Draft 해제(Ready), 제목/본문 정리 및 리뷰어 지정(`hornetmj`·`H2SU`·`shparkcubrid` 중 선택)을 진행한다.
3. **엔진 PR [#8514](https://github.com/CUBRID/cubrid/pull/8514) 리뷰 게이트 정리**: 현재 `hornetmj`, `shparkcubrid`, `H2SU`가 `APPROVED`이고 `beyondykk9`가 `pending request`로 `BLOCKED`다. 리베이스·CI 완료 후 `beyondykk9` 재리뷰 대기, 요청 해제, 또는 명시적 예외 승인 중 하나를 사용자 결정에 따라 처리한다.
4. **최종 병합 핸드오프**: 위 항목 완료 후 `cubrid-pr-approval-check` 재실행 → `#4877` 승인/병합 및 0-파일 `#4173` 무변경 확인 후 종료 → `Check TC PRs` 재실행 GREEN 확인 → `#8514` 병합 순서로 진행한다.

### 근거 파일 (2026-11-24, head `8e2f18dcb6`)

- head observation: `cubrid-ci` 데이터 디렉터리의 `github-actions/CUBRID-cubrid/pr-8514/8e2f18dcb6fde008c137ffec19233cb4de235613/observations/20261124T083413.018220767Z-2581844-0/result.json`
- head 검증 요약: 같은 head 디렉터리의 `providers/github-actions/runs/45132951323/attempts/1/{test_medium,test_shell,test_sql_by_cci}/summary.json`
- head 실패 상세: 같은 run 디렉터리의 `test_shell/failures/shell_06_issues_26_2h_cbrd_28061_cases_cbrd_28061_sh-6639bbc2f3/`, `test_sql_by_cci/failures/sql_13_issues_26_2h_cases_cbrd_28202_sql-932a55f4f8/`, `test_sql_by_cci/failures/sql_36_guava_cbrd_27752_cases_cbrd_27752_sql-e68bb090ac/`
- head `cbrd_28073.sh` / `cbrd_27780.sh` 통과 JUnit: 같은 run 디렉터리의 `test_shell/raw/shards/09/linux_shell_64bit_optdebug.xml`, `test_shell/raw/shards/11/linux_shell_64bit_optdebug.xml`
- base observation / 검증 요약: `cubrid-ci` 데이터 디렉터리의 `github-actions/CUBRID-cubrid/commits/30eb0c4b8bf12c09697977c325918df8bbd2acb6/observations/20261124T083534.157598311Z-2627235-0/result.json` 및 `providers/github-actions/runs/45204880813/attempts/1/{test_medium,test_shell,test_sql_by_cci}/summary.json`
- TC Git 객체 확인: `/home/vimkim/gh/cubrid-testcases-private-ex/develop` (`023a5ec33d34`, `913bb726d41e`), `/home/vimkim/gh/cubrid-testcases/develop` (`aaa0ac947c2e`, `98b4755b9e02`)

## keep_form 반영 리베이스 후 재실행: 2026-11-25, head `337e4f5867`, run 45385469421

> **경고.** 이번 수집은 전체 검증을 통과하지 못했다(`report_mode: warning`, `observation: incomplete`, `requested_summaries: partial`, `baseline: partial_exact`, `regression_conclusions_allowed: false`). `test_sql`은 head와 exact merge-base 모두 기존 shard 01 JUnit 19건 누락 무결성 오류로 `collection_failed`이다. 따라서 `test_sql` 실패 7건은 검증된 요약이 아니라 raw `summary_info`, raw JUnit, CI job log, 아티팩트 서버의 `ctp_log.tgz`(core 분석 포함)에서 직접 읽었다. 이 절의 `test_sql` 판정은 그 한계 안의 추론이다.

### 요약

- 분석일 2026-11-25 (Asia/Seoul). head `337e4f5867`의 run [45385469421](https://github.com/CUBRID/cubrid/actions/runs/45385469421) attempt 1에서 `test_shell` 1건, `test_sql` 7건이 실패했다. `test_medium`(975/975), `test_sql_by_cci`(17882/17882), debug/release build는 통과했다.
- **`test_shell` `bug_bts_8907.sh`**: server 재시작 뒤 10초 안에 CCI 재연결을 기대하는 타이밍 테스트다. 이번에는 `-224`(`ER_OBJ_NO_CONNECT`)만 나왔다. 2026-11-19 run 44522105929에서도 같은 testcase가 실패했고, Chronicle에는 다른 PR 4개와 PR 없는 run 1개에서 실패 5번, 통과 480번이 있다. 간헐 실패이고 PR 관련성은 `unlikely`(확신 높음)이다.
- **`test_sql` 7건은 원인이 하나다.** `cbrd_27742_02.sql` 실행 중 debug `cub_server`가 `pgbuf_timed_sleep`(`page_buffer.c:8063`)의 `assert (0)`으로 죽었다. vacuum worker(`vacuum_heap_page`)가 READ latch(`fcnt=1`)가 걸린 heap page에 WRITE latch를 300초 기다렸다. 나머지 6건은 그 결과다. `cbrd_27927.sql`은 server 복구 중 연결에 실패했고, 5건은 `cbrd_27742_02`가 지우지 못한 객체(`p1`–`p3`, `f4`, `f5`, `t`, `t2`, `v2`) 때문에 실패했다.
- exact merge-base `8e052e99c5`의 run [45425193182](https://github.com/CUBRID/cubrid/actions/runs/45425193182)에서는 4개 suite가 모두 통과했다(`cbrd_27742_02` 635 ms, `bug_bts_8907` 통과). SQL testcase tree는 head와 base에서 바이트까지 같다. 따라서 8건 모두 `additional_on_head`이다. 하지만 PR diff는 `_db_serial` 행 인코딩(`keep_form`)만 바꾸고 page latch, vacuum, heap scan 경로는 바꾸지 않는다. 실패한 testcase는 serial을 쓰지 않는다.
- `cbrd_27742_02`는 로컬에 보관된 다른 CI 번들 38개에서 모두 통과했다. 실패는 이번 1건뿐이다. vacuum 진행 타이밍에 따라 드물게 나는 page latch 교착으로 추정한다. PR 관련성은 `unlikely`(확신 중간)이다. 이 교착은 PR과 별개인 엔진 버그 후보이다.
- **다음 행동**: `/run rerun 45385469421`(실패 job만 재실행)을 권장한다. 코드나 TC 수정은 필요 없다. `cbrd_27742_02` 교착은 별도 JIRA 후보로 추적한다(CI 통과 요건을 면제하지 않는다).

### 대상

| 항목 | 값 |
| --- | --- |
| PR | https://github.com/CUBRID/cubrid/pull/8514 (`OPEN`, non-draft) |
| head | `337e4f5867fc524676a63f66dd11028bdebb9a83` (base `8e052e99c5` 위 커밋 8개, 마지막 2개 `bee8a9d6d9`, `337e4f5867`) |
| base / merge-base | `develop` `8e052e99c508141dbdd6dc338b65e437e31d756a` (merge-base와 같음) |
| head run | https://github.com/CUBRID/cubrid/actions/runs/45385469421 attempt 1 (`issue_comment`, 2026-11-24T11:34:47Z ~ 16:55:37Z) |
| base run | https://github.com/CUBRID/cubrid/actions/runs/45425193182 attempt 1 (`workflow_dispatch`, `dispatch all 8e052e99c5…`, 2026-11-24T15:24:42Z ~ 19:57:33Z; sql shard 01 build producer run `45367274144`) |
| 요청 suite | `test_medium`, `test_sql`, `test_shell`, `test_sql_by_cci` (head에 `gha-ci: test_sql_by_cci` status 있음) |
| 수집 / 검증 | head `collect` exit 4, `verify` exit 3; base `collect-base` exit 4, `verify` exit 3; `cubrid-ci 0.2.0 (00205d576de0, release)` |
| head observation | `pr-8514/337e4f5867fc524676a63f66dd11028bdebb9a83/observations/20261125T072403.224025797Z-2945664-0` |
| base observation | `commits/8e052e99c508141dbdd6dc338b65e437e31d756a/observations/20261125T073206.661741922Z-3533071-0` |
| verify / report_mode | identity `established`, observation `incomplete`, manifest `validated`, requested summaries `partial`, baseline `partial_exact` → `report_mode: warning` |
| testcase revision (head) | shell: `cubrid-testcases-private-ex` `69fd91f84bd814d1948eae38693603b47f5a5b84` (`tc/pr-8514`); sql: `cubrid-testcases` `8386e07a96119a2127ca752085d6d182e560d252` (`tc/pr-8514`, "[CBRD-28073] Sync tc/pr-8514 with develop") |
| testcase revision (base) | shell: `07af85a51694bbb11df2a04a5f76d9762b15c768` (`develop`); sql: `36ccc691414ebbcda7cf1c4b3912391957dbb7cc` (`develop`) |
| engine build provenance | head shard `build.sha=337e4f5867…` (debug, `run_id=45385469421`); base sql shard 01 `build.sha=8e052e99c5…` (debug, `run_id=45367274144`) |

### Suite 상태

| Suite | head CI 결과 | head 수집 상태 | head (tests/pass/fail/err/skip) | base run 45425193182 |
| --- | --- | --- | --- | --- |
| `test_medium` | `SUCCESS` | `completed` (`validated`) | 975 / 975 / 0 / 0 / 0 | `SUCCESS` / `validated` / 975 / 975 / 0 / 0 / 0 |
| `test_shell` | `FAILURE` | `completed` (`validated`) | 3684 / 3653 / 1 / 0 / 30 (`run=3654`) | `SUCCESS` / `validated` / 3683 / 3653 / 0 / 0 / 30 |
| `test_sql` | `FAILURE` | `collection_failed` (요약 없음) | raw: shard 01 `summary_info` 3557건 중 nok 7 (JUnit 3538건 중 failure 5); 다른 shard 실패 없음 | `SUCCESS` / `collection_failed` (raw shard 01 `summary_info` 3557/0, `failed.list` 0건) |
| `test_sql_by_cci` | `SUCCESS` | `completed` (`validated`) | 17882 / 17882 / 0 / 0 / 0 | `SUCCESS` / `validated` / 17882 / 17882 / 0 / 0 / 0 |

- `test_shell`의 head/base +1 차이는 TC PR [#4877](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4877)이 더한 `shell/_06_issues/_26_2h/cbrd_28073/cases/cbrd_28073.sh`다. 이번 head shard 28에서 통과했다(17.487 s). `cbrd_27780.sh`(CBRD-28257)도 통과했다(42.152 s).
- `TC Merge Gate / Check TC PRs`의 `FAILURE`(run [45385325626](https://github.com/CUBRID/cubrid/actions/runs/45385325626/job/138414631738))는 TC PR을 격리하려고 열어 둔 결과다. 회귀 실패가 아니다. 최종 병합 핸드오프에서 처리한다.

### 실패 목록

| # | Suite | Testcase | 결과 | 관찰 시그니처 | base 비교 | 분류 | PR 관련성 (확신) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `test_shell` | `shell/_06_issues/_12_2h/bug_bts_8907/cases/bug_bts_8907.sh` (shard 41) | failure | `bug_bts_8907-2 : NOK`; 재시작 구간에서 `cci_execute fail: -224`, 이어서 `cci_prepare fail: -224`만 반복, `-677` 뒤 `prepared` 없음 | `additional_on_head` (input 같음) | 간헐 타이밍 실패 (`cubrid-tcr`: `no_match`) | `unlikely` (높음) |
| 2 | `test_sql` | `sql/_05_plcsql/_01_testspec/_05_bug_fix/cbrd-27742/cases/cbrd_27742_02.sql` | nok (304390 ms) | case 6 `SELECT c, f5() FROM t2 …`에서 `Error:-21019`, 이후 `-677`; `core.1060` `pgbuf_timed_sleep` `page_buffer.c:8063` assert, `vacuum_heap_page` WRITE 대기 | `additional_on_head` (input 같음, base 635 ms 통과) | 엔진 page latch 교착 추정 (`cubrid-tcr`: `no_match`) | `unlikely` (중간) |
| 3 | `test_sql` | `sql/_05_plcsql/_01_testspec/_05_bug_fix/cbrd-27927/cases/cbrd_27927.sql` | nok | JDBC `Failed to connect to database server, 'basic'` (server 복구 중) | `additional_on_head` | #2의 결과 | `unlikely` (중간) |
| 4 | `test_sql` | `sql/_05_plcsql/_01_testspec/_06_authorization/cases/01_normal_grant_revoke.sql` | failure | `_db_stored_procedure`, `db_stored_procedure` 조회에 `dba.p1`–`p3`, `f4`, `f5` 행 추가 | `additional_on_head` | #2의 잔여 객체 | `unlikely` (중간) |
| 5 | `test_sql` | `sql/_05_plcsql/_01_testspec/_06_authorization/cases/07_permission_with_recursive.sql` | failure | 같은 잔여 procedure/function 행 추가 | `additional_on_head` | #2의 잔여 객체 | `unlikely` (중간) |
| 6 | `test_sql` | `sql/_05_plcsql/_01_testspec/_06_authorization/cases/12_db_stored_procedure_view_permission.sql` | failure | 같은 잔여 procedure/function 행 추가 | `additional_on_head` | #2의 잔여 객체 | `unlikely` (중간) |
| 7 | `test_sql` | `sql/_06_manipulation/_01_select/_001_inner_join/cases/1061.sql` | failure | `create class t2 …`에서 `Error:-494`, 이후 문장 연쇄 실패 | `additional_on_head` | #2의 잔여 `t2` | `unlikely` (중간) |
| 8 | `test_sql` | `sql/_06_manipulation/_01_select/_002_outer_join/cases/1009.sql` | failure | `create class t ( a int )`에서 `Error:-494`, 이후 문장 연쇄 실패 | `additional_on_head` | #2의 잔여 `t` | `unlikely` (중간) |

- **개수 정합성**: head 실패 8건 = `test_shell` 1(검증됨) + `test_sql` 7(raw, 미검증). `additional_on_head` 8, `also_observed_on_base` 0, `base_only` 0. `test_shell` 비교는 검증된 요약끼리 했다. `test_sql` 비교는 양쪽 raw `summary_info`로 했다. `test_sql`은 비교 범위 밖(`comparison_scope: none`)이므로 그 비교는 참고용이다.
- `test_sql` JUnit에는 5건만 있다. `cbrd_27742_02`와 `cbrd_27927`은 JUnit이 빼는 중첩 경로 `_05_bug_fix/cbrd-*/cases` 19건에 속한다. 그래서 collector와 Chronicle은 이 두 건을 보지 못한다.

### 원인 분석

#### 그룹 1: `bug_bts_8907.sh` — server 재시작 타이밍 (`test_shell`)

- **관찰.**
  - testcase(revision `69fd91f84b`)는 CCI 프로그램을 띄우고 10초 뒤 server를 내린 다음, 3초 뒤 다시 올리고 10초 기다린다. 그 뒤 `cci_prepare fail: -677` 다음 줄에 `prepared`가 1번 이상 있는지 본다.
  - 이번 결과에는 `-677`이 없다. 재시작 구간 전체에서 `-224`(`ER_OBJ_NO_CONNECT`, `src/base/error_code.h:298`)만 나왔다. 하위 항목 1, 3, 4, 5는 OK이고 core는 없다.
  - testcase는 `t1 (code int)` 하나만 쓴다. serial, AUTO_INCREMENT, OOS 열은 쓰지 않는다. private testcase 디렉터리는 head와 base에서 같다.
  - Chronicle: 통과 480번, 실패 5번(2026-11-16 ~ 17; PR #8416, #8561, #8513, #8489, PR 없는 run 1번). 이 PR의 이전 run 44522105929(2026-11-19)에서도 실패했다(위 절).
- **추론.** debug build의 server 재시작이 10초 관찰 구간을 넘으면 실패하는 간헐 타이밍 실패다. PR 관련성은 `unlikely`(확신 높음)이다.
- **모르는 것.** 이전 실패 5번의 NOK 내용은 Chronicle에 보관되지 않았다(`failed.list`, `test_status.data`만 있음). 그래서 증상이 같은지 비교하지 못했다.
- **반증 조건.** 같은 head에서 재실행할 때 계속 실패하고 base에서 계속 통과하면 이 판정은 틀리다.
- **다음 행동.** 재실행한다. 이번에 `cubrid-tcr` 텍스트 시그니처 `bug_bts_8907-reconnect-window-224`(`cci_prepare fail: -224`)를 추가했다.

#### 그룹 2: `cbrd_27742_02.sql` 중 `cub_server` page latch 300초 대기 assert와 연쇄 실패 (`test_sql` 7건)

- **관찰 (CI job log, `ctp_log.tgz`의 `cbrd_27742_02.err`).**
  - 16:14:51Z에 `cbrd_27742_02.sql`이 시작했다. 16:19:52Z에 `cub_server: …/page_buffer.c:8063: int pgbuf_timed_sleep(THREAD_ENTRY*, PGBUF_BCB*): Assertion '0' failed.`가 나왔다. core는 `/home/CUBRID/databases/basic/core.1060`이다.
  - 죽은 thread 스택: `vacuum_process_log_block` → `vacuum_heap` → `vacuum_heap_page` → `pgbuf_fix_debug(…, PGBUF_LATCH_WRITE, PGBUF_UNCONDITIONAL_LATCH, caller vacuum.c:1769)` → `pgbuf_latch_bcb_upon_fix` → `pgbuf_block_bcb` → `pgbuf_timed_sleep`(`wait_msecs = 300000`).
  - 대기 당시 BCB 상태는 `old_impl = {latch_mode = PGBUF_LATCH_READ, waiter_exists = 0, fcnt = 1}`이다. 다른 thread 하나가 이 heap page를 READ로 잡고 있었다. core 분석기는 죽은 thread만 출력하므로 holder thread는 알 수 없다.
  - `.result`와 `.answer` 비교: case 5까지는 같다. case 6 `SELECT c, f5() FROM t2 WHERE c < 3 ORDER BY c;`가 `Error:-21019`(broker 통신 실패)이고, 그 뒤 모든 문장이 `-677`이다. `f5`의 본문은 `SELECT COUNT(*) INTO n FROM (SELECT c AS x FROM t2 GROUP BY c) z`이다. 바깥 `t2` scan의 각 행에서 PL/CSQL 함수가 다시 `t2`를 scan한다.
  - 다음 testcase에서 남은 객체가 보였다. `_06_authorization` 3건에는 `dba.p1`, `p2`, `p3`, `f4`, `f5`가 나왔다. `f7` 이후 객체는 없다. 이는 case 6에서 멈췄다는 사실과 맞는다. `1061`은 `t2`, `1009`는 `t`를 만들 때 `-494`로 실패했다. 이 객체들은 모두 `cbrd_27742_02.sql` 앞부분에서 만들고 끝의 `DROP`이 지운다.
  - `cbrd_27927.sql`(16:19:55Z)은 server 복구 중 JDBC 연결에 실패했다.
  - [`page_buffer.c:7050-7072`](https://github.com/CUBRID/cubrid/blob/337e4f5867fc524676a63f66dd11028bdebb9a83/src/storage/page_buffer.c#L7050-L7072) (`337e4f5867`): READ latch가 걸린 page에 대기자가 있으면, holder가 아닌 thread의 새 READ 요청은 block된다. [`page_buffer.c:8060-8063`](https://github.com/CUBRID/cubrid/blob/337e4f5867fc524676a63f66dd11028bdebb9a83/src/storage/page_buffer.c#L8060-L8063): 무한 대기 요청이 시간 초과되면 debug build에서 `assert (0)`이 실행된다.
  - PR diff(`8e052e99c5..337e4f5867`)는 `src/query/serial.c`의 3개 호출을 `heap_attrinfo_transform_to_disk_keep_form`으로 바꾸고 `src/storage/heap_file.c`/`.h`에 `keep_form` 경로를 더한다. 나머지는 `unit_tests/oos/`이다. `keep_form=false`(일반 user heap)의 동작, `page_buffer.c`, `vacuum.c`, heap scan, PL 실행 경로는 바뀌지 않는다. `cbrd_27742_02.sql`에는 serial, AUTO_INCREMENT, `NEXT_VALUE`가 없다.
  - `cbrd_27742`(CBRD-27742, `ad7a255c55`)와 `cbrd_27927`(CBRD-27927, `b7987f91fa`)의 엔진 수정은 base와 head에 모두 있다.
- **추론.**
  - case 6에서 바깥 scan이 `t2` heap page를 READ로 잡은 채 `f5()`를 호출하고, `f5`의 중첩 scan이 다른 server thread에서 같은 page에 READ를 요청할 수 있다. 그 사이 vacuum이 WRITE 대기자로 들어오면 중첩 READ는 대기자 뒤에서 block된다. 그러면 바깥 scan은 `f5`를, `f5`는 vacuum을, vacuum은 바깥 scan을 기다리는 3자 교착이 된다. 300초 뒤 vacuum 쪽 `assert (0)`이 server를 죽인다. 이 메커니즘은 BCB 상태, 멈춘 위치, 대기 규칙과 맞는다. 하지만 holder 스택이 없으므로 가설이다. vacuum이 그 page에 도착하는 시점에 따라 나므로 드물게 나타난다(로컬 보관 번들 39개 중 1번).
  - 7건은 하나의 엔진 사건이고 PR의 serial 행 인코딩 변경과 관계가 없다. PR 관련성은 `unlikely`(확신 중간)이다. 확신이 중간인 이유는 head에서만 1번 관찰되었고 holder를 확인하지 못했기 때문이다.
- **모르는 것.** READ holder thread의 스택. 중첩 PL/CSQL 질의가 같은 server thread에서 실행되는지 다른 thread에서 실행되는지(같은 thread이면 holder 예외로 READ가 허용되므로 위 가설은 틀리다). develop에서의 발생 빈도(Chronicle은 중첩 경로를 인덱싱하지 않는다).
- **반증 조건.** `core.1060`의 전체 thread 스택(`thread apply all bt`)에서 holder가 `f5`를 기다리는 바깥 scan이 아니면 교착 가설은 틀리다. 같은 head에서 재실행할 때 `cbrd_27742_02`가 반복해서 실패하고 base에서는 통과하면 PR 관련성 판정을 다시 해야 한다.
- **다음 행동.** (1) `/run rerun 45385469421`로 실패 job을 재실행한다. (2) 재실행과 별도로, PR과 관계없는 엔진 버그 후보로 추적한다. `cubrid-jira-dup` 후보는 [CBRD-27591](https://jira.cubrid.org/browse/CBRD-27591)(Resolved, "[PL/CSQL] DML on the page being scanned by the calling SELECT waits on its own page latch"), [CBRD-27723](https://jira.cubrid.org/browse/CBRD-27723)(Resolved, parallel heap scan과 vacuum 교착), [CBRD-27062](https://jira.cubrid.org/browse/CBRD-27062)(Tested, 탐지되지 않는 page latch 교착)이다. 셋 모두 같은 증상(SELECT 중 PL/CSQL 호출 + vacuum WRITE 대기)을 다루지는 않는다. 확정된 중복은 없다. 로컬 재현(debug build에서 `cbrd_27742_02.sql` 반복 실행 + vacuum 강제)으로 holder를 잡은 뒤 이슈를 작성한다.

### Base 비교

- **Pinned identities**: head `337e4f5867fc524676a63f66dd11028bdebb9a83`, target `develop` tip(수집 시점) `8e052e99c508141dbdd6dc338b65e437e31d756a`, exact merge-base `8e052e99c508141dbdd6dc338b65e437e31d756a`(일치), `observed_at 2026-11-25T07:29:27Z`.
- **Selected runs**: head `45385469421` attempt 1 vs base `45425193182` attempt 1.
- **TC revision 대조**:
  - public `cubrid-testcases`: head `8386e07a96` vs base `36ccc69141`. `git diff`의 `sql/` 차이는 0이다. 실패한 7개 SQL 파일과 answer는 같다.
  - private `cubrid-testcases-private-ex`: head `69fd91f84b` vs base `07af85a516`. 차이는 `cbrd_28073.sh`(+173줄) 1건이다. `bug_bts_8907` 디렉터리는 같다.
- **설정과 한계**: 양쪽 모두 `test_shell`/`test_sql`은 debug, `test_sql_by_cci`는 release이다. 각 1번 실행했다. `test_sql`은 양쪽 `collection_failed`이어서 raw로만 대조했다. 동일 input에서 head만 실패했지만 단일 실행이므로 회귀를 증명하지 않는다.

### 수집 기록과 진단

- **Acquisition ledger**: head와 base 모두 `test_medium` 1/1, `test_shell` 50/50, `test_sql` 10/10, `test_sql_by_cci` 10/10 shard가 `retained`이다(`failed` 0, `not_attempted` 0).
- **Binary budget**: 양쪽 `configured_bytes: 536870912`, `consumed_bytes: 0`.
- **`test_sql` 진단**: head는 `summary_info 3550/7/0` 대 `JUnit 3533/5/0`, base는 `3557/0/0` 대 `3538/0/0`이다. 양쪽 모두 `_05_bug_fix/cbrd-*/cases` 19건이 JUnit에서 빠진 기존 문제다. 이번에는 빠진 19건에 실패 2건(`cbrd_27742_02`, `cbrd_27927`)이 들어 있어 JUnit 실패 수(5)와 CI가 보고한 실패 수(7)가 다르다.
- **추가 근거 수집(읽기 전용)**: `gh api repos/CUBRID/cubrid/actions/jobs/138418185466/logs`(sql shard 01 job log), `http://192.168.1.48:30080/runs/45385469421/sql/shard/01/artifacts/ctp_log.tgz`(`cbrd_27742_02.err/.result/.answer`).

### Testcase 이력

- 도구 버전: `cubrid-tcc 0.3.0`, `cubrid-tcr 0.1.0`.
- `cubrid-tcc sync-data --run 45385469421 --suite test_shell|test_sql --revisit-limit 0 --json`: 둘 다 `inserted_snapshots: 0`, `observations: 0`, `unavailable_files: 3`, `missing_remaining: 2985`이다. 이번 run은 인덱싱되지 않았다. `--missing` 갭(2985 run)은 사용자 유지보수 항목으로 남긴다.
- `bug_bts_8907.sh`: `SEEN_BEFORE`, 실패 5번 / 통과 480번(위 그룹 1). 실패 execution: 38602(run 43831255516, PR #8416, engine `fba87586b8`), 37132(run 43897556424, PR 없음, `4b73a5f832`), 36243(run 43999554179, PR #8561, `2d42421a8f`), 35649(run 44013281521, PR #8513, `185118dde4`), 35530(run 44017820660, PR #8489, `3fe5c5c662`). engine과 testcase revision이 서로 달라 같은 revision의 PASS/FAIL 비교로 flakiness를 확정하지는 못한다. `cubrid-tcr check`: `no_match`; `--record`는 run 미인덱싱으로 `no_occurrence`이다.
- `1009.sql`, `1061.sql`, `07_…recursive.sql`, `12_…permission.sql`: `UNKNOWN_HISTORY`(`target_failure_not_indexed`), 기존 기록은 모두 PASS(188~190번).
- `01_normal_grant_revoke.sql`: `UNKNOWN_HISTORY`, 기존 FAIL 1번(run 38687274058, PR #7157, 2026-10-15)과 PASS 189번. 이번 증상은 잔여 객체 때문이므로 그 FAIL과 비교하지 않았다.
- `cbrd_27742_02.sql`, `cbrd_27927.sql`: `UNKNOWN_HISTORY`(`not_indexed`, 기록 0번). JUnit이 빼는 중첩 경로라서 Chronicle이 보지 못한다. 대신 로컬 `cubrid-ci` 데이터에서 `summary_info`를 찾았다. `cbrd_27742_02.sql:ok`는 38개 번들, `:nok`는 이번 1개 번들이다.
- `cubrid-tcr` 기록: `bug_bts_8907` 시그니처 추가, `cbrd_27742_02` note 추가(run 45385469421 근거). 둘 다 판정을 바꾸지 않는다.

### 모르는 것

- `core.1060`의 READ holder thread와 전체 thread 스택(아티팩트에는 core 분석 텍스트만 있다).
- 재실행에서 두 suite가 통과하는지.
- develop에서 `cbrd_27742_02` 교착의 발생 빈도.

### 다음 행동

1. **`/run rerun 45385469421`** (실패한 `test_shell`·`test_sql` job만 재실행; 사용자 승인 후 `cubrid-ci-trigger`로 진행). 두 실패 모두 PR 코드나 TC 수정이 필요 없다.
2. 재실행에서 `cbrd_27742_02`가 다시 같은 assert로 실패하면 head와 base로 로컬 반복 실행(`cubrid-test-sql-run`)해 PR 관련성을 다시 판정한다.
3. PR과 별개로: `cbrd_27742_02` page latch 교착을 엔진 버그 후보로 재현하고 holder 스택을 확보한 다음 JIRA 이슈를 작성한다(중복 후보 CBRD-27591, CBRD-27723, CBRD-27062 확인).
4. `TC Merge Gate`는 TC PR 격리 결과이다. 최종 병합 핸드오프에서 처리한다.

### 근거 파일 (2026-11-25, head `337e4f5867`)

- head observation: `cubrid-ci` 데이터 디렉터리의 `github-actions/CUBRID-cubrid/pr-8514/337e4f5867fc524676a63f66dd11028bdebb9a83/observations/20261125T072403.224025797Z-2945664-0/result.json`
- head 검증 요약: 같은 head 디렉터리의 `providers/github-actions/runs/45385469421/attempts/1/{test_medium,test_shell,test_sql_by_cci}/summary.json`
- `bug_bts_8907` 실패 상세: 같은 run 디렉터리의 `test_shell/failures/shell_06_issues_12_2h_bug_bts_8907_cases_bug_bts_8907_sh-0e7a776ddd/`
- `test_sql` raw: 같은 run 디렉터리의 `test_sql/raw/collect/failed.list`, `test_sql/raw/shards/01/{summary_info,linux_sql_64bit_optdebug.xml,build.read,tc.read}`
- `cbrd_27742_02` core 분석과 결과: 아티팩트 서버 `runs/45385469421/sql/shard/01/artifacts/ctp_log.tgz` 안의 `result/y2026/m11/schedule_linux_sql_64bit_2501095798_11.5.0.3046-337e4f5/sql/_05_plcsql/_01_testspec/_05_bug_fix/cbrd-27742/cbrd_27742_02.{err,result,answer}`
- sql shard 01 job log: job `138418185466` (`gh api …/actions/jobs/138418185466/logs`)
- base observation과 요약: `cubrid-ci` 데이터 디렉터리의 `github-actions/CUBRID-cubrid/commits/8e052e99c508141dbdd6dc338b65e437e31d756a/observations/20261125T073206.661741922Z-3533071-0/result.json`과 `providers/github-actions/runs/45425193182/attempts/1/`
