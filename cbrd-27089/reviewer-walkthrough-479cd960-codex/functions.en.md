# PR #7600 — function inventory and direct calls

This is a lookup reference. Start with the [short English guide](start-here.en.md) or [Korean guide](start-here.ko.html) for the one-row example.

## Scope and result

Compare base `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` with HEAD `479cd960ec04196c92bf9789b1fc340af9046c2c`.

- **68 named definitions/test bodies:** 49 newly created, 19 modified, 0 deleted.
- Of these, **32 are in production source files:** 13 new and 19 modified. One of the 32 is a test-only bridge.
- **36 are in test files:** 29 new TEST_F bodies and 7 new named helpers/constructors/destructors. The 29 bodies comprise 28 SQL tests and one disabled vacuum regression.
- **Two new anonymous callback bodies** are listed separately. They are not included in the 68 named entries.
- Four unchanged functions previously described in the guide are listed after the inventory. They must not be mislabeled as modified.
- All **63 diff hunks** are accounted for in the final appendix, including declarations, comments, includes and the test timeout setting.

“Newly created” describes a new function definition, not necessarily new behavior. For example, the old locator_insert_force implementation becomes locator_insert_force_internal, while locator_insert_force remains as a modified wrapper. No deleted source function was found. Extraction relationships are explained in the entries.

## How to read the calls

**Caller → callee means a direct, explicitly named source call.** Conditional calls are included; an arrow does not mean the call always runs. Added/removed/retained compares call targets, so changed arguments to a retained target remain important in the prose.

Repository searches cover src/ and unit_tests/ at both revisions. Incoming links point to call sites. The expandable call details exclude uppercase macro invocations and member/function-pointer expressions. Constructor/destructor calls may be implicit; callback and GoogleTest dispatch are described separately. This is a source call index, not a compiler-resolved runtime graph or a list of calls observed in a running server. Test SQL reaches engine functions indirectly through SQL execution.

## Suggested first path

Follow locator_attribute_info_force, partition_prune_insert_by_attrinfo, partition_prune_insert_internal, partition_find_partition_for_attrinfo, then heap_attrinfo_get_effective_key. Return to locator_attribute_info_force to follow row construction. These are separate calls from the orchestration function, not one continuous linear call chain.

## Function index

