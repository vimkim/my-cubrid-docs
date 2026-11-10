# PR 8348 CI 분석: head 00b421e (리뷰 반영 후)

hornetmj 리뷰 반영 커밋 이후 CI 실패가 이 PR 때문인지 판단하려고 증거를 정리한다. 분석일은 2026-11-10, Asia/Seoul이다.

**이번 수집은 불완전하다. 이 CI 자료만으로 회귀 여부나 근본 원인을 결론 내릴 수 없다.** head와 merge-base 양쪽에서 `test_sql` shard `01`의 workflow 결과와 JUnit 집계가 달라 수집기가 exit `4`로 끝났다. 10/30 분석([ci_analysis_report_6288576_claude.md](ci_analysis_report_6288576_claude.md))과 같은 오류이다. 아래 내용은 검증된 suite의 관찰과, 그 관찰에서 나온 추론을 구분해 적는다.

## 요약

| Suite | GitHub 상태 | 수집 상태 | 검증한 집계 | 판단 |
| --- | --- | --- | --- | --- |
| `test_medium` | SUCCESS | completed, validated | 975 계획, 975 통과 | 실패 없음 |
| `test_sql` | SUCCESS | collection_failed | 미검증 | 판단 불가. GitHub SUCCESS를 testcase 집계로 대체하지 않는다. |
| `test_shell` | FAILURE | completed, validated | 3,490 계획, 3,460 실행, 3,459 통과, 실패 1, skip 30 | 실패 1건. PR 관련성 `unlikely`, 신뢰도 중간 |
| `test_sql_by_cci` | FAILURE | completed, validated | 17,630 계획, 17,573 통과, 실패 57 | 알려진 이슈. 이 PR 원인 아님 |

다음 작업: `bug_bts_5492`만 실패한 shell shard를 다시 돌려 재발 여부를 본다. CI 재실행은 사용자 승인이 필요하다.

## 대상과 증거 범위

- 엔진 head: `00b421e327f2850c8633f0db5a93736adcc7d857`. 앞 head `628857607`에서 `vacuum_heap_record`의 `heap_add_bestpage` 호출 3줄을 `log_sysop_commit` 뒤로 옮긴 것만 다르다.
- 대상 브랜치 `feature/oos-merge`. target tip과 merge-base 모두 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`이다(관찰 `2026-11-10T08:08:01Z`).
- head 실행: [42578641410, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/42578641410). 2026-11-09 18:58 KST 종료.
- merge-base 실행: [40738391553, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/40738391553). 이 실행에는 `test_sql_by_cci`가 없다(`not_observed`). `test_sql`은 head와 같은 이유로 `collection_failed`이다. baseline 판정은 `partial_exact`이다.
- 수집기: `cubrid-ci 0.2.0 (4d00de674d86, release)`. `doctor` 정상. head observation `20261110T080707.605794583Z-1257021-0`.
- `report_mode.py` 판정: `warning`, 회귀 결론 불가, 비교 범위 없음.
- shell testcase revision: 50개 shard 모두 `a0b3bb729263cee95431542322301505121c3621`(`tc/pr-8348`). 10/30 실행과 같은 revision이다.
- 증거 위치: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8348/00b421e327f2850c8633f0db5a93736adcc7d857/`.

## 실패 목록

| Suite | Testcase | 결과 | 관찰한 증상 | baseline 분류 | PR 관련성 | 신뢰도 |
| --- | --- | --- | --- | --- | --- | --- |
| `test_shell` | `shell/_06_issues/_11_1h/bug_bts_5492/cases/bug_bts_5492.sh` | failure (shard 49) | CAS 재시작 뒤 broker1 CAS가 60초 안에 생기지 않음 | `additional_on_head` (base에서는 PASS) | `unlikely` | 중간 |
| `test_sql_by_cci` | 57건 (shard 01, 03, 04, 05, 06, 07, 09) | failure | 아래 목록 | `uncomparable` (base에 suite 없음) | 알려진 이슈 | 높음 |

merge-base shell의 실패 1건은 `shell/_01_utility/_19_loaddb_parameter/parameter_combine/cases/parameter_combine.sh`이다. head에서는 통과했다(`base_only`).

## shell: `bug_bts_5492`

### 관찰

- testcase는 `APPL_SERVER_MAX_SIZE=1`, `MIN/MAX_NUM_APPL_SERVER=1`로 broker를 재시작한다. 그다음 JDBC로 `SessionTest`를 돌리고, CAS가 크기 제한으로 재시작돼 pid가 바뀌었는지 본다(`a0b3bb7`의 소스로 확인).
- `message.txt` 274~312행:
  - 첫 CAS pid는 `18852`였다.
  - `SessionTest.testAutoCommit`에서 재연결하던 중 `BrokerHandler.connectBroker`가 `Request timed out`을 냈다. 이때 CAS는 `18888`이었다.
  - `testNoAutoCommit`의 새 연결도 같은 위치에서 timeout이 났고, 이어서 `NullPointerException`이 났다.
  - 그 뒤 60초 동안 `broker1_cub_cas` 프로세스가 하나도 없었다(`pid2=[]`).
