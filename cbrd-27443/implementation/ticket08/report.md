# CBRD-27443 ticket08: final integrated Linux verification

The final focused Linux integration passed: exactly four native cases, four successes, zero failures and zero skips in 1,189 seconds. All 2,566 matrix checks and nine supplemental assertions pass at one committed source/test/install state. The named platform and configuration gaps below remain unverified; this is not universal specification or whole-QA completion.

## Final state and scope

Engine `/home/vimkim/gh/cb/CBRD-27443-fd-clean`, branch `CBRD-27443-fd-clean`, commit `0809a480df55ac6767a905d03fa3d31edd40a93c`. Tests `/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean`, branch `tc/CBRD-27443-fd-clean`, commit `6bdbb89738088948c479a6d85662276126a31bb5`. Test commit 6bdbb897 passed the normal hooks without bypass. This worker changed tests only after accepting the original ticket07 worker's scaling correction. No engine edits or rebuild were needed after the exact 0809 configure/build/install. The actual installed and native-copy version is `11.5.0.2659-0809a48` (Debug Linux).

Final native attempt: `/home/vimkim/.cache/cbrd27443-08.QVVajj`. Its `engine-commit.txt`, `testcase-commit.txt`, empty patches, `preflight.json`, `runtime.txt`, `command.sh`, `conf/shell.conf`, `expected-cases.txt`, `run.log`, `exit.status`, `verdict.json`, native CTP artifacts and detailed fixture JSON bind the result to one committed source/test/install state. Earlier green matrices are historical evidence, not added to this verdict.

The four native cases are broker/cases/broker.sh, cases/cbrd_27443.sh, ha/cases/ha.sh and logging/cases/logging.sh under shell/_01_utility/cbrd_27443. Splitting logical matrices preserves every prior scenario and the existing 1,200-second per-case policy. The complete shell corpus is the read-only scenario root; scenario_disk provides the sibling shared helpers. Exactly these four cases, one slot, no retries, updates or continuation, and no unrelated macro skips are required by the verifier.

## Exact final verdict and detailed evidence

Native runner exit is 0; native artifact verification passed twice, and main independently reran it. `verdict.json` and `independent-verdict.txt` are key/value verifier outputs despite the first filename extension. `test_status.data`, XML, feedback, dispatch and run-log identities agree on four expected cases with no failures or skips. Feedback records 13 positive shell assertions (4 broker, 5 base, 2 HA, 2 logging).

| Native case | Seconds | Verdict |
|---|---:|---|
| broker | 140.451 | PASS |
| base lifecycle | 389.749 | PASS |
| HA/replication | 569.315 | PASS |
| logging interactions | 88.382 | PASS |

The longest case remains below 570 seconds, within the unchanged 1,200-second per-case limit. The full run took 1,189 seconds.

The 180 matrix captures comprise 179 background captures with independent captured-stream EOF, no caller holders and lock release before stopping services, plus one intentional PID1-supervised foreground master. For master-matrix capture23, the sole holder is the PID in actual init-master.pid, and only its supervisor stdout/stderr pipe targets remain; its general caller file and lock are released. The fixture explicitly checks its foreground contract and later cleanup. The original present probe separately confirms both EOF, lock availability with live server/PL and final cleanup. Launcher result and collector result remain separate fields, including original failure codes.

The worker audit is preserved as `worker-audit.py`; outputs `all-assertions.json` and `safe-summary.json` preserve every passing check, exact report paths, actual file hashes, foreground exception, faults and rows. Main independent audit also passed; its separate result is `main-independent-audit.json` in this same attempt, confirming 2,566 assertions, 179 background captures plus the explicit foreground exception, the present probe, 12 fresh live faults, 15 replicated rows, 18 installed/copy pairs and all 252 actual files. Detailed final matrices:

