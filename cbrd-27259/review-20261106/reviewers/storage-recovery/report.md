# Storage and Recovery review, PR #8416 (CBRD-27259)

## Pinned identity
- Checkout /home/vimkim/gh/cb/CBRD-27259-storage-force-inline, HEAD = 9ae07b9491b1393841ecb0f3579752a598bf68ec (verified equal to head). base = d52b1889e907abcf84190ec504dde3bc93de260d. Working tree clean; I changed nothing in it.
- Binary under test: $CUBRID=/home/vimkim/.cub/install/CBRD-27259-storage-force-inline/debug_gcc (libcubridsa.so built 2026-11-05 20:38, contains heap_oos_warn_bigone_without_oos). Built about 40 s before the head commit timestamp; I did not prove byte identity with HEAD, but -1393/-1388 and FORCE_INLINE behaviour match HEAD source and line numbers (heap_file.c:14266, heap_oos.cpp:1103).
- No rebuild. Databases: rv1 only, under .../reviewers/storage-recovery/db, deleted afterwards (deletedb). Probes, gdb scripts and raw output sit beside this report (probe*.sql, gdb*.cmd, raw-*).

## Inspected paths
object_representation_sr.c/.h, storage_common.h, heap_file.c (heap_attrinfo_determine_disk_layout, heap_attrinfo_transform_to_disk_internal, heap_attrinfo_set_uninitialized), heap_oos.cpp/.hpp (heap_oos_warn_bigone_without_oos, heap_oos_needs_record_preparation, heap_oos_finalize_record, heap_prepare_oos_record, heap_attrinfo_prepare_record), locator_sr.c (locator_finalize_oos_record), error_manager.c (er_set notification path, er_stack_push/pop, er_log), execute_schema.c and class_object.c (flag storage only), spec OOS-CONTEXT.md lines 55-125.

## Invariants and safety facts
| # | Fact | Evidence |
|---|---|---|
| S1 | The flag is a single 3-bit mask value in att->flags (catalog). or_get_current_representation maps it with a switch on the masked value, FORCE_INLINE=3 fits the unsigned enum bitfield `oos_storage:2`. | L2 source; L4 gdb: FORCE_INLINE column read back as oos_storage=3, DEFAULT=0 |
| S2 | FORCE_INLINE columns are excluded from demotion candidates (heap_file.c:13191). FORCE_OUTLINE pre-selection (13164) cannot touch them because only one flag persists. PREFER_INLINE only changes sort priority. | L2; L5 insert probes (t1) |
| S3 | Layout runs only in write paths (transform_to_disk_internal via locator_attribute_info_force, heap_attrinfo_prepare_record, heap_prepare_oos_record, serial.c). Redo, undo, vacuum, and rollback replay stored bytes and never call it, so neither -1388 nor -1393 can fire there. Grep of callers: only locator_sr.c, serial.c, heap_oos.cpp. | L2/L3 source; L5 crash probe |
| S4 | Policy flags do not touch log records. ALTER STORAGE changes only the class record; stored rows stay readable (readers follow per-attribute VOT IS_OOS bit, not the flag). | L2; L5: ALTER t3 to FORCE_INLINE, new process (restart), rows with OOS-demoted a still selected |
| S5 | -1393 uses er_stack_push, er_set(NOTIFICATION), er_stack_pop. A pending caller error is saved and restored, the notification clears itself. Write returns success. | L2 error_manager.c:1438, 1542; L5 insert succeeded |
| S6 | Crash restart with an uncommitted insert whose layout fired -1393: recovery UNDO of 1 transaction, row absent, no -1393/-1388 in recovery log. | L5 (gdbcrash2.cmd, raw-crash2-restart.txt) |
| S7 | Hot-path cost added: one integer compare per layout (`!has_oos && heap_is_big_length`) and one enum compare per column inside the already-gated demotion block (record above DB_PAGESIZE/4). No catalog lookup added (oos_storage is already cached in the class representation). heap_oos_needs_record_preparation did not change. | L2, source-based claim, not measured |

