# T6 — Write and upload the CBRD-27230 spec

- label: `wayfinder:task`
- status: open
- assignee: (unclaimed)
- blocked-by: [T4](./T4-lock-cleanup-architecture.md), [T5](./T5-capture-cbrd-26950-locked-design.md)
- map: [CBRD-27230 OOS UPDATE dedup](../map.md)

## Question

Assemble the final Korean spec via `cubrid-jira-issue-write` (Issue Triage block — 목적 / 이유(AS-IS·TO-BE) / 방안), covering:

- unchanged = **not assigned in the UPDATE statement** (no content comparison; content-equality dedup explicitly out of scope);
- the locked cleanup architecture (T4) and its invariant-level contract;
- the vacuum / crash-recovery / MVCC / rollback / replication / SA_MODE story, citing the T1–T3 findings;
- relationship to CBRD-26950's identity stamp (T5) — dependency or orthogonality;
- the superseding ownership-invariant wording and the new test scenarios sketch;
- out-of-scope list from the map.

**HITL gate**: the dev reviews the markdown before upload. On approval, upload replaces the ticket's current 작성 중 description. Also update OOS-CONTEXT.md's ownership invariant / limitation rows to point at the accepted design (via the context repo, per `cubrid-oos-context` policy).

## Resolution

(pending)
