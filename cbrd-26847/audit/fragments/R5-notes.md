# R5 — Reverse audit: utility paths consuming heap instance record images

HEAD: 6816023df (read-only tree /home/vimkim/gh/cb/CBRD-26847-oos-visible-version)
Scope: unloaddb, compactdb (client + server), loaddb server loader, diagdb, checkdb, and the
terminal transformers (`desc_disk_to_obj`, `heap_attrinfo_read_dbvalues`). Rows R-401..R-412,
exclusions X-401..X-407.

## Headline: unloaddb status at this HEAD

**unloaddb receives EXPANDED records, not stubs, at HEAD 6816023df.** The CBRD-26948 regression
(census §3: "making Expand opt-in in PR #7093 left `xlocator_fetch_all` no longer expanding,
re-leaking OIDs to unloaddb/compactdb") is **NOT reproduced in the current code**.

- `xlocator_fetch_all` (locator_sr.c:2912-2913) calls `heap_next(... COPY, HEAP_RECDES_CONSUME_RAW_BYTES)`.
- `HEAP_RECDES_CONSUME_RAW_BYTES` → `expand_oos=true` (heap_file.c:26218) → `heap_record_replace_oos_oids`
  materializes every stub. The peeked-REC_HOME fast-path shortcut is explicitly disabled when it would
  skip expansion (heap_file.c:26240-26243, `shortcut_would_skip_oos_expansion`).
- Therefore the copyarea shipped to the CS-mode unloaddb client contains fully materialized records;
  `desc_disk_to_obj` (OOS-blind) sees real values, not 16B stubs.

Reconciliation note (per OOS-CONTEXT authority rule): the normative census dated 2026-07-13 lists
CBRD-26948 as OPEN and describes the leak as present. The checked-out source at 6816023df is evidence
that this exact revision **does** expand. Either the fix was applied after the census snapshot, or the
census tracks a window that this HEAD has moved past. Verdict recorded as CORRECT-at-HEAD with
finding F-R5-01 flagging the fragility (safety is entirely upstream; the terminal parser has no guard).

## Terminal parsers (byte ranges read)

- `desc_disk_to_obj` / `get_desc_current` / `get_desc_old` (src/loaddb/load_object.c): **OOS-blind**.
  Zero OOS references in the whole file (`rg -c OOS load_object.c` = 0). Reads the VOT via
  `or_get_offset_internal` and computes each variable size as `vars[i]=offset2-offset` (get_desc_current:596-627),
  then `att->type->data_readval` over the variable area. It does NOT test the IS_OOS VOT bit, so a stub
  would be read as a 16-byte attribute value → garbage. Used by unloaddb (R-401) and offline compactdb (R-403).
  Byte range: VOT offsets + variable area interpreted as values. Safety = upstream Expand only.
- `heap_attrinfo_read_dbvalues` (server, heap_file.c): **OOS-aware / Resolve**. The variable-read helper
  checks `OR_IS_OOS(offset)` (heap_file.c:10476) and dispatches to `heap_attrvalue_read_oos_inline` →
  `oos_read` (heap_file.c:10479). Used by compactdb_sr (R-405), diagdb value dump (R-409), checkdb key
  rebuild (R-411), loaddb loader (R-408). These resolve OOS per attribute regardless of fetch policy.

## compactdb reinsert semantics (team-lead question)

Server compactdb (`boot_compact_db`→`process_class`, compactdb_sr.c):
1. `xlocator_lock_and_fetch_all` (:395) → per-object `locator_get_object(... CONSUME)` (locator_sr.c:2340,
   a census 5-list genuine-expand site) → expanded copyarea.
2. `desc_disk_to_attr_info`→`heap_attrinfo_read_dbvalues` (:443) parses to attr_info (double-safe: expanded
   AND attr-layer Resolves).
3. `process_object` (:197) re-fetches the current physical image with `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`
   (:215-217) into `copy_recdes`, fixes dangling OID references (`process_value`), and only if something
   changed calls `locator_attribute_info_force(LC_FLUSH_UPDATE, ..., &copy_recdes)` (:261-265).

Who re-demotes on reinsert: the ordinary write path. `locator_attribute_info_force` →
`heap_attrinfo_transform_to_disk` → `heap_attrinfo_determine_disk_layout` re-runs largest-first demotion
on the (fully-valued) attr_info, allocating **fresh** OOS value chains (M1 always-new-OID). The old
physical image (`copy_recdes`, stubs preserved via DONT_CONSUME) is the correct undo reference and must
NOT be expanded — verified it is not. Old OOS chains of the superseded version are **not** leaked: this is
a standard MVCC UPDATE, so vacuum reclaims the old chains when it reclaims the old heap-record version
(invariant 3, vacuum_forward_walk_oos_delete_atomic). compactdb does no bespoke OOS chain handling.

## OVER_EXPAND (redundant CONSUME) — finding F-R5-02

Three sites pass `HEAP_RECDES_CONSUME_RAW_BYTES` where it is unnecessary. All SAFE (correctness intact),
flagged for the forward audit / cleanup census:
- compactdb.c:564-566 (R-404): `heap_get_visible_version(..., recdes=NULL, ..., CONSUME)` — pure OID
  existence probe, recdes never consumed. DONT_CONSUME suffices.
- compactdb_sr.c:108-110 (R-407): same shape, referenced-OID existence/class probe, recdes NULL.
- load_server_loader.cpp:246-247 (R-408): CONSUME then `heap_attrinfo_read_dbvalues` (which Resolves
  per-attribute), so the expand is redundant; db_user rows are tiny/never OOS in practice.

These mirror the census claim that ~17 of ~22 `_expand_oos`-style sites were mechanically migrated and
should revert to the cheap fetch. Not bugs; perf/clarity only.

---

## Search ledger

### Block 1 — locate utility source files
- 검색 목적: enumerate utilities that consume heap instance record images
- 명령: `ls src/executables`, `rg -l 'RECDES|recdes' src/executables`, `find load_object/unload_object`
- raw candidate 수: executables using RECDES = 2 (compactdb.c, unload_object.c); utilities present:
  unloaddb, compactdb(+cl/sr/common), loaddb, diagdb, checkdb, spacedb, backupdb, restoredb, migrate, checksumdb
- included: unload_object.c, compactdb.c, compactdb_sr.c, load_object.c, load_server_loader.cpp
- excluded: unload_schema.c (schema), migrate.c, checksumdb.c (SQL), backup/restore/spacedb (physical)
- duplicate: compactdb.c~ (backup file, ignore per AGENTS)
- pending: none

### Block 2 — unloaddb fetch→parse chain
- 검색 목적: trace request→server fetch policy→copyarea→client parse
- 명령: `rg -n 'locator_fetch_all|desc_disk_to_obj|LC_RECDES' unload_object.c`; read unload_fetcher/unload_printer
- raw candidate 수: 1 chain (unload_fetcher:1538 → unload_printer:1385 → desc_disk_to_obj:1387)
- included: R-401, R-402
- pending: none

### Block 3 — xlocator_fetch_all current policy at HEAD
- 검색 목적: verify heap_next policy inside xlocator_fetch_all (CBRD-26948 claim)
- 명령: read locator_sr.c:2766-2945; read heap_file.c:26210-26329 (expand_oos wiring), heap_oos.cpp:351-362
- raw candidate 수: 1 (heap_next call at :2912)
- 결과: HEAP_RECDES_CONSUME_RAW_BYTES present → expands. CBRD-26948 NOT reproduced.
- included: folded into R-401 evidence + F-R5-01
- pending: none

### Block 4 — compactdb client + server
- 검색 목적: record parsing/moving semantics, reinsert, old-chain fate
- 명령: read compactdb.c:356-603, compactdb_sr.c:70-497; xlocator_lock_and_fetch_all expand at locator_sr.c:2336-2341
- raw candidate 수: 5 policy sites (compactdb.c:429,565; compactdb_sr.c:110,217,395)
- included: R-403,R-404,R-405,R-406,R-407
- pending: none

### Block 5 — loaddb server loader consumer
- 검색 목적: what parses the CONSUME fetch at load_server_loader.cpp:247
- 명령: read load_server_loader.cpp:235-274
- raw candidate 수: 1 (heap_get_visible_version:246 → heap_attrinfo_read_dbvalues:260)
- included: R-408 (OVER_EXPAND, consumer OOS-aware)
- pending: none

### Block 6 — diagdb / checkdb sweep
- 검색 목적: diagdb record dump + checkdb consistency record parsing
- 명령: `rg heap_dump/heap_check heap_file.c`; read heap_dump:15489-15647; read locator_check_class:10538-10651;
  awk locator_check_btree_entries:9613-9640; heap_chkreloc_next structural check
- raw candidate 수: diagdb 2 (spage_dump raw hex; heap_attrinfo value dump), checkdb 2 (key rebuild; structural)
- included: R-409,R-410,R-411,R-412
- excluded: checksumdb (SQL) X-401
- pending: none

### Block 7 — remaining utility exclusions
- 검색 목적: confirm backup/restore/spacedb/migrate/vacuumdb/unload_schema carry no raw instance-record parse
- 명령: `rg heap_next|heap_attrinfo|desc_disk_to_obj|or_get` on those files/paths (all 0 for instance parse)
- included exclusions: X-402..X-407
- pending: none

## New symbols discovered
- `HEAP_RECDES_CONSUMPTION_POLICY` enum (heap_file.h:363-372): CONSUME_RAW_BYTES vs DONT_CONSUME_RAW_BYTES;
  `HEAP_IS_VALID_RECDES_CONSUMPTION_POLICY` macro.
- `heap_scan_get_visible_version_impl` (heap_file.c:26210): peeked-record shortcut with
  `shortcut_would_skip_oos_expansion` guard (:26240-26243).
- `heap_record_replace_oos_oids` early-return for DONT_CONSUME (heap_oos.cpp:351-362).
- `heap_attrvalue_read_oos_inline` (heap_file.c:10382) — the Resolve dispatch at :10476-10479 keyed on
  `OR_IS_OOS(offset)`.
- `desc_disk_to_attr_info` (compactdb_sr.c:301) — thin wrapper over `heap_attrinfo_read_dbvalues`.
- `xlocator_lock_and_fetch_all` per-object expand at locator_sr.c:2336-2341 (`locator_get_object` CONSUME).

## Ambiguities / caveats
- R-412 (checkdb structural pass): `heap_chkreloc_next` confirmed to read `spage_get_record_type` only,
  not attribute values; classified PRESERVE_PHYSICAL with confidence, but I did not exhaustively read every
  branch of heap_check_all_pages — the relocation/structural nature is well-established by function purpose.
- F-R5-01 status ambiguity is a source-vs-census disagreement, resolved in favor of source-at-HEAD per the
  OOS-CONTEXT authority rule (source is evidence of the revision; JIRA/census are dated observations).
- The three OVER_EXPAND sites (F-R5-02) overlap the forward audit's policy-site census; recorded here from
  the consumer side and cross-linked, not claimed as this reverse audit's exclusive finding.