- `result2.log`는 AUTO COMMIT ON 구간 중간에서 끊겼다.
- 이력(`cubrid-tcc`, 마지막 동기화 2026-11-02): 2026-10-23~11-02 사이에 이 케이스를 9번 실행해 모두 PASS였다. 같은 testcase revision으로 앞 head `628857607`을 돌린 실행 41050496911과 merge-base 실행 40738391553도 포함된다. 색인된 실패는 PR 7837(CAS·SQL 컴파일러 통합 PoC, develop 기반)의 실행 39772813997 한 건뿐이다. flaky 여부는 비교할 맥락이 부족해 `UNKNOWN`이다.

### 추론

- 실패 위치는 broker가 클라이언트에 CAS를 넘겨주는 handshake(`connectBroker`)와 CAS 프로세스 재기동이다. 서버 vacuum이 페이지를 언제 bestspace에 공개하는지와는 직접 이어지는 경로가 보이지 않는다.
- 이 PR의 변경은 forward 페이지를 bestspace에 공개하는 시점을 늦출 뿐이다. 새 대기를 만들지 않고, 오히려 줄인다(로컬 재현으로 확인).
- 따라서 PR 관련성은 `unlikely`로 본다. 다만 CAS가 다시 뜨지 않은 원인은 증거에 없다. broker, CAS 로그는 수집되지 않았다.

### 모르는 것

- 새 CAS가 뜨지 못한 이유. 기동 실패인지, 서버 연결 중 멈춘 것인지 알 수 없다.
- 같은 head에서 재실행하면 다시 나는지.

### 반증 조건

- 같은 head로 다시 돌렸을 때 재발하고, 같은 testcase revision에서 `628857607`로 돌리면 통과하면 이 판단을 다시 본다.

### 다음 작업

- shell shard 49(또는 이 케이스 하나)를 다시 돌린다. 재발하면 `cubrid-test-shell-run`으로 로컬에서 재현하고 broker, CAS 로그를 남긴다.

## sql_by_cci: 알려진 이슈

`cubrid-common`의 Known CI issues 목록에 있는 "`sql_by_cci` job fails on every branch" 항목(2026-12-09까지 유효)에 해당한다. 이 job은 gha-ci에 새로 추가됐고, `develop`에서도 실패한다. 규칙에 따라 원인 분석은 하지 않고 목록만 남긴다. merge-base 실행에는 이 suite가 없어 비교할 수 없다.

실패한 57건은 PL/CSQL `%TYPE`, aggregate/analytic(`avg`, `median`, `percentile_cont/disc`), host variable, `cbrd_27510` 계열이다. vacuum이나 OOS와 관련된 이름은 없다.

<details><summary>57건 전체</summary>

