# CBRD-28073 PR draft context

Resume and publication bookkeeping for `pr-body.md`. This file is not uploaded.

| Field | Value |
| --- | --- |
| Ticket | [CBRD-28073](https://jira.cubrid.org/browse/CBRD-28073) (Sub-task of CBRD-26978) |
| Operation | create (draft PR) |
| Target repository | `CUBRID/cubrid` |
| Base | `feature/oos-merge` (`c02f897268`) |
| Source repository / branch | `vimkim/cubrid` / `CBRD-28073-serial-nextval-keep-form` |
| Head spec | `vimkim:CBRD-28073-serial-nextval-keep-form` |
| SOURCE_COMMIT | `31c72e8342cb05fc60860d7fcec2da60e2e0b9ab` (rebased onto `c02f897268`; previous head `f3076784bc`) |
| Remote head at preparation | `87a6f40ac1` on `vk` (fast-forward to SOURCE_COMMIT); no PR for this head |
| Proposed title | `[CBRD-28073] Keep serial row storage form in NEXT VALUE` |
| Assignee | `vimkim` |
| Docs task branch | `cbrd-28073-pr-body` (integration branch `main`) |
| Body | `cbrd-28073/pr-body.md` |
| Context | `cbrd-28073/pr-context.md` |

## Authorization

On 2026-11-12 the user approved the plan "vk에 push한 뒤 feature/oos-merge 대상 draft PR을 만들겠습니다" with
"좋아. 승인할게." After the risk review the user said "응 바로 만들자. 고치고 테스트를 다시 돌린 뒤 draft PR 을 만들자."
(2026-11-12), which directs creation once the hardening commit passes the tests.

## Proposed operations

1. Commit `cbrd-28073/` files on `cbrd-28073-pr-body`, rebase onto `origin/main`, push `main` to `origin` of
   my-cubrid-docs.
2. Push `CBRD-28073-serial-nextval-keep-form` to remote `vk` (`github.com/vimkim/cubrid`), no force.
3. `gh pr create --repo CUBRID/cubrid --draft --base feature/oos-merge --head vimkim:CBRD-28073-serial-nextval-keep-form
   --assignee vimkim --title <proposed title> --body-file cbrd-28073/pr-body.md`.
4. Leave PR #8492 and #8496 open until this PR is verified and the #8492 session agrees.

## Execution record

- 2026-11-12: hardening commit `f3076784bc`; OOS ctest 53/53; SA/CS matrix, cross-serial, grow, page-full and upgrade
  scenarios all intact (scratch output `keepform-final3.txt`).
- 2026-11-12: draft PR https://github.com/CUBRID/cubrid/pull/8514 created at `f3076784bc`; first `/run all` (run 43217057347)
  failed shell, sql, sql_by_cci on a base 33 commits behind `feature/oos-merge`.
- 2026-11-13: user approved rebase ("1. yes"). Rebased onto `c02f897268`, resolved `unit_tests/oos/sql/CMakeLists.txt`,
  capped the `oosserialdb` setup fixture at 60 s for CBRD-28067's timeout check. OOS ctest 66/66 in this worktree
  (earlier ctest runs after the hardening had followed an inherited `CUBRID_BUILD_DIR` into the #8492 worktree and
  are not evidence). Scenario scripts intact (`keepform-rebased.txt`). Force-pushed with lease to `31c72e8342`; PR body
  updated with the new base and ctest count.
- 2026-11-19: user approved rebase, TC sync, `/run all`. Rebased onto `71993ddb63` (includes #8491), resolved
  `unit_tests/oos/CMakeLists.txt` by keeping both fixtures; OOS ctest 69/69 with the direnv-pinned build dir;
  force-pushed with lease to `8d736ff51c`. Merged `feature/oos-merge` into `tc/pr-8514` in both testcase repos
  (public `1a02bb474`, private `a91fb1ead`). `/run all` run 44476482025: all six gha-ci contexts SUCCESS.
  `cbrd_27780` checked locally: the base fails items 3 and 5 with the old testcase and passes with the fixed one.
  ALTER-merge path (`serial.c:2285`): no OOS chain leak (JIRA comment 4778780). User approved draft -> ready with
  the body updated for the new base, ctest count and CI result.
- 2026-11-19 (evening): five-reviewer review of `8d736ff51c` (report `code-review-pr8514.md`, PR comment 7007762519,
  Greptile threads answered and resolved). User approved rebase + fixes: rebased onto `8c478d8559` (CBRD-27230 conflict
  resolved onto `reused_stub`), added `a39cdf84a1` (DDL merge keep-form) and `8e9d71fda0` (release guard).
  Delta verification V1/V2/V3 passed (OOS ctest 74/74). User approved: force-push with lease to `vk`
  (`8d736ff51c` -> `8e9d71fda0`), PR body update from `pr-body.md`, TC sync (private `tc/pr-8514` -> `b4fac7513`,
  public already current), `/run all` (run 44522105929), PE1/PE2 JIRA drafts.

