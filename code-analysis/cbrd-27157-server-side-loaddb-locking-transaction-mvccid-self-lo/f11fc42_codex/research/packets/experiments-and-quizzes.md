# Role 4 packet — CUBRID Experiments and Korean Quizzes

## Packet identity

- Role: Experiment and Quiz Designer
- Topic: `CBRD-27157 server-side loaddb locking, transaction MVCCID self-lock, and BU_LOCK`
- Declared Scope digest: `f07826ef64e37143f055cdf4814be26d965d9bc531421f21439871475722fa5b`
- CUBRID revision: `f11fc42594732c263d8f10101f9df73a21346ee9` (`WORKTREE`; dirty-state details are frozen in `provenance.json`)
- PostgreSQL revision: `fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc`
- MySQL revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- Relevant CUBRID history: CBRD-23375 `1994f0be34e919d3819c92eef39837f00d98827f`, CBRD-26942 `741734a8f3785a3e2a678bb52e289000c2261b6f`, CBRD-27157 fix `8bcfd7dd278cbe2b16a064bce4105e68cf80d6a1`
- Timestamp (UTC): `2026-08-11T07:05:55Z`
- Output contract: this packet is a read-only design. No Experiment was executed, no source was instrumented, and no Book/Quiz/report JSON file was changed by this role.

## Scope interpretation

The three central behaviors are tested separately so that a learner does not confuse a class object lock with a transaction-keyed rendezvous lock.

| Experiment | Central behavior | Main observable | What it distinguishes |
|---|---|---|---|
| `experiment-1` | `lock-resource-owner-lifecycle` | A class resource has a session-owned `BU_LOCK`; a normal DML requester waits; after the loader session ends the same DML is immediate | resource, owner, mode, waiter, lifetime; class `BU_LOCK` versus a transaction resource |
| `experiment-2` | `mvccid-self-lock-rendezvous` | `lockdb -c` prints `Transaction self-lock (inserter MVCCID = ...)` with an `X_LOCK` holder and an `S_LOCK` waiter; unique/FK statements resume and re-check after the inserter ends | MVCCID key versus row/class OID, inserter X versus checker S, wait/re-check/release |
| `experiment-3` | `loaddb-oos-regression` | Fixed debug build completes `loaddb -C`, remains connectable, preserves values, and reports an OOS file only for the 5,000-byte case | ordinary loaddb control versus OOS lazy-file path; fixed end-to-end behavior, not merely an assert-free release build |

The experiments require only the pinned CUBRID build and POSIX shell utilities. PostgreSQL and MySQL servers are not used. The comparison questions in the Quizzes must be answered from the Book's source-backed comparison chapters.

## Source seams used to make the designs discriminating

The main agent should validate the Claim ledger against these complete functions before attaching runtime run IDs.

| Behavior | File and symbol at the pinned revision | Design consequence |
|---|---|---|
| `BU_LOCK` compatibility | `src/transaction/lock_table.c`, `lock_Comp` | `BU_LOCK` is compatible with `BU_LOCK` and `SCH_S_LOCK`, but conflicts with ordinary `IS/S/IX/SIX/X` requests. Experiment 1 uses normal DML rather than assuming that every operation conflicts. |
| loaddb class lock acquisition | `src/loaddb/load_server_loader.cpp`, `server_class_installer::locate_class` | The `%class` line is enough to make the server-side session locate the class with `BU_LOCK`; the FIFO can then pause before sending a row. |
| loaddb worker ownership redirect | `src/transaction/lock_manager.c`, `lock_object`, `lock_has_lock_on_object` | A `TT_LOADDB` worker does not acquire its own class/instance lock. Its object-lock check is redirected to the connection/session transaction that owns `BU_LOCK`. |
| batch transaction lifetime | `src/loaddb/load_session.cpp`, `load_task::execute` | Each batch gets a fresh `tran_index`, then calls `xtran_server_commit` or `xtran_server_abort`. Experiment 3 tests the full batch path; Experiment 1 deliberately pauses before a row batch is sent. |
| transaction resource identity | `src/transaction/lock_manager.c`, `lock_create_mvccid_search_key`, `lock_transaction_mvccid` | The resource type is `LOCK_RESOURCE_TRANSACTION` and the active key is the full MVCCID, not an OID. |
| self-lock acquisition | `src/transaction/log_tran_table.c`, `logtb_acquire_mvccid_self_lock`, `logtb_self_lock_assigned_mvccid`, `logtb_ensure_mvccid_self_lock` | Inserter requests `X_LOCK` once per current MVCCID. `self_locked_mvccid` is an idempotence hint. |
| unique/FK wait and re-check | `src/storage/btree.c`, `btree_wait_for_inserter_end`, `btree_key_wait_for_insert_mvccid`, `btree_fk_object_does_exist` | A checker requests `S_LOCK`, releases page latches before blocking, releases S after grant, and restarts/re-checks. Experiment 2 makes both the unique and FK result successful by choosing rollback/commit outcomes intentionally. |
| transaction-end release | `src/transaction/lock_manager.c`, `lock_unlock_all` | Transaction resources share `inst_hold_list`; commit/abort removal wakes S waiters. Post-run dumps must prove that the observed MVCCID resources disappear. |
| bulk record lacks INSID | `src/storage/heap_file.c`, `heap_insert_adjust_recdes_header` | `is_bulk_op` omits the normal MVCC INSID stamp. A non-OOS bulk load does not need this rendezvous merely because it inserted a row. |
| OOS trigger and lazy file creation | `src/loaddb/load_server_loader.cpp`, `server_object_loader::finish_line`; `src/storage/heap_file.c`, `heap_attrinfo_transform_to_disk_internal`, `heap_oos_find_vfid`; `src/storage/oos_file.cpp`, `oos_create_file_internal` | A 5,000-byte `BIT VARYING` value is above the current 4,060-byte four-record target and is not string-compressed. The first demotion creates `FILE_OOS`. |
| hidden MVCCID request | `src/storage/file_manager.c`, `file_create` | `FILE_OOS` is among file types whose candidate VFID is checked against vacuum's dropped-file list using `logtb_get_current_mvccid`. |
| exact CBRD-27157 boundary | `src/transaction/lock_manager.c`, `lock_internal_perform_lock_object` | The pinned fix permits a `TT_LOADDB` request only when `search_key.type == LOCK_RESOURCE_TRANSACTION`; the object-lock prohibition remains asserted. |
| runtime OOS proof | `src/executables/csql.c`, `S_CMD_OOS_STATS`; `src/compat/db_admin.c`, `db_get_oos_stats` | `;oos_stats <class>` can distinguish “no OOS file” from a real OOS file on this pinned branch without instrumentation. |

## Shared runtime and safety gate

These gates are mandatory before any of the three experiments.

