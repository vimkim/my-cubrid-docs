# T1 — PostgreSQL TOAST unchanged-value reuse on UPDATE

- ticket: [T1](../tickets/T1-pg-toast-unchanged-value-reuse.md)
- map: [CBRD-27230 OOS UPDATE dedup](../map.md)
- sources: PostgreSQL `master` (Copyright 2000-2026), fetched 2026-08-13 from `raw.githubusercontent.com/postgres/postgres`. No local PG checkout exists under `/home/vimkim/gh`. Line numbers are from that fetch and may drift; function names are the stable citation.
- files read: `src/backend/access/table/toast_helper.c`, `src/backend/access/common/toast_internals.c`, `src/backend/access/heap/heaptoast.c`, `src/backend/access/heap/heapam.c`, `src/backend/access/heap/heapam_visibility.c`, `src/backend/commands/vacuum.c`, `src/include/varatt.h`, `src/include/utils/snapshot.h`

## Summary

1. Reuse is decided in `toast_tuple_init` (`toast_helper.c`) by a **`memcmp` of the on-disk TOAST pointer itself** — not the value, not a pointer-identity test, not an "attribute assigned" flag. Equal pointer bytes ⇒ same `va_valueid` ⇒ reuse the chunks untouched.
2. Reuse is the **default outcome**, not an optimization: an unassigned column arrives in the new tuple carrying the *same 18 pointer bytes* copied from the old tuple, so the memcmp trivially matches and the column is marked `TOASTCOL_IGNORE`.
3. Ownership is **"the newest row version owns the chunks."** Old row versions never cascade. Chunks are released exactly once, by the transaction that either changes the column (`toast_tuple_cleanup`) or deletes the row (`heap_delete` → `heap_toast_delete`).
4. Toast-table MVCC does **not** provide ownership. It provides only the **grace period** between release and physical removal: `toast_delete_datum` sets `xmax` via `simple_heap_delete`, and the chunks survive until the toast table's own VACUUM finds that `xmax` below the removal horizon.
5. Toast reads deliberately **ignore `xmax`** (`HeapTupleSatisfiesToast`), so an old row version can still detoast a chunk that has already been logically deleted.
6. Crash-safety is ordinary WAL + MVCC rollback; there is **no idempotence** — `simple_heap_delete` raises `"tuple already updated by self"` on a double release. PG avoids that by the one-owner discipline, not by defensive coding.
7. PG needs **no generation id and no persisted update log**. `TOASTCOL_NEEDS_DELETE_OLD` is an in-memory "list of chains this UPDATE dropped" that is consumed microseconds later in the same call.
8. For OOS: parts (1)–(3) transfer directly. Part (4) does not — but OOS does not need per-chunk MVCC, because its cleanup is *already* gated on the global MVCC horizon by vacuum scheduling.
9. What OOS genuinely lacks is the **ownership half**: PG's release decision is made synchronously by the transaction holding both images; OOS defers it to vacuum, which sees only the undo image.
10. Persisting `TOASTCOL_NEEDS_DELETE_OLD` across that time gap is exactly the map's preferred **option 2 (OOS update log)**.

---

## 1. Unchanged detection — the exact rule

The whole decision lives in `toast_tuple_init` (`src/backend/access/table/toast_helper.c:59-98`), which runs once per attribute at the top of every toast pass. For an UPDATE (`ttc_oldvalues != NULL`):

```c
			/*
			 * If the old value is stored on disk, check if it has changed so
			 * we have to delete it later.
			 */
			if (att->attlen == -1 && !ttc->ttc_oldisnull[i] &&
				VARATT_IS_EXTERNAL_ONDISK(old_value))
			{
				if (ttc->ttc_isnull[i] ||
					!VARATT_IS_EXTERNAL_ONDISK(new_value) ||
					memcmp(old_value, new_value,
						   VARSIZE_EXTERNAL(old_value)) != 0)
				{
					/*
					 * The old external stored value isn't needed any more
					 * after the update
					 */
					ttc->ttc_attr[i].tai_colflags |= TOASTCOL_NEEDS_DELETE_OLD;
					ttc->ttc_flags |= TOAST_NEEDS_DELETE_OLD;
				}
				else
				{
					/*
					 * This attribute isn't changed by this update so we reuse
					 * the original reference to the old value in the new
					 * tuple.
					 */
					ttc->ttc_attr[i].tai_colflags |= TOASTCOL_IGNORE;
					continue;
				}
			}
```

