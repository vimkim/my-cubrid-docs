# Ticket07 review — acceptance pending

Main performs the Standards and Spec axes directly, as authorized by the handoff's one-worker-per-ticket topology. No extra review agents were used. Engine dispatch base: `41ac0c2ce39590349e8e5759dc376f88e1cb660b`; testcase dispatch base: `8c1a1bc791e5e29174fd5f6e78d98d6cec02f7bb`. Parent spec and ticket07 remain authoritative.

## Standards

Reviewed the broker/base changes against root/src/broker/base AGENTS and personal CUBRID policy. The user-approved enforced formatter supersedes the no-tabs guidance. New STL preparation is in broker_process.cpp, catches throwing allocation locally and translates to errno; fork children only use the existing async-safe spawn path. memory_wrapper.hpp is last with its required comment. CMake includes the helper in the affected UNIX targets. Shared-memory structure layouts are unchanged. Parent-owned per-invocation groups replace implicit inherited launch resources; no global group pointer or child environment mutation is added.

No outstanding documented-standard finding in the reviewed candidate. Final committed diff, normal-hook result and clean state must still be recorded after the rollback correction and native verification.

## Spec

Six creation boundaries are covered: admin broker/CAS/proxy and legacy non-CAS restart, plus internal broker CAS/proxy restart. The legacy non-CAS branch is unreachable through the current CAS/CAS_CGW configuration table. shard_admin_pub.c raw forks are wholly guarded by UNDEFINED (lines24–775). Synchronous proc_execute is unchanged. Explicit child environment and signal policy preserve SOURCE_ENV ordering/process-key override and each legacy SIGCHLD disposition. Required exec descriptors are0–2; real client SQL qualifies later SCM_RIGHTS communication.

Main review required outer readiness-wait ownership, explicit finish before shared-memory rollback, producer-exec versus helper-setup failure classification, and nonpositive PID retry handling. These findings have corresponding implementation and focused coverage. Worker self-review subsequently found the late-finish rollback index/detached-pointer bug; correction928e3e503 is committed but still requires the strengthened multi-broker regression and exact native qualification. This is an outstanding acceptance condition, not a passed check.

Focused prior-candidate evidence: green4 lifecycle281 checks, fail-green2 failures44, recover1 recovery57. Main inspected their matrices and independently confirmed positive-PID-set restart detection, internal-FD assertions, real CCI SQL, private IPC/syslog containment and actual missing-executable recovery. Existing proxy/CAS retry intervals yielded2/23 exec failures over~2.303s, then recovered after executable restoration. The expanded final failure matrix adds proxy log-open, missing relay, unsupported configuration, multi-broker rollback and fresh SQL checks; those results are pending.

Exact baseline41 failure contracts remain: missing broker1, ordinary missing CAS0, SHARD missing proxy0, SHARD missing CAS1 with original diagnostics. Ticket06's pending public0→1 decision does not authorize changing these07 results. Gateway targets/CAS_CGW receive compilation/source review only; no external ODBC backend functional verification. Windows is source-reviewed, not runtime/build qualified here. These limitations preclude an unqualified universal compatibility claim.

## Retained unsuccessful native attempt

`/home/vimkim/.cache/cbrd27443-07-00edb90.PvHSSd`: candidate00edb90df/test9a06fe217, intentionally canceled during master matrix after the rollback finding. Native artifacts record0pass/1fail/context-canceled even though runner returned0. It does not qualify the correction and is not attributed as a demonstrated engine failure.
