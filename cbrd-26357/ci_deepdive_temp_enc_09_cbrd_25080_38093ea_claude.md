# CI Deep Dive: `temp_enc_09` and `cbrd_25080` — PR #6864 at `38093ea`

- **PR**: https://github.com/CUBRID/cubrid/pull/6864 (`develop <- feat/oos` tracking PR)
- **Commit**: `38093ea859a8a08e20405b72b0cb395205bedb2f` (Merge origin/develop into feat/oos, 2026-09-14)
- **CI snapshot**: test_shell job 155191 (3277 tests, 7 failures), test_sql job 155194 (17463 tests, 2 failures)
- **Evidence bundle**: `~/gh/cubrid-circleci-analyzer/data/CBRD-26357/38093ea/`
- **Companion report**: `ci_analysis_report_38093ea_codex.md` (signature-level inventory). This document adds locally *verified* root causes for the two cases that were not trivially attributable, plus a short verdict per remaining failure.

## Executive Summary

Both deep-dived failures are **testcase-expectation breakages, not engine defects**.

1. **`temp_enc_09` (TDE)** — develop's [CBRD-27235] (#7831) moved the CREATE INDEX sort into the new `btree_sort.c`, whose debug trace prints `btree_sort(): tde_encrypted` instead of `sort_listfile(): tde_encrypted`. The test greps only `sort_listfile`, so exactly one `= 0` and one `= 1` line disappear. **Not OOS-related**; reproduces on plain develop debug builds.
2. **`cbrd_25080` (optimizer)** — the printed selectivity of `col_c='11'` flipped from a sampled `0.099921` (develop) to an exactly-correct `0.1` (feat/oos) because a fixed-seed 90k/100k reservoir feeds a Wald-bound MCV qualification that sits on a razor edge for this perfectly uniform column (counts ~9000±29 vs cutoff ≈9060). feat/oos's heap rework changes the physical row stream, flipping the draw from 1 MCV to 0 MCVs. **OOS-triggered but not an OOS bug** — the feat/oos estimate is the statistically correct one; the answer encodes develop's borderline sampling artifact.

## Failure Inventory (all 9, with verdicts)

