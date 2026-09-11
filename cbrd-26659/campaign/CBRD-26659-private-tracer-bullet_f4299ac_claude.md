# CBRD-26659 — Private tracer bullet: worktree and first shell case end to end (ticket 14)

> Observed: 2026-09-11 (KST). Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` (ticket 11); normative context `f6543de` + sha256 `c9daf3c4…`; requirement catalogue sha256 `0cc33c82…` (ticket 12).
> Author: Claude Opus 5 (1M context), for the [Adversarial OOS testcase campaign](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/spec.md) ticket 14.
> Revision 6, after both axes of a two-axis review and three confirmation passes; §8 lists what the reviews changed and everything was re-run.
> Records: [`evidence/ticket14/`](evidence/ticket14/) — the oracle and its derivation, the isolation demonstration and its live counterpart, two manifests, two attempt records, two replay-bundle indexes, four matrix rows, two checker validations, the format probes, and the per-attempt evidence.

Vocabulary follows the [docs glossary](../../CONTEXT.md). This is the private suite's runner smoke check; all ten private case tickets (23 to 32) were blocked on it.

## 1. What exists now

| | |
|---|---|
| Private worktree | `/home/vimkim/gh/tc/cubrid-testcases-private-ex-cbrd-26659`, branch `CBRD-26659-oos-testcases-handover` |
| Base | `origin/develop` = `e9c2d86874b9c08cdd72b120c2ead84f525e15fc`, verified with `git ls-remote` **and** `git fetch` returning the same object before the worktree was created |
| Testcase commit | `c3d1e71466f93c8a4bc3ef7e0d3ee904f78b3122`, local only. Nothing pushed, no pull request |
| Case | `shell/_06_issues/_26_2h/cbrd_26659_oos_dur01/cases/cbrd_26659_oos_dur01.sh`, covering `OOS-DUR-01` and `OOS-REP-07` |
| Checker validation | `…/cbrd_26659_oos_dur01/cases/make_negative_control.sh` (a helper, never discovered as a case) |
| Untouched | The canonical clone `/home/vimkim/cubrid-testcases-private-ex` is still on `develop` at `6eb3b19ba`; the three existing private worktrees (`tc/pr-6864`, `CBRD-27403-oos-error-code-answers`, `CBRD-27398-pgbuf-inspector-fixtures`) and their uncommitted changes were not read or written |

The issue bucket `_26_2h` follows the repository's convention (year and half); the campaign key is in the case directory name so the case is findable by ticket.

## 2. Isolation, done before anything ran

This was the ticket's first criterion and the one that could damage unrelated work. The CTP shell helpers clean up without scope:

| Helper | What it does |
|---|---|
| `init`, `finish` | `cubrid service stop`, then **`pkill cub`** — a name match over every process this UNIX user owns |
| `release_broker_sharedmemory` (in `finish`) | `ipcs \| grep $USER` then **`ipcrm -m`** on every segment it finds |
| `xkill <pattern>` | `ps -u $USER` then `kill -9` |

**Method: a user namespace owning a private PID namespace and a private System V IPC namespace.** Every invocation runs as

```
unshare --user --map-current-user --pid --fork --mount-proc --ipc -- ctp.sh shell -c <conf>
```

`--map-current-user` keeps the uid, so `$USER`, file ownership under `/home` and `ps -u $USER` all keep their ordinary meaning inside. `--pid --fork --mount-proc` gives the invocation its own `/proc`, so processes outside it are not merely protected but **unaddressable**. `--ipc` does the same for System V segments. The wrapper is [`isolation/campaign_ns.sh`](evidence/ticket14/isolation/campaign_ns.sh).

**Demonstrated, with matched controls.** [`isolation/isolation_check.sh`](evidence/ticket14/isolation/isolation_check.sh) runs four checks as two pairs, and exits non-zero unless all four hold ([`isolation.txt`](evidence/ticket14/isolation/isolation.txt), `failures=0`):

| Check | Result |
|---|---|
| A `cub`-named process started **outside** survives `pkill cub`, the `ps`+`kill -9` sweep and a direct `kill -9` by pid, all run **inside** | passed — `/proc/<pid>` is not visible and the direct kill reports "No such process" |
| The **same sweep**, run in the namespace that owns the decoy, does kill it | passed — without this, check 1 would also pass if the sweep silently did nothing |
| A System V segment created **outside** survives the `ipcrm` sweep and a direct `ipcrm` **inside** | passed — `ipcs` lists zero rows and the direct `ipcrm` reports "invalid id" |
| The same commands, in the namespace that owns the segment, list and destroy it | passed |

No unscoped `pkill` or `ipcrm` was ever executed on the host: the two positive controls run their sweeps inside a namespace containing only their own decoy.

**And on a real neighbour, not a decoy.** Another session's CUBRID instance (`cub_master` plus `cub_server demodb`, same UNIX user) was running on this host throughout. Its master survived every invocation of this ticket — two `pkill cub` sweeps each — and every case's journal recorded `pre_existing_masters=[]`, which is what invisibility looks like from inside. See [`isolation/live-containment.txt`](evidence/ticket14/isolation/live-containment.txt). Ticket 13 had to stop such a process by hand before its run; that is no longer necessary.

**Ports are the one thing the namespace does not isolate.** An unprivileged network namespace cannot bring up loopback (`--map-current-user` grants no `CAP_NET_ADMIN`, and `lo` stays down, so CUBRID cannot connect to itself), so the campaign allocates ports instead — 26659 for the master, 33120 and 33121 for the brokers, 33122 for HA — and the runner verifies all four are free before starting. This is recorded as a residual, not as a solved problem.

**Second-order scope, inside the case itself.** The case snapshots the `cub_master` pids that already exist before it starts anything and kills only masters absent from that snapshot. So even run *without* the namespace it cannot take down someone else's master. It also refuses to proceed if it cannot extract its own `cub_server` pid, rather than "verifying" a database that was in fact shut down cleanly.

## 3. The case

`CREATE TABLE oos_dur01 (id INT, v BIT VARYING)` — ticket 11's schema A verbatim, so its boundary table applies without re-derivation.

| Row | N | Pattern | Placement | Chosen as |
|---:|---:|---|---|---|
| 1 | 4,036 | `AA` | out of row, 1 chunk | smallest N demoted under **both** accountings |
| 2 | 16,284 | `BB` | out of row, 2 chunks | smallest N needing two chunks under **both** |
| 3 | 4,011 | `CC` | inline | largest N inline under **both** |
| 4 | 4,036 | `DD` | out of row, 1 chunk | deleted and committed before the crash |

[`derive_case_sizes.py`](evidence/ticket14/derive_case_sizes.py) imports ticket 11's `oos_boundaries.py` rather than restating its arithmetic, and computes every boundary twice — once with the pinned accounting (gate `DB_PAGESIZE/4` = 4,086, 16-byte stub and chunk header) and once with the normative one (CBRD-27057 target 4,060, CBRD-26950 24-byte stub and chunk header) — taking only sizes on which the two agree. The pinned and normative demotion triggers are 4,036 and 4,012, and the chunk splits 16,284 and 16,276; taking the larger of each pair keeps every expectation outside both disputed bands. **That is what makes the placement assertable rather than merely observed**, and it is why the inline comparator is 4,011 and not ticket 11's 4,035, which is inside the disputed band.

The flow is: insert the four rows and commit; check activation; commit an UPDATE of row 1 to pattern `EE` and a DELETE of row 4; `kill -9` the server, its PL server and the master the case started; restart; verify.

Seventeen assertions, listed and justified in [`expected-oracle.md`](evidence/ticket14/expected-oracle.md). Each surviving value is checked whole — MD5, octet length, bit length, disk size and a direct SQL equality against the literal it was built from — never by length alone. The MD5s are recomputed at run time from the byte pattern with `md5sum`, so the expectation never comes from the engine under test; they were also computed independently in Python and the two agree.

**One provenance claim had to be withdrawn, and it is worth reading before trusting any oracle in this campaign.** An earlier revision of the oracle said that no OOS-backed value, placement, chunk count or recovery result of this fixture had been observed before it was written. That was false. [`probes/probe_format.sh`](evidence/ticket14/probes/probe_format.sh) ran at 12:58 and the oracle was first written at 13:07; the probe had used a table of the same shape with rows of exactly 4,036 `AA`, 16,284 `BB` and 4,011 `CC`, applied the same `EE` update, crashed and restarted the server and read back `COUNT(*)`, the three digests and `SHOW HEAP OOS` before and after recovery. What survives is that the **justification** is independent of the engine — arithmetic over ticket 11's constants plus two independent digest computations, which would have produced the same numbers with no engine available, and which an independent reviewer re-derived — but the **ordering** claim cannot be made. Independence here rests on the derivation, not on ignorance of the answer. Two of the four probes ([`probe_restart.sh`](evidence/ticket14/probes/probe_restart.sh) and `probe_restart2.sh`) did use a deliberately unrelated one-row fixture, which is what the discipline should have been throughout. **For tickets 18 to 22 and 23 to 32: probe format on a fixture that is not the case's fixture.** It costs nothing and keeps the stronger claim available.

Four design points worth naming:

- **Correct results are not accepted as OOS coverage.** `SHOW HEAP OOS OF oos_dur01` must report one OOS file and exactly four chunk records before the crash, on a table the case owns exclusively. Without it the case would pass identically on an engine that stored everything inline.
- **`Oos_recs_sumlen` is recorded, never asserted.** The pinned run reported 24,444, matching the derivation exactly (4,044 + 16, 16,292 + 2×16, 4,044 + 16). The accepted 24-byte chunk header would give 24,476. That divergence is the `OOS-REP-05` / CBRD-26950 Capability gap, so the number belongs in the journal, not in an expectation.
- **The post-recovery chunk count is a range, 3 to 5.** Three live chunks plus the two dead chains that vacuum reclaims asynchronously. A point value would make the case flaky for a reason that has nothing to do with durability.
- **The post-crash `cubrid server start` and `checkdb` run with `SKIP_CHECK_RECOVERY_ERROR=TRUE`.** CTP's `cubrid` wrapper archives the whole installation and adds a NOK line of its own when one of those utilities exits non-zero. This case crashes on purpose and reports its own verdict, so the wrapper's archive would be noise. It is the convention `cbrd_27229` established and five other private cases use. **Because that switches off CTP's snapshot channel, the case preserves its own failure evidence**: the first failed assertion captures processes, journals, server status and the CUBRID logs, and cleanup copies the recovered database and the server logs aside before deleting them. Without that, a failed value assertion — the most valuable thing this case can find — would have left nothing but a result line. Every copy step's exit status is checked and a failed copy is reported as a further NOK, so a lost image cannot be silent. The negative control exercises the path: it journalled `preservation|ok` and preserved a 259 MiB database image.
- **The case states a campaign outcome of its own.** CTP has only PASS and FAIL per case, so assertion-level skips are not enough: on a build without `SHOW HEAP OOS`, assertions 5 and 15 would both skip and the case would still report `[OK]` — a pass with no activation evidence at all, which is exactly what the campaign forbids. The case therefore writes `PASS`, `FAIL` or `SKIP` with a reason into `<evidence>/case_outcome`, the runner surfaces it, and the manifest's case outcome comes from it. A run that proved durability but never observed the out-of-row path is recorded as SKIP and is not counted as coverage. On both pinned builds the file reads `PASS`.

**Transaction-state model.** `OOS-DUR-01`'s authority note forbids judging recovery by "a missing acknowledgement means rollback". The case keeps an external journal — a request line before each transaction and an acknowledgement line after it carrying the `csql` exit status, the affected-row count and the error count — and takes the crash only after the third acknowledgement, so the permitted state is a single one: all three committed. `OOS-DUR-03`, where an outcome is genuinely unknown, is a different requirement and is not claimed here. The durable-commit configuration is read back from `cubrid paramdump -S` rather than assumed: `async_commit=n`, `group_commit_interval_in_msecs=0`, `auto_restart_server=n`.

## 4. Runs

All on the pinned unmodified installs, 16 KiB pages, client-server, under the namespace. Library hashes are re-verified against ticket 11 before the launcher is allowed to start, because a CUBRID binary reports whichever library the loader resolves.

**The two campaign attempts** — these are the only runs with a manifest, an attempt record, a replay-bundle index and matrix rows:

| Attempt | Build | Cases | Assertions | Skips | Case | Outcome |
|---|---|---|---|---|---|---|
| `att-T14-0023` (`inv-T14-0001`) | release | expected 1, discovered 1, executed 1 | 16 executed, 16 OK, 0 NOK | 1 | 14 s (25 s invocation) | **PASS** |
| `att-T14-0024` (`inv-T14-0002`) | debug | expected 1, discovered 1, executed 1 | 17 executed, 17 OK, 0 NOK | 0 | 18 s (26 s invocation) | **PASS** |

**Two supporting runs, neither of which is a campaign attempt.** They have no manifest, no attempt record and no matrix row, on purpose — one is checker validation and the other is a verification step — so their verdicts below are results, not coverage. Each directory carries a README saying why:

| Run | Build | Cases | Assertions | Skips | Case | Result |
|---|---|---|---|---|---|---|
| `att-T14-0025` — checker validation | release | expected 1, discovered 1, executed 1 | 16 executed, 15 OK, **1 NOK** | 1 | 13 s (20 s invocation) | **FAIL**, as required of a negative control |
| `att-T14-0016-bucket` — coexistence | release | expected 11, discovered 11, executed 11 | this case: 16 OK, 0 NOK | 1 | 12 s (397 s invocation) | this case **PASS**; 2 sibling cases failed, see below |

Each run also verified, by hashing before and after, that the pinned install's `conf` and `databases` came back byte-identical and that the user's own `~/.CUBRID_SHELL_FM` was neither read nor written: `install_conf_drift_lines=0`, `install_databases_drift_lines=0`, `user_shell_fm_drift_lines=0`. The testcase worktree was left with zero untracked files after every run.

### SKIP semantics

CTP fails a case if and only if a result line contains the substring `NOK`, and it has no per-assertion skip concept. The case therefore writes a skip on the assertion's own number, in a form that is **neither `OK` nor `NOK`**:

```
cbrd_26659_oos_dur01-17 : SKIP debug_oos_log_records_chain_delete : release build: oos_debug
and oos_trace are compiled out under NDEBUG, so $CUBRID/log/oos.log is never written
```

The result file therefore stays contiguously numbered 1 to 17 the way `write_ok` numbers it. The skip is visible in the result file and in CTP's `feedback.log`, it is recorded machine-readably in the case's `skipped.journal`, and it is carried into the manifest as `skip_reason` with `assertions.expected = executed = 16` against the oracle's 17. It never becomes an `OK`, so it cannot inflate the pass count. The prior private encryption case (`log_enc_04`) writes a bare `write_ok` and exits on a non-debug build; this replaces that behaviour while reusing the idea of a debug-gated observation.

### Checker validation

Three checking mechanisms, three controlled failures.

**The whole-value oracle.** [`cases/make_negative_control.sh`](/home/vimkim/gh/tc/cubrid-testcases-private-ex-cbrd-26659/shell/_06_issues/_26_2h/cbrd_26659_oos_dur01/cases/make_negative_control.sh) derives the control from the regression case by exactly two textual mutations and refuses to emit anything if either stops applying, so the control cannot drift away from the case it validates. The defect is one byte: the expected size of the multi-chunk row becomes 16,283 while the row still holds 16,284. The checker caught it on every axis at once:

```
oos_dur01_negative_control-12 : NOK recovered_value_id2_multi_chunk_oos :
  expected [OOSROW|2|05787a81…|16283|130264|16288|1]
  got      [OOSROW|2|02b6cc6d…|16284|130272|16292|0]
