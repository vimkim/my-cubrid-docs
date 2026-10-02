# Ticket 06 — two-node replication descriptor lifecycle

Status: **verified candidate; acceptance pending one explicit user decision**. Source/tests are committed and clean. Exact final native and independent artifact verification both PASS: 1 testcase, 0 failures, 0 skips, all 1,326 detailed checks. The local missing-executable public exit correction (observed baseline 0 → candidate 1) still awaits the user's explicit decision. Do not mark this ticket complete or accepted until that contract exception is resolved. Source/test/build ownership is released to main; this worker remains available for a later scoped correction.

## Identity and boundaries

Engine worktree `/home/vimkim/gh/cb/CBRD-27443-fd-clean`, branch `CBRD-27443-fd-clean`, dispatch `8aa8fcab689088b3cd24ad6e44e567e3915eae7e`, candidate `41ac0c2ce39590349e8e5759dc376f88e1cb660b`.

Test worktree `/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean`, branch `tc/CBRD-27443-fd-clean`, dispatch `992b4076c3a8d8f8e2ee1aee7495ed8fe562b004`, candidate `8c1a1bc791e5e29174fd5f6e78d98d6cec02f7bb`.

| Boundary | Policy and verification |
|---|---|
| `us_hb_copylogdb_start` and `us_hb_applylogdb_start`, local calls | Replace only these asynchronous `proc_execute` calls with explicit null stdin, dedicated console producer pipes and unrelated-FD closure. Existing local liveness/PID checks remain in their three outer owners. All local output forms are exercised while real producers live. |
| `us_hb_process_start` | Own one batch across initial copy+apply launch, pump every stream fairly during the original `HB_START_WAITING_TIME_IN_SECS`, then finish all relay barriers and release channels on every return path. Existing server registration and failure cleanup remain. |
| `us_hb_process_copylogdb` / `us_hb_process_applylogdb` | Same batch lifecycle for explicit local starts. Remote branches keep synchronous commdb requests and original registration check/sleep. `heartbeat replication start` calls these wrappers, so it inherits the local policy rather than the old generic asynchronous helper. |
| Remote `-h nodeb` → `cub_commdb -t/-h` → `hb_start_util_process` | Actual sender nodea and recipient master nodeb are distinct. Already-fixed ticket05 launch uses recipient paths and bounded server-console output; no new exec FD contract. Actual remote copy/apply and subsequent replicated rows qualify this shared policy. |
| `hb_resource_job_proc_start` | Actual copy and apply are killed separately and replaced by the recipient master; each replacement has a new PID, no master internal targets, and a subsequent exact source row arrives at the target. The other producer stays alive. Original HA recovery/registration timers are unchanged. |
| `background_process_wait` | Optional bounded framing only for multi-producer HA batches; up to 8 KiB per stream/producer. Emit complete short lines, flush long newline-free fragments at the fixed bound, and flush trailing partial text at EOF. Other existing callsites retain their unframed behavior. |
| Parent/producer reaping | Local generic async launches already reset producer SIGCHLD to DEFAULT. New local helper preserves that policy. Master-managed/restarted producers changed from inherited IGN to DEFAULT in05; actual copy/apply runtime uses heartbeat and log-processing pthreads, with no fork/exec/wait dependency in inspected utility/log paths. Actual live producer status verifies DEFAULT and multiple threads. CLI synchronous registration queries may reset parent SIGCHLD to DEFAULT, so batch pumping reaps only its known producer/relay PIDs with nonblocking waitpid; parent ownership remains explicit. |
| Unused helper | `us_hb_utils_start` under `ENABLE_UNUSED_FUNCTION` has only declaration and definition, no source callers; its local dynamic-array contract now holds batch records. No runtime claim for this disabled path. |

Generic `proc_execute`, unrelated synchronous commands, broker/CAS/proxy paths and public registration protocol remain unchanged. Executable paths are asserted below the existing 128-byte field limit separately for cub_server and cub_admin on both nodes.

## Isolation and observable behavior

Each node has its own CUBRID root, config, registry, database volumes, error/console logs, copy log directory, network, UTS and mount namespaces. Private hostnames nodea/nodeb resolve through node-specific mounted hosts files to a veth pair 10.44.0.1/24 and10.44.0.2/24. Both use TCP35443 and heartbeat35444 inside distinct private networks. `/tmp` is bound separately to each node's retained private runtime directory; the logical `/tmp/repl` path in remote arguments resolves to the receiver's own retained log tree. An outer private user/PID/network/mount namespace and PID1 reaper contain every process. A private device tree retains real null/zero/random/urandom devices and has no host syslog socket. No host/shared service, network, hostname or hosts file was changed.

