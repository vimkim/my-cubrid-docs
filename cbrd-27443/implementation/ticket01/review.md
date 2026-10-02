# Ticket 01 main review

Fixed point: `15e7dc8b5b56fd8751d56ccae1fdf87d315bd35d`; reviewed engine tip `c4e2bd9106e94e08c3fd81d31e501c28bfc6429e` and shell tip `6c189443112f2931c8f49167ff5e982eadab44af` against `dfb7da195`. Main performed both code-review axes directly under the user's one-worker-per-ticket topology; no parallel reviewer agents were used.

Standards: accepted. Required hooks and diff whitespace checks passed. New C++ code uses explicit FD ownership, parent-side preparation, limited post-fork operations and last memory-wrapper includes. The user approved the live enforced formatter over conflicting no-tabs prose. Windows callsite remains on the original branch; no Windows build claim.

Spec: accepted for ticket01. Independently inspected final native preflight (source clean, installed c4e2bd9 matches), verifier (1 successful selected case, zero failures/skips), and retained matrix (121 checks, no failures). Capture modes, command/EOF distinction, SQL/PL after EOF, general FD/lock release, exact missing-DB diagnostic, exec/log failures, current-attempt isolation including another writer, append behavior, and direct/synchronous compatibility are covered. Both worktrees were clean at acceptance.

Review corrections resolved by this worker: nonregular/FIFO log paths cannot hang startup; spool seek/read/write failures propagate; utility SIGCHLD policy stays at the callsite; marker length cannot alter argv semantics; test master setup uses regular output and short isolated Unix socket paths; renamed executable fixture is identified by its actual role.

Rotation, runtime log failure policy, master boundaries, restart/PL internal descriptors, difficult FD limits/platform fallbacks and HA/broker coverage are explicitly assigned to later tickets. No whole-spec or whole-QA pass is claimed.
