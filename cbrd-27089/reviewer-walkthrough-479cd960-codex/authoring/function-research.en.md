# PR #7600: production function research

Compared base `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` with HEAD `479cd960ec04196c92bf9789b1fc340af9046c2c`. Primary evidence is the source at those two commits and their Git diff. This document covers all 32 changed/new definitions in the four changed implementation files: 31 runtime definitions and one unit-test bridge. It excludes SQL test bodies, other test helpers and header declarations, which belong in the complete inventory. No production function definition is deleted.

Status is based on function identity. A public function reduced to a wrapper is **modified**. A new `_internal` function holding its old body is **newly created (extracted implementation)**. Deleted lines do not by themselves mean a deleted function.

The direct-call lists below select calls relevant to this change; they are not the exhaustive repository call graph. Each section’s HEAD source link owns its purpose, change and callee evidence. The base link shows the previous implementation. The reason is an explanation of the source comments and control flow, not an independently measured result. No engine tests were run for this research.

Vocabulary: a **heap** stores rows; an **OOS file** stores out-of-row values for one heap; the **source class** describes the assignments/old row; the **destination class** identifies the child selected for the new row. **Caller → callee** means a direct call. Callback dispatch is named separately.

## `partition_find_partition_for_expr` — newly created

**Purpose:** Evaluate the partition expression and choose exactly one child.

**Change:** Extract the expression evaluation and matching work from partition_find_partition_for_record. Return a borrowed partition descriptor only on success.

**Reason:** The new key-only path and the existing full-record path must use the same matching rules.

**Relevant direct callers:** partition_find_partition_for_attrinfo; partition_find_partition_for_record.

**Relevant direct callees:** fetch_peek_dbval; partition_prune_db_val; pruningset_popcount; pruningset_iterator_init; pruningset_iterator_next.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3480); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c).

## `partition_start_key_attrinfo` — newly created

**Purpose:** Create and bind the partition context’s one-key storage slot.

**Change:** Extract lazy attribute-cache initialization from the old record routing function. Keep the slot in the pruning context.

**Reason:** Expression bindings must point to stable storage, not a temporary stack value. Both routing paths need that storage.

**Relevant direct callers:** partition_find_partition_for_attrinfo; partition_find_partition_for_record.

**Relevant direct callees:** heap_attrinfo_start; partition_set_cache_info_for_expr.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3549); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c).

## `partition_find_partition_for_attrinfo` — newly created

**Purpose:** Choose a child from the pending write’s partition-key value.

**Change:** Clear a previous probe key, obtain an owned effective key in the stable context slot, evaluate it, copy the destination only on success, then clear the key.

**Reason:** Choose the destination before writing OOS values, without preparing every column or consuming the original assignments.

**Relevant direct callers:** partition_prune_insert_internal; partition_prune_update_internal.

**Relevant direct callees:** partition_start_key_attrinfo; heap_attrinfo_clear_dbvalues; heap_attrinfo_get_effective_key; partition_find_partition_for_expr.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3570); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c).

## `partition_find_partition_for_record` — modified

**Purpose:** Choose a child from an already serialized row.

**Change:** Delegate slot initialization and expression matching to the new helpers. Retain temporary root representation decoding, value cleanup, destination outputs, and destination representation patching.

**Reason:** Keep final row routing as a separate check while sharing its matching rules with early key-only routing. This function was not deleted.

**Relevant direct callers:** partition_prune_insert_internal; partition_prune_update_internal.

**Relevant direct callees:** partition_start_key_attrinfo; heap_attrinfo_read_dbvalues; partition_find_partition_for_expr; or_set_rep_id; heap_attrinfo_clear_dbvalues.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3618); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3467).

## `partition_prune_insert_internal` — newly created

**Purpose:** Manage the common INSERT routing context and explicit-child checks.

**Change:** Move the previous partition_prune_insert body into an internal helper. Dispatch to attribute routing when attr_info is present, otherwise record routing.

**Reason:** Both entry points need the same context ownership and validation rules. This is an extraction, not a replacement routing policy.

**Relevant direct callers:** partition_prune_insert; partition_prune_insert_by_attrinfo.

**Relevant direct callees:** partition_find_partition_for_attrinfo; partition_find_partition_for_record; partition_init_pruning_context; partition_load_pruning_context; partition_clear_pruning_context.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3702); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c).

## `partition_prune_insert` — modified

**Purpose:** Route an INSERT that already has a row image.

**Change:** Replace its implementation with a wrapper that supplies NULL attr_info to partition_prune_insert_internal.

**Reason:** Preserve existing callers and record-routing behavior while adding an early route.

