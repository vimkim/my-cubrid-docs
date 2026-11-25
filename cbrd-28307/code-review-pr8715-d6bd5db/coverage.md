# Coverage — CUBRID/cubrid#8715 at d6bd5db6ab

| Path / invariant | Owner | Evidence | Result | Remaining action |
| --- | --- | --- | --- | --- |
| `src/transaction/boot_sr.c` `xboot_shutdown_server` reorder (only changed path) | R1, R2, coordinator | Source trace (L3), coordinator line recheck | Correct | None |
| Shared challenge: no thread touches pgbuf daemons after/while `pgbuf_daemons_destroy` runs, for the CDC producer | R1 (opus) and R2 (sonnet), independent | Both: `cdc_kill_producer` waits for DEAD set after loop exit; `destroy_daemon` joins; request not reset after workers stopped (L3) | Agree: closed for the producer | Optional fault-injection probe (see report) |
| Residual daemons alive across pgbuf destroy (checkpoint / log daemons, PL server, parallel workers) | R1, R2 | Source (L2) | Pre-existing, not widened by PR; checkpoint path tracked as CBRD-28341 | Out of scope (CBRD-28341) |
| New hang / ordering dependency between CDC finalize and pgbuf daemons | R1, R2 | Source (L2-3) | None; liveness improves | None |
| Storage / recovery: final flush, `log_final`, `dwb_destroy`, durable CDC state | R2 | Source (L2): producer read-only; `cdc_finalize` frees CDC memory only | No effect | None |
| HA / CDC client visibility | R2 | Source (L2): log writers and client connections closed before shutdown | Not applicable beyond shutdown ordering | None |
| Comment formatting (GNU indent) | R1 | indent 2.2.11 probe (L4) | Unchanged by indent | Optional wording nit |
| Build | Coordinator | `debug_gcc` build-and-install at head | Pass | None |
| TC #5119 `shell/_06_issues/_26_2h/cbrd_28307` static review | R2, coordinator | Source review vs helpers and siblings | Valid regression guard; low-severity robustness nits | Optional |
| TC #5119 runtime | Coordinator | Contained native testkit run at head (attempt `~/tk/c28307-1`) | OK 5/5 rounds, verify exit 0 | None |
| SA_MODE | R1 | Hunk is inside `#if defined(SERVER_MODE)` | Not applicable | None |
