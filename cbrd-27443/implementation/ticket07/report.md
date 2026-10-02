# CBRD-27443 ticket07 implementation handoff

Status: implementation and final native qualification complete; source/test ownership released cleanly to main. Main retains acceptance and Standards/Spec review authority.

## Identity and scope

- Engine worktree `/home/vimkim/gh/cb/CBRD-27443-fd-clean`, branch `CBRD-27443-fd-clean`.
- Dispatch engine base `41ac0c2ce39590349e8e5759dc376f88e1cb660b`; final candidate `928e3e5038b07dd554851cb668987118b202c51a` (implementation `00edb90df87a11998244c92a50953da8fa708a76`, rollback correction `928e3e503`).
- Shell worktree `/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean`, branch `tc/CBRD-27443-fd-clean`.
- Dispatch shell base `8c1a1bc791e5e29174fd5f6e78d98d6cec02f7bb`; candidate `b55b16a3594a6a65d162d86b03da9394f1440b58` (initial tests `9a06fe2172f7a136a9a19fabc461dd9e52bf549a`).
- Combined engine review base remains user-adopted `15e7dc8b5b56fd8751d56ccae1fdf87d315bd35d`.
- Scope is ordinary CUBRID broker/CAS and real supported SHARD proxy operation. External ODBC gateway/CAS_CGW is compiled and source-reviewed but has no configured backend here and remains functionally unverified. Do not describe this as all broker/gateway configuration compatibility.
- Ticket06 is untouched; main owns its legacy exit-code correction after this worker releases. No change to default branches, remote refs, JIRA, external CI or host services.

## Eight acceptance checkboxes

All eight implementation acceptance items have evidence below, subject to the named unverified gateway/Windows configurations. This is not a claim that every broker configuration is qualified.

- [x] 1. Separate initial and internal creation maps, including direct/indirect common-helper effects: below.
- [x] 2. Synchronous admin waits, output, redirection and existing public codes preserved; long-lived descendants detach caller descriptors.
- [x] 3. Explicit service output destinations and exec FD contracts; original broker logs remain active.
- [x] 4. Isolated initial/restarted brokers receive EOF and release locks before stop, while actual CCI client SQL succeeds.
- [x] 5. Actual SHARD proxy creation and restart tested with SQL, including executable restoration after actual execve ENOENT.
- [x] 6. Existing exec failure messages/codes and EOF retained; new console/relay setup failures checked and rolled back.
- [x] 7. Unchanged/disabled boundaries documented with source and runtime evidence; gateway/Windows limitations remain explicit.
- [x] 8. Sustainable native shell case, exact source/test commits, installed/copied/actual fixture hashes and independent verdict proof.

## Creation, output, preservation and signal map

| Boundary | Policy and output | Exec FD contract | SIGCHLD / reaping |
|---|---|---|---|
| `util_service.c:process_broker` → synchronous `cubrid_broker` | Generic `proc_execute` unchanged; admin stdout/stderr remain caller-owned, including redirects | Existing synchronous inheritance into admin unchanged | Existing synchronous parent wait and status policy unchanged |
| `broker_admin_pub.c:br_activate` → `cub_broker` | Null stdin, two producer pipes to bounded `log/broker-console.log`; initial diagnostics captured through existing broker readiness loops | Only0/1/2 survive producer exec; master SHM ID/port passed as environment strings | Parent retains existing SIG_IGN; child explicitly resets DEFAULT, as old child did |
| `as_activate` → initial or admin-added CAS | Null stdin, two pipes to `log/cas-console.log`; ordinary `ut_is_appl_server_ready` and SHARD checks pump every owned startup channel | Only0/1/2; APPL_SERVER_SHM_KEY and AS_ID environment values; client socket arrives later via SCM_RIGHTS | Preserve inherited child policy, often IGN during initial start, DEFAULT for direct add; do not impose broker restart policy here |
| `proxy_activate_internal` → initial proxy | Null stdin, pipes to `log/proxy-console.log`; channels remain owned through outer SHARD connection checks | Only0/1/2; PROXY_SHM_KEY and PROXY_ID environment values | Explicit child DEFAULT, matching old code |
| Threaded `broker.c:run_appl_server` → CAS creation/restart | Null stdin; preserve broker's dedicated stdout/stderr pipes, so restarted output appends to broker console | Only0/1/2; no listener, shared-memory backing FD, error log, previous client socket or general parent descriptor survives | Existing parent IGN; child DEFAULT, matching legacy reset |
| Threaded `run_proxy_server` → proxy restart | Same explicit internal stdio policy as CAS | Only0/1/2; proxy attaches IPC/connects sockets after exec | Existing parent IGN; child DEFAULT |
| Legacy non-CAS `admin_restart_cmd` fork branch | Parent-prepared environment, CAS console policy, inherited SIGCHLD | Only0/1/2 | Source-reviewed only: `broker_config.c:128` accepts CAS and CAS_CGW, both satisfy `broker_config.h:35` IS_APPL_SERVER_TYPE_CAS and take the earlier branch |
| `shard_admin_pub.c:24–775` raw forks | No change | Not a live boundary | Entire translation-unit body enclosed by `#if defined(UNDEFINED)` |
| Direct `cub_broker` / `cubrid_broker` entry | Reserve absent stdio before logging; every valid target stays unchanged | Direct admin descendants use policies above; direct broker retains valid own output | No new daemon/foreground semantics |
| PL, server/master/HA helper callers | Existing default signal/output policy retained | Existing explicit contracts unchanged | New optional environment/reset arguments leave prior callsite defaults intact; full prior matrices rerun |

