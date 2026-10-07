# PR7927: simplify review without changing the approved OOS design

Status: resolved
Approved: 2026-10-07, user selected "all three" architecture candidates.
Tracker: 293
Source starting point: `6b53181d31d6d6d2615b18b4f914623bb017d7c4`
Integration baseline: `fb567a629cdb390fff920542173fa36f454c74a0`

## Problem Statement

Reviewers must coordinate parallel finalizer collections and duplicated locator
handoffs, while the SHOW diagnostics module contains most write verification.

## Solution

Concentrate finalization facts and post-routing ordering in their existing
modules, and organize verification at the existing SQL/engine test seam.
The [approved design](../../cbrd-27089/design/no-record-type-design.md) remains
binding; this is a refinement of its implementation, not a new design.

## User Stories

1. As a reviewer, I want each pending value's payload, result and current patch location together, so that collection order is explicit.
2. As a maintainer, I want batch result addresses stable before insertion, so that vector growth cannot invalidate them.
3. As a reader, I want one bounds-checked stub decode, so that memory and disk adapters retain one validation contract.
4. As a writer, I want destination selection to precede adaptation and finalization, so that chains belong to the correct heap.
5. As a reviewer, I want INSERT and UPDATE to share their completed-row handoff, so that ordering knowledge has locality.
6. As a maintainer, I want owner lifetime visible in the existing callers, so that helpers cannot retain borrowed context.
7. As a tester, I want write verification in a focused module, so that SHOW diagnostics remain independently reviewable.
8. As a contributor, I want every assertion and test identity traceable after relocation, so that review simplification does not lose coverage.
9. As a contributor, I want historical verification preserved and current results dated, so that evidence remains attributable.

## Implementation Decisions

- Keep the public OOS finalization and value-reference interfaces and the small
  memory/disk Resolve interface; introduce no generic visitor or new descriptor.
- Keep each current-view patch location, retained payload span and insertion
  result together. Build the contiguous batch adapter after collecting values;
  insert the batch before patching any stub. Retain failure/publication handling.
- Centralize locator adaptation, owner selection and finalization after routing.
  Keep local received owners in INSERT/UPDATE; moving UPDATE forwards to INSERT.
- Preserve no new record type, unchanged shared RECDES layout, compact reuse,
  in-place finalization, validated indices, owner lifetime and storage/export guards.
- Preserve legacy eager serialization, fresh-chain UPDATE, replication grouping,
  LOB behavior and loader finalization before heap-page latching.
- Relocate write tests through the existing real SQL/database adapter. Share only
  fixture/statistics helpers needed by both modules; keep diagnostic-only helpers
  local. Do not add mocks or test-only engine interfaces.
- Keep failed-size-probe error behavior explicit; redundant checks are removable
  only when the same caller error contract survives.

## Testing Decisions

Use the already-approved SQL/engine ownership, storage/export and replication
interfaces as the test surface. Existing tests supply the refactoring oracle;
no tests that mirror the new bookkeeping are required. Compile/install changes,
run focused cases, prove relocation identity/body mapping, run the configured
suite once at completion, and finish with separate Standards and Spec reviews.
The starting SHOW executable has 39 fixture cases plus one generic packing case:
keep four diagnostic cases and relocate all 36 remaining cases without losing
assertions. Preserve serial OOS_DB fixture execution and workload timeouts.

## Out of Scope

New ownership models, shared descriptor fields, pointer registries, unchanged-chain
reuse, UPDATE optimizations, broader latch/serialization redesign, benchmarks,
remote replies, push, CI and integration merges.

## Further Notes

The user selected all three candidates and their existing test seams from the
architecture report. No material design frontier remains. Local task files are
publication; no external issue or reply is posted. Historical task281/284/289
outcomes remain complete. Implementation refinements are tracked separately as 293.
All three tasks are implemented at `4be72fc20`; see the
[verification and independent review](../../cbrd-27089/design/review-simplification.md).
