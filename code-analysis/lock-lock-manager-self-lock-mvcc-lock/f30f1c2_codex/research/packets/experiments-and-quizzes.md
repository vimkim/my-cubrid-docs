# Role 4 packet — CUBRID Experiments and Korean Mechanism Quizzes

## Packet metadata

- Role: Experiment and Quiz Designer (Role 4 only)
- Analysis Topic: `CUBRID lock과 lock manager: self lock 및 MVCC lock의 필요성`
- Declared Scope: `research/scope.md`
- Declared Scope SHA-256: `711d1a0f5bfebdbe1b55b4299973efc353d90636e2f00fc807f51d031766a839`
- CUBRID root: `/home/vimkim/gh/cb/cubrid-analysis`
- CUBRID revision: `f30f1c26003e5aa8e93182648e06cad76fc77064` (`WORKTREE`)
- CUBRID frozen status SHA-256 supplied by the Report Run: `6f459c90a9e5391919b0f19ac04ffd081eab7905b9fde6cc27658f45f817bad1`
- PostgreSQL revision carried by the frozen scope: `fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc`
- MySQL revision carried by the frozen scope: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- Timestamp (UTC): `2026-08-11T08:44:36Z`
- Output contract: this file is a read-only design packet. This role did not build CUBRID, start a database, run an Experiment or Quiz, instrument source, or change source, `report.json`, `claims.jsonl`, Book, Experiment, or Quiz artifacts.

## Executive design

Use four separate, skill-owned databases so that each Central Behavior has one discriminating runtime Experiment and one reproducible Korean Quiz. Do not collapse all four into one large timing test: the whole teaching point is to distinguish class/instance resources, ordinary wait-for edges, MVCC read/write policy, and MVCCID transaction resources.

| ID | Central Behavior | Owned database | Central runtime observation | Proposed runtime Claim |
|---|---|---|---|---|
| `experiment-1` / `quiz-1` | `resource-mode-hierarchy` | `calocke1f30` / `qalockq1f30` | One `SELECT ... FOR UPDATE` transaction owns class `IX_LOCK` and instance `X_LOCK` entries with the same `tran_index`; both disappear at transaction end | `CUBRID-C006` |
| `experiment-2` / `quiz-2` | `wait-deadlock-release` | `calocke2f30` / `qalockq2f30` | Two row-X holders form a wait-for cycle; exactly one transaction is aborted, the survivor resumes, and only one transaction's complete pair of updates remains | `CUBRID-C016` |
| `experiment-3` / `quiz-3` | `mvcc-lock-policy` | `calocke3f30` / `qalockq3f30` | A plain snapshot read returns the committed version while another writer is active, whereas a locked read on the same row appears as an X waiter and resumes after rollback | `CUBRID-C028` |
| `experiment-4` / `quiz-4` | `mvccid-self-lock-rendezvous` | `calocke4f30` / `qalockq4f30` | Unique and FK observers wait with `S_LOCK` on two distinct `Transaction self-lock (inserter MVCCID = ...)` resources whose inserters hold `X_LOCK`, then re-check successfully after rollback/commit | `CUBRID-C038` |

The proposed Claim IDs are members of the corresponding Central Behavior's reserved Claim set in `report.json`. The main agent must bind each run to the actual `runtime` or `source+runtime` Claim after validating the ledger; it must not keep a proposed ID merely because this packet suggested it.

No instrumentation is proposed. SQL-visible values, direct csql receipts, `cubrid lockdb`, the existing csql histogram watcher, actor exit status, and the owned server event log are sufficient. Runtime cannot alone prove every internal call or latch-release line; those limitations are explicitly preserved below.

## Source checks that constrain the oracles

These are source-derived design constraints, not yet Claim ledger entries. The main agent must reopen complete functions and attach pinned hashes before promoting them to Claims.

| Mechanism or oracle | Pinned source checked | Consequence for Experiment design |
|---|---|---|
| Compatibility and conversion | `src/transaction/lock_table.c:30-239`, `lock_Comp`, `lock_Conv` | `IX` is compatible with another `IX` but not with `S`/`X`; `IS + IX -> IX`, while `S + IX -> SIX`. Do not explain a wait by mode names without reading the matrix in the correct row/column orientation. |
| Class intent for locked read | `src/query/query_executor.c:24339-24379`, `qexec_for_update_set_class_locks` | `SELECT ... FOR UPDATE` on an MVCC class requests class `IX_LOCK`. Experiment 1 uses this as its hierarchy parent. |
| Row X and re-evaluation | `src/transaction/locator_sr.c:13101-13232`, `locator_lock_and_get_object_with_evaluation` | The locked/read-for-update path acquires instance `X_LOCK`; if the version changed while waiting, it re-evaluates rather than trusting the pre-wait row. Experiment 3 chooses a holder rollback so the post-wait result is unambiguous. |
| Plain MVCC select does not take a row lock | `src/transaction/locator_sr.c:13235-13340`, `locator_get_object` | For `S_SELECT` on an MVCC class, the chosen instance mode is `NULL_LOCK` and the visible version is read. This is the negative half of Experiment 3; it is not a claim that the entire statement takes no schema/class locks. |
| Object wait counter | `src/transaction/lock_manager.c:4053-4079`, `lock_internal_perform_lock_object`; metadata at `src/base/perf_monitor.c:236-247` | `Num_object_locks_waits` increments immediately before `lock_suspend`. A csql histogram watcher must already be attached. Treat `>= N` as supporting evidence, never an exact global count. |
| Object wait time counter | `src/base/perf_monitor.c:1099-1112`, `perfmon_lk_waited_time_on_objects` | The wait duration and per-mode time are updated after resume only while lock-object performance tracking is active. Exact microseconds are never an oracle. |
| Counter increment-site search | `rg 'PSTAT_LK_NUM_WAITED_ON_OBJECTS' src` found the one increment at `lock_manager.c:4061` plus definitions/metadata | For this revision the counter means entries that reached the object-lock suspend state. It includes ordinary object resources and transaction self-lock resources because both reuse the same internal engine. |
| Lock dump types | `src/transaction/lock_manager.c:5583-5768`, `lock_dump_resource` | Full `lockdb` distinguishes class, instance, and transaction resources; transaction resources print the literal `Transaction self-lock (inserter MVCCID = N)`. Holder/waiter `tran_index` is not the same identity as resource MVCCID. |
| Contention filter | `src/transaction/lock_manager.c:8939-9063`, `xlock_dump`; `src/executables/util_cs.c:1286-1354`, `lockdb` | `lockdb -c` prints only resources with a blocked holder or waiter. Use full `lockdb` for uncontended hierarchy/readiness, `-c` for waits. Filter out the administrative `lockdb` transaction itself. |
| Wait cleanup | `src/transaction/lock_manager.c:4081-4110` | Timeout, deadlock victim, and interrupt remove the waiting entry. A post-run dump must show no target holder/waiter remains. |
| Deadlock construction and resolution | `src/transaction/lock_manager.c:8180-8515`, `lock_detect_local_deadlock` | The detector builds wait-for edges from incompatible holder/waiter entries, prefers a timeout-capable victim, otherwise selects an abort victim, writes a `DEADLOCK` event, and wakes a victim. Keep actor lock timeout infinite so the experiment exercises unilateral abort rather than timeout preference. |
| Transaction-end release | `src/transaction/lock_manager.c:7348-7423`, `lock_unlock_all`; commit/abort callers at `src/transaction/log_manager.c:5190-5260, 5320-5355` | Instance, class, and root-class hold lists are drained at transaction end. For MVCC, active-state completion precedes unlock. Post-run absence and resumed waiters are valid lifecycle observations. |
| Self-lock X acquisition | `src/transaction/log_tran_table.c:4050-4188`, `logtb_acquire_mvccid_self_lock`, `logtb_get_current_mvccid`, `logtb_ensure_mvccid_self_lock` | A normal active worker transaction obtains an X self-lock on its current MVCCID, and the hint makes repeated ensure calls idempotent. |
| Per-row X replacement for append | `src/storage/heap_file.c:20505-20584`, insert-location path | MVCC appends ensure the self-lock and skip the per-row X entry when tracking succeeds. A full lock dump can therefore distinguish transaction-resource protection from a row OID lock; runtime still does not prove the allocation-count saving for all workloads. |
| Self-lock S wait and re-read | `src/storage/btree.c:23670-23773`, `btree_is_active_other_inserter`, `btree_wait_for_inserter_end`, `btree_key_wait_for_insert_mvccid` | The checker drops object/page state, requests S on the inserter MVCCID, releases it after grant, verifies inactivity, and restarts from the root. Experiment 4 selects rollback/commit results that require a post-wait decision. |
| MVCC completion before unlock | `src/transaction/log_manager.c:5203-5257, 5334-5355` | The report may combine source ordering with runtime wakeup; SQL output alone cannot timestamp `logtb_complete_mvcc` versus `lock_unlock_all`. |

