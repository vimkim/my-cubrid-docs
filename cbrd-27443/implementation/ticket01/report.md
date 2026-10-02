# CBRD-27443 ticket01 worker report

Ticket01 implementation and required Linux verification are complete and committed. Final native result: exact1 case,1 success,0 failure,0 skip;121 matrix checks passed. Main retains integration acceptance responsibility.

## Ownership and commits

- Engine worktree/branch: `/home/vimkim/gh/cb/CBRD-27443-fd-clean`, `CBRD-27443-fd-clean`.
- User-approved immutable replacement base: `15e7dc8b5b56fd8751d56ccae1fdf87d315bd35d`. The external fast-forward from the original assigned `c63a3b9` was discovered before edits, paused, and explicitly adopted by the user through main.
- Engine commits: `c98e50b26` (explicit initial-server spawn/console relay), `c4e2bd9106e94e08c3fd81d31e501c28bfc6429e` (full argv preserved despite bounded marker and diagnostic errno preservation).
- Testcase worktree/branch: `/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean`, `tc/CBRD-27443-fd-clean`.
- Testcase commits: `447d9d8d2`, `ee49d56d7`, final `6c1894431` (normalizes `cub_server.real` fixture executable to the server role).
- Case: `shell/_01_utility/cbrd_27443/cases/cbrd_27443.sh` with `probe.py`, `matrix.py`, `namespace-init.py`, `run-probe.sh`.
- No rebase, merge, push, PR, CI trigger, JIRA publication, nested delegation, shared-service stop, or tracker edits were performed by this worker.

## Behavior and durable interfaces

Only the POSIX normal server-start branch in `process_server()` selects the new background policy. `is_server_running()` still decides startup success at its original registration boundary. Direct `cub_server`, existing `proc_execute` synchronous management paths, and Windows branches retain their old execution path.

`background_process_start(path, args, relay_path, log_path, state)` prepares descriptors in the parent, launches `cub_console`, then launches the actual server. `state.pid` and `state.relay_pid` belong to the caller's child-reaping policy. The helper does not set the invoking process's SIGCHLD policy; the utility callsite retains its existing SIG_IGN policy. Failed exec children are waited by exact PID when not automatically reaped. The helper currently compiles into `cubrid-bin`; later master/PL consumers must add it to their appropriate build/link targets deliberately.

The server receives `/dev/null` stdin, private stdout/stderr pipes, and an exec-error channel marked close-on-exec. General inherited descriptors, including higher duplicate caller pipe writers and caller locks, are closed rather than unlocked. The separately exec'd relay owns only valid null standard descriptors and its internal log/input/spool/control descriptors. The post-fork child performs descriptor operations, signal reset, exec, a bounded errno write, and `_exit` on failure.

Relay private descriptor protocol: 0/1/2 null, 3 append log, 4/5 server stdout/stderr readers, 6/7 anonymous current-attempt spools, 8 completion/control reader, 9 acknowledgement writer. Parent close/control EOF requests completion, including when the caller crashes. The relay snapshots each pipe's queued bytes with FIONREAD, drains at most that amount, closes startup spool/control handles, then acknowledges. It continues logging later output until all producers close their streams. This costs one lightweight process per server generation (initial PL shares the generation's output pipes). A continuous producer cannot indefinitely extend the byte-count barrier.

`background_process_finish_start(state)` waits for that finite barrier, then replays only this attempt's stdout spool to caller stdout and stderr spool to caller stderr. Seeking/reading/writing errors report failure and retain errno. Shared persistent log offsets are never used as a diagnostic oracle.

Log destination is the constant `$CUBRID/log/server-console.log`, separate from the existing error logs, opened once with O_APPEND and creation mode 0600. Symlinks and nonregular files are rejected; O_NONBLOCK prevents an existing FIFO from hanging log open. A marker records time, launcher PID, and hex-encoded database bytes; the marker prefix is bounded and explicitly marked truncated, but argv is passed in full. Constant path plus hex encoding avoids filename injection and marker newline forging. Shared log streams can interleave across DBs; diagnostic replay remains per attempt. Logging/relay exec failures happen before server creation and report a nonzero start result even without a usable log.

## Acceptance checklist

