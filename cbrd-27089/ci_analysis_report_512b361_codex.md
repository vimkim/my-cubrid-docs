# CI Failure Analysis: PR #7927 at `512b361`

## Executive Summary

All runtime suites are terminal:25 failures, zero error/unknown records,30 shell skips. Twenty-four failure signatures independently reproduce on the current parent38093ea. The remaining partition-loader case expects acceptance of invalid input; candidate rejection, batch rollback and subsequent usability were verified. No introduced defect is identified in this inventory. This does not make failed CI jobs green.

All local counterparts are terminal. The acceptance decision below reconciles this inventory with the current producer/resource evidence. The repaired4KB bootstrap testcase cbrd_20683 passes remotely.

## CI Snapshot

| Suite | CircleCI job | Total | Success | Failure | Skip | Error | Unknown |
|---|---|---:|---:|---:|---:|---:|---:|
| medium | [155215](https://circleci.com/gh/CUBRID/cubrid/155215) | 975 | 972 | 3 | 0 | 0 | 0 |
| sql | [155214](https://circleci.com/gh/CUBRID/cubrid/155214) | 17463 | 17461 | 2 | 0 | 0 | 0 |
| shell | [155217](https://circleci.com/gh/CUBRID/cubrid/155217) | 3277 | 3227 | 20 | 30 | 0 | 0 |

Release155218, debug155213 and download-build155216 succeeded. GitHub static checks5/5 succeeded. These jobs belong to workflow20f7ce36-11b5-4ce1-94e1-838aec4803b7. Single trigger comment5666059284 was retained without duplicates.

## Evidence Scope

- PR: https://github.com/CUBRID/cubrid/pull/7927
- Engine:512b361a7a34a4857cd8ad91c496c7e0e94c0769; current parent38093ea859a8a08e20405b72b0cb395205bedb2f.
- Public tests:6ab786aa9145489ce1e1336dd829779e9de8c58a; all10 failing case/answer files match downloaded sources byte-for-byte.
- Private tests:6ce89517e700f8f41e9fa451e3df24cf9e52d7a0; tools a1bec8762644f58dc48c99a8dfb227fa0bcc70ca. All50 shell checkout logs agree. Private directories were extracted from exact local Git objects because collector links did not carry immutable revisions.
- Collector0.1.0 (3e9502f72350), text/source mode, no wait: all three exit0. Shell165 text artifacts/181208528 bytes; no core downloads.
- Collection/replay date:2026-09-15 KST.

Durable collector root: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/512b361`. Separate read-only API evidence: sibling `512b361-api-20260914`, including complete50-node checkout observations and shell-observed-signatures.json. Normalized summaries, all failed-test messages/diffs, source indices, node XML and targeted feedback logs were inspected. Counts reconcile with all25 rows below.

## Failure Inventory

| Suite | Test | Observed signature | Category | Attribution |
|---|---|---|---|---|
| medium | `medium/_02_xtests/cases/to_char_order_by.sql` | Conversion SELECT without ORDER BY returns a different permutation | Ordering | Parent-reproduced |
| medium | `medium/_02_xtests/cases/to_number_order_by.sql` | Conversion SELECT without ORDER BY returns a different permutation | Ordering | Parent-reproduced |
| medium | `medium/_02_xtests/cases/to_timestamp_order_by.sql` | Conversion SELECT without ORDER BY returns a different permutation | Ordering | Parent-reproduced |
| sql | `sql/_13_issues/_14_1h/cases/bug_bts_10516.sql` | Wide LOB insert returns-1383; later operations see zero rows | OOS/bigone boundary | Parent-reproduced |
| sql | `sql/_15_fbo/_02_qa_test/cases/fbo_ddl02.sql` | Wide LOB insert returns-1383; later operations see zero rows | OOS/bigone boundary | Parent-reproduced |
| shell | `shell/_36_damson/cbrd_23608_tde/tbl_enc_08/cases/tbl_enc_08.sh` | TDE page/file/sort diagnostics differ from expected storage layout | Physical storage expectation | Parent-reproduced |
| shell | `shell/_36_damson/cbrd_23608_tde/log_enc_04/cases/log_enc_04.sh` | Expected RVHF_INSERT_NEWHOME log record is missing | Physical storage expectation | Parent-reproduced |
| shell | `shell/_36_damson/cbrd_23608_tde/tbl_enc_14/cases/tbl_enc_14.sh` | TDE page/file/sort diagnostics differ from expected storage layout | Physical storage expectation | Parent-reproduced |
| shell | `shell/_06_issues/_15_1h/bug_bts_15489/cases/bug_bts_15489.sh` | CI112pages; OptDebug parent104pages; both violate below100 | Index reclamation threshold | Parent-reproduced |
| shell | `shell/_39_fig_cake/cbrd_24044_enhance_optimizer/cbrd_25080/cases/cbrd_25080.sh` | Selectivity/cardinality diagnostic differences | Optimizer expectations | Parent-reproduced |
| shell | `shell/_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh` | Additional OOS errors-1382/-1384/-1385 | Default error list | Parent-reproduced |
| shell | `shell/_36_damson/cbrd_23608_tde/file_enc_03/cases/file_enc_03.sh` | TDE page/file/sort diagnostics differ from expected storage layout | Physical storage expectation | Parent-reproduced |
| shell | `shell/_36_damson/cbrd_23608_tde/file_enc_02/cases/file_enc_02.sh` | TDE page/file/sort diagnostics differ from expected storage layout | Physical storage expectation | Parent-reproduced |
| shell | `shell/_36_damson/cbrd_23608_tde/temp_enc_09/cases/temp_enc_09.sh` | TDE page/file/sort diagnostics differ from expected storage layout | Physical storage expectation | Parent-reproduced |
| shell | `shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh` | Invalid partition row rejected; expected answer accepts2 rows | Intended routing correction | Intended rejection; CI remains failed |
| shell | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | Extraction rc=-10, including zero/small targets in CI | CDC extraction | Parent-reproduced |
| shell | `shell/_06_issues/_26_1h/cbrd_26527/cases/cbrd_26527.sh` | Expected MULTIPAGE HFID cannot be extracted | Physical storage expectation | Parent-reproduced |
| shell | `shell/_36_damson/cbrd_23608_tde/file_enc_04/cases/file_enc_04.sh` | TDE page/file/sort diagnostics differ from expected storage layout | Physical storage expectation | Parent-reproduced |
| shell | `shell/_06_issues/_11_2h/bug_bts_5423/cases/bug_bts_5423.sh` | Additional index_build_buffer_size=2.0M | Parameter list | Parent-reproduced |
| shell | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | Extraction errors at4K/8K/16K despite2000 updates and zero corruption | CDC extraction | Parent-reproduced |
| shell | `shell/_36_damson/cbrd_23608_tde/file_enc_07/cases/file_enc_07.sh` | TDE page/file/sort diagnostics differ from expected storage layout | Physical storage expectation | Parent-reproduced |
| shell | `shell/_36_damson/cbrd_23608_tde/file_enc_05/cases/file_enc_05.sh` | TDE page/file/sort diagnostics differ from expected storage layout | Physical storage expectation | Parent-reproduced |
| shell | `shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh` | Additional OOS errors-1382/-1384/-1385 | Default error list | Parent-reproduced |
| shell | `shell/_35_cherry/issue_21654_server_side_loaddb/bigPageSize/cases/bigPageSize.sh` | Compared dumps contain different external LOB locators | LOB output identity | Parent-reproduced |
| shell | `shell/_36_damson/cbrd_23608_tde/file_enc_01/cases/file_enc_01.sh` | TDE page/file/sort diagnostics differ from expected storage layout | Physical storage expectation | Parent-reproduced |

## Root-Cause Analysis

**Ordering (3).** The failing conversion SELECTs lack ORDER BY. Exact case/answer bytes are unchanged from historical fixtures, but fresh38093ea/512b361 CTP replays were performed. All three fail with byte-identical local actual outputs. CI permutations need not match local permutations. Confidence is high for the expectation mismatch; adding an explicit ordering contract would falsify that explanation.

**OOS/bigone boundary (2).** Initial wide LOB insertion returns-1383, followed by zero-row cascades. Both cases fail identically on the fresh pair. This is preexisting OOS/ordinary-overflow compatibility behavior, not evidence that destination-owned preparation newly lost successful rows. Any boundary-policy repair is separate work; expected answers were not changed.

**Physical storage, diagnostic and optimizer expectations.** Parent replay reproduces OOS-versus-MULTIPAGE layout, encryption diagnostic, missing RVHF_INSERT_NEWHOME, default error-list, parameter-list, external LOB locator and optimizer selectivity/cardinality signatures. This establishes preexistence with high confidence, not a claim that every underlying expectation should be changed. TDE diagnostics do not by themselves prove encrypted-data leakage. Review the intended physical/diagnostic contract before changing tests. For LOB output, differing generated locators require a stable comparison of logical values and row identity.

**Index reclamation (1).** CI observes112 pages against0 < pages <100 after60 seconds. Debug parent/candidate pass at89/88. An unchanged testcase on fresh OptDebug parent fails at104. The recorded btree compiler command uses-O2 and-DCUBRID_OPTDEBUG with assertions enabled, matching CI's build mode rather than local-O0. Confidence is high that the threshold failure predates this branch; the precise vacuum/tree cause and exact page count remain unknown. Preserve the earlier passes and investigate convergence separately before tightening or relaxing the threshold.

**CDC extraction (2).** CDC27064 reproduces rc=-10 on the current parent; timing-dependent targets differ from CI. CDC27075 fails on both builds at every page size, with all2000 updates completed, zero corruption and nonzero extracted items. Parent error counts3/3/3; candidate4/4/2. Captured4K/8K driver logs show rc=-10. Remote feedback and final XML retain different2-versus4-error observations; neither is discarded. Preexistence is established, but exact internal causes and remote crash-stack equivalence are not. Inspect extraction return-path diagnostics before attributing either failure to a particular historical assertion.

**Partition routing (1).** Parent accepts the testcase's invalid row, while destination routing rejects it. A fresh merged-candidate probe verifies nonzero load status, zero surviving rows/live OOS records after failed batch, and successful subsequent valid insert. Retained empty OOS capacity is not a live-chain leak. This is intended rejection, not a baseline failure or an unavailable check; remote CI remains failed.

## Local Evidence

- `~/.cache/codex/pr7927-512b361-sql`: exact2SQL/3medium cases fail on both; all five actual-result hashes match in paired-output.json. Candidate engine hashes match published integration provenance despite its embedded pre-merge6acfbb8 version string. Source hashes were revalidated against512b361. Preserved installed JDBC jars differ and are explicitly recorded; do not claim identical complete installations. CTP source files match the pinned tools commit; eight installed CTP jars differ only in MANIFEST.MF, with unchanged class/resource contents, so whole-jar byte identity is not claimed.
- `~/.cache/codex/pr7927-512b361`: four-case pairs completed4executed/3failed/1passed each, no skips. Full feedback and selected CDC driver output retained. Fresh partition-probe.log and /tmp/oos-loader17-qoxhqtbs/partition-result.json establish rollback and next-write usability.
- `~/.cache/codex/pr7927-512b361-optdebug`: parent index replay1executed/1failed,104pages, with source/binary hashes, compiler command and complete CTP output.
- `~/.cache/codex/pr7927-512b361-remaining`: parent16executed/15failed/1passed, no skips; exact signatures in baseline-results.json. Candidate counterpart completed16executed/16failed/0skipped; the additional failure is intended partition rejection. Both result inventories are retained.

All CTP executions isolate processes, network, IPC, registries and databases from unrelated work. Testcase and answer files remain unchanged. Process exit0 is not mistaken for testcase success.

## Acceptance Decision

V21-CI and V21-ACCEPT are satisfied for tested engine512b361 within the accepted destination-owned deferred-write scope. This is evidence-backed replacement acceptance, not all-green CI or a claim that independent OOS defects are fixed.

All requested checks have terminal evidence;24 failures reproduce independently on38093ea and the remaining partition rejection is intended. The earlier introduced4KB bootstrap defect is repaired and its original testcase passes remotely. Paired counterpart runs finished and preserve every failed attempt and differing timing/count observation.

The fresh35/35 configured CTest and recorded real loader, HA, transaction/recovery, bootstrap and scoped lifetime tests cover the producer matrix in the linked integration report. The24-sample memory comparison against38093ea measures loader server-growth increases of7084/7596KiB. This measured cost is accepted for retaining canonical payloads until destination selection: direct accounting records50392B for a50KB owner and3225600B for64 queued rows. RSS includes staging/allocators and is not an exact live-owner count. No full-inline temporary row or finalization-only payload duplicate is introduced; no numerical threshold or whole-process8MiB cap is invented.

The source guide, ticket22 and parent/map record this decision. The detailed producer/resource evidence remains at [integration verification](CBRD-27089-deferred-write_be7c01a_codex.md). Curated current CI/paired evidence is indexed by [manifest](deferred-write-512b361-acceptance/manifest.json), with [classification](deferred-write-512b361-acceptance/classification.json), [parent cases](deferred-write-512b361-acceptance/parent-shell-results.json), [candidate cases](deferred-write-512b361-acceptance/candidate-shell-results.json), [SQL/medium hashes](deferred-write-512b361-acceptance/sql-medium-paired-output.json), [OptDebug result](deferred-write-512b361-acceptance/optdebug-index-result.json), and [partition rollback](deferred-write-512b361-acceptance/partition-result.json).

## Limitations

Historical878f18b results are retained separately and were not substituted for this revision. Baseline failures remain failed CI results. Specific local tests do not certify vacuum convergence, no-logging crash durability, multi-node heartbeat failover or undefined-value cleanliness. Final Standards and Spec reviews report zero blockers. The14-file curated manifest hashes and relative links validate. Publication receipts are recorded in the local ticket. No new test threshold or expected answer has been silently adopted.
