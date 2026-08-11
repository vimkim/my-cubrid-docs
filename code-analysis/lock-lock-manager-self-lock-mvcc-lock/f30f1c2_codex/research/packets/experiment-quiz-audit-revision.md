# Role 4 audit-revision packet — Experiments and Quizzes

## Packet metadata

- Role: Experiment and Quiz Designer, read-only audit revision
- Analysis Topic: `CUBRID lock과 lock manager: self lock 및 MVCC lock의 필요성`
- Declared Scope: `research/scope.md`
- Declared Scope SHA-256: `711d1a0f5bfebdbe1b55b4299973efc353d90636e2f00fc807f51d031766a839`
- CUBRID root/revision: `/home/vimkim/gh/cb/cubrid-analysis` @ `f30f1c26003e5aa8e93182648e06cad76fc77064`
- CUBRID frozen status SHA-256: `6f459c90a9e5391919b0f19ac04ffd081eab7905b9fde6cc27658f45f817bad1`
- Report directory: `/home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex`
- Packet timestamp (UTC): `2026-08-11T09:57:53Z`
- Constraint honored: this audit did not execute CUBRID, mutate a database, source, Book, report, Claim ledger, evidence, Experiment, or Quiz. Only this packet was written.

This packet gives the sole final-artifact writer exact revision content and a proposed execution plan. A proposed run ID is not Evidence until `reportctl.py record` creates a successful immutable receipt. Do not put a proposed ID into a Claim or manifest before its receipt exists and its raw output satisfies the invariant.

## 1. Current evidence and exact sealed runtime to disclose

Every `experiment.md` must contain an `환경과 증거 identity` section with the following facts and links. Copy them exactly; do not replace them with “local debug build.”

| Item | Exact recorded value |
|---|---|
| Runtime build receipt | `../../evidence/runs/runtime-baseline-build-2/meta.json` |
| Runtime snapshot | `../../evidence/runtime-tools-baseline.json` |
| Source | `f30f1c26003e5aa8e93182648e06cad76fc77064` |
| Release | `CUBRID 11.5.0 (11.5.0.2374-f30f1c2) (64bit debug build for Linux) (Jul 28 2026 17:53:27)` |
| Build preset/mode | `debug_gcc`; build directory `/home/vimkim/gh/cb/cubrid-analysis/build_preset_debug_gcc` |
| Install root | `/home/vimkim/.cub/install/cubrid-analysis/debug_gcc` |
| `csql` | `/home/vimkim/.cub/install/cubrid-analysis/debug_gcc/bin/csql`, SHA-256 `beb90bf72abab0334bf096d783bfef58608dbd21031daa4913cf93f137fdf722` |
| `cubrid` | `/home/vimkim/.cub/install/cubrid-analysis/debug_gcc/bin/cubrid`, SHA-256 `56ddaca924ecb6229a8f1c22b5322457a21a45a458e478c12a402f372ef53179` |
| `cub_server` | `/home/vimkim/.cub/install/cubrid-analysis/debug_gcc/bin/cub_server`, SHA-256 `4e3c59bc19b6a42d7a924b5052fcb4237d26e73e4e03d869d15b3b8c799331ea` |
| Database registry | `/home/vimkim/.cub/db/cubrid-analysis/commondb/databases.txt` |
| Locale/environment | `LANG=en_US.UTF-8`, `LC_ALL=C.UTF-8`; full captured environment is in the runtime snapshot |
| Instrumentation | `not-used`; no source marker/patch and no instrumented runtime |
| Existing observation runtime-environment hash | `461d49f56d29cff5619369872274c0b26d97cb69e43c7dd592ddff4f1f0e9a1f` in each successful Experiment receipt |

The current successful lock dumps also directly print the effective lock configuration for their sessions:

- isolation: `COMMITTED READ`;
- transaction lock timeout: `Infinite wait`;
- lock escalation threshold: `100000`;
- deadlock detector interval: `1.00` second.

For the revision runs, capture rather than assume the complete effective configuration. While the owned database is running, add these two supporting receipts per Experiment:

```bash
python3 /home/vimkim/.agents/skills/cubrid-code-analysis-report/scripts/reportctl.py record \
  --report-dir /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex \
  --id expN-paramdump-audit \
  --cwd /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/experiments/experiment-N \
  --expect-exit 0 \
  --runtime-tools-snapshot evidence/runtime-tools-baseline.json \
  -- /home/vimkim/.cub/install/cubrid-analysis/debug_gcc/bin/cubrid paramdump calockeNf30
```

`session-config.sql` must contain exactly:

```sql
GET TRANSACTION ISOLATION LEVEL;
GET TRANSACTION LOCK TIMEOUT;
```

Capture it directly with csql as `expN-session-config-audit`, using the same argv shape as the Experiment runner except `-i session-config.sql`. Replace `N` with `1` through `4`; the database names are exactly `calocke1f30` through `calocke4f30`. Link both receipts from `experiment.md` and quote only values actually printed. `paramdump` and `GET TRANSACTION` are read-only supporting observations and do not belong in manifest `run_ids`.

