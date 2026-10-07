# PR7927 proposal without a pending record type

Status: design, transport contract, verification seams and four-task breakdown
approved on 2026-10-07; implementation in progress. Work-tracker: 281 (design agreement). Reviewed source
is `aecce0e1216a813771621c13112c8f27d43df22e`; its merge base with
`feature/oos-merge` is `fb567a629cdb390fff920542173fa36f454c74a0`.
The [interview](temporary-oos-stub-interview.md) records accepted constraints and
open decisions. This note makes the interface direction concrete; code-level
details remain proposals and verification obligations.

## What the owner argument means

`heap_pending_record` already owns the compact record allocation and the selected
serialized OOS payload allocations. An **owner argument** is a borrowed pointer
to that existing object, valid only while the caller keeps it alive. It would be
passed through prepared-row readers, rather than encoded in the record or added
to shared `RECDES`. It is an implementation parameter, not new domain vocabulary.

For a retained 6,000-byte value, the proposed temporary 24-byte stub is:

```text
null head OOS OID | full length = 6000 | payload index = 0
```

The common value reader uses the supplied owner to find retained payload 0. It
checks that the owner is prepared, that the record borrows the owner's allocation,
and that the index and length match an owned payload before constructing a memory
reference. Without the appropriate owner, the null head remains invalid. The
current source instead encodes a raw address and authorizes it with
`REC_OOS_PENDING` (`heap_oos.cpp:56-114`). The proposed index avoids putting a
memory address in serialized bytes and needs no separate location-to-value map.

After destination insertion, the same stub becomes:

```text
real head OOS OID | full length = 6000 | packed identity stamp
```

Ordinary disk readers then use the stored chain. The existing common
`length()`/`read_into()` contract remains; memory reads still copy into the
caller's buffer.

## Proposed call flow

The existing owner is available in `locator_attribute_info_force`
(`locator_sr.c:7701,7807-7840`) and both duplicate probes
(`query_executor.c:12051,12271`). Proposed flow, not compilable final signatures:

```text
prepare into existing owner
  -> pass borrowed RECDES plus owner through locator force
  -> partition routing reads required values using that owner
  -> finalizer(destination, current RECDES view, owner)
  -> heap/index consumers receive completed disk references
```

Required reader propagation includes `partition_prune_insert/update`,
`partition_find_partition_for_record`, scalar/grouped attribute Resolve,
`heap_attrvalue_get_key`, composite-key sizing/value reads, and function-index
evaluation. A function index creates a different attribute cache, so forwarding
context only to the outer cache would miss that path
(`heap_file.c:15182,15219,19755-19815`). Explicit arguments avoid retaining a
borrowed owner in reusable caches. Movement must forward the owner into
destination INSERT.

Copy-area rows already have routable values and continue routing first; their
destination conversion creates its owner afterward. Redistribution and loader
rows already have owners. Loader moves preserve allocations, byte accounting
includes record and retained payload memory, and bulk finalization stays before
heap-page latching.

## State and header handling

The owner must distinguish preparation from completed finalization independently
of payload-list emptiness. Inline-only prepared rows still require the per-row
OOS publication reset; a second call for an already-completed row must not clear
a later row's publication queue. Failed finalization retains the existing
rollback-required, non-retryable contract.

The finalizer receives the **current descriptor view** as well as the owner.
UPDATE can move the body and change the borrowed view's length while adding an
MVCC header (`locator_sr.c:5920-5959`,
`base/object_representation_sr.c:4424-4434`). Owner provenance therefore cannot
require equality with the owner's original descriptor length. Finalization uses
the current representation/VOT walk to find stub locations; it stores no patch
pointers that could become stale during header changes.

## Accepted storage and transport contract

Heap logical INSERT/UPDATE currently reject the descriptor marker
(`heap_file.c:25141,25573`). Replace those guards with heap-row validation using
the destination class representation. Accept legitimate disk references and
reject null-head OOS placeholders before storage. A finalizer with no owner must
also validate disk-only input before subsequent index/replication publication.
Apply bounds checks before reading row headers or fields. Do not require a
`LAST_ELEMENT` sentinel in legacy rows: the existing `heap_recdes_get_oos_refs`
walk is prior art, but it lacks early header bounds checks, allocates, and aborts
when the sentinel is absent. Generic slotted pages also hold non-row records, so
these checks belong in heap-row write paths.

