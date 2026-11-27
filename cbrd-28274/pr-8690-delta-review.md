# CUBRID/cubrid#8690 delta re-review (CBRD-28274, release/11.4)

- **PR:** [CUBRID/cubrid#8690](https://github.com/CUBRID/cubrid/pull/8690), "[CBRD-28274] Rebuild a row of an older representation in the latest one before redistributing it to partitions"
- **Base:** `release/11.4` `065c452fe82724f12c78e136f90cb6c595cbbc49`
- **Previously reviewed head:** `46e71173c06c9c9fa24400c4de10239eaac84c95`, verdict CHANGES_REQUESTED (F1). See [first review](pr-8690-review.md).
- **New head:** `182431bea7e7af4b3d6f8d1f16dd7ac68bcda914`. The old head is an ancestor. The delta is 4 commits:
  - `e0bc8d7c40`
  - `47e1a6988c`
  - `50621132d3`
  - `182431bea7`
- **Delta:** `git diff 46e71173c0 182431bea7`
  - `src/storage/heap_file.c` +5/−1
  - `src/transaction/locator_sr.c` +77/−23
  - SHA-256 `c836998031be…`
- **Full change:** `git diff 065c452fe8 182431bea7`, +117/−2 over the same 2 files.
- **Testcase PRs:**
  - [cubrid-testcases#4397](https://github.com/CUBRID/cubrid-testcases/pull/4397) (`release/11.4`, `d44208d080`)
  - [cubrid-testcases#4371](https://github.com/CUBRID/cubrid-testcases/pull/4371) (`develop`, `f286f3aa78`)
  - one private shell test PR
- **Date:** 2026-11-27

## Verdict

**APPROVE (recommended).** The delta fixes F1. It also fixes the pre-existing redistribute redo defect P-1 ([CBRD-28107](https://jira.cubrid.org/browse/CBRD-28107)) on release/11.4. Source review, server-mode crash-restart probes, and the TC runs found no new defect. The remaining items are non-blocking: one pre-existing redo nit (N-2), stale TC PR descriptions (N-3), and develop follow-ups (O-1, O-2).

## What changed since the first review

1. **`locator_rebuild_record_in_latest_rep` (new static function, `locator_sr.c:12708`).**
   - The rebuild block moves out of `redistribute_partition_data` into this function, and behavior is preserved.
   - Before the header is written back, the function now clears two flags:
     - `OR_MVCC_FLAG_VALID_DELID` when the DELID is not valid (`:12742-12745`). This fixes F1.
     - `OR_MVCC_FLAG_VALID_INSID` when INSID is `MVCCID_ALL_VISIBLE` (`:12738-12741`). This is new.
2. **`heap_mvcc_log_redistribute` (`heap_file.c:24862-24864`).**
   - It now logs `MVCC_GET_DELID` of the record, packed with `OR_PUT_MVCCID`, instead of an uninitialized stack `MVCCID`.
   - `heap_rv_mvcc_redo_redistribute` reads the value with `OR_GET_MVCCID`, so the byte order now matches.
   - This is the P-1 fix (CBRD-28107).

## Findings

| ID | Status | Summary |
|---|---|---|
| F1 | **Fixed, verified** | An old-representation REC_BIGONE row that shrinks into a home record no longer keeps the DELID flag. The crash-restart replay passes, and the old head asserted at `heap_file.c:16054` in the same scenario. |
| D-1 | **Correct, verified** | Clearing the INSID flag when INSID is `MVCCID_ALL_VISIBLE`. For a row that becomes a home record, redo no longer stamps the transaction's MVCCID onto a row that vacuum has already passed. For a row that stays REC_BIGONE, `heap_insert_adjust_recdes_header` restores the maximum header with INSID = `MVCCID_ALL_VISIBLE` (`HEAP_MVCC_SET_HEADER_MAXIMUM_SIZE`), the same as for unrebuilt rows. |
| P-1 | **Fixed on release/11.4, verified** | A deleted row moved by REORGANIZE no longer comes back after crash recovery. A redo trace shows that the logged DELID equals the deleting transaction's MVCCID. Before the fix it was a stack address. |
| D-3 | OK | The refactor keeps behavior and error paths: every error `goto exit`s, and `attr_info` and `new_record` are cleaned up there. |
| N-1 | nit, improved | `redistribute_partition_data` complexity: CCN 33→38 and length 216→255, down from 33→41 and 273 at the old head. The new function has CCN 8. |
| N-2 | nit, pre-existing | `heap_rv_mvcc_redo_redistribute` leaves `mvcc_rec_header.chn` uninitialized (`heap_file.c:24902`) before `or_mvcc_add_header` (`:24958`). The impact is low because only committed-deleted rows take this path. `MVCC_REC_HEADER_INITIALIZER` would make it clean. |
| N-3 | nit | The descriptions of #4397 and #4371 still say 7 cases, and #4397 still says `_25_2h`. The diffs add 9 cases under `sql/_13_issues/_26_2h/`. |
| O-1 | follow-up, develop | `develop` (`36a047bebd`) still logs the uninitialized `delid` in `heap_mvcc_log_redistribute`. release/11.4 now has a fix that develop lacks, and CBRD-28107 should carry it to develop. |
| O-2 | follow-up, develop (unverified) | R-2 from the first review: `heap_prepare_oos_record` on develop copies the overflow header verbatim, so the F1 and D-1 shape may exist there. It is tracked separately and not run. |

The first review's pre-existing items P-2 and P-3 are now filed as [CBRD-28433](https://jira.cubrid.org/browse/CBRD-28433) and [CBRD-28434](https://jira.cubrid.org/browse/CBRD-28434). The delta does not touch either.

## Verification (head `182431bea7`, debug build `11.4.7.2012-182431b`)

Every crash case runs in CS (server) mode: setup and commit, `kill -9` of `cub_server`, an explicit restart (crash recovery), a comparison of the data before and after, then `checkdb`.

| Check | Result |
|---|---|
| Build, static check (cppcheck, clang-tidy, CPD: 0 new), GNU indent (0 diff) | PASS |
| F1: drop all 10 `CHAR(2048)` columns of 5 overflow rows, then REORGANIZE (rows shrink to home) | PASS. 732 records redone, data identical, `checkdb` 0, no assert. Replayed independently by the coordinator. |
| F1 variant: drop 1 column (rows stay REC_BIGONE); control with no DROP COLUMN | PASS, both |
| P-1: DELETE a row, REORGANIZE, commit, crash | PASS. 4 rows, sum 12 after restart; the deleted row was not resurrected. Logged delid = deleting MVCCID (redo breakpoint). |
| D-1: 6 cases (REORGANIZE and COALESCE × shrink, stay-big, current-rep control), with vacuum past the rows before the DDL | PASS. Recovery OK, data identical, `checkdb` 0. Headers after redo: rebuilt-to-home rows have flags 0x0; rebuilt-big and control rows have 0x7 with insid=3 (ALL_VISIBLE). |
| SQL TC #4397 (`sql/_13_issues/_26_2h/cases/cbrd_28274.sql`), native testkit | PASS 1/1 |
| Private shell test (server crash after redistribution) | PASS, 11/11 checks |

The answers for the new SQL cases 8 and 9 were also checked by hand arithmetic, and #4397 and #4371 are byte-identical. The first review's TC items are resolved:
- T1: folder `_26_2h`.
- T2: #4387 closed.
- T3: `is null` checks added.
- T4: overflow cases 8 and 9 added, and crash recovery is covered by the shell test.

## Not run / limits

- The private shell test was not run on the base build, because no base debug install was available. The old head's failures (the F1 assert and the P-1 resurrection) are indirect evidence that it fails before the fix.
- Release build: not run (R-1 from the first review remains a source-level argument).
- REMOVE PARTITIONING was covered by the TCs only, not by the header probes.
- REC_RELOCATION source rows in an old representation, and LOB columns, are not exercised by the TCs.
- develop items O-1 and O-2: source only.
