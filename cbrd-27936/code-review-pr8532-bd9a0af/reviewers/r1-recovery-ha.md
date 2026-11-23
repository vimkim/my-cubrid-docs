# R1 Recovery + HA review: CUBRID/cubrid PR #8532 (head bd9a0afc7b)

Coverage: **complete** for assigned scope (source-only; no execution available). Budget: ~45 tool calls, within allowance.

## Pinned identity

- Checkout `/home/vimkim/gh/cb/CBRD-27936`, `git rev-parse HEAD` = `bd9a0afc7bb84aee33a5947c9b9c56ca8eabd9b8` (verified), clean.
- `gh-pr-info`: PR 8532, OPEN, head `CBRD-27936-free-saved-space-after-commit`, base `develop`, headRefOid bd9a0afc7bb8.
- Comparison base 505c07dde1; patch `/home/vimkim/temp/cubrid-code-review/pr8532-bd9a0af/evidence/pr8532.patch` (one hunk set in `log_commit_local`).
- All `file:line` below are at bd9a0afc7b.

## Inspected paths

- `src/transaction/log_manager.c`: `log_commit_local` 5377-5487, `log_abort_local` 5503-5560, `log_commit` 5578-5665, `log_complete` 5879-5960, `log_complete_for_2pc` 5984-6230, `log_append_repl_info_and_commit_log` 4828-4845, `log_append_donetime_internal` 4859-4884, `log_change_tran_as_completed` 4903-4950, `log_append_commit_log` 4962-4975.
- `src/transaction/log_append.cpp`: `prior_lsa_next_record_internal` 1406-1600.
- `src/transaction/log_page_buffer.c`: `logpb_append_prior_lsa_list` 3114-3148, `logpb_prior_lsa_append_all_list` 3179-3200, `logpb_flush_all_append_pages` 3311-3900 (two-step, first-page-last, EOF marker, nxio update), `logpb_flush_pages_direct` 4043, `logpb_flush_pages` 4076-4180, `logpb_flush_log_for_wal` 4253, `logpb_need_wal` 11964, `logpb_checkpoint_trans` 7248-7292, checkpoint snapshot under `prior_lsa_mutex` 7504-7522.
- `src/storage/page_buffer.c`: victim WAL skip 4602, `pgbuf_bcb_flush_with_wal` 11596-11734 (WAL at 11709 before `dwb_add_page` 11734), write-latch owner-only flush 11618-11638.
- `src/storage/slotted_page.c`: `spage_free_saved_spaces` 393-470, `spage_save_space` 488-650, `spage_get_saved_spaces` 703-760, `spage_has_enough_total_space` 4611-4640.
- `src/transaction/log_recovery.c`: `log_rv_analysis_run_postpone` 1111-1185, `log_rv_analysis_complete` 1534-1600, `log_rv_analysis_end_checkpoint` 1855-1990 (checkpoint state load 1955-1962), `log_recovery_finish_postpone` 4466-4510, `log_recovery_undo` 4710-4760, 2PC recovery call 918-927.
- `src/transaction/log_tran_table.c`: `logtb_is_active` 3305-3340, undo-tdes mapper (state filter at ~4674), `logtb_clear_tdes` 1643.
- `src/transaction/log_2pc.c`: callers 600, 760, 2585; `log_2pc_append_decision` 1929-1965; `log_2pc_commit` dispatch 880-940; `log_2pc_recovery` 2663-2720.
- `CMakeLists.txt:617-619`, `build.sh:40` (CCI_XA on by default).
- Formal model reference (not run): `/home/vimkim/.claude/skills/cubrid-verify-heap-slot-undo/SKILL.md` finding 2 `commit-window-saved-space`.

## Checked invariants and safety facts

### SF1 — Reuse LSA > commit LSA (ordering at append time). Level 3.

