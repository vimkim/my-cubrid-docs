# T8 — Write-path mechanics of reuse: where "assigned" is known and how the old stub carries forward

- Ticket: [T8](../tickets/T8-write-path-mechanics-of-reuse.md) | Map: [CBRD-27230](../map.md)
- Source: worktree `/home/vimkim/gh/cb/CBRD-27230-oos-update-dedup` @ `725a32c6e` (read-only; nothing modified)
- Inputs: locked contract [T4](../tickets/T4-lock-cleanup-architecture.md), OOS-CONTEXT §3/§5, CBRD-26950 20B-stub design
- Note on branch state: this worktree still has the raw `DB_PAGESIZE / 4` gate (`heap_file.c:12345`) and a 16B
  `OR_OOS_INLINE_SIZE` (`object_representation.h:459`); CBRD-27057's `heap_oos_inline_target_size()` and CBRD-26950's
  20B stub are **not** in this tree. Nothing below depends on which gate constant is in force.

## Summary

1. "Assigned" is knowable at exactly one place: `attr_info->values[i].state == HEAP_UNINIT_ATTRVALUE` on entry to
   `heap_attrinfo_set_uninitialized` (`heap_file.c:12156`) — the per-row reset/assign pair is
   `heap_attrinfo_clear_dbvalues` + `heap_attrinfo_set` (`query_executor.c:10714`, `:10822/:10826`).
2. That same function immediately destroys the signal by materializing the old value: `heap_attrvalue_read`
   (`:12158`) → `heap_attrvalue_read_oos_inline` → `oos_read` (`heap_file.c:10482`). This is OOS-CONTEXT Idea A's
   touch point and the read to eliminate.
3. Downstream nothing knows the value came from the old record: `heap_attrinfo_determine_disk_layout` sizes it by
   `pr_data_writeval_disk_size` (`:12244`), re-demotes it (`:12382`), and `heap_attrinfo_insert_to_oos` writes a
   brand-new chain (`:12680`) whose fresh head OID is stamped into the new stub (`:13047`).
4. Minimal TO-BE: capture `(head OID, full length[, generation])` from the old stub inside `set_uninitialized`,
   mark the column "reused", and split `heap_oos_column_plan.selected` (write a stub) from "needs insert"
   (allocate a chain). The stub writer at `:13039-13050` then needs no change.
5. The same single pass yields the drop list for free: assigned + old-VOT-`OR_IS_OOS` ⇒ one notify entry. No
   comparison, no read.
6. The registration vicinity is the three `heap_log_update_physical` call sites (`:24145`, `:23588`, `:23906`),
   the same window where the SA_MODE eager cleanup already sits (`:24190`, `:23705`).
7. **Blocking mechanical detail for T6**: vacuum's block stream is fed only by MVCC *undo* appends
   (`log_append.cpp:967-996`, `:1384`), and `logtb_complete_mvcc` runs *before* `log_tran_do_postpone`
   (`log_manager.c:5228` vs `:5245`) — so a bare `log_append_postpone` of an MVCC-undo-shaped notify cannot work
   as-is. Three concrete shapes are listed in §2.3; the T4 invariant survives all three.
8. Edge case A: a reused stub stays OOS-backed even below the gate. That is safe — the gate literal exists only
   inside `determine_disk_layout` and nowhere on the read/vacuum/recovery path.
9. Edge case B: `heap_oos_delete_unreferenced` needs no change; its old-minus-new skip (`heap_oos.cpp:754-760`) is
   already the shared-chain rule, and its doc comment already describes the UPDATE case that way.
10. Idea B is pure synergy: it moves `oos_insert` into the same window the notify registration needs, and dedup
    shrinks the OOS repl-log volume Idea B has to correlate.

---

## 1. AS-IS trace

### 1.1 Where "assigned" is known — and for how long

The UPDATE write path receives the assigned set twice, in two different shapes:

**(a) Per-value state.** `qexec_execute_update` resets the whole attr_info once per row and then sets only the
assigned columns:

- `heap_attrinfo_clear_dbvalues (&internal_class->attr_info)` — `query_executor.c:10714`; the function clears every
  non-UNINIT value back to `HEAP_UNINIT_ATTRVALUE` (`heap_file.c:10331-10345`).
