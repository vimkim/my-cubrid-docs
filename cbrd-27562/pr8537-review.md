# Code review: CUBRID PR #8537 — [CBRD-27562] No sysop for temp sector reservation / temp volume growth

- **Review date (`Asia/Seoul`):** `2026-11-24`
- **PR:** [CUBRID/cubrid#8537](https://github.com/CUBRID/cubrid/pull/8537) (`[CBRD-27562] Do not start a system operation for temporary sector reservation or temporary volume growth`, author `hornetmj`, head `hornetmj:CBRD-27562-temp-no-sysop` → `develop`)
- **Jira / Tracker:** [CBRD-27562](https://jira.cubrid.org/browse/CBRD-27562) · Tracker `#1069`
- **Base / merge base:** `13131ed83272e39c131238ee284553779e49b6b2`
- **Head:** `e863def7872adab232300b4f91f53aa46da0c0e6`. The remote was rechecked before finalizing and was unchanged.
- **Patch SHA-256:** `b11b63626e01eafe060ceddbc84640ac9850b18821c08893eab852c54a708d57`
- **Goal:** verify that removing the system operation (and the log flushes) from temp-purpose sector reservation and temp-type volume add/expand keeps crash, abort and temp-volume invariants, and does not break permanent volumes.

## Verdict

**`no-confirmed-findings`**. GitHub review status: **`APPROVED` submitted**.

**Follow-up review required: no.** All planned coverage completed (see [pr8537-coverage.md](pr8537-coverage.md)). The residual checks listed below are optional and do not block merge.

The patch gates every sysop start/commit/abort and every log flush on `voltype == DB_PERMANENT_VOLTYPE` (add/expand/format) or on `purpose != DB_TEMPORARY_DATA_PURPOSE` (reserve) in [`src/storage/disk_manager.c`](https://github.com/CUBRID/cubrid/blob/e863def7872adab232300b4f91f53aa46da0c0e6/src/storage/disk_manager.c#L4142). No `log_append_*` call or its guard changed. Temp-purpose sector bits and temp-type volume headers were never logged in the base, so the removed sysops were empty and protected nothing. Runtime probes on a debug build of the pinned head confirmed:

- crash recovery during temp volume growth,
- crash recovery for a permanent volume with temp purpose,
- exact cache and bitmap accounting after repeated reservation failures and cancellations in parallel workers,
- zero system operations for a parallel sort.

## Confirmed findings

None.

## Non-defect notes (optional)

- **N1 (comment wording, nit).** [`src/storage/file_manager.c#L3162-L3165`](https://github.com/CUBRID/cubrid/blob/e863def7872adab232300b4f91f53aa46da0c0e6/src/storage/file_manager.c#L3162-L3165) says "Before CBRD-27562, `file_create()` opened a system operation for a temp file too". Strictly, `file_create` never opened one for a temp file (`do_logging = !is_temp`). It was its callee `disk_reserve_sectors`. Suggested wording: "`file_create() → disk_reserve_sectors()` opened…". Found by Storage/Concurrency; the coordinator confirmed it at `file_manager.c:3346/3394-3399`.
- **PE1 (pre-existing, not attributed).** In `disk_volume_expand`, a temp volume header's `nsect_total` is incremented and dirtied before `fileio_expand_to`. If the expand fails (`ENOSPC`), nothing restores the header. The base had the same order, and its temp sysop held no undo, so it could not restore it either. Debug builds `assert (false)` there ([`disk_manager.c#L2022-L2028`](https://github.com/CUBRID/cubrid/blob/e863def7872adab232300b4f91f53aa46da0c0e6/src/storage/disk_manager.c#L2022-L2028)). Found by Systems/HA and Recovery at source level (L3). It was not reproduced, and the change does not make it worse.
- **PE2 (pre-existing, benign).** `disk_reserve_from_cache` reads `extend_info->nsect_total` for the `temp_file_max_size_in_pages` check under the reserve mutex, while `disk_extend` updates it under `mutex_extend`. This stale read already existed across transactions in the base.

## Safety facts and effects outside the diff

| Changed behavior | Safety fact | Owner | Evidence | Level |
|---|---|---|---|---|
| Temp-purpose `disk_reserve_sectors` opens no sysop | Temp bits are unlogged (`disk_stab_unit_reserve` logs only permanent purpose, `disk_manager.c:3681-3688`), and the error path reverts bits and cache explicitly | Storage/Concurrency | P3a: 6× `ER_BO_MAXTEMP_SPACE_HAS_BEEN_EXCEEDED` in parallel workers; online `checkdb -C` after each (`disk_check` compares bitmap and cache per volume and per purpose, and a debug assert fires on mismatch) gave rc 0 each time; the server never crashed | 5 |
| Temp-type add/expand opens no sysop and skips the log flush | No WAL exists for temp type; restart mounts only permanent volumes and destroys unknown temp files | Recovery | P1: gdb on a parallel sort worker (`sort_listfile_execute`) hit the temp add before `boot_dbparm_save_volume` and the temp expand before `fileio_expand_to`, both with `tdes->topops.last = -1`; SIGKILL at the expand; the restart log shows `Volume "…_t32766" is unknown at server restart` → `Destroyed volume`; recovery finished; query returned 81920; `checkdb -S` 0 | 5 |
| Permanent-type volume with temp purpose | Format undo, sysop and flush are keyed by type and preserved; boot resets the temp-purpose bitmap | Recovery + Storage/Concurrency | P2: `addvoldb -p temp`; gdb hit a temp reservation on volid 2 (perm type, temp purpose) with `topops.last=-1`; SIGKILL; restart recovery OK; volume retained; query 81920; `checkdb -S` 0 | 5 |
| `boot_dbparm_save_volume` assert moved into the permanent branch | The permanent caller still holds the sysop; the temp path touches only in-memory `boot_Db_parm` | Recovery | Source (L3). The P1 debug build passed through the temp call without an assert | 5 |
| Workers of one transaction now overlap in reserve/extend | Only thread-, page- or global-keyed state is touched, each with its own lock (reserve mutex per purpose, global `mutex_extend`, `CSECT_DISK_CHECK` reader, page latches). The shared `topops` stack is untouched. Lock order is unchanged | Storage/Concurrency | Source table and two-worker schedule (L3). P3b: 12 cancels at 0.0–1.3 s (6 on cold start with temp add/expand) each gave `ER_INTERRUPTED`, no assert or crash, `checkdb -C` 0 each time, final `checkdb -S` 0 and a rerun query of 81920 | 5 (timing-based) |
| HA log stream | Empty sysops never emitted commit/sysop-end/replication records, so the applier sees identical records | Systems/HA | `log_manager.c:4023-4085, 4218-4315` | 3 |
| PR goal | Temp work starts no sysop | Coordinator | P4: `Num_tran_start_topops` deltas were idle 0, cold sort 0, warm sort 0, `CREATE TABLE` control 14. CI shell TC `cbrd_27562` passed at the pinned head | 5 |

Removed risk (not a base defect claim): in the base, a worker's temp sysop sat on the **shared** tdes, so its `log_sysop_abort` or commit could in principle roll back or wrap records appended by a sibling or by the leader of the same transaction. The head no longer touches the shared stack. Reachability in a supported plan was not shown (L2).

## Coverage and verification

See [pr8537-coverage.md](pr8537-coverage.md). All five changed paths and both shared challenges are covered.

| Check | Command / artifact | Result |
|---|---|---|
| Patch identity | `git diff … \| sha256sum` | matches `b11b6362…` |
| Static check | `cubrid-static-check 13131ed832 e863def787` | 0 new cppcheck/clang-tidy/CPD findings; complexity growth under the flag threshold (`disk_reserve_sectors` CCN +4) |
| Comment-only proof | `g++ -fpreprocessed -E -P` base vs head for the 3 comment files | identical |
| Build | `just build-and-install` (`debug_gcc`, GCC 11.5) | exit 0, no warnings in changed files |
| P1 temp growth crash | `p1_crash_temp_growth.sh` | pass |
| P2 perm/temp-purpose crash | `p2_crash_perm_temp_purpose.sh` (earlier attempt 1 failed to reach kill point due to gdb script error) | pass |
| P3a reserve failure accounting | `p3_fail_and_cancel.sh` | pass |
| P3b cancel during parallel sort | `p3b_cancel.sh` | pass |
| P4 topops count | `p4_topops.sh` | pass |
| CI at pinned head | `gha-ci` run 44917565351 (job logs show `checkout cubrid @ e863def787`; TC private-ex `aa615087f`): build debug/release, `medium`, `sql`, `sql_by_cci` and `shell` shards | all success |
| TC Merge Gate | run 44917558680 | FAILURE, expected while TC PRs `cubrid-testcases#4203` and `cubrid-testcases-private-ex#4911` are open |
| Approval gate | `cubrid-pr-approval-check --repo CUBRID/cubrid --pr 8537` (pre-approval snapshot) | `lht1199` APPROVED, `shparkcubrid` APPROVED, `vimkim` subsequently submitted `APPROVED` |

Optional residual checks, none blocking:

1. A deterministic hold of one worker inside temp `disk_extend` (gdb non-stop) to watch a sibling reach `disk_lock_extend` without `rmutex_topop`. This is covered indirectly by `topops.last = -1` at every observed temp reservation.
2. Forcing the dirtied temp header page to disk before SIGKILL in P1.
3. A base-build `Num_tran_start_topops` comparison. JIRA reports 674–724 and the TC description about 370.
4. A HA pair run.

## Unverified risks and dropped candidates

- Unverified risks: none material.
- Candidates by reviewer:
  - Recovery: 0 candidates, 7 hypotheses rejected.
  - Systems/HA: 0 candidates, 1 pre-existing note (PE1).
  - Storage/Concurrency: 0 candidates, 8 hypotheses rejected, notes N1 and PE2.
- Pre-existing items PE1 and PE2 are kept separate and are not attributed to this change.

## Budget

- Mode: bounded, no hard cap enforced.
- Agents: Recovery, Systems/HA (earlier Codex session, usage unrecorded) and Storage/Concurrency (this session; about 7 min, 161,822 tokens harness-reported, within its 25-min target). The coordinator took about 50 min (build, five probes, adjudication) and its tokens were not measured.
- No retries or nested agents. Overshoot of the original 62-min envelope cannot be verified, because the first session's usage is unknown.

## Publication status and local run archive

Published to `my-cubrid-docs` `main`, formal GitHub `APPROVED` review submitted, and Korean summary posted on PR #8537. Raw probe scripts, logs, and reviewer outputs remain archived locally outside Git at `/home/vimkim/temp/cubrid-pr-8537-e863def7.7j6WLH/`.
