# Suspected causes of Linux QA failures: feature/oos-merge versus develop

Report date: 2026-09-29. QA snapshot fetched at approximately 14:06 KST. Work item: 213.

Publication update: the [source-level triage](qa_source_triage_1ec35f8_codex.md) adds deeper source evidence. S04 below now identifies preserved cardinality mismatches, and R01 accounts for the additional reader cores. The candidate inventory and counts are unchanged.

**Conclusion:** the snapshot contains additional non-CDC failure candidates; it does not establish that feature/oos-merge has no additional failures. Several candidates have strong explanations (missing develop fix, diagnostic-answer drift, physical-output drift, topology state, timing thresholds). Others remain unresolved. All explanations below are assessments of existing evidence, not locally reproduced root causes.

**Requested scope:** report only, following the user’s clarification. No local testcase execution, engine/testcase repair, QA rerun, or publication was performed. Reproduction was explicitly waived for this report. A preparatory local build was completed before that clarification.

## Build identity and comparability

| Role | Build | Exact source commit |
|---|---|---|
| Feature | 11.5.0.2625-1ec35f8 | `1ec35f86c5e43b9ca86d81e202c68899f8ce4f21` |
| Develop | 11.5.0.2622-e1c3db1 | `e1c3db19800a0170942cec8b23cac4705efbb6e3` |

Feature QA uses engine/testcase branch feature/oos-merge. Develop QA is the baseline identified by the user. Both build labels were verified in authenticated portal responses. Only the Linux functional table is compared; it contains 64-bit rows. Windows and the separate driver/server compatibility matrices are omitted. This report does not claim 32-bit coverage.

Feature HEAD’s merge-base with the named baseline is `c63a3b993be552ef6ad3ce244c386d5081147958`. Five develop commits through e1c3db198 are missing from feature ancestry: CBRD-27389 session validation, CBRD-27449 crypto performance, CBRD-27394 master management security, APIS-1112 CCI update, and CBRD-27407 hash aggregation. Missing ancestry is verified; only CBRD-27407 has strong direct evidence connecting it to a particular failure in this report.

Exact QA testcase SHAs and full per-suite settings are not exposed by the downloaded summaries. Local supporting snapshots are public `89d4ec2423d94b973b5f9cf0c612c9576b9ccce6` and private-ex `1274a4d6462a3d5ae5daeb004e042f89496991d8`; both were dated 2026-09-25. They are supporting source evidence, not asserted to be the exact QA checkouts. HA/CCI/JDBC use a separate private corpus not available in these two local testcase repositories.

## Counts and exclusions

- Feature: 133 failed suite/testcase rows in the Linux table.
- CDC excluded: 51 rows (47 cdc_repl, plus cbrd_27064 and cbrd_27075 in shell and shell_debug).
- Non-CDC baseline overlap: 36 rows also fail in the corresponding develop suite.
- Additional non-CDC candidates: 46 rows across 35 distinct testcase identities.

Of the 46, **six candidate rows lack a completed comparator**: cci (2), cci_debug (1), shell_perf (2), and RQG (1). They remain provisional, not confirmed new regressions. The remaining 40 candidate rows are absent from the corresponding completed baseline failure lists.