### Exact command/receipt disclosure rule

For each accepted run, `experiment.md` must link `meta.json`, `stdout.txt`, and `stderr.txt` and print the exact `argv` array copied from `meta.json`. For example, Experiment 3's mandatory argv is:

```json
["/home/vimkim/.cub/install/cubrid-analysis/debug_gcc/bin/csql", "-C", "-u", "dba", "--no-auto-commit", "-i", "observe.sql", "-t", "calocke3f30"]
```

Do not paraphrase `-C`, `--no-auto-commit`, or `-t`. State that `-C` is client/server mode, `dba` is the test owner, auto-commit is disabled, and transaction completion is explicit in SQL. Setup, reset, holder, auxiliary lock dump, invariant verification, and cleanup receipts must be listed separately from the mandatory direct-csql observation.

## 2. Current safety defects to fix before any repetition or Quiz run

### Experiment setup/cleanup

All four current `setup.sh`/`cleanup.sh` pairs have the same material gaps:

1. `.owned-db` stores only the database name. It does not bind the report, Experiment, source revision, registry path, or volume/log paths. If the original DB is removed and another DB later reuses the name, current cleanup cannot distinguish them.
2. `createdb` uses the default common database directory rather than an Experiment-owned explicit volume/log directory.
3. The ownership marker is written only after `createdb`; a failure between creation and marker leaves a database that cannot be safely attributed by the cleanup script.
4. Setup has no error trap for a partially created/started owned database.
5. Setup refuses merely because `observed/` exists, so it cannot safely preserve old Evidence and create per-repetition output. The `observed/setup-release` wait is orchestration residue and makes setup non-idempotent.
6. Cleanup executes `server stop ... || true`; suppressing an unexpected stop error and continuing to deletion loses a safety boundary.
7. Cleanup validates neither the registry row's volume/log path nor recorded child PIDs/cmdlines before stopping/deleting.
8. `capture.sh` overwrites one shared file and uses mode strings anywhere in the dump. Experiment 1 does not prove same-owner hierarchy through its predicate; Experiments 2–4 do not require all holder/waiter modes to occur in one parsed resource block.

Before rerunning, revise `setup.sh` into provisioning only. It must:

- refuse with exit 73 before mutation if the exact DB name already occurs in registry field 1;
- refuse stale `.owned-db` rather than guessing ownership;
- use exact `runtime/db` and `runtime/log` paths under the Experiment directory;
- create a `state=reserved` marker before `createdb`, then atomically replace it with `state=owned` only after the registry row fields match the expected paths;
- record `report_dir`, `experiment_id`, `db_name`, `source_revision`, `registry`, `volume_path`, `log_path`, and a fresh invocation nonce;
- start only `cubrid server start <exact-db>`; never use a service-wide stop/start;
- on failure, clean only when this invocation's marker and exact registry path both match;
- return after server readiness; remove the `setup-release` loop.

Capture `setup.sql` separately through direct csql. For cleanup, verify all marker fields and the current registry row before mutation; validate/finish only recorded csql PIDs by `/proc/<pid>/cmdline`; require exact `server stop` success or a proved already-stopped state; run `deletedb` only for the matching exact row; verify row absence; remove only the known marker and empty directories with `rmdir`. Never use a recursive delete.

### Quiz cleanup — currently unsafe

All four `cleanup.sql` files contain an unconditional `DROP TABLE IF EXISTS dba.qN_*`. The Quiz prose does not give an exact connection command, and no DB identity or ownership marker is checked. A learner who invokes this SQL against a pre-existing/user DB can delete an unrelated fixed-name table. This is the clearest unsafe current cleanup.

Delete `cleanup.sql` from each Quiz and replace it with owner-verified `cleanup.sh` that stops/deletes only the Quiz-owned database. `run.sh` must pass an exact fixed database name to every csql invocation and must refuse a pre-existing registry row before executing any SQL.

At packet-review time, registry inspection showed none of `calocke1f30`…`calocke4f30` or `qalockq1f30`…`qalockq4f30`; this is a transient observation, not permission to skip the collision check at execution time.

## 3. Common Experiment revision contract

Each `experiment.md` must use these headings, in Korean, in this order:

1. `질문과 가설`
2. `관찰 범위와 비관찰 범위`
3. `Sealed build/runtime/configuration`
4. `입력과 exact argv`
5. `Setup → Action → Observation → Cleanup`
6. `반복, warm/cold 상태, variability`
7. `Raw observation`
8. `Interpretation`
9. `Controls와 alternative explanations`
10. `Observer effect와 한계`
11. `Evidence links와 Claim`

Use this exact warm/cold disclosure for new three-run series:

> DB와 server는 세 반복 직전에 한 번 새로 생성한다. 첫 반복도 schema 생성과 readiness/lockdb 확인으로 catalog, heap, index page가 이미 접근되므로 strict cold-cache run이 아니다. 반복 사이에는 transaction 종료와 `reset.sql`만 수행하고 server/cache를 재시작하거나 flush하지 않는다. 따라서 뒤의 두 반복은 warm run으로 분류한다. 시간값은 oracle이 아니며 cache를 통제한 성능 비교로 해석하지 않는다.

