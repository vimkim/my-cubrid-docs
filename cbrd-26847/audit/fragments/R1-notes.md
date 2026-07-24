# R1 — Reverse audit notes (WAL / recovery / MVCC old-version / vacuum / rollback)

Agent: rev-wal | Tree: /home/vimkim/gh/cb/CBRD-26847-oos-visible-version | HEAD 6816023df (read-only)
Rows: R-001..R-025 (25 included reverse rows) + X-001..X-006 (6 excluded) = 31 rows in R1.tsv.
Verdict tally: CORRECT=25, EXCLUDED=6. No BUG / OVER_EXPAND / CONTRACT_GAP found in this area.

Legend for classification used here:
- PRESERVE_PHYSICAL = path treats the record as opaque physical bytes (recovery/rollback) OR deliberately
  interprets OOS stubs AS stubs on a stored-form image (vacuum/eager delete). Either way it depends on the
  STORED form (stubs intact) and never Expands.
- EXPAND = record-level Expand (heap_record_replace_oos_oids), opt-in via HEAP_GET_CONTEXT.expand_oos.

---

## Search ledger

### SL-1 — Locate OOS subsystem + Expand/Resolve entry points
- 검색 목적: find heap_record_replace_oos_oids / oos_read / vacuum_oos / heap_oos file locations and callers.
- 명령: `rg -n heap_record_replace_oos_oids src/`; `rg -n 'oos_read' src/`; `fd heap_oos|oos_file|vacuum_oos src/`.
- raw candidate 수: 3 callers of heap_record_replace_oos_oids (heap_file.c:7460,7482,26444).
- included: all 3 examined — 2 are current-version fetch (7460/7482, forward-audit territory, referenced as context), 1 is MVCC old-version (26444 → R-014).
- excluded: 0. duplicate: 0. pending: 0. (raw 3 = inc 3 + exc 0 + dup 0 + pending 0)

### SL-2 — WAL undo/redo image creation in heap ops
- 검색 목적: confirm the recdes logged as undo image is the stored on-page record, never an expanded fetch.
- 명령: `rg -n 'log_append_undo(redo)?_recdes|log_append_redo_recdes|log_append_undo_recdes2' src/storage/heap_file.c`;
  `rg -n 'RVHF_UPDATE_NOTIFY_VACUUM|RVHF_DELETE_NEWHOME_NOTIFY_VACUUM' src/storage/heap_file.c`.
- raw candidate 수: ~15 log_append_* sites in heap_file.c.
- included: update home/reloc/bigone (R-001..R-003), delete home/reloc/bigone (R-004..R-006), insert (R-007).
- excluded: RVHF_STATS/RVHF_CHAIN/RVHF_CREATE_HEADER/RVHF_REUSE_PAGE metadata (X-003),
  RVHF_MVCC_UPDATE_OVERFLOW ovf_recdes (X-004), REC_NEWHOME forwarding temp_recdes (X-006).
- duplicate: 0. pending: 0. (raw 15 = inc 7 + exc 8-ish metadata/forwarding folded into X-003/X-004/X-006)

### SL-3 — Provenance of the undo image (is it ever an expanded recdes?)
- 검색 목적: answer Q(a). Trace context->home_recdes / forward_recdes to their source read.
- 명령: `rg -n 'home_recdes' src/storage/heap_file.c | rg spage_get_record`; `rg -n 'expand_oos' src/storage/heap_file.c`.
- raw candidate 수: all home_recdes/forward_recdes reads are `spage_get_record(... PEEK|COPY)` from the live page
  (heap_file.c:22752, 22944, 23889, 22494, 22635, 23412…). `expand_oos` appears only at 26218/26241 — the
  visible-version FETCH path, on HEAP_GET_CONTEXT, never on the update/delete HEAP_OPERATION_CONTEXT.
- included: folded into R-001..R-006.  excluded: 0. duplicate: 0. pending: 0.

### SL-4 — Recovery redo/undo (heap_rv_*)
- 검색 목적: confirm recovery applies physical images and never interprets the variable area / OOS.
- 명령: `rg -n '^heap_rv_[a-z_]+ ?\(' src/storage/heap_file.c`; `rg -n 'oos' <recovery files>`.
- raw candidate 수: ~30 heap_rv_* functions; grep for `oos` in log_recovery.c/recovery.c/heap_rv → ZERO hits.
- included: update (R-008), delete undo/redo (R-009/R-010), insert redo/undo (R-011/R-012).
- excluded: 0 (all other heap_rv_* are metadata/page-hdr/reuse — same PRESERVE_PHYSICAL class, representative
  rows suffice). duplicate: 0. pending: 0.

### SL-5 — MVCC old-version read
- 검색 목적: answer Q(b). Does the prev_version_lsa → undo path honor CONSUME_RAW_BYTES?
- 명령: read heap_get_visible_version_internal (26374), heap_get_visible_version_from_log (26042),
  log_get_undo_record (log_manager.c:9801), heap_record_replace_oos_oids gate (heap_oos.cpp:351).
- raw candidate 수: 1 reconstruction path + 1 Expand gate.
- included: R-013 (reconstruction producer), R-014 (Expand gate), R-015 (log_get_undo_record terminal producer).
- excluded: 0. duplicate: 0. pending: 0.

### SL-6 — Vacuum OOS reclamation
- 검색 목적: classify every vacuum path that reads a heap/undo record to reclaim OOS.
- 명령: read vacuum_oos.cpp in full; `rg -n 'vacuum_forward_walk_reclaim_oos|vacuum_heap_oos_delete_within_sysop|vacuum_oos_find_vfid_for_heap_record' src/`;
  `rg -n 'heap_recdes_get_oos_oids' src/`.
