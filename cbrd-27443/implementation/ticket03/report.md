# CBRD-27443 ticket 03 implementation report

Ticket03 is implemented and committed, ready for main review. Final exact-commit native verifier PASS:1 selected/dispatched/finished case,1 success,0 failures,0 skips;767 detailed assertions across four matrices plus the original present probe. Both task worktrees are clean.

## Identity and scope

- Engine worktree `/home/vimkim/gh/cb/CBRD-27443-fd-clean`, branch `CBRD-27443-fd-clean`.
- Dispatch base `11ad631c56b35675a96c7c9c15fc66025fb0aab0`.
- Engine final commit `74ee7520a76dd5c1635bed9e75a06c233026115a`; ticket commits `336ef2da5`, `29e730288`, `c8532fdbd`, `74ee7520a`.
- Shell worktree `/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean`, branch `tc/CBRD-27443-fd-clean`.
- Test dispatch base `7df0ede4bb5e76f59f644a1d6c7df03cfcd2e93c`; final commit `8b00d634cfb36d654c88d747114aa126efa866c6`. All ticket testcase changes are committed on the assigned branch.
- No push, PR, rebase, merge, external CI, host/shared service operation, JIRA mutation, or tracker mutation. Main owns documentation and tracking.

## Behavior and design

Ordinary master recovery uses the existing background helper and `server-console.log`. Its attempt channel ends immediately because there is no CLI collector for automatic recovery. The monitor still checks original server registration independently; exec success does not replace readiness. No new product timeout or process-group policy was added. Synchronous setup/exec failures are paced using the existing one-second monitor interval before requeueing. Indefinite recovery remains. Review found 740–872 retries in the original one-second missing-executable windows; a formal pacing assertion also failed on the superseded336 build. The paced29e build observed3 failed attempts in2.244 seconds and subsequently recovered.

PL startup and restart use a narrow stdio-only spawning interface: null stdin, explicitly duplicated parent stdout/stderr, and no other inherited descriptors. This preserves service relay output and direct/standalone output. PL deliberately retains its previous caller-level `SIGCHLD=SIG_IGN` policy, including inheritance into the PL executable; setup errors are checked. This matters for automatic reaping after monitor destruction in a still-running standalone library caller. The shared helper never changes parent signal policy. Relay and service producer paths retain their previous child-side signal reset. Partial per-monitor waitpid reaping was evaluated and rejected before the commit because it would miss PL termination after monitor destruction.

The helper keeps its relay mapping private (destinations 0–9, producer 0–2; owned sources at least 16). It does not expose an unbounded mapping API. Every path, allocation, source duplication and signal action structure is prepared in the parent; the fork child uses signal/FD operations, exec, fixed-size error-pipe write and `_exit`. Failed exec cannot return to master or PL parent flow.

Linux tries `close_range` and then raw `getdents64` on `/proc/self/fd` with stack storage in the fork child. It avoids libc directory allocation/locks and avoids a stale parent snapshot that could miss other threads' opened FDs. If unavailable, the existing portable close loop uses the hard limit rather than the lowered soft limit, with the integer bound clamped safely. Linux raw enumeration was forced by seccomp returning ENOSYS for close_range. The portable hard-limit loop and non-Linux platforms were reviewed, not executed; a finite hard-limit loop assumes no descriptors surviving above a subsequently lowered hard limit and has cost proportional to the bound. The tested contract lowers the soft limit. Windows PL creation remains on the legacy path; no Windows build/runtime claim.

Closed stdio is reserved at utility, master, direct server and csql executable entry, before logging opens files. csql deliberately links the shared helper; its config header now precedes platform guards. The immutable old binary demonstrably replayed a server stdout marker into `log/cub_server.err` when stdout was closed; the final equivalent checks every non-console log for contamination. A separate red SA observation on29e proved parent and child fd1 both referenced `csql.err`, which contained the injected PL stdout marker. The final equivalent requires null stdout, uncontaminated error logs, working PL, and preserved stderr. Direct server gets the same narrow absent-stdout test plus a valid-stdout control. Direct/foreground valid output targets remain preserved.