| Matrix | Checks | Captures | Evidence (under final attempt/home/.cache) |
|---|---:|---:|---|
| b-broker | 301 | 22 | fd-b-broker.dCxDON/matrix.json |
| b-failure | 117 | 12 | fd-b-failure.A7ji11/matrix.json |
| b-recovery | 77 | 2 | fd-b-recovery.DqW9XS/matrix.json |
| b-rot | 383 | 6 | fd-b-rot.zaxbly/matrix.json |
| b-scaling | 147 | 7 | fd-b-scaling.F98c2y/matrix.json |
| boundary-matrix | 386 | 14 | fd-boundary-matrix.UZv5Gh/matrix.json |
| ha | 195 | 19 | fd-ha.x9Kb5u/matrix.json |
| master-matrix | 216 | 25 | fd-master-matrix.4L0BsF/matrix.json |
| matrix | 121 | 14 | fd-matrix.td1NwT/matrix.json |
| repl | 401 | 49 | fd-repl.H0FJSY/matrix.json |
| restart-matrix | 74 | 1 | fd-restart-matrix.KpdbvF/matrix.json |
| rot | 148 | 9 | fd-rot.Jekgv0/matrix.json |

All 12 matrices terminate in strict cleanup assertions; master cleanup is a list of ten empty snapshots, while broker cleanup records one empty process list. Broker private IPC identities differ from the host and no SHM remains. The nine supplemental assertions independently confirm five internal restarts retain only dedicated parent stdio and four exact 4,000-line stdout/stderr sets survive.

Final scaling samples show maximum launcher FD counts 21 for ordinary 32-CAS and two-broker 64-CAS at hard=soft 128, and 33 for SHARD 32-CAS at hard=soft 1024. This is the actual final sample, not the earlier focused SHARD maximum of 32. Exact 4,096-line current-attempt streams, late producer output and rollback remain passing assertions.

## Binary identity

The primary SHA256 identities are:

| Object | SHA256 |
|---|---|
| bin/cubrid | ffd6b5ee7eb6766fa60872a1952f6a277d0676f6e5b2a898c7ab0d9330f0bc60 |
| bin/cub_server | 3cf219a5ad7a25a8f5765745973fe2c70b16e5b4a5348a000d9489754e20554e |
| bin/cub_master | f2f1ea24b379d75bd42db3a2b806c108c77c5a3d9e28fee21b3aed8d42054785 |
| bin/cub_pl | 2e6cddcac8ca3db3e49e90299fb9eda21b786a12909c7f1c703cbaf82c8a39d0 |
| bin/cub_console | 3a937c52b07586bbbef0ed32803202ff9b8931d900e38291d47cf0d8018ef39d |

Final safe-summary.json records matching hashes for all 18 installed/native-copy executable/library pairs and all 252 independently rehashed restored actual fixture objects across 12 matrices, the second replication peer and the original present probe. The actual native version includes `(64bit debug build for Linux) (Oct 3 2026 02:49:16)`.

## Changes and observed contracts

The persistent tests combine bounded console rotation with real initial startup, ordinary server and PL-only restart, single-node HA restart, two-node copy/apply restart, and ordinary/SHARD broker/CAS/proxy startup and internal restart. Volume wrappers emit 640 1,024-byte records per stream and then exec the actual unchanged image. Actual producer PIDs are recorded separately, including multiple CAS; SQL, PL, CCI prepare/execute/fetch and replicated rows prove the real service continued. HA cub_admin restores the original basename argv[0] so registration and subsequent stop/start identity remain unchanged.

Each relevant log remains at most 1 MiB active plus three 1 MiB archives, private 0600; prior-tail assertions select data still within that retention window. Runtime snapshots reject deleted console descriptors. Twelve active logging faults replace a live console pathname with a directory, force producer output exceeding pipe capacity, require a fresh timestamped 256-byte operation=open failure record, and perform real SQL/PL, CCI or replication while the fault remains. The same services and relays survive; restored destinations accept a recovery marker and subsequent operations. Old failure records intentionally persist after successful logging. Failed bytes are drained/discarded and later logging recovers; lossless delivery during storage failure is not claimed.

