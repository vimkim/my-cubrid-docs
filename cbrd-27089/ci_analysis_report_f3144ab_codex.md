# PR #7927 terminal CI assessment — f3144ab

The published engine and revised partition testcase were tested together. The partition case **passes** in a validated, positive case-level JUnit record. CI remains **red** with three medium ordering failures and two CDC failures. The loader-diagnostic and index-capacity cases that failed in the previous run pass in this execution without changing their assertions. No further testcase correction or engine repair is justified by this assessment alone.

All five head failures are reconciled: **2 `also_observed_on_base`, 0 `additional_on_head`, 3 `uncomparable` for attribution**. The exact baseline has three separate `base_only` observations. The three ordering diffs recur byte for byte from the previous head, but the engine-only cause remains unknown. CDC failures remain enabled and visible; their pre-existing signatures and accepted history-scope decision do not waive CI requirements. Human code-review approval is also outstanding.

## Exact identities and terminal snapshot

| Identity | Value |
| --- | --- |
| PR | [CUBRID/cubrid #7927](https://github.com/CUBRID/cubrid/pull/7927), OPEN, non-draft; review decision empty at the final query |
| Head repository / branch | `vimkim/cubrid` / `feat/oos-deferred-write` |
| Tested engine | `f3144ab4b72fc2bf73f115c9da1cf193c756457a` |
| Engine tree | `2b8afa19ef2955320088e38f8989cd5b1c1e4765` |
| Public testcase, medium and SQL | `f5e610d91efdeaa9fcf089f47bf4a89c103a4a93`, `tc/pr-7927` |
| Private testcase, shell | `10f3500291c3d3f5c7bcf6ed5c90142a6ed0f532`, `tc/pr-7927` |
| Target branch / observed target tip | `feature/oos-merge` / `fb567a629cdb390fff920542173fa36f454c74a0` |
| Independently resolved exact merge-base | `fb567a629cdb390fff920542173fa36f454c74a0` |
| Head run / attempt | [37616249409 / 1](https://github.com/CUBRID/cubrid/actions/runs/37616249409/attempts/1), terminal failure; updated `2026-10-07T12:32:37Z` |
| Baseline run / attempt | [36570256001 / 1](https://github.com/CUBRID/cubrid/actions/runs/36570256001/attempts/1) |
| Baseline relationship observation | `2026-10-07T11:49:42.832542765Z`, matching this head and target |
| Head collection / observation | `2026-10-07T12:33:25.958302107Z` / `20261007T123317.944496887Z-1862088-0`, complete |
| Baseline collection / observation | `2026-10-07T11:50:39.237930591Z` / `20261007T115039.071413616Z-1862325-0`, complete |
| Collector and schema source | `cubrid-ci 0.2.0 (16d7252122d1, release)`; schema source `16d7252122d185dc8866c99598644dd974044bd2` |

| Suite | Collection state / CI verdict | Planned | Run | Passed | Failures | Errors | Skipped | Unrun |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `test_medium` | completed / FAILURE | 975 | 975 | 972 | 3 | 0 | 0 | 0 |
| `test_sql` | completed / SUCCESS | 17,471 | 17,471 | 17,471 | 0 | 0 | 0 | 0 |
| `test_shell` | completed / FAILURE | 3,289 | 3,259 | 3,257 | 2 | 0 | 30 | 0 |
| Total | all requested suites complete | 21,735 | 21,705 | 21,700 | 5 | 0 | 30 | 0 |

Debug and Release builds and all five static checks passed. The suite run used Debug builds for every shard; successful Release compilation does not establish a Release regression-suite result. All 61 test shard jobs completed: medium 0/1 successful, SQL 10/10 successful, shell 48/50 successful. Job counts and testcase counts are distinct. The 30 shell skips remain explicit and are not passes.

GitHub Actions reports workflow `head_sha=ea57708a785e34b35a91e10cd0694839a53a4fe5` for this issue-comment run. The tested engine identity is proven independently by all shard build receipts, not by that API field. [Run metadata](/home/vimkim/tmp/docs-main-integration-20261013-025904/original-worktree-files/docs--pr7927-ci-f3144ab/cbrd-27089/ci_analysis_evidence_f3144ab_codex/run-identity.json), [final PR metadata](/home/vimkim/tmp/docs-main-integration-20261013-025904/original-worktree-files/docs--pr7927-ci-f3144ab/cbrd-27089/ci_analysis_evidence_f3144ab_codex/final-pr.json), and [validation receipt](/home/vimkim/tmp/docs-main-integration-20261013-025904/original-worktree-files/docs--pr7927-ci-f3144ab/cbrd-27089/ci_analysis_evidence_f3144ab_codex/ci-validation.json) preserve the distinction.

## Evidence boundary and validation

This continuation explicitly took over tracker 242 and the existing collector from `codex-pr7927-publish-f3144ab`. It reused the single delegated status, single waiting head collection, and single exact-base collection. No acquisition was repeated to improve the snapshot. [Session receipt](/home/vimkim/tmp/docs-main-integration-20261013-025904/original-worktree-files/docs--pr7927-ci-f3144ab/cbrd-27089/ci_analysis_evidence_f3144ab_codex/session.json) records ownership and command identity; acquisition exited zero on both sides, which means complete evidence even though CI is red.

Both bundles independently pass command, manifest, observation request/result, suite-summary, raw-index and failure schemas. Request/result identities and options agree; each observation uniquely matches its saved result. All requested suites and retained shard ledgers reconcile. All **780 raw files per bundle**, their lengths/digests, summary digests, shard engine/testcase receipts and failure metadata/files validate. Head raw bytes total 27,826,832; baseline 27,872,236. No binary download was requested or performed. Head counts satisfy `tests = passed + failures + errors + skipped` and `planned = run + unrun + skipped`; every failure/error has one record.

The executable analyzer gate permits `full` output and comparison only for validated cases. The initial head-only gate permits no comparison; the subsequent gate accepts the independently validated exact baseline. Its permission is not causal evidence. [Gate inputs](/home/vimkim/tmp/docs-main-integration-20261013-025904/original-worktree-files/docs--pr7927-ci-f3144ab/cbrd-27089/ci_analysis_evidence_f3144ab_codex/assessment.json), [head gate](/home/vimkim/tmp/docs-main-integration-20261013-025904/original-worktree-files/docs--pr7927-ci-f3144ab/cbrd-27089/ci_analysis_evidence_f3144ab_codex/head-report-mode.json), and [comparison gate](/home/vimkim/tmp/docs-main-integration-20261013-025904/original-worktree-files/docs--pr7927-ci-f3144ab/cbrd-27089/ci_analysis_evidence_f3144ab_codex/report-mode.json).

Immutable selected manifest/observation snapshots and six suite summaries are retained in `ci_analysis_evidence_f3144ab_codex/`. Full raw evidence remains in the collector-owned roots returned by the commands:

- Head: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/f3144ab4b72fc2bf73f115c9da1cf193c756457a/`.
- Base: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/fb567a629cdb390fff920542173fa36f454c74a0/`.

The recorded discovery covers exact-commit status/check-linked executions selected by the collector. It does not prove that no other execution ever existed. This assessment uses the selected run/attempt and does not substitute older green results. No raw environment dumps, signed URLs, cores or credentials are copied into the report.

## Partition correction: positive case-level proof

The full case `shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh` appears exactly once in head shard **27**, duration **29.432 seconds**, with no failure, error or skipped node. Its JUnit file is digest-validated (`7fd6bfc35f68f5b9ccb54f7c82188d5eed919ea269c63564e6ce41c2b83efab7`); that shard's receipts prove engine `f3144ab…` and private testcase `10f350029…`. A floating `develop` URL in `classname` is not its revision identity. [Case verdict receipt and exact XML](/home/vimkim/tmp/docs-main-integration-20261013-025904/original-worktree-files/docs--pr7927-ci-f3144ab/cbrd-27089/ci_analysis_evidence_f3144ab_codex/partition-verdict.json).

The exact testcase source contains the expected checks: generated child-partition input; invalid direct-child rejection and zero-inserted/one-failed counts; root/child rollback; next valid load; root routing and valid direct-child insertion; wrong-child and out-of-domain rejection; preserved committed rows after both failed batches; recovery with another valid load; existing test1/test3 answer comparisons. The three-file partition-only change is independently identified in [testcase tree comparison](/home/vimkim/tmp/docs-main-integration-20261013-025904/original-worktree-files/docs--pr7927-ci-f3144ab/cbrd-27089/ci_analysis_evidence_f3144ab_codex/published-testcase-tree-comparison.json). The prior [testcase assessment](testcase-assessment/assessment.md) owns its contract justification and controlled native verification.

**Limit:** passing CI JUnit does not retain a per-assertion console body. This collection proves the case-level PASS and exact revised source identity; it does not independently report “28 OK” for CI. The 28-OK/zero-NOK result is the separate prior native receipt. Windows native execution remains unverified. The baseline's PASS used the old testcase and is not proof that it satisfies the revised child-domain contract.

## Complete head failure disposition

| Suite / full testcase path | Observed signature | Baseline classification | PR relation / confidence |
| --- | --- | --- | --- |
| `test_medium` / `medium/_02_xtests/cases/to_char_order_by.sql` | Four unordered conversion outputs reorder the same five values; numeric/date/time/timestamp presentation changes | `uncomparable`: baseline PASS; unmatched CTP/archive/config/runtime inputs prevent attribution | `unknown`; high observation, low causal confidence |
| `test_medium` / `medium/_02_xtests/cases/to_number_order_by.sql` | Unordered `3,5,1,2,4` becomes `4,1,2,3,5` | `uncomparable`: baseline PASS; same input limitations | `unknown`; high observation, low causal confidence |
| `test_medium` / `medium/_02_xtests/cases/to_timestamp_order_by.sql` | Unordered February 2/3 result positions swap, preserving values | `uncomparable`: baseline PASS; same input limitations | `unknown`; high observation, low causal confidence |
| `test_shell` / `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | DELETE and UPDATE extraction fail with `rc=-10`, extractor exit 1 and incomplete target counts; zero reported corruption | `also_observed_on_base`: same subcases/error category; counts/LSAs differ | `unlikely` for a newly introduced category; high observation, medium pre-existence inference; incremental PR influence unknown |
| `test_shell` / `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | Extraction errors at 4K and 16K; `FINAL_SEQ=2000`, zero reported corruption; only 1/3 configurations meets the unchanged predicate | `also_observed_on_base`: same extraction-error category at these configurations, variable counts | `unlikely` for a newly introduced category; high observation, medium pre-existence inference; incremental PR influence unknown |

[Full inventory, source coverage and diagnostic excerpts](/home/vimkim/tmp/docs-main-integration-20261013-025904/original-worktree-files/docs--pr7927-ci-f3144ab/cbrd-27089/ci_analysis_evidence_f3144ab_codex/failure-comparison.json) account for all five head and five baseline records. All diffs are available; no missing-diff inference is needed. Signatures classify observations, not harmlessness or identical causes.

### Ordering group

**Observed:** the three new diffs are byte-identical to engine `4be72fc…` run 37595050033 attempt 1. The failed queries have no `ORDER BY`; their source also includes explicitly ordered queries, which have no retained failure diff. Equal value multisets support a narrow presentation finding for the reported queries, not a proof about every output. Exact source/answer objects and the entire public repository tree match the baseline despite the initialization commit changing its SHA. Head/base/prior medium plan bytes are equal.

**Inference:** the observations recur across the extraction change and do not justify changing answers or removing ordering predicates. PR insert/finalization paths can affect inline rows, so small fixtures do not exclude engine involvement. The extraction did not remove the CI symptom. Causal confidence remains low; an engine-only regression is not established. [Exact engine-source object comparisons](/home/vimkim/tmp/docs-main-integration-20261013-025904/original-worktree-files/docs--pr7927-ci-f3144ab/cbrd-27089/ci_analysis_evidence_f3144ab_codex/engine-source-objects.json) identify changed loader/locator/heap files and unchanged parser/error-handler/session/B-tree/vacuum files; object equality alone does not establish causal exclusion.

**Unknown:** exact historical medium archive/helper/config bytes, starting database state, OID/page allocation, execution plans and timing are unmatched. Head uses CTP `44e3f97c788ad82091d5b66d728852f3279b1e86`; the baseline uses `4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb`. Both objects are absent from the inspected local CTP repository. The completed native assessment passed all 444 cases on original head/base and retained byte-equal ordering results, but used native testkit and different assets; it does not reproduce this historical CTP environment or establish the final engine's historical equivalence. Do not repeat those completed checks merely to reconstruct context.

**Falsifier and next action:** obtain the recorded medium archive/helper/config identities and compare starting database/OID state and query plans on exact `f3144ab…`/`fb567a6…` with matched inputs. A base order change or tool/state-only explanation falsifies an engine-only hypothesis. A changed value multiset or explicitly ordered mismatch falsifies the narrow presentation-only finding. Keep existing answers and tracker 242's ordering-preservation objective. A separate legacy CTP replay/comparison requires explicit user authorization; this assessment performs none.

### CDC group

**Observed:** `cbrd_27064` reports DELETE 0/700 and UPDATE 0/2400 with extractor exit 1/`rc=-10`; the base reports DELETE 23/700 and UPDATE 0/2400 with the same error category. INSERT passes on both. For `cbrd_27075`, head extraction-error counts are **3/0/1** at 4K/8K/16K; base is **4/4/4**. Both report final sequence 2000 and zero corruption counters. The previous head's counts were 1/0/1; the changed 4K count remains visible. Equal extracted NOK-label diffs do not imply equal underlying metrics or LSAs.

**Inference:** the recurring categories are consistent with the accepted deferred OOS-history scope; [ADR-0005](https://github.com/vimkim/cubrid-oos-context/blob/75f8b58674ac901d478ba60f9b2cc2fff11f66f6/docs/adr/0005-defer-oos-history-from-the-11-5-merge.md) explicitly keeps both cases enabled and visibly failing. This is design context, not runtime proof of every failure's cause. Their affected testcase directories are object-equal across base/head; the private repository's only changed files are the partition correction.

**Unknown:** differing runtime/tool inputs and variable extraction counts prevent excluding incremental PR influence or proving an identical root cause. Zero reported corruption is a measured counter, not a general corruption guarantee.

**Falsifier and next action:** a new head-only extractor stack/error tied to finalization under matched inputs would falsify an exclusively pre-existing explanation. Preserve extractor errors/LSAs and both enabled testcases for the separate history investigation. Their baseline failure is not a CI waiver.

## Previous observations that now pass

The [historical comparison receipt](/home/vimkim/tmp/docs-main-integration-20261013-025904/original-worktree-files/docs--pr7927-ci-f3144ab/cbrd-27089/ci_analysis_evidence_f3144ab_codex/historical-comparison.json) positively checks all eight prior failures against current JUnit; it does not infer outcomes from absence in the failure list.

| Previous failure | Current case-level result | Disposition |
| --- | --- | --- |
| Partition loader | PASS, shard 27 | Intended revised contract tested on the published engine; separate native justification retained |
| `shell/_06_issues/_25_2h/cbrd_26280/cases/cbrd_26280.sh` | PASS, shard 30 | Unchanged testcase/fixtures; retain all 18 diagnostic/count predicates. Historical missing syntax diagnostic is not causally explained |
| `shell/_06_issues/_15_1h/bug_bts_15489/cases/bug_bts_15489.sh` | PASS, shard 41 | Unchanged strict `0 < total_pages < 100` predicate. Passing JUnit lacks an exact page-count trace; historical 100-page observation remains unexplained |

No new head failure paths appear relative to the previous report. These passes do not prove a source repair, an intermittent mechanism, or that every historical assertion metric is now known. Passing-case console traces are absent. The previous controlled native passes remain distinct evidence and have not been rerun here.

**Falsifier / next action for the diagnostic and index observations:** a repeatable matched-input head-only diagnostic suppression or persistent index-capacity boundary miss would falsify an exclusive harness/timing explanation. Preserve the testcase predicates; if the symptoms recur, trace loader error callbacks or allocation/vacuum capacity over time before considering a repair. A single current PASS does not close those causal questions.

## Exact baseline and comparison limits

The baseline independently validates 975 medium passes, 17,471 SQL passes, and shell 3,254 passes/5 failures/30 skips; no errors or unrun cases. Its relation matches the pinned head and exact target/merge-base. Every relevant case has positive JUnit coverage on both sides. Twenty-two source reads cover 11 distinct cases at their recorded revisions; the case-directory/answer comparisons are equal except for the deliberately revised partition case. [Exact source identities](/home/vimkim/tmp/docs-main-integration-20261013-025904/original-worktree-files/docs--pr7927-ci-f3144ab/cbrd-27089/ci_analysis_evidence_f3144ab_codex/testcase-sources.json).

| Input | Head | Baseline | Limit |
| --- | --- | --- | --- |
| Public testcase | `f5e610d…` | `bdba62aee0faec05abdd861518824c69b6c1b3c5` | Entire trees equal; generated/external inputs not established |
| Private testcase | `10f350029…` | `c4b9d482fbd491a68510b2552df2c3cac91911fc` | Only the three partition-case files differ |
| CTP branch / SHA | `develop` / `44e3f97c788ad82091d5b66d728852f3279b1e86` | `develop` / `4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb` | Different objects; affected helper equivalence unknown |
| Test builds | Debug, 61 shards | Debug, 61 shards | Exact engine/build-producing-run receipts validate; runtime/config bytes unmatched |
| Configuration labels | `conf/medium_dev.conf`, `conf/sql.conf`, `conf/shell_ci.conf` | Same labels | Labels do not prove equal file contents or effective parameters |
| Medium/SQL plan | Equal head/base/prior bytes | Equal head/base/prior bytes | Allocation coverage only; no runtime equivalence claim |
| Shell plan | Different from base and prior | Different from head | Shard assignment/predecessors and timing differ |

Three **base-only observed signatures** are accounted for separately; current head JUnit says PASS for each:

| Full testcase path | Baseline signature | Head observation / relation |
| --- | --- | --- |
| `shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases/hide_cubrid_replay.sh` | Process-output answer difference around `qa9.answer` / `result.txt` | PASS shard 17; `unknown`, high observation/low cause |
| `shell/_06_issues/_15_1h/bug_bts_15156/cases/bug_bts_15156.sh` | Subcase1 shutdown-success predicate still 0 after retries | PASS shard 37; `unknown`, high observation/low cause |
| `shell/_40_guava/cbrd_26349/cases/cbrd_26349.sh` | Subcases2/3 remote-column diagnostic mismatch against authentication predicate | PASS shard 31; `unknown`, high observation/low cause |

**Inference/unknown:** these are execution differences, not demonstrated PR fixes. **Falsifier/next action:** reproduce matching signatures under matched head inputs to falsify a fix interpretation; retain separate process-sampling, service-lifecycle and DB-link diagnostic follow-ups. Their configuration/runtime equivalence is unverified. Never compute regression counts by subtracting aggregate failure totals.

## Decision and next action

1. The user requested a fresh-agent handoff for **local medium diagnosis**: run the complete serial `_02_xtests` directory on exact published head `f3144ab…` and exact base `fb567a6…` under matched native testkit inputs, retaining raw order, plans and allocation evidence. Establish whether the CI base-pass/head-fail split reproduces locally; preserve answers. Reconcile any local pass with the earlier native passes and historical CTP/archive/config gaps. A legacy CTP comparison or new CI execution still requires separate authorization.
2. Keep both CDC cases visible for the accepted separate history follow-up. Retain the variable counts and exact error category; no exclusion, answer rewrite or CI waiver.
3. Keep the partition correction as verified by its revised-source case-level PASS and prior independent contract/native evidence. Leave the diagnostic/index predicates intact; preserve their historical questions and the three base-only observations.
4. Obtain human code-review approval and a justified disposition of remaining failures before proposing PR integration. This report does not authorize a PR merge, source/testcase edits, a rerun, publication, comments or review-thread resolution.

The assessment itself is complete locally. Broader ordering/failure attribution remains open. Only documentation/evidence is changed. The original engine worktree remains at 4be72fc with its CCI/JDBC changes, and its diff/CCI-header hash/JDBC identity match the earlier preservation receipt. Both testcase worktrees, the extraction source and docs main remain clean and unchanged. [Workspace receipt](/home/vimkim/tmp/docs-main-integration-20261013-025904/original-worktree-files/docs--pr7927-ci-f3144ab/cbrd-27089/ci_analysis_evidence_f3144ab_codex/preserved-workspaces.json).

## Evidence files and local verification

The ticket [README](README.md) indexes every retained file. The evidence directory contains command/status/publication receipts; immutable manifests and observation pairs; six summary snapshots; schema/raw/provenance/count validation; initial/final gate decisions; positive case and partition verdicts; exact source/tree comparisons; prior-run comparison; bounded excerpts for all 10 head/base failure records; live PR/run metadata; preservation and final integrity/reconciliation receipts.

Verification is read-only except for local docs/evidence writes. The same validator was reused from the monitor and extended case comparison includes every prior failure and the partition case. Reproducible local checks use `/usr/bin/python3` because that interpreter has `jsonschema`:

```bash
/usr/bin/python3 cbrd-27089/ci_analysis_evidence_f3144ab_codex/validate_ci.py cbrd-27089/ci_analysis_evidence_f3144ab_codex
/usr/bin/python3 /home/vimkim/.agents/skills/cubrid-ci-analyze/scripts/report_mode.py cbrd-27089/ci_analysis_evidence_f3144ab_codex/assessment.json
/usr/bin/python3 cbrd-27089/ci_analysis_evidence_f3144ab_codex/compare_cases.py
/usr/bin/python3 cbrd-27089/ci_analysis_evidence_f3144ab_codex/retain_assessment.py
```

These scripts inspect retained artifacts/Git objects; they never trigger CI or run database tests. Python bytecode is already covered by the repository's tracked ignore rule. The docs assessment is retained on its topic branch under the supplied local-commit workflow; local integration into docs main still requires confirmation, and publication requires its own explicit request.
