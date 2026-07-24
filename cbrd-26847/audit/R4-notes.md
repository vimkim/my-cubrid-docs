# CBRD-26847 Reverse Audit R4 — copyarea / network / client-parse / heap-reinsert

Agent: rev-copyarea
Source anchor (HEAD): 6816023df4ed910687523ab4d34bf667ab32b9cd
Branch: CBRD-26847-oos-visible-version
Repo (read-only): /home/vimkim/gh/cb/CBRD-26847-oos-visible-version
Rows: R-301..R-314 (14 included), X-301..X-313 (13 exclusions). Total 27.

## Verdict tally

- CORRECT: R-301, R-302, R-303, R-304, R-305, R-306, R-307, R-308, R-309, R-310, R-311, R-312, R-313 (13)
- OVER_EXPAND: R-314 (1)
- EXCLUDED: X-301..X-313 (13)
- BUG: 0 ; CONTRACT_GAP: 0 ; FOLLOWUP: 0 (findings recorded, none are unresolved raw-stub-leak bugs at this HEAD)

## Search ledger

### Block 1 — LC_COPYAREA instance-record pack sites (server->client)
검색 목적: 모든 heap instance RECDES가 copy area로 packing되어 client로 shipping되는 지점
source anchor: 6816023df
명령: rg 'HEAP_RECDES_CONSUME_RAW_BYTES|DONT_CONSUME|expand_oos' src/transaction/locator_sr.c ; awk enclosing-function map for all 26 policy lines ; rg 'LC_RECDES_IN_COPYAREA|obj->length = recdes|LC_COPYAREA_ONEOBJ'
raw candidate 수: 3 primary pack helpers (locator_return_object_assign / xlocator_fetch_all / xlocator_lock_and_fetch_all)
included: R-301 (locator_lock_and_return_object central helper; feeds xlocator_fetch/lockset/lockhint), R-302 (xlocator_fetch_all), R-303 (xlocator_lock_and_fetch_all), R-304 (CHN-uptodate no-body branch)
excluded: X-301 (net transport opaque), X-308 (fk_validity DONT_CONSUME attr-resolve)
duplicate: 0
pending: 0
새 symbol: locator_return_object_assign, LC_RECDES_IN_COPYAREA, LC_NEXT_ONEOBJ_PTR_IN_COPYAREA, locator_notify_decache

### Block 2 — client-side terminal parsers
검색 목적: client가 copyarea instance record byte를 parse하는 최종 소비자
명령: rg 'tf_disk_to_mem|LC_RECDES_TO_GET_ONEOBJ|ws_cache' src/transaction/locator_cl.c ; rg 'desc_disk_to_obj' src/loaddb src/executables
raw candidate 수: 2 terminal parsers (tf_disk_to_mem client, desc_disk_to_obj unloaddb/loaddb)
included: R-305 (tf_disk_to_mem), R-306 (desc_disk_to_obj via unload_printer)
excluded: X-309 (locator_cl.c mflush = client producer, logical images), X-310 (method/SP DB_VALUEs), X-311 (QFILE query results)
duplicate: 0 ; pending: 0
새 symbol: tf_disk_to_mem, desc_disk_to_obj, unload_printer, LC_RECDES_TO_GET_ONEOBJ

### Block 3 — heap re-insert provenance
검색 목적: 다른 heap record에서 온 RECDES를 heap에 다시 쓰는 경로와 그 provenance/re-demotion
명령: rg 'heap_insert_logical|heap_update_logical|locator_insert_force|locator_update_force' ; rg 'heap_attrinfo_transform_to_disk' src ; catalog_class.c/compactdb.c/load_server_loader.cpp function maps
raw candidate 수: 7 (redistribute_partition_data, repl-apply, LC_FLUSH_INSERT_OOS, client DML insert, loaddb loader, catcls_*, compactdb)
included: R-307, R-308, R-309, R-310, R-311, R-312, R-313
excluded: X-302 (sp_code attr-read), X-304 (delete_lob attr), X-306 (compactdb existence NULL recdes), X-307 (update_force old-record), X-312 (dblink DONT_CONSUME), X-313 (loaddb read fetch)
duplicate: 0 ; pending: 0
새 symbol: locator_fixup_oos_oids_in_recdes, locator_oos_insert_force, heap_recdes_contains_oos, LC_FLUSH_INSERT_OOS, desc_obj_to_disk, heap_create_insert_context, heap_create_update_context

