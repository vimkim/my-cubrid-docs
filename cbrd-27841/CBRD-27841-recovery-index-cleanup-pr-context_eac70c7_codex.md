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

The user authorized proceeding with R6 and the previously agreed independent issue/PR workflow. The issue has been created and local changes committed. Publication of this new PR and document integration/push await explicit confirmation of these saved files and operations under cubrid-pr-create and the user's Git workflow.