Ordinary initial missing-CAS failure rotates the current attempt's nearly-full log, proven by inode change, and still returns legacy 0 with original diagnostic and independent EOF/lock evidence. SHARD missing-CAS remains 1. Successful initial launches require all planned volume. Early failed SHARD startup can finish its finite diagnostic boundary before other producers emit every planned record; that observation is retained explicitly, without adding a readiness wait. Current-attempt failure messages remain distinct from older logs.

The accepted 07 engine correction shares at most three relay destinations per broker invocation, independent of initial child count. Real 32-CAS and two-broker 64-CAS startup succeeds at hard=soft 128; valid SHARD 32 uses 1,024 because its existing configuration requires a higher limit. Verbose current-attempt output, late first-CAS diagnostics across a later broker, existing readiness boundaries, failure rollback and clean IPC are retained. Local missing copy/apply/replication exec and ordinary missing CAS still expose historical public 0; public heartbeat-start failure remains 1. The earlier raw managed cub_commdb missing-exec correction 0→255 remains explicitly distinct from those public interfaces.

## Nine ticket checklist results

- [x] 1. Final exact source/test/native identity and every predecessor matrix verified in one four-case native run.
- [x] 2. A01–A16 mapped to final evidence below; named source-only/unverified boundaries are not counted as runtime passes.
- [x] 3. Independent launcher/collector codes, captured stdout/stderr EOF and caller-lock release before stop verified; real SQL/PL while alive; master-present/absent/failure included. Intentional foreground exception is separately verified.
- [x] 4. Combined rotation/startup/restart/HA/broker/failure and live logging fault/recovery observed in the final run.
- [x] 5. Direct server, synchronous management and daemon master behavior verified; dedicated exec stdio and later real SCM_RIGHTS communication retained.
- [x] 6. Exact project build/configuration and native focused artifacts verified. Linux result is separate from Windows/non-Linux gaps and disabled unit tests.
- [x] 7. Worker self-review complete; confirmed scaling defect routed to the original ticket07 worker and corrected; main owns separate Standards+Spec review under approved no-subagent adaptation.
- [x] 8. Baseline, corrected result, fixture failures and unverified paths distinguished below; no whole-platform or whole-QA claim.
- [x] 9. Meaningful engine/test changes committed; both worktrees clean at final audit. Main archives documentation/evidence and controls tracker; no parent-issue edit by worker.

## A01–A16 final-state map

In this table OBSERVED denotes the final native verdict and the named matrix's passing assertions. Paths resolve through final-attempt safe-summary.json and all-assertions.json, with raw records at home/.cache/fd-<mode>.<id>/matrix.json. Supplemental assertions are recorded separately rather than inflated into native testcase counts.

