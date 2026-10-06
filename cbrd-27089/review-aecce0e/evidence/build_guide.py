"""Render individually researched explanations and enforce symbol coverage."""
import json
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
DATA = json.loads((HERE / 'symbols.json').read_text())
HEAD = DATA['head']

# Each row contains: symbol | what it is | why it exists | why this PR changes/adds it.
PRODUCTION = r'''
heap_pending_record | A move-only owner of one compact record_descriptor and the separately allocated serialized OOS values referenced by that record. | The producer's DB_VALUEs and attribute cache can be cleared before routing or a loader flush; the row and all its borrowed memory references need one lifetime. | Adds a small ownership module around the existing serializer instead of publishing chains during serialization. Only selected OOS payloads need separate retention; inline values already live in the compact record.
heap_pending_record::heap_pending_record(default) | The default constructor creates a STANDARD_BLOCK_ALLOCATOR record descriptor and explicitly sets an empty external buffer. | Preparation requires an initially empty record, and the pending owner must own any buffer the serializer subsequently allocates. | Establishes the empty-data precondition used by heap_attrinfo_prepare_record. Setting the empty external buffer makes get_recdes legal before serialization; a default record_descriptor otherwise has INVALID data-source state.
heap_pending_record::heap_pending_record(move) | A noexcept move constructor transfers the record allocation and swaps the payload vector, then zeros the source byte count. | Loader vector growth and explicit owner handoff must preserve the addresses encoded into pending stubs. | Enables queueing a prepared row without copying payloads or freeing memory still referenced by the moved record.
heap_pending_record::~heap_pending_record | The destructor frees each retained payload allocation; record_descriptor separately releases its record buffer. | One abandoned candidate or failed preparation must release all owned memory exactly once. | Replaces manual copy-area cleanup for pending rows. It does not delete persisted OOS chains or roll back transactions; those remain the caller's responsibility.
heap_pending_record::heap_pending_record(copy deleted) | An explicitly deleted copy constructor. | Copying this owner's raw buffer references would create two owners of the same allocations. | Makes accidental copies fail at compile time; loader and other handoffs must use moves.
heap_pending_record::operator= | An explicitly deleted copy assignment operator. | Assignment must not duplicate ownership or invalidate pointers borrowed from an existing row. | Completes the non-copyable contract. The class provides move construction, not an unrestricted assignment API.
heap_pending_record::record | A mutable accessor returning the owned record_descriptor. | Preparation needs a serializer destination, and bulk finalization must update the owner's descriptor type. | Provides a narrow bridge to existing buffer and serializer operations without exposing the payload vector.
heap_pending_record::get_recdes | A const accessor returning a borrowed RECDES view of the owned record. | Partition, index and locator APIs already consume RECDES; changing those interfaces would spread the redesign. | Lets existing consumers read the compact pending row while its owner remains alive. A copied RECDES is not an ownership transfer.
heap_pending_record::retained_bytes | Computes record buffer capacity, retained payload lengths and payload-vector capacity overhead. | A tiny compact record can reference many megabytes of retained values, so compact length alone understates queue memory. | Supplies the loader's 8 MiB flush accounting. This is retained allocation accounting, not a process RSS measurement or a hard cap on a single row.
heap_pending_record::retain | Transfers an oos_buffer allocation into the owner's vector and increments the payload byte count only after insertion succeeds. | Newly serialized selected values must survive destruction of their DB_VALUE sources. | Adds explicit ownership transfer with bad_alloc translated to ER_OUT_OF_VIRTUAL_MEMORY. On failure the caller still owns and frees the rejected payload.
heap_oos_value_ref | A decoded, non-owning tagged reference with memory and disk alternatives and a common length/read_into interface. | Partition-key evaluation, ordinary attribute reads and composite-index reads need logical values before disk publication as well as after it. | Extends the existing per-attribute Resolve boundary to server-created pending rows while keeping fetched and received rows disk-only.
heap_oos_value_ref::kind | The private enum distinguishing memory from disk references. | The same 24-byte stub fields have different meanings before and after finalization. | Makes the decoder choose an explicit alternative so a pending address is never passed to oos_read as an OOS chain.
heap_oos_value_ref::value | A private union containing either a borrowed const char pointer or an oos_chain_ref. | A decoded reference carries one alternative at a time and owns neither allocation nor page. | Stores pending memory references alongside existing chain identity without changing the durable stub layout.
heap_oos_value_ref::value::value | The union constructor value-initializes its disk member. | A default-constructed wrapper needs deterministic storage before decode succeeds. | Gives the new union a valid initial alternative. Callers must still check decode's result before reading.
heap_oos_value_ref::heap_oos_value_ref | Initializes disk kind, zero length and the union. | Attribute readers construct a destination wrapper before decoding a stub. | Provides an inert starting state for the new common reference API.
heap_oos_value_ref::length | Returns the validated serialized byte length stored by decode. | Readers allocate exactly the destination capacity required by either alternative. | Lets memory and disk consumers share size logic and allows index-key sizing without reading a disk chain.
heap_oos_value_ref::encode_memory | Writes a null head OOS OID, payload length and packed process address into a temporary 24-byte stub. | The ordinary variable-offset table and attribute readers must locate a selected value before an OOS OID exists. | Introduces a local-only encoding identified by REC_OOS_PENDING. The uintptr_t static assertion checks that an address fits the packed field; this encoding must never be stored or transmitted.
heap_oos_value_ref::decode | Bounds-checks the stub, validates length, then decodes either a permitted pending pointer or an identity-checked disk reference. | Reading a corrupt stub or treating remote bytes as an address can invalidate the entire record-read path. | Accepts null head OIDs only when the descriptor is locally marked REC_OOS_PENDING and its address is nonzero; existing disk validation still uses heap_oos_parse_inline_ref.
heap_oos_value_ref::read_into | Copies the memory alternative with memcpy or invokes oos_read for the disk alternative after checking destination length and address. | Callers need caller-owned bytes regardless of where the value currently resides. | Keeps pending payload borrowing inside the reference wrapper; logical consumers receive their own buffers rather than a pointer whose owner may disappear.
heap_oos_finalize_record | Publishes all selected memory payloads into the destination class's OOS file and overwrites their stubs in the existing record buffer. | Only the selected destination heap may own the chains referenced by its row; indexes and heap storage need real disk stubs. | Moves publication after routing. All request/result/stub arrays are prepared before insertion, stubs change only after batch success, and the descriptor becomes REC_HOME. On failure the caller must roll back; the call is not a retryable insertion contract.
heap_oos_read_grouped_payloads | Collects selected attributes' raw payload buffers for grouped attribute Resolve. | Reading several disk-backed values together reuses the existing batched storage read path. | Copies pending memory values directly and queues only disk references for oos_read_many; a memory-only group does not perform a disk batch read.
heap_oos_column_plan | The serializer's per-attribute demotion plan containing selection, length and eventual chain identity. | Layout planning separates choosing which values move out of row from writing their representations. | Adds memory so a selected value can be serialized to retained bytes before publication. A selected plan now requires either memory or a real head OOS OID.
heap_attrinfo_prepare_record | Builds the ordinary compact row with the existing serializer while retaining selected OOS values in a heap_pending_record. | SQL writes and duplicate probes need a routable row before any destination-specific OOS insertion. | Adds the pending preparation entry point, resets publication state, catches allocation failures, preserves the LOB-copy choice and marks successful rows REC_OOS_PENDING, including rows with no selected OOS value.
heap_prepare_oos_record | Adapts an existing serialized row into a pending owner through attribute reads and the current class representation. | Workspace copy-area rows and redistribution start with serialized bytes rather than the SQL producer's attribute cache. | Rebuilds without repeating LOB copies or assignment effects, preserves insert/delete IDs and previous-version LSA, and recomputes representation ID and HAS_OOS for the new compact row.
heap_attrinfo_transform_to_disk_internal | The shared serializer that fills defaults/unassigned values, plans layout, builds headers and writes columns with grow-and-retry buffer handling. | One serializer must preserve established type, LOB, MVCC and variable-offset semantics for all producers. | Adds an optional pending owner: selected values are retained in memory when supplied, while legacy callers still publish immediately. Existing OOS-plus-bigone rejection precedes both paths; growth retries reuse already serialized selected values.
heap_attrinfo_transform_variable_to_disk | Writes one variable attribute and updates its variable-offset-table entry. | Compact records require the same offset layout for inline values and OOS stubs. | Adds the memory-stub branch after the existing bounds check, advances by the same OR_OOS_INLINE_SIZE and leaves the existing disk-stub writer available.
heap_attrinfo_transform_columns_to_disk | Walks all attributes and delegates fixed and variable byte serialization. | Every column must follow the representation's ordering and offset-size contract. | Broadens the selected-plan assertion to accept retained memory before publication; all column consumers still use the established writer.
heap_attrvalue_read_oos_inline | Resolves one OOS-marked attribute into a scratch or owned raw-value buffer. | Type deserialization needs logical value bytes rather than a packed inline stub. | Uses heap_oos_value_ref decode/read_into so partition and index callers can read pending memory values through the existing attribute API, preserving allocation and error cleanup.
heap_midxkey_get_oos_extra_size | Computes the serialized value capacity required when an OOS-marked attribute participates in a multi-column index key. | A composite key must reserve space for the value rather than the short stub. | Replaces its disk-only null-OID check with the common decoder, making pending memory keys eligible while rejecting malformed references through the same validation boundary.
heap_insert_logical | The storage entry point for logical row insertion, including MVCC, logging and address reservations. | Locator ultimately needs one engine path that stores a valid durable record. | Rejects REC_OOS_PENDING before storage and adds a test-only one-shot heap-insert failure after an OOS-bearing row has been finalized. An address reservation is excluded from that injection.
heap_update_logical | The corresponding logical row-update entry point. | Updating heap bytes must preserve MVCC and logging contracts. | Rejects pending descriptors before storage so a missed finalization cannot persist a process address.
heap_oos_test_fail_preparation_once | A test-only function arming an atomic one-shot preparation failure. | Deterministic allocation-boundary tests must fail the next preparation without depending on real memory exhaustion. | Adds a failure seam to check zero partial publication, owner cleanup and the usability of the next operation.
heap_oos_test_fail_heap_insert_once | A test-only function arming a failure at logical heap insertion of an OOS-bearing record. | A successful chain publication followed by a failed row write is a different rollback boundary from failed preparation. | Lets new tests prove that the surrounding transaction rolls back chains when the later row insertion fails.
record_descriptor::pack | Serializes a descriptor type and record bytes into a transport buffer. | Ordinary descriptors are sent through existing packing interfaces. | Returns with ER_GENERIC_ERROR before writing any bytes if the descriptor is REC_OOS_PENDING, preventing both the temporary type and process addresses from leaving the server.
record_descriptor::unpack | Reconstructs a descriptor and copied buffer from transport data. | Received records must remain ordinary serialized input, even when the sender supplies an unexpected type. | Maps an incoming pending type to REC_UNKNOWN; receipt alone cannot authorize the memory branch of heap_oos_value_ref::decode. It does not validate every other possible incoming type.
qexec_remove_duplicates_for_replace | Finds rows conflicting with a REPLACE candidate across unique indexes so they can be removed. | REPLACE must identify its conflicts before performing the accepted row write. | Replaces an immediately serialized copy area with a local pending owner using copy_lobs=false. Candidate keys remain readable, but conflict probing alone creates no candidate OOS chains; RAII handles memory cleanup.
qexec_oid_of_duplicate_key_update | Finds the conflicting row for INSERT ON DUPLICATE KEY UPDATE, including unique/composite index keys. | The executor must choose between inserting the candidate and updating an existing row. | Uses pending preparation with copy_lobs=true instead of a copy area; existing LOB semantics remain distinct from REPLACE while abandoned candidate OOS values stay in memory.
locator_prepare_copyarea_record | A local adapter replacing a received RECDES view with an owner-backed pending view when adaptation succeeds. | Raw workspace/client writes arrive through copy areas and do not pass the SQL attribute-producer path. | Converts only after routing; skips catalog-disabled bootstrap, root/system classes and empty/address-only input. It avoids repeating workspace LOB copies and preserves the incoming header via heap_prepare_oos_record.
locator_insert_force | Routes, locks and inserts one row and its indexes into the chosen heap. | This is the shared write boundary for SQL, client copy areas, loader and movement. | Adds from_copyarea adaptation after partition selection, finalizes against real_class_oid before heap/index writes, and lets loader workers use the session's already held destination BU locks.
locator_update_force | Applies an update, handles MVCC/index/foreign-key work and selects partition movement when needed. | Existing rows require old-image handling and possibly a new destination heap. | Carries from_copyarea to movement; for nonmoving user rows, adapts received input and finalizes before index updates. Pending SQL rows use the same finalizer without a second adaptation.
locator_move_record | Inserts the post-image into a new heap and removes the old row as one movement operation. | A partition-key update cannot keep the row in its former heap. | Propagates from_copyarea through both destination-insert paths so a workspace move gets destination preparation, while an already pending SQL row keeps its original owner until consumption finishes.
locator_attribute_info_force | The server-side attribute-cache dispatcher for INSERT/UPDATE/DELETE and related operations. | SQL execution supplies changed DB_VALUEs and an old row rather than a client copy area. | Owns a heap_pending_record for insert/update preparation, passes the borrowed row to existing routing/force APIs and clears publication state on errors; deleted operations retain their established path.
locator_force_for_multi_update | Applies a batch of serialized updates from an LC_COPYAREA. | The multi-update protocol shares update logic while supplying record bytes directly. | Marks those rows from_copyarea=true and resets OOS publication state on failure, ensuring this producer gets adaptation instead of bypassing deferred ownership.
locator_multi_insert_force | The loader's optimized nonpartitioned, non-HA multirow insertion path. | Bulk page logging reduces overhead when row-by-row routing or replication is unnecessary. | Changes its input to movable pending owners, releases any cached heap-page latch, finalizes every row before bulk data-page latching, and updates each owner's descriptor type. Partition/HA/filtered-error loads use the row path instead.
locator_add_or_remove_index_internal | Maintains indexes and the primary-key replication information associated with a row operation. | Index changes and replication must agree on the row's stored values and operation ordering. | Emits the accumulated OOS replication items only on the insert side, preventing stale insert publication state from being consumed by an index-removal pass.
xlocator_force | Applies workspace copy-area inserts, updates and deletes on the server. | Client flushes must retain the existing protocol and input-image contract. | Flags received insert/update rows for adaptation, saves/restores their original representation ID after pruning, and clears publication state on eligible failures. It preserves caller copy-area bytes instead of converting them in place.
xlocator_repl_force | Applies replication copy-area items, including OOS payload items and their following heap row. | Replica-local OOS OIDs differ from source OIDs and are fixed up before row storage. | Keeps the OOS items and owning row within one row top operation, rejects truncated/interrupted groups, aborts outstanding work on errors, and keeps replicated disk-stub rows out of the workspace adaptation path.
redistribute_partition_data | Moves existing rows when partition definitions are reorganized. | DDL redistribution must preserve each row's logical values and MVCC metadata while changing its owning heap. | Fetches the source child's compact record without eager whole-record Expand, adapts its values into a pending owner and inserts through destination routing. This rebuilds destination-owned chains instead of transplanting source stubs.
cubload::server_object_loader | The per-worker loader maintaining converted DB_VALUEs, an insertion queue and a scan cache. | Server loaddb parses lines separately from flushing batches into heap/index storage. | Replaces a vector of bare record descriptors with pending owners and adds retained-byte accounting and persistent pruning type, so queued references outlive input cleanup and rows can route correctly.
cubload::server_class_installer::register_class_with_attributes | Registers a loader class and its attribute metadata under the loading session. | Worker insertions need class information and the locks acquired by their session. | Acquires BU locks on every child destination of a partitioned input before workers route rows; releases temporary partition metadata and reports lock failures through the loader's normal error handler.
cubload::server_object_loader::server_object_loader | Initializes the worker's loader state and queue. | Each worker starts with no collected rows or active class-specific routing state. | Initializes retained bytes to zero and pruning type to DB_NOT_PARTITIONED_CLASS for the newly owned queue.
cubload::server_object_loader::destroy | Tears down class-specific attribute, scan-cache and queue state. | Loader reuse/destruction must release rows and their retained values before switching context. | Resets retained bytes when clearing the pending-owner queue, keeping memory accounting consistent with RAII cleanup.
cubload::server_object_loader::finish_line | Completes conversion of one input line and queues its row when syntax-only mode and errors permit. | Parsed DB_VALUEs are cleared after each line, but inserts can be delayed until a batch flush. | Prepares a pending owner, catches queue allocation failures, retains payload memory before clearing input, and flushes at 8 MiB including row/vector overhead. A single larger legal row is queued and flushed immediately.
cubload::server_object_loader::start_attrinfo | Starts the class attribute cache for the current loader target. | The loader needs current representation and partition metadata before preparing or writing rows. | Resolves the root OID and records whether input names an ordinary table, partitioned root or direct child; that distinction selects routing or child-domain verification at flush.
cubload::server_object_loader::flush_records | Writes collected loader rows with either per-row top operations or optimized bulk insertion. | Error filtering, replication and partition routing impose different atomicity and bookkeeping needs. | Adds the partitioned per-row path and pruning context, uses SINGLE_ROW_INSERT for routed unique statistics, aborts failed rows, distinguishes filtered errors from session failure and resets retained accounting after a successful flush. This is the direct CI partition-test behavior change.
OosSqlShow | The GoogleTest fixture for SHOW HEAP OOS and now destination-ownership integration assertions. | SQL-visible statistics provide physical ownership evidence beyond logical SELECT equality. | Extends the existing fixture for the new deferred-write matrix and changes cleanup ordering so dependent tables can be dropped safely.
OosSqlShow::SetUp | Drops leftover fixture tables and commits before a test. | Previous tests must not contaminate schema or OOS statistics of the next case. | Drops t_oos_show_yes before t_oos_show_no, permitting new cases where yes references no through a foreign key.
OosSqlShow::TearDown | Drops the same fixture tables and commits after a test. | Every integration case must release table/OOS resources for subsequent tests. | Uses the same foreign-key-safe drop order as SetUp for the expanded matrix.
write_failure | A test-only enum naming preparation, VFID lookup, partial batch and heap insertion failures. | Rollback must be checked at several distinct publication boundaries. | Adds a compact way to drive the new failure matrix without duplicating seam-selection logic.
arm_write_failure | Dispatches one write_failure value to its one-shot injection hook. | Each failure case must target the intended boundary deterministically. | Connects both new preparation/heap seams and existing VFID/partial-batch seams to the new SQL integration tests.
domain_case | A test-data struct containing SQL type, representative value and partition boundary strings. | Routing correctness must cover supported scalar partition domains rather than one integer fixture. | Adds the shared matrix for integer, date/time/time-zone and character key cases; this is test data, not a new engine domain representation.
bridge_oos_debug_counters_reset | A newly declared existing test bridge that clears storage-operation counters. | Logical equality cannot prove that a duplicate probe avoided OOS writes. | Exposes the established counter reset in this test translation unit so individual candidate operations can be measured; its implementation is unchanged.
bridge_oos_debug_counters_get | A newly declared existing test bridge returning OOS debug counters. | Tests need insertion-request counts to separate final writes from speculative probe writes. | Exposes existing instrumentation for the added duplicate-probe assertions; it does not add a production statistics API.
REC_OOS_PENDING | A descriptor-only marker with value 0x100, outside the ordinary persisted record-type domain. | Null-OID temporary stubs must be authorized only for locally constructed rows. | Introduces the marker shared by preparation, Resolve, finalization and storage/transport guards; it is not a new slotted-page or network record type.
LC_RECDES_TO_GET_ONEOBJ | A macro constructing an ordinary RECDES view over one received copy-area object. | Client flush decoding must populate descriptor metadata before locator processing. | Explicitly sets REC_HOME so uninitialized/reused descriptor state cannot authorize pending-memory decoding.
LC_REPL_RECDES_FOR_ONEOBJ | A macro constructing a replicated row's descriptor after its packed key bytes. | Replication copy-area data needs the established key/record offset adjustment. | Sets REC_HOME explicitly for received disk-format replication records; no process-address alternative is admitted.
LC_RECDES_IN_COPYAREA | A macro initializing a RECDES view at the start of a copy area's data region. | Existing copy-area construction/decoding needs a complete descriptor. | Initializes REC_HOME for the same local-versus-received type distinction.
_HEAP_PENDING_RECORD_HPP_ | The include guard for the new pending-owner header. | The class definition must appear once per translation unit. | Adds conventional protection for the new ownership module; this macro has no runtime behavior.
'''

