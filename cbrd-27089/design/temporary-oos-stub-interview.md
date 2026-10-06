# PR7927 temporary OOS stub design interview

Status: in-place finalization and full replacement scope accepted; user proposes discriminated memory/disk reference with a uniform interface. Exact placement and provenance remain open. Design discussion only; no engine implementation authorized by this interview.
Work tracker: 276. Source inspected: `feat/oos-deferred-write`, `9232f111a`.

## User objective

Replace `heap_prepared_row` with an ordinary RECDES layout, temporary OOS inline stubs and retained values. Read retained values when routing needs them, then insert into the selected destination heap's OOS file. Minimize total code and reviewer effort.

The earlier full-inline destination-write POC (work item 271) was withdrawn and removed. This is a different proposal. Existing source submodule changes and untracked `repro.sh` are preserved.

## Source facts

- `src/query/partition.c:3508`: pruning uses `heap_attrinfo_read_dbvalues` unless the prepared-row override is supplied. Shared decoder support could remove that override.
- `src/storage/heap_file.c:11077`: single-attribute OOS Resolve currently reads a persisted chain into scratch or owned memory. Borrowed pending bytes need a defined ownership contract.
- `src/storage/heap_oos.cpp:465`: NULL head OOS OID is rejected; it cannot simply become an implicitly trusted memory pointer marker.
- `src/storage/heap_file.c:11384`, `src/storage/heap_oos.cpp:516`: grouped prefetch bypasses the single-attribute resolver. It also needs pending handling or a deliberate bypass.
- `src/storage/heap_file.c:15615`: pre-finalization composite index key construction uses prepared values to size keys; a compact RECDES length alone is insufficient.
- `src/transaction/locator_sr.c:5063`: INSERT finalizes after partition selection; destination is already known there.
- `src/transaction/locator_sr.c:14125`: bulk loaddb finalizes retained rows before bulk heap page latching to avoid heap-header/data-page latch interaction.
- Actual branch and normative specification use a 24-byte persisted OOS inline stub. Proposed transient encoding must not change that persisted layout.

## Proposed vocabulary (not yet ratified)

- Pending OOS value: an attribute value selected for OOS whose storage destination has not yet been materialized.
- Pending OOS stub: the temporary representation referring to that value before a stored chain exists.
- Suggested implementation owner name: `heap_pending_oos_values`. Retain only selected serialized values; ordinary attributes remain in the RECDES.

Update canonical `CONTEXT.md` only after terminology is agreed. No ADR yet: encoding, scope and alternatives remain open.

## Round 1 frontier

1. Self-contained access: original question remains open. User clarified a mandatory constraint: reuse the built RECDES and overwrite its OOS inline stubs in place with real OOS references. This is feasible with either accessor design and does not settle pointer versus context. Recommend self-contained access conditionally on an enforceable trusted transient-record boundary.
2. Replacement scope: ACCEPTED by user Q2 "yes": replace prepared-row use across existing supported PR paths, including UPDATE movement, duplicate probes, loader and HA.

## Subsequent questions and proof obligations

Exact encoding and transient trust boundary depend on question 1; sequencing depends on scope. Investigate stable payload ownership across vector moves, RECDES copying, retries, LOB exactly-once effects, grouped reads, key sizing, partial insertion rollback and publication/replication. These correctness facts are the agent's work, not questions asking the user to relax safety.

Implementation requires explicit confirmation of shared design understanding under the invoked grilling skill. No build, DB experiment, push or PR modification performed.

## Accepted in-place finalization constraint

Serialize inline attributes once into the compact RECDES and reserve exactly one 24-byte field per selected OOS value. Once destination insertion returns the real chain references, overwrite those same fields with head OOS OID, full serialized length and identity stamp. Finalization must not reserialize ordinary attributes, allocate a replacement record or change its length or VOT offsets. Existing partition representation-ID changes are distinct from rebuilding the record.

This constraint applies to finalization of the pending record, not all subsequent heap-layer MVCC/header manipulation. The current `heap_prepared_row::finalize` already demonstrates an in-place 24-byte overwrite (`src/storage/heap_file.c:14367`); the proposed change removes the larger owner/API design around it.

