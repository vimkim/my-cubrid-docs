# CI Failure Analysis: PR #6864 test_shell at `c2cbeaf` (historical commit)

> **WARNING — historical-commit analysis.** This report analyzes the most recent commit of PR #6864 for which a collected `test_shell` snapshot exists: `c2cbeaf9f08c767290cdf14c9af0726447c59a1b` (CircleCI job 139543, run 2026-07-22 14:55–15:26 KST). The PR head at analysis time is `0ad6afc0ff871f5aa6c002923868fc6527149ea0`; its manifest records `test_shell` as `missing` (no shell job status on that commit). There are 46 commits between the two, none of them checked for shell runs. Nothing here is a statement about the current head's shell status.

## Executive Summary

`test_shell` at `c2cbeaf` failed 18 of 3,238 tests (30 skipped, 0 errors/unknowns). The 18 failures resolve into 9 root-cause groups (A–I below):

- **8 tests are directly attributable to intended feat/oos behavior changes** — new OOS error codes in the default `call_stack_dump_activation_list` (A: 2), the new `PERF_PAGE_OOS` perfmon page type growing the server stats block by exactly 4,464 B (B: 1), OOS demotion removing the heap-overflow shape that `diagdb` tests assert (C: 3), OOS demotion removing the `RVHF_INSERT_NEWHOME` WAL record a log-encryption test greps for (E: 1), and OOS row-order change exposing a nondeterministic tie-break (F: 1, via a prior local reproduction).
- **6 TDE `file_enc` tests (D) failed against answer baselines that QA re-baselined the same afternoon** — the job cloned the testcase branch at 14:55 KST; the QA mainline updated these exact answers (e.g. `pages = 5` → `pages = 9`) at 17:55 KST for engine PR #7353 (bestspace redesign), which merged into feat/oos at 18:09 KST — after `c2cbeaf`. OOS demotion of `char(2000)` rows on the tests' 4K-page databases is the concrete mechanism that breaks the old baselines, but why these tests did not fail at the previous snapshot is unresolved.
- **2 tests (I) are hash-join build-method drift** (`memory` vs `hybrid` temp) from develop-side planner/statistics changes merged between snapshots — unlikely OOS.
- **1 test (H, `cbrd_23430`) is an environment failure, not OOS**: `createdb jsondb` failed because a leftover `jsondb_vinf` volume file already existed in the case directory, so the server never started and the JSON workload never ran.
- **1 test (G, `cbrd_25365`) remains unknown**: CTP timeout (1,255.8 s > 1,200 s cap) plus archive-log timing failures.

Versus the previous snapshot `5b5ff58` (2026-07-08, 9 failures): 7 failures persist, 2 resolved (`cbrd_22803`, `bug_bts_6867` — fixed or flaky, undetermined), 11 are new.

No evidence in this bundle indicates OOS data corruption or a crash attributable to OOS code. The dominant pattern is test-expectation drift against intended feat/oos behavior, plus one same-day testcase/engine synchronization race.