TESTS = r'''
InsertOwnsOosInDestinationHeap | Inserts a large value through a range-partitioned root and inspects root/child OOS statistics. | SELECT alone cannot detect chains written into the wrong heap. | Adds the ticket's fundamental destination-ownership regression.
RawClientInsertOwnsDestinationOos | Exercises a raw client/workspace row insert and checks destination ownership. | Client flushes bypass SQL's attribute-cache producer. | Verifies that the new copy-area adaptation reaches the selected child.
WorkspacePartitionInsertAndMovementOwnDestination | Inserts and changes a partition key through the workspace object path. | Workspace movement can follow different APIs from SQL UPDATE. | Covers both original child ownership and rewriting values into the destination child's OOS file.
RedistributionRewritesMultichunkValuesAtDestination | Reorganizes partitions containing multichunk OOS values and checks values and physical ownership. | Copying a source stub unchanged would leave chains owned by the former heap. | Guards the new compact-source adaptation and destination publication in DDL redistribution.
RawCopyAreaRoutesInsertAndMovementWithoutChangingPayload | Applies raw copy-area inserts and moving updates and compares the source image. | Pruning can rewrite representation metadata while the client still owns its input buffer. | Checks destination chains together with restoration/preservation of copy-area bytes.
RawClientUpdatePreservesUnassignedValuesAndRollsBackFailure | Updates selected client attributes while leaving others unassigned, then tests failure rollback. | Adapting received rows must preserve the complete logical post-image and old committed row. | Covers update adaptation and the error path beyond the SQL producer.
PendingReferencesResolveAndFinalizeInPlace | Reads two retained values before finalization, rejects transport and untrusted memory decoding, then compares memory and disk payloads. | The central representation boundary must preserve values, lifetimes and all non-stub bytes. | Proves source cleanup survival, grouped Resolve, unchanged buffer/length and stub-only finalization; the finalized copied image survives owner destruction.
SerializedPreparationPreservesMvccAndOutlivesSource | Adapts an already serialized record with explicit insert/delete IDs and previous-version LSA, then moves its owner. | Raw adaptation is not a new assignment and must not discard MVCC history or borrow dead input. | Verifies header preservation, default/forced-outline key values and long payload readback after the original owner is gone.
RedistributionFailurePreservesSourceAndNextOperation | Injects preparation, VFID and partial-batch failures during partition reorganization. | DDL movement must not lose original rows or poison a later operation after publication fails. | Checks original multichunk values after rollback and a subsequent successful reorganization.
InternalAndAddressReservationsBypassPreparation | Exercises serial/system work and workspace address reservations. | Bootstrap/system records and OID allocation do not satisfy ordinary user-row preparation assumptions. | Protects the explicit copy-area bypass cases from the new adapter.
ForcedOutlineKeyRoutesFromPreparedBytes | Uses a FORCE_OUTLINE partition key that must be evaluated before its chain exists. | Record-size gating is insufficient: forced-outline values can be selected even for a small row. | Verifies that existing partition readers Resolve the memory alternative and pick the correct child.
RejectedDestinationCreatesNoOosAndNextInsertSucceeds | Inserts a row outside the declared partition domain and follows it with a valid row. | Routing rejection must occur before destination-specific storage effects and must not corrupt publication state. | Covers no-chain creation on an invalid route and recovery of the next insertion.
LobPreparationPreservesSourceAndDestinationValues | Prepares/uses LOB-containing rows and checks source and destination logical values. | Retaining serialized ELO locators must preserve established external-LOB copying semantics. | Guards the serializer's LOB-copy option while OOS write timing changes.
SupportedPartitionDomainsPreserveValuesAndOwnership | Iterates the domain_case matrix for accepted partition-key types. | Canonical bytes must feed the existing type-aware partition evaluator for every supported key domain. | Adds value and physical-ownership coverage across integer, temporal and character keys.
LoaderQueueRetainsClearedInputsAndRollsBackBulkFailure | Queues 64 pending multichunk rows, clears DB_VALUE input and tests bulk failure followed by success. | The loader deliberately delays consumption and moves owners during vector growth. | Checks retained lifetime/accounting and rollback in locator_multi_insert_force; this is a native integration test of the queue contract, not the parser/worker process itself.
AllocationAndStorageFailureLeaveNextInsertUsable | Injects failures at preparation, VFID lookup, partial insertion and later heap insertion. | Every stage has different memory/publication/transaction cleanup obligations. | Adds zero-row/zero-chain rollback assertions and a valid next INSERT for all four boundaries.
ConstraintFailureAfterOosAllowsNextInsert | Forces a duplicate primary-key error after preparing an OOS-bearing candidate. | A failed accepted write must not poison the next operation's publication state. | Protects transaction cleanup after finalization and constraint checking.
DuplicateProbesDoNotPersistCandidateValues | Exercises REPLACE and ON DUPLICATE KEY UPDATE with root/child statistics and insertion counters. | A speculative duplicate-key search must read candidate keys without writing speculative chains. | Distinguishes real final-write requests from probe work and checks no root-owned OOS file is created.
DuplicateProbesReadCompositeKeys | Uses a forced-outline component in a multi-column unique key. | Composite key sizing/deserialization must read complete values rather than temporary stubs. | Guards heap_midxkey_get_oos_extra_size and the common reference decoder in duplicate paths.
DuplicateProbesPreserveFunctionIndexesAndCompressedCompositeKeys | Combines compressed character values, composite uniqueness and scalar/composite function indexes. | Key generation has type/compression/function-index paths beyond simple attribute lookup. | Protects those existing semantics while query-executor probes switch to pending rows.
AbandonedDuplicateCandidateDoesNotWriteOos | Runs a duplicate candidate whose alternative update does not require retaining its large candidate payload. | Speculative candidate ownership must end without a disk chain if the candidate is abandoned. | Adds direct evidence that only the selected update's values are persisted.
DuplicateProbeFailuresLeaveNextWriteUsable | Injects preparation and subsequent storage failures around duplicate-key operations. | Probe rejection and accepted-write rejection must both leave a clean next operation. | Covers failure cleanup for both executor duplicate functions and their downstream force paths.
DuplicateProbesPreserveLobValuesAndRollback | Runs duplicate operations with LOB values and verifies rollback/readback. | REPLACE and duplicate UPDATE intentionally have different LOB-copy choices. | Guards preservation of external LOB semantics and committed values after the pending-owner change.
ReplaceProbeReadsOutlinedCandidateAgainstInlineExistingKey | Matches an outlined candidate key against an inline existing key and checks insertion counts. | Equality must compare logical values despite different storage representations. | Verifies the REPLACE probe's memory Resolve and that it does not publish candidate chains merely to compare keys.
DuplicateProbesPreserveMultipleUniqueConstraintsAndForeignKeys | Combines several unique constraints with foreign-key checking. | Duplicate detection must continue across indexes and respect referential integrity. | Protects cross-index and FK semantics while speculative row construction stops creating OOS chains.
UpdateMovementAllocatesOnlyAtDestination | Moves a SQL-updated row between children and inspects ownership. | The UPDATE producer knows the old class before it knows the new destination. | Verifies that the new post-image is published only into the destination child's file.
UpdateDomainsPreserveUnassignedValuesThroughMovementAndRollback | Iterates partition-key domains while moving rows with unassigned payloads, including rollback. | Retained values must include unassigned UPDATE attributes and survive type-aware key evaluation. | Covers common serializer/default/old-image behavior across moving and aborted updates.
UpdateForcedKeyUsesCanonicalValueAndRejectsWrongPartition | Rejects a direct-child update to an out-of-domain key, then moves through the root and uses DEFAULT. | Forced-outline/default keys must remain logical routing inputs before chain publication. | Guards child validation, root movement and restoration of default key semantics.
UpdateLayoutGrowthAndLobOverwritePreserveValues | Varies payload sizes across offset/layout boundaries while replacing and moving a CLOB. | Buffer growth, PREFER_INLINE and LOB overwrites interact with retained selected values. | Checks successful values and aborted old images without duplicating LOB effects during retry/adaptation.
UpdateFailureClearsPublicationAndRollsBackBothDestinations | Injects preparation/VFID/partial-batch failures for moving and nonmoving updates. | Either target heap can otherwise retain partial chains after a failed post-image write. | Asserts original row equality, zero new chain records, empty publication state and a usable next update.
UpdateIndexFailureRollsBackMovementAndNonmovement | Forces duplicate-key failures in the same and a different child after values become OOS-sized. | Finalization precedes accepted index maintenance, so later index failure must undo new chains. | Covers rollback and follow-up updates on both movement branches.
NonpartitionedUpdateChecksForeignKeysAfterFinalization | Rejects an invalid FK while expanding a nonpartitioned row to OOS, then applies a valid FK update. | Ordinary tables share finalization and must not lose existing FK enforcement. | Guards the nonpartitioned update path and preservation of old values after FK rejection.
RollbackPreservesMultiChunkValuesAndLiveOwnership | Inserts and updates multichunk values, aborts, and checks committed values and current ownership. | Deferred publication must coexist with MVCC undo holding existing disk stubs. | Adds scoped rollback/readback protection; it does not prove long-running vacuum or CDC history correctness.
'''