There is no dedicated `PSTAT_*` deadlock counter in the searched lock/perf sources. Do not use a similarly named generic counter as a deadlock oracle. For Experiment 2 use the two-edge lock dump when captured, the actor failure class, the owned `DEADLOCK` event block, the survivor's completion, and the final atomic value invariant.

## Shared build, identity, capture, and ownership gate

### Mandatory runtime gate

Before writing/running any Experiment or Quiz artifact, the main agent must:

1. List live `cub_master`, `cub_server`, `cub_pl`, and csql processes and correlate their executable paths with the pinned worktree environment. If `just build` would replace binaries used by a user-owned server, stop for authorization. Never stop a global service for convenience.
2. Capture the baseline build from the pinned root:

```bash
python3 /home/vimkim/.agents/skills/cubrid-code-analysis-report/scripts/reportctl.py record \
  --report-dir /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex \
  --id runtime-baseline-build \
  --cwd /home/vimkim/gh/cb/cubrid-analysis \
  --expect-exit 0 \
  -- just build
```

3. Seal runtime tools:

```bash
python3 /home/vimkim/.agents/skills/cubrid-code-analysis-report/scripts/reportctl.py runtime-snapshot \
  --report-dir /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex \
  --id baseline \
  --build-run-id runtime-baseline-build
```

4. Read the absolute `csql` and `cubrid` paths from `evidence/runtime-tools-baseline.json`. In all scripts and manifests replace `CSQL_ABS_FROM_SNAPSHOT` and `CUBRID_ABS_FROM_SNAPSHOT` with those literal absolute paths. Placeholders are allowed in this design packet only.
5. Bind `report.json.runtime.runtime_build_run_id`, `baseline_tools_snapshot`, and `active_tools_snapshot` to this evidence before any Experiment observation.

### Canonical direct-csql capture shape

Every manifest `run_id` below names a direct csql invocation, not a wrapper. The exact candidate command shape is:

```bash
python3 /home/vimkim/.agents/skills/cubrid-code-analysis-report/scripts/reportctl.py record \
  --report-dir /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex \
  --id expN-observe-rK \
  --cwd /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/experiments/experiment-N \
  --expect-exit 0 \
  --runtime-tools-snapshot evidence/runtime-tools-baseline.json \
  -- CSQL_ABS_FROM_SNAPSHOT --CS-mode --user dba --no-auto-commit \
     --input-file observe.sql DB_NAME
```

The manifest `runner_argv` must be the resulting literal argv vector, for example:

```json
["/absolute/sealed/bin/csql", "--CS-mode", "--user", "dba", "--no-auto-commit", "--input-file", "observe.sql", "calocke1f30"]
```

When a direct observer must remain blocked while `lockdb` runs, start the entire `reportctl.py record ... -- CSQL ...` command asynchronously through the host execution facility. Do not hide the mandatory runner behind `bash`, `timeout`, `nohup`, or another launcher.

### Owned database rules

Each Experiment setup script follows the same transaction:

1. Verify the exact database name is absent from the first field of the sealed environment's `databases.txt` and that the Experiment's `runtime-owner.txt`, `runtime/db`, and `runtime/log` do not exist. A collision exits 73 without mutation.
2. Create exact local directories under that Experiment directory. Use `cubrid createdb --db-volume-size=64M --log-volume-size=64M --file-path <absolute runtime/db> --log-path <absolute runtime/log> <db> en_US.utf8` through the sealed absolute `cubrid` binary.
3. Immediately write `runtime-owner.txt` with report directory, Experiment ID, database name, CUBRID revision, registry path, resolved volume path, and creation timestamp. The setup error trap may clean only a resource it created in this invocation.
4. Start only the exact named database with `cubrid server start <db>`. Never call `cubrid service stop`.
5. Run separately captured direct setup SQL.

Cleanup must validate all owner fields and the registry path, confirm every recorded process has exited, stop only the exact named database, call `cubrid deletedb <db>`, verify its registry row is absent, and remove only known empty Experiment runtime directories. Never recursively delete a path derived from an unset variable. If ownership is uncertain, hard-stop and preserve evidence.

All holder/action PIDs live below the Experiment directory. Before signaling a survivor during failure cleanup, compare `/proc/<pid>/cmdline` with the recorded absolute csql path, exact SQL input, Experiment cwd, and database name. Prefer normal SQL completion. A forced signal makes that repetition failed and is not cleanup verification.

### Common csql histogram prelude

Where specified, the SQL runner begins:

```sql
;set communication_histogram=yes
;.hist on
;time on
```

and invokes `;.dump_hist` before its final `COMMIT`/`ROLLBACK`. This attaches the required watcher before the workload. The oracle uses `Num_object_locks_waits >= N`, not an exact duration or total acquisitions. Per-transaction csql histograms do not observe daemon threads and do not prove that a specific source branch ran without the accompanying lock dump and SQL state.

---

# Experiment 1 — resource identity, intent hierarchy, mode, owner, lifetime

## Identity and links

- Experiment ID: `experiment-1`
- Central Behavior: `resource-mode-hierarchy`
- Proposed runtime Claim: `CUBRID-C006`
- Book anchor: `chapters/03-interface-and-resources.html#resource-mode-hierarchy`
- Quiz: `quiz-1`
- Owned database: `calocke1f30`
- Instrumentation: not used
- Repetitions: 3

## Question → Hypothesis

Question: 하나의 `SELECT ... FOR UPDATE`가 한 row를 예약할 때 Lock Manager는 이를 하나의 “table lock”으로만 표현하는가, 아니면 class intent resource와 instance resource를 같은 transaction owner에 연결하는가?

Hypothesis:

1. The observer obtains an `IX_LOCK` on class `dba.e1_account` and an `X_LOCK` on the selected instance.
2. A full lock dump shows two different resource keys, both owned by the same observer `tran_index`.
3. The class IX entry communicates the existence of a descendant write lock; it is not a replacement for the row X entry.
4. After `ROLLBACK`, neither target class/instance holder remains.