`src/broker/broker_send_fd.c:82` sets SCM_RIGHTS at runtime; `broker_recv_fd.c` receives client sockets after exec. Shared-memory segments are attached from keys in the executable environment. Neither requires an inherited arbitrary exec FD.

`broker_process_group` is an invocation-local owner, never a global pointer. Parent code constructs argv0 and a private environment vector, applying SOURCE_ENV entries in original order and then process-key overrides; environment storage lives through the exec handshake. Threaded fork children perform only signal/FD operations, execve/execv, bounded error writes and `_exit`.

Groups pump all bounded channels fairly during the original readiness intervals. All finish barriers are signaled before any one stream drains to EOF, preserving bounded8KiB short-line framing. Explicit finish propagates output/setup failure before admin shared-memory rollback; the destructor is fallback cleanup. Existing checks/counts/readiness conditions remain; there is no success-on-exec or new product startup timeout.

The helper's child error packet separately marks whether exec was actually attempted. Only producer exec failure can use a legacy code-preservation path. New log/FD/relay preparation failure is a checked group failure. Rollback handles both an in-progress initialization and a completed loop, including a trailing disabled broker; detached pointers are cleared and completed-loop indexing is bounded.

Console logs use the already qualified1MiB active plus3 archive policy,0600 files, stable flock lock, bounded failure record and draining relay. Original CAS SQL/error and broker admin/proxy logs are not redirected or deleted by the new helper. Actual query logging is asserted.

## Preserved legacy failure contracts

Exact dispatch baseline `/home/vimkim/.cache/cbrd27443-07-fail-red/bf.json` ran against the immutable ticket06 native installation, not a rebuilt working install.

| Failure | Public `cubrid broker start` code | Original caller stderr retained |
|---|---:|---|
| Ordinary missing `cub_broker` |1| `cub_broker: No such file or directory` and `fdbr: unknown error` |
| Ordinary missing `cub_cas` |0| `cub_cas: No such file or directory` |
| SHARD missing `cub_proxy` |0| `fdbr_cub_proxy_1: No such file or directory` |
| SHARD missing `cub_cas` |1| `cub_cas: No such file or directory` and `fdbr: failed to run appl server.` |

The two legacy0 cases are not functional success claims. They preserve the agreed external code contract and are explicitly tested as unavailable-service cases. No ticket06 exception is inferred.

An active proxy PID0 now represents a failed-exec retry; intentionally disabled negative proxy PID remains disabled. Liveness never calls kill on zero/negative IDs. The original one-second proxy recheck and100ms CAS monitor interval remain. Actual syscall traces showed2 proxy and23 CAS ENOENT attempts over approximately2.303 seconds in the focused recovery run, followed by new PIDs and real SQL after restoring each executable. Initial missing-proxy recovery is also covered.

## Runtime containment and functional evidence

`run-probe.sh` now unshares IPC in addition to user/mount/net/PID namespaces. Every broker fixture asserts host/private IPC identities differ. Private config, DB registry, `/tmp`, network and PID1 reaper remain. A private device tree binds only real null/zero/random/urandom, private shm and proc FD links; `/dev/log` is absent so logging faults cannot reach host syslog. Cleanup requires no surviving service/relay processes and no private SysV shared-memory segments.

The shared process scanner includes unknown names; same-PID exit permission races receive bounded retries and persistent unreadability fails. Restart proof excludes the full pre-kill PID set, not just the killed PID. Internal parent targets are compared by their actual objects, not coincident FD numbers.

Actual ctypes CCI calls connect to private broker port35441, prepare/execute/fetch `select /*+ shard_id(0) */ 27443`, and check returned value27443. SHARD uses one real backend DB and one proxy; ordinary CAS and SHARD CAS/proxy creation, internal replacement, admin on/off, direct add and admin restart all receive functional checks. Rollback recovery additionally queries port35446 on a second broker. This is not `csql` bypassing the broker.