No generic legacy `create_child_process` policy changed, and HA/broker paths were not implicitly migrated. Log rotation/runtime log-failure policy remains ticket 04. PL is a shared path for server/SA and therefore intentionally changes there, including use by an HA server; HA lifecycle qualification is still assigned to later tickets.

## Communication contracts

Master/server registration and client sockets are established or passed at runtime (see `tcp.c` recvmsg/SCM_RIGHTS and css_transfer_fd), not inherited from master across exec. PL connects through runtime UDS/TCP (`pl_connect_server_uds`, `pl_connect_server_tcp`). Neither new producer boundary requires an internal parent socket preserved across exec. The relay alone deliberately inherits its fixed control/data/log descriptors. SQL and PL calls after normal startup, recovery, direct master and fallback paths verify required communication remains usable; source review distinguishes those runtime sockets from an exec allowlist.

## Commands and containment

Build/install (live personal interface):

```sh
direnv exec . just configure
direnv exec . just build
```

Both were rerun after the engine commit. Debug GCC, `UNIT_TESTS=OFF`; no ctest pass is claimed. Final logs: `/home/vimkim/.cache/cbrd27443-ticket03-final2-configure.log`, `/home/vimkim/.cache/cbrd27443-ticket03-final2-build.log`. Earlier successful configure/build logs retain the `final`, `paced` and `entry` labels. The only generated submodule change was inspected and restored: `cubrid-cci/win/cci_version.h`. Normal commit hooks enforced the approved formatter; no bypass.

Native invocation from the engine worktree:

```sh
CTP_HOME=/home/vimkim/gh/ctp/run-sql/CTP \
CUBRID_TESTCASES_PRIVATE_EX_DIR=/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean \
direnv exec . bash /home/vimkim/.cache/cbrd27443-run-native.sh \
  03-final /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc
```

The recorded launcher copies installation and CTP into its retained attempt, uses one slot, full read-only shell corpus with `scenario_disk=on`, no retries/continuation/update, and exact one-case list. It invokes `TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell -c <attempt>/conf/shell.conf` and independently runs `testkit-focused.py verify --suite shell`. Testkit hash `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`. Each fixture further uses private user/PID/network/mount namespaces, private `/tmp`, and a PID1 reaper. No GUI was launched.

## Baseline and all retained attempts

- Immutable baseline native: `/home/vimkim/.cache/cbrd27443-ticket03-baseline-11ad.2dRpHv`. Source/install `11ad631` matched; source clean. Native verifier FAIL: 1 dispatched/finished, 0 success, 1 fail, 0 skip, even though runner exit was 0. Original three submatrices passed; added initial PL assertion failed. Exact target intersection: `fdtest_lgat` plus server `.err`, `.access`, `.event`. Safe detailed observation: `home/.cache/cbrd27443-restart-matrix.b2lfv0/matrix.json`. The new baseline script is also retained as `restart_matrix.py` because it was not yet tracked.
- Additional red CLI boundary on that copied immutable installation: `boundary-red.json` and `boundary-red.log` under the baseline attempt. Closed stdout misdirected `FDSTDIO-out` into `log/cub_server.err`; runtime `/home/vimkim/.cache/cbrd27443-boundary-red.6amGEG` retained.
- Development probes: `/home/vimkim/.cache/cbrd27443-ticket03-iteration/`. `restart.log` stopped on transient zombie `/proc` PermissionError; corrected scanner records all namespace processes (not just comm whitelist), permits inaccessible descriptors only for confirmed zombies, and still requires eventual empty cleanup. `restart2.log` reached SA then failed an overly narrow target selector that excluded `csql.err`/`csql.access` outside `/log`; actual parent/child snapshot retained under `/home/vimkim/.cache/cbrd27443-restart2.BJBiTM/sa-boundary.json`. `restart3.log` passed 42 checks; `boundary.log` passed 371 checks. Those iteration successes predate final signal compatibility and diagnostic-gating changes, so final native evidence supersedes them. Fixed-delay failure injection was strengthened to require a new failure diagnostic before restoring binaries.
- Superseded complete native pass: `/home/vimkim/.cache/cbrd27443-ticket03-final-336ef2da5.PDs6n8`. Independent verifier: 1 case, 1 success, 0 fail, 0 skip; 121 original,216 master,44 restart,360 boundary checks. This predates retry pacing and direct/SA absent-stdout fixes. Source/install matched `336ef2d`, clean, no mismatch exception. `copied-binary-identity.json` proves installed/attempt SHA256 equality for cubrid, cub_server, cub_master, cub_pl, cub_console, csql, libcubridsa.so and libcubridcs.so. `binary-sha256.txt` and `additional-binary-sha256.txt` hold full hashes.