- `heap_attrinfo_set (oid, attr_id, …)` per assignment — `query_executor.c:10822` / `:10826`; it ends with
  `value->state = HEAP_WRITTEN_ATTRVALUE` (`heap_file.c:12084`).

So at write-path entry the predicate **"unassigned" ≡ `value->state == HEAP_UNINIT_ATTRVALUE`** holds exactly. The
MVCC re-evaluation path re-establishes the same invariant for its second pass: it clears and re-sets only the
assignments (`locator_sr.c:13729-13749`).

**(b) The `att_id[] / n_att_id` array** passed to `locator_attribute_info_force`
(`query_executor.c:10875-10879` → `locator_sr.c:7569-7574`). This is used for index maintenance
(`heap_attrinfo_check_unique_index`, `locator_sr.c:7706`) and is **not** forwarded into
`heap_attrinfo_transform_to_disk` (`locator_sr.c:7499`), so inside the record transformer only signal (a) exists.

### 1.2 The old record reaches the transformer unexpanded

`locator_attribute_info_force` fetches the pre-image with `heap_get_last_version` (`locator_sr.c:7616`) or
`locator_lock_and_get_object` (`:7634`), both with `HEAP_RECDES_DONT_CONSUME_RAW_BYTES` — i.e. **no record-level
Expand**; the old record still carries its OOS inline stubs. It is handed down as `old_recdes` through
`locator_allocate_copy_area_by_attr_info` (`:7682`) → `heap_attrinfo_transform_to_disk` (`:7499`).

### 1.3 The `oos_read` we want to remove

`heap_attrinfo_transform_to_disk_internal` (`heap_file.c:13234`) opens with
`heap_attrinfo_set_uninitialized (thread_p, …, old_recdes, attr_info)` (`:13257`).

Inside (`heap_file.c:12111-12215`):

```c
for (i = 0; i < attr_info->num_values; i++)
  {
    value = &attr_info->values[i];
    if (value->state == HEAP_UNINIT_ATTRVALUE)
      {
        ret = heap_attrvalue_read (recdes, value, attr_info);   /* heap_file.c:12158 */
```

`heap_attrvalue_read` (`:10634`) → `heap_attrvalue_point_variable` (`:10513`) → the OOS branch at `:10539`
(`OR_IS_OOS (offset)`) → `heap_attrvalue_read_oos_inline` (`:10444`) → **`oos_read`** (`:10482`), which walks the
whole chain into a stack scratch of `IO_MAX_PAGE_SIZE` (`:10640`) or a heap buffer (`:10474`). The DB_VALUE is then
built with COPY semantics because the OOS buffer is transient (`:10608`), and the value's state becomes
`HEAP_READ_ATTRVALUE` (`:10597` / `:10610`).

One read on this path is *not* removable and is unrelated to dedup: for an **assigned** BLOB/CLOB the function
deliberately re-reads the old value to delete the old external ELO (`:12164-12194`). That branch keys on
`HEAP_WRITTEN_ATTRVALUE`, i.e. assigned columns only. (The DELETE-side equivalent
`heap_attrinfo_delete_lob` at `:11249` is likewise untouched — T4 §4 leaves DELETE alone.)

### 1.4 What then happens to the unassigned OOS-backed attribute

By the time layout is decided, the value is an ordinary materialized DB_VALUE and is treated as such:

| Step | Site | Effect on an unassigned OOS-backed attribute |
|---|---|---|
| payload sizing | `heap_attrinfo_get_record_payload_size`, `heap_file.c:12244` | counted at its **logical** size (`pr_data_writeval_disk_size`), so the record looks big again |
| gate | `heap_attrinfo_determine_disk_layout`, `:12345` | `header + payload + mvcc_extra > DB_PAGESIZE/4` fires |
| candidate | `:12355` | eligible again (`column_size[i] > OR_OOS_INLINE_SIZE`), largest-first sorted at `:12371` |
| demote | `:12382` | `(*oos_plan)[cand.attr_index].selected = true`, `*has_oos = true` |
| serialize | `heap_attrinfo_serialize_oos_value` `:12596` → `heap_attrinfo_dbvalue_to_recdes` `:12508` | the value is re-serialized from the DB_VALUE |
| insert | `heap_attrinfo_insert_to_oos` `:12680` → `heap_oos_insert_serialized_values` (`heap_oos.cpp:630`) → `oos_insert_many` | **a brand-new chain**; the fresh head OID lands in `plan.oid` via the request built at `:12645` |
| write stub | `heap_attrinfo_transform_variable_to_disk` `:13039-13050` | `OR_SET_VAR_OOS` on the VOT offset at `:13033`, then `or_put_oid (plan.oid)` + `or_put_bigint (plan.length)` |

