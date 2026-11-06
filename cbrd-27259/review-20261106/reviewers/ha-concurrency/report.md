# HA and Concurrency review, CUBRID PR #8416

Reviewer role: HA + Concurrency (combined). Read-only review. No code was changed, committed, pushed or posted. No agents were spawned.

## Pinned identity
- Checkout: /home/vimkim/gh/cb/CBRD-27259-storage-force-inline, `git rev-parse HEAD` = 9ae07b9491b1393841ecb0f3579752a598bf68ec (equals pinned head).
- base = merge base = d52b1889e907abcf84190ec504dde3bc93de260d
- `gh-pr-info`: PR 8416, base `feature/oos-merge`, head ref `CBRD-27259-storage-force-inline`, headRefOid = pinned head, state OPEN.
- Patch: .../review-20261106/evidence/pr8416.patch (1456 lines, read in full). Spec: /home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md (STORAGE policy rules at lines 94-122, replication at 249-263).
- Build used for the probe: build_preset_debug_gcc / install $CUBRID=/home/vimkim/.cub/install/CBRD-27259-storage-force-inline/debug_gcc. `libcubridsa.so` contains `heap_oos_warn_bigone_without_oos` (built 2026-11-05 20:38:58, so it contains the patch symbol). No rebuild.

## Inspected paths
Patch hunks: heap_file.c (determine_disk_layout, transform_to_disk_internal), heap_oos.cpp/.hpp, execute_schema.c, object_representation_sr.c/.h, class_object.c, parse_tree*.c/.h, grammar/lexer/keyword, unload_schema.c, object_printer.cpp, storage_common.h, error_code.h, msg catalogs.
Unchanged code followed: src/transaction/log_applier.c (la_apply_statement_log, la_apply_insert_log, la_disk_to_obj, la_repl_add_object), src/query/execute_statement.c (do_replicate_statement), src/transaction/locator_sr.c (locator_finalize_oos_record, locator_attribute_info_force, locator_lock_and_get_object, locator_mvcc_reev_cond_*), src/query/query_executor.c, src/query/serial.c, src/base/error_manager.c (er_set_internal, er_stack_push/pop), src/storage/page_buffer.c and heap_file.c (notification-under-latch precedents), heap_file.c classrepr cache decache, src/storage/disk_manager.c (storage format guard).

## Invariants and safety facts

HA
| # | Fact | Evidence |
|---|---|---|
| H1 | DDL is replicated as the original user SQL text, not as a re-printed parse tree. `do_replicate_statement` sets `repl_stmt.stmt_text = statement->sql_user_text` (execute_statement.c ~17190). The applier runs it with `la_update_query_execute(stmt_text)` -> `db_execute` (log_applier.c la_apply_statement_log). So `STORAGE FORCE_INLINE` and `STORAGE DEFAULT` clauses reach the replica verbatim and the replica derives its flags with the same `do_resolve_oos_storage_flag` code. | Level 3 (source path) |
| H2 | Fixed-type `STORAGE DEFAULT` / `FORCE_INLINE` persist no flag (`oos_flag` stays 0 when `!is_variable`), so there is no catalog state to diverge. Variable-type FORCE_INLINE persists SM_ATTFLAG_OOS_FORCE_INLINE (0x4000) in the class record; flag is set in do_add_attribute / do_change_att_schema_only, which run identically on the replica. | Level 2 |
| H3 | Row apply does not copy bytes. The applier decodes the master record into a DB_OTMPL (`la_disk_to_obj`), flushes it as an object; the server then re-lays it out: `locator_finalize_oos_record` -> `heap_oos_needs_record_preparation` -> `heap_prepare_oos_record` -> `heap_attrinfo_prepare_record` -> `heap_attrinfo_determine_disk_layout` with the replica's own representation (`last_attrepr->oos_storage`). Shortcut (no re-layout) applies only to small, same-repr records with no FORCE_OUTLINE columns, where FORCE_INLINE has no effect anyway. Replica OOS references are replica-local (spec section 4). | Level 3 |
| H4 | The layout and its -1388 estimate are a pure function of (values, column policy flags, DB_PAGESIZE, is_mvcc_class). `inline_size_after_oos` is built from the insert header size plus `OR_MVCC_MAX_HEADER_SIZE - OR_MVCC_INSERT_HEADER_SIZE` for both insert and update, and `is_update` only changes the local header_size used later for writing. So master and replica estimates agree for the same row and policy, and the new FORCE_INLINE guard in determine_disk_layout does not add any master-only input. | Level 3 |
| H5 | Policy ordering between DML and ALTER is preserved on the replica. On the master, ALTER needs the class X lock and waits for every transaction holding IX on the class; transactions are applied in commit order and `la_apply_insert_log` calls `la_flush_repl_items` before statement items. So no row is laid out under a different policy on the replica than on the master. | Level 3 (lock reasoning + applier order); not run |
| H6 | Rolling upgrade is not a requirement here (see Not applicable). | |

