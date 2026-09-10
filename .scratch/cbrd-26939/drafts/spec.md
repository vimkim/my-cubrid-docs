# Durable OOS historical images and remaining PR failures

Status: draft-for-review

## Problem Statement

PR #6864 currently fails CDC extraction because retained historical log records contain references to OOS value chains that vacuum can reclaim before extraction. The reproduced DELETE workload fails with vacuum enabled, passes when vacuum is disabled, and fails again after vacuum is restored. Users need correct historical values and a surviving server while ordinary reclamation continues. The latest verified GHA snapshot also contains an independent server crash in the JDBC concurrency test bug_bts_4633; the PR goal includes resolving that failure without assuming a shared cause.

## Solution

Record durable, expanded supplemental images for OOS-backed before/after images when supplemental logging is enabled. CDC and flashback consume the supported history from retained logs after vacuum. Preserve physical recovery logging and ordinary reclamation. Reject unresolved legacy OOS history explicitly, while preserving readable non-OOS history. Required image-recording failures fail the originating write through normal rollback handling.

Existing databases adopt the format through an explicit offline, one-way in-place activation after clean shutdown and coordinated engine/reader upgrade. Persist compatibility protection before any new-format image is written. Fresh databases use the current format immediately; older engines cannot open them, including before their first OOS change. Existing inactive databases retain their compatibility level and cannot write new-format images. Operations requiring the new durable OOS history report an activation-required error until activation instead of silently generating incomplete history.

## User Stories

1. As a CDC consumer, I want a delayed INSERT image to survive later updates and deletion, so that extraction preserves the inserted value.
2. As a CDC consumer, I want an UPDATE's before and after images, so that I can reproduce the actual change after vacuum.
3. As a CDC consumer, I want a DELETE's complete before image, so that downstream removal uses the correct historical values.
4. As a flashback user, I want the same durable images, so that historical inspection does not depend on live OOS slots.
5. As a database operator, I want normal vacuum reclamation, so that consumer delays do not indefinitely retain OOS chains.
6. As a consumer using all-column conditions, I want every required historical column, so that missing values cannot masquerade as successful extraction.
7. As a consumer using key conditions, I want existing extraction semantics, so that OOS support does not change the public contract.
8. As an application writer, I want failed image construction or append to fail my write, so that a successful commit has complete required history.
9. As an application writer, I want rollback to preserve transaction semantics, so that failed publication does not expose committed partial changes.
10. As an operator with supplemental logging disabled, I want existing write behavior, so that inactive historical logging does not introduce supplemental payload overhead.
11. As a reader of legacy non-OOS history, I want existing supported extraction, so that introducing the new format does not discard usable history.
12. As a reader of unresolved legacy OOS history, I want a clear error and a surviving server, so that failure is explicit instead of silently wrong data.
13. As an operator of an existing database, I want offline in-place activation, so that I preserve current data without recreation.
14. As an operator, I want activation to persist its compatibility protection before new writes, so that a crash cannot expose new images under the old compatibility level.
15. As an operator of an inactive database, I want its old compatibility level preserved, so that an unrelated database is not implicitly upgraded.
16. As an operator creating a fresh database, I want current-format support immediately, so that supported CDC tests and applications require no second activation step.
17. As an operator, I want older engines to reject activated or current-format databases before recovery, so that they cannot misread their history.
18. As an HA operator, I want a defined coordinated reader upgrade and validation policy, so that independent log readers are included in rollout.
19. As an operator restoring a backup, I want the activation state preserved and validated, so that restoration does not weaken format protection.
20. As a consumer restarting after interruption, I want correct supported extraction across log rollover and server recovery, so that historical values remain available within retained history.
21. As a user of large or multiple OOS-backed attributes, I want byte-correct images across chunks and data/log page sizes, so that coverage is not limited to a single payload shape.
22. As a user of triggered, relocated, or partitioned row changes, I want the same history guarantees, so that alternate DML paths cannot bypass publication.
23. As a maintainer, I want measured WAL, memory, and runtime costs, so that the accepted logging trade-off is quantified.
24. As a PR reviewer, I want both remaining failure paths independently reproduced and repaired, so that passing CDC tests does not hide the JDBC crash.
25. As a maintainer, I want tests based on public observable results, so that implementation refactoring cannot invalidate the evidence.

## Implementation Decisions

