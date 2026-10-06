# CBRD-27512 / PR #8095: necessity and behavioral correctness review

**Verdict: the change is justified and proportionate as an interruption-safety regression fix. No newly introduced implementation defect was found in the reviewed paths.** It restores the caller's interruption policy, while deliberately reducing cancellation responsiveness inside protected operations. Timeout-safe cleanup remains separate work.

This is a source-level review. Native reproductions, builds, benchmarks, crash injection, and replication tests were not run by this review. Manual test outcomes in the PR description are author-reported evidence, not independently reproduced results.

## Review identity and scope

| Item | Value |
|---|---|
| Reviewed PR | [CUBRID/cubrid #8095](https://github.com/CUBRID/cubrid/pull/8095) |
| Issue | [CBRD-27512](http://jira.cubrid.org/browse/CBRD-27512) |
| Reviewed head | `89817b52beac79caa5184748350f4ab42d23c641` |
| Diff base / merge-base | `15e7dc8b5b56fd8751d56ccae1fdf87d315bd35d` |
| Target branch snapshot | `develop` at `67bea1201e6e3be640fff347a4a745f4fcd3ff38` |
| Change | One file, eleven deleted lines in `src/storage/page_buffer.c` |
| Review date | 2026-10-06 |
| Reviewer | Codex, with an independent storage/recovery source review |

The target branch snapshot had advanced beyond the head's parent. GitHub's compare API confirmed that the merge-base was `15e7dc8b5...` and the PR diff contained only this one commit and deletion. Source links below are pinned to the reviewed head, unless explicitly marked as the base.

Scope: necessity, requirement fidelity, user-visible behavior, concurrency, storage consistency, atomicity, isolation, durability, recovery, and replication/HA implications. Formatting, naming, and mechanical standards checks are excluded. No engine code was changed and no formal GitHub approval is implied by this report.

## Contract reconstructed from the evidence

The requirements and evidence must be distinguished:

| Type | Contract or observation | Evidence |
|---|---|---|
| Current issue requirement | Fix the server crash during temporary-file destruction in `bug_bts_6938`. | [CBRD-27512](http://jira.cubrid.org/browse/CBRD-27512) |
| Established storage invariant | Temporary-file destruction must not be interrupted, because interrupted destruction leaks pages. | [file_manager.c:4130–4133](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/file_manager.c#L4130-L4133) |
| Related feature requirement | Allow killtran/client termination to end `THREAD_PGBUF_SUSPENDED` waits, and show those waits as `WAIT`. | [CBRD-26295](http://jira.cubrid.org/browse/CBRD-26295) |
| Explicitly accepted tradeoff | Respecting the caller's mask partially restores the old cancellation behavior; the issue discussion prioritizes the regression fix. | CBRD-27512, assignee comment dated 2026-10-02 |
| Review inference | The general buffer wait must not override a caller's deliberate protection unless the caller can safely handle interruption. | The failure path and other protected callers described below |
| Open decision | Which affected release branches should receive the fix? | CBRD-27512 requests a backport assessment; this review establishes no backport decision |

CBRD-26295's original cancellation requirement is broader than the behavior retained by this patch. Therefore, the appropriate conclusion is a justified, intentional partial retreat from that feature, rather than unconditional preservation of all cancellation behavior.

## Why a change was necessary

The original behavior violates an existing cleanup invariant:

1. `file_temp_retire_internal()` removes a temporary file's entry from its transaction list. If the file is not cached, it then destroys the file. [file_manager.c:4490–4506](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/file_manager.c#L4490-L4506)
2. `file_destroy(..., true)` disables interrupts, explicitly to avoid page leaks. [file_manager.c:4130–4133](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/file_manager.c#L4130-L4133)
3. It invalidates temporary pages, decreases temporary-file statistics, and invalidates/unfixes the file header before returning its disk sectors. [file_manager.c:4248–4311](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/file_manager.c#L4248-L4311)
4. Sector return needs write latches on the volume header and sector-table pages. These are shared between sessions, so a query-private temporary file can still encounter shared-page contention. [disk_manager.c:4828–4843](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/disk_manager.c#L4828-L4843)
5. At the base revision, `pgbuf_timed_sleep()` temporarily forces `check_interrupt=true` for `TT_WORKER`, overriding the caller's protection. [Base page_buffer.c:7251–7270](https://github.com/CUBRID/cubrid/blob/15e7dc8b5b56fd8751d56ccae1fdf87d315bd35d/src/storage/page_buffer.c#L7251-L7270)
6. Disconnect processing may wake the suspended worker when that flag is true. Shutdown has a corresponding flag gate. [network_sr.c:961–981](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/communication/network_sr.c#L961-L981), [server_support.c:2177–2187](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/connection/server_support.c#L2177-L2187)
7. An interrupt wake makes the latch wait fail with `ER_INTERRUPTED`; sector return fails and reaches `file_destroy()`'s assertion. [page_buffer.c:7266–7276](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/page_buffer.c#L7266-L7276), [file_manager.c:4311–4315](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/file_manager.c#L4311-L4315)

The reported stack is consistent with this chain. The exact triggering interleaving was not reproduced independently here.

```text
Session A                    Session B                         Disconnect/shutdown
holds volume-header latch    starts temporary-file cleanup
                             disables interruption
                             invalidates pages/header
                             waits for shared header latch
                             BASE: enables interruption        wakes B
                             sector return fails
                             assertion / incomplete cleanup

                             HEAD: retains disabled mask       leaves B waiting
releases header latch        obtains latch
                             completes sector return
                             restores caller's mask
```

The lower half assumes the latch is released before a failing watchdog expiry or other error. The patch does not make every cleanup failure impossible.

### Why this implementation is proportionate

Removing only the assertion would leave storage allocated after ownership/tracking information has been discarded. Retrying destruction from its beginning is not established as safe after partial destruction; it would require retaining progress and metadata.

A special case for `file_destroy()` would also leave the same contradiction in other protected paths:

| Protected path | Reason or effect | Source |
|---|---|---|
| Temporary allocation | No rollback; temporary changes are not logged. | [file_manager.c:8719–8735](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/file_manager.c#L8719-L8735) |
| Temporary-file reset | Interruption can ruin the file. | [file_manager.c:9034–9038](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/file_manager.c#L9034-L9038) |
| Temporary partial-allocation rollback | Reverts unlogged allocation while interrupts are disabled. | [disk_manager.c:4393–4403](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/disk_manager.c#L4393-L4403) |
| UPDATE/DELETE duplicate-elimination hash cleanup | Failure leaks reserved sectors. | [query_executor.c:10387–10400](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/query/query_executor.c#L10387-L10400) |
| Internal B-tree deletion | Traversal/mutation explicitly wraps an interruption-disabled region. | [btree.c:34533–34541](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/btree.c#L34533-L34541) |

Making all these operations safely interruptible would require a larger design involving undo or resumable cleanup. Restoring the existing caller policy is the smallest consistent fix supported by this review. That does not prove every existing mask is optimally scoped.

## User behavior and concurrency

| Situation | Before the patch | After the patch |
|---|---|---|
| Active worker, mask already true | Cancellation handlers can wake a page-latch wait. | Same behavior. |
| Active worker, mask deliberately false | Timed read/write wait overrides the mask, allowing cancellation to interrupt protected work. | Cancellation handlers respect the mask; the waiter normally continues after latch grant. |
| Non-active transaction, such as rollback/postpone | Cancellation checks suppress interruption; watchdog expiry retries. | Same transaction-state rules. |
| Non-`TT_WORKER` context | Removed override did not apply. | No change from this deletion. |
| FLUSH wait | Uses a separate suspension path. | Unchanged by this deletion. |

Worker contexts start with interruption enabled. The ordinary interrupt-enabled behavior remains supported by the wakeup handlers. Successful latch grants still return normally, and the patch changes neither latch acquisition order nor waiter queue handling. The suspension primitive loops on its resume predicate, so a condition-variable spurious wake alone is not treated as cancellation. [thread_entry.cpp:112](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/thread/thread_entry.cpp#L112), [thread_entry.cpp:574–599](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/thread/thread_entry.cpp#L574-L599)

The original mask is restored at common exits from temporary destruction/allocation/reset; the reviewed deletion no longer mutates the nested caller's policy. [file_manager.c:4321–4338](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/file_manager.c#L4321-L4338), [file_manager.c:8955–8962](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/file_manager.c#L8955-L8962), [file_manager.c:9183–9198](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/file_manager.c#L9183-L9198)

The user impact extends beyond cleanup: object-existence and object-null checks also disable interrupts and acquire page latches, and query scans/evaluation call them. A routine query can therefore enter a protected path. [heap_file.c:8798](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/heap_file.c#L8798), [heap_file.c:8922](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/heap_file.c#L8922), [scan_manager.c:6140](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/query/scan_manager.c#L6140), [query_evaluator.c:2212](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/query/query_evaluator.c#L2212)

Longer protected waits can retain workers, concurrency slots, and already-held resources after cancellation is requested. The patch preserves the watchdog rather than resolving all possible latch deadlocks. No quantitative latency or throughput result is established by this review.

## ACID, recovery, and HA assessment

| Aspect | Assessment and boundary |
|---|---|
| Atomicity | Temporary operations rely on completing protected work instead of transaction undo. The patch prevents one class of premature failure; it does not make unlogged temporary operations transactional. |
| Consistency | Prevents interruption-driven incomplete reclamation. No newly introduced double allocation, bitmap inconsistency, or accounting defect was found. |
| Isolation | MVCC visibility, transaction lock rules, and snapshot selection are unchanged. Longer resource retention can affect other sessions' progress. |
| Durability | Log records, page LSAs, storage layouts, and WAL enforcement are unchanged. |
| Statement/transaction rollback and savepoints | No rollback/savepoint records or decision logic change. Non-active rollback/postpone waits retain their existing retry policy. No savepoint scenario was executed. |
| Replication/HA | No replication payload or commit-decision changes were found. Protected waits can delay shutdown, and the separate shutdown deadline can force process exit. No failover or replication scenario was executed. |

### Temporary storage crash points

Temporary sector release immediately clears bitmap bits and updates the free-space cache without transaction logging. A recoverable query interruption before or between these releases can leave space unreachable in the running process after the file header/tracking entry is gone. [disk_manager.c:4899–4910](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/disk_manager.c#L4899-L4910)

A process crash after invalidation but before/during sector return is handled differently: startup resets sector tables in permanent volumes with temporary-data purpose, and temporary volumes are excluded from the normal volume boot-loading path. This restart mechanism does not establish safe in-process retry of interrupted destruction. [disk_manager.c:2462–2484](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/disk_manager.c#L2462-L2484)

### Permanent storage crash points and repeated recovery

| Crash point | Existing recovery mechanism |
|---|---|
| Before permanent destruction executes | `RVFL_DESTROY` records the postponed intention; destruction is performed after commit is confirmed. [file_manager.c:4374–4409](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/file_manager.c#L4374-L4409) |
| During logical destruction | Destruction runs under a system operation. Recovery aborts an interrupted logical operation before completing postpones. Tracker removal has logical undo/compensation. [log_recovery.c:4139–4146](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/transaction/log_recovery.c#L4139-L4146), [file_manager.c:10244–10282](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/file_manager.c#L10244-L10282) |
| After sector-release intention, before physical release | Permanent sector release appends `RVDK_UNRESERVE_SECTORS` postpone records rather than immediately clearing the bits. [disk_manager.c:4892–4897](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/disk_manager.c#L4892-L4897) |
| When physical release executes | The dispatcher logs `LOG_RUN_POSTPONE` before applying the handler, records the reference LSA, and assigns the change's LSA to the page. [log_manager.c:8681–8687](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/transaction/log_manager.c#L8681-L8687), [log_manager.c:3010–3025](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/transaction/log_manager.c#L3010-L3025) |
| Repeated crash after logging/applying release | Analysis tracks remaining postpone work using reference LSAs; redo handles run-postpone records and skips page changes already covered by persisted page LSAs. The bitmap handler alone is not the full idempotence mechanism. [log_recovery.c:1164–1185](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/transaction/log_recovery.c#L1164-L1185), [log_recovery.c:521–571](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/transaction/log_recovery.c#L521-L571) |
| Crash during undo | Compensation records preserve undo progress and participate in redo. [log_manager.c:3146–3161](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/transaction/log_manager.c#L3146-L3161), [log_recovery.c:1222–1231](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/transaction/log_recovery.c#L1222-L1231) |

WAL is still enforced before data-page writes. [page_buffer.c:10746–10750](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/page_buffer.c#L10746-L10750)

None of these records, handlers, formats, or ordering rules changes in this PR. These conclusions describe the source mechanisms inspected, not a proof from crash-injection execution.

## Review follow-ups, separate from new implementation defects

### R1. Correct the universal 300-second wait-bound claim

**Classification: confirmed documentation accuracy issue.** The PR Remarks describe a wait upper bound of `page_latch_timeout_in_msecs` (default 300 seconds). This is not a universal bound on cancellation completion or the whole protected operation:

- The timeout is constructed per timed wait. One operation can encounter several waits, each finishing before its own watchdog expires.
- Inactive transactions retry timeout expiry instead of returning failure.
- Server shutdown uses a separate overall deadline and can call `_exit()` while workers remain.

Evidence: [page_buffer.c:7250–7254](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/page_buffer.c#L7250-L7254), [page_buffer.c:7287–7289](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/page_buffer.c#L7287-L7289), [server_support.c:2325–2329](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/connection/server_support.c#L2325-L2329).

A concrete counterexample to an operation-wide bound is two sequential protected waits, each granted after 200 seconds: neither individual watchdog expires, but cancellation completion takes more than 300 seconds.

Suggested wording: "For active transactions, each timed read/write latch wait normally uses the configured latch watchdog. This does not bound the complete protected operation or cancellation latency. Non-active transaction waits retry on timeout, and shutdown has a separate deadline."

### R2. Preserve deterministic regression verification

**Classification: verification gap, not an observed new code defect.** At the review snapshot, both testcase PRs had zero changed files: [public #3638](https://github.com/CUBRID/cubrid-testcases/pull/3638) and [private #4307](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4307).

The existing `shell/_06_issues/_12_2h/bug_bts_6938` starts 100 JDBC query threads, runs a three-way `db_class` join, kills the client, and stops the service. Its shell assertion checks statdump output before shutdown. It supplies concurrency stress, but does not deterministically synchronize the protected latch wait or explicitly assert sector reclamation. The wider runner may detect a server crash; a passing stress run still does not prove the relevant interleaving occurred.

The PR description reports injected-delay tests, repeated stress runs, release-space checks, and ordinary-wait cancellation. Those results are useful author evidence but were not reproduced independently by this review. No attached committed testcase was found that preserves those focused checks.

### R3. Retain CBRD-27559 as an inherited limitation

**Classification: existing defect, explicitly outside this patch's interruption fix.** An active transaction is still treated as a latch-timeout victim regardless of `check_interrupt=false`. Protected temporary destruction can consequently fail on watchdog expiry. Non-active transactions instead retry. [page_buffer.c:7278–7305](https://github.com/CUBRID/cubrid/blob/89817b52beac79caa5184748350f4ab42d23c641/src/storage/page_buffer.c#L7278-L7305)

[CBRD-27559](http://jira.cubrid.org/browse/CBRD-27559) records this problem and reports reproduction after applying CBRD-27512. Its runtime measurements are issue-author evidence, not execution by this review. The interruption patch should not be presented as eliminating all temporary-cleanup crashes or leaks under prolonged contention.

## Focused verification plan

These tests are proposed, not executed:

| Scenario | Setup and event | Required observations |
|---|---|---|
| Protected temporary destruction | Hold a temporary-purpose volume-header write latch in A. Drive B through uncached temp retirement, confirm its mask is false and it is queued, then disconnect/kill B. Release A before watchdog expiry. | B is not interrupted while protected; destruction finishes; allocated bits/free-space accounting reconcile; the caller's original mask is restored. |
| Protected destruction during shutdown | Same synchronized wait, then initiate shutdown and release A before both relevant deadlines. | Cleanup completes and workers drain without the interruption-driven assertion/leak. |
| Ordinary interrupt-enabled wait | Put B in a timed read/write wait with mask true; disconnect or kill B while queued. | Prompt interruption remains; waiter removal leaves no stale queue entry or leaked latch ownership. |
| Temporary allocation rollback / hash cleanup | Synchronize contention during a protected cleanup path besides destruction. | Protected work finishes and accounting reconciles; nested mask restoration is correct. |
| Existing timeout limitation | Keep A's latch beyond a deliberately shortened watchdog during active protected destruction. | Characterize the inherited failure separately; do not attribute it to this patch. |
| Cancellation latency in query checks | Force a protected object-existence/null-check wait, request cancellation, then release the holder. | Document the accepted responsiveness change and verify later processing handles cancellation according to the surrounding path. |
| Permanent-storage recovery | Crash before/after destruction postpone, during its system operation, and before/after sector-release run-postpone; restart repeatedly. | Tracker/bitmap state follows logged progress, no double release, and committed data/space state remains valid. |

Run debug and release variants for the focused temporary-storage scenarios. Debug survival catches assertions, while release accounting checks are necessary to detect silent leakage. Ensure temp caching does not bypass actual destruction.

## Recommendation and evidence limits

Accept the implementation as a focused regression fix, correct the wait-bound explanation, and preserve repeatable protected/ordinary-wait verification. Track timeout-safe cleanup, any tighter interruption-mask scopes, and backport decisions separately.

The necessity conclusion has strong source support. Absence of a newly introduced defect is bounded by the inspected paths and source reasoning. It does not establish whole-engine ACID correctness, runtime cancellation timing, recovery execution, or failover behavior. CI results were not used as substitutes for these behavioral checks.
