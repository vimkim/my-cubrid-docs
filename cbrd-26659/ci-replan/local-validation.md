# CBRD-26659: local testcase validation

Research date: 2026-10-08 (Asia/Seoul). The user clarified that validation stays **local**, initially with **OptDebug**. SQL around ten minutes and shell around ten minutes are separate, informal design guidance. There is no combined 600-second cap, per-configuration timing gate, 480-second target, company-worker resource mandate, or company GHA timing acceptance step. This clarification supersedes the planning assumptions recorded in [ci-environment.md](ci-environment.md); that report remains company-runner context.

This investigation used help, configuration/source reads, version inspection and read-only `cub-workenv doctor`. No build, testcase run, environment initialization, configuration change, installation or cleanup was performed.

## Installed local state

| Component | Observed state |
| --- | --- |
| Source | `CBRD-26659-oos-testcases-handover`, HEAD `fb567a629cdb390fff920542173fa36f454c74a0`; existing unrelated `cubrid-cci` modification preserved. |
| Selected build | `.env` selects `debug_gcc`; `build_preset_debug_gcc/CMakeCache.txt` records `CMAKE_BUILD_TYPE=Debug`, install `/home/vimkim/.cub/install/CBRD-26659-oos-testcases-handover/debug_gcc`, and `UNIT_TEST_OOS=ON`. This is not the agreed initial OptDebug mode. |
| Installed engine | Explicit `.../debug_gcc/bin/cubrid_rel` reports `11.5.0.2637-fb567a6`, 64-bit debug Linux, built 2026-10-08 15:01:21. Its advertised commit matches the current source HEAD. |
| Host workenv | **Explicit `direnv exec .` from the task source worktree** reports `CUBRID_RUNTIME_READY=1`, registry `.cub-workenv/databases`, and TMP `/tmp/cwe-1000/43868481c4b0`. Doctor reports an unconfirmed/stale `sp_testdb.sock` entry and 2393 inaccessible PIDs. Neither ownership nor inactivity was inferred; no socket was removed. Disposable attempts must not reuse this host registry. |
| Native runner | `/home/vimkim/.local/bin/testkit`; `--version` reports `cubrid-testkit dev`. `go version -m` records revision `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`, `vcs.modified=true`; binary SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`. The local testkit checkout has the same HEAD, but the modified-build metadata prevents assuming the binary is exactly pristine source. |
| Selected CTP assets | Worktree loader selects `/home/vimkim/gh/ctp/run-sql/CTP`, whose Git HEAD is `9c62858b10005d721546cc007be260844033b9e9`. Several tracked helper/runner files are modified and a JDBC jar is untracked. The plain shell config has retry=1; focused preparation explicitly changes it to zero in the copied attempt. |
| Java | Read-only `direnv exec .` path inspection selects `/home/vimkim/.local/share/mise/installs/java/temurin-8.0.462+8`. SQL preflight requires JDK 8 with `javac`; it must be checked again at execution. |
| JDBC readiness | `cubrid-jdbc` is uninitialized at the source's pinned `71d7dfeef93eb788f8b03b7bd21a9e4974a7a7c0`; no JDBC jar was found in the current engine install. Native SQL uses `$CUBRID/jdbc/cubrid_jdbc.jar` for fixture compilation, so the old CTP jar does not establish readiness. |
| Testcase selection | Loaded `CUBRID_TESTCASES_DIR` and `CUBRID_TESTCASES_PRIVATE_EX_DIR` are unset. Local clean develop worktrees are public `4a7a4aed983ccc0acfef7f2d970810e434ccb29d` and private `dfb7da1955173d6858703b15818fe030ff178d1e`. Future attempts must explicitly bind the chosen testcase task worktrees and record their HEAD/diff; do not assume these develop snapshots are the intended submission baseline. |

Evidence for selected paths: [loader, lines 41–57 and 88–99](/home/vimkim/my-cubrid/stow/cubrid/.envrc:41), [current preset](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.env:1), [current cache](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/build_preset_debug_gcc/CMakeCache.txt:31). Identity observations above come from `git rev-parse`, `git status --short`, `git submodule status`, `testkit --version`, `go version -m`, `sha256sum`, explicit `cubrid_rel`, and whitelisted path printing through `direnv exec .`. No environment secrets were dumped.

The ambient tool shell is a different observation: `direnv status` reported a previously loaded PR-8096 worktree, and plain `command -v cubrid` / `command -v csql` found neither executable. Its inherited `CUBRID` or preset must not identify this task's execution environment. The table describes recorded task configuration, the explicitly addressed installed binary, and a task-specific per-command load; changing a tool call's working directory alone does not load that environment.

## Prepare the agreed build later

The live interface was checked with `just --list` and `just --show`. `just build` compiles/installs with logs; `just test`, `just ctest`, and `just build-test` run configured **ctest**, not SQL/shell regression suites. The existing `just ctp::shell-debug*` recipes explicitly run legacy CTP and are not the native focused-run workflow. Evidence: [core recipes](/home/vimkim/my-cubrid/stow/cubrid/.just/core.just:172), [CTP recipes](/home/vimkim/my-cubrid/stow/cubrid/.just/ctp.just:5).

`cmake --list-presets=configure` includes the upstream `optdebug`; it sets `CMAKE_BUILD_TYPE=OptDebug` and has a matching build preset. Use this name, rather than treating `debug_gcc` as equivalent: [CMakePresets.json](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/CMakePresets.json:36).

The current Git rule chooses the checkout from its starting branch: create/reuse a sibling topic worktree from main/develop/feature, but use an existing other named task checkout directly. **Do not create another source worktree from the existing CBRD-26659 task branch merely to avoid its ready Debug workenv.** Build/install optdebug in the selected checkout through the live build interface and bind disposable native attempts explicitly.

For a **previously uninitialized checkout permitted by that Git rule**, the future first-use preparation is:

```bash
just -f "$HOME/my-cubrid/cubrid-justfiles/justfile" -d . prepare-build
just preset optdebug
git submodule update --init cubrid-jdbc
direnv exec . just configure
direnv exec . just build
direnv exec . sh -c 'cub-workenv init --worktree "$PWD" --install "$CUBRID" --preset "$PRESET_MODE" --no-db'
```

These commands are planning instructions, not executed work. Build/install and host initialization are separate operations; `--no-db` avoids creating an ordinary host testdb solely for disposable regression runs. A ready workenv records one install/preset, and repeated `init` does not change that selection. Do not apply the first-use initialization sequence blindly to the existing debug_gcc workenv. A host-execution transition needs explicit compatibility review; a focused native contained attempt can instead select the matching OptDebug install with its complete attempt-owned configuration/registry/TMP and paths. Its preflight checks selected install directories, installed commit, Java and containment, rather than requiring a ready host allocation. Preserve the existing host environment and do not run plain host DB commands under a mismatched selection. Evidence: [host preparation boundary](/home/vimkim/my-cubrid/docs/host-workenv.md:8), [ready-selection behavior](/home/vimkim/gh/cubrid-workenv/docs/workflow.md:25), [focused preflight](/home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py:76), [JDBC build guidance](/home/vimkim/.agents/skills/cubrid-build/SKILL.md:107). Verify the resulting install contains the matching JDBC jar before SQL execution.

## Iteration and the complete selected OOS sets

Use [cubrid-test-sql-run](/home/vimkim/.agents/skills/cubrid-test-sql-run/SKILL.md) and [cubrid-test-shell-run](/home/vimkim/.agents/skills/cubrid-test-shell-run/SKILL.md), both governed by the [shared focused contract](/home/vimkim/.agents/skills/cubrid-common/references/testkit-focused.md). The same retained-attempt mechanism supports one tracer bullet, a coverage-family group, and the complete explicitly selected OOS delivery. It does not establish whole-repository regression qualification.

1. **Bind identity before running.** From the chosen source checkout, explicitly select public/private testcase roots and the complete matching OptDebug install/configuration/registry/TMP environment, verify tracked paths and independent answers/assertions, then run `python3 "$TESTKIT_FOCUSED" preflight --suite sql` or `--suite shell` under that selected environment. `direnv exec .` is sufficient only when its loaded selection already matches; it must not silently substitute the existing Debug host workenv or an unrelated inherited shell. Set `TESTKIT_FOCUSED=/home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py`. Retain its source/install commit, runner hash, CTP/JDK paths and containment result. Never bypass a source/install mismatch by default. [Preflight implementation](/home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py:57).
2. **Make a fresh attempt.** Copy the selected install and CTP assets to unique retained attempt paths, preserving any copied database registry under another name and creating an empty attempt registry. SQL copies the selected case groups, including answers and fixtures, with their relative layout intact. Shell reads the chosen corpus through the disposable disk overlay. Rebind every runtime path, including `CUBRID_CONF_FILE` and `init_path` where inherited, to the attempt; verify native executable resolution. [Attempt contract](/home/vimkim/.agents/skills/cubrid-common/references/testkit-focused.md:17).
3. **Freeze the case list.** SQL expected paths refer to copied `.sql` files in execution order. Shell expected paths name exactly `<name>/cases/<name>.sh`, sorted reproducibly. For the final selected sets, reconcile this list with every delivered case in the coverage table. Preserve required grouped ordering/fixtures; unrelated corpus cases should not silently enter the run. If selected SQL groups require several invocations, verify every group and report their elapsed-time sum plus the group count.
4. **Prepare copied config.** Both suites run serially (`parallel_slots=1`). SQL preserves JDBC/locale/server/broker settings and disables memory-leak mode. Shell sets `scenario_disk=on`, exact `testcase_from_file`, retry=0, update=false, continuation=false, and file feedback. Macro skip policy remains inspectable; a selected skip cannot be counted as a pass. [Configuration helper](/home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py:276).

The exact configuration commands, after the immutable copies and expected lists exist, are:

```bash
python3 "$TESTKIT_FOCUSED" prepare-config --suite sql \
  --base-conf "$ATTEMPT_DIR/CTP/conf/sql.conf" \
  --output-conf "$ATTEMPT_DIR/conf/sql.conf" \
  --scenario "$COPIED_SQL_SCENARIO" \
  --expected-list "$ATTEMPT_DIR/expected-cases.txt"

