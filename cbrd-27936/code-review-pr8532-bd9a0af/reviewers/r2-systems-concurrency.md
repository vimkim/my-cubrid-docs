# R2 report: Systems + Concurrency + Storage/performance (PR #8532, head bd9a0af)

Coverage status: **complete** for the assigned scope (source-only; no runtime available, so no level 4/5 evidence).
Budget: about 55 tool calls, inside the soft bound. No source was modified. Only this file was written.

## 0. Pinned identity and scope

- Checkout `/home/vimkim/gh/cb/CBRD-27936`, `git rev-parse HEAD` = `bd9a0afc7bb84aee33a5947c9b9c56ca8eabd9b8` (pinned value, clean tree).
- `git diff 505c07dde1 bd9a0afc7b` is one file, `src/transaction/log_manager.c` (+17/-9). It is byte-identical to `evidence/pr8532.patch` (checked with `diff`).
- `gh-pr-info`: PR 8532, base `develop`, head `CBRD-27936-free-saved-space-after-commit`, OPEN. `AGENTS.user.md` absent (skipped). `/home/vimkim/my-cubrid/CUBRID.md` readable.
- Inspected: `log_manager.c` (log_commit_local 5377-5483, log_abort_local, log_commit, log_complete, append helpers, log_tran_do_postpone 8405), `slotted_page.c` (save/free/get/has_enough, 380-770, 4611), `log_tran_table.c` (all `first_save_entry` sites), `log_2pc.c` (commit paths, `log_2pc_append_decision`), `log_append.cpp` (`prior_lsa_next_record_internal`), `log_page_buffer.c` (flush, WAL, `logpb_start_append`), `log_recovery.c` (analysis, end of log, checkpoint tdes), `heap_file.c` / `bestspace.cpp` / `locator_sr.c` (consumers of saved-space views).

## 1. Invariants checked and safety facts

I1. The release of U's saved space must not happen before U's commit record C has an LSA (and is in the prior list).
- SF1 (level 3). New site `log_manager.c:5437-5441` follows `log_append_repl_info_and_commit_log` / `log_append_commit_log` (5427/5431) in the same thread. Both append to the prior list under `prior_lsa_mutex` (`log_append.cpp:1406-1612`, mutex at 1419-1421 or held by the `_with_lock` caller `log_manager.c:4839-4844`). So C's LSA is assigned and C is linked before the release.
- SF2 (level 3). A consumer T can see the freed bytes only through U's `head->mutex` unlock (or hash erase) in `spage_free_saved_spaces` (`slotted_page.c:393-464`). T reads under the same mutex or the lock-free hash (`spage_get_saved_spaces`, 703-770). That gives release/acquire from U's earlier C append to T's later space check. T's page change and its log record are in the same page-latch hold, so T's LSA is greater than C's LSA (assigned under `prior_lsa_mutex`).
- SF3 (level 3). The log is persisted and replayed as a prefix, so "T durable implies C durable":
  - Prior list order equals LSA order. Nodes are linked inside the mutex, and `logpb_append_prior_lsa_list` drains in order (`log_page_buffer.c:~3110-3140`). `logpb_start_append` is fatal if `back_lsa != prev_lsa` (`log_page_buffer.c:4310`).
  - `nxio_lsa` is a single watermark set only after write + fsync (`log_page_buffer.c:~3840-3894`). `logpb_need_wal(lsa)` is `nxio_lsa <= lsa` (11964-11976). Group commit and async commit wait on or request the same watermark (`logpb_flush_pages`, 4072-4140). Data-page WAL uses the same watermark (`logpb_flush_log_for_wal`, 4253).
  - Recovery walks the `forw_lsa` chain and stops at a corrupted log page without advancing (`log_recovery.c:2787-2800`, 2950-2954). A partially flushed tail record gets an end-of-log placeholder (`log_page_buffer.c:~3840-3900`, `partial_append`).
  - The `logpb_flush_all_append_pages` multi-page write order (disk-level torn write) was not traced in full. It is the same prefix assumption that already protects every commit and the existing "unlock log before releasing locks" rule (`log_manager.c:5419-5423`).

I2. Lock/latch legality of the call site.
- SF4 (level 3). `spage_free_saved_spaces` takes only a lock-free-hash epoch (`start_tran`/`end_tran`), `head->mutex` and (for the last entry) `erase_locked`. It takes no page latch, no `prior_lsa_mutex`, no `LOG_CS`, no csect. `head->mutex` is a leaf. In `spage_save_space` and `spage_get_saved_spaces` it covers only list/counter edits and `malloc`, never a wait for a latch, a log mutex or I/O. So no lock-order or deadlock implication.
- At the new local site no log mutex is held: the repl variant unlocks `prior_lsa_mutex` before returning (`log_manager.c:4844`). `log_commit_local` is not called under a page latch or `LOG_CS`. The old site had the same context.

