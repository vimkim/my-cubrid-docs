# 02: Route partitioned INSERTs without a full-row probe

**What to build:** Partitioned inserts that select their destination from an effective key and build the full row once, preserving final values and correct per-heap OOS ownership across all legal key types and partition expressions.

**Blocked by:** 01 — Characterize and safely share existing routing behavior.

**Status:** resolved

**Parent:** [Effective-key routing specification](../spec.md).

**Execution gate:** Publication is not authorization to edit the engine, execute tests or experiments, commit, or push. This INSERT milestone is not approval to ship an incomplete replacement for the full INSERT/UPDATE scope.

- [x] Develop through red/green behavior slices using SQL insertion, selected-partition observations, stored values, and OOS owner inspection; retain a safe differential reference from ticket 01.
- [x] Obtain an owned effective key that honors assignment state, omitted values, representation defaults, already evaluated dynamic defaults/generated values, and column-domain conversions without mutating original assignments.
- [x] Cover all baseline-legal key types and expressions: integer widths, temporal variants, CHAR/VARCHAR, padding/collation behavior, and range/list/hash. Include NULL, direct-partition writes, and missing destinations. No silent type-specific fallback.
- [x] Reuse existing normalization/codec semantics; a scalar-only round trip is allowed. Do not reconstruct the whole inline row or a fabricated partial full-record layout merely for routing. Stop and reopen design if equivalence needs excessive duplicated semantics.
- [x] Key-only routing performs no LOB deletion/copy, OOS insertion, or OOS publication reset, and leaves no temporary expression binding alive after its owned value is freed.
- [x] Use destination-aware normal first-pass transformation, not the existing second-pass contract that assumes increments already ran. Preserve source cache identity separately from the destination OOS owner.
- [x] Retain final routing, explicit validation, representation patching, locks, index behavior, and partition scan-cache selection. Early and final destinations agree.
- [x] Demonstrate small FORCE_OUTLINE values, ordinary large uncompressed payloads, several externalized attributes, and an OOS-backed string key with correct owner files. Preserve the pre-insertion OOS-plus-big-record rejection gate.
- [x] Preserve non-OOS inserts and the final copy-area lifetime. One full-row transformation does not prohibit codec work, OOS payload serialization, or buffer retries; report structural/resource observations separately from behavioral assertions.
- [x] Keep the prior UPDATE path correct until ticket 03 transitions it. Do not alter REPLACE/duplicate-key probes or shared storage policy as collateral scope.

**Completion evidence:** Complete legal-key INSERT coverage, differential equivalence, ownership results, and explicit scope of the remaining UPDATE transition. No performance improvement is presumed.

**Spec coverage:** User stories 1–14, 22–24, 30, 36–37; effective-key, normalization, first-pass destination, and INSERT force contracts.

## Comments

- 2026-09-08 — User authorized ticket 02 after the ticket-01 handoff. Claimed by Codex, work item 75. Scoped engine/test edits and isolated verification authorized; no commits, pushes, later-ticket work, or parent-spec changes.
- 2026-09-08 — Completed INSERT-only implementation and review. 57/57 SA checks; two paired SQL batches match the frozen ticket-01 reference with timing text excluded. Evidence and scope: [ticket-02 report](../../../cbrd-27089/design/ticket02-insert-routing-b871ea386-codex.md). Work item 75. Parent spec unchanged; no commits/pushes. Ticket 03 requires separate authorization.