def parse_rows(text):
    result = {}
    for line in text.strip().splitlines():
        fields = [f.strip() for f in line.split(' | ')]
        assert len(fields) == 4, line
        assert fields[0] not in result
        result[fields[0]] = fields[1:]
    return result


NOTES = parse_rows(PRODUCTION)
NOTES.update({'OosSqlShow.' + k: v for k, v in parse_rows(TESTS).items()})
NOTES['OosServerTest.ReplicaIncompleteOosGroupRollsBackAndUnwinds'] = [
    'Builds a replication force area ending after one OOS item, with and without a publication allocation failure.',
    'A truncated group cannot leave committed chains or an open top operation without an owning heap row.',
    'Checks the new row-group rejection, top-operation depth, empty publication state and unchanged OOS record count.']
NOTES['OosServerTest.ReplicaRowFailureRollsBackItsAppliedOosItem'] = [
    'Applies one OOS item followed by a heap row requiring two chain references, forcing replica fixup failure.',
    'A row failure must undo OOS items already applied for that row rather than treating each item as independent work.',
    'Guards the shared top-operation boundary and verifies no partial-chain growth or leaked operation depth.']
for test, first in [('ReplicaIncompleteOosGroupRollsBackAndUnwinds',
                     'Disarms injection hooks, aborts any remaining nested top operations and clears publication/error state.'),
                    ('ReplicaRowFailureRollsBackItsAppliedOosItem',
                     'Aborts remaining nested top operations and clears publication/error state.')]:
    prefix = 'OosServerTest.' + test + '::'
    NOTES[prefix + 'lambda#1'] = [first, 'Assertion exits must not contaminate later server tests.',
                                 'Adds RAII test cleanup for the newly exercised row-group failure path.']
    NOTES[prefix + 'lambda#2'] = ['Frees the temporary serialized replication record buffers.',
                                 'The synthetic input buffers outlive apply but must be released on any assertion exit.',
                                 'Owns the new failure fixture buffers independently of persisted-chain rollback.']
    NOTES[prefix + 'lambda#3'] = ['Frees the request and reply LC_COPYAREA allocations.',
                                 'Synthetic force areas must be cleaned even if an assertion ends the test early.',
                                 'Completes RAII cleanup for the new replica failure fixture.']

