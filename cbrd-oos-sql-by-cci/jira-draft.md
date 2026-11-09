# [OOS] feature/oos-merge에서 새 CI suite test_sql_by_cci를 통과시킨다

**한 줄 요약**: 새로 도입된 gha-ci suite `test_sql_by_cci`에서 `feature/oos-merge`만 실패하는 28개 case를 없애, feature merge PR #7990이 develop과 같은 기준으로 CI를 통과하게 한다.

- 상위 이슈: CBRD-26978
- 권장 JIRA type: Task (CI 통과를 위한 branch 동기화와 확인 작업)

## Issue Triage

**이슈 수행 목적**: `feature/oos-merge`의 `test_sql_by_cci` 결과에서 develop에도 있는 실패를 뺀 나머지가 0개가 되게 한다. 남는 실패가 있으면 그것만 OOS 작업으로 분리한다.

**이슈 수행 이유**: 2026-11-06부터 gha-ci가 `cubrid-testcases/sql`을 CCI driver로 실행하는 `test_sql_by_cci`를 실행한다. PR #8434(base `feature/oos-merge`)의 `/run all`에서 이 suite만 실패했다(57개 case). 이 중 28개는 develop 기반 PR run 6개에서 모두 통과한다. #7990을 develop에 merge하려면 이 28개를 설명하고 없애야 한다.

**영향**: OOS 개발자와 #7990 reviewer가 영향을 받는다. 28개가 남아 있으면 #7990의 CI 결과에서 develop 공통 실패와 OOS 고유 실패를 구분하기 어렵다. 분석 결과 28개 모두 develop 미동기화로 설명되며, OOS 기능 결함을 보여 주는 case는 확인되지 않았다. 이 판단은 develop을 merge한 뒤의 재실행으로 확인해야 한다.

**이슈 수행 방안**: TBD - ANALYSIS 단계에서 해결 방안과 구현 범위를 결정한다.

---

## AI-Generated Context

## Description

`test_sql_by_cci`는 SQL testcase를 csql 대신 CCI driver로 실행하고, `.answer_cci`가 있으면 그것을, 없으면 `.answer`를 기대 결과로 쓴다. 이 suite는 develop에서도 아직 실패한다. 비교한 develop 기반 PR run 6개에서 31-49개 case가 실패했다. 그래서 `feature/oos-merge`의 실패에서 develop 공통 실패를 먼저 빼야 OOS 쪽 작업 범위가 보인다.

PR #8434 run 42562225722(엔진 `0034bc2fb`, testcase `tc/pr-8434` `e61878fb7`)의 실패 57개를 develop 기반 PR run 6개와 비교한 결과는 다음과 같다.

| 분류 | 수 | 설명 |
|---|---|---|
| develop에서도 실패 | 29 | 이 이슈의 범위가 아니다. `test_sql_by_cci` 도입 작업에서 다룬다. |
| `feature/oos-merge`에서만 실패 | 28 | 아래 두 묶음이다. |
| 불명확 | 0 | |

### feature/oos-merge에서만 실패하는 28개

**묶음 1: testcase answer가 오래됨 (18개).** OOS 엔진의 실제 출력이 develop testcase의 answer와 줄 단위로 같다. `feature/oos-merge` testcase branch의 `.answer_cci`만 옛 값이다. develop testcase는 2026-10-27 commit `ab02108cd`([CBRD-27510] cci answer 수정)에서 이 파일들을 바꿨고, `feature/oos-merge` testcase branch에는 이 commit이 없다.

- `_13_issues/_14_1h/cases/bug_bts_13653.sql`
- `_13_issues/_14_1h/cases/bug_bts_13916.sql`
- `_13_issues/_15_1h/cases/bug_bts_16039.sql`
- `_23_apricot_qa/_01_sql_extension3/_05_analytic_functions/_14_avg/cases/` 의 `avg_constraints.sql`, `avg_null.sql`, `avg_numeric.sql`
- `_26_features_920/issue_11087_median/cases/` 의 `11087_1.sql`, `11087_3.sql`
- `_27_banana_qa/issue_11088_percentile_cont/` 의 `_01_aggregate_function/cases/_03_character_string1.sql`, `_03_character_string2.sql`, `_02_analytic_function/cases/p_cont_bit_lob.sql`, `p_cont_character_string.sql`, `p_cont_partition_list.sql`
- `_27_banana_qa/issue_11089_percentile_disc/` 의 `_01_aggregate_function/cases/_03_character_string1.sql`, `_03_character_string2.sql`, `_02_analytic_function/cases/p_disc_bit_lob.sql`, `p_disc_character_string.sql`, `p_disc_partition_list.sql`

**묶음 2: CCI 경로에서만 결과 type이 다름 (10개).** 같은 run의 `test_sql`(csql)은 같은 엔진과 같은 answer로 10개 모두 통과한다. CCI로 실행할 때만 숫자 표기(`7.000` 대 `7.0`), boolean 표기(`true` 대 `18`), 에러 코드(`-621` 대 `-176`)가 다르다. 2026-11-05 이후 develop을 base로 하는 엔진은 CCI로도 모두 통과한다.

- `_13_issues/_26_2h/cases/` 의 `cbrd_27327.sql`, `cbrd_27504.sql`, `cbrd_27668.sql`
- `_36_guava/cbrd_27510/cases/` 의 `07_scope_once_conversion.sql`, `08_to_number_domain.sql`, `13_compare_outside_terms.sql`, `14_index_key_probes.sql`, `23_unresolved_domain_axes.sql`, `25_string_constant_over_bind_sum.sql`, `29_analytic_string_first_value.sql`

원인 후보는 merge base(`4781495f0`, 2026-10-26) 이후 develop commit `52193efa9` [CBRD-27583] "Eliminate server-side runtime type resolve with bind-type-keyed xasl"이다. CCI는 broker의 prepare가 알려준 column type으로 값을 받으므로, prepare type과 실행 type이 다르면 CCI 출력만 달라진다. 이 귀속은 commit 범위와 변경 내용에서 추론한 것이며 bisect로 확인하지 않았다.

이 10개는 작은 숫자, 날짜, 짧은 문자열 column을 쓴다. OOS가 heap 밖에 저장하는 큰 record가 아니다. `feature/oos-merge`의 merge base 이후 변경에는 broker, `db_vdb.c`, `object_domain.c` 변경이 없다.

### ANALYSIS에서 확인할 것

- develop 엔진과 develop testcase를 `feature/oos-merge`에 merge한 뒤 #7990에서 `test_sql_by_cci`를 다시 실행했을 때, develop에서 통과하고 `feature/oos-merge`에서만 실패하는 case가 남는가. 남는 case만 OOS 결함으로 분석한다.
- 묶음 2가 develop merge 뒤에도 남으면 CBRD-27583 귀속은 틀린 것이다. 그때는 OOS 엔진의 CCI 경로를 직접 분석한다.

### 완료 조건

- #7990의 `test_sql_by_cci` 실패 목록이 같은 시점 develop 기반 run의 실패 목록에 모두 포함된다.
- 포함되지 않는 case가 있으면 각 case의 원인과 담당 이슈가 기록되어 있다.

### 근거

- 분석 보고서: my-cubrid-docs `cbrd-oos-sql-by-cci/report.md` (run, commit, case별 diff 요약 포함)
- 비교한 develop 기반 run: 42561576358 (#8356), 42561491148 (#8359), 42559330339 (#8316), 42558914847 (#8449), 42549533432 (#8451), 42560787750 (#8433)
