# CBRD-27443 ticket02 worker report

Ticket02 implementation and required Linux verification are complete and committed. Exact final native result:1 testcase,1 success,0 failures,0 skips; all3 shell assertions OK. Behavioral matrices pass337 checks (121 existing-master +216 master), with39 capture attempts plus the basic present-master probe. Main retains final integration acceptance responsibility.

## Scope and commits

- Engine: `/home/vimkim/gh/cb/CBRD-27443-fd-clean`, branch `CBRD-27443-fd-clean`; dispatch base `c4e2bd9106e94e08c3fd81d31e501c28bfc6429e`.
- Engine changes: `f6d5f113285902cdb4af0f8ff1de646a81989564` (master output/FD ownership); `d0311e11d3639e3269c42097a85fdf9a85bd13bc` (Application install integration correction); final `11ad631c56b35675a96c7c9c15fc66025fb0aab0` (preserve actual daemon comm).
- Shell: `/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean`, branch `tc/CBRD-27443-fd-clean`; base `6c189443112f2931c8f49167ff5e982eadab44af`; implementation `4a201c38cf8fa3f745aff1992d3c4c68d6519fa8`, cleanup evidence correction `ad2b28a51200bbc949b38e0b5f01cc52485c6e80`, final `7df0ede4bb5e76f59f644a1d6c7df03cfcd2e93c` (explicit comm/alternate-image assertions).
- No develop rebase/merge, remote push, PR, external CI, JIRA message, tracker change, nested delegation, or host/shared service stop.

## Interfaces and preserved contracts

Service `process_master()` applies ticket01's explicit helper to `NO_DAEMON` master creation, keeping its existing port-connect readiness criterion and 180 iterations with one-second sleep. Each failed attempt finishes its anonymous output spools before retry; final attempt finishes before reporting. The utility callsite keeps its prior asynchronous SIGCHLD policy. Required descriptors are selected before exec, general inherited descriptors close, and stdin is valid `/dev/null`.

Direct daemon master uses the same helper, with a private final argv marker carrying the invoking Linux process comm and stripped before original argument interpretation. PR_GET_NAME/PR_SET_NAME failures are diagnosed; actual comm is preserved even when argv0 is unrelated. Re-exec preserves original arguments. Linux `/proc/self/exe` ensures the actual invoked executable survives alternate paths or installation disagreement; other POSIX builds resolve argv0 directly or through PATH. The daemon child keeps original signal/session/umask setup and avoids the redundant fork/wait. The direct parent observes existing port-connect readiness or exact child exit solely to finish diagnostic collection, with no new product timeout.

The historical direct-daemon parent code remains0 after successful launch even if subsequent child initialization fails. This was measured on baseline, preserved in regression, and is explicitly not a readiness guarantee. Real server registration and SQL/PL after EOF prove functional readiness for successful direct starts. Pre-launch logging/relay failures return failure and diagnostics.

Direct `CUBRID_NO_DAEMON` retains foreground standard output destinations. The pre-existing `getppid()==1` init/inittab exception retains its original PID and attached supervisor stdout/stderr contract, including its original FD cleanup. That supervisor exception is not counted as detached daemon mode; tests explicitly record attached output. Direct `cub_server` and synchronous commands keep ticket01 regression coverage. Windows paths remain unchanged and were not executed.

Master direct stdout/stderr destination: constant `$CUBRID/log/master-console.log`, append and mode0600 creation using the ticket01 relay/spools. Existing `<hostname>_master.err` stays separate. Previous master log contents are not replayed as a new attempt. Relay is compiled into the master consumer via `background_process.cpp` in the POSIX target, and `cub_console` now installs into `${CUBRID_BINDIR}` with component `Application`. Runtime log failures/rotation remain ticket04's responsibility. API signature and private relay FD protocol are unchanged.

## Baseline and intermediate evidence

- `/home/vimkim/.cache/cbrd27443-ticket02-red/binary-sha256.txt`: actual dispatch-installed binary hashes.
- `absent.json`: c4e2bd9 start code0, neither stream EOF after launcher exit+2s, caller lock unavailable while master survives.
- `direct-master.json`: code0, neither EOF; general lock already released by legacy daemon FD loop.
- `direct-init-baseline.json`: real init failure from `/tmp/CUBRID35443` directory, parent0, original socket diagnostic, eventual EOF and no survivor.
- `master-matrix.json`: persistent new absent-master test fails on EOF with dispatch binary.
- Native baseline `/home/vimkim/.cache/cbrd27443-ticket02-native-red.HBB6xG`: exact retained c4e2bd9 install, one dispatched testcase, old two shell assertions pass, new third assertion NOK on missing EOF. Runner0 is not a pass; independent verifier rejects fail count1. Source worktree had the recorded implementation patch while HEAD still matched c4e2bd9; actual old binary hashes are retained independently in the attempt.
- `/home/vimkim/.cache/cbrd27443-ticket02-green1/master-matrix.json`: early dirty implementation,70 checks/7 captures pass (absent-master six modes plus DB failure).
- `/home/vimkim/.cache/cbrd27443-ticket02-green2/master-matrix.json`: intermediate dirty implementation,205 checks/25 captures pass, including complete180-second initialization failure, direct daemon, foreground and PID1 compatibility. Later alternate-binary and install corrections require final evidence below.
- Application component baseline `/home/vimkim/.cache/cbrd27443-ticket02-component-red`: cub_master installed, cub_console absent. Command/output `/home/vimkim/.cache/cbrd27443-ticket02-component-red.log`.

