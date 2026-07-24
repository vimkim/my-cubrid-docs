# F1 forward-audit notes — src/storage/heap_file.c (+ heap_file.h, heap_oos.cpp)

Repo: /home/vimkim/gh/cb/CBRD-26847-oos-visible-version @ HEAD 6816023df (read-only)
Range: F-001 .. F-043 (43 rows). Direction: forward.

## Terminology / plumbing correction (IMPORTANT for other fragments)

- The prompt referred to `HEAP_GET_CONTEXT.expand_oos`. There is **no such struct field**.
  The struct field is `HEAP_GET_CONTEXT.recdes_consumption_policy`
  (`HEAP_RECDES_CONSUMPTION_POLICY`, heap_file.h:397). `expand_oos` exists only as a
  local bool alias inside `heap_scan_get_visible_version_impl`
  (`const bool expand_oos = recdes_consumption_policy == HEAP_RECDES_CONSUME_RAW_BYTES;`, heap_file.c:26218).
- Policy sink: `heap_record_replace_oos_oids` (heap_oos.cpp:351). It early-returns
  S_SUCCESS when policy==DONT_CONSUME (heap_oos.cpp:362) and also short-circuits when
  `!heap_recdes_contains_oos(rec)` (377). CONSUME_RAW_BYTES -> full record rebuild via
  heap_oos_parse_vot/read_values/compute_layout/build_record.

## Policy flow verification (section A) — PLUMBING IS CORRECT

All three visible-version families funnel into one policy sink:

    heap_get_visible_version(param) ----\
    heap_scan_get_visible_version(param) >-- heap_init_get_context sets
    heap_next/heap_prev(param) ---------/    context->recdes_consumption_policy
        -> heap_next_internal -> heap_scan_get_visible_version_impl
        -> heap_get_visible_version_internal
             |-> heap_get_record_data_when_all_ready -> heap_record_replace_oos_oids (honors policy)
             \-> heap_get_visible_version_from_log  -> heap_record_replace_oos_oids (honors policy, 26444)
    heap_get_last_version -> heap_get_record_data_when_all_ready -> replace_oos_oids (26638)

- CONSUME_RAW_BYTES maps to expansion; DONT_CONSUME preserves stored form. Confirmed both
  the current-version path (7460 REC_RELOCATION, 7482 REC_HOME) and the prev-version/undo-log
  path (26444) call the sink.
- REC_BIGONE path (heap_get_bigone_content, 7463/20172) does NOT expand — correct, because
  OOS+bigone is rejected at write time (ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE, CBRD-26937), so a
  REC_BIGONE never carries OOS inline stubs (F-043 EXCLUDED).
- Fast-path shortcut in heap_scan_get_visible_version_impl (26237-26243) correctly refuses to
  return peeked bytes as-is when `expand_oos && heap_recdes_contains_oos(peeked_recdes)`.
- get_rec_info branch of heap_next_internal ignores policy and calls heap_get_record_info,
  which reads only header/CHN/repid/MVCC (heap_file.c:19881-19893) — never the variable area.

## Search ledger

### 검색 1 — explicit policy tokens in heap_file.c
- 목적: enumerate every policy call site / constant usage inside the file
- 명령: `grep -n "heap_record_replace_oos_oids\|recdes_consumption_policy\|HEAP_RECDES_CONSUME_RAW_BYTES\|HEAP_RECDES_DONT_CONSUME_RAW_BYTES\|expand_oos" heap_file.c`
- raw candidates: 34 line hits
- included: all mapped to F-rows (plumbing F-001..F-011; fixed sites F-012..F-025; bigone F-043)
- excluded: none
- duplicate: multiple hits per function collapsed into one row per branch/terminal
- pending: none

### 검색 2 — external callers of every fixed-policy wrapper
- 목적: section C caller enumeration
- 명령: `rg -n "\bheap_first\b|\bheap_last\b|\bheap_next_1page\b|\bheap_scanrange_to_following\b|\bheap_scanrange_to_prior\b|\bheap_scanrange_next\b|\bheap_next_record_info\b|\bheap_prev_record_info\b|\bheap_get_class_record\b" -g '*.c' -g '*.cpp' -g '*.h'` (excluding heap_file.* and extern decls)
- raw candidates: heap_first 4, heap_last 0 external, heap_next_1page 4, scanrange_to_following 1, scanrange_to_prior 1, scanrange_next 1, next_record_info 1, prev_record_info 1, heap_get_class_record ~22
- included: all heap_first / heap_next_1page / scanrange / record_info callers traced individually (F-026..F-038); heap_get_class_record traced representatively (F-039..F-042) + full list captured
- excluded: heap_scanrange_prev / heap_scanrange_first / heap_scanrange_last / heap_cmp — under `#if defined(ENABLE_UNUSED_FUNCTION)` (dead)
- pending: heap_get_class_record raw-consumer confirmation -> reverse audit