python3 "$TESTKIT_FOCUSED" prepare-config --suite shell \
  --base-conf "$ATTEMPT_DIR/CTP/conf/shell_ci.conf" \
  --output-conf "$ATTEMPT_DIR/conf/shell.conf" \
  --scenario "$SELECTED_PRIVATE_TC_ROOT/shell" \
  --expected-list "$ATTEMPT_DIR/expected-cases.txt"
```

Use a separate `ATTEMPT_DIR` and matching manifest for each command. SQL config preparation rejects a partial scenario list; shell checks every selected path lies within its corpus. Configuration is written only to the retained attempt, never back to shared CTP.

## Execution, verdict and practical timing

After rebinding the attempt environment exactly as the shared contract specifies, the execution commands are:

```bash
TESTKIT_NATIVE=sql TESTKIT_CONTAIN=1 \
  /usr/bin/time -f 'elapsed_seconds=%e' -o "$ATTEMPT_DIR/runner-time.txt" \
  testkit sql -c "$ATTEMPT_DIR/conf/sql.conf" \
  >"$ATTEMPT_DIR/run.log" 2>&1

TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 \
  /usr/bin/time -f 'elapsed_seconds=%e' -o "$ATTEMPT_DIR/runner-time.txt" \
  testkit shell -c "$ATTEMPT_DIR/conf/shell.conf" \
  >"$ATTEMPT_DIR/run.log" 2>&1
