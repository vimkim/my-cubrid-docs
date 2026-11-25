# CBRD-28379 review: commit 11b40319ee

- Branch `CBRD-28379` (local worktree), base `origin/develop` ca39c2c6a4. `gh-pr-info` found no PR yet.
- Scope: `src/storage/page_buffer.c` (two hunks), `unit_tests/oos/test_pgbuf_conditional_latch_server.cpp`, `unit_tests/oos/CMakeLists.txt`.
- Method: read-only code review. I did not build the code or run the tests. The claims that "all four cases fail on develop" and the 5-round OOS reproduction are not verified here.

## Verdict

**No blocking issue found.** The core change (a conditional request no longer sets `waiter_exists`) is correct and minimal. It restores the behavior from before CBRD-26425, when a conditional request never queued and so never looked like a waiter. The new fallback in `pgbuf_unlatch_bcb_upon_unfix` can be reached, is safe and is worth keeping. The findings below are should-fix or smaller.

## Checks done (no finding)

1. **CAS loops and memory order** (`page_buffer.c:7020-7131`)
   - When a conditional request is refused, `new_impl == old_impl`, so the CAS writes nothing. A CAS failure caused by a concurrent lock-free `fcnt++/--` sends the loop back to recompute. That is harmless.
   - The lock-free paths cannot interfere:
     - `pgbuf_lockfree_fix_ro` (8453) requires `READ && !waiter_exists && fcnt>0`, so it can never fix a `NO_LATCH` BCB.
     - `pgbuf_lockfree_unfix_ro` (8534) refuses when `fcnt==1`, so the last unfix always takes the mutex path.
   - Every change to `waiter_exists` still happens under the BCB mutex. The change only enables the lock-free READ path in more cases, and those are exactly the cases with no queued waiter.
2. **Wait queue**
   - `pgbuf_block_bcb` asserts (7745) that READ/WRITE waiters set the mark before they queue. Both unconditional paths still do: case 3 (7124) and sub-case 2-2 (7110).
   - Flush waiters do not depend on the mark (9667).
   - `pgbuf_wakeup_reader_writer` (8297) and `pgbuf_timed_sleep_error_handling` (7970) still clear the mark when they find no reader or writer in the queue.
   - Starvation: nothing relies on a conditional request setting the mark to hold back new readers. Before CBRD-26425 the check was `pgbuf_is_exist_blocked_reader_writer` (a scan of the queue), so a conditional request never blocked readers then either. No new starvation compared with the pre-26425 baseline.
3. **Promotion**
   - A refused conditional promotion (sub-case 2-2) now leaves the latch word unchanged, which is correct.
   - `pgbuf_promote_read_latch` (2944-3008) has its own CAS and is not affected. It sets the mark only on the path where it blocks.
   - The checks of `wait_for_latch_promote` are unchanged.
4. **Fallback (7535-7546)**: the BCB state is the same as on the no-waiter path.
   - The mutex is held. `pgbuf_wakeup_reader_writer` does not release it.
   - A granted waiter always gets READ or WRITE, never `NO_LATCH`. So `get_latch()==NO_LATCH` reliably means no waiter took the latch, and `fcnt==0`.
   - It cannot place the BCB twice:
     - It runs only when `blocked_reader_writer` is true, and then the zone switch above was skipped.
     - If `MOVE_TO_LRU_BOTTOM` was set, `pgbuf_move_bcb_to_bottom_lru` already moved the BCB out of `VOID`.
     - `pgbuf_unlatch_void_zone_bcb` asserts that the zone is `VOID`.
   - Victimization cannot be involved. The BCB had `fcnt>0` until this thread's CAS under the mutex, so no victimizer and no direct-victim claim can have it in `VOID`.
   - Vacuum direct-victim assignment, the private LRU index (same macro as 7413-7420), async flush (it runs afterwards, as on the normal path) and temp pages all behave as on the normal path.
   - **It can be reached.** On timeout or interrupt, `pgbuf_timed_sleep` sets `request_latch_mode = PGBUF_NO_LATCH` under the entry lock only, then waits for the BCB mutex in `pgbuf_timed_sleep_error_handling`. If the holder takes the mutex in that window, the holder reads the mark as true, wakeup removes the entry, and no waiter gets the latch. The pre-26425 scan had the same window, so the fallback also closes an older leak. It costs nothing on the no-waiter path.
5. **`SA_MODE`**: the fallback is inside `SERVER_MODE`. In `SA_MODE` the non-idle path asserts, so the change in the CAS loop has no effect there.
6. **Heal safety net (6995-7007)**: unchanged. With this fix, a stranded mark is even less likely.
7. **Code style**
   - `indent -l120 -lc120` on a scratch copy of `page_buffer.c` gives a byte-identical file.
   - The commit message matches the code.

## Findings

### F1 [should-fix, PLAUSIBLE]: exact LRU-count assertions can be flaky

