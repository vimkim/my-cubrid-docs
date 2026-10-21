# Work456 ticket 08: schema changes and partition ownership

Date: 2026-10-21; corrected verification: 2026-10-22, Asia/Seoul. Audience: the author and reviewers of [PR8128](https://github.com/CUBRID/cubrid/pull/8128).
Scope: supplement operations O54–O56 and preserve the related standalone C++ contracts.

The corrected partition run completed all required observations and retains 13 native FAIL verdicts.
Its child memberships, logical unions, complete values, and raw destination heaps pass; 82 chain-owner and 14 attribute-state defect observations remain separate.
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
The manual does not publish a literal hash formula, but the exact d13 INT hash and child metadata order provide an independent implementation oracle.
The corrected hash fixtures use that pinned expected destination and separately compare each actual chain owner with the actual record heap.

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

The partition fixtures use C/S mode and exercise DEFAULT and FORCE_OUTLINE independently.
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
The original range fixture used `p0 < 10`, so its key `3` correctly belonged to `p0`.
The previous attribution of that placement to an engine routing defect is withdrawn.
The original ONLY/named-child results also cannot establish parent widening or unsupported child access; their fixture placed all three keys in p0.
The raw record OID, class representation, complete payload, file allocation, and owner descriptor support these observations.
These failures stay linked to [PR7927](https://github.com/CUBRID/cubrid/pull/7927) and Work393 as a separate repair scope.
That link does not establish the internal cause of the observed ownership or rewrite failures.

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

## Corrected range and hash oracle

The independent merger found a test-fixture error before ticket 08 integration.
Seven range scenarios expected key 3 in p1 while their DDL assigned it to p0 below 10.
Those routing assertions were invalid; the old receipts remain implementation history.
The corrected fixture changes the exclusive boundary to 3 and retains the independently intended memberships.
It does not change expected membership to match observed engine output.

| Phase | Independent row-to-partition expectation |
| --- | --- |
| Initial range, rejection snapshots, existing-table partitioning | p0 below 3 contains 1,2; p1 from 3 contains 3 |
| After movement and rejected movement | p0 contains 1; p1 contains 3,12; key 2 is absent |
| Split, or the initial merge fixture | low below 2 contains 1; mid from 2 below 3 contains 2; p1 contains 3 |
| Merged | merged below 3 contains 1,2; p1 contains 3 |
| REMOVE PARTITIONING | All 1,2,3 rows belong to the unpartitioned root |
| List before/split/merge | Explicit lists assign 1,2 to p0 or merged; split assigns 1 to low and 2 to mid; 3 stays in p1 |
| d13 INT hash with two children | p0 contains 3; p1 contains 1,2 |
| d13 INT hash with three children | p0 contains 2; p1 is empty; p2 contains 1,3 |

The [range manual](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/sql/partition.rst#L64) defines continuous half-open intervals.
The [source equality rule](https://github.com/CUBRID/cubrid/blob/d13aebf6428a68c2852d16df143d1da203d86dea/src/query/partition.c#L1454) requires `min <= key < max`.
The [child access contract](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/sql/partition.rst#L315) supports ordinary child names and `PARTITION(name)` as single-child SQL access.
ONLY is also supported; the old bound mismatch supplies no evidence of broader scans.
These are logical SQL contracts, separate from the stopped root-OID-to-child-class/HFID physical proof.

The INT hash oracle uses [unsigned 32-bit mixing](https://github.com/CUBRID/cubrid/blob/d13aebf6428a68c2852d16df143d1da203d86dea/src/base/memory_hash.c#L2621) before modulo.
The independently calculated hashes for 1,2,3 are 663891101, 3329832309, and 2278584254.
Ordered child creation, catalog serialization, heap loading, and the retained order after COALESCE establish the pN mapping for d13.
No expected destination comes from observed row placement.
Equality and selective IN probes compare full values before and after resizing, with documented `USING INDEX NONE` for sequential access.
Their SQL result contract does not claim an executed-plan count of skipped partitions.
The raw output records routing, actual owner, and attribute-state defects separately.

The copied configuration has no global `vacuum_disable` setting; the d13 default is false.
The corrected partition helper saves the exact current configuration, sets `vacuum_disable=yes` before every stopped SA diagnostic boot, and restores byte-identical prior configuration before C/S restart.
The correction does not claim that historical unguarded diagnostics were vacuum-free.
All 13 partition cases must rerun because they execute the changed helper: 26 independent DEFAULT/FORCE_OUTLINE invocations.
The six schema cases and retained owner case, the four lifecycle cases, SQL5, and the five retained C++ DDL cases keep only their unchanged executed-input scope.
The old aggregate 20-case receipt and its copied all-common-file manifest do not qualify the corrected helper.

The independent oracle notes have SHA-256 `063b584a20b5b50821d4ce5b95126889fb5766e79639d459d527431e82df9b4e`.
The complete phase audit and preserved pre-correction receipts are under the raw `range-correction` directory.
The final committed correction ran as `r3` at private `58280d595ffa1712643a11382aa83e7f0b79f658`.
Its exact d13 source checkout is `/home/vimkim/gh/cb/work456-ticket08-rerun-source`, separate from the later integration branch.
The helper SHA-256 is `2d192e0fa398f77060312959bccca2913151a810db8c4b72376e111f853d6ae4`; the capture wrapper is `b2df7207dfaff06bf4f149d354fa5bad53387a5d78bcce856627a4018d4bd644`.
The unchanged shared reader is `ec243112a0206157c119eb8b85015f375ecd9ffde86cc883480487d83ed0b058`.
The frozen independent oracle is raw `range-correction/oracle-audit.json`, SHA-256 `b9c3e9c1fc1f8bca13ceb2027d7109fd9ead65681b804c90c2f9fa08543041b1`.
The pre-retention `9111148b` oracle is preserved only as `range-correction/r3-before-retention-oracle-audit.json` and grants no final runtime credit.

`r3` selected, dispatched, and finished exactly the same 13 cases, with both policies: 26 invocations, no skip, all declared phases and owned cleanup.
All 48 physical snapshots qualified, including 48 preboot vacuum guards and exact configuration restores; no observer error or setup gap remains in this invocation.
The native runner returned 0 and the verifier returned 1: all 13 case verdicts remain FAIL in 400.372325 seconds.
Completed observations do not turn those failing contracts into passing partition coverage.
The XML SHA-256 is `dd50f37e0fa7487331a130b2c1d38e068a14b73df462aefab896de416fedfbba`.
The expected, dispatched, and finished lists share SHA-256 `e00f82d51c150e25492f3a8866c70e801ddbdb5cedb28ef58fe39f51ea19b11a`.

| Corrected contract | Actual `r3` evidence |
| --- | --- |
| Named-child membership and complete child union | 104 membership checks and 46 complete logical union checks pass; zero failures |
| Complete ordinary values | All 50 pre/post snapshot models pass, including the unpartitioned prestate |
| Hash equality/IN reads | All 40 full-value probes pass with the independent d13 destination map |
| Actual raw destination | All 144 current rows map to their intended actual class/HFID; zero raw routing defects |
| Actual attribute bytes and owner | 144 complete payload comparisons; 82 actual chain-owner mismatch observations and 14 separately recorded storage-state observations |

The 14 storage-state observations are not inferred from ownership metadata.
The exact current `REC_HOME` flags and actual VOT entries are clear/inline where the independent model requires OOS.
The only large attribute is 5,107 or 5,133 payload bytes, serialized as 5,112 or 5,140 bytes, independently above the accepted 4,060-byte target.
Ordinary destination reserialization must apply the normative demotion rule; raw reinsertion into another heap requires Expand under specification §3.
Complete values remain equal and the recorded DEFAULT/FORCE_OUTLINE policies remain unchanged.
The breakdown is COALESCE row 3 under both policies (2); REMOVE rows 2 and 3 under both policies (4); range/list SPLIT row 2 under both policies (4); and range/list MERGE row 2 under both policies (4).
For example, COALESCE row 3 moves from the correct p2 current OID `(1,1025,2)` with flags 9 and a 24-byte stub to correct p0 OID `(1,769,2)` with flags 0 and a 5,140-byte inline field.
Its full payload SHA-256 remains `8239374ab423f18cfb8b420d4a08559c2a6b9db7b7f242c7432d7141a0ea274e`.
That is a storage-state failure with passing routing and full values, not another chain-owner count.
The owner failures remain linked to the separate [PR7927](https://github.com/CUBRID/cubrid/pull/7927)/Work393 repair scope; these observations do not establish its internal cause or integrate any repair.

The intermediate `r2` run completed 13 cases, 26 policy invocations, and 48 raw snapshots in 415.818780 seconds.
Its supplementary `direct_child_identity` comparison incorrectly searched a numeric subsequence in an array of row pairs with `jq index($pair)`.
That built an empty subset and produced 46 harness failures; those failures receive no engine attribution.
The corrected helper uses exact pair membership, compares the complete ordinary child pair union with the root logical identities, and leaves physical membership to the stopped raw class/HFID proof.
The complete root value and physical population queries have no child ID filter, so an extra row outside a child query's selected IDs is still rejected.
Pure controls cover 23 supported child phases, 145 invalid child populations/metadata, and positive plus extra/missing/duplicate/wrong-value root populations.

The `r2` independent raw classification found zero routing defects and zero ordinary child membership failures.
It recorded 82 actual chain-owner defect observations and 14 attribute-state observations, counted separately from the 46 harness failures.
The 14 storage-state observations are COALESCE row 3 twice; REMOVE rows 2 and 3 under both policies four times; range/list SPLIT row 2 four times; and range/list MERGE row 2 four times.
These are repeated observations across fixtures and phases, not 96 distinct engine issues.
The stopped diagnostic and page-frame inputs were not retained in `r2`, so the final run adds replayable input retention and supersedes that receipt.

The partition-only retention wrapper delegates to the byte-identical qualified reader.
It records the exact frames returned by that reader's existing page reads, with source volume, VPID, byte offset, and SHA-256.
It preserves stopped heaphex, filetable and file diagnostics, complete root scan and retirement ledger, current row/model inputs, phase SQL/policy observations, guarded configuration, and reader code before cleanup.
Each phase writes a compressed archive under the owned installation's `oos08_evidence` directory.
Offline replay uses only those inputs and frames and never opens the original database volume.
Pure controls prove byte-identical stdout, stderr, and exit status for reader results 0, 1, and 2; changed or missing frames/dumps are rejected.
Archive-only replay also succeeds after the original volume and diagnostic paths are removed.
All five added Python testcase files pass a Python 3.6 AST/API inspection; no actual Python 3.6 interpreter execution is claimed.
The shared reader remains unchanged, preserving the separate schema and lifecycle executed-input scope.
The six schema cases and retained owner case reuse only `final01` public `a55886659` / private `754defba5` input closures.
The four lifecycle cases reuse only `lifecycle-final01` private `9b4ec150e`; SQL5 reuses `final-sql01` public `a55886659` / private `9b4ec150e`.
Before the unrelated integration merges, only the unexecuted partition module differed in those two broad common-file manifests; no SQL5 input differed.
After the merges, the unexecuted `snapshot_controller.sh` also differs, and the corrected run's broad manifest additionally includes an unrelated change to `oos15_notify.sh`.
The final closure audit verifies all 29 executed corrected-partition dependencies byte-for-byte and excludes those unrelated modules explicitly.
The later native partition receipt grants no new replay or passing coverage to those earlier invocations.

The first corrected attempt, `corrected-partitions01`, failed server startup before loading the partition helper.
Its five dispatched failures and interrupted selection receive no partition conformance credit.
The exact `CUBRID_TMP` was 83 bytes: the PL socket fit at 105 bytes including NUL, but the server-to-master socket required 113 bytes with the retained namespace PID 11508.
The [server handshake path](https://github.com/CUBRID/cubrid/blob/d13aebf6428a68c2852d16df143d1da203d86dea/src/connection/master_connector.cpp#L451) appends `cubrid_tcp_setup_server<PID>`.
The [socket setup](https://github.com/CUBRID/cubrid/blob/d13aebf6428a68c2852d16df143d1da203d86dea/src/connection/tcp.c#L881) passes the complete pathname length to `bind`; Linux's `sun_path` field holds 108 bytes.
The retained server stderr contains only repeated master-reconnect messages; the master stdout and stderr are empty.
The native containment cleanup left zero owned processes, an empty registry, and no database assets.
The retry runner now rejects oversized master, PL, server, and csql socket paths before boot for both policies and a maximum ten-digit PID.
This is an attempt setup failure, separate from any OOS ownership verdict.

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

The historical `final01` shell selection contains exactly 20 cases: 6 schema PASS, 14 partition FAIL, and zero skips in 809.274748 seconds.
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
| `r3`, corrected shell 13 | 0 PASS, 13 FAIL, 0 skip | 400.372325 s | Governs all 13 corrected partition cases; 26 policy invocations, 48 retained/replayed raw snapshots |
| `final01`, historical shell 20 | 6 PASS, 14 FAIL, 0 skip | 809.274748 s | Reuse only six unchanged schema cases and retained owner; all 13 partition-helper cases are superseded |
| `lifecycle-final01`, shell 4 | 0 PASS, 4 FAIL, 0 skip | 326.312484 s | Range/list ADD/DROP and PROMOTE, both policies, all eight invocations reached every declared phase and cleanup |
| `final-sql01`, JDBC 5 | 5 PASS, 0 FAIL, 0 skip | 51.981954 s | `schema`, `schema_materialize`, `schema_rewrites`, `partition`, and `partition_routing`; logical invocation only |
| `control-flag01`, shell 1 | 1 deliberate FAIL | 9.013243 s | Copied corpus changes only row 2's expected `has_oos` from true to false; actual stored flags reject it |
| `control-payload01`, shell 1 | 1 deliberate FAIL | 10.094665 s | Copied model changes only expected `c3` bytes to `c4`; complete raw VARBIT comparison rejects it |

Both controls have one case, zero skips, and owned cleanup.
Each native runner returned `0`; both independent verifiers returned `1` and retained the failure.
The controls intentionally stop at the changed assertion and receive no later-phase credit.
The unmodified attribute CS case passed in `final01` before these disposable corpora were used.
No tracked test or expected answer was modified for a control.

Across the two original shell selections, all 38 new mode/policy invocations mechanically reached all declared phases and cleanup.
This does not validate the seven inconsistent range routing oracles; the corrected partition receipt supersedes that scope.
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
`r3` actual PID/IPC/mount/network identities are `4026537061`/`4026537060`/`4026537059`/`4026537062`; all differ from the captured host identities.
Every policy logs actual master port 1568, broker master SHM 1568, and broker ports/application SHM 10090 and 13091.
These actual copied settings are distinct from the auxiliary worktree's allocation labels 41102/41103.
The actual native slot's 38 engine/library/VM artifacts match immutable provider14, independently of the host copied-prefix view.
The final short TMP is 63 bytes, with maximum master/PL/server/csql socket lengths 76/85/98/96 including NUL and a ten-digit PID.

The native slot's CUBRID filesystem is a separate mount view.
The exporter pins its live source evidence directory, reads completed archives through that directory FD, validates gzip/tar and every manifest hash, and copies them to `r3/retained-archives` before namespace teardown.
All 48 archive hashes match the hashes printed by the native cases.
They contain 54 actual 16 KiB page frames (884,736 bytes), in 2,647,062 compressed bytes with diagnostics and code.
After cleanup, all original database/volume paths are absent and all 48 archives replay with byte-identical stdout, stderr, and exit status.
Four disposable copies of actual product evidence reject changed/missing frames and heap dumps; retained archives remain unchanged.
Replay entrypoint: `python3 code/oos08_partition_capture.py --replay EXTRACTED_ARCHIVE_DIRECTORY`.
`r3/offline-replay-receipt.json` records exact archive, manifest, and replay identities.
The merger independently replayed all 48 archives and separately decoded 144 heap records, 82 complete chains, 62 complete inline values, and 60 owning-file descriptors from 48 allocation dumps.
Its independent raw audit is `independent-r3-raw-audit.json`, SHA-256 `041f286a87c661f8fa64c321821d36cb7e4cafb9cc18c6a0d477815642cb3ece`.
It confirms zero membership/routing defects, 82 owner observations, and the same 14 storage-state observations; destination integration remains the coordinator's separate review.
The exporter closes its source directory FD after the 48 copies; no native process or resource lease remains.
The SQL registry retains only its normal comment header.
The six sampled binaries in every final attempt match the immutable ticket 14 d13 provider exactly.

The handoff source branch includes integration `9c21a1ae701c847803690bd1c567b74f0d0918a9`.
The public task branch includes integration `ae5714ab4689d01adf243c92426d9efd2b48b8a6` at `59f077ad4e4e4fac8120604105d80b8e7c48cff5`.
The private task branch includes integration `a5a886bd762f6469281b489ecad3641de1377f86` at `304ca9f3639a41fdc44851811eab2e513552d67d`.
The corrected runtime remains frozen at `58280d595`; later merges bring unrelated tickets without transferring their execution credit.
The executed dependency closure remains byte-identical after these merges; unrelated changed common modules receive no ticket 08 execution credit.
These merge identities do not transfer d13 execution credit to another source installation.
The coordinator's final combined qualification remains separate.
There is no ticket 08 engine change.

Earlier `probe01`–`probe04`, `green01`–`green04`, and `lifecycle-probe01` remain implementation history.
They include initial unqualified class-name probes, the range-bound mismatch, helper initialization corrections, and the initial diagnostic-error classification.
Their passes do not substitute for the final frozen selections.
The exact revision, environment, configuration, command, case list, inputs, raw native results, independent audits, and cleanup receipt remain in the raw attempt root.
The raw attempt root is `/home/vimkim/temp/work456-implementation/ticket08`.
Large logs, copied installations, and generated intermediate inventories remain outside Git.
The report and this ticket directory's README are the only selected documentation changes.

No source/TC push, CI trigger, JIRA edit, TC PR action, or destination integration occurred during this implementation.
Performance and HA remain deferred.
