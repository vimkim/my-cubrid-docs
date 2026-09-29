# PR #7927 CI evidence warning — `34a9072a`

## Decision boundary

**This snapshot does not support a regression or root-cause conclusion.** It cannot safely determine whether the shell failures in gha-ci run [35857219636](https://github.com/CUBRID/cubrid/actions/runs/35857219636) are caused by CBRD-27089, the testcase branch, or unrelated/flaky behavior.

The PR and exact commit identity are established. The collector returned a schema-v2 command result and manifest, but the installed collector predates the append-only observation format required by the current analyzer. It created no matching `observations/<id>/request.json` and `result.json`. In addition, all three raw indexes lack the current required `summary_sha256` binding. The analyzer safety gate therefore selected `warning` with `regression_conclusions_allowed=false`.

The raw records do show four shell failures, none of whose testcase paths is the CBRD-27089 testcase. That fact alone is not enough to classify causality: an engine change can break older tests, and the missing observation/integrity binding prevents treating this bundle as validated evidence.

## Identity

| Field | Value |
|---|---|
| Repository | `CUBRID/cubrid` |
| PR | [#7927](https://github.com/CUBRID/cubrid/pull/7927) |
| Title | `[CBRD-27089] Defer OOS writes until destination heap selection` |
| Exact head | `34a9072a19fdd5baf420273992c136119e719503` |
| Status snapshot | `2026-09-25T05:36:13Z` |
| Collection result | `2026-09-25T05:36:21.111549505Z`, exit `0` |
| Collector | `cubrid-ci 0.2.0 (31bd609fda78, release)` |
| Evidence directory | `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503` |

The status snapshot, command result, and manifest all name the same PR and 40-character head SHA.

## Raw suite states

The following values are reported by the bundle but are not accepted as validated suite evidence because the observation is absent and the raw indexes fail the current schema.

| Suite | Run / attempt | Raw verdict | Raw counts | Testcase revision |
|---|---:|---|---|---|
| `test_medium` | `35857219636 / 1` | pass | 444 passed; 0 failed; 444 total | public `7fb227854a00daca5a3ccd3a74160de4b7e1254a` |
| `test_shell` | `35857219636 / 1` | fail | 1 passed; 4 failed; 5 total | private `018fc45bb12a63d24f4d85315790437cbf7cdaae` |
| `test_sql` | `35857219636 / 1` | pass | 1,866 passed; 0 failed; 1,866 total | public `7fb227854a00daca5a3ccd3a74160de4b7e1254a` |

The live status snapshot also reports both builds, medium, SQL, code style, cppcheck, license, memory-monitor, and PR-style as successful for the exact head. Shell is the only current failing gha-ci context.

## Raw shell records

These are observations from unvalidated raw files, not causal classifications.

| Testcase | Recorded signature | Classification |
|---|---|---|
| `shell/_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh` | server `call_stack_dump_activation_list` output differs in cases 2 and 3 | PR relation `unknown`; confidence unavailable |
| `shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh` | server `call_stack_dump_activation_list` output differs in case 1 | PR relation `unknown`; confidence unavailable |
| `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | CDC delete/update extraction reports `rc=-10`, zero target records | PR relation `unknown`; confidence unavailable |
| `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | CDC extraction errors occur at all three tested page sizes; corruption count remains zero | PR relation `unknown`; confidence unavailable |

The raw rerun planned five shell cases and recorded one pass plus these four failures. It does not expose a validated comparison run or repeat history sufficient to label any case flaky.

## Validation and acquisition ledger

| Check | Outcome |
|---|---|
| PR/commit identity | established |
| Command result schema | valid |
| Manifest schema | valid |
| Three suite-summary schemas | individually valid |
| Four shell failure-metadata schemas | individually valid; declared message/diff files exist |
| Matching terminal observation | missing; no `observations/` directory exists |
| Command-result/observation equality | not established |
| Requested-suite reconciliation against observation | not established |
| Raw-index schemas | invalid; each lacks required `summary_sha256` |
| Acquisition ledger | unavailable because the observation is missing |
| Binary evidence | not requested |
| Analyzer report mode | `warning`; regression conclusions prohibited |

No suite or shard can be labeled `retained`, `failed`, or `not_attempted` at acquisition level without the required observation ledger. The manifest reports all three suites as completed, but that is not a substitute for invocation-level acquisition proof.

## Unknowns

- Whether the collected raw responses are integrity-bound to the summaries and this exact collector invocation.
- Whether any of the four shell failures is reproducible on the exact engine/testcase pair.
- Whether each failure is introduced by the engine PR, by testcase-branch state, or is a pre-existing/flaky failure.
- Whether a validated baseline run at the same testcase revisions produces the same signatures.

## Required next action

Install a `cubrid-ci` build containing the observation/integrity hardening at local commit `4594401` or newer, then take one fresh status snapshot and collect this same exact head again. The new bundle must contain a unique matching terminal observation and schema-valid raw indexes before the failures can be assigned to CBRD-27089, the testcase branch, or unrelated/flaky behavior.

This action only recollects existing CI evidence; it does not rerun CI.


## 2026-09-30 KST snapshot: run 36102128913

**Warning: this collection is unvalidated. No regression or root-cause conclusion is supported.**

This update supersedes the earlier snapshot for current-run inventory only. The earlier report is retained above. The user requested all-failure attribution and preservation of existing SELECT scan order; those causal/design conclusions remain unfinished.

Exact commit: `34a9072a19fdd5baf420273992c136119e719503`. Collected at `2026-09-29T23:12:39.146191807Z` using `cubrid-ci 0.2.0 (31bd609fda78, release)`. Collection exit 0; analyzer gate returned `warning` and `regression_conclusions_allowed=false`.

[Requested trigger](https://github.com/CUBRID/cubrid/pull/7927#issuecomment-5827803591); [selected run](https://github.com/CUBRID/cubrid/actions/runs/36102128913), attempt 1. Public HTML shows the September 25 `/run all` comment; exact comment-to-run linkage was not independently established by a collection observation.

| Suite | Reported state/verdict | Planned | Run | Passed | Failures | Errors | Skipped |
|---|---|---:|---:|---:|---:|---:|---:|
| test_medium | completed / fail | 975 | 975 | 972 | 3 | 0 | 0 |
| test_shell | completed / fail | 3286 | 3256 | 3246 | 10 | 0 | 30 |
| test_sql | completed / fail | 17466 | 17466 | 17465 | 1 | 0 | 0 |

### Raw failure signatures — not causal classifications

**The raw inventory contains more than row-permutation signatures:** error-code, utility usage, log-header, parameter-output and CDC extraction differences are recorded. This observation does not establish which changes introduced them.

| Testcase | Recorded signature | Evidence |
|---|---|---|
| `medium/_02_xtests/cases/to_char_order_by.sql` | Recorded unordered SELECT row permutation differs. | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503/providers/github-actions/runs/36102128913/attempts/1/test_medium/failures/medium_02_xtests_cases_to_char_order_by_sql-81a7176eb9/message.txt) |
| `medium/_02_xtests/cases/to_number_order_by.sql` | Recorded unordered SELECT row permutation differs. | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503/providers/github-actions/runs/36102128913/attempts/1/test_medium/failures/medium_02_xtests_cases_to_number_order_by_sql-2914e2cc1a/message.txt) |
| `medium/_02_xtests/cases/to_timestamp_order_by.sql` | Recorded unordered SELECT row permutation differs. | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503/providers/github-actions/runs/36102128913/attempts/1/test_medium/failures/medium_02_xtests_cases_to_timestamp_order_by_sql-f88d9035bb/message.txt) |
| `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | CDC extraction errors at 4K/8K/16K; CONFIGS_OK=0; corruption=0. | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503/providers/github-actions/runs/36102128913/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27075_cases_cbrd_27075_sh-f42063033e/message.txt) |
| `shell/_06_issues/_15_1h/bug_bts_15912/cases/bug_bts_15912.sh` | Extra `upgradedb` entry in actual utility usage. | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503/providers/github-actions/runs/36102128913/attempts/1/test_shell/failures/shell_06_issues_15_1h_bug_bts_15912_cases_bug_bts_15912_sh-807266212f/message.txt) |
| `shell/_32_features_930/issue_12504_show_log_header/_01_show_log_header/_02_relative_path/_01_csql/cases/_01_csql.sh` | Extra `System_metadata_version` field in actual log-header output. | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503/providers/github-actions/runs/36102128913/attempts/1/test_shell/failures/shell_32_features_930_issue_12504_show_log_header_01_show_log_header_02_relative-bd5f046f99/message.txt) |
| `shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh` | `call_stack_dump_activation_list` output mismatch. | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503/providers/github-actions/runs/36102128913/attempts/1/test_shell/failures/shell_06_issues_14_2h_bug_bts_14120_cases_bug_bts_14120_sh-2917c23aa5/message.txt) |
| `shell/_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh` | `call_stack_dump_activation_list` output mismatch. | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503/providers/github-actions/runs/36102128913/attempts/1/test_shell/failures/shell_06_issues_12_2h_bug_bts_9836_cases_bug_bts_9836_sh-74957cfea4/message.txt) |
| `shell/_32_features_930/issue_12504_show_log_header/_01_show_log_header/_03_absolute_path/_01_self_log/cases/_01_self_log.sh` | Extra `System_metadata_version` field in actual log-header output. | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503/providers/github-actions/runs/36102128913/attempts/1/test_shell/failures/shell_32_features_930_issue_12504_show_log_header_01_show_log_header_03_absolute-b71bf934be/message.txt) |
| `shell/_06_issues/_25_1h/cbrd_25478/cases/cbrd_25478.sh` | Extra `System_metadata_version` field in actual log-header output. | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503/providers/github-actions/runs/36102128913/attempts/1/test_shell/failures/shell_06_issues_25_1h_cbrd_25478_cases_cbrd_25478_sh-b94dc3fbd6/message.txt) |
| `shell/_32_features_930/issue_12504_show_log_header/_01_show_log_header/_01_basic_log/cases/_01_basic_log.sh` | Extra `System_metadata_version` field in actual log-header output. | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503/providers/github-actions/runs/36102128913/attempts/1/test_shell/failures/shell_32_features_930_issue_12504_show_log_header_01_show_log_header_01_basic_lo-ae20658d46/message.txt) |
| `shell/_06_issues/_15_1h/bug_bts_16378/cases/bug_bts_16378.sh` | Extra `System_metadata_version` field in actual log-header output. | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503/providers/github-actions/runs/36102128913/attempts/1/test_shell/failures/shell_06_issues_15_1h_bug_bts_16378_cases_bug_bts_16378_sh-b38545cb8f/message.txt) |
| `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | CDC extraction `rc=-10`; delete 4/700, update 1/2400. | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503/providers/github-actions/runs/36102128913/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118/message.txt) |
| `sql/_33_elderberry/cbrd_23844/cbrd_24337/cases/cbrd_24337.sql` | `create table _db_class`: expected -494, actual -493. | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503/providers/github-actions/runs/36102128913/attempts/1/test_sql/failures/sql_33_elderberry_cbrd_23844_cbrd_24337_cases_cbrd_24337_sql-c0d5024efe/message.txt) |