Use this exact common observer-effect disclosure:

> `SLEEP`은 정상 업무보다 lock lifetime을 인위적으로 늘려 capture window를 만든다. `lockdb`는 별도 administrative transaction을 만들고 lock table을 순회하므로 transaction 목록과 scheduling을 교란할 수 있다. Debug build, csql 출력, polling도 지연을 더한다. 따라서 wait duration, polling attempt, transaction index, OID, MVCCID, dump order는 채점하지 않는다. 같은 resource block의 identity/mode relation, SQL-visible final invariant, 정상 transaction cleanup만 채점한다.

Every repetition gets its own `observed/rK/` directory. The capture script accepts exactly one numeric repetition argument, writes only there, and fails if the directory/file already exists. It parses complete resource blocks rather than grepping unrelated mode strings. The post-run verifier must check both the direct csql stdout invariant and the repetition's complete lock block. If capture misses, preserve the failed receipt and retry under a new suffix; never rewrite an immutable run directory.

## 4. Experiment-specific revisions

### Experiment 1 — hierarchy only

Keep one successful combined observation (`exp1-observe-r3` plus `exp1-lockdb-r3`) and `repetitions: 1`. Replace the scope paragraph in `experiment.md` with:

> 이 runtime case가 직접 관찰한 범위는 한 `SELECT ... FOR UPDATE` transaction이 서로 다른 class resource의 `IX_LOCK`과 선택 instance resource의 `X_LOCK`을 동시에 보유한다는 hierarchy 한 가지다. 두 holder는 같은 `tran_index=1`로 기록되었고 resource key는 class OID와 instance OID로 달랐다. 이 SQL은 기존 mode에 새 mode를 더하는 conversion을 실행하지 않았고 instance-lock threshold를 넘기지 않았으므로 `lock_Conv`, `SIX`, escalation trigger/replace 동작은 runtime으로 검증하지 않았다. Conversion과 escalation 설명은 pinned source에만 근거하며 `CUBRID-C040`의 runtime 범위에 포함하지 않는다.

Add these exact Evidence links:

- mandatory csql: `../../evidence/runs/exp1-observe-r3/{meta.json,stdout.txt,stderr.txt}`;
- auxiliary dump: `../../evidence/runs/exp1-lockdb-r3/{meta.json,stdout.txt,stderr.txt}`;
- cleanup: `../../evidence/runs/exp1-cleanup-r3/meta.json`;
- build/runtime: `../../evidence/runs/runtime-baseline-build-2/meta.json`, `../../evidence/runtime-tools-baseline.json`.

State the existing mandatory argv exactly as the current manifest does. The successful run is warm relative to the preceding `exp1-observe-r2` attempt on the same newly created DB; no cache reset occurred. The accepted runtime invariant is only “same owner, distinct class/instance resource, IX/X relation.” `exp1-lockdb-r2` failed to catch the hierarchy predicate and is a disclosed failed auxiliary attempt, not a successful repetition.

Strengthen future `capture.sh` even if Experiment 1 is not rerun: parse one `Class = dba.e1_account` block and one `Instance ... = dba.e1_account` block, extract holder `tran_index`, require the class holder's `Granted_mode = IX_LOCK`, the instance holder's `Granted_mode = X_LOCK`, and require identical non-`lockdb` transaction indices.

Manifest stays:

```json
"run_ids": ["exp1-observe-r3"],
"repetitions": 1
```

Do not add `exp1-lockdb-r3` to manifest `run_ids`; it is auxiliary and its argv is not the mandatory direct-csql runner. Keep it in the runtime Claim's supporting IDs if the Claim schema permits auxiliary runs.

### Experiment 2 — one-way wait/release only; deadlock untested

Replace the scope paragraph with:

> 이 runtime case에는 transaction 두 개와 row 하나만 있다. T1의 instance `X_LOCK`을 T2의 `X_LOCK` 요청이 한 방향으로 기다리고, T1 rollback 뒤 T2가 진행해 `balance=101`을 commit하는 wait/release만 검증한다. 상호 wait edge가 없으므로 cycle, deadlock detector 실행, victim selection, victim의 선행 변경 rollback은 runtime으로 전혀 시험하지 않았다. `wait-deadlock-release` 장의 deadlock 부분은 pinned source 근거이며 `CUBRID-C041`의 runtime 결과로 표현하지 않는다.

Use three fresh accepted repetitions: `r3`, `r4`, `r5`. Change only `holder.sql` capture window from `SLEEP (60.0)` to `SLEEP (12.0)` after proving readiness polling completes with adequate margin. Keep `observe.sql` bytes unchanged so its current SHA-256 and mandatory argv remain valid. Add `reset.sql` before every repetition, including the first after schema setup.

Required invariant per repetition:

- direct csql exits zero and stdout contains exactly the result row `id=1, balance=101`;
- one complete instance resource block for `dba.e2_account` contains X holder and X waiter simultaneously;
- holder exits zero after rollback;
- exact recorded actor transaction indices do not remain holders/waiters in a post-run dump;
- no statement timeout or deadlock error occurs.

