# T3 — Cleanup paths under chain reuse: exact failure scenarios and the two candidate fixes

- label: `wayfinder:research`
- status: closed
- assignee: claude-research (fired at charting)
- blocked-by: (none)
- map: [CBRD-27230 OOS UPDATE dedup](../map.md)

## Question

Today every OOS cleanup path assumes each value chain is owned by exactly one logical heap-record version (old/new head-OID disjointness after UPDATE). Chain reuse breaks that. Establish precisely what breaks and evaluate the ticket's two candidate architectures.

1. **Enumerate the cleanup paths** on `feat/oos` (`vacuum_oos.cpp`, `heap_oos.cpp`):
   - vacuum forward-walk (`vacuum_forward_walk_oos_delete_atomic`) — derives old head OOS OIDs from UPDATE/DELETE undo images;
   - within-sysop delete (`vacuum_heap_oos_delete_within_sysop`);
   - SA_MODE eager delete (`heap_oos_delete_unreferenced`) — note it already compares old vs new head OIDs.
   For each: write the concrete failure sequence under chain reuse (an UPDATE that keeps attribute A's chain but replaces attribute B's; then vacuum processes the update's undo image).
2. **Option 1 (generation-id compare at vacuum time)** — the JIRA sketch: vacuum heap & forward-walk "look at the generation id, go find it, delete when heap generation id == oos generation id". Against the CBRD-26950 identity-stamp design (page-local 4-byte counter stamped in chunk header AND the heap stub; `oos_delete(expected_generation)` no-ops on mismatch — see `my-cubrid-docs/cbrd-26950/CBRD-26950-oos-generation-identity-stamp_01d110e_claude.md`): can that stamp distinguish "dead chain" from "chain shared with the live record version"? (Suspicion: no — a reused chain has the SAME (head OID, generation) in both the undo image and the live stub, so equality says *delete* exactly when it must not. Option 1 as written may require vacuum to visit the live heap record. Spell out what option 1 actually requires and its cost/complexity.)
3. **Option 2 (OOS update log)** — a new log record written at UPDATE listing exactly the chains the update *dropped* (assigned attributes' old chains); vacuum deletes chains when it encounters this log instead of re-deriving them from undo images. Specify the minimal contract: what it must record, idempotency under vacuum block retry (the CBRD-26950 re-run scenario), rollback of the updating transaction (log written but update undone — chains must survive), crash between heap update and log write, interaction with the per-record sysop structure, and whether DELETE (not just UPDATE) also moves to this scheme.
4. **The decoupling question** — under option 2, does dedup need the generation id at all, or does the generation stamp remain solely CBRD-26950's slot-reuse defense (orthogonal, still valuable)?
5. **Fit-check the SA_MODE eager path** — does its existing old∩new comparison already give correct dedup behavior for SA_MODE, unchanged?

Sources (local, read-only): this worktree, OOS-CONTEXT.md §3–4, `my-cubrid-docs/cbrd-26950/` (verification report + identity-stamp doc).

## Resolution

Only the **forward-walk** (`src/query/vacuum_oos.cpp:154`, fed from `vacuum.c:3591`/`:3730`) breaks
under chain reuse — it deletes every chain named by the undo image, including reused ones the live
record still points at: silent data loss. The **within-sysop** path (`vacuum_oos.cpp:400`) is a
downstream casualty (re-deletes an already-freed chain; hard error, no probe, stalls the slot) and
widens CBRD-26950 to a single uninterrupted vacuum run. The **SA_MODE eager** path
(`heap_oos.cpp:702`) is already correct, unchanged — it does the `old ∖ new` difference the others
lack. **Option 1 is refuted**: a reused chain carries the *same* `(head OID, generation)` in undo
image, live stub and chunk header, so equality fires exactly when deleting is wrong; the repairs are
re-stamping (an OOS page write per reused chain per UPDATE) or fetching the live version (and then
the generation is unused). **Option 2 is sound and is the bigger simplification** — reuse the
existing emitter-less `RVOOS_NOTIFY_VACUUM`; DELETE keeps the REMOVE path; the forward-walk is
removed, not gated, which retires the whole log-image-parsing machinery. Two things must be pinned:
append the record before the heap update record (else crash ⇒ leak), and make emission
commit-conditional (rollback). Dedup does **not** need the generation id; CBRD-26950 stays required
and orthogonal for block-retry safety. Adjacent, needs runtime confirmation: the current forward-walk
looks exposed to *rolled-back* UPDATEs independent of dedup (§7).

Findings: [../findings/T3-cleanup-paths-under-chain-reuse.md](../findings/T3-cleanup-paths-under-chain-reuse.md)
