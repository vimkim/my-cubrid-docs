# Work456 ticket 08: schema changes and partition ownership

Date: 2026-10-21, Asia/Seoul. Audience: the author and reviewers of [PR8128](https://github.com/CUBRID/cubrid/pull/8128).
Scope: supplement operations O54–O56 and preserve the related standalone C++ contracts.

The new schema fixtures compare complete values and actual stored records in SA and CS modes.
The partition fixtures keep the intended destination heap and OOS owner requirements.
A reproduced partition failure receives no passing coverage credit.
This report does not claim that the separate loader or deferred-write repairs are integrated.

## Authority and revisions

The [approved specification](supplement-spec-work456-20261021.md) and [ticket 08](supplement-tickets/issues/08-schema-and-partition-ownership.md) define the scope.
The [operation inventory](supplement-operation-inventory-work456-20261021.md) identifies the initial obligations.
The [ticket 02 report](ticket02-policy-contract-20261021.md) supplies the accepted policy omission and reset rules.
The normative OOS context has SHA-256 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`.

| Component | Exact identity | Evidence limit |
| --- | --- | --- |
| New native engine and installed binaries | `d13aebf6428a68c2852d16df143d1da203d86dea` | Linux OptDebug, 16 KiB, `UNIT_TEST_OOS=ON`. Each attempt copies the immutable ticket 14 provider. |
| Source starting integration | `d13aebf6428a68c2852d16df143d1da203d86dea` | Source and installation match at each native preflight. No engine repair is part of this ticket. |
| Public TC starting integration | `754dfffd83f7b3a14e13e8a5b965ccf4f2ae2920` | Existing answers remain unchanged. |
| Private TC starting integration | `e5fa4b460fb80a9712f6191402b2abe6ade501df` | Existing schema and partition regressions remain enabled. |
| Retained C++ execution | `1ef86a7efa34002e971b1b30bcf5d451e9db441b` | The separate ticket 14 baseline invocation tested the five DDL cases. |
| SA loader repair, PR7925 | `6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f` | Separate source and evidence. Its successes do not qualify the handover engine. |
| Deferred-write dependency, PR7927 | `4a4d069c21fc19f14337efceca512b726724ecd8` | Separate revision from the original supplement inventory. No repair integration or passing credit is inferred. |

The initial source environment has no local build directory or compilation database.
Text inspection and the matching installed provider support this tests-only work.
A source build and its compilation database remain necessary for local build or LSP work.

## Schema oracles and record states

The small control is the exact six-byte value `19ab23cd45ef`.
The other payload has 1,701 bytes `a1`, 1,703 bytes `b2`, and 1,703 bytes `c3`.
The second distinct large attribute has 1,709 bytes `d4`, 1,711 bytes `e5`, and 1,713 bytes `f6`.
Every logical snapshot checks all surviving rows and complete value equality.
Counts and payload lengths alone cannot satisfy these assertions.

`schema_rewrites_cs` and `schema_rewrites_sa` use the same mixed-row model.
They check nullable ADD/DROP, FIRST/AFTER reordering, rename, MODIFY precision/nullability, MODIFY and CHANGE scalar conversions, and defaults.
Changing a default preserves existing `77` values and gives a subsequent omitted insert the new value `88`.
Rejected precision conversion, explicit fixed-type storage policy, and hard-default-disabled ADD preserve full values and canonical DDL.
The physical checks classify the exact logical rows by `HAS_OOS` after every relevant operation.
They record meaningful CHN fields without imposing a SQL CHN monotonicity or padding equality rule.

`schema_attributes_cs` and `schema_attributes_sa` separately qualify actual attributes.
The original mixed heap contains an inline control and a row with two OOS-backed attributes.
The tests materialize the reordered representation before decoding its attribute map.
Dropping the first OOS attribute preserves the complete second value and its actual owner.
Dropping the last OOS attribute and materializing the new representation clears the actual record flag.
These checks do not require immediate reclamation of retained versions or their chains.

A separate fixture starts with a 3,000-byte inline value and a readable 2,500-byte literal default.
Literal ADD alone leaves the stored record clear.
`ADD hard INT NOT NULL` without a DEFAULT invokes the accepted hard-default materialization path.
The physical result must demote the larger original attribute and retain the smaller default inline.
The test verifies both actual attribute entries and their full payloads.

The existing public `schema` and `schema_materialize` cases remain retained.
The existing private `schema_cs` and `schema_sa` cases retain data-bearing ADD/UPDATE/DROP and catalog assertions.
The new JDBC `schema_rewrites` case extends the mixed-row logical model.
JDBC results do not establish physical placement in another invocation.

## Physical observation contract

The record observer starts with complete ordinary SQL values and distinct row identifiers.
`SELECT_RECORD_INFO` provides the physical OID, record type, flags, and transaction fields.
The current-record qualification admits only a unique logical `REC_HOME` candidate for each expected row.
The predicate never selects rows by an expected `HAS_OOS` value.

The stopped observation uses these existing product interfaces:

```sh
cubrid diagdb -d 9 --dump-records --class-name dba.TABLE DATABASE
cubrid diagdb -d 1 DATABASE
cubrid diagdb -d 2 DATABASE
```

`diagdb` requires the schema-qualified class name in this revision.
The heap dump supplies exact slot bytes and the complete current class representation.
The helper requires the stored representation ID to match that qualified representation.
It obtains variable-attribute locations from that representation, then decodes each actual VOT entry and 24-byte stub.
The head OID, complete serialized length, and identity stamp must agree with the actual OOS chunk.
All reconstructed VARBIT payload bytes must match the independent input model.
Unused alignment padding is outside the equality contract.

The owner check resolves the chunk page through the exact file allocation table.
It compares that file's class OID and heap descriptor with the actual record heap.
The read-only raw page reader validates page identity, page type, encryption flags, footer watermark, and bounded slot spans.
Its qualified profile is Linux little endian, 16,384-byte I/O pages, and a 16,344-byte database area.
It rejects relocation, unknown volume mappings, encrypted pages, missing or duplicate identities, and unsupported layouts.
No new production API or engine behavior supports this observation.
The product interfaces come from [heap dump](https://github.com/CUBRID/cubrid/blob/d13aebf6428a68c2852d16df143d1da203d86dea/src/storage/heap_file.c#L16242), [slot hex dump](https://github.com/CUBRID/cubrid/blob/d13aebf6428a68c2852d16df143d1da203d86dea/src/storage/slotted_page.c#L4237), and [file allocation dump](https://github.com/CUBRID/cubrid/blob/d13aebf6428a68c2852d16df143d1da203d86dea/src/storage/file_manager.c#L7667).
The raw chain profile uses the [OOS chunk and stamp definitions](https://github.com/CUBRID/cubrid/blob/d13aebf6428a68c2852d16df143d1da203d86dea/src/storage/oos_file.hpp#L32).

Partition DDL can leave an old marked record and a current successor in separate slots.
The complete before/after population remains in the evidence.
A new retirement must name a previously observed live slot and its stable row marker.
Its delete transaction ID must match the observed successor insert ID after the owned DDL client ends.
An earlier retired generation keeps its saved provenance.
A later type 6/7 tombstone is accepted only at that exact previously qualified retired OID with all logical and MVCC fields NULL.
Retired records and tombstones receive no current-row or clear-flag credit.
Any new anonymous, duplicate live, or relocated record remains an observation failure.

Direct child SQL scans are supplementary observations.
They must agree with the independent range/list membership model and the stopped physical heap map.
A root diagnostic traversal or root aggregate cannot substitute for a child heap.
Hash routing has no manual-specified literal child formula in this test.
Its ownership oracle uses the actual heap independently established from the stopped record dump.

## Partition workloads and intended failures

The manual checkout is `3b6ae97bfbdc664b010ffa933ded5a05b291ae03`.
Its [partition manual](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/sql/partition.rst#L317) defines direct partition access, range/list reorganization, hash resizing, and removal of partitioning.
[ADD/DROP](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/sql/partition.rst#L420) supports the separate range/list lifecycle.
[PROMOTE](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/sql/partition.rst#L520) supports range and list only.
Hash PROMOTE and literal DROP are inapplicable; the retained hash cases execute the supported ADD/COALESCE clauses.
The generic committed `_01_promotion.sql` and `_02_promotion_errors.sql` also preserve these syntax and support contracts.
Range/list membership comes from the independent literal partition bounds and lists.
The manual excludes VARBIT from supported partition-key domains.
A partition-key domain rejection and invalid ADD after MAXVALUE must preserve the original table and its complete data.

The native cases exercise DEFAULT and FORCE_OUTLINE independently.
A new database and an explicit cleanup separate each policy invocation.
An earlier ownership failure does not stop the remaining intended operations.
Range/list split and merge each have separate initial fixtures.
Hash ADD and COALESCE also have separate initial fixtures.
The removal fixture verifies the final unpartitioned destination through actual records and raw chain ownership.

| Workload | Native case suffix | Independent oracle |
| --- | --- | --- |
| Initial routing and reads | `partition_route_range`, `partition_route_list`, `partition_route_hash` | Complete mixed rows, range/list child membership, actual current record flags, and actual chain owner |
| Partition-key movement and rejection | `partition_move` | Correct destination, absent old logical key, duplicate-key rejection, unchanged surviving values and ownership |
| Range split and merge | `partition_reorganize_range`, `partition_reorganize_range_merge` | Exact literal destination bounds, deleted source class where applicable, complete surviving values and destination owner |
| List split and merge | `partition_reorganize_list`, `partition_reorganize_list_merge` | Exact literal list membership and destination owner |
| Existing table partitioning | `partition_repartition` | Independent source values survive in actual new child heaps with correct child ownership |
| Remove partitioning | `partition_remove` | All original rows survive in the actual unpartitioned heap and its OOS file |
| Hash redistribution | `partition_hash_resize`, `partition_hash_coalesce` | Complete surviving values and per-record actual destination heap ownership |
| ADD/populate/DROP lifecycle | `partition_add_drop_range`, `partition_add_drop_list` | Newly added child data and exact chains disappear after selected DROP; sibling complete values and actual owners survive |
| Promotion lifecycle | `partition_promote_range`, `partition_promote_list` | A populated child becomes a standalone table and preserves complete values and its own OOS chains after source-root destruction |
| Rejection atomicity | `partition_partition_rejection` | Expected rejection, rejected object absence, unchanged canonical DDL and full surviving values |

The initial probe found actual records in a child heap while their OOS chains belonged to the root heap.
One multirow range fixture also placed the key `3` in `p0` despite the intended `p1` destination.
The raw record OID, class representation, complete payload, file allocation, and owner descriptor support these observations.
These failures stay linked to [PR7927](https://github.com/CUBRID/cubrid/pull/7927) and Work393 as a separate repair scope.
That link does not establish the internal cause of every new routing or rewrite failure.

The separate ADD/DROP fixtures issue single-row INSERT statements and establish correct literal child membership before checking ownership.
After selected DROP, the exact removed large-value chain remains allocated under the root owner with its original logged identity.
The check follows that identity without requiring immediate page reclamation or zero-filled pages.
Complete sibling values and actual surviving owners are checked independently.

PROMOTE keeps the populated child under its documented standalone name.
The fixture removes the source root and then attempts the complete promoted-table value oracle.
The failing engine reports inconsistent or corrupted OOS metadata for the large value.
The stopped diagnostic still supplies current heap slot bytes and class layout; its later object-value read reports an error.
The lifecycle adapter records that product-read failure and requires the independent slot parser to succeed.
A missing allocated owner produces an ownership defect and `full_payload_verified=false`.
It does not receive full-payload, head-stamp, or survival credit.
Unknown layout or incomplete slot bytes still stop the observer as an unqualified result.

The retained public `partition` case keeps its intended movement/reorganization answer.
The retained `partition_routing` case remains useful for logical routing reads and duplicate rejection.
The retained private `partition_owner` case keeps its correct root-empty and destination-owned expectations.
No expected answer was changed to match observed defects.

## C++ disposition and execution

All five `OosSqlDdl` cases remain retained.
Their source is byte-identical between the shared baseline and the ticket starting source.
No C++ case was removed, migrated, or weakened.
The native baseline receipt SHA-256 is `d55d4243db537e6c8c5338ffd15d8f41429e76391f04d18990b367cbbb585b9e`.
An independent audit matched the declaration, discovery, start, console-pass, and GoogleTest XML identities.
The dedicated fixture-aware CTest invocation passed all five cases with zero skips.

| Retained case | Actual assertions and limit |
| --- | --- |
| `AlterAddColumn` | Existing value lengths, nullable ADD acceptance, insertion with the new column, and final row count. Length alone does not classify OOS. |
| `AlterDropOosColumn` | DROP acceptance and surviving row count. New shell cases add complete surviving values and actual attribute state. |
| `CreateTableAsSelect` | Destination count, copied value length, and readability after source destruction. It does not identify each stored attribute. |
| `DropAndRecreateSameName` | Recreated table accepts row `1`, label `new_table`, and the expected value length. It preserves distinct SA execution behavior. |
| `DropCreateCycles` | Repeated create/populate/drop remains executable and returns expected counts across its recorded cycles. |

The stronger SQL/shell values do not justify deleting distinct standalone execution contracts.
The [accepted SA prepared-row decision](../cbrd-27424/sa-inline-preservation-decision-20261017.md) still governs workspace CHN, policy, ownership, transactions, and buffer lifetime.
Its 21 stored-row and 13 real loader/workspace comparisons belong to the separate PR7925 revision.
The known handover SA loader physical regression remains linked to [CBRD-27424](https://jira.cubrid.org/browse/CBRD-27424) and [PR7925](https://github.com/CUBRID/cubrid/pull/7925).
Neither the C++ DDL baseline nor these schema SQL fixtures substitute for those actual loader invocations.

## Native receipts and handoff

The frozen `final01` shell selection contains exactly 20 cases: 6 schema PASS, 14 partition FAIL, and zero skips in 809.274748 seconds.
The native runner returned `0`; the independent verifier returned `1` because the 14 failures remain failures.
All 30 new mode/policy invocations reached `all_required_phases` and `owned_cleanup`.
The independent audit found zero observer errors and 58 raw attribute/owner snapshots.
The input bytes remained unchanged through that invocation.
The artifact XML SHA-256 is `3d558a16f9823529d6f61c25a3dd567771467e0bacec7ba1b8327ad0368e8d74`.
The expected, dispatched, and finished case-list hashes all equal `0ae74543286719598555feab016a77303422c48682aa68f9e4c9f4b9f2904f61`.

The frozen test commits are public `a55886659` and private `754defba5`.
The lifecycle additions were frozen at private `9b4ec150e` and ran separately.
They do not change the frozen 20-case receipt.

| Native selection | Exact verdict | Wall time | Observation limit |
| --- | --- | --- | --- |
| `final01`, shell 20 | 6 PASS, 14 FAIL, 0 skip | 809.274748 s | Four new schema modes, retained schema CS/SA, 13 independent partition cases, and retained partition owner |
| `lifecycle-final01`, shell 4 | 0 PASS, 4 FAIL, 0 skip | 326.312484 s | Range/list ADD/DROP and PROMOTE, both policies, all eight invocations reached every declared phase and cleanup |
| `final-sql01`, JDBC 5 | 5 PASS, 0 FAIL, 0 skip | 51.981954 s | `schema`, `schema_materialize`, `schema_rewrites`, `partition`, and `partition_routing`; logical invocation only |
| `control-flag01`, shell 1 | 1 deliberate FAIL | 9.013243 s | Copied corpus changes only row 2's expected `has_oos` from true to false; actual stored flags reject it |
| `control-payload01`, shell 1 | 1 deliberate FAIL | 10.094665 s | Copied model changes only expected `c3` bytes to `c4`; complete raw VARBIT comparison rejects it |

Both controls have one case, zero skips, and owned cleanup.
Each native runner returned `0`; both independent verifiers returned `1` and retained the failure.
The controls intentionally stop at the changed assertion and receive no later-phase credit.
The unmodified attribute CS case passed in `final01` before these disposable corpora were used.
No tracked test or expected answer was modified for a control.

Across the two final shell selections, all 38 new mode/policy invocations reached all required phases and cleanup.
The audit found 86 raw snapshots, no observer errors, and no changed input bytes.
Missing OOS owners after PROMOTE remain explicit conformance failures with no reconstructed-payload credit.
A failing SQL/JDBC case could not provide these physical facts; the independent SQL selection passed all five logical contracts.

| Artifact | SHA-256 |
| --- | --- |
| Lifecycle 4 shell XML | `ef6681cc05968297fb748c2da3d9b7fc2cfc52315423cedd5d827a352dc71ce0` |
| JDBC 5 XML | `c6133701fd5751ead03009fd3947eef57e0a57b2ad65700f1c66f7f40981060c` |
| Wrong flag control XML | `6b804022043ea64182617cd69c48acc0e3136bdf60fa280554ae9860e6e7730b` |
| Wrong payload control XML | `17367414a5e805f216687cd3fcb393e439a619f3f6b9f210ffa31e6a4e84dd16` |

Each attempt uses its own copied d13 installation, CTP, HOME, registry, configuration, and TMP.
The source worktree was initialized with `cub-workenv init --no-db`.
Every preflight reports source `d13aebf` matching the installed commit, native mode, and containment available.
Shell uses explicit `TESTKIT_NATIVE=shell`; JDBC uses `TESTKIT_NATIVE=sql`; both set `TESTKIT_CONTAIN=1`.
Each suite uses one native slot and no retries or exclusions.
The shell slot snapshot records master port `1568` and broker ports `10090`/`13091` inside its private network namespace.
The SQL configuration specifies master `41092`, broker `41093`, master SHM `0x6200005c`, and application SHM `0x6200005d`.
Actual PID, IPC, mount, and network namespace identities differ from the host.
The SQL receipt independently captured nine owned native processes and the one-slot readiness log.

The runner SHA-256 is `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`.
Its Go revision is `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`, with `vcs.modified=true` recorded.
No runner rebuild or shared installation mutation occurred.
The cleanup receipt confirms no owned process, registered database, or database asset remains.
The SQL registry retains only its normal comment header.
The six sampled binaries in every final attempt match the immutable ticket 14 d13 provider exactly.

The read-only handoff source branch includes integration `9c21a1ae701c847803690bd1c567b74f0d0918a9`.
The public task branch includes integration `65f9393ada5455a4908c649a7dc0469f5a7e2ebb` at `376c5a6ee130a91d925c606a2b0a244f6fb6f4dd`.
The private task branch includes integration `5c0fc6175881efac22f623dbc1169b84b0aa455b` at `0833ba939a2ca8201ab16ef82f4b6975d1f68f4d`.
All selected input bytes remain identical after these merges.
These merge identities do not transfer d13 execution credit to another source installation.
The coordinator's final combined qualification remains separate.
There is no ticket 08 engine change.

Earlier `probe01`–`probe04`, `green01`–`green04`, and `lifecycle-probe01` remain implementation history.
They include the rejected unqualified class-name/ONLY-child observations, helper initialization corrections, and the initial diagnostic-error classification.
Their passes do not substitute for the final frozen selections.
The exact revision, environment, configuration, command, case list, inputs, raw native results, independent audits, and cleanup receipt remain in the raw attempt root.
The raw attempt root is `/home/vimkim/temp/work456-implementation/ticket08`.
Large logs, copied installations, and generated intermediate inventories remain outside Git.
The report and this ticket directory's README are the only selected documentation changes.

No source/TC push, CI trigger, JIRA edit, TC PR action, or destination integration occurred during this implementation.
Performance and HA remain deferred.
