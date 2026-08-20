# CI Failure Analysis: PR #7588 at `d959074`

## Executive Summary

PR [#7588](https://github.com/CUBRID/cubrid/pull/7588) is open and its exact tested head is
`d9590749d9008ccfa237d89177e44533760f7337`. Build, debug build, GitHub static checks, and
`test_medium` passed. `test_sql` failed 30 of 17,444 tests and `test_shell` failed 39 of 3,251 tests.
There are no error or unknown test results.

The CBRD-27157 regression itself is not observed in the collected failure evidence:

- no failure contains the old `TT_LOADDB -> lock_internal_perform_lock_object` self-lock assertion;
- `itrack_10006` and `bug_xdbms_sus880`, the two focused failed tests in the earlier `feat/oos`
  snapshot, are absent from the current failure list;
- `cbrd_25481` completes all loaddb operations with zero failed objects and no server core, but four
  answer comparisons still fail because generated IDs are `1,21,41,61,81` instead of `1,2,3,4,5`.

This does **not** make the PR merge-ready. The PR is currently red, three shell failures have no useful
failure detail, and the branch is 20 commits behind the current `feat/oos` head. A conflict-free merge
was validated with `git merge-tree`; therefore the next decision-quality snapshot should be collected
only after updating the base and rerunning CI.

## CI Snapshot

| Suite | State | CircleCI job | Tests | Failures | Errors | Unknown | Warning |
|---|---|---:|---:|---:|---:|---:|---|
| `test_medium` | pass | [146973](https://circleci.com/gh/CUBRID/cubrid/146973) | 975 | 0 | 0 | 0 | None |
| `test_sql` | fail | [146972](https://circleci.com/gh/CUBRID/cubrid/146972) | 17,444 | 30 | 0 | 0 | All failures are output/behavior mismatches outside the changed function's reachable path |
| `test_shell` | fail | [146976](https://circleci.com/gh/CUBRID/cubrid/146976) | 3,251 | 39 | 0 | 0 | Three failures expose only `Test failed`; two separate OOS allocation crashes remain |

Prerequisite jobs `build` (146974), `build_debug` (146971), and `download-build` (146975) passed.
GitHub `license`, `pr-style`, `code-style`, `cppcheck`, and `memory-monitor-check` also passed.

## Workflow Status

- PR state: open, non-draft, GitHub review decision `APPROVED`, merge state `UNSTABLE` because CI is red.
- Existing approvals by `lht1199` and `YeunjunLee` were submitted against old head `f11fc425`, not
  current head `d959074`.
- Five review requests remain active: `hgryoo`, `H2SU`, `youngjun9072`, `InChiJun`, and `hornetmj`.
- JIRA `CBRD-27157`: `Develop`, unresolved, updated 2026-08-18.
- Current branch divergence from `origin/feat/oos`: 4 commits ahead, 20 commits behind. The current
  base head is `465cf53e3878cc36465cbeb36e85894bdd993d7b`.
- `git merge-tree --write-tree HEAD origin/feat/oos` completed without conflicts.

## Evidence Scope

- Collection time: 2026-08-20 04:27:25 UTC.
- Collector: `cubrid-ci 0.1.0 (3e9502f72350, release)`.
- Exact source commit: `d9590749d9008ccfa237d89177e44533760f7337`.
- Evidence root: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27157/d959074`.
- SQL testcase revision: `479cd5fbf74edc28a522f9762eb8c433f7104125`.
- The shell summary does not expose a testcase revision and its private testcase sources were not
  downloaded. Shell classification therefore uses the normalized result message, diff, action logs,
  and text artifacts only.
- The historical `07fef9d` PR #6864 snapshot is used only to identify previously observed failure
  families. It is not an exact baseline because source and testcase revisions differ.
- The PR-specific diff from its tested base `e1e651deb` changes only
  `src/transaction/log_tran_table.c` (14 additions, 2 deletions), adding the `TT_LOADDB` early return.

## Failure Inventory

Every failure is listed once below. “PR relation” means relation to the `TT_LOADDB` self-lock exception,
not relation to the wider incomplete OOS branch.

### SQL failures (30)

| Category | Count | Observed signature | PR relation | Confidence |
|---|---:|---|---|---|
| Identifier-length enforcement | 6 | Former success/other errors become `-493`/`-494`; aligns with imported CBRD-26891 behavior | unlikely | High |
| AUTO_INCREMENT/serial cache output | 4 | current/start values and generated IDs advance by cached blocks | unlikely | High |
| Query-profile output | 16 | `GROUPBY` gains `readrows`; some plans gain parallel-worker text | unlikely | High |
| Optimizer plan text | 2 | changed terms, scan choice, or sargs | unlikely | High |
| Shifted error number | 2 | expected `-1379`, actual `-1380` | unlikely | High |

Identifier-length enforcement:

```text
sql/_01_object/_02_class/_001_basic/cases/1079.sql
sql/_01_object/_03_virtual_class/_001_basic/cases/1079.sql
sql/_08_javasp/cases/412-1.sql
sql/_13_issues/_13_2h/cases/bug_bts_11008.sql
sql/_13_issues/_13_2h/cases/bug_bts_11842.sql
sql/_23_apricot_qa/_01_sql_extension3/_02_new_sql_types/_01_enum/cases/_18_adhoc_multiple.sql
```

AUTO_INCREMENT/serial cache output:

```text
sql/_13_issues/_12_2h/cases/bug_bts_8537.sql
sql/_13_issues/_14_1h/cases/bug_bts_12943.sql
sql/_14_mysql_compatibility_2/_04_table_related/_02_alter_change_column/_07_auto_incr/cases/1072.sql
sql/_17_sql_extension2/_02_full_test/_03_alter_table/_01_alter_change/cases/alter_change_026.sql
```

Query-profile output:

```text
sql/_13_issues/_14_1h/cases/bug_bts_13158.sql
sql/_13_issues/_17_1h/cases/cbrd_20857.sql
sql/_13_issues/_17_1h/cases/cbrd_20865.sql
sql/_13_issues/_20_2h/cases/cbrd_23665.sql
sql/_13_issues/_23_1h/cases/cbrd_24843_4.sql
sql/_13_issues/_23_1h/cases/cbrd_24906_1.sql
sql/_13_issues/_23_1h/cases/cbrd_24906_2.sql
sql/_28_features_930/issue_13133_hash_query_profile/cases/hash_agg_query_profile.sql
sql/_34_fig/cbrd_24252/cases/cbrd_24252_31.sql
sql/_35_fig_cake/cbrd_24044/cbrd_25214/cases/cbrd_25214.sql
sql/_35_fig_cake/cbrd_25748/cases/cbrd_25748.sql
sql/_36_guava/cbrd_25447/cases/cbrd_25447.sql
sql/_36_guava/cbrd_25776/cases/cbrd_25776.sql
sql/_36_guava/cbrd_26104/cases/cbrd_26104.sql
sql/_36_guava/cbrd_26258/cases/single_orderby_skip.sql
sql/_36_guava/cbrd_26522/cases/cbrd_26522.sql
```

Optimizer plan text:

```text
sql/_13_issues/_23_1h/cases/cbrd_24906_3.sql
sql/_35_fig_cake/cbrd_25382/cases/cbrd_25382_1.sql
```

Shifted error number:

```text
sql/_13_issues/_14_1h/cases/bug_bts_10516.sql
sql/_15_fbo/_02_qa_test/cases/fbo_ddl02.sql
```

### Shell failures (39)

| Category | Count | Observed signature | PR relation | Confidence |
|---|---:|---|---|---|
| AUTO_INCREMENT/serial behavior | 11 | cached-block IDs, serial start/current values, or serial catalog output differ | unlikely | High |
| Query-profile output | 8 | `readrows`, parallel, and trace text drift | unlikely | High |
| Statistics/index display | 4 | index name is now printed before BTID | unlikely | High |
| Optimizer/XASL diagnostics | 2 | one cost delta and changed cache delete counters | unlikely | High |
| Identifier-length enforcement | 3 | long identifiers now fail and cause downstream output differences | unlikely | High |
| System-parameter display | 3 | activation/deactivation lists or parameter inventory differ | unlikely | High |
| Timezone answer drift | 2 | an additional result set is present | unlikely | High |
| OOS page-allocation assertion | 2 | `pgbuf_fix_debug` core via `file_numerable_add_page -> oos_file_alloc_new` | unlikely to this PR; direct to wider OOS | High |
| TDE recovery-log expectation | 1 | expected `RVHF_INSERT_NEWHOME` record is absent | unlikely | High |
| Opaque failure | 3 | only `Test failed`; no diff, node, source, or usable artifact | unknown | Low |

AUTO_INCREMENT/serial behavior:

```text
shell/_10_plcsql/cbrd_24731/cbrd_24871/cbrd_24871_plcsql/cases/cbrd_24871_plcsql.sh
shell/_01_utility/_17_loaddb/itrack_10009/cases/itrack_10009.sh
shell/_35_cherry/issue_21654_server_side_loaddb/loaddb_CS/_01_utility/_17_loaddb/itrack_10009/cases/itrack_10009.sh
shell/_05_addition/cubridsus1961/cases/cubridsus1961.sh
shell/_35_cherry/issue_21654_server_side_loaddb/loaddb_CS/_05_addition/cubridsus1961/cases/cubridsus1961.sh
shell/_06_issues/_24_1h/cbrd_25360/cases/cbrd_25360.sh
shell/_06_issues/_24_2h/cbrd_25481/cases/cbrd_25481.sh
shell/_06_issues/_13_2h/bug_bts_10682/cases/bug_bts_10682.sh
shell/_37_elderberry/cbrd_23842_cdc/ddl/serial/serial02/cases/serial02.sh
shell/_37_elderberry/cbrd_23842_cdc/ddl/serial/serial03/cases/serial03.sh
shell/_37_elderberry/cbrd_23842_cdc/ddl/serial/serial04/cases/serial04.sh
```

Query-profile output:

```text
shell/_28_features_844/issue_10984_query_profiling/_01_set_trace/_01_set_trace_common/cases/_01_set_trace_common.sh
shell/_28_features_844/issue_10984_query_profiling/_01_set_trace/_02_set_trace_index/cases/_02_set_trace_index.sh
shell/_28_features_844/issue_10984_query_profiling/_02_auto_trace/_01_auto_trace_common/cases/_01_auto_trace_common.sh
shell/_28_features_844/issue_10984_query_profiling/_02_auto_trace/_02_auto_trace_index/cases/_02_auto_trace_index.sh
shell/_28_features_844/issue_10984_query_profiling/_03_mixed_test/_02_having/cases/_02_having.sh
shell/_28_features_844/issue_10984_query_profiling/_03_mixed_test/_04_group_by_topnsort/cases/_04_group_by_topnsort.sh
shell/_28_features_844/issue_10984_query_profiling/_03_mixed_test/_06_update_delete/cases/_06_update_delete.sh
shell/_40_guava/cbrd_25846/cases/cbrd_25846.sh
```

Statistics/index display:

```text
shell/_06_issues/_20_2h/cbrd_23732/cases/cbrd_23732.sh
shell/_37_elderberry/cbrd_23931/reuse_oid_05/cases/reuse_oid_05.sh
shell/_39_fig_cake/cbrd_24044_enhance_optimizer/cbrd_24409/cases/cbrd_24409.sh
shell/_39_fig_cake/cbrd_24044_enhance_optimizer/cbrd_24873/cases/cbrd_24873.sh
```

Optimizer/XASL diagnostics:

```text
shell/_40_guava/cbrd_26403/cases/cbrd_26403.sh
shell/_06_issues/_17_1h/cbrd_20149_recompile/cases/cbrd_20149_recompile.sh
```

Identifier-length enforcement:

```text
shell/_06_issues/_12_2h/bug_bts_10205/cases/bug_bts_10205.sh
shell/_06_issues/_13_2h/bug_bts_10641/cases/bug_bts_10641.sh
shell/_30_banana_qa/issue_13637_show_index_header/_02_partition/cases/_02_partition.sh
```

System-parameter display:

```text
shell/_06_issues/_11_2h/bug_bts_5423/cases/bug_bts_5423.sh
shell/_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh
shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh
```

Timezone answer drift:

```text
shell/_30_banana_qa/issue_14774_utc_date/cases/issue_14774_utc_date.sh
shell/_30_banana_qa/issue_9328_utc_time/cases/issue_9328_utc_time.sh
```

OOS page-allocation assertion:

```text
shell/_39_fig_cake/cbrd_25365/cases/cbrd_25365.sh
shell/_35_cherry/issue_21522_json/cbrd_23430/cases/cbrd_23430.sh
```

TDE recovery-log expectation:

```text
shell/_36_damson/cbrd_23608_tde/log_enc_04/cases/log_enc_04.sh
```

Opaque failures:

```text
shell/_35_cherry/issue_21654_server_side_loaddb/bigPageSize/cases/bigPageSize.sh
shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh
shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh
```

## Root-Cause Analysis

### CBRD-27157 target behavior

**Observed:** `itrack_10006` and `bug_xdbms_sus880` passed. `cbrd_25481` records successful object
loads, no core, and only four serial-ID answer mismatches. No collected failure contains
`TT_LOADDB`, `logtb_acquire_mvccid_self_lock`, `lock_transaction_mvccid`, or
`lock_internal_perform_lock_object`.

**Inferred:** the agreed `TT_LOADDB` early return removes the original self-lock assertion path.
Confidence is high because the two focused tests changed from failed to passed and the remaining
focused test crossed the previously crashing loaddb operations successfully.

**Falsifier:** a fresh optdebug run on an updated base that produces the old stack, or a load-worker
path that exposes an INSID and therefore needs a transaction self-lock.

### Imported output and behavior drift (SQL 30; shell 33)

The tested PR head merged 49 base commits between the earlier `07fef9d` snapshot and base
`e1e651deb`. The observed clusters match those imported changes: identifier validation
(CBRD-26891), cached AUTO_INCREMENT allocation (CBRD-26976 plus the OOS serial-consumption hotfix),
index-name display (CBRD-27175), optimizer changes, and query-profile output changes. None of the SQL
tests can create a `TT_LOADDB` worker; the shell signatures do not enter the changed self-lock
function.

**Relation:** unlikely to the PR-specific change, high confidence. This is not proof that every answer
file should be changed. The intended behavior of each imported base change and an exact current-base
CI run must decide whether code or testcase answers are stale.

### Separate OOS allocation crash (2 shell tests)

`cbrd_25365` and `cbrd_23430` core in `pgbuf_fix_debug` at `page_buffer.c:2419`, reached through
`file_numerable_add_page -> file_alloc -> oos_file_alloc_new -> oos_find_best_page`. This stack is
different from CBRD-27157 and appeared in the older `07fef9d` snapshot.

**Relation:** direct to the wider OOS implementation, unlikely to the one-function self-lock skip.
The next observation needed is the assertion expression and page/VFID state from a targeted local
reproduction or binary core artifact; text-only mode has the stack but not the core.

### Opaque failures (3 shell tests)

`bigPageSize`, `cbrd_27064`, and `cbrd_27075` expose only `Test failed`, with no node index, diff,
downloaded private source, or targeted artifact. Their relationship is unknown. `bigPageSize` is
especially important because it exercises server-side loaddb and was associated with the historical
regression family, but the current evidence cannot say whether it failed for the old assertion,
another OOS defect, or harness/reporting loss.

## Recommended Actions

1. Merge current `origin/feat/oos` into the PR branch. The branch is 20 commits behind and the merge
   is conflict-free in `git merge-tree`; analyzing or fixing the old red snapshot first would target a
   superseded base.
2. Rebuild and run the focused loaddb tests on the updated head: `itrack_10006`,
   `bug_xdbms_sus880`, `cbrd_25481`, and `bigPageSize`. Treat `bigPageSize` as unresolved until a run
   yields an actual message/stack.
3. Trigger one fresh `/run all` for the updated exact head. Do not carry the current 30/39 counts
   forward as the new branch status.
4. Do not change the `TT_LOADDB` implementation to chase query-trace, identifier, serial, statistics,
   timezone, TDE, or separate OOS allocation failures. Reconcile those against current-base CI and
   their owning changes.
5. Once the updated exact-head CI is acceptable, request fresh review because the two recorded
   approvals target `f11fc425`, not the current or future head.

## Evidence and Limitations

Inspected evidence includes the commit manifest, all three suite summaries, both complete failed-test
inventories, every failure metadata/message/diff record, action-log and artifact indexes, targeted
text artifacts, the exact source diff, local OOS/JIRA context, and live PR/JIRA metadata. No CI was
rerun or triggered during analysis, no PR/JIRA state was modified, and no binary artifacts were
requested.

The strongest supported conclusion is narrow: the original CBRD-27157 assertion is absent and its two
focused failures pass, while the PR as a whole remains red and stale against its base. The evidence
does not support declaring `bigPageSize` fixed or declaring all other failures harmless.
