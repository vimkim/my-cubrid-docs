# PR6864 non-CDC repair proposal v1 — 2026-09-15

Status: awaiting-fix-approval

## Scope and identities

PR https://github.com/CUBRID/cubrid/pull/6864 is open at engine `38093ea859a8a08e20405b72b0cb395205bedb2f`. Remote testcase branches `tc/pr-6864` remain SQL `94e094bc669e6721018555b48f2db1dd579d1fa9` and private shell `c71941cf856ace83649ed64e45f82c41f7b045d5`.

User deferred CDC27064/27075 on 2026-09-15. Current scope is seven non-CDC cases, comprising six concrete testcase repairs and diagnosis of the remaining optimizer case. The TC merge gate remains separately failed; closing or merging companion PRs is not part of this proposal.

SQL discovery checkout `/home/vimkim/gh/tc/cubrid-testcases-feat-oos` is clean but on feat/oos at396504540fdbde32e6773c2800300f9f6ddb1c2d, not the tested SHA. Private checkout `/home/vimkim/gh/tc/cubrid-testcases-private-ex-tc-pr-6864` is clean on the tested branch/SHA. Engine `/home/vimkim/gh/cb/oos-storage` matches the tested head but has unrelated submodule/user changes. Preserve these; use isolated testcase worktrees pinned to the remote SHAs and a verified private engine installation. Existing exact engine checkout `/home/vimkim/gh/cb/oos-acceptance-38093ea` has a dirty CCI submodule; do not silently treat its installation as byte-identical. Environment testcase variables were unset; roots were located and validated through Git, without a sync helper.

## Diagnosis and sync decision

See [validated snapshot](../../ci_analysis_report_38093ea_codex.md). CircleCI SQL2 and shell7 failures; medium0; zero error/unknown. Actions duplicates the nine failed testcase names with verified provenance. CDC is accepted-outside-scope for this repair pass, not passed.

Four error-number cases are high-confidence expectation drift justified by exact error_code.h and the symbolic default list. The parameter case is a high-confidence missing expectation for the declared new parameter. The TDE case filters out the new index-sort diagnostic: exact btree_sort.c:1098 emits `btree_sort(): tde_encrypted = ...`; preserve the three query sorts plus one index build for each encryption setting by accepting both function names and keeping eight exact messages in order.

Remote private develop at48250d60cf8cece13abaff0f1b29982c59a256c0 has byte-identical case/answer files for bug_bts_5423, temp_enc_09 and cbrd_25080. A branch sync alone therefore does not repair these cases. Numeric answers are OOS-branch-specific; do not replace them with develop answers that expect wide INSERT success.

## Concrete proposed edits

Eight files in two testcase repositories; engine behavior remains unchanged by this proposal. Diff text below is a proposal only and has not been applied to testcase files.

### sql/_13_issues/_14_1h/answers/bug_bts_10516.answer

Repository: CUBRID/cubrid-testcases

```diff
--- a/sql/_13_issues/_14_1h/answers/bug_bts_10516.answer
+++ b/sql/_13_issues/_14_1h/answers/bug_bts_10516.answer
@@ -11,7 +11,7 @@
 ===================================================
 0
 ===================================================
-Error:-1382
+Error:-1383
 ===================================================
 1
 ===================================================
```

### sql/_15_fbo/_02_qa_test/answers/fbo_ddl02.answer

Repository: CUBRID/cubrid-testcases

```diff
--- a/sql/_15_fbo/_02_qa_test/answers/fbo_ddl02.answer
+++ b/sql/_15_fbo/_02_qa_test/answers/fbo_ddl02.answer
@@ -9,7 +9,7 @@
 ===================================================
 0
 ===================================================
-Error:-1382
+Error:-1383
 ===================================================
 1
 ===================================================
```

### shell/_06_issues/_12_2h/bug_bts_9836/cases/log2.answer

Repository: CUBRID/cubrid-testcases-private-ex

