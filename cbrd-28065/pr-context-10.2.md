# CBRD-28065 release/10.2 backport PR draft context

Resume metadata for `pr-body-10.2.md`. This file is not uploaded.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | CBRD-28065 (target version 10.2.20) |
| Source commit | `e448549f3317cc6f1f61c60ebcd688bc81d64057` |
| Source branch | `CBRD-28065-10.2` (local only. No remote branch was observed on `vk` on 2026-11-19.) |
| Base | `release/10.2` at `45e25f1d35a6596a77fdac218c19ad4272c126ba` |
| Ported from | develop commit `a954b136cc65601afb3f8674ffbfdc5f80266695` (local), applied without conflicts. The changed lines are identical. |
| Target repository | `CUBRID/cubrid` |
| Operation | create |
| Proposed title | `[CBRD-28065] [Backport-10.2.20] Keep a commit waiting until its log record is on disk` |
| Body | `cbrd-28065/pr-body-10.2.md` |
| Explanation | `cbrd-28065/verification.md` (shared with the develop PR) |
| Docs task branch | `docs/CBRD-28065-pr-drafts`, integration branch `main` |

## Required edits before publishing

- Replace `develop PR #NNNN` in the body with the develop PR number.
- The commit message says "Backport of develop commit a954b136cc (local; replace with the develop PR number once it merges)". Amend it with the develop PR number before pushing.

## Proposed operations (not authorized yet)

1. Merge the docs task branch into `main` of `vimkim/my-cubrid-docs` and push it (shared with the develop draft).
2. After the develop PR exists, push `CBRD-28065-10.2` to `vk` and create the PR against `release/10.2`, assigned to `vimkim`. The kickoff for this draft said not to push or open any PR.

## Verification build on the preparing host

Debug build with the Makefile generator (as build.sh does) and CMAKE_DISABLE_FIND_PACKAGE_Git=TRUE (.git/HEAD read as a file); host workarounds: AWK='gawk --traditional' for the bundled libgpg-error 1.27, GCRYPT_LIBRARIES pointed at the bundled libgcrypt.a so HAVE_LIBGCRYPT is set, -include string -include cstdlib, -Wl,--allow-multiple-definition. These settings are local to the verification build and are not part of the change.
