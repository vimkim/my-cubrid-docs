# Work 456 ticket 12: physical record and key boundaries

Date: 2026-10-21, Asia/Seoul. Audience: PR 8128 reviewers and the ticket 16 implementer.

Ticket 12 delivers and executes the required record and key boundary tests. At source `5551d08fcfa2dc08b3352a71e1b4568af4f72a44`, SQL passes 2/2 and the retained C++ selection passes 14/14. The five-case shell selection has three passes and two correct failures. Both failures preserve the accepted physical-target oracle. They receive no passing-coverage credit.

The source still uses 4086 bytes for demotion trigger and stop. The accepted target is 4060 bytes. The next aligned estimate, 4064 bytes, exposes both differences with `unfill_factor=0.0` and `0.10`. The separate layout, residual and B-tree fixtures complete despite those failures. There is no missing required execution or unresolved expectation in this ticket. Engine readiness remains a separate question.

This report extends the [operation inventory](supplement-operation-inventory-work456-20261021.md), the [C++ inventory](supplement-cpp-inventory-work456-20261021.md), and the [approved ticket12](supplement-tickets/issues/12-physical-record-and-key-boundaries.md). It preserves the [older 4060/4064 reproducer](ci-replan/delivery/03-target-4060-reproducer.sql) without changing its oracle. Source and testcase publication, CI, performance and HA are outside this delivery.

## Authority and exact profile

