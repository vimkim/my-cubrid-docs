# CI Failure Analysis: PR #7927 at `512b361`

## Executive Summary

All requested runtime suites finished: medium3, SQL2 and shell20 failures, with zero error/unknown records. Shell has30 skips. Builds and five static checks passed. The repaired cbrd_20683 bootstrap case now passes remotely. Acceptance remains open: four shell failures are new relative to878f18b and require investigation. All three collector bundles are complete; fresh-parent attribution and acceptance reconciliation remain in progress.

## CI Snapshot

| Suite | Job | Total | Success | Failure | Skipped | Error | Unknown |
|---|---|---:|---:|---:|---:|---:|---:|
| medium | [job 155215](https://circleci.com/gh/CUBRID/cubrid/155215) | 975 | 972 | 3 | 0 | 0 | 0 |
| sql | [job 155214](https://circleci.com/gh/CUBRID/cubrid/155214) | 17463 | 17461 | 2 | 0 | 0 | 0 |
| shell | [job 155217](https://circleci.com/gh/CUBRID/cubrid/155217) | 3277 | 3227 | 20 | 30 | 0 | 0 |

## Evidence Scope

Pinned source `512b361a7a34a4857cd8ad91c496c7e0e94c0769`, PR https://github.com/CUBRID/cubrid/pull/7927. Current local and remote heads were reverified. Collection date2026-09-15 KST. Job identity metadata confirms this revision and workflow20f7ce36-11b5-4ce1-94e1-838aec4803b7.

Collector0.1.0 (3e9502f72350): medium and SQL bundles completed with exit0; shell collection also completed with exit0 (165 text artifacts,181208528 bytes). Separate read-only v1.1 API test inventories supply interim counts; that endpoint returns the complete tests array, without a pagination token. Durable roots:

- `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/512b361`
- `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/512b361-api-20260914`

## Failure Inventory

Every failure in the three API inventories appears once below. Unknown attribution is intentional while evidence collection and paired replay are incomplete.

| Suite | Test | Observed signature | Category | PR relation |
|---|---|---|---|---|
| medium | `medium/_02_xtests/cases/to_char_order_by.sql` | Same values in a different order; failing SELECT lacks ORDER BY | Ordering expectation | unlikely; new-parent replay pending |
| medium | `medium/_02_xtests/cases/to_number_order_by.sql` | Same values in a different order; failing SELECT lacks ORDER BY | Ordering expectation | unlikely; new-parent replay pending |
| medium | `medium/_02_xtests/cases/to_timestamp_order_by.sql` | Same values in a different order; failing SELECT lacks ORDER BY | Ordering expectation | unlikely; new-parent replay pending |
| sql | `sql/_13_issues/_14_1h/cases/bug_bts_10516.sql` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| sql | `sql/_15_fbo/_02_qa_test/cases/fbo_ddl02.sql` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| shell | `shell/_36_damson/cbrd_23608_tde/tbl_enc_08/cases/tbl_enc_08.sh` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| shell | `shell/_36_damson/cbrd_23608_tde/log_enc_04/cases/log_enc_04.sh` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| shell | `shell/_36_damson/cbrd_23608_tde/tbl_enc_14/cases/tbl_enc_14.sh` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| shell | `shell/_06_issues/_15_1h/bug_bts_15489/cases/bug_bts_15489.sh` | Index has112 pages; testcase requires0 < pages <100 after60 seconds | Index capacity / reclamation | unknown |
| shell | `shell/_39_fig_cake/cbrd_24044_enhance_optimizer/cbrd_25080/cases/cbrd_25080.sh` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| shell | `shell/_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| shell | `shell/_36_damson/cbrd_23608_tde/file_enc_03/cases/file_enc_03.sh` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| shell | `shell/_36_damson/cbrd_23608_tde/file_enc_02/cases/file_enc_02.sh` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| shell | `shell/_36_damson/cbrd_23608_tde/temp_enc_09/cases/temp_enc_09.sh` | Two expected sort_listfile encryption diagnostic lines are absent | TDE diagnostic expectation | unknown |
| shell | `shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| shell | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| shell | `shell/_06_issues/_26_1h/cbrd_26527/cases/cbrd_26527.sh` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| shell | `shell/_36_damson/cbrd_23608_tde/file_enc_04/cases/file_enc_04.sh` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| shell | `shell/_06_issues/_11_2h/bug_bts_5423/cases/bug_bts_5423.sh` | Extra index_build_buffer_size=2.0M parameter in utility output | Expected parameter list | unlikely; parent parameter exists |
| shell | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| shell | `shell/_36_damson/cbrd_23608_tde/file_enc_07/cases/file_enc_07.sh` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| shell | `shell/_36_damson/cbrd_23608_tde/file_enc_05/cases/file_enc_05.sh` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| shell | `shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| shell | `shell/_35_cherry/issue_21654_server_side_loaddb/bigPageSize/cases/bigPageSize.sh` | Test failed; artifact/source analysis pending | Unclassified | unknown |
| shell | `shell/_36_damson/cbrd_23608_tde/file_enc_01/cases/file_enc_01.sh` | Test failed; artifact/source analysis pending | Unclassified | unknown |

## Root-Cause Analysis

Medium uses public testcase revision6ab786aa9145489ce1e1336dd829779e9de8c58a. All three downloaded case files and all three answer files are byte-identical to the retained b10727db4 fixtures. The diffs show only ordering changes in conversion queries without ORDER BY. This supports an ordering-expectation diagnosis, but old9c768e4 replay is not a fresh38093ea baseline result.

New shell failures relative to878f18b are bug_bts_5423, bug_bts_15489, temp_enc_09, and cbrd_27075. The first exposes an additional parameter already present in target38093ea;15489 records112 index pages against a below100 threshold, and temp_enc_09 lacks two expected sort diagnostic lines. CDC27075 currently has only a generic failure message in the test inventory and needs its artifacts before diagnosis.

Four previous shell failures now pass: bug_bts_5048, cbrd_20683, cbrd_20145_1, and issue_11161_volume. Passing these cases does not imply subsystem-wide correctness or classify the remaining failures.

## Recommended Actions

Collector session1966 finished successfully. Inspect all failure artifacts and exact private testcase/testtools checkout revisions. Prioritize CDC27075 and index-capacity15489; reproduce on fresh pinned parent38093ea and candidate512b361 where needed. Repair introduced failures, verify, and reconcile the producer/resource acceptance matrix. Do not alter expected answers merely to make CI green.

## Evidence and Limitations

Medium summary, all medium failure messages/diffs and source hashes, complete API test inventories, exact job identities, and four new shell messages were inspected. SQL diffs show initial error-1383 on the wide LOB insert, followed by zero-row cascading results. Both case/answer pairs are byte-identical to retained b10727db4 fixtures, but a fresh38093ea baseline is still needed. Remaining shell root causes are not yet assessed. Source/testcase changes prevent carrying the previous23-baseline classification forward. Historical waiting snapshot is superseded by these terminal results. V21-CI and V21-ACCEPT remain open. This report is local and unpublished.

## Replay preparation — 2026-09-15 KST

All50 shell checkout logs identify private testcase6ce89517e700f8f41e9fa451e3df24cf9e52d7a0 and tools a1bec8762644f58dc48c99a8dfb227fa0bcc70ca. Complete observations are shell-checkout-identities.json and shell-checkout-node*.log in the separate API directory.

The four newly failing shell directories were extracted unchanged from that exact Git object. Fresh isolated parent38093ea and candidate512b361 installations are running the selected four-case CTP scenario. Process/network/IPC/user namespaces isolate cleanup; a private dummy network interface provides the CDC connection prerequisite. No answers or scripts were changed. Binary hashes, scenario, command and retained outputs are under /home/vimkim/.cache/codex/pr7927-512b361. Sessions63248/94155 remain live; initial testcase5423 creates several large database volumes. No replay outcome is claimed yet.

## Completed shell collection and paired observations

All20 shell XML failure signatures are preserved in shell-observed-signatures.json in the API evidence directory. Source auto-download found no revision-qualified private links; independent50-node checkout verification and exact local Git objects establish source identity.

Fresh parent38093ea and candidate512b361 both fail bug_bts_5423 with the extra index_build_buffer_size parameter and temp_enc_09 with missing sort diagnostics. Both pass bug_bts_15489 locally; its CI112-page result is therefore not reproduced or explained. These are per-case observations from still-running four-case scenarios, not final suite outcomes. CDC27075 replay remains live.

Remote CDC27075 node33 feedback records two extraction errors per page size; node33 final XML records four per size. Both show FINAL_SEQ2000, zero corruption, and nonzero extracted items. These differing retained observations must not be collapsed into one invented count. Exact error return codes are absent from those summaries; do not equate this with the historical CDC27064 server assertion.

Other shell signatures are physical file/page TDE diagnostic differences; default OOS error-list differences (9836/14120); differing external LOB locators (bigPageSize); rejected invalid partition input; missing expected MULTIPAGE HFID (26527); optimizer selectivity/cardinality differences (25080); and CDC27064 extraction rc=-10. All remain failed tests; current-parent attribution must be established independently.

Fresh SQL/medium pairs use all10 downloaded case/answer files byte-for-byte. Managed sessions28184 (parent) and58704 (candidate) run SQL then medium sequentially in separate isolated installations. Provenance and logs: /home/vimkim/.cache/codex/pr7927-512b361-sql.

## Completed fresh-parent pairs — 2026-09-15 KST

SQL executes exactly2 cases and fails both on38093ea and512b361; medium executes exactly3 and fails all three on both. All five paired actual-result files are byte-identical, recorded in /home/vimkim/.cache/codex/pr7927-512b361-sql/paired-output.json. Candidate engine hashes match the published integration provenance; its embedded6acfbb8 version string predates the merge commit. Source hashes were revalidated against512b361. The preserved preexisting JDBC checkout is explicitly recorded; these runs use the recorded installed jars.

The four-case shell pair completed on both:4 executed,3 failed,1 passed,0 skipped.5423 and temp_enc09 match the parent failure signatures. CDC27075 fails on both with extraction rc=-10 captured before cleanup; all three page sizes finish2000 updates and report zero corruption. Parent extraction-error counts are3/3/3 and candidate4/4/2. This demonstrates a preexisting extraction failure, not equality of timing-sensitive counts or proof of the exact internal cause.15489 passes with89 parent pages and88 candidate pages; CI112 remains unexplained.

The remaining16 shell cases are replaying unchanged on current parent38093ea in session69521, under /home/vimkim/.cache/codex/pr7927-512b361-remaining. A separate ci_optdebug_gcc preset was declared locally in the isolated parent worktree and validated by CMake before invoking the standard local build helper. It selects OptDebug to match CI's optimized assertions-enabled mode; previous replays use Debug (-O0). Build session45336 is live. This mode difference is a hypothesis for index-reclamation timing, not an established root cause.

## Index-capacity failure resolved as parent-reproducible

The OptDebug parent replay completed1 testcase with1 failure and0 skips:104 index pages violate the unchanged below100 assertion. CI candidate512b361 reports112 pages. Thus the threshold-failure signature independently reproduces on parent38093ea. Exact page-count equality and a proven vacuum implementation root cause are not claimed. Earlier Debug parent/candidate89/88-page passes are retained and do not erase the CI failure.

The build command for btree.c confirms -O2 and -DCUBRID_OPTDEBUG, without -DNDEBUG. Source, binaries, testcase, command, final CTP counts and104-page output are recorded in /home/vimkim/.cache/codex/pr7927-512b361-optdebug (result.json, provenance.json, btree-compile-command.txt, baseline/runner.log and CTP logs). Build and replay sessions45336/58826 completed successfully as processes; the testcase itself failed as expected.
