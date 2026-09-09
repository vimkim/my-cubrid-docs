# 01: Characterize and safely share existing routing behavior

**What to build:** A verifiable routing baseline and shared partition-selection behavior that preserve current SQL results, validation, and OOS ownership while making effective-key routing testable without duplicating partition semantics. Perform necessary behavior-preserving prefactoring before the replacement write path is introduced.

**Blocked by:** None (can start immediately).

**Status:** resolved

**Parent:** [Effective-key routing specification](../spec.md).

**Execution gate:** Publication approves the breakdown only. Engine edits, test execution, experiments, commits, and pushes need subsequent authorization. No parent-spec changes are authorized by this ticket.

- [x] Pin characterization to source revision `b871ea386d2c5419b7abae07dda58b9b7f36377a`; identify build mode, fixture state, and actual revision for every result.
- [x] Establish SQL-level reference observations for range/list/hash, expression keys, boundaries, NULL, explicit-partition validation, and missing destinations, including row values and owner-file observations.
- [x] Prefer existing SQL and failure-injection seams; introduce at most the focused effective-key routing seam allowed by the spec, not separate test-only interfaces for every helper.
- [x] Share expression evaluation and match/result semantics while retaining record reading, root/child representation handling, wrapper validation, and context ownership. Existing callers remain behaviorally unchanged.
- [x] Use independently owned equivalent input values and isolated state for differential tests: the existing probe mutates values and can perform LOB work, so reusing one mutable cache is not a valid oracle.
- [x] Verify successful and failing context reuse across rows; no dangling expression bindings or stale previous-row values.
- [x] Preserve the current probe and its protections as the baseline; do not introduce a partially optimized production path in this prefactor.
- [x] Record baseline failures as attributed evidence and escalate anything that prevents a trustworthy oracle; do not waive coverage or fix unrelated defects silently.

**Completion evidence:** Before/after behavior comparison, relevant regression results, seam contract, and an explanation of any prefactoring. Functional assertions concern outcomes, not private helper call order.

**Spec coverage:** Shared selection and context contracts; user stories 1, 3–9, 30, 32, 36. Later tickets establish candidate-path coverage.

## Comments

- 2026-09-08 — User authorized implementation of ticket 01. Claimed by Codex; work-tracker item 74. Authorization covers scoped engine/test edits and isolated local verification, not later tickets, parent-spec changes, commits, or pushes.
- 2026-09-08 — Completed: private expression/match extraction, five SQL/ownership characterizations, and 43/43 checks before and after in independent SA databases. Standards/spec reviews have no outstanding findings. Probe/rebuild and final routing retained. No baseline failures; no parent-spec change, commit, push, or later-ticket implementation.

## Answer

[Implementation and verification report](../../../cbrd-27089/design/ticket01-routing-prefactor-b871ea386-codex.md) records the helper contract, exact SQL/owner-file observations, provenance, review, and retained evidence.

Context qualification: successful rows reuse a live statement context; a later failing row triggers the existing context cleanup. A subsequent successful statement verifies recovery, not continued use of a cleared context. No new temporary binding is introduced; effective-key binding restoration remains a later-ticket obligation. Reference and candidate tests used independently created databases, not one mutating cache.

Safety qualification: built through the local build workflow and ran selected existing binaries with private fixtures. Did not run the unqualified build-test recipe because its configured CTest setup/cleanup embeds shared database paths. Final results: SHOW/routing 10/10, storage 25/25, transactions 8/8. No server lifecycle or performance claim.

Ticket 02's dependency on this ticket is satisfied; its execution still requires separate user authorization.