symbols = DATA['symbols']
covered = [s for s in symbols if s['kind'] != 'declaration']
# Header prototypes are mapped to their separately explained definition; existing bridge prototypes get entries.
covered += [s for s in symbols if s['kind'] == 'declaration' and s['name'].startswith('bridge_oos_debug_counters_')]
missing = [s['name'] for s in covered if s['name'] not in NOTES]
assert not missing, missing
for symbol in symbols:
    assert symbol['name'] in NOTES, ('unexplained declaration', symbol['name'])

INTRO = '''# PR #7927 code review guide — aecce0e12

Review [PR #7927](https://github.com/CUBRID/cubrid/pull/7927) at **`aecce0e1216a813771621c13112c8f27d43df22e`**, relative to exact merge base **`fb567a629cdb390fff920542173fa36f454c74a0`** on `feature/oos-merge`. This is the net PR diff: 19 files, 2,452 insertions and 138 deletions. Source links below are pinned to HEAD, not the moving branch.

The bug is physical ownership: serialization used to write OOS chains into the input/root heap before partition selection, while the row subsequently went into a child heap. SELECT can still succeed by following its stub, but vacuum looks for the OOS file in the row's owning heap. The change retains selected serialized values in memory, routes the compact row, then publishes those values into the destination heap's OOS file.

The current implementation uses `heap_pending_record` and `heap_oos_value_ref`. Older reports describing `heap_prepared_row`, a five-part column store or an explicit building/prepared/consumed/completed state machine describe earlier PR revisions. Those types and mechanisms are not in this net diff. Rationale here is reconstructed from this exact source, the current PR body and [CBRD-27089](https://jira.cubrid.org/browse/CBRD-27089), whose historical description still uses the old names.

## Read in this order

1. The ownership/reference types and their inline methods: `heap_pending_record.hpp/.cpp`, `heap_oos.hpp`.
2. Prepare and Resolve: `heap_attrinfo_prepare_record`, `heap_prepare_oos_record`, the changed serializer and attribute/key readers.
3. Destination selection and publication: `locator_insert_force`, `locator_update_force`, `locator_move_record`, `heap_oos_finalize_record`.
4. Producers that bypass ordinary SQL preparation: copy areas, redistribution, loader, replica apply.
5. Storage/transport guards, duplicate probes, and the individually mapped regression tests.

```mermaid
flowchart TD
    A[SQL attributes or server loader] --> B[Prepare compact pending row and retain OOS bytes]
    B --> C[Existing partition and key readers Resolve memory values]
    C --> D[Select and lock destination heap]
    E[Client copy-area row] --> D
    D --> F[Adapt client input if required]
    F --> G[Publish chains into destination OOS file]
    G --> H[Overwrite existing 24-byte stubs and mark REC_HOME]
    H --> I[Existing heap and index writes]
    J[Replica OOS items and following row] --> K[One row top operation and disk-stub fixup]
    K --> I
```

## Review contracts and limits

- The pending owner holds the record allocation and only separately serialized selected OOS values. Its destructor frees memory; rollback of written chains belongs to the enclosing transaction/system operation.
- Pending RECDES views borrow the owner. Moving an owner preserves allocations; destroying it invalidates its unfinalized memory references. A copied descriptor does not extend that lifetime.
- Finalization updates the type of the RECDES argument, not every aliased descriptor. The bulk path explicitly writes the finalized type back to its owner; other force callers consume a local borrowed descriptor while the owner stays alive.
- Prepare retains selected values without inserting their OOS chains. It can read old OOS values and can perform established LOB-copy effects; it is not a guarantee of zero I/O or zero other side effects.
- Finalize happens after routing and before accepted heap/index writes. It changes stubs in place, preserves record length/offset layout and publishes no partial set of stub replacements on batch failure. Its result does not mean the heap write or transaction committed.
- A failed finalization must be rolled back. Unlike the older prepared-row implementation, this revision has no explicit consumed phase field enforcing one-shot retry; review every caller against the stated non-retryable contract.
- `REC_OOS_PENDING` authorizes process-address decoding only for locally prepared descriptors. Heap insert/update and descriptor packing reject it; unpack/copy-area construction do not give received bytes that authorization. Review the guards as a complete caller chain, not merely the null-OID check.
- The loader's 8 MiB threshold includes retained payloads and queue capacity; one large legal input can exceed it transiently. Partitioned, replicated and error-filtered loads take the per-row path. Child-input validation also changes ordinary integer-only loader behavior.
- Replication keeps consecutive OOS items and their following heap row atomic. `LC_IS_FLUSH_INSERT` includes `LC_FLUSH_INSERT_OOS`; the continuation check therefore permits multiple OOS items. Review rejection of truncated groups and operation-depth cleanup.
- This PR changes OOS publication timing, not the 24-byte durable stub, identity-stamp mechanism, demotion policy or CDC historical lifetime. The base's raw `DB_PAGESIZE/4` gate differs from the normative four-record physical target; that inherited conformance gap is outside this diff.

## CI findings to bring into the review

The [exact-head CI analysis](../ci_analysis_report_aecce0e_codex.md) records six failed cases: three medium queries differing only in unordered row presentation, one loader case directly affected by child-domain validation, and two CDC failure categories also observed on the exact merge base. The medium result is not enough to attribute drift to the engine: CTP revisions differ between runs. The loader's rejection is intentional according to the PR description, but its legacy answer must still be reconciled with the intended partition contract. No all-green CI or whole-OOS acceptance is claimed.

## Every changed definition

Each entry answers what the symbol is, why it exists and why it is changed at this HEAD. Functions declared in more than one file have one explanation plus a declaration-location index below. C++ classes, the new union and enums are included in addition to structs. Added `= delete` declarations prohibit copying; they are not deletions of previously implemented functions. There are no deleted function/type definitions in this net diff.
'''

