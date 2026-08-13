# T8 — Write-path mechanics of reuse: where "assigned" is known and how the old stub carries forward

- label: `wayfinder:research`
- status: closed
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

(2026-08-13, claude-research.) Full trace with file:line evidence:
[../findings/T8-write-path-mechanics-of-reuse.md](../findings/T8-write-path-mechanics-of-reuse.md).

1. **AS-IS**: "unassigned" ≡ `state == HEAP_UNINIT_ATTRVALUE` at `heap_attrinfo_set_uninitialized`
   (`heap_file.c:12156`); the same function destroys the signal by calling `heap_attrvalue_read` → `oos_read`
   (`:12158`, `:10482`). Downstream the value is indistinguishable from an assigned one: it is re-sized
   logically (`:12244`), re-demoted (`:12382`), re-inserted as a fresh chain (`:12680`), stamped into a new
   stub (`:13047`). Cost per unassigned OOS attribute: one `oos_read` + one `oos_insert` + one dead chain.
2. **TO-BE**: capture the old stub `(head OID, length[, generation])` inside `set_uninitialized`; split
   `heap_oos_column_plan.selected` into "write a stub" vs "allocate a chain" so
   `heap_attrinfo_prepare_oos_insert_requests` (`:12633`) skips reused columns. The stub writer
   (`:13039-13050`) needs no change. The same pass yields the drop list (assigned + old-VOT `OR_IS_OOS`).
   Registration vicinity: just before the three `heap_log_update_physical` calls (`:24145`, `:23588`, `:23906`).
3. **Open mechanical point for T6** (invariant unaffected): vacuum's stream is fed only by MVCC *undo* appends
   (`log_append.cpp:970-996`, `:1384`) and `logtb_complete_mvcc` precedes `log_tran_do_postpone`
   (`log_manager.c:5228` vs `:5245`) — a bare `log_append_postpone` cannot deliver a vacuum-visible notify.
   Three shapes listed in the findings; a commit hook placed before `logtb_complete_mvcc` is recommended.
4. **Edge checks**: a reused stub below the gate is safe — the gate literal exists only in
   `determine_disk_layout` (`:12345`, `:12378`) and reuse can only shrink the record, so the OOS+bigone guard
   (`:13295`) cannot newly trip. `heap_oos_delete_unreferenced` needs no change (`heap_oos.cpp:754-760`);
   the notify stays gated to `is_mvcc_op`.
5. **Idea B**: synergy only — it moves `oos_insert` into the same window the notify needs and inherits fewer
   OOS repl records thanks to dedup; the only caution is preserving the pre-append ordering.