**Relevant direct callers:** locator_insert_force_internal.

**Relevant direct callees:** partition_prune_insert_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3800); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3605).

## `partition_prune_insert_by_attrinfo` — newly created

**Purpose:** Expose early INSERT routing from assigned values.

**Change:** Assert that assignments are present and call the shared INSERT helper with no serialized row.

**Reason:** The caller can determine the child heap before the full row transformer creates OOS values.

**Relevant direct callers:** locator_attribute_info_force.

**Relevant direct callees:** partition_prune_insert_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3816); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c).

## `partition_prune_update_internal` — newly created

**Purpose:** Manage common UPDATE routing, including source-child/root context and explicit-child checks.

**Change:** Extract the old partition_prune_update body and add an attribute-based branch. In that branch recdes is the supplied old row; in the record branch it is the new row.

**Reason:** An UPDATE may leave the key unchanged or move the row. Both early and final routing must preserve the established validation contract.

**Relevant direct callers:** partition_prune_update; partition_prune_update_by_attrinfo.

**Relevant direct callees:** partition_find_partition_for_attrinfo; partition_find_partition_for_record; partition_init_pruning_context; partition_load_pruning_context; partition_clear_pruning_context.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3847); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c).

## `partition_prune_update` — modified

**Purpose:** Route the completed UPDATE row and patch its representation.

**Change:** Retain the public name as a wrapper into the internal helper with NULL attr_info.

**Reason:** The final serialized record still determines and verifies the destination. It is not removed by early routing.

**Relevant direct callers:** locator_update_force.

**Relevant direct callees:** partition_prune_update_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3974); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c#L3712).

## `partition_prune_update_by_attrinfo` — newly created

**Purpose:** Expose early UPDATE routing from assignments and the supplied old row.

**Change:** Pass both the assignments and old_recdes to the shared UPDATE helper.

**Reason:** If the statement did not assign the partition key, routing must read its old value without rewriting the source row first.

**Relevant direct callers:** locator_attribute_info_force.

**Relevant direct callees:** partition_prune_update_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/partition.c#L3985); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/partition.c).

## `qexec_remove_duplicates_for_replace` — modified

**Purpose:** Find and remove rows that conflict with a REPLACE candidate.

**Change:** Pass a non-NULL probe result pointer and a NULL OOS owner to copy-area construction; retain LOB_FLAG_EXCLUDE_LOB.

**Reason:** The temporary candidate is used for index lookup. Creating OOS chains for an image that will never be inserted can leave unowned data.

**Relevant direct callers:** qexec_execute_insert [unchanged context].

**Relevant direct callees:** locator_allocate_copy_area_by_attr_info; partition_prune_unique_btid [unchanged context].

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L11921); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/query_executor.c#L11921).

## `qexec_oid_of_duplicate_key_update` — modified

**Purpose:** Find the existing row that conflicts with an INSERT ON DUPLICATE KEY UPDATE candidate.

**Change:** Use the same OOS-suppressed probe request; retain LOB_FLAG_INCLUDE_LOB.

**Reason:** A unique-index probe must not publish OOS chains for its temporary row image. This does not claim that every LOB side effect is suppressed.

**Relevant direct callers:** qexec_execute_duplicate_key_update [unchanged context].

**Relevant direct callees:** locator_allocate_copy_area_by_attr_info; partition_prune_unique_btid [unchanged context].

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/query_executor.c#L12158); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/query/query_executor.c#L12153).

## `heap_attrinfo_get_effective_key` — newly created

**Purpose:** Obtain the partition key as it will be represented in storage.

**Change:** Use an independent reader for an unchanged UPDATE key, the existing default reader for an omitted INSERT value, or a clone for an assigned value. Apply a pending increment to the clone. Round-trip the scalar value through its storage codec, then clear temporary memory.

**Reason:** Early routing must agree with the completed row, including defaults, old representations, CHAR padding and increments. The original assignments must remain available for normal preparation.

**Relevant direct callers:** partition_find_partition_for_attrinfo.

**Relevant direct callees:** heap_attrvalue_locate; heap_attrinfo_start; heap_attrinfo_read_dbvalues_without_oid; heap_attrinfo_end; heap_attrvalue_read; pr_clone_value; qdata_increment_dbval; pr_clear_value. Indirect codec callbacks: pr_type->get_disk_size_of_value, pr_type->data_writeval, pr_type->data_readval.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12117); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c).

## `heap_attrinfo_determine_disk_layout` — modified

**Purpose:** Choose inline versus OOS storage and compute record size.

