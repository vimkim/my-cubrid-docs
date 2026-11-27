# Code review — CUBRID/cubrid#8792 (CBRD-28140)

**PR:** [CUBRID/cubrid#8792](https://github.com/CUBRID/cubrid/pull/8792) — "[CBRD-28140] Fail the server start when it cannot register to master, and stop leaking sockets and retrying without delay" (author InChiJun)
**Snapshot:** base `446437aa63bc08d77bda18547eaa689c1d9e150a` (develop) · head `cc845fa345a8cdb0078881482f6d3c14706715dd` · merge base `a921084ab7df75af0d2f2fb762dd30c61ccc6495` · reviewed 2026-11-27 (KST). Head and base rechecked unchanged before finalizing.
**Comparison:** `git diff a921084ab7df75af0d2f2fb762dd30c61ccc6495 cc845fa345a8cdb0078881482f6d3c14706715dd` — 8 files, +379/−36, patch sha256 `78c38ee11143326dde4c52d50015efbcf18b938bf40d6077212bda658608a74b`. `git merge-tree` against current develop: clean.

## Verdict

- **Verdict:** `no-confirmed-findings` — the review found no defect introduced or exposed by this PR.
- **Follow-up review required:** **no.** The remaining gaps are optional evidence and need not precede merge: HA mode and the 30 s and 60 s timeout paths were checked only in source. Each was traced to evidence level 3, independently by two reviewers where it was a shared question, and the author reports fake-master tests that cover these paths.
- **Recommendation:** **APPROVE.** Comments to consider are listed below; none of them blocks.

The PR's headline claims reproduced on a debug build of the head:
- With no master, `cub_server` exits with code 2 in about 1.4–4.7 s and leaves no socket.
- After master is killed, the server retries every 5.00 s without fd growth and re-registers in about 1 s once master returns.
- A bind failure ends the start immediately without a leak.
- Auto-revive stops after exactly 3 quick revives and logs `ERROR -989`.

## Confirmed findings

None attributable to this PR.

## Pre-existing defects observed (not introduced by this PR)

| ID | Priority | Location (head) | Defect | Evidence | Suggested action |
|---|---|---|---|---|---|
| PE-1 | P3 | `src/connection/master_connector.cpp:580`, `:843` | `er_set_with_oserror (..., ERR_CSS_ERROR_DURING_SERVER_CONNECT, 1)` passes no argument for its `%s`. Undefined behaviour; the message comes out garbled. The same two calls exist at the merge base (`:459`, `:714`). | Runtime P5 (CUBRID_TMP of 88 chars): `Communication error during connect for .... Invalid argument`, no crash in this run. | The PR defers this to CBRD-28313, which should cover **both** lines (`:843`, accept failure, as well as `:580`). Without HA, after registration this path can repeat every 5 s while the cause persists, not only once at startup. |
| PE-2 | P3 | `src/executables/master_server_monitor.cpp:301-309` | If `execv` fails in the forked child, the child returns into the cub_master monitor code (`return execv (...)`) and keeps running as a second monitor, which can fork again. | R3 harness on the production file at base and head. The pattern is the same at the merge base (`:273`). | `_exit (127)` after `execv`, as heartbeat does. A follow-up issue is suggested. |
| PE-3 | P3 | `master_server_monitor.cpp:202-208` | When `fork()` fails, the same REVIVE is requeued immediately with no delay or cap. A persistent `fork` failure spins the monitor thread. | Source (R2). Unchanged by the PR, which only makes the uncounted retry explicit in a comment. | Back off on fork failure (optional). |
| PE-4 | info | `master_connector.cpp:928` | Duplicate-name rejection logs the literal `"server name"`: `Server server name already exists.` | Runtime P3b | Pass the actual name (optional). |

PE-4 sits next to the PR's improvement 5 (the rejection reason is now visible), but the PR did not create it.

## Comments to consider (non-blocking, design or wording)

- **C1 — revive bound covers only fast failures** (R2-C1). The count resets when a revived server lives longer than 120 s, counted from the later of fork or registration. A server that, for example, runs a long recovery and then fails before registering is still revived without limit at that cadence. This matches the base behaviour and the code comment (`master_server_monitor.cpp:193-195`), but the PR's "Remarks" do not state it.
- **C2 — no backoff between quick revives** (R3-2, stated in the PR). The 3 attempts can finish within seconds, so a transient cause that lasts longer ends auto-revive permanently until a manual start. Once auto-revive gives up, the entry is erased, so a later manual start begins with a fresh count.
- **C3 — exit code and message after a post-registration loop failure** (R1-C2). A failure inside the event loop after registration is practically unreachable. If it happens, it now exits with code 2 and the fallback `ER_NET_NO_MASTER` text, which reads as "could not contact master".
- **C4 — complexity.** `connector::execute` grew from CCN 17 to 29 (lizard). Splitting out the per-state deadline and reestablish handling would help later maintenance.
- **C5 — cosmetic** (R1-C4). The log line after the unix-socket wait times out can print a stale errno.

## Safety facts and effects outside the diff

| Effect | Safety fact | Owner / evidence |
|---|---|---|
| `css_init` now returns failure after boot. | `net_server_start` runs `xboot_shutdown_server ()` and `css_final_conn_list ()` on both paths, as the pre-PR no-master path did, so the volume lock is released and no half-booted server remains. | R1 L3 · runtime P1a + coordinator replay (exit 2, no leftovers) |
| `css_tcp_setup_server_datagram` now closes the socket on failure. | No caller (connector, `connection_sr.c`, `connection_cl.cpp`) closes it again. | R1 L3 · P5 no fd growth |
| `css_make_conn` leaves the fd to its caller on NULL. | All server-side callers close or hand off the fd. In `master.c:1019` the only newly unclosed case is a failed mutex lock inside `css_get_next_client_id`, which is practically unreachable. | R1/R2 L3 |
| New connector fields and deadlines. | The connector is a stack local of `css_init`; `run`, `disconnect`, reestablish and `stop` all run on one thread. | R2 L3 · P4 |
| Exit code 0 → 2 when master is absent. | Nothing in the tree reads `cub_server`'s exit code. `cubrid server start` reports fail because the process ends. Heartbeat and the monitor detect death by socket close or signal. | R3 L3 |
| HA registration semantics. | `m_registered_once` becomes true only after the heartbeat registration is fully sent; post-registration HA behaviour, including exit 0 on rejection, is unchanged. The monitor never revives HA (`#`-prefixed) servers, and HA forces `auto_restart_server` off. | R3 L3 (HA not run) |
| Revive dedupe and bound. | Pid-tagged REVIVE/CONFIRM jobs drop a duplicate report of one exit. A manual start that races a revive ends up monitored without an extra fork. Pid reuse would need a full pid wrap within about 1 s and at worst causes one extra failed fork. | R3 L4 harness, R2 L3, P6 |
| `cuberr::context` on the monitor thread. | The context is `thread_local` on a new thread, which is joined before `er_final`. | R2/R3 L3 · P6 (ERROR logged, master alive) |

## Coverage and verification

Per-path coverage is in the appendix below. Reviewers: R1 Systems (opus), R2 Concurrency/lifecycle (sonnet), R3 HA/master monitor (opus). The Recovery and Storage roles were not applicable: the PR has no WAL, page or on-disk changes. Shared challenge Q1 (connector failure paths) went to R1 and R2; Q2 (revive policy) to R2 and R3. Each pair answered independently and reached the same conclusion.

Checks run:

| Check | Revision / config | Result |
|---|---|---|
| `just configure-build` (debug_gcc) | head | pass (BUILD_RC=0) |
| `cubrid-static-check a921084ab7 cc845fa345` | MB..head | 0 new cppcheck / clang-tidy / CPD; 1 complexity flag |
| R1 syscall probe (bind on a long path, listen readability, POLLRDHUP) | host kernel | pass |
| R2 kernel/timer probes (60k poll iterations, read after hangup, accept after peer close, `-ftrapv` timers) | host kernel | pass |
| R3 monitor harness: production `master_server_monitor.cpp` with stubs | base and head | head bounded to 3, no double fork; base unbounded / double fork |
| Runtime P1–P6 (no master, normal start, duplicate DB/name, master `kill -9`, bind failure, auto-revive give-up) | head debug install, dedicated master port | all pass; PE-1 and PE-4 messages observed |
| Coordinator replay of P1a | head | rc=2, 1.35 s, no leftovers |

Not run: the release (`-Werror`) build (the author reports it passes); HA cluster runtime; the 30 s unix-socket accept timeout and the 60 s silent-master handshake deadline at runtime; the stale-request drop path at runtime.

## Unverified risks and dropped candidates

- No material unverified risk remains.
- **R2-C4** (pre-existing, source-only): a possible deadlock or null-pointer dereference during cub_master shutdown around `master_Server_monitor.reset ()`. It is outside the PR's hunks and has not been replayed. Owner: an optional follow-up issue.
- **Dropped:**
  - R1: C3 (error replaced during shutdown). Disproven by P1a, where stderr shows the real cause.
  - R2: C5 (same question as R1-C3, disproven the same way); C6 and C7 merged into PE-1 and the `css_make_conn` safety fact.
  - R2-C2 (a manual start inherits the count): reduced to design note C2. Give-up erases the entry, and the PR text states the count survives registration by design.
- **Count by reviewer:**

| Reviewer | Candidates | Pre-existing | Comments | Dropped or merged |
|---|---|---|---|---|
| R1 | 4 | 1 | 2 | 1 |
| R2 | 7 | 2 | 1 | 4 |
| R3 | 2 | 1 | 1 | 0 |

## Linked testcase PRs (cubrid-xref)

- Private testcase repository, `tc/pr-8792`: draft, 0 changed files.
- CUBRID/cubrid-testcases#4515 `tc/pr-8792`: draft, 0 changed files.

R3 found no testcase that depends on the old `cub_server` message. No TC change is required.

## Budget accounting

- **Mode:** bounded by default; no user-supplied limit, and no hard cap was enforced.
- **Agents:** 4 — 3 reviewers plus 1 runtime-verification agent drawn from the coordinator's reservation. No retries.
- **Subagent tokens reported by the harness:**
  - R1 ≈ 162k
  - R2 ≈ 287k
  - R3 ≈ 211k
  - runtime ≈ 159k
- **Coordinator usage:** unknown. Per-agent account attribution is unavailable, and the optional allowance targets cannot be verified.

## Appendix — coverage

| Path / invariant | Primary | Also | Evidence | Result | Remaining |
|---|---|---|---|---|---|
| `src/connection/tcp.c` — datagram socket closed on bind/listen failure; no caller double-closes | R1 (opus) | R2 | L3 source (all callers incl. `connection_cl.cpp`), L4 syscall probe, L5 runtime P5 (no fd growth) | clear | — |
| `src/connection/connection_sr.c` — `css_make_conn` fd ownership moved to caller; `css_connect_to_master_server` closes on NULL | R1 | R2 | L3 (5 server-side callers); master.c:1019 leaks only if `css_get_next_client_id` mutex lock fails | clear (info R2-C7) | — |
| `src/connection/server_support.c` — `css_init` fails when `run()` fails; ER_NET_NO_MASTER fallback; shutdown sequence | R1 | R2 | L3 (`net_server_start` → `xboot_shutdown_server`, same as pre-PR no-master path); L5 P1a + coordinator replay (exit 2, no leftovers) | clear | — |
| `master_connector.cpp/.hpp` — every pre-registration failure ends `run()` false exactly once, releases fds/socket file (Q1) | R1 | R2 (shared Q1) | Both L3 independently; R2 L4 kernel probes (poll/POLLRDHUP, read-after-hangup, accept after peer close, timer arithmetic -ftrapv); L5 P1a/P3b/P5 | clear | 30 s accept and 60 s handshake deadlines not runtime-tested (author reports fake-master tests) |
| connector event loop threading, reconnect 5 s delay, deadlines | R2 (sonnet) | — | L3 single-threaded (connector is a stack local of css_init); L5 P4 (5.00 s period, stable fds, low CPU) | clear | — |
| `close_unixsocket()` cannot unlink another server's socket | R1 | — | L3 (path contains pid; empty after duplicate rejection) | clear | — |
| er_set argument counts for new ER_HB_PROCESS_EVENT / ER_NET_NO_MASTER sites | R1 | — | L2–3 against `msg/en_US.utf8/cubrid.msg` | clear | pre-existing missing args at :580/:843 (PE-1) |
| HA registration path (`m_registered_once` after hb register sent), post-registration behavior unchanged, exit-code consumers | R3 (opus) | — | L3; no in-tree consumer of cub_server exit code; HA forces `auto_restart_server` off (`system_parameter.c:10599`), `#`-prefixed HA names skipped (`master.c:554`, `:1265`) | clear | HA not runtime-tested |
| `master_server_monitor.cpp/.hpp`, `master.c` — revive bound, pid-tagged dedupe, no lost revive (Q2) | R3 | R2 (shared Q2) | R3 L4: production `master_server_monitor.cpp` compiled at base and head with logging stubs and driven by cub_master job sequences; R2 L3 schedules; L5 P6 (exactly 3 revives + ERROR -989 logged, master survives) | clear | stale-request drop path not exercised at runtime (P6b) |
| monitor thread `cuberr::context` | R3 | R2 | L3 (thread_local, new thread; joined before er_final); L5 P6 (ERROR logged, cub_master alive) | clear | — |
| Static analysis (cppcheck, clang-tidy bugprone, CPD, lizard) | coordinator | — | 0 new defects; `connector::execute` CCN 17→29 | nit | — |
| Build | coordinator | — | `just configure-build` debug_gcc at head: BUILD_RC=0  | pass | release (-Werror) not built locally; author reports pass |

Not applicable: Recovery and Storage/performance roles — no WAL, page, slotted-page, heap or on-disk change; server-start failure path verified to run the existing `xboot_shutdown_server` (volume lock released).

Shared challenges:
- Q1 — R1 (opus) yes, L3; R2 (sonnet) yes, L3 + L4 kernel probes. Independent agreement; runtime P1a/P3b/P5 consistent.
- Q2 — R2 (sonnet) no race/lost revive, gaps are design-level P3; R3 (opus) no race/lost revive, L4 production-code harness. Runtime P6 consistent.
