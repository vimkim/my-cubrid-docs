# F3 forward-audit notes — query/optimizer explicit policy sites (CBRD-26847)

Scope: fwd-query. Read-only tree /home/vimkim/gh/cb/CBRD-26847-oos-visible-version @ HEAD 6816023df.
Rows: F-201 .. F-218 (18 sites). All sites in F3.tsv.

## Anchor: the two consumption paths

- **Record-level Expand** (`HEAP_RECDES_CONSUME_RAW_BYTES`): `heap_get*`/`heap_next` set
  `context.recdes_consumption_policy`; when `== CONSUME_RAW_BYTES`, `expand_oos=true`
  (`heap_file.c:26218`) and `heap_record_replace_oos_oids` (`heap_oos.cpp:351`) rewrites the whole
  record, replacing every 16B OOS inline stub with its `oos_read` value. Early-returns when policy is
  `DONT_CONSUME_RAW_BYTES` (`heap_oos.cpp:362`).
- **Attribute-level Resolve** (correct for `DONT`): terminal reader is
  `heap_attrinfo_read_dbvalues` -> `heap_attrvalue_read` (`heap_file.c:10571`) ->
  `heap_attrvalue_point_variable` -> `heap_attrvalue_read_oos_inline` (`heap_file.c:10382`) ->
  `oos_read` (`heap_file.c:10419`). Resolves each OOS-backed variable attribute on demand; never needs
  the record-level Expand.

Decision rule applied: a `DONT` site is CORRECT iff the recdes is consumed only through the attribute
layer / fixed / header / existence, and never shipped raw, re-inserted, byte-compared, or OR_BUF-parsed
as a whole record. A `CONSUME` site is OVER_EXPAND iff the only consumer is the attribute layer.

## Search ledger

