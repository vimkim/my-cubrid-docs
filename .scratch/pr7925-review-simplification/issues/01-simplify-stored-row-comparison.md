# 01: Simplify SQL/workspace comparison tests

**What to build:** A comparison test that writes the same values through real SQL and workspace operations, inspects the two stored rows, and proves the expected values and OOS placement without building a third record through an extra converter invocation. Reviewers should be able to follow the two real writes and their required results directly.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] Keep the real SQL INSERT/commit and workspace flush/commit, and capture both stored rows by OID. Copy captured bytes before ending the heap scan cache; introduce no production test-only interface.
- [x] Remove the preliminary manual workspace serialization, its large scratch buffer, the third attrinfo conversion, and the system operation used only to clean up that conversion's OOS data. Retain ordinary fixture transaction/database cleanup.
- [x] Preserve all 21 comparison cases: the eight named scenarios and 13 size-boundary instances. Each retains its intended value, storage-policy, encoding, or layout assertion rather than merely retaining its test name.
- [x] Assert explicit expected values and important per-attribute OOS selections in addition to comparing the two paths, so a shared converter mistake cannot automatically pass through equality.
- [x] Preserve small/NULL/empty-value behavior, FORCE_OUTLINE, largest-first selection, PREFER_INLINE, equal-size candidate behavior, compressed strings/JSON, wide layouts, and the encoding/offset boundaries.
- [x] Compare decoded collections when optional domain information legitimately changes their encoding. Retain meaningful offset-width and record-body-size checks while accounting for committed MVCC header differences.
- [x] Preserve the old-representation scenario by explicitly checking the original 5,000-byte value, the added column's default, and actual OOS storage after the real workspace write. Do not compare its old raw layout as the expected current format.
- [x] Retain all 13 real loader/workspace scenarios. Partition cases remain integration checks with CBRD-27089; this task does not change partition selection or implement its ownership fix.
- [x] Build and run the focused comparison tests, then the configured OOS CTests including the real utility fixture at the final revision. Record exact revisions, executed case counts, commands, verdicts, and any prerequisite-related limitation rather than hiding or weakening a failing case.
- [x] Review the new diff against Standards and the approved specification, inspect the resulting whole-PR diff, and make a focused local commit that preserves unrelated changes. Keep production memory ownership and allocation policy unchanged in this task.

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

## Comments

2026-10-07: Claimed by fresh clean-context agent `/root/ticket01` under the
[orchestration record](../orchestration.md). Branch `task/pr7925-01-stored-rows`
in `/home/vimkim/gh/cb/pr7925-01-stored-rows`, based on private integration
`review/pr7925-simplification` at `1c660d22e4340ee707336ad08c8b4bf4b69744de`.


2026-10-07: Implemented and independently reviewed at final commit
`625b193745959d0ab047f26f4354e9aacb48160d`. The Standards review's small
expectation-grouping suggestion was addressed by the same ticket agent.
Both final review axes have zero findings. Actual final runtime receipts
resolve the reviews' then-pending runtime observation.

## Answer

The test now captures the two real committed rows by OID and compares their
stored results. The extra manual serialization, third conversion and its
exclusive rollback machinery are removed. Explicit value, per-attribute OOS,
encoding, offset and old/current representation expectations remain. The
production delta from the ticket base is empty; all 13 real utility/workspace
cases remain unchanged.

The two scoped commits are `ba308c529a65d25f64897f7733ff167e2f6c1745` and
`625b193745959d0ab047f26f4354e9aacb48160d`. They were inspected, rebased onto
the private integration tip (no-op) and fast-forwarded into
`review/pr7925-simplification` in
`/home/vimkim/gh/cb/pr7925-simplification-integration`. Both engine trees are
clean. Existing PR, shared and default branches were preserved.

At final commit, debug_gcc build/install and formatting passed. The agent's
focused run passed 4/4 CTests with 21 comparison and 13 loader/workspace cases;
its full OOS selection passed 37/37 CTests and 336/336 GoogleTests, with zero
failures, skips or disabled cases. The coordinator independently rebuilt and
passed 4/4 focused CTests with the same 21+13 executed cases in the private
integration worktree. Requested case identities match the baseline.

- [Acceptance mapping, exact commands and failed iterations](../evidence/ticket01/report.md)
- [Final agent verification](../evidence/ticket01/verification-final.json)
- [Independent receipt/source verification](../evidence/coordinator-verification.json)
- [Private integration verification](../evidence/integration/verification.json)
- [Final Standards review](../evidence/review-final/standards.md)
- [Final Spec review](../evidence/review-final/spec.md)

The dependency is not integrated. These partition passes concern the current
PR implementation and do not establish final combined-branch acceptance.
Ticket 02 and the parent specification remain unfinished.

Cleanup is blocked by the recorded process ownership uncertainty under the
host database-lifetime policy. The ticket worktree/branch, selected install,
TMP and allocation are preserved; [inventory](../evidence/ticket01/cleanup-inventory.json)
and saved workenv files make the remaining state reviewable. No process or
unrelated database was stopped or removed.
