# 04: Teach the contract and object model

**What to build:** Give a target maintainer the first complete learning slice: understand what the page-buffer Module owns, distinguish its six core objects and four independent state axes, verify those concepts in the pinned source, and know where to continue.

**Blocked by:** 03: Establish the document-set shell

**Status:** ready-for-agent

- [ ] The page begins with the maintainer problem and teaches the conceptual successful-fix postcondition before algorithms.
- [ ] VPID, BCB, frame, `PAGE_PTR`, global `fcnt`, and holder each have distinct meaning, owner, and lifetime.
- [ ] The Module boundary and caller/dependency seams show what the page buffer owns and what callers still complete.
- [ ] Residency, ownership, concurrency, and durability are presented as independent state axes.
- [ ] Fixed, resident, dirty, durable, flushed, evicted, invalidated, and deallocated are not used as synonyms.
- [ ] A simplified English object/ownership visual shows the non-linear object graph without revision-sensitive catalogs.
- [ ] An English state-axes visual uses the confirmed vocabulary and does not depend on color alone.
- [ ] Exact pinned-source anchors sit near implementation-specific claims.
- [ ] The Predict–Locate–Explain exercise produces an object/lifetime sketch and a defensible state distinction.
- [ ] A concise adjacent model answer explains the reasoning and evidence boundary.
- [ ] Navigation reaches the guide entry, next learning page, source map, and invariant index.
- [ ] Aggregate validation passes for this completed slice.
