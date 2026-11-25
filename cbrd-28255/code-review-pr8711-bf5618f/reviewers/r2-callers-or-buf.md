# r2 - Systems/callers + concurrency/recovery/HA applicability seat - CUBRID/cubrid#8711

## Identity and scope
- Pinned SHA: bf5618f6275c4a1053b648b17b22786dca31bfcc (verified `git rev-parse HEAD`, worktree clean). Base 6d8296b15c.
- Patch: only src/storage/heap_file.c (+57/-31). No build, no server run by this reviewer (read-only source review).
- Inspected (all at the pinned head):
  - src/storage/heap_file.c: heap_midxkey_get_value 12558, heap_midxkey_locate_record_attr 12657, heap_midxkey_get_oos_extra_size 12686,
    heap_midxkey_attr_extra_size 12729, heap_locate_last_attrepr 13212, heap_midxkey_key_get 16058, heap_midxkey_key_generate 16255,
    heap_attrinfo_generate_key 16399, heap_attrvalue_get_key 16583.
  - src/base/object_representation.h (or_init 1534, or_advance 1578, or_pad/or_put_align32/or_put_* , or_put_data 2144, or_multi_header_size 2712).
  - src/object/object_representation.c (or_put_varchar_internal 789-933), src/object/object_primitive.c (all mr_index_writeval_*, string/char/bit/varbit/numeric internals, pr_write_*_to_buffer 14586/14663).
  - src/base/object_representation_sr.c (or_get_default_value 1380), src/query/execute_schema.c (ALTER CHANGE modes 11060-11215, 12840-12900), locator_sr.c xlocator_upgrade_instances_domain 14679.
  - All callers listed in section 2; btree_sort.c parallel worker setup (1887-1893, 2060-2085); btree_load.c bt_load_heap_scancache_start_for_attrinfo 1125.

## 1. Shared question Q1
Q1: "Is there any reachable record/schema/index state where the bytes written into midxkey.buf exceed MAX(midxkey_size, DBVAL_BUFSIZE) at the PR head?"

Answer: no. I could not construct a reachable state where the key exceeds the bound. One exotic hypothesis (H-NUM: fixed NUMERIC default re-read through a float-NUMERIC domain) was examined and rejected by source (section 6). Evidence level 3 (complete path argument, per-type enumeration of index_writeval vs data encoding); no execution evidence from this seat.

