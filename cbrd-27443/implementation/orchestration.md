# Implementation continuation

Work-tracker item: 261. Handoff contract: `/tmp/handoff-cbrd-27443-orchestrated-Sb9MbYnm.md`. Read the whole parent spec and all tickets from this worktree's `.scratch/cbrd-27443/` when resuming. Parent spec is unchanged.

## Ownership and bases

- Engine: `/home/vimkim/gh/cb/CBRD-27443-fd-clean`, branch `CBRD-27443-fd-clean`.
- User-confirmed implementation base: `15e7dc8b5b56fd8751d56ccae1fdf87d315bd35d`. User confirmed this new base and exclusive worktree availability after an external fast-forward. Never include the earlier upstream advance as our implementation diff.
- Shell tests: `/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean`, branch `tc/CBRD-27443-fd-clean`, original base `dfb7da195`.
- Documentation: `/home/vimkim/gh/my-cubrid-docs-cbrd-27443-implementation`, branch `docs/cbrd-27443-implementation`, original base `ece982c`.
- Main alone edits ticket status, map and docs. One fresh implementation worker per ticket, numeric order, no nested workers. Tickets01–02 accepted. Latest engine `11ad631c56b35675a96c7c9c15fc66025fb0aab0`, shell `7df0ede4bb5e76f59f644a1d6c7df03cfcd2e93c`. See per-ticket report/review files. Current worker: `/root/ticket03`, dispatch engine base `11ad631c56b35675a96c7c9c15fc66025fb0aab0`, shell base `7df0ede4bb5e76f59f644a1d6c7df03cfcd2e93c`.

## Preparation evidence

`baseline-15e7dc8b5/` contains exact-base reproduction, binary hashes and native preflight. Full debug_gcc build/install passed. Source/install commit match and native containment passed. Earlier `baseline/` retains the c63a3b9 reproduction and transient shared-tooling preparation failure.

Runtime initialized using supported `cub-workenv init --no-db`. Shared personal tooling changed during preparation; inspect live recipes. `CUBRID_TESTCASES_PRIVATE_EX_DIR` was not exported; use the assigned exact shell root above when invoking test tools. CTP assets resolve to `/home/vimkim/gh/ctp/run-sql/CTP`. Native runner is installed; do not install/update it. Preserve containment and PID-1 reaping.

## Ticket 01 design checkpoint

Main accepted the worker's proposed explicit background spawn plus separately executed console relay. It separates startup diagnostics by attempt using anonymous spools, preserves original streams, appends continued output, and drops launcher-facing resources after a finite drain barrier. Subsequent log rotation belongs to ticket 04. This is a design checkpoint, not an implementation or acceptance claim.

Review constraints: no unbounded drain under continuous writers; preserve existing registration timing and SIGCHLD/termination semantics; helper exec/log-open failures must reach launcher; relay keeps no caller stdio/lock; parent loss closes attempt spool/control descriptors; safely encode DB log names; document relay lifecycle and prepare for coordinated rotation among multiple relays sharing a log.

## Completion workflow

For each ticket, capture immutable dispatch base, require narrowly committed source/tests and native verdict-bearing evidence, review actual diff against both Standards and Spec, and resolve checkboxes only when evidence supports them. Return corrections to the same worker. Main performs the two review axes itself in place of stock code-review's extra reviewer agents.

Current reports should be returned under `/home/vimkim/.cache/cbrd27443-ticketNN-report.md`; main copies meaningful results into this documentation worktree. No develop merge, push, PR, external CI or JIRA mutation is authorized. At completion, request one concrete local rebase/fast-forward approval covering relevant repositories, then clean only merged task worktrees/branches.

## Formatting decision

The user explicitly approved following the enforced repository formatter on 2026-10-02. The supplied AGENTS.md line133 says no tabs, but codestyle.sh line28 uses AStyle `-xT8`, which forces mixed tab/space indentation. Use the live formatter and normal commit hooks; no hook changes or bypass are authorized. This task-specific user decision resolves the conflict for subsequent workers.

## Ticket 02 checkpoint

Service and direct daemon master use the explicit background helper. Preserve the existing PID1/NO_DAEMON foreground exceptions. Linux re-exec uses `/proc/self/exe` and carries actual PR_GET_NAME through a private last argument; original argv interpretation is preserved. The relay is included in Application installs. Final native `ticket02-final-11ad631c5.8gBHRC` passed 1 case, 216 master checks and 121 original checks. Earlier d031 native failure exposed comm restoration and a strict post-stop observation race; both were corrected and prior evidence retained. Source/test worktrees are clean and released. Ticket03 owns server/PL restart and internal FD cleanup; the basic present probe still visibly shows PL inheriting parent error-log/volume targets before that work.

## Ticket 03 design checkpoint

Main accepted the proposed explicit exec-boundary mapping: PL keeps valid existing stdout/stderr, takes null stdin, and drops unrelated parent descriptors. This preserves direct/SA output. Ordinary server restart uses the background relay and finishes its startup channel immediately; the existing monitor remains responsible for later registration confirmation. Legacy create_child_process remains unchanged to avoid assigning policies implicitly to other consumers. This is a proposed direction, not verified completion.

Review constraints: map sources above every destination or validate the supported mapping count; do not rely solely on a parent-side open-FD snapshot in a multithreaded parent; failed exec children must report and exit rather than return to parent control flow. Closed-stdio cases must inspect actual targets because error-manager initialization before spawn can reuse closed standard numbers. Preserve direct/foreground output semantics when choosing the reservation boundary.

