# 10. Source map and evidence ledger

Claims below connect the narrative and diagrams to exact source intervals. All unmarked source intervals refer to the pinned head. History claims explicitly identify the base. Source facts describe code; inferences explain consequences; runtime observations apply to the recorded binary/input; unknowns name missing evidence.

Head: `b871ea386d2c5419b7abae07dda58b9b7f36377a`. Base: `2940b1cfbc3c2d4d0fac3f9244a960350debd380`. Full SHA links remain usable after the PR changes. The captured source intervals are also in `evidence/source-excerpts.json` for offline inspection.

## Supplemental reading

- OOS normative context: `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md`, last-updated label 2026-08-28. Its target policy differs from the pinned layout code; see chapter 2.
- [CUBRID manual, partitioning](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/sql/partition.rst#L1-L120): local checkout at `3b6ae97bfbdc664b010ffa933ded5a05b291ae03`, lines 1–120; used for SQL concepts, not proof of OOS implementation.
- [Earlier PR report](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27089/CBRD-27089-oos-chain-owner-b871ea3_codex.md): historical broader tests and issue narrative; no new CI or backup claim.
- Local issue draft: `/home/vimkim/gh/my-cubrid-jira/issues/CBRD-27089-partition-oos-owner_b871ea3_codex.md`; intent and prior results.

## Claims

<a id="C-001"></a>
### C-001 · source_fact

The selected class determines the heap whose OOS file receives serialized values.

- [src/storage/heap_oos.cpp:631–660](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_oos.cpp#L631-L660) — `heap_oos_insert_serialized_values`
- [src/storage/heap_file.c:199–209](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L199-L209) — `HEAP_HDR_STATS`
- [src/storage/heap_file.c:12759–12768](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12759-L12768) — `heap_attrinfo_insert_to_oos`

<a id="C-002"></a>
### C-002 · source_fact

Before the PR ordinary serialization preceded lower-locator partition routing.

- [src/transaction/locator_sr.c:7692–7725](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/transaction/locator_sr.c#L7692-L7725) — `locator_attribute_info_force` **BASE history**
- [src/storage/heap_file.c:12724–12735](https://github.com/CUBRID/cubrid/blob/2940b1cfbc3c2d4d0fac3f9244a960350debd380/src/storage/heap_file.c#L12724-L12735) — `heap_attrinfo_insert_to_oos` **BASE history**
- [src/transaction/locator_sr.c:4984–4996](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L4984-L4996) — `locator_insert_force`

<a id="C-003"></a>
### C-003 · source_fact

The added regression checks logical equality and root/p0/p1 OOS ownership.

- [unit_tests/oos/sql/test_oos_sql_show.cpp:387–456](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/unit_tests/oos/sql/test_oos_sql_show.cpp#L387-L456) — `PartitionedForceOutlineStoresOosInPrunedHeap`
- [unit_tests/oos/sql/test_oos_sql_show.cpp:47–67](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/unit_tests/oos/sql/test_oos_sql_show.cpp#L47-L67) — `show_heap_oos_query`
- [unit_tests/oos/sql/test_oos_sql_show.cpp:194–214](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/unit_tests/oos/sql/test_oos_sql_show.cpp#L194-L214) — `OosSqlShow fixture`

<a id="C-004"></a>
### C-004 · source_fact

Partition routing evaluates a partition key and returns child class and heap identities.

- [src/query/partition.c:3467–3581](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/partition.c#L3467-L3581) — `partition_find_partition_for_record`
- [src/query/partition.c:3605–3689](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/partition.c#L3605-L3689) — `partition_prune_insert`

<a id="C-005"></a>
### C-005 · source_fact

Heap records use slotted pages; OID, VPID, VFID and HFID identify different storage objects.

- [src/storage/slotted_page.h:85–91](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/slotted_page.h#L85-L91) — `SPAGE_SLOT`
- [src/storage/storage_common.h:190–231](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/storage_common.h#L190-L231) — `HFID and RECDES`
- [src/compat/dbtype_def.h:956–974](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/compat/dbtype_def.h#L956-L974) — `VPID and VFID`
- [src/compat/dbtype_def.h:1040–1055](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/compat/dbtype_def.h#L1040-L1055) — `OID`

<a id="C-006"></a>
### C-006 · source_fact

The partitioned root holds no row data on the traced UPDATE path; child partitions supply heap identities.

- [src/query/partition.c:3755–3777](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/partition.c#L3755-L3777) — `partition_prune_update`
- [src/query/partition.c:3550–3570](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/partition.c#L3550-L3570) — `partition_find_partition_for_record`

<a id="C-007"></a>
### C-007 · source_fact

Attribute state, record descriptors and copy-area memory have distinct roles.

- [src/storage/storage_common.h:220–231](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/storage_common.h#L220-L231) — `RECDES`
- [src/transaction/locator_sr.c:7490–7562](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L7490-L7562) — `locator_allocate_copy_area_by_attr_info`
- [src/storage/heap_file.c:13317–13359](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13317-L13359) — `heap_attrinfo_transform_to_disk_internal`

<a id="C-008"></a>
### C-008 · source_fact

The allocator dispatches probe first, then explicit-owner final mode, then LOB-specific ordinary mode.

- [src/transaction/locator_sr.c:7490–7562](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L7490-L7562) — `locator_allocate_copy_area_by_attr_info`

<a id="C-009"></a>
### C-009 · source_fact

OOS uses a head-OID/length stub, attribute offset flag, record flag and linked chunk headers.

- [src/base/object_representation.h:448–468](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/base/object_representation.h#L448-L468) — `OR_OOS_INLINE_SIZE`
- [src/base/object_representation_constants.h:159–174](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/base/object_representation_constants.h#L159-L174) — `OR_RECORD_FLAG_HAS_OOS`
- [src/storage/oos_file.hpp:28–34](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/oos_file.hpp#L28-L34) — `oos_record_header`
- [src/storage/heap_file.c:13088–13122](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13088-L13122) — `heap_attrinfo_transform_variable_to_disk`
- [src/storage/heap_file.c:12869–12910](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12869-L12910) — `heap_attrinfo_transform_header_to_disk`

<a id="C-010"></a>
### C-010 · source_fact

The transformer rejects OOS plus bigone before OOS insertion.

- [src/storage/heap_file.c:13386–13410](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13386-L13410) — `heap_attrinfo_transform_to_disk_internal`

<a id="C-011"></a>
### C-011 · inference

Logical SELECT can succeed despite a wrong heap-owner association.

- [src/storage/heap_file.c:10452–10505](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L10452-L10505) — `heap_attrvalue_read_oos_inline`
- [src/storage/heap_oos.cpp:631–660](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_oos.cpp#L631-L660) — `heap_oos_insert_serialized_values`

Rationale: The read uses the parsed physical head OID directly, while write ownership is selected by class-to-heap lookup. A wrong owner can leave a readable physical chain. Earlier reports corroborate this but the old binary was not rerun.

<a id="C-012"></a>
### C-012 · source_fact

At the pinned head, missing-file success and lookup failure take different branches in the vacuum helper.

- [src/storage/heap_file.c:12433–12543](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12433-L12543) — `heap_oos_find_vfid`
- [src/query/vacuum_oos.cpp:401–446](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/vacuum_oos.cpp#L401-L446) — `vacuum_oos_find_vfid_for_heap_record`

<a id="C-013"></a>
### C-013 · unknown

The full current-server failure path of deliberately inconsistent ownership has not been reproduced here.


Resolve by: Use an owned SERVER_MODE database and a controlled test seam to construct wrong ownership, then trace lookup result, VFID and cleanup. Do not infer current abort behavior from old comments.

<a id="C-014"></a>
### C-014 · source_fact

The pinned layout code still uses DB_PAGESIZE/4; this differs from the loaded normative physical-capacity target.

- [src/storage/heap_file.c:12365–12430](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12365-L12430) — `heap_attrinfo_determine_disk_layout`

<a id="C-015"></a>
### C-015 · source_fact

The new wrappers implement ordinary/probe/final modes; final mode assumes a previous successful probe.

- [src/storage/heap_file.c:12790–12854](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12790-L12854) — `transform wrappers`
- [src/storage/heap_file.c:13317–13356](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13317-L13356) — `heap_attrinfo_transform_to_disk_internal`

<a id="C-016"></a>
### C-016 · source_fact

The locator shares INSERT/UPDATE preparation, performs suppressed early routing when needed, and retains the ordinary no-demotion path.

- [src/transaction/locator_sr.c:7599–7875](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L7599-L7875) — `locator_attribute_info_force`
- [src/query/query_executor.c:13620–13644](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/query_executor.c#L13620-L13644) — `qexec_execute_insert`

<a id="C-017"></a>
### C-017 · source_fact

Lower locators still route, lock and write; cross-partition UPDATE can move the record.

- [src/transaction/locator_sr.c:4984–5079](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L4984-L5079) — `locator_insert_force`
- [src/transaction/locator_sr.c:5980–6050](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L5980-L6050) — `locator_update_force`

<a id="C-018"></a>
### C-018 · inference

Early and final routing should agree because the logical partition values are preserved across serialization modes.

- [src/query/partition.c:3496–3514](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/partition.c#L3496-L3514) — `partition_find_partition_for_record`
- [src/storage/heap_file.c:13339–13354](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13339-L13354) — `increment pre-seeding`
- [src/transaction/locator_sr.c:7719–7799](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L7719-L7799) — `locator_attribute_info_force`

Rationale: The same prepared DB_VALUEs underlie the inline probe and final image, and routing reads logical values. This supports agreement but is not exhaustive concurrency validation.

<a id="C-019"></a>
### C-019 · source_fact

Partition selection reads through root representation and adjusts the chosen child representation.

- [src/query/partition.c:3467–3581](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/partition.c#L3467-L3581) — `partition_find_partition_for_record`

<a id="C-020"></a>
### C-020 · source_fact

Ordinary suppression returns inline size before sorting and selection; oversized rows without eligible candidates need not demote.

- [src/storage/heap_file.c:12312–12430](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12312-L12430) — `heap_attrinfo_determine_disk_layout`

<a id="C-021"></a>
### C-021 · source_fact

FORCE_OUTLINE suppression reports a hypothetical demotion and continues before mutating selection/payload/has_oos.

- [src/storage/heap_file.c:12338–12363](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12338-L12363) — `heap_attrinfo_determine_disk_layout`

<a id="C-022"></a>
### C-022 · source_fact

Layout precedes OOS insertion, and OOS insertion precedes the buffer-writing retry loop.

- [src/storage/heap_file.c:13317–13450](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13317-L13450) — `heap_attrinfo_transform_to_disk_internal`
- [src/storage/heap_file.c:12632–12776](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12632-L12776) — `OOS request preparation and insertion`

<a id="C-023"></a>
### C-023 · source_fact

The second PR commit added the forced-loop suppression and its small-value regression.

- [src/storage/heap_file.c:12343–12352](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12343-L12352) — `FORCE_OUTLINE suppression`
- [unit_tests/oos/sql/test_oos_sql_show.cpp:387–456](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/unit_tests/oos/sql/test_oos_sql_show.cpp#L387-L456) — `PartitionedForceOutlineStoresOosInPrunedHeap`

<a id="C-024"></a>
### C-024 · source_fact

A per-call set prevents repeated fixed increments; final mode seeds a new set after a successful probe.

- [src/storage/heap_file.c:12964–13035](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12964-L13035) — `heap_attrinfo_transform_fixed_to_disk`
- [src/storage/heap_file.c:13339–13354](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13339-L13354) — `heap_attrinfo_transform_to_disk_internal`

<a id="C-025"></a>
### C-025 · source_fact

Both inline and OOS serializers use the LOB-written state guard, which survives in attr_info across passes.

- [src/storage/heap_file.c:12545–12647](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12545-L12647) — `heap_attrinfo_dbvalue_to_recdes and serialize helper`
- [src/storage/heap_file.c:13123–13201](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13123-L13201) — `heap_attrinfo_transform_variable_to_disk`

<a id="C-026"></a>
### C-026 · source_fact

REPLACE and ODKU use suppressed temporary key images while retaining their duplicate-search behavior and LOB modes.

- [src/query/query_executor.c:11920–12143](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/query_executor.c#L11920-L12143) — `qexec_remove_duplicates_for_replace`
- [src/query/query_executor.c:12158–12373](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/query_executor.c#L12158-L12373) — `qexec_oid_of_duplicate_key_update`

<a id="C-027"></a>
### C-027 · source_fact

Copy-area cleanup is distinct from persistent-chain lifetime; the new final pass does not create a transaction boundary.

- [src/transaction/locator_sr.c:7747–7875](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L7747-L7875) — `locator_attribute_info_force`
- [src/storage/heap_oos.cpp:674–701](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_oos.cpp#L674-L701) — `heap_oos_delete_unreferenced contract`
- [src/storage/heap_file.c:12727–12776](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12727-L12776) — `heap_attrinfo_insert_to_oos`

<a id="C-028"></a>
### C-028 · inference

The OOS partition path adds serialization and routing work and can require a large temporary inline image.

- [src/transaction/locator_sr.c:7710–7778](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L7710-L7778) — `locator_attribute_info_force`
- [src/storage/heap_file.c:13412–13445](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13412-L13445) — `buffer growth loop`

Rationale: Two explicit transformations and an early pruning call add work. The probe retains logical inline payload bytes. No latency or memory benchmark was performed.

<a id="C-029"></a>
### C-029 · source_fact

The pinned PR changes six implementation/header/test files, with 306 additions and 23 deletions.

- [src/storage/heap_file.h:505–518](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.h#L505-L518) — `new declarations`
- [src/transaction/locator_sr.h:83–90](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.h#L83-L90) — `allocator declaration`

<a id="C-030"></a>
### C-030 · source_fact

The selected regression target uses GoogleTest and the standalone engine.

- [unit_tests/oos/sql/CMakeLists.txt:21–56](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/unit_tests/oos/sql/CMakeLists.txt#L21-L56) — `SA test targets`
- [unit_tests/oos/sql/test_oos_sql_common.hpp:51–86](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/unit_tests/oos/sql/test_oos_sql_common.hpp#L51-L86) — `SqlServerEnv`

<a id="C-031"></a>
### C-031 · runtime_observation

The existing recorded regression binary passed the selected test in a fresh private SA database.

Runtime check R-001: `evidence/regression.json`.


<a id="C-032"></a>
### C-032 · unknown

Runtime validation of the full UPDATE/LOB/increment/duplicate/vacuum/crash matrix remains open.


Resolve by: Add/run the distinct focused experiments listed in chapter 7 in owned environments, recording actual state and ownership rather than only SQL equality.

<a id="C-033"></a>
### C-033 · inference

The interface is a stateful caller protocol that could be made more explicit in a future design.

- [src/storage/heap_file.c:12796–12831](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12796-L12831) — `probe and final wrappers`
- [src/transaction/locator_sr.c:7513–7533](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L7513-L7533) — `mode dispatch`

Rationale: Mode depends on nullable pointers and prior mutation. A mode/prepared-state type is a possible design improvement, not implemented in this PR.

<a id="C-034"></a>
### C-034 · source_fact

Lazy OOS file creation uses a system operation with encryption policy, heap-header logging and page cleanup.

- [src/storage/heap_file.c:12446–12542](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12446-L12542) — `heap_oos_find_vfid`

<a id="C-101"></a>
### C-101 · source_fact

REPLACE allocates a mode selector. Exact changes and commentary are in H01 of chapter 6.

- [src/query/query_executor.c:11937–11943](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/query_executor.c#L11937-L11943) — `REPLACE allocates a mode selector`

<a id="C-102"></a>
### C-102 · source_fact

REPLACE suppresses discarded-image OOS writes. Exact changes and commentary are in H02 of chapter 6.

- [src/query/query_executor.c:11952–11962](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/query_executor.c#L11952-L11962) — `REPLACE suppresses discarded-image OOS writes`

<a id="C-103"></a>
### C-103 · source_fact

ODKU allocates its mode selector. Exact changes and commentary are in H03 of chapter 6.

- [src/query/query_executor.c:12175–12181](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/query_executor.c#L12175-L12181) — `ODKU allocates its mode selector`

<a id="C-104"></a>
### C-104 · source_fact

ODKU obtains an inline key image. Exact changes and commentary are in H04 of chapter 6.

- [src/query/query_executor.c:12195–12205](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/query_executor.c#L12195-L12205) — `ODKU obtains an inline key image`

<a id="C-105"></a>
### C-105 · source_fact

Declare layout mode and verdict. Exact changes and commentary are in H05 of chapter 6.

- [src/storage/heap_file.c:694–703](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L694-L703) — `Declare layout mode and verdict`

<a id="C-106"></a>
### C-106 · source_fact

Declare the internal transformation protocol. Exact changes and commentary are in H06 of chapter 6.

- [src/storage/heap_file.c:783–790](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L783-L790) — `Declare the internal transformation protocol`

<a id="C-107"></a>
### C-107 · source_fact

Document hypothetical versus actual layout. Exact changes and commentary are in H07 of chapter 6.

- [src/storage/heap_file.c:12299–12309](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12299-L12309) — `Document hypothetical versus actual layout`

<a id="C-108"></a>
### C-108 · source_fact

Match the layout definition to its declaration. Exact changes and commentary are in H08 of chapter 6.

- [src/storage/heap_file.c:12311–12320](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12311-L12320) — `Match the layout definition to its declaration`

<a id="C-109"></a>
### C-109 · source_fact

Clear the verdict before planning. Exact changes and commentary are in H09 of chapter 6.

- [src/storage/heap_file.c:12325–12334](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12325-L12334) — `Clear the verdict before planning`

<a id="C-110"></a>
### C-110 · source_fact

Stop FORCE_OUTLINE selection inside a probe. Exact changes and commentary are in H10 of chapter 6.

- [src/storage/heap_file.c:12343–12357](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12343-L12357) — `Stop FORCE_OUTLINE selection inside a probe`

<a id="C-111"></a>
### C-111 · source_fact

Return full inline size for an ordinary probe. Exact changes and commentary are in H11 of chapter 6.

- [src/storage/heap_file.c:12387–12405](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12387-L12405) — `Return full inline size for an ordinary probe`

<a id="C-112"></a>
### C-112 · source_fact

Carry an owner without replacing attribute metadata. Exact changes and commentary are in H12 of chapter 6.

- [src/storage/heap_file.c:12711–12725](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12711-L12725) — `Carry an owner without replacing attribute metadata`

<a id="C-113"></a>
### C-113 · source_fact

Select the actual OOS owner at publication. Exact changes and commentary are in H13 of chapter 6.

- [src/storage/heap_file.c:12759–12765](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12759-L12765) — `Select the actual OOS owner at publication`

<a id="C-114"></a>
### C-114 · source_fact

Expose ordinary, probe and final wrappers. Exact changes and commentary are in H14 of chapter 6.

- [src/storage/heap_file.c:12790–12834](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12790-L12834) — `Expose ordinary, probe and final wrappers`

<a id="C-115"></a>
### C-115 · source_fact

Preserve the except-LOB entry point. Exact changes and commentary are in H15 of chapter 6.

- [src/storage/heap_file.c:12848–12855](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12848-L12855) — `Preserve the except-LOB entry point`

<a id="C-116"></a>
### C-116 · source_fact

Specify the internal caller obligations. Exact changes and commentary are in H16 of chapter 6.

- [src/storage/heap_file.c:13306–13322](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13306-L13322) — `Specify the internal caller obligations`

<a id="C-117"></a>
### C-117 · source_fact

Derive suppression and allocate an index variable. Exact changes and commentary are in H17 of chapter 6.

- [src/storage/heap_file.c:13324–13331](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13324-L13331) — `Derive suppression and allocate an index variable`

<a id="C-118"></a>
### C-118 · source_fact

Reconstruct the increment guard for the second pass. Exact changes and commentary are in H18 of chapter 6.

- [src/storage/heap_file.c:13339–13357](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13339-L13357) — `Reconstruct the increment guard for the second pass`

<a id="C-119"></a>
### C-119 · source_fact

Pass mode and verdict into layout calculation. Exact changes and commentary are in H19 of chapter 6.

- [src/storage/heap_file.c:13365–13372](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13365-L13372) — `Pass mode and verdict into layout calculation`

<a id="C-120"></a>
### C-120 · source_fact

Forward the selected owner only when inserting OOS. Exact changes and commentary are in H20 of chapter 6.

- [src/storage/heap_file.c:13401–13407](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L13401-L13407) — `Forward the selected owner only when inserting OOS`

<a id="C-121"></a>
### C-121 · source_fact

Keep the unit-test bridge on its original owner. Exact changes and commentary are in H21 of chapter 6.

- [src/storage/heap_file.c:28525–28530](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L28525-L28530) — `Keep the unit-test bridge on its original owner`

<a id="C-122"></a>
### C-122 · source_fact

Publish the two transformation interfaces. Exact changes and commentary are in H22 of chapter 6.

- [src/storage/heap_file.h:507–518](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.h#L507-L518) — `Publish the two transformation interfaces`

<a id="C-123"></a>
### C-123 · source_fact

Extend the copy-area adapter. Exact changes and commentary are in H23 of chapter 6.

- [src/transaction/locator_sr.c:7475–7492](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L7475-L7492) — `Extend the copy-area adapter`

<a id="C-124"></a>
### C-124 · source_fact

Dispatch probe before owner before LOB mode. Exact changes and commentary are in H24 of chapter 6.

- [src/transaction/locator_sr.c:7510–7526](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L7510-L7526) — `Dispatch probe before owner before LOB mode`

<a id="C-125"></a>
### C-125 · source_fact

Orchestrate probe, early routing and final serialization. Exact changes and commentary are in H25 of chapter 6.

- [src/transaction/locator_sr.c:7708–7770](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L7708-L7770) — `Orchestrate probe, early routing and final serialization`

<a id="C-126"></a>
### C-126 · source_fact

Keep MVCC reevaluation on its existing path. Exact changes and commentary are in H26 of chapter 6.

- [src/transaction/locator_sr.c:13851–13857](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.c#L13851-L13857) — `Keep MVCC reevaluation on its existing path`

<a id="C-127"></a>
### C-127 · source_fact

Expose the adapter’s expanded signature. Exact changes and commentary are in H27 of chapter 6.

- [src/transaction/locator_sr.h:83–90](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/transaction/locator_sr.h#L83-L90) — `Expose the adapter’s expanded signature`

<a id="C-128"></a>
### C-128 · source_fact

Include the string type directly. Exact changes and commentary are in H28 of chapter 6.

- [unit_tests/oos/sql/test_oos_sql_show.cpp:21–27](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/unit_tests/oos/sql/test_oos_sql_show.cpp#L21-L27) — `Include the string type directly`

<a id="C-129"></a>
### C-129 · source_fact

Copy and normalize the diagnostic name. Exact changes and commentary are in H29 of chapter 6.

- [unit_tests/oos/sql/test_oos_sql_show.cpp:155–192](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/unit_tests/oos/sql/test_oos_sql_show.cpp#L155-L192) — `Copy and normalize the diagnostic name`

<a id="C-130"></a>
### C-130 · source_fact

Check value and all three heap owners. Exact changes and commentary are in H30 of chapter 6.

- [unit_tests/oos/sql/test_oos_sql_show.cpp:384–458](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/unit_tests/oos/sql/test_oos_sql_show.cpp#L384-L458) — `Check value and all three heap owners`