### 검색 3 — class/catalog OOS exclusion in demotion gate
- 목적: decide oos_capable for class-object records (heap_get_class_record)
- 명령: read heap_attrinfo_determine_disk_layout (heap_file.c:12095-12164)
- result: NO class/root/system/catalog exclusion. Gate is purely size-based
  (`header_size+payload_size+mvcc_extra > DB_PAGESIZE/4`, still literal DB_PAGESIZE/4 here —
  CBRD-27057 four-record target NOT yet applied in this working tree; out of scope for this
  audit but noted) + eligibility `!is_fixed && column_size > OR_OOS_INLINE_SIZE`. Therefore
  class objects are OOS-capable by contract.

## Findings

- **FIND-01 (OVER_EXPAND, reachable)** — heap_scanrange_next first-object fetch uses
  CONSUME_RAW_BYTES (heap_file.c:8579), but the returned recdes is consumed by the attribute
  layer (scan_manager.c:5916 -> eval_data_filter 5971). The sibling fetches in the same function
  (heap_next at 8584/8605) correctly use DONT_CONSUME. Result: an unnecessary full-record Expand
  on the first object of every grouped heap-scan block. Functionally correct, wasteful. Fix:
  change 8579 to HEAP_RECDES_DONT_CONSUME_RAW_BYTES. Rows F-024, F-036.

- **FIND-02 (OVER_EXPAND, unreachable/dead)** — heap_scanrange_to_following (8370) and
  heap_scanrange_to_prior (8481) use CONSUME_RAW_BYTES on a local RECDES that is only used for
  the scan code and then discarded. Both branches require a non-NULL start_oid/last_oid, but the
  sole callers (scan_manager.c:5053 / 5057) always pass NULL, so the branches are unreachable.
  Fix (cleanup): DONT_CONSUME (or note as dead). Rows F-020, F-022, F-034, F-035.

- **FIND-03 (CONTRACT_GAP / FOLLOWUP)** — heap_get_class_record hardcodes DONT_CONSUME
  (heap_file.c:26850) but several callers parse the returned class-object record as raw bytes via
  or_get_classrep (object_representation_sr.c:949, btree.c:21593) and catalog construction
  (catalog_class.c:4800/4927/5376/5613). Since heap_attrinfo_determine_disk_layout applies no
  class-level OOS exclusion, a sufficiently large class object could be OOS-backed and would then
  be misparsed. Not proven reachable (requires a class object > OOS target with a >16B variable
  value). Hand to reverse audit to confirm whether root/class objects ever reach the OOS demotion
  path. Rows F-019, F-039..F-042.

## New symbols / aliases / consumers for the reverse audit

Raw-byte (or logical) RECDES consumers reached from heap_file.c wrappers — these are the
reverse-audit entry points:

- `or_get_classrep(recdes, ...)` — raw OR parse of a class object (object_representation_sr.c:953,
  btree.c near 21593). Fed by heap_get_class_record (DONT_CONSUME).
- `eval_data_filter` / `heap_attrinfo_read_dbvalues` — attribute-layer Resolve (NOT raw). Safe.
- `heap_get_record_info` — header/CHN/repid/MVCC only via or_rep_id/or_chn/or_mvcc_get_header
  (heap_file.c:19881-19893, 19935-19948). Does not touch variable area.
- tde_get_keyinfo raw memcpy of record body (tde.c:600) — non-OOS-capable heap (no class repr).
- boot_get_db_parm raw struct copy (boot_sr.c:307-310) — non-OOS-capable heap.

heap_get_class_record full external caller list (for reverse-audit raw-consumer sweep):
object_representation_sr.c:949; catalog_class.c:4800,4927,5376,5613; btree.c:21593;
locator_sr.c:5577,10686,10707,10810,10990; query_executor.c:24581,25522; query_opfunc.c:8913;
system_catalog.c:1891,5765; serial.c:1223; sp_code.cpp:203; connection_support.cpp:2396;
file_manager.c:11293; boot_sr.c:3647; load_server_loader.cpp:390.

Public visible-version APIs whose external callers the reverse audit must enumerate
(these are PROPAGATE — the leak/over-expand risk lives at the CALLER's chosen policy):
- heap_get_visible_version (heap_file.c:26168)
- heap_scan_get_visible_version (26332)
- heap_next / heap_prev (20003 / 20053)
- heap_get_last_version (26596) — callers set context policy via heap_init_get_context

## Ambiguities / non-TBD caveats

- oos_capable="no" for tde keyinfo (F-026) and boot db parm (F-027): these heaps are started with
  NULL class_oid and their records are written as raw fixed structs (tde_insert_keyinfo /
  boot db parm), never through heap_attrinfo_transform_to_disk, so no VOT / no OOS demotion path.
  Raw consumption is therefore safe. This is a code-contract judgment, not a "no OOS today" excuse.
- DB_PAGESIZE/4 literal at heap_file.c:12117/12148 vs. the spec's heap_oos_inline_target_size()
  four-record target (CBRD-27057): the working tree has NOT yet adopted the physical target here.
  Noted only; it does not affect RECDES-consumption-policy correctness (this audit's subject).
