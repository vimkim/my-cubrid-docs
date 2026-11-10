# CI analysis: PR #8434 `test_sql_by_cci`

Question: are the `test_sql_by_cci` failures of CUBRID/cubrid#8434 caused by the PR?

Analysis date: 2026-11-10 (Asia/Seoul). Reader: the PR author and reviewers.

## Summary

- **Result.** `test_sql_by_cci` has 57 failures and no errors in 17,630 cases. All other gha-ci suites pass: `test_sql`, `test_medium`, `test_shell`, and both builds.
- **PR relation: unlikely, high confidence.** Unrelated PR CUBRID/cubrid#8348 also targets `feature/oos-merge` and does not contain the PR #8434 commits. Its run fails the same 57 cases with byte-identical diffs (57 of 57). The same 57 cases also failed on the two earlier heads of PR #8434 (`0034bc2fb` and `26e6d1d6f`).
- **No case touches OOS.** The diffs are differences in CCI value rendering (45), query plan or profile text (5), and error codes or results (7).
- **Limit.** The exact merge base `95ff126a8` has no `test_sql_by_cci` run, so the formal baseline is `unavailable`. The conclusion depends on a peer PR comparison. It does not depend on an exact merge-base comparison.
- **Merge gate.** `test_sql_by_cci` is not in the stable required gha-ci set (build release, `test_shell`, `test_sql`, `test_medium`). `gh pr checks --required` returned an empty list for this PR.
- **Next action.** Do not change PR #8434 for these failures. Track the `feature/oos-merge` `test_sql_by_cci` failures as separate work. Section 6 lists the candidates.

## 1. CI snapshot

