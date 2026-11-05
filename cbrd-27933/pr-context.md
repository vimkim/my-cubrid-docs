# CBRD-27933 PR draft context

- Ticket: CBRD-27933
- Source commit: `80d6e721edebf11331e97eed6eae58dbaa2e10d6`
- Source repository and branch: `vimkim/cubrid` (remote `vk`), `CBRD-27933-vacuum-oos-vfid-lookup-error`. Not pushed yet (no remote branch observed on 2026-11-05).
- Base: `CUBRID/cubrid` `feature/oos-merge` at `d52b1889e907abcf84190ec504dde3bc93de260d`
- Target repository: `CUBRID/cubrid`. Operation: create. No existing PR.
- Proposed title: `[CBRD-27933] Fix OOS leak when vacuum cannot find the OOS file`
- Docs task branch: `docs/CBRD-27933-formal-20261105`, integration branch `main`.
- Body: `cbrd-27933/pr-body.md`. Context: `cbrd-27933/pr-context.md`. Linked explanation: `cbrd-27933/fix-decisions.md`, public URL `https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27933/fix-decisions.md`.

## Proposed operations

1. Rebase the docs task branch on `main`, merge it with `git merge --ff-only`, and push `main` to `origin` (files: `cbrd-27933/README.md`, `fix-decisions.md`, `reviewer-reply-draft.md`, `pr-body.md`, `pr-context.md`).
2. Push `CBRD-27933-vacuum-oos-vfid-lookup-error` at the source commit to `vk`.
3. Create a draft PR from `vimkim:CBRD-27933-vacuum-oos-vfid-lookup-error` into `CUBRID:feature/oos-merge` with the body file and the proposed title, assigned to `vimkim`.
4. After creation, trigger CUBRID CI once and report its result (standing authorization in the personal CUBRID instructions).

## Decisions recorded

- 2026-11-05: the user chose to open the draft PR after the fix round without waiting for the team lead, to keep the fixed 1 s re-run gate, and to keep the new error code -1393.
