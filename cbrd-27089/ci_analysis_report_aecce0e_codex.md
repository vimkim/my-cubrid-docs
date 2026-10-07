> Status updated 2026-10-07: Exact remote-head CI evidence for aecce0e; these results do not verify later local commits.
> Current entry point: [CBRD-27089](README.md). Historical evidence below is preserved.

# PR #7927 CI failure attribution — aecce0e12

## Decision

**One failure is directly related to this PR's intentional loader behavior change; two CDC failure categories already occur on the exact merge base; three medium failures are unordered-output differences whose relationship to the PR remains unknown.** This snapshot establishes no new value-loss, incorrect sorted result or OOS-owner defect in the six failed cases. It also does not establish that the PR preserves existing unordered output or that all six failures can be waived.

The three medium cases pass in the baseline run and fail at HEAD, but the CTP runner revisions differ. Treat them as an observed differential requiring a controlled comparison, not as proven engine regressions or automatically harmless test flakes. The partition loader now rejects an invalid direct-child value that the baseline accepted. That is a concrete PR effect even though the fixture contains only an integer column and does not activate OOS.

## Pinned identity and validated evidence

| Item | Identity |
|---|---|
| PR | [#7927 — CBRD-27089](https://github.com/CUBRID/cubrid/pull/7927), `feat/oos-deferred-write` → `feature/oos-merge`, draft/open at snapshot |
| HEAD | `aecce0e1216a813771621c13112c8f27d43df22e` — exactly the user's source-worktree HEAD |
| Target tip and unique merge base | `fb567a629cdb390fff920542173fa36f454c74a0` |
| Head run / attempt | [37463919574 / 1](https://github.com/CUBRID/cubrid/actions/runs/37463919574) |
| Baseline run / attempt | [36570256001 / 1](https://github.com/CUBRID/cubrid/actions/runs/36570256001) |
| Snapshot time | 2026-10-06 17:00:43 UTC; 2026-10-07 02:00:43 KST |
| Head collection time | 2026-10-06 17:01:16.870823232 UTC |
| Baseline relationship observed | 2026-10-06 17:01:40.388897416 UTC |
| Baseline collection time | 2026-10-06 17:02:42.228340010 UTC |
| Collector | `cubrid-ci 0.2.0 (16d7252122d1, release)`; local schema checkout is the same full revision |
| Head observation | `20261006T170105.975956105Z-613061-0` |
| Baseline observation | `20261006T170232.572466949Z-614743-0` |

One status snapshot, one exact-head collection and one exact-merge-base collection were taken. Both collectors exited 0 with complete terminal observations. Independent schema, identity, path, summary-digest, raw-size/digest, metadata and count checks validated all three suites on both sides and **780 raw files per bundle**. The analyzer's executable gate returned `mode=full`, `comparison_scope=validated_cases_only`. Binary collection was not requested and consumed zero binary-budget bytes. [Validation](review-aecce0e/evidence/ci-validation.json), [report-mode result](review-aecce0e/evidence/report-mode.json), [snapshot](review-aecce0e/evidence/snapshot.json).

The baseline suites consumed an exact-base debug build produced by **36570061594 / 1**, distinct from suite run 36570256001. Per-shard build provenance proves the consumed Engine SHA. A workflow's own `head_sha` or title is not the tested Engine identity. Head shards consumed build **37463919574 / 1**. [Run and source provenance](review-aecce0e/evidence/source-and-run-provenance.json).

Durable collector roots:

- Head: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/aecce0e1216a813771621c13112c8f27d43df22e`.
- Base: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/fb567a629cdb390fff920542173fa36f454c74a0`.

## Suite verdicts and counts

All suites are `completed`, not incomplete acquisitions or job-level failures. The debug and release build checks also passed at HEAD.

| Suite | HEAD verdict | HEAD passed / failed / errors / skipped | Base verdict | Base passed / failed / errors / skipped |
|---|---|---|---|---|
| `test_medium` | FAIL | 972 / 3 / 0 / 0 | PASS | 975 / 0 / 0 / 0 |
| `test_sql` | PASS | 17,471 / 0 / 0 / 0 | PASS | 17,471 / 0 / 0 / 0 |
| `test_shell` | FAIL | 3,256 / 3 / 0 / 30 | FAIL | 3,254 / 5 / 0 / 30 |

Both medium executions planned and ran 975 cases; both SQL executions planned and ran 17,471. Both shell executions planned 3,289, ran 3,259 and skipped 30, with zero unrun cases. The `tests` totals include skips. Head totals reconcile to 21,735 tests = 21,699 passed + 6 failed + 0 errors + 30 skipped.

## Every failed case

These are full suite-relative paths, not basename matches. `also_observed_on_base` below means the same testcase's failure predicate/signature category was observed; it does not assert equal numeric counters or prove an identical low-level cause. The confidence column distinguishes observations from inferred mechanism.

| Suite and exact testcase | Observed signature | Baseline classification | Category | PR relation / confidence |
|---|---|---|---|---|
| `test_medium`: `medium/_02_xtests/cases/to_char_order_by.sql` | Four unordered `SELECT to_char(f) FROM foo` outputs reorder identical numeric/date/time/timestamp values; ordered statements are not in the extracted differences. | `uncomparable`: baseline case passes, but CTP input changes are unverified. | Unordered presentation differential | `unknown`; high confidence in order-only observation, low confidence in cause |
| `test_medium`: `medium/_02_xtests/cases/to_number_order_by.sql` | First unordered result changes `3,5,1,2,4` to `4,1,2,3,5`; same values. | `uncomparable`: baseline case passes, CTP differs. | Unordered presentation differential | `unknown`; high observation / low causal confidence |
| `test_medium`: `medium/_02_xtests/cases/to_timestamp_order_by.sql` | Unordered result swaps the February 2 and February 3 timestamp positions; values are unchanged. | `uncomparable`: baseline case passes, CTP differs. | Unordered presentation differential | `unknown`; high observation / low causal confidence |
| `test_shell`: `shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh` | Test2 reports `Line 6:Appropriate partition does not exist.` and `Total 0 object(s) inserted, 1 object(s) failed.` where the answer accepts two rows in child p0. The separate test2 count/check result is OK. | `additional_on_head`: base case passes; exact fixture/answer revision is equal and changed source directly explains rejection. | Intended partition-domain validation / legacy expectation conflict | `direct`; high confidence in relation, no claim that every output-count detail is established correct |
| `test_shell`: `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | Subcases 2 and 3 NOK; extractor exits 1 before reaching DELETE/UPDATE target counts, without reported log-corruption lines. | `also_observed_on_base`: same two subcases and premature-extraction signature category. | Existing CDC/OOS-history gap | `unlikely` to be newly caused by deferred writes; high pre-existence / medium mechanism confidence |
| `test_shell`: `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | CDC extraction errors at 4K/8K; 16K meets this run's success predicate. `CONFIGS_OK=1`, expected 3; `TOTAL_CORRUPTION=0`. | `also_observed_on_base`: extraction-error/configuration-failure signature; base also has errors at 16K. | Existing CDC/OOS-history gap | `unlikely` to be newly caused by deferred writes; high pre-existence / medium mechanism confidence |

Classification totals: **6 head failures = 2 shared + 1 additional + 3 uncomparable**. Four cases are absent from the baseline failure list, but only the loader case has an evidence-supported direct source relation. [Machine-readable classification](review-aecce0e/evidence/failure-comparison.json).

Exact testcase outcomes were also checked directly in each validated shard's JUnit: all four differentials are baseline **passes**, not skipped/unrun cases; all three base-only cases are HEAD passes. [Per-case JUnit comparison](review-aecce0e/evidence/junit-case-comparison.json).

## A. Medium ordering differences

**Observed evidence.** All three testcase sources were read from public testcase revision `bdba62aee0faec05abdd861518824c69b6c1b3c5`, the exact revision used by both runs. The failing queries have no `ORDER BY`, even though the filenames contain `order_by`. Each fixture also executes ascending and descending `ORDER BY 1` statements. The normalized differences identify only the unordered results; the complete cases fail rather than proving each statement separately passed.

The head diffs are retained individually: [to_char](review-aecce0e/evidence/head-medium_02_xtests_cases_to_char_order_by_sql-81a7176eb9-diff.txt), [to_number](review-aecce0e/evidence/head-medium_02_xtests_cases_to_number_order_by_sql-2914e2cc1a-diff.txt), [to_timestamp](review-aecce0e/evidence/head-medium_02_xtests_cases_to_timestamp_order_by_sql-f88d9035bb-diff.txt).

**Inference.** This is a presentation/order compatibility difference, not evidence that conversions changed values. The fixtures hold five small inline values: no selected OOS payload is needed. That narrows the hypothesis but does not remove all PR involvement: ordinary INSERT also now passes through [heap_attrinfo_prepare_record](https://github.com/CUBRID/cubrid/blob/aecce0e1216a813771621c13112c8f27d43df22e/src/storage/heap_file.c#L13251) and [locator_attribute_info_force](https://github.com/CUBRID/cubrid/blob/aecce0e1216a813771621c13112c8f27d43df22e/src/transaction/locator_sr.c#L7692). The non-OOS finalizer clears the pending type without publishing chains. No modified function in this diff establishes a new SQL ordering contract.

**Unknowns.** Heap/OID allocation, database starting state, query-plan details and the effect of the CTP change have not been isolated. The local testtools repository contains the head CTP object but lacks the baseline CTP object, so no exact tool-source equivalence was asserted. These runs cannot establish that the same unordered ordering will change deterministically when only the Engine is changed.

**Falsifier and next action.** A same-CTP, same-medium-archive, complete serial `_02_xtests` comparison on the exact base and HEAD that repeatedly preserves base ordering but changes HEAD ordering would establish an Engine-dependent effect. Conversely, order variation on repeated baseline runs, or restoration by changing only CTP, would falsify the simple engine-only explanation. A changed value multiset or an explicitly ordered result difference would falsify the narrow presentation-only finding. Preserve original results and ordering expectations until that comparison resolves the cause; an unordered query is not by itself permission to rewrite its answer.

## B. Partition loader validation

**Observed evidence.** The exact private source creates `t(i int)` with only `PARTITION p0 VALUES LESS THAN (10)`, inserts `1`, unloads, and appends `100` to the generated objects file before server loaddb. The Linux answer expects `dba.t__p__p0 2 instances committed` and `Total 2 object(s) inserted, 0 object(s) failed.` in that second load. Thus it expects a value outside the named child's domain to be accepted. HEAD emits the explicit domain error; baseline passes this same answer. [Head diff](review-aecce0e/evidence/head-shell_35_cherry_issue_21654_server_side_loaddb_partition_tbls_cases_partition_tb-9e01a2a475-diff.txt).

**Direct source relation.** [server_object_loader::start_attrinfo](https://github.com/CUBRID/cubrid/blob/aecce0e1216a813771621c13112c8f27d43df22e/src/loaddb/load_server_loader.cpp#L1204) now distinguishes root from direct-child input. [flush_records](https://github.com/CUBRID/cubrid/blob/aecce0e1216a813771621c13112c8f27d43df22e/src/loaddb/load_server_loader.cpp#L775) sends partitioned rows through `locator_insert_force` with that pruning type instead of the unpartitioned bulk path. The unchanged existing partition evaluator therefore verifies the child's domain. The current PR body explicitly calls out rejection of formerly accepted wrong-child inputs and the need to correct that expectation.

**Inference.** The failure is an intentional compatibility correction needed by the destination-routing implementation, not evidence of malformed OOS stubs or wrong OOS ownership. Its direct relation does not depend on proving identical CTP versions: the source change, exact invalid input, explicit runtime error and PR description agree.

**Unknowns.** The sorted text comparison aggregates loaddb progress output, so it does not by itself fully establish retained-row counts for every worker/batch rollback choice in test2. The follow-up successful 10,000-row test makes the test2 failure primarily visible through loader output, not a dedicated invariant check of the invalid load's final table.

**Falsifier and next action.** If the original `100` belongs to a different valid destination in an extended schema yet root input still rejects it, or a valid `<10` direct-child row is rejected, the current intentional-child-validation explanation would be insufficient. A focused follow-up should check the actual generated `%class`, invalid-child rejection, rollback/retained counts, valid root routing and valid direct-child loading. Then update the legacy answer around those established invariants; do not merely remove the error line. No answer or source was changed in this analysis.

## C. CDC failures already visible on the base

**Observed evidence.** Both CDC testcase sources use private revision `c4b9d482fbd491a68510b2552df2c3cac91911fc` on both sides. For `cbrd_27064`, HEAD's DELETE and UPDATE targets stop at **37/700** and **1/2400**, with extractor exit 1 and corruption count 0. Base stops at **23/700** and **0/2400**, also exit 1 and corruption count 0. The failing predicates match; numeric counts do not. [Head excerpt](review-aecce0e/evidence/head-shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118-excerpt.txt), [base excerpt](review-aecce0e/evidence/baseline-shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118-excerpt.txt).

For `cbrd_27075`, HEAD reports extraction errors **2/1/0** at **4K/8K/16K**, hence `CONFIGS_OK=1/3`; base reports **4/4/4**, hence `CONFIGS_OK=0/3`. Both reach final sequence 2000 and report total corruption 0. This snapshot does not show log-corruption messages and must not be retold as a newly observed corruption/crash failure. [Head excerpt](review-aecce0e/evidence/head-shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27075_cases_cbrd_27075_sh-f42063033e-excerpt.txt), [base excerpt](review-aecce0e/evidence/baseline-shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27075_cases_cbrd_27075_sh-f42063033e-excerpt.txt).

**Inference.** The existing OOS-history lifetime gap is a stronger explanation than newly deferred chain creation. [Accepted ADR-0005](/home/vimkim/gh/cubrid-oos-context/docs/adr/0005-defer-oos-history-from-the-11-5-merge.md) explicitly defers CDC/flashback historical images and keeps these two cases enabled and visibly failing. The normative context was last updated 2026-09-22; its accepted scope decision is design authority, while these two exact runs establish current failure evidence. PR #7927 does not add the deferred historical-image implementation.

**Unknowns.** Generic extraction error counts and incomplete target counts do not identify the precise failure instruction, reclamation event or returned low-level error for every attempt. Matching categories on base do not prove the PR has zero impact on timing, counts or failure severity; differing CTP versions also prevent attributing the apparently improved 16K outcome to this PR.

**Falsifier and next action.** A controlled exact-base/HEAD comparison showing a new extraction error/stack only at HEAD after finalization would falsify an exclusively pre-existing explanation and warrant tracing the changed publication path. For the existing gap, preserve each extractor's full error/LSA evidence and investigate under the separate CBRD-26939 history work. Keep these tests visible; do not mask them to make this PR green.

## Baseline inputs, coverage and separate base-only observations

| Input | HEAD | Exact merge-base run | Comparison implication |
|---|---|---|---|
| Public testcase SHA | `bdba62aee0faec05abdd861518824c69b6c1b3c5` | Same | Exact tracked testcase, answer, fixture and helper objects in this repository are equal. |
| Private testcase SHA | `c4b9d482fbd491a68510b2552df2c3cac91911fc` | Same | Exact private testcase repository objects are equal. |
| CTP branch/SHA | `develop` / `44e3f97c788ad82091d5b66d728852f3279b1e86` | `develop` / `4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb` | Different external runner/helper source; no affected-tool-file equality proof. |
| Build mode | debug for every shard | debug for every shard | Release-build passing checks are separate from these debug suite verdicts. |
| Suite configuration labels in collect evidence | medium `conf/medium_dev.conf`; SQL `conf/sql.conf`; shell `conf/shell_ci.conf` | Same labels | Equal filenames do not prove byte-identical configuration when CTP differs. |
| Runner/image/runtime state | Runs are separated by one week | Historical run | Image digest, medium archive bytes, initial databases and host timing were not proven identical here. |

Exact-head and merge-base identities are validated independently. Baseline discovery covers all paginated exact-commit statuses and check links, not every repository workflow run. The CLI selected the available exact-base execution; an absent newer run is not proof that no other run ever occurred. The copied per-observation validation pins the bundle used here even if a collector root manifest is updated later.

During final verification another collection replaced the baseline root manifest at 17:19:16 UTC. Its suite selections remained the same; only discovery selection and collection time changed. This report retains the originally validated PR #7927 relationship from this invocation's saved result and exact matching immutable observation, and revalidates the retained manifest snapshot and all raw evidence. [Snapshot provenance](review-aecce0e/evidence/manifest-snapshot-origin.txt). No acquisition command was repeated.

Three baseline shell failures are absent from HEAD's complete failure list:

- `shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases/hide_cubrid_replay.sh`.
- `shell/_06_issues/_15_1h/bug_bts_15156/cases/bug_bts_15156.sh`.
- `shell/_40_guava/cbrd_26349/cases/cbrd_26349.sh`.

These are **three base-only observed cases**, recorded separately from the six head failures. They are not demonstrated fixes by PR #7927 because CTP/runtime differences remain. Head failure count 6 versus baseline count 5 is therefore not a causal regression metric.

## Prioritized follow-up and review material

1. Resolve medium ordering with a controlled complete-directory replay using the same runner/archive/config inputs and exact engines. This is the principal unresolved PR-relation question; no ordering answer was changed or waived.
2. Reconcile the partition-loader answer with the explicitly intended child-validation behavior, adding checks for valid routing and rollback counts when doing that separate testcase work.
3. Carry the two CDC failures as the existing deferred history gap, with complete extractor errors/LSAs for the separate investigation. They remain red CI evidence.

The [code review guide](review-aecce0e/code_review_guide.md) explains every changed function/type definition individually, including tests and inline/deleted methods, and indexes declaration/build wiring. Its machine-checked coverage is **87 functions, 9 types, 6 cleanup lambdas**, plus macros and newly exposed existing counter declarations. No independent Standards/Spec review verdict or new runtime acceptance is implied by this guide.

## Evidence inventory and handoff boundary

[Validation program](review-aecce0e/evidence/validate_ci.py), [validated inventory](review-aecce0e/evidence/ci-validation.json), [source/run provenance](review-aecce0e/evidence/source-and-run-provenance.json), [six-case classification](review-aecce0e/evidence/failure-comparison.json), [full guide coverage](review-aecce0e/evidence/guide-coverage.json) and [hunk audit](review-aecce0e/evidence/hunk-coverage.json) are retained with the report. Every head failure appears exactly once in the classification table; all requested suites appear once, count arithmetic reconciles, and the source of all 11 head/base failure records was read at its recorded Git revision. Curated differences/excerpts support the observations; original messages, JUnit, source references and raw indexes remain in the collector roots.

This task collected and analyzed existing CI and wrote documentation. It did not trigger another CI run, publish GitHub/JIRA comments, edit Engine/testcase sources, change answers or run a local regression reproduction. Existing source-worktree submodule changes and `repro.sh` were preserved. Reports are prepared on a separate local documentation branch for review.
