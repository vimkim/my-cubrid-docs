# cbrd_25481 Failure Diagnosis (Server Crash During Server-Side loaddb of OOS-Demotable Rows)

- TC: `shell/_06_issues/_24_2h/cbrd_25481/cases/cbrd_25481.sh` (TC mainline `5bdb0e1d4`, 2024-08-07 — unchanged since)
- CI evidence: PR #6864 head `0ad6afc0ff871f5aa6c002923868fc6527149ea0`, test_shell job 142161, node 42, run_time 160.5 s, NOK sub-cases 6/13/20/27
- Analysis date: 2026-07-31. Local build: `11.5.0.2460-0ad6afc` 64-bit **debug** (CI was optdebug; same asserts active)

## Verdict

**Engine bug (feat/oos × develop interaction), PR relation: direct. Reproduced locally with identical NOK set and a pinned crash stack.**

`cub_server` for the loaded DB **aborts on `assert (thread_p->type != TT_LOADDB)`** (`src/transaction/lock_manager.c:3539`) whenever server-side loaddb (`loaddb -C`) loads the first OOS-demotable row of a class. The chain: OOS lazy file creation on the loaddb worker thread → `file_create (FILE_OOS)` needs the current MVCCID for the vacuum dropped-file check → the transaction has no MVCCID yet → lazy assignment now **self-locks the fresh MVCCID through the ordinary lock manager** (new behavior from develop's CBRD-26942, merged into feat/oos by head merge `0ad6afc` itself) → lock manager's 2019-era contract "loaddb workers never lock" (CBRD-23375) fires the assert → SIGABRT.

The TC's four NOK sub-cases (6, 13, 20, 27) are the four `test-CS` legs — one per database — and each one dumped its own `cub_server` core with the **identical stack**. The csql "transaction aborted by the system due to server failure or mode change" / "Failed to connect" lines in the CI diff are downstream symptoms of the dead server, not independent failures.

## Reproduction (Observed)

Worktree `/home/vimkim/gh/cb/feat-oos-fix-regression`, HEAD exactly `0ad6afc0ff871f5aa6c002923868fc6527149ea0`, clean tree (untracked personal tooling files only), install `~/.cub/install/feat-oos-fix-regression/debug_gcc` (`cubrid_rel`: `11.5.0.2460-0ad6afc` debug, built Jul 30 2026 18:11).

```bash
# CTP single-TC run (conf copied from ~/CTP/conf/shell_ci.conf with scenario=<TC dir>,
# testcase_update_yn=false, exclude list disabled)
~/CTP/bin/ctp.sh shell -c <temp.conf>   # scenario=~/cubrid-testcases-private-ex/shell/_06_issues/_24_2h/cbrd_25481
```

Result (543 s): **NOK at exactly sub-cases 6, 13, 20, 27 — identical to CI job 142161.** Each NOK was accompanied by a `cub_server` core, auto-preserved by CTP under:

- `~/ERROR_BACKUP/AUTO_11.5.0.2460-0ad6afc_20260731_133658.tar.gz` (db_25481_1_load)
- `~/ERROR_BACKUP/AUTO_11.5.0.2460-0ad6afc_20260731_133926.tar.gz` (…_2_load)
- `~/ERROR_BACKUP/AUTO_11.5.0.2460-0ad6afc_20260731_134139.tar.gz` (…_3_load)
- (fourth backup for db_25481_4_load produced analogously; sub-case 27 NOK)

Local testcase checkout: `~/cubrid-testcases-private-ex` on branch `feature/oos-m2` (NOTE: not the `tc/pr-6864` branch named in the analysis prompt; this TC's directory is identical — last commit `5bdb0e1d4` 2024-08-07, verified via `git log -- shell/_06_issues/_24_2h/cbrd_25481`).

## The Decisive Observation

All local `cub_server` cores (db_25481_1/2/3_load) contain this stack (CUBRID's own crash-time text dump, `CUBRID/log/coredump/cub_server_*.coredump`; frames abridged):

```
__assert_fail
lock_internal_perform_lock_object      lock_manager.c:3541   ← assert at :3539
lock_transaction_mvccid                lock_manager.c:6485
logtb_acquire_mvccid_self_lock         log_tran_table.c:4093
logtb_self_lock_assigned_mvccid        log_tran_table.c:4118
logtb_get_current_mvccid               log_tran_table.c:4154  (lazy-assign branch :4148-4151)
file_create                            file_manager.c:3456    (vacuum dropped-VFID check)
oos_create_file                        oos_file.cpp:983
heap_oos_find_vfid                     heap_file.c:12280      (create_if_missing=true)
heap_oos_insert_serialized_values      heap_oos.cpp:648
heap_attrinfo_insert_to_oos            heap_file.c:12548
heap_attrinfo_transform_to_disk_internal  heap_file.c:13128
heap_attrinfo_transform_to_disk_except_lob heap_file.c:12597
cubload::server_object_loader::finish_line  load_server_loader.cpp:707
cubload::parser::parse / load_task::execute (loaddb worker pool thread, TT_LOADDB)
```

The assert is `assert (thread_p->type != TT_LOADDB);` (`lock_manager.c:3539`, introduced 2019 by `1994f0be3` "[CBRD-23375] no locking for load workers").

Note on core filenames: the kernel pattern `core.%e` uses the **thread** name, so the server core appears as `core.loaddb.<pid>` in the TC directory — `file(1)` confirms `execfn: .../bin/cub_server db_25481_1_load`. A second core, `core.cub_admin.*`, is the `cubrid loaddb -C` **client** killed while polling in `ldr_server_load` (`load_db.c:1404`) after the server died — collateral, not a separate defect.

## Evidence Chain

1. **Observed (CI bundle)**: diff shows the four `test-CS_*.log` legs replacing expected `char_length` rows with "Your transaction has been aborted by the system due to server failure or mode change" (sub-cases 6/20/27) and "Failed to connect to database server, 'db_25481_2_load…'" (sub-case 13). CTP trace (`artifacts/node-42/tmp/logs/ctp_log/test_local.log:110980-114084`) shows, for **all four** DBs: `loaddb -C` prints "Start object loading." then never prints the completion line, and the immediately following `cubrid server stop db_25481_X_load` reports "**server 'db_25481_X_load' is not running**". The CI bundle contains no server `.err`/core artifacts for node 42 (only CTP logs), so the stack could not be pinned from CI alone.
2. **Observed (local)**: same NOK set; every failing leg produced a `cub_server` abort core with the stack above; the loaded-DB server `.err` ends normally at "Server status is UP" + master connect — no engine error precedes the abort (assert goes straight to SIGABRT).
3. **Observed (code)**: `file_create` obtains `tran_mvccid = logtb_get_current_mvccid (thread_p)` for `FILE_BTREE/FILE_HEAP/FILE_HEAP_REUSE_SLOTS/FILE_OOS` to consult `vacuum_is_file_dropped` (`file_manager.c:3448-3470`). `logtb_get_current_mvccid` lazily assigns and then self-locks via `logtb_self_lock_assigned_mvccid` (`log_tran_table.c:4146-4152`); the self-lock goes through `lock_transaction_mvccid → lock_internal_perform_lock_object`, which asserts against TT_LOADDB threads.
4. **Observed (why only the OOS path trips it)**: server-side loaddb inserts run with `has_BU_lock=true → context.is_bulk_op` (`locator_sr.c:5065`), and bulk inserts **skip the MVCC INSID stamp** — `heap_insert_adjust_recdes_header` guards `logtb_get_current_mvccid` with `!insert_context->is_bulk_op` (`heap_file.c:21224-21226`); the CBRD-26942 hunk in `heap_get_insert_location_with_lock` runs only when `lock == X_LOCK`, which loaddb workers don't use (CBRD-23375). So in a non-OOS load **no** TT_LOADDB thread ever requests an MVCCID; lazy OOS file creation is the sole such site.
5. **Observed (timeline)**: the self-lock mechanism arrived in develop commit `741734a8f` "[CBRD-26942] Replace per-row X-lock on appended rows with transaction MVCCID self-lock (#7266)" (2026-07-25). `git merge-base --is-ancestor` confirms it is **not** in `c2cbeaf` (previous snapshot, 7/22 develop merge) and **is** in `0ad6afc` (this head is itself the develop merge that imported it). This matches the TC being ★ new-failing at head.
6. **Inferred**: crash requires (a) server-side loaddb worker (TT_LOADDB), (b) a row whose transform demotes at least one value to OOS, (c) the class's OOS file not yet existing — i.e. the first OOS-demotable row per class in a freshly loaded DB, exactly this TC's shape (single/first row of ~1.1-7 MB JSON, far above the `DB_PAGESIZE/4` demotion gate at head).

## Why It Behaves Differently

- **vs develop**: develop has CBRD-26942 too, but no OOS — no `FILE_OOS` lazy creation, and bulk loaddb inserts skip MVCCID entirely, so no TT_LOADDB thread ever reaches the self-lock. TC passes on develop (its answer files predate OOS and still match SA legs at head).
- **vs c2cbeaf (7/22 snapshot)**: feat/oos had the same OOS lazy-creation-on-TT_LOADDB behavior, but `logtb_get_current_mvccid` did not self-lock, so `file_create` merely read an MVCCID and continued. TC passed. (Cross-snapshot claim; c2cbeaf suite report has no cbrd_25481 section — verified by grep.)
- **Release build**: the assert compiles out; the X self-lock on a fresh MVCCID never waits, so release-mode behavior is likely unaffected (Inferred — not tested). The failure class is debug/optdebug CI builds, which is what QA runs.

## Fix Options

Fix phase owner: engine worktree `/home/vimkim/gh/cb/feat-oos-fix-regression` (grill-and-implement), engine-side. No TC change is warranted — the TC is a faithful regression test and its answers are correct.

1. **(Recommended) Exempt loaddb workers in `logtb_acquire_mvccid_self_lock`** — extend the existing boot/recovery/non-worker guard (`log_tran_table.c:4085-4091`) with a TT_LOADDB check (or equivalently return early before `lock_transaction_mvccid`). Rationale: bulk-loaded rows carry **no INSID stamp** (`is_bulk_op` skip), so no unique/FK waiter can ever key on this transaction's MVCCID through a loaddb-inserted row; the self-lock protects an invariant ("observable INSID ⇒ held X self-lock") that loaddb rows cannot violate. This also preserves CBRD-23375's "load workers never lock" contract. Risk: if some server-side loaddb insert path stamps INSID despite bulk mode, the invariant would be silently waived for it — worth an assert/comment at the guard. **Additional safety facts (Observed, `load_session.cpp:120-211`)**: each loaddb batch runs in its **own batch-scoped transaction owned by exactly one TT_LOADDB thread** (`logtb_assign_tran_index` at :151, `xtran_server_commit` at :187, tran end at :210) — workers do NOT share the session transaction (they only copy its client ids, :159; the BU_LOCK stays with the session transaction). Therefore (a) the lazy MVCCID check-then-assign in `logtb_get_current_mvccid` cannot race between workers (single-threaded per tdes), and (b) a worker transaction bulk-inserts and commits within one batch, so it has no opportunity to produce an INSID in its lifetime — the skipped self-lock has no possible observer. The alternative fix "let TT_LOADDB acquire the self-lock (relax the assert for TRANSACTION keys)" was considered and rejected: it would be the first-ever lock acquisition by a load worker and would need a proof that this is safe against the session transaction's locks, versus zero proof burden for the skip (identical semantics to pre-CBRD-26942 loaddb).
2. **Pre-assign the MVCCID on a non-TT_LOADDB thread** — e.g. in the load session (`load_session.cpp`) before dispatching batches to workers, call `logtb_get_current_mvccid` on the session/request thread so workers always take the already-assigned fast path. Fixes this crash without touching lock policy, but assigns an MVCCID to every server-side load transaction whether or not it needs one, and must run on every transaction boundary loaddb uses (schema/object phases commit separately).
3. **Avoid lazy MVCCID assignment in `file_create`'s dropped-file check** (use a "current if assigned, else NULL" accessor and treat NULL appropriately in `vacuum_is_file_dropped`). Touches shared heap/btree file-creation semantics; highest blast radius — not recommended for this bug alone.

Expected outcome after fix (any of 1/2): all four `test-CS` legs pass; the TC returns to full OK on the next test_shell run. **Cross-TC impact (Inferred, to verify in their own reports): the same mechanism plausibly explains the `loaddb_CS` family failures at head — prio 3 `itrack_10006` and prio 4 `bug_xdbms_sus880` — if their loaded rows exceed the OOS demotion gate; their seeded CBRD-26948 stub-leak hypothesis should be re-checked against this crash first.** Note the seeded hypothesis for THIS TC ("OOS multi-chunk read/unloaddb-hang path") is refuted: unloaddb never hung (all hang sub-cases OK), reads are fine (SA/split legs OK), and the abort is on the loaddb *write* path.

## Preserved Artifacts

- CI bundle: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26357/0ad6afc/test_shell/failures/shell_06_issues_24_2h_cbrd_25481_cases_cbrd_25481_sh-8fc84b9ff9/{metadata.json,message.txt,diff.txt}`; CTP trace `artifacts/node-42/tmp/logs/ctp_log/test_local.log` lines 110980-114084.
- Local cores + server logs (per failing DB): `~/ERROR_BACKUP/AUTO_11.5.0.2460-0ad6afc_20260731_{133658,133926,134139}.tar.gz` — each contains `CUBRID/log/coredump/cub_server_*.coredump` (text stack), raw `core.loaddb.*` (= cub_server) and `core.cub_admin.*` (loaddb client, collateral), and `CUBRID/log/server/db_25481_*_load_latest.err`.
- CTP transcript: `/tmp/shell_single.yPpww0.log`; per-case result `~/cubrid-testcases-private-ex/shell/_06_issues/_24_2h/cbrd_25481/cases/cbrd_25481.result`.
- No engine or testcase files were modified; no temporary diagnostic edits were needed.

## Addendum: PoC Fix Verification (2026-07-31, post-analysis)

The recommended fix (option 1) was prototyped after this report was written, on branch
`CBRD-00001-oos-fix-regression-poc` (base `0ad6afc`, same worktree/build):

- Change: `logtb_acquire_mvccid_self_lock` (`src/transaction/log_tran_table.c`) — added a TT_LOADDB
  early return after the existing boot/recovery/non-worker guard, with the safety rationale in a comment
  (+14 lines, one file; NULL `thread_p` resolved via `thread_get_thread_entry_info`, mirroring file convention).
- Result (Observed): full TC re-run via CTP — **28/28 sub-cases OK, 0 failures, 0 new cores** (261 s vs 543 s
  on the failing run). The four previously-failing `test-CS` legs all pass.
- The per-batch single-threaded worker-transaction facts above were verified during PoC review
  (`load_session.cpp:120-211`) and folded into both this report and the code comment.
- **Cross-TC verification (Observed, 2026-07-31 16:26-16:28 KST)**: the two `loaddb_CS` family failures were confirmed to share this root cause.
  - With the PoC fix: `loaddb_CS/_01_utility/_17_loaddb/itrack_10006` → 2/2 OK (30 s); `loaddb_CS/_05_addition/bug_xdbms_sus880` → 1/1 OK (24 s).
  - Control (fix stashed, pristine `0ad6afc` rebuild): `itrack_10006` → NOK×2 + `cub_server itrack` core with the **identical stack** (`oos_create_file → file_create:3456 → lock_transaction_mvccid → lock_internal_perform_lock_object:3541 assert`), preserved at `~/ERROR_BACKUP/AUTO_11.5.0.2460-0ad6afc_20260731_162749.tar.gz`. Fix restored and rebuilt afterward.
  - Consequence: the prio 3/4 seeded hypothesis (CBRD-26948 unloaddb stub leak) is **not** the mechanism for these two TCs at this head — they are the same TT_LOADDB self-lock crash. This one fix repairs 3 of the 19 head failures (cbrd_25481, itrack_10006, bug_xdbms_sus880).
- Unique/PK-index `loaddb -C` smoke test passed (values intact, unique/PK violations detected, post-load OOS insert OK). Committed as `c0a5e1ee8` on branch `CBRD-00001-oos-fix-regression-poc`; draft PR https://github.com/CUBRID/cubrid/pull/7588 (placeholder ticket).
- **CI confirmation (Observed, 2026-08-01, test_shell job 142569)**: all three TCs (`cbrd_25481`, `itrack_10006`, `bug_xdbms_sus880`) left the failed list — 19 base failures → 18 (16 identical carryovers + 2 appearances unrelated to this fix: `_01_cursor_holdability/_01_cursor_functional` new, `log_enc_04` re-appearing after being resolved at `0ad6afc`, both consistent with intermittent TCs; neither touches the loaddb path). `test_sql` failed with the identical 2-TC set as base in two independent runs (inherited); `test_medium` passed.

## Claim Labels Summary

| Claim | Label |
|---|---|
| Server aborts on `assert(thread_p->type != TT_LOADDB)` via OOS lazy file creation during `loaddb -C` | Observed (local cores ×3, identical stack; CI signature matches) |
| CI failure = same crash | Inferred (identical NOK set/diff signature and "server not running" trace; CI bundle has no core/err artifacts to confirm directly) |
| New at head because of CBRD-26942 (`741734a8f`, not in c2cbeaf) | Observed (git ancestry) + Inferred (no other candidate commit touches this path) |
| Non-OOS loaddb unaffected (`is_bulk_op` INSID skip, no X_LOCK) | Observed (code) |
| Release build unaffected | Inferred, untested |
| Explains itrack_10006 / bug_xdbms_sus880 | Inferred, unverified — check in their reports |
