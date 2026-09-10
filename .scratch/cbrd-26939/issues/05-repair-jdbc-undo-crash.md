# 05: Diagnose and repair bug_bts_4633 independently

**What to build:** The existing JDBC concurrency scenario completes without the observed MVCC undo-read server crash, with a causal diagnosis and regression test at the public JDBC interface.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Pin engine/testcase identities and preserve the current GHA core stack as the exact symptom.
- [ ] Reproduce safely in an isolated environment; for a flaky failure, establish and report a useful reproduction rate before theorizing.
- [ ] Minimize the workload and test ranked falsifiable hypotheses rather than attributing the stack to CDC.
- [ ] Implement only the evidence-supported fix and verify its behavior through the real concurrent callers.
- [ ] The final verdict includes actual server survival/core detection; the original script-level OK is insufficient.
- [ ] Keep this result and its regression independently assessable from the CDC change.

## Context

Part of the confirmed CBRD-26939/PR #6864 contract. Use the feature specification and ADR-0004. User approved the ticket breakdown, dependencies and public test seams on 2026-09-08. See [feature specification](../spec.md).
