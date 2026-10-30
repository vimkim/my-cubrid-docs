# CBRD-27841 publication proposal

This records reviewable material and proposed operations. It does not grant permission.

## Identity

- Ticket is [CBRD-27841](https://jira.cubrid.org/browse/CBRD-27841), created and read back as a Sub-task of OOS M2, CBRD-26583. Status is Open, unassigned, related to CBRD-27230. Live description matches the reviewed Markdown conversion.
- Source repository is `vimkim/cubrid`; remote is `vk`.
- Source branch is `CBRD-27841-remove-unused-oos-recovery-index`; initial task name was `review/pr7990-hornet-r6`.
- Source commit is `eac70c7e740d55b4623b46bb84797e8214dcdcc4`.
- Target repository is `CUBRID/cubrid`, base `feature/oos-merge`.
- Fetched base is `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`. R1 and R5 are independent branches.
- Source branch was absent on `vk` and no matching PR existed at preparation.
- Proposed title is `[CBRD-27841] Remove unused OOS recovery index`.
- Create as a draft, assigned to `vimkim`. No reviewer request or ready transition is proposed.

## Material and revisions

- Agent is `codex`.
- PR body and context are the two `CBRD-27841-recovery-index-cleanup-pr-*` files in this directory, with source identity `eac70c7`.
- Docs task is `docs/pr7990-hornet-r6-20261030`; integration destination is docs main.
- Retained docs paths are this directory's body, context and README, plus the shared PR7990 checklist, R6 detailed report and their ticket README under `cbrd-26357/`.
- JIRA notes task is `docs/CBRD-27841-recovery-index`; integration destination is notes main. Incoming paths are README and `issues/CBRD-27841-oos-recovery-index-cleanup_eac70c7_codex.md`.
- No optional public explanation is linked from the body. The live ticket contains the scope and local verification.
- `00dedf3fb` adds the format-guard characterization test; its engine is unchanged from the base. `eac70c7e7` removes the unused index and bumps the format revision.
- The fixed binaries were built at the original source commit `cac4d38e2`; amending that local commit removed only one test-script narration comment. All four compiled engine files are identical to `eac70c7e7`. The final script was used for the passing fixed CTest.

## Evidence and limits

- All 142 retained enum/table entries align at 0 through 141. Retained handler and dump rows are unchanged. The two shifted entries are the only numeric changes.
- Baseline and fixed debug builds/installations passed. The same focused CTest selection passed 10/10 before and after, including six fixture entries, one format-guard script and three binaries with 13 GoogleTests.
- Format revision 2 was read from the dedicated verification volume. The guard checks 0, previous revision 1 and future revision 3 through csql, checkdb and emergency patch, restores the current stamp, and leaves refused-database deletion to its owned fixture.
- GDB observed `rv_check_rvfuns` during a real standalone open. The actual binary reported IDs 140/141 and the expected retained table rows and heap undo/redo handlers.
- Separate committed INSERT/UPDATE/DELETE and aborted UPDATE/INSERT were checked after reopening. Counts were 1 total row, 1 exact committed 30000-byte value, 0 deleted row and 0 rolled-back row. `checkdb -S` returned success.
- The first GDB attempt passed SQL through command-line quoting and failed to select the intended DB. It did not reach the registry breakpoint or run the data test. Using an input SQL file and disabling debugger startup-shell argument handling fixed the observation method; the successful run then verified the registry and data. The first logs were retained.
- Release, cross-build HA, separate same-build replica replay, and guaranteed emission/replay of the two shifted producers are not verified by this local test selection. SA crash redo does not establish those paths. Independent correctness review found no blocker and recorded these limits.
- The existing reserved name also appears in the accepted future CBRD-27230 notification design. Removing the current unused stub does not implement or cancel that design.

## Proposed operations after explicit approval

1. Recheck the source commit and cleanliness, fetched base, approved material and exact duplicate-PR query.
2. Rebase the docs task onto current local main, preserve any other agent's R5 changes, audit only the six retained R6 paths, validate, fast-forward merge and push main. Include final publication records only within these retained paths.
3. Integrate and push the JIRA notes task through the same procedure. The ticket was already created and verified; do not rewrite its description or change its fields.
4. Normally push only the reviewed source branch/commit to `vk`, then verify the remote SHA. No organization topic branch, native stack or source merge.
5. Create one company draft PR using the exact saved body/title, base `feature/oos-merge`, personal-fork head and assignee `vimkim`. Read back all metadata and the body fingerprint.
6. If approved with publication, run the fresh activity and feature testcase baseline checks, then post one `/run all` and verify pickup. Existing activity, changed source or missing/stale testcase baselines require the CI skill's handling. This does not authorize testcase branch changes or cancelling another run.
7. Record results, integrate/push the final R6 document records under the same approval, and clean only successfully merged document worktrees/branches. Preserve the R6 source worktree and verification DB. Do not alter R5 work, PR7990 review threads, reviewer replies, review requests or source merges.

## Approval state

The user confirmed the saved body and listed operations with `yes` on 2026-10-30. This authorization covers this publication attempt, including the document integration/push, personal-fork source push, company draft PR and one full CI after its preflight. It does not grant permission for future source changes, reviewer requests or source merges.

## Publication results, 2026-10-30

- Docs main had advanced to `0b0ba75027de27922e3d01f4a0ca283ee91c8d2e` with the other agent's completed R5 evidence. Rebase conflicts were confined to the shared checklist and index. R5's detailed section was preserved byte-for-byte, and only the status summaries were combined. The approved PR body, context, R6 report and ticket index were unchanged during conflict resolution.
- Audited the full incoming history and six intended R6 document paths, validated links and material, then fast-forward merged and pushed docs main at `db85923346beb2879aa54153e8f04433034a6dc5`. Final publication records are integrated separately under the same approval.
- JIRA notes main was fast-forward merged and pushed at `1938d1f39ccc62d38a7dde2760e46b933c88b872`. Only README and the keyed report were incoming. Its Markdown SHA256 remains `09e21b2c005917af66215a2389d0f0eaf1834f396ccd17b4b96ecfb6a0496456`. The live issue description and fields were not rewritten.
- A normal push published `vimkim/cubrid:CBRD-27841-remove-unused-oos-recovery-index`. The remote commit was read back and matched `eac70c7e740d55b4623b46bb84797e8214dcdcc4`.
- Created [CUBRID/cubrid PR 8347](https://github.com/CUBRID/cubrid/pull/8347), draft, assigned to `vimkim`, base `feature/oos-merge`. Source repository, branch, commit, base, title, draft state and assignee matched the proposal on readback.
- The published body SHA256 is `769d90fee615ac67452a0b887e999805150ae33a5c5ee85f9264e62ea0d3cffc`, exactly matching the reviewed file including its final newline.
- Both feature testcase ancestry checks passed. Public `tc/pr-8347` was `f54abce15d6d21e87a20f47fda2d678d100124fd`, containing baseline `70db22a1c99dbbaa27fa1438c8967effdfcad551`. Private `tc/pr-8347` equaled its baseline `75a02020e19be4bfc64e47f7c7a3d5c2b02d7676`. The agent changed no testcase branches.
- With no existing `/run` comment or gha-ci activity for this head, posted one approved [`/run all`](https://github.com/CUBRID/cubrid/pull/8347#issuecomment-6521534443). Both build contexts and SQL, medium and shell contexts became PENDING and pointed to [gha-ci 41048233875](https://github.com/CUBRID/cubrid/actions/runs/41048233875). No stable required gha-ci context was missing at pickup.
- `gh pr checks --required` returned exit 1 with `no required checks reported on the 'CBRD-27841-remove-unused-oos-recovery-index' branch`. The five gha-ci statuses were verified separately. CI completion and company review remain pending; this record does not claim a passing result.