```diff
--- a/shell/_06_issues/_12_2h/bug_bts_9836/cases/log2.answer
+++ b/shell/_06_issues/_12_2h/bug_bts_9836/cases/log2.answer
@@ -1,2 +1,2 @@
-[C*] call_stack_dump_activation_list=-3,-2,-7,-13,-14,-17,-19,-21,-22,-45,-46,-48,-50,-1381,-1383,-1384,-51,-52,-76,-78,-79,-81,-90,-96,-97,-313,-314,-407,-415,-416,-417,-583,-603,-836,-859,-890,-891,-976,-1040,-1075,-1131,-1084,-4 ()
-[S*] call_stack_dump_activation_list=-3,-2,-7,-13,-14,-17,-19,-21,-22,-45,-46,-48,-50,-1381,-1383,-1384,-51,-52,-76,-78,-79,-81,-90,-96,-97,-313,-314,-407,-415,-416,-417,-583,-603,-836,-859,-890,-891,-976,-1040,-1075,-1131,-1084,-4 ()
+[C*] call_stack_dump_activation_list=-3,-2,-7,-13,-14,-17,-19,-21,-22,-45,-46,-48,-50,-1382,-1384,-1385,-51,-52,-76,-78,-79,-81,-90,-96,-97,-313,-314,-407,-415,-416,-417,-583,-603,-836,-859,-890,-891,-976,-1040,-1075,-1131,-1084,-4 ()
+[S*] call_stack_dump_activation_list=-3,-2,-7,-13,-14,-17,-19,-21,-22,-45,-46,-48,-50,-1382,-1384,-1385,-51,-52,-76,-78,-79,-81,-90,-96,-97,-313,-314,-407,-415,-416,-417,-583,-603,-836,-859,-890,-891,-976,-1040,-1075,-1131,-1084,-4 ()
```

### shell/_06_issues/_12_2h/bug_bts_9836/cases/log3.answer

Repository: CUBRID/cubrid-testcases-private-ex

```diff
--- a/shell/_06_issues/_12_2h/bug_bts_9836/cases/log3.answer
+++ b/shell/_06_issues/_12_2h/bug_bts_9836/cases/log3.answer
@@ -1,2 +1,2 @@
 [C ] call_stack_dump_activation_list= ()
-[S*] call_stack_dump_activation_list=-2,-7,-13,-14,-17,-19,-21,-22,-45,-46,-48,-50,-1381,-1383,-1384,-51,-52,-76,-78,-79,-81,-90,-96,-97,-313,-314,-407,-415,-416,-417,-583,-603,-836,-859,-890,-891,-976,-1040,-1075,-1131,-1084 ()
+[S*] call_stack_dump_activation_list=-2,-7,-13,-14,-17,-19,-21,-22,-45,-46,-48,-50,-1382,-1384,-1385,-51,-52,-76,-78,-79,-81,-90,-96,-97,-313,-314,-407,-415,-416,-417,-583,-603,-836,-859,-890,-891,-976,-1040,-1075,-1131,-1084 ()
```

### shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120_1.answer

Repository: CUBRID/cubrid-testcases-private-ex

```diff
--- a/shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120_1.answer
+++ b/shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120_1.answer
@@ -8,5 +8,5 @@
 [S ] error_log_warning=n (n)
 [S ] error_log_size=536870912 (536870912)
 [S ] call_stack_dump_on_error=n (n)
-[S*] call_stack_dump_activation_list=-2,-7,-13,-14,-17,-19,-21,-22,-45,-46,-48,-50,-1381,-1383,-1384,-51,-52,-76,-78,-79,-81,-90,-96,-97,-313,-314,-407,-415,-416,-417,-583,-603,-836,-859,-890,-891,-976,-1040,-1075,-1131,-1084 ()
+[S*] call_stack_dump_activation_list=-2,-7,-13,-14,-17,-19,-21,-22,-45,-46,-48,-50,-1382,-1384,-1385,-51,-52,-76,-78,-79,-81,-90,-96,-97,-313,-314,-407,-415,-416,-417,-583,-603,-836,-859,-890,-891,-976,-1040,-1075,-1131,-1084 ()
 [S ] call_stack_dump_deactivation_list= ()
```

### shell/_06_issues/_11_2h/bug_bts_5423/cases/bug_bts_5423.answer

Repository: CUBRID/cubrid-testcases-private-ex

```diff
--- a/shell/_06_issues/_11_2h/bug_bts_5423/cases/bug_bts_5423.answer
+++ b/shell/_06_issues/_11_2h/bug_bts_5423/cases/bug_bts_5423.answer
@@ -30,3 +30,4 @@
 [S ] max_subquery_cache_size=2.0M (2.0M)
 [S ] auto_scaling_window_size=4 (4)
 [S ] auto_increment_cache_size=20 (20)
+[S ] index_build_buffer_size=2.0M (2.0M)
```

