# CBRD-28271 CI 분석 — PR #8736, run 45567167574 (경고 보고서)

> **이 스냅샷으로는 회귀(regression)나 근본 원인 결론을 내릴 수 없습니다.** `test_sql` 수집이 무결성 오류로 실패했고, 판정 규칙(`report_mode.py`)이 `mode: warning`, `regression_conclusions_allowed: false`를 반환했습니다. 아래 내용은 검증된 증거만 담습니다.

## 요약

- PR: [CUBRID/cubrid#8736](https://github.com/CUBRID/cubrid/pull/8736), head `fd7d071ed5c625612d6035a5028d99f74b0922d7`, base `develop` (merge base `bfb59bdd133518da140f9af6c48bef5568df67af`).
- Run: [45567167574](https://github.com/CUBRID/cubrid/actions/runs/45567167574) attempt 1, `/run all`. 2026-11-25T11:05:57Z에 종료, 결과 `failure`.
- 통과: `build (debug)`, `build (release)`, `test_medium`, `test_shell`.
- 실패: `test_sql`(3건, shard 09), `test_sql_by_cci`(3건, shard 09).
- `test_sql_by_cci`의 3건은 검증된 증거로 확인했습니다. 세 건 모두 optimizer 실행 계획 또는 trace 출력 차이입니다. 세 testcase 모두 serial 객체(`CREATE SERIAL`, `NEXT_VALUE`, `AUTO_INCREMENT`)를 쓰지 않습니다. (관찰)
- `cubrid-tcr` 판정: 세 건 모두 `known_job`("the job is known noisy and each failure's symptom still needs analysis").
- `test_sql`의 3건은 testcase 이름을 확인하지 못했습니다(아래 "수집 진단").
- 다음 조치: `test_sql` 증거 수집 문제를 해결하고, develop의 같은 base에서 같은 3건이 실패하는지 확인합니다. 수정, push, CI 재실행은 하지 않았습니다.

## CI 스냅샷

| Suite | 상태 | 판정 | 수(검증된 것만) |
| --- | --- | --- | --- |
| `test_medium` | completed, summary `validated` | SUCCESS | — |
| `test_shell` | completed, summary `validated` | SUCCESS | — |
| `test_sql` | `collection_failed`, summary `absent` | FAILURE (status) | 확인 불가. collect annotation은 `sql: 3 failed` |
| `test_sql_by_cci` | completed, summary `validated` | FAILURE | planned 17902, run 17902, passed 17899, failures 3, errors 0 |

## 증거 범위

- Collector: `cubrid-ci 0.2.0 (00205d576de0, release)`. Collection 시작 2026-11-25T11:06Z, exit `4`. `cubrid-ci verify` exit `3`.
- Assessment: `identity: established`, `observation: incomplete`, `manifest: validated`, `requested_summaries: partial`.
- 증거 디렉터리: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8736/fd7d071ed5c625612d6035a5028d99f74b0922d7`
- Testcase revision: `CUBRID/cubrid-testcases` `tc/pr-8736` `b2609e6579e6` (모든 shard 동일). 이 revision은 CBRD-28111 TC 변경 `7e99b9007`을 포함합니다.
- 엔진 변경 범위: `src/query/serial.c` 한 파일(+7/−1).

## 수집 진단 (`test_sql`)

- 첫 수집(2026-11-25T10:59:46Z, run 진행 중): `integrity` 오류. "shard 01 JUnit omits 19 testcases that summary_info reports (summary_info 3557/0/0, JUnit 3538/0/0)". 빠진 19건은 모두 `sql/_05_plcsql/_01_testspec/_05_bug_fix/` 아래 testcase입니다.
- 두 번째 수집(11:06Z, run 종료 후): `integrity` 오류. "immutable evidence already exists with different content: …/test_sql/raw/github/collect.log". 첫 수집이 run 진행 중에 받은 `collect.log`와 종료 후 받은 내용이 다릅니다.
- 결론 범위: `test_sql` 실패 testcase 이름, 수, 차이는 알 수 없습니다. 무결성 오류는 우회하지 않았습니다.

## 실패 목록 (`test_sql_by_cci`, 검증됨)

| Testcase | Shard | 관찰된 차이 | `cubrid-tcr` | PR 관련성 |
| --- | --- | --- | --- | --- |
| `sql/_36_guava/cbrd_26795/cases/cbrd_26795.sql` | 09 | `show trace`의 `SCAN (table: dba.px_wide_t)` / `px_rnd_t` 줄 끝에 `(oos time: ?, fetch: ?, ioread: ?)`가 추가됨 (4개 statement) | `known_job` | `unknown` (경고 모드) |
| `sql/_36_guava/cbrd_27748/cases/cbrd_27748.sql` | 09 | 실행 계획에서 `temp(sort limit)` 대신 `iscan`이 outer가 되고, `/* ---> skip ORDER BY */`가 추가됨 | `known_job` | `unknown` (경고 모드) |
| `sql/_36_guava/cbrd_28121/cases/cbrd_28121.sql` | 09 | 실행 계획 출력에서 `skip order by: true` 줄이 빠짐 | `known_job` | `unknown` (경고 모드) |

### 관찰과 추론 (결론 아님)

- 관찰: 세 차이는 optimizer의 ORDER BY skip 판단(`src/optimizer/`)과 scan trace의 OOS 통계 출력(`src/query/scan_manager.c:9952`)에서 나옵니다. PR은 `src/query/serial.c`의 `serial_update_serial_object`만 바꿉니다. 추가된 분기는 serial 행이 페이지에 들어가지 않을 때만 실행됩니다.
- 관찰: 세 testcase에 serial 객체 사용이 없습니다. "serial"이 나오는 곳은 모두 "병렬이 아닌(serial) 실행"이라는 뜻의 주석과 문자열입니다.
- 추론: PR 변경과 관련이 없을 가능성이 큽니다. merge base `bfb59bdd13`이 바로 CBRD-28111 엔진 커밋이고, `cbrd_27748`/`cbrd_28121`의 차이는 같은 ORDER BY skip 판단에 걸립니다.
- 반증 조건: 같은 엔진 base `bfb59bdd13`(또는 PR 변경이 없는 develop)에서 같은 TC revision으로 세 testcase가 통과하면 이 추론은 틀립니다.
- 알 수 없음: develop `bfb59bdd13`에 CI 결과가 없어 baseline 비교가 불가능합니다(`collect-base` 결과: 4개 suite 모두 `not_observed`, `baseline: unavailable`).

## Baseline 비교

- Target `develop` `bfb59bdd133518da140f9af6c48bef5568df67af`, merge base 같음. 관찰 시각 2026-11-25T11:06:58Z.
- 모든 suite가 `not_observed`라서 baseline이 없습니다. `test_sql_by_cci`는 develop commit에 원래 status가 없습니다.

## Testcase 이력

- `cubrid-tcc history`: 세 testcase 모두 이전 실패 0건. `cbrd_26795`는 2026-10-27 PASS 기록만 있고, `cbrd_27748`/`cbrd_28121`은 `not_indexed`. `test_sql_by_cci`는 Chronicle suite가 없어 이력이 없습니다.
- 로컬 수집 증거: `cbrd_27748`은 PR #8128(run 45384316698)과 PR #8632(run 45133100934)의 `test_sql_by_cci`에서도 실패했습니다. 숫자를 지운 차이 비교 결과는 이번 실패와 다릅니다. 같은 증상이라고 볼 근거가 없습니다.
- `cubrid-tcc sync-data --run 45567167574`는 exit `2`로 실패해 이번 run을 색인하지 못했습니다.

## 조치 순서

1. `test_sql` 증거: collector의 immutable 충돌(run 진행 중 수집한 `collect.log`)을 해결한 뒤 다시 수집합니다. 데이터 삭제나 우회는 별도 승인이 필요합니다.
2. Baseline: develop `bfb59bdd13` 또는 그 이후 develop 커밋에서 같은 세 testcase가 실패하는지 확인합니다. 다른 PR의 최신 run이 같은 실패를 보이면 이 PR과 무관하다는 근거가 됩니다.
3. 참고: develop이 `bfb59bdd13` 이후 진행되었고, 그 사이에 같은 함수를 바꾸는 `cbed1d5707 [CBRD-28073] Keep serial row storage form in NEXT VALUE (#8514)`가 들어왔습니다. merge 전에 develop 반영(rebase)이 필요할 수 있습니다.
4. 수정, push, CI 재실행은 사람의 지시 후에만 합니다.

---

# 두 번째 run — head `fb05460a1f`, run 45603558494 (경고 보고서)

> **판정 규칙(`report_mode.py`)이 다시 `mode: warning`을 반환했습니다.** `test_sql` 수집이 첫 run과 같은 무결성 오류(shard 01 JUnit이 19건 누락)로 실패했습니다. 아래 회귀 판단은 CI 증거 비교가 아니라 로컬 재현과 bisect에 근거합니다.

## 요약

- Head `fb05460a1f0b8601e542b7d5a7b762d04cb1ef9b` = develop `a5ab407ba0`(CBRD-28073 포함) 위로 rebase한 같은 수정. TC: private `52eaedb2b`, public `43c1aa8de`(둘 다 develop merge).
- Run [45603558494](https://github.com/CUBRID/cubrid/actions/runs/45603558494) attempt 1, 2026-11-25T17:16:56Z 종료, `failure`.
- 통과: `build (debug)`, `build (release)`, `test_medium`. 실패: `test_shell`(1 failure, 1 error), `test_sql`(수집 실패), `test_sql_by_cci`(4 failures).
- 핵심 결과: **`cbrd_27744_sa` 실패는 develop 회귀이고, 첫 bad commit은 `e74826c46c [CBRD-27562]`입니다.** 이 PR의 수정이 없는 develop에서도 같은 값으로 실패합니다.

## 실패 목록 (검증된 suite)

| Suite | Testcase | 관찰 | PR 관련성 (로컬 근거) |
| --- | --- | --- | --- |
| `test_shell` | `shell/_06_issues/_26_2h/cbrd_27744_sa/cases/cbrd_27744_sa.sh` | 13: `sa_crash serial after recovery: expected '140001 2147483647 1', got '1 2147483647 1'`; 14: `ids: expected '1 210001', got '1 70001'` | `unlikely`, 신뢰도 높음 |
| `test_shell` | `shell/_06_issues/_26_2h/cbrd_28255/cases/cbrd_28255.sh` (error) | csql -S 139, checkdb 인덱스 0개, core (`er_dump_call_stack_internal`) | `unlikely`: 엔진 수정 `ca39c2c6a`(#8711)가 rebase 뒤(11:18:03Z)에 develop에 들어감, TC는 이미 develop에 있음 |
| `test_sql_by_cci` | `sql/_13_issues/_26_2h/cases/cbrd_28255.sql` | `CREATE INDEX`가 `Error:-190` | 같은 이유로 `unlikely` |
| `test_sql_by_cci` | `sql/_36_guava/cbrd_26795`, `cbrd_27748`, `cbrd_28121` | 첫 run과 같은 optimizer/trace 차이 | 첫 run과 같음 (`unknown`, serial 무관) |

## `cbrd_27744_sa` 재현과 bisect

로컬 debug 빌드, 최신 CTP(`cubrid-testtools` `origin/develop` `db9b870`를 별도 디렉터리에 풀어 씀. 공유 CTP checkout은 `wait_until`이 없는 32 commit 뒤 버전), TC `52eaedb2b`.

| 엔진 | 결과 |
| --- | --- |
| `fb05460` (develop + 이 PR) | 13, 14 NOK (CI와 같은 값) |
| `a5ab407` (develop, 이 PR 없음) | 13, 14 NOK (같은 값) |
| `510157f` (CBRD-28073 이전) | 13, 14 NOK |
| `47692d4`, `c0dee81`, `e74826c` | 13 NOK |
| `9937d09` (`e74826c`의 부모) | 13 OK |

- `git bisect` 결과: first bad commit `e74826c46c55015c0b5e252dc03b057bea6afcdf` "[CBRD-27562] Do not start a system operation for temporary sector reservation or temporary volume growth (#8537)".
- 첫 run(`fd7d071` = `bfb59bd` + 이 PR)은 CI에서 `cbrd_27744_sa`를 통과했습니다(shard 28, 37.1s).
- 병합 순서: #8537의 마지막 `test_shell`은 2026-11-21에 통과했습니다. CBRD-27744 엔진(`44e9290f38`)과 TC(`fb02a1c72`)는 2026-11-24에 들어왔습니다. 두 변경은 함께 CI를 거치지 않았습니다.
- 추론(확인 안 됨): sa_crash는 크래시 전에 `INSERT ... SELECT ... LIMIT 5000`으로 임시 파일을 씁니다. 임시 sector 예약이 system operation 없이 진행되면서, SA 재시작 복구에서 DDL undo(`RVHF_SERIAL_DDL_UPDATE_UNDO`)가 값을 지키는 경로를 타지 못하는 것으로 보입니다. 원인 분석은 하지 않았습니다.
- 반증 조건: `e74826c` 단독 revert로 13, 14가 OK가 되지 않으면 이 귀속은 틀립니다.
- JIRA 중복 확인(`cubrid-jira-dup candidate-find`): 일치하는 이슈 없음. 상위 후보 CBRD-28127, CBRD-27564, CBRD-27991, CBRD-27641은 serial cache, HA, 동시 ALTER SERIAL 문제입니다.

## 조치

1. CBRD-27562 담당자(#8537 작성자 `hornetmj`)에게 develop 회귀를 알리고 JIRA 이슈를 만듭니다. 사람의 결정이 필요합니다.
2. 이 PR의 CI는 develop 회귀(`cbrd_27744_sa`)와 TC/엔진 시차(`cbrd_28255`)가 해결된 develop으로 다시 rebase한 뒤 재실행해야 green이 됩니다.
3. `test_sql` 수집 무결성 오류(shard 01 JUnit 19건 누락)는 두 run에서 반복되었습니다. collector 또는 CI 산출물 문제로 따로 다룰 필요가 있습니다.
