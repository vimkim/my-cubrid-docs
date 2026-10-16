# PR7925: use the prepared row after workspace conversion

Accepted: 2026-10-17, Asia/Seoul. Work Item 397. Related Work Item 393.
Starting engine revision: `b755678cd9a3ab465215228d5664f7f1edf24846`.

The user accepted the proposed implementation sequence after reading the plain-English HTML explanation and the [review assessment](review-comment-4257963742_b755678cd_ste.md).
Use the common prepared-row path when preparation is necessary.
Remove the late SA-only branch that discards the prepared inline row.

## Revised guarantee

Workspace conversion must preserve column values and meaningful header fields, including the workspace-assigned cache change number (CHN).
Preserve schema defaults, NULL and empty values, valid layout, OOS selection, destination ownership, external LOB behavior, and existing transaction behavior.
Preserve finalization, publication reset, and error propagation.
Keep the prepared buffer valid through all consumers.
Release temporary memory when its owner leaves scope on success or failure.

Valid encoding differences and unused padding may differ from the input bytes.
This decision does not require complete input-byte identity after preparation.
It does not claim that every eligible input differs only in padding.

This decision supersedes User Story 27 and the original-row/prompt-release clause in the earlier simplification specification.
That specification states: "Keep the input record when no value is demoted and release the unused conversion buffer promptly."
Its retained local source is `.scratch/pr7925-review-simplification/spec.md` in the main documentation checkout.
The remaining requirements in that specification still apply.
The earlier requirement explains the historical branch. It does not govern the selected response to review comment 4257963742.

## Implementation boundary

Keep the existing preparation and finalization functions.
Select the prepared record and its received owner in both SA and server builds.
Do not add a competing preparation filter or change partition selection.
PR7927 owns the related filter and destination interface.
Its observed open head is `9ba5b9b927e5c1820f2f9d7a6f7d9acfa447e773` on 2026-10-17.
Actual dependency integration and combined acceptance remain pending under WI393.

The change preserves storage thresholds, demotion policy, disk format, and the existing logged-operation contract.
Successful no-logging loading remains supported within its existing limitations.
Memory cleanup does not undo database writes.

## Required verification

1. Build and install the changed source with the selected debug configuration.
2. Preserve and execute all 21 stored-row comparisons and 13 loader/workspace cases.
3. Check CHN against the actual workspace object after its flush.
4. Check values, storage policy, defaults, finalization, errors, rollback, and buffer lifetime.
5. Execute the focused native loader partition regression.
6. Compare matched small-row and OOS loader workloads, including peak memory.
7. Review Standards and Spec against the pinned starting revision.
8. Publish scoped source changes and trigger one new full CI cycle after focused checks pass.
9. Wait for CI, report its result and merge gates, then stop for human direction.

These are required checks, not completed results.
The completed baseline [CI report](ci_analysis_report_b755678cd_run38861566581_codex.md) does not test this change.
Final verification results will identify the changed engine revision and exact testcase inputs.