1. PASS: newly built adopted-base15e7dc8 reproduced launcher rc0 with both EOF absent and lock unavailable; separate master was prepared before caller descriptors were created. Parent authoritative baseline: `/home/vimkim/gh/my-cubrid-docs-cbrd-27443-implementation/cbrd-27443/implementation/baseline-15e7dc8b5/`. Worker baseline install retained at `/home/vimkim/.cache/cbrd27443-baseline-install-15e7dc8`.
2. PASS (exact final native): stdout-only, stderr-only, separate, merged, cat, rg; explicit launcher and collector codes; independent EOF timestamps and launcher exit times.
3. PASS (exact final native): live server and initial PL recorded at EOF; SQL and actual PL function result27443 checked after EOF for all six capture modes. Registration criterion unchanged in source.
4. PASS (exact final native): error log remains, direct stdout/stderr fixture messages reach separate console, old sentinel survives repeated starts, mode0600 checked; marker and isolated spools define attempts.
5. PASS (exact final native): missing database retains exact server stderr diagnostic and rc1; failing child stdout/stderr preserved; missing server executable, missing relay executable, console-directory and console-FIFO failures report rc1/EOF; failed-start process cleanup checked.
6. PASS (exact final native): old-attempt sentinel excluded; concurrent other DB writes added to final matrix with explicit no-cross-replay assertions; no-log failures observable.
7. PASS (exact final native): regular caller file, flock descriptor, and duplicate stdout FD57 are absent from live server/PL/relay holders; a fresh descriptor can acquire the caller lock after caller closes its own reference.
8. PASS (exact final native): direct `cub_server` unknown-DB diagnostic and nonzero status preserved; synchronous status output and return code retained; ordinary stop/create/delete controls remain functional with dedicated regular-file redirection.
9. PASS (exact final native): persistent shell case exists and native testcase result files, dispatch, feedback, XML, counts and assertion verdicts verified. Collector/runner zero exit is never treated as product pass.

## Runs and evidence

- `/home/vimkim/.cache/cbrd27443-red.fYHOLd`: first expected missing-EOF assertion; native metadata inconclusive because 21 unrelated macro skips polluted selected totals. Its copied CTP results contained stale unrelated prior logs; DO NOT bulk-publish test_local.log. Prefer the clean red attempt below.
- `/home/vimkim/.cache/cbrd27443-red-basic.pmI3ly`: clean native baseline red, exact1 dispatched/1 failure/0 skip, missing-EOF assertion (runner rc0 correctly rejected).
- `/home/vimkim/.cache/cbrd27443-green-basic.0RsIpm`: draft native1 success/0 failure/0 skip; basic EOF/lock/server/PL regression.
- `/home/vimkim/.cache/cbrd27443-green-matrix.ICTRRl`: failed harness attempt, not a product pass. Long CUBRID_TMP exceeded Unix socket pathname length; direct daemon master control also used PIPE before ticket02. Fixed with namespace-private `/tmp` and regular-file control output.
- `/home/vimkim/.cache/cbrd27443-green-matrix2.9NEt0n`: draft native1 success/0 failure/0 skip;110 checks all passed.
- `/home/vimkim/.cache/cbrd27443-final-c4e2bd9.VxVuCJ`: setup rejection only, source/install identity mismatch because incremental build had stale version15e7dc8. No mismatch bypass used. Explicit configure then build refreshed version.
- `/home/vimkim/.cache/cbrd27443-final-c4e2bd9.2H1hAP`: exact enginec4e2bd9,76 successful matrix checks before harness StopIteration. Renaming real executable behind output shim changed `/proc/comm` to cub_server.real; subsequent test commit recognizes this precise fixture role.
- Final PASS: `/home/vimkim/.cache/cbrd27443-final-c4e2bd9-r2.mVkxfU`; exact enginec4e2bd9/testcase6c1894431; native1 success/0 failure/0 skip,121 matrix checks,14 captures, plus original probe assertions. Native verifier passed; runner rc0 alone was not used.

Every retained native attempt contains effective config, expected-cases.txt, run.log, exit.status, preflight, and native CTP result directory. Final attempts also have command.sh, engine/testcase commits and binary hashes. Effective config uses full shell corpus read-only, scenario_disk=on, one slot, file feedback, no retry/continuation/update, and empty irrelevant macro exclusion for this explicit supported Linux selection. Runtime copy, HOME, CTP, registry and tmp are disposable. Nested user/PID/network/mount namespaces retain a PID1 reaper and private /tmp; all inherited CUBRID_* runtime overrides are cleared except this fixture's selected registry/tmp.