Concurrency
| # | Fact | Evidence |
|---|---|---|
| C1 | On the ordinary INSERT/UPDATE paths `heap_attrinfo_transform_to_disk_internal` runs before heap page latching. gdb backtrace: qexec_execute_insert -> locator_attribute_info_force -> heap_attrinfo_prepare_record -> transform (no page fixed). `old_recdes` is `copy_recdes` (COPY). locator_finalize_oos_record runs "before heap/index writes". loaddb and partition-redistribute paths also prepare before locator_insert_force. | Level 4 (gdb for INSERT), Level 2 (others) |
| C2 | One path does run it under a heap page latch: MVCC update/delete reevaluation. `locator_lock_and_get_object` peeks the record (`recdes` PEEK, `context.home_page_watcher` stays fixed until `heap_clean_get_context` at exit) and calls `locator_mvcc_reev_cond_assigns` -> `locator_allocate_copy_area_by_attr_info` -> `heap_attrinfo_transform_to_disk` -> the new notification. See finding HC-1. | Level 3 |
| C3 | `serial_update_serial_object` also transforms with the serial page latched (`pgptr`), but db_serial rows are tiny and the class cannot carry user STORAGE flags, so `heap_is_big_length` is never true there. | Level 2 |
| C4 | `er_stack_push` + `er_set(ER_NOTIFICATION_SEVERITY)` + `er_stack_pop` is safe with respect to error state. er_set_internal clears a notification at the end (`crt_error.clear_error()`); the explicit push gives it a fresh entry so the caller's pending error is untouched (er_set_internal would also auto-push if an error were pending). Runtime: INSERT returned "1 row affected" and commit succeeded after the notification. | Level 4 (gdb + csql SA) |
| C5 | The log write takes only `er_Log_file_mutex` (a leaf mutex, no other lock taken inside), then fprintf/fflush to the error log. This is blocking file I/O, but existing code already does the same under latches: `heap_oos_delete_unreferenced` -> `heap_oos_diagnose_skipped_cleanup` (er_set NOTIFICATION) on the "delete home"/"update" heap paths (heap_file.c 24335, 25252), and `er_stack_push/er_set` while holding BCB mutex in page_buffer.c 4203. No lock-order cycle: nothing under er_Log_file_mutex waits for a page latch. | Level 3 |
| C6 | DML reads the policy from the cached class representation (`attr_info->values[i].last_attrepr->oos_storage`, built by `or_get_current_representation` from the class record). A flag-only ALTER writes the class record under X lock; `HEAP_MAYNEED_DECACHE_GUESSED_LASTREPRS` decaches on the root-heap update and `tx_transient_class_registry::decache_heap_repr` decaches on rollback. DML takes IX on the class (query_executor.c 13850, locator MVCC IX), which conflicts with the ALTER X lock, so no DML can fetch the representation between "class record written" and ALTER commit, and the representation is a single decoded object (no half-updated view). Edge: `heap_classrepr_decache` drops only unfixed entries, but a statement holding a fixed old repr also holds IX, so the ALTER cannot be in progress. | Level 3 |
| C7 | New shared mutable state is only `heap_Oos_test_bigone_without_oos_warnings`, a `std::atomic<int>` with relaxed add/load, compiled only under `CUBRID_UNIT_TEST_ENABLED` (CMake adds it when any unit test is enabled, so it can exist in a server built with unit tests). Tests use before/after deltas, so lack of a reset is fine. No other statics added; `oos_Policy_flags` is `static const`. | Level 2 |
| C8 | do_change_att_schema_only's loop over `oos_Policy_flags` is order-safe: GAINED clears the whole mask then sets one flag, LOST clears only its own flag; checked all six transitions among PREFER_INLINE / FORCE_OUTLINE / FORCE_INLINE. | Level 3 |