I3. Ownership of `tdes->first_save_entry`.
- SF5 (level 2-3). The list is built only in `spage_save_space` (the 2 sites: `slotted_page.c:566`, `633`). It is guarded by `space < 0 || !logtb_is_active()` (`slotted_page.c:518`). `logtb_is_active` is `state == TRAN_ACTIVE` (`log_impl.h:143`). Once `log_commit_local` sets `TRAN_UNACTIVE_WILL_COMMIT` (5396), no entry can be added. The 2PC code reverts to a 2PC state, which is not active either. So the list that the old site freed is the same list the new site frees. The head is touched only by the owner thread (one thread per transaction, per the code comment at `slotted_page.c:~409`).
- Every branch of `log_commit_local` that is reached with `first_save_entry != NULL` frees and NULLs it: local (5437), 2PC (5456), `tail_lsa == NULL` (5472, unchanged). No `return` sits between the old and new points. `log_abort_local` is unchanged (5524/5542).
- Other writers of the pointer (all reset-only, none can leak a live list after the move):
  - `logtb_set_tdes` (`log_tran_table.c:932`), `logtb_clear_tdes` (1643), `logtb_initialize_tdes` (1734): reset to NULL without freeing.
  - `logtb_descriptors_start_scan` (5950): prints the pointer value, no dereference.
  - `log_tdes::copy_to` (6768): shallow copy.
- In the commit path, `logtb_clear_tdes` is reached only via `log_complete -> logtb_get_new_tran_id`, after `log_commit_local` has freed in every branch (`log_commit`, `log_manager.c:~5647`). So no leak and no double free from the move.
- Restart: `log_2pc_recovery_commit_decision` (`log_2pc.c:2576-2593`) calls `log_commit_local(.., false, false)` with `first_save_entry == NULL` (`logtb_clear_tdes` at `log_recovery.c:1957`; `spage_save_space` returns early in crash recovery; the hash is fresh after `spage_boot`). The `!= NULL` guard skips it.
- Only residual leak: `spage_free_saved_spaces` returns early if `erase_locked` fails (`slotted_page.c:~431-437`). That is old behavior, and the PR does not change it.

I4. The work between the old and new release points does not depend on the release.
- SF6 (level 2-3). `log_cleanup_modified_class_list` (`log_manager.c:5341-5356`; per-class callback 5313) only does `partition_decache_class`, `xcache_remove_by_oid`, `fpcache_remove_by_class`, `locator_drop_transient_class_name_entries` (early return if `num_transient_classnames <= 0`, `locator_sr.c:~1366`) and `tx_transient_class_registry::clear`. These are in-memory caches and name tables. They fix no heap page and call no `spage_*` (`locator_drop_class_name_entry` has no `heap_/spage_/pgbuf_/log_append` calls: grep empty). `log_append_commit_log` / `log_append_repl_info_and_commit_log` only allocate prior nodes and link them (optionally `log_append_supplemental_info`). So U cannot fail to fit its own write there; U writes no heap page there at all.
- SF7 (level 3). Even if U did write, `spage_has_enough_total_space` (`slotted_page.c:4611-4638`) subtracts saved space only when `logtb_is_active(current tran)`; otherwise `total_saved = 0`, the whole page free space counts. For an active transaction it subtracts the total including its own entry (`spage_get_total_saved_spaces` -> `spage_get_saved_spaces`, which returns `total_saved`, and `my_saved_space` is not removed). U in `TRAN_UNACTIVE_WILL_COMMIT` or `COMMITTED_WITH_POSTPONE` sees no reservation at all, its own included. The new window does not make U compete with its own reservation. (`spage_get_free_space` / `spage_max_space_for_new_record`, 902/959, subtract unconditionally. Their heap consumers are `heap_file.c:5496, 24040` and `bestspace.cpp`. Neither runs between 5413 and 5441.)
- SF8 (level 3). `log_tran_do_postpone` (5411; function at 8405) runs before both release points and in the same state (WILL_COMMIT or COMMITTED_WITH_POSTPONE). The postpone actions run with total_saved = 0 and add no entries (`slotted_page.c:518`). The move cannot change what they see. For a postpone transaction, `log_append_commit_postpone` (the commit-with-postpone record) already is the commit point, so the old early release was safe for it. The PR only lengthens the window for it.

