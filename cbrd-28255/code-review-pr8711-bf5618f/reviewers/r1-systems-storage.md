# r1 — Systems + Storage seat — CUBRID/cubrid#8711 (CBRD-28255)

## Pinned identity

- Checkout `/home/vimkim/gh/cb/CBRD-28255`, `git rev-parse HEAD` = `bf5618f6275c4a1053b648b17b22786dca31bfcc` (verified, clean).
- Base / merge-base `6d8296b15c9694a7fc2c7920e539ec66d3d004aa`. Patch: `review-8711/patch.diff` (only `src/storage/heap_file.c`).
- No build, no server run (per brief). All evidence below is source-level (levels 2–3). Nothing reproduced.

## Inspected paths

- `src/storage/heap_file.c`: `heap_midxkey_get_value` (12558), `heap_midxkey_locate_record_attr` (12657), `heap_midxkey_get_oos_extra_size` (12686), `heap_midxkey_attr_extra_size` (new, 12727), `heap_locate_attribute` (13188), `heap_locate_last_attrepr` (13212), `heap_midxkey_key_get` (16058), `heap_midxkey_key_generate` (16255), `heap_attrinfo_generate_key` (16399), `heap_attrvalue_get_key` (16583), `heap_attrinfo_start`, `heap_eval_function_index` (result/domain only).
- `src/object/object_primitive.c`: index/data writeval + readval for string (VARCHAR), CHAR, BIT, VARBIT, NUMERIC, ENUM, all fixed scalar types, `pr_do_db_value_string_compression`, `mr_lengthval_char/string`, `pr_write_(un)compressed_string_to_buffer`.
- `src/base/object_representation.h`: `or_init`, `or_put_data/byte/short/int`, `or_advance`, `or_pad`, `or_put_align32`, `or_varchar_length_internal`, `or_varbit_length_internal`, `or_multi_header_size`, `or_multi_put_*offset`, `OR_VALUE_ALIGNED_SIZE`.
- `src/object/object_representation.c`: `or_packed_value_size`, `or_db_value_size`, `or_put_varbit`.
- `src/base/object_representation_sr.c`: `or_get_default_value` (how `default_value.val_length/value` are built).
- `src/query/numeric_opfunc.h/.c`: `numeric_repr_disk_size_by_value/_by_precision`, float-numeric coercion.
- `src/query/execute_schema.c`: ALTER CHANGE type classification (`ATT_CHG_TYPE_PREC_INCR`, `ATT_CHG_TYPE_NUMERIC_PREC_INCR`, UPGRADE/NEED_ROW_CHECK → row update), constraint drop/rebuild at 11180.
- `src/object/object_domain.c`: `tp_domain_match` TP_STR_MATCH for VARCHAR/VARBIT vs CHAR/BIT.
- `src/object/schema_manager.c`: `build_storage_order` (domain change ⇒ new representation).
- Callers: `btree_load.c` (5950, 6246, 7650, `bt_load_heap_scancache_start_for_attrinfo` 1147), `locator_sr.c` (all `heap_attrvalue_get_key` callers and 14328), `query_executor.c` 18148/18378; all stack buffers.
- `src/storage/heap_oos_value_ref.hpp` (`length()` is `std::size_t`).

## Invariants checked

- I1 (buffer capacity): bytes written into `midxkey.buf` ≤ real capacity = `midxkey_size` if heap-allocated, else `DBVAL_BUFSIZE` (caller stack buffer).
- I2 (bound passed to `or_init`): `MAX(midxkey_size, DBVAL_BUFSIZE)` equals that real capacity.
- I3 (estimate decomposition): written = `or_multi_header_size(n)` + Σ key elements (+ func result). Estimate = `recdes->length` + `or_multi_header_size(n')` + Σ extras (+ `OR_VALUE_ALIGNED_SIZE(fi_res)`). Need n == n' and, per key column, key bytes ≤ bytes the estimate attributes to it.
- I4 (ownership): heap/stack choice, `need_clear`, and the free on the error path use the same predicate `midxkey_size > DBVAL_BUFSIZE`.

## Shared question Q1 — answer

