# CI Failure Analysis: PR #7695 at `a37b5b1`

## Executive Summary

**CI remains failed: 2 SQL failures and 20 shell failures.** Medium passed all 975 cases. All suites have zero error and unknown-result records; shell also has 30 skipped cases, which are not passes. No requested suite is unavailable.

The highest-priority unresolved failures are **CDC extraction in `cbrd_27064` and `cbrd_27075`**. Complete JUnit artifacts expose their symptoms, which the CircleCI tests API reduced to generic failure messages. An OOS historical-value lifetime problem is plausible, but this exact run does not include a usable server stack proving that cause. The remaining 20 cases have identifiable size-limit, physical-layout, trace, statistics, or comparison discrepancies; this does **not** establish that all are harmless or pre-existing.

One concrete testcase defect is established: `cbrd_26123` searches whole output rows with the regular expression `0.00`, which matches `0200` in its CI hostname. This inflates its zero-time counts. Long-statement truncation is also observed and needs separate assessment.

No CUBRID/testcase source was changed, CI was not triggered, and this report is uncommitted. The earlier local 35-test pass is not a substitute for these remote suites.

## CI Snapshot

| Suite | State | CircleCI job | Tests | Success | Failures | Errors | Unknown | Skipped |
|---|---|---|---:|---:|---:|---:|---:|---:|
| test_medium | success | [154628](https://circleci.com/gh/CUBRID/cubrid/154628) | 975 | 975 | 0 | 0 | 0 | 0 |
| test_sql | failed | [154630](https://circleci.com/gh/CUBRID/cubrid/154630) | 17459 | 17457 | 2 | 0 | 0 | 0 |
| test_shell | failed | [154632](https://circleci.com/gh/CUBRID/cubrid/154632) | 3275 | 3225 | 20 | 0 | 0 | 30 |

All three build prerequisites in the manifest succeeded: release [154629](https://circleci.com/gh/CUBRID/cubrid/154629), debug [154627](https://circleci.com/gh/CUBRID/cubrid/154627), and download-build [154631](https://circleci.com/gh/CUBRID/cubrid/154631). Suite execution occurred September 11 UTC (shell completed September 12 KST); this is a September 14 collection, not a new test run.

## Evidence Scope

- PR: [CUBRID/cubrid#7695](https://github.com/CUBRID/cubrid/pull/7695), “Verify OOS chain identity before vacuum delete”.
- Exact engine: `a37b5b1a54589007caf0ea1c0adf627e5bef366b`; local HEAD matches. Merge base parent used for source comparison: `9c768e4777006f13910c41813495fd35e9f58dec` (`feat/oos`). No new baseline execution was performed.
- Collector: `cubrid-ci 0.1.0 (3e9502f72350, release)`, text artifacts and testcase-source enrichment, no waiting for CI. Manifest collected at `2026-09-14T13:41:38.167736982Z`.
- Validated collector bundle: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1`. SQL downloaded 64 text artifacts (65,871,256 bytes); shell downloaded 208 (187,778,797 bytes). No core/binary artifact mode was used.
- Additional read-only evidence: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1-api-20260914`. This separate supplement contains checkout logs, extracted full JUnit failure text, source snapshots, source hashes, per-case provenance, and the normalized analysis inventory. It does not modify the collector schema.
- Both SQL cases and their answers are from `CUBRID/cubrid-testcases@b10727db4b9fd1b52aed49330634a3395d532048`, established individually by collector source records and matched byte-for-byte to exact local Git objects.
- All 20 failing shell cases are from `CUBRID/cubrid-testcases-private-ex@80c58d4afdbf820ff3bfdb4ec571a28a93198515`, branch `develop`. Every failing node's checkout log proves this SHA; generic API cases map to nodes 29, 34 and 41 through JUnit names and runner output. `shell-case-provenance.json` records the mapping. The collector had no shell source links; exact Git-object snapshots were added separately.
- `CUBRID_TESTCASES_DIR` and `CUBRID_TESTCASES_PRIVATE_EX_DIR` were unset. Repositories were located under `/home/vimkim/gh/tc/`. The shell checkout used for object access is `cubrid-testcases-private-ex-cbrd-26659`, whose HEAD is `c4fe45173ddbfccc6dc59212670ec91e94b8f6f1`; its clean checkout was not treated as CI source. Explicit Git objects at the proven CI revision supplied the files. SQL objects came from `cubrid-testcases`; working-tree bytes were not used as evidence.
- Supplemental SQL/medium checkout-log retrieval was incomplete after an HTTP 404, so this report does not infer a shared revision for all passing cases. Medium testcase revision remains unverified. This does not invalidate its engine/job identity or reported result counts.

## Failure Inventory

Each failed testcase appears exactly once. Confidence distinguishes observed symptoms from unproven causal attribution. “PR relation” concerns the identity-stamp changes relative to the merge parent; OOS feature relationships are stated separately.

| Suite | Test | Result | Observed signature | Category | PR relation | Confidence | Evidence |
|---|---|---|---|---|---|---|---|
| test_sql | `sql/_13_issues/_14_1h/cases/bug_bts_10516.sql` | failure | INSERT returns -1383; later operations see zero rows | A | unlikely introduced; OOS-related | high signature / medium attribution | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_sql/failures/sql_13_issues_14_1h_cases_bug_bts_10516_sql-6910fb5224/message.txt) |
| test_sql | `sql/_15_fbo/_02_qa_test/cases/fbo_ddl02.sql` | failure | INSERT returns -1383; later operations see zero rows | A | unlikely introduced; OOS-related | high signature / medium attribution | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_sql/failures/sql_15_fbo_02_qa_test_cases_fbo_ddl02_sql-81a733f244/message.txt) |
| test_shell | `shell/_06_issues/_26_1h/cbrd_26527/cases/cbrd_26527.sh` | failure | Cannot extract MULTIPAGE HFID; first three DROP checks pass | B | unlikely introduced; OOS-related | high | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_shell/failures/shell_06_issues_26_1h_cbrd_26527_cases_cbrd_26527_sh-8c825fdc35/message.txt) |
| test_shell | `shell/_36_damson/cbrd_23608_tde/tbl_enc_08/cases/tbl_enc_08.sh` | failure | OOS file/class description replaces MULTIPAGE overflow; AES remains present | B | unlikely introduced; OOS-related | high | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_shell/failures/shell_36_damson_cbrd_23608_tde_tbl_enc_08_cases_tbl_enc_08_sh-a96cea1219/message.txt) |
| test_shell | `shell/_29_features_920/issue_11161_volume/cases/issue_11161_volume.sh` | failure | SYSTEM page count 33 vs 34; total 214 vs 215 | F | unknown | high signature / low cause | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_shell/failures/shell_29_features_920_issue_11161_volume_cases_issue_11161_volume_sh-9c8f3369d4/message.txt) |
| test_shell | `shell/_06_issues/_17_1h/cbrd_20145_1/cases/cbrd_20145_1.sh` | failure | Page locks 27 actual vs 25 expected | G | unknown | high signature / low cause | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_shell/failures/shell_06_issues_17_1h_cbrd_20145_1_cases_cbrd_20145_1_sh-0d0ff4c7de/message.txt) |
| test_shell | `shell/_36_damson/cbrd_23608_tde/file_enc_05/cases/file_enc_05.sh` | failure | Extra deallocation and NONE trace entries | C | plausible OOS layout interaction; introduction unknown | high signature / medium cause | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_shell/failures/shell_36_damson_cbrd_23608_tde_file_enc_05_cases_file_enc_05_sh-bc7c25c903/message.txt) |
| test_shell | `shell/_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh` | failure | Actual default stack list adds -1382,-1384,-1385 | E | unlikely introduced; OOS-related | high | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_shell/failures/shell_06_issues_12_2h_bug_bts_9836_cases_bug_bts_9836_sh-74957cfea4/message.txt) |
| test_shell | `shell/_36_damson/cbrd_23608_tde/tbl_enc_14/cases/tbl_enc_14.sh` | failure | OOS file/class description replaces MULTIPAGE overflow; AES remains present | B | unlikely introduced; OOS-related | high | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_shell/failures/shell_36_damson_cbrd_23608_tde_tbl_enc_14_cases_tbl_enc_14_sh-afd5d2d444/message.txt) |
| test_shell | `shell/_06_issues/_25_2h/cbrd_26123/cases/cbrd_26123.sh` | failure | 10 assertions fail; hostname matches 0.00 regex; long SQL also truncated | J | unlikely identity-stamp change | high for regex defect | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_shell/failures/shell_06_issues_25_2h_cbrd_26123_cases_cbrd_26123_sh-56c402ee07/message.txt) |
| test_shell | `shell/_36_damson/cbrd_23608_tde/log_enc_04/cases/log_enc_04.sh` | failure | Expected RVHF_INSERT_NEWHOME encrypted-log entry absent | D | unlikely introduced; OOS-related | high signature / medium cause | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_shell/failures/shell_36_damson_cbrd_23608_tde_log_enc_04_cases_log_enc_04_sh-3ddc50c80f/message.txt) |
| test_shell | `shell/_06_issues/_11_1h/bug_bts_5048/cases/bug_bts_5048.sh` | failure | Statistics/cardinality 0/0 vs expected 1/6 after DELETE | H | unlikely identity-stamp change | high signature / medium attribution | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_shell/failures/shell_06_issues_11_1h_bug_bts_5048_cases_bug_bts_5048_sh-42a95b5427/message.txt) |
| test_shell | `shell/_36_damson/cbrd_23608_tde/file_enc_03/cases/file_enc_03.sh` | failure | Extra AES and deallocation trace entries | C | plausible OOS layout interaction; introduction unknown | high signature / medium cause | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_shell/failures/shell_36_damson_cbrd_23608_tde_file_enc_03_cases_file_enc_03_sh-f49a799f7e/message.txt) |
| test_shell | `shell/_35_cherry/issue_21654_server_side_loaddb/bigPageSize/cases/bigPageSize.sh` | failure | Only CLOB/BLOB physical locator paths differ between databases | K | plausible LOB-copy interaction; introduction unknown | high signature / medium cause | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1-api-20260914/node-29-failure.txt) |
| test_shell | `shell/_36_damson/cbrd_23608_tde/file_enc_01/cases/file_enc_01.sh` | failure | Actual filtered trace empty: grep requires exactly 9 pages | C | plausible OOS layout interaction; introduction unknown | high signature / medium cause | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_shell/failures/shell_36_damson_cbrd_23608_tde_file_enc_01_cases_file_enc_01_sh-3fd2e80979/message.txt) |
| test_shell | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | failure | CDC extract errors 2/3/5 at 4/8/16K; configs OK 0/3 | L | plausible OOS-history lifetime interaction | high symptom / medium hypothesis | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1-api-20260914/node-34-failure.txt) |
| test_shell | `shell/_36_damson/cbrd_23608_tde/file_enc_07/cases/file_enc_07.sh` | failure | Two fewer AES trace entries; recovery check passes | C | plausible OOS layout interaction; introduction unknown | high signature / medium cause | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_shell/failures/shell_36_damson_cbrd_23608_tde_file_enc_07_cases_file_enc_07_sh-63ce2de252/message.txt) |
| test_shell | `shell/_39_fig_cake/cbrd_24044_enhance_optimizer/cbrd_25080/cases/cbrd_25080.sh` | failure | Selectivity and cardinality digits differ in three normalized plans | I | unlikely identity-stamp change | high signature / medium attribution | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_shell/failures/shell_39_fig_cake_cbrd_24044_enhance_optimizer_cbrd_25080_cases_cbrd_25080_sh-b5da6c59bb/message.txt) |
| test_shell | `shell/_36_damson/cbrd_23608_tde/file_enc_04/cases/file_enc_04.sh` | failure | AES/NONE application trace entries differ | C | plausible OOS layout interaction; introduction unknown | high signature / medium cause | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_shell/failures/shell_36_damson_cbrd_23608_tde_file_enc_04_cases_file_enc_04_sh-7f9f14b589/message.txt) |
| test_shell | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | failure | CDC -10; DELETE 8/700, UPDATE 0/2400; INSERT passes | L | plausible OOS-history lifetime interaction | high symptom / medium hypothesis | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1-api-20260914/node-41-failure.txt) |
| test_shell | `shell/_36_damson/cbrd_23608_tde/file_enc_02/cases/file_enc_02.sh` | failure | One extra allocation/AES pair in actual trace | C | plausible OOS layout interaction; introduction unknown | high signature / medium cause | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_shell/failures/shell_36_damson_cbrd_23608_tde_file_enc_02_cases_file_enc_02_sh-3efacd3b08/message.txt) |
| test_shell | `shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh` | failure | Actual default stack list adds -1382,-1384,-1385 | E | unlikely introduced; OOS-related | high | [log](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26950/a37b5b1/test_shell/failures/shell_06_issues_14_2h_bug_bts_14120_cases_bug_bts_14120_sh-2917c23aa5/message.txt) |

