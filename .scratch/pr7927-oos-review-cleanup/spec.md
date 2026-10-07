# PR7927: remove the pending record type and consolidate review documentation

Status: ready-for-agent
Approved: 2026-10-07, user response "I approve" to the final design, verification seams and four-task breakdown.
Work-tracker: 281 (design agreement), 284 (documentation and reviewer assessment).

## Problem Statement

The destination-owned OOS implementation introduces a temporary record type that
confuses reviewers and couples generic record descriptors to local preparation.
Older documents and task notes compete with the current design. Reviewers also
need a precise account of UPDATE costs and whether unchanged-chain reuse is safe.

## Solution

Keep the shared RECDES layout and existing persisted record types. Pass the
existing prepared-row owner explicitly to readers that need pending OOS values.
Finalize those values into the destination heap and patch the compact buffer in
place. Enforce storage and actual heap-row export boundaries. Provide one current
documentation entry point with historical evidence and locally drafted replies.

## User Stories

1. As an engine reviewer, I want no new pending record type, so that persisted and local preparation concepts remain clear.
2. As an engine maintainer, I want the shared RECDES layout unchanged, so that generic descriptor initialization and copying remain familiar.
3. As a prepared-row reader, I want an explicit borrowed owner, so that memory access requires valid local ownership.
4. As a row owner, I want placeholders to identify retained payloads without raw addresses, so that byte images cannot supply arbitrary memory references.
5. As a routing caller, I want scalar reads to resolve pending values, so that destination selection remains correct.
6. As a routing caller, I want grouped reads to resolve pending values, so that batching remains correct.
7. As a duplicate probe, I want composite keys to include complete values, so that outlined attributes do not change uniqueness semantics.
8. As a function-index evaluator, I want the same owner forwarded to its separate attribute cache, so that expression keys remain correct.
9. As an INSERT caller, I want chains written only into the destination heap, so that a partitioned root does not own child values.
10. As an UPDATE caller, I want destination movement to retain the row owner, so that relocated rows use their destination's OOS file.
11. As an UPDATE caller, I want current MVCC header views supported, so that body relocation cannot leave stale patch addresses.
12. As a finalization caller, I want the compact allocation reused, so that finalization does not rebuild ordinary attributes.
13. As a row owner, I want stable allocations across moves, so that queued readers remain valid.
14. As a row owner, I want retained-byte accounting preserved, so that loader batch limits reflect memory held.
15. As a loader caller, I want finalization before heap-page latching, so that existing latch ordering survives.
16. As a publication caller, I want inline-only rows to reset publication once, so that stale OOS metadata cannot attach to another row.
17. As a publication caller, I want repeated finalization not to clear another row's publication, so that completion remains stable.
18. As a transaction caller, I want failed finalization to require rollback, so that partial insertions are never retried as a fresh operation.
19. As a heap writer, I want copied temporary byte images rejected, so that stored rows contain only valid disk references.
20. As a network exporter, I want expanded heap rows checked before publication, so that temporary or unexpanded OOS stubs cannot be transmitted.
21. As a generic packer caller, I want arbitrary-byte packing retained, so that non-row payloads keep their baseline contract.
22. As a replication caller, I want incoming rows to remain disk-only, so that remote bytes cannot acquire local ownership.
23. As a replication caller, I want OOS payloads and error replies preserved, so that row guards do not parse unrelated content.
24. As an engine maintainer, I want root metadata and legacy rows supported, so that safety checks do not impose a new format requirement.
25. As a reviewer, I want newly added client adaptation cost distinguished from existing fresh-chain UPDATE behavior, so that performance concerns receive an accurate disposition.
26. As an MVCC reviewer, I want chain identity distinguished from reclamation eligibility, so that unchanged-chain reuse is not accepted on insufficient evidence.
27. As a documentation reader, I want one current entry point, so that I can find the agreed design, verification and reviewer replies.
28. As a documentation reader, I want historical reports labeled and evidence preserved, so that old verification remains useful without claiming current validity.
29. As the contributor, I want remote replies kept as local drafts, so that I can review them before publication.
30. As the contributor, I want meaningful changes locally committed and unrelated work preserved, so that the result is reviewable.

## Implementation Decisions

- Reuse the existing compact row/payload owner; add no replacement record type,
  shared descriptor field, pointer registry or owner pointer in reusable caches.
- Pending placeholders use null head, full length and an owner-local payload
  index. Validate preparation state, record allocation association, index and
  length before constructing the common memory/disk value reference.
- Propagate explicit borrowed owner arguments through routing, scalar/grouped
  reads, composite-key sizing and reads, duplicate probes and function indexes.
- Finalization accepts the current descriptor view and owner, preserving buffer,
  record length and offsets during the 24-byte disk-reference patch. Subsequent
  heap-layer MVCC header manipulation retains its existing contract.
- Distinguish prepared, completed and failed state independently of payload
  emptiness. Retain rollback and per-logical-row publication guarantees.
- Copy-area routing occurs before destination conversion; loader owners stay
  server-local and bulk finalization remains before heap-page latching.
- Logical heap writes and ownerless finalization validate disk references against
  the class representation. Check bounds and preserve supported legacy layouts.
- At the three actual server LC_FETCH row-publication seams, reject residual OOS
  fields after Expand, before descriptor/count publication. Root-class metadata
  and no-content descriptors remain outside this row check.
- Restore generic descriptor packing to its baseline arbitrary-byte semantics.
  Incoming replication rows never receive local owner arguments.
- Keep fresh-chain behavior. Unchanged-chain reuse requires separate MVCC,
  vacuum ownership/reclamation and replication work.
- Use canonical destination heap, pending OOS value, OOS value reference and
  OOS finalization terminology. Old architecture names remain in labeled history.

## Testing Decisions

- Test observable behavior at the approved existing SQL/engine ownership and
  replication seams; avoid new test-only accessors and implementation snapshots.
- Extend current tests for owner lifetime, moves, invalid/missing owner, header
  growth, compact-buffer reuse, in-place patching and publication state.
- Exercise destination INSERT, copy-area UPDATE, partition movement, grouped
  reads, composite/function indexes, loader queuing, rollback and replication
  group failures through their existing supported interfaces.
- Replace the direct generic-pack rejection assertion with rejection at actual
  heap-row export. Verify copied temporary images and unchanged publication on
  rejection, including checks with assertions disabled.
- Verify logical storage rejection and successful disk/expanded rows, generic
  arbitrary bytes, root metadata, no-content descriptors and legacy row support.
- Run the configured debug build, focused tests during implementation, configured
  CTest once at completion, and the established real server-loader fixture.
- Record exact local revision, commands, verdicts and limits. Historical passes
  do not establish results for new changes. Finish with Standards and Spec review
  against the pinned PR head, also inspect the whole PR diff against its baseline.

## Out of Scope

Unchanged-chain reuse, new UPDATE performance optimizations or benchmarks,
independent vacuum correctness fixes, broad feature qualification, remote replies,
thread resolution, push, CI triggering and integration merges.

## Further Notes

Pinned PR head: aecce0e1216a813771621c13112c8f27d43df22e.
Pinned baseline: fb567a629cdb390fff920542173fa36f454c74a0.
The old effective-key routing ADR is historical PR7600 scope, not an added
performance requirement for this work. Four approved tasks are recorded in the
map and separate issue files. Publication means local Markdown only.