| Acceptance | Final Linux evidence | Scope/status |
|---|---|---|
| A01 master absent | master-matrix successful CLI start, separate EOF/lock, server/PL and SQL | OBSERVED |
| A02 master present | matrix and present probe, all capture forms, functional SQL/PL | OBSERVED |
| A03 collectors | matrix/master-matrix/ha/repl/broker matrices: stdout only, stderr only, separate, merged, cat and rg; collector and launcher codes recorded independently | OBSERVED |
| A04 missing DB/start failure | matrix/master-matrix current diagnostic, original code, both EOF; surviving master has no caller FD | OBSERVED |
| A05 master/exec/log failure | master-matrix original master wait/failure, missing producer/relay, invalid log/FIFO, failed children/FD cleanup; rotation/broker failure matrices add setup and rollback cases | OBSERVED |
| A06 inherited descriptors | capture FD 57 duplicate writer, ordinary caller file and flock, runtime process/relay snapshots, lock reacquired before service stop | OBSERVED |
| A07 ordinary automatic restart | restart-matrix plus rot: real restarted server/PL registration, SQL/PL, explicit stdio/internal-FD audit and restart rotation | OBSERVED |
| A08 PL-only/SA | restart-matrix SA and closed-stdio paths; rot PL-only restart emits actual producer volume then executes real PL and SQL | OBSERVED |
| A09 logging lifecycle | rot initial/concurrent/ordinary/PL; ha and repl actual initial/restart; b-rot ordinary/SHARD initial/internal restart. Bounded retention, private mode, existing error logs, no deleted FD and twelve live fault/recovery operations | OBSERVED |
| A10 current failure diagnostics | matrix isolation from old/other DB; rot concurrent successful/failing startup during rotation; b-rot initial failure inode proof, exact existing diagnosis and old-log exclusion | OBSERVED |
| A11 direct/synchronous | matrix/restart-matrix/master-matrix direct cub_server, SA/CUBRID_NO_DAEMON, synchronous management stdout/stderr redirection and codes | OBSERVED |
| A12 daemon master | master-matrix actual daemon/alternate image, EOF/lock and dedicated stdio; intended foreground/PID1 behavior remains explicitly attached | OBSERVED |
| A13 descriptor boundary | boundary-matrix FD 65535 above lowered soft 256, closed 0/1/2 and forced close_range ENOSYS→raw Linux getdents64; b-scaling hard=soft 128 startup | OBSERVED on Linux; portable fallback source-only |
| A14 single-node HA | ha actual transitions/restart/heartbeat stop, SQL/PL, volume during initial/restart and live logging fault; explicit PID/reaping snapshots | OBSERVED |
| A15 two-node replication | repl real copy/apply local/remote starts, automatic restart, initial/restart volume and row progression 1–15 including live faults; both node identities and cleanup | OBSERVED |
| A16 broker/CAS/proxy | b-broker/b-failure/b-recovery/b-scaling/b-rot: actual ordinary/SHARD CCI SQL, required stdio and SCM_RIGHTS, initial/internal restart, failure contracts, scaling and rotation/live faults | OBSERVED in ordinary/SHARD scope; gateway unverified |

## Baseline, review findings and preserved attempts

Original user-approved baseline 15e7dc8 reproduces launcher 0 while both EOF remain absent and a caller flock stays held. Authoritative baseline evidence is archived under docs implementation/baseline-15e7dc8b5; ticket01 records its native red and subsequent correction. Per-ticket reports preserve other earlier red/fixed experiments. These are not final-state passes.

Ticket08 first confirmed an additional 07 scaling regression: immutable pre07 41ac starts 32 CAS at soft 128 with real CCI SQL, while b0 fails with EMFILE and only succeeds after soft 256. Both clean up. Detailed comparison, exact invocations, 36 actual identity triples and initial release remain in `/home/vimkim/.cache/cbrd27443-ticket08-scaling-checkpoint.md` and `/home/vimkim/.cache/cbrd27443-08-scaling/`. The original ticket07 worker corrected this at 0809; its focused evidence and main independent audit remain in `/home/vimkim/.cache/cbrd27443-07s-0809a480/`. Final native b-scaling requalifies the correction with the rest of the suite.

Retained ticket08 fixture iterations (all under /home/vimkim/.cache) are not hidden or counted as product passes:

- cbrd27443-08-rot1: SQL attempted before existing server registration after restart; added existing status gate.
- cbrd27443-08-rot2: wrapper emitted on cub_pl management ping/stop, corrupting its output; restrict volume to actual DB producer invocation. rot3 passed 148 checks.
- cbrd27443-08-br1: one marker per role was overwritten by second CAS; now per-PID evidence, preserving legitimate two-CAS config.
- cbrd27443-08-br2: expected full planned volume after early SHARD failure; observed partial producer output with correct diagnosis/EOF. Successful volume remains exact; failure asserts current-attempt rotation/diagnosis without inventing a readiness wait. br3 passed 383 checks.
- cbrd27443-08-repl1: shebang changed cub_admin argv[0] to absolute script path, breaking later HA exact stop/start identity. Restore original cub_admin argv[0], retain management CLI assertions. repl2 passed 401 checks and 15 real rows.
- cbrd27443-08-ha1 passed 195 checks. Strengthened present probe passed with all namespace processes, including unknown names and relays, included in cleanup.

