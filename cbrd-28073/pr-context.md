# CBRD-28073 PR draft context

Resume and publication bookkeeping for `pr-body.md`. This file is not uploaded.

| Field | Value |
| --- | --- |
| Ticket | [CBRD-28073](https://jira.cubrid.org/browse/CBRD-28073) (Sub-task of CBRD-26978) |
| Operation | create (draft PR) |
| Target repository | `CUBRID/cubrid` |
| Base | `feature/oos-merge` (`67220b7e23`) |
| Source repository / branch | `vimkim/cubrid` / `CBRD-28073-serial-nextval-keep-form` |
| Head spec | `vimkim:CBRD-28073-serial-nextval-keep-form` |
| SOURCE_COMMIT | `87a6f40ac1512367dbbf1fc2698a56488421ef55` |
| Remote head at preparation | branch absent on `vk`; no PR for this head |
| Proposed title | `[CBRD-28073] Keep serial row storage form in NEXT VALUE` |
| Assignee | `vimkim` |
| Docs task branch | `cbrd-28073-pr-body` (integration branch `main`) |
| Body | `cbrd-28073/pr-body.md` |
| Context | `cbrd-28073/pr-context.md` |

## Authorization

On 2026-11-12 the user approved the plan "vk에 push한 뒤 feature/oos-merge 대상 draft PR을 만들겠습니다" with
"좋아. 승인할게." The PR body itself awaits the user's review before creation.

## Proposed operations

1. Commit `cbrd-28073/` files on `cbrd-28073-pr-body`, rebase onto `origin/main`, push `main` to `origin` of
   my-cubrid-docs.
2. Push `CBRD-28073-serial-nextval-keep-form` to remote `vk` (`github.com/vimkim/cubrid`), no force.
3. `gh pr create --repo CUBRID/cubrid --draft --base feature/oos-merge --head vimkim:CBRD-28073-serial-nextval-keep-form
   --assignee vimkim --title <proposed title> --body-file cbrd-28073/pr-body.md`.
4. Leave PR #8492 and #8496 open until this PR is verified and the #8492 session agrees.

## Execution record

(none yet)