## Commands run and results
1. `git rev-parse HEAD` in the checkout -> 9ae07b949... (matches). `gh-pr-info` -> PR 8416 as above.
2. Read patch, spec, reviewers.md, CUBRID.md; grep/sed traces of the paths above (results folded into the tables).
3. `nm -C $CUBRID/lib/libcubridsa.so | grep heap_oos_warn_bigone_without_oos` -> 1 symbol present.
4. Probe database (not HA): `CUBRID_DATABASES=.../ha-concurrency/probe/databases cubrid createdb --db-volume-size=64M --log-volume-size=64M pdb en_US` -> exit 0 (probe/createdb.out).
5. `csql -S -u dba pdb -i probe.sql` (probe/probe.sql, probe.out): `create table t1 (id int storage default, a/b/c varchar(20000) storage force_inline)` accepted; `;schema t1` prints `STORAGE FORCE_INLINE` on a, b, c and nothing on the fixed `id`; inserts succeed. Exit 0.
6. First probe values were `repeat('a',7000)`. They did not trigger the notification because LZ4 string compression shrinks them (gdb showed `inline=216`). The estimate uses compressed disk size (existing behavior). Not a defect of this PR, but a test using repeat() would not exercise the path.
7. gdb batch run on `csql -S` with a breakpoint at heap_file.c:14271 and incompressible data (`md5('x1')||md5('x2')...`, 3 x 9600 chars, probe/p4.sql, probe/gdbcmds):
   - t1 (FORCE_INLINE): `HIT class=0|202|1 nvals=4 inline=28416 has_oos=0 max=16236`; csql.err has `NOTIFICATION ... heap_oos.cpp line 1103 CODE = -1393 ... A record of class 0|202|1 needs 28416 bytes ...`; statement printed "1 row affected", commit OK. Notification is not an error. (Level 4/5.)
   - t2 (default policy): `inline=116 has_oos=1`, no notification, as designed.
   - Backtrace at determine_disk_layout confirmed the INSERT call chain has no page latch held (C1).
No HA server processes were started. The probe directory is under .../ha-concurrency/probe/.

## Candidate findings
### Reproduced
None. The notification emission and non-error behavior were reproduced (C4) but no defect.

### Source-only
**HC-1 (low): blocking error-log I/O under a heap home page latch on the MVCC reevaluation path.**
- Location: src/storage/heap_file.c:14271-14274 (new call) reached via locator_sr.c `locator_lock_and_get_object` (13560-13650) -> `locator_mvcc_reev_cond_assigns` (~14002) -> `locator_allocate_copy_area_by_attr_info` -> `heap_attrinfo_transform_to_disk`.
- Preconditions: concurrent UPDATE/DELETE that must re-evaluate after waiting on a row lock, on a class whose rewritten row estimate exceeds `heap_Maxslotted_reclength` with no OOS (for example FORCE_INLINE or wide fixed columns).
- Failure: the notification takes `er_Log_file_mutex` and writes to the error log while the record's home page latch is held, lengthening latch hold time for other users of that page.
- Mitigation facts: rare path; existing code already does notification/ER logging under heap and BCB latches (C5), and the same path already runs a full OOS insert under that latch when `has_oos`. No deadlock cycle found.
- Evidence level 3 (source path; latch mode on home_page_watcher not checked). Disproof attempt: checked whether reev recdes is a copy (it is PEEK, `old_recdes` only becomes copy in the later force path). Unresolved: the latch mode. Suggested direction: accept (document), or emit the notification after the caller releases the latch.

**HC-2 (low, informational): unbounded notification per write.** Every INSERT/UPDATE of a no-OOS bigone row, including each loaddb row, logs one ~400-byte line under the global `er_Log_file_mutex` with fprintf/fflush. There is no rate limit or once-per-class filter. Spec says the report is intended; flag only for bulk-load log growth and mutex serialization. Evidence level 2. Next check: `loaddb` of N bigone rows, compare error log size and time against base.