1. Record `just build` from `/home/vimkim/gh/cb/feat-oos-fix-regression` as `runtime-baseline-build`. This is the report workflow's local build gate; do not present `just` as a CUBRID organization command in the Book.
2. Create `evidence/runtime-tools-baseline.json` with `reportctl.py runtime-snapshot --id baseline --build-run-id runtime-baseline-build`.
3. Resolve `CSQL_ABS` and `CUBRID_ABS` from that snapshot. Do not use a PATH-resolved substitute. Every mandatory observation's `runner_argv[0]` is exactly `CSQL_ABS`.
4. Use `evidence/runtime-tools-baseline.json` as both baseline and active snapshot because no instrumentation is proposed.
5. Every setup, action, auxiliary observation, and cleanup is separately captured with `reportctl.py record`. All Experiment observation runs pass `--runtime-tools-snapshot evidence/runtime-tools-baseline.json`.
6. Setup and cleanup may be shell scripts. A manifest's mandatory `run_ids`, however, name only direct `csql --input-file` runs that use the hashed SQL runner and exit zero.
7. When a direct observation must remain blocked while `lockdb` is captured, launch the `reportctl record` call asynchronously through the host execution facility. Do not replace its runner with `bash`, `timeout`, or a wrapper. Run the auxiliary captured command concurrently, then wait for the original direct-csql receipt.

Canonical command shape after the snapshot exists:

```bash
python3 /home/vimkim/.agents/skills/cubrid-code-analysis-report/scripts/reportctl.py record \
  --report-dir /home/vimkim/gh/my-cubrid-docs/code-analysis/cbrd-27157-server-side-loaddb-locking-transaction-mvccid-self-lo/f11fc42_codex \
  --id expN-observe-r1 \
  --cwd /home/vimkim/gh/my-cubrid-docs/code-analysis/cbrd-27157-server-side-loaddb-locking-transaction-mvccid-self-lo/f11fc42_codex/experiments/experiment-N \
  --expect-exit 0 \
  --runtime-tools-snapshot evidence/runtime-tools-baseline.json \
  -- "$CSQL_ABS" --CS-mode --user dba --input-file observe.sql ca27157_eN_f11fc42
```

The shell expands `CSQL_ABS` before `reportctl.py`; the stored `runner_argv` must contain the absolute binary path. Keep `observe.sql` relative to the Experiment cwd so the manifest can hash the same bytes consumed by `csql`.

### Resource ownership rule shared by setup/cleanup

- Database names: `ca27157_e1_f11fc42`, `ca27157_e2_f11fc42`, `ca27157_e3_src_f11fc42`, and `ca27157_e3_dst_f11fc42`.
- Before `createdb`, test the first field of `$CUBRID_DATABASES/databases.txt`. If a name already exists, stop with exit 73. Never delete or reuse it.
- After successful creation, write `runtime-owner.txt` containing report directory, database name, CUBRID revision, creation timestamp, and the exact database-volume directory. Cleanup is authorized only when all fields match and the registry entry still points below the Experiment directory.
- Start only these named database servers. Cleanup may stop those exact servers. It must never call the global `cubrid service stop`.
- Runtime FIFOs and PID files live below `experiments/experiment-N/runtime/rK/`. Cleanup names each one explicitly; it never recursively deletes an unresolved path.
- If a holder/action is still running, validate `/proc/<pid>/cmdline` against the recorded absolute binary/script, Experiment path, and database name before sending a signal. Prefer the normal gate/transaction completion path. `SIGTERM` is a failure cleanup only.
- Database cleanup uses the CUBRID `deletedb` utility only after the owner check. A failed ownership check is a hard stop, not permission to remove files manually.

---

# Experiment 1 — class `BU_LOCK`: resource, owner, waiter, lifetime

## Identity and links

- ID: `experiment-1`
- Central behavior: `lock-resource-owner-lifecycle`
- Claim link reserved by `report.json`: `CUBRID-C001`
- Chapter anchor: `chapters/03-cubrid-lock-resources.html#lock-resource-owner-lifecycle`
- Instrumentation: not used
- Repetitions: 3

## Question

server-side loaddb가 아직 한 class를 적재 중일 때, `BU_LOCK`은 어떤 resource에 어느 transaction 소유로 존재하며, 일반 DML은 언제까지 기다리는가? 이 resource는 MVCCID transaction self-lock과 어떻게 다르게 출력되는가?

## Hypothesis

1. `%class dba.e1_target ...`를 server-side loaddb가 처리하면 class resource에 session transaction 소유 `BU_LOCK`이 생긴다.
2. loaddb의 object input을 FIFO에서 멈춰 session을 살아 있게 두면, 다른 client의 `UPDATE`는 class `IX_LOCK`을 얻지 못해 기다린다.
3. FIFO를 끝까지 보내 loaddb session이 종료되면 `BU_LOCK`이 사라지고, 기다리던 `UPDATE`와 바로 뒤의 같은 `UPDATE`가 모두 성공한다.
4. 해당 lock dump block은 class 이름/OID를 표시하며 `Transaction self-lock (inserter MVCCID = ...)`라고 표시되지 않는다.

## Owned setup

`setup.sql`:

```sql
CREATE TABLE dba.e1_target (
  id INT PRIMARY KEY,
  payload VARCHAR(20)
);
COMMIT;
```

각 repetition의 `runtime/rK/payload.objects`:

```text
%class dba.e1_target (id payload)
K 'load-K'
```

`K`는 1, 2, 3 중 해당 repetition 번호로 치환한다. 이 값은 20바이트 미만이어서 OOS를 유발하지 않는다.

`feed.sh`의 정확한 역할과 본문:

```bash
#!/usr/bin/env bash
set -euo pipefail
rep=${1:?repetition required}
case "$rep" in 1|2|3) ;; *) exit 64 ;; esac
run_dir="runtime/r${rep}"
exec 9<>"${run_dir}/objects.fifo"
IFS= read -r class_line <"${run_dir}/payload.objects"
printf '%s\n' "$class_line" >&9
printf '%s\n' ready >"${run_dir}/feeder.state"
IFS= read -r command <"${run_dir}/gate.fifo"
test "$command" = continue
tail -n +2 "${run_dir}/payload.objects" >&9
exec 9>&-
printf '%s\n' done >"${run_dir}/feeder.state"
```

`release.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
rep=${1:?repetition required}
case "$rep" in 1|2|3) ;; *) exit 64 ;; esac
printf '%s\n' continue >"runtime/r${rep}/gate.fifo"
```

`prepare-repetition.sh` creates only the exact `runtime/rK` directory, checks that none of its runtime paths exist, creates `objects.fifo` and `gate.fifo`, and writes the two-line object file. It does not start a process. Capture it separately.

## Mandatory direct-csql observation

`observe.sql`:

```sql
;time on
UPDATE dba.e1_target SET payload = payload WHERE id = -1;
UPDATE dba.e1_target SET payload = payload WHERE id = -2;
SELECT COUNT(*) AS loaded_rows FROM dba.e1_target;
```

The first `UPDATE` is the positive conflict probe. It changes no row but still needs ordinary table-write locking. The second is the after-release negative control. Both must succeed, so the direct `csql` process exits zero.

## Precise run order for each repetition

1. Capture `prepare-repetition.sh K`.
2. Start a captured `feed.sh K` asynchronously; wait until `feeder.state` contains `ready`.
3. Start, asynchronously, a separately captured direct utility action:

   ```text
   CUBRID_ABS loaddb -C -u dba -d runtime/rK/objects.fifo ca27157_e1_f11fc42
   ```