The matrix includes separated/stdout/stderr/merged/cat/rg captures, independent collector and launcher codes, ordinary files/locks, a confirmed caller-pipe duplicate at FD4096 with soft limit1024, direct admin closed-stdio combinations, and source-env/child-signal probes. Verbose actual executable wrappers emit4000 lines on each stdout/stderr for broker/CAS/proxy, then exec the real binaries; exact counts and subsequent SHARD SQL establish complete startup capture and readiness preservation. Wrapper records contain only six explicitly tested environment keys and signal/PID fields.

## Attempts retained

All paths below are under `/home/vimkim/.cache/`; runtime directories are recorded in their corresponding `.log` files.

| Attempt | Result / distinction |
|---|---|
| `cbrd27443-07-red/br.json` | Exact baseline leak and real ordinary SQL; NOK because fixture incorrectly expected an idle ordinary CAS to restart without the next connection trigger. |
| `cbrd27443-07-red2/br.json` | Exact baseline ordinary/SHARD SQL and replacement; intended EOF assertion fails, both streams absent and lock held, broker/CAS retain FD4096. |
| `cbrd27443-07-fail-red/bf.json` | Exact baseline public-code/diagnostic observations for four missing executables. |
| `cbrd27443-07-green1/br.json` |63 preliminary checks pass, then matrix strengthened. |
| `cbrd27443-07-green2/br.json` | NOK: fixture expected word“already”; actual preserved diagnostic is“broker is running.” |
| `cbrd27443-07-green3/br.json` | NOK: fixture used unsupported public `cubrid broker add`; corrected to actual direct `cubrid_broker add` and disabled auto-add. |
| `cbrd27443-07-green4/br.json` |281 checks pass: full ordinary/SHARD lifecycle, capture modes, SOURCE_ENV, signal/output probes. |
| `cbrd27443-07-fail-green1/bf.json` | Actual product NOK: finishing only after shared-memory cleanup left public0 for new CAS console-open failure; moved checked finish before rollback. |
| `cbrd27443-07-fail-green2/bf.json` |44 focused failure checks pass; later extended with proxy/relay and multi-broker rollback. |
| `cbrd27443-07-recover1/brc.json` |57 checks pass, including actual ENOENT and restoration+SQL for proxy/CAS and initial failed proxy. |
| `cbrd27443-07-00edb90.PvHSSd` | Superseded native candidate. Intentionally interrupted by SIGINT to its owned testkit process after source review found late rollback indexing. Runner exit0 but independent verifier correctly reports one failed case. `superseded.txt` explains why it cannot qualify final code. |
| `cbrd27443-07-rollback/rb.json` | Multi-broker rollback, no-process/no-IPC checks and restored SQL passed. NOK at new unsupported-config assertion: expected parameter name, actual preserved diagnostic is generic type mismatch. Corrected expected text. |
| `cbrd27443-07-928e3e5.qYsGp8` | Final exact candidate: runner 0, independent verifier total 1 / success 1 / fail 0; 1,822 matrix assertions pass. |

`cbrd27443-07-baseline-identity.json` independently verifies24 observed object hashes across red/red2/fail-red against the immutable41ac native installation. Baseline and fixed claims remain distinct.

## Build and native commands

Actual local build/install used the loaded `debug_gcc` preset via `direnv exec . just configure` and `direnv exec . just build`, followed by explicit `cub-workenv init --worktree /home/vimkim/gh/cb/CBRD-27443-fd-clean --install /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc --preset debug_gcc --no-db`. Logs: `cbrd27443-07-final2-{configure,build,init}.log`. CMake build typeDebug, UNIT_TESTS=OFF; no CTest pass is claimed.

Final native invocation:

```sh
direnv exec . env CTP_HOME=/home/vimkim/gh/ctp/run-sql/CTP \
  bash /home/vimkim/.cache/cbrd27443-run-native.sh 07-928e3e5 \
  /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc
```

The retained launcher uses installed native testkit SHA`31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`, exactly one shell case, one slot, full corpus read-only with scenario_disk, private install/CTP/HOME/config/registry, no updates/retry/continuation, and the explicit native family under containment. Its independent verifier checks artifacts rather than trusting runner0.

## Final exact-candidate qualification

Attempt root: `/home/vimkim/.cache/cbrd27443-07-928e3e5.qYsGp8`.

