# Ticket 04 — bounded console storage and rotation

Complete and committed. Final exact native shell verification passed1 testcase,0 failures,0 skips; all889 recorded checks passed. Both assigned worktrees are clean and released to main. No further source/test work is in progress.

## Identity and scope

Exclusive engine worktree `/home/vimkim/gh/cb/CBRD-27443-fd-clean`, branch `CBRD-27443-fd-clean`; dispatch `74ee7520a76dd5c1635bed9e75a06c233026115a`. Engine commits: `ac7f26091` (rotation and bounded startup channels), `5604e9e04` (per-open-description locking, migration, SIGXFSZ relay handling), `731b39e0f976a97f0dac62374aba976b9dca37f9` (checked startup file-limit failure and socket portability).

Testcase worktree `/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean`, branch `tc/CBRD-27443-fd-clean`; dispatch `8b00d634cfb36d654c88d747114aa126efa866c6`. Commits `6193aee65` and final `28d75755d9dd69ef61a1d80a80a37aabade3a7ab` add `rotation_matrix.py` to the existing single shell testcase, then remove the host syslog endpoint dependency with a private device tree. No default branch, merge, push, CI, PR, JIRA, tracker or documentation worktree changes. No nested agents, host services or GUI.

## Policy and behavior

- Both `server-console.log` and `master-console.log`: active file plus `.1`, `.2`, `.3`, each at most 1 MiB; total retained console content at most 4 MiB per service log. Creation and accepted files are regular, single-link, effective-UID-owned, mode0600; symlink/FIFO/directory log and lock objects are rejected. Existing oversized active and archive files keep their newest1MiB during startup migration. Archive deletion/tail migration is the explicit retention policy, not startup diagnostic truncation.
- Stable sibling `.lock` is a mode0600 regular file, exactly256 bytes after initialization. Independent open descriptions use `flock`, so relays, launchers and concurrent launcher threads coordinate correctly. Marker writes use the same lock/rotation path. Relays reopen the active name under lock for every append, never retain archived or deleted console inodes. The lock must remain in place while these relays run; replacing/removing the coordination inode or mixing old uncoordinated binaries is outside this policy.
- The lock file also preserves the latest reported failure: timestamp, PID, operation and errno. Successful writers never erase another writer's failure. On each distinct error episode the relay writes the bounded record while holding the lock and sends a nonblocking syslog datagram. A held-lock failure cannot safely change the shared record; its notification uses syslog. Lock acquisition makes at most100 nonblocking attempts separated by1ms sleeps. Filesystem scheduling/syscall stalls are not a hard real-time guarantee.
- During logging faults, failed console bytes are discarded after recording/reporting the fault; producer pipes continue draining and later writes retry. This preserves service liveness without an unbounded fallback file. If both the destination filesystem and syslog sink cannot accept any data, durable error reporting cannot be guaranteed. Tests use a namespace-private device tree and `/dev/log` for every injected logging fault. They explicitly start with no syslog endpoint, verify real character-device bindings, and retain null/zero/random/urandom plus proc-fd stdio links and private shm; no host logger is contacted.
- Startup diagnostics use bounded anonymous pipes instead of unbounded anonymous files. The parent drains each stream fairly during the original server/master readiness waits. Each pump turn has bounded reads and a monotonic time budget; no new readiness condition/deadline is added. Finish drains both streams while the relay performs the existing finite FIONREAD barrier, then reads acknowledgement. All current-attempt bytes before that barrier survive permanent-log rotation and remain on their original stream; old/other-attempt logs are never replayed.
- Caller death closes diagnostic readers/control, allowing EPIPE cleanup and continued producer logging. Runtime relay ignores its own SIGPIPE/SIGXFSZ. Startup logging blocks and consumes only newly generated synchronous SIGXFSZ in the calling thread, restores the original mask, and preserves disposition/prior pending signals. It reports inherited file-size-limit failures through the existing failure path.
- Normal server start, service master start, direct daemon master and ordinary automatic server restart share the policy through the same helper. Existing error-log destinations, direct valid stdio, PL stdio/reaping, SIGCHLD policy, registration criteria and ordinary exit contracts remain unchanged. Runtime logging faults do not stop the DB.

