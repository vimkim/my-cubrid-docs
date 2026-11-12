# CBRD-28046 CI 분석: PR #8495, gha-ci run 43163141709

## 결론

- 판정: 이 PR 변경으로 생긴 실패는 관찰되지 않았다. 실패한 testcase는 모두 merge-base develop
  `2d1513a8af`의 gha-ci run 43047833612에서도 같은 path와 같은 symptom으로 실패했다.
- `test_sql_by_cci` shard 09에서 서버가 실행 중 `LOG FATAL ERROR: log_fetch_from_archive`로 죽었다.
  이 PR은 로그 flush를 바꾸므로 가장 위험해 보이는 신호다. 같은 FATAL이 merge-base develop run과
  PR #8416, #8299의 CI에서도 `_36_guava` 구간에서 관찰되었다. 그래서 기존 실패로 분류한다.
- `TC Merge Gate / Check TC PRs` 실패는 테스트 실패가 아니다. TC 브랜치 동기화 봇이 만든 TC PR 두 개가
  아직 열려 있어서 gate가 막은 것이다. 이 PR은 TC 변경이 필요하지 않다.
- 한계: report gate 결과는 `warning`이다. `test_sql`과 `test_sql_by_cci`는 collector가 validated
  summary를 만들지 못했다. 이 두 suite의 비교는 raw job log와 `failed.list`에서 읽은 것이다.
  validated summary 기반의 결론은 아니다.
- 다음 조치: 코드 수정은 필요하지 않다. 현재 head로 failure-only rerun을 하면 test_shell과 test_sql은
  다시 실패한다(원인 A 참고). PR을 현재 develop(`98b892cf49` 이후)로 rebase하고, `tc/pr-8495` 두 브랜치를
  TC develop에 맞춘 뒤 `/run all`을 돌려야 한다. TC PR 두 개는 사람이 닫는다.

## 분석 범위

| 항목 | 값 |
| --- | --- |
| PR | https://github.com/CUBRID/cubrid/pull/8495 |
| Head | `6a7ca6b4a89e5dd96bfea81b9f6655893641b9a7` |
| Merge base (develop tip) | `2d1513a8afe6c843388e916fcdf34483b78a2051` |
| Head run | gha-ci run 43163141709 attempt 1 |
| Baseline run | gha-ci run 43047833612 attempt 1 |
| TC Merge Gate run | 43171996710 |
| 수집 시각 | 2026-11-12T08:37Z (head), 2026-11-12T08:38Z (baseline) |
| Collector | cubrid-ci 0.2.0 (5141d5bf05ed, release) |
| Evidence | `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8495/6a7ca6b4a8.../` |
| Verify assessment | identity established, observation incomplete, manifest validated, summaries partial |
| Report mode | `warning`, `regression_conclusions_allowed: false` |

## Suite 상태

| Suite | CI verdict | Collector state | Failure 수 | Baseline |
| --- | --- | --- | --- | --- |
| test_medium | SUCCESS | validated | 0 | validated |
| test_shell | FAILURE | validated | 2 / 3584 (skipped 30) | validated, 같은 2건 |
| test_sql | FAILURE | collection_failed | 3 (raw `failed.list`) | collection_failed, 같은 3건 (raw) |
| test_sql_by_cci | FAILURE | job_level_failure | 52 case (raw log) | collection_failed, 53 case (raw) |
| Check TC PRs | FAILURE | 해당 없음 | gate | 해당 없음 |

`test_sql` collection_failed 원인: shard 01 JUnit이 summary_info보다 17 case 적다
(summary_info 3548/0/0, JUnit 3531/0/0). 누락 case는 `sql/_05_plcsql/.../cbrd-27556`,
`cbrd-27584`, `cbrd-27633`이다. baseline에서도 같은 integrity 오류가 나므로 collector 또는 CTP 결과
파일 문제이다. shard 01의 실패 수는 양쪽 모두 0이다.

`test_sql_by_cci` job_level_failure 원인: shard 09에 JUnit XML이 없다. shard 09는 서버 crash 뒤
case마다 `cci_connect` 대기를 반복하다 취소되었다.

## 실패 목록과 baseline 비교

