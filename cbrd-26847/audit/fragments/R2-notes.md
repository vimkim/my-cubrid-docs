# R2 — Reverse audit: CDC & Flashback (CBRD-26847 OOS raw-RECDES consumption)

Scope: CDC (Change Data Capture) and flashback reconstruct heap record images from WAL
undo/redo and interpret them as logical rows. Read-only tree HEAD 6816023df.
Fragment: `fragments/R2.tsv` (rows R-101..R-110, X-101..X-107).

## Bottom line

- **CDC resolves OOS-backed attributes correctly today.** `cdc_make_dml_loginfo` reads
  every column value through `heap_attrinfo_read_dbvalues`, which routes into the
  attribute-layer OOS Resolve (`heap_attrvalue_point_variable` → `OR_IS_OOS` →
  `heap_attrvalue_read_oos_inline` → `oos_read`). No raw `or_*` value parsing of the
  variable area, no raw recdes bytes shipped outward. The loginfo shipped to clients is
  packed DB_VALUEs (`cdc_put_value_to_loginfo`), produced *after* Resolve.
- **Flashback resolves OOS-backed attributes correctly today too.** `flashback_make_loginfo`
  uses the identical `cdc_get_recdes` + `cdc_make_dml_loginfo(is_flashback=true)` path and
  ships packed DB_VALUE loginfo via `flashback_pack_loginfo`; it never sends raw recdes.
