# T2 — OOS replication replay under chain reuse

- ticket: [T2](../tickets/T2-oos-replication-replay-under-chain-reuse.md)
- worktree: `/home/vimkim/gh/cb/CBRD-27230-oos-update-dedup` (branch `feat/oos`, commit `725a32c6e`)
- method: read-only source analysis; every claim is cited as `file:line`

## Summary

1. The repl log never carries a resolved row image. It carries *pointers*: one `RVREPL_OOS_INSERT` item per OOS value, whose `lsa` points at the master's physical `RVOOS_INSERT` WAL record, followed by one `RVREPL_DATA_INSERT`/`RVREPL_DATA_UPDATE` item for the heap row (`locator_sr.c:8150-8173`, `locator_sr.c:8940-8979`, `replication.c:459-470`).
2. The replica reads the master's WAL chunk bytes out of those LSAs, runs **its own `oos_insert`** (`locator_sr.c:5287` `locator_oos_insert_force`), and then rewrites the master's OOS OIDs inside the replicated heap record with its own (`locator_sr.c:14166` `locator_fixup_oos_oids_in_recdes`). That is the code that makes OOS-CONTEXT invariant 5 true.
3. The master↔replica contract is **positional and count-exact**: #OOS-flagged attributes in the record must equal #OOS items applied just before it, or the replica errors out (`locator_sr.c:14179`, `:14234`, `:14253`).
4. Sub-Q2 — yes: an UPDATE that does not assign an OOS attribute still resolves it (`heap_attrvalue_point_variable`, `heap_file.c:10514/10445`), re-inserts a fresh chain (`heap_file.c:13302-13310`), and therefore still ships the attribute's **full value** through the WAL to the replica on every update.
5. Sub-Q3 — under naive dedup the replica **fails loudly, not silently**: fewer OOS items than stubs ⇒ `ER_HA_GENERIC_ERROR "not enough OOS OIDs" / "missing OOS OID"`, HA apply stops. Silent divergence is not reachable, because dedup can only *reduce* the published count while the flagged-attribute count stays fixed.
6. Sub-Q3 — the replica **does need a change**. Dedup must emit a per-reused-attribute *marker* item to keep the positional 1:1 contract, and the replica's fixup must source that slot's OID from **its own previous row version** instead of from a fresh insert. The old version is already fetched at `locator_sr.c:6943` — but with OOS **expansion on**, so the stub is gone; it must be switched to `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`.
7. Replica-side vacuum then needs the same old∩new head-OID sharing check as the master (`vacuum_oos.cpp:154`), since the replica's own old and new row versions would share a chain.
8. `applylogdb` sql.log breaks per deduped UPDATE (cache keyed by master head OID, miss ⇒ `ER_FAILED`, `log_applier.c:3837-3847`); it is error-isolated from row apply, so it degrades rather than stops.
9. CDC/flashback get *better* diffs (unchanged OOS columns stop looking modified) but their unimplemented stub-resolve gap gets *harder*: the value's chunks now live in an older, possibly archived transaction (`log_manager.c:11942`, `:12480`).
10. Bonus AS-IS defect found at the known refactoring site: `locator_add_or_remove_index_internal` can emit OOS repl items from a **stale** `thread_p->oos_oids` on a DELETE (`locator_sr.c:8150`), draining an empty LSA queue into `assert(false)` (`replication.c:461-469`).

---

## 1. AS-IS replication content

### 1.1 What the master writes — pointers, not values

OOS values are replicated by **reference into the master's own WAL**, never as a resolved row image.

Physical layer. Every OOS chunk insert is logged with `RVOOS_INSERT` carrying the full on-page chunk record (header + payload):

- `oos_insert_record_in_fixed_page` → `oos_log_insert_physical (thread_p, page_ptr, &oos_vfid, &oid, &oos_recdes)` — `oos_file.cpp:1530`.

Repl-tracking layer. When `log_append_{undo,}redo_crumbs` appends an `RVOOS_INSERT`, its LSA is pushed onto a per-transaction queue:

```c
else if (rcvindex == RVOOS_INSERT && !tdes->oos_suppress_insert_lsa_queueing)
  {
    tdes->oos_insert_lsa_queue.push (tdes->tail_lsa);
```
— `log_manager.c:2253-2257` (and the mirror at `:2522`). Queue field: `log_impl.h:529`; suppression flag: `log_impl.h:530`.