## Commands run (summary; raw files beside report)
- createdb rv1 (64M) then csql -S probes: probe1.sql (DDL: FORCE_INLINE on varchar/int, FORCE_OUTLINE, ALTER between policies all accepted), probe3 (show create table keeps `STORAGE FORCE_INLINE`).
- probe2 (repeat('x',20000)) showed no layout effect: string compression shrank 20000 'x' to 100 bytes. Not a defect; later probes use random data (probe8, 9, 10).
- probe8: t1 FORCE_INLINE varchar(30000)+b. Result: a<=16150 stored silently. a=16200..30000 with b of 10 bytes stored with -1393 (5 notifications, sizes 16272, 16372, 16456, 20072, 30072); a=20000 with b of 30 bytes rejected -1388 (20084 > 16236); prefer_inline and default tables demoted and accepted. diagdb -d 9: 6 BIGONE slots, all in t1.
- probe9: t9 (id, a FORCE_INLINE), a = 16150..16199 (50 inserts). 17 -1393 notifications, all "needs 16240 bytes", but diagdb shows 0 BIGONE slots for t9 and HOME records up to 16232 bytes. See F1.
- probe10: after ALTER to FORCE_INLINE and restart, `update t3 set id=904 where id=204` (row with OOS a and 30-byte b) fails -1388; the same update on a row with a 10-byte b succeeds with -1393. See F2.
- 3 single-row UPDATEs of a BIGONE row produced 3 notifications (one per row update, no duplicate per statement).
- loaddb of t1 (3 rows): the 20000+30 row is rejected with -1388 at line 4; same layout code runs (locator_finalize_oos_record then heap_prepare_oos_record).
- gdb (gdb*.cmd): confirmed call chain locator_attribute_info_force -> heap_attrinfo_prepare_record -> transform_to_disk_internal -> determine_disk_layout, and oos_storage per column.

## Candidate findings

### Reproduced
**F1 (Low) -1393 over-reports: it fires for records that are stored as REC_HOME.**
- Location: heap_file.c:14271 (`!has_oos && heap_is_big_length ((int) inline_size_after_oos)`), after `inline_size_after_oos += OR_MVCC_MAX_HEADER_SIZE - OR_MVCC_INSERT_HEADER_SIZE` (14256ish). The estimate reserves the extra MVCC header bytes (about 16) that the stored insert record does not have.
- Repro: probe9.sql (raw-t9-reclens.txt, raw-diag-heap.txt, raw-csql-last.err). 17 of 50 inserts logged "needs 16240 bytes ... is stored as a multipage overflow record (REC_BIGONE)" while diagdb shows those rows as HOME, length 16212..16232 (limit 16236); t9 has zero BIGONE slots.
- Impact: the message text states a fact that is false for a window of about 16 bytes (a stored length of 16221..16236 bytes). Noise and misleading diagnostics, no data effect. The same conservative estimate already gates -1388 (pre-existing), so a record with OOS stubs in that window can be rejected although it would fit; FORCE_INLINE makes records near 16K far more common. I did not reproduce that false rejection (needs an OOS stub plus FORCE_INLINE value in the window; unproven).
- Fix direction: compare the real header size for the notification (without the future-MVCC reserve) or reword the message to "may become REC_BIGONE after update".
- Evidence L5. Disproof tried: checked that no BIGONE exists for t9. Coordinator replay: pending.

**F2 (Medium, spec-consistent, usability hazard) ALTER to FORCE_INLINE makes some existing rows non-updatable, even by an unrelated column.**
- Location: heap_file.c:13191 plus guard at 14264 (-1388), UPDATE re-reads all columns (heap_attrinfo_set_uninitialized) so no chain reuse exists in this checkout.
- Repro: probe10.sql / raw-probe10.txt. Row (a=20000 random chars, b=30 chars) existed with both values demoted; after `ALTER ... a ... STORAGE FORCE_INLINE`, `UPDATE t3 SET id=904 WHERE id=204` fails with -1388 (size 20084). b (30B, above the 24B threshold) gets demoted although demoting it cannot make a 20000-byte inline `a` fit, so the write is rejected. The same update on the row with a 10-byte b is accepted with -1393.
- Spec: OOS-CONTEXT.md line 104 explicitly says the guard rejects when other values were demoted. The spec's "Open" note (line 109) on UPDATE keeping stubs concerns this case. Report as a risk for the design decision, not a violation. Same effect on plain INSERT of such shapes (probe8, id 201) and loaddb.
- Fix direction (design): when FORCE_INLINE and non-candidate payload alone already exceeds heap_Maxslotted_reclength, skip demotion so the record falls into the -1393 path, or decide chain-reuse semantics before shipping. Not done in this PR.
- Evidence L5.