## Rebuild and PR update direction

User suggested starting over from `feature/oos-merge` and force-pushing rather than reworking the prepared-row implementation. Favor a fresh sibling source worktree from that integration branch while preserving the existing worktree/branch and its unrelated modifications for comparison. Implementation still follows shared-design confirmation; publication follows verification. Use an explicit expected-old-head lease so concurrent remote work is not overwritten.

Live read-only checks: PR7927 targets `feature/oos-merge`; its head is `vimkim/cubrid:feat/oos-deferred-write` at `9232f111a7e7b6c71dbfa451db2812ae14766041`, routed through `vk`. Remote `origin/feature/oos-merge` matches local base at `fb567a629cdb390fff920542173fa36f454c74a0`. Recheck these before implementation/publication. No branch reset or push performed.

## Round 2 frontier: transient descriptor provenance

Q3: allow an in-memory-only discriminator in the existing `RECDES.type`, while preserving the descriptor structure, the allocated record buffer, length and VOT? Recommend yes. A locally prepared pending record may use a NULL-head/length/accessor temporary field and shared readers branch on the trusted descriptor discriminator. After successful destination insertion, overwrite the same 24-byte fields with ordinary chain references and restore the normal descriptor type before heap storage. Encoding details remain to be verified.

Source evidence: `storage_common.h:226` has INT16 type; persisted slotted-page type is four bits (`slotted_page.h:90`). Pruning leaves type intact. Current INSERT normalizes type only after finalization (`locator_sr.c:5086`). UPDATE movement passes the descriptor through to destination INSERT. Copies preserve type.

Correctness obligations: locator copy-area macros do not initialize type (`locator.h:55`, `75`), so initialize it per incoming row; prohibit transient descriptors through generic pack/unpack (`record_descriptor.cpp:327`, `334`) or physical storage; leave persistent NULL-reference validation intact. Stable allocated payload addresses, owner lifetime and bulk retained-byte accounting remain mandatory. No global pointer registry is needed if descriptor provenance is enforced. This is source-supported feasibility, not executed proof.

## User steering: discriminated memory/disk reference

User challenges situational decoder behavior and proposes a discriminated union exposing one OOS value-access interface regardless of memory or disk storage. Favor this direction: decode the packed field once into a proposed `heap_oos_value_ref` with explicit memory and disk alternatives. Expose one `read_into` contract so callers share copying, error and value-decoding behavior. Keep `oos_read` as the physical disk-chain reader; the memory alternative copies retained serialized bytes into the requested destination.

This supersedes Q3 as a choice of making callers inspect `RECDES.type`. Such a field could still be an internal provenance mechanism, but it is not a required user-facing interface or an accepted encoding decision. A discriminated union centralizes representation dispatch; it does not by itself establish validity/lifetime of a memory accessor decoded from bytes. Resolve that inside construction/validation rather than spreading state tests through partitioning and indexes.

The runtime C++ tagged union is distinct from the packed 24-byte record representation: do not memcpy an ABI-sized union or std::variant into the stub. Existing persisted layout remains OID/length/stamp. Pending packed encoding can use a reserved representation only after invalid/corrupt disk and incoming bytes are prevented from constructing a trusted memory reference. Finalization converts each pending packed field to the existing disk representation in place.

Revised Q3 recommendation: put the memory/disk union and common read operation at the heap attribute-access seam, preserve disk-only `oos_read`, and keep partition/index callers representation-agnostic. This scope avoids rewriting physical OOS storage APIs while solving the two real access modes. Exact tag encoding and memory-owner mechanics remain implementation design facts to investigate.

### Round 3 frontier: common access contract

Q4: should both alternatives expose the same copy-into-caller-buffer operation rather than memory returning borrowed bytes and disk returning allocated bytes? Recommend yes for initial redesign: use caller scratch where available and preserve the existing DB_VALUE copy/free contract. This keeps representation and ownership branching out of callers. Direct borrowed access can be considered later only if measurements justify complicating that contract.

Source investigation confirms the proposed union can stay at heap Resolve, with size inspection, single reads and grouped reads consuming it. Grouped disk reads should preserve batching. No compilation/runtime experiment performed.
