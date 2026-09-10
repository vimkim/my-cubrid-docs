# CBRD-27151 — Bulk file destroy vs. recovery-time re-execution of `file_destroy`

Source tree: `/home/vimkim/gh/cb/review-CBRD-27151-drop-sec`, branch `CBRD-27151-bulk-file-destroy`, HEAD `93f11fb3f`.
All line numbers below are read at `93f11fb3f` unless a commit is named explicitly.

---

## Verdict

**CONFIRMED** as a real correctness hole, with one framing correction and one important
bound the original finding does not mention.

Every link of the claimed chain exists in code. The permanent-file destroy collects the
file's sector list from the *in-memory* header (`src/storage/file_manager.c:4139`), unfixes
the header (`:4158`), and then discards every buffered page of those sectors — **including
the file header page and the ftab pages themselves** — by clearing the dirty flag and
invalidating the BCB with no flush and no log record (`src/storage/page_buffer.c:3487`,
`:3514-3517`, `:3553`). That is a deliberate WAL-invariant violation for those pages. A
checkpoint that runs its buffer-pool scan after the discard will not see those BCBs, so its
redo LSA advances to the checkpoint-start LSA (`src/transaction/log_page_buffer.c:7011`,
`:7025-7030`) and the un-flushed header/ftab updates become unreplayable. Recovery then
*does* re-execute an interrupted permanent destroy: it aborts the interrupted logical
run-postpone sysop and re-runs the `RVFL_DESTROY` postpone
(`src/transaction/log_recovery.c:4361` calls `log_recovery_abort_interrupted_sysop`, `:4370` re-runs `log_do_postpone`,
whose own comment names "file destroy" as the motivating case,
`src/transaction/log_recovery.c` — see quote in §4), and `file_rv_destroy` re-enters
`file_destroy()` (`src/storage/file_manager.c:4280`), which re-reads the on-disk header and
re-collects the VSID list. With a stale on-disk header the retry unreserves a smaller sector
set → **permanent sector leak**; with a header whose on-disk image predates the file's
creation the retry's `OLD_PAGE` fix hits `ptype == PAGE_UNKNOWN`, returns `NULL`
(`src/storage/page_buffer.c:2473-2492`) and `file_rv_destroy` fails on `assert_release`
(`src/storage/file_manager.c:4281-4287`) → **recovery aborts**. No checkpoint exclusion,
latch, or atomic-sysop marker protects the interval; I found none.

**Framing correction / bound the finding misses:** once the destroy's sysop reaches
`LOG_SYSOP_START_POSTPONE`, the sector list *is* already durably recorded — as the
`RVDK_UNRESERVE_SECTORS` postpone records appended by `disk_unreserve_ordered_sectors`
(`src/storage/disk_manager.c:4876`) — and recovery finishes those postpones instead of
re-running `file_destroy` (`log_recovery_finish_sysop_postpone`). So the exposed window is
bounded and small: `[pgbuf_discard_pages_of_sectors() at file_manager.c:4161,
LOG_SYSOP_START_POSTPONE of the run-postpone sysop]`. Both the checkpoint's *completion*
(log header flush, `log_page_buffer.c:7211-7229`) and the crash must land inside that
window.

**Confidence.** High (≈0.9) that the mechanism is real and that the change introduced it —
every step is verified in source, and the old path did not have it. Moderate-to-low (≈0.3)
that it is reachable in practice without a deliberate hook, because the required
coincidence is a millisecond-scale race; and I did **not** reproduce it. The `checkdb`
sector-leak detector that would catch the benign outcome exists
(`disk_map_clone_check_leaks`, `src/storage/disk_manager.c`), which is consistent with the
base commit's claim of clean checkdb runs — those runs would simply not have hit the race.

---

## Evidence

### 1. What exactly does the new path discard, and when?

`file_destroy()` — `src/storage/file_manager.c:4076`. Order for a permanent file
(`is_temp == false`):

| Step | Line | Action |
|---|---|---|
| 1 | `:4105` | `file_tracker_unregister (thread_p, vfid)` — logged (`RVFL_TRACKER_UNREGISTER`, undo/redo) |
| 2 | `:4116` | `page_fhead = pgbuf_fix (…, OLD_PAGE, PGBUF_LATCH_WRITE, UNCONDITIONAL)` |
| 3 | `:4137` | `assert (FILE_IS_TEMPORARY (fhead) \|\| log_check_system_op_is_started (thread_p))` |
| 4 | `:4139` | `file_table_collect_all_vsids (thread_p, page_fhead, &vsid_collector)` — reads the **in-memory** header |
| 5 | `:4158` | `pgbuf_unfix_and_init (thread_p, page_fhead)` |
| 6 | `:4161` | `pgbuf_discard_pages_of_sectors (thread_p, vsid_collector.vsids, vsid_collector.n_vsids)` |
| 7 | `:4228` | `disk_unreserve_ordered_sectors (…, volpurpose, n_vsids, vsids)` |

```c
/* src/storage/file_manager.c:4149-4162 */
  if (!FILE_IS_TEMPORARY (fhead))
    {
      /* bulk destroy: do not fix and deallocate pages one by one - that reads the whole file from disk
       * ... buffered pages are discarded (cleared of dirty status and invalidated) so that no stale content can
       * reach disk after the sectors are reused; pages that are not buffered are not even touched. */
      pgbuf_unfix_and_init (thread_p, page_fhead);

      /* scan the buffer pool once for pages of the destroyed sectors. cost is proportional to the pool size. */
      pgbuf_discard_pages_of_sectors (thread_p, vsid_collector.vsids, vsid_collector.n_vsids);
    }
```

