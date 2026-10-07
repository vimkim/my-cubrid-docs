# PR7927 proposal without a pending record type

Status: proposed, not accepted or implemented. Work-tracker: 281. Reviewed source
is `aecce0e1216a813771621c13112c8f27d43df22e`; its merge base with
`feature/oos-merge` is `fb567a629cdb390fff920542173fa36f454c74a0`.
The [interview](temporary-oos-stub-interview.md) records accepted constraints and
open decisions. This note makes the proposed interface concrete.

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

## Storage and transport proof obligation

Heap logical INSERT/UPDATE currently reject the descriptor marker
(`heap_file.c:25141,25573`). Their replacement can inspect heap-row fields and
reject null-head OOS placeholders before storage. Generic slotted pages also
hold non-row records, so those checks belong in heap-row write paths.

All newly prepared rows emit a `LAST_ELEMENT` VOT sentinel
(`heap_file.c:13807`). A copied pending byte image retains its placeholders.
A bounded, allocation-free scan can recognize and reject a complete modern
temporary heap-row image before a row packer writes its first byte. The existing
`heap_recdes_get_oos_refs` traversal is prior art, not a ready-made universal
validator: it lacks early header bounds checks, allocates, and aborts for a
missing sentinel. Legacy images must retain their existing supported behavior.

**Open transport contract:** `record_descriptor` also represents arbitrary byte
buffers. A shared-header flag alone does not prove a buffer is a heap row, and
copied bytes lose external provenance. A byte-only check cannot both permit every
arbitrary sequence and reject that identical sequence as a pending heap row.
The implementation must either make heap-row export explicit, or explicitly
reserve/reject the complete temporary heap-row byte pattern during packing.
Neither choice is yet accepted. This is not a reason to interpret arbitrary
data as heap metadata or silently reject legacy formats.

Verification must cover no/wrong owner, invalid index/length, owner moves, scalar,
grouped, composite and function reads, header growth, inline-only publication
reset, copied-view packing with untouched output on rejection, and ordinary
disk/non-row/legacy export. No replacement build or runtime verification has
been performed.