## Setup SQL

`setup.sql`:

```sql
CREATE TABLE dba.e1_account (
  id INTEGER PRIMARY KEY,
  balance INTEGER NOT NULL
);
INSERT INTO dba.e1_account VALUES (1, 100), (2, 200);
COMMIT;
```

Capture setup directly with csql in a separate `exp1-setup` run. The committed setup transaction must end before observations; otherwise its insertion self-locks are an avoidable confounder.

## Mandatory direct observation

`observe.sql`:

```sql
;set communication_histogram=yes
;.hist on
;time on
SELECT id, balance FROM dba.e1_account WHERE id = 1 FOR UPDATE;
SELECT SLEEP (12.0) AS hold_window;
;.dump_hist
ROLLBACK;
```

Direct runner argv for all repetitions:

```text
[CSQL_ABS_FROM_SNAPSHOT, --CS-mode, --user, dba, --no-auto-commit,
 --input-file, observe.sql, calocke1f30]
```

## Auxiliary lock-dump capture

Start the direct observer asynchronously. `capture-held.sh K`, itself separately captured through `reportctl.py record`, polls full `CUBRID_ABS_FROM_SNAPSHOT lockdb calocke1f30` every 50 ms for at most 8 seconds. It succeeds only when one saved dump contains:

- a `Class = dba.e1_account` resource with an `IX_LOCK` holder;
- an instance-of-`dba.e1_account` resource with an `X_LOCK` holder;
- the same non-lockdb `Tran_index` in both holder lines.

Do not merely grep `IX_LOCK` and `X_LOCK` anywhere in the file. Parse resource blocks, record the class OID, row OID, and holder `tran_index`, and exclude the administrative `lockdb` transaction. Save the successful bytes as `runtime/rK/held.lockdb.txt`.

After the observer exits zero, `capture-post.sh K` runs a full lock dump and fails if the target observer `tran_index` still owns either captured target resource. The table may legitimately have unrelated short-lived schema locks; the oracle is scoped to the recorded target identities.

Run order and stable IDs:

```text
exp1-reset-rK             direct csql reset/verification, separately captured
exp1-observe-rK           mandatory direct csql; start asynchronously
exp1-held-lock-rK         captured lockdb poll while SLEEP holds the transaction
exp1-post-lock-rK         captured full lockdb after observer rollback
```

## Observation, interpretation, controls, alternatives, cleanup

- Observation invariant: two distinct target resource blocks exist at the same time; class holder mode is IX, instance holder mode is X, and the holder `tran_index` matches. Both disappear after rollback.
- Interpretation: this observed case demonstrates multi-granularity intent plus descendant ownership. It does not prove every lock mode, conversion, or escalation branch.
- Positive control: the full dump is taken while the direct transaction is deliberately held open.
- Negative control: the post-rollback dump has no holder for the captured target identities.
- Resource-type control: neither target block is accepted as the self-lock result merely because an X mode exists; Experiment 4 requires the literal transaction-resource label and MVCCID key.
- Alternative “only a class lock exists”: rejected by the separate instance OID/X block.
- Alternative “different transactions own the two locks”: rejected by the same parsed holder `tran_index`.
- Alternative “the dump itself created the target locks”: reject the `lockdb` client `tran_index`; the target observer is the csql process recorded by the direct run.
- Alternative “the histogram proves IX/X”: it does not. The histogram only supplies acquisition/count context; the resource blocks supply type/mode/owner evidence.
- Conversion and escalation are intentionally source/Quiz-backed here. Reconfiguring the shared `lock_escalation` parameter or locking 100,000 rows would add risk/cost without improving the central hierarchy observation.
- Cleanup: run the shared owner-verified cleanup after all repetitions. A dump that cannot correlate the same owner or a target lock surviving observer termination is a hard stop.

## Manifest design

```json
{
  "schema_version": 1,
  "id": "experiment-1",
  "behavior_ids": ["resource-mode-hierarchy"],
  "claim_ids": ["CUBRID-C006"],
  "runner": "observe.sql",
  "runner_sha256": "COMPUTE_AFTER_WRITING",
  "runner_argv": ["ABSOLUTE_CSQL_FROM_SNAPSHOT", "--CS-mode", "--user", "dba", "--no-auto-commit", "--input-file", "observe.sql", "calocke1f30"],
  "run_ids": ["exp1-observe-r1", "exp1-observe-r2", "exp1-observe-r3"],
  "oracle_ko": "같은 transaction owner가 dba.e1_account class resource의 IX_LOCK과 선택된 instance resource의 X_LOCK을 동시에 보유하고, rollback 뒤 두 holder가 모두 사라진다.",
  "controls_ko": "held 상태의 full lock dump가 positive control이고 동일 target identity의 post-rollback 부재가 negative control이다. lockdb client transaction은 제외한다.",
  "alternative_explanations_ko": "mode 이름만 grep하지 않고 resource block과 같은 tran_index를 연결해 우연한 다른 lock 및 lockdb observer를 배제한다. conversion/escalation 전체는 이 runtime case가 증명하지 않는다.",
  "repetitions": 3,
  "cubrid_runtime_only": true,
  "runtime_tools_snapshot": "evidence/runtime-tools-baseline.json",
  "cleanup_verified": "SET_TRUE_ONLY_AFTER_CAPTURED_CLEANUP"
}
```

Design markers must be replaced with real hashes/paths/booleans before writing the actual manifest.

---

# Experiment 2 — incompatible wait, wait-for cycle, deadlock victim, release

## Identity and links

- Experiment ID: `experiment-2`
- Central Behavior: `wait-deadlock-release`
- Proposed runtime Claim: `CUBRID-C016`
- Book anchor: `chapters/06-wait-deadlock-release.html#wait-deadlock-release`
- Quiz: `quiz-2`
- Owned database: `calocke2f30`
- Instrumentation: not used
- Repetitions: 3

## Question → Hypothesis

Question: 두 transaction이 서로 다른 row X lock을 가진 뒤 상대 row를 요청하면 wait-for graph, victim 처리, transaction-level release는 어떤 observable invariant를 남기는가?

Hypothesis:

1. Session A owns row 1 and waits for row 2; session B owns row 2 and waits for row 1.
2. At least one repetition captures two contended instance-resource blocks whose holder/waiter transaction indices form A → B and B → A.
3. With infinite transaction lock timeout, the deadlock detector aborts exactly one actor rather than treating both as successful.
4. The survivor resumes, acquires the released row lock, and commits both of its row changes; the victim's first-row change is also rolled back.
5. Final values are therefore both 10 or both 100, never `(10,100)`, `(100,10)`, or a partial mixture. Target locks disappear afterward.

## Setup and reset SQL

`setup.sql`:

```sql
CREATE TABLE dba.e2_pair (
  id INTEGER PRIMARY KEY,
  value_no INTEGER NOT NULL
);
INSERT INTO dba.e2_pair VALUES (1, 0), (2, 0);
COMMIT;
```

`reset.sql`, executed only after all actor processes from the previous repetition have exited:

```sql
UPDATE dba.e2_pair SET value_no = 0;
COMMIT;
GET TRANSACTION LOCK TIMEOUT;
```

The actor receipts must show infinite wait (`-1`) or the repetition is not the intended unilateral-abort case. Do not change the server-wide deadlock interval or lock timeout parameter.

## Actor SQL and exact action shape

