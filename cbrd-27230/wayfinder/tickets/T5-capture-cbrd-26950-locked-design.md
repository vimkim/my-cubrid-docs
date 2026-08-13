# T5 — Capture the locked CBRD-26950 generation-id design as external input

- label: `wayfinder:task`
- status: closed
- assignee: dhkim (claimed 2026-08-13)
- blocked-by: (none — waits on the external CBRD-26950 effort, not on map tickets)
- map: [CBRD-27230 OOS UPDATE dedup](../map.md)

## Question

CBRD-26950 (vacuum slot-reuse data loss — CRITICAL, high priority, same dev, separate effort) introduces the OOS identity stamp. The working design as of 2026-08-12 (`my-cubrid-docs/cbrd-26950/CBRD-26950-oos-generation-identity-stamp_01d110e_claude.md`, base `01d110e8a`): OOS inline stub 16B→20B (+4B expected generation), chunk header 16B→20B, page slot-0 generation counter, `oos_delete(expected_generation)` no-ops on mismatch/absence.

When that design locks (final review or merge to `feat/oos`), record here what the dedup spec must assume: final stub layout and `OR_OOS_INLINE_SIZE`, generation semantics, the `oos_delete` contract, and any drift from the 2026-08-12 doc. This blocks only final spec assembly (T6) — dedup analysis and the architecture decision proceed in parallel.

## Resolution

(2026-08-13) The dev confirmed the CBRD-26950 identity-stamp design is **locked as written** in `my-cubrid-docs/cbrd-26950/CBRD-26950-oos-generation-identity-stamp_01d110e_claude.md` (base `01d110e8a`). What the T6 spec must assume:

- **OOS inline stub 16B → 20B**: head OOS OID (8B) + full length (8B) + expected generation (4B); `OR_OOS_INLINE_SIZE` = 20.
- **Chunk header 16B → 20B**: +4B stored generation.
- **Generation issuance**: per-data-page monotone `uint32` counter in a slot-0 `OOS_PAGE_HEADER` record, issued under the already-held W-latch at insert; redo replays with MAX; failed inserts don't consume values.
- **`oos_delete(thread_p, vfid, oid, expected_generation)`**: compares the head chunk's stored generation against the expected value; mismatch (slot reused) and absence (already reclaimed) are error-free no-ops; only real I/O errors propagate. `oos_chunk_exists` is deleted.
- **`oos_chain_ref` = (head OOS OID, generation)** pair, extracted by `heap_recdes_get_oos_refs` — exactly the pair shape the T4 notify record carries per dropped chain.
