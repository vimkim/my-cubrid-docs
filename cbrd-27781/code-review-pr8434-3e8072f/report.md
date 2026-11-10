# CUBRID PR 8434 review (CBRD-27781, ADR-0008) — run 2, specialists

Saved by the lead session from the coordinator's returned text (the harness refused the coordinator's own report writes). The "Resolution after the review" section at the end was added by the lead session.

## Scope

- Base and merge base `d52b1889e907abcf84190ec504dde3bc93de260d`; head `3e8072f5681854a0b345c33adf5096b226fa2ce3` (unchanged at the end).
- Patch `evidence/pr.patch` (sha256 ed2ce918…a08a).
- R1 fix: specialists reviewed `evidence/r1-fix-worktree.patch` (sha256 b22b31c5…). The worktree then moved to 38f1a458… (adds a rebuild floor); that delta had a coordinator-only read. The lead session later committed the fix as `6ac2d7de6`.

## Verdict

`incomplete`. No confirmed findings, because execution was forbidden in this pass (no build, ctest, or servers). Evidence for every item is at most level 3 (a complete source argument). Follow-up review is required: run the R2 check before committing the R1 fix, and settle R3, R4, and R5 before merge.

## Unverified risks, ranked

### R2 (proposed P2; introduced by the R1 fix) — a notification-only block asserts `oldest <= newest`

- Assert: the `vacuum_data_entry` constructor (head+fix `vacuum.c:8447`), reached from `vacuum_produce_log_block_data` (`vacuum.c:3149`) and the SA partial-block path (`vacuum.c:1085`).
- Path:
  1. T bulk-UPDATEs OOS columns on a quiet server; each row logs one `RVOOS_UPDATE_DROP_POSTPONE`.
  2. At commit, `logtb_complete_mvcc` (`log_manager.c:5308`) runs before `log_tran_do_postpone` (5325).
  3. The vacuum master moves the global oldest visible G past m.
  4. A log block whose first MVCC record is one of T's notifications gets oldest = G and newest = m (`log_append.cpp:1357-1358`); the fix no longer lowers oldest.
  5. When the log crosses into the next block, the constructor asserts.
- Impact: debug only (dispatch reads only newest). The new test misses it because its filler insert raises newest. The v2 rebuild floor can also restore a header with oldest = floor > newest = m.
- Fix direction: relax the constructor assert for notification blocks. Do not raise newest; the block would never become ready on an idle system.
- Found by r1fix (opus, proposed P1); assert and commit order verified by the coordinator.

### R5 (proposed P2; introduced by the PR; reachability unproven) — eager reclaim at commit fail-stops on a transient latch miss

- Path: `oos_rv_reclaim_on_postpone` (`oos_file.cpp:3837-3862`) → `oos_delete` → `oos_fix_page_if_oos` (2486). With lock timeout 0, `pgbuf_fix` turns `PGBUF_UNCONDITIONAL_LATCH` into a conditional request (`page_buffer.c:2247-2256`, verified). A busy page returns `ER_LK_PAGE_TIMEOUT` → `oos_reclaim_fail_stop` (3808-3823) → `logpb_fatal_error`. Nothing on the commit path lifts no-wait.
- Preconditions: SERVER_MODE, non-MVCC DML on an OOS-bearing record (MVCC-disabled class or in-place update), lock_timeout 0, a concurrent latch on one of the chain's pages.
- Base: the eager delete ran inside the DML; the same miss failed only the statement. ADR decision 3 reserves fail-stop for persistent errors.
- Fix: wrap the reclaim in `pgbuf_force_latch_wait` (`page_buffer.c:5364`; used at `disk_manager.c:3242/3520`) or retry.
- Open: do OOS-bearing records exist in MVCC-disabled classes or on in-place update paths?
- Found by concurrency (sonnet).

### R3 (proposed P2; introduced by the PR; v2 closes most) — restart rebuild seeds oldest from a notification

