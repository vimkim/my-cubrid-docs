# Work456/13: independent churn, reclaim, reuse, and space observations

Date: 2026-10-21, Asia/Seoul. Reader: the Work456 coordinator and testcase reviewers. Related PRs: [engine 8128](https://github.com/CUBRID/cubrid/pull/8128), [private TC 4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365).

This report answers whether independent repeated writes preserve exact values and recover reusable OOS storage. The source is `CUBRID/cubrid@1ef86a7efa34002e971b1b30bcf5d451e9db441b`. Ticket 13 changes testcases only. All seven required shell cases executed. All four new workloads completed three cycles. Page-return observations and the retained rollback/vacuum regression failed. The product eligibility observation limit below still prevents ticket 13 completion.

## Baseline and test seams

The source branch is `task/work456-13-source` in `work456-ticket13`. It starts at the exact handover source above. The task branch has no associated PR. The starting branch belongs to engine PR 8128, head repository `vimkim/cubrid`, head `CBRD-26659-oos-testcases-handover`, base `feature/oos-merge`.

The private TC branch `task/work456-13-private` starts at the integrated ticket 01 commit `5e8a9eaa885a53922826ff5320787f1115034a13`. The public TC head remains `df8596dd999e825b1ec9812a735bbe01e50ac715`. Ticket 13 has no public TC edits. Documentation branch `docs/work456-13` starts at `c784cd0008f8943bf7f1b25be8bd49381d60391e`.

The [approved supplement](supplement-spec-work456-20261021.md) supplies the test seams. Native shell controls the lifecycle and sessions. CSQL checks complete values. Existing product diagnostics observe current stored records, OOS chunks/pages, heap capacity, index capacity, file ownership, reserved sectors, and database volume use.

The [ticket 01 receipt](ticket01-baseline-and-observer-20261021.md) supplies the matching Linux, 16 KiB, optdebug installation. Ticket 13 copies that immutable installation before use. Its own workenv selects a separate copied prefix and allocates master/broker ports 41076/41077 and SHM IDs 1644167244/1644167245. `cub-workenv init --no-db` creates no host DB. Every native invocation uses another disposable install, CTP, HOME, empty registry, configuration, TMP, and scenario overlay. The native runner SHA-256 is `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`. Each preflight requires `commit_match=yes` without an exception.

The source worktree has no build directory or compile database. Static source inspection does not depend on these facilities. No source build or C++ execution occurs in ticket 13. Pre-existing CCI and CTP modifications remain intact.

## Independent logical and physical oracles

The base model has two exact rows. Row 0 holds the six literal bytes `19ab23cd45ef`. Row 1 holds 4,207 bytes: `19` repeated 1,200 times, `87` repeated 1,400 times, and `fe` repeated 1,607 times. Row 0 has HAS_OOS clear. Row 1 has HAS_OOS set. The fixture has only one variable attribute, `payload`.

Each cycle inserts rows 2–33. Each payload has 33,001 bytes. The initial generation uses segments `2a × 10000`, `cb × 11000`, `56 × 12000`, and one final byte equal to the row ID. The UPDATE generation uses `a4`, `d5`, and `e6` for those first three segments. The row-specific final byte prevents substitution between rows. Full SQL equality checks every byte beside the exact ID model. Independent MD5 checks supplement equality. CSQL hashes the hexadecimal character form of VARBIT for this function.

The intended physical models are:

| Phase | Current logical rows | OOS chunk records | Sum of OOS record bytes |
| --- | ---: | ---: | ---: |
| Base or drained survivor state | 2 | 1 | 4,236 |
| Base plus one temporary generation | 34 | 97 | 1,062,796 |
| Old reader retains the first generation after UPDATE commits | 34 per reader | 193 | 2,121,356 |

The serialized VARBIT lengths and 24-byte chunk headers produce these byte totals. They are intended input/layout models, not captured defective output. Each UPDATE reader first pins REPEATABLE READ. The writer then commits the complete replacement model. The old reader must still read its complete initial model. A fresh reader must read the complete replacement model. The controller acknowledges reader commit and process exit before it advances vacuum eligibility.

Current `SELECT_RECORD_INFO` observations project full value equality beside aliased row IDs, record type, physical slot, MVCC IDs, and flags. The ticket 01 observer rejects relocated records, duplicate identities, delete-marked records, and incorrect values or flags. Updated current records must pass this check in their actual fixture. Old-reader values use ordinary snapshot reads. They receive no old-version flag attribution from the physical-slot observer. A deleted row receives no clear-flag credit.

Chunk deletion and page return have separate assertions. The controller closes relevant log blocks, then requires the first log page still needed by vacuum to exceed the mutation block. It checks exact surviving values and the complete expected chunk model. Page return then has a separate bounded poll. One remaining chunk can occupy at most one data page, plus the sticky header page. If the diagnostic count is exact, every other formatted data page is empty. This requirement concerns empty-page return and requires no cross-page compaction.

Eligibility has an additional source condition. At the pinned source, `oos_reclaim_sample_horizon` includes regular transaction and internal system-transaction head LSAs, then clamps that horizon to the sampled append LSA (`src/storage/oos_file.cpp:1454`). Product SHOW statistics do not expose every empty page's LSA or the internal system horizon. `oos_get_stats_by_vfid` also accepts a slight undercount when a conditional page fix fails (`src/storage/oos_file.cpp:3829`). `SHOW TRANSACTION TABLES` scans regular `all_tdes` entries without the separate system-transaction map (`src/transaction/log_tran_table.c:5474`). Closed owned sessions and completed relevant vacuum blocks do not, alone, establish that hidden condition. The report therefore distinguishes product bounded page-return observations from deterministic internal eligibility evidence owned by ticket 15. The actual process-restart case ends prior-process transaction state. Fresh-heap size alone never proves eligibility.

## Space attribution and comparison

The fresh heap has the same schema and exact two-row base model. Each cycle compares its state with the churn heap at that same live model. `SHOW HEAP OOS` identifies the owned class/HFID/VFID and reports OOS user pages, chunks, record bytes, physical bytes, and unused bytes. Unused bytes indicate aggregate slack. The tests do not measure exact fragmentation within each page.

`SHOW HEAP CAPACITY` identifies the ordinary heap separately. `SHOW ALL INDEXES CAPACITY` identifies the narrow primary-key B-tree separately. Neither count substitutes for OOS pages. `spacedb` describes the whole database, including the log-filler table and fresh reference heap. Its totals do not attribute all growth to OOS.

The controller stops only its owned server for offline `diagdb`. File descriptions must agree with the saved class/HFID/VFID. File-table headers then give exact allocated/free page and reserved-sector counts. Source `src/storage/file_manager.c:297` defines those fields. Equal live data and sector reuse are the comparison conditions. A reader may legitimately require both value generations at once. The IUD sector baseline therefore includes its first such highwater. Reserved sectors and operating-system volume files need not shrink afterward.

## Native execution ledger

Raw evidence is retained outside Git under `/home/vimkim/temp/work456-implementation/ticket13`. Each attempt records preflight, expected selection, config, input hashes, command, runner status, timing, and native artifacts. Optional attempt-owned evidence retention preserves phase SQL, diagnostics, journals, and cleanup receipts before the native scenario overlay disappears.

| Attempt | Selection / result | Interpretation |
| --- | --- | --- |
| `red01` | INSERT/DELETE tracer, 1 NOK, 0 skip, 13.841 s | Test-helper argument error after the 34-row physical fixture passed. The existing owner observer expects a JSON filepath. |
| `green01` | INSERT/DELETE tracer, 1 NOK, 0 skip, 66.187 s | All three logical/chunk cycles and refill executed. Its early page sample and unsupported equal-peak-page assertion needed oracle correction. |
| `batch01` | 7 selected/executed, 1 PASS, 6 NOK, 0 skip, 331.592 s | IUD/restart exposed harness and observer-scope errors, updated before the final run. |
| `final01` | 7 selected/executed, 1 PASS, 6 NOK, 0 skip, 459.820 s | All new cycles completed on committed TC inputs. Correct FAIL oracles remain active. |
| `negative-value` | Separate 1 selected/executed, 1 NOK, 0 skip, 9.383 s | Same-length wrong final byte failed the full-value assertion and native verifier. |

`green01` retained low page counts 11, 17, and 98 with one live chunk, against two fresh pages. Its first/final reserved sectors were 2/2. These are observations at its exact input hashes. The unsupported peak-page equality assertion supplies no engine-failure attribution. The bounded corrected attempts supply the current disposition. The historical page-return and rollback-after-vacuum scripts retain their existing intended oracles.

`batch01` dispatched all seven cases and returned 1 PASS, 6 NOK, and zero skips in 331.592 seconds. Snapshot visibility passed. The first IUD cycle passed its old-reader and exact UPDATE/chunk checks, then cycle 1 met a test-helper guard against reusing a persistent-session bootstrap name. The restart case completed its first restart and exact logical values, then the strict observer rejected retained physical `REC_MARKDELETED` slots with NULL attributes. These are harness/observer-scope errors. Their dependent phases are explicitly unexecuted in that attempt. The final implementation uses unique session names and retains an all-slot diagnostic beside its current-REC_HOME-only classification. Missing current rows or relocated live rows still fail the exact expected set. Deleted slots receive no clear-flag credit.

The private TC implementation is commit `f245c6e31`. The task branch includes the current `tc/pr-8128` integration tip. `final01` selects all seven cases from these committed inputs in sorted dispatch order. The independent audit matched the exact expected, dispatched, finished, feedback, test-log, and XML case populations. Status totals agree with XML. Every input hash still matches the clean committed file. The maintained verifier rejects the six NOK cases despite runner exit 0. No required phase is missing from the four new workloads. Cleanup succeeded in all seven cases: owned DB registration and directories disappeared, all owned groups were empty, and configuration was restored.

| Exact shell case basename | Required executed behavior | Native verdict |
| --- | --- | --- |
| `cbrd_26659_churn_insert_delete` | Three independent INSERT/DELETE cycles, exact mixed survivors, chunk drains, fresh comparisons, sector reuse | FAIL: three bounded page-return observations |
| `cbrd_26659_churn_insert_update_delete` | Three INSERT/UPDATE/DELETE cycles, three exact old readers, reader release, both chunk drains, fresh comparison, sector reuse | FAIL: three bounded page-return observations |
| `cbrd_26659_churn_restart` | Three cycles with acknowledged process stop/restart, exact current rows/flags, next writes and final sector reuse | FAIL: three bounded page-return observations |
| `cbrd_26659_churn_abort_retry` | Acknowledged INSERT abort, exact base, retry, three cycles and final refill | FAIL: three bounded page-return observations |
| `cbrd_26659_snapshot_visibility` | Exact old/new snapshots and acknowledged obsolete-chunk drain | PASS |
| `cbrd_26659_snapshots_reclaim` | Exact old/new values and stable 9→4 chunk drain, page-return assertion | FAIL: 9→9 pages after the acknowledged vacuum boundary |
| `cbrd_27237_rollback_vacuum` | Immediate rollback model, control-table vacuum completion, attempted complete pre-image read | FAIL: OOS metadata inconsistency error on the post-vacuum read |

Each basename identifies `shell/_40_guava/<basename>/cases/<basename>.sh`. The final expected list contains those seven absolute tracked paths in dispatch order. The original snapshot case's embedded churn remains unexecuted after its page-return assertion. The new independent cases execute the churn obligation. The rollback case's later physical-count diagnostic remains unexecuted after the failed full-value read. Neither dependent phase receives passing credit. No native command or outer case timeout occurred. Twelve page-return polls reached their separate 20-second deadlines. Those deadlines are operational bounds, not speed thresholds.

At equal exact live data, the final invocation observed:

| Workload | OOS user pages after cycles 0 / 1 / 2 | Fresh OOS user pages | Owned OOS sectors, baseline→refill |
| --- | --- | ---: | --- |
| INSERT/DELETE | 10 / 98 / 9 | 2 | 2→2 |
| INSERT/UPDATE/DELETE | 177 / 153 / 175 | 2 | 4→4 |
| Restart | 15 / 98 / 55 | 2 | 2→2 |
| INSERT abort/retry | 100 / 28 / 27 | 2 | 2→2 |

Every low state reports one OOS chunk and 4,236 record bytes. Each ordinary heap reports one data page and its narrow primary-key index reports one B-tree page. The fresh heap reports the same heap/index counts. For example, the last ID low state reports 9 OOS pages and 142,860 aggregate unused bytes, against fresh 2 pages and 28,452 unused bytes. These remain slack observations, with the conditional-fix limitation above. The last IUD low database totals 5,568 used permanent pages of 12,288. The other three total 5,376 used pages of 12,288. These whole-database totals include filler, catalog, reference-heap, and reserved space.

The wrong-value control changes only the expected final byte from `ef` to `ee`. The inserted value stays correct. Both row count 2 and payload byte sum 4,213 remain unchanged. `value_ok` and `digest_ok` each become 1 instead of 2. The full-value assertion fails, the native case records NOK, and the artifact verifier rejects runner exit 0. Cleanup passes. The disposable control changes no committed expectation.

The coordinator released the native lease after both invocations and cleanup audits. The own workenv doctor reports ready without opening a DB. It reports 1,970 inaccessible other-user PIDs, so it supplies no global inactivity claim.

## C++ dispositions and repair boundaries

Ticket 13 retains all existing C++ cases. It keeps every case at its existing seam. Product equality does not replace private hint, cursor, latch, horizon, fault, or SA lifecycle assertions. The [complete inventory](supplement-cpp-inventory-work456-20261021.md) remains authoritative for those identities.

All 11 `OosGrowthSweepTest` cases remain required. They include `SweepReclaimsAfterCommittedDeleteBurst`, `TransientWriteLatchMissKeepsReclaimDebt`, `ConcurrentGrowerWaitsForActiveSweep`, `SweepLeavesAbortRestoredChunksAlone`, `InsertRollbackRearmsGrowthSweep`, `SweepIsIncrementalWithCursorContinuation`, `SweepCursorWrapsAcrossSectorBoundary`, `SweepCounterResetsOnCleanLapAndRearms`, `SweepDefersUncommittedDeletesButAllowsGrowth`, `BootRuleSweepsUnconditionallyAfterRestart`, and `SweepSkipsRefilledPageAndNeverReclaimsHeader`. The boot-rule case simulates all hint loss. The shell restart case establishes an actual process restart. Those contracts remain distinct.

Retain the related bestspace, delete, mock-vacuum, real-vacuum, remove-file, vacuum leaf/heap, SQL eager-cleanup, and SQL update/delete targets. Ticket 14 supplied its separate baseline receipt. Ticket 13 reconciled all 116 inventory cases assigned to 13 against the receipt's expected, runtime-discovered, started, console-passed, and XML-PASS identities. All match. The receipt is `/home/vimkim/temp/work456-implementation/ticket14/baseline/receipt.json`, SHA-256 `d55d4243db537e6c8c5338ffd15d8f41429e76391f04d18990b367cbbb585b9e`. The exact per-case reconciliation is retained as `ticket13/cpp-reconciliation.json` with raw evidence. That mode enables `UNIT_TEST_OOS=ON` in ticket 14's own optdebug build/install. It is separate from the ticket 13 product invocation.

| Retained target | Exact assigned cases | Baseline XML result |
| --- | ---: | --- |
| `test_oos_bestspace` | 23 | 23 PASS |
| `test_oos_delete` | 9 | 9 PASS |
| `test_oos_delete_server` | 9 | 9 PASS |
| `test_oos_growth_sweep` | 11 | 11 PASS |
| `test_oos_mock_vacuum_server` | 6 | 6 PASS |
| `test_oos_real_vacuum_server` | 10 | 10 PASS |
| `test_oos_remove_file` | 8 | 8 PASS |
| `test_oos_remove_file_server` | 7 | 7 PASS |
| `test_oos_sql_eager_cleanup` | 12 | 12 PASS |
| `test_oos_sql_update_delete` | 7 | 7 PASS |
| `test_oos_vacuum_server` | 14 | 14 PASS |

Ticket 15 owns any further deterministic eligibility, identity, and hint assertions. Generic unit eligibility checks do not establish the horizon or LSA of a page from this product invocation.

Separate repair scopes remain [CBRD-26786](https://jira.cubrid.org/browse/CBRD-26786) and [CBRD-26658](https://jira.cubrid.org/browse/CBRD-26658) for reclaim/reuse, [CBRD-27237](https://jira.cubrid.org/browse/CBRD-27237) for rollback/vacuum, and [CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230) for commit-conditional notification and chain ownership. These links do not establish a common cause for a new timeout. Unresolved attribution remains under triage. Ticket 13 makes no engine repair, CI, performance, perfect-packing, or OS-shrink claim.


## Remaining acceptance boundary

There is no remaining missing execution in the four new workloads. The retained regressions execute their failing assertions. The rollback error and historical page-return oracle remain visible. This report identifies their separate repair scopes.

One product observation capability gap remains: the actual formatted pages and their reclaim horizon are not fully qualified in the CS invocation. The new bounded page-return NOK results therefore remain under triage for eligibility attribution. A generic C++ PASS, fresh-heap count, or successful sector reuse cannot close that gap. Ticket 15 must provide applicable actual-page/eligibility evidence or leave the gap open. Ticket 13 must not be marked resolved while this required evidence is missing.

The only retained documentation changes are this report and its README index row. Raw logs, copied installations, controls, and receipt JSON remain outside Git. Source and public TC have no task edits. No publication, integration into destination branches, CI, or TC PR action occurred. The source/TC task branches include their current integration tips. The coordinator owns final integration and tracker state.