lines = [INTRO]
current = None
for symbol in covered:
    if symbol['path'] != current:
        current = symbol['path']
        lines += [f"\n### {current}\n"]
    node = symbol['head'] or symbol['base']
    revision = HEAD if symbol['head'] else DATA['base']
    url = f"https://github.com/CUBRID/cubrid/blob/{revision}/{symbol['path']}#L{node['start']}"
    what, exists, changed = NOTES[symbol['name']]
    lines += [f"\n#### `{symbol['name']}` — {symbol['status']} {symbol['kind']}\n\n",
              f"[Source, line {node['start']}]({url})\n\n",
              f"- **What:** {what}\n- **Why it exists:** {exists}\n- **Why changed here:** {changed}\n"]

lines += ['''
## Declaration and build wiring index

The following declarations refer to symbols explained above. New function bodies are explained at their definition, while changed defaults/signatures are described in the corresponding entry. The indentation wrappers added around `locator_allocate_copy_area_by_attr_info` in `locator_sr.h` do not change its declaration or implementation; the function itself is unchanged and remains available for other callers.

| Declaration | File and line | Change |
|---|---|---|
''']
for symbol in symbols:
    if symbol['kind'] != 'declaration':
        continue
    node = symbol['head'] or symbol['base']
    url = f"https://github.com/CUBRID/cubrid/blob/{HEAD}/{symbol['path']}#L{node['start']}"
    lines.append(f"| `{symbol['name']}` | [{symbol['path']}:{node['start']}]({url}) | {symbol['status']} |\n")