So the rule is a three-part guard, and **reuse is the `else` branch** — the code is written to detect *change*, and treats "not changed" as the fallthrough:

| Test | Meaning |
|---|---|
| `att->attlen == -1 && !ttc_oldisnull[i] && VARATT_IS_EXTERNAL_ONDISK(old_value)` | there is an old on-disk TOAST pointer at all; otherwise nothing to reuse or delete |
| `ttc_isnull[i]` | new value is NULL ⇒ changed |
| `!VARATT_IS_EXTERNAL_ONDISK(new_value)` | new value is inline/compressed/in-memory-external ⇒ changed |
| `memcmp(old_value, new_value, VARSIZE_EXTERNAL(old_value)) != 0` | pointer bytes differ ⇒ changed |

**It is a byte comparison of the TOAST pointer, not of the value and not of the C pointer.** `VARSIZE_EXTERNAL(PTR)` is `VARHDRSZ_EXTERNAL + VARTAG_SIZE(VARTAG_EXTERNAL(PTR))` (`varatt.h:333-335`); for `VARTAG_ONDISK` that is 2 header bytes plus `sizeof(varatt_external)` = 16, so the memcmp covers the tag byte and all four fields of

```c
typedef struct varatt_external
{
	int32		va_rawsize;		/* Original data size (includes header) */
	uint32		va_extinfo;		/* External saved size (without header) and
								 * compression method */
	Oid			va_valueid;		/* Unique ID of value within TOAST table */
	Oid			va_toastrelid;	/* RelID of TOAST table containing it */
} varatt_external;
```

Equality therefore implies identical `va_valueid` **and** `va_toastrelid` **and** identical size/compression metadata. That is stronger than needed for chunk identity, and deliberately so: it also rejects a pointer that names the same chunks through a different toast relation (the CLUSTER/table-rewrite case, see §3).

**Why this is equivalent to "attribute not assigned."** PG has no "assigned" flag at this layer — by the time `heap_update` calls the toaster it holds a fully-formed new `HeapTuple` (`heapam.c:3965`), with no record of which columns the executor actually touched. But an unassigned varlena column is reconstructed by copying the old datum verbatim, and for an already-toasted column that datum *is* the 18-byte pointer. So the memcmp is a content-addressed re-derivation of "not assigned": cheap (18 bytes, no I/O, no detoast) and conservative in the safe direction — a false "changed" costs a rewrite, never corruption.

Note the consequence marked in the `TOASTCOL_IGNORE` path: `continue` skips the rest of the loop body, so the attribute is never detoasted, never re-measured (`tai_size` stays 0), and is invisible to `toast_tuple_find_biggest_attribute` (`toast_helper.c:198-199`, which skips `TOASTCOL_IGNORE`). A reused value can never be selected for re-externalization in this tuple. The comment at `toast_helper.c:130-136` states the resulting invariant for everything that reaches the later code:

```c
			/*
			 * We took care of UPDATE above, so any external value we find
			 * still in the tuple must be someone else's that we cannot reuse
			 * (this includes the case of an out-of-line in-memory datum).
```

## 2. Chunk lifetime ownership

### Who deletes, and when

There are exactly three call sites of `toast_delete_datum` (`toast_internals.c:376`):

| Caller | Path | Trigger |
|---|---|---|
| `toast_tuple_cleanup` (`toast_helper.c:299-310`) | UPDATE that **changed** the column | `TOASTCOL_NEEDS_DELETE_OLD` set in §1 |
| `toast_delete_external` (`toast_helper.c:317-337`) | DELETE, via `heap_toast_delete` | every on-disk external attr in the dying tuple |
| same, `is_speculative = true` | `heap_abort_speculative` (`heapam.c:6512`) | INSERT ... ON CONFLICT backing out |

