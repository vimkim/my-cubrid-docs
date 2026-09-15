# CI Failure Analysis: PR #7927 at `878f18b`

## Executive Summary

The latest available completed snapshot has **25 failed testcases: 3 medium, 2 SQL, and 20 shell**, with zero error or unknown records. All requested suites are available. Thirty shell tests are skipped. Release/debug builds and the five GitHub checks pass, but runtime acceptance remains unresolved.

Subsequent exact-revision local replays identify **one introduced catalog-bootstrap regression**, now repaired locally: a fresh 4KB database unexpectedly allocates an authorization OOS file before the system-class OID cache exists. **Twenty-three failures reproduce on upstream parent `9c768e4`**; this includes the CDC extraction failure, whose remote run contains an OOS before-image server assertion. The remaining partition-loader failure reflects correct rejection of deliberately invalid input; a focused probe verifies batch rollback and subsequent usability. Baseline failures remain failed CI results, and the local repair still needs its own exact-revision remote verification.

## CI Snapshot

| Suite | State | CircleCI job | Tests | Passed | Failures | Errors | Unknown | Skipped |
|---|---|---|---:|---:|---:|---:|---:|---:|
| test_medium | failed, completed | [154806](https://circleci.com/gh/CUBRID/cubrid/154806) | 975 | 972 | 3 | 0 | 0 | 0 |
| test_sql | failed, completed | [154803](https://circleci.com/gh/CUBRID/cubrid/154803) | 17459 | 17457 | 2 | 0 | 0 | 0 |
| test_shell | failed, completed | [154805](https://circleci.com/gh/CUBRID/cubrid/154805) | 3275 | 3225 | 20 | 0 | 0 | 30 |

Runs completed on September 12, 2026 UTC. [Release build 154801](https://circleci.com/gh/CUBRID/cubrid/154801), [debug build 154802](https://circleci.com/gh/CUBRID/cubrid/154802), and download-build 154804 succeeded. GitHub reports all five checks successful in [workflow 34594310697](https://github.com/CUBRID/cubrid/actions/runs/34594310697). No missing-suite warning applies.

## Evidence Scope

- PR: [#7927, CBRD-27089](https://github.com/CUBRID/cubrid/pull/7927), `feat/oos-deferred-write` → `feat/oos`, OPEN.
- Exact analyzed commit: `878f18b364784c2dc4b4af6a100eaf9e326bf6d7`. Final read-only PR refresh still reports this head.
- Collector: `cubrid-ci 0.1.0 (3e9502f72350, release)`. Manifest collection timestamp: `2026-09-14T13:41:04.545467642Z`; supplemental analysis and PR refresh followed that collection.
- Medium anchor resolved the SHA; SQL and shell collection used that full SHA sequentially, with text artifacts and test sources, without waiting for new CI.
- SQL/medium source links individually pin `CUBRID/cubrid-testcases` revision `b10727db4b9fd1b52aed49330634a3395d532048`. All ten downloaded case/answer files match that revision's git objects and recorded SHA-256 hashes. Local public checkout HEAD differs, so current working-tree files were not substituted.
- All 50 shell-node checkout logs identify private testcase revision `80c58d4afdbf820ff3bfdb4ec571a28a93198515` on develop and testtools revision `a1bec8762644f58dc48c99a8dfb227fa0bcc70ca`. The collector found no shell source links; all 20 exact scripts were exported separately from the pinned git object. Nineteen match the current clean local checkout; one differs, so pinned exports govern this analysis.
- Remote analysis remains pinned to `878f18b364784c2dc4b4af6a100eaf9e326bf6d7`. The separately authorized ticket22 implementation subsequently replayed exact detached builds of that commit and its upstream parent `9c768e4777006f13910c41813495fd35e9f58dec`. The current repair is recorded separately as that head plus a hashed patch; remote results do not validate the repair. Both paired builds use debug_gcc, pinned CCI/JDBC, and the proven testcase/testtools revisions. The local evidence section below supersedes the initial read-only report's unresolved attribution.

Collector evidence: [/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/manifest.json). Supplemental read-only API, checkout, pinned-source, and XML evidence: [/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b-api-20260914](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b-api-20260914). The initial anonymous GitHub rate-limit failure was resolved by authenticated read-only collection. No credentials appear in this report.

## Failure Inventory

Each testcase appears once. PR relation refers to the deferred-write change, not merely membership in the broader OOS feature. Confidence distinguishes observed signatures from causal hypotheses where needed. Each testcase link opens its exact normalized evidence; XML supplements the two generic records.

| Suite | Test | Result | Observed signature | Category | PR relation | Confidence |
|---|---|---|---|---|---|---|
| test_medium | [medium/_02_xtests/cases/to_char_order_by.sql](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_medium/failures/medium_02_xtests_cases_to_char_order_by_sql-81a7176eb9/message.txt) | failure | Same values, different row order | A | unlikely | high |
| test_medium | [medium/_02_xtests/cases/to_number_order_by.sql](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_medium/failures/medium_02_xtests_cases_to_number_order_by_sql-2914e2cc1a/message.txt) | failure | Same values, different row order | A | unlikely | high |
| test_medium | [medium/_02_xtests/cases/to_timestamp_order_by.sql](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_medium/failures/medium_02_xtests_cases_to_timestamp_order_by_sql-f88d9035bb/message.txt) | failure | Same values, different row order | A | unlikely | high |
| test_sql | [sql/_13_issues/_14_1h/cases/bug_bts_10516.sql](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_sql/failures/sql_13_issues_14_1h_cases_bug_bts_10516_sql-6910fb5224/message.txt) | failure | Expected INSERT success; actual error -1383 | B | unlikely | medium |
| test_sql | [sql/_15_fbo/_02_qa_test/cases/fbo_ddl02.sql](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_sql/failures/sql_15_fbo_02_qa_test_cases_fbo_ddl02_sql-81a733f244/message.txt) | failure | Expected INSERT success; actual error -1383 | B | unlikely | medium |
| test_shell | [shell/_06_issues/_11_1h/bug_bts_5048/cases/bug_bts_5048.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_06_issues_11_1h_bug_bts_5048_cases_bug_bts_5048_sh-42a95b5427/message.txt) | failure | Committed statistics expected 1 and 6; actual 0 and 0 | J | unlikely | high |
| test_shell | [shell/_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_06_issues_12_2h_bug_bts_9836_cases_bug_bts_9836_sh-74957cfea4/message.txt) | failure | call_stack_dump_activation_list contains OOS errors | F | unlikely | high |
| test_shell | [shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_06_issues_14_2h_bug_bts_14120_cases_bug_bts_14120_sh-2917c23aa5/message.txt) | failure | call_stack_dump_activation_list contains OOS errors | F | unlikely | high |
| test_shell | [shell/_06_issues/_16_2h/cbrd_20683/cases/cbrd_20683.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_06_issues_16_2h_cbrd_20683_cases_cbrd_20683_sh-19eef560aa/message.txt) | failure | Extra authorization OOS file during fresh 4KB catalog bootstrap | N | direct | high |
| test_shell | [shell/_06_issues/_17_1h/cbrd_20145_1/cases/cbrd_20145_1.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_06_issues_17_1h_cbrd_20145_1_cases_cbrd_20145_1_sh-0d0ff4c7de/message.txt) | failure | Expected 25 page locks, actual 27 | M | unknown | high signature; low cause |
| test_shell | [shell/_06_issues/_26_1h/cbrd_26527/cases/cbrd_26527.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_06_issues_26_1h_cbrd_26527_cases_cbrd_26527_sh-8c825fdc35/message.txt) | failure | OOS diagnostic file type replaces ordinary overflow | H | unlikely | high |
| test_shell | [shell/_29_features_920/issue_11161_volume/cases/issue_11161_volume.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_29_features_920_issue_11161_volume_cases_issue_11161_volume_sh-9c8f3369d4/message.txt) | failure | SYSTEM pages33 versus34 expected; reproduced on parent | L | unlikely | high signature; allocation cause unresolved |
| test_shell | [shell/_35_cherry/issue_21654_server_side_loaddb/bigPageSize/cases/bigPageSize.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_35_cherry_issue_21654_server_side_loaddb_bigPageSize_cases_bigPageSize_sh-79322aefcb/message.txt) | failure | Reload passes; selected CLOB/BLOB locator strings differ | D | plausible | medium |
| test_shell | [shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_35_cherry_issue_21654_server_side_loaddb_partition_tbls_cases_partition_tb-9e01a2a475/message.txt) | failure | Out-of-range row rejected; 0 inserted, 1 failed | C | direct | high |
| test_shell | [shell/_36_damson/cbrd_23608_tde/file_enc_01/cases/file_enc_01.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_36_damson_cbrd_23608_tde_file_enc_01_cases_file_enc_01_sh-3fd2e80979/message.txt) | failure | TDE page-event counts or ordering differ | G | plausible | medium |
| test_shell | [shell/_36_damson/cbrd_23608_tde/file_enc_02/cases/file_enc_02.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_36_damson_cbrd_23608_tde_file_enc_02_cases_file_enc_02_sh-3efacd3b08/message.txt) | failure | TDE page-event counts or ordering differ | G | plausible | medium |
| test_shell | [shell/_36_damson/cbrd_23608_tde/file_enc_03/cases/file_enc_03.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_36_damson_cbrd_23608_tde_file_enc_03_cases_file_enc_03_sh-f49a799f7e/message.txt) | failure | TDE page-event counts or ordering differ | G | plausible | medium |
| test_shell | [shell/_36_damson/cbrd_23608_tde/file_enc_04/cases/file_enc_04.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_36_damson_cbrd_23608_tde_file_enc_04_cases_file_enc_04_sh-7f9f14b589/message.txt) | failure | TDE page-event counts or ordering differ | G | plausible | medium |
| test_shell | [shell/_36_damson/cbrd_23608_tde/file_enc_05/cases/file_enc_05.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_36_damson_cbrd_23608_tde_file_enc_05_cases_file_enc_05_sh-bc7c25c903/message.txt) | failure | TDE page-event counts or ordering differ | G | plausible | medium |
| test_shell | [shell/_36_damson/cbrd_23608_tde/file_enc_07/cases/file_enc_07.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_36_damson_cbrd_23608_tde_file_enc_07_cases_file_enc_07_sh-63ce2de252/message.txt) | failure | TDE page-event counts or ordering differ | G | plausible | medium |
| test_shell | [shell/_36_damson/cbrd_23608_tde/log_enc_04/cases/log_enc_04.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_36_damson_cbrd_23608_tde_log_enc_04_cases_log_enc_04_sh-3ddc50c80f/message.txt) | failure | Expected RVHF_INSERT_NEWHOME absent | I | unlikely | medium |
| test_shell | [shell/_36_damson/cbrd_23608_tde/tbl_enc_08/cases/tbl_enc_08.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_36_damson_cbrd_23608_tde_tbl_enc_08_cases_tbl_enc_08_sh-a96cea1219/message.txt) | failure | OOS diagnostic file type replaces ordinary overflow | H | unlikely | high |
| test_shell | [shell/_36_damson/cbrd_23608_tde/tbl_enc_14/cases/tbl_enc_14.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_36_damson_cbrd_23608_tde_tbl_enc_14_cases_tbl_enc_14_sh-afd5d2d444/message.txt) | failure | OOS diagnostic file type replaces ordinary overflow | H | unlikely | high |
| test_shell | [shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118/message.txt) | failure | CDC extraction rc=-10 and cub_server assertion | E | plausible | high mechanism; medium lifetime attribution |
| test_shell | [shell/_39_fig_cake/cbrd_24044_enhance_optimizer/cbrd_25080/cases/cbrd_25080.sh](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/test_shell/failures/shell_39_fig_cake_cbrd_24044_enhance_optimizer_cbrd_25080_cases_cbrd_25080_sh-b5da6c59bb/message.txt) | failure | Checks 3–5 fail after first two cardinality checks pass | K | unlikely | medium |

## Root-Cause Analysis

### A. Unordered conversion output (3 tests)

**Observed:** The three conversion cases fail on SELECT statements without ORDER BY; the diffs permute the same values. For example, expected 3,5,1,2,4 becomes 4,1,2,3,5. The recorded failing statements do not establish an explicit-order regression.

**Inferred:** These are order-sensitive expectations for unordered queries. Their names contain `order_by`, but the failing statements do not. There is no concrete deferred-write dependency in the failing expressions. **Next action / falsifier:** Compare value multisets and the explicitly ordered statements at this head and its upstream parent. Any changed value or failure under a complete ORDER BY would falsify the narrow ordering explanation. Make the testcase ordering contract explicit before changing answers.

### B. OOS plus oversized base record (2 tests)

**Observed:** Both BLOB/CLOB DDL cases expect successful large-row insertion; the engine returns `Error:-1383`, followed by zero counts where rows were expected. At this source revision, `src/base/error_code.h` defines `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` as -1383.

**Inferred:** The rows reach the existing unsupported boundary combining OOS with an oversized remaining heap record. This is a semantic rejection, not merely an error-number answer drift. **Observed locally:** Both exact cases fail on both builds, with byte-identical `.result` files. The boundary is therefore reproduced independently on the upstream parent. **Next action / falsifier:** Address the existing OOS-plus-bigone limitation in its own scope; inspect the remaining record layout before changing successful-insertion expectations.

### C. Partition-loader destination validation (1 test)

**Observed:** `partition_tbls` appends value 100 to unloaded objects for a range partition accepting values below 10. Its script explicitly intends to generate an error, but the answer expects two inserted rows. Current output reports `Line 6:Appropriate partition does not exist.` and zero inserted / one failed. The second top-level check passes.

**Inferred:** This is directly connected to the new server-loader pruning path: `load_server_loader.cpp` around lines 796–827 and 1229–1239 routes partition rows through `locator_insert_force`; `partition.c` rejects a missing destination. Rejecting 100 agrees with the partition constraint. **Observed locally:** The unchanged CTP case passes on the parent and fails on the candidate. A focused patched-build probe loads a valid 50KB row followed by key100 in one batch: exit3, zero visible rows and zero live OOS records; a following valid load succeeds with complete bytes. Empty allocated capacity remains, which is not a live-value leak. This agrees with the accepted failed-batch rollback contract. **Next action / falsifier:** Revise the partition testcase expectation in its own reviewed testcase change while retaining its deliberate invalid-input check and successful periodic-commit checks. No answer file was changed here.

### D. Large-page reload LOB identity comparison (1 test)

**Observed:** The normalized record only says `Test failed`; node 23 XML restores `bigPageSize-1 : NOK` for `csql1.log` versus `csql2.log`, with differences in `cl`/`bl` external LOB locator identities. `bigPageSize-2 : OK` confirms the load-log comparison passes. This snapshot does not show an incomplete load or self-lock failure.

**Inferred:** The script compares one row selected using `ORDER BY 1 DESC LIMIT 1`. The fixture repeatedly copies the same first-column value, leaving 256 tied rows with copied LOB identities. Different tied-row selection or locator allocation can explain the observed text. Loader insertion order could affect selection, hence a plausible relation, but payload damage is not established. **Next action / falsifier:** Compare all 256 rows using a stable unique key or a value multiset, including byte-level BLOB/CLOB contents. Missing rows or changed content would falsify an identity-only explanation. Do not simply mask locators.

### E. CDC reads an invalid OOS page (1 test)

**Observed:** Node 20 XML recovers the details absent from normalized failure text. INSERT extraction passes; DELETE reaches 0/700 and UPDATE 0/2400, with `EXTRACT_ERROR: rc=-10`. The text core trace enters `cdc_make_dml_loginfo` for an UPDATE undo image, then heap attribute decoding, `oos_read`, `oos_read_within_page`, and `pgbuf_fix_debug` at `src/storage/page_buffer.c:2487`. That source assertion rejects an OLD_PAGE fetch whose page type is PAGE_UNKNOWN. This is a server crash, not just a count-answer mismatch.

**Inferred:** The CDC before-image follows an OOS reference whose page is no longer valid. Premature reclamation is consistent with the documented CDC/OOS lifetime gap, but the trace alone does not identify the reclamation event. Local context: [CBRD-26939 lifetime analysis](/home/vimkim/gh/my-cubrid-jira/issues/CBRD-26939-oos-cdc-vacuum-lifetime_725a32c_codex.md), used as design context, not as a validated current baseline. The changed deferred-write ownership paths make a relationship plausible; this snapshot cannot attribute the defect specifically to them.

**Next action / falsifier:** Reproduce on this head and upstream parent with a delayed CDC consumer, trace OOS allocation/reclamation and vacuum progress, and check the offending undo-image reference. A still-live page or a newly malformed reference would challenge the reclamation hypothesis. Preserve correct before/after payloads through CDC consumption; suppressing the assertion or skipping DML is insufficient. Highest priority because it crashes the server.

### F. Default error-list expectation (2 tests)

**Observed:** Both parameter-dump tests differ in the default activation list. The full `bug_bts_14120` diff shows actual -1382,-1384,-1385 inserted after -50; the answer omits those entries. `system_parameter.c` around 5861–5863 includes the symbolic OOS errors.

**Inferred:** The generic develop test expectation omits feature-specific defaults. This is independent of deferred write timing; do not describe it merely as renumbering a previously present trio. **Next action / falsifier:** Compare the pinned answers and symbolic defaults on the upstream parent, then verify which errors the feature intends to activate. Different runtime defaults from the declared list would invalidate the expectation-only diagnosis.

### G. Physical TDE trace expectations (6 tests)

**Observed:** Six file-encryption cases compare physical debug event sequences. `file_enc_01` misses expected apply blocks; 02/03 have additional AES events; 04 differs in apply/page sequences; 05 has additional deallocation/NONE events; 07 passes its first check and fails the second AES sequence. Their scripts exercise encrypted page allocation, file reuse/drop, or recovery, then filter fixed trace patterns. In particular, 01 anchors filtering to an exact nine-page apply message.

**Inferred:** OOS allocation/layout changes can alter these physical traces, including filters that stop matching. The current evidence does not prove a plaintext leak or prove every difference harmless; deferred allocation timing is a plausible contributor. **Next action / falsifier:** Compare parent/head traces with file types and page ownership retained, and verify encryption flags for every allocated/recovered OOS page. A missing AES flag on a page requiring encryption would invalidate the trace-expectation hypothesis and require an engine fix.

### H. Ordinary-overflow diagnostic assumptions (3 tests)

**Observed:** `tbl_enc_08` and `tbl_enc_14` show `OUT_OF_LINE_OVERFLOW` and `OOS for HFID` where answers expect `MULTIPAGE_OBJECT_HEAP` and `Overflow for HFID`; AES remains present. `cbrd_26527` passes three checks, then cannot extract a MULTIPAGE HFID.

**Inferred:** These tests assume the ordinary overflow representation of long values. OOS changes that representation independently of deferred write timing. **Next action / falsifier:** Teach the diagnostic checks to locate the intended OOS owner/file and verify the original encryption or file-cleanup invariant. A missing owner, wrong encryption algorithm, or leaked file would refute a diagnostic-only explanation. Do not replace the expected type without preserving those checks.

### I. TDE WAL workload no longer reaches relocation (1 test)

**Observed:** `log_enc_04` fails its coverage loop at `RVHF_INSERT_NEWHOME`, with a zero match count. The loop breaks there; absence of later recovery types is not independently established.

**Inferred:** Externalizing long values can prevent the workload from forcing the same heap relocation. No WAL corruption is established by this missing coverage event. **Next action / falsifier:** Inspect the row layout and design a workload that demonstrably forces relocation under OOS, then verify encrypted recovery records. Actual relocation without the necessary WAL would refute a workload-coverage explanation.

### J. Statistics return-contract mismatch (1 test)

**Observed:** The pinned `bug_bts_5048` script expects committed-row statistics of 1 and 6; the console obtains zero for both. At this head, `statistics_sr.c` around line 356 compares `heap_get_num_objects(...)` to NO_ERROR, while the implementation in `heap_file.c` returns the object count. Positive counts therefore fail that success test.

**Inferred:** The testcase expects the CBRD-27140 / PR #7856 statistics fix, whose local commit `519cc1a43` is not an ancestor of this head. This is a source/test compatibility problem with a concrete preexisting return-contract defect, not evidence for deferred-write ownership failure. **Next action / falsifier:** Verify and integrate the appropriate return-contract fix in its own scope, then replay this exact test. Continued zero statistics after the contract is aligned would require further diagnosis.

### K. Optimizer dump and cardinality expectations (1 test)

**Observed:** `cbrd_25080` passes the first two node-cardinality checks, then fails checks 3, 4, and 5. The no-limit dump includes selectivity precision and masked cardinality-width differences. Its masking retains numeric width, so numeric/output changes survive as different question-mark sequences.

**Inferred:** This merge includes upstream optimizer work, including cost-model change #7622, which is a more concrete lead than OOS write deferral. The exact cause of every changed estimate is still unknown. **Next action / falsifier:** Inspect unmasked outputs for all three failing checks and compare against the upstream parent; validate expected cardinalities before changing masks or answers. A difference introduced only by deferred-write changes would falsify the proposed upstream attribution.

### L. Physical space accounting expectation (1 test)

**Observed:** `issue_11161_volume` fails checks 4 and 5 while the others pass; the visible diff includes SYSTEM pages 33 actual versus 34 expected and total 214 versus 215. The same testcase fails on both paired builds. The separately introduced `cbrd_20683` failure is category N.

**Inferred:** This expectation difference already exists on the upstream parent. Its allocation cause is not proved by the count alone. **Next action / falsifier:** Inspect per-file accounting before adapting expected counts; a leak or incorrect accounting would refute a benign-layout explanation.

### M. Page-lock counter increase (1 test)

**Observed:** `cbrd_20145_1` passes checks 1 and 2; check 3 compares `lock.answer_debug` against `lock.result`, finding `Num_page_locks_acquired` 25 expected versus 27 actual. The pinned workload creates a table with one integer column, inserts, updates, selects, and deletes. It does not itself require a large OOS payload.

**Observed locally:** Both exact builds reproduce 27 versus expected25. **Unknown:** Which upstream call paths added the two acquisitions. This is not the reply-byte-size mismatch described in older reports, and an OOS payload explanation is unsupported for this fixture. **Next action / falsifier:** Run the exact debug fixture on head and upstream parent, attributing counter increments to call paths. Both already produce27, so investigate the upstream counter difference before changing the answer; this is not a demonstrated deferred-write-specific increase.

### N. Catalog bootstrap incorrectly prepares internal records (1 test)

**Observed:** `cbrd_20683` passes unchanged on parent9c768e4 and fails on candidate878f18b. A minimized fresh 4KB/64MB `createdb` comparison has72 files on the parent and73 on the candidate. The extra OOS file belongs to `_db_authorization`; it adds one0.25MiB allocation sector. A debugger stopped in `locator_prepare_client_row` during authorization installation: `catcls_Enable=false`, actual classOID `(0|193|5)`, cached authorizationOID all zero. The existing `oid_is_system_class` bypass consequently misses the internal row.

**Repair:** Bypass deferred preparation while catalog classes are disabled, and apply the corresponding error-cleanup guard. Normal restart compiles catalog classes before ordinary workloads. The new fresh-database utility regression fails on unpatched878f18b and passes on the repair. The original unchanged CTP testcase also passes1/1 after the repair. Standards and Spec reviews found no blocking issues. This establishes the local repair, not remote acceptance.

## Subsequent Local Verification

Durable evidence: [paired runs and patched verification](ci-fix/pr-7927/878f18b-20260914/). The original analysis was read-only; the following work belongs to the separately authorized implementation of ticket22. No remote testcase answers were changed.

| Cases | Parent9c768e4 | Candidate878f18b | Interpretation |
|---|---|---|---|
| Three medium conversions | 3/3 fail | 3/3 fail | All three paired `.result` files byte-identical; unordered expectations remain unsupported |
| Two SQL OOS/bigone cases | 2/2 fail | 2/2 fail | Both paired `.result` files byte-identical |
| Seventeen shell cases excluding bootstrap, partition loader and CDC | 17/17 fail | 17/17 fail | Baseline-reproduced failures; this does not establish every physical/encryption difference harmless |
| CDC, corrected network setup | INSERT700/700; DELETE21/700; UPDATE0/2400 | INSERT700/700; DELETE15/700; UPDATE2/2400 | Both extraction failures use rc-10; the local counts differ and do not prove an identical crash stack |
| Partition loader | pass | fail | Intended rejection; patched probe establishes batch rollback and next-operation usability |
| Fresh 4KB space case | pass | fail | Introduced bootstrap error; patched run1/1 pass |

The first all20 shell sweep reported18 parent failures and20 candidate failures, but its CDC attempt lacked a usable non-loopback address and failed during connection setup. It is retained as infrastructure evidence, not engine attribution. A separate dummy interface inside an isolated network namespace enabled the corrected CDC runs above. No host network configuration changed.

The first patched shell replay passed both volume comparisons but CTP flagged a stale September11 core copied from the existing installation. The retained attempt records the old core identity. CTP moved that file into its backup; the clean subsequent replay has one executed testcase, one success and zero failures. Initial SQL attempts used incorrectly absolute exclusion paths; they were stopped, retained, and replaced with scenario-relative exclusions. Final SQL/medium runs execute exactly2/3 cases respectively.

Patched verification:27/27 CTest tests pass in137.13s; loader, replication/HA, and fresh bootstrap utility runners pass. Transaction/MVCC/crash recovery passes on a retained retry. Its first attempt passed MVCC but the restart utility reported the killed server still running; the retry used the same code in a fresh fixture after the initial concurrent load subsided. This is a retained restart-timing flake, not an erased failure or proof of timing robustness. The catalog query verifies DBA/PUBLIC existence, not exhaustive authorization values.

The repair is committed locally as `6acfbb82342c74806fea57c6328a9aff16ec273d`. The push was rejected by the local `lefthook.yml` freshness hook because current target `38093ea859a8a08e20405b72b0cb395205bedb2f` adds the OOS identity-stamp change and other storage/test work. No source push or CI trigger occurred. A scope decision on merging/revalidating that materially changed base is pending. A read-only [merge preview](ci-fix/pr-7927/878f18b-20260914/merge-preview/assessment.json) finds one CMake content conflict and a semantic integration gap: the textually merged prepared finalizer does not request or serialize the new identity stamp into its24-byte stub. This is source evidence, not a tested merged-build failure; conflict resolution alone would be insufficient. The repaired source is tracked separately by `patched/source.patch`, its SHA-256 in `patched/provenance.json`, and hashes of the installed server/library. Patched-worktree provenance also records preserved preexisting JDBC checkout936df5f and generated CCI edits; the paired comparison builds used their pinned submodules. The affected patched utility check uses CSQL, not JDBC. Original878f18b also passed all27 configured tests and the loader, replication and transaction runners before repair. Those historical passes are not relabeled as patched runs.

Paired resource measurements use three repetitions of four identical workloads (24 samples total), with fresh servers, `/proc`VmHWM and GNU-time client RSS. Median values below are KiB; no numerical performance threshold was agreed.

| Workload | Parent server peak / growth | Candidate server peak / growth | Parent / candidate client peak |
|---|---:|---:|---:|
| SQL,32-byte values | 350044 / 8284 | 351968 / 8288 | 18560 / 19840 |
| SQL,50000-byte values | 393600 / 50560 | 393600 / 49920 | 19200 / 19200 |
| Loader,mixed32/4000/50000-byte values | 478752 / 136348 | 486352 / 142672 | 59080 / 58860 |
| Loader,50000-byte values | 663724 / 320684 | 673372 / 329092 | 212468 / 213468 |

The loader growth delta is6324/8408KiB, consistent with retaining canonical input within the per-worker8MiB batching budget, plus staging and oversized-row allowance. This is an inference from the ownership design and RSS, not a direct allocation count or new leak proof. The bootstrap-only patch does not change those loader ownership paths; these measurements remain explicitly tied to unpatched878f18b. Existing scoped Valgrind evidence is historical and does not establish current undefined-value cleanliness. Vacuum convergence, no-logging crash durability and multi-node heartbeat failover remain outside these runs.

## Recommended Actions

1. Publish the reviewed bootstrap repair and collect its own exact-revision GitHub/CTP results. Keep ticket22 and replacement acceptance open until that evidence is reconciled.
2. Retain the23 baseline-reproduced failures separately. The CDC before-image crash is the highest-severity broader OOS defect; investigate allocation/reclamation and delayed-consumer payloads rather than suppressing its assertion.
3. Review a separate partition testcase correction that expects invalid-destination rejection and checks batch rollback. Its existing answer contradicts the script's stated intent; it was not modified here.
4. Preserve semantic coverage when correcting physical TDE/overflow, LOB identity, statistics/optimizer, default-list and unordered-result expectations. A baseline reproduction does not certify encryption, reclamation or accounting correctness.

## Evidence and Limitations

- [Manifest](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b/manifest.json), each suite's `summary.json`, `failed-tc.txt`, `failed-tests.json`, all 25 failure metadata/message/diff directories, and artifact/log/source indexes were inspected. Counts reconcile to 21,709 total records, 21,654 success, 25 failure, and 30 skipped; no error or unknown records need a separate inventory.
- Downloaded text artifacts: medium 28 (23,749,268 bytes), SQL 52 (65,922,085 bytes), shell 187 (143,020,272 bytes). Empty normalized diffs for bigPageSize and cbrd_27064 were supplemented from the matching shell XML; empty files were not treated as matching outputs.
- [CDC extracted XML text](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b-api-20260914/cbrd_27064-xml-text.txt) and [bigPageSize extracted XML text](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b-api-20260914/bigPageSize-xml-text.txt) come from node 20 and node 23 `test-shell.xml` artifacts respectively. Their original XML remains in the collector artifact tree.
- [Shell checkout provenance](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b-api-20260914/shell-checkouts.json), [pinned script hashes](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b-api-20260914/pinned-shell-sources.json), and [final PR state](/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/878f18b-api-20260914/pr-status.json) preserve supplemental identity. Shell job workflow is `4fa243e4-52e7-446e-8600-d174bd115efe`.
- The binary core archive was not downloaded. CDC immediate failure analysis uses the text backtrace and exact source; allocation/reclamation timing remains inferred. Some side-by-side diffs truncate columns, limiting exact numeric reconstruction.
- Older reports are not used as proof of this head's baseline behavior. New local paired runs and the bootstrap repair are recorded above; no remote CI trigger or testcase-answer publication is implied by them. Existing submodule changes and unrelated docs changes were preserved.
