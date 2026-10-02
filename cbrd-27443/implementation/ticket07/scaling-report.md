# Ticket07 scaling correction

Status: correction and focused qualification complete; clean source/test/build ownership released to main for ticket08 resume. Main retains review and acceptance authority.

## Exact state

- Engine worktree `/home/vimkim/gh/cb/CBRD-27443-fd-clean`, branch `CBRD-27443-fd-clean`; dispatch `b0f569011731d37516f2f62dad9d3d4c76312291`, correction `0809a480df55ac6767a905d03fa3d31edd40a93c`.
- Tests `/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean`, branch `tc/CBRD-27443-fd-clean`; dispatch `26ab88a3545aaa08a2bb5ef461b03fb0192e8a6d`, correction `27c82c071a0c6c4bb9d86376e8eee4fc67b6102e`.
- Engine changes only `src/base/background_process.{cpp,hpp}` and `src/broker/broker_process.{cpp,hpp}`. Tests add `broker_scaling_matrix.py`, register it in `cbrd_27443.sh`, and retain actual cleanup process snapshots in `broker_fixture.py` without changing the cleanup assertion.
- Original ticket06 compatibility correction is preserved; `src/executables/util_service.c` and `replication_matrix.py` are unchanged by this correction. No approved 0→1 exception is inferred.
- Exact build installed under `/home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc`; retained immutable copy `/home/vimkim/.cache/cbrd27443-07s-0809a480/cubrid`.

## Confirmed regression and correction

The original ticket07 group held four startup descriptors per producer until outer finish. An ordinary valid configuration with MIN/MAX_NUM_APPL_SERVER=32 and soft RLIMIT_NOFILE=128 started all 32 CAS on immutable pre07 `41ac0c2`, with real CCI SQL returning 27443. The dispatch build `b0f5690` returned 1, emitted nine `cub_cas: Too many open files` messages and rolled back. Raising only its soft limit to 256 restored success. This was a real product regression, not a fixture or environment failure. Baseline still retained caller pipes and locks; baseline functional success is not a claim that its EOF behavior passed.

Original differential evidence and all 36 recorded/installed/actual runtime object triples are retained under `/home/vimkim/.cache/cbrd27443-08-scaling/{identity.json,audit.json,pre07/s08.json,current/s08.json}`. A persistent test written before correction independently fails on exact b0 at the expected 32-CAS/128 success assertion: `/home/vimkim/.cache/cbrd27443-07s-red/b-scale.json`.

Main approved the following narrow design before implementation:

- One invocation-owned channel/relay per service destination (`broker-console.log`, `cas-console.log`, `proxy-console.log`), shared by initial producers using that destination. No global owner or cross-invocation transport.
- The parent retains two producer pipe write ends plus the existing four startup/control/acknowledgement FDs per destination. At most three destinations means 18 persistent channel FDs, independent of CAS count or number of configured brokers. No soft/hard limit is changed.
- Existing initial/readiness/registration checks and outer finish points remain untouched. Earlier ready CAS, and a completed first broker, continue forwarding diagnostics until the same outer boundary. There is no per-child early finish, new readiness criterion, product timeout or success-on-exec rule.
- Each producer still gets null stdin, explicit stdout/stderr pipes and closure of unrelated inherited FDs. Parent-prepared argv/environment and each initial child's legacy SIGCHLD policy remain unchanged. Internal CAS/proxy restart policy is unchanged.
- The optional `background_process_streams` argument is the only new shared-helper contract. Default callers keep the prior per-producer behavior. A reused stream still performs the existing log-open/start marker validation before every producer, then safely spawns the producer. Console retention, draining/error policy and finite finish barrier are unchanged.
- Independent lightweight PID records preserve per-producer reaping ownership; relay state belongs to its destination. A successful relay remains owned and finishable when its first producer fails to exec, even when no producer ever successfully starts. Failed setup before a relay exists has no acknowledgement to read.
- Producer exec classification is cleared before parent environment/path preparation, including on reused entries, so a previous exec failure cannot turn a later allocation/setup failure into preserved legacy success.
- All shared producer write ends are closed at outer finish; all control barriers are signaled before draining every service stream and checking each relay acknowledgement. Setup/output errors remain checked before admin rollback.

Each service retains bounded 8 KiB framing per stream. Shared producer pipes preserve the original caller-pipe atomicity for writes up to PIPE_BUF. Multi-write/long producer records can interleave as they could in the original shared caller pipe; the change makes no stronger whole-record guarantee for those writes. Existing console logging and marker serialization still use the stable log lock.

## Persistent functional regression

`broker_scaling_matrix.py` executes real `cubrid broker start`, real installed CAS, and CCI prepare/execute/fetch through the actual broker. It remains in the sustainable native shell case for ticket08's final integrated run.

