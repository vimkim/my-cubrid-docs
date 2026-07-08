# Reply to `my-review-214d4b1.md` — CBRD-27006 OOS read/insert path

**Scope:** answers + a risk-ordered plan. No code changed yet. The one contested item (where the
OOS→DB_VALUE transform lives) is called out as a decision, not folded in.

## Context in one paragraph

CBRD-27006 batches OOS I/O for page locality. On the **read** side, a record with ≥2 requested
OOS columns prefetches all of them through a single `oos_read_many` instead of one `oos_read` per
column; on the **insert** side, all OOS columns of a record are serialized and written through one
batched `heap_oos_insert_serialized_values`. All four review points sit on the seam between
`heap_file.c` (owns DB_VALUE ⇄ RECDES serialization and the attribute read loop) and
`heap_oos.cpp` (owns the OOS file and the batched OOS API calls). The last three commits
(`0dc301b8a`, `3db4c8a78`, `214d4b1a4`) deliberately kept `heap_attrvalue_read` and
`heap_attrvalue_transform_to_dbvalue` **`static`** in `heap_file.c`; the answers below respect that
boundary unless we explicitly decide to move it.

---

## Q1 — Why does `heap_attrvalue_read` take `prefetched_oos`? What if I remove it? Alternatives?

### Why it exists

`prefetched_oos` is the **hand-off channel** for the batched read. The work is split across two
files:

- `heap_oos_read_grouped_payloads` (`heap_oos.cpp:495`) **prefetches**: parse each inline
  `[OID|length]` ref → allocate a buffer → one `oos_read_many` for the whole record.
- `heap_attrvalue_transform_to_dbvalue` (`heap_file.c:10660`, **`static`**) **materializes** the raw
  bytes into `value->dbvalue`.

Because the transform is private to `heap_file.c`, the prefetched bytes have to travel *back* into
`heap_file.c` to become DB_VALUEs. `prefetched_oos` is that pointer (`heap_file.c:10736`):

```c
if (prefetched_oos != NULL && prefetched_oos->data != NULL)
  {
    /* bytes already fetched by oos_read_many — transform straight from them (COPY) */
    return heap_attrvalue_transform_to_dbvalue (value, value->read_attrepr, prefetched_oos, true);
  }
```

So the parameter is not incidental: it is the only thing connecting the batched prefetch to
per-column materialization while keeping the transform inside `heap_file.c`. It is **not** needed for
the correctness of ordinary reads — only to consume the `oos_read_many` result without exporting or
duplicating the conversion logic.

### What removing it looks like

Deleting the parameter forces one of two outcomes:

1. **Lose the read-path optimization.** `heap_attrvalue_read` goes back to always doing its own
   scalar `oos_read` per column. `heap_oos_read_grouped_payloads` would still allocate buffers and
   call `oos_read_many`, then the loop would re-read each OOS attribute scalar-style and free the
   grouped buffers unused. Correctness is unchanged, but the *read* half of CBRD-27006 becomes dead
   code. (The insert half would still batch.)
2. **Move the transform out of `heap_file.c`.** If the grouped reader materializes the DB_VALUEs
   itself, no hand-off is needed — but then `heap_attrvalue_transform_to_dbvalue` must become
   non-static/extern, which re-opens the exact boundary the last three commits closed.

In other words: the parameter is the price of keeping the transform `static` while still batching.
Remove it and you must give up one of those two properties.

### Alternatives

| Option | Idea | Cost |
|---|---|---|
| **A. Keep the param, minimal cleanup** *(recommended)* | Leave the transform `static`; keep the hand-off; just drop the redundant `grouped` flag (Q2). | Smallest diff; seam stays but becomes honest and documented. |
| B. Explicit branch in the loop | Remove the param; in `_internal`'s loop, call `heap_attrvalue_transform_to_dbvalue` when a prefetched payload is present, else the scalar `heap_attrvalue_read`. Both helpers stay `static`. | Slightly clearer than the param, but the loop still mixes dispatch + buffer ownership + scalar fallback. |
| C. Move transform into `heap_oos.cpp` | `heap_oos_read_grouped_payloads` resolves OOS attrs end-to-end; scalar loop skips them. Removes the param entirely. | Best cohesion (OOS read fully owned by heap_oos.cpp) but re-exposes `heap_attrvalue_transform_to_dbvalue` — reverses the recent static restoration. |
| D. Stash on `HEAP_ATTRVALUE` | Add a transient "prefetched bytes" field to the value struct. | Invasive; adds a lifetime hazard to a widely-used struct. Rejected. |