lines += ['''
| Other changed file | Why it changes |
|---|---|
| `cubrid/CMakeLists.txt` | Compiles the new pending-owner implementation into the server engine target. |
| `sa/CMakeLists.txt` | Compiles the same owner into standalone mode, including SQL integration consumers. |
| `unit_tests/oos/sql/CMakeLists.txt` | Raises the existing `test_oos_sql_show` timeout to 90 seconds for the expanded expected-error matrix and debug stack-trace collection. |

## Coverage and verification boundary

[Symbol inventory](evidence/symbols.json) was extracted from both exact Git revisions with tree-sitter C++ and a GNU top-level function-boundary fallback for conditionally compiled `.c` functions. [Authoring/coverage script](evidence/build_guide.py) requires an individual three-part explanation for every inventory symbol, including inline methods, deleted copy operations, nested types, newly exposed existing counter declarations and the six new cleanup lambdas. Existing lambdas merely shifted by added lines are not counted as changed.

[Hunk audit](evidence/hunk-coverage.json) independently checks the definition inventory against the zero-context net diff. Non-definition hunks are classified as includes, declarations, build wiring or comments/whitespace. This is an explanation guide, not an independent Standards/Spec review verdict. CI builds passed at this HEAD; the PR body's older local CTest/loader claims were not rerun or promoted into new verification claims during this documentation task.
''']
guide = ''.join(lines)
(ROOT / 'code_review_guide.md').write_text(guide)
validation = {'base': DATA['base'], 'head': HEAD, 'inventory_records': len(symbols),
              'explained_entries': len(covered), 'functions': sum(s['kind'] == 'function' for s in symbols),
              'types': sum(s['kind'] in ('class', 'struct', 'union', 'enum') for s in symbols),
              'lambdas': sum(s['kind'] == 'lambda' for s in symbols), 'missing_explanations': []}
(HERE / 'guide-coverage.json').write_text(json.dumps(validation, indent=2) + '\n')
print(json.dumps(validation, indent=2))
