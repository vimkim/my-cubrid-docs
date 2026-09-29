# PR #7927 CI 검증 결과 — 34a9072

2026-09-29 수집. 정확한 엔진 커밋: `34a9072a19fdd5baf420273992c136119e719503`. 수집기 0.2.0 (45944012aaaa). 최초 구버전 수집의 한계는 보존하고, 별도 깨끗한 증거 디렉터리의 새 수집을 검증했다.

command/manifest/observation 식별, 모든 schema, raw 파일의 크기·SHA256, summary 연결 hash, 실행·판정 집계, failure metadata를 검증했다. 분석 모드 full. 바이너리 수집은 요청하지 않았다. 이 검증은 CI 자료의 진위를 확인하며 실패 원인을 자동으로 확정하지 않는다.

| Suite | 실행 / 통과 / 실패 / skip | Run / attempt | 테스트 리비전 |
|---|---|---|---|
| test_medium | 975 / 972 / 3 / 0 | [36102128913/1](https://github.com/CUBRID/cubrid/actions/runs/36102128913) | 7fb227854a00daca5a3ccd3a74160de4b7e1254a |
| test_shell | 3256 / 3246 / 10 / 30 | [36102128913/1](https://github.com/CUBRID/cubrid/actions/runs/36102128913) | 018fc45bb12a63d24f4d85315790437cbf7cdaae |
| test_sql | 17466 / 17465 / 1 / 0 | [36102128913/1](https://github.com/CUBRID/cubrid/actions/runs/36102128913) | 7fb227854a00daca5a3ccd3a74160de4b7e1254a |

## 실패 목록

| Suite | 테스트 | 판단 | 증거 |
|---|---|---|---|
| test_medium | medium/_02_xtests/cases/to_char_order_by.sql | 원인 미확정, 비교·재현 필요 | [message](evidence/pr7927-failures/medium_02_xtests_cases_to_char_order_by_sql-81a7176eb9/message.txt) · [diff](evidence/pr7927-failures/medium_02_xtests_cases_to_char_order_by_sql-81a7176eb9/diff.txt) |
| test_medium | medium/_02_xtests/cases/to_number_order_by.sql | 원인 미확정, 비교·재현 필요 | [message](evidence/pr7927-failures/medium_02_xtests_cases_to_number_order_by_sql-2914e2cc1a/message.txt) · [diff](evidence/pr7927-failures/medium_02_xtests_cases_to_number_order_by_sql-2914e2cc1a/diff.txt) |
| test_medium | medium/_02_xtests/cases/to_timestamp_order_by.sql | 원인 미확정, 비교·재현 필요 | [message](evidence/pr7927-failures/medium_02_xtests_cases_to_timestamp_order_by_sql-f88d9035bb/message.txt) · [diff](evidence/pr7927-failures/medium_02_xtests_cases_to_timestamp_order_by_sql-f88d9035bb/diff.txt) |
| test_shell | shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh | 합의된 CDC 연기 범위. 추출 실패 관측; 이 수집만으로 내부 원인 확정 안 함 | [message 원본(gzip)](evidence/pr7927-failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27075_cases_cbrd_27075_sh-f42063033e/message.txt.gz) · [diff](evidence/pr7927-failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27075_cases_cbrd_27075_sh-f42063033e/diff.txt) |
| test_shell | shell/_06_issues/_15_1h/bug_bts_15912/cases/bug_bts_15912.sh | 원인 미확정, 비교·재현 필요 | [message](evidence/pr7927-failures/shell_06_issues_15_1h_bug_bts_15912_cases_bug_bts_15912_sh-807266212f/message.txt) · [diff](evidence/pr7927-failures/shell_06_issues_15_1h_bug_bts_15912_cases_bug_bts_15912_sh-807266212f/diff.txt) |
| test_shell | shell/_32_features_930/issue_12504_show_log_header/_01_show_log_header/_02_relative_path/_01_csql/cases/_01_csql.sh | 원인 미확정, 비교·재현 필요 | [message](evidence/pr7927-failures/shell_32_features_930_issue_12504_show_log_header_01_show_log_header_02_relative-bd5f046f99/message.txt) · [diff](evidence/pr7927-failures/shell_32_features_930_issue_12504_show_log_header_01_show_log_header_02_relative-bd5f046f99/diff.txt) |
| test_shell | shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh | 원인 미확정, 비교·재현 필요 | [message](evidence/pr7927-failures/shell_06_issues_14_2h_bug_bts_14120_cases_bug_bts_14120_sh-2917c23aa5/message.txt) · [diff](evidence/pr7927-failures/shell_06_issues_14_2h_bug_bts_14120_cases_bug_bts_14120_sh-2917c23aa5/diff.txt) |
| test_shell | shell/_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh | 원인 미확정, 비교·재현 필요 | [message](evidence/pr7927-failures/shell_06_issues_12_2h_bug_bts_9836_cases_bug_bts_9836_sh-74957cfea4/message.txt) · [diff](evidence/pr7927-failures/shell_06_issues_12_2h_bug_bts_9836_cases_bug_bts_9836_sh-74957cfea4/diff.txt) |
| test_shell | shell/_32_features_930/issue_12504_show_log_header/_01_show_log_header/_03_absolute_path/_01_self_log/cases/_01_self_log.sh | 원인 미확정, 비교·재현 필요 | [message](evidence/pr7927-failures/shell_32_features_930_issue_12504_show_log_header_01_show_log_header_03_absolute-b71bf934be/message.txt) · [diff](evidence/pr7927-failures/shell_32_features_930_issue_12504_show_log_header_01_show_log_header_03_absolute-b71bf934be/diff.txt) |
| test_shell | shell/_06_issues/_25_1h/cbrd_25478/cases/cbrd_25478.sh | 원인 미확정, 비교·재현 필요 | [message 원본(gzip)](evidence/pr7927-failures/shell_06_issues_25_1h_cbrd_25478_cases_cbrd_25478_sh-b94dc3fbd6/message.txt.gz) · [diff](evidence/pr7927-failures/shell_06_issues_25_1h_cbrd_25478_cases_cbrd_25478_sh-b94dc3fbd6/diff.txt) |
| test_shell | shell/_32_features_930/issue_12504_show_log_header/_01_show_log_header/_01_basic_log/cases/_01_basic_log.sh | 원인 미확정, 비교·재현 필요 | [message](evidence/pr7927-failures/shell_32_features_930_issue_12504_show_log_header_01_show_log_header_01_basic_lo-ae20658d46/message.txt) · [diff](evidence/pr7927-failures/shell_32_features_930_issue_12504_show_log_header_01_show_log_header_01_basic_lo-ae20658d46/diff.txt) |
| test_shell | shell/_06_issues/_15_1h/bug_bts_16378/cases/bug_bts_16378.sh | 원인 미확정, 비교·재현 필요 | [message](evidence/pr7927-failures/shell_06_issues_15_1h_bug_bts_16378_cases_bug_bts_16378_sh-b38545cb8f/message.txt) · [diff](evidence/pr7927-failures/shell_06_issues_15_1h_bug_bts_16378_cases_bug_bts_16378_sh-b38545cb8f/diff.txt) |
| test_shell | shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh | 합의된 CDC 연기 범위. 추출 실패 관측; 이 수집만으로 내부 원인 확정 안 함 | [message 원본(gzip)](evidence/pr7927-failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118/message.txt.gz) · [diff](evidence/pr7927-failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118/diff.txt) |
| test_sql | sql/_33_elderberry/cbrd_23844/cbrd_24337/cases/cbrd_24337.sql | 원인 미확정, 비교·재현 필요 | [message](evidence/pr7927-failures/sql_33_elderberry_cbrd_23844_cbrd_24337_cases_cbrd_24337_sql-c0d5024efe/message.txt) · [diff](evidence/pr7927-failures/sql_33_elderberry_cbrd_23844_cbrd_24337_cases_cbrd_24337_sql-c0d5024efe/diff.txt) |

## 원인 판단과 다음 검증

관측: 실패 목록과 diff는 위 exact revision의 자료다. PR 관계는 내부 원인 기준 unknown, 관측 신뢰도는 높지만 인과 신뢰도는 미확정이다. CDC 두 건은 ADR-0005의 명시적 연기 범위에 해당한다. 동일 증상이 develop 또는 부모에서 재현되는지는 별도 비교가 필요하다.

비CDC 관측은 medium 출력 순서 3건, SQL 오류 코드 -494/-493 차이 1건, shell의 utility 목록·오류 기본 목록·로그 헤더 차이 8건이다. 기대값 차이일 가능성은 있으나 현재 paired 실행 증거가 없다. 반증 조건은 동일 버전·설정·테스트로 비교했을 때 논리값이나 오류 조건이 달라지는 것이다. 다음 조치는 부모와 후보의 해당 실패를 동일 자산으로 비교하고, 출력 계약과 의도된 변경을 확인하는 것이다. answer를 먼저 바꾸지 않는다.

증거 디렉터리: `/home/vimkim/tmp/oos-readiness-221/ci-clean/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503`. Observation: `/home/vimkim/tmp/oos-readiness-221/ci-clean/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503/observations/20260929T122022.399106674Z-3606243-0/result.json`. 원본 testcase는 각 summary shard의 SHA로 로컬 git show를 통해 존재를 확인했다.
