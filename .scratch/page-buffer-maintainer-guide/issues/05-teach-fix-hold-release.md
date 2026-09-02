# 05: Teach fix, hold, and release

**What to build:** Give a core maintainer a complete normal acquisition-and-release trace that connects caller intent, hit/miss convergence, latch grant, ownership ledgers, borrowed pointer lifetime, and matching release debt.

**Blocked by:** 04: Teach the contract and object model

**Status:** ready-for-agent

- [ ] Fetch intent is explained as caller knowledge rather than convenience, including expected non-acquisition.
- [ ] Latch mode and wait condition remain separate choices.
- [ ] One normal resident hit and the cold-miss path converge on the same caller-visible postcondition.
- [ ] The page marks every identity recheck and the point where ownership debt becomes committed.
- [ ] Global `fcnt` and the per-thread holder ledger are distinguished, including nested fixes returning the same pointer.
- [ ] Release variants are taught in one canonical location and every successful acquisition creates exactly one debt.
- [ ] Borrowed page and page-local pointer lifetime ends with ownership, regardless of address equality.
- [ ] Lock-free internals, promotion, and ordered watchers are named and routed to advanced material rather than taught prematurely.
- [ ] The retained hit/miss convergence visual passes wording and evidence review.
- [ ] A new English two-ledger visual explains replacement exclusion versus current-thread debt.
- [ ] The Predict–Locate–Explain exercise produces an annotated call path and debt ledger with an adjacent model answer.
- [ ] Aggregate validation passes for this completed slice.