The load-bearing negative result: **`heap_update` never calls `heap_toast_delete`.** Its only toast call is

```c
			if (need_toast)
			{
				/* Note we always use WAL and FSM during updates */
				heaptup = heap_toast_insert_or_update(relation, newtup, &oldtup, 0);
```

(`heapam.c:3962-3966`), which releases only the per-attribute subset chosen in §1. `heap_delete` by contrast cascades unconditionally (`heapam.c:3171-3184`):

```c
	/*
	 * If the tuple has toasted out-of-line attributes, we need to delete
	 * those items too.  We have to do this before releasing the buffer
	 * because we need to look at the contents of the tuple, but it's OK to
	 * release the content lock on the buffer first.
	 */
	...
	else if (HeapTupleHasExternal(&tp))
		heap_toast_delete(relation, &tp, false);
```

Put together, the ownership rule is **the newest row version owns the chunks**. An old version created by an UPDATE holds a *borrowed* pointer: it will never itself release those chunks, no matter how it dies. Ownership migrates forward on every reuse, and is finally surrendered either when some later UPDATE replaces the column or when the row is deleted.

This is worth stating plainly because it is the part most easily mistaken for "MVCC handles it": **MVCC is not what decides who deletes.** The static call graph decides that, and it decides it the same way whether or not the chunks are shared.

### What MVCC actually contributes

Chunks are ordinary heap tuples in the toast table, so `toast_delete_datum`'s inner loop is a normal MVCC delete (`toast_internals.c:420-429`):

```c
	while ((toasttup = systable_getnext_ordered(toastscan, ForwardScanDirection)) != NULL)
	{
		/*
		 * Have a chunk, delete it
		 */
		if (is_speculative)
			heap_abort_speculative(toastrel, &toasttup->t_self);
		else
			simple_heap_delete(toastrel, &toasttup->t_self);
	}
```

`simple_heap_delete` sets `xmax` on each chunk row; the bytes stay on the page. MVCC's contribution is precisely the interval between that `xmax` and physical reclamation, and it is exact for free: **the `xmax` stamped on the chunks is the same xid that stamped `xmax` on the main-table row version that surrendered them.** Both therefore cross the removal horizon at the same instant. No coordination, no cross-table bookkeeping.

Reads over that interval are deliberately permissive. `HeapTupleSatisfiesToast` (`heapam_visibility.c:451-479`) never looks at `xmax` at all:

```c
 * This is a simplified version that only checks for VACUUM moving conditions.
 * It's appropriate for TOAST usage because TOAST really doesn't want to do
 * its own time qual checks; if you can see the main table row that contains
 * a TOAST reference, you should be able to see the TOASTed value.  However,
 * vacuuming a TOAST table is independent of the main table, and in case such
 * a vacuum fails partway through, we'd better do this much checking.
```

It checks only that `xmin` is committed and not an aborted speculative insertion, then `return true`. So a repeatable-read transaction reading a dead old row version detoasts a chunk whose `xmax` its snapshot cannot see — and that is intended, not a hole. The guarantee is not "the chunk is visible to my snapshot" but "the chunk has not yet been *removed*," and removal is what the horizon governs.

Concretely, for the shared case this map cares about:

```
T1: UPDATE t SET a = 1            -- b (toasted, chunk C) unassigned
      V0.xmax = T1                -- V0 keeps pointer to C
      V1 created, points to C     -- reuse; C untouched, no xmax
S:  BEGIN REPEATABLE READ         -- snapshot predates T1's commit; can see V0
T2: DELETE FROM t
      V1.xmax = T2
      heap_toast_delete -> C.xmax = T2
S:  SELECT b ...                  -- reads V0, detoasts C
                                  -- C.xmax = T2 invisible to S, and
                                  -- HeapTupleSatisfiesToast ignores xmax anyway
VACUUM (toast): cannot remove C while T2 >= horizon, i.e. while S is alive
```

### Main-table VACUUM vs toast-table VACUUM