In parallel, each successfully inserted head OID is published into a per-thread vector:

- `oos_publish_oos_oid` → `thread_p->oos_oids.push_back (oid)` — `oos_file.cpp:1143-1152`, called from `oos_insert` (`oos_file.cpp:1209`) and `oos_insert_many` (`oos_file.cpp:1256`, `:1332`). Vector declared at `thread_entry.hpp:322`.

The pair `(oos_oids, oos_insert_lsa_queue)` is reset once per *logical heap record build*:

- `heap_oos_begin_insert_publication` clears both — `heap_oos.cpp:606-620`, called first thing in `heap_attrinfo_insert_to_oos` (`heap_file.c:12691`).

Multi-chunk values get a boundary marker so the applier knows to reassemble. `oos_insert_across_pages` logs an empty `LOG_DUMMY_OOS_RECORD`, suppresses the per-chunk auto-queueing, and enqueues exactly two entries — the dummy LSA and the *tail* chunk LSA — plus a `oid_Null_oid` publication:

```c
log_append_empty_record (thread_p, LOG_DUMMY_OOS_RECORD, NULL);
LSA_COPY (&dummy_lsa, &tdes->tail_lsa);
tdes->oos_suppress_insert_lsa_queueing = true;
...
tdes->oos_insert_lsa_queue.push (dummy_lsa);
tdes->oos_insert_lsa_queue.push (tail_chunk_lsa);
thread_p->oos_oids.push_back (oid_Null_oid);
```
— `oos_file.cpp:1439-1442`, `:1485-1490`; the pairing contract is documented in the block comment at `oos_file.cpp:1380-1401`.

Repl-item layer. `repl_log_insert` maps each published OID to one replication item and pops its LSA off the queue:

```c
case RVREPL_OOS_INSERT:
case RVREPL_DUMMY_OOS_RECORD:
  if (!tdes->oos_insert_lsa_queue.is_empty ())
    { LOG_LSA oos_lsa = tdes->oos_insert_lsa_queue.pop (); LSA_COPY (&repl_rec->lsa, &oos_lsa); }
  else { assert (false); }
```
— `replication.c:459-470`. The item body itself carries only class name + packed PK (`replication.c:391-419`) — **no column data**. All value bytes are reached through `repl_rec->lsa`.

Rcvindex definitions: `recovery.h:202-208` (`RVREPL_OOS_INSERT = 137`, `RVREPL_OOS_DELETE = 138`, `RVREPL_DUMMY_OOS_RECORD = 140`). Note `RVREPL_OOS_DELETE` has **no producer and no consumer** anywhere in `src/` — only a name-table entry (`recovery.c:893`) and a TDE predicate mention (`tde.h:142`). It is a reserved placeholder.

### 1.2 The two emission sites (and the known refactoring note)

**INSERT / DELETE — `locator_add_or_remove_index_internal` (`locator_sr.c:7869`).** This is the "unnecessary OOS replication log in `locator_add_or_remove_index`" item from OOS-CONTEXT §5. The OOS items are emitted inside the index-maintenance loop, guarded by `index->type == BTREE_PRIMARY_KEY` (`:8147`), immediately before the row item:

```c
if (heap_recdes_contains_oos (recdes))
  {
    for (int i = 0; i < (int) thread_p->oos_oids.size (); i++)
      {
        LOG_RCVINDEX oos_repl_rcvindex =
          OID_ISNULL (&thread_p->oos_oids[i]) ? RVREPL_DUMMY_OOS_RECORD : RVREPL_OOS_INSERT;
        error_code = repl_log_insert (thread_p, class_oid, &thread_p->oos_oids[i], LOG_REPLICATION_DATA,
                                      oos_repl_rcvindex, key_dbvalue, REPL_INFO_TYPE_RBR_NORMAL);
```
— `locator_sr.c:8150-8168`, followed by the row item at `:8170-8173`.

Two things are wrong with the site, which is presumably why it is flagged for refactoring:

- *Wrong module.* Emitting an OOS (heap/storage) replication record from B-tree index maintenance only because that is where the PK value happens to be already unpacked (`:8138-8146` comment). OOS-CONTEXT §5 Optimization B proposes moving both emissions next to the heap-row repl log at `attrinfo_force` time.
- *Reachable stale-state bug.* The block runs for **DELETE too** (`is_insert == false`), gated only on the *old* record containing OOS. `thread_p->oos_oids` is not cleared after emission — the only clears are per-network-request (`server_support.c:1997`), per-record-build (`heap_oos.cpp:617`), on OOS insert error (`oos_file.cpp:1157`), and on the replica's apply loop (`locator_sr.c:7167/7187/7209`). So a request that first builds an OOS-backed record and then deletes an OOS-backed row re-emits the *previous* record's OIDs as `RVREPL_OOS_INSERT` items, popping an already-drained queue → `assert (false)` at `replication.c:468` in debug, and an unset `repl_rec->lsa` shipped to the replica in release. Any dedup design that touches this site should fix or delete the DELETE-path emission at the same time.

**UPDATE — `locator_update_index` (`locator_sr.c:8389`).** Same shape, under `if (pk_btid_index != -1)`; OOS items first, then `RVREPL_DATA_UPDATE`:

```c
/* insert oos replication log */
if (heap_recdes_contains_oos (new_recdes))
  { ... repl_log_insert (..., oos_repl_rcvindex, new_key, REPL_INFO_TYPE_RBR_NORMAL); ... }
error_code = repl_log_insert (thread_p, class_oid, oid, LOG_REPLICATION_DATA, RVREPL_DATA_UPDATE, repl_old_key, ...);
```
— `locator_sr.c:8940-8979`. Note the OOS items are keyed by the **new** PK value, the row item by the **old** PK value (`:8905-8934`).

No PK ⇒ no replication at all for the row, OOS items included (`locator_sr.c:8991-9006`).

### 1.3 What the replica does — its own `oos_insert`, then OID fixup

`applylogdb` dispatch (`log_applier.c:6710-6741`):

| item | handler | effect |
|---|---|---|
| `RVREPL_DUMMY_OOS_RECORD` | `la_apply_dummy_oos_log` (`:6018`) | sets `apply->need_oos_rebuild = true` (field: `:273`) |
| `RVREPL_OOS_INSERT` | `la_apply_oos_insert_log` (`:6043`) | materializes the chunk record, queues it as `LC_FLUSH_INSERT_OOS` |
| `RVREPL_DATA_INSERT` / `_UPDATE` | `la_apply_insert_log` / `la_apply_update_log` | queues the heap row |

`la_apply_oos_insert_log` reads the master's WAL at `item->target_lsa`: single-chunk goes straight through `la_get_recdes` (`:6104`); multi-chunk walks the log forward from the tail chunk and concatenates via `la_rebuild_oos_recdes` (`:6078`, implementation `:4871-…`, which validates `total_data_length` agreement across chunks at `:4957-4966`). The result is queued with `operation = LC_FLUSH_INSERT_OOS` (`:5635-5637`) through `la_repl_add_object`.

Client-side batching keeps the group atomic — the OOS objects and the heap row **must** land in the same `xlocator_repl_force` copy area, so the flush is grown rather than split when an OOS insert is pending:

```c
/* OOS insert records must be forced together with the following heap insert/update record.
 * The server uses the OID produced by LC_FLUSH_INSERT_OOS to rewrite the OOS placeholder
 * in the heap record within the same xlocator_repl_force call. */
```
— `locator_cl.c:7040-7047`; the `pending_oos_insert` latch is set at `:7119`.

Server-side apply, `xlocator_repl_force` (`locator_sr.c:7043-7189`):

1. `LC_FLUSH_INSERT_OOS` → `locator_oos_insert_force` (`:5287-5339`) — finds/creates the *replica's own* OOS file (`heap_oos_find_vfid (..., true)`, `:5306`), strips the logged `OOS_RECORD_HEADER`, and calls `oos_insert` (`:5325-5326`). That call publishes the **replica's** OID into `thread_p->oos_oids` (`oos_file.cpp:1209`).
2. Heap row → before dispatch, `locator_fixup_oos_oids_in_recdes` (`:7089-7098`, implementation `:14166-14263`) walks the record's variable-offset table, finds `OR_IS_OOS (offset)` slots in attribute order, and overwrites each 8-byte head OID in place with `thread_p->oos_oids[oos_oid_count++]` (`:14242-14250`).
3. `thread_p->oos_oids.clear ()` after every non-OOS object (`:7185-7188`), on OOS failure (`:7164-7169`), and on any error exit (`:7209`).