**Change:** Accept suppress_oos and a would-demote output. In probe mode report whether a column would move to OOS, but keep the complete inline payload and leave the OOS plan unselected.

**Reason:** Temporary key-probe images need the values but must not cause OOS insertion. The image may exceed a normal heap record’s capacity.

**Relevant direct callers:** heap_attrinfo_transform_to_disk_internal.

**Relevant direct callees:** heap_attrinfo_get_record_payload_size; heap_attrinfo_get_record_header_size; heap_oos_get_demote_priority [unchanged context].

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12440); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L12310).

## `heap_attrinfo_insert_to_oos` — modified

**Purpose:** Prepare serialized OOS requests and insert their value chains.

**Change:** Accept an optional destination class and pass it to heap_oos_insert_serialized_values; fall back to attr_info->class_oid when absent. Keep payload preparation based on the original attr_info.

**Reason:** The OOS file must belong to the child heap that will store the row. The source class must still identify the old representation and LOB preparation context.

**Relevant direct callers:** heap_attrinfo_transform_to_disk_internal; bridge_heap_attrinfo_insert_to_oos [test-only].

**Relevant direct callees:** heap_oos_begin_insert_publication; heap_attrinfo_prepare_oos_insert_requests; heap_oos_insert_serialized_values; heap_attrinfo_free_oos_payloads [all unchanged context].

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12847); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L12686).

## `heap_attrinfo_transform_to_disk` — modified

**Purpose:** Build a normal row image with LOB handling.

**Change:** Pass NULL owner, NULL probe output and false for already-applied increments to the enlarged internal interface.

**Reason:** Keep normal callers on their existing first-pass behavior.

**Relevant direct callers:** locator_allocate_copy_area_by_attr_info_internal (normal branch); other existing normal transformation callers.

**Relevant direct callees:** heap_attrinfo_transform_to_disk_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12916); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L12755).

## `heap_attrinfo_transform_to_disk_with_oos_owner` — newly created

**Purpose:** Build the row normally while directing OOS values to a chosen heap.

**Change:** Pass a required owner, no probe output and false for already-applied increments.

**Reason:** The main write path has already chosen the child from one key. It can now prepare the full row once with the correct OOS owner.

**Relevant direct callers:** locator_allocate_copy_area_by_attr_info_internal (oos_first_pass branch).

**Relevant direct callees:** heap_attrinfo_transform_to_disk_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12930); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c).

## `heap_attrinfo_transform_to_disk_probe_oos` — newly created

**Purpose:** Build an inline-only image for a temporary probe.

**Change:** Pass the caller’s would-demote pointer and no owner to the common transformer.

**Reason:** Avoid OOS publication during duplicate-key lookup. Normal assignment preparation can still occur, including increments and permitted LOB work.

**Relevant direct callers:** locator_allocate_copy_area_by_attr_info_internal (probe branch).

**Relevant direct callees:** heap_attrinfo_transform_to_disk_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12951); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c).

## `heap_attrinfo_transform_to_disk_oos_class` — newly created

**Purpose:** Complete an owner-directed transformation after an earlier full probe.

**Change:** Pass the owner and true for already-applied increments.

**Reason:** Retain a two-pass interface without applying an increment twice. The current main partitioned write uses with_oos_owner instead; do not teach this as its active second stage.

**Relevant direct callers:** locator_allocate_copy_area_by_attr_info_internal (owner supplied without first-pass or probe flag).

**Relevant direct callees:** heap_attrinfo_transform_to_disk_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12968); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c).

## `heap_attrinfo_transform_to_disk_except_lob` — modified

**Purpose:** Build a normal row image without creating LOB objects.

**Change:** Supply NULL owner, NULL probe output and false for already-applied increments.

**Reason:** Adapt to the internal signature while preserving this entry point’s existing mode.

**Relevant direct callers:** locator_allocate_copy_area_by_attr_info_internal (exclude-LOB branch).

**Relevant direct callees:** heap_attrinfo_transform_to_disk_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12990); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L12775).

## `heap_attrinfo_transform_to_disk_internal` — modified

**Purpose:** Run shared row preparation, layout selection, OOS insertion and serialization.

**Change:** Add owner, probe and already-applied-increment parameters. Derive suppression from pointer presence, premark increments only for the retained second-pass mode, pass suppression into layout and owner into OOS insertion.

**Reason:** Support real writes and temporary probes through the same serializer while controlling OOS ownership and avoiding double increments.

**Relevant direct callers:** heap_attrinfo_transform_to_disk; heap_attrinfo_transform_to_disk_with_oos_owner; heap_attrinfo_transform_to_disk_probe_oos; heap_attrinfo_transform_to_disk_oos_class; heap_attrinfo_transform_to_disk_except_lob.