- Native runner `exit.status`: **0**. Both retained `verdict.json` and separately rerun `independent-verdict.txt`: **total 1, success 1, fail 0**. The verifier checks dispatched/finished case identities and positive assertion artifacts, not only exit status.
- Runtime identifies itself as `CUBRID 11.5.0.2655-928e3e5`, Linux 64-bit Debug. `engine-commit.txt` and `testcase-commit.txt` match the final commits above; `engine.patch` and `testcase.patch` are both empty.
- `safe-summary.json` records **1,822 passing matrix checks**, including **495 broker checks**, **nine supplemental restart/output checks**, and **90 actual fixture-object hash comparisons**. No matrix check failed.
- `copied-binary-identity.json` establishes matching installed/copied hashes for all 18 runtime objects: cubrid, cub_server, cub_master, cub_pl, cub_console, csql, cub_admin, cubrid_broker, cub_broker, cub_cas, cub_proxy, broker_monitor, broker_changer, libcubrid.so, libcubridsa.so, libcubridcs.so, libcascci.so, and libbrokeradmin.so. Supplemental verification matches those same 18 objects in all three final broker fixtures and both final replication nodes (90 comparisons).
- Three broker matrices record host IPC `ipc:[4026537350]` versus private IPC `ipc:[4026537281]`, with final no-service/no-relay/no-SysV-shm checks. Equal private identity strings across sequential fixtures reflect kernel reuse, not use of host IPC.
- Final recovery recorded two proxy and 22 CAS failed exec attempts over about 2.302 seconds, consistent with existing one-second and 100 ms monitor cadence; executable restoration yielded new processes and actual CCI SQL. Five internal-restart snapshots prove null stdin, the explicit parent's dedicated stdout/stderr objects, and no leaked parent internal FD targets.
- Retained `broker-console.log` contains exactly 4,000 restart probe lines for each CAS/proxy stdout and stderr stream, in addition to initial capture assertions. This qualifies where internally restarted output goes.

| Matrix | Passing checks | Retained matrix |
|---|---:|---|
| matrix | 121 | `home/.cache/fd-matrix.7ySeYo/matrix.json` |
| master-matrix | 216 | `home/.cache/fd-master-matrix.DBTMZb/matrix.json` |
| restart-matrix | 74 | `home/.cache/fd-restart-matrix.YYjLIL/matrix.json` |
| boundary-matrix | 386 | `home/.cache/fd-boundary-matrix.rANSAN/matrix.json` |
| rot | 96 | `home/.cache/fd-rot.CBmfCs/matrix.json` |
| ha | 152 | `home/.cache/fd-ha.v0wcax/matrix.json` |
| repl | 282 | `home/.cache/fd-repl.6z4vDD/matrix.json` |
| b-broker | 301 | `home/.cache/fd-b-broker.Oig154/matrix.json` |
| b-failure | 117 | `home/.cache/fd-b-failure.vYLSrB/matrix.json` |
| b-recovery | 77 | `home/.cache/fd-b-recovery.3qcV1P/matrix.json` |

Prior matrices total 1,327 in this run versus the prior ticket06 report's 1,326. Some detailed checks enumerate the actual process/FD population, so individual restart/boundary totals vary; no previous scenario or assertion was removed. The prior matrix sources are unchanged by ticket07; their shared namespace launcher gains private IPC isolation.

Independent verification commands:

```sh
/usr/bin/python3 /home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py verify \
  --suite shell \
  --result-dir /home/vimkim/.cache/cbrd27443-07-928e3e5.qYsGp8/CTP/result/shell/current_runtime_logs \
  --expected-list /home/vimkim/.cache/cbrd27443-07-928e3e5.qYsGp8/expected-cases.txt \
  --run-log /home/vimkim/.cache/cbrd27443-07-928e3e5.qYsGp8/run.log --runner-exit 0
/usr/bin/python3 /home/vimkim/.cache/cbrd27443-07-verify-final.py
```

Both worktrees pass `git diff --check` from their immutable ticket07 dispatch bases and have empty `git status --short`. Normal commit hooks/formatter passed; only task files were staged. The generated `cubrid-cci/win/cci_version.h` change was inspected and restored after build. No host services or shared IPC were stopped or modified. The focused native pass is not an upstream whole-corpus shell-equivalence claim.

## Limits and decisions for ticket08

- Linux native focused evidence only; no Windows build/runtime or other Unix runtime claim. Windows guards and unchanged live Windows launch branches reviewed; dead nested POSIX branches removed.
- CAS_CGW/external ODBC gateway binaries build from the modified shared code, but backend operation is unverified. No provisioning expansion is authorized; preserve this named limitation and do not claim every broker configuration passes.
- Legacy non-CAS admin restart is unreachable through the current accepted configuration table; actual unsupported APPL_SERVER rejection plus source evidence qualifies that exclusion. Disabled shard_admin code stays source-only.
- Broker process death itself has no new automatic broker supervisor; explicit off/on/start recreates it. CAS/proxy internal monitors are separately tested.
- Existing public false-success0 for ordinary missing CAS and SHARD missing proxy is preserved and documented; any later change needs its own contract decision.
- No universal readiness protocol, service timeout, process-group redesign or default-branch publication was added.
- Ownership is released with both topic worktrees clean at the exact qualified commits. Main can now perform the scheduled ticket06 compatibility correction and ticket08 integration review; do not carry forward this exact-binary claim after another source change without rebuilding.
