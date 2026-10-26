# CBRD-26357: public TC PR body context

Prepared: 2026-10-27, Asia/Seoul. Agent: `claude`.
Status: prepared for review; not published.
This context does not establish publication permission.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | https://jira.cubrid.org/browse/CBRD-26357 |
| Operation | `update` existing body |
| Target repository | `CUBRID/cubrid-testcases` |
| PR | https://github.com/CUBRID/cubrid-testcases/pull/3551 |
| Existing title | `[CBRD-26357] Draft: TC changes for PR CUBRID/cubrid#7990` |
| Title operation | Preserve |
| PR state | `OPEN`, draft=`false` |
| Draft/ready operation | Preserve |
| Source repository | `CUBRID/cubrid-testcases` |
| Source branch | `tc/pr-7990` |
| SOURCE_COMMIT | `70db22a1c99dbbaa27fa1438c8967effdfcad551` |
| Observed remote head | `70db22a1c99dbbaa27fa1438c8967effdfcad551` |
| Base branch | `develop` |
| Observed base commit | `2c828d25ddf282b9696dde7258ec80c220e09e9b` |
| Engine for recorded CI | `5a70787feea9e0488222af7e3a0249cc431562ca` (gha-ci run 40349442612) |
| Original decoded GitHub body SHA-256 | `00bfbce2339a1f4fcb9073a5c76eb466340f682f0ca65cf8eb30d6a01135bf6b` |

## Saved material

- Body: [CBRD-26357-public-tc-changes-pr-body_70db22a_claude.md](CBRD-26357-public-tc-changes-pr-body_70db22a_claude.md).
- Detailed explanation: [CBRD-26357-tc-pr-changes_5a70787_claude.md](CBRD-26357-tc-pr-changes_5a70787_claude.md), public URL `https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-26357/CBRD-26357-tc-pr-changes_5a70787_claude.md`.
- Docs task branch: `docs/pr7990-tc-pr-bodies-20261027`. Integration branch: `main` of `vimkim/my-cubrid-docs`.

The original body was the sync-bot template plus a note about the earlier `feat/oos` PRs (#3159, #3782). It did not list the testcase changes. The new body replaces it; #3159 remains in Remarks. The title keeps its `Draft:` word although the PR is not a GitHub draft; the title is preserved because no title change was requested.

## Proposed operations

1. Commit the body, context, and explanation files on the docs task branch; rebase onto `main`, fast-forward `main`, and push `origin main`.
2. Verify the explanation URL resolves on GitHub.
3. Update the body of PR #3551 from the body file with `gh pr edit 3551 --repo CUBRID/cubrid-testcases --body-file <body>`. Keep the title and draft/ready state.
4. Verify the published body SHA-256 equals the body file SHA-256 and record the result here.

No source push is needed.