1. U's commit record LSA C is assigned in `prior_lsa_next_record_internal` under `prior_lsa_mutex` (log_append.cpp:1419-1423 lock + load, 1560 store, 1566-1575 list link, 1580-1582 unlock). HA path holds the mutex across repl-info + commit (log_manager.c:4839-4844).
2. The release happens after that call returns (log_manager.c:5427/5431 then 5437-5441).
3. The release is visible to another transaction T only through the per-page `SPAGE_SAVE_HEAD` (`head->mutex` lock/unlock in `spage_free_saved_spaces`, slotted_page.c:418-468; T reads it under the same mutex via `spage_Saving_hashmap.find`, slotted_page.c:733-751; erase is done under the locked head, 433). So T's space decision happens after C is assigned.
4. T's log record for the operation that uses the bytes is appended after that decision, through a fresh `prior_lsa_mutex` acquisition. `log_Prior_lsa` is monotonic under the mutex, so T's LSA > C. The prior list is linked in LSA order under the same mutex (log_append.cpp:1563-1575).

No mutex nesting is added: the release runs after `prior_lsa_mutex` is dropped (4844 / inside `prior_lsa_next_record`), so no new lock order.

### SF2 — Durable log is an LSA prefix. Level 3.

- Prior list drains to log pages in list order (log_page_buffer.c:3123-3146), so page content follows LSA order.
- `logpb_flush_all_append_pages` writes all later pages first and the `nxio_lsa` page (holding the previous EOF) last, after fsync (comment 3436-3462, step code 3635-3690 and 3740-3770). A partially appended record is replaced with `LOG_END_OF_LOG` in a copy before writing (3486-3520). `nxio_lsa` advances only after sync (3874-3894).
- Restart analysis stops at `LOG_END_OF_LOG` (log_recovery.c:2502, 2842-3060).
- Therefore, if any record with LSA X is durable and readable by analysis, every record with LSA < X is durable.

### SF3 — WAL: a data page cannot reach disk ahead of its log. Level 2-3.

- `pgbuf_bcb_flush_with_wal` calls `logpb_flush_log_for_wal (page LSA)` before `dwb_add_page` (page_buffer.c:11709, 11734); victim selection skips pages whose LSA needs WAL (4602-4615, 4683). `logpb_need_wal` compares against `nxio_lsa` (log_page_buffer.c:11964-11977).
- A write-latched page is flushed only by its latch owner (page_buffer.c:11618-11638), so a page with T's change but an older page LSA is not written by another thread.
- Combining SF1-SF3: any durable trace of T's reuse (log record or data page) implies C is durable.

### SF4 — Restart undo set. Level 2-3.

- Only `TRAN_UNACTIVE_UNILATERALLY_ABORTED` / `TRAN_UNACTIVE_ABORTED` tdes with non-NULL `undo_nxlsa` are undone (log_recovery.c:4752-4758; mapper filter log_tran_table.c ~4674).
- A durable `LOG_COMMIT` removes U in analysis (`log_rv_analysis_complete`, log_recovery.c:1590-1598).
- Saved space is memory-only and ignored during crash recovery (`spage_save_space` 504-507, `spage_get_saved_spaces` 717-726, `logtb_is_active` returns false before restart 3312-3315).

### SF5 — Checkpoint snapshot during `TRAN_UNACTIVE_WILL_COMMIT`. Level 3.

- Snapshot runs under `prior_lsa_mutex` (log_page_buffer.c:7504-7522). `logpb_checkpoint_trans` skips a tdes once `commit_abort_lsa` is set (7256); that field is set under the same mutex when C is assigned (log_append.cpp:1543-1547).
- So a checkpoint either (a) precedes C and records U as ACTIVE or WILL_COMMIT, or (b) follows C and omits U; in (b) END_CHKPT LSA > C, so a durable checkpoint implies durable C.
- Case (a) with WILL_COMMIT: analysis loads state WILL_COMMIT (log_recovery.c:1955-1962, only ACTIVE/ABORTED become UNILATERALLY_ABORTED). `log_recovery_finish_postpone` commits it (4479-4508). It is never in the undo set (SF4), so U never needs its bytes. `undo_nxlsa` being NULL (5400) or not (window 5396-5400) does not matter because WILL_COMMIT is never undone.
- Case (a) with ACTIVE: U is a loser only if C is not durable; then by SF1-SF3 no reuse is durable.
- Note: the base bug needed no checkpoint snapshot inside the WILL_COMMIT window; a snapshot there makes restart commit U anyway.

