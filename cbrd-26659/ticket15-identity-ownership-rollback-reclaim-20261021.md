# Work456/15: identity, ownership, rollback and reclaim contracts

Date: 2026-10-21, Asia/Seoul. Reader: Work456 reviewers and ticket16 implementers. Related engine PR: [8128](https://github.com/CUBRID/cubrid/pull/8128).

The retained C++ cases establish distinct identity, visibility, undo and page-return contracts. Three additions cover real system-worker undo, SQL stub reuse and existing-file TDE application. The SQL reuse case correctly fails against the accepted contract. The TDE and system-worker cases pass. No production code or observation API changes.

## Revision and execution identities

The task source starts exactly at `CUBRID/cubrid@1ef86a7efa34002e971b1b30bcf5d451e9db441b`. Final source commit: `06bc687631f2051e52a8c4df045d3a8f99ac20e2`. The task merges the latest source integration tip before handoff. Source changes affect only tests and CTest registration. The separate ticket14 tests do not change the engine implementation.

Public TC baseline is `410ba5d2ce3151054b11f8443d2da9966a5eafff`. Private TC baseline is `f934b56621c352df84fc7b5a7965148adb07d5ea`. This ticket changes neither repository. The own documentation branch starts from main `52386eea1eef630d6570c15b6bc7ffd7334fd0ec`.

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

## External and prepared-row boundaries

Ticket13 owns its actual CS churn, exact survivors, reader release, acknowledged vacuum and page-return observations. This module PASS cannot prove that ticket13's product pages had older LSAs than their live regular/system horizon. SHOW's conditional scans can omit busy pages. The product-specific page LSA/horizon observation limit remains explicit. The historical positive page-return oracle stays active. This ticket introduces no perfect-packing or fresh-heap-equality requirement.

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
