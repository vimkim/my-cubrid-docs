# CI Failure Analysis and Fix Plan: `c6334f6` / PR #7415

Report companion: `test_shell_failure_c6334f6_pr7415_circleci135930.md`

Target CI job: `https://app.circleci.com/pipelines/github/CUBRID/cubrid/32125/workflows/3f4e16df-84ad-45f0-8ab2-71c2680ba7fc/jobs/135930/tests`

## Current Assessment

Job 135930 has 8 failed TCs. They look like testcase/output mismatches, not code defects in PR #7415:

| Group | TCs | Plan |
|-------|-----|------|
| Legacy overflow assumptions | `tbl_enc_08`, `tbl_enc_14`, `cbrd_26527` | Report-only for PR #7415. Fix tests to accept OOS-era storage layout. |
| OOS error-code default list | `bug_bts_9836`, `bug_bts_14120` | Report-only. Refresh expected answers or derive expected list. |
| LOB locator nondeterminism | `bigPageSize` | Report-only. Apply testcase determinism fix if/when TC changes are requested. |
| Exact runtime counters | `cbrd_22803`, `cbrd_20145_1` | Baseline before answer update. No PR #7415 code change. |

## Analysis Plan

1. Freeze the CI evidence.
   - Keep the CircleCI test API URL in reports: `https://circleci.com/api/v1.1/project/github/CUBRID/cubrid/135930/tests`.
   - Keep artifact node assignments:
     - node 1: `tbl_enc_14`
     - node 11: `bug_bts_9836`
     - node 18: `bigPageSize`
     - node 27: `cbrd_20145_1`
     - node 33: `bug_bts_14120`
     - node 35: `cbrd_22803`
     - node 38: `tbl_enc_08`
     - node 43: `cbrd_26527`
   - Do not infer from side-by-side `diff -y` alone for long lines; use raw `diff -b` lines from artifacts.

2. Validate PR #7415 scope independently.
   - Confirm `src/storage/file_manager.c` handles the three intended utility paths:
     - `file_header_dump_descriptor()` prints `OOS file`.
     - `file_tracker_get_and_protect()` skips `FILE_OOS` in the generic online check path until owner metadata exists.
     - `file_tracker_item_spacedb()` folds OOS pages into heap totals.
   - Verify no failed TC reports `assert`, `assert_release`, `ER_FAILED`, core, or `Internal Error` from these paths.

3. Classify each TC before proposing fixes.
   - If the failure is an output/answer mismatch with no internal error, record it as TC mismatch.
   - If the failure is a crash, assert, loader error, data-content mismatch, or recovery/logging error, escalate to engine debugging.
   - For job 135930, all 8 fit the first bucket.

## Fix Plan by Category

### 1. OOS-aware `diagdb` tests

TCs: `tbl_enc_08`, `tbl_enc_14`, `cbrd_26527`

Problem: the tests assume large table values use legacy heap overflow and therefore look for `MULTIPAGE_OBJECT_HEAP` / `Overflow for HFID`. OOS changes that physical representation.

Fix direction:

1. Keep the current checks for ordinary heap/table presence where they still apply.
2. For OOS-enabled builds, do not require `MULTIPAGE_OBJECT_HEAP` for large variable columns.
3. For TDE tests, verify encryption metadata for the actual file types present rather than requiring the old overflow file line.
4. For `cbrd_26527` Case 4, split the predicate:
   - if a legacy overflow HFID exists, verify it disappears after `DROP TABLE`;
   - if no legacy overflow HFID exists because OOS handled the row, verify OOS/table-owned pages are absent after drop or mark the overflow-only subcheck as not applicable.

Report-only note: no PR #7415 engine fix is indicated by these three failures.

### 2. `call_stack_dump_activation_list` answers

TCs: `bug_bts_9836`, `bug_bts_14120`

Problem: actual output includes the OOS error codes added to `call_stack_dump_error_codes[]`:

```text
-1378,-1380,-1381
```

Fix direction:

1. Update answer files to include the new OOS codes after `-50`, matching current `system_parameter.c` order.
2. Prefer generating the expected default list from the running binary if the testcase framework supports it; hardcoded full lists fail every time an error code is intentionally added.
3. Keep this as a testcase update. The branch intentionally wants OOS corruption/invalid-argument errors to trigger call-stack dumps.

Report-only note: no engine change is needed unless product decides these OOS errors should not be default call-stack dump targets.

### 3. `bigPageSize` determinism

TC: `bigPageSize`

Problem: the query uses `ORDER BY 1 DESC LIMIT 1`; all 256 copied rows tie on the selected key. The source and loaded target DB can select different physical rows. The only current diff is raw CLOB/BLOB locator text.

Fix direction:

1. Preferred: make the selected row deterministic by adding `id` to the projection/order predicate, for example `ORDER BY 1 DESC, id DESC`, if both DBs preserve the same logical `id`.
2. Alternative: mask `file:...` locator strings before comparing source and target output.
3. Alternative: compare LOB content with conversion functions instead of raw locator strings, but that drops locator-preservation coverage.

Report-only note: job 135930 shows `loaddb` succeeded and `load.answer` matched; do not debug OOS loader code from this failure alone.

### 4. Exact counter/statistics outputs

TCs: `cbrd_22803`, `cbrd_20145_1`

Problem:

- `cbrd_22803`: `Num_hit` and `Num_page_request` differ by 1 in CS mode.
- `cbrd_20145_1`: `MNT_SERVER_COPY_STATS` receive size changed from `86400` to `90864`.

Fix direction:

1. Run the same TCs on a clean `develop` build and on current `feat/oos` before editing answers.
2. If the drift is stable on `feat/oos`, update answer files or mask volatile counters.
3. If the drift is unstable across reruns, convert the test to compare invariants instead of exact runtime counters.
4. Only debug engine code if the counters indicate resource leakage, a monotonic growth pattern, or an unexpected error in logs.

Report-only note: PR #7415 does not touch these monitor paths directly.

## Execution Order

1. Treat PR #7415 CI job 135930 as a report-only TC mismatch set.
2. Do not modify PR #7415 code based on this CI job.
3. If testcase edits are requested, start with the two stable answer updates:
   - `bug_bts_9836`
   - `bug_bts_14120`
4. Next fix `bigPageSize` determinism, because the previous preserved-log diagnosis already identifies the root cause.
5. Then make the three `diagdb` tests OOS-aware.
6. Leave the two counter/stat tests until after a clean baseline comparison.

## Stop Conditions

Do not continue into engine debugging unless at least one of these appears in a rerun:

- `FILE_OOS` assert or `assert_release`;
- server `Internal Error`;
- loader object failures in `bigPageSize`;
- data-content mismatch after masking volatile locator names;
- `DROP TABLE` leaves `UNKNOWN-CLASS` or unreclaimed table-owned pages;
- exact counter drift grows across reruns instead of staying at a stable expected-output delta.

## Grill Review Notes

| Question | Decision |
|----------|----------|
| Is this plan mixing PR #7415 code fixes with testcase cleanup? | No. PR #7415 code is treated as independently scoped utility hardening; the 8 failures are testcase-output work. |
| Are there any failures that need immediate C/C++ debugging? | Not from the available job 135930 evidence. |
| Which fixes are safest to do first? | The call-stack answer updates, because the raw diff and source code exactly identify the new OOS codes. |
| Which fixes need more evidence? | `cbrd_22803` and `cbrd_20145_1`; exact counters should be baselined before answer churn. |
| Does the plan satisfy "If it looks like a TC mismatch, just report"? | Yes. It reports all 8 as TC mismatches and avoids proposing PR #7415 engine changes. |
