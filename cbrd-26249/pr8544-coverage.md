# Coverage — CUBRID/cubrid#8544 ([CBRD-26249]) at `e54b7611e68ac98361e27eb9814c7dd62b91b8e6` (base `477fad77ae87ae1f831f5bea23ce4d4af88f0681`)

Every changed path has a primary owner. Evidence levels follow the reviewer contract (1 assertion … 5 reproduction in the running utility).

## Changed paths

| Path(s) | Primary reviewer | Invariant(s) | Evidence | Result | Remaining action |
|---|---|---|---|---|---|
| [`src/executables/util_sa.c`](https://github.com/CUBRID/cubrid/blob/e54b7611e68ac98361e27eb9814c7dd62b91b8e6/src/executables/util_sa.c#L6373) (`delvoldb`) | Systems | CLI parsing, prompts/EOF, exit codes, DBA auth, restart/shutdown pairing | source; ~15 arg-parsing runs; author `delvol-basic.sh` 16/17 (stale EOF assertion) | F3 (success message on unlink failure); SYS-1 test drift | Fix F3; author to update the attached basic script |
| `src/executables/util_admin.c`, `util_front.c`, `util_service.c`, `util_support.c`, `utility.h`, `win/cubridsa/cubridsa.def` | Systems | utility table/dispatch alignment, removed `-C/-c/-f`, SA export | script check of `UTIL_INDEX` vs `ua_Utility_Map` (0 mismatches); grep; `nm`-level symbol check | cleared (level 4) | `util_front.c` not fully analyzed by clang-tidy (pre-existing compile-db gap) |
| `msg/en_US.utf8/{utils,cubrid}.msg`, `msg/ko_KR.utf8/{utils,cubrid}.msg` | Systems | format-arg match, en/ko numbering, catalog contiguity | scripts; runtime messages seen in tests | cleared (level 4) | renumber on rebase (`develop` took −1404) |
| `src/base/error_code.h` | Systems + HA | new code + `ER_LAST_ERROR`, client mirrors | grep (no `dbi_compat.h` mirror; CCI mirror already stale) | cleared; **rebase conflict** | renumber −1404 → next free code |
| `src/base/fault_injection.{c,h}` | Recovery | FI ids 100003/4/5 at the claimed points | gdb/FI runs in `delvol-crash.sh` and probes | cleared (level 5) | — |
| `src/communication/network_interface_cl.{c,h}` | Concurrency (+ Systems) | SA-only wrappers, enter/exit_server pairing | source (level 3); build | cleared | — |
| `src/transaction/boot_sr.{c,h}` (`boot_dbparm_delete_last_volume`) | Concurrency + Recovery | parm/heap/cache agreement, flush-undo, durability before link cut | source; FI 100005 case | forward path cleared; undo ordering → F2 | Fix F2 |
| [`src/storage/disk_manager.{c,h}`](https://github.com/CUBRID/cubrid/blob/e54b7611e68ac98361e27eb9814c7dd62b91b8e6/src/storage/disk_manager.c#L2937) (check, delete, finish, cache remove, pending list, rollback, complete, newvol/undo/redo format changes) | Storage (+ Systems for C-level, Recovery for protocol) | emptiness, cache reversal, file lifecycle, DWB drain, `-u` path choice, pending decision rule | source; author suite; probes P1/R-1/SYS-2/ST-1 | F1, F3; U-C2, U-ST1, U-ST3 risks | Fix F1/F3; optional U-C2 hardening |
| `src/transaction/log_page_buffer.c`, `log_impl.h` (`logpb_reset_backup_lsa`) | Recovery (+ HA readers) | reset durable; readers of NULL LSAs | source enumeration (HA §5); `delvol-incremental.sh` pass | cleared (level 5) | U-2 product decision (reset after `restoredb`) |
| `src/transaction/log_recovery.c` (call site) | Recovery | complete runs after `boot_reset_db_parm`, after the redo worker join and undo | source; crash/server-recovery tests | cleared; **rebase conflict** | delta review after rebase |
| `src/transaction/recovery.{c,h}` (`RVDK_DELETE_VOLUME` = 145) | HA | `RV_fun` order/count, consumers of DBEXTERN | script (146 entries, matching); debug startup assert | cleared; **rebase conflict: `develop` took 145** | renumber; recheck `RV_fun` order and any persisted logs from test runs |

## Cross-domain risks and owners

| Risk | Owners | Result |
|---|---|---|
| Volid reuse vs. buffered/DWB/redo work of the old volume | Storage (primary), Concurrency | Normal and SA-restore paths cleared (level 4). Server resume of an interrupted restore: in-place route refuted at runtime; other routes source-only (U-ST1) |
| Aborted deletion / relocated restore consistency | Recovery, HA/compat (shared) | F1 confirmed |
| Undo ordering parm vs. link (restart pre-recovery invariant) | Recovery | F2 confirmed |
| Backup chain after deletion | Recovery, HA | cleared (incremental refused until level 0) |
| HA replication / log consumers | HA | cleared at source (level 3); HA runtime not exercised |

## Shared challenge questions

| # | Question | Seat A (model) | Seat B (model) | Independent results | Coordinator adjudication |
|---|---|---|---|---|---|
| 1 | Can an aborted deletion or an interrupted relocated restore leave link, `boot_Db_parm` and volume files inconsistent, or clean up a file outside the restore? | Recovery (`opus`) | HA/compat (`sonnet`) | Both: committed `-u` path consistent; a rolled-back deletion under `-u` rewrites link + `_vinf` with the old path, and the original's file can be adopted on the same host (R-3 / C1). HA also flagged the unmounted logged-path unlink (C2). | F1 confirmed by replay (restart route); crash route clean; C2 kept as risk U-C2 |
| 2 | Is deactivated volume identity and descriptor lifetime safe through startup recovery, including dirty/in-flight DWB/page-buffer writes when a VOLID is reused? | Concurrency (prior Codex, `gpt-6.1-sol`) | Storage (`sonnet`) | Concurrency: safe for normal paths, open C-1 (server resume of an interrupted restore). Storage first pass: unreachable; revised after reading C-1 to ST-1 (P2 proposed). Recovery (third view): C-1 precondition unreachable (H1–H4). | Disagreement resolved by probe `st1-interrupted-restore.sh`: no recovery ran on server start (in-place route). Kept as U-ST1 (P3 latent, source-only for H2–H4) |

## Not applicable / not covered

- Online (`SERVER_MODE`) deletion: rejected by code (`ER_ONLY_IN_STANDALONE`); out of scope by design.
- Middle-volume deletion and volid reuse (Acceptance 4–5): out of scope by the PR (phase 2).
- Not executed: HA runtime, release binary execution, valgrind, power loss, `suppress_fsync`, `no_logging`, 128M `createdb` variants.
