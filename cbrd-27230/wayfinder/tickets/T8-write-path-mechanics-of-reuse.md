# T8 — Write-path mechanics of reuse: where "assigned" is known and how the old stub carries forward

- label: `wayfinder:research`
- status: open
- assignee: claude-research (fired at T4 resolution)
- blocked-by: (none — T4's contract is its input, already locked)
- map: [CBRD-27230 OOS UPDATE dedup](../map.md)

## Question

Ground the T6 spec's Implementation section: trace the current `feat/oos` UPDATE write path and identify the minimal changes for chain reuse under the locked T4 contract.

1. **AS-IS trace** — for an UPDATE, where does the write path learn which attributes were assigned, and what happens to *unassigned* OOS-backed attributes today? Expected trail: `heap_attrinfo_set_uninitialized` / `heap_attrvalue_read` resolving old values (the `oos_read` we want to eliminate — OOS-CONTEXT Optimization Idea A names this touch point), then `heap_attrinfo_determine_disk_layout` re-demoting and `heap_attrinfo_insert_to_oos` writing fresh chains. Confirm with file:line.
2. **TO-BE sketch (invariant level, for the spec)** — what minimally changes so that (a) an unassigned OOS-backed attribute's inline stub is copied verbatim from the old record version into the new one (no `oos_read`, no new chain — note the stub is 20B once CBRD-26950 lands); (b) assigned OOS-backed attributes still demote normally and additionally produce the `(head OOS OID, expected generation)` entries for the commit-time postpone notify record; (c) the postpone registration hooks in before the heap update record is appended (locate the right vicinity, e.g. around `heap_log_update_physical`).
3. **Edge checks** — what happens when an unassigned attribute's row *shrinks below* the OOS gate after other columns shrink (does the reused stub stay OOS-backed even though a fresh insert wouldn't demote it — presumably yes, and say why that's fine); and confirm the SA_MODE eager path (`heap_oos_delete_unreferenced`) needs no change under reuse (its old-minus-new difference already handles shared chains).
4. **Idea-B interplay** — note whether the commit-time postpone conflicts or synergizes with the deferred "move `oos_insert` to `attrinfo_force`" idea (OOS-CONTEXT Optimization Idea B); one paragraph, no design work.

Sources (local, read-only): worktree `/home/vimkim/gh/cb/CBRD-27230-oos-update-dedup` @ `725a32c6e` (`src/storage/heap_file.c`, `heap_oos.cpp`, `oos_file.cpp`), OOS-CONTEXT.md §3/§5, the locked contract in [T4](./T4-lock-cleanup-architecture.md).

## Resolution

(pending)