4. Capture `wait-for-held-bu.sh K`. It polls `CUBRID_ABS lockdb ca27157_e1_f11fc42` at 50 ms intervals for at most 10 seconds and succeeds only when one dump contains both `dba.e1_target` and `BU_LOCK`. Save the exact successful dump as `runtime/rK/held.lockdb.txt`.
5. Start the mandatory `exp1-observe-rK` direct-csql run asynchronously with `observe.sql`.
6. Capture `wait-for-bu-contention.sh K`. It polls `CUBRID_ABS lockdb -c ca27157_e1_f11fc42` and succeeds only when the same dump contains `dba.e1_target`, `BU_LOCK`, at least one holder, and at least one blocked waiter. Save it as `runtime/rK/contended.lockdb.txt`.
7. Capture `release.sh K`. This lets the feeder send the one row and close the object FIFO.
8. Wait for the feeder, loaddb action, and mandatory csql run. All three must exit zero. The loaddb output must contain `Total 1 object(s) inserted, 0 object(s) failed.`
9. Capture `CUBRID_ABS lockdb ca27157_e1_f11fc42` to `runtime/rK/post.lockdb.txt`; the `dba.e1_target` resource must not have a `BU_LOCK` holder.
10. Do not infer timing from a threshold alone. Preserve CSQL's `;time on` output as supporting evidence; the lock dump's holder/waiter state is the central oracle.

Run IDs:

```text
exp1-prepare-rK
exp1-feed-rK
exp1-loaddb-rK
exp1-held-lock-rK
exp1-observe-rK                 # manifest run_ids; direct csql --input-file
exp1-contention-lock-rK
exp1-release-rK
exp1-post-lock-rK
```

## Expected observations and oracle

- `held.lockdb.txt`: a class resource for `dba.e1_target`, one `BU_LOCK` holder, and no transaction-resource label for that block.
- `contended.lockdb.txt`: the same class resource still has the `BU_LOCK` holder plus a blocked ordinary DML waiter. Mode wording may vary with the message catalog; accept the structural holder/waiter counts and the presence of `BU_LOCK`, not one translated sentence.
- `observe.sql`: first statement remains pending until step 7; after release both updates affect zero rows and the count increases by exactly one for the repetition.
- `post.lockdb.txt`: no `BU_LOCK` remains for the target class.
- Across repetitions, scheduler timing may vary; resource type, modes, completion order, row-count delta, and release are invariant.

## Controls

- Positive control: first `UPDATE` while `BU_LOCK` is held must appear as a waiter.
- Negative control: the same type of `UPDATE` after loader completion must complete without a corresponding waiter; no timeout error is intentionally generated, keeping the mandatory run exit zero.
- OOS exclusion control: the object value is tiny. `FILE_OOS` and MVCCID self-lock are not required for this experiment.
- Cross-experiment distinction: compare this class resource block with Experiment 2's literal `Transaction self-lock (inserter MVCCID = ...)` block.

## Alternative explanations and how the design addresses them

| Alternative | Discriminator |
|---|---|
| The DML was merely slow | `lockdb -c` must show it as a waiter on the target class resource. |
| A row lock caused the wait | The update predicate matches no row, while the contended block is the named class resource with `BU_LOCK`. |
| The worker transaction owns `BU_LOCK` | Correlate the lock dump's holder `tran_index`/client metadata with the loaddb session and the source redirect in `lock_has_lock_on_object`; do not infer owner from the worker thread name. |
| `BU_LOCK` blocks every possible operation | Do not make that claim. The source matrix says it is compatible with `BU_LOCK` and `SCH_S_LOCK`; this runtime case proves only conflict with the observed ordinary DML mode. |
| Lock disappearance was caused by server restart | The database server remains running, the waiting csql connection resumes, and no server-stop command occurs between held and post dumps. |

## Cleanup and hard stops

- Normal cleanup runs only after all three repetitions: verify the owner marker, stop only `ca27157_e1_f11fc42`, run `deletedb` for that exact name, and remove only the six explicitly named FIFO/state runtime paths per repetition.
- On failure, first write `continue` to any gate whose feeder is alive, then wait. Signal only a validated recorded PID if normal completion fails.
- Hard-stop if class/BU state is not observed within 10 seconds, if `UPDATE` finishes before the contention dump, if a different pre-existing database owns the name, if the server dies, or if any cleanup owner check fails.

## Manifest design

```json
{
  "schema_version": 1,
  "id": "experiment-1",
  "behavior_ids": ["lock-resource-owner-lifecycle"],
  "claim_ids": ["CUBRID-C001"],
  "runner": "observe.sql",
  "runner_sha256": "COMPUTE_AFTER_WRITING",
  "runner_argv": ["ABSOLUTE_CSQL_FROM_SNAPSHOT", "--CS-mode", "--user", "dba", "--input-file", "observe.sql", "ca27157_e1_f11fc42"],
  "run_ids": ["exp1-observe-r1", "exp1-observe-r2", "exp1-observe-r3"],
  "oracle_ko": "BU_LOCK을 가진 class resource에 첫 DML이 waiter로 나타나고, loaddb session 종료 후 같은 종류의 DML이 성공하며 해당 BU holder가 사라진다.",
  "controls_ko": "held 상태의 첫 DML은 positive conflict control이고 release 뒤 두 번째 DML은 negative control이다. 작은 값으로 OOS 경로를 제외한다.",
  "alternative_explanations_ko": "단순 지연과 row lock 가능성은 target class의 BU holder/waiter lockdb block으로 배제한다. 이 실험은 BU가 모든 mode와 충돌한다고 일반화하지 않는다.",
  "repetitions": 3,
  "cubrid_runtime_only": true,
  "runtime_tools_snapshot": "evidence/runtime-tools-baseline.json",
  "cleanup_verified": "SET_TRUE_ONLY_AFTER_CAPTURED_CLEANUP"
}
```

`COMPUTE_AFTER_WRITING`, `ABSOLUTE_CSQL_FROM_SNAPSHOT`, and the cleanup boolean are design markers only. They must never be written into the actual manifest as placeholders.

---

# Experiment 2 — unique/FK checker and MVCCID self-lock rendezvous

## Identity and links

- ID: `experiment-2`
- Central behavior: `mvccid-self-lock-rendezvous`
- Claim link reserved by `report.json`: `CUBRID-C010`
- Chapter anchor: `chapters/05-mvccid-self-lock.html#mvccid-self-lock-rendezvous`
- Instrumentation: not used
- Repetitions: 3

## Question

다른 transaction이 아직 commit/rollback하지 않은 row의 unique key 또는 referenced PK를 검사할 때, CUBRID는 어떤 resource와 mode로 기다리고, inserter가 끝난 뒤 왜 B-tree를 다시 읽어야 하는가?

## Hypothesis

1. 각 inserter는 자기 MVCCID로 keyed된 transaction resource에 `X_LOCK`을 보유한다.
2. 같은 unique key를 삽입하려는 transaction과 아직 commit되지 않은 parent를 참조하려는 FK insert는 각각 그 MVCCID resource에 `S_LOCK` waiter로 나타난다.
3. unique holder가 rollback하면 재검사에서 key가 사라졌으므로 observer의 insert가 성공한다.
4. FK holder가 commit하면 재검사에서 parent가 보이므로 child insert가 성공한다.
5. holder transaction 종료 뒤 해당 MVCCID resource가 lock dump에서 사라진다.