Note the replica never emits OOS repl markers itself — `oos_needs_repl_tracking` returns false under `LOG_CHECK_LOG_APPLIER` (`oos_file.cpp:2338-2342`), so `oos_insert_across_pages` publishes exactly **one** entry per value on the replica versus **two** (null + real) on the master. The vector therefore means different things on the two sides: on the master it is a list of *publication events*; on the replica it is a list of *values*, positionally paired with the record's OOS-flagged attributes. **The positional attribute pairing is a replica-side-only contract.**

The contract is enforced with three hard errors:

```c
if (thread_p->oos_oids.empty ())            → "missing OOS OID while applying replicated heap record"   (:14179-14184)
if (oos_oid_count >= (int) thread_p->oos_oids.size ()) → "not enough OOS OIDs while applying replicated heap record" (:14234-14240)
if (oos_oid_count != (int) thread_p->oos_oids.size ()) → "too many OOS OIDs while applying replicated heap record"   (:14253-14258)
```

This is the code backing OOS-CONTEXT invariant 5: the replica's OIDs are its own, only value equality is replicated.

---

## 2. Sub-question 2 — UPDATE today re-ships the full value of unassigned OOS attributes

**Yes.** The full value crosses the wire (well, the log) on every update, for every OOS-backed attribute, assigned or not.

Chain of evidence, master side:

1. The UPDATE executor populates only the assigned attributes; the rest stay `HEAP_UNINIT_ATTRVALUE`. At disk-transform time, `heap_attrinfo_transform_to_disk_internal` fills them from the *old* record:
   ```c
   /* get any of the values that have not been set/read */
   if (heap_attrinfo_set_uninitialized (thread_p, &attr_info->inst_oid, old_recdes, attr_info) != NO_ERROR)
   ```
   — `heap_file.c:13257`; the loop that calls `heap_attrvalue_read` for each uninitialized value is at `heap_file.c:12153-12163`.
2. `heap_attrvalue_read` → `heap_attrvalue_point_variable` (`heap_file.c:10514`) detects `OR_IS_OOS (offset)` and **resolves the chain out of the OOS file** via `heap_attrvalue_read_oos_inline` (`heap_file.c:10445`, dispatch at `:10539-10543`). The unchanged attribute is now a materialized `DB_VALUE`.
3. `heap_attrinfo_determine_disk_layout` (`heap_file.c:12305-12394`) re-plans demotion from scratch. It has **no notion of "unchanged"** — the only inputs are `is_fixed`, `oos_storage` (FORCE_OUTLINE / PREFER_INLINE), `column_size[i] > OR_OOS_INLINE_SIZE`, and the `DB_PAGESIZE/4` target (`:12326-12337`, `:12345-12390`).
4. Every selected column is re-serialized and re-inserted:
   ```c
   if (has_oos) { status = heap_attrinfo_insert_to_oos (thread_p, attr_info, lob_create_flag, &oos_plan); }
   ```
   — `heap_file.c:13302-13310` → `heap_attrinfo_prepare_oos_insert_requests` (`:12619-12651`) → `oos_insert_many` (`heap_oos.cpp:653`). Requests are built and consumed strictly in ascending attribute index order (`heap_file.c:12628`, `oos_file.cpp:1282-1360` — greedy same-page batching, **no reordering**), which is exactly what makes the replica's positional fixup correct.
5. Each of those inserts emits a fresh `RVOOS_INSERT` WAL record containing the full payload, and publishes a fresh OID — so `locator_update_index` emits a fresh `RVREPL_OOS_INSERT` item for the unchanged attribute too (`locator_sr.c:8956-8968`).

Replica side: it cannot tell the difference. It applies an `oos_insert` of the re-shipped value, gets a brand-new replica-local OID, and patches it into the stub. The replica's *old* chain is left for its own vacuum, exactly as on the master.

Costs visible in this path today: one `oos_read` + one `oos_insert` + one full-payload WAL record + one repl item per unchanged OOS attribute per update, on **both** master and replica. This is the CBRD-26516 / OOS-CONTEXT §5 Optimization-A waste, and confirms the OOS-CONTEXT §3 claim ("UPDATE always allocates fresh value chains") against the code.