The lock relation, not elapsed time, proves waiting. Poll count and wait duration may vary. `exp2-observe-r1/r2` are historical one-way confirmations; use them in a historical table if desired, but the revised manifest should bind the homogeneous fresh `r3`–`r5` series.

Revised manifest fields:

```json
"run_ids": ["exp2-observe-r3", "exp2-observe-r4", "exp2-observe-r5"],
"repetitions": 3,
"oracle_ko": "세 반복 모두 동일 instance block의 X holder/X waiter를 보였고 holder rollback 뒤 direct observer가 balance 101을 commit했다. deadlock은 실행하지 않았다.",
"controls_ko": "같은 row의 contended block이 positive control이고 reset된 committed 100 및 post-run target transaction 부재가 negative/lifecycle controls다.",
"alternative_explanations_ko": "단순 sleep 지연은 lockdb의 same-resource X waiter로 배제한다. 이 one-way wait에는 cycle이나 victim이 없으므로 deadlock 정책 근거로 사용하지 않는다."
```

### Experiment 3 — MVCC visibility versus locked-read exclusion

Use three fresh repetitions `r2`, `r3`, `r4`; keep `observe.sql` unchanged and add `reset.sql`:

```sql
UPDATE dba.e3_account
   SET balance = CASE id WHEN 1 THEN 100 ELSE 200 END;
COMMIT;
```

Reduce holder `SLEEP` to 12 seconds only after readiness polling is in place. Required invariant per repetition:

- stdout, in statement order: `plain=100`, `locked=100`, `final=101`;
- while the locked statement is pending, one `dba.e3_account` instance block has T1 X holder and T2 X waiter;
- the plain result appears before the locked wait capture, but no numeric latency threshold is used;
- holder rollback and observer commit both exit zero;
- target actor locks disappear afterward.

Do not say runtime identified `locator_mvcc_reev_cond_and_assignment`; runtime behavior is consistent with a post-wait decision, while exact function/restart path is source-confirmed. Do not generalize from the captured `COMMITTED READ` case to other isolation levels.

Revised manifest:

```json
"run_ids": ["exp3-observe-r2", "exp3-observe-r3", "exp3-observe-r4"],
"repetitions": 3,
"oracle_ko": "세 반복 모두 active writer의 900 동안 plain=100을 먼저 출력하고, 동일 instance의 X waiter가 된 locked read는 holder rollback 뒤 locked=100, final=101을 출력한다.",
"controls_ko": "plain read는 visibility negative-wait control, 같은 row FOR UPDATE는 positive-wait control, rollback과 final 101은 post-wait state decision control이다.",
"alternative_explanations_ko": "lockdb same-instance X waiter가 latch-only 또는 단순 출력 지연 설명을 배제한다. exact re-evaluation 함수와 다른 isolation level은 이 runtime case가 증명하지 않는다."
```

### Experiment 4 — MVCCID self-lock rendezvous

Use three fresh repetitions `r2`, `r3`, `r4`. Add `reset.sql`:

```sql
DELETE FROM dba.e4_unique;
COMMIT;
```

Reduce holder `SLEEP` to 12 seconds only after X self-lock readiness is detected. Required invariant per repetition:

- one complete literal `Transaction self-lock (inserter MVCCID = N)` block has inserter X holder and observer S waiter;
- resource MVCCID, holder `tran_index`, waiter `tran_index` are captured as separate fields; numeric equality is not expected;
- holder rollback and observer both exit zero;
- stdout contains only `id=7, note_text=observer-after-wait` for the queried key;
- the exact captured MVCCID resource and both actor transaction indices are absent after completion.

MVCCID and `tran_index` values vary by repetition and are reported, never compared to constants. Runtime does not directly expose page-unfix, inactive-bit publication instruction, root restart, scaling benefit, fallback, or prepared-2PC conversion.

Revised manifest:

```json
"run_ids": ["exp4-observe-r2", "exp4-observe-r3", "exp4-observe-r4"],
"repetitions": 3,
"oracle_ko": "세 반복 모두 한 MVCCID transaction-resource block에서 inserter X holder와 observer S waiter가 나타났고 rollback 뒤 observer key 7 insert가 성공했다.",
"controls_ko": "literal transaction-resource label과 same-block X/S relation이 resource-type control이고 holder rollback 및 exact MVCCID post-run 부재가 lifecycle control이다.",
"alternative_explanations_ko": "transaction-resource dump가 row-lock-only 및 latch-only 설명을 배제하지만 page-unfix/root-restart instruction, fallback, 2PC, scaling은 source 또는 별도 실험 범위다."
```

## 5. Exact proposed repetition run IDs and reportctl command shapes

The following IDs were absent at audit time. Recheck before use; receipts are immutable. The direct observation runner bytes must remain unchanged and its SHA-256 must match the manifest. `setup.sql`, `reset.sql`, `holder.sql`, and `observe.sql` are each captured directly by csql; supporting shell scripts never substitute for a mandatory direct observation.

