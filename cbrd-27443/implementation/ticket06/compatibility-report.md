# Ticket06 compatibility correction — verified and released

The correction is complete and committed; main retains acceptance authority. Final native and independent artifact verification PASS: **1 case, 0 failures, 0 skips; 1,843 matrix assertions plus 9 supplemental checks**. All 18 installed/native-copy SHA256 pairs and 90 actual fixture objects match. Both topic worktrees are clean. Source/test/build ownership is released to main.

This supplements the historical `/home/vimkim/.cache/cbrd27443-ticket06-report.md`, which remains unchanged. Its proposed local missing-executable 0→1 exception is superseded: no exception was approved, so this correction follows the original specification's preservation requirement. No user answer was inferred from silence.

## Exact committed state

- Engine `/home/vimkim/gh/cb/CBRD-27443-fd-clean`, branch `CBRD-27443-fd-clean`, dispatch `928e3e5038b07dd554851cb668987118b202c51a`, final **`b0f569011731d37516f2f62dad9d3d4c76312291`**. Correction commits: `356709979e27a2029e3433930ce6a799bf47bbd7`, `43d348e566b8f5172c7398d083393492259baffd`, `b0f569011731d37516f2f62dad9d3d4c76312291`. Only `src/executables/util_service.c` changed.
- Tests `/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean`, branch `tc/CBRD-27443-fd-clean`, dispatch `b55b16a3594a6a65d162d86b03da9394f1440b58`, final **`26ab88a3545aaa08a2bb5ef461b03fb0192e8a6d`**. Correction commits: `b6d3da93d14e66ad5c7718bfc81d6660977d7224`, `ecbf4426d3da13e5ca5051c3d2a886c426375dfc`, `26ab88a3545aaa08a2bb5ef461b03fb0192e8a6d`. Only the existing `shell/_01_utility/cbrd_27443/cases/replication_matrix.py` changed.

Normal hooks ran; their formatting rewrite was inspected and staged, with no bypass. Explicit NULL arguments keep new C++ default-argument syntax out of legacy C formatting regions. No rebase, merge, default-branch change, push, PR, external CI, JIRA mutation, GUI, nested agent or host/shared-service action occurred. Main alone owns docs/tracker.

## Behavioral correction and boundary map

`background_process.exec_failed`, introduced by ticket07, classifies an attempted producer exec separately from FD/signal/log/relay setup. The four local HA utility APIs now carry an explicit, invocation-local optional flag. Explicit copy/apply and replication-start request compatibility; heartbeat-start and the disabled internal helper pass NULL and retain checked failure. Only an attempted producer exec failure may produce legacy success. New setup errors always return failure, including after an earlier compatible exec failure in the same batch.

The failed producer still uses the helper's safe `_exit`; no child returns into launcher code. The parent removes the failed batch record before any liveness check or output pumping, so negative PIDs are never probed. The parent emits compatibility messages through existing catalogs. Failed producers/relays and their private channels are cleaned before the caller finishes.

| Creation/caller boundary | Final policy/evidence |
|---|---|
| `us_hb_copylogdb_start` / `us_hb_applylogdb_start` local starts | Same explicit background helper, null input, dedicated bounded output and unrelated-FD closure. New optional exec-failure flag preserves only the observed public compatibility contract. |
| `us_hb_process_copylogdb` / `us_hb_process_applylogdb` | Own pending channels through original 10-second wait and PID checks; setup/output/late-producer failures override compatibility. Remote branches retain synchronous commdb requests, original wait and registration check. |
| `process_heartbeat_util` | Exact stable original code 0, execv diagnostic, utility success/fail pair and heartbeat success/fail pair, all emitted by parent. |
| `process_heartbeat_replication` | Observed original missing-producer0 preserved. Both producer diagnostics and meaningful result counts retained; unsafe duplicated child stop/shutdown control flow removed. |
| `process_heartbeat_start` → `us_hb_process_start` | Observed original failure1 preserved with execv/HA-start/heartbeat-start failure diagnostics and safe cleanup. No compatibility opt-in. |
| Initial HA server / remote `-h nodeb` → `cub_commdb -t` → `hb_start_util_process` | Ticket05 helper unchanged; actual nodea request executes on nodeb and is followed by replicated data. |
| `hb_resource_job_proc_start` | Ticket05 helper unchanged; real copy and apply are killed separately, restarted by nodeb master, and followed by distinct replicated records. |
| Disabled `ENABLE_UNUSED_FUNCTION us_hb_utils_start` | No callers; explicit NULL preserves checked policy. Source-reviewed only. |