- **The OOS-CONTEXT "missing feature" note ("CDC flashback needs to replace OOS inline
  stubs with actual values in recdes") is STALE as a description of record-level Expand.**
  CDC/flashback never needed record-level Expand: they consume per-attribute DB_VALUEs, and
  the attribute layer Resolves each OOS-backed column. The stub-in-recdes replacement the
  note asks for is unnecessary for this consumer class.
- **The real residual gap is lifetime, not parsing (R-110, FOLLOWUP).** CDC/flashback
  Resolve *old-version* OOS-backed attributes by following the undo image's head OOS OID
  into an OOS value chain. Those old chains are reclaimed by vacuum when the old heap-record
  version is reclaimed (invariants 2/3). Flashback in particular reads historical log
  ranges, so the old chains are very likely already vacuumed → `oos_read` fails
  (`ER_HEAP_OOS_CORRUPTED_RECORD`) or, under the CBRD-26950 slot-reuse bug, silently reads a
  *different* live row's value. There is no retention/pin protecting these chains for
  CDC/flashback. Classified CONTRACT_GAP/FOLLOWUP, not BUG, because it is not a raw-stub
  leak and the raw-consumption contract (this audit's subject) is satisfied.

## Key mechanism verified

- `oos_read(THREAD_ENTRY*, const OID &oid, oos_buffer dest)` (`oos_file.cpp:1684`) needs
  ONLY `thread_p` + the **head OOS OID**. The head OOS OID is a physical OID
  (volid+pageid+slotid) that self-locates the chunk record; `oos_read` fixes the OOS page by
  VPID directly. It does **NOT** need the class hfid or the OOS file VFID. → The task's
  "thread/context mismatch would break Resolve" concern is **unfounded**: any server thread
  with a valid `thread_p` (CDC producer thread, flashback via network_interface_sr) can
  Resolve, regardless of class-context wiring. `heap_attrvalue_read_oos_inline`
  (`heap_file.c:10382`) obtains the head OID + full length purely from the inline stub in the
  recdes (`heap_oos_parse_inline_ref`), never from a class file handle.
- Per-attribute Resolve is driven by the **VOT IS_OOS bit** (`OR_IS_OOS(offset)` in
  `heap_attrvalue_point_variable`, `heap_file.c:10476`), which is independent of the MVCC
  header HAS_OOS flag. `heap_attrinfo_read_dbvalues_with_oos_prefetch` (`heap_file.c:10687`)
  uses HAS_OOS (`heap_recdes_contains_oos`) only to choose grouped vs individual prefetch;
  the individual path still checks IS_OOS per attribute. So even if CDC's redo
  reconstruction dropped HAS_OOS, Resolve would still fire from the VOT.
- Reconstructed images are **stored-form**: undo via `log_get_undo_record`
  (`cdc_get_undo_record`), redo via verbatim body memcpy after OR-header rebuild
  (`log_manager.c:11745-11763`). OOS inline stubs and VOT IS_OOS bits are preserved
  (invariant 2), never expanded at reconstruction.

## Search ledger

### Block 1 — locate CDC/flashback files and entry points
- 검색 목적: find CDC producer + flashback source and the recdes/loginfo functions
- 명령: `rg -l 'cdc_'` / `rg -l 'flashback' -i` over src/; `grep -n 'cdc_get_recdes|cdc_make_dml_loginfo|log_append_supplement|LOG_SUPPLEMENT' src/transaction/log_manager.c`
- raw candidate 수: 2 producers (`cdc_get_recdes`, `flashback_make_loginfo`) + supplemental appenders
- included: log_manager.c (CDC core), flashback.c
- excluded: connection/communication/util_cs wiring (transport only, no recdes interpretation)
- duplicate: network_interface_sr/cl (transport of already-packed loginfo)
- pending: 0

### Block 2 — CDC DML value read path (does it Resolve OOS?)
- 검색 목적: confirm cdc_make_dml_loginfo reads values via OOS-aware attribute layer
- 명령: read `cdc_make_dml_loginfo` 12903-13372; `heap_attrinfo_read_dbvalues` 10908; dispatch 10687; `heap_attrvalue_point_variable` 10450; `heap_attrvalue_read_oos_inline` 10382
- raw candidate 수: 2 value-read sites (undo :13006, redo :13067) → R-103, R-104
- included: R-103, R-104
- excluded: X-102 (or_rep_id/or_chn header), X-103 (schema-change guard), X-106 (LOB from db_value), X-107 (error loginfo)
- duplicate: cdc_put_value_to_loginfo call sites (all consume resolved DB_VALUEs)
- pending: 0

### Block 3 — recdes reconstruction (stored-form?)
- 검색 목적: confirm undo/redo images are stored-form (stubs possible)
- 명령: read `cdc_get_recdes` 11380-11880; `cdc_get_undo_record` 11286; `log_get_undo_record`; overflow path 11522/11553
- raw candidate 수: undo image (R-101), redo image (R-102), overflow image (R-109)
- included: R-101, R-102, R-109
- excluded: —
- duplicate: RVHF_MVCC_INSERT vs RVHF_UPDATE redo builders (same stored-form outcome → single row R-102)
- pending: 0

### Block 4 — flashback path
- 검색 목적: confirm flashback materializes values and ships no raw recdes
- 명령: read flashback.c 406-1062; `flashback_pack_loginfo` 675; `flashback_make_loginfo` 767
- raw candidate 수: INSERT (R-105), UPDATE (R-106), DELETE (R-107) + client packing (X-104)
- included: R-105, R-106, R-107
- excluded: X-104 (packs post-resolve loginfo, not recdes)
- duplicate: flashback_get_summary supplement scan (uses cdc_get_undo_record for classoid filter only)
- pending: 0

### Block 5 — supplemental logging (what images get logged)
- 검색 목적: determine stored form vs logical of supplemental log images
- 명령: read `log_append_supplemental_info` 4857, `log_append_supplemental_lsa` 4912, `log_append_supplemental_undo_record` 4967
- raw candidate 수: LOG_SUPPLEMENT_UNDO_RECORD stored-form image (R-108); LSA-ref appenders (X-105); DDL (X-101)
- included: R-108
- excluded: X-101 (DDL text), X-105 (OID+LSA refs only)
- duplicate: —
- pending: 0

## New symbols / functions of record

- `cdc_get_recdes` (log_manager.c:11380) — reconstructs undo/redo stored-form images; shared by CDC and flashback (is_flashback flag).
- `cdc_get_undo_record` (:11286) → `log_get_undo_record` (:9801) — undo image reconstruction.
- `cdc_get_overflow_recdes` (fwd-decl :332) — overflow/REC_BIGONE image (OOS-free by CBRD-26937 rejection).
- `cdc_make_dml_loginfo` (:12903) — the logical consumer; `heap_attrinfo_read_dbvalues` at :13006/:13067.
- `cdc_put_value_to_loginfo` (:13736) — packs a resolved DB_VALUE (no recdes).
- `log_append_supplemental_undo_record` (:4967), `log_append_supplemental_lsa` (:4912), `log_append_supplemental_info` (:4857).
- `flashback_make_loginfo` (flashback.c:767), `flashback_pack_loginfo` (:675).
- `heap_attrinfo_read_dbvalues_with_oos_prefetch` (heap_file.c:10687), `heap_attrvalue_read_oos_inline` (:10382), `oos_read` (oos_file.cpp:1684).

## Ambiguities / uncertainties

- **R-110 severity.** I did not dynamically prove that vacuum reclaims a value chain before
  flashback reads it; it is an architectural inference from invariants 2/3 + CBRD-26950 +
  the standing "CDC flashback OOS-stub Resolve" note. It is real enough to flag as FOLLOWUP
  but needs a repro (flashback over a time range old enough for vacuum to have run on
  updated/deleted OOS-backed rows) to confirm the failure/wrong-data mode. This is a
  lifetime/retention gap, distinct from the raw-parse bug class this audit targets.
- **Error/schema branches (verified, no raw fallback):** on `partition_find_root_class_oid`
  failure, `heap_attrinfo_start` failure, or `cdc_check_if_schema_changed` true, the code
  emits a logical `cdc_make_error_loginfo` (CDC) or raises `ER_FLASHBACK_SCHEMA_CHANGED`
  (flashback) — never ships raw recdes bytes. Older representation is handled inside
  `heap_attrinfo_read_dbvalues` via `heap_attrinfo_recache(or_rep_id(recdes))`, and OOS
  Resolve still works because IS_OOS is per-record in the VOT.

## Verdict tally

- R-rows: 10 → CORRECT 6 (R-101,R-102,R-103,R-104,R-108,R-109), FOLLOWUP 4 (R-105,R-106,R-107,R-110)
- X-rows: 7 → all EXCLUDED
- pending: 0
