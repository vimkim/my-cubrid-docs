# T4 — Lock the cleanup architecture: OOS update log vs generation-id compare

- label: `wayfinder:grilling`
- status: closed
- assignee: dhkim (claimed 2026-08-13)
- blocked-by: [T1](./T1-pg-toast-unchanged-value-reuse.md), [T2](./T2-oos-replication-replay-under-chain-reuse.md), [T3](./T3-cleanup-paths-under-chain-reuse.md)
- map: [CBRD-27230 OOS UPDATE dedup](../map.md)

## Question

Decide the dedup cleanup architecture (HITL — grilling + domain-modeling with the dev). Standing preference: **option 2, the OOS update log** — verify it withstands T3's failure scenarios (crash mid-update, vacuum block-retry idempotency, rollback of the updating transaction, MVCC snapshot readers, SA_MODE) and T2's replication findings, informed by T1's PG model. Fall back to option 1 (or a hybrid) only with evidence.

The resolution must state, at invariant level (no code):

- the chosen architecture and why the alternative lost;
- what replaces the old/new head-OID disjointness assumption — the new ownership rule for shared chains;
- the update-log contract (if option 2): when it is written, what it lists, how vacuum consumes it exactly once;
- whether dedup depends on the CBRD-26950 generation id at all (T3 §4);
- the superseding text for OOS-CONTEXT's ownership invariant.

## Resolution

(2026-08-13, HITL — all five clauses decided by the dev.) **Option 2 — the OOS notify log — is locked.** The invariant-level contract:

1. **Emission (commit-conditional, §3.4a)**: UPDATE registers the notify as a *postpone action* (`log_append_postpone`; precedent `RVHF_MARK_REUSABLE_SLOT`), so `RVOOS_NOTIFY_VACUUM` materializes only at commit. Invariant: *the notify record exists on disk only if the UPDATE committed.* The §3.5 ordering pin attaches to the postpone registration — registered before the heap update record, so "heap update durable ⇒ notify eventually durable" (no chain leak). This also fixes CBRD-27237 as a side effect.
2. **Content (§3.1)**: per dropped chain, one `(head OOS OID, expected generation)` pair — the CBRD-26950 `oos_chain_ref` shape — plus OOS file identity. Dropped = the old chain of every *assigned* OOS-backed attribute (unchanged = not assigned; no comparison, no read). An UPDATE that drops nothing emits nothing.
3. **Consumption (§3.2)**: `RVOOS_NOTIFY_VACUUM` (=139, already exists, already MVCC-classified, not heap-classified) gets its first emitter; vacuum handles it in a new `vacuum_process_log_block` branch, each delete in its own per-record sysop. Retry safety comes entirely from CBRD-26950's `oos_delete(expected_generation)` no-op — option 2 has no idempotency of its own (§3.3).
4. **Removals**: the forward-walk (`vacuum_forward_walk_reclaim_oos`) and its whole undo-image-parsing machinery are removed, not gated. **DELETE is untouched** — the REMOVE path already reclaims a deleted row's chains inside the slot-removal sysop; a notify there would double-delete.
5. **Dependency**: CBRD-26950 is a **hard prerequisite**; the two are orthogonal mechanisms and both are required (stated explicitly in the spec, not left implicit).
6. **Superseding ownership invariant** (goes into OOS-CONTEXT.md via T6): *"An OOS value chain is owned by the newest logical record version that references it; older versions hold borrowed references via their undo images. A chain is released exactly once — by the commit of the UPDATE that dropped it (notify record, consumed by vacuum) or by vacuum's removal of the row's last version (REMOVE path). Undo images are never a deletion source."*
7. **Replication (Q5a)**: the T6 spec includes the replication protocol changes as a section of the same document — per-reused-attribute marker item, replica-side fixup from its own previous row version (non-expanding fetch), replica-side vacuum protection, `applylogdb` sql.log handling (T2 findings). Not a separate ticket.

**Mechanism refinement (post-lock, from [T8](./T8-write-path-mechanics-of-reuse.md))**: the clause-1 invariant stands unchanged, but a bare `log_append_postpone` cannot implement it — vacuum's stream is fed only by MVCC *undo* appends, and `logtb_complete_mvcc` runs before `log_tran_do_postpone`, so a postpone-materialized record would never reach a vacuum worker. T8's findings list three viable shapes; recommended: emit the notify from a commit hook placed **before** `logtb_complete_mvcc`. T6 must spell out the chosen shape.

**Why option 1 lost**: generation equality cannot distinguish "dead" from "shared with the live version" (same pair in undo image and live stub — T3 §2); its repairs converge on per-update re-stamping or live-record fetches, i.e. more I/O and complexity while keeping the log-image-parsing machinery that option 2 deletes. The pass-2 set-difference variant (T3 §6) is rollback-safe but strictly more complex and was not preferred.

Evidence: [T1](./T1-pg-toast-unchanged-value-reuse.md) (PG has no generation id / update log because it decides at UPDATE time — the notify log is that decision persisted), [T2](./T2-oos-replication-replay-under-chain-reuse.md), [T3](./T3-cleanup-paths-under-chain-reuse.md), [T7/CBRD-27237](./T7-forward-walk-rollback-exposure.md).