**Relevant direct callees:** heap_attrinfo_set_uninitialized; heap_attrinfo_determine_disk_layout; heap_attrinfo_insert_to_oos; heap_attrinfo_transform_header_to_disk; heap_attrinfo_transform_columns_to_disk.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L13458); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L13239).

## `bridge_heap_attrinfo_insert_to_oos` — modified (test-only)

**Purpose:** Expose the static OOS insertion helper to unit tests.

**Change:** Pass NULL for the new owner parameter.

**Reason:** Keep the bridge using its supplied class through attr_info, with no owner override. It is compiled only under CUBRID_UNIT_TEST_ENABLED.

**Relevant direct callers:** unit-test code; not a production entry point.

**Relevant direct callees:** heap_attrinfo_insert_to_oos.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L28661); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/storage/heap_file.c#L28425).

## `locator_insert_force_internal` — newly created

**Purpose:** Insert the finished row and maintain its indexes.

**Change:** Extract the previous locator_insert_force body. Add an optional expected child and compare it with final record routing before proceeding with the partitioned insert.

**Reason:** OOS chains can already belong to the early child. A different final child must produce an error instead of placing the row elsewhere. Transaction error handling is responsible for rollback; this guard is not a local delete-all operation.

**Relevant direct callers:** locator_insert_force; locator_attribute_info_force.

**Relevant direct callees:** partition_prune_insert; heap_insert_logical [unchanged context].

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L4953); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c).

## `locator_insert_force` — modified

**Purpose:** Keep the existing record-based force-insert entry point.

**Change:** Wrap locator_insert_force_internal with NULL expected_class_oid.

**Reason:** Existing callers do not have an early chosen OOS destination and keep their established behavior. The original function name still exists.

**Relevant direct callers:** locator_move_record [unchanged context]; existing force-insert callers.

**Relevant direct callees:** locator_insert_force_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5299); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L4952).

## `locator_update_force` — modified

**Purpose:** Update or move the finished row and maintain indexes.

**Change:** Accept an optional expected child. After final partition routing, reject a different child before the following source-class refresh and instance move/index operations.

**Reason:** Do not move a row to a heap different from the one chosen for its OOS chains.

**Relevant direct callers:** locator_attribute_info_force; locator_force_for_multi_update; xlocator_repl_force; xlocator_force.

**Relevant direct callees:** partition_prune_update; locator_move_record [unchanged context].

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5490); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L5465).

## `locator_force_for_multi_update` — modified

**Purpose:** Apply a force copy-area batch for multi-row updates.

**Change:** Pass NULL for the new expected-class argument.

**Reason:** This path did not make an early OOS-owner decision; keep its existing update contract.

**Relevant direct callers:** xlocator_force.

**Relevant direct callees:** locator_update_force.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L6664); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L6631).

## `xlocator_repl_force` — modified

**Purpose:** Apply replicated insert, update and delete operations.

**Change:** Pass NULL for the new expected-class argument in the UPDATE call.

**Reason:** Replication’s existing record-based path has no early destination to verify.

**Relevant direct callers:** external server request / standalone entry callers; see complete call inventory.

**Relevant direct callees:** locator_update_force.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7051); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7018).

## `xlocator_force` — modified

**Purpose:** Apply a copy-area batch of force operations.

**Change:** Pass NULL for expected_class_oid in its UPDATE call.

**Reason:** Preserve the existing path when no earlier attribute-based routing occurred.

**Relevant direct callers:** external server request / standalone entry callers; see complete call inventory.

**Relevant direct callees:** locator_update_force; locator_force_for_multi_update.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7285); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7251).

## `locator_allocate_copy_area_by_attr_info_internal` — newly created

**Purpose:** Allocate a buffer and transform assignments into a row image.

**Change:** Extract the old public body and add mode dispatch: selected-owner first pass, inline-only probe, retained owner-directed second pass, exclude-LOB normal pass, or normal pass.

**Reason:** Give the real write path and duplicate-key probes explicit serialization choices while preserving buffer allocation and error handling.

**Relevant direct callers:** locator_allocate_copy_area_by_attr_info; locator_attribute_info_force.

**Relevant direct callees:** heap_attrinfo_transform_to_disk_with_oos_owner; heap_attrinfo_transform_to_disk_probe_oos; heap_attrinfo_transform_to_disk_oos_class; heap_attrinfo_transform_to_disk_except_lob; heap_attrinfo_transform_to_disk.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7522); [Base file: name absent](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c).

## `locator_allocate_copy_area_by_attr_info` — modified

