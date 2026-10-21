# Work456/10: ordinary FK actions and actual OOS-backed FK keys

Date: 2026-10-21, Asia/Seoul. Scope: Work458/459 and CBRD-26659 PR8128.
Reader: testcase and engine reviewers.

All 28 required shell cases and 676 phases pass at source `5551d08`.
The independent native SQL case passes. All 3 wrong-expectation controls produce the required failures.
Ticket 10 establishes no engine defect or required execution/oracle gap. It changes no engine source.

## Contract and fixtures

The normative OOS specification defines per-attribute value chains and record flags.
The local manual defines same-type PK/FK references and supported actions.
Its DELETE actions are CASCADE, RESTRICT, NO ACTION, and SET NULL.
Its UPDATE actions are RESTRICT, NO ACTION, and SET NULL.
Default actions are RESTRICT. UPDATE CASCADE has no grammar production.

The ticket09 reference has two distinct 5,107-byte VARBIT values.
They share 5,106 bytes and differ at their final byte.
Each actual-key row contains only fixed INT attributes and one variable key.
An observed HAS_OOS flag therefore identifies the indexed key's stored representation.
Ordinary INT-key fixtures use an independently checked variable payload instead.
Their OOS payload observations receive no actual-key coverage credit.

Twenty-four independent shell cases cover both kinds, single/composite keys,
and six action declarations. Four additional cases exercise a rejected downstream cascade.
Each case uses an owned database and cleanup audit.
The native SQL case separately verifies logical JDBC behavior and FK build rejection.
A populated FK build must reject a missing parent and preserve both complete rows.
After correcting that key, the same FK build must succeed.
Its invocation receives no physical credit from any shell invocation.

Each model includes every surviving ID, note, tenant, key, and applicable payload.
The model requires exact cardinality and full-value equality.
A NOT EXISTS query also checks all complete foreign-key relationships.
Physical diagnostics select named surviving rows without a flag/MVCC filter.
Expected-error INSERT markers do not qualify as visible rows.
DELETE absence receives no HAS_OOS-clear credit.

Normal SQL reads visible versions. SELECT_RECORD_INFO reads current physical slots.
During an acknowledged writer, those observations use separate complete models.
After rollback and commit, both observations must again match the required model.

SHOW establishes each heap's associated OOS VFID.
Stopped diagdb joins that VFID with the heap and class owner.
The observer disables SA startup vacuum before boot and verifies its effective parameter.
It restores the exact configuration before the next CS server starts.
Parent, child, and applicable grandchild VFIDs must differ.
The failed downstream cascade must preserve every row and each heap's stored chunk-record count and bytes.
Its grandchild FK uses fixed INT child IDs. Its separate OOS attribute is payload.
Only the parent/child keys receive actual large-key FK coverage credit.
The documented outer cascade error is -926 and names the outer fk_ref constraint.
It does not expose the downstream restriction's message identity.
The B-tree overflow-key file is a separate observation and receives no heap-flag credit.

## Required execution

| Selection | Required | Actual verdict |
| --- | ---: | --- |
| Shell fixture/action combinations | 28 | 28 PASS, 0 fail/skip |
| Declared shell phases | 676 | 676 completed exactly once |
| Native SQL files | 1 | 1 PASS |
| Effective wrong-value and wrong-flag controls | 2 | Each produces exactly 1 native NOK |
| Effective wrong-SQL-answer control | 1 | Exactly 1 native NOK |

## Retained C++ assertions

Ticket 10 retains every existing C++ case. It adds no C++ case.
The fixed inventory assigns no dedicated FK C++ case to this ticket.
Eight related OosSqlTxn assertions remain unchanged at `5551d08`.
Their original `1ef86a7` fixture-aware receipt reconciles registration, expected IDs,
discovery, actual starts, and passing GTest XML for all 8.
That receipt proves SA transaction assertions at `1ef86a7`.
It does not establish ticket10 CS, FK, or `5551d08` execution.

The source registration is `unit_tests/oos/sql/CMakeLists.txt:43`.
Its `OOS_DB` fixture and serial execution remain part of the original receipt.
The source bytes and all 8 expected/discovered/started/XML IDs match the retained audit.

| Retained ID | Actual assertion contract |
| --- | --- |
| `OosSqlTxn.RollbackInsert` | Count 1 within transaction, then count 0 after abort. |
| `OosSqlTxn.RollbackUpdate` | Length 4096 within update, restored 2048 after abort. |
| `OosSqlTxn.CommittedDataPersists` | Count 2 and expected LENGTH results 4096/8192 after commit. |
| `OosSqlTxn.RollbackMultiChunk` | Count 1 after repeated-value insert, then count 0 after abort. |
| `OosSqlTxn.ComboThenCommit` | IUD survivors count 2 and expected lengths 2048/8192. |
| `OosSqlTxn.RollbackDelete` | Count 0 within delete, restored count 1 and length 2048 after abort. |
| `OosSqlTxn.DeleteCommit` | Committed delete leaves count 0. |
| `OosSqlTxn.DeleteRollback` | Abort restores length 4096. |