**The header page is inside the discarded set.** `file_table_collect_all_vsids`
(`src/storage/file_manager.c:3948`) collects every VSID of the partial and full sector
tables. `file_create` picks the header VPID as a page inside the *first reserved sector*
(`:3487-3494`: `vfid->fileid = SECTOR_FIRST_PAGEID (vsids_reserved->sectid)`; for
HEAP/BTREE a page inside a reserved sector of the same volume, `:3441-3483`) and then
populates *all* reserved sectors into the partial table (`:3646-3700`, with explicit
`VSID_IS_SECTOR_OF_VPID (&partsect_ftab->vsid, &vpid_fhead)` bookkeeping at `:3663` and
`:3686`). So the header's own sector is in the collected array, and `pgbuf_discard_page` is
invoked for the header VPID like any other page. The unfix at `:4158` is what makes this
possible — `pgbuf_discard_page` requires `fcnt == 0` (`src/storage/page_buffer.c:3504-3511`).
The ftab pages (`fhead->n_page_ftab` of them) are likewise inside the file's own sectors and
are likewise discarded.

The order matters for the claim: the VSID list is collected from the correct in-memory
header **before** the discard, so the *first* execution is always correct. Only a
re-execution reads the on-disk image.

### 2. What does `pgbuf_discard_pages_of_sectors()` do to a dirty BCB?

`src/storage/page_buffer.c:3605` scans the whole pool, filters by sector (`bsearch` over the
sorted VSID array, `:3625-3633`), and routes every candidate to the static helper
`pgbuf_discard_page()` (`:3487`). The helper:

```c
/* src/storage/page_buffer.c:3514-3518 */
  /* discard content: the buffered copy must never reach disk. */
  if (pgbuf_bcb_is_dirty (bufptr))
    {
      pgbuf_bcb_clear_dirty (thread_p, bufptr);
    }
```

```c
/* src/storage/page_buffer.c:3553-3557 */
  (void) pgbuf_invalidate_bcb (thread_p, bufptr);
  /* bufptr->mutex has been released in above function. */

  /* confirm the page is really gone; pgbuf_invalidate_bcb gives up on rare transient states. */
  goto retry;
```

- **No flush ever happens.** `pgbuf_bcb_clear_dirty` is just
  `pgbuf_bcb_update_flags (…, 0, PGBUF_BCB_DIRTY_FLAG)` (`src/storage/page_buffer.c:16132-16136`).
- It *waits* for an in-flight flush (`:3520-3532`, flush-waiter protocol
  `set_waiter_exists` + `pgbuf_block_bcb (PGBUF_LATCH_FLUSH)`) but does not initiate one.
- It removes the BCB from hash/LRU via `pgbuf_invalidate_bcb` and loops until the lookup
  finds nothing — the "hard guarantee" documented at `:3469-3486`.
- Contrast: `pgbuf_flush_page_and_neutralize_bcb`-style helpers and
  `pgbuf_invalidate`/`pgbuf_invalidate_all` flush dirty pages before invalidating (the
  `pgbuf_invalidate_bcb` caller at `:3455-3463` is reached only after a safe flush). The
  destroy path deliberately bypasses that.
- Contrast: `pgbuf_dealloc_temp_page` (`src/storage/page_buffer.c:2731`) clears dirty
  without invalidating and is used only for temporary files — the "actually remove dirty
  flag" comment in the temp branch of `file_destroy` (`src/storage/file_manager.c:4166`).
  Temporary files are never recovered, so that pre-existing pattern is not comparable.

**What the follow-up commits changed.** The "clear dirty, never flush" semantics are
present unchanged since the base commit. `git show e3ff1a6e1:src/storage/page_buffer.c`
already has `if (pgbuf_bcb_is_dirty (bufptr)) pgbuf_bcb_clear_dirty (...)` inside the pool
scan. `commit 759109e15` only strengthened *removal*: it replaced the
`pgbuf_bcb_safe_flush_force_lock` call (which early-returned for non-dirty BCBs, so it
never actually waited for an in-flight flush) with the flush-waiter protocol, and removed
the `avoid_victim` skip that used to leave a clean BCB in the hash forever.
`commit e98dd6ac6` did not touch the discard; it added the NEW_PAGE neutralization in
`pgbuf_fix` (`src/storage/page_buffer.c:2513-2535`) for stale copies that recovery redo
*re-materializes*. `commit 93f11fb3f` only deleted the `FILE_DESTROY_DISCARD_BY_PROBE`
alternative and made `pgbuf_discard_page` static. **None of the three follow-ups addressed
the missing durability of the discarded pages' own contents.**

Note that `e98dd6ac6`'s commit message states the premise of this whole finding explicitly:

> Destroying a file discards its buffered pages, but the discard is a runtime-only action
> that leaves no log record. After a crash, recovery redo replays the log written before the
> destroy and re-materializes those pages in the buffer …

That is exactly the *benign* case (redo start LSA still precedes those records). The
finding under review is the case where redo start LSA has moved past them.

### 3. Does the checkpoint derive its redo start LSA from dirty pages in the pool?

**Yes.** `logpb_checkpoint` (`src/transaction/log_page_buffer.c:6901`) stamps
`newchkpt_lsa` = LSA of the `LOG_START_CHKPT` record (`:6996`), then:

```c
/* src/transaction/log_page_buffer.c:7010-7030 */
  detailed_er_log ("logpb_checkpoint: call pgbuf_flush_checkpoint()\n");
  if (pgbuf_flush_checkpoint (thread_p, &newchkpt_lsa, &chkpt_redo_lsa, &tmp_chkpt.redo_lsa, &flushed_page_cnt) !=
      NO_ERROR)
    { goto error_cannot_chkpt; }
  …
  if (LSA_ISNULL (&tmp_chkpt.redo_lsa))
    {
      LSA_COPY (&tmp_chkpt.redo_lsa, &newchkpt_lsa);
    }
  assert (LSA_LE (&tmp_chkpt.redo_lsa, &newchkpt_lsa));
```