## Failed exact-commit verification and corrections

`/home/vimkim/.cache/cbrd27443-ticket02-final-d0311e11d.TcO799` is NOK, not final passing evidence. Existing-master matrix121 checks passed, but direct master process discovery failed because Linux `/proc/self/exe` re-exec named it `exe`. This is a product-visible process-name regression; the final source preserves the parent's actual `PR_GET_NAME` through the private marker and checks `PR_SET_NAME` in the child, reporting failures. It preserves actual comm independently of pathname/argv0, not an inferred executable basename.

The basic probe also saw a process in its immediate post-stop snapshot; it failed before persisting the report, so the precise survivor was not retained. The observation did not establish a persistent leak. The probe now allows up to3 seconds of test-only observation for PID1 reaping, still requires an empty final snapshot, and persists failures before asserting. No product cleanup deadline changed. Final verification passed the strict empty snapshot check. The earlier failure remains recorded rather than being treated as a pass.

## Final evidence

- Exact final native attempt: `/home/vimkim/.cache/cbrd27443-ticket02-final-11ad631c5.8gBHRC`; independent verifier PASS (total1, success1, fail0); status/XML/feedback also show zero skips and3 successful shell assertions.
- Preflight: source clean, installed11ad631 matches source11ad631c56b35675a96c7c9c15fc66025fb0aab0; no mismatch bypass; containment available; native testkit SHA256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`.
- Final Application component install pass: `/home/vimkim/.cache/cbrd27443-ticket02-component-final-verdict.json`, install log `...-component-11ad631c5.log`; disposable `...-component-11ad631c5` contains master, relay and utility with SHA256 equal to final runtime binaries. Older d0311e11d component evidence remains historical.
- Final configure/build logs: `/home/vimkim/.cache/cbrd27443-ticket02-final4-{configure,build}.log`. Intermediate builds are retained under the ticket02 build/final/final2/final3 log names; they are not final binary proof.
- Actual final binary SHA256:

```text
30629a7ad66d032aca67ca3a723d6ebd0f7d1d6f4efbbae21fff25ba8aef1f6e  /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc/bin/cubrid
38d6c326e28c20fea9d0f1f344b709ad4e6f06ca365140c85267f9c72ce3e70b  /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc/bin/cub_server
162f8f3a19e3863f4ac7c9c0e01ee575fa4c699ebc3694323f82d5e4f8515971  /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc/bin/cub_master
c7bbd66b717dc86995e10248676a56a0f8a479340dff0929be9d5fce8f98d6c2  /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc/bin/cub_pl
7a43f83e59fef833312dcf988a0005a492c6f5b474c8efdcffc7e0c8d0fa0c70  /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc/bin/cub_console

