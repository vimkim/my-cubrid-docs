# PR #7925: simplify workspace OOS tests and record memory ownership

Status: ready-for-agent
Approved: 2026-10-07; the user accepted both proposals and assigned partition selection to CBRD-27089.
Work-tracker: 292
Related work: [CBRD-27424](https://jira.cubrid.org/browse/CBRD-27424), [PR #7925](https://github.com/CUBRID/cubrid/pull/7925)
Dependency: [CBRD-27089](https://jira.cubrid.org/browse/CBRD-27089) / [PR #7927](https://github.com/CUBRID/cubrid/pull/7927) for the production ownership interface and partition integration acceptance. Test cleanup can proceed independently.

## Problem Statement

Reviewers need to understand a focused fix: standalone object loading and CSQL
workspace writes should apply the existing OOS policy while preserving values,
object references, and transaction behavior. The original bug allowed a
5,000-byte VARBIT value to remain inside the heap record when written through
the workspace, even though ordinary SQL execution stored it in OOS. Reading the
value alone did not reveal the difference.

The current PR carries extra work that makes that fix harder to review. Its
comparison test writes two real rows, then builds a third record by manually
serializing values and calling the existing converter again. That call can
create additional OOS data, requiring separate system-operation cleanup. It is
another invocation of the converter, not a second converter implementation.
The extra reference path was useful for an earlier direct-byte implementation
that has since been withdrawn.

Production INSERT and UPDATE also track a converted record description and its
allocated buffer separately. Reviewers must follow their relationship through
conversion, heap/index processing, and manual cleanup on every exit. This work
should be simpler without changing the storage behavior that CBRD-27424 adds.

## Solution

Compare the two real stored rows produced by ordinary SQL execution and workspace
writing. Remove the third conversion and its preparation and cleanup, while
retaining independent expected results and every existing test scenario.

Keep the converted record and its temporary memory under one ownership rule.
First use any suitable ownership already supplied by the accepted CBRD-27089
implementation. If a separate workspace buffer still needs an owner, use a
small private owner that releases the existing cached copyarea automatically.
Adopt this production change only when the resulting code is easier to review.

Partition selection and the general partition/OOS ownership fix belong to
CBRD-27089. This PR consumes the destination heap supplied by that work and
verifies integration after the dependency is included.

## User Stories

1. As an engine reviewer, I want the comparison test to follow two actual database writes, so that its purpose is visible without tracing an extra reference conversion.
2. As a test maintainer, I want test-only serialization and rollback machinery removed when unnecessary, so that maintenance work stays focused on observable behavior.
3. As an engine reviewer, I want explicit expected values and OOS placement, so that a mistake shared by both write paths cannot pass through equality alone.
4. As a standalone loader user, I want eligible large values stored using the existing OOS policy, so that loading applies the same storage rules as ordinary SQL.
5. As a CSQL user, I want statements that actually use workspace writing to receive OOS conversion, so that choosing standalone execution preserves the intended storage behavior.
6. As an application developer, I want reads to return the original values, so that storage conversion does not alter application data.
7. As a schema designer, I want small, NULL, and empty values handled by the existing policy, so that this simplification does not introduce unnecessary OOS storage.
8. As a schema designer, I want FORCE_OUTLINE preserved, so that explicit storage policy remains effective.
9. As a schema designer, I want largest-first selection and PREFER_INLINE preserved, so that the existing demotion priorities remain effective.
10. As an engine maintainer, I want equal-size candidate behavior preserved, so that the refactor does not change established selection results.
11. As a test maintainer, I want all 13 parameterized size-boundary cases retained, so that encoding and offset-width transitions remain covered.
12. As a test maintainer, I want compressed strings and JSON retained in coverage, so that these value representations survive workspace conversion.
13. As an application developer, I want equal collection values accepted despite optional encoding differences, so that valid alternative collection representations do not cause false failures.
14. As an engine maintainer, I want wide variable-offset tables and many-attribute records covered, so that record layout remains valid beyond small schemas.
15. As a schema-evolution user, I want an older row to produce the correct current values and added-column default, so that removing the extra conversion does not weaken old-representation coverage.
16. As a loader user, I want values spanning multiple OOS chunks preserved, so that large payloads remain readable in full.
17. As a loader user, I want forward and backward object references preserved, so that loading related objects keeps their relationships intact.
18. As a workspace caller, I want reserved OIDs handled correctly, so that assigning an object address before its write does not bypass OOS conversion.
19. As an engine maintainer, I want temporary conversion memory valid until heap and index processing finish, so that callers never read released bytes.
20. As an engine maintainer, I want temporary conversion memory released on success and failure, so that lifetime cleanup is easy to verify.
21. As a transaction user, I want failed logged operations to undo their OOS and heap/index changes together, so that an error leaves no unreferenced new OOS data.
22. As a loader user, I want ignored duplicate-key errors to clean up the rejected object's changes and allow later objects to load, so that filtered errors preserve the existing loading contract.
23. As an application developer, I want workspace UPDATE rollback, commit, and subsequent DELETE behavior retained, so that record cleanup stays consistent through the row lifecycle.
24. As a LOB user, I want existing external BLOB/CLOB files and locator semantics preserved, so that converting other values does not copy, lose, or delete my LOB data.
25. As a loader user, I want successful no-logging loads and reads preserved, so that this review simplification does not remove supported loading behavior.
26. As an engine maintainer, I want CHN preserved during storage conversion, so that the workspace-assigned cache change number is not advanced again.
27. As an engine maintainer, I want the original workspace bytes retained when no demotion is selected, so that an unnecessary rewrite does not alter the record or header.
28. As an engine maintainer, I want cached copyarea reuse preserved, so that ownership cleanup does not replace the allocation policy without evidence.
29. As an engine maintainer, I want later foreign-key record replacements respected, so that cleanup does not restore an obsolete active record pointer.
30. As an engine maintainer, I want OOS+bigone rejection and ordinary non-OOS bigone support preserved, so that existing size policy remains consistent across writes.
31. As a SQL and client-server user, I want ordinary SQL, CS loader, and replication behavior preserved, so that the standalone cleanup stays within its intended scope.
32. As the contributor, I want partition selection fixed under CBRD-27089, so that reviewers can assess the two issues separately.
33. As an engine maintainer, I want this PR to use the accepted dependency's ownership interface where suitable, so that integration does not introduce duplicate owners or preparation paths.
34. As an engine reviewer, I want a measured assessment of any allocation or lifetime change, so that simpler code does not conceal a loader regression.
35. As the contributor, I want focused local commits and exact verification evidence, so that teammates can review the final change while unrelated work is preserved.

## Implementation Decisions

- The scope is the workspace-versus-SQL comparison test and temporary converted-record ownership in locator INSERT/UPDATE forcing. Retain all 21 comparison cases and all 13 real loader/workspace cases. Reducing line count is desirable; reducing the amount of code a reviewer must follow is the acceptance criterion.
- Keep the real SQL INSERT/commit and real workspace flush/commit. Capture their stored rows by OID through a common existing heap-read approach, copying the bytes before ending the scan cache. Add no public test-only accessors.
- Remove the preliminary manual workspace serialization, its large scratch buffer, the third attrinfo conversion, and the system operation used solely to undo that conversion's OOS writes. Fixture cleanup still owns ordinary test transactions and database objects.
- Compare logical values and per-attribute OOS selection. Keep explicit fixture expectations for important storage-policy outcomes rather than deriving all expectations from another invocation of the production converter. Preserve meaningful offset-width and record-body-size checks, accounting for legitimate committed MVCC header differences.
- Compare decoded collection values where optional domain information can legitimately change encoding. For the schema-evolution case, explicitly assert the retained 5,000-byte value, the added column's default, and expected OOS storage. Do not use the old stored row's raw layout as the expected current representation or drop this scenario.
- Wait for CBRD-27089's accepted write/ownership interface before implementing the production ownership cleanup. Prefer an existing owner that already controls the workspace conversion buffer. If it does not cover that lifetime, introduce one private, non-copyable owner holding the record description and cached copyarea, with non-throwing automatic memory cleanup.
- A separate private owner, if needed, uses the current copyarea allocation and conversion approach. Preserve allocator error propagation and buffer reuse. Do not switch to the generic owning record descriptor merely to reduce caller declarations. Review the relative release order of independent scratch buffers and record any effect on cache reuse.
- Keep the active record pointer separate from memory ownership. Redirect it only after successful conversion; never restore it from a destructor, because foreign-key processing can legitimately select a different record later. Place owner initialization so existing error jumps remain valid, and protect added C++ syntax from the legacy formatter where required.
- Keep the input record when no value is demoted and release the unused conversion buffer promptly. Preserve CHN, existing external LOB handling, metadata exclusions, and already-converted-record behavior. Excluding another copy of an external LOB file must not change the accepted eligibility of its serialized locator bytes for OOS.
- Temporary memory cleanup and database rollback remain separate responsibilities. An owner releases memory only. OOS creation or finalization and the following heap/index changes remain within the existing transaction/system-operation scope, including filtered-error handling.
- Preserve the accepted force flags and workspace-origin propagation. Carrying that origin through an existing partition-move path enables OOS at destination insertion; it does not change how the destination is chosen.
- CBRD-27089 owns partition selection and general destination-heap/OOS ownership correctness. Integrate its accepted implementation into the shared integration branch before final partition acceptance, then adapt this PR to its interface and verify the combined revision. Do not copy its fix into this PR or repair a partition-selection failure here.
- The test cleanup is independent of that prerequisite. Keep it reviewable separately from production ownership changes. If the prerequisite already removes the ownership problem, record that outcome and avoid adding a redundant owner. Retain the current production arrangement if an additional owner makes the resulting code harder to review.
- Change no schema, SQL syntax, external protocol, persisted OOS reference format, storage threshold, or demotion policy. Existing supported successful no-logging behavior remains; this work adds no failure-recovery guarantee for unlogged writes.

## Testing Decisions

- Use the testing interfaces already approved in the conversation: real SQL and workspace writes followed by inspection of the stored result, plus real standalone loader/CSQL execution. These exercise the force path through its existing callers. No new production testing interface is required.
- Good tests assert stored values, expected OOS-backed attributes, relevant layout properties, and observable cleanup after failure. Do not test owner member names, destructor call counts, private helper structure, or copied transformer logic. A comparison of two paths sharing a converter is useful but cannot replace independent expected outcomes.
- Use the existing workspace comparison fixtures as prior art. Preserve the eight named scenarios and 13 size-boundary instances: small/NULL/empty values, demotion priorities, equal-size candidates, offset-width changes, compressed strings/JSON, collections, wide layouts, and old disk representations.
- Preserve all 13 loader/workspace scenarios as prior art for full-path behavior: real loading, reserved OIDs, object references, workspace writes, rollback, ignored errors, LOB preservation, storage policy, multi-chunk values, bigone behavior, and successful no-logging loading. Retain their partition scenarios as integration checks with CBRD-27089.
- For small values and no demotion, assert the expected absence of OOS and intact input values. For forced and large-value cases, assert actual OOS storage and the required selected attributes. For layout checks, compare only quantities with a defined expectation for those fixtures; do not require byte identity where valid encodings differ.
- For schema evolution, inspect expected values and storage after the real workspace write. Preserve the original value and the new default even though the source SQL row used an older representation.
- Exercise successful and failing INSERT/UPDATE through existing callers. Preserve unique-error rollback and ignored-error continuation checks, including the absence of leftover OOS data under the existing logged-operation contract. Review all exits for memory lifetime and cleanup; use focused memory checking if the production ownership change warrants it.
- Confirm existing external LOB filenames/content and CHN behavior through available checks and source review. Keep the established successful no-logging test without treating it as evidence for crash recovery or rollback of failed unlogged writes.
- Run focused existing tests while making changes. After the final source revision, build with the configured project workflow and run the configured OOS CTests, including the real utility fixture. Record the executed case counts and results; planned preservation of 21 and 13 cases is not a claim that they have already passed after the refactor.
- After CBRD-27089 is included, rerun partition integration cases against the combined revision and record both changes' source identities. Attribute any routing failure to its owning issue rather than expanding this PR's implementation scope.
- If production allocation or release behavior changes, compare proportionate small-row and OOS loader measurements under the same configuration. Investigate a reproducible regression beyond measurement noise. No runtime improvement is promised and no broad benchmark campaign is required.
- Complete Standards and Spec review of the new changes against the pinned starting revision, and inspect the resulting whole-PR diff against its integration baseline. Record exact revisions, commands, verdicts, and any limitation before making focused local commits.

## Out of Scope

- Partition-selection algorithms, general destination-heap/OOS ownership repairs, and the implementation of CBRD-27089. This specification records the dependency and its integration checks.
- A new serialization implementation, changes to OOS eligibility or selection policy, threshold tuning, new record types, shared record-descriptor layout changes, or a new disk/protocol format.
- Broad allocator repairs, replacing the copyarea cache, unrelated force-interface redesign, and changes to the previously accepted force flags.
- New UPDATE chain-reuse, vacuum, reclamation, recovery, or replication features. Existing behavior is preserved within this PR's scope.
- Repair of the separately identified fresh-workspace-LOB INSERT defect, or expansion into a full LOB feature test campaign.
- New guarantees for failure recovery or identity uniqueness in no-logging operation, and broad feature qualification or performance optimization.
- Remote publication, pushing, CI triggering, external comments, JIRA description changes, and integration merges. Those actions remain separate from preparing this specification and implementing local changes.

## Further Notes

The user approved both simplifications after the report was rewritten with
background, a three-record example, and a distinction between freeing temporary
memory and rolling back database pages. The subsequent partition instruction
takes precedence over any earlier wording that implied this PR should fix
partition selection.

The source snapshot for this specification is PR #7925 at
`1c660d22e4340ee707336ad08c8b4bf4b69744de`, compared with integration baseline
`fb567a629cdb390fff920542173fa36f454c74a0`. The head repository is `vimkim/cubrid`,
the branch is `CBRD-27424-oos-loaddb-sa`, and the target is `feature/oos-merge`.
PR #7927 was observed open at `6b53181d31d6d6d2615b18b4f914623bb017d7c4`; that
observation is not an immutable prerequisite revision or proof of integration.
Verify the accepted dependency interface when implementation begins.

The original CBRD-27424 requirement and the OOS normative specification remain
authoritative for preserved behavior. The accepted LOB-locator decision keeps
locator bytes OOS-eligible while external LOB storage retains its own lifecycle.
The historical PR #7600 routing ADR does not add a performance gate to this work.

Publication here means a persistent Markdown specification in the configured
local issue tracker, labeled `ready-for-agent`. No engine source changes or new
runtime test results are produced by this specification step. The next workflow
step is `to-tickets`, recording the independent test task and the production
ownership dependency explicitly.