## Assignment answers

### 1. Recovery

Crash-point table for a no-postpone U (local branch, new order):

| Crash point | Durable state | Restart outcome | Needs U's bytes? |
|---|---|---|---|
| Before C assigned | U's records ≤ tail; no reuse (not released) | U loser, undo | Yes; reservation never released, no reuse exists |
| After C assigned, before release | Prefix ≤ some X; no reuse | If C durable: U committed. Else loser, undo | Only if C not durable; no reuse exists |
| After release, T reused, T's record R (LSA > C) | Prefix ≤ X | If X ≥ R: C durable → U committed. If X < R: R not durable, T's page change not on disk (WAL) → bytes free for U's undo | Only when R not durable, when bytes are free |
| T committed (sync/group commit) | T's commit flush forces prefix ≥ T commit > C | U committed | No |
| T committed (async) | Prefix arbitrary | Same as previous two rows | Same |

- Reverse-LSA undo of losers T and U is **not** needed for safety: "T's reuse durable but T loser, U loser" cannot occur because a durable R forces C durable (SF2). The PR body's sentence "T의 commit이 디스크에 없으면 T도 loser다 … T가 먼저 되돌려져" describes an unreachable case (see C2).
- `log_append_commit_log` allocation failure (log_manager.c:4870-4875, `/* FIXME */ return`): no commit record and `commit_lsa` stays NULL; `log_change_tran_as_completed` → `logpb_flush_pages` takes the direct-flush path for NULL LSA (log_page_buffer.c:4094-4101; debug asserts at 4092). The release still happens. Base also released without a commit record (earlier). **Not worse than base.** Pre-existing: a "committed" transaction without a commit record becomes a loser at restart. PR Remarks already lists this.
- Point-in-time media recovery (`log_rv_analysis_complete` with `stop_at`, log_recovery.c:1556-1585): the log is reset at the first commit/abort record (in LSA order) whose `at_time` exceeds `stop_at`. That also keeps an LSA prefix, so SF1+SF2 still apply. The fix also closes the same window for PITR, which in base could keep T's reuse (LSA < C) and cut U's C.

### 2. 2PC (`is_local_tran == false`)

Callers with `false`:

| Caller | Role | Decision before call | Build |
|---|---|---|---|
| `log_2pc_commit_second_phase` (log_2pc.c:760) | coordinator (`LOG_2PC_EXECUTE_FULL`, non-CCI_XA) or XA RM participant (`LOG_2PC_EXECUTE_COMMIT_DECISION`, log_2pc.c:924/935) | `log_2pc_append_decision (LOG_2PC_COMMIT_DECISION)` at log_2pc.c:750 assigns D and calls `logpb_flush_pages (&D)` (log_2pc.c:1941-1956) | both |
| `log_2pc_recovery_commit_decision` (log_2pc.c:2585) | restart, decision read from log | D durable by definition; tdes rebuilt by `logtb_clear_tdes` and no save during recovery → `first_save_entry == NULL` | **only `#ifndef CCI_XA`** (log_2pc.c:2698-2702); default `build.sh:40 support_xa="true"` → `CMakeLists.txt:617-619 -DCCI_XA`, so not reached in default builds |