A row means one testcase in one suite/variant, not one failing assertion. Matching testcase identity does not prove matching failure symptoms. New/Verified portal labels use a historical reference and cannot replace this explicit build comparison. CDC failures remain visible under [ADR-0005](https://github.com/vimkim/cubrid-oos-context/blob/75f8b58674ac901d478ba60f9b2cc2fff11f66f6/docs/adr/0005-defer-oos-history-from-the-11-5-merge.md). No non-CDC HA or replication case is removed merely because it involves replication.

| Suite | Feature failures | Develop failures | Additional candidate rows | CDC exclusions | Comparator |
|---|---:|---:|---:|---:|---|
| sql | 0 | 0 | 0 | 0 | complete |
| sql_debug | 0 | 0 | 0 | 0 | complete |
| medium | 0 | 0 | 0 | 0 | complete |
| medium_debug | 0 | 0 | 0 | 0 | complete |
| sql_by_cci | 11 | 9 | 2 | 0 | complete |
| shell | 24 | 15 | 10 | 2 | complete |
| shell_debug | 21 | 10 | 10 | 2 | complete |
| shell_heavy | — | — | 0 | 0 | missing / incomplete |
| shell_long | — | — | 0 | 0 | missing / incomplete |
| cci | 2 | — | 2 | 0 | missing / incomplete |
| cci_debug | 1 | 0 | 1 | 0 | missing / incomplete |
| ha_shell | 8 | 3 | 7 | 0 | complete |
| ha_repl | — | 2 | 0 | 0 | missing / incomplete |
| ha_repl_debug | 8 | 3 | 7 | 0 | complete |
| shell_perf | 3 | 1 | 2 | 0 | missing / incomplete |
| isolation | 1 | 0 | 1 | 0 | complete |
| isolation_debug | 2 | 0 | 2 | 0 | complete |
| jdbc | 4 | 4 | 1 | 0 | complete |
| RQG | 1 | — | 1 | 0 | missing / incomplete |
| cdc_repl | 47 | 47 | 0 | 47 | complete |
| shell_ext | — | — | 0 | 0 | missing / incomplete |
| unittest | — | — | 0 | 0 | missing / incomplete |
| unittest_debug | 0 | — | 0 | 0 | missing / incomplete |

## Suspected reasons by symptom family

Confidence describes how directly the artifacts support the proposed explanation. High confidence in an observed failure mechanism is not proof of its complete root cause.

### I01: Missing develop fix for the partition/parallel hash-aggregation crash

Confidence: **High**. Additional rows: **2**.

Feature isolation and isolation_debug fail reorganization_select_01.ctl; develop passes both. QA records server death and repeated cores. The verification table cites CBRD-27407. Develop baseline e1c3db198 is the fix itself, while feature HEAD has merge-base c63a3b993 and does not contain it. Its restore_agg_part_list_for_append() repair is absent from the feature source. Suspected cause: a pre-existing develop defect survives in the older feature integration baseline, rather than a demonstrated OOS-triggered defect. This is nevertheless an additional failure against the chosen baseline.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=58997&resultType=NOK).

Sources: [fix commit / PR #7983](https://github.com/CUBRID/CUBRID/commit/e1c3db19800a0170942cec8b23cac4705efbb6e3), [CBRD-27407](http://jira.cubrid.org/browse/CBRD-27407), [JIRA verification](http://jira.cubrid.org/browse/CBRD-27407). The live issue is Closed/Fixed and records a 2026-09-29 regression verification passing both isolation variants on 11.5.0.2622-e1c3db1.

### S01: OOS changes the default error-code list expected by bug_bts_15529

Confidence: **High**. Additional rows: **2**.

The only observed parameter-output differences are call_stack_dump_activation_list. The captured actual default includes -1383,-1385,-1386, while the answer omits them. Those codes are ER_HEAP_OOS_BAD_INLINE_HEADER, ER_HEAP_OOS_CORRUPTED_RECORD, and ER_HEAP_OOS_INVALID_ARGUMENT, explicitly added to call_stack_dump_error_codes[]. Suspected cause: deterministic answer drift for an intentional OOS diagnostic default; not evidence of failed DML. Both release and debug variants have the mismatch.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=58999&resultType=NOK).

Source: [feature default list](https://github.com/CUBRID/CUBRID/blob/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21/src/base/system_parameter.c#L5901).

### S02: DBLink DML plan-cost snapshots differ

Confidence: **Medium**. Additional rows: **8**.

All four DBLink DML variants fail subcase _07_*_dblink_push. The captured MySQL side-by-side diff identifies a cost-line difference (masked digits have different widths); its visible data rows match. Suspected cause: changed storage/statistics estimates or plan-output normalization, rather than a demonstrated result-value error. The other three variants have the same failed assertion family, but their complete results must not be presumed identical to MySQL.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=58999&resultType=NOK).

### S03: DBLink server/ownership expected-output mismatch

Confidence: **Medium-low**. Additional rows: **6**.

The MySQL, Oracle, and MariaDB-general cases fail _07_server_check. The captured MySQL/Oracle differences include syntax-versus-user-validation errors and G1/G2 server-owner results. Suspected cause: parser/catalog state or testcase/answer version inconsistency in the QA deployment. Local semantic_check.c, schema_manager.c, and schema_system_catalog_install.cpp have no difference against the named baseline; the grammar difference is OOS STORAGE syntax. These facts do not prove the deployed binaries or QA testcase snapshots match local source. The ownership differences remain substantive and must not be dismissed as formatting alone.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=58999&resultType=NOK).

