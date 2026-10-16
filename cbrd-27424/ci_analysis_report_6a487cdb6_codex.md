# PR7925: CI result with incomplete testcase evidence

Date: 2026-10-17, Asia/Seoul. Work Items 397 and 393.
Engine: `6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f`.

**Warning: this record supports no testcase-level regression or root-cause conclusion.**
The workflow finished with failure. GitHub reports both builds, SQL, and medium successful, and shell failed.
The collector cannot produce trustworthy testcase summaries because the shard marker contract differs from its expected contract.
Do not interpret missing summaries as zero failures or as failed SQL/medium testcases.

## Run and observed statuses

The agent posted exactly one [`/run all`](https://github.com/CUBRID/cubrid/pull/7925#issuecomment-6220855678) after publishing the source and completing focused checks.
All five contexts selected [run 38938588691](https://github.com/CUBRID/cubrid/actions/runs/38938588691), attempt 1.
The workflow reached its terminal failure result at about 03:00 KST.

| Check | GitHub status | Collector state | Testcase counts |
| --- | --- | --- | --- |
| Release build | SUCCESS | Outside testcase collection | Not applicable |
| Debug build | SUCCESS | Outside testcase collection | Not applicable |
| Medium | SUCCESS | `job_level_failure` | Unknown |
| SQL | SUCCESS | `job_level_failure` | Unknown |
| Shell | FAILURE | `job_level_failure` | Unknown |

All ten SQL shard jobs and the medium job succeeded.
Of the 50 shell shard jobs, 44 succeeded and six failed.
These are job results. They do not establish testcase totals or a complete testcase failure list.

| Failed shell shard | GitHub job |
| --- | --- |
| 30 | [Job 117103553048](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103553048) |
| 31 | [Job 117103552750](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103552750) |
| 36 | [Job 117103552509](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103552509) |
| 40 | [Job 117103552653](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103552653) |
| 44 | [Job 117103552843](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103552843) |
| 48 | [Job 117103552752](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103552752) |

The final `collect` job also failed.
This record does not assign the shell failures to the SA branch removal.

## Collection observation

Collector: `cubrid-ci 0.2.0 (16d7252122d1, release)`.
One delegated status snapshot and one exact-head collection with `--wait` ran for this cycle.
Collection returned exit 3 with an incomplete observation.
The result identifies the requested PR, source SHA, run, and attempt consistently.
The command result, manifest, observation request, and terminal observation pass their JSON schema and identity checks.
No requested suite has a complete trustworthy testcase summary.

Observation ID: `20261016T180137.135602229Z-1650129-0`.
The observation started at 03:01:37 KST and finished at 03:02:33 KST.
The local report-mode gate returns `warning`, with regression conclusions disabled.

The collector reports this diagnostic for each suite:

```text
CI pipeline failed before trustworthy testcase evidence: shard 00 has no ctp_rc
```

The retained shard markers contain `test_rc`, while the collector diagnostic requires `ctp_rc`.
The medium shard `00` marker contains this decisive excerpt:

```text
suite=medium
idx=00
assigned=975
test_rc=0
```

`assigned` describes the assignment. It does not establish how many cases executed or passed.
The same field-name difference appears in all 61 retained shard markers.
This observation explains the collection limit. It does not explain the six failed shell jobs.

| Acquisition ledger | Retained shards | Failed acquisition | Not attempted |
| --- | --- | --- | --- |
| Medium | 1 | 0 | 0 |
| SQL | 10 | 0 | 0 |
| Shell | 50 | 0 | 0 |

Retained means the response set reached local storage. It does not establish a suite verdict.
The request excluded binary collection. The observation consumed zero binary bytes.
Absent binary downloads do not establish absent provider artifacts.

## Input markers and evidence boundary

Every retained `build.read` names source `6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f`, debug mode, and run 38938588691, attempt 1.
Every medium/SQL `tc.read` names public TC `26f964b8a6e222c33765fa317eaaf4fe666d5f44` on `tc/pr-7925`.
Every shell `tc.read` names private TC `a261508a624efc7115ac181073d40bca7fc9448c` on that branch.
Independent marker checks cover all 61 retained shard directories.
These input markers do not replace complete testcase summaries or raw-summary reconciliation.

No new exact merge-base comparison ran because the head testcase evidence is incomplete.
The earlier [baseline report](ci_analysis_report_b755678cd_run38861566581_codex.md) concerns another engine revision and another run.
It does not establish attribution for this run.

The collector owns the retained bundle under:
`/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f`.

Separate read-only GitHub API evidence and local validation receipts remain under:
`/mnt/nvme/data-5/tmp/wi397-pr7925-20261017.FGB89ikS`.
Relevant files are `ci-run-latest.json`, `ci-checks-final.json`, `ci-collection.json`, `ci-validation.json`, `ci-input-markers.json`, and `ci-report-mode.json`.
The API evidence supplies job/status results because the collector cannot supply complete testcase results.
It does not upgrade the incomplete collector observation.

## Remaining gates and next direction

The next evidence step requires reconciling the collector and shard-marker contracts, then obtaining trustworthy summaries before failure attribution.
That is follow-up work requiring new direction under the one-cycle project policy.
The agent made no source fix, further source push, or CI rerun after this result.

[Public TC PR3679](https://github.com/CUBRID/cubrid-testcases/pull/3679) and [private TC PR4360](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4360) remain open at the revisions above.
The maintained project TC gate still requires human merge/closure disposition.
The live `gh pr checks --required` query reports no required checks for this branch.
The five gha-ci statuses above remain separate evidence. That query does not waive the project CI or TC policies.

[PR7927](https://github.com/CUBRID/cubrid/pull/7927) remains open at `9ba5b9b927e5c1820f2f9d7a6f7d9acfa447e773`.
Actual integration and combined acceptance remain pending under WI393.
The [preservation decision and local verification](sa-inline-preservation-decision-20261017.md) remain valid within their stated local scope.
