# Review of CUBRID/cubrid PR #8539 ([CBRD-26086])

- **Review date (`Asia/Seoul`):** `2026-11-24`
- **PR:** [CUBRID/cubrid#8539](https://github.com/CUBRID/cubrid/pull/8539) (`[CBRD-26086] Remove temporary volumes by scanning their directory at server start and stop`, author `hornetmj`, head `hornetmj/cubrid:CBRD-26086-temp-vol-remove` → `develop`)
- **Jira / Tracker:** [CBRD-26086](https://jira.cubrid.org/browse/CBRD-26086) · Tracker `#1067`
- **Snapshot:** head `101106d2eebc4c49b63b6c9c1d31a2db45978c57`, base and merge base `5962ff2901c8e74fd941f1aa7df697de4ed10697`
- **Comparison:** `git diff --no-ext-diff --binary --full-index 5962ff2901c8e74fd941f1aa7df697de4ed10697 101106d2eebc4c49b63b6c9c1d31a2db45978c57 --`. Patch SHA-256 `03140c14966ade51fb83735a91555e2f235242e94c43235c533828b3d52cf40d`.
- **Most consequential result:** the new classifier's fcntl-lock guard never applies to a real CUBRID data volume. CUBRID neither locks data volumes while it formats them nor when it mounts them. The new directory scan also reaches every `<db>_t<N>` name. As a result, starting, stopping or deleting database `X` deletes the volume of another database while that volume is being formatted, if the file is named `X_t<N>`. Replayed twice on the pinned build.

## Verdict and follow-up

| Item | Value |
|---|---|
| Verdict | `changes-required` (one confirmed P3 defect) |
| GitHub review status | `CHANGES_REQUESTED` submitted |
| Follow-up review required | **yes**. The author must either fix the guard or explicitly accept the risk and correct the comment, the PR table and test 4-3. A delta review of the new head is then needed (see [pr8539-handoff.md](pr8539-handoff.md)). |
| Coverage | Complete for the assigned scope (Systems/Storage, Storage/Recovery, lifecycle concurrency). HA is not applicable (reason below). See [pr8539-coverage.md](pr8539-coverage.md). |

The PR otherwise achieves its goal. The gap case is fixed, all 8 author-defined behaviors hold at the pinned head, and the cleanup is idempotent and recovery-safe.

## Confirmed findings

### F1 (P3): deletes another database's volume while that volume is being formatted, because the fcntl-lock guard never covers data volumes

- **Location (pinned head `101106d2eebc4c49b63b6c9c1d31a2db45978c57`):**
  - [`src/storage/disk_manager.c#L6407-L6480`](https://github.com/CUBRID/cubrid/blob/101106d2eebc4c49b63b6c9c1d31a2db45978c57/src/storage/disk_manager.c#L6407) (`disk_is_permanent_volume_file`): the `F_GETLK` block and its comment, "A permanent volume is locked by the process that formats or mounts it…".
  - [`src/transaction/boot_sr.c#L1053`](https://github.com/CUBRID/cubrid/blob/101106d2eebc4c49b63b6c9c1d31a2db45978c57/src/transaction/boot_sr.c#L1053) (`boot_remove_temp_volume_file`): it classifies a candidate, then calls `pgbuf_invalidate_all` and `fileio_unformat`.
  - The PR body: its table row "다른 프로세스가 fcntl 락을 잡음(포맷 중이거나 마운트 중인 permanent 볼륨) → 모름 → 남김" and Verification 4-3.
- **Facts (pinned source):**
  - `disk_format` calls `fileio_format(..., is_sweep_clean = (purpose == DB_PERMANENT_DATA_PURPOSE), is_do_lock = false, ...)` ([`disk_manager.c#L580`](https://github.com/CUBRID/cubrid/blob/101106d2eebc4c49b63b6c9c1d31a2db45978c57/src/storage/disk_manager.c#L580)). The purpose flag is the sweep-clean argument, not the lock argument (`fileio_format` signature at [`file_io.c#L2312`](https://github.com/CUBRID/cubrid/blob/101106d2eebc4c49b63b6c9c1d31a2db45978c57/src/storage/file_io.c#L2312)).
  - `boot_mount` calls `fileio_mount(..., lock_wait = false, ...)` ([`boot_sr.c#L1257`](https://github.com/CUBRID/cubrid/blob/101106d2eebc4c49b63b6c9c1d31a2db45978c57/src/transaction/boot_sr.c#L1257)).
  - Among database files only the active log is locked (`log_manager.c:1200`, `log_page_buffer.c:1571`).
  - Page 0 has no CUBRID header until the end of `disk_format`, so during the format the file is a regular file with no lock and no magic. `disk_is_permanent_volume_file` therefore returns `is_permanent=false`, and the file is unlinked.
- **Preconditions:**
  - A second process creates a file named exactly `X_t<NNN>` in X's temporary-volume directory: `createdb` of a database named `X_t100`, `addvoldb -n X_t500 -F <X dir>` of another database, or `restoredb` or `copydb`.
  - `NNN` is greater than X's last permanent volid.
  - X starts, stops, or runs `deletedb` (or any SA utility boot/shutdown) during that format window. The window lasts the whole volume format, which takes seconds or longer for large volumes.
  - Default configuration. The hidden `dbfiles_protect=yes` adds a read lock that would close the gap.
- **Replay (coordinator, level 5, pinned debug build `11.5.0.3013-101106d`):**
  1. **`addvoldb` run (`ss1.sh` → `ss1.out`):**
     - DB A `t26086ss` was running. DB B `s26086b` ran `cub_admin addvoldb -S -p temp -n t26086ss_t500 -F <A dir>` under gdb, stopped at `disk_stab_init`, which is after file creation and before the header is written.
     - Stopping server A printed `after A stop: REMOVED`.
     - `addvoldb` then completed with rc=0, and `checkdb -S` of B failed with rc=1: `Unable to mount disk volume ".../t26086ss_t500".... No such file or directory`.
     - **Expected:** the file is kept, as the PR table promises. **Actual:** B's new volume was deleted and B can no longer restart.
  2. **`createdb` run (`sr1.sh` → `sr1.out`):**
     - `/proc/locks` showed 0 locks on A's running primary volume and 1 on `_lgat`. This confirms that a mounted data volume has no lock.
     - `cub_admin createdb t26086sr_t100` ran in A's directory under gdb, stopped at `disk_stab_init`. The file was 64 MB with 0 locks.
     - Stopping A printed `REMOVED`.
     - The later start failure of `t26086sr_t100` (`Unable to mount disk volume … No such file`) is confounded, because gdb killed the paused `createdb` at quit. Only the removal step counts as evidence from this run.
- **Attribution:**
  - In base, `boot_remove_all_temp_volumes` returns early when `temp_nvols == 0`, and it runs the unknown-volume scan only before the server is restarted. That scan goes downward from 32766 and stops at the first missing number. So base never reaches `X_t500` or `X_t100` in these scenarios (`git show 5962ff2901:src/transaction/boot_sr.c`, function `boot_remove_all_temp_volumes`).
  - Attribution rests on this level-3 source argument. No base binary was built for a contrast run.
  - For volumes with a valid header the PR is strictly safer than base: base deleted in-range files with no type check at all. The newly exposed case is only the headerless window.
- **Impact:** silent loss of another database's volume while it is being created. The creating process writes to an unlinked inode and the new database or volume becomes unmountable. Reach is low, because it needs the `X` / `X_t<digits>` naming in one directory plus a start or stop of X during the format.
- **Fix direction (author's choice):**
  - (a) Do not delete a headerless `<db>_t<N>` that this process cannot prove is its own temp volume. For example, remove mounted temp volumes by volid from the fileio table at shutdown. At restart, accept a headerless file only when it is empty, or is not recently modified, or another rule shows it cannot be an in-progress format.
  - (b) Take a real non-blocking write lock while formatting and mounting permanent volumes. This is a larger behavior change.
  - (c) At minimum, correct the comment in `disk_is_permanent_volume_file`, the PR table and test 4-3, which simulates a lock that production never takes, and record the accepted risk.
- **Independent discovery:** found separately by both specialists, as SS-1 (opus) and SR-1 (sonnet), and deduplicated here. SR-1 correctly identified that `is_do_lock` is always false. SS-1 had attributed the lock to permanent-purpose volumes.

## Safety facts and effects outside the diff

| Safety fact | Owner | Evidence | Level | Result |
|---|---|---|---|---|
| Name filter accepts exactly `fileio_make_volume_temp_name` output (`%03d`) with `last_volid < volid ≤ 32766` | Systems/Storage, Storage/Recovery | name_probe (42 cases), name_filter_probe (ASan), production source compiled with stubs | 4 | Holds |
| A mounted permanent volume is never reopened, at all three call sites (restart [`2568`](https://github.com/CUBRID/cubrid/blob/101106d2eebc4c49b63b6c9c1d31a2db45978c57/src/transaction/boot_sr.c#L2568), shutdown [`3098`](https://github.com/CUBRID/cubrid/blob/101106d2eebc4c49b63b6c9c1d31a2db45978c57/src/transaction/boot_sr.c#L3098), deletedb [`5343`](https://github.com/CUBRID/cubrid/blob/101106d2eebc4c49b63b6c9c1d31a2db45978c57/src/transaction/boot_sr.c#L5343)) | both | `disk_Cache` is initialised at each site; classify_probe S6 | 3–4 | Holds. It assumes contiguous volids `0..nvols_perm-1` and a non-NULL `disk_Cache` (SR-I1, informational) |
| A formatted permanent volume of this or another DB is kept | both | permname and otherdb runtime cases | 5 | Holds |
| A file another process is formatting is kept | both | ss1/sr1 replay | 5 | **Fails: F1** |
| A file another process locks is kept | coordinator | `locked.sh`: kept at stop and start, removed after unlock, 2 notifications | 5 | Holds, but no CUBRID data path takes such a lock (F1) |
| An unreadable file is kept | coordinator (author case) | unreadable case | 5 | Holds |
| Gap below a missing number is cleaned and the number is reusable | coordinator | `gap.sh` | 5 | Holds (fixed by this PR) |
| Restart runs after recovery, and `boot_Db_parm` is fresh | Storage/Recovery | `log_recovery.c:888/901` `boot_reset_db_parm`, F5 | 3 | Holds |
| A crash during the new cleanup is idempotent; the dbparm reset is logged and the temporary transaction commits | Storage/Recovery | H6 | 3 | Holds |
| `temp_nvols`/`temp_last_volid` readers stay consistent (first temp volid 32766) | Storage/Recovery | grep of all readers (`boot_sr.c` only), stop/crash/tracked runtime | 5 | Holds |
| A standalone utility (SA) boot/shutdown removes stale temp volumes | coordinator | `locked.sh` SA leg: crash left 2, `checkdb -S` rc=0 left 0 | 5 | Holds |
| readdir with unlink during iteration; errno handling | Systems/Storage | readdir_probe (5000/5000 on xfs); errno reset before each readdir | 4 | Holds |
| The header read is a plain pread (no TDE, no checksum, no O_DIRECT) | both | `file_io.c` source; header page never encrypted | 2–3 | Holds. A TDE run was not performed |
| HA: temp volume add/remove is not logged or replicated | Storage/Recovery | `disk_format` logs only when the volume type is permanent; dbparm is updated through a local heap | 2 | Not applicable |

## Coverage and verification

See [pr8539-coverage.md](pr8539-coverage.md).

**Checks run (all on the pinned head; `debug_gcc` preset, `cubrid_rel` = `11.5.0.3013-101106d`):**

| Check | Command or artifact | Result |
|---|---|---|
| Build and install | `just build-and-install` | pass (exit 0). Earlier incomplete build log stopped at 894/1501. |
| Static check | `cubrid-static-check 5962ff2901 101106d2ee` | 3 clang-tidy leads, all cleared by the Systems reviewer (loop bound ≤ 32766 is asserted; `strncmp` stops at the magic's NUL; the `atoi` input is length-checked and round-tripped). Complexity grew in `disk_is_permanent_volume_file` (CCN 17) and `boot_remove_temp_volumes` (CCN 14); noted, not a defect. |
| Author suite, 8 cases | `bash scripts/all.sh` with isolated env (port 47311, private `CUBRID_DATABASES`/`CUBRID_TMP`) | 8/8 pass: stop, crash, tracked, permname, otherdb, unreadable, temppath, deletedb |
| Author gap case | `scripts/gap.sh` | pass (0 files after start; re-add rc=0/0) |
| Coordinator locked + SA probe | `locked.sh` | pass |
| F1 replay (addvoldb) | `ss1.sh` | defect reproduced |
| F1 replay (createdb, `/proc/locks`) | `sr1.sh` | removal reproduced; no lock on data volume |
| Reviewer probes | name, readdir, fcntl and classifier models | passed within stated model limits |

The author's scripts were downloaded from the JIRA attachments (verified by SHA-256 checksums in the run archive).

**Not run:**
- release build and `-Werror` compile (the author reports one);
- TDE-enabled permname case;
- base-binary contrast of F1;
- Windows build (`dirent.h` use matches `file_io.c`);
- SS-2 replay;
- a large-buffer-pool timing of `pgbuf_invalidate_all` per unknown file;
- an old (pre-11) volume-header layout.

**PR movement:** head is unchanged at finalisation (`101106d2ee…`, base `5962ff2901…`). `develop` advanced from `8e052e99c5` to `696c75dceb` during the review. The PR's merge base is unchanged, and the advance was not reviewed.

## Unverified risks and dropped candidates

| ID | Risk | Owner | Status / next check |
|---|---|---|---|
| SS-2 (P4, info) | A symlink or hard link named `<db>_t<N>` that points to a file this process locks outside `disk_Cache` (`_lgat`, `databases.txt`, keys) passes the inode guard. Closing the second fd then releases this process's own lock. Needs a deliberately misleading link. | Systems/Storage | Unverified (level 3 + OS model). Cheap hardening: `lstat`/`O_NOFOLLOW` + `S_ISREG`, or also check system-volume fds. |
| SS-U1 | `pgbuf_invalidate_all` is a linear scan of the buffer pool for each removed unknown file at restart (base did this only for tracked ones). | Systems/Storage | Not measured; low. |
| SS-U2 | A permanent volume with an older header layout might be misclassified. | Systems/Storage | Not verified; low. |
| SR-I1 | The guard dereferences `disk_Cache` without a NULL check and assumes contiguous volids. True at all current callers. | Storage/Recovery | Hardening only. |
| SR-I2 | With hidden `dbfiles_protect=yes`, extra error/notification noise appears. | Storage/Recovery | Informational. |
| SR-I3 | At shutdown, a mounted temp volume whose header cannot be read (`EMFILE`/`EIO`) is left until the next start. | Storage/Recovery | Informational behavior change. |
| Disclosed | A same-named DB sharing `temp_volume_path` can lose live temp volumes; a permanent `<db>_t32766` blocks temp creation. | — | Disclosed in PR Remarks; the review found nothing worse. |

**Dropped or cleared hypotheses:**
- **Systems/Storage:** 3 static leads, the errno/readdir handling, Windows portability, header TDE, temp-path mismatch.
- **Storage/Recovery:** H1–H14, which include a stale dbparm after recovery, crash mid-addvoldb, a stale `disk_Cache`, daemons touching removed pages, `EMFILE`, and the notification range.
- All of these were disproven by source and/or probes. None was left untested for lack of time.
- **Duplicates:** SS-1 and SR-1 were merged into F1.

**Pre-existing, not attributed to this PR:** shutdown leaves `disk_Cache` temp entries stale, and daemons can still race with page invalidation. Both are unchanged from base.

## Budget accounting

- **Mode:** bounded default; no user-supplied absolute budget. No hard cap was enforced. Targets were prompt-level and time-based only.
- **Agents (this session):** 2 specialists, run in parallel.
  - Systems/Storage on `opus`: 149,643 subagent tokens, 38 tool uses, about 7.5 min.
  - Storage/Recovery on `sonnet`: 288,570 subagent tokens, 72 tool uses, about 14.4 min. This exceeded its ~25-minute *work* target in tokens rather than time; measured tokens are reported, and nothing was enforced.
  - Retries: 0.
- **Models:** pstack `interrogate reviewers: opus, sonnet` was used, so the shared challenge got model diversity. The prior Codex attempt planned `gpt-6.2-sol`/`astra` reviewers but produced no reviewer output, and its usage is unknown.
- **Coordinator:** build, 5 runtime scenarios, about 50 minutes of elapsed time. Token usage is unknown (no telemetry).
- **Total envelope:** the original 35-minute target was exceeded. The resumed run took about 60 minutes of elapsed time, mainly the runtime replays. That overshoot is disclosed here.

## Local run archive provenance

Raw logs, probe scripts, reviewer transcripts, and build outputs remain archived locally outside Git at `/home/vimkim/temp/cubrid-pr-8539-review.4Sz0gW/`.
