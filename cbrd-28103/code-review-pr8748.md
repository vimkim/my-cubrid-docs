# Code Review: `CUBRID/cubrid#8748` (`CBRD-28103`)

- **PR:** [CUBRID/cubrid#8748](https://github.com/CUBRID/cubrid/pull/8748) — `[CBRD-28103] Keep a reference whose object compactdb fails to read, and count the object as failed` (`YeunjunLee`, 3 files, `+59/-13`).
- **Reviewed snapshot:**
  - `base` (`develop`): `d8176c1d37c4735964899c273b74045760925eb6`
  - `merge_base`: `d8176c1d37c4735964899c273b74045760925eb6`
  - `head`: `8815efd22b55487310d691c92e16a7a57be85869`
- **Comparison and patch:** `git diff d8176c1d37c4735964899c273b74045760925eb6..8815efd22b55487310d691c92e16a7a57be85869` (patch SHA-256 `95e2705b4bd523091ddff15a70a35cd98e3672cc99c51a0a5ea687636aa4f803`).
- **JIRA:** [CBRD-28103](https://jira.cubrid.org/browse/CBRD-28103)
- **Review date:** 2026-11-27 (Asia/Seoul). Delta review of `8815efd22b55487310d691c92e16a7a57be85869` following initial snapshot `a3bf590f12`.

## Goal and Verdict

The review verified whether SA (`compactdb.c`) and CS (`compactdb_sr.c`) `compactdb` behave identically and safely across `S_SUCCESS`, missing-object (`S_DOESNT_EXIST`, `S_SNAPSHOT_NOT_SATISFIED`), and read-error (`S_ERROR`) paths, including set attributes, error-state cleanup, single- and multi-batch representation deletion (`-d`, including `big_objects` and failed objects), concurrency/MVCC, and HA/recovery boundaries.

- **Verdict:** `changes-required`
- **Follow-up review required:** `yes` — fix `F1` (`src/storage/compactdb_sr.c` missing `er_clear()`) and re-verify CS single-batch `S_ERROR` isolation before merge.

All SA-side changes in `src/executables/compactdb.c` passed runtime and `gdb` fault-injection checks, and commit `8815efd22b` cleanly fixed the CS multi-batch `-d` old-representation deletion bug (`COMPACTDB_REPR_KEEP` + `big_objects[i] == 0`). However, in CS `src/storage/compactdb_sr.c`, PR #8748 still counts `object_processed < 0` as failed (`:452-455`) without clearing `er_errid()`. Runtime fault injection on `8815efd22b` confirmed that a single `S_ERROR` (`ER_IO_READ = -13`) leaves `er_errid() == -13` set and cascades into subsequent objects' `pgbuf_ordered_fix()` (`LK_FORCE_ZERO_WAIT`) calls, failing remaining relocating objects in that batch.

## Confirmed Findings

### `F1` (`P2`): CS `compactdb_sr.c` omits `er_clear()`, causing one `S_ERROR` to cascade-fail subsequent objects in the same batch

- **Location:**
  - [`src/storage/compactdb_sr.c:452-455`](https://github.com/CUBRID/cubrid/blob/8815efd22b55487310d691c92e16a7a57be85869/src/storage/compactdb_sr.c#L452-L455) (`process_class`: increments `(*failed_objects)++` on `object_processed < 0` without calling `er_clear ()`)
  - [`src/storage/compactdb_sr.c:114-124`](https://github.com/CUBRID/cubrid/blob/8815efd22b55487310d691c92e16a7a57be85869/src/storage/compactdb_sr.c#L114-L124) (`process_value`: returns `ASSERT_ERROR_AND_SET` on `S_ERROR`, leaves error set on `S_DOESNT_EXIST`/`S_SNAPSHOT_NOT_SATISFIED`)
  - Cascade site: [`src/storage/page_buffer.c:13287-13314`](https://github.com/CUBRID/cubrid/blob/8815efd22b55487310d691c92e16a7a57be85869/src/storage/page_buffer.c#L13287-L13314) (`pgbuf_ordered_fix`)
- **Trigger & Mechanism:**
  1. Object `k` in a CS batch encounters `scan_code == S_ERROR` (e.g., `ER_IO_READ = -13`) in `process_value()`. `process_object()` returns `-13`, `process_class()` increments `*failed_objects`, and `er_errid()` stays `-13`.
  2. Subsequent object `k+1` in the same batch needs an update (e.g., schema representation upgrade after `ALTER TABLE ADD COLUMN`) whose record grows and calls `heap_update_home()` → `heap_insert_newhome()` → `heap_find_bestpage()` → `pgbuf_ordered_fix()` under `LK_FORCE_ZERO_WAIT`.
  3. At `page_buffer.c:13287`, `pgbuf_ordered_fix()` checks `er_status = er_errid_if_has_error ()` when conditional latching skips a page; finding stale `-13`, it skips `er_status = ER_LK_PAGE_TIMEOUT` and returns `-13` up through `locator_attribute_info_force()` (`compactdb_sr.c:263`). `process_object()` returns `-1` (`:275`), failing healthy objects `k+1..N` in that batch.
- **Attribution:** Pre-existing missing `er_clear()` on `e23905d89a` / `d8176c1d37` (where `< 0` errors were also uncounted), directly in the hunk PR #8748 modified at `compactdb_sr.c:452` while adding `er_clear()` only to SA `compactdb.c:448, 597`.
- **Verification Evidence (Level 5, `debug_gcc` + `gdb`):**
  - **On `8815efd22b` (`db3d_f1`):** 200-row altered table (`CHAR(2000)`, `ALTER TABLE ADD COLUMN tag VARCHAR(1000) DEFAULT 800*'T'`), running `cubrid compactdb -C -d -p 1 -v db3d_f1 dba.f1_t` with **one** `ER_IO_READ` / `S_ERROR` injected on `compactdb_sr.c:114` (`$hit == 1`, detached immediately after injection) produced **`Total objects: 200, Failed objects: 3, Modified objects: 197`** (2 subsequent relocating objects in Batch 1 failed from the single injected error). Unlike earlier `a3bf590f12`, old representations were preserved in catalog (`COMPACTDB_REPR_KEEP`).
  - **On `a3bf590f12` (same unmodified `compactdb_sr.c:452-455` hunk):**
    - On a 200-row altered table (`db3b4`, `char(2000)`, `add column tag varchar(16) default 'v1'`), 1 injected `ER_IO_READ`/`S_ERROR` produced `locator_attribute_info_force()` failures (`err_ret = -13`, `er_errid = -13`) on **42** subsequent objects in that batch (`Total objects: 200, Failed objects: 43, Modified objects: 157`). Re-running without injection compacted all 43 remaining rows cleanly (`Failed objects: 0, Modified objects: 43`).
    - On a 500-row 5-batch test (`db3d`), 1 injected `S_ERROR` in Batch 1 caused `Failed objects: 12` in Batch 1.
  - By contrast, `S_DOESNT_EXIST` (`ER_HEAP_UNKNOWN_OBJECT`) without injection (`200` rows, 1 deleted reference) completed with `Failed objects: 0, Modified objects: 200` because warning severity does not trigger `er_errid_if_has_error()`, though clearing it at `compactdb_sr.c:120` as well avoids intra-RPC stale-error hazards.
- **Required Action:** Call `er_clear ();` in `src/storage/compactdb_sr.c` when `object_processed < 0` (`:455`) and when clearing a missing-object reference (`:120`).

### `F2` (`P3`, non-blocking): SA `compactdb` writes `"FAILURE: No error message available."` to `cubrid_utility.log` after `er_clear()`

- **Location:** [`src/executables/compactdb.c:153-157`](https://github.com/CUBRID/cubrid/blob/8815efd22b55487310d691c92e16a7a57be85869/src/executables/compactdb.c#L153-L157), interacting with [`compactdb.c:448`](https://github.com/CUBRID/cubrid/blob/8815efd22b55487310d691c92e16a7a57be85869/src/executables/compactdb.c#L448).
- **Evidence (Level 5):** After `er_clear()` clears `crt_error.msg_area` on failed objects, `compactdb_start()` returns `status = 1` and `compactdb()` calls `util_log_write_errstr ("%s\n", db_error_string (3))`, logging `FAILURE: No error message available.` in `cubrid_utility.log`.
- **Suggested Fix:** Guard `compactdb.c:156` with `if (er_errid () != NO_ERROR)` (or log a summary string). Non-blocking.

## Resolved Pre-Existing Bugs in `8815efd22b`

- **`PRE1` / `PRE3` (`P1`) — RESOLVED in `8815efd22b`:** Commit `8815efd22b` adds [`COMPACTDB_REPR_KEEP (-3)`](https://github.com/CUBRID/cubrid/blob/8815efd22b55487310d691c92e16a7a57be85869/src/base/server_interface.h#L63-L64) and checks `big_objects[i] == 0` alongside `failed_objects[i] == 0`, preserving `initial_last_repr_id[i] = COMPACTDB_REPR_KEEP` across batches whenever an earlier batch ends with `!OID_ISNULL(last_processed_oid)` and `failed_objects[i] > 0 || big_objects[i] > 0` ([`compactdb_sr.c:630-666`](https://github.com/CUBRID/cubrid/blob/8815efd22b55487310d691c92e16a7a57be85869/src/storage/compactdb_sr.c#L630-L666)).
  - **Level 5 Verification (`db3d_pre` on `8815efd22b`):** Created `multi_in` (`enable_string_compression=no`, 1 big 30,000-byte row + 120 1,500-byte rows, `ALTER TABLE ADD COLUMN c INT DEFAULT 7`), ran `cubrid compactdb -C -v -d -p 1 db3d_pre dba.multi_in` (`exit 0`, `Failed objects: 0, Modified objects: 120, Big objects: 1, Old class representations preserved in catalog.`), restarted `db3d_pre` cold-cache, queried `SELECT id, tag, LENGTH(bigcol), c FROM multi_in WHERE id = 1` → `1, 'v1', 30000, 7`, and passed `cubrid checkdb -S db3d_pre` (`exit 0`).
  - **Level 5 Verification (`db3d_f1` on `8815efd22b`):** Batch 1 `S_ERROR` during multi-batch `-C -d -p 1 -v` also preserved old representations in catalog (`Old class representations preserved in catalog.`), resolving the `a3bf590f12` failure where Batch 5 dropped representations and caused `#23586`.

## Remaining Pre-Existing Defects & Scope Limitations

- **`PRE2` (`P1`, source-only Level 3): SA Phase 2 (`heap_reclaim_addresses`) runs when `failed_objects != 0`.**
  - `compactdb.c:257-305` retains a `TODO` (`:262-267`) and proceeds into Phase 2 unconditionally. If an object has both a deleted reference and an `S_ERROR` reference, skipping `disk_update_instance()` leaves the deleted reference on disk while Phase 2 reclaims deleted slots/pages.
- **`PRE4` (`P2`, Level 3):** `lock_unlock_object(..., true)` at `compactdb_sr.c:450` decrements double-acquired `X_LOCK` (`2 -> 1`) without releasing it until batch commit.
- **`PRE5` (`P2`, Level 3):** SA `compactdb.c:451-454` (`desc_disk_to_obj` failure) omits `er_clear()`, and `compactdb.c:535` ignores `disk_update_instance()` failure (noted in PR description).
- **`PRE6` (`P2`, Level 3):** CS `process_object()` decodes `attr_info` from snapshot `fetch_area` rather than `copy_recdes` under `TRAN_READ_COMMITTED`.

## Verified Safe Behavior & Checks Run

- **Build & static analysis (`debug_gcc` at `8815efd22b`):** `just build-and-install` passed (`exit 0`). `cubrid-static-check d8176c1d37 8815efd22b` passed (`exit 0`, **0** new cppcheck, clang-tidy, PMD CPD, or lizard issues across all 3 changed files). Style note: comment at `src/executables/compactdb.c:446` expands to 122 columns with 8-space tabs (over `-lc120`).
- **SA deleted-object reference regression (Level 5, `a3bf590f12`, unchanged in `compactdb.c` on `8815efd22b`):** Single class (30 rows, 4 deleted refs), multi-class (2 classes × 10 rows, 2 deleted refs each), and set attribute (10 rows, 2 deleted refs) all passed in one `cubrid compactdb -S -v` run (`exit 0`, sums `402/42/42`, `cubrid checkdb -S` `exit 0`).
- **SA `S_ERROR` fault injection (`gdb`, Level 5, `a3bf590f12`, unchanged in `compactdb.c` on `8815efd22b`):**
  - 1st or 3rd of 3 references (`ER_IO_READ` + `S_ERROR`): exits `1`, prints `"Only 2 out of 3 objects processed successfully."`, preserves all 3 references.
  - Partial set mutation (`set{deleted_ref, S_ERROR_ref}`): row 1 is counted as failed (`exit 1`) and NOT written to disk (partial nulling discarded); row 2 is still processed and cleaned.
  - Altered class (`ALTER TABLE ADD COLUMN`): `S_ERROR` suppresses `catalog_drop_old_representations()`, all rows remain readable.
- **CS single-batch `S_ERROR` + deleted ref + altered class (`gdb`, Level 5):** `Failed objects: 1`, `Modified objects: 2`, `Old class representations preserved in catalog.`, row 1 ref kept, row 2 deleted ref set to NULL, all rows readable cold-cache.
- **HA / Replication & MVCC (`S_SNAPSHOT_NOT_SATISFIED`):** Cleared at Level 3 (`S_SNAPSHOT_NOT_SATISFIED` requires valid `DELID`; PR changes no WAL records or replication payloads).
