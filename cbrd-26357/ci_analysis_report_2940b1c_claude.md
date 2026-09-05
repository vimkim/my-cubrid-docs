# CI Failure Analysis: PR #6864 at `2940b1c`

- **PR**: https://github.com/CUBRID/cubrid/pull/6864 — `[CBRD-26357] ( develop <- feat/oos ) CircleCI tracking draft PR`
- **Analyzed commit**: `2940b1cfbc3c2d4d0fac3f9244a960350debd380` (feat/oos, merge of origin/develop, 2026-09-04)
- **Collected**: 2026-09-05T06:45Z, `cubrid-ci 0.1.0 (3e9502f72350)`, `--artifact-mode text --include-test-sources`
- **Evidence**: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26357/2940b1c/test_shell` (CircleCI job 152256) and
  `cbrd-26357/2940b1c/gha-ci-33844280456/` (GitHub Actions beta shell suite excerpts, same commit)
- **Author**: Claude (Fable 5.1). Rev 1 (2026-09-04) was written from GitHub Actions names only while CircleCI was
  pending; this rev 2 (2026-09-05) replaces every inferred signature with the CircleCI observation. Not grilled:
  `grill-with-docs` was not invocable from this session; run it on this file before circulating.

## Executive Summary

CircleCI test_shell at `2940b1c` reports **8 failures out of 3,274** (3,236 success, 30 skipped, 0 error, 0 unknown).
The GitHub Actions beta shell suite on the same commit and the same testcase revision reported **9**: the same eight
plus `bug_bts_6938`, which **passed on CircleCI** and is therefore a GHA-only flake candidate. The per-node JUnit
XML reconciles exactly with CircleCI's count this time (8 nodes, one failure each; no ingestion undercount).

The eight failures have four causes, and only one of them is an engine problem:

| Group | Tests | Cause (observed) | PR relation | Fix location |
|---|---|---|---|---|
| A. Error codes renumbered by the develop merge | `bug_bts_9836`, `bug_bts_14120` | Engine prints `-50,-1380,-1382,-1383,-51`; tc/pr-6864 answers say `-50,-1378,-1380,-1381,-51` | direct, answer drift | 3 answer files on tc/pr-6864 |
| B. OOS TDE answers lost in develop→tc/pr-6864 merges | `file_enc_03`, `file_enc_05` | CI output is line-for-line the 2026-08-03 OOS answer (`e7e87aa43`); the merged answers dropped 1 and 4 lines | TC regression | 2 answer files on tc/pr-6864 (restore from `e7e87aa43`) |
| C. Known TC-side residuals | `log_enc_04`, `bigPageSize` | `RVHF_INSERT_NEWHOME is missing!`; `csql1.log`/`csql2.log` differ only in two LOB locator lines (loaddb itself now succeeds) | direct (OOS layout) | TC workload / tiebreaker on tc/pr-6864 |
| D. CDC extractor dereferences reclaimed OOS chains | `cbrd_27064`, `cbrd_27075` | 3 `cub_server` cores, all from `cdc_make_dml_loginfo` → `heap_attrinfo_read_dbvalues` → `oos_read`: 1× `oos_check_head_header` assert, 2× `pgbuf_fix` on a deallocated page | **direct, engine** | feat/oos engine (CBRD-26939 draft) |

Compared with the `07fef9d` analysis (2026-08-05), six failures are gone: the loaddb MVCCID self-lock family
(`cbrd_25481`, `itrack_10006`, `bug_xdbms_sus880`, `bug_bts_5730`; CBRD-27157 `1d207f4dd` is in this commit) and
the numerable FILE_OOS family (`cbrd_23430`, `cbrd_25365`). `bigPageSize` dropped from the crash layer to the
tie-pick layer for the same reason. The two paramdump tests and the two TDE tests are *re*-failures caused by
merges, not by engine changes.

The one finding that needs engineering is group D. It is the known CDC/OOS lifetime gap described in the local
JIRA draft `CBRD-26939-oos-cdc-vacuum-lifetime`, but the dominant crash signature has changed since that draft:
with CBRD-26786 (`0d994560c`, vacuum now returns empty OOS pages via `file_dealloc`) a stale CDC reference mostly
lands on a **deallocated page**, so `pgbuf_fix (OLD_PAGE)` asserts in `page_buffer.c:2487` instead of the older
`oos_check_head_header` chain-head assert. Two of the three cores in this run are the new signature.

## CI Snapshot

| Suite | Source | State | Job | Tests | Failures | Errors | Unknown | Skipped | Note |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| test_shell | CircleCI | failed | [152256](https://circleci.com/gh/CUBRID/cubrid/152256) | 3274 | 8 | 0 | 0 | 30 | parallelism 50; queued 12:29:45Z, stopped 13:09:06Z (39.2 min); failed nodes 14, 17, 23, 24, 35, 36, 37, 42 |
| test_shell | GitHub Actions `gha-ci` (beta) | failed | [33844280456](https://github.com/CUBRID/cubrid/actions/runs/33844280456) | 3274 | 9 | 0 | 0 | 30 | debug build, 50 shards; the 8 above + `bug_bts_6938` (shard 07) |
| test_medium | CircleCI | passed | [152258](https://circleci.com/gh/CUBRID/cubrid/152258) | — | 0 | — | — | — | commit status only; not collected (request scoped to test_shell) |
| test_sql | CircleCI | passed | [152259](https://circleci.com/gh/CUBRID/cubrid/152259) | — | 0 | — | — | — | same |
| Check TC PRs | GitHub Actions `tc-merge-gate` | failed | [100931833722](https://github.com/CUBRID/cubrid/actions/runs/33843985896/job/100931833722) | — | — | — | — | — | gate, not a test: TC PRs #3159 and #3782 are open drafts |

Reconciliation: `result_counts` 3236 + 8 + 30 = 3274 = `test_count`. Each of the eight `failed_node_indexes`
carries exactly one `<failure>` in its `test-shell.xml` (the XML is present twice per node, under `tmp/logs/` and
`tmp/logs/ctp_log/`; 16 raw hits = 8 unique). Cores: CTP reported three (`core.75252` and `core.84625` on node 14,
`core.119793` on node 36), moved to `/home/ERROR_BACKUP/AUTO_11.5.0.2634-2940b1c_*` on the runners; the artifact
list carries one coredump entry (node 36), not downloaded in text mode. Core stacks below are CTP's in-log CORE
ANALYZER output, not a local gdb session.

## Evidence Scope

- Manifest `schema_version: 1`; `resolved_commit`, `short_sha`, `pr_url`, `pr_number` match the request.
- Engine: local worktree `/home/vimkim/gh/cb/oos-storage` is at exactly `2940b1cfb`; all source citations are exact.
- Testcases: both CIs ran `cubrid-testcases-private-ex` `tc/pr-6864`; GHA recorded `ba3344c36d18cf10f21ffd9ec71cda50d8a6cfca`
  (2026-09-04T06:18Z, manual develop merge by Daehyun Kim) and it was still the branch tip when the CircleCI job
  started at 12:29Z. `summary.json` carries no `testcase_revision` and `sources/index.json` is empty (collector
  downloaded 0 sources), so testcase content was read from the local clone `~/cubrid-testcases-private-ex` at
  `ba3344c36`, `e7e87aa43`, `6a29c0442` (develop) via `git show`; the clone's checkout was not changed.
- Artifacts: 91 listed, 88 text artifacts downloaded (122,734,385 bytes). `failures/*/message.txt` and `diff.txt`
  are empty for `bigPageSize`, `cbrd_27064`, `cbrd_27075` (metadata `node: null`); their evidence was read from
  the node XML `<failure>` bodies. CTP's side-by-side diffs truncate each column at ~60 characters; the exact
  paramdump lists were recovered from the nodes' `test_local.log`/`feedback.log`.
- No valid local execution. A 2026-09-05 attempt to run the five fixed testcases via CTP inside a PID/IPC/mount
  namespace produced no usable result and stopped the host's pgbuf-analysis master (port 1523) through a TCP
  `cubrid service stop`; see `2940b1c/local-verify-attempt-2026-09-05/INCIDENT.md`. Every signature in this
  report comes from CI evidence only.
- Prior context: `cbrd-26357/ci_analysis_report_07fef9d_claude.md` (2026-08-05), `feat-oos/ci-142161-tde-shell-failures-analysis_e20543df8_claude.md`
  (2026-08-03), `cbrd-26357/5b5ff58/failed_tcs/bigpagesize-report.md` (2026-07-08), `cbrd-26847/ci_analysis_report_32cb34e_codex.md`,
  and the JIRA draft `my-cubrid-jira/issues/CBRD-26939-oos-cdc-vacuum-lifetime_725a32c_codex.md`.

## Failure Inventory

| # | Node | Test | Result | Observed signature | Category | PR relation | Confidence |
|---|---:|---|---|---|---|---|---|
| 1 | 24 | `_06_issues/_12_2h/bug_bts_9836` (61 s) | failure | cases 2, 3 NOK: `diff log2.txt log2.answer failed`, `diff log3.txt log3.answer failed`; printed list has `-50,-1380,-1382,-1383,-51`, answers have `-50,-1378,-1380,-1381,-51` | A | direct (answer drift) | High (observed) |
| 2 | 23 | `_06_issues/_14_2h/bug_bts_14120` (10 s) | failure | case 1 NOK on the `[S*] call_stack_dump_activation_list=` line (same renumbering); case 2 OK | A | direct (answer drift) | High (observed) |
| 3 | 17 | `_36_damson/cbrd_23608_tde/file_enc_03` (6 s) | failure | `result.log` has 16 lines = `e7e87aa43` answer; `result.answer` (15 lines) lacks one `pgbuf_dealloc_page` line after the first `file_destroy` | B | TC regression | High (observed) |
| 4 | 35 | `_36_damson/cbrd_23608_tde/file_enc_05` (8 s) | failure | `result.log` has 22 lines (11 `pgbuf_dealloc_page` + 11 `… tde_algorithm = NONE`) = `e7e87aa43`; `result.answer` has 9 + 9 | B | TC regression | High (observed) |
| 5 | 37 | `_36_damson/cbrd_23608_tde/log_enc_04` (31 s) | failure | `grep -rc 'rcvindex = RVHF_INSERT_NEWHOME' result.log` = 0 → `RVHF_INSERT_NEWHOME is missing!`; unchanged from `07fef9d` | C | direct (OOS layout) | High (observed) |
| 6 | 42 | `_35_cherry/issue_21654_server_side_loaddb/bigPageSize` (35 s) | failure | `bigPageSize-2 : OK` (loaddb loaded 256 objects); `bigPageSize-1 : NOK`, `diff csql1.log csql2.log` differs only in the `cl`/`bl` locator lines of the `LIMIT 1` row | C | direct (row order under OOS) | High for the layer; tie-pick vs regeneration still per 2026-07-08 evidence |
| 7 | 14 | `_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064` (157 s) | failure | case 1 OK; case 2 (DELETE, 700 expected) `EXTRACT_ERROR: rc=-10`, `TARGET_COUNT: 0/700`; case 3 (UPDATE round 1, 2400 expected) `rc=-10`, `0/2400`; `CORRUPTION=0`; **2 `cub_server` cores** (`oos_check_head_header` `oos_file.cpp:2600`; `pgbuf_fix_debug` `page_buffer.c:2487`) | D | direct (engine) | High (observed stacks) |
| 8 | 36 | `_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075` (248 s) | failure | 4K config: `FINAL_SEQ=-1 … FIND_ERR=27 EXTRACT_ERR=2 TOTAL_ITEMS=1`; 8K OK (`FINAL_SEQ=2000`); 16K `FINAL_SEQ=2000 EXTRACT_ERR=3`; `CONFIGS_OK=1`, `TOTAL_CORRUPTION=0`; **1 `cub_server` core** (`pgbuf_fix_debug` `page_buffer.c:2487`, 22:01:37 KST) | D | direct (engine) | High (observed stack) |
| — | GHA 07 | `_06_issues/_12_2h/bug_bts_6938` | GHA failure / **CircleCI success (24.5 s)** | GHA: `[NOK], TRY->0`, no detail; CircleCI passed on the same build and testcases | GHA-only | unlikely | Medium: flake candidate, single observation |

## Root-Cause Analysis

### A. Error codes renumbered by the develop merge (2 tests)

**Observed.** Node 24 and node 23 logs contain both strings: the answers' `…,-48,-50,-1378,-1380,-1381,-51,-52,…`
and the engine's `…,-48,-50,-1380,-1382,-1383,-51,-52,…`. The answers were set by `876639d8d` (tc/pr-6864,
2026-08-03, "Add OOS error codes to default call_stack_dump answers"). `git diff 07fef9d48 2940b1cfb -- src/base/error_code.h`
shows develop inserted `ER_BT_LOAD_NOTIFY_VACUUM_LIMIT` (-1377) and `ER_AU_CANT_ALTER_LOGIN` (-1378) ahead of the
OOS block, moving `ER_HEAP_OOS_BAD_INLINE_HEADER`/`_CORRUPTED_RECORD`/`_INVALID_ARGUMENT` to -1380/-1382/-1383.
`system_parameter.c` lists those three symbols in `call_stack_dump_error_codes[]` between
`ER_HEAP_BAD_RELOCATION_RECORD` (-50) and `ER_HEAP_BAD_OBJECT_TYPE` (-51), which is exactly where the diff sits.

**Conclusion.** Deterministic answer drift; no engine defect. It was already fixed once (group A of the `c2cbeaf`
report) and will recur at every develop merge that adds an error code, and again when feat/oos lands on develop.

**Next action.** Regenerate `bug_bts_9836/cases/log2.answer`, `log3.answer`, and `bug_bts_14120/cases/bug_bts_14120_1.answer`
on tc/pr-6864 (substitute `-1378,-1380,-1381` → `-1380,-1382,-1383`; verify in isolation). Then make the two tests
insensitive to OOS numbering (strip the three OOS codes before comparing) or pin OOS error numbers before merge.

### B. OOS TDE answers lost in develop→tc/pr-6864 merges (2 tests)

**Observed (CI).** Sequence of `result.log` vs the two answers, classifying each line as SET (`pgbuf_set_tde_algorithm … AES`),
NONE (`… = NONE`), DESTROY (`file_destroy`), DEALLOC (`pgbuf_dealloc_page`):

```text
file_enc_03  CI actual     : SET×7 DESTROY DEALLOC×5 DESTROY DEALLOC×2          (16 lines)
             e7e87aa43     : SET×7 DESTROY DEALLOC×5 DESTROY DEALLOC×2          (16 lines)  == actual
             ba3344c36 (CI): SET×7 DESTROY DEALLOC×4 DESTROY DEALLOC×2          (15 lines)
file_enc_05  CI actual     : DEALLOC×11 NONE×11                                 (22 lines)
             e7e87aa43     : DEALLOC×11 NONE×11                                 (22 lines)  == actual
             ba3344c36 (CI): DEALLOC×9  NONE×9                                  (18 lines)  == develop
```

**Observed (testcase history, `cubrid-testcases-private-ex`).**

| Date | Commit | file_enc_03 `result.answer` | file_enc_05 `result.answer` |
|---|---|---|---|
| 2026-07-22 | `82f32f141` (develop) | 14 lines | 18 lines |
| 2026-08-03 | `e7e87aa43` "[CBRD-26517] Revise TDE testcases for OOS demotion" | **16** (+1 SET, +1 DEALLOC) | **22** (+2 DEALLOC, +2 NONE) |
| 2026-08-20 | `6365d36ee` (develop, CBRD-27151 TC for engine PR #7509) | new `file_destroy` message format | answer **removed**, script rewritten |
| 2026-08-20 | `de2b136e3` merge develop → tc/pr-6864 | took develop's version | took develop's removal (**OOS answer deleted**) |
| 2026-08-20 | `eb715e21d` "Preserve OOS TDE baseline after develop merge" | OOS baseline re-applied in the new format | not touched |
| 2026-08-21 | `dd547125b` (develop, revert of `6365d36ee`) | 14 lines, old format | 18 lines re-added |
| 2026-09-04 | `ba3344c36` merge develop → tc/pr-6864 | **15-line hybrid** (7 SET from the OOS side + develop's DESTROY/DEALLOC counts) | **identical to develop** |

`git log -- <path>` hides `e7e87aa43` for both files (the merges are tree-same to the develop parent);
`git log --full-history` exposes the chain. Both `.sh` scripts are unchanged since `e7e87aa43`. Engine `2940b1c`
does not contain CBRD-27151 (#7509): `file_manager.c:4170` still emits the old `file_destroy()` message, which is
why develop's *old-format* answers are right for develop and only the OOS line counts are missing.

**Conclusion.** The tests fail because the OOS-specific expected counts were dropped during two manual develop
merges. TDE behavior under OOS is unchanged: the CI output equals the 2026-08-03 verified answer exactly, so the
CBRD-26786 vacuum-deallocation change did not add lines to these insert-then-drop workloads.

**Next action.** On tc/pr-6864: `git checkout e7e87aa43 -- shell/_36_damson/cbrd_23608_tde/file_enc_03/cases/result.answer
shell/_36_damson/cbrd_23608_tde/file_enc_05/cases/result.answer`, push, and make sure `file_enc_05/cases/result.answer`
appears in PR #3782's file list (it does not today). Process guard: after each develop→tc/pr-6864 merge, compare
`gh pr view 3782 --json files` against the known OOS-TC file set and re-verify anything that vanished.

### C. Known TC-side residuals (2 tests)

- **`log_enc_04`** — identical to `07fef9d`: the TDE-encrypted log dump contains no `RVHF_INSERT_NEWHOME` record
  because OOS demotion never produces a NEWHOME relocation for this workload. Prior action #5 (rewrite the workload
  on tc/pr-6864 so it genuinely produces the record under OOS, after checking what fires on develop) is still open.
- **`bigPageSize`** — the crash layer is gone (`bigPageSize-2 : OK`, loaddb loaded 256 objects). What remains is the
  layer the 2026-07-08 preserved-log report diagnosed: `SELECT … ORDER BY 1 DESC LIMIT 1` over 256 rows identical in
  every selected column picks a different tied row in db1 (16K, SA) and db2 (4K, CS, freshly loaded), so only the
  `cl`/`bl` LOB locator lines differ. The proposed one-line tiebreaker (`order by 1 desc, id`, CBRD-26828 draft) is
  still not on tc/pr-6864. The 2026-07-08 evidence chain showed locator preservation (tie-pick); the alternative
  "locator regeneration" reading from a later analysis has not been re-tested on this head, and this run's
  truncated diff cannot settle it.

**Next action.** Land the `bigPageSize` tiebreaker and the `log_enc_04` workload fix on tc/pr-6864; verify both in
isolation at `2940b1c`.

### D. CDC extractor dereferences reclaimed OOS chains (2 tests, 3 cores) — engine

**Observed.** All three cores share one stack from frame 11 down (CTP CORE ANALYZER, node 14 and node 36):

```text
#17 cdc_make_dml_loginfo                          src/transaction/log_manager.c:13040
#16 heap_attrinfo_read_dbvalues
#15 heap_attrinfo_read_dbvalues_with_oos_prefetch  src/storage/heap_file.c:10779
#14 heap_attrinfo_read_dbvalues_individually       src/storage/heap_file.c:10714
#13 heap_attrvalue_read                            src/storage/heap_file.c:10681
#12 heap_attrvalue_point_variable                  src/storage/heap_file.c:10547   (OR_IS_OOS (offset) branch)
#11 heap_attrvalue_read_oos_inline
#10 oos_read                                       src/storage/oos_file.cpp:2635 / 2638
  core.84625 (node 14):  #9 oos_check_head_header  oos_file.cpp:2615 → #8 oos_file.cpp:2600  assert (header.chunk_index == 0)
  core.75252 (node 14),
  core.119793 (node 36): #9 oos_read_within_page   oos_file.cpp:2536 → #8 pgbuf_fix_debug page_buffer.c:2487  assert (false) — OLD_PAGE fix of a deallocated page
#18 cdc_log_extract                                src/transaction/log_manager.c:11015
#19 cdc_loginfo_producer_execute                   src/transaction/log_manager.c:11242   (daemon thread)
```

The caller is the CDC log-info producer daemon converting a supplemental-log record image into DB_VALUEs. The
record image holds the 16-byte OOS inline stub, so `heap_attrvalue_read` resolves it against the *current* OOS
file. `log_manager.c` still carries the acknowledgements: `cdc_get_recdes` (line 11942) "//TODO : Additional
handling for OOS columns in CDC will be needed later." and `cdc_get_overflow_recdes` (line 12480) "TODO: add CDC
support for rebuilding multi-chunk OOS records after this marker" (`LOG_DUMMY_OOS_RECORD`).

Both testcases are 4K-page CDC regressions with payloads far above one page (`cbrd_27064`: BIT VARYING 16 000–20 380 B,
700 deletes and 2 400 updates per round; `cbrd_27075`: 5-page payloads, 2 000 updates per page size with
`log_max_archives=2`, `force_remove_log_archives=yes`). Under OOS these payloads are demoted, so every UPDATE/DELETE
image references an OOS chain that vacuum is free to reclaim once the old version is invisible. Inserts pass
(`cbrd_27064-1 : OK`; `cbrd_27075` 8K config fully OK), deletes/updates fail (`rc=-10`, `TARGET_COUNT 0/700`,
`0/2400`), and the server dies when the reference is followed under `assert`.

**Inferred.** This is the lifetime gap already written up in `CBRD-26939-oos-cdc-vacuum-lifetime` (analyzed at
`725a32c`, job 145308): CDC's consumer LSA protects archive logs but not the OOS chains those logs reference. What
is new at `2940b1c` is the signature mix. CBRD-26786 (`0d994560c`, in this commit) makes vacuum return emptied OOS
pages through `file_dealloc`, so a stale reference now usually hits a deallocated page (`pgbuf_fix_debug:2487`,
2 of 3 cores) rather than a reused page whose chunk header no longer starts a chain (`oos_check_head_header:2600`,
1 of 3). In a release build the deallocated-page path would surface as `ER_PB_BAD_PAGEID` from `pgbuf_fix` rather
than an abort; extraction would still fail. `CORRUPTION=0` in both tests confirms the original CBRD-27064/27075
log-page-boundary fixes are intact; this is not a regression of those bugs.

**Falsifier.** A core whose stack does not pass through `cdc_make_dml_loginfo`, or a run with vacuum disabled
(`vacuum_disable=yes` is not a production option, but as an experiment) in which both tests pass.

**Next action.** Decide whether CDC-with-OOS gates the feat/oos merge (the `cbrd-26847` report already recommended
retaining it as a gate). Then implement the CBRD-26939 direction (materialize OOS payloads into the supplemental
log, or pin OOS chains until the CDC/flashback safe LSA passes; the draft lists the trade-offs). Until then, the
engine must at minimum not abort: `oos_read` should treat a non-head chunk or a deallocated page as an error
return (`ER_HEAP_OOS_CORRUPTED_RECORD`-class) so `cdc_make_dml_loginfo` can fail the record instead of killing
`cub_server`. Verify with `cbrd_27064` case 2 (fastest reproducer: single DELETE sweep, 157 s total) in the isolated
container runner.

### GHA-only: `bug_bts_6938`

**Observed.** Failed on GHA shard 07 (`TRY->0`, names only), **passed on CircleCI** node run in 24.5 s with the same
build and testcase commit. The test starts a 100-CAS broker and a Java client, sleeps 1 s, and requires more than
60 `Num` lines from `cubrid statdump`. `perf_monitor.c` defines 200 `Num_…` statistics at `2940b1c`, at `07fef9d`,
and at the develop merge-base, so the statistic set is unchanged. The testcase is unchanged since the 2016 import.

**Inferred.** Environment/timing on the GHA shard (statdump or the Java client not ready 1 s after start under a
~12 GiB-peak container). Engine relation unlikely. One observation only; treat as a flake candidate and watch the
next GHA run.

## Recommended Actions

1. **Testcase fixes on tc/pr-6864 (groups A–C, 7 files, no engine change)**: regenerate the three paramdump
   answers with `-1380,-1382,-1383`; restore the two TDE answers from `e7e87aa43`; add the `bigPageSize` tiebreaker;
   rewrite the `log_enc_04` workload. Verify only in a fully isolated environment (PID + IPC + **network**
   namespace with a CTP-replaceable `~/.CUBRID_SHELL_FM`, or a host/VM with no other CUBRID instance); the
   container recipe mounts the install read-only, and the 2026-09-05 namespace attempt without a network
   namespace stopped the host master (see the incident note). Then re-trigger with `/run shell`.
2. **Engine (group D)**: confirm the merge-gate decision for CDC-with-OOS, then implement CBRD-26939. As a first
   step make `oos_read` fail soft on non-head chunks and deallocated pages instead of asserting, so CDC degrades to
   an extraction error. Use `cbrd_27064` case 2 as the reproducer.
3. **Guard the TC branch**: after every develop→tc/pr-6864 merge, diff PR #3782's file list against the known
   OOS-TC set; anything missing is a regression before CI runs.
4. **Reduce recurring numeric drift**: make `bug_bts_9836`/`bug_bts_14120` insensitive to OOS error-code numbers, or
   reserve fixed numbers before the develop merge.
5. **`Check TC PRs` stays red** until TC PRs #3159 and #3782 are merged or closed; it is a gate, not a defect.
6. **CI evidence**: the collector left `message.txt`/`diff.txt` empty for the three `node: null` failures and
   downloaded no testcase sources; file both against the analyzer. GHA should publish per-shard `test-shell.xml`
   (or at least the `<failure>` bodies) as run artifacts so names are not the only thing visible off-runner.

## Evidence and Limitations

- Inspected: `manifest.json`, `test_shell/summary.json`, `failed-tc.txt`, `failed-tests.json`, `attempts/152256/raw/tests.json`
  (`bug_bts_6938` = success), all eight `failures/*` directories, node XML `<failure>` bodies for nodes 14, 36, 42,
  `test_local.log`/`feedback.log` for nodes 23 and 24, `artifacts.json`, `logs/index.json`, `sources/index.json`;
  GHA `collect` and nine shard job logs; testcase history and file contents in the local private-ex clone; engine
  sources at `2940b1c` (`error_code.h`, `system_parameter.c`, `file_manager.c`, `perf_monitor.c`, `oos_file.cpp`,
  `page_buffer.c`, `heap_file.c`, `log_manager.c`).
- Core stacks come from CTP's CORE ANALYZER text in the node XML; the coredumps themselves were not downloaded
  (`--artifact-mode text`) and no local gdb was run.
- `bigPageSize`'s diff is truncated to ~60 characters per column, so the tie-pick vs locator-regeneration question
  from the `07fef9d` report is still open; only the layer (post-loaddb SELECT) is settled.
- test_medium and test_sql were not collected; their pass state is from GitHub commit statuses.
- No valid local execution (see the incident note). The group A–C testcase edits live in a separate worktree of the
  private-ex repo (`/home/vimkim/gh/tc/cubrid-testcases-private-ex-tc-pr-6864`, branch tc/pr-6864), uncommitted and
  unpushed; no engine source was modified; nothing was committed or pushed.
- No credentials, signed URLs, or environment values are included.