Required behavior follows [OOS-CONTEXT.md at context commit c6fc51b](https://github.com/vimkim/cubrid-oos-context/blob/c6fc51bc0e27032c9c4fb999ce3e0342b20d2349/OOS-CONTEXT.md), read in full with SHA-256 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`. The checked-out engine establishes current implementation only. The target repair remains linked to [CBRD-27057](https://jira.cubrid.org/browse/CBRD-27057). JIRA reported status `Resolved` and resolution `Fixed` at lookup, but this source lacks the accepted helper and retains both raw-quarter-page comparisons.

| Input | Identity and scope |
| --- | --- |
| Engine | `CUBRID/cubrid`, `5551d08fcfa2dc08b3352a71e1b4568af4f72a44`. clean ticket 12 source checkout. no source changes by ticket 12 |
| Integration PR | [PR8128](https://github.com/CUBRID/cubrid/pull/8128), head `vimkim/cubrid:CBRD-26659-oos-testcases-handover`, base `feature/oos-merge`. the private task branch has no separate PR |
| Build | Linux amd 64, OptDebug, `UNIT_TEST_OOS=ON`. installed identity `11.5.0.2641-5551d08`. 16 KiB I/O and log pages |
| Install provider | Immutable ticket 11 installation. all 247 files in its reviewed immutable manifest matched before copying and after execution |
| Owned install | `~/.cub/install/work456-ticket12/optdebug`. initialized with `cub-workenv init --no-db`. each invocation copies its install, CTP, HOME, registry and configuration |
| C++ execution | Exact copied ticket 11 binaries and registered CTest fixture metadata. only paths and environment select the owned view. setup and teardown execute for each binary |
| Runtime allocation | Owned master port 41096. the final C++ configuration and `CUBRID_CUBRID_PORT_ID` both select 41096 |
| Public TC | Final task commit `8a4a974a103ebb117ebabfc73819d63b574ac2c9`. new logical boundary SQL plus retained `sql05_bigone` |
| Private TC | Curated task commit `5aec7954925cb618fdf0eef83a0814e1e42374d2`. seven added files only |
| Runner | Native `cubrid-testkit`, binary SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`. Go build revision `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`, modified build |
| CTP assets | Commit `9c62858b10005d721546cc007be260844033b9e9` with existing local asset changes. exact changed-script and JDBC-jar hashes are in `final-audit.json` |
| Java | Temurin `8.0.462+8`. exact release-file hash retained. the provider manifest excludes the JDK directory symlink |

Preflights require source/install commit equality. No mismatch exception was used. SQL uses the native SQL family and JDBC with UTF-8 assets. Shell uses the native shell family, one slot, `scenario_disk=on`, no retry, no continuation and no update. Both use `TESTKIT_CONTAIN=1`. The actual slot's network, PID, IPC and mount namespaces differ from the host. Raw configs, input hashes and namespace identities remain with each invocation.

The ticket 12 source checkout has no build directory or compile database. The OOS environment validator reports those limits. This task uses no LSP-dependent result and performs no new compilation. CTest uses the approved owned projection of the matching configured build. `ldd` resolves both CUBRID libraries to its copied installation. The original provider build and install remain unchanged.

## Units and independent oracles

All source anchors below refer to engine `5551d08fcfa2dc08b3352a71e1b4568af4f72a44`.

| Contract | Formula and exact neighbor | Evidence |
| --- | --- | --- |
| Page layout | I/O 16384, reserved area 32, watermark 8, DB page 16344, slotted header 32, slot 4, heap chain 40 bytes | `file_io.h`, `slotted_page.h`, `heap_file.c:290`. matching-library debug symbols confirm structure sizes |
| Nonheader capacity | `spage_max_record_size = 16344 - 32 - 4 = 16308`. nonheader capacity `16308 - 40 = 16268` | `slotted_page.c:841`, `heap_file.c:28138` |
| Physical target | `ALIGN_DOWN((16268 - 4*4)/4,4) = 4060`. next aligned size 4064 | Accepted context. `4*(4060+4)=16256 <=16268`, but `4*(4064+4)=16272 >16268` |
| Variable value | VARBIT uses `ALIGN_UP(prefix + ceil(bits/8),4)` in heap records. prefix is 1 byte below 255 bits, otherwise 5 bytes | `object_representation.h:2340`, `object_primitive.c:13881`. full payload bytes are independent inputs |
| Demotion | Eligible variable representation exceeds the 24-byte stub. ordinary candidates precede PREFER_INLINE, then largest first. stop at 4060 or candidate exhaustion | Accepted context. current path `heap_file.c:12800` |
| Residual maximum | `ALIGN_DOWN(16308 - ALIGN_UP(40,4) - 8*4,4) = 16236`. guard rejects strictly greater estimates | `heap_manager_initialize`, `heap_file.c:3763`. `heap_is_big_length`, line 1079 |
| Three-stub fixture | Max MVCC header 32 + VOT 8 + id/note 8 + bound map 4 + three stubs 72 =124 bytes. fixed BIT 16112 gives 16236, next input byte 16113 gives 16237, aligned successor 16116 gives 16240 | Layout/header computation at `heap_file.c:12720,12757`. guard at line 13806 |
| B-tree transition | `BTREE_MAX_KEYLEN_INPAGE = floor(16344/8) =2043`. VARBIT index encoding uses CHAR alignment, so payload 2037/2038 gives serialized 2042/2043 | `btree_load.h:168`, `btree.c:4125`, `object_primitive.c:13845`. `>=2043` uses overflow |

An early resource message used the wrong decomposition `16288 - 20 - 32` for the residual maximum. The debug-symbol result above supersedes that explanation. The 16236-byte result and executed fixture inputs did not change.

The target estimate reserves future MVCC header fields. It is not the current on-page byte count. For `id INT, payload VARBIT`, input 4011 serializes to 4016 and produces estimate 4060. Input 4012 serializes to 4020 and produces estimate 4064. Their initial stored lengths are 4044 and 4048. At the accepted target, the first remains inline and the second demotes.

The three-stub maximum similarly stores 16220 bytes with a 16-byte INSERT header while the guard estimates 16236. Offline SA observation can remove an all-visible INSERT ID, reducing the actual header by 8 bytes. The reader derives each header from its flags and checks the corresponding length. It never changes the accepted gate or residual maximum to fit observed output.

No test forces four rows onto one page. Unfill controls page selection, not the accepted target formula. The broader impractical guard limits remain in [ticket11](ticket11-serialization-chunk-guard-boundaries-20261021.md). This ticket makes no full-size-storage claim for those limits.

## Physical models and results

Each fixture compares complete values, fixed ballast and row markers against its input model. Lengths and counts support those comparisons. They cannot replace them. CSQL record diagnostics identify the individual stored slot before expansion. HAS_OOS set/clear is checked on that record. An absent rejected row receives no clear-flag credit.

The offline reader checks page identity, encryption state, watermark, slot bounds, record type, MVCC header size, VOT width and every variable-field span. It checks each stub's 24-byte width, serialized length, head stamp and complete chunk payload. The actual chunk page must have one allocated OOS-file owner matching the heap's VFID, HFID and class OID. Physical variable order is not assumed to equal DDL declaration order. Distinct complete values identify fields, while SQL checks each value against its named attribute. Padding equality is not an oracle.

| Fixture suffix | Required model and observed result |
| --- | --- |
| `layout` | `b12_largest`:3000/1200-byte inputs, only the larger attribute demotes. `b12_priority`: PREFER_INLINE 3000 stays inline while ordinary 2000 demotes. `b12_exhaust`: fixed 5000 plus those two candidates demotes both and accepts a residual above target. `b12_noeligible`: fixed 14000 plus a 19-byte VARBIT stays HAS_OOS-clear in REC_HOME. All pass. |
| `layout`, multiple stubs | Twelve inputs 800–811 bytes use distinct values. The largest eight demote, with the first four declaration-order attributes retained inline. The boundary does not split an equal-sized serialized group. All 12 values, eight stubs and SHORT-width VOT spans pass. |
| `residual`, acceptance | Fixed 16112 plus three stubs accepts the exact 16236 estimate. All three full values, stubs, owners and remaining record spans pass. |
| `residual`, rejection | Fixed 16113 INSERT rejects estimate 16237. Fixed 16116 INSERT and UPDATE reject estimate 16240. Error identity is `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE=-1384`, checked through current CSQL catalog text and retained direct C++ error-ID assertions. |
| `residual`, atomicity | A preexisting row owns one OOS chain. Rejected INSERT/UPDATE preserve its full fields, physical identity, CHN, MVCC metadata, SHOW state, owner and every byte of its stub. The separate empty table remains empty with no OOS file. |
| `residual`, pre-insertion proof | Before and after all three rejected writes, complete WAL dumps contain 6 `RVOOS_INSERT` records: two file headers and four value chunks. No insertion record is added. Live chunk counts and full stub images also remain equal. Source places this guard before `heap_attrinfo_insert_to_oos`. |
| `residual`, ordinary bigone | Fixed 17500 with NULL variable value succeeds as REC_BIGONE(type 5), HAS_OOS-clear, with full fixed-value equality and no OOS file. It remains distinct from the OOS rejection. |
| `keys`, exact neighbors | FORCE_OUTLINE payload 2037 and 2038 both have actual indexed-key stubs. Only 2038 has a separate BTREE_OVERFLOW_KEY file. DEFAULT copies at both sizes remain HAS_OOS-clear while preserving the same B-tree transition. All pass. |
| `keys`, larger default key | DEFAULT payload 5107 is itself indexed and OOS-backed, with a distinct key-overflow file. Full values, policy DDL, OOS owner/page mapping and named-index scans pass. No adjacent eligible payload substitutes for the key. |
| `target0`, `target10` | Effective server parameter dumps confirm 0.0 and 0.10. At estimate 4060, HAS_OOS remains clear. At 4064, accepted demotion is missing. Both cases retain FAIL. |
| `target0`, `target10`, stop | Inputs 5000/3983 leave estimate 4064 after the first demotion. The accepted target requires both stubs. Current source stops after one, leaving a 4048-byte initial record instead of the accepted 80-byte initial record. Both cases retain FAIL. |

The key threshold is a successful representation transition. It is not a hard rejection maximum. Overflow descriptors name a BTID, which is matched to the owning B-tree VFID/class separately from the heap's OOS file. Each key fixture executes a query plan using its named key index and checks the complete value. The current 14 KB non-OOS record and 17.5 KB non-OOS bigone also demonstrate why payload size cannot classify HAS_OOS.

These exact fixed-BIT neighbors require different schemas. Key neighbors use separate heaps to attribute overflow files unambiguously. The retained stored-VOT C++ case additionally checks actual clear/set records in one mixed heap. No companion invocation receives credit for observing the public SQL invocation.

## Executed selections and controls

Raw evidence root: `/home/vimkim/temp/work456-implementation/ticket12`.

| Invocation | Exact result | Verdict artifacts |
| --- | --- | --- |
| `shell-final` |5 executed, 3 PASS, 2 correct target FAIL, 0 skip/missing. 76.273 s | `CTP/result/shell/current_runtime_logs/` contains dispatch/finish/status/feedback/XML/logs. `CTP/result/work456-ticket12/<mode>/` retains values, DDL, metadata, raw records/chunks, allocations, WAL and cleanup |
| `sql-final02` |2/2 PASS, 0 fail/skip/missing. 52.519 s | Native result root ends `schedule_linux_sql_64bit_2122593639_11.5.0.2641-5551d08`. Summaries, XML and both generated `.result` files pass the maintained verifier |
| `cpp-final02` |14/14 PASS in three separate CTest invocations, 0 fail/skip/missing | CTest setup/test/teardown XML, GTest XML, started-case identities, discovery, linked-library paths and empty registries |
| `shell-negative` |2 executed, 2 intended NOK, 0 skip/missing. 23.711 s | Disposable wrong HAS_OOS expectation rejects `b12_many`. A disposable wrong final payload byte rejects `b12_key_large` |
| `sql-negative` |2 executed, 1 PASS/1 intended FAIL, 0 skip/missing. 48.970 s | Only the disposable expected answer changes: exact_rows 1 becomes 0. The unchanged engine result 1 fails comparison. |

All native runner processes return 0, including the intended failure selections. The maintained verifier returns 1 for those selections. The separate receipt audit reconciles their expected, dispatched, finished and XML case identities, exact totals and completed feedback. It keeps the failures visible instead of relabeling the run as a pass.

The frozen private execution used commit `09cc3477a7d8f6c25d5ada2926993448be401748`. Its seven selected files are byte-identical to the curated final commit `5aec79549`. During local review, a broad lint-edit glob was found to have touched the older record-flags wrapper. That unrelated file was restored from the live integration. Curated history contains only the seven intended additions. The unused attempt-history branch remains local for inspection. The final audit reconciles 27 selected input hashes and confirms the old observer is unchanged.

Earlier attempts remain retained. `green01`–`green05` expose harness corrections for data-volume mapping, CSQL formatting, physical attribute order, MVCC header removal and valid OOS slot 0. `green06` first completes the three independent passing fixtures and both target failures. `sql-final` has only answer-format differences from independently defined values. The first `cpp-final` has 14 passing assertions but copied a default port into its fixture view. It is provisional and receives no final qualification credit. `cpp-final02` replaces it with explicit allocated-port proof.

## C++ assertion disposition

No C++ test is removed or migrated. Twelve cases assigned by the original inventory remain, plus two relevant VOT contracts added by ticket 11. All 14 execute here at source `5551`. The older 302-case receipt at source `1ef` remains separate historical evidence.

| Case | Retained assertions and reason |
| --- | --- |
| `OosSqlBigone.OosColumnWithBigoneRejected` | Negative execution result, exact error ID and no stored row after abort. retains the SA SQL path. |
| `OosSqlBigone.BigoneWithoutOosColumnSucceeds` | Successful ordinary bigone and one stored row. the new shell adds full-value/type/flag evidence. |
| `OosSqlBigone.OosColumnInlineBetween4kAnd16kSucceeds` | Successful exhausted residual and row count. the new exact maximum extends this broad neighbor. |
| `OosSqlBigone.UpdateIntoOosBigoneRejected` | Exact error ID, abort and preserved NULL value. physical/WAL checks extend this contract without replacing SA execution. |
| `OosSqlBoundary.NullOosColumn` | NULL/insert/update/NULL transitions, count and bit length. its name does not prove placement. |
| `OosSqlBoundary.DropTableWithOos` | Successful inserts, count and DROP. no added file-reclaim claim. |
| `OosSqlBoundary.DropAndRecreateOosFile` | DROP/recreate/insert and complete reported bit length. no invented owner assertion. |
| `OosSqlBoundary.IndexScanWithOos` | Index setup and qualifying count. new key fixtures independently prove indexed-attribute placement and named scans. |
| `OosSqlBoundary.MvccHeaderWithOos` | Repeated committed updates and final bit length. retains its SA path. |
| `OosSqlBoundary.CopyReadPath` | CTAS and destination count. no claim that count proves expanded bytes. |
| `OosSqlBoundary.InsertSelect` | Destination count and selected value length after INSERT SELECT. |
| `OosSqlBoundary.MidSizeColumnsEligibleForOos` | Ten-column insertion, count and first/middle/last bit lengths. new raw layout checks extend placement coverage. |
| `OosBoundaries.StoredVotBoundariesAndExpandedValuesPreserveMixedRows` | Stored record types, row IDs, actual HAS_OOS, VOT width, expansion clearing HAS_OOS and complete expected bytes in one mixed heap. |
| `OosBoundaries.NonOosShortIntVotBoundaryPreservesCompleteValues` | Non-OOS SHORT/INT VOT boundary, fixed fields and complete values. distinct from demotion and SQL counts. |

SQL equality overlaps some observable results. It does not replace direct error IDs, SA lifecycle behavior, stored-versus-expanded flags, VOT widths or full-byte module checks. Therefore no equivalent-replacement or deletion claim is made.

## Cleanup and handoff

`receipt-audit.json` records case reconciliation and actual namespace separation. `final-audit.json` records SQL identities, linked input hashes, dependencies and cleanup. There are zero owned CUBRID/testkit/C++/Java processes after execution. All 22 active attempt/workenv registries are blank or comment-only. Every final shell case and control records `owned_cleanup=1`. The source checkout remains clean. The integration checkout's unrelated CCI header changes are outside this work and remain preserved. Native C is released.

Only this report and its README row are selected documentation. Raw downloads, logs, JSON receipts, copied installations, generated CTest views, models and negative-control corpora remain outside tracked documentation. They substantiate this report through the retained raw root and handoff receipt. No remote branch, issue, PR or CI run was changed.

Ticket 16 must retain the two active target failures and combine the final source/TC revisions before qualification. The accepted oracle must not change to 4086 or to the observed one-stub stop. SA-loader, partition ownership, UPDATE ownership, rollback/vacuum and page-return failures retain their separate repair scopes. This ticket does not repair or qualify them. Performance and HA Work 463 remain deferred.