| Suite | Testcase | 증상 | Baseline | PR 관련성 | 신뢰도 |
| --- | --- | --- | --- | --- | --- |
| test_shell | `shell/_40_guava/cbrd_27236_merge/cases/cbrd_27236_merge.sh` | `index_build_merge_fanin` 파라미터를 엔진이 모른다. NOK 24줄 | also_observed_on_base, NOK 24줄 같음 | unlikely | high |
| test_shell | `shell/_36_damson/cbrd_23608_tde/temp_enc_08/cases/temp_enc_08.sh` | `file_create` temporary 파일 수가 answer와 다르다 | also_observed_on_base, NOK 4줄 같음 | unlikely | high |
| test_sql | `sql/_36_guava/cbrd_27236/cases/cbrd_27236_01_fanin.sql` | NOK, shard 09 | also_observed_on_base | unlikely | medium (raw) |
| test_sql | `sql/_36_guava/cbrd_27236/cases/cbrd_27236_02_unique.sql` | NOK, shard 09 | also_observed_on_base | unlikely | medium (raw) |
| test_sql | `sql/_36_guava/cbrd_27236/cases/cbrd_27236_03_long_keys.sql` | NOK, shard 09 | also_observed_on_base | unlikely | medium (raw) |
| test_sql_by_cci | 48 case (shard 03, 04, 05, 06, 07, 09) | 결과 불일치와 shard 09 서버 crash | also_observed_on_base | unlikely | medium (raw) |
| test_sql_by_cci | `sql/_36_guava/cbrd_27510/cases/18`–`21` (4 case) | `CUBRID server is not available, waiting for recovery` | additional_on_head | unlikely | medium |
| Check TC PRs | 해당 없음 | `TC Merge Gate FAILED — TC changes are not on TC develop yet` | 해당 없음 | 해당 없음 (gate) | high |

`test_sql_by_cci` 대조: head NOK 52 case, base NOK 53 case. head에만 있는 case는 `cbrd_27510` 4개뿐이다.
4개 모두 shard 09 crash 뒤 서버가 없어서 실패했다. 실패 내용은 testcase 동작이 아니라 연결 불가다.
base에만 있는 case(base_only)는 5개다. crash 뒤에 남은 case가 run마다 달라서 생긴 차이로 본다(추론).

## 원인별 분석

### A. 테스트가 엔진보다 앞선 CBRD-27236 testcase

- 관찰: shell `cbrd_27236_merge`의 서버 시작이 `The 'index_build_merge_fanin' parameter ... Unrecognized keyword`로
  실패한다. sql `cbrd_27236_*` 3 case도 NOK이다. 같은 실패가 develop `2d1513a8af`에서도 난다.