`pgbuf_flush_checkpoint` (`src/storage/page_buffer.c:4274`) scans the pool and collects
only BCBs that are *currently dirty*:

```c
/* src/storage/page_buffer.c:4338-4344 */
      /* flush condition check */
      if (!pgbuf_bcb_is_dirty (bufptr)
	  || (!LSA_ISNULL (&bufptr->oldest_unflush_lsa) && LSA_GT (&bufptr->oldest_unflush_lsa, flush_upto_lsa))
	  || pgbuf_is_temporary_volume (bufptr->vpid.volid))
	{
	  PGBUF_BCB_UNLOCK (bufptr);
	  continue;
```

and `smallest_lsa` (the out-parameter that becomes `chkpt.redo_lsa`) is written **only in
the flush-failed branch** of `pgbuf_flush_seq_list`:

```c
/* src/storage/page_buffer.c:4676-4690 */
      else
	{
	  assert (false);
	  …
	  /* get the smallest oldest_unflush_lsa */
	  if (!LSA_ISNULL (&bufptr->oldest_unflush_lsa)
	      && (LSA_ISNULL (chkpt_smallest_lsa) || LSA_LT (&bufptr->oldest_unflush_lsa, chkpt_smallest_lsa)))
	    {
	      LSA_COPY (chkpt_smallest_lsa, &bufptr->oldest_unflush_lsa);
	    }
	}
```

Therefore, on a healthy checkpoint `chkpt.redo_lsa == newchkpt_lsa`. **A BCB that is no
longer dirty, or no longer in the pool, contributes nothing** — losing it before the
checkpoint's scan reaches it lets the redo LSA advance past that page's log records. The
`ER_LOG_CHECKPOINT_SKIP_INVALID_PAGE` WAL-violation detector at
`src/storage/page_buffer.c:4348-4360` cannot fire either, because it inspects BCBs that are
*present*.

The result is made durable: `log_Gl.hdr.chkpt_lsa = newchkpt_lsa`
(`src/transaction/log_page_buffer.c:7211-7213`), `log_Gl.chkpt_redo_lsa = tmp_chkpt.redo_lsa`
(`:7225`), then `logpb_flush_header (thread_p)` (`:7229`).

Recovery consumes it: `log_recovery.c:796` `LSA_COPY (&rcv_lsa, &log_Gl.hdr.chkpt_lsa)`;
analysis lowers the redo start to the checkpoint record's `redo_lsa`
(`src/transaction/log_recovery.c:2075-2078`):

```c
  if (LSA_LT (&chkpt.redo_lsa, start_redo_lsa))
    {
      LSA_COPY (start_redo_lsa, &chkpt.redo_lsa);
    }
```

then `log_recovery_redo (thread_p, &start_redolsa, &end_redo_lsa)` (`:881`). Records before
`start_redolsa` are never read; records at or after it are skipped per page when the page is
already newer (`src/transaction/log_recovery.c:532`: `if (rcv_lsa <= *rcv_page_ptr) … return false;`).

Corroborated by the local knowledge base:
`/home/vimkim/gh/my-cubrid-docs/log-manager/cubrid-log-manager-overview_4cfc837_claude.md:432`
— "플러시하지 못한 가장 작은 LSA를 `chkpt_redo_lsa`로 회수 — 이것이 복구 redo 시작점이다."

**Step 3 of the claim is sound as a code property.** Its weakness is purely temporal (see §7).

### 4. How is a permanent-file destroy replayed after a crash?

`file_postpone_destroy` (`src/storage/file_manager.c:4300`) appends a **logical postpone**:

```c
/* src/storage/file_manager.c:4326 */
  log_append_postpone (thread_p, RVFL_DESTROY, &addr, sizeof (*vfid), vfid);
```

`RVFL_DESTROY`'s dispatch entry uses `file_rv_destroy` for **both** undo and redo
(`src/transaction/recovery.c:116-121`), i.e. it serves (a) logical undo of `file_create`
and (b) run-postpone at commit. `file_rv_destroy` re-enters the full function:

```c
/* src/storage/file_manager.c:4271-4287 */
file_rv_destroy (THREAD_ENTRY * thread_p, LOG_RCV * rcv)
{
  VFID *vfid = (VFID *) rcv->data;
  …
  assert (log_check_system_op_is_started (thread_p));

  error_code = file_destroy (thread_p, vfid, false);
  if (error_code != NO_ERROR)
    {
      /* Not acceptable. */
      assert_release (false);
      return error_code;
    }
```

At runtime the postpone is executed as a logical sysop
(`src/transaction/log_manager.c:8636-8641`):

```c
      /* Logical postpone. Use a system operation and commit with run postpone */
      log_sysop_start (thread_p);
      error_code = (*RV_fun[rcvindex].redofun) (thread_p, &rcv);
      assert (error_code == NO_ERROR);
      log_sysop_end_logical_run_postpone (thread_p, log_lsa);
```

At recovery, `log_recovery_finish_postpone` first finishes any interrupted sysop postpone,
then aborts an interrupted run-postpone sysop and re-runs the transaction postpones
(`src/transaction/log_recovery.c:4334-4370`). The abort routine's own comment is the
in-code statement of the requirement this finding is about:

```c
/* src/transaction/log_recovery.c, log_recovery_abort_interrupted_sysop() */
  /* how it works:
   * we can have so-called logical run postpone system operation for some complex cases (e.g. file destroy or
   * deallocate). if these operations are interrupted by crash, we must abort them first before finishing the postpone
   * phase of system operation or transaction. …
   */
```