- raw candidate 수: 3 public vacuum-OOS entry points + heap_recdes_get_oos_oids extractor.
- included: forward-walk delete atomic (R-016), forward-walk reclaim wrapper (R-017), within-sysop (R-018),
  vfid lookup (R-019), heap_recdes_get_oos_oids extractor (R-020).
- excluded: REC_BIGONE vacuum branch (X-005), btree branch (X-001), lob es_uri branch (X-002).
- duplicate: 0. pending: 0.

### SL-7 — SA_MODE eager delete + rollback
- 검색 목적: classify heap_oos_delete_unreferenced (eager) and transaction rollback.
- 명령: `rg -n 'heap_oos_delete_unreferenced' src/`; `rg -n 'oos_delete' src/`.
- raw candidate 수: 4 heap_oos_delete_unreferenced call sites.
- included: update home (R-021), update relocation (R-022), delete home (R-023), delete relocation (R-024),
  rollback via RV funcs (R-025).
- excluded: 0. duplicate: 0. pending: 0.

Global closure: every raw candidate found in SL-1..SL-7 is accounted for as an R-row, an X-row, or folded into
a representative row noted above. **Pending = 0.**

---

## Newly discovered symbols / aliases (relative to OOS-CONTEXT.md)

- `vacuum_forward_walk_reclaim_oos` (vacuum_oos.cpp:222) — the wrapper that reads the log-block undo image and
  guards on REC_HOME/REC_NEWHOME + heap_recdes_contains_oos before calling the delete-atomic helper. The context
  file names `vacuum_forward_walk_oos_delete_atomic` but not this wrapper; the wrapper is where the stored-form
  guard and the "stable_copy before page fix" hazard mitigation live.
- `vacuum_oos_vfid_lookup` / `VACUUM_OOS_VFID_MEMO` (vacuum_oos.cpp:85) — one-entry heap→OOS VFID cache.
- `heap_recdes_get_oos_oids` (heap_file.c:27747) and `heap_recdes_contains_oos` (heap_file.c:27740) — the
  stored-form stub extractor + HAS_OOS flag probe; shared terminal consumers for all vacuum/eager paths.
- `HEAP_RECDES_CONSUME_RAW_BYTES` / `HEAP_RECDES_DONT_CONSUME_RAW_BYTES` policy enum drives the Expand gate;
  `heap_get_visible_version_from_log` is the reconstruction seam.
- Merge-readiness instrumentation confirmed present (matches OOS-CONTEXT §Current Status): `abort()` in
  vacuum_oos.cpp:315 & :372 (flag-set-but-no-OOS-file) and vacuum.c:2556 (OOS+REC_BIGONE remove). All labeled
  REVERT/remove BEFORE MERGE. Not normative behavior; noted, not classified as bugs.

---

## Answers to the two key questions

### (a) Can an expanded recdes ever become an undo (or redo) image?  →  NO.

Structural guarantee: the Expand flag (`expand_oos`) is a field of **HEAP_GET_CONTEXT** (the read/fetch context),
checked exactly once inside `heap_record_replace_oos_oids` (heap_oos.cpp:362). The WAL undo/redo images produced by
UPDATE/DELETE/INSERT come from **HEAP_OPERATION_CONTEXT** — a different structure with no Expand concept:

- Undo image = `context->home_recdes` / `forward_recdes`, always read straight from the live page via
  `spage_get_record(... PEEK|COPY)` (heap_file.c:22752, 22944, 23889, 22494, 22635). Stored form, stubs intact.
- Redo image = `context->recdes_p`, freshly built by the record transformer (demotion + new stubs). Stored form.
- Recovery/rollback (heap_rv_*) apply `rcv->data` as opaque physical slot bytes (heap_rv_undoredo_update →
  heap_update_physical, heap_file.c:17601-17627); no heap_rv_* function references OOS at all (grep = 0).

There is no code path where a CONSUME_RAW_BYTES fetch result is fed back into an update/delete undo image. The only
Expand call reachable from this audit area (R-014) writes into the caller's fetch recdes, not into any log image.

### (b) Does the MVCC old-version path honor CONSUME_RAW_BYTES?  →  YES.

`heap_get_visible_version_internal` (heap_file.c:26374): when the current version is TOO_NEW_FOR_SNAPSHOT it calls
`heap_get_visible_version_from_log` (26439) which reconstructs the old version from the undo chain via
`log_get_undo_record` (26094) — a pure physical byte reconstruction, so the reconstructed recdes carries OOS stubs
intact (stored form). Immediately after (26441-26445):

```
if (scan == S_SUCCESS && context->recdes_p != NULL)
    scan = heap_record_replace_oos_oids (thread_p, context);
```

`heap_record_replace_oos_oids` is gated (heap_oos.cpp:362-367): it returns S_SUCCESS as a no-op when the policy is
`HEAP_RECDES_DONT_CONSUME_RAW_BYTES`, and only Expands when the policy is `HEAP_RECDES_CONSUME_RAW_BYTES`. So:

- DONT_CONSUME callers (attribute-layer / fixed / header / existence) get the stored-form old version with stubs,
  and the attribute layer Resolves lazily. CORRECT.
- CONSUME_RAW_BYTES callers (heap_get_visible_version_expand_oos) get the old version **Expanded** as well. CORRECT.

The mirror-hazard described in OOS-CONTEXT §3 (a raw-byte path that forgot to Expand) does **not** apply to the
MVCC old-version reconstruction itself — the Expand call sits on the shared internal path and is reached for both
the current-version and old-version branches. Any leak would come from a *caller* choosing the wrong fetch wrapper
(forward-audit territory, e.g. CBRD-26948 xlocator_fetch_all), not from this reconstruction path.
