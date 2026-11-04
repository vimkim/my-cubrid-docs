# Sidecar design interrogation

Adversarial review of `design.md` as first drafted on 2026-11-04, before any engine code. Engine: CUBRID `develop` at `e64a04a79` in `/home/vimkim/gh/cb/sidecar`. Two adversaries ran on one brief (`/home/vimkim/gh/my-cubrid-docs/.scratch/sidecar/interrogate/brief.md`): seat 1 on Opus, seat 2 on Sonnet. Their repro scripts are in `.scratch/sidecar/interrogate/adv-1/` and `adv-2/`. The coordinator reran or re-read every finding before keeping it.

## Intent

The user wants large values out of the heap record, so that a scan of small columns reads fewer pages. Tables that never use the feature must not slow down by more than about 5%. Recovery, MVCC, vacuum, HA replication, TDE and the regression suites must keep working. The design claims that a large value stored as an ordinary MVCC heap record, stamped with DELID by the transaction that drops it and removed by stock vacuum, shares the row's lifecycle and avoids the OOS defect classes.

## Verdict

No finding attacks the lifecycle rule itself. Ten findings survived verification. They share four root causes: hooks placed at caller-level choke points instead of the heap manager's own entry and exit, header rewrites that drop the new flag, a record-size edge where refs meet `REC_BIGONE`, and a horizon pin placed after the visibility decision.

## Findings

Paths are under `src/` at `e64a04a79`.

### Root cause 1. Hooks at the locator layer and copy-area sites miss callers that go straight to the heap

| # | Finding | Seat | Evidence the coordinator checked |
|---|---|---|---|
| 1a | Old versions read from the undo log skip the copy-point expansion. `heap_get_visible_version_internal` jumps to `exit` after `heap_get_visible_version_from_log` (`storage/heap_file.c:27039-27047`). `xlocator_fetch_all`, used by `unloaddb` and SA `compactdb`, never calls `locator_return_object_assign` (its only caller is `transaction/locator_sr.c:2342`). | 1 | Code read at both sites. Seat 1's live run showed `unloaddb` printing a version that exists only in the log during an uncommitted UPDATE. |
| 1b | SA `compactdb` rewrites rows with `heap_update_logical` directly (`executables/compactdb.c:701-703`). The locator shim never runs, so old store records are never stamped and become permanent orphans. | 1 | Code read. |
| 1c | `ALTER TABLE ... PARTITION BY` runs `UPDATE t SET key=key` (`query/execute_schema.c:5841`). `locator_move_record` inserts the kept-ref image into the partition heap (`transaction/locator_sr.c:5932`) before any post-pruning hook, so refs cross heaps. | 1 | Code walk; seat 1's probe showed the rows moving into new heap files. |
| 1d | `locator_multi_insert_force` holds a freshly allocated hot page latched while it calls `locator_insert_force` for each record (`transaction/locator_sr.c:14144` loop, `storage/heap_file.c:27634`). Store inserts and the first store-creation sysop would run with a hot page held, against I-7 and G11. | 2 | Code read of the loop: `heap_alloc_new_page`, then `locator_insert_force` per record, unfix after the loop. |

Direction for the fix: make the heap manager's own entry and exit points the hooks. On the write side, Sidecar runs inside `heap_insert_logical`, `heap_update_logical` and `heap_delete_logical`, so every producer (qexec, client flush, loaddb, the applier, compactdb, partition moves) converges there. On the read side, expansion happens at the single exit of `heap_get_visible_version_internal` and in `heap_next` for readers that are not protected, after both the heap and the log paths. Multi-row insert either externalizes before it allocates the batch page or takes the per-row path for classes with a store.

### Root cause 2. Header rewrites that drop `0x08`

| # | Finding | Seat | Evidence |
|---|---|---|---|
| 2a | Server-side `loaddb` takes `BU_LOCK`, which sets `is_bulk_op` (`transaction/locator_sr.c:5026`). The insert path then runs `MVCC_CLEAR_ALL_FLAG_BITS` (`storage/heap_file.c:21655`, macro at `transaction/mvcc.h:102`), which clears every flag bit. A loaded row would keep its trailer and refs but lose `0x08`, so readers decode refs as values. The G8 audit listed only `MVCC_SET_FLAG`. | 2 | Code read. Seat 2's probe, `probe_bulk_strip`, ran the real header functions on a flagged record: `flag_byte=0x09 -> 0x00`, trailer magic still present. Seat 2 observed `BU_LOCK` granted during `loaddb -C`. |