| ID | Function | Status | Source file |
|---|---|---|---|
| F01 | [partition_find_partition_for_expr](#f01) | newly created | `src/query/partition.c` |
| F02 | [partition_start_key_attrinfo](#f02) | newly created | `src/query/partition.c` |
| F03 | [partition_find_partition_for_attrinfo](#f03) | newly created | `src/query/partition.c` |
| F04 | [partition_find_partition_for_record](#f04) | modified | `src/query/partition.c` |
| F05 | [partition_prune_insert_internal](#f05) | newly created | `src/query/partition.c` |
| F06 | [partition_prune_insert](#f06) | modified | `src/query/partition.c` |
| F07 | [partition_prune_insert_by_attrinfo](#f07) | newly created | `src/query/partition.c` |
| F08 | [partition_prune_update_internal](#f08) | newly created | `src/query/partition.c` |
| F09 | [partition_prune_update](#f09) | modified | `src/query/partition.c` |
| F10 | [partition_prune_update_by_attrinfo](#f10) | newly created | `src/query/partition.c` |
| F11 | [qexec_remove_duplicates_for_replace](#f11) | modified | `src/query/query_executor.c` |
| F12 | [qexec_oid_of_duplicate_key_update](#f12) | modified | `src/query/query_executor.c` |
| F13 | [heap_attrinfo_get_effective_key](#f13) | newly created | `src/storage/heap_file.c` |
| F14 | [heap_attrinfo_determine_disk_layout](#f14) | modified | `src/storage/heap_file.c` |
| F15 | [heap_attrinfo_insert_to_oos](#f15) | modified | `src/storage/heap_file.c` |
| F16 | [heap_attrinfo_transform_to_disk](#f16) | modified | `src/storage/heap_file.c` |
| F17 | [heap_attrinfo_transform_to_disk_with_oos_owner](#f17) | newly created | `src/storage/heap_file.c` |
| F18 | [heap_attrinfo_transform_to_disk_probe_oos](#f18) | newly created | `src/storage/heap_file.c` |
| F19 | [heap_attrinfo_transform_to_disk_oos_class](#f19) | newly created | `src/storage/heap_file.c` |
| F20 | [heap_attrinfo_transform_to_disk_except_lob](#f20) | modified | `src/storage/heap_file.c` |
| F21 | [heap_attrinfo_transform_to_disk_internal](#f21) | modified | `src/storage/heap_file.c` |
| F22 | [bridge_heap_attrinfo_insert_to_oos](#f22) | modified | `src/storage/heap_file.c` |
| F23 | [locator_insert_force_internal](#f23) | newly created | `src/transaction/locator_sr.c` |
| F24 | [locator_insert_force](#f24) | modified | `src/transaction/locator_sr.c` |
| F25 | [locator_update_force](#f25) | modified | `src/transaction/locator_sr.c` |
| F26 | [locator_force_for_multi_update](#f26) | modified | `src/transaction/locator_sr.c` |
| F27 | [xlocator_repl_force](#f27) | modified | `src/transaction/locator_sr.c` |
| F28 | [xlocator_force](#f28) | modified | `src/transaction/locator_sr.c` |
| F29 | [locator_allocate_copy_area_by_attr_info_internal](#f29) | newly created | `src/transaction/locator_sr.c` |
| F30 | [locator_allocate_copy_area_by_attr_info](#f30) | modified | `src/transaction/locator_sr.c` |
| F31 | [locator_attribute_info_force](#f31) | modified | `src/transaction/locator_sr.c` |
| F32 | [locator_mvcc_reev_cond_assigns](#f32) | modified | `src/transaction/locator_sr.c` |
| F33 | [scoped_sa_server](#f33) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F34 | [~scoped_sa_server](#f34) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F35 | [get_string_column](#f35) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F36 | [unqualified_table_name](#f36) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F37 | [expect_sql_count](#f37) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F38 | [expect_oos_records](#f38) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F39 | [OosSqlShow.PartitionedForceOutlineStoresOosInPrunedHeap](#f39) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F40 | [OosSqlShow.PartitionRangeBoundaryAndNullOwnership](#f40) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F41 | [OosSqlShow.PartitionListExpressionAndFailedBatchOwnership](#f41) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F42 | [OosSqlShow.PartitionHashNullOwnership](#f42) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F43 | [OosSqlShow.PartitionRangeExpressionValidationAndMovement](#f43) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F44 | [OosSqlShow.PartitionListRejectsNullWithoutDestination](#f44) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F45 | [OosSqlShow.PartitionUpdatePreservesDuplicateProbesAndNonKeyIncrement](#f45) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F46 | [OosSqlShow.PartitionUpdateStringDomains](#f46) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F47 | [OosSqlShow.PartitionUpdateLegalKeysAndNullMovement](#f47) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F48 | [OosSqlShow.PartitionUpdateOldOosKeyAndRepresentation](#f48) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F49 | [OosSqlShow.PartitionUpdateLobLifecycle](#f49) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F50 | [OosSqlShow.PartitionUpdateDedicatedIncrementsAndArithmetic](#f50) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F51 | [OosSqlShow.EffectiveUpdateRouteUsesMissingHistoricalKeyDefault](#f51) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F52 | [OosSqlShow.EffectiveUpdateRoutePreservesOldKeyAndPendingIncrement](#f52) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F53 | [OosSqlShow.PartitionPreparationFailuresRollBackAndAllowNextWrite](#f53) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F54 | [OosSqlShow.PartitionLobPreparationAndIndexFailuresPreserveCommittedValues](#f54) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F55 | [OosSqlShow.EffectiveKeyCodecFailureClearsOutputAndPreservesAssignment](#f55) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F56 | [failing_codec](#f56) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F57 | [OosSqlShow.EffectiveRoutingFailurePreservesAssignmentsAndPublication](#f57) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F58 | [OosSqlShow.EffectiveInsertRoutePreservesOmittedAssignments](#f58) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F59 | [OosSqlShow.EffectiveInsertRoutePreservesAssignedChar](#f59) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F60 | [OosSqlShow.EffectiveInsertRouteLegalKeyDefaults](#f60) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F61 | [OosSqlShow.PartitionInsertLegalKeySqlMatrix](#f61) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F62 | [OosSqlShow.PartitionInsertOwnsExternalKeyAndMultiplePayloads](#f62) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F63 | [OosSqlShow.PartitionInsertRetainsBigoneRejectionBeforeOos](#f63) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F64 | [OosSqlShow.PartitionInsertGeneratedKeysAndDomainConversion](#f64) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F65 | [OosSqlShow.PartitionInsertDynamicDefault](#f65) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F66 | [OosSqlShow.PartitionInsertUsesColumnCollation](#f66) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F67 | [OosSqlShow.PartitionInsertCompressedExpressionKey](#f67) | newly created | `unit_tests/oos/sql/test_oos_sql_show.cpp` |
| F68 | [OosRealVacuum.DISABLED_RolledBackUpdateKeepsCommittedOosAfterVacuum](#f68) | newly created | `unit_tests/oos/test_oos_real_vacuum_server.cpp` |

## Function explanations

<a id="f01"></a>

### F01 · `partition_find_partition_for_expr` — newly created

**Purpose:** Evaluate the partition expression and choose exactly one child.

**Change:** Extract the expression evaluation and matching work from partition_find_partition_for_record. Return a borrowed partition descriptor only on success.

**Reason:** The new key-only path and the existing full-record path must use the same matching rules.

**Relevant direct callers:** partition_find_partition_for_attrinfo; partition_find_partition_for_record.

**Relevant direct callees:** fetch_peek_dbval; partition_prune_db_val; pruningset_popcount; pruningset_iterator_init; pruningset_iterator_next.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3480); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** [partition_find_partition_for_attrinfo](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3596); [partition_find_partition_for_record](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3648).

**Added targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3502); [assert_release](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3539); [db_value_is_null](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3504); [er_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3525); [fetch_peek_dbval](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3495); [partition_prune_db_val](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3510); [pruningset_init](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3492); [pruningset_iterator_init](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3536); [pruningset_iterator_next](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3538); [pruningset_popcount](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3511).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f02"></a>

### F02 · `partition_start_key_attrinfo` — newly created

**Purpose:** Create and bind the partition context’s one-key storage slot.

**Change:** Extract lazy attribute-cache initialization from the old record routing function. Keep the slot in the pruning context.

**Reason:** Expression bindings must point to stable storage, not a temporary stack value. Both routing paths need that storage.

**Relevant direct callers:** partition_find_partition_for_attrinfo; partition_find_partition_for_record.

**Relevant direct callees:** heap_attrinfo_start; partition_set_cache_info_for_expr.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3549); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** [partition_find_partition_for_attrinfo](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3574); [partition_find_partition_for_record](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3629).

**Added targets:** [heap_attrinfo_start](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3555); [partition_set_cache_info_for_expr](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3560).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f03"></a>

### F03 · `partition_find_partition_for_attrinfo` — newly created

**Purpose:** Choose a child from the pending write’s partition-key value.

**Change:** Clear a previous probe key, obtain an owned effective key in the stable context slot, evaluate it, copy the destination only on success, then clear the key.

**Reason:** Choose the destination before writing OOS values, without preparing every column or consuming the original assignments.

**Relevant direct callers:** partition_prune_insert_internal; partition_prune_update_internal.

**Relevant direct callees:** partition_start_key_attrinfo; heap_attrinfo_clear_dbvalues; heap_attrinfo_get_effective_key; partition_find_partition_for_expr.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3570); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** [partition_prune_insert_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3759); [partition_prune_update_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3931).

**Added targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3586); [heap_attrinfo_clear_dbvalues](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3603); [heap_attrinfo_get_effective_key](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3593); [partition_find_partition_for_expr](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3596); [partition_start_key_attrinfo](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3574).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f04"></a>

### F04 · `partition_find_partition_for_record` — modified

**Purpose:** Choose a child from an already serialized row.

**Change:** Delegate slot initialization and expression matching to the new helpers. Retain temporary root representation decoding, value cleanup, destination outputs, and destination representation patching.

**Reason:** Keep final row routing as a separate check while sharing its matching rules with early key-only routing. This function was not deleted.

**Relevant direct callers:** partition_prune_insert_internal; partition_prune_update_internal.

**Relevant direct callees:** partition_start_key_attrinfo; heap_attrinfo_read_dbvalues; partition_find_partition_for_expr; or_set_rep_id; heap_attrinfo_clear_dbvalues.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3618); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3467).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [partition_prune_insert](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3660); [partition_prune_update](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3793).

**HEAD callers:** [partition_prune_insert_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3764); [partition_prune_update_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3936).

**Added targets:** [partition_find_partition_for_expr](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3648); [partition_start_key_attrinfo](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3629).

**Removed targets:** [assert_release](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3555); [db_value_is_null](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3519); [er_set](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3541); [fetch_peek_dbval](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3510); [heap_attrinfo_start](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3486); [partition_prune_db_val](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3525); [partition_set_cache_info_for_expr](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3492); [pruningset_init](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3482); [pruningset_iterator_init](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3552); [pruningset_iterator_next](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3554); [pruningset_popcount](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3526).

**Retained targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3627); [heap_attrinfo_clear_dbvalues](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3673); [heap_attrinfo_read_dbvalues](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3639); [or_rep_id](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3636); [or_set_rep_id](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3667).

</details>

<a id="f05"></a>

### F05 · `partition_prune_insert_internal` — newly created

**Purpose:** Manage the common INSERT routing context and explicit-child checks.

**Change:** Move the previous partition_prune_insert body into an internal helper. Dispatch to attribute routing when attr_info is present, otherwise record routing.

**Reason:** Both entry points need the same context ownership and validation rules. This is an extraction, not a replacement routing policy.

**Relevant direct callers:** partition_prune_insert; partition_prune_insert_by_attrinfo.

**Relevant direct callees:** partition_find_partition_for_attrinfo; partition_find_partition_for_record; partition_init_pruning_context; partition_load_pruning_context; partition_clear_pruning_context.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3702); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** [partition_prune_insert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3804); [partition_prune_insert_by_attrinfo](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3821).

**Added targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3720); [er_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3775); [partition_clear_pruning_context](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3791); [partition_find_partition_for_attrinfo](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3759); [partition_find_partition_for_record](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3764); [partition_init_pruning_context](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3730); [partition_load_pruning_context](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3743).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f06"></a>

### F06 · `partition_prune_insert` — modified

**Purpose:** Route an INSERT that already has a row image.

**Change:** Replace its implementation with a wrapper that supplies NULL attr_info to partition_prune_insert_internal.

**Reason:** Preserve existing callers and record-routing behavior while adding an early route.

**Relevant direct callers:** locator_insert_force_internal.

**Relevant direct callees:** partition_prune_insert_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3800); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3605).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [locator_insert_force](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L4989).

**HEAD callers:** [locator_insert_force_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L4990); [OosSqlShow.EffectiveInsertRouteLegalKeyDefaults](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1481); [OosSqlShow.EffectiveInsertRoutePreservesAssignedChar](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1402); [OosSqlShow.EffectiveInsertRoutePreservesOmittedAssignments](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1324).

**Added targets:** [partition_prune_insert_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3804).

**Removed targets:** [assert](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3623); [er_set](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3670); [partition_clear_pruning_context](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3686); [partition_find_partition_for_record](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3660); [partition_init_pruning_context](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3633); [partition_load_pruning_context](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3646).

**Retained targets:** None.

</details>

<a id="f07"></a>

### F07 · `partition_prune_insert_by_attrinfo` — newly created

**Purpose:** Expose early INSERT routing from assigned values.

**Change:** Assert that assignments are present and call the shared INSERT helper with no serialized row.

**Reason:** The caller can determine the child heap before the full row transformer creates OOS values.

**Relevant direct callers:** locator_attribute_info_force.

**Relevant direct callees:** partition_prune_insert_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3816); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** [locator_attribute_info_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7776); [OosSqlShow.EffectiveInsertRouteLegalKeyDefaults](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1465); [OosSqlShow.EffectiveInsertRoutePreservesAssignedChar](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1382); [OosSqlShow.EffectiveInsertRoutePreservesOmittedAssignments](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1302); [OosSqlShow.EffectiveRoutingFailurePreservesAssignmentsAndPublication](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1242).

**Added targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3820); [partition_prune_insert_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3821).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f08"></a>

### F08 · `partition_prune_update_internal` — newly created

**Purpose:** Manage common UPDATE routing, including source-child/root context and explicit-child checks.

**Change:** Extract the old partition_prune_update body and add an attribute-based branch. In that branch recdes is the supplied old row; in the record branch it is the new row.

**Reason:** An UPDATE may leave the key unchanged or move the row. Both early and final routing must preserve the established validation contract.

**Relevant direct callers:** partition_prune_update; partition_prune_update_by_attrinfo.

**Relevant direct callees:** partition_find_partition_for_attrinfo; partition_find_partition_for_record; partition_init_pruning_context; partition_load_pruning_context; partition_clear_pruning_context.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3847); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** [partition_prune_update](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3977); [partition_prune_update_by_attrinfo](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3990).

**Added targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3915); [er_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3947); [partition_clear_pruning_context](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3964); [partition_find_partition_for_attrinfo](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3931); [partition_find_partition_for_record](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3936); [partition_find_root_class_oid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3893); [partition_init_pruning_context](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3891); [partition_load_pruning_context](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3905).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f09"></a>

### F09 · `partition_prune_update` — modified

**Purpose:** Route the completed UPDATE row and patch its representation.

**Change:** Retain the public name as a wrapper into the internal helper with NULL attr_info.

**Reason:** The final serialized record still determines and verifies the destination. It is not removed by early routing.

**Relevant direct callers:** locator_update_force.

**Relevant direct callees:** partition_prune_update_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3974); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3712).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [locator_delete_force_internal](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L6464); [locator_update_force](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5989).

**HEAD callers:** [locator_delete_force_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6497); [locator_update_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6014); [OosSqlShow.EffectiveUpdateRoutePreservesOldKeyAndPendingIncrement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L988); [OosSqlShow.EffectiveUpdateRouteUsesMissingHistoricalKeyDefault](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L904).

**Added targets:** [partition_prune_update_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3977).

**Removed targets:** [assert](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3779); [er_set](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3803); [partition_clear_pruning_context](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3820); [partition_find_partition_for_record](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3793); [partition_find_root_class_oid](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3757); [partition_init_pruning_context](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3755); [partition_load_pruning_context](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3769).

**Retained targets:** None.

</details>

<a id="f10"></a>

### F10 · `partition_prune_update_by_attrinfo` — newly created

**Purpose:** Expose early UPDATE routing from assignments and the supplied old row.

**Change:** Pass both the assignments and old_recdes to the shared UPDATE helper.

**Reason:** If the statement did not assign the partition key, routing must read its old value without rewriting the source row first.

**Relevant direct callers:** locator_attribute_info_force.

**Relevant direct callees:** partition_prune_update_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3985); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** [locator_attribute_info_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7782); [OosSqlShow.EffectiveUpdateRoutePreservesOldKeyAndPendingIncrement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L957); [OosSqlShow.EffectiveUpdateRoutePreservesOldKeyAndPendingIncrement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L978); [OosSqlShow.EffectiveUpdateRouteUsesMissingHistoricalKeyDefault](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L888).

**Added targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3989); [partition_prune_update_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3990).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f11"></a>

### F11 · `qexec_remove_duplicates_for_replace` — modified

**Purpose:** Find and remove rows that conflict with a REPLACE candidate.

**Change:** Pass a non-NULL probe result pointer and a NULL OOS owner to copy-area construction; retain LOB_FLAG_EXCLUDE_LOB.

**Reason:** The temporary candidate is used for index lookup. Creating OOS chains for an image that will never be inserted can leave unowned data.

**Relevant direct callers:** qexec_execute_insert [unchanged context].

**Relevant direct callees:** locator_allocate_copy_area_by_attr_info; partition_prune_unique_btid [unchanged context].

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L11921); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/query_executor.c#L11921).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [qexec_execute_insert](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/query_executor.c#L13595); [qexec_execute_insert](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/query_executor.c#L13776).

**HEAD callers:** [qexec_execute_insert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L13605); [qexec_execute_insert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L13786).

**Added targets:** None.

**Removed targets:** None.

**Retained targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12081); [assert_release](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L11973); [btree_is_unique_type](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L11985); [db_make_null](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L11948); [er_errid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12045); [heap_attrinfo_clear_dbvalues](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L11950); [heap_attrinfo_read_dbvalues](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L11967); [heap_attrvalue_get_key](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12000); [locator_allocate_copy_area_by_attr_info](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L11958); [locator_attribute_info_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12066); [locator_delete_lob_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12057); [locator_free_copy_area](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12127); [locator_get_partition_scancache](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12040); [partition_prune_unique_btid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12015); [pr_clear_value](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12121); [xbtree_find_unique](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12024).

</details>

<a id="f12"></a>

### F12 · `qexec_oid_of_duplicate_key_update` — modified

**Purpose:** Find the existing row that conflicts with an INSERT ON DUPLICATE KEY UPDATE candidate.

**Change:** Use the same OOS-suppressed probe request; retain LOB_FLAG_INCLUDE_LOB.

**Reason:** A unique-index probe must not publish OOS chains for its temporary row image. This does not claim that every LOB side effect is suppressed.

**Relevant direct callers:** qexec_execute_duplicate_key_update [unchanged context].

**Relevant direct callees:** locator_allocate_copy_area_by_attr_info; partition_prune_unique_btid [unchanged context].

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12158); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/query_executor.c#L12153).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [qexec_execute_duplicate_key_update](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/query_executor.c#L12386).

**HEAD callers:** [qexec_execute_duplicate_key_update](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12396).

**Added targets:** None.

**Removed targets:** None.

**Retained targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12276); [btree_is_unique_type](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12221); [db_make_null](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12184); [er_errid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12278); [er_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12295); [heap_attrinfo_clear_dbvalues](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12193); [heap_attrinfo_read_dbvalues](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12210); [heap_attrvalue_get_key](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12236); [locator_allocate_copy_area_by_attr_info](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12201); [locator_free_copy_area](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12344); [locator_get_partition_scancache](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12273); [partition_prune_unique_btid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12251); [pr_clear_value](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12338); [xbtree_find_unique](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12258).

</details>

<a id="f13"></a>

### F13 · `heap_attrinfo_get_effective_key` — newly created

**Purpose:** Obtain the partition key as it will be represented in storage.

**Change:** Use an independent reader for an unchanged UPDATE key, the existing default reader for an omitted INSERT value, or a clone for an assigned value. Apply a pending increment to the clone. Round-trip the scalar value through its storage codec, then clear temporary memory.

**Reason:** Early routing must agree with the completed row, including defaults, old representations, CHAR padding and increments. The original assignments must remain available for normal preparation.

**Relevant direct callers:** partition_find_partition_for_attrinfo.

**Relevant direct callees:** heap_attrvalue_locate; heap_attrinfo_start; heap_attrinfo_read_dbvalues_without_oid; heap_attrinfo_end; heap_attrvalue_read; pr_clone_value; qdata_increment_dbval; pr_clear_value. Indirect codec callbacks: pr_type->get_disk_size_of_value, pr_type->data_writeval, pr_type->data_readval.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12117); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** [partition_find_partition_for_attrinfo](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3593); [OosSqlShow.EffectiveKeyCodecFailureClearsOutputAndPreservesAssignment](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1183); [OosSqlShow.EffectiveKeyCodecFailureClearsOutputAndPreservesAssignment](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1191).

**Added targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12131); [db_make_null](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12157); [db_private_alloc](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12196); [db_private_free_and_init](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12217); [er_errid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12191); [heap_attrinfo_end](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12152); [heap_attrinfo_read_dbvalues_without_oid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12147); [heap_attrinfo_start](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12142); [heap_attrvalue_locate](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12133); [heap_attrvalue_read](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12158); [or_init](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12209); [pr_clear_value](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12221); [pr_clone_value](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12183); [qdata_increment_dbval](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12175).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f14"></a>

### F14 · `heap_attrinfo_determine_disk_layout` — modified

**Purpose:** Choose inline versus OOS storage and compute record size.

**Change:** Accept suppress_oos and a would-demote output. In probe mode report whether a column would move to OOS, but keep the complete inline payload and leave the OOS plan unselected.

**Reason:** Temporary key-probe images need the values but must not cause OOS insertion. The image may exceed a normal heap record’s capacity.

**Relevant direct callers:** heap_attrinfo_transform_to_disk_internal.

**Relevant direct callees:** heap_attrinfo_get_record_payload_size; heap_attrinfo_get_record_header_size; heap_oos_get_demote_priority [unchanged context].

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12440); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L12310).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [heap_attrinfo_transform_to_disk_internal](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L13274).

**HEAD callers:** [heap_attrinfo_transform_to_disk_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L13510).

**Added targets:** None.

**Removed targets:** None.

**Retained targets:** [db_value_is_null](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12470); [heap_attrinfo_get_record_header_size](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12551); [heap_attrinfo_get_record_payload_size](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12460); [heap_oos_get_demote_priority](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12509).

</details>

<a id="f15"></a>

### F15 · `heap_attrinfo_insert_to_oos` — modified

**Purpose:** Prepare serialized OOS requests and insert their value chains.

**Change:** Accept an optional destination class and pass it to heap_oos_insert_serialized_values; fall back to attr_info->class_oid when absent. Keep payload preparation based on the original attr_info.

**Reason:** The OOS file must belong to the child heap that will store the row. The source class must still identify the old representation and LOB preparation context.

**Relevant direct callers:** heap_attrinfo_transform_to_disk_internal; bridge_heap_attrinfo_insert_to_oos [test-only].

**Relevant direct callees:** heap_oos_begin_insert_publication; heap_attrinfo_prepare_oos_insert_requests; heap_oos_insert_serialized_values; heap_attrinfo_free_oos_payloads [all unchanged context].

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12847); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L12686).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [bridge_heap_attrinfo_insert_to_oos](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L28434); [heap_attrinfo_transform_to_disk_internal](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L13310).

**HEAD callers:** [bridge_heap_attrinfo_insert_to_oos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L28670); [heap_attrinfo_transform_to_disk_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L13546).

**Added targets:** None.

**Removed targets:** None.

**Retained targets:** [er_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12877); [heap_attrinfo_free_oos_payloads](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12898); [heap_attrinfo_prepare_oos_insert_requests](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12882); [heap_oos_begin_insert_publication](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12857); [heap_oos_insert_serialized_values](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12888).

</details>

<a id="f16"></a>

### F16 · `heap_attrinfo_transform_to_disk` — modified

**Purpose:** Build a normal row image with LOB handling.

**Change:** Pass NULL owner, NULL probe output and false for already-applied increments to the enlarged internal interface.

**Reason:** Keep normal callers on their existing first-pass behavior.

**Relevant direct callers:** locator_allocate_copy_area_by_attr_info_internal (normal branch); other existing normal transformation callers.

**Relevant direct callees:** heap_attrinfo_transform_to_disk_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12916); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L12755).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [serial_update_serial_object](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/serial.c#L1192); [locator_allocate_copy_area_by_attr_info](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7513).

**HEAD callers:** [serial_update_serial_object](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/serial.c#L1192); [locator_allocate_copy_area_by_attr_info_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7572).

**Added targets:** None.

**Removed targets:** None.

**Retained targets:** [heap_attrinfo_transform_to_disk_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12919).

</details>

<a id="f17"></a>

### F17 · `heap_attrinfo_transform_to_disk_with_oos_owner` — newly created

**Purpose:** Build the row normally while directing OOS values to a chosen heap.

**Change:** Pass a required owner, no probe output and false for already-applied increments.

**Reason:** The main write path has already chosen the child from one key. It can now prepare the full row once with the correct OOS owner.

**Relevant direct callers:** locator_allocate_copy_area_by_attr_info_internal (oos_first_pass branch).

**Relevant direct callees:** heap_attrinfo_transform_to_disk_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12930); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** [locator_allocate_copy_area_by_attr_info_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7553); [OosSqlShow.EffectiveUpdateRoutePreservesOldKeyAndPendingIncrement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L981).

**Added targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12934); [heap_attrinfo_transform_to_disk_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12935).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f18"></a>

### F18 · `heap_attrinfo_transform_to_disk_probe_oos` — newly created

**Purpose:** Build an inline-only image for a temporary probe.

**Change:** Pass the caller’s would-demote pointer and no owner to the common transformer.

**Reason:** Avoid OOS publication during duplicate-key lookup. Normal assignment preparation can still occur, including increments and permitted LOB work.

**Relevant direct callers:** locator_allocate_copy_area_by_attr_info_internal (probe branch).

**Relevant direct callees:** heap_attrinfo_transform_to_disk_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12951); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** [locator_allocate_copy_area_by_attr_info_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7558); [OosSqlShow.EffectiveInsertRouteLegalKeyDefaults](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1475); [OosSqlShow.EffectiveInsertRoutePreservesAssignedChar](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1396); [OosSqlShow.EffectiveInsertRoutePreservesOmittedAssignments](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1318); [OosSqlShow.EffectiveUpdateRoutePreservesOldKeyAndPendingIncrement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L936); [OosSqlShow.EffectiveUpdateRouteUsesMissingHistoricalKeyDefault](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L864); [OosSqlShow.EffectiveUpdateRouteUsesMissingHistoricalKeyDefault](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L901).

**Added targets:** [heap_attrinfo_transform_to_disk_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12955).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f19"></a>

### F19 · `heap_attrinfo_transform_to_disk_oos_class` — newly created

**Purpose:** Complete an owner-directed transformation after an earlier full probe.

**Change:** Pass the owner and true for already-applied increments.

**Reason:** Retain a two-pass interface without applying an increment twice. The current main partitioned write uses with_oos_owner instead; do not teach this as its active second stage.

**Relevant direct callers:** locator_allocate_copy_area_by_attr_info_internal (owner supplied without first-pass or probe flag).

**Relevant direct callees:** heap_attrinfo_transform_to_disk_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12968); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** [locator_allocate_copy_area_by_attr_info_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7563).