## Owned setup

`setup.sql`:

```sql
CREATE TABLE dba.e2_uq (
  k INT PRIMARY KEY,
  note VARCHAR(30)
);
CREATE TABLE dba.e2_parent (
  id INT PRIMARY KEY
);
CREATE TABLE dba.e2_child (
  id INT PRIMARY KEY,
  parent_id INT,
  CONSTRAINT fk_e2_parent FOREIGN KEY (parent_id) REFERENCES dba.e2_parent (id)
);
INSERT INTO dba.e2_parent VALUES (1);
COMMIT;
```

`prepare-repetition.sql`:

```sql
DELETE FROM dba.e2_child;
DELETE FROM dba.e2_uq;
DELETE FROM dba.e2_parent WHERE id <> 1;
COMMIT;
```

## Concurrent holders

`holder-unique.sql`, executed directly by captured `csql --no-auto-commit --input-file`:

```sql
INSERT INTO dba.e2_uq VALUES (100, 'holder');
SELECT 'UNIQUE_HOLDER_READY' AS marker;
SELECT SLEEP(8.0) AS holder_delay;
ROLLBACK;
```

`holder-fk.sql`, also a direct captured csql run:

```sql
INSERT INTO dba.e2_parent VALUES (200);
SELECT 'FK_HOLDER_READY' AS marker;
SELECT SLEEP(16.0) AS holder_delay;
COMMIT;
```

The delays make observation feasible, but no exact duration is part of the oracle.

## Mandatory direct-csql observation

`observe.sql`:

```sql
;time on
INSERT INTO dba.e2_uq VALUES (101, 'control');
INSERT INTO dba.e2_child VALUES (1, 1);
INSERT INTO dba.e2_uq VALUES (100, 'observer');
INSERT INTO dba.e2_child VALUES (2, 200);
SELECT k, note FROM dba.e2_uq ORDER BY k;
SELECT id, parent_id FROM dba.e2_child ORDER BY id;
```

The first two statements are negative controls on different/committed keys. The third and fourth statements are the two positive rendezvous cases. Every statement is designed to succeed after the appropriate re-check; no expected SQL error is used.

## Auxiliary wait capture

Before launching the observer, `wait-for-two-holders.sh` polls a full `CUBRID_ABS lockdb ca27157_e2_f11fc42` dump until at least two `Transaction self-lock (inserter MVCCID = N)` resources with X holders exist. It saves the successful dump. This is readiness, not the central observation.

`capture-two-waits.sh` is launched as a separately captured command while the mandatory observer is running:

```bash
#!/usr/bin/env bash
set -euo pipefail
seen_file=runtime/seen-wait-mvccids.txt
: >"$seen_file"
for attempt in $(seq 1 500)
do
  scan="runtime/contention-${attempt}.txt"
  "$CUBRID/bin/cubrid" lockdb -c ca27157_e2_f11fc42 >"$scan"
  while IFS= read -r mvccid
  do
    test -n "$mvccid" || continue
    if ! grep -Fxq "$mvccid" "$seen_file"
    then
      printf '%s\n' "$mvccid" >>"$seen_file"
      cp "$scan" "runtime/wait-$(wc -l <"$seen_file" | tr -d ' ').lockdb.txt"
    fi
  done < <(sed -n 's/.*Transaction self-lock (inserter MVCCID = \([0-9][0-9]*\)).*/\1/p' "$scan")
  test "$(wc -l <"$seen_file")" -ge 2 && exit 0
  sleep 0.05
done
exit 1
```

Because `lockdb -c` emits only contended resources, every captured transaction resource must also contain an S waiter. The main agent must still inspect the two saved blocks and reject a malformed/localized output rather than trusting the parser alone.

`verify-release.sh` captures a full post-run lock dump, reads the two exact IDs from `seen-wait-mvccids.txt`, and fails if either `inserter MVCCID = <id>` remains.

## Precise run order for each repetition

1. Capture a direct-csql setup run of `prepare-repetition.sql`.
2. Start captured direct-csql runs for `holder-unique.sql` and `holder-fk.sql` asynchronously. Both use `--no-auto-commit`.
3. Capture `wait-for-two-holders.sh` and save the readiness dump.
4. Start mandatory direct-csql `exp2-observe-rK` asynchronously with `observe.sql` and default autocommit.
5. Immediately capture `capture-two-waits.sh`; it must collect two distinct contended MVCCID resource blocks.
6. Wait for both holders and the observer. All exit zero.
7. Capture `verify-release.sh` and a final value verification. The unique rows must be `(100,'observer')` and `(101,'control')`; the child rows must be `(1,1)` and `(2,200)`.

Run IDs:

```text
exp2-prepare-rK
exp2-unique-holder-rK
exp2-fk-holder-rK
exp2-holders-ready-rK
exp2-observe-rK                 # manifest run_ids; direct csql --input-file
exp2-two-waits-rK
exp2-release-check-rK
```

## Expected observations and oracle

- First saved contention block: literal transaction self-lock resource, one X holder, one S waiter. After holder rollback, observer's `k=100` insert succeeds.
- Second saved contention block: a different MVCCID transaction resource, one X holder, one S waiter. After holder commit, observer's `parent_id=200` insert succeeds.
- `lockdb` holder/waiter `tran_index` values are not expected to equal the resource MVCCID. Record them separately.
- The two negative controls finish before either positive result and do not create an S waiter on either holder MVCCID. CSQL timing is supporting evidence only.
- The post-run dump no longer contains either captured MVCCID resource.

## Controls

- Unique negative control: insert a different key (`101`) while the `100` inserter is active.
- FK negative control: reference previously committed parent `1` while parent `200` is in progress.
- Unique positive control: same key `100`; holder rollback makes the observer's re-check succeed.
- FK positive control: referenced key `200`; holder commit makes the observer's re-check succeed.
- Resource-type control: accept the central result only when `lockdb` explicitly labels the resource as a transaction self-lock keyed by MVCCID.

## Alternative explanations and how the design addresses them

| Alternative | Discriminator |
|---|---|
| A row OID X lock caused the wait | The captured resource is literally transaction-typed and keyed by MVCCID, with X/S modes. |
| Unique index latch caused the wait | `btree_key_wait_for_insert_mvccid` releases leaf/overflow latches before the wait; runtime `lockdb` shows a transaction lock waiter. |
| The observer continued without re-check | Outcomes are chosen so the final answer depends on post-wait state: rollback frees the unique key; commit makes the FK parent valid. |
| `tran_index`, transaction ID, and MVCCID are one number | Lock dump reports the holder/waiter transaction indices separately from the resource's MVCCID. The Book must point this out. |
| A precise 8/16-second timing proves the protocol | It does not. Scheduling and setup overhead vary; modes, wait state, outcomes, and resource disappearance are the oracle. |

## Feasibility and hard stops