### Source-only / observations
**O1 (Low) Notification is emitted before the row is written, so it also fires for statements that later fail** (unique violation, lock timeout, DOESNT_FIT retries are inside the loop so they do not repeat). Evidence L2.
**O2 (Low) Spec text says the target is heap_oos_inline_target_size() (4060 B); code gate still uses DB_PAGESIZE / 4 (heap_file.c:13181, 13206). Pre-existing, not changed by this PR.** Evidence L2, outside scope.

## Performance
- Hot path: see S7. Source-based claim, not measured.
- Notification volume (risk, assumed workload): bulk loaddb or batch UPDATE of N rows whose layout stays above 16236 bytes without OOS (large BIT(n)/fixed columns, many small varchars, or FORCE_INLINE columns). The default error_log_level is NOTIFICATION, so every row writes one ~370-byte line. er_log holds er_Log_file_mutex and does fprintf plus fflush per message (error_manager.c:1520-1522, 1645), which gives one write syscall per row, serialized across all server threads, and about 370 MB of error log per million rows (log size cap error_log_size 512 MB with rotation). Measured per-insert overhead in probes was not isolated. Verified one line per row insert/update (3 updates, 3 lines). Suggest rate limiting or once-per-class-per-interval. Evidence L2/L5 for count, L1 for throughput impact.
- Also F1 inflates the volume for rows near the limit.

## Cleared risks
- Redo/undo/vacuum/rollback running layout or raising -1393/-1388: cleared at L3 (call-graph) + L5 (crash then recovery, no notification). Limits: vacuum and rollback were source-checked only.
- Stale catalog after ALTER: each csql run is a fresh SA boot; an in-server stale class-representation cache across ALTER in CS mode was not tested.
- Bitfield truncation of FORCE_INLINE=3: cleared (gdb read 3).
- ALTER policy switching leaving two flag bits: cleared by loop logic in execute_schema.c (GAINED re-masks, LOST clears one bit); ran ALTER FORCE_OUTLINE then FORCE_INLINE successfully.

## Q1 answer
- Can a FORCE_INLINE value reach OOS through any write path? No path found. Layout is the only place that selects OOS values and it excludes FORCE_INLINE. Server-side INSERT/UPDATE (L5), loaddb and client-built records (copy area into locator_finalize_oos_record then heap_prepare_oos_record, or already below the threshold and thus unaffected) (loaddb L5, others L2), partition redistribution (L2), ALTER copy (INSERT..SELECT, L2). Replication apply goes through SQL/locator_force (L2, not run). Records received with existing stubs are always re-laid-out (heap_recdes_contains_oos forces preparation) so a FORCE_INLINE column in an old stub is inlined on the next write (L2; L5 for the UPDATE side).
- Wrong accept/reject: the rule is implemented as specified (-1388 for has_oos + big, -1393 + store for no-OOS big) and verified (probe8). Deviations: (a) F1, notification fires for HOME-stored records within about 16 bytes of the limit; (b) F2, valid-looking rows rejected with -1388 because a small demotable value is demoted first (spec-conformant); (c) compressible strings make the layout use compressed size (probe2), correct, noted only.
- Not exercised: replication apply, HA, CS-mode server with long-lived class cache.

## Coverage
**partial.** Complete: assigned source paths, demotion logic, guard, error-stack behavior, restart read after ALTER, crash/undo, loaddb, INSERT/UPDATE. Not run: CS-mode ALTER with concurrent writers (stale repr), replication apply, real vacuum of BIGONE rows, throughput measurement of notification flood (next check: loaddb 1M-row BIGONE load with and without error_log_level=WARNING_SEVERITY, perf/strace write counts; needs no rebuild).