**Added targets:** [heap_attrinfo_transform_to_disk_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12972).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f20"></a>

### F20 · `heap_attrinfo_transform_to_disk_except_lob` — modified

**Purpose:** Build a normal row image without creating LOB objects.

**Change:** Supply NULL owner, NULL probe output and false for already-applied increments.

**Reason:** Adapt to the internal signature while preserving this entry point’s existing mode.

**Relevant direct callers:** locator_allocate_copy_area_by_attr_info_internal (exclude-LOB branch).

**Relevant direct callees:** heap_attrinfo_transform_to_disk_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12990); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L12775).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [server_object_loader::finish_line](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/loaddb/load_server_loader.cpp#L707); [locator_allocate_copy_area_by_attr_info](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7509).

**HEAD callers:** [server_object_loader::finish_line](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/loaddb/load_server_loader.cpp#L707); [locator_allocate_copy_area_by_attr_info_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7568).

**Added targets:** None.

**Removed targets:** None.

**Retained targets:** [heap_attrinfo_transform_to_disk_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12993).

</details>

<a id="f21"></a>

### F21 · `heap_attrinfo_transform_to_disk_internal` — modified

**Purpose:** Run shared row preparation, layout selection, OOS insertion and serialization.

**Change:** Add owner, probe and already-applied-increment parameters. Derive suppression from pointer presence, premark increments only for the retained second-pass mode, pass suppression into layout and owner into OOS insertion.

**Reason:** Support real writes and temporary probes through the same serializer while controlling OOS ownership and avoiding double increments.

**Relevant direct callers:** heap_attrinfo_transform_to_disk; heap_attrinfo_transform_to_disk_with_oos_owner; heap_attrinfo_transform_to_disk_probe_oos; heap_attrinfo_transform_to_disk_oos_class; heap_attrinfo_transform_to_disk_except_lob.

**Relevant direct callees:** heap_attrinfo_set_uninitialized; heap_attrinfo_determine_disk_layout; heap_attrinfo_insert_to_oos; heap_attrinfo_transform_header_to_disk; heap_attrinfo_transform_columns_to_disk.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L13458); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L13239).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [heap_attrinfo_transform_to_disk](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L12758); [heap_attrinfo_transform_to_disk_except_lob](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L12778).

**HEAD callers:** [heap_attrinfo_transform_to_disk](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12919); [heap_attrinfo_transform_to_disk_except_lob](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12993); [heap_attrinfo_transform_to_disk_oos_class](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12972); [heap_attrinfo_transform_to_disk_probe_oos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12955); [heap_attrinfo_transform_to_disk_with_oos_owner](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12935).

**Added targets:** None.

**Removed targets:** None.

**Retained targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L13570); [er_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L13538); [heap_attrinfo_determine_disk_layout](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L13510); [heap_attrinfo_insert_to_oos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L13546); [heap_attrinfo_set_uninitialized](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L13498); [heap_attrinfo_transform_columns_to_disk](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L13574); [heap_attrinfo_transform_header_to_disk](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L13562); [heap_is_big_length](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L13536); [mvcc_is_mvcc_disabled_class](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L13507); [or_init](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L13558); [unlikely](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L13536).

</details>

<a id="f22"></a>

### F22 · `bridge_heap_attrinfo_insert_to_oos` — modified

**Purpose:** Expose the static OOS insertion helper to unit tests.

**Change:** Pass NULL for the new owner parameter.

**Reason:** Keep the bridge using its supplied class through attr_info, with no owner override. It is compiled only under CUBRID_UNIT_TEST_ENABLED.

**Relevant direct callers:** unit-test code; not a production entry point.

**Relevant direct callees:** heap_attrinfo_insert_to_oos.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L28661); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L28425).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [OosServerTest.OosClassLookupFailureSeesCleanPublicationState](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/test_oos_server.cpp#L416); [OosServerTest.OosLogicalPreparationFailureSeesCleanPublicationState](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/test_oos_server.cpp#L402); [OosServerTest.OosVfidLookupFailureSeesCleanPublicationState](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/test_oos_server.cpp#L435).

**HEAD callers:** [OosServerTest.OosClassLookupFailureSeesCleanPublicationState](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/test_oos_server.cpp#L416); [OosServerTest.OosLogicalPreparationFailureSeesCleanPublicationState](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/test_oos_server.cpp#L402); [OosServerTest.OosVfidLookupFailureSeesCleanPublicationState](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/test_oos_server.cpp#L435).

**Added targets:** None.

**Removed targets:** None.

**Retained targets:** [heap_attrinfo_insert_to_oos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L28670).

</details>

<a id="f23"></a>

### F23 · `locator_insert_force_internal` — newly created

**Purpose:** Insert the finished row and maintain its indexes.

**Change:** Extract the previous locator_insert_force body. Add an optional expected child and compare it with final record routing before proceeding with the partitioned insert.

**Reason:** OOS chains can already belong to the early child. A different final child must produce an error instead of placing the row elsewhere. Transaction error handling is responsible for rollback; this guard is not a local delete-all operation.

**Relevant direct callers:** locator_insert_force; locator_attribute_info_force.

**Relevant direct callees:** partition_prune_insert; heap_insert_logical [unchanged context].

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L4953); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** [locator_attribute_info_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7812); [locator_insert_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5305).

**Added targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5250); [assert_release](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5050); [catalog_insert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5135); [catcls_insert_catalog_classes](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5185); [er_errid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5242); [er_log_debug](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5265); [er_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5000); [heap_create_insert_context](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5072); [heap_create_update_context](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5237); [heap_get_class_repr_id](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5083); [heap_insert_logical](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5088); [heap_update_logical](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5239); [locator_add_or_remove_index](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5207); [locator_check_foreign_key](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5224); [locator_free_copy_area](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5289); [locator_get_partition_scancache](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5026); [locator_increase_catalog_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5257); [locator_permoid_class_name](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5121); [lock_subclass](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5006); [or_class_name](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5116); [or_class_rep_dir](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5180); [or_replace_rep_id](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5084); [partition_prune_insert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L4990); [qexec_clear_list_cache_by_class](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5263); [qmgr_add_modified_class](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5273); [strlen](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5118).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f24"></a>

### F24 · `locator_insert_force` — modified

**Purpose:** Keep the existing record-based force-insert entry point.

**Change:** Wrap locator_insert_force_internal with NULL expected_class_oid.

**Reason:** Existing callers do not have an early chosen OOS destination and keep their established behavior. The original function name still exists.

**Relevant direct callers:** locator_move_record [unchanged context]; existing force-insert callers.

**Relevant direct callees:** locator_insert_force_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5299); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L4952).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [server_object_loader::flush_records](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/loaddb/load_server_loader.cpp#L783); [locator_attribute_info_force](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7708); [locator_move_record](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5391); [locator_move_record](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5408); [locator_multi_insert_force](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L14062); [locator_multi_insert_force](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L14093); [locator_multi_insert_force](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L14148); [redistribute_partition_data](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L13092); [xlocator_force](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7334); [xlocator_repl_force](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7124).

**HEAD callers:** [server_object_loader::flush_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/loaddb/load_server_loader.cpp#L783); [locator_move_record](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5415); [locator_move_record](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5432); [locator_multi_insert_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L14168); [locator_multi_insert_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L14199); [locator_multi_insert_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L14254); [redistribute_partition_data](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L13198); [xlocator_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7368); [xlocator_repl_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7157).

**Added targets:** [locator_insert_force_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5305).

**Removed targets:** [assert](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5241); [assert_release](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5041); [catalog_insert](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5126); [catcls_insert_catalog_classes](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5176); [er_errid](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5233); [er_log_debug](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5256); [heap_create_insert_context](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5063); [heap_create_update_context](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5228); [heap_get_class_repr_id](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5074); [heap_insert_logical](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5079); [heap_update_logical](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5230); [locator_add_or_remove_index](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5198); [locator_check_foreign_key](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5215); [locator_free_copy_area](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5280); [locator_get_partition_scancache](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5017); [locator_increase_catalog_count](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5248); [locator_permoid_class_name](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5112); [lock_subclass](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L4997); [or_class_name](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5107); [or_class_rep_dir](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5171); [or_replace_rep_id](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5075); [partition_prune_insert](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L4989); [qexec_clear_list_cache_by_class](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5254); [qmgr_add_modified_class](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5264); [strlen](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5109).

**Retained targets:** None.

</details>

<a id="f25"></a>

### F25 · `locator_update_force` — modified

**Purpose:** Update or move the finished row and maintain indexes.

**Change:** Accept an optional expected child. After final partition routing, reject a different child before the following source-class refresh and instance move/index operations.

**Reason:** Do not move a row to a heap different from the one chosen for its OOS chains.

**Relevant direct callers:** locator_attribute_info_force; locator_force_for_multi_update; xlocator_repl_force; xlocator_force.

**Relevant direct callees:** partition_prune_update; locator_move_record [unchanged context].

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5490); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5465).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [locator_attribute_info_force](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7726); [locator_force_for_multi_update](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L6750); [xlocator_force](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7350); [xlocator_repl_force](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7140).

**HEAD callers:** [locator_attribute_info_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7831); [locator_force_for_multi_update](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6783); [xlocator_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7384); [xlocator_repl_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7173).

**Added targets:** None.

**Removed targets:** None.

**Retained targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6144); [catalog_insert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5707); [catalog_update](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5686); [catcls_insert_catalog_classes](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5755); [catcls_update_catalog_classes](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5582); [er_clear](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6099); [er_errid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6051); [er_log_debug](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6177); [er_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6024); [fpcache_remove_by_class](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5773); [free_and_init](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6195); [heap_create_update_context](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6134); [heap_delete_hfid_from_cache](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5678); [heap_get_class_info](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6037); [heap_get_class_name_alloc_if_diff](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5556); [heap_get_class_oid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6031); [heap_get_class_record](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5602); [heap_get_hfid_if_cached](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5671); [heap_get_visible_version](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5968); [heap_update_logical](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6135); [locator_add_or_remove_index](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6106); [locator_check_foreign_key](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6120); [locator_free_copy_area](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6200); [locator_get_partition_scancache](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5791); [locator_increase_catalog_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6168); [locator_lock_and_get_object_with_evaluation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5815); [locator_move_record](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6060); [locator_update_index](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6077); [lock_has_lock_on_object](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5888); [lock_object](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5946); [lock_subclass](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6047); [log_add_to_modified_class_list](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5573); [log_does_allow_replication](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6159); [logtb_find_current_mvccid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5884); [logtb_get_mvcc_snapshot](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5955); [mvcc_is_mvcc_disabled_class](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5801); [or_class_hfid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5664); [or_class_name](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5552); [or_class_rep_dir](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5748); [or_class_tde_algorithm](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5539); [or_mvcc_get_header](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5898); [or_mvcc_set_header](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5933); [partition_prune_update](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6014); [qexec_clear_list_cache_by_class](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6175); [qmgr_add_modified_class](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6185); [repl_add_update_lsa](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6162); [strlen](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5570); [tde_is_loaded](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5540); [xcache_remove_by_oid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5768).

</details>

<a id="f26"></a>

### F26 · `locator_force_for_multi_update` — modified

**Purpose:** Apply a force copy-area batch for multi-row updates.

**Change:** Pass NULL for the new expected-class argument.

**Reason:** This path did not make an early OOS-owner decision; keep its existing update contract.

**Relevant direct callers:** xlocator_force.

**Relevant direct callees:** locator_update_force.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6664); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L6631).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [xlocator_force](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7436).

**HEAD callers:** [xlocator_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7470).

**Added targets:** None.

**Removed targets:** None.

**Retained targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6692); [er_errid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6772); [er_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6683); [locator_end_force_scan_cache](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6831); [locator_manyobj_flag_is_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6804); [locator_start_force_scan_cache](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6747); [locator_update_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6783); [logtb_get_mvcc_snapshot](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6769); [logtb_tran_update_unique_stats](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6815).

</details>

<a id="f27"></a>

### F27 · `xlocator_repl_force` — modified

**Purpose:** Apply replicated insert, update and delete operations.

**Change:** Pass NULL for the new expected-class argument in the UPDATE call.

**Reason:** Replication’s existing record-based path has no early destination to verify.

**Relevant direct callers:** external server request / standalone entry callers; see complete call inventory.