- `vacuum_recover_lost_block_data` (head `vacuum.c:5920`) walks backward; if the newest MVCC record is a notification, recovered blocks and the restored header (5942) get oldest ≤ m, possibly below the last saved entry. Always the case after a restart rerun of drop postpones; also after a crash late in a long postpone phase.
- Debug: asserts in vacuum_boot at 5566, 8424, 8431, 7406 on every restart. Release: oldest_unvacuumed moves backward (treated conservatively).
- Found by r1fix (opus) and recovery (opus) independently.
- v2: the last-saved-entry floor fixes ordering. Remaining: (a) restored header oldest > newest is R2; (b) no floor when `last_page->index_free == 0` while an earlier page holds entries — unanalysed.

### R4 (proposed P3; debug only; introduced by the PR) — notification appended during restart recovery

- During `log_recovery_finish_all_postpone` (`log_recovery.c:4082`), the rerun of `oos_rv_update_drop_on_postpone` appends `RVOOS_NOTIFY_VACUUM` before vacuum_boot (`boot_sr.c:2451`). `LOG_ISRESTARTED()` is false (no block produced, `log_append.cpp:1412`); `get_global_oldest_visible()` is MVCCID_NULL (`mvcc_table.cpp:173`); `does_block_need_vacuum` is stale on-disk.
- Flag false: header oldest becomes 0; next MVCC append asserts at `log_append.cpp:1363`. Flag true and a later block: asserts at 1366/1367. Release: vacuum_recover_lost_block_data rewrites the header, except with vacuum disabled.
- First MVCC record ever appended by a restart postpone (level 2).
- Found by r1fix, recovery, and concurrency independently.
- Fix: when `!LOG_ISRESTARTED()`, keep only the mvcc_op_log_lsa link and the flag; skip the asserts and the global-oldest read.
- Check: SERVER_MODE crash test with an `_exit` hook in `oos_rv_update_drop_on_postpone`, ≥ 2 drop postpones (also covers R3-restart and ADR consequence 5).

### R6 (P3) — inconsistent out-of-memory handling in the notification consumer

`vacuum_oos.cpp:218-226` returns ER_OUT_OF_VIRTUAL_MEMORY without fail-stop (debug assert in vacuum_check_shutdown_interruption; release retries the block), while `oos_reclaim_notified_chains` fail-stops on the same error from unpack (`oos_file.cpp:3955-3959`). `er_errid()` at 3964 can be stale.

### R7 (P3; hardening) — readers never check the link stamp

`oos_read_across_pages` (`oos_file.cpp:2623`) ignores `next_chunk_stamp`; `oos_read_within_page` (2597-2619) uses a plain fix. A reader without a snapshot racing a reclaim could read another chain's chunk in release, or hit ER_PB_BAD_PAGEID / a debug assert. MVCC readers are excluded by A'.

### R8 (P3; mechanism predates the PR) — stop between LOG_COMMIT_WITH_POSTPONE and LOG_COMMIT drops replication records

Postpones run at `log_manager.c:5325`; replication records and commit are appended at 5349; recovery's `log_complete` appends only the commit (5832). Silent master/slave divergence. The PR adds a deliberate fail-stop in that window for eager non-MVCC reclaims. Fix: document in ADR consequence 6, or keep reclaim failures off the user-commit path.

### R9 (P3) — fail-stop prints an uninitialised intent header

`oos_file.cpp:3839/3952` then 3845/3958: when unpack fails before its memcpy, the header is unfilled. Fix: `= {}`.

### R10 (P3) — the R1-fix comment cites the wrong reason

The real safety fact: dropped-file cleanup is SA_MODE only (single caller at `vacuum.c:1113`, inside the SA branch of xvacuum, after every block is done), and the lookup compares m < D strictly (6954).

### R1 (head, without the fix)

Debug ordering asserts remain. The release consequence in run 1 is disproven: in SERVER_MODE nothing removes dropped-file entries (besides SA cleanup, only undo of an add and redo of a cleanup).

## Pre-existing (reported separately)