They are separate relations with separate vacuums, and — importantly — **main-table VACUUM does not cascade to toast**. Removing a dead heap tuple never touches a chunk; had it tried, the shared-chunk case above would be exactly where it broke. The toast table is merely vacuumed *alongside* its parent as a scheduling convenience (`vacuum.c:2348-2368`):

```c
	/*
	 * If the relation has a secondary toast rel, vacuum that too while we
	 * still hold the session lock on the main table.  Note however that
	 * "analyze" will not get done on the toast table. ...
	 */
	if (toast_relid != InvalidOid)
	{
		...
		vacuum_rel(toast_relid, NULL, toast_vacuum_params, bstrategy,
				   isTopLevel);
	}
```

This recursion is suppressible (`PROCESS_TOAST`, `vacuum.c:267-268, 2284-2287`) and skipping it is merely a space leak, never a correctness problem — further evidence that the toast table's own horizon, not the parent's vacuum, is what holds the line.

## 3. Deletion when the column *is* changed

The release is deferred to the very end of the toast pass, in `toast_tuple_cleanup` (`toast_helper.c:296-310`):

```c
	/*
	 * Delete external values from the old tuple
	 */
	if ((ttc->ttc_flags & TOAST_NEEDS_DELETE_OLD) != 0)
	{
		...
			if ((attr->tai_colflags & TOASTCOL_NEEDS_DELETE_OLD) != 0)
				toast_delete_datum(ttc->ttc_rel, ttc->ttc_oldvalues[i], false);
	}
```

Note the shape: `toast_tuple_init` *marks*, the compression/externalization rounds run, and `toast_tuple_cleanup` *acts*. The set of flags is, functionally, an in-memory update log — "here are the chains this UPDATE dropped" — with a lifetime of one function call. This matters for the transfer assessment below.

Ordering inside `heap_update`: the toaster runs at `heapam.c:3965`, after the old tuple has been locked and its visibility flags adjusted, and after the concurrent-update checks have already succeeded — but before the new tuple is placed. So the release cannot be stranded by a `TM_Updated` outcome; the only way out after this point is transaction abort.

**Crash-safety.** There is no bespoke mechanism. The chunk deletes are ordinary WAL-logged MVCC deletes on the toast heap, so:

- Abort or crash ⇒ the `xmax` on the chunks is an aborted xid ⇒ chunks are live again, and the old row version they belong to is live again. The two recover in lockstep because they carry the same xid.
- The *new* chunks written by `toast_save_datum` in the same aborted transaction carry an aborted `xmin` ⇒ dead on arrival, reclaimed by the toast table's next VACUUM. `HeapTupleSatisfiesToast`'s `HeapTupleHeaderXminInvalid` / `!TransactionIdIsValid(...GetXmin(...))` checks (`heapam_visibility.c:462-474`) keep them from ever being read.

**Idempotence: PG does not have it, and does not need it.** `simple_heap_delete` (`heapam.c`) hard-errors rather than tolerating a repeat:

```c
		case TM_SelfModified:
			/* Tuple was already updated in current command? */
			elog(ERROR, "tuple already updated by self");
```

A second release of the same `va_valueid` in the same transaction would find the chunks again — `HeapTupleSatisfiesToast` ignores the `xmax` it just set — and abort the transaction. Safety comes entirely from the one-owner discipline of §2: exactly one row version is ever in a position to call `toast_delete_datum` for a given chunk set. **This is the property that chain reuse must not break, in PG or in OOS.**

One related mechanism, easily mistaken for reuse, is worth separating out. `toast_save_datum` can adopt an existing `va_valueid` (`toast_internals.c:222-261`), but only when `rel->rd_toastoid` is set — i.e. during CLUSTER / VACUUM FULL / table rewrite:

```c
				/*
				 * There is a corner case here: the table rewrite might have
				 * to copy both live and recently-dead versions of a row, and
				 * those versions could easily reference the same toast value.
				 * When we copy the second or later version of such a row,
				 * reusing the OID will mean we select an OID that's already
				 * in the new toast table.  Check for that, and if so, just
				 * fall through without writing the data again.
```