I5. Abort and no-log branches.
- SF9 (level 2). `log_abort_local` and the `tail_lsa == NULL` branch are untouched by the diff (the hunks are lines 5410-5465 only). In the abort path the release (5524) follows `log_rollback` (all compensation records appended), so the "consumer LSA greater than every CLR" argument holds as before. The `tail_lsa == NULL` branch can only hold entries in the no-logging case, where no undo exists.

## 2. Concurrency: effect of the longer reservation window

The only behavior change is that other transactions see less space on U's pages for about `t(cleanup) + t(commit-log append)` longer. Source-based effects:
- Heap insert and update paths: `spage_update`/`spage_insert` return no-fit and the heap relocates the record (`heap_update_home` family) or picks another page through bestspace. `spage_max_space_for_new_record` checks in bestspace re-measure (`bestspace.cpp:703-717`, `980`, `1056`).
- `ER_SP_NOSPACE_IN_PAGE` (`heap_file.c:24040-24042`) applies only to a caller-supplied `home_hint_p`. The only supplier is `heap_alloc_new_page` (`locator_sr.c:16030-16084`, a freshly formatted page). No saved entry can exist there. So no error propagates because of the window (level 2).
- Best-space cache: `heap_add_bestpage` records free space with `spage_get_free_space_without_saving` (`heap_file.c:4964`). It advertises U's reserved bytes. A searcher that fixes the page during the reservation writes the lower measured value back (`bestspace.cpp:703-717`). `spage_free_saved_spaces` does not notify bestspace, so the entry can stay low until a later delete promotes the tier (`heap_file.c:4970-4977`). This exists for the whole U lifetime today. The PR adds only a small extra share of exposure. It is a space-efficiency effect, not a correctness one (level 2-3).
- No assertion keys on "committing transaction still has a saved entry". The debug asserts I read (`slotted_page.c:757-761`, `spage_check` 4448-4475, line 1677) are about sums and about the current thread's own state.
- Vacuum workers: `spage_save_space` returns early for them (`slotted_page.c:508-514`). They free bytes (vacuum slot removal), do not take new bytes, and are not the reservation owners. The longer window only makes them see slightly less free space. The slot/undo interplay of vacuum sysops is not changed by this diff and belongs to the recovery review and `cubrid-verify-vacuum-slot-undo`.
- System operations of other transactions on the same page are active transactions and see the entry. The result is the same less-space view and relocation.
- Lock order: free precedes `lock_unlock_all` before and after the PR (before: free 5413-region then unlock; after: 5437 then 5445). A transaction waiting on U's row locks therefore resumes only after the release in both versions. The new site sits at the same "after C appended" barrier as the lock release (`log_manager.c:5419-5423`), which is the existing safety design for slot reuse.

## 3. Storage and performance (all model/source-based, nothing measured)

- Window length added: `t(log_cleanup_modified_class_list)` + `t(log_append_commit_log)` (+ `t(log_append_repl_info)` on an HA master with replication). The release call itself costs the same as before and sits at the same place relative to `lock_unlock_all` and the flush. The flush wait (the dominant commit latency) stays outside the window (`log_change_tran_as_completed`, 5449, after the release).
- Typical DML transaction: cleanup is empty (no transient classes, `locator_sr.c:~1366` early return), so the added time is one prior-node allocation plus `prior_lsa_mutex` (hold time of a few hundred ns to a few µs). Under many concurrent committers the mutex wait is the main term. If the prior list is at the log-memory limit, `prior_lsa_next_record_internal` sleeps 1 ms after unlocking (`log_append.cpp:~1606-1612`), and that sleep now lies inside the window. This is a saturation case.
- DDL transaction: cleanup walks the XASL cache (`xcache_remove_by_oid` -> `xcache_invalidate_entries`, O(entries)), so the window grows by that cost. DDL transactions are rare, so the effect on user pages is small. Not measured.
- HA master: `log_append_repl_info_with_lock` appends all pending replication records under `prior_lsa_mutex` before C (`log_manager.c:4821-4844`). The window grows with the number of unflushed replication items of that transaction (a few µs per item by model). The reservation already lasted the whole transaction, so the relative increase is small.
- Expected cost: window fraction is about `delta / L`, where L is the time from U's shrinking operation to commit. A conflicting writer that lands in the extra window relocates a record (extra page fix per read until vacuum or update, one extra log record) or takes a different page, or allocates a page if bestspace has no candidate. This is the same cost class the author names ("other page is used"). I cannot give a number without a benchmark. The suggested check is a pgbench-like hot-page update/shrink workload with `Num_relocated_recs`, before and after.
- 2PC branch addition: one pointer test in a rarely used branch, zero instructions on the local hot path. The count of release calls per commit is unchanged (one). Code size: five copies of the 4-line block, no runtime effect.

