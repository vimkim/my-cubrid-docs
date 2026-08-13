# T3 — Cleanup paths under chain reuse: failure scenarios and the two candidate fixes

- ticket: [T3](../tickets/T3-cleanup-paths-under-chain-reuse.md) · map: [CBRD-27230](../map.md)
- verified against worktree `/home/vimkim/gh/cb/CBRD-27230-oos-update-dedup` @ `725a32c6e` (`feat/oos` tip), source read-only
- date: 2026-08-13 · tool: Claude Code (Opus 5)

> **Path correction (do not reuse the ticket's paths).** `vacuum_oos.cpp` lives in `src/query/`, not
> `src/storage/`. `heap_oos_delete_unreferenced` is at `src/storage/heap_oos.cpp:702` (comment block
> starts at `:676`), not `:425`. Everything below cites the tip's real locations.

## Summary

1. All three cleanup paths were audited. Only the **forward-walk** breaks under chain reuse, and it
   breaks as silent data loss: it deletes every chain named by the UPDATE's undo image, including the
   ones the live post-image still points at (`vacuum_oos.cpp:154`, `:286`).
2. The **within-sysop** path (`vacuum_oos.cpp:400`) computes a correct set on its own, but it becomes
   the forward-walk's second victim: it re-deletes an already-freed chain, which is a *hard* error
   there (no probe at all) and stalls the heap slot's vacuum.
3. The **SA_MODE eager** path (`heap_oos.cpp:702`) is already correct for dedup, unchanged — it does
   the old ∖ new set difference the other two lack (`heap_oos.cpp:754-760`).
4. **Option 1 as sketched is refuted.** A reused chain carries the *same* (head OID, generation) in
   the undo image, in the live stub and in the chunk header, so generation equality fires exactly
   when deleting is wrong. Making option 1 work needs either re-stamping on reuse (puts an OOS page
   write back into every UPDATE) or fetching the live heap version (and then the generation is
   unused for this decision).
5. **Option 2 is sound and is the bigger simplification** — it retires the whole "parse a heap record
   out of the log" machinery. Contract in §3. Two things must be pinned: the record must be appended
   *before* the heap update record (else a crash leaks), and rollback must be answered explicitly.
6. Dedup does **not** need the generation id (§4). 26950 stays required, orthogonally, for block-retry
   safety; the notify record should carry `(OID, generation)` so the two compose.
7. **Adjacent finding (§7), needs runtime confirmation:** the current forward-walk looks exposed to
   *rolled-back* UPDATEs, independent of dedup. The CBRD-26668 caveat doc's argument covers the
   in-flight abort window but not the post-abort one.

---

## 1. The three cleanup paths and their failure sequences under chain reuse

### 1.0 The model used throughout

```sql
CREATE TABLE t (id INT PRIMARY KEY, a BIT VARYING, b BIT VARYING);
-- row R: both a and b demoted to OOS -> chain CA (head OID A), chain CB (head OID B)
UPDATE t SET b = <new value> WHERE id = 1;
```

Under CBRD-27230's decided semantics ("unchanged = not assigned in the UPDATE"), `a` is unchanged →
**chain CA is reused**, its 16B stub byte-copied into the new record; `b` is assigned → a fresh chain
CB' is written by `oos_insert`.

- pre-image (undo) references `{A, B}`
- post-image (live) references `{A, B'}`

The ownership invariant that every path below assumes — "each OOS value chain is owned by exactly one
logical heap-record version" (OOS-CONTEXT §3, and the code comment at `heap_oos.cpp:678-681`: *"OOS
OIDs are freshly allocated per heap record and never shared across rows"*) — is exactly what dedup
retires.

---

### 1.1 Forward-walk — `vacuum_forward_walk_oos_delete_atomic` (`src/query/vacuum_oos.cpp:154`)

Fed by `vacuum_forward_walk_reclaim_oos` (`vacuum_oos.cpp:223`), which is called from
`vacuum_process_log_block` at two sites:

| site | rcvindex | undo image is |
|---|---|---|
| `vacuum.c:3591` | `RVHF_UPDATE_NOTIFY_VACUUM` | the pre-image of an MVCC heap UPDATE (`heap_file.c:23590`, `:23819`, `:23908`, `:24145`) |
| `vacuum.c:3730` | `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` | the old forward `REC_NEWHOME` of an UPDATE that relocated a row (`heap_file.c:23866-23872`) |

**Failure sequence (silent data loss):**

1. `UPDATE t SET b = ...` runs. `heap_attrinfo_insert_to_oos` (`heap_file.c:12681`, called at
   `:13305`) writes only CB'; CA is untouched, its stub copied verbatim into the new record.
2. `heap_log_update_physical` appends `RVHF_UPDATE_NOTIFY_VACUUM` with undo = pre-image (`{A, B}`),
   redo = post-image (`{A, B'}`) — e.g. `heap_file.c:24145` for the home case.
3. The transaction commits. The log block eventually passes the visibility gate and is dispatched.
4. Pass 1 of `vacuum_process_log_block` (`vacuum.c:3490-3741`) reaches the record.
   `vacuum_forward_walk_reclaim_oos` passes the `REC_HOME`/`REC_NEWHOME` + `heap_recdes_contains_oos`
   guard (`vacuum_oos.cpp:245`), copies the image to private memory (`:259-270`), and calls
   `heap_recdes_get_oos_oids` (`heap_file.c:28252`), which walks the variable-offset table and
   returns **`{A, B}`**. That function reads the record image and nothing else — it has no notion of
   "still referenced".
5. `vacuum_forward_walk_oos_delete_atomic` sorts the OIDs, opens its own sysop (`vacuum_oos.cpp:171`),
   probes `oos_chunk_exists(A)` (`oos_file.cpp:2236`) → **true**, because CA is alive and occupied,
   and calls `oos_delete(A)` (`oos_file.cpp:2308` → `oos_delete_chain`, `:2153`).
6. `oos_delete_chain` walks `next_chunk_oid` out of each chunk header (`oos_file.cpp:2192-2215`) and
   deletes **every chunk of CA**, then commits the sysop (`vacuum_oos.cpp:196`). No error, no warning.
7. The live row's stub for attribute `a` now points at a freed slot. `SELECT a FROM t WHERE id=1`
   fails inside `oos_read` with the same symptom the CBRD-26950 PoC produced:
   `Internal error: slot N on page P of volume ".../oos..." is not allocated.`

The exists probe is structurally unable to help: it returns *true* precisely because the chain is
alive (`oos_file.cpp:2262-2265` — `S_SUCCESS` ⇒ exists, contents never read).

**Same failure, relocation variant** (`RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`): in
`heap_update_relocation`'s `remove_old_forward` sub-path the old forward `REC_NEWHOME` pre-image is
logged for the forward-walk (`heap_file.c:23861-23872`), listing `{A, B}` while the relocated new
version references `{A, B'}`. Steps 4-7 are identical.

**Multi-chunk amplification:** if CA spans several chunks, step 6 destroys the entire chain, because
`oos_delete_chain` follows `next_chunk_oid` from the *current occupant* of each slot
(`oos_file.cpp:2194`). Same amplification the 26950 report documents in its §2.

---

### 1.2 Within-sysop — `vacuum_heap_oos_delete_within_sysop` (`src/query/vacuum_oos.cpp:400`)

Called only from `vacuum_heap_record`, for `REC_RELOCATION` (`vacuum.c:2522`) and OOS-bearing
`REC_HOME` (`vacuum.c:2597`), inside the caller's sysop (precondition documented at
`vacuum_oos.cpp:385-393`). It deletes every chain referenced by `helper->record`, the record whose
slot is being removed.

