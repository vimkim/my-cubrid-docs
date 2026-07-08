# Reply to `my-review-214d4b1.md` — CBRD-27006 OOS read/insert path

Scope of this doc: **answers + a future plan only.** No code is changed yet — the one
contested item (where the OOS→dbvalue transform lives) is called out as a decision, and the
recommended edits are staged, not applied.

## Context in one paragraph

CBRD-27006 batches OOS I/O for page locality. On the **read** side, a record with ≥2 requested
OOS columns prefetches all of them through a single `oos_read_many` instead of one `oos_read`
per column; on the **insert** side, all OOS columns of a record are serialized and written
through one batched `heap_oos_insert_serialized_values`. The four review points all sit on the
seam between `heap_file.c` (owns DB_VALUE ⇄ RECDES serialization and the attribute read loop)
and `heap_oos.cpp` (owns the OOS file and the batched OOS API calls).

---

## Q1 — Why does `heap_attrvalue_read` take `prefetched_oos`? What if I remove it? Alternatives?

### Why it exists

`prefetched_oos` is the **hand-off channel** for the batched read. The work is split across two
files:

- `heap_oos_read_grouped_payloads` (heap_oos.cpp) **prefetches**: parse each inline
  `[OID|length]` ref → allocate a buffer → one `oos_read_many` for the whole record.
- `heap_attrvalue_transform_to_dbvalue` (heap_file.c, **`static`**) **materializes** the raw
  bytes into `value->dbvalue`.

Because the transform is private to `heap_file.c`, the prefetched bytes have to travel *back*
into `heap_file.c` to be turned into dbvalues. `prefetched_oos` is that pointer:

```c
if (prefetched_oos != NULL && prefetched_oos->data != NULL)
  {
    /* bytes already fetched by oos_read_many — transform straight from them (COPY) */
    return heap_attrvalue_transform_to_dbvalue (value, value->read_attrepr, prefetched_oos, true);
  }
```

So the parameter is not incidental — it is the only thing connecting the batched prefetch to
per-column materialization while keeping the transform inside `heap_file.c`.

### What removing it looks like

Deleting the parameter forces one of two outcomes:

1. **Lose the read-path optimization.** `heap_attrvalue_read` goes back to always doing its own
   scalar `oos_read` per column. Correctness is unchanged, but `oos_read_many` on the read path
   becomes dead code and the *read* half of CBRD-27006 stops doing anything. (The insert half
   would still batch.)
2. **Move the transform out of `heap_file.c`.** If the grouped reader materializes the dbvalues
   itself, no hand-off is needed — but then `heap_attrvalue_transform_to_dbvalue` must become
   non-static/extern, which re-opens the exact `static` boundary the last three commits
   (`0dc301b8a`, `3db4c8a78`, `214d4b1a4`) deliberately closed.

In other words: the parameter is the price of keeping the transform `static` while still
batching. Remove it and you must give up one of those two properties.

### Alternatives

| Option | Idea | Cost |
|---|---|---|
| **A. Keep the param, minimal cleanup** *(recommended)* | Leave the transform `static`; keep `prefetched_oos`; just remove the redundant `grouped` flag (see Q2). | Smallest diff; seam stays but is honest and documented. |
| B. Move transform into `heap_oos.cpp` | `heap_oos_read_grouped_payloads` resolves OOS attrs end-to-end; scalar loop skips them. Removes the param *and* the Q2 ternary. | Best cohesion (OOS read fully owned by heap_oos.cpp) but re-exposes `heap_attrvalue_transform_to_dbvalue` — reverses the recent static restoration. |
| C. Thread the whole batch | Pass `std::vector<RECDES>*` + base index into `heap_attrvalue_read`. | Same coupling as A, uglier signature. |
| D. Stash on `HEAP_ATTRVALUE` | Add a transient "prefetched bytes" field to the value struct. | Invasive; adds lifetime hazard to a widely-used struct. Rejected. |

**Recommendation: A.** Keep the transform private to `heap_file.c` and keep `prefetched_oos` as
the documented seam. Option B is genuinely cleaner in cohesion terms, but it undoes a boundary
that was just settled on purpose, so it should only happen as a deliberate, separate decision —
not folded in here.

