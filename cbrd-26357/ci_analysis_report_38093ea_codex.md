# CI Failure Analysis: PR #6864 at `38093ea`

## Executive Summary

CircleCI reports **9 failed tests: 2 SQL and 7 shell**, with zero error/unknown records. Medium passes all 975 tests. Four failures are stale OOS error-number expectations; two follow the index-build sort split (a new parameter and changed diagnostic call path); one compares optimizer diagnostic estimates; two are incomplete CDC historical extraction. The latter remain a functional stability concern. This snapshot does not certify `feat/oos` as stable.

GitHub Actions independently reports the same two SQL and seven shell testcase names. Its seven failing shell XML records show the same categories, with timing-dependent CDC counts. “Check TC PRs” is a separate merge gate: companion testcase PRs were still open.

## CI Snapshot

| Suite | State / CircleCI job | Tests | Success | Failure | Skip | Error | Unknown |
|---|---|---:|---:|---:|---:|---:|---:|
| test_medium | success / [155193](https://circleci.com/gh/CUBRID/cubrid/155193) | 975 | 975 | 0 | 0 | 0 | 0 |
| test_sql | failed / [155194](https://circleci.com/gh/CUBRID/cubrid/155194) | 17463 | 17461 | 2 | 0 | 0 | 0 |
| test_shell | failed / [155191](https://circleci.com/gh/CUBRID/cubrid/155191) | 3277 | 3240 | 7 | 30 | 0 | 0 |

All requested suites are terminal and collected. Release/debug build prerequisites passed. No missing suite is represented as successful.

## Evidence Scope

- PR: https://github.com/CUBRID/cubrid/pull/6864 (`feat/oos` → `develop`).
- Engine: `38093ea859a8a08e20405b72b0cb395205bedb2f`; collection date: 2026-09-15 KST. The head includes the OOS identity-stamp merge and a subsequent develop merge.
- Collector: `0.1.0 (3e9502f72350, release)`. All three collections exited 0, using text artifacts and testcase-source enrichment, without waiting for CI. Existing gh authentication resolved the earlier unauthenticated GitHub rate limit.
- Durable collector bundle: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26357/38093ea`. SQL downloaded 65 text artifacts / 64,586,548 bytes; shell 77 / 138,709,304 bytes. No binary cores were downloaded.
- SQL case/answer links independently pin both failures to `CUBRID/cubrid-testcases@94e094bc669e6721018555b48f2db1dd579d1fa9`; all four referenced sources downloaded successfully.
- CircleCI shell revision is **unknown**: source index is empty and seven checkout-output requests returned HTTP 404. Moving `develop` links are not revision proof. Current XML/feedback still proves the observed failures.
- Supplemental evidence: `/home/vimkim/gh/cubrid-circleci-analyzer/data/api-pr6864-38093ea-20260915`, with `provenance.json`, exact engine Git objects, source diffs, Actions logs, seven failing shell XMLs and per-shard `build.read`/`tc.read` files.
- Actions [run 34851520737](https://github.com/CUBRID/cubrid/actions/runs/34851520737), attempt 1, is an `issue_comment` workflow at workflow SHA `f1ae86ff7d1d80e1a96413dd464a2853ab03d191`. That is not the tested engine SHA: each failing shell shard's build provenance pins the engine above. Collect logs reconcile 50/50 shell and 10/10 SQL shards to this run, with no unrun cases. All seven failing shell shards pin `CUBRID/cubrid-testcases-private-ex@c71941cf856ace83649ed64e45f82c41f7b045d5`, branch `tc/pr-6864`. Exact case directories were extracted from that Git object, not from a different checkout HEAD.
- Exact engine source was read through Git objects in `/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write`; the working tree was not changed or used as the tested revision. The OOS environment validator found only an unset PRESET_MODE warning; no builds or local reproductions were needed for this snapshot.

## Failure Inventory

The rows below inventory each CircleCI failure once. Actions repeats the same testcase names; it is corroboration, not nine additional distinct tests. Categories total A=4, B=1, C=1, D=1, E=2.

| Suite | Test | Result | Observed signature | Category | OOS relation | Confidence |
|---|---|---|---|---|---|---|
| test_sql | `sql/_13_issues/_14_1h/cases/bug_bts_10516.sql` | failure | Expected -1382; actual -1383 | A: error-number drift | direct expectation coupling | high |
| test_sql | `sql/_15_fbo/_02_qa_test/cases/fbo_ddl02.sql` | failure | Expected -1382; actual -1383 | A: error-number drift | direct expectation coupling | high |
| test_shell | `shell/_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh` | failure | Checks 2–3: default call-stack error list differs | A: error-number drift | direct expectation coupling | high |
| test_shell | `shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh` | failure | Check 1: default call-stack error list differs | A: error-number drift | direct expectation coupling | high |
| test_shell | `shell/_06_issues/_11_2h/bug_bts_5423/cases/bug_bts_5423.sh` | failure | Check 6: extra index_build_buffer_size=2.0M | B: parameter-list expectation | unlikely; develop sort change | high |
| test_shell | `shell/_36_damson/cbrd_23608_tde/temp_enc_09/cases/temp_enc_09.sh` | failure | Six sort_listfile TDE lines versus eight expected | C: sort diagnostic path | unlikely; integer-only test | high cause / bounded security conclusion |
| test_shell | `shell/_39_fig_cake/cbrd_24044_enhance_optimizer/cbrd_25080/cases/cbrd_25080.sh` | failure | Checks 1–2 pass; checks 3–5 differ in masked selectivity/cardinality | D: optimizer diagnostic expectations | unlikely; no demonstrated OOS path | high signature / medium attribution |
| test_shell | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | failure | DELETE 0/700, UPDATE 0/2400; extraction rc=-10 | E: CDC historical extraction | plausible history-lifetime defect | high failure / medium precise cause |
| test_shell | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | failure | All sizes reach 2000 updates but have extraction errors; CONFIGS_OK=0 | E: CDC historical extraction | plausible history-lifetime defect | high failure / medium precise cause |

## Root-Cause Analysis

### A. Error-number drift (4 tests)

**Observed:** Both SQL diffs are only `Error:-1382` → `Error:-1383` for a wide LOB INSERT. The testcase answers already expect rejection; these are not the develop-answer variants that expect insertion success and then show zero-row cascades. Shell feedback on nodes 17 and 42 shows actual `-1382,-1384,-1385` versus expected `-1381,-1383,-1384` in `call_stack_dump_activation_list`.

**Cause:** Exact `src/base/error_code.h:1778` inserts `ER_SP_PARALLEL_ENABLE_NO_SQL=-1380` ahead of the OOS errors. `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` is now -1383, and BAD_INLINE_HEADER/CORRUPTED_RECORD/INVALID_ARGUMENT are -1382/-1384/-1385. `system_parameter.c:5901` uses those symbolic constants, so its numeric list changes automatically. The diff against `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` records this second shift. The prior answer correction was for the previous numbering.

`heap_file.c:13902` still rejects a demoted OOS-backed record that would require ordinary big-record overflow, before writing OOS records. The many-LOB-column cases exercise that boundary; the current mismatch concerns its numeric identity.

**Next / falsifier:** Update the two SQL answers and three shell answers to the independently verified current constants, then replay those four unchanged cases. Any remaining nonnumeric difference would falsify the claim that renumbering alone repairs them. Do not copy the previous report's old numbers. No answers were changed in this task.

Evidence: SQL `failures/*/{message,diff}.txt`, downloaded case/answer sources; shell nodes 17/42 `ctp_log/feedback.log`; supplemental `source/error_code.h`, `source/system_parameter.c`, `source/heap_file.c`, `error-code-delta.patch`. Historical context: [previous repair report](ci_analysis_report_f4299ac_codex.md) and local JIRA draft `CBRD-27403-oos-error-code-answers_f4299ac_codex.md`; neither is a current JIRA-status claim.

### B. New index-build parameter (1 test)

**Observed:** `bug_bts_5423` passes checks 1–5. Check 6 compares the parameter dump and sees an additional `[S ] index_build_buffer_size=2.0M (2.0M)` line.

**Cause:** Commit `6faddec23` (index-build sort separation, PR #7831), reachable from the tested head, adds this parameter. The expected parameter listing omits it. This is directly supported by `index-sort-delta.patch`, not an inferred OOS side effect.

**Next / falsifier:** Extend the expected parameter listing after checking the new parameter's declared default. Replay all six checks; a differing existing value would require a separate diagnosis. Evidence: node 48 feedback and exact Actions case/answer sources.

### C. Index sort no longer emits the counted query-sort diagnostics (1 test)

**Observed:** `temp_enc_09` compares eight expected `TDE: sort_listfile()` messages against six actual messages (three unencrypted and three encrypted). Its source executes ORDER BY, GROUP BY, analytic sorting and CREATE INDEX for an integer-only ordinary/encrypted table pair, then filters diagnostics specifically by `sort_listfile`.

**Cause:** The same `6faddec23` change moves index construction from `sort_listfile()` to `btree_sort()` (`btree_index_sort` call-site diff). The two CREATE INDEX operations therefore no longer contribute to that filtered diagnostic count. Exact `btree_sort.c` retains `includes_tde_class`/`tde_encrypted` propagation. This explains the missing two lines; it does **not** independently prove every new index-sort spill is correctly encrypted.

**Next / falsifier:** Split query-sort and index-sort diagnostic expectations and verify the new index-sort encryption path before revising coverage. If either query-sort message is absent or an encrypted index spill is plaintext, this is more than diagnostic drift. Evidence: node 49 XML/feedback, exact testcase, `index-sort-delta.patch`, `source/btree_sort.c`.

### D. Optimizer diagnostic estimates survive normalization (1 test)

**Observed:** `cbrd_25080` passes both explicit LIMIT node-cardinality checks. Its three full-plan comparisons fail: actual selectivity renders as `?.?` versus expected `?.??????`, and masked estimated cardinality has a different digit count. The no-limit plan remains an index scan and both sides report no rows. The testcase inserts col_c values 0–9, then queries col_c='11'; expected-result comparison includes optimizer estimates as well as semantic output.

**Inferred:** The immediate failure is an overly specific diagnostic expectation. Masking digits retains their count and decimal width, so it does not actually ignore changing estimates. The exact optimizer change responsible for the estimate was not isolated; this report does not declare every estimate correct or propose blanket answer replacement.

**Next / falsifier:** Compare raw selectivity/cardinality calculations and preserve explicit LIMIT/plan-shape assertions while defining the stable diagnostic contract. Wrong actual row results or a violated explicit LIMIT assertion would falsify the diagnostic-only interpretation. Evidence: node 47 full feedback/three diffs and pinned Actions source/answers. Recent local reports at `cbrd-27089/ci_analysis_report_512b361_codex.md` and `cbrd-26950/ci_analysis_report_a37b5b1_codex.md` describe similar signatures, but are not substituted for current-run evidence.

### E. Incomplete CDC historical extraction (2 tests)

**Observed:** CircleCI node 38 XML shows `cbrd_27064` INSERT coverage passing, DELETE extraction failing at 0/700 and first UPDATE round at 0/2400, both with `rc=-10`. Node 24 XML shows `cbrd_27075` completing 2000 updates at each of 4K/8K/16K, but with EXTRACT_ERR=3/3/3 and CONFIGS_OK=0. Both tests report zero detected payload corruption; this does not excuse missing history.

The collector's normalized CDC messages contain only `Test failed` and empty diffs. Their full node XMLs supply the diagnostics above. Actions independently observes DELETE 8/700 and UPDATE 0/2400 for 27064; 27075 extraction-error counts are 2/4/2, with all 2000 updates completed. Counts differ with timing; both runs demonstrate incomplete extraction.

**Inferred, medium confidence for precise cause:** These are consistent with the known mismatch between historical CDC images and OOS value-chain lifetime. Exact `log_manager.c:13141` materializes undo images through `heap_attrinfo_read_dbvalues`, which can resolve OOS references. A historical image can outlive the physical chain it references. The accepted durable supplemental-image design addresses this dependency; identity checking alone does not preserve historical payloads.

However, this snapshot does not contain a current crash stack proving a particular assertion or an internal explanation of every rc=-10. Do not copy the old oos_check_head_header crash attribution onto this run. The authoritative OOS context (updated 2026-09-09) and its ADR-0004 provide the required behavior; the local JIRA draft `CBRD-26939-oos-cdc-vacuum-lifetime_725a32c_codex.md` provides historical diagnosis, not current ticket status.

**Highest-priority next action / falsifier:** Capture server-side CDC extraction-return diagnostics for the focused 27064 DELETE case and establish which OOS reference/read fails. Check the current durable supplemental-image implementation and verification before choosing a repair. An unrelated protocol/connection failure with valid historical values would falsify the lifetime attribution. Do not relax extraction counts or classify these as harmless flaky tests.

## Other Failed Check

[Check TC PRs run 34851470827](https://github.com/CUBRID/cubrid/actions/runs/34851470827) explicitly reports open testcase PRs [3159](https://github.com/CUBRID/cubrid-testcases/pull/3159) and [3782](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/3782), then exits 1. Metadata links this attempt to PR6864 and the tested head. This is an intended merge gate, separate from runtime failures; opening a tracking draft does not automatically satisfy it. No PR was closed, merged or commented on during this analysis.

## Recommended Actions

1. Treat the two CDC failures as unresolved functional stability work; obtain the precise current extraction error before claiming the historical fix applies unchanged.
2. Repair independently justified numeric/parameter expectations for four error-number cases and the one parameter-list case, then replay them without weakening assertions.
3. Update TDE coverage for the split index-sort path; investigate the optimizer estimate contract before revising its expected diagnostics.
4. Handle testcase merge gates as part of planned integration. Only a fresh exact-engine/exact-testcase run can establish the effects of any future repairs.

## Evidence and Limitations

All nine CircleCI failure records were inspected, including metadata/messages/diffs, seven shell node XMLs, targeted feedback, all suite summaries and source/log/artifact indices. Counts reconcile to A4+B1+C1+D1+E2=9. There are no abnormal error/unknown test records needing another inventory.

SQL sources are exact for CircleCI. Shell sources are exact for the verified Actions run; CircleCI shell revision remains unknown after checkout output HTTP404. Similar output is not proof of identical source bytes. Testcase environment variables were unset; the existing private testcase repository was found locally and read by immutable Git object, with clean working-tree status.

Actions failed SQL names and counts come from its collect/shard logs; the detailed SQL cause here is established from CircleCI's immutable diffs and matching SQL revision. Actions runtime artifacts are hosted by the CI system, not GitHub's artifacts endpoint (which returned an empty list); seven shell XMLs were fetched from the run's documented artifact location. Their build/testcase identity files were verified individually. API supplemental files are separate from collector-schema output.

The exact source objects and source deltas are preserved with hashes in supplemental `provenance.json`. Historical source, local replays performed in other tasks, and older reports are explicitly supporting context, not new experiments performed here. No engine/testcase changes, local runtime replay, CI trigger, PR/JIRA update, commit or push was performed. Report is saved uncommitted for review.