## Acceptance results

All seven ticket acceptance checkboxes satisfied by the final source, testcase and evidence:

- [x] Policy: limits/count/permissions/owner/rotation/runtime fault policy documented; existing error logs unchanged.
- [x] Repeatable actual executable producers write stdout/stderr beyond retention and verify bounds (runtime `/proc` FD injection is supplemental).
- [x] Restart/append and concurrent rotations retain permitted history and reopen current log paths.
- [x] Concurrent successful and missing-DB attempts each deliver320000 exact tokens per original stream beyond permanent retention, without cross-attempt contamination, including the native DB failure message.
- [x] Startup open/object/write-limit and runtime write/rotation/reopen/held-lock failures are visible and complete without an output collection hang.
- [x] Existing errors, SQL/PL, launcher codes, EOF, direct/SA/restart and descriptor regressions pass.
- [x] Source and persistent CLI testcase commits provided; policy already shared by current server/master/restart paths. Ticket08 owns final all-service combination, HA/broker remain outside ticket04.

## Retained red/green development evidence

1. `/home/vimkim/.cache/cbrd27443-04-red/{run.log,rot.json}` on dispatch engine74ee: active log was5243111 bytes after repeatable5MiB producer-FD injection; the1MiB bound failed. Runtime `/home/vimkim/.cache/fd-rot.nT3v6t` retains the oversized log.
2. `/home/vimkim/.cache/cbrd27443-04-green1/{run.log,rot.json}` on ac7: initial focused slice passed12 checks.
3. `/home/vimkim/.cache/cbrd27443-04-green2/{run.log,rot.json}` on5604: expanded focused probe passed87 checks. This predates the startup-limit fix/final testcase; it is not final acceptance.
4. `/home/vimkim/.cache/cbrd27443-04-red-fsize/{run.log,rot.json}` on5604: inherited startup file-size limit terminated the launcher with `-25` (SIGXFSZ) and empty stderr. The final testcase requires code1 and a visible `server background start` diagnostic.

5. `/home/vimkim/.cache/cbrd27443-04-731b39e.ZSmpsh` is a retained full native PASS on engine731b39e/test6193aee65: independent verifier1 case/1 success/0 failures/0 skips; all889 checks passed (121 server +216 master +74 restart +386 boundary +92 rotation). It predates only the private-device testcase portability correction. Its compact `safe-summary.json` and nine-file `copied-binary-identity.json` are retained.

These probe exits are not native testcase verdicts. All failed attempt namespaces were reaped; retained directories contain evidence only.

## Commands and final native evidence

Local build commands: `direnv exec . just configure`, then `direnv exec . just build`, after each source commit. Final logs `/home/vimkim/.cache/cbrd27443-04-{configure3,build3,init}.log`. Initialization explicitly used `cub-workenv init --worktree /home/vimkim/gh/cb/CBRD-27443-fd-clean --install /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc --preset debug_gcc --no-db`. Only generated `cubrid-cci/win/cci_version.h` changes were inspected/restored. Formatter hook rejections were restaged and committed normally; no hook bypass.

Native invocation: `direnv exec . bash /home/vimkim/.cache/cbrd27443-run-native.sh 04-731b39e /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc`.

Final attempt: `/home/vimkim/.cache/cbrd27443-04-731b39e.S8CNvN`. Exact selected testcase: `shell/_01_utility/cbrd_27443/cases/cbrd_27443.sh`. Full testcase corpus read-only, disposable scenario overlay/install/CTP/HOME, one native shell slot, no updates/retries/continuation, explicit native containment. The attempt retains preflight, commit files, empty patches, effective config, expected list, command, runner status, native result and independent verification. Raw CTP logs can include environment variables and must not be copied wholesale into shared documentation.

