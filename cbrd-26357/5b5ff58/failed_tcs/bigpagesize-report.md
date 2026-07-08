# bigPageSize Failure Diagnosis (Preserved-Log Reproduction)

Generated: 2026-07-08 KST
Build under test: `11.5.0.2367-309753d` (debug, matches the report set; worktree HEAD `f59e9b8b2` is NOT in this build)

## Verdict

**Not an engine bug. No OOS Expand / raw-record corruption.** The testcase compares raw CLOB/BLOB
locator strings between two rows that are chosen nondeterministically among 256 duplicates tied on the
`ORDER BY` key. The OOS branch changed db2's physical row order (OOS demotion instead of `REC_BIGONE`
on 4k pages), so db1 and db2 no longer happen to pick the same tied row.

## Reproduction

- Commented out the cleanup `rm -rf ...` line in `cases/bigPageSize.sh` (temporary, still in place).
- `just shell-debug .../bigPageSize` → `bigPageSize-1 : NOK`, `diff csql1.log csql2.log failed`.
- `bigPageSize-2` (load.answer vs load.log) is OK: `Total 256 object(s) inserted, 0 object(s) failed.`

## The Entire Diff (out of 35,537 lines)

```text
35483,35484c35483,35484
<         cl : file:4609046085/ces_475/dba.t.00001783484829960615_9250
<         bl : file:4609046084/ces_535/dba.t.00001783484829960534_9637
---
>         cl : file:4609046085/ces_673/dba.t.00001783484842143449_8229
>         bl : file:4609046084/ces_724/dba.t.00001783484842143317_7306
```

## Evidence Chain

1. `init.sql` inserts ONE seed row, then doubles it 8 times via `INSERT ... SELECT` → 256 rows
   **identical in every selected column** (`col1 = -32768` for all). Only `cl`/`bl` differ per row,
   because LOB copy-on-insert (`db_elo_copy_with_prefix` in the `LOB_FLAG_INCLUDE_LOB` transform)
   gives each copied row fresh lob files. `id` (auto_increment) is not in the SELECT list.
2. The test query is `select ... from t order by 1 desc limit 1` → `col1` ties on all 256 rows →
   the returned row is arbitrary (physical order / sort tie-break dependent).
3. Both of csql2's "different" locators exist **verbatim** in `tdb1_objects`, adjacent on the SAME
   object row → server-side loaddb preserved locators exactly; no lob re-creation, no cross-row mixing.
   (`to_db_elo_ext` builds the ELO from the unloaded locator verbatim; loader uses
   `heap_attrinfo_transform_to_disk_except_lob` = `LOB_FLAG_EXCLUDE_LOB`, so no copy.)
4. `tdb1_objects` contains exactly 256 distinct CLOB locators + 256 distinct BLOB locators.
5. Row-position check: csql1 (db1, 16k pages, SA) returned unload-order row **#1**;
   csql2 (db2, 4k pages, CS, freshly loaded) returned unload-order row **#256**.
6. Timestamps: csql2's locator epoch (13:27:22) predates the tdb2 server start (13:27:42) —
   the locator was minted by db1's `INSERT...SELECT` doubling, further proof it is an original db1 locator.

## Why It Passes on develop

Locator preservation is identical on develop. The test passed because db1 and db2 happened to produce
the same physical row order, so both sides picked the same tied row. On the OOS branch, db2 (4k pages,
`DB_PAGESIZE/8 = 512B` threshold) stores these rows as OOS records instead of `REC_BIGONE` multipage
records; page allocation / scan order differs, and the arbitrary tie-pick diverges.

## Fix Options (testcase-side)

- **(A) Deterministic tiebreak (recommended):** change the query to `order by 1 desc, id desc`
  (or `order by id desc`). Both DBs then pick the same row, and the byte-comparison of locators
  still verifies unloaddb/loaddb locator preservation — the strongest regression value, minimal diff.
- **(B)** Normalize/mask `file:...` locator text in both logs before comparison; keeps the tie but
  drops locator-preservation coverage.
- **(C)** Select LOB content (`CLOB_TO_CHAR(cl)`, `BLOB_TO_BIT(bl)`) instead of raw locators;
  verifies content round-trip but no longer checks locator preservation.

## Preserved Artifacts

`~/cubrid-testcases-private-ex/shell/_35_cherry/issue_21654_server_side_loaddb/bigPageSize/cases/`
(`csql1.log`, `csql2.log`, `tdb1_objects` **522MB**, `tdb1_schema`, `load.log`, `bigPageSize.result`).
The cleanup line in `bigPageSize.sh` is still commented out; restore it (and remove artifacts) once a fix
direction is decided.