```

Exactly one assertion failed and the case failed; the other fifteen still passed, so the control is narrow.

**It is kept outside the regression cases, and that is demonstrated rather than asserted.** CTP discovers a case iff the file name equals its **grandparent directory name plus `.sh`** — `Dispatch.getAllTestCaseScripts` runs `find … -name "*.sh" | awk -F / '{ if ($(NF-2)".sh" == $NF) print }'` — *not* because the directory is called `cases`. `make_negative_control.sh` does not match, which is the same reason the 272 other helper scripts that live inside a `cases/` directory in this repository are never run as cases. [`discovery.txt`](evidence/ticket14/discovery.txt) runs that exact command over the whole `_26_2h` bucket and shows the generator absent from all eleven discovered cases.

**The activation channel's failure classifier.** A `SHOW HEAP OOS` that does not answer is classified three ways, not two: only a syntax error means the build lacks the statement and skips, and anything else — a disconnect, an authorization error, a renamed column, a class-name mismatch — is this case's problem and fails. Collapsing them would record a real failure as a capability gap, and since a SKIP line carries no NOK the case would pass with no activation evidence: the inverse of what the case is for. [`tools/checker_validation_classifier.sh`](evidence/ticket14/tools/checker_validation_classifier.sh) puts **fourteen** output shapes through it, and it has earned every one: the classifier has been wrong four times, and each defect would have passed a green run.

| Defect | Caught by |
|---|---|
| Two outcomes and a catch-all, so any non-syntax failure read as a missing capability | the Standards confirmation pass |
| Matching the bare class name, which also matches `ERROR: Unknown class "dba.oos_dur01".`, so an error read as an answer and fields came out of the error text | shape 5, while writing the fix for the first |
| Hardcoded column positions — a row wide enough is not a row whose field 11 is still `Oos_num_recs`; a reordering in `show_meta.c` read silently as `has_oos=577`, `chunks=16344` | the Standards confirmation pass, second round |
| A shell-quoting error in that fix, which made the class-name match look for a doubly-quoted name so no real row matched at all | shape 1, before it shipped |

The shipped version requires the single-quoted class name (matched with `index()`, so the dots are not a regex), a header seen first, and a row at least as wide as that header; it reads each column by **name** from the output's own header rather than by position; and one selector feeds both the classification and the extraction so the two cannot disagree about which line is the row. A column the case needs that the header does not have is a failure, not a capability gap. Shape 8 — a class with no OOS file — is the one shape no run of this case can produce, so it is constructed from the engine source instead: `heap_oos.cpp` makes only `Oos_volume_id` and `Oos_file_id` null when `has_oos_file` is 0, and csql renders a NULL as the literal token `NULL`, so the row keeps its full width. That is precisely the shape where a wrong field count would have turned a real finding into a capability gap. Two of the fourteen shapes pin an interaction rather than a past defect. Shape 13 is the only construction in which a column located by name could point past the row's last field — a header wider than the data row — and it fails closed. Shape 14 locks the column-name comparison to **exact field equality**: this header carries both `Heap_volume_id` and `Oos_volume_id`, and `Oos_num_recs` shares fragments with `Oos_recs_sumlen` and `Oos_num_user_pages`, so a substring or regex match on the name side would reintroduce by-name precisely the wrong-column bug that was just removed by-position. The Standards confirmation pass raised that as an explicit guess about code it had not read; the code was already exact, and the shape exists to keep it that way. Output in [`checker-validation-classifier.txt`](evidence/ticket14/checker-validation-classifier.txt), `failures=0`.

**The acknowledgement parser.** The case's third checking mechanism turns `csql` output into the affected-row and error counts that `assert_txn` judges a committed transaction by. [`tools/checker_validation_journal.sh`](evidence/ticket14/tools/checker_validation_journal.sh) gives it controlled failures: a SQL error and a connection failure must both yield `affected=0` with `errors ≥ 1`. That matters because `csql` was observed exiting **0** while printing `ERROR: Failed to connect`, so a parser that read those shapes as success would let a transaction that never ran be journalled as acknowledged. Output in [`checker-validation-journal.txt`](evidence/ticket14/checker-validation-journal.txt), eleven checks, `failures=0`.

### Activation evidence

**Proven, not reused**, for both configurations: each invocation collects its own `SHOW HEAP OOS` output inline, in the same session, same fixture and same execution path as the assertions it supports. This is stronger than ticket 13's public case, which had to mark its evidence `reused` because CTP ran client-server while its checker ran standalone.

The release run reported `Has_oos_file 1`, `Oos_num_recs 4`, `Oos_num_user_pages 4`, `Oos_page_size 16344`, `Oos_recs_sumlen 24444`, and after recovery `Oos_num_recs 5` — the top of the asserted range, both dead chains still present at the moment of the observation.

The debug run adds the delete-side channel. Ticket 11 §6 found that at this pin the debug `oos.log` carries delete-side lines only, because the SQL insert path calls `oos_insert_many`, which has no `oos_debug` call. A probe for this ticket added a second fact: in client-server mode a committed UPDATE and DELETE wrote nothing to `oos.log` within three seconds, because the chains are reclaimed by vacuum asynchronously, while the same statements in standalone mode wrote `heap_recdes_get_oos_oids`, `oos_delete` and `oos_delete_chain` synchronously through the SA_MODE eager path. Assertion 17 therefore runs its update standalone, last, after every durability assertion has finished, and asserts an **increase** over the line count taken immediately before. In the recorded debug run vacuum had in fact already written four delete lines about three seconds after the restart, and the standalone step added two more — which is why the assertion is written as an increase and not as "the log is non-empty".

### Coexistence

The case was also run in one invocation with all ten existing cases of its issue bucket ([`att-T14-0016-bucket/`](evidence/ticket14/att-T14-0016-bucket/)). It produced the same 16 OK, 1 SKIP and `case_outcome=PASS` as when run alone, the install configuration and the worktree came back unchanged, and CTP dispatched it last. Two sibling cases failed — `cbrd_26777` ("Failed to start cubrid manager", a prerequisite this pinned install does not provide) and `cbrd_27097` — both identically in two earlier runs of the same bucket and both before this case ran in dispatch order. They are recorded as an observation for whichever tickets own those requirements, not attributed here.

## 5. Timing and budget (for ticket 17)

| | Case time | Invocation wall time |
|---|---:|---:|
| Release | 14 s | 25 s |
| Debug | 18 s | 26 s |
| Whole 11-case bucket | — | 397 s |

A crash-and-recovery case at 16 KiB costs well under 30 seconds end to end, so **this workload belongs in the fast tier**, not the scheduled one: 14 s against a 120 s per-case cap and a 900 s invocation cap. That is the second fast-tier data point after ticket 13's 39 s SQL case, and the first for the shell seam. The bucket figure is a useful second number for ticket 17: the whole existing `_26_2h` bucket plus this case runs in under seven minutes, so a fast-tier invocation that selects a whole issue bucket is still inside the 15-minute cap.

One deviation to record rather than hide: the launcher's own `testcase_timeout_in_secs` was set to 900, not to the tier's 120 s per-case cap, deliberately — CTP enforces its timeout with a kill, and a crash-recovery case truncated mid-restart would leave a running server and destroy its own evidence. The campaign cap is therefore currently judged from the measured time rather than enforced by the harness. **Enforcing caps with evidence capture belongs to ticket 15.**

Storage: the whole ticket occupies about 280 MiB under, almost all of it the negative control's preserved database image, `/home/vimkim/.cub/campaign/cbrd-26659/ticket14`, against the campaign's 100 GiB budget; `/home` had 2.3 TiB free when the runs started. Nothing was written to the temporary filesystem.

## 6. Findings for other tickets

**a. The shell seam has a real assertion counter; the SQL seam does not.** Ticket 13 had to record `executed.assertion_count` as null because CTP's SQL runner reports only `Total`, `Success`, `Fail` and `execute_case`. The shell runner is different: the case writes one `<case>-<n> : OK|NOK` line per assertion into its `.result` file and CTP reproduces them in `feedback.log`. Ticket 13's finding `P4` does not carry over, and the counts in this ticket's manifests are measured. **Ticket 15** can count shell assertions with `grep -cE "^<case>-[0-9]+ : (OK|NOK)"`.

**b. The launcher still exits 0 on a failed case.** The negative control reported `Total Fail Case: 1` with launcher exit status 0, exactly as on the SQL side. **Ticket 15's wrappers must read `result/shell/current_runtime_logs/test_status.data`, never `$?`.** A blank result file is the one thing CTP treats as a failure on its own.

**c. CTP rewrites `$CUBRID/conf` from `~/.CUBRID_SHELL_FM` before every case, and does not put its own changes back.** `Test.resetCUBRID_linux` runs `rm -rf ${CUBRID}/conf/*` then `cp -rf ~/.CUBRID_SHELL_FM/conf/*`, and the same for `databases/`. On this host that snapshot is a **whole foreign install carrying `cubrid_port_id = 1523`**, so an unguarded run replaces the pinned install's configuration with it. CTP then writes the invocation's ports into `cubrid.conf`, `cubrid_broker.conf` and `cubrid_ha.conf` and leaves them there. The runner here redirects `HOME` to a campaign-owned directory seeded from the pinned install and restores `conf` and `databases` verbatim afterwards, verifying both by hash. **Any ticket that runs CTP shell against the pinned installs must do the same.**

**d. A capability gate needs three outcomes, not two, or a failure becomes a capability gap.** The activation check began as "syntax error → skip, row found → assert, anything else → skip". That catch-all made a disconnect, an authorization error or a renamed column indistinguishable from a build that lacks the statement: the skip reason asserted a cause that was never established, and because a SKIP line carries no `NOK`, the case passed with no activation evidence at all. Every capability gate in tickets 23 to 32 wants the three-way shape — the one specific signal that really means "absent" skips, and everything else fails — plus its own controlled failure examples, because this defect passes every green run.

**e. The CTP `cubrid` wrapper archives the whole installation when `server` or `checkdb` exits non-zero**, unless `SKIP_CHECK_RECOVERY_ERROR=TRUE` is set (`$init_path/cubrid` → `should_save_snapshot_for_recovery` → `do_save_snapshot_by_type`). Every crash-and-recovery case in tickets 23 to 32 wants that variable on its post-crash start, as `cbrd_27229` does.

**f. `csql` cannot be judged by its exit status alone.** It exits 1 on a SQL error and on a connection failure to an unknown database, but it was observed exiting **0** while printing `ERROR: Failed to connect to database server` when the master held a stale registration for a killed server. Every assertion here checks output content as well as status, and the parser has its own controlled failure example.

**g. A `kill -9` of `cub_server` alone is not a usable crash.** With `auto_restart_server=y` (the default) `cub_master` restarts the server itself, so recovery happens before the case asks for it. With `auto_restart_server=no` the master keeps a stale registration, `cubrid server start` returns 0 while doing nothing, and connections fail. **The protocol that works is to kill the server, its `cub_pl` and the master together and then `cubrid server start`, which restarts the master and recovers the database.** Tickets 23 to 32, and 24 in particular, should reuse this rather than rediscover it.

**h. CTP's discovery rule is about the file name, not the directory name.** A script is a case iff its name equals its grandparent directory name plus `.sh`. Two consequences: a helper inside `cases/` is never run (272 already exist in this repository), and a case file renamed without renaming its directory silently stops being discovered.

**i. A selector must match the shape of the row, not the name of the thing it carries — and not its position either.** This one cost four defects in one small function and will recur in every case that reads a `SHOW` statement at the SQL seam. Three layers, each of which looked fine until it was attacked: matching the class *name* also matches `ERROR: Unknown class "dba.oos_dur01".`, so an error classified as an answer; matching a *field count* proves a row is wide enough but not that field 11 is still `Oos_num_recs`, and the column order lives one line away in `src/parser/show_meta.c`; and the code that decides "is there a row" must be the same code that reads it, or the two drift. The shipped form: the single-quoted class name matched literally, a header seen first, a row at least as wide as that header, and every column located by **name** from that header. Generalized by the Standards confirmation pass, whose framing this is. The corollary is the practical one — **write the controlled failure example for the fix, not just for the thing being fixed**: two of those four defects were in a fix, and both were caught by the shapes written to validate it rather than by any run of the case. Three of the four were caught by that validator rather than by review, which is the reviewer's own assessment of where the credit sits: a twelve- then fourteen-shape table keeps working after everyone stops looking at the code, and shape 1 catching a shell-quoting slip inside a fix is not something reading would reliably have found.

**j. Ticket 13 left three `.forFun` files in the pinned release install's `conf/`** (`cubrid.conf.forFun`, `cubrid_broker.conf.forFun`, `cubrid_ha.conf.forFun`), copied in from the user's `~/.CUBRID_SHELL_FM` snapshot by finding (c). They are inert — CUBRID reads only `cubrid.conf` — and were left in place rather than removed, since they are part of the state ticket 13's audit recorded. The debug install has none. Noted so a later drift check does not read them as new.

## 7. Ticket 14 criteria checklist

| Criterion | Status |
|---|---|
| New private worktree on branch `CBRD-26659-oos-testcases-handover`, based on a freshly fetched and verified `origin/develop` tip; base and testcase SHAs recorded; canonical checkout untouched | met (§1) |
| Process-ownership isolation established and demonstrated before any case ran; method recorded | met (§2) — namespace method, four checks with matched controls, plus a live unrelated instance that survived every invocation |
| One case following init / write_ok / write_nok / finish: disposable database, OOS-backed values sized from the boundary table, commit, restart, exact whole values; owns and cleans only its own resources; has a deadline | met (§3) — every wait carries a deadline, and a reached deadline captures evidence, ends the attempt and cannot report success |
| A missing capability records SKIP with a reason, visible in the manifest | met (§4) — one skip on release, `skip_reason` in `inv-T14-0001`, `skipped.journal` in the bundle |
| The CTP shell launcher discovers and runs the case here; discovery and assertion counts recorded | met (§4) — expected 1 = discovered 1 = executed 1 alone, and 11 = 11 = 11 in the bucket; 16 and 17 assertions measured |
| One negative control produces a failed assertion and a failed case, kept outside the regression cases | met (§4) — one NOK, case failed, non-discovery demonstrated with CTP's own rule; a second control covers the journal parser |
| Activation evidence from a debug-build run recorded with applicability conditions | met (§4) — `inv-T14-0002`; evidence is `proven` rather than `reused` in both configurations |
| Hand-written manifest and matrix row per ticket 12's schemas, in the evidence home; run time recorded for ticket 17 | met — two manifests, two attempt records, two replay-bundle indexes and four matrix rows, all validating; `tools/check_campaign_records.py` passes |
| Work committed locally; nothing pushed | met — testcase commit `c3d1e7146`, no push, no pull request |

## 8. What the review changed

A two-axis review ran, Standards first and then Spec. Both returned findings; all were fixed, the case was re-committed, and **every run in §4 is a re-run of the fixed case**. Revisions 1 and 2 (`att-T14-0001` to `att-T14-0012-bucket`) are retained as history and are cited by no manifest.

### Standards axis

| Finding | Fix |
|---|---|
| The negative-control generator sat in a `negative_control/` directory beside `cases/` — a directory shape this repository has no instance of | Moved into `cases/` as a non-discovered helper, the shape 272 other helpers already use |
| The post-crash `cubrid server start` and `checkdb` lacked `SKIP_CHECK_RECOVERY_ERROR=TRUE`, so a failure would make CTP archive the whole installation | Added, following `cbrd_27229` |
| `skip()` invented a `-skip` suffix, breaking `write_ok`'s contiguous numbering | The skip now takes the next assertion number |
| The guard on `OOS_CAMPAIGN_EVIDENCE_DIR` accepted any `/home/*/*` path before `rm -rf`-ing it | The case never deletes a caller-supplied directory; it must be absent or empty |
| `oos_field` could return more than one line, turning the numeric range check into a shell error rather than a failed assertion | Takes the first row; the numeric comparisons are quoted |

Two judgement calls were also taken: the `pass()` wrapper around `write_ok` was removed as a middle man, and the two `SHOW HEAP OOS` reads were factored into one helper so the read, the record and the skip live in one place. The scratch format probes were moved out of the campaign's tools directory into [`probes/`](evidence/ticket14/probes/) with a note on what each one settled, since the oracle cites them.

### Spec axis

The Spec reviewer independently re-derived the sizes, the digests, the chunk counts, the non-discovery argument and the `proven` evidence status, and all of them hold. It returned one critical finding and three major ones.

| Finding | Fix |
|---|---|
| **Critical.** The oracle's "nothing of this fixture was observed beforehand" claim was false: `probe_format.sh` had already run the case's fixture, sizes, update, crash and restart nine minutes earlier | The claim is withdrawn in the oracle, in `probes/README.txt` and in §3 above, with the process finding for the remaining tickets |
| Switching off CTP's snapshot channel removed the last database image, while `fail()` captured nothing and cleanup deleted the database unconditionally — so the most valuable failure this case can find was being destroyed before triage | `fail()` captures a first-failure snapshot; cleanup copies the recovered database and the server logs aside when anything failed. The negative control exercises the path |
| The attempt records declared `deadline.seconds: 120` while the case allowed a 180 s restart, so a 150 s restart would have passed while blowing the declared cap | The case's waits are now 30 s and 60 s, chosen so a run reaching both still finishes inside the 120 s cap |
| SKIP was assertion-level only: on a build without `SHOW HEAP OOS` the case would have reported `[OK]` with no activation evidence at all | The case now states a campaign outcome of its own; that situation records `SKIP` |

Two smaller points were also acted on: the `applicability` block is now filled in on every evidence record rather than left null, which is what criterion 7's "recorded with applicability conditions" asks for; and the coexistence run, which no criterion asked for, is labelled as the implementation workflow's verification step rather than as coverage.

### Confirmation passes

Both reviewers then verified their findings against the artifacts rather than against my report, and both closed their axes. Three of their own recommendations were withdrawn in the process, which is worth recording because in each case the disposition that survived was better than the one originally proposed: deleting the probe scripts would have destroyed the evidence of the provenance overclaim the Spec axis went on to find; the negative control's missing attempt record was a legibility gap, fixed by a README and by splitting the runs table, not by fabricating a FAIL attempt; and `validate_records.py` is not a duplicate of `check_campaign_records.py`, which never reads a ticket's records. One correction went the other way: the Standards report said a non-zero `cubrid server start` triggers `do_save_snapshot_by_type`, when it fires only if `should_save_snapshot_for_recovery` matches the failure text — accepted, and it does not change the fix.

The Standards axis then confirmed all seven mechanical points against the new commit — including that nothing was half-wrapped, that the numbering really is contiguous in both result files, and that the case-level SKIP branch is genuinely reachable rather than lost to a subshell — and found one new MEDIUM defect the quoting fix had not touched: the activation channel's failure classifier collapsed three outcomes into two, so any non-syntax `SHOW HEAP OOS` failure was reported as a missing capability. That is fixed in revision 5, and writing its controlled failure example caught a second defect in my own fix before it shipped. A third confirmation pass, scoped to the revised code that no reviewer had yet read, then found that the new selector still trusted hardcoded column positions and settled from the engine source the one row shape no run of this case can produce; revision 6 reads every column by name from the output's own header, and a twelfth shape caught a shell-quoting error in *that* fix. Four defects in one small function, none of which any green run would have revealed — see the classifier table in §4, which is the clearest argument in this ticket for the campaign's rule that every checking mechanism needs a controlled failure.

The Spec axis left one residual, minor and non-blocking, which is fixed in revision 4: `do_cleanup`'s preservation copies discarded their errors with `2>/dev/null`, so a full filesystem or a permission problem would have left an empty directory and nobody told. Every step is now checked and a failed copy is reported as a further NOK. Because that copy is the only image a failing run leaves behind, a silent loss there is precisely the failure mode this campaign exists to prevent — so it was fixed here rather than deferred to the tickets that inherit the helper.

## 9. What this does not claim

- **It does not claim coverage.** Two requirements of the sixty-three are executed. Forty-nine assertable or observation-only requirements still have no executed case, and they are listed in both manifests; tickets 18 to 22 and 23 to 32 close them.
- **It does not claim `OOS-DUR-02`, `-03`, `-05` or `-06`.** Every transaction here is acknowledged before the crash, so nothing is undone, nothing has an unknown outcome, and no vacuum delete is interrupted.
- **It does not assert the engine identity from inside the case.** The case records `cubrid_rel` in its journal and asserts nothing about it, so the same case stays meaningful on a later build; the pin is asserted by the runner, which refuses to start if the library hashes do not match ticket 11, and is recorded in the manifests.
- **It does not attribute the two sibling failures** in the bucket run to anything. They are an observation.
- **It no longer claims that the oracle was written before the engine was consulted.** §3 says what actually happened. The expectations are independently derived and independently reproduced; the ordering claim is withdrawn.
- **The specification's independent agent review is outstanding.** The two-axis review of §8 was commissioned by the authoring session and does not satisfy that requirement. There is no answer promotion to sign off: the shell seam has no answer artifact, because the case is its own comparator.

## 10. Decision requests

1. **Fast-tier placement of crash-recovery workloads.** §5 measures 14 s and 18 s. Ticket 17 should decide whether crash and restart cases sit in the fast tier on that evidence, given that they take a server down and back up.
2. **Cap enforcement.** The launcher timeout is deliberately above the campaign's per-case cap so that CTP cannot destroy a crash case's evidence. Ticket 15 owns enforcing the cap with evidence capture instead; until it does, caps on the shell seam are measured, not enforced.
3. **Namespace isolation as a campaign-wide rule.** It worked here without privileges and it removes the need to stop unrelated CUBRID processes by hand, which ticket 13 had to do. Recommend making `campaign_ns.sh` a precondition of every private shell invocation, and of public SQL invocations too. Ports remain allocated rather than isolated.
