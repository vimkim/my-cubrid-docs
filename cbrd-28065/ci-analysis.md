# CBRD-28065 CI 분석: PR #8642 gha-ci run 44496524091

## Summary

- 결과: run 44496524091 (attempt 1)은 `failure` 로 끝났다. 실패는 `test_shell` 의 testcase 하나, `shell/_06_issues/_26_2h/cbrd_27217/cases/cbrd_27217.sh` 의 판정 12개 중 1개(판정 8)다. `test_medium`, `test_sql`, `test_sql_by_cci`, 두 빌드는 GitHub 상태가 SUCCESS다.
- 이 PR과의 관계: `unlikely`, 신뢰도 중상. 실패한 판정은 읽기 전용 SELECT 반복의 결과 행 비교이고, 읽기 전용 트랜잭션은 커밋 레코드를 쓰지 않아 이번 변경(`logpb_flush_pages()` 의 대기 조건)을 지나지 않는다. 같은 모양의 실패가 이 변경이 없는 develop 엔진 `2d925cb868` 에서도 있었다(2026-10-27).
- 한계: merge-base 기준선이 없어서(`1ecb2e7f37` 의 gha-ci 결과 없음) 회귀 여부를 결론 내릴 수 없다. 4개 suite 범위의 수집은 `test_sql` 의 수집기 무결성 오류로 불완전해 경고 수준만 허용되었다. 그래서 실패가 있는 `test_shell` 만 다시 수집해 검증된 증거로 분석했다. 실패한 20번째 실행이 무엇을 출력했는지는 CI 증거에 남아 있지 않다.
- 이 PR이 더한 shell TC `cbrd_28065` 는 CI pod에서 통과했다(shard 14, 16.8초).
- 다음 행동: 운영자가 `/run rerun 44496524091` 로 실패한 shell 케이스를 다시 돌릴지 정한다. 다시 돌려 통과하면 실패가 이 PR과 무관하다는 근거가 하나 더 생긴다. 같은 판정이 다시 실패하면 아래 반증 조건에 따라 원인을 다시 본다.

## CI snapshot

| Suite | GitHub 상태 | run / attempt | 수집 상태 | 판정 수 |
| --- | --- | --- | --- | --- |
| `build (release)`, `build (debug)` | SUCCESS | 44496524091 / 1 | 해당 없음 | - |
| `test_medium` | SUCCESS | 44496524091 / 1 | validated (4-suite 수집) | 실패 0 |
| `test_sql` | SUCCESS | 44496524091 / 1 | `collection_failed` (아래 참고) | 판정 읽지 않음 |
| `test_sql_by_cci` | SUCCESS | 44496524091 / 1 | validated (4-suite 수집) | 실패 0 |
| `test_shell` | FAILURE | 44496524091 / 1 | validated (shell 단독 수집, `report_mode` = full) | tests 3655, passed 3624, failures 1, errors 0, skipped 30 |