### S04: Preserved cardinality assertions differ in cbrd_26354

Confidence: **High for observed cardinality mismatch; low for cause**. Additional rows: **2**.

Both variants show plan-answer differences. Deeper debug-diff inspection finds retained cardinalities changing, including expected 55 versus actual 11 and expected 200000 versus actual 99986. The testcase deliberately preserves these estimates to check LIMIT-driven cardinality behavior. Investigate setup/statistics and estimation; an answer refresh could mask the intended regression guard. The short VARCHAR(20) setup does not establish OOS value demotion. See the [expectation review](triage-expectations_1ec35f8_codex.md#s04-cardinality-changes-cannot-be-masked).

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=58999&resultType=NOK).

### S05: Server-side loaddb signal timing assumptions

Confidence: **Medium**. Additional rows: **1**.

signals-2 lacks the expected current transaction aborted message; signals-3 finds all 1,000,000 rows when it expects fewer; signals-8 sees a completed million-object load. Suspected cause: the signal arrives after the work finishes, or workload duration / batching differs. OOS could change throughput, but the available logs do not prove that causal link or a signal-handling defect.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=58999&resultType=NOK).

### S06: SQL replay timeout in sql_05

Confidence: **Low**. Additional rows: **1**.

The debug shell log reports timeout and blank result. Suspected cause: workload completion, locking, or SQL-runner stall. A timeout alone does not identify a deadlock, OOS defect, or deterministic failure.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=59001&resultType=NOK).

### Q01: SQL-by-CCI auto-increment result mismatch

Confidence: **Medium-low**. Additional rows: **1**.

The fetched statement table for alter_change_026.sql shows the fourth generated id as 21 where the answer expects 4; subsequent ordered output also differs. Suspected cause: serial allocation/cache behavior or CCI/session setup. This is a real observed result mismatch, not just whitespace. Tiny INT/FLOAT rows do not establish OOS demotion. It is absent from the failure list of the completed develop sql_by_cci run.

[QA evidence](https://qahome.cubrid.org/qaresult/showFailResult.nhn?m=showFailVerifyItem&statid=285707&srctb=resultstat).

[Statement-level expected/actual table](https://qahome.cubrid.org/qaresult/showfile.nhn?filePath=sql%2F_17_sql_extension2%2F_02_full_test%2F_03_alter_table%2F_01_alter_change%2Fcases%2Falter_change_026.sql&statid=285707&itemid=3458354&tc=sql_by_cci&buildId=11.5.0.2625-1ec35f8&isNew=N&m=showCaseFile&isSuccessFul=false&srctb=resultstat).

### Q02: SQL-by-CCI trace collection/normalization mismatch

Confidence: **Medium**. Additional rows: **1**.

The cbrd_26104 statement table shows show trace returning null for statements 90, 111, 114, 117, 120, and 123 instead of expected parallel/subquery plans; statement 104 shows a dual scan rather than the expected trace. Suspected cause: CCI trace lifetime, session collection, or answer normalization. Normal sql/sql_debug pass the corpus. That distinction directs attention to the interface/trace path, without proving an interface-only cause.

[QA evidence](https://qahome.cubrid.org/qaresult/showFailResult.nhn?m=showFailVerifyItem&statid=285707&srctb=resultstat).

[Statement-level expected/actual table](https://qahome.cubrid.org/qaresult/showfile.nhn?filePath=sql%2F_36_guava%2Fcbrd_26104%2Fcases%2Fcbrd_26104.sql&statid=285707&itemid=3458362&tc=sql_by_cci&buildId=11.5.0.2625-1ec35f8&isNew=N&m=showCaseFile&isSuccessFul=false&srctb=resultstat).

### H01: HA alternate-host/failover client failure

Confidence: **Low**. Additional rows: **1**.

bug_bts_6198 counts one FAIL in java.log after TestAlhost. Suspected cause: alternate-host connection/failover behavior or HA environment convergence. The failing Java assertion text is not retained in the visible result summary, so no narrower cause is justified.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=59000&resultType=NOK).

### H02: HA mode-change and connection availability

Confidence: **Medium-low**. Additional rows: **1**.

bug_bts_6803 subcases 1, 2, and 4 fail; the console records transactions aborted due to server failure or mode change and failures connecting to hatestdb on func13. Suspected cause: failover readiness/timing or host availability. No crash stack in this case establishes an OOS storage failure.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=59000&resultType=NOK).

### H03: Unexpected HA topology member in heartbeat output

Confidence: **High**. Additional rows: **1**.

cbrd_24738 subcases 4 and 5 have an extra Node func13 ... state unidentified line in actual heartbeat status, absent from master_status.answer. Suspected cause: stale/additional HA cluster membership or environment isolation, rather than a demonstrated replicated-data error.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=59000&resultType=NOK).

### H04: HA online-index cleanup not visible on replicas

Confidence: **Medium-low**. Additional rows: **2**.

cbrd_21506_02 and cbrd_22705_03 fail subcase 8: grep idx1 produces zero matches where both checked replica logs require three. Suspected cause: replica schema/index propagation or timing, or unexpected output/error in those logs. The existence/count assertion alone cannot distinguish a replication defect from a harness problem.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=59000&resultType=NOK).