`session-a.sql`:

```sql
;set communication_histogram=yes
;.hist on
;time on
UPDATE dba.e2_pair SET value_no = value_no + 10 WHERE id = 1;
SELECT SLEEP (4.0) AS phase_gate;
UPDATE dba.e2_pair SET value_no = value_no + 10 WHERE id = 2;
;.dump_hist
COMMIT;
```

`session-b.sql`:

```sql
;set communication_histogram=yes
;.hist on
;time on
UPDATE dba.e2_pair SET value_no = value_no + 100 WHERE id = 2;
SELECT SLEEP (4.0) AS phase_gate;
UPDATE dba.e2_pair SET value_no = value_no + 100 WHERE id = 1;
;.dump_hist
COMMIT;
```

`run-deadlock.sh K` is a hashed, separately captured action script. It launches these exact child argv vectors within milliseconds of one another:

```text
[CSQL_ABS_FROM_SNAPSHOT, --CS-mode, --user, dba, --no-auto-commit,
 --error-continue, --input-file, session-a.sql, calocke2f30]
[CSQL_ABS_FROM_SNAPSHOT, --CS-mode, --user, dba, --no-auto-commit,
 --error-continue, --input-file, session-b.sql, calocke2f30]
```

It saves PIDs, stdout, stderr, and child exit codes under `runtime/rK/`. It returns zero only when the sorted child statuses are exactly `0 1`, one actor output contains the unilateral-deadlock-abort error class, the other reports both updates/commit successful, and neither process remains. It must not choose in advance which actor is the victim.

`--error-continue` is required so a victim csql can finish its file and preserve the histogram/error receipt; csql's failure count remains its nonzero exit status. If this revision returns a different exact status after one failed statement, determine it with source/runtime evidence and update the action predicate rather than accepting arbitrary nonzero values.

## Concurrent cycle capture

Before starting `run-deadlock.sh`, start a separately captured `capture-cycle.sh K` asynchronously. It polls `CUBRID_ABS_FROM_SNAPSHOT lockdb -c calocke2f30` every 20 ms for at most 12 seconds and saves every candidate under `runtime/rK/scan-N.txt` outside the source worktree.

It succeeds when one dump has two different `dba.e2_pair` instance-resource blocks such that:

- block R1: holder transaction A, X waiter transaction B;
- block R2: holder transaction B, X waiter transaction A;
- both transactions are csql actors, not the `lockdb` client.

Because the configured detector interval is short, the exact two-edge state may be transient. Run three repetitions. At least one valid two-edge dump is required for the report's direct wait-for-cycle statement. If all three miss the transient but actor/event/final-state evidence succeeds, preserve that as a limitation and do not fabricate the cycle dump; redesign or mark that runtime subclaim blocked.

The owned server's event log is supporting evidence. Record its exact pre-action size/inode and copy only the appended block for this owned database after the actors finish. It should contain a new `DEADLOCK` event because `lock_detect_local_deadlock` calls `event_log_start("DEADLOCK")`. Do not grep unrelated server logs or treat a pre-existing event as this run.

## Mandatory direct observation after resolution

`observe.sql`:

```sql
;time on
SELECT id, value_no FROM dba.e2_pair ORDER BY id;
SELECT CASE
         WHEN MIN (value_no) = MAX (value_no)
              AND MIN (value_no) IN (10, 100)
           THEN 1
         ELSE 0
       END AS atomic_survivor_invariant
FROM dba.e2_pair;
COMMIT;
```

Direct runner argv:

```text
[CSQL_ABS_FROM_SNAPSHOT, --CS-mode, --user, dba, --no-auto-commit,
 --input-file, observe.sql, calocke2f30]
```

The mandatory run must exit zero and print `atomic_survivor_invariant = 1`. A separately captured verifier may parse the captured stdout and fail on any other value; it must not replace the direct csql run.

Run order and stable IDs:

```text
exp2-reset-rK               direct csql
exp2-cycle-watch-rK         captured shell/lockdb poll; start asynchronously
exp2-actors-rK              captured hashed script; starts two csql children
exp2-observe-rK             mandatory direct csql after actors resolve
exp2-output-check-rK        captured parser of actor/direct outputs
exp2-post-lock-rK           captured full lockdb, no target actor holds/waits
```

## Observation, interpretation, controls, alternatives, cleanup

- Central oracle: one and only one actor fails with the deadlock-victim class; the other resumes and commits; the direct final invariant is 1; no target lock remains.
- Strong cycle evidence: a saved two-resource dump contains reciprocal holder/waiter `tran_index` edges. Resource iteration order is unspecified and must not be an oracle.
- Histogram support: each actor that reached suspension should show at least one `Num_object_locks_waits`; exact wait microseconds and which actor the detector chooses are nondeterministic.
- Positive control: reciprocal second updates create a cycle.
- Negative/control comparison: a final partial mixture would mean statement/transaction cleanup or the experiment interpretation is wrong and hard-stops the run.
- Alternative “one statement timed out normally”: actor `GET TRANSACTION LOCK TIMEOUT` must show infinite wait, the owned event append must be a `DEADLOCK` block, and the victim error class must match deadlock abortion.
- Alternative “both transactions committed serially”: rejected by exactly one failed actor and the event/cycle evidence.
- Alternative “the first update of the victim leaked”: rejected by both final values being identical and from only one actor's delta.
- Alternative “cycle dump proves victim policy”: it does not. The dump proves reciprocal waits; the actor/event result proves one observed resolution. The youngest-victim rule remains source-backed and should not be generalized from actor names.
- Observer effect: aggressive `lockdb` polling adds admin connections and hash-table traversal. It may miss the transient or perturb timing; it cannot create the reciprocal row ownership pattern itself.
- Cleanup: after all actors/watchers exit, owner-verified stop/delete. Any unvalidated csql/watch process, final partial value, missing victim evidence, or residual target lock is a hard stop.

## Manifest design

```json
{
  "schema_version": 1,
  "id": "experiment-2",
  "behavior_ids": ["wait-deadlock-release"],
  "claim_ids": ["CUBRID-C016"],
  "runner": "observe.sql",
  "runner_sha256": "COMPUTE_AFTER_WRITING",
  "runner_argv": ["ABSOLUTE_CSQL_FROM_SNAPSHOT", "--CS-mode", "--user", "dba", "--no-auto-commit", "--input-file", "observe.sql", "calocke2f30"],
  "run_ids": ["exp2-observe-r1", "exp2-observe-r2", "exp2-observe-r3"],
  "oracle_ko": "상호 X wait cycle에서 정확히 한 transaction이 deadlock victim으로 실패하고 survivor가 재개되어 두 행 모두 자기 delta로 commit한다. victim의 선행 변경도 rollback되고 모든 target lock이 사라진다.",
  "controls_ko": "infinite lock timeout과 reciprocal second update가 deadlock 조건을 고정한다. final two-row equality 및 exactly-one actor failure가 partial cleanup과 단순 직렬 성공을 배제한다.",
  "alternative_explanations_ko": "전용 perf counter가 없으므로 reciprocal lockdb block, owned DEADLOCK event, victim 오류, survivor 결과를 함께 요구한다. detector timing과 victim identity는 일반화하지 않는다.",
  "repetitions": 3,
  "cubrid_runtime_only": true,
  "runtime_tools_snapshot": "evidence/runtime-tools-baseline.json",
  "cleanup_verified": "SET_TRUE_ONLY_AFTER_CAPTURED_CLEANUP"
}
```

