# Work456/13: independent churn, reclaim, reuse, and space observations

Date: 2026-10-21, Asia/Seoul. Reader: the Work456 coordinator and testcase reviewers. Related PRs: [engine 8128](https://github.com/CUBRID/cubrid/pull/8128), [private TC 4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365).

This report answers whether independent repeated writes preserve exact values and recover reusable OOS storage. The original invocation source is `CUBRID/cubrid@1ef86a7efa34002e971b1b30bcf5d451e9db441b`. Ticket 13 changes testcases only. The original seven required shell cases executed, and all four new churn workloads completed three cycles. Their page-return observations and the retained rollback/vacuum regression failed. A separate eighth case now supplies exact product-owned page census and post-restart reuse evidence. It passed on committed inputs without changing those historical oracles or reconstructing their earlier live horizons.

## Baseline and test seams

The source branch is `task/work456-13-source` in `work456-ticket13`. It starts at the exact handover source above. The task branch has no associated PR. The starting branch belongs to engine PR 8128, head repository `vimkim/cubrid`, head `CBRD-26659-oos-testcases-handover`, base `feature/oos-merge`.

The private TC branch `task/work456-13-private` starts at the integrated ticket 01 commit `5e8a9eaa885a53922826ff5320787f1115034a13`. The original invocation used public TC `df8596dd999e825b1ec9812a735bbe01e50ac715`. Ticket 13 has no public TC edits. Documentation branch `docs/work456-13` starts at `c784cd0008f8943bf7f1b25be8bd49381d60391e`.

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

The fresh heap has the same schema and exact two-row base model. Each cycle compares its state with the churn heap at that same live model. `SHOW HEAP OOS` identifies the owned class/HFID/VFID and reports OOS user pages, chunks, record bytes, physical bytes, and unused bytes. Unused bytes indicate aggregate slack. The original four churn tests do not measure exact fragmentation within each page. The additional qualified census below records exact per-page free-space and occupancy fields for its separate fixture.

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

## Stopped-page census and mixed-mode restart receipt

The additional native case is `cbrd_26659_qualified_reuse`. Its implementation is private TC commit `f6b84ff96ce4b9b90267e384c59ddfde5fa5e771`. Its product source and copied immutable ticket 14 installation are `d13aebf6428a68c2852d16df143d1da203d86dea`, Linux 16 KiB optdebug with the provider's `UNIT_TEST_OOS=ON` build setting. No test hook is activated by this product case. This source adds ticket 14 unit coverage to the original product baseline. The earlier seven-case invocation remains attributed to `1ef86a7`.

Independent review subsequently found that the initial two stopped diagnostic rounds in this receipt still used `vacuum_disable=n`. SA boot can run vacuum for these normal utility clients (`src/transaction/boot_sr.c:2652`). The seven returned pages cannot therefore be attributed solely to CS vacuum. All raw frames remain exact post-diagnostic observations. Later pressure rounds already used verified `y`, so their restart/reuse proof remains valid. The guarded reruns below supply separate mode-qualified evidence; this receipt is never relabelled pure CS.

The case uses acknowledged owned server shutdown, then the existing `diagdb -d 1` file-table dump to enumerate every allocated VPID for the exact OOS VFID. `diagdb -d 2` independently reconciles the class/HFID/VFID ownership. Reserved but unallocated pages receive no occupancy credit. The file-table parser reconciles sector, user, table, free and allocated-page totals, including full-sector headings that the utility can append to its preceding VPID line. Volume paths come from owned `spacedb` output and must resolve inside the fixture directory.

The read-only helper opens only those stopped owned volumes. Debug symbols in the actual provider library qualify the Linux little-endian layout: 16,384-byte I/O page, 32-byte reserved header, 16,344-byte DB area, eight-byte duplicate LSA watermark, 32-byte slotted-page header and four-byte slot. It validates VPID, page type, plaintext flags, watermark, slot spans and record counts. Deleted slots are empty when their offset is zero; their old length may remain. Source anchors at `d13aebf` are `src/storage/file_io.h:165`, `src/storage/slotted_page.h:64`, `src/storage/slotted_page.c:2094` and `src/transaction/log_lsa.hpp:38`. The helper requires GCC and this explicitly checked profile; a missing capability produces NOK rather than skipped proof.

Every raw allocated page is copied to an attempt artifact before fixture deletion. A separate Python audit decodes the retained frames independently of the C helper. It reconciles all VPIDs, page LSAs, exact chunk counts and complete row-specific payloads. The serialized VARBIT model follows `src/base/object_representation.h:2340`: a five-byte prefix and four-byte packed alignment make a 16,000-byte value occupy 16,008 serialized bytes, plus its 24-byte OOS header. A one-chunk record therefore occupies 16,032 bytes and cannot share a data page with another such record or the survivor.

The seed has the original two-row base plus 64 distinct 16,000-byte values. Their segments are `31 × 5000`, `72 × 6000`, `a3 × 4998`, then the two-byte row ID. After exact SQL equality/current-record checks and an initial stopped census, the case restarts, commits DELETE of those 64 rows, acknowledges log/vacuum progress, checks the complete surviving base, then stops again. Chunk deletion and actual page deallocation are separate observations.

At that second stopped boundary, the final run found seven old data VPIDs absent from the exact allocation set, one live survivor chunk, and 57 still-allocated empty data pages. Each empty page had 16,308 total and contiguous free bytes. A fresh actual process restart ends the prior process's undo sources. Vacuum is disabled and acknowledged by hidden parameter dump in the new process. An owned non-OOS logged transaction commits before the append barrier is captured. All 57 persisted old page LSAs are strictly below barrier `[194, 8328]`. Inference from the acknowledged graceful restart and the pinned head-LSA lifecycle: fresh process transaction heads cannot retain the ended process's undo state, and new heads originate at fresh append positions after persisted old page LSAs. Pressure records start at or after the captured barrier. Individual system-head values are not reconstructed by this census. This qualifies the new restart workload, not the earlier live horizon.

The next 125 independent committed inserts use distinct payloads `b4 × 5000`, `c5 × 6000`, `d6 × 4998`, then their two-byte row ID. Their intermediate stopped census proves that all 57 prior empty VPIDs now contain one exact new chunk each while the file still owns the same two sectors. This avoids inferring sector reservation order solely from page LSAs. After another acknowledged restart, eleven more committed inserts force permitted growth. No perfect-packing equality against a fresh heap is used: one survivor page, 136 full-size single-chunk pages, one protected sticky header and one file-table page require 139 pages, exceeding the prior 128-page reservation.

| Stopped census, `qualified-final01` | Exact chunks | Chunk record bytes | OOS user pages | File-table pages | Reserved sectors |
| --- | ---: | ---: | ---: | ---: | ---: |
| Seed peak | 65 | 1,030,284 | 66 | 1 | 2 |
| DELETE/vacuum drain | 1 | 4,236 | 59 | 1 | 2 |
| All old candidates reused | 126 | 2,008,236 | 127 | 1 | 2 |
| Further required growth | 137 | 2,184,588 | 138 | 1 | 3 |

The final growth census preserves every candidate's new value. Each candidate's new page LSA precedes the first occupied new-sector page LSA `[205, 5200]`. The intermediate census is the direct no-growth proof; this LSA ordering is supplemental. Exact SQL equality and independent raw decoding cover all bytes at every census, with one current REC_HOME row per expected ID. OOS counts remain separate from ordinary heap/index and whole-database volume observations.

These mixed-mode results are bounded positive observations. Conditional page-latch misses and refill outcomes can permit transient growth; an unqualified ordering or failed intermediate observation would remain an observation/attribution gap, not proof that every candidate was unbusy on every allocator call. Two complete mixed-mode invocations passed their then-current oracles. No new engine defect is inferred from the earlier testcase-parser/configuration errors or from those permitted transient outcomes.

| Additional attempt | Native artifact result | Executed scope / correction |
| --- | --- | --- |
| `qualified-red01` | 1 NOK, 0 skip, 17.399 s | Peak and drained logical fixture executed; parser wrongly required cleared lengths on deleted slots. |
| `qualified-green01` | 1 NOK, 0 skip, 21.807 s | Exact drain/deallocation census passed; an unnecessary bare checkpoint-interval override rejected restart. In-controller cleanup reported failure; native containment exited and the outer copied registry was empty. |
| `qualified-green02` | 1 NOK, 0 skip, 21.409 s | Drain and fresh restart executed; vacuum-disable validation needed the utility's hidden-parameter dump. |
| `qualified-green03` | 1 NOK, 0 skip, 44.157 s | Complete final logical values executed; full-sector dump parsing failed. The initial record-byte model omitted packed VARBIT alignment. |
| `qualified-green04` | 1 NOK, 0 skip, 26.515 s | All raw counts/values executed; first pressure page LSA equalled the captured append position, requiring the correct `>=` relation. |
| `qualified-green05` | 1 PASS, 0 skip, 31.934 s | Intermediate no-growth census and all later phases passed; 63 retained empty candidates reused. |
| `qualified-final01` | 1 PASS, 0 skip, 31.329 s | Clean committed inputs; exact one required = selected = dispatched = finished = XML PASS; 57 retained candidates reused. |

For that mixed-mode receipt, the maintained verifier reports 1 PASS, 0 failures, 0 skips. All 13 wrapper-required phases passed; there is no missing, timed-out or unexecuted required phase in this new case. The separate raw audit also checks native status totals and exact dispatch/finish/XML identities. All owned DB, registry, directory, process-group and configuration cleanup assertions passed. The native C lease was released afterward.

Two read-only diagnostic controls use copied actual final pages, never a source DB: the unchanged sparse copy passes, while one changed watermark byte fails with `offline census: page watermark mismatch`; a mismatched free-page total fails exact file-header/bitmap reconciliation. The previous independent same-length wrong-value control remains valid. None changes committed expectations. The provider installation matches all 236 entries in ticket 14's final manifest after execution.

Raw evidence and scripts remain under `ticket13/qualified-final01`, `qualified-offline-controls`, `offline-layout-gdb.log`, `offline-layout-enum.log`, `qualified-provider-audit.json` and `audit_qualified.py` in the external evidence root. The original attempts and their original qualification limits remain intact.

## Observer-mode correction and authoritative guarded receipt

The observer correction is private TC commit `89d1730e48a8a43bfcc9c498bbf506d268126c6d`. Before **every** stopped diagnostic round, it saves the exact preceding configuration, temporarily sets vacuum disabled, and invokes the effective parameter check and both diagnostics with `CUBRID_VACUUM_DISABLE=y`. This preboot environment guard matters because `paramdump -S` itself calls `db_restart` (`src/executables/util_cs.c:2402`). `prm_check_environment` applies the explicit override before boot (`src/base/system_parameter.c:7361`). The hidden dump must confirm `y` before either diagnostic executes. Raw frames are then read, and exact saved bytes and SHA-256 are restored. A failure cleanup hook restores the saved configuration as well. Only the raw inspector's file access is claimed read-only; SA boot is not claimed to have no administrative side effects.

The authoritative guarded invocation is **`qg3`**, product source/install `5551d08fcfa2dc08b3352a71e1b4568af4f72a44`, copied immutable provider 11, Linux 16 KiB optdebug. Its assertions and all 16 helper files match committed `89d1730e4`. Its frozen attempt-owned wrapper adds only read-only namespace recording; the exact patch and all executed input hashes are retained. It does not change workload or verdict logic.

The copied shell configuration explicitly selects the workenv allocation: master 41076, broker 41077, master SHM `0x6200004c`, application SHM `0x6200004d`, and broker 2 OFF. Effective CS parameters confirm master port 41076. `CUBRID_JAVA_HOME` explicitly selects the copied bundled Temurin 8u462 JDK. Its `libjvm.so` matches the earlier provider's audited library; plain `JAVA_HOME` alone is not the PL loader's selector (`src/sp/pl_sr_jvm.cpp:330`). The attempt-local TMP produces an 89-byte PL socket path, within the 108-byte `sockaddr_un.sun_path` limit.

Host namespace IDs were recorded before launch. The actual positive slot recorded its own IDs before the controller. All four differ: host PID/net/IPC/mount `4026531836/4026531840/4026531839/4026531841`; positive slot `4026537296/4026537297/4026537295/4026537294`. These are the positive receipt's own values, not the negative run's IDs.

Every peak and drain observation confirms preboot vacuum disabled, then restores the exact preceding **n** configuration hash. Reused and pressure observations confirm the same guard, then restore their preceding **y** configuration hash. All four complete observer-mode receipts pass. The pre-restart CS phase and acknowledged CS shutdown return **58** old data VPIDs. The protected stopped diagnostics leave **6** exact allocated empty pages, each with 16,308 total/contiguous free bytes. All six old LSAs precede the fresh-process barrier `[195, 15232]`. The next intermediate census proves all six pages reused while the same two sectors remain. Further pressure independently requires the third sector. Full SQL equality, current-record checks and independent raw decoding pass for every complete payload at all four censuses.

| Stopped census, guarded `qg3` | Exact chunks | Chunk record bytes | OOS user pages | File-table pages | Reserved sectors |
| --- | ---: | ---: | ---: | ---: | ---: |
| Seed peak | 65 | 1,030,284 | 66 | 1 | 2 |
| CS DELETE/vacuum drain | 1 | 4,236 | 8 | 1 | 2 |
| All six old candidates reused | 126 | 2,008,236 | 127 | 1 | 2 |
| Further required growth | 137 | 2,184,588 | 138 | 1 | 3 |

`qg3` is 1 required = selected = dispatched = finished = XML PASS, zero failure/skip, 29.551 seconds wall time. All 13 required wrapper phases pass, four distinct owned server generations exit cleanly, all owned process groups are empty, the DB/registry/directories disappear, and both controller and framework configuration restoration pass. All 247 entries of the immutable provider 11 manifest remain unchanged; its manifest SHA-256 is `445cfbe889268e11db98b315fc76ee18cf12e856eb3c31452914905ec8ca4e50`. Native B was released after this audit.

The independent intended guard control **`qgn2`** keeps the actual preboot override at `y` but changes only the disposable copy's expected guard predicate. It reaches the protected parameter check, confirms actual `y`, then fails with `observer vacuum-disable guard not effective`. Native XML has 1 NOK and zero skips; the maintained verifier rejects runner exit 0. Exact cleanup succeeds in 11.520 seconds. This is intended negative-control propagation, not an engine failure. It does not change committed expectations.

Two preceding attempts remain separate failures. `qualified-guarded01` (76.681 seconds) passes the protected peak census and exact prior-n restoration, then expires the 40-second CS restart readiness deadline. Its master eventually exits 1 while the next server repeatedly attempts to reconnect. `qualified-guard-negative` (55.290 seconds) expires initial server readiness before the intended guard check, with a Java SP `CallStaticIntMethod` error. Their later required phases and intended guard-negative propagation are unexecuted. Both preserve failed in-controller stop/delete receipts; subsequent owned group reaping and native teardown complete, and outer copied registries are empty. Neither is a page-return failure or a successful negative control.

Read-only path calculation found the failed negative attempt's PL socket path was 110 bytes (`src/sp/pl_comm.c:228`), exceeding the Unix socket field. The shortened setup corrects that verified path problem and explicitly uses the allocated ports/SHM. It does not establish a cause for the earlier master exit, and inherited port 1568 in a contained attempt is not evidence of a host collision. `qg2` is a separate guarded full PASS, 29.801 seconds, with **61 returned / 3 retained-and-reused** pages; it lacks the positive namespace receipt, so `qg3` is authoritative. Its numbers are never mixed with `qg3`'s **58/6** or mixed-mode `qualified-final01`'s **7/57**.

The prior pure watermark/allocation and full-value negative controls retain their exact older artifact scopes. The C inspector and its invariant checks are unchanged, but those controls do not become physical-input controls for this new CS run. The detailed guarded receipt is `ticket13/guarded-final-audit.json`, with full raw-value audit in `qg3/independent-audit.json`; both remain outside Git. Earlier twelve page-return polls retain their original live-horizon limits. The guarded result does not reconstruct those earlier internal horizons or turn a transient conditional-latch/refill miss into a proven defect.

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


## Acceptance boundary and handoff

All eight required product case identities have executed across the original seven-case invocation and the separate qualified case. The four original independent workloads complete all required cycles and exact reader/survivor checks. The separate guarded `qg3` case supplies the additional actual-page observation evidence for its stopped-page and fresh-process restart scope, with exact empty-page identities, old LSAs, actual deallocation, reuse before further growth, and independently necessary growth.

The earlier twelve bounded page-return observations remain under triage for their original hidden live horizon and conditional SHOW-count limits. The historical page-return and CBRD-27237 oracles remain correct FAILs and retain their separate repair links. No new result relabels those attempts. The original snapshot's later embedded churn and rollback case's later physical diagnostic remain unexecuted after their preserved failures, as recorded above; independent owned cases supply the required safe workload coverage. The new case leaves no required phase unexecuted. A conditional-latch or refill outcome is not, by itself, a new engine defect.

The source task includes integration `5551d08fcfa2dc08b3352a71e1b4568af4f72a44`, which is also the guarded product source. The private task includes integration `5dbddeadf77dbde60aeb7b5e2bacfc09fe1f3dab` before the guard commit and execution freeze. The docs task includes main `de21a6dd0c7ce91e152a381024c8f18aaf8b96c2`, preserving its reports and index rows.

The retained documentation changes are this report and its README index row. Raw logs, copied installations, controls and receipt JSON remain outside Git. Ticket 13 makes no engine or public-TC edits. No publication, destination merge, CI or TC PR action occurred. The coordinator owns acceptance review, final integration and tracker state.
