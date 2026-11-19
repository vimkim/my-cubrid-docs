# PR #8632 systemic review (Claude): configurable OOS trigger threshold

Date: 2026-11-19 (Asia/Seoul). Ticket CBRD-28062. PR https://github.com/CUBRID/cubrid/pull/8632 (draft), base `feature/oos-merge`.

## Question, scope, and principal finding

The review looked for systemic defects, bugs, and consistency errors in the new static server parameter
`oos_trigger_threshold`. It is for human reviewers and the PR author.

The principal finding is **F1**. Raising the threshold after `_db_serial` rows were moved to OOS makes NEXT VALUE
regrow those rows in place. On a full page, a debug server aborts. Emulating the release path showed that NEXT VALUE fails,
and that a crash afterwards leaves a database whose restart redo cannot apply the logged update.
This affects 4 KiB and 8 KiB pages only.

The verdict is **changes-required**. Follow-up review is required after a fix for F1 and F2.

## Pinned identity

| Item | Value |
|---|---|
| Comparison | `git diff e262e79fab73401568168a42327bfb5576631cc6 44dab49185a64f2417b7b8d1ae7d9d4e33335654` (merge base = base) |
| Commits | `49d8df0dd5` (parameter), `44dab49185` (lower bound = automatic target) |
| Patch SHA-256 | `05807d0bead8e4f2e3fb94a6152391bb2b572ef6e450f3db9906be6b4dd1921e` |
| Runtime build | installed debug_gcc 11.5.0.3032. Its gdb line table matches head function lines, and probes separate rev 1 from rev 2. |
| PR movement | The base tip is now `71993ddb63`. The PR merges cleanly onto it (`git merge-tree`), and the new base commits do not touch the reviewed hunks. |

Changed paths: `src/base/system_parameter.{c,h}`, `src/storage/heap_file.c`, `unit_tests/oos/CMakeLists.txt`,
`unit_tests/oos/scripts/test_oos_trigger_threshold.sh`, `unit_tests/oos/sql/test_oos_sql_storage.cpp`.

## What the change does, and who depends on it

`heap_oos_inline_target_size()` (heap_file.c:14088) returns the parameter when it is nonzero, and the automatic
four-rows-per-page target otherwise. Two places consume it:

- the layout gate in `heap_attrinfo_determine_disk_layout` (14176);
- the copy-area preparation decision in `heap_oos_needs_record_preparation` (heap_oos.cpp:129).

`heap_manager_initialize` (3959) refuses any value outside [automatic target, `heap_Maxslotted_reclength`] with
`ER_PRM_BAD_VALUE`. It runs at three boot sites (boot_sr.c:2301, 4975, 5554).

Before this change, the target was a pure function of the page size. Every caller that re-lays out a record therefore produced
a record no larger than the one it replaced, unless its values grew. The change breaks that property across restarts and
processes. F1 is the consumer that depended on it.

## Findings

### F1. Blocker: a raised threshold regrows `_db_serial` rows in place, and NEXT VALUE then aborts or fails (4K/8K pages)

- **Where:** `src/query/serial.c:1575-1597` (`serial_update_serial_object`, unchanged), reached through
  `heap_oos_inline_target_size()` at `src/storage/heap_file.c:14088-14097`.
  - The function re-lays out the whole row with the current threshold.
  - It asserts that the row fits (1587).
  - It appends the `RVHF_UPDATE` redo record (1589) **before** `spage_update` (1592), which can fail.
- **Why it broke:** before this PR, a serial row moved to OOS under the fixed target could never grow back, because the
  target depended only on the page size. Now a restart with a higher value, an SA process with a higher
  `[standalone]`/`[@db]`/environment value, or a failover to a node with a higher value re-lays the row out inline.
  If the page has no room, the update fails.
- **Reach:** serial rows can exceed the automatic target (988 B on 4K, 2012 B on 8K) through long comments or long
  multibyte names. On 16K pages they stay below 4060 B, so 16K is not affected. AUTO_INCREMENT goes through the same
  function (serial.c:1086, 1446).