---

# Experiment 3 — MVCC snapshot read versus locked read and writer protection

## Identity and links

- Experiment ID: `experiment-3`
- Central Behavior: `mvcc-lock-policy`
- Proposed runtime Claim: `CUBRID-C028`
- Book anchor: `chapters/07-mvcc-lock-policy.html#mvcc-lock-policy`
- Quiz: `quiz-3`
- Owned database: `calocke3f30`
- Instrumentation: not used
- Repetitions: 3

## Question → Hypothesis

Question: MVCC가 plain read에 과거 committed version을 제공한다면, 왜 `SELECT ... FOR UPDATE`와 UPDATE에는 여전히 logical row lock이 필요한가?

Hypothesis:

1. Holder T1 updates row 1 from 100 to 900 without commit and holds an instance X lock.
2. Observer T2's plain `SELECT` of the same row completes before its locked read and returns committed value 100, not uncommitted 900.
3. T2's `SELECT ... FOR UPDATE` then appears as an X waiter on that same instance resource.
4. After T1 rolls back, T2 resumes, re-reads/locks value 100, updates it to 101, and commits.
5. This separates visibility (which version may be read) from exclusion (who may establish the next write).

## Setup and holder

`setup.sql`:

```sql
CREATE TABLE dba.e3_account (
  id INTEGER PRIMARY KEY,
  balance INTEGER NOT NULL
);
INSERT INTO dba.e3_account VALUES (1, 100), (2, 200);
COMMIT;
```

`reset.sql`:

```sql
UPDATE dba.e3_account
   SET balance = CASE id WHEN 1 THEN 100 ELSE 200 END;
COMMIT;
```

`holder.sql`, a separately captured direct csql run started asynchronously:

```sql
;time on
UPDATE dba.e3_account SET balance = 900 WHERE id = 1;
SELECT SLEEP (12.0) AS hold_window;
ROLLBACK;
```

Holder argv:

```text
[CSQL_ABS_FROM_SNAPSHOT, --CS-mode, --user, dba, --no-auto-commit,
 --input-file, holder.sql, calocke3f30]
```

Before starting the observer, `wait-holder.sh K` polls full `lockdb` until the target row instance has an X holder and records its OID and holder `tran_index`.

## Mandatory direct observation

`observe.sql`:

```sql
;set communication_histogram=yes
;.hist on
;time on
SELECT 'plain_same' AS phase, balance FROM dba.e3_account WHERE id = 1;
SELECT 'plain_other' AS phase, balance FROM dba.e3_account WHERE id = 2;
SELECT 'locked_same' AS phase, balance FROM dba.e3_account WHERE id = 1 FOR UPDATE;
UPDATE dba.e3_account SET balance = balance + 1 WHERE id = 1;
;.dump_hist
COMMIT;
SELECT 'final' AS phase, balance FROM dba.e3_account WHERE id = 1;
```

Direct runner argv:

```text
[CSQL_ABS_FROM_SNAPSHOT, --CS-mode, --user, dba, --no-auto-commit,
 --input-file, observe.sql, calocke3f30]
```

Start it asynchronously after holder readiness. `capture-wait.sh K` polls `cubrid lockdb -c calocke3f30` and succeeds only when the previously recorded target instance block contains T1 X holder and a different csql transaction's X waiter. Save the block and both transaction indices.

Run order and stable IDs:

```text
exp3-reset-rK
exp3-holder-rK             direct csql, asynchronous
exp3-holder-ready-rK       captured full-lock poll
exp3-observe-rK            mandatory direct csql, asynchronous
exp3-contention-rK         captured -c lock dump
exp3-post-lock-rK          no captured target holder/waiter after both end
```

## Observation, interpretation, controls, alternatives, cleanup

- SQL oracle: `plain_same=100`, `plain_other=200`, `locked_same=100`, `final=101`.
- Concurrency oracle: while the direct observer is pending, the same instance resource has T1 X holder and T2 X waiter; observer histogram has `Num_object_locks_waits >= 1`.
- The plain statement's csql timing should be materially smaller than the locked statement's in this controlled case, but no numeric cutoff is part of the invariant.
- Positive lock control: `SELECT ... FOR UPDATE` on row 1 waits.
- Negative visibility control: plain read on the same row returns 100 while T1 is still active; row 2 verifies the session remains responsive on an unrelated row.
- Outcome control: holder rollback means the locked read must re-evaluate against the committed row, not accept the uncommitted 900.
- Alternative “plain read secretly waited for T1”: the observer must already be visible as the later X waiter while holder is still active, and its ordered output/timing shows both prior plain reads completed.
- Alternative “only an index/page latch blocked”: `lockdb -c` explicitly shows an instance transaction-lock waiter; the wait counter increment site is the Lock Manager suspend state. Runtime does not directly show every latch release.
- Alternative “MVCC eliminates all locks”: class/schema locks are outside the negative instance-lock statement, and locked read/DML here visibly require X. The experiment must not be described as globally lock-free reading.
- Alternative “the final value proves the exact reevaluation function”: it is consistent with and behaviorally requires a post-wait decision, but the exact `locator_mvcc_reev_cond_and_assignment` call remains source-backed.
- Cleanup: wait for holder/observer, require both zero, require post-lock absence, then owned DB cleanup. If plain read returns 900, observer finishes its locked statement before contention capture, or final is not 101, hard-stop.

## Manifest design

```json
{
  "schema_version": 1,
  "id": "experiment-3",
  "behavior_ids": ["mvcc-lock-policy"],
  "claim_ids": ["CUBRID-C028"],
  "runner": "observe.sql",
  "runner_sha256": "COMPUTE_AFTER_WRITING",
  "runner_argv": ["ABSOLUTE_CSQL_FROM_SNAPSHOT", "--CS-mode", "--user", "dba", "--no-auto-commit", "--input-file", "observe.sql", "calocke3f30"],
  "run_ids": ["exp3-observe-r1", "exp3-observe-r2", "exp3-observe-r3"],
  "oracle_ko": "active writer가 900을 만든 동안 plain SELECT는 committed 100을 읽지만 같은 row의 SELECT FOR UPDATE는 instance X waiter가 된다. holder rollback 뒤 locked read는 100을 얻고 observer update가 101을 commit한다.",
  "controls_ko": "같은 row plain read와 다른 row plain read가 negative controls이고 같은 row locked read가 positive wait control이다. rollback outcome이 post-wait 재판정을 요구한다.",
  "alternative_explanations_ko": "statement timing만이 아니라 동일 instance의 X holder/waiter lockdb block과 wait counter를 함께 사용한다. exact source function 및 모든 MVCC/isolation 조합은 이 case가 증명하지 않는다.",
  "repetitions": 3,
  "cubrid_runtime_only": true,
  "runtime_tools_snapshot": "evidence/runtime-tools-baseline.json",
  "cleanup_verified": "SET_TRUE_ONLY_AFTER_CAPTURED_CLEANUP"
}
```

---

# Experiment 4 — MVCCID self-lock inserter/observer rendezvous

## Identity and links

- Experiment ID: `experiment-4`
- Central Behavior: `mvccid-self-lock-rendezvous`
- Proposed runtime Claim: `CUBRID-C038`
- Book anchor: `chapters/08-mvccid-self-lock.html#mvccid-self-lock-rendezvous`
- Quiz: `quiz-4`
- Owned database: `calocke4f30`
- Instrumentation: not used
- Repetitions: 3

