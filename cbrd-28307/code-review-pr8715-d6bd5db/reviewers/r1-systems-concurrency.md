# R1 Systems + Concurrency reviewer (model: opus, effort xhigh)

Saved by the coordinator from the agent's final message (the agent's Write was refused by the harness).

- Pinned identity verified: HEAD `d6bd5db6abd400cd48c4c09de190c488c4214003`, clean, merge-base = base `8e052e99c508141dbdd6dc338b65e437e31d756a`, patch sha256 `3b08d427…`.
- Coverage: complete (source level). Budget: ~36 of ~40 tool-call target.

## Q1 Shared challenge: can anything still touch the pgbuf daemons after the reorder?

- CDC producer: closed (evidence level 3).
  - `cdc_kill_producer` waits for `state == CDC_PRODUCER_STATE_DEAD`, set only after the producer leaves its loop (`src/transaction/log_manager.c:11764`).
  - Looper re-invocations set RUN, see `TO_BE_DEAD`, and return without touching pgbuf (`log_manager.c:11688`).
  - `destroy_daemon` then stops and joins the producer thread (`src/thread/thread_daemon.cpp:90-105`) before `pgbuf_daemons_destroy`.
  - Nothing resets `request`: other writers are `scdc_*` handlers, and `css_init` stops all request workers before `xboot_shutdown_server` (`src/connection/server_support.c:702-750`).
- Residual windows: all pre-existing, not added or widened by the PR.
  - Log checkpoint daemon (CBRD-28341) stays live through the pgbuf teardown and can reach the flush-daemon wakeup via `disk_set_checkpoint` -> `disk_get_volheader` -> `pgbuf_fix` on a header-page miss (level 2).
  - Inside `pgbuf_daemons_destroy` the maintenance daemon, the only daemon that wakes the flush daemon, is destroyed first.
  - Parallel query workers must be idle by then (asserted at `px_worker_manager_global.cpp:89`). Vacuum, sessions, dwb and pl_server are already stopped or do not touch pgbuf.

## Q2 New hang or ordering regression?

- None. `cdc_finalize` frees only CDC memory; pgbuf daemons never read CDC state.
- Liveness likely improves: a producer waiting on a free BCB is served by the still-running flush daemons (unproven).
- SA_MODE and `supplemental_log=0` paths unchanged; parameter is not runtime-changeable.

## Q3 Crash claim

- `pgbuf_is_page_flush_daemon_available` is a plain unlocked NULL read (`src/storage/page_buffer.c:18411`).
- `destroy_and_untrack_resource` deletes before nulling (`src/thread/thread_manager.hpp:468-470`).
- The author's call chain exists at head. The window is a few instructions wide, consistent with no base reproduction.
- Cheapest decisive check: debug delay between `delete` and `res = NULL`, open CDC session, small buffer pool.

## Q4 Comment

- GNU indent 2.2.11 (`-l120 -lc120`) leaves base and head unchanged (level 4; probe in `systems/indent/`).
- Nit: "stop it" could be read as the flush daemon; "stop the producer" is clearer.

## Candidates

- SYS-1 (P3, pre-existing): checkpoint-daemon window (tracked as CBRD-28341).
- SYS-2 (nit): comment wording.