**Purpose:** Expose copy-area construction to existing and probe callers.

**Change:** Become a wrapper with owner and probe arguments, passing false for the private first-pass selector. The header supplies defaults for compatibility.

**Reason:** Allow duplicate-key probes to suppress OOS and retain the earlier owner/rebuild interface; keep the main first-pass selector private.

**Relevant direct callers:** qexec_remove_duplicates_for_replace; qexec_oid_of_duplicate_key_update; locator_attribute_info_force; locator_mvcc_reev_cond_assigns.

**Relevant direct callees:** locator_allocate_copy_area_by_attr_info_internal.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7611); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7482).

## `locator_attribute_info_force` — modified

**Purpose:** Turn pending assignments into an inserted or updated row.

**Change:** For partitioned writes, choose write_destination from the key first. Build the full row with that OOS owner, then pass the expected destination to final force. Keep the original source class. Nonpartitioned writes pass NULL mode arguments.

**Reason:** This changes the critical order: choose the child, create OOS values for its heap, then verify and store the row. It avoids a full-row pre-routing probe.

**Relevant direct callers:** query execution write callers; see complete call inventory.

**Relevant direct callees:** partition_prune_insert_by_attrinfo; partition_prune_update_by_attrinfo; locator_allocate_copy_area_by_attr_info_internal; locator_allocate_copy_area_by_attr_info; locator_insert_force_internal; locator_update_force.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7655); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L7583).

## `locator_mvcc_reev_cond_assigns` — modified

**Purpose:** Reevaluate conditions and assignments against a current row version.

**Change:** Pass NULL owner and NULL probe output to copy-area construction.

**Reason:** Keep the existing normal transformation behavior after the interface gains two parameters.

**Relevant direct callers:** locator_mvcc_reev_cond_and_assignment [unchanged context].

**Relevant direct callees:** locator_allocate_copy_area_by_attr_info.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L13802); [Base implementation](https://github.com/CUBRID/cubrid/blob/f4299ac0cd777a2a964c1f197ae5ebf9841a4936/src/transaction/locator_sr.c#L13696).

## `heap_oos_insert_serialized_values` — unchanged context

**Purpose:** Resolve the supplied class to its heap, find or create that heap’s OOS file, and insert the serialized values there.

**Change:** Its definition is unchanged. The changed caller now supplies the selected child class rather than always using the source class.

**Reason for inclusion:** This is where the owner argument becomes an actual OOS file choice. The chain is direct: `heap_attrinfo_insert_to_oos → heap_oos_insert_serialized_values → oos_insert_many`.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_oos.cpp#L631). Its other relevant direct callees are `heap_get_class_info` and `heap_oos_find_vfid`.

## `locator_move_record` — unchanged context

**Purpose:** Move a row from its current heap to another heap.

**Change:** Its definition is unchanged. The modified `locator_update_force` can reach this existing operation only after the new destination check succeeds.

**Reason for inclusion:** Early OOS-owner selection does not replace row movement. Actual code inserts the destination row first and then deletes the source row; do not infer the opposite order from a summary comment.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L5389). Relevant direct calls are `locator_insert_force` followed by `locator_delete_force_for_moving` on the successful path.

## `oos_insert_many` — unchanged context

**Purpose:** Insert multiple serialized value requests into the supplied OOS file and publish their resulting object addresses.

**Change:** Its definition is unchanged. It receives the file selected by `heap_oos_insert_serialized_values`.

**Reason for inclusion:** The PR changes how the caller chooses the file. It does not add a new low-level batch insertion algorithm.

**Evidence:** [HEAD implementation](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/oos_file.cpp#L2193). A relevant direct caller is `heap_oos_insert_serialized_values`.

## `vacuum_oos_find_vfid_for_heap_record` — unchanged context

**Purpose:** Find the OOS file associated with the heap whose row vacuum is processing.

**Change:** Its definition is unchanged. This PR repairs the write path that could put OOS data in a different heap’s file.

**Reason for inclusion:** A successful value read does not prove correct ownership. This cleanup path uses the row’s heap to find an OOS file. At this HEAD, a row marked as containing OOS with no OOS file found for its heap reaches an explicit `abort()`. Some surrounding comments describe skipping cleanup, but the executable `abort()` occurs first.

**Evidence:** [HEAD implementation and failure branch](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/vacuum_oos.cpp#L401). Relevant direct callee: `heap_oos_find_vfid`; error branch: `abort`. Calls from the vacuum implementation are at [line 2106](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/vacuum.c#L2106) and [line 2222](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/query/vacuum.c#L2222).
