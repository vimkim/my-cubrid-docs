# Code review: CUBRID/cubrid#8434 at 8e139f4db

Goal: review PR #8434 (ADR-0008 OOS reclaim after the delete is final, with the CBRD-27953 and CBRD-27925 follow-ups) before it is marked Ready for review.

Most consequential result: no confirmed defect. Five specialist reviewers found only source-level P3 risks. The largest open item is performance, not correctness: since `8e139f4db` every OOS page allocation takes the per-file growth lock, which now also covers `file_alloc`, and its waiters cannot be interrupted. Nobody has measured the throughput cost.

## Verdict and follow-up

- **Verdict: `incomplete`.** No confirmed findings. Coverage of the delta since the previous review is complete. The full-PR re-derivation is partial where the previous review already covered it. The growth-lock throughput risk (U-1) is unmeasured.
- **Follow-up review required: yes, for evidence, not as a correctness blocker.**
  - Needed: measure U-1 (multi-threaded insert into one OOS file, `c255c7c3b` vs `8e139f4db`).
  - Optional: the CLR-redo variant of the crash probe, and a test for the growth lock through `file_alloc`.
  - The reviewers found no correctness item that must precede merge.

## Scope

- Repository CUBRID/cubrid, PR https://github.com/CUBRID/cubrid/pull/8434.
- Base and merge base `95ff126a8464179a2fab3092b6f56468528ab954`. Head `8e139f4dbb2635058032d0b9dafd5f624c726754`.
- At the snapshot, the remote base `feature/oos-merge` had advanced to `50619ce53`. The merge base did not change.
- Comparison: `git diff 95ff126a8464179a2fab3092b6f56468528ab954 8e139f4dbb2635058032d0b9dafd5f624c726754`. 38 files, +3831/-1341, patch SHA-256 `95b4fec7dc07ac3e130feee256c258013cf83751ce701d1a9b0fbb119e468f61`. No renames, deletions, submodules, or binaries.
- Previous review: [code-review-pr8434-3e8072f](../code-review-pr8434-3e8072f/report.md) at `3e8072f56` (rebased as `c255c7c3b`).
  - Its outcomes: R1-R6, R9, R10 fixed. R7 -> CBRD-27981. R8 -> ADR-0008 consequence 8. P-1 -> CBRD-28012. P-2 -> CBRD-27982.
  - The delta since then (`c255c7c3b..8e139f4db`, 14 files) had first priority:
    - review fixes;
    - R6 (`b6bcc09c6`);
    - CBRD-27953 (`0034bc2fb`, `26e6d1d6f`): defer a notification whose heap-header lookup fails, and finish the rest of the block;
    - CBRD-27925 (`e01d8d576`, `8e139f4db`): emptied-page set, growth lock through `file_alloc`, RVOOS_INSERT undo carrying the OOS VFID.
- Specifications: ADR-0008, ADR-0009, ADR-0010 in `cubrid-oos-context/docs/adr/`.

## Confirmed findings

None. No candidate was reproduced as wrong behavior against the pinned code.

## Safety facts and effects outside the diff

