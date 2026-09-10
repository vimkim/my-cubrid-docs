# 07: Integrate and enforce the specification's acceptance gates

**What to build:** One evidence-backed acceptance decision for the final integrated effective-key routing revision, covering the entire specification rather than combining unrelated green results from different revisions.

**Blocked by:** 04 — Prove failure cleanup and unaffected write behavior; 05 — Prove server-mode lifecycle correctness; 06 — Measure resource savings and regression risk.

**Status:** blocked

**Parent:** [Effective-key routing specification](../spec.md).

**Execution gate:** Integration edits, verification runs, commits, pushes, and release/PR publication require the applicable subsequent authorization. Ticket completion must not close or modify the parent spec automatically.

- [ ] Pin the final integrated source revision and tested binaries; identify which earlier results remain applicable and rerun every check or measurement affected by intervening changes.
- [ ] Map all 37 user stories, all 15 implementation decisions, and all 14 testing decisions to authoritative evidence. Missing or indirect evidence is not completion.
- [ ] Verify all legal key types/expressions and the scoped INSERT/UPDATE paths use the agreed route without silent type-dependent fallback or replacement full-row probes.
- [ ] Confirm stored-key equivalence, original assignment preservation, exactly-once real increments/LOB operations, context lifetime, and early/final destination agreement.
- [ ] Confirm final validation, representation handling, locks, scan caches, indices, movement, OOS ownership, error behavior, transaction cleanup, and unaffected paths are preserved.
- [ ] Reconcile standalone, server, failure, recovery/vacuum, and resource/timing evidence against the same final behavior; do not substitute SA coverage for server requirements.
- [ ] Review the integrated change against repository standards and the agreed spec, including all stop/reopen conditions and source-indentation requirements. Resolve in-scope findings with renewed verification; do not turn a review into unapproved scope expansion.
- [ ] Apply the benefit gate to the final candidate. A prior ticket's completed report is not a passed performance gate. Unresolved regressions or baseline blockers prevent declaring the full feature accepted.
- [ ] Produce either a fully supported acceptance recommendation or an explicit unmet-gate report requesting the required design decision. Do not claim acceptance through reduced scope, waived legal-key coverage, or inconclusive measurements.
- [ ] Keep the parent spec unchanged and report the final state to the user; do not publish a PR or push merely because verification succeeded.

**Completion evidence:** Full requirement-to-evidence matrix, integrated review findings, final-revision verification and measurements, and explicit acceptance or blocked/unmet-gate disposition. The overall implementation remains unaccepted when required gates are unmet.

**Spec coverage:** All user stories and implementation/testing decisions, especially cross-ticket integration and stop/reopen gates. Tickets 01–03 are transitively required through 04–06.

## Comments

- 2026-09-09 (blocked handoff): User authorized routing review and local commit handoff without push or gate waivers. [Review](../../../cbrd-27089/design/routing-review-213ce80f5-codex.md) found no new implementation defect/scope creep, one optional Standards duplication suggestion, and three retained Spec acceptance limitation groups. [Handoff](../../../cbrd-27089/design/blocked-handoff-213ce80f5-codex.md) points to source commit 213ce80f5, the preliminary matrix and saved evidence. Ticket remains blocked; no new database experiments or final acceptance claim.

- 2026-09-09 (dependency clarification): Wait specifically for the forthcoming CBRD-27237 fix, not an assumed CBRD-27230 solution. User-approved rollback/vacuum regression is necessary but insufficient for ticket 05 closure. Final routing is unchanged; ticket 06 runtime acceptance remains open. See the corrected [completion path](../../../cbrd-27089/design/acceptance-completion-path-213ce80f5-codex.md).

- 2026-09-09: User accepted the lifecycle dependency wait. Final routing remains unchanged; ticket 05 stays blocked and ticket 06's runtime gate stays open. Final acceptance remains blocked. Reopen on a concrete lifecycle-fix patch or a new user direction; integration and verification still require authorization.

- 2026-09-09: Ticket 04 is complete, but ticket 05 remains blocked and ticket 06 measurement delivery does not close its inconclusive runtime gate. Final routing stays unchanged. The [recommended completion path](../../../cbrd-27089/design/acceptance-completion-path-213ce80f5-codex.md) records upstream findings, proposed dependency handling and final-revision proof obligations; the wait-versus-separate-design decision is pending. No acceptance gate changed.

- 2026-09-08: All remaining tickets authorized, but ticket 05 reproduced a baseline rollback/vacuum failure on both engines. Final acceptance remains blocked; no full-matrix/review/measurement completion is claimed. See [unmet-gate report](../../../cbrd-27089/design/tickets04-07-lifecycle-blocker-b871ea386-codex.md). A user decision is required before broadening scope or continuing independent work with this explicit prerequisite.


- 2026-09-10: [Merged-head diagnosis](../../../cbrd-27089/design/ticket06-runtime-diagnosis-988a4d2-codex.md) establishes a reproducible small-row runtime regression at `988a4d2fa`; ticket 06 now awaits the specified tradeoff decision rather than a merely inconclusive measurement. Ticket 05 still awaits CBRD-27237: its local worktree remains at `f4299ac0c` with no engine fix. The failing vacuum regression in the user's worktree remains uncommitted. Final acceptance remains blocked by both dependencies; historical test results are not substituted for final integrated verification. Parent specification and acceptance checkboxes are unchanged.