### shell/_36_damson/cbrd_23608_tde/temp_enc_09/cases/temp_enc_09.sh

Repository: CUBRID/cubrid-testcases-private-ex

```diff
--- a/shell/_36_damson/cbrd_23608_tde/temp_enc_09/cases/temp_enc_09.sh
+++ b/shell/_36_damson/cbrd_23608_tde/temp_enc_09/cases/temp_enc_09.sh
@@ -48,7 +48,7 @@
 csql -udba -S -c "select avg(a) over (partition by b) from ttt_enc;" $db_name    # analytics
 csql -udba -S -c "create index ttt_enc_idx on ttt_enc (a);" $db_name           # load index
 
-grep "TDE:" csql.err| grep  "sort_listfile" > result.log 2>&1
+grep "TDE:" csql.err| grep -E "(sort_listfile|btree_sort)\(\)" > result.log 2>&1
 compare_result_between_files result.log result.answer
 
 cubrid deletedb $db_name
```

### shell/_36_damson/cbrd_23608_tde/temp_enc_09/cases/result.answer

Repository: CUBRID/cubrid-testcases-private-ex

```diff
--- a/shell/_36_damson/cbrd_23608_tde/temp_enc_09/cases/result.answer
+++ b/shell/_36_damson/cbrd_23608_tde/temp_enc_09/cases/result.answer
@@ -1,8 +1,8 @@
 TDE: sort_listfile(): tde_encrypted = 0
 TDE: sort_listfile(): tde_encrypted = 0
 TDE: sort_listfile(): tde_encrypted = 0
-TDE: sort_listfile(): tde_encrypted = 0
+TDE: btree_sort(): tde_encrypted = 0
 TDE: sort_listfile(): tde_encrypted = 1
 TDE: sort_listfile(): tde_encrypted = 1
 TDE: sort_listfile(): tde_encrypted = 1
-TDE: sort_listfile(): tde_encrypted = 1
+TDE: btree_sort(): tde_encrypted = 1
```

## Optimizer case: investigate before proposing an edit

For `shell/_39_fig_cake/cbrd_24044_enhance_optimizer/cbrd_25080/cases/cbrd_25080.sh` and its three plan answers, preserve both explicit LIMIT cardinality checks and all existing comparisons. Reproduce the raw selectivity/cardinality output with the pinned testcase on the tested engine and an appropriate develop baseline. Trace the estimator difference and the shared normalization behavior. No optimizer answer replacement, assertion removal, broader numeric masking, testtools edit or engine edit is approved by this proposal. Present the resulting exact correction separately if required. A changed actual result or LIMIT contract is an engine finding, not permission to bless output.

## Verification plan

After approval, use the existing focused SQL/shell runners with isolated PID/network/IPC/mount namespaces, private /tmp sockets, configuration and installation. Initialize the pinned JDBC submodule and prepare the selected build via the cubrid-build workflow. Retain original RED and patched GREEN outputs with exact engine/testcase/patch/install identities.

Configure each SQL scenario to one full case path and run `ctp.sh sql -c <focused-sql.conf>`; configure each shell scenario to its one full directory and run `ctp.sh shell -c <focused-shell.conf>` through the isolated runner. Exact generated config and invocation paths belong to each retained attempt, not guessed commands.

Acceptance for the concrete patch: each SQL case1/1 passes; bug_bts_9836 all3 checks pass; bug_bts_14120 both2 pass; bug_bts_5423 all6 pass; temp_enc_09 still verifies all8 ordered diagnostics, including encrypted index sort=1 and unencrypted index sort=0. Check that the TDE assertion detects a changed/missing index-sort entry. Do not count process exit0 as testcase success. Run the optimizer case for diagnosis with its assertions unchanged.

If results disagree with these diagnoses, retain failures and revise the proposal rather than silently expanding scope. Full remote verification requires a later reviewed publication set and explicit push/CI-trigger approval. Proposed eventual destinations are canonical testcase tc/pr-6864 branches (or reviewed companion branches targeting them); no destination is published by this approval. CDC and the TC merge gate will remain visible even if this scoped repair passes.

## Approval record

Requested: apply and locally verify the eight-file/six-test patch above; continue read-only/local baseline diagnosis of cbrd_25080. No new push, commit, trigger or external comment authorization has been granted for this set. Historical 2026-09-09 publication approvals belong to the earlier set and do not cover these new commits.