- `SLEEP` is a CUBRID SQL function whose argument is in seconds at this revision. If the direct holder output does not show its ready marker and two X resources are not visible within 5 seconds, abort the repetition; do not lengthen the test blindly.
- Starting both holders and the observer requires concurrent host execution while retaining direct `csql` runner argv. If the host cannot do this, the experiment is blocked; a wrapper-only observation is not an acceptable v1 substitute.
- Hard-stop if only object resources appear, if either positive statement completes before any S waiter is captured, if the two IDs are not distinct, or if an observed ID remains after both holder transactions end.

## Cleanup

After every repetition, capture `prepare-repetition.sql` again only after all processes have exited; this returns the tables to the baseline rows. Final cleanup validates ownership, stops only `ca27157_e2_f11fc42`, and deletes that exact DB. A partial holder failure should be allowed to finish its SQL transaction; signal only its validated recorded process if it does not exit.

## Manifest design

```json
{
  "schema_version": 1,
  "id": "experiment-2",
  "behavior_ids": ["mvccid-self-lock-rendezvous"],
  "claim_ids": ["CUBRID-C010"],
  "runner": "observe.sql",
  "runner_sha256": "COMPUTE_AFTER_WRITING",
  "runner_argv": ["ABSOLUTE_CSQL_FROM_SNAPSHOT", "--CS-mode", "--user", "dba", "--input-file", "observe.sql", "ca27157_e2_f11fc42"],
  "run_ids": ["exp2-observe-r1", "exp2-observe-r2", "exp2-observe-r3"],
  "oracle_ko": "서로 다른 두 MVCCID transaction resource에서 inserter X holder와 checker S waiter를 관찰하고, rollback 뒤 unique 재삽입과 commit 뒤 FK 참조가 각각 성공하며 두 resource가 transaction 종료 뒤 사라진다.",
  "controls_ko": "다른 unique key와 이미 commit된 parent 참조는 negative controls이고, 같은 key와 미완료 parent 참조는 positive controls이다.",
  "alternative_explanations_ko": "transaction self-lock이라는 lockdb label과 X/S holder-waiter block으로 row lock·page latch 설명을 구분한다. 시간값 자체는 oracle이 아니다.",
  "repetitions": 3,
  "cubrid_runtime_only": true,
  "runtime_tools_snapshot": "evidence/runtime-tools-baseline.json",
  "cleanup_verified": "SET_TRUE_ONLY_AFTER_CAPTURED_CLEANUP"
}
```

---

# Experiment 3 — fixed `loaddb -C` + OOS end-to-end regression

## Identity and links

- ID: `experiment-3`
- Central behavior: `loaddb-oos-regression`
- Claim link reserved by `report.json`: `CUBRID-C020`
- Chapter anchor: `chapters/06-cbrd-27157-regression.html#loaddb-oos-regression`
- Instrumentation: not used
- Repetitions: 3 destination recreations from one owned source dump

## Question

CBRD-27157 수정이 포함된 pinned debug build에서 server-side `loaddb -C`로 첫 OOS 대상 행을 적재하면 서버가 살아 있고, 논리 값과 OOS file 존재가 모두 올바른가? 같은 load의 작은 값 control은 OOS file을 만들지 않는가?

## Hypothesis

1. 5,000-byte `BIT VARYING` 값을 가진 row는 current four-record target을 넘고 OOS demotion을 유발한다.
2. 첫 OOS file 생성이 `file_create(FILE_OOS)`에서 MVCCID를 lazy 할당해도, pinned fix가 `TT_LOADDB`의 transaction resource self-lock을 허용하므로 debug server는 abort하지 않는다.
3. `loaddb -C`는 두 row를 모두 적재하고 exit zero를 반환한다. 이후 직접 연결한 csql은 정확한 logical sizes/value equality를 확인한다.
4. `;oos_stats`는 5,000-byte case에 OOS file/live records를 보고하고 100-byte case에는 “no OOS file”을 보고한다.

## Source database setup

`source-setup.sql`:

```sql
CREATE TABLE dba.e3_case_a (
  id INT PRIMARY KEY,
  big BIT VARYING
);
CREATE TABLE dba.e3_case_b (
  id INT PRIMARY KEY,
  big BIT VARYING
);
INSERT INTO dba.e3_case_a
  VALUES (1, CAST(REPEAT('11', 100) AS BIT VARYING));
INSERT INTO dba.e3_case_b
  VALUES (1, CAST(REPEAT('AA', 5000) AS BIT VARYING));
COMMIT;
```

Create/start `ca27157_e3_src_f11fc42`, capture the direct-csql setup, and capture this exact utility action from the Experiment directory:

```text
CUBRID_ABS unloaddb -u dba --CS-mode ca27157_e3_src_f11fc42
```

Require the exact files `ca27157_e3_src_f11fc42_schema` and `ca27157_e3_src_f11fc42_objects` to exist and hash both before proceeding. Capture a source-side `verify-source.sql` that checks `DISK_SIZE` and equality; this prevents a corrupt dump seed from being blamed on loaddb.

## Destination action

For each repetition:

1. Verify `ca27157_e3_dst_f11fc42` does not exist, create it in the owned Experiment path, write a repetition-specific owner marker, and start only that DB server.
2. Capture this direct utility action from the Experiment directory:

   ```text
   CUBRID_ABS loaddb -C -u dba -s ca27157_e3_src_f11fc42_schema -d ca27157_e3_src_f11fc42_objects ca27157_e3_dst_f11fc42
   ```

3. Require action exit zero and output containing `Total 2 object(s) inserted, 0 object(s) failed.` Reject any `Aborted`, `server failure`, or connection-loss text.
4. Run the mandatory direct-csql observation below.
5. Capture a direct status/connectivity check. The successful mandatory csql connection already proves the server survived; `cubrid server status` is supporting evidence only.
6. Capture destination cleanup and delete this owned DB before recreating it for the next repetition. Never reuse data pages across repetitions; every repetition must begin with classes that have no OOS VFID.

## Mandatory direct-csql observation

`observe.sql`:

```sql
SELECT id,
       DISK_SIZE(big) AS bytes_on_disk,
       (big = CAST(REPEAT('11', 100) AS BIT VARYING)) AS same_value
  FROM dba.e3_case_a;
;oos_stats dba.e3_case_a
SELECT id,
       DISK_SIZE(big) AS bytes_on_disk,
       (big = CAST(REPEAT('AA', 5000) AS BIT VARYING)) AS same_value
  FROM dba.e3_case_b;
;oos_stats dba.e3_case_b
```

The main agent must confirm that csql treats each `;oos_stats` line as a session command when read through `--input-file`. The actual mandatory runner is direct `CSQL_ABS`, not the loaddb utility.

Run IDs:

```text
exp3-source-create
exp3-source-sql
exp3-source-unload
exp3-source-verify
exp3-destination-create-rK
exp3-loaddb-rK
exp3-observe-rK                 # manifest run_ids; direct csql --input-file
exp3-server-status-rK
exp3-destination-cleanup-rK
exp3-source-cleanup
```

## Expected observations and oracle

