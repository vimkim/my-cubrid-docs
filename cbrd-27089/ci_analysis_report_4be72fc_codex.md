# PR7927 CI analysis — 4be72fc20

**Decision boundary:** the complete exact-head inventory is validated. This run is red: eight testcase failures, no testcase errors, and no unrun cases. The exact merge-base inventory is also independently validated. Two CDC signatures were already observed there; the partition-loader failure has a direct source explanation. Five failures remain **uncomparable for attribution**, including two shell observations absent from the preceding head analysis. This evidence does not establish an engine regression, resolve the ordering-preservation question, or satisfy all CI requirements.

PR: [CUBRID/cubrid #7927](https://github.com/CUBRID/cubrid/pull/7927), `[CBRD-27089] Defer OOS writes until destination heap selection`.
Head repository/ref: `vimkim/cubrid`, `feat/oos-deferred-write`.
Target: `CUBRID/cubrid`, `feature/oos-merge`.
Exact Engine head: `4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c`.
Exact target tip and merge base: `fb567a629cdb390fff920542173fa36f454c74a0`.
Tracker: **242**. Agent: **codex**. Report publication and a PR summary comment were separately authorized on 2026-10-07. The report and evidence are prepared on `docs/pr7927-ci-4be72fc`; reviewer replies remain unpublished drafts.

## Terminal snapshot and reconciled suite counts

The requested [run 37595050033](https://github.com/CUBRID/cubrid/actions/runs/37595050033), attempt 1, finished before tracker 242 was resumed. Exactly one delegated status command, one head collection and one merge-base collection were then executed. Both collectors exited 0; a red testcase verdict is complete evidence, not a collector failure.

| Requested suite | Collection state | Head verdict | Tests | Passed | Failures | Errors | Skipped | Planned / run / unrun | Run / attempt |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| test_medium | completed | FAIL | 975 | 972 | 3 | 0 | 0 | 975 / 975 / 0 | [37595050033 / 1](https://github.com/CUBRID/cubrid/actions/runs/37595050033) |
| test_sql | completed | PASS | 17471 | 17471 | 0 | 0 | 0 | 17471 / 17471 / 0 | [37595050033 / 1](https://github.com/CUBRID/cubrid/actions/runs/37595050033) |
| test_shell | completed | FAIL | 3289 | 3254 | 5 | 0 | 30 | 3289 / 3259 / 0 | [37595050033 / 1](https://github.com/CUBRID/cubrid/actions/runs/37595050033) |

Head totals: **21,735 tests = 21,697 passed + 8 failed + 0 errors + 30 skipped**. Planned = 21,735; run = 21,705; unrun = 0. Both debug and release build contexts passed; all testcase shards consumed **debug** builds. SQL has no validated failures or errors, so no SQL root cause is invented. The 30 shell skips remain skips.

## Evidence identity and validation

| Evidence fact | Recorded value |
| --- | --- |
| Status snapshot | `2026-10-07T09:20:45+00:00` |
| Head collected at | `2026-10-07T09:21:04.724907371Z` |
| Head observation | `20261007T092054.465105654Z-715271-0`, outcome `complete` |
| Baseline relationship observed | `2026-10-07T09:21:55.967012619Z` |
| Baseline collected at | `2026-10-07T09:21:59.368880589Z` |
| Baseline observation | `20261007T092159.206482946Z-719391-0`, outcome `complete` |
| Collector | `cubrid-ci 0.2.0 (16d7252122d1, release)` |
| Matching schema source | `/home/vimkim/gh/cubrid-ci/schema` at `16d7252122d185dc8866c99598644dd974044bd2` |

Head command/manifest schema v2 and observation schema v1 validate independently of baseline command/manifest v3 and observation v2. Each result uniquely matches its immutable terminal observation, including collection time. Request identities, canonical suite sets, options, run/attempts, manifest/result equality, summary digests, raw lengths/digests, failure metadata/files, exact per-shard Engine/testcase receipts and count arithmetic all reconcile. The selected manifest snapshots and observation pairs are retained; a future change to a collector root manifest does not select new evidence for this report.

Both collections retain all **61 shards**: 1 medium, 10 SQL, 50 shell. Head integrity checks cover **780 raw files / 27,917,485 file bytes**; baseline checks cover **780 / 27,872,236**. These are validated file sizes, not network-consumption claims. There are no structured collector errors, incomplete suite summaries, interrupted observations or unvalidated head records. Binary collection was disabled; each observation consumed zero of its configured 536,870,912-byte binary budget. No core/binary absence or budget-exhaustion inference is made.

The initial report-mode gate allowed a full head inventory with no comparison. After independent baseline validation it returns `mode=full`, `comparison_scope=validated_cases_only`. This permits bounded comparisons; it is not proof of causality. See [validation](ci_analysis_evidence_4be72fc_terminal_codex/ci-validation.json), [assessment](ci_analysis_evidence_4be72fc_terminal_codex/assessment.json), and [gate](ci_analysis_evidence_4be72fc_terminal_codex/report-mode.json).

Collector-owned roots:

- Head: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c`.
- Baseline: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/fb567a629cdb390fff920542173fa36f454c74a0`.

## Complete head failure inventory

Each row is one failed testcase, not one shell subcase or one failed workflow job. Full paths and signature categories are compared, not basenames or aggregate counts. Shared categories do not imply byte-identical messages or the same low-level cause.

| Suite / exact testcase path | Result and observed signature | Baseline classification / exact case outcome | Category | PR relation / confidence |
| --- | --- | --- | --- | --- |
| test_medium: `medium/_02_xtests/cases/to_char_order_by.sql` | failure; four unordered conversion outputs reorder the same five values, including numeric/date/time/timestamp results | `uncomparable`; baseline PASS, differing CTP/config inputs unverified | Unordered presentation | `unknown`; high observation / low cause |
| test_medium: `medium/_02_xtests/cases/to_number_order_by.sql` | failure; unordered `3,5,1,2,4` becomes `4,1,2,3,5` | `uncomparable`; baseline PASS, differing CTP/config inputs unverified | Unordered presentation | `unknown`; high observation / low cause |
| test_medium: `medium/_02_xtests/cases/to_timestamp_order_by.sql` | failure; unordered February 2/3 positions swap, values retained | `uncomparable`; baseline PASS, differing CTP/config inputs unverified | Unordered presentation | `unknown`; high observation / low cause |
| test_shell: `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | failure; DELETE 30/700 and UPDATE 3/2400, extractor exits 1, reported corruption 0 | `also_observed_on_base`; same failing subcases and premature-extraction category, base 23/700 and 0/2400 | CDC/history extraction gap | `unlikely` to be newly introduced; high prior-signature / medium mechanism |
| test_shell: `shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh` | failure; test2 rejects invalid child value with `Appropriate partition does not exist`; 0 inserted / 1 failed instead of accepting 2 rows | `additional_on_head`; baseline PASS; equal exact fixture/answer and direct changed routing/validation path | Intended partition validation / legacy expectation conflict | `direct`; high |
| test_shell: `shell/_06_issues/_25_2h/cbrd_26280/cases/cbrd_26280.sh` | failure; test7 returns exit 3, emits missing-attribute diagnostic but omits `syntax error` at `NNUL`; failed-object count 1 instead of 2 | `uncomparable`; baseline PASS; exact testcase/fixture equal, CTP and worker timing unverified | Loader diagnostic/error-count difference | `plausible`; high observation / low cause |
| test_shell: `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | failure; 4K/8K/16K extraction errors 1/0/1; `CONFIGS_OK=1`, reported corruption 0 | `also_observed_on_base`; same extraction-error category, base errors 4/4/4 and `CONFIGS_OK=0` | CDC/history extraction gap | `unlikely` to be newly introduced; high prior-signature / medium mechanism |
| test_shell: `shell/_06_issues/_15_1h/bug_bts_15489/cases/bug_bts_15489.sh` | failure; 4K database, index reports `Num_total_page=100` after DELETE and 60-second wait; predicate requires `0 < pages < 100`; internal-error count 0 | `uncomparable`; baseline PASS, exact baseline page count unavailable; CTP/runtime and prior shard cases differ | Post-delete index-capacity threshold | `unknown`; high observation / low cause |

Classification reconciliation: **8 head failures = 2 shared signatures + 1 additional + 5 uncomparable**. There are **6 observed head-fail/base-pass cases**, but five lack sufficient input equivalence for causal classification. Baseline has 5 failures = 2 shared + 3 separate base-only observations. All 11 distinct cases are located exactly once on each side in validated JUnit, with real PASS/FAIL outcomes rather than absence from a failure list. [Classification and source object equality](ci_analysis_evidence_4be72fc_terminal_codex/failure-comparison.json), [case outcomes and provenance](ci_analysis_evidence_4be72fc_terminal_codex/case-comparison.json).

## Cause groups, hypotheses and falsifiers

### A. Three medium ordering differences

**Observed.** The exact sources create five small inline values and run unordered conversion queries followed by ascending/descending `ORDER BY 1` queries. Only unordered statements occur in the extracted differences. The differences preserve the value sets; they do not show incorrect conversions or incorrect explicitly ordered results. A failed whole case is not independent proof that every other statement passed. See the three medium message/diff pairs in the [excerpt inventory](ci_analysis_evidence_4be72fc_terminal_codex/failure-comparison.json).

**Inference — relation `unknown`, causal confidence low.** Ordinary INSERT now passes through [heap_attrinfo_prepare_record at this head](https://github.com/CUBRID/cubrid/blob/4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c/src/storage/heap_file.c#L13279) and [locator_attribute_info_force](https://github.com/CUBRID/cubrid/blob/4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c/src/transaction/locator_sr.c#L7816), so small inline fixtures do not exclude PR involvement. No changed source establishes a new ordering contract or isolates an Engine-only mechanism. The baseline passes and the same symptoms in the preceding report are observations, not a controlled experiment.

**Unknowns.** Exact CTP/helper/config equivalence, medium archive bytes, starting database/OID allocation and execution plans have not been established. Matching medium shard plan bytes establish allocation only.

**Falsifier / next action.** Compare a complete serial `_02_xtests` directory on the exact engines with the same CTP revision, archive, configuration and starting state, retaining order and value multisets. Repeated base order changes or a CTP-only explanation falsify an Engine-only hypothesis; different value multisets or explicitly ordered differences falsify the narrow presentation finding. This is proposed follow-up, not a reproduction run performed here. Preserve the existing answers until the ordering-preservation question is resolved.

### B. Partition-loader expectation conflict

**Observed.** The exact private fixture creates only `p0 VALUES LESS THAN (10)`, inserts `1`, unloads, and appends `100` to the objects file before server loaddb. Its answer expects two committed child rows. Head rejects the out-of-domain row and reports 0 inserted / 1 failed; the same exact case passes on the base. The separate test3 count check passes and the log reports 10,000 rows loaded, so that final check is not a test2 rollback invariant.

**Inference — relation `direct`, confidence high.** [start_attrinfo](https://github.com/CUBRID/cubrid/blob/4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c/src/loaddb/load_server_loader.cpp#L1205) distinguishes root and direct-child input. [flush_records](https://github.com/CUBRID/cubrid/blob/4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c/src/loaddb/load_server_loader.cpp#L813) routes partitioned rows through `locator_insert_force` with that pruning type. The invalid input, exact runtime domain error and source change explain the answer conflict independently of an unmeasured CTP performance effect. The published PR body already describes this intended child-domain rejection. This does not establish every loader output/count detail as correct.

**Unknowns.** Actual generated `%class`, invalid-load rollback/retained-row counts and valid root/child routing invariants are not independently asserted by this sorted output comparison.

**Falsifier / next action.** A valid `<10` child row rejected at this head, a root row rejected despite a valid destination, or an invalid value actually persisted would defeat the intended-validation explanation. In separate testcase work, check those invariants and error/rollback counts before revising the legacy expectation. No answer is changed or waived here.

### C. Two CDC signatures observed on the exact base

**Observed.** Both sides fail the same DELETE/UPDATE subcases in the first CDC case with extractor exit 1 and incomplete target counts. The second case reaches sequence 2000 but reports extraction errors: head 1/0/1 at 4K/8K/16K versus base 4/4/4. Both report zero corruption counters. Head's successful 8K predicate is variable evidence; it is not a demonstrated fix. There is no newly observed crash/corruption signature in these retained diagnostic excerpts.

**Inference — relation `unlikely` to be newly introduced, high confidence in prior observation and medium confidence in mechanism.** [Accepted ADR-0005](https://github.com/vimkim/cubrid-oos-context/blob/75f8b58674ac901d478ba60f9b2cc2fff11f66f6/docs/adr/0005-defer-oos-history-from-the-11-5-merge.md) explicitly defers OOS historical images and keeps these two cases enabled and visibly failing. The normative context was updated 2026-09-22. That design gap is a plausible mechanism; the two exact executions establish pre-existence of the failure category, not the exact failing instruction or zero PR influence.

**Unknowns.** Full extractor error/LSA-to-reclamation correlation and the cause of each error are not isolated. Differences in counts, page-size outcomes, runner input and timing prevent attributing apparent severity changes to the PR.

**Falsifier / next action.** A controlled comparison producing a new head-only stack/error tied to finalization would falsify an exclusively pre-existing explanation. Retain exact extractor error/LSA evidence for the separate history investigation; keep both tests visible. Their prior signatures do not waive CI requirements.

### D. Newly observed loader diagnostic difference: cbrd_26280

**Observed.** Test7 loads the exact fixture `6 'kk end' NNUL` into a three-attribute table. It fails, as intended, but emits only `Missing attribute values. Expected 3, found 2.` and counts one failed object. The expected answer also contains the parser's `syntax error` line and counts two failures. The test's syntax-message predicate fails; its duplication predicate is bypassed after that failure. Earlier successful data/whitespace checks are not the observed failure. Head exit 3 means this is not accidental acceptance of malformed input.

**Inference — relation `plausible`, causal confidence low.** The PR changes [finish_line](https://github.com/CUBRID/cubrid/blob/4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c/src/loaddb/load_server_loader.cpp#L724), including skipping preparation for a line already marked erroneous and handling preparation failure differently. That makes loader error propagation a concrete review target. The parser and error-handler files checked in [source evidence](ci_analysis_evidence_4be72fc_terminal_codex/engine-source-evidence.json) are unchanged. Neither fact proves which thread or callback suppressed the parser diagnostic. Different CTP inputs and shell predecessors leave the base-pass/head-fail observation uncomparable for attribution.

**Unknowns.** Parser/worker callback order, session-failure publication and the exact affected external helper bytes are unverified. It is not established whether the expected double error count is desirable or whether the head loses a required diagnostic.

**Falsifier / next action.** Repeat this exact malformed fixture with the same runner/config on both engines, capturing parser and loader error-handler callbacks and final counts. The same missing diagnostic on controlled base reruns, or a runner-only explanation, falsifies an Engine-only regression hypothesis. If only head consistently suppresses the syntax diagnostic, trace the changed finish-line path before deciding a source repair or expectation correction. Do not approve an answer rewrite from this snapshot alone.

### E. Newly observed index-capacity boundary: bug_bts_15489

**Observed.** The source creates an index on `(id, name)`, inserts 46,000 rows with 128-character values, deletes all rows, waits 60 seconds, and queries index capacity in a 4K database. Head observes exactly 100 total pages, failing the strict `<100` condition. The trace reports zero internal errors. Base JUnit is PASS but supplies no retained exact page-count observation for this comparison.

**Inference — relation `unknown`, causal confidence low.** The fixed wait makes cleanup progress and physical allocation concrete candidate explanations. Ordinary INSERT is changed by the PR, while inspected B-tree and vacuum source blobs are equal to the base. These are hypotheses to isolate; unchanged B-tree code does not exonerate callers, and an index-size threshold is not proof of corruption, a memory leak or a measured performance regression.

**Unknowns.** Base page count, repeated-run distribution, B-tree allocation shape, vacuum progress and effects of earlier cases on this different shard are unavailable.

**Falsifier / next action.** Compare repeated identical-input runs, recording capacity before/after DELETE and cleanup progress beyond the existing wait. Base sometimes reaching 100, or head reaching the expected range after more cleanup, falsifies a simple persistent head-only growth hypothesis. A repeatable larger retained index only at head under matched inputs warrants tracing allocation/cleanup through changed callers. Preserve the predicate while investigating.

## Exact baseline inputs, discovery and separate base-only observations

Baseline discovery covers **all paginated exact-commit statuses and check-run links**, without a repository-wide workflow scan. The collector selected [36570256001 / 1](https://github.com/CUBRID/cubrid/actions/runs/36570256001). Every shard independently proves that it consumed the exact merge-base debug build produced by **36570061594 / 1**. The head's build producer is **37595050033 / 1**. Workflow revision/title/PR association alone is not Engine provenance.

| Baseline suite | Verdict | Tests | Passed | Failures | Errors | Skipped | Planned / run / unrun |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| medium | PASS | 975 | 975 | 0 | 0 | 0 | 975 / 975 / 0 |
| SQL | PASS | 17471 | 17471 | 0 | 0 | 0 | 17471 / 17471 / 0 |
| shell | FAIL | 3289 | 3254 | 5 | 0 | 30 | 3289 / 3259 / 0 |

Baseline totals: 21,735 tests = 21,700 passed + 5 failed + 0 errors + 30 skipped. Head and baseline shell aggregate counts are identical, but their failure sets differ; aggregate equality is not equivalence.

| Input | Head | Exact base | Comparison limit |
| --- | --- | --- | --- |
| Public testcase commit | `bdba62aee0faec05abdd861518824c69b6c1b3c5` | Same; branch `tc/pr-7990` rather than head `tc/pr-7927` | Commit identity is equal; branch label differs |
| Private testcase commit | `c4b9d482fbd491a68510b2552df2c3cac91911fc` | Same; branch `tc/pr-7990` | Exact testcase/answer/fixture objects are equal |
| CTP branch / commit | `develop` / `44e3f97c788ad82091d5b66d728852f3279b1e86` | `develop` / `4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb` | Different tool revisions; affected tool-file equivalence unknown |
| Suite config labels | `conf/medium_dev.conf`, `conf/sql.conf`, `conf/shell_ci.conf` | Same labels | Equal filenames do not prove equal bytes |
| Build mode | debug | debug | Both Engine identities and producing executions validated |
| Medium / SQL shard plans | SHA-256 `d39bbb00…` / `b10cf9e7…` | Equal plan bytes | Does not prove runner/archive/database equivalence |
| Shell shard plan | SHA-256 `682f185f…` | `dc0d344b…` | Allocation differs; case predecessors/runtime state may differ |
| Image / archive / initial state | Not proven identical | Historical run on 2026-09-29 | No controlled single-input Engine comparison |

All 13 head/base failure-source records were read with `git show <recorded-sha>:<full-path>`. The 11 distinct cases and their relevant case-directory objects, or medium answers, were compared by exact Git object listing and are equal. The equal repository SHAs additionally identify the same tracked repositories; this does not prove equal generated fixtures, external helper inputs or runtime state. Both CTP objects are absent in the inspected `/home/vimkim/gh/ctp/run-sql` repository; no fetch/checkout or external-tool equivalence claim was made. [Exact object and coverage receipt](ci_analysis_evidence_4be72fc_terminal_codex/failure-comparison.json).

Three **base-only observed cases** are separate from the eight head failures. Their head JUnit records are PASS; CTP/runtime differences prevent claiming PR fixes:

| Exact baseline-only testcase | Baseline signature | Head outcome | PR relation / confidence |
| --- | --- | --- | --- |
| `shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases/hide_cubrid_replay.sh` | subcase 7: expected masked argument text absent from process-sampling output | PASS | `unknown`; high observation / low cause |
| `shell/_06_issues/_15_1h/bug_bts_15156/cases/bug_bts_15156.sh` | shutdown-success predicate remains 0 after retries in subcase 1 | PASS | `unknown`; high observation / low cause |
| `shell/_40_guava/cbrd_26349/cases/cbrd_26349.sh` | subcases 2/3: remote column-information error differs from expected authentication predicate | PASS | `unknown`; high observation / low cause |

**Unknown / falsifier / next action for these three:** their different pass/fail outcomes cannot be assigned to this PR. A matched-input replay reproducing each base-only signature on head would falsify a fix interpretation; retain these as separate process-sampling, service-lifecycle and DB-link diagnostic follow-ups. Never derive a regression count by subtracting suite failure totals.

## Prioritized actions and local handoff

1. Investigate **cbrd_26280** diagnostic delivery with matched inputs and loader/parser callback evidence. This is new, plausibly related loader behavior with a base PASS, not just order drift.
2. Investigate **bug_bts_15489** with repeated capacity/cleanup observations, including the exact base page count. Do not turn a strict boundary miss into a corruption or leak claim.
3. Resolve the three medium ordering cases with the complete-directory matched-input comparison described above; retain tracker 242's ordering-preservation objective and existing answers.
4. Reconcile the partition-loader legacy answer after checking valid routing and invalid-load rollback/retained counts.
5. Preserve both CDC failures as visible follow-up work under the accepted history-scope decision, and retain the three separate base-only observations. Prior signatures do not waive CUBRID CI requirements.

These are next actions, not authorized CI triggers, repairs, testcase edits or local reproductions performed by this analysis. The current terminal evidence acquisition/report request is complete; broader causality and ordering-preservation work remains pending. Existing source/submodule changes and testcase worktrees/indexes are preserved. Reviewer replies remain in [the existing local draft](design/reviewer-comments-aecce0e.md), unchanged and unpublished.

## Evidence inventory

Local evidence directory: `ci_analysis_evidence_4be72fc_terminal_codex/`.

- `run-terminal.json`, `status.json`, `result.json`, `base-result.json`, collector exit files and `session.json`: execution, snapshot and invocation identity.
- `head-manifest.json`, `baseline-manifest.json`, `head-observation-request.json`, `head-observation-result.json`, `base-observation-request.json`, `base-observation-result.json`: immutable selected identities/observations.
- `ci-validation.json`, `validate_ci.py`, `assessment.json`, `head-assessment.json`, `head-report-mode.json`, `report-mode.json`: independently validated summaries, raw integrity and executable gate inputs/results.
- `case-comparison.json`, `compare_cases.py`, `testcase-sources.json`, `failure-comparison.json`, `analyze_evidence.py`: exact per-case JUnit outcomes, testcase revisions/object equality and complete classification.
- `engine-source-evidence.json`: source excerpts at the pinned head and explicit unchanged-file object checks.
- `excerpts/`: all 13 failure-record message excerpts and available extracted diffs, indexed with original message paths/digests in `failure-comparison.json`. Full messages and targeted raw JUnit/plan/provenance/log files remain in their collector-owned roots and raw indexes. No full environment or credential-bearing console trace is copied into this report.
- `preterminal-report.md`: preserves the earlier incomplete local snapshot without reusing it as terminal evidence.
- `artifact-digests.json`, `final-reconciliation.json`: retained-file integrity and final report/count/source-link checks.

The analysis performed no reviewer reply posting, thread resolution, additional CI trigger, source/testcase edit or local merge. Report publication and the separate PR summary comment are authorized follow-up actions; they do not publish the reviewer reply drafts.
