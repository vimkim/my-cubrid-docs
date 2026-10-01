# PR 7990 analysis of three unexpected CI failures

**The CI retry setting did change, but the three failures have different explanations.** `cbrd_26349` is a confirmed false failure caused by counting part of an IP address. `hide_cubrid_replay` has a confirmed invalid user fixture and a probable process-sampling race. `bug_bts_15156` failed after the master was restarted; its underlying cause is still open because the decisive diagnostics are not in the collected text logs.

This report covers the September 29 run on engine `fb567a629cdb390fff920542173fa36f454c74a0`. The two CDC failures are counted for completeness and excluded from causal analysis, as requested. It does not establish overall OOS merge readiness.

## Conclusions by testcase

| Testcase and independent report | Why it reported failure | Confidence and PR relation | Action |
| --- | --- | --- | --- |
| [cbrd_26349](ci_fb567a6/cbrd_26349.md) | `grep -wc 100` counted `.100` in the runner IP. Correct outputs became false counts of 3 instead of 0 and 2. | Confirmed, high; PR relation unlikely | Correct result-row parsing |
| [hide_cubrid_replay](ci_fb567a6/hide_cubrid_replay.md) | `qa9` creation failed because `db_user` has no `add_user` method. Replay failed to connect; the asynchronous process check produced no mask sample. | Fixture and empty result confirmed; missed-window cause medium-high; PR relation unlikely | Fix user setup and synchronize the password-mask check |
| [bug_bts_15156](ci_fb567a6/bug_bts_15156.md) | Master restart passed, but 21 database-stop checks failed. No CPU-threshold failure was recorded. | Failed assertion confirmed; underlying cause unknown; PR relation unknown | Preserve/recover server diagnostics and compare exact PR and develop builds |

The first two reports identify actionable testcase defects. The third must remain unresolved; calling all three harmless flakes would exceed the evidence. Each report is standalone, with its own source links, observations, inference limits, falsifier and next action. They are separate testcase analyses, not three independent reviewers of the same testcase.

## What changed in CI retries

The current shell logs for shards 17, 35 and 46 explicitly print `testcase_retry_num=0`, including the resolved CTP properties. These shards ran CTP `4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb`. A cached [September 25 CI run](https://github.com/CUBRID/cubrid/actions/runs/36104247286) prints `testcase_retry_num=1` with CTP `db9074728040c29532b4feb5da4d9640fb09f9fc`. [Timestamped excerpts](ci_fb567a6/evidence.md#retry-setting-evidence).

Thus the observed setting changed between those runs, and this run retained first-attempt failures. The available evidence does **not** establish the exact change commit, deployment time, or whether the stated motivation was to catch flaky tests earlier. The exact current CTP source object is absent from the local clone; the old local configuration was not substituted for it. The executed logs are the evidence for the current value.

Retry removal affects visibility, not the underlying defect:

- The DBLink IP-counting bug will normally persist on a same-pod retry.
- The replay sampler could pass with different scheduling while its broken fixture remains. Older September 21 and 23 logs already show a terminal failure with `TRY->1`; retry availability did not guarantee a pass.
- For the master-restart testcase, neither a retry pass nor its cause is established at this commit.

The historical logs are supporting context only. They are not a controlled before/after experiment with identical engine, testcase and runner identities, and are not included in the current suite totals.

## Current CI snapshot

[Run 36570256001](https://github.com/CUBRID/cubrid/actions/runs/36570256001), attempt 1, uses engine `fb567a629cdb390fff920542173fa36f454c74a0`. All three suites have complete, validated collection results.

| Suite | Verdict | Planned | Executed | Passed | Failed | Errors | Skipped | Unrun |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| test_medium | Pass | 975 | 975 | 975 | 0 | 0 | 0 | 0 |
| test_sql | Pass | 17,471 | 17,471 | 17,471 | 0 | 0 | 0 | 0 |
| test_shell | Fail | 3,289 | 3,259 | 3,254 | 5 | 0 | 30 | 0 |

The five failed testcases are: `hide_cubrid_replay` (shard 17), `bug_bts_15156` (35), `cbrd_26349` (46), and the excluded CDC cases `cbrd_27064` (29) and `cbrd_27075` (49). Multiple failed assertions inside one testcase do not increase the testcase failure count. Both release and debug build status checks passed; the collected testcase shards used the debug build.

## Evidence and validation

Collection time: `2026-10-01T08:55:07.029880512Z`. Collector: `cubrid-ci 0.2.0 (45944012aaaa, release)`. Observation: `20261001T085455.124687095Z-71082-0`. The selected terminal observation and manifest agree with the saved command result and PR head. All requested suite summaries, all five failure records, and all 780 indexed raw files passed schema, path, length/digest and identity checks as applicable. Counts reconcile; the analyzer's report-mode gate returned `full`.

The public testcase revision was `bdba62aee0faec05abdd861518824c69b6c1b3c5`; the private shell revision was `c4b9d482fbd491a68510b2552df2c3cac91911fc`. The three studied testcase directories have no diff from the merged private develop parent `c8880167e176c3a8c0bd60c883355313ebe2e153`. Relevant engine source was read with `git show` at the exact engine SHA and compared to its integrated develop parent `f1bd99ed43a134383bc0be1d766a6f121601a499`.

The issue-comment workflow itself ran from develop `f1bd99ed43a134383bc0be1d766a6f121601a499`; this is distinct from the engine SHA under test. The collector's build receipts establish the latter. [Workflow invocation of CTP](https://github.com/CUBRID/cubrid/blob/f1bd99ed43a134383bc0be1d766a6f121601a499/.github/workflows/gha-ci.yml#L2005-L2021).

Evidence bundle on the investigation host:

```text
/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7990/fb567a629cdb390fff920542173fa36f454c74a0
```

Within that bundle, the suite evidence lives under `providers/github-actions/runs/36570256001/attempts/1/<suite>/`. The inventory comprises `manifest.json`, the observation's `request.json` and `result.json`, each suite's `summary.json` and `raw/index.json`, all five `failures/<stable_id>/metadata.json` records with their declared message/diff files, and the selected shell shard JUnit files. [Validation receipt and failure paths](ci_fb567a6/validation.json), [readable excerpts](ci_fb567a6/evidence.md), and [offline parser verification](ci_fb567a6/verification.txt) accompany this report. Cached GitHub job logs used for retry history are identified separately in the excerpts.

The text collection did not request binary archives. This is a scope limitation, not a collection failure or proof of no cores. No full testcase was rerun, and there is no matched develop runtime comparison. Exact process-sampling data for replay and the decisive lifecycle logs for `15156` remain unavailable in this text snapshot. The separate `Check TC PRs` gate is outside this failure-cause report.

## Recommended order of work

1. Correct and verify the deterministic DBLink parser defect.
2. Correct replay user setup, assert successful preparation, and make mask observation reliable without filtering plaintext exposure away.
3. Keep `bug_bts_15156` open. Recover the diagnostic archive or capture server lifetime, HA mode and every stop response in an isolated baseline comparison before attributing it to flakiness or OOS.

Changing retries alone would hide evidence without resolving these causes. No source or testcase edits, CI reruns, or default-branch merges were performed as part of this report.