Generic proc_execute, bounded per-stream framing, logging/rotation policy, original registration waits, parent reaping, master restart policy and broker implementation remain unchanged by this correction. Local utility producers already had SIGCHLD DEFAULT under the old generic launcher. Ticket05 changed raw master-managed producers from inherited IGN to DEFAULT; actual copy/apply threaded runtime and live signal masks remain qualified by the final matrix. Parent pumping still performs targeted nonblocking reaping across synchronous registration helpers that may reset parent SIGCHLD.

## Exact public-contract evidence

Immutable baseline `/home/vimkim/.cache/cbrd27443-06-red4/repl.json` captures 4/8 proves explicit copy/apply missing cub_admin returns0 and these stable stdout lines, substituting the utility name:

```
@ cubrid heartbeat copylogdb
@ copylogdb start
++ copylogdb start: success
++ copylogdb start: fail
++ cubrid heartbeat copylogdb: success
++ cubrid heartbeat copylogdb: fail
```

Stderr is exactly `execv: No such file or directory\n`. Final native captures 28/35 independently match the baseline stdout, stderr and code 0 exactly, recorded in `final-code-comparison.json`. The contradictory historical result messages are intentional compatibility.

Additional sibling observations use the same immutable8aa installation and real private peers: `/home/vimkim/.cache/cbrd27443-06c-baseline/repl.json` capture 4 is replication-start0; capture 5 is heartbeat-start1. The pre-correction928 candidate observations in `cbrd27443-06c-candidate/repl.json` are replication1 and heartbeat1. Both probes complete47 checks and cleanup. Historical failed children duplicated and interleaved launcher/stop/shutdown branches nondeterministically. Final replication checks require one success and one failure per utility, two execv diagnostics, one replication success and two replication failures. They do not reproduce unsafe duplicate side effects or arbitrary interleaving. Heartbeat-start keeps meaningful failure diagnostics and code 1 with one safe cleanup path.

Final native also proves, for both utilities: unlisted DB1, remote missing executable1, relay ENOENT setup failure1 with `HA utility background start`, and console EISDIR setup failure1. Equal errno ENOENT cannot confuse relay setup with producer exec. Recovery is followed by actual replicated row11. A same-request mixed fixture configures fdtest/fdsetup under replication-start: after the first missing producer, its real relay exits and a private wrapper makes the console path a directory. The next configured launch fails EISDIR, final code is1, and the original PID set is restored. fdsetup is fault injection before producer exec, not a claimed real third database. Missing-log-parent and low-FD setup variants were not newly executed in this correction.

## Final native run and independent verification

Attempt **`/home/vimkim/.cache/cbrd27443-06c-b0f5690.RGZgmT`**. Runner exit0 is separately retained; it alone is not the verdict. Both launcher verification and an independent `testkit-focused.py verify` report total1/success1/fail0. `test_status.data` reports one selected/executed/successful case, zero failures/skips. The run took about 1057 seconds.