## Root-Cause Analysis

### A — OOS plus oversized-record rejection (2 SQL cases)

**Observed:** Both sources create `allcolumn_t4` with 1,000 BLOB/CLOB columns. INSERT expects success but gets `Error:-1383`; subsequent copies, count, update and delete consequently see zero rows. Node 2 and node 4 `basic` server error logs report **26,036 bytes versus a 16,236-byte maximum**, at `heap_file.c:13354`. The error is `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`, not the newly added eager-cleanup diagnostic (-1386).

**Cause:** `heap_attrinfo_transform_to_disk_internal` rejects a record still too large after OOS demotion before writing its OOS values. The accepted OOS specification forbids coexistence with `REC_BIGONE`. The PR expands each OOS stub from 16 to 24 bytes, changing physical sizing; the rejection rule itself exists in the merge parent. Earlier local reports describe the same many-LOB cases rejecting on an older base; that is supporting context, not a fresh exact-base comparison.

**Next/falsifier:** Replay both exact testcase/answer pairs on parent `9c768e477` and this head with the same configuration. Parent success would falsify “unlikely introduced”. Review OOS-compatible testcase intent and preserve rejection/state assertions; do not blindly replace expected success or renumber answers.

### B — Tests require legacy overflow-file representation (3 shell cases)