| # | Suite | Case | Observed signature | Verdict |
|---|-------|------|--------------------|---------|
| 1 | shell | `bug_bts_5423` | paramdump diff: log has `index_build_buffer_size=2.0M`, answer does not | Develop-side: new parameter from [CBRD-27235]; answer stale (inferred) |
| 2 | shell | `bug_bts_9836` | paramdump diff on `call_stack_dump_activation_list` | feat/oos adds 3 `ER_HEAP_OOS_*` codes to the default `call_stack_dump_error_codes[]`; printed numbers also shift on every develop merge; develop-based answers mismatch (verified at source level) |
| 3 | shell | `bug_bts_14120` | same `call_stack_dump_activation_list` diff | Same cause as #2 |
| 4 | shell | `temp_enc_09` | 3+3 `sort_listfile` TDE traces vs 4+4 expected | **Deep dive below — develop-side [CBRD-27235], not OOS** |
| 5 | shell | `cbrd_27064` (CDC) | `EXTRACT_ERROR: rc=-10`, 0/700 and 0/2400 overflow DML events captured | Signature only; CDC-on-overflow is an active OOS work area ([CBRD-26939] PR #7897) — plausible OOS relation, not yet analyzed |
| 6 | shell | `cbrd_27075` (CDC) | `EXTRACT_ERR=3` per page-size config (20K/40K/80K payloads), `CONFIGS_OK=0` | Same bucket as #5 |
| 7 | shell | `cbrd_25080` | plan diff: `sel ?.?` vs `?.??????`, `card ?????` vs `????` | **Deep dive below — razor-edge MCV statistics, OOS-triggered, brittle answer** |
| 8 | sql | `bug_bts_10516` | expected `Error:-1382`, got `Error:-1383` | OOS error-code renumbering: answers on `tc/pr-6864` pinned `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` when it was −1382; develop merges inserted `ER_CDC_ARCHIVE_KEPT`(−1379), `ER_SP_PARALLEL_ENABLE_NO_SQL`(−1380), `ER_VACUUM_MASTER_DAEMON_NOT_AVAILABLE`(−1381), shifting the OOS block to −1382..−1386 (verified) |
| 9 | sql | `fbo_ddl02` | identical `-1382` vs `-1383` | Same cause as #8 |

## Deep Dive 1: `temp_enc_09` — trace renamed by the index-build sort split

**Test mechanics** (`shell/_36_damson/cbrd_23608_tde/temp_enc_09`, debug builds only): runs ORDER BY, GROUP BY, an analytic function, and CREATE INDEX on a plain table `ttt` and an encrypted table `ttt_enc`, then compares:

```sh
grep "TDE:" csql.err | grep "sort_listfile" > result.log
```

The answer expects 4×`tde_encrypted = 0` + 4×`tde_encrypted = 1` (one per sort-triggering statement per table). CI produced 3+3 — the CREATE INDEX line missing on each side.

**Root cause (observed in source at the tested commit):** [CBRD-27235] "Separate the b+tree index build sort from the query sort" (#7831, merged from develop by `38093ea85`) introduces `src/storage/btree_sort.c`. The index-build path no longer goes through `sort_listfile()`; its TDE trace is now:

```c
tde_er_log ("btree_sort(): tde_encrypted = %d\n", sort_param->tde_encrypted);   /* btree_sort.c:1098 */
```

while the query sorts still log `sort_listfile(): tde_encrypted = %d` (`external_sort.c:1504`). The grep for `sort_listfile` therefore drops exactly the two CREATE INDEX traces.

**Relation to OOS: none.** This fails on any develop debug CI. Fix belongs on the develop testcases branch (grep for both `sort_listfile` and `btree_sort`, or regenerate the answer); `tc/pr-6864` inherits it.

## Deep Dive 2: `cbrd_25080` — razor-edge MCV qualification flipped by row-stream order

**Failure**: cases 3–4 (`no_limit_test`, `limit_test`) diff only in masked numbers:

- actual `(sel ?.?)` = `0.1`, `card ?????` = `10000`
- answer `(sel ?.??????)` ≈ `0.099921`, `card ????` ≈ `9992`

The answer being compared is the Sep-11 re-baseline on `cubrid-testcases-private-ex` `tc/pr-6864` (`ea4040a87`, tc-sync-bot for engine PR #7622 / [CBRD-27094]); the plan *shape* (iscan + skip ORDER BY) already matches — only the estimate digits differ.

**A/B reproduction** (local debug builds, client/server mode, identical repro of the test's setup):

| Build | `sel col_c='11'` | `card` | Histogram state |
|---|---|---|---|
| feat/oos `4f43198c2` (pre-merge; CI at `38093ea` identical) | `0.1` exactly | 10000 | `mcv_count=0`, `nonmcv_distinct=10`, `total_rows=100000` |
| develop `f1ae86ff7` (the merge's develop parent) | `0.099921` | 9992 | `mcv_count=1` (freq `0.100711`), `nonmcv_distinct=9` |

**Verified causal chain** (gdb on the exact binaries):

1. Histogram fetch and probe succeed on both branches — no error is raised or swallowed (`stats_get_histogram`, `db_get_histogram` for all 8 columns, every `er_set` traced). This rules out an OOS catalog/blob read failure.
2. With 0 MCVs, `histogram_get_equal_selectivity` prices `'11'` by the residual rule `(1 − Σmcv − nullfrac) / ndistinct = 1/10 = 0.1` — the **true selectivity**. With develop's 1 MCV, it prices `(1 − 0.100711)/9 = 0.099921`.
3. `UPDATE STATISTICS` collects via a **fixed-seed** reservoir (seed 0 unless `WITH RANDOM SEED`) of `sample_size = 300 buckets × 300 = 90,000` rows over the 100,000-row table. `col_c` is perfectly uniform (10 values × 10,000): reservoir counts land at ~9,000 ± 28.5 (1σ, hypergeometric).
4. `stats_analyze_mcv_list` (Wald-type lower confidence bound) has its qualification cutoff at ≈ 9,060 for these parameters. Observed top candidate counts: develop setup-context draw **9,064** (qualifies → 1 MCV); feat/oos draw **~9,055** (fails → 0 MCVs). Standalone re-collections on *both* branches drew 9,051–9,055 → 0 MCVs → `sel 0.1` on develop too, confirming the decision is a razor edge, not a branch defect.
5. The seed is fixed, so the differing draw is caused by a differing **row stream**: same 100,000 rows, same 1,125 pages, but feat/oos's heap/file-manager rework (`heap_file.c` ±1,935 lines vs develop) yields a different physical row order into the reservoir. A benign layout change flips the statistical coin.

**Relation to OOS: indirect.** No OOS code misbehaves; OOS's storage layout legitimately perturbs a borderline statistics decision, and the answer file encodes the digit-width of develop's particular draw.

**Recommended actions**

1. Re-baseline the three `cbrd_25080` answers on `tc/pr-6864` from a feat/oos CI debug build (`sel ?.?`, `card ?????`).
2. Consider filing an upstream issue: MCV qualification for near-uniform columns at this sample ratio is unstable under any row-order change, which makes plan-dump regression tests flaky by construction. Options: hysteresis in `stats_analyze_mcv_list`, exact counting when `ndistinct ≤ mcv_cap`, or masking estimate widths in CTP answers.

## Evidence and Methods

- Collector: `cubrid-ci 0.1.0`, suites pinned to `38093ea85…`; per-failure `diff.txt`/`message.txt`; CDC details from `test-shell.xml` JUnit artifacts (nodes 24/38).
- Source inspection at the exact tested commit (local worktree HEAD == CI commit).
- gdb traces on debug builds: `stats_get_histogram` / `db_get_histogram` / `er_set` (fetch path), `histogram_get_equal_selectivity` outcome (`success=1, selectivity=0.1`), histogram internals (`mcv_count`, `total_rows`), `stats_analyze_mcv_list` candidate counts.
- A/B worktree: `~/gh/cb/oos-ab-develop` at `f1ae86ff7` (develop merge parent), same debug preset.
- Limitations: CDC cases (#5/#6) and paramdump cases (#1–#3) were attributed from signatures plus source reading, without local reruns; the CDC `rc=-10` extraction failures still need a dedicated deep dive.