- **Reproduced (level 5):**
  - Setup: 4K database; 40 serials with 1000-byte comments (rows 1138 B); NEXT VALUE at threshold 0 moves each comment to
    OOS (rows 150 B); 750 short serials then fill the freed space.
  - Run `select s1.next_value` with `CUBRID_OOS_TRIGGER_THRESHOLD=3948`. The process aborts at
    `serial.c:1587: Assertion spage_is_updatable(...)` (rc=134).
  - In CS mode, `cub_server` itself aborts (reviewer R2).
  - Control at threshold 0: every NEXT VALUE succeeds.
- **Release-path emulation (level 4):** under gdb on the same debug binary, I skipped only the debug-only assertions.
  1. NEXT VALUE returned `ERROR: Cannot update serial object.`
  2. A second debug check fired on unfix: `page_buffer.c:7388 LSA_ISNULL(oldest_unflush_lsa) || dirty`. The page holds the
     LSA of the failed record but is not dirty.
  3. I killed the process after later commits flushed the log, before the shutdown checkpoint.
  4. The next open runs recovery. Redo applies the logged update, and it fails in `heap_update_physical`
     (`heap_file.c:26324`, debug abort).
  - In a release build that path returns an error to `heap_rv_undoredo_update` (19730), and `log_rv_redo_record` calls
    `logpb_fatal_error` (log_recovery.c:465-475). So every restart fails. That last step is source-level (level 3).
    My gdb rerun of the release restart was aborted unfinished.
- **Suggested fix:**
  - Make `serial_update_serial_object` keep the stored layout: update the fixed-size columns in place, or fall back to
    `heap_update` when the new row does not fit.
  - Check `spage_is_updatable` before appending the redo record, and fail without logging.
  - An alternative that also closes CBRD-28035: never move system-class or MVCC-disabled rows to OOS.
  - Add a 4K test that raises the threshold after serial rows were moved to OOS.

### F2. Should-fix: restoredb checks the threshold only after it overwrote the volumes, and a normal open then silently loses post-backup commits

- **Where:** `boot_sr.c:2289` (`logpb_restore`) runs before `2301` (`heap_manager_initialize`).
- **Reproduced (level 5):**
  1. 4K database; `t(a)`; insert 1; `backupdb -S`; insert 2 and 3; commit.
  2. With `oos_trigger_threshold=3949`, `restoredb -B` fails (rc=1, parameter named). The data volume, `_vinf` and
     `_bkvinf` have already been rewritten.
  3. After fixing the conf, `csql -S` shows only row 1, with no warning, and `checkdb` returns 0.
  4. Rerunning `restoredb` with a valid conf restores rows 1-3.
  - R1 also showed that writing into the half-restored database and then rerunning restoredb fails in redo
    (`spage_insert_for_recovery` assertion).
- **Cause:** before this PR, nothing configuration-driven failed after `logpb_restore`. The PR makes an interrupted
  restore deterministic. Restore performs no record layout, so the check adds no safety there.
- **Suggested fix:** skip the check when `from_backup`, or validate against the backup page size before `logpb_restore`
  writes anything.

### F3. Minor: `createdb -r` removes the old database and then fails the check

- **Where:** `boot_sr.c:1700` (`boot_remove_all_volumes`) runs before 1750 (`db_set_page_size`) and 4975 (validation).
- **Reproduced (level 5):** with 3949 on a 4K database, `createdb -r` returns rc=1 and leaves only `lob/`. The
  `databases.txt` entry stays, and opening the database fails with "Unable to locate volume information".
- **Impact:** `-r` already intends to discard the old database, so the defect is the failed replacement and the stale
  entry. The console message does not name the parameter.
- **Suggested fix:** validate against `db_desired_pagesize` before removing the old volumes.

### F4. Minor: diagnostics

- `ER_PRM_BAD_VALUE` does not state the page-size-dependent range: 988-3948 on 4K, 2012-8044 on 8K, 4060-16236 on 16K.
- `createdb` prints only "Unable to create volumes".
- `paramdump` and `;get` round byte values: 4060 and 4096 both print as `4.0K`.

### F5. Minor: test gaps