### H05: Physical heap offsets differ by eight bytes

Confidence: **High**. Additional rows: **1**.

cbrd_26374_ha compares physical record diagnostics. Actual t_offset values include 1192,1280,1368 against expected 1184,1272,1360: a consistent +8-byte shift. Suspected cause: record-layout/physical-diagnostic expectation drift under the OOS branch. This is not by itself proof of logical data corruption. This testcase contains no CDC/flashback operation in its captured console and remains in the non-CDC inventory.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=59000&resultType=NOK).

### H06: HA UUID/DDL schema and expectation mismatch

Confidence: **Medium-low**. Additional rows: **1**.

cbrd_26486 fails schema output comparisons: INTEGER nullability differs; expected UUID columns are missing from actual output; actual logs include unknown-class/attribute errors for UUID tables. Suspected cause: incomplete DDL setup/propagation, failed earlier creation, or testcase/answer drift. Full console content is truncated by the portal, so assigning this to OOS replication would exceed the evidence.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=59000&resultType=NOK).

### H07: HA SQL replay discrepancy; detailed cause unavailable

Confidence: **Low**. Additional rows: **7**.

Seven additional ha_repl_debug testcases are listed as NOK, but the fetched endpoint contains test names and HA slot names only. Three involve shared attributes; others cover an old issue, MAX/GROUP BY, Korean identifiers, and WIDTH_BUCKET NULL. Suspected areas are shared-attribute representation/DDL replay, replication value reconstruction, or per-slot harness/answer differences. These are candidate areas, not established causes. The portal marks all eight feature ha_repl_debug failures as previously known (New=0), but seven do not occur in this exact baseline.

[QA evidence](https://qahome.cubrid.org/qaresult/showFailResult.nhn?m=showFailVerifyItem&statid=6159&srctb=ha_repl_main&failType=ha_repl).

### P01: Strict performance improvement threshold missed at equality

Confidence: **High**. Additional rows: **1**.

cbrd_23865 subcase 2 returns the correct 47,000 count, with current timing 26 seconds versus reference 34 seconds. The difference is exactly 8 seconds; the testcase requires strictly more than 8. Subcases 1 and 3 pass. Suspected cause: a brittle timing threshold or real performance margin change. This run still beats the reference; it does not show a wrong result or establish a performance regression against develop, whose suite is incomplete.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=59009&resultType=NOK).

Local supporting testcase: [strict >8-second check](https://github.com/cubrid/cubrid-testcases-private-ex/blob/1274a4d6462a3d5ae5daeb004e042f89496991d8/shell_perf/_06_issues/_21_1h/cbrd_23865/cases/cbrd_23865.sh#L108).

### P02: Prefix-index versus comparison-query output discrepancy

Confidence: **Low**. Additional rows: **1**.

_03_data_validate_ja_01 subcase 3 fails diff res3.log res33.log. The visible Japanese string/GROUP BY output is truncated before a decisive differing row is recoverable. Suspected areas: prefix-index/collation grouping, query ordering, or result formatting. Do not label this harmless ordering drift or data corruption without the complete diff.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=59009&resultType=NOK).

### I02: Isolation client-output ordering differs

Confidence: **Medium-high**. Additional rows: **1**.