## Question → Hypothesis

Question: 아직 끝나지 않은 inserter의 unique key나 FK parent를 본 checker는 row OID가 아니라 어떤 identity/mode로 기다리며, inserter 종료 뒤 무엇을 다시 판단하는가?

Hypothesis:

1. Each inserter holds X on a distinct `LOCK_RESOURCE_TRANSACTION` keyed by its full MVCCID.
2. The same-unique-key checker and the FK checker appear, sequentially, as S waiters on those two resources.
3. Unique holder rollback makes the observer's same-key insert succeed after re-read.
4. FK holder commit makes the observer's child insert succeed after re-read.
5. The observer releases each temporary S grant, and transaction end removes each inserter resource.

## Setup and reset

`setup.sql`:

```sql
CREATE TABLE dba.e4_uq (
  key_no INTEGER PRIMARY KEY,
  note_text VARCHAR(40)
);
CREATE TABLE dba.e4_parent (
  id INTEGER PRIMARY KEY
);
CREATE TABLE dba.e4_child (
  id INTEGER PRIMARY KEY,
  parent_id INTEGER,
  CONSTRAINT fk_e4_parent FOREIGN KEY (parent_id)
    REFERENCES dba.e4_parent (id)
);
INSERT INTO dba.e4_parent VALUES (1);
COMMIT;
```

`reset.sql`:

```sql
DELETE FROM dba.e4_child;
DELETE FROM dba.e4_uq;
DELETE FROM dba.e4_parent WHERE id <> 1;
COMMIT;
```

## Inserter holders

`holder-a.sql`:

```sql
INSERT INTO dba.e4_uq VALUES (100, 'holder');
SELECT SLEEP (12.0) AS hold_window;
ROLLBACK;
```

`holder-b.sql`:

```sql
INSERT INTO dba.e4_parent VALUES (200);
SELECT SLEEP (24.0) AS hold_window;
COMMIT;
```

Start both as separately captured direct csql runs with `--no-auto-commit`. `wait-two-holders.sh K` polls full `lockdb calocke4f30` until it sees at least two distinct `Transaction self-lock (inserter MVCCID = N)` blocks, each with an X holder. Save the exact two MVCCIDs and holder transaction indices before starting the observer.

## Mandatory direct observation

`observe.sql`:

```sql
;set communication_histogram=yes
;.hist on
;time on
INSERT INTO dba.e4_uq VALUES (101, 'control');
INSERT INTO dba.e4_child VALUES (1, 1);
INSERT INTO dba.e4_uq VALUES (100, 'observer');
INSERT INTO dba.e4_child VALUES (2, 200);
SELECT key_no, note_text FROM dba.e4_uq ORDER BY key_no;
SELECT id, parent_id FROM dba.e4_child ORDER BY id;
;.dump_hist
COMMIT;
```

Direct runner argv:

```text
[CSQL_ABS_FROM_SNAPSHOT, --CS-mode, --user, dba, --no-auto-commit,
 --input-file, observe.sql, calocke4f30]
```

`capture-two-waits.sh K` runs concurrently with the direct observer and polls `cubrid lockdb -c calocke4f30`. It records a resource only when a block:

- has the literal `Transaction self-lock (inserter MVCCID = N)` label;
- has X total/holder mode and S waiter mode;
- contains one holder and at least one waiter;
- matches one of the two readiness MVCCIDs.

It must capture two distinct MVCCIDs, which may appear in separate dumps because the observer reaches the unique and FK waits sequentially. A compact candidate loop is:

```bash
seen="runtime/r${rep}/seen-mvccids.txt"
: >"$seen"
for attempt in $(seq 1 800)
do
  scan="runtime/r${rep}/contention-${attempt}.txt"
  CUBRID_ABS_FROM_SNAPSHOT lockdb -c calocke4f30 >"$scan"
  # Parse complete transaction-resource blocks; for each valid X-holder/S-waiter block,
  # record a readiness-listed MVCCID only once and copy the complete source dump.
  test "$(wc -l <"$seen")" -ge 2 && exit 0
  sleep 0.05
done
exit 1
```

The actual parser must operate on complete blocks; the comments above are design prose and should not be answer-bearing comments in a learner Quiz script.

After both holders and observer exit, `verify-release.sh K` runs full `lockdb`, reads the exact recorded MVCCIDs, and fails if either transaction resource remains. It also verifies final rows `(100,'observer')`, `(101,'control')`, child `(1,1)`, and child `(2,200)` through a separate direct csql result.

Run order and stable IDs:

```text
exp4-reset-rK
exp4-holder-a-rK             direct csql, asynchronous
exp4-holder-b-rK             direct csql, asynchronous
exp4-holders-ready-rK        captured full lockdb
exp4-observe-rK              mandatory direct csql, asynchronous
exp4-two-waits-rK            captured -c lockdb poll
exp4-release-check-rK        captured full lockdb and exact-ID absence
```

## Observation, interpretation, controls, alternatives, cleanup

- Central lock oracle: two distinct MVCCID-keyed transaction resource blocks, each with inserter X holder and observer S waiter.
- SQL oracle: unique conflict succeeds after the holder rolls back; FK insert succeeds after the parent holder commits; control rows also succeed.
- Histogram support: observer `Num_object_locks_waits >= 2`. Do not demand exactly 2 because unrelated internal object waits are possible.
- Positive controls: same unique key 100 and uncommitted parent 200.
- Negative controls: different unique key 101 and already committed parent 1 should not create an S waiter on either holder MVCCID.
- Resource-type control: holder/waiter `tran_index` values must be recorded separately from resource MVCCID; numeric equality is neither expected nor meaningful.
- Alternative “a per-row X lock caused the wait”: rejected for the observed waits by the literal transaction-resource label and MVCCID key. This does not prove no fallback row lock exists in every exceptional path.
- Alternative “a B-tree page latch caused the wait”: the runtime dump proves a transaction-lock suspension; source proves the latch release/restart sequence. Runtime without instrumentation does not expose each unfix call.
- Alternative “wakeup alone determines the answer”: the two chosen outcomes differ. Rollback removes the unique conflict; commit creates the FK parent. Success therefore requires evaluating post-wait state, although the exact restart-from-root function remains source-backed.
- Alternative “self-lock is a special new mode”: the observed modes are ordinary X and S on a different resource identity. The generic mode machinery is reused.
- Performance limitation: one or two rows do not quantify the per-row lock-count saving. The Book may state the source algorithm and use this Experiment only for identity/protocol behavior, not a measured scaling ratio.
- Cleanup: wait for all three csql runs, require zero, require exact resource disappearance, then owner-verified DB deletion. Missing one of the two blocks, a holder ending before readiness, or a residual recorded MVCCID is a hard stop.

## Manifest design

