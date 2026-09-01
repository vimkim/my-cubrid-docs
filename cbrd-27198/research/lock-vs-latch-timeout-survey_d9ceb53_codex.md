# Lock timeout versus latch timeout: CUBRID, PostgreSQL, and MySQL/InnoDB

**Research question.** Does CUBRID need to separate transaction lock timeout from internal page-latch timeout, and—if so—should an internal latch wait be bounded by 300 seconds, 1 second, or another policy?

**Primary CUBRID revision analyzed:** `d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530` (`CBRD-27198_disk-reserve-sectors-assert-on-page-timeout`)

**PR provenance:** GitHub PR [CUBRID/cubrid#7630](https://github.com/CUBRID/cubrid/pull/7630) reported HEAD `bd5c43cfc1a0fadc55bea0d3b9eea0a69c83ea65` at research time. The local worktree did **not** exactly match it. No checkout or fetch was performed. A read-only remote patch audit showed that the commits after local `d9ceb53` changed a comment and replaced literal `0` with `LK_ZERO_WAIT`; they did not change the behavior analyzed below. [`f98998c`, comment-only](https://github.com/CUBRID/cubrid/commit/f98998c18791b6dbcb50e9d1de9ec47d72072368) [`67f03f2`, constant spelling](https://github.com/CUBRID/cubrid/commit/67f03f2f3ed45649348cd2540e1a43e1a7fa6a8a)

## Executive verdict

- **[FACT]** CUBRID exposes `lock_timeout` as a transaction-lock policy, yet `pgbuf_fix_internal()` reads the transaction's `LOG_TDES::wait_msecs` and silently converts an explicitly unconditional page-latch request to conditional for `LK_ZERO_WAIT` and `LK_FORCE_ZERO_WAIT`. This is the design leak at the center of the issue. [`LOG_TDES::wait_msecs`, `log_impl.h:474-487`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/transaction/log_impl.h#L474-L487) [`pgbuf_fix_internal`, `page_buffer.c:2160-2236`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L2160-L2236)
- **[FACT]** A positive CUBRID `lock_timeout` does **not** determine how long a page-latch acquisition sleeps. Every nonzero lock-wait policy—finite or infinite—uses the hidden `page_latch_timeout_in_msecs`, default 300,000 ms. The transaction lock policy affects what error/abort is produced after that internal timeout. [`pgbuf_timed_sleep`, `page_buffer.c:7213-7378`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L7213-L7378) [`PRM_ID_PAGE_LATCH_TIMEOUT_IN_MSECS`, `system_parameter.c:5340-5351`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/base/system_parameter.c#L5340-L5351)
- **[FACT]** PostgreSQL and MySQL/InnoDB separate user-visible lock acquisition deadlines from internal latches. Neither applies `lock_timeout`/`innodb_lock_wait_timeout` to buffer-page latches, lightweight locks, mutexes, or rw-locks. Internal deadlock avoidance is instead built from ordering, short critical sections, conditional try/retry, and invariant watchdogs. PostgreSQL's stuck spinlock timeout and InnoDB's semaphore watchdog are fatal bug detectors, not transaction timeouts. Sources are traced below.
- **[INFERENCE]** PR #7630 is a localized symptom mitigation, not the root design fix. It makes two disk metadata fixes ignore both zero-wait values. It leaves the transaction-to-latch coupling everywhere else, and it also weakens the semantic distinction between user no-wait (`LK_ZERO_WAIT`) and the engine's deliberate, silent deadlock-avoidance policy (`LK_FORCE_ZERO_WAIT`).
- **[RECOMMENDATION]** Separate the policies and restore locality at the page-buffer module seam. Make `PGBUF_LATCH_CONDITION` authoritative at `pgbuf_fix`/ordered-fix admission, including its wait and error invariants. Replace uses of transaction `wait_msecs` as an implicit latch-admission policy with typed latch operations such as wait, try, and ordered retry. Keep transaction lock timeout solely in the lock-manager/transaction module.
- **[RECOMMENDATION]** Do **not** choose “1 second versus 300 seconds” as one universal latch acquisition deadline. One second is a deadlock-polling/default-detection interval in the compared systems, not a precedent for aborting latch acquisition. Preserve 300 seconds temporarily only as a compatibility watchdog while splitting it into separately named warning and fatal/progress-watchdog controls. Ordinary latch correctness should come from ordering and explicit conditional retry, not a recoverable global timeout.

## Method and revision control

The survey used local source as primary evidence, then used official in-tree manuals and comments to establish intended semantics. It traced the acquisition call paths, not merely parameter definitions. No source tree was modified.

Evidence labels have strict meanings: **[FACT]** is directly supported by cited source; **[INFERENCE]** is a conclusion drawn from those facts; **[RECOMMENDATION]** is proposed policy; **[UNRESOLVED]** requires further evidence. A label applies to its paragraph and any immediately following explanatory list, table, or diagram until the next labeled claim.

| Repository | Exact revision | Worktree state before research |
|---|---|---|
| CUBRID | `d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530` | clean; branch `CBRD-27198_disk-reserve-sectors-assert-on-page-timeout` |
| PostgreSQL | `fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc` | tracked files clean; pre-existing untracked `.omc/` |
| MySQL | `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8` | clean; branch `trunk` |
| CUBRID manual | `3b6ae97bfbdc664b010ffa933ded5a05b291ae03` | clean |
| Documentation output repository | `4c81af523d63179803daa76e7d6fddf9e1bc881f` | pre-existing unrelated untracked `code-analysis/page-buffer-subsystem-centered-on-the-complete-lifecycle-and-cal/` preserved |

**[UNRESOLVED]** Because the local CUBRID worktree did not contain remote PR HEAD `bd5c43c`, line-level CUBRID citations below intentionally anchor to local `d9ceb53`. The remote patch audit establishes semantic equivalence of the relevant code, but the two revisions must not be represented as identical.

## Terms that must not be collapsed

| Mechanism | Meaning | Typical outcome |
|---|---|---|
| Acquisition deadline | Maximum time one lock request may remain queued | Recoverable statement/transaction error |
| Immediate `NOWAIT` / conditional try | Do not queue if currently unavailable | “Would block” result immediately |
| Deadlock polling/detection interval | When to run an expensive wait-for-cycle check | Select victim if a cycle exists; not a wait limit |
| Warning threshold | When to emit diagnostics for a suspiciously long internal wait | Log/telemetry; wait may continue |
| Fatal watchdog | Time/condition after which an internal invariant is considered broken | PANIC/crash/abort for diagnosis; not normal flow control |

The values “1 second,” “50 seconds,” “300 seconds,” and “600 seconds” below control different rows of this table. Comparing their numbers without comparing their semantics would produce the wrong design.

## CUBRID: transaction lock policy leaks into page-latch admission

### The documented policy is transaction-lock waiting

**[FACT]** `LOG_TDES::wait_msecs` is documented in source as the wait policy “for locks.” The public `lock_timeout` parameter defaults to `-1`, permits `-1` as its minimum, and is session/client/user changeable. [`LOG_TDES::wait_msecs`, `log_impl.h:474-487`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/transaction/log_impl.h#L474-L487) [`lock_timeout` registration, `system_parameter.c:1345-1355`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/base/system_parameter.c#L1345-L1355)

The manual independently calls it “Transaction Lock Timeout”: `-1` waits indefinitely, `0` does not wait, and a positive value limits transaction-lock waiting. It lists `deadlock_detection_interval_in_secs` separately, with a 1-second default. [`config.rst:1089-1112`, manual 3b6ae97](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/admin/config.rst#L1089-L1112) [`config.rst:1148-1152`, manual 3b6ae97](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/admin/config.rst#L1148-L1152) [`transaction.rst:1172-1193`, manual 3b6ae97](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/sql/transaction.rst#L1172-L1193)

The internal values are:

- `LK_ZERO_WAIT = 0`: immediate failure, with lock-timeout error;
- `LK_INFINITE_WAIT = -1`: wait indefinitely;
- `LK_FORCE_ZERO_WAIT = -2`: immediate failure without setting the usual error, used by engine code to probe/avoid deadlock.

[`LK_WAIT_MSECS`, `lock_manager.h:55-63`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/transaction/lock_manager.h#L55-L63) [`xlogtb_reset_wait_msecs`, `log_tran_table.c:2537-2570`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/transaction/log_tran_table.c#L2537-L2570)

**[FACT]** The public parameter cannot select `-2` because its lower bound is `-1`; `LK_FORCE_ZERO_WAIT` is therefore an internal policy, not another spelling of user `lock_timeout=0`. [`lock_timeout` registration, `system_parameter.c:1345-1355`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/base/system_parameter.c#L1345-L1355)

### Actual heavyweight/object lock path

```text
lock request conflicts
  ├─ tdes.wait_msecs == LK_ZERO_WAIT       → fail now + timeout error
  ├─ tdes.wait_msecs == LK_FORCE_ZERO_WAIT → fail now, intentionally quiet
  └─ otherwise
       → lock_suspend()
       → waiter tracked with start time + lockwait_msecs
       → deadlock daemon wakes on timeout/interrupt/victim
```

The lock manager implements the three branches directly. It refuses to suspend while an unsafe page latch is held, queues a finite/infinite waiter, and distinguishes timeout, deadlock victim, and interrupt on wakeup. [`lock_suspend`, `lock_manager.c:2320-2497`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/transaction/lock_manager.c#L2320-L2497) [`lock_internal_perform_lock_object`, immediate branches, `lock_manager.c:3793-3824`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/transaction/lock_manager.c#L3793-L3824) [`lock_internal_perform_lock_object`, suspend result, `lock_manager.c:4072-4104`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/transaction/lock_manager.c#L4072-L4104)

**[FACT]** The deadlock daemon's 1-second default is not a one-second acquisition deadline. Its loop checks interrupt/expired finite waits frequently and performs the full local deadlock search according to `deadlock_detection_interval_in_secs`. [`lock_manager.c:6051-6137`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/transaction/lock_manager.c#L6051-L6137) [`lock_force_timeout_expired_wait_transactions`, `lock_manager.c:7940-8023`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/transaction/lock_manager.c#L7940-L8023) [`deadlock_detection_interval_in_secs`, `system_parameter.c:1356-1366`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/base/system_parameter.c#L1356-L1366)

### The page-buffer interface already has the right direct policy axis

**[FACT]** The page-buffer interface explicitly accepts `PGBUF_LATCH_CONDITION`: `PGBUF_UNCONDITIONAL_LATCH` means queue/wait; `PGBUF_CONDITIONAL_LATCH` means try immediately and reject if busy. [`PGBUF_LATCH_CONDITION`, `page_buffer.h:189-203`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.h#L189-L203) [`pgbuf_block_bcb`, `page_buffer.c:6211-6230`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L6211-L6230)

The design breach occurs at the entry to `pgbuf_fix_internal()`:

```text
caller supplies PGBUF_UNCONDITIONAL_LATCH
                 │
                 ▼
pgbuf_fix_internal() reads transaction LOG_TDES::wait_msecs
                 │
        ZERO or FORCE_ZERO?
          ├─ yes → silently rewrite to PGBUF_CONDITIONAL_LATCH
          └─ no  → preserve caller's latch condition
```

[`pgbuf_fix_internal`, `page_buffer.c:2160-2236`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L2160-L2236)

If the page is busy after that rewrite, `LK_ZERO_WAIT` sets `ER_LK_PAGE_TIMEOUT`; `LK_FORCE_ZERO_WAIT` deliberately stays quiet. [`pgbuf_block_bcb`, `page_buffer.c:6494-6528`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L6494-L6528)

**[INFERENCE]** This makes `PGBUF_UNCONDITIONAL_LATCH` a misleading interface promise: it is only unconditional if implementation state from the lock-manager/transaction module permits it. `LOG_TDES::wait_msecs` leaks across the `pgbuf_fix` admission seam and forces callers that legitimately need an unconditional internal metadata latch to add exceptions, as PR #7630 does.

### What the hidden 300 seconds actually controls

The hidden server parameter `page_latch_timeout_in_msecs` defaults to 300,000 ms and is capped at 3,000,000 ms. It is absent from the public CUBRID manual surveyed here. [`pgbuf_latch_timeout_msecs`, `page_buffer.c:105-108,1639-1649`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L105-L108) [`pgbuf_initialize`, `page_buffer.c:1639-1649`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L1639-L1649) [`PRM_ID_PAGE_LATCH_TIMEOUT_IN_MSECS`, `system_parameter.c:5340-5351`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/base/system_parameter.c#L5340-L5351)

`pgbuf_timed_sleep()` applies it as follows:

| `LOG_TDES::wait_msecs` | Actual latch sleep interval | Active transaction on expiry | Inactive transaction on expiry |
|---|---:|---|---|
| `LK_ZERO_WAIT` | 0 | immediate timeout cleanup if this function is reached | requeue/rearm at zero interval; no total bound |
| `LK_FORCE_ZERO_WAIT` | 0 | immediate, quiet cleanup if this function is reached | requeue/rearm at zero interval; no total bound |
| positive finite lock timeout | hidden latch timeout (300s default), **not the positive value** | `ER_PAGE_LATCH_TIMEDOUT` then `ER_LK_PAGE_TIMEOUT` | requeue/rearm; no total 300s bound |
| `LK_INFINITE_WAIT` | hidden latch timeout (300s default) | timed-out latch treated as invariant failure; debug assertion and unilateral-abort classification | requeue/rearm; no total 300s bound |

[`pgbuf_timed_sleep`, duration selection, `page_buffer.c:7213-7249`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L7213-L7249) [`pgbuf_timed_sleep`, inactive retry, `page_buffer.c:7284-7303`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L7284-L7303) [`pgbuf_timed_sleep`, error classification, `page_buffer.c:7326-7378`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L7326-L7378)

**[FACT]** In the ordinary busy-page path, zero/force-zero has already changed an unconditional request to conditional, so it is rejected before joining the timed-sleep queue. The zero rows above describe `pgbuf_timed_sleep()` itself if reached. For every timeout value, the inactive check precedes error classification and rearms the wait. Worker page-latch sleeps temporarily enable interrupt checking; an interrupt removes the waiter, sets `ER_INTERRUPTED`, and returns failure. [`pgbuf_fix_internal`, `page_buffer.c:2227-2236`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L2227-L2236) [`pgbuf_timed_sleep`, interrupt and inactive paths, `page_buffer.c:7249-7303`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L7249-L7303)

**[FACT]** The page wait queue comments explicitly acknowledge that page-latch deadlocks are not ruled out and say a timed sleep is used so the waiting transaction can become a victim. [`pgbuf_timed_sleep`, `page_buffer.c:7000-7089`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L7000-L7089)

**[FACT]** The same 300-second variable also guards a different condition: waiting for a direct buffer victim/BCB in `pgbuf_allocate_bcb()`. The code describes forgotten-victim vulnerability and asserts that this wait “should not timeout.” [`pgbuf_allocate_bcb`, `page_buffer.c:8112-8185`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L8112-L8185) [`pgbuf_allocate_bcb`, suspend and timeout, `page_buffer.c:8238-8280`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L8238-L8280)

**[INFERENCE]** `page_latch_timeout_in_msecs` is not one coherent user policy. It currently combines at least:

1. an active transaction's recoverable latch-wait cutoff when its lock timeout is positive;
2. a dead-latch/invariant watchdog when its lock policy is infinite;
3. a repeated diagnostic interval, not a total deadline, while a transaction is inactive;
4. a buffer-frame/victim-supply progress watchdog.

Changing this single value to 1 second would change all four behaviors and would therefore be unsafe without first splitting the mechanisms.

### Ordered fix exposes the intended deadlock-avoidance design

`pgbuf_ordered_fix()` chooses unconditional acquisition when the thread holds no other fixed pages and conditional acquisition when it already holds pages. If the conditional attempt fails, it may unfix, reorder, and refix; but it again consults the transaction-derived wait value to decide whether zero-wait should unwind immediately. [`pgbuf_ordered_fix`, condition choice, `page_buffer.c:12177-12267`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L12177-L12267) [`pgbuf_ordered_fix`, failure/retry, `page_buffer.c:12313-12360`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L12313-L12360)

**[FACT]** Existing callers use `LK_FORCE_ZERO_WAIT` as an implicit latch operation. Best-space `L1_fix` temporarily installs it around ordered fix and maps contention; B-tree code installs it before a heap lookup while already holding a B-tree latch specifically to avoid a dead latch. [`bestspace::L1_fix`, `bestspace.cpp:672-703`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/bestspace.cpp#L672-L703) [`btree_get_statistics`, `btree.c:19757-19778`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/btree.c#L19757-L19778)

**[INFERENCE]** This is further evidence that the missing abstraction is a typed latch policy/result at the page-buffer interface, not another timeout number. Using illustrative names, an internal caller should request `TRY` or `ORDERED_RETRY` directly and receive `WOULD_BLOCK`; it should not mutate a transaction-lock field so page-buffer code guesses what the caller meant.

### PR #7630 behavior and limits

At local `d9ceb53`, the patch adds a thread-local scoped flag. `pgbuf_find_current_wait_msecs()` normally reads the shared transaction descriptor, but while that flag is set it maps either zero-wait value to `LK_INFINITE_WAIT`; positive and infinite values are unchanged. The stated reason for thread-local state is that parallel workers may share a transaction descriptor, making mutation of `LOG_TDES::wait_msecs` racy. [`pgbuf_set_force_latch_wait`, `page_buffer.c:5305-5339`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L5305-L5339) [`pgbuf_find_current_wait_msecs`, `page_buffer.c:16872-16910`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L16872-L16910) [`THREAD_ENTRY` flag, `thread_entry.hpp:252-260`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/thread/thread_entry.hpp#L252-L260)

Only two disk metadata page fixes are wrapped:

- `disk_get_volheader_internal()` fixes the volume-header page unconditionally; [`disk_manager.c:3218-3247`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/disk_manager.c#L3218-L3247)
- `disk_stab_cursor_fix()` fixes the sector-allocation bitmap page unconditionally. [`disk_manager.c:3497-3525`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/disk_manager.c#L3497-L3525)

For a transaction whose public `lock_timeout=0`, this prevents a busy metadata page from being conditionally rejected. It instead queues the page latch and reaches the existing 300-second watchdog path. This does not add a new 300-second value.

**[FACT]** During sector reservation, the code holds the volume-header page with a write latch while fixing and updating sector-table pages, then releases the header at function exit. [`disk_reserve_sectors_in_volume`, `disk_manager.c:4075-4167`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/disk_manager.c#L4075-L4167)

```text
hold volume-header WRITE latch
        │
        ├─ scan/fix sector-table page
        │       └─ if busy after PR: wait in BCB queue
        │
        └─ release volume-header latch only at common exit
```

**[INFERENCE]** The patch fixes the immediate false “would block” error for these pages, but a blocked sector-table acquisition now retains the volume-header write latch. That can create a volume-wide convoy. A cycle is possible if any holder of the sector page needs the header before release, but this survey did not prove such a current call path; it remains a lock-order audit item, not a claimed confirmed deadlock.

The error cleanup explains why the original special case surfaced as an assertion: partial reservations are undone, while only interrupts and a small set of I/O errors are classified as expected; other failures assert and invoke disk checking/retry behavior. [`disk_reserve_sectors`, cleanup, `disk_manager.c:4380-4457`, d9ceb53](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/disk_manager.c#L4380-L4457)

**[FACT]** The three local PR commits change only source implementation files and add no tests (`afb93e4ef`, `623357410`, `8d036fc6b`).

**[INFERENCE]** The flag is a defensible thread-safety mechanism for an interim scoped exception. It is still an abstraction patch around a global coupling: all other unconditional page fixes remain subject to transaction no-wait demotion, and these two sites now also override deliberate internal `LK_FORCE_ZERO_WAIT`.

## PostgreSQL: user lock deadline is isolated from internal synchronization

### Heavyweight locks

**[FACT]** PostgreSQL `lock_timeout` applies to each attempt to acquire table, index, row, and other database-object locks, only while waiting. Its default is zero (disabled). `deadlock_timeout` defaults to 1 second and means how long to wait before running a deadlock check; it also gates lock-wait logging. [`lock_timeout`, `guc_parameters.dat:1616-1624`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/utils/misc/guc_parameters.dat#L1616-L1624) [`config.sgml:10767-10801`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/doc/src/sgml/config.sgml#L10767-L10801) [`deadlock_timeout`, `guc_parameters.dat:626-634`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/utils/misc/guc_parameters.dat#L626-L634) [`config.sgml:11712-11754`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/doc/src/sgml/config.sgml#L11712-L11754)

```text
LockAcquire(dontWait)
  ├─ conflict + dontWait → LOCKACQUIRE_NOT_AVAIL immediately
  └─ conflict + wait
       → ProcSleep()
       → arm deadlock timer and, independently, lock_timeout timer
       → latch wait + CHECK_FOR_INTERRUPTS
       → grant | deadlock victim | cancellation | lock-timeout error
```

[`LockAcquireExtended`, `lock.c:780-813,1102-1254`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/storage/lmgr/lock.c#L780-L813) [`WaitOnLock`, `lock.c:1934-2018`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/storage/lmgr/lock.c#L1934-L2018) [`ProcSleep`, `proc.c:1380-1534`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/storage/lmgr/proc.c#L1380-L1534)

The timeout handler sends an interrupt; the main interrupt path distinguishes lock timeout from statement timeout and reports different SQL errors. [`ProcSleep`, timer cleanup, `proc.c:1757-1778`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/storage/lmgr/proc.c#L1757-L1778) [`ProcessInterrupts`, `postgres.c:3575-3612`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/tcop/postgres.c#L3575-L3612) [`LockTimeoutHandler`, `postinit.c:1411-1443`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/utils/init/postinit.c#L1411-L1443)

### LWLocks and buffer content locks

PostgreSQL's in-tree lock-manager design document distinguishes:

- spinlocks: extremely short critical sections, stuck acquisition eventually PANICs;
- LWLocks: internal shared-memory locks, normally OS-semaphore-backed when contended, no deadlock detection and no timeout;
- heavyweight locks: user-visible database-object locking with deadlock/timeout machinery.

[`src/backend/storage/lmgr/README:6-45`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/storage/lmgr/README#L6-L45)

**[FACT]** `LWLockAcquire()` holds off interrupts, spins/queues/sleeps until the lock becomes available, and has no transaction timeout. `LWLockConditionalAcquire()` is the explicit immediate try interface. [`LWLockAcquire`, `lwlock.c:1141-1311`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/storage/lmgr/lwlock.c#L1141-L1311) [`LWLockConditionalAcquire`, `lwlock.c:1313-1361`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/storage/lmgr/lwlock.c#L1313-L1361) [`lwlock.h:116-118`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/include/storage/lwlock.h#L116-L118)

At this revision, a buffer content lock is a specialized lock encoded in buffer state rather than literally an LWLock, but it follows the same separation. `BufferLockAcquire()` waits without a timeout while interrupts are held; `BufferLockConditional()` tries immediately. [`BufferDesc`, `buf_internals.h:303-310`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/include/storage/buf_internals.h#L303-L310) [`BufferLockAcquire`, `bufmgr.c:5902-6031`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/storage/buffer/bufmgr.c#L5902-L6031) [`BufferLockConditional`, `bufmgr.c:6062-6107`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/storage/buffer/bufmgr.c#L6062-L6107)

**[FACT]** PostgreSQL prevents internal cycles by design: buffer mapping partition locks are ordered; some buffer paths use conditional content-lock acquisition specifically to avoid deadlock, release the victim, and retry. [`storage/buffer/README:123-142`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/storage/buffer/README#L123-L142) [`bufmgr.c:2589-2610`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/storage/buffer/bufmgr.c#L2589-L2610) [`bufmgr.c:4330-4344`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/storage/buffer/bufmgr.c#L4330-L4344)

Spinlock acquisition has a roughly minute-scale stuck-lock PANIC guard, but comments require a spinlock to be held for only a few instructions. [`spin.h:13-29`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/include/storage/spin.h#L13-L29) [`s_lock.c:57-91`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/storage/lmgr/s_lock.c#L57-L91) [`s_lock.c:123-165`, fd2b898](https://github.com/postgres/postgres/blob/fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc/src/backend/storage/lmgr/s_lock.c#L123-L165)

**[INFERENCE]** Even if a statement-timeout signal arrives while a backend is blocked on an internal latch, `HOLD_INTERRUPTS()` defers processing until a safe point; it is not an internal latch acquisition deadline. PostgreSQL does not let transaction/user timeout state silently change a blocking internal acquisition into a conditional one.

## MySQL/InnoDB: transactional waits, MDL, and internal latches are distinct

### InnoDB transaction locks and server metadata locks

**[FACT]** `innodb_lock_wait_timeout` is an InnoDB record/table lock acquisition timeout in seconds, default 50 and minimum 1; very large values disable it. A deadlock rolls back a transaction, while a lock-wait timeout normally rolls back only the current statement unless `innodb_rollback_on_timeout` is enabled. [`innodb_lock_wait_timeout`, `ha_innodb.cc:1117-1121`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/handler/ha_innodb.cc#L1117-L1121) [`innodb_lock_wait_timeout` lookup, `ha_innodb.cc:1990-1994`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/handler/ha_innodb.cc#L1990-L1994) [`error handling, ha_innodb.cc:2105-2179`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/handler/ha_innodb.cc#L2105-L2179)

InnoDB stores the timeout on its wait slot, releases a dictionary latch before sleeping, and reports timeout, deadlock victim, and interruption separately. Its wait daemon scans timeouts with approximately one-second resolution and separately builds a wait-for graph. [`lock_wait_suspend_thread`, `lock0wait.cc:206-355`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/lock/lock0wait.cc#L206-L355) [`lock_wait_check_slots_for_timeouts`, `lock0wait.cc:465-555`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/lock/lock0wait.cc#L465-L555) [`lock_wait_timeout_thread`, `lock0wait.cc:1377-1460`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/lock/lock0wait.cc#L1377-L1460)

**[FACT]** `NOWAIT` and `SKIP LOCKED` are explicit select modes. A conflicting record lock returns `DB_LOCK_NOWAIT`/`DB_SKIP_LOCKED`; it does not derive this behavior from an internal latch timeout. [`SELECT_MODE`, `lock0types.h:47-51`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/include/lock0types.h#L47-L51) [`lock_rec_lock_slow`, `lock0lock.cc:1717-1810`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/lock/lock0lock.cc#L1717-L1810)

MySQL's server-level `lock_wait_timeout` is a separate, extremely long-default lock timeout used by metadata locking. The MDL path turns timeout zero into a try-lock, otherwise computes an absolute deadline, checks kill state, and performs immediate deadlock detection. [`lock_wait_timeout`, `sys_vars.cc:2381-2385`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/sql/sys_vars.cc#L2381-L2385) [`LONG_TIMEOUT`, `sql_const.h:160`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/sql/sql_const.h#L160) [`MDL_wait::timed_wait`, `mdl.cc:1796-1851`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/sql/mdl.cc#L1796-L1851) [`MDL_context::acquire_lock`, `mdl.cc:3352-3540`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/sql/mdl.cc#L3352-L3540)

### Page rw-locks and mutexes

Buffer-page acquisition calls InnoDB rw-lock operations and records the acquired latch in the mini-transaction memo. Normal S/X acquisition spins, reserves a sync-array cell, sleeps on an event, and repeats without consulting `innodb_lock_wait_timeout`. Optimistic paths explicitly call `rw_lock_*_lock_nowait()` and unfix/return false on contention. [`mtr_add_page`, `buf0buf.cc:4148-4179`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/buf/buf0buf.cc#L4148-L4179) [`buf_page_optimistic_get`, `buf0buf.cc:4512-4582`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/buf/buf0buf.cc#L4512-L4582) [`rw_lock_s_lock_func`, `sync0rw.cc:273-345`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/sync/sync0rw.cc#L273-L345) [`rw_lock_x_lock_func`, `sync0rw.cc:573-641`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/sync/sync0rw.cc#L573-L641)

**[FACT]** The sync-array event wait itself has no transaction deadline or transaction-kill check; interruption is handled in record/MDL wait managers, not in this internal rw-lock/mutex wait. The sync cell records reservation time and lock identity for diagnostics. Debug latch-level checking enforces acquisition order. [`sync_array_reserve_cell`, `sync0arr.cc:180-239`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/sync/sync0arr.cc#L180-L239) [`sync_array_wait_event`, `sync0arr.cc:307-343`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/sync/sync0arr.cc#L307-L343) [`sync_check_lock_validate`, `sync0debug.cc:167-210`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/sync/sync0debug.cc#L167-L210)

### Internal semaphore warning/deadlock/fatal watchdog

InnoDB does monitor internal waits, but with intentionally different outcomes from record-lock timeout:

- the sync array can infer internal wait-for edges and treats a detected semaphore deadlock as fatal; it acknowledges possible false negatives;
- the error monitor checks about once per second;
- a long waiter gets diagnostics after a hard-coded four-minute warning threshold;
- the default fatal semaphore wait threshold is 600 seconds, followed by repeated confirmation before fatal termination.

[`sync0arr.cc:73-82,281-305`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/sync/sync0arr.cc#L73-L82) [`sync_array_detect_deadlock`, `sync0arr.cc:450-682`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/sync/sync0arr.cc#L450-L682) [`sync_array_print_long_waits`, `sync0arr.cc:781-901`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/sync/sync0arr.cc#L781-L901) [`srv_error_monitor_thread`, `srv0srv.cc:1827-1897`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/srv/srv0srv.cc#L1827-L1897) [`srv_fatal_semaphore_wait_threshold`, `srv0srv.cc:121-127`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/srv/srv0srv.cc#L121-L127)

The configurable 600-second “semaphore wait timeout” is exposed only in debug builds and explicitly describes a server crash, not a transaction error. [`innodb_semaphore_wait_timeout_debug`, `ha_innodb.cc:22287-22293`, 06a5c1c](https://github.com/mysql/mysql-server/blob/06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8/storage/innobase/handler/ha_innodb.cc#L22287-L22293)

**[INFERENCE]** MySQL provides useful precedent for separating internal wait telemetry and fatal invariant enforcement from ordinary record/MDL lock deadlines. It does not provide precedent for making an internal page latch fail after one second or after `innodb_lock_wait_timeout`.

## Cross-database comparison

| Concern | CUBRID at d9ceb53 | PostgreSQL at fd2b898 | MySQL at 06a5c1c |
|---|---|---|---|
| Transaction/object lock acquisition deadline | `LOG_TDES::wait_msecs`; public `lock_timeout` | `lock_timeout`, armed only in heavyweight `ProcSleep` | `innodb_lock_wait_timeout` for InnoDB locks; server `lock_wait_timeout` for MDL |
| Immediate nonblocking request | `LK_ZERO_WAIT`, internal quiet `LK_FORCE_ZERO_WAIT` | heavyweight `dontWait`; explicit conditional LW/buffer-lock APIs | record `NOWAIT`/`SKIP LOCKED`; MDL timeout 0; explicit rw-lock nowait |
| Internal page-latch ordinary wait | Hidden 300s timed sleep, with behavior classified by transaction lock policy | waits without lock timeout; interrupts deferred | waits without transaction lock timeout |
| Internal cycle avoidance | ordered fix and conditional mode exist, but transaction field also silently controls them | documented ordering, conditional acquisition, release/retry | latch levels/order checking, nowait optimistic algorithms; internal semaphore deadlock detector is fatal |
| Deadlock detection interval | object-lock daemon default 1s; page latch not integrated into the same recoverable WFG | heavyweight default 1s; no LW/buffer-latch detector | InnoDB transaction WFG daemon roughly 1s; MDL immediate; internal semaphore cycle fatal |
| Internal warning/watchdog | 300s knob conflates active cutoff, assertion/abort, inactive repeat, BCB victim progress | stuck spinlock roughly minute -> PANIC; no LW/buffer timeout | warning after 4m, fatal threshold default 600s with confirmation |
| Does user lock timeout demote an internal blocking latch to try-lock? | **Yes** | **No** | **No** |

## Design options for CUBRID

| Option | Benefit | Cost/risk | Judgment |
|---|---|---|---|
| A. Merge PR #7630 unchanged and stop | Repairs known two-page symptom with small diff | Coupling remains; overrides `LK_FORCE_ZERO_WAIT`; no tests; possible header-latch convoy | Insufficient as a root fix |
| B. Change hidden latch timeout from 300s to 1s | Detects stalls quickly | Turns scheduler/I/O stalls into transaction failures/assertions; also changes BCB victim watchdog; no peer precedent | Reject |
| C. Apply positive `lock_timeout` directly to page latches | Numerically consistent | Makes an internal correctness primitive user-configurable; can expose partial-operation failures | Reject |
| D. Remove all page-latch deadlines and wait forever | Clear separation | Existing code admits potential latch cycles; inactive waits already effectively repeat; failures could hang silently | Unsafe before ordering audit/telemetry |
| E. Restore locality at the `pgbuf_fix`/ordered-fix seam: make `PGBUF_LATCH_CONDITION` authoritative and migrate implicit `wait_msecs` uses | Deepens the page-buffer module, preserves caller intent, and matches peers | Requires call-site audit and compatibility staging | Recommended root design |
| F. Split admission, warning, and fatal/progress watchdogs | Each number gains one meaning; better diagnostics | More state and operational knobs | Recommended with E |
| G. Add page-latch waits to a recoverable global WFG | Can choose a victim rather than wait for watchdog | Complex: holders/ownership, nested pages, rollback safety; victim may itself require latches | Possible long-term research, not smallest change |

### Smallest safe next change

**[RECOMMENDATION]** Treat PR #7630 as an interim compatibility patch, but narrow the scoped override to **user** `LK_ZERO_WAIT` only. Preserve `LK_FORCE_ZERO_WAIT` as an engine-authored “do not queue, stay quiet” instruction. Add a deterministic contention test before merge. This repairs the reproduced `lock_timeout=0` disk-reservation symptom without silently defeating existing dead-latch-avoidance probes.

The immediate patch should also record telemetry when its special override causes an actual wait while the volume-header write latch is held. This makes convoy exposure measurable rather than speculative.

**[UNRESOLVED]** If product requirements explicitly say that even engine-installed `LK_FORCE_ZERO_WAIT` must never affect these exact two disk pages, that behavior can remain—but only after an audit proves no path relies on the quiet probe to break a header↔sector or B-tree/heap cycle. Current source alone does not prove that safety property.

### Larger follow-up: repair the interface

1. Introduce or formalize typed page-latch acquisition operations in the page-buffer interface. The identifiers below are illustrative, not existing CUBRID names:

   - `PGBUF_WAIT`: caller has established legal latch order and may queue;
   - `PGBUF_TRY`: never queue, return `PGBUF_WOULD_BLOCK` without manufacturing a lock-timeout error;
   - `PGBUF_ORDERED_RETRY`: page-buffer layer may release/reorder/refix according to a documented algorithm.

2. Make the supplied latch condition authoritative inside `pgbuf_fix_internal()`; delete the silent rewrite from `LOG_TDES::wait_msecs`.
3. Migrate best-space, B-tree, and other `xlogtb_reset_wait_msecs(LK_FORCE_ZERO_WAIT)` users to the typed page-buffer operations.
4. Confine `LOG_TDES::wait_msecs` to object/transaction lock paths. If an operation wants a user-facing overall deadline, pass an explicit operation deadline at a higher layer rather than reading it implicitly in page buffer.
5. Split `page_latch_timeout_in_msecs` into at least:

   - a **warning/telemetry threshold** that never changes control flow;
   - a **fatal dead-latch watchdog** for an invariant violation;
   - a separate **buffer-victim progress watchdog** for `pgbuf_allocate_bcb()`.

6. Document latch order for volume header, sector allocation table, best-space pages, heap pages, and B-tree pages. Use conditional retry at any edge that cannot be globally ordered.

### Numeric policy

**[RECOMMENDATION]** Do not adopt a universal one-second latch timeout. One second should remain a deadlock-detection/polling cadence where applicable, not an acquisition deadline.

The staging must be explicit:

1. **Interim PR stage:** leave the hidden knob and all positive-policy expiry behavior unchanged. The smallest patch therefore does not silently change existing finite `lock_timeout` behavior.
2. **Split stage:** retain 300 seconds initially for separately named **fatal dead-latch** and **BCB progress** watchdogs. Also preserve the current positive-policy recoverable cutoff temporarily behind a separately named compatibility mechanism, so its later removal is an observable and testable behavior change.
3. **Post-audit stage:** after explicit latch policies, ordering tests, and telemetry are in place, remove the recoverable active-transaction page-latch cutoff that is inferred from transaction lock policy. It is a migration value, not evidence that 300 seconds is intrinsically correct.

For ordinary page-latch waits:

- a correctly ordered `PGBUF_WAIT` should wait until progress, with interrupt handling only at a proven safe point;
- an acquisition that could form a cycle should use `PGBUF_TRY`/ordered release-and-retry rather than any elapsed-time guess;
- emit long-wait diagnostics before the fatal watchdog. Choose the initial warning threshold from production latency histograms; if a bootstrap value is unavoidable, 1 second is acceptable only as a **warning**, never as an abort threshold.

This follows both peer systems: PostgreSQL uses no transaction timeout for LW/buffer latches and PANICs on a stuck spinlock invariant; MySQL waits internally, warns on long semaphore waits, and fatally diagnoses internal deadlock/stall separately from transaction lock timeout.

## Required tests and telemetry

### Tests

1. **Policy matrix:** `{LK_ZERO_WAIT, LK_FORCE_ZERO_WAIT, positive, infinite}` × `{conditional, unconditional}` × `{scoped disk override off/on}` under deterministic page contention. Assert queueing, return code, and error stack. Any suggested `WOULD_BLOCK` result name in this report is illustrative, not an existing CUBRID identifier.
2. **Active/inactive expiry:** reduce the test-only latch watchdog and verify active positive timeout, active infinite assertion/abort path, and inactive rearm behavior independently.
3. **Disk metadata contention:** hold the volume-header or sector-table latch in a controlled worker, execute reservation with public `lock_timeout=0`, and verify no false assertion, no leak, correct rollback/unreserve, and eventual progress.
4. **Force-zero regression:** exercise best-space and B-tree/heap callers and prove an internal `LK_FORCE_ZERO_WAIT` still produces the equivalent nonqueueing outcome without unexpected waiting or error pollution.
5. **Ordering/convoy test:** block the sector-table acquisition while the requester holds the volume-header write latch; measure that unrelated volume operations are blocked as expected and establish an upper bound in the test.
6. **Lock-manager isolation:** prove `lock_timeout=0` still makes conflicting object locks fail immediately after the page-buffer redesign.
7. **BCB victim watchdog:** test it independently after its timeout is split from latch acquisition.
8. **Fault injection:** interrupt and error each wait phase; verify latch ownership, waiter removal, partial sector rollback, and error classification.

### Telemetry needed before tuning numbers

- latch wait histograms (`p50`, `p95`, `p99`, `p99.9`, maximum) by acquisition symbol, page type, latch mode, and outcome;
- time spent spinning versus queued, queue length, waiter/holder thread and transaction identifiers;
- all page latches held by a thread when it begins another wait, sufficient to reconstruct ordering edges;
- volume-header hold time and number of requests convoyed behind it;
- conditional-acquisition failure and ordered-retry counts;
- warning, interrupt, active-timeout, inactive-rearm, fatal-watchdog, and BCB-victim-watchdog counts kept separate;
- scheduler stall and I/O latency context so infrastructure pauses are not misdiagnosed as latch bugs.

**[RECOMMENDATION]** Tune a warning threshold only after observing these distributions in normal and stressed production-like workloads. Set a fatal threshold according to incident-detection/restart policy, not query latency SLO. They are different controls.

## Direct answers to the eight design questions

1. **Does CUBRID currently conflate lock and latch policy? In exactly which mechanisms and call paths?**

   **Yes.** `LOG_TDES::wait_msecs` belongs to transaction/object-lock policy, but `pgbuf_fix_internal()` reads it through `pgbuf_find_current_wait_msecs()` and rewrites unconditional latch admission to conditional for both zero-wait values. `pgbuf_timed_sleep()` reads the same state again to select zero versus the hidden 300-second interval and to classify expiry. `pgbuf_ordered_fix()` reads it a third time to decide whether to unwind or reorder/retry. Best-space and B-tree callers reinforce the coupling by temporarily writing `LK_FORCE_ZERO_WAIT` to obtain latch behavior.

2. **Does PR #7630 correct the root abstraction or bypass it at two call sites?**

   It bypasses it at two call sites. A thread-local flag makes the volume-header and sector-table fixes see zero/force-zero as infinite. The lock-manager/transaction implementation state still leaks across the `pgbuf_fix` admission seam everywhere else.

3. **Is its behavior nevertheless correct and safe as an immediate fix?**

   It is correct for the reproduced public `lock_timeout=0` false contention symptom. It is not yet sufficiently demonstrated safe: there are no added contention tests, waiting for a sector page can retain the volume-header write latch and create a convoy, and overriding `LK_FORCE_ZERO_WAIT` may defeat an engine-authored deadlock-avoidance probe. The smallest safer interim behavior overrides only `LK_ZERO_WAIT`, pending a latch-order audit.

4. **What should the target CUBRID architecture be?**

   Page buffer should be the deep module that owns latch admission plus wait/error invariants. `PGBUF_LATCH_CONDITION` should be the single authoritative policy at the `pgbuf_fix`/ordered-fix seam. The interface should expose typed wait, try, and ordered-retry operations/results; the lock-manager/transaction module's `LOG_TDES::wait_msecs` should not cross that seam.

5. **What should happen to the existing 300-second page-latch watchdog?**

   Do not merely delete or retune it. The interim PR should preserve all current behavior. In the root follow-up, split its four roles into a warning/telemetry threshold, a fatal dead-latch watchdog, an independent BCB victim-progress watchdog, and a temporary explicitly named compatibility cutoff for current positive-policy behavior. After the latch-order audit and migration, remove the recoverable active-transaction cutoff inferred from transaction lock policy. Retain 300 seconds initially for compatible fatal/progress behavior until telemetry justifies separate values.

6. **Should any 1-second value be introduced? If yes, what does it control?**

   Not as a latch acquisition deadline. One second is peer precedent for deadlock-check/poll cadence. If an early diagnostic is operationally useful, it may bootstrap a warning-only telemetry event, with no change to waiting or error control flow; its final value must be measurement-driven.

7. **What is the smallest safe next change?**

   Narrow the PR override to public `LK_ZERO_WAIT`, preserve `LK_FORCE_ZERO_WAIT`, and add deterministic disk-metadata contention plus force-zero regression tests. Record whether the special wait occurs while the volume-header write latch is held.

8. **What larger follow-up work, tests, and telemetry are required?**

   Restore locality at the page-buffer seam, migrate implicit force-zero callers to typed latch operations, document/audit latch order, split watchdog roles, and consider a recoverable latch wait-for graph only as later research. Run the policy, active/inactive, disk contention, force-zero, convoy, lock-manager-isolation, BCB, and fault-injection tests above; collect per-site wait histograms, ownership/order edges, queue/convoy data, retry counts, and separated warning/timeout/watchdog outcomes.

## Verification performed

- Captured exact SHA, branch, and dirty status for CUBRID, PostgreSQL, MySQL, the CUBRID manual, and the documentation repository.
- Queried GitHub PR #7630 metadata read-only; compared local CUBRID HEAD with remote PR HEAD without fetch, checkout, or source mutation.
- Audited the remote PR patch after local `d9ceb53` and confirmed only comment/constant-spelling deltas in the relevant behavior.
- Traced CUBRID object-lock suspension, zero-wait branches, deadlock daemon, latch condition rewrite, timed sleep, active/inactive handling, ordered fix, BCB victim wait, PR scoped override, disk reservation latch ownership, and cleanup.
- Traced PostgreSQL heavyweight lock timers and interrupts, LWLock/buffer content lock blocking and conditional paths, ordering rules, and stuck-spinlock guard.
- Traced MySQL/InnoDB record-lock/MDL timeouts, NOWAIT/SKIP LOCKED, page rw-lock/sync-array waits, internal deadlock detection, warning threshold, and fatal semaphore watchdog.
- Inspected the local PR commit stats and found no added tests.
- Searched `/home/vimkim/gh/my-cubrid-docs` and `/home/vimkim/gh/my-cubrid-jira` for existing CBRD-27198 context, then independently verified conclusions against source.
- Did not build or execute database tests because this was a read-only design survey and no source changes were made.