### Block 4 — other server->outside channels (method/sp/dblink/repl-log)
검색 목적: heap instance record byte를 외부로 내보내는 나머지 경로
명령: rg 'RECDES' src/method src/sp ; rg 'CONSUME_RAW_BYTES|heap_record_replace_oos_oids' src excluding known files ; repl_log_insert around heap_recdes_contains_oos
raw candidate 수: 5 (sp_code, repl-log source-side, method, dblink, query/scan)
included: 0 new (all reinsert/ship covered above); R-314 (repl_prepare over-expand) recorded under network
excluded: X-302, X-305, X-310, X-311, X-312
duplicate: 0 ; pending: 0
새 symbol: repl_log_insert, RVREPL_OOS_INSERT, RVREPL_DUMMY_OOS_RECORD, or_chn

## New symbols / aliases discovered (fed back into seed)
locator_return_object_assign, locator_lock_and_return_object, locator_get_object, locator_lock_and_get_object_internal, locator_fixup_oos_oids_in_recdes, locator_oos_insert_force, heap_recdes_contains_oos, tf_disk_to_mem, desc_disk_to_obj, desc_obj_to_disk, heap_create_insert_context/heap_create_update_context, LC_FLUSH_INSERT_OOS, LC_RECDES_IN_COPYAREA, LC_RECDES_TO_GET_ONEOBJ.

## Findings

- F26847-R4-01 (OVER_EXPAND, P2) — locator_repl_prepare_force (locator_sr.c:6943-6960) fetches the old record with HEAP_RECDES_CONSUME_RAW_BYTES but consumes only or_chn(old_recdes) (header/CHN). Full record expansion (including oos_read of every OOS chain) is wasted. Should be HEAP_RECDES_DONT_CONSUME_RAW_BYTES. Safe today (correct value, just extra OOS I/O). Row R-314.

- F26847-R4-02 (behavior note, P3/followup) — Raw-recdes reinsert paths do NOT re-demote to OOS: redistribute_partition_data (R-307), catcls_* (R-312), compactdb disk_update_instance (R-313). OOS demotion lives only in heap_attrinfo_transform_to_disk[_internal] (heap_file.c:12095 heap_attrinfo_determine_disk_layout), invoked on the attrinfo build path. locator_insert_force / heap_update_logical store the given recdes verbatim (locator_sr.c:5060-5079, no attrinfo transform). Consequence: an expanded (stub-free) record reinserted raw is stored as a large inline REC_HOME or, if > heap_Maxslotted_reclength (~16KB), as a NON-OOS REC_BIGONE overflow record. This is data-safe (no stub leak, no OOS-chain aliasing — expand cleared HAS_OOS at heap_oos.cpp:282 and rewrote the VOT without IS_OOS bits) and does NOT fail/corrupt (REC_BIGONE chains arbitrary length). It only loses the OOS storage benefit and can bloat the target heap. NOT a correctness bug for CBRD-26847. Correction to prior context wording ("re-inserted expanded images re-demote"): they do NOT re-demote on the raw path; they rely on REC_BIGONE/large-inline.

- F26847-R4-03 (OVER_EXPAND, P2, fwd-misc lane) — sp_get_code_attr (sp_code.cpp:90-91) fetches CONSUME then reads via heap_attrinfo_read_dbvalues (attribute layer). CONSUME is redundant; DONT_CONSUME would resolve only the requested attribute. Recorded X-302, deferred to forward agents.

## Required explicit answers

### (a) ALL server->client heap-instance-record channels and expansion guarantee

