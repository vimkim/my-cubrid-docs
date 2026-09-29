# Source-level triage of QA expectation candidates

Read-only assessment, 2026-09-29. Feature engine `1ec35f86c5e43b9ca86d81e202c68899f8ce4f21`; named develop baseline `e1c3db19800a0170942cec8b23cac4705efbb6e3`. No testcase, build, instrumented experiment, or repair was run. The user's explicit source-only scope waives the diagnosis skill's reproduction phases; these are source-supported assessments, not reproduced diagnoses.

The original inventory remains authoritative for suite identities: [QA comparison](qa_comparison_1ec35f8_codex.md). S01, S02, S03, S04, H05 and I02 have completed baseline comparators. P01 remains provisional because the develop performance suite has only 47/58 completed verdicts.

**Main correction to the earlier report:** S04 is not safely described as cosmetic plan drift. Several changed `card` values are exactly what its testcase deliberately preserves and checks. Do not refresh those answers without explaining the semantic change.

## Action table

| Family / additional rows | Decision | Evidence / proposed action | Confidence | Eventual validation |
|---|---|---|---|---|
| S01 bug_bts_15529, shell + debug, 2 | Narrow answer update is justified as a candidate | Add exactly the intentional three default diagnostic codes, retaining every other parameter assertion. Source matches captured actual values; existing testcase branch still lacks them. | High for source/answer mismatch; diagnostic-policy acceptance is reviewable, not independently mandated by the OOS spec. | Run both variants on exact repaired engine/TC SHAs; diff all parameters, custom-list setting and reset behavior. |
| S02 four cbrd_24501 DBLink DML variants, shell + debug, 8 | Narrow cost-token normalization is a candidate; do not change logical answers | All four retained debug summaries show one cost digit-width difference. Existing masking replaces individual digits and preserves width. Normalize only the unasserted numeric cost scalar, while retaining plans, pushed SQL, errors and rows. Confirm complete logs first. | High for observed normalization weakness; low for why raw cost changed. | Each backend, both variants; prove query rows and pushdown plan shape unchanged before accepting normalization. |
| S03 MySQL/Oracle/MariaDB server-owner checks, shell + debug, 6 | Hold answers; potential functional/parser behavior discrepancy | User-validation versus syntax errors and G1/G2 owner outcomes differ. Local supporting SQL lacks those G1/G2 scenarios, so deployed TC identity must be established first. | High that mismatch is substantive; low for cause. | Obtain exact deployed SQL/answers/harness and SHA, map each statement to error/owner result, then verify intended authorization behavior. |
| S04 cbrd_26354, shell + debug, 2 | Hold answers; investigate targeted cardinality behavior | Preserved cardinalities change, including case 16: 55 versus 11, and case 18: 200000 versus 99986. These are testcase assertions, not masked costs. | High for the observed assertion change; low for root cause. | Same setup row counts, NDVs, stats and engine/TC/harness revisions; verify each LIMIT/cardinality rule before any answer refresh. |
| H05 cbrd_26374_ha, ha_shell, 1 | Conditional physical-offset update is a justified candidate | All nine classical diff rows differ only in t_offset, uniformly +8. Added heap page-header VFID explains +8 on Linux ABI. Keep lengths/types/MVCC fields and all HA subcases unchanged. | High for layout mechanism; full deployed testcase still unavailable. | Fresh databases, prove header length change and first-page identity, verify all diagnostics and replicated logical values; never subtract 8 from arbitrary rows. |
| I02 insert_odku_online_index_01.ctl, isolation_debug, 1 | Narrow concurrent-output comparison repair is a candidate; do not merely swap snapshot lines | C3/C4 are released together; readiness waits do not impose their completion order. Actual and expected differ in order of one-row/two-row messages, with visible final data matching. | Medium-high for unconstrained order; only captured run observed. | Preserve both DML counts, lock/block barriers, final index/data assertions; collect per-client output or accept only the two allowed completion permutations. |
| P01 cbrd_23865 subcase 2, shell_perf, 1 | Hold performance requirement and provisional comparator | 34−26=8 seconds; predicate requires >8. This correctly fails its current requirement. Neither changing > to >= nor refreshing an answer establishes required performance. | High for threshold mechanism; cause and regression attribution unknown. | Complete develop comparator and matched machine/reference build runs; retain correct-result guards and decide required performance from issue intent. |

