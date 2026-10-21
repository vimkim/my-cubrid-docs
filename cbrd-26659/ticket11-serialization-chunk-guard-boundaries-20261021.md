# Work 456/11: serialization and buffer boundaries

Date: 2026-10-21, Asia/Seoul. Readers: the Work 456 coordinator and boundary-test reviewers.
Related PRs: engine [8128](https://github.com/CUBRID/cubrid/pull/8128), public TC [3688](https://github.com/CUBRID/cubrid-testcases/pull/3688), private TC [4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365).

This report checks the serialized profitability floor, chunk capacity, VOT widths, length guards and stub writer bounds.
The intended oracles distinguish input bytes, terminators, serialized bytes, headers and destination capacity.
All required selections pass at the recorded revision.
The three disposable wrong-expectation controls fail as intended.
No engine repair or unresolved ticket 11 execution gap remains.

## Revisions and execution identity

| Component | Exact identity |
| --- | --- |
| Source | `5551d08fcfa2dc08b3352a71e1b4568af4f72a44`, branch `task/work456-11-source`, worktree `work456-ticket11` |
| Starting source | Live integration `d13aebf6428a68c2852d16df143d1da203d86dea`. The owned verification remains at the stated source commit. |
| Public TC | `754dfffd83f7b3a14e13e8a5b965ccf4f2ae2920`, branch `task/work456-11-public`. No ticket 11 changes. |
| Private TC | `151d812bbfd2c104eb5c967f659c7e3a6fa840e8`, branch `task/work456-11-private`, based on live `216d13109`. One added shell case. |
| Build and install | Linux, 16 KiB, OptDebug, `UNIT_TEST_OOS=ON`, eight build jobs. Own build and install only. |
| Install prefix | `/home/vimkim/.cub/install/work456-ticket11/optdebug` |
| Host allocation | Master 41090, broker 41091, SHM 1644167258/1644167259, own registry and `/tmp/cwe-1000/58210fa03306` |
| Native runner | `cubrid-testkit dev`, SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`, Go revision `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`, modified build |
| CTP / JDBC | Asset commit `9c62858b10005d721546cc007be260844033b9e9`, existing edits preserved. JDBC SHA-256 `17e2e0ee4c0756b4b0a7cd679f1fea4630124f5704bc69db0c2107235190ff98` |
| Java | Temurin `8.0.462+8`, selected through the owned environment |
| Installed revision | `5551d08`, `commit_match=yes`, no mismatch exception in every native preflight |
| Immutable install manifest | 247 static installation files, SHA-256 `445cfbe889268e11db98b315fc76ee18cf12e856eb3c31452914905ec8ca4e50`. Runtime log, tmp, database and var directories are outside this manifest. Directory symlinks are outside its scope. |
| Normative specification | OOS-CONTEXT dated 2026-10-08, SHA-256 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65` |

`gh-pr-info` found no PR for the independent source branch.
The integration PR uses head repository `vimkim/cubrid`, head `CBRD-26659-oos-testcases-handover`, and base `feature/oos-merge`.
The integration's unrelated CCI changes remain untouched.
The raw evidence retains the owned CCI generated header.
The worker restored that header after verification.
The task source checkout is clean.
Its compiled header hash remains in the build manifest.

The build uses the maintained configure, build and install recipes.
The supplemental CMake option enables OOS unit tests in the owned cache.
CTest runs under the installation runtime lock with an owned registry, configuration and temporary directory.
Native SQL and shell runs use separate copied installations, CTP assets and HOME directories.
Each invocation selects its native family and containment explicitly.
No source or TC push, CI trigger, TC closure or TC merge belongs to this handoff.

The [approved specification](supplement-spec-work456-20261021.md) and [operation inventory](supplement-operation-inventory-work456-20261021.md) define this ticket's scope.
This report supplies the ticket 11 evidence for profitability, chunk, VOT, stub bounds and descriptor guards.
The physical target and other ticket 12 cells keep their separate owners.

## Independent limits and units

| Contract | Limit and tested successor | Oracle and observation |
| --- | --- | --- |
| Serialized profitability | 24 B stub, then 28 B aligned value | VARCHAR 22 characters uses a prefix, terminator and alignment for 24 B. VARCHAR 23 uses 28 B. FORCE_OUTLINE keeps the first inline and demotes the second. The schema-policy case checks complete values and current mixed REC_HOME flags. |
| VARBIT profitability | 24 B serialized, then 28 B | VARBIT 20–23 input bytes uses a one-byte prefix and reaches 24 B. Input 24 bytes reaches 28 B. Public representation checks full values and independent expected answers. There is no terminator. |
| Single chunk | 16280 serialized payload bytes, then 16281 | The C++ test stores raw binary bytes without a helper terminator. It inspects one versus two real chunks, every header, every fragment and the reconstructed value. The 16 KiB layout independently determines the capacity. |
| SQL chunk successor | 16280 serialized bytes, then 16284 | VARBIT input 16275/16276 bytes adds a five-byte prefix and rounds to four bytes. Serialized 16281 is unavailable through this SQL encoding. The shell checks exact chunks, slot bytes, complete values and individual stored flags. |
| Second chunk boundary | 32560 serialized bytes, then 32564 | Input 32555/32556 bytes crosses from two to three chunks. The independent fixture also covers the lower neighbor and a four-chunk value. |
| BYTE VOT | 127 numeric bound, 124 aligned layout, then 128 | Input 91/92 VARBIT bytes serializes to 96/100 B. Header 16, VOT 4, fixed id 4 and bound map 4 give initial layouts 124/128. Stored records select BYTE/SHORT. |
| SHORT VOT | 32767 numeric bound, 32764 aligned initial layout, then 32768 | A fixed BIT value of 32716/32720 B plus one 24 B VARCHAR produces the two candidates. Neither attribute is demotion-eligible. The wider INT VOT adds 4 B. Bigone storage expands the MVCC header separately. Tests compare header-relative VOT ends 32748/32756 and complete SQL values. |
| VOT-defined stub field | Exactly 24 B, with 20/28 B invalid aligned neighbors | Crafted BYTE/SHORT/INT records check both field bounds and one-byte record/table truncation. Parsing preserves all input bytes. These are module guard tests. |
| Parsed full length | 1 through 1073741823 B, with 0 and 1073741824 rejected | Descriptor parsing alone checks endpoints. No large allocation or full-size storage occurs. This is guard-only coverage. |
| Insert narrowing | `INT_MAX` span bound, with `INT_MAX+1` rejected | A deliberately unrealized span checks rejection before payload access. NULL and zero-length spans also reject. A real 29 B survivor still reads completely. This does not store or allocate `INT_MAX` bytes. |
| Stub writer capacity | 24 remaining bytes, with 23 rejected | The actual value cursor has 23 B while the offset-table cursor has ample space. The writer returns `S_DOESNT_FIT`, preserves cursor and canaries, then retries successfully with 24 B. Every stub field matches the independent reference. |
| Offset entry capacity | Four bytes, with three rejected | An undersized offset entry returns `S_DOESNT_FIT` before any byte changes. |

The earlier string helper stores its terminator too.
Its input size therefore differs from its serialized span size by one byte.
The new exact chunk test avoids that helper and compares complete binary vectors, including embedded zero bytes.
Existing neighboring-size tests remain useful within their original string contract.

Expand must return valid offsets, clear HAS_OOS, preserve row identity and return every value byte.
The tests do not require the expanded VOT width to equal the stored width.
They also do not invent an expanded-record normalization requirement.
The fixed BIT controls exercise supported non-OOS overflow, distinct from an OOS chunk chain.
Physical target, residual-record rejection and B-tree key-overflow qualification remain ticket 12 responsibilities.

Code evidence uses the stated source commit: `oos_file.cpp:2088` checks input lengths and `oos_file.cpp:3645` defines chunk capacity.
`heap_file.c:12757` selects VOT widths, `heap_file.c:13543` checks the actual stub cursor, and `heap_file.c:22036` expands bigone headers.
`heap_oos.cpp:441` checks inline lengths and `heap_file.c:11019` checks VOT-defined stub bounds.
The nine new test functions provide the corresponding executable assertions.

## Added module contracts

The source adds `unit_tests/oos/test_oos_boundaries.cpp`.
Its target uses GoogleTest and the existing OOS_DB CTest fixture.
One wrapper sits beside the existing unit-test bridges in `src/storage/heap_file.c`.
The existing `CUBRID_UNIT_TEST_ENABLED` condition excludes the wrapper from production builds.
The wrapper constructs one valid selected-column plan and calls the existing static writer.
It adds no production API, production control-flow change or engine repair.

| Added test in `OosBoundaries` | Contract |
| --- | --- |
| `ExactChunkCapacityAndOneByteOverStoreOneAndTwoChunks` | Actual raw serialized capacity and one-byte successor, fragment/header/chain integrity, full binary equality |
| `CallerLengthOneByteEitherSideRejectsAndPreservesStoredBytes` | Short/long read destinations reject in single/multiple chunk paths, canaries survive, stored bytes remain readable |
| `InsertLengthNarrowingGuardOnlyRejectsWithoutTouchingExistingChain` | Invalid spans reject before access and preserve a real survivor |
| `InlineLengthEndpointsAreParserGuardsOnly` | Full-length descriptor range endpoints without implied large-value storage |
| `EveryVotWidthRequiresExactlyOneStubWithinFieldAndRecord` | BYTE/SHORT/INT field width and truncated-record/table bounds |
| `StubWriterUsesValueCursorAndRetriesAtExactCapacity` | Actual value cursor, 23 B rejection, 24 B retry and complete reference identity |
| `StubWriterOffsetEntryOneByteShortChangesNothing` | Offset-table write rejection before mutation |
| `StoredVotBoundariesAndExpandedValuesPreserveMixedRows` | Actual BYTE/SHORT stored rows, mixed flags, legal Expand offsets and complete distinct values |
| `NonOosShortIntVotBoundaryPreservesCompleteValues` | Actual SHORT/INT initial layout transition, clear HAS_OOS and complete fixed/variable values |

## Retained contracts and testcase selection

All 140 ticket 11-related existing C++ cases retain their assertions and execution modes.
Their exact identities remain in the [complete C++ inventory](supplement-cpp-inventory-work456-20261021.md).
No test migrates or disappears.
The seven retained groups contain 21 `test_oos`, 33 identity-stamp, 36 server, 10 real-vacuum, 25 storage, 8 SQL-boundary and 7 byte-writer cases.
The original 302-case receipt remains at source `1ef86a7` with its original scope.
It does not count as this ticket's new cases or replace the final own-revision selection.

The retained assertions include SA and SERVER_MODE chain behavior, full-length disagreement, malformed references, bounded append, exact stub identity and chunk-neighbor behavior.
SQL equality cannot replace these internal error and mode contracts.
The original mid-size SQL C++ test checks roundtrip lengths, not actual placement.
The new shell and stored-record cases supply their own physical proof.

The new private case is `shell/_40_guava/cbrd_26659_serialized_chunks/cases/cbrd_26659_serialized_chunks.sh`.
It reuses the reviewed chunk and width SQL/JSON models from the existing representation fixture.
It executes those groups independently of the earlier physical-target group.
Each phase joins the complete modeled value predicate to one current logical row and REC_HOME flag observation.
The observer remains limited to current, unrelocated rows in an unpartitioned heap.

The selected public cases are `cbrd_26659_oos_representation.sql`, `cbrd_26659_oos_chunk_boundaries.sql` and `cbrd_26659_oos_vot_many_attributes.sql`.
Their committed answers remain unchanged.
The selected existing schema-policy shell case supplies the same-heap profitability, NULL and empty controls at the final revision.
The public JDBC invocation and each physical shell fixture retain separate evidence claims.

## Native results and verdict controls

The delivery adds nine C++ cases and one private shell case.
The public answers do not change.
Each CTest invocation creates and deletes its own fixture database.
The eight invocations contain 149 distinct required cases.
The first seven contain 139 cases, and the separate real-vacuum invocation contains 10.
These counts do not represent one process or one 149-case binary.

| Final selection | Required / actual | Verdict | Raw receipt under the ticket 11 directory |
| --- | --- | --- | --- |
| CTest, seven fixture-aware invocations | 139 /139 | 139 PASS, 0 FAIL, 0 skip, 0 missing | `final/receipt.json`, SHA-256 `1e106b5729ecd3e4f5cd5daebd8cef20e9e59f11cc87b231712682f7f8696dc2` |
| Separate real-vacuum CTest invocation | 10 /10 | 10 PASS, 0 FAIL, 0 skip, 0 missing | `final-real-vacuum/receipt.json`, SHA-256 `503a7b4c581ba58564802e76b5b14c97f5e1ff8534a71fed17e1e85f9a82a80c` |
| Native SQL / JDBC | 3 /3 | 3 PASS, 0 FAIL, 0 skip | `sql-final/verify.log`, 53.2 s |
| Native shell | 2 /2 | 2 PASS, 0 FAIL, 0 skip | `shell-final/verify.log`, 26.2 s |

The C++ reconciliation matches required identities, discovery, started cases and GoogleTest XML.
Every CTest process returns 0.
The complete retained 140-case set appears in these final receipts.
The narrow shell case executes all 13 modeled phases and 45 passing checks, including cleanup.
The schema-policy case independently executes its four-row floor fixture in one heap.

| Disposable control | Intended change | Observed detection |
| --- | --- | --- |
| C++ writer | A 23 B destination incorrectly expects `S_SUCCESS` | One selected GoogleTest case fails. CTest returns 8. No case is missing. |
| SQL answer | First expected serialized length changes from 3008 to 3009 | Exact 3-case selection gives 2 PASS/1 FAIL. Runner returns 0 and artifact verifier returns 1. |
| Shell record flag | The control inverts the first current-row HAS_OOS expectation | Exact 1-case selection gives 1 FAIL/0 skip. The flag/value assertion produces NOK, then all owned cleanup checks pass. Runner returns 0 and verifier returns 1. |

The C++ control predates the task commit and records the identical writer code under the initial dirty test development revision.
The native controls use final source `5551d08`.
All control changes stay outside committed tests and answers.
They provide no engine-failure or passing-coverage credit.

`cleanup-final.json` records no owned CUBRID process and no host fixture files.
The host registry and all four native attempt registries contain no database registration.
Positive shell artifacts show owned server exit, database deletion, directory removal and configuration restoration.
CTest receipts independently record an empty process list after every invocation.
The task preserves unrelated resources and source changes.

The first unit-disabled configure was an initialization error and never supplied test credit.
Its build stopped before the unit-enabled configuration.
The first unit-enabled build found a constness mistake in the new test, which the next build resolved.
The commit hook formatted only the new C++ file.
Its second run passed.

`green01` ran all nine cases and reported eight passes plus one incorrect test expectation.
That assertion compared initial record size with the larger MVCC header required for a bigone record.
Source inspection identified the header expansion in `heap_file.c`.
The corrected assertion compares independently modeled offsets relative to the header end.
`green02` passed all nine cases.
The final source omits an unnecessary exact Expand width assertion.
These test-development errors are not engine defects or accepted expected-output changes.

The first CPP negative attempt stopped at discovery because its declaration file still used the previous test name.
It opened no database and supplies no verdict-control credit.
The second attempt selected one writer case with a disposable wrong expectation.
It reported one GoogleTest failure and CTest exit 8.
The task commit contains the intended assertions.

## Artifact retention and handoff

Raw commands, logs, XML, manifests and receipts remain outside Git at `/home/vimkim/temp/work456-implementation/ticket11`.
The selected document and its README row preserve the useful analysis.
No generated inventory or execution log enters documentation history.

`final-summary.json` reconciles all selections and all three controls.
No required ticket 11 case is missing, skipped or under triage.
The source commit is `5551d08fcfa2dc08b3352a71e1b4568af4f72a44`.
The private TC commit is `151d812bbfd2c104eb5c967f659c7e3a6fa840e8`.
Source and TC publication remain with the final authorized handoff.
The final combined source revision still requires ticket 16 qualification.
Earlier receipts retain their original revision and do not establish passing coverage for later combined code.
Performance qualification and HA/replication Work 463 remain deferred.
The report grants no passing credit to unexecuted cases or unrelated known defects.
