"""Audited source claims. Ranges refer to HEAD unless evidence says otherwise."""
def source(path, start, end, symbol='', kind='source', revision=None):
    result = dict(type=kind, path=path, start_line=start, end_line=end, symbol=symbol)
    if revision:
        result['revision'] = revision
    return result

H = 'src/storage/heap_file.c'
L = 'src/transaction/locator_sr.c'
P = 'src/query/partition.c'
Q = 'src/query/query_executor.c'
T = 'unit_tests/oos/sql/test_oos_sql_show.cpp'
BASE = '2940b1cfbc3c2d4d0fac3f9244a960350debd380'

def claim(number, text, evidence, kind='source_fact', **extra):
    return dict(id=f'C-{number:03}', text=text, kind=kind,
                confidence='medium' if kind in ('inference','unknown') else 'high', evidence=evidence, **extra)

CLAIMS = [
claim(1,'The selected class determines the heap whose OOS file receives serialized values.',[source('src/storage/heap_oos.cpp',631,660,'heap_oos_insert_serialized_values'),source(H,199,209,'HEAP_HDR_STATS'),source(H,12759,12768,'heap_attrinfo_insert_to_oos')]),
claim(2,'Before the PR ordinary serialization preceded lower-locator partition routing.',[source(L,7692,7725,'locator_attribute_info_force','history',BASE),source(H,12724,12735,'heap_attrinfo_insert_to_oos','history',BASE),source(L,4984,4996,'locator_insert_force')]),
claim(3,'The added regression checks logical equality and root/p0/p1 OOS ownership.',[source(T,387,456,'PartitionedForceOutlineStoresOosInPrunedHeap','test'),source(T,47,67,'show_heap_oos_query','test'),source(T,194,214,'OosSqlShow fixture','test')]),
claim(4,'Partition routing evaluates a partition key and returns child class and heap identities.',[source(P,3467,3581,'partition_find_partition_for_record'),source(P,3605,3689,'partition_prune_insert')]),
claim(5,'Heap records use slotted pages; OID, VPID, VFID and HFID identify different storage objects.',[source('src/storage/slotted_page.h',85,91,'SPAGE_SLOT'),source('src/storage/storage_common.h',190,231,'HFID and RECDES'),source('src/compat/dbtype_def.h',956,974,'VPID and VFID'),source('src/compat/dbtype_def.h',1040,1055,'OID')]),
claim(6,'The partitioned root holds no row data on the traced UPDATE path; child partitions supply heap identities.',[source(P,3755,3777,'partition_prune_update'),source(P,3550,3570,'partition_find_partition_for_record')]),
claim(7,'Attribute state, record descriptors and copy-area memory have distinct roles.',[source('src/storage/storage_common.h',220,231,'RECDES'),source(L,7490,7562,'locator_allocate_copy_area_by_attr_info'),source(H,13317,13359,'heap_attrinfo_transform_to_disk_internal')]),
claim(8,'The allocator dispatches probe first, then explicit-owner final mode, then LOB-specific ordinary mode.',[source(L,7490,7562,'locator_allocate_copy_area_by_attr_info')]),
claim(9,'OOS uses a head-OID/length stub, attribute offset flag, record flag and linked chunk headers.',[source('src/base/object_representation.h',448,468,'OR_OOS_INLINE_SIZE'),source('src/base/object_representation_constants.h',159,174,'OR_RECORD_FLAG_HAS_OOS'),source('src/storage/oos_file.hpp',28,34,'oos_record_header'),source(H,13088,13122,'heap_attrinfo_transform_variable_to_disk'),source(H,12869,12910,'heap_attrinfo_transform_header_to_disk')]),
claim(10,'The transformer rejects OOS plus bigone before OOS insertion.',[source(H,13386,13410,'heap_attrinfo_transform_to_disk_internal')]),
claim(11,'Logical SELECT can succeed despite a wrong heap-owner association.',[source(H,10452,10505,'heap_attrvalue_read_oos_inline'),source('src/storage/heap_oos.cpp',631,660,'heap_oos_insert_serialized_values')],kind='inference',rationale='The read uses the parsed physical head OID directly, while write ownership is selected by class-to-heap lookup. A wrong owner can leave a readable physical chain. Earlier reports corroborate this but the old binary was not rerun.'),
claim(12,'At the pinned head, missing-file success and lookup failure take different branches in the vacuum helper.',[source(H,12433,12543,'heap_oos_find_vfid'),source('src/query/vacuum_oos.cpp',401,446,'vacuum_oos_find_vfid_for_heap_record')]),
claim(13,'The full current-server failure path of deliberately inconsistent ownership has not been reproduced here.',[],kind='unknown',resolution='Use an owned SERVER_MODE database and a controlled test seam to construct wrong ownership, then trace lookup result, VFID and cleanup. Do not infer current abort behavior from old comments.'),
claim(14,'The pinned layout code still uses DB_PAGESIZE/4; this differs from the loaded normative physical-capacity target.',[source(H,12365,12430,'heap_attrinfo_determine_disk_layout')]),
claim(15,'The new wrappers implement ordinary/probe/final modes; final mode assumes a previous successful probe.',[source(H,12790,12854,'transform wrappers'),source(H,13317,13356,'heap_attrinfo_transform_to_disk_internal')]),
claim(16,'The locator shares INSERT/UPDATE preparation, performs suppressed early routing when needed, and retains the ordinary no-demotion path.',[source(L,7599,7875,'locator_attribute_info_force'),source(Q,13620,13644,'qexec_execute_insert')]),
claim(17,'Lower locators still route, lock and write; cross-partition UPDATE can move the record.',[source(L,4984,5079,'locator_insert_force'),source(L,5980,6050,'locator_update_force')]),
claim(18,'Early and final routing should agree because the logical partition values are preserved across serialization modes.',[source(P,3496,3514,'partition_find_partition_for_record'),source(H,13339,13354,'increment pre-seeding'),source(L,7719,7799,'locator_attribute_info_force')],kind='inference',rationale='The same prepared DB_VALUEs underlie the inline probe and final image, and routing reads logical values. This supports agreement but is not exhaustive concurrency validation.'),
claim(19,'Partition selection reads through root representation and adjusts the chosen child representation.',[source(P,3467,3581,'partition_find_partition_for_record')]),
claim(20,'Ordinary suppression returns inline size before sorting and selection; oversized rows without eligible candidates need not demote.',[source(H,12312,12430,'heap_attrinfo_determine_disk_layout')]),
claim(21,'FORCE_OUTLINE suppression reports a hypothetical demotion and continues before mutating selection/payload/has_oos.',[source(H,12338,12363,'heap_attrinfo_determine_disk_layout')]),
claim(22,'Layout precedes OOS insertion, and OOS insertion precedes the buffer-writing retry loop.',[source(H,13317,13450,'heap_attrinfo_transform_to_disk_internal'),source(H,12632,12776,'OOS request preparation and insertion')]),
claim(23,'The second PR commit added the forced-loop suppression and its small-value regression.',[source(H,12343,12352,'FORCE_OUTLINE suppression'),source(T,387,456,'PartitionedForceOutlineStoresOosInPrunedHeap','test')]),
claim(24,'A per-call set prevents repeated fixed increments; final mode seeds a new set after a successful probe.',[source(H,12964,13035,'heap_attrinfo_transform_fixed_to_disk'),source(H,13339,13354,'heap_attrinfo_transform_to_disk_internal')]),
claim(25,'Both inline and OOS serializers use the LOB-written state guard, which survives in attr_info across passes.',[source(H,12545,12647,'heap_attrinfo_dbvalue_to_recdes and serialize helper'),source(H,13123,13201,'heap_attrinfo_transform_variable_to_disk')]),
claim(26,'REPLACE and ODKU use suppressed temporary key images while retaining their duplicate-search behavior and LOB modes.',[source(Q,11920,12143,'qexec_remove_duplicates_for_replace'),source(Q,12158,12373,'qexec_oid_of_duplicate_key_update')]),
claim(27,'Copy-area cleanup is distinct from persistent-chain lifetime; the new final pass does not create a transaction boundary.',[source(L,7747,7875,'locator_attribute_info_force'),source('src/storage/heap_oos.cpp',674,701,'heap_oos_delete_unreferenced contract'),source(H,12727,12776,'heap_attrinfo_insert_to_oos')]),
claim(28,'The OOS partition path adds serialization and routing work and can require a large temporary inline image.',[source(L,7710,7778,'locator_attribute_info_force'),source(H,13412,13445,'buffer growth loop')],kind='inference',rationale='Two explicit transformations and an early pruning call add work. The probe retains logical inline payload bytes. No latency or memory benchmark was performed.'),
claim(29,'The pinned PR changes six implementation/header/test files, with 306 additions and 23 deletions.',[source('src/storage/heap_file.h',505,518,'new declarations'),source('src/transaction/locator_sr.h',83,90,'allocator declaration')]),
claim(30,'The selected regression target uses GoogleTest and the standalone engine.',[source('unit_tests/oos/sql/CMakeLists.txt',21,56,'SA test targets','config'),source('unit_tests/oos/sql/test_oos_sql_common.hpp',51,86,'SqlServerEnv','test')]),
claim(31,'The existing recorded regression binary passed the selected test in a fresh private SA database.',[dict(type='runtime',runtime_check='R-001')],kind='runtime_observation'),
claim(32,'Runtime validation of the full UPDATE/LOB/increment/duplicate/vacuum/crash matrix remains open.',[],kind='unknown',resolution='Add/run the distinct focused experiments listed in chapter 7 in owned environments, recording actual state and ownership rather than only SQL equality.'),
claim(33,'The interface is a stateful caller protocol that could be made more explicit in a future design.',[source(H,12796,12831,'probe and final wrappers'),source(L,7513,7533,'mode dispatch')],kind='inference',rationale='Mode depends on nullable pointers and prior mutation. A mode/prepared-state type is a possible design improvement, not implemented in this PR.'),
claim(34,'Lazy OOS file creation uses a system operation with encryption policy, heap-header logging and page cleanup.',[source(H,12446,12542,'heap_oos_find_vfid')]),
]