**No reachable record/schema/index state was found in which the bytes written exceed `MAX(midxkey_size, DBVAL_BUFSIZE)` at the PR head, under the stated preconditions.** These preconditions are: no duplicate key columns, type changes rewrite rows, and the on-disk strings use the current encoding. Evidence level 3 (complete source path argument). There is no execution evidence (level 4/5 not attempted per brief). See the "Runtime probes" section for checks that could refute this.

### Safety facts

| # | Fact | Evidence | Level |
|---|---|---|---|
| S1 | Header count matches: generate_key estimate uses `fi_attr_index_start+1` or `attr_info->num_values` (heap_file.c:16472); `heap_midxkey_key_generate` advances by `or_multi_header_size(num_vals)` with the same choice (16280–16297). get_key uses `attr_index_start+1` or `n_atts` (16661) == `heap_midxkey_key_get` `num_atts` (16074–16089). `func_res != NULL` iff `func_index_info != NULL` in both. `or_multi_header_size` includes the size-offset slot (object_representation.h:2712, 2856). | source | 3 |
| S2 | `attr_info->num_values == n_atts` for every generate_key caller: `heap_attrinfo_start` sets `num_values = requested_num_attrs` (capped only downward); btree_load (1147, online path 7400 via same helper) and locator_sr.c:14316 start attr_info with the same `n_attrs/attr_ids` passed to generate_key. When it is capped, the estimate loop skips ids that `heap_locate_last_attrepr` does not find. So (f): `num_values` is never smaller than the number of elements written; the element count *is* `num_values`. | source | 3 |
| S3 | Default vs record attribute decision is identical in estimate and writer. Estimate: `heap_midxkey_attr_extra_size` → `heap_midxkey_locate_record_attr(recdes, att, attr_info)`. Writer: `heap_midxkey_get_value` calls the same function and uses the default only when it returns NULL (12575–12591). generate_key passes `last_attrepr`, while key_generate passes `heap_locate_attribute` = `read_attrepr ?: last_attrepr`. Both have the same `id`. `locate_record_attr` matches by id in `read_classrepr`, or returns `att` when rep == last rep, so both resolve the same record attribute or the same `last_attrepr->default_value` (e). Dropped attribute: the index is dropped with it. Re-added same name: new id ⇒ absent ⇒ default in both. | source | 3 |
| S4 | All fixed scalar types write exactly `tp_X.disksize` in `index_writeval` (int, short, bigint, float, double, time, utime, timestamptz, datetime, datetimetz, money, date, object/oid, enum) = the disk size of the fixed record field. No per-element alignment in midxkey (`or_put_data`, CHAR_ALIGNMENT). (c) | object_primitive.c index_writeval bodies | 2 |
| S5 | VARCHAR/CHAR: on SERVER/SA builds, `mr_readval_string_internal`/`mr_readval_char_internal` keep the on-disk compressed bytes (`db_set_compressed_string(value, compressed, size, true)`) or mark `DB_UNCOMPRESSABLE`. `mr_writeval_{string,char}_internal` then re-emit the same compressed/uncompressed payload with the same length prefix. The index form (CHAR_ALIGNMENT) drops only the NUL and INT padding (`or_varchar_length_internal`). So key ≤ disk for record values, OOS payloads and default images. (a) | object_primitive.c:10776–10955, 12057–12280; object_representation.h:2416 | 3 |
| S6 | CHAR is never re-padded on the key path: the char reader sets `medium.length = precision` of the *read* domain, and `db_get_string_length` returns `medium.length` when set (string_opfunc.c:8527). So `char_count == src_precision` and `pr_pad_char_to_precision` is skipped. BIT writes `STR_SIZE(value precision)` = disk size of the record domain. VARBIT index ≤ packed varbit. (b) | object_primitive.c:12057–12095, 12990–13050; string_opfunc.c:8523–8530 | 3 |
| S7 | The domain of the record representation drives both the disk format and the read. A domain change always creates a new representation (`build_storage_order`, schema_manager.c:10052–10057). Schema-only ALTER CHANGE is limited to VARCHAR/VARBIT precision increase (`TP_STR_MATCH`, same type; CHAR/BIT require equal precision ⇒ UPGRADE/row update) and `NUMERIC_PREC_INCR`. All type changes go through row update. Key writers size from the *value* (read with the record domain), not from `atts[i]->domain` precision. So a larger last-rep precision cannot inflate the key. (b) | execute_schema.c:12836–12895, 11180; object_domain.c:1754–1803 | 3 |
| S8 | NUMERIC: disk and index use the same `mr_data_writeval_numeric` (index wrapper). Size is by value, or by header precision for float numeric. Float-ness is read from the domain precision (== 40 sentinel), and the coercion to such a domain always makes a float value (`numeric_opfunc.c:7168`). So the key size equals the record size. (c) | object_primitive.c:8697–8830; numeric_opfunc.c:7138–7185 | 2 |
| S9 | `default_value.val_length` is the catalog's disk image length after the domain tag (`or_get_default_value`, object_representation_sr.c:1380–1416). It is read through `data_readval` and then `index_writeval`, so S5/S6 apply. Original (add-time) default is used by both estimate and writer. | source | 3 |
| S10 | Function index (d): `OR_VALUE_ALIGNED_SIZE(fi_res)` = `or_packed_value_size(...,include_domain)` + MAX_ALIGNMENT. This uses `type->get_disk_size_of_value` = data lengthval (INT alignment; CHAR lengthval pads the value *in place* and tries compression), so the later `index_writeval` of the same value is ≤. In generate_key the writer type is `tp_domain_resolve_default(type of fi_res)`, the same type as the value. Estimate loops cover *all* `n_atts`, including function-argument attributes, which is only an over-estimate. | object_representation.h:54; object_representation.c:4739–4805 | 3 (get_key: see U2) |
| S11 | I2: every caller buffer is `char buf[DBVAL_BUFSIZE + MAX_ALIGNMENT]` aligned with `PTR_ALIGN(…, MAX_ALIGNMENT)` (locator_sr.c 4229, 4636, 5891, 10202, 10725/6, 11422, 11865, 12301, 14284; btree_load.c 5732, 6089, 7561; query_executor.c 18081, 18312). So the bound equals the real capacity, and the debug asserts fire only on a real overrun. | source | 3 |
| S12 | Release behaviour unchanged: `or_put_data/byte/short/int`, `or_advance`, `or_pad`, `or_put_align32` check `endptr` only with `assert` (object_representation.h:1578–1791, 2144). There is no release-mode error return that the unchecked `index_writeval` return value could silently drop, so passing a finite bound cannot cause a silent truncation in release. | source | 2 |
| S13 | I4: allocation, error-path free (`midxkey_size > DBVAL_BUFSIZE`), and `need_clear` all use the same unchanged predicate (16484–16516, 16667–16698). The larger estimate only moves borderline keys from stack to heap, and ownership stays consistent. | source | 3 |

