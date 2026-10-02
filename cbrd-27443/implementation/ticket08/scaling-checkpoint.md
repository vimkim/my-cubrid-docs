# Ticket08 checkpoint: confirmed ticket07 scaling regression; ownership released

Ticket08 is incomplete. Investigation of the first assigned review question confirmed a substantive broker startup regression. Per the orchestration contract, expansion and final native qualification stop here so main can route correction to the original ticket07 worker. No engine/test edits, commits, builds, installs, external actions or tracker/doc edits occurred in this assignment.

## Exact state and evidence

- Engine worktree `/home/vimkim/gh/cb/CBRD-27443-fd-clean`, branch `CBRD-27443-fd-clean`, clean at `b0f569011731d37516f2f62dad9d3d4c76312291`.
- Test worktree `/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean`, branch `tc/CBRD-27443-fd-clean`, clean at `26ab88a3545aaa08a2bb5ef461b03fb0192e8a6d`.
- Immutable pre07 install `/home/vimkim/.cache/cbrd27443-06-41ac0c2.FvYAKF/cubrid`, actual version `11.5.0.2653-41ac0c2`.
- Immutable current install `/home/vimkim/.cache/cbrd27443-06c-b0f5690.RGZgmT/cubrid`, actual version `11.5.0.2658-b0f5690`.
- Evidence root `/home/vimkim/.cache/cbrd27443-08-scaling` contains `identity.json`, `audit.json`, `pre07/s08.json`, `current/s08.json`, `pre07.log`, `current.log` and scratch fixture sources. `audit.json` freshly compares all 18 recorded/installed/actual runtime hashes per installation; all 36 triples match.
- Actual fixture roots: baseline `/home/vimkim/.cache/fd-s08.vA5Gn4/root`, current `/home/vimkim/.cache/fd-s08.zvmt4i/root`.

## Reproduction and result

Scratch driver: `/home/vimkim/.cache/cbrd27443-08-scaling/scaling.py`. It imports copies of the committed broker and CLI fixtures, changes ordinary broker MIN_NUM_APPL_SERVER and MAX_NUM_APPL_SERVER to32, and invokes actual `cubrid broker start` under soft limits128 and256. Each successful startup requires all32 actual CAS and CCI prepare/execute/fetch of27443. Both versions use identical fixture/configuration, private user/mount/net/PID/IPC namespaces, private real device mounts without host syslog, PID1 reaper and private DB. Baseline EOF is observational because its known leak must not prevent functional comparison.

Exact commands from the engine worktree:

```sh
bash /home/vimkim/.cache/cbrd27443-08-scaling/run-probe.sh /home/vimkim/.cache/cbrd27443-06-41ac0c2.FvYAKF/cubrid /home/vimkim/.cache/cbrd27443-08-scaling/pre07 s08 scaling > /home/vimkim/.cache/cbrd27443-08-scaling/pre07.log 2>&1
bash /home/vimkim/.cache/cbrd27443-08-scaling/run-probe.sh /home/vimkim/.cache/cbrd27443-06c-b0f5690.RGZgmT/cubrid /home/vimkim/.cache/cbrd27443-08-scaling/current s08 scaling > /home/vimkim/.cache/cbrd27443-08-scaling/current.log 2>&1
```

| Build | Soft limit | Startup code | CAS after startup | Actual CCI SQL | EOF/lock before stop |
|---|---:|---:|---:|---|---|
| pre07 41ac |128|0|32|27443|Neither EOF; lock held (known baseline defect)|
| pre07 41ac |256|0|32|27443|Neither EOF; lock held (known baseline defect)|
| current b0 |128|1|0 after rollback|Unavailable; not called|Both EOF at~2.472s; lock free|
| current b0 |256|0|32|27443|Both EOF at~0.935s; lock free|

Current128 stderr contains nine `cub_cas: Too many open files` lines. The resource limit change alone restores successful current startup, with the same32-CAS configuration. Both executions return0 as observational probes, with50 and44 fixture checks respectively; these collector codes are not a product pass for current128. Both explicitly verify no remaining namespace service/relay processes and no private SysV shared memory. No failed attempts were deleted. No native testcase verdict was produced by ticket08 yet.

## Finding and proposed correction

High-priority regression: a formerly functional ordinary32-CAS startup fails solely due to new cumulative launcher FD consumption. Source evidence: `broker_process_group::start` retains each `background_process` entry until group finish (`src/broker/broker_process.cpp:141–159`); the state holds output[2], control and acknowledgement (`src/base/background_process.hpp:32–42`). Ordinary CAS readiness returns at `src/broker/broker_admin_pub.c:3513`, while the loop starts subsequent children at3275–3277; entries remain until outer finish. Draining output does not release these four per-child channels.

Correction must bound admin FD usage independently of initial child count while retaining complete current-attempt diagnostic capture until the original outer readiness/result boundary. A shared invocation-owned relay/transport or other bounded descriptor aggregation is a candidate; ticket07 should choose the concrete design. Simply finishing each child early, dropping diagnostic channels, raising the caller limit, reducing configured CAS, or changing readiness would not satisfy the contract. Add a persistent32-CAS/128 CLI regression and verify verbose/late diagnostics and rollback in the affected ordinary/SHARD paths. Preserve the observed legacy public failure codes.

## Nine ticket08 checkbox results at handoff

1. Partial: existing exact b0/test26 installation identified; no final post-correction integrated state yet.
2. Pending: final A01–A16 evidence map must be completed on the final state.
3. Pending: inherited earlier matrices have not been rerun by ticket08.
4. Pending: real startup/restart/HA/broker rotation and runtime logging fault interactions remain to implement/qualify.
5. Partial: ordinary broker CCI communication observed at32CAS; remaining final direct/synchronous/FD contracts await qualification.
6. Pending: no new build/native final qualification; no Windows build/runtime claim.
7. Finding open: confirmed scaling regression is routed to original07. Main owns Standards+Spec review.
8. Partial: baseline/current difference and retained observations documented here; full final report remains pending.
9. Partial: both worktrees clean, no meaningful repository changes made; scratch diagnostic artifacts retained for main archival.

A01–A15 remain prior-ticket evidence only at this checkpoint, not new final integrated qualification. A16 has a confirmed current defect at32CAS/128; current32CAS/256 runtime communication succeeds. Windows/non-Linux build/runtime and external ODBC gateway backend remain unverified. Earlier exact native b0/test26 1/0/0 evidence is historical and cannot qualify the upcoming correction or missing interaction combinations. No whole-spec/whole-QA completion claim.

## Release

Exclusive engine/test/build ownership is released cleanly to main for original07 correction. Ticket08 will resume after main returns the corrected clean source/test/install state. No unfinished changes exist in either assigned worktree; no process from these completed namespaces remains. No merge, rebase, push, PR, JIRA write, external CI, shared-service operation or nested agent was performed.