- No test covers 8K pages, the createdb or server-start refusal, unit suffixes, the copy-area path with a nonzero
  threshold, or a threshold raised across a restart. A test for that last case would have caught F1.
- The gtests hard-code 16K sizes without a page-size guard.
- The shell test reports a misleading "createdb rejected" failure when `TMPDIR` pushes `CUBRID_TMP` past 96 characters.
- The shell test writes createdb logs into the shared `$CUBRID/log`.
- Surviving mutants (argued from source, reviewer R3): the REC_BIGONE comparator or margin, a needs-preparation skip that
  is too broad, the demotion-loop stop `<=` changed to `<`, the target off by +1 to +3, and the validation result ignored
  at boot_sr.c:4975/5554.

### Problems that existed before this PR

- The pre-demotion header used inside the demotion loop over-demotes near the variable-offset width thresholds
  (heap_file.c:14176-14210; level 5; harmless to correctness).
- A replicated `_db_serial` update that carries OOS stubs is written without its OOS chunks, so the replica fails the row
  (locator_sr.c:16121; CBRD-28035 territory; level 3).
- The server applies client parameter changes without the user-changeable or range checks
  (system_parameter.c:7937-7944). This parameter is re-read on every layout, so a non-standard client could change it
  unvalidated. Caching the validated value would close this (level 2-3).
- The size parser maps `0.5`, `inf` and `1e30` to 0 through `strtod`, which silently selects the automatic target.

## Focus areas with no defect found

| Area | Evidence |
|---|---|
| 1. Processes that lay out records | Every layout goes through the one function. CS clients, CAS and applylogdb never lay out records. SA processes read `[common]`, then `[@db]`, `[standalone]` and the environment, and each validates at its own boot. Measured: the server read 6.0K while `paramdump -S` read 7.0K. The spec permits this difference, so it is not a defect. It does feed F1. |
| 2. HA | The replica stores the master image through `locator_insert_force`/`locator_update_force` with `from_copyarea=false`, so it skips preparation (level 3). For ordinary rows, rejection does not depend on T within the valid range. |
| 3. Recovery | Undo and redo use physical images, and no recovery function lays out a record (level 3). Crash probes with a different threshold before and after restart, in both directions, gave identical contents and correct OOS counts (level 5). F1 is the exception: a failed forward update leaves a redo record. |
| 4. Vacuum and OOS ownership | UPDATE drops exactly the chains it no longer references. An MVCC reader kept reading its own chains, and vacuum reclaimed the chains from 60 to 0 (level 5). |
| 5. Parameter machinery | `prm_Def` order matches the enum. The PL ordinals are unchanged and the parameter is not PL-context. `SET SYSTEM PARAMETERS` is refused. A plain number means bytes, and `4K`/`4KB` mean 4096. Message 839 takes one argument (level 4-5). |
| 6. Boundary arithmetic | 4K 988..3948, 8K 2012..8044, 16K 4060..16236, all measured (level 5). At T = maximum, the 16K switch from inline to OOS falls exactly at E = 16236. A FORCE_INLINE row is rejected at 16240 > 16236. No REC_BIGONE appeared, and the copy-area decision agrees with the layout. |
| 7. Test leaks | Each test uses a private registry and `CUBRID_TMP`. The guard restores the parameter before `TearDown`, and the tables are dropped. Only createdb logs leak into `$CUBRID/log`. |

## Method and limits

- Coordinator (Claude Opus) plus three reviewers: R1 parameters and processes (Sonnet), R2 HA, recovery and vacuum
  (Opus), R3 boundaries and tests (Sonnet).
- The shared question "same threshold in every process" went to R1 and R2. Both answered independently: the value can
  differ, but every process validates its own value.
- I replayed F1, F2, F3, the 8K bounds, and the 16K upper-bound placement myself.
- The run was bounded with no hard cap. Agents used about 120 (R1), 143 (R2) and 85 (R3) tool calls.
- Not run: a real HA pair, a release build, and a completed gdb emulation of the release restart for F1.
- Raw evidence stays in the local session scratchpad and is not retained.
