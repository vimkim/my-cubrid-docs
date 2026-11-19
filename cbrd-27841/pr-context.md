# CBRD-27841 PR context: remove RVREPL_OOS_DELETE

Resume metadata for [pr-body.md](pr-body.md). This file is not uploaded.

## Source and target

- Ticket: CBRD-27841
- `SOURCE_COMMIT`: `1d86f1d31b4a30efead5e789ab8bf03f357c4d3f` (rebased from `9b366302dc` with an identical patch; full SHA recorded at publication below)
- Source: `vimkim/cubrid`, branch `CBRD-27841-drop-repl-oos-delete`
- Base: `CUBRID/cubrid` `feature/oos-merge` at `d25c9e8d20a0ef422b0878f00b91279243d7238d` (moved from `71993ddb63` by #8638 during the work)
- Remote head before publication: branch absent on `vk`
- Operation: create a draft PR
- Proposed title: `[CBRD-27841] Remove the unused recovery index RVREPL_OOS_DELETE`
- Docs task branch: `docs/cbrd-27841-repl-oos-delete-20261119`, integrated into `main`
- Files: `cbrd-27841/pr-body.md`, `cbrd-27841/pr-context.md`, `cbrd-27841/verification.md`, `cbrd-27841/README.md`

## Proposed operations

1. Commit the docs files, rebase onto local `main`, fast-forward `main`, push `main` to `origin`.
2. Push `CBRD-27841-drop-repl-oos-delete` to the `vk` remote.
3. `gh pr create --repo CUBRID/cubrid --draft --base feature/oos-merge --head vimkim:CBRD-27841-drop-repl-oos-delete --assignee vimkim` with the title above and `pr-body.md`.

## Authorization

The operator's kickoff of 2026-11-19 (brief `brief-CBRD-27841.md`, "Authorized end point" item 2) authorizes the local commit, the push to `vk`, and a draft PR into `feature/oos-merge` created with this skill, and states that it is the explicit confirmation the skill needs. It does not authorize merging, comments to reviewers, or changes to #8559 or #7990.

## History

- #8347 (closed 2026-11-05, unmerged) removed `RVOOS_NOTIFY_VACUUM`, which #8434 later made live. Its drafts are the `e523d4f` and `eac70c7` files in this directory. This PR does not reuse them.

## Publication record

(Filled in after publication.)