| Channel | Server fetch + policy | Expansion guaranteed? |
|---|---|---|
| xlocator_fetch / xlocator_fetch_lockset / xlocator_fetch_lockhint_classes (single/multi object) | locator_lock_and_return_object -> locator_get_object CONSUME (locator_sr.c:2340) | YES (R-301) |
| xlocator_fetch_all (LC_FETCH_ALL, unloaddb/compactdb) | heap_next CONSUME (locator_sr.c:2912) | YES (R-302) |
| xlocator_lock_and_fetch_all (locked scan) | heap_get_visible_version CONSUME (:12150) / heap_next CONSUME (:12166) | YES (R-303) |
| CHN-uptodate reply | no body shipped (LC_FETCH_VERIFY_CHN) | N/A — no record bytes (R-304) |
| Query results | attribute-layer scan -> DB_VALUE -> QFILE tuples | N/A — not raw heap records (X-311) |
| Method / SP | DB_VALUE marshaling | N/A — not raw heap records (X-310) |
| Network transport | opaque LC_COPYAREA byte stream | N/A — expansion decided upstream (X-301) |

Terminal client parsers (tf_disk_to_mem, desc_disk_to_obj) are OOS-blind by design; correctness relies entirely on the server expanding, which all three raw-shipping channels do at this HEAD. No unexpanded server->client instance-record channel found.

### (b) Status of xlocator_fetch_all at this HEAD (CBRD-26948)

FIXED / not-present at 6816023df. xlocator_fetch_all passes HEAP_RECDES_CONSUME_RAW_BYTES to heap_next (locator_sr.c:2912-2913), so it DOES expand OOS stubs before packing into the copyarea consumed by unloaddb/compactdb (desc_disk_to_obj, OOS-blind). The task premise citing "locator_sr.c:11969 heap_next(...DONT_CONSUME...)" as xlocator_fetch_all is inaccurate at this HEAD: line 11969 is xlocator_check_fk_validity (an attribute-layer FK scan that correctly uses DONT_CONSUME, X-308), a different function. The CBRD-26948 stub-leak regression is therefore not reproducible on this branch/HEAD. (Recommend a regression test asserting fetch_all/unloaddb of OOS-backed rows yields logical values — R-302/R-306 test column.)

### (c) Raw-reinsert paths and who re-demotes

| Path | Provenance of reinserted recdes | Re-demotes? | Row |
|---|---|---|---|
| Client DML INSERT (locator_attribute_info_force) | heap_attrinfo_transform_to_disk (write-time demotion) | YES (self, via attrinfo build) | R-310 |
| loaddb server loader | heap_attrinfo_transform_to_disk_except_lob | YES (self) | R-311 |
| Replication apply RBR (locator_force) | client copyarea WITH stubs, fixup remaps OOS OIDs | N/A — preserves physical stubs (already demoted on master) | R-308 |
| LC_FLUSH_INSERT_OOS | replicated OOS chunk (OOS_RECDES) | N/A — OOS chunk insert | R-309 |
| redistribute_partition_data | heap_get_visible_version CONSUME (expanded, stub-free) -> locator_insert_force raw | NO — stored large-inline / non-OOS REC_BIGONE | R-307 |
| catcls_update_instance / catcls_delete_instance / catcls_update_class_stats | heap_get_visible_version CONSUME (expanded) -> heap_update_logical raw | NO — same as above | R-312 |
| compactdb disk_update_instance | desc_obj_to_disk from logical DESC_OBJ -> heap_update_logical raw | NO (utility transform, no OOS demotion) | R-313 |

Summary: only the attrinfo-build paths (client DML, loaddb) re-demote. The three CONSUME-expand-then-raw-reinsert paths (partition redistribute, catalog maintenance, compactdb) do NOT re-demote; they are data-safe (no stub leak / no chain aliasing) but forfeit OOS backing on the rewritten record, which can become a non-OOS REC_BIGONE. No path fails or corrupts. See F26847-R4-02.

## Cross-links to other agents
- rev-repl: R-308, R-309 (RBR OOS apply), source-side repl_log_insert keyed on OOS OIDs (locator_sr.c:8150-8168).
- fwd-locator: R-310, R-312, X-303, X-304, X-307 (locator_update_force old-record CONSUME sites 5799/5942).
- fwd-query: X-305, X-311, X-312.
- fwd-misc: R-311, R-313, X-302 (sp_code), X-313 (loaddb read).

## Not verified dynamically
Read-only static audit only (no build/run per task constraint). Dynamic scenarios noted in the `test` column of R-301/302/303/306/307/308/311/312/313/314 are recommendations for the verification phase.