insert_odku_online_index_01.ctl moves a 1 row affected line from before to after a 2 rows affected line, while the visible final selected rows match. The QA verification table says not reproduced. Suspected cause: nondeterministic ordering of concurrent-client completion output, rather than a demonstrated OOS data error.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=59007&resultType=NOK).

### C01: CCI expected secondary log is empty

Confidence: **Low**. Additional rows: **1**.

bug_bts_7941 subcase 1 passes; subcase 2 fails because logs1/cci_2_id.log is empty after a five-second wait. Suspected cause: client worker startup/completion, logging, or connection timing. Develop cci has no result in this snapshot, so additional-regression attribution is unavailable.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=58996&resultType=NOK).

### C02: CCI timeout without result

Confidence: **Low**. Additional rows: **2**.

bug_cubridsus2771 reports timeout and blank result in feature cci and cci_debug. Suspected cause: unfinished worker/connection wait or runtime environment. Develop cci is absent and cci_debug is only 215/322 complete; neither provides a completed comparator.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=59008&resultType=NOK).

### J01: JDBC LOB test exhausts the Java heap

Confidence: **Medium**. Additional rows: **1**.

testBlob01() reports Java heap space. Develop also reports Java heap space in testClob01() and testBlob03(), which feature shares. Suspected cause: heap budget/LOB materialization or memory retained by test ordering. The extra failing method is real at testcase identity level, but evidence does not establish an engine memory leak or OOS causality.

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=59022&resultType=NOK).

### R01: Vacuum fixes a deallocated page as OLD_PAGE

Confidence: **High for immediate assertion; low for origin**. Additional rows: **1**.

RQG dead_data_03_big_record.sh retains five analyzed server cores: one OLD_PAGE write fix through vacuum_heap_page and four OLD_PAGE read fixes through index-to-heap lookup. All reach the PAGE_UNKNOWN/deallocated-page assertion in pgbuf_fix_debug. Final standalone checkdb returned 254 with an empty captured log; the corruption type is not identified. Investigate common heap-page lifetime, queued vacuum work, stale index OIDs and post-crash recovery before proposing a patch. Develop RQG has no result. The page_buffer.c diff is only PAGE_OOS status accounting elsewhere; the assertion site does not establish OOS causality. See the [RQG source reconstruction](triage-rqg-vacuum_1ec35f8_codex.md).

[QA evidence](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=58998&resultType=NOK).

