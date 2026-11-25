# CBRD-28379 PR draft context

Bookkeeping for the PR body draft. Not uploaded.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | CBRD-28379 |
| `SOURCE_COMMIT` | `5c213aaac66549e92f805d2ed643c8fbdbc57939` |
| Source repository / branch | `vimkim/cubrid` (remote `vk`) / `CBRD-28379` |
| Base | `develop` at `ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e` |
| Observed remote head | none: `CBRD-28379` has not been pushed to `vk` (2026-11-25) |
| Target repository | `CUBRID/cubrid` |
| Operation | `create` (no existing PR; `gh-pr-info` found none for branch `CBRD-28379`) |
| Proposed title | `[CBRD-28379] Fix refused conditional latch leaving waiter_exists set` |
| Draft status | new PR is created as draft |

## Docs

| Field | Value |
| --- | --- |
| Docs task branch | `cbrd-28379-docs` |
| Integration branch | `main` of `vimkim/my-cubrid-docs` (Tier 1: integrate and push without asking) |
| Body | `cbrd-28379/pr-body.md` |
| Context | `cbrd-28379/pr-context.md` |
| Detailed explanation | `cbrd-28379/verification-report.md` (not linked from the body; the body stands alone) |
| Review | `cbrd-28379/review-findings.md` (independent review of `11b40319ee`) |

## Proposed publication operations (need explicit confirmation)

1. Push `CBRD-28379` at `5c213aaac6` to `vk` (`github.com/vimkim/cubrid`) as a new branch.
2. Create a draft PR in `CUBRID/cubrid` from `vimkim:CBRD-28379` to `develop` with the title above and the body in `cbrd-28379/pr-body.md`, assigned to `vimkim`.
3. After the TC Branch Sync bot creates the TC PRs, report that no TC change is needed and keep those TC PRs open.
4. Trigger CUBRID CI once through `cubrid-ci-trigger` (`/run`), wait, report the result, and stop.
5. Transition CBRD-28379 `Confirmed -> Develop` in JIRA.
6. Create the separate JIRA issue for review finding F7 from `my-cubrid-jira` `issues/CBRD-XXXXX-pgbuf-discard-flush-wait-sets-waiter-exists.md` (`8271f3a`; user answered "3. yes" on 2026-11-25). Duplicate check done: closest is CBRD-27971 (Resolved), whose fix `2b1db6ca29` missed this path from CBRD-27151 `063d84e537`.

User decision record (2026-11-25, Asia/Seoul): "1. yes 3. yes 2. yes", in reply to the decision list:

- 1 yes: hold publication now and approve it in one step after the docs review.
- 2 yes: keep the unfix fallback in this PR.
- 3 yes: handle F7 as a separate JIRA issue.

The user has not yet confirmed operations 1–6.

## Static evidence

`cubrid-static-check origin/develop 11b40319ee`. The amend `5c213aaac6` changed only a comment and the test in the source; no re-run was needed for the `src/` analysis.

| Check | New |
| --- | --- |
| cppcheck (high-signal rules) | 0 |
| clang-tidy (bugprone-*) | 0 |
| Duplicated code (CPD) | 0 |
| Complexity | `pgbuf_latch_bcb_upon_fix` CCN 43→44, `pgbuf_unlatch_bcb_upon_unfix` CCN 32→36 (below the flag threshold) |

Disposition: no defect to report.

## Function reuse

No new function under `src/`. Test-only helpers live in the test file.