---

## 3. Sub-question 3 — what must change under chain reuse

### 3.1 What breaks if nothing else changes

Master-side dedup means: the stub for the unchanged attribute is copied from the old record, no `oos_insert` runs, so nothing is published into `thread_p->oos_oids` and nothing is queued into `oos_insert_lsa_queue`. The emission loop at `locator_sr.c:8956` is driven by `oos_oids.size ()`, so it emits **N − reused** OOS items while the record still carries **N** `OR_IS_OOS` stubs.

On the replica, `locator_fixup_oos_oids_in_recdes` walks all N stub slots against a vector of N − reused entries:

- all attributes reused ⇒ empty vector ⇒ `"missing OOS OID while applying replicated heap record"` (`locator_sr.c:14179-14184`);
- some reused ⇒ `"not enough OOS OIDs while applying replicated heap record"` (`:14234-14240`).

Either way `xlocator_repl_force` goes to `exit_on_error`, `applylogdb` records a failure and retries/stops (`log_applier.c:6760-6790`). **Fail-loud, not silent divergence** — worth stating explicitly in the spec, because it is a structural property, not luck: dedup can only shrink the published count while the flagged-attribute count is fixed by the record layout, so the count check always fires. There is no arrangement of reused/new attributes that produces a count match with shifted pairing.

Also note what the *unfixed* record would mean if the guard were removed: the reused slot would still hold the **master's** OID, which on the replica addresses an unrelated (or non-existent) slot in the replica's OOS file. That is precisely the corruption the guard exists to prevent.

### 3.2 What the repl log must carry

The minimum the replica needs, per OOS-flagged attribute slot, is a one-of-two decision: *(a) here is a freshly logged chain, insert it and use your new OID*, or *(b) keep whatever OID your own current row version has in this slot*. Two ways to deliver it:

**Option A — reuse marker, keeps the positional contract (recommended).** Emit a payload-free marker item per reused attribute so the item count stays equal to the stub count. Mechanically this needs a distinct rcvindex; `RVREPL_DUMMY_OOS_RECORD` is **not** available (it already means "the next `RVREPL_OOS_INSERT` is multi-chunk", `log_applier.c:6018-6029`) and the `oid_Null_oid` sentinel in `oos_oids` is already taken by the same multi-chunk convention (`oos_file.cpp:1489`). The unused `RVREPL_OOS_DELETE = 138` slot (`recovery.h:203`) or a new code is the clean choice, plus a matching sentinel pushed into `oos_oids` at dedup time so `locator_sr.c:8956`'s loop stays a straight walk.

Replica changes required by Option A:

1. `la_apply_*` — a new handler that queues a "reuse" placeholder object in the same copy-area group (the group-atomicity latch at `locator_cl.c:7119` must treat it like `LC_FLUSH_INSERT_OOS`, or the row can be split into a different force call and the pairing is lost).
2. `locator_fixup_oos_oids_in_recdes` (`locator_sr.c:14166`) — on a reuse slot, take the OID from the replica's **own previous version** of the row rather than from a fresh insert.
3. **The old version is already fetched but currently unusable.** `locator_repl_prepare_force` fetches it at `locator_sr.c:6943-6945`:
   ```c
   scan = heap_get_visible_version (thread_p, &obj->oid, &obj->class_oid, old_recdes, force_scancache, PEEK,
                                    NULL_CHN, HEAP_RECDES_CONSUME_RAW_BYTES);
   ```
   `HEAP_RECDES_CONSUME_RAW_BYTES` means *materialize OOS values* (`heap_file.h:367`; it sets `expand_oos = true` at `heap_file.c:26475`), so the returned record has **no stubs left to copy**. Today `old_recdes` is used only for `or_chn (old_recdes)` (`:6960`) — i.e. this is also one of the CBRD-26847 census sites that expands for no reason. Switching it to `HEAP_RECDES_DONT_CONSUME_RAW_BYTES` both removes a pointless `oos_read` per replicated UPDATE and hands the dedup fixup exactly the stub bytes it needs (`heap_recdes_get_oos_oids`, `heap_file.c:28252`, parses them).

With that, **the replica's dedup falls out naturally**: it writes a stub pointing at its own existing chain and performs no `oos_insert`. It does not need to re-derive "was this attribute assigned?" — the master already decided, and the marker transports the decision.

