# 07: Teach one flush generation

**What to build:** Give a core maintainer a complete generation-based durability trace from logged mutation through stable copy, WAL gating, DWB/direct submission, concurrent re-dirty, completion, and ordinary rollback.

**Blocked by:** 06: Teach caller-completed correctness

**Status:** ready-for-agent

- [ ] Write permission, recoverability, transaction durability, and page propagation are explicitly separated.
- [ ] Page LSA and `oldest_unflush_lsa` have distinct roles and a worked example.
- [ ] Stable snapshot, DIRTY clearing, FLUSHING state, protection release, WAL force, and write submission appear in correct order.
- [ ] Concurrent re-dirty is explained as a new resident generation that survives successful old-generation completion.
- [ ] Ordinary failure restores the dirty generation and checkpoint lower-bound material before completing cleanup.
- [ ] TDE, DWB, direct-write, and home-page persistence boundaries are labeled without overclaiming event names.
- [ ] Runtime evidence appears only in bounded cards stating setup, observation, supported conclusion, unsupported conclusion, and receipt.
- [ ] The durability visual retains responsibility lanes and integrates the useful re-dirty timeline in English.
- [ ] Exact pinned-source anchors accompany implementation-specific statements and unresolved early-return candidates retain their status.
- [ ] The Predict–Locate–Explain exercise produces a generation timeline with an adjacent evidence-aware model answer.
- [ ] Aggregate validation passes for this completed slice.