**Observed:** `tbl_enc_08` and `tbl_enc_14` see `OUT_OF_LINE_OVERFLOW` and an OOS owner description where answers require `MULTIPAGE_OBJECT_HEAP`/`Overflow for HFID`. AES is still reported. `cbrd_26527` passes its before-DROP presence, no-unknown-class, and after-DROP absence checks, then cannot extract a MULTIPAGE HFID.

**Inferred:** The tests assume the pre-OOS representation. Exact sources create large variable/now-variable CHAR or VARCHAR values and grep for a physical overflow type. The identity-stamp PR does not introduce OOS file selection. These failures do not prove failed encryption or failed DROP reclamation.

**Next/falsifier:** Review representation-aware assertions against the intended storage policy while retaining AES and reclaim checks. An OOS page lacking encryption, or retained pages after DROP, would invalidate a pure expectation explanation. Compare the exact parent if introduction matters.

### C — Physical-page-dependent TDE trace expectations (6 shell cases)

**Observed:** `file_enc_01/02/03/04/05/07` fail exact debug-log comparisons. `file_enc_01` filters for an exact **9-page** `file_apply_tde_algorithm` event and gets an empty result. `02` has an extra allocation/AES pair; `03` extra AES/deallocation; `04` differing AES/NONE applications; `05` extra deallocation/NONE; `07` two fewer AES entries, while its preceding recovery-log check passes.