**Option B — keep shipping the value (not recommended).** The master could still log the unchanged value so the replica keeps doing a fresh `oos_insert` and no replica code changes at all. It is *correct* (invariant 5 only promises value equality), but it requires the master to `oos_read` + WAL-log the value it just decided not to rewrite — which is the entire cost dedup is meant to remove (`heap_file.c:10445` read + `oos_file.cpp:1530` log). It also leaves the replica strictly more expensive than the master forever. Only worth keeping as a fallback if marker plumbing proves too invasive for the milestone.

### 3.3 Consequences the replica inherits

- **Replica vacuum needs the same fix as the master.** Once the replica reuses a chain, its own old and new row versions share head OIDs, and `vacuum_forward_walk_oos_delete_atomic` (`vacuum_oos.cpp:154`, which pulls head OIDs straight out of the UPDATE undo recdes at `:285-290`) will delete a chain the live post-image still references. The old∩new sharing check that OOS-CONTEXT §5 Optimization A lists as a prerequisite is **not master-only** — the replica runs its own vacuum. (Owned by T3; flagged here because the replication design cannot assume it.)
- **SA_MODE eager cleanup is already reuse-safe**, and is the existing template for the check: `heap_oos_delete_unreferenced` skips any old OID present in the new record (`heap_oos.cpp:754-757`, via `oos_oid_in_vector`).
- **`applylogdb` sql.log degrades.** With sql logging on, the applier caches each assembled OOS payload keyed by the **master's** head OID (`log_applier.c:6145-6149` → `la_cache_oos_value`, `:3767`) and resolves it at row-emit time (`la_get_current` → `la_resolve_oos_value_for_sql_log`, `:3993`, `:3837`). A reused attribute has no chunk to cache, so the lookup misses and the function deliberately fails loudly: `ER_HA_GENERIC_ERROR "OOS value missing from SQL log cache"` (`:3845`). Row replication survives — the call is wrapped in `er_stack_push/pop` + `la_set_error_sql_log` (`:6136-6156`) — but every deduped UPDATE would log an error and drop the column from sql.log. Under Option A the applier must instead resolve that column from the replica's own chain (an `oos_read` on the replica-side OID) or skip it deliberately. **This needs an explicit decision in the spec; it is the one place where "the replica needs no change" is definitely false.**
- **A reused chain is a chain the replica must not lose.** Nothing in the apply path pins it: the replica's post-image references it, so ordinary MVCC + the vacuum sharing check above are sufficient. No extra pinning is needed, but the sharing check is load-bearing.

---

## 4. Sub-question 4 — CDC / flashback edges

Both CDC and flashback consume the *physical* heap log records, not the replication items, through the same helper:

- `cdc_get_recdes` (`log_manager.c:11414`), called from CDC's log-scan loop (`log_manager.c:10962`, `:10993`, `:11046`) and from flashback (`flashback.c:947`, `:990`, `:1050`).
- OOS is explicitly unhandled there: `//TODO : Additional handling for OOS columns in CDC will be needed later.` — `log_manager.c:11942`, directly above the `RVHF_INSERT`/`RVHF_INSERT_NEWHOME` redo extraction.
- The multi-chunk marker is seen but not acted on: in `cdc_get_overflow_recdes`, `LOG_DUMMY_OOS_RECORD` terminates the overflow walk with `/* TODO: add CDC support for rebuilding multi-chunk OOS records after this marker. */` — `log_manager.c:12475-12481`.

So today CDC and flashback hand consumers a recdes containing **raw 16-byte OOS stubs** (head OID + length) where the column value should be. That is the OOS-CONTEXT §5 "CDC flashback OOS-stub Resolve" gap.

How chain reuse moves that gap:

- **It gets one thing right for free.** Today every UPDATE rewrites the stub OID of *every* OOS column, so a CDC/flashback consumer diffing undo-vs-redo raw bytes sees an unchanged OOS column as **modified** on every update. Under dedup the stub bytes are byte-identical between pre- and post-image for unassigned attributes, so a byte-diff correctly reports "no change". Any future CDC OOS support gains an exact, cheap "did this column change?" test.
- **It makes the resolve itself materially harder.** The obvious way to close the gap without random-reading the live OOS file is to reconstruct the value from the `RVOOS_INSERT` records that sit in the *same* transaction, just before the `RVHF_UPDATE` (that is exactly what `la_rebuild_oos_recdes`, `log_applier.c:4871`, already does for the applier, and what the `LOG_DUMMY_OOS_RECORD` hook at `log_manager.c:12478` was left for). Under dedup, a reused attribute has **no `RVOOS_INSERT` in the current transaction** — its chunks were logged whenever the value was last written, arbitrarily far back and quite possibly in an archived or purged log volume. A log-only CDC resolve is then impossible for reused columns; CDC would have to fall back to reading the live OOS file by OID, which is only valid while that version is still alive (flashback of an old transaction may find the chain already vacuumed).
- **Practical recommendation for the spec:** state that dedup makes "resolve OOS from the current transaction's WAL" unimplementable as a general CDC strategy, and that closing the CDC gap must be designed as an OID-based read against the OOS file with an explicit answer for the vacuumed-chain case. Worth a line in the CBRD-27230 risk section even though CDC OOS support is not in scope.

---

## Appendix — key call sites

| Concern | Symbol | Location |
|---|---|---|
| Physical OOS chunk WAL record | `oos_log_insert_physical` call | `src/storage/oos_file.cpp:1530` |
| Chunk-LSA auto-queue | `tdes->oos_insert_lsa_queue.push` | `src/transaction/log_manager.c:2253`, `:2522` |
| Head-OID publication | `oos_publish_oos_oid` | `src/storage/oos_file.cpp:1143` |
| Per-record publication reset | `heap_oos_begin_insert_publication` | `src/storage/heap_oos.cpp:606` |
| Multi-chunk marker + pairing | `oos_insert_across_pages` | `src/storage/oos_file.cpp:1380-1495` |
| Master repl emission (INSERT/DELETE) | `locator_add_or_remove_index_internal` | `src/transaction/locator_sr.c:8150-8173` |
| Master repl emission (UPDATE) | `locator_update_index` | `src/transaction/locator_sr.c:8940-8979` |
| Repl item → WAL LSA binding | `repl_log_insert` | `src/transaction/replication.c:459-470` |
| Applier: multi-chunk marker | `la_apply_dummy_oos_log` | `src/transaction/log_applier.c:6018` |
| Applier: OOS chunk apply | `la_apply_oos_insert_log` | `src/transaction/log_applier.c:6043` |
| Applier: multi-chunk reassembly | `la_rebuild_oos_recdes` | `src/transaction/log_applier.c:4871` |
| Applier: sql.log value cache | `la_cache_oos_value` / `la_resolve_oos_value_for_sql_log` | `src/transaction/log_applier.c:3767` / `:3837` |
| Group-atomic flush | `pending_oos_insert` | `src/transaction/locator_cl.c:7040-7119` |
| Replica: own `oos_insert` | `locator_oos_insert_force` | `src/transaction/locator_sr.c:5287` |
| Replica: stub OID rewrite | `locator_fixup_oos_oids_in_recdes` | `src/transaction/locator_sr.c:14166` |
| Replica: old version fetch (expands OOS today) | `locator_repl_prepare_force` | `src/transaction/locator_sr.c:6943` |
| UPDATE resolves unassigned OOS attrs | `heap_attrvalue_point_variable` → `heap_attrvalue_read_oos_inline` | `src/storage/heap_file.c:10514` / `:10445` |
| UPDATE re-plans demotion (no reuse notion) | `heap_attrinfo_determine_disk_layout` | `src/storage/heap_file.c:12305` |
| UPDATE re-inserts every selected column | `heap_attrinfo_insert_to_oos` | `src/storage/heap_file.c:12680`, called `:13305` |
| Vacuum forward walk (needs old∩new check) | `vacuum_forward_walk_oos_delete_atomic` | `src/query/vacuum_oos.cpp:154` |
| SA_MODE reuse-safe precedent | `heap_oos_delete_unreferenced` | `src/storage/heap_oos.cpp:702-757` |
| CDC/flashback recdes builder | `cdc_get_recdes` (TODO at `:11942`) | `src/transaction/log_manager.c:11414` |
| CDC multi-chunk hook | `LOG_DUMMY_OOS_RECORD` TODO | `src/transaction/log_manager.c:12478-12481` |
