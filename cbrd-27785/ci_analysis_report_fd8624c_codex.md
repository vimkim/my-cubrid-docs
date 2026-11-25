# PR #8299 CI recovery recommendation and incomplete SQL evidence

Date is 2026-10-29, Asia/Seoul. The intended reader is the PR author.
The question is whether a source fix, testcase fix, or failure-only rerun can recover [PR #8299](https://github.com/CUBRID/cubrid/pull/8299).

The release build needs a source correction before another qualification run.
The shell artifacts identify two failed testcases and earlier failure records.
They do not establish that the failures are flaky or harmless.
Teams is available as a connector but is not connected in this session.
No Teams messages were read.

## Evidence boundary

**This is a warning report. The collected snapshot does not support a complete regression or root-cause conclusion.**
Both exact-head and exact-merge-base collections rejected SQL shard 01 because workflow and JUnit counts disagree.
The report-mode gate returns `warning`, `regression_conclusions_allowed=false`, and `comparison_scope=none`.
The shell and medium evidence below passed independent schema, identity, count, and digest checks.
No SQL verdict was reconstructed through another endpoint to bypass the integrity check.
The compiler diagnostics come from separately preserved GitHub job logs.

The collector is `cubrid-ci 0.2.0 (dd290e9f7b9b, release)`.
Chronicle is `cubrid-tcc 0.3.0`.
Doctor passed before one status request, one head collection, and one baseline collection.
Both collection commands returned exit 4 with established PR and commit identities.

| Identity | Value |
| --- | --- |
| Engine repository | `CUBRID/cubrid` |
| PR head | `fd8624c83f1f3c05b32d3fffb6ee4a1c9306c8b0` |
| Source checkout | `/home/vimkim/gh/cb/CBRD-27785-unified-reader`, clean |
| Remote head | `vimkim/cubrid:CBRD-27785-oos-read-performance` |
| Target | `feature/oos-merge` |
| Target tip and exact merge base | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| Baseline relationship observed | `2026-10-29T05:43:48.653018451Z` |
| Head run | [40756857314, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/40756857314) |
| Baseline run | [40738391553, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/40738391553) |
| Head collection finished | `2026-10-29T05:43:19.238589101Z` |
| Baseline collection finished | `2026-10-29T05:47:48.554640828Z` |

Baseline discovery used all paginated exact-commit statuses and check runs.
It did not use a repository-wide workflow scan or substitute an older green execution.
The workflow revision is distinct from the tested Engine revision.
The head run uses workflow `639628d731be38879f8b467aa8fcbebc84164eae`.

## Current checks and retained suite evidence

The current head has release and shell FAILURE statuses.
Debug, SQL, and medium have SUCCESS statuses.
A provider SUCCESS status does not resolve the SQL evidence mismatch.

| Suite | Head collection | Retained head counts | Baseline collection |
| --- | --- | --- | --- |
| `test_shell` | Completed, validated FAIL | Planned 3,490. Run 3,460. Passed 3,458. Failed 2. Errors 0. Skipped 30. Unrun 0. | Completed, validated FAIL. Passed 3,459, failed 1, skipped 30. |
| `test_medium` | Completed, validated PASS | Planned and passed 975. Failures, errors, skips, and unrun are 0. | Completed, validated PASS, 975 passed. |
| `test_sql` | Collection failed, integrity diagnostic | No validated suite count or reconstructed verdict. Provider status is SUCCESS. | Same shard 01 integrity diagnostic. |

The head shell testcase revision is `0b3d3428e54913e35cc7ba518e4412372593b8a5`.
The baseline shell revision is `75a02020e19be4bfc64e47f7c7a3d5c2b02d7676`.
The head medium revision is `dc80444c95f93d753bbddd960c513780cec76c4d`.
The baseline medium revision is `70db22a1c99dbbaa27fa1438c8967effdfcad551`.
All validated suite shards consumed their pinned Engine's debug build.

The acquisition ledgers retain all 50 shell shards, medium shard 00, and all 10 SQL shards.
No shard is marked failed or not attempted at acquisition.
Retained SQL responses do not establish a valid suite summary.
The diagnostic occurs during identity/count reconciliation, after acquisition.
It reports `result identity mismatch: shard 01 workflow result and JUnit counts disagree`.
It does not report a failed HTTP endpoint or failed-response byte count.

The observation budget is 536,870,912 bytes, with 0 bytes consumed by binary transfers.
Binary collection was disabled.
The head shell and medium raw indexes validate 616 and 28 files.
The baseline shell and medium indexes validate another 616 and 28 files.
All indexed lengths and SHA-256 digests match.

## Validated shell observations

### check_option.sh

The full path is `shell/_39_fig_cake/cbrd_25282/check_option/cases/check_option.sh`.
[Head shard 07](https://github.com/CUBRID/cubrid/actions/runs/40756857314/job/123061350891) reports check 44 as NOK.
Its message records `sum_objects=30000` and `err_cnt=0`.
The [tested script](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/0b3d3428e54913e35cc7ba518e4412372593b8a5/shell/_39_fig_cake/cbrd_25282/check_option/cases/check_option.sh) starts 12 unload processes with `max_clients=10`.
Its assertion requires fewer than 30,000 dumped objects and exactly one connection failure.
The observed successful completion of all objects violates that assertion.
This is not an unload data-loss observation.

Chronicle finds an earlier failure in [PR #8229 run 39701775791](https://github.com/CUBRID/cubrid/actions/runs/39701775791).
That run used Engine `5dd9e8c4f582cdfa1cec06017c67f888dbce4afe` and private TC `8f24d416411812108f37e15e9a1363cfc36e0508`.
Its hash-verified JUnit message has the same check 44, 30,000 objects, and zero connection errors.
Both testcase directories have Git tree `af4d946bd27ff22339fd5e787edbb7add1697811`.
This establishes recurrence of the observed signature on another Engine.
It does not prove identical execution conditions or root cause.

The selected baseline run records this case as PASS.
The baseline and head testcase directories are identical.
Common CTP helpers, host scheduling, and all runtime inputs were not proven equal.
No regression classification is assigned under this report's warning boundary.

### bug_bts_13242.sh

The full path is `shell/_06_issues/_14_1h/bug_bts_13242/cases/bug_bts_13242.sh`.
[Head shard 16](https://github.com/CUBRID/cubrid/actions/runs/40756857314/job/123061351032) reports its sorted lock-output comparison as NOK.
The retained diff changes catalog classes and lock modes, including SCH_S_LOCK versus X_LOCK entries.
It does not identify an OOS corruption or a failed offset read.
Those causes remain unknown.

The [tested script](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/0b3d3428e54913e35cc7ba518e4412372593b8a5/shell/_06_issues/_14_1h/bug_bts_13242/cases/bug_bts_13242.sh) waits for total lock counts before taking a dump.
The current script and answer both use `[6,4,11,6,8,9]`.
The message reaches those counts.
Equal total counts do not establish that the same objects and lock modes are ready.

An [earlier PR #7925 report](../cbrd-27424/ci_analysis_report_6a487cdb6_collector_recovery_codex.md) documents failure and failure after rerun.
Its specific answer-versus-polling-count mismatch must not be transferred to the current testcase.
Only the answer changed between that report's `a261508a624efc7115ac181073d40bca7fc9448c` input and the current directory.
The current answer removes that recorded numeric mismatch.
Chronicle's earlier failures establish testcase recurrence, not recurrence of that old cause.

The selected baseline run records this case as PASS.
Its directory and the head directory both have Git tree `8010c23bb999a8ac6712a999658ebf519b4206cb`.
No regression classification is assigned under the warning boundary.
The baseline's one failed case is instead `shell/_01_utility/_19_loaddb_parameter/parameter_combine/cases/parameter_combine.sh`.
That observation does not make the two current failures harmless.

## History limits

One bounded refresh indexed run 40756857314's shell results.
The refresh used `--revisit-limit 0`.
Status and current-run explain were then repeated once for each exact testcase path.
Both explain results are `SEEN_BEFORE`.
Both flakiness assessments remain `UNKNOWN`.
The recent-window counts are 44 PASS and 2 FAIL for check_option, and 130 PASS and 5 FAIL for bug_bts_13242.
These counts describe retained observations, not a population failure rate.

The selected current occurrences are execution 15630 and 15639.
Engine and testcase SHAs match the independently validated shell bundle.
Chronicle leaves attempt and job attribution unresolved and marks snapshots partial.
Its broad discovery remains stale through 2026-10-27.
The targeted refresh does not make recent cross-company history complete.

## Recovery actions

The [release job](https://github.com/CUBRID/cubrid/actions/runs/40756857314/job/123058048537) rejects `offset` and `next_off` with `-Werror=maybe-uninitialized`.
This is independent of the shell testcase assertions.
The preserved local production flags contain `-Wno-error=maybe-uninitialized`.
A successful local build with that suppression does not qualify the strict release build.

The smallest source candidate adds an explicit error return to the default branch of [heap_recdes_get_var_offset_pair](https://github.com/vimkim/cubrid/blob/fd8624c83f1f3c05b32d3fffb6ee4a1c9306c8b0/src/storage/heap_file.c#L11003).
Every successful switch case already assigns both outputs.
The width validation already rejects unsupported widths.
The candidate makes the switch's error exit explicit for compiler analysis.
It is a proposal, not a compiled fix or proof of a runtime uninitialized read.
The helper and both direct callers were inspected at the exact head.

The proposed branch is:

```c
    default:
      assert_release (false);
      return ER_GENERIC_ERROR;
```

The candidate patch remains unapplied outside the source checkout.
Strict verification must use CI's GCC build environment and recompile heap_file.c for both standalone and server release targets.
The commands must retain `-O2 -DNDEBUG -Wall -Werror` and exclude `-Wno-error=maybe-uninitialized`.
No source repair or strict compilation was performed in this investigation.

| Option | What it can establish | Limitation |
| --- | --- | --- |
| Same-head `/run rerun 40756857314` | Another observation of the recorded shell failures. | The unchanged release source still has the compiler blocker. Passing rerun cases would not prove a root cause. |
| Verified helper fix, push, then `/run all` | Qualifies the new Engine head with both builds and all suites. | The TC failures still need their observed verdicts. This is the recommended next execution. |
| TC stabilization | Can remove an invalid timing assumption after controlled reproduction. | Requires separate evidence and the corresponding TC head-branch workflow. No TC fix is approved by this report. |

For check_option, a stabilization candidate must hold enough client sessions open before testing rejection.
Starting multiple short processes alone does not guarantee simultaneous saturation.
Changing the assertion to accept zero errors would discard the intended connection-limit check.
For bug_bts_13242, first prove query completion while holding the transaction open, then compare its object-specific lock contract.
Do not update its answer or reuse the old numeric fix without a controlled reproduction.
These are investigation proposals, not established causes or tested fixes.

Resolve the SQL workflow-versus-JUnit mismatch before relying on a complete collector report.
A same-head rerun or a separate API read must not conceal that integrity failure.
No CI trigger, source change, TC change, PR-body publication, or Teams post occurred.

## Retained evidence

The local investigation directory is `/mnt/nvme/data-5/tmp/CBRD-27785-ci-triage-20261029-yoWggl`.
The raw bundles remain collector-owned under `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/`.
No raw logs, downloaded artifacts, or query caches are committed to the documentation repository.

The reviewable local evidence includes:

- `status.json`, `head-result.json`, and `base-result.json` preserve the delegated requests.
- `head-result-validation.json`, `base-result-validation.json`, and `validate_bundle.py` preserve independent checks.
- `assessment.json` and `report-mode.json` preserve the warning gate.
- `base-tc-comparison.json` and `base-case-observations.json` preserve input equality and baseline observations.
- `tc-input-comparison.json` records the earlier-versus-current testcase limits.
- The two `*-status-refreshed.json` and `*-explain-refreshed.json` files preserve scoped Chronicle findings.
- `history-sync.json` preserves the one-run refresh.
- `check-option-prior-junit.xml` preserves the hash-verified earlier failure signature.

The prior source campaign directory retains `ci-release-build-clean.log`, `compiler-flags-equality.json`, and `proposed-release-warning-fix.patch`.
Its append-only `decisions.tsv` includes this investigation's new-run boundary.
Model the Domain kept validation records keyed by suite.
Prove It Works kept artifact validation separate from provider status.
Fix Root Causes favored an explicit helper-contract candidate over warning suppression or assertion weakening.