**Inferred:** These are allocation/layout-sensitive traces. Several exact tests explicitly use 4K pages with 2,000-byte CHAR values to obtain one row per heap page; OOS changes that premise. `file_enc_03` uses 20,000-byte VARCHAR. Identity stamps also increase stub/chunk sizes, so the exact effect of this PR on counts remains plausible. No identical-parent comparison or page-by-page encryption audit was done.

**Next/falsifier:** Run the six cases on identical parent/head builds and map each differing log event to its file/page. Validate encryption and decryption across allocation/recovery, then adjust only unsupported fixed-count assumptions. Unencrypted OOS pages or failed recovery/value checks would be engine defects, not answer drift.

### D — Missing heap-relocation recovery index (1 shell case)

**Observed:** `log_enc_04` successfully performs its DML, finds several encrypted recovery indexes, then fails because `RVHF_INSERT_NEWHOME` has count zero. The script intends a 10,000-byte VARCHAR update to force heap relocation; it stops at the first missing index, so later expected-index coverage is not established. Its internal-error check reports zero.

**Inferred:** OOS demotion can prevent the heap relocation this workload expects. This is not proof of missing required encryption logging for operations that actually occurred.

**Next/falsifier:** Confirm the physical record transition and encrypted OOS log entries on parent/head. If the heap really relocates but its required encrypted record is missing, investigate engine logging. Otherwise use a workload that deliberately exercises the required relocation and separate OOS logging coverage.

### E — Default diagnostic error-list expectations (2 shell cases)

**Observed:** `bug_bts_9836` and `bug_bts_14120` have additional actual entries `-1382,-1384,-1385`. The exact source's `call_stack_dump_error_codes` in `system_parameter.c:5861` contains `ER_HEAP_OOS_BAD_INLINE_HEADER`, `ER_HEAP_OOS_CORRUPTED_RECORD`, and `ER_HEAP_OOS_INVALID_ARGUMENT`; the exact header assigns those numbers. The new -1386 cleanup notification is not in this list.

