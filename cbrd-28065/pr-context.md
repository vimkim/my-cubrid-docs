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
- Merge order: this PR first. The three backport drafts cite it as `develop PR #8642`.

## Execution record

- 2026-11-19: docs `main` fast-forwarded to `619aa1c` and pushed. The public `verification.md` matched the reviewed SHA-256 `82b6968340ed3968494984067abb89c2d7e265e2866b3208bb5509ef08543dc4`.
- 2026-11-19: pushed `CBRD-28065-commit-durability` to `vk`; the remote head equals `9cc4cf8302a857c65a2d93cfde69300a02e586e7`.
- 2026-11-19: created https://github.com/CUBRID/cubrid/pull/8642 (draft, base `develop`, assignee `vimkim`). The published body equals `pr-body.md` (SHA-256 `5c4611ba0e76e385f02e65bcd633707ff0eeed099890a5633618fb0dc2b755f0`) apart from the trailing newline. `TC Branch Sync` created `tc/pr-8642`.
- 2026-11-19: posted JIRA comment 4778794 on CBRD-28065 with the four PR links and the verification summary.
