# PR #7927: validated CI failure inventory and baseline alignment

Updated 2026-09-30 KST. This report supersedes the earlier warning-only snapshots, retained in Git history.

## Decision

**The 14 failures are not all ordering failures.** Three medium cases show row permutations. Nine cases have obsolete testcase expectations; the remaining two are CDC extraction failures also observed on the latest OOS integration run. No engine ordering repair is established yet.

The user requested preserving existing unordered SELECT behavior and explicitly rejected adding ORDER BY merely to make these tests pass. The next controlled experiment aligns both testcase branches exactly to the latest OOS baseline and merges that engine baseline into PR #7927 before a fresh full CI run.

## Validated evidence

- PR engine: `34a9072a19fdd5baf420273992c136119e719503`, [run 36102128913](https://github.com/CUBRID/cubrid/actions/runs/36102128913), attempt 1.
- Current integration engine: `fb567a629cdb390fff920542173fa36f454c74a0`, [run 36570256001](https://github.com/CUBRID/cubrid/actions/runs/36570256001), attempt 1. This is newer than the PR's exact pre-change base `b8f3c4807470dbeb30b5113acb7dd99d2340347c`; it is not an exact-parent control.
- Collector: `cubrid-ci 0.2.0 (45944012aaaa, release)`; PR collection at `2026-09-29T23:28:58.248231891Z`, integration collection at `2026-09-29T23:31:28.133735372Z`.
- Each collection has a matching schema-valid terminal observation, command and manifest equality, summary identities/counts, metadata and declared files. All 780 raw files per bundle pass length and SHA-256 verification. The executable report gate permits `full` for both bundles.
- Installation first encountered the old incompatible cache. That failed attempt is retained separately in `pr7927-20260930-evidence/result.json`; a new evidence root reacquired the remote data without altering the old bundle.
- PR testcase revisions: public `7fb227854a00daca5a3ccd3a74160de4b7e1254a`, private `018fc45bb12a63d24f4d85315790437cbf7cdaae`.
- Integration testcase revisions: public `bdba62aee0faec05abdd861518824c69b6c1b3c5`, private `c4b9d482fbd491a68510b2552df2c3cac91911fc`.
- Exact testcase source objects for all failures are available locally. No binary/core collection was requested.

| Run | Suite | Planned | Run | Passed | Failures | Errors | Skipped |
|---|---|---:|---:|---:|---:|---:|---:|
| PR | test_medium | 975 | 975 | 972 | 3 | 0 | 0 |
| PR | test_shell | 3286 | 3256 | 3246 | 10 | 0 | 30 |
| PR | test_sql | 17466 | 17466 | 17465 | 1 | 0 | 0 |
| Integration | test_medium | 975 | 975 | 975 | 0 | 0 | 0 |
| Integration | test_shell | 3289 | 3259 | 3254 | 5 | 0 | 30 |
| Integration | test_sql | 17471 | 17471 | 17471 | 0 | 0 | 0 |

## All PR failures

| Suite / testcase | Observed signature | PR relation / confidence |
|---|---|---|
| `medium/_02_xtests/cases/to_char_order_by.sql` | Unordered conversion SELECT returns a different permutation | unknown / high confidence in symptom, causal attribution pending |
| `medium/_02_xtests/cases/to_number_order_by.sql` | Unordered conversion SELECT returns a different permutation | unknown / high confidence in symptom, causal attribution pending |
| `medium/_02_xtests/cases/to_timestamp_order_by.sql` | Unordered conversion SELECT returns a different permutation | unknown / high confidence in symptom, causal attribution pending |
| `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | CDC extraction errors at all three page sizes | unlikely / high (also observed on integration) |
| `shell/_06_issues/_15_1h/bug_bts_15912/cases/bug_bts_15912.sh` | Extra `upgradedb` utility entry | unlikely / high (stale answer) |
| `shell/_32_features_930/issue_12504_show_log_header/_01_show_log_header/_02_relative_path/_01_csql/cases/_01_csql.sh` | Extra `System_metadata_version` field | unlikely / high (stale answer) |
| `shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh` | Old OOS error numbers in call-stack activation list answer | unlikely / high (stale answer) |
| `shell/_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh` | Old OOS error numbers in call-stack activation list answer | unlikely / high (stale answer) |
| `shell/_32_features_930/issue_12504_show_log_header/_01_show_log_header/_03_absolute_path/_01_self_log/cases/_01_self_log.sh` | Extra `System_metadata_version` field | unlikely / high (stale answer) |
| `shell/_06_issues/_25_1h/cbrd_25478/cases/cbrd_25478.sh` | Extra `System_metadata_version` field | unlikely / high (stale answer) |
| `shell/_32_features_930/issue_12504_show_log_header/_01_show_log_header/_01_basic_log/cases/_01_basic_log.sh` | Extra `System_metadata_version` field | unlikely / high (stale answer) |
| `shell/_06_issues/_15_1h/bug_bts_16378/cases/bug_bts_16378.sh` | Extra `System_metadata_version` field | unlikely / high (stale answer) |
| `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | CDC delete/update extraction returns -10 | unlikely / high (also observed on integration) |
| `sql/_33_elderberry/cbrd_23844/cbrd_24337/cases/cbrd_24337.sql` | `create table _db_class`: expected -494, actual -493 | unlikely / high (stale answer) |

## Attribution and falsifiers

### Nine stale expectations — separate from ordering

**Observed:** The exact failed testcase revision differs from both the current PR testcase branch and integration testcase branch at the relevant expected output. The current answers add `upgradedb`, include/normalize `System_metadata_version`, expect -493 for `create table _db_class`, and replace OOS activation-list error numbers -1382/-1384/-1385 with -1383/-1385/-1386. The defining engine files (`src/base/error_code.h`, `src/base/system_parameter.c`, `src/parser/show_meta.c`, `src/transaction/log_manager.c`) are unchanged between exact base b8f3c4807 and PR head `34a9072a1`. The latest integration run does not list these nine failures.

**Inference:** These nine reported mismatches arise from stale testcase expectations, not SELECT order; a deferred-write regression is unlikely (high confidence). The PR itself does not introduce the printed constants or metadata field.

**Unknown:** No new local replay of all nine shell/SQL cases was performed in this session. **Falsifier:** They continue to produce the same mismatches when the exact synchronized TC revisions run on the aligned engine. **Next action:** Inspect the freshly authorized full CI results using recorded testcase identities.

### Two CDC failures — inherited integration scope

**Observed:** Both exact testcase directories are unchanged between the recorded PR and integration revisions. Both runs show extraction errors for cbrd_27064 and cbrd_27075; cbrd_27064 returns -10 for delete/update extraction, and cbrd_27075 records extraction errors across 4K/8K/16K pages. The normative OOS context explicitly defers durable CDC history and leaves these cases enabled.

**Inference:** The failures are unlikely to be introduced by this PR (high confidence for baseline overlap, not a fresh root-cause proof). **Unknown:** Exact-parent runtime reproduction and internal CDC failure sites remain outside this comparison. **Falsifier:** Matched base/head executions isolate a new PR-only CDC failure mechanism. **Next action:** Keep these visible and report any changed signature independently.

### Three medium permutations — still require matched reproduction

**Observed:** to_char_order_by, to_number_order_by, and to_timestamp_order_by each insert five small values and compare an unordered conversion SELECT before their explicitly ordered queries. The entire medium/_02_xtests directory has no diff between the failed testcase revision, current PR testcase branch, and current integration testcase branch. The integration run passes all 975 medium cases; the PR run fails these three.

**Inference:** The symptom is real, but the two CI runs differ in engine revision and execution context. These observations do not isolate a deferred-write cause. PR relation unknown. **Falsifier for a PR-only explanation:** A matched exact-base/head run yields identical unordered outputs. **Next action:** Use the aligned CI run, then reproduce any remaining permutations with identical database initialization and testcase order; compare record bytes, OIDs/page placement and the actual query path before proposing an engine change. Do not change ORDER BY or expected row order as a workaround.

## Current base has five shell failures

The newest integration run has five failures, not only two CDC failures. In addition to cbrd_27064 and cbrd_27075, it records hide_cubrid_replay (masking-output difference), bug_bts_15156 (NOK), and cbrd_26349 (DBLink authentication/error-output differences). These three are not in the 14-failure PR inventory and are not attributed to this PR. Medium and SQL pass completely.

## Testcase synchronization

The user-supplied checker fetched published refs and found both PR testcase branches 15 integration-only commits behind, with 2 TC-only commits. The failed run predates even those PR tips: it tested `7fb227854`/`018fc45bb`, whereas the pre-reset published tips were `9fae5aa61`/`44a541c78`.

At the user’s explicit instruction, both local and published `tc/pr-7927` branches were reset to their corresponding `origin/feature/oos-merge` tips. Force pushes used exact leases. Backup branches `backup/pr7927-before-reset-20260930-local` and `backup/pr7927-before-reset-20260930-published` retain the previous local and published tips in each TC repository. The post-reset checker passes with TC-only=0 and OOS-only=0 for both.

This removes the PR-specific testcase commits from the new comparison, including its partition-loader expectation adjustment. A failure caused by that deliberately removed expectation must be distinguished from an engine regression.

## Evidence inventory

- PR bundle: `/home/vimkim/.local/share/cubrid-ci-data-observation-v1/github-actions/CUBRID-cubrid/pr-7927/34a9072a19fdd5baf420273992c136119e719503`
- Integration bundle: `/home/vimkim/.local/share/cubrid-ci-data-observation-v1/github-actions/CUBRID-cubrid/pr-7990/fb567a629cdb390fff920542173fa36f454c74a0`
- Each bundle: observations/<id>/{request,result}.json; manifest.json; providers/github-actions/runs/<run>/attempts/1/<suite>/summary.json; raw/index.json; failures/<stable_id>/{metadata.json,message.txt,diff.txt}.
- Committed companion receipts: `pr7927-20260930-evidence/` contains result/assessment/inventory records, testcase comparisons, and before/after sync output. Full raw evidence remains in the local collector store.
- Local medium attempt on `34a9072a1`: `/home/vimkim/tmp/pr7927-ordering/head-01`; native contained runner verified all 444 cases in the complete `_02_xtests` directory passed. All three ordering result files are byte-identical to their unchanged answers. This is not a full 975-case CI replay or an exact-base pair. Contained archive ownership warnings occurred, but all required verdict artifacts passed verification. The archive SHA-256 is recorded in the companion evidence.

## Engine baseline merge

The user authorized merging `origin/feature/oos-merge` into the PR workspace and retriggering CI. Merge `9232f111a7e7b6c71dbfa451db2812ae14766041` has parents `34a9072a1` and `fb567a629` and completed without conflicts. The stable patch ID of the PR-only diff is identical before and after merge (`0f31161dac4d8ba7ebc5aa59514fb1afb0f0826a`), preserving the deferred-write change while updating the baseline. The original workspace was fast-forwarded to this merge; its existing submodule working contents and `repro.sh` were verified unchanged.

## Aligned CI handoff

- Debug build and installation passed for merged engine `9232f111a`; all 35 configured CTest targets passed in 198.61 seconds. PR-only diff whitespace check passed.
- Pushed `vimkim/cubrid:feat/oos-deferred-write` to `9232f111a7e7b6c71dbfa451db2812ae14766041`.
- Posted exactly one [`/run all`](https://github.com/CUBRID/cubrid/pull/7927#issuecomment-5901188637) after checking that no same-PR run was active and no competing trigger had appeared.
- Pickup verified in [run 36646767174](https://github.com/CUBRID/cubrid/actions/runs/36646767174): both debug/release builds and medium/SQL/shell contexts are pending on the pushed head. No stable gha-ci context is missing. `gh pr checks --required` reports no required checks for this branch; this does not imply CI passed.
- Expected TC inputs are public `bdba62aee0faec05abdd861518824c69b6c1b3c5` and private `c4b9d482fbd491a68510b2552df2c3cac91911fc`. Validate the actual checkout receipts when the run completes.
- Work item 242 remains waiting on this controlled CI run. Next action: collect its exact-head terminal evidence, classify remaining non-ordering failures separately, then investigate any reproduced ordering drift without changing the test queries.
- Cleanup limitation: `git worktree remove /home/vimkim/gh/cb/pr7927-order-head` refused because the worktree contains submodules, even after clean deinitialization. The worktree and `investigate/pr7927-order-head` branch remain; no forced removal was used. The unused exact-parent worktree `/home/vimkim/gh/cb/pr7927-order-base` remains available for follow-up reproduction.
