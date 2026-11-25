# CBRD-28378 PR draft context

Companion metadata for `pr-body.md`. This file is not uploaded.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | CBRD-28378 (JIRA status Confirmed at drafting; transition to Develop not performed) |
| SOURCE_COMMIT | `d9d641fbaceef65304a33cbcf8e6fb79363b5959` |
| Source branch | `CBRD-28378` (local only; not pushed) |
| Base | `develop` at `ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e` |
| Observed remote head | none; branch does not exist on `vk` or `origin` |
| Target repository | `CUBRID/cubrid` |
| Operation | create (new draft PR) |
| Proposed title | `[CBRD-28378] Keep OOS bestspace hints off latched pages` |

## Documents

| Role | Repo-relative path |
| --- | --- |
| Body | `cbrd-28378/pr-body.md` |
| Context | `cbrd-28378/pr-context.md` |
| Explanation (linked from Remarks) | `cbrd-28378/verification.md`, public URL `https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-28378/verification.md` |

Docs task branch `docs/cbrd-28378`, integration branch `main` (Tier 1, authorized).

## Proposed publication operations (require explicit confirmation)

1. Push `CBRD-28378` to the personal fork `vk` (`github.com/vimkim/cubrid`).
2. Create a draft PR `vimkim:CBRD-28378` → `CUBRID/cubrid:develop` with the title above and `pr-body.md` unchanged, assigned to `vimkim`.

Not proposed here: `/run` CI trigger, JIRA transition, TC PR changes. The user's task instruction (2026-11-25) states these wait for explicit approval.

## Static check

`cubrid-static-check origin/develop d9d641fbac`:

| Check | New | Disposition |
| --- | --- | --- |
| cppcheck | 0 | — |
| clang-tidy bugprone | 0, incomplete | Tool could not process `oos_file.cpp` on base or head; coverage gap only. |
| Duplicated code | 0 | — |
| lizard | `oos_stats_find_page_in_bestspace` CCN 34 → 44 | Accepted: busy-candidate skip and unit-test seam branches; no defect. |

## Review

Independent read-only review (separate agent) found no blocker; findings 1, 2, 6, 7 fixed before the commit, 3–5 accepted as advisory-hint tradeoffs, 8 deferred to CBRD-28379. See `verification.md`.

## Publication record (2026-11-25, user confirmed "yes")

| Operation | Result |
| --- | --- |
| Source push | `vk/CBRD-28378` = `d9d641fbaceef65304a33cbcf8e6fb79363b5959` (verified with `git ls-remote`) |
| Draft PR | https://github.com/CUBRID/cubrid/pull/8754 — draft, base `develop`, head `vimkim:CBRD-28378`, assignee `vimkim`; uploaded body SHA-256 prefix `2c07003e844cc6c3` equals `pr-body.md` |
| TC PRs (TC Branch Sync) | https://github.com/CUBRID/cubrid-testcases/pull/4463, https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5164 — no TC changes; kept open until the final merge handoff |
| JIRA | `Start Develop`: Confirmed → Develop (verified) |
| CI | `/run all` at 2026-11-25T12:48:41Z (https://github.com/CUBRID/cubrid/pull/8754#issuecomment-7162890085), gha-ci run https://github.com/CUBRID/cubrid/actions/runs/45617357842, `cubrid-ci-watch` request #109 |
