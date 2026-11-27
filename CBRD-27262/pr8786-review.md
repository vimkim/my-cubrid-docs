# Code review: CUBRID/cubrid#8786 (CBRD-27262)

**Goal:** review [CUBRID/cubrid#8786](https://github.com/CUBRID/cubrid/pull/8786), "[CBRD-27262] Give the bcb back its state when a flush fails before the write" (author `hornetmj`). Also check its linked TC PRs.

**Result:** I found no confirmed defect in the reviewed scope.
- **Base behavior:** when a flush failed while encrypting the page (TDE) or getting a DWB slot, the BCB stayed FLUSHING with DIRTY cleared. Synchronous flushers then hung, and the change could later be lost.
- **What the PR does:** it routes these failures through the same cleanup as the existing write-failure path. It also keeps the first-try `oldest_unflush_lsa` across a retry that happens when DWB is disabled mid-flush.
- **What remains:** two low-priority risks that were not executed (R-1, R-2). Both are non-blocking.

## Verdict and follow-up

- **Verdict:** `no-confirmed-findings`.
- **Recommendation:** APPROVE, with two non-blocking comments (R-1, R-2) and one nit (N-1).
- **Follow-up review required:** no. R-1 and R-2 are optional evidence, not merge prerequisites. They are narrow, source-only risks.
  - R-1 needs the server running without its TDE key loaded.
  - R-2 needs two transient failures in a row on the same page, followed by a crash. The base code hung in the same states.

## Snapshot

| Item | Value |
|---|---|
| Repository | CUBRID/cubrid |
| Comparison | `git diff e638a2f224f1cea990c5358da81a0214d249e4b5 7a7a48ac1a0a4e96e51f1d4540ea9bc7f62ae49c` |
| Base (`develop`) / merge base | `e638a2f224f1cea990c5358da81a0214d249e4b5` |
| Head (`CBRD-27262-flush-error-restore`) | `7a7a48ac1a0a4e96e51f1d4540ea9bc7f62ae49c` |
| Patch sha256 | `c7a9eee168277f4436da20e838f4b42a9ad57bc35809b491f99186dc26bea73c` |
| Changed files | `src/storage/page_buffer.c` (+40/-17). No renames, deletions, submodules or binaries. |
| Snapshot | 2026-11-27. I rechecked the base and head at 04:06Z and they had not changed. |
| Linked TC PRs | Two TC PRs, both draft with 0 changed files: [cubrid-testcases#4507](https://github.com/CUBRID/cubrid-testcases/pull/4507), and #5203 in the private testcase repository. |

The head has two commits: `64ac0e4031` (the code change) and `7a7a48ac1a` (comments only).

## What changed

All changes are in [`pgbuf_bcb_flush_with_wal`](https://github.com/CUBRID/cubrid/blob/7a7a48ac1a0a4e96e51f1d4540ea9bc7f62ae49c/src/storage/page_buffer.c#L11617-L11862).

1. **Error routing.** The `tde_encrypt_data_page` and `dwb_set_data_on_next_slot` failures used to `return error` with FLUSHING set and DIRTY cleared. They now `goto error_locked`. The `dwb_add_page` and `fileio_write` failure path now goes there too.
2. **The `error_locked` block.** It runs with the BCB mutex held and does three things:
   - calls `pgbuf_bcb_mark_was_not_flushed (was_dirty)`;
   - restores the saved `oldest_unflush_lsa` when it is non-NULL;
   - wakes the flush waiters (`SERVER_MODE`).
3. **The local `oldest_unflush_lsa`.** It starts NULL and is copied from the BCB only while still NULL. A retry after DWB is disabled mid-flush therefore keeps the first-try value, where base overwrote it with NULL.

## Confirmed findings

None.

## Safety facts and effects outside the diff

| # | Safety fact | Source | Evidence | Result |
|---|---|---|---|---|
| S-1 | At every `goto error_locked`, the BCB mutex is held and `*is_bcb_locked == true`. | First round: caller-held mutex, flag set on entry. Retry: relock before `goto start_copy_page`. Write failure: relock before the goto. | L3 (A, B independently) | Holds |
| S-2 | Callers treat "nonzero return with the BCB locked" as "already reverted", and none of them cleans up again. | Call sites `page_buffer.c:4628`, `9658` (`pgbuf_bcb_safe_flush_internal` and its 9 callers), `13064`. Each unlocks at most once, only when locked. None calls `mark_was_not_flushed`, wakes waiters, or writes `oldest_unflush_lsa`. | L3 (A, B independently, shared question) | Holds |
| S-3 | After the error path, the page is DIRTY again (if it was dirty), and the BCB's `oldest_unflush_lsa` is no later than the oldest change not on disk. | `pgbuf_bcb_mark_was_not_flushed` never clears DIRTY. A first-round failure happens before the BCB LSA is nulled. A retry failure restores the earlier L1 instead of NULL. | L3 (A) | Holds. The windows the PR body lists as pre-existing are out of scope. |
| S-4 | Waking the waiters cannot trip `pgbuf_wakeup_reader_writer` assertions or loop without bound. | `pgbuf_wake_flush_waiters` dequeues only `PGBUF_LATCH_FLUSH` waiters. FLUSHING and the async request are clear afterwards. Checkpoint, discard and invalidate waiters each re-evaluate a bounded number of times. | L3 (A) | Holds |
| S-5 | The BCB cannot change identity between the first try and the retry. | FLUSHING is in the victim-avoid mask. Invalidate rechecks it. Discard waits. | L3 (A, B) | Holds |
| S-6 | The success path is unchanged apart from cost. | One extra NULL store and one compare. On a retry, `logpb_flush_log_for_wal` may run once more, which is a cheap compare when the log is already flushed. | L3 (B) | Holds. Not measured. |
| S-7 | Every error path sets an error. | TDE: `ER_TDE_CIPHER_IS_NOT_LOADED` or `ER_TDE_ENCRYPTION_ERROR`. DWB slot with `can_wait=false`: `ER_DWB_DISABLED`. Write failure: `ER_FAILED`, as in base. | L3 (B) | Holds |

Execution evidence comes from the author, not from this review.
- **Author's tests:** the PR body reports release-build gdb fault injection T1, T2, T4, T5 and T7, run base against head. The scripts are attached to the Jira issue. I did not replay them.
- **CI at head `7a7a48ac1a`:**
  - Pass: release and debug builds, `test_medium`, `test_sql`, `test_sql_by_cci`, and the static checks (license, pr-style, code-style, cppcheck, memory-monitor-check).
  - `test_shell` failed. The PR body attributes it to 30 testcases that also fail on develop because of an unrelated testcase answer change. I did not verify this attribution.
  - The "Check TC PRs" gate fails because both TC PRs are still open drafts, which is expected.

## Unverified risks (non-blocking)

### R-1 (P3, liveness): a TDE page that keeps failing now aborts every victim-flush round

Found independently by A-1 and B-1, then deduplicated.

- **Mechanism:**
  - After an encryption failure the page is DIRTY again, so `pgbuf_flush_victim_candidates` picks it again in later rounds.
  - Each failure stops the round at [`goto end` (page_buffer.c:4642)](https://github.com/CUBRID/cubrid/blob/7a7a48ac1a0a4e96e51f1d4540ea9bc7f62ae49c/src/storage/page_buffer.c#L4642).
  - By default, candidates are sorted by VPID ([4547](https://github.com/CUBRID/cubrid/blob/7a7a48ac1a0a4e96e51f1d4540ea9bc7f62ae49c/src/storage/page_buffer.c#L4547)). Candidates after the failing page may then stay unflushed by the daemon, and each round logs an error.
- **Precondition:** the server runs with the TDE key not loaded (boot tolerates a key-load failure), and a TDE page became dirty. DWB slot errors are transient.
- **Base comparison:** base leaked the BCB as FLUSHING and hung every synchronous flusher, but the daemon kept making progress.
- **PR body:** it states that the round stops. It does not state that later candidates may starve or that the log may fill with errors.
- **Suggested fix (follow-up is fine):** `continue` past a failed candidate instead of `goto end`, or skip a BCB that failed in the last round.
- **Cheapest decisive check:** release build with a small buffer pool and victim pressure. Use gdb to make `tde_encrypt_data_page` fail every time for one low-VPID page, then compare flushed-page and victim-wait counters and `.err` growth between base and head.

### R-2 (P3, durability; sharpens PR Remarks ③): the checkpoint's "flush again" step trusts a waited-on flush

Found by A-2.

- **Where:** in `pgbuf_flush_seq_list`, the second `pgbuf_bcb_safe_flush_internal` call ([5098-5103](https://github.com/CUBRID/cubrid/blob/7a7a48ac1a0a4e96e51f1d4540ea9bc7f62ae49c/src/storage/page_buffer.c#L5098-L5103)) sets `done_flush = true` on `NO_ERROR` and does not recheck the LSA.
- **Schedule:**
  1. Checkpoint C waits on page P.
  2. The flush it waited on fails, and C is woken.
  3. C waits again, either because a permanent write-latch holder has P or because another flusher restarted on P.
  4. That flush fails too.
  5. A release build then counts P as flushed and leaves its `oldest_unflush_lsa` out of the checkpoint's smallest LSA. A debug build hits `assert` at 5101.
  6. If the server crashes before P reaches disk, redo can start after the lost change.
- **Attribution:** this already existed for write failures. The PR extends it to TDE and DWB failures only in states where base hung forever. It needs two failures in a row on the same page.
- **PR body:** the Remarks say "checkpoint re-flushes after waking, and a second failure hits `assert (false)` in debug". That holds only when the second attempt is the checkpoint's own flush, not another wait.
- **Suggested action:** correct the Remarks, or after the recheck, relock and test the LSA condition again. Either can be a follow-up.
- **Cheapest decisive check:** release build with gdb double injection on one BCB. Break after 5098 and inspect `done_flush` and the checkpoint smallest LSA, then `kill -9` and verify the row after restart.

### N-1 (nit): the header comment overclaims

The new header says "on error, the bcb is locked, no longer flushing, ... waiters are woken up". The early `pgbuf_check_bcb_page_vpid` failure (`assert (false); return ER_FAILED`) returns before FLUSHING is set and wakes nobody. The state is consistent there, so only the wording overclaims.

## Pre-existing issues seen during review (outside this PR, source-only)

- **P-1:** the retry relock does not recheck the write latch. A writer that took the latch between rounds can be mid-change while the retry copies the page, so the copy could be torn. Base behaves the same.
- **P-2:** the `CUBRID_DEBUG`-only unfix path ignores the flush error and then invalidates a dirty page.
- **P-3:** in the DWB, if `dwb_slots_hash_insert` fails, the filled slot is never counted in its block.
- The woken-waiter "assume flushed" behavior and the two windows in Remarks (checkpoint skipping a page that is FLUSHING with DIRTY cleared; `pgbuf_set_lsa` checking NULL without the mutex) are acknowledged in the PR body. I did not re-analyze them.

## Coverage and verification

| Path / invariant | Primary | Second | Evidence | Result | Remaining |
|---|---|---|---|---|---|
| `page_buffer.c` `pgbuf_bcb_flush_with_wal`: error routing, `error_locked`, lock flag | B (Systems) | A | L3 | Pass | — |
| Retry LSA preservation (`copy_unflushed_lsa`) | A (Recovery) | B | L3 | Pass | — |
| Flag and counter transitions (`mark_is_flushing` / `was_not_flushed`, `dirties_cnt`, async request) | B (Storage) | A | L3 | Pass | — |
| Waiter wake semantics (checkpoint, flush_all, flush_with_wal, discard, invalidate) | A (Concurrency) | B | L3 | Pass; R-2 noted | Optional R-2 probe |
| Caller contracts at 4628, 9658 (plus 9 callers), 13064 | Shared question: A and B, independent | — | L3 | Pass (both) | — |
| Victim-flush daemon behavior on a page that keeps failing | B (Perf) | A | L3 | R-1 risk | Optional R-1 probe |
| Checkpoint durability (smallest LSA) | A (Recovery) | — | L3 | R-2 risk (two failures in a row) | Optional |
| C/C++ build (release `-Werror`, debug) | Coordinator | — | CI at head: build (release) and build (debug) pass | Pass | — |
| HA / replication | n/a | — | No log record, protocol or replication change; local data-page flush only | N/A | — |
| Standards: indent, license, PR title, cppcheck | Coordinator | — | CI static checks pass at head | Pass | — |
| Spec conformance (PR body intent T1–T7) | Coordinator | — | Code matches the described design. The author's gdb tests were not replayed. | Pass (source) | — |
| TC PRs `tc/pr-8786` | Coordinator | — | cubrid-xref: both are drafts with 0 files | No TC change | Keep open until `/cubrid-pr-merge` |

**Shared question:** "Can any caller or woken waiter, after `error_locked`, see a state that leads to a hang, a double cleanup, a lost DIRTY flag, a wrong LSA, an assertion, or a premature 'flushed' conclusion that base did not have?"
- A (opus): no new caller issue. The waiter "assume flushed" behavior is the acknowledged ③; A sharpened it into R-2.
- B (sonnet): no new caller issue. The debug assert in the checkpoint's "flush again" step and the "assume flushed" behavior match the pre-existing write-failure path.

**Gaps:**
- I ran no runtime replay of R-1 or R-2.
- I did not trace the `pgbuf_get_victim` wait timeout, so the severity of R-1 starvation is unmeasured.
- The `test_shell` failure attribution comes from the PR body. I did not verify it.

## Dropped candidates

| Reviewer | Dropped | Reason |
|---|---|---|
| A | 4 | Disproven: BCB reassigned mid-flush; conditional restore losing a change; SA-mode regression; invalidating a page that is DIRTY again in the temp-page discard path. |
| B | 9 | Disproven (cleared risks): goto over initialization; unset error on the DWB path; wrong lock flag; double unlock or wake; dirty-counter drift; DWB slot leak; TDE nonce reuse; BCB identity change; success-path cost. |
| B-2 | merged | Same as the woken-waiter issue the PR acknowledges, and covered by R-2. |

## Budget

- **Mode:** bounded. No hard cap was enforced.
- **Reviewers:** two agents, A (opus, xhigh, about 12 min) and B (sonnet, xhigh, about 10 min). Each used about 50 tool uses and about 190k–210k subagent tokens, as reported by the harness.
- **Coordinator:** usage was not measured. There were no retries.
- **Envelope:** within target.
