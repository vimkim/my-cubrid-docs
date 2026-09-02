# 08: Teach frame replacement

**What to build:** Give a core maintainer a complete path from an unfixed resident page to safe frame reuse, clearly separating hard eligibility predicates from replaceable selection and progress policy.

**Blocked by:** 07: Teach one flush generation

**Status:** ready-for-agent

- [ ] Victim eligibility includes identity, ownership, dirty/flushing, waiter/transient, and final protected revalidation requirements.
- [ ] A counterexample demonstrates why `fcnt == 0` alone is insufficient.
- [ ] LRU placement, private/shared domains, quotas, candidate queues, and direct assignment are labeled as policy or advanced mechanisms.
- [ ] Direct-victim assignment is presented as revocable when a candidate becomes fixed again.
- [ ] Victimization, invalidation, unfix, flush, and logical deallocation are distinguished.
- [ ] Existing runtime evidence is not presented as victim proof because it did not force eviction.
- [ ] A new English visual shows hard predicates gating policy choices and does not depend on color alone.
- [ ] Exact pinned-source anchors accompany the candidate and final-recheck path.
- [ ] The Predict–Locate–Explain exercise produces a predicate-versus-policy table and adjacent model answer.
- [ ] Navigation reaches the capstone and advanced replacement-progress route.
- [ ] Aggregate validation passes for this completed slice.