- `test_sql` 수집 실패: shard 01의 JUnit 파일이 summary_info가 센 19개 PL/CSQL testcase(`sql/_05_plcsql/...`)를 빠뜨렸다(summary_info 3557/0/0, JUnit 3538/0/0 passed/failed/skipped). 수집기의 identity 검사가 이를 무결성 오류로 처리했다. GitHub 상태는 SUCCESS이고 실패 수는 양쪽 모두 0이지만, 이 분석은 `test_sql` 판정을 검증된 증거로 쓰지 않았다.
- `TC Merge Gate / Check TC PRs` FAILURE는 TC PR(#5028, #4340)이 열려 있어서 생기는 격리 게이트다. 회귀 실패가 아니며 엔진 병합 직전 handoff에서 처리한다.

## Evidence scope

- PR: https://github.com/CUBRID/cubrid/pull/8642, head `9cc4cf8302a857c65a2d93cfde69300a02e586e7`. 모든 shell shard의 엔진 `build.sha` 와 같다.
- testcase: `cubrid-testcases-private-ex` `eef8e0754edef6456497aef2303b79e4872f20cd` (`tc/pr-8642`), 모든 shard 같음.
- 수집기: `cubrid-ci 0.2.0 (00205d576de0, release)`. 4-suite 수집 2026-11-19 11:21Z (exit 4, verify exit 3, `report_mode` warning). `test_shell` 단독 수집(exit 0, verify exit 0, `report_mode` full, `comparison_scope` none).
- 증거 디렉터리: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8642/9cc4cf8302a857c65a2d93cfde69300a02e586e7/providers/github-actions/runs/44496524091/attempts/1/test_shell/` (`summary.json`, `failures/shell_06_issues_26_2h_cbrd_27217_cases_cbrd_27217_sh-d15ad5393f/`).
- 한계: `loop_part.log` 는 CI 산출물에 없어서 다른 출력의 내용을 모른다. Chronicle 동기화(`cubrid-tcc 0.3.0`)는 이 run에서 `unavailable_files: 1`, 관측 0건이었다.

## Failure inventory

| Suite | Testcase | 결과 | 관측된 증상 | 기준선 분류 | 분류 | PR 관계 | 신뢰도 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `test_shell` | `shell/_06_issues/_26_2h/cbrd_27217/cases/cbrd_27217.sh` (shard 03) | failure, 판정 12개 중 8번 NOK | `partitioned_table_no_list_file_growth : trace: workers '3' gather 'row by row' (expected 2+ 'row by row'), 19 of 20 executions printed the expected line, list_file.c bytes grew by 0, 4 of 4 partitions in the trace` | `uncomparable` (기준선 없음) | 간헐적 결과 행 누락으로 보임(추론) | `unlikely` | 중상 |

head 실패 1, 기준선과 공유 0, head에만 0, 비교 불가 1, base에만 0.

`cubrid-tcr check`: `no_match` (규칙 없음). 이력 수치: 실패 1, 통과 446.

## Root cause analysis

### cbrd_27217 판정 8: 20번 반복 중 1번이 기대한 결과 행을 출력하지 않음

- 관측:
  - `loop_verdict part` 는 `select count(*), sum(id) from pt where v = 7 and rownum <= 1000;` 을 trace로 한 번, 예열 5번, 측정 20번 실행한다(`eef8e0754` 의 `cbrd_27217.sh` 165~214, 323~329줄).
  - trace 조건은 맞았다(parallel workers 3, gather "row by row", 4개 파티션 모두 trace에 나옴). `list_file.c` 메모리도 72000바이트 그대로였다. 실패 조건은 `matched=19`, 곧 20번 중 1번의 출력이 `^[[:space:]]*200[[:space:]]+19901400[[:space:]]*$` 와 맞지 않은 것이다.
  - 이 반복은 `csql -i` 의 autocommit 읽기 전용 SELECT다.
  - Chronicle에 같은 testcase의 이전 실패 1건이 있다. run 40532265994, shard 11, 엔진 `2d925cb868` (develop 이력, 이 PR 없음), testcase `a4e12efc7e`, 2026-10-27. 증상은 판정 9 `parallel_2_no_list_file_growth : trace: workers '2' gather 'row by row' (expected 2 'row by row'), 19 of 20 executions printed the expected line, list_file.c bytes grew by 0` 이다.
- 추론:
  - 이번 변경은 `logpb_flush_pages()` 의 대기 조건만 바꾼다. 이 함수는 커밋·체크포인트 중 abort·2PC·HA 서버 상태 레코드를 붙인 트랜잭션만 부른다. 로그 레코드가 없는 읽기 전용 트랜잭션의 커밋은 커밋 레코드를 쓰지 않으므로 이 경로를 지나지 않는다. 그래서 이 SELECT 반복의 결과에 영향을 줄 수 없다.
  - 이 PR이 없는 develop 엔진에서 같은 검사(병렬 행 단위 gather 반복에서 20번 중 1번 결과 행 누락)가 실패한 적이 있다. 병렬 스캔이나 테스트의 출력 비교가 간헐적으로 다른 결과를 내는 것으로 보인다.
- 모르는 것: 20번째 실행이 오류였는지, 다른 값을 냈는지, 출력 형식이 달랐는지. 같은 엔진과 testcase 리비전에서 통과와 실패가 함께 관측된 적은 없어서, flaky라고 확정할 근거는 없다.
- 반증 조건: 같은 head로 다시 돌렸을 때 판정 8이 반복해서 실패하고, 같은 testcase 리비전의 develop(이 변경 없음)에서는 실패하지 않으면 이 PR과의 관련을 다시 본다. 20번째 실행의 출력이 커밋 대기나 로그 flush와 관련된 오류(예: 시간 초과)로 확인되어도 다시 본다.
- 다음 행동: 실패한 shell 케이스 재실행(`/run rerun 44496524091`)은 운영자가 정한다. 원인 확인이 필요하면 develop 빌드에서 `cbrd_27217` 를 여러 번 돌려 `loop_part.log` 를 남긴다. 이 반복 실패는 이 PR과 별도로 CBRD-27217 담당자에게 알릴 후속 작업이다.

## Baseline comparison

- head `9cc4cf8302`, 대상 `develop` `1ecb2e7f37`, merge base `1ecb2e7f37` (2026-11-19 11:22Z 관측).
- `cubrid-ci collect-base` 는 네 suite 모두 `not_observed` (exit 3)였고, `verify` 의 기준선 상태는 `unavailable` 이다. merge base에 gha-ci suite 결과가 없다.
- 그래서 정확한 기준선 비교는 없다. 위의 이전 실패는 이력 맥락이며 기준선 분류를 대신하지 않는다.

## Testcase history

- 질의: `cubrid-tcc history shell/_06_issues/_26_2h/cbrd_27217/cases/cbrd_27217.sh --suite test_shell` (`cubrid-tcc 0.3.0`). `history_result` 는 `UNKNOWN_HISTORY` 다(shell 증거는 실패만 기록하므로 통과 이력이 불완전하다).
- 발생: 통과 446, 실패 1(실행 28324, run 40532265994, shard 11, 엔진 `2d925cb8685600135eb1fb1781811f6b45fdecb0`, testcase `a4e12efc7ecdc0e37b17456b02ce8b40f876f128`). 증상 비교는 `cubrid-tcc evidence --execution 28324 --file test-results/test-shell.xml` 로 했다.
- 이번 run은 Chronicle에 아직 색인되지 않았다(`sync-data --run 44496524091` 가 관측 0건). 그래서 이번 발생을 이력에 묶지 못했다.
- 기록: `cubrid-tcr` 에 서명 `loop-missing-result-row` (`--text "executions printed the expected line, list_file.c bytes grew by 0"`)와 메모를 더했다. 규칙은 더하지 않았다(규칙은 운영자 승인 대상).

## Actions and evidence

1. #8642를 ready로 바꾸지 않고, 리뷰어를 지정하지 않으며, JIRA를 바꾸지 않았다(실패 시 지시대로).
2. 재실행 여부를 운영자가 정한다: `gh pr comment https://github.com/CUBRID/cubrid/pull/8642 --body "/run rerun 44496524091"`. 재실행이 통과하면 #8642의 ready 전환 조건을 다시 본다.
3. `cbrd_27217` 의 간헐적 실패는 이 PR과 별도 후속으로 남긴다.

증거 파일: 위 증거 디렉터리의 `summary.json`, `failures/.../message.txt`, `failures/.../diff.txt`, `raw/shards/14/linux_shell_64bit_optdebug.xml` (`cbrd_28065` 통과). Chronicle 실행 28324의 `test-results/test-shell.xml`.
