# CBRD-26357: private TC PR body context

Prepared: 2026-10-27, Asia/Seoul. Agent: `claude`.
Status: published and checked on 2026-10-27. GitHub body matches the approved file.
This context does not establish publication permission.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | https://jira.cubrid.org/browse/CBRD-26357 |
| Operation | `update` existing body |
| Target repository | `CUBRID/cubrid-testcases-private-ex` |
| PR | https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4210 |
| Existing title | `[CBRD-26357] Draft: TC changes for PR CUBRID/cubrid#7990` |
| Title operation | Preserve |
| PR state | `OPEN`, draft=`false` |
| Draft/ready operation | Preserve |
| Source repository | `CUBRID/cubrid-testcases-private-ex` |
| Source branch | `tc/pr-7990` |
| SOURCE_COMMIT | `75a02020e19be4bfc64e47f7c7a3d5c2b02d7676` |
| Observed remote head | `75a02020e19be4bfc64e47f7c7a3d5c2b02d7676` |
| Base branch | `develop` |
| Observed base commit | `88bec5cd8881fe496a2a10c8754105c0c25ef8b4` |
| Engine for recorded CI | `5a70787feea9e0488222af7e3a0249cc431562ca` (gha-ci run 40349442612) |
| Original decoded GitHub body SHA-256 | `0931bb390b9bd943878ef19ca0597a16812b270e5fb42123dad193f1c8a36f99` |

## Saved material

- Body: [CBRD-26357-private-tc-changes-pr-body_75a0202_claude.md](CBRD-26357-private-tc-changes-pr-body_75a0202_claude.md).
- Detailed explanation: [CBRD-26357-tc-pr-changes_5a70787_claude.md](CBRD-26357-tc-pr-changes_5a70787_claude.md), public URL `https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-26357/CBRD-26357-tc-pr-changes_5a70787_claude.md`.
- Docs task branch: `docs/pr7990-tc-pr-bodies-20261027`. Integration branch: `main` of `vimkim/my-cubrid-docs`.

The original body was the sync-bot template plus a note about the earlier `feat/oos` PRs (#3159, #3782). It did not list the testcase changes. The new body replaces it; #3782 remains in Remarks as the source of 16 ported files. The title keeps its `Draft:` word although the PR is not a GitHub draft; the title is preserved because no title change was requested.

## Proposed operations

1. Commit the body, context, and explanation files on the docs task branch; rebase onto `main`, fast-forward `main`, and push `origin main`.
2. Verify the explanation URL resolves on GitHub.
3. Update the body of PR #4210 from the body file with `gh pr edit 4210 --repo CUBRID/cubrid-testcases-private-ex --body-file <body>`. Keep the title and draft/ready state.
4. Verify the published body SHA-256 equals the body file SHA-256 and record the result here.

No source push is needed.

## Publication record

- Confirmed by the user in conversation on 2026-10-27 ("게시해").
- Docs: commit `86ce44b` fast-forwarded into `main` and pushed to `origin main`. The raw GitHub content of the explanation matches the reviewed file (SHA-256 `97d242d89a2ed48edd6a852f64e24c333532ffe11a8dad1feaf02e011d90740e`).
- Before the write, the PR head, title, state and original body fingerprint matched this context.
- Body updated with `gh pr edit 4210 --body-file`. Published body SHA-256 `737cb5685eaaef9930c6d1648944e1c35ed9f761f218944813b8f907c5791389` equals the body file SHA-256. Title, head and draft/ready state are unchanged.