| Scenario | Actual limits | Result and evidence |
|---|---|---|
| Ordinary 32 CAS | soft 128 | Success, exactly 32 CAS, CCI SQL 27443, caller EOF and lock release before stop. |
| Ordinary 32 CAS with probes | hard = soft 128 | Success, all 32 actual producers retain both limits; maximum sampled launcher FD population 21. |
| SHARD 32 CAS with real proxy | hard = soft 1024 | Success and real CCI SQL; maximum sampled launcher FD population 32. The pre-existing configuration check requires 560 FDs, so hard 128 is not a valid SHARD configuration here. |
| Two ordinary brokers, 32 CAS each | hard = soft 128 | Success, exactly 64 actual CAS, SQL on both ports 35441 and 35446; maximum sampled launcher FD population 21. |
| Late missing CAS executable after 31 successful CAS | hard = soft 128 | Preserved ordinary legacy code 0 and `cub_cas: No such file or directory`; 31 actual CAS and SQL observed before restoration/stop. No false functional claim for the missing producer. |
| Late console setup fault after 31 successful CAS | hard = soft 128 | Checked code 1 and `cub_cas: Is a directory`; every earlier broker/CAS is rolled back and private SysV IPC is empty. |
| Restored setup, original binaries | hard = soft 128 | Fresh 32-CAS success, real SQL, explicit broker stop and strict no-process/no-IPC cleanup. |

For each successful probed group, every CAS writes 128 distinct short records to each stream (4,096 per stream for 32 CAS, 8,192 for two brokers). Assertions compare complete sets and counts, preserving intact concurrent diagnostics. The first CAS also forks a short fixture-only writer that emits a final record after the last configured CAS is reached; in the multiple-broker scenario, the first broker's early CAS waits for the second broker's last producer. The last producer waits for those writer acknowledgements before exec. This proves output remains captured past earlier per-child/per-broker readiness. The same complete output checks apply to both late-failure scenarios.

Soft/hard limits are read from the launcher and actual running CAS `/proc/PID/limits`. Parent FD counts are sampled by actual exec-boundary wrappers. Wrapper records contain only test IDs, PID and FD counts, never the host environment. Every capture independently checks launcher code, both EOFs, caller lock and no inherited caller FD holders. The unchanged scanner includes unknown process names.

