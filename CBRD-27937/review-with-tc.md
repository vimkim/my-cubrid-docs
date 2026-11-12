# Code review: CUBRID/cubrid#8454 (CBRD-27937) with TC CUBRID/cubrid-testcases-private-ex#4803

## Goal and headline

**Goal.** Encrypted (TDE) tables must not leave their values in plaintext in log volumes. The PR closes the leaks that come from six recovery indexes missing from `LOG_MAY_CONTAIN_USER_DATA`. This review asks two things. First, does the fix close those leaks without breaking recovery or HA? Second, does the paired shell TC prove it reliably?

**Headline.** No confirmed defect in the engine change or the TC.
- On the pre-fix build, the TC fails exactly the five checks it names: 2, 4, 6, 7 and 9.
- On the post-fix build, all ten checks pass, in 16 to 19 seconds.
- Recovery after a crash with the newly encrypted B-tree records succeeded on the head build.

The review also reproduced two plaintext leaks that predate this PR and that it does not address:
- `CREATE TABLE ... ENCRYPT AS SELECT` (R1).
- Supplemental (CDC) undo images with `supplemental_log=1` (R2).

They contradict the PR's broader purpose statement, but not its stated scope. Each needs its own issue.

## Verdict and follow-up

- **Verdict:** `no-confirmed-findings`.
- **Follow-up review required:** no.
  - The open items below are either pre-existing leaks outside the PR's scope (R1, R2, R4), which belong in new issues, or optional measurement and hardening (R3, R5).
  - None needs to happen before merge.
- **Suggested, non-blocking:**
  - Narrow the PR's "Purpose" sentence, or note R1 and R2 as known remaining paths.
  - Consider the TC robustness suggestions T1 to T4.

## Pinned scope

| Repository | Base (= merge base) | Head | Patch sha256 |
|---|---|---|---|
| CUBRID/cubrid | `2b1db6ca296db20d6bc86eba9f7f69e1866ae10e` | `3ee2faece234768fe158986b4ff7e7960ac6c999` | `16312c680f49f89e24bdb7d4bda117cda49a928abfa62193647c85d09fc875bb` |
| CUBRID/cubrid-testcases-private-ex | `a0c66dfbea5a3ba02d7e7baabba33e72702c1c45` | `c6dab13e6450b37897f6961ee898c5fd7eb7fb5b` | `d06af66b2ad37b576e8af18e50e6c36db9c708792ddb4476a271a363bdcded3a` |

Changed paths:
- `src/storage/tde.h`: +6.
- `src/transaction/log_manager.c`: +18/−6.
- `shell/_06_issues/_26_2h/cbrd_27937/cases/cbrd_27937.sh`: added, 252 lines.

Both PRs were rechecked before publication and had not moved.

## Confirmed findings

None.

## What the change does, and the facts that make it safe

**The six indexes now reach an encryption decision against the right page.** Two reviewers traced this independently.

| Record | Writer (head) | Page used | Result |
|---|---|---|---|
| `RVBT_MVCC_DELETE_OBJECT`, `RVBT_MARK_DELETED` | `btree.c:26859`, `26865` (leaf or overflow-OID page, asserted non-NULL) | leaf page | encrypted |
| `RVBT_DELETE_OBJECT_POSTPONE` | `btree.c:26867` through `log_append_postpone`; run postpone writes `RVBT_DELETE_OBJECT_PHYSICAL` with a page (`btree.c:40992`) | leaf page | encrypted |
| Rollback of the above | `RVBT_RECORD_MODIFY_COMPENSATE` with a leaf page (`btree.c:37075`) | leaf page | encrypted (already listed) |
| `RVBT_MVCC_NOTIFY_VACUUM` | `btree_load.c:4792`, `4882`, with `pgptr = NULL` | file header, through the new `file_get_tde_algorithm` branch | encrypted unless the conditional latch fails (R3) |
| `RVVAC_HEAP_RECORD_VACUUM` | `vacuum.c:7575` | heap page | encrypted. Its compensation on vacuum sysop abort is now encrypted too. |
| `RVPGBUF_NEW_PAGE` | `locator_sr.c:14717` (server-side loader page image); file-manager pages | page | encrypted when the page's TDE flag is set. `file_alloc` sets it before logging. |