- 관찰: `tc/pr-8495`의 분기점은 두 TC 저장소 모두 CBRD-27236 TC 커밋 이후다. private-ex의 분기점은
  `90f15f0c8c6c` "[CBRD-27236] Add shell testcases for the merge and the temp space of an index build,
  and update the answer of temp_enc_08 (#4687)"다. 이 커밋이 temp_enc_08 answer도 바꿨다.
- 관찰: CBRD-27236 엔진 변경 `4255a337dd` (#8358)는 merge-base `2d1513a8af` 이후에 develop에 들어왔다.
  `origin/develop`의 `src/base/system_parameter.c`에는 `index_build_merge_fanin`이 있다.
- 추론: 이 PR의 엔진은 CBRD-27236 이전이고, testcase는 CBRD-27236 이후다. 그래서 shell 2건과 sql 3건이 실패한다.
  B의 temp_enc_08도 같은 원인이다(answer가 CBRD-27236 동작 기준으로 바뀜).
- 반증 조건: develop tip run에서 이 case가 통과하는데 PR head에서만 실패하면 이 판단은 틀린다.
- 조치: PR을 현재 develop으로 rebase하면 해소될 것으로 본다(추정, rebase 뒤 run으로 확인).

### B. temp_enc_08의 temporary 파일 생성 수

- 관찰: answer보다 temporary `file_create` 출력이 더 많다. NOK 수와 위치가 base와 같다.
- 추론: 원인 A와 같다. TC 커밋 #4687이 CBRD-27236 엔진 동작 기준으로 answer를 바꿨다.
  이 PR은 commit postpone 로그 flush만 바꾸고 temp 파일 생성 경로는 건드리지 않는다.
- 반증 조건: base에서 통과하는 run이 반복해서 나오고 head에서만 실패하면 다시 본다.
- 조치: PR 조치는 없다.

### C. test_sql_by_cci 결과 불일치와 shard 09 `log_fetch_from_archive` FATAL

- 관찰: shard 09 서버가 05:57:13Z, `cbrd_27482_coalesce.sql`이 OK로 끝난 직후 실행 중에
  `LOG FATAL ERROR: log_fetch_from_archive`로 죽었다. 이후 재시작마다 recovery가
  `Unable to mount disk volume ".../basic_lgar000"`로 실패했다.
- 관찰: 같은 FATAL이 retained evidence 4개에 있다. merge-base develop run 43047833612의 test_sql_by_cci
  (`cbrd_27469` 부근), PR #8416 run 42865557030의 test_sql(`cbrd_27478` 부근), PR #8299 run 42801815682의 test_sql이다.
- 관찰: `cubrid-tcr check --job "shard sql_by_cci 09"`의 verdict는 `known`, 규칙은 `sql-by-cci-every-branch`다.
  이 규칙에는 tracking issue가 없다.
- 추론: 이 PR의 diff를 적용하지 않은 develop에서도 같은 FATAL이 나므로 원인은 이 PR 이전에 있다.
  `_36_guava` 구간의 어떤 testcase나 그 구간에서 도는 작업이 archive 없는 상태에서 오래된 로그를 읽는다고 본다(추측).
- 미확인: 서버 error log(`basic_20261112_1450.err`)는 artifact로 남지 않아서 stack을 확인하지 못했다.
- 반증 조건: develop의 반복 run에서 이 FATAL이 없고, PR head에서만 반복되면 PR 관련성을 다시 본다.
  특히 postpone 실행이 아직 log buffer로 옮겨지지 않은 레코드를 읽는 경로가 있는지 확인해야 한다.
- 조치: 이 PR의 코드 수정 근거는 없다. 이 FATAL 자체는 develop의 별도 결함이므로 이슈로 추적할 가치가 있다.

### D. TC Merge Gate

- 관찰: run 43171996710이 `TC changes are not on TC develop yet`으로 실패했다.
- 추론: TC Branch Sync 봇이 만든 `tc/pr-8495` PR 두 개가 열려 있기 때문이다.
- 조치: 이 PR은 TC 변경이 필요하지 않다. 사람이 TC PR 두 개를 닫으면 gate를 다시 돌린다.
  TC PR을 닫기 전에는 rerun해도 다시 실패한다.

## Testcase 이력

`cubrid-tcr check --case` 출력은 JSON parse에 실패해서 testcase별 이력을 얻지 못했다. 이력 결론은 없다.
merge-base 비교와 retained evidence 검색만 근거로 쓴다.

## 우선순위 조치

1. failure-only rerun은 현재 head에서 효과가 없다. `cubrid-pr-tc-base-check --pr 8495`도 실패했다
   (두 TC 브랜치 모두 최신 TC develop을 포함하지 않음). PR을 develop으로 rebase하고 TC 브랜치를 맞춘 뒤 `/run all`을 돌린다.
2. 사람이 TC PR 두 개를 닫은 뒤 TC Merge Gate를 다시 돌린다.
3. 별도 작업: `log_fetch_from_archive` FATAL(`_36_guava`, develop 재현)을 이슈로 등록하고 server error log를 확보한다.
4. 별도 작업: collector의 test_sql shard 01 JUnit/summary_info 불일치(17 case)를 확인한다.

## Evidence 파일

- Head bundle: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8495/6a7ca6b4a89e5dd96bfea81b9f6655893641b9a7/`
- Baseline bundle: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/2d1513a8afe6c843388e916fcdf34483b78a2051/`
- Shard 09 crash log: job 130999512218 (`gh run view -R CUBRID/cubrid --job 130999512218 --log`)
