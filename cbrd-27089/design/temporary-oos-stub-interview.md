# PR7927 temporary OOS stub design interview

Status: round 1 pending. Design discussion only; no engine implementation authorized by this interview.
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

1. Self-contained access: should a pending RECDES be readable without threading an owner/context through existing readers? Recommend yes, conditionally: tagged process-local access plus an explicit lifetime owner and an enforceable transient-record boundary. Compare against slot indices with a passed context. Prove that copied/moved records retain access and persisted/corrupt records cannot trigger pointer dereferences.
2. Replacement scope: replace prepared-row use across existing PR paths, or begin with ordinary INSERT and retain the old design elsewhere? Recommend one replacement covering existing supported paths, including UPDATE movement, duplicate probes, loader and HA; reduce implementation machinery rather than supported behavior.

## Subsequent questions and proof obligations

Exact encoding and transient trust boundary depend on question 1; sequencing depends on scope. Investigate stable payload ownership across vector moves, RECDES copying, retries, LOB exactly-once effects, grouped reads, key sizing, partial insertion rollback and publication/replication. These correctness facts are the agent's work, not questions asking the user to relax safety.

Implementation requires explicit confirmation of shared design understanding under the invoked grilling skill. No build, DB experiment, push or PR modification performed.