**Recommendation: A**, with B as the fallback if you want the param gone without moving the
boundary. C is genuinely cleaner in cohesion terms, but it undoes a boundary that was just settled on
purpose, so it should be a deliberate, separate decision — not folded in here.

---

## Q2 — `grouped ? &oos_raws[i] : NULL` looks awkward. Alternatives?

Most of the awkwardness is removable **without** touching the boundary: the `grouped` bool is fully
redundant.

`heap_oos_read_grouped_payloads` sets `*handled = false` and leaves `oos_raws` **untouched** on both
non-grouped early returns (`heap_oos.cpp:504,508,521`), and only does `raws.resize(...)` *after*
`*handled = true` on the grouped path (`heap_oos.cpp:524,528`). So `oos_raws.empty()` already carries
exactly the signal `grouped` carries, and within a resized vector `data == NULL` already marks "not
OOS here, use the scalar reader." Verified: `grouped`/`handled` is read nowhere except this one
ternary (`heap_file.c:10821`).

**Before**

```c
std::vector<RECDES> oos_raws;
bool grouped = false;
...
ret = heap_oos_read_grouped_payloads (thread_p, recdes, attr_info, oos_raws, &grouped);

for (i = 0; ret == NO_ERROR && i < attr_info->num_values; i++)
  {
    ret = heap_attrvalue_read (recdes, &attr_info->values[i], attr_info,
                               grouped ? &oos_raws[i] : NULL);
  }
```

**After** (drop the `handled` out-param and the `grouped` local; derive from emptiness)

```c
std::vector<RECDES> oos_raws;   /* non-empty only on the grouped path */
...
ret = heap_oos_read_grouped_payloads (thread_p, recdes, attr_info, oos_raws);

for (i = 0; ret == NO_ERROR && i < attr_info->num_values; i++)
  {
    /* On the grouped path every slot exists; data==NULL means "not OOS, scalar-read it". */
    RECDES *prefetched = oos_raws.empty () ? NULL : &oos_raws[i];
    ret = heap_attrvalue_read (recdes, &attr_info->values[i], attr_info, prefetched);
  }
```

This deletes an out-parameter from the helper and turns the ternary into a bounds-guarded index that
reads as what it is. `heap_attrvalue_read` already NULL-guards both `prefetched_oos` and
`prefetched_oos->data`, so no other change is needed. It is safe on the grouped **error** path too:
if request-building or `oos_read_many` fails, the function returns non-`NO_ERROR`, the caller loop
is skipped, and `heap_oos_free_grouped_payloads` still cleans up.

If you'd rather remove the parameter entirely (not just the flag), that is Q1 option B — a larger but
still boundary-preserving change: split the loop into an explicit "transform prefetched payload vs.
scalar-read" branch. The cleanest *end-state* is Q1 option C (a dedicated grouped read helper), at
the boundary cost noted above.

---

## Q3 — Now that the grouped logic exists, is there still a reason to separate `heap_attrinfo_read_dbvalues` from `..._internal`?

**Yes — the separation is *new in this PR*, added precisely to avoid duplicating the grouped logic.**
The review's premise ("now no reason to separate") is inverted.

`heap_attrinfo_read_dbvalues_internal` did not exist before; it was introduced by this branch's own
commit `8d053f641 [CBRD-27006] Simplify batched OOS paths and dispatch only multi-OOS reads`. It holds
the three-step grouped sequence in **one** place:

```
heap_oos_read_grouped_payloads()  ->  per-attribute loop  ->  heap_oos_free_grouped_payloads()
```

Both public entry points call it:

- `heap_attrinfo_read_dbvalues` → `_internal` (`heap_file.c:11058`)
- `heap_attrinfo_read_dbvalues_without_oid` → `_internal` (`heap_file.c:11115`), and `_without_oid`
  is a long-pre-existing public function with a real external caller (`locator_sr.c:12634`).

Merging `_internal` back into `heap_attrinfo_read_dbvalues` would re-duplicate the grouped
prefetch/loop/free into `_without_oid`. So the split is load-bearing.

The two public wrappers differ only in: (a) `_without_oid` skips the `inst_oid`-gated representation
check, and (b) it does not cache `inst_chn`/`inst_oid` at the end. They *could* be collapsed into one
function with a nullable `inst_oid`, but that predates this PR and is unrelated to OOS — out of scope.

**Recommendation:** keep `_internal`. The name is the only weak point — it no longer says what it
does. Either add a one-line comment noting it is the shared read loop for both entry points, or (if
you want a rename) `heap_attrinfo_read_dbvalues_from_recdes` describes it better. Rename is optional
churn; a comment is enough.

---

## Q4 — Why is `heap_attrinfo_insert_to_oos` in `heap_file.c` and not `heap_oos.cpp`? Redesign for readability.

### Why it lives in `heap_file.c`

It is a **serialization adapter**, not OOS-file logic. Its body:

1. For each selected column, serialize `DB_VALUE → RECDES` via `heap_attrinfo_dbvalue_to_recdes` — a
   **`static` heap_file.c** function that also performs the BLOB/CLOB `db_elo_copy_with_prefix` step,
   **shared with the inline record writer**.
2. Build the `oos_insert_request` vector.
3. Delegate the write to `heap_oos_insert_serialized_values` (heap_oos.cpp), which owns OOS file
   lookup, transaction-descriptor validation, publication-state reset, and the batched
   `oos_insert_many`.

So the boundary already matches ownership:

```
heap_file.c   -> choose OOS attributes, serialize DB_VALUEs (incl. ELO copy) into stable RECDES buffers
heap_oos.cpp  -> insert already-serialized payloads into the OOS file
```

Moving the adapter into `heap_oos.cpp` would drag `heap_attrinfo_dbvalue_to_recdes` (and its ELO-copy
coupling with the inline writer) across the boundary — spreading heap serialization into the OOS
file. That is a worse split, not a better one. The current header comment states this; it's correct.

### Readability redesign (local, keeps the boundary)

The function does three jobs in one body. Split it into small `static` helpers, all staying in
`heap_file.c`:

```c
static SCAN_CODE heap_attrinfo_serialize_oos_value (THREAD_ENTRY *thread_p, HEAP_CACHE_ATTRINFO *attr_info,
                                                    int index, int lob_flag, RECDES *payload);
static SCAN_CODE heap_attrinfo_prepare_oos_insert_requests (THREAD_ENTRY *thread_p, HEAP_CACHE_ATTRINFO *attr_info,
                                                            std::vector<bool> *oos_columns,
                                                            std::vector<OID> *oos_oids,
                                                            std::vector<DB_BIGINT> *oos_lengths,
                                                            std::vector<RECDES> *payloads,
                                                            std::vector<oos_insert_request> *requests);
static void heap_attrinfo_free_oos_payloads (std::vector<RECDES> *payloads);
```

`heap_attrinfo_insert_to_oos` then reads as orchestration:

```
reserve payload/request vectors
prepare serialized payloads + request spans   (per-column serialize lives in the helper)
heap_oos_insert_serialized_values (...)
free payload buffers
return S_SUCCESS / S_ERROR
```

The asserts and the `recdes.data == NULL || length <= 0` guard move into
`heap_attrinfo_serialize_oos_value`. This keeps `heap_oos.cpp` free of heap serialization details
while making the insert path easy to follow.

Two more notes:

- **Minor correctness-of-reading nit:** in the current cleanup loop, `free_and_init (request_data)`
  operates on a local `char *request_data`, so it nulls the local, not the vector slot. It is correct
  (the vector is discarded right after) but slightly misleading; folding cleanup into
  `heap_attrinfo_free_oos_payloads` removes the head-scratch. The `goto cleanup` idiom itself is fine
  and matches engine C-in-C++ style — no change.
- **The deeper smell is the three parallel out-vectors** — `oos_columns` (bool), `oos_oids` (OID),
  `oos_lengths` (DB_BIGINT), all indexed by attribute. Collapsing them into one
  `std::vector<oos_column_plan>` of `{ bool selected; OID oid; DB_BIGINT length; }` would remove the
  parallel-index coupling. **But** these vectors are produced in
  `heap_attrinfo_determine_disk_layout` and consumed again in
  `heap_attrinfo_transform_columns_to_disk`, so this is a cross-function refactor, not a local one —
  flagged as a separate, larger change below, not bundled here.

---

## Future plan (ordered by risk, lowest first)

| # | Change | Files | Risk | Ties to |
|---|---|---|---|---|
| 1 | Add a one-line comment on `_internal` noting it is the shared read loop for both `read_dbvalues` entry points (optional rename to `_from_recdes`). | heap_file.c | none | Q3 |
| 2 | Drop the redundant `handled`/`grouped` flag; derive the grouped path from `oos_raws.empty()`. Update the helper signature and its doc comment. | heap_file.c, heap_oos.cpp/.hpp | low | Q2 |
| 3 | Extract `heap_attrinfo_serialize_oos_value` / `heap_attrinfo_prepare_oos_insert_requests` / `heap_attrinfo_free_oos_payloads`; fold in the cleanup so `free_and_init` no longer nulls a local. | heap_file.c | low | Q4 |
| 4 | *(deferred, decide separately)* Remove `prefetched_oos` via an explicit transform-vs-scalar branch (Q1 opt. B), or a dedicated grouped read helper (opt. C). | heap_file.c | low–medium | Q1/Q2 |
| 5 | *(deferred, decide separately)* Collapse the three parallel OOS out-vectors into one `oos_column_plan` across `determine_disk_layout` / `insert_to_oos` / `transform_columns_to_disk`. | heap_file.c | medium | Q4 |
| 6 | *(deferred, decide separately)* Move `heap_attrvalue_transform_to_dbvalue` to extern and relocate OOS materialization into `heap_oos.cpp`, removing `prefetched_oos` entirely (Q1 opt. C end-state). | heap_file.c/.h, heap_oos.cpp | medium | Q1 |

Items 1–3 are safe, boundary-preserving, and shrink the diff/complexity the review flagged. Items
4–6 each re-open a design point (or a settled boundary) and should be an explicit yes/no, not a
drive-by.

**Verification for whatever we implement:** `just build` + `just build-test`, then `test_oos` (SA),
`test_oos_server`, `test_oos_sql_crud` — including
`OosSqlCrud.Cbrd27006ReadDispatchBatchesOnlyMultiOosProjections`, which asserts the ≥2-OOS dispatch
via `read_many_calls`. The `oos_debug_counters` fields are all asserted by tests, so none of items
1–3 may change counter semantics (they don't). Formatter: `indent -l120` for `.c`.

---

## Open questions for you

1. **Read path (items 2 vs 4):** ship just the redundant-flag cleanup now (item 2, minimal diff), or
   go straight to removing `prefetched_oos` via the explicit branch / grouped helper (item 4)?
2. **Boundary (item 6):** confirm we keep the transform `static` (item 6 stays deferred)? I'll write
   the reply around "keep static" unless you say otherwise.
3. **Write path (items 3 vs 5):** is the local helper extract (item 3) enough for now, or do you want
   the parallel-array → `oos_column_plan` struct refactor (item 5) in the same pass?
4. **Q3:** one-line comment, or rename `_internal` → `_from_recdes`, or leave it as-is?