**Inferred:** The develop answers omit OOS diagnostic defaults. This is directly explained by existing OOS configuration, rather than evidence of a runtime cleanup failure.

**Next/falsifier:** Compare complete lists symbolically against the intended defaults and update compatible testcase expectations through review. Any extra non-OOS mismatch or unintended default requires separate diagnosis.

### F — System-space accounting expectation (1 shell case)

**Observed:** `issue_11161_volume` passes checks 1–3, then observes SYSTEM page count 33 instead of 34 and aggregate 214 instead of 215 in checks 4–5. Its source creates volumes, tables/indexes and scans catalog rows before checking `spacedb` output.

**Unknown:** The exact missing/differently-accounted system page is not established; a one-page difference alone does not prove harmless drift or an OOS regression.

**Next/falsifier:** Compare file-level `spacedb`/`diagdb` inventory at the same checkpoints on parent/head. A candidate-only accounting inconsistency, rather than a valid allocation difference, would establish a regression.

### G — Page-lock statistics expectation (1 shell case)

**Observed:** `cbrd_20145_1` expects 25 page locks and gets 27; other displayed lock counters match. The source runs small create/insert/update/delete/select statements and compares a fixed debug statistics answer.

**Unknown:** The two additional acquisitions have not been assigned to a call path. This snapshot does not establish an incorrect lock or a deadlock.

**Next/falsifier:** Trace page-lock acquisitions for its exact `test2.sql` on parent/head and compare which pages/operations account for the difference. A candidate-only unnecessary/conflicting lock would change attribution; do not merely change 25 to 27.

### H — Post-delete statistics/cardinality expectations (1 shell case)

**Observed:** `bug_bts_5048` inserts/commits, deletes/rolls back, deletes again, updates statistics and inspects stats/plans. Actual parsed values are `result1=0`, `result2=0`; the test requires 1 and 6. Inputs are small strings, with no evident OOS-sized payload.

**Inferred:** Statistics/visibility or expectation semantics are more likely than identity-stamp handling, but intended post-delete statistics semantics were not independently adjudicated.

**Next/falsifier:** Run the exact two statement sequences on parent/head and inspect visibility plus statistics before changing assertions. Candidate-only statistics differences would falsify the “unlikely identity-stamp” assessment.

### I — Optimizer trace expectations (1 shell case)

**Observed:** `cbrd_25080` passes two node-cardinality count checks, then three normalized plan comparisons differ in selectivity/cardinality digit patterns. The numeric masking preserves digit count, so differing estimates survive normalization. The identity-stamp delta relative to `9c768e477` does not edit optimizer source.

**Inferred:** Optimizer/testcase-baseline differences are more likely than this PR's storage identity logic. Indirect storage-statistics effects are not excluded.

**Next/falsifier:** Compare unmasked selectivity/cardinality and plans with the identical base and testcase data. Candidate-only estimates under equal statistics would require investigating a storage-to-statistics effect. Do not assume a plan difference is harmless or optimal.

### J — Transaction-list parsing and formatting (1 shell case)

**Observed:** `cbrd_26123` has ten NOK subchecks. Its `grep -o "0.00"` scans all columns. The actual hostname `ccita-1b520200-2752-5e3c-85e6-1da03fc96f38-kvjmji` contains `0200`, which matches that regex. An idle one-transaction check counts 2 instead of 1; two transactions count 4 instead of 2. Long SQL is also truncated in one output (`create table long_table_name_fo`), while another output contains the full statement. Cleanup additionally invokes `timeout 5s wait PID`, whose separate shell says the PID is not its child; that cleanup issue is not claimed to cause the earlier assertions.

**Cause/inference:** Whole-row regex counting is a proven testcase defect. This explains the inflated counts; it does not by itself resolve the long-SQL display expectation or every NOK.

**Next/falsifier:** Parse the named Query time/Tran time fields and compare literal numeric values; test with the observed hostname. Then assess full/truncated SQL expectations independently and use a same-shell process wait in cleanup. Continued failures with correct field parsing would require further utility/timing diagnosis.

### K — Physical LOB locators compared across unload/load (1 shell case)

**Observed:** Full node-29 JUnit text shows only two changed fields: `cl` and `bl`. Both have equal `file:<size>` prefixes but different `ces_*` paths and object suffixes. The source selects raw CLOB/BLOB locators from original and loaded databases, then compares whole formatted outputs. `loaddb -C` succeeds; its expected load-log comparison is not reported failed.

