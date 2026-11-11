# CBRD-28052 PR draft context

Resume and publication bookkeeping for `pr-body.md`. This file is not uploaded.

| Field | Value |
| --- | --- |
| Ticket | [CBRD-28052](https://jira.cubrid.org/browse/CBRD-28052) |
| Operation | create (draft PR) |
| Target repository | `CUBRID/cubrid` |
| Base | `feature/oos-merge` (`67220b7e23`) |
| Stacked on | PR #8492 head `7e9a4a5137` (branch `vimkim:CBRD-28035-serial-oos-chain-leak`) |
| Merge after | PR #8492 and PR #8434 |
| Source repository / branch | `vimkim/cubrid` / `CBRD-28052-serial-sa-rollback` |
| Head spec | `vimkim:CBRD-28052-serial-sa-rollback` |
| SOURCE_COMMIT | `9ba684e54761521b57d47baaf34124bf56b1db38` |
| Remote head at preparation | branch absent on `vk`; no PR for this head |
| Proposed title | `[CBRD-28052] Open a topop for serial row updates in SA mode` |
| Docs task branch | `docs/cbrd-28052-pr` (integration branch `main`) |
| Body | `cbrd-28052/pr-body.md` |
| Context | `cbrd-28052/pr-context.md` |

## Authorization

The user's task message on 2026-11-11 says: "The user authorizes pushing the branch to remote vk and creating a
DRAFT PR against feature/oos-merge through cubrid-pr-create. Do not mark it ready, do not merge, do not push to
origin, do not edit JIRA, and do not touch PR #8492 or its worktree." A later message from the PR #8492 session,
relayed by the user, asks to re-scope the fix to the first NEXT VALUE that moves an inline comment to OOS, or to
rebase on #8492, and to say in the PR how it depends on #8492. This is the standing instruction for the operations
below.

## Proposed operations

1. Commit `cbrd-28052/` files on `docs/cbrd-28052-pr`, rebase onto `main`, fast-forward `main`, push `main` to
   `origin` of my-cubrid-docs.
2. Push `CBRD-28052-serial-sa-rollback` to remote `vk` (`github.com/vimkim/cubrid`), no force.
3. `gh pr create --repo CUBRID/cubrid --draft --base feature/oos-merge --head vimkim:CBRD-28052-serial-sa-rollback
   --assignee vimkim --title <proposed title> --body-file cbrd-28052/pr-body.md`.

## Evidence

Scripts and outputs live in the session scratchpad, not in Git. The combination build is a temporary branch in the
scratch worktree: PR #8434 head `0d9732a63` merged with `feature/oos-merge` `67220b7e23`, then the #8492 commits and
this branch's commits.
