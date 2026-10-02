# Ticket 05 — single-node HA descriptor lifecycle

Complete and committed. Exact native verification and independent artifact verification PASS:1 testcase,0 failures,0 skips, all1034 detailed checks including152 HA checks. Both worktrees are clean and released to main for review.

## Identity

Engine worktree `/home/vimkim/gh/cb/CBRD-27443-fd-clean`, branch `CBRD-27443-fd-clean`, dispatch `731b39e0f976a97f0dac62374aba976b9dca37f9`, implementation `8aa8fcab689088b3cd24ad6e44e567e3915eae7e`. Test worktree `/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean`, branch `tc/CBRD-27443-fd-clean`, dispatch `28d75755d9dd69ef61a1d80a80a37aabade3a7ab`, implementation `992b4076c3a8d8f8e2ee1aee7495ed8fe562b004`.

No merge/rebase/push/PR/CI/JIRA/host-service action or nested worker. Main owns docs and tracker. Formatter hook ran normally; its first autoformat rejection was inspected and restaged. The only generated CCI change, `win/cci_version.h`, was inspected and restored.

## Boundary map and behavior

| Boundary | Explicit policy and evidence scope |
|---|---|
| `util_service.c:4692 process_heartbeat_start` → `process_master` | Existing ticket02 helper: null input, dedicated master relay, unrelated FD closure. Actual absent-master HA start with caller duplicate FD4096 above lowered soft limit1024 exercises this indirect path. |
| `us_hb_process_start:4018` → `us_hb_server_start:3919` → `process_server` | Existing ticket01/04 helper pumps bounded current-attempt output during original server registration waits. No readiness or public result logic changed. Actual six capture forms and public failures exercise it. |
| `master_heartbeat.c:3073 hb_resource_job_proc_start` | Now uses `hb_spawn_process`; all HA process types share this restart boundary. Parent copies/tokenizes bounded registered arguments; no allocation/cleanup/control-flow return in the child. Existing first-registration-based30-second recovery delay, one-second failed-spawn queue, state assignment, and `HB_RJOB_CONFIRM_START` remain. Actual server restart/failed-exec/recovery tested. Actual copy/apply recovery is ticket06. |
| `master_heartbeat.c:6669 hb_start_util_process` | Now prepares bounded arguments/path in the parent, launches through the same explicit helper, and replies failure on checked launch/exec errors. Real `cub_commdb -t` IPC exercises a private executable shim, stdout/stderr preservation, master targets, missing exec, empty and excessive arguments. No two-node replication claim. |
| `master_heartbeat.c:4074 hb_spawn_process` | Null stdin; producer pipes for stdout/stderr; no master sockets, logs or unrelated descriptors retained across exec. Uses existing bounded `server-console.log` retention for HA servers and managed utility producers. Master retains its existing SIGCHLD auto-reaping; helper does not alter the parent disposition. The executed HA producer now uses the standard background-helper SIGCHLD=SIG_DFL policy; the former raw HA fork/exec inherited the master SIG_IGN. Server/PL behavior is tested, and PL explicitly reinstates its existing ignore policy at its own launch callsite. Copy/apply internal child handling remains06 qualification. |
| `util_service.c:4772 process_heartbeat_stop` / `us_hb_deactivate` | Existing synchronous `cub_commdb` IPC, deactivation/confirmation and final wait unchanged. Commands create no long-lived child themselves; any IPC-created producer is handled at its actual master launch boundary. Stop's code/output/EOF and prior start EOF are independently measured. |
| `util_service.c:3325,3607` copy/apply local starts | Direct asynchronous `proc_execute` paths are unchanged in05, explicitly applicable to06. Single-node configuration with the actual local hostname skips peer launch. An early localhost-alias probe accidentally entered these paths and retained genuine caller-FD leakage evidence; it is not a passing single-node result. |
| `us_hb_process_copylogdb:4172`, `us_hb_process_applylogdb:4258`, remote `cub_commdb -t/-h` | Local starts reach the remaining direct paths; remote managed starts reach the changed master boundary. Existing public liveness/registration checks remain unchanged. Actual replication, copy/apply initial creation/restart and remote-node functionality remain06. |
| HA server → PL | Existing ticket03 stdio-only helper is indirectly used. Real SQL plus exact PL data-row result after HA EOF/restart proves required runtime connections; volume/error-log targets are absent in PL. |