### Run-ID matrix

| Experiment | Provision/schema/config | Repetition K | Reset | Holder | Mandatory direct observer | Lock capture | Invariant/post check | Cleanup |
|---|---|---:|---|---|---|---|---|---|
| 2 | `exp2-provision-audit`, `exp2-schema-audit`, `exp2-paramdump-audit`, `exp2-session-config-audit` | 3 | `exp2-reset-r3` | `exp2-holder-r3` | `exp2-observe-r3` | `exp2-lockdb-r3` | `exp2-verify-r3` | rowspan below |
| 2 | same DB | 4 | `exp2-reset-r4` | `exp2-holder-r4` | `exp2-observe-r4` | `exp2-lockdb-r4` | `exp2-verify-r4` | rowspan below |
| 2 | same DB | 5 | `exp2-reset-r5` | `exp2-holder-r5` | `exp2-observe-r5` | `exp2-lockdb-r5` | `exp2-verify-r5` | `exp2-cleanup-audit` |
| 3 | `exp3-provision-audit`, `exp3-schema-audit`, `exp3-paramdump-audit`, `exp3-session-config-audit` | 2 | `exp3-reset-r2` | `exp3-holder-r2` | `exp3-observe-r2` | `exp3-lockdb-r2` | `exp3-verify-r2` | rowspan below |
| 3 | same DB | 3 | `exp3-reset-r3` | `exp3-holder-r3` | `exp3-observe-r3` | `exp3-lockdb-r3` | `exp3-verify-r3` | rowspan below |
| 3 | same DB | 4 | `exp3-reset-r4` | `exp3-holder-r4` | `exp3-observe-r4` | `exp3-lockdb-r4` | `exp3-verify-r4` | `exp3-cleanup-audit` |
| 4 | `exp4-provision-audit`, `exp4-schema-audit`, `exp4-paramdump-audit`, `exp4-session-config-audit` | 2 | `exp4-reset-r2` | `exp4-holder-r2` | `exp4-observe-r2` | `exp4-lockdb-r2` | `exp4-verify-r2` | rowspan below |
| 4 | same DB | 3 | `exp4-reset-r3` | `exp4-holder-r3` | `exp4-observe-r3` | `exp4-lockdb-r3` | `exp4-verify-r3` | rowspan below |
| 4 | same DB | 4 | `exp4-reset-r4` | `exp4-holder-r4` | `exp4-observe-r4` | `exp4-lockdb-r4` | `exp4-verify-r4` | `exp4-cleanup-audit` |

Do not literally use `rowspan below`; it only denotes one cleanup after the three rows.

### Exact command pattern

For Experiment `N`, expand `E` to the literal Experiment directory and `DB` to `calockeNf30`. The commands below are exact after replacing the enumerated `N` and `K` with a row from the matrix; do not add a wrapper around the csql command after `--`.

Provision:

```bash
python3 /home/vimkim/.agents/skills/cubrid-code-analysis-report/scripts/reportctl.py record \
  --report-dir /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex \
  --id expN-provision-audit \
  --cwd /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/experiments/experiment-N \
  --expect-exit 0 --runtime-tools-snapshot evidence/runtime-tools-baseline.json \
  -- bash setup.sh
```

Schema or reset direct csql (`INPUT` is exactly `setup.sql` or `reset.sql`, with the matching matrix ID):

```bash
python3 /home/vimkim/.agents/skills/cubrid-code-analysis-report/scripts/reportctl.py record \
  --report-dir /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex \
  --id expN-schema-or-reset-id \
  --cwd /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/experiments/experiment-N \
  --expect-exit 0 --runtime-tools-snapshot evidence/runtime-tools-baseline.json \
  -- /home/vimkim/.cub/install/cubrid-analysis/debug_gcc/bin/csql -C -u dba --no-auto-commit -i INPUT -t calockeNf30
```

Start the holder through the host's asynchronous execution facility; the recorded argv after `--` remains direct csql:

```bash
python3 /home/vimkim/.agents/skills/cubrid-code-analysis-report/scripts/reportctl.py record \
  --report-dir /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex \
  --id expN-holder-rK \
  --cwd /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/experiments/experiment-N \
  --expect-exit 0 --runtime-tools-snapshot evidence/runtime-tools-baseline.json \
  -- /home/vimkim/.cub/install/cubrid-analysis/debug_gcc/bin/csql -C -u dba --no-auto-commit -i holder.sql -t calockeNf30
```

Do not start the observer until a separately captured readiness poll has seen the intended holder resource. Then start this command asynchronously:

```bash
python3 /home/vimkim/.agents/skills/cubrid-code-analysis-report/scripts/reportctl.py record \
  --report-dir /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex \
  --id expN-observe-rK \
  --cwd /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/experiments/experiment-N \
  --expect-exit 0 --runtime-tools-snapshot evidence/runtime-tools-baseline.json \
  -- /home/vimkim/.cub/install/cubrid-analysis/debug_gcc/bin/csql -C -u dba --no-auto-commit -i observe.sql -t calockeNf30
```