- All three loaddb actions exit zero with exactly two inserted and zero failed objects.
- All three mandatory csql runs connect successfully after loaddb.
- `e3_case_a`: `DISK_SIZE(big)=100`, equality result true, one row, and the output says the class has no OOS file.
- `e3_case_b`: `DISK_SIZE(big)=5000`, equality result true, one row, and OOS stats show a non-null OOS VFID with at least one live OOS record and at least one physical page.
- No exact VFID/page count is an oracle; allocation varies.
- The pinned runtime snapshot must identify a debug build. If build flavor cannot be proved, the experiment can verify data but cannot claim that the debug-only assert regression was exercised.

## Controls

- Positive OOS case: 5,000-byte uncompressed `BIT VARYING`, above the pinned revision's target.
- Negative OOS case: 100-byte value in an otherwise identical schema, below the target.
- Source integrity control: source-side sizes/equality and hashes before unload.
- Repetition control: destination DB is deleted and recreated for every run, so each OOS case exercises lazy first-file creation.
- Fixed-path control: server survival is proved by a new csql connection and query after the loaddb action, not only by absence of an assert string.

## Alternative explanations and limitations

| Alternative | Discriminator or limitation |
|---|---|
| The 5,000-byte value was compressed below the trigger | It is `BIT VARYING`, not `VARCHAR`; `DISK_SIZE=5000` and `;oos_stats` prove the case actually created OOS storage. |
| loaddb silently skipped the row | Exact two/zero summary plus row count/value equality rejects this. |
| The server aborted and restarted automatically | The experiment starts no restart action between loaddb and mandatory csql; preserve timestamps/PIDs/status output. |
| Passing fixed HEAD proves the historical pre-fix crash | It does not. The pinned experiment proves TO-BE only. The AS-IS crash stack comes from separately pinned historical/CI evidence. Do not switch to an old binary inside this Report Run. |
| Small-value success alone proves OOS fix | It is only the negative control. `e3_case_b` OOS stats and survival are required. |
| This proves every OOS or loaddb workload | It proves the exact two-row input on the pinned debug build, repeated three times. It does not cover HA, replication, crash recovery, every OOS type, or performance. |

## Feasibility risks and hard stops

- `;oos_stats` is branch-specific developer observability. It exists in the pinned source, but if the sealed csql binary does not recognize it, stop: that indicates binary/source mismatch or a failed build gate.
- `unloaddb`/`loaddb` output basename depends on the database name and cwd. Verify exact files and hashes rather than searching a broad directory.
- If OOS stats say no file for `e3_case_b`, do not reinterpret the run as a pass even if the logical value is correct.
- If the runtime build is release or unknown, do not claim direct validation of the former debug assert.
- If cleanup of the destination DB fails after a repetition, do not start the next repetition with the same name.

## Cleanup

After each repetition, owner-check and stop/delete only `ca27157_e3_dst_f11fc42`. After all three repetitions, owner-check and stop/delete only `ca27157_e3_src_f11fc42`. Preserve the generated schema/object files and their hashes as Experiment inputs; do not delete them during runtime cleanup. Record cleanup success only after the database registry has no entries for either name and no owned server PID remains.

## Manifest design

```json
{
  "schema_version": 1,
  "id": "experiment-3",
  "behavior_ids": ["loaddb-oos-regression"],
  "claim_ids": ["CUBRID-C020"],
  "runner": "observe.sql",
  "runner_sha256": "COMPUTE_AFTER_WRITING",
  "runner_argv": ["ABSOLUTE_CSQL_FROM_SNAPSHOT", "--CS-mode", "--user", "dba", "--input-file", "observe.sql", "ca27157_e3_dst_f11fc42"],
  "run_ids": ["exp3-observe-r1", "exp3-observe-r2", "exp3-observe-r3"],
  "oracle_ko": "고정 debug build에서 loaddb -C가 OOS 대상과 작은 control을 모두 적재하고 서버가 살아 있으며, 직접 csql 검증에서 값이 일치하고 OOS file은 5,000-byte case에만 존재한다.",
  "controls_ko": "100-byte BIT VARYING은 negative OOS control, 5,000-byte BIT VARYING은 positive OOS case이며 destination을 매번 재생성한다.",
  "alternative_explanations_ko": "OOS stats와 DISK_SIZE로 실제 demotion을 확인하고 새 csql 연결로 서버 생존을 확인한다. 이 run은 과거 미수정 binary의 crash를 다시 증명하지 않는다.",
  "repetitions": 3,
  "cubrid_runtime_only": true,
  "runtime_tools_snapshot": "evidence/runtime-tools-baseline.json",
  "cleanup_verified": "SET_TRUE_ONLY_AFTER_CAPTURED_CLEANUP"
}
```

---

# Quiz designs

The main agent should create exactly `quiz/quiz-1`, `quiz/quiz-2`, and `quiz/quiz-3`. Each directory must contain Korean `quiz.md`, Korean `answer.md`, and the runnable artifacts named below. The question files and scripts must not contain the answer statements from the answer sections.

## Quiz 1 — lock의 다섯 질문으로 `BU_LOCK` 읽기

### Links and level

- Central behavior: `lock-resource-owner-lifecycle`
- Claim: `CUBRID-C001`
- Book: `chapters/03-cubrid-lock-resources.html#lock-resource-owner-lifecycle`
- Prerequisite: mutex와 SQL transaction의 commit/rollback
- Expected time: 25–35 minutes
- Runnable artifacts: `run.sh`, `probe.sql`, `cleanup.sh`; the runner may reuse a quiz-owned copy of Experiment 1's FIFO feeder logic under database `ca27157_q1_f11fc42`

### `quiz.md` design (non-answer-leaking)

학습자에게 실행 전 아래 표를 채우게 한다.

| 관찰 대상 | 예측할 항목 |
|---|---|
| case가 멈춰 있는 동안의 첫 lock block | resource key/type, requested/granted mode, owner transaction, waiter transaction |
| gate를 연 직후 | 먼저 깨어날 statement와 그 이유 |
| 두 번째 동일 DML | 첫 번째와 달라질지 여부 |
| transaction resource block | 나타날지 여부와 판단 근거 |

실행 절차:

1. `bash run.sh`를 실행한다.
2. `raw/held.lockdb.txt`, `raw/contended.lockdb.txt`, `raw/post.lockdb.txt`, `raw/probe.out`을 순서대로 읽는다.
3. lock block에서 class name/OID, holder의 `tran_index`, granted mode, waiter의 `tran_index`/mode를 표시한다.
4. “loaddb worker가 직접 이 class lock을 소유한다”라는 문장이 맞는지 resource/owner lookup 관점에서 설명한다.
5. `BU_LOCK`과 호환되는 mode를 source matrix에서 찾아, 실험이 증명한 범위와 source가 말하는 전체 matrix를 구분한다.
6. 마지막에 4문장 teach-back을 작성한다: 무엇을 보호하는가, 누가 소유하는가, 누가 기다리는가, 언제 풀리는가.

`probe.sql`은 답을 설명하는 주석 없이 다음만 포함한다.

```sql
;time on
UPDATE dba.q1_target SET payload = payload WHERE id = -1;
UPDATE dba.q1_target SET payload = payload WHERE id = -2;
SELECT COUNT(*) AS n FROM dba.q1_target;
```