Two properties matter:

- Its **own** set is still correct under dedup. It processes a slot whose latest version is
  delete-marked and dead; dedup shares chains only *temporally, within one row*, so no live version
  references them. There is no cross-row sharing to worry about.
- It has **no idempotency guard at all** — unlike the forward-walk it does not call
  `oos_chunk_exists`; it goes straight to `oos_delete` (`vacuum_oos.cpp:416`). A missing chunk is a
  hard error inside `oos_delete_chain` (`oos_file.cpp:2176-2182`).

**Failure sequence (vacuum-stalling hard error, plus a widened 26950 window):**

1. `UPDATE t SET b = ...` on row R, reusing CA. Live version v2 references `{A, B'}`.
2. `DELETE FROM t WHERE id = 1`. v2 gets a delete MVCCID; its stubs are untouched (OOS-CONTEXT §3
   DELETE).
3. Both operations fall into the same vacuum block (or the UPDATE into an earlier one processed in
   the same worker run).
4. Pass 1 runs the forward-walk on the UPDATE's undo image and deletes CA and CB (§1.1 steps 4-6).
5. Pass 2 (`vacuum_heap`, `vacuum.c:3746`) reaches R's slot with `can_vacuum == VACUUM_RECORD_REMOVE`.
   `has_oos` is true (`vacuum.c:2455-2457`), a sysop is opened (`:2464`), the slot is vacuumed, and
   `vacuum_heap_oos_delete_within_sysop` is called with `{A, B'}`.