- "Before the fix this path already released after the decision" — **confirmed**. Base released at the same point for both branches: after `log_tran_do_postpone`, inside `!LSA_ISNULL (tail_lsa)`, which is after D was appended by the caller. The new 2PC branch only moves the release past `log_cleanup_modified_class_list` (no page or space effect). 2PC behavior unchanged.
- `log_complete_for_2pc` (5984-6230) appends the final commit/inform records and unlocks; it never reads saved space, and `first_save_entry` is already NULL.
- Comment accuracy (C1): "The commit decision is already on disk: log_2pc_append_decision flushed it" is not literally true with `log_async_commit=yes`: `logpb_flush_pages` sets `need_wait = false` and returns (log_page_buffer.c:4113, 4133, 4149-4152). It is also false when D's prior node allocation fails (log_2pc.c:1934-1938). Safety still holds by SF1+SF2: any reuse has LSA > D. If D is durable, analysis puts U in `TRAN_UNACTIVE_2PC_COMMIT_DECISION`, which is not in the undo set. If D is not durable, no reuse is durable. Not a defect; wording only.
- Pre-existing (unchanged, PR notes it): a prepared participant or decision-state loose end has no reservation after restart (memory-only), so a later abort undo can find no room.

### 3. All callers of `log_commit_local`

Found by `grep -rn "log_commit_local\b" src`:

| Caller | `is_local_tran` | Behavior change |
|---|---|---|
| `log_commit` (log_manager.c:5647), used by ordinary commits, the HA applier on the slave, and a prepared non-coordinator participant (`!log_2pc_clear_and_is_tran_distributed`) | true | Release moves from before C to after C, before unlock and flush. This is the intended fix. No other state differs: `trid` and tran index are unchanged until `log_complete` (assert at slotted_page.c:409 still holds). |
| CCI_XA DBLink coordinator `log_2pc_commit_first_phase` (log_2pc.c:600) followed by `log_complete (…, LOG_ALREADY_WROTE_EOT_LOG)` | true | Same as the row above. Improvement. |
| `log_2pc_commit_second_phase` (log_2pc.c:760) | false | None (see §2) |
| `log_2pc_recovery_commit_decision` (log_2pc.c:2585) | false | None; `first_save_entry` is NULL; not compiled into the switch under CCI_XA |

- Restart finishing of committed-with-postpone / WILL_COMMIT uses `log_recovery_finish_postpone` → `log_do_postpone` + `log_complete (LOG_NEED_TO_WRITE_EOT_LOG)` (log_recovery.c:4479-4508). It does not call `log_commit_local`, and no saved space exists during recovery.
- `log_complete` (5926) and `log_complete_for_2pc` (6209/6213) append commit records without touching saved space.

### 4. HA

**Not applicable (source-based):**

- Saved space is per-server memory (`spage_Saving_hashmap`), never logged. The change adds, removes, and reorders no log record of U. `log_append_repl_info_and_commit_log` still appends repl info + commit atomically under `prior_lsa_mutex` (4839-4844).
- The only effect on the global log is that T's space-consuming record can no longer precede C. Every new-code execution corresponds to a base execution with a different timing (T arriving slightly earlier sees the reservation in base too), so copylogdb and applylogdb see only log orders that base could already produce.
- CUBRID HA replicates logically (applylogdb replays `LOG_REPLICATION_DATA` on the slave); no physical page or page-server replication exists in this tree (no `page_server` sources), so the slave's page layout and reservations are independent.
- The `LOG_CHECK_LOG_APPLIER` path (applier transactions on the slave) uses `log_append_commit_log` and gets the same fix locally.
- Commit acknowledgment and flush semantics are unchanged: `log_change_tran_as_completed` still flushes after unlock (5449), and no flush is added.

### 5. Abort path and `tail_lsa == NULL`

- `log_abort_local`: `log_rollback` (5518) appends a CLR for each undone record before `spage_free_saved_spaces` (5524-5528). The PR claim holds.
- After a crash between release and `LOG_ABORT`: any reuse R has LSA > the last CLR, so a durable R implies all CLRs are durable. The final CLR's undo-next is NULL, so U enters the "aborted with NULL undo_nxlsa → log_complete" path (log_recovery.c:4752-4758) and does nothing. If R is not durable, the bytes are free.
- Partial-CLR durability: only the not-yet-compensated records remain, and the bytes are free because no reuse is durable.
- `tail_lsa == NULL` (5463-5482 commit, 5538-5552 abort): no log records → nothing to undo at restart → release is safe. Unchanged.

