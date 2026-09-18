# Code Review: PR #7925 at `39d5e5e` (CBRD-27424)

- **PR**: [CUBRID/cubrid#7925](https://github.com/CUBRID/cubrid/pull/7925) — `[CBRD-27424] Support OOS in standalone workspace writes`
- **Issue**: [CBRD-27424](https://jira.cubrid.org/browse/CBRD-27424)
- **Reviewed range**: `git diff origin/feat/oos...HEAD` (three-dot; merge-base `38093ea85`), HEAD = `39d5e5e5e`
- **Content commits**: `e24b458bf` (engine + regression test), `fe1a918f9` (opt-in CLI regression), `736353fff` (first-review fixes: `LOCATOR_FORCE_FLAG` bitmask, helper renamed `locator_oos_demote_workspace_record` and owning the recdes swap, doc headers). `d4a155a01` and `39d5e5e5e` are merges of `origin/feat/oos`; both verified content-free (`git diff-tree --cc` prints no combined hunks).
- **Base movement since the first review**: `9c768e477` → `38093ea85`, which brings PR #7695 (CBRD-26950 identity stamps) into the base. In `locator_sr.c` the base only changed the replication stub fix-up path (`thread_p->oos_oids[i]` gained `.oid`/`.identity_stamp`); the new helper touches none of it and `locator_allocate_copy_area_by_attr_info` keeps its signature.
- **Files**: `src/loaddb/load_server_loader.cpp` (+3/−2), `src/transaction/locator_sr.c` (+~140/−~20), `src/transaction/locator_sr.h` (+16/−2), `unit_tests/oos/CMakeLists.txt` (+13), `unit_tests/oos/scripts/test_workspace_oos.py` (new, 235 lines); +406/−24 over 5 files
- **Method**: two-axis review (Standards vs Spec) run as two independent agents so neither axis masks the other. Spec sources: the current CBRD-27424 issue description (`my-cubrid-jira/issues/CBRD-27424-sa-workspace-oos_736353f_fable.md`), the PR body's commitments, and the OOS normative specification (`cubrid-oos-context/OOS-CONTEXT.md`, 2026-09-09). Standards sources: repo `CLAUDE.md`/`AGENTS.md` set, `src/AGENTS.md`, `unit_tests/AGENTS.md`, `CONTRIBUTING.md`, GNU-indent rules, `.github/workflows/codestyle.sh`, plus a fixed Fowler smell baseline (judgement calls only).
- **Prior review**: [code_review_d4a155a_fable.md](https://github.com/vimkim/my-cubrid-docs/blob/861ad4fc647391b561ee156f9ae07d1104d5582b/cbrd-27424/code_review_d4a155a_fable.md). Its accepted findings were fixed in `736353fff`; items the author deliberately declined are listed at the end and were not re-raised.
- **Reviewer**: Claude Fable 5.1 (AI-assisted; every finding below was traced in code at HEAD, not taken from the PR's claims; the aggregator independently spot-checked the load-bearing claims of both axes)
- **Date**: 2026-09-18

## Executive Summary

The PR at `39d5e5e5e` implements the issue as specified and nothing else. Every commitment in the issue and PR body traces to code: the workspace flag is set only on the standalone routes and forwarded through partition movement, demotion runs after partition determination, CHN is restored (load-bearing, since the transformer would otherwise write 0 or `inst_chn+1`), the temporary copy area is released on every exit path, OOS chains are written inside the force top operation (including the per-object one used for ignored load errors), and the CBRD-26937 rejection fires before any chain is written. The first review's accepted findings are all resolved, and the `LOCATOR_FORCE_FLAG` refactor is bit-for-bit semantics-preserving at all 10 `locator_insert_force` call sites.

No hard standards violations and no spec defects were found. What remains is optional polish:

1. **Untested disclosed behaviour change (Spec, coverage)** — the PR and issue now disclose that formerly-`REC_BIGONE` records can be rejected with `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` (-1375) on `loaddb -S`, but `test_workspace_oos.py` has no scenario exercising it. The code path is correct.
2. **Small file-convention items (Standards, judgement calls)** — the `LOCATOR_FORCE_FLAG` typedef name is never used as a type, the new static lacks the forward declaration every other static in the file has, and the CMake `option` spelling differs from the master list.

Nothing here blocks merge from the review's standpoint.

## Standards

*Report of the Standards agent, lightly cleaned. Style tools were run on copies; the worktree was left unchanged.*

### Hard violations (documented / CI-enforced)

**None found.**

### Judgement calls

1. **`LOCATOR_FORCE_FLAG` is a dead type name.** `src/transaction/locator_sr.h:142` names the enum, but no declaration ever uses it. `force_flags` is plain `int` at `locator_sr.h:149`, `locator_sr.c:5033`, and `load_server_loader.cpp:748`. Only the doc comment at `locator_sr.c:5023` mentions it. Possible **Primitive Obsession**: a bitmask genuinely wants `int` in C, so this is soft. Either type the parameter or drop the typedef name.
2. **Enum member prefix does not match the typedef.** Members are `LC_FORCE_FLAG_*` (`locator_sr.h:136-141`) under a `LOCATOR_FORCE_FLAG` typedef. The two enums in `locator.h` keep prefixes aligned (`LC_COPYAREA_OPERATION`, `LC_FETCH_VERSION_TYPE`), while `locator_sr.c:85` `LOCATOR_INDEX_ACTION_FLAG` uses unprefixed members. No documented rule covers it, so cosmetic only.
3. **New static lacks a forward declaration.** `locator_oos_demote_workspace_record` is defined at `src/transaction/locator_sr.c:4946` with no prototype in the block at lines 147-242. Every other static in the file has one, including the sibling OOS helper `locator_fixup_oos_oids_in_recdes` at `locator_sr.c:242`. File-local convention, not an AGENTS.md rule.
4. **CMake option placement and spacing.** `unit_tests/AGENTS.md` ("Adding a New Test Module") says options go in the master list; `option(UNIT_TEST_OOS_WORKSPACE_CLI ...)` sits at `unit_tests/oos/CMakeLists.txt:198`. The 13 options at `unit_tests/CMakeLists.txt:33-45` also all write `option (` with a space. The documented rule targets new modules, not a new test inside one, so this is soft.
5. **Possible Duplicated Code.** The BU-lock plus FK flag composition appears at `load_server_loader.cpp:748` and `locator_sr.c:14156-14157`. Two sites, three lines. Extraction would likely cost more than it saves.

### Verified conforming

- **codestyle.sh fixed point**: `locator_sr.c`, `locator_sr.h`, `load_server_loader.cpp` all unchanged by GNU indent 2.2.11 and astyle.
- **INDENT fences**: both C++ default-argument prototypes wrapped exactly, at `locator_sr.h:144-150` and `locator_sr.c:150-157`.
- **Comments**: no `//` in the `.c`/`.h` hunks; `//` only in the `.cpp`.
- Line width under 120, no bare `free`, no `#pragma once`, no include changes, `_LOCATOR_SR_H_` guard intact, `module_action_object` naming, Apache header on the new Python file.
- Copy areas freed on every exit path, including fall-through success, at `locator_sr.c:5370` and `locator_sr.c:6278`.

### Prior-review fixes

All four resolved: bitmask flags, `locator_oos_demote_workspace_record` owning the recdes swap, and the four doc-block parameters at `locator_sr.c:5022-5023`, `5458`, `5558-5559`. Author-declined items (Python polish, CS-route CTest, residual `from_workspace` bools, the twice-used ternary, the AGENTS.md test-kind note) confirmed still open as known.

### Aggregator verification note

Claims 1-3 were re-checked in source and hold. One nuance on claim 1: `.c` files in this repo compile as C++17, where `force_flags | LC_FORCE_FLAG_BULK_LOGGING` yields `int` and would need a cast at every OR site to pass to an enum-typed parameter. Keeping the parameter `int` is therefore the pragmatic choice; the realistic fix is to drop the typedef name (keep an anonymous enum) or keep it purely as documentation, not to retype the parameter.

## Spec

*Report of the Spec agent, lightly cleaned. All line numbers are at HEAD `39d5e5e5e`.*

### (a) Missing / partial

- **Partial (test coverage only):** the disclosed behaviour change ("`ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` (-1375)로 거부될 수 있다" — workspace writes can now be rejected) has no scenario in `test_workspace_oos.py`. The code path is correct (see (d)), but the regression suite never exercises a bigone-after-demotion record through `loaddb -S`.
- Acceptance criterion 6 ("일반 SA/CS SQL INSERT와 CS loader 동작을 확인" — CS routes) is manual-only. Known/declined.
- Everything else in the issue and PR body is code-traced as implemented.

### (b) Scope creep

None found. `LOCATOR_FORCE_FLAG` refactor: all 10 `locator_insert_force` callers map bit-for-bit to their old `(has_BU_lock, dont_check_fk, use_bulk_logging)` bools (`load_server_loader.cpp:748,785`; `locator_sr.c:5489,5506,7242,7452,7826,13209,14181,14212,14267`); `xlocator_repl_force`, `locator_attribute_info_force`, `redistribute_partition_data`, `locator_multi_insert_force` and the CS loader do not set `FROM_WORKSPACE`. The two non-workspace `locator_update_force` callers (`locator_sr.c:7258`, `7843`) keep the `from_workspace=false` default.

Scope boundary worth knowing: the helper body is `#if defined (SA_MODE)` (`locator_sr.c:4949`), so CS-mode workspace writes (`csql` without `-S` with `insert_execution_mode=0`) remain inline — consistent with the issue's "standalone" scope, but the flag comment at `locator_sr.h:140` ("OOS demotion has not been applied yet and must happen at force time") reads as unconditional.

### (c) Implemented but looks wrong

None found. Checked specifically: CHN, header shape (`old_recdes=NULL`, still safe: `heap_update_logical` normalizes), partition move, eager-cleanup gating, and publication of `thread_p->oos_oids` when `has_index` is false (stale entries are harmless: `log_does_allow_replication` is `false` in SA, `log_comm.c:274`).

### (d) Verified correct

- **Call-path discrimination**: `xlocator_force` insert/update `locator_sr.c:7452-7454,7468-7470`; multi-update `6868-6870`; move forwards the flag `5489-5491,5506-5508`.
- **Exclusions**: root class and already-demoted records `locator_sr.c:4955`; `n_variable == 0` `4966`; class objects never reach the instance branch (`5565` root branch; insert asserts non-root `5058`).
- **Partition first**: insert demotes after `partition_prune_insert` with `real_class_oid` `5146`; update demotes after the `heap_get_class_oid` refresh `6143`; the move case `return`s at `6135` before the demote block, so no double demotion; the target insert demotes against the partition.
- **CHN**: the transformer writes CHN 0 for MVCC classes (`heap_file.c:13446`) or `inst_chn+1` for non-MVCC (`13417,13467`); the helper restores `or_chn(recdes)` at fixed `OR_CHN_OFFSET` (`object_representation.h:519`, same offset `or_replace_chn` uses) `locator_sr.c:4990`. Load-bearing, not cosmetic.
- **Buffer release**: insert `error1→error2` `5370-5373`; update `error:` `6278-6281`; all `return`s in update (`5850,5893,6135`) precede allocation; `heap_attrinfo_end` on every helper path `4968,4994`.
- **Transaction scope**: outer topop `7411`; per-object topop when `num_ignore_error>0` `7440-7449`, aborted on filtered error `7522`; multi-update runs before `end_topop` `7554-7560`. Rejection precedes `heap_attrinfo_insert_to_oos` (`heap_file.c:13902-13912`), so no orphan chains on -1375.
- **SA eager cleanup**: `HEAP_UPDATE_IS_MVCC_OP` is `false` outside SERVER_MODE (`heap_file.c:171-172`), so `heap_update_home` calls `heap_oos_delete_unreferenced` (`24829-24834`); a new inline record deletes all old chains (`heap_oos.cpp` empty `new_oos_refs` path); stamps come from the shared `oos_insert` writer.
- **LOB**: `LOB_FLAG_EXCLUDE_LOB` only skips `db_elo_copy_with_prefix` (`heap_file.c:13133,13664`); the locator string still demotes per ADR-0002.
- **No-logging**: nothing in the diff reads LSAs; inserts only.
- **Test map**: acceptance criteria 1-5 each have a scenario (`basic_loader`, `workspace_sql`, `references`, `partitions`, `partition_move`, `rollback`, `update_cleanup`, `failed_load`, `filtered_load`, `storage_policy`, `external_lobs`, `no_logging`). CMake gate OFF by default; Python only inside `if(UNIT_TEST_OOS_WORKSPACE_CLI)` (`unit_tests/oos/CMakeLists.txt:198-206`); no other Python reference.
- **Merged base**: only the `thread_p->oos_oids` element type and the replication stub fix-up changed in `locator_sr.c`; the helper uses none of it; `locator_allocate_copy_area_by_attr_info` signature unchanged (`7600`).

### Aggregator verification note

Re-checked in source and confirmed: the `return error_code;` after `locator_move_record` (`locator_sr.c:6137`) precedes the `if (from_workspace)` demote block; `HEAP_UPDATE_IS_MVCC_OP` is defined as `(false)` in the non-`SERVER_MODE` branch (`heap_file.c:171-172`) and `heap_update_home` gates `heap_oos_delete_unreferenced` on `!is_mvcc_op && ... heap_recdes_contains_oos (&context->home_recdes)`; `log_does_allow_replication` returns `false` under `SA_MODE` (`log_comm.c:274`); the `LC_FORCE_FLAG_FROM_WORKSPACE` comment at `locator_sr.h:140-141` does not mention the SA-only effect.

## Per-Axis Tally

| Axis | Findings | Worst issue |
|---|---|---|
| Standards | 5 (0 hard, 5 judgement calls) | `LOCATOR_FORCE_FLAG` typedef name is never used as a type; the parameter stays `int` (pragmatic under C++ compilation, but the name and the `LC_`/`LOCATOR_` prefix split are then noise) |
| Spec | 2 (0 missing, 0 wrong, 0 creep; 1 coverage gap, 1 doc nuance) | The disclosed `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` rejection on `loaddb -S` has no regression scenario |

## Recommended Actions

All optional; none blocks merge from the review's standpoint. CI on head `39d5e5e5e` still needs a fresh trigger.

1. **Add a rejection scenario** to `test_workspace_oos.py`: load, via `loaddb -S`, a record with a large fixed-length `BIT(n)` plus an OOS-eligible `BIT VARYING` that stays above the bigone threshold after demotion; assert the -1375 error and that `Live OOS records` for the table is unchanged (no orphan). This is exactly OOS spec test category 9.6 applied to the standalone route.
2. **Forward-declare** `locator_oos_demote_workspace_record` in the static prototype block of `locator_sr.c`, matching the file convention.
3. **Tidy the flag type**: either drop the `LOCATOR_FORCE_FLAG` typedef name (anonymous enum) or keep it as documentation only, and note in the `LC_FORCE_FLAG_FROM_WORKSPACE` comment that demotion is applied in `SA_MODE` builds only.
4. Cosmetic: `option (` spelling to match `unit_tests/CMakeLists.txt`.

## Known / Declined (not re-raised)

From the first review, deliberately declined by the author and confirmed still open as known: Python test polish (version guard, duplicated helpers in `test_workspace_oos.py`); CS-route CTest regression (manual verification only); residual `bool from_workspace` on the static `locator_update_force`/`locator_move_record`; the twice-used ternary in `locator_move_record`; describing the Python-driver test kind in `unit_tests/AGENTS.md`.