Decomposition. Bytes written = or_multi_header_size(num) + sum over key columns of index_writeval length. Estimate = recdes->length + or_multi_header_size(num) + sum over key columns of extra (default val_length if the attribute is not in the record's representation, else OOS ref length, else 0) [+ OR_VALUE_ALIGNED_SIZE(func_res) for function indexes]. `num` is identical in estimate and writer: generate_key header uses `func_index_info ? fi_attr_index_start+1 : attr_info->num_values` (heap_file.c:16471), writer uses `func_res ? func_attr_index_start+1 : attrinfo->num_values` (16280-16284); get_key estimate `index->func_index_info ? attr_index_start+1 : n_atts` (16658) vs writer `num_atts = n_atts; if (func_res) attr_index_start+1` (16072-16076), and func_res is non-NULL iff func_index_info is non-NULL in both callers (16427-16436, 16627-16634).

Safety facts (S1-S6):
- S1 (estimate and writer use the same attribute object). Absent case: estimate uses `heap_locate_last_attrepr` (generate_key) or `index->atts[i]` (get_key), both the last-representation OR_ATTRIBUTE; writer in key_generate uses `heap_locate_attribute` = read_attrepr if non-NULL else last_attrepr (13196-13199 pattern), and absent means read_attrepr==NULL, so same object; key_get uses `atts[i]` directly. heap_midxkey_get_value (12575) decides "present/absent" with the same `heap_midxkey_locate_record_attr` (by att->id against read_classrepr, or att itself when rep id == last), so the estimate branch and the write branch cannot diverge. Level 2-3.
- S2 (present, non-OOS columns are inside recdes->length). `heap_attrvalue_point_fixed/variable` return raw pointers inside recdes (12597-12613); key encoding of such a value <= its disk encoding (see S3). Record header, var offset table, bound bits, NUL and padding of strings are slack. Level 2-3.
- S3 (index_writeval length <= disk length of the same value; roundtrip). Fixed types (int, short, bigint, float, double, time, utime, date, enum): or_put_data(tp_X.disksize) of the same type (object_primitive.c 2430-4755, 14256) == tp_domain_disk_size. string/char (CHAR_ALIGNMENT) vs data (INT_ALIGNMENT): key = 1(+8 if >=255) + bytes, disk adds NUL + align32 (pr_write_*_to_buffer 14586-14716; mr_writeval_string_internal 10750; mr_writeval_char_internal 12042). Compressed values: SERVER/SA readval keeps the compressed buffer (object_primitive.c ~10905 `#if defined(CS_MODE)` else branch), DB_TRIED_COMPRESSION is set, so the key writes the compressed form again (9 + compressed bytes). Uncompressable >= 255: 9 + size, no recompression. bit/varbit: same bytes, no alignment (12975, 13719). numeric: mr_index_writeval_numeric == mr_data_writeval_numeric, value built from the stored header (precision/scale/size) so the roundtrip reproduces the stored size (8693-8740, 8800-8830) except H-NUM. Level 2-3.
- S4 (NULL columns write nothing). `if (!DB_IS_NULL (&value))` guards every writeval (16145-16150, 16329-16334); NULL fixed columns still occupy full disk bytes, so many-NULL keys only gain slack. Level 2.
- S5 (OOS). `heap_midxkey_get_oos_extra_size` returns the OOS chain length (stub bytes also inside recdes->length, so double-counted = slack). Corrupt stub -> 0, read later reports the error (unchanged). Level 2.
- S6 (capacity = bound). Stack path: caller buffers are `char buf[DBVAL_BUFSIZE + MAX_ALIGNMENT]` + PTR_ALIGN(MAX_ALIGNMENT) (section 2), usable >= 4096 = the bound used when midxkey_size <= 4096. Heap path: db_private_alloc(midxkey_size) == the bound. Level 2.

Hypotheses tried and cleared:
- Compressed strings: key <= disk (S3); the recompression path cannot run for values read from disk (compression state is set by readval).
- Fixed CHAR precision vs record representation domain after ALTER: present columns are read with the record's own (old) domain (get_value `att = record_att`, 12575-12580), so padding precision == what was stored. CHAR/BIT precision changes are UPGRADE (ATT_CHG_TYPE_UPGRADE, execute_schema.c 12853) -> `xlocator_upgrade_instances_domain` rewrites every tuple to the latest representation (locator_sr.c 14657-14660 "The entire tuple is rewritten"), so no absent/old CHAR rows survive. NUMERIC precision increase (ATT_CHG_TYPE_NUMERIC_PREC_INCR) also forces the row rewrite: `is_srv_update_needed` is true for it (execute_schema.c:11066-11068) and runs do_run_upgrade_instances_domain (11180-11213). Only VARCHAR/VARBIT precision increase (ATT_CHG_TYPE_PREC_INCR) stays schema-only, and a VARCHAR/VARBIT precision change does not change the key or default bytes. Default CHAR(n) is coerced to the column domain on ALTER ADD (schema_template.c:1363 tp_value_cast), so stored padded. Level 2-3 (unproven by execution).
- Function-index results: OR_VALUE_ALIGNED_SIZE = or_db_value_size + MAX_ALIGNMENT (object_representation.h:54); CHAR results padded identically by lengthval and writeval. func-arg columns that are not written are still estimated (n_atts loop covers atts beyond attr_index_start), so only over-estimation. Level 2.
- Many NULL columns / header: header counted via or_multi_header_size (n+7)/8 + n+1 (object_representation.h 2688-2715) with n identical to the writer's.
- Attribute in record rep with a different domain in the last rep: key_get writes through `atts[i]->domain->type` (last rep's type object) while the value was read with the old domain. Different type objects are only possible for non-schema-only changes, which rewrite rows (above); same-type changes keep the same writer. Level 2.
- Fixed vs variable layout mismatch between old and last rep: location comes from record_att (old rep) in estimate and writer (S1).

## 2. Caller buffer contract (Q2)
Every caller passes `char buf[DBVAL_BUFSIZE + MAX_ALIGNMENT]` aligned with PTR_ALIGN(.., MAX_ALIGNMENT) (DOUBLE_ALIGNMENT, memory_alloc.h:77), so usable bytes >= DBVAL_BUFSIZE (4096, btree.h:566). No caller passes NULL or a smaller buffer. Grep over the whole tree (src, plus non-src dirs): no other caller, no function-pointer use.

heap_attrvalue_get_key (call site -> buffer declaration):
- src/query/query_executor.c:18148 (qexec_remove_duplicates_for_replace) -> 18081-18082
- src/query/query_executor.c:18378 (qexec_oid_of_duplicate_key_update) -> 18312-18313
- src/transaction/locator_sr.c:4303 (locator_check_foreign_key) -> 4229, 4247
- src/transaction/locator_sr.c:4661 (locator_child_still_refers) -> 4636, PTR_ALIGN inline arg
- src/transaction/locator_sr.c:5916 (locator_wait_for_row_child_writers) -> 5891
- src/transaction/locator_sr.c:10309 (locator_add_or_remove_index_internal) -> 10202, 10228
- src/transaction/locator_sr.c:10944 / 10947 (locator_update_index) -> 10725-10726, 10777-10778 (separate old/new buffers)
- src/transaction/locator_sr.c:11239 / 11277 (locator_update_index, replication keys) -> same aligned_oldbuf / aligned_newbuf
- src/transaction/locator_sr.c:11527 / 11550 (xlocator_remove_class_from_index) -> 11422, 11440
- src/transaction/locator_sr.c:11968 (locator_check_btree_entries, checkdb) -> 11865, 11888
- src/transaction/locator_sr.c:12429 (locator_check_unique_btree_entries) -> 12301, 12322
heap_attrinfo_generate_key:
- src/storage/btree_load.c:5950 (btree_sort_get_next_parallel) -> 5732, 5746
- src/storage/btree_load.c:6246 (btree_sort_get_next) -> 6089, 6099
- src/storage/btree_load.c:7650 (online_index_builder, serial and parallel loader) -> 7561, 7574
- src/transaction/locator_sr.c:14328 (xlocator_check_fk_validity, ADD FOREIGN KEY) -> 14284, aligned at 14305ish
Also verified for generate_key callers: attr_info is started with exactly n_attrs attributes (bt_load_heap_scancache_start_for_attrinfo btree_load.c:1147-1150; xlocator_check_fk_validity heap_attrinfo_start(n_attrs)), so `attr_info->num_values == n_atts` and the header estimate (num_values) matches the n_atts loop. Level 2.

Ownership of the key on callers (heap path now taken more often): every caller already handled heap-owned keys (need_clear set at 16511/16694): pr_clear_value at query_executor.c 18260/18270/18471/18481, locator_sr.c 4388/4408/4414/4688/5929/10498/10509/11219/11224/11301/11317/11354/11359/11483/11522/12051-12053/12510-12512/14341, btree_load.c 5963-6059 and 7674. The PR only raises the frequency of the heap path (records within header+defaults of 4096), no new ownership rule. Level 2.

## 3. or_init / OR_BUF semantics (Q3)
- or_init (object_representation.h:1534-1550): `length <= 0 || length == DB_INT32_MAX` -> endptr = OR_INFINITE_POINTER (all-ones); otherwise endptr = data + length. With the PR, length is always >= 4096 (MAX with DBVAL_BUFSIZE), so it is finite (except the degenerate exact INT_MAX).
- Every write on the key path is debug-assert only: or_advance 1578, or_pad 1597, or_put_align32 1611, or_put_byte 1713, or_put_short 1747, or_put_int 1784, or_put_bigint 1821, or_put_oid 2553, or_put_data 2144, or_put_varbit_internal (object_representation.c 764/769/776), mr_writeval_varbit_internal 13794. All compiled out in release (CMakeLists.txt:230,232 `-DNDEBUG`).
- Runtime (release) endptr checks exist only in or_put_varchar_internal (object_representation.c:928, post-hoc `ptr > endptr` -> ER_TF_BUFFER_OVERFLOW; reachable via or_packed_put_varchar, not via mr_index_writeval_string/char which use pr_write_*_to_buffer without the check) and in mr_data_writeval_set (object_primitive.c:7061/7086; sets cannot be key columns). Reader-side runtime guards (8531, 8776-8815) apply to the read buffer `OR_BUF buf` in heap_midxkey_get_value, unaffected by this change.
- key_get/key_generate only use `buf` for or_advance, index_writeval and `buf.ptr - buf.buffer` arithmetic (16086-16228, 16292-16360); no readval touches it.
Conclusion: a finite size cannot turn a former silent success into a release error on the key path; release behavior is identical. In debug builds the new asserts fire only on a real overflow of the actual capacity (S6). No new error return, hence no new leak/mishandling of midxkey.buf or domain on a buffer-overflow path. Level 3 (complete path + callee enumeration), no execution. (Backport note, from the PR text: 11.4 or_put_data checks at runtime; not applicable at this head.)

## 4. Ownership / error paths (Q4)
Unchanged and verified by diff: allocation condition `midxkey_size > DBVAL_BUFSIZE` (db_private_alloc at 16486/16672) and the identical condition on the error path free (generate_key error block `db_private_free_and_init`, get_key error block) and on success `need_clear = true`. `midxkey_size` is not modified after the allocation in either function. `pr_clear_value (db_valuep/db_value)` on error covers the function-index result; `set_domain` freed at get_key `error:`. The three new callees (heap_midxkey_attr_extra_size, heap_midxkey_locate_record_attr, heap_locate_last_attrepr) allocate nothing and have no error return that can skip cleanup. Edge (theoretical, pre-existing pattern): int overflow of midxkey_size (sum of >= 3 default values near 1 GiB) would make `midxkey_size > DBVAL_BUFSIZE` false and select the stack buffer; not reachable with real index keys, noted only. `(int) ref.length ()` truncation is pre-existing. Level 2.

## 5. Concurrency / Recovery / HA (Q5)
- Concurrency: the new code reads only (a) caller-owned recdes (copy, or page-latched PEEK in btree_sort_get_next*), (b) the per-thread HEAP_CACHE_ATTRINFO, (c) immutable cached OR_CLASSREP objects referenced by attr_info (last_classrepr/read_classrepr are fixed for the attr_info's lifetime). Estimate and writer read the same OR_ATTRIBUTE (S1), no TOCTOU. Parallel index build: btsort_start_parallelism memcpy's SORT_ARGS per worker (btree_sort.c:1887-1893) but each worker memsets and restarts its own `attr_info` (btree_sort.c:2070-2085 -> bt_load_heap_scancache_start_for_attrinfo btree_load.c:1147), and the key buffer is a per-call stack array (5732, 6089, 7561); `heap_attrinfo_recache` in generate_key (16462-16468, unchanged except comment) therefore mutates only worker-local state. Online index builder: attr_info is the local one started at btree_load.c:7378. N/A for lock/latch/atomics: the patch adds none. Level 2-3.
- Recovery: N/A. The diff changes no log record, RV index, undo/redo data, page layout or flush ordering; the bytes written into midxkey.buf are the same bytes as before wherever the old code did not overflow. Level 2 (grep of diff: only heap_file.c, no log_*/rv calls).
- HA: N/A with a note. Replication items take the key via locator_update_index (locator_sr.c 11239-11330 repl_log_insert with the DB_VALUE key); the key serialization format is unchanged. Keys that were previously corrupted by overflow (garbage/overwritten) are now correct, which only improves slave-side lookups; no producer/consumer field is added, no NULL/default field value is newly produced. Level 2.

## 6. Candidates
None. No defect candidate supported by evidence at this seat.

### Rejected hypothesis H-NUM (was proposed P3)
- Claim tested: a fixed NUMERIC(p,s) default (stored header precision p<40, by-value size) read through the last domain after a NUMERIC precision increase to precision 40 (DB_DEFAULT_NUMERIC_PRECISION, dbtype_def.h:622) is flagged float (object_primitive.c:8463, 8800) and mr_data_writeval_numeric (8706-8735) would write by-precision size (up to 20 bytes) while heap_midxkey_attr_extra_size counted only default_value.val_length (heap_file.c:12736), up to 16 bytes per column.
- Rejection: the precondition (old-representation rows that lack the column after the type change) cannot survive. ATT_CHG_TYPE_NUMERIC_PREC_INCR sets `is_srv_update_needed` (execute_schema.c:11066-11068), which runs do_run_upgrade_instances_domain for the class, or each partition user (11180-11213); xlocator_upgrade_instances_domain rewrites the entire tuple in the latest representation (locator_sr.c:14657-14660, loop from 14727). After it no row is in an older representation, so the default path is never taken for that column. Present (non-default) rows read with the record's own old domain (heap_file.c:12575-12580), so the float flag follows the stored encoding.
- Residual (not a defect): a concurrent or crash-interrupted ALTER leaves the catalog and heap under SCH_M_LOCK/transaction rollback, not a state visible to index key generation. Evidence level 3 (source). Not executed.
- Executable check if the coordinator wants closure (debug build, `csql -S`): CREATE TABLE t(id INT, big VARCHAR(5000)); INSERT one row with a 4090-char incompressible big; ALTER TABLE t ADD COLUMN n1 NUMERIC(38,0) DEFAULT 1 (repeat n1..n6); ALTER TABLE t CHANGE COLUMN n1 n1 NUMERIC (repeat n2..n6); CREATE INDEX i ON t(big,n1,n2,n3,n4,n5,n6); cubrid checkdb. Expected: no or_put_data assert, checkdb clean.

## 7. Cleared risks (with limits)
- Release behavior change from a finite or_init size: cleared (section 3), source enumeration, level 3.
- Caller buffer contract (>= DBVAL_BUFSIZE usable): cleared for all 15 call sites (section 2), level 2 (no runtime assertion run).
- Ownership/error-path regression: cleared (section 4), level 2.
- Parallel/online index build attr_info sharing: cleared (section 5), level 2-3.
- Recovery/HA/log impact: N/A (section 5).
- H-NUM (NUMERIC default re-read through float domain): rejected by source, section 6, level 3.
- Key header size / attribute count mismatch between estimate and writer: cleared, level 2 (func and non-func variants).

## 8. Unresolved questions
- None material. Residual items are execution-only confirmations of source arguments (S1, S3 for every index-capable type). H-NUM closure check is in section 6.
- Compile check of the diff is left to the coordinator build (heap_file.c is compiled as C++; new code uses a block-scope loop variable and MAX (macro, evaluates twice, args side-effect free)).
- Coordinator-run suggestion for S6/S1 as an executable guard: in a debug build, temporarily assert `midxkey->size <= MAX (midxkey_size, DBVAL_BUFSIZE)` after both writers over the PR's TC corpus plus an index-build matrix over all index-capable types with ADD COLUMN DEFAULT, to extend S3 to all types. A passing run supports only the tested types/data.
- Observation (not a defect): heap_midxkey_locate_record_attr now runs twice per key column per old-representation record (estimate + write), linear in the number of attributes of the old representation; negligible for normal widths, mention to the performance seat if wide tables with many old representations matter.

## 9. Budget and coverage
Budget: about the 40-minute target, no overrun, no agents spawned. Coverage: complete (source level) for assignments 1-5; assignment 1 is execution-unproven (level 3). Nothing posted, no source modified.
