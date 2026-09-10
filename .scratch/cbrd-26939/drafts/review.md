# Proposed review package

Architecture Q1–Q9 is confirmed. Review only these concrete test seams and work slices; do not reopen accepted choices.

Public seams: SQL transaction results plus CDC API; flashback utility; lifecycle utilities including an actual baseline engine; existing JDBC concurrency scenario. Observable assertions cover byte-exact values, transaction outcomes, checked errors, compatibility and server survival. No private helper unit tests are proposed.

| Ticket | Blocked by | Delivery |
|---|---|---|
| 01 Activation | none | Fresh/current and existing/offline activation, compatibility protection, lifecycle behavior |
| 02 DELETE | 01 | Byte-correct CDC DELETE after vacuum, legacy error and publication failure handling |
| 03 INSERT/UPDATE | 02 | Both images survive later changes across supported DML paths |
| 04 Flashback/restart | 03 | Shared historical reads across restart, rollover and backup/restore |
| 05 JDBC crash | none | Independent diagnosis, causal fix and regression for bug_bts_4633 |
| 06 Integration | 01–05 | Original cases, contract matrix, review, costs and exact-commit CI |

Tickets are vertical end-to-end slices. Ticket 05 has no CDC blocker. The integration branch must not be presented as a supported release before all required behavior is complete.

On approval, publish spec.md and one file per issue to the configured local feature tracker with ready-for-agent status. Then implement available blockers-first tickets via TDD at these agreed seams.