```json
{
  "schema_version": 1,
  "id": "experiment-4",
  "behavior_ids": ["mvccid-self-lock-rendezvous"],
  "claim_ids": ["CUBRID-C038"],
  "runner": "observe.sql",
  "runner_sha256": "COMPUTE_AFTER_WRITING",
  "runner_argv": ["ABSOLUTE_CSQL_FROM_SNAPSHOT", "--CS-mode", "--user", "dba", "--no-auto-commit", "--input-file", "observe.sql", "calocke4f30"],
  "run_ids": ["exp4-observe-r1", "exp4-observe-r2", "exp4-observe-r3"],
  "oracle_ko": "unique와 FK checker가 서로 다른 inserter MVCCID transaction resource에서 S waiter가 되고 각 inserter는 X holder로 보인다. rollback/commit 뒤 checker가 재판정해 성공하고 두 resource가 사라진다.",
  "controls_ko": "다른 unique key와 committed parent는 negative controls이고 같은 key와 uncommitted parent는 positive controls이다. exact MVCCID로 post-release 부재를 검증한다.",
  "alternative_explanations_ko": "literal transaction self-lock label과 X/S block으로 row OID lock 및 latch-only 설명을 구분한다. latch release 함수, 모든 fallback, lock-count scaling은 source 또는 별도 측정 범위다.",
  "repetitions": 3,
  "cubrid_runtime_only": true,
  "runtime_tools_snapshot": "evidence/runtime-tools-baseline.json",
  "cleanup_verified": "SET_TRUE_ONLY_AFTER_CAPTURED_CLEANUP"
}
```

---

# Korean mechanism Quiz designs

Every Quiz uses its own fixed database name and owner marker; it never reuses an Experiment database. `quiz.md` and `answer.md` are Korean. Canonical English terms, SQL, identifiers, commands, and paths remain English. Filenames and script comments must be neutral: do not reveal `IX`, `X`, victim identity, expected value, or self-lock answer before the learner predicts it.

## Quiz 1 — 두 resource를 한 transaction으로 연결하기

### Links and progression

- Quiz ID: `quiz-1`
- Central Behavior: `resource-mode-hierarchy`
- Chapter/anchor: `chapters/03-interface-and-resources.html#resource-mode-hierarchy`
- Claim set: the finalized direct CUBRID Claims from this behavior, including the runtime Claim that consumes `experiment-1`
- Owned database: `qalockq1f30`
- Expected time: 20–25 minutes
- Progression: predict → run locked read → annotate full lock dump → apply compatibility/conversion matrix → reason about escalation trade-off → teach back Interface obligations.

### Runnable artifact shape

Include `setup.sql`, neutral `session-a.sql`, `inspect.sh`, `post.sql`, and owner-checked `cleanup.sh`.

`session-a.sql` contains only:

```sql
;time on
SELECT id, balance FROM dba.q1_account WHERE id = 1 FOR UPDATE;
SELECT SLEEP (12.0);
ROLLBACK;
```

The learner starts it with direct csql `--no-auto-commit`, runs `cubrid lockdb qalockq1f30`, then runs the post dump. `inspect.sh` captures bytes but does not label a mode as correct.

### `quiz.md` questions without answer leakage

1. 실행 전에 class와 row 각각에 대해 `resource key`, 예상 mode, owner identity, lifetime을 빈 표에 적으라.
2. full lock dump에서 같은 `tran_index`가 가진 모든 target resource block을 표시하고, class OID와 instance OID가 왜 다른 key인지 설명하라.
3. class entry가 row entry를 대체하지 않는 이유를 “상위 granularity에서 충돌을 미리 판단”이라는 caller obligation 관점으로 설명하라.
4. Book의 `lock_Comp` 표를 이용해 두 transaction이 서로 다른 row를 `FOR UPDATE`할 때 class 단계에서 서로 막히는지 예측하라.
5. 같은 transaction이 class S를 이미 가진 상태에서 IX를 요청할 때 conversion 결과를 구하고, 왜 단순히 “더 큰 mode”라고 부르면 잘못인지 설명하라.
6. row 수가 escalation threshold를 넘을 때 memory/lookup cost와 concurrency가 어떻게 trade off 되는지 설계 선택을 적으라. 실제 Quiz는 shared parameter를 바꾸지 않는다.
7. rollback 뒤 사라진 것과 남을 수 있는 unrelated schema/admin lock을 구분해 teach-back하라.

### `answer.md` causal content

The separate answer explains the observed class IX + instance X with one owner, mode-matrix direction, `S + IX -> SIX`, transaction lifetime release, and why escalation is policy rather than a new resource type. Common misconceptions: “IX means the row itself is exclusively locked,” “OID is transaction ID,” “mode numeric order alone defines strength,” and “post-dump must be globally empty.” State that one locked read does not measure escalation or all conversion paths. Add PostgreSQL/MySQL comparison reasoning only from the Book, never by requiring their servers.

## Quiz 2 — wait-for cycle에서 원자성과 victim cleanup 설명하기

### Links and progression

- Quiz ID: `quiz-2`
- Central Behavior: `wait-deadlock-release`
- Chapter/anchor: `chapters/06-wait-deadlock-release.html#wait-deadlock-release`
- Owned database: `qalockq2f30`
- Expected time: 30–40 minutes
- Progression: predict two owners → draw wait-for graph → run two actors → classify victim/survivor → verify final transaction atomicity → redesign timeout/deadlock policy.

### Runnable artifact shape

Use neutral `session-a.sql`, `session-b.sql`, `run.sh`, `inspect.sh`, and `verify.sql`, based on Experiment 2 but with table `dba.q2_pair` and deltas chosen in the Quiz text. Scripts return nonzero on unexpected child-status sets or final invariant failure and clean partial resources only after owner validation. No script comment says which actor should win.

### `quiz.md` questions

1. Before execution draw two instance resources and two transaction nodes after each first UPDATE, then add the second requests.
2. Predict all permitted final pairs, not one victim identity. Explain why scheduler order may change the victim but not the atomic invariant.
3. Run the actors and `lockdb -c`; reconstruct directed edges using holder/waiter `tran_index` rather than file order.
4. Identify which evidence distinguishes deadlock victim abort from a finite ordinary lock timeout.
5. Explain why releasing only the victim's current waiter entry is insufficient; connect abort to its earlier held row lock and `lock_unlock_all`.
6. If final rows contain one delta from each actor, list which atomicity/cleanup invariant was violated.
7. Using the Book, compare how CUBRID, PostgreSQL, and InnoDB represent/resolve the same logical cycle and label only genuinely matching axes.
8. Propose a conformance test that accepts either victim but rejects partial state and a leaked holder.

### `answer.md` causal content

Explain reciprocal WFG edges, one observed unilateral victim, survivor wakeup, statement error versus whole transaction rollback, and final values from one transaction only. Common mistakes: assuming actor B must be the victim, reading `lockdb` order as wait order, treating timeout and deadlock as synonyms, or checking only that one csql returned nonzero. Limitations: three runs do not prove starvation freedom, every victim tie-break, or every interrupt/shutdown path.

## Quiz 3 — “읽을 수 있음”과 “다음 writer가 될 수 있음” 분리하기

### Links and progression

- Quiz ID: `quiz-3`
- Central Behavior: `mvcc-lock-policy`
- Chapter/anchor: `chapters/07-mvcc-lock-policy.html#mvcc-lock-policy`
- Owned database: `qalockq3f30`
- Expected time: 25–30 minutes
- Progression: predict versions/waits → run active writer → compare plain and locked reads → inspect row waiter → explain re-evaluation → map policy seams.

### Runnable artifact shape

Use neutral `session-a.sql` for an uncommitted update followed by `SLEEP`/rollback, `session-b.sql` for the ordered plain/locked/update sequence, `inspect.sh` for the contended dump, and `verify.sql` for final values. The script contains no comment such as “plain does not wait.”

### `quiz.md` questions