Capture and verify while the direct observer is pending:

```bash
python3 /home/vimkim/.agents/skills/cubrid-code-analysis-report/scripts/reportctl.py record \
  --report-dir /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex \
  --id expN-lockdb-rK \
  --cwd /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/experiments/experiment-N \
  --expect-exit 0 --runtime-tools-snapshot evidence/runtime-tools-baseline.json \
  -- bash capture.sh K

python3 /home/vimkim/.agents/skills/cubrid-code-analysis-report/scripts/reportctl.py record \
  --report-dir /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex \
  --id expN-verify-rK \
  --cwd /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/experiments/experiment-N \
  --expect-exit 0 --runtime-tools-snapshot evidence/runtime-tools-baseline.json \
  -- bash verify-repetition.sh K
```

Cleanup after all three repetitions:

```bash
python3 /home/vimkim/.agents/skills/cubrid-code-analysis-report/scripts/reportctl.py record \
  --report-dir /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex \
  --id expN-cleanup-audit \
  --cwd /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/experiments/experiment-N \
  --expect-exit 0 --runtime-tools-snapshot evidence/runtime-tools-baseline.json \
  -- bash cleanup.sh
```

`verify-repetition.sh K` must read the immutable direct receipt at `../../evidence/runs/expN-observe-rK/stdout.txt`, not a copied/transcribed output. It should also calculate observation elapsed time from `started_at_utc` and `finished_at_utc` only for a variability table. Report min/median/max descriptively, with the explicit statement that they are scheduler/capture-window measurements and not performance results.

## 6. Common safe Quiz artifact design

Each Quiz must contain `quiz.md`, `answer.md`, `setup.sql`, neutral `session-a.sql` and optional `session-b.sql`, `run.sh`, and `cleanup.sh`. Remove `cleanup.sql`. `raw-output/` is created at runtime and contains a unique `run.XXXXXX/`, preserving learner output without overwriting earlier results.

### Required `quiz.md` sections

Use these headings in every Quiz:

1. `학습 목표`
2. `선행 지식과 준비물`
3. `예상 시간`
4. `실행 전 예측`
5. `안전한 실행 명령`
6. `관찰할 것`
7. `분석과 teach-back`
8. `Cleanup과 재실행`
9. `연결 장과 Claim`

The prerequisites must state: Bash, the exact sealed CUBRID debug runtime above, no PostgreSQL/MySQL server, no existing DB with the Quiz name, and permission only for the Quiz-owned DB. The exact learner command is:

```bash
cd /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/quiz/quiz-N
bash ./run.sh
```

State: if the database already exists, `run.sh` exits 73 before any SQL or server mutation. It never stops a global service. Successful or failed runs invoke exact owner-verified cleanup. If the shell is forcibly killed before the trap, run `bash ./cleanup.sh`; it refuses without an exact owner marker and matching registry paths. Never advise manual `cubrid deletedb` as a shortcut.

### Required ownership marker

The runner must use the fixed DB name `qalockqNf30`, explicit volume/log directories under `quiz/quiz-N/runtime/`, and `.quiz-owner`. Before `createdb`, verify the name is absent from registry field 1. The marker must bind:

```text
state=reserved-or-owned
quiz_id=quiz-N
db_name=qalockqNf30
report_dir=/home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex
source_revision=f30f1c26003e5aa8e93182648e06cad76fc77064
registry=/home/vimkim/.cub/db/cubrid-analysis/commondb/databases.txt
volume_path=<absolute quiz-N/runtime/db>
log_path=<absolute quiz-N/runtime/log>
nonce=<fresh invocation nonce>
```

The marker is written in `reserved` state before `createdb` and becomes `owned` only after the registry row exactly matches both paths. `cleanup.sh` validates all fixed fields plus the exact registry row. It stops only `qalockqNf30`, calls `deletedb` only on that matching row, verifies absence, removes the exact marker, and uses `rmdir` only for known empty runtime directories. A missing/mismatched marker is a hard refusal, not a reason to delete by name.

### Required noninteractive `run.sh` behavior

`run.sh` must:

1. run `set -euo pipefail` and verify SHA-256 of the exact `csql` and `cubrid` binaries against the sealed snapshot values;
2. refuse pre-existing DB/stale marker/runtime ownership before mutation;
3. create one unique `raw-output/run.XXXXXX` directory with `mktemp -d`;
4. provision the explicit-path DB and write/validate the owner marker;
5. start only this DB and run `setup.sql` with exact `csql -C -u dba --no-auto-commit -i setup.sql -t <DB>`;
6. start neutral session files with exact csql argv and record child PIDs;
7. for concurrency cases, allow a bounded readiness interval, then save raw full/contended `lockdb` without parsing answer-bearing modes in the learner script;
8. wait for all csql children and return nonzero if any child fails;
9. on `EXIT`, `INT`, or `TERM`, validate any surviving PID's `/proc/<pid>/cmdline` contains the exact csql path, SQL file, cwd, and DB before signaling it;
10. call owner-verified `cleanup.sh`; preserve only raw learner output.