All runs use private user/mount/network/PID/**IPC** namespaces, PID1 reaper, private configuration/registry and `/tmp`, private real device mounts, and no host syslog endpoint. No host/shared service or IPC is touched.

## Retained attempts

All attempt prefixes below are under `/home/vimkim/.cache/`; each has its corresponding `.log` with the actual fixture root.

- `cbrd27443-08-scaling`: original pre07/current differential, retained independently by ticket08.
- `cbrd27443-07s-red`: persistent regression fails on exact b0 at ordinary 32-CAS/soft128 success. Namespace teardown contains failed-run descendants.
- `cbrd27443-07s-green`: product starts 32 CAS at soft128 and hard128 and captures all 4,096 lines per stream. Fixture incorrectly expected decimal SHM key35442; actual config is hexadecimal and environment key218178. This also prevented the late-writer barrier from firing. Retained NOK; keys corrected.
- `cbrd27443-07s-green2`: ordinary hard128 and late output pass. SHARD is rejected before any producer by the existing minimum-FD check (`current:128, required:560`). Retained NOK for invalid test configuration; only SHARD moved to valid1024. Ordinary/multiple-broker128 stayed unchanged.
- `cbrd27443-07s-green3`: scaling, all diagnostics, late faults/rollback and final restored SQL pass; strict final cleanup fails. No final process snapshot existed yet. Retained NOK.
- `cbrd27443-07s-green4`: same cleanup failure reproduced with actual retained snapshot. Final recovery broker PID604, CAS606–637 and relays603/605 remained; all belonged to the last successful recovery capture. Fixture `cleanup()` stops the configured service list (`service=server`), so it correctly stopped server/master but did not stop the separately launched broker. The new final recovery block had omitted the explicit broker stop used by earlier broker tests. Added that explicit stop; no product code or cleanup assertion was weakened. Failed namespaces are destroyed by their reaper.
- `cbrd27443-07s-green5`: **147 checks pass**, including empty `cleanup_processes` and private SysV IPC after the explicit stop. This is the exact committed test content.
- First source commit attempt was reformatted/rejected by the normal code-style hook; inspected the formatting-only changes, restaged, and normal hooks passed. No bypass.

## Build and focused commands

Exact source0809 was configured/built through the live debug_gcc personal recipes, then explicitly initialized without creating a host database:

```sh
direnv exec . just configure
direnv exec . just build
cub-workenv init --worktree /home/vimkim/gh/cb/CBRD-27443-fd-clean \
  --install /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc \
  --preset debug_gcc --no-db
```

Logs: `cbrd27443-07s-{configure,build,init}.log`. UNIT_TESTS=OFF; no CTest pass is claimed. Inspected and restored only generated `cubrid-cci/win/cci_version.h` after the build.

Each focused driver uses the committed namespace launcher:

```sh
bash /home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean/shell/_01_utility/cbrd_27443/cases/run-probe.sh \
  /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc \
  /home/vimkim/.cache/cbrd27443-07s-focused MODE MATRIX
```

Focused modes/matrices: `b-broker broker_matrix`, `b-failure broker_failure_matrix`, `b-recovery broker_recovery_matrix`, `matrix matrix`, `repl replication_matrix`. Scaling final uses `cbrd27443-07s-green5 b-scale broker_scaling_matrix`. These are isolated real CLI focused checks, not a new native testkit verdict. Main explicitly deferred the complete all-matrix native run to ticket08's required final integrated qualification, avoiding a duplicate full run.

## Final focused verdict and provenance

All six direct CLI driver invocations returned 0, and independent `/home/vimkim/.cache/cbrd27443-07s-verify.py` verification returned 0 after inspecting every positive matrix assertion, EOF/lock/holder capture, terminal cleanup assertion, exact worktree identity, and runtime object. **1,076 checks pass**, plus **nine supplemental restart/output checks**. This remains focused CLI evidence, not a native testkit verdict.

| Module | Checks | Evidence |
|---|---:|---|
| Scaling | 147 | `/home/vimkim/.cache/cbrd27443-07s-green5/b-scale.json` |
| Broker lifecycle | 301 | `/home/vimkim/.cache/cbrd27443-07s-focused/b-broker.json` |
| Broker failures | 117 | `/home/vimkim/.cache/cbrd27443-07s-focused/b-failure.json` |
| Broker recovery | 77 | `/home/vimkim/.cache/cbrd27443-07s-focused/b-recovery.json` |
| Generic startup | 121 | `/home/vimkim/.cache/cbrd27443-07s-focused/matrix.json` |
| Replication | 313 | `/home/vimkim/.cache/cbrd27443-07s-focused/repl.json` |

The prior broker failure matrix qualifies the zero-successful-producer case: missing first broker/CAS/proxy retains the exact prior public code/diagnostic, new relay/log setup faults return failure, and startup capture/rollback finish correctly. The lifecycle/recovery matrices retain real ordinary/SHARD SQL, initial SOURCE_ENV/signal assertions, complete verbose startup, independent CAS/proxy replacement, actual ENOENT restoration, unknown-process scans and private IPC cleanup. Supplemental checks verify five internal-restart stdio/FD snapshots and 4,000 restarted CAS/proxy output lines per stream in the dedicated broker console.

The unchanged replication matrix confirms original local copy/apply/replication missing-executable 0 and heartbeat failure 1, checked setup failure precedence, actual rows 1–11, automatic producer restarts, remote starts and complete two-node cleanup. No ticket06 contract or prior assertion was relaxed. Its detailed count of 313 reflects the committed correction matrix and actual enumerated process population.

Fresh provenance is retained in `/home/vimkim/.cache/cbrd27443-07s-0809a480/verification.json` and `verification.log`: **18 installed/immutable-copy SHA256 pairs** and **126 actual fixture-object comparisons** (four broker fixtures, generic fixture, and two replication nodes) all match. This includes cubrid, server/master/PL/admin/console, broker admin/broker/CAS/proxy, broker monitor/changer, CSQL, the CCI library, brokeradmin library, and all three client/server/standalone libraries. Recorded broker hashes and both replication node hashes also match the fresh installed hashes.

Actual retained version: `CUBRID 11.5.0.2659-0809a48`, Linux 64-bit Debug. Focused fixtures copy executable binaries and reference the selected installation's libraries; their actual bytes were rehashed while exclusive build ownership prevented replacement. The immutable full installation copy preserves those same bytes for later review even after ticket08 rebuilds the selected install. Do not reinterpret a later changed install symlink target as the version executed in this run.

Both worktrees are clean at the exact commits above; dispatch-range `git diff --check` passes in both. All meaningful source/tests are committed, normal formatting hooks passed, and no further edits/builds are pending. Final source/test ownership is released.

## Remaining boundaries and handoff

Main may now resume ticket08 with the exact clean source/test/install state above. Final08 must run the complete native case including the new scaling module and its separately owned interaction additions. Earlier exact native passes remain historical and do not qualify this correction.

Windows/non-Linux runtime and an external ODBC gateway backend remain unverified. The new API remains under existing POSIX guards; no Windows branch was modified. No source outside the four listed files changed, no shared-helper default was deliberately altered, and no merge/rebase/push/PR/CI/JIRA/host-service action or nested agent occurred. Main alone owns docs, tracker and final acceptance.