The native raw CTP logs contain harness environment output and should not be copied wholesale into shareable documentation. Report filtered assertion/identity summaries instead.

Additional retained development evidence: `sa-closed-red.json/log` under the iteration directory tests the new pacing assertion against336 and fails it; despite the attempt label, it stops before SA. `sa-closed-red2.json/log` on29e passes pacing then fails closed SA stdout. Runtime `/home/vimkim/.cache/cbrd27443-sa-closed-red2.vR2411` retains `csql.err` with the injected marker and the boundary snapshot. These are probe results, not substitute native-verifier claims.

First74ee native attempt, retained NOK: `/home/vimkim/.cache/cbrd27443-ticket03-final-74ee7520a.GUOuoJ`. The native verifier reports1 failed case despite runner0. SA normal/closed output checks and direct target checks passed, then the direct functional query raced registration (client connection error). Test-only correction4c5f7cbaa observes existing `cubrid server status` registration before SQL. Source remains unchanged. Its `copied-binary-identity.json` contains all8 full executable/library SHA256 pairs and verifies copied/installed equality. `preflight.json` records clean source, installed74ee752 and exact source/install match without bypass. Source and testcase commits are also saved within the attempt.

The corrected focused `direct-ready.json/log` then passed registration and SQL but hit the stop watchdog: the observer owned the direct Popen and was not reaping it while stop waited for PID disappearance. An exact-child wait thread before stop fixes this fixture ownership cycle without global reaping or product changes. `direct-reap.json/log` passed73 checks including both direct modes, exit0 and complete cleanup.

Second74ee native attempt, retained NOK: `/home/vimkim/.cache/cbrd27443-ticket03-final-74ee7520a-reaped.T3f60D`. This longer label produced a132-byte executable path. Existing `CSS_SERVER_PROC_REGISTER::exec_path[128]` (`connection_globals.h:73`, `connection_sr.c:1049`) truncates it to127 bytes, ending `/bin/cub_s`; the correctly restored binary could never be found by master. Focused runs and earlier native labels fit the bound. Test3cb2e757e now checks this fixture precondition explicitly; the next native attempt uses a shorter label. No unrelated registration-protocol expansion was made. Engine74ee7520a and testcaseeb84a119b; copied-binary identity again verifies all8 executables/libraries.

Superseded short-label attempt `/home/vimkim/.cache/cbrd27443-03-74ee.gcPMuz` was deliberately interrupted after review requested durable per-fixture shortening too. `interrupted.json` records SIGTERM to the verified owned namespacePID1 (host326198, namespacePID1, exact attempt command), with PID1 and its contained driver subsequently absent. No host/shared service was signaled. Its failed verifier is an interrupted-run result, not acceptance evidence.

Final accepted-evidence attempt (PASS): `/home/vimkim/.cache/cbrd27443-03-final.CNCI1F`, source74ee7520a, tests8b00d634c. The fixture now uses the physical basename `fd-${mode}.XXXXXX` plus the explicit path bound; no symlink semantics change. All8 executable/library hashes again match installed and copied binaries. Existing long-install-path restart behavior remains outside the final claims.

## Ticket acceptance evidence

All eight ticket checkboxes are supported within the stated Linux/runtime and platform-review boundaries:

- [x] Ordinary automatic restart after caller resource release: final restart matrix observes fresh server and PL, SQL/PL values27443, exclusion of original pipe/file/lock targets, exactly one master/server after failure recovery.
- [x] Parent internal resources: actual target intersections are empty for initial PL, master→revived server, revived server→PL, CLI PL restart and missing-executable PL recovery. Parent resource sets are nonempty and include server error/access/event logs and DB volume/log files.
- [x] PL-only and SA: `cubrid pl restart` recovers stored procedures; missing PL executable is observed as a new failure before restoration. SA records live csql parent error/access files and clean PL exec targets. Both SA output markers remain separated. Closed SA stdout maps to null rather than csql.err. Valid and closed-stdout direct server cases serve SQL/PL and stop/reap with exit0.
- [x] FD boundaries: duplicate stdout at65535, soft limit256 after duplication, large-limit launch, forced close_range fallback, all seven closed-stdio combinations, direct daemon master variants, and descriptor-allocation failure. Intended0/1/2 targets and actual file contents are checked, including no injected console text in unrelated error logs. Caller lock acquisition and EOF occur before service shutdown.
- [x] Required communication: source review distinguishes fixed relay exec handoff from master client sockets passed at runtime and PL UDS/TCP connections opened at runtime; CLI SQL/PL and startup diagnostics remain functional. No generic legacy launcher policy was changed.
- [x] Multithread/failure/platform review: master and server thread counts exceed1 before restart; missing executables produce new diagnostics; failure leaves no extra child or zombie; persistent master failure produces3 retries over2.244 seconds and later recovers. Raw Linux fallback was exercised; portable loop/non-Linux behavior is reviewed only, with limits stated above.
- [x] Tests use actual CLI/output boundaries; private wrappers inject high/closed FDs, denied close_range, missing binaries and immediate SA/direct PL target observations. Process enumeration includes unknown names, treats unreadable live FD tables as errors and requires final namespace processes to disappear.
- [x] Integrated unchanged-path regressions:121 original startup/failure/direct/synchronous checks,216 master checks,76 restart/SA/direct checks,354 boundary checks, all passing on final source74ee7520a/test8b00d634c. Boundary counts include per-log contamination assertions, so totals can vary with the number of timestamped log files created; every final assertion is retained.

## Final handoff

Final artifact root: `/home/vimkim/.cache/cbrd27443-03-final.CNCI1F`.

- `verdict.json`: independent native verifier pass.
- `CTP/result/shell/current_runtime_logs/test_status.data`: exact1 total/executed/success and0 fail/skip.
- `safe-summary.json`: source/test identity, all767 assertion names/verdicts, actual internal FD targets, exec failure observations, retry pacing, SA/direct boundaries and clean worktree records. This is safe to copy into implementation docs; omit raw harness environment logs.
- `copied-binary-identity.json`: full SHA256 matches for the9 executable/library files.
- `preflight.json`: clean source, installed74ee752, exact source/install match, no bypass, native containment available.
- `clean-worktrees.json`: final branch/commit/status for both assigned worktrees.

Final restart runtime is `home/.cache/fd-restart-matrix.CONpSw`; its actual registered executable path is102 bytes. The earlier NOK path was `/home/vimkim/.cache/cbrd27443-ticket03-final-74ee7520a-reaped.T3f60D/home/.cache/cbrd27443-restart-matrix.a9WHyO/root/bin/cub_server` (132 bytes), truncated by the existing registration field to `/home/vimkim/.cache/cbrd27443-ticket03-final-74ee7520a-reaped.T3f60D/home/.cache/cbrd27443-restart-matrix.a9WHyO/root/bin/cub_s` (127 bytes).

No unresolved failure remains in this authorized focused Linux scope. Historical failed/interrupted attempts remain retained. No claim covers non-Linux runtime, the existing long-install-path registration limitation, whole-corpus QA, or later rotation/HA/broker tickets. The source/test worktrees are released to main after this handoff; no merge or publication was performed.

Final identity supplement also includes `lib/libcubrid.so`, which contains the SERVER implementation behind cub_server. Final `copied-binary-identity.json` therefore covers9 matching executables/libraries, including SERVER, SA and CS libraries. Earlier8-file supplements remain historical.
