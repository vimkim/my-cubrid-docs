# CBRD-26659: sql TC PR body publication context

Prepared: 2026-10-27, Asia/Seoul. Agent: `codex`.
Status: published and checked. GitHub body matches the approved file.
This context does not establish publication permission.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | https://jira.cubrid.org/browse/CBRD-26659 |
| Operation | `update` existing body |
| Target repository | `CUBRID/cubrid-testcases` |
| PR | https://github.com/CUBRID/cubrid-testcases/pull/3688 |
| Existing title | `[CBRD-26659] Draft: TC changes for PR CUBRID/cubrid#8128` |
| Title operation | Preserve |
| PR state | `OPEN`, draft=`true` |
| Draft/ready operation | Preserve |
| Source repository | `CUBRID/cubrid-testcases` |
| Source branch | `tc/pr-8128` |
| SOURCE_COMMIT | `4f6557f7f96ac789e1697ef8b27dd8bf2807802e` |
| Observed remote head | `4f6557f7f96ac789e1697ef8b27dd8bf2807802e` |
| Base branch | `feature/oos-merge` |
| Observed base commit | `696a8fd85e0ddc2bad54fc40177cabbf02970415` |
| Engine for recorded CI | `c4c4f5c5ed55fb0130c72bb261061ec441662554` |
| Original decoded GitHub body SHA-256 | `1af702e148a30c4badaf6b1e5b0a3aeb7fde771774beec6a99a6015b5bd0966c` |
| Prepared body file SHA-256 | `e8283299de7c6cf0d315c058232669bfd549f94f56462cbdf5b19cebe1eb2078` |

## Saved material

- Body: [CBRD-26659-oos-sql-regressions-pr-body_4f6557f_codex.md](CBRD-26659-oos-sql-regressions-pr-body_4f6557f_codex.md).
- Context: `cbrd-26659/CBRD-26659-oos-sql-regressions-pr-context_4f6557f_codex.md`.
- Previous published description: [CBRD-26659-oos-sql-regressions-pr-body_1a556a0_codex.md](CBRD-26659-oos-sql-regressions-pr-body_1a556a0_codex.md).
- Docs task branch: `docs/work456-tc-pr-bodies-20261027`.
- Docs integration branch: `main`, remote `origin` of `vimkim/my-cubrid-docs`.
- Initial docs integration commit: `def505f`.
- Detailed explanation: none. The body links existing revision-pinned TC inventories.

The earlier description remains historical. Its October 8 native counts do not
establish results for SOURCE_COMMIT. The new body describes the complete current
PR diff and current execution selection. This description update does not change testcase bodies or answers.

## Evidence and limits

- The complete PR diff contains 28 SQL/answer pairs: 25 enabled and 3 disabled.
- The PR preserves disabled case and answer content under `disabled/failing/sql/`.
- `disabled/README.md` and `disabled/oos-pr8128.tsv` identify the three failures.
- Run [40324320840](https://github.com/CUBRID/cubrid/actions/runs/40324320840) used this public TC head and the Engine above. SQL and medium commit-status contexts are PASS. The workflow conclusion is FAIL because two shell shards failed.
- The body makes a suite-status claim. It does not claim a newly checked complete SQL testcase-level collector inventory. The earlier run40311481032 full SQL collection had a shard01 summary/JUnit count mismatch, retained in the TC README.
- SQL logical outcomes do not establish physical state for another shell invocation.
- Disabled failures receive no passing-coverage credit. Broader Work456 independent qualification remains incomplete. Performance comparison and HA Work463 remain deferred.
- The current checks contain no automated TC Merge Gate entry for `feature/oos-merge`. Both TC PRs remain open for human review and merge.

## Exact proposed operations for both TC bodies

One confirmation will cover this shared operation list:

1. Reread both saved bodies. Check both remote PR heads, branches, bases, draft states, and original body fingerprints. Reconcile any changed source revision or GitHub body before publication.
2. Rebase `docs/work456-tc-pr-bodies-20261027` onto the current local `main`. Review the incoming files and links. Fast-forward the docs destination and push `origin main`. The retained files are the two new bodies, their two contexts, and `cbrd-26659/README.md`.
3. Update only the body of public TC PR3688 from `CBRD-26659-oos-sql-regressions-pr-body_4f6557f_codex.md` and private TC PR4365 from `CBRD-26659-oos-shell-regressions-pr-body_8486abd_codex.md`. Preserve titles, draft/ready states, head branches, and bases.
4. Read both GitHub bodies and check their decoded UTF-8 bytes against the approved files. Record per-PR results and body fingerprints in these contexts. Update only publication status in the docs README. Commit and push the docs execution records under the same integration approval.
5. After checking integration and publication, remove only this merged docs task worktree and remove its local topic branch without force. Preserve valuable local material.

These operations do not include source/TC commits or pushes, CI triggers, JIRA
writes, PR merges or closures, or remote branch deletion. TC PR merge, closure,
and branch deletion remain human actions.

## Publication record

- Confirmation: the user said `yes publish` after the assistant presented both body drafts and the shared operation list.
- Docs integration/push: commit `57ce44eb6e5e18802b77f70e604e63d40725627b` was fast-forwarded into `main` and pushed to `origin main` before the GitHub edits.
- GitHub body update: https://github.com/CUBRID/cubrid-testcases/pull/3688, checked at `2026-10-26T15:21:27.642369+00:00`.
- Checked remote body fingerprint: `e8283299de7c6cf0d315c058232669bfd549f94f56462cbdf5b19cebe1eb2078`. Decoded UTF-8 bytes equal the approved body file.
- GitHub returned the same source revision, head/base branches, OPEN state, title, and draft state.
- This attempt changed only the two PR bodies and the approved docs. It did not push source/TC commits or trigger CI.