**HC-3 (low, spec conformance, for spec/storage reviewer): no system/root class exemption.** The new check in `heap_attrinfo_transform_to_disk_internal` applies to every class. Spec line 122 says root and system class records are outside the rule; `locator_finalize_oos_record` excludes them for client-supplied records (`!OID_IS_ROOTOID && !oid_is_system_class`), but the server-side attr_info path (`locator_attribute_info_force`, line 7886) has no such guard. Whether any system class row can exceed 16236 bytes was not determined. Evidence level 2.

**HC-4 (informational, pre-existing): printed parse tree drops STORAGE DEFAULT / PREFER_OUTLINE.** `pt_print_attr_def` (parse_tree_cl.c ~7270) prints only PREFER_INLINE, FORCE_OUTLINE, FORCE_INLINE. On MODIFY of a variable column, omitted clause (UNSET) keeps the old flag while DEFAULT clears it, so a re-printed tree would change meaning. It is not on the HA path (H1: replication uses `sql_user_text`) and predates this PR (DEFAULT was already unprinted). Only `CREATE/ALTER SERVER` statements are re-printed for replication. Evidence level 3.

**HC-5 (informational, portability, pre-existing pattern): enum bit-fields.** `OR_ATTRIBUTE_OOS_STORAGE oos_storage:2` now holds value 3 and `attr_storage:3` holds value 5. With GCC on Linux, an enum with no negative enumerators is unsigned, so values fit. A compiler that treats enum bit-fields as signed (MSVC) would read 3 as -1 and FORCE_INLINE would silently behave as DEFAULT. The same hazard already existed for FORCE_OUTLINE. Evidence level 2. Relevant only if Windows builds are still supported.

## Cleared risks
- DDL clause lost in replication: cleared by H1 (SQL text replicated and replayed). Limit: source trace only, no HA run.
- Replica disagreement on layout or -1388 due to different policy flags: cleared by H3-H5 under the stated assumptions (same binary and page size on both sides, commit-order apply, class X lock serialization). Limit: not run on a real master/replica pair.
- Replica applying master bytes with master-local OOS or FORCE_INLINE state: cleared; replica re-lays out from values (H3).
- Notification clobbering caller error state: cleared by C4 (runtime).
- Half-updated policy visible to DML during concurrent ALTER: cleared by C6 (lock + decache).
- Race on the new test counter: cleared (C7).
- Error-code renumbering: `ER_HEAP_BIGONE_WITHOUT_OOS=-1393`, `ER_LAST_ERROR=-1394`, en_US and ko_KR catalogs updated, the arrays sized by `-ER_LAST_ERROR` grow automatically; er_set accepts -1393 (runtime proved the message prints). Merge-time risk: another branch may also claim -1393 (spec notes numbers shift with develop merges).

## Not applicable
- Older-binary readability of the new catalog flag (HA question 3): not applicable. The OOS storage format is unreleased and guarded by `disk_check_storage_format` (ER_BO_INCOMPATIBLE_STORAGE_FORMAT, "unreleased builds of one disk compatibility level ... must be recreated"), so mixed-version HA with an older binary is not supported for databases that carry OOS. For information only: the pre-PR `or_get_current_representation` masks only PREFER_INLINE/FORCE_OUTLINE bits, so an older OOS build would read bit 0x4000 as DEFAULT without crashing. No requirement was invented.
- HA runtime check: out of scope. Next check if wanted: master/replica with a FORCE_INLINE table; run `ALTER ... MODIFY c STORAGE FORCE_INLINE`, then inserts and updates of a >16236-byte row, then compare `;schema`, row lengths and the replica error log (expect -1393 notification, no -1388).

## Coverage status
complete for source tracing of all assigned HA and concurrency questions; runtime evidence limited to the single-node SA probe above (no HA processes, as instructed). Open items: HC-1 latch mode; HC-3 whether any system class record can exceed the limit; the spec's open question about UPDATE reuse of stubs after a policy change (CBRD-27230) affects replica reuse markers and was not tested.
