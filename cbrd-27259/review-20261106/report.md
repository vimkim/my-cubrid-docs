# Review report: CUBRID PR #8416 (CBRD-27259)

**Goal.** Find real defects in STORAGE FORCE_INLINE, fixed-type STORAGE DEFAULT and the ER_HEAP_BIGONE_WITHOUT_OOS (-1393) notification before merge.

**Most consequential result.** The storage rules are correct. No path traced places a FORCE_INLINE value in OOS, and no path wrongly accepts or rejects a record. The confirmed defects are all in the new -1393 notification: it reports some rows that were never stored as REC_BIGONE (SYS-1, F1).

## Verdict
- **Verdict:** `changes-required` (P3 only).
- **Follow-up review required:** yes, but only a delta review after a fix to the notification, plus the open risks below. None of these is a data-correctness blocker.

**Snapshot**
- base = merge base: d52b1889e907abcf84190ec504dde3bc93de260d
- head: 9ae07b9491b1393841ecb0f3579752a598bf68ec
- patch sha256: e7ffb9028b12bb73c69a075b0adabb01eb57f1a7a0883ff9157e83ea5dce990d

## Confirmed findings

### R1 (P3). -1393 reports rows that are never stored, and reports some rows twice (SYS-1)
- **Location.** `src/storage/heap_file.c:14271-14274` (`heap_attrinfo_transform_to_disk_internal`). The report fires when the record is laid out. The heap write happens later. Other callers also lay out the record:
  - REPLACE duplicate removal (`query_executor.c:12661`)
  - ODKU lookup (`query_executor.c:12887`)
  - MVCC re-evaluation (`locator_sr.c:14002`). Source only.
- **Coordinator replay.** Script: `coordinator/replay_sys1.sh`. Setup: SA install at `~/.cub/install/CBRD-27259-storage-force-inline/debug_gcc`, table `q(id INT PK, a BIT VARYING STORAGE FORCE_INLINE)`, 17000-byte random value.

  | Statement | Reports | Rows stored |
  |---|---|---|
  | New INSERT | 1 | 1 |
  | REPLACE on an existing key | 2 | 1 |
  | Duplicate-key INSERT that fails with a unique violation | 1 | 0 |

  Final `count(*) = 1`. Expected one report per stored REC_BIGONE row.
- **Attribution.** The notification is new in this PR.
- **Impact.** The message says the record "is stored as ... REC_BIGONE", which is false here. Diagnostics mislead and the log grows faster. Data is correct.
- **Fix direction.** Report at the heap write, where a record without OOS values actually becomes REC_BIGONE. Otherwise, skip the report in the builders used only for duplicate checks.

### R2 (P3). -1393 fires for records stored as REC_HOME within the 16-byte estimate window (F1, SYS-2)
- **Location.** `heap_file.c:14256`. The estimate adds `OR_MVCC_MAX_HEADER_SIZE - OR_MVCC_INSERT_HEADER_SIZE` (16 bytes) before the check at line 14271.
- **Coordinator replay.** Script: `coordinator/replay_f1.sh`. It inserts 80 FORCE_INLINE varchar rows with random values of 16150 to 16229 characters.
  - 47 -1393 reports, with estimates from 16240 bytes up.
  - `cubrid diagdb -d 9` shows 23 `type = BIGONE` slots.
  - At least 24 reported rows are REC_HOME, with lengths up to 16236.
- **Spec.** The spec (OOS-CONTEXT.md:122) says to report when "the same estimate" exceeds the boundary. The estimate itself conforms; the message text does not.
- **Fix direction.** Either reword the message to say "may need REC_BIGONE", or test the report against the size without the delete-header slack. The -1388 guard has the same conservative window, but that predates this PR.

