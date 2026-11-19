# CBRD-28065 release/11.3 backport PR draft context

Resume metadata for `pr-body-11.3.md`. This file is not uploaded.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | CBRD-28065 (target version 11.3.7) |
| Source commit | `f3e25e9986e4a6cf591336e5a9be1da6ba61c1f6` |
| Source branch | `CBRD-28065-11.3` (local only. No remote branch was observed on `vk` on 2026-11-19.) |
| Base | `release/11.3` at `15360995b554ccc1c2b562fff71f5f44fe14977c` |
| Ported from | develop commit `a954b136cc65601afb3f8674ffbfdc5f80266695` (local), applied without conflicts. The changed lines are identical. |
| Target repository | `CUBRID/cubrid` |
| Operation | create |
| Proposed title | `[CBRD-28065] [Backport-11.3.7] Keep a commit waiting until its log record is on disk` |
| Body | `cbrd-28065/pr-body-11.3.md` |
| Explanation | `cbrd-28065/verification.md` (shared with the develop PR) |
| Docs task branch | `docs/CBRD-28065-pr-drafts`, integration branch `main` |

## Required edits before publishing

- Replace `develop PR #NNNN` in the body with the develop PR number.
- The commit message says "Backport of develop commit a954b136cc (local; replace with the develop PR number once it merges)". Amend it with the develop PR number before pushing.

## Proposed operations (not authorized yet)

1. Merge the docs task branch into `main` of `vimkim/my-cubrid-docs` and push it (shared with the develop draft).
2. After the develop PR exists, push `CBRD-28065-11.3` to `vk` and create the PR against `release/11.3`, assigned to `vimkim`. The kickoff for this draft said not to push or open any PR.

## Verification build on the preparing host

Debug build from a plain local clone at the source commit, because the branch's CMakeLists.txt reads .git/HEAD as a file (fails in a linked worktree); host workarounds: -include string (GCC 11 headers), -Wl,--allow-multiple-definition (cubrid_esql link with the host flex), WITH_JDBC=ON with the cubrid-jdbc submodule. These settings are local to the verification build and are not part of the change.
