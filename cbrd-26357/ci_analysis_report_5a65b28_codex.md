# PR 7990: partition loader failure at `5a65b28`

Analysis date: 2026-10-26, Asia/Seoul. Audience: PR author and testcase reviewers.

## Finding and scope

`partition_tbls.sh` fails because its answer still expects an invalid partition value to load successfully. Confidence: high.
The engine rejects that value through partition validation added by [PR 7927](https://github.com/CUBRID/cubrid/pull/7927).
That change predates the recent conflict-resolution merge.

The requested analysis covers the shell suite, with detailed diagnosis limited to `partition_tbls.sh`.
The two CDC failures remain in the inventory. The user handles their disabling separately.
This analysis changes no engine code, testcase, CI definition, or remote PR state.

Keep the partition test enabled. Update its negative test to require rejection, then check rollback and a subsequent valid load.
The current CI output establishes the rejection and comparison failure. It does not independently establish the failed batch's stored row count.

## Snapshot and evidence identity

| Item | Exact identity or result |
| --- | --- |
| Engine PR | [7990](https://github.com/CUBRID/cubrid/pull/7990), `feature/oos-merge` to `develop` |
| Engine head | `5a65b28073f322bde6407e1754c0d27691de8f89` |
| Head execution | [39930102206, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/39930102206) |
| Consumed head build | Debug, producing run `39928884909`, attempt 1 |
| Head shell testcases | `fea33d9feaa991249188627a6516c5431bdfd847`, branch `tc/pr-7990` |
| Exact merge base | `c1dfe7e8719d254d61b33fc513d704f4f4f0a8b2` |
| Base execution | [39979262220, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/39979262220) |
| Consumed base build | Debug, producing run `39919677226`, attempt 1 |
| Base shell testcases | `c79be6f9cacc62108fcf755337f0f1321331b0a4`, branch `develop` |
| Workflow revision, both executions | `eb88ab4eab3f6ae28040d15606a884e1d3846269` |
| Collector | `cubrid-ci 0.2.0`, source `9536bd3c28670c9ed5ad721e9e84289f1b1d4ea4` |
| Chronicle | `cubrid-tcc 0.3.0` |

The single status snapshot reports successful release and debug builds, SQL, and medium.
Only shell evidence received full collection and validation in this analysis.
The other suite counts were not collected and are unknown here.

| Collected suite | State | Planned | Run | Passed | Failures | Errors | Skipped | Unrun |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Head `test_shell` | Completed, fail | 3486 | 3456 | 3453 | 3 | 0 | 30 | 0 |
| Base `test_shell` | Completed, pass | 3486 | 3456 | 3456 | 0 | 0 | 30 | 0 |

Both collections completed with exit 0. A red suite is a collected verdict, not an acquisition failure.
The manifests, command results, matching terminal observations, summaries, failures, and raw indexes passed schema and identity validation.
All 616 raw files in each bundle passed size and SHA-256 checks.
The head bundle contains 20,207,080 raw bytes. The base bundle contains 1,710,236 raw bytes.
This collection requested no binaries or cores.
The report-mode gate returned `full`, with comparison limited to validated cases.

## Failure inventory

All paths below are relative to `cubrid-testcases-private-ex`.

| Shard | Full testcase path | Observed signature | Baseline classification | Category, PR relation, confidence |
| --- | --- | --- | --- | --- |
| 08 | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | Delete extraction returns `rc=-10` after 81/700 target events. Update extraction returns `rc=-10` at 0/2400. | `additional_on_head`. Corresponding base case passes. | CDC extraction error. Causal PR relation unknown, confidence unknown. Detailed diagnosis excluded. |
| 11 | `shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh` | `partition_tbls-1 : NOK`. Output reports partition rejection while answer expects two successful inserts. `partition_tbls-2 : OK`. | `additional_on_head`. Corresponding base case passes. | Stale expected output. PR relation direct, confidence high. |
| 25 | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | `CONFIGS_OK=1` of 3. 8K and 16K configurations report extraction errors. Reported corruption is zero. | `additional_on_head`. Corresponding base case passes. | CDC extraction error. Causal PR relation unknown, confidence unknown. Detailed diagnosis excluded. |

Reconciliation: head failures 3, shared signatures 0, additional observed failures 3, uncomparable cases 0, base-only failures 0.
These classifications describe the observed pair. They do not establish an engine defect or CDC causality.

## Why the partition case fails

### Test responsibility and inputs

The script exercises three loader scenarios: a normal hash-partition load, an invalid range-partition load, and a periodic-commit load.
Its second scenario explicitly says it modifies the object file to generate an error.
It creates a table with one partition, inserts the valid value `1`, unloads it, and appends `100`.
It then recreates the database and invokes server-side `loaddb -C`.

```sql
create table t(i int)
partition by range(i) (partition p0 values less than (10));
```

The appended value has no valid partition.
See the pinned [script, lines 47–60](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/fea33d9feaa991249188627a6516c5431bdfd847/shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh#L47).

The pinned [Linux answer, lines 40–50](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/fea33d9feaa991249188627a6516c5431bdfd847/shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/bug_bts_11093.answer#L40) still expects:

```text
dba.t__p__p0 2 instances committed
Total 2 object(s) inserted, 0 object(s) failed.
```

The actual CI diff instead contains:

```text
Line 6:Appropriate partition does not exist.
Total 0 object(s) inserted, 1 object(s) failed.
```

The script compares the combined loader output at line 75, so this intentional rejection makes assertion 1 fail.
The diff also lacks the successful test2 statistics and closing messages expected after a commit.
The 40-row and 10,000-row successful load totals match their answers.
Assertion 2, the final schema and row-count comparison, reports `OK`.
The observed failure is therefore localized to test2's expected behavior.

### Engine responsibility and changed call path

The loader must select or validate the destination partition before inserting each partitioned row.
At the head revision, `start_attrinfo()` determines whether the target is a parent or a child partition.
It stores `DB_PARTITIONED_CLASS` or `DB_PARTITION_CLASS` in `m_pruning_type`.
See [load_server_loader.cpp, lines 1217–1227](https://github.com/CUBRID/cubrid/blob/5a65b28073f322bde6407e1754c0d27691de8f89/src/loaddb/load_server_loader.cpp#L1217).

`flush_records()` sends partitioned rows through `locator_insert_force()` with that pruning type and a pruning context.
It selects the single-row operation for those rows.
See [lines 815–837](https://github.com/CUBRID/cubrid/blob/5a65b28073f322bde6407e1754c0d27691de8f89/src/loaddb/load_server_loader.cpp#L815).

The locator calls `partition_prune_insert()` when the pruning type indicates a partitioned class.
See [locator_sr.c, lines 5034–5044](https://github.com/CUBRID/cubrid/blob/5a65b28073f322bde6407e1754c0d27691de8f89/src/transaction/locator_sr.c#L5034).
The partition code returns `ER_PARTITION_NOT_EXIST` when the value cannot select one partition.
See [partition.c, lines 3529–3546](https://github.com/CUBRID/cubrid/blob/5a65b28073f322bde6407e1754c0d27691de8f89/src/query/partition.c#L3529).

The loader error path reports failure and aborts the row's system operation.
An unfiltered session failure stops further processing.
See [load_server_loader.cpp, lines 838–848](https://github.com/CUBRID/cubrid/blob/5a65b28073f322bde6407e1754c0d27691de8f89/src/loaddb/load_server_loader.cpp#L838).
The retained CI output reports zero inserted objects, but this script does not query both tables after test2.
Do not infer complete rollback verification from that printed count alone.

### Origin and causal assessment

`git log -S m_pruning_type` identifies `3252fcffce9762641fb9ae6f4a5d8ae89affc738`, [PR 7927](https://github.com/CUBRID/cubrid/pull/7927).
That commit added the partition classification and row-routing path for deferred OOS writes.
Its parent is the previously tested `1a8c7057623d92205dbc1324ec43e3cc40fc4cd2`.
The merge base still uses a hard-coded pruning type of zero in this loader.

The loader difference between pre-conflict head `c451a5739b7b8be6f4ddc82e7caaadc18d5e268e` and tested head `5a65b28` changes only a catalog attribute index.
It does not add this partition-validation behavior.

**Inference:** the direct cause of the red assertion is an answer that preserves the old validation bypass.
The engine's new rejection is consistent with the partition definition and the script's own negative-test comment.
Confidence is high. This is a testcase compatibility change associated with the PR's loader behavior.

**Unknowns:** this analysis did not reproduce the case locally, inspect a live database after the rejected batch, or validate Windows execution.
The consumed CTP helper revision is not independently pinned here.

**Falsifier:** a controlled run could reject an in-range value, retain rows after the failed batch, or fail the subsequent valid load.
Those findings would establish an additional engine problem.
Any such finding would invalidate treating an answer update as the complete remedy.

**Next action:** preserve test2's invalid input and add explicit failure, row-count, and recovery assertions before refreshing its answers.

## Exact baseline comparison

The baseline wrapper records PR 7990 head `5a65b28`, target `develop`, and target tip and merge base `c1dfe7e8`.
Its relationship observation time is `2026-10-26T06:22:04.204600121Z`.
It discovers runs from all paginated exact-commit statuses and checks, without a repository-wide workflow scan.
It selected existing dispatch run `39979262220`, attempt 1. This analysis triggered no baseline run.

The head case fails in shard 11. The baseline case passes in shard 30.
Both use debug builds and the same workflow revision.
All four files under `partition_tbls` are byte-identical across head testcases, base testcases, and earlier PR testcase revision `28ffb736`.
The shared tree object is `d1049baa6b43d45cc16cd0660af85bea48a8102a`.
The script blob is `8bcc57385d53a90a2a281ec82c6996e17039b7d5`.
The Linux answer blob is `46815e7bb7e8ac030390668f91145d929df448d4`.

Both CDC case directories also have equal Git tree objects in the head and baseline testcase commits.
Their baseline records pass. Their underlying causes remain outside the requested detailed diagnosis.
Equal case files do not establish identical random payloads, scheduling, configuration, or CTP helper bytes.
The observed comparison identifies additional failures, while the source trace supports the partition case's causal explanation.
Whole-repository testcase equivalence is not claimed.

## Testcase history

Chronicle initially lacked run `39930102206`. One bounded shell-only refresh added its retained records.
The selected partition occurrence is execution `12425`, shard 11, ordinal 1, at engine `5a65b28` and testcases `fea33d9f`.
Its JUnit digest is `031587c67be73f895acf414de5b44b8adadd944cadda38037da56cc3f9eebce6`, locator `testcase[62]`.
Chronicle leaves attempt and job attribution unresolved and marks this shard partial because CTP reported failure.
The independently validated collector provides the current attempt and complete suite inventory.

`explain` reports `SEEN_BEFORE` for this testcase identity.
Its earlier failure is run `38687274058`, execution `7179`, engine `71ae9f3f615cf09025c6a29ed9841b2ad9ecaa43`, testcases `54033447bdbd81126d2b5af6fd5bbc2847f2f6f2`.
That earlier JUnit digest is `bc800728dc659cc9071c0a7ed11c83230d7a4bd9e51038842210e264dbc7274e`, locator `testcase[54]`.
Hash-verified earlier evidence shows output-order differences, while test2 still commits two objects successfully.
It does not contain the current partition-rejection signature.
The earlier failure therefore does not establish recurrence of this cause.

An indexed previous PR run `39589070215` passes at engine `1a8c7057` and testcases `28ffb736`.
That run predates the loader-routing change. Its equal partition testcase files help explain the changed expectation boundary.
Historical execution ordering alone does not establish Git ancestry. The source history supplies the parent relationship above.

Chronicle's flakiness assessment is `UNKNOWN`, with no comparable mixed-outcome contexts.
The index reports stale and incomplete discovery despite the selected-run refresh.
Historical counts describe retained observations only. They do not prove the first occurrence or flakiness.
Both CDC history queries report earlier failures, but their symptom histories were not analyzed here.

Related historical context: [the earlier develop probe](../partition-loader/develop-partition-tc-ba88e470_codex.md) demonstrates the old invalid-row acceptance at `ba88e470`.
[CBRD-27441 documentation](../cbrd-27441/CBRD-27441-validate-partition-range-server-loaddb_109f16a_claude.md) describes a separate proposed repair and stronger testcase checks.
Those reports retain their original revision limits. The introducing change identified for this head is PR 7927.

## Recommended repair and verification

1. Keep `partition_tbls.sh` active and preserve its invalid `100` input.
2. Capture the invalid loader command's exit status and require a failure plus the partition error.
3. Query the parent and child partition immediately after failure. Require zero rows in both for this uncommitted batch.
4. Load the preserved valid input again. Require success and exactly one `i = 1` row through both table names.
5. Refresh the Linux and Windows test2 answers or separate the negative scenario from the successful-output comparison.
6. Preserve test1, test3, and the final schema and 10,000-row assertions. Run the focused native shell testcase before publication.

These changes remain proposals. No testcase repair, CI rerun, remote comment, or publication occurred during this analysis.

## Retained evidence and checks

Analysis working evidence: `/home/vimkim/tmp/pr7990-partition-analysis-gmv0yh4b`.

- `status.json`: single pinned status snapshot, including uncollected SQL and medium status observations.
- `head-result.json`, `base-result.json`, corresponding exit files: collector results.
- `validation.json`, `validate_bundles.py`, `assessment.json`: schema, identity, digest, count, and report-mode checks.
- `case-comparison-records.json`, `partition-input-equivalence.json`, `failed-case-input-trees.json`: exact case records and Git object equality.
- `partition-*-refreshed.json`, `history-refresh.json`, `history-coverage.json`: bounded Chronicle queries and coverage.
- `partition-history-evidence-index.json`, `partition-earlier-junit.xml`, `partition-earlier-message.txt`: hash-verified earlier symptom evidence.
- `cbrd_27064-history-*.json`, `cbrd_27075-history-*.json`: inventory-only CDC history queries.

Head bundle root:
`/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7990/5a65b28073f322bde6407e1754c0d27691de8f89`.
Its matching observation is `20261026T062139.914722342Z-3701388-0`.
The suite summary is `providers/github-actions/runs/39930102206/attempts/1/test_shell/summary.json` beneath that root.
The partition failure has stable ID `shell_35_cherry_issue_21654_server_side_loaddb_partition_tbls_cases_partition_tb-9e01a2a475`.
Read its `metadata.json`, `message.txt`, and `diff.txt` under the suite's `failures` directory.

Base bundle root:
`/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/c1dfe7e8719d254d61b33fc513d704f4f4f0a8b2`.
Its matching observation is `20261026T062305.021006950Z-3705662-0`.
The suite summary is `providers/github-actions/runs/39979262220/attempts/1/test_shell/summary.json` beneath that root.

Checks: both bundle validators and the report-mode gate passed. Counts and all three failure records reconcile.
Pinned Git objects establish testcase equality and source lineage. Report links, index entry, and Git whitespace checks receive local verification before commit.
Engine and testcase worktrees remain unchanged.