| Suite | Run / attempt | Verdict | Counts |
| --- | --- | --- | --- |
| `test_sql_by_cci` | [42603737999](https://github.com/CUBRID/cubrid/actions/runs/42603737999) / 1 | FAILURE | planned 17630, run 17630, passed 17573, failures 57, errors 0, skipped 0 |
| `test_sql` | same run | SUCCESS | not collected (out of scope) |
| `test_medium` | same run | SUCCESS | not collected (out of scope) |
| `test_shell` | same run | SUCCESS | not collected (out of scope) |
| build (release), build (debug) | same run | SUCCESS | — |

Failed shards: 01 (6), 03 (9), 04 (1), 05 (3), 06 (3), 07 (14), 09 (21). Shards 00, 02, and 08 pass.

## 2. Evidence scope

- Engine: CUBRID/cubrid PR #8434 head `8e139f4dbb2635058032d0b9dafd5f624c726754`. Base `feature/oos-merge` `95ff126a8464179a2fab3092b6f56468528ab954`, which is also the exact merge base.
- Testcases: `tc/pr-8434` `e61878fb79591bb367f672074ac4c36c366a7122` in CUBRID/cubrid-testcases. This is `feature/oos-merge` `70db22a1c` plus one initialization commit.
- Collector: `cubrid-ci 0.2.0 (4d00de674d86, release)`. Collected 2026-11-10T05:37:07Z. `cubrid-ci verify` result: identity established, observation complete, manifest and summary validated. Report mode `full`. Regression conclusions are not permitted, because no baseline was available.
- Evidence directory: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8434/8e139f4dbb2635058032d0b9dafd5f624c726754/providers/github-actions/runs/42603737999/attempts/1/test_sql_by_cci/`. All 57 failures have an extracted `diff.txt`.
- Peer evidence: PR #8348 head `00b421e327f2850c8633f0db5a93736adcc7d857`, run [42578641410](https://github.com/CUBRID/cubrid/actions/runs/42578641410). Testcases `683bf41f9747250f615f23577cc62c1a4c4c17cf`. Verified with `cubrid-ci verify` (complete, validated). Counts are identical: 17573 passed, 57 failures.
- Earlier heads of PR #8434: NOK lists were extracted from the GitHub job logs of the failed shards (`Case Name:` followed by `Test Result: NOK`). These lists are not collector-validated. For run 42603737999, the log extraction gives the same 57 paths as the validated inventory.
- Limitation: Chronicle (`cubrid-tcc 0.3.0`) indexes only `sql`, `medium`, and `shell`. It has no `test_sql_by_cci` history.

## 3. Failure inventory

Head failures: 57. Classification against PR #8348: 57 also observed with an identical diff, 0 additional on head, 0 uncomparable. #8348 has no failures that PR #8434 lacks. Merge-base classification: not possible (baseline `unavailable`).

Column "develop peer" is context only. It is the result of the same case in run [42751409301](https://github.com/CUBRID/cubrid/actions/runs/42751409301) (PR #8403, a `develop` submodule update): 17 of the 57 cases are NOK there too. `develop` has diverged from `feature/oos-merge` in engine and testcases, so this column does not classify the failures.

| Shard | Testcase | Result | Category | vs PR #8348 | develop peer | PR relation | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 01 | `sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/04_normal_percent_type_parameter.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 01 | `sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/05_error_percent_type_return.sql` | failure | error code or result | also on #8348 (identical diff) | not NOK | unlikely | high |
| 01 | `sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/05_normal_percent_type_return.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 01 | `sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/24_normal_viewtable_percent_type_parameter.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 01 | `sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/25_error_viewtable_percent_type_return.sql` | failure | error code or result | also on #8348 (identical diff) | not NOK | unlikely | high |
| 01 | `sql/_05_plcsql/_01_testspec/_02_declaration/_09_percent_type/cases/25_normal_viewtable_percent_type_return.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 03 | `sql/_13_issues/_14_1h/cases/bug_bts_13653.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 03 | `sql/_13_issues/_14_1h/cases/bug_bts_13916.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 03 | `sql/_13_issues/_15_1h/cases/bug_bts_16039.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 03 | `sql/_13_issues/_20_2h/cases/cbrd_23665.sql` | failure | error code or result | also on #8348 (identical diff) | not NOK | unlikely | high |
| 03 | `sql/_13_issues/_26_2h/cases/cbrd_27327.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 03 | `sql/_13_issues/_26_2h/cases/cbrd_27504.sql` | failure | error code or result | also on #8348 (identical diff) | not NOK | unlikely | high |
| 03 | `sql/_13_issues/_26_2h/cases/cbrd_27668.sql` | failure | error code or result | also on #8348 (identical diff) | not NOK | unlikely | high |
| 03 | `sql/_14_mysql_compatibility_2/_04_table_related/_02_alter_change_column/_11_trigger/cases/1101.sql` | failure | error code or result | also on #8348 (identical diff) | not NOK | unlikely | high |
| 03 | `sql/_14_mysql_compatibility_2/_15_host_variable/_12_common/cases/agg_group_by.sql` | failure | value rendering | also on #8348 (identical diff) | also NOK | unlikely | high |
| 04 | `sql/_17_sql_extension2/_02_full_test/_03_alter_table/_01_alter_change/cases/alter_change_026.sql` | failure | value rendering | also on #8348 (identical diff) | also NOK | unlikely | high |
| 05 | `sql/_23_apricot_qa/_01_sql_extension3/_05_analytic_functions/_14_avg/cases/avg_constraints.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 05 | `sql/_23_apricot_qa/_01_sql_extension3/_05_analytic_functions/_14_avg/cases/avg_null.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 05 | `sql/_23_apricot_qa/_01_sql_extension3/_05_analytic_functions/_14_avg/cases/avg_numeric.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 06 | `sql/_26_features_920/issue_11087_median/cases/11087_1.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 06 | `sql/_26_features_920/issue_11087_median/cases/11087_3.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 06 | `sql/_26_features_920/issue_11087_median/cases/11087.sql` | failure | value rendering | also on #8348 (identical diff) | also NOK | unlikely | high |
| 07 | `sql/_27_banana_qa/issue_11088_percentile_cont/_01_aggregate_function/cases/_00_from_dev.sql` | failure | value rendering | also on #8348 (identical diff) | also NOK | unlikely | high |
| 07 | `sql/_27_banana_qa/issue_11088_percentile_cont/_01_aggregate_function/cases/_03_character_string1.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 07 | `sql/_27_banana_qa/issue_11088_percentile_cont/_01_aggregate_function/cases/_03_character_string2.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 07 | `sql/_27_banana_qa/issue_11088_percentile_cont/_02_analytic_function/cases/p_cont_bit_lob.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 07 | `sql/_27_banana_qa/issue_11088_percentile_cont/_02_analytic_function/cases/p_cont_character_string.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 07 | `sql/_27_banana_qa/issue_11088_percentile_cont/_02_analytic_function/cases/p_cont_partition_list.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 07 | `sql/_27_banana_qa/issue_11089_percentile_disc/_01_aggregate_function/cases/_00_from_dev.sql` | failure | value rendering | also on #8348 (identical diff) | also NOK | unlikely | high |
| 07 | `sql/_27_banana_qa/issue_11089_percentile_disc/_01_aggregate_function/cases/_03_character_string1.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 07 | `sql/_27_banana_qa/issue_11089_percentile_disc/_01_aggregate_function/cases/_03_character_string2.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 07 | `sql/_27_banana_qa/issue_11089_percentile_disc/_02_analytic_function/cases/p_disc_bit_lob.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 07 | `sql/_27_banana_qa/issue_11089_percentile_disc/_02_analytic_function/cases/p_disc_character_string.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 07 | `sql/_27_banana_qa/issue_11089_percentile_disc/_02_analytic_function/cases/p_disc_partition_list.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 07 | `sql/_27_banana_qa/issue_16066_BINARY_charset/_00_String_Functions_and_Operators/cases/rtrim_002.sql` | failure | error code or result | also on #8348 (identical diff) | also NOK | unlikely | high |
| 07 | `sql/_28_features_930/issue_13133_hash_query_profile/cases/hash_agg_query_profile.sql` | failure | plan/profile text | also on #8348 (identical diff) | not NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_25447/cases/cbrd_25447.sql` | failure | plan/profile text | also on #8348 (identical diff) | not NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_26258/cases/join_orderby_skip.sql` | failure | plan/profile text | also on #8348 (identical diff) | also NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_26431/cases/cbrd_26431.sql` | failure | plan/profile text | also on #8348 (identical diff) | not NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27397/cases/cbrd_27397.sql` | failure | plan/profile text | also on #8348 (identical diff) | not NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27503/cases/cbrd_27503.sql` | failure | value rendering | also on #8348 (identical diff) | also NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27510/cases/01_fetch_gate_probes.sql` | failure | value rendering | also on #8348 (identical diff) | also NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27510/cases/02_fetch_gate_bind_reads.sql` | failure | value rendering | also on #8348 (identical diff) | also NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27510/cases/03_session_variable_types.sql` | failure | value rendering | also on #8348 (identical diff) | also NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27510/cases/05_common_value_constants.sql` | failure | value rendering | also on #8348 (identical diff) | also NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27510/cases/06_precast_plan.sql` | failure | value rendering | also on #8348 (identical diff) | also NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27510/cases/07_scope_once_conversion.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27510/cases/08_to_number_domain.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27510/cases/10_list_aggregate_probes.sql` | failure | value rendering | also on #8348 (identical diff) | also NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27510/cases/11_analytic_interpolation_keys.sql` | failure | value rendering | also on #8348 (identical diff) | also NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27510/cases/13_compare_outside_terms.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27510/cases/14_index_key_probes.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27510/cases/20_conversion_contract.sql` | failure | value rendering | also on #8348 (identical diff) | also NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27510/cases/23_unresolved_domain_axes.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27510/cases/24_sum_avg_date_argument.sql` | failure | value rendering | also on #8348 (identical diff) | also NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27510/cases/25_string_constant_over_bind_sum.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |
| 09 | `sql/_36_guava/cbrd_27510/cases/29_analytic_string_first_value.sql` | failure | value rendering | also on #8348 (identical diff) | not NOK | unlikely | high |

## 4. Root-cause analysis

All three groups share one finding: the same failure, with the same diff, occurs on `feature/oos-merge` without the PR #8434 commits. Each group's cause is in the `feature/oos-merge` engine, the CCI client, or the CCI answer files. The cause is not in OOS reclamation.

### Group V: CCI value rendering (45 cases)

- Observed: the CCI output renders the same value in a different form than the `.answer_cci` file. Examples:
  - `0.1` becomes `0.100000000000000` in `_09_percent_type/04_normal_percent_type_parameter.sql`.
  - `9876543210987654321098.7654321098765432` becomes `…765432109876543`, which is one fewer fractional digit.
  - `2.00` becomes `2.0` in `cbrd_27510/14_index_key_probes.sql`.
  - `5.0` becomes `5.0000000000000000` in `cbrd_27510/24_sum_avg_date_argument.sql`.
  - AVG output changes in the ninth digit: `111.209500504` becomes `111.209500122` (`_14_avg/avg_constraints.sql`).
  - `2024-01-02 10:00:01.0` becomes `2024-01-02 10:00:01` (`cbrd_27510/05_common_value_constants.sql`).
  - `1.797…e308` is printed in full on one side and as `1.797693e+308` on the other (`11087_3.sql`).
- Observed: `test_sql` (JDBC) passes in the same run. At testcase `e61878fb`, `04_normal_percent_type_parameter.answer_cci` expects `v_NUMERIC 0.1`. That answer file was split from the JDBC answer by CBRD-24707 (testcases `1488289c2`, 2024-10-28).
- Inference: the result type, scale, or precision that the engine reports, or the way the CCI client formats it, differs from what the CCI answers expect. Candidates are aggregate result domains (AVG, SUM, MEDIAN, PERCENTILE), host-variable and constant domain changes such as `cbrd_27510`, and NUMERIC precision handling in PL/CSQL `%TYPE`. None of these code paths is changed by PR #8434.
- Unknown: which engine or CCI revision introduced each rendering change.
- Falsifier: a `test_sql_by_cci` run of `feature/oos-merge` `95ff126a8` (or of PR #8348) that passes these cases.
- Next action: run `test_sql_by_cci` on a `feature/oos-merge` tip and on `develop`, then bisect the domain or format change. Alternatively, check with the owners of `cbrd_27510` and the aggregate domain work whether the CCI answers need regeneration.

### Group P: plan and profile text (5 cases)

- Observed:
  - `hash_agg_query_profile.sql` and `cbrd_26431.sql` print `hash: true` where the answer expects `hash: partial`.
  - `join_orderby_skip.sql` prints `method: memory` where the answer expects `hybrid`.
  - `cbrd_27397.sql` prints additional trace plan blocks.
  - `cbrd_25447.sql` prints an additional `parallel workers` line and renders values differently.
- Inference: the hash aggregation and hash join build decisions, or the trace output format, differ on `feature/oos-merge` under the CCI runner. A memory-size or parameter difference between the JDBC and CCI runners is also possible.
- Unknown: whether the CCI runner sets different memory parameters.
- Falsifier: the same diff disappears on `feature/oos-merge` without the PR. It already fails on #8348, so this falsifier does not apply to PR #8434.
- Next action: compare the runner configuration of `test_sql` and `test_sql_by_cci`, and the merged hash-aggregation work on `feature/oos-merge`.

### Group E: error code or result (7 cases)

- Observed:
  - `cbrd_27504.sql`: `Error:-621` becomes `Error:-176`.
  - `1101.sql`: `Error:-528` becomes `Error:-526`.
  - `_09_percent_type/05_error_percent_type_return.sql` and `25_error_viewtable_percent_type_return.sql` now fail with `-889` ("numeric value does not fit in the target type's precision and scale") where the answer expects a value.
  - `cbrd_27668.sql`: `true` becomes `18`.
  - `cbrd_23665.sql`: a different count (`150000` becomes `100000`) and a rewritten query that selects one more column.
  - `rtrim_002.sql`: a one-space difference in a multibyte row.
- Inference: these are engine behavior or testcase/answer drift on `feature/oos-merge`. The `-889` cases match group V's NUMERIC precision change. None of the statements uses OOS-sized values or vacuum.
- Unknown: the introducing commits.
- Falsifier: as for group V.
- Next action: triage these cases first, because a changed error code or result is more likely a real behavior change than a rendering difference.

## 5. Baseline comparison

- Pinned identities: head `8e139f4db`, target `feature/oos-merge` `95ff126a8`, exact merge base `95ff126a8`. Observed 2026-11-10T05:37:29Z.
- `cubrid-ci collect-base` exit 3: `test_sql_by_cci` is `not_observed` for the merge base. Baseline: **unavailable**. No exact merge-base classification is made.
- Substitute comparison, not a baseline:
  - PR #8348 (base `feature/oos-merge`, head `00b421e32`, run 42578641410, testcases `683bf41f`) fails the same 57 paths. All 57 `diff.txt` files are byte-identical to PR #8434's.
  - PR #8348 does not contain the PR #8434 or CBRD-27925 commits. Its testcases `683bf41f` and PR #8434's `e61878fb` are both `feature/oos-merge` `70db22a1c` plus one initialization commit, with no difference under `sql/`.
- Earlier PR #8434 heads: runs [42562225722](https://github.com/CUBRID/cubrid/actions/runs/42562225722) (`0034bc2fb`) and [42585563930](https://github.com/CUBRID/cubrid/actions/runs/42585563930) (`26e6d1d6f`) have the same 57 NOK paths, from log extraction. Neither the CBRD-27953 commit `26e6d1d6f` nor the CBRD-27925 commits `e01d8d576` and `8e139f4db` changed the failure set.
- PR #8416 (`feature/oos-merge`, run 42573078376) has the same 57 cases plus 4 of its own (`cbrd_25717` ×3, `cbrd_26719`), from log extraction. Those 4 belong to that PR.

## 6. Testcase history

Not available: Chronicle does not index `test_sql_by_cci`. Section 5 gives the recurrence evidence instead: 4 runs of 3 PRs on `feature/oos-merge` between 2026-11-09 04:30Z and 13:43Z. No flakiness assessment is possible. The failure set was identical in every observed run.

## 7. Actions

1. PR #8434: no change for `test_sql_by_cci`. The required gha-ci contexts pass. This finding does not waive any CI requirement that the reviewers or the TC Merge Gate apply.
2. `feature/oos-merge`: open a separate item for the 57 `test_sql_by_cci` failures. Start with group E (7 cases), then groups V and P. A `test_sql_by_cci` run on the `feature/oos-merge` tip would give the missing exact baseline.
3. Tooling: Chronicle support for `test_sql_by_cci` would give history for the next analysis.

Evidence files (collector-owned, not in this repository): the PR #8434 and PR #8348 bundles under `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/`, each with `summary.json` and `failures/*/diff.txt`.