Do not put `IX`, `X holder`, `S waiter`, victim, expected values, or “self-lock” in script comments or output filenames. The raw dump may naturally contain those values after the learner has made a prediction.

The runner is idempotent in this precise sense: after a successful cleanup it can run again and creates a new raw-output directory. It must not silently take over a stale owner marker or pre-existing DB.

## 7. Quiz-specific exact revisions

### Quiz 1 — resource/mode/hierarchy

- Final `quiz.md` title: `Quiz 1 — 한 locked read의 잠금 지도 그리기`. Do not retain “두 resource” in the title because it leaks the first prediction.
- Database: `qalockq1f30`
- Expected time: 20 minutes
- Sessions: only `session-a.sql`; start it asynchronously, wait a bounded 2 seconds, save full `cubrid lockdb qalockq1f30`, then wait for rollback.
- Pre-run prediction table columns: `statement`, `resource type/key`, `mode`, `owner`, `lifetime`, `wait 가능성`.
- Observe: two target resource blocks, their OIDs, both holder `tran_index` values, and post-rollback absence. Ask the learner to distinguish the lockdb administrative transaction.
- Explain: why class intent does not replace instance lock; compatibility is applied after resource identity; conversion and escalation are source/table thought exercises only.
- Related: `chapters/03-interface-and-resources.html#resource-mode-hierarchy`; Claims `CUBRID-C001`, `CUBRID-C002`, `CUBRID-C003`, `CUBRID-C004`, `CUBRID-C040`.
- `answer.md` must accept variable OID/transaction order, explain same-owner IX/X causality, list misconceptions (IX as row lock, `tran_index` as OID/MVCCID, one dump proving escalation), and state that Quiz 1 does not execute conversion/escalation or quantify overhead.

### Quiz 2 — one-way wait/release and unexecuted deadlock reasoning

- Final `quiz.md` title: `Quiz 2 — 기다리던 UPDATE의 종료 경로`.
- Database: `qalockq2f30`
- Expected time: 25 minutes
- Sessions: start `session-a.sql`, wait 2 seconds, start `session-b.sql`, wait 2 seconds, save `cubrid lockdb -c qalockq2f30`, then wait for both.
- Pre-run prediction table: `T1 state`, `T2 state`, `resource`, `holder mode`, `waiter mode`, `rollback 후 SQL-visible result`.
- Observe: one same-instance holder/waiter block and final row output. Do not claim the Quiz ran a cycle.
- Explain: enqueue/suspend, rollback release, wake/grant, operation resume, final commit; then design—but do not run unless separately supplied—a deadlock test with victim-independent atomic invariants.
- Related: `chapters/06-wait-deadlock-release.html#wait-deadlock-release`; Claims `CUBRID-C010`, `CUBRID-C011`, `CUBRID-C012`, `CUBRID-C041`.
- `answer.md` must add misconceptions (SLEEP itself caused result; wakeup equals commit; one-way wait proves deadlock detector) and limits (no timeout/interrupt/cycle/victim/starvation test).

### Quiz 3 — MVCC visibility and locked-read exclusion

- Final `quiz.md` title: `Quiz 3 — 동시 읽기와 변경 결과 예측하기`.
- Database: `qalockq3f30`
- Expected time: 25 minutes
- Sessions/capture: same neutral two-session sequence as Quiz 2, using `lockdb -c qalockq3f30`.
- Pre-run prediction table for each `session-b.sql` statement: `visible value`, `instance mode`, `can wait`, `post-wait recheck 필요성`.
- Observe ordered direct output and the contended instance block. Ask why plain 100 does not prove the whole statement is lock-free.
- Explain snapshot visibility versus class IX/instance X exclusion, post-wait state decision, and seam separation from a page latch.
- Related: `chapters/07-mvcc-lock-policy.html#mvcc-lock-policy`; Claims `CUBRID-C020`, `CUBRID-C021`, `CUBRID-C022`, `CUBRID-C027`, `CUBRID-C042`.
- `answer.md` must add misconceptions (MVCC means no lock anywhere; 100 proves no wait; page latch equals transaction lock; pre-wait tuple remains valid) and limits (only recorded COMMITTED READ, rollback holder, one row; exact function and other isolation levels not proved).

### Quiz 4 — MVCCID rendezvous

- Final `quiz.md` title: `Quiz 4 — 끝나지 않은 inserter를 만났을 때`. Do not put `MVCCID`, “transaction resource”, or “self-lock” in the title or pre-run procedure; they are answers the learner must predict.
- Database: `qalockq4f30`
- Expected time: 30 minutes
- Sessions/capture: start `session-a.sql`, wait 2 seconds, start `session-b.sql`, wait 2 seconds, save `cubrid lockdb -c qalockq4f30`, then wait for both.
- Pre-run prediction: choose among row OID, class OID, `tran_index`, TRANID, and MVCCID; separately predict holder and waiter modes and name a falsifier.
- Observe: literal transaction-resource label, resource MVCCID, holder/waiter transaction indices, modes, and final rows. The different-key insert is the negative control.
- Explain: why “self” names inserter ownership, ordinary X/S compatibility on a different resource identity, why S grant requires re-read, publication/release ordering, and per-row versus per-MVCCID trade-off.
- Related: `chapters/08-mvccid-self-lock.html#mvccid-self-lock-rendezvous`; Claims `CUBRID-C030`, `CUBRID-C031`, `CUBRID-C032`, `CUBRID-C043`.
- `answer.md` must add misconceptions (`tran_index == MVCCID`; self-lock is self-deadlock; S permanently protects the key; this removes every row X) and limits (one unique rollback case; no FK, page-unfix/root restart instruction, scaling, fallback, or prepared-2PC runtime proof).

