# 17: Ship failure and proof-obligation guidance

**What to build:** Give an advanced maintainer a disciplined route from a source-visible exceptional path to the mechanism, state ledger, required fault or schedule, verification seam, and sole current status—without manufacturing production defect claims.

**Blocked by:** 13: Ship advanced acquisition concurrency; 14: Ship advanced replacement progress; 15: Ship advanced recovery and lifecycle; 16: Ship specialized-interface guidance

**Status:** ready-for-agent

- [ ] Every current `VS-*` entry is routed to the canonical core or advanced mechanism that explains it.
- [ ] Each candidate distinguishes source-visible control flow, reachability, surviving state, production impact, and current-branch status.
- [ ] Ownership failures identify global count, latch grant, holder, waiters, identity, and retry postconditions.
- [ ] Flush failures identify DIRTY/FLUSHING, saved lower bound, copied generation, waiters, DWB/TDE/I/O ownership, and retry postconditions.
- [ ] Concurrency proof obligations identify the required interleaving and memory-order argument rather than relying on absence of observed failure.
- [ ] Historical findings remain explicitly revision-bound and do not become current tickets through this guide.
- [ ] Fault injection, controlled schedule, pressure, and crash verification are selected at the highest relevant seam.
- [ ] The uncertainty registry remains the sole mutable status source; this page links by ID and does not copy status prose.
- [ ] The page links to the verification playbook and every relevant canonical mechanism.
- [ ] Aggregate validation passes for the complete advanced route.