**Relevant direct callees:** locator_update_force.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7051); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7018).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [slocator_repl_force](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/communication/network_interface_sr.cpp#L1301).

**HEAD callers:** [slocator_repl_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/communication/network_interface_sr.cpp#L1301).

**Added targets:** None.

**Removed targets:** None.

**Retained targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7219); [assert_release](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7254); [db_value_put_null](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7086); [er_clear](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7092); [er_errid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7254); [er_msg](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7220); [er_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7203); [heap_get_class_info](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7100); [heap_recdes_contains_oos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7138); [locator_area_op_to_pruning_type](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7171); [locator_delete_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7187); [locator_end_force_scan_cache](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7266); [locator_fixup_oos_oids_in_recdes](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7140); [locator_insert_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7157); [locator_oos_insert_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7150); [locator_repl_add_error_to_copyarea](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7220); [locator_repl_get_key_value](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7096); [locator_repl_prepare_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7131); [locator_start_force_scan_cache](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7116); [locator_update_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7173); [perfmon_inc_stat](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7193); [pr_clear_value](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7261); [xtran_server_end_topop](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7269); [xtran_server_start_topop](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7125).

</details>

<a id="f28"></a>

### F28 · `xlocator_force` — modified

**Purpose:** Apply a copy-area batch of force operations.

**Change:** Pass NULL for expected_class_oid in its UPDATE call.

**Reason:** Preserve the existing path when no earlier attribute-based routing occurred.

**Relevant direct callers:** external server request / standalone entry callers; see complete call inventory.

**Relevant direct callees:** locator_update_force; locator_force_for_multi_update.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7285); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7251).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [locator_force](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/communication/network_interface_cl.c#L792); [slocator_force](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/communication/network_interface_sr.cpp#L1464).

**HEAD callers:** [locator_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/communication/network_interface_cl.c#L792); [slocator_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/communication/network_interface_sr.cpp#L1464).

**Added targets:** None.

**Removed targets:** None.

**Retained targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7484); [assert_release](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7485); [er_errid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7485); [er_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7413); [locator_area_op_to_pruning_type](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7382); [locator_delete_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7397); [locator_end_force_scan_cache](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7489); [locator_filter_errid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7433); [locator_force_for_multi_update](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7470); [locator_insert_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7368); [locator_manyobj_flag_is_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7468); [locator_start_force_scan_cache](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7322); [locator_update_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7384); [perfmon_inc_stat](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7403); [xtran_server_end_topop](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7492); [xtran_server_start_topop](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7347).

</details>

<a id="f29"></a>

### F29 · `locator_allocate_copy_area_by_attr_info_internal` — newly created

**Purpose:** Allocate a buffer and transform assignments into a row image.

**Change:** Extract the old public body and add mode dispatch: selected-owner first pass, inline-only probe, retained owner-directed second pass, exclude-LOB normal pass, or normal pass.

**Reason:** Give the real write path and duplicate-key probes explicit serialization choices while preserving buffer allocation and error handling.

**Relevant direct callers:** locator_allocate_copy_area_by_attr_info; locator_attribute_info_force.

**Relevant direct callees:** heap_attrinfo_transform_to_disk_with_oos_owner; heap_attrinfo_transform_to_disk_probe_oos; heap_attrinfo_transform_to_disk_oos_class; heap_attrinfo_transform_to_disk_except_lob; heap_attrinfo_transform_to_disk.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7522); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** [locator_allocate_copy_area_by_attr_info](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7615); [locator_attribute_info_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7792).

**Added targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7587); [free](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7598); [heap_attrinfo_transform_to_disk](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7572); [heap_attrinfo_transform_to_disk_except_lob](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7568); [heap_attrinfo_transform_to_disk_oos_class](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7563); [heap_attrinfo_transform_to_disk_probe_oos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7558); [heap_attrinfo_transform_to_disk_with_oos_owner](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7553); [locator_allocate_copy_area_by_length](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7591); [locator_free_copy_area](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7588).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f30"></a>

### F30 · `locator_allocate_copy_area_by_attr_info` — modified

**Purpose:** Expose copy-area construction to existing and probe callers.

**Change:** Become a wrapper with owner and probe arguments, passing false for the private first-pass selector. The header supplies defaults for compatibility.

**Reason:** Allow duplicate-key probes to suppress OOS and retain the earlier owner/rebuild interface; keep the main first-pass selector private.

**Relevant direct callers:** qexec_remove_duplicates_for_replace; qexec_oid_of_duplicate_key_update; locator_attribute_info_force; locator_mvcc_reev_cond_assigns.

**Relevant direct callees:** locator_allocate_copy_area_by_attr_info_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7611); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7482).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [qexec_oid_of_duplicate_key_update](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/query_executor.c#L12192); [qexec_remove_duplicates_for_replace](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/query_executor.c#L11954); [locator_attribute_info_force](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7696); [locator_mvcc_reev_cond_assigns](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L13783).

**HEAD callers:** [qexec_oid_of_duplicate_key_update](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12201); [qexec_remove_duplicates_for_replace](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L11958); [locator_attribute_info_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7799); [locator_mvcc_reev_cond_assigns](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L13889).

**Added targets:** [locator_allocate_copy_area_by_attr_info_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7615).

**Removed targets:** [assert](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7528); [free](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7539); [heap_attrinfo_transform_to_disk](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7513); [heap_attrinfo_transform_to_disk_except_lob](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7509); [locator_allocate_copy_area_by_length](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7532); [locator_free_copy_area](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7529).

**Retained targets:** None.

</details>

<a id="f31"></a>

### F31 · `locator_attribute_info_force` — modified

**Purpose:** Turn pending assignments into an inserted or updated row.

**Change:** For partitioned writes, choose write_destination from the key first. Build the full row with that OOS owner, then pass the expected destination to final force. Keep the original source class. Nonpartitioned writes pass NULL mode arguments.

**Reason:** This changes the critical order: choose the child, create OOS values for its heap, then verify and store the row. It avoids a full-row pre-routing probe.

**Relevant direct callers:** query execution write callers; see complete call inventory.

**Relevant direct callees:** partition_prune_insert_by_attrinfo; partition_prune_update_by_attrinfo; locator_allocate_copy_area_by_attr_info_internal; locator_allocate_copy_area_by_attr_info; locator_insert_force_internal; locator_update_force.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7655); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7583).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [dblink_global_tran_insert_row](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/dblink_global_tran_catalog.c#L179); [dblink_global_tran_update_state](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/dblink_global_tran_catalog.c#L313); [qexec_execute_delete](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/query_executor.c#L11608); [qexec_execute_duplicate_key_update](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/query_executor.c#L12491); [qexec_execute_increment](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/query_executor.c#L14522); [qexec_execute_insert](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/query_executor.c#L13627); [qexec_execute_insert](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/query_executor.c#L13807); [qexec_execute_update](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/query_executor.c#L10790); [qexec_execute_update](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/query_executor.c#L10971); [qexec_remove_duplicates_for_replace](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/query_executor.c#L12061); [process_object](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/compactdb_sr.c#L263); [heap_object_upgrade_domain](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L19029); [locator_check_primary_key_delete](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L4512); [locator_check_primary_key_update](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L4854).

**HEAD callers:** [dblink_global_tran_insert_row](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/dblink_global_tran_catalog.c#L179); [dblink_global_tran_update_state](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/dblink_global_tran_catalog.c#L313); [qexec_execute_delete](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L11608); [qexec_execute_duplicate_key_update](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12501); [qexec_execute_increment](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L14532); [qexec_execute_insert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L13637); [qexec_execute_insert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L13817); [qexec_execute_update](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L10790); [qexec_execute_update](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L10971); [qexec_remove_duplicates_for_replace](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12066); [process_object](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/compactdb_sr.c#L263); [heap_object_upgrade_domain](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L19265); [locator_check_primary_key_delete](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L4512); [locator_check_primary_key_update](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L4854).

**Added targets:** [locator_allocate_copy_area_by_attr_info_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7792); [locator_insert_force_internal](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7812); [partition_prune_insert_by_attrinfo](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7776); [partition_prune_update_by_attrinfo](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7782).

**Removed targets:** [locator_insert_force](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7708).

**Retained targets:** [assert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7821); [er_clear](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7744); [er_errid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7740); [er_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7862); [heap_attrinfo_check_unique_index](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7825); [heap_clean_get_context](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7704); [heap_get_last_version](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7703); [heap_init_get_context](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7701); [locator_allocate_copy_area_by_attr_info](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7799); [locator_delete_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7852); [locator_free_copy_area](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7843); [locator_lock_and_get_object](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7721); [locator_update_force](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7831); [lock_has_xlock_or_self_lock](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7707).

</details>

<a id="f32"></a>

### F32 · `locator_mvcc_reev_cond_assigns` — modified

**Purpose:** Reevaluate conditions and assignments against a current row version.

**Change:** Pass NULL owner and NULL probe output to copy-area construction.

**Reason:** Keep the existing normal transformation behavior after the interface gains two parameters.

**Relevant direct callers:** locator_mvcc_reev_cond_and_assignment [unchanged context].

**Relevant direct callees:** locator_allocate_copy_area_by_attr_info.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L13802); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L13696).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** [locator_mvcc_reev_cond_and_assignment](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L13654).

**HEAD callers:** [locator_mvcc_reev_cond_and_assignment](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L13760).

**Added targets:** None.

**Removed targets:** None.

**Retained targets:** [fetch_peek_dbval](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L13862); [heap_attrinfo_clear_dbvalues](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L13849); [heap_attrinfo_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L13868); [locator_allocate_copy_area_by_attr_info](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L13889); [locator_free_copy_area](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L13884); [locator_mvcc_reeval_scan_filters](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L13834); [pr_clear_value](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L13871).

</details>

<a id="f33"></a>

### F33 · `scoped_sa_server` — newly created

**Purpose:** Enter server allocation mode for a direct server-interface test call.

**Change:** Increment db_on_server on construction.

**Reason:** The standalone SQL harness normally acts as a client; these direct calls need server allocation rules.

**Evidence:** [479cd960:44](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L44). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** Automatic scoped_sa_server objects in the direct-interface SQL tests invoke construction/destruction through C++ lifetime rules. These implicit calls are not in the named-call index.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** None.

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f34"></a>

### F34 · `~scoped_sa_server` — newly created

**Purpose:** Leave the temporary server allocation mode.

**Change:** Decrement db_on_server when the scope ends.

**Reason:** Restore the previous mode, including when a fatal test assertion returns early.

**Evidence:** [479cd960:48](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L48). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** Automatic scoped_sa_server objects in the direct-interface SQL tests invoke construction/destruction through C++ lifetime rules. These implicit calls are not in the named-call index.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** None.

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f35"></a>

### F35 · `get_string_column` — newly created

**Purpose:** Read a string from a SHOW result column.

**Change:** Fetch a DB_VALUE, reject a missing string, copy it into std::string and clear the DB_VALUE.

**Reason:** The ownership test must distinguish the root row from p0 and p1 by table name.

**Evidence:** [479cd960:183](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L183). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** [OosSqlShow.PartitionedForceOutlineStoresOosInPrunedHeap](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L469).

**Added targets:** [db_get_string](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L193); [db_make_null](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L189); [db_query_get_tuple_value](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L190); [db_value_clear](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L204).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f36"></a>

### F36 · `unqualified_table_name` — newly created

**Purpose:** Remove a schema prefix from a reported table name.

**Change:** Return the part after the last dot, or the whole name when no dot exists.

**Reason:** Ownership assertions should compare table names without depending on qualification.

**Evidence:** [479cd960:208](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L208). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** [OosSqlShow.PartitionedForceOutlineStoresOosInPrunedHeap](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L476).

**Added targets:** None.

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f37"></a>

### F37 · `expect_sql_count` — newly created

**Purpose:** Check one integer SQL result.

**Change:** Run fetch_single_int and compare with the expected count under SCOPED_TRACE.

**Reason:** Repeated failure-path tests need a short check for rows that must remain or must not appear.

**Evidence:** [479cd960:215](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L215). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** [OosSqlShow.EffectiveInsertRoutePreservesOmittedAssignments](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1336); [OosSqlShow.EffectiveKeyCodecFailureClearsOutputAndPreservesAssignment](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1200); [OosSqlShow.EffectiveRoutingFailurePreservesAssignmentsAndPublication](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1268); [OosSqlShow.PartitionHashNullOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L577); [OosSqlShow.PartitionHashNullOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L578); [OosSqlShow.PartitionHashNullOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L581); [OosSqlShow.PartitionInsertCompressedExpressionKey](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1657); [OosSqlShow.PartitionInsertCompressedExpressionKey](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1659); [OosSqlShow.PartitionInsertDynamicDefault](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1621); [OosSqlShow.PartitionInsertGeneratedKeysAndDomainConversion](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1603); [OosSqlShow.PartitionInsertGeneratedKeysAndDomainConversion](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1605); [OosSqlShow.PartitionInsertLegalKeySqlMatrix](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1533); [OosSqlShow.PartitionInsertLegalKeySqlMatrix](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1534); [OosSqlShow.PartitionInsertOwnsExternalKeyAndMultiplePayloads](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1561); [OosSqlShow.PartitionInsertOwnsExternalKeyAndMultiplePayloads](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1565); [OosSqlShow.PartitionInsertRetainsBigoneRejectionBeforeOos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1584); [OosSqlShow.PartitionInsertRetainsBigoneRejectionBeforeOos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1591); [OosSqlShow.PartitionInsertUsesColumnCollation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1640); [OosSqlShow.PartitionInsertUsesColumnCollation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1642); [OosSqlShow.PartitionListExpressionAndFailedBatchOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L547); [OosSqlShow.PartitionListExpressionAndFailedBatchOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L554); [OosSqlShow.PartitionListExpressionAndFailedBatchOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L555); [OosSqlShow.PartitionListExpressionAndFailedBatchOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L558); [OosSqlShow.PartitionListRejectsNullWithoutDestination](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L642); [OosSqlShow.PartitionListRejectsNullWithoutDestination](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L649); [OosSqlShow.PartitionListRejectsNullWithoutDestination](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L650); [OosSqlShow.PartitionLobPreparationAndIndexFailuresPreserveCommittedValues](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1099); [OosSqlShow.PartitionLobPreparationAndIndexFailuresPreserveCommittedValues](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1106); [OosSqlShow.PartitionPreparationFailuresRollBackAndAllowNextWrite](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1051); [OosSqlShow.PartitionPreparationFailuresRollBackAndAllowNextWrite](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1054); [OosSqlShow.PartitionPreparationFailuresRollBackAndAllowNextWrite](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1060); [OosSqlShow.PartitionRangeBoundaryAndNullOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L519); [OosSqlShow.PartitionRangeBoundaryAndNullOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L520); [OosSqlShow.PartitionRangeBoundaryAndNullOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L523); [OosSqlShow.PartitionRangeExpressionValidationAndMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L610); [OosSqlShow.PartitionRangeExpressionValidationAndMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L611); [OosSqlShow.PartitionRangeExpressionValidationAndMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L613); [OosSqlShow.PartitionRangeExpressionValidationAndMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L622); [OosSqlShow.PartitionRangeExpressionValidationAndMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L623); [OosSqlShow.PartitionRangeExpressionValidationAndMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L624); [OosSqlShow.PartitionUpdateDedicatedIncrementsAndArithmetic](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L822); [OosSqlShow.PartitionUpdateDedicatedIncrementsAndArithmetic](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L827); [OosSqlShow.PartitionUpdateDedicatedIncrementsAndArithmetic](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L829); [OosSqlShow.PartitionUpdateDedicatedIncrementsAndArithmetic](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L831); [OosSqlShow.PartitionUpdateDedicatedIncrementsAndArithmetic](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L837); [OosSqlShow.PartitionUpdateDedicatedIncrementsAndArithmetic](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L842); [OosSqlShow.PartitionUpdateLegalKeysAndNullMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L732); [OosSqlShow.PartitionUpdateLegalKeysAndNullMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L735); [OosSqlShow.PartitionUpdateLegalKeysAndNullMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L741); [OosSqlShow.PartitionUpdateLegalKeysAndNullMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L743); [OosSqlShow.PartitionUpdateLobLifecycle](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L783); [OosSqlShow.PartitionUpdateLobLifecycle](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L790); [OosSqlShow.PartitionUpdateLobLifecycle](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L793); [OosSqlShow.PartitionUpdateOldOosKeyAndRepresentation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L761); [OosSqlShow.PartitionUpdateOldOosKeyAndRepresentation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L765); [OosSqlShow.PartitionUpdateOldOosKeyAndRepresentation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L770); [OosSqlShow.PartitionUpdatePreservesDuplicateProbesAndNonKeyIncrement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L665); [OosSqlShow.PartitionUpdatePreservesDuplicateProbesAndNonKeyIncrement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L668); [OosSqlShow.PartitionUpdatePreservesDuplicateProbesAndNonKeyIncrement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L671); [OosSqlShow.PartitionUpdatePreservesDuplicateProbesAndNonKeyIncrement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L673); [OosSqlShow.PartitionUpdateStringDomains](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L685); [OosSqlShow.PartitionUpdateStringDomains](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L694).