---

## Q2 — `grouped ? &oos_raws[i] : NULL` looks awkward. Alternatives?

The awkwardness is a direct symptom of Q1's seam, but most of it is removable **without**
touching the boundary: the `grouped` bool is fully redundant.

`heap_oos_read_grouped_payloads` only resizes `oos_raws` to `num_values` on the grouped path;
otherwise it leaves the vector **empty**. So `oos_raws.empty()` already carries exactly the
signal `grouped` carries, and entries with `data == NULL` already mark "not OOS here, use the
scalar reader." The separate `bool *handled` out-param and the `bool grouped` local are pure
duplication.

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

**After** (drop `handled`/`grouped`; derive from emptiness)

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

This deletes an out-parameter from the helper and turns the ternary into a bounds-guarded index
that reads as what it is. `heap_attrvalue_read` already NULL-guards both `prefetched_oos` and
`prefetched_oos->data`, so no other change is needed. Verified: `grouped`/`handled` is used
nowhere except this one ternary.

(Option B from Q1 would remove the line entirely, at the boundary cost described above.)

---

## Q3 — Now that the grouped logic exists, is there still a reason to separate `heap_attrinfo_read_dbvalues` from `..._internal`?

**Yes — and the separation is *new in this PR*, added precisely to avoid duplicating the grouped
logic.** The review's premise ("now no reason to separate") is inverted.

On the base branch (`feat/oos`, commit `5b5ff588f`) there was **no `_internal`**. Both public
entry points carried their own copy of the per-attribute read loop:

- `heap_attrinfo_read_dbvalues` — base `heap_file.c:11031` (`for … heap_attrvalue_read (…)`)
- `heap_attrinfo_read_dbvalues_without_oid` — base `heap_file.c:11094` (identical loop)

This PR replaced that duplicated loop with the three-step grouped sequence
(`heap_oos_read_grouped_payloads` → loop → `heap_oos_free_grouped_payloads`) and factored it
into `_internal` so it lives in **one** place. Both public functions still call it:

- `heap_attrinfo_read_dbvalues` → `_internal` (heap_file.c:11058)
- `heap_attrinfo_read_dbvalues_without_oid` → `_internal` (heap_file.c:11115),
  and `_without_oid` has a real external caller (`locator_sr.c:12634`).

Merging `_internal` back into `heap_attrinfo_read_dbvalues` would re-duplicate the grouped
prefetch/loop/free into `_without_oid`. So the split is load-bearing.

The two public wrappers differ only in: (a) `_without_oid` skips the `inst_oid`-gated
representation check, and (b) it does not cache `inst_chn`/`inst_oid` at the end. They *could* be
collapsed into one function with a nullable `inst_oid`, but that pre-dates this PR and is
unrelated to OOS — out of scope here. **Recommendation: keep `_internal`; optionally add a
one-line comment noting it is shared by both entry points so this question does not recur.**

---

## Q4 — Why is `heap_attrinfo_insert_to_oos` in `heap_file.c` and not `heap_oos.cpp`? Redesign for readability.

### Why it lives in `heap_file.c`

It is a **serialization adapter**, not OOS-file logic. Its body:

1. For each selected column, serialize `DB_VALUE → RECDES` via `heap_attrinfo_dbvalue_to_recdes`
   — a **`static` heap_file.c** function (heap_file.c:12393) that also performs the BLOB/CLOB
   `db_elo_copy_with_prefix` step, **shared with the inline record writer**.
2. Build the `oos_insert_request` vector.
3. Delegate the actual write to `heap_oos_insert_serialized_values` (heap_oos.cpp) — which owns
   OOS file lookup, publication-state reset, and the batched insert.

So the file split already matches ownership: **serialization + ELO copy = heap_file.c; OOS write
= heap_oos.cpp.** Moving the adapter into `heap_oos.cpp` would drag `heap_attrinfo_dbvalue_to_recdes`
(and its ELO-copy coupling with the inline writer) across the boundary — spreading heap
serialization into the OOS file. That is a worse split, not a better one. The current header
comment states this; it's correct.

### Readability redesign (local, keeps the boundary)

