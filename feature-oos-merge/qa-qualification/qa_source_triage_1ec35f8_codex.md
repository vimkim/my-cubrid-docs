# Source-level Linux QA triage and repair order

Date: 2026-09-29. Work item: 213. Feature source: `1ec35f86c5e43b9ca86d81e202c68899f8ce4f21`. Develop QA baseline: `e1c3db19800a0170942cec8b23cac4705efbb6e3`.

**First repair task: incorporate the missing CBRD-27407 fix through the agreed additive develop synchronization, then validate the two isolation variants first.** The RQG testcase is the highest-risk unresolved investigation: it contains five server cores, including four index-to-heap read failures in addition to the vacuum failure. No missing develop patch has been shown to address those cores.

This is a source-level triage plan. The user explicitly excluded testcase reproduction and code/testcase-answer changes. No tests, builds, instrumentation, merge, cherry-pick, repair, commit, push, or publication were performed in this follow-up. The diagnosis skill's feedback-loop, reproduction, instrumentation, and repair phases were skipped under that explicit instruction. Proposed causes remain hypotheses unless stated as verified source facts. Future validation below is required work, not completed work.

## Evidence boundary and counts

The [original comparison](qa_comparison_1ec35f8_codex.md) and [machine-readable inventory](comparison_1ec35f8_codex.json) retain the authenticated Linux functional QA snapshot. Windows and separate driver/server compatibility matrices are outside scope. Both source commits are fixed; a newer develop head must not silently replace the tested baseline.

The 133 failed feature suite/testcase rows reconcile as **51 CDC exclusions + 36 same-suite baseline overlaps + 46 additional non-CDC candidates**. Those 46 rows represent **35 distinct testcase identities**. A release/debug variant counts separately. Multiple subcase failures or cores within one testcase do not add inventory rows.

Six rows remain **provisional for regression attribution**: CCI 2, CCI debug 1, shell performance 2, and RQG 1. Develop CCI and RQG have no results; develop CCI debug has 215/322 completed verdicts and shell performance 47/58. Feature RQG has 98/99 verdicts. The other 40 candidates are absent from the corresponding completed develop failure lists; exact QA testcase SHAs, configuration equality, and deterministic failure equivalence are not proved. A serious provisional crash still deserves immediate investigation.

