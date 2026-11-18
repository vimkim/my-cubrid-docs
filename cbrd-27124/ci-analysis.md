# PR #8617 SQL CI 증거 경고

2026-11-18 KST. 이 보고서는 CUBRID PR #8617의 일반 SQL과 CCI SQL 실패를 조사하는 엔진 개발자를 위한 기록이다. 대상은 gha-ci run `44276812011` attempt `1`의 Engine `1e71328a5e370c3f46d9794e21841f0068c1dd5b`다. 두 잡은 `tc/pr-8617`의 `56ef406c1b3a9e6929ef74f9d547dd9aa9894934`를 사용했다. [PR #8617](https://github.com/CUBRID/cubrid/pull/8617), [실행](https://github.com/CUBRID/cubrid/actions/runs/44276812011/attempts/1)

**수집 검증 상태는 `warning`이다. 이 스냅샷으로 회귀나 근본 원인을 확정할 수 없다.** `cubrid-ci 0.2.0 (00205d576de0, release)`가 Engine SHA와 실행을 확인했고 CCI SQL 요약을 검증했다. 일반 SQL 요약은 JUnit의 누락 때문에 생성되지 않았다.

| Suite | CI 상태 | 검증 상태와 집계 | Job |
| --- | --- | --- | --- |
| `test_sql` (optdebug) | 실패 | `collection_failed`. CI의 16 NOK는 아래 원본 진단을 참조한다. | [collect](https://github.com/CUBRID/cubrid/actions/runs/44276812011/job/134743927593) |
| `test_sql_by_cci` (release) | 실패 | 요약 검증 완료. 17,832개 계획·실행, 17,821 통과, 11 실패, 오류·건너뜀·미실행 0. | [collect](https://github.com/CUBRID/cubrid/actions/runs/44276812011/job/134739755841) |

## 일반 SQL 수집 진단

`collect`는 종료 코드 4, `verify`는 종료 코드 3을 반환했다. 수집 관측은 `incomplete`이며 manifest 검증을 통과했다. 검증기가 보고한 이슈는 `test_sql`의 `unavailable`이다. 수집기는 shard 01의 집계 불일치를 `identity_or_integrity`로 기록했다.

두 suite에서 shard 00–09를 모두 `retained`로 기록했다. 불일치는 응답 보관 이후 결과 검증 단계에서 발견했다. 바이너리 예산은 536,870,912바이트 중 0바이트를 사용했다.

- shard 01의 `summary_info`는 통과 3,549건과 실패 8건을 기록한다. JUnit은 통과 3,530건과 실패 8건을 기록한다. 빠진 통과 19건은 모두 `sql/_05_plcsql/_01_testspec/_05_bug_fix/` 아래에 있다.
- 원본 10개 shard에서 CI `summary_info`를 합하면 17,832건에 통과 17,816건과 NOK 16건이다. JUnit에는 17,813개 행이 있으며 통과 17,797건, failure 15건, error 1건이다. 양쪽 기록과 CI `failed.list`의 16개 실패 경로가 일치한다. shard 03의 `cbrd_27843.sql`은 CI에서 NOK, JUnit에서 error다. 이 집계는 누락 범위를 보여 주는 진단이다. [원본 집계와 경로](/home/vimkim/temp/cubrid-pr8617-sql-a1.3xUpCE/sql-reconciliation.json)
- Attempt 1의 shard 03 로그에는 `cbrd_27843.sql` 실행 중 `btsort_radix_validate` assertion과 직후의 DB 연결 실패가 있다. 원본 JUnit의 메시지와 이 로그를 보관했다. [shard 03](https://github.com/CUBRID/cubrid/actions/runs/44276812011/job/134708812543), [로그 발췌](/home/vimkim/temp/cubrid-pr8617-sql-a1.3xUpCE/github/sql-shard03-relevant.log), [JUnit 메시지](/home/vimkim/temp/cubrid-pr8617-sql-a1.3xUpCE/sql-raw)

## 검증된 CCI SQL 실패 11건

각 메시지의 `** Expected :`가 지정한 정확한 TC revision의 답안을 Git에서 확인했다. 11개 답안 모두 아래 케이스 디렉터리의 형제 `answers/`에 있는 `.answer`였다. [소스와 답안 경로 및 Git blob](/home/vimkim/temp/cubrid-pr8617-sql-a1.3xUpCE/testcase-inputs.json)

| Shard | Testcase 경로 | 기대값 → 실제값 |
| --- | --- | --- |
| 01 | `sql/_04_operator_function/_05_arighmetic_op/_008_round/cases/1012.sql` | `ROUND(INT,FLOAT)` 결과 행 → `Error:-427` |
| 01 | `sql/_04_operator_function/_05_arighmetic_op/_008_round/cases/1029.sql` | `ROUND(SMALLINT,FLOAT)` 결과 행 → `Error:-427` |
| 01 | `sql/_04_operator_function/_05_arighmetic_op/_008_round/cases/1031.sql` | `ROUND(SMALLINT,REAL)` 결과 행 → `Error:-427` |
| 01 | `sql/_04_operator_function/_05_arighmetic_op/_008_round/cases/1032.sql` | `ROUND(SMALLINT,NUMERIC)` 결과 행 → `Error:-427` |
| 01 | `sql/_04_operator_function/_05_arighmetic_op/_008_round/cases/1033.sql` | `ROUND(SMALLINT,MONETARY)` 결과 행 → `Error:-427` |
| 01 | `sql/_04_operator_function/_05_arighmetic_op/_008_round/cases/1034.sql` | `ROUND(INT,REAL)` 결과 행 → `Error:-427` |
| 01 | `sql/_04_operator_function/_05_arighmetic_op/_008_round/cases/1035.sql` | `ROUND(INT,NUMERIC)` 결과 행 → `Error:-427` |
| 01 | `sql/_04_operator_function/_05_arighmetic_op/_008_round/cases/1036.sql` | `ROUND(INT,MONETARY)` 결과 행 → `Error:-427` |
| 03 | `sql/_13_issues/_26_2h/cases/cbrd_27361_double_nan.sql` | `a = b`의 `count(*), sum(id)`가 `(2,7)` → `(1,4)`. `a <> b`는 `(3,8)` → `(4,11)`. |
| 03 | `sql/_13_issues/_26_2h/cases/cbrd_27843.sql` | `ROUND(SMALLINT, -1)`의 상한 초과에서 `Error:-427` → `-32766`. `WIDTH_BUCKET`의 NaN 인수 사례에서 `Error:-771` → `6`. |
| 05 | `sql/_23_apricot_qa/_02_performance/_02_function_based_index/cases/function_based_index_function_ROUND.sql` | `ROUND(i,g)<=1`에 포함되지 않아야 할 `i=9223372036854775807`, `g=2` 행이 포함됨. |

## 기준선과 이력의 범위

- 정확한 merge-base는 `25b933925529907a9ad092a36de76a0ab944e3f3`이고 당시 `develop` tip은 `2e67e1d9482714f077b554dec5b17a64d167393f`다. 정확한 SHA에 달린 status와 check-run 링크를 페이지 끝까지 탐색했다. 두 suite 모두 `not_observed`였으며 검증기는 `baseline: unavailable`을 반환했다. [기준선 수집](/home/vimkim/temp/cubrid-pr8617-sql-a1.3xUpCE/base-result.json), [기준선 검증](/home/vimkim/temp/cubrid-pr8617-sql-a1.3xUpCE/base-verify.json)
- 이전 PR #8474 run `44040137124` attempt 1에서 CCI SQL 17,821건이 전부 통과했다. 당시 engine은 `09ee1c5158d665e1f67e7f7da8b9924273c65d81`, TC는 `2a0b427cc4bbe52975ccd4a8d3dda0ff46efbd74`였다. 현재 실패한 CCI 11개가 그 실행에서 통과했고 각 SQL과 답안 blob이 일치한다. 당시 일반 SQL은 GitHub status가 성공이지만 수집기의 일반 SQL 검증에는 같은 19건 누락이 있다. PR #8474 실행은 비교용 이력이다. [이전 실행](https://github.com/CUBRID/cubrid/actions/runs/44040137124/attempts/1), [CCI 케이스 비교](/home/vimkim/temp/cubrid-pr8617-sql-a1.3xUpCE/nearby-cases.json)
- `cubrid-tcr 0.1.0`은 일반 SQL 원본의 16개 경로에 `no_match`를 반환했다. `cubrid-tcc 0.3.0`은 일반 SQL 16개 경로의 이력을 `UNKNOWN_HISTORY`로 반환했다. 현재 run으로 한 번 새로 수집했으나 snapshot과 testcase 관측이 0건이었고 파일 1개가 unavailable이었다. Chronicle의 CCI SQL 이력은 제공되지 않는다. [규칙 조회](/home/vimkim/temp/cubrid-pr8617-sql-a1.3xUpCE/known-rules), [이력 조회](/home/vimkim/temp/cubrid-pr8617-sql-a1.3xUpCE/chronicle), [Chronicle 갱신](/home/vimkim/temp/cubrid-pr8617-sql-a1.3xUpCE/chronicle/sync-current.json)

## 보관 위치와 확인할 사항

- [Head 검증 결과](/home/vimkim/temp/cubrid-pr8617-sql-a1.3xUpCE/verify.json), [수집 결과](/home/vimkim/temp/cubrid-pr8617-sql-a1.3xUpCE/result.json), [관측 및 acquisition ledger](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8617/1e71328a5e370c3f46d9794e21841f0068c1dd5b/observations/20261118T105832.712037848Z-1436033-0/result.json), [보고 모드](/home/vimkim/temp/cubrid-pr8617-sql-a1.3xUpCE/report-mode.json)
- [CCI 검증 요약](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8617/1e71328a5e370c3f46d9794e21841f0068c1dd5b/providers/github-actions/runs/44276812011/attempts/1/test_sql_by_cci/summary.json), [별도 GitHub 로그](/home/vimkim/temp/cubrid-pr8617-sql-a1.3xUpCE/github), [Engine과 TC의 Git 이력](/home/vimkim/temp/cubrid-pr8617-sql-a1.3xUpCE/git-provenance.txt)
- 일반 SQL shard 01의 19개 통과 행이 빠진 JUnit 생성 경로를 확인한다. 각 shard의 실행 목록, `summary_info`, JUnit이 일치하는 증거로 전체 suite를 검증한다. 정확한 기준선에서 실행한 같은 TC revision의 결과가 있어야 두 Engine 사이를 비교할 수 있다.