**Added targets:** [fetch_single_int](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L220).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f38"></a>

### F38 · `expect_oos_records` — newly created

**Purpose:** Check one table’s OOS file and chunk count.

**Change:** Run SHOW HEAP OOS, inspect the two counts and require exactly one result row.

**Reason:** A successful SQL read alone cannot detect OOS data written for the wrong heap.

**Evidence:** [479cd960:224](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L224). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** [OosSqlShow.EffectiveInsertRouteLegalKeyDefaults](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1492); [OosSqlShow.EffectiveInsertRouteLegalKeyDefaults](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1493); [OosSqlShow.EffectiveInsertRouteLegalKeyDefaults](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1494); [OosSqlShow.EffectiveInsertRoutePreservesAssignedChar](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1414); [OosSqlShow.EffectiveInsertRoutePreservesAssignedChar](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1415); [OosSqlShow.EffectiveInsertRoutePreservesAssignedChar](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1416); [OosSqlShow.EffectiveInsertRoutePreservesOmittedAssignments](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1337); [OosSqlShow.EffectiveInsertRoutePreservesOmittedAssignments](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1338); [OosSqlShow.EffectiveInsertRoutePreservesOmittedAssignments](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1339); [OosSqlShow.EffectiveKeyCodecFailureClearsOutputAndPreservesAssignment](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1201); [OosSqlShow.EffectiveKeyCodecFailureClearsOutputAndPreservesAssignment](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1202); [OosSqlShow.EffectiveRoutingFailurePreservesAssignmentsAndPublication](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1269); [OosSqlShow.EffectiveRoutingFailurePreservesAssignmentsAndPublication](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1270); [OosSqlShow.EffectiveRoutingFailurePreservesAssignmentsAndPublication](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1271); [OosSqlShow.EffectiveUpdateRoutePreservesOldKeyAndPendingIncrement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L997); [OosSqlShow.EffectiveUpdateRoutePreservesOldKeyAndPendingIncrement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L998); [OosSqlShow.EffectiveUpdateRoutePreservesOldKeyAndPendingIncrement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L999); [OosSqlShow.PartitionHashNullOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L584); [OosSqlShow.PartitionHashNullOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L585); [OosSqlShow.PartitionHashNullOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L586); [OosSqlShow.PartitionInsertCompressedExpressionKey](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1661); [OosSqlShow.PartitionInsertCompressedExpressionKey](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1662); [OosSqlShow.PartitionInsertCompressedExpressionKey](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1663); [OosSqlShow.PartitionInsertDynamicDefault](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1627); [OosSqlShow.PartitionInsertDynamicDefault](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1628); [OosSqlShow.PartitionInsertDynamicDefault](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1629); [OosSqlShow.PartitionInsertGeneratedKeysAndDomainConversion](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1608); [OosSqlShow.PartitionInsertGeneratedKeysAndDomainConversion](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1609); [OosSqlShow.PartitionInsertGeneratedKeysAndDomainConversion](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1610); [OosSqlShow.PartitionInsertLegalKeySqlMatrix](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1542); [OosSqlShow.PartitionInsertLegalKeySqlMatrix](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1543); [OosSqlShow.PartitionInsertLegalKeySqlMatrix](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1544); [OosSqlShow.PartitionInsertOwnsExternalKeyAndMultiplePayloads](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1570); [OosSqlShow.PartitionInsertOwnsExternalKeyAndMultiplePayloads](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1571); [OosSqlShow.PartitionInsertOwnsExternalKeyAndMultiplePayloads](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1572); [OosSqlShow.PartitionInsertRetainsBigoneRejectionBeforeOos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1585); [OosSqlShow.PartitionInsertRetainsBigoneRejectionBeforeOos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1586); [OosSqlShow.PartitionInsertRetainsBigoneRejectionBeforeOos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1587); [OosSqlShow.PartitionInsertRetainsBigoneRejectionBeforeOos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1592); [OosSqlShow.PartitionInsertUsesColumnCollation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1644); [OosSqlShow.PartitionInsertUsesColumnCollation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1645); [OosSqlShow.PartitionInsertUsesColumnCollation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1646); [OosSqlShow.PartitionListExpressionAndFailedBatchOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L548); [OosSqlShow.PartitionListExpressionAndFailedBatchOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L549); [OosSqlShow.PartitionListExpressionAndFailedBatchOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L550); [OosSqlShow.PartitionListExpressionAndFailedBatchOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L562); [OosSqlShow.PartitionListExpressionAndFailedBatchOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L563); [OosSqlShow.PartitionListExpressionAndFailedBatchOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L564); [OosSqlShow.PartitionListRejectsNullWithoutDestination](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L643); [OosSqlShow.PartitionListRejectsNullWithoutDestination](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L644); [OosSqlShow.PartitionListRejectsNullWithoutDestination](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L645); [OosSqlShow.PartitionListRejectsNullWithoutDestination](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L652); [OosSqlShow.PartitionListRejectsNullWithoutDestination](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L653); [OosSqlShow.PartitionListRejectsNullWithoutDestination](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L654); [OosSqlShow.PartitionLobPreparationAndIndexFailuresPreserveCommittedValues](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1101); [OosSqlShow.PartitionLobPreparationAndIndexFailuresPreserveCommittedValues](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1102); [OosSqlShow.PartitionLobPreparationAndIndexFailuresPreserveCommittedValues](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1103); [OosSqlShow.PartitionLobPreparationAndIndexFailuresPreserveCommittedValues](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1108); [OosSqlShow.PartitionPreparationFailuresRollBackAndAllowNextWrite](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1012); [OosSqlShow.PartitionPreparationFailuresRollBackAndAllowNextWrite](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1013); [OosSqlShow.PartitionPreparationFailuresRollBackAndAllowNextWrite](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1055); [OosSqlShow.PartitionPreparationFailuresRollBackAndAllowNextWrite](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1056); [OosSqlShow.PartitionPreparationFailuresRollBackAndAllowNextWrite](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1057); [OosSqlShow.PartitionPreparationFailuresRollBackAndAllowNextWrite](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1063); [OosSqlShow.PartitionPreparationFailuresRollBackAndAllowNextWrite](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1065); [OosSqlShow.PartitionRangeBoundaryAndNullOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L526); [OosSqlShow.PartitionRangeBoundaryAndNullOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L527); [OosSqlShow.PartitionRangeBoundaryAndNullOwnership](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L528); [OosSqlShow.PartitionRangeExpressionValidationAndMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L615); [OosSqlShow.PartitionRangeExpressionValidationAndMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L616); [OosSqlShow.PartitionRangeExpressionValidationAndMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L617); [OosSqlShow.PartitionRangeExpressionValidationAndMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L627); [OosSqlShow.PartitionRangeExpressionValidationAndMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L628); [OosSqlShow.PartitionRangeExpressionValidationAndMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L629); [OosSqlShow.PartitionUpdateDedicatedIncrementsAndArithmetic](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L824); [OosSqlShow.PartitionUpdateDedicatedIncrementsAndArithmetic](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L825); [OosSqlShow.PartitionUpdateLegalKeysAndNullMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L737); [OosSqlShow.PartitionUpdateLegalKeysAndNullMovement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L738); [OosSqlShow.PartitionUpdateLobLifecycle](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L785); [OosSqlShow.PartitionUpdateLobLifecycle](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L787); [OosSqlShow.PartitionUpdateOldOosKeyAndRepresentation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L767); [OosSqlShow.PartitionUpdateOldOosKeyAndRepresentation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L768); [OosSqlShow.PartitionUpdatePreservesDuplicateProbesAndNonKeyIncrement](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L674); [OosSqlShow.PartitionUpdateStringDomains](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L686); [OosSqlShow.PartitionUpdateStringDomains](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L696); [OosSqlShow.PartitionUpdateStringDomains](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L698).

**Added targets:** [db_query_end](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L238); [db_query_next_tuple](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L237); [get_int_column](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L234); [show_heap_oos_query](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L230).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f39"></a>

### F39 · `OosSqlShow.PartitionedForceOutlineStoresOosInPrunedHeap` — newly created

**Purpose:** Verify PartitionedForceOutlineStoresOosInPrunedHeap.

**Change:** Force a 64-byte value; verify value equality and root/p0/p1 ownership (0/1/0 chunks). Small forced data isolates policy from the ordinary size gate.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:437](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L437). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L447); [db_query_end](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L503); [db_query_next_tuple](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L496); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L445); [fetch_single_int](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L450); [get_int_column](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L473); [get_string_column](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L469); [show_heap_oos_query](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L456); [unqualified_table_name](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L476).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f40"></a>

### F40 · `OosSqlShow.PartitionRangeBoundaryAndNullOwnership` — newly created

**Purpose:** Verify PartitionRangeBoundaryAndNullOwnership.

**Change:** Alternate keys 10, 9, 11 and NULL in one INSERT; assert both boundary placement and per-child two-chunk totals. Reused routing state must not leak between rows.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:506](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L506). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L517); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L514); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L528); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L523).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f41"></a>

### F41 · `OosSqlShow.PartitionListExpressionAndFailedBatchOwnership` — newly created

**Purpose:** Verify PartitionListExpressionAndFailedBatchOwnership.

**Change:** Route ABS(id) over LIST partitions, fail a batch after a valid first row, explicitly abort, then insert again. Check original values, ownership and successful recovery of reusable state.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:531](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L531). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_abort_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L546); [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L553); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L552); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L564); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L558).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f42"></a>

### F42 · `OosSqlShow.PartitionHashNullOwnership` — newly created

**Purpose:** Verify PartitionHashNullOwnership.

**Change:** Exercise HASH with repeated keys and NULL; verify known p0/p1 placements and owner counts. This tests the existing hash rule for the chosen integers, not a general hash formula.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:567](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L567). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L575); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L572); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L586); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L581).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f43"></a>

### F43 · `OosSqlShow.PartitionRangeExpressionValidationAndMovement` — newly created

**Purpose:** Verify PartitionRangeExpressionValidationAndMovement.

**Change:** Use RANGE(id+1), reject a missing destination and explicit-child mismatch for INSERT/UPDATE, then perform a root-targeted move. Error codes and unchanged pre-error data discriminate the contracts.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:589](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L589). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_abort_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L608); [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L621); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L620); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L629); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L624).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f44"></a>

### F44 · `OosSqlShow.PartitionListRejectsNullWithoutDestination` — newly created

**Purpose:** Verify PartitionListRejectsNullWithoutDestination.

**Change:** A LIST with no NULL destination rejects NULL before publishing any OOS file; a subsequent valid write creates only p1's file.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:632](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L632). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_abort_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L641); [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L648); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L647); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L654); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L650).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f45"></a>

### F45 · `OosSqlShow.PartitionUpdatePreservesDuplicateProbesAndNonKeyIncrement` — newly created

**Purpose:** Verify PartitionUpdatePreservesDuplicateProbesAndNonKeyIncrement.

**Change:** Combine non-key INCR, ODKU moving id=11 to 9 and REPLACE. Assert final values and no root OOS file. This does not enumerate every probe-side child orphan or SERVER_MODE lifecycle case.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:657](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L657). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L663); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L670); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L674); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L673).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f46"></a>

### F46 · `OosSqlShow.PartitionUpdateStringDomains` — newly created

**Purpose:** Verify PartitionUpdateStringDomains.

**Change:** Update case-insensitive VARCHAR keys and compressed expression keys across a length boundary. Check the logical key and owner, with only forced payload OOS in the DEFAULT-policy compressed-key case.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:677](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L677). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L693); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L698); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L694).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f47"></a>

### F47 · `OosSqlShow.PartitionUpdateLegalKeysAndNullMovement` — newly created

**Purpose:** Verify PartitionUpdateLegalKeysAndNullMovement.

**Change:** Loop 13 supported key specifications through default INSERT, unchanged-key UPDATE, NULL movement, reassignment and rollback. Explicit padded CHAR bounds distinguish stored-domain behavior.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:701](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L701). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_abort_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L742); [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L730); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L740); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L738); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L743).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f48"></a>

### F48 · `OosSqlShow.PartitionUpdateOldOosKeyAndRepresentation` — newly created

**Purpose:** Verify PartitionUpdateOldOosKeyAndRepresentation.

**Change:** Use an OOS-backed string key, add a schema column, update payload then move key and abort. Check inherited default and multi-payload preservation across representation change.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:748](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L748). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_abort_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L769); [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L759); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L763); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L768); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L770).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f49"></a>

### F49 · `OosSqlShow.PartitionUpdateLobLifecycle` — newly created

**Purpose:** Verify PartitionUpdateLobLifecycle.

**Change:** Move a row containing inline CLOB and forced BLOB locator, then change both LOBs and abort. Read external LOB contents and count two OOS chunks at destination; locator storage is distinct from external payload storage.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:774](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L774). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_abort_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L792); [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L781); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L788); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L787); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L793).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f50"></a>

### F50 · `OosSqlShow.PartitionUpdateDedicatedIncrementsAndArithmetic` — newly created

**Purpose:** Verify PartitionUpdateDedicatedIncrementsAndArithmetic.

**Change:** Test INCR/DECR and ordinary arithmetic for SMALLINT/INT/BIGINT, including extrema where the dedicated increment behavior resets to zero. Ensure the same key used for routing is eventually stored.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:797](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L797). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L840); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L841); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L825); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L842).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f51"></a>