### Cleared risks / rejected hypotheses

- H-a (compressed record string decompressed into key): rejected, S5. CS_MODE drops the compressed copy, but CS_MODE does not build midxkeys.
- H-b1 (CHAR(n)→CHAR(m) without rewrite pads key to m): rejected. CHAR precision change is not `TP_STR_MATCH` ⇒ UPGRADE/row update, and the writer never re-pads (S6, S7).
- H-b2 (varchar→char or type change without rewrite): rejected. A type change ⇒ row update and constraint rebuild (S7). Hierarchy type changes are guarded by `ER_ALTER_CHANGE_CLASS_HIERARCHY` (not fully traced, level 2).
- H-c (alignment/padding inflation): rejected (S4, S5). The index form is CHAR_ALIGNMENT, and disk is INT-aligned with a NUL.
- H-e (estimate and writer resolve different attributes/defaults): rejected (S3). This also covers partition/inheritance, because attr_info is per class and ids are shared.
- H-f (`num_values` < written elements): rejected (S2).
- H-dup (same column twice in one key ⇒ double use of one record field): blocked by `ER_SM_INDEX_ATTR_DUPLICATED` / `MSGCAT_SEMANTIC_INDEX_ATTR_DUPLICATED` (semantic_check.c:13958).
- H-bound (finite `or_init` bound causes false debug asserts): rejected (S11). The bound equals the real capacity.

## Candidate findings

No P1–P3 defect candidate introduced by the PR. Two low-priority, pre-existing residuals are recorded for completeness:

### R1-C1 (P4, pre-existing, not introduced): `midxkey_size` int overflow from OOS lengths

