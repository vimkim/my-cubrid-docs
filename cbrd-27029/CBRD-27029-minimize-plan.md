# CBRD-27029 — PR #7416 Diff Minimization Plan

> **EXECUTED 2026-07-07** — squashed commit `6496b4ba2`, all flips reverted (zero behavior
> change), scripted mapping audit passed, `just build-test` 23/23, codestyle hook green.
> Not pushed — force-push to `vk` + CI rerun is Daehyun's (W00). See Outcome at bottom.

**Goal**: reduce PR #7416 (`cbrd-27029-oos-expand-raw-records` → `feat/oos`) to only what is
necessary, per Daehyun 2026-07-07: keep the WITH/WITHOUT **policy explicitness** (signature
changes that turn silent merges into compile breaks), revert **behavior changes** that are hard
to review. Then Daehyun reruns `test_shell` CI.

**Why now**: the ~318 shell failures that motivated the aggressive reclassification were a CI
environment bug (unittestdb conf not restored after setup), fixed by feat/oos head `5b5ff588f`
(#7427). Post-hotfix baseline fails only 9 shell TCs — none attributable to expand policy.
So no behavior flip in this PR is *proven necessary* by CI. Sources:
`~/temp/todays-schedule/ci-report-2026-07-07.md`, `oos-ci-green/PLAN.md`.

---

## Minimization rule

Every call site maps 1:1 to its base (`origin/feat/oos`, merge-base `891c2c802`) behavior:

| Base call | Minimized call |
|-----------|----------------|
| `heap_next / heap_prev / heap_next_sampling (...)` | same + `HEAP_WITHOUT_OOS_EXPAND` |
| `heap_next_expand_oos (...)` | `heap_next (..., HEAP_WITH_OOS_EXPAND)` |
| `heap_get_visible_version (...)` | same + `HEAP_WITHOUT_OOS_EXPAND` |
| `heap_get_visible_version_expand_oos (...)` | `heap_get_visible_version (..., HEAP_WITH_OOS_EXPAND)` |
| `heap_scan_get_visible_version (...)` | same + `HEAP_WITHOUT_OOS_EXPAND` |
| `heap_init_get_context (...)` (no expand set after) | same + `HEAP_WITHOUT_OOS_EXPAND` |
| locator getter 3종 (base: never expand) | same + `HEAP_WITHOUT_OOS_EXPAND` at every caller |

Result: the PR becomes **pure signature threading with zero behavior change**. A reviewer only
has to check the mapping above per hunk — no data-flow reasoning needed.

## What stays (already in branch, KEEP)

1. `HEAP_OOS_EXPAND_POLICY` enum + `HEAP_IS_VALID_OOS_EXPAND_POLICY` in `heap_file.h`;
   `HEAP_GET_CONTEXT.expand_oos: bool` → `oos_expand_policy` enum.
2. Policy parameter on: `heap_next`, `heap_prev`, `heap_next_sampling`,
   `heap_get_visible_version`, `heap_scan_get_visible_version`, `heap_init_get_context`,
   `locator_lock_and_get_object`, `locator_lock_and_get_object_with_evaluation`,
   `locator_get_object`. (→ future develop merges break at compile time.)
3. Wrapper removal: `heap_next_expand_oos`, `heap_get_visible_version_expand_oos`
   (their call sites become `..., HEAP_WITH_OOS_EXPAND` — same behavior).
4. Enforcement funnel: `assert` in `heap_init_get_context`, invalid-policy
   `er_set + S_ERROR` in `heap_record_replace_oos_oids`.
5. The ~30 call sites whose policy already equals base behavior (e.g. `scan_manager.c`,
   `query_executor.c`, `btree_load.c`, `catalog_class.c` heap_next sites,
   `xlocator_fetch_all`, `xlocator_lock_and_fetch_all`, `redistribute_partition_data`, …).

## Behavior flips at HEAD `846b5c7cf` → REVERT to base-equivalent

### A. Base expanded, HEAD doesn't (WITH → restore `HEAP_WITH_OOS_EXPAND`) — 17 sites

| # | Site | Note |
|---|------|------|
| 1 | `compactdb.c` `process_value` | recdes=NULL; expansion is a no-op, but map mechanically |
| 2 | `compactdb_sr.c` `process_value` | recdes=NULL; same |
| 3 | `load_server_loader.cpp` re-fetch after `heap_next` | |
| 4–6 | `serial.c` ×3 (`xserial_get_current_value_internal`, `serial_update_cur_val_of_serial`, `xserial_get_next_value_internal`) | base conservative-WITH |
| 7 | `sp_code.cpp` `sp_get_code_attr` | |
| 8–10 | `heap_file.c` scanrange: `to_following` (start_oid path), `to_prior` (last_oid path), `scanrange_next` (first-object path) | drop the now-wrong "scanrange = WITHOUT" comment block |
| 11 | `locator_sr.c` `locator_all_reference_lockset` | |
| 12–13 | `locator_sr.c` `locator_update_force` ×2 | |
| 14 | `locator_sr.c` `locator_delete_lob_force` | |
| 15 | `locator_sr.c` `locator_repl_prepare_force` | |
| 16 | `locator_sr.c` `locator_mvcc_reeval_scan_filters` | |
| 17 | `lock_manager.c` `lock_dump_resource` | header-only read, but base said WITH |

### B. Base didn't expand, HEAD does (revert to `HEAP_WITHOUT_OOS_EXPAND`) — 9 sites

| # | Site | Note |
|---|------|------|
| 1–2 | `heap_first` / `heap_last` internal policy | back to base behavior (no expand); keep base signature, one-line comment |
| 3 | `heap_file.c` scanrange `to_following`/`to_prior` first/last-object paths | **restore the `heap_first`/`heap_last` calls** — delete the hand-inlined `OID_SET_NULL + heap_next/heap_prev` blocks (the "hard to review" churn) |
| 4–5 | `system_catalog.c` `catalog_check_consistency`, `catalog_dump` | class records — no OOS in practice |
| 6 | `locator_sr.c` `locator_initialize`, `locator_check_class_names` | class records |
| 7 | `locator_sr.c` `locator_lock_and_return_object` → `locator_get_object` | ⚠ see Open Question 1 |
| 8 | `locator_sr.c` `locator_delete_force_internal` (with_evaluation) | |
| 9 | `locator_sr.c` `locator_check_all_entries_of_all_btrees`; `heap_file.c` `heap_get_class_record` | class records |

### C. Extra hardening noise → trim

- Drop the duplicated `if (!HEAP_IS_VALID_OOS_EXPAND_POLICY) return S_ERROR;` blocks in
  `heap_next_internal` and `heap_scan_get_visible_version_impl` — the funnel
  (`heap_init_get_context` assert + `heap_record_replace_oos_oids` er_set) already covers them.
- Keep the enum TODO comment pointing at CBRD-26847 (it replaces the base TODO that lived on
  the deleted `heap_get_visible_version_expand_oos`).

## Commit strategy

Squash the 6 commits into **one**: `[CBRD-27029] Make heap fetch OOS expand policy explicit`
— message states "no behavior change: every call site preserves the base expand behavior".
Requires force-push to `vk` (pushed head is `c33d0ff8`; `846b5c7cf` is local-only).
Per W00 in oos-ci-green/PLAN.md, push + CI trigger are Daehyun's — branch will be left ready.

## Verification

1. `git diff --check` clean; diff vs `origin/feat/oos` shrinks (~437 changed lines → est. ~300,
   all mechanical).
2. Mapping audit: script-grep every hunk — each `WITH` site must correspond to a base
   `*_expand_oos` call; each `WITHOUT` site to a base plain call. Zero exceptions.
3. `just build-test` (debug_gcc build + unit tests).
4. No `*_expand_oos` identifiers left; no `HEAP_OOS_EXPAND_POLICY_INVALID` passed anywhere.
5. Update `~/gh/my-cubrid-jira/issues/CBRD-27029-oos-expand-raw-records.md` (and PR #7416
   description) to the reduced scope: API contract only, reclassification deferred to
   CBRD-26847.

## Decisions (Daehyun, 2026-07-07)

1. **`locator_lock_and_return_object` (LC_COPYAREA single-object fetch → client)**: revert to
   base (WITHOUT) in this PR; **marked ANALYSIS NEEDED** as a follow-up. Base is inconsistent —
   `xlocator_fetch_all` expands, the single-object fetch path does not. If a CS-mode client
   receives an instance record with inline OOS OID slots it cannot resolve them (oos_read is
   server-side), so this is a plausible correctness gap — but nothing in the 9-TC post-hotfix
   baseline exercises it. Needs its own ticket with a repro test (CS-mode single-object fetch
   of an OOS-bearing row, e.g. object fetch via workspace / unloaddb non-fetch-all path).
2. **History**: squash to 1 commit, force-push to `vk` (push/CI by Daehyun per W00).
