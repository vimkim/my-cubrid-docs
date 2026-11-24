# Code review — CUBRID/cubrid#8544 `[CBRD-26249] Add delvoldb to delete an empty last permanent volume in stand-alone mode`

- **Review date (`Asia/Seoul`):** `2026-11-24`
- **Jira / Tracker:** [CBRD-26249](https://jira.cubrid.org/browse/CBRD-26249) · Tracker `#1070`
- **Review goal:** full specialist review (Systems, Concurrency, Storage, Recovery, HA/compat), verification checks, and adjudication of the stand-alone `delvoldb` change at a pinned snapshot.

**Most consequential result:** the normal delete path and the single-crash paths are sound. The author's five test scripts pass at the pinned head; the only failure is a stale assertion in the v4 script. Three defects were reproduced against the pinned debug build and replayed by the coordinator:
- **F1 (P2):** a relocated `restoredb -u` of a log that contains a **rolled-back** deletion produces a restored database that either cannot start, or (same host) silently mounts the **original database's** volume file.
- **F2 (P3):** with `double_write_buffer_size=0`, a second crash during rollback recovery leaves the database permanently unstartable until `_vinf` is edited by hand.
- **F3 (P3):** `delvoldb` reports success and exits 0 when the volume file could not be removed.

## Snapshot

| Field | Value |
|---|---|
| Repository | CUBRID/cubrid, PR [CUBRID/cubrid#8544](https://github.com/CUBRID/cubrid/pull/8544) (author `hornetmj`, head repo `hornetmj/cubrid`, `CBRD-26249-delvoldb-last` → `develop`) |
| Comparison | PR merge base → pinned head: `git diff --binary --no-ext-diff --no-textconv 477fad77ae87ae1f831f5bea23ce4d4af88f0681 e54b7611e68ac98361e27eb9814c7dd62b91b8e6` |
| Base = merge base | `477fad77ae87ae1f831f5bea23ce4d4af88f0681` |
| Head | `e54b7611e68ac98361e27eb9814c7dd62b91b8e6` (rechecked against GitHub at 2026-11-24T12:59:56Z: unchanged) |
| Patch | sha256 `40868ececcd4eed7fbffb58eb01c37620229a5f75a887257a175df01a06ae7af`; 25 files, +1107/−128, no renames, binaries or submodule changes |
| Snapshot time | 2026-11-24T12:15:36Z |
| PR movement | Head unchanged. GitHub reports **CONFLICTING** against current `develop` `c59a6e30a70a3912c1e26e0786cc6a9f43ecbc5e`. Conflicting files are `msg/*/cubrid.msg`, `error_code.h`, `recovery.h/.c` and `log_recovery.c`. `develop` already took **rcvindex 145** (`RVHF_SERIAL_DDL_UPDATE_UNDO`) and **error −1404** (`ER_BT_LOAD_NO_LOGGING_DURING_BACKUP`). The rebase must renumber `RVDK_DELETE_VOLUME` and `ER_DISK_CANNOT_DELETE_VOLUME`, and that needs a delta review (see [pr8544-handoff.md](pr8544-handoff.md)). |

## Verdict and follow-up

- **Verdict: `changes-required`.** F1–F3 each have a retained probe and a coordinator replay against the pinned debug build.
- **GitHub review status: `CHANGES_REQUESTED` submitted.** F1 has a small, local fix and its same-host outcome (two databases sharing one volume file) is a corruption class. The author's Remarks admit only "next start may fail". F2 and F3 are cheap to fix alongside.
- **Follow-up review required: yes.** Before merge: (1) delta review of the F1/F2/F3 fixes and of the rebase onto `develop`, which must renumber the on-disk rcvindex and the error code; (2) rerun of the author's suite plus probes P1, R-1 and SYS-2 on the new head. Optional evidence: power-loss check R-2 and a release-build run. See [pr8544-handoff.md](pr8544-handoff.md).
- The PR approval gate was not applied because this review does not recommend a merge.

## Confirmed findings

### F1 (P2) — relocated restore of a rolled-back deletion rewrites `_vinf` with the old path; the restored database cannot start or adopts the original database's volume

- **Location (pinned head `e54b7611e68ac98361e27eb9814c7dd62b91b8e6`):** [`src/storage/disk_manager.c#L2937`](https://github.com/CUBRID/cubrid/blob/e54b7611e68ac98361e27eb9814c7dd62b91b8e6/src/storage/disk_manager.c#L2937) (`disk_delete_volume_rollback`, unconditional `logpb_recreate_volume_info`), called from [`disk_rv_complete_delete_volume`](https://github.com/CUBRID/cubrid/blob/e54b7611e68ac98361e27eb9814c7dd62b91b8e6/src/storage/disk_manager.c#L3053-L3100) (`:3053-3100`). Unchanged dependencies: `disk_set_link` undo payload = old `(next_volid, next_vol_fullname)` (`:1038-1053`); `disk_rv_undoredo_link` applies it blindly (`:1488`).
- **Preconditions:** a backup taken before the deletion. Then a deletion interrupted before its sysop commit (crash at FI 100003, a kill or power loss there, or an in-process abort), followed by a normal restart that rolls it back and writes the compensation records. Then `restoredb -u` of that backup to a different directory.
- **Mechanism:** during the restore replay, redo of the CLR writes the original path `P_V` into volume `V-1`'s link. `disk_rv_complete_delete_volume` sees the pending entry with `volid <= last_volid` and calls `disk_delete_volume_rollback`. `V` is already mounted and cached at the new path (`mounted again = 0, cached again = 0`), yet the function still rebuilds `_vinf` from the links. The correct new-path `_vinf` is replaced with one that names `P_V`.
- **Reproduction:** `probes/p1-relocated-rollback.sh` (`MODE=restart`), `p1.out` and `p1-restart.out`.
  - Other host (`KEEP_OLD=0`):
    - `restoredb -u` rc=0.
    - `new/dv26249_vinf` line `3 .../dv26249/dv26249_x003` (old path), while the restored file is `new/dv26249_x003`.
    - `spacedb -S` rc=1: `Unable to mount disk volume ".../dv26249/dv26249_x003".... No such file or directory`. `checkdb` rc=1.
  - Same host (`KEEP_OLD=1`):
    - `spacedb`/`checkdb` rc=0, but `spacedb` lists volume 3 as `.../dv26249/dv26249_x003`. That is the original database's file (md5 `b706c303…`), not the restored `new/dv26249_x003`, so two databases now share one volume file.
  - Control (`MODE=crash`, rollback done by the restore's own undo instead of a CLR replay): `_vinf` names `new/dv26249_x003`, and `spacedb`/`checkdb` pass. The defect needs the CLR-redo route.
- **Attribution:** introduced by this PR (new `RVDK_DELETE_VOLUME` record, new rollback step with the unconditional `_vinf` rebuild). Found independently by HA/compat (C1) and Recovery (R-3).
- **Relation to the PR's known limitation:** the Remarks say the next start "may fail with a volume-count mismatch". The replay shows a different failure mode ("unable to mount" via a stale `_vinf`). It also shows silent adoption of the original database's file on the same host, and an ordinary crash + restart (not only "undo during restore") triggers it.
- **Fix direction:**
  - In `disk_delete_volume_rollback`, recreate `_vinf` only when the volume had to be mounted or cached again. Better, rewrite `V-1`'s link to the **mounted** label (`fileio_get_volume_label (volid, PEEK)`) before rebuilding.
  - Do not mount a logged path without a `db_creation`/volid header check (see risk U-C2).

### F2 (P3) — DWB off: a second crash inside rollback recovery makes the database unstartable (`ER_BO_INCONSISTENT_NPERM_VOLUMES`)

- **Location (pinned head `e54b7611e68ac98361e27eb9814c7dd62b91b8e6`):** [`src/storage/disk_manager.c#L2715-L2728`](https://github.com/CUBRID/cubrid/blob/e54b7611e68ac98361e27eb9814c7dd62b91b8e6/src/storage/disk_manager.c#L2715-L2728) (`disk_delete_volume_extension`: parm update with `RVPGBUF_FLUSH_PAGE` undo, then `disk_set_link (…, NULL_VOLID, …)`). Unchanged: `disk_set_link` logs a flush-undo only when `next_volid != NULL_VOLID` (`:1024-1031`); `disk_rv_undoredo_link` does not flush (`:1488-1501`).
- **Preconditions:** `double_write_buffer_size=0`, deletion interrupted after the link cut and before commit (FI 100003), then restart #1 crashes between the parm flush-undo and the end-of-undo `pgbuf_flush_all` (`log_recovery.c:5275`).
- **Mechanism:**
  - Restart #1's mount phase sees a cut link and rewrites `_vinf` to `n−1` volumes (`boot_sr.c:1118-1130`).
  - Undo then writes `boot_Db_parm` (`n` volumes) to disk before the restored link reaches disk.
  - After a crash at that point, every start fails in `boot_find_rest_permanent_volumes`, before log recovery could replay the CLR.
  - This inverts the ordering the forward path relies on (the PR's own comment: "restart … fails when it finds fewer volumes than `boot_Db_parm` counts").
- **Reproduction:** `probes/r1-double-crash.sh` → `r1.out`.
  - DWB off: gdb hits `pgbuf_rv_flush_page` from `log_recovery_undo`, then `log_recovery.c:5275`, then the process is killed. `_vinf` drops from 4 to 3 entries. Restarts #2 and #3 both give rc=1, `Inconsistent 3 permanent volumes were found when 4 were expected`. Manually appending volume 3 to `_vinf` → `spacedb` rc=0, `checkdb` rc=0.
  - Control, DWB on: `_vinf` stays at 4, restarts rc=0.
- **Attribution:** introduced by this PR (new unlink-then-relink undo). The pre-existing `addvoldb` undo lowers the parm before cutting the link.
- **Impact:** permanent restart failure after a double crash in a short window with a supported non-default setting. No data loss, and the database can be repaired by hand.
- **Fix direction:**
  - Log an `RVPGBUF_FLUSH_PAGE` undo for `V-1`'s header page immediately before `disk_set_link (…, NULL_VOLID, …)`, or make `disk_set_link` log it unconditionally. Undo then makes the restored link durable before the parm.
  - With DWB on, keep the same order durable (for example a `dwb_synchronize` after the link undo).

### F3 (P3) — `delvoldb` reports success when the volume file is not removed

- **Location (pinned head `e54b7611e68ac98361e27eb9814c7dd62b91b8e6`):** [`disk_delete_volume_finish`](https://github.com/CUBRID/cubrid/blob/e54b7611e68ac98361e27eb9814c7dd62b91b8e6/src/storage/disk_manager.c#L2869-L2874) (`disk_manager.c:2869-2874`) → `fileio_unformat` → `(void) remove (…)` ([`file_io.c#L2735-L2740`](https://github.com/CUBRID/cubrid/blob/e54b7611e68ac98361e27eb9814c7dd62b91b8e6/src/storage/file_io.c#L2735-L2740)); `delvoldb` prints [`DELVOLDB_MSG_DONE`](https://github.com/CUBRID/cubrid/blob/e54b7611e68ac98361e27eb9814c7dd62b91b8e6/src/executables/util_sa.c#L6373) once `boot_delete_volume_extension` returns `NO_ERROR` (`util_sa.c`).
- **Reproduction:** `probes/sys2-unlink-fail.sh` → `sys2.out`. The volume is created with `addvoldb -F <dir>`, then `chmod a-w <dir>`.
  - `delvoldb -i 2` exits 0 and prints `"The volume (volume id: 2) has been deleted…"`.
  - `dv26249_x002` (64 MB) is still present.
  - `checkdb` passes.
  - A later `addvoldb -F <dir>` fails: `Volume ".../vols/dv26249_x002" already exists.`
- **Attribution:** new user-facing path (the `remove` silence itself is pre-existing, shared with `deletedb`). The code comment acknowledges "at worst an unused file is left", but the user is not told, and reclaiming disk space is the utility's purpose. Found by Systems (SYS-2) and Storage (ST-2).
- **Fix direction:** check the `remove` result (or re-check `fileio_is_volume_exist`) and print a warning that names the leftover path. Keep exit 0 or use a distinct code, since the database change is committed.

## Safety facts and effects outside the diff

| Effect / consumer | Safety fact | Owner | Evidence | Level | Remaining uncertainty |
|---|---|---|---|---|---|
| Crash recovery never needs the deleted file | Step-1 `logpb_checkpoint` makes the redo point the checkpoint itself in SA. No record between the checkpoint and the sysop touches V. SA vacuum runs at boot before the check. | Recovery | `page_buffer.c:4780-4785`, `log_page_buffer.c:7514-7519`, `disk_manager.c:2696-2714`, `boot_sr.c:2669-2678`; `delvol-crash.sh` passes 6/6 | 4 | Vacuum dropped-files argument is level 2 |
| All-or-nothing across a single crash (100005/100003/100004, DWB on/off, `_vinf` removed) | WAL holds; undo restores parm and link; the decision rule is "`volid > last_volid` after undo means committed" | Recovery | `delvol-crash.sh` 6/6 pass; `delvol-server-recovery.sh` pass | 5 | Double crash → F2 |
| Disk-cache accounting | `disk_cache_remove_volume` exactly reverses `disk_cache_load_volume` for DATA and TEMP. The PR also fixes the base TEMP-purpose aggregate in `disk_rv_redo_format`/`undo_format`. | Storage | source + `checkdb` passes after every scenario | 3–4 | — |
| Emptiness check | `nsect_free == nsect_total − (SECTOR(sys_lastpage)+1)`; `nsect_total` 64-sector aligned | Storage | source; basic test rejects a used volume | 4 | Can refuse a legal delete of a TEMP-purpose volume created by redo in the same process (safe direction) |
| Old dirty pages / DWB slots vs. a reused volid | `pgbuf_invalidate_all` flushes; dismount → `dwb_synchronize` before close/unlink | Storage, Concurrency | source; author's restore test with re-add at 128M passes (size and `checkdb`) | 4 | `suppress_fsync>0` (hidden) skips the drain (risk ST-3) |
| Interrupted restore resumed by a server start (C-1/ST-1) | Normal start redoes from the log header checkpoint, which cannot precede the deletion. In-place restore keeps the original header. | Recovery vs. Storage (disagreed) | Coordinator probe `st1-interrupted-restore.sh`: `restoredb` killed at `NEWVOL` redo, then `cubrid server start` ran **no recovery at all** (no recovery/DISK lines) | 4 for the in-place route; 3 for the H2–H4 routes | See risk U-ST1 |
| `RV_fun` table | 146 entries for 0..145, order checked by a debug startup assert | HA, Systems | script comparison + every debug run | 4 | Renumbering needed on rebase |
| HA appliers/CDC/flashback | All skip `LOG_DBEXTERN_REDO_DATA` regardless of rcvindex (`default: break`), same as `RVDK_NEWVOL` | HA | source | 3 | HA runtime not exercised |
| Backup LSA reset | Read only by `backupdb` level selection and dumps; not by archive purge, recovery or restore. Same reset as `renamedb`. | HA, Recovery | source; `delvol-incremental.sh` pass | 5 | Over-conservative after `restoredb` (product decision U-2) |
| CLI / catalogs / error code | Message args match; en/ko consistent; `cubrid.msg` 1..1405 contiguous; dispatch maps aligned | Systems | scripts, compile variants, ~15 argument-parsing runs | 4 | — |

## Coverage and verification

See [pr8544-coverage.md](pr8544-coverage.md) for the per-path table and shared questions.

**Checks run (coordinator):**

| Check | Command / artifact | Result |
|---|---|---|
| Patch identity | `git diff … \| sha256sum` | matches manifest |
| Debug build+install at head | `just build-and-install` (preset `debug_gcc`) | exit 0; 6 `-Wmaybe-uninitialized` warnings, all in unchanged lines of `network_interface_cl.c` |
| Static check | `cubrid-static-check 477fad77ae… e54b7611e6…` | 0 new cppcheck, clang-tidy or duplicated-code findings; `delvoldb` CCN 40 / 206 lines; `util_front.c` not fully analyzed by clang-tidy (base and head) |
| Author suite v4 (debug, 20M, isolated `runtime/`) | `delvol-{basic,crash,restore,incremental,server-recovery}.sh` | crash, restore (incl. `-u`), incremental and server-recovery: **pass**. basic: 16/17; the failure is the stale EOF-exit-0 assertion (`SYS-1`) |
| P1 (F1) | `probes/p1-relocated-rollback.sh` | reproduced (restart route); crash route clean |
| R-1 (F2) | `probes/r1-double-crash.sh` | reproduced with DWB off; DWB on clean |
| SYS-2 (F3) | `probes/sys2-unlink-fail.sh` | reproduced |
| ST-1 / C-1 | `probes/st1-interrupted-restore.sh` | not reproduced: the server start performed no recovery |
| Existing CI at head | `cubrid-ci status 8544`; run 45339539025 | build debug/release, `test_medium`, `test_sql`, `sql_by_cci` pass. `test_shell`: 1 NOK `shell/_06_issues/_26_2h/apis_1125` (Chronicle: 72 failures across many unrelated PRs on develop, 11-13…11-17; history context, not attributed). `"Check TC PRs"` failing (TC gate). |

**Not run or limitations:**
- Release-build execution (CI built release; the author reports basic/restore pass at an earlier head).
- HA runtime.
- valgrind.
- `suppress_fsync` and `no_logging` variants.
- Power-loss simulation.
- 128M `createdb` variants (the author ran them).

The Concurrency report comes from the earlier Codex attempt (model recorded as `gpt-6.1-sol` in the old manifest) and is marked `partial`. Its item 4 ("flush daemons do not run during recovery") was corrected by both Storage and Recovery (`log_manager.c:1453` enables them before `log_recovery`); there is no V page for them to write. Its open question C-1 is resolved above.

## Unverified risks and dropped candidates

| ID | Risk | Owner | Level | Decisive next check |
|---|---|---|---|---|
| U-R2 (P4) | With DWB off, step 4 unlinks V without fsyncing V-1's header or `_vinf`. A power loss can persist the unlink but lose the cut link, and boot then fails. Same pattern as `addvoldb`, but this step cannot be undone. | Recovery | 3 | `dm-log-writes` / `dm-flakey` power-cut at `fileio_unformat`; fix direction: `fileio_synchronize_all` before unlink |
| U-C2 (P3/P4 hardening) | `disk_delete_volume_finish` unlinks, and `disk_delete_volume_rollback` mounts, the **logged** path of an unmounted volume with no `db_creation`/volid check (unlike `log_recovery_notpartof_volumes`). Reachable only after interrupted restore or recovery with a mount miss. Matches the author's second limitation. | HA | 2 | gdb-driven P4 with strace on `unlink` |
| U-ST1 (P3 latent) | A mid-redo finish in `disk_rv_redo_dboutside_newvol` closes and reuses a volid without draining parallel redo workers. It is only reachable if a SERVER-mode recovery range contains `DELETE(V)` then `NEWVOL(V)`. The in-place interrupted-restore route was refuted at runtime; other routes are argued unreachable from source (Recovery H2–H4). | Storage / Recovery | 3 | Optional: interrupted `restoredb` with the backup's active log (H2) or archive-only (H3) layout, then server start |
| U-ST3 (P4) | Hidden `suppress_fsync>0` skips `dwb_flush_force` on dismount, so stale DWB slots could reach a reused volid during restore | Storage | 2 | `delvol-restore.sh` with `suppress_fsync=10` |
| U-NL | `no_logging=yes` would make a crash in the delete unrecoverable (same as `addvoldb`) | HA | 1–2 | Check whether SA utilities honor it; optionally refuse in `delvoldb` |
| SYS-3 / ST-5 (nit) | Redo/dump of `RVDK_DELETE_VOLUME` does not validate `rcv->length` or the volid range | Systems / Storage | 3 | Not reachable without log corruption |
| ST-4 (P4 model) | Per-entry `_vinf` rebuild and realloc during recovery | Storage | 2 | — |

**Not a defect:** `SYS-1`. The attached `delvol-basic.sh` v4 expects exit 0 on EOF cancel, but head returns 1 since `350c04f9b5`, as the PR body intends. The PR body's statement that "all six scripts pass at head" therefore does not hold for the attached v4 script; the author should attach the current script.

**Dropped / rejected (by reviewer):**
- Systems: 10 hypotheses rejected with evidence (dispatch alignment, option removal, catalog numbering, redo sizing, realloc/qsort/memmove, `-i` overflow, restart/shutdown pairing, compile variants, GNU indent).
- Storage: 14 (H1–H14), including the emptiness off-by-one and cache reversal; H14 was kept as U-ST1.
- Recovery: 10, including checkpoint redo bound, WAL, decision rule, backup-LSA durability and idempotence.
- HA: 11, including `RV_fun`, the applier, CDC, archive purge, `copydb`/`renamedb` and the contiguity assumptions.
- Concurrency: 5.

Duplicates merged: HA C1 + Recovery R-3 → F1; Systems SYS-2 + Storage ST-2 → F3; Concurrency C-1 + Storage ST-1 → U-ST1.

**Pre-existing (outside this PR, separate triage):**
1. A normal start after an interrupted `restoredb` can open a partially restored database without recovery. Observed in the ST-1 probe: 4 volumes after the server start, deleted volume 3 back.
2. `restoredb -d` resetlog keeps stale backup LSAs.
3. Committed `addvoldb` replay under `restoredb -u` formats the volume at the logged path (same family as F1).
4. Base `disk_rv_redo_format`/`undo_format` updated the wrong aggregate for TEMP-purpose permanent volumes; **fixed** by this PR.

## Budget accounting

- **Mode:** bounded (no explicit user limit). Per-specialist target ~25 min with an ~18 min checkpoint; coordinator reservation for builds, tests and replays. **No hard cap was enforced** (prompt targets only); overshoot occurred.
- **Agents in this session:** 4 (Systems `sonnet`, Storage `sonnet`, Recovery `opus`, HA/compat `sonnet`; effort `xhigh` from the pstack rule), no retries, no nested agents. The Concurrency seat reused the prior Codex report (no new agent).
- **Measured (harness-reported subagent tokens / wall time):**
  - Systems: 392,569 tok / 21.7 min
  - Storage: 428,168 tok / 25.6 min
  - Recovery: 312,060 tok / 20.8 min
  - HA/compat: 332,350 tok / 17.4 min
  - Specialist total: ~1.47 M tokens.
- **Self-reported working time:** Systems ~50, Storage ~35, Recovery ~40, HA ~45 min. All four exceeded the 25-minute target.
- **Unknown:** coordinator token usage and the prior Codex session's usage. Provider allowance telemetry is not available, so per-agent share of any quota is unverifiable.

## Local run archive provenance

Raw logs, probes, reviewer reports, JIRA attachments, and CI job logs remain archived locally outside Git at `/home/vimkim/temp/cubrid-pr-8544-review.PS3692/`.