This is a *different* dedup — cross-version sharing preserved through a rewrite, detected with a `SnapshotAny` existence probe (`toastrel_valueid_exists`, deliberately counting dead rows too) rather than by comparing images. It is not on the UPDATE path and does not participate in §1's decision. It is, however, direct confirmation from the PG source that **multiple heap versions legitimately share one toast value** and that PG considers *not* sharing them the bug ("wasting space; and what's worse, the copies belonging to already-deleted heap tuples would not be reclaimed by VACUUM").

---

## Transfer assessment for CUBRID OOS

Baseline for the comparison (OOS-CONTEXT.md §3–4): OOS chunk records are physical slotted-page records with **no MVCC header**; UPDATE always allocates fresh chains (`heap_attrinfo_insert_to_oos`); DELETE/UPDATE never clean inline; vacuum reclaims chains, and the forward-walk (`vacuum_forward_walk_oos_delete_atomic`) derives the head OIDs to delete **from the UPDATE/DELETE undo image**. The current invariant — "each OOS value chain is owned by exactly one logical heap-record version" — is what dedup retires.

### Decompose PG's safety into two independent halves

The single most useful result of this ticket is that PG's model is **not** one mechanism but two, and only one of them is about MVCC:

| Half | What it does | Where PG implements it |
|---|---|---|
| **A. Ownership** — who releases the chunks, exactly once | newest version owns; old versions hold borrowed references and never cascade | static call graph: `toast_tuple_cleanup` on change, `heap_delete`→`heap_toast_delete` on delete; `heap_update` deliberately does *not* cascade |
| **B. Grace period** — chunks survive release until no snapshot can reach any referencing version | chunk `xmax` = the releasing xid = the referencing version's `xmax`; toast VACUUM honours the removal horizon | toast-table MVCC + `HeapTupleSatisfiesToast` |

The ticket asks whether "toast-table MVCC alone carries the safety." **It does not.** It carries half B only. Half A is a structural property of where the delete calls live, and it would be equally necessary in a system with no MVCC at all.

### What transfers

**Half A transfers essentially unchanged, and OOS already has a working instance of it.** The SA_MODE eager path `heap_oos_delete_unreferenced` (`heap_oos.cpp:425`) already "compar[es] old and new head OOS OIDs to keep any chain the post-image still references" — that is `TOASTCOL_NEEDS_DELETE_OLD` under a different name, computed at UPDATE time by the actor holding both images. It should be correct for dedup as-is, and it is the shape the MVCC path needs to reach.

**The detection rule transfers, and CUBRID can do better than PG.** PG memcmps the pointer because by `heap_update` time it has lost the information about which columns were assigned. CUBRID's `heap_attrinfo` layer still has it, and the map has already decided "unchanged ⇔ not assigned in the UPDATE statement" — which is the thing PG's memcmp is *reconstructing*. So take the direct signal; the memcmp is available as a cheap assertion, not as the primary mechanism. Two PG details worth copying regardless:

- Compare/carry the **stub bytes**, never the value. No `oos_read` on the reuse path — the same reason PG's `TOASTCOL_IGNORE` branch `continue`s before any detoast.
- Make reuse **exclude the attribute from re-layout decisions** (PG: skipped by `toast_tuple_find_biggest_attribute`). A reused OOS attribute must not be re-considered for demotion or re-chunking in the same record.

**Half B transfers in substance but not in mechanism — and OOS does not need per-chunk MVCC to get it.** This is the point where the "chunk records have no MVCC" objection is weaker than it first appears. PG needs `xmax` on each chunk because its toast table is vacuumed by a *generic* heap vacuum that has no idea what a chunk is; the `xmax` is how the chunk tells that vacuum when it may go. OOS chunk deletion is instead driven by CUBRID's vacuum, which only processes log records already below the oldest active MVCCID. The horizon gate is therefore **already present, one level up**, in vacuum's scheduling rather than in per-chunk headers. A chain released by version *Vn* is not reclaimed until *Vn*'s log record is below the horizon — the same condition PG expresses as "chunk `xmax` below the horizon."

