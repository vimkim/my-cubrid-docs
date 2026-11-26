# Code review: CUBRID/cubrid#8690 (CBRD-28274, release/11.4) and TC PRs #4397, #4387

**Goal:** review the release/11.4 fix that rebuilds rows of an older representation before REORGANIZE, COALESCE or REMOVE PARTITIONING redistributes them. Check backport accuracy against develop, and the linked TC PRs.

**Main result:** the fix gets the values right in every case tested (TC + 131 probe checks pass). But it introduces a **crash-recovery defect**. An old-representation overflow row (REC_BIGONE) that shrinks into an ordinary in-page row keeps the overflow-row MVCC header flags. That makes the MVCC insert redo fail after a crash (finding **F1, P1**). The fix is a few lines.

## Verdict and follow-up

- **Verdict:** `changes-required` (GitHub review: `CHANGES_REQUESTED`). 1 confirmed finding: P1 ×1.
- **Follow-up review required:** yes. Re-review the fix for F1, plus a server-mode crash-restart test, before merge. The release-build consequence of F1 and the develop/OOS variant (R-2) are open questions; neither blocks the 11.4 fix.

## Pinned scope

| Item | Value |
|---|---|
| Engine PR | [CUBRID/cubrid#8690](https://github.com/CUBRID/cubrid/pull/8690), author hornetmj, head `CBRD-28274-release-11.4` |
| base (release/11.4) | `065c452fe82724f12c78e136f90cb6c595cbbc49` |
| head | `46e71173c06c9c9fa24400c4de10239eaac84c95` |
| merge base | `065c452fe82724f12c78e136f90cb6c595cbbc49` |
| Comparison | `git diff 065c452fe82724f12c78e136f90cb6c595cbbc49 46e71173c06c9c9fa24400c4de10239eaac84c95` (patch sha256 `4dc8ecc1…3a402790`) |
| Changed paths | `src/transaction/locator_sr.c` (+58/−1, `redistribute_partition_data` only) |
| develop reference | `ca5c2153edb860ed28259aedf55753382df745a0`; #7990 merge `68a9c7766ffd99c60cc8dd18fba0394e4a60f2e1` |
| TC PRs | cubrid-testcases#4397 `a49b6062c484b8f6ca63a2b29d2c703ddad2d4b7`; #4387 `cf1e43c9db8d947a1f636d2d49d82e190cc4bae1`; related #4371 `102c149972f696e79c47830d19a54812e3f3911b` |
| Snapshot | 2026-11-26 |

## Confirmed findings

### F1 [P1] An old-representation overflow row rebuilt into an in-page row keeps the overflow header's DELID flag, so redo of the insert fails after a crash

- **Location:** [`locator_sr.c:12891-12905`](https://github.com/CUBRID/cubrid/blob/46e71173c06c9c9fa24400c4de10239eaac84c95/src/transaction/locator_sr.c#L12891-L12905) (`or_mvcc_get_header` → `repid := latest` → `or_mvcc_set_header`).
- **Preconditions:**
  - Server mode. In SA mode `heap_insert_logical` logs non-MVCC (`heap_file.c:23148-23153`).
  - A row stored as REC_BIGONE in an older representation, whose rebuilt length fits in a page. Typical case: DROP COLUMN of the large columns, then REORGANIZE, COALESCE or REMOVE PARTITIONING.
  - A crash before the target heap page is flushed, or log replay (`restoredb`).
- **Mechanism:**
  1. Overflow rows always carry the maximum MVCC header: INSID | DELID(=MVCCID_NULL) | PREV_VERSION (`HEAP_MVCC_SET_HEADER_MAXIMUM_SIZE`, `heap_file.c:129-148`; `heap_file.c:19225-19246`).
  2. The PR copies those flags unchanged onto the rebuilt record.
  3. `heap_insert_adjust_recdes_header` (UPDATE_INPLACE_OLD_MVCCID) strips only PREV_VERSION (`heap_file.c:20284-20289`). The row is inserted as REC_HOME with the DELID flag set but no valid DELID.
  4. Because the DELID is not valid, the insert is logged by `heap_mvcc_log_insert`, which records only the flag word and the body (`heap_file.c:15969-15985`).
  5. Redo `heap_rv_mvcc_redo_insert` asserts `!(mvcc_flag & OR_MVCC_FLAG_VALID_DELID)` (`heap_file.c:16054`). It then rebuilds the header from an uninitialized `MVCC_REC_HEADER` (`heap_file.c:16017`), so in release builds the DELID written back is stack garbage.
- **Precedent for the right handling:** `locator_update_force` (`locator_sr.c:5819-5827`) copies DELID only when `MVCC_IS_HEADER_DELID_VALID`, and clears the flag otherwise.
- **Attribution:** base never rebuilds. An old-representation overflow row stays REC_BIGONE (bytes relabelled) and takes the overflow logging path, so this header state is unreachable on base. That is a source argument; base was not built. A same-build control on the relabel path recovers cleanly (see below).
- **Reproduction (level 5, coordinator replayed):**
  - Script: `systems/probe/redo/run.sh setup.sql coord-shrink`, on the head debug install `11.4.7.2008-46e7117`.
  - Steps: CHAR(2048)×10 + VARCHAR, 5 rows; DROP the 10 CHAR columns; REORGANIZE; `kill -9` the server; restart with `csql -S`.
  - Expected: recovery completes and 5 rows are returned.
  - Actual: `heap_file.c:16054: int heap_rv_mvcc_redo_insert(THREAD_ENTRY*, LOG_RCV*): Assertion '!(mvcc_flag & OR_MVCC_FLAG_VALID_DELID)' failed.`, `csql -S exit=134`.
  - Controls on the same build both recover with 5 rows, exit 0: `setup_nodrop.sql` (relabel path, the base behavior) and `setup_drop1.sql` (rebuilt but still overflow).
  - R2 reproduced this independently in client/server mode (the `cub_server` restart loop aborts in redo).
- **Impact:**
  - Debug builds cannot restart past this DDL after a crash.
  - Release builds (source only, not run): redo restores the row with an arbitrary DELID. The row can become invisible and be removed by vacuum, which is silent data loss after crash or media recovery.
- **Fix direction:** right after `or_mvcc_get_header (&recdes, &mvcc_header)`, add:

  ```c
  if (!MVCC_IS_HEADER_DELID_VALID (&mvcc_header))
    {
      MVCC_CLEAR_FLAG_BITS (&mvcc_header, OR_MVCC_FLAG_VALID_DELID);
    }
  MVCC_CLEAR_FLAG_BITS (&mvcc_header, OR_MVCC_FLAG_VALID_PREV_VERSION);   /* optional; adjust_recdes_header strips it anyway */
  ```

  Then rerun the crash-restart probe in server mode (old-representation big row → DROP COLUMN → REORGANIZE/COALESCE/REMOVE → `kill -9` → restart).

## Safety facts and effects outside the diff

| # | Fact | Owner | Evidence |
|---|---|---|---|
| S1 | **Values match SELECT (Q1, both reviewers independently).** The rebuild reads with `heap_attrinfo_read_dbvalues` against the partition's own representation, the same reader as SELECT. ADD COLUMN defaults come from `last_attrepr->default_value`, DROP/FIRST/AFTER match by attribute id, and LOB locators pass through `_except_lob`. | R1, R2 | L3 source; L4 probes a–e (125/125) + c2 (6/6) |
| S2 | **Schema-only domain changes.** Only VARCHAR/VARBIT precision increase, NUMERIC precision increase with the same scale, and compatible set changes leave old-representation rows. Other type changes rewrite every row (`xlocator_upgrade_instances_domain`). W1 observed old-representation rows for VARCHAR(10)→(50) and NUMERIC(5,2)→(10,2); both redistributed correctly. | R1, W1 | L3 + L4 |
| S3 | **Header growth fits.** The transform reserves 16 spare bytes and `record_descriptor` never shrinks, so `or_mvcc_set_header` and the later maximum-size header fit. `new_recdes` is refreshed per row. | R1 | L3 |
| S4 | **Resource pairing.** attrinfo start/end is paired on every path, there is no per-row DB_VALUE leak, and every new error branch returns a set code. | R1 | L3 |
| S5 | **LOB files.** 50 LOB files before and after REORGANIZE/REMOVE, and content is equal. | W1 | L4 (probe d) |
| S6 | **Latching.** Fetching an old representation under the instance-page WRITE latch takes only a READ latch on the root-class heap page. The same pattern already runs in `locator_insert_force` → `heap_get_class_repr_id` and in `scan_next_heap_scan`. No new latch-order cycle found. | R1, R2 | L3, not stress-tested |
| S7 | **Undo and rollback.** Insert undo deletes the slot regardless of the bytes. Source partitions are dropped only after redistribution. | R2 | L3 |
| S8 | **HA/CDC.** The ALTER replicates as a statement, and the slave runs its own redistribute. No data replication item, no supplemental insert log, and no log or disk format change. | R2 | L3 |
| S9 | **Source/target layout parity** (a pre-existing assumption, `partition.c:3051-3056`). Partitions get the root's attribute ids and order, and promotion creates no new representation. Covered by TC case 6 (ADD FIRST/AFTER). | R1, R2, R3 | L3 + L4 (TC) |

## Backport accuracy (release/11.4 vs develop)

- **Develop is already fixed.** #7990 (`68a9c7766f`, single parent `de4f32740`) routes every redistributed row through `heap_prepare_oos_record`, which reads with the row's own representation and re-encodes into the latest one. No later develop commit touches the function, so the PR's claim that develop needs only a TC holds (L3).
- **Equivalent for old-representation rows.** The 11.4 fix matches develop on the representation used, defaults, LOB exclusion and the header copy (copy the source header, set `repid`, `or_mvcc_set_header`). The intended differences are that 11.4 rebuilds only rows with `or_rep_id != latest` and has no OOS. Passing the parent `class_oid` to `heap_get_visible_version` (develop passes the partition) is irrelevant on 11.4.
- **Develop shares the header copy (R-2, unverified).** `heap_prepare_oos_record` has the same verbatim copy (`header.repid = …; or_mvcc_set_header`). On develop an overflow row whose columns move to OOS can shrink to an in-page record, which may reach the F1 state even without DROP COLUMN. Not executed.
- **Older release lines.** The same defect shape exists on release/11.3, 11.2, 11.4_hotfix, 11.1, 11.0 and 10.x (report only; porting is the owner's decision).

## TC PRs

| TC PR | repo / base | path | author | state | relation |
|---|---|---|---|---|---|
| [#4397](https://github.com/CUBRID/cubrid-testcases/pull/4397) | cubrid-testcases / release/11.4 | `sql/_13_issues/_25_2h/{cases,answers}/cbrd_28274.*` (+136/+270) | hornetmj | open | TC for #8690. Byte-identical to #4371 except the folder. |
| [#4371](https://github.com/CUBRID/cubrid-testcases/pull/4371) | cubrid-testcases / develop | `sql/_13_issues/_26_2h/…` (+136/+270) | hornetmj | draft | develop regression TC, named in the #8690 body |
| [#4387](https://github.com/CUBRID/cubrid-testcases/pull/4387) | cubrid-testcases / develop | `sql/_13_issues/_26_2h/…` (+117/+173) | vimkim | open | Same path and purpose as #4371; `git merge-tree` shows add/add conflicts on both files, so only one can land. |
| `tc/pr-8690` | both TC repos | — | — | absent | release/11.4 has no TC Branch Sync / TC Merge Gate workflows |

TC notes (not defects of the engine change):

- **T1 (P3): wrong folder.** #4397 says release/11.4 has no `_26_2h`, but live release/11.4 (`c4884303d`) has it (15 cases; other 11.4 backports use it). The TC branch base `82df17e15` is 79 commits behind. Rebasing and moving the files to `_26_2h` would keep the path identical on develop and 11.4. Coordinator replayed.
- **T2 (P3): duplicate develop TCs.** #4371 covers more: HASH 6→2, mixed old and latest rows, NOT NULL DEFAULT, FIRST/AFTER, index vs full-scan counts, a control table. #4387 adds boundary-row SELECTs and NULL checks at every stage. Suggest keeping #4371, closing #4387 (vimkim's own; tracker #1059 already says "정리만"), and optionally porting #4387's boundary SELECTs. Coordinator replayed the conflict.
- **T3 (P4): NULL-blind predicates.** In cases 1, 5 and 6 (`x <> 'dflt'`, `v <> 'v'||id`, `count(distinct x)`), NULL compares as UNKNOWN. Other aggregates partly mitigate this.
- **T4 (P3): uncovered paths.** The TC does not cover LOB, overflow or relocated old-representation rows, schema-only domain widening, or crash restart. The engine verification was SA-only (`csql -S`), and SA never logs MVCC inserts, so it cannot catch F1. Recommend adding at least an overflow-row case to the TC, and running a server-mode crash-restart check during review.
- **Answers are correct.** R3 recomputed every aggregate independently. The TC passes on head: native testkit verify `total=1 success=1 fail=0`.

## Coverage and verification

Checks actually run (local artifact paths are relative to the review run directory `/home/vimkim/temp/cubrid-reviews/pr-8690-20261126/`):

| Check | Revision / config | Result | Artifact |
|---|---|---|---|
| Build + install | head, `debug_gcc` | exit 0 | `build-test/logs/head-configure-build-install.log` |
| TC #4397 `cbrd_28274` (native testkit sql, contained) | head debug, TC a49b6062c4 | PASS 1/1 | `/home/vimkim/tk/p8690a/verify.txt` |
| Probes a–e (type change, defaults, MVCC mix, LOB, overflow) | head debug, SA | 125/125 pass, checkdb 0 | `build-test/probe-out/head*/` |
| Probe c2 (concurrent REPEATABLE READ reader) | head debug, CS | 6/6 pass | `build-test/probe-out/head-c2/` |
| F1 crash-restart redo | head debug, CS + `kill -9` + restart | assertion, exit 134 (R1, R2, coordinator replay) | `systems/probe/redo/coord-shrink/` |
| F1 controls (nodrop, drop1) | same | recover OK | `systems/probe/redo/out-nodrop`, `out-drop1` |
| `cubrid-static-check` | base..head | cppcheck 0, clang-tidy 0, CPD 0; lizard `redistribute_partition_data` CCN 33→41 | `static-check.md` |
| GNU indent 2.2.11 `-l120 -lc120` | head file | zero diff | `systems/probe/indent.diff` |

**Not run:**
- Base build or any base run.
- Release build (F1 release consequence).
- REC_RELOCATION/NEWHOME old-representation rows (the probe could not produce them).
- HA slave end-to-end.
- Latch stress.
- Develop variant R-2.

## Unverified risks and pre-existing defects

| ID | Kind | Statement | Next check |
|---|---|---|---|
| R-1 | unverified | F1 on a release build: garbage DELID after redo hides or vacuums the row. | Run `run.sh` against a release install. |
| R-2 | unverified, develop | `heap_prepare_oos_record` copies the overflow header the same way; an OOS-shrunk row may hit the F1 state on develop. | Server-mode crash-restart after COALESCE of a table with overflow rows on develop. |
| P-1 | pre-existing (since 2015, also on develop) | `heap_mvcc_log_redistribute` logs an uninitialized `MVCCID delid` (`heap_file.c:24835`), so crash redo can bring back a row deleted in the same transaction before redistribution. R2 reproduced it: COUNT 4 → 5 after restart, logged delid `0x00007f07ebf75060`. Coordinator verified the source only. | Separate CBRD issue; fix with `delid = MVCC_GET_DELID (&mvcc_rec_header)`. |
| P-2 | pre-existing | `redistribute_partition_data` `exit:` reads an uninitialized `scan_cache.page_watcher.pgptr` on an error before the first `heap_scancache_start` (`locator_sr.c:12709/12948`). | Initialize the watcher at function entry. |
| P-3 | pre-existing | `diagdb -d 9 --dump-records` crashes with SIGSEGV in `heap_attrinfo_dump` (`heap_file.c:10634`) on heaps with old-representation rows missing an added column. | Separate issue. |
| N-1 | nit | `redistribute_partition_data` CCN 33→41; the rebuild block could be a helper (`static int locator_rebuild_to_latest_repr (...)`). | Optional. |

**Dropped candidates:**
- R1 rejected 7 hypotheses (header overflow, deleted-row type mismatch, CHAR/NUMERIC slot size, layout/repid collision, latch deadlock, indent mangling).
- R2 rejected source-row deletion, PREV_VERSION leakage to vacuum, and HA format change.
- R3 rejected the relevance of the `class_oid` difference.
- Duplicates: R1-C1 and R2-C1 merged into F1.

## Budget accounting

- **Mode:** bounded. No hard cap was enforced.
- **Agents:** 3 reviewer subagents (R1 opus xhigh, R2 sonnet xhigh, R3 sonnet xhigh) + 1 Herdr build/test tab (`w2RB:t2`, Claude) + the coordinator. No retries.
- **Targets:** R1 and R3 within about 45 minutes. R2 ran about 30 minutes over its 45-minute target for the C1/P-1 probes. W1 about 13 minutes.
- **Measured usage:** subagent tokens R1 324k, R2 402k, R3 223k. Coordinator and W1 tokens unknown.
- **Account telemetry:** 5-hour window 87% → 80% used across a reset, 7-day 91–92%.
