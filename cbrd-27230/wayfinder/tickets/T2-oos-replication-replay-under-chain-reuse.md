# T2 — OOS replication replay under chain reuse

- label: `wayfinder:research`
- status: closed
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

The repl log carries no values — one `RVREPL_OOS_INSERT` item per OOS value whose `lsa` points at the master's physical `RVOOS_INSERT` WAL record, then the row item (`locator_sr.c:8150`, `:8940`; `replication.c:459`). The replica reads those WAL bytes, runs its own `oos_insert` (`locator_sr.c:5287`), and rewrites the master's OIDs in the record (`locator_sr.c:14166`) — that is invariant 5's implementation. Today an UPDATE re-resolves and re-inserts even unassigned OOS attributes, so their full value ships every time (`heap_file.c:10514`, `:13302`). Under naive dedup the replica fails **loudly**, never silently: fewer items than stubs trips "missing/not enough OOS OIDs" (`locator_sr.c:14179`, `:14234`) and HA apply stops. The replica does need changes: a per-reused-attribute marker item to keep the count-exact positional contract, and a fixup that takes the reused slot's OID from the replica's own previous row version — already fetched at `locator_sr.c:6943` but with OOS expansion on, so it must switch to `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`. Replica-side vacuum needs the same old∩new sharing check as the master, and `applylogdb` sql.log breaks per deduped UPDATE (`log_applier.c:3845`). CDC/flashback gain correct "unchanged" diffs but lose any chance of a log-only stub resolve (`log_manager.c:11942`, `:12478`). Bonus AS-IS defect at the known refactoring site: the DELETE path can emit OOS repl items from a stale `thread_p->oos_oids` (`locator_sr.c:8150`), draining an empty LSA queue into `assert(false)`.

Findings: [T2 findings](../findings/T2-oos-replication-replay-under-chain-reuse.md)