Net cost per unassigned OOS-backed attribute per UPDATE today: **one full `oos_read` + one full `oos_insert`**
(new chain, per-chunk WAL, per-chunk replication log) **+ one dead chain** for vacuum to reclaim.

The dead old chain is reclaimed by:

- MVCC: `vacuum_forward_walk_reclaim_oos` (`vacuum_oos.cpp:223`) → `vacuum_forward_walk_oos_delete_atomic`
  (`:154`), driven from `RVHF_UPDATE_NOTIFY_VACUUM` / `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` undo images
  (`vacuum.c:3723-3729`, `:4232-4241`). T4 removes this machinery.
- non-MVCC / SA_MODE: `heap_oos_delete_unreferenced` (`heap_oos.cpp:702`), called at `heap_file.c:24192`
  ("update home") and `:23707` ("update relocation").

This is precisely the old/new head-OID disjointness that OOS-CONTEXT §3 records as the M1 assumption.

---

## 2. TO-BE sketch (invariant level)

### 2.1 (a) Verbatim stub carry-forward

**Invariant R1.** For an UPDATE (`old_recdes != NULL`), an attribute that is still `HEAP_UNINIT_ATTRVALUE` when
`heap_attrinfo_set_uninitialized` reaches it **and** whose VOT entry in `old_recdes` has `OR_IS_OOS` set is *not*
read. Instead its old inline stub — head OOS OID, full length, and (post-CBRD-26950) the 4B generation — is copied
into the per-column plan, and its DB_VALUE stays unmaterialized.

Representation: a new `HEAP_ATTRVALUE_STATE` (e.g. `HEAP_OOS_REUSED_ATTRVALUE`, `heap_attrinfo.h:29-37`) or a
`reused` flag on `heap_oos_column_plan` (`heap_file.c:690-695`). The plan struct already holds exactly the two
fields a stub needs (`OID oid`, `DB_BIGINT length`); CBRD-26950 adds the generation to it anyway.

Obligations this creates, all inside `heap_file.c`:

1. **Sizing** — `heap_attrinfo_get_record_payload_size` (`:12224`) must contribute `OR_OOS_INLINE_SIZE` for a reused
   column instead of calling `pr_data_writeval_disk_size` on an unset DB_VALUE (`:12244`).
2. **Layout** — `heap_attrinfo_determine_disk_layout` must treat a reused column as *already OOS*: never a demote
   candidate (skip at `:12355`), never re-added to payload, and it must set `*has_oos = true` so the record header
   flag and the OOS+bigone guard stay correct.
3. **Insert plan** — `heap_attrinfo_prepare_oos_insert_requests` currently keys purely on `plan.selected`
   (`:12633`); it must skip reused columns. Hence `selected` must split into *"write a stub"* vs *"allocate a
   chain"*. The debug assert at `:13176` (`!plan.selected || !OID_ISNULL (&plan.oid)`) remains valid, because a
   reused plan carries a non-null OID.
4. **Stub writer** — `heap_attrinfo_transform_variable_to_disk` (`:13039-13050`) needs **no change**: it already
   writes the stub purely from `plan.oid` / `plan.length`. Under reuse those fields simply come from the old record
   rather than from `oos_insert`. (Post-26950 it also writes the generation — the *old* one, not a fresh one.)
5. **Retry idempotency** — the `S_DOESNT_FIT` grow-and-retry loop (`:13313-13340`) re-enters the column writer.
   The reuse capture must happen once, before that loop, exactly like `heap_attrinfo_insert_to_oos` at `:13305`.