| Fact | Owner | Evidence | Level |
| --- | --- | --- | --- |
| A block left unfinished by a deferral or interrupt is never marked vacuumed. A rerun skips chains already reclaimed, using the identity stamp. | concurrency, systems (Q2) | `vacuum_process_log_block` sets `vacuum_complete` only after the `oos_deferred` check. The error stack push and pop are balanced, including `vacuum_heap`'s pair. | 3 |
| No undo reinserts into an OOS page, so a page in the emptied-page set is never an undo target. Reclaim re-proves "PAGE_OOS and zero records" under the OOS header WRITE latch and a page WRITE fix before deallocation. | recovery, storage (Q1) | RVOOS_DELETE is redo-only. `oos_rv_undo_insert` only deletes. `oos_try_reclaim_page_internal` has two phases. | 3 |
| Restart undo of an uncommitted multi-chunk OOS insert (new 8-byte RVOOS_INSERT undo image) succeeds, and the space is reusable. | coordinator | Probe [`evidence/rcv-p1-probe.sh`](evidence/rcv-p1-probe.sh) (below): "UNDO Phase ... transactions to undo: 1". The loser row is gone, the committed 200 KB row is intact, a new 200 KB insert succeeds, and `checkdb` exits 0. Debug build, no assert. | 5 |
| Reclaim deletes only its own chain and finishes a partial chain after a crash. Vacuum slot-undo invariants hold except the known pre-existing CBRD-27858. | recovery | `cubrid-verify-vacuum-slot-undo` TLA+ check at `8e139f4db`. The extracted shape matches head (tail_first, link_stamp, per_chunk, reclaim_postpone). The model does not cover page deallocation. | 4 for the model's abstraction |
| The log applier skips the new undo image by `ulength`. The new reclaim, postpone, and notify records are not interpreted by the slave. The slave reclaims through its own postpones and vacuum. R8 is not widened beyond ADR-0008 consequence 8. | ha | `la_rebuild_oos_recdes` rcvindex and NULL-info checks; dump functions present; RV_fun indexes contiguous. | 2-3 |
| No latch cycle with the growth lock. Its holder waits only on the OOS stats header, conditional data-page fixes, and file/disk latches. No waiter holds those. | concurrency, storage | Lock order: growth lock, then OOS header, then file header. | 3 |
| Throwing STL operations are caught. Payload parsing is bounds-checked. Unit-test seams compile out of production. The fail-stop always exits in production. | systems | Source. | 2-3 |

## Unverified risks (all P3, source-only unless stated)

| ID | Risk | Seats | Next check |
| --- | --- | --- | --- |
| U-1 | Growth lock on every OOS page allocation, now held through `file_alloc` (`oos_reclaim_claim_growth`, `oos_file.cpp:1788-1840`). One `pthread_cond_t` shared by all files is broadcast under the global bestspace mutex, which gives O(N) wakeups per allocation with N waiting growers. The wait has no timeout and no interrupt check, so query cancel and shutdown wait for `file_alloc` or a lap. `oos_reclaim_check_emptied` (`1847-1900`) also copies the whole set (up to 4096) under the global mutex per growth. | storage C-1, C-2; concurrency CC-3 | Measure: 16-64 threads inserting page-filling values into one OOS file, `c255c7c3b` vs `8e139f4db`, with throughput and futex wakeups. Possible fix: a per-file condvar, skip the lock when the set is empty and the file is known, a timed wait with an interrupt check, a bounded slice per round. |
| U-2 | `oos_reclaim_fix_candidate` (`oos_file.cpp:1520-1527`) reads `er_errid ()` after a conditional `pgbuf_fix` failure that sets no error unless the wait is zero. A stale `ER_PB_BAD_PAGEID` classifies a busy page as gone, so the empty page waits for the next delete or lap. A stale `ER_INTERRUPTED` fails a growth. Same pattern in base `oos_find_best_page`. | systems S-3 | `er_clear ()` before the fix; or a unit probe with a stale error and a latched page. |
| U-3 | `vacuum_oos_reclaim_notified_chains` (`vacuum_oos.cpp:247`) treats every non-interrupt error as a lookup deferral. In production, the other errors fail-stop first. Only the unit-test fail-stop hook reaches this, where a test could pass for the wrong reason. | systems S-1, concurrency CC-1 | Return a distinct marker from the lookup branch. |
| U-4 | RVOOS_NOTIFY_VACUUM can be dropped silently: `log_append_undo_crumbs_internal` returns void on node allocation failure (OOM at commit) and under no-logging. The dropped chains then leak permanently, with no fail-stop. Every log append has the same OOM weakness. The no-logging case applies to UPDATE only. | ha C-1, systems S-4 | Accept and document, or use an append variant that returns an error and call `oos_reclaim_fail_stop`. |
| U-5 | Emptied-set imprecision, bounded and self-healing: a lap re-adds busy pages without proof that they are empty, possibly already deallocated. One growth examines a page only once, which partly contradicts the `8e139f4db` message. After a 4096 overflow, the next growth runs a full-file lap even when the set has drained. | storage C-3, C-4; concurrency CC-2 | Optional: re-add only after a phase-1 proof; count lost adds. |
| U-6 | Test gaps: no test reaches `file_alloc` under the growth lock (`ConcurrentGrowerWaitsForActiveSweep` stops before it). No test covers an insert that fails before its first record. No test covers CLR redo of the new RVOOS_INSERT undo image. The crash-recovery test counts any read error as reclaimed. | storage C-5, recovery RCV-1, systems | Add the probes in [`evidence/probe-growth-lock-covers-alloc.md`](evidence/probe-growth-lock-covers-alloc.md) and the CLR variant of [`evidence/probe-restart-undo-oos-insert.md`](evidence/probe-restart-undo-oos-insert.md). |

