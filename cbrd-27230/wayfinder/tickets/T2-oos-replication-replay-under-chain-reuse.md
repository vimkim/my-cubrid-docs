# T2 — OOS replication replay under chain reuse

- label: `wayfinder:research`
- status: open
- assignee: claude-research (fired at charting)
- blocked-by: (none)
- map: [CBRD-27230 OOS UPDATE dedup](../map.md)

## Question

How does `feat/oos` replicate OOS-backed values today, and what would break on a replica if the master starts reusing existing OOS value chains for attributes not assigned by an UPDATE?

1. **AS-IS replication content** — what exactly goes into the replication log for an INSERT/UPDATE of a record with OOS-backed attributes? Full values, or OOS inline stubs? (OOS-CONTEXT invariant 5 says the replica performs its own `oos_insert` and slave OOS OIDs may differ from the master's — find the code that makes that true.) Look at the OOS repl-log paths (`oos_repl_log`-related code, the known "unnecessary OOS replication log in `locator_add_or_remove_index`" refactoring note, `log_append`/repl machinery).
2. **UPDATE today** — for an UPDATE where an OOS-backed attribute is *not* assigned, does the current repl log still carry that attribute's full value (because a fresh chain is written)? What does the replica do with it?
3. **Under dedup** — if the master reuses the old chain (no new `oos_insert`, stub unchanged), what must the repl log carry so the replica keeps *its own* corresponding chain alive and its stub consistent? Does the replica need any change at all, or does its own dedup logic fall out naturally when it replays the UPDATE?
4. **HA/CDC edges** — note any flashback/CDC paths that parse OOS stubs from repl logs (OOS-CONTEXT lists a CDC flashback gap) that chain reuse would affect.

Sources (local, read-only): this worktree `/home/vimkim/gh/cb/CBRD-27230-oos-update-dedup` (branch = `feat/oos` tip), OOS-CONTEXT.md §4, `src/transaction/log_append.cpp`, `src/storage/heap_file.c`, `src/storage/oos_*`, `src/query/`/locator repl-log call sites.

## Resolution

(pending)
