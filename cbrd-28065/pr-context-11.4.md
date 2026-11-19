# CBRD-28065 release/11.4 backport PR draft context

Resume metadata for `pr-body-11.4.md`. This file is not uploaded.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | CBRD-28065 (target version 11.4.8) |
| Source commit | `3682d2708bf48ef465c37df9ae9028fe8c7d92ee` |
| Source branch | `CBRD-28065-11.4` (local only. No remote branch was observed on `vk` on 2026-11-19.) |
| Base | `release/11.4` at `28b98c349689974eca3f92a34b0470028194daf4` |
| Ported from | develop commit `a954b136cc65601afb3f8674ffbfdc5f80266695` (local), applied without conflicts. The changed lines are identical. |
| Target repository | `CUBRID/cubrid` |
| Operation | create |
| Proposed title | `[CBRD-28065] [Backport-11.4.8] Keep a commit waiting until its log record is on disk` |
| Body | `cbrd-28065/pr-body-11.4.md` |
| Explanation | `cbrd-28065/verification.md` (shared with the develop PR) |
| Docs task branch | `docs/CBRD-28065-pr-drafts`, integration branch `main` |

## Required edits before publishing

- Replace `develop PR #NNNN` in the body with the develop PR number.
- The commit message says "Backport of develop commit a954b136cc (local; replace with the develop PR number once it merges)". Amend it with the develop PR number before pushing.

## Proposed operations (not authorized yet)

1. Merge the docs task branch into `main` of `vimkim/my-cubrid-docs` and push it (shared with the develop draft).
2. After the develop PR exists, push `CBRD-28065-11.4` to `vk` and create the PR against `release/11.4`, assigned to `vimkim`. The kickoff for this draft said not to push or open any PR.

## Verification build on the preparing host

debug_gcc preset build. These settings are local to the verification build and are not part of the change.