No verified equivalent replacement exists for deleting these SA assertions.
The new CS FK checks therefore supplement them.

## Limits

This report excludes HA, replication, failover, performance, and vacuum eligibility qualification.
Ticket 10 changes no production behavior or API. Its intended answers preserve correct failures.
Missing, skipped, unclear, and unexecuted required tests block ticket10 completion.

## Independent error and support evidence

The local manual is `CUBRID/cubrid-manual@3b6ae97bfbdc664b010ffa933ded5a05b291ae03`.
Its `en/sql/schema/table_stmt.rst:607–710` defines ordinary FK relationships and actions.
Its `en/admin/error_log_sql.rst:1205–1209` documents error -926.
At source `5551d08`, `src/transaction/locator_sr.c:4470–4493` maps a failed nested
CASCADE deletion to that outer error in `locator_check_primary_key_delete`.
`src/base/error_code.h:1160` identifies `ER_FK_CANT_DELETE_INSTANCE` as -926.

The committed generic TC baseline is `df8596dd999e825b1ec9812a735bbe01e50ac715`.
Its `_01_object/_08_primary_foreign_key/_004_rule/answers/1011.answer`
requires grammar error -493 for UPDATE CASCADE.
The `_003_manipulation` answers establish -922 missing-parent and -924 restricted-parent errors.
Ticket 09's committed duplicate-key oracle supplies -670 for direct duplicate DML.

| Combination | Contract and proof |
| --- | --- |
| Same-type INT FK with OOS payload | Executed logical and per-row payload-state proof. No OOS-key credit. |
| Same-type 5,107-byte VARBIT parent/child keys | Actual key is the only eligible attribute. Stored flags and named PK/FK plans prove the path. |
| Single/composite keys | Composite queries constrain the leading tenant and complete key. |
| Duplicate child keys | Distinct child rows may reference the same parent. |
| Duplicate parent keys | Direct duplicate insertion/update rejects and preserves both models. |
| NULL foreign keys | Single NULL and composite partial/all-NULL controls remain accepted and correctly represented. |
| UPDATE CASCADE | Unsupported syntax, independently specified -493 and no table publication. |
| Other key-domain/collation matrices | No FK claim. Ticket 09 retains its separate PK/UNIQUE matrix. |

These owner observations establish file association and survivor values.
SHOW counts stored chunk records, including any retained MVCC versions.
Those counts do not identify which transaction can reclaim an individual chain.
They do not establish full 24-byte stub identity or vacuum reclamation eligibility.
Ticket 15 retains those distinct internal contracts.

## Attempt history

The raw root is `/home/vimkim/temp/work456-implementation/ticket10`.
Each attempt retains its install/CTP/HOME/registry/configuration and exact input hashes.
Each final native shell case records a network/PID/IPC/mount namespace identity.
The controller compares each namespace with the host before database creation.
The independent audit repeats that comparison from the retained receipts.
Qualified attempts record the JVM release, libjvm, PL socket length, and allocated ports.

| Attempt | Outcome and retained limitation |
| --- | --- |
| tracer01 | Harness NOK. Physical newest-slot observation incorrectly used the visible old-reader model. |
| tracer02 | Harness NOK. A second persistent session reused a retained bootstrap filename. |
| tracer03 | Complete single-key cascade PASS, 26/26 phases. |
| final01 | 12 single cases PASS.12 composite cases stopped at a lookup lacking its leading tenant equality.624 required/342 reached. |
| tracer04 | Composite positive PASS. New downstream case expected the underlying error instead of documented outer -926. |
| tracer05 | Both prerequisite cases PASS, 40/40 phases. |
| final02 | 28/28 PASS,676/676 phases,508.516 s. This is the complete frozen shell qualification. |

Earlier partial phases never become completed-case credit.
The final audit reconciles each expected/discovered/dispatched/started/finished/XML identity.
It also checks 676 declared phases, complete logical models, record flags, and physical owners.
Discovery uses native dispatch_tc_ALL after fetch.
Actual starts use each case's initial journal, model metadata, physical SQL, and separate archive.


## Exact execution and delivery identities

The initial profile is Linux, 16 KiB I/O pages, optdebug, UTF-8, and one native slot.
Native shell and JDBC SQL claims remain separate.

