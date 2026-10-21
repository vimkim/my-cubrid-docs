# Work456/05: read, relation, copy and LOB verification

Date: 2026-10-21, Asia/Seoul. Reader: the Work456 coordinator and the ticket 16 coverage reviewer. Related PRs: [engine 8128](https://github.com/CUBRID/cubrid/pull/8128), [public TC 3688](https://github.com/CUBRID/cubrid-testcases/pull/3688), [private TC 4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365).

This report answers whether the ticket 05 read and copy operations preserve complete values and relational semantics across actual stored C/S records. `C` means HAS_OOS clear. `S` means HAS_OOS set. The new native SQL case passed all relation and transfer assertions. Three native shell cases also passed their value and physical assertions. The retained eight-case C++ CRUD target passed separately in SA mode. The tables below record final committed-input and negative-control receipts.

This work adds tests and record-level linkage. It changes no engine implementation and removes no C++ assertion. The operation assignments come from the [83-operation inventory](supplement-operation-inventory-work456-20261021.md). The [ticket 01 receipt](ticket01-baseline-and-observer-20261021.md) defines the shared record observer and its limits.

## Exact revisions and configuration

| Component | Identity and limits |
| --- | --- |
| Source | `CUBRID/cubrid` commit `1ef86a7efa34002e971b1b30bcf5d451e9db441b`, own branch `task/work456-05-source`. No source edits or new source commit. |
| Public TC | Base `df8596dd999e825b1ec9812a735bbe01e50ac715`, new commit `2033d98a0587764b7d1abbc4d9114053638980a9` on `task/work456-05-public`. One new SQL/answer pair. |
| Private TC | Base `5e8a9eaa885a53922826ff5320787f1115034a13`, new commit `83524eea20ed438ffef3e2d7932ca4d8c9a8500f` on `task/work456-05-private`. Four modified files across three existing shell cases. |
| Product installation | Copy of the immutable ticket 01 Linux, 16 KiB, OptDebug installation. Own prefix `/home/vimkim/.cub/install/work456-ticket05/optdebug`. Each attempt copies this prefix again. Preflight reports installed commit `1ef86a7`, `commit_match=yes`, and no mismatch exception. This task reuses the matching build. |
| Dependencies | CTP `9c62858b10005d721546cc007be260844033b9e9`, with its pre-existing tracked dirt preserved. CCI build dependency remains the ticket 01 gitlink/header receipt. JDK Temurin `8.0.462+8`. JDBC driver SHA-256 `17e2e0ee4c0756b4b0a7cd679f1fea4630124f5704bc69db0c2107235190ff98`. |
| Native runner | `cubrid-testkit dev`, binary SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`. The version label alone is insufficient. |
| Normative OOS context | Complete read of the 2026-10-08 context. SHA-256 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`, unchanged across the read. ADR-0002 separates locator demotion from external LOB storage. |
| Manual | `cubrid-manual` commit `3b6ae97bfbdc664b010ffa933ded5a05b291ae03`. `en/sql/function/stmt_set_op.rst:12` documents the three operators and ALL variants. `en/sql/query/select.rst:80` defines SELECT INTO variables. `en/sql/function/typecast_fn.rst:43` documents BIT/string casts. |

The source validator found no own build directory or compile database. These tests use the exact matching copied installation and do not use LSP or a local rebuild. The separate C++ run uses ticket 14's owned `UNIT_TEST_OOS=ON` build and installation.

The coordinator granted native slot B before initialization or execution. `cub-workenv init --no-db` allocated master port 41078, broker port 41079, SHM IDs 1644167246/1644167247 and TMP `/tmp/cwe-1000/652b87311670`. Initialization creates no host database. Each native attempt has its own installation, empty registry, HOME, TMP, CTP, configuration and result tree. The explicit native family uses serial slot containment. The native slot supplies its own network, PID, IPC and mount namespaces.

SQL copies only the selected cases and answers. It uses the SQL runner's HA configuration, its own allocated port/SHM settings and the copied driver. Broker SHM values use hexadecimal configuration syntax. The copied `System.xml` names the attempt-local driver. Shell uses `scenario_disk=on`, exact file selection, no retry or continuation, and read-only source with a disposable write layer. Its ordinary CS/LOB/JDBC configurations remain distinct from native SQL. All configuration and driver changes affect attempt copies only.

The source installation omits the separately built JDBC distribution. The shell JDBC case therefore accepts the copied CTP driver when the installed driver is absent. It records the selected jar hash. This is an explicit dependency selection, not a claim that the driver was built from engine `1ef86a7`.

## Independent intended oracle

The new public case is `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_read_relations.sql`. The preparation model defines its answer before execution. The external preparation model remains in raw `write_relations.py` and `relation-oracle.json`. The testcase runner uses neither file.

| Logical input | Complete value and purpose | Actual default state |
| --- | --- | --- |
| id 1, A | 99 bytes `19`, then `ab`, total 100 bytes | C |
| id 2, B | 1701 bytes `a1`, 1703 bytes `b2`, 1703 bytes `c3`, total 5107 bytes | S |
| id 3, C | Same as B except final byte `c4`, also 5107 bytes | S |
| id 4, B | Exact duplicate of id 2's full value | S |
| id 5, N | NULL | C |
| id 6, E | Empty VARBIT | C |

Every relation output classifies the complete payload by equality against these input values. Unknown or corrupted values become `BAD`. Prefixes, lengths, row counts and digests cannot substitute for that equality. The answer contains exact ordered row identities, full-value classes and multiplicities.

The left multiset is `{A:1, B:2, C:1, E:1, N:1}`. The right relation selects ids 2, 3, 5 and 6, giving `{B:1, C:1, E:1, N:1}`. Their independently intended results are:

| Operator | Exact output multiplicity |
| --- | --- |
| UNION | A1 B1 C1 E1 N1 |
| UNION ALL | A1 B3 C2 E2 N2 |
| INTERSECTION | B1 C1 E1 N1 |
| INTERSECTION ALL | B1 C1 E1 N1 |
| DIFFERENCE | A1 |
| DIFFERENCE ALL | A1 B1 |

The same-length B/C distinction makes tail comparison observable. The duplicated B rows expose duplicate elimination and ALL multiplicity. NULL and empty remain separate classes. Full-payload descending order with an id tie-breaker and LIMIT returns `(3,C),(2,B),(4,B),(1,A)`. Full-value grouping produces B multiplicity 2 and four singleton groups. MIN/MAX, DISTINCT aggregates, joins, an outer join, correlation and CTE results have independently enumerated answers.

## Record-state and transfer proof

The new SQL case includes `SELECT_RECORD_INFO` in its actual native JDBC execution. Each relevant diagnostic compares complete values beside `t_rectype` and the HAS_OOS bit. Expected type 2 means `REC_HOME`. No companion case supplies placement for this public invocation.

| Fixture or operation | Required state/model proof |
| --- | --- |
| Mixed default source and its plain copy | C for A/N/E, S for B/C/B in each heap. Every diagnostic also checks the complete id/value model. |
| FORCE_OUTLINE source | S for all four profitable nonempty values, C for NULL/empty. A's identical 100-byte value can therefore start in either C or S. |
| Four INSERT SELECT destinations | A crosses C→C, C→S, S→C and S→S through DEFAULT and FORCE_OUTLINE destinations. The case checks every other full value and relevant state too. |
| Large fixed/variable transfers | Identical 5107-byte B/C values transfer from variable S into fixed `BIT(40856)` C, then from fixed C into variable S or fixed C. The fixed column has no variable candidate. It remains a valid ordinary `REC_HOME` record. |
| CTAS | Exact six-row model and default C/S destination records, then the same values and flags after source DELETE/DROP. |
| Self-copy | Six source rows produce exactly six new ids. Both sets have complete value/flag assertions. Deleting original ids leaves exact ids 11–16 with the expected stored flags. |
| Rejected transfers | NULL primary-key transfers from the C and S source classes reject with ordinary error `-631`. The complete destination and source models remain intact. |
| Copy rollback | The writer observes its six-row S/C destination before rollback. Rollback leaves no logical destination rows. The source's complete values and physical model remain intact. Absence receives no C credit. |
| VARCHAR/NCHAR VARYING expressions | Independently known complete strings, CAST/COALESCE and concatenation outputs. The case directly observes both profitable forced and short clear record controls. |

The five ordinary copy destinations and both fixed-derived copies retain their complete models after source destruction. The case asserts their surviving stored states. Large variable values cannot be forced clear with a nonexistent FORCE_INLINE policy. The fixed-domain fixture supplies the supported clear layout instead. NULL/empty cannot form a profitable stub larger than 24 bytes. Those cells are inapplicable to forced demotion, with a concrete domain/serialization reason.

SELECT INTO binds query values to variables in the documented grammar. It is not a second stored-table materialization interface. CTAS supplies the supported stored-table contract here. Query intermediates and relation outputs have no HAS_OOS state.

Physical classification covers only current, unrelocated `REC_HOME` records. Fresh fixtures avoid old-version ambiguity. The self-copy post-delete diagnostic selects new survivor ids that were never updated or deleted. Original deleted ids are outside that explicit relation. No deleted physical slot becomes a clear-state control. This report makes no old-version, forwarding, relocation, partition-owner, per-attribute-stub or chain-identity claim.

## Actual shell invocations and LOB boundaries

The three retained entrypoints are under `shell/_40_guava/`. The cases print their new diagnostic JSON into the native test log.

| Case | Actual invocation and retained contract |
| --- | --- |
| `cbrd_26659_read_paths` | CS CSQL source, inline control and CTAS copy each receive full payload/tag equality and record/type/slot/flag checks. Source and copy have C/S mixed records. Existing heap/PK/multicolumn plans, eleven ordered relation checks, source DROP, surviving copy, file ownership and checkdb assertions remain. |
| `cbrd_26659_jdbc_storage` | The same JDBC connection writes with `PreparedStatement.setBytes`, compares every returned byte with independent input arrays and emits actual record diagnostics before source DROP. Its copy receives the same diagnostics before and after DROP. The shell parser requires exact row/slot identities, type, full-value success and flags. This is not a CSQL companion fixture. Existing ordinary-reader, OOS owner and checkdb assertions remain. |
| `cbrd_26659_lob_locators` | Actual seed C, FORCE_OUTLINE locator S and copied locator S records bind full BLOB/CLOB values to stored flags. The case checks copy S again after source destruction. Only the two locator attributes can demote in this fixture. Existing two-chunk/serialized-locator-size and heap ownership assertions remain. |

The independent artifact audit parsed all 11 shell physical snapshots, containing 29 record observations. Every record has type 2, exact value success and no delete mark. The JDBC, CSQL and LOB copies retain their logical identities, slots and HAS_OOS states across source removal. Lower MVCC flag bits can change: for example, flags 9 become 8 while HAS_OOS stays set.

The LOB payload oracle uses independent files and complete SQL equality. The BLOB is 17 repetitions of bytes `01 02 03 a1`. The CLOB is literal `OOS09-CLOB-A-head-middle-tail`. The shell fixture records separate seed/source/copy external paths and compares all external bytes. It removes only its saved source/input files and proves the copied external files and SQL values survive. The case separately checks source OOS file removal and destination ownership.

Deleting OOS locator bytes does not establish external LOB deletion. SQL DELETE/DROP may or may not remove the source files in this scenario. The fixture records that disposition and explicitly destroys remaining owned sources. This report gives no general external-file garbage-collection, backup/restore or vacuum credit.

## Native case reconciliation

Raw evidence root: `/home/vimkim/temp/work456-implementation/ticket05/`. Each attempt retains preflight, effective config, expected list, input hashes, environment, command, timing, process status and native verdict artifacts.

| Attempt | Exact verdict | Meaning |
| --- | --- | --- |
| `red-jdbc01` | 1 FAIL, 0 skip | TDD red. Existing JDBC values passed, but the required actual JDBC record receipt was absent. Runner exit 0 did not hide NOK. |
| `green-shell01` | 3 PASS, 0 fail/skip | First complete same-invocation JDBC/read/LOB record linkage. |
| `green-sql01` | 1 FAIL, 0 skip | Answer formatting error: expected uppercase `NULL`, while the native JDBC renderer writes lowercase `null`. The independently intended null relation and all other expected rows matched. Corrected presentation only. |
| `final-sql01` | 5 PASS, 0 fail/skip | New relation case and four retained SQL cases. |
| `final-sql02` | 5 PASS, 0 fail/skip | Final SQL inputs add post-source-removal physical assertions for fixed-derived copies and self-copy survivors. |
| `final-shell01` | 3 PASS, 0 fail/skip | Committed private inputs, including printed record and external-file JSON. |
| `negative-tail01` | 1 FAIL, 0 skip, as intended | Disposable answer expects B for id 3. Actual full-value class C differs only at the tail. Native verifier rejects despite runner exit 0. |

The five SQL cases are the new `cbrd_26659_oos_read_relations` and retained `cbrd_26659_oos_sql01_insert_select`, `cbrd_26659_oos_sql07_read_paths`, `cbrd_26659_oos_sql09_lob_copy`, and `cbrd_26659_oos_sql09_lob_maxcols`. Each has its matching answer. Existing logical SQL cases retain their own scope. Their separate shell fixtures do not supply missing per-record observations for those public invocations.

The maintained verifier requires exact positive dispatch/finish identities and passing status, feedback, XML and result artifacts. Shell process status and runner exit alone are insufficient. SQL result roots come from each invocation's `Result Root Dir:` line. The independent audit checks final input hashes against committed TC bytes. The explicit native family runs each selected case.

The independent audit checked all 20 shell input files and 10 SQL/answer files against their committed bytes. Final effective config SHA-256 values are shell `ed6daa8278f3a5d6cff40188b5aa8066547cfe2da519a2b54be2fa612806eb4b` and SQL `789d488d0fa6129d133c0234276581eb28475bb5e65db199c66c12682ccb6405`.

Final shell runner time is 46.806 s. Final SQL runner time is 56.184 s, with 2.404 s reported for case execution. These are operational timings without a performance verdict. The wrong-tail control differs from its result in exactly one expected output cell, line 74: expected `(3,B)`, actual `(3,C)`. Committed expectations remain unchanged.

All seven attempt registries are empty after cleanup. Every final shell case reports owned server absence, database deletion, registry absence and configuration restoration. The owned-process audit finds no remaining executable or CUBRID environment under ticket 05's prefixes. The read-only doctor reports the own environment ready. It also reports inaccessible foreign PIDs, so this is not global-host inactivity evidence. The coordinator accepted release of native slot B. Raw `independent-artifact-audit.json`, `physical-snapshots.json`, `cleanup-audit.json` and `doctor-after.log` preserve these checks.

## C++ dispositions and separate SA execution

All eight cases in `test_oos_sql_crud` remain **retain**. Add/migrate/remove counts are zero for C++. External full-value tests augment their assertions and do not establish redundant execution modes.

| Case suffix under `OosSqlCrud` | Original assertion retained | New external complement |
| --- | --- | --- |
| `BasicInsertSelect` | SQL insert/select success and expected length | Complete values, mixed C/S and copy survival |
| `SmallRecordNoOos` | Small-record SQL success and expected length | Actual C record control |
| `MultipleOosColumns` | Three projected lengths | Complete multi-column bytes in retained read/JDBC cases |
| `Cbrd27006MultiOosColumnSelectsAndUpdate` | Projected and post-UPDATE lengths | Read/copy full values. UPDATE transitions remain ticket 06. |
| `Cbrd27006MixedSingleChunkAndMultiChunkRow` | Single/multichunk projected lengths | Existing full-value read and JDBC region arrays |
| `Cbrd27006ReadDispatchBatchesOnlyMultiOosProjections` | Non-OOS and single-OOS `read_many_calls=0`. Multi-OOS calls=1, requests=2, grouped head pages=1. | No replacement. Equal SQL answers cannot prove these counters. |
| `MultiChunkOos` | Multichunk SQL success and expected length | Complete multi-region values |
| `MixedChunkSizes` | Count and projected lengths | Exact identities and complete mixed-row values |

Ticket 14 executed the unchanged target at source `1ef86a7`, OptDebug with `UNIT_TEST_OOS=ON`, linked to `cubridsa`. All eight discovered cases started and passed their GTest XML assertions. There were zero missing, disabled or skipped cases. CTest and its setup/cleanup fixtures passed. This report independently parsed the XML and froze the selected identity/result excerpt in raw `shared-crud-receipt.json`.

Central artifacts are under `/home/vimkim/temp/work456-implementation/ticket14/baseline/test_oos_sql_crud/`. GTest XML SHA-256 is `e9373104c2a41e2efa33e8d0e623f011ca6fcce7c072086c051f7d497ff2e87e`. The exact executable hash is `c13c3e600ff04742aa82fc6e83dfd7ec426826bbc5663aef8935150ce10e7793`. The central receipt also identifies configuration/install hashes. This separate SA run does not replace the CS/native SQL or JDBC receipts. Internal Expand, dispatch and buffer-lifetime additions remain ticket 14's responsibility.

## Coverage handoff and limits

| Inventory operation | Ticket 05 disposition |
| --- | --- |
| O14–O18 | Heap/index/projection/existence, predicates, joins, correlation, CTE, ordering/LIMIT, grouping, aggregates and DISTINCT executed with full-value models and actual C/S fixtures. Internal cheap-fetch assertions remain under ticket 14. |
| O19–O20 | All six supported set forms executed over full payloads with exact multiplicity and NULL/empty semantics. |
| O21–O22 | Supported CAST/expressions and VARBIT/string/national-string values executed. Actual JDBC prepared bytes, getBytes results and physical source/copy linkage executed. Boundary obligations stay with ticket 11. |
| O26–O27 | Multirow INSERT SELECT, self-copy and CTAS executed. Actual destination flags, error/rollback preservation and post-source-removal survivors checked. Other schema rewrite obligations stay with ticket 08. |
| O63 | Actual locator record states, complete external values, independent copied files and source destruction executed. Utility roundtrips remain ticket 04. Internal retry/bounds assertions remain ticket 14. |
| O81 | Retained CRUD dispatch target executed separately in SA mode. No assertion removed. |

No reproducible engine failure occurred in these tested contracts. The first NOK detects the deliberately missing JDBC receipt. The second detects an answer-formatting error. Both retain their artifacts and receive no PASS credit. Final negative-control and cleanup reconciliation passed. No missing or unexecuted required ticket 05 case remains. This report grants no whole-corpus, HA, performance, vacuum/reclaim, partition or competing-source integration qualification.

Local task commits only. No source/TC push, integration merge, CI trigger, TC PR action or JIRA change occurred. The coordinator owns ticket/map status and subsequent integration. The task preserves all unrelated CCI/CTP dirt and foreign resources.
