# CBRD-28065 release/11.3 backport PR draft context

Resume metadata for `pr-body-11.3.md`. This file is not uploaded.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | CBRD-28065 (target version 11.3.7) |
| Source commit | `663f08e2c35153a07ddc1eb8790a7734b72d730a` |
| Source branch | `CBRD-28065-11.3` (local only. No remote branch was observed on `vk` on 2026-11-19.) |
| Base | `release/11.3` at `a4c752660bdf6dd9c30b6ac57798688c9dc7d48c` |
| Ported from | CUBRID/cubrid#8642 (develop head `9cc4cf8302`; verified as `a954b136cc`), applied without conflicts. The changed lines are identical. |
| Target repository | `CUBRID/cubrid` |
| Operation | create |
| Proposed title | `[CBRD-28065] [Backport-11.3.7] Keep a commit waiting until its log record is on disk` |
| Body | `cbrd-28065/pr-body-11.3.md` |
| Explanation | `cbrd-28065/verification.md` (shared with the develop PR) |
| Docs task branch | `docs/CBRD-28065-pr-drafts`, integration branch `main` |

## Edits made before publishing

- The body cites `develop PR #8642`, and the commit message says "Backport of CUBRID/cubrid#8642 (develop)".
- Rebased onto the current release tip before the push. The verified build used the previous base; the changed lines are identical, and the rebased tree was compiled.

## Proposed operations

1. Merge the docs task branch into `main` of `vimkim/my-cubrid-docs` and push it (shared with the develop draft).
2. Push `CBRD-28065-11.3` to `vk` and create a draft PR against `release/11.3`, assigned to `vimkim`.

The user confirmed these operations on 2026-11-19.

## Execution record

- 2026-11-19: pushed `CBRD-28065-11.3` to `vk`; the remote head equals `663f08e2c3`.
- 2026-11-19: created https://github.com/CUBRID/cubrid/pull/8644 (draft, base `release/11.3`, assignee `vimkim`). The published body equals `pr-body-11.3.md` apart from the trailing newline.

## Verification build on the preparing host

Debug build from a plain local clone at the source commit, because the branch's CMakeLists.txt reads .git/HEAD as a file (fails in a linked worktree); host workarounds: -include string (GCC 11 headers), -Wl,--allow-multiple-definition (cubrid_esql link with the host flex), WITH_JDBC=ON with the cubrid-jdbc submodule. These settings are local to the verification build and are not part of the change.