## SHARED CHALLENGE Q1 — answer

**No.** I found no feasible schedule under the new order in which a durable log record (or flushed data page) that uses U's released bytes exists while U's commit record does not. I also found none in which restart undoes any part of U after those bytes were reused.

Safety facts:

1. **Ordering**: release follows C's LSA assignment under `prior_lsa_mutex` (log_append.cpp:1419-1582; log_manager.c:5427/5431 → 5437-5441). T sees the release only through `head->mutex` (slotted_page.c:418-468, 733-751). T's record therefore gets a later LSA. Prior list order equals LSA order.
2. **Prefix durability**: drain in list order, first page last, EOF marker, `nxio_lsa` after fsync (log_page_buffer.c:3123-3146, 3436-3520, 3740-3894). Analysis stops at EOF (log_recovery.c:2502).
3. **WAL**: data page flush forces log through the page LSA (page_buffer.c:11709 before 11734; 4602-4615; log_page_buffer.c:4253-4270, 11964-11977).
4. **Undo set**: only UNILATERALLY_ABORTED/ABORTED with non-NULL `undo_nxlsa` (log_recovery.c:4752-4758). Durable C, durable END_CHKPT with WILL_COMMIT, or durable 2PC COMMIT_DECISION each exclude U.

Mode coverage:

- **Async commit**: no wait (log_page_buffer.c:4133-4152), but facts 2-3 do not depend on waiting.
- **Group commit**: waits on `nxio_lsa` (4160-4178), same prefix.
- **HA**: same records and order constraint (§4).
- **2PC**: D < reuse, same argument (§2).
- **Checkpoints**: snapshot under the mutex, `commit_abort_lsa` exclusion (SF5).
- **PITR**: truncation keeps a prefix.

Limits:

- Source-level argument only (level 3). Relies on general invariants that this PR does not touch: every space-consuming heap/catalog change is logged with a page-LSA update while write-latched, and log pages are torn-write detected.
- Runtime confirmation is unproven here. The PR body reports gdb+SIGKILL reproduction 3/3 debug and 1/1 release pass on its own scripts (not replayed by me).

## Pre-existing concerns: is the change worse?

- `logtb_complete_mvcc` before the commit record (5394): the window from MVCC completion to C is unchanged in length because the commit append position did not move. The release moved out of that window, so the window is marginally shorter. **Not worse.**
- `spage_has_enough_total_space` honors reservations only for active transactions (slotted_page.c:4624-4634). U's reservation now lives longer. Active consumers respect it for longer; non-active consumers (aborting txns, commit-postpone executors, recovery) ignore it identically before and after. **Not worse.**
- Post-restart 2PC prepared/decision loose ends have no reservation: unchanged.

## Candidate findings

### R1-C1 — P4 (comment accuracy, not a defect)

- **Statement**: the new 2PC-branch comment says the commit decision "is already on disk: log_2pc_append_decision flushed it". With `log_async_commit=yes`, `logpb_flush_pages` returns without waiting. On prior-node allocation failure, no decision record is written.
- **Location**: log_manager.c:5453-5455 (changed hunk), symbol `log_commit_local`. Evidence: log_page_buffer.c:4113, 4133, 4149-4152; log_2pc.c:1934-1938, 1941-1956.
- **Preconditions**: 2PC commit (non-CCI_XA coordinator or XA RM COMMIT_DECISION) with `log_async_commit=yes`.
- **Invariant**: none violated. Safety holds by LSA ordering (D < reuse) plus prefix durability, the same reason the local branch is safe.
- **Introduced by change**: yes, the comment is new. Behavior is unchanged vs base.
- **Impact**: misleading rationale for future maintainers. **Fix**: phrase the 2PC rationale as "the commit decision record precedes, in LSA order, any log that reuses the space, so the space is reused only by logs that cannot be durable without the decision record."
- **Evidence level**: 2 (pinned source). No execution needed. Coordinator replay: read the cited lines.