`run.sh`의 요구사항:

- pre-existing DB면 exit 73;
- quiz-owned DB/table/FIFO만 생성;
- `%class`만 FIFO에 먼저 보내고 `lockdb`에서 target class lock을 확인;
- `probe.sql`을 direct csql input으로 시작;
- contention dump를 저장한 다음 gate를 열기;
- 프로세스 exit와 post dump를 저장;
- 정상/실패 모두 `cleanup.sh`로 exact owned resources만 정리;
- 출력에는 “정답은 BU의 session ownership이다” 같은 설명을 쓰지 않는다.

### Separate `answer.md` design

정답은 다음 causal chain을 쉬운 한국어로 설명한다.

1. resource는 `dba.q1_target` class object이고 mode는 `BU_LOCK`이다.
2. holder는 client/session transaction이다. `TT_LOADDB` worker의 object-lock 조회는 session transaction으로 redirect된다.
3. 첫 DML은 class-level ordinary mode가 `BU_LOCK`과 충돌하여 wait한다. row가 실제로 선택되지 않아도 class lock 결정은 필요하다.
4. FIFO가 끝나 load session transaction이 종료되면 `lock_unlock_all` 경로로 holder가 사라지고 waiter가 진행한다. 두 번째 DML은 더 이상 같은 waiter가 되지 않는다.
5. `BU_LOCK`은 mutex가 아니고, “모든 것과 충돌하는 X lock”도 아니다. `BU_LOCK`/`SCH_S_LOCK`과 호환된다는 source matrix 한계를 적는다.
6. 이 Quiz는 worker 내부 thread scheduling, 모든 lock mode, deadlock victim policy를 증명하지 않는다고 명시한다.

흔한 오답:

- “BU는 row마다 잡힌다” — dump resource와 source acquisition seam이 class임을 놓쳤다.
- “worker가 BU를 소유한다” — thread와 transaction owner를 혼동했다.
- “gate를 열면 mutex가 unlock된다” — transaction lifetime의 lock과 FIFO coordination tool을 혼동했다.
- “BU와 MVCCID self-lock은 같은 lock이다” — resource key/type이 다르다.

## Quiz 2 — unique/FK가 기다린 뒤 무엇을 다시 판단하는가

### Links and level

- Central behavior: `mvccid-self-lock-rendezvous`
- Claim: `CUBRID-C010`
- Book: `chapters/05-mvccid-self-lock.html#mvccid-self-lock-rendezvous`
- Prerequisite: primary/unique key, foreign key, MVCC에서 uncommitted row가 존재할 수 있다는 사실
- Expected time: 35–45 minutes
- Runnable artifacts: `holder-a.sql`, `holder-b.sql`, `observer.sql`, `run.sh`, `cleanup.sh`

### `quiz.md` design (non-answer-leaking)

실행 전에 네 statement의 결과와 대기 여부를 예측하게 한다.

1. active transaction의 key와 다른 unique key insert
2. 이미 commit된 parent를 가리키는 child insert
3. active transaction과 같은 unique key insert
4. 아직 끝나지 않은 parent를 가리키는 child insert

그 다음 `bash run.sh`를 실행하고 다음을 답하게 한다.

- 두 contention dump의 resource key는 OID인가 MVCCID인가?
- X holder와 S waiter의 `tran_index`는 resource key 숫자와 같은가?
- 첫 holder의 종료 결과와 두 번째 holder의 종료 결과가 다른데도 두 observer statement가 왜 모두 성공하는가?
- wait하는 동안 B-tree page latch를 계속 들고 있다면 어떤 문제가 생길 수 있는가?
- CUBRID의 이 protocol을 PostgreSQL transaction-ID wait나 InnoDB transaction/record wait와 비교할 때 왜 `partial analogy`라고 해야 하는가?
- 마지막에 wait/re-check state machine을 6단계로 다시 그린다.

`holder-a.sql`, `holder-b.sql`, `observer.sql`은 Experiment 2의 SQL에서 table prefix만 `q2_`로 바꾼다. Script comments에는 rollback/commit 뒤 observer가 성공하는 이유를 쓰지 않는다. `run.sh`는 raw lock dumps와 final query result만 보여 준다.

### Separate `answer.md` design

정답의 핵심:

1. inserter가 자신의 MVCCID resource에 X self-lock을 가진다.
2. checker가 index entry의 active INSID를 보면 해당 MVCCID resource에 S를 요청한다.
3. checker는 page latch와 임시 object lock을 놓고 wait한다.
4. transaction end가 X를 놓으면 S가 granted되고 즉시 해제된다.
5. unique path는 root부터 다시 찾아 rollback으로 key가 사라졌음을 확인한 뒤 insert한다.
6. FK path는 다시 찾아 commit된 parent가 존재함을 확인한 뒤 child를 insert한다.
7. 다른 key/committed parent controls는 해당 active MVCCID에 S waiter가 되지 않는다.

흔한 오답:

- “S lock은 row를 읽기 위한 일반 shared lock이다” — 여기서는 transaction resource 종료를 기다리는 rendezvous다.
- “X self-lock이라서 자기 자신이 deadlock된다” — fresh MVCCID를 자기 transaction이 먼저 X로 잡으므로 acquisition 자체는 기다리지 않는다.
- “wake되면 이전 index 판단을 그대로 사용한다” — wait 동안 page/index state가 변할 수 있어 re-check가 핵심이다.
- “MVCCID와 tran_index가 같다” — 용도와 dump field가 다르다.

한계: 이 Quiz는 deadlock victim selection, crash recovery, 2PC, 모든 unique/FK interleaving을 증명하지 않는다. PostgreSQL/MySQL 실행도 하지 않는다.

## Quiz 3 — 작은 값과 큰 값을 `loaddb -C`로 적재해 회귀 경계를 설명하기

### Links and level

- Central behavior: `loaddb-oos-regression`
- Claim: `CUBRID-C020`
- Book: `chapters/06-cbrd-27157-regression.html#loaddb-oos-regression`
- Prerequisite: Experiment/Quiz 1–2의 class lock과 transaction self-lock 구분
- Expected time: 30–40 minutes
- Runnable artifacts: `seed.sql`, `verify.sql`, `run.sh`, `cleanup.sh`

### `quiz.md` design (non-answer-leaking)

학습자는 실행 전에 `case_a=100 bytes`, `case_b=5,000 bytes`에 대해 다음을 예측한다.

- 어느 case에서 OOS file이 생길까?
- 두 case 모두 bulk insert이므로 INSID가 같은 방식으로 기록될까?
- `FILE_OOS` lazy create가 필요해지면 왜 MVCCID 발급 코드로 들어갈까?
- fixed debug build에서 loaddb worker에게 허용되는 lock resource type은 어디까지일까?
- `loaddb` 성공 문자열만으로 OOS 경로 실행을 증명할 수 있을까?

`bash run.sh`가 quiz-owned source/destination DB를 만들고, `seed.sql`을 입력하고, `unloaddb`, `loaddb -C`, direct `csql --input-file verify.sql`을 실행하게 한다. `verify.sql`은 답을 말하는 alias/comment 없이 다음 관찰만 출력한다.

