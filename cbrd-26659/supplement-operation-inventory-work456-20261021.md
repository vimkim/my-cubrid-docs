# Work456/01: operation population and record-state obligations

Date: 2026-10-21, Asia/Seoul. Reader: the implementers of approved local tickets 02–16 and the Work458 reviewer.

This inventory assigns every operation family accepted by the Work456 specification. It extends Work109 and Work401 without replacing their historical receipts. It records **required cells**, existing assertion families and remaining owners. Except for the two observer rows, these are **not fresh passing claims**. A source-supported SQL feature can still have an OOS implementation or observation gap.

The engine is `1ef86a7efa34002e971b1b30bcf5d451e9db441b`. Public TC is `df8596dd999e825b1ec9812a735bbe01e50ac715`. Private baseline is `5c9d8de1a916ae0acbddc8409770b51fd31da13b`. The new observer is private commit `5e8a9eaa885a53922826ff5320787f1115034a13`. See the [baseline and runtime receipt](ticket01-baseline-and-observer-20261021.md) and [302-case C++ dispositions](supplement-cpp-inventory-work456-20261021.md).

Ticket 07 now has a separate [executed alternative-write receipt](ticket07-alternative-write-paths-20261021.md) for O35–O37 and its O78 share: SQL 3 PASS, ordinary/indexed shell 8 PASS, unassigned-stub shell 2 correct FAIL linked to CBRD-27230. This does not rewrite the baseline observations below.

## State and support rules

`C` means a stored record without HAS_OOS. `S` means a stored record with HAS_OOS. Each assertion must observe the actual input/output record. Policy, value length, a different fixture and aggregate SHOW statistics cannot supply that observation. Size remains relevant only to a size-dependent boundary.

| State obligation | Required cells and inapplicable cells |
| --- | --- |
| R: read/diagnose/index build | Inputs C and S, including mixed records in one heap. Output is a logical value/relation, with no stored flag unless materialized. A read has no stored-state transition. |
| I: insert | No input record: ∅→C and ∅→S. Input C/S is inapplicable to INSERT VALUES. Existing source rows in INSERT SELECT use X. |
| U: update/rewrite | C→C, C→S, S→C and S→S where assignment/policy permits them. Observe pre/post states. Accepted unassigned-chain reuse can retain S below the ordinary gate. Rejected writes use E. |
| D: delete/drop/truncate | C→absent and S→absent logically. MVCC may retain physical deleted records for readers/vacuum. Neither absence nor a delete mark is C. |
| X: copy/materialize/load | Source C/S independently crossed with destination C/S where target policy/layout permits it. Source state need not equal destination state. Nonstored intermediate query results have no HAS_OOS state. |
| E: rejection/rollback | Applicable C/S pre-images remain exact, or rejected new row remains absent. Check full values, metadata, membership and relevant ownership. An error itself has no record flag. |
| N: metadata/runner | No per-record input/output when the heap is empty or operation changes only metadata. Inspect populated dependent operations through their R/U/X rows. |

A genuinely impossible combination needs the support/domain/policy reason in the owning ticket. Do not label a missing implementation, unavailable observer or unexecuted case inapplicable. Large-key prefix/collation/FK support must be established for the selected domain before creating its oracle. HA/performance are deferred by the approved scope, not unsupported.

The accepted OOS specification supplies demotion, Resolve/Expand, ownership, identity, MVCC, reclaim and lifecycle oracles. Accepted policy decisions supplement its omitted FORCE_OUTLINE details. Ordinary SQL operation support is visible in the pinned parser grammar, SQL execution paths and corresponding generic corpus. The dedicated fixtures below establish current assertions, not automatic OOS support for every variant.

