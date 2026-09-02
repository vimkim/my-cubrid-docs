# 06: Teach caller-completed correctness

**What to build:** Give a core maintainer one complete caller trace showing exactly what successful page acquisition guarantees and what a heap mutation must still validate, log, dirty, and release on every exit.

**Blocked by:** 05: Teach fix, hold, and release

**Status:** ready-for-agent

- [ ] One representative heap mutation is traced from fetch/latch choice through validation, mutation, logging, page LSA, dirtying, release, and every error exit.
- [ ] Module guarantees and caller obligations are separated in a two-column contract ledger.
- [ ] Page latch and transaction lock are described as protecting different state.
- [ ] `NEW_PAGE` is taught as materialization knowledge after allocation, not as an allocation operation.
- [ ] A short B-tree contrast introduces conditional acquisition, promotion, or restart without teaching advanced internals.
- [ ] Page type, on-page layout, record validity, logging semantics, and higher-level retry remain caller responsibilities.
- [ ] Exact pinned-source anchors cover the representative caller and its page-buffer seam.
- [ ] The source exercise requires tracing every cleanup exit rather than only the successful path.
- [ ] The adjacent model answer explains where fix success stops being sufficient evidence.
- [ ] Navigation reaches the neighboring core pages and relevant acquisition/recovery advanced routes.
- [ ] Aggregate validation passes for this completed slice.