```

Execute each under captured nonfatal shell status (`set +e`, save `$?` as `RUNNER_EXIT`, restore `set -e`) and a managed process/session. A complete environment invocation is in the [shared contract, lines 46–65](/home/vimkim/.agents/skills/cubrid-common/references/testkit-focused.md:46). Keep `TESTKIT_SLOT_VOLATILE` unset: bypassing synchronization would change durability/recovery conditions rather than simply speed the same test. Do not omit `TESTKIT_NATIVE`; omission silently delegates to CTP. [Native routing and sync semantics](/home/vimkim/gh/cubrid-testkit/main/docs/category/sql/04-configuration.md:58).

Time each suite from native runner launch through its setup, fixture creation, execution and normal teardown. Report initial copying/config preparation and verification time separately as developer-session overhead; build/download time also stays separate. Use per-case timing to find expensive cases, while whole-run elapsed includes runner setup/cleanup. Around ten minutes is guidance for the selected SQL set and separately for shell; report measured values and optimize waste without rejecting a valid case at an invented numeric gate. No timing has been measured for the planned OOS delivery.

Take SQL's `RESULT_DIR` only from this attempt's `Result Root Dir:` line. Shell's is `$ATTEMPT_DIR/CTP/result/shell/current_runtime_logs`. Then:

```bash
python3 "$TESTKIT_FOCUSED" verify --suite "$SUITE" \
  --result-dir "$RESULT_DIR" \
  --expected-list "$ATTEMPT_DIR/expected-cases.txt" \
  --run-log "$ATTEMPT_DIR/run.log" --runner-exit "$RUNNER_EXIT"