6. `oos_delete(A)` finds the slot empty → `spage_get_record != S_SUCCESS` → error
   (`oos_file.cpp:2176-2182`) → `log_sysop_abort` (`vacuum.c:2600`) → `vacuum_heap_record` returns the
   error → `vacuum_heap_page` logs "Failed to vacuum object" and `assert_release (false)`
   (`vacuum.c:1794-1799`). The heap slot is **not** reclaimed; debug builds assert.
7. **Worse variant:** if between steps 4 and 5 another transaction's `oos_insert` reused slot `A`
   (OOS pages are ANCHORED and freed slots are re-registered in bestspace immediately —
   `oos_file.cpp:2210`), step 6 does not error. It deletes the **new occupant's** chain. That is
   CBRD-26950's exact mechanism, now reachable *inside a single uninterrupted vacuum run*, with no
   block retry and no crash required.

So dedup does not make this path's logic wrong; it makes the path a downstream casualty, and it
converts one silent loss into either a stuck vacuum or a second silent loss.

---

### 1.3 SA_MODE eager — `heap_oos_delete_unreferenced` (`src/storage/heap_oos.cpp:702`)

Called from four sites, all under `!is_mvcc_op`:

| site | old_recdes | new_recdes |
|---|---|---|
| `heap_file.c:22929` delete relocation | forward `REC_NEWHOME` | `NULL` |
| `heap_file.c:23275` delete home | `context->home_recdes` | `NULL` |
| `heap_file.c:23707` update relocation | forward `REC_NEWHOME` | `context->recdes_p` |
| `heap_file.c:24192` update home | `context->home_recdes` | `context->recdes_p` |

**No failure sequence** — see §5. This path already does the set difference the other two lack:
`oos_oid_in_vector (new_oos_oids, &old_oid)` → `continue` (`heap_oos.cpp:754-760`, helper at
`src/storage/oos_util.cpp:35`). Under dedup, `old ∩ new` is exactly the reused set.

---

## 2. Option 1 — generation-id compare at vacuum time

### 2.1 What the CBRD-26950 stamp actually decides

Per the locked design (`cbrd-26950/CBRD-26950-oos-generation-identity-stamp_01d110e_claude.md`): a
page-local `uint32` counter issues a generation at chunk insert under the page's already-held W latch
(`oos_insert_record_in_fixed_page`); the value is written into **both** the chunk header and the
20-byte heap stub; `oos_delete(vfid, oid, expected_generation)` compares them via
`oos_chain_head_matches` and no-ops on mismatch or absence.

The predicate it computes is **physical identity**:

> *is the chunk now sitting in slot (volid, pageid, slotid) the same chunk that was there when this
> stub was written?*

The predicate dedup needs is **reachability**:

> *is this chain still referenced by a heap-record version that some reader can still reach?*

### 2.2 Why equality answers the wrong question — confirmed

Chain reuse means the new record's stub is a **byte copy** of the old record's stub. That is the whole
point of the feature: no `oos_read`, no `oos_insert`, nothing written to the OOS file. Therefore:

- undo image stub for `a` = `(A, gen_A)`
- live post-image stub for `a` = `(A, gen_A)`
- chunk header at `A` still stores `gen_A` (nothing bumped it)

So `oos_delete(A, expected = gen_A)` **matches** and deletes. Generation equality fires exactly in the
case that must not delete, and mismatch occurs only when the chain was already reclaimed and its slot
reused — i.e. only in the case where there is nothing to do anyway. The suspicion in the ticket is
**confirmed, and the correlation is inverted**, not merely absent.

### 2.3 Rescue 1a — re-stamp the chain head on reuse

Bump the head chunk's generation at UPDATE time and write the new value into the new record's stub.
Then undo image holds `gen_old`, chunk and live stub hold `gen_new` → mismatch → no-op. It is
logically sound, and it composes with 26950's recovery rules (issue from the page counter; replay with
`counter = MAX(counter, chunk_gen)` in `oos_rv_redo_insert`; on rollback the physical undo restores
`gen_old`, matching the restored stub). Multi-version chains (v1→v2→v3 all reusing CA) work: both
older undo images mismatch, and the last dead version is reclaimed through the REMOVE path, which
reads the live stub.

