# R2 Storage + Recovery + HA + TC reviewer (model: sonnet, effort xhigh)

Saved by the coordinator from the agent's final message (the agent's Write was refused by the harness).

- Pinned identity verified: engine HEAD `d6bd5db6ab` clean, single hunk `src/transaction/boot_sr.c:3141-3142`; TC branch `tc/pr-8715` at `f0714e9ebd` (read with `git show`).
- Coverage: complete at source level for Q1-Q3 and the static TC review; residual windows partial. Budget: ~42 tool calls vs ~40 target (slight overshoot).

## Q1 Shared challenge

- CDC producer does no pgbuf fix after `cdc_kill_producer` returns (level 3, not executed).
  - DEAD is set only after the loop exits (`src/transaction/log_manager.c:11830`); only `is_cdc_daemon = false; return` follows.
  - `destroy_daemon` joins the thread (`src/thread/thread_daemon.cpp:104`) before `pgbuf_daemons_destroy`.
  - Looper re-invocations before the join do nothing because `request` stays `TO_BE_DEAD`.
- Producer page access is indirect only (`heap_classrepr_get`, `heap_attrinfo_start`, `heap_attrinfo_read_dbvalues`); no direct fix/dirty/log-append/heap-write.
- The race is a NULL test followed by a dereference (`src/storage/page_buffer.c:12541`) against `delete res; res = NULL` (`src/thread/thread_manager.hpp:470`). The PR closes it for the producer.
- `scdc_*` handlers are joined first by `css_init` shutdown (`src/connection/server_support.c:698-760`).
- Residuals not fixed by the PR (pre-existing):
  - Log checkpoint and other log daemons survive the pgbuf destroy (`log_daemons_destroy` inside `log_final`, `log_manager.c:1830`) -> CBRD-28341.
  - `pl_server_destroy` and parallel-query workers are destroyed after pgbuf (unproven whether they can fix pages then).
  - The normal path lacks `BO_DISABLE_FLUSH_DAEMONS` / `dwb_daemons_destroy` before the pgbuf destroy, unlike the restart failure path; "same order as the restart failure path" holds only for cdc-before-pgbuf.

## Q2 Storage / recovery

- Producer is read-only: no log, page or LSA writes, so final flush, `log_final`, `dwb_destroy` are unchanged (level 2).
- Only persisted CDC state is the archive pin in the log header, written from consumer request threads; `cdc_finalize` does not touch `arv_keep_lsa`/pin; pgbuf reads nothing it frees.
- Old order could stall a producer waiting on a buffer after the flush daemon was gone; the new order removes that.

## Q3 HA / CDC

- No effect (level 2): log writers and client connections are closed before `xboot_shutdown_server`.

## Candidates

- None reproduced; no defect introduced by the PR. Source-only: checkpoint-daemon residual (level 2).

## Q4 TC #5119

Exercises the claimed path (supplemental_log=1, open CDC client, background DML, `cubrid server stop`, 5 rounds). Cannot reach the race (64 MB DB never exhausts buffers); description says so honestly. Helpers exist and are used correctly; placement `_26_2h/cbrd_28307/cases/` matches siblings; no answer file needed.

- T1 (low/medium): error-log grep covers every `db28307_*.err`, including earlier runs; a stale file can cause a false NOK. Fix: delete at start, or count before/after like cores.
- T2 (low): `dml_running_at_stop` printed but not asserted.
- T3 (low): `hostname -I` can be empty; `localhost` avoids it.
- T4 (low): core detection depends on core files being written (systemd-coredump hosts write none).
- T5 (low): empty `$USER` makes `server_pid` empty and the exit check silently passes.
- T6 (info): per-round diagnostics deleted even after NOK.
- Public draft cubrid-testcases#4422 (info): 0 files; close-without-merge candidate at final handoff.