### F51 · `OosSqlShow.EffectiveUpdateRouteUsesMissingHistoricalKeyDefault` — newly created

**Purpose:** Verify EffectiveUpdateRouteUsesMissingHistoricalKeyDefault.

**Change:** Construct old serialized bytes before adding the key, then route an unchanged UPDATE using the missing-attribute default. Compare with an independent inline reference; no actual heap row is installed, isolating representation decoding from ALTER redistribution.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:846](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L846). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L873); [db_find_class](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L874); [db_identifier](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L874); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L871); [heap_attrinfo_end](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L911); [heap_attrinfo_start](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L882); [heap_attrinfo_transform_to_disk_probe_oos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L901); [partition_clear_pruning_context](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L908); [partition_load_pruning_context](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L885); [partition_prune_update](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L904); [partition_prune_update_by_attrinfo](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L888); [thread_get_thread_entry_info](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L879).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f52"></a>

### F52 · `OosSqlShow.EffectiveUpdateRoutePreservesOldKeyAndPendingIncrement` — newly created

**Purpose:** Verify EffectiveUpdateRoutePreservesOldKeyAndPendingIncrement.

**Change:** Prepare old key 10 and test unchanged, pending +1, pending -1 and assigned 9. Assert source state/representation/increment remain unchanged after repeated routing, then assert the real transform applies once and final OID/HFID agrees.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:915](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L915). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_attribute_id](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L924); [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L920); [db_find_class](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L925); [db_get_attribute](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L924); [db_get_int](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L984); [db_identifier](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L925); [db_make_int](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L950); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L917); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L999); [heap_attrinfo_end](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L995); [heap_attrinfo_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L951); [heap_attrinfo_start](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L944); [heap_attrinfo_transform_to_disk_probe_oos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L936); [heap_attrinfo_transform_to_disk_with_oos_owner](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L981); [heap_attrvalue_locate](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L945); [partition_prune_update](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L988); [partition_prune_update_by_attrinfo](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L978); [thread_get_thread_entry_info](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L928).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f53"></a>

### F53 · `OosSqlShow.PartitionPreparationFailuresRollBackAndAllowNextWrite` — newly created

**Purpose:** Verify PartitionPreparationFailuresRollBackAndAllowNextWrite.

**Change:** Inject failures after one publication, after publication reset, before VFID lookup and during OID publication allocation, for INSERT and moving UPDATE. Disarm hooks, abort, check committed values/counts and retry successfully. Multi-chunk payload prevents a single small batch hiding partial progress.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:1002](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1002). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [bridge_heap_attrinfo_disarm_publication_reset_failure](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1046); [bridge_heap_attrinfo_fail_after_oos_publication_reset_once](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1031); [db_abort_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1064); [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1011); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1059); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1065); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1060); [heap_oos_test_disarm_fail_before_vfid_lookup](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1047); [heap_oos_test_fail_before_vfid_lookup_once](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1035); [oos_test_disarm_insert_publication_failures](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1045); [oos_test_fail_insert_many_after_publications](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1027); [oos_test_throw_bad_alloc_on_next_oid_publication](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1039).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f54"></a>

### F54 · `OosSqlShow.PartitionLobPreparationAndIndexFailuresPreserveCommittedValues` — newly created

**Purpose:** Verify PartitionLobPreparationAndIndexFailuresPreserveCommittedValues.

**Change:** Fail LOB preparation before VFID lookup and fail a moving update on a unique key, with/without new LOB assignments. Abort and verify committed LOB contents and OOS counts, then prove a new write works.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:1070](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1070). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_abort_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1109); [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1079); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1104); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1108); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1106); [heap_oos_test_disarm_fail_before_vfid_lookup](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1096); [heap_oos_test_fail_before_vfid_lookup_once](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1087).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f55"></a>

### F55 · `OosSqlShow.EffectiveKeyCodecFailureClearsOutputAndPreservesAssignment` — newly created

**Purpose:** Verify EffectiveKeyCodecFailureClearsOutputAndPreservesAssignment.

**Change:** Swap in a failing scalar codec on private attribute/domain copies only. Fail write and partial read; expect a NULL output and unchanged source assignment, restore the codec and retry. It avoids mutating cached shared schema.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:1113](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1113). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_attribute_id](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1149); [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1143); [db_find_class](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1144); [db_get_attribute](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1147); [db_get_string](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1194); [db_get_string_size](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1194); [db_identifier](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1146); [db_make_null](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1190); [db_make_string](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1163); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1140); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1202); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1200); [heap_attrinfo_end](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1198); [heap_attrinfo_get_effective_key](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1191); [heap_attrinfo_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1164); [heap_attrinfo_start](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1161); [heap_attrvalue_locate](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1165); [pr_clear_value](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1196); [thread_get_thread_entry_info](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1159).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f56"></a>

### F56 · `failing_codec` — newly created

**Purpose:** Install controlled codec failures on a private PR_TYPE copy.

**Change:** The constructor replaces either the read or write callback with a failing lambda.

**Reason:** Test effective-key cleanup without modifying shared cached schema metadata.

**Evidence:** [479cd960:1119](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1119). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** The enclosing EffectiveKeyCodecFailureClearsOutputAndPreservesAssignment test constructs this local type; callbacks run later through codec dispatch.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** None.

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f57"></a>

### F57 · `OosSqlShow.EffectiveRoutingFailurePreservesAssignmentsAndPublication` — newly created

**Purpose:** Verify EffectiveRoutingFailurePreservesAssignmentsAndPublication.

**Change:** Seed OID/LSA publication containers and alternate valid/missing destinations in one pruning context. Assert routing preserves source assignments and both markers; reset test markers on exit. These are preparation-state assertions, not durability tests.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:1205](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1205). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_attribute_id](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1215); [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1210); [db_find_class](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1217); [db_get_attribute](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1215); [db_get_int](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1249); [db_identifier](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1217); [db_make_int](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1238); [er_clear](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1262); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1207); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1271); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1268); [heap_attrinfo_end](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1266); [heap_attrinfo_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1239); [heap_attrinfo_start](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1222); [heap_attrvalue_locate](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1251); [heap_oos_begin_insert_publication](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1264); [partition_clear_pruning_context](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1265); [partition_init_pruning_context](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1224); [partition_prune_insert_by_attrinfo](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1242); [thread_get_thread_entry_info](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1220).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f58"></a>

### F58 · `OosSqlShow.EffectiveInsertRoutePreservesOmittedAssignments` — newly created

**Purpose:** Verify EffectiveInsertRoutePreservesOmittedAssignments.

**Change:** Route an omitted CHAR default before any full transform; all candidate slots remain uninitialized and NULL. A separate reference transform must select the same expected child and HFID, without any OOS files.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:1274](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1274). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1280); [db_find_class](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1284); [db_identifier](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1286); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1276); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1339); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1336); [heap_attrinfo_end](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1334); [heap_attrinfo_start](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1293); [heap_attrinfo_transform_to_disk_probe_oos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1318); [partition_prune_insert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1324); [partition_prune_insert_by_attrinfo](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1302); [thread_get_thread_entry_info](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1289).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f59"></a>

### F59 · `OosSqlShow.EffectiveInsertRoutePreservesAssignedChar` — newly created

**Purpose:** Verify EffectiveInsertRoutePreservesAssignedChar.

**Change:** Assign an unpadded CHAR value and snapshot its bytes/state. Early routing must match a separately serialized reference while preserving those original bytes and the untouched payload slot.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:1342](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1342). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_attribute_id](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1354); [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1348); [db_find_class](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1355); [db_get_attribute](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1352); [db_get_string](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1391); [db_get_string_size](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1391); [db_identifier](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1357); [db_make_string](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1371); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1344); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1416); [heap_attrinfo_end](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1412); [heap_attrinfo_set](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1373); [heap_attrinfo_start](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1364); [heap_attrinfo_transform_to_disk_probe_oos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1396); [partition_prune_insert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1402); [partition_prune_insert_by_attrinfo](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1382); [thread_get_thread_entry_info](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1360).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f60"></a>

### F60 · `OosSqlShow.EffectiveInsertRouteLegalKeyDefaults` — newly created

**Purpose:** Verify EffectiveInsertRouteLegalKeyDefaults.

**Change:** Compare effective INSERT routing with an independent serialized reference across 13 default key types. Check source slots stay uninitialized and no root/child OOS publication occurs.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:1419](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1419). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1447); [db_find_class](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1448); [db_identifier](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1450); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1446); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1494); [heap_attrinfo_end](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1490); [heap_attrinfo_start](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1457); [heap_attrinfo_transform_to_disk_probe_oos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1475); [partition_prune_insert](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1481); [partition_prune_insert_by_attrinfo](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1465); [thread_get_thread_entry_info](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1453).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f61"></a>

### F61 · `OosSqlShow.PartitionInsertLegalKeySqlMatrix` — newly created

**Purpose:** Verify PartitionInsertLegalKeySqlMatrix.

**Change:** Execute assigned, NULL and omitted/default INSERTs across 13 types using HASH. Validate logical data, per-child row/chunk correspondence, and print literal partition results for a separate reference run; this test alone is not that separate run.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:1498](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1498). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1529); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1528); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1544); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1534); [fetch_single_int](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1538); [printf](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1541).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f62"></a>

### F62 · `OosSqlShow.PartitionInsertOwnsExternalKeyAndMultiplePayloads` — newly created

**Purpose:** Verify PartitionInsertOwnsExternalKeyAndMultiplePayloads.

**Change:** Insert an externalized expression key plus forced small and ordinary large VARBIT payloads into both children. Three single-chunk values per row make the expected physical count exactly three per child.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:1548](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1548). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1560); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1555); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1572); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1565).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f63"></a>

### F63 · `OosSqlShow.PartitionInsertRetainsBigoneRejectionBeforeOos` — newly created

**Purpose:** Verify PartitionInsertRetainsBigoneRejectionBeforeOos.

**Change:** Force OOS beside BIT(140000), expect the exact bigone rejection and zero OOS files after abort, then prove the non-OOS whole-record overflow case remains valid with NULL payload.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:1575](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1575). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_abort_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1583); [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1590); [er_errid](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1582); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1589); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1592); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1591).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f64"></a>

### F64 · `OosSqlShow.PartitionInsertGeneratedKeysAndDomainConversion` — newly created

**Purpose:** Verify PartitionInsertGeneratedKeysAndDomainConversion.

**Change:** AUTO_INCREMENT produces 9 then 10 across a range boundary; string input '11' is converted to integer. Check values and owner counts 1/2 in the children.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:1595](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1595). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1602); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1601); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1610); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1605).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f65"></a>

### F65 · `OosSqlShow.PartitionInsertDynamicDefault` — newly created

**Purpose:** Verify PartitionInsertDynamicDefault.

**Change:** A CURRENT_DATE default is compared against an explicit CURRENT_DATE captured in the same INSERT. Assert logical equality and physical ownership rather than hard-coding today's date or hash destination.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:1613](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1613). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1620); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1618); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1629); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1621); [fetch_single_int](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1625).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f66"></a>

### F66 · `OosSqlShow.PartitionInsertUsesColumnCollation` — newly created

**Purpose:** Verify PartitionInsertUsesColumnCollation.

**Change:** Mix 'BETA', 'AlPhA' and 'beta' with utf8_en_ci LIST partitions. Case-insensitive routing must preserve payload identity and per-child chunk totals.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:1632](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1632). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1639); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1637); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1646); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1642).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f67"></a>

### F67 · `OosSqlShow.PartitionInsertCompressedExpressionKey` — newly created

**Purpose:** Verify PartitionInsertCompressedExpressionKey.

**Change:** Use forced compressed VARCHAR expression keys at lengths 2999/3000, plus forced payloads. Assert both value equality and two OOS chunks in each selected child.

**Reason:** Add an executable check for this behavior; the test name alone is not evidence that it passed.

**Evidence:** [479cd960:1649](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1649). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/sql/test_oos_sql_show.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [db_commit_transaction](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1656); [exec_sql](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1654); [expect_oos_records](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1663); [expect_sql_count](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1659).

**Removed targets:** None.

**Retained targets:** None.

</details>

<a id="f68"></a>

### F68 · `OosRealVacuum.DISABLED_RolledBackUpdateKeepsCommittedOosAfterVacuum` — newly created

**Purpose:** Reproduce a committed OOS value becoming unreadable after an UPDATE rollback and real vacuum.

**Change:** Add a DISABLED_ test: commit an original value and a separate witness, roll back the replacement, read the original, vacuum the deleted witness, then read the original again.

**Reason:** Keep the regression available without pretending that a daemon wakeup proves reclamation or that the disabled test is passing. This is not a partition-specific test.

