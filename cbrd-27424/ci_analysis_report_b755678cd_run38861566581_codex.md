# PR7925: full CI after the testcase updates

Date: 2026-10-16, Asia/Seoul. Work Item: 393. Related review: Work Item 397.

**The requested full run finished with three shell testcase failures.**
Both build checks passed. Medium and SQL passed every executed case.
The collector completed successfully. Its complete evidence includes the failed testcases.
This result does not satisfy CI acceptance.

One failed case also fails on the exact merge-base baseline.
Two failed cases pass there, but different execution conditions prevent a causal conclusion.
The reviewed source remains unchanged. This run does not test removal of the SA preservation branch.
See the [separate review assessment](review-comment-4257963742_b755678cd_ste.md) for that proposal and its tradeoffs.

## Run and inputs

The user requested one `/run all` before further source work.
I posted the [request comment](https://github.com/CUBRID/cubrid/pull/7925#issuecomment-6209558975) at 15:30:07 KST.
All five CI contexts selected [run 38861566581, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/38861566581).
The terminal workflow verdict is failure.

| Input | Exact revision |
| --- | --- |
| Engine, `vimkim/cubrid:CBRD-27424-oos-loaddb-sa` | `b755678cd9a3ab465215228d5664f7f1edf24846` |
| Public TC, `CUBRID/cubrid-testcases:tc/pr-7925` | `26f964b8a6e222c33765fa317eaaf4fe666d5f44` |
| Private TC, `CUBRID/cubrid-testcases-private-ex:tc/pr-7925` | `a261508a624efc7115ac181073d40bca7fc9448c` |

Every retained shard records these engine and applicable TC revisions.
The suites used the debug build produced by [run 37747856853, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/37747856853).
The build checks in the new run passed through artifact reuse. They do not establish a fresh compilation in this run.

## Complete head inventory

Each suite below completed in run 38861566581, attempt 1.
The skipped column is separate from executed cases. No planned case remains unrun.

| Suite | State | Verdict | Planned | Executed | Passed | Failed | Errors | Skipped | Unrun |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Medium | completed | pass | 975 | 975 | 975 | 0 | 0 | 0 | 0 |
| SQL | completed | pass | 17,471 | 17,471 | 17,471 | 0 | 0 | 0 | 0 |
| Shell | completed | fail | 3,289 | 3,259 | 3,256 | 3 | 0 | 30 | 0 |
| Total | completed | fail | 21,735 | 21,705 | 21,702 | 3 | 0 | 30 | 0 |

The shell matrix has 50 shards. Two shards failed. They contain all three testcase failures.
The ten SQL shards and one medium shard passed.
The workflow's `collect` job failed because the test results contain failures.
The separate local evidence collection returned exit zero with complete summaries.

| Full testcase path | Shard | Result | Observed signature | Baseline classification | Category | PR relation | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `shell/_06_issues/_18_1h/bug_bts_14305/cases/bug_bts_14305.sh` | 14 | failure | Expected interruption diagnostics are absent from the background query output | `uncomparable` | Transaction interruption assertion | unknown | High for the failed assertion, low for cause |
| `shell/_06_issues/_15_1h/bug_bts_15489/cases/bug_bts_15489.sh` | 44 | failure | Index `total_pages=107` exceeds the expected limit below 100 | `uncomparable` | Index capacity after deletion | unknown | High for the measured value, low for cause |
| `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | 44 | failure | DELETE and UPDATE extraction return `rc=-10` before the target counts | `also_observed_on_base` | CDC extraction | unknown | High for the shared error category, low for a common cause |

Head failures reconcile as follows: one also observed on base, zero classified additional, and two uncomparable.
Four separate failures appear only in the selected baseline run.
The additional count is a classification result. It does not prove that this PR introduces no failures.

## Failure assessment

### Transaction interruption: bug_bts_14305

**Observed:** The script starts 200,000 literal queries in a background CSQL process.
It creates a DBA user, issues `kill 1`, and waits for the query process to end.
The kill acknowledgment and user-creation assertions pass.
The expected interruption-message count is zero, so the first assertion fails.
The internal-error count is zero. The testcase lasts about 22 seconds.

**Inference:** Completion timing or diagnostic selection could explain the missing message.
The retained trace does not distinguish these possibilities from an interruption defect.
PR relation remains unknown because the evidence does not connect this assertion to a changed function.

**Unknown:** The retained message does not contain the complete background `result1.log` contents.
The baseline case passes, but runner timing and process scheduling are not matched.

**Falsifier:** A retained background log showing an interrupted active transaction without the expected diagnostic would weaken the normal-completion explanation.
**Next action:** If directed, retain that log and session identity during a focused reproduction before changing the engine or assertion.

### Index capacity: bug_bts_15489

**Observed:** The script creates a database with 4K pages, inserts 46,000 rows, and deletes them.
After a 60-second wait, the index reports 107 pages.
The assertion requires a positive page count below 100.
The internal-error count is zero. The testcase lasts about 68 seconds.

**Inference:** Cleanup progress or page allocation behavior could affect this result.
The artifact establishes the threshold failure, not its mechanism.
PR relation remains unknown. The baseline case passes with the same tracked testcase subtree.

**Unknown:** The evidence does not establish matched vacuum progress, runner load, or an engine change responsible for the page count.
**Falsifier:** Repeated matched runs that finish cleanup and reproduce a head-only page count would weaken the timing explanation.
**Next action:** If directed, compare allocation and vacuum state in matched focused runs. Preserve the existing threshold and wait period.

### CDC extraction: cbrd_27064

**Observed:** INSERT extraction reaches 700/700 with extractor exit zero.
DELETE stops at 19/700. UPDATE stops at 4/2,400.
Both failing phases report `EXTRACT_ERROR: rc=-10` and extractor exit one.
Both report a zero corruption counter. Neither reports timeout exit 124.
The second and third assertions fail.

The exact baseline also reports `rc=-10` in both phases.
Its DELETE count is 23/700. Its UPDATE count is 0/2,400.
These differences prevent a claim that the executions or underlying causes are identical.

**Inference:** The shared extraction-error category supports a separate existing CDC investigation.
It does not establish that PR7925 cannot affect the failure.
PR relation and the underlying cause remain unknown.

**Unknown:** The retained artifacts do not identify which source condition produced the extractor error.
A zero corruption counter does not establish successful extraction or correct historical values.

**Falsifier:** A matched reproducer that isolates a changed PR7925 path as necessary would establish a stronger PR relation.
**Next action:** If directed, retain extractor diagnostics and compare the failing log position on both engine revisions.
Keep this case and `cbrd_27075` enabled under the [accepted CDC history decision](../../cubrid-oos-context/docs/adr/0005-defer-oos-history-from-the-11-5-merge.md).
The shared signature grants no CI waiver.

## Exact baseline and comparison limits

The baseline collector resolved this relationship at 16:30:06 KST.

| Identity | Value |
| --- | --- |
| PR | [CUBRID/cubrid#7925](https://github.com/CUBRID/cubrid/pull/7925) |
| Pinned head | `b755678cd9a3ab465215228d5664f7f1edf24846` |
| Target | `feature/oos-merge` |
| Observed target tip and exact merge base | `fb567a629cdb390fff920542173fa36f454c74a0` |
| Selected suite run | [36570256001, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/36570256001) |
| Consumed debug build run | [36570061594, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/36570061594) |
| Public TC | `bdba62aee0faec05abdd861518824c69b6c1b3c5`, `tc/pr-7990` |
| Private TC | `c4b9d482fbd491a68510b2552df2c3cac91911fc`, `tc/pr-7990` |

Discovery covered all paginated statuses and checks linked to that exact engine commit.
It did not scan repository-wide workflow history.
The selected workflow title mentions PR7990. Verified shard provenance establishes the baseline engine identity.

Baseline medium passes 975/975. Baseline SQL passes 17,471/17,471.
Baseline shell has 3,289 planned, 3,259 executed, 3,254 passed, five failed, and 30 skipped cases.
It has zero errors and zero unrun cases.

The baseline's four other failures have explicit passing JUnit records on the head:

- `shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases/hide_cubrid_replay.sh`
- `shell/_06_issues/_15_1h/bug_bts_15156/cases/bug_bts_15156.sh`
- `shell/_40_guava/cbrd_26349/cases/cbrd_26349.sh`
- `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh`

The baseline has explicit passing records for bug_bts_14305 and bug_bts_15489.
All seven affected testcase subtrees are identical between the recorded private TC revisions.
This comparison includes their tracked cases, answers, and sibling resources.

Both engine builds use debug mode. The suite sizes and skip counts match.
However, the runs occurred on different dates with different engine builds and TC branch revisions.
The evidence does not establish equal runner load, scheduling, random payloads, or every effective runtime setting.
This report does not assert equivalent CTP revisions.
These limits support the two `uncomparable` classifications and constrain the shared CDC comparison to its observed signature.

## Testcase updates and remaining gates

The new run consumed both published TC updates.
JUnit records explicitly pass these three medium cases:

- `medium/_02_xtests/cases/to_char_order_by.sql`
- `medium/_02_xtests/cases/to_number_order_by.sql`
- `medium/_02_xtests/cases/to_timestamp_order_by.sql`

The shell record also explicitly passes `shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh`.
These records check the selected testcase updates. They do not establish every future combined implementation's behavior.

At the final metadata check, [PR7927](https://github.com/CUBRID/cubrid/pull/7927) remains open at `9ba5b9b927e5c1820f2f9d7a6f7d9acfa447e773`.
Its actual shared integration remains pending.
The [public TC PR3679](https://github.com/CUBRID/cubrid-testcases/pull/3679) and private TC PR4360 remain open at the revisions listed above.
TC Merge Gate still requires their human disposition before the engine PR can merge.
The agent did not merge or close either TC PR.

The next decisions are the remaining shell investigations and the separate SA preservation-contract proposal.
The standing workflow stops after this run's result. No further source correction, push, or CI rerun occurred.

## Evidence validation and retained files

The collector version is `cubrid-ci 0.2.0 (16d7252122d1, release)`.
Its source revision is `16d7252122d185dc8866c99598644dd974044bd2`.
Head collection completed at 16:28:43 KST. Baseline collection completed at 16:31:19 KST.

The head observation is `20261016T072829.154840051Z-3201074-0`.
The baseline observation is `20261016T073102.603203024Z-3589093-0`.
Both are complete and match their saved terminal command results.
Schema checks cover both manifests, observations, all suite summaries, raw indexes, and failure metadata.
Count checks reconcile every suite and failure inventory.
Every shard's build provenance matches its selected engine commit.
Independent size and SHA256 checks passed for 780 indexed head files and 780 indexed baseline files.
The report-mode gate permits a full head report with comparisons limited to checked cases.
That permission does not establish regression causality.

Evidence root:

```text
/mnt/nvme/data-5/tmp/pr7925-ci-review-20261016.yk6yokqp
```

| Retained file or directory | Purpose |
| --- | --- |
| `trigger-receipt.json`, `run-terminal.json`, `checks-final.json` | Request, selected workflow, and terminal checks |
| `collector-status.json` | The single delegated head status snapshot |
| `head-result.json`, `base-result.json` | The successful head and exact-baseline acquisition results |
| `head-validation.json`, `base-validation.json`, `validate-collection.py` | Schema, identity, count, path, and raw-file validation |
| `case-comparison.json` | Positive JUnit records and seven tracked-subtree comparisons |
| `report-mode-assessment.json`, `report-mode-result.json` | Checked facts and the report-mode decision |
| `validated-snapshots/` | Copies of both selected manifests and observation pairs |
| `collector/github-actions/CUBRID-cubrid/` | Complete selected summaries, raw responses, messages, and diffs |
| `dependency-final.json`, `public-tc-final.json`, `private-tc-final.json` | Final dependency and TC status snapshots |

One initial invocation rejected `--poll-interval 60` before acquisition.
The retained argument-error files distinguish it from the single successful head observation, which uses `60s`.
There was no second head observation to replace an unfavorable result.
Raw downloads and local caches remain outside the documentation repository.

The acquisition commands were:

```bash
CI_REVIEW_EVIDENCE=/mnt/nvme/data-5/tmp/pr7925-ci-review-20261016.yk6yokqp
cubrid-ci status 7925 --json
cubrid-ci collect https://github.com/CUBRID/cubrid/pull/7925 \
  --commit b755678cd9a3ab465215228d5664f7f1edf24846 \
  --wait --poll-interval 60s --data-dir "$CI_REVIEW_EVIDENCE/collector" --json
cubrid-ci collect-base https://github.com/CUBRID/cubrid/pull/7925 \
  --data-dir "$CI_REVIEW_EVIDENCE/collector" --json
```

The head shell summary contains each failure's full message path, diff path, and message SHA256.
Those checked files support the signatures above.
The earlier focused checks remain documented in the [review assessment](review-comment-4257963742_b755678cd_ste.md).
Neither those checks nor this full run execute the proposed branch removal.
