# 09: Ship the maintainer capstone

**What to build:** Let a core maintainer demonstrate connected maintenance reasoning by reviewing one source-visible ownership or durability candidate without implementing it or promoting it into a production defect claim.

**Blocked by:** 08: Teach frame replacement

**Status:** ready-for-agent

- [ ] The capstone provides a reusable change-impact template covering behavior, owners, state, guards, invariants, unwind, caller impact, evidence seam, and remaining uncertainty.
- [ ] One review packet covers holder-allocation cleanup after latch/fix grant while retaining candidate status.
- [ ] One review packet covers dirty/FLUSHING cleanup around an exceptional write path while retaining candidate status.
- [ ] Each packet names the source evidence already available and the fault or schedule still required.
- [ ] The review rubric distinguishes a source-grounded argument from runtime proof.
- [ ] The reader completes either packet for core completion and both for advanced preparation.
- [ ] Concise model answers explain evidence limits rather than prescribing an unverified fix.
- [ ] The applied-path handoff requires one controlled caller regression or narrow runtime probe on the target revision.
- [ ] Real change-impact plans require review by another maintainer before counting as readiness evidence.
- [ ] Navigation reaches the playbooks, advanced route, source inventory, and uncertainty registry.
- [ ] Aggregate validation passes for the completed core learning path.