**Evidence:** [479cd960:833](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/test_oos_real_vacuum_server.cpp#L833). This definition is absent from the [base file](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/unit_tests/oos/test_oos_real_vacuum_server.cpp).

**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.

<details>
<summary>Direct call sites and base → HEAD call changes</summary>

**Base callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**HEAD callers:** No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.

**Added targets:** [build_heap_recdes_with_oos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/test_oos_real_vacuum_server.cpp#L851); [delete_row_and_close_block](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/test_oos_real_vacuum_server.cpp#L861); [heap_update_mvcc](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/test_oos_real_vacuum_server.cpp#L853); [insert_row_with_oos](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/test_oos_real_vacuum_server.cpp#L842); [wait_for_vacuum](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/test_oos_real_vacuum_server.cpp#L862); [xtran_server_abort](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/test_oos_real_vacuum_server.cpp#L854).

**Removed targets:** None.

**Retained targets:** None.

</details>

## Anonymous callback bodies — newly created

These callbacks are nested inside the new failing_codec constructor (F number above). They are listed separately from named functions.

### A01 · failing_codec read callback

**Change and reason:** Assign f_data_readval a lambda that creates a partially decoded string, clones it into the output, then returns ER_FAILED. This checks that heap_attrinfo_get_effective_key clears partially produced output on a read failure while preserving the original assignment. Direct named calls in this callback are db_make_string and pr_clone_value. The codec invokes it indirectly; the enclosing test does not directly call those operations merely by defining the lambda. [Source](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1123).

### A02 · failing_codec write callback

**Change and reason:** Assign f_data_writeval a lambda that returns ER_FAILED immediately. This checks the write-failure branch before decoding starts. It contains no direct function call. Invocation is indirect through the codec. [Source](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L1133).

## Unchanged context functions

These functions appeared in the earlier explanation. Their definitions are unchanged between base and HEAD.

- **heap_oos_insert_serialized_values — unchanged.** Takes the supplied class, obtains its heap and OOS file, then directly calls oos_insert_many. The PR changes which class its caller supplies. [Source](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_oos.cpp#L631).
- **oos_insert_many — unchanged.** Writes the requested values to the supplied OOS file. It does not decide which partition should own the row. [Source](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/oos_file.cpp#L2193).
- **locator_move_record — unchanged.** Inserts a moved row at the destination and then deletes it from the source. It is directly called by modified locator_update_force. [Source](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5402).
- **vacuum_oos_find_vfid_for_heap_record — unchanged.** Looks up the OOS file belonging to the heap being cleaned; this revision explicitly aborts on the missing-file condition. It explains the impact of wrong ownership, but is not a newly added step in the INSERT call path. [Source](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/vacuum_oos.cpp#L401).

## Diff-hunk coverage and changes outside definitions

Every hunk in the frozen diff is accounted for below. A declaration and its definition are one function identity, not two functions. Comments and blank separators are outside definition spans. Header signatures, test includes, local class scaffolding and TIMEOUT 300 are recorded here rather than called deleted/new functions. Changed return-type/storage-class lines next to a recovered GNU-style definition belong to that definition's declaration.

<details>
<summary>H01 · src/query/partition.c</summary>

**Definitions:** No function body changes.

**Hunk explanation:** Declare the extracted evaluator, stable-key initializer and shared INSERT implementation before use. These are internal seams; the public entry points are declared separately in partition_sr.h.

**Outside definition spans:** 7 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-01).

</details>

<details>
<summary>H02 · src/query/partition.c</summary>

**Definitions:** [partition_find_partition_for_expr](#f01); [partition_find_partition_for_record](#f04).

**Hunk explanation:** Rename the core to partition_find_partition_for_expr, accept an explicit thread and borrowed destination output, and remove decoding from this function. Decoding is relocated to the record adapter in H05. The evaluator can now consume either an effective key or a decoded record key without duplicating partition semantics.

**Outside definition spans:** 20 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-02).

</details>

<details>
<summary>H03 · src/query/partition.c</summary>

**Definitions:** [partition_find_partition_for_expr](#f01); [partition_find_partition_for_record](#f04).

**Hunk explanation:** The evaluator no longer owns temporary record DB_VALUE cleanup. Return ER_PARTITION_NOT_EXIST directly on failed matching; the adapter that owns the key handles cleanup.

[Read this hunk](review.ko.html#hunk-03).

</details>

<details>
<summary>H04 · src/query/partition.c</summary>

**Definitions:** [partition_find_partition_for_expr](#f01); [partition_find_partition_for_record](#f04).

**Hunk explanation:** Keep the original no-destination/internal-error choice, replacing a cleanup jump with a direct return. This does not relax the requirement for exactly one destination.

[Read this hunk](review.ko.html#hunk-04).

</details>

<details>
<summary>H05 · src/query/partition.c</summary>

**Definitions:** [partition_find_partition_for_attrinfo](#f03); [partition_find_partition_for_expr](#f01); [partition_find_partition_for_record](#f04); [partition_start_key_attrinfo](#f02).

**Hunk explanation:** Return the context-owned OR_PARTITION, then add a reusable one-key slot and the attrinfo adapter. Clear stale key values before evaluation, mark the slot readable, prepare only the owned effective key, copy OID/HFID only after success and clear it on exit. Reintroduce the old record adapter: decode under root representation, restore the original ID, evaluate using the shared core, and retain destination representation patching.

**Outside definition spans:** 19 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-05).

</details>

<details>
<summary>H06 · src/query/partition.c</summary>

**Definitions:** [partition_find_partition_for_record](#f04).

**Hunk explanation:** Read rep_id from the returned partition instead of indexing with the evaluator's old local pos. The same selected descriptor supplies destination OID, HFID and representation ID.

[Read this hunk](review.ko.html#hunk-06).

</details>

<details>
<summary>H07 · src/query/partition.c</summary>

**Definitions:** No function body changes.

**Hunk explanation:** Rename the internal documentation and describe attr_info as an optional alternative to recdes. Remove the stale scan_cache parameter description because this internal function does not take it.

**Outside definition spans:** 4 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-07).

</details>

<details>
<summary>H08 · src/query/partition.c</summary>

**Definitions:** [partition_prune_insert](#f06); [partition_prune_insert_internal](#f05).

**Hunk explanation:** Make the implementation private and accept both recdes and attr_info. Public wrappers choose one; context loading, validation and cleanup remain shared.

[Read this hunk](review.ko.html#hunk-08).

</details>

<details>
<summary>H09 · src/query/partition.c</summary>

**Definitions:** [partition_prune_insert](#f06); [partition_prune_insert_internal](#f05).

**Hunk explanation:** A non-NULL attr_info routes a key with old_recdes=NULL; otherwise use the record adapter. Both feed the same later explicit-partition validation and cleanup path.

[Read this hunk](review.ko.html#hunk-09).

</details>

<details>
<summary>H10 · src/query/partition.c</summary>

**Definitions:** [partition_prune_insert](#f06); [partition_prune_insert_by_attrinfo](#f07).

**Hunk explanation:** The original signature becomes a wrapper passing NULL attrinfo. The new by_attrinfo wrapper passes NULL recdes and asserts assignments exist. UPDATE documentation is also revised to distinguish supplied old row from final new row.

**Outside definition spans:** 17 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-10).

</details>

<details>
<summary>H11 · src/query/partition.c</summary>

**Definitions:** [partition_prune_update](#f09); [partition_prune_update_internal](#f08).

**Hunk explanation:** Add optional attrinfo to a private UPDATE internal. Source-child to root discovery and the caller-owned context requirements remain in this common implementation.

[Read this hunk](review.ko.html#hunk-11).

</details>

<details>
<summary>H12 · src/query/partition.c</summary>

**Definitions:** [partition_prune_update](#f09); [partition_prune_update_internal](#f08).

**Hunk explanation:** In attrinfo mode, recdes is the supplied old row used for an unchanged key; in record mode it is the already serialized new row. Preserving this distinction avoids substituting current defaults for historical values.

[Read this hunk](review.ko.html#hunk-12).

</details>

<details>
<summary>H13 · src/query/partition.c</summary>

**Definitions:** [partition_prune_update](#f09); [partition_prune_update_by_attrinfo](#f10).

**Hunk explanation:** Keep the original UPDATE wrapper passing NULL attrinfo. Add by_attrinfo with explicit old_recdes. Both reuse validation and context lifetime; only the source of the key differs.

**Outside definition spans:** 8 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-13).

</details>

<details>
<summary>H14 · src/query/partition_sr.h</summary>

**Definitions:** No function body changes.

**Hunk explanation:** Expose INSERT and UPDATE by_attrinfo entry points to locator code; UPDATE includes the supplied old record. OID/HFID and optional superclass outputs match the existing routing interfaces.

**Outside definition spans:** 10 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-14).

</details>

<details>
<summary>H15 · src/query/query_executor.c</summary>

**Definitions:** [qexec_remove_duplicates_for_replace](#f11).

**Hunk explanation:** Add a local Boolean whose address selects suppression. False is an initial verdict, not a request to disable suppression.

[Read this hunk](review.ko.html#hunk-15).

</details>

<details>
<summary>H16 · src/query/query_executor.c</summary>

**Definitions:** [qexec_remove_duplicates_for_replace](#f11).

**Hunk explanation:** Pass NULL owner and a non-NULL verdict pointer when building the duplicate-search image. Preserve EXCLUDE_LOB. The image is never installed, so it must not create OOS chains.

[Read this hunk](review.ko.html#hunk-16).

</details>

<details>
<summary>H17 · src/query/query_executor.c</summary>

**Definitions:** [qexec_oid_of_duplicate_key_update](#f12).

**Hunk explanation:** Add the corresponding verdict storage for duplicate-key UPDATE lookup. Mode is selected by pointer presence; the caller does not need the reported value afterward.

[Read this hunk](review.ko.html#hunk-17).

</details>

<details>
<summary>H18 · src/query/query_executor.c</summary>

**Definitions:** [qexec_oid_of_duplicate_key_update](#f12).

**Hunk explanation:** Build the duplicate-key lookup image through suppression while retaining INCLUDE_LOB. This prevents OOS publication for the temporary image; it is not a promise of zero LOB preparation effects.

[Read this hunk](review.ko.html#hunk-18).

</details>

<details>
<summary>H19 · src/storage/heap_file.c</summary>

**Definitions:** No function body changes.

**Hunk explanation:** Thread suppress_oos and would_demote_oos through the private layout planner declaration. Actual placement and hypothetical demotion are distinct outputs.

**Outside definition spans:** 5 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-19).

</details>

<details>
<summary>H20 · src/storage/heap_file.c</summary>

**Definitions:** No function body changes.

**Hunk explanation:** Add destination owner, optional suppression output and second-pass increment state. Wrappers set these deliberately; default behavior must remain the normal first pass.

**Outside definition spans:** 3 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-20).

</details>

<details>
<summary>H21 · src/storage/heap_file.c</summary>

**Definitions:** [heap_attrinfo_get_effective_key](#f13).

**Hunk explanation:** Read an unchanged UPDATE key with an independent reader of the supplied old row; read omitted INSERT defaults on copied metadata; otherwise clone the source. Apply pending increments only to the copy, preserve NULL, then size/write/read with the domain codec. Use aligned scratch for small values and owned allocation for larger ones. Every failure clears a partial output. The guide's block table explains the branches; direct tests compare reference routing and assert source preservation.

**Outside definition spans:** 17 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-21).

</details>

<details>
<summary>H22 · src/storage/heap_file.c</summary>

**Definitions:** No function body changes.

**Hunk explanation:** Document that suppression retains inline values and that would_demote is hypothetical. has_oos continues to describe the actual emitted layout.

**Outside definition spans:** 2 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-22).

</details>

<details>
<summary>H23 · src/storage/heap_file.c</summary>

**Definitions:** [heap_attrinfo_determine_disk_layout](#f14).

**Hunk explanation:** Keep declaration, definition and caller consistent. Passing the mode separately allows layout decisions to avoid selecting any OOS plan entry.

[Read this hunk](review.ko.html#hunk-23).

</details>

<details>
<summary>H24 · src/storage/heap_file.c</summary>

**Definitions:** [heap_attrinfo_determine_disk_layout](#f14).

**Hunk explanation:** Initialize has_oos false and clear a supplied would-demote output before scanning columns. A reused Boolean must not inherit the previous row's verdict.

[Read this hunk](review.ko.html#hunk-24).

</details>

<details>
<summary>H25 · src/storage/heap_file.c</summary>

**Definitions:** [heap_attrinfo_determine_disk_layout](#f14).

**Hunk explanation:** FORCE_OUTLINE runs before the ordinary size gate. Under suppression set would-demote and continue before plan.selected, payload subtraction and has_oos updates. This is the small-forced-value regression's decisive branch.

[Read this hunk](review.ko.html#hunk-25).

</details>

<details>
<summary>H26 · src/storage/heap_file.c</summary>

**Definitions:** [heap_attrinfo_determine_disk_layout](#f14).

**Hunk explanation:** After discovering ordinary eligible candidates, report whether candidates exist and return the fully inline size without sorting/selecting/demoting them. The fully inline temporary image can be larger than a heap slot.

[Read this hunk](review.ko.html#hunk-26).

</details>

<details>
<summary>H27 · src/storage/heap_file.c</summary>

**Definitions:** [heap_attrinfo_insert_to_oos](#f15).

**Hunk explanation:** Extend heap_attrinfo_insert_to_oos with an optional class OID and document per-heap ownership. Retain source attrinfo for payload and LOB preparation.

**Outside definition spans:** 4 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-27).

</details>

<details>
<summary>H28 · src/storage/heap_file.c</summary>

**Definitions:** [heap_attrinfo_insert_to_oos](#f15).

**Hunk explanation:** Pass the override to heap_oos_insert_serialized_values, falling back to attrinfo class for legacy callers. This is where early destination selection becomes a different physical OOS file.

[Read this hunk](review.ko.html#hunk-28).

</details>

<details>
<summary>H29 · src/storage/heap_file.c</summary>

**Definitions:** [heap_attrinfo_transform_to_disk](#f16); [heap_attrinfo_transform_to_disk_oos_class](#f19); [heap_attrinfo_transform_to_disk_probe_oos](#f18); [heap_attrinfo_transform_to_disk_with_oos_owner](#f17).

**Hunk explanation:** Normal wrapper uses NULL owner/NULL verdict/false. Owner-aware first pass uses owner/NULL/false. Probe uses NULL/verdict/false. Retained second pass uses owner/NULL/true. The final true skips increments already applied by an earlier probe; it must not be used for the new main path's first transform.

**Outside definition spans:** 28 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-29).

</details>

<details>
<summary>H30 · src/storage/heap_file.c</summary>

**Definitions:** [heap_attrinfo_transform_to_disk_except_lob](#f20).

**Hunk explanation:** The except_lob wrapper supplies EXCLUDE_LOB with default owner, no suppression and first-pass increment behavior. This signature adaptation retains the existing contract.

[Read this hunk](review.ko.html#hunk-30).

</details>

<details>
<summary>H31 · src/storage/heap_file.c</summary>

**Definitions:** [heap_attrinfo_transform_to_disk_internal](#f21).

**Hunk explanation:** Document pointer-presence suppression, destination override and the retained second-pass flag in the common transformer. The definition matches the updated declaration.

**Outside definition spans:** 3 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-31).

</details>

<details>
<summary>H32 · src/storage/heap_file.c</summary>

**Definitions:** [heap_attrinfo_transform_to_disk_internal](#f21).

**Hunk explanation:** Compute suppress_oos from would_demote_oos != NULL. Add an index variable for the retained second-pass premark loop; it is not the early key routing algorithm.

[Read this hunk](review.ko.html#hunk-32).

</details>

<details>
<summary>H33 · src/storage/heap_file.c</summary>

**Definitions:** [heap_attrinfo_transform_to_disk_internal](#f21).

**Hunk explanation:** When increments_already_applied is true, prefill the same set consulted by the fixed-column writer. Current owner-aware main writes pass false; buffer-retry protection in the normal writer remains independently necessary.

[Read this hunk](review.ko.html#hunk-33).

</details>

<details>
<summary>H34 · src/storage/heap_file.c</summary>

**Definitions:** [heap_attrinfo_transform_to_disk_internal](#f21).

**Hunk explanation:** Pass suppression and verdict to the planner while retaining actual has_oos and inline-size outputs. Later OOS writing is controlled by the actual has_oos result.

[Read this hunk](review.ko.html#hunk-34).

</details>

<details>
<summary>H35 · src/storage/heap_file.c</summary>

**Definitions:** [heap_attrinfo_transform_to_disk_internal](#f21).

**Hunk explanation:** The transform sends oos_class_oid to the OOS insertion boundary only after the existing bigone rejection. This propagates the destination selected by locator without rewriting attrinfo identity.

[Read this hunk](review.ko.html#hunk-35).

</details>

<details>
<summary>H36 · src/storage/heap_file.c</summary>

**Definitions:** [bridge_heap_attrinfo_insert_to_oos](#f22).

**Hunk explanation:** Supply NULL for the new owner parameter in the pre-existing bridge. Its synthetic attrinfo class continues to determine ownership.

[Read this hunk](review.ko.html#hunk-36).

</details>

<details>
<summary>H37 · src/storage/heap_file.h</summary>

**Definitions:** No function body changes.

**Hunk explanation:** Declare the effective-key helper plus owner-first-pass, probe and retained rebuild wrappers. Old transformer declarations remain. This is an internal engine header change, not a client protocol change.

**Outside definition spans:** 12 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-37).

</details>

<details>
<summary>H38 · src/transaction/locator_sr.c</summary>

**Definitions:** No function body changes.

**Hunk explanation:** Extend the private locator_update_force declaration with an optional expected destination. Each caller must explicitly say whether it has an early decision to validate.

**Outside definition spans:** 2 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-38).

</details>

<details>
<summary>H39 · src/transaction/locator_sr.c</summary>

**Definitions:** No function body changes.

**Hunk explanation:** Rename the comment to match the new private internal function. Behavior is provided by the surrounding signature and agreement-check changes.

**Outside definition spans:** 2 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-39).

</details>

<details>
<summary>H40 · src/transaction/locator_sr.c</summary>

**Definitions:** [locator_insert_force](#f24); [locator_insert_force_internal](#f23).

**Hunk explanation:** Add expected_class_oid while keeping the old public API via H42. This avoids forcing unrelated callers to create an early destination.

**Outside definition spans:** 3 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-40).

</details>

<details>
<summary>H41 · src/transaction/locator_sr.c</summary>

**Definitions:** [locator_insert_force_internal](#f23).

**Hunk explanation:** After final record pruning succeeds, compare against the early owner. On mismatch return ER_GENERIC_ERROR through existing error handling before the following subclass/heap insertion path. Do not silently redirect already-prepared OOS chains.

[Read this hunk](review.ko.html#hunk-41).

</details>

<details>
<summary>H42 · src/transaction/locator_sr.c</summary>

**Definitions:** [locator_insert_force](#f24).

**Hunk explanation:** The original public locator_insert_force forwards all existing arguments plus NULL expected owner. Only the main attribute write invokes the private guarded variant directly.

**Outside definition spans:** 4 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-42).

</details>

<details>
<summary>H43 · src/transaction/locator_sr.c</summary>

**Definitions:** No function body changes.

**Hunk explanation:** Document that the optional early class must agree with final routing before the subsequent row heap/index mutation. This is a comparison contract, not a transaction-abort implementation.

**Outside definition spans:** 1 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-43).

</details>

<details>
<summary>H44 · src/transaction/locator_sr.c</summary>

**Definitions:** [locator_update_force](#f25).

**Hunk explanation:** Extend the private definition to receive expected_class_oid. H45 consumes it after final routing; unrelated callers pass NULL.

[Read this hunk](review.ko.html#hunk-44).

</details>

<details>
<summary>H45 · src/transaction/locator_sr.c</summary>

**Definitions:** [locator_update_force](#f25).

**Hunk explanation:** Compare final class with the early OOS owner before source-class reidentification and partition movement. Failure follows existing error cleanup; logged OOS work depends on the caller's rollback path.

[Read this hunk](review.ko.html#hunk-45).

</details>

<details>
<summary>H46 · src/transaction/locator_sr.c</summary>

**Definitions:** [locator_force_for_multi_update](#f26).

**Hunk explanation:** Append NULL expected class to the existing nonpartitioned multi-update caller. It has no early attrinfo routing result to certify.

[Read this hunk](review.ko.html#hunk-46).

</details>

<details>
<summary>H47 · src/transaction/locator_sr.c</summary>

**Definitions:** [xlocator_repl_force](#f27).

**Hunk explanation:** Append NULL to replication's existing record-based UPDATE call. This does not introduce effective-key preparation into the replication path.

[Read this hunk](review.ko.html#hunk-47).

</details>

<details>
<summary>H48 · src/transaction/locator_sr.c</summary>

**Definitions:** [xlocator_force](#f28).

**Hunk explanation:** Append NULL to xlocator_force's existing UPDATE call. Preserve behavior for callers that already supply serialized records.

[Read this hunk](review.ko.html#hunk-48).

</details>

<details>
<summary>H49 · src/transaction/locator_sr.c</summary>

**Definitions:** No function body changes.

**Hunk explanation:** Rename the implementation comment; the public wrapper is reintroduced below. Allocation ownership stays with the existing copy-area API.

**Outside definition spans:** 2 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-49).

</details>

<details>
<summary>H50 · src/transaction/locator_sr.c</summary>

**Definitions:** [locator_allocate_copy_area_by_attr_info](#f30); [locator_allocate_copy_area_by_attr_info_internal](#f29).

**Hunk explanation:** Private builder receives owner, probe verdict and oos_first_pass. This extra private flag distinguishes a real first transform from the retained owner-after-probe rebuild contract.

**Outside definition spans:** 6 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-50).

</details>

<details>
<summary>H51 · src/transaction/locator_sr.c</summary>

**Definitions:** [locator_allocate_copy_area_by_attr_info](#f30); [locator_allocate_copy_area_by_attr_info_internal](#f29).

**Hunk explanation:** Priority is owner-first-pass, probe, retained owner-rebuild, except-LOB, normal. The first branch asserts owner exists and no probe output is present. Existing buffer growth and copy-area release behavior remain below; mode selection does not itself perform rollback.

[Read this hunk](review.ko.html#hunk-51).

</details>

<details>
<summary>H52 · src/transaction/locator_sr.c</summary>

**Definitions:** [locator_allocate_copy_area_by_attr_info](#f30).

**Hunk explanation:** The public builder forwards its expanded arguments with oos_first_pass=false. New main writes deliberately bypass it for the private first-pass owner mode.

**Outside definition spans:** 4 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-52).

</details>

<details>
<summary>H53 · src/transaction/locator_sr.c</summary>

**Definitions:** [locator_attribute_info_force](#f31).

**Hunk explanation:** Initialize write_destination to NULL so nonpartitioned calls naturally have no expected destination. Preserve the existing local source class/HFID copies.

[Read this hunk](review.ko.html#hunk-53).

</details>

<details>
<summary>H54 · src/transaction/locator_sr.c</summary>

**Definitions:** [locator_attribute_info_force](#f31).

**Hunk explanation:** For partitioned writes initialize fallback destination identifiers, select INSERT or UPDATE key routing, and stop on error. Then build the row once with INCLUDE_LOB, selected owner and oos_first_pass=true. Leave source class untouched for final validation and movement. Nonpartitioned writes explicitly request the default modes.

[Read this hunk](review.ko.html#hunk-54).

</details>

<details>
<summary>H55 · src/transaction/locator_sr.c</summary>

**Definitions:** [locator_attribute_info_force](#f31).

**Hunk explanation:** Call the private INSERT variant and pass the selected destination unless NULL. Existing default use_bulk_logging=false is now explicit along with the other unchanged flags.

[Read this hunk](review.ko.html#hunk-55).

</details>

<details>
<summary>H56 · src/transaction/locator_sr.c</summary>

**Definitions:** [locator_attribute_info_force](#f31).

**Hunk explanation:** Pass the same selected destination into final UPDATE. An unchanged key and a moving key both require agreement with the OOS owner chosen before transformation.

[Read this hunk](review.ko.html#hunk-56).

</details>

<details>
<summary>H57 · src/transaction/locator_sr.c</summary>

**Definitions:** [locator_mvcc_reev_cond_assigns](#f32).

**Hunk explanation:** The MVCC reevaluation copy-area call adds NULL owner and NULL probe output. This is signature adaptation, not evidence that all concurrent reevaluation paths have been validated by the new standalone tests.

[Read this hunk](review.ko.html#hunk-57).

</details>

<details>
<summary>H58 · src/transaction/locator_sr.h</summary>

**Definitions:** No function body changes.

**Hunk explanation:** Expose the added owner and suppression output parameters consistently with all callers. The private first-pass flag is deliberately not part of this public engine declaration.

**Outside definition spans:** 3 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-58).

</details>

<details>
<summary>H59 · unit_tests/oos/sql/CMakeLists.txt</summary>

**Definitions:** No function body changes.

**Hunk explanation:** Override only test_oos_sql_show's timeout to 300 seconds. Fault injection and routing errors collect debug stacks; fixture requirements and serial execution are unchanged.

**Outside definition spans:** 3 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-59).

</details>

<details>
<summary>H60 · unit_tests/oos/sql/test_oos_sql_show.cpp</summary>

**Definitions:** [scoped_sa_server](#f33); [~scoped_sa_server](#f34).

**Hunk explanation:** Include routing, locator, OOS, logging, record and primitive APIs plus string support. Declare existing failure hooks. scoped_sa_server increments/decrements db_on_server around direct server calls so SA allocation follows server conventions; it does not start a SERVER_MODE process.

**Outside definition spans:** 17 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-60).

</details>

<details>
<summary>H61 · unit_tests/oos/sql/test_oos_sql_show.cpp</summary>

**Definitions:** [expect_oos_records](#f38); [expect_sql_count](#f37); [get_string_column](#f35); [unqualified_table_name](#f36).

**Hunk explanation:** Add string extraction with DB_VALUE cleanup, schema-prefix removal, count queries and exact OOS file/chunk expectations. The physical helper checks a single row and closes its query result. Distinct logical and physical oracles catch the original bug that successful SELECT missed.

**Outside definition spans:** 4 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-61).

</details>

<details>
<summary>H62 · unit_tests/oos/sql/test_oos_sql_show.cpp</summary>

**Definitions:** [OosSqlShow.EffectiveInsertRouteLegalKeyDefaults](#f60); [OosSqlShow.EffectiveInsertRoutePreservesAssignedChar](#f59); [OosSqlShow.EffectiveInsertRoutePreservesOmittedAssignments](#f58); [OosSqlShow.EffectiveKeyCodecFailureClearsOutputAndPreservesAssignment](#f55); [OosSqlShow.EffectiveRoutingFailurePreservesAssignmentsAndPublication](#f57); [OosSqlShow.EffectiveUpdateRoutePreservesOldKeyAndPendingIncrement](#f52); [OosSqlShow.EffectiveUpdateRouteUsesMissingHistoricalKeyDefault](#f51); [OosSqlShow.PartitionHashNullOwnership](#f42); [OosSqlShow.PartitionInsertCompressedExpressionKey](#f67); [OosSqlShow.PartitionInsertDynamicDefault](#f65); [OosSqlShow.PartitionInsertGeneratedKeysAndDomainConversion](#f64); [OosSqlShow.PartitionInsertLegalKeySqlMatrix](#f61); [OosSqlShow.PartitionInsertOwnsExternalKeyAndMultiplePayloads](#f62); [OosSqlShow.PartitionInsertRetainsBigoneRejectionBeforeOos](#f63); [OosSqlShow.PartitionInsertUsesColumnCollation](#f66); [OosSqlShow.PartitionListExpressionAndFailedBatchOwnership](#f41); [OosSqlShow.PartitionListRejectsNullWithoutDestination](#f44); [OosSqlShow.PartitionLobPreparationAndIndexFailuresPreserveCommittedValues](#f54); [OosSqlShow.PartitionPreparationFailuresRollBackAndAllowNextWrite](#f53); [OosSqlShow.PartitionRangeBoundaryAndNullOwnership](#f40); [OosSqlShow.PartitionRangeExpressionValidationAndMovement](#f43); [OosSqlShow.PartitionUpdateDedicatedIncrementsAndArithmetic](#f50); [OosSqlShow.PartitionUpdateLegalKeysAndNullMovement](#f47); [OosSqlShow.PartitionUpdateLobLifecycle](#f49); [OosSqlShow.PartitionUpdateOldOosKeyAndRepresentation](#f48); [OosSqlShow.PartitionUpdatePreservesDuplicateProbesAndNonKeyIncrement](#f45); [OosSqlShow.PartitionUpdateStringDomains](#f46); [OosSqlShow.PartitionedForceOutlineStoresOosInPrunedHeap](#f39); [failing_codec](#f56).

**Hunk explanation:** This large hunk contains 28 new tests, not one undifferentiated fixture. The test catalog below links each exact function and explains its distinguishing assertions, reference independence and limits. Four earlier SHOW tests remain unchanged.

**Outside definition spans:** 28 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-62).

</details>

<details>
<summary>H63 · unit_tests/oos/test_oos_real_vacuum_server.cpp</summary>

**Definitions:** [OosRealVacuum.DISABLED_RolledBackUpdateKeepsCommittedOosAfterVacuum](#f68).

**Hunk explanation:** Add a DISABLED_ test: committed original and independent witness, replacement update and abort, successful pre-vacuum original read, committed witness delete, observed vacuum progress, then original readback. Allocate the witness before reclaimable versions to avoid aliasing a recycled OOS slot. Historical final readback fails; DISABLED_ keeps it out of normal runs pending CBRD-27237. This is not a partition-specific test or a passing lifecycle result.

**Outside definition spans:** 6 added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).

[Read this hunk](review.ko.html#hunk-63).

</details>

## Method and limits

The background research checked production definitions against source at both commits. An independent syntax extraction compared definitions, collected explicit named calls and mapped changed lines to function spans. GNU-style definition recovery handled preprocessor constructs that the whole-file parser missed. The index was reconciled with the manually reviewed production list. Test macro bodies, named helpers and the two callback lambdas were checked separately.

The call index covers both revision snapshots, including preprocessor-conditional source. It does not resolve dynamic function pointers, all implicit C++ operations, external libraries or build-configuration reachability. Repeated calls to one target are summarized as one target in outgoing lists; incoming links retain individual call sites. These limits do not turn a SQL-submission test into a direct engine caller.

No engine tests or benchmarks were run. New tests are classified by source addition, not execution success. Changes in this report are relative to the fixed commits above, not later PR updates.

Reproducible evidence: [function definitions](evidence/functions-ast.json), [source call index](evidence/callers-index.json), [all hunk mappings](evidence/function-hunk-coverage.json), [frozen diff](evidence/pr.diff). Generator scripts are retained under authoring/.
