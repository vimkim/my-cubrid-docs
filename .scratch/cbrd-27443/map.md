# CBRD-27443 implementation map

Work-tracker: 261. Main orchestrator owns this map and ticket statuses.
Engine implementation base: `15e7dc8b5b56fd8751d56ccae1fdf87d315bd35d`, adopted with user confirmation after an external fast-forward on 2026-10-02. Earlier fresh baseline at `c63a3b993` is retained separately.
Engine worktree: `/home/vimkim/gh/cb/CBRD-27443-fd-clean`.
Shell worktree: `/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean`, branch `tc/CBRD-27443-fd-clean`, base `dfb7da195`.

| Ticket | Blocked by | Status |
|---|---|---|
| 01 | none | resolved: c4e2bd910, native 1 pass / 121 checks |
| 02 | 01 | resolved: 11ad631c5, native 1 pass / 216 master + 121 existing checks |
| 03 | 02 | ready-for-agent |
| 04 | 01 | ready-for-agent |
| 05 | 02 | ready-for-agent |
| 06 | 05 | ready-for-agent |
| 07 | 01 | ready-for-agent |
| 08 | 03, 04, 06, 07 | ready-for-agent |

One fresh worker per ticket, numeric order, one active worker. Main performs Standards and Spec review against each dispatch base and the original base for final integration. No additional reviewer agents.

Baseline preparation uses debug_gcc and the retained namespace probe with PID-1 reaping. Historical probe results do not qualify the new build. Required fixed-binary evidence remains outstanding for all tickets.