### R1-C2 — P4 (PR description precision, not code)

- **Statement**: the PR body's "T의 commit이 디스크에 없으면 T도 loser다. undo는 LSA 역순이라 T가 먼저 되돌려져 공간이 빈 뒤 U를 되돌린다" describes an unreachable state. If T's reuse record is durable, C is durable (prefix), so U is not a loser. If the reuse is not durable, T's page change is not on disk (WAL). The real safety fact is prefix durability + WAL, not reverse-LSA undo.
- **Location**: `/home/vimkim/temp/cubrid-code-review/pr8532-bd9a0af/evidence/pr-body.md` (diagram footnote).
- **Fix**: replace with the prefix + WAL argument.
- **Evidence level**: 3 (path argument via SF2/SF3).

No P1-P3 candidates in Recovery/HA scope.

## Cleared risks (with limits)

- Lock-order or deadlock from the new release position: release runs with no `prior_lsa_mutex` held (log_manager.c:4844; log_append.cpp:1580-1582). Level 2.
- Release-time assertion `current->tranid == logtb_find_current_tranid` (slotted_page.c:409): `trid` is unchanged until `log_complete`/`logtb_get_new_tran_id`. Level 2.
- Checkpoint during the commit window: SF5. Level 3.
- Archive retention: `smallest_lsa` excludes U only after `commit_abort_lsa` is set; END_CHKPT > C. Level 2.
- HA log content and order: subset of base executions. Level 3.

## Rejected hypotheses

- H1 "T's record gets LSA < C because LSA is assigned before the space check": rejected. Space is checked under page latch before T's log append; the LSA is taken later under `prior_lsa_mutex` (SF1).
- H2 "log page with T's record written before the page with C": rejected. Two-step flush writes later pages first but stamps EOF in the earlier page until the final step, and analysis stops at EOF (SF2).
- H3 "checkpoint snapshot with WILL_COMMIT and nulled `undo_nxlsa` causes a wrong undo": rejected. WILL_COMMIT is committed at restart, never undone (SF5).
- H4 "2PC behavior changed": rejected (§2).
- H5 "commit-record allocation failure is worse after the change": rejected. Equal to base.

## Unresolved questions / cheapest decisive checks

1. **Runtime confirmation of Q1 (unproven at level 4/5 by me).** Cheapest check: replay the PR's `commit-crash-saved-space-v2.sh` (Jira attachment, sha1 32ee850a) on bd9a0afc7b, plus an async-commit variant (`log_async_commit=yes` with T's commit and a forced `logpb` flush up to T's commit). Expect restart success and U committed.
2. **Formal model.** `python3 /home/vimkim/.claude/skills/cubrid-verify-heap-slot-undo/scripts/check.py --rev bd9a0afc7b` from the checkout should report that known finding `commit-window-saved-space` no longer applies (shape `commit_frees_saved=after_commit_record`). Caveat: that skill targets develop without OOS, and develop now has OOS (`src/storage/oos_file.cpp`), so it may report OUT OF SYNC. The OOS skill `cubrid-verify-vacuum-slot-undo` does not model `commit_frees_saved`. Not run, per the "read-only, no execution" instruction.
3. **Unrelated pre-existing note (not chased):** under `log_async_commit=yes`, 2PC prepare and decision records are not waited on before the protocol proceeds (`log_2pc_append_decision` uses `logpb_flush_pages`). This could weaken XA durability. It is outside this PR; flagged for a separate look only.

## Commands run

All read-only, from `/home/vimkim/gh/cb/CBRD-27936`: `git rev-parse HEAD`, `git status`, `gh-pr-info`, `grep -n`/`sed -n` over the files listed above, plus `grep` over `CMakeLists.txt`/`build.sh` and the verification skill's SKILL.md and check.py. No builds, servers, models, or agents.
