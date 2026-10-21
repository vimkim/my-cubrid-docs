# Work456/15: identity, ownership, rollback and reclaim contracts

Date: 2026-10-21, Asia/Seoul. Reader: Work456 reviewers and ticket16 implementers. Related engine PR: [8128](https://github.com/CUBRID/cubrid/pull/8128).

The retained C++ cases establish distinct identity, visibility, undo and page-return contracts. Three C++ additions cover real system-worker undo, SQL stub reuse and existing-file TDE application. Three independent CS additions cover committed-only notification, borrowed undo, unassigned whole-stub retention and observable dropped-chain release/repeat safety. The original C++ run has nine PASS and one correct engine FAIL. The separate CS run has three correct engine FAILs. No production code or observation API changes.

## Revision and execution identities

The task source starts exactly at `CUBRID/cubrid@1ef86a7efa34002e971b1b30bcf5d451e9db441b`. Executed source commit: `06bc687631f2051e52a8c4df045d3a8f99ac20e2`. The original C++ run and each separately identified CS batch use its immutable installation. The revised CS batch preflights against clean detached source `/home/vimkim/gh/cb/work456-ticket15-runtime06bc`, with commit matching enabled. The handoff source branch also merges ticket11 integration `5551d08fcfa2dc08b3352a71e1b4568af4f72a44`; that merge receives no new runtime credit here. The integrated source tip is `9c21a1ae701c847803690bd1c567b74f0d0918a9`; the retained task source branch is `e1d7dd0af735d5b71f3dcab9232c7058c1da7ddd` with the same tree. Source changes affect only tests and CTest registration. The separate ticket14 tests do not change the engine implementation.

Public TC baseline is `410ba5d2ce3151054b11f8443d2da9966a5eafff`. The new private TC checkout starts at `216d131098becb3f44056844052ca907b67dfae0`, incorporates current integration `db047bd8ea3842d5a79d10b9f16d77314d93ca0d`, and first executes committed tests at `1e7633340973081a68c650d0009801366327c1fd`. After merging integration `5dbddeadf77dbde60aeb7b5e2bacfc09fe1f3dab`, the compatibility correction produces the compatibility batch’s executed private TC tip `f0c9dd0f33106b39678b9395ebbd2b55ec125d67`. The later release/repeat invocation uses `be66aecbb45dcd6abaa577c4cadb36ab78381135`; its handoff branch is `de44129ef63270e9a670c02a51d22eeac8756c04`, as detailed below. Its two changed helper expressions have separate rerun evidence; earlier receipts keep their original inputs. This ticket adds five private TC files. The public TC repository remains unchanged. The own documentation branch starts from main `52386eea1eef630d6570c15b6bc7ffd7334fd0ec`.

The build uses Linux, 16 KiB database/log pages, `CMAKE_BUILD_TYPE=OptDebug` and `UNIT_TEST_OOS=ON`. Configure, build and installation use the maintained preset workflow. The own build is `work456-ticket15/build_preset_optdebug`. The own installation is `/home/vimkim/.cub/install/work456-ticket15/optdebug`. CCI remains at `79d0888c26a2543d31f53eb7b6c9738db110fff4`, with generated version-header dirt excluded from commits.

The complete normative OOS context has SHA-256 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`. Its identity, UPDATE ownership, LSA horizon and existing-file encryption requirements supply the intended oracles. The [accepted SA decision](../cbrd-27424/sa-inline-preservation-decision-20261017.md) supplies the prepared-row boundary.

## Retained cases and dispositions

All **238 ticket15-related cases** remain. Their **1,981 lexical assertion sites** remain unchanged. Helper assertions also remain. The raw disposition file joins every exact ID, source location and assertion to ticket14's frozen baseline receipt. All 238 required IDs match discovery, started IDs and XML PASS results. These are retained results at source `1ef86a7`, within 302 cases from 29 separate fixture-aware invocations. They are not 238 new executions by ticket15.

| Binary | Retained cases | Contract retained |
| --- | ---: | --- |
| `test_oos` | 21 | SA file API, bytes, stubs, chunks and malformed headers |
| `test_oos_server` | 36 | SERVER owners, publication, replica fixup, allocation faults and grouped reads |
| `test_oos_identity_stamp` | 33 | Issued/persisted identity, stale references, grouped reads and abort restoration |
| `test_oos_delete` | 9 | SA chain deletion, stale reads, space and emptied-page candidates |
| `test_oos_delete_server` | 9 | SERVER chain deletion, stale/reused references and space |
| `test_oos_eager_diagnostics` | 10 | Kept post-image chains, dropped stale references, diagnostics and error paths |
| `test_oos_bestspace` | 23 | Cache, page/slot reuse, sync, eviction and delete feedback |
| `test_oos_growth_sweep` | 11 | Cursor, writers, rollback, latch misses and simulated hint/boot loss |
| `test_oos_remove_file` | 8 | SA file destruction and page-return gates |
| `test_oos_remove_file_server` | 7 | SERVER file destruction and regular-transaction page-return gates |
| `test_oos_mock_vacuum_server` | 6 | Direct-delete workloads with vacuum-like orchestration |
| `test_oos_vacuum_server` | 14 | Vacuum leaf and heap seams, crafted identity references and eager cleanup |
| `test_oos_real_vacuum_server` | 10 | Real daemon, reader horizons, chunks, version chains and repeated vacuum |
| `test_oos_no_logging` | 1 | Actual no-logging mode and its stamp-uniqueness exception |
| `test_oos_tde_gate` | 3 | User-data encryption classification by recovery index |
| `test_oos_sql_crash_recovery` | 2 | SA restart and forked-writer committed crash redo |
| `test_oos_sql_delete` | 8 | SA SQL deletion, survivors and reinsertion |
| `test_oos_sql_txn` | 8 | SA commit, rollback, combined writes and multichunk undo |
| `test_oos_sql_update_delete` | 7 | SA assigned/unassigned UPDATE, transitions and delete/reinsert |
| `test_oos_sql_eager_cleanup` | 12 | SA synchronous cleanup and repeated replacement/deletion |

There are no remove or migrate candidates. SQL equality cannot replace internal identity, fault, publication, batch, buffer or execution-mode assertions. Names and payload lengths alone do not establish actual HAS_OOS placement for older SQL fixtures.

## Identity and eligibility are separate

A chain reference combines the head OOS OID and its issued identity stamp. Existing tests reject stale reads and skip stale deletes. They preserve current occupants through slot reuse, deallocation and page retyping. Abort tests retain the original reference before deletion. They check restored bytes and stamp after regular-transaction abort, sysop abort and recovery-image restoration.

These assertions establish target identity. They cannot establish ownership or deletion eligibility. A borrowed undo stub can equal the live record's entire stub. The accepted UPDATE contract assigns ownership to the newest logical version. It requires commit-conditional notifications for dropped chains. Undo images are never deletion sources.

`ForwardWalkReclaimsLiveReferenceAndSkipsStaleOne` retains its narrow current leaf identity and retry assertions. Its PASS does not approve the obsolete forward-walk cleanup source. Reader cases retain their actual schedules and chunk outcomes. They do not establish the page LSA and undo horizon of every external product page.

SA eager cleanup remains separate from SERVER MVCC cleanup. `UpdateKeepsAChainTheNewImageStillReferencesAndDiagnosesOnlyTheDropped` checks a retained chain and a dropped stale chain in one eager UPDATE. It does not establish the SERVER commit-notification contract.

## Added contracts

| Exact new ID | Independent intended oracle | Result |
| --- | --- | --- |
| `OosFileDestroyServerTest.SystemWorkerUndoDefersPageReturnAndAbortRestoresTheChain` | Real system-worker deletion empties a real page. Active system undo prevents return. Abort restores the issued stamp and every payload byte. After a committed delete, the empty page returns only after its LSA precedes all regular/system undo heads and append LSA. | PASS |
| `OosSqlOwnership.UnassignedUpdateRetainsWholeStubAcrossCommitAndAbort` | SQL UPDATE of id1 to id2 preserves the unassigned payload's head OID, length and stamp. Assigned replacement followed by abort restores the committed stub, CHN and complete value model. | Engine FAIL: the first UPDATE changes head OID and stamp |
| `OosSqlOwnership.ExistingOosFileReceivesClassAesAndPreservesIdentityAndValues` | Existing populated NONE OOS file receives class AES. After shutdown/reopen, its VFID, stub, length, CHN and complete values remain. File and every mapped user page report AES. | PASS |

The SQL fixture has one fixed integer and one variable attribute. Its value contains 17,001 `a1` bytes, 17,003 `b2` bytes and 17,003 `c3` bytes. Complete SQL equality uses an explicit VARBIT cast. The heap COPY observer verifies `REC_HOME`, the expected integer and actual HAS_OOS. It then parses the sole variable attribute's complete stub. A second heap fetch must reach `S_END`, so extra rows cannot escape the model.

The reuse failure is a direct conformance observation within [CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230)'s accepted repair scope. It does not prove another branch's repair outcome or every SERVER notification defect. Full committed values, assigned-update abort, restored committed reference and CHN pass. The changed OID/stamp assertions stay active. No expected answer copies the defective result.

The TDE test uses the existing class metadata setter, class flush and `xfile_apply_tde_to_class_files`. That function explicitly includes an already-created OOS file at the baseline [file-manager boundary](https://github.com/CUBRID/cubrid/blob/1ef86a7efa34002e971b1b30bcf5d451e9db441b/src/storage/file_manager.c#L12485). This is an SA module invocation. It does not claim SQL ALTER encryption syntax, CS execution, new WAL/sentinel coverage or coverage of another fixture. It closes the existing-file application observation at this reachable boundary within [CBRD-26830](https://jira.cubrid.org/browse/CBRD-26830)'s scope. Ticket04's lazy-file, WAL, sentinel and crash receipts remain separate.

The page-return test records actual page LSA, system undo head, regular horizon and append LSA. The baseline [horizon implementation](https://github.com/CUBRID/cubrid/blob/1ef86a7efa34002e971b1b30bcf5d451e9db441b/src/storage/oos_file.cpp#L1454) considers regular transactions and system-worker tdes. The test creates and retires a real registered system-worker transaction. It fabricates neither LSA nor horizon. It proves its own direct-storage candidate contract within [CBRD-26786](https://jira.cubrid.org/browse/CBRD-26786)'s scope.

## Added SERVER commit notification and borrowed-undo schedules

The [locked T4 ownership decision](../cbrd-27230/wayfinder/tickets/T4-lock-cleanup-architecture.md) requires on-disk `RVOOS_NOTIFY_VACUUM` only for a committed UPDATE that drops an assigned old chain. An aborted UPDATE and an UPDATE assigning no OOS attribute emit none. Older logical versions borrow their references; undo images never supply deletion candidates. [T8](../cbrd-27230/wayfinder/tickets/T8-write-path-mechanics-of-reuse.md) preserves this invariant while requiring notification before MVCC completion. Tests use this accepted invariant without assuming a future payload or record layout.

The frozen engine [reserves the index without an emitter](https://github.com/CUBRID/cubrid/blob/06bc687631f2051e52a8c4df045d3a8f99ac20e2/src/transaction/recovery.h#L206). An actual CS replacement and committed restart therefore must still fail if its complete owned WAL contains no notification. A crafted leaf reference and the SA eager-cleanup case cannot replace this assertion.

Each case creates its own database, table and transactions. The table has fixed integer `id`/`note`, a small inline VARBIT row and a 5,107-byte OOS VARBIT row. Independent literals cover every payload byte and the complete row set. A persistent REPEATABLE READ reader retains A before and during the writer's mutation, and again after commit or rollback. A fresh reader verifies the current complete model. Both sessions close before stopped diagnostics and the later acknowledged vacuum.

| Exact private shell case | Intended oracle | Observed result at `06bc687` |
| --- | --- | --- |
| `cbrd_26659_notify_commit` | Assigned A-to-B UPDATE commits. The old reader retains A; current B survives restart/vacuum. Complete WAL contains a dropped-chain notification. | Engine FAIL only at `commit_notification`: zero notifications. Ordinary OOS WAL, full values, old reader, ownership and vacuum checks PASS. |
| `cbrd_26659_notify_abort` | Assigned A-to-B UPDATE aborts. Original complete stub and A remain. No notification appears. Vacuum cannot delete the live A through its borrowed undo reference. | Absence, restored whole stub, reader and current A PASS. Engine FAIL at `after_vacuum_values`: metadata inconsistent/corrupted after acknowledged vacuum. |
| `cbrd_26659_notify_nodrop` | UPDATE changes only `note`; the OOS attribute is unassigned. Its entire 24-byte stub remains. No notification appears; A survives vacuum. | Engine FAIL only at `retained_whole_stub`: actual head/stamp change. Full A, absence, old reader and vacuum checks PASS. |

The commit and no-drop failures are directly within [CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230)'s accepted scope. The abort/vacuum failure is recorded separately against [CBRD-27237](https://jira.cubrid.org/browse/CBRD-27237)'s rollback exposure scope. These links do not prove the internal cause of the observed corruption or a repair outcome. No defective result becomes an expected answer.

Stopped `diagdb -d 8 -- DB 1 -1 -1 -1` supplies the complete owned WAL. Every case independently requires the log-dump banner, numeric record LSAs and ordinary `RVOOS_INSERT` records before checking the notification name. Complete raw dumps include binary value data and are retained losslessly as gzip artifacts with hashes. The test does not parse an unspecified future notification payload. It does not claim per-chain multiplicity, crash-time ordering, retry consumption or an internal vacuum deletion-source trace from record presence alone.

Actual current `REC_HOME` rows are joined to stopped `diagdb -d 9 --dump-records --class-name dba.oos_live` hex and its complete class representation. `diagdb -d 1` provides the allocated file owner. The copied ticket08 parser records meaningful CHN and validates offsets from that representation, actual HAS_OOS, whole stub, head/stamp, chain bytes and matching class/HFID/VFID. The first batch uses copied qualified helper SHA-256 `a6a2ecc0e6f1dad13ee32e2804590da2593b100b0a3982f826ace0e4291e8cdc`; the compatibility revision uses `e3bf5769d3928bd9af47b6faa78e97bf357467c6aab54182bd0118498fb85f0e`. The output's `d13aebf` profile label identifies the inherited format qualification, while this receipt identifies the actual executed engine `06bc687`. Its accepted profile is plain Linux little-endian 16 KiB, current representation and modeled VARBIT fields. It grants no relocated-row or alternate-format credit. Padding is ignored. Stops can prune MVCC flags, so whole-header identity is not required.

The abort case retains the exact initial 24-byte stub before vacuum. The no-drop case observes a new head `1|835|0` replacing `1|834|0`, with the same logical value length but a different issued stamp. This is actual CS stored-row evidence, independent of the earlier SA failure. After reader/transaction closure, plain inline filler advances the log and `vacuumdb -C --dump` acknowledges a first-unvacuumed page beyond the mutation's complete four-page block. The intended live-value survival assertion stays active. Normal CS execution uses vacuum; only stopped diagnostic SA boots temporarily disable vacuum, then restore the configuration before restart.

The first committed O46 batch has selected/finished/XML **3/3/3**, **0 PASS / 3 correct engine FAIL / 0 skip**, and **44 distinct assertion phases**. Each schedule reaches its COMPLETE marker and passes owned cleanup. Native runner exit is 0; the strict passing verifier correctly rejects all three NOK cases. The delivery audit independently verifies each exact failure and all other phases. That first batch receipt is `ticket15/o46/final01/receipt.json` under the evidence root below, SHA-256 `ea1dc83fc8852dc84e8cac3c5659649677e3cf2cc3b818eb8589ee5d3279d12f`. Its exact committed-input audit supersedes a static runner-template note that incorrectly labels these inputs uncommitted. The original ten-case C++ receipt remains unchanged and separate.

Disposable controls count only the injected oracle and cleanup in their native wrapper. Their complete controller journals retain known engine failures separately, so a preexisting failure cannot supply the control's native NOK. `nv02` changes only the expected final A byte from `c3` to `c2`, at unchanged length: the normally-passing `initial_values` phase fails, with the other row still matching. `nw02` substitutes the known ordinary `RVOOS_INSERT` label as the forbidden token: normally-passing `no_notification` fails on the observed positive count. Each exact one-case XML is NOK solely at that injected phase, with COMPLETE and cleanup preserved; the strict passing verifier rejects it. The `nv02` receipt SHA-256 is `ff5c2abf5bb3d04800316f0841305d6d7c12e4f15991040d5faf368dbe94106a`; `nw02` is `02aba7b1bd88fc9af5ce2848119f47fd388b1d069ba6b2b79270f36aaa4e1388`. Final cleanup finds zero owned executables and empty attempt registries. All 248 immutable installation hashes still match. These two isolated controls retain their older TC `1e763334` input scope. Their counted full-SQL and grep oracles are unchanged by the compatibility correction; they receive no revised-helper native credit.

The copied helper originally used `Path.is_relative_to` and `int.bit_count`, which CI Python 3.6 does not provide. Private commit `f0c9dd0f3` changes only those two expressions to resolved ancestor membership and `bin(mask).count("1")`. The file/no-symlink checks and resolved ownership boundary remain. A Python 3.6 grammar parse, API audit, five path cases and all 256 flag values verify compatibility equivalence. These checks do not claim execution by a Python 3.6 interpreter. The revised native batch at TC `f0c9dd0f33106b39678b9395ebbd2b55ec125d67` completes in 97.97 seconds. Exact selected/dispatched/started/finished/XML counts are **3/3/3/3/3**: **0 PASS / 3 correct engine FAIL / 0 skip**, with the same 44 distinct phases and exact three intended failure phases. All six complete physical checkpoints PASS; every schedule reaches COMPLETE and passes owned cleanup. Runner exit is 0 and strict passing verifier exit is 1. New receipt `ticket15/o46/py36/r01/receipt.json` has SHA-256 `e9b7dc61eb08417a74c1c1a2d1b7857c84ecc06b4a5100d11b994266aa00efa9`. Its audit verifies committed input objects, complete native ledgers, status, XML, full WAL artifacts and unchanged 248-file installation. The copied registry is empty and no owned executable remains.

Pure physical-parser controls use that revised run’s actual initial heap/classrepr, file-owner dump and independent row models. Replaying the inline row with the correct observer succeeds. A disposable observer that adds one to the popcount fails at fixed-row identity. A diagnostic copy that maps the OOS volume through a parent symlink to an outside regular file fails at `volume outside owned DB`; the final file itself is not a symlink, so the resolved-ancestor guard supplies the rejection. Both controls exit 2 at their intended error, with a positive control exiting 0. They run on Python 3.9.21 without database execution and receive no native XML credit. Receipt `ticket15/o46/py36/physical-controls/receipt.json` has SHA-256 `946f7426d0341db632b32b221ed8c8e003ff3959c20d07e6b8c62ef12992789e`. Old receipts retain their original inputs and hashes.

The first WAL probe exposed CLI negative arguments without `--`; the first value-control attempt exposed an overlong copied TMP socket path and did not reach its oracle. These are retained setup failures without conformance credit. Shorter owned attempt names keep the native slot's copied TMP socket paths within `sun_path`. Complete gzip retention is also verified in the final run. No production or testkit repair is included.

## Actual committed release and repeated acknowledged vacuum

A later independent audit identified a remaining O46 gap: notification presence and B survival do not establish that dropped A is gone or that repeating vacuum preserves the exact owned chunk set. The earlier receipts retain their original scope. This follow-up changes only private testcases and this report. It starts from integrated private `5c0fc6175881efac22f623dbc1169b84b0aa455b` and docs `0f4ff3807b6a1584805f61f45dddffb1bc1caa9e`, on separate release branches. Source remains integrated `e1d7dd0af735d5b71f3dcab9232c7058c1da7ddd`; no source, C++, engine or provider change occurs. The new native invocation uses the same strictly matched clean detached `06bc687` and immutable installation.

Private revision `be66aecbb45dcd6abaa577c4cadb36ab78381135` adds an allocated-page census to the actual committed SQL schedule. Every allocated page of the actual class/HFID/VFID owner is read while stopped, with vacuum disabled only for diagnostics. The observer checks the complete diagdb allocation count, volume/page identity, watermarks, plain 16 KiB profile, slot spans, overlap and occupied-slot/header counts. `PAGE_FTAB` is separately declared metadata. All other allocated pages must be `PAGE_OOS`; unsupported types/layouts remain observer gaps. Every occupied value slot is inspected, including slots unreachable from the current B stub. SHOW's potentially busy scan is not used as exact count evidence.

The one file-statistics record is also separate from value chunks. Only slot 0 on the exact owner file's diagdb `vpid_sticky_first` can be `OOS_HDR_STATS`, and only when its REC_HOME type, 264-byte length and VFID match. The frozen library's debug layout confirms size 264 and VFID offsets fileid 0/volid 4. The pinned [declaration](https://github.com/CUBRID/cubrid/blob/06bc687631f2051e52a8c4df045d3a8f99ac20e2/src/storage/oos_file.hpp#L133) and [creation path](https://github.com/CUBRID/cubrid/blob/06bc687631f2051e52a8c4df045d3a8f99ac20e2/src/storage/oos_file.cpp#L1147) establish this role. Every other occupied slot on that page is still inspected. Cached statistics and unused padding supply no equality or counting oracle.

The actual owner is VFID `1|832`, HFID `641|1|640`, class `0|195|2`. Initial A has saved reference `1|834|0`, stamp `177|9616`. Before vacuum, current B has `1|835|0`, stamp `177|13088`; the census sees both A and B. The first acknowledged vacuum advances beyond mutation page 177 to first-unvacuumed page 184. The subsequent guarded census reads all four allocated pages and finds exactly one value chunk, B. Saved A is absent from active allocated records. The statistics record at `1|833|0` remains separately qualified. Empty allocated pages need not return for this contract.

The second pass uses fresh plain filler IDs starting at 100000 and distinct command/dump/acknowledgement paths. Its own mutation bound is page 187 and acknowledgement is page 192. Complete B and inline-row values pass before and after this second pass. The second census has the same exact B chunk set/count and meaningful chunk metadata. The saved A reference remains absent. No notification or earlier release failure can short-circuit these phases. These assertions establish observable release and repeat stability; they do not claim an internal deletion-call count or prove the obsolete forward-walk architecture conforms to the required notification design.

| New required commit phase | Intended result | Actual result |
| --- | --- | --- |
| `initial_owned_chunks`, `after_owned_chunks` | Qualified exact owner census and saved A/current B reference sets | PASS; one A, then A plus B |
| `released_stored_bytes`, `released_owned_chunks`, `dropped_chain_released` | Full B/inline model; saved A absent; every owned value chunk belongs to B | PASS; exactly one B chunk |
| `repeat_vacuum_ack`, `repeat_vacuum_values` | Fresh distinct acknowledgement and complete current values | PASS |
| `repeated_stored_bytes`, `repeated_owned_chunks`, `repeat_chain_set`, `repeat_stable_set` | Complete values and unchanged exact B-only set/count after repetition | PASS |

The new `once/r02` batch completes in 112.33 seconds: selected/dispatched/started/finished/XML **3/3/3/3/3**, **0 PASS / 3 correct engine FAIL / 0 skip**, with **55 distinct assertion phases**. All new release/repeat phases and eight complete stored-row checkpoints PASS. The three overall case failures remain exactly the missing commit notification, aborted-value corruption after vacuum and unassigned-stub change. All schedules reach COMPLETE and pass cleanup. Strict passing verification rejects the three NOK cases; the independent delivery audit accepts the exact intended outcomes. Receipt `ticket15/o46/once/r02/receipt.json` has SHA-256 `83a225445d481c0cb6d11376956fba275881f5051f4408dfbcaf3ab0c52ee955`.

Pure controls use this invocation's actual references, exact census and saved raw frames. Correct release, repeat stability and complete raw replay each pass. Replacing saved A with live B fails at the A-absence oracle. Adding A to the expected B-only set fails the exact set/count oracle. Lowering a live data page's raw record count from one to zero fails the occupied-slot/header count guard. All three intended failures exit 2 at their specific assertions. These are Python 3.9.21 offline controls, without database execution or native XML credit. Their receipt SHA-256 is `6efa5c4064ebde7330bf4f58845d9fe4809062c1734dca5dc5af9fcb3417a9c6` at `ticket15/o46/once/controls/receipt.json`. Python 3.6 syntax/API compatibility is audited; no actual Python 3.6 execution is claimed.

The first `once/r01` attempt rejected the sticky statistics record as an unknown value-header layout. It retains no release-once credit and is preserved as an observer implementation gap. The corrected run qualifies that exact metadata record and all value slots. File-only debug-layout inspection and a replay of ticket13's independently saved frames qualify format guards only; they supply no ticket15 product-release or page-eligibility credit. New helper SHA-256 is `e450910acf8074d4fe8b4543fc44f928f4b73936d3ae40d899501bc2f876c762`.

The new receipt pins actual private suite namespaces, short TMP, Java identity, allocated ports/SHM, complete diagnostic frames, both acknowledgements and all input objects. The 248 immutable installation hashes remain unchanged, the copied registry is empty, and no owned executable remains. Native B is released. Original C++10, earlier O46 batches, compatibility replay and isolated SQL/WAL controls retain their separate revisions and unchanged receipts.

## External and prepared-row boundaries

Ticket13 owns its actual CS churn, exact survivors, reader release, acknowledged vacuum and page-return observations. This module PASS cannot prove that ticket13's product pages had older LSAs than their live regular/system horizon. SHOW's conditional scans can omit busy pages. That historical live-SHOW observation limit remains explicit. Any subsequent stopped-census and bounded restart/growth qualification belongs to ticket13’s own receipt, source, pages and barrier. It cannot retroactively establish an earlier live-SHOW horizon. The historical positive page-return oracle stays active. This ticket introduces no perfect-packing or fresh-heap-equality requirement.

Growth-sweep tests retain simulated hint loss and boot-state reset. Resetting a side map is not a process restart. The retained crash-recovery binary has its own actual SA process/restart proof. Neither receipt supplies ticket13's missing product-specific eligibility observations.

Prepared-row requirements preserve values, meaningful headers and workspace-assigned CHN, policies, ownership, transactions and buffer lifetime. Unused padding identity remains superseded. The accepted decision's 21 stored-row and 13 loader/workspace cases ran on separate source `6a487cdb6`. They are absent from this baseline's 302-case population and receive no current-branch PASS credit. Ticket14's actual COPY/PEEK lifetime evidence and ticket04's actual loader receipts keep their own boundaries. This ticket adds no competing prepared-row path.

## Native verification and negative controls

The final source and installed release both identify `06bc687`. The catalog contains 307 declarations in 30 binaries after ticket14 integration and three ticket15 additions. This final run executes only the two binaries below. Their declaration, discovery, selection, live GTest start and XML identities agree. CTest repeats failed output in its summary. The audit counts the prefixed live stream once and checks duplicate XML identities separately.

| Final CTest binary | Required/discovered/started/XML | PASS | Engine FAIL | CTest status |
| --- | --- | ---: | ---: | ---: |
| `test_oos_remove_file_server` | 8/8/8/8 | 8 | 0 | 0 |
| `test_oos_sql_ownership` | 2/2/2/2 | 1 | 1 | 8 |

No required case is missing, disabled or skipped. The delivery audit exits 0. The strict passing verifier exits 1 because the correct ownership failure remains. It grants no passing credit to that case.

The system-worker candidate is page `1|706`. During its uncommitted delete, page LSA and system undo head both equal `177|2496`. Reclaim leaves the page allocated, and sysop abort restores its original bytes and stamp. After the later committed delete, the empty page LSA is `177|2928`, the regular horizon is NULL and append LSA is `177|3128`. The test checks every system head is NULL or newer before reclaim. The actual page then becomes deallocated.

In the failed SQL reuse case, the stored head changes from `1|709|0`, stamp `176|11024`, to `1|713|0`, stamp `176|14240`. Both identity assertions fail. Complete committed values, assigned-update rollback, the restored committed stub and restored CHN pass. The separate TDE case completes all actual NONE-to-AES, reopen, file/page, identity and full-value assertions.

| Disposable control | Selected/started/XML | Intended result | Actual verifier result |
| --- | --- | --- | --- |
| `red-control-03` | 1/1/1 | Wrong AES expectation disagrees with five actual NONE user pages | Exactly one failed case, only five page-algorithm assertions, CTest 8 and strict verifier 1 |
| `negative-value` | 1/1/1 | Change only the expected final byte from `c3` to `c2`, at unchanged length | Exactly one failed full-value assertion, CTest 8 and strict verifier 1 |

The first development attempts exposed a fixed-field order assumption and a missing VARBIT cast. A preliminary assertion also assumed SQL UPDATE always increases CHN. The accepted CHN rule preserves workspace-assigned values and does not impose that SQL rule. Final source uses one fixed field, an explicit value cast and preservation of the committed CHN through rollback. The raw history preserves these attempts without assigning them engine-failure credit.

Final receipt SHA-256 is `a6d7836709f64e3fb71a2f05ac35a5199cc1232d791cd27209aeff285524f89e`. The 248-file installation manifest has SHA-256 `ccf56f4bdd257ca5210b441c6b1f7c6384e2022045188c995977f4a4eb7659af`. Every hashed installed file is unchanged after execution. The receipt also pins both test executables, configuration and CMake files. A separate manifest pins the actual linked libraries.

The immutable shared baseline receipt has SHA-256 `d55d4243db537e6c8c5338ffd15d8f41429e76391f04d18990b367cbbb585b9e`. Its source `1ef86a7` results remain separate from this final source `06bc687` run. These two revisions do not become one combined invocation.

Every CTest invocation owns a fresh `unittestdb` fixture and cleanup. The runtime uses the maintained installation-use lock. Its config and registry live in `work456-ticket15/.cub-workenv`. Master/broker ports are 41084/41085. Broker SHM IDs are 1644167252/1644167253. TMP is `/tmp/cwe-1000/6d7fb8657672`. Config selects 64 MiB data buffer, 16 MiB log buffer and `vacuum_log_block_pages=4` for this database.

Logs use regular files and bounded subprocesses. Core dumps are disabled. All observed owned processes, registrations and database files disappear after execution. Maintained cleanup leaves an empty fixture/LOB directory tree. Allocated config bytes remain unchanged. Doctor reports inaccessible other-user PIDs, so this report makes no global-host inactivity claim. No shared installation, global service or IPC cleanup occurs.

The raw evidence root is `/home/vimkim/temp/work456-implementation/ticket15`. It retains source catalogs, exact required/new IDs, assertion dispositions, CMake registration, discovery/start/XML receipts, binary and installation hashes, control sources, verifier results, configuration and cleanup identities. Large artifacts stay outside Git. The selected document and README index are the only documentation changes.

No source/TC push, integration-destination merge, CI trigger or TC PR action occurs in this implementer. Ticket16 must combine the separately scoped receipts without converting failures or observation limits into passing coverage.