Selected case: `shell/_01_utility/cbrd_27443/cases/cbrd_27443.sh`. Full corpus read-only with scenario_disk, one slot, no retry/update/continuation. All prior and broker matrices are included. Preflight proves clean source b0f569011, installed b0f5690, commit_match=yes, no mismatch exception; native testkit SHA256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`. Source/test patches in the attempt are empty.

Commands:

```
direnv exec . just configure
direnv exec . just build
direnv exec . cub-workenv init --worktree /home/vimkim/gh/cb/CBRD-27443-fd-clean --install /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc --preset debug_gcc --no-db
direnv exec . bash /home/vimkim/.cache/cbrd27443-run-native.sh 06c-b0f5690 /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc
/usr/bin/python3 /home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py verify --suite shell --result-dir /home/vimkim/.cache/cbrd27443-06c-b0f5690.RGZgmT/CTP/result/shell/current_runtime_logs --expected-list /home/vimkim/.cache/cbrd27443-06c-b0f5690.RGZgmT/expected-cases.txt --run-log /home/vimkim/.cache/cbrd27443-06c-b0f5690.RGZgmT/run.log --runner-exit 0
/usr/bin/python3 /home/vimkim/.cache/cbrd27443-06c-verify-final.py /home/vimkim/.cache/cbrd27443-06c-b0f5690.RGZgmT
```

Final configure/build logs: `/home/vimkim/.cache/cbrd27443-06c-configure-3.log`, `cbrd27443-06c-build-3.log`; explicit no-DB init log `cbrd27443-06c-init-3.log`. Final source was committed before configure/build to refresh embedded SHA. UNIT_TESTS=OFF; no CTest claim. Only the inspected generated `cubrid-cci/win/cci_version.h` diff was restored.

| Matrix | Passed checks |
|---|---:|
| matrix | 121 |
| master-matrix | 216 |
| restart-matrix | 76 |
| boundary-matrix | 374 |
| rot | 96 |
| ha | 152 |
| repl | 313 |
| b-broker | 301 |
| b-failure | 117 |
| b-recovery | 77 |

All 1,843 matrix assertions pass, plus9 supplemental broker checks. Observed process-dependent assertion counts can differ between runs; no assertions were weakened. Detailed matrices, `safe-summary.json`, `independent-verdict.txt`, `final-code-comparison.json` and `copied-binary-identity.json` are retained in the attempt.

## Actual two-node data and FD evidence

Replication matrix: `/home/vimkim/.cache/cbrd27443-06c-b0f5690.RGZgmT/home/.cache/fd-repl.6SKJ17/matrix.json`. All 49 captures exit, receive all captured EOFs, release the caller flock and retain no caller holder. Both initial commands return0 while actual copy/apply processes remain alive.

- nodea: root `/home/vimkim/.cache/cbrd27443-06c-b0f5690.RGZgmT/home/.cache/fd-repl.6SKJ17/root`, address `10.44.0.1`, keeper PID 11; namespaces {'net': 'net:[4026537422]', 'uts': 'uts:[4026537421]', 'mnt': 'mnt:[4026537420]'}. Registered cub_server/cub_admin byte lengths: 95/94.
- nodeb: root `/home/vimkim/.cache/cbrd27443-06c-b0f5690.RGZgmT/home/.cache/fd-repl.6SKJ17/b`, address `10.44.0.2`, keeper PID 18; namespaces {'net': 'net:[4026537488]', 'uts': 'uts:[4026537487]', 'mnt': 'mnt:[4026537486]'}. Registered cub_server/cub_admin byte lengths: 92/91.

The peers have separate configs, registries, DB volumes, logs, network/UTS/mount namespaces and private /tmp. Node-specific hosts mounts route private veth10.44.0.1/10.44.0.2, TCP35443 and heartbeat35444. Outer user/PID/network/mount/IPC namespaces, PID 1 reaper and private real device mounts prevent host leakage; no host /dev/log exists. Every actual registered executable path is below 128 bytes without protocol expansion.

Source-only CREATE TABLE/INSERT rows are checked through explicit nodeb `fdtest@localhost`, which cannot silently fall back to nodea: boot_cl explicit-host handling and CSQL's no preferred-host/capability retry branch establish that source basis. Exact records 1–11 are retained, avoiding headings or process-presence false positives:1 initial,2 copy restart,3 apply restart,4–8 local output-mode cycles,9 remote copy,10 remote apply,11 executable/log fault recovery.

- copylogdb restart PID 569→585, master 309, unwanted master-FD intersection `[]`.
- applylogdb restart PID 573→595, master 309, unwanted master-FD intersection `[]`.
- Remote copylogdb PID 745 on nodeb under master 309, unwanted master-FD intersection `[]`.
- Remote applylogdb PID 759 on nodeb under master 309, unwanted master-FD intersection `[]`.

Live scans cover all descendants including unknown names and zombies; actual stdin is null, SIGCHLD DEFAULT and required runtime threads/communication survive. FD4096 is a real inherited caller duplicate above lowered soft 1024. Failed launch PID sets restore completely. The late concurrent short-output batch preserves all 2,000 intact lines per producer/stream; the long batch preserves20,000 newline-free payload bytes plus final unterminated tail per producer/stream. Both remain checked failure1 and are fully reaped. Final assertion confirms both private nodes and every descendant gone. Broker matrices also confirm complete private SysV IPC cleanup.

## Fresh binary identities

The following freshly computed installed and native-copy hashes are equal. `copied-binary-identity.json` records both members of every pair. Supplemental verification independently rehashes all 18 objects in nodea, nodeb, and each of three broker fixture roots:90 matching actual files. Recorded per-node and broker hashes also match; no prior-run hashes are substituted. `safe-summary.json` records the90 actual fixture identities.

| Object | Installed = native-copy SHA256 |
|---|---|
| `bin/cubrid` | `db051dd7844bf4fa48bde3687f857df8cf9c48979c0171e0410efc72e7d57344` |
| `bin/cub_server` | `8eb26587bd27e1054ad498ee221656501c1f6a1a5d885b0d3ceb88a88a660ae6` |
| `bin/cub_master` | `9f191ec2bd5a84f8cbf45933433ced0493da73ebd7673983eb07c3e13af252c4` |
| `bin/cub_pl` | `753ab60b040727b4f380e82d672835b4e52b9d6f7a95102ab57ac41f36cb69ed` |
| `bin/cub_console` | `140b59478302e158dd9074081161d72a89dd6d772d3aff80b563a0ef671c5468` |
| `bin/csql` | `79baa974178e3a10baf76137f5bd32ad180dd342dc6d9a7bbb33bd1f28c9ae05` |
| `bin/cub_admin` | `f20e75102a3b3f70bc2eb700d30d692556de68e6c570a1a0dff202cfa4a714e8` |
| `bin/cubrid_broker` | `ff542f1e782e8494f6cf704140ca3e3922325569526a737d2f86619f81e7c759` |
| `bin/cub_broker` | `2cd3b240b1e374c01315085824355a3c6b4fac81dd7919ba4c79a0fe71f1cb31` |
| `bin/cub_cas` | `a1e7688c4f7f45157596688c501517591241a729d8cd165e340742182a03011b` |
| `bin/cub_proxy` | `0cee790d24c1f0873560f185af01b307a09fde283ed35c46b0e310418f059d99` |
| `bin/broker_monitor` | `2a17f85a539807ab2b8f20f5a7b07b236cc41359a5e3666b5de938cd6cd3c74d` |
| `bin/broker_changer` | `806cb293eea845cbcf03bff739d625876bd6b17887e1262a5e1a0b3a2624fbc7` |
| `lib/libcubrid.so` | `526650a82809718a68721bfaae558e1df9df9844e0f40e905f96d13f3fdb72b3` |
| `lib/libcubridsa.so` | `7c25742ab8c44948bd50e6e025f949714fa939c016859d1e7f7c6bb693a663c5` |
| `lib/libcubridcs.so` | `15d73c6e84a26ab00ea8f6b993454385a270f5674abeec2540fd9ecc68b71c6c` |
| `lib/libcascci.so` | `9d8421a566e00b19ee25b155911dd108e8e66d8629f6b655b4b75bdaf1b7dba4` |
| `lib/libbrokeradmin.so` | `260fb947bc83afe2e57ee99c8be5895a1137049e93abbabc36db87e9ee27b2b5` |

## Retained correction attempts and limitations

All paths below are under `/home/vimkim/.cache/`; prior initial06 candidate/native evidence remains unchanged.

- `cbrd27443-06c-baseline`, `cbrd27443-06c-candidate`: sibling observational probes,47 checks each, full cleanup. Not final qualification.
- `cbrd27443-06c-red`: scratch reduction selected an earlier remote loop and failed on undefined sequence before the intended assertion. Fixture failure, not product evidence.
- `cbrd27443-06c-red2`: genuine RED on immutable928; corrected exact copylogdb expectation fails with actual1/only failure messages instead of original0/pairs. Regression was authored before source correction; failed descendants contained/reaped.
- `cbrd27443-06c-green`:129 checks pass for corrected explicit/sibling/isolated setup contracts; mixed fixture then omits required node argument and fails at usage, before intended injection. Retained; no product regression claim.
- `cbrd27443-06c-mixed`: corrected same-request fixture PASS 62 with final1 and original PID-set cleanup.
- Final native `cbrd27443-06c-b0f5690.RGZgmT`: PASS as above. No source/test drift or runner retry.
- Initial explicit cub-workenv init omitted required install/preset arguments and failed; final explicit command succeeded. Earlier configure/build attempts succeeded. Formatter first rejected/reformatted staged source; normal hooks then passed.

This is Linux focused native verification, not whole-corpus or Windows/non-Linux qualification. Disabled helper runtime remains unverified. Ticket08 owns final integration/rotation combinations; main separately owns follow-up investigation of broker FD scaling. No change or claim about that question is made here. No code exception remains pending for this ticket06 correction.

## Seven acceptance checkboxes — verified evidence, main accepts

- [x] Initial local copy/apply, remote master-managed creation and separate automatic restart boundaries investigated and handled under ticket05 contracts.
- [x] Two real isolated nodes, configs/DB/logs/private networking identified; host/shared services untouched.
- [x] All 49 final caller captures reach EOF and release locks/resources; actual required producers live during success checks, no unwanted caller/master FD remains.
- [x] Exact source records reach target after initial launch, each distinct producer restart and remote/local cycles; records 1–11 observed.
- [x] Runtime communication preserved; original explicit/replication missing-exec0 and heartbeat1 restored, diagnostics checked; new setup failures1 and precedence verified.
- [x] Shared helper indirect effects and SIGCHLD distinction investigated with actual copy/apply runtime; unchanged/disabled boundaries have explicit source/runtime limits.
- [x] Independent exact native verdict, source/test commits,18 install/copy pairs,90 actual fixture hashes, all retained attempts and clean status recorded.

Both worktrees remain clean at final verification. Exclusive source/test/build ownership is released to main. This worker remains available for a later scoped correction; no further edits are pending.