- **Only the two `btree_load.c` sites reach the new `pgptr == NULL` branch.**
  - Every other undo-only writer of a listed index passes a fixed page.
  - The vfid is the B-tree file being built, which holds the schema lock.
  - `btree_create_file` applies TDE to that file before `btree_load` writes anything.
  - Evidence level 3, consistent across both engine reviewers. Level 5 for the fix: scenario 4 of the TC shows 408 hits pre-fix and 0 post-fix.
- **Recovery, vacuum, CDC and the HA sender all decrypt at page fetch.**
  - `logpb_read_page_from_file`, `logpb_read_page_from_active_log` and `logpb_fetch_from_archive` decrypt every page they read.
  - Keys load in `boot_sr.c:2332`, before `log_initialize` at `boot_sr.c:2433`.
  - Executed check (probe P1 on head):
    1. On an encrypted, indexed table: commit a 1,000-row DELETE, then roll back a 1,000-row DELETE.
    2. `kill -9` the server. cub_master revived it.
    3. Restart recovery ran REDO over 21,365 records and UNDO over 3 transactions.
    4. The table then held exactly 1,000 rows, all with the marker, and `checkdb` passed.
  - Plaintext hits: 0 on head and 1,955 on base. Evidence level 5 for this configuration.
- **No new deadlock.**
  - The new `file_get_tde_algorithm` call is a conditional READ fix of the B-tree file header.
  - The index-build thread holds leaf and overflow pages, not the header.
  - A conditional fix cannot wait, so it cannot join a cycle. Evidence level 3.
- **HA.**
  - applylogdb reads only replication and commit records, so it needs nothing new.
  - Copied logs on replicas are plaintext for every record, before and after the PR, because replication-log TDE is compiled out (`UNSTABLE_TDE_FOR_REPLICATION_LOG`, `log_writer.c:846-925`). This is existing design and out of scope. Evidence level 2.

## TC review (CUBRID/cubrid-testcases-private-ex#4803)

### (1) Fails before the fix, passes after

The runs used native cubrid-testkit with contained, disposable attempts and one selected case. The CTP was upstream `cubrid-testtools` develop `3d5c13c6b6eaa7811cc0c6a875bfe58873f0e031`. The build was debug_gcc.

| Build | Check results | Hits in the NOK messages | Runtime |
|---|---|---|---|
| base `2b1db6c` | NOK: 2, 4, 6, 7, 9. OK: 1, 3, 5, 8, 10 | S1ENCROW 1, S2ENCKEY 1996, S3ENCKEY 1970, S4ENCKEY 408, S5ENCROW 88 | 19 s |
| head `3ee2fae` | all 10 OK | none | 16 s |

This matches the TC's own claim ("Before the fix, checks 2, 4, 6, 7 and 9 are NOK") and the PR's table.

The testkit `verify` helper reported `FAIL: total case count is 22, expected 1`. Its count includes 21 cases that the corpus scan skipped by macro. The run summary shows `Total Execution Case: 1`, with success 1 (head) and fail 1 (base). The verdicts above come from the case's own assertion lines in `test_local.log`.

A first head attempt used a stale local CTP (`9c62858`) that predates `wait_until`. The check failed there with `wait_until: command not found`. That attempt is inconclusive and was not counted.

### (2) Is the plaintext detection reliable?

**False positives (a marker found when the record was encrypted): none expected.**
- The grep reads only `<db>_lgat` and `<db>_lgar*`.
- Statement text reaches the log only through HA or supplemental logging. Both are off in this TC.
- The `check_in_log` controls show that the marker bytes survive as plain text when the table is not encrypted.