**Inferred:** Physical locator identity is being compared across separate databases. Equal sizes and other fields do not prove equal LOB content. Changed locator creation/copy behavior could interact with OOS, so introduction is unknown.

**Next/falsifier:** Compare `clob_to_char`/`blob_to_bit` values or content digests and sizes, and verify the intended locator-preservation contract. Any payload difference turns this into a data-correctness failure; do not mask the paths before checking content.

### L — CDC extraction failure, OOS-history hypothesis (2 shell cases)

**Observed:** Full node-41 JUnit text restores `cbrd_27064`'s missing API diagnostics: INSERT passes; DELETE returns `EXTRACT_ERROR: rc=-10` after 8/700 target records; UPDATE returns -10 at 0/2400. The extractor exits 1, not timeout exit 124. The script's corruption-text counter is zero. In node 34, `cbrd_27075` reaches final sequence 2,000 and finds LSAs successfully at every page size, but extraction errors are 2, 3 and 5 at 4K, 8K and 16K; `CONFIGS_OK=0`, reported corruption count zero. Its summary does not provide individual error codes.

`src/api/cubrid_log.h:55` defines **-10 as `CUBRID_LOG_FAILED_CONNECT`**. `cubrid_log.c:1189` and following checks return it for request/receive failures or malformed replies. This does not, by itself, prove a server crash, page corruption, or an identity mismatch. Zero grep-based corruption counts are not proof of healthy extraction.

**Plausible mechanism:** `cdc_make_dml_loginfo` in `log_manager.c:13142` reads historical undo/redo records through `heap_attrinfo_read_dbvalues`; the OOS path resolves their inline references against storage. Reclaimed/reused historical OOS chains therefore remain relevant. The accepted [durable supplemental-image ADR](/home/vimkim/gh/cubrid-oos-context/docs/adr/0004-durable-oos-supplemental-images.md) exists precisely to decouple CDC history from OOS lifetime. This PR changes stub layout and identity validation, making interaction plausible, but the exact failing call/stack is absent from the present artifacts. Older reports describe related CDC failures; they are supporting history, not proof of this run's cause.

**Next/falsifier:** Prioritize focused parent/head runs of these exact CDC cases, preserving per-process server errors and extractor trace before testcase cleanup. Locate which -10 path occurs and whether server-side OOS resolution failed; repeat with a controlled vacuum condition if the evidence points there. A transport-only failure without OOS access, or successful history reads followed by unrelated disconnects, would falsify the lifetime hypothesis. Keep value completeness/corruption checks, and do not replace these failures with successful expectations.

## Recommended Actions

1. Diagnose both CDC cases with retained server/client traces and an identical-base comparison. They report incomplete extraction and remain the principal unresolved runtime risk.
2. Repair the proven `cbrd_26123` whole-row regex defect in the testcase project; separately decide SQL-display and process-cleanup expectations.
3. Check LOB payload equality in `bigPageSize` before deciding whether locator differences are acceptable.
4. Review OOS-compatible size, layout, diagnostic-default and TDE assertions while preserving encryption, reclamation, and state checks. Resolve page accounting, page locks and optimizer/statistics deltas through targeted base comparisons before editing answers.

## Evidence and Limitations

All suite manifests/summaries, complete failed-test inventories, per-failure metadata/messages/diffs, log/source/artifact indexes, selected runner logs and full JUnit payloads were inspected. The shell API omits long failure text for three cases; supplemental extraction from already downloaded JUnit artifacts fills that gap. A zero-byte extracted diff is never treated as a passing comparison. Raw suite result counts reconcile with the summaries; no error/unknown-result records require a separate inventory.

Supporting local context consulted: the exact-head OOS design report `CBRD-26950-oos-identity-stamp-page-lsa_eaf1165_claude.md`, the older `cbrd-27089/ci_analysis_report_be7c01a_codex.md`, `cbrd-26357/ci_analysis_report_f4299ac_codex.md`, the local diagnostic-default issue draft, and the accepted OOS specification/CDC ADR. Older reports are not substituted for current evidence, and their baseline results were not independently recollected here.

This is an evidence-based snapshot, not a repair or a claim that all failures predate the PR. No new reproduction, benchmark, core analysis, encryption audit, or base/head test pair was executed. Underlying causes remain unknown where explicitly labeled. The 30 skipped shell tests and unverified passing-test revisions limit coverage. The collector initially hit an unauthenticated GitHub rate limit; using the existing GitHub CLI credential completed collection without exposing the credential.