```

Commands used:

```sh
# Required local workflow, after final commit:
direnv exec . just configure
direnv exec . just build
# Disposable packaging check:
cmake --install build_preset_debug_gcc --prefix /home/vimkim/.cache/cbrd27443-ticket02-component-11ad631c5 --component Application
# Exact focused attempt creation/execution (command.sh and effective config retained):
direnv exec . env CTP_HOME=/home/vimkim/gh/ctp/run-sql/CTP bash /home/vimkim/.cache/cbrd27443-run-native.sh ticket02-final-11ad631c5 /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc
# Within the contained immutable attempt, the helper executes:
TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell -c "$ATTEMPT/conf/shell.conf"
/usr/bin/python3 /home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py verify --suite shell --result-dir "$ATTEMPT/CTP/result/shell/current_runtime_logs" --expected-list "$ATTEMPT/expected-cases.txt" --run-log "$ATTEMPT/run.log" --runner-exit 0
```

The exact selected case is `shell/_01_utility/cbrd_27443/cases/cbrd_27443.sh`. Native full-corpus read-only selection uses one slot, disposable overlay, no macro exclusion, no retries/continuation/update. Fixtures use nested private user/PID/network/mount namespaces, private `/tmp`, copied installation/config/registry and PID1 reaper. Source/testcase commit IDs and patches, binary hashes, effective configuration, command, process status and verdict-bearing results are retained per attempt.

## Ticket checkbox verdicts

1. PASS — the same explicit output/FD helper is selected for service-created `NO_DAEMON` master and direct daemon master. Service retry/readiness and direct-daemon semantics are preserved; normal documented execution is covered.
2. PASS — absent-master startup succeeds with original code/result, stdout/stderr EOF, live master/server/PL, successful SQL and actual PL function output after EOF. All six collection modes pass before stopping any required process.
3. PASS — absent master + missing DB returns1 with original unknown-database diagnostic and EOF. Surviving master retains neither caller pipe/lock nor other tested inherited descriptors.
4. PASS — missing master executable, missing relay, invalid log directory/FIFO, and actual master initialization failures preserve diagnosis/EOF/cleanup. Transient initialization failure then success replays the failed attempt exactly once. Exhausted service initialization returns1 at180.346 seconds, both EOF at180.3459 seconds,180 original socket diagnostics, lock available, no process/FD holders. Direct post-launch initialization failure intentionally keeps baseline parent0 while returning original diagnostic and proving no surviving master; this is not misreported as readiness.
5. PASS — six direct daemon capture modes finish with original parent0, one running master, independent daemon session, and exact original `cub_master` comm. Actual server registration and SQL/PL work after EOF. Alternate executable invocation with unrelated argv0 preserves actual binary and comm despite a different canonical install executable.
6. PASS — master console policy is documented above; stdout/stderr are retained separately for startup replay and appended to dedicated mode0600 log, old attempt data is excluded, original master error log exists. Direct foreground `NO_DAEMON` retains actual stdout/stderr destinations, and PID1 supervisor exception retains original PID/attached streams. Direct server and synchronous command regression checks pass.
7. PASS — inherited general file FD, flock and duplicate pipe writer FD57 are released in detached modes; fresh caller lock acquisition succeeds. Six capture forms (separate/stdout-only/stderr-only/merged/cat/rg) and existing-master121-check regression pass. Pipeline launcher and collector codes are recorded independently; direct quiet `rg` collector1 is not confused with master launcher0.
8. PASS — committed contained CLI shell testcase has exact native baseline NOK and exact final native PASS. Binary hashes, source/testcase revisions, command/EOF times, live process/FD snapshots, result artifacts and failed attempts are retained. Native runner0 alone was never counted as passing.

## Exact verdict artifacts and final status

Final attempt root: `/home/vimkim/.cache/cbrd27443-ticket02-final-11ad631c5.8gBHRC`.

- `verdict.json`, `preflight.json`, `binary-sha256.txt`, `engine-commit.txt`, `testcase-commit.txt`, `expected-cases.txt`, `command.sh`, `conf/shell.conf`, `run.log`, `exit.status`.
- `CTP/result/shell/current_runtime_logs/{test_status.data,test-shell.xml,feedback.log,dispatch_tc_ALL.txt,dispatch_tc_FIN_local.txt,test_local.log}` establish the exact successful selected case and3 OK assertions.
- Existing-master matrix: `home/.cache/cbrd27443-matrix.2Lt2Jc/matrix.json` —121 checks/14 captures, no failure.
- Master matrix: `home/.cache/cbrd27443-master-matrix.zjIfWN/matrix.json` —216 checks/25 captures, no failure; all bounded cleanup snapshots empty.
- Basic present-master probe: `home/.cache/cbrd27443-present.WezWDz/present.json` —code0, both EOF, caller lock free and final cleanup empty.
- Independently inspected summary: `/home/vimkim/.cache/cbrd27443-ticket02-final-summary.json`.

Final `git status --short` is empty in both owned worktrees. Source hooks/formatter and diff checks passed; Python/shell syntax and native execution passed. Build-generated CCI `win/cci_version.h` was the only submodule modification; its exact generated version-only diff was inspected and restored after builds. No meaningful source/test changes remain uncommitted. Narrow testcase `.gitignore` only covers disposable `cases/__pycache__/`; retained evidence lives outside the repositories.

## Carry-forward decisions

Ticket03 can link/use the helper in master now; service/direct master has no new exec-preserved descriptors. Private relay protocol is unchanged, and callsites retain child reaping ownership. Ticket04 should apply rotation/runtime error policy to both `server-console.log` and `master-console.log`. The generic helper currently labels its optional args[1] start-marker field `database-hex`; for master this is argument metadata, not a database identifier. Master errors must continue using the original error-log path.

Do not simplify direct daemon parent0 into readiness, and do not classify PID1 supervisor or direct `NO_DAEMON` as the detached output contract. The native failure revealed that `/proc/self/exe` re-entry must preserve Linux comm as well as executable identity; retain both checks.

## Limits

Focused Linux CLI/native shell evidence only, no full QA or HA/broker/restart/PL-internal-FD qualification. No Windows or non-Linux runtime/build verification. Alternate executable and unrelated argv0 are exercised; deletion during launch and injected prctl failures are not runtime-tested. UNIT_TESTS is OFF, so no CTest pass is claimed. Later tickets own rotation/runtime logging, restarts/internal-FD cleanup, difficult FD-limit fallback cases, and HA/broker coverage.