The production transport audit found no pending-row uses of
`record_descriptor::pack`. Actual row transport uses `LC_COPYAREA`;
`locator_send_copy_area` sends content unchanged (`locator.c:673–686`). That
shared transport also carries flush requests, replication OOS payloads and
key/error/message replies, which must not be parsed as heap rows.

Recommend one heap-row export check at the three server `LC_FETCH` publication
seams: `locator_return_object_assign` (`locator_sr.c:2185–2216`),
`xlocator_fetch_all` (`2915–2925`) and `xlocator_lock_and_fetch_all`
(`12247–12304`). Each knows the class and already requests raw-byte consumption,
which expands OOS attributes. Safely reject a successful non-root row that still
has the OOS header flag, before publishing its descriptor or incrementing the
copy-area object count. This rejects copied temporary images and accidentally
unexpanded persisted stubs, without schema parsing at export. Preserve root-class
metadata and CHN/deleted/decache descriptors without row content.

Restore generic `record_descriptor::pack/unpack` to their baseline arbitrary-byte
contract. A generic byte copy does not supply an owner or authorize memory
access. Its current direct-pack rejection test does not exercise production row
transport; replace that assertion with a release-build rejection test at the
actual row-export seam. Incoming flush/replication bytes remain disk-only and
never acquire the local owner. Loader network batches carry source text; pending
owners are created and queued server-side.

This accepted contract resolves the earlier ambiguous byte-pattern scan proposal.
No new descriptor field, record type, generic serialization contract or global
pointer registry is needed. Acceptance establishes the intended design;
implementation and verification must establish the safety guarantee.

## Accepted verification seams

Prefer existing engine/SQL tests and their public behavior over new test-only
accessors. Cover destination ownership, copy-area UPDATE, partition movement,
scalar/grouped reads, composite and function-index keys, loader queuing and
rollback, and replication group failure. Existing owner tests cover compact
allocation reuse, in-place finalization, current MVCC header views and payload
lifetime. Extend those to missing/wrong owner, invalid payload index/length,
owner moves, and inline-only/repeated-finalization publication state.

At the actual export and logical-storage boundaries, reject temporary rows and
copied byte images in release builds without publishing a copy-area descriptor,
accept finalized/expanded rows, and retain supported root/non-row/legacy paths.
Keep arbitrary-byte packing tests separate. Run the configured debug build and
CTest suite, focused guard checks without assertions, and the established real
server-loader fixture. Record results against the resulting local commit; old
verification remains historical. No replacement build or runtime verification
has been performed.

## Approved task breakdown

1. **Explicit-owner prepared-row access.** No blockers. Introduce the trusted
   owner-index access path through all supported readers and current-view
   finalization, with ownership and SQL coverage. Keep the existing marker only
   as a migration guard until task 2; add no replacement type.
2. **Remove the marker at storage/export boundaries.** Blocked by 1. Remove
   `REC_OOS_PENDING`, enforce the row-aware storage/export contracts, restore
   generic packing, and run the agreed build, CTest, guard and loader checks.
3. **Reconcile reviewer dispositions and local replies.** Blocked by 2. Recheck
   the two comments against the resulting local revision and fixed PR baseline,
   preserving the evidence distinction between new adaptation cost and existing
   fresh-chain behavior. Keep chain reuse outside this implementation.
4. **Publish the current documentation entry point.** Blocked by 2 and 3. Align
   vocabulary and task status, mark superseded narratives, preserve verification
   evidence, repair links and expose current design/checks/replies from one index.

The user confirmed the final design and this breakdown with "I approve".
The [spec](../../.scratch/pr7927-oos-review-cleanup/spec.md) and
[task map](../../.scratch/pr7927-oos-review-cleanup/map.md) record the authorized
implementation and final two-axis review. Remote replies remain local drafts;
pushes and integration merges require separate authorization.
