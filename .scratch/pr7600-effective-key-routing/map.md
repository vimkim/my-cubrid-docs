# Effective-key routing work map

[Parent spec](spec.md) is unchanged. Dependency readiness is not execution authorization.

| Ticket | Status | Dependencies |
|---|---|---|
| [01 — Characterize/shared routing](issues/01-characterize-and-share-routing.md) | Resolved; 43/43 before and after | None |
| [02 — INSERT routing](issues/02-route-partitioned-inserts.md) | Resolved; 57/57 SA checks and paired SQL equivalence | 01 satisfied |
| [03 — UPDATE/increments](issues/03-route-updates-and-increments.md) | Resolved; 72/72 SA checks, forced retries, paired SQL | 02 satisfied |
| [04 — Failure cleanup](issues/04-verify-failure-cleanup.md) | Resolved; cleanup proofs and affected SQL suites pass | 03 satisfied |
| [05 — Server lifecycle](issues/05-verify-server-lifecycle.md) | Blocked: baseline rollback/vacuum defect; work item 82 | 03 satisfied |
| [06 — Measurements](issues/06-measure-benefit-and-regressions.md) | Resolved measurement delivery; runtime acceptance inconclusive/unmet | 03 satisfied |
| [07 — Integration/gates](issues/07-integrate-and-enforce-gates.md) | Blocked by 05 and unmet 06 runtime gate; not accepted | 04, 05, 06 |

Ticket 01 evidence: [report](../../cbrd-27089/design/ticket01-routing-prefactor-b871ea386-codex.md). Work-tracker item 74. No commit or push performed.

Ticket 02 evidence: [report](../../cbrd-27089/design/ticket02-insert-routing-b871ea386-codex.md). Work-tracker item 75. INSERT milestone only; UPDATE, fault-cleanup, server, and measurement gates remain. No commit or push performed.

Ticket 03 evidence: [report](../../cbrd-27089/design/ticket03-update-routing-b871ea386-codex.md). Work-tracker item77. UPDATE/increment milestone complete, including a shared-context stale-key fix for duplicate UPDATE/REPLACE. Subsequent04–07 status is recorded above.

2026-09-09: user-authorized independent04/06 work delivered under work item82. [Cleanup](../../cbrd-27089/design/ticket04-cleanup-b871ea386-codex.md) and [measurements](../../cbrd-27089/design/ticket06-measurements-b871ea386-codex.md). 24/25 configured binaries pass after three infrastructure-only socket-path reruns; preserved baseline vacuum regression remains red. Resource savings demonstrated, runtime acceptance not established. No final integration acceptance or push.

Local implementation commit `213ce80f54dc54130fcef22e616cb28f4835f6d5` includes01–03 dependencies and04 tests; the05 red test remains unchanged/uncommitted. Post-format rebuild and32 routing/cleanup tests pass. The measurement candidate remains separately identified by its pre-format diff and exact binaries.

2026-09-09: user approved a reviewed, locally committed **blocked handoff**, not full acceptance and not push. [Handoff](../../cbrd-27089/design/blocked-handoff-213ce80f5-codex.md), [two-axis routing review](../../cbrd-27089/design/routing-review-213ce80f5-codex.md), and [preliminary complete matrix](../../cbrd-27089/design/ticket07-preliminary-evidence-matrix-213ce80f5-codex.md). No new routing defects identified; optional test-data duplication and known acceptance evidence gaps remain explicit. Wait specifically for CBRD-27237; final routing unchanged. Source regression remains uncommitted, with an archived patch in the handoff evidence.
