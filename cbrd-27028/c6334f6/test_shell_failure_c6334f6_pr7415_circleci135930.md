**Ultimate goal**: remove all `test_shell` failures on the `develop` <- `origin/feat/oos` tracking PR, currently [CUBRID/cubrid#6864](https://github.com/CUBRID/cubrid/pull/6864).

| JIRA Issue | PR | Commit | test_shell (web) | test_shell tests API (agent-fetchable) |
|------------|----|--------|------------------|----------------------------------------|
| [CBRD-26357](https://jira.cubrid.org/browse/CBRD-26357) | [#6864](https://github.com/CUBRID/cubrid/pull/6864) (`develop` <- `feat/oos`) | `5b5ff588f8fbd69f1ac70900d05fc9d0efe4d3ff` | [CircleCI job 135486](https://app.circleci.com/pipelines/github/CUBRID/cubrid/32007/workflows/e7df3128-6f19-4982-b3dd-56dcd22aaba7/jobs/135486/tests) | `https://circleci.com/api/v1.1/project/github/CUBRID/cubrid/135486/tests` |
| [CBRD-27028](https://jira.cubrid.org/browse/CBRD-27028) | [#7415](https://github.com/CUBRID/cubrid/pull/7415) (`feat/oos` <- `oos-m2-plan1-file-oos-utilities`) | `c6334f6a69a11c2037ceb34b7f75e5022523dc4a` | [CircleCI job 135930](https://app.circleci.com/pipelines/github/CUBRID/cubrid/32125/workflows/3f4e16df-84ad-45f0-8ab2-71c2680ba7fc/jobs/135930/tests) | `https://circleci.com/api/v1.1/project/github/CUBRID/cubrid/135930/tests` |

# test_shell Failure Report: PR #7415 at `c6334f6`

Report date: 2026-07-08 KST

Scope: CircleCI `test_shell` job 135930 for PR #7415, branch `pull/7415/head`, commit `c6334f6a69a11c2037ceb34b7f75e5022523dc4a`. The API reports 8 failed TCs, 3193 successful TCs, and 30 skipped TCs.

---

## Executive Summary

**Verdict**: the 8 failures visible in job 135930 are testcase/output expectation mismatches, not evidence that PR #7415's `FILE_OOS` utility handling broke engine behavior.

PR #7415 changes one source file, `src/storage/file_manager.c`, to:

- print `OOS file` instead of asserting in `file_header_dump_descriptor()`;
- skip `FILE_OOS` in online file-tracker protection until owner metadata exists;
- fold `FILE_OOS` space into `SPACEDB_HEAP_FILE` instead of hitting `assert_release(false)`.

None of the 8 failures shows a `FILE_OOS` assert, fatal, or internal error. The targeted utility-hardening PR is still necessary, but the remaining CI failures are expected-output/test-predicate drift around OOS-era storage layout, OOS error-code defaults, volatile LOB locator strings, and exact runtime counters.

| Category | Count | TCs | Code fix for PR #7415? |
|----------|-------|-----|------------------------|
| OOS-vs-legacy-overflow `diagdb` expectation drift | 3 | `tbl_enc_08`, `tbl_enc_14`, `cbrd_26527` | No. Report as TC expectation drift. |
| OOS error-code additions in `call_stack_dump_activation_list` | 2 | `bug_bts_9836`, `bug_bts_14120` | No. Answer files lag the OOS branch defaults. |
| Known LOB locator nondeterminism in `bigPageSize` | 1 | `bigPageSize` | No. Existing preserved-log diagnosis says TC mismatch. |
| Exact counter/statistics output drift | 2 | `cbrd_22803`, `cbrd_20145_1` | No direct PR #7415 link. Baseline before answer changes. |

---

## Source Material

- CircleCI job metadata: `https://circleci.com/api/v1.1/project/github/CUBRID/cubrid/135930`
- CircleCI tests API: `https://circleci.com/api/v1.1/project/github/CUBRID/cubrid/135930/tests`
- CircleCI artifacts API: `https://circleci.com/api/v1.1/project/github/CUBRID/cubrid/135930/artifacts`
- Local OOS context: `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md`
- Local testcase tree: `/home/vimkim/cubrid-testcases-private-ex`
- Prior preserved-log `bigPageSize` diagnosis: `/home/vimkim/gh/my-cubrid-docs/cbrd-26357/5b5ff58/failed_tcs/bigpagesize-report.md`
- PR #7415 design docs: `/home/vimkim/gh/my-cubrid-docs/cbrd-27028/`

Limitations: I did not rerun the 8 TCs locally for this report. The classification uses CircleCI tests/artifacts, local testcase scripts/answers, PR #7415 code, and existing preserved-log diagnostics.

---

## Failure Inventory

| # | TC | CI evidence | Classification | Action |
|---|----|-------------|----------------|--------|
| 1 | `shell/_36_damson/cbrd_23608_tde/tbl_enc_14/cases/tbl_enc_14.sh` | Actual `diagdb -d1` output lacks answer-side `MULTIPAGE_OBJECT_HEAP` / `Overflow for HFID` lines for table data. `BTREE_OVERFLOW_KEY` remains. | OOS-vs-overflow TC drift | Report-only for PR #7415. Make TC OOS-aware separately. |
| 2 | `shell/_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh` | Cases 2 and 3 differ only by added `-1378,-1380,-1381` in `call_stack_dump_activation_list`. | Answer mismatch from OOS error-code defaults | Report-only; answer update. |
| 3 | `shell/_35_cherry/issue_21654_server_side_loaddb/bigPageSize/cases/bigPageSize.sh` | `loaddb` succeeds and `load.answer` matches. Only `cl`/`bl` `file:...` locator strings differ between source and target query output. | Known TC mismatch / nondeterministic tied-row comparison | Report-only; see prior preserved-log diagnosis. |
| 4 | `shell/_06_issues/_17_1h/cbrd_20145_1/cases/cbrd_20145_1.sh` | `MNT_SERVER_COPY_STATS` receive size changes from `86400` to `90864`; other checks pass. | Runtime stats exact-output drift | Baseline before answer update. |
| 5 | `shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh` | Case 1 differs only by added `-1378,-1380,-1381` in server-side `call_stack_dump_activation_list`. Case 2 passes. | Answer mismatch from OOS error-code defaults | Report-only; answer update. |
| 6 | `shell/_06_issues/_20_2h/cbrd_22803/cases/cbrd_22803.sh` | CS-mode `show page buffer status`: `Num_hit` 765 vs 764, `Num_page_request` 831 vs 830. | Exact page-buffer counter drift | Baseline before answer update. |
| 7 | `shell/_36_damson/cbrd_23608_tde/tbl_enc_08/cases/tbl_enc_08.sh` | Actual `diagdb -d1` output lacks answer-side `vfid`, `MULTIPAGE_OBJECT_HEAP`, and `Overflow for HFID` lines. | OOS-vs-overflow TC drift | Report-only for PR #7415. Make TC OOS-aware separately. |
| 8 | `shell/_06_issues/_26_1h/cbrd_26527/cases/cbrd_26527.sh` | Cases 1-3 pass; Case 4 cannot extract a `MULTIPAGE_OBJECT_HEAP` HFID for `dba.tbl` from `diagdb_before.log`. | OOS-vs-overflow parser assumption | Report-only for PR #7415. Make TC predicate OOS-aware. |

---

## Category 1: OOS-vs-Overflow `diagdb` Drift

Affected TCs: `tbl_enc_08`, `tbl_enc_14`, `cbrd_26527`

These tests assume that large values appear through legacy heap overflow (`MULTIPAGE_OBJECT_HEAP`) in `diagdb` output. On the OOS branch, large variable columns can be represented through `FILE_OOS` instead of heap overflow. That changes diagnostic shape without proving row corruption.

The two TDE tests create encrypted tables with `varchar(20000)` and filter `diagdb -d1` output around `ttt|Overflow`. The expected files include `MULTIPAGE_OBJECT_HEAP` / `Overflow for HFID`. The actual output is missing those legacy overflow lines and reports no `Internal Error`.

`cbrd_26527` is even more explicit: the test extracts a `MULTIPAGE_OBJECT_HEAP` HFID tied to `dba.tbl`. In job 135930, Cases 1-3 prove the table appears before `DROP TABLE`, `UNKNOWN-CLASS` is absent after drop, and table pages are reclaimed. Only Case 4 fails because the test cannot find the legacy overflow HFID premise.

Root cause: **storage-layout-sensitive TC assumptions**, not PR #7415 failure. PR #7415 removes assert-prone utility paths for `FILE_OOS`; it does not promise that old overflow-oriented answer files remain valid.

---

## Category 2: `call_stack_dump_activation_list` Answer Drift

Affected TCs: `bug_bts_9836`, `bug_bts_14120`

The raw artifact diff is exact and stable. Actual output includes OOS error codes:

```text
-1378,-1380,-1381
```

The local source explains why. `src/base/system_parameter.c` adds these to `call_stack_dump_error_codes[]`:

```text
ER_HEAP_OOS_BAD_INLINE_HEADER       -> -1378
ER_HEAP_OOS_CORRUPTED_RECORD       -> -1380
ER_HEAP_OOS_INVALID_ARGUMENT       -> -1381
```

The checked-in answer files under `/home/vimkim/cubrid-testcases-private-ex` still expect the pre-OOS list. This is a testcase answer mismatch caused by intended OOS diagnostics, not a product regression.

---

## Category 3: `bigPageSize` LOB Locator Mismatch

Affected TC: `bigPageSize`

CircleCI artifact node 18 shows:

- `loaddb` succeeds;
- `load.answer` vs `load.log` is OK: 256 objects inserted, 0 failed;
- only `bigPageSize-1` is NOK;
- the only raw diff is the CLOB/BLOB locator strings:

```text
< cl : file:.../ces_560/...
< bl : file:.../ces_524/...
---
> cl : file:.../ces_126/...
> bl : file:.../ces_444/...
```

This matches the preserved-log diagnosis in the previous report set: 256 rows are tied on `ORDER BY 1 DESC`, so source and target DBs can select different physical rows. The locator values differ, while the loaded data and LOB preservation path are not shown to be broken.

Root cause: **testcase comparison nondeterminism**. This should be reported as TC mismatch unless a new rerun shows data-content mismatch or loader errors.

---

## Category 4: Exact Counter/Statistics Drift

Affected TCs: `cbrd_22803`, `cbrd_20145_1`

`cbrd_22803` asserts exact page-buffer counters after a small CS-mode workflow. Job 135930 differs by one hit and one page request:

```text
Num_hit          765 actual vs 764 expected
Num_page_request 831 actual vs 830 expected
```

`cbrd_20145_1` asserts exact communication histogram sizes. `MNT_SERVER_COPY_STATS` receive size changes:

```text
90864 actual vs 86400 expected
```

The OOS branch adds storage/page concepts and monitor output such as `PAGE_OOS`; exact counter tests are fragile across such branch-wide changes. These are not touched by PR #7415's one-file `file_manager.c` change. Treat them as baseline/answer-drift candidates, not a PR #7415 engine defect.

---

## PR #7415 Impact Matrix

| TC | Should PR #7415 fix this failure? | Reason |
|----|-----------------------------------|--------|
| `tbl_enc_08` | No | Failure is missing legacy overflow lines, not a `FILE_OOS` assert. |
| `tbl_enc_14` | No | Same. PR commit message already states this still fails on expected-output assumptions. |
| `cbrd_26527` | No | Cases 1-3 pass; Case 4 assumes `MULTIPAGE_OBJECT_HEAP`. |
| `bug_bts_9836` | No | Expected answer lacks OOS call-stack error codes. |
| `bug_bts_14120` | No | Same. |
| `bigPageSize` | No | Known LOB locator tied-row comparison mismatch; loader output is OK. |
| `cbrd_22803` | No | Exact page-buffer counter drift; no direct PR #7415 change. |
| `cbrd_20145_1` | No | Exact monitor payload-size drift; no direct PR #7415 change. |

---

## Recommended Disposition

For PR #7415 / CBRD-27028, **report these as TC mismatches and do not chase engine code changes from this CI job alone**. The intended PR scope is still valid: remove `FILE_OOS` assertion/fatal hazards in `diagdb`, `spacedb`, and `checkdb` utility paths.

The testcase work should be tracked separately:

1. Make `tbl_enc_08`, `tbl_enc_14`, and `cbrd_26527` OOS-aware.
2. Refresh `bug_bts_9836` and `bug_bts_14120` answers for the OOS call-stack default list.
3. Fix `bigPageSize` determinism or mask volatile LOB locator strings.
4. Baseline `cbrd_22803` and `cbrd_20145_1` on `develop` vs `feat/oos` before changing exact counter answers.

---

## Grill Review Notes

| Question | Answer |
|----------|--------|
| Did any failed TC show a `FILE_OOS` assert/fatal? | No. The visible failures are diffs or parser assumptions; server internal-error checks are 0 where shown. |
| Are `bug_bts_9836` and `bug_bts_14120` really only answer drift? | Yes. The raw `diff -b` lines show actual output inserts `-1378,-1380,-1381`; local source confirms those OOS error codes are in `call_stack_dump_error_codes[]`. |
| Is `bigPageSize` underdiagnosed? | No for this run. Artifact node 18 exposes the raw diff: only `cl`/`bl` locator strings differ, and `loaddb` output matches `load.answer`. |
| Is PR #7415 overclaimed as a fix for all 8 failures? | No. The report narrows PR #7415 to utility assert hardening and treats all 8 visible failures as testcase/output drift. |
| What remains risky? | The two exact counter/statistics failures should be compared against clean `develop` and `feat/oos` baselines before answer changes. They are not direct evidence against PR #7415. |
