# 11: Ship change and verification playbooks

**What to build:** Give a maintainer an end-to-end operational route from a proposed page-buffer change through interface and ownership analysis, negative-path review, representative caller selection, risk-matched evidence, and reproducible disclosure.

**Blocked by:** 10: Ship compact source and invariant references

**Status:** ready-for-agent

- [ ] The change playbook starts with a caller-visible behavior statement and identifies the interface family and owners.
- [ ] The change playbook records state, guards, temporarily dropped protection, dependency seams, success debt, retry behavior, and failure unwind.
- [ ] Every early return is audited against resources and state already acquired.
- [ ] Contract changes and policy changes are separated and routed to appropriate callers and tests.
- [ ] CUBRID legacy indentation and C++ syntax guard requirements are preserved accurately.
- [ ] Negative paths cover expected absence, conditional rejection, timeout, interrupt, loader retry, allocation failure, read/decrypt/validation failure, WAL/DWB/write failure, partial refix, and lifecycle context as applicable.
- [ ] The verification playbook maps risk to focused unit, representative caller, concurrency, fault injection, controlled pressure, or crash/recovery evidence.
- [ ] Verification guidance uses standard CMake, `ctest`, and project-provided test concepts.
- [ ] Runtime probes record revision, build, configuration, workload, observer effects, observed boundary, and untested boundary.
- [ ] Both playbooks link to canonical core explanations, compact references, evidence sources, and open proof obligations without copying them.
- [ ] Aggregate validation passes for both operational routes.