`hb_proc_make_arg` now reserves the terminating NULL and rejects empty/excessive argument lists. The utility path copies the bounded incoming command in the parent and no longer silently truncates each token through the former64-byte child buffer. The total existing1024-byte command bound and16-pointer argv storage are unchanged; no registration protocol expansion.

Automatic recovery has no CLI collector. Management IPC has only a status string, no stdout/stderr channel. Therefore both finish the bounded startup channel immediately; any early bytes copied to the master's original streams remain in the master console, while all producer bytes are retained in the server console. Registration jobs retain readiness ownership. Log retention is inherited unchanged from04: active+3 archives, each1MiB,0600, coordinated reopen/rotation and bounded observable fault status. Existing master/server error logs remain separate.

The internal raw management acknowledgement is deliberately corrected: baseline missing executable returned0 after fork despite exec failure; checked helper failure now returns `ER_FAILED`, seen as255 from `cub_commdb`. Public `cubrid heartbeat` retains success0/failure1, original result messages, unknown-DB diagnostic and current-attempt startup diagnostics. This distinction is not hidden behind a claim that all raw codes are unchanged.

## Retained development evidence

All paths below are under `/home/vimkim/.cache/`; failed namespaces exited through the private PID1 reaper. Probe exits are not native verdicts.

- `cbrd27443-05-red/ha.json`: dispatch731, `ha_node_list=fdtest@localhost` alias caused utility code to launch copy/apply against localhost because `util_is_localhost` compares the configured hostname to `gethostname`, while master normalizes localhost. Public start0 but both EOF absent and lock held by actual `cub_admin` copy/apply. Useful06 evidence, not the intended single-node no-peer fixture.
- `cbrd27443-05-red2/ha.json`: dispatch731 with actual hostname. Initial HA start0/EOF/lock pass. Automatic restarted server inherited the actual master `.err` file and socket; persistent test failed on that intersection.
- `cbrd27443-05-red3`: fixture-only invocation typo (`commdb`, installed binary is `cub_commdb`); no product claim.
- `cbrd27443-05-red4/ha.json`: retained exact731 installation from `cbrd27443-04-731b39e.S8CNvN/cubrid`. Managed shim inherited master `.err` and two actual socket targets. Missing exec baseline raw acknowledgement0. Baseline script and nine-object hashes retained in this directory.
- `cbrd27443-05-public-red/public.json`: exact731 public missing-DB baseline passes6 checks: heartbeat1/fail, original `Database "missing_ha" is unknown`, both EOF, caller resources released. Script and namespace assets retained.
- `cbrd27443-05-green1`: observer raced a dying PID: Linux denied `/proc/PID/fd` before stat becameZ. Scanner now retries that exact PID for up to200ms; persistent unreadable live PIDs still fail, confirmed zombies remain visible, no names are hidden and final cleanup remains strict.
- `cbrd27443-05-green2`: initial fixed8aa HA slice passed30 checks.
- `cbrd27443-05-green3`: lowered softlimit128 was below the server's own descriptor needs; existing coordinator assertion caused public failure. Use supported soft1024 with inherited FD4096 above it; no product limit changed.
- `cbrd27443-05-green4`: assertion incorrectly expected internal raw failure1; actual255 recorded. Corrected expected internal code; public utility expectation remains1.
- `cbrd27443-05-green5`: repeated actual restart events existed, but warning-level failure messages were filtered by default `error_log_warning=no`. Isolated configuration enables existing warning logging; no product severity change.
- `cbrd27443-05-green6`: actual warning observed; test incorrectly measured original30-second guard from kill rather than first registration. Corrected to master log registration/restart timestamps; source timing unchanged.
- `cbrd27443-05-green7`: expanded pre-native PASS147 checks. Recovery first restart30.074s after first registration,17.172s after kill;3 failed attempts in2.211s, then SQL/PL recovery. Final committed fixture additionally strengthens exact data-row PL results, immediate-parent target exclusion, no extra managed child/relay, actual high-FD/soft-limit injection and startup/restart state-transition logs.