PL reaping decision: preserve the legacy POSIX SIGCHLD=SIG_IGN policy explicitly at the PL launch callsite, with checked failure. The generic helper leaves parent signal disposition unchanged. A new waitpid in the monitor loop alone would be incomplete after the monitor ends, especially in a long-lived SA library caller; this ticket does not redesign PL destruction. Caller-owned reaping includes explicit auto-reaping. Verify restart/error cleanup under this preserved policy.

The PL child also keeps the legacy inherited SIGCHLD disposition. The private low-level spawn has an explicit reset choice: existing relay/background paths reset, stdio-only PL spawn preserves it.

Main review found that synchronous exec/log failure feeds the monitor's immediate failed-spawn requeue. Retained restart2/restart3 probes recorded 872/740 attempts during one-second missing-executable windows. Worker03 is authorized to reuse the monitor's existing one-second interval for failed-spawn pacing and verify bounded attempts plus later recovery. This is a retry delay, not a new deadline or readiness condition. The first native attempt at source336ef2da5 remains historical evidence and cannot qualify the later corrected source.

Further A13 review reproduced a closed-stdout hole in direct SA at source29e730288: csql.err reused parent FD1 and PL inherited that target. Red evidence is `ticket03-iteration/sa-closed-red2.json` with the immediate parent/child snapshot. Worker03 is adding absent-stdio reservation at csql launcher and direct cub_server entry, preserving every valid existing target, plus focused SA/direct verification. Source29e's pacing check recorded 3 attempts over 2.244 seconds. Final acceptance still requires the later committed exact native run.

Source74ee includes all current fixes. Its first native run exposed fixture readiness ordering; the next reaped attempt exposed an existing registration limit: CSS_SERVER_PROC_REGISTER::exec_path has 128 bytes and connection_sr.c truncates the 132-byte native runtime path to127, ending `/bin/cub_s`. Main authorized shorter physical fixture basenames, an explicit registered-path byte-length precondition and a shorter native attempt label. Do not widen that existing protocol as part of this FD task. Keep the NOK evidence and exclude pre-existing overlong installation paths from the claimed runtime coverage. Final native acceptance is still pending.

Ticket03 accepted: final native `cbrd27443-03-final.CNCI1F` passed 767 assertions and one native case with no failures/skips on engine74ee7520a/test8b00d634c. Main checked all matrices, native verdict, clean worktrees and nine installed/copied executable/library identities. Retry pacing was 3 attempts/2.244s; registered path102 bytes. Worker03 released ownership. Retained failures and platform limits are documented in ticket03/report.md.

Ticket04 dispatched from engine `74ee7520a76dd5c1635bed9e75a06c233026115a`, shell `8b00d634cfb36d654c88d747114aa126efa866c6`. Fresh worker04 exclusively owns source/tests/build; main owns docs/tracker. Scope is bounded append console logging, coordinated rotation and observable failure handling, preserving per-attempt diagnostics and existing readiness/output contracts.

## Ticket 04 design checkpoint

Proposed permanent retention: 1 MiB active console file plus three archives, owner-only permissions, stable sibling lock coordinating marker/output writes and rotation. Each writer reopens the active file under that lock so rotations do not strand active writers on old inodes. Runtime failure should leave bounded visible status and a rate-limited syslog event while continuing to drain producers. These are design decisions to verify, not completed behavior.

Replace anonymous unbounded startup spools with bounded pipes, pumped fairly during existing readiness waits without changing registration criteria or deadlines. Finish must drain both streams while waiting for acknowledgement; ack-before-drain would deadlock. Per-pump work must be finite under continuous output. Current-attempt diagnostics must remain complete even if permanent archives rotate. Verify all master/server/automatic-restart callsites, caller loss, runtime fault status, regular/nofollow log and lock handling, concurrent writers and original stdout/stderr destinations.

Ticket04 accepted: source731b39e0f/test28d75755d, exact native S8CNvN1/0/0 with889 checks and9 binary identities. Console policy and limits are in ticket04/report.md; startup pipes require pumping during original waits. Worker04 released clean source/tests. Main findings on locking, oversized migration, SIGXFSZ and private fault logger are resolved.

Ticket05 dispatch: engine731b39e0f976a97f0dac62374aba976b9dca37f9, shell28d75755d9dd69ef61a1d80a80a37aabade3a7ab. Fresh worker05 owns source/tests/build exclusively for single-node HA; main owns docs/tracker. Inspect HA startup, automatic restart and management utility boundaries independently of ordinary monitor. Reuse bounded console/helper contracts where applicable.

## Ticket 05 design checkpoint

Initial heartbeat server start already traverses the explicit utility/server launcher. The separate HA restart job and master-mediated utility start are raw fork/exec boundaries requiring parent-only argument preparation and explicit cleanup. Proposed HA producer output uses the existing bounded server-console.log family; master diagnostics keep their current destination. Immediate startup-channel completion is appropriate where the commdb IPC carries status rather than producer stdout, with existing registration confirmation jobs/timers preserved. Verify the managed utility boundary via real commdb IPC in the single-node fixture even though ordinary single-node startup skips copy/apply. Two-node replication and direct local copy/apply launches remain ticket06 work.
