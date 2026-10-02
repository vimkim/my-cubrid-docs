# CBRD-27443 implementation map

Work-tracker: 261. Main orchestrator owns this map and ticket statuses.
Engine base: `c63a3b993be552ef6ad3ce244c386d5081147958`.
Engine worktree: `/home/vimkim/gh/cb/CBRD-27443-fd-clean`.
Shell worktree: `/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean`, branch `tc/CBRD-27443-fd-clean`, base `dfb7da195`.

| Ticket | Blocked by | Status |
|---|---|---|
| 01 | none | baseline preparation |
| 02 | 01 | ready-for-agent |
| 03 | 02 | ready-for-agent |
| 04 | 01 | ready-for-agent |
| 05 | 02 | ready-for-agent |
| 06 | 05 | ready-for-agent |
| 07 | 01 | ready-for-agent |
| 08 | 03, 04, 06, 07 | ready-for-agent |

One fresh worker per ticket, numeric order, one active worker. Main performs Standards and Spec review against each dispatch base and the original base for final integration. No additional reviewer agents.

Baseline preparation uses debug_gcc and the retained namespace probe with PID-1 reaping. Historical probe results do not qualify the new build. Required fixed-binary evidence remains outstanding for all tickets.