## 4. SHARED CHALLENGE Q1 (answered independently)

**Answer: no, on the stated conditions. Under the new order I found no feasible schedule in which a durable log record consumes U's released bytes while U's commit record is not durable, and none in which restart undoes U after its bytes were reused.** Evidence level 3 (complete source path argument); the disk-torn-write part rests on the engine's prefix assumption and is unproven by execution.

Safety facts (see section 1): SF1-SF3 plus the checks below.

Reference schedule that shows the fix (U has no postpone, A = U's shrinking update at LSA a, bytes b reserved):

1. U: A on page P, `spage_save_space` records b (`slotted_page.c:2118`). T cannot use b while U is active (`slotted_page.c:4628-4633`).
2. U: `log_commit_local`: state WILL_COMMIT, `log_tran_do_postpone` has nothing, C is assigned LSA c and linked under `prior_lsa_mutex` (`log_append.cpp:1406-1612`). Sync: mutex order.
3. U: `spage_free_saved_spaces`: `head->mutex` lock/unlock, entry removed. Sync: head mutex or lock-free hash erase.
4. T (other row on P, active): `find`/mutex sees b free, `spage_update` consumes b under the page latch, then logs at LSA t > c (T's append is after U's step 2 through the happens-before in step 3, and LSA order = `prior_lsa_mutex` order).
5. Crash at any point:
   - Before step 2 or before C is flushed and T not durable: U loser, T not durable (no page with T's change can be flushed, WAL needs the log up to t, which includes c via the single watermark). The page on disk has A without T, so U's undo fits. Undo order is reverse LSA anyway.
   - T durable (its commit or even a data page with T's change, which needs `nxio_lsa > t`, hence `> c`): C durable, recovery analysis marks U committed, no undo of U.
   - T loser but T's log durable: T's op has LSA greater than A (latch order on P), so reverse-LSA undo reverts T before A. U is a loser only if C is not durable, in which case, by the prefix property, nothing after C is durable.
   - A committed system operation of T (not undone at restart) that consumes b: its LSA is also greater than c, so it is durable only if C is.

Per mechanism:
- **Async commit** (`async_commit`, `logpb_flush_pages` 4090-4140): U may return before C is durable, but the log still flushes as a prefix. T's own durability or page flush needs `nxio_lsa > t > c`. No gap is possible.
- **Group commit**: same watermark; waiters compare `nxio_lsa` with their own LSA (`logpb_need_wal`).
- **Checkpoint**: a snapshot taken after `tdes->state = WILL_COMMIT` (5396) carries `undo_nxlsa = NULL` (5398-5401), so U is a winner at restart (`log_recovery.c:1960-1966` copies the state; only ACTIVE/ABORTED become `UNILATERALLY_ABORTED`). A snapshot taken earlier has U as loser candidate, but then recovery scans forward from the checkpoint and finds C if C is durable. Saved space is memory-only and not in the checkpoint.
- **2PC** (`log_2pc.c:734-763`, restart path 2576-2593): the 2PC-branch release runs after `log_2pc_append_decision` has flushed `LOG_2PC_COMMIT_DECISION` (1940-1953). Recovery sets `TRAN_UNACTIVE_2PC_COMMIT_DECISION` (`log_recovery.c:2232`) and `log_2pc_recovery_commit_decision` commits it. The undo phase selects only `UNILATERALLY_ABORTED` / `ABORTED` transactions (`log_recovery.c:4754`, 6807-6810). The dblink path (`log_2pc.c:~600`) calls `log_commit_local(.., true)` and uses the local branch, so it releases after C.
- **HA**: C and the replication items are appended together under `prior_lsa_mutex` (`log_manager.c:4839-4844`) and the release is after the unlock. Replica shipping reads flushed log pages, so ordering is unchanged. HA reviewer owns the rest.
- **Prior-list ordering**: SF3.

Not covered by Q1 (residual, pre-existing, not introduced by the PR): a consumer that does not see U's reservation at all, because it is a non-active transaction (`slotted_page.c:4628`) or because the reservation was lost at restart (2PC prepared transactions). See R2-O1 and R2-O2.

## 5. Candidate findings

**No defect introduced by this PR was found** at evidence levels 2-3. Nothing reproduced (no runtime). Source-only observations follow. None is proposed as blocking.

- **R2-O1 (informational, pre-existing, proposed P3, evidence 2).** The residual hole the author already lists: a non-active consumer (T in postpone or WILL_COMMIT) ignores every reservation (`slotted_page.c:4624-4636`), so it could take U's bytes while U is still active and later reach C ahead of U. The PR does not touch it. Disproof attempt: none made. I did not trace any postpone action's page effect, so this is an open question, not a cleared one. Unresolved: which postpone actions can grow a heap page. Cheapest decisive check: grep the postpone redo functions (`RVHF_*` postpone entries) for `spage_insert`/growing `spage_update`, or add a debug assertion at `slotted_page.c:4628` when a non-active transaction takes bytes on a page with others' saved space.
- **R2-O2 (informational, pre-existing, proposed P3, evidence 2).** Reservations are memory-only; after restart a 2PC-prepared transaction has none, so new transactions may reuse its bytes before the decision arrives. The PR comment correctly says "no saved space" at restart; the consequence for a later abort decision is outside this PR.
- **R2-O3 (hardening suggestion, evidence 2).** If `prior_lsa_alloc_and_copy_data` fails, `log_append_donetime_internal` returns with `commit_lsa` NULL (`log_manager.c:4860-4880`) and the release still runs. The new comment's claim (the log after the release has a larger LSA than the commit log) is false in that out-of-memory case. The old code was equally exposed. The same holds for `log_2pc_append_decision` (`log_2pc.c:1934-1938`). Optional guard: skip the release when `LSA_ISNULL(&commit_lsa)`, or treat it as fatal. Low value.
- **R2-O4 (no action).** The PR removes the stale comment about "files created by this transaction" and cursors. The code never closed cursors there. No correctness effect.

## 6. Cleared risks and rejected hypotheses

- Cleared (level 3): new latch/mutex-order or deadlock risk (SF4).
- Cleared (level 3): U failing its own write because its own reservation counts against it between 5413 and 5441 (SF6, SF7). U does no heap write there and non-active states ignore reservations.
- Cleared (level 3): postpone actions affected (SF8).
- Cleared (level 2-3): leak or double free of `first_save_entry` on error, retain_lock, 2PC, tdes reuse, `logtb_clear_tdes` (SF5).
- Cleared (level 2): assertion or error propagation caused by the longer window (`ER_SP_NOSPACE_IN_PAGE` and debug asserts, section 2).
- Cleared (level 2): the 2PC branch behavior. Old code also released after the decision flush; the new site is just after `log_cleanup_modified_class_list`, a no-heap-write function.
- Rejected: "the release is now under `prior_lsa_mutex`". The repl helper unlocks first (`log_manager.c:4844`).
- Rejected: "T can get a smaller LSA than C because of log-before-physical ordering". A reserver's LSA a < T's LSA t holds by page-latch order on P, and t > c comes from the release being after step 2.
- Rejected: "checkpoint can make U a loser after T is durable". See Q1 checkpoint item.
- Limits of evidence: all source-based. Runtime-only facts (actual window length, torn log write order, relocation counts, `Num_relocated_recs`) are unproven here. The author's runtime evidence (3/3 and 1/1 passes with gdb pause at `log_append_commit_log`) is theirs, not mine, and I did not replay it.

## 7. Unresolved questions and cheapest decisive checks

1. Do any postpone actions grow a heap page (R2-O1)? Source grep of postpone redo functions; debug-only assert as above.
2. Multi-page torn log write order in `logpb_flush_all_append_pages` (only the prefix assumption was used). Recovery reviewer can check `logpb_writev_append_pages` (`log_page_buffer.c:2821`) for page order and the checksum rule at `log_recovery.c:2787`.
3. Quantify the window under a hot-page shrink/update workload on HA master vs. non-HA (`Num_relocated_recs`, commit latency, `prior_lsa_mutex` wait), before/after build. Not run.
4. Cross-check with the existing model `cubrid-verify-heap-slot-undo` (its trigger list names "saved-space release in log_commit_local"). It was not run here. Recommend the recovery reviewer or coordinator run it against this HEAD and read its stated abstraction before relying on it.

## 8. Commands run (read-only)

`git rev-parse HEAD`, `git status --short`, `git diff --stat`, `git diff ... | diff - evidence/pr8532.patch`, `gh-pr-info`, `sed -n`, `grep -n`, `awk` for line numbers. No build, no server, no agent spawned.
