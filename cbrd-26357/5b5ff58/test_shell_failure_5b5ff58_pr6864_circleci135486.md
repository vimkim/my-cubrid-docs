**Ultimate goal**: remove all `test_shell` failures on the `develop` <- `origin/feat/oos` tracking PR, currently [CUBRID/cubrid#6864](https://github.com/CUBRID/cubrid/pull/6864).

| JIRA Issue | PR | Commit | test_shell (web) | test_shell tests API (agent-fetchable) |
|------------|----|--------|------------------|----------------------------------------|
| [CBRD-26357](https://jira.cubrid.org/browse/CBRD-26357) | [#6864](https://github.com/CUBRID/cubrid/pull/6864) (`develop` <- `feat/oos`) | `5b5ff588f8fbd69f1ac70900d05fc9d0efe4d3ff` | [CircleCI job 135486](https://app.circleci.com/pipelines/github/CUBRID/cubrid/32007/workflows/e7df3128-6f19-4982-b3dd-56dcd22aaba7/jobs/135486/tests) | `https://circleci.com/api/v1.1/project/github/CUBRID/cubrid/135486/tests` |
| [CBRD-27028](https://jira.cubrid.org/browse/CBRD-27028) | [#7415](https://github.com/CUBRID/cubrid/pull/7415) (`feat/oos` <- `oos-m2-plan1-file-oos-utilities`) | PR head observed: `c6334f6a69a11c2037ceb34b7f75e5022523dc4a` | Related `FILE_OOS` utility-hardening PR; visible job 135486 failures still look like OOS-vs-overflow output drift | N/A |

# test_shell Failure Report: PR #6864 at `5b5ff58`

**Recommended file name**: `test_shell_failure_5b5ff58_pr6864_circleci135486.md`

**Report date**: 2026-07-08 KST

**Scope**: CircleCI `test_shell` job 135486 for PR #6864 at commit `5b5ff58`. The job reports 9 failed TCs. Skipped TCs in the CircleCI API are intentionally excluded from the failure count.

---

## Source Material

- CircleCI tests API for job 135486.
- PR #6864 metadata: head `feat/oos`, base `develop`, observed head `5b5ff588f8fbd69f1ac70900d05fc9d0efe4d3ff`.
- PR #7415 metadata and diff: `src/storage/file_manager.c` only.
- Local OOS context: `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md`.
- Local CTP scripts under `/home/vimkim/cubrid-testcases-private-ex`.

Limitations: this docs checkout is not a CUBRID source tree, so no local LSP/build validation was performed from this directory. I did not reproduce the 9 TCs locally; this report is based on CI output, test scripts, OOS context, and the PR #7415 diff.

---

## Executive Summary

The 9 failures split into four buckets:

| Category | Count | TCs | Likely relation to OOS | Expected PR #7415 impact |
|----------|-------|-----|------------------------|---------------------------|
| OOS-vs-overflow `diagdb` expectation drift, with related `FILE_OOS` utility hardening | 3 | `tbl_enc_08`, `tbl_enc_14`, `cbrd_26527` | Direct | PR #7415 removes related assert-prone utility paths, but the visible failures likely still need answer/parser changes |
| Counter/statistics output drift | 2 | `cbrd_22803`, `cbrd_20145_1` | Possibly incidental OOS/branch I/O change | None expected |
| Config/paramdump output drift | 2 | `bug_bts_14120`, `bug_bts_9836` | Not obviously OOS-specific | None expected |
| Resource or underdiagnosed utility failures | 2 | `bug_bts_6867`, `bigPageSize` | Needs reproduction/artifacts | None expected |

The 3 targeted failures are OOS-related, but the visible CircleCI tests API output does **not** show `FILE_OOS` assertion crashes for them. It shows `diagdb` output/parser drift caused by records that used to be represented as `MULTIPAGE_OBJECT_HEAP` overflow now being represented through OOS behavior. PR #7415 is still relevant hardening because it removes three `FILE_OOS` assertion/default-failure sites in `file_manager.c`:

- `file_header_dump_descriptor`: print a simple `OOS file` descriptor instead of `assert(false)`.
- `file_tracker_get_and_protect`: allow `FILE_OOS` during read-only tracker iteration without returning an unprotected VFID.
- `file_tracker_item_spacedb`: fold `FILE_OOS` into `SPACEDB_HEAP_FILE` instead of `assert_release(false)`.

Important nuance: PR #7415 should remove latent `FILE_OOS` assert/fatal hazards in utility paths. It should **not** be treated as sufficient for the observed job 135486 failures unless a rerun proves it, because those observed failures are mostly missing expected overflow lines or parser assumptions about `MULTIPAGE_OBJECT_HEAP`.

---

## Failure Inventory

| # | TC | What it tests | CI failure evidence | Category | Related? |
|---|----|---------------|---------------------|----------|----------|
| 1 | `shell/_35_cherry/issue_21654_server_side_loaddb/bigPageSize/cases/bigPageSize.sh` | `unloaddb` from source DB, then `loaddb` into a 4 KB page-size DB; table includes large `varchar`, large `string`, JSON, CLOB, and BLOB values | CircleCI API only says `Test failed`; no diff/fatal detail exposed | Underdiagnosed utility failure | Likely OOS-adjacent, not proven |
| 2 | `shell/_06_issues/_20_2h/cbrd_22803/cases/cbrd_22803.sh` | `show page buffer status` in CS and SA modes | CS-mode answer drift: `Num_hit` 765 vs 764, `Num_page_request` 831 vs 830 | Counter/statistics drift | Possibly incidental |
| 3 | `shell/_06_issues/_12_2h/bug_bts_6867/cases/bug_bts_6867.sh` | UPDATE/checkpoint/server-stop timing with modified checkpoint/shutdown parameters | Server fatal: `Resources allocation failed. Raise up 'max_bestspace_entries=1000000'.` | Resource/config regression | Unknown |
| 4 | `shell/_36_damson/cbrd_23608_tde/tbl_enc_08/cases/tbl_enc_08.sh` | TDE table with large encrypted `varchar(20000)`, then `diagdb -d1` filtered around class/overflow metadata | Actual output is missing answer-side `MULTIPAGE_OBJECT_HEAP` / `Overflow for HFID` lines; server log check reports no `Internal Error` | OOS-vs-overflow `diagdb` expectation drift | Direct |
| 5 | `shell/_36_damson/cbrd_23608_tde/tbl_enc_14/cases/tbl_enc_14.sh` | TDE table with large encrypted primary-key `varchar(20000)`, then `diagdb -d1` filtered around class/overflow metadata | Actual output is missing answer-side `MULTIPAGE_OBJECT_HEAP` / `Overflow for HFID` lines; server log check reports no `Internal Error` | OOS-vs-overflow `diagdb` expectation drift | Direct |
| 6 | `shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh` | `cubrid paramdump -b` for error-log and call-stack dump parameters before/after a broker/client test | Answer drift in `call_stack_dump_*`/error-log parameter dump output | Config/paramdump drift | Not obviously OOS |
| 7 | `shell/_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh` | `call_stack_dump_activation_list` parameter parsing with explicit/default values | `paramdump` answer drift for `call_stack_dump_activation_list` in cases 2 and 3 | Config/paramdump drift | Not obviously OOS |
| 8 | `shell/_06_issues/_26_1h/cbrd_26527/cases/cbrd_26527.sh` | DROP TABLE should reclaim heap/overflow pages; validates by parsing `diagdb -d 2` before/after | Case 4 failed to extract `MULTIPAGE_OBJECT_HEAP` HFID for `dba.tbl` from `diagdb_before.log` | OOS-vs-overflow `diagdb` parser assumption | Direct |
| 9 | `shell/_06_issues/_17_1h/cbrd_20145_1/cases/cbrd_20145_1.sh` | `;.hist` communication histogram and monitor counters after simple SQL | Histogram/counter answer drift in client request statistics | Counter/statistics drift | Possibly incidental |

---

## Category 1: OOS-vs-Overflow `diagdb` Drift (3 TCs)

| TC | Utility surface | Why OOS matters | PR #7415 expectation |
|----|-----------------|-----------------|----------------------|
| `tbl_enc_08` | `cubrid diagdb -d1` | Encrypted large `varchar(20000)` used to produce answer-side `MULTIPAGE_OBJECT_HEAP` / `Overflow for HFID` output. With OOS, the large variable value no longer has to appear as a heap overflow file in that shape. | PR #7415 may remove latent `FILE_OOS` descriptor assertion hazards, but the observed diff likely needs an OOS-aware answer/filter update. |
| `tbl_enc_14` | `cubrid diagdb -d1` | Encrypted large primary-key `varchar(20000)` still has btree overflow output, but the table-value overflow lines expected by the answer are absent. | Same as above. |
| `cbrd_26527` | `cubrid diagdb -d2` parser | The test intentionally extracts a `MULTIPAGE_OBJECT_HEAP` HFID for `dba.tbl`; OOS can make that parser premise false even though cases 1-3 confirm the table appears before DROP and disappears after DROP. | PR #7415 may remove related utility hazards, but the observed Case 4 failure needs a changed TC predicate for OOS-era storage. |

**Root cause analysis**: The visible job 135486 failures are best explained as tests assuming heap overflow (`MULTIPAGE_OBJECT_HEAP`) for large values, while OOS externalizes large variable columns through `FILE_OOS` instead. This is not an OOS record read/write correctness problem by itself; it is utility/test expectation drift around storage layout and `diagdb` output.

**PR #7415 relation**: PR #7415 is still an appropriate companion fix because generic file utilities should not assert or default-fail when they encounter `FILE_OOS`. However, its own commit message now notes that targeted `cbrd_26527` and `tbl_enc_14` still fail on expected-output assumptions after the assert handling is fixed. Treat it as necessary hardening, not as a complete fix for the three observed TC failures.

**Expected fix path**:

1. Merge or rebase PR #7415 onto `feat/oos` to remove the latent `FILE_OOS` utility assertions.
2. Rerun the three targeted TCs and check whether any assertion/fatal disappears.
3. Update the TCs for OOS-aware semantics:
   - TDE `diagdb` tests should accept either legacy heap overflow output or the OOS-era absence of `MULTIPAGE_OBJECT_HEAP` for demoted large variable values.
   - `cbrd_26527` should validate DROP reclaim without requiring an overflow HFID when OOS prevents the original overflow layout.

---

## Category 2: Counter and Statistics Drift (2 TCs)

| TC | Evidence | Risk |
|----|----------|------|
| `cbrd_22803` | `show page buffer status` differs by +1 page hit/request in CS mode. | Low by itself. This kind of exact counter assertion is fragile when storage layout or utility setup changes. |
| `cbrd_20145_1` | Communication histogram/monitor counters differ after simple SQL. | Low to medium. Needs comparison against develop or rerun stability before changing expected output. |

**Root cause hypothesis**: these TCs assert exact runtime counters. OOS or adjacent branch setup may add a page request or monitor request without changing user-visible semantics.

**Proposed fix**: rerun after PR #7415 and after any config cleanup. If the drift is stable and intended, adjust the answer filters to normalize volatile counters. If it is unstable, treat as test fragility rather than a product regression.

---

## Category 3: Config/Paramdump Drift (2 TCs)

| TC | Evidence | Risk |
|----|----------|------|
| `bug_bts_14120` | `cubrid paramdump -b` output differs for error-log/call-stack dump parameters. | Medium until compared with a clean develop baseline. |
| `bug_bts_9836` | `call_stack_dump_activation_list` output differs for default-list cases. | Medium until default parameter behavior is confirmed. |

**Root cause hypothesis**: these are not exercising OOS storage. They are sensitive to `cubrid.conf` defaults, restore behavior, or output formatting. Commit `5b5ff58` itself is a hotfix to restore `cubrid.conf` after OOS unittest DB setup, so remaining config-output failures should be treated as config hygiene or expected-output drift until reproduced.

**Proposed fix**: compare `cubrid paramdump` output on `develop` and `feat/oos` with the same generated `cubrid.conf`. Do not update answer files until it is clear whether the changed parameter text is intentional.

---

## Category 4: Resource or Underdiagnosed Failures (2 TCs)

| TC | Evidence | Next diagnostic step |
|----|----------|----------------------|
| `bug_bts_6867` | Server fatal: `Resources allocation failed. Raise up 'max_bestspace_entries=1000000'.` | Reproduce locally or fetch full `/home/ERROR_BACKUP/AUTO_11.5.0.2366-5b5ff58_20260707_083024` artifacts. Inspect whether `max_bestspace_entries` was changed by prior setup or whether OOS/heap bestspace growth is consuming more entries. |
| `bigPageSize` | CircleCI API only says `Test failed`; the script keeps artifacts for a CBRD-27029 investigation and exercises `unloaddb`/`loaddb` across page sizes with large variable data. | Fetch full job artifacts or rerun locally with preserved `load.log`, `csql1.log`, `csql2.log`, schema/object files, and diff output. |

**Root cause status**: not enough CI detail to make a defensible root-cause call.

**Proposed fix**: keep these out of the PR #7415 expected-fix bucket. They need separate artifact review or local reproduction.

---

## PR #7415 Impact Matrix

| Failed TC | Should PR #7415 fix it? | Expected post-PR behavior |
|-----------|-------------------------|---------------------------|
| `tbl_enc_08` | Not by itself | PR #7415 should remove latent `FILE_OOS` utility assertion risk. The observed missing-overflow diff likely still needs an OOS-aware answer/filter update. |
| `tbl_enc_14` | Not by itself | Same as above; PR #7415's own commit message says this still fails on expected-output assumptions after the utility hardening. |
| `cbrd_26527` | Not by itself | Same as above; update the Case 4 predicate so it does not require a `MULTIPAGE_OBJECT_HEAP` HFID when OOS changes the storage layout. |
| `bigPageSize` | No proven impact | Needs artifacts/reproduction. |
| `cbrd_22803` | No expected impact | Counter drift remains unless incidental. |
| `bug_bts_6867` | No expected impact | Resource fatal remains unless incidental. |
| `bug_bts_14120` | No expected impact | Config/paramdump drift remains unless incidental. |
| `bug_bts_9836` | No expected impact | Config/paramdump drift remains unless incidental. |
| `cbrd_20145_1` | No expected impact | Counter drift remains unless incidental. |

---

## Priority Actions

1. P0: merge/rebase PR #7415 into `feat/oos` to remove latent `FILE_OOS` utility asserts, then rerun at least `tbl_enc_08`, `tbl_enc_14`, and `cbrd_26527`.
2. P0: update the three `diagdb`-based TCs for OOS-era storage expectations; the visible job 135486 failures are missing-overflow/parser-premise failures, not direct assert stacks.
3. P1: fetch artifacts or locally rerun `bigPageSize`; the CircleCI tests API does not expose enough detail for root cause.
4. P1: investigate `bug_bts_6867` with full server logs and current `cubrid.conf` to determine why `max_bestspace_entries` is exhausted.
5. P2: compare `cbrd_22803`, `cbrd_20145_1`, `bug_bts_14120`, and `bug_bts_9836` against a clean develop baseline before deciding whether they are answer drift, config leakage, or real regressions.

---

## Grill Review Notes

Self-review questions applied before sharing:

| Question | Answer |
|----------|--------|
| Was the PR #7415 claim narrowed after review? | Yes. The first pass overclaimed that PR #7415 would fix the three targeted TCs. The revised report says PR #7415 removes related `FILE_OOS` utility assertion risk, while the visible failures likely require OOS-aware TC answer/parser updates. |
| Are the non-PR #7415 failures kept out of that bucket? | Yes. The report separates counters, paramdump output, resource fatal, and underdiagnosed `bigPageSize` from the `FILE_OOS` utility bucket. |
| Are unsupported root causes marked as hypotheses? | Yes. `bigPageSize` and `bug_bts_6867` are explicitly not assigned definitive root causes. |
| Are proposed fixes concrete? | Yes. The report names the PR, TCs to rerun, and artifact/logs needed for the remaining buckets. |