## Safety facts and effects outside the diff
- **FORCE_INLINE is never a demotion candidate.** Owners: systems and storage-recovery, the shared Q1. Both answered no independently. Evidence level 4/5: unit tests plus SA probes of INSERT, UPDATE and loaddb. Paths traced in source: partition move, ALTER type change, compactdb (CS) and serial.
- **-1388 and -1393 are mutually exclusive and run before any OOS insert.** Owner: systems. Level 4/5. No orphan chain remains on -1388.
- **The caller's error state is preserved.** Owners: systems and ha-concurrency. Level 3, plus successful writes observed.
- **Redo, undo and vacuum never re-run the layout.** Owner: storage-recovery. Level 3 from source, plus a crash and restart run. In that run the uncommitted -1393 insert was undone and no report appeared during recovery.
- **DDL policy semantics, partitions, subclasses, LIKE, unloaddb/loaddb round trip and SHOW CREATE re-parse.** Owner: schema. Level 5, with all accepted spec rules checked.
- **FORCE_INLINE is a non-reserved keyword.** Owner: schema. Level 5. The 8 new bison conflicts share the existing FORCE_OUTLINE states.
- **HA DDL travels as the user's SQL text.** Owners: schema and ha-concurrency. Level 3. The policy order matches through the class X lock and commit-order replay.

## Unverified risks
- **U1 (SYS-3/HC-2, design).** Every qualifying write produces one unthrottled log line of about 550 B under the global error-log mutex. This needs no FORCE_INLINE opt-in: large fixed columns such as `BIT(n)` and wide tables qualify too. Debug SA measured 3000 rows: 2.15/1.32 s with logging versus 0.79/0.83 s without. That is indicative only. Next check: a release server with concurrent sessions, logging on versus off. A design option is to report once per class or once per time window.
- **U2 (HC-3).** The spec says root and system class records are outside the rule. No exemption was found on the server `heap_attrinfo_transform_to_disk` path; known system-class users such as serial and dblink write tiny records. Next check: a system-class row above 16 KB, for example a large stored procedure source, then grep the log for -1393.
- **U3 (HC-1).** On the MVCC re-evaluation path the report is written while the heap home page latch is held. Precedent exists (`heap_oos_diagnose_skipped_cleanup`). The latch mode and contention were not measured. R1's fix at the heap write would also move this site.
- **U4 (reviewer disagreement, not material).** On HA row apply, ha-concurrency says the replica lays the row out again (`la_disk_to_obj` → `locator_finalize_oos_record`). Systems says `xlocator_repl_force` stores the master image as is. Both conclude that no divergence and no extra -1388 occur. Unresolved: whether the replica also logs -1393. Next check: a real master/replica pair.
- **D1 (F2, spec-conformant, product decision).** After `ALTER ... STORAGE FORCE_INLINE`, an UPDATE of an unrelated column on an old row can fail with -1388. This happens when a small value gets demoted but cannot rescue the large inline value. The behaviour follows OOS-CONTEXT.md:104 and ties to the deferred CBRD-27230 decision.

## Dropped or rejected
- **schema.** 0 candidates. Notes N1 (missing unit tests for partition and round trip), N2 (enum comment style) and N3 (`catcls_filter_attflag` predates the PR) are not defects.
- **storage-recovery.** O1 (report on a later-failing statement) merged into R1. O2 (`DB_PAGESIZE/4` against `heap_oos_inline_target_size()`) predates the PR.
- **systems.** OLD-1 (offline compactdb bypass) and OLD-2 (cubrid-cci error codes) predate the PR.
- **ha-concurrency.** HC-4 (`pt_print_attr_def` gap) has a known separate JIRA. HC-5: enum bit-fields would be signed under MSVC. That is source-only; the 3-bit field holding values 0..5 is unsigned on GCC. Kept as information.

## Coverage and checks
See `coverage.md`. Reviewer reports are under `reviewers/*/report.md`. The schema and systems reports were saved by the coordinator from the hand-back text, because the harness blocked subagent file writes.

Checks:
- `test_oos_sql_storage`: 43/43 passed. Systems and schema each ran it independently.
- Many SA csql, unloaddb, loaddb and diagdb probes, all passed or reproduced as described.
- Coordinator replays R1 and R2 reproduced.

Not run:
- SERVER (CS) mode runtime
- release build
- HA pair
- concurrent ALTER with DML
- throughput in server mode

## Budget
- Mode: best effort, user-approved. There was no enforcement mechanism. 4 reviewer agents, no retries.
- Subagent token totals reported by the harness: 188,553 (systems), 155,678 (storage-recovery), 150,897 (schema) and 179,998 (ha-concurrency).
- Coordinator usage is unknown.
- Compliance with the percentage-of-allowance limit is unverified.