1. Fill a before-run table for each statement: version expected, instance-lock request, can wait, and why.
2. Run the case and use statement order, csql timing, and the saved instance holder/waiter block to identify the first actual suspend point.
3. Explain why returning committed 100 while 900 is uncommitted is a visibility rule, not evidence that no locks exist anywhere in the statement.
4. Explain why `SELECT ... FOR UPDATE` must re-check the row after wakeup rather than return the version evaluated before waiting.
5. Replace holder rollback with commit as a thought experiment. Predict what value/qualification the locked read must reconsider; do not run unless a separate expected-output Quiz variant is provided.
6. Place each responsibility at the correct seam: MVCC snapshot, class intent lock, row X transaction lock, page latch.
7. Explain why “MVCC lock” is a policy composition, not a unique `MVCC_LOCK` enum mode.
8. Compare nearest PostgreSQL and InnoDB mechanisms from the Book and name at least one partial analogy rather than forcing equivalence.

### `answer.md` causal content

Explain committed-version visibility, plain MVCC instance `NULL_LOCK`, locked-read class IX/row X, suspend/wakeup, predicate/version re-evaluation, and final 101 after rollback. Common mistakes: calling MVCC “lock free” without granularity, confusing page latch with transaction lock, assuming the pre-wait tuple stays valid, and claiming one READ COMMITTED case covers SERIALIZABLE. State exactly what the runtime output does not prove.

## Quiz 4 — MVCCID rendezvous를 row lock과 구분하고 재구현하기

### Links and progression

- Quiz ID: `quiz-4`
- Central Behavior: `mvccid-self-lock-rendezvous`
- Chapter/anchor: `chapters/08-mvccid-self-lock.html#mvccid-self-lock-rendezvous`
- Owned database: `qalockq4f30`
- Expected time: 35–45 minutes
- Progression: predict unique conflict → identify transaction resource → follow X/S lifecycle → infer required re-check → compare per-row alternative → write a small reimplementation contract.

### Runnable artifact shape

For a compact Quiz use one unique case: `session-a.sql` inserts key 100, sleeps, and rolls back; `session-b.sql` inserts control 101 then conflicting 100; `inspect.sh` captures contention; `verify.sql` lists final keys and confirms exact recorded MVCCID absence. Keep filenames/mode comments neutral. An optional advanced variant adds the FK commit case from Experiment 4.

### `quiz.md` questions

1. Before execution predict whether the wait target key is row OID, class OID, `tran_index`, transaction ID, or MVCCID, and state what observation would falsify the prediction.
2. In the dump record resource MVCCID, holder `tran_index`, waiter `tran_index`, holder mode, and waiter mode in separate columns.
3. Explain why the inserter calls this a self-lock even though another transaction later waits on it.
4. Explain why ordinary X/S compatibility is sufficient and why introducing a special `MVCC_LOCK` mode is unnecessary.
5. After holder rollback, explain why S grant/wakeup alone cannot justify inserting key 100; list the state that must be re-read.
6. Derive the invariant `observable INSID => matching X self-lock held` and explain what race appears if INSID publication precedes X acquisition.
7. Derive the release-order requirement `publish inactive -> unlock -> wake/recheck`. Explain what an observer could mis-conclude if unlock happened first.
8. Compare two designs: one X per appended row versus one X per inserter MVCCID. Discuss resource count, waiter fan-in, false contention, cleanup, 2PC/fallback, and failure handling.
9. Using the Book only, compare PostgreSQL transaction-ID/speculative insertion and InnoDB transaction/record wait responsibilities. Mark `partial analogy` where resource identity or caller Interface differs.
10. Write pseudocode for `ensure_self_lock`, `wait_for_inserter`, and transaction-end release, including error branches and re-check, without reopening source.

### `answer.md` causal content

Explain MVCCID-keyed `LOCK_RESOURCE_TRANSACTION`, inserter X, checker S, immediate S release, active-state verification, B-tree restart, and transaction-end ordering. Common mistakes: equating MVCCID with `tran_index`, calling self-lock a self-deadlock, assuming the S lock protects the key permanently, or concluding the optimization removes all row locks. State that the small runtime case demonstrates rendezvous identity/behavior, not a quantitative scalability gain or every 2PC/subtransaction path.

## Quiz safety and self-check checklist

For all four Quizzes the main agent must:

1. Use only the pinned CUBRID runtime plus shell tools; PostgreSQL/MySQL servers are never dependencies.
2. Create a fixed Quiz-owned database only after collision checks; verify owner marker before cleanup.
3. Save scripts before running them; use `bash -n` for shell scripts and direct csql `--input-file` for SQL observations.
4. Ensure every concurrent script validates child PIDs/cmdlines and exits nonzero on an unexpected invariant.
5. Make reset idempotent only inside a positively owned database. Never use broad filesystem deletion or global service stop.
6. Run each Quiz at least once and confirm `answer.md` matches the actual pinned build. Run concurrency-sensitive Quizzes three times or state scheduler variability.
7. Read `quiz.md` as a learner and remove mode/value answers from filenames, SQL comments, grep predicates shown before prediction, and expected-output filenames.
8. Keep answer and limitations separate. A correct final value without causal lock evidence is not a complete answer.

## Unknowns and feasibility risks to preserve

1. The exact installed absolute `csql`/`cubrid` paths are intentionally unknown until the baseline runtime snapshot. Actual manifests/scripts must contain the sealed literal paths and their hashes, not packet placeholders.
2. The baseline build may be blocked by user-owned live CUBRID processes. This requires authorization; it is not permission to stop them.
3. Deadlock cycle visibility is transient relative to the default detector interval. Three repetitions and early aggressive polling reduce the gap but do not eliminate observer effects. Do not claim a captured two-edge dump if none was captured.
4. `lockdb` output contains localized message-catalog text for many resource lines, while the new transaction self-lock label is literal English in source. Parsers should use structural blocks and saved raw output, and the main agent must manually inspect the first successful sample before trusting automation.
5. `Num_object_locks_waits` includes any Lock Manager object-resource suspension in the watched transaction, including transaction self-locks. It cannot identify the waited resource by itself; always pair it with lock dump and SQL order.
6. `lockdb` itself is an administrative client and perturbs transaction/resource enumeration. Filter its `tran_index`; do not require the whole dump to be empty.
7. Experiment 3 tests the default isolation/runtime configuration captured by the snapshot. It does not establish every isolation anomaly, serializable predicate locking, DDL behavior, or non-MVCC class path.
8. Experiment 4 behaviorally requires post-wait decisions but cannot directly observe every page unfix, active-bit publication instruction, or B-tree restart call. Keep those as source-confirmed Claims with runtime-consistent support.
9. Experiment 4 does not measure the lock-entry reduction at scale. Do not convert the source design motivation into a measured performance claim.
10. Fixed `SLEEP` windows are feasibility aids, not timing oracles. If debug startup consumes the window before readiness, hard-stop and redesign the gate rather than silently increasing delays until a desired output appears.
11. The proposed runtime Claim numbers assume the last CUBRID Claim in each reserved behavior range is suitable for runtime evidence. The main agent owns final Claim semantics and must update manifests atomically if the ledger assigns differently.

## Handoff to the main agent

Before implementation, validate each SQL statement against the sealed binary and reopen the cited complete functions. Create actual Experiment/Quiz files only from the main agent. Hash every runner after its final bytes are written, record setup/action/observation/cleanup separately, bind direct csql argv exactly, and promote no runtime Claim until raw output, repetitions, alternatives, and owner-verified cleanup all agree.

