# T6 — Write and upload the CBRD-27230 spec

- label: `wayfinder:task`
- status: open
- assignee: (unclaimed)
- blocked-by: [T4](./T4-lock-cleanup-architecture.md) (closed — contract locked), [T5](./T5-capture-cbrd-26950-locked-design.md), [T8](./T8-write-path-mechanics-of-reuse.md)
- map: [CBRD-27230 OOS UPDATE dedup](../map.md)

## Question

Assemble the final Korean spec via `cubrid-jira-issue-write` (Issue Triage block — 목적 / 이유(AS-IS·TO-BE) / 방안), covering:

- unchanged = **not assigned in the UPDATE statement** (no content comparison; content-equality dedup explicitly out of scope);
- the locked cleanup architecture (T4, closed) and its invariant-level contract — all seven clauses of the T4 resolution;
- the vacuum / crash-recovery / MVCC / rollback / replication / SA_MODE story, citing the T1–T3 findings; per Q5(a) the **replication protocol changes are a section of this same spec** (marker item, replica fixup, replica vacuum protection, applylogdb handling);
- the Implementation sketch from T8 (write-path mechanics of reuse);
- relationship to CBRD-26950's identity stamp (T5) — dependency or orthogonality;
- the superseding ownership-invariant wording and the new test scenarios sketch;
- out-of-scope list from the map.

**HITL gate**: the dev reviews the markdown before upload. On approval, upload replaces the ticket's current 작성 중 description. Also update OOS-CONTEXT.md's ownership invariant / limitation rows to point at the accepted design (via the context repo, per `cubrid-oos-context` policy).

## Resolution

(pending)