- Accepted architecture is recorded in ADR-0004 in the authoritative OOS context repository; all Q1–Q9 choices are confirmed.
- Keep ordinary recovery undo/redo unchanged. Durable OOS history belongs to supplemental logging and its shared CDC/flashback record reconstruction.
- Reuse record-level OOS expansion through an owned-copy interface. The caller's recovery image and buffer ownership remain intact. Serialized OOS values include external-LOB locator bytes, not a new promise to retain external LOB content.
- Capture before images while their values remain protected and before destructive/eager cleanup. Capture after images before they can become reclaimable. Preserve transaction and trigger associations.
- Publish durable image records and their DML references through checked operations. Propagate construction, allocation, and append failures to normal write rollback; do not advertise an image LSA that was not successfully appended.
- Use a distinguishable expanded-image contract preserving existing supplemental enum values and DML metadata relationships. The exact encoding is an implementation choice validated through compatibility and malformed-image tests; do not rely on an unknown subtype being rejected by old readers.
- Decode supported images on both undo and redo paths through the shared historical record reader. Retain valid legacy non-OOS decoding. Explicitly reject unresolved legacy OOS references without reading potentially reused slots.
- Fresh database creation establishes the current format. Existing database startup supports its inactive state, with explicit clean-shutdown/offline activation. Activation preserves data, is one-way, and durably establishes protection before new image emission. Supplemental logging off does not undo activation.
- Use an enforceable existing old-engine compatibility check for activated databases, with supported inactive/current handling throughout lifecycle utilities. Reserve the actual compatibility identifier through release integration; do not make an unconditional global change that rejects ordinary inactive databases.
- Cover coordinated HA and historical-reader rollout. The engine-open check does not by itself prevent an independent old applier from reading copied logs; validation and deployment requirements must be stated accurately.
- Treat bug_bts_4633 as an independent diagnosis and repair. No cause or fix is preselected from its MVCC undo-read stack.
- Keep intermediate tickets on an integration branch until the full capability is verified. Do not publish a partial feature as a supported release merely because an early slice passes.

## Testing Decisions

Proposed public test seams for review:

1. SQL transaction outcomes plus the public CDC extraction interface: drive real writes, control consumer delay and vacuum, assert exact event identities, counts, before/after bytes, error returns, and server survival. Reuse the existing CDC test-client pattern. Fault injection targets publication failures, but assertions remain public write/transaction/extraction behavior.
2. The user-facing flashback utility: query retained historical changes and verify their values and checked failures using the same database fixtures.
3. Database lifecycle utilities: create, clean shutdown, offline activation, start, backup/restore, and an actual older engine's open attempt. Verify persistent state indirectly through supported/denied behavior and data preservation. Include upgraded reader validation and the HA rollout contract.
4. The existing JDBC concurrency testcase: reproduce the observed undo-read crash, minimize or improve its reproduction rate, assert server survival and correct behavior rather than trusting its permissive script-level OK.

Required coverage:

- Regression fixtures use fixed known VARBIT bytes, not runtime randomness or expected values recomputed with the implementation. Counts alone cannot prove correctness.
- Exercise actual reclamation before extraction; a fixed sleep alone is insufficient evidence of vacuum. Establish a reliable synchronization method and record the observed reclamation condition.
- Cover INSERT later changed/deleted, UPDATE, DELETE, all_in_cond modes, multiple attributes/chunks, and 4KB/8KB/16KB data/log layouts where supported.
- Include trigger, relocation, partition, applicable eager/non-MVCC cases, rollback and write failure paths.
- Cover compression on/off, archive rollover, delayed/restarted consumers, crash recovery, activation interruption, and backup/restore.
- Check fresh, inactive legacy, activated legacy, mixed usable non-OOS and rejected legacy OOS history. Test that rejecting legacy history cannot silently advance past missing changes.
- Measure WAL/serialization/memory costs with representative OOS workloads and supplemental logging off. No unagreed percentage or absolute performance budget is assumed.
- Re-run original cbrd_27064 and cbrd_27075, the independently repaired bug_bts_4633, appropriate builds/tests, and CI on the final engine commit. Keep exact engine/testcase identities with evidence.
- Preserve the private namespace runner's process, network, IPC, filesystem socket, install and database isolation; ordinary host CUBRID instances must remain untouched.

## Out of Scope

- Preserving OOS chains indefinitely for CDC, hybrid retention, online activation, downgrade support after activation/current-format creation, and reconstructing unresolved legacy OOS history from arbitrary reclaimed storage.
- Changing the ordinary OOS recovery representation, introducing OOS compression policy, or redesigning unrelated vacuum ownership projects.
- Extending history beyond retained archives, overriding existing schema-change limitations, or retaining external LOB payloads merely because their locator was OOS-backed.
- Assuming bug_bts_4633 is fixed by the CDC change or reducing the overall PR success objective to the CDC tests alone.

## Further Notes

Baseline engine: 2940b1cfbc3c2d4d0fac3f9244a960350debd380. Verified testcase revision: 01af62db73351ea3fdb445ccd03a19c39084d1cc. Exact GHA diagnosis snapshot: run 34186373809. Preserve evidence from that snapshot while verifying later runs independently.

The existing reduced DELETE loop is diagnostic evidence, not yet the final deterministic byte-value regression test. The independent JDBC crash is not yet locally reproduced. No engine fix is complete at specification time.

Review status: architecture confirmed; concrete test seams and ticket granularity are presented with this draft for review. Local tracker publication uses ready-for-agent after that review. External JIRA/GitHub issue publication is not part of this local drafting step.