Detailed final runtime JSON is under the final attempt's `home/.cache/cbrd27443-present.*/present.json` and `home/.cache/cbrd27443-matrix.*/matrix.json`, surviving testcase-overlay disposal. `matrix.json` records commands, actual outputs, exit/EOF times, independent lock verdicts, process IDs and FD targets. The output-shim fixture intentionally renames the real binary to cub_server.real; the process dictionary's name field records its normalized server role.

## Build and source checks

All builds/configurations used the live `direnv exec . just configure` / `direnv exec . just build` workflow. Final version refresh logs: `/home/vimkim/.cache/cbrd27443-ticket01-configure-c4e2bd9.log` and `/home/vimkim/.cache/cbrd27443-ticket01-rebuild-c4e2bd9.log`. Earlier build logs are `/home/vimkim/.cache/cbrd27443-ticket01-build*.log` and are retained. Final configure/build succeeded; generated-only CCI win/cci_version.h changes were inspected then restored.

`UNIT_TESTS:BOOL=OFF` in selected debug_gcc cache; no ctest/unit coverage is claimed. Relevant execution is native shell CLI integration. Shell syntax and Python compilation checks passed. Precommit's mandatory codestyle hook passed. Hook uses `-xT8`, introducing tabs despite textual AGENTS no-tabs guidance; main obtained explicit user approval to follow the enforced formatter. No hook bypass/modification occurred.

## Limits and required later-ticket decisions

This is ticket01 only. No whole-spec completion, whole-shell equivalence, whole-corpus CI pass, Windows build/runtime verification, non-Linux runtime verification, HA/broker coverage, master-absent EOF fix, automatic restart fix, PL internal-FD cleanup, or high-FD/lowered-hard-limit fallback proof is claimed.

Ticket03 must harden/verify the portable close-range fallback (currently loops to parent RLIMIT_NOFILE hard bound), high descriptors/closed standards, and new threaded callers' ownership and signal/reaping contracts. Linux close_range handles the actual tested path. Non-Linux pipe/mkstemp fallbacks still need their concurrency/platform review.

Ticket04 must complete bounded rotation and runtime log-write/rotation-error policy, coordinate reopen/locking across relays sharing server-console.log, and address potentially large startup spools. Current relay reports logging/spool failure during startup in its barrier status; after startup its persistent I/O error is only retained in relay status until exit, so runtime error observability is explicitly unfinished for04. No rotation or bounded-storage claim is made here. Parent/control EOF drops startup handles by implementation; dedicated caller-crash and continuous-producer stress measurements were not run in01.

## Final identity

Machine-readable full hashes: `/home/vimkim/.cache/cbrd27443-ticket01-final-identity.json` and baseline `/home/vimkim/.cache/cbrd27443-baseline-binary-sha256.json`. Final native preflight confirms source/installc4e2bd9 match. Installed version is11.5.0.2638-c4e2bd9.

- bin/cubrid: `80ab0e9786c76552633e92e8cb83ff2e07ef917e3f3c2f54551b7b87908a91c7`
- bin/cub_server: `b2a84d5cb0a30a68de8f2ff3fa0cdb86e4538078849758f7c22a5d68422b6968`
- bin/cub_master: `203d20095a6c769a85dd2118514e11ddb9bd9ef7dafb1fdc53fc683f530b7bfc`
- bin/cub_pl: `e88c551b44ac4221877a7a8de59fe10d30ab4b0212fe5735b111b2000294de20`
- bin/cub_console: `812a01d695d71289f16845c9c4d36a9479a8961fc09f6be78b9b82d83bca4d2c`

Final working-tree recheck: source and testcase both clean; git diff --check passed.

Exact final invocation: `direnv exec . bash /home/vimkim/.cache/cbrd27443-run-native.sh final-c4e2bd9-r2 /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc`. The retained attempt `command.sh` expands the explicit `TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell -c <attempt>/conf/shell.conf` invocation and verification command.

Exact final detailed evidence: `/home/vimkim/.cache/cbrd27443-final-c4e2bd9-r2.mVkxfU/home/.cache/cbrd27443-matrix.1I4ZWV/matrix.json` (121 checks,14 captures) and `.../cbrd27443-present.DdE8w1/present.json` (rc0, both EOF true, lock available while server/PL alive).