That is precisely the **"abort 후 재실행"** contract: the interrupted destroy is *aborted*
(the `RVFL_TRACKER_UNREGISTER` undo re-registers the file —
`file_rv_tracker_unregister_undo`, `src/storage/file_manager.c:10086`, whose comment reads
"undo the unregister of file. may happen if file_destroy is only partially …") and the
`RVFL_DESTROY` postpone is then **re-executed** by `log_do_postpone`
(`src/transaction/log_recovery.c:4370`).

**Is the VSID list durably captured anywhere?** Not before the discard, and this is the
crux. The sector unreserve is itself a postpone, appended *after* the discard:

```c
/* src/storage/disk_manager.c:4870-4877 (disk_stab_unit_unreserve) */
      if (context->purpose == DB_PERMANENT_DATA_PURPOSE)
	{
	  /* postpone */
	  addr.pgptr = cursor->page;
	  addr.offset = cursor->offset_to_unit;
	  log_append_postpone (thread_p, RVDK_UNRESERVE_SECTORS, &addr, sizeof (unreserve_bits), &unreserve_bits);
	}
```

So the timeline inside the destroy sysop is:

```
log_sysop_start
  ├─ RVFL_TRACKER_UNREGISTER            (logged undoredo, immediate)
  ├─ collect VSIDs from in-memory header (correct)
  ├─ pgbuf_discard_pages_of_sectors      <-- WAL hole opens (file_manager.c:4161)
  ├─ RVDK_UNRESERVE_SECTORS × N          (postpone records only; bitmap untouched)
  └─ log_sysop_end_logical_run_postpone
       └─ LOG_SYSOP_START_POSTPONE       <-- WAL hole closes: list now durable & replayable
          → run the RVDK_UNRESERVE_SECTORS postpones
          → LOG_SYSOP_END_LOGICAL_RUN_POSTPONE
```

- Crash **before** `LOG_SYSOP_START_POSTPONE`: sysop aborted, its postpones discarded, the
  bitmap never changed → destroy re-executed → **on-disk header re-read**. Exposed.
- Crash **after** `LOG_SYSOP_START_POSTPONE`: `log_recovery_finish_sysop_postpone`
  (`src/transaction/log_recovery.c`) reads `sysop_start_postpone_lsa`, replays the remaining
  `RVDK_UNRESERVE_SECTORS` postpones from the log, and simulates the sysop commit — no
  header read, no re-collection. Safe.

So the answer to the research question is: **the retry re-executes `file_destroy()` and
re-reads on-disk metadata**; the sector list is durably captured only from
`LOG_SYSOP_START_POSTPONE` onward. "The retry reads outdated on-disk metadata" is possible.

### 5. Is "recently expanded file, sector-list updates only in dirty buffers" reachable?

**Yes.** All header/ftab mutations are ordinary page-oriented (physiological) undoredo
records on the header page, made durable only by WAL + eventual page flush:

```c
/* src/storage/file_manager.c:4633-4645 (file_perm_expand) */
  save_lsa = *pgbuf_get_lsa (page_fhead);

  /* file extended successfully. log the change. */
  log_append_undoredo_data2 (thread_p, RVFL_EXPAND, NULL, page_fhead, 0, 0,
			     expand_size_in_sectors * sizeof (VSID), NULL, vsids_reserved);
  …
  pgbuf_set_dirty (thread_p, page_fhead, DONT_FREE);
```

Same shape for `RVFL_PARTSECT_ALLOC` (`:5163`), `RVFL_FHEAD_ALLOC` (`:1265`),
`RVFL_FHEAD_DEALLOC` (`:1300`), `RVFL_EXTDATA_*`, and the header's own creation via
`pgbuf_log_new_page (thread_p, page_fhead, DB_PAGESIZE, PAGE_FTAB)` (`:3831` →
`RVPGBUF_NEW_PAGE` full-page redo, `src/storage/page_buffer.c:15167-15176`).

These records are **self-sufficient for redo** — `RVFL_EXPAND`'s redo function
`file_rv_perm_expand_redo` reconstructs the partial table from the logged VSID array, and
`RVPGBUF_NEW_PAGE` carries the whole page — but only if the redo scan actually reaches them,
i.e. only if `start_redolsa <= record LSA`. Nothing in `file_perm_expand` or
`file_perm_alloc` forces the header page to disk. The header can therefore be dirty-only for
an unbounded time before the destroy, and `file_perm_expand` runs in its own committed
sysop (`:4597-4600`, `log_sysop_start` … `log_sysop_commit`) so the expansion survives the
dropping transaction's boundaries.

**Latching / concurrency.** During `file_destroy` the header is `PGBUF_LATCH_WRITE`-held from
`:4116` to `:4158`, which excludes concurrent expansion (every expansion path goes through
the header write latch). The file is also already unregistered from the tracker (`:4105`)
and the object is exclusively locked by the DDL. So the *collected* list is correct; the
exposure is not a collection race but the loss of durability of the metadata the *retry*
depends on. Between `:4158` and `:4161` the header BCB is unfixed and still dirty, so a
victimizer or the flush daemon *may* happen to write it — that is an accidental mitigation,
not a guarantee (`pgbuf_discard_page` waits for such a flush at `:3520-3532` but never
starts one).

### 6. What did the OLD path do?

`git show e3ff1a6e1 -- src/storage/file_manager.c` removed a loop that fixed every page and
called `pgbuf_dealloc_page`, plus these two lines for the file's own table pages:

```c
/* removed by commit e3ff1a6e1, from the pre-change file_destroy */
-		  pgbuf_dealloc_page (thread_p, page_ftab);
…
-      /* deallocate header page */
-      pgbuf_dealloc_page (thread_p, page_fhead);
```