### Validation and acquisition limitations

- Command result, manifest, three summaries, and all fourteen failure metadata objects individually pass their current schemas. Declared message/diff files exist beneath their suite directories. All count equations reconcile and summary run/attempt identities match the command result.
- No `observations/*/result.json` exists. There is no matching request/result pair, invocation acquisition ledger, or result-to-observation equality proof.
- All three raw indexes fail the current schema: `summary_sha256` is required but absent. Individually valid summaries do not establish a validated evidence bundle.
- All acquisition shard states remain unknown; absent observations cannot be reconstructed as retained/failed/not_attempted facts.
- Binaries were not requested. No binary-budget or binary-presence conclusion is made.
- Reported testcase revisions: public `7fb227854a00daca5a3ccd3a74160de4b7e1254a`; private `018fc45bb12a63d24f4d85315790437cbf7cdaae`. Both are reported as `tc/pr-7927`.
- Reported build SHA matches the head; build provenance names run `35836821909`, while the selected test execution is `36102128913`. Build reuse needs preservation in a validated provenance record.
- No exact-base paired reproduction was run. The user-reported two-CDC-only baseline is not independently verified in this snapshot.

### Required next work

1. Obtain a collector installation compatible with the current observation and raw-index schemas; perform a new explicitly scoped collection. Do not fabricate missing observations or hashes to make the old snapshot pass.
2. Validate the new terminal bundle and inspect exact testcase/answer revisions before assigning PR relations.
3. Establish a paired reproduction on the PR and exact base using identical testcase revisions and database setup. Preserve current unordered SELECT behavior as the acceptance requirement; do not add ORDER BY to dismiss the difference.
4. Review record serialization, MVCC sizing, insertion/relocation and heap page-selection differences only after the ordering symptom has a reproducible pass/fail loop. No specific engine fix is established here.

Evidence root: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503`. Invocation receipts and validator assessment: `/tmp/pr7927-ci-analysis/`. Engine/testcase worktrees were unchanged; existing `cubrid-cci`, `cubrid-jdbc`, and `repro.sh` changes were preserved.