6. **No stranded value consumers.** Anything downstream that reads the *value* of an unassigned column out of this
   attr_info would now see an unmaterialized DB_VALUE. Checked: index maintenance builds its own `index_attrinfo`
   from the old/new recdes (`locator_sr.c:8513-8518`), so it resolves through the attribute layer and is
   unaffected; partition pruning's `attr_info.values[0]` read (`partition.c:4402`) is a b-tree attrinfo, not the
   update attrinfo; MVCC re-evaluation re-runs clear+set (`locator_sr.c:13729-13749`). The spec should state this
   as a checked precondition rather than assume it.

*Adjacent opportunity, not required for dedup*: `locator_update_index` reads the old and new images into two
separate attrinfos (`locator_sr.c:8513-8518`), so an **indexed** OOS-backed column costs two `oos_read`s per UPDATE
today. Under reuse the two stubs are bit-identical whenever the column is unassigned, which is a cheap sufficient
condition for "key unchanged" — worth noting as a follow-up, but out of scope here.

### 2.2 (b) Drop list for the notify record

**Invariant R2.** In the *same* pass, an attribute that **is** assigned and whose `old_recdes` VOT entry has
`OR_IS_OOS` set contributes exactly one `(head OOS OID, expected generation)` entry to the drop list, read out of
the old stub. R1 and R2 are complements over the same loop, so the whole T4 §2 rule ("dropped = the old chain of
every assigned OOS-backed attribute; no comparison, no read") falls out of one traversal of `old_recdes`.

Two properties worth pinning in the spec:

- R2 keys on the **old** stub, not on the new layout. An OOS-backed column assigned a value that now stays inline
  still drops its old chain.
- Assigned columns are otherwise untouched: they carry a real DB_VALUE, and the gate + largest-first loop
  (`:12345-12390`) run exactly as today.

Extraction helper: `heap_recdes_get_oos_oids` (`heap_file.c:28252`; `heap_recdes_get_oos_refs` post-26950) already
walks the VOT and pulls head OIDs out of stubs — the reuse pass needs the same walk but *per attribute index*
rather than whole-record, so the two should share the entry decoder.

**Carrier.** The drop list is produced at the attrinfo layer and consumed at the heap layer, across
`locator_allocate_copy_area_by_attr_info` → `locator_update_force` → `heap_update`. Two viable homes:
a vector on `HEAP_OPERATION_CONTEXT`, or the transaction descriptor / thread entry alongside the OOS publication
state that already travels this way (`thread_p->oos_oids`, `tdes->oos_insert_lsa_queue`, reset together in
`heap_oos_begin_insert_publication`, `heap_oos.cpp:607-620`). The tdes route is precedent-backed and avoids
threading a new parameter through `locator_update_force`.

### 2.3 (c) Where the registration hooks in — and one mechanical constraint

The heap update log record is appended by `heap_log_update_physical` (`heap_file.c:24288`) at exactly three sites:

| Site | Path | Old / new images available there |
|---|---|---|
| `heap_file.c:24145` | `heap_update_home` | `context->home_recdes` / `context->recdes_p` |
| `heap_file.c:23588` | `heap_update_bigone`, old-home update | same |
| `heap_file.c:23906` | `heap_update_relocation`, forward record | `forward_recdes` / `context->recdes_p` |

So the correct vicinity is *immediately before* each of those three calls. That window is already proven to have
the drop set available: the SA_MODE eager cleanup runs in the same window (`:24190` for home, `:23705` for
relocation) and computes exactly the old-minus-new difference there.

**Constraint found in the log layer.** T4 locks the *invariant* ("the notify exists on disk only if the UPDATE
committed"), but a bare `log_append_postpone (RVOOS_NOTIFY_VACUUM, …)` does not deliver it as-is:

1. Postpone is documented and (under `CUBRID_DEBUG`) checked as *page-level* logging — `log_append_postpone`
   rejects `addr->pgptr == NULL` (`log_manager.c:2781-2790`) and requires a non-NULL `redofun`. The
   `RVOOS_NOTIFY_VACUUM` slot currently holds `vacuum_rv_es_nop` for both undo and redo (`recovery.c:899-905`), so
   it is usable but semantically empty.
2. **Vacuum only sees MVCC undo appends.** `vacuum_produce_log_block_data` is driven from the MVCC-op append path
   (`log_append.cpp:1384`), and the vacuum-info block asserts `LOG_MVCC_UNDO_DATA / LOG_MVCC_UNDOREDO_DATA` plus
   `LOG_IS_MVCC_OPERATION` (`log_append.cpp:970-996`), with a hardcoded NULL-VFID exemption for
   `RVES_NOTIFY_VACUUM`. The existing precedent notify is therefore an `log_append_undo_data` with
   `addr = {pgptr = NULL, vfid = NULL, offset = -1}` (`vacuum.c:8081-8103`), consumed in `vacuum_process_log_block`
   at `vacuum.c:3709-3722`. A `LOG_RUN_POSTPONE` record is not in that stream.
3. **Timing.** In `log_commit_local`, `logtb_complete_mvcc` (`log_manager.c:5228`) runs *before*
   `log_tran_do_postpone` (`:5245`), so a postpone action executing at commit no longer has a live MVCCID to stamp
   an MVCC-undo record with.

Three shapes satisfy T4's invariant; the spec must pick one explicitly:

- **(i) Postpone + new vacuum feed.** Register the postpone at update time (which naturally satisfies T4 §3.5's
  "registered before the heap update record"), and teach vacuum to consume the run-postpone form. Most faithful to
  the T4 wording, largest vacuum-side change.
- **(ii) Commit hook before `logtb_complete_mvcc`.** Append the RVES-shaped MVCC-undo notify during commit, ahead
  of `log_manager.c:5228`. Keeps vacuum's consumption path unchanged (one new `rcvindex` branch, as T4 §3 assumes).
  The no-leak argument shifts from "before the heap record" to "before the commit record" — equally sound, and
  arguably simpler. **Recommended** unless vacuum-side changes are cheap.
- **(iii) At-update-time MVCC undo append**, exactly like `RVES_NOTIFY_VACUUM`. Simplest to write, but *not*
  commit-conditional — it re-opens the rollback exposure that T4/CBRD-27237 set out to close. Listed only for
  completeness.

### 2.4 20B stub (CBRD-26950) assumptions

- The reuse copy carries the generation automatically, because it copies the whole stub; no re-stamping, and the
  drop entry is literally the `oos_chain_ref` pair read from the old stub.
- `OR_OOS_INLINE_SIZE` 16→20 moves the profitability floor to `> 20B` — it is a constant reference in both places
  the layout code uses it (`heap_file.c:12330/12334`, `:12356/:12384`), so reuse inherits it for free.
- Reuse must write the **old** generation into the new stub. Writing a fresh one would make the surviving chain
  un-deletable (every future `oos_delete` would no-op), i.e. a permanent leak — the same failure mode CBRD-26950
  documents for a missing replica-side fixup.

---

## 3. Edge checks

### 3.1 An unassigned attribute whose row shrinks below the gate

**Yes — the reused stub stays OOS-backed, and that is fine.** Evidence:

- **No code treats "record ≤ gate ⇒ no OOS".** The gate literal appears at exactly two places, both inside
  `heap_attrinfo_determine_disk_layout` (`heap_file.c:12345` trigger, `:12378` loop stop). Grep over `src/` finds no
  other occurrence — nothing on the read, vacuum, recovery or replication path derives "has OOS" from record size.
- **The read path is stub-driven, not size-driven**: per-attribute via the VOT `OR_IS_OOS` bit
  (`heap_attrvalue_point_variable`, `:10539`) and per-record via `OR_RECORD_HAS_OOS`
  (`object_representation.h:584`, used at `heap_file.c:21360`, `:21508`, `:28248`). A small record carrying a stub
  is fully consistent with both.
- **The one hard invariant moves the safe way.** The only record-level rejection is OOS+bigone
  (`heap_file.c:13295`: `has_oos && heap_is_big_length (inline_size_after_oos)` → `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`).
  Reuse can only make the inline record *smaller or equal* versus today, because today the same column also occupies
  a stub of the same size in the new record. So reuse can never newly trip that guard.
- **Re-inlining would cost more than it saves**: it requires precisely the `oos_read` being removed, plus dropping
  the chain, plus a notify entry — work in exchange for a record that was already correct.
- **PG precedent** (T1): an unchanged value keeps its TOAST pointer regardless of the new row's size; PG re-toasts
  only on assignment.

Behavioral consequence worth one line in OOS-CONTEXT: the gate is a **write-time trigger for newly assigned
values**, not a record-level invariant. A row can sit below the gate and still be OOS-backed; it converges back to
inline the next time that column is assigned. The cost is the same per-SELECT chain read the row already paid
before the UPDATE.

### 3.2 SA_MODE eager path needs no change

`heap_oos_delete_unreferenced` (`heap_oos.cpp:702`) already implements the shared-chain rule:

```c
error_code = heap_recdes_get_oos_oids (old_recdes, old_oos_oids);   /* heap_oos.cpp:710 */
…
error_code = heap_recdes_get_oos_oids (new_recdes, new_oos_oids);   /* :730 */
…
for (const OID &old_oid : old_oos_oids)
  {
    if (oos_oid_in_vector (new_oos_oids, &old_oid))
      {
        /* Same physical OOS referenced by both old and new recdes; keep it. */
        continue;                                                    /* :756-759 */
      }
    error_code = oos_delete (thread_p, oos_vfid, old_oid);           /* :761 */
```

and its header comment already describes the UPDATE case in exactly those terms ("OIDs present in both images …
are preserved", `:678-681`). Under reuse the shared chain appears in both images as a bit-identical stub, so it is
preserved; a dropped chain appears only in the old image and is deleted at update time. Notes:

- The comment's rationale sentence ("OOS OIDs are freshly allocated per heap record and never shared across rows")
  stays literally true: reuse shares a chain across *versions of one row*, and in non-MVCC mode there is no other
  version to share with.
- DELETE still passes `new_recdes == NULL` and deletes everything (`heap_file.c:22929`, `:23275`) — correct: the
  row is going away, and T4 §4 leaves DELETE untouched.
- Post-26950 the extractor becomes `heap_recdes_get_oos_refs` returning `(OID, generation)`; the membership test
  may compare either the OID alone or the whole pair — equivalent here, since a reused stub copies the generation
  verbatim.
- The notify must be emitted only on the `is_mvcc_op` branch, mirroring the existing `!is_mvcc_op` gates at
  `heap_file.c:24190` and `:23705`. Emitting it in SA_MODE would double-delete what the eager path already
  reclaimed.

---

## 4. Idea-B interplay (OOS-CONTEXT §5 B)

**Synergy, no conflict.** Today `oos_insert` fires inside the record transform (`heap_file.c:13305`), which runs in
`locator_allocate_copy_area_by_attr_info` — i.e. *before* the heap operation even starts. That is why the OOS
replication LSAs have to be queued out of band (`tdes->oos_insert_lsa_queue`, filled at `log_manager.c:2255` /
`:2524`, cleared per record at `heap_oos.cpp:618`, popped in `replication.c:461-467`) while the UPDATE's own repl
record deliberately leaves its LSA null "because this function is called before the heap file update"
(`replication.c:438-444`). Idea B moves the insert down to `attrinfo_force` time so the OOS repl log is generated
together with the heap record's repl log (enabling PK inclusion).

Dedup and Idea B pull in the same direction. Dedup *shrinks* Idea B's problem — unassigned attributes produce no
`oos_insert` at all, so there are fewer queued LSAs and fewer OOS repl records to correlate with the heap record.
And both want the same physical outcome: the complete OOS decision for a row (new chains, reused stubs, dropped
chains) materialized in the same window as the heap update log record. If Idea B lands, the reuse plan and the
notify registration end up in one function, which makes T4 §3.5's ordering pin trivial to hold and makes T4 §7's
per-reused-attribute replication marker natural to emit alongside the heap record's repl log, with the PK in hand.
The only sequencing caution: if dedup lands first, the notify registration sits just before
`heap_log_update_physical`; a later Idea B refactor must not reorder it *after* that append.
