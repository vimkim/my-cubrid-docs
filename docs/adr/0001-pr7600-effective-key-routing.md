---
status: accepted
---

# Pursue effective-key routing without splitting all row preparation

For PR #7600, choose a narrow effective-partition-key routing design while preserving per-heap OOS ownership and the existing global preparation/LOB lifecycle. The user accepted this direction after comparing it with retaining the full inline probe and splitting preparation from serialization: the narrow route targets redundant whole-row work without immediately relocating stateful LOB handling. This is a direction for specification, not implementation authorization or a claim of proven feasibility; if key semantics require excessive duplication or measurements show insufficient benefit, reopen the decision.

The user subsequently accepted complete legal-key coverage on the scoped path (no silent type-dependent fallback) and retention of downstream record-based routing for the initial change. Temporary allocation/copying savings may justify replacement even with flat runtime, but a reproducible slowdown beyond measured noise on small non-OOS or nonpartitioned controls requires a new trade-off decision. Error precedence may differ for multiply-invalid statements; successful behavior, single-failure errors, and transactional cleanup remain protected.

Evidence and confirmation status: [research](../../cbrd-27089/design/probe-rebuild-research-b871ea386-codex.md), [interview](../../cbrd-27089/design/design-interview.md). Full preparation split and downstream force-interface redesign are not implicitly authorized. The user confirmed shared understanding by invoking `to-spec` after the final summary; specification is authorized, implementation and experiments are not.
