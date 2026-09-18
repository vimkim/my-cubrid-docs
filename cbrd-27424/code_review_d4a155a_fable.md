# Code Review: PR #7925 at `d4a155a` (CBRD-27424)

- **PR**: [CUBRID/cubrid#7925](https://github.com/CUBRID/cubrid/pull/7925) — `[CBRD-27424] Support OOS in standalone workspace writes`
- **Issue**: [CBRD-27424](https://jira.cubrid.org/browse/CBRD-27424)
- **Reviewed range**: `git diff origin/feat/oos...HEAD` (three-dot; merge-base `9c768e477`), HEAD = `d4a155a01`
- **Content commits**: `e24b458bf` (engine + regression test), `fe1a918f9` (opt-in CLI regression); `d4a155a01` is a content-free merge of `origin/feat/oos`
- **Files**: `src/transaction/locator_sr.c` (+~130), `src/transaction/locator_sr.h`, `unit_tests/oos/CMakeLists.txt`, `unit_tests/oos/scripts/test_workspace_oos.py` (new, 235 lines); +372/−12
- **Method**: two-axis review (Standards vs Spec) run as two independent agents so neither axis masks the other. Spec source: the CBRD-27424 issue description (`my-cubrid-jira/issues/CBRD-27424-sa-workspace-oos_e24b458_codex.md`) plus the PR body's own commitments. Standards sources: repo `CLAUDE.md`/`AGENTS.md` set, `CONTRIBUTING.md`, GNU-indent rules, plus a fixed Fowler smell baseline (judgement calls only).
- **Reviewer**: Claude Fable 5 (AI-assisted; findings below were traced in code, not taken from the PR's claims)
- **Date**: 2026-09-18

## Executive Summary

The change does what the issue asked, where the issue asked: OOS demotion is correctly inserted into the standalone workspace force path *after* partition pruning, CHN and object references are preserved, buffers are freed on every exit path, and rollback / ignored-load-error cleanup was verified down to the topop structure. No scope creep; server/CS behavior untouched. The regression suite genuinely asserts the orphan-count invariant.

Two things deserve action before or alongside merge:

1. **Undisclosed user-visible failure mode (Spec)** — SA `loaddb` can now reject records that previously loaded as `REC_BIGONE`, with `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` (the CBRD-26937 policy now applies to SA loads). This is the intended TO-BE, but the issue and PR body never state it. Recommend adding it to both.
2. **Function-header doc blocks (Standards)** — `locator_sr.c` documents every parameter in its function headers; the new `from_workspace` parameter and the new function's header don't follow that convention.

## Standards

**Documented-standard conformance (checked, passing)**

- C++ default args (`bool from_workspace = false`) in GNU-indent files are correctly fenced with `/* *INDENT-OFF* */ ... /* *INDENT-ON* */` in both `src/transaction/locator_sr.c` (forward decl) and `src/transaction/locator_sr.h:132-138`.
- C-comment-only rule, GNU braces, space-before-paren, `module_action_object` naming (`locator_demote_workspace_record`), `er_set`/negative-code error model, `ASSERT_ERROR_AND_SET`, `locator_free_copy_area` (no bare `free`) — all conform. No indentation-only hunks. Apache header present in the new Python file. No violations of memory, error-handling, include-order, or anti-pattern rules found.

**Hard-leaning violation (prevailing documented comment pattern)**

- `locator_sr.c` documents every parameter in function headers (e.g. `need_locking(in)` at lines 5444, 6295, 6323). The diff adds `from_workspace` to `locator_insert_force`, `locator_update_force`, `locator_move_record` without updating those doc blocks, and the new `locator_demote_workspace_record` header (~line 4931) omits the file-standard `return:` / `arg(in):` lines. `CLAUDE.md` doesn't spell this format out, so: strong consistency breach, not CI-enforced.

**Soft violation (unit_tests/AGENTS.md)**

- `unit_tests/AGENTS.md` defines unit_tests as Catch2 C++ modules (`test_*.cpp`, `TEST_CASE`, option in master CMakeLists). `scripts/test_workspace_oos.py` is a Python subprocess driver with its `option()` in the module CMakeLists. The oos module already deviates (GTest, shell fixtures), so judgement call — but AGENTS.md should be told about this test kind, or the test relocated to `tests/` (shell integration).

**Baseline smells (all judgement calls)**

- *Primitive Obsession / flag args*: `locator_insert_force` now takes 19 params, 4 trailing bools; call sites read `UPDATE_INPLACE_NONE, NULL, false, false, false, true)` — unreadable at a glance. A flags enum/struct would fix it; long C param lists are codebase idiom, tempering this.
- *Duplicated Code (C)*: the demote-then-swap block plus `locator_free_copy_area (workspace_copyarea)` cleanup is repeated in `locator_insert_force` and `locator_update_force`; mirrors the existing `cache_attr_copyarea` idiom — low priority.
- *Duplicated Code (Python)*: `{p: p.read_bytes() for p in self.lob.rglob("*") if p.is_file()}` appears 3× in `external_lobs`; the regex `r"Live OOS records\s*:\s*(\d+)"` appears 4× — extract helpers.
- *Mysterious Name (mild)*: "demote" already means lock demotion in this file (`xchksum_insert_repl_log_and_demote_table_lock`); here it means OOS out-of-row demotion. Python `check()` is also generic.

## Spec

**Verified as correctly implemented** (traced in code, not just claimed)

- Spec: "실제 파티션과 heap을 고른 뒤 변환한다" — insert demotes after `partition_prune_insert` using `real_class_oid` (`locator_sr.c:5130`); update demotes after the prune/`heap_get_class_oid` refresh (`:6129`), and the move path forwards `from_workspace` to the target `locator_insert_force` (`:6116-6119`). Correct.
- Spec: "OOS 분리를 수행한 레코드는 입력 CHN을 보존한다" — CHN sits at fixed `OR_CHN_OFFSET` regardless of MVCC flags (matches `or_replace_chn`); the transform writes a placeholder 0, and `:4982` overwrites it with `or_chn(recdes)`. Correct.
- Spec: "모든 종료 경로에서 해제" — insert success/failure both fall through `error1:/error2:`; update falls through `error:`; the three early `return`s in update precede allocation. No leak.
- Rollback / ignored-error cleanup — OOS chains are written inside `heap_attrinfo_insert_to_oos` during demotion, which runs inside `xlocator_force`'s outer topop and the per-object topop when `num_ignore_error > 0` (`:7420-7524`); the test's `filtered_load` scenario genuinely asserts the orphan count. Correct.
- Class definitions and pre-demoted records excluded (`OID_IS_ROOTOID` / `OR_RECORD_HAS_OOS` guard, `:4947`); repl path (`xlocator_repl_force`, ~`:7250`) untouched; CMake gate is OFF-default, Python3 3.7 `find_package` only when ON, no other Python dependency. All match the PR claims.

**(a) Missing / partial**

1. Acceptance criterion "일반 SA/CS SQL INSERT와 CS loader 동작을 확인" — the added CTest regression exercises only SA routes (`csql -S`, `loaddb -S`); the CS comparison exists only as manual verification in the report. Minor.
2. Python ≥3.7 is enforced only by CMake; the spec documents direct invocation (`python3 unit_tests/oos/scripts/test_workspace_oos.py`) but the script has no version guard — on 3.6 it dies with an unrelated `TypeError` (`text=` kwarg). Nit.

**(b) Scope creep**

None. Changed files exactly match the spec's 변경 범위. `from_workspace=true` is passed unconditionally in `xlocator_force` even for SERVER_MODE builds, but the demote body is `#if defined (SA_MODE)`, so CS/server behavior is unchanged — consistent with "일반 SQL 실행기, CS loader와 복제 경로의 호출 동작은 유지".

**(c) Implemented, but worth noting**

1. Applying "기존 저장 정책" to SA loads imports the CBRD-26937 OOS+bigone rejection: a record with a huge fixed attribute plus eligible variables that previously loaded as `REC_BIGONE` can now fail with `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`. Intended by TO-BE, but a user-visible SA-loaddb failure mode the issue text never states. Recommend disclosing in the issue and PR body.
2. Update-path demotion transforms with `old_recdes=NULL` (insert-style header, no prev-version-LSA reservation), diverging from the SQL executor's update transform — verified safe (`heap_update_logical` normalizes headers, and pre-change workspace records had the same shape), not a defect.

Out of scope by design: CS-mode workspace writes (`insert_execution_mode=0` without `-S`) still bypass OOS, per the spec's standalone-only 목적.

## Per-Axis Tally

| Axis | Findings | Worst issue |
|---|---|---|
| Standards | 6 (1 hard-leaning, 1 soft, 4 judgement calls) | New/changed function headers in `locator_sr.c` omit the file's per-parameter doc convention |
| Spec | 3 (2 missing/partial, 1 disclosure gap) | SA loaddb can newly fail with `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` on records that previously loaded as `REC_BIGONE`; undisclosed in issue/PR text |

## Recommended Actions

1. Add the `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` behavior change (SA loaddb, formerly-`REC_BIGONE` records) to the JIRA issue and PR body.
2. Update the `locator_sr.c` function-header doc blocks for `from_workspace` and complete the `locator_demote_workspace_record` header.
3. Optionally: note the Python-driver test kind in `unit_tests/AGENTS.md`; extract the two duplicated Python helpers; consider a CS-route regression follow-up.