### SL-1 enumerate explicit policy call sites in scope
- 검색 목적: locate every HEAP_RECDES_* policy argument in query/ + optimizer/.
- 명령: `grep -rn "HEAP_RECDES_CONSUME_RAW_BYTES|HEAP_RECDES_DONT_CONSUME_RAW_BYTES|recdes_consumption_policy" src/query src/optimizer`
- raw candidate 수: 18 (matches team-lead's cited line set exactly).
- included: all 18. excluded: 0. duplicate: 0. pending: 0.

### SL-2 confirm attr-layer Resolve is the OOS-aware reader
- 검색 목적: prove heap_attrinfo_read_dbvalues reaches oos_read.
- 명령: grep heap_attrvalue_read_oos_inline / oos_read in heap_file.c; read heap_attrvalue_read body.
- result: confirmed chain heap_attrvalue_read -> point_variable -> read_oos_inline -> oos_read
  (heap_file.c:10382,10419). eval_data_filter uses heap_attrinfo_read_dbvalues (query_evaluator.c:2763).

### SL-3 serial re-serialize path (the flagged CONSUME sites)
- 검색 목적: determine whether serial_update_serial_object consumes old recdesc as raw bytes.
- 명령: read serial.c:910-1008 serial_update_serial_object; heap_file.c:12998 transform_to_disk_internal;
  heap_file.c:11902 heap_attrinfo_set_uninitialized.
- result: transform_to_disk reads any *unread* attr from old_recdes via `heap_attrvalue_read`
  (heap_file.c:11948) — the OOS-aware attr reader — NOT raw. New record is rebuilt from resolved
  attr_info DB_VALUEs and written by spage_update. `recdesc->type` read (serial.c:963) is header-only.
  => no raw variable-area consumption at 234/511/648.

### SL-4 enclosing-function resolution
- awk column-0 header scan per file; confirmed: scan_next_heap_scan (5863),
  scan_next_index_lookup_heap (6784); qexec_execute_update/delete/duplicate_key_update/obj_fetch/
  selupd_list; xserial_get_current_value_internal / serial_update_cur_val_of_serial /
  xserial_get_next_value_internal; find_row_by_gtrid_bqual / dblink_global_tran_scan_for_recovery;
  leaf_slot_walker::process_oid (387); xhistogram_build_multi_by_fullscan_reservoir (1792) /
  xstats_collect_ndv_by_fullscan_reservoir (2174).

## Verdict tally
- CORRECT: 15 (F-201..210, F-214..218) — all DONT sites; consumers are strictly attr-layer / MVCC
  reeval / header-only.
- OVER_EXPAND: 3 (F-211, F-212, F-213) — serial.c CONSUME_RAW_BYTES sites. Findings FIND-F3-01/02/03.
- BUG / CONTRACT_GAP / FOLLOWUP: 0.

## Suspected findings (for team-lead / fix phase)
- **FIND-F3-01/02/03 (serial.c:234, 511, 648)**: db_serial fetches use CONSUME_RAW_BYTES (record-level
  Expand) but consume the record purely through the attribute layer (heap_attrinfo_read_dbvalues, and
  for the update paths heap_attrinfo_transform_to_disk whose residual reads go through the OOS-aware
  heap_attrvalue_read). No raw-byte / re-insert / OR_BUF path. Expand is wasted work; DONT is correct
  and faster. Additionally db_serial records are far below the 4,060B OOS trigger, so has_oos is
  effectively never set — the Expand is a no-op in practice today, but the *policy* is still wrong per
  the audit contract (judged by consumer, not by "no OOS attrs"). These are exactly the 3 sites the
  weekly-meeting note flagged. Recommend revert to HEAP_RECDES_DONT_CONSUME_RAW_BYTES.
  - Risk note: the update paths write via spage_update on the peeked serial page; behavior is unchanged
    by the policy flip because the write is built from resolved attr_info DB_VALUEs, not from recdesc.

## Newly discovered symbols / aliases / callbacks (for the reverse audit)
- `heap_attrinfo_transform_to_disk` / `heap_attrinfo_transform_to_disk_internal` (heap_file.c:12514/
  12998): re-serializes a record from attr_info; **not** a raw-byte consumer — its old_recdes reads go
  through `heap_attrinfo_set_uninitialized` -> `heap_attrvalue_read` (OOS-aware). Reverse audit can
  treat any `transform_to_disk(old_recdes=...)` caller as attr-layer, NOT raw.
- `heap_attrinfo_set_uninitialized` (heap_file.c:11902): reads residual/unset attrs from a recdes via
  the OOS-aware attr reader; also re-reads BLOB/CLOB for old-value delete.
- `heap_attrinfo_read_dbvalues_with_oos_prefetch` / `_from_prefetched_oos` /
  `heap_oos_read_grouped_payloads` (heap_file.c:10688/10656/10702): grouped OOS Resolve fast path used
  when >=2 OOS attrs requested; still attr-layer, still oos_read-backed. Relevant if reverse audit sees
  these symbols.
- `eval_data_filter` (query_evaluator.c:2741): predicate-filter wrapper; reads pred attrs via
  heap_attrinfo_read_dbvalues (line 2763). Any scan feeding a recdes here is attr-layer RESOLVE.
- `serial_update_serial_object` (serial.c:920): serial-specific in-place update; builds new recdes with
  transform_to_disk + spage_update + log_append_redo_recdes. The `new_recdesc` it writes is a freshly
  serialized record (would itself run OOS demotion via determine_disk_layout) — NOT the raw fetched
  recdes. Not an OOS raw-byte re-insert of the fetched image.
- `or_set_rep_id` (used at query_executor.c:12325): rewrites rep-id header bits only; not variable-area
  / OOS consumption.
- `locator_lock_and_get_object_with_evaluation`: when called with recdes=NULL (query_executor.c:14556)
  it returns no body to the caller; policy governs only the internal reeval fetch (attr-layer).

## Ambiguities / no TBD
- No undecidable rows. All 18 terminal consumers reach a concrete attr-layer reader or header/no-body
  consumption. oos_capable is annotated per class; for system-catalog classes (db_serial,
  CT_GLOBAL_TRAN) marked no/unlikely by record-size contract, but verdicts are driven by the consumer
  path, not by oos_capable.
- Byte-range convention: "variable" = attr-layer per-column resolve of the variable area (no raw
  whole-record byte consumption); "none" = recdes not returned to caller (F-210).
