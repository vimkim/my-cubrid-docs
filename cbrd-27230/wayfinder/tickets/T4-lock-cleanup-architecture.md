# T4 — Lock the cleanup architecture: OOS update log vs generation-id compare

- label: `wayfinder:grilling`
- status: open
- assignee: (unclaimed)
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

(pending)
