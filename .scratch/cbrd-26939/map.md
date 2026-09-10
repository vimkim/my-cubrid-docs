# CBRD-26939 implementation tickets

Approved specification: [spec.md](spec.md).

| Ticket | Status | Dependencies |
| --- | --- | --- |
| [01: Safe activation and compatibility](issues/01-activate-history-format.md) | resolved (`9960c7fc6`) | None |
| [02: Durable DELETE history](issues/02-durable-delete-history.md) | resolved (`7d97d4bf6`) | 01 resolved |
| [03: Durable INSERT and UPDATE history](issues/03-durable-insert-update-history.md) | resolved (`7d97d4bf6`) | 02 resolved |
| [04: Flashback and restarted readers](issues/04-flashback-restart-history.md) | resolved (`7d97d4bf6`) | 03 resolved |
| [05: Independent JDBC undo crash](issues/05-repair-jdbc-undo-crash.md) | ready; unblocked | None |
| [06: Integrate and verify PR](issues/06-integrate-verify-pr.md) | ready; blocked | 01–05 |

Tickets 01–04 implement the CDC/OOS feature. Independent JDBC repair (05) and complete-PR CI verification (06) remain open. See the final CDC report for the exact test scope and timeout/retest evidence.

Implementation branch/worktree: `CBRD-26939-oos-cdc`. Draft PR: https://github.com/CUBRID/cubrid/pull/7897, targeting `feat/oos`. Do not implement directly on `feat/oos`.
