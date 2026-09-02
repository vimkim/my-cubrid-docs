# 13: Ship advanced acquisition concurrency

**What to build:** Give an advanced maintainer a source-traceable explanation of optimized and multi-page acquisition protocols while preserving the normal ownership contract learned in the core path.

**Blocked by:** 12: Ship symptom-driven diagnosis

**Status:** ready-for-agent

- [ ] Lock-free READ hits are explained through their invariant and memory-ordering dependence rather than as a separate caller contract.
- [ ] VPID-keyed load serialization distinguishes one resident-identity owner from physical device I/O claims.
- [ ] Latch queue, conditional rejection, wait, timeout, wakeup, and barging limits retain their evidence boundaries.
- [ ] Blocking promotion identifies released ownership and every observation that becomes stale.
- [ ] Ordered watchers explain rank/group choice, conditional acquisition, release/sort/refix, partial failure, and `page_was_unfixed` revalidation.
- [ ] Strict FIFO, starvation freedom, and exact timeout timing are not claimed without proof.
- [ ] Exact pinned-source anchors and representative heap/B-tree callers accompany mechanism claims.
- [ ] An English latch-transition visual is retained only if it materially clarifies the advanced relationships.
- [ ] The page links back to the canonical core ownership and lifetime explanations.
- [ ] Aggregate validation passes for this advanced route.
