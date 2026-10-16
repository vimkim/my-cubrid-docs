# PR7925: use the prepared row after workspace conversion

Accepted: 2026-10-17, Asia/Seoul. Work Item 397. Related Work Item 393.
Starting engine revision: `b755678cd9a3ab465215228d5664f7f1edf24846`.

The user accepted the proposed implementation sequence after reading the plain-English HTML explanation and the [review assessment](review-comment-4257963742_b755678cd_ste.md).
Use the common prepared-row path when preparation is necessary.
Remove the late SA-only branch that discards the prepared inline row.

## Revised guarantee

Workspace conversion must preserve column values and meaningful header fields, including the workspace-assigned cache change number (CHN).
Preserve schema defaults, NULL and empty values, valid layout, OOS selection, destination ownership, external LOB behavior, and existing transaction behavior.
Preserve finalization, publication reset, and error propagation.
Keep the prepared buffer valid through all consumers.
Release temporary memory when its owner leaves scope on success or failure.

Valid encoding differences and unused padding may differ from the input bytes.
This decision does not require complete input-byte identity after preparation.
It does not claim that every eligible input differs only in padding.

This decision supersedes User Story 27 and the original-row/prompt-release clause in the earlier simplification specification.
That specification states: "Keep the input record when no value is demoted and release the unused conversion buffer promptly."
Its retained local source is `.scratch/pr7925-review-simplification/spec.md` in the main documentation checkout.
The remaining requirements in that specification still apply.
The earlier requirement explains the historical branch. It does not govern the selected response to review comment 4257963742.

## Implementation boundary

Keep the existing preparation and finalization functions.
Select the prepared record and its received owner in both SA and server builds.
Do not add a competing preparation filter or change partition selection.
PR7927 owns the related filter and destination interface.
Its observed open head is `9ba5b9b927e5c1820f2f9d7a6f7d9acfa447e773` on 2026-10-17.
Actual dependency integration and combined acceptance remain pending under WI393.

The change preserves storage thresholds, demotion policy, disk format, and the existing logged-operation contract.
Successful no-logging loading remains supported within its existing limitations.
Memory cleanup does not undo database writes.

## Required verification

1. Build and install the changed source with the selected debug configuration.
2. Preserve and execute all 21 stored-row comparisons and 13 loader/workspace cases.
3. Check CHN against the actual workspace object after its flush.
4. Check values, storage policy, defaults, finalization, errors, rollback, and buffer lifetime.
5. Execute the focused native loader partition regression.
6. Compare matched small-row and OOS loader workloads, including peak memory.
7. Review Standards and Spec against the pinned starting revision.
8. Publish scoped source changes and trigger one new full CI cycle after focused checks pass.
9. Wait for CI, report its result and merge gates, then stop for human direction.

The results below record the completed local checks.
The completed baseline [CI report](ci_analysis_report_b755678cd_run38861566581_codex.md) does not test this change.

## Implementation and local verification

Changed engine: `6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f`.
The source change removes the late SA branch in `locator_finalize_oos_record`.
The common path selects the prepared record and retains its received owner.
The comparison fixture also checks each committed row's CHN against the workspace object after its flush.
The change adds no test case and removes no test case.

The selected configuration is `debug_gcc`.
The changed source compiled and installed successfully in both SA and server builds.
After the commit, reconfiguration and another build refreshed the installed revision metadata.
Native preflight then proved that the source and installed revisions match.
The initial metadata preflight stopped before testcase execution. The native runner used no mismatch bypass.

| Check | Result | Evidence scope |
| --- | --- | --- |
| Configured CTests | 38/38 pass in 351.05 seconds | Exact changed source before its packaging commit |
| GoogleTest XML | 374 pass, zero failures/errors/disabled/skips | Case names match the baseline inventory exactly |
| Stored-row comparisons | 21/21 pass | Includes the new CHN assertions in all fixtures |
| Real loader/workspace cases | 13/13 pass | Includes rollback, ignored errors, LOBs, partitions, and successful no-logging loads |
| Native partition loader | 1/1 case, 28/28 assertions pass | Containment enabled, strict artifact verifier passes |
| Source and formatting | Pass | Tested source hashes match the commit and the formatter left the test unchanged |

