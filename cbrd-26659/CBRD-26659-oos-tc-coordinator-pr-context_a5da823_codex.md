# CBRD-26659 engine coordinator PR proposal

Prepared: 2026-10-10 (Asia/Seoul). Agent: codex. Implementation work item: 306 (done); publication work item: 314. Status: saved material ready for review; no remote writes.

## Source and destination

- Ticket: CBRD-26659.
- SOURCE_COMMIT: `a5da823b2a84e95b4b22d48abe4a3f9fd601c176`.
- Source repository: `vimkim/cubrid`; branch: `CBRD-26659-oos-testcases-handover`; push remote: `vk`.
- Target repository: `CUBRID/cubrid`; base: `feature/oos-merge`; operation: create.
- Base observed after fetch: `fb567a629cdb390fff920542173fa36f454c74a0`. It is the exact parent of SOURCE_COMMIT.
- Source tree: `016702849c2d67eb349a51ca4c8bf1a7157ea789`, identical to the parent. Exactly one additional empty commit and zero changed files.
- Remote source branch: absent on 2026-10-10. `gh-pr-info` reports no PR for this branch; recheck exact repository/head/base before publication.
- Proposed title: `[CBRD-26659] Initialize OOS testcase review`.
- Proposed state: draft; assignee: `vimkim`; no automatic reviewer assignment.
- Existing unrelated CCI submodule changes remain uncommitted and excluded. The empty-commit check verified the same status and header bytes before and after the commit.

## Saved material

- Body: `cbrd-26659/CBRD-26659-oos-tc-coordinator-pr-body_a5da823_codex.md`; upload these exact reviewed UTF-8 bytes.
- Context: `cbrd-26659/CBRD-26659-oos-tc-coordinator-pr-context_a5da823_codex.md`.
- Docs task branch: `docs/oos-tc-prs`; integration branch: `main`.
- No external explanation link and no docs remote push are required.

## Exact proposed publication operations

1. Recheck engine source/base/remote head, the unchanged source tree, unrelated dirt, body bytes and the PR material checker. If the source/base or proposed contents change, reconcile and return for review.
2. Push only `CBRD-26659-oos-testcases-handover` at SOURCE_COMMIT to `vimkim/cubrid` through `vk`, without force and without updating an engine base branch.
3. Create a draft PR in `CUBRID/cubrid`, head `vimkim:CBRD-26659-oos-testcases-handover`, base `feature/oos-merge`, title above, saved body unchanged and assignee `vimkim`.
4. Opening this PR automatically invokes TC Branch Sync GHA. Observe that run read-only and record the two bot-created TC PR URLs, exact head commits and bases. Verify that both TC bases are `feature/oos-merge`; never reuse an unrelated engine PR's TC branches.
5. Commit verified publication records and integrate this docs task into local `main` by rebase and fast-forward merge, including final record updates, then safely remove only the merged docs task worktree/branch. Audit all incoming paths and preserve useful local files before cleanup. The incoming selection is README, three PR bodies and three companion contexts; no raw receipts are included.

This phase proposes no manual `gha-ci` request, testcase push/body update, PR merge/close, remote branch deletion, JIRA publication or engine file changes. Confirmation of this proposal would authorize an exception to the prior blanket no-push/no-GHA instructions only for the engine topic push and automatic TC branch creation listed above. No testcase base branch is merged by the agent.

## Subsequent testcase preparation

After branch creation, preserve both validated task branches as source snapshots. Prepare the bot TC branches by integrating the public and private commits while retaining each bot initialization commit; do not force-push or replace the bot branch history. Check source-byte equivalence, fresh base inclusion, cleanup evidence and independent expectations before proposing the exact TC head pushes and description updates. The user obtains teammate review; the agent never merges or closes those TC PRs.

The original standalone TC publication contexts are superseded. Their body files remain valid historical descriptions of the payload and validation, but future updates must identify the actual bot PRs and integrated TC heads before publication. Relevant source baselines are public `bdba62aee0faec05abdd861518824c69b6c1b3c5` and private `c4b9d482fbd491a68510b2552df2c3cac91911fc`.

## Validation scope and full-CI decision

- Public payload: `c94961578dc43bfe05a74591d52dff30d44a43d3`; 17 SQL/answer pairs in ordinary discovery paths; only 16 have passing selected native qualification. `cbrd_26659_oos_partition.sql` remains a correct failing reproducer outside the green selection.
- Private payload: `f5fc1fa815fbc6eec71135f506e377c0b1096da3`; 18 shell entrypoints in ordinary discovery paths; only 14 have passing selected native qualification. `partition_owner`, `snapshots_reclaim`, `cbrd_27237_rollback_vacuum` and `utility_sa_physical` remain failing or inconclusive reproducers outside the green selection.
- Existing timings are historical exact-source native results, not a new engine-head build or full-CI verdict. The empty engine commit requires no compilation to verify its identical tree.
- Before requesting full CI, select an explicit disposition for the five retained reproducers. Preserve the failing expectations and evidence; do not silently disable, relocate or weaken them to report a green full suite.

This context is a proposal, not an approval token. Publication requires confirmation of the saved body and exact operations from the conversation.