Two consequences worth checking during design rather than assuming:

- Vacuum processes log records oldest-first, so the *older* borrowing version is reclaimed before the *newer* owning version. That ordering is what makes "newest version owns" safe without refcounts — the last owner is also the last reclaimed. This follows from vacuum's log ordering and should be confirmed against the code in T3, not taken on faith from this ticket.
- PG's read path tolerates reading an already-released chunk (`HeapTupleSatisfiesToast` ignoring `xmax`). OOS's equivalent tolerance is that `oos_read` on an undo-image stub must succeed for any chain not yet physically reclaimed. That holds today; dedup does not change it.

### What does not transfer

**The decision timing.** This is the whole difficulty, and it is not about MVCC:

```
PG:   release decided at UPDATE time, by the transaction, with BOTH images in hand
OOS:  release decided at VACUUM time, by vacuum, with ONLY the undo image in hand
```

PG never needs to ask "is this chunk still referenced?" because it answers that question at the only moment the answer is locally available and then acts on it immediately. OOS defers the action across an unbounded time gap, and at the far end of that gap the forward-walk has lost the successor's head OIDs — which is precisely why old/new disjointness had to be made an invariant. Chain reuse violates the invariant, so the forward-walk would delete, from the undo image, a chain the live record still points to. Dangling stub.

**Therefore: no generation id, no update log — in PG.** The ticket's suspicion is confirmed. PG carries nothing resembling either. `TOASTCOL_NEEDS_DELETE_OLD` is the closest analogue and it is a `uint8` in a stack-allocated `ToastAttrInfo` that dies at the end of `heap_toast_insert_or_update`. PG can get away with an in-memory flag *because the gap between deciding and acting is a few hundred instructions*.

That reframes the map's preferred architecture rather neatly:

> **Option 2 (OOS update log) is PG's `TOASTCOL_NEEDS_DELETE_OLD` set, persisted.** Same content — "the chains this UPDATE dropped." Same producer — the updating transaction, holding both images. The only difference is that CUBRID must write it down, because its consumer runs later and elsewhere.

Framed that way, option 2 is not an exotic addition; it is the minimum needed to close the timing gap, and it restores the exactly-once discipline that §3 shows PG depends on absolutely (`simple_heap_delete` hard-errors on double release — PG has no tolerance for getting this wrong either).

**A note on option 1 (generation-id compare at vacuum time).** This finding supports T3's stated suspicion on structural grounds. Under reuse, the undo image and the live stub hold the *same* head OID and, per CBRD-26950's design, the same generation stamp — so a stamp-equality test reports "match" exactly in the case where deletion must be suppressed. The stamp answers "is this chunk still the one my stub named?" (slot-reuse defense), not "does anyone else still name it?" (ownership). Those are different questions, and PG answers the second one without any stamp at all — by never letting a borrower be in a position to delete. T3 owns the full evaluation; this is the mechanism-level reason to expect option 1 to require vacuum to visit the live heap record.

### Residual differences to keep in view

- **Rollback is *easier* under reuse, not harder.** If the UPDATE aborts, the reused chain was never deleted and the restored undo image still points at it. PG gets the same result via aborted `xmax`; OOS gets it by having done nothing. Chains freshly written for *assigned* attributes are undone by the normal path.
- **Replication.** PG's toast reuse is invisible to physical replication (byte-identical pages). OOS replicas perform their own `oos_insert` and may hold different OIDs (OOS-CONTEXT §4, "Slave OOS OIDs may differ from master"), so "reuse the old chain" is not directly replayable as an OID and needs its own treatment. PG offers no guidance here — that is T2's question, and it is a genuine OOS-only problem.
- **No cross-row dedup in PG either.** Every `toast_save_datum` outside a table rewrite mints a fresh `va_valueid` (`toast_internals.c:214-221`). PG's reuse is strictly *same-row, across-versions* — exactly the scope CBRD-27230 has chosen. The map's out-of-scope call on cross-row dedup matches PG's own boundary.