`preflight.json` proves clean source731b39e, installed commit731b39e, no mismatch exception, installed native testkit SHA256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`, containment available. `copied-binary-identity.json` contains full SHA256 equality for9 installed/copied files: cubrid, cub_server, cub_master, cub_pl, cub_console, csql, libcubrid.so (SERVER), libcubridsa.so, libcubridcs.so. Install prefix `/home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc`.

## Final verdict and evidence details

Final engine `731b39e0f976a97f0dac62374aba976b9dca37f9`; testcase `28d75755d9dd69ef61a1d80a80a37aabade3a7ab`. Native XML and independent `testkit-focused.py verify --suite shell` both prove the exact positive case set:1 total,1 success,0 failures,0 skipped. Runner exit0 is recorded separately and was not used as the verdict shortcut. The independent verifier was rerun after completion against the same expected list/result directory.

All889 checks passed: server121, master216, restart76, FD boundary380, rotation96, plus the separate present probe. Dynamic process/file observations can change duplicate assertion counts between runs; assertions were not removed or weakened. Final rotation includes absent host syslog endpoint, real private character devices, exact full attempt token counts, native missing-DB error, failure status/hold-lock syslog, migration/retention, caller-crash and continuous-output behavior, SQL/PL and final cleanup. The original error manager independently wrote `Database "missing_rotation" is unknown` and `Unable to restart/initialize the database server` into `home/.cache/fd-rot.2uBRwy/root/log/server/missing_rotation_20261002_2316.err` lines3 and6.

Retained result: `/home/vimkim/.cache/cbrd27443-04-731b39e.S8CNvN/CTP/result/shell/current_runtime_logs` (status, feedback, XML, case logs and summary). `verdict.json`, `safe-summary.json`, `copied-binary-identity.json`, `engine-commit.txt`, `testcase-commit.txt`, `preflight.json`, `expected-cases.txt` and config are in the attempt root. `safe-summary.json` excludes captured message bodies/raw CTP environment dumps and retains all check names/verdicts, command/EOF metadata, output sizes/hashes and volume-attempt measurements. The nine identity pairs match exactly.

Final `git diff --check` passed for both task diffs; `git status --short` is empty in both assigned worktrees. Build configuration has `UNIT_TESTS:BOOL=OFF`. Source and testcase ownership is released now; main owns acceptance/documentation/tracker updates.

| Installed/copied file | SHA256 (identical) |
|---|---|
| `bin/cubrid` | `d5466324e25aae6330a5a3c9cdb59134ea99952c2beeb5e7462b2e0c6b7329e7` |
| `bin/cub_server` | `cce857570d0437058e03db9356479919f9fe0fdbed37032f00e81a15c24a75e7` |
| `bin/cub_master` | `600fca4d623bab9b4ac0d6cb5b9e60b9e444ae8b734b36223d7934f20a66565d` |
| `bin/cub_pl` | `ea195b8b73e38487d70f5ca4198856d37d600118342965781235e7c4b9d19bd9` |
| `bin/cub_console` | `f3e143312cb5076493776595b3cd048e77c283358d6f5fda51a8a6948698f383` |
| `bin/csql` | `69834e83667bf33e9afddc7b24c140d6e56cc1cc06dc7c523a8d7ccfee43c5cf` |
| `lib/libcubrid.so` | `2ebb0af57d8d32035b10e395cf4606187130c561c4f890e624a1fcd9515ac2b6` |
| `lib/libcubridsa.so` | `9833cf8c60a12912dc96e99fb81cae2086017b3ef454910165f9ffa48a964e49` |
| `lib/libcubridcs.so` | `246ee4d261612b43607a2d268a34804b26053077445928915802eae5fe29bc86` |

## Limits

Linux debug_gcc focused CLI validation only. UNIT_TESTS is OFF: no CTest claim. No Windows, non-Linux runtime, HA two-node replication, broker, whole-corpus QA or unsupported overlong restart-registration path claim. Non-Linux socket flags have an explicit fcntl fallback; Windows paths remain excluded by the existing build boundary. As with ordinary CLI output, an external caller that refuses to consume its own pipe may apply backpressure. The testkill budget is only containment, not a product startup SLA. Ordinary filesystem syscalls can still stall on a broken filesystem; bounded lock retries do not imply a universal I/O deadline.
