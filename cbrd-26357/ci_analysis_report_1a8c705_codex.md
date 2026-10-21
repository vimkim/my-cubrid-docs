# PR 7990: four non-CDC shell failures after the develop merge

Analysis date: 2026-10-21, Asia/Seoul. Intended readers: the OOS author and reviewers of [PR 7990](https://github.com/CUBRID/cubrid/pull/7990).

## Finding and decision boundary

The four requested failures have different symptoms. One directly follows an OOS diagnostic-default change. Two compare statistics or estimates against exact answer values. One is a real `csql` allocator abort during partition-schema cleanup.

The shell evidence is complete and independently validated. **The exact merge-base CI baseline is unavailable. None of these four failures is established as a regression introduced by this PR.** The crash remains the highest-priority investigation. No source or testcase repair is part of this report.

CDC cases `cbrd_27064` and `cbrd_27075` remain in the validated six-failure inventory. Their investigation is excluded at the user's request. The other four cases do not exercise CDC.

## Exact inputs and evidence validation

| Input | Recorded identity |
| --- | --- |
| Engine, `CUBRID/cubrid` | `1a8c7057623d92205dbc1324ec43e3cc40fc4cd2`, branch `feature/oos-merge` |
| CI run and attempt | [39589070215, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/39589070215/attempts/1) |
| Consumed engine build | Debug build from run `39588845552`, attempt `1`, at the same engine SHA |
| Private shell testcases | `28ffb73654b812c3c156c3f2512bad066506808c`, branch label `tc/pr-7990` |
| CI CTP assets | `af69c0039ff084fea5ee5ff296cc5301203d4c3f`, confirmed in all four saved job logs |
| Public testcases, previous full-run receipt | `c434a1a10cc6bbb5e251b3ce10f08a884f0f34e9`. Outside this shell-only source analysis |
| Collector | `cubrid-ci 0.2.0 (9536bd3c2867, release)` |
| Shell collection | `2026-10-21T12:19:55.335361507Z`, exit `0`, `ok: true` |
| Matching observation | `20261021T121942.808215320Z-391012-0`, terminal outcome `complete` |

The current PR status snapshot still identifies the engine SHA above. All 50 shard summaries identify that engine and private testcase revision. The producing build run differs from the test run because CI reused its build artifact. This is consistent provenance.

The validation checked the observation request/result schemas, command-result and manifest schemas, their equality, requested suite identity, and all failure schemas. It also checked the summary digest, all **616** indexed raw-file lengths and SHA-256 digests, path containment, and declared message/diff files. All 50 raw JUnit files independently reproduce the suite counts and all six normalized failure messages.

The report-mode gate returns `full` for the head inventory, with `comparison_scope: none` and `regression_conclusions_allowed: false`. No binary collection was requested. Binary consumption was zero.

| Requested suite | State | Verdict | Planned | Run | Passed | Failures | Errors | Skipped | Unrun |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `test_shell` | `completed` | FAIL | 3476 | 3446 | 3440 | 6 | 0 | 30 | 0 |

Both reconciliations hold: `3476 = 3440 + 6 + 0 + 30` and `3476 = 3446 + 0 + 30`.

The previous all-suite observation remains intact under `/home/vimkim/tmp/oos-develop-sync-20261021`. Its collection failed SQL integrity validation because two status rows lack JUnit entries. This report does not make that collection complete or validate SQL. The separate `Check TC PRs` gate also remains failed. Neither gate is waived by this analysis.

## Failure inventory

Paths are relative to private testcase revision `28ffb73654b812c3c156c3f2512bad066506808c`.

| Case and full path | Shard / job | Observed result and signature | Baseline classification | Category / PR relation / confidence |
| --- | --- | --- | --- | --- |
| `cbrd_23136`: `shell/_06_issues/_19_2h/cbrd_23136/cases/cbrd_23136.sh` | 41 / [119188399345](https://github.com/CUBRID/cubrid/actions/runs/39589070215/job/119188399345) | FAIL, assertion 1. `csql` abort in `mspace_free`, called while freeing an attribute name during schema rollback | `uncomparable` | Memory failure during disconnect stress. relation `unknown`. high confidence in crash site, low confidence in introducing cause |
| `cbrd_26354`: `shell/_40_guava/cbrd_26354/cases/cbrd_26354.sh` | 34 / [119188399319](https://github.com/CUBRID/cubrid/actions/runs/39589070215/job/119188399319) | FAIL, subcases 01–12 and 17–20. selectivity shape, term order, and cardinality differences | `uncomparable` | Estimate/answer compatibility. relation `plausible`. high confidence in mismatch, medium confidence in histogram-path explanation |
| `bug_bts_15529`: `shell/_06_issues/_14_2h/bug_bts_15529/cases/bug_bts_15529.sh` | 22 / [119188399284](https://github.com/CUBRID/cubrid/actions/runs/39589070215/job/119188399284) | FAIL, assertion 1. actual default list additionally contains `-1386,-1388,-1389` | `uncomparable` | Diagnostic-default answer mismatch. relation `direct`. high confidence |
| `cbrd_24916_check_index_ovfps`: `shell/_38_fig/cbrd_24916_check_index_ovfps/cases/cbrd_24916_check_index_ovfps.sh` | 04 / [119188473715](https://github.com/CUBRID/cubrid/actions/runs/39589070215/job/119188473715) | FAIL, subcases 8, 9, 10, 12, 13. overflow-page metrics differ | `uncomparable` | Physical index statistics versus fixed answers. relation `plausible`. high confidence in metric differences, low confidence in their cause |
| `cbrd_27064`: `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | 32 | FAIL. CDC investigation excluded | Not assessed, excluded | User-requested exclusion |
| `cbrd_27075`: `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | 22 | FAIL. CDC investigation excluded | Not assessed, excluded | User-requested exclusion |

Inventory accounting: six head failures = four analyzed failures + two excluded CDC failures. For the four analyzed failures: shared with base `0 validated`, additional on head `0 validated`, uncomparable `4`. Baseline-only failures are unknown. These zeros describe validated comparisons, not the absence of shared or additional failures.

## 1. `bug_bts_15529`: OOS changes the tested default

**Observed evidence.** The case tests system-parameter reads, explicit changes, and reset-to-default behavior. At testcase `test.sql:382–386`, it reads `call_stack_dump_activation_list`, sets `4207500`, and restores `defaulT`. The debug answer at lines 949 and 959 contains the upstream default without OOS errors. The CI normal diff shows only two changed parameter-list lines. The explicit `4207500` value and the error-output comparison pass.

The engine explicitly adds three constants to `call_stack_dump_error_codes`: `ER_HEAP_OOS_BAD_INLINE_HEADER`, `ER_HEAP_OOS_CORRUPTED_RECORD`, and `ER_HEAP_OOS_INVALID_ARGUMENT`. They resolve to `-1386`, `-1388`, and `-1389`. These are OOS diagnostics, not CDC errors. See [system_parameter.c:5989](https://github.com/CUBRID/cubrid/blob/1a8c7057623d92205dbc1324ec43e3cc40fc4cd2/src/base/system_parameter.c#L5989) and [error_code.h:1789](https://github.com/CUBRID/cubrid/blob/1a8c7057623d92205dbc1324ec43e3cc40fc4cd2/src/base/error_code.h#L1789).

**Inference and confidence.** This is a direct mismatch between the OOS branch's diagnostic default and the inherited debug answer. Confidence is high. The observed failure does not demonstrate that setting or restoring a parameter is broken.

**Unknowns.** Whether the release answer needs the same adjustment requires checking its selected-build output. No answer was edited.

**Falsifier.** This explanation would be incomplete if the CI comparison contained differences beyond the two default-list lines. The retained normal diff contains only those two changes.

**Next action.** In a separately authorized testcase repair, align the applicable default expectations with the three named OOS errors. Preserve the explicit-value and reset behavior checks.

## 2. `cbrd_26354`: exact plan snapshots depend on the estimation path

**Observed evidence.** The case creates 100000 `t1` rows and 500 `t2` rows, builds indexes, and updates statistics. It masks numeric digits in plan dumps. It deliberately restores the real top-level `card` value because that estimate is the subject of CBRD-26354. See testcase script lines 38–56 and 94–116.

Sixteen of 20 subcases fail. Expected selectivity `sel ?.???` becomes actual `sel ?.????????`. Three-table cases also change join-term order. Several top-level cardinalities change from expected `100000` to actual `99986`. These are **optimizer estimates**, not evidence that SELECT returned fourteen fewer rows.

The printer uses `%G`, which preserves a value-dependent number of significant digits. The formatter masks the digits but preserves their count. The estimator first attempts `histogram_get_join_selectivity`. If that fails, it uses `1 / max(index cardinality)`. See [query_graph.c:9927](https://github.com/CUBRID/cubrid/blob/1a8c7057623d92205dbc1324ec43e3cc40fc4cd2/src/optimizer/query_graph.c#L9927), [query_planner.c:11899](https://github.com/CUBRID/cubrid/blob/1a8c7057623d92205dbc1324ec43e3cc40fc4cd2/src/optimizer/query_planner.c#L11899), and the [exact CI formatter](https://github.com/CUBRID/cubrid-testtools/blob/af69c0039ff084fea5ee5ff296cc5301203d4c3f/CTP/shell/init_path/init.sh#L1151).

**Inference and confidence.** The answer assumes an estimation path or statistic value that this execution does not reproduce. Histogram-based estimation is a plausible explanation for the selectivity and estimate changes. Confidence is medium for that path attribution because the masked output does not record a branch trace. Confidence is high that this is more than whitespace noise.

**PR relationship.** `plausible`, not established. `query_graph.c`, `query_planner.c`, and both `statistics_cl.c` and `statistics_sr.c` are byte-identical to the exact engine merge base. However, OOS changes shared heap scanning and the histogram sampler's `heap_next` call. Equal planner files do not prove equal runtime statistics.

**Historical context.** Private testcase commit `fb6e302a26c8f5604eb7d66a1b301156665ba293` previously excluded this case for the same class of selectivity-digit mismatch. That commit message describes the reverse value direction, so it is context rather than an exact signature match. Commit `7842a35f46b2504a7549f58b1bbd7e475d190bd2` restored the case by rename without changing its contents. Both commits precede the tested private revision.

**Falsifier.** The histogram-path hypothesis would fail if a traced execution reached the cardinality fallback yet produced the same mismatch. An equal-input base execution with the same statistics would also challenge a PR-specific explanation.

**Next action.** Compare raw selectivities, collected statistics, and final estimates on head and merge base using the same testcase files. Decide whether the estimates are acceptable before changing answers. Masking `card` would remove the feature assertion.

## 3. `cbrd_24916_check_index_ovfps`: physical page metrics differ

**Observed evidence.** CI's normal diffs retain full numeric values that the narrow side-by-side summary truncates. Actual versus expected values are:

| Index | Metric | Actual | Expected |
| --- | --- | ---: | ---: |
| `test_partition__p__xx1.testidx` | `Avg_num_ovf_page_per_key` | 54 | 55 |
| `test_partition__p__xx1.testidx` | `Num_ovf_page` | 274 | 278 |
| `test_partition__p__xx2.testidx` | `Num_ovf_page` | 282 | 280 |

Subcases 8–10 and 12 repeat the average-metric difference under different sort/key options. Subcase 13 compares total overflow pages. Subcase 11, which checks maximum pages per key, passes. The output retains the expected table/index rows. The current failure is not the old catalog-query error recorded in the CBRD-26832 draft.

The test inserts 100000 rows into each `xx` table. It builds one index during inserts and makes it invisible afterward. It compares literal page counts after querying capacity. The installed script obtains these metrics through `SHOW INDEX CAPACITY`. The engine returns actual overflow-page counts and an integer average. See testcase script lines 52–69 and 151–170, [check_index_ovfps.sh:343](https://github.com/CUBRID/cubrid/blob/1a8c7057623d92205dbc1324ec43e3cc40fc4cd2/contrib/scripts/check_index_ovfps.sh#L343), and [btree.c:26386](https://github.com/CUBRID/cubrid/blob/1a8c7057623d92205dbc1324ec43e3cc40fc4cd2/src/storage/btree.c#L26386).

**Inference and confidence.** Different physical index layout is consistent with the observed metric changes. The evidence does not prove that layout changed harmlessly or identify the operation responsible. The script uses fixed `RANDOM` seeds, so unseeded SQL randomness is not an established explanation. Confidence is high in the observed differences and low in their cause.

**PR relationship and unknowns.** Relation is `plausible`. `btree.c` and the installed script's source are byte-identical to engine merge base. Heap allocation, OID inputs, bulk-load paths, and execution configuration can still affect layout. No controlled base runtime is available here. Private commit `b932529607c81dcff5428ad075667c10e8ecf69a` previously re-baselined this case for OID-ordered overflow chains. That historical rationale does not validate these new values.

**Falsifier.** A matched base/head execution with identical OID placement and different reported counts would challenge the layout-input explanation. Independent traversal that disagrees with `SHOW INDEX CAPACITY` would identify a capacity-accounting problem instead.

**Next action.** Preserve databases on a controlled base/head comparison. Check index integrity, OID distribution, and independently counted overflow pages before changing expected metrics. Preserve owner, class, invisible-index, threshold, and sorting assertions.

## 4. `cbrd_23136`: allocator abort while cleaning a partition class

**Observed evidence.** The test runs the partition-DDL input `1223.sql` repeatedly in `csql`. Another process repeatedly kills and restarts its server. The outer case checks for cores over approximately 255 seconds. Its input uses ordinary numeric/timestamp columns and does not invoke CDC.

CI records a `csql` core. The relevant stack is:

```text
mspace_free
  classobj_clear_attribute, class_object.c:4801
  classobj_free_threaded_array
  classobj_free_class
  ws_decache
  ws_abort_mops
  tran_internal_abort_upto_savepoint, savepoint "aDDuNIQUEcONSTRAINT"
  update_class
  sm_finish_class
  dbt_finish_class
  do_create_partition
```

At the recorded line, `classobj_clear_attribute` frees `att->header.name`. Workspace class eviction owns disposal of the cached class and its attribute array. Rollback calls workspace cleanup before requesting the partial server abort. See [class_object.c:4799](https://github.com/CUBRID/cubrid/blob/1a8c7057623d92205dbc1324ec43e3cc40fc4cd2/src/object/class_object.c#L4799), [work_space.c:2760](https://github.com/CUBRID/cubrid/blob/1a8c7057623d92205dbc1324ec43e3cc40fc4cd2/src/object/work_space.c#L2760), and [transaction_cl.c:1237](https://github.com/CUBRID/cubrid/blob/1a8c7057623d92205dbc1324ec43e3cc40fc4cd2/src/transaction/transaction_cl.c#L1237).

**Inference and confidence.** The observed allocator abort occurs during attribute-name disposal on the schema error path. Confidence is high in this localization. The stack alone cannot distinguish a double free, an invalid allocation owner, or earlier memory corruption. It does not identify the earlier write or free.

**PR relationship and unknowns.** Relation is `unknown`. The failing clear function is unchanged from engine merge base. Workspace cleanup, transaction cleanup, and `schema_manager.c` are also byte-identical. OOS does change other schema and record-conversion code. Neither unchanged cleanup nor those nearby changes establish causality. The saved merge-conflict patch does not establish the origin of this crash.

**Falsifier.** Attribution to this disposal path would fail if a matching replay/core showed a different failing free. A controlled base reproduction with the same signature would disprove the claim that only head can exhibit it.

**Next action.** Obtain a repeatable failure under matching optimization, allocator, and interruption timing. Then trace ownership of the affected attribute name, starting before partition creation and through rollback. Preserve the crash as an engine investigation. Do not replace its expected result or classify it as harmless timing noise.

## Exact merge-base comparison and merge context

One `cubrid-ci collect-base ... --suite test_shell --json` returned exit `3`. Its schema-v3 manifest and observation-v2 pair validate independently. The matching observation is `20261021T122037.639240195Z-391107-0`, outcome `incomplete`.

| Relationship | SHA |
| --- | --- |
| Pinned PR head | `1a8c7057623d92205dbc1324ec43e3cc40fc4cd2` |
| Observed target `develop` tip | `3ba41d74509d9a6c19ef9adc6cf12d9ebebdbbac` |
| Exact merge base | `3ba41d74509d9a6c19ef9adc6cf12d9ebebdbbac` |
| Target observation time | `2026-10-21T12:19:40.829912783Z` |

Discovery covered all paginated exact-commit statuses and check runs. It found no candidate execution. `test_shell` is `not_observed`, with no selected run, shards, or baseline testcase revision. This is an unavailable baseline, not a passing baseline. No CI was triggered.

Source comparison used exact Git objects. All **37** files under the four testcase directories, including scripts, answers, and SQL inputs, equal private develop merge parent `05fdcbea80b8c4268f21dd6241eb843952eb6fc8`. This establishes affected-directory equality, not equality of every external helper. The saved equality inventory records every blob ID.

The merge made additional cases eligible for CI. `bug_bts_15529` and `cbrd_26354` were restored from `_25_unstable` by private commit `7842a35f4`. `cbrd_24916_check_index_ovfps` was repaired and restored by `fd4b59dda2368cef39ebd1f58a42704d19fa2f50`. These changes explain newly active coverage. They do not explain the `cbrd_23136` crash or prove that any engine defect was introduced by the merge.

Nine relevant engine files also have equal base/head blobs: planner, query graph, client/server statistics, schema manager, workspace, transaction client, B-tree implementation, and the index-check script. Modified shared heap and histogram-sampler paths remain comparison limitations. Full equality inventories are retained outside the document repository.

## Testcase history

History used `cubrid-tcc 0.3.0`. Initial exact-path `status`, selected-run `explain`, and unrestricted retained `history` queries lacked the current execution. One bounded refresh selected run `39589070215`, suite `shell`, with `--revisit-limit 0`. It retained 50 snapshots and reported one unavailable file. Each affected query was then repeated once.

| Exact testcase | Current execution ID | Recorded PASS / FAIL observations | Historical conclusion |
| --- | ---: | --- | --- |
| `bug_bts_15529` | 12385 | 17 / 2 | `SEEN_BEFORE`, but the earlier failure has a different signature |
| `cbrd_23136` | 12404 | 136 / 1 | `UNKNOWN_HISTORY`. No earlier retained failure of this exact path |
| `cbrd_26354` | 12397 | 18 / 1 | `UNKNOWN_HISTORY`. No earlier retained failure of this exact path |
| `cbrd_24916_check_index_ovfps` | 12367 | 0 / 1 | `UNKNOWN_HISTORY`. No earlier retained occurrence of this exact path |

Each selected occurrence matches the current engine SHA, testcase SHA, full path, suite, and shard. Chronicle leaves attempt and job fields unresolved and marks the snapshots partial with `runner_error`. The candidate jobs match the selected CI jobs. These occurrences supply historical context, not independent validation of attempt 1. The independently validated `cubrid-ci` bundle establishes the current verdict.

The earlier `bug_bts_15529` failure is execution `7341`, [run 38889243506](https://github.com/CUBRID/cubrid/actions/runs/38889243506), engine `5566537938101f8fa8f73efa58944939d5f1bd1a`, private testcase `60dade07b511ebb7d7bd5b377442d4b25fb6702e`. It completed on `2026-10-16T11:32:32Z`. Its hash-verified JUnit evidence reports missing `optimizer_reserve_02`, not added OOS stack-dump errors. Therefore recurrence of the testcase does not establish recurrence of this failure signature. The retained JUnit digest is `98bc3e46c5f34eb1eec0bb52d8945d81cfe08efa6e201bafbbe412d65b756971`.

Chronicle reports flakiness `UNKNOWN` for all four cases. Mixed outcomes use different engine/testcase contexts and do not prove flakiness. Discovery remains stale through `2026-10-19T06:05:24Z`, with incomplete coverage. The selected-run refresh does not make broader discovery complete. Renamed `_25_unstable` paths are separate identities in these exact-path queries. Historical commit descriptions above remain separately labeled source history.

## Local reproduction

The retained source checkout is `/home/vimkim/gh/cb/oos-develop-sync-20261021`, at the analyzed SHA. Its initial installation reported `fb567a6`, so native preflight correctly rejected that install. The selected `debug_gcc` configuration was regenerated. The engine was then rebuilt and installed. The resulting `cubrid_rel` reports `11.5.0.2726-1a8c705`. No commit-mismatch exception was used.

The contained native attempt copies the installation and CTP assets and uses a disposable home and database registry. The testcase checkout stays at the recorded private SHA. Effective configuration selects exactly the four non-CDC cases, one slot, `scenario_disk=on`, file feedback, no updates, no retries, no continuation, and a 1200-second per-case limit.

```text
TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell -c <attempt>/conf/shell.conf
```

The local runner is `cubrid-testkit dev`, SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`. CTP assets come from `/home/vimkim/gh/ctp/run-sql/CTP`, repository HEAD `9c62858b10005d721546cc007be260844033b9e9`. Pre-existing changes to its shell wrapper, compatibility helper, and shell XML configuration were copied and preserved. These local assets, the host, and the CMake Debug build differ from the CI runner and its optdebug binary. This run is a focused reproduction, not full-suite qualification or an exact CI binary replay.

The runner completed in 423 seconds and returned `0`. Both dispatch and finish lists contain exactly the four requested paths. The text summary reports three failures and one success. It also counts 21 unrelated macro exclusions from corpus discovery, resulting in `Total Case:25`.

| Requested case | Local text observation | Relationship to CI |
| --- | --- | --- |
| `bug_bts_15529` | NOK. Both OOS-default differences recur. An additional local `log_max_archives` difference is `2147483647` versus expected `0`. | The four CI diff lines recur. The extra configuration difference is local. |
| `cbrd_24916_check_index_ovfps` | NOK. All twelve CI normal-diff lines recur, including 54/55, 274/278, and 282/280. | Same observed metric signature in text logs. |
| `cbrd_26354` | NOK. All sixty CI normal-diff lines recur, including `100000` versus `99986`. | Same observed plan/estimate signature in text logs. |
| `cbrd_23136` | The text log reports OK after the full interruption interval. It reports no core. | The CI crash did not recur in this attempt. This does not validate a passing testcase verdict. |

**Formal local verdict: inconclusive.** The required artifact verifier rejects `total case count is 25, expected 4`. Independent XML parsing also fails at line 1169, column 185. The emitted JUnit file contains invalid UTF-8 bytes in captured shell tracing. These bytes and the original counts remain unchanged. The text comparisons support symptom reproduction, but they do not repair the artifact contract or establish a validated pass for `cbrd_23136`.

The attempted command, actual exit status, complete dispatch lists, and `verification.txt` remain in `attempt-01`. `local-diagnostics.json` records the 76 matching CI normal-diff lines and the two additional local lines. No retry changed testcase files, expected answers, or tool-owned results.

To obtain a validated native verdict, address the runner's unrelated macro accounting and XML encoding separately, then create a new retained attempt. A repeat under the same artifact conditions cannot establish a pass. To investigate the crash itself, also match the CI binary optimization and interruption conditions.

## Prioritized actions

1. Reproduce and localize the `cbrd_23136` allocator abort under matching runtime conditions. Keep it visible as an engine failure.
2. Prepare a narrow testcase repair for `bug_bts_15529` that preserves its parameter-mutation checks.
3. Compare head/base statistics and raw selectivities for `cbrd_26354`. Preserve the asserted top-level estimate.
4. Compare index layout and capacity on equal inputs for `cbrd_24916_check_index_ovfps`. Verify integrity before accepting new counts.
5. Resolve the separate SQL evidence discrepancy and `Check TC PRs` gate through their own workflows. CDC remains excluded from this investigation.

No new CI trigger, remote comment, source/testcase push, testcase merge, or final PR merge occurred.

## Evidence inventory and reproduction records

Evidence root `R` is `/home/vimkim/tmp/pr7990-four-shell-analysis-20261021`. Raw evidence remains tool-owned and is not copied into this report's Git history.

| Reference under `R` | Purpose |
| --- | --- |
| `status.json`, `head-result.json`, `head-validation.json`, `raw-crosscheck.json` | Pinned status, shell-only command, schema/digest checks, raw JUnit reconciliation |
| `assessment.json`, `validate_bundle.py` | Assessment inputs and retained validation procedure |
| `base-result.json`, `base-validation.json` | Independently validated unavailable-baseline observation |
| `source/testcase-file-equality.json`, `source/engine-file-equality.json` | Exact Git blob comparisons |
| `source/*-changes.json` | Selected full-width normal-diff lines with original message line numbers |
| `ci-ctp-revisions.json`, `source/ci-ctp-init.sh` | Saved job-log CTP identities and exact CI formatter source |
| `history/*-refreshed.json`, `history/coverage.json`, `history/sync.json` | Exact-path history, one refresh, and coverage limitations |
| `history/earlier-7341-evidence.json`, `history/earlier-7341-test-shell.xml` | Earlier failure signature and verified evidence bytes |
| `configure.log`, `build-install.log`, `preflight-matched.json` | Exact-source build and native-run identity |
| `attempt-01/` | Exact case list, copied config/assets, command, runner status, and native verdict artifacts |
| `local-diagnostics.json` | Text-signature matches and the bounded local artifact failure |

Head bundle `H` is `R/ci-evidence/github-actions/CUBRID-cubrid/pr-7990/1a8c7057623d92205dbc1324ec43e3cc40fc4cd2`. The suite directory is `H/providers/github-actions/runs/39589070215/attempts/1/test_shell`.

The [validated shell summary](https://dev2.baboon-rudd.ts.net:8443/home/vimkim/tmp/pr7990-four-shell-analysis-20261021/ci-evidence/github-actions/CUBRID-cubrid/pr-7990/1a8c7057623d92205dbc1324ec43e3cc40fc4cd2/providers/github-actions/runs/39589070215/attempts/1/test_shell/summary.json) identifies every shard and failure. Each failure directory below contains `metadata.json`, `message.txt`, and `diff.txt`:

| Case | Stable directory below suite `failures/` | Useful message lines |
| --- | --- | --- |
| `cbrd_23136` | `shell_06_issues_19_2h_cbrd_23136_cases_cbrd_23136_sh-f9987cbd70` | Core analyzer and full stack near the start |
| `cbrd_26354` | `shell_40_guava_cbrd_26354_cases_cbrd_26354_sh-181d539eef` | Full-width normal differences start at 799 |
| `bug_bts_15529` | `shell_06_issues_14_2h_bug_bts_15529_cases_bug_bts_15529_sh-b72b2a89dc` | 1110–1116, both changed default-list lines |
| `cbrd_24916_check_index_ovfps` | `shell_38_fig_cbrd_24916_check_index_ovfps_cases_cbrd_24916_check_index_ovfps_sh-528899b208` | 580–582 and 1210–1214, full page metrics |

Raw CI evidence is in `raw/shards/04`, `22`, `34`, and `41`, with digests in `raw/index.json`. The summary SHA-256 is `2d86d5cfee7d46b7d11886017c49ace8bcf58cc50e113f2a443b9e2a9bf999b3`.

The earlier failed all-suite command remains `/home/vimkim/tmp/oos-develop-sync-20261021/ci-collection.json`. Its SQL discrepancy remains in `sql-count-discrepancy.json` beside it. The original handoff remains `/mnt/nvme/data-5/tmp/handoff-pr7990-four-shell-failures-20261021.md`. Work item `483` records this analysis separately from completed merge/CI item `478`.
