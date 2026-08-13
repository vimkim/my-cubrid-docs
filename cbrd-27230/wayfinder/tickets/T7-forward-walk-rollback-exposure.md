# T7 — Confirm the forward-walk rollback exposure at runtime

- label: `wayfinder:task`
- status: open
- assignee: (unclaimed)
- blocked-by: (none)
- map: [CBRD-27230 OOS UPDATE dedup](../map.md)

## Question

T3's analysis ([findings §7](../findings/T3-cleanup-paths-under-chain-reuse.md)) suspects the **current** `feat/oos` forward-walk is exposed to **rolled-back UPDATEs**, independent of dedup: if `vacuum_forward_walk_oos_delete_atomic` processes the UPDATE log record of an aborted transaction, it would delete the old chains named in the undo image — chains the rollback-restored record still references. Confirm or refute at runtime:

1. Does vacuum hand aborted transactions' UPDATE records to the forward-walk at all (MVCCID visibility / compensation-record handling in `vacuum.c`)?
2. If yes, reproduce on a stock debug build: OOS-backed row → UPDATE (new chains written) → ROLLBACK → force vacuum of that block → read the row. Adapt the `my-cubrid-docs/cbrd-26950/cbrd-26950-poc.sh` harness.

If **confirmed**: this is an AS-IS data-loss bug — file it as its own JIRA issue (outside this map's destination), and record here that option 2's commit-conditional emission also fixes it (strengthens T4 and belongs in the T6 spec's 이유 section). If **refuted**: record the mechanism that protects aborted transactions, since option 2's commit-conditional design can then mirror it.

## Resolution

(pending)
