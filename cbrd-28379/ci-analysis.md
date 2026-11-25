# CBRD-28379 CI 분석: PR #8753, run 45615415274 (경고 보고서)

> **이 스냅샷은 회귀 판단이나 근본 원인 결론을 뒷받침하지 않습니다.** 판정 규칙(`report_mode.py`)이 `mode: warning`을 반환했습니다. `test_sql` 수집이 무결성 오류로 실패했고, merge-base baseline은 아직 실행 중이라 비교할 수 없습니다. 아래의 "PR과 무관" 판단은 검증된 CI 비교가 아니라, 같은 testcase가 이 PR 변경이 없는 다른 실행에서도 실패한 관찰과 이전 bisect에 근거한 추론입니다.

- PR: [CUBRID/cubrid#8753](https://github.com/CUBRID/cubrid/pull/8753) `[CBRD-28379] Fix refused conditional latch leaving waiter_exists set`
- 엔진 head: `5c213aaac66549e92f805d2ed643c8fbdbc57939` (base `develop`, merge base `ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e`)
- Run: [45615415274](https://github.com/CUBRID/cubrid/actions/runs/45615415274) attempt 1, `/run all`, 2026-11-25T12:36:37Z 트리거, 2026-11-25T18:00:25Z 완료
- 관찰 시각: 2026-11-25T18:42Z (UTC), collector `cubrid-ci 0.2.0 (00205d576de0, release)`

## 요약

| Suite | CI 결과 | 수집 상태 | 검증된 수치 | 실패 testcase |
| --- | --- | --- | --- | --- |
| `build (release)`, `build (debug)` | SUCCESS | — | — | — |
| `test_medium` | SUCCESS | `validated` | 975 / 975 통과 | 없음 |
| `test_shell` | FAILURE | `validated` | 3704 중 3672 통과, 2 실패, 30 skip | `cbrd_27744_sa`, `cbrd_28117` |
| `test_sql` | FAILURE | `collection_failed` (무결성) | 없음 | shard 09 로그: `cbrd_26795`, `cbrd_27748`, `cbrd_28121` (검증 안 됨) |
| `test_sql_by_cci` (선택) | FAILURE | `validated` | 17909 중 17906 통과, 3 실패 | `cbrd_26795`, `cbrd_27748`, `cbrd_28121` |

- 실패 5종(서로 다른 testcase)은 모두 이 PR 변경(`src/storage/page_buffer.c`의 latch/unfix 경로)이 없는 다른 실행에서도 같은 testcase로 실패했습니다(아래 "다른 실행에서의 관찰"). PR 관계는 모두 `unlikely`로 봅니다. 단, 위 경고에 따라 이는 추론입니다.
- TC Merge Gate: `Check TC PRs`가 FAILURE입니다. TC PR [cubrid-testcases#4462](https://github.com/CUBRID/cubrid-testcases/pull/4462), [cubrid-testcases-private-ex#5163](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5163)이 열려 있어서이며, 회귀 실패와 별개입니다. 이 변경은 TC 수정이 필요 없고, 두 TC PR은 최종 병합 handoff까지 열어 둡니다.
- 다음 조치: develop 회귀(`cbrd_27744_sa`)와 SQL answer 불일치가 develop에서 해결되고 CBRD-28117 엔진 커밋이 들어간 develop으로 rebase한 뒤 CI를 다시 실행합니다. 재실행은 사람의 지시가 필요합니다.

## 증거 범위와 제한

- 증거 디렉터리: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8753/5c213aaac66549e92f805d2ed643c8fbdbc57939` (로컬 collector 소유, 이 저장소에 넣지 않음)
- `cubrid-ci verify` 평가: `identity: established`, `observation: incomplete`, `manifest: validated`, `requested_summaries: partial`.
- TC revision: `test_shell`은 `cubrid-testcases-private-ex` `0ff7ca104008556a395a641fd8188d9a80216e3f` (`tc/pr-8753`), `test_sql_by_cci`는 `cubrid-testcases` `82d6dcf3e776aa132a62cdbe3570c1c3ed9c47c2` (`tc/pr-8753`).
- `test_sql` 무결성 오류: 같은 head에 대한 첫 관찰(`20261125T184132.610379427Z-1231156-0`, 이 세션이 시작하지 않은 수집)에서 "shard 01 JUnit omits 19 testcases that summary_info reports (summary_info 3557/0/0, JUnit 3538/0/0)"로 실패했습니다. 누락된 19건은 `sql/_05_plcsql/...` testcase입니다. 이어진 이 분석의 수집(`20261125T184232.052927026Z-1331724-0`)은 이미 저장된 `test_sql/raw/github/collect.log`와 내용이 달라 "immutable evidence already exists with different content"로 실패했습니다. 같은 shard 01 JUnit 누락은 CBRD-28271 분석의 두 run에서도 반복되었습니다([cbrd-28271/ci-analysis.md](../cbrd-28271/ci-analysis.md)). 무결성 오류는 우회하지 않았습니다.
- `test_sql` 실패 이름은 GitHub job 로그(`sql / shard sql 09`, job 139211658827)의 `[NOK]` 줄에서 읽은 것으로, 검증되지 않은 원시 증거입니다.
- 환경: 이 호스트의 `PATH`에 `~/my-cubrid/bin`(`cubrid-pr-status`)이 없어 `cubrid-ci`를 처음에 실행하지 못했습니다. 분석 명령에만 `PATH`를 덧붙였습니다.

## 실패 목록

| Suite | Testcase | 관찰된 증상 | Baseline 분류 | PR 관계 / 신뢰도 |
| --- | --- | --- | --- | --- |
| `test_shell` | `shell/_06_issues/_26_2h/cbrd_27744_sa/cases/cbrd_27744_sa.sh` (shard 16) | 13: `sa_crash serial after recovery: expected '140001 2147483647 1', got '1 2147483647 1'`; 14: `sa_crash ids: expected '1 210001', got '1 70001'` | `uncomparable` | `unlikely` / 높음 |
| `test_shell` | `shell/_06_issues/_26_2h/cbrd_28117/cases/cbrd_28117.sh` (shard 44) | 5: `single session: threads at 5 checks: 67 67 67 67 67 (2 to 8 expected), queries 2686 -> 3771` | `uncomparable` | `unlikely` / 높음 |
| `test_sql_by_cci` | `sql/_36_guava/cbrd_26795/cases/cbrd_26795.sql` (shard 09) | `show trace`의 `SCAN (table: dba.px_wide_t)` 줄 끝에 `(oos time: ?, fetch: ?, ioread: ?)`가 추가됨 | `uncomparable` | `unlikely` / 중간 |
| `test_sql_by_cci` | `sql/_36_guava/cbrd_27748/cases/cbrd_27748.sql` (shard 09) | outer가 `temp(sort limit)` 대신 `iscan`, `/* ---> skip ORDER BY */` 추가 | `uncomparable` | `unlikely` / 중간 |
| `test_sql_by_cci` | `sql/_36_guava/cbrd_28121/cases/cbrd_28121.sql` (shard 09) | `skip order by: true` 줄이 빠짐 | `uncomparable` | `unlikely` / 중간 |

수치 대조: 검증된 실패 5건(shell 2, sql_by_cci 3)이 위 표에 한 번씩 있습니다. `test_sql`의 3건은 검증되지 않아 수치에 넣지 않았고, 이름은 `test_sql_by_cci`의 3건과 같습니다. 공유·추가·base-only 수는 baseline이 없어 0/0/0이 아니라 "비교 불가"입니다.

`cubrid-tcr check`(offline): 5건 모두 `no_match`. `cubrid-common`의 Known CI issues 목록에도 해당 항목이 없습니다.

## 원인별 관찰과 추론

### 1. `cbrd_27744_sa`: develop 회귀 (이전 bisect)

- 관찰: CBRD-28271 분석에서 로컬 bisect로 첫 bad commit을 `e74826c46c` "[CBRD-27562] Do not start a system operation for temporary sector reservation or temporary volume growth (#8537)"로 찾았습니다. CBRD-28271 PR 변경이 없는 develop `a5ab407`에서도 같은 13, 14 NOK 값이 나왔습니다([cbrd-28271/ci-analysis.md](../cbrd-28271/ci-analysis.md)의 "`cbrd_27744_sa` 재현과 bisect").
- 관찰: `e74826c46c`는 이 PR head의 조상입니다. 이번 실패 값은 bisect 기록과 같습니다.
- 관찰: 이 PR 변경이 없는 다른 PR 실행에서도 같은 testcase가 실패했습니다(아래 표).
- 추론: 이 PR과 무관한 develop 회귀입니다. 이 PR의 변경 중 waiter_exists 부분은 조건부 latch 거절에만, unfix 보정은 `SERVER_MODE`에만 영향을 주며, 이 시나리오는 `csql -S`(SA 모드)입니다.
- 반증 조건: 이 PR head에서 `page_buffer.c` 변경만 되돌린 빌드가 13, 14를 통과하면 틀립니다.
- 조치: CBRD-27562 쪽 develop 회귀를 JIRA로 올리는 일은 CBRD-28271 분석의 조치 1로 이미 남아 있습니다. 사람의 결정이 필요합니다. `cubrid-jira-dup` 검색에서는 일치 이슈가 없었습니다(상위 후보 CBRD-28052, CBRD-28073은 OOS serial 저장 형태 문제).

### 2. `cbrd_28117`: TC가 이 PR base보다 새 엔진 커밋을 요구함

- 관찰: testcase는 TC `5136a30b3` "[CBRD-28117] Add a shell TC: idle parallel-query threads end after a burst (#4935)"로 들어왔습니다. 짝이 되는 엔진 커밋 `14b75ea4cf` "[CBRD-28117] Take the most recently returned worker first in the basic worker pool (#8560)"은 develop의 merge base 다음 커밋이며 이 PR head에 **없습니다**.
- 관찰: 증상(유휴 thread 수가 67에서 줄지 않음)은 그 엔진 수정이 다루는 동작입니다. PR #8754(CBRD-28378)의 실행에서도 같은 testcase가 실패했습니다.
- 추론: TC/엔진 시차입니다. develop로 rebase하면 해결될 것으로 봅니다.
- 반증 조건: `14b75ea4cf`를 포함한 develop에서도 같은 NOK가 나면 틀립니다.

### 3. SQL 3건(`cbrd_26795`, `cbrd_27748`, `cbrd_28121`): develop에서도 실패

- 관찰: 세 testcase의 엔진 커밋(`47fcc321f6`, `30eb0c4b8b`, `186674424f`)은 모두 이 PR head에 들어 있습니다. 차이는 optimizer의 ORDER BY skip 판단과 scan trace의 OOS 통계 출력에서 나오며, 페이지 버퍼와 관련이 없습니다.
- 관찰: develop tip `14b75ea4cf`의 dispatch run [45644773022](https://github.com/CUBRID/cubrid/actions/runs/45644773022)(아직 shell 진행 중)의 `sql`, `sql_by_cci` 실패 목록이 정확히 같은 3건입니다(CI 산출물 서버의 `collect/failed.list`, 검증되지 않음). CBRD-28271 분석의 run에서도 같은 증상이었습니다.
- 추론: develop의 answer와 엔진 출력이 어긋난 상태이며 이 PR과 무관합니다.
- 반증 조건: develop tip run의 검증된 결과에서 세 testcase가 통과하면 틀립니다.
- JIRA 중복 확인: 일치 이슈 없음(상위 후보 CBRD-27314, CBRD-28121, CBRD-27748은 해결된 원 이슈).

## 다른 실행에서의 관찰 (검증되지 않은 원시 증거)

최근 완료된 `gha-ci` run 19개 중, CI 산출물 서버에서 `collect/failed.list`를 읽을 수 있었던 run입니다. 모두 이 PR 변경이 없는 다른 PR head를 테스트했습니다.

| Run | PR | `test_shell` 실패 | `test_sql` 실패 |
| --- | --- | --- | --- |
| 45617357842 | #8754 (CBRD-28378) | `cbrd_27744_sa`, `cbrd_27780`, `cbrd_28117` | 같은 SQL 3건 |
| 45637749074 | #8686 (CBRD-28289) | `cbrd_27744_sa` | 같은 SQL 3건 |
| 45624045146 | #8693 (CBRD-28257) | `cbrd_27744_sa` | 없음 |
| 45617650171 | #8534 (CBRD-27966) | `bug_bts_17534`, `cbrd_27780` | 없음 |
| 45639775540, 45639549970 | #8702, #8532 | 없음 | 없음 |

`cbrd_27744_sa`가 일부 PR에서만 실패하는 것은 각 PR의 base가 `e74826c46c`와 CBRD-27744 엔진/TC를 모두 포함하는지에 따라 다를 수 있습니다. 확인하지 않았습니다.

## Baseline 비교

- Target `develop` `14b75ea4cf4952cfadde5d0fca884be6d4242391`, merge base `ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e`, 관찰 2026-11-25T18:43:17Z.
- `collect-base` 결과: 4개 suite 모두 `running`, `baseline: unavailable`. merge base의 dispatch run [45644779630](https://github.com/CUBRID/cubrid/actions/runs/45644779630)은 관찰 시점에 queued 상태였습니다.
- 정확한 merge-base 비교는 할 수 없습니다. 위 "다른 실행" 표는 그 대체가 아닙니다.

## Testcase 이력

`cubrid-tcc history`: 5건 모두 이전 실패 0건, `not_indexed`(`cbrd_26795`는 `target_failure_not_indexed`). 인덱스가 2026-10-14 이후 일부만 덮어, 이력이 없다는 것이 처음 실패라는 뜻은 아닙니다. flakiness 근거도 없습니다.

## 조치

1. CI를 다시 돌리기 전에, develop이 `cbrd_27744_sa` 회귀와 SQL 3건을 해결했는지 확인합니다. develop tip run 45644773022와 merge base run 45644779630이 끝나면 결과를 봅니다.
2. 그 뒤 PR 브랜치를 develop으로 rebase하고(`cbrd_28117`의 엔진 커밋 포함) `/run all`을 한 번 실행합니다. rebase, push, 재실행 모두 사람의 지시가 필요합니다.
3. `test_sql` 수집 무결성 오류(shard 01 JUnit 19건 누락)는 세 번째로 반복되었습니다. collector 또는 CI 산출물 문제로 따로 다룹니다.
4. 이 호스트의 `PATH`에 `~/my-cubrid/bin`을 넣어 `cubrid-ci`, `cubrid-pr-status`가 바로 실행되게 합니다.
