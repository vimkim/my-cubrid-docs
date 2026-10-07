# PR #7927 testcase assessment and local verification

The justified testcase change is confined to the server-side partition-loader case. Its old test2 answer requires accepting an out-of-domain value in a direct child partition. Independent partition-domain, destination-routing, rollback and recovery evidence supports replacing that success expectation with explicit semantic checks. The committed testcase passes against both the original PR head and the final `heap_oos_value_ref` extraction. No medium answer, loader diagnostic/count predicate, index threshold or CDC testcase was changed.

This is a bounded native local assessment, not a replay of the historical GitHub Actions CTP environment and not a CI waiver. Tracker **242** retains the wider ordering-preservation and failure-attribution follow-ups.

## Inputs and revision boundary

The [published exact-head report](https://github.com/vimkim/my-cubrid-docs/blob/1f16cb1e0da2ac63d76023f8b9a399d2c3f92b93/cbrd-27089/ci_analysis_report_4be72fc_codex.md), [posted summary](https://github.com/CUBRID/cubrid/pull/7927#issuecomment-6035585732), and `.handoff/pr7927-testcase-fix.md` supplied the failure inventory, required falsifiers and branch routing. The report remains evidence for its pinned executions; the native results below are separate evidence.

| Input | Exact revision / identity |
| --- | --- |
| PR identity, rechecked before reproduction | `CUBRID/cubrid#7927`; head repository `vimkim/cubrid`; head branch `feat/oos-deferred-write`; base branch `feature/oos-merge` |
| Original engine head | `4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c` |
| PR base and merge-base | `fb567a629cdb390fff920542173fa36f454c74a0` |
| Final engine, locally committed extraction | `f3144ab4b72fc2bf73f115c9da1cf193c756457a`; install reports `11.5.0.2648-f3144ab` |
| Public native testcase revision; unchanged | `f5e610d91efdeaa9fcf089f47bf4a89c103a4a93`, bot initialization on `tc/pr-7927` |
| Original private native testcase revision | `57ed79b2178c66c5a7c57d455b8673ada2dba15e`, bot initialization on `tc/pr-7927` |
| Final private testcase, locally committed fix | `10f3500291c3d3f5c7bcf6ed5c90142a6ed0f532` |
| CI testcase revisions | Public `bdba62aee0faec05abdd861518824c69b6c1b3c5`; private `c4b9d482fbd491a68510b2552df2c3cac91911fc` |
| Native runner | `cubrid-testkit dev`; binary SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a` |
| Copied runner assets | CTP checkout `9c62858b10005d721546cc007be260844033b9e9`, with pre-existing local asset modifications recorded below |
| Medium archive | `mdb.tar.gz` SHA-256 `63833b7abf965621539bc4216aeb5fc3527c173c7a4d91436bd113a2f4269a06` |
| Manual | `CUBRID/cubrid-manual` develop `3b6ae97bfbdc664b010ffa933ded5a05b291ae03` |
| Authoritative OOS context | `vimkim/cubrid-oos-context` HEAD `75f8b58674ac901d478ba60f9b2cc2fff11f66f6`; loaded normative `OOS-CONTEXT.md` local update of 2026-09-22, SHA-256 `8b42fe41a314cca6dcdeac90d32d40b51974a11177fd14f4f2ca0d590e912dc7` |

Both testcase worktrees were inspected, fetched and fast-forwarded to their current bot-created initialization commits before edits. Their selected directory Git objects are identical to the pinned CI testcase revisions. [Input manifest](input-manifest.json) records those object identities, parser/error-handler/session/B-tree/vacuum source identities, manual/context hashes and the complete tracked CTP asset hash inventory. The two initialization commits have no substantive testcase changes.

The current CTP checkout already had executable-mode changes in `util_compat_test.sh`, `shell/init_path/cubrid`, `sql/bin/interactive.sh`, and `sql/bin/run_memory.sh`, plus `shell_config.xml` broker-port changes and untracked result/JDBC assets. All were preserved and copied as native assets. The report's historical head/base CTP revisions (`44e3f97…` / `4d0043a…`) differ from these native assets. No historical tool, helper, configuration, runtime, shard-predecessor or CI equivalence is claimed. Generated JUnit `classname` URLs say `develop`; exact executed source identity is the retained `identity.json` plus expected/dispatch lists, not those generated floating URLs.

## Decision for each selected failure

| Pinned head failure | Independent contract and local evidence | Decision and remaining work |
| --- | --- | --- |
| `medium/_02_xtests/cases/to_char_order_by.sql` | Preserve conversion values, explicitly ordered results and tracker 242's ordering objective. Complete serial native directory passes on exact head/base; this case's raw result is byte-equal to base and the existing answer. | No change. Historical unordered-output drift is not causally explained by this local pass. |
| `medium/_02_xtests/cases/to_number_order_by.sql` | Same preserved contract; raw head/base/answer bytes are equal in the controlled complete-directory run. | No change. Do not sort away the observation or rewrite the answer. |
| `medium/_02_xtests/cases/to_timestamp_order_by.sql` | Same preserved contract; raw head/base/answer bytes are equal in the controlled complete-directory run. | No change. Historical execution-state/plan/tool differences remain unresolved. |
| `shell/_06_issues/_25_2h/cbrd_26280/cases/cbrd_26280.sh` | The testcase explicitly requires SA/CS diagnostic formatting consistency, a syntax diagnostic for malformed `NNUL`, one missing-attribute message, no duplicates, and two counted errors. All 18 existing assertions pass twice on each exact engine with matched native configuration. | No change. The historical missing parser diagnostic/count-one observation remains unresolved; no callback trace establishes a replacement contract. |
| `shell/_06_issues/_15_1h/bug_bts_15489/cases/bug_bts_15489.sh` | Keep its documented post-CBRD-20074 strict `0 < total_pages < 100` predicate, 4K database, 46,000 rows, DELETE and 60-second wait. Native head page counts are 64 and 92; base 55 and 82. Existing assertion passes in all four observations. | No change. The historical exact-100 boundary is neither exonerated nor evidence for changing the bound; allocation/vacuum timing remains a follow-up. |
| `shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh` | Reject invalid direct-child input; accept valid child input; route root input; preserve committed data and roll back a failed batch. Fresh generated-fixture and two-child probes establish these behaviors. Original case: native base PASS, original head FAIL due to old success answer. Fixed case: original head and final extraction PASS with 28 assertions. | Narrow fix justified and committed. Windows answer shape is corrected; Windows execution is unverified. |
| `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | Exact pinned report shows the same failing DELETE/UPDATE extraction category on base. Accepted ADR-0005 requires this CDC/history gap to remain visible. | Unchanged and not rerun locally. Pre-existence does not waive CI or prove zero PR influence. |
| `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | Pinned head/base both report extraction errors, with differing page-size/count outcomes. ADR-0005 keeps the case enabled. | Unchanged and not rerun locally. Preserve extractor-error/LSA follow-up rather than masking it. |

The [manual ORDER BY contract](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/sql/query/select.rst#L561) permits variability when SQL has no `ORDER BY`. That SQL rule does not cancel the user's ordering-preservation objective or justify an answer rewrite. [Raw ordering comparison](ordering/comparison.json) proves each selected native case individually; six retained `.result` files preserve presentation bytes. The complete directory's 444 passing case records are retained, including ordered tests and their predecessors. No conclusion relies only on the suite total or absence from a failure list.

For `cbrd_26280`, `load_grammar.yy`, `load_error_handler.cpp` and `load_session.cpp` have equal exact source blobs on base/head, while `finish_line` changes its prepare/error path. Those identities narrow investigation; they do not establish which callback suppressed the historical parser message. The native assertion receipts explicitly include Test7's failure status, syntax/error messages, nonduplication and expected failed-count checks. This assessment did not instrument callbacks because the controlled executions did not reproduce the missing diagnostic.

For `bug_bts_15489`, B-tree and vacuum source blobs match the base; changed insert callers can still affect allocation. Only the original 60-second endpoint was measured. There is no before-delete capacity trace, extended cleanup series or historical predecessor reproduction, so no claim of a persistent growth defect, corruption, or repaired performance is supported.

The [accepted history-scope ADR](https://github.com/vimkim/cubrid-oos-context/blob/75f8b58674ac901d478ba60f9b2cc2fff11f66f6/docs/adr/0005-defer-oos-history-from-the-11-5-merge.md#L17) is design context for CDC preservation. The three pinned base-only observations (`hide_cubrid_replay`, `bug_bts_15156`, `cbrd_26349`) remain separate process-sampling, service-lifecycle and DB-link follow-ups; none was changed or rerun, and their head PASS observations are not claimed as PR fixes.

## Why the partition fix is correct

### Required behavior and source connection

The [range-partition manual](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/sql/partition.rst#L115) requires rejection when no range accepts a value. [Direct child access](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/sql/partition.rst#L325) requires an error if inserted/updated data does not belong to that child. Thus child `p0 VALUES LESS THAN (10)` may contain `1`, and cannot accept `100`; a sibling accepting `11` does not make direct-p0 `11` valid.

Current loader implementation distinguishes root/child pruning in [server_object_loader::start_attrinfo](https://github.com/CUBRID/cubrid/blob/4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c/src/loaddb/load_server_loader.cpp#L1205), then uses [locator_insert_force in flush_records](https://github.com/CUBRID/cubrid/blob/4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c/src/loaddb/load_server_loader.cpp#L827) to select and validate the destination. The unchanged [partition code](https://github.com/CUBRID/cubrid/blob/4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c/src/query/partition.c#L3530) distinguishes no accepting destination (`ER_PARTITION_NOT_EXIST`, -891) from [a value outside an explicitly selected child](https://github.com/CUBRID/cubrid/blob/4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c/src/query/partition.c#L3671) (`ER_INVALID_DATA_FOR_PARTITION`, -1109).

The [periodic commit option](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/admin/migration.inc#L422) and [load_session batch handling](https://github.com/CUBRID/cubrid/blob/4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c/src/loaddb/load_session.cpp#L177) support testing both records in one failed batch. The fix specifies `-c 100` for two-row error fixtures; session stats count rows committed after transaction commit. Exact zero inserted / one failed counts and retained rows are verified independently, not inferred from a printed error alone.

The manual describes SQL partition semantics; applying the same domain invariant to server loaddb is supported here by PR intent, the changed loader routing path and fresh direct loader execution. It is not asserted solely from a SQL manual paragraph.

### Fresh independent oracle before editing expectations

[Host probe receipts](evidence/head-partition-contract-03/events.json) identify the exact original head and fresh owned database `probe7927c`. [Its verdict](evidence/head-partition-contract-03/verdict.txt) checks:

1. Actual `unloaddb` output contains `%class [dba].[t__p__p0] ([i])`. Appending `100` to the valid `1` input fails, inserts zero, reports one failed object, and leaves both root and child empty.
2. Reloading the untouched valid input succeeds and leaves exactly one row, `i=1`, visible through both root and child.
3. For a fresh two-child table, root input `1,11` routes to p0/p1; direct-child input `2` succeeds. The committed root values are exactly `1,2,11`.
4. Direct-p0 batch `3,11` fails with the wrong-child error and rolls back pending `3`. Root batch `4,100` fails with no destination and rolls back pending `4`. Counts/minimum/maximum in both children and root show the committed `1,2,11` rows survive both failures.
5. Subsequent root input `12` succeeds and routes to p1; root/child counts are exact.

The first host attempt was inconclusive because a daemon retained a stdout pipe; the runner was corrected to capture daemon output in files. The second reached sibling rejection but the probe expected the wrong diagnostic (-891) where source specifies -1109; it returned failure despite correctly rejecting the row. The third corrected oracle passes. These failed attempts and receipts remain under the full attempt root and their bounded diagnostics are retained. Neither harness mistake is classified as an engine defect.

Prior testcase history (`018fc45bb12a63d24f4d85315790437cbf7cdaae`, and the corresponding later correction on another retained branch) showed a partition-expectation correction. It was research evidence only. The actual decision and added assertions above rely on the fresh source/manual/loader oracle, not on promoting previous output to an answer.

### Committed testcase changes

Private commit `10f3500291c3d3f5c7bcf6ed5c90142a6ed0f532` changes only:

- `shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh`
- `shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/bug_bts_11093.answer`
- `shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/bug_bts_11093.answer_WIN`

The two answers remove only test2's 19-line invalid-input success transcript; they preserve test1/test3 bytes, including existing carriage-return formatting. Failed loads use separate output files with explicit exit/error/count checks. New SQL row checks establish rollback and recovery through root and child, then validate root selection, valid child input, wrong-child rejection, pre-existing row preservation and another valid load. Existing test1's 40-row success and test3's 10,000-row periodic-commit/count checks remain active. The initial new generated-class regex omitted `unloaddb`'s closing `]`; its failed run is retained, the regex was corrected, and a fresh native run passed before commit.

The native final run uses the committed private revision, clean engine/testcase status, and the copied final installation's embedded SHA. It passes **1/1 case, 28 write_ok, 0 write_nok, zero skips**. This verifies the extracted engine and revised testcase together. Linux native execution is the verification boundary; the Windows answer was updated for the identical invalid success block but Windows execution was not performed.

## Native verification receipts

The replay used the suite-specific focused helper's preflight/config/verdict checks, `TESTKIT_NATIVE=shell` or `sql`, containment enabled, one slot and no retries. Shell source checkouts remain read-only during runtime; medium copies the entire `_02_xtests` directory and archive, preserving serial predecessors. Each attempt has independent installation copy, HOME, registry, config, TMP and contained process/IPC/network resources. The scripts [replay_native.py](replay_native.py), [partition_contract_probe.py](partition_contract_probe.py), [inventory_inputs.py](inventory_inputs.py), and [retain_evidence.py](retain_evidence.py) are retained. No legacy CTP command or comparison was executed.

| Attempt | Engine / testcase | Executed evidence and verdict |
| --- | --- | --- |
| `head-shell-01` | 4be72fc / private57ed79b | Selected 2 PASS / partition FAIL; total24 includes21 unselected macro skips. Runner0, verifier1; aggregate verdict inconclusive for focused contract. |
| `base-shell-01` | fb567a6 / private57ed79b | Selected3 PASS; same21 unselected macro skips. Runner0, verifier1; aggregate verdict inconclusive. |
| `head-medium-01` | 4be72fc / publicf5e610d | Preparation fails because namespace ccache temporary path is not writable, causing locale/createdb failure; no testcase verdicts, runner1. |
| `base-medium-01` | fb567a6 / publicf5e610d | Same preparation failure; no testcase verdicts, runner1. |
| `head-shell-02` | 4be72fc / private57ed79b | Exactly3 executed, zero skips; index/cbrd_26280 PASS, original partition FAIL; runner0, strict verifier1. |
| `base-shell-02` | fb567a6 / private57ed79b | Exactly3 executed, zero skips;3/3 PASS; runner0, verifier0. |
| `head-medium-02` | 4be72fc / publicf5e610d | Complete serial directory444/444 PASS; runner0, verifier0; selected raw results byte-equal to answers. |
| `base-medium-02` | fb567a6 / publicf5e610d | Complete serial directory444/444 PASS; runner0, verifier0; same selected raw bytes. |
| `head-partition-fixed` | 4be72fc / uncommitted patch on57ed79b | 27 OK /1 NOK; only generated-class regex assertion incorrect;1 failed case, strict verifier1. |
| `head-partition-fixed-02` | 4be72fc / corrected patch on57ed79b |1/1 PASS;28 OK /0 NOK; runner0, verifier0. |
| `final-partition` | f3144ab / committed10f350029 |1/1 PASS;28 OK /0 NOK; zero skips; clean source statuses; runner0, verifier0. |

[Evidence manifest](evidence/manifest.json) links full local attempts and hashes retained receipts/full run logs. Each successful/failed suite receipt includes expected membership, dispatch/JUnit records, configuration, exact identity, runner exit and strict verification. Failed runner/setup attempts are retained rather than omitted from the table. Shell assertion excerpts preserve case-level checks and index page counts. Medium JUnit retains all 444 case verdicts; [ordering/comparison.json](ordering/comparison.json) retains explicit selected-case byte comparisons.

For corrected shell selection, the initial native discovery added corpus-wide `LINUX_NOT_SUPPORTED` skips despite the focused list. Only the attempt-local macro filter was cleared, after confirming none of the three selected scripts contains the macro. Expected selection and selected case memberships are unchanged; no repository predicate was edited. The medium preparation reruns use attempt-local `CCACHE_DIR` and `CCACHE_TEMPDIR`. Archive extraction still emits uid1106/gid1003 ownership warnings inside containment; subsequent database preparation and case execution pass. These warnings are not relabeled as testcase failures.

[Normalized shell configuration](evidence/shell-normalized.conf) and [medium configuration](evidence/medium-normalized.conf) are byte-equal between controlled head/base after replacing only attempt-root paths. Raw config hashes differ because testcase-list/archive/scenario paths are attempt-local. Archive bytes, runner binary, copied assets and medium scenario file hashes match. This proves local controlled inputs, not historical CI equivalence or identical internal worker schedules/OIDs/plans.

## Local deliverables and preserved resources

| Worktree | Branch / commit | State and purpose |
| --- | --- | --- |
| `/home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-7927` | `tc/pr-7927` / `10f3500291c3d3f5c7bcf6ed5c90142a6ed0f532` | Clean; three-file partition fix; `bash -n`, `git diff --check`, original/final native runs pass. |
| `/home/vimkim/gh/cubrid-testcases/tc-pr-7927` | `tc/pr-7927` / `f5e610d91efdeaa9fcf089f47bf4a89c103a4a93` | Clean; unchanged;444-case native head/base verification and selected order receipts. |
| `/home/vimkim/gh/my-cubrid-docs-pr7927-testcase-assessment` | `docs/pr7927-testcase-assessment` | Assessment, reproduction scripts, manifests and bounded receipts committed locally; exact docs commit is in the agent handoff. |
| `/home/vimkim/gh/cb/pr7927-assessment-head` | `investigate/pr7927-assessment-head` /4be72fc | Clean source; independent debug_gcc build/install; retained owned probe DBs. |
| `/home/vimkim/gh/cb/pr7927-assessment-base` | `investigate/pr7927-assessment-base` /fb567a6 | Clean source; independent debug_gcc build/install. |

[Build receipts](evidence/build-receipts.json) retain successful build/install tails and full-log hashes. Both engine builds used their live preset-aware just workflow with `CMAKE_BUILD_PARALLEL_LEVEL=4`; only their newly generated CCI version header was restored after verification. The original dirty engine worktree, original installation, CCI/JDBC changes and Agent2 build/install were preserved; Agent2's installation was copied only after the orchestrator's explicit idle/ready gate. No engine source repair was made in this assessment.

Full native attempts are retained at `/home/vimkim/tmp/pr7927-assessment-20261007`; source/install repro worktrees and owned probe databases remain for human inspection. Probe-specific server and selected service stop commands completed; no global kill, IPC cleanup or unrelated DB deletion was performed. [Final head doctor receipt](evidence/head-doctor-final.txt) still reports stale or unconfirmed `sp_probe7927{,b,c}.sock` filesystem entries and 2422 inaccessible PIDs. These entries are preserved. Limited process visibility prevents claiming the entire host is inactive; that limitation is separate from completed native contained runs and successful semantic verdicts.

## Remaining limits and next action

Historical ordering drift, missing parser diagnostic/error-count behavior, and the exact-100 index observation are still unresolved. The controlled native results support preserving their current contracts, and establish no new reproducible engine defect in this investigation. They do not erase the pinned failures or prove an engine-only, runner-only or harmless cause. CDC/history failures remain a separately accepted design gap requiring visible tests and future investigation.

If those signatures recur, retain exact runner/helper/config/archive and predecessor inputs, plans/OIDs/order bytes, loader parser/worker callback order, and before/after allocation/vacuum progress as appropriate. An explicitly authorized legacy comparison or future CI execution is a separate workflow. No push, CI trigger, external comment, reviewer-thread action or local integration merge was performed. All meaningful task changes are locally committed for review; integration still requires the prescribed confirmation.
