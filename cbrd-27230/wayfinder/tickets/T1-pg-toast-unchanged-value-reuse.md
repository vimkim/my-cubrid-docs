# T1 — PG TOAST unchanged-value reuse on UPDATE: mechanism and vacuum safety

- label: `wayfinder:research`
- status: closed
- assignee: claude-research (fired at charting)
- blocked-by: (none)
- map: [CBRD-27230 OOS UPDATE dedup](../map.md)

## Question

How does PostgreSQL reuse TOAST data for unchanged toasted values on UPDATE, and what keeps VACUUM from reclaiming a toast value that multiple row versions share? Specifically:

1. **Unchanged detection** — in `heap_toast_insert_or_update` / `toast_helper.c`, what is the exact rule that decides "old value can be kept"? Pointer equality on the TOAST pointer? Attribute-not-assigned? Byte comparison?
2. **Chunk lifetime ownership** — TOAST chunks live in a toast *table* with ordinary MVCC. When an UPDATE reuses the old TOAST pointer, both the old and new main-table row versions reference the same `chunk_id`. Who deletes the chunks, and when? (`toast_delete_datum` call sites; how VACUUM of the main table relates to VACUUM of the toast table.)
3. **Deletion on change** — when the toasted column IS assigned a new value, how/when does the old datum get deleted, and how is that crash-safe / idempotent?
4. **Transfer assessment** — CUBRID OOS chunk records have **no MVCC** (physical slotted-page records, vacuum-driven cleanup from undo images). Which parts of the PG model transfer to OOS and which fundamentally cannot? Note especially whether PG needs anything like a generation id or an "update log" — or whether toast-table MVCC alone carries the safety.

Primary sources: PostgreSQL source (`src/backend/access/heap/heaptoast.c`, `src/backend/access/common/toast_internals.c`, `toast_helper.c`) and PG docs. Check for a local PG checkout under `/home/vimkim/gh` first; otherwise fetch from github.com/postgres/postgres.

## Resolution

PG's safety is **two** mechanisms, not one, and only the second is MVCC. (A) *Ownership*: the newest row version owns the chunks; old versions hold borrowed pointers and never cascade — `heap_update` deliberately never calls `heap_toast_delete`, so a chain is released exactly once, either by a later UPDATE that changes the column (`toast_tuple_cleanup`) or by `heap_delete`. (B) *Grace period*: toast-table MVCC only spans release→physical removal; the chunk `xmax` is the same xid as the referencing version's `xmax`, so both cross the horizon together, and `HeapTupleSatisfiesToast` ignores `xmax` entirely. Detection is a `memcmp` of the 18-byte on-disk TOAST pointer in `toast_tuple_init` — not the value, not pointer identity — with reuse as the fallthrough branch. Crash-safety is plain WAL + MVCC rollback; there is **no** idempotence (`simple_heap_delete` errors `"tuple already updated by self"`), so PG depends absolutely on the one-owner discipline.

PG carries **no generation id and no update log**: `TOASTCOL_NEEDS_DELETE_OLD` is a stack flag consumed a few hundred instructions later. Half (A) transfers to OOS directly — SA_MODE's `heap_oos_delete_unreferenced` already implements it. Half (B) transfers in substance without per-chunk MVCC, since OOS cleanup is *already* horizon-gated by vacuum scheduling. What genuinely does not transfer is the **decision timing**: PG decides with both images in hand at UPDATE time, OOS defers to vacuum which sees only the undo image. Closing that gap is exactly option 2 — **the OOS update log is PG's `TOASTCOL_NEEDS_DELETE_OLD` set, persisted.** Supports T3's suspicion on option 1: a reused chain has the same head OID *and* generation in both images, so stamp equality says "delete" precisely when it must not.

Findings: [T1 — PostgreSQL TOAST unchanged-value reuse on UPDATE](../findings/T1-pg-toast-unchanged-value-reuse.md)
