# Ticket 03 main review

Dispatch fixed points: engine `11ad631c56b35675a96c7c9c15fc66025fb0aab0`, shell `7df0ede4bb5e76f59f644a1d6c7df03cfcd2e93c`. Main performed Standards and Spec review directly under the approved one-worker-per-ticket topology; no extra review agents.

Status: source review complete through `74ee7520a`; final native evidence pending at `ticket03-final-74ee7520a-reaped.T3f60D`. Do not interpret the superseded source336ef2da5 native pass as acceptance of this later source.

Standards review: explicit stdio-only spawn keeps general descriptors private, while the relay retains its bounded internal FD mapping. Paths, source copies, memory preparation and signal action setup stay in the parent. Linux fallback uses raw getdents64 and stack storage in the child, avoiding libc directory locks and stale parent snapshots. Legacy create_child_process and Windows branches remain unchanged. New POSIX consumers have deliberate CMake linkage; csql launcher loads config before the platform-guarded helper declaration. Normal formatting hooks passed. Final clean status is still to be confirmed with evidence.

Spec review: ordinary restart retains registration confirmation and uses the server console relay. PL keeps existing valid stdout/stderr and drops internal files/sockets, with explicit legacy SIGCHLD auto-reaping in both parent and child. Runtime socket registration is distinguished from exec inheritance. Missing standard descriptors are reserved at utility, master, csql launcher and direct server entry before logging can reuse them; valid output destinations remain intact.

Findings resolved by the same worker:

- Partial waitpid reaping in the PL monitor would miss exits after monitor destruction in a long-lived SA caller. Preserve the existing caller auto-reaping policy and child inheritance explicitly.
- Fixed-duration missing-executable tests did not prove an exec attempt. Require a new failure diagnostic while the executable is still absent, then restore and verify recovery.
- Synchronous launch failure immediately requeued restart and produced 740–872 failed attempts per second in retained probes. Reuse the existing one-second monitor interval for pacing, without a deadline or changed readiness condition. A persistent-fault assertion rejects the previous retry rate.
- SA closed stdout was reused by csql.err and inherited by PL. Extend early absent-stdio reservation to csql/direct-server entries and require target/output checks.
- A comm-only process whitelist could hide failed unnamed children. The fixture records all relevant namespace processes, distinguishes confirmed zombies from unreadable live processes, and requires eventual empty cleanup.

The first source74ee native attempt exposed fixture-only direct-start ordering: a PL snapshot preceded registration, and the observer had to reap its own direct child while server stop waited for PID disappearance. Tests now gate SQL on existing server status and reap only the owned Popen concurrently. Focused restart/SA/direct verification passed 73 assertions before the final native rerun; earlier failed attempts remain retained.

Limits: Linux close_range and forced raw-getdents fallback are exercised; the portable hard-limit loop is source-reviewed only and assumes descriptors were not retained above a subsequently lowered hard limit. Large limits and lowered soft limits are tested. No non-Linux/Windows build/runtime or CTest pass is claimed. Rotation, runtime logging errors, HA/broker lifecycle qualification and final integrated acceptance remain assigned to later tickets.