`pgbuf_dealloc_page` (`src/storage/page_buffer.c:15246`) does **not** drop dirty state
silently — it logs and keeps the page dirty:

```c
/* src/storage/page_buffer.c:15271-15291 */
  log_append_undoredo_data2 (thread_p, RVPGBUF_DEALLOC, NULL, page_dealloc, 0, sizeof (udata), 0, &udata, NULL);
  …
  /* set unknown type */
  bcb->iopage_buffer->iopage.prv.ptype = (unsigned char) PAGE_UNKNOWN;
  /* clear page flags (now only tde algorithm) */
  bcb->iopage_buffer->iopage.prv.pflag = (unsigned char) 0;

  /* set dirty and mark to move to the bottom of lru */
  pgbuf_bcb_update_flags (thread_p, bcb, PGBUF_BCB_DIRTY_FLAG | PGBUF_BCB_MOVE_TO_LRU_BOTTOM_FLAG, 0);
```

So the review's phrasing — "the old path retained dirty metadata for checkpoint flushing" —
is **substantively correct but mechanically imprecise**. The old path's actual protection was
stronger than "retained for flushing": it *never broke the WAL invariant* for those pages.
Every dealloc was a page-oriented undoredo record that stamped the page LSA, the BCB stayed
dirty and in the pool, and therefore no checkpoint could ever advance its redo LSA past an
un-flushed header/ftab change. Consequently the retry after an "abort 후 재실행" was always
served correct data: redo could rebuild the header from disk + log, and the sysop abort
undid `RVPGBUF_DEALLOC` via `pgbuf_rv_dealloc_undo`
(`src/storage/page_buffer.c:15328`), restoring `ptype` so the retry's `OLD_PAGE` fix was
legitimate.

The temp-branch comment "invalidate pages in page buffer. actually remove dirty flag."
(`src/storage/file_manager.c:4166`) does predate the change, but it guards
`pgbuf_dealloc_temp_page` on **temporary** files only — which are never recovered
(`pgbuf_is_temporary_volume` also excludes them from the checkpoint flush,
`src/storage/page_buffer.c:4343`). It is not an existing instance of the hazard.

**Conclusion for §6: the change introduced a new hazard class; it did not inherit one.**

### 7. Verdict detail — the minimal window and the weakest link

**Weakest link: the temporal coincidence required by steps 3 + 4, not their validity.**
Every individual mechanism is verified. What is unverified is the frequency with which a
checkpoint *completes* (through `logpb_flush_header`, `src/transaction/log_page_buffer.c:7229`)
inside the exposed window *and* a crash follows inside the same window.

Minimal concrete window:

- **Pages:** the destroyed file's header page (`VPID{vfid->volid, vfid->fileid}`) and its
  `fhead->n_page_ftab` ftab pages. User pages are genuinely safe — they are only revisited
  through `NEW_PAGE` after sector reuse, which is exactly what `e98dd6ac6` hardened
  (`src/storage/page_buffer.c:2513-2535`).
- **Log records at risk:** any `RVFL_EXPAND` / `RVFL_PARTSECT_ALLOC` / `RVFL_FHEAD_*` /
  `RVFL_EXTDATA_*` / `RVPGBUF_NEW_PAGE` record on those pages whose effect had not yet been
  flushed at the moment of `file_manager.c:4161`.
- **Boundaries:** opens at `pgbuf_discard_pages_of_sectors` (`src/storage/file_manager.c:4161`);
  closes at the `LOG_SYSOP_START_POSTPONE` written by
  `log_sysop_end_logical_run_postpone` (`src/transaction/log_manager.c:8641` →
  `log_sysop_commit_internal`) for the run-postpone sysop of `file_rv_destroy`. Wall-clock
  content of the window: one pool scan (the base commit measures ~1-4 ms) plus
  `disk_unreserve_ordered_sectors` (`:4228`, one postpone record per 64-sector
  `DISK_STAB_UNIT`, so tens of records for a 1 GB file) plus the sysop commit prologue.
- **Also required:** the checkpoint's own pool scan must pass the discarded BCB slots
  *after* the discard cleared them. Since `pgbuf_flush_checkpoint` interleaves scanning with
  rate-limited IO batches (`src/storage/page_buffer.c:4310-4332`,
  `PRM_ID_LOG_CHECKPOINT_SLEEP_MSECS`), a long-running checkpoint whose cursor has not yet
  reached those BCB indices satisfies this without any tight timing on the checkpoint's
  *start*. Only its *completion* must fall inside the window.