Independently created empty databases follow the manual quick-start. Source-only CREATE TABLE and exact INSERT rows must appear on the standby, rather than treating process presence as replication. `csql ... fdtest@localhost` in the nodeb network targets nodeb: `boot_cl.c` explicit-host parsing around578–603 supplies only that host, and its CSQL branch around807 bypasses preferred-host/capability retry routing; the registry peer list cannot silently redirect this verification to nodea. The matrix records each row's exact id/marker, both live producer identities, before/after restart PIDs, caller stream EOF times independently from launch exit, flock availability, actual FD targets and final empty cleanup. FD4096 really duplicates the caller pipe before softlimit1024. All namespace processes, including unknown names and confirmed zombies, remain visible to the scanner.

## Retained attempts

All paths below are under `/home/vimkim/.cache/`.

- `cbrd27443-06-red`: fixture setup failed because the second root copy already included empty db/repl directories; no product verdict.
- `cbrd27443-06-red2`: fixture waited for active before starting the other peer; source remained to-be-active. Corrected ordering starts both peers first; no product failure claim.
- `cbrd27443-06-red3`: exact installed8aa baseline,37 checks, actual row1 replicated. Both heartbeat commands return0 but their two actual copy/apply descendants retain caller pipe/lock/general resources. Final cleanup empty. Baseline script and10 object hashes retained.
- `cbrd27443-06-red4`: exact copied8aa baseline from accepted05 native install,77 checks. Actual two-node row1, unlisted DB public1/original message, remote missing-exec public1. Local missing-exec public0 plus contradictory success/fail lines and `execv: No such file or directory`; failed child returns into utility control flow. Concurrent short failure producers deliver exactly2000 intact diagnostic lines per producer/stream and heartbeat1. Scratch baseline fixture retained separately.
- `cbrd27443-06-green1`: candidate c1cd actual rows1/2/3 and distinct automatic restarts passed before deliberate interruption. Added private `/dev` before proceeding to log-fault testing; no log fault was exercised in this earlier run. Incomplete, not PASS.
- `cbrd27443-06-green2`: candidate c1cd passes actual rows1–11, both automatic restarts, local modes, remote launches, exec and console-fault recovery, then NOK at the concurrent short-message test. All430000 bytes per stream were present, but 8192-byte read boundaries spliced some short diagnostic lines. This was a real new readability regression, not allowed unordered output. Exact original line assertions retained; bounded framing fixes it.
- `cbrd27443-06-green3`: focused installed09a framing verification PASS80. Both real nodes and row1 work with peer registry configuration. Short batch has2000 intact lines for copy/apply on both streams; separate long batch has20000 newline-free payload bytes and one unterminated tail per producer/stream. Both failure launches return1 with EOF/locks released, no zombies, and final namespace empty. Source41 is formatting-only after09a; this probe does not substitute for final exact41 native verification.

## Public failure distinction

Unlisted DB1 and its existing diagnostic, remote exec failure1, and genuine late producer failure1 are preserved. Console-setup failure1 with an explicit caller diagnostic is a newly introduced checked failure condition. Local missing executable currently changes observed baseline false-success0 to checked1 while keeping the errno diagnostic. The explicit user decision for that public-code exception is pending; do not describe it as preservation.

## Build/native and final acceptance

Normal hooks ran; formatter rewrites were inspected and staged, with no bypass. Configured/built debug_gcc after source commits through the live just interface. `UNIT_TESTS=OFF`; no CTest claim. Known generated `cubrid-cci/win/cci_version.h` is inspected/restored. Final exact native verdict, ten-object installed/copied and per-node identities, clean statuses, and checkbox assessment are recorded below.

No rebase/merge/default-branch modification, push, PR, external CI, JIRA mutation, GUI or nested agent. Main alone owns documentation/tracker. Linux focused verification does not establish Windows/non-Linux execution or whole-corpus qualification. Ticket07 owns broker/CAS/proxy; ticket08 owns final all-service integration.

## Candidate exact native run — PASS