**Decision boundary:** answer/testcase updates are justified today only for groups A (paramdump pair), C (diagdb trio), and F (deterministic tie-break). Groups B and D were already re-baselined on the QA testcase mainline (TC PR #3529 and CBRD-27005) — the right move is to re-run `test_shell` at the current head, which now contains engine PR #7353 and will clone the re-initialized testcase branch (re-init 2026-07-30), and see what survives. Do not hand-edit B/D answers before that run.

## CI Snapshot

| Suite | State | CircleCI job | Tests | Failures | Errors | Unknown | Warning |
|---|---|---:|---:|---:|---:|---:|---|
| test_shell | completed (failure) | [139543](https://circleci.com/gh/CUBRID/cubrid/139543) | 3,238 | 18 | 0 | 0 | Historical commit `c2cbeaf`, not current head |
| test_medium | completed (success) | [139541](https://circleci.com/gh/CUBRID/cubrid/139541) | 975 | 0 | 0 | 0 | In bundle; analysis out of scope |
| test_sql | completed (failure) | [139540](https://circleci.com/gh/CUBRID/cubrid/139540) | 17,442 | 5 | 0 | 0 | In bundle; analysis out of scope. Its node logs show the same `-1378`/`-1381` error-code drift signal as group A |

Current head `0ad6afc` (manifest collected 2026-07-30): build/build_debug success, test_medium success, test_sql **failure**, test_shell **missing**.

Skipped tests (30) are excluded from failure analysis by policy.

## Evidence Scope

- Exact commit: `c2cbeaf9f08c767290cdf14c9af0726447c59a1b` (`feat/oos`, build `11.5.0.2414-c2cbeaf`, debug build confirmed in console traces).
- Evidence bundle: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26357/c2cbeaf/` — originally collected 2026-07-22 (cubrid-ci 0.1.0), re-collected 2026-07-30 (cubrid-ci 0.1.0 `6f1272cb94f7`, `--artifact-mode text --include-test-sources`).
- Available evidence: commit `manifest.json`, per-suite `summary.json`, `failed-tests.json`/`failed-tc.txt`, all 18 `failures/*/{metadata.json,message.txt,diff.txt}`, step logs for all 15 failed shell nodes.
- **Limitation — job artifacts not downloaded, later expired.** The original 2026-07-22 shell collection listed 169 artifacts (`summary.json` at that time; overwritten by the re-collection) but downloaded none; the same-day `test_sql` collection likewise lists 97 artifacts with `downloaded: false`. By the 2026-07-30 re-collection the shell artifact list was empty (expired). Server error logs and preserved testcase outputs for job 139543 are therefore unrecoverable from CI. The gap is a collection-mode gap, not late collection.
- **Testcase sources.** The job cloned branch `tc/pr-6864` of `cubrid-testcases-private-ex` (observed in all 15 node logs); the shell `summary.json` carries no `testcase_revision` field, so the exact job-time revision is unproven. Script/answer statements in this report come from the local checkout `/home/vimkim/cubrid-testcases-private-ex` and are tied to dated mainline commits (e.g. `c4a124cc0` 2026-06-12, `82f32f141` 2026-07-22 17:55 KST) so their relation to the job's 14:55 KST clone is explicit. The local `tc/pr-6864` was re-initialized on 2026-07-30 (`dee1952a2`) and is *not* byte-identical to what the job saw. (`test_sql/summary.json` does carry `testcase_revision`, but that pins the public SQL repo, not the shell repo.)
- Source evidence pinned to exact commits via `git show`/`git merge-base --is-ancestor` in the local feat/oos worktree.
- OOS behavioral claims checked against the normative spec `cubrid-oos-context/OOS-CONTEXT.md` (2026-07-13), with one code/spec skew noted in *Evidence and Limitations*.
- Baseline: `my-cubrid-docs/cbrd-26357/5b5ff58/` (job 135486 report + `bigpagesize-report.md` local reproduction) used as an explicitly labeled historical comparison.

## Delta vs Previous Snapshot (`5b5ff58`, job 135486, 2026-07-08)

| Status | Tests |
|---|---|
| Persisting (7) | `tbl_enc_08`, `tbl_enc_14`, `cbrd_26527`, `cbrd_20145_1`, `bug_bts_9836`, `bug_bts_14120`, `bigPageSize` |
| Resolved (2) | `cbrd_22803` (page-buffer counter drift), `bug_bts_6867` (server fatal `max_bestspace_entries`) — no longer failing at `c2cbeaf`; fixed vs flaky undetermined. The `bug_bts_6867` fatal disappearing without a tracked fix deserves a note in the bestspace workstream |
| New (11) | `file_enc_01/02/03/04/05/07`, `log_enc_04`, `cbrd_25365`, `cbrd_23430`, `cbrd_23828`, `cbrd_25846` |

"Resolved/new" is relative to the baseline report's failure list; that report does not distinguish pass from skip, so "new" means "did not *fail* then."

## Failure Inventory

| # | Test | Result | Observed signature | Category | PR relation | Confidence |
|---|---|---|---|---|---|---|
| 1 | `_06_issues/_12_2h/bug_bts_9836` | failure | `paramdump` prints `-1378,-1380,-1381` inside `call_stack_dump_activation_list`; answer lacks them | A | direct | high |
| 2 | `_06_issues/_14_2h/bug_bts_14120` | failure | Same added codes in `paramdump -b` output | A | direct | high |
| 3 | `_06_issues/_17_1h/cbrd_20145_1` | failure | `;.hist` `MNT_SERVER_COPY_STATS` recv size 86,400 → 90,864 (+4,464 B); only 2 differing lines in a 657-line diff | B | direct | high |
| 4 | `_36_damson/cbrd_23608_tde/tbl_enc_08` | failure | `diagdb` result missing answer-side `MULTIPAGE_OBJECT_HE…`/`Overflow for HFID` block | C | direct | high |
| 5 | `_36_damson/cbrd_23608_tde/tbl_enc_14` | failure | Same missing overflow block next to `BTREE_OVERFLOW_KEY` output | C | direct | high |
| 6 | `_06_issues/_26_1h/cbrd_26527` | failure | Case 4: `Failed to extract MULTIPAGE HFID for dba.tbl from diagdb_before.log` | C | direct | high |
| 7 | `_36_damson/cbrd_23608_tde/file_enc_01` | failure | Result empty after `pages = 5` grep anchor mismatch; answer-only diff lines | D | plausible (mechanism direct, baseline confounded) | medium |
| 8 | `_36_damson/cbrd_23608_tde/file_enc_02` | failure | 2 extra result-side `file_alloc`/AES trace lines | D | plausible | medium |
| 9 | `_36_damson/cbrd_23608_tde/file_enc_03` | failure | Extra result-side trace lines only (1 `pgbuf_set_tde_algorithm`, 1 `pgbuf_dealloc_page`) | D | plausible | medium |
| 10 | `_36_damson/cbrd_23608_tde/file_enc_04` | failure | TDE trace block drift in both directions | D | plausible | medium |
| 11 | `_36_damson/cbrd_23608_tde/file_enc_05` | failure | TDE trace block drift | D | plausible | medium |
| 12 | `_36_damson/cbrd_23608_tde/file_enc_07` | failure | 4 extra result-side AES `pgbuf_set_tde_algorithm` lines | D | plausible | medium |
| 13 | `_36_damson/cbrd_23608_tde/log_enc_04` | failure | Script's own check: `RVHF_INSERT_NEWHOME is missing!` from dumped WAL (other 4 expected record types found) | E | direct | medium-high |
| 14 | `_35_cherry/issue_21654_server_side_loaddb/bigPageSize` | failure | This bundle: only `Test failed` (`diff_extraction: unavailable`). Prior local repro: single CLOB/BLOB locator pair differs on a 256-way `ORDER BY` tie | F | direct (testcase fragility; this run unverified) | high for mechanism, low for this run |
| 15 | `_39_fig_cake/cbrd_25365` | failure | `NOK timeout` (1,255.8 s > 1,200 s CTP cap) + archive-log creation-time NOKs (cases 6–12, 20, 22, 24; case 6: active log never archived) | G | unknown | low |
| 16 | `_35_cherry/issue_21522_json/cbrd_23430` | failure | `createdb jsondb` failed: `Volume "…/cases/jsondb_vinf" already exists.` → server never started → csql/loaddb connect errors | H | unlikely (environment/testcase state) | high |
| 17 | `_06_issues/_21_1h/cbrd_23828` | failure | Query trace `SCAN (hash temp(m)…)` vs answer `hash temp(h)` — only differing line | I | unlikely | medium |
| 18 | `_40_guava/cbrd_25846` | failure | 3 cases NOK (select_6, select_7_2, select_9); trace `method: memory` vs answer `hybrid`/`temp(h)` | I | unlikely | medium |

Each failure appears in exactly one category: A(2) B(1) C(3) D(6) E(1) F(1) G(1) H(1) I(2) = 18.

## Root-Cause Analysis

### A. OOS error codes added to the default `call_stack_dump_activation_list` (2 tests)

**Observed:** both `paramdump` outputs contain `…,-48,-50,-1378,-1380,-1381,-51,…` where the answers have `…,-48,-50,-51,…` (full lists in `message.txt`; `diff.txt` truncates them). At `c2cbeaf`, `src/base/error_code.h` defines `ER_HEAP_OOS_BAD_INLINE_HEADER = -1378`, `ER_HEAP_OOS_CORRUPTED_RECORD = -1380`, `ER_HEAP_OOS_INVALID_ARGUMENT = -1381` (lines 1774/1778/1780), and `src/base/system_parameter.c` adds all three to the call-stack-dump default code list (lines 5687–5689).

**Inference:** intended feat/oos change; the tests assert byte-exact `paramdump` output and must fail on any branch extending the default list. develop's `error_code.h` ends at `ER_LAST_ERROR = -1377` with no OOS codes, so the falsifier (develop printing the same codes) fails — attribution holds. The same drift signal appears in the `test_sql` node logs at this commit, so SQL-side answer churn should be expected too.

**Next action:** update the `bug_bts_9836`/`bug_bts_14120` answers on `tc/pr-6864` or normalize the volatile list in the tests' filters; fold into the mainline answers when feat/oos merges. No engine action.

### B. `PERF_PAGE_OOS` grew the server stats copy by exactly 4,464 B (1 test)

**Observed:** `cbrd_20145_1` diffs only in `;.hist` sizes: `MNT_SERVER_COPY_STATS` recv 86,400 → 90,864. `perf_monitor.h` at `c2cbeaf` adds `PERF_PAGE_OOS` (`PERF_PAGE_CNT` 18 → 19); the seven page-type-indexed perfmon arrays (fix, promote success/fail, unfix, lock-time, hold-time, fix-time) contribute 135+36+36+36+135+45+135 = 558 counters × 8 B = **4,464 B**, matching the observed delta exactly (verified during report review).

**Also observed:** QA already re-baselined `cbrd_20145_1/2` answers on the testcase mainline — `82f32f141` (2026-07-22 17:55 KST, after this job's 14:55 clone) rewrote `test1.answer(_debug)`, and `5e3c3aefb` (CBRD-27005, 2026-07-27) masks volatile server-statistics fields.

**Next action:** none locally; verify the next shell run (which clones the re-initialized TC branch) passes. If it still fails, compare against the masked answers before editing anything.

### C. OOS demotion removes the heap-overflow shape that `diagdb` tests assert (3 tests)

**Observed:** `tbl_enc_08`/`tbl_enc_14` results are missing the answer-side `type = MULTIPAGE_OBJECT_HE…` + `Overflow for HFID` block for a TDE table with `varchar(20000)` values (workload confirmed in `message.txt`); `cbrd_26527` case 4 cannot extract a `MULTIPAGE HFID` for `dba.tbl` from `diagdb -d 2` output. Same signature as the `5b5ff58` snapshot. PR #7415 (`FILE_OOS` utility-assert handling, `8b209ee3c`) is in this history and, consistent with the `5b5ff58` baseline analysis, removes the assert hazards without restoring the expected overflow output.

**Inference:** with OOS, large variable values demote to the OOS file instead of producing `MULTIPAGE_OBJECT_HEAP` overflow files, so the expected overflow lines never appear. Intended behavior; the tests' storage-layout premise is stale.

**Falsifier:** a `c2cbeaf` local run of `tbl_enc_08` producing the overflow block would refute demotion as the cause.

**Next action:** make the three testcases OOS-aware on `tc/pr-6864`: accept the absence of `MULTIPAGE_OBJECT_HEAP` for demoted values, and change `cbrd_26527`'s reclaim check to not require an overflow HFID. (These were *not* touched by the 7/22 TC re-baseline.)

### D. TDE `file_enc` cluster: stale baselines re-baselined the same afternoon (6 tests, new since `5b5ff58`)

**Observed timeline (all 2026-07-22 KST):**

| Time | Event |
|---|---|
| 14:55–14:58 | Job 139543 starts; nodes clone `tc/pr-6864` (branch initialized ~2026-07-06) |
| 15:24–15:26 | `file_enc_*` tests fail against the then-current answers |
| 17:55 | TC mainline commit `82f32f141` "[CBRD-26176] Fix testcases for bestspace#7353" (#3529, 61 files) rewrites `file_enc_01.sh` (`pages = 5` → `pages = 9` grep anchor) and the `file_enc_01/03/04/05/07` answers, plus `cbrd_20145_1/2` answers and ~50 other files |
| 18:09 | Engine commit `e84a7f6dc` "[CBRD-26176] Redesign bestspace (#7353)" — **not** an ancestor of `c2cbeaf`, **is** an ancestor of current head `0ad6afc` |

So the job tested the pre-#7353 engine against pre-re-baseline answers, and both sides of that comparison changed within four hours of the run.

**Mechanism (direct, but attribution confounded):** the tests create 4K-page databases (`--db-page-size=4K`, added to TC on 2026-06-12 by `c4a124cc0` for CBRD-26663) and insert `char(2000)` rows. At `c2cbeaf` the OOS gate is raw `DB_PAGESIZE / 4` (`heap_file.c`), ≈1,014 B on a 4K-page DB; CHAR is variable-length since `83b29b02c` (CBRD-26663, in **both** snapshots); each 2,000 B value is OOS-eligible and demotes. The tests grep TDE traces anchored on exact data-page counts (`pages = 5`), which demotion invalidates — `file_enc_01`'s result.log is empty precisely because its grep anchor never matches.

**Unresolved:** every engine and TC precondition above also held at `5b5ff58` (2026-07-08), where these six tests did not fail (pass vs skip indistinguishable from the baseline evidence). Some engine change in `5b5ff58..c2cbeaf` (4 develop merges + 2 OOS commits) or run-to-run variance flipped them; the specific trigger is not identified from this bundle.

**Next action:** the next shell run at the current head is the decisive experiment — it has engine #7353 *and* clones the re-initialized TC branch (2026-07-30) containing the `pages = 9` baselines. If `file_enc_*` still fails there, run `file_enc_01` locally at the head commit and diff the TDE trace against both baselines. Do not hand-edit these answers now.

### E. Expected WAL record type absent from encrypted-log dump (1 test)

**Observed:** `log_enc_04` fails its only case with the script's own message `RVHF_INSERT_NEWHOME is missing!` while scanning a dumped log for five expected record types (the other four are found). The workload is visible in the console trace: `alter table t add column b varchar(10000)` then `update t set b=rpad('b',10000,' ')`, and the script (local `tc/pr-6864` checkout) carries the literal comment `# RVHF_INSERT_NEWHOME` on that statement — the update is designed to grow the record so it relocates.

**Inference (direct):** with OOS, the 10,000 B varchar demotes at update time, the heap record stays small, no relocation occurs, and `RVHF_INSERT_NEWHOME` is never logged. The same "did not fail at `5b5ff58`" caveat as group D applies (pass vs skip unknown there).

**Next action:** adjust the testcase to force relocation with a sub-gate-size growth (records that stay inline), or accept the OOS-era record mix; confirm on the next run at head.

### F. `bigPageSize`: nondeterministic tie-break exposed by OOS row order (1 test)

**Observed (this bundle):** only `Test failed`; `metadata.json` says `diff_extraction: unavailable`, and node-27's log carries no diff detail. **Observed (prior local reproduction, 2026-07-08, `bigpagesize-report.md`):** the entire diff was one CLOB/BLOB locator pair; the test picks 1 row out of 256 tied on the `ORDER BY` key, and the OOS branch changes the loaded DB's physical row order, so the two DBs pick different tied rows. Not an engine bug; loaddb preserved all 256 locators exactly.

**Inference:** the same failure mode at `c2cbeaf` is likely but not verified for this run.

**Next action:** apply the deterministic tie-break (`order by 1 desc, id desc` — the table has `id int AUTO_INCREMENT`, so this is valid) on `tc/pr-6864`, then confirm on the next run.

### G. `cbrd_25365`: CTP timeout plus archive-log timing failures (1 test)

**Observed:** the suite's slowest test (1,255.8 s vs the 1,200 s `testcase_timeout_in_secs` cap → `NOK timeout`), plus NOKs in cases 6–12/20/22/24: case 6 reports the workload never archived the active log (`db25365_lgar000` not found), and later creation-time comparisons print empty timestamps, consistent with cascading from the missing archive/timeout.

**Inference:** unknown root cause. Plausible contributors: debug-build slowdown, OOS write-path overhead changing log volume for the fixed workload, node variance. Nothing distinguishes these; the test was not touched by the 7/22 TC re-baseline.

**Next action:** local timed run at the head commit (and develop merge-base) to see whether the runtime and the missing-archive condition reproduce.

### H. `cbrd_23430`: createdb failed on a leftover volume file — environment, not OOS (1 test)

**Observed (`message.txt`):** `cubrid createdb jsondb` fails with `Couldn't create database. Volume "…/issue_21522_json/cbrd_23430/cases/jsondb_vinf" already exists.`; both subsequent `server start jsondb` attempts fail with `Database "jsondb" is unknown`; csql/loaddb then report connect failures — which is what the answer diff shows. The script's server-error-log check found 0 `Internal Error`. The 50 KB JSON workload never executed, so no OOS path was exercised.

**Inference:** stale-workspace/testcase-hygiene failure. The provenance of the leftover `jsondb_vinf` is unknown (node-17 ran the test once, `TRY->1`); it either leaked from an earlier run on the node image or is present in the TC state the job received.

**Next action:** make the testcase remove leftover `jsondb*` volume/state files before `createdb` (and investigate where the leftover came from before assuming the test is otherwise healthy). Deprioritized from P0: no engine implication is in evidence.

### I. Hash-join build-method drift from develop (2 tests)

**Observed:** `cbrd_23828`'s only differing line is `SCAN (hash temp(m)…)` vs answer `hash temp(h)`; `cbrd_25846` fails 3 cases (select_6, select_7_2, select_9) with `method: memory` vs `hybrid` in both text and JSON traces. Both are new since `5b5ff58`. The range `5b5ff58..c2cbeaf` contains 4 develop merges bringing hash-join/statistics work: CBRD-26475 (#6782), CBRD-26900 (#7269), CBRD-27039 (#7442), CBRD-26936 (#7286).

**Inference:** the hash-join temp/build method decision changed (memory vs hybrid) — develop-side planner/statistics behavior; OOS relation unlikely. Whether develop's own CI fails these is unknown from this bundle.

**Falsifier:** the develop merge-base failing the same way confirms develop-side; passing would reopen an OOS interaction (e.g. statistics affected by OOS storage).

**Next action:** check these two tests on develop CI (or run locally at the merge-base) before deciding between develop-side answer updates and an OOS investigation.

## Recommended Actions

1. **P0 — run the decisive experiment:** trigger `test_shell` on the current head (`/run all` chatops) and re-collect. The head contains engine #7353 and the run will clone the re-initialized TC branch (2026-07-30, includes the 7/22 re-baselines and the CBRD-27005 masking), which should by itself resolve groups B and D if the same-day sync race is the whole story. test_sql at head is already failing and needs its own analysis (expect group A's error-code drift to appear there).
2. **P1 — testcase updates on `tc/pr-6864`** for the proven intended-drift groups: A (`bug_bts_9836`, `bug_bts_14120` — new OOS error codes), C (`tbl_enc_08`, `tbl_enc_14`, `cbrd_26527` — OOS-aware diagdb expectations), F (`bigPageSize` — deterministic tie-break), E (`log_enc_04` — restore or drop the NEWHOME premise). None of these were covered by the 7/22 QA re-baseline.
3. **P1 — if group D still fails at head,** run `file_enc_01` locally at the head commit and diff TDE traces against the `pages = 9` baseline; only then consider answer edits.
4. **P2 — `cbrd_23430`:** add pre-`createdb` cleanup of leftover `jsondb*` files to the testcase and find the leftover's origin.
5. **P2 — hash-join pair (`cbrd_23828`, `cbrd_25846`):** classify against develop CI; if develop fails them too, they belong to develop, not this PR.
6. **P2 — `cbrd_25365`:** time it locally; decide between a testcase time budget fix and a performance investigation.
7. **Process — collect with artifact download enabled** (`--artifact-mode text` at minimum) immediately after failed runs. This job's collection ran the same day but skipped artifact download, and the artifacts (server logs, cores) expired before anyone fetched them — which is why groups G's and (until the console trace was read) H's evidence was thin.

## Evidence and Limitations

- Files inspected: commit manifests (`c2cbeaf`, `0ad6afc`), all three suite `summary.json` files, shell `failed-tc.txt`/`failed-tests.json`, all 18 `failures/*` records, `logs/index.json` + all 15 failed-node step logs, `sources/index.json` (empty), `artifacts.json` (empty at re-collection), `test_sql/artifacts.json` (97 listed, none downloaded).
- Source evidence at exact commits: `error_code.h` (−1378/−1380/−1381), `system_parameter.c` (default call-stack-dump list), `perf_monitor.h/.c` (`PERF_PAGE_OOS`), `heap_file.c` (OOS gate `DB_PAGESIZE / 4` present at both `5b5ff58` and `c2cbeaf`); ancestry checks for `83b29b02c` (CBRD-26663, in both snapshots), `e84a7f6dc` (#7353, in head only), `8b209ee3c` (#7415, in `c2cbeaf`); commit-range survey `git log 5b5ff58..c2cbeaf` (4 develop merges, OOS commits #7415/#7416).
- Testcase evidence from the local `cubrid-testcases-private-ex` checkout, tied to dated mainline commits (`c4a124cc0`, `82f32f141`, `5e3c3aefb`, `dee1952a2`); the job-time `tc/pr-6864` revision is unproven (no `testcase_revision` for shell).
- **Spec/code skew noted for the OOS context file:** `OOS-CONTEXT.md` (2026-07-13) describes the demotion gate as `heap_oos_inline_target_size()` (4,060 B, CBRD-27057) and instructs not to call it raw `DB_PAGESIZE/4` — but at `c2cbeaf` the code *is* raw `DB_PAGESIZE / 4` and that function does not exist yet; the spec's fixed 16K-layout figure also hides the page-size scaling that matters for group D's 4K-page databases. Separately, the spec states `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE = -1375`, but at `c2cbeaf` it is `-1379` (`-1375` is `ER_QSTR_INVALID_UUID_FORMAT`). The spec should be updated for both.
- Not supported by this bundle: any claim about `test_shell` at the current head or the 46 intermediate commits; a root cause for `cbrd_25365`; the exact engine delta that flipped group D between snapshots; a confirmed diff for this run's `bigPageSize`; develop-baseline status for the hash-join pair; whether the two failures resolved since `5b5ff58` were fixed or are flaky.
- test_sql failures at `c2cbeaf` and `0ad6afc` are out of scope (suite not requested), with the single cross-suite observation that the group-A error-code drift is visible in the sql node logs.