```

SQL proof requires exact positive expected/executed identities, `summary_info`, `main.info`, summary/JUnit XML and every `.result`, all passing. Shell proof requires exact dispatch/finished lists, `test_status.data`, `feedback.log`, `main_snapshot.properties`, per-environment logs, JUnit and no skips or failed assertions. Runner/script exit zero alone is insufficient. Preserve failed/inconclusive attempts when later iterations pass. Evidence: [SQL verification](/home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py:424), [shell verification](/home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py:509).

## Compatibility and remaining limits

Repository review still checks existing testcase layout, shell initialization/helpers, answer encoding/order, configuration policy, cleanup and actual OOS-path evidence. Static `testkit check-cases` can inspect selected shell code for ineffective verdict calls/self-comparisons without executing the engine; its findings supplement human oracle review. [Read-only checker description](/home/vimkim/gh/cubrid-testkit/main/README.md:128).

Current company CTP configuration is context for these conventions, not a new execution requirement. Native SQL's published equivalence gate has passed, while native shell's whole-corpus gate remains open; neither establishes compatibility of this newly authored selected OOS set. The actual local CTP assets are older and modified, so record those differences. A separate **local** CTP comparison can be considered only if explicitly requested; it must use independent retained attempts and must not replace or hide a native failure. [Gate state](/home/vimkim/gh/cubrid-testkit/main/README.md:78), [fallback policy](/home/vimkim/.agents/skills/cubrid-common/references/testkit-focused.md:65).

Outstanding execution prerequisites are the agreed OptDebug install, initialized matching JDBC dependency, explicit testcase roots/revisions, exact final manifests, and runtime containment preflight. The host socket warning remains preserved; no broad process/IPC cleanup is part of this plan. Final local evidence must demonstrate every delivered selected case passed and report both suites' actual elapsed time. No company CI trigger or worker-resource validation is required for this planning phase or local acceptance.

## Ordinary HA replication feasibility

**Recommendation: retain ordinary HA replication as an explicit coverage gap/preparation dependency in the initial selected shell set.** The inspected local setup does not already provide a usable two-node topology for the accepted focused native workflow. This is an environment finding, not a claim that one compact case is too slow. No HA daemon, test, container, remote connection or configuration change was started during this inspection.

The reusable CTP harness is present at `$CTP_HOME/shell/init_path/make_ha.sh`: it reads master/slave addresses, SSH credentials, engine/heartbeat/broker/manager ports and shared-memory keys, then aliases slave execution/upload/download to CTP's Java SSH helpers. [Harness inputs and transport](/home/vimkim/gh/ctp/run-sql/CTP/shell/init_path/make_ha.sh:64), [Java invocation](/home/vimkim/gh/ctp/run-sql/CTP/common/script/run_remote_script:27). Its setup creates databases on both hosts, rewrites four configuration files, uploads them, starts local heartbeat and broker and remote heartbeat, and polls the master's active mode up to 150 seconds. The HA node list uses distinct master/slave hostnames. Cleanup stops heartbeat/service, deletes the owned database and clears `$CUBRID/log/*`; therefore both nodes must use disposable, dedicated installs and registries. [Setup](/home/vimkim/gh/ctp/run-sql/CTP/shell/init_path/make_ha_upper.sh:305), [node list](/home/vimkim/gh/ctp/run-sql/CTP/shell/init_path/make_ha_upper.sh:215), [cleanup](/home/vimkim/gh/ctp/run-sql/CTP/shell/init_path/ha_common.sh:27).

The existing `HA.properties` is populated, but both node addresses differ from this host's current interface addresses, loopbacks and hostname; it is not evidence of a local pair. Credentials were redacted and no connectivity/authentication was attempted. Its configured ports are SSH 22, CUBRID 1523, heartbeat 59901, brokers 30000/33000 and manager 8001; their availability and node installations are unverified. Merely finding host `docker`, `podman`, `sshd`, `ssh` and `expect` executables does not establish running nodes or a configured container backend. `csb`/`cluster-sandbox` are absent from PATH, and testkit's `extensions/cluster-sandbox` is an uninitialized submodule pinned at `3081496ed2aac0b61db70185107be5d16f176475` (`git submodule status`, 2026-10-08).

There is an actual reuse reference: [HA/shell/_22_ha/bug_xdbms3769/cases/bug_xdbms3769.sh at private develop `1cae6fb`](https://github.com/CUBRID/cubrid-testcases-private/blob/1cae6fbb8a90fe7ca32ddd656ed8c8961aab9f51/HA/shell/_22_ha/bug_xdbms3769/cases/bug_xdbms3769.sh#L3) runs insert, delete and update on a master and compares master/slave query files before cleanup. It belongs to **cubrid-testcases-private**, a third repository whose HA corpus was not found in the checked local roots, rather than the included private-ex repository. Its [fixture](https://github.com/CUBRID/cubrid-testcases-private/blob/1cae6fbb8a90fe7ca32ddd656ed8c8961aab9f51/HA/shell/_22_ha/bug_xdbms3769/cases/3769.sql#L1) uses BLOB/CLOB, so this is a structural replication reference, not existing OOS coverage. Its bare sleeps, `wirte_nok` typo and master/slave agreement oracle need review before adapting it: an OOS case also needs independently specified expected values and explicit OOS-path proof. An older different-engine/two-machine CTP measurement reported 75.2 seconds for this reference; it does not predict or validate this task's local runtime. [Historical measurement](/home/vimkim/gh/cubrid-testkit/main/docs/project/evidence/ha/p1-sleep-to-wait.md:3).

The inspected private-ex `develop` shell scripts contain no calls to `setup_ha_environment`, `wait_for_slave` or `run_on_slave` (`rg`, 2026-10-08). Existing [changemode utility coverage](/home/vimkim/gh/cubrid-testcases-private-ex/develop/shell/_01_utility/_39_changemode/itrack01/cases/itrack01.sh:14) starts a local HA database; [applylogdb/copylogdb help coverage](/home/vimkim/gh/cubrid-testcases-private-ex/develop/shell/_06_issues/_14_1h/bug_bts_13747/cases/bug_bts_13747.sh:7) invokes utilities without database arguments. Neither demonstrates ordinary replication to a slave.

Two native-runner restrictions are concrete. The native shell deployment has no `DeployHA` adapter writing this attempt's `HA.properties`. Also, even one contained real shell worker receives its own network namespace with loopback/dummy local interfaces, so the copied historical SSH helper cannot reach those external node addresses as configured. The outer containment alone does not create the network namespace; the shell slot does. [Unimplemented deployment adapter](/home/vimkim/gh/cubrid-testkit/main/docs/project/design/module-shell.md:56), [single-worker slot creation](/home/vimkim/gh/cubrid-testkit/main/internal/runner/shellsuite/shell.go:302), [network isolation](/home/vimkim/gh/cubrid-testkit/main/internal/contain/slot.go:78). The documented sandbox alternative provisions engine nodes without sshd/CTP/JVM facilities required by this legacy shell harness; its `ha_repl` path is a separate suite. [Topology-provider decision](/home/vimkim/gh/cubrid-testkit/main/docs/project/adr/ADR-022-topology-provider.md:73).

Including one ordinary HA case therefore requires a separate preparation/proof task: establish two isolated local nodes with distinct reachable hostnames, matching OptDebug installs and dedicated configuration/database/log ownership; provide a runner-compatible way for the shell case to coordinate them; populate attempt-owned topology/transport settings; and prove setup, bounded replication wait, reviewed expected data, OOS-path evidence on the relevant node(s), failure verdict, cleanup and elapsed time. Disabling containment or silently falling back to CTP is not the existing approved focused workflow. Once that task succeeds, a small repository-conforming replication case can enter the selected private-ex set. Until then it receives no verified coverage credit; HA failover/crash/stress remain separate gaps.