- P-1: the eager path still fixes the heap header while holding a heap data page (`heap_oos.cpp:985/1030` → `heap_file.c:13350`), the cycle CBRD-27860 fixed for vacuum. Tracked as [CBRD-28012](https://jira.cubrid.org/browse/CBRD-28012). Same in base; the rewrite could carry the HFID as the MVCC path does.
- P-2: on a reused heap VFID, a notification from an older transaction is classified as dropped and skipped → chain leak. FILE_HEAP tables without reuse-OID only. Tracked as [CBRD-27982](https://jira.cubrid.org/browse/CBRD-27982).

## Missing evidence and spec conformance

- Missing ADR-0008 consequence 5 tests: crash between LOG_COMMIT_WITH_POSTPONE and the notification (restart rerun of the drop postpone); restart of a vacuum REMOVE sysop's postpone; page deallocation during a reclaim (partial); concurrent reclaimers of one chain.
- The crash test is SA_MODE only; its second child accepts any nonzero exit, and a debug `logpb_fatal_error` aborts, so "re-failure during recovery" is not established (`test_oos_sql_crash_recovery.cpp:489-495`).
- NULL-snapshot readers not fully enumerated.
- Performance (from code, unmeasured): one postpone per updated row; past 512 entries the postpone cache overflows (`system_parameter.c:5476-5486`) and commit scans with log_do_postpone (`log_manager.c:8319-8327`); any rollback resets the cache (8155). About 400 B log per row. Vacuum fixes the heap header once per notification (VFID memo removed); collect and delete passes fix each chunk twice. Probe: `reviewers/systems-storage/probe_ss1_bulk_update.sql`.

## Cleared (source level 3)

- `log_do_postpone` LSA_LE is correct for all callers; develop has the same LT bug; `find_first_postpone` keeping LT is harmless.
- Each intent runs exactly when its deciding unit commits; every abort path discards it; INCR sub-transaction UPDATE correct.
- Crash points (a)–(f) restart correctly for OOS; notification undo is a no-op; a rolled-back notification still reaching vacuum is safe (commit record flushed first); RVOOS_DELETE is redo-only with a single emitter.
- Latch order has no cycle; same-chain races closed by the stamp check under a write latch; thread_local sink and shared maps safe; A' snapshot-safe for registered snapshots.
- 32-byte header layout consistent; tail-first link stamps correct; reclaimer loops bounded; error/unfix paths sound.
- HA: no replication records needed for OOS deletes (RVREPL_OOS_DELETE has no producer at base or head); applier, CDC, flashback tolerate the new records; rcvindex table contiguous 0..143; TDE consistent; applier header initializer matches.

## Shared questions

- Q1 (dropped-file safety without lowering): SAFE. Decisive fact: in SERVER_MODE dropped-file entries are never cleaned up. Restart reruns hold no locks; WAL order protects them.
- Q2: see R4 and R3.

## R1-fix verdict

- b22b31c5: sound with gaps — live-path ordering restored and exemption right; introduces R2, leaves R3 and R4 open, comment wrong (R10). The new test fails at head and passes with the fix; it does not cover a notification-only block, the rebuild, or a restart rerun; mild flake risk (block crossing between filler and notification; 30 s / 60 s waits).
- 38f1a458 (coordinator-only): adds the rebuild floor (closes R3 ordering except the empty-last-page edge); R2 stands and is reachable through the restored header; R4 and R10 unchanged.

## Coverage

| Reviewer | Model | Coverage | Duration |
|---|---|---|---|
| r1fix | opus xhigh | complete | 25 min |
| recovery | opus xhigh | complete | 27 min |
| concurrency | sonnet xhigh | complete (NULL-snapshot reader enumeration open) | 25 min |
| systems-storage | sonnet xhigh | partial (no execution; not every heap_update_logical caller audited for an enclosing sysop) | 24 min |
| ha | sonnet xhigh | complete | 18 min |

Checks run: git rev-parse/diff, sha256, gh-pr-info, read-only greps, one ha probe (`probe_rvfun_contiguity.py`, exit 0). No build, ctest, or runtime checks.

Budget: best effort, no cap; 5 agents, no retries; subagent tokens ≈ 2.33M (r1fix 363,877; recovery 469,873; concurrency 533,303; systems-storage 555,419; ha 409,826). Coordinator usage unmeasured.

## Resolution after the review (lead session, 2026-11-06)

Executed checks and fixes on top of `3e8072f56`, pushed to the PR as `6ac2d7de6`, `9406a0f71`, `2e32517bb`:

| Item | Result | Evidence |
|---|---|---|
| R1 | Fixed (`6ac2d7de6`): a notification no longer lowers the block's oldest; the debug range check accepts an older notification. | New test `NotifyOlderThanBlockOldestKeepsBlockOrderAndDrains` fails without the fix (block oldest 11720 lowered to 9256) and passes with it. |
| R2 | Confirmed and fixed (`9406a0f71`): the `vacuum_data_entry` constructor no longer asserts oldest <= newest. | New test `NotificationOnlyBlockIsProducedAndVacuumed` aborts on that assert when it is restored, and passes without it. |
| R3 | Fixed (`9406a0f71`): the rebuild floor is the oldest of the last entry in vacuum data, found by walking the pages (covers the empty-last-page edge). | Exercised by the restart in `test_oos_server_crash_recovery`; 5 server crash/restart rounds after OOS UPDATE commits restarted cleanly and drained to the live record count. |
| R4 | Confirmed and fixed (`9406a0f71`): a notification appended while `!LOG_ISRESTARTED()` keeps only the link and the block flag. | New `test_oos_server_crash_recovery` (stop after 2 of 4 drop postpones, restart): without the fix the restart aborts at `log_append.cpp:1372` (`MVCCID_IS_VALID (log_Gl.hdr.oldest_visible_mvccid)`); with it, vacuum reclaims exactly the dropped chains. |
| R5 | Fixed (`9406a0f71`): `oos_rv_reclaim_on_postpone` wraps the reclaim in `pgbuf_force_latch_wait`. | Not tested (needs a contended latch from another thread); `test_oos_server` 38/38 shows no hang. |
| R9, R10 | Fixed (`9406a0f71`). | Source. |
| cppcheck | Fixed (`2e32517bb`): dump arguments spelled out. | cppcheck not available locally. |
| R6 | Fixed (`b6bcc09c6`, first committed as `6a8d16da7`): the notification consumer fail-stops on every error but a shutdown interrupt; the redundant undo-data copy is gone and a successful OOS file lookup no longer reads a stale `er_errid ()`. | New test `NotifyConsumerFailStopsOnAHeapWithoutAnOosFileDespiteAStaleError` returns `ER_INTERRUPTED` without a fail-stop before the fix and passes with it. |
| R7 | Split to [CBRD-27981](https://jira.cubrid.org/browse/CBRD-27981). | [jira-drafts/CBRD-27981-null-snapshot-reader-link-stamp.md](../jira-drafts/CBRD-27981-null-snapshot-reader-link-stamp.md) |
| R8 | Recorded without a code change as ADR-0008 consequence 8 (2026-11-06). Line references still hold at `8e139f4db`. | ADR-0008 consequence 8 |
| P-1 | Split to [CBRD-28012](https://jira.cubrid.org/browse/CBRD-28012) (2026-11-10); the path is unchanged at `8e139f4db`. | [jira-drafts/CBRD-28012-eager-oos-heap-header-latch-order.md](../jira-drafts/CBRD-28012-eager-oos-heap-header-latch-order.md) |
| P-2 | Split to [CBRD-27982](https://jira.cubrid.org/browse/CBRD-27982). | [jira-drafts/CBRD-27982-reused-heap-vfid-notification-skip.md](../jira-drafts/CBRD-27982-reused-heap-vfid-notification-skip.md) |

Debug OOS ctest: 52/52 at `2e32517bb` (two tests over their 60 s limit under load average 100–195 passed when run directly: `test_oos_identity_stamp` 33/33, `test_oos_server` 38/38). gha-ci passed at `3e8072f56` (run 42169072318).