## Build and native commands

Ran `direnv exec . just configure` then `direnv exec . just build` after the source commit; both passed. Logs: `cbrd27443-05-configure.log`, `cbrd27443-05-build.log`. Explicit `cub-workenv init --worktree /home/vimkim/gh/cb/CBRD-27443-fd-clean --install /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc --preset debug_gcc --no-db`; log `cbrd27443-05-init.log`. `UNIT_TESTS:BOOL=OFF`; no CTest claim. Python syntax and shell syntax checks passed.

Final native invocation: `direnv exec . bash /home/vimkim/.cache/cbrd27443-run-native.sh 05-8aa8fca /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc`.

Attempt: `/home/vimkim/.cache/cbrd27443-05-8aa8fca.UE7ABw`. Preflight proves clean source8aa, installed8aa, no mismatch exception, installed native testkit SHA256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`, and containment available. Full shell corpus remains read-only; scenario_disk disposable overlay; copied install/CTP/HOME; one slot; no retry/update/continuation. Each probe adds private user/PID/network/mount namespaces, private tmp and PID1 reaping. No host/shared service was stopped. Physical executable path<128 assertion preserves the existing registration field constraint.

Exact case: `shell/_01_utility/cbrd_27443/cases/cbrd_27443.sh`. Native runner status0 was recorded separately; both `verdict.json` and the rerun `independent-verdict.txt` prove exactly1 selected/dispatched/finished successful testcase,0 failures/0 skips. `test_status.data`, XML and all7 shell assertions agree. Full detailed counts:121 server+216 master+75 restart+374 boundary+96 rotation+152 HA=1034, plus the basic present probe. Count differences from04 are dynamic process/file observations, with no weakened assertions. Nine installed/copied executable/library hashes already match in `copied-binary-identity.json`: cubrid, cub_server, cub_master, cub_pl, cub_console, csql, libcubrid.so, libcubridsa.so, libcubridcs.so. Raw CTP logs must not be bulk-shared because they can contain environment values.

## Limitations and06 handoff

Linux debug_gcc focused native evidence only; no Windows/non-Linux runtime, CTest, whole-corpus qualification, two-node replication or broker claim. HA source is excluded from Windows by existing util/CMakeLists.txt. Low-level child cleanup portability coverage remains inherited03 Linux claims; portable hard-limit loop remains reviewed-only. No host service/network configuration was changed.

Actual copy/apply replication progress, initial direct utility output ownership and restart semantics remain applicable and unverified for06, even though their shared master restart and remote-management spawn implementation changes here. The real managed shim proves descriptor/output/exec-failure policy at that IPC boundary; it does not stand in for replication. Reuse server-console retention and preserve current public utility readiness checks when migrating direct paths. The localhost-alias leakage above is an additional regression condition to understand during06, not an invitation to alter node-name semantics here.

## Ticket acceptance and final evidence

- [x] All HA creation/restart/management boundaries mapped, including indirect service/PL helpers and applicable copy/apply paths.
- [x] Required master restart and management boundaries apply explicit output and FD ownership. Previously-correct initial master/server paths are exercised through actual HA CLI; unmanaged direct copy/apply work remains explicitly06.
- [x] Isolated startup/restart preserve service behavior and release caller streams/FDs/locks. Six capture forms pass; FD4096 really points to the caller pipe before lowering softlimit1024. Parent internal targets are absent after exec.
- [x] Original HA idle→standby→to-be-active→active transitions are present for initial/restarted server; exact SQL/PL data rows work after EOF. Previous start EOF and stop's own code/EOF are measured independently while master remains alive.
- [x] Public missing-DB/exec/log-open failures retain1/fail and diagnostics/EOF. Raw managed missing-exec baseline0→checked255 is explicitly distinguished; failed children and relays are absent while HA remains live.
- [x] Exact native result and actual source/install/copied binary identities retained; these are independent measurements, separate from historical reviewer reports.
- [x] Applicable unexecuted replication/other-platform paths are listed with06 follow-up; no full HA or two-node qualification claim.

Final attempt `/home/vimkim/.cache/cbrd27443-05-8aa8fca.UE7ABw` contains preflight, effective config/identity, exact case list, source/test commits with empty patches, command, runner status, native result directory, `verdict.json`, `independent-verdict.txt`, `safe-summary.json`, `copied-binary-identity.json`, and `clean-worktrees.json`. Result root: `CTP/result/shell/current_runtime_logs`. Native fixture data: `home/.cache/fd-ha.B1dWfh/matrix.json` (152 passing checks,19 separate captures), with retained private runtime logs/volumes.

Initial HA start: launcher0 at13.1400s; stdout EOF13.1399s, stderr EOF13.1400s; lock free and no caller holders while master/server/PL remain alive. Initial heartbeat stop is a separate capture: launcher0 at2.0920s, stdout EOF2.0919s, stderr EOF2.0920s. Master survives and HA children are gone. Timing values are observations, not product SLAs.

Automatic restart: first attempt30.186s after initial registration and17.130s after SIGKILL;3 failed attempts observed over2.209s with the executable absent, no zombies or duplicate master, then recovery after restoring it. Master-managed utility and automatic-restart actual-target intersections are both empty. The managed child's full exec snapshot has only null FD0 plus dedicated producer pipes FD1/2. Its immediate parent's additional targets are compared after excluding only explicitly asserted child standard targets; pre-dispatch master targets are also checked. The exact pre-management PID set is restored after failures, proving no extra failed child/relay while HA remains operational.

After recovery, both ordinary SELECT and PL return27443 in the actual data row, rather than counting column headings. Initial and restarted server logs record the full HA state progression. All six start capture forms and each stop release their own pipes/locks. Public missing-DB returns1 at1.1067s with original diagnostic; missing-executable and console-open failure return1 with caller diagnostics and EOF. Every capture's lock is available and caller-holder list empty. Final namespace process snapshot is empty after service stop/deletedb.

Source and testcase `git diff --check` against dispatch passed; final statuses are empty. `clean-worktrees.json` records exact branch/head/path/status. Source/test/build ownership is released now. No work remains uncommitted.

### Installed/copied binary identity

All nine pairs match exactly:

| Object | SHA256 |
|---|---|
| `bin/cubrid` | `b824517cb00a35f37f547da8171504f1a2f0854221095f3ee45e8e43f4c07aef` |
| `bin/cub_server` | `b926284293864e6d81249e00525ec167e987c193eba44fcd84f717056b56556c` |
| `bin/cub_master` | `10ee2100946d90810d8a348095ea5997d3572bee66c0e6fcc4727180f2ea27cf` |
| `bin/cub_pl` | `3b1f31b862443db3aa5b908a6870082fa820c36cdf4f315d2f9c4693e68fe575` |
| `bin/cub_console` | `3b0e56c13cdea7dfbe8e519f29211426af63c5c7da6ad499c6585e7acb81cc18` |
| `bin/csql` | `cf84848e0f3b60cbc1704c5270789f46fbe90309158693939340e6353a024533` |
| `lib/libcubrid.so` | `4a07e579483b2fcf8986bc827a03ab77091f0931880f904a6366fa28decd5be0` |
| `lib/libcubridsa.so` | `58684702c9550e6638ed83dffd8232a905e5dbd0f10284b31bdca58c5ffc32fc` |
| `lib/libcubridcs.so` | `bb5fd534735eec443ad5e4750fbcd1d9e4a6edcf6f2f4177675cce5e3b592f71` |

Ticket06 must inspect actual copy/apply producer spawning/reaping under the explicit default child SIGCHLD policy, test real copy/apply initial/restarted processes, and prove two-node replication progress. The managed shim here proves only its real IPC launch boundary.
