# Code Review: PR #7927 at `290aa50` (CBRD-27089)

- **PR**: [CUBRID/cubrid#7927](https://github.com/CUBRID/cubrid/pull/7927) — `[CBRD-27089] Defer OOS writes until destination heap selection`
- **Issue**: [CBRD-27089](https://jira.cubrid.org/browse/CBRD-27089)
- **Reviewed range**: `git diff origin/feature/oos-merge...HEAD` (three-dot; merge-base `b8f3c4807`), HEAD = `290aa50cb`
- **Commits**: 16 (`b8ce4cba7` … `290aa50cb`); `c38123a51` is a merge of `origin/feature/oos-merge` and its merged-in content was excluded from review
- **Files**: 14 files, +2647/−243 — `src/storage/heap_prepared_row.hpp` (new), `src/storage/heap_file.{c,h}`, `src/storage/heap_oos.hpp`, `src/transaction/locator_sr.{c,h}`, `src/query/partition.c`, `src/query/partition_sr.h`, `src/query/query_executor.c`, `src/loaddb/load_server_loader.{cpp,hpp}`, `unit_tests/oos/sql/CMakeLists.txt`, `unit_tests/oos/sql/test_oos_sql_show.cpp`, `unit_tests/oos/test_oos_server.cpp`
- **Method**: two-axis review (Standards vs Spec), run as two independent agents so that neither axis masks the other. The findings are reported separately and are not reranked across axes.
  - **Spec sources**: PR body; `my-cubrid-jira/issues/CBRD-27089-oos-deferred-write_bffe13b_claude.md`, `CBRD-27089-partition-oos-owner_b871ea3_codex.md`, `CBRD-27089-vacuum-oos-vfid-abort.md`; design doc `cbrd-27089/CBRD-27089-deferred-write_bffe13b_claude.md` (and the `be7c01a` audit).
  - **Standards sources**: repo `CLAUDE.md`/`AGENTS.md`, `src/AGENTS.md`, `CONTRIBUTING.md`, the personal CUBRID policy (`CUBRID.md`, which overrides repo guidance where they conflict), and a fixed Fowler smell baseline (judgement calls only).
- **Reviewer**: Claude Opus 5.5 (AI-assisted, read-only; nothing was built or run)
- **Date**: 2026-09-23

## Executive Summary

The core contract is implemented for SQL INSERT/UPDATE, partition move, raw client rows, the loader, redistribution and duplicate-key probes. Each of these paths works in three steps:

1. Prepare the canonical bytes once in `heap_prepared_row`.
2. Route the row to its destination partition.
3. Finalize the OOS chain and the record in the destination heap.

The owner can be moved but not copied, and it hands off its buffers without copying the payload again. Error paths reset the pending-publication state, and about 34 new tests cover routing, rollback and allocation failure.

Worst item per axis:

- **Standards**: about 500 lines of STL class implementation (`heap_prepared_row`) were placed in the legacy `heap_file.c` rather than in a new `.cpp`.
- **Spec**: the loader's behaviour changed (server-side partition routing with BU locks on every partition, `MULTI_ROW_INSERT` → `SINGLE_ROW_INSERT` for HA and filtered-error loads, a changed abort check). This conflicts with the PR's claim that SQL semantics do not change ("SQL 의미는 바꾸지 않습니다").

Confidence varies: several Spec findings are rated LOW confidence and need verification before they are fixed.

## Standards

### Hard violations (documented rules)

1. **Line width > 120** (CLAUDE.md, 120-column limit). Most of these lines are inside `/* *INDENT-OFF* */`, so GNU indent will not wrap them:
   - `src/query/partition.c:162` (131 columns)
   - `src/storage/heap_file.c:729`, `:12804` (123 columns)
   - `src/storage/heap_file.h:549` (124 columns)
   - `src/loaddb/load_server_loader.cpp:756` (129 columns)
2. **New STL code in a legacy `.c` file** (CUBRID.md: "Prefer new `.cpp` files for new STL code"). About 500 lines of the `heap_prepared_row` class (`std::vector`, `new`/`delete`, `std::atomic`, try/catch) are in `heap_file.c:13878-14380`. The header `heap_prepared_row.hpp` is new, but there is no `.cpp` counterpart.
3. **RAII memory management in engine C code** (CLAUDE.md anti-pattern). `storage::~storage` frees buffers, and stack-owned `heap_prepared_row` objects appear in C functions:
   - `query_executor.c:12166`, `:12390`
   - `locator_sr.c:6814`, `:7431`, `:7728`, `:7831`, `:13200`

   This is a deliberate design choice. Maintainers should accept it explicitly rather than let it pass silently.
4. **Indentation diverges from the surrounding file** (CUBRID.md: preserve existing indentation). New INDENT-OFF regions are space-indented inside tab-indented GNU output:
   - Continuation lines: `partition_sr.h:119`, `locator_sr.h:139`, `locator_sr.c:219`
   - Argument alignment is also not GNU-style: `locator_sr.c:6813-6832`, `:7430-7439`, `:13199-13212`

### Minor

- `heap_file.c:12847` uses `NULL`, while the same function uses `nullptr` a few lines earlier.
- Several small INDENT-OFF blocks in `.c` bodies exist only because they use `nullptr`. `NULL` would keep those bodies formattable by indent (`locator_sr.c:7057`, `:6068`).
- `load_server_loader.cpp:26`: `heap_oos.hpp` breaks the alphabetical include order.
- `heap_prepared_row.hpp` uses `std::size_t` without including `<cstddef>`.

### Smells (judgement calls)

- **Duplicated Code**
  - `er_errid () == NO_ERROR ? ER_FAILED : er_errid ()` appears 12 or more times. Extract a helper such as `er_errid_or_failed ()`.
  - The error-path cleanup `(void) heap_oos_begin_insert_publication` appears about 9 times.
  - The `write_record`/`pending` ternary pair appears twice (`locator_sr.c:6819-6820`, `:7438-7439`).
  - The catalog-bypass condition `catcls_Enable && !OID_IS_ROOTOID && !oid_is_system_class` appears twice (`locator_sr.c:6663`, `:7505`).
  - The phase-readable check is repeated across `record`, `read_values` and `read_value`.
  - The retained-bytes threshold check is repeated (`load_server_loader.cpp:755-757`, `:779`).
- **Mysterious Name**
  - `heap_oos_begin_insert_publication` is also called to discard pending state on error, and the name hides that second role.
  - `m_recdes_collected` (`load_server_loader.hpp:115`) now holds prepared rows, not recdes.
- **Primitive Obsession**
  - `heap_prepared_row_allocation_failed (1/2/3)` takes raw integers, although `enum class heap_prepared_row_allocation` exists.
  - The limit `8 * 1024 * 1024` is an inline magic number (`load_server_loader.cpp:753`).
- **Data Clumps**: `locator_insert_force` now takes 18 parameters, and callers pass runs such as `false, false, false, prepared` (`locator_sr.c:5420`).
- **Divergent Change**: `heap_file.c` now also hosts unit-test failure hooks, including one on the `heap_insert_logical` hot path (`heap_file.c:25578`).

### Consistent with policy

- `std::bad_alloc` is caught at each call site and translated into CUBRID error codes (`heap_file.c:14339`, `locator_sr.c:14191`, loader `push_back`).
- The legacy `// *INDENT-OFF*` markers were normalised to the `/* ... */` form.
- The new header has the Apache license block and an `_HEAP_PREPARED_ROW_HPP_` guard.
- `memory_wrapper.hpp` is still the last include.

## Spec

Severity and confidence are given as severity/confidence.

### (a) Missing or partial

- **Replication apply is not on the prepared path** (MEDIUM/LOW).
  - Spec: "복제 경로가 같은 준비 → 기록 계약을 따릅니다."
  - On the replica, `LC_FLUSH_INSERT_OOS` still writes the chain first under `obj->class_oid` (`locator_sr.c:7208`, via `locator_oos_insert_force` at `:5313`); the row is pruned only afterwards.
  - The code documents this as intentional (`locator_sr.c:6661-6663`). It is safe only if the source always logs the child-partition class OID. It appears to, because finalize runs before the index and replication steps (`locator_sr.c:6068`).
  - A prune-verify re-route on the replica could still split the owners.
- **The catalog-bootstrap bypass is broader than bootstrap** (LOW/LOW). `c136beec7` skips preparation whenever `!catcls_Enable` (`locator_sr.c:6667`). That flag also stays false for user classes when `boot_sr.c:2605` skips catalog compilation.

### (b) Scope creep

- **Loader** (MEDIUM/MEDIUM). This conflicts with "SQL 의미는 바꾸지 않습니다".
  - Partitioned loads are now routed on the server, with BU locks taken on every partition (`load_server_loader.cpp:391-417`).
  - `locator_insert_force` reuses the session's BU locks (`locator_sr.c:5004-5012`).
  - HA and filtered-error loads pass `SINGLE_ROW_INSERT` instead of `MULTI_ROW_INSERT` (`load_server_loader.cpp:842`), which changes how unique statistics are handled.
  - The abort check changed from `er_has_error()` to `m_session.is_failed()` (`:856`).
- **Replica apply atomicity** (MEDIUM/HIGH). OOS items and their heap row now share one grouped top operation. A failed OOS item aborts the whole `repl_force` where it previously continued past the error (`locator_sr.c:7173-7187`, `7270-7274`, `7299-7305`). This changes error-handling behaviour.
- **Smaller items** (LOW):
  - `heap_attrinfo_dbvalue_to_recdes` now rejects `length<=0` for all callers (`heap_file.c:13100`).
  - The public `lob_create_flag` parameter and the `_except_lob` API were removed.
  - A DELETE replication fix at `locator_sr.c:8281`.

### (c) Implemented but likely wrong

- **Latent eager writer to the root heap** (HIGH/LOW).
  - `heap_attrinfo_transform_to_disk` still writes the chain to `attr_info->class_oid` (`heap_file.c:13260`).
  - One caller is MVCC re-evaluation (`locator_sr.c:13918`). That caller would also replace `prepared.record()->data` through `new_recdes` (`locator_sr.c:5814`), and the owner would later free `copyarea->mem`.
  - No path reaches this today, because every prepared UPDATE passes a non-null `old_recdes`. It is a latent hazard.
- **Demotion-policy drift** (LOW/MEDIUM). This contradicts "demotion 정책…바꾸지 않습니다".
  - The prepared path sizes the payload as `fixed_length` including alignment padding (`heap_file.c:12823`).
  - The legacy path sums unpadded `tp_domain_disk_size` values (`heap_file.c:12736`).
  - A row at the boundary can therefore be demoted on one path and kept inline on the other.
- **"Serialize once" holds per write, not per statement** (LOW/HIGH).
  - The ODKU and REPLACE probes serialize the full row, and the real INSERT then serializes it again.
  - ODKU probes still copy LOBs (`query_executor.c:12428`), as they did before this PR.
- **Dead adjustment** (LOW). `prepare_internal` performs `mvcc_extra -= PREV_VERSION_LSA_SIZE` after the capacity is already fixed (`heap_file.c:478`), so the change has no effect.

The Spec agent also flagged `try/catch` in engine code (`heap_file.c:343`, `locator_sr.c:14195`) as against the CLAUDE.md "no exceptions" rule. That finding is dropped here: `CUBRID.md` explicitly permits catching STL exceptions at the call site and translating them.

### What checks out

- The owner is move-only and hands off buffers without copying them again (`heap_file.c:401-406`, `541`).
- Finalize writes the OID, the length and the head identity stamp (`heap_file.c:688-690`).
- Every error path that was traced resets the publication state.
- Duplicate-key probes build keys only from prepared values and write no chain.
- About 34 new tests cover routing, rollback and allocation failures.

## Summary

| Axis | Findings | Worst within axis |
|------|----------|-------------------|
| Standards | 4 hard, 4 minor, ~10 smells | STL class implementation placed in legacy `heap_file.c` |
| Spec | 2 missing/partial, 3 scope-creep, 4 likely-wrong | Loader semantics change (locking, insert mode, abort check) contradicts "no SQL semantics change" |