Attempt `/home/vimkim/.cache/cbrd27443-06-41ac0c2.FvYAKF` started with source41ac0c2ce/test8c1a1bc79, both clean. Preflight proves installed41ac0c2, `commit_match=yes`, no mismatch exception, native testkit SHA256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`, and available containment. The effective config uses full shell corpus read-only, scenario_disk=on, one slot, no retry/update/continuation, file feedback, timeout1200 seconds. Exactly one tracked case is selected: `shell/_01_utility/cbrd_27443/cases/cbrd_27443.sh`.

Final configure/build logs: `.cache/cbrd27443-06-configure3.log`, `.cache/cbrd27443-06-build3.log`; final explicit no-DB initialization: `.cache/cbrd27443-06-init3.log`. Commands were `direnv exec . just configure`, `direnv exec . just build`, then `cub-workenv init --worktree /home/vimkim/gh/cb/CBRD-27443-fd-clean --install /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc --preset debug_gcc --no-db`. Native invocation: `direnv exec . bash /home/vimkim/.cache/cbrd27443-run-native.sh 06-41ac0c2 /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc`.

All ten installed/copied hashes already match in `copied-binary-identity.json` (the prior nine plus actual replication launcher cub_admin). `clean-worktrees.json` records paths, exact branches/commits and empty status. Source/test patches retained in the attempt are empty. Final per-node hashes are recorded by the replication matrix before fault renames.

Additional retained comparison: `/home/vimkim/.cache/cbrd27443-06-diagnostic-comparison.json` distinguishes exact byte inventories from complete lines. Baseline and framed candidate both have 2,000 complete lines per producer/stream; the intermediate unframed candidate had430000 bytes but fewer intact lines. The final regression keeps complete-line assertions, and the separate long/tail batch avoids treating long unbroken fragments as short-line promises.

Both actual final native nodes match all ten copied/installed objects, independently recorded in `two-node-binary-identity.json`. Registered paths are94/93 bytes for nodea cub_server/cub_admin and91/90 for nodeb. These remain below 128 without changing the protocol.

## Final evidence

Final attempt `/home/vimkim/.cache/cbrd27443-06-41ac0c2.FvYAKF`; native result directory `CTP/result/shell/current_runtime_logs`. Native runner exit0 is recorded separately in `exit.status`. Both `verdict.json` and a separate invocation recorded in `independent-verdict.txt` prove exactly 1 selected/dispatched/finished successful case,0 failures / 0 skips; `test_status.data` agrees. All 8 shell subchecks pass. Detailed matrices:121 server +216 master +76 restart +383 boundary +96 rotation +152 HA +282 replication =1,326. Dynamic process observations explain count differences from05; assertions were not weakened.

Replication matrix: `home/.cache/fd-repl.P7kyph/matrix.json`. All 44 capture commands exit, receive every captured EOF, release their caller flock, and retain no caller FD target. Both initial commands return0 while real copy/apply processes remain alive. Nodea exits at13.1721s, stdout/stderr EOF at13.1720/13.1721s; nodeb exits at13.1555s with EOF at13.1553/13.1554s. These are observations, not new product deadlines.

Actual master-managed copy restart: PID569→585; apply restart: PID573→595. Recipient master remains PID309. Both actual master-target intersection sets are empty; the other producer survives each distinct restart and the old PID is reaped. Remote copy/apply launches produce PID746/760 on the recipient node under the same master309, with empty internal-FD intersections. Live post-replication snapshots exclude every prior caller pipe, lock, general file and uncaptured output file; actual stdin is null, SIGCHLD is DEFAULT, runtime worker threads remain alive, and there are no zombies.

Records are exact `(id, marker)` rows:1/`replicated_1` after initial launch;2 after copy restart;3 after apply restart;4–8 after stdout/stderr/merged/cat/rg local restart cycles;9 after remote copy start;10 after remote apply start;11 after exec/console-fault recovery. Table creation and insertion occur only on nodea; the query uses explicit localhost in nodeb's isolated network. Each observation's complete SQL data rows are retained, avoiding column-heading or process-presence false positives.

Unlisted-DB and missing-executable diagnostics are recorded for both tools. Remote missing-executable failure remains1. Local missing-executable returns the proposed checked1 with the original `execv: No such file or directory` text; acceptance of the old false-success0→1 correction is pending. Newly checked console-open failure returns1 with a visible caller diagnostic despite the unusable console file; both tools recover after executable/log restoration, and row11 replicates. Before/after PID sets are identical after failed local/remote exec and console setup, proving no stray failed producers/relays. The failed late batch keeps its original failure1 and each of the8,000 complete short diagnostic lines (2 tools ×2 streams ×2,000). The separate long batch preserves all 80,000 newline-free payload bytes and4 unterminated tails, returns1 with EOF, and leaves no zombies. Both private node keepers and all descendants are absent at final cleanup.

`safe-summary.json` contains compact verdicts, row evidence, first-launch timings, restart/remote identities, cleanup sets and topology. `copied-binary-identity.json`, `two-node-binary-identity.json`, and `clean-worktrees.json` independently bind actual files to exact committed source/tests. Do not bulk-share raw CTP environment logs.

## Seven acceptance checkboxes

- [x] Investigated and handled initial local copy/apply, real remote master-managed creation and every automatic restart boundary using05 contracts.
- [x] Identified two isolated node configs, database volumes, error/console/copy logs, namespaces and peer communication without host/shared-service changes.
- [x] Every tested start request has caller EOF/lock/FD release while required real replication processes remain alive; high duplicate FD and internal master targets are checked.
- [x] Exact source changes reach the independent target initially, after separate copy restart, after separate apply restart, after local capture cycles, after remote launches and after failure recovery.
- [ ] Runtime communication and existing genuine producer/unlisted/remote failure contracts are verified, but final acceptance of the observed local missing-executable public false-success0→checked1 correction awaits the user's explicit decision. The original errno diagnostic is preserved. This is the only pending acceptance issue.
- [x] Indirect shared-helper effects, explicit producer/parent SIGCHLD behavior, runtime socket/thread creation and disabled/no-caller helper are documented and backed by full native regression evidence within Linux scope.
- [x] Independent native artifact verdict and exact source/test/build/copied/per-node identities are retained. The exercised local creation, remote master creation and per-utility automatic restart boundaries use real two-node progress; single-node HA and process presence do not substitute for replication evidence. The disabled unused helper remains explicitly unexecuted.

## Installed, copied and actual-node identity

Every value below matches installation, native copied install, actual nodea root and actual nodeb root. This includes the requested nine objects plus the actual replication launcher cub_admin.

| Object | SHA256 |
|---|---|
| `bin/cubrid` | `9370d6fc4457873153708db87a8abb7f50e47d9b81456d84554a3112a5066dae` |
| `bin/cub_server` | `2b104bb22f837905f9850d2dc4f1ba582e3e5cbb482ece2163d40618042bc41d` |
| `bin/cub_master` | `56fa8d2a4a3bf97bcbd08e2beec435cb3eadb24f01ec82f9420aee2207336565` |
| `bin/cub_pl` | `00d548ac08f0134d5dde859d7cb55286095605bccde145e10c1c0cdbf38a8642` |
| `bin/cub_console` | `5fa80b518c6da4f33c20a690989b8ca04493f52f78ef94e5ae913c41c0feb019` |
| `bin/csql` | `2c49e27dee82eaeed0202f963af4f5a64b0af8d3ae6eebb46db68464ec2fa6d0` |
| `bin/cub_admin` | `ec3fee4773793b379f0d9ef482fce3b22dfbc705b4261ef0e9eb55c622453186` |
| `lib/libcubrid.so` | `47f7a3ca141aa98dc83ce5439bf281484bcff7a29db2859865b6bc2f29afeb33` |
| `lib/libcubridsa.so` | `24140f62655a9fbaa4c52262d19f17e63e605bb02204ec99a6914e8274e43b3c` |
| `lib/libcubridcs.so` | `7972b27285f7426c26a217c6d37d9d8c9c69e9311cdb019a35943ffacf7b4e39` |

## Clean handoff and limits

Final source/test `git diff --check` against dispatch passes; both `git status --short` outputs are empty. Native preflight/source patches confirm exact committed identity. No pending source/test changes remain, and ownership is released to main for review/independent07. Ticket06 remains a verified candidate awaiting the one public-code decision; any subsequent code correction should return to this worker under a new explicit ownership handoff.

No Windows/non-Linux runtime, CTest (disabled), whole-corpus QA, broker/CAS/proxy or full all-service acceptance is claimed. Existing portable hard-limit FD fallback remains previously reviewed-only; Linux paths are exercised by the inherited full suite. Existing HA timers, registration criteria and exec-path field size are unchanged. Very long diagnostic lines exceeding8 KiB may be chunked, while short lines and EOF tails are preserved; runtime console retention/failure behavior remains the bounded04 policy. Ticket07 owns broker/CAS/proxy; ticket08 owns final combined-service acceptance.
