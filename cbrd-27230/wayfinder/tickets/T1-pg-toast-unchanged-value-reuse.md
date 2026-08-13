# T1 — PG TOAST unchanged-value reuse on UPDATE: mechanism and vacuum safety

- label: `wayfinder:research`
- status: open
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

(pending)