**False negatives (the TC passes although a leak exists): possible in principle, measured as not happening now.**
- **Log encryption is per log page.** A plaintext record that shares a page with an encrypted record is hidden.
  - Scenarios 2, 3 and 4 produce hundreds to thousands of hits pre-fix, so masking cannot hide them all.
  - Scenario 1 depends on **one** record (1 hit pre-fix, as in the PR's table). A pre-fix run could pass check 2 whenever that record shares a page with an encrypted one. This weakens regression detection for `RVVAC_HEAP_RECORD_VACUUM` but never causes a false NOK. See T1.
- **Archives.** The shipped `cubrid.conf` has `log_max_archives = 0`.
  - In both runs the trace shows `cat db27937_lgat 'db27937_lgar[0-9]*'` with the glob unexpanded. No archive was ever created, so every check read the full log history in the 20 MB active log.
  - If the TC's log volume ever outgrows the active log, the early scenarios' records could be archived and then removed, and their leaks would go unseen. See T2.
- **Vacuous passes.** Scenarios 1, 3 and 4 have no non-encrypted control.
  - For scenario 1, check 1 guards the precondition by waiting until vacuum has removed the relocated row.
  - Scenarios 3 and 4 have row-count guards but no proof that the logging path ran. In these runs the pre-fix hits (1970 and 408) show the paths did run.
  - Scenario 3 cannot tell a rollback-compensation leak from the DELETE leak on a pre-fix build. It still guards the compensation records post-fix.
- **Wrong-marker matches.** Each marker is unique per table, and controls use distinct markers, so the controls cannot satisfy the encrypted checks.

### (3) Shell TC conventions

**Cleanup.** Verified on the head run:
- `do_cleanup` ran `cubrid server stop`, `cubrid deletedb` and `rm -rf db27937`.
- The attempt's `databases.txt` was empty afterwards and no `cub_server db27937` remained.
- `finish` restored `cubrid.conf` from `cubrid.conf.org`, which undoes `change_db_parameter`.
- `abort_test` is never called inside `$(...)`, so its `exit 1` stops the case.

**Layout.** `cases/<name>.sh`, the DESCRIPTION block, `init test`, and `write_ok`/`write_nok`/`finish` match sibling cases in `_26_2h`.

**Environment.**
- Needs CTP with `wait_until` (cubrid-testtools `af69c00`, CUBRIDQA-1657). CI's CTP develop has it.
- Assumes the default 16K page size for scenario 1's relocation layout.
- Uses `loaddb -C` against a running server and the auto-created TDE key file. No HA, broker or fixed-port assumptions beyond the framework's.

**Runtime.** 16 to 19 seconds per run. The worst case is bounded by `wait_until 120`.

### TC suggestions (non-blocking)

- **T1.** Scenario 1 relies on one vacuum record. Add a non-encrypted twin table with `check_in_log`, or relocate and delete several rows. A pre-fix run would then fail reliably instead of by page placement.
- **T2.** Set a nonzero `log_max_archives` (for example with `change_db_parameter`), or assert that no archive was removed. The checks then cannot lose history silently if the TC grows.
- **T3.** Assert that the precondition ran in scenario 4 (`i_c_e` exists) and in scenario 2 (2,000 rows inserted before the delete). Alternatively, add non-encrypted twins as in scenarios 2 and 5.
- **T4.** Make the internal names (`s4_*` for scenario 1, `s1.log` for scenario 2, and so on) match the scenario numbers, and pin `--db-page-size=16K`, which scenario 1's layout assumes.

## Unverified risks and leaks outside the diff

| ID | Kind | Status | Owner and next check |
|---|---|---|---|
| R1 | Pre-existing leak, reproduced | `CREATE TABLE t (...) ENCRYPT AS SELECT ...` logs the inserted rows and keys in plaintext | New CBRD issue |
| R2 | Pre-existing leak, reproduced | `supplemental_log=1` logs full row images of encrypted tables in plaintext on DELETE | New CBRD issue |
| R3 | Introduced pattern, source only | Fail-open fallback and a stale error in the new branch | Optional hardening |
| R4 | Pre-existing, source only | `LOG_SYSOP_START_POSTPONE` copies a sysop's logical-undo key unencrypted | Include in the R2 issue or a separate one |
| R5 | Cost, model only | One header fix and unfix per `RVBT_MVCC_NOTIFY_VACUUM`, on every table | Optional benchmark |

**R1. CTAS on an encrypted table logs its rows in plaintext.** Pre-existing, evidence level 5.
- Root cause: `do_create_entity` runs the INSERT ... SELECT ([`execute_schema.c:10263`](https://github.com/CUBRID/cubrid/blob/3ee2faece234768fe158986b4ff7e7960ac6c999/src/query/execute_schema.c#L10263)) before `file_apply_tde_to_class_files` ([`execute_schema.c:10308`](https://github.com/CUBRID/cubrid/blob/3ee2faece234768fe158986b4ff7e7960ac6c999/src/query/execute_schema.c#L10308)). The heap and index files carry no TDE flag while the rows and keys are logged.
- Probe (2,000 rows, debug build, hits after a flushing commit):

| Statement | Head | Base |
|---|---|---|
| CTAS with a primary key | 5,894 | 6,014 |
| CTAS without an index | 1,875 | 1,875 |
| `CREATE TABLE ... ENCRYPT` then `INSERT ... SELECT` | 0 | 0 |

- `db_class.tde_algorithm` is `AES` for all three tables.
- Fix direction: apply TDE to the class files before running the CTAS insert.

**R2. Supplemental (CDC) undo images bypass TDE.** Pre-existing, evidence level 5.
- `log_append_supplemental_undo_record` ([`log_manager.c:5039`](https://github.com/CUBRID/cubrid/blob/3ee2faece234768fe158986b4ff7e7960ac6c999/src/transaction/log_manager.c#L5039)) passes the row to `log_append_supplemental_info` with `RV_NOT_DEFINED` and never calls `prior_set_tde_encrypted`. The call site for an ordinary DELETE is [`heap_file.c:23586`](https://github.com/CUBRID/cubrid/blob/3ee2faece234768fe158986b4ff7e7960ac6c999/src/storage/heap_file.c#L23586).
- Probe: with `supplemental_log=1`, insert 2,000 rows into an encrypted table without an index, then DELETE them.
  - After the insert: 0 hits.
  - After the delete: 1,297 hits on head and 1,626 on base.
- Fix direction: look up the class's TDE algorithm (as `replication.c:383` does) and mark the node encrypted.

**R3. Fail-open fallback in the new branch.**
- If the conditional READ fix of the B-tree file header fails, `RVBT_MVCC_NOTIFY_VACUUM` is logged in plaintext ([`log_manager.c:2389`](https://github.com/CUBRID/cubrid/blob/3ee2faece234768fe158986b4ff7e7960ac6c999/src/transaction/log_manager.c#L2389)).
- During an index build only the leader latches that header, so the failure needs an interrupt, an I/O error or buffer-claim failure. The latch reviewer judged it practically unreachable. Evidence level 3.
- With lock timeout 0, the failed fix also leaves `ER_LK_PAGE_TIMEOUT` set:
  - The serial caller (`btree_load.c:4792`) ignores it, so the error is stale.
  - `bt_load_append_vacuum_notifications` (`btree_load.c:4884`) fails the CREATE INDEX.
- This is the same policy as the existing `log_sysop_end_logical_undo` lookup (`log_manager.c:4606-4616`).
- Hardening options:
  - Encrypt when the lookup fails and keys are loaded, because an extra encryption is harmless.
  - Save and restore the error state around the probe.
  - Pass the algorithm the loader already computes (`btree_load.c:5581-5597`).

**R4. `LOG_SYSOP_START_POSTPONE` copies the sysop's logical undo (key plus OID) without encryption.** Pre-existing, evidence level 2–3.
- Path: `log_append_sysop_start_postpone`, `log_manager.c:4545-4559`.
- Reaching it needs a B-tree sysop that ends with a logical undo and also holds a postpone, such as an online-index transaction delete that frees an overflow page. Reachability for user MVCC tables is not proven.

**R5. Cost of the new branch.** Model only, not measured.
- Every `RVBT_MVCC_NOTIFY_VACUUM` record, on encrypted and plain tables alike, now does a conditional READ fix and unfix of the index file header. A conditional fix bypasses the lock-free read fast path.
- Notify records are written once per key whose row is not yet all-visible, which is nearly every row right after a bulk insert.
- The latch reviewer's model puts the cost at a few percent or less of CREATE INDEX on such data.
- Caching the algorithm per build would remove it. Measuring needs release builds of base and head running CREATE INDEX on a large, freshly inserted plain table.

### Rejected or cleared hypotheses

- **NULL `pgptr` in the unguarded `pgbuf_get_tde_algorithm` calls (undoredo, redo, postpone) for the new indexes:** every writer passes a fixed page. Level 3.
- **`log_sysop_end_logical_undo` assert, or a NULL vfid, for the new indexes:** none of them is written through that path, because `btree_insert_sysop_end` rejects it for MVCC delete operations. Level 3.
- **Stale or unflagged vfid in the new branch:** `btree_create_file` applies TDE before the load. The one window where the class record is unreadable has an empty table. Level 3.
- **Vacuum, CDC or recovery needing plaintext of the newly encrypted records:** all decrypt at fetch. Level 5 for restart recovery (P1).
- **`prior_set_tde_encrypted` failing and dropping the record:** pre-existing pattern. The engine reviewer found no reachable path where a flagged page or file coexists with unloaded keys. Level 2–3.

## Relation to the 2026-11-11 review of the same snapshot

An earlier review ([review.md](review.md)) pinned the same engine base and head and ended `incomplete`. It ran no database. Its PR comment is [issuecomment-6794004856](https://github.com/CUBRID/cubrid/pull/8454#issuecomment-6794004856). This review keeps that report unchanged and resolves its items as follows.

| Earlier item | Status in this review |
|---|---|
| R1: a lookup failure queues a page-less key unencrypted | Same root cause as R3 here. Two new source traces agree: during an index build only the leader latches the header, so only an interrupt, an I/O error or a buffer-claim failure triggers the fallback. Base logged this record unencrypted on every path. Treated as non-blocking hardening. Still not executed in a real server. |
| R2: restart-undo compensation with a NULL page is unencrypted | Pre-existing (`log_manager.c:3186-3192`, also found by latch-perf-sonnet). Not re-executed. Ordinary restart recovery with the new encrypted records was executed and passed (P1). |
| R3: cipher-error fallback and plaintext HA copies | Pre-existing and out of this PR's scope. HA copies confirmed plaintext by design from source. |
| Audit gap: other recovery indexes | Closed at level 3 by two independent traces of heap, B-tree, overflow, vacuum and page-buffer indexes. Runtime probes found two leaks outside the recovery-index list (R1 CTAS, R2 supplemental), both pre-existing. |

## Coverage

See [review-with-tc-coverage.md](review-with-tc-coverage.md). Every changed path has an owner and a terminal result.

Shared question Q1 asked whether any path still writes a plaintext value. Opus and Sonnet answered it independently and agreed:
- Within the heap, B-tree, overflow, vacuum and page-buffer recovery indexes, the PR's list is complete.
- Residual leaks exist through record types outside the list (supplemental) and through the conditional fallback.
- Opus alone found R4.
- R1 came from a coordinator probe that the Opus reviewer proposed as P3.

Not covered:
- Release-build behavior.
- HA runtime: replica applylogdb and copylogdb were traced in source only.
- Online index build interleavings for R4.
- Measured performance for R5.

## Checks run

Artifact paths are local to the reviewer's host. `evidence/` is relative to the run directory `/home/vimkim/gh/review-runs/pr8454-3ee2fac`. The counts and results needed to judge each check are stated in this report.

| Check | Revision | Result | Artifacts |
|---|---|---|---|
| Build and install, debug_gcc | head `3ee2fae`, base `2b1db6c` | pass | `evidence/build-{head,base}.log` |
| Shell TC, native testkit, contained, stale CTP `9c62858` | head | inconclusive (`wait_until` missing) | `~/tk/p8454/head1` |
| Shell TC, native testkit, contained, CTP `3d5c13c` | head | 10 of 10 OK | `~/tk/p8454/head2` |
| Same | base | NOK on 2, 4, 6, 7, 9 | `~/tk/p8454/base2` |
| P1 crash and restart after encrypted B-tree DELETE and ROLLBACK | head, base | recovery OK. Hits: 0 head, 1,955 base | `evidence/probes2-{head,base}`, `probes2.sh` |
| P3 and R1 CTAS variants | head, base | leak on both (table above) | `evidence/probes{,2}-{head,base}` |
| P4 supplemental-log DELETE | head, base | leak on both (1,297 and 1,626) | `evidence/probes-{head,base}`, `probes.sh` |

The first probe script's `pkill` matched nothing, so its "after crash" lines are not a crash test. `probes2.sh` used the server PID. The server error log shows the kill and the automatic revive with full recovery, at 17:41:57.8 on head.

## Budget

- **Mode:** bounded. No hard cap was enforced. Targets were set in the prompts only.
- **Agents:** three reviewers, no retries.

| Reviewer | Target | Tool calls | Subagent tokens |
|---|---|---|---|
| engine-opus | 60 | 78 | 217k |
| latch-perf-sonnet | 60 | 52 | 172k |
| tc-sonnet | 50 | 47 | 136k |

- engine-opus exceeded its target by 18 tool calls.
- Coordinator usage is not measured. The coordinator ran two builds, three TC attempts and two probe rounds.
