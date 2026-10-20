# CBRD-27712 PR draft context

- Ticket: https://jira.cubrid.org/browse/CBRD-27712 (`3rdparty prefix`).
- Agent: `codex`.
- Source commit: `15609d2a779e3082aafe5af576487ebbdc8d70f6`.
- Source repository / branch: `vimkim/cubrid:CBRD-27712-thirdparty-reuse`.
- Base: `CUBRID/CUBRID:develop`, observed `14b0b1cbd94c26860ea0ed006d8f928a90eec514`.
- Target: `CUBRID/CUBRID`, operation `create`.
- Existing matching PR: none observed on 2026-10-21. No current PR title, state, or body fingerprint applies.
- Proposed title: `[CBRD-27712] Add reusable Linux third-party prefixes`.
- Proposed PR state: draft. Proposed assignee: `vimkim`.
- Docs repository: `vimkim/my-cubrid-docs`.
- Docs task branch: `docs/CBRD-27712-thirdparty-prefix`.
- Docs integration branch: `main`.
- Body file: `CBRD-27712/CBRD-27712-thirdparty-prefix-pr-body_15609d2_codex.md`.
- Context file: `CBRD-27712/CBRD-27712-thirdparty-prefix-pr-context_15609d2_codex.md`.
- Explanation file: `CBRD-27712/CBRD-27712-thirdparty-prefix_15609d2_codex.md`.
- Index file: `CBRD-27712/README.md`.
- Public explanation URL: https://github.com/vimkim/my-cubrid-docs/blob/main/CBRD-27712/CBRD-27712-thirdparty-prefix_15609d2_codex.md

## Preparation and source publication

The user provided standing authorization to commit and push a checked CUBRID implementation. Source push uses `vk`, the configured personal fork. This authorization does not cover local integration into source `develop`.

The source push completed on 2026-10-21. The remote branch points to `15609d2a779e3082aafe5af576487ebbdc8d70f6`. The pre-push base freshness check passed against `origin/develop`. This context does not grant approval for the proposed operations below.

## Proposed operations for confirmation

1. Rebase the docs task branch onto current local `main`. Review its selected documents and links. Merge with fast-forward, or squash if necessary under the approved workflow. Push the resulting `main` to `vimkim/my-cubrid-docs`. Include the four files listed above and any final publication execution-record updates to this context and index.
2. Check that the source branch on `vimkim/cubrid` still points to the recorded source commit and that no matching PR exists. A source revision change requires reconciliation and another review.
3. Create a draft PR in `CUBRID/CUBRID`, from `vimkim:CBRD-27712-thirdparty-reuse` to `develop`, with the proposed title, exact saved body, and assignee `vimkim`. Publish the linked explanation before creating the PR.
4. Record the verified PR URL and publication results in this context. Update the ticket index with the PR number. Commit those records, integrate them into docs `main`, and push them to `vimkim/my-cubrid-docs`.
5. Under the standing CUBRID CI authorization, trigger one CUBRID CI run after source publication and any required TC pushes. This change requires no TC changes. Wait for the run, then report its result, run URL, and both TC Merge Gate dependencies. Stop for human direction before follow-up fixes, pushes, or CI reruns.

The proposal excludes source merge, deployment, TC PR merge/closure, TC branch deletion, and remote branch deletion. The human closes the two bot-created TC PRs when the change requires no TC changes.

## Validation and review state

The explanation records local validation and its host-specific corrections. Standards review found 0 issues. Spec review found 1 issue, resolved by `15609d2a7` and independently rechecked. The source branch contains the committed changes. PR creation and CI remain pending.

Review the saved body and explanation before publication approval. The user can edit the body directly. Reread and check the current files before an approved publication attempt. Record their SHA-256 fingerprints for that attempt. Upload the reviewed text unchanged.
