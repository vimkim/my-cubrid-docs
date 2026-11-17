# CI 분석: PR #8565, run 43854919568 (경고 보고서)

> **이 스냅샷으로는 회귀 여부나 근본 원인을 결론 내릴 수 없다.** head 수집이 `incomplete`로 끝났다(`test_sql`, `test_sql_by_cci` 수집 실패). `report_mode.py` 판정은 `warning`이다. 아래의 PR 관련성과 확신도는 검증된 부분 증거에서 끌어낸 추론이며, 게이트를 통과한 결론이 아니다.

## 요약

- 분석일: 2026-11-17 (Asia/Seoul). 대상: [PR #8565](https://github.com/CUBRID/cubrid/pull/8565) head `436d1cd5bbe14bc09e7cd2e7f6e327972034b0f8`, base `develop`, merge base `666bb10ae673c666c18aa9ae58dda59c9df59fdf`.
- `test_medium` 통과(975/975). `test_shell` 실패 1건, `test_sql_by_cci` 실패. `test_sql`은 CI 결과 SUCCESS지만 collector 무결성 검사에 걸렸다(base에서도 같다).
- 새 TC `shell/_40_guava/cbrd_28102/cases/cbrd_28102.sh`는 shard 36에서 실행되어 통과했다(7.754초).
- `test_shell` 실패 `cbrd_21737.sh`는 `statdump` 출력 파일이 비었다는 타이밍 검사 실패다. 같은 testcase 트리를 쓴 base에서는 통과했지만, 같은 증상이 이 PR 변경이 없는 다른 두 engine(PR #8318, #8347)에서 이미 나왔다. postpone 경로와 연결점도 없어 PR 관련성은 낮다고 추론한다.
- `test_sql_by_cci`는 known-issue 규칙 `sql-by-cci-every-branch`에 걸린다(base에서도 실패). shard 05/07 실패 3건은 base와 정확히 같은 케이스다. 다만 **shard 09는 head에서만** `cbrd_27485.sql` 도중 서버 연결이 끊기고(`-677` `ER_BO_CONNECT_FAILED`) 이후 케이스가 모두 약 250초씩 걸려 2시간 timeout으로 취소되었다. base shard 09는 9분에 끝났다. 이 서버 다운 증상은 원인을 모른다. 가장 우선할 다음 조치는 이 증상의 서버 로그나 core를 얻거나 재현하는 것이다.
- TC Merge Gate(`Check TC PRs`) 실패는 회귀가 아니다. TC PR [CUBRID/cubrid-testcases-private-ex#4942](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4942)(`tc/pr-8565`)가 열려 있어서이며, 최종 merge handoff까지 미룬다.

## 대상과 증거 범위

| 항목 | 값 |
| --- | --- |
| PR | https://github.com/CUBRID/cubrid/pull/8565 `[CBRD-28102] Run the postpone that precedes a system operation` |
| head | `436d1cd5bbe14bc09e7cd2e7f6e327972034b0f8` (`src/transaction/log_manager.c` `log_do_postpone`의 `LSA_LT` → `LSA_LE` 한 곳) |
| merge base / target tip | `666bb10ae673c666c18aa9ae58dda59c9df59fdf` (`develop`, 관측 2026-11-17T06:21:42Z) |
| head run | https://github.com/CUBRID/cubrid/actions/runs/43854919568 attempt 1 |
| base run | https://github.com/CUBRID/cubrid/actions/runs/43897550601 attempt 1 |
| 수집 | head observation `20261117T061538.819814171Z-222089-0`, `cubrid-ci 0.2.0 (961fc3e59494, release)` |
| head 판정 | `verify` exit 3: identity `established`, observation `incomplete`, manifest `validated`, requested_summaries `partial` → `report_mode` `warning`, comparison_scope `none` |
| baseline 판정 | `collect-base` exit 4, `verify` exit 3 → `partial_exact` (`test_sql`만 수집 실패) |
| shell testcase | head `cubrid-testcases-private-ex` `d1112ba69e11` (`tc/pr-8565`), base `9c12c9185b3b` (`develop`) |
| sql testcase | head `cubrid-testcases` `15ef213c54ce` (`tc/pr-8565`, base에 빈 init 커밋 하나), base `a62230375a17` (`develop`); 두 revision의 트리 차이 없음 |
| build | shell/sql/medium: debug, sql_by_cci: release. 모든 shard의 build SHA가 각 commit과 일치 |

## Suite 상태

| Suite | CI 결과 | 수집 상태 | 개수 (head) | base |
| --- | --- | --- | --- | --- |
| test_medium | SUCCESS | validated | 975개 모두 통과 | 975개 모두 통과 |
| test_shell | FAILURE | validated | 3613개: 통과 3582, failure 1, error 0, skip 30 | 3612개: 통과 3581, failure 1 (`apis_1125.sh`), skip 30 |
| test_sql | SUCCESS | collection_failed (integrity) | 검증된 판정 없음 | 같은 진단으로 collection_failed |
| test_sql_by_cci | FAILURE | collection_failed (remote, job_level) | 검증된 판정 없음 | validated: 17815개 중 failure 7 |
| Check TC PRs | FAILURE | 해당 없음 (gate) | TC PR 미병합 | 해당 없음 |

### 수집 원장과 진단

- `test_medium` shard 00, `test_shell` shard 00–49, `test_sql` shard 00–09: 모두 `retained`.
- `test_sql`: `identity_or_integrity`. shard 01 JUnit이 `summary_info`보다 18개 적다(3550 대 3532, 실패 0). 빠진 18개는 모두 `sql/_05_plcsql/_01_testspec/_05_bug_fix/` 아래 `cbrd-27556`, `cbrd-27584`, `cbrd-27633`, `cbrd-27634`, `cbrd-27742`, `cbrd-27927` 케이스다. base run에서도 같은 진단이 나왔다. CI 쪽 결과 파일 문제로 보며 실패 판정은 아니다.
- `test_sql_by_cci`: shard 00–04, 06, 08 `retained`. shard 05, 07은 `junit` 단계에서 `remote` 실패("error decoding response body", 각각 603684, 530988 byte 소비). shard 09는 `job_level`: JUnit XML 없음.
- binary budget: 536870912 byte 중 0 byte 소비. budget 제약 없음.

## 실패 목록

분류 열의 baseline 비교는 report mode가 `warning`이므로 정식 분류가 아니다. 괄호 안은 관측 사실이다.

| Suite | Testcase | 결과 | 현상 | baseline 분류 | known-issue | PR 관련성 (추론) | 확신 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| test_shell | `shell/_06_issues/_18_2h/cbrd_21737/cases/cbrd_21737.sh` | failure (shard 44) | `cbrd_21737-3 : NOK stat.log is empty` | uncomparable (warning 모드). 관측: base shard 17에서 통과, testcase 트리 동일 → 비교가 허용됐다면 `additional_on_head` (base pass) | `no_match` | unlikely | 높음 |
| test_sql_by_cci | job-level, shard 09 | job 취소 (2시간 timeout), JUnit 없음 | `cbrd_27485.sql`의 7번째 문장부터 `Error:-677`, 이후 `cbrd_27487`부터 26개 케이스가 각 약 250초 걸려 NOK | uncomparable (head 미검증). 관측: base shard 09는 9분에 끝났고 `cbrd_27485` 통과(0.652초) | `known` (`sql-by-cci-every-branch`, issue 없음) | unknown | 낮음 |
| test_sql_by_cci | `sql/_23_apricot_qa/_02_performance/_01_filtered_index/cases/filtered_index_basicfunction_delete_004.sql` | failure (shard 05, 대체 경로) | unexpected result | uncomparable. 관측: base에서도 같은 케이스 실패 | `known` (job 규칙) | unlikely | 중간 |
| test_sql_by_cci | `sql/_27_banana_qa/issue_16066_BINARY_charset/_00_String_Functions_and_Operators/cases/rtrim_002.sql` | failure (shard 07, 대체 경로) | unexpected result | uncomparable. 관측: base에서도 실패 | `known` (job 규칙) | unlikely | 중간 |
| test_sql_by_cci | `sql/_27_banana_qa/issue_5765_timezone_support/_01_table_operations/_04_select/cases/_05_select_subquery_t.sql` | failure (shard 07, 대체 경로) | unexpected result | uncomparable. 관측: base에서도 실패 | `known` (job 규칙) | unlikely | 중간 |

개수: 검증된 head 실패는 1건(test_shell)이다. shared 0, additional 0, uncomparable 1(warning 모드라 정식 비교 불가). base_only 관측: test_shell `shell/_06_issues/_26_2h/apis_1125/cases/apis_1125.sh`(head shard 22에서 통과). sql_by_cci 행은 collector가 검증하지 못한 대체 증거이며 개수에 넣지 않는다.

## 원인 분석

### cbrd_21737: statdump 타이밍 검사

- **관측**: testcase(`d1112ba`)는 `cubrid statdump $db -i 1 | grep checkpoint > stat.log &`를 띄우고, `java Insert`(20개 thread의 insert)가 끝나자마자 `xkill -f statdump`로 죽인 뒤 바로 `[ -s stat.log ]`를 검사한다. head에서 이 검사만 NOK이고 나머지 3개 검사는 OK다. checkpoint 메시지 없음(검사 2)과 checkpoint 통계 0(검사 4)은 통과했다. base는 같은 트리(`b9d95601c2c4`)로 통과했다(12.1초, head 13.8초).
- **추론**: `grep`은 파일로 쓸 때 출력을 버퍼에 모으고, `statdump`가 kill된 뒤 EOF를 받아야 flush한다. 검사가 그보다 먼저 실행되면 파일이 비어 있다. 이 경쟁은 engine 동작과 관계없다. 테스트 DB는 기본 reuse_oid 테이블만 쓰고, PR이 바꾼 경로(commit 시 postpone 캐시가 넘친 경우의 `log_do_postpone`)가 statdump 출력에 영향을 줄 방법이 보이지 않는다.
- **이력**: 같은 증상이 이 PR 변경이 없는 두 engine(PR #8318, #8347, 2026-10-30)에서 이미 나왔다. 아래 "Testcase 이력"을 본다.
- **모름**: shell job 로그와 서버 로그를 보지 못했다. 같은 engine에서 반복 실행한 PASS/FAIL 쌍은 없다.
- **반증 조건**: 같은 head에서 반복 실행해 항상 실패하거나, base에서 반복 실행해 항상 통과하면 이 추론은 틀리다.
- **다음 조치**: 실패한 suite만 다시 돌려 통과하는지 본다(별도 승인 필요). 필요하면 `cubrid-test-shell-run`으로 head와 base에서 로컬 반복 실행한다.

### test_sql_by_cci shard 09: head에서만 서버 연결 끊김

- **관측 (대체 증거)**: 아티팩트 서버의 `sql_by_cci/shard/09/artifacts/ctp_log.tgz`(sha256 `416e07ee…b61c`)의 `summary.info`에서 418개 OK, 30개 NOK. NOK 30개는 base shard 09에서도 실패한 3개(`cbrd_25984.sql`, `cbrd_26258/join_orderby_skip.sql`, `cbrd_27101.sql`), `cbrd_27485.sql`, 그리고 약 250초씩 걸린 26개다. `cbrd_27482_coalesce.sql`까지는 다른 케이스가 정상이었고, `cbrd_27485.sql`의 결과는 앞 6개 문장(drop, create, insert 50행 2번)은 정상이고 7번째 문장(`insert into outer_big ... limit 100000`)부터 끝까지 `Error:-677`이다. 다음 `cbrd_27487`부터 `cbrd_27510/21_common_value_char_types.sql`까지 26개 케이스가 각 약 250초 걸리고 결과 파일이 비어 있다. base에서 실패한 `cbrd_27683`까지는 가지 못했다. job은 "Run CTP" 단계에서 2시간(12:28:39Z–14:28:12Z) 뒤 취소되었다.
- **관측 (검증된 base)**: base run shard 09는 9분(16:12:33Z–16:21:31Z)에 끝났다. `cbrd_27485`는 0.652초, `cbrd_27510/*` 29개는 모두 0.39초 이내에 통과했다. `cbrd_27485` 디렉터리는 두 revision에서 같은 트리(`485f62ef382a`)다.
- **관측 (미검증 head raw)**: head debug `test_sql`(collector 무결성 검사로 suite 미검증)의 shard 09 JUnit에서 `cbrd_27485.sql`은 2.555초에 통과했다.
- **추론**: `-677`은 CAS가 DB 서버에 연결하지 못했다는 뜻이다. release 서버가 이 시점에 죽었거나 응답하지 않게 된 뒤 다시 살아나지 않은 것으로 보인다. 같은 testcase가 debug `test_sql`에서는 통과했으므로, 이 케이스에서 결정적으로 재현되는 증상은 아닌 것으로 보인다. 서버가 죽은 정확한 시점(7번째 문장 실행 중인지, 그 이전인지)은 정할 수 없다.
- **PR 변경과의 관계 검토**: PR은 `log_do_postpone`에서 시작 LSA가 system operation의 last parent와 같을 때 그 레코드를 건너뛰지 않고 스캔하게 한다. 그 LSA가 `LOG_SYSOP_END`(연속된 system operation)라도 switch에서 무시되므로 그 자체로는 crash 경로가 아니다. 새로 실행되는 것은 last parent 위치의 `LOG_POSTPONE` 하나이며, 실행은 `log_do_postpone`이 쓰일 때(postpone 캐시가 넘친 commit, system operation postpone, 재시작 복구)로 한정된다. 100000행 insert가 이런 postpone을 만들고 그 redo 함수가 실패하는지는 확인하지 못했다. 따라서 PR 관련성은 `unknown`이다.
- **known-issue**: `cubrid-tcr check --job "shard sql_by_cci 09"`는 규칙 `sql-by-cci-every-branch`(`job_contains = "sql_by_cci"`, issue 없음, 만료 2026-12-09)로 `known`을 반환한다. 이 규칙은 job 이름만 보고 걸리는 포괄 규칙이며, 이번 서버 다운 증상은 비교한 base run에는 없었다. 따라서 이 증상까지 규칙이 다룬다고 보지 않고 따로 보고한다.
- **반증 조건**: 서버 에러 로그나 core가 postpone 실행(`log_run_postpone_op`, `log_do_postpone`) 밖의 위치를 가리키거나, 같은 head에서 sql_by_cci shard 09를 다시 실행해 통과하면 PR 관련 가설은 약해진다. core stack에 `log_do_postpone` 아래의 recovery 함수가 있으면 PR 관련성이 강해진다.
- **다음 조치**: shard 09의 서버 에러 로그나 core를 얻는다(아티팩트에는 `ctp_log.tgz`만 있고 GitHub job 로그는 120초 안에 내려받지 못했다). 그 다음 sql_by_cci만 다시 돌리거나, 로컬 release build에서 `sql/_36_guava/cbrd_27485`를 CCI로 반복 실행한다.

### test_sql_by_cci shard 05/07: base와 같은 실패

- **관측 (대체 증거)**: collector가 디코딩하지 못한 shard 05/07 JUnit을 같은 URL에서 다시 받았다(HTTP 200, sha256 `6c6a8e29…9182`, `7b19980d…868f`). 2639개 중 1개, 2171개 중 2개 실패이며, 세 케이스 모두 base run의 검증된 실패 목록에 있다.
- **추론**: 이 3건은 develop에 이미 있는 sql_by_cci 실패다. 대체 증거라서 정식 `also_observed_on_base` 분류는 아니다.

## Baseline 비교

- head `436d1cd5bb` / target tip `666bb10ae6` / merge base `666bb10ae6`. 탐색 범위: exact-commit status와 check run 전부, 저장소 전체 workflow 검색 없음.
- base 선택: run 43897550601 attempt 1. medium/shell/sql_by_cci 검증됨. sql은 head와 같은 무결성 진단으로 수집 실패.
- 입력 동일성: shell `cbrd_21737` 트리 `b9d95601c2c4` 양쪽 같음. sql testcase는 head revision이 base revision에 빈 init 커밋만 더한 것(트리 diff 없음). build 모드는 양쪽 같음.
- 한계: head report mode가 `warning`이라 정식 비교 범위는 `none`이다. 위 비교는 관측으로만 쓴다.

## Testcase 이력

- `cbrd_21737.sh` (shell): `cubrid-tcc 0.3.0` `history` 결과 `SEEN_BEFORE`. sync 후 색인된 실행 484건 중 PASS 482, FAIL 2. 이번 run 43854919568은 아직 색인되지 않았다.

  | run | shard | engine | testcase | PR (base) | 완료 시각 | 증상 |
  | --- | --- | --- | --- | --- | --- | --- |
  | [40995546195](https://github.com/CUBRID/cubrid/actions/runs/40995546195) | 44 | `7f2f138bc974` | `89480ca89c89` (`tc/pr-8318`) | #8318 (`develop`) | 2026-10-30T03:49:56Z | `cbrd_21737-3 : NOK stat.log is empty`, 검사 1·2·4 OK |
  | [41048233875](https://github.com/CUBRID/cubrid/actions/runs/41048233875) | 38 | `eac70c7e740d` | `8c8aec181e56` (`tc/pr-8347`) | #8347 (`feature/oos-merge`) | 2026-10-30T12:20:38Z | 같음 |

  두 실패는 이번 실패와 증상이 같다(retained JUnit, Chronicle execution 19076, 15861에서 확인). 두 build 모두 이 PR 커밋(2026-11-16 작성)보다 먼저 만들어졌으므로 이 PR 변경을 포함하지 않는다. `eac70c7e740d`는 로컬에서 PR 커밋을 조상으로 갖지 않음을 확인했고, `7f2f138bc974`는 로컬 객체가 없어 ancestry는 시간 순서로만 판단했다. CLI 플래키 판정은 없다(같은 engine revision에서의 PASS/FAIL 쌍이 없음). 그래서 플래키라고 단정하지 않고, "다른 engine에서 같은 증상이 반복된 간헐 실패"로만 기록한다.
- 커버리지 한계: `cubrid-tcr check`의 `sync_hint`에 따라 `cubrid-tcc sync-data --since 2026-10-27 --until 2026-11-17 --suite shell --revisit-limit 0`을 한 번 실행했다. exit 2로 끝났다: snapshot 14965개를 넣었고 run 29개는 GitHub HTTP 502로 실패했다. `history`의 window 2026-10-14–2026-11-17 커버리지는 `discovery_complete: false`, 누락 run 3437건이다. `check` 판정은 `no_match` 그대로다. 다시 sync하지 않았다.
- `cubrid-tcr`에 이 반복 증상을 note로 남겼다.
- `test_sql_by_cci`: Chronicle이 이 suite를 색인하지 않아 이력이 없다.

## TC Merge Gate

`github-actions: Check TC PRs` FAILURE(https://github.com/CUBRID/cubrid/actions/runs/43854345085/job/133254638583)는 TC PR CUBRID/cubrid-testcases-private-ex#4942(`tc/pr-8565`, `shell/_40_guava/cbrd_28102/cases/cbrd_28102.sh` 추가)가 아직 병합되지 않아서다. 회귀가 아니며, testcase lifecycle에 따라 리뷰와 다른 CI가 끝난 뒤 최종 engine merge 직전에 처리한다. 이 gate가 막혀 있는 동안 PR을 green으로 보지 않는다.

## 우선순위별 조치

1. sql_by_cci shard 09 서버 다운의 원인 증거를 얻는다: 서버 에러 로그나 core. 얻을 수 없으면 sql_by_cci만 다시 돌려 재현 여부를 본다(CI 트리거는 별도 승인).
2. `test_shell`을 다시 돌려 `cbrd_21737`이 통과하는지 본다. 같은 재실행에서 sql_by_cci도 함께 본다.
3. `test_sql` 수집 무결성 문제(shard 01 JUnit 18개 누락)는 base에도 있으므로 PR과 별도로 CI 쪽 후속 작업으로 둔다.
4. TC PR #4942는 최종 merge handoff까지 열어 둔다.

## 증거 파일

- head bundle: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8565/436d1cd5bbe14bc09e7cd2e7f6e327972034b0f8/` (observation `20261117T061538.819814171Z-222089-0`)
  - shell 실패: `providers/github-actions/runs/43854919568/attempts/1/test_shell/failures/shell_06_issues_18_2h_cbrd_21737_cases_cbrd_21737_sh-780b03eb03/{message.txt,diff.txt}`
  - cbrd_28102 결과: `.../test_shell/raw/shards/36/linux_shell_64bit_optdebug.xml`
- base bundle: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/666bb10ae673c666c18aa9ae58dda59c9df59fdf/providers/github-actions/runs/43897550601/attempts/1/`
- 대체 증거(collector 밖, 분석 세션 scratch, 보존 보장 없음): sql_by_cci shard 05/07 JUnit, shard 09 `ctp_log.tgz`, run job 목록. 원본 URL은 `http://192.168.1.48:30080/runs/43854919568/sql_by_cci/shard/{05,07,09}/` 아래다.
