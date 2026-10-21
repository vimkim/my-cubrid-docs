# PR #8227 CI failure: confirmed check failures and incomplete SQL evidence

Date: 2026-10-21, Asia/Seoul. Author: `codex`.

The question is why [PR #8227](https://github.com/CUBRID/cubrid/pull/8227) failed CI. This report supports the author's next review and repair decision. It covers the three regression suites and the independent license and TC gate checks for Engine commit `15609d2a779e3082aafe5af576487ebbdc8d70f6`.

The license check rejected two new files without approved Apache headers. The TC gate rejected two open draft testcase PRs. The regression workflow reported SQL failure, but the collector rejected inconsistent SQL evidence on both the head and its exact merge base.

**Warning: this snapshot supports no SQL regression or testcase root-cause conclusion.** SQL has no validated failure inventory. The independent license and TC gate findings below use separate GitHub check evidence.

## Confirmed independent checks

### License headers

The [license job](https://github.com/CUBRID/cubrid/actions/runs/39541817707/job/119031051143) printed:

```text
3rdparty/build.sh: FAIL
3rdparty/tests/probe/main.cpp: FAIL
Process completed with exit code 1.
```

At the pinned commit, [build.sh](https://github.com/CUBRID/cubrid/blob/15609d2a779e3082aafe5af576487ebbdc8d70f6/3rdparty/build.sh#L1) starts with the shebang and implementation comments. [main.cpp](https://github.com/CUBRID/cubrid/blob/15609d2a779e3082aafe5af576487ebbdc8d70f6/3rdparty/tests/probe/main.cpp#L1) starts with includes. Both omit the required license header.

The [check implementation](https://github.com/CUBRID/cubrid/blob/15609d2a779e3082aafe5af576487ebbdc8d70f6/.github/workflows/check.yml#L25) checks changed `.sh` and `.cpp` files. It compares each file's leading lines with approved header templates and fails if none match.

This finding directly concerns files added by the PR. Confidence is high: the exact-head source and job output agree. A matching approved header in both tested files would disprove this explanation. The next action is to add the appropriate existing project headers. This check does not evaluate the bundled unixODBC distribution license.

### Open testcase PRs

The [TC gate job](https://github.com/CUBRID/cubrid/actions/runs/39541817580/job/119042802173) reported:

```text
TC Merge Gate FAILED — TC changes are not on TC develop yet
```

The subsequent read-only PR inspection found:

| Repository | TC PR | State | Changed files |
| --- | --- | --- | --- |
| `CUBRID/cubrid-testcases` | [#3826](https://github.com/CUBRID/cubrid-testcases/pull/3826) | Open, draft | 0 |
| `CUBRID/cubrid-testcases-private-ex` | [#4514](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4514) | Open, draft | 0 |

The [gate's open-PR rule](https://github.com/CUBRID/cubrid/blob/15609d2a779e3082aafe5af576487ebbdc8d70f6/.github/workflows/tc-merge-gate.yml#L61) blocks an open TC PR before checking branch file contents. Its message permits closure when the PR carries no change. The executed job log contains this rule.

This is a direct PR prerequisite, with high confidence. Closed or merged TC PRs at the failed check's evaluation time would disprove this explanation. The next action is human closure of both empty PRs. The check must subsequently evaluate the updated state. This investigation did not close PRs or trigger that evaluation.

## Regression snapshot and collection outcome

The [head regression run](https://github.com/CUBRID/cubrid/actions/runs/39541991227), attempt 1, concluded `failure`. Both build jobs passed. The reported failing jobs were `shard sql 09` and `collect`.

Collector: `cubrid-ci 0.2.0 (9536bd3c2867, release)`. The installed source checkout matches full tool commit `9536bd3c28670c9ed5ad721e9e84289f1b1d4ea4`.

One status command and one exact-head collection ran. Head collection finished at `2026-10-21T06:12:10.196495591Z`, with exit `4`. One exact merge-base collection also returned exit `4`.

| Requested suite | Head CI status | Head collection | Validated head counts | Exact-base collection |
| --- | --- | --- | --- | --- |
| `test_medium` | Success | Completed | 975 planned, run and passed, 0 failed, errors, skipped or unrun | Completed: 975 passed, 0 failed, errors, skipped or unrun |
| `test_sql` | Failure | `collection_failed` | Unknown, no validated suite summary | `collection_failed`, GitHub reports success, but no validated SQL summary exists |
| `test_shell` | Success | Completed | 3,470 planned/tests, 3,440 run/passed, 30 skipped, 0 failed, errors or unrun | Completed: 3,469 planned/tests, 3,439 run/passed, 30 skipped, 0 failed, errors or unrun |

Completed medium and shell summaries passed schema, run/attempt, Engine identity, count and raw-file digest checks. Their failure arrays are empty. This validates their own inventories and does not validate SQL.

## SQL integrity diagnostic

Both collector command results contain the same structured error:

```text
suite: test_sql
kind: integrity
diagnostic: identity_or_integrity
message: result identity mismatch: shard 01 workflow result and JUnit counts disagree
```

The collection stopped during SQL count reconciliation. This is an evidence validation failure, distinct from the reported CI job failure in SQL shard 09. It does not identify a failed testcase or explain that job's failure.

As a bounded diagnostic observation, both retained shard 01 markers state `assigned=3533` and `test_rc=0`. Each retained JUnit file contains 3,531 testcase elements. These observations do not establish why the workflow result and JUnit counts differ. This report does not promote SQL failure names, diffs or engine causes from the rejected bundle.

The analyzer's local report gate returned:

```json
{"mode":"warning","regression_conclusions_allowed":false,"comparison_scope":"none"}
```

The `cubrid-ci-analyze` workflow requires a bounded warning report for incomplete or unvalidated collections. Its instruction is to “write a bounded warning report and make no regression or root-cause conclusion.”

## Acquisition ledger and validation

Head observation: `20261021T061200.553108691Z-455546-0`.

Baseline observation: `20261021T061343.398287057Z-460757-0`.

Each terminal observation uniquely matches its saved command result, including the collection timestamp. Request/result schemas and observation IDs match. Head manifest/result v2 and baseline manifest/result v3 validate independently. Requested repository, PR/head relationship, suite sets and collection options reconcile.

| Bundle | Suite shard indices | Acquisition state |
| --- | --- | --- |
| Head and exact base | Medium `00` | Retained |
| Head and exact base | Shell `00` through `49`, inclusive | Every shard retained |
| Head and exact base | SQL `00` through `09`, inclusive | Every shard retained, SQL summary validation failed |

There are no failed or unattempted acquisition entries. “Retained” means the collector acquired the raw response set. It does not establish a SQL testcase verdict.

The SQL diagnostic occurred in local summary validation, with no failed remote endpoint recorded. The observation does not record an aggregate text-response byte budget. This collection requested no binary download. Binary consumption was zero, with the configured 536,870,912-byte budget untouched on each collection.

The validated raw indexes cover 28 medium files and 616 shell files per bundle. Verified head bytes are 559,390 and 1,696,017 respectively. Verified base bytes are 562,679 and 1,699,155 respectively. Summary digests, declared file lengths and SHA-256 values match.

## Exact merge-base limits

The baseline relationship observed at `2026-10-21T06:12:43.269702685Z` records:

- Head: `15609d2a779e3082aafe5af576487ebbdc8d70f6`.
- Target `develop` tip: `196a2a76ae476dd19c4b1aca9be923ea708f472d`.
- Exact merge base: `14b0b1cbd94c26860ea0ed006d8f928a90eec514`.
- Selected base execution: [run 39449080902](https://github.com/CUBRID/cubrid/actions/runs/39449080902), attempt 1.

Discovery covered all paginated exact-commit statuses and check runs. It did not scan repository-wide workflow history. Head and baseline requests select all three suites. Their completed medium and shell shards identify the requested Engine commits and `debug` build mode.

| Input | Head revision | Base revision |
| --- | --- | --- |
| Public TC repository, used by medium and retained SQL evidence | `15d7f1841068bca7b589d36a69b139326b3afb05` | `e0acb2ed3c458a359e3b6b30e371efe6909c6dcd` |
| Private TC repository, used by shell | `17729af4db9eca98a0049f963b98679aa68b92a2` | `fd2b7bb29f130315579241d61f5d23f28c7f81d8` |

Testcase inputs differ. This analysis establishes no affected SQL file equality or case-level coverage comparison. No SQL case receives `also_observed_on_base`, `additional_on_head`, or `base_only` classification. Their counts are unknown, rather than zero. The same collector diagnostic on the base does not prove the same SQL test failure existed there.

## Next actions

1. Add approved license headers to the two new source files.
2. Have the human close both unchanged TC PRs and verify the gate's subsequent result.
3. Reconcile the existing SQL workflow-result and JUnit counts in the producer/collector contract. Preserve the rejected evidence and exact execution identities.
4. Obtain a validated SQL summary and exact-base comparison before naming an engine regression or selecting a testcase reproduction.

SQL attribution remains unknown. This analysis changed no Engine or testcase source, triggered no CI, and published no report or JIRA update.

## Local evidence inventory

- Head bundle: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8227/15609d2a779e3082aafe5af576487ebbdc8d70f6`.
- Base bundle: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/14b0b1cbd94c26860ea0ed006d8f928a90eec514`.
- Saved commands, validation assessment and validation result: `/mnt/nvme/data-5/tmp/cubrid-ci-analysis-8227.jf0sf7gr/`.
- Independent check logs, run/job metadata, TC PR metadata and annotations: the same temporary directory's `misc-checks/` subdirectory. These files remain separate from collector-owned schema output.

The report uses the existing `CBRD-27712/` directory to preserve repository index and path conventions. Local task commits follow the user's Git workflow. Report publication requires a separate request.
