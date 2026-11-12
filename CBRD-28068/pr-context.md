# CBRD-28068 PR publication proposal

The goal is to restore develop release builds with GCC 11.5 without suppressing warnings. This change prepares a draft PR for explicit user approval.

## Source and target

- Ticket is https://jira.cubrid.org/browse/CBRD-28068.
- Operation is `create`. No PR exists for the task branch.
- Target repository is `CUBRID/cubrid`.
- Head repository is `vimkim/cubrid`, using remote `vk`.
- Head branch is `CBRD-28068-partition-key-build`.
- Source commit is `2e04e056af7c9fd7ad5c45f4ba5873339d6c65e0`.
- Base branch is `develop` at `98b892cf496ced0d1e7836f58189797f9842e1ec` when fetched on 2026-11-12.
- The head branch does not exist on the fork as of the preparation check.
- Proposed title is `[CBRD-28068] Fix GCC release build of partition key lookup`.
- Proposed state is draft. Proposed assignee is `vimkim`.

## Prepared documents

The docs repository is `vimkim/my-cubrid-docs`. Its task branch is `docs/CBRD-28068-partition-key-build`, with integration into `main`.

- `CBRD-28068/pr-body.md` is the exact proposed GitHub body.
- `CBRD-28068/pr-context.md` records source identity and proposed operations.
- `CBRD-28068/README.md` indexes the prepared material.

The issue report is locally committed in `vimkim/my-cubrid-jira` on `docs/build-partition-key-20261112`. Commit `6dff2cf` names `issues/CBRD-28068-partition-key-gcc11.md`. The issue itself was created under the brief's explicit authorization. Its live summary and raw description exactly matched the create preview. Local notes integration and push remain proposed.

## Verification

On 2026-11-12, GCC 11.5.0 package `11.5.0-5` failed the unmodified source at `qo_node_partition_key()` with `-Werror=return-local-addr`. The release configuration used `RelWithDebInfo`, `-O2`, `-DNDEBUG`, and fatal warnings.

Release and debug builds and installations passed with the fix. The debug standalone probe returned join count 3 and sum 41, then count 2 and sum 21 with a constant key predicate. GDB counted six calls to the changed helper.

The existing `sql/_36_guava/cbrd_27866` testcase at `CUBRID/cubrid-testcases` commit `89f591ac7` passed native SQL testkit under containment. The verifier confirmed one expected and executed testcase, one success, and zero failures. JDBC used `test_default.xml`, charset `en_US`, and one slot. The copied configuration retained locale generation and test mode.

Both builds and the SQL checks used base `98b892cf49` with the uncommitted source patch. The final commit's complete source diff exactly matches the patch recorded before the native run. GNU indent and the pre-commit style check passed. No full CI run or full regression suite ran during preparation.

The source checkout is clean. Unrelated modifications and untracked files in the starting develop checkout were preserved. No runtime processes remain from the dedicated host probe or contained test. The probe database and local test evidence are retained.

## Proposed operations after confirmation

1. Rebase each documentation task branch onto its current local `main`, review and check it, merge by fast-forward, and push `main` to its configured origin. Use the authorized squash fallback only if required. This includes the prepared PR material and the issue report.
2. Push source commit `2e04e056af7c9fd7ad5c45f4ba5873339d6c65e0` to `vimkim/cubrid`, branch `CBRD-28068-partition-key-build`.
3. Create the draft PR in `CUBRID/cubrid` against `develop`, with the proposed title, the exact reviewed body, and assignee `vimkim`.
4. Inspect both automatically created TC PRs. No testcase change is proposed. The human closes their unchanged TC PRs.
5. Trigger CUBRID CI once after the source push, wait for completion, report the run URL, result and any TC Merge Gate blocker, then stop for human direction.

No engine merge, deployment, TC PR merge or closure, remote deletion, or force push is proposed. This file records a proposal. Approval must come from the conversation.

## Publication attempt on 2026-11-12

The user explicitly resumed the approved documentation integration and push, source push, draft PR creation, and one CI run on 2026-11-12. This section records execution, not permission for later operations.

- The approved body SHA-256 is `e7967470cad2e809628b4f872302b94e632d2aced1329e354b6718be8e20c3dc`.
- The source commit still equals `2e04e056af7c9fd7ad5c45f4ba5873339d6c65e0`.
- Before publication, the fork branch was absent and the exact head/base search found no open PR.
- Both documentation integration checkouts had unrelated tracked edits. Preserve those edits through scoped temporary stashes and verify their restoration after integration.

## Publication results

- PR material was integrated and pushed to `vimkim/my-cubrid-docs:main` at `5230cd5ff1f6bb35278794cca9c287a5383c0ac7`.
- The issue report was integrated and pushed to `vimkim/my-cubrid-jira:main` at `6dff2cf809f1d20564bf0b5c5b29cdfafdd38ae8`.
- Both main checkouts' unrelated edits were restored. Binary diff comparisons matched their saved pre-integration contents.
- `vimkim/cubrid:CBRD-28068-partition-key-build` was pushed and its remote head verified as `2e04e056af7c9fd7ad5c45f4ba5873339d6c65e0`.
- Draft PR https://github.com/CUBRID/cubrid/pull/8510 was created against `develop` and assigned to `vimkim`. Read-back verified the exact body, title, source repository, source commit, branches, and draft state. The published body SHA-256 equals the approved fingerprint above.
- Automatic TC PRs https://github.com/CUBRID/cubrid-testcases/pull/4169 and https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4873 each contain only the bot's empty initialization commit and have zero changed files. No testcase edit is required. The human closes these unchanged PRs.
- One `/run all` was posted at `2026-11-12T09:03:35Z`. Its receipt is https://github.com/CUBRID/cubrid/pull/8510#issuecomment-6819366084.
- Both build contexts and all suite contexts were observed pending on https://github.com/CUBRID/cubrid/actions/runs/43188099115. Completion remains pending at this execution-record commit. Work Tracker item 936 records the terminal result after observation.