- **Where:** `test_pgbuf_conditional_latch_server.cpp:160,171,183,194`
- **Problem:** `count_lru_bcbs()` comes from `pgbuf_peek_stats`, an unlocked scan of zones across the whole pool. The tests assert `lru_after == lru_before + 1` exactly.
- **Failure scenario:** between the two reads, a background thread of the in-process server (vacuum master or worker, checkpoint, page flush/post-flush daemon) fixes a page that is not in the buffer. It takes a BCB from the free list, and on unfix that BCB enters an LRU list, so the delta is +2. Or, under victim pressure, a BCB leaves the LRU list for direct-victim assignment, and the delta is 0 although the fix works. With an idle fresh DB the risk is low, but `RefusedWriteRequestLetsNewPageEnterLru` repeats the window 8 times.
- **Fix options:**
  - Best: check the BCB's own zone directly. For example, add a small test-only accessor (`pgbuf_is_page_in_lru (PAGE_PTR/VPID)` under `!NDEBUG`) or reuse an existing debug hook, and assert per page.
  - Otherwise, relax to an aggregate check over N pages: `lru_after - lru_before >= N` with the bug giving about 0. Also log the counts on failure.

### F2 [nit]: no test reaches the new fallback

- **Where:** `page_buffer.c:7535`
- **Problem:** the four tests all exercise the conditional-latch hunks. None reaches the case where every waiter gave up before wakeup. The fallback is correct by reading, but a regression in it would go unnoticed.
- **Fix:** if the code base has a fault-injection point (`FI_TEST`) or a debug sleep, add one between the `request_latch_mode = PGBUF_NO_LATCH` assignment and `pgbuf_timed_sleep_error_handling` in `pgbuf_timed_sleep`. Then use a short latch timeout to test it. Otherwise, state in the commit message or the test header that the fallback has no test.

### F3 [nit]: the fallback skips the `pgbuf_pg_unfix_cnt` count

- **Where:** `page_buffer.c:7407-7411` vs 7535
- **Problem:** the fallback does not increment `thread_p->pgbuf_pg_unfix_cnt`. This matches the old path with waiters, and the counter only feeds the monitor sum (2213-2248), so it affects statistics only.
- **Fix:** none needed. Mention it only if the fallback is meant to be exactly the no-waiter unfix.

### F4 [nit]: worker task can hang if the callback throws

- **Where:** `test_pgbuf_conditional_latch_server.cpp:72-83`
- **Problem:** `other_thread::run` waits on `done_future` with no limit. If `func` throws (gtest assertion macros do not throw by default), `done.set_value()` is never called and the test hangs until the 60 s ctest `TIMEOUT`. `tran_index` is also not restored in that case.
- **Fix:** wrap `func` in try/catch or a scope guard that always restores `tran_index` and sets the promise. Optionally use `wait_for` with a bound.
- Not a problem: `ASSERT_NE` inside the lambda (244) only returns from the lambda. That is fine, because the outer `EXPECT_FALSE (promoted)` then fails with a clear message.

### F5 [nit]: a page-buffer test lives in the OOS directory

- **Where:** `unit_tests/oos/CMakeLists.txt:86,383-388`
- **Problem:** a page-buffer test is registered under the OOS unit tests so that it can reuse `ServerModeEnv` and the `OOS_DB` fixture. The comment states this, which is acceptable. If the OOS tests are later split out or turned off, this test goes with them.
- **Fix:** none needed now. Move it if a common server-mode test harness is added later.

### F6 [nit]: comment capitalization

- **Where:** `page_buffer.c:7101`
- **Problem:** "Conditional latch fails. it is refused below ..." has a lowercase sentence after a period.
- **Fix:** "Conditional latch fails; it is refused below without waiting and leaves waiter_exists as it is."

### F7 [question, pre-existing, out of scope]: `pgbuf_discard_page` contradicts the flush-waiter rule

- **Where:** `page_buffer.c:3654` (CBRD-27151)
- **Problem:** `pgbuf_discard_page` calls `set_waiter_exists (true)` before it blocks as a `PGBUF_LATCH_FLUSH` waiter on a `NO_LATCH` BCB. This contradicts the rule at 7744 and 9667 ("a flush waiter does not set waiter_exists"). `pgbuf_wake_flush_waiters` does not clear the mark. Because the queue is not empty, the heal at 6999 would not fire. Then a concurrent `pgbuf_latch_bcb_upon_fix` would spin forever on the idle-grant CAS (which expects `waiter_exists == false`) while it holds the mutex.
- **Mitigation:** the caller contract says no concurrent fix is possible, and `pgbuf_invalidate_bcb` or the reuse of the BCB resets the latch word. Not caused by this commit.
- **Fix:** consider dropping that `set_waiter_exists (true)` in a separate issue.

## Housekeeping

- An ignored backup `src/storage/page_buffer.c~` (from indent, 20:36) is in the worktree. It is ignored by `.gitignore:132 *.*~` and is harmless. Delete it before packaging, if desired.
- C++ style of the test file: no `.astylerc` is in the worktree, so astyle conformance was not checked.