```sql
SELECT id, DISK_SIZE(big),
       (big = CAST(REPEAT('11', 100) AS BIT VARYING))
  FROM dba.q3_case_a;
;oos_stats dba.q3_case_a
SELECT id, DISK_SIZE(big),
       (big = CAST(REPEAT('AA', 5000) AS BIT VARYING))
  FROM dba.q3_case_b;
;oos_stats dba.q3_case_b
```

관찰 후 학습자는 다음 call chain의 빈칸을 채운다.

```text
server_object_loader::finish_line
  -> [record layout / OOS insert seam]
  -> [lazy OOS VFID/file seam]
  -> file_create(FILE_OOS)
  -> [lazy MVCCID seam]
  -> [self-lock seam]
  -> lock_internal_perform_lock_object
```

마지막 질문은 설계 판단형으로 한다: “TT_LOADDB이면 self-lock을 skip”과 “transaction resource만 uniform하게 허용” 중 각각 어떤 미래 불변식과 위험을 갖는가? 질문 파일은 정답 선택지를 표시하지 않는다.

### Separate `answer.md` design

정답의 핵심:

1. 100-byte case는 target 아래라 OOS file이 없다. 5,000-byte `BIT VARYING` case는 4,060-byte target을 넘어 demotion되고 OOS file/live record가 관찰된다.
2. OOS는 crash의 lock 원인이 아니라 hidden trigger다. Lazy `FILE_OOS` creation이 vacuum dropped-file safety를 위해 current MVCCID를 요구한다.
3. MVCCID 첫 발급이 X self-lock을 요청하고, 과거 broad `TT_LOADDB` assert와 충돌했다.
4. pinned fix의 조건은 `TT_LOADDB` 전체 lock 허용이 아니라 `is_transaction_lock`일 때만 허용이다. Object locks는 session `BU_LOCK` 계약에 계속 의존한다.
5. post-load direct csql의 value equality, `DISK_SIZE`, OOS stats, fresh connection이 함께 있어야 end-to-end oracle이 된다.
6. skip안은 현재 bulk row에 observer가 없다는 사실에 의존하지만 future INSID producer에 약하다. Uniform transaction self-lock은 invariant를 구조적으로 유지하되, `is_transaction_lock` 분류가 정직해야 한다.

흔한 오답:

- “OOS가 BU_LOCK과 충돌해 crash했다” — class object resource와 transaction MVCCID resource를 합쳤다.
- “release build도 반드시 같은 assert로 죽는다” — assert는 debug/optdebug 영향이다.
- “5,000 characters면 충분하다” — 반복 `VARCHAR`는 compression 때문에 물리 크기가 달라질 수 있다. 여기서는 `BIT VARYING`과 `DISK_SIZE`를 쓴다.
- “한 번 성공했으므로 historical cause까지 runtime으로 증명했다” — fixed HEAD는 TO-BE만 관찰한다.

한계: 이 Quiz는 historical pre-fix binary, HA/replication, crash recovery, 모든 OOS type을 실행 검증하지 않는다.

---

# Quiz safety and reproducibility checklist

The main agent should reject a Quiz artifact unless every item is true.

- [ ] `quiz.md` and `answer.md` are separate Korean files.
- [ ] Question prose and scripts do not state the predicted lock mode/outcome as an answer.
- [ ] At least one SQL/shell artifact is directly runnable with the pinned CUBRID runtime.
- [ ] Database and object names are quiz-specific and checked for pre-existence.
- [ ] `run.sh` is non-interactive, `set -euo pipefail`, and has a trap that invokes ownership-checked cleanup.
- [ ] No script calls global service stop, deletes a broad directory, kills an unvalidated PID, or reuses an existing DB.
- [ ] Concurrency Quizzes validate resource/mode/outcome invariants rather than a precise duration.
- [ ] PostgreSQL/MySQL are reasoning questions only; their binaries/servers are not dependencies.
- [ ] Each answer explains causality, common misconceptions, Claim/chapter links, and what the run does not prove.
- [ ] `bash -n` passes for all shell scripts.
- [ ] Each Quiz is run at least once by the main agent against the sealed local CUBRID build before publication.

# Suggested `expected-oracle.md` wording

The following concise forms keep observation separate from interpretation.

## Experiment 1

> Observation invariant: while the target class has a `BU_LOCK` holder, the first direct-csql DML appears as a waiter on that class resource. After captured loaddb completion, the DML succeeds and no target-class BU holder remains. Timing is supporting evidence only.

## Experiment 2

> Observation invariant: two distinct contended `Transaction self-lock (inserter MVCCID = N)` blocks are captured. Each contains an X holder and S waiter. The rollback unique case and commit FK case both succeed after re-check, and both captured resources disappear after transaction end.

## Experiment 3

> Observation invariant: each fresh destination load exits zero with two inserted and zero failed rows; the server accepts a new csql connection; both logical values match; only the 5,000-byte class reports a real OOS file/live record. No exact VFID, page count, or duration is required.

# Unknowns and feasibility risks to preserve in the final report

1. Experiment 1 proves the observed DML conflict, not every cell of the compatibility matrix. The complete matrix remains source-confirmed evidence.
2. Experiment 2's SQL-visible blocking plus transaction-resource lock dump strongly identifies the rendezvous. It still observes only two deliberately selected interleavings, not every unique/FK race.
3. Experiment 3 cannot reproduce the historical crash without switching revisions/binaries, which would violate the pinned runtime contract. Historical AS-IS evidence must remain separately labeled source/CI/core evidence.
4. `;oos_stats` is implementation-specific observability on this revision. Its absence from the built binary is an identity failure, not permission to claim OOS from `DISK_SIZE` alone.
5. A locale change can alter surrounding `lockdb` prose. Match the hardcoded transaction-resource line and structural modes/counts, and retain raw output.
6. Concurrent `reportctl record` calls are required for direct-csql runner compliance plus in-wait `lockdb` capture. If the host implementation cannot safely record distinct run IDs concurrently, ask the main agent to serialize via the host's yielded execution sessions; do not wrap the mandatory csql runner.
7. Every actual manifest must use Claim IDs already owned by its linked central behavior. If the Claim ledger assigns more precise runtime Claims, update `report.json.central_behaviors[*].claim_ids` first; do not cite an unowned Claim merely because it is convenient.

# Handoff to the main agent

- Write the Experiment and Quiz files from these designs, then compute real hashes. Never copy the uppercase design markers into JSON.
- Bind only the direct `csql --input-file` observation receipts in each manifest `run_ids`; link action/holder/lockdb/setup/cleanup receipts from `experiment.md` and Claim limitations.
- Execute baseline build/snapshot before any setup.
- Keep `report.json.instrumentation.status` as `not-used`.
- After execution, create CUBRID runtime or source+runtime Claims for `CUBRID-C001`, `CUBRID-C010`, and `CUBRID-C020` (or revise the reserved IDs consistently) and attach every mandatory Experiment run ID.
- Preserve failed attempts as evidence, but do not list them as successful manifest runs.
- Do not set `cleanup_verified=true` until exact database registry, process, FIFO, and ownership checks have been captured successfully.
