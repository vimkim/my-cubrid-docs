# CBRD-28065 develop PR draft context

Resume metadata for `pr-body.md`. This file is not uploaded.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | CBRD-28065 |
| Source commit | `9cc4cf8302a857c65a2d93cfde69300a02e586e7` (the verified commit `a954b136cc65601afb3f8674ffbfdc5f80266695`, rebased without conflicts. The changed lines are identical.) |
| Source branch | `CBRD-28065-commit-durability` (local only. No remote branch was observed on `vk` on 2026-11-19.) |
| Base | `develop` at `1ecb2e7f37` for publication. Verification builds used base `86b3c49c1045db26acd1276095dbceb3bfb3f227`. |
| Target repository | `CUBRID/cubrid` |
| Operation | create |
| Proposed title | `[CBRD-28065] Keep a commit waiting until its log record is on disk` |
| Body | `cbrd-28065/pr-body.md` |
| Explanation | `cbrd-28065/verification.md`, public URL `https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-28065/verification.md` |
| Docs task branch | `docs/CBRD-28065-pr-drafts`, integration branch `main` |

## Proposed operations

1. Merge the docs task branch into `main` of `vimkim/my-cubrid-docs` and push it, so the explanation link resolves.
2. Push `CBRD-28065-commit-durability` to `vk` (`github.com/vimkim/cubrid`).
3. Create the PR against `develop` as a draft, assigned to `vimkim`.

The user confirmed these operations on 2026-11-19, together with the listed defaults (draft PR, rebase onto the current `origin/develop` before the push), a shell TC on `tc/pr-<number>`, and a JIRA comment after the PR exists.

## Notes for review

- The develop tip `86b3c49c10` (and `1ecb2e7f37`) does not build on the preparing host without `#include <ctype.h>` in `src/broker/cas_cgw_odbc.c` (`toupper`/`tolower` lost a transitive include after `8e6c51784e`). The local verification builds used that one-line include, uncommitted. It is not part of this PR. develop CI built `1ecb2e7f37` successfully (gha-ci push run, 2026-11-19), so the failure is specific to the preparing host.
- `cubrid-static-check 86b3c49c10 a954b136cc`: cppcheck 0 new, PMD CPD 0 new, lizard 0 flags (`logpb_flush_pages` CCN 18, length 114 to 109). clang-tidy (`bugprone-*`) was incomplete: it exited 1 on `log_page_buffer.c` for both base and head, and 4 head findings were not compared. Disposition: a direct `clang-tidy --checks='-*,bugprone-*'` run on the head file reports 81 findings file-wide and none in `logpb_flush_pages` (lines 4076 to 4185), so none comes from this change.
- Merge order: this PR first. The three backport drafts (`pr-body-11.4.md`, `pr-body-11.3.md`, `pr-body-10.2.md`) reference it as `develop PR #NNNN`; fill in the number before publishing them.