## 8. One-run validation plan for every exact Quiz

After the final Quiz files are written, hash them, run shell syntax validation, then run each exact Quiz once. These are Quiz validation receipts; they do not replace Experiment mandatory direct-csql runs and need not be added to Experiment manifests.

For `N=1,2,3,4`, first capture syntax validation:

```bash
python3 /home/vimkim/.agents/skills/cubrid-code-analysis-report/scripts/reportctl.py record \
  --report-dir /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex \
  --id quizN-bash-n-audit \
  --cwd /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/quiz/quiz-N \
  --expect-exit 0 \
  -- bash -n run.sh cleanup.sh
```

Then recheck that `qalockqNf30` is absent and capture the real run:

```bash
python3 /home/vimkim/.agents/skills/cubrid-code-analysis-report/scripts/reportctl.py record \
  --report-dir /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex \
  --id quizN-run-audit-r1 \
  --cwd /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/quiz/quiz-N \
  --expect-exit 0 \
  --runtime-tools-snapshot evidence/runtime-tools-baseline.json \
  -- bash run.sh
```

Accepted evidence for each Quiz consists of: exit zero; csql session stdout/stderr in its unique raw-output directory; a raw lock dump for the intended capture window; exact database row absence after cleanup; no surviving recorded child; and `answer.md` matching observed values/resource relations. Add a short `validation.md` in the Quiz directory linking the successful receipt and naming the raw-output directory. Do not copy an answer into `quiz.md`.

Proposed Quiz run IDs:

```text
quiz1-bash-n-audit       quiz1-run-audit-r1
quiz2-bash-n-audit       quiz2-run-audit-r1
quiz3-bash-n-audit       quiz3-run-audit-r1
quiz4-bash-n-audit       quiz4-run-audit-r1
```

If a pre-existing DB is found, the correct validation result is refusal/stop; do not delete it and do not switch the Quiz to a user DB. Choose a new fixed unique Quiz name in all artifacts only through an explicit coordinated revision.

## 9. Manifest and Claim integration checklist for the main agent

After successful runs only:

1. Recompute `runner_sha256` from the final `observe.sql`. It should remain the current value when this packet says to keep bytes unchanged.
2. Confirm every manifest `runner_argv` byte-for-byte equals each declared observation receipt's `argv` and each run used the Experiment directory as cwd.
3. Set Experiment 2 run IDs to r3–r5, Experiment 3 to r2–r4, and Experiment 4 to r2–r4; set repetitions to 3. Keep Experiment 1 at one accepted run and narrow it to hierarchy.
4. Keep lockdb/config/setup/reset/holder/verify/cleanup IDs out of manifest `run_ids`; link them in `experiment.md` and the runtime Claim as supporting evidence where applicable.
5. Update the corresponding runtime Claim IDs only after receipts exist: `CUBRID-C041`, `CUBRID-C042`, `CUBRID-C043`. Do not broaden `CUBRID-C040` or `CUBRID-C041` to conversion/escalation or deadlock.
6. For each new series, add a table with run ID, exact stdout invariant, parsed resource/modes, variable identities, elapsed time, warm/cold classification, and pass/fail. A value row alone is insufficient without the matching lock resource block.
7. Link exact cleanup receipts and keep `cleanup_verified=true` only after registry/path/process checks succeed.
8. Re-run the report verifier/audit after the sole final-artifact writer integrates these material changes.

## 10. Unknowns and hard stops

- The proposed 12-second holder window is expected to be practical on this debug runtime, but readiness and contention capture—not the number 12—are authoritative. If readiness consumes the window, preserve the failure and redesign; do not lengthen repeatedly until a desired answer appears without disclosing the change.
- `lockdb` block text is partly message-catalog dependent. Inspect the first new dump manually before relying on an awk parser; preserve raw bytes.
- `paramdump` may include parameters irrelevant to locking. Link the full receipt and summarize only exact effective values relevant to the experiment.
- A process, registry row, marker, or volume-path mismatch is a hard stop. Never use `rm -rf`, global `cubrid service stop`, or an unverified `deletedb` to recover.
- If a direct observation exits zero but the SQL invariant or complete lock block fails, it is a failed repetition and must not enter the manifest or Claim.
- No instrumentation is needed for these audit gaps. Existing csql, `lockdb`, `paramdump`, registry checks, and SQL-visible results are sufficient.