### Design questions for the author (not defects)

- A heap-header read error that keeps failing now makes vacuum retry the notification block indefinitely without stopping the server (concurrency U1). Before `0034bc2fb` this path fail-stopped. This matches the CBRD-27933 and CBRD-27953 policy that the PR body states.
- An OOM while unpacking a notification fail-stops, although nothing has been modified yet (systems S-2). This matches ADR-0008 decision 3 as applied in R6. Deferral is an alternative.
- `serial_update_serial_object` (`serial.c:1254`) holds the db_serial page WRITE latch while it transforms the record. If a serial record ever needs OOS, it waits on the uninterruptible growth lock with that latch held. This is a latency risk only, and whether a serial record can reach the OOS threshold is unverified (concurrency R1).

### Cosmetic

`vacuum.c` orphans the doc comment of `vacuum_recover_lost_block_data`. ER 1393's text does not fit the notification path. `oos_pack_reclaim_intent` copies struct padding into log bytes (systems S-5).

### Pre-existing (not attributed to this PR)

- CBRD-27858: forward-slot undo (TLA+ known finding, also at base).
- CBRD-28012: P-1 eager-path latch order.
- The stale `er_errid` and error-left-set pattern in `oos_find_best_page` fallback paths.

### Dropped candidates

- S-1 and CC-1 merged as U-3.
- C-1, C-2, and CC-3 merged as U-1.
- C-3, C-4, and CC-2 merged as U-5.
- HA C-1 and S-4 merged as U-4.
- RCV-1 is narrowed to the CLR variant inside U-6, since the coordinator probe executed restart undo.

No candidate was disproven outright. All remain as P3 risks or design questions.

## Checks run

| Check | Command | Result |
| --- | --- | --- |
| Build (debug_gcc, OOS unit tests) | `cmake --preset debug_gcc -DUNIT_TESTS=OFF -DUNIT_TEST_OOS=ON -DUNIT_TEST_SPAGE=ON -DUNIT_TEST_PAGE_BUFFER=ON` then `just build-and-install` | pass; no warning in PR files |
| All configured tests | `ctest --test-dir build_preset_debug_gcc --output-on-failure` | 54/54 pass (743 s, load average 21-35) |
| Restart undo of an uncommitted OOS insert | [`evidence/rcv-p1-probe.sh`](evidence/rcv-p1-probe.sh): `kill -9` the server with one open 200 KB insert after a committed 200 KB insert, restart, query, insert, `checkdb` | pass (see the safety facts) |
| Vacuum/OOS slot-undo model | `python3 ~/.claude/skills/cubrid-verify-vacuum-slot-undo/scripts/check.py --rev 8e139f4db` | all OOS properties pass; CBRD-27858 known finding; exit 3 because covered code changed since the model's sync commit (shape re-checked by hand) |

Two earlier coordinator ctest attempts are void and not evidence:
- One used a nonexistent label.
- One ran against a library configured with `UNIT_TESTS` off by `just configure`, so every binary failed with an undefined symbol.

Not run: the growth-lock throughput measurement, the HA smoke test, and the CLR-redo crash variant.

## Budget

- Mode: bounded, with no user ceiling and no hard cap enforced.
- Five reviewer seats: recovery and concurrency on opus, systems, storage, and HA on sonnet, all at reasoning effort xhigh.
- A provider usage limit interrupted three seats. Concurrency and systems resumed from their transcripts after the reset. Recovery had already written its report. No seat was restarted fresh.
- Per-agent usage is unknown, because account-wide telemetry includes other sessions. Coordinator work included three builds, three ctest attempts, and one crash probe.
- The optional per-assignment targets cannot be verified.

## Artifacts

- [coverage.md](coverage.md) and [handoff.md](handoff.md).
- [evidence/](evidence/) holds the crash probe and the two probe designs. Reviewer reports and raw logs remain in the local run directory and are not published.