Main's read-only review caught stale failure-record acceptance: successful logging preserves old records, so checking only operation=open could falsely pass. The final helper compares before/after mtime_ns and records both versions without clearing the old record. Main reviewed final broker interactions and README without another confirmed finding. The aggregate engine diff check from approved base 15e7dc8 and the ticket08 test commit-range diff check pass. The aggregate testcase diff check from dfb7da195 reports `shell/_01_utility/cbrd_27443/cases/cli_fixture.py:163: new blank line at EOF`, introduced by earlier commit 4a201c38cf. Main accepted this as a minor pre-existing style note and directed preserving the committed native state; a clean full-range testcase diff check is not claimed. No engine defect emerged from the added interactions; Main reported no remaining source/test review finding; final integration acceptance remains with main.

## Build, containment and limits

Project debug_gcc CMake configure/build/install for 0809 succeeded in the original ticket07 worker; retained internal logs `/home/vimkim/.cache/cbrd27443-07s-configure.log`, `cbrd27443-07s-build.log`, `cbrd27443-07s-init.log` record live recipe provenance. Final preflight confirms matching source/install and no exception. UNIT_TESTS=OFF; no CTest/unit-test pass is claimed. The actual cache is `build_preset_debug_gcc/CMakeCache.txt`, with `UNIT_TESTS:BOOL=OFF`. Native `testkit shell -c <effective config>` and the focused artifact verifier are the organization-facing regression procedure. Personal direnv/just and launcher invocations remain in internal logs/command.sh. Installed testkit SHA256 is 31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a; no installation or update was performed.

All fixture instances use private user/mount/net/PID/IPC namespaces, PID1 reaping, private devices/syslog isolation and private install/DB/tmp/registry. Cleanup checks include unknown namespace process names; broker matrices also require no remaining private SysV SHM. No shared host service, network, hosts or syslog was modified/stopped. No external CI, publication, merge/rebase, JIRA write or nested agent occurred.

Windows/non-Linux build and runtime remain unverified. Linux close_range and forced raw /proc fallback are observed; the non-Linux hard-limit loop is source-only and assumes no open FD remains above a subsequently lowered hard limit. The final high-FD experiment lowers soft, not hard, so it is not claimed as a runtime test of the latter. External ODBC/CAS_CGW gateway backend is unconfigured and functionally unverified despite shared code compiling. Legacy non-CAS admin restart is source-reviewed/configuration-unreachable (accepted CAS/CAS_CGW types take the earlier branch); shard_admin_pub.c raw forks are under UNDEFINED and not live boundaries. Shared helper effects on these paths were included in prior source reviews, not inferred from nearby ordinary/SHARD success. No whole-spec across every supported platform/configuration, whole-corpus QA or external CI completion is claimed. Ordinary disk operation errors are covered; indefinitely stalled filesystem operations are not bounded by a new product SLA.

Internal exact final invocation from the engine worktree:

```sh
direnv exec . env CTP_HOME=/home/vimkim/gh/ctp/run-sql/CTP bash /home/vimkim/.cache/cbrd27443-08-run-native.sh 08 /home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc > /home/vimkim/.cache/cbrd27443-08-native-launch.log 2>&1
```

## Final release

Both engine and testcase worktrees are clean at the exact commits identified above. All final fixture namespaces and descendants were reaped; all broker private shared-memory segments were removed. Engine/test/build ownership is explicitly RELEASED cleanly to main. No further worker source/test/build task remains. Main owns documentation archival, tracker status and final Standards+Spec acceptance. This release does not authorize publication or merging.

## Main acceptance and durable archive

Main accepted ticket 08 after independently verifying the native artifact verdict, every matrix, the foreground contract exception, all 252 fixture hashes and nine supplemental observations. All eight implementation tickets are resolved within the named Linux scope. See the [combined Standards/Spec review](../final-review.md), [durable evidence index](evidence/README.md), [independent audit](evidence/main-independent-audit.json), and [complete assertions](evidence/all-assertions.json). Earlier unsuccessful attempts remain identified above and in the orchestration record. Local integration requires the user's separate confirmation and a clean destination; publication remains a separate action.