| Input | Pinned identity |
| --- | --- |
| Engine used by every new native invocation | `5551d08fcfa2dc08b3352a71e1b4568af4f72a44` |
| Tested private TC | `6891a0f5b71f482565c77f90f3460eafb2c97778` |
| Tested public TC | `d4d0443fd29d3dce711013bfd40d10a617453811` |
| Product provider | Read-only ticket11 optdebug copy, 247 checked manifest entries |
| Provider manifest SHA-256 | `445cfbe889268e11db98b315fc76ee18cf12e856eb3c31452914905ec8ca4e50` |
| Native testkit executable SHA-256 | `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a` |
| CTP asset checkout | `9c62858b10005d721546cc007be260844033b9e9`, copied with recorded local deltas |
| JVM for PL and JDBC | Temurin 8.0.462+8, explicit CUBRID_JAVA_HOME with release/libjvm hashes |
| Host allocation | Master 41098, broker 41099, distinct allocated SHM IDs |
| Required shell schedule | 28 independently named cases,676 phases, 84 named positive index plans |
| Actual physical observations | 672 observations, 3,098 qualified stored rows |
| Rejected/rollback owner comparisons | 156 class/heap/OOS identity and stored chunk-record count/byte comparisons |
| Native SQL | 1 case, 56.922 s, committed answer and actual result byte-identical |
| SQL error blocks | 13 × -922, 4 × -670, 2 × -924, 1 × -493, all independently specified |
| Wrong flag / wrong tail / wrong SQL controls | Each 1 NOK/0 skip,9.431 s / 14.272 s / 60.171 s |

Each attempt has a copied installation and CTP, owned HOME/config/TMP and empty registry.
Each final case proves distinct network, PID, IPC, and mount namespaces.
The computed shell PL socket paths remain below 108 bytes. No shared provider receives writes.
Every final and control attempt ends with no owned process or registry entry.

The handoff source tree now includes `9c21a1ae701c847803690bd1c567b74f0d0918a9`.
Its incoming difference from 5551 is ticket 15 C++ tests and registration only.
The native execution claims remain 5551. They do not become a 9c runtime claim.
The private delivery commit is `cc2b035c589f46bbc6a560a420412560a89df744`.
The public delivery commit is `136a9bd3597714d2a1a4e9431e73dcaca1f5e747`.
Both include their latest local integration tips, with tested selected input bytes unchanged.

| Audit | Evidence |
| --- | --- |
| [Shell qualification](https://dev2.baboon-rudd.ts.net:8443/home/vimkim/temp/work456-implementation/ticket10/final02/independent-audit.json) | Exact 28 cases/676 phases, stored rows, flags, plans and owner comparisons |
| [SQL qualification](https://dev2.baboon-rudd.ts.net:8443/home/vimkim/temp/work456-implementation/ticket10/sql01/independent-audit.json) | Native 1/1, exact answer/result SHA and 20 intended errors |
| [Wrong-flag control](https://dev2.baboon-rudd.ts.net:8443/home/vimkim/temp/work456-implementation/ticket10/negative-flag01/independent-control-audit.json) | Actual record checker rejects false HAS_OOS expectation |
| [Wrong-tail control](https://dev2.baboon-rudd.ts.net:8443/home/vimkim/temp/work456-implementation/ticket10/negative-tail01/independent-control-audit.json) | Actual full-value checker rejects one changed tail byte |
| [Wrong-SQL-answer control](https://dev2.baboon-rudd.ts.net:8443/home/vimkim/temp/work456-implementation/ticket10/negative-sql01/independent-control-audit.json) | Native mismatch while actual bytes still equal the committed good answer |
| [Retained C++ audit](https://dev2.baboon-rudd.ts.net:8443/home/vimkim/temp/work456-implementation/ticket10/cpp-retained-audit.json) | Original SA 8 expected/discovered/started/XML agreement and unchanged assertions |
| [Post-merge input audit](https://dev2.baboon-rudd.ts.net:8443/home/vimkim/temp/work456-implementation/ticket10/postmerge-input-audit.json) | Selected TC/helper/answer bytes still equal qualified inputs |

## Reproduction and handoff

Run the selected cases through maintained native SQL/shell runners under containment.
Use one slot, immutable copied cases, no retry, and an empty owned registry.
Keep each prior attempt and compare the exact verdict artifacts.
The source test build and host allocation are independent from the testcase verdict.

Source/TC push, CI, TC merge/closure, and remote JIRA writes remain deferred to the coordinator.
The original integration checkout's unrelated cubrid-cci header dirt remains preserved.

Related evidence: [ticket09 reference keys](ticket09-large-indexed-oos-keys-20261021.md),
[ticket01 physical observer](ticket01-baseline-and-observer-20261021.md),
[ticket14 retained baseline](ticket14-cpp-read-expand-buffer-20261021.md), and
[ticket 15 ownership contracts](ticket15-identity-ownership-rollback-reclaim-20261021.md).
The normative OOS specification is [c6fc51b](https://github.com/vimkim/cubrid-oos-context/blob/c6fc51bc0e27032c9c4fb999ce3e0342b20d2349/OOS-CONTEXT.md),
SHA-256 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`.
