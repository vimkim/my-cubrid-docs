# CBRD-27443 combined review

Source review is complete; final native runtime acceptance is pending. The review compares engine `0809a480df55ac6767a905d03fa3d31edd40a93c` with the user-approved implementation base `15e7dc8b5b56fd8751d56ccae1fdf87d315bd35d`. Final tests are committed at `6bdbb89738088948c479a6d85662276126a31bb5`, based on `dfb7da1955173d6858703b15818fe030ff178d1e`.

The main orchestrator performs the code-review skill's Standards and Spec axes directly, as required by the approved one-worker-per-ticket workflow. No additional review agents were used. The [orchestration record](orchestration.md) preserves intermediate findings, corrections, ownership and unsuccessful test attempts.

## Standards

No outstanding source finding. The combined review covers all 22 changed engine files: process helper and console relay, build integration, ordinary/HA utility launchers, master recovery, PL, and broker administration/internal recovery.

- Personal CUBRID policy and the user's explicit enforced-formatter choice govern. New throwing STL preparation lives in `.cpp`, with local exception translation to errno. C++ additions in legacy formatted sources use INDENT guards.
- Preparation and allocation occur in the parent. The child performs descriptor remapping/cleanup, signal disposition, prepared exec and bounded error notification, then `_exit` on failure. It cannot return into parent control flow.
- Descriptor sources are moved above reserved mappings; early executable entry reserves absent standard descriptors. Linux close-range and raw directory fallback cover inherited high descriptors independently of a lowered limit.
- Callers retain explicit signal and reaping ownership. Existing synchronous `proc_execute` behavior is unchanged. PL, direct server and SA preserve intentional output destinations.
- Build/source guards preserve Windows-specific launch branches. This source inspection is not a Windows or non-Linux build result.

New interfaces serve actual creation boundaries. The review found no unrelated refactoring required by the skill's code-smell heuristics. Normal commit hooks and diff checks were used.

## Spec

No outstanding source finding. Runtime acceptance still requires the final four-case native result at the exact commits above; earlier passing runs do not substitute for it.

The implementation separates caller startup capture from long-lived output while retaining existing readiness checks and public result contracts. Each service console has an active file and three archives, each bounded to 1 MiB. Stable locking, reopening for each append and private file modes support multiple writers and restart rotation. Runtime logging failure records bounded diagnostics, continues draining, and retries later. This deliberately does not promise lossless output when storage is unavailable.

Corrections reviewed and verified during integration:

- **HA failure compatibility:** local missing-producer exec preserves the observed legacy public zero result and meaningful diagnostic/result inventory; heartbeat-start and checked remote paths retain their failure behavior. New relay/log/descriptor setup failures take precedence. The failed child exits safely, rather than recreating duplicated legacy child-side shutdown effects. See [ticket 06 correction](ticket06/compatibility-report.md).
- **Broker rollback:** finish errors are handled before rollback, with valid shared-memory pointer/index bookkeeping. Missing CAS/proxy recovery uses explicit active/nonpositive PID states and the existing retry intervals. See [ticket 07 report](ticket07/report.md).
- **Broker descriptor scaling:** the initial per-producer channel design failed a valid 32-CAS configuration at soft limit 128. One invocation-owned channel per service destination now bounds persistent launcher descriptors independently of CAS count, retaining all original readiness waits and diagnostics. The correction also resets `exec_failed` before potentially throwing parent preparation. Real 32-CAS and 64-CAS starts at hard/soft 128, valid SHARD configuration, full current/late output, rollback and CCI SQL pass. See [scaling report](ticket07/scaling-report.md) and its retained baseline/candidate evidence.

The final test diff retains every prior matrix and adds ordinary/PL, single-node HA, replication and ordinary/SHARD broker rotation interactions. Functionality is checked while logging is actively failing, before restoration. Fresh failure-record timestamps prevent stale diagnostics from passing. Per-PID volume evidence handles concurrent CAS; replication wrappers preserve the original argument identity. Early failed SHARD startup is checked for its actual diagnostic/code/EOF and current-attempt rotation without requiring future output from canceled producers.

## Final qualification

Pending: native attempt `/home/vimkim/.cache/cbrd27443-08.QVVajj`, four exact cases, one slot, unchanged 1,200-second per-case timeout, no retry/update/continuation. Preflight source/install identities and effective configuration were independently inspected. Main's final audit will check the native artifacts, every matrix, actual fixture hashes and the A01–A16 evidence mapping.

## Limits

- Linux focused runtime only; Windows and other Unix builds/runtime are unverified.
- External ODBC gateway backend operation is unverified. Shared gateway targets compile, but supported ordinary CUBRID and SHARD client execution does not qualify every gateway configuration.
- Disabled `UNDEFINED` code and configuration-unreachable legacy non-CAS administration receive source review, not invented runtime coverage.
- Configured build has `UNIT_TESTS=OFF`; no ctest pass is claimed. Focused tests do not establish whole-corpus QA or external CI completion.
- No local integration, push, PR, external CI trigger or JIRA mutation follows from this review. Unrelated changes in the engine `develop` worktree remain preserved.
