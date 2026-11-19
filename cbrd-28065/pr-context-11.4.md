# CBRD-28065 release/11.4 backport PR draft context

Resume metadata for `pr-body-11.4.md`. This file is not uploaded.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | CBRD-28065 (target version 11.4.8) |
| Source commit | `3a9eae91f034586d6a946d2a5c5b96de987e8aca` |
| Source branch | `CBRD-28065-11.4` (local only. No remote branch was observed on `vk` on 2026-11-19.) |
| Base | `release/11.4` at `82957b8f4135be1616a4407e6d273e0dfaf1aee0` |
| Ported from | CUBRID/cubrid#8642 (develop head `9cc4cf8302`; verified as `a954b136cc`), applied without conflicts. The changed lines are identical. |
| Target repository | `CUBRID/cubrid` |
| Operation | create |
| Proposed title | `[CBRD-28065] [Backport-11.4.8] Keep a commit waiting until its log record is on disk` |
| Body | `cbrd-28065/pr-body-11.4.md` |
| Explanation | `cbrd-28065/verification.md` (shared with the develop PR) |
| Docs task branch | `docs/CBRD-28065-pr-drafts`, integration branch `main` |

## Edits made before publishing

- The body cites `develop PR #8642`, and the commit message says "Backport of CUBRID/cubrid#8642 (develop)".
- Rebased onto the current release tip before the push. The verified build used the previous base; the changed lines are identical, and the rebased tree was compiled.

## Proposed operations

1. Merge the docs task branch into `main` of `vimkim/my-cubrid-docs` and push it (shared with the develop draft).
2. Push `CBRD-28065-11.4` to `vk` and create a draft PR against `release/11.4`, assigned to `vimkim`.

The user confirmed these operations on 2026-11-19.

## Execution record

- 2026-11-19: pushed `CBRD-28065-11.4` to `vk`; the remote head equals `3a9eae91f0`.
- 2026-11-19: created https://github.com/CUBRID/cubrid/pull/8643 (draft, base `release/11.4`, assignee `vimkim`). The published body equals `pr-body-11.4.md` apart from the trailing newline.

## Verification build on the preparing host

debug_gcc preset build. These settings are local to the verification build and are not part of the change.