```text
01 sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/04_normal_percent_type_parameter.sql
01 sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/05_error_percent_type_return.sql
01 sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/05_normal_percent_type_return.sql
01 sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/24_normal_viewtable_percent_type_parameter.sql
01 sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/25_error_viewtable_percent_type_return.sql
01 sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/25_normal_viewtable_percent_type_return.sql
03 sql/_13_issues/_14_1h/cases/bug_bts_13653.sql
03 sql/_13_issues/_14_1h/cases/bug_bts_13916.sql
03 sql/_13_issues/_15_1h/cases/bug_bts_16039.sql
03 sql/_13_issues/_20_2h/cases/cbrd_23665.sql
03 sql/_13_issues/_26_2h/cases/cbrd_27327.sql
03 sql/_13_issues/_26_2h/cases/cbrd_27504.sql
03 sql/_13_issues/_26_2h/cases/cbrd_27668.sql
03 sql/_14_mysql_compatibility_2/_04_table_related/_02_alter_change_column/_11_trigger/cases/1101.sql
03 sql/_14_mysql_compatibility_2/_15_host_variable/_12_common/cases/agg_group_by.sql
04 sql/_17_sql_extension2/_02_full_test/_03_alter_table/_01_alter_change/cases/alter_change_026.sql
05 sql/_23_apricot_qa/_01_sql_extension3/_05_analytic_functions/_14_avg/cases/avg_constraints.sql
05 sql/_23_apricot_qa/_01_sql_extension3/_05_analytic_functions/_14_avg/cases/avg_null.sql
05 sql/_23_apricot_qa/_01_sql_extension3/_05_analytic_functions/_14_avg/cases/avg_numeric.sql
06 sql/_26_features_920/issue_11087_median/cases/11087.sql
06 sql/_26_features_920/issue_11087_median/cases/11087_1.sql
06 sql/_26_features_920/issue_11087_median/cases/11087_3.sql
07 sql/_27_banana_qa/issue_11088_percentile_cont/_01_aggregate_function/cases/_00_from_dev.sql
07 sql/_27_banana_qa/issue_11088_percentile_cont/_01_aggregate_function/cases/_03_character_string1.sql
07 sql/_27_banana_qa/issue_11088_percentile_cont/_01_aggregate_function/cases/_03_character_string2.sql
07 sql/_27_banana_qa/issue_11088_percentile_cont/_02_analytic_function/cases/p_cont_bit_lob.sql
07 sql/_27_banana_qa/issue_11088_percentile_cont/_02_analytic_function/cases/p_cont_character_string.sql
07 sql/_27_banana_qa/issue_11088_percentile_cont/_02_analytic_function/cases/p_cont_partition_list.sql
07 sql/_27_banana_qa/issue_11089_percentile_disc/_01_aggregate_function/cases/_00_from_dev.sql
07 sql/_27_banana_qa/issue_11089_percentile_disc/_01_aggregate_function/cases/_03_character_string1.sql
07 sql/_27_banana_qa/issue_11089_percentile_disc/_01_aggregate_function/cases/_03_character_string2.sql
07 sql/_27_banana_qa/issue_11089_percentile_disc/_02_analytic_function/cases/p_disc_bit_lob.sql
07 sql/_27_banana_qa/issue_11089_percentile_disc/_02_analytic_function/cases/p_disc_character_string.sql
07 sql/_27_banana_qa/issue_11089_percentile_disc/_02_analytic_function/cases/p_disc_partition_list.sql
07 sql/_27_banana_qa/issue_16066_BINARY_charset/_00_String_Functions_and_Operators/cases/rtrim_002.sql
07 sql/_28_features_930/issue_13133_hash_query_profile/cases/hash_agg_query_profile.sql
09 sql/_36_guava/cbrd_25447/cases/cbrd_25447.sql
09 sql/_36_guava/cbrd_26258/cases/join_orderby_skip.sql
09 sql/_36_guava/cbrd_26431/cases/cbrd_26431.sql
09 sql/_36_guava/cbrd_27397/cases/cbrd_27397.sql
09 sql/_36_guava/cbrd_27503/cases/cbrd_27503.sql
09 sql/_36_guava/cbrd_27510/cases/01_fetch_gate_probes.sql
09 sql/_36_guava/cbrd_27510/cases/02_fetch_gate_bind_reads.sql
09 sql/_36_guava/cbrd_27510/cases/03_session_variable_types.sql
09 sql/_36_guava/cbrd_27510/cases/05_common_value_constants.sql
09 sql/_36_guava/cbrd_27510/cases/06_precast_plan.sql
09 sql/_36_guava/cbrd_27510/cases/07_scope_once_conversion.sql
09 sql/_36_guava/cbrd_27510/cases/08_to_number_domain.sql
09 sql/_36_guava/cbrd_27510/cases/10_list_aggregate_probes.sql
09 sql/_36_guava/cbrd_27510/cases/11_analytic_interpolation_keys.sql
09 sql/_36_guava/cbrd_27510/cases/13_compare_outside_terms.sql
09 sql/_36_guava/cbrd_27510/cases/14_index_key_probes.sql
09 sql/_36_guava/cbrd_27510/cases/20_conversion_contract.sql
09 sql/_36_guava/cbrd_27510/cases/23_unresolved_domain_axes.sql
09 sql/_36_guava/cbrd_27510/cases/24_sum_avg_date_argument.sql
09 sql/_36_guava/cbrd_27510/cases/25_string_constant_over_bind_sum.sql
09 sql/_36_guava/cbrd_27510/cases/29_analytic_string_first_value.sql
```

</details>

## test_sql 수집 오류

수집기는 `result identity mismatch: shard 01 workflow result and JUnit counts disagree`를 보고했다. head와 merge-base 모두 같고, 10/30 실행에서도 같았다. 이것은 수집기 쪽 무결성 검사 결과이고, testcase 실패의 증거가 아니다. GitHub 상태는 SUCCESS이다. 수집기 쪽 문제로 따로 다뤄야 한다.

## 우선순위

1. shell `bug_bts_5492`만 다시 돌려 재발 여부를 확인한다. `test_shell`은 머지 조건이다. 승인이 필요하다.
2. 재발하면 로컬에서 재현하고 broker, CAS 로그를 확인한다.
3. `test_sql` 수집 오류(shard 01 집계 불일치)는 `cubrid-ci` 쪽 이슈로 따로 남긴다.
4. `sql_by_cci`는 알려진 이슈이므로 이 PR에서 할 일이 없다. 다만 머지 조건에서 빠지는지 확인한다.
