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