The function is doing three jobs in one body. Suggested shape:

1. **Extract the per-column serialize step.** A small static helper, e.g.
   `heap_attrinfo_serialize_oos_column (thread_p, value, class_oid, lob_flag, &recdes)`, returning
   the exact-size RECDES (or an error). The main loop then reads:
   ```c
   for each i:
     if (!(*oos_columns)[i]) continue;
     if (serialize column i → recdes != S_SUCCESS) goto cleanup;
     (*oos_lengths)[i] = recdes.length;
     requests.push_back ({ oos_buffer (recdes.data, recdes.length), &(*oos_oids)[i] });
   ```
   The asserts and the `recdes.data == NULL || length <= 0` guard move into the helper.

2. **The real smell is the three parallel out-vectors** — `oos_columns` (bool),
   `oos_oids` (OID), `oos_lengths` (DB_BIGINT), all indexed by attribute and passed as three
   `std::vector<...> *`. Collapsing them into one `std::vector<oos_column_plan>` of
   `{ bool selected; OID oid; DB_BIGINT length; }` would remove the parallel-index coupling and
   read far better. **But** these three vectors are produced in `heap_attrinfo_determine_disk_layout`
   and consumed again in `heap_attrinfo_transform_columns_to_disk`, so this is a cross-function
   refactor, not a local one. Flagged as a **separate, larger** change (see plan) rather than
   bundled here.

3. **Minor:** in the cleanup loop, `free_and_init (request_data)` operates on a local copy
   `char *request_data`, so it nulls the local, not the vector slot. It is correct (the vector is
   about to be discarded) but slightly misleading; a one-line comment or clearing the slot
   directly would remove the head-scratch. The `goto cleanup` idiom itself is fine and matches
   engine C-in-C++ style — no change.

---

## Future plan (ordered by risk, lowest first)

| # | Change | Files | Risk | Ties to |
|---|---|---|---|---|
| 1 | Add a one-line comment on `_internal` noting it is shared by both `read_dbvalues` entry points. | heap_file.c | none | Q3 |
| 2 | Drop the redundant `handled`/`grouped` flag; derive the grouped path from `oos_raws.empty()`. Update the helper signature and its doc comment. | heap_file.c, heap_oos.cpp/.hpp | low | Q2 |
| 3 | Extract `heap_attrinfo_serialize_oos_column` from `heap_attrinfo_insert_to_oos`; add the cleanup comment (item Q4.3). | heap_file.c | low | Q4 |
| 4 | *(deferred, decide separately)* Collapse the three parallel OOS out-vectors into one `oos_column_plan` struct across `determine_disk_layout` / `insert_to_oos` / `transform_columns_to_disk`. | heap_file.c | medium | Q4.2 |
| 5 | *(deferred, decide separately)* Move `heap_attrvalue_transform_to_dbvalue` to extern and relocate OOS materialization into `heap_oos.cpp`, removing `prefetched_oos` entirely. | heap_file.c/.h, heap_oos.cpp | medium | Q1 opt. B |

Items 1–3 are safe, boundary-preserving, and shrink the diff/complexity the review flagged.
Items 4–5 each re-open a boundary and should be an explicit yes/no, not a drive-by.

**Verification for whatever we implement:** `just build` + `just build-test`, then
`test_oos` (SA), `test_oos_server`, `test_oos_sql_crud` — including
`OosSqlCrud.Cbrd27006ReadDispatchBatchesOnlyMultiOosProjections`, which asserts the ≥2-OOS
dispatch via `read_many_calls`. The 10 `oos_debug_counters` fields are all asserted by tests, so
none of items 1–3 may change counter semantics (they don't). Formatter: `indent -l120` for `.c`.

---

## Open questions for you

1. **Q4.2 scope** — do you want the parallel-array → `oos_column_plan` struct refactor (item 4),
   or is the local extract (item 3) enough for now?
2. **Q1 option B** — confirmed we keep the transform `static` (item 5 stays deferred)? I'll write
   the reply around "keep static" unless you say otherwise.
3. **Q3** — is a one-line comment (item 1) worth adding, or do you consider the two-caller fact
   self-evident and want no code touch there at all?