The CDC exclusions are unchanged. No HA replay testcase is excluded just because it involves replication. [ADR-0005](https://github.com/vimkim/cubrid-oos-context/blob/75f8b58674ac901d478ba60f9b2cc2fff11f66f6/docs/adr/0005-defer-oos-history-from-the-11-5-merge.md) keeps the deferred CDC cases visible rather than suppressing them.

Supporting investigations:

- [Missing develop fixes and dependency assessment](triage-develop-fixes_1ec35f8_codex.md).
- [RQG page lifecycle, five cores, and ranked predictions](triage-rqg-vacuum_1ec35f8_codex.md).
- [Expectation changes, physical layout, and testcase evidence](triage-expectations_1ec35f8_codex.md).

## Which missing develop commits explain failures?

Feature and the tested develop baseline share merge-base `c63a3b993be552ef6ad3ce244c386d5081147958`. Exactly five baseline commits are absent from feature ancestry.

| Missing commit | Verified change | Relationship to additional candidates | Integration treatment |
|---|---|---|---|
| `e1c3db198` / CBRD-27407 | Restores partial hash-aggregate list state after parallel-worker list takeover; reopens append state; handles serial fallback and allocation sizes. | **Direct match to I01**, `reorganization_select_01.ctl` in isolation and isolation_debug. QA cites the same issue and the exact develop build passes both. Seven old patch hunks match feature source; no dependency on the other four patches is apparent. | Incorporate upstream repair through true develop synchronization; keep existing testcase expectations. |
| `bc1a91769` / CBRD-27389 | Broker cancellation validation, session identity/token checks, protocol-13 handling. | Only speculative relevance to CCI cancellation/timeouts; no captured packet, broker error, or failing call links it to C01/C02. No direct serial or trace repair. | Keep coordinated with APIS-1112; do not count timeouts as fixed without validation. |
| `b27c70f14` / APIS-1112 | CCI gitlink advances to `79d0888c26a2543d31f53eb7b6c9738db110fff4`, adding cancellation token bytes and protocol 13. | Same weak timeout/interface relevance. Older feature engine/driver pair being internally matched is not proof of a protocol defect. JDBC gitlink is identical across these QA source builds. | Validate the pinned driver/broker pair together; avoid selecting one side alone. |
| `fa1187540` / CBRD-27394 | Master administrative request/security restrictions and HA request checks. | HA subsystem overlap only. No demonstrated remedy for the unexpected topology member, missing UUID tables, online-index output, or seven replay differences. | Integrate as develop-owned change; verify administration behavior separately. |
| `60f4da8e8` / CBRD-27449 | OpenSSL algorithm/context reuse and crypto/decryption changes. | No measured crypto bottleneck or decrypt error ties this to P01 or DBLink costs/ownership. | Integrate as develop-owned change; retain crypto/TDE validation without claiming a TC repair. |

None of these five commits modifies the vacuum/page-reclamation lifecycle implicated by RQG. Upstream fix correspondence is strongest for CBRD-27407; local runtime causality has not been established for any case during this investigation. Exact patch and source links appear in the [develop-fix note](triage-develop-fixes_1ec35f8_codex.md).

## Prioritized action table

P0 means urgent crash/lifecycle investigation. P1 means known crash repair or possible functional defect. P2 means interface, timing, environment, or incomplete-evidence investigation. P3 means a constrained expectation-maintenance candidate. This is risk ordering; execution can start with the well-supported upstream fix while the RQG investigation proceeds separately.

The assessment IDs match the original report and the exact testcase inventory below. Confidence qualifies the stated mechanism or hypothesis, not a claim of reproduced root cause. All validation in the last column is prospective.

| Priority / ID | Affected TCs / additional rows | Evidence and proposed change or next action | Confidence / comparator | Eventual validation required |
|---|---|---|---|---|
| P0 / R01 | `dead_data_03_big_record` / **1** | Five cores: vacuum OLD_PAGE write and four index-to-heap OLD_PAGE reads. Investigate shared heap-page lifetime, queued vacuum work, relocation notifications, and index OIDs; collect allocation/deallocation and WAL history. No code fix is justified yet; preserve assertions. | High for captured invariant; low for originating lifecycle. **Provisional baseline**. | Same seeded workload and corpus on both builds; all five stack signatures; correct data/index reachability before and after vacuum/recovery; no cores. |
| P1 / I01 | `reorganization_select_01.ctl`, release + debug / **2** | Missing CBRD-27407 with matching QA issue and source path. Incorporate upstream fix through additive develop merge, without an OOS-specific replacement. | High source/QA match; completed baseline. | Both isolation modes; exact partition/parallel hash aggregation path; serial fallback; result equality and server survival. |
| P1 / Q01 | `alter_change_026.sql`, SQL-by-CCI / **1** | Fourth generated ID is 21 instead of 4 after ALTER. Source cache default is 20, so a lost/re-reserved block is a falsifiable lead. Inspect serial OID, issued value, cache tail, ALTER/decache results, and client/session settings. Do not bless 21 as an answer update. | Medium-low causal explanation; completed baseline. | Exact same DDL, cache settings, CCI/session handling on both builds; serial uniqueness and expected next value across ALTER; inspect cache-flush errors. |
| P1 / S03 | DBLink MySQL, Oracle, MariaDB-general, both modes / **6** | Server owner and validation-error differences are semantic; captured G1/G2 scenarios are absent from local supporting SQL/answer. Pin QA testcase/answer versions, inspect setup/catalog owners and preceding errors; narrow parser/catalog defect only after deployment evidence. | Low cause confidence; completed baseline. | Three backends, both modes; accepted syntax, authorization errors, and owners all correct. Preserve negative assertions. |
| P1 / H04 | HA `cbrd_21506_02`, `cbrd_22705_03` / **2** | Replica `idx1` match count is zero instead of three. Obtain complete replica logs, index lifecycle, applied-LSA barrier, and source assertions; distinguish schema propagation from grep/log problems. | Medium-low; completed baseline. | Online index interruption/cleanup; replica index catalogs and logical values after convergence. No reduction of expected counts without proof. |
| P1 / H06 | HA `cbrd_26486` / **1** | Missing UUID tables/attributes and nullability differences. Find first failing CREATE/ALTER and compare source/replica schemas before downstream counts. No answer rewrite for missing classes. | Medium-low; completed baseline; truncated console. | Full DDL sequence, UUID values/counts/nullability on all nodes; correct replication barrier and absence of earlier setup errors. |
| P1 / H07 | Seven HA replay cases: shared attributes, MAX/GROUP BY, Korean identifiers, WIDTH_BUCKET, old issue / **7** | Only NOK identities/slot names are retained. Obtain per-case master/replica outputs and corpus SHA before proposing replication changes. Large OOS log-applier diff is a review boundary, not proof of cause. | Low; completed baseline list, missing per-case bodies. | Seven exact cases, same locale/collation/config; source/replica result and schema equality; confirm replay path from detailed evidence. |
| P1 / P02 | Japanese prefix-key `_03_data_validate_ja_01` / **1** | `res3.log` vs `res33.log` differs; decisive rows are truncated. Obtain full diff; separate grouping/collation/index defect from permissible order. No ordering normalization until the invariant is known. | Low; **provisional baseline**. | Completed develop comparator; exact collation and query plans; logical grouped results equal under index and comparison paths. |
| P1 / S04 | `cbrd_26354`, both modes / **2** | Deeper diff inspection finds retained cardinalities changed, including 55 vs 11 and 200000 vs 99986. This testcase targets cardinality correctness. Investigate data setup/statistics and estimation source; do not refresh the answer or erase card fields. | High observed cardinality mismatch; low root cause; completed baseline. | Original cardinality assertions with known row distributions and statistics; correct query rows and intended estimate behavior; separately account for dump-format lines. |
| P2 / Q02 | `cbrd_26104.sql`, SQL-by-CCI / **1** | Seven SHOW TRACE mismatches; preceding query result rows match. Investigate session trace producer/consumer lifecycle and extra statements, not answer replacement with NULL. | Medium for trace-path focus; completed baseline. | Pin CCI/runner; capture statement order, sessions, trace flags/buffers; required parallel and serial plans present while values stay correct. |
| P2 / S06 | `cbrd_23613_6/sql_05`, debug / **1** | Shell wrapper invokes four SQL subtrees via SSL-enabled CTP and updates its corpus. Timeout has no inner failing statement. Retain nested job logs, progress, timeout and exact checkout; identify stalled phase before engine changes. | Low; completed baseline. | Isolated QA wrapper and inner workload with pinned assets/settings; completion, Fail:0 and restored environment; verify any identified defect separately. |
| P2 / C02 | CCI `bug_cubridsus2771`, both modes / **2** | Timeout/blank result. Inspect worker phase, sockets, cancellation and broker/driver versions; missing protocol fixes are only hypotheses. | Low; **provisional baseline** in both modes. | Completed matched baseline first; exact timed-out call, worker completion and cleanup; coordinated engine/CCI cancellation behavior. |
| P2 / C01 | CCI `bug_bts_7941` / **1** | Secondary log empty after five seconds. Retain worker exit/error and connection log before changing wait policy. | Low; **provisional baseline**. | Completed baseline; both subcases; intended secondary client result present; startup/connect errors still fail. |
| P2 / H01 | HA `bug_bts_6198` / **1** | Alternate-host Java test counts one FAIL; exact assertion absent. Obtain Java assertion and host transition/connect evidence. | Low; completed baseline. | Correct alternate-host retry/failover under same topology and driver; exact failed assertion passes. |
| P2 / H02 | HA `bug_bts_6803` / **1** | Mode-change aborts and failed connections. Align cluster state/timing and inspect server errors; do not merely add sleeps. | Medium-low; completed baseline. | Controlled mode transitions; intended availability and client semantics at explicit readiness points; no hidden server crash. |
| P2 / H03 | HA `cbrd_24738` / **1** | Extra unidentified func13 node in heartbeat status. Verify initial membership/configuration and management response; isolate environment if stale state is demonstrated. | High for topology mismatch; completed baseline. | Start from intended membership; status includes exactly intended nodes through subcases 4/5. Do not mask extra nodes globally. |
| P2 / J01 | JDBC `TestAPIS825.testBlob01()` / **1** | Java heap exhaustion; two other heap-failing methods overlap develop. Inspect JVM heap flags, test order and retained LOB objects; no evidence of an engine leak yet. | Medium hypothesis; completed baseline. | Same JVM/driver/heap budget/order; complete method logs and memory attribution; LOB bytes correct and heap growth bounded. |
| P2 / S05 | Server-side loaddb `signals`, release / **1** | Source polls process after two-second sleeps, then signals by process-name lookup; actual load already completed. Propose deterministic in-progress coordination only after confirming timing, not accepting full load for interruption tests. | Medium timing mechanism; completed baseline. | INT/QUIT/KILL/killtran target active loader; proper abort/commit boundary and expected incomplete row count; loader exit and signal receipt recorded. |
| P2 / P01 | `cbrd_23865`, subcase 2 / **1** | Count 47,000 correct; 34−26=8 seconds fails strict >8. Preserve threshold pending comparable measurements and performance policy decision. | High assertion mechanism; **provisional baseline**. | Completed same-host baseline, actual reference version/configuration, repeated timings with variance and query plans; functional count remains exact. |
| P3 / S02 | Four DBLink DML backends, both modes / **8** | All four inspected debug diffs show masked cost width (??? vs ????); per-digit formatter preserves digit count. Candidate: normalize only approved cost-field representation after retaining full results/plan invariants and checking both modes. | High for four debug formatting symptoms; medium causal explanation; completed baseline. | Full backend/mode diffs; row values, DML effects, pushdown behavior and selected plan requirements preserved; numeric cost differences remain reviewable. |
| P3 / I02 | `insert_odku_online_index_01.ctl`, debug / **1** | Concurrent affected-row messages move; visible final rows agree. Candidate compare per-client completion output while preserving overlapping DML and barriers. Avoid global sorting of SQL results or serializing the test workload. | Medium-high ordering hypothesis; completed baseline. | Correct affected counts assigned to each client, intended lock/schedule behavior, final rows/index consistency and no intermittent data failure. |
| P3 / H05 | HA `cbrd_26374_ha` / **1** | Added eight-byte HEAP_HDR_STATS.oos_vfid explains uniform +8 slot offsets. Candidate update only exact physical offsets after full logical/layout check; not caused by HAS_OOS header flag. | High layout mechanism; completed baseline; full HA test source unavailable. | All physical rows/spacing match new header; source/replica data/schema unchanged; no offsets outside this header shift silently accepted. |
| P3 / S01 | `bug_bts_15529`, both modes / **2** | Source explicitly adds -1383,-1385,-1386 to diagnostic defaults, matching actual output. Narrow candidate testcase-answer update for this exact default list. | High source/output match; completed baseline. | Both modes; only intended parameter changes; user-set lists/other defaults and genuine diagnostics remain checked. |

## RQG investigation boundary

The original report highlighted one vacuum stack. The source follow-up also identifies four later cores from index-to-heap reads in the same testcase. This materially widens the investigation toward common heap-page allocation/lifetime and stale index OIDs. It does not prove all five crashes share one root cause or that OOS caused them. Core files are listed by the portal; their memory contents are not available locally. A sixth core appears in an archive listing without an analyzed stack. Final standalone checkdb returned 254 with an empty captured log, so integrity verification failed without identifying a corruption type.

Use the [RQG investigation note](triage-rqg-vacuum_1ec35f8_codex.md) for exact stack signatures, source paths, and ranked falsifiable predictions. In particular, distinguish heap page removal from OOS page reclamation and read the existing interrupted-vacuum/drop guards before proposing a tolerance change. No replacement of OLD_PAGE with a permissive fix mode, assertion suppression, or silent skip is justified by current evidence.

The accepted OOS reclamation invariant and identity-stamp design are relevant context, but known OOS defects described in dated design documents cannot be assigned to this testcase without tracing the actual page and WAL sequence. This task does not expand into fixing every independent OOS merge gate.

## Further source facts for Q01, Q02, S05, and S06

For **Q01**, [the testcase](https://github.com/CUBRID/cubrid-testcases/blob/89d4ec2423d94b973b5f9cf0c612c9576b9ccce6/sql/_17_sql_extension2/_02_full_test/_03_alter_table/_01_alter_change/cases/alter_change_026.sql#L12) widens/reorders the auto-increment column after generating 1, 2, 3; the next ID is 21 in the captured statement table. The [cache default](https://github.com/CUBRID/CUBRID/blob/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21/src/base/system_parameter.c#L5525) is 20 in both source revisions. [Serial block allocation](https://github.com/CUBRID/CUBRID/blob/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21/src/query/serial.c#L1002) reserves the block end; [decache](https://github.com/CUBRID/CUBRID/blob/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21/src/query/serial.c#L1734) attempts to hand back the unissued tail. The feature serial diff changes heap-fetch policy and checks an attribute-read result; it does not newly introduce the block policy. Therefore 21 is suggestive of a cache boundary, not proof of a particular OOS bug. Inspect actual cache/catalog/session state and errors before modifying serial code or answers.

For **Q02**, actual result rows match for statements 89, 103, 110, 113, 116, 119, and 122 preceding the failing SHOW TRACE statements. [session_get_trace_stats](https://github.com/CUBRID/CUBRID/blob/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21/src/session/session.c#L2917) returns NULL when both stored plan and trace buffers are absent, and marks successful consumption for clearing. [Query completion](https://github.com/CUBRID/CUBRID/blob/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21/src/query/query_executor.c#L17690) clears trace state when flagged; [trace production](https://github.com/CUBRID/CUBRID/blob/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21/src/query/query_executor.c#L28398) installs the captured trace. Session source, CAS execution, and client query source are unchanged against the exact baseline. This supports inspecting statement/session lifecycle, trace flags, and extra requests; it does not establish who cleared or failed to produce the missing trace. Removing trace checks would discard the testcase's parallel-execution purpose.

For **S05**, [wait_loaddb_start](https://github.com/cubrid/cubrid-testcases-private-ex/blob/1274a4d6462a3d5ae5daeb004e042f89496991d8/shell/_25_unstable/_35_cherry/issue_21654_server_side_loaddb/signals/cases/signals.sh#L6) sleeps two seconds before each process check. [Signal dispatch and assertions](https://github.com/cubrid/cubrid-testcases-private-ex/blob/1274a4d6462a3d5ae5daeb004e042f89496991d8/shell/_25_unstable/_35_cherry/issue_21654_server_side_loaddb/signals/cases/signals.sh#L40) use a second process-name lookup and require an aborted/incomplete load. A completed load can race both checks. Source supports this timing lead; the captured result does not prove actual signal delivery or throughput causality.

For **S06**, [sql_05.sh](https://github.com/cubrid/cubrid-testcases-private-ex/blob/1274a4d6462a3d5ae5daeb004e042f89496991d8/shell/_25_unstable/_06_issues/_20_1h/cbrd_23613_6/sql_05/cases/sql_05.sh#L8) prepares four full SQL subtrees. It [enables SSL, changes broker/HA configuration, updates testcase branch and launches CTP](https://github.com/cubrid/cubrid-testcases-private-ex/blob/1274a4d6462a3d5ae5daeb004e042f89496991d8/shell/_25_unstable/_06_issues/_20_1h/cbrd_23613_6/sql_05/cases/sql_05.sh#L50). A wrapper timeout is not a minimized individual SQL failure. Retain `ctp_sql.log`/`ctp_sql.fail`, checkout identity, child-process progress and cleanup evidence before deciding whether SSL, HA, capacity, or an inner query stalled.

## Conditions for expectation changes

Only S01 currently has an exact source/default-output match sufficient to propose a tightly bounded answer change. H05 has a strong physical-header explanation, but full HA source and logical checks remain a condition of editing its answer. Neither change is performed here.

S02/I02 are narrower follow-up candidates, not pre-approved updates: capture every decisive diff, preserve logical outputs and schedule assertions, and normalize only a field whose variability is justified. **S04 is promoted from the original report's plan-drift suspicion to a potential cardinality-estimation regression**: deeper inspection found differences in the very card fields the testcase intentionally preserves. Keep those assertions. P01's strict timing requirement must stay intact until measurements and an explicit performance requirement justify changing it. S03/Q01/H04/H06/P02 include potential functional differences and must not be made green by answer replacement. Q02 must continue proving the intended trace path.

The [expectation review](triage-expectations_1ec35f8_codex.md) gives the source-to-output accounting, local testcase status and remaining proof requirements. Testcase fixes should be independent focused changes on the PR-associated testcase branches, preserving CDC visibility and all unrelated negative assertions.

## First narrowly scoped repair task

**Task: prepare additive develop synchronization to bring in CBRD-27407, with I01 as the first acceptance target.**

The existing [agreed integration contract](README.md#integration-contract) requires a real develop merge into the stable integration branch. Although the CBRD-27407 patch has clean source context, a standalone cherry-pick or squashed develop snapshot is not the default landing method. Do not rewrite feature history.

When repair is authorized, pin and record the chosen develop target before preparation. The five-commit assessment above applies only through `e1c3db198`; if synchronizing a newer develop head, review its extra commits separately. Prepare the merge in an isolated worktree, preserve the existing AGENTS.md change, resolve only necessary conflicts, and inspect the CBRD-27407 semantics and coordinated engine/CCI update. Keep RQG fixes, testcase-answer edits, optimizer changes, and unrelated refactors out of this first task.

Acceptance must eventually include source identity and merge ancestry, configured build checks, both I01 isolation variants, correct query results, absence of server death/cores, and evidence that the repaired parallel/hash path was exercised. Record exact engine/testcase revisions and configuration. A passing build alone cannot close the two QA failures. Publication and the later full Linux QA run remain outside this report-only task.

After this bounded integration, reclassify only failures actually verified as resolved. Continue RQG page-lifecycle diagnosis, recover the missing HA/interface artifacts, then land justified testcase changes independently. Final qualification still needs completed baseline comparisons and the integrated Linux suites: the few PR CI testcases cannot establish the requested absence of additional manual-QA failures.

## Exact additional testcase inventory

The inventory below preserves every candidate from the original comparison. The action table accounts for all 46 suite/testcase rows; no new exclusion was introduced during source triage.

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

Validation of this document: all 23 assessment families cover the original 46 rows and 35 identities; suite counts reconcile to both saved QA summaries. Local artifact links were checked. No testcase execution is implied by this document audit.
