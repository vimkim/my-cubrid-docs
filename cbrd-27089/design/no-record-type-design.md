# PR7927 destination-owned OOS writes without a temporary record type

Approved 2026-10-07. Work-tracker 281 records design agreement; 289 implements
engine tasks; 284 records documentation and reviewer work. Enter through the
[current CBRD-27089 index](../README.md). The [interview](temporary-oos-stub-interview.md)
preserves questions and decisions; the [spec](../../.scratch/pr7927-oos-review-cleanup/spec.md)
and [task map](../../.scratch/pr7927-oos-review-cleanup/map.md) record acceptance.

The remote PR head used for comparison is
`aecce0e1216a813771621c13112c8f27d43df22e`; its baseline is
`fb567a629cdb390fff920542173fa36f454c74a0`. Local implementation begins with
`c73f01c1d` and `29281a205`; the [verification record](no-record-type-verification.md)
identifies the final local revision and its checks. Remote CI remains separate.

## Owner and representation

The existing `heap_pending_record` owns the compact record allocation and selected
serialized payload allocations. A borrowed owner argument points to that object
while its caller keeps it alive. Preparation state belongs to this owner, with
empty, prepared, finalized and failed states. Shared `RECDES` retains its baseline
layout, and prepared rows use the existing `REC_HOME` type. `REC_OOS_PENDING` is
removed with no replacement type.

A temporary 24-byte OOS inline stub contains:

```text
null head OOS OID | full length | owner-local payload index
```

It contains no memory address. A prepared-row reader requires the supplied owner
to be prepared, the record view to borrow its allocation, and the index and length
to match a retained payload. A copied byte image or different owner cannot grant
memory access. The common OOS value reference keeps `length()` and `read_into()`
for memory and disk values; reading still copies into the caller's buffer.

After insertion into the destination heap's OOS file, the same stub contains:

```text
real head OOS OID | full length | packed chain identity stamp
```

This is the existing disk representation. Identity identifies a chain occupant;
it does not prove that vacuum may reclaim a shared chain.

## Routing and finalization

```text
prepare into the existing row owner
  -> route through a borrowed record view and explicit owner
  -> finalize(destination heap, current record view, owner)
  -> publish completed disk references to heap/index consumers
```

Owner arguments reach scalar/grouped attribute reads, partition routing,
composite-key sizing and reads, duplicate probes and the separate function-index
attribute cache. They are not retained in reusable caches. A moving UPDATE passes
the owner to destination INSERT. Client copy-area rows route before conversion;
conversion creates a server-local owner afterward. Incoming replication bytes
never acquire an owner.

Finalization locates stubs through the current descriptor's representation and
variable-offset table, then patches only their 24 bytes. UPDATE can grow the MVCC
header while retaining the allocation; owner association therefore checks the
allocation and capacity rather than requiring its original record length.
Finalization updates the owner's descriptor length to the current view. No saved
patch address or complete row clone is required.

Owner moves preserve payload allocations and retained-byte accounting. Server
loader bulk insertion finalizes before heap-page latching. The per-row fallback
for partitioning, HA or filtered insert errors also forwards its queued owner.
Inline-only prepared rows reset per-row publication once. Repeated successful
finalization does not clear later publication. Failure marks the owner failed;
partial chain creation requires rollback and cannot be retried as a fresh row.

## Storage and transport boundaries

Logical heap INSERT/UPDATE and ownerless finalization validate heap-row headers,
variable-offset bounds and OOS references against the class representation.
Null-head placeholders are rejected before storage. Supported legacy rows need
no new `LAST_ELEMENT` sentinel. Root metadata and address reservations retain
their supported paths. Generic slotted-page records are not treated as heap rows.

The three locator fetch producers already request OOS expansion. Their shared
`locator_copyarea_add_fetch` guard rejects residual OOS or short non-root row
headers before publishing a descriptor or incrementing the object count. CHN,
deleted and decache descriptors have no row content and retain their paths.

Review also identified an inherited optional-neighbor prefetch path that copies
raw slotted-page rows. It skips malformed or OOS-bearing non-root neighbors and
continues collecting inline neighbors. OOS neighbors can be fetched normally
through the expanding path. Expanding them while holding the heap-page latch
would require a separate latch-order design.

Generic `record_descriptor::pack/unpack` retains its baseline arbitrary-byte
contract. Storage and actual row export provide the guards. Shared copy-area
transport also carries flush requests, replication OOS payloads and key/error
replies; those payloads are not parsed as fetched heap rows.

## Verification and scope

The [verification record](no-record-type-verification.md) reports debug build and
configured CTest, focused storage/export/ownership checks with assertions disabled,
real server-loader batching and routing, and the Standards/Spec review. It
preserves failed reproductions and subsequent corrections. Historical reports
apply only to their pinned revisions.

The [reviewer dispositions and Korean drafts](reviewer-comments-aecce0e.md)
distinguish newly introduced client copy-area adaptation from existing client
whole-row work and server fresh-chain UPDATE behavior. Total performance impact
remains unmeasured. Unchanged-chain reuse remains separate CBRD-27230 work requiring
MVCC ownership, commit-conditional reclamation and replication changes;
CBRD-27237 vacuum correctness remains independent. Replies stay local drafts.
