# CBRD-27259 PR draft context

Prepared 2026-11-05 (Asia/Seoul). This file records the proposal. It is not an approval record.

## Source and target

| Item | Value |
| --- | --- |
| Ticket | CBRD-27259 |
| Source commit | `e19d8c613c581cde2350474fe3451c60ecb04c66` |
| Source repository and branch | `vimkim/cubrid` (remote `vk`), `CBRD-27259-storage-force-inline` |
| Observed remote head | Branch absent on `vk` (2026-11-05 `git ls-remote`) |
| Base | `CUBRID/cubrid` `feature/oos-merge`, tip `d52b1889e` (source commit's parent) |
| Target repository | `CUBRID/cubrid` |
| Operation | `create` (no open PR for this head branch on 2026-11-05) |
| Proposed title | `[CBRD-27259] Add STORAGE FORCE_INLINE and fixed-type STORAGE DEFAULT` |

## Documents

| Item | Value |
| --- | --- |
| Docs task branch | `docs/CBRD-27259-pr` |
| Docs integration branch | `main` |
| Body | `cbrd-27259/pr-body.md` |
| Context | `cbrd-27259/pr-context.md` |
| Detailed explanation | None |

## Proposed publication operations

1. Docs: rebase `docs/CBRD-27259-pr` onto local `main`, merge with `git merge --ff-only`, and push `main` to `origin` (`vimkim/my-cubrid-docs`). Files: `cbrd-27259/README.md`, `cbrd-27259/pr-body.md`, `cbrd-27259/pr-context.md`.
2. Source: `git push -u vk CBRD-27259-storage-force-inline` at the source commit above.
3. PR: create a draft PR in `CUBRID/cubrid` from `vimkim:CBRD-27259-storage-force-inline` into `feature/oos-merge`, with the proposed title, `cbrd-27259/pr-body.md` as the body, and assignee `vimkim`.

After the PR exists, the standing CUBRID PR instruction covers one CI trigger. No TC changes are planned, so the TC PRs created by TC Branch Sync are left for the user to close.

## Conversation record

- 2026-11-05: the user chose the draft PR route over a local merge ("1. 좋아"). Publication of this body still needs the user's confirmation after review.
- 2026-11-05: after review, the user approved the three listed operations ("1. 승인").

## Publication record

| Step | Result (2026-11-05) |
| --- | --- |
| Body fingerprint (SHA-256) | `8894bd68e1609b87d5bbb5df4d3877d24362bb8361212a3c6f81e136d356d259` |
| Source push | `vk/CBRD-27259-storage-force-inline` = `e19d8c613c581cde2350474fe3451c60ecb04c66` |
| Draft PR | https://github.com/CUBRID/cubrid/pull/8416, draft, base `feature/oos-merge`, assignee `vimkim` |
| Body check | Published body is byte-identical to `cbrd-27259/pr-body.md` |
| Docs integration | This commit, merged into `main` and pushed after the PR write |