## S01: precise diagnostic-default drift

[system_parameter.c:5901](https://github.com/CUBRID/CUBRID/blob/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21/src/base/system_parameter.c#L5901) adds `ER_HEAP_OOS_BAD_INLINE_HEADER`, `ER_HEAP_OOS_CORRUPTED_RECORD` and `ER_HEAP_OOS_INVALID_ARGUMENT` to `call_stack_dump_error_codes[]`. They are `-1383`, `-1385`, `-1386` in [error_code.h:1783](https://github.com/CUBRID/CUBRID/blob/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21/src/base/error_code.h#L1783). Captured actual defaults contain exactly those additions.

Both supporting answers still omit them at lines 949 and 959: [test.answer](https://github.com/cubrid/cubrid-testcases-private-ex/blob/1274a4d6462a3d5ae5daeb004e042f89496991d8/shell/_25_unstable/_06_issues/_14_2h/bug_bts_15529/cases/test.answer#L949) and [testdebug.answer](https://github.com/cubrid/cubrid-testcases-private-ex/blob/1274a4d6462a3d5ae5daeb004e042f89496991d8/shell/_25_unstable/_06_issues/_14_2h/bug_bts_15529/cases/testdebug.answer#L949). The testcase also checks setting a custom list, so do not rewrite the entire output or replace all lists globally.

This is an intentional source-level diagnostic default, not an observed occurrence of corruption. OOS accepted design includes diagnostics for malformed records and eager cleanup, but does not independently prescribe this exact activation list. Source agreement alone establishes answer staleness relative to the implemented default; accepting the default remains part of reviewing the feature.

The prior testcase commit `cebbd0884cd2cef8134fe99ec754ffded186327a` rebaselines `bug_bts_9836` and `bug_bts_14120`, not this testcase. Do not assume the existing testcase PR already repairs S01.

## S02: masking preserves cost-number width

All four DBLink DML debug result summaries contain the same decisive difference:

```text
actual:    cost:  ???  card ????
expected:  cost:  ???? card ????
```

The actual log is the left argument in the reported `diff _07_*_dblink_push.log ...answer`. Saved raw [debug summary](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=59001&resultType=NOK), HTML pre blocks 16, 17, 18 and 20, includes MySQL, MariaDB, CUBRID and Oracle. These are the only differing cost rows in those retained summaries; this does not establish full deployed-console equivalence in every variant.

[MySQL testcase:200](https://github.com/cubrid/cubrid-testcases-private-ex/blob/1274a4d6462a3d5ae5daeb004e042f89496991d8/shell/_25_unstable/_38_fig/cbrd_24501_dblink_dml/cbrd_24501_mysql/cases/cbrd_24501_mysql.sh#L200) applies `format_query_plan`. Supporting local [CTP helper:1091](https://github.com/cubrid/cubrid-testtools/blob/7ae1c231a3ba5557a85432bc1ae25898cbe07c40/CTP/shell/init_path/init.sh#L1091) masks `[0-9]` individually between `Join graph segments` and `Query stmt:`, so 999 and 1000 become `???` and `????`. This helper is read-only supporting evidence, not proof of the QA harness SHA and not authorization to run CTP.

The normalization intent is evident because costs are already masked. A focused scalar normalization can remove residual digit-width dependence while retaining all plan structure and result assertions. A global collapse of every question-mark sequence would also hide other differences and is not recommended. The engine optimizer `query_plan.c`/`query_graph.c` have no diff against the named baseline; the changed histogram sampler call selects the OOS-aware record consumption policy. That does not establish the reason for the changed cost.

## S03: authorization differences remain functional

Saved raw debug summary pre block 10 includes, for example:

```text
actual:   ERROR: before ' ;  '
expected: ERROR: User "userx" is invalid.
actual:   owner G1
expected: owner G2
```

Other differences include missing expected `srv1` rows and unexpected already-exists/not-found/permission errors. Replacing expected output with actual would risk legitimizing changed ownership and authorization behavior.

The local [MySQL SQL](https://github.com/cubrid/cubrid-testcases-private-ex/blob/1274a4d6462a3d5ae5daeb004e042f89496991d8/shell/_25_unstable/_37_elderberry/cbrd_23843_dblink/cbrd_24420_mysql/cases/_07_server_check.sql#L1) has 144 lines, and its answer has 400 lines; neither contains G1/G2 scenarios present in QA. The [runner:181](https://github.com/cubrid/cubrid-testcases-private-ex/blob/1274a4d6462a3d5ae5daeb004e042f89496991d8/shell/_25_unstable/_37_elderberry/cbrd_23843_dblink/cbrd_24420_mysql/cases/cbrd_24420_mysql.sh#L181) copies SQL and substitutes connection/host fields. Therefore the retained QA scenario content cannot be reconstructed from that local file. This is stronger evidence of a testcase/harness mismatch than merely not knowing its SHA, but does not by itself explain the incorrect results.

`semantic_check.c`, `schema_manager.c`, `schema_system_catalog_install.cpp` and the checked authorization sources have no diff against the named baseline. Grammar changes add OOS-related storage syntax/tokens and SHOW HEAP OOS, with no direct DBLink-owner grammar change. Shared storage/catalog code still changes broadly under OOS; absence of an owner-specific source diff does not rule out an engine bug or parser generation issue.

## S04: cardinality changes cannot be masked

[Testcase:97](https://github.com/cubrid/cubrid-testcases-private-ex/blob/1274a4d6462a3d5ae5daeb004e042f89496991d8/shell/_25_unstable/_40_guava/cbrd_26354/cases/cbrd_26354.sh#L97) intentionally restores the real top-level `card` after general plan masking. Its declared purpose is LIMIT-driven row-count estimation for nested-loop joins. The saved debug pre block 6 has these actual assertion differences; here the reported diff compares answer on the left to actual on the right:

| Case | Expected card | Actual card |
|---|---:|---:|
| 4 | 1002 | 1001 |
| 5 | 2002 | 2000 |
| 8–12 | 100000 | 99986 |
| 16 | 55 | 11 |
| 18 | 200000 | 99986 |

Case 16 explicitly swaps the driving side to the high-NDV column. [Case 18:242](https://github.com/cubrid/cubrid-testcases-private-ex/blob/1274a4d6462a3d5ae5daeb004e042f89496991d8/shell/_25_unstable/_40_guava/cbrd_26354/cases/cbrd_26354.sh#L242) deliberately forces nested loops and asserts uncapped LIMIT cardinality. Therefore accepting 99986 instead of 200000 would undo the documented guard. The raw console has further differing plan/selectivity lines, including scientific-notation widths. None justify broad answer refresh.

Setup uses seven `VARCHAR(20)` columns and short decimal strings, so this testcase does not demonstrate OOS demotion. Statistics, sampling, actual setup cardinality, catalog shape or corpus/harness version may explain some estimates; each is a hypothesis requiring evidence. Pure optimizer-core source equality is useful for narrowing an investigation, not a waiver of the failing assertion.

## H05: account for the uniform +8 bytes at the heap page header

The nine classical diff row pairs in [HA raw summary](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=59000&resultType=NOK), pre block 4, differ only in token 3, `t_offset`. The actual/answer values are 1192/1184, 1280/1272, 1368/1360, 1868/1860, 2000/1992, 2132/2124, 2264/2256, 2388/2380 and 2512/2504. Length, record type and all other visible diagnostic tokens match.

The source chain accounts for that fixed displacement:

1. The only `HEAP_HDR_STATS` field difference against e1c3db198 is added `VFID oos_vfid` at [heap_file.c:215](https://github.com/CUBRID/CUBRID/blob/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21/src/storage/heap_file.c#L215).
2. [VFID:964](https://github.com/CUBRID/CUBRID/blob/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21/src/compat/dbtype_def.h#L964) is `int32_t fileid` plus `short volid`: eight bytes including tail padding under the Linux ABI. Inserting it before existing integer fields preserves downstream alignment and increases this struct by eight bytes.
3. The heap page header is stored as a real slotted record with `recdes.length = sizeof(HEAP_HDR_STATS)` and inserted into the header slot at [heap_file.c:4974](https://github.com/CUBRID/CUBRID/blob/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21/src/storage/heap_file.c#L4974).
4. [slotted_page.c:1438](https://github.com/CUBRID/CUBRID/blob/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21/src/storage/slotted_page.c#L1438) assigns the next record the current free-area offset, then advances it by record length plus alignment waste. An eight-byte header increase shifts later header-page records by eight, retaining their lengths and gaps.
5. [heap_get_record_info:20684](https://github.com/CUBRID/CUBRID/blob/1ec35f86c5e43b9ca86d81e202c68899f8ce4f21/src/storage/heap_file.c#L20684) reports the actual slot offset, not a synthesized OOS offset.

This explanation does **not** use the HAS_OOS MVCC flag: the normative spec explicitly says that flag does not change MVCC header size. Nor does it require any tested row's value to be demoted to a 24-byte stub. The one-OOS-file-per-heap specification requires the association, and this is the implementation's persisted association layout. ADR-0005 permits format changes between unreleased feature revisions while keeping disk compatibility 11.5 and requiring database recreation; it does not require preserving these physical diagnostic offsets.

An update of these nine expected offsets is therefore a well-supported candidate for the new format, conditional on obtaining the full deployed testcase and verifying fresh-database/header-page assumptions. Do not normalize every diagnostic offset away: that would discard the testcase's physical-location checks. Do not treat this as evidence that every other HA result passes.

## I02: readiness waits do not determine C3/C4 output order

[Control file:32](https://github.com/CUBRID/cubrid-testcases/blob/89d4ec2423d94b973b5f9cf0c612c9576b9ccce6/isolation/_06_features/cbrd_22705_online_index_parallel/dml_online_index/insert_odku_online_index_01.ctl#L32) starts C3 duplicate-key INSERT and C4 UPDATE while both are blocked by online-index DDL. C1 commit releases C2, whose lock demotion releases C3 and C4. Sequential `wait until C3 ready` then `wait until C4 ready` waits for events but does not impose a happens-before relationship between those two operations finishing.

The captured [isolation_debug diff](https://qahome.cubrid.org/qaresult/viewShellTestResult.nhn?shellTestId=59007&resultType=NOK) moves `1 row affected` relative to `2 rows affected`; both messages and visible final index/data output remain present. Because the testcase intentionally overlaps DML with index build, serializing the DML to make the output match would weaken the intended coverage. Prefer comparing client-labelled output or permitting just the two legitimate message orders, retaining all lock barriers and final-state checks. No testcase change is made here.

## P01: strict speed target is currently a valid failing assertion

[Performance testcase:108](https://github.com/cubrid/cubrid-testcases-private-ex/blob/1274a4d6462a3d5ae5daeb004e042f89496991d8/shell_perf/_06_issues/_21_1h/cbrd_23865/cases/cbrd_23865.sh#L108) requires result count 47000 and `reference_seconds - current_seconds > 8`; both elapsed values are truncated to integer seconds. The captured run is 34 versus 26 seconds, so the existing predicate correctly fails at equality. That is evidence of a one-boundary-value miss, not permission to weaken the requirement.

The reference is 10.2, not the named develop build. Returning the correct count is necessary but does not prove acceptable performance. Determine the intended performance criterion from the owning issue and obtain a complete matched develop comparator before deciding whether to repair timing measurement/threshold policy or investigate engine overhead. Keep the count guard and the second workload's time requirement.

## Testcase branch and policy checks

Read-only `rev-parse` and tree diff checks show public `tc/pr-7990` and `feature/oos-merge` at `89d4ec2423d94b973b5f9cf0c612c9576b9ccce6`, private-ex at `1274a4d6462a3d5ae5daeb004e042f89496991d8`, with no tree differences between those two branch names in either repository. None of the proposed candidates above is already fixed merely by switching between those local branch names. These identities remain supporting snapshots, not asserted QA testcase SHAs.

ADR-0005 retains the existing public/private testcase PRs for independent non-CDC expectation corrections, but specifically requires the deferred CDC cases to remain enabled and visibly failing. None of the proposals above modifies CDC tests, removes failed cases, or establishes full QA qualification.
