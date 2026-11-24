# Handoff: PR #8539 review follow-up ([CBRD-26086])

1. **Goal and stop reason.**
   - Reviewed [CUBRID/cubrid#8539](https://github.com/CUBRID/cubrid/pull/8539) (tracker `#1067`) at pinned head `101106d2ee`.
   - The snapshot review finished with verdict `changes-required` (`F1`, P3, confirmed). See [pr8539-review.md](pr8539-review.md).
   - Follow-up is required because the author must resolve `F1` and the new head needs a delta review.
2. **Identity.**
   - Repository `CUBRID/cubrid`, PR https://github.com/CUBRID/cubrid/pull/8539, compared by merge base.
   - Base and merge base `5962ff2901c8e74fd941f1aa7df697de4ed10697`; head `101106d2eebc4c49b63b6c9c1d31a2db45978c57`.
   - Patch SHA-256 `03140c14966ade51fb83735a91555e2f235242e94c43235c533828b3d52cf40d`.
3. **Locations.**
   - Published docs: [pr8539-review.md](pr8539-review.md), [pr8539-coverage.md](pr8539-coverage.md), [pr8539-handoff.md](pr8539-handoff.md).
   - Local run archive: `/home/vimkim/temp/cubrid-pr-8539-review.4Sz0gW/` (`report.md`, `coverage.md`, `manifest.md`, `handoff.md`, `reviewers/`, `evidence/`, `runtime/`).
   - Policies: `/home/vimkim/my-cubrid/CUBRID.md`, `src/storage/AGENTS.md`, `src/transaction/AGENTS.md`.
4. **Findings and open items.**
   - `F1` (P3, level 5): a headerless `X_t<N>` file is unlinked while another process is formatting it. Data volumes are never fcntl-locked (`disk_manager.c:580` `is_do_lock=false`; `boot_sr.c:1257` `lock_wait=false`), so the `F_GETLK` guard and PR test 4-3 do not protect production.
   - `SS-2` (P4, unverified, level 3): a symlink or hard link to a file this process locks (`_lgat`) makes it release its own lock.
   - `SS-U1` (perf, unmeasured), `SS-U2` (old header layout), `SR-I1`/`I2`/`I3` (informational).
   - There is no reviewer disagreement.
5. **Remaining scope:**
   - the delta between `101106d2ee` and the author's next head (`disk_manager.c` `disk_is_permanent_volume_file`, `boot_sr.c` `boot_remove_temp_volume_file`/`boot_remove_temp_volumes`);
   - the callers at `boot_sr.c` restart, shutdown and deletedb;
   - optionally: a release `-Werror` build, a TDE permname run and a base-binary contrast for `F1`.
6. **Commands and environment.**
   - From `/home/vimkim/gh/cb/CBRD-26086` (review role; do not push): `just build-and-install`.
   - Then `cd <run>/runtime && source env.sh && setsid -w timeout 3000 bash scripts/all.sh`, followed by `scripts/gap.sh`, `scripts/locked.sh`, `scripts/ss1.sh` and `scripts/sr1.sh`. Each is `setsid -w … </dev/null > file 2>&1`.
   - The environment is isolated (port 47311, private DB dir). Run servers serially.
7. **Budget.** The original envelope is spent and overshot (see [pr8539-review.md](pr8539-review.md#budget-accounting)). The delta review needs a new allocation; one Systems+Recovery reviewer is enough unless the fix changes locking in `fileio_format` or `fileio_mount`.
8. **Proposed assignment.**
   - Check that the fix prevents unlinking a file that is being formatted. Replay `ss1.sh` and `sr1.sh`; expect the file to be kept and the DB to start.
   - Re-run the 8 cases plus gap and locked.
   - If the fix adds locks to data-volume format or mount, add a Concurrency/HA reviewer for backup, restore, copydb and HA tools that open volumes.
   - Done when `F1` is resolved or explicitly accepted with a corrected comment and PR text, and `SS-2` is hardened or accepted.
9. **Finish conditions.** Re-pin the new head and base. Revalidate the affected callers. Keep the original snapshot report intact.
