# CBRD-27443 implementation map

Work-tracker: 261. Main orchestrator owns this map and ticket statuses.
Engine implementation base: `15e7dc8b5b56fd8751d56ccae1fdf87d315bd35d`, adopted with user confirmation after an external fast-forward on 2026-10-02. Earlier fresh baseline at `c63a3b993` is retained separately.
Engine worktree: `/home/vimkim/gh/cb/CBRD-27443-fd-clean`.
Shell worktree: `/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean`, branch `tc/CBRD-27443-fd-clean`, base `dfb7da195`.

| Ticket | Blocked by | Status |
|---|---|---|
| 01 | none | resolved: c4e2bd910, native 1 pass / 121 checks |
| 02 | 01 | resolved: 11ad631c5, native 1 pass / 216 master + 121 existing checks |
| 03 | 02 | resolved: 74ee7520a, native 1 pass / 767 checks |
| 04 | 01 | resolved: 731b39e0f, native 1 pass / 889 checks |
| 05 | 02 | resolved: 8aa8fcab6, native 1 pass / 1,034 checks |
| 06 | 05 | resolved:b0f569011; native1pass/1843 checks; legacy exit codes preserved |
| 07 | 01 | resolved:928e3e503; native1pass/1822 checks |
| 08 | 03, 04, 06, 07 | ready-for-agent |

One fresh worker per ticket, numeric order, one active worker. Main performs Standards and Spec review against each dispatch base and the original base for final integration. No additional reviewer agents.

Baseline preparation uses debug_gcc and the retained namespace probe with PID-1 reaping. Historical probe results do not qualify the new build. Tickets01–07 have accepted fixed-binary evidence. Ticket08 integration remains outstanding.