Source support anchors: [SQL grammar](https://github.com/CUBRID/cubrid/blob/1ef86a7efa34002e971b1b30bcf5d451e9db441b/src/parser/csql_grammar.y), [heap layout/write/record diagnostics](https://github.com/CUBRID/cubrid/blob/1ef86a7efa34002e971b1b30bcf5d451e9db441b/src/storage/heap_file.c), [B-tree representation](https://github.com/CUBRID/cubrid/blob/1ef86a7efa34002e971b1b30bcf5d451e9db441b/src/storage/btree_load.h), and the [earlier normative/source analysis](ci-replan/spec-and-unit-inventory.md).

## Operations, independent oracles and assigned gaps

Evidence abbreviations: `P:name` expands to public `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_<name>.sql`. `S:name` expands to private `shell/_40_guava/cbrd_26659_<name>/cases/cbrd_26659_<name>.sh`. `C:name` names the C++ module in the complete inventory. A historical PASS remains limited to its original source/TC/configuration. Every owner must strengthen/reuse the cited assertions and obtain required flag/visibility evidence for its own invocation.

### Policy and diagnostics

| ID / operation | States | Independent intended result | Existing assertions / remaining obligation | Tickets |
| --- | --- | --- | --- | --- |
| O01 CREATE policies/default/omission | N | Accepted policy metadata, eligible domains and initial defaults | P:storage_policy; S:schema_policy; C:storage | 02 |
| O02 PREFER_INLINE priority and necessary fallback | I,U | Ordinary candidates demote before preferred candidates, then largest first | P:storage_policy,representation; S:schema_policy | 02,11 |
| O03 FORCE_OUTLINE profitable/NULL/empty placement | I,U | Accepted policy bypasses record gate but obeys serialized profitability; exact values survive | P:storage_policy; C:storage | 02,11 |
| O04 ALTER policy/reset/nonretroactive behavior | U | Metadata changes immediately; existing row representation changes only on rewrite | P:storage_policy; S:schema_policy | 02 |
| O05 CREATE LIKE and copied policy/defaults | N,X | Copied metadata follows accepted policy; copied values remain exact | P:storage_policy; C:storage | 02,04 |
| O06 Malformed/repeated/conflicting clauses | E | Grammar rejects each invalid clause without partial schema/data change | P:storage_policy partial; missing clause population | 02 |
| O07 Ineligible domains/class/shared/context | E,N | Semantic errors preserve metadata and values; rejection stage is explicit | P:storage_policy; S:schema_policy; C:storage | 02 |
| O08 Quoted/unquoted identifiers and clause positions | N,E | Supported identifiers retain accepted interpretation; rejected placements preserve state | No dedicated complete population; parser grammar | 02 |
| O09 SHOW HEAP OOS / SHOW ALL HEAP OOS | R | Exact object attribution and supported fields, no-file controls and positive file evidence | S:owner_drop,jdbc_storage; C:show | 03 |
| O10 SHOW invalid/missing/view/system/hierarchy arguments | R,E | Accepted targets return attributable rows; invalid targets return intended error | P:storage_policy partial; C:show partial | 03 |
| O11 SHOW ordinary-user denial and DBA positive | R,E | Granted data read succeeds; both DBA-only SHOW forms fail explicitly for ordinary user | S:jdbc_storage | 03 |
| O12 Stored-record flag and mixed heap observer | R | Every logical row joins a real REC_HOME slot with stored flags and complete values | NEW S:record_flags (01 PASS) | 01,14 |
| O13 Physical slots versus transaction visibility | R,D | Physical uncommitted slot is separate from ordinary visible rows; absence is not clear | NEW S:record_flags (01 PASS) | 01,06,14 |

### Reads and relational operations

| ID / operation | States | Independent intended result | Existing assertions / remaining obligation | Tickets |
| --- | --- | --- | --- | --- |
| O14 Heap scan, selective projection, existence/header fetch | R | Exact full projected values/row set; no accidental attribute read/Expand for internal cheap-fetch contract | P:sql07_read_paths; S:read_paths; C:crud,visible_version | 05,14 |
| O15 Index lookup/range/descending/index-driven update fetch | R,U | Correct row identity and complete payload independent of access path | P:sql07_read_paths,sql04_update; S:read_paths | 05,06,09 |
| O16 Full-payload predicates/equality/order/comparison | R | Compare full values including distinct tails, NULL/empty and duplicate semantics | P:sql07_read_paths partial | 05,09 |
| O17 JOIN / outer join / correlated/subquery / CTE | R | Independent relation model determines all matching rows and full values | P:sql07_read_paths,sql04_update; S:read_paths partial | 05 |
| O18 GROUP BY / aggregate / DISTINCT / ORDER BY / LIMIT | R | Full-value grouping/order and exact selected relation, not only counts/prefixes | P:sql07_read_paths partial | 05,09 |
| O19 UNION and UNION ALL | R,X | Distinct/full multiset results follow ordinary SQL semantics over complete payloads | Generic corpus union.sql; dedicated OOS proof missing | 05 |
| O20 INTERSECTION and DIFFERENCE with supported ALL variants | R,X | Exact full-value relation/multiplicity follows supported grammar | Parser grammar; dedicated OOS proof missing | 05 |
| O21 CAST/expressions/VARBIT/string/national-string values | R,I,U | Type conversion and complete output values remain correct; compressed length is not placement proof | P:representation,sql07_read_paths; C:boundary | 05,11 |
| O22 Client fetch/JDBC prepared setBytes/getBytes | R,I,X | All bytes match independent arrays; actual invocation receives its own physical proof | S:jdbc_storage (Work401 historical PASS) | 05,14 |
| O23 Raw record consumers / opt-in Expand / buffer lifetime | R,X | Raw consumers receive full materialization; stored observer runs before Expand; buffers remain valid | C:visible_version,crud,identity_stamp; source fetch census | 14 |

### Copies and basic writes

| ID / operation | States | Independent intended result | Existing assertions / remaining obligation | Tickets |
| --- | --- | --- | --- | --- |
| O24 INSERT VALUES/single and multirow | I | Every accepted row matches distinct full model; rejected statement leaves previous model | P:sql01_insert_select; S:transactions; NEW S:record_flags | 06 |
| O25 INSERT SET/default/expression/subquery forms | I | Supported form produces independently specified row/default model | Generic grammar; dedicated complete OOS population missing | 06 |
| O26 INSERT SELECT/bulk copy/self-copy | X | Destination rows equal independent source model; both heaps retain separate state proof | P:sql01_insert_select; S:jdbc_storage; C:boundary | 05,06 |
| O27 CTAS / SELECT INTO supported materialization | X | Values and supported schema/policies follow contract; source destruction leaves destination readable | P:sql07_read_paths,schema_materialize; S:read_paths,jdbc_storage | 05,08 |
| O28 UPDATE assigned equal/new value | U | Exact post-image; assigned-equal follows ordinary insertion rule and correct ownership | P:sql04_update; S:dml_transitions | 06,15 |
| O29 UPDATE unassigned OOS payload | U | Full 24-byte stub retained under accepted reuse contract; newest version owns chain | S:dml_transitions values only; C:visible_version dispatch; reuse gap | 06,15 |
| O30 UPDATE single/multirow/join/subquery | U | Each matched row changes once according to independent relation model; other rows unchanged | P:sql04_update; S:dml_transitions | 06 |
| O31 UPDATE C-to-S/S-to-C/S-to-S/C-to-C | U | Actual pre/post flags and exact values, including NULL/empty and multi-chunk changes | P:sql04_update; S:dml_transitions aggregate physical only | 06 |
| O32 DELETE PK/payload predicate/selective/all | D | Intended rows absent and all survivor bytes exact; no clear-flag credit for absence | P:sql04_delete; S:dml_transitions; NEW S:record_flags | 06,15 |
| O33 TRUNCATE and reinsertion | D,I | No prior logical rows; fresh inserts exact and correct file ownership/lifecycle | P:sql04_delete; C:update_delete | 06,13,15 |
| O34 DROP populated/inline-only/recreate | D,I | Saved owner/file disappears, separate survivor values/owners remain exact | S:owner_drop; C:remove_file | 04,13,15 |

### Alternative writes

| ID / operation | States | Independent intended result | Existing assertions / remaining obligation | Tickets |
| --- | --- | --- | --- | --- |
| O35 MERGE matched UPDATE / unmatched INSERT / supported DELETE | U,I,D | Independent match model controls each branch and survivor/error behavior | Generic VARBIT _008_varbit_merge.sql; OOS proof missing | 07 |
| O36 REPLACE VALUES/SET/SELECT | I,U,D,X | Ordinary replacement/constraint semantics preserve exact rows and ownership | Generic VARBIT _006/_007_varbit_replace*.sql; OOS proof missing | 07 |
| O37 ON DUPLICATE KEY UPDATE hit/miss and assigned/unassigned | U,I,E | Hit updates intended row, miss inserts; rejected branch is atomic | Generic VARBIT _002_varbit_on_duplicate.sql; OOS proof missing | 07 |

### Constraints and triggers

| ID / operation | States | Independent intended result | Existing assertions / remaining obligation | Tickets |
| --- | --- | --- | --- | --- |
| O38 NOT NULL / CHECK / defaults / multirow rejection | E,I,U | Correct error identity and unchanged previous rows/metadata; subsequent valid DML succeeds | P:sql05_constraints; S:transactions | 06 |
| O39 Narrow-key PK/UNIQUE with OOS payload | E,I,U,D | Ordinary duplicates/NULL rules and exact full surviving payloads | P:sql05_constraints; S:transactions | 06,09 |
| O40 Ordinary single-node FK and supported actions | E,I,U,D | Referenced integrity, RESTRICT/NO ACTION and supported cascade/set-null preserve full rows | Generic corpus support; dedicated OOS proof missing | 06,10 |
| O41 BEFORE/AFTER INSERT/UPDATE/DELETE trigger/mirror/reject | E,I,U,D | Independent old/new full values and side-effect log, rejected DML atomic; classify actual resulting records | P:sql06_triggers; pre-trigger shell only in earlier delivery | 06 |

### Transactions and storage lifecycle

| ID / operation | States | Independent intended result | Existing assertions / remaining obligation | Tickets |
| --- | --- | --- | --- | --- |
| O42 COMMIT / ROLLBACK of INSERT/UPDATE/DELETE | I,U,D,E | Committed model survives, rollback restores pre-image and row membership | P:sql05_transactions; S:transactions; C:txn | 06,15 |
| O43 SAVEPOINT / partial rollback / failed DML then success | I,U,D,E | Restore exactly the named savepoint without losing prior work or owner chains | P:sql05_transactions; S:transactions | 06,15 |
| O44 Old reader during/after writer commit | R,U,D | Pinned reader reconstructs exact old model; new reader sees committed model | S:snapshot_visibility (historical PASS) | 06,13,15 |
| O45 Aborted UPDATE then acknowledged vacuum | U,R | Committed pre-image remains readable after real vacuum progress | S:../cbrd_27237_rollback_vacuum (retained historical FAIL) | 13,15 |
| O46 Committed update notification/borrowed chain ownership | U,D | Only committed dropped chains release once; undo/borrowed live references never delete | Source reserved notify/no-emitter gap; C:vacuum leaf is insufficient | 15 |
| O47 Same-slot stale identity read/delete retry | R,D,E | Stale read errors; stale/gone delete skips safely; replacement bytes remain intact | C:identity_stamp,eager_diagnostics,delete_server | 15 |
| O48 SA eager UPDATE/DELETE/non-MVCC lifecycle | U,D | Synchronous unreferenced cleanup preserves live chains, meaningful headers and diagnostics | S:dml_transitions,utility_sa; C:eager_cleanup,eager_diagnostics | 06,15 |
| O49 Repeated INSERT/DELETE at equal live data | I,D,R | Every survivor matches independent model; eligible empties return/reuse without avoidable growth | C:mock_vacuum/growth_sweep; S:snapshots_reclaim prerequisite FAIL | 13 |
| O50 Repeated INSERT/UPDATE/DELETE independently from failure | I,U,D,R | Full final model, bounded reuse/growth and equivalent live-data measurements for every required cycle | C:eager_cleanup/mocks only; product workload delivery missing | 13 |
| O51 Chunk deletion versus empty-page return/horizon | D,R | Count freed chunks separately; eligible empty pages return after reader/writer horizon permits | C:remove_file,growth_sweep,real_vacuum; S:snapshots_reclaim FAIL | 13,15 |
| O52 Lost hints/restart/debt/growth-gate sweep | I,D,R | Bitmap/empty-page truth survives hint loss; safely reclaim before new sector growth | C:growth_sweep simulated boot-rule only; product restart missing | 13,15 |
| O53 Fresh-equivalent packing/fragmentation comparison | R,I,U,D | Attribute pages, chunk bytes, heap/index/volume separately at equal exact live data | No complete product repeated-workload/fresh-reference receipt | 13 |

### Schema and partition operations

| ID / operation | States | Independent intended result | Existing assertions / remaining obligation | Tickets |
| --- | --- | --- | --- | --- |
| O54 ALTER ADD/DROP/REORDER/MODIFY/CHANGE/precision/default | U,E | Surviving full values, accepted policies/defaults and row membership remain exact; failures atomic | P:schema,schema_materialize; S:schema_cs,schema_sa,schema_policy | 02,08 |
| O55 Partition initial routing/read/pruning | I,R | Actual child heap owns row/OOS file and exact payload; root aggregate is insufficient | P:partition_routing; S:partition_owner (historical FAIL) | 08 |
| O56 Partition-key movement/reorganization/repartition | U,X,E | Destination ownership matches logical routing and survives source destruction/errors | P:partition; S:partition_owner (historical FAIL) | 08 |
| O57 CREATE INDEX/ALTER ADD PK or UNIQUE after rows | R | Full existing key relation indexes successfully, physical attribute proof and duplicates atomic | C:DDL partial narrow keys; generic large-key corpus | 09 |
| O58 DROP/RECREATE index/constraint and schema introspection | R,E | Accepted metadata and remaining data stay exact; heap OOS and key overflow remain separate | P:schema/storage_policy partial | 02,08,09 |

### Utilities and independent lifecycle

| ID / operation | States | Independent intended result | Existing assertions / remaining obligation | Tickets |
| --- | --- | --- | --- | --- |
| O59 unloaddb schema/data and CS loaddb | X | Policy/value/default/index metadata preserved; destination owns its file after source drop | S:utility_cs,backup_restore; default policies only | 04 |
| O60 SA loaddb logged/no-logging and prepared-row lifetime | X | Accepted value/header/CHN/policy/owner/txn/buffer contract; correct destination physical state | S:utility_sa logical PASS,utility_sa_physical FAIL; separate PR7925 | 04,08,15 |
| O61 compactdb / checkdb / diagdb / spacedb attribution | R,U,X | Complete values/metadata/owner survive compaction; diagnostics succeed and attribute correct subsystem | S:utility_cs/sa,owner_drop; no aggregate-to-record inference | 04,13 |
| O62 backupdb/restoredb engine volumes/logs | X,R | Independent acknowledged values/schema/owner return after owned destructive restore | S:backup_restore (historical PASS); retained external LOB not restored | 04 |
| O63 BLOB/CLOB locator demotion and copy/retry | R,I,U,X,D | Serialized locators demote profitably and preserve LOB copy semantics; payload lifecycle stays separate | P:sql09_lob_copy/maxcols; S:lob_locators; ADR0002 bounds regression | 04,05,14 |
| O64 Committed crash redo and uncommitted crash undo | I,U,D,R | Acknowledged committed model returns; uncommitted model rolls back with complete bytes | S:crash_committed,crash_undo,tde_crash_*; C:crash_recovery | 04,15 |
| O65 TDE lazy file/existing file/WAL/sentinel/reopen | I,U,D,R | Owned OOS file/user-data WAL apply class encryption; positive plaintext control and exact recovered values | S:tde_wal,tde_storage,tde_crash_*; existing-file application gap | 04,15 |

### Limits and representation

| ID / operation | States | Independent intended result | Existing assertions / remaining obligation | Tickets |
| --- | --- | --- | --- | --- |
| O66 Serialized profitability floor and aligned successor | I,U,E | At/below 24-byte stub no demotion; first profitable serialized neighbor demotes when required | P:representation; C:storage,identity_stamp | 11 |
| O67 PG four-record physical target/next aligned record/unfill | I,U | Accepted 4060-byte target at 16 KiB; next aligned 4064 crosses; target excludes unfill | Retained 4060/4064 reproducer; source quarter-page conformance gap | 12 |
| O68 Largest-first/priority/candidate exhaustion/residual | I,U | Independent layout target selects only needed eligible values; exhausted valid residual succeeds | P:representation/storage_policy; C:bigone; individual attr proof missing | 11,12 |
| O69 Chunk capacity/exact successor/multichunk | I,U,R | Full head/middle/tail bytes reconstruct and physical serialized topology matches exact capacity | P:chunk_boundaries; S:representation_chunks; C:real_vacuum | 11 |
| O70 VOT BYTE/SHORT/INT and many stubs | I,U,R | Exact representable neighbors preserve offsets, values and bounds; width-specific OOS bits valid | P:vot_many_attributes; S:representation_chunks; C:identity_stamp | 11 |
| O71 Inline stub width/read/write/grow-and-retry bounds | E,R,I,U | Never read/write beyond VOT field or output capacity; retry completes with correct bytes | C:identity_stamp,byte_span_writer; product LOB retry seed | 11,14 |
| O72 Signed length/descriptor maxima and impractical guards | E | Guard rejects invalid descriptor before allocation/I/O and preserves state | C:oos/identity_stamp internal guards; no full-size storage claim | 11 |
| O73 OOS+bigone residual rejection and ordinary bigone | I,U,E | Reject combined OOS+bigone before chain insertion; previous rows unchanged; non-OOS bigone accepted | P:sql05_bigone; S:transactions; C:bigone | 12 |
| O74 B-tree in-page key to overflow representation | R,I,U | Supported key continues with exact full value and index semantics; not an OOS rejection maximum | Source btree_load.h/btree.c; generic large-key corpus | 09,12 |

### Large indexed OOS value

| ID / operation | States | Independent intended result | Existing assertions / remaining obligation | Tickets |
| --- | --- | --- | --- | --- |
| O75 PK/UNIQUE before versus after population | I,R,E | Both maintenance/build paths enforce full-key uniqueness and retain actual indexed attribute stub | Generic tbl_enc_14 OOS/key-overflow headers only; dedicated proof missing | 09 |
| O76 Supported single/composite/prefix/domain/collation keys | I,U,R,E | Supported combinations preserve comparison semantics; unsupported combinations reject atomically | Generic key corpus; explicit support/rejection ledger required | 09,10 |
| O77 Equality/range/order/index projection and join by large key | R | Complete indexed value and exact result model, positive index-path/attribute placement evidence | P:sql07_read_paths narrow keys beside OOS payload only | 09 |
| O78 Key INSERT/UPDATE/DELETE/REPLACE/duplicate-key branch | I,U,D,E | Complete surviving keys/payloads and constraint ownership remain exact across all branches | Dedicated indexed-OOS fixture missing | 09,07 |
| O79 Duplicate/NULL/rollback/error handling | E,I,U,D | Ordinary supported PK/UNIQUE NULL/duplicate rules, complete rollback/pre-image after errors | P:sql05_constraints narrow-key only | 09 |
| O80 FK referenced/referencing keys and cascade/restrict/set-null | I,U,D,E | Supported large-key relation enforces ordinary single-node FK actions with exact values | Dedicated large-key FK fixture missing; depends 09 | 10 |

### Internal-only and final reconciliation

| ID / operation | States | Independent intended result | Existing assertions / remaining obligation | Tickets |
| --- | --- | --- | --- | --- |
| O81 Dispatch/batching/Expand avoidance and non-OOS control | R,X | Required counters/routes remain discriminating when logical outputs coincide | C:crud,visible_version,server | 14 |
| O82 Identity/publication/allocation/fault/cleanup atomicity | E,I,U,D | Fault leaves valid published pair, correct diagnostics and intact survivor chain/bytes | C:server,identity_stamp,eager_diagnostics,vacuum | 15 |
| O83 Final SQL/shell/C++ exact selection and wrong-expectation controls | N | Every required execution has native verdict/artifacts, exact identity and truthful FAIL/gap disposition | 01 tracer PASS+two NOK controls; complete final selection not run | 16 |

## Exact dedicated testcase population

All 18 public cases and their matching answers remain retained. None ran again in ticket01. Their ordinary SQL assertions remain useful independently of missing per-record evidence. The partition movement case remains a correct failing candidate.

| Public case basename | Retained assertion family | Owner tickets |
| --- | --- | --- |
| `cbrd_26659_oos_chunk_boundaries.sql` | Representation/chunk/offset exact values and lengths | 11,12 |
| `cbrd_26659_oos_partition.sql` | Routing/movement exact values, separate physical-owner gap | 08 |
| `cbrd_26659_oos_partition_routing.sql` | Routing/movement exact values, separate physical-owner gap | 08 |
| `cbrd_26659_oos_representation.sql` | Representation/chunk/offset exact values and lengths | 11,12 |
| `cbrd_26659_oos_schema.sql` | Schema rewrite/materialization exact values and metadata | 02,08 |
| `cbrd_26659_oos_schema_materialize.sql` | Schema rewrite/materialization exact values and metadata | 02,08 |
| `cbrd_26659_oos_sql01_insert_select.sql` | Distinct full bulk/copy model | 05,06 |
| `cbrd_26659_oos_sql04_delete.sql` | Exact UPDATE/DELETE model and survivors | 06 |
| `cbrd_26659_oos_sql04_update.sql` | Exact UPDATE/DELETE model and survivors | 06 |
| `cbrd_26659_oos_sql05_bigone.sql` | Residual-size error and preserved row | 12 |
| `cbrd_26659_oos_sql05_constraints.sql` | Constraint errors and preserved model | 06,09,10 |
| `cbrd_26659_oos_sql05_transactions.sql` | Commit/rollback/savepoint exact model | 06,15 |
| `cbrd_26659_oos_sql06_triggers.sql` | Trigger side effects/rejection/row values | 06 |
| `cbrd_26659_oos_sql07_read_paths.sql` | Read/relational/copy full model | 05,14 |
| `cbrd_26659_oos_sql09_lob_copy.sql` | External LOB copy/locator or rejected maximum | 04,05,11,14 |
| `cbrd_26659_oos_sql09_lob_maxcols.sql` | External LOB copy/locator or rejected maximum | 04,05,11,14 |
| `cbrd_26659_oos_storage_policy.sql` | Policy DDL/eligibility/metadata/error model | 02,03,04 |
| `cbrd_26659_oos_vot_many_attributes.sql` | Representation/chunk/offset exact values and lengths | 11,12 |

The 24 existing directly related private entrypoints plus the new observer make 25 retained entrypoints. Discovery requires the exact repeated basename pattern above. Helper scripts in `oos_common`, `oos_utility` and case directories are dependencies, not additional discovered cases.

| Private case key | Existing assertion/evidence and limit | Owners |
| --- | --- | --- |
| `backup_restore` | Owned engine-volume/log destructive restore and exact model, external LOB retained | 04 |
| `crash_committed` | Acknowledged commit crash/redo and exact values | 04,15 |
| `crash_undo` | Acknowledged open writes, crash undo and pre-image | 04,15 |
| `dml_transitions` | SA exact values plus table current chunks, no individual flags | 06,13,15 |
| `jdbc_storage` | All JDBC bytes and actual heap SHOW, permissions and copied survivor | 03,05,14 |
| `lob_locators` | Actual locator demotion, external copy independence and full values | 04,05,14 |
| `owner_drop` | Positive owner and file disappearance with exact separate survivor | 04,13,15 |
| `partition_owner` | Correct destination-owner assertion, historical FAIL | 08 |
| `read_paths` | Exact reads/materialized survivors and selected path plans | 05,14 |
| `record_flags` | NEW actual same-heap flags/type/slot/full values and visibility,01 PASS | 01,14 |
| `representation_chunks` | Distant gate/floor/offset/chunk models, not accepted physical target | 11,12 |
| `schema_cs` | CS rewrite/routing metadata and exact values, limited ownership | 08 |
| `schema_policy` | Accepted policy metadata, rejected ALTER preservation and physical behavior | 02,04 |
| `schema_sa` | Distinct SA workspace rewrite model and placement limits | 08,15 |
| `snapshot_visibility` | Old/new exact snapshots and obsolete chunk removal, no page-return credit | 06,13,15 |
| `snapshots_reclaim` | Correct page-return prerequisite FAIL, dependent churn not executed | 13,15 |
| `tde_crash_committed` | AES acknowledged crash/redo and owned headers | 04,15 |
| `tde_crash_undo` | AES uncommitted crash undo and owned pre-image | 04,15 |
| `tde_storage` | Mapped OOS-volume/active-log plain-positive and AES-negative sentinel | 04,15 |
| `tde_wal` | Lazy AES/file metadata/WAL flags, existing-file application gap | 04,15 |
| `transactions` | Exact transaction/error atomicity with current aggregate OOS observations | 06,12,15 |
| `utility_cs` | CS unload/load/compact values/schema/owner; default-policy fixture | 04 |
| `utility_sa` | SA logical utility PASS at original revision, no OOS destination credit | 04,08,15 |
| `utility_sa_physical` | Correct SA destination-placement assertion, historical FAIL | 04,08,15 |
| `cbrd_27237_rollback_vacuum` | Correct abort/vacuum survivor read, historical timeout/FAIL | 13,15 |

Wider-corpus reuse candidates at public `df8596d` include `sql/_32_damson/cbrd_23679/_03_insert/_04_type_varbit_allow/cases/`: `_008_varbit_merge.sql`, `_006_varbit_replace_values_set.sql`, `_007_varbit_replace_select.sql` and `_002_varbit_on_duplicate.sql`. They establish useful syntax/ordinary assertions. They do not establish HAS_OOS placement or full large indexed-key coverage. The private `shell/_36_damson/cbrd_23608_tde/tbl_enc_14/cases/tbl_enc_14.sh` identifies OOS, B-tree and key-overflow file headers, but does not replace the required actual indexed-attribute proof. Generic FK/set-operation assets require the same support/oracle audit before reuse.

## Work109 requirement reconciliation

The 31 prior requirements retain their existing [assertions, receipts and limits](ci-replan/coverage.md). The following mapping prevents the new population from dropping earlier obligations. It adds no passing credit.

| Prior requirements | New ticket owners and remaining classification |
| --- | --- |
| R01 basic insert/read/copy | 05,06,14. Individual input/destination states and full model. |
| R02 largest-first, R03 target/floor, R04 NULL/VOT, R05 chunks | 11,12,14. Accepted target failure and exact serialized neighbors remain separate. |
| R06 policies | 02,04. Accepted syntax/eligibility/persistence and nonretroactive ALTER. |
| R07 types, R08 locators | 04,05,11,14. Attribute serialization is separate from external LOB payload lifecycle. |
| R09 writes, R10 transactions, R11 bigone, R12 constraints/triggers | 06,07,09,10,12,15. Alternative writes and ordinary FK add missing population. |
| R13 reads | 05,09,14. Full comparisons, set operations and indexed OOS key extend existing narrow-key reads. |
| R14 schema, R15 partitions | 02,08,15. Actual destination owner and SA behavior remain necessary. |
| R16 SHOW | 03. Target/argument/permission population and observation scope. |
| R17 redo, R18 undo | 04,15. Preserve ordinary and AES historical crash subsets at their own revisions. |
| R19 snapshots, R20 rollback/vacuum, R21 chain ownership, R22 identity retry | 06,13,15. Identity cannot prove ownership or commit eligibility. |
| R23 page reclaim/reuse | 13,15. Independently execute both churn workloads and fresh-equivalent comparison. |
| R24 owner/DROP, R25 utilities, R26 backup | 04,08,15. Same-invocation owner/value and explicit policy roundtrip. |
| R27 TDE | 04,15,16 retain/reconcile existing exact subset. Existing-file application stays a capability gap. |
| R28 HA transport | Work463 deferred by explicit user direction. No replacement by single-node FK or crash. |
| R29 CDC/flashback | Accepted release deferral. Existing cbrd_27064/27075 stay enabled and visibly failing. |
| R30 internal faults/bounds | 11,14,15. Preserve internal controls and reachable external atomicity separately. |
| R31 future/proposed/non-OOS | 16 retains scope ledger. No invented FORCE_INLINE/compression/PEEK/sharding contract. |

## Work401 dispositions and completion boundary

The [Work401 report](coverage-additions-work401-20261016.md) retains all 29 partial/failed matrix dispositions. Its exact 19-case run and separate 1-case sentinel are two invocations. Four correct regressions remain FAIL at their recorded source. Ticket01 neither reruns them nor changes their expectations.

| Work401 matrix rows | Owners / retained obligation |
| --- | --- |
| contract-1, performance-1, performance-2 | User-deferred performance qualification. No throughput/latency/baseline claim. |
| contract-3 | 12 accepted physical target and next aligned neighbor. |
| representation-3, representation-4 | 11,14,15 persisted VOT/stub bounds, retry and identity. |
| writes-3 | 06,08,15 trigger/workspace physical ownership and rejection. |
| reads-2, reads-3 | 04,05,14 internal dispatch/raw fetch, actual JDBC and SA loader scope. |
| transactions-3, transactions-4 | 06,13,15 retain abort/vacuum FAIL and actual snapshot subset. No extra broad qualification promise. |
| lifecycle-3, lifecycle-4 | 13,15 page return/churn/restart and accepted chain reuse/commit notification. |
| schema-4 | 08 actual partition destination ownership. |
| recovery-3, recovery-4 | 04,11,15 typed recovery boundaries and deterministic internal faults. |
| utilities-3, utilities-4 | 04,08,15 preserve SA physical FAIL and bounded engine-only backup claim. |
| replication-1, replication-2 | Work463 deferred HA topology/transport/failover. |
| replication-3 | Deferred CDC/flashback, existing enabled regressions unchanged. |
| security-2, security-3 | 04,15,16 retain existing-file application gap and actual bounded AES/crash/sentinel subset. |
| operations-2, operations-3 | 03,14 permission/busy-page limits. Broad operator runbook remains outside promised supplement. |
| performance-3 | 13 storage efficiency/churn is required despite deferred speed benchmarking. |
| performance-4 | 16 preserves Linux/16KiB/optdebug scope, no whole-platform release claim. |
| delivery-1, delivery-3 | 16 exact artifacts/compatibility/review/CI boundaries, separate Work371 integration readiness. |

Every new ticket must attach execution-specific evidence to these obligations. The01 observer enables current REC_HOME mixed-record evidence only. Relocated slots, forwarding records, older visible versions, partition ownership and per-attribute IS_OOS remain separate validation obligations. Missing required tests, unclear support/oracles and missing native executions prevent supplement completion. Reproduced engine FAIL cases retain their independent correct oracles and receive no passing credit.
