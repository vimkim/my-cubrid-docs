# PR #7925: standards, correctness, and simplification review

Date: 2026-10-07. Issue: [CBRD-27424](https://jira.cubrid.org/browse/CBRD-27424). PR: [CUBRID/cubrid#7925](https://github.com/CUBRID/cubrid/pull/7925). Work-tracker item: **291**.

No newly introduced correctness defect or hard standards violation was found. The strongest optional simplification is buffer ownership: use an existing owning `record_descriptor` directly while retaining the current heap attrinfo conversion, destination selection, and transaction scope. This proposal was reviewed in source; it has not been implemented or benchmarked.

## Reviewed revisions and method

| Item | Pinned value |
| --- | --- |
| Base ref | `origin/feature/oos-merge`, refreshed from `CUBRID/CUBRID` |
| Base and merge-base | [`fb567a629cdb390fff920542173fa36f454c74a0`](https://github.com/CUBRID/cubrid/commit/fb567a629cdb390fff920542173fa36f454c74a0) |
| Local and PR HEAD | [`1c660d22e4340ee707336ad08c8b4bf4b69744de`](https://github.com/vimkim/cubrid/commit/1c660d22e4340ee707336ad08c8b4bf4b69744de) |
| Head repository and branch | `vimkim/cubrid`, `CBRD-27424-oos-loaddb-sa` |
| Diff scope | Eight files; 972 insertions and 24 deletions |

The review covered the full merge-base-to-HEAD diff, surrounding implementations, and callers. Standards and requirements were reviewed independently in parallel; the coordinating reviewer assessed design alternatives and checked the supporting evidence.

```bash
git diff fb567a629cdb390fff920542173fa36f454c74a0...1c660d22e4340ee707336ad08c8b4bf4b69744de
git log fb567a629cdb390fff920542173fa36f454c74a0..1c660d22e4340ee707336ad08c8b4bf4b69744de --oneline
```

Sources were the freshly fetched JIRA description, PR body, personal CUBRID policies, applicable source and test instructions, and the complete OOS normative specification updated 2026-09-22. The generic review skill's `docs/agents/issue-tracker.md` convention is absent from the engine checkout; the configured `cubrid-jira` workflow supplied issue context instead. The OOS test subtree explicitly permits GoogleTest despite the parent test instructions' Catch2 default.

The current PR body still describes historical Python CLI tests. The pinned diff contains their GoogleTest successors; historical implementation and validation descriptions were not treated as proof of current behavior.

## 1. Standards findings

**Zero hard violations.** The added default arguments in legacy `.c` and `.h` files have the required GNU-indent guards. The changed interfaces retain `THREAD_ENTRY *thread_p` first, and the new tests use the OOS subtree's established GoogleTest framework.

**Optional finding: possible Data Clumps / Middle Man.** At [locator_sr.c:4946](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L4946), the helper exposes both `RECDES *demoted_recdes` and `LC_COPYAREA **copyarea`. Their lifetimes are coupled. Both insert and update maintain the owning pointer, record view, and manual release. The copyarea allocation at line 4975 delegates conversion to an existing record transformer even though this caller needs only an owned local record.

This is a design judgment, not a documented-standard breach. The concrete proposal and its validation requirements appear in section 3; it is one opportunity, not two independent findings.

## 2. Spec and correctness findings

**Zero confirmed defects introduced by this PR, missing functional requirements, or unjustified production scope expansion.**

The issue requires applying existing OOS policy to standalone loader and CSQL workspace writes while preserving values and object references. The helper reuses the heap attrinfo transformer with `LOB_FLAG_EXCLUDE_LOB`, retains the original workspace representation when no demotion is selected, and restores the workspace change number (CHN): [locator_sr.c:4972](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L4972).

The partition ownership and movement requirements are respected. INSERT selects the destination before conversion: [locator_sr.c:5065](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L5065), then [line 5144](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L5144). Movement forwards workspace provenance to destination insertion: [line 5488](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L5488). UPDATE returns from the movement path before its same-partition conversion block: [line 6131](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L6131).

The acceptance criteria require no orphan chains after rollback or ignored load errors. Conversion remains inside the existing force top operation, and filtered object errors abort the object's operation: [locator_sr.c:7386](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L7386), [line 7431](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L7431), and [line 7508](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L7508). Multi-update forcing completes before the outer operation attaches: [line 7554](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L7554).

The boolean-to-flags refactor preserves the existing loader, ordinary SQL, bulk logging, foreign-key, and replication call semantics. The standalone-only helper implementation leaves server behavior unchanged. The OOS+bigone rejection is explicitly intended by the issue; the transformer rejects before writing OOS chains.

### Limits and inherited concerns

- Added automated compatibility coverage uses SA mode. The issue's recorded CS compatibility checks concern older revisions. Earlier reviews explicitly record CS automation as a known, author-declined follow-up; this review does not reclassify it as a new defect.
- Successful no-logging loading remains supported. The specification does not promise rollback after a failed no-logging load or stamp uniqueness when logging is disabled.
- The existing `DB_PAGESIZE/4` threshold discrepancy relative to the normative four-record physical target is inherited from the pinned base and tracked separately by CBRD-27057.
- Uncaught throwing STL allocations in the existing attrinfo planner, including [heap_file.c:12806](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/storage/heap_file.c#L12806), remain a separate error-handling concern. That implementation is unchanged by this PR's final diff; it is not counted as a newly introduced standards or correctness finding.

## 3. Design and simplification opportunities

### Optional: remove the copyarea adapter from local conversion

The helper currently calls `locator_allocate_copy_area_by_attr_info` at [locator_sr.c:4975](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L4975). That allocator already builds a `record_descriptor`, invokes `heap_attrinfo_transform_to_disk_except_lob`, and adapts the resulting bytes into an `LC_COPYAREA`: [line 7603](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L7603).

**Proposal:** use the existing owning `record_descriptor` as the converted record's storage, with a mutable `RECDES` view for the force operation. Keep both alive until heap/index forcing finishes. This could remove the copyarea adapter and the manual release blocks at [insert cleanup](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L5370) and [update cleanup](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L6281), without introducing a new public type or another serialization policy.

Illustrative pseudocode, not a compiled patch or a complete replacement function:

```cpp
record_descriptor converted;  // declared at force-function entry
RECDES converted_view;        // both live through heap/index forcing

/* Existing attrinfo initialization and reading. */
scan = heap_attrinfo_transform_to_disk_except_lob(
    thread_p, &attr_info, nullptr, &converted);

/* Preserve existing attrinfo cleanup and error translation. */
if (scan != S_SUCCESS)
    return cubrid_error;

if (OR_RECORD_HAS_OOS(converted.get_data()))
{
    converted_view = converted.get_recdes();
    preserve_workspace_chn(source, &converted_view);
    active_record = &converted_view;
}

/* Otherwise active_record still references the original record. */
```

The benefit is less caller ownership bookkeeping and better locality for conversion. The tradeoff is allocation behavior: existing `record_descriptor` allocators have failure assumptions, so choosing an owning descriptor alone does not establish correct out-of-memory handling. Preserve the current CUBRID error contract and validate allocation failures before adopting this change. No performance improvement is claimed.

Keep the current seam in locator forcing, after actual destination selection and inside the existing force operation. Retain the original record on non-demotion, CHN preservation on demotion, and existing LOB exclusion semantics. Do not introduce a simple length-only early exit: `STORAGE FORCE_OUTLINE` can require demotion below the normal size gate.

### Why retain the current conversion approach

The earlier direct serialized-byte implementation has already been withdrawn. The [matched restoration report](https://github.com/vimkim/my-cubrid-docs/blob/0539f640f6c225ae1e38d678a55ed7eb5cfce353/cbrd-27424/CBRD-27424-workspace-oos-restoration_1c660d22e_codex.md) reports lower large-load CPU for the restored attrinfo implementation in all five measured pairs. That evidence is limited to those shared-host workloads, but it supports retaining existing conversion machinery rather than reopening the broader direct-byte rewrite in this PR.

### Validation for any implementation follow-up

Build the changed engine and run the configured OOS CTests, preserving workspace insert/update, reserved and referenced OIDs, partition ownership and movement, rollback, ignored load errors, external LOB preservation, no-demotion controls, OOS+bigone rejection, and successful no-logging loading. Check allocation failure behavior explicitly. The owning buffer must survive all heap/index consumers and be released on every return path.

If performance is used to justify the change, compare matched builds with the same fixtures, record elapsed and user/system CPU separately, and verify identical values and physical OOS placement. Simpler ownership is the proposal's immediate goal; an unmeasured speedup is not part of the recommendation.

## Verification performed for this review

`git diff --check` over the pinned range and `bash -n unit_tests/oos/scripts/benchmark_workspace_oos.sh` passed. PR and local HEAD matched the pinned revision, and the refreshed base remained unchanged when the review finished.

The [exact-HEAD restoration report](https://github.com/vimkim/my-cubrid-docs/blob/0539f640f6c225ae1e38d678a55ed7eb5cfce353/cbrd-27424/CBRD-27424-workspace-oos-restoration_1c660d22e_codex.md) records successful Debug and Release builds and **37/37 CTests**, including 13 loader/workspace cases and 21 comparison cases. Those are earlier recorded executions, not tests rerun by this review. Engine tests and benchmarks were not rerun, and the proposed ownership change has no runtime validation yet.

The review made no engine source edits or GitHub posts. The pre-existing dirty `cubrid-cci` submodule was preserved. Publication of this Markdown report and its PR summary was subsequently authorized by the user.

Review totals: **Standards 0 hard violations and 1 optional smell; Spec 0 confirmed new defects; Design 1 optional ownership simplification.**