Exact feature source: [deallocated-page assertion](https://github.com/CUBRID/CUBRID/blob/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21/src/storage/page_buffer.c#L2472), [vacuum caller](https://github.com/CUBRID/CUBRID/blob/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21/src/query/vacuum.c#L1693).

## Complete additional-candidate inventory

| Assessment | Suites | Exact testcase identity |
|---|---|---|
| C01 | cci | `interface/CCI/shell/_20_cci/_12_issue/bug_bts_7941/cases/bug_bts_7941.sh` |
| C02 | cci, cci_debug | `interface/CCI/shell/_20_cci/_12_issue/bug_cubridsus2771/cases/bug_cubridsus2771.sh` |
| H01 | ha_shell | `HA/shell/_12_bts_issue/bug_bts_6198/cases/bug_bts_6198.sh` |
| H02 | ha_shell | `HA/shell/_12_bts_issue/bug_bts_6803/cases/bug_bts_6803.sh` |
| H03 | ha_shell | `HA/shell/_12_bts_issue/cbrd_24738/cases/cbrd_24738.sh` |
| H04 | ha_shell | `HA/shell/_31_cherry/issue_21506_online_index/cbrd_21506_02/cases/cbrd_21506_02.sh` |
| H04 | ha_shell | `HA/shell/_31_cherry/issue_22705_online_index/cbrd_22705_03/cases/cbrd_22705_03.sh` |
| H05 | ha_shell | `HA/shell/_40_guava/cbrd_26374_ha/cases/cbrd_26374_ha.sh` |
| H06 | ha_shell | `HA/shell/_40_guava/cbrd_26486/cases/cbrd_26486.sh` |
| H07 | ha_repl_debug | `sql/_13_issues/_11_1h/cases/bug_bts_3742.test` |
| H07 | ha_repl_debug | `sql/_14_mysql_compatibility_2/_04_table_related/_02_alter_change_column/_16_shared_attribute/cases/name.test` |
| H07 | ha_repl_debug | `sql/_14_mysql_compatibility_2/_04_table_related/_02_alter_change_column/_16_shared_attribute/cases/name_order.test` |
| H07 | ha_repl_debug | `sql/_23_apricot_qa/_01_sql_extension3/_05_analytic_functions/_04_max/cases/max_group_by.test` |
| H07 | ha_repl_debug | `sql/_23_apricot_qa/_03_i18n/ko_KR/_09_identifiers/_01_table/cases/Column001.test` |
| H07 | ha_repl_debug | `sql/_24_aprium_qa/_01_i18n/issue_9403_collationperclass/cases/12_shared_attribute.test` |
| H07 | ha_repl_debug | `sql/_24_aprium_qa/_02_sql_extension/issue_4209_width_bucket/cases/width_bucket_null.test` |
| I01 | isolation, isolation_debug | `isolation/_01_ReadCommitted/partition_table/range/dml_ddl/reorganization_select_01.ctl` |
| I02 | isolation_debug | `isolation/_06_features/cbrd_22705_online_index_parallel/dml_online_index/insert_odku_online_index_01.ctl` |
| J01 | jdbc | `interface/JDBC/test_jdbc/src/cubrid/jdbc/driver/TestAPIS825.java => testBlob01()` |
| P01 | shell_perf | `shell_perf/_06_issues/_21_1h/cbrd_23865/cases/cbrd_23865.sh` |
| P02 | shell_perf | `shell_perf/_27_aprium_qa/_01_i18n/issue_7737_prefixkey/_03_data_validate_ja_01/cases/_03_data_validate_ja_01.sh` |
| Q01 | sql_by_cci | `sql/_17_sql_extension2/_02_full_test/_03_alter_table/_01_alter_change/cases/alter_change_026.sql` |
| Q02 | sql_by_cci | `sql/_36_guava/cbrd_26104/cases/cbrd_26104.sql` |
| R01 | RQG | `random_query_generator/_03_mvcc/vacuum/dead_data_03/dead_data_03_big_record/cases/dead_data_03_big_record.sh` |
| S01 | shell, shell_debug | `shell/_25_unstable/_06_issues/_14_2h/bug_bts_15529/cases/bug_bts_15529.sh` |
| S02 | shell, shell_debug | `shell/_25_unstable/_38_fig/cbrd_24501_dblink_dml/cbrd_24501_cubrid/cases/cbrd_24501_cubrid.sh` |
| S02 | shell, shell_debug | `shell/_25_unstable/_38_fig/cbrd_24501_dblink_dml/cbrd_24501_mariadb/cases/cbrd_24501_mariadb.sh` |
| S02 | shell, shell_debug | `shell/_25_unstable/_38_fig/cbrd_24501_dblink_dml/cbrd_24501_mysql/cases/cbrd_24501_mysql.sh` |
| S02 | shell, shell_debug | `shell/_25_unstable/_38_fig/cbrd_24501_dblink_dml/cbrd_24501_oracle/cases/cbrd_24501_oracle.sh` |
| S03 | shell, shell_debug | `shell/_25_unstable/_37_elderberry/cbrd_23843_dblink/cbrd_24420_mysql/cases/cbrd_24420_mysql.sh` |
| S03 | shell, shell_debug | `shell/_25_unstable/_37_elderberry/cbrd_23843_dblink/cbrd_24420_oracle/cases/cbrd_24420_oracle.sh` |
| S03 | shell, shell_debug | `shell/_25_unstable/_38_fig/cbrd_24551/01_mariadb_general/cases/01_mariadb_general.sh` |
| S04 | shell, shell_debug | `shell/_25_unstable/_40_guava/cbrd_26354/cases/cbrd_26354.sh` |
| S05 | shell | `shell/_25_unstable/_35_cherry/issue_21654_server_side_loaddb/signals/cases/signals.sh` |
| S06 | shell_debug | `shell/_25_unstable/_06_issues/_20_1h/cbrd_23613_6/sql_05/cases/sql_05.sh` |

## Baseline failure overlap

These 36 rows are removed from the additional-testcase shortlist because the same testcase fails in the same develop suite. Their exact identities and both sets of raw pages are retained in the JSON. Complete symptom equivalence is not claimed for rows exposing only verification metadata.

| Suite | Testcase | Observed overlap / limitation |
|---|---|---|
| shell_debug | `shell/_25_unstable/_06_issues/_18_2h/cbrd_22484/cases/cbrd_22484.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell | `shell/_25_unstable/_06_issues/_18_2h/cbrd_22484/cases/cbrd_22484.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell | `shell/_06_issues/_17_1h/cbrd_20145_1/cases/cbrd_20145_1.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell | `shell/_25_unstable/_06_issues/_14_2h/bug_bts_11320/cases/bug_bts_11320.sh` | Both fail; captured assertions vary. Feature also has an OK subcase where develop has NOK. |
| shell_debug | `shell/_25_unstable/_06_issues/_14_2h/bug_bts_11320/cases/bug_bts_11320.sh` | Both fail; captured assertions vary. Feature also has an OK subcase where develop has NOK. |
| shell | `shell/_25_unstable/_06_issues/_17_1h/cbrd_20580/cases/cbrd_20580.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell_debug | `shell/_25_unstable/_06_issues/_17_1h/cbrd_20580/cases/cbrd_20580.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell | `shell/_25_unstable/_06_issues/_23_1h/cbrd_24533/cases/cbrd_24533.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell | `shell/_25_unstable/_35_cherry/issue_22015_QEWC/multi_queries_2/cases/multi_queries_2.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell_debug | `shell/_25_unstable/_35_cherry/issue_22015_QEWC/multi_queries_2/cases/multi_queries_2.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell | `shell/_25_unstable/_38_fig/cbrd_24916_check_index_ovfps/cases/cbrd_24916_check_index_ovfps.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell_debug | `shell/_25_unstable/_38_fig/cbrd_24916_check_index_ovfps/cases/cbrd_24916_check_index_ovfps.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell | `shell/_25_unstable/_39_fig_cake/cbrd_25230/cases/cbrd_25230.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell_debug | `shell/_25_unstable/_39_fig_cake/cbrd_25230/cases/cbrd_25230.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell | `shell/_25_unstable/_39_fig_cake/cbrd_25278_memmon/cbrd_25278_option/cases/cbrd_25278_option.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell_debug | `shell/_25_unstable/_39_fig_cake/cbrd_25278_memmon/cbrd_25278_option/cases/cbrd_25278_option.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell | `shell/_25_unstable/_39_fig_cake/cbrd_25278_memmon/cbrd_25278_tracking/cases/cbrd_25278_tracking.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell | `shell/_25_unstable/_40_guava/cbrd_26111/cases/cbrd_26111.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell_debug | `shell/_25_unstable/_40_guava/cbrd_26111/cases/cbrd_26111.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell | `shell/_40_guava/cbrd_26501/cases/cbrd_26501.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell_debug | `shell/_40_guava/cbrd_26501/cases/cbrd_26501.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| shell_perf | `shell_perf/_06_issues/_24_2h/cbrd_25454/cases/cbrd_25454.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| jdbc | `interface/JDBC/test_jdbc/src/com/cubrid/jdbc/test/spec/statement/TestSetObjectJavaTime.java => testTimeZoneColumnTakesTheValueButCannotGiveItBack()` | Both show UTC UTC expected versus Asia/Seoul KST actual. |
| sql_by_cci | `sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/04_normal_percent_type_parameter.sql` | Both fail lists contain this case; shared-assertion details not compared. |
| sql_by_cci | `sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/05_error_percent_type_return.sql` | Both fail lists contain this case; shared-assertion details not compared. |
| sql_by_cci | `sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/05_normal_percent_type_return.sql` | Both fail lists contain this case; shared-assertion details not compared. |
| sql_by_cci | `sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/24_normal_viewtable_percent_type_parameter.sql` | Both fail lists contain this case; shared-assertion details not compared. |
| sql_by_cci | `sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/25_error_viewtable_percent_type_return.sql` | Both fail lists contain this case; shared-assertion details not compared. |
| sql_by_cci | `sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/25_normal_viewtable_percent_type_return.sql` | Both fail lists contain this case; shared-assertion details not compared. |
| sql_by_cci | `sql/_19_apricot/_02_pseudo_col_in_default/_01_create_table/cases/1001.sql` | Both fail lists contain this case; shared-assertion details not compared. |
| sql_by_cci | `sql/_36_guava/cbrd_26258/cases/join_orderby_skip.sql` | Both fail lists contain this case; shared-assertion details not compared. |
| sql_by_cci | `sql/_36_guava/cbrd_26473/cases/cbrd_26473.sql` | Both fail lists contain this case; shared-assertion details not compared. |
| ha_repl_debug | `sql/_13_issues/_23_1h/cases/cbrd_24544.test` | Both NOK lists contain this case; no per-case result diff returned. |
| ha_shell | `HA/shell/_22_ha/bug_xdbms2525/cases/bug_xdbms2525.sh` | Same failure/assertion family visible; exact byte-for-byte equivalence not asserted. |
| jdbc | `interface/JDBC/test_jdbc/src/cubrid/jdbc/driver/TestAPIS825.java => testClob01()` | Both show Java heap space. |
| jdbc | `interface/JDBC/test_jdbc/src/cubrid/jdbc/driver/TestAPIS825.java => testBlob03()` | Both show Java heap space. |

## Limits and priority for subsequent work

This report is complete for the requested read-only assessment. It is not a merge certificate.

1. Address the missing CBRD-27407 develop fix through the integration process; the existing upstream fix has direct evidence matching the failure. No new OOS fix is proposed for that case.
2. Treat the RQG deallocated-page assertion as a serious unresolved crash; its develop comparator is absent. Do not classify it as CDC or hide it behind the New count.
3. Review justified expectation drift separately from functional failures: error defaults, physical offsets, plan costs/dumps, and concurrent output ordering. No answers were edited.
4. Obtain complete HA DDL/index/replication diffs and exact QA corpus revisions before assigning those cases to engine owners. The portal truncates some consoles at about 300 KB; a missing decisive diff is explicitly a limitation.
5. Complete the missing/incomplete baseline comparisons if qualification is later resumed. Feature ha_repl, shell_heavy, shell_long, shell_ext, and unittest have no results; develop CCI, RQG, and unit suites are absent/incomplete. Baseline cci_debug is 215/322 complete and shell_perf is 47/58 completed verdicts in the snapshot. Feature RQG has 98 verdicts out of 99, so its one failure is observed but its aggregate run is incomplete.

## Reproducible evidence and parser audit

The generic fetcher initially returned 518 deduplicated develop findings because it also collects interface compatibility results and collapses some variant identities. That number is not the requested Linux functional baseline. The comparison instead selects `table[name=linux_func]`, maps result URLs to the exact row suite, removes duplicate repository/home prefixes, and retains Java method names. lxml repairs an unclosed first-row rowspan cell. Empty unit-result pages are not converted into failing testcases.

Parsed failure identity counts equal the reported failure counts for every numeric suite row in both snapshots, including all four JDBC methods. Feature fetcher warnings: 7; develop: 9. Raw inspection recovered the identity omissions; missing HA per-case bodies remain limitations. Count reconciliation proves inventory coverage, not root-cause coverage.

[Comparison parser](compare_qa_1ec35f8_codex.py) and [full machine-readable comparison](comparison_1ec35f8_codex.json). Decisive symptom excerpts are retained in the reports and supporting investigation notes.

See [recomputation instructions](README.md#recomputing-the-inventory). The parser reads retained QA snapshots; it does not rerun tests. Reports include manual source assessments and are maintained directly.

- feature: `/home/vimkim/gh/cubrid-qahome-fetcher/runs/20260929-140608-11.5.0.2625-1ec35f8`; [functional QA summary](https://qahome.cubrid.org/qaresult/showFuntionRes.nhn?tree_id=5328&buildId=11.5.0.2625-1ec35f8); [functional summary](https://qahome.cubrid.org/qaresult/showFuntionRes.nhn?tree_id=5328&buildId=11.5.0.2625-1ec35f8); HTTP 200, 78762 bytes, requested build label verified.
- develop: `/home/vimkim/gh/cubrid-qahome-fetcher/runs/20260929-140608-11.5.0.2622-e1c3db1`; [functional QA summary](https://qahome.cubrid.org/qaresult/showFuntionRes.nhn?tree_id=5329&buildId=11.5.0.2622-e1c3db1); [functional summary](https://qahome.cubrid.org/qaresult/showFuntionRes.nhn?tree_id=5329&buildId=11.5.0.2622-e1c3db1); HTTP 200, 80889 bytes, requested build label verified.