Direction: every flag rewrite clears only INSID, DELID and PREV. Extend the audit to `MVCC_CLEAR_ALL_FLAG_BITS` and every assignment to `mvcc_flag`.

### Root cause 3. Refs meet `REC_BIGONE` through header growth

| # | Finding | Seat | Evidence |
|---|---|---|---|
| 3a | I-9 says refs never sit in a `REC_BIGONE` hot record. A record written as `REC_HOME` near the size limit becomes `REC_BIGONE` when the stock code grows its MVCC header (`storage/heap_file.c:21725`, `:23317-23356`). | 1 | Coordinator rerun of `adv-1/bigone_probe.py` on the base debug build: the largest value stored as `REC_HOME` at INSERT is 16,203 bytes; after `UPDATE id = 2` (value not assigned) and after an uncommitted DELETE, `Num_overflowed_recs` goes from 0 to 1. |

Direction: the policy keeps a hot record with refs at least 32 bytes (the largest MVCC header) under `heap_Maxslotted_reclength`, or the design allows refs in a `REC_BIGONE` hot record and says how it is read.

### Root cause 4. The horizon pin is taken after the visibility decision

| # | Finding | Seat | Evidence |
|---|---|---|---|
| 4a | Section 5.6(c) pins after the reader decides which version to read. A committed-version reader can take V from the undo log while the updater is active; the updater commits; the pin then registers a horizon that no longer covers the updater; vacuum removes the store record; the reuse store gives the slot to another value of the same column and length; the reader returns that value. | 1 | Coordinator rerun of `adv-1/pin_after_visibility.py`: "design order (visibility, then pin): 16 violating interleavings", "pin before visibility: 0 violating interleavings". Example trace: U0 U1 R0 U2 R1 V0 X0 R2. |

Direction: either pin before the visibility decision, or use the non-reuse store, where a removed slot stays `REC_MARKDELETED`, and have the expander retry from the hot record when a store record is absent. The second removes the pin.

### Other findings

| # | Finding | Seat | Evidence |
|---|---|---|---|
| 5a | `heap_reuse` resets the header without the `reserve0..2` fields that hold the store link (`storage/heap_file.c:5315-5326`). A reused hot heap keeps a stale store link. The design calls `sidecar_store_destroy` both at DROP and at reuse, so either the store is destroyed twice or it leaks. | 1 | Code read of the reset list. Seat 1 saw DROP and CREATE of a `DONT_REUSE_OID` table reuse the same file id. |
| 6a | The raw-byte census misses `query/expr_batch.c`. It has its own variable-column decoders (`:734`, `:757`, `:1370`, `:3556`) and builds layouts with `heap_rec_layout_init_repr_hdr` (`:4231`), not the hooked `heap_rec_layout_init`. | 1 | `grep` at `:4231` confirmed the layout call. |
| 7a | The IO arithmetic in section 9 overstates the hot record. The design assumed a 100-byte small part. Seat 2 measured 76 bytes at insert. A table shaped like Sidecar's hot record took 717 pages for 100,000 rows against 878 predicted, and the 1 KB `develop` table took 7,693 pages against 8,334. A2's absolute criterion "within 10% of 879 times the factor" would fail a correct build. The ratios are better than predicted, about 10.7x at 1 KB and 46x at 4 KB. | 2 | Seat 2's `repro_f2_layout.sh` output (`f2_layout.out`, `hot_capacity.out`). |

Direction: correct section 9 from measured layouts, and state every A2 threshold as a ratio against the `develop` baseline measured in the same run.

## Dropped

- Seat 1: none of its seven findings was dropped.
- Seat 2: none of its three findings was dropped. Seat 2 attacked the section 5.6 proof, the pin and the vacuum windows and reported nothing it could demonstrate there.

## Process note

Both adversaries' harness refused their `findings.md` writes, so the findings came back as text and the coordinator wrote this report. The repro scripts are in place.