The native shell testcase is `shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh`.
Its private TC revision is `a261508a624efc7115ac181073d40bca7fc9448c`.
The public TC head remains `26f964b8a6e222c33765fa317eaaf4fe666d5f44`.
Both feature-baseline ancestry checks pass. This source change needs no additional TC changes.

### Standards

The independent Standards review found zero findings in `b755678cd...6a487cdb6`.
The deletion preserves the existing error style and formatter guards.
The CHN assertion follows the established GoogleTest fixture.

### Spec

The independent Spec review found zero findings in the same diff.
INSERT and UPDATE retain function-local received owners through heap, index, foreign-key processing, and all success/error exits.
Foreign-key replacement can select another record without a destructor restoring an obsolete pointer.
The common finalization call, publication reset, header transfer, and error propagation remain intact.
Actual dependency integration and combined acceptance remain under WI393.

## Matched loader measurements

Five alternating before/after pairs ran each workload on logical CPU 79.
The installations contain baseline `b755678cd` and changed `6a487cdb6`, using the same debug configuration.
Each sample creates a private database and times only standalone `cubrid loaddb`.
No local build or test ran concurrently with measurement.
The host remains shared. CPU affinity does not reserve the CPU or storage.

The existing benchmark harness supplies 100,000 rows with a 48-byte value and 10,000 rows with a 5,000-byte value.
A retained harness copy adds peak RSS to the existing elapsed and CPU measurements.
All 20 timed loads pass independent row-count and value checks.
Every small sample has no OOS file. Every large sample has 10,000 OOS records.

| Workload | Elapsed median, before → after | CPU median, before → after | Peak RSS in every sample |
| --- | --- | --- | --- |
| Small inline rows | 5.51 → 5.45 seconds | 4.35 → 4.30 seconds | 194,560 KiB on both versions |
| OOS rows | 10.19 → 10.15 seconds | 8.96 → 8.91 seconds | 264,960 KiB on both versions |

The comparison shows no observed regression in these workloads.
The small timing differences do not establish a production speed improvement.
These debug measurements do not replace release qualification or an allocation profile.
The prepared buffer still lives longer on the changed inline path, even though process peak RSS matches.

## Evidence and remaining gates

Raw receipts remain outside the documentation repository:
`/mnt/nvme/data-5/tmp/wi397-pr7925-20261017.FGB89ikS`.
The selected summaries are `ctest-verification.json`, `native-shell-summary.json`, `review-summary.json`, and `benchmark-summary.json`.
The directory also retains build logs, execution logs, XML, source hashes, benchmark order, installation hashes, and per-sample placement checks.

The pre-existing CCI change remains outside the source commit.
Its `win/cci_version.h` SHA-256 remains `f9766b68dab0c3f615a02cf29368396a43e887b8bc052e0fba321add407259a3`.
No shared source integration, TC merge/closure, or documentation-main merge occurred during these checks.
Human TC disposition remains pending at this checkpoint.

## Published source and one CI cycle

Commit `6a487cdb6` reached `vimkim/cubrid:CBRD-27424-oos-loaddb-sa` through a normal fast-forward push.
The pre-push freshness check confirmed that it contains the latest target tip.
Both testcase branches contain their current feature baselines.
No source merge or TC publication occurred in this step.

The agent posted exactly one new [`/run all` request](https://github.com/CUBRID/cubrid/pull/7925#issuecomment-6220855678).
All five gha-ci contexts selected [run 38938588691](https://github.com/CUBRID/cubrid/actions/runs/38938588691), attempt 1, for this source head.
The contexts initially reported pending.
The requested terminal result remains pending at this checkpoint.
After reporting that result, the agent must stop before another fix, push, or rerun until directed.
