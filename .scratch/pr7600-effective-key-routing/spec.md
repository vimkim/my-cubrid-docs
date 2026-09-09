# PR 7600: effective-key routing without a full inline row probe

Status: ready-for-agent

Execution authorization: specification only. Engine edits, test execution, instrumentation, benchmarks, commits, and pushes require a subsequent user request. This status means ready for implementation planning, not permission to execute it.

Baseline: CUBRID source revision `b871ea386d2c5419b7abae07dda58b9b7f36377a` (PR #7600 head studied in this conversation). Test seams confirmed by the user on 2026-09-08.

## Problem Statement

Partitioned writes must place externalized attribute values in the OOS file associated with the heap that stores the row. The existing solution builds a complete inline row to determine the destination, then rebuilds it with OOS references when externalization is required. For rows with large unrelated attributes, this creates temporary serialization, allocation, and copying work that may be unnecessary for a routing decision based on one partition-key column.

The current solution is the correctness baseline, not a demonstrated performance defect. Non-OOS rows retain their first record image rather than undergoing two full transformations. The user wants a source-grounded design improvement whose correctness and useful resource savings can be demonstrated without broadly restructuring stateful row preparation.

## Solution

Determine the destination from an owned temporary effective partition-key value, then perform one full-row transformation using that destination for OOS writes. Preserve existing per-heap ownership and final partition validation, representation handling, locking, scan-cache selection, and UPDATE movement.

The effective key must represent the same value that the stored-record decoder would expose, including defaults, old-record values, column-domain normalization, and pending increments. It is not simply the caller's current cached value. Use the existing partition-expression evaluation and matching behavior rather than introduce a second interpretation of partition rules.

Accept the replacement only after complete coverage and correctness are established and measurements demonstrate useful temporary allocation/copying savings. Flat runtime is acceptable; reproducible control-workload slowdowns require a new user decision. If preserving key semantics requires excessive duplication or special cases, stop and reopen the design rather than silently narrow coverage or expand the refactor.

## User Stories

1. As a database user, I want partitioned inserts to choose the same destination as before, so that optimizing storage preparation does not change my data distribution.
2. As a database user, I want OOS values to belong to the row's destination heap, so that partition lifecycle operations cannot remove another partition's live values.
3. As a database user, I want range-boundary keys routed correctly, so that equality at a boundary never places a row in the wrong partition.
4. As a database user, I want list and hash partitions supported, so that the optimization is not restricted to range partitioning.
5. As a database user, I want partition expressions evaluated with existing semantics, so that routing uses the expression result rather than incorrectly comparing the raw column.
6. As a database user, I want every legal partition-key type supported on the targeted write path, so that some types do not silently retain the expensive probe.
7. As a database user, I want NULL routing preserved, so that nullable keys retain their existing placement or rejection behavior.
8. As a database user, I want explicit-partition writes validated, so that an early selected destination cannot bypass the partition I explicitly named.
9. As a database user, I want missing-partition errors preserved, so that invalid keys are rejected rather than redirected.
10. As a database user, I want omitted INSERT values to use the correct defaults, so that early routing agrees with the row ultimately stored.
11. As a database user, I want dynamic defaults and generated values consumed without duplicate evaluation, so that routing and storage see the same value.
12. As a database user, I want assigned values coerced consistently with their column domains, so that early routing cannot disagree with stored-value routing.
13. As a database user, I want CHAR padding and string collation behavior preserved, so that textual partition keys retain their meaning.
14. As a database user, I want temporal key variants supported consistently, so that date, time, and timezone-related domains do not change routing.
15. As a database user, I want unchanged UPDATE keys read from the appropriate old record, so that updating a payload does not change partition placement accidentally.
16. As a database user, I want old representations and absent historical attributes handled, so that schema evolution does not break routing.
17. As a database user, I want key-changing updates to move rows correctly, so that new OOS values follow the destination heap.
18. As a database user, I want ordinary arithmetic assignments preserved, so that their effective values determine routing.
19. As a database user, I want dedicated INCR and DECR operations applied once to the real row, so that routing preparation cannot double or suppress a mutation.
20. As a database user, I want integer increment boundary behavior preserved, so that overflow and underflow cases remain compatible with the existing operation.
21. As a database user, I want LOB copies and deletions to retain their lifecycle, so that removing a routing probe does not duplicate or lose external objects.
22. As a database user, I want small FORCE_OUTLINE values stored under the correct heap, so that ownership correctness does not depend on exceeding the ordinary size threshold.
23. As a database user, I want ordinary large OOS values and multiple externalized attributes supported, so that the optimization covers realistic payloads.
24. As a database user, I want unsupported OOS-plus-big-record combinations rejected before OOS insertion, so that failed writes do not publish invalid storage.
25. As a database user, I want rollback to preserve prior values and ownership, so that an unsuccessful write cannot leave durable partial effects.
26. As a concurrent reader, I want old row versions to remain readable, so that an updated or moved row does not invalidate my snapshot.
27. As a database operator, I want recovery and vacuum behavior preserved, so that storage preparation changes do not alter reclamation safety.
28. As a database user, I want existing nonpartitioned behavior preserved, so that a partition-specific optimization does not regress ordinary tables.
29. As a database user, I want REPLACE and duplicate-key UPDATE behavior preserved, so that unrelated duplicate-probe protections remain intact.
30. As a maintainer, I want reused routing contexts to contain no dangling pointers or previous-row values, so that bulk writes are as correct as single-row writes.
31. As a maintainer, I want resource ownership explicit on failure paths, so that temporary values, buffers, and publication state are cleaned correctly.
32. As a database user, I want single-failure errors preserved, so that the optimization does not obscure the cause of an invalid statement.
33. As a maintainer, I want independently invalid statements allowed to report a different first error, so that irrelevant work is not retained solely to preserve error precedence.
34. As a database operator, I want measurable reductions in temporary allocation and copying, so that the added design complexity produces a useful benefit.
35. As a database operator, I want small-row and nonpartitioned controls measured separately, so that an aggregate performance result cannot hide a regression.
36. As a maintainer, I want changes tested through behavior-level interfaces, so that tests survive internal refactoring.
37. As a design owner, I want failed equivalence or benefit gates brought back for a decision, so that implementation does not silently change the agreed scope.

## Implementation Decisions

1. **Scope and ownership.** Replace the full inline routing probe on the partitioned INSERT/UPDATE attribute-force path under study. Keep at most one OOS file per heap and direct new OOS values to the selected destination heap. Do not introduce shared partition OOS storage, new on-disk formats, or new SQL syntax.
2. **Effective-key interface.** The heap attribute module supplies an owned temporary key value without changing the original assignment state. Its contract includes slot state, old/default representation, column-domain semantics, and pending mutations. It must not delete/copy LOB objects, allocate OOS chains, or reset OOS publication state.
3. **Stored-value equivalence.** The temporary key must equal the value the existing serialized-record read path would present to partition-expression evaluation. Reuse existing type conversion and codec behavior. A scalar-only write/read round trip is permitted where necessary; serializing the complete row or manufacturing a partially populated full-row layout is not the intended replacement.
4. **Coverage.** Cover all legal partition column types and expression results at the baseline: supported integer widths, date/time and timestamp/datetime variants, and CHAR/VARCHAR, including domain and collation behavior. Cover range, list, and hash selection. No silent type-dependent probe fallback. If complete equivalence cannot be established, stop and reopen design.
5. **Defaults and old values.** Consume already evaluated assignments, defaults, and generated values where present. Resolve uninitialized keys using the appropriate old representation or representation default. Do not reevaluate dynamic defaults or fetch an unrelated version instead of the old record supplied by the existing write path.
6. **Pending increments.** Apply the existing dedicated integer increment operation to the temporary key when required, leaving the original pending operation intact. The real row transformation applies it once, including across buffer retries. Preserve dedicated INCR/DECR behavior rather than substituting generic arithmetic. Ordinary arithmetic UPDATE expressions remain separately covered.
7. **Shared partition logic.** Record-based and effective-key callers share partition-expression evaluation and matching semantics. Preserve NULL handling, exactly-one-match requirements, explicit-partition checks, root discovery, superclass reporting, and context ownership. Temporary expression bindings must be cleared or restored before their referenced values are released.
8. **First-pass destination override.** Provide destination-aware normal first-pass transformation semantics. The existing destination-aware second-pass contract assumes increments were already applied and must not be reused unchanged after temporary-key-only routing. Keep source cache identity separate from destination OOS identity.
9. **One full-row transformation.** Invoke normal full-row transformation once after early selection on the optimized path. OOS payload serialization and buffer-growth retries remain necessary and are not represented as eliminated. The final copy area and attribute cache remain part of the write path.
10. **LOB locality.** Leave global value preparation and LOB deletion/copying in the existing real transformation lifecycle. Preserve LOB locator state, metadata ownership, demotion eligibility, and retry behavior. Do not retarget the source cache's class identity merely to choose the destination OOS file.
11. **Final force behavior.** Retain downstream record-based routing initially, including the existing representation-ID patch and surrounding lock, scan-cache, index, and cross-partition movement behavior. Do not bypass it by marking the class nonpartitioned. Early and final destinations must agree; disagreement is a correctness failure requiring cleanup and investigation, not a reason to redirect already-written chains.
12. **Resource and publication ownership.** Preserve existing buffer, payload, context, and transaction cleanup responsibilities. Start/reset OOS publication state at the real OOS preparation stage before fallible payload preparation. Freeing a temporary buffer does not undo persistent inserts. Preserve the existing logged insertion and transactional failure handling rather than add ad hoc chain deletion.
13. **Error policy.** Preserve successful results, single-failure errors, and transactional correctness. The first reported error may differ when multiple independent errors coexist. Early invalid routing may therefore reject before unrelated preparation side effects. Preserve the pre-insertion OOS-plus-big-record rejection gate.
14. **Unchanged paths.** Keep nonpartitioned transformation and REPLACE/duplicate-key probe behavior intact. Those probes have independent index/duplicate-detection purposes; this change does not claim their removal. Do not extend the optimization to unrelated write entry points without a separate contract analysis and decision.
15. **Acceptance and reopening.** Complete key coverage, semantic equivalence, cleanup, and useful measured savings are requirements, not optional follow-ups. Excessive semantic duplication, incomplete coverage, routing disagreement, insufficient benefit, or repeatable regression reopens the design. A broad preparation split or elimination of final routing is not an automatic fallback implementation.

## Testing Decisions

1. **Confirmed primary seam: existing SQL execution and OOS inspection.** Exercise the heap attribute, partition, locator, and OOS modules together through stored results, partition placement, owner-file observations, statement errors, and transaction behavior. Prefer observable outcomes to private helper ordering or implementation-specific call-count assertions.
2. **Prior art.** Extend the existing partitioned FORCE_OUTLINE ownership regression, SQL transaction/rollback tests, storage-policy tests, and server OOS publication-failure tests. The standalone SQL fixture alone does not establish server MVCC or vacuum safety.
3. **Supporting existing seam: OOS failure injection.** Reuse preparation, class lookup, file lookup, and partial-publication failure mechanisms. Assert correct publication state and recovery of subsequent writes. Supplement with routing failure and final heap/index failure coverage through existing appropriate mechanisms.
4. **One focused new seam if needed: effective-key routing.** Test the behavior-level key/routing result against the existing record-based reference for legal types, expressions, defaults, old representations, coercions, and pending increments. Check destination identity, normalized value, and unchanged original assignment state. Do not expose multiple low-level helpers solely for testing.
5. **Differential oracle safety.** The existing inline probe is stateful. Run candidate and reference on independently owned equivalent inputs and isolated fixture state; do not run both against the same mutable assignment cache and accidentally mask double application. Comparing results must not create unrelated OOS or LOB effects. Pin the baseline and preserve the original reference behavior during characterization.
6. **Routing matrix.** Include range boundaries, list/hash routes, expression keys, NULL, absent partitions, direct-partition validation, integer widths, temporal variants, CHAR padding, VARCHAR/collation behavior, and an OOS-backed string key. Reuse a routing context across alternating rows and destinations to expose stale bindings.
7. **Preparation matrix.** Include omitted INSERT values, already evaluated dynamic defaults/generated values, unchanged UPDATE keys, old representations, ordinary arithmetic assignments, dedicated INCR/DECR boundary crossings and overflow-to-zero semantics, and retries. Both routing and the final stored row must reflect the same effective key.
8. **Storage and lifecycle matrix.** Include small FORCE_OUTLINE payloads, ordinary OOS candidates, several externalized attributes, large uncompressed payloads, inline and demoted LOB locators, unchanged LOBs, written LOBs, same-partition updates, moved updates, OOS-plus-big-record rejection, and rollback. Verify both logical values and correct owner files; row equality alone is insufficient.
9. **Server validation.** Add appropriate server-mode coverage for concurrent old-version readers, moved-update rollback, and OOS lifecycle interactions with vacuum/recovery. Preserve existing behavior rather than claiming to repair unrelated baseline defects. Baseline failures must be attributed and presented, not silently treated as passing coverage or waived requirements.
10. **Failure expectations.** Test each single-failure category and selected multiply-invalid statements. Multi-error tests require an appropriate failure and cleanup, not the old exact first error. Assert no durable partial effects, no new OOS writes from key-only routing, valid cached-value lifetimes, and correct subsequent operations after failure.
11. **Measurement is separate from correctness testing.** Record full-row transformation/retry counts, temporary allocation bytes and peak memory, copied bytes, OOS payload serialization bytes, OOS insertion counts, routing invocations, CPU time, and elapsed time as diagnostic measurements. Do not couple functional tests to a private helper's exact invocation count.
12. **Paired benchmark controls.** Compare the pinned baseline and candidate with equivalent compiler/build configuration, database settings, data, and workload. Include large uncompressed non-key payloads, small forced-outline values, small non-OOS rows, unchanged-key and moved updates, and nonpartitioned controls, with integer and string/expression keys. Keep instrumentation equivalent, record warmup/repetition methodology, estimate noise, and report per-workload distributions and repeatable differences rather than only an aggregate average.
13. **Benefit gate.** Demonstrate elimination of the temporary whole inline row on the claimed optimized path and measurable temporary allocation/copying savings for OOS-producing writes. Flat runtime is acceptable. Reproducible slowdown beyond measured noise on small non-OOS or nonpartitioned controls requires renewed user approval; other repeatable workload regressions must also be disclosed and resolved as an explicit trade-off. Inconclusive measurements do not prove the gate passed.
14. **Coverage versus execution.** This specification defines future tests and measurements; none were run to validate the candidate during research or specification. Execution requires separate approval. After approval, characterize the baseline and implement behavior/test slices incrementally, maintaining the agreed coverage instead of replacing difficult requirements with easy passing tests.

## Out of Scope

- Shared OOS storage across partition heaps; new file formats, OOS reference layouts, or ownership rules.
- A global preparation/serialization split, relocation of LOB lifecycle operations, or broad force-interface redesign.
- Removing downstream partition selection in the initial implementation.
- Removing all REPLACE/duplicate-key probes, optimizing every write entry point, or changing nonpartitioned behavior.
- Changing demotion thresholds, storage policies, compression, OOS-chain reuse, vacuum algorithms, or replication design.
- Silently limiting legal-key support or shipping a partial type-dependent fast path under a complete-coverage claim.
- Repairing unrelated baseline defects as incidental scope expansion.
- Engine edits, experiments, test execution, commits, pushes, or PR publication merely because this local tracker item is marked ready-for-agent.

## Further Notes

- Accepted design: [ADR 0001](../../docs/adr/0001-pr7600-effective-key-routing.md).
- User decisions and proof obligations: [completed interview](../../cbrd-27089/design/design-interview.md).
- Pinned source evidence and test prior art: [research report](../../cbrd-27089/design/probe-rebuild-research-b871ea386-codex.md).
- Existing probe behavior remains the baseline, not an assumed performance bug. Keeping downstream selection can add routing work for small non-OOS rows; the control-workload gate deliberately tests this trade-off.
- The specification requires equivalent effective-key behavior, not a particular unproven codec implementation. A key-only codec round trip is a conservative candidate to test; if it cannot satisfy the full contract without excessive duplication, return to the design owner.
- Readiness means the agreed scope, interfaces, invariants, acceptance gates, and stop conditions are specified. Equivalence, cleanup, and performance remain proof obligations for implementation and verification, not established results.
- Publication is this file in the repository's configured local Markdown tracker. No GitHub/JIRA issue creation, git commit, or push is implied.
- Next workflow step: implementation planning or ticket decomposition from this spec, when requested. No implementation tickets were created by this publication. Test-first implementation and experiments require the user's subsequent approval.