- **Two outcomes:** (a) stale-but-self-consistent header → smaller VSID set → sectors
  leaked, silently (`file_table_collect_all_vsids`' `n_vsids != n_sector_total` guard,
  `src/storage/file_manager.c:3990-3995`, passes because it compares against the stale
  header's own counter); (b) header image predating the file's creation →
  `ptype == PAGE_UNKNOWN` → `pgbuf_fix (OLD_PAGE)` returns `NULL` with `ER_PB_BAD_PAGEID`
  (`src/storage/page_buffer.c:2473-2492`) → `file_destroy` `ER_FAILED` (`:4118-4123`) →
  `file_rv_destroy` `assert_release (false)` (`:4281-4287`; `assert_release` is `assert`
  and stays active in release builds per `src/base/error_manager.h:189-197`) → recovery
  cannot complete. Outcome (b) matches the finding's "a never-flushed header can prevent
  recovery altogether"; it is most plausible for the *logical-undo-of-create* context
  (`CREATE` … rollback, `src/storage/file_manager.c:4266-4268`), where the header may never
  have been flushed at all.

**No checkpoint exclusion protects the window** — I searched for one and found none:
`file_destroy` holds no log CS, sets no atomic-sysop marker, and `logpb_checkpoint` has no
awareness of in-progress destroys beyond recording commit-postpone sysops in the
`LOG_END_CHKPT` record (`src/transaction/log_page_buffer.c:7105-7124`), which does not
constrain `redo_lsa`.

### 8. Testability

**Existing machinery, and what is missing.**

- **Crash injection:** `src/base/fault_injection.h:55-89` defines
  `FI_TEST_LOG_MANAGER_RANDOM_EXIT_AT_RUN_POSTPONE = 500000` and
  `FI_TEST_LOG_MANAGER_RANDOM_EXIT_AT_END_SYSTEMOP = 500001`, both wired to
  `fi_handler_random_exit` (`src/base/fault_injection.c:66-67`) and grouped for random use
  (`:82-83`). The run-postpone hook fires **before** `log_run_postpone_op`
  (`src/transaction/log_manager.c:8436-8449`) — i.e. before `file_destroy` even starts — and
  the source itself notes the gap immediately after: `/* TODO: consider to add FI here */`
  (`src/transaction/log_manager.c:8449`). **There is no existing injection point inside the
  destroy window.** Hitting `[file_manager.c:4161, LOG_SYSOP_START_POSTPONE]` deterministically
  requires adding one (e.g. a new `FI_TEST_FILE_MANAGER_*` code right after
  `pgbuf_discard_pages_of_sectors`).
- **Forcing a checkpoint:** `csql --sysadm` has a `;checkpoint` session command
  (`src/executables/csql_session.c:95` → `src/executables/csql.c:1269-1285` →
  `db_checkpoint()`, `src/compat/db_admin.c:1557` → `NET_SERVER_LOG_CHECKPOINT`). Also
  `checkpoint_interval` / `checkpoint_sleep_msecs` parameters
  (`src/base/system_parameter.c:183-187`) can be tuned to make checkpoints frequent and slow.
  So "force a checkpoint" is available; "force it to complete exactly between the discard and
  the sysop start-postpone" is not, without the injection point above.
- **Detection after restart:** `cubrid checkdb --check-file-tracker`
  (`src/executables/utility.h:1285-1286`, `src/executables/util_cs.c:732-735` →
  `CHECKDB_FILE_TRACKER_CHECK` → `file_tracker_check`, `src/storage/file_manager.c:11907`).
  In **SA mode** it clones every permanent volume's sector table
  (`disk_map_clone_create`, `src/storage/disk_manager.c:6634`), subtracts what every tracked
  file claims (`file_tracker_item_check`, `src/storage/file_manager.c:12032`), and then:

  ```c
  /* src/storage/disk_manager.c, disk_map_clone_check_leaks() */
	  if (*unit != 0)
	    {
	      /* leaked sectors */
	      assert_release (false);
	      return DISK_INVALID;
	    }
  ```

  That is exactly the detector for outcome (a). `disk_check`
  (`src/storage/disk_manager.c:6445`, called unconditionally from
  `xboot_check_db_consistency`, `src/transaction/boot_sr.c:3727`) validates the disk cache
  against the sector tables but would *not* flag a leak, because the leaked sectors remain
  consistently marked reserved. Outcome (b) needs no detector — the server fails to restart.
- **Honest assessment:** the proposed test (pause after discard → force checkpoint → crash →
  restart → checkdb) is the right test, and the *observation* half is fully supported by
  shipped tooling. The *provocation* half is **not** reproducible with what exists: it needs a
  debug-only hook inside `file_destroy` between `:4161` and the sysop commit. Once that hook
  exists, the test is straightforward and deterministic (create a table, insert enough to
  force at least one `file_perm_expand` whose header update is never flushed, `DROP`, block in
  the hook, `;checkpoint` from a second `csql --sysadm`, `kill -9`, restart,
  `cubrid checkdb --check-file-tracker` in SA mode). I did not attempt it; nothing in this
  note is an empirical result. There is no `tests/` directory in this worktree (the shell/SQL
  suites come from CTP), so I could not point at an existing in-repo crash-recovery test to
  extend; the base commits reference the external QA scenarios `bug_bts_17534` (fault
  injection) and `cbrd_23430` (hard-kill/recovery loops), which are the natural homes for it
  but which exercise *random* exit points, not this window.

---

## Open questions / not verified

1. **Not reproduced.** No crash was provoked; no leak or recovery failure was observed. The
   entire note is source-derived.
2. **Real-world probability not quantified.** I did not instrument the window or measure how
   often a checkpoint completes inside `[file_manager.c:4161, LOG_SYSOP_START_POSTPONE]`.
   Whether this is a once-in-a-million-DROPs event or effectively unreachable is **not
   determined**.
3. **Whether a victimizer/flusher effectively closes the hole in practice.** Between `:4158`
   and `:4161` the header is unfixed and dirty and could be flushed by the page-flush daemon.
   I did not assess how likely that is, and it is not a guarantee in any case.
4. **Outcome (b) severity in release builds.** I traced `pgbuf_fix (OLD_PAGE)` → `NULL` →
   `ER_FAILED` → `assert_release`, and confirmed `assert_release` maps to `assert` in the
   non-`NDEBUG` arm of `src/base/error_manager.h:189-197`. I did **not** verify which arm the
   project's release build selects, so whether a release server aborts or continues with a
   corrupt error path is **not determined**. I also did not evaluate whether a garbage
   (non-`PAGE_UNKNOWN`) header image could pass the guards and cause `file_destroy` to
   unreserve sectors belonging to *other* files — a worse outcome than a leak. That path
   deserves its own analysis.
5. **No originating spec found locally.** `grep` for `CBRD-27151` across
   `/home/vimkim/gh/my-cubrid-jira` and `/home/vimkim/gh/my-cubrid-docs` found only an
   incidental mention in `cbrd-26357/ci_analysis_report_2940b1c_claude.md:160,168`. The
   Korean requirement phrase **"abort 후 재실행"** does not appear anywhere in either
   knowledge base, so I could not read the requirement in its original wording. What I *can*
   attest is that the in-code contract matching that phrase exists verbatim in intent — see
   the `log_recovery_abort_interrupted_sysop` comment quoted in §4, which names "file
   destroy" as its motivating case.
6. **TDE interaction not analyzed.** `file_destroy` logs a TDE-specific trace for encrypted
   files (`src/storage/file_manager.c:4129-4132`, reworded by `commit e98dd6ac6`). Whether a
   stale/garbage header read on retry interacts badly with TDE key handling is **not
   examined**.
7. **HA / replication (`log_recovery_redo` on a replica, page-server modes)** not considered.
8. **`file_destroy` from other callers** (`src/storage/file_manager.c:10641`, `:11482`,
   `:11655-11666`, `:9587`) not individually traced for whether they too can be re-executed
   after an abort. `:11482` and `:10641` are tracker-driven cleanup paths that plausibly run
   under their own sysops; I checked only the `RVFL_DESTROY` contexts.

---

## Proposed remedy options

Both options in the finding are viable; they differ sharply in cost against the change's
purpose (cold `DROP` commit 1.5-2.0 s → 2 ms, per `commit e3ff1a6e1`).

### Option A — preserve recoverable metadata until completion

**A1 (recommended): keep per-page dealloc logging for the file's own table pages only.**
Restore `pgbuf_dealloc_page` for the header page and the `n_page_ftab` ftab pages, and keep
the bulk discard for user pages. This is literally the two removed lines from
`commit e3ff1a6e1` plus the ftab loop, restricted to table pages
(`file_extdata_collect_ftab_pages` already exists and is still used by the temp branch,
`src/storage/file_manager.c:4176-4182`).

- *Why it is correct:* `RVPGBUF_DEALLOC` is a page-oriented undoredo record that stamps the
  page LSA and leaves the BCB dirty (`src/storage/page_buffer.c:15271-15291`), so no
  checkpoint can advance past those pages' un-flushed changes, and the sysop abort restores
  `ptype` via `pgbuf_rv_dealloc_undo` (`:15328`) so the retry's `OLD_PAGE` fix is legitimate.
  This is exactly the invariant the old path relied on.
- *Cost:* `n_page_ftab` page fixes (all of which are in the buffer or cheap to read — they
  are the file's own metadata, already touched by `file_table_collect_all_vsids`) plus
  `n_page_ftab` log records. For a 1 GB heap, `n_page_ftab` is a handful of pages against
  ~65 000 user pages. **The perf win is preserved essentially intact.**
- *Risk:* smallest of the options; it is a partial revert to known-good behavior.

**A2: flush the header + ftab pages before discarding them.** Fix each table page, force it
out with `pgbuf_flush_page_and_neutralize_bcb`-style handling *while its sectors are still
reserved*, then discard the rest.

- *Cost:* `n_page_ftab` synchronous writes on the commit path — worse than A1 (which adds
  log bytes, not IO) and it re-introduces IO latency into the commit that the change set out
  to remove. Prefer A1.

### Option B — durably record the sector list needed for retry

Make the retry independent of the on-disk header.

- **B1: move the durability boundary before the discard.** The list *is* already made
  replayable at `LOG_SYSOP_START_POSTPONE` (§4). One could append the collected VSID array
  as an explicit redo/postpone record *before* `pgbuf_discard_pages_of_sectors` and have the
  retry consume it. But a record appended inside a sysop that recovery *aborts* is not
  consulted by the re-execution — `log_recovery_abort_interrupted_sysop` +
  `log_do_postpone` re-run `RVFL_DESTROY` from the *transaction's* postpone record, which
  carries only the `VFID` (`src/storage/file_manager.c:4326`). Making this work requires
  either restructuring the destroy so its start-postpone precedes the discard, or extending
  the transaction-level `RVFL_DESTROY` payload.
- **B2: put the VSID array in the transaction-level `RVFL_DESTROY` postpone record.** Then
  `file_rv_destroy` never reads the header. But that record is appended by
  `file_postpone_destroy` at DDL-execution time, long before commit, when the sector list is
  not yet final; it would have to be collected early and kept authoritative, which is
  fragile and changes the record format (a log-compatibility concern).
- *Cost:* B1/B2 add log volume proportional to `n_sector_total` (~1 KB per 1000 sectors —
  negligible) and no IO, so their *runtime* cost is attractive. Their *engineering* cost and
  risk are markedly higher than A1: restructuring sysop/postpone boundaries in the destroy
  path, or a log-record format change.

### Recommendation

**A1.** It restores the exact invariant the old path depended on, at a cost bounded by
`n_page_ftab` (not `n_page_user`), so the DROP/TRUNCATE commit-cost goal that motivates
CBRD-27151 survives. It is also the smallest reviewable diff and needs no log-format change.
If A1 is adopted, the discard's own doc comment
(`src/storage/page_buffer.c:3469-3486`) and the `file_destroy` comment
(`src/storage/file_manager.c:4149-4155`) should be updated to state explicitly that the bulk
discard is valid **only** for pages that no recovery path re-reads — user pages — and that
the file's own table pages are excluded for that reason.

Independently of the remedy chosen, adding the missing fault-injection point noted in §8
(right after `file_manager.c:4161`) is worthwhile on its own: it makes this window testable
and closes the `/* TODO: consider to add FI here */` gap at
`src/transaction/log_manager.c:8449`.

---

## Sources

Read at `93f11fb3f` (worktree `/home/vimkim/gh/cb/review-CBRD-27151-drop-sec`):

- `src/storage/file_manager.c` — `file_destroy` (`:4076-4260`), `file_rv_destroy` (`:4271`),
  `file_postpone_destroy` (`:4300-4326`), `file_table_collect_all_vsids` (`:3948`),
  `file_create` (`:3440-3700`), `file_perm_expand` (`:4549`), `file_perm_alloc` (`:5071`),
  `file_header_update_mark_deleted` (`:1316`), `file_log_fhead_dealloc` (`:1283`),
  `file_rv_tracker_unregister_undo` (`:10086`), `file_tracker_check` (`:11907`),
  `file_tracker_item_check` (`:12032`), `file_temp_retire_internal` (`:4378`)
- `src/storage/page_buffer.c` — `pgbuf_discard_page` (`:3487`),
  `pgbuf_discard_pages_of_sectors` (`:3605`), `pgbuf_compare_vsids_for_discard` (`:3572`),
  `pgbuf_flush_checkpoint` (`:4274`), `pgbuf_flush_chkpt_seq_list` (`:4415`),
  `pgbuf_flush_seq_list` (`:4525`, smallest-LSA branch `:4676-4690`),
  `pgbuf_fix` deallocated/NEW_PAGE handling (`:2465-2536`),
  `pgbuf_dealloc_page` (`:15246`), `pgbuf_rv_dealloc_redo/undo` (`:15309`, `:15328`),
  `pgbuf_dealloc_temp_page` (`:2731`), `pgbuf_log_new_page` (`:15167`),
  `pgbuf_bcb_clear_dirty` (`:16132`)
- `src/storage/page_buffer.h` — `pgbuf_discard_pages_of_sectors` decl (`:277`),
  `pgbuf_flush_checkpoint` decl (`:365`)
- `src/storage/disk_manager.c` — `disk_unreserve_ordered_sectors` (`:4703`),
  `disk_unreserve_ordered_sectors_without_csect` (`:4735`),
  `disk_stab_unit_unreserve` (`:4847`, postpone at `:4876`), `disk_check` (`:6445`),
  `disk_map_clone_create` (`:6634`), `disk_map_clone_check_leaks`
- `src/transaction/log_page_buffer.c` — `logpb_checkpoint` (`:6901-7270`), notably `:7011`,
  `:7025-7030`, `:7211-7229`
- `src/transaction/log_recovery.c` — `log_rv_fix_page_and_check_redo_is_needed` (`:503-543`),
  recovery driver (`:751-881`), `log_rv_analysis_end_checkpoint` (`:1852-2085`),
  `log_recovery_analysis` (`:2609`), `log_recovery_redo` (`:3399`),
  `log_recovery_abort_interrupted_sysop`, `log_recovery_finish_sysop_postpone`,
  `log_recovery_finish_postpone` (`:4334`), `log_recovery_finish_all_postpone` (`:4403`)
- `src/transaction/log_manager.c` — `log_sysop_end_logical_run_postpone` (`:4043`),
  `log_do_postpone` (`:8280`, FI point `:8436-8449`), `log_execute_run_postpone` (`:8586-8641`)
- `src/transaction/recovery.h` — `RVFL_*` / `RVDK_*` indexes (`:43-76`, `:262-290`)
- `src/transaction/recovery.c` — dispatch entries for `RVFL_DESTROY` (`:116-121`),
  `RVFL_EXPAND` (`:122-125`), `RVPGBUF_NEW_PAGE` (`:790-793`)
- `src/transaction/boot_sr.c` — `xboot_check_db_consistency` (`:3716-3790`)
- `src/base/fault_injection.h` (`:38-121`), `src/base/fault_injection.c` (`:60-90`)
- `src/base/error_manager.h` — `assert_release` (`:189-197`)
- `src/base/system_parameter.c` — checkpoint parameter names (`:183-187`)
- `src/executables/csql_session.c` (`:95`), `src/executables/csql.c` (`:1269-1285`),
  `src/executables/util_cs.c` (`:298`, `:732-735`), `src/executables/utility.h` (`:1285-1286`),
  `src/compat/db_admin.c` (`:1557`), `src/communication/network_interface_cl.c` (`:2598-2620`)

Git history:

- `commit e3ff1a6e1` — base change (message + `git show e3ff1a6e1 -- src/storage/file_manager.c`
  + `git show e3ff1a6e1:src/storage/page_buffer.c`)
- `commit 759109e15` — discard hardening (message + stat)
- `commit e98dd6ac6` — NEW_PAGE neutralization after crash recovery (message + stat)
- `commit 93f11fb3f` — removal of the probe variant (message + stat)
- `commit f8f5b4401` — pre-change baseline (referenced only)

Knowledge bases consulted:

- `/home/vimkim/gh/my-cubrid-docs/log-manager/cubrid-log-manager-overview_4cfc837_claude.md`
  — §checkpoint (`:429-438`) and §recovery redo (`:471-495`); corroborates the
  `chkpt_redo_lsa` → redo-start relationship independently of my own reading.
- `/home/vimkim/gh/my-cubrid-docs/cbrd-26357/ci_analysis_report_2940b1c_claude.md:160,168`
  — the only local reference to CBRD-27151 (a CI-side `file_destroy` message-format change);
  no design or requirement content.
- `/home/vimkim/gh/my-cubrid-jira` — searched for `CBRD-27151` and for the phrase
  "abort 후 재실행"; **no matching document exists**, so the originating spec text could not
  be read.
- `/home/vimkim/gh/my-cubrid-docs/pgbuf-analysis/` — inventoried
  (`pgbuf-defects-report_5cd4f860e_claude.md`, `cubrid-page-buffer-report_5cd4f860e_claude.html`);
  neither covers the destroy/discard path, so neither is cited above.
