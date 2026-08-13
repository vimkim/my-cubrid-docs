# T6 — Write and upload the CBRD-27230 spec

- label: `wayfinder:task`
- status: closed
- assignee: dhkim (claimed 2026-08-13)
- blocked-by: [T4](./T4-lock-cleanup-architecture.md) (closed — contract locked), [T5](./T5-capture-cbrd-26950-locked-design.md), [T8](./T8-write-path-mechanics-of-reuse.md)
- map: [CBRD-27230 OOS UPDATE dedup](../map.md)

## Resolution

(2026-08-13) Spec written, grill-reviewed (2 rounds, APPROVED — 15+ citations source-verified at `725a32c6e`), **dev-approved at the HITL gate** (including the embedded emission-shape decision: commit hook before `logtb_complete_mvcc`), committed and pushed (`my-cubrid-jira` `8821d04`, `issues/CBRD-27230-oos-update-dedup_725a32c_claude.md`), and **uploaded to [CBRD-27230](http://jira.cubrid.org/browse/CBRD-27230)** with read-back verification, replacing the 작성 중 description. OOS-CONTEXT.md updated with the superseding ownership invariant and accepted-design notes. **This was the map's final act — destination reached.**

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
