# T5 — Capture the locked CBRD-26950 generation-id design as external input

- label: `wayfinder:task`
- status: open
- assignee: (unclaimed)
- blocked-by: (none — waits on the external CBRD-26950 effort, not on map tickets)
- map: [CBRD-27230 OOS UPDATE dedup](../map.md)

## Question

CBRD-26950 (vacuum slot-reuse data loss — CRITICAL, high priority, same dev, separate effort) introduces the OOS identity stamp. The working design as of 2026-08-12 (`my-cubrid-docs/cbrd-26950/CBRD-26950-oos-generation-identity-stamp_01d110e_claude.md`, base `01d110e8a`): OOS inline stub 16B→20B (+4B expected generation), chunk header 16B→20B, page slot-0 generation counter, `oos_delete(expected_generation)` no-ops on mismatch/absence.

When that design locks (final review or merge to `feat/oos`), record here what the dedup spec must assume: final stub layout and `OR_OOS_INLINE_SIZE`, generation semantics, the `oos_delete` contract, and any drift from the 2026-08-12 doc. This blocks only final spec assembly (T6) — dedup analysis and the architecture decision proceed in parallel.

## Resolution

(pending)
