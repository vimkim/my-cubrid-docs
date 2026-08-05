# CI Failure Analysis: PR #6864 at `07fef9d`

- **PR**: https://github.com/CUBRID/cubrid/pull/6864 — `[CBRD-26357] ( develop <- feat/oos ) CircleCI tracking draft PR`
- **Analyzed commit**: `07fef9d48b4776e60c42e8afa25b9f21c54b8226` (feat/oos, merge of origin/develop)
- **Collected**: 2026-08-05T01:20Z, `cubrid-ci 0.1.0 (3e9502f72350)`
- **Evidence**: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26357/07fef9d`
- **Author**: Claude (Fable 5), 2026-08-05 (rev 2 after adversarial review)

## Executive Summary

test_medium and test_sql are fully green. CircleCI reports **9** test_shell failures, but the
per-node evidence in the same bundle shows **10** failing testcases: `bug_bts_5730` (a
`loaddb_CS` test with an in-window `cub_server` coredump on node 33) is present in node 33's
JUnit XML and step log yet absent from CircleCI's aggregated test list — the widely quoted "9"
is an ingestion artifact and undercounts by one.

The headline finding concerns **bigPageSize.sh**: its current failure is **NOT the previously
concluded ORDER BY tie** — `loaddb -C` exits 254 with zero objects loaded because `cub_server`
crashes (coredump inside the test's run window), matching the CBRD-27157 loaddb-worker MVCCID
self-lock assert that draft PR #7588 fixes. The ORDER BY comparison never executes in the
current runs. The ORDER BY-tie conclusion (CBRD-26828 draft + 2026-07-08 preserved-log report)
was correct *for the July failure mode* and becomes relevant again **after** #7588 lands: a
2026-08-03 local verification with the fix showed loaddb succeeding and a residual 2-line
CLOB/BLOB locator diff. However, the two prior analyses of that residual diff **contradict each
other** (tie-pick with locators preserved vs. locator regeneration by the feat/oos loaddb
path), and the discriminating check has not been run on the current head. The proposed one-line
TC tiebreaker (`order by 1 desc, id`) was **never landed** on any TC branch (`tc/pr-6864`, TC
`feat/oos`, TC `develop` all verified without it).

Failure budget (10): 5 in the server-side-loaddb crash family (bigPageSize's current layer,
cbrd_25481, itrack_10006, bug_xdbms_sus880, bug_bts_5730 — the first four mapped to CBRD-27157,
the fifth likely but unconfirmed), 2 in the known numerable-FILE_OOS page-bookkeeping defect
family (cbrd_23430, cbrd_25365 — mapping inferred from prior exact stacks, with caveats), 2 CDC
tests excluded from analysis by direction (cbrd_27064, cbrd_27075), and 1 TDE testcase whose
workload assumption breaks under OOS (log_enc_04, `RVHF_INSERT_NEWHOME` never produced).

## CI Snapshot

| Suite | State | CircleCI job | Tests | Failures | Errors | Unknown | Skipped | Warning |
|---|---|---:|---:|---:|---:|---:|---:|---|
| test_medium | completed | [143293](https://circleci.com/gh/CUBRID/cubrid/143293) | 975 | 0 | 0 | 0 | 0 | — |
| test_sql | completed | [143292](https://circleci.com/gh/CUBRID/cubrid/143292) | 17444 | 0 | 0 | 0 | 0 | — |
| test_shell | completed | [143291](https://circleci.com/gh/CUBRID/cubrid/143291) | 3250 | 9 | 0 | 0 | 30 | CircleCI count is short by 1 (see below) |

Reconciliation: CircleCI's test list gives 3211 success + 9 failure + 30 skipped = 3250, but
`summary.json.failed_node_indexes` lists **ten** nodes `[14,27,32,33,38,40,41,44,45,47]`, and
summing `<failure>` records across the ten per-node `test-shell.xml` files gives **10**. The
missing test is `loaddb_CS/_06_issues/_11_2h/bug_bts_5730` (node 33): its failure record exists
in node 33's XML but has no corresponding entry in `attempts/143291/raw/tests.json`.

Baseline context: the previous analyzed cycle, job 142161 at `0ad6afc` (2026-07-31), had 19
shell failures per its analysis doc. TC-side fixes pushed to `tc/pr-6864` (mirrored in
cubrid-testcases-private-ex PR #3806, OPEN) removed the TDE answer-staleness group and others,
leaving the current set.

## Evidence Scope

- All three suites collected at the same pinned commit `07fef9d48…`; manifest
  `schema_version: 1` and PR identity validated.
- Artifact mode `text` — 111 text artifacts (146,117,309 B) downloaded; the 12 listed coredumps
  were intentionally not downloaded, and no gdb/backtrace artifacts exist in the run. All
  crash-site attributions for *this run* are therefore inferred from run-window timing plus
  prior exact-stack local reproductions, and labeled as such.
- **Retry/core asymmetry**: CTP retries each failed test once, and every collected core lies in
  a *retry* window (first attempts of bigPageSize and bug_xdbms_sus880 failed identically but
  left no surviving core). Core counts therefore must not be compared against failure counts.
- `testcase_revision` is **absent** from all three suite summaries (the older `c2cbeaf` bundle
  did carry it for test_sql — possibly a collector regression worth filing). The effective TC
  branch is `tc/pr-6864` per `.circleci/config.yml` (`TC_BRANCH="tc/pr-${PR}"` for `pull/*`,
  resolved against `cubrid-testcases-private-ex` for shell, falling back to `develop` only if
  five `ls-remote` retries fail). CTP's `main_snapshot.properties` and the JUnit `classname`
  URLs print `develop`, but those are cosmetic defaults; the run's *content* proves the
  `tc/pr-6864` fixes were in effect (the 12 TDE/other TCs fixed on that branch all pass here),
  and the branch tip `e21c7ce9c` (2026-08-04T09:32Z) predates the job start (14:58Z).
- The local engine worktree (`/home/vimkim/gh/cb/oos-storage`) is at exactly `07fef9d48…`;
  source citations are exact.
- Prior context used: CBRD-26828 JIRA draft (ORDER BY tiebreaker), 2026-07-08 preserved-log
  report (`cbrd-26357/5b5ff58/failed_tcs/bigpagesize-report.md`), 2026-08-03 CI-142161 analysis
  (`feat-oos/ci-142161-tde-shell-failures-analysis_e20543df8_claude.md`), predecessor snapshot
  report (`cbrd-26357/ci_analysis_report_c2cbeaf_claude.md`), PR #7588 (CBRD-27157; **draft**
  PoC, head `CBRD-00001-oos-fix-regression-poc`).

## Failure Inventory

| # | Test | Node | Observed signature | Category | PR relation | Confidence |
|---|---|---:|---|---|---|---|
| 1 | `_35_cherry/issue_21654_server_side_loaddb/bigPageSize` | 44 | `loaddb -C` exit 254 on both attempts; `load.log` missing "Total 256 object(s) inserted"; `cub_server` core 00:28:06 inside retry window 00:27:51–00:28:09 | loaddb MVCCID self-lock crash (CBRD-27157) | direct (OOS) | High |
| 2 | `_06_issues/_24_2h/cbrd_25481` | 32 | "Your transaction has been aborted by the system" after CS loaddb/unloaddb steps; 4 in-window `cub_server` cores | loaddb MVCCID self-lock crash (CBRD-27157) | direct (OOS) | High |
| 3 | `loaddb_CS/_01_utility/_17_loaddb/itrack_10006` | 47 | 1st attempt: `cub_admin loaddb … -d MQDB_objects -C` **client process Aborted** (shell: `63340 Aborted`), cases 1–2 NOK; retry: stale workspace (`Volume "itrack_vinf" already exists` → `Database "itrack" is unknown`) | loaddb MVCCID self-lock crash (CBRD-27157) — mapping from PR #7588's local repro, not this run | direct (OOS) | Medium |
| 4 | `loaddb_CS/_05_addition/bug_xdbms_sus880` | 14 | `bug_xdbms_sus880-1 : NOK`; in-window `cub_server` core on retry (00:28:13) | loaddb MVCCID self-lock crash (CBRD-27157) | direct (OOS) | High |
| 5 | `loaddb_CS/_06_issues/_11_2h/bug_bts_5730` — **missing from CircleCI's count** | 33 | cases 1–2 OK; after `loaddb … -d lecl_web_objects lecl -C`, index load `loaddb -i lecl_web_indexes -C` fails with `ERROR: In line 1, column 1 before '<garbage>'` / "Error occurred during index loading."; `cub_server` core 00:27:31 inside window 00:27:11–00:28:43 | server-side-loaddb crash family; exact assert unconfirmed; garbled index file is an open sub-question | direct (OOS) | Medium |
| 6 | `_35_cherry/issue_21522_json/cbrd_23430` | 45 | 1st attempt: createdb + server start OK, then first `csql` after `loaddb --no-user-specified-name -d init_data -C` gets "Failed to connect" (server died); retry: stale-workspace cascade (`Volume "jsondb_vinf" already exists`) | numerable FILE_OOS page-bookkeeping defect (inferred from 8/03 exact stack) | direct (OOS) | Medium |
| 7 | `_39_fig_cake/cbrd_25365` | 38 | NOK cases 6–12, 20, 22, 24 + one timeout (24/28 checks OK); case 6: "Archive log file … not found. Insert sufficient data…"; no core captured this run | numerable FILE_OOS defect family (8/03 stack) — with a live workload-volume alternative for the archive cases | direct (OOS) | Medium-Low |
| 8 | `_36_damson/cbrd_23608_tde/log_enc_04` | 27 | `RVHF_INSERT_NEWHOME is missing!` — grep count 0 in TDE-encrypted log dump; other rcvindex checks pass; no crash | OOS layout change broke TC workload assumption | direct (OOS) | Medium (inferred) |
| 9 | `_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064` | 40 | (excluded from analysis by direction) | CDC — out of scope | — | — |
| 10 | `_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075` | 41 | (excluded from analysis by direction; for core bookkeeping: node 41's 5 cores — 3 `cub_server`, 2 `csql` — all fall inside this test's run window) | CDC — out of scope | — | — |

Core bookkeeping: `artifacts.json` lists 12 cores — node 14 ×1 (bug_xdbms_sus880), node 32 ×4
(cbrd_25481), node 33 ×1 (bug_bts_5730), node 41 ×5 (cbrd_27075 window), node 44 ×1
(bigPageSize). All 12 are attributed to failing tests; none are orphaned.

## Root-Cause Analysis

### 1. loaddb worker MVCCID self-lock assert — CBRD-27157, fixed by draft PR #7588 (4 tests, + 1 likely)

**Observed (this run):** In bigPageSize, `cubrid loaddb -C -d tdb1_objects -s tdb1_schema -udba
tdb2` returned **254** (console trace `+ '[' 254 -eq 0 ']'`), `load.log` ends after "Start
object loading." with no completion line and no error text, and node 44 captured
`cub_server_20260805002806.294.coredump` inside the retry window (the 00:22:14 first attempt
failed identically — deterministic, not flaky; its core did not survive collection).
cbrd_25481 shows the post-crash client signature ("transaction aborted by the system") with
four in-window `cub_server` cores. bug_xdbms_sus880 has one in-window core. itrack_10006's
first attempt shows the **client** utility (`cub_admin loaddb … -C`) dying on SIGABRT — a
different observable than a server-side worker assert, so its CBRD-27157 mapping rests on PR
#7588's local reproduction ("same crash stack" per the PR author, who also authored the 8/03
doc — same source, not independent), not on this run's evidence.

**Mechanism (verified in source at this exact commit):**
`src/transaction/lock_manager.c:3539` contains the unrelaxed
`assert (thread_p->type != TT_LOADDB);` inside `lock_internal_perform_lock_object`. The lazy
OOS file creation path requires an MVCCID: `oos_create_file` → `file_create`
(`src/storage/file_manager.c:3455` calls `logtb_get_current_mvccid` for `FILE_OOS` under
`SERVER_MODE`). Since develop's CBRD-26942 (commit `741734a8f`), first MVCCID issuance takes an
X self-lock via `logtb_acquire_mvccid_self_lock` (`log_tran_table.c:4071`) →
`lock_transaction_mvccid` (`log_tran_table.c:4093`) → the asserting function. On a `TT_LOADDB`
worker thread (assigned in `src/loaddb/load_worker_manager.cpp`) in a debug/optdebug build (CI
is optdebug), the assert aborts the server. PR #7588 relaxes the assert to
`… || is_transaction_lock`; its author reports cbrd_25481, itrack_10006, and bug_xdbms_sus880
passing locally with it.

**bigPageSize belongs to this group but is not claimed by PR #7588.** Its rows (c2 ≈ 12 KB,
c3 ≈ 1.2 MB CLOB locator column, j ≈ 1.5 MB JSON) are OOS-eligible on the 4K-page `tdb2`, so
server-side loaddb triggers lazy OOS file creation. Recommendation: add bigPageSize to #7588's
affected-TC list as "crash layer" (see §2 for why the TC will still not pass).

**bug_bts_5730 (the uncounted 10th failure) is likely this family but unconfirmed.** Same
`loaddb_CS` suite, `cub_server` core at 00:27:31 right after `loaddb … -d lecl_web_objects lecl
-C`. Two open sub-questions: (a) the follow-up index load failed parsing **garbage bytes** in
`lecl_web_indexes` — if the file (written by the preceding `unloaddb`) is genuinely corrupt,
that overlaps the CBRD-26948 family (unloaddb consuming unresolved OOS stubs) rather than pure
crash fallout; (b) no stack. Include it in #7588 local verification; if it still fails there,
treat the index-file corruption as its own defect.

**Falsifier / next observation:** the node-44 (and node-33) core stacks — not downloaded in
text mode. If they do not show `lock_internal_perform_lock_object` ←
`logtb_acquire_mvccid_self_lock` ← `file_create(FILE_OOS)` on a loaddb worker, this attribution
is wrong.

### 2. bigPageSize deep review — the "order by" conclusion, reassessed (requested focus)

Three layers must be kept separate:

**Layer A — what fails in CI today (07fef9d): the loaddb crash above.** The script's
`if [ $? -eq 0 ]` guard means the csql1/csql2 ORDER BY comparison is *skipped entirely* when
loaddb fails; the reported NOK is `diff load.answer load.log failed`. So "bigPageSize fails
because of ORDER BY" is **stale** as a description of the current CI signal.

**Layer B — the ORDER BY tie analysis (CBRD-26828 + 2026-07-08 report) remains sound for the
failure mode it analyzed.** Its evidence was strong: 256 rows tied on `col1 = -32768`
(1 seed row + 8 self-doublings); `heap_insert_physical` vpid/slot instrumentation showing OOS
flips the 4K-page scan-first row from row 1 to row 256 (develop stores these rows as 8-byte
`REC_BIGONE` pointers, 256 per header page; OOS demotes columns and keeps ~656 B `REC_HOME`
records, pushing rows 1–255 to later pages and landing row 256 in the header page's remaining
slot); and — critically — both of csql2's "different" CLOB/BLOB locators were found **verbatim
in `tdb1_objects` on the same dumped row**, proving server-side loaddb preserved locators and
the diff came from *picking a different tied row*, not from data corruption. One bookkeeping
error in the CBRD-26828 draft: its "Actual Result" says the diff is in the `id` column, but
`id` is not in the SELECT list — the actual diff is the `cl`/`bl` locator strings (the only
per-row-unique selected values). Correct this if the draft is filed.

**Layer C — what happens after PR #7588: the residual diff, and a contradiction to resolve.**
The 2026-08-03 local verification (branch `feat-oos-fix-regression-TDE`, #7588 included) found
loaddb succeeds and the TC still fails on a 2-line `cl`/`bl` locator diff. That doc attributes
the diff to **feat/oos loaddb regenerating ELO locators** ("develop preserves locators, so
feat/oos must be regenerating them"), flagged there as needing further debugging. This
attribution **contradicts the 7/08 verbatim-preservation finding** (locators preserved on the
feat/oos build under test then; diff explained by tie-pick alone). The 8/03 doc does not report
the discriminating check (grep csql2's locators in `tdb1_objects`, or compare locator-embedded
timestamps against the tdb2 load window), so tie-pick remains the better-evidenced explanation
— unless a locator-handling regression landed between build `309753d` (7/08) and `e20543df8`
(8/03), which is unverified either way. This report deliberately leaves the question **open**.

**Discriminating experiment (minutes, settles it):** on a #7588-patched local build, run
bigPageSize with cleanup disabled, then:
1. `grep -F '<csql2 cl locator>' tdb1_objects` — found on a *different* dumped row ⇒ tie-pick
   (Layer B story holds end-to-end); absent ⇒ regeneration is real.
2. Cross-check the epoch embedded in csql2's locator names against the tdb2 server start time.
3. Equivalent single shot: apply the CBRD-26828 tiebreaker (`order by 1 desc, id limit 1`) and
   rerun — OK ⇒ tie-pick confirmed *and* the TC is fixed; still NOK ⇒ locator regeneration is
   real and needs a JIRA (including LOB *content* equality verification, since value round-trip
   was never confirmed in the 8/03 run).

**The TC fix was never landed.** Verified at analysis time: `bigPageSize.sh:24` is
`from t order by 1 desc limit 1` on `tc/pr-6864` (tip `e21c7ce9c`), TC `feat/oos` (PR #3806
head — #3806 does not touch bigPageSize), and TC `develop`. Whatever the Layer C outcome, the
256-way tie is proven latent nondeterminism; land the one-line tiebreaker on `tc/pr-6864` (and
mirror into PR #3806) as part of the experiment above.

### 3. Numerable FILE_OOS page-bookkeeping defect family (2 tests, mapping inferred)

**Observed (this run):** cbrd_23430 — the *first* attempt is the informative one: createdb and
`cubrid server start jsondb` succeed, `cubrid loaddb --no-user-specified-name -d init_data -C
jsondb -udba` runs, and the immediately following `csql` gets "Failed to connect" — the server
died right after a server-side loaddb. The collected failure record is the *retry*, which is
pure stale-workspace cascade (`Volume "jsondb_vinf" already exists` → `Database "jsondb" is
unknown`) and must not be read as a crash signature. (The predecessor `c2cbeaf` report called
cbrd_23430 "an environment failure, not OOS" — true of the retry cascade it looked at, but the
first-attempt server death is a real engine signal.) cbrd_25365 — NOK cases 6–12, 20, 22, 24
plus a timeout; no core captured this run.

**Inferred:** the 2026-08-03 analysis reproduced both with exact stacks: `pgbuf_fix_debug`
assert (`page_buffer.c:2564`) — for cbrd_23430 via `oos_insert_many → oos_find_best_page →
oos_file_alloc_new → file_alloc` handing out a page already initialized as a dirty `PAGE_FTAB`
page of the *same* OOS file (user-page/FTAB double allocation), and for cbrd_25365 via
`file_numerable_add_page` (`file_manager.c:8055`) on an ordinary transaction worker. Both are
the **numerable FILE_OOS bookkeeping defect**; ADR-0001's non-numerable migration (implemented
on `oos-m2-all-plans-experimental`) is the fix direction that removes this regime. Two caveats:
(a) this run captured no stacks on those nodes, so the mapping is prior-stack inference;
(b) since cbrd_23430's trigger is also `loaddb -C`, a CBRD-27157 overlap can't be excluded from
this run's evidence alone — the 8/03 stack is what separates them. For cbrd_25365, case 6's own
message ("Insert sufficient data (i.e. increase values in create_insert_tbl()) to archive the
active log") names a live **alternative**: OOS-compacted records may simply generate too little
log volume to roll an archive, which would be the same workload-assumption family as §5, not a
crash. Cases 20/22/24 (patchlog/copydb creation-time checks) also don't fit the crash story
cleanly. Re-judge cbrd_25365 only after the engine fix, on a build where no cores occur.

**Next action:** file the JIRA for the numerable FILE_OOS defect (referencing the 8/03 stacks)
and decide whether to pull the ADR-0001 migration into `feat/oos` before merge.

### 4. CDC tests (2 tests — excluded by direction)

`cbrd_27064` (node 40) and `cbrd_27075` (node 41) are not analyzed per instruction. Node 41's
five cores fall inside cbrd_27075's run window and are bookkept to it (see inventory); prior
context on both tests exists in the 2026-08-03 doc for whoever picks them up. They should not
be used as OOS merge-gate signals until separately triaged.

### 5. TDE log_enc_04 — OOS breaks the workload's log-record assumption (1 test)

**Observed:** the test greps a TDE-encrypted recovery-log dump for a fixed list of rcvindex
types; `RVHF_MVCC_REDISTRIBUTE` (1), `RVHF_INSERT` (8), `RVHF_UPDATE` (6), `RVHF_DELETE` (2)
are all present, but `grep -rc 'rcvindex = RVHF_INSERT_NEWHOME'` returns **0** → NOK. No crash,
no cores.

**Inferred:** `RVHF_INSERT_NEWHOME` has two producers in this tree: the record-relocation path
(`heap_file.c:22010`, REC_NEWHOME on UPDATE overflow of the home page) and the bestspace-page
insert path (`heap_file.c:4048`). Under OOS, the workload's large values (a 20,000-byte pad
into `t2_big`, `varchar(10000)` column adds) are demoted to OOS stubs, so records stay small —
plausibly suppressing whichever producer fired on develop. This is the same family as the eight
TDE TCs already re-baselined on `tc/pr-6864` (OOS layout change invalidating TC expectations),
but log_enc_04 likely needs a **workload** tweak, not just an answer tweak — e.g. an UPDATE
that grows a record while staying under the OOS inline target (~4,060 B at 16 K pages), so the
record genuinely relocates. **Check first** which producer emitted the record on a develop
build at the same TC revision; if develop also produces 0, the OOS attribution is wrong.

## Recommended Actions

1. **Finalize and merge PR #7588** (CBRD-27157; currently a *draft* PoC on head
   `CBRD-00001-oos-fix-regression-poc` — needs a real ticket branch/title before merge).
   Expected to clear cbrd_25481, itrack_10006, bug_xdbms_sus880, likely bug_bts_5730, and
   bigPageSize's crash layer. Add bigPageSize (and bug_bts_5730 if verified) to the PR's
   affected-TC list.
2. **Run the bigPageSize discriminating experiment** (§2 Layer C) on a #7588-patched build,
   which includes landing the CBRD-26828 one-line tiebreaker on `tc/pr-6864` + PR #3806. Tie-pick
   confirmed ⇒ done; still NOK ⇒ new JIRA for ELO locator regeneration in the feat/oos loaddb
   path, with LOB content-equality verification.
3. **Verify bug_bts_5730 under #7588** and inspect `lecl_web_indexes` from a local run — if the
   index file is corrupt independent of the crash, file it separately (possible CBRD-26948
   family: unloaddb consuming unresolved OOS stubs).
4. **File the numerable FILE_OOS bookkeeping JIRA** (cbrd_23430 + cbrd_25365, 8/03 stacks) and
   decide on pulling the ADR-0001 non-numerable migration into `feat/oos`; re-judge
   cbrd_25365's non-crash cases (6–12, 20, 22, 24) afterward, including the log-volume
   alternative for the archive cases.
5. **Fix log_enc_04's workload** on `tc/pr-6864` to genuinely produce `RVHF_INSERT_NEWHOME`
   under OOS, after confirming which producer fires on develop at the same TC revision.
6. **Improve CI evidence retention** for this class of failure: collect core stacks (or rerun
   `cubrid-ci` with `--artifact-mode all` on demand), and preserve `*_loaddb.log` and
   `$CUBRID/log/server/*.err` in the artifact set — the TC's own cleanup (`rm -rf …
   tdb2_loaddb.log …`) currently destroys the loaddb error text that would settle §1 instantly.
7. **File the CircleCI ingestion undercount** (bug_bts_5730 missing from the tests API while
   present in node XML) against the CI tooling — anyone steering by the aggregated count alone
   will miss real failures.

## Evidence and Limitations

- Files inspected: commit `manifest.json`; three suite `summary.json`; `failed-tc.txt`; all
  nine collected `failures/*/{metadata.json,message.txt,diff.txt}`; step logs
  `logs/steps/008-Run_tests/node-{14,27,32,33,38,40,41,44,45,47}.log`; per-node CTP logs
  (`feedback.log`, `test_local.log`, `test-shell.xml`, `main_snapshot.properties`,
  `test_status.data`) for nodes 33, 40, 41, 44, 45, 47; `attempts/143291/raw/tests.json`;
  `artifacts.json` core inventory; engine source at exactly `07fef9d48…` (`lock_manager.c`,
  `log_tran_table.c`, `file_manager.c`, `heap_file.c`, `heap_oos.cpp`, `oos_file.hpp`,
  `load_worker_manager.cpp`, `.circleci/config.yml`); TC repo branches via GitHub API
  (`tc/pr-6864` tip `e21c7ce9c`, `feat/oos`, `develop`); PR #7588 and #3806 metadata via `gh`.
- Coredump binaries were not downloaded (text mode); no backtrace artifacts exist in this run.
  Crash-site attributions are inferred (run-window timing + prior exact stacks) and labeled.
- Only last-attempt cores survive CTP collection; absence of a first-attempt core is not
  evidence against a first-attempt crash.
- The exact TC SHA used by job 143291 is not recorded in the collected evidence
  (`testcase_revision` absent); branch identity is derived from config + content, as described
  in Evidence Scope.
- The Layer C contradiction (tie-pick vs. locator regeneration) is deliberately left **open**;
  this report does not endorse the regeneration hypothesis without the discriminating check.
- CDC root causes are intentionally not asserted here (out of scope by direction).
- Nothing in this report asserts test_sql/test_medium regressions; both were green at this
  commit.
