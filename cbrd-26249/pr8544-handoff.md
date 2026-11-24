# Handoff — CUBRID/cubrid#8544 ([CBRD-26249]) review

## 1. Goal and why this stops here

The goal was a full specialist review of [CUBRID/cubrid#8544](https://github.com/CUBRID/cubrid/pull/8544) (stand-alone `delvoldb`), tracker `#1070`. The review at the pinned snapshot is complete: verdict `changes-required`, with three confirmed findings (`F1` P2, `F2` P3, `F3` P3). See [pr8544-review.md](pr8544-review.md) and [pr8544-coverage.md](pr8544-coverage.md).

Follow-up is required because:
- (a) the author must fix `F1`–`F3`;
- (b) the PR is `CONFLICTING` with `develop` and its rebase must renumber an on-disk log record index and an error code;
- (c) some optional evidence remains (`U-R2` power loss, release run).

## 2. Identity

- Repo: `CUBRID/cubrid`, PR https://github.com/CUBRID/cubrid/pull/8544 (author `hornetmj`, `CBRD-26249-delvoldb-last` → `develop`). This is a review checkout: no push or CI authorization.
- Comparison: merge base → head. `git diff --binary --no-ext-diff --no-textconv 477fad77ae87ae1f831f5bea23ce4d4af88f0681 e54b7611e68ac98361e27eb9814c7dd62b91b8e6`
- Base = merge base `477fad77ae87ae1f831f5bea23ce4d4af88f0681`; head `e54b7611e68ac98361e27eb9814c7dd62b91b8e6`; patch sha256 `40868ececcd4eed7fbffb58eb01c37620229a5f75a887257a175df01a06ae7af`.
- `develop` at recheck: `c59a6e30a70a3912c1e26e0786cc6a9f43ecbc5e`. It has taken rcvindex 145 (`RVHF_SERIAL_DDL_UPDATE_UNDO`) and error −1404 (`ER_BT_LOAD_NO_LOGGING_DURING_BACKUP`).

## 3. Locations

- Published docs: [pr8544-review.md](pr8544-review.md), [pr8544-coverage.md](pr8544-coverage.md), [pr8544-handoff.md](pr8544-handoff.md).
- Local run archive (`/home/vimkim/temp/cubrid-pr-8544-review.PS3692`):
  - Main documents: `report.md`, `coverage.md`, `manifest.json`, `pr-summary-ko.md`.
  - Reviewer reports: `reviewers/{systems,concurrency,storage,recovery,ha-compat}.md`.
  - `evidence/`: `pr.patch`, `pr-initial.json`, `jira.txt`, `jira-attachments` (author tests v4), `static-check.md`, build log, `ci/` job logs.
  - Probes: `probes/{p1-relocated-rollback,r1-double-crash,sys2-unlink-fail,st1-interrupted-restore}.sh`, with outputs in `runtime/logs/`.
  - Runtime env: `runtime/env.sh`. It uses the isolated `CUBRID_DATABASES` and `CUBRID_TMP` under `runtime/`, install `/home/vimkim/.cub/install/CBRD-26249/debug_gcc`, and test port 34163.
- Policies: `/home/vimkim/my-cubrid/CUBRID.md`, `/home/vimkim/.agents/skills/cubrid-code-review/`, `src/AGENTS.md`.

## 4. Findings and open questions (stable IDs)

- **F1 (P2, confirmed L5):** a `restoredb -u` replay of a rolled-back deletion (CLR route) rewrites `_vinf` from links that hold the old path. The restored DB then cannot start, or on the same host mounts the original database's volume. Root: unconditional `logpb_recreate_volume_info` in `disk_delete_volume_rollback` (`disk_manager.c:2937`) plus the link CLR carrying the old path.
- **F2 (P3, confirmed L5):** with DWB off, a double crash during rollback recovery makes every start fail with `ER_BO_INCONSISTENT_NPERM_VOLUMES`. Root: the parm flush-undo precedes link restoration; `disk_set_link` logs no flush-undo when unlinking.
- **F3 (P3, confirmed L5):** a silent `remove()` failure still yields exit 0 and the `"has been deleted"` message.
- **Unverified risks:**
  - `U-R2` (P4, power loss, DWB off: no fsync of V-1 header/`_vinf` before unlink)
  - `U-C2` (P3/P4: logged-path unlink/mount without an ownership check)
  - `U-ST1` (P3 latent: no drain of redo workers before a mid-redo volid reuse; the in-place resume route was refuted at runtime; the H2/H3 layouts are source-only)
  - `U-ST3` (P4: `suppress_fsync`)
  - `U-NL` (`no_logging`)
  - `SYS-3`/`ST-5` (nits)
- **Disagreement record:** Storage proposed `ST-1` as P2; Recovery argued it is unreachable. The coordinator probe supports Recovery for the in-place route.
- **Not a defect:** `SYS-1`, a stale EOF assertion in the attached `delvol-basic.sh` v4.

## 5. Inspected scope and what remains

All 25 changed paths are covered (see [pr8544-coverage.md](pr8544-coverage.md)). What remains:
- **Delta review after the author's fix and rebase.** Focus on:
  - the renumbered `RVDK_DELETE_VOLUME` (check the `RV_fun` order and the debug startup assert);
  - the renumbered `ER_DISK_CANNOT_DELETE_VOLUME` (both `cubrid.msg` catalogs, `ER_LAST_ERROR`);
  - the `log_recovery.c` merge around `boot_reset_db_parm` / `disk_rv_complete_delete_volume`;
  - the F1/F2/F3 fix hunks and their callers (`disk_rv_complete_delete_volume`, `disk_set_link` users, `fileio_unformat` users).
- **Optional:**
  - `U-R2` power-cut test;
  - `U-ST1` with H2/H3 restore layouts;
  - release-build execution of `delvol-basic.sh`/`delvol-restore.sh`;
  - HA smoke (HA probe P3).

## 6. Next commands and environment

```sh
source /home/vimkim/temp/cubrid-pr-8544-review.PS3692/runtime/env.sh
# after the new head is built and installed into the install prefix above (cd ~/gh/cb/CBRD-26249 && just build-and-install, checkout at the new head)
S=/home/vimkim/temp/cubrid-pr-8544-review.PS3692/evidence/jira-attachments/x-delvoldb-tests-v4   # or the author's updated tests
P=/home/vimkim/temp/cubrid-pr-8544-review.PS3692/probes
for t in basic crash restore incremental server-recovery; do bash $S/delvol-$t.sh </dev/null; echo "$t exit=$?"; done
MODE=restart KEEP_OLD=0 bash $P/p1-relocated-rollback.sh </dev/null   # F1: expect spacedb/checkdb rc=0 and _vinf naming new/…
MODE=restart KEEP_OLD=1 bash $P/p1-relocated-rollback.sh </dev/null   # F1: expect spacedb to list new/dv26249_x003
DWB=off REPAIR=0 bash $P/r1-double-crash.sh </dev/null                # F2: expect restart #2/#3 rc=0
bash $P/sys2-unlink-fail.sh </dev/null                                # F3: expect a warning naming the leftover file
```

Run the scripts serially; they share DB name `dv26249` and port 34163. Add `/usr/sbin` to `PATH` if `ss` is needed (`server-recovery` prints a harmless `"ss: command not found"` otherwise). The `r1` probe's gdb breakpoint `log_recovery.c:5275` must be re-pinned to the `pgbuf_flush_all` line at the end of `log_recovery_undo` in the new head.

## 7. Budget

This run's budget is spent: 4 specialists, ~1.47 M subagent tokens, every one over its 25-minute target, and coordinator usage unknown. No hard cap was enforced. A delta review needs a new allocation; reusing an assignment does not reset its budget. A narrow delta needs 1–2 seats: Recovery+Storage for F1/F2, Systems for F3, plus the renumbering checks.

## 8. Proposed focused assignments

| Question | Seat | Completion condition |
|---|---|---|
| F1 fix correct for crash route, CLR route, same host and other host | Recovery (+ HA as a second seat if it fits) | P1 all four variants pass; `_vinf` and link name the mounted label; no mount of a logged path without a header check |
| F2 fix restores link durability before the parm | Recovery | `r1-double-crash.sh` DWB off and on both pass; the author's crash suite passes |
| F3 user feedback | Systems | Warning names the leftover path; exit-code contract documented |
| Rebase renumbering | HA/Systems | `RV_fun` order assert passes; message catalogs contiguous; no rcvindex collision with `develop` |

## 9. Conditions to finish

- A new head is pinned and its patch is hashed.
- F1–F3 are fixed and their probes pass.
- The rebase delta has been reviewed, including the renumbering.
- The author suite passes, with the updated basic script.
- CI (`test_shell` beyond the known `apis_1125` noise) and the TC merge gate are resolved by the author.
- If a merge is to be recommended, the PR approval gate has been run.
