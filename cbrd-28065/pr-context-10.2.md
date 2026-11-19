# CBRD-28065 release/10.2 backport PR draft context

Resume metadata for `pr-body-10.2.md`. This file is not uploaded.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | CBRD-28065 (target version 10.2.20) |
| Source commit | `4f0f0c410889e58173592950d45bf346f014c833` |
| Source branch | `CBRD-28065-10.2` (local only. No remote branch was observed on `vk` on 2026-11-19.) |
| Base | `release/10.2` at `45e25f1d35a6596a77fdac218c19ad4272c126ba` |
| Ported from | CUBRID/cubrid#8642 (develop head `9cc4cf8302`; verified as `a954b136cc`), applied without conflicts. The changed lines are identical. |
| Target repository | `CUBRID/cubrid` |
| Operation | create |
| Proposed title | `[CBRD-28065] [Backport-10.2.20] Keep a commit waiting until its log record is on disk` |
| Body | `cbrd-28065/pr-body-10.2.md` |
| Explanation | `cbrd-28065/verification.md` (shared with the develop PR) |
| Docs task branch | `docs/CBRD-28065-pr-drafts`, integration branch `main` |

## Edits made before publishing

- The body cites `develop PR #8642`, and the commit message says "Backport of CUBRID/cubrid#8642 (develop)".
- Rebased onto the current release tip before the push. The verified build used the previous base; the changed lines are identical, and the rebased tree was compiled.

## Proposed operations

1. Merge the docs task branch into `main` of `vimkim/my-cubrid-docs` and push it (shared with the develop draft).
2. Push `CBRD-28065-10.2` to `vk` and create a draft PR against `release/10.2`, assigned to `vimkim`.

The user confirmed these operations on 2026-11-19.

## Verification build on the preparing host

Debug build with the Makefile generator (as build.sh does) and CMAKE_DISABLE_FIND_PACKAGE_Git=TRUE (.git/HEAD read as a file); host workarounds: AWK='gawk --traditional' for the bundled libgpg-error 1.27, GCRYPT_LIBRARIES pointed at the bundled libgcrypt.a so HAVE_LIBGCRYPT is set, -include string -include cstdlib, -Wl,--allow-multiple-definition. These settings are local to the verification build and are not part of the change.
