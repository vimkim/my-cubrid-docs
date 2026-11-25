# Code review: CUBRID/cubrid#8715 at d6bd5db6ab

- **PR:** [CUBRID/cubrid#8715](https://github.com/CUBRID/cubrid/pull/8715), "[CBRD-28307] Stop the CDC producer before the page buffer daemons at server shutdown" (author hornetmj).
- **Companion TC PRs:** [cubrid-testcases-private-ex#5119](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5119) (`tc/pr-8715`, 2 added files). [cubrid-testcases#4422](https://github.com/CUBRID/cubrid-testcases/pull/4422) is a draft with 0 changed files.
- **Goal:** Check whether the shutdown reorder closes the use-after-free it targets, adds no new hang or ordering regression, and whether the TC is a sound regression guard.
- **Result:** No confirmed defect. The reorder closes the CDC producer window, and the TC passes 5/5 rounds on a local debug build at the head.

## Snapshot

| Item | Value |
| --- | --- |
| Base | `8e052e99c508141dbdd6dc338b65e437e31d756a` (develop) |
| Head | `d6bd5db6abd400cd48c4c09de190c488c4214003` |
| Merge base | `8e052e99c508141dbdd6dc338b65e437e31d756a` |
| Comparison | `git diff 8e052e99c508141dbdd6dc338b65e437e31d756a d6bd5db6abd400cd48c4c09de190c488c4214003` |
| Patch | `src/transaction/boot_sr.c`, +3/-1, sha256 `3b08d42731bd7613a03fb101eb7b90ad1a9661803708cd389270c01ccffcd7b2` |
| TC #5119 head | `f0714e9ebdcf34af1ef607dad671b5cd571f055e` (base develop `07af85a51694`) |
| Snapshot date | 2026-11-25 KST. The base and head were rechecked as unchanged before publication. |

## Verdict and follow-up

- **Verdict:** `no-confirmed-findings`.
- **Follow-up review required:** no. The optional evidence below would turn the source argument into an executed one. It does not block merging.
- **Formal approval readiness:**
  - Engine #8715 is ready for approval on code grounds. One optional comment-wording nit is listed below.
  - TC #5119 is ready for approval. Its robustness nits are optional.
  - The PR approval gate is currently `BLOCKED` on both PRs, because the requests to lht1199 and vimkim are still pending.

## What changed

In `xboot_shutdown_server` ([boot_sr.c:3139-3142](https://github.com/CUBRID/cubrid/blob/d6bd5db6abd400cd48c4c09de190c488c4214003/src/transaction/boot_sr.c#L3139-L3142)), `cdc_daemons_destroy ()` now runs before `pgbuf_daemons_destroy ()`. A comment explains why. The change is inside `#if defined(SERVER_MODE)`. The restart failure path ([boot_sr.c:2797-2801](https://github.com/CUBRID/cubrid/blob/d6bd5db6abd400cd48c4c09de190c488c4214003/src/transaction/boot_sr.c#L2797-L2801)) already destroyed the CDC daemon before the pgbuf daemons.

## Confirmed findings

None.

## Safety facts and effects outside the diff

| # | Safety fact | Owner | Evidence | Level |
| --- | --- | --- | --- | --- |
| S1 | The crash the PR describes is real. `pgbuf_wakeup_page_flush_daemon` tests `pgbuf_Page_flush_daemon != NULL` without a lock and then dereferences it ([page_buffer.c:12541-12544](https://github.com/CUBRID/cubrid/blob/d6bd5db6abd400cd48c4c09de190c488c4214003/src/storage/page_buffer.c#L12541-L12544), [:18411](https://github.com/CUBRID/cubrid/blob/d6bd5db6abd400cd48c4c09de190c488c4214003/src/storage/page_buffer.c#L18411)). `destroy_and_untrack_resource` runs `delete res;` before `res = NULL;` ([thread_manager.hpp:469-471](https://github.com/CUBRID/cubrid/blob/d6bd5db6abd400cd48c4c09de190c488c4214003/src/thread/thread_manager.hpp#L469-L471)). The producer call chain in the PR body exists at the head. | R1, R2 | Source | 3 |
| S2 | After `cdc_daemons_destroy` returns, the producer cannot fix a page. (1) `cdc_kill_producer` waits until `state == DEAD` ([log_manager.c:14957-14969](https://github.com/CUBRID/cubrid/blob/d6bd5db6abd400cd48c4c09de190c488c4214003/src/transaction/log_manager.c#L14957-L14969)). (2) The producer sets DEAD only after it leaves its loop, and only a return follows ([log_manager.c:11830](https://github.com/CUBRID/cubrid/blob/d6bd5db6abd400cd48c4c09de190c488c4214003/src/transaction/log_manager.c#L11830)). (3) A looper re-run sees `TO_BE_DEAD` and returns without page access. (4) `destroy_daemon` stops and joins the thread ([thread_daemon.cpp:90-105](https://github.com/CUBRID/cubrid/blob/d6bd5db6abd400cd48c4c09de190c488c4214003/src/thread/thread_daemon.cpp#L90-L105)). | R1, R2 independently; coordinator rechecked | Source | 3 |
| S3 | Nothing can reset `producer.request` after the kill. Its other writers are `cdc_initialize` and the consumer handlers that run on request workers (`network_interface_sr.cpp:12554-12751`, `cdc_cleanup`). `css_init` stops every request worker before it calls `xboot_shutdown_server` ([server_support.c:700-750](https://github.com/CUBRID/cubrid/blob/d6bd5db6abd400cd48c4c09de190c488c4214003/src/connection/server_support.c#L700-L750), [network_sr.c:1252](https://github.com/CUBRID/cubrid/blob/d6bd5db6abd400cd48c4c09de190c488c4214003/src/communication/network_sr.c#L1252)). | R1; coordinator rechecked | Source | 3 |
| S4 | The reorder adds no dependency in either direction. `cdc_finalize` frees only CDC memory, the pgbuf daemons read no CDC state, and the producer writes no log records, pages, or LSAs. Final flush, `log_final`, and `dwb_destroy` behave as before. Liveness likely improves: a producer that waits for a free buffer is now served by the flush daemons that are still running. The liveness improvement is unproven. | R1, R2 | Source | 2-3 |
| S5 | The shutdown with an open CDC session and running DML still completes cleanly at the head. | Coordinator | TC run below | 5 (regression guard only; the race window is not forced) |

**Cleared risks**

- SA_MODE: the block is server-only.
- `supplemental_log = 0`: `cdc_daemons_destroy` returns early.
- HA: log writers and client connections close before `xboot_shutdown_server` runs.
- Order inside `pgbuf_daemons_destroy`: the maintenance daemon, which wakes the flush daemon, is destroyed first.
- GNU indent 2.2.11 (`-l120 -lc120`) leaves the hunk unchanged (R1 probe, level 4).

**Pre-existing residual windows.** This PR neither introduces nor widens any of these.

- The log checkpoint daemon lives until `log_final` and can reach the same wakeup through `disk_set_checkpoint` → `disk_get_volheader` → `pgbuf_fix` when the volume header page is not cached. The PR's Remarks track this as CBRD-28341 (level 2).
- The PL server and the parallel query workers are destroyed after the pgbuf daemons. The parallel workers must be idle at that point, which `px_worker_manager_global.cpp:89` asserts. Whether the PL server can fix a page there is unproven, but no transaction is active at that point.
- The PR body says "the same order the restart failure path already uses". That holds only for CDC before pgbuf. The restart failure path also calls `BO_DISABLE_FLUSH_DAEMONS` and `dwb_daemons_destroy` before the pgbuf destroy, and destroys the PL server before CDC. This is informational.

**Optional evidence (not merge-blocking):** add a debug-only delay between `delete res` and `res = NULL` in `destroy_and_untrack_resource`. Then run with an open CDC session and a small `data_buffer_size` to force buffer exhaustion. The expected result is a crash on the base and a clean stop at the head. This would raise S2 to level 4.

## Coverage and verification

See [coverage.md](coverage.md) and the reviewer reports [R1](reviewers/r1-systems-concurrency.md) and [R2](reviewers/r2-storage-recovery-ha-tc.md). Every changed path has an owner, and no path was left uninspected.

| Check | Command / identity | Result |
| --- | --- | --- |
| Build | Debug build and install of the head, preset `debug_gcc` | Pass (`cubrid_rel`: `11.5.0.3040-d6bd5db`, debug) |
| TC cbrd_28307 | Native cubrid-testkit, contained (`TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell`, 1 slot, `scenario_disk=on`). Engine head d6bd5db6ab debug; TC `f0714e9ebdcf`. | **OK** 1/1, verify exit 0. Five rounds: `stop_rc=0`, `server_alive=n`, `dml_running_at_stop=y`, CDC items 1103 / 1172 / 1282 / 2379 / 3448; `core_after=0`, `assert_cnt=0`. |
| Base TC run | Not run here. The author reports that the base also passes. | Not run. The TC does not reproduce the race. |
| Existing CI | Head d6bd5db6ab: build, test_medium, test_sql, test_sql_by_cci, and test_shell passed. Only `TC Merge Gate / Check TC PRs` fails, because the TC PRs are open by design. | Observed, not rerun |

**Shared challenge.** The question was whether any thread can touch the pgbuf daemons during or after `pgbuf_daemons_destroy` once the reorder is in place. R1 (opus) and R2 (sonnet) answered independently. Both found the window closed for the CDC producer, and both named only the pre-existing residual windows above.

## TC #5119 review

The TC exercises the intended path. It enables `supplemental_log=1`, keeps a CDC client session open and extracting, runs background DML, and calls `cubrid server stop` in each of 5 rounds. Its DESCRIPTION states honestly that it is a regression guard and not a reproducer: a 64 MB database never exhausts the buffer pool, so the race is not reached. The placement `_06_issues/_26_2h/cbrd_28307/cases/`, the helper usage, and the cleanup match the sibling CDC TCs. A shell TC needs no answer file.

Optional robustness nits, none blocking:

- **T1:** The final grep covers every `$CUBRID/log/server/db28307_*.err` file, including the `_latest` symlink. A file left by an earlier local run can produce a false NOK. In this run the glob expanded to only `db28307_20261125_1633.err` and `db28307_latest.err`, so not every round's log may be inspected. That coverage question is unverified. Suggestion: record the files before and after the run, as the TC already does for cores.
- **T2:** `dml_running_at_stop` is printed but never asserted. That is acceptable for a guard, but asserting it would show that the stop raced live DML.
- **T3:** `hostname -I` can be empty on some hosts. `localhost` or `127.0.0.1` avoids that.
- **T4:** Core detection depends on core files being written; hosts that use systemd-coredump write none. The TC DESCRIPTION already says this.

## Unverified risks and dropped candidates

- **SYS-1 (pre-existing, out of scope):** the checkpoint-daemon window, tracked as CBRD-28341.
- **SYS-2 (nit):** in the new comment, "stop it" could be read as referring to the page flush daemon. Something like "stop the producer before pgbuf_daemons_destroy deletes that daemon" is clearer.
- Dropped candidates: none. Neither reviewer reported a defect attributable to the change.

## Budget accounting

- **Mode:** bounded. The user gave no absolute budget, and no hard cap was enforced.
- **Agents:** 2.
  - R1 Systems+Concurrency (opus, xhigh): 36 tool calls, about 111k subagent tokens.
  - R2 Storage+Recovery+HA+TC (sonnet, xhigh): 42 tool calls, about 149k tokens. That is slightly over the target of about 40 calls.
- **Retries:** none.
- **Coordinator:** one build and one contained TC run. Coordinator token usage was not measured.
- **Five-role scope:** the change is a one-line reorder, so the five roles were combined into two seats.
