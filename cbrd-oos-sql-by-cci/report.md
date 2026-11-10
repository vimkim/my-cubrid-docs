# feature/oos-merge의 test_sql_by_cci 실패 분류

작성: 2026-11-09 (Asia/Seoul). 대상: PR [CUBRID/cubrid#8434](https://github.com/CUBRID/cubrid/pull/8434) gha-ci run [42562225722](https://github.com/CUBRID/cubrid/actions/runs/42562225722).
관련: feature merge PR [CUBRID/cubrid#7990](https://github.com/CUBRID/cubrid/pull/7990), 상위 이슈 CBRD-26978.

> **2026-11-10 갱신.** develop 동기화 뒤 다시 실행한 결과, `feature/oos-merge`에서만 실패하는 case는 0개이다. 자세한 내용은 아래 "develop 동기화 결과"에 있다. JIRA 등록은 필요 없다.

## 질문과 결론

질문은 새 CI suite `gha-ci: test_sql_by_cci`의 실패 중 무엇을 `feature/oos-merge`가 스스로 고쳐야 하는가이다.
develop에서도 실패하는 case는 OOS 작업이 아니다.

결론은 다음과 같다.

| 분류 | 수 | 뜻 |
|---|---|---|
| (a) develop에서도 실패 | 29 | 비교한 develop run 6개 중 1개 이상에서 같은 case가 실패한다. |
| (b) `feature/oos-merge`에서만 실패 | 28 | 비교한 develop run 6개 모두에서 통과한다. |
| (c) 불명확 | 0 | 해당 없음. |

(b) 28개 중 OOS 코드가 원인으로 보이는 case는 없다.
(b)는 모두 `feature/oos-merge`가 2026-10-26 이후 develop을 받지 않아서 생긴 차이로 설명된다.

- **(b1) 18개: testcase answer가 오래됨.** OOS run의 실제 출력 줄이 develop testcase의 answer에 모두 들어 있다. 엔진 출력은 develop과 같고, `feature/oos-merge` testcase branch의 `.answer_cci`만 옛 값이다. develop testcase는 2026-10-27 commit `ab02108cd` ([CBRD-27510] cci answer 수정)에서 이 answer들을 바꿨다.
- **(b2) 10개: CCI 경로의 엔진 결과가 develop과 다름.** 같은 run의 `test_sql`(csql)은 같은 엔진, 같은 answer로 10개 모두 통과한다. CCI로 실행할 때만 결과 type의 표기나 에러 코드가 다르다. develop 엔진(2026-11-05 이후 base)에서는 CCI로도 통과한다. 원인 후보는 merge base 이후 develop commit `52193efa9` ([CBRD-27583] Eliminate server-side runtime type resolve with bind-type-keyed xasl)이다. 이 귀속은 commit 범위와 변경 내용에서 추론한 것이며, bisect로 확인하지 않았다.

따라서 필요한 조치는 OOS 코드 수정이 아니라 develop 동기화이다.
`feature/oos-merge`에 develop 엔진과 develop testcase를 merge한 뒤 다시 실행한다.
그 뒤에도 남는 (b) case만 OOS 작업으로 다룬다.

PR #7990에 `/run`은 올리지 않았다. 지금 #7990을 실행하면 동기화되지 않은 같은 branch를 다시 시험하므로, 분류를 바꿀 정보가 나오지 않는다.

## 비교한 run과 commit

`feature/oos-merge`와 develop의 merge base는 `4781495f0` (2026-10-26, [CBRD-27307])이다.
`test_sql_by_cci`는 develop `2d928e34b` (2026-11-06, [CUBRIDQA-1709])부터 실행되었다. 그래서 merge base 근처의 develop run은 없다.
develop push run은 build만 하고 test shard를 건너뛴다. 그래서 develop을 base로 하는 PR run을 baseline으로 썼다.

| run | PR | 엔진 SHA (PR head) | 엔진의 develop/feature base | testcase SHA (branch) | 실패 수 |
|---|---|---|---|---|---|
| [42562225722](https://github.com/CUBRID/cubrid/actions/runs/42562225722) | #8434 (base `feature/oos-merge`) | `0034bc2fb` | `95ff126a8` (feature, 2026-11-06) | `e61878fb7` (`tc/pr-8434`) | 57 |
| [42561576358](https://github.com/CUBRID/cubrid/actions/runs/42561576358) | #8356 | `1f5026996` | `e98bdd885` (2026-11-05) | `6463c3e16` (`tc/pr-8356`) | 31 |
| [42561491148](https://github.com/CUBRID/cubrid/actions/runs/42561491148) | #8359 | `2e3cbe125` | `53d6bdfd2` (2026-11-09) | `0667da638` (`tc/pr-8359`) | 36 |
| [42559330339](https://github.com/CUBRID/cubrid/actions/runs/42559330339) | #8316 | `f34cf3ab9` | `53d6bdfd2` (2026-11-09) | `7608f3e7b` (`tc/pr-8316`) | 34 |
| [42558914847](https://github.com/CUBRID/cubrid/actions/runs/42558914847) | #8449 | `c958d19ad` | `063d84e53` (2026-11-09) | `f5471c7d2` (`tc/pr-8449`) | 33 |
| [42549533432](https://github.com/CUBRID/cubrid/actions/runs/42549533432) | #8451 | `70c3ee928` | `063d84e53` (2026-11-09) | `4ea72cf8c` (`tc/pr-8451`) | 33 |
| [42560787750](https://github.com/CUBRID/cubrid/actions/runs/42560787750) | #8433 | `debffec88` | `953e83256` (2026-11-06) | `f9e5170b4` (`tc/pr-8433`) | 49 |

모든 run은 `sql_by_cci` 10 shard를 모두 끝냈고 release build를 썼다. develop run 6개의 실패 case 합집합은 55개이다.

`tc/pr-8434`는 `feature/oos-merge` testcase branch(`70db22a1c`)에 초기화 commit 1개를 더한 것이다. 이 branch는 develop testcase보다 110 commit 뒤처져 있다(GitHub compare 기준, 2026-11-09).

## 방법

1. 각 run의 실패 shard log에서 `Case Name:` 다음 `Test Result: NOK`로 끝나는 block을 뽑아 실패 목록을 만들었다. OOS run의 결과는 브리프의 shard별 수(01:6, 03:9, 04:1, 05:3, 06:3, 07:14, 09:21, 합계 57)와 같다.
2. log는 결과를 공백으로 지운다. 그래서 각 shard가 내부 evidence server에 올린 JUnit XML(`linux_sql_by_cci_64bit_release.xml`)에서 statement별 diff를 읽었다. XML의 실패 수는 log의 실패 수와 7개 run 모두 같다.
3. OOS run의 실패 case가 develop run 6개 중 하나에서라도 실패하면 (a), 6개 모두에서 통과하면 (b)로 나눴다. 6개 run 모두 해당 case를 실행했고, 통과(`ok`)로 기록했다.
4. (b) 각 case에 대해 OOS run의 실제 출력 줄(diff의 `+` 줄)이 develop testcase answer(`6463c3e16` 기준)에 있는지 확인했다. 모두 있으면 (b1), 아니면 (b2)로 나눴다.
5. (b2) 10개는 같은 OOS run의 `test_sql` shard XML에서 판정을 확인했다. 10개 모두 `ok`였다.
6. (a) 29개는 OOS run과 develop run의 diff 줄을 비교했다. 10개는 diff가 같고, 19개는 다르다. 다른 19개는 아래 "(a) 중 signature가 다른 case"에서 따로 확인했다.

cubrid-ci 0.2.0의 collector는 `sql_by_cci` suite를 지원하지 않는다. 그래서 위 절차는 GitHub job log와 evidence server 파일을 직접 읽었고, collector의 manifest 검증은 거치지 않았다.

## (b2)가 OOS 때문이 아니라고 보는 근거

관찰:

- 같은 OOS 엔진 `0034bc2fb`, 같은 testcase `e61878fb7`에서 csql 경로(`test_sql`)는 10개 모두 통과하고, CCI 경로(`test_sql_by_cci`)는 10개 모두 실패한다.
- 차이는 결과 값의 type 표기(`7.000` 대 `7.0`, `2.25` 대 `2.2500000000000000`), boolean 표기(`true` 대 `18`), 에러 코드(`-621` ER_QSTR_INVALID_DATA_TYPE 대 `-176` ER_DATE_CONVERSION)이다. 저장된 값 자체가 바뀐 줄은 없다.
- 관련 table의 column은 작은 숫자, 날짜, 짧은 문자열이다. OOS는 큰 record의 column을 heap 밖에 저장하는 기능이므로 이 case들의 record에는 적용되지 않는다.
- `4781495f0..origin/feature/oos-merge`의 commit은 OOS 작업과 develop merge뿐이다. `src/broker`, `src/compat/db_vdb.c`, `src/object/object_domain.c`에는 변경이 없다. parser 변경은 OOS용 문법(`STORAGE`, `OOS`, `PREFER_INLINE` 등)과 `show_meta.c`이다. `src/query/query_executor.c` 변경은 update, delete, replace의 OOS record 쓰기 경로이다.
- base가 2026-11-05 이후인 develop 엔진 6개는 모두 CCI로도 통과한다. merge base `4781495f0`부터 가장 오래된 base `e98bdd885`까지 develop first-parent commit은 87개이다.

추론:

- 이 87개 중 `52193efa9` [CBRD-27583]은 prepare 시점의 결과 type을 bind type별 XASL로 고정하고, server의 runtime type 결정을 없앤다. 변경 파일에 `src/broker/cas_execute.c`, `src/compat/db_vdb.c`, `src/object/object_domain.c`가 들어 있다. CCI는 모든 statement를 broker의 prepare/execute로 실행하고, prepare가 알려준 column type으로 값을 받는다. 그래서 prepare type과 실행 type이 다르면 CCI 출력만 달라질 수 있다. 이 설명은 (b2)의 증상과 맞는다.
- 반증 조건: develop을 merge한 `feature/oos-merge`에서도 이 10개가 CCI로 실패하면 이 추론은 틀리다. 그때는 해당 case를 OOS 엔진 문제로 다시 본다.

## (a) 중 signature가 다른 case

(a) 29개 중 19개는 OOS run의 diff가 develop run의 diff와 다르다. 차이의 출처는 아래와 같고, 모두 branch 간 develop 차이로 설명된다.

- `cbrd_27510` 10개, `cbrd_27503`: 두 branch의 answer가 서로 반대 방향이다. OOS run은 answer `1.5`, 실제 `1.5000000000000000`이고, develop run은 answer `1.5000000000000000`, 실제 `1.5`이다. 두 branch 모두 실패한다.
- `cbrd_23665`, `cbrd_25447`, `cbrd_26431`, `hash_agg_query_profile`, `join_orderby_skip`: plan/profile 출력 차이이다. develop 엔진은 `groups (est.)` 같은 새 항목을 출력하고 OOS 엔진은 출력하지 않는다.
- `11087.sql`, `percentile_cont/_00_from_dev.sql`, `percentile_disc/_00_from_dev.sql`: develop과 공통인 숫자 표기 차이 외에, OOS run에만 `Error:-181`(ER_TP_CANT_COERCE) 대신 `Error:-1118`(ER_ARG_CAN_NOT_BE_CASTED_TO_DESIRED_DOMAIN)이 나오는 statement가 있다. 대상은 `median(c13)`이고 `c13`은 `varchar(255)`에 `'1.0'` 같은 짧은 값이 들어 있다. OOS 저장 경로가 쓰이지 않는 record이고, 같은 run의 `test_sql`은 이 case를 통과한다. 그래서 (b2)와 같은 CCI 경로 type 처리 차이로 본다. develop 동기화 뒤 다시 확인할 대상이다.

## 실패 목록

"develop 실패 횟수"는 develop run 6개 중 실패한 수이다. "실패 signature"는 OOS run의 diff 줄이 develop run 중 하나와 같은지를 뜻한다. "차이 유형"은 diff 문자열로 자동 분류한 참고값이다.

### (a) develop에서도 실패 (29)

| # | shard | testcase | develop 실패 횟수 (6회 중) | 실패 signature | 차이 유형 (자동 분류, 참고) |
|---|---|---|---|---|---|
| 1 | 01 | `_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/04_normal_percent_type_parameter.sql` | 2 | 동일 | 숫자·시간 표기(scale) |
| 2 | 01 | `_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/05_error_percent_type_return.sql` | 2 | 동일 | 기타 결과 차이 |
| 3 | 01 | `_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/05_normal_percent_type_return.sql` | 2 | 동일 | 숫자·시간 표기(scale) |
| 4 | 01 | `_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/24_normal_viewtable_percent_type_parameter.sql` | 2 | 동일 | 숫자·시간 표기(scale) |
| 5 | 01 | `_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/25_error_viewtable_percent_type_return.sql` | 2 | 동일 | 기타 결과 차이 |
| 6 | 01 | `_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/25_normal_viewtable_percent_type_return.sql` | 2 | 동일 | 숫자·시간 표기(scale) |
| 7 | 03 | `_13_issues/_20_2h/cases/cbrd_23665.sql` | 2 | 다름 | 기타 결과 차이 |
| 8 | 03 | `_14_mysql_compatibility_2/_04_table_related/_02_alter_change_column/_11_trigger/cases/1101.sql` | 2 | 동일 | 기타 결과 차이 |
| 9 | 03 | `_14_mysql_compatibility_2/_15_host_variable/_12_common/cases/agg_group_by.sql` | 6 | 동일 | 숫자·시간 표기(scale) |
| 10 | 04 | `_17_sql_extension2/_02_full_test/_03_alter_table/_01_alter_change/cases/alter_change_026.sql` | 6 | 동일 | 기타 결과 차이 |
| 11 | 06 | `_26_features_920/issue_11087_median/cases/11087.sql` | 5 | 다름 | 숫자 표기 + 에러 코드(-181→-1118) |
| 12 | 07 | `_27_banana_qa/issue_11088_percentile_cont/_01_aggregate_function/cases/_00_from_dev.sql` | 5 | 다름 | 숫자 표기 + 에러 코드(-181→-1118) |
| 13 | 07 | `_27_banana_qa/issue_11089_percentile_disc/_01_aggregate_function/cases/_00_from_dev.sql` | 5 | 다름 | 숫자 표기 + 에러 코드(-181→-1118) |
| 14 | 07 | `_27_banana_qa/issue_16066_BINARY_charset/_00_String_Functions_and_Operators/cases/rtrim_002.sql` | 6 | 동일 | 기타 결과 차이 |
| 15 | 07 | `_28_features_930/issue_13133_hash_query_profile/cases/hash_agg_query_profile.sql` | 2 | 다름 | plan/profile 출력 |
| 16 | 09 | `_36_guava/cbrd_25447/cases/cbrd_25447.sql` | 2 | 다름 | plan/profile 출력 |
| 17 | 09 | `_36_guava/cbrd_26258/cases/join_orderby_skip.sql` | 6 | 다름 | plan/profile 출력 |
| 18 | 09 | `_36_guava/cbrd_26431/cases/cbrd_26431.sql` | 2 | 다름 | plan/profile 출력 |
| 19 | 09 | `_36_guava/cbrd_27397/cases/cbrd_27397.sql` | 2 | 동일 | plan/profile 출력 |
| 20 | 09 | `_36_guava/cbrd_27503/cases/cbrd_27503.sql` | 5 | 다름 | 숫자·시간 표기(scale) |
| 21 | 09 | `_36_guava/cbrd_27510/cases/01_fetch_gate_probes.sql` | 5 | 다름 | 숫자·시간 표기(scale) |
| 22 | 09 | `_36_guava/cbrd_27510/cases/02_fetch_gate_bind_reads.sql` | 5 | 다름 | 숫자·시간 표기(scale) |
| 23 | 09 | `_36_guava/cbrd_27510/cases/03_session_variable_types.sql` | 5 | 다름 | 숫자·시간 표기(scale) |
| 24 | 09 | `_36_guava/cbrd_27510/cases/05_common_value_constants.sql` | 5 | 다름 | 숫자·시간 표기(scale) |
| 25 | 09 | `_36_guava/cbrd_27510/cases/06_precast_plan.sql` | 5 | 다름 | 숫자·시간 표기(scale) |
| 26 | 09 | `_36_guava/cbrd_27510/cases/10_list_aggregate_probes.sql` | 5 | 다름 | 숫자·시간 표기(scale) |
| 27 | 09 | `_36_guava/cbrd_27510/cases/11_analytic_interpolation_keys.sql` | 5 | 다름 | 숫자·시간 표기(scale) |
| 28 | 09 | `_36_guava/cbrd_27510/cases/20_conversion_contract.sql` | 5 | 다름 | 숫자·시간 표기(scale) |
| 29 | 09 | `_36_guava/cbrd_27510/cases/24_sum_avg_date_argument.sql` | 5 | 다름 | 숫자·시간 표기(scale) |

### (b1) feature/oos-merge testcase answer가 develop보다 오래됨 (18)

판정 근거: OOS 실제 출력 줄이 develop answer에 모두 있음.

| # | shard | testcase | 기대 파일 | 대표 차이 (answer → actual) |
|---|---|---|---|---|
| 1 | 03 | `_13_issues/_14_1h/cases/bug_bts_13653.sql` | `bug_bts_13653.answer_cci` | `123.0000000000000000 123.0000000000000000 1.0` → `123.0 123.0 1.0000000000000000 1.000000000000` |
| 2 | 03 | `_13_issues/_14_1h/cases/bug_bts_13916.sql` | `bug_bts_13916.answer_cci` | `11.0000000000000000` → `11.0` |
| 3 | 03 | `_13_issues/_15_1h/cases/bug_bts_16039.sql` | `bug_bts_16039.answer_cci` | `1.0000000000000000` → `1.0` |
| 4 | 05 | `_23_apricot_qa/_01_sql_extension3/_05_analytic_functions/_14_avg/cases/avg_constraints.sql` | `avg_constraints.answer_cci` | `111.110001 11111.13 8000.0 111.209500504` → `111.110001 11111.13 8000.0 111.209500122` |
| 5 | 05 | `_23_apricot_qa/_01_sql_extension3/_05_analytic_functions/_14_avg/cases/avg_null.sql` | `avg_null.answer_cci` | `null 300 50000000 12345.06789 111.230003 1111` → `null 300 50000000 12345.06789 111.230003 1111` |
| 6 | 05 | `_23_apricot_qa/_01_sql_extension3/_05_analytic_functions/_14_avg/cases/avg_numeric.sql` | `avg_numeric.answer_cci` | `200 12345.06789 111.160004 111.210006714` → `200 12345.06789 111.160004 111.210002899` |
| 7 | 06 | `_26_features_920/issue_11087_median/cases/11087_1.sql` | `11087_1.answer_cci` | `9.5000000000000000` → `9.5` |
| 8 | 06 | `_26_features_920/issue_11087_median/cases/11087_3.sql` | `11087_3.answer_cci` | `179769313486231570814527423731704356798070567` → `1.797693e+308` |
| 9 | 07 | `_27_banana_qa/issue_11088_percentile_cont/_01_aggregate_function/cases/_03_character_string1.sql` | `_03_character_string1.answer_cci` | `This is a cat. 19.0000000000000000` → `This is a cat. 19.0` |
| 10 | 07 | `_27_banana_qa/issue_11088_percentile_cont/_01_aggregate_function/cases/_03_character_string2.sql` | `_03_character_string2.answer_cci` | `This is a cat. 0.5000000000000000` → `This is a cat. 0.5` |
| 11 | 07 | `_27_banana_qa/issue_11088_percentile_cont/_02_analytic_function/cases/p_cont_bit_lob.sql` | `p_cont_bit_lob.answer_cci` | `11111 b00000 2049.1824000000015076` → `11111 b00000 2049.1824` |
| 12 | 07 | `_27_banana_qa/issue_11088_percentile_cont/_02_analytic_function/cases/p_cont_character_string.sql` | `p_cont_character_string.answer_cci` | `0.5 0.7 2222.0000000000000000` → `0.5 0.7 2222.0` |
| 13 | 07 | `_27_banana_qa/issue_11088_percentile_cont/_02_analytic_function/cases/p_cont_partition_list.sql` | `p_cont_partition_list.answer_cci` | `0.32 0.7 0.3200000000000000` → `0.32 0.7 0.32` |
| 14 | 07 | `_27_banana_qa/issue_11089_percentile_disc/_01_aggregate_function/cases/_03_character_string1.sql` | `_03_character_string1.answer_cci` | `This is a cat. 19.0000000000000000` → `This is a cat. 19.0` |
| 15 | 07 | `_27_banana_qa/issue_11089_percentile_disc/_01_aggregate_function/cases/_03_character_string2.sql` | `_03_character_string2.answer_cci` | `This is a cat. 0.5000000000000000` → `This is a cat. 0.5` |
| 16 | 07 | `_27_banana_qa/issue_11089_percentile_disc/_02_analytic_function/cases/p_disc_bit_lob.sql` | `p_disc_bit_lob.answer_cci` | `11111 b00000 123.4560000000000031` → `11111 b00000 123.456` |
| 17 | 07 | `_27_banana_qa/issue_11089_percentile_disc/_02_analytic_function/cases/p_disc_character_string.sql` | `p_disc_character_string.answer_cci` | `0.5 0.7 2222.0000000000000000` → `0.5 0.7 2222.0` |
| 18 | 07 | `_27_banana_qa/issue_11089_percentile_disc/_02_analytic_function/cases/p_disc_partition_list.sql` | `p_disc_partition_list.answer_cci` | `0.32 0.7 0.3200000000000000` → `0.32 0.7 0.32` |

### (b2) feature/oos-merge 엔진의 CCI 경로 결과가 develop과 다름 (10)

판정 근거: answer는 두 branch가 같거나 OOS 출력이 develop answer에 없음.

| # | shard | testcase | 기대 파일 | 대표 차이 (answer → actual) |
|---|---|---|---|---|
| 1 | 03 | `_13_issues/_26_2h/cases/cbrd_27327.sql` | `cbrd_27327.answer` | `499.5 249.75 749 0.501 0.5 4 499500 row-00000` → `499.5000000000000000 249.7500000000000000 749` |
| 2 | 03 | `_13_issues/_26_2h/cases/cbrd_27504.sql` | `cbrd_27504.answer` | `Error:-621` → `Error:-176` |
| 3 | 03 | `_13_issues/_26_2h/cases/cbrd_27668.sql` | `cbrd_27668.answer` | `true` → `18` |
| 4 | 09 | `_36_guava/cbrd_27510/cases/07_scope_once_conversion.sql` | `07_scope_once_conversion.answer` | `27.0 31.5 12.0 2.5` → `27.0000000000000000 31.5000000000000000 12.00` |
| 5 | 09 | `_36_guava/cbrd_27510/cases/08_to_number_domain.sql` | `08_to_number_domain.answer` | `7.000` → `7.0` |
| 6 | 09 | `_36_guava/cbrd_27510/cases/13_compare_outside_terms.sql` | `13_compare_outside_terms.answer` | `1 10 1.00 a` → `1 10 1.0 a` |
| 7 | 09 | `_36_guava/cbrd_27510/cases/14_index_key_probes.sql` | `14_index_key_probes.answer` | `2 2.00` → `2 2.0` |
| 8 | 09 | `_36_guava/cbrd_27510/cases/23_unresolved_domain_axes.sql` | `23_unresolved_domain_axes.answer` | `1 1 2.25` → `1 1 2.2500000000000000` |
| 9 | 09 | `_36_guava/cbrd_27510/cases/25_string_constant_over_bind_sum.sql` | `25_string_constant_over_bind_sum.answer` | `5.0 5.0 6.0` → `5.0000000000000000 5.0 6.0000000000000000` |
| 10 | 09 | `_36_guava/cbrd_27510/cases/29_analytic_string_first_value.sql` | `29_analytic_string_first_value.answer` | `1 3.0` → `1 3.0000000000000000` |


## 다음 조치

1. `feature/oos-merge`에 develop 엔진을 merge한다. 이것으로 (b2) 10개와 (a)의 OOS 쪽 signature 차이가 사라질 것으로 예상한다(추론).
2. `feature/oos-merge` testcase branch에 develop testcase를 merge한다. 이것으로 (b1) 18개가 사라질 것으로 예상한다. `ab02108cd`가 이 18개 answer를 develop 엔진 출력에 맞게 바꿨기 때문이다.
3. 두 merge 뒤 #7990에서 `test_sql_by_cci`를 다시 실행하고 develop run과 같은 방법으로 비교한다. 그때도 develop에서 통과하는데 OOS에서만 실패하는 case가 OOS 작업의 대상이다.
4. (a) 29개는 develop 공통 실패이다. 이 문서의 범위가 아니며 `test_sql_by_cci` 도입 작업(CUBRIDQA-1709 계열)에서 다룬다.

## 추가 표본: PR #8416 (2026-11-10 확인)

`feature/oos-merge`를 base로 하는 PR #8416(엔진 `abd2136f5`, [CBRD-27259] STORAGE FORCE_INLINE)의 run [42573078376](https://github.com/CUBRID/cubrid/actions/runs/42573078376)을 같은 방법으로 비교했다. 실행 17630건 중 61건이 실패했다.

- (b) 28개는 #8416에서도 모두 실패한다. 28개가 한 PR이 아니라 `feature/oos-merge` 전체의 차이라는 분류를 두 번째 표본이 뒷받침한다.
- #8416에만 있는 실패가 4개 있다. `_36_guava/cbrd_25717/cases/`의 `cbrd_25717_null_join_key.sql`, `cbrd_25717_overflow_dependent_list.sql`, `cbrd_25717_overflow_record.sql`과 `_36_guava/cbrd_26719/cases/cbrd_26719_03_probe_overflow_tuple.sql`이다. 모두 기대 결과 대신 `Error:-1388`을 낸다. #8416 엔진 `abd2136f5`에서 -1388은 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`이다(develop 동기화 뒤 번호는 -1393). 즉 #8416에서는 이 case들의 큰 record가 OOS로 나가지 못하고 저장 한도를 넘는다. 같은 4개는 #8434 run과 develop run 6개에서 모두 통과한다. 그래서 #8416의 변경 자체에서 온 실패일 가능성이 크다(추론). 이 4개는 #8416에서 다룰 일이며 이 문서의 (b) 집합에 넣지 않는다.

## develop 동기화 결과 (2026-11-10)

### 동기화한 commit

| 저장소 | `feature/oos-merge` 이전 | 이후 | 내용 |
|---|---|---|---|
| CUBRID/cubrid | `95ff126a8` | `dcf38cb0a` | develop `1b2645925` merge(`336bfe814`), page batch OOS 수정(`dcf38cb0a`) |
| CUBRID/cubrid-testcases | `70db22a1c` | `36412f7e8` | develop merge(`54d2a2fc9`), OOS error code 번호 변경(`36412f7e8`) |
| CUBRID/cubrid-testcases-private-ex | `75a02020e` | `5c440ce44` | develop merge |

두 testcase 저장소의 `tc/pr-7990`도 같은 tip으로 맞췄다.
엔진 merge에서 바뀐 점 두 가지는 이 분류와 관련이 있다.

- develop이 error code -1387..-1391을 새로 썼다. 그래서 OOS error code를 -1392..-1398로 옮겼다. `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`는 -1388에서 -1393이 되었고, 이 번호가 들어 있는 sql answer 2개를 함께 바꿨다.
- develop의 page batch(CBRD-27361)는 heap record bytes에서 column을 바로 읽는다. OOS 값이 있는 record를 읽으면 틀린 결과가 나왔다. `test_oos_sql_workspace_bytes`의 `LargestFirstAndPreferInline`이 2가 아니라 0을 셌다. `dcf38cb0a`는 이런 record가 든 chunk를 row path로 보낸다. 수정 뒤 OOS ctest 50개가 모두 통과했다.

### 다시 실행한 run

#7990 head `dcf38cb0a`에서 `/run sql_by_cci`를 실행했다. run은 [42763653366](https://github.com/CUBRID/cubrid/actions/runs/42763653366)이고, testcase는 `36412f7e8`(`tc/pr-7990`)이다.
build 2개는 통과했다. `test_sql_by_cci`는 10 shard를 모두 끝냈고 34개 case가 실패했다.

비교 baseline은 위 표의 develop run 5개에 2026-11-10 run 2개를 더했다.
#8433 run은 이번에 쓰지 않았다.

| run | PR | 실패 수 |
|---|---|---|
| [42763131880](https://github.com/CUBRID/cubrid/actions/runs/42763131880) | #8019 | 36 |
| [42762733877](https://github.com/CUBRID/cubrid/actions/runs/42762733877) | #8424 | 48 |

### 방법

위 "방법"과 같다.
실패 목록은 shard log의 `Case Name:`/`Test Result: NOK`에서 뽑았다. diff는 artifact server(`/runs/<run>/sql_by_cci/shard/<n>/test-results/`)의 JUnit XML에서 읽었다.
8개 run 모두 log와 XML의 실패 수가 같다.
이 절차로 이전 OOS run 42562225722를 다시 세면 57개가 나오고, develop run 5개도 위 표의 수와 같다.

diff 비교는 case마다 `+` 줄 집합과 `-` 줄 집합을 비교했다. 줄 안의 공백은 하나로 줄였다.

### 결과

| 분류 | 수 |
|---|---|
| develop에서도 실패 | 34 |
| `feature/oos-merge`에서만 실패 | 0 |

- 34개 모두 develop run 7개 중 1개 이상에서 실패한다.
- 34개 모두 diff가 develop run 중 하나와 줄 단위로 같다. OOS run에만 나오는 출력 줄은 없다.
- 이전 run의 (b) 28개는 모두 통과한다. (b1) 18개는 develop testcase를 merge해서 없어졌다. (b2) 10개는 develop 엔진을 merge해서 없어졌다. 이것은 (b2)를 develop 차이로 본 위 추론과 맞는다. 다만 원인 commit이 `52193efa9`인지는 여전히 bisect로 확인하지 않았다.
- (a)에서 OOS 쪽만 다르던 `Error:-1118` statement(`11087.sql`, percentile 2개)도 이제 develop과 같은 diff를 낸다.
- 새로 실패하는 17개는 develop run에서도 실패한다(7개 중 3~7개). 이번 merge로 develop의 기존 실패가 함께 들어온 것이다.

### 판단

`test_sql_by_cci`에서 OOS 작업이 고칠 case는 없다. [jira-draft.md](jira-draft.md)는 등록하지 않는다.
남은 34개는 develop 공통 실패로, `test_sql_by_cci` 도입 작업(CUBRIDQA-1709 계열)의 범위이다.

이 결과는 `sql_by_cci`만 다룬다. head `dcf38cb0a`에서 `test_shell`, `test_sql`, `test_medium`은 아직 실행하지 않았다.
엔진 `feature/oos-merge`는 2026-11-10 기준 develop보다 11 commit 뒤처져 있다.

## 2차 develop 동기화와 전체 run (2026-11-10)

### 동기화한 commit

| 저장소 | 이전 | 이후 |
|---|---|---|
| CUBRID/cubrid | `dcf38cb0a` | `50619ce53` (develop `2dd94e32a` merge) |
| CUBRID/cubrid-testcases | `36412f7e8` | `b53a7984c` |
| CUBRID/cubrid-testcases-private-ex | `5c440ce44` | `e56dfa32a` |

develop이 error code -1392..-1394를 새로 써서, OOS error code를 다시 -1395..-1401로 옮겼다. `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`는 -1396이다.

### run

#7990 head `50619ce53`에서 `/run all`을 실행했다. run은 [42785110884](https://github.com/CUBRID/cubrid/actions/runs/42785110884)이다.

| suite | 실패 | develop에서도 실패 | OOS에서만 실패 |
|---|---|---|---|
| `test_medium` | 0 | 0 | 0 |
| `test_sql` | 2 | 2 | 0 |
| `test_sql_by_cci` | 38 | 38 | 0 |
| `test_shell` | 4 | 1 | 3 |

baseline은 같은 날 develop 대상 PR run 3개이다. [42807018862](https://github.com/CUBRID/cubrid/actions/runs/42807018862)(#8409), [42790013637](https://github.com/CUBRID/cubrid/actions/runs/42790013637)(#8356), [42784848562](https://github.com/CUBRID/cubrid/actions/runs/42784848562)(#8168)이다. 실패 목록은 artifact server의 `/runs/<run>/<suite>/collect/failed.list`에서 읽었다. 이번 비교는 case 이름만 비교했고, `sql_by_cci` diff signature 비교는 하지 않았다.

- `test_sql` 2개(`cbrd_27762.sql`, `r_outer_join.sql`)는 #8168 run에서도 똑같이 실패한다.
- `test_sql_by_cci` 38개는 모두 baseline run 중 하나 이상에서 실패한다. 1차 run(34개)보다 늘어난 4개(`cbrd_27337.sql`, `r_outer_join.sql`, `cbrd_25984.sql`, `cbrd_27762.sql`)도 develop에서 실패한다.
- `test_shell`의 `cbrd_27571.sh`는 develop에서도 실패한다.

### shell OOS-only 3개

`bug_bts_9836`, `bug_bts_14120`, `bug_bts_15529`는 모두 `call_stack_dump_activation_list` 기본값 출력만 다르다. 엔진은 OOS code `-1395,-1397,-1398`을 내고, private-ex answer는 1차 번호 `-1387,-1389,-1390`을 갖고 있었다. 2차 번호 변경 때 이 answer 5개를 고치지 않은 것이 원인이다. 엔진 결함이 아니다.

private-ex 로컬 commit `8ef4f6278`이 answer 5개를 고쳤다. 같은 변경은 이전 merge에서도 있었다(`aa1db95f8`). 이 commit은 아직 push하지 않았고, push 뒤 `/run shell`로 확인해야 한다.

### 판단

OOS 작업이 고칠 엔진 실패는 없다. 남은 일은 private-ex answer 5개 push와 `test_shell` 재확인이다.

## 한계

- develop baseline은 develop push run이 아니라 develop 기반 PR run이다. 각 PR 변경이 일부 case에 영향을 줄 수 있다. 그래서 6개 run을 썼고, (b)는 6개 모두에서 통과한 case만 넣었다.
- `test_sql`은 debug build, `test_sql_by_cci`는 release build를 쓴다. (b2)의 csql 대 CCI 비교에는 build mode 차이도 함께 있다.
- (b2)의 원인 commit은 bisect로 확인하지 않았다.
- collector manifest 검증 없이 GitHub log와 evidence server 파일을 직접 읽었다. log와 XML의 실패 수가 7개 run 모두 같다는 것으로 일관성을 확인했다.
