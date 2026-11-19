# CBRD-28062 / PR #8632 systemic code review (reviewer: Sonnet coordinator with four specialist reviewers)

## Question, reader, scope, principal result

- **Question.** Does PR [#8632](https://github.com/CUBRID/cubrid/pull/8632) (CBRD-28062, `oos_trigger_threshold`) hold up under its systemic interactions: every process that lays out heap records, HA, recovery, vacuum, the parameter machinery, boundary arithmetic on 4K/8K/16K pages, and the tests?
- **Reader.** The PR author and human reviewers, before review. Style and naming are out of scope.
- **Result.** Verdict **`changes-required`**. No blocker. Two should-fix defects, both reproduced by the reviewers and replayed by the coordinator:
  1. `restoredb` validates the threshold only after it has overwritten the data volumes (S1).
  2. After the threshold is raised on a 4K-page database, `NEXT VALUE` on a serial whose comment is in OOS grows a `_db_serial` row in place and aborts a debug server (S2).
- The arithmetic at the minimum and the maximum, the client copy-area gate, HA/replica apply, redo/undo/vacuum, MVCC UPDATE/DELETE/relocation and OOS chain reclaim across threshold changes showed **no defect** on the paths that ran (details in sections 4 and 8).

## Identity and method

| Item | Value |
| --- | --- |
| Date (Asia/Seoul) | 2026-11-19 |
| Repository / PR | `CUBRID/cubrid`, PR #8632 (draft), base `feature/oos-merge` |
| Base SHA | `e262e79fab73401568168a42327bfb5576631cc6` (equals the merge base) |
| Head SHA | `44dab49185a64f2417b7b8d1ae7d9d4e33335654` (commits `49d8df0dd5`, `44dab49185`) |
| Comparison | `git diff e262e79fab 44dab49185`: 6 files, 299 insertions, 9 deletions |
| Patch SHA-256 | `05807d0bead8e4f2e3fb94a6152391bb2b572ef6e450f3db9906be6b4dd1921e` |
| Remote recheck | `gh pr view 8632` at the end of the review: head and base unchanged (draft, open) |
| Source worktree | `/home/vimkim/gh/cb/CBRD-28062-oos-param`, read only, clean at head |
| Runtime | Installed debug build `/home/vimkim/.cub/install/CBRD-28062-oos-param/debug_gcc` (assertions on); every server and utility under `taskset -c 0-15`; private databases, ports and roots per reviewer; all databases and roots deleted afterwards |
| Spec and ticket | `OOS-CONTEXT.md` section 1 and 4 (`bcb834f`), `CBRD-28062.md` (acceptance criteria) |

**Build identity.** `cubrid_rel` prints `11.5.0.3032-49d8df0` because that string is fixed at configure time. The binary nevertheless has the commit-2 lower bound (4K: 987 refused, 988 accepted; `heap_oos_auto_inline_target_size` is present). The only `src/` difference between `49d8df0dd5` and `44dab49185` is `heap_file.c`. The ignored backup `src/storage/heap_file.c~` (15:23:49) is byte-identical to the head's `heap_file.c`, and the library was built at 15:24:08, so it compiled the head's content (level 3). A bit-identical rebuild was not done.

**Method.** The `cubrid-code-review` workflow with four specialist reviewers (models from pstack `interrogate reviewers`), a pinned patch, a coverage table, and independent coordinator replay of every finding that could be replayed. The harness refused report files from subagents, so each reviewer returned its report as messages; this document is the consolidated result, and raw outputs stay under the local run directory named in section 10. Findings keep the reviewer IDs (R1-x, R2-x, R3-x, R4-x) next to the coordinator IDs (S = should-fix, M = minor).

Evidence levels: 1 assertion, 2 pinned source, 3 complete path argument, 4 executed probe/test of production code, 5 reproduction in the running database or utility.

## 1. Verdict and follow-up

- **Verdict:** `changes-required` (S1 and S2 are replayed; neither depends on a reviewer's word alone).
- **Coverage:** complete for the assigned questions on the debug build, Linux, 4K and 16K at runtime, 8K for the boundary arithmetic and the layout (runtime) but source-only for recovery and HA. The gaps are listed in section 6.
- **Follow-up review required:** yes.
  - Before merge: the author's decision on S1 and S2 and a re-run of their reproductions on the fixed head; the release-build check U1 if S2 is fixed by anything other than keeping system-class rows on the automatic target.
  - Optional evidence: HA pair run (U3), `patchdb -r` path (U2).

## 2. Confirmed findings (ranked)

### Blocker

None.

### Should-fix

#### S1. `restoredb` checks the threshold after the data volumes are overwritten (R1-1, R4-1; coordinator-replayed, level 5)

- **Where.** The new check is `src/storage/heap_file.c:3970-3977`. It runs from `heap_manager_initialize()` at `src/transaction/boot_sr.c:2301`, which comes **after** `logpb_restore()` at `boot_sr.c:2289`. `logpb_restore` writes the volumes (`fileio_restore_volume`, `src/transaction/log_page_buffer.c:9504`). The page size it depends on is read from the backup header earlier, at `log_page_buffer.c:9282`.
- **Scenario.** A 4K database with a full backup; two more rows committed after the backup; `oos_trigger_threshold=987` (accepted by the parser, outside the 4K range 988..3948; a value that is valid for 16K, such as 4060, behaves the same). `cubrid restoredb -B <dir> <db>` exits 1 with `"oos_trigger_threshold": Unknown system parameter or bad value. Restoredb cancelled or an error occurred.` The volumes are already the backup state, the log is untouched, and a plain open then serves the backup state without any error.
- **Reproduction (coordinator replay; commands from `$W`, conf `[common]` + `oos_trigger_threshold=<v>`, every command under `taskset -c 0-15`, stdin `/dev/null`):**

  ```sh
  cubrid createdb --db-volume-size=20M --log-volume-size=20M --db-page-size=4K -F $W/db rdb en_US.utf8   # conf value 0
  csql -S -u dba rdb -c 'create table t (id int); insert into t values (1);'
  cubrid backupdb -S -D $W/bk -l 0 rdb
  csql -S -u dba rdb -c 'insert into t values (2);'
  # conf value 987
  cubrid restoredb -B $W/bk -l 0 rdb            # actual: rc=1, message above
  # conf value 0
  csql -S -u dba rdb -c 'select * from t order by id'   # actual: 1 row (id 1)
  ```

  Expected: a configuration error stops `restoredb` before it changes the database (rows 1 and 2 stay). Actual: only row 1 remains.
- **Controls.** The same sequence with a valid value restores rows 1 and 2 (the log is rolled forward). Rerunning `restoredb` with a valid value right after the failed run recovers rows 1 and 2. A value the *parser* rejects (`log_buffer_size=1`) stops `restoredb` before any volume mtime changes, so configuration errors have so far been harmless here (R1 probe P12).
- **Worse variant (R4-1; coordinator-replayed).** After the failed `restoredb`, open the database and commit two more rows (6 and 7), then rerun `restoredb` with a valid value: rc=254 with the debug assertion `src/storage/slotted_page.c:1970 spage_insert_for_recovery: slot_p->offset_to_record == SPAGE_EMPTY_OFFSET`. The database is left with only row 1; rows 2, 6 and 7 are gone. A successful `restoredb`, writes, and a second `restoredb` from the same backup returns rc=0 and keeps every row (control).
- **Attribution.** This PR introduces the trigger. At the base `heap_manager_initialize` fails only on allocation errors, so a `cubrid.conf` value cannot make `restoredb` stop after the destructive step. The wider hazard (a failure after `logpb_restore` leaves stale volumes) is old (R1 names timezone and charset mismatch), but this PR adds a deterministic, operator-reachable cause.
- **Impact.** An operator who restores a 4K database on a host whose `[common]` threshold fits another page size sees a failed utility that names a parameter. If they start the database instead of rerunning the restore, transactions committed after the backup are silently missing, and `checkdb` passes (R1 step 9). With writes in between, the retry fails on a recovery assertion and the loss is not recoverable.
- **Suggested fix.** Put the range check in one helper (for example `heap_oos_check_trigger_threshold(page_size)`) and call it in `logpb_restore` right after the backup header's page size is applied and before the first `fileio_restore_volume`. Keep the call in `heap_manager_initialize` for the other paths. Add a test that an invalid value leaves a restorable database untouched.

#### S2. Raising the threshold makes `_db_serial` rows grow in place; `NEXT VALUE` aborts (R3-1; coordinator-replayed in SA and CS, level 5)

- **Where.** `src/query/serial.c:1575` (`serial_update_serial_object` re-lays out the whole row with `heap_attrinfo_transform_to_disk`), `:1587` (`assert (spage_is_updatable (...))`), `:1590` (`log_append_redo_recdes`), `:1592` (`spage_update`), `:1595` (`ER_QPROC_CANNOT_UPDATE_SERIAL`). The PR exposes it through `heap_oos_inline_target_size()` (`heap_file.c:14088-14097`) and the range check that accepts values above the automatic target (`:3970-3977`).
- **Mechanism.** On a 4K page the automatic target is 988 B. `CREATE SERIAL` is a client write and system classes skip the OOS preparation (`locator_sr.c:6132`), so a serial whose comment is about 1000 B starts inline (about 1.17 KB). The first server-side `NEXT VALUE` re-lays the row out under 988 B and moves the comment to OOS, so the row shrinks and other `_db_serial` rows take the freed space. After the threshold is raised (any value from 989), the next `NEXT VALUE` lays the row out inline again. The row grows by about 976 B on a page that has no room, and `serial_update_serial_object` has no relocation fallback (it updates in place by design).
- **Reproduction (coordinator replay, 4K database, SA mode):**

  ```sh
  # conf value 0
  csql -S -u dba -i mk.sql db        # three CREATE SERIAL big1..3 ... NOCACHE COMMENT '<1000 random chars>'
  csql -S -u dba -c 'select serial_next_value(big1,1), serial_next_value(big2,1), serial_next_value(big3,1) from db_root' db
  csql -S -u dba -c 'show heap oos of _db_serial' db      # has_oos=1, 3 OOS records
  csql -S -u dba -i small.sql db     # 40 x CREATE SERIAL smallNN NOCACHE: fills the page
  csql -S -u dba -i nv.sql db        # control at 0: rc=0
  # conf value 1300 (3948 also fails)
  csql -S -u dba -i nv.sql db
  ```

  Expected: `NEXT VALUE` returns 3 as at the default. Actual: rc=134, `Assertion 'spage_is_updatable (thread_p, addr.pgptr, serial_oidp->slotid, (int) new_recdesc.get_size ())' failed` at `serial.c:1587`. Back at 0, `NEXT VALUE` works again.
- **CS mode (coordinator replay, level 5 for the server death).** The same state with `cubrid server start` and `csql -C`: the client gets `Your transaction has been aborted by the system due to server failure or mode change.` and the master starts a new `cub_server` (a second server log file is created at the moment of the failed `NEXT VALUE`; the first log ends without a shutdown record). The assertion text is not captured because the server's stderr is not a file the review owns, so the cause is consistent with, not read from, the abort.
- **Precondition found by the replay.** The page holding the serial's row must lack about 976 free bytes. With only the three big serials and nothing else on the page, the same raise succeeds and the row simply grows. Scope: 4K pages only, because `CREATE SERIAL` rejects comments over 1024 bytes ("Maximum length of a comment is 1024 bytes"), so on 8K (automatic target 2012) and 16K (4060) a serial row stays inline at every setting. An AUTO_INCREMENT serial row with 222-byte (maximum) multibyte identifiers did not reach OOS on 4K in the coordinator's attempt (R3-1's O2 not reproduced).
- **Attribution.** The assert, the "log, then update" order and the missing fallback are unchanged since `e262e79fab` (`git show e262e79fab:src/query/serial.c`). At the base the target is fixed, so a serial row's layout never changes between runs. The PR makes the layout depend on a configuration value that can change between restarts. The lower bound blocks only the inline-to-OOS direction (the CBRD-28035 leak); the PR's own comment (`heap_file.c:3968-3969`) and the spec state that system-class placement must not change, but raising the value does change it.
- **Impact.** Debug build: `abort` of `csql -S` or `cub_server`. Release build (source argument, level 3): the `assert` is compiled out, `spage_update` fails, and every `NEXT VALUE` of that serial returns `ER_QPROC_CANNOT_UPDATE_SERIAL` while the raised value stays in effect. A crash after the failed update could make restart redo fatal (U1, unproven).
- **Suggested fix.** (1) Lay system-class rows out with the automatic target (`oid_is_system_class (&attr_info->class_oid)` in `heap_attrinfo_determine_disk_layout`), which also removes the dependence of catalog rows on the setting. (2) Or keep unchanged OOS chains in `serial_update_serial_object` (the `keep_oos` approach of the CBRD-28035 PR #8492). (3) Separately, check that the new row fits before `log_append_redo_recdes`. Add the 4K steps above to `test_oos_trigger_threshold.sh`.

### Minor

#### M1. Startup error text is generic, and `createdb` does not name the parameter on the console (R1-3, R2-4, R4-2; R1-3 replayed)

`heap_file.c:3975` reports `ER_PRM_BAD_VALUE`: `"oos_trigger_threshold": Unknown system parameter or bad value.` It carries no value, range, page size or conf location, whereas an out-of-range existing parameter prints file, line and `Value is out of range` (`max_clients=1`). For `cubrid createdb`, `boot_sr.c:1862` replaces it with `Unable to create volumes for database "<db>"`; the parameter name is only in `$CUBRID/log/<db>_createdb.err`. Failure is otherwise clean: no volumes, no registry row, one empty `lob` directory. Fix: a dedicated message with the value, the range for the page size and the page size, and validate in `createdb` right after `db_set_page_size` (`boot_sr.c:1750`). Reproduced (level 5) with threshold 500 on a 4K `createdb`.

#### M2. The value printed by `;get` and `paramdump` does not round-trip (R1-2; coordinator-replayed)

The new entry carries `PRM_SIZE_UNIT` (`system_parameter.c:5790`) and `util_byte_to_size_string` keeps one decimal (`util_common.c:1120`). A 4K database with 3948 prints `3.9K` (`paramdump -S`), 4060 prints `4.0K`, 16236 prints `15.9K`. Writing the printed value back: `3.9K` and `4.0K` are refused on 4K (`3.9K`=3993, `4.0K`=4096 are above 3948); `4.0K` on 16K is silently accepted as 4096, not 4060. The range is narrow and byte-exact, so the rounding matters more here than for other size parameters. Fix: print exact bytes for this parameter, or drop `PRM_SIZE_UNIT` (the PR body advertises `4K` input, so printing is the less intrusive change).

#### M3. Test gaps (R4-3, R4-4, R4-5, R2-1; R4-3 not replayed by the coordinator)

- The `heap_oos.cpp:129` gate (`record->length > heap_oos_inline_target_size () - OR_MVCC_MAX_HEADER_SIZE`) is not pinned by any test. R4 patched a private copy of `libcubridsa.so` so that this call uses the automatic target; all three new gtests and the shell test still pass (level 4). The source argument agrees: a record that skips the gate is re-laid out through the layout path that reads the parameter, so placement is unchanged and only CPU cost differs. The ticket names this gate as a consumer. Fix direction: copy the `heap_oos_needs_record_preparation` check at `test_oos_sql_deferred_write.cpp:150-154` with the parameter at the maximum.
- 8K is untested: the shell script covers 4K and 16K only, and the spec lists only those ranges. Measured: 4K 988..3948, 8K 2012..8044, 16K 4060..16236 (R2 bisection; the coordinator's coarse scan agrees).
- No automated test for CS INSERT/UPDATE placement, CS or SA loaddb, an invalid value at `createdb`/`restoredb`/`cubrid server start`. The gtests set the parameter after boot with `prm_set_bigint_value`, so they bypass validation and hard-code 16K sizes.
- The shell test takes 29-31 s against its 60 s ctest `TIMEOUT` (2 createdb, 21 `csql -S` boots; 28.7 s even with a load average near 67). A timeout kill skips the `EXIT` trap and leaves `/tmp/oos-threshold.*`. `expect_refused` cannot tell a static parameter from an unknown one (the unknown-parameter error also echoes the assignment); the startup assertions in the same script already prove the parameter exists.
- State leakage into other tests: none found (private conf, registry and TMP; the variable `CUBRID_OOS_TRIGGER_THRESHOLD` is unset; RAII restore in the gtests; the gtest binary passes 49/49 and 3 shuffled repeats).

#### M4. Explicit values that are not multiples of 4 act rounded down (R2-2; coordinator-replayed)

Layout sizes are multiples of 4, so `T` and `ALIGN_BELOW(T, 4)` give the same boundary. Replay on 4K, one `varchar` row: `T=2000`, `2001`, `2003` all flip at n=1946 inline / 1947 OOS; `T=2004` flips at 1950/1951. The stored value is unrounded, so the spec sentence "Preserve explicit byte values without rounding or clamping" is true for the setting and misleading for its effect. Fix: document the 4-byte granularity, or round the accepted value down at startup.

#### M5. "A row that fits a page stays inline" holds only up to the maximum minus the 16-byte header slack (R2-3; coordinator-replayed)

The guard counts the full MVCC header (`heap_file.c:15264-15281`). On 4K at `T=3948` a `varchar` row stays inline up to n=3894 and goes to OOS from 3895 (stored length reaches exactly 3948 after update and delete, 0 overflowed records); the same 54-byte offset from the maximum holds on 8K (7990/7991) and 16K (16182/16183). With `STORAGE FORCE_INLINE`, n=3895 is rejected with `size (3952 bytes) exceeds the maximum record size (3948 bytes)`: the message prints record+16, not the stored size. This is the earlier guard (PR #8416) exposed at the raised target, documented in the spec's "Size estimate and scope" paragraph, but the ticket and PR body wording ("fits a page stays inline") is looser. Fix: keep the behaviour, document the slack, and consider naming the reserved header in the message.

#### M6. `inf` is accepted and stored as 0 (R1-4; coordinator-replayed; pre-existing parser defect)

`*size_num = (UINT64) val;` at `util_common.c:1209` casts `+inf` to an unspecified value. `oos_trigger_threshold=inf` gives `csql -S` rc=0 and `paramdump -S` prints `0.0B` (the automatic target). Other size parameters are protected only because their lower limit is above 0. Not caused by this PR; reachable through its new parameter.

#### M7. Operational notes (design observations, no severity)

- No nonzero value is valid for both a 4K and a 16K database (4K 988..3948, 16K 4060..16236), so a nonzero `[common]` value stops every database of the other page size on that host; `[@db]` sections are the way out (three servers with different page sizes ran at once that way).
- `[standalone]` applies to SA tools but not to `cub_server` (conventional; it is the ticket's Open Decision 2, so the documentation should say so).
- The ticket body still calls 4,060 B the default and the lower bound undecided; the spec now says 0 is the automatic default and the lower bound is the automatic target.

## 3. Pre-existing defects seen (not attributed to this PR)

| Item | Evidence |
| --- | --- |
| `_db_serial` OOS chain growth at the automatic target on 4K (CBRD-28035): 4-5 OOS records added per `NEXT VALUE` run at 0, none at 3948 | R2-5, R3 (Oos_num_recs 6 and 9), level 5 |
| `unloaddb -S` and `compactdb -S` exit with the error code modulo 256 (`-113` becomes 143) on any boot failure | R1, R4 |
| `emergency_patchlog -r` on a 4K database with a missing active log defaults the page size to 16K (`boot_sr.c:5537`) and aborts in `pgbuf_set_bcb_page_vpid` even at value 0 | R1 p11, level 5 |
| A failed `createdb` calls `boot_server_all_finalize` twice (`boot_sr.c:5239`, then 1925); completes without error | R1 |
| `compactdb` does not read the threshold (`compactdb.c:524`; CBRD-27924, known) | R3 source |
| Debug assertion `slotted_page.c:1970` when `restoredb` is rerun over a database written after a half-finished restore (exposed by S1) | R4-1, replayed |

## 4. Effects outside the diff and safety facts

| Changed behaviour and unchanged consumers | Safety fact | Evidence |
| --- | --- | --- |
| New `ER_PRM_BAD_VALUE` return from `heap_manager_initialize` before four cache initializers; every boot site unwinds through `boot_server_all_finalize` and `heap_manager_finalize` | The four finalizers return early when their globals are NULL (`heap_file.c:18547`, `:1329`, `:27487`; `oos_file.cpp:331`) | Level 2 (coordinator re-read) and level 5: SA, CS (`cub_server`), `createdb`, `restoredb`, `copydb` and eleven SA utilities fail cleanly with rc 1/143/3, no crash and no hang in 2.1 s (R1, R4) |
| Page size known when the check runs | `createdb`: `db_set_page_size` (`boot_sr.c:1750`) before `boot_create_all_volumes` (1769); restart: `log_get_io_page_size` (2263) before 2301; restore: backup header page size set at `log_page_buffer.c:9282` before heap init | Level 3 and level 5 (4K and 16K `createdb`, 4K `restoredb` with value 3000 valid only on 4K, with and without the active log). The emergency-patch path is already broken at the base (section 3) |
| Both consumers of the target (`heap_file.c:14176`, `heap_oos.cpp:129`) | Both read `heap_oos_inline_target_size()`; the preparation gate `T-32` always fires at least 16 B before the layout gate `T-16`, so it never skips a re-layout the layout gate would perform | Level 3 and level 5: CS client copy area and CS loaddb flip at the same row size as server-side INSERT in five configurations (R2) |
| Layout gate vs REC_BIGONE guard | At `T == heap_Maxslotted_reclength` both use `> Max`, MVCC (full 32-byte header) and non-MVCC (`mvcc_extra` 0) alike; an INSERT version `R` becomes at most `R+16` after update and delete | Level 3 and level 5: stored length exactly Max after insert, update, delete on 4K, 8K, 16K; 0 overflowed records; 108 SA sweeps with 0 errors (R2) |
| Placement depends on the process that writes | CS INSERT/UPDATE and CS loaddb use the server's value (the client's `CUBRID_OOS_TRIGGER_THRESHOLD` is ignored); SA tools use their own conf, `[standalone]` and environment | Level 5 (R4, R1) |
| Recovery, vacuum, replica apply do not re-lay out a record | No caller of `heap_attrinfo_determine_disk_layout` or `heap_oos_needs_record_preparation` is reachable from redo/undo (`RVHF_*`, `RVOOS_*`), vacuum, the OOS reclaimer or `xlocator_repl_force` (`from_copyarea=false`) | Level 3 (R3 grep of `log_*`, `recovery.c`, `vacuum*`, `oos_file.cpp`, `log_applier*`, `locator_sr.c:8641,8659`) |
| Chain ownership after a threshold change | The drop-notification guards test the old record (`heap_file.c:25787`, `:26263`), so an OOS-to-inline UPDATE drops its chain exactly once after vacuum | Level 5 on 16K CS and SA: raise, lower, rollback, delete, relocation, `kill -9` then restart under another value; `SHOW HEAP OOS` counts exact; values intact; `checkdb` rc 0 (R3, R2) |

## 5. Focus areas from the brief

| # | Focus area | Result | Evidence checked |
| --- | --- | --- | --- |
| 1 | All layout processes see the same threshold and validate alike | Defect **S1** (`restoredb` order), minor **M1**; otherwise clean | Three `heap_manager_initialize` sites; `cub_server`, `csql -S`, `createdb`, `restoredb`, `compactdb`, `loaddb -S`/`-C`, `unloaddb`, `checkdb`, `diagdb`, `backupdb`, `copydb`, `spacedb`, `vacuumdb`, `optimizedb`, `paramdump`, `renamedb`; client conf with a bad value is ignored by a CS client (conventional) |
| 2 | HA: different values, failover, applier | **No defect** (source, level 3; no HA pair run, U3) | `xlocator_repl_force` applies the master's row image with `from_copyarea=false`; `locator_oos_insert_force` and `locator_fixup_oos_oids_in_recdes` give replica-local OIDs; replica never reads its threshold; ticket and spec describe the same code from two sides; no `LOG_REPL`/`repl_log` size limit reached by rows up to `heap_Maxslotted_reclength` (applier buffers are dynamic) |
| 3 | Recovery, redo/undo re-layout | **No defect** | Section 4 rows 6-7; `kill -9` runs with committed and uncommitted threshold-crossing UPDATEs, restart under a different value |
| 4 | Vacuum, system classes, catalog rows, non-MVCC, MVCC UPDATE, chain ownership | Defect **S2** (system class `_db_serial` only); rest clean | Catalog rows are client-built and skip preparation (`locator_sr.c:6132`): catalog placement identical at 0 and 3948 (R2 DDL run); only the two `serial.c` callers re-lay out a system-class row; non-MVCC rows never grow; MVCC UPDATE, relocation (up to 237 relocated rows), partition moves, bulk insert path: 0 errors, 0 overflowed |
| 5 | Parameter machinery | **No defect** for ordinals; minor **M2**, **M6** | `prm_Def[]` entry appended after `PRM_ID_NUMERIC_EMPTY_STRING_AS_NULL` (403, new id 404); PL `static_assert`s unchanged; `SysParam.java` highest ordinal 403; debug `sysprm_check_id_order` passes on every boot; field order matches `SYSPRM_PARAM`; footprint equals `row_snapshot_max_rows`; no testcase enumerates parameters; `SET SYSTEM PARAMETERS` refused in SA and CS; `[@db]` overrides `[common]` and survives `sysprm_reload_and_init`; environment override applies |
| 6 | Boundary arithmetic 4K/8K/16K and REC_BIGONE | **No defect**; minor **M4**, **M5** | Measured ranges 988..3948, 2012..8044, 4060..16236; never empty or inverted; page sizes below 4K clamp to 4K and 32K clamps to 16K; the check and `heap_Maxslotted_reclength` come from the same page size in the same function |
| 7 | Tests can fail; leakage | Minor **M3** | 12 binary mutants (below); no leakage |

R4's 12 library mutants: eight validation and flag mutants (lower bound removed or off by one, upper bound exclusive, off by one or removed, zero treated as a value, validation removed, `PRM_USER_CHANGE` added) are killed by the shell test; "layout ignores the parameter" and "gate `>=` in both comparisons" are killed by the gtests and the existing `FourRecordTargetGateIsStrict`; "outer `>=` only" is an equivalent mutant (the loop re-tests); "preparation gate left on the old constant" survives (M3). "Validation before the page size is known" was not mutated; the 4K/16K accept/refuse pairs constrain it indirectly.

## 6. Unverified risks and the decisive next check

| ID | Risk | Owner | Decisive check |
| --- | --- | --- | --- |
| U1 | S2 in a release build: the redo-only `RVHF_UPDATE` is logged (`serial.c:1590`) before `spage_update` fails; a crash before the page is flushed or a checkpoint passes could make restart redo fatal (`heap_update_physical` fails, `logpb_fatal_error`; R3 source level 3) | R3 / coordinator | Release build, the S2 steps, one failing `NEXT VALUE`, `kill -9` of the server before a checkpoint, restart; look for "Error applying redo record" in the server log |
| U2 | `emergency_patchlog -r` on a 4K database without its log checks the value against 16K numbers (page size defaults to 16K, `boot_sr.c:5537`) | R1, R4 | Already aborts at the base; recheck after that is fixed |
| U3 | HA at runtime: master at 16236 with a replica at 0 and the reverse, `SHOW HEAP OOS` counts equal, a threshold-crossing UPDATE reclaimed on the replica, failover writes | R3 | Two-node HA run on private ports |
| U4 | 9 ERROR lines in one of R2's CS server logs were deleted unread; R2 attributes them to a restart script that raced the previous shutdown; a polling-restart rerun of the whole threshold-transition sequence gave 0 at every step | R2 | Replay the transition sequence with a polling restart and keep the log |
| U5 | R3-1 through an AUTO_INCREMENT serial row with long multibyte identifiers on 4K | R3 | Coordinator attempt with 210- and 222-byte names did not demote the row, so not reached; low likelihood |
| U6 | MVCC boundary lifecycle in CS used single-variable-column rows; two-column, fixed-plus-variable and bit-varying shapes ran only in SA (non-MVCC updates) | R2 | Repeat the CS lifecycle for those shapes |
| U7 | Crash and restart at the maximum boundary ran on 16K only | R3 | Same `kill -9` runs on 4K at 3948 |
| U8 | Release build never ran | all | Repeat S1, S2 and the startup-failure probes on a release install |
| U9 | CS `unloaddb` to `loaddb -C`, `restoreslave`, SA `compactdb` with a raised value | R4 | Not run; compactdb ignores the threshold (CBRD-27924) |

## 7. Cleared hypotheses (condensed)

Each reviewer's cleared and rejected hypotheses, with the limits stated in section 8, are summarised here by the claim they refuted.

- **Unwinding after the new early return touches uninitialised caches** (R1 H1): rejected, finalizers are NULL-guarded; runtime on SA, CS, `createdb`, `restoredb`, `copydb`.
- **`cubrid server start` hangs or leaves master state** (R1 H2, R4): rejected, rc 1 in 2.1 s, no zombie, no stale lock, restart after the fix works.
- **Some SA tool fails without naming the parameter** (R1 H3, R4): rejected for `spacedb`, `checkdb`, `diagdb`, `backupdb`, `unloaddb`, `compactdb`, `loaddb`, `optimizedb`, `paramdump`, `vacuumdb`, `copydb`, `renamedb`; `deletedb` and `alterdbhost` do not boot the heap manager and still work.
- **Page size unknown or different at check time** (R1 H4): rejected for `createdb`, restart, restore (4K backup with value 3000 restores).
- **A path uses the threshold without the check** (R1 H5): rejected; the two consumers are server code reached only after `heap_manager_initialize`; `SET SYSTEM PARAMETERS` is refused in CS and SA.
- **Appending shifts ordinals or breaks the PL server** (R1 H6): rejected.
- **Parsing** (R1 H7): `0x400`, `1e3`, `+988`, `988.9`, `8K`, `0x2000`, `8192B` accepted; `-1`, `malformed`, empty, `nan`, `20000`, `4096k`, `8192 K` refused; `inf` is M6.
- **CS uses the client's value** (R4): rejected in six CS runs and CS loaddb.
- **Raised value leaks or frees an OOS chain too early** (R3 C1-C8): rejected on 16K and 4K for raise and lower, rollback, DELETE, UPDATE then DELETE, relocated forward records with stubs, SA/non-MVCC eager path, `kill -9` with another value after restart.
- **Drop notification needs OOS in the new record** (R3 C2): rejected; both guards test the old record.
- **Recovery, vacuum or replay re-lays out records** (R3 C9): rejected, level 3 and `kill -9` runs.
- **Raised value creates sizes that relocation or header growth cannot handle** (R3 C12, R2 H-a/H-b/H-c): rejected; sizes between the automatic target and the maximum were already reachable at the base when no demotion candidate remained.
- **Unprepared copy-area records exceed the page** (R3 C13, R2 H-d): rejected; an unprepared record is at most `Max-32`.
- **Bulk insert path mishandles rows above `capacity*(1-unfill)`** (R2 H-i): no defect; big rows briefly preallocate empty pages that later inserts reuse.
- **Partition moves exceed the maximum** (R2 H-g): rejected on 4K.
- **Fixed assumptions about 4060/988 outside tests** (R3 C15): only tests, which run at the default and restore the value.

## 8. Shared challenge questions

| Question | Reviewers (models) | Independent answers |
| --- | --- | --- |
| Q-A: at `T == heap_Maxslotted_reclength` and at `T ==` automatic target, can an accepted row end in REC_BIGONE, an unfit relocation, an assertion or an orphan chain on 4K, 8K, 16K? Does the ticket claim hold? | R2 (sonnet), R3 (opus) | Both: no for user tables on 4K and 16K at runtime (R2 also 8K at runtime; R3's 8K is source-only). R3 alone found the exception, system-class `_db_serial` rows on 4K (S2). The two reports agree on the 16 B slack and on the claim holding for user tables with the documented exceptions |
| Q-B: with an invalid value, does every process that boots a server fail cleanly with a message that names the parameter? | R1 (opus), R4 (sonnet) | Both: no, with two exceptions, `restoredb` (S1) and `createdb` console text (M1). Both found S1 independently; no other process failed unclean |

## 9. Coverage

| Changed path | Primary reviewer | Invariant | Result |
| --- | --- | --- | --- |
| `src/base/system_parameter.c` (name, `prm_Def[]` entry) | R1, coordinator | I3 table consistency, parse/print | Clean for ordinals; M2, M6 |
| `src/base/system_parameter.h` (enum, `PRM_LAST_ID`) | R1 | ordinal order | Clean |
| `src/storage/heap_file.c` `heap_manager_initialize` check | R1, R2, R4 | validation order, page size, unwinding | S1, M1; otherwise clean |
| `src/storage/heap_file.c` `heap_oos_auto_inline_target_size`, `heap_oos_inline_target_size`, layout gate | R2, R3 | boundary arithmetic, system classes, chain ownership | S2 (exposed); otherwise clean |
| `unit_tests/oos/CMakeLists.txt`, `scripts/test_oos_trigger_threshold.sh` | R4, coordinator | can fail, leakage, timing | M3 |
| `unit_tests/oos/sql/test_oos_sql_storage.cpp` (3 tests, `scoped_oos_threshold`) | R4, coordinator | can fail, leakage | M3 |
| Outside the diff: `boot_sr.c`, `log_page_buffer.c`, `serial.c`, `heap_oos.cpp`, `locator_sr.c`, `log_applier.c`, `oos_file.cpp`, vacuum | R1, R2, R3 | consumers of the target and the check | S1, S2 |

Not applicable domains: none; HA is source-only (U3).

## 10. Checks run

All under `taskset -c 0-15`, stdin from `/dev/null`, daemons with output to files, the debug install named above, private databases and ports (coordinator 52110, R1 52120, R2 52130, R3 52140, R4 52150). Exit status shown where it decides a result.

- **Coordinator replays (all matched the reviewers):**
  - Coarse range scan: 4K accepted 988..3948 (987 and 3949 refused); 8K refused at 2000 and 8100, accepted from 3000 through 8000; 16K accepted 4060..16236 (4000 and 16237 refused).
  - S1: failed `restoredb` rc=1, stale open (1 row), control `restoredb` with 0 (2 rows), rerun after the failure (2 rows), retry after writes rc=254 with the `slotted_page.c:1970` assertion, control second `restoredb` rc=0 with 4 rows.
  - S2: SA rc=134 at `serial.c:1587` (conf 1300), control rc=0; first attempt with a non-full page did not abort (precondition); CS `csql -C` aborted by server failure, server restarted by the master.
  - M2 (`3.9K`, `4.0K`, `15.9K`; rc 1, 1, 0 and the 16K `4.0K` acceptance), M4 (n=1946/1947/1950/1951 at T=2000/2001/2003/2004), M5 (`FORCE_INLINE` n=3894 ok, n=3895 rejected 3952 vs 3948), M6 (`inf` rc=0, `0.0B`), R1-3 (`createdb` 500 on 4K rc=1, no registry row).
  - O2 attempt (AUTO_INCREMENT, 210 and 222 B names): not reached.
  - Build identity: `heap_file.c~` equals head; remote PR head and base unchanged.
- **Reviewer runs** (evidence files kept by each reviewer: R1 94, R2 58, R3 106, R4 81). R1: probes `p1`-`p16` (`createdb`, startup failure, section and environment precedence, 11 SA utilities, restore, parsing, `copydb`, `deletedb`). R2: bisection on three page sizes, 108 SA sweeps, CS lifecycles, relocation, loaddb, partition and bulk-insert runs. R3: caller enumeration, threshold-crossing UPDATE/DELETE/ROLLBACK, crash runs, boundary probes on 4K and 16K. R4: the shell test twice unmutated, twelve mutants, three gtest binaries, the acceptance walk, startup failures. The shell test passed unmutated (rc 0, about 29-31 s); the gtests passed (`OosSqlStorage.Configured*` 3/3, whole binary 49/49, three shuffled repeats).
- **Not run:** the real `ctest` driver (it writes `Testing/` into the source worktree), a release build, HA, `patchdb -r`, `cubrid-static-check` (run earlier by the author per `pr-context.md`: 0 new findings).
- **Raw evidence (local, may be cleared):** the run directory `/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-my-cubrid-docs/e61f8f93-ad0c-4056-88bb-ca120c5785bf/scratchpad/run` holds the patch, briefs, `evidence/coord/` (coordinator replays) and `r1`-`r4/evidence/` (reviewer outputs). Findings above carry their commands inline so they do not depend on it.

## 11. Budget accounting

- **Mode:** bounded (no absolute budget given); no hard cap was enforced, so overshoot was possible. Targets: about 45 minutes of wall-clock per reviewer with a checkpoint at about 35 minutes; each reviewer had a finite scope.
- **Agents:** four specialist reviewers (R1 opus, R3 opus, R2 sonnet, R4 sonnet), effort `xhigh` per the pstack budget; zero nested agents. Reviewer-reported wall-clock: R1 about 15 min, R3 about 25 min, R4 about 32 min, R2 about 35 min; all under the target (self-reported, not independently measured).
- **Retries and continuation:** none restarted; each reviewer was sent one request to resend its report as messages because the harness refuses report files from subagents (R1 four parts, R2 six, R3 four, R4 seven), plus one message relaying the `rm` rule.
- **Usage:** no provider telemetry was available, so per-agent token or allowance use is unknown. The coordinator's own work was the scope pinning, briefs, the replays listed in section 10, and this report.
- **Targets met:** wall-clock targets met (self-reported); no usage figure can be claimed.

## 12. Follow-up and handoff

- **Follow-up review required:** yes (section 1).
- **Resumable request:** "Resume `cubrid-code-review` for PR #8632 at head `44dab49185a64f2417b7b8d1ae7d9d4e33335654` (base `e262e79fab`), report `CBRD-28062/systemic-review-sonnet.md` on branch `docs/CBRD-28062-review-sonnet`; open IDs S1, S2, U1, U3, U4, U6, U7, U8."
- **If the author pushes a fix:** pin the new head, rerun the S1 sequence (an invalid value must leave rows 1 and 2 in place), the S2 sequence at 1300 and 3948, and the startup-failure probes; revisit `serial.c` callers and `locator_sr.c:6132` for any other in-place system-class update; rerun `test_oos_trigger_threshold` for timing after any test additions.
- **Resources needed:** the debug install above (or a rebuild of the fixed head), private ports 52110-52150 are free again, all private roots and databases of this review are deleted.
- **Authorizations:** this handoff authorizes no push, no GitHub or JIRA write, and no merge.