- Location: heap_file.c:12715 `return (int) ref.length ();` with accumulation at 16478 / 16663 (`int midxkey_size`).
- Failure: `ref.length()` is `std::size_t` (decoded from a 64-bit stub length). A corrupt stub with length > INT_MAX, or two near-`DB_MAX_STRING_LENGTH` (~1 GB) OOS values in one composite key, makes `midxkey_size` wrap negative. Then `midxkey_size <= DBVAL_BUFSIZE` ⇒ the 4 KB stack buffer is used ⇒ a large overrun. `MAX(midxkey_size, DBVAL_BUFSIZE)` then equals 4096, so only the debug build asserts.
- Preconditions: corrupted OOS stub (only `heap_recdes_get_oos_inline_stub` field-boundary check is applied), or a ~2 GB composite key. Practically unreachable for valid data.
- Introduced? No. The OOS summation existed at base. The PR adds `default_value.val_length`, which is bounded by the class record. The PR does not widen the type.
- Fix direction: accumulate in `INT64`/`size_t`, and fail with an error (or clamp to heap allocation) when the value exceeds a sane maximum. Treat stub length > `DB_MAX_STRING_LENGTH` as corruption in `heap_midxkey_get_oos_extra_size`.
- Evidence level 2. No execution. Disproof attempts: checked that the `(int)` cast has no guard, and that `heap_oos_value_ref::decode` returns no error for large lengths (not fully traced).

### R1-C2 (P4/question, pre-existing): `heap_midxkey_key_get` writes the function result with `func_domain->type`, not the value's type

- Location: heap_file.c:16098 `func_domain->type->index_writeval (&buf, func_res);` vs the estimate `OR_VALUE_ALIGNED_SIZE(fi_res)` (16649), which uses the value's own type.
- Concern: if `func_pred->func_regu->domain` type ≠ the runtime type of the result (`heap_eval_function_index` clones the result and does not cast it to the domain), the writer may size differently. The worst case is a CHAR writer that receives a VARCHAR value with non-floating precision and pads to that precision.
- Not shown reachable: the regu domain normally equals the result type. generate_key avoids this by using `tp_domain_resolve_default(value type)`. Not introduced by the PR.
- Evidence level 1–2. The cheapest check is `assert (TP_DOMAIN_TYPE (func_domain) == DB_VALUE_DOMAIN_TYPE (func_res))` at 16098 under the function-index regression suite.

## Unresolved questions

- U1: Databases migrated from versions before string compression (old `0xFF + int len` varchar encoding, 5-byte prefix) would be rewritten by the index writer with the 9-byte new prefix (+4 bytes per long string). Per-record slack (record header + var offset table ≥ 2 bytes/var attr with ≥ 2-byte offsets) very likely absorbs this, and supported upgrade paths may forbid such images. Not verified. Applies equally to base.
- U2: Function-index `heap_attrvalue_get_key` path: see R1-C2.
- U3: `ER_ALTER_CHANGE_CLASS_HIERARCHY` coverage for type changes of inherited attributes was not traced to its raise site.

## Runtime probes the coordinator could run (debug build of head, which now asserts on overrun)

1. Jira case (default path, get_key + generate_key):
   ```sql
   create table t (id int primary key, a int);
   insert into t select rownum, rownum from db_class limit 10;
   alter table t add column c varchar(5000) default repeat('x', 4200);
   create index i_c_id on t (c, id);      -- generate_key (btree_load)
   update t set a = a + 1;                -- get_key old+new
   delete from t where id = 1;
   ```
   Expected at head: no assert/crash; `checkdb -S <db>` clean. At base: overflow (Jira).
2. Header-only case (no ADD COLUMN): 60 SMALLINT + 1 VARCHAR columns, composite index on all 61, row near 4050 bytes. Expected: no assert at head.
3. Compression case: two `VARCHAR(20000)` columns filled with `repeat('a', 8000)` (highly compressible), composite index `(v1, v2, id)`. The key must stay compressed (S5). Expected: `midxkey_size < 4096` stack path, no assert.
4. CHAR default: `alter table t add column ch char(3000) default 'a'; create index i2 on t(ch, id);`. Expected: no assert (padding is in the default image).

## Budget status

About 40 minutes used. Stopped at the budget, with Q1 sub-items a–f covered at level 2–3.

## Coverage

`partial`: source-level coverage of Q1 (a)–(f), overflow and ownership is complete. No execution evidence, because building and running were excluded by the brief. Probes 1–4 above are the cheapest refutation checks.
