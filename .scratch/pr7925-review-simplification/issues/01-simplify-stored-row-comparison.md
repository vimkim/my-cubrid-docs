# 01: Simplify SQL/workspace comparison tests

**What to build:** A comparison test that writes the same values through real SQL and workspace operations, inspects the two stored rows, and proves the expected values and OOS placement without building a third record through an extra converter invocation. Reviewers should be able to follow the two real writes and their required results directly.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Keep the real SQL INSERT/commit and workspace flush/commit, and capture both stored rows by OID. Copy captured bytes before ending the heap scan cache; introduce no production test-only interface.
- [ ] Remove the preliminary manual workspace serialization, its large scratch buffer, the third attrinfo conversion, and the system operation used only to clean up that conversion's OOS data. Retain ordinary fixture transaction/database cleanup.
- [ ] Preserve all 21 comparison cases: the eight named scenarios and 13 size-boundary instances. Each retains its intended value, storage-policy, encoding, or layout assertion rather than merely retaining its test name.
- [ ] Assert explicit expected values and important per-attribute OOS selections in addition to comparing the two paths, so a shared converter mistake cannot automatically pass through equality.
- [ ] Preserve small/NULL/empty-value behavior, FORCE_OUTLINE, largest-first selection, PREFER_INLINE, equal-size candidate behavior, compressed strings/JSON, wide layouts, and the encoding/offset boundaries.
- [ ] Compare decoded collections when optional domain information legitimately changes their encoding. Retain meaningful offset-width and record-body-size checks while accounting for committed MVCC header differences.
- [ ] Preserve the old-representation scenario by explicitly checking the original 5,000-byte value, the added column's default, and actual OOS storage after the real workspace write. Do not compare its old raw layout as the expected current format.
- [ ] Retain all 13 real loader/workspace scenarios. Partition cases remain integration checks with CBRD-27089; this task does not change partition selection or implement its ownership fix.
- [ ] Build and run the focused comparison tests, then the configured OOS CTests including the real utility fixture at the final revision. Record exact revisions, executed case counts, commands, verdicts, and any prerequisite-related limitation rather than hiding or weakening a failing case.
- [ ] Review the new diff against Standards and the approved specification, inspect the resulting whole-PR diff, and make a focused local commit that preserves unrelated changes. Keep production memory ownership and allocation policy unchanged in this task.

## Context

The [approved specification](../spec.md) is the complete behavior contract.
The user approved this task and its lack of blockers on 2026-10-07.
The starting PR #7925 revision is `1c660d22e4340ee707336ad08c8b4bf4b69744de`,
with integration baseline `fb567a629cdb390fff920542173fa36f454c74a0`.
Verify current source state before implementing and preserve unrelated work.

The extra reference conversion was retained from a withdrawn direct-byte
implementation. It calls the existing converter again; it does not implement
another converter. The common stored-row capture is part of this task and needs
no separate prefactoring ticket. This task can be verified using the current
production implementation and does not require ticket 02.

Local source edits and verification are the deliverable. Push, CI triggering,
remote publication, and integration merges remain separate actions.