The cost is what kills it: every UPDATE that *keeps* a chain must `pgbuf_fix` that chain's head page
with a W latch, write 4 bytes, log it, and dirty the page — O(#reused chains) page fixes and WAL
records per UPDATE, plus a new heap-data-page-held → OOS-page-fix latch sequence. Dedup's headline
benefit is "an unchanged OOS value costs nothing at UPDATE"; this reduces the saving to "you don't
rewrite the payload", and re-introduces OOS page contention for updates that do not change the value.

### 2.4 Rescue 1b — visit the live heap record (what the JIRA sketch really implies)

To decide "is `A` still referenced", vacuum must obtain the current version of the row. Concretely,
in pass 1 that means:

1. **Find the row.** `log_record_data.{volid,pageid,offset}` gives a heap OID
   (`vacuum.c:3563-3565`, via `heap_rv_remove_flags_from_offset`). That is workable for the
   `RVHF_UPDATE_NOTIFY_VACUUM` home case, but **not uniform**:
   - the `update_old_forward` sub-path logs against the **forward** OID (`heap_file.c:23906`), so the
     live version may have moved and only the home slot knows where;
   - `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` names a slot that has been **physically deleted**, which is
     precisely why it is classified as an MVCC op but *not* a heap op and nothing is collected for it
     (`recovery.h:209-213`). There is no live slot at that OID at all; vacuum would have to route
     home slot → `REC_RELOCATION` → new forward OID, and the home OID is not in the log record.
2. **Fix the heap page(s)** from inside the log walk, which today holds no heap page. This lands on
   top of a known hazard: `vacuum_oos_vfid_lookup` already fixes the heap *header* page
   (`vacuum_oos.cpp:102-116` → `heap_oos_find_vfid`), and the CBRD-26668 caveat review confirmed
   `heap_oos_find_vfid`'s unconditional header fix under held data latches as a real deadlock
   inversion (`cbrd-26668/2026-06-15-CBRD-26668-caveats-rollback-and-latch-inversion.md`, caveat 2).
   Holding a heap data page across it turns that from latent into live. Option 1b therefore has the
   conditional-latch + release-and-retry rework as a prerequisite.
3. **Re-copy the undo image.** Any additional page fix can rotate the worker's log page out from
   under the image — the function already memcpys the image before its first fix for exactly this
   reason, with an observed live corruption (`vacuum_oos.cpp:250-270`: *"the flags byte at this
   address changed from 0x69 to 0x00 across the lookup"*). More fixes, more of this.
4. **Cost.** One extra heap page fix per updated row per block, taken in *log order* — the opposite
   of page order. Pass 2 exists precisely to get page locality: `vacuum_collect_heap_objects`
   (`vacuum.c:3567`) accumulates and sorts before `vacuum_heap` (`vacuum.c:3746`).
5. **Race.** Between reading the live record and deleting, the row can be updated again. That is safe
   in one direction only (a newer version can add chains, and a chain the newer version dropped is
   named by that update's own log record) — safe by argument, not by construction.

And the punchline: **once you hold the live record, the generation id contributes nothing to the
dedup decision.** What you compute is `old_chains ∖ live_chains` — set difference on head OIDs, the
same thing `heap_oos_delete_unreferenced` already does (`heap_oos.cpp:754-760`). The generation is
still needed, but only for 26950's retry safety.

### 2.5 Verdict on option 1

Option 1 as written in JIRA ("look at the generation id, go find it, delete when heap gen == oos
gen") does not work. Its two repairs are (a) re-stamping, which costs an OOS page write per reused
chain per UPDATE and undercuts the feature, or (b) live-version lookup, which is a set difference
that does not use the generation at all and drags in heap page fixes, the `heap_oos_find_vfid` latch
rework, and a non-uniform "find the live version" problem for the relocation cases. The team's prior
judgement ("conceptually verbose and hard to maintain") is supported by the code.

---

## 3. Option 2 — OOS update log: minimal invariant-level contract

### 3.1 What it records

For one logical heap-record UPDATE, per dropped chain: **`(head OOS OID, expected generation)`** —
the pair shape 26950 already introduces as `oos_chain_ref` / `heap_recdes_get_oos_refs`. Plus the OOS
file identity, which vacuum needs anyway and today derives from `log_vacuum.vfid` +
`vacuum_oos_vfid_lookup` (`vacuum_oos.cpp:85`).

The list is **exactly the chains the update dropped** = chains referenced by the pre-image and not by
the post-image. Under the decided "unchanged = not assigned" semantics that is *the old chain of every
assigned OOS-backed attribute*, which the writer already knows at record-transform time — no
comparison, no read.

Not needed: row OID, MVCCID (the block gate supplies visibility), chunk list (`oos_delete_chain`
walks it), record type, or any part of the heap image.

An UPDATE that drops nothing emits nothing — so a non-OOS UPDATE, or an UPDATE that only assigns
inline columns, adds zero log volume. Contrast today, where every `RVHF_UPDATE_NOTIFY_VACUUM` record
in every block pays a full undo-image parse.

### 3.2 Where the record slots into the log machinery

- It must be **MVCC-classified** so it joins the `prev_mvcc_op_log_lsa` chain and reaches a worker at
  all (`log_append.cpp:1389-1416`; `LOG_IS_MVCC_OPERATION`, `mvcc.h:271-277`).
- It must **not** be `LOG_IS_MVCC_HEAP_OPERATION`, or `vacuum_process_log_block` would try to
  `vacuum_collect_heap_objects` a slot for it (`vacuum.c:3560-3567`).
  `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` is the existing precedent for that combination
  (`recovery.h:209-213`).
- **`RVOOS_NOTIFY_VACUUM` (=139) already exists, has no emitter, and is already a member of
  `LOG_IS_MVCC_OPERATION` (`mvcc.h:275`).** Its `recovery.h:204-207` TODO says to either give it a
  real purpose or retire it before the develop merge. This is that purpose — no new rcvindex, no
  renumbering.
- Recovery handlers: no-ops both ways. Writing the record changes no page; like `RVES_NOTIFY_VACUUM`
  it is a pure notification (`vacuum.c:3709`; emitter `vacuum.c:8103`).
- Consumer: a new `else if (rcvindex == RVOOS_NOTIFY_VACUUM)` branch in `vacuum_process_log_block`,
  running in **its own sysop** exactly like `vacuum_forward_walk_oos_delete_atomic`
  (`vacuum_oos.cpp:171`/`:196`), because pass 1 has no enclosing sysop (asserted at `vacuum.c:3740`).
  The REMOVE path keeps the opposite contract (`vacuum_oos.cpp:385-393`). No new nesting.

### 3.3 Idempotency under vacuum block re-run — the 26950 T1–T7 timeline, replayed

| step | with the OOS update log |
|---|---|
| T1 | `UPDATE R1` drops chain `V\|P\|S`. An `RVOOS_NOTIFY_VACUUM` naming `(V\|P\|S, gen)` is appended in block B. |
| T2 | B's MVCCIDs fall below the visibility threshold; master dispatches B, vacuum data marks it IN_PROGRESS. |
| T3 | Worker reads the notify record, deletes `V\|P\|S`, commits the per-record sysop. Slot freed and re-registered in bestspace (`oos_file.cpp:2210`). **`start_lsa` still does not advance** (`vacuum.c:3766` TODO); no per-record progress note. |
| T4 | Another transaction's `oos_insert` reuses `V\|P\|S`. Under 26950 the new chunk gets a **different** generation (page-local monotone counter, replayed with MAX in `oos_rv_redo_insert`). |
| T5 | The worker is interrupted before finishing B — shutdown (`vacuum.c:3494`), mid-block error, or crash → `set_interrupted` (`vacuum.c:3928`). |
| T6 | Restart: IN_PROGRESS blocks are reloaded as AVAILABLE+INTERRUPTED with `start_lsa` unchanged (`vacuum.c:4403`). |
| T7 | B is re-run from `data->start_lsa` (`vacuum.c:3490`). The same immutable notify record yields the same `(V\|P\|S, gen)`. `oos_delete` compares the stored generation → **mismatch → no-op.** |

**Conclusion: option 2 supplies no idempotency of its own.** The notify record is exactly as immutable
and exactly as re-read as the undo image it replaces, so it inherits the CBRD-26950 exposure
unchanged. Its retry safety comes entirely from the 26950 identity check. Without 26950 the consumer
would need at minimum today's `oos_chunk_exists` probe (`vacuum_oos.cpp:179`), which the 26950
verification already refuted as an identity test (its §3 row F: *"`oos_chunk_exists` returns true on
`S_SUCCESS` unconditionally — it does not even read the contents"*).

This should be stated in the spec as a dependency, not left implicit: **CBRD-27230 option 2 and
CBRD-26950 are orthogonal and both are required.**

### 3.4 Rollback of the updating transaction

The requirement: the UPDATE is undone, the pre-image is the live row again and still references the
dropped chains → the log must not cause their deletion.

A plain log record written at UPDATE time **does not satisfy this by itself.** It survives rollback
verbatim, and vacuum reaches it after the aborting transaction's MVCCID retires. Three ways to close
it:

- **(a) Postpone-based emission.** Append via `log_append_postpone` so it materialises only on commit
  (the same mechanism `heap_log_delete_physical` uses for `RVHF_MARK_REUSABLE_SLOT`,
  `heap_file.c:23396`). Cleanest answer to rollback. Cost: the notification's LSA moves to commit
  time, so it lands in a later block (harmless — the block gate is MVCCID-based, not LSA-based), and
  the commit path grows work.
- **(b) Vacuum-side liveness guard.** Keep the record where it is and have the consumer drop entries
  the live record still references — which is option 1b's set difference again, with all of §2.4's
  costs.
- **(c) Inherit today's semantics.** Only defensible if §7 resolves as a non-issue; it is not
  currently established that it does.

Recommendation: **(a)**, and write it into the contract as an invariant — *the notify record exists on
disk only if the UPDATE committed.* This is also the one place where option 2 can be made strictly
safer than the status quo rather than merely equivalent.

### 3.5 Crash window between the heap update and the notify record

Both are appended in the same transaction with no intervening flush, so the durable outcomes are
"both" or "notify missing". The two failure directions are asymmetric:

- **notify present, heap update undone by recovery** → the rollback case of §3.4.
- **heap update durable, notify missing** → the dropped chains are never reclaimed: a permanent leak
  of exactly those chains, invisible to every tool (`spacedb` folds `FILE_OOS` into heap accounting —
  OOS-CONTEXT §5).

Invariant that removes the second case for free: **append the notify record *before* the heap update
record** in the same transaction, so "heap update durable ⇒ notify durable" holds by LSA ordering. It
costs nothing — at the point `heap_log_update_physical` is reached, the new record image (hence the
reused-vs-new stub decision) is already built, so the dropped set is already known. If §3.4(a) is
adopted the ordering constraint applies to the postpone append instead, and the commit-time
materialisation preserves it.

### 3.6 Does DELETE also move to this scheme? — No

DELETE keeps the REMOVE path, unchanged. A DELETE drops no chain: the row's last version keeps its
stubs and stays on the page until vacuum removes the slot (OOS-CONTEXT §3 DELETE), so the chains are
reclaimed by `vacuum_heap_oos_delete_within_sysop` inside the *same sysop* as the slot removal
(`vacuum.c:2519-2530` for `REC_RELOCATION`, `vacuum.c:2586-2605` for `REC_HOME`). That path re-reads
the live record and is naturally gated by its MVCC header, which is why CBRD-26950 explicitly scopes
the REMOVE path out (its §5 Q5). Emitting a notify record for DELETE would create a second, ungated
deleter for the same chains → guaranteed double delete.

So: **UPDATE → notify record. DELETE → REMOVE path, untouched.**

### 3.7 What happens to the forward-walk for UPDATEs? — Removed, not gated

Its entire input is superseded, and leaving both alive would double-delete every dropped chain.
Concretely, option 2 deletes:

- `vacuum.c:3589-3592` — the `RVHF_UPDATE_NOTIFY_VACUUM` → `vacuum_forward_walk_reclaim_oos` call,
  replaced by the `RVOOS_NOTIFY_VACUUM` branch.
- `vacuum.c:3724-3731` — the `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` branch. The relocation case is just
  another UPDATE and its dropped chains are in the same notify record. The rcvindex then has no
  remaining purpose: `heap_file.c:23866-23870` reverts to plain `RVHF_DELETE`, and its
  `LOG_IS_MVCC_OPERATION` clause (`mvcc.h:276`) and its "MVCC op but not heap op" special case
  (`recovery.h:209-213`) go with it.
- `vacuum.c:4233-4241` — both OOS tags leave the undo-image unpacking whitelist. Vacuum stops needing
  heap undo images for OOS entirely.
- `src/query/vacuum_oos.cpp:205-319` — `vacuum_forward_walk_reclaim_oos` in full, and with it: the
  `REC_HOME`/`REC_NEWHOME` type guard added because a forwarding-pointer undo image would be
  misparsed as an MVCC header (`:236-245`), the private-copy dance against log page rotation
  (`:250-270`), the `VACUUM_OOS_VFID_NONE` → `abort()` instrumentation (`:305-316`), and the
  `heap_recdes_get_oos_oids` call on log bytes — whose bounds handling is documented as not fully
  supporting legacy records without `OR_VAR_BIT_LAST_ELEMENT` (`heap_file.c:28265-28267`).

In my reading **this deletion of machinery is option 2's strongest argument, larger than the dedup
correctness win itself**: it removes the only place in the engine that reconstructs a heap record
image out of raw log bytes for a non-recovery purpose.

Retained by option 2 (unchanged): `vacuum_heap_oos_delete_within_sysop`, `vacuum_oos_vfid_lookup`,
`vacuum_oos_find_vfid_for_heap_record`, and the eager SA_MODE path.

---

## 4. Does dedup need the generation id at all under option 2?

**No — not for the dedup decision.** The drop list is computed by the *writer*, which knows exactly
which attributes were assigned. Nothing at vacuum time re-derives ownership, so nothing has to tell
"dead" from "shared". The question option 1 could not answer simply stops being asked.

**Yes — the stamp stays required, for CBRD-26950, orthogonally.** The notify record is immutable and
re-read on block retry (§3.3 T1–T7), so `oos_delete` still needs to refuse to delete a chunk that is
no longer the chain the record named. The two predicates are cleanly separated:

| question | answered by |
|---|---|
| which chains did this UPDATE drop? | the writer, at UPDATE time → the notify record (CBRD-27230) |
| is the chunk at this OID still that chain? | the page-local generation stamp (CBRD-26950) |

One coupling, in option 2's favour: the notify record should carry `(head OID, generation)` rather
than a bare OID, so the 26950 check has an expected value. That is the same `oos_chain_ref` shape the
26950 design already introduces for `heap_recdes_get_oos_refs`, so the two compose without friction —
and after option 2, the identity check becomes the *only* barrier between a retried block and live
data, which strengthens rather than weakens 26950's priority.

Note also: under **option 1b** the generation would *still* not answer the dedup question (§2.4); it
is not an argument for either option.

---

## 5. Fit-check: does the SA_MODE eager path already give correct dedup behaviour?

**Yes, unchanged.** `heap_oos_delete_unreferenced` (`heap_oos.cpp:702`) extracts both images'
references (`:710`, `:730`) and skips any old OID present in the new set
(`:756` — `oos_oid_in_vector`, `src/storage/oos_util.cpp:35`). Under dedup `old ∩ new` is exactly the
reused set → reused chains preserved, dropped chains deleted. Its own doc comment already anticipates
this: *"OIDs present in both images (same physical OOS referenced before and after) are preserved"*
(`heap_oos.cpp:679-681`).

Checks performed:

- **Head-OID equality is exact here.** A reused chain is bit-identical (dedup copies the stub), so
  equality is not an approximation. A false positive — a *new* chain landing on the OID of a
  *different* old chain — is impossible: `heap_attrinfo_insert_to_oos` runs during the record
  transform (`heap_file.c:13305`), strictly before `heap_update_logical` frees anything, so the old
  chain still occupies its slot when the new one is allocated.
- **All four call sites pass the right images.** Updates pass `context->recdes_p`
  (`heap_file.c:23707`, `:24192`); deletes pass `NULL` (`:22929`, `:23275`), which stays correct
  because a DELETE drops everything.
- **`heap_update_bigone` has no eager call** — safe only because OOS + `REC_BIGONE` is rejected at
  write time with `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` (`heap_file.c:13295`, CBRD-26937). Dedup does not
  change that; the guard runs before any OOS write.
- **`heap_update_relocation` re-reads `forward_recdes` after the eager delete** (`heap_file.c:23851`)
  when the page was unfixed. Harmless: the re-read can only lose an INSID removed by vacuum, and this
  branch is `!is_mvcc_op` (no vacuum).

Two pre-existing wrinkles to carry into the spec, neither caused by dedup:

1. The `!is_mvcc_op` gate also fires in SERVER_MODE for MVCC-disabled (catalog) classes, so despite
   the "SA_MODE" wording in its diagnostics this code runs server-side too (`heap_oos.cpp:686-690`).
2. It is a **hard-error** path today: a missing chunk propagates an error (`heap_oos.cpp:761-772`),
   and the caller must abort the transaction. CBRD-26950 changes absence/mismatch to a no-op (its
   Remarks 2), which is what makes it retry-tolerant. Dedup adds no new reason to delete twice here,
   so this is purely a 26950 interaction.

If 26950 lands first, this path should compare `(OID, generation)` pairs rather than bare OIDs. With
dedup the pair is identical for reused chains, so the comparison stays exact.

---

## 6. A third option worth putting on the table: set difference in pass 2

Both option 1b and option 2(b) converge on the same computation — `old_chains ∖ live_chains` — and
§2.4 showed the expensive part is *getting the live record in pass 1*. But vacuum already fetches
that record in **pass 2**: `vacuum_heap_record` runs with the home page latched and
`helper->record` in hand (`vacuum.c:2455-2457`), which is exactly where
`vacuum_heap_oos_delete_within_sysop` already reads OOS references.

Shape: pass 1 stops deleting and instead attaches the undo image's chain list to the collected heap
object (`vacuum_collect_heap_objects`, `vacuum.c:3567`); pass 2 computes the difference against the
live record under the latch it already holds.

Properties, for the record:

- dedup-safe by construction (shared chains are in `live`);
- **rollback-safe for free** — after a rollback the live record *is* the pre-image, so the difference
  is empty and nothing is deleted, which neither option 1 nor a naive option 2 gets;
- page-local (no extra fixes, correct visit order);
- still needs 26950 for retry safety (a re-run recomputes the same non-empty difference);
- costs memory proportional to `n_heap_objects` per block, and needs a defined ordering against the
  REMOVE deletes inside `vacuum_heap_record`;
- does **not** solve the `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` case, where the slot named by the log
  record no longer exists (`recovery.h:209-213`) — that case still needs either the notify record or a
  home-slot route.

It is strictly more complex than option 2 and keeps the log-image parsing machinery option 2 deletes,
so I do not recommend it over option 2. It is listed because it is the honest "make option 1 work"
end state, and because its rollback property is the cleanest argument for why option 2 must adopt
§3.4(a).

---

## 7. Adjacent finding — the forward-walk and *rolled-back* UPDATEs (needs runtime confirmation)

This is independent of dedup, but it determines what §3.4 must promise, so it belongs here.

The forward-walk acts on log content alone with no re-validation against current state. Every other
vacuum consumer re-reads the live structure and no-ops when the operation was rolled back — the heap
path says so in as many words: *"Object cannot be vacuumed. Most likely it was already vacuumed by
another worker or it was rollbacked and reused"* (`vacuum.c:1812-1814`).

What I verified on this tip:

1. Log records join the `prev_mvcc_op_log_lsa` chain at **append** time
   (`log_append.cpp:1389-1416`); rollback appends compensation records and never unlinks the original.
2. `vacuum_process_log_record` (`vacuum.c:4079-4302`) has **no** commit/abort filter. It gates only on
   dropped files (`:4220`) and rcvindex (`:4233-4241`).
3. On abort, `heap_rv_undo_update` (`recovery.c:352-357`) physically restores the pre-image as the
   live record — byte-identical stubs — while the new chains are removed by `RVOOS_INSERT`'s undo
   (`recovery.c:875-880`, `oos_rv_redo_delete`).
4. The existing analysis
   (`cbrd-26668/2026-06-15-CBRD-26668-caveats-rollback-and-latch-inversion.md`, caveat 1) concludes
   "safe by design" from the visibility gate plus abort ordering (`log_rollback` before
   `logtb_complete_mvcc`). That argument correctly shows vacuum cannot run **while** the abort is in
   flight. It does not cover the window **after** the abort completes: the MVCCID then retires,
   `oldest_visible` advances, the block becomes eligible, and the same undo image is still there. The
   doc's stated conclusion — *"the writing transaction has committed"* — does not follow from the
   gate; an aborted transaction's MVCCID retires the same way.

If that reading is right, the sequence is:

1. `UPDATE t SET b = ... WHERE id = 1;` (OOS row) — new chains written, `RVHF_UPDATE_NOTIFY_VACUUM`
   appended with undo = pre-image.
2. `ROLLBACK;` — pre-image restored as the live record; new chains removed by undo. The pre-image's
   chains are live **and referenced**.
3. The aborted MVCCID retires; the block passes the gate and is dispatched.
4. The forward-walk parses the undo image and deletes the pre-image's chains — i.e. the live row's
   chains. Silent loss, same symptom as CBRD-26950.

I could not find a mechanism that prevents step 4, but I did **not** run it. It would not have shown
up in the CBRD-26950 PoC, whose workload contains no rollbacks. Suggested check (cheap, debug build,
no source change): create an OOS row, commit; `UPDATE` it, `ROLLBACK`; drive enough further log
traffic to publish and vacuum the block; `SELECT` the row. Under my reading it fails with
`slot ... is not allocated`.

Bearing on this ticket: if confirmed, it is a separate CBRD ticket, but it also means option 2 must
adopt §3.4(a) (commit-conditional emission) rather than "inherit today's semantics", and it makes
§6's rollback property a genuine tiebreaker rather than a nicety.

---

## 8. Sources

- Source, read-only: `/home/vimkim/gh/cb/CBRD-27230-oos-update-dedup` @ `725a32c6e` —
  `src/query/vacuum_oos.cpp`, `src/query/vacuum.c`, `src/storage/heap_oos.cpp`,
  `src/storage/oos_file.cpp`, `src/storage/oos_file.hpp`, `src/storage/oos_util.cpp`,
  `src/storage/heap_file.c`, `src/transaction/recovery.{h,c}`, `src/transaction/log_append.cpp`,
  `src/transaction/log_manager.c`, `src/transaction/mvcc.h`.
- `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md` §3, §4, §5.
- `cbrd-26950/2026-07-31-CBRD-26950-vacuum-oos-slot-reuse-verification.md` (T1–T7 timeline, §3 A–H,
  §5 Q5, §5-1).
- `cbrd-26950/CBRD-26950-oos-generation-identity-stamp_01d110e_claude.md` (locked stamp design).
- `cbrd-26668/2026-06-15-CBRD-26668-caveats-rollback-and-latch-inversion.md` (both caveats; §7 above
  revisits caveat 1).
