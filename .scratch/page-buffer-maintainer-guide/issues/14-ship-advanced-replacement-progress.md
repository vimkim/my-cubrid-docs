# 14: Ship advanced replacement progress

**What to build:** Give an advanced maintainer a source-traceable account of CUBRID replacement and background progress policy without weakening or obscuring the core victim-eligibility contract.

**Blocked by:** 12: Ship symptom-driven diagnosis

**Status:** ready-for-agent

- [ ] Private/shared LRU domains, zones, quotas, candidate queues, and victim hints are described as pinned implementation policy.
- [ ] Direct victims and revocation are explained as progress mechanisms layered after eligibility.
- [ ] Victim-flush and post-flush coordination are connected to the core dirty-generation model.
- [ ] Daemon ownership and cadence are labeled version-sensitive rather than caller guarantees.
- [ ] AOUT data structures and intended role are described only with the analyzed-default-disabled caveat.
- [ ] The guide never summarizes current CUBRID unconditionally as using 2Q.
- [ ] Existing runtime observations are labeled as no-eviction evidence and do not prove replacement schedules.
- [ ] Exact source anchors and external deep references support every implementation-policy claim.
- [ ] The page links back to the canonical eligibility and generation explanations.
- [ ] Aggregate validation passes for this advanced route.
