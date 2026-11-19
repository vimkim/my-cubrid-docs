# CBRD-27841 PR context: remove RVREPL_OOS_DELETE

Resume metadata for [pr-body.md](pr-body.md). This file is not uploaded.

## Source and target

- Ticket: CBRD-27841
- `SOURCE_COMMIT`: `4ee2bc4ebb` after #8559 merged (earlier heads `9b366302dc`, `1d86f1d31b`; full SHA recorded below)
- Source: `vimkim/cubrid`, branch `CBRD-27841-drop-repl-oos-delete`
- Base: `CUBRID/cubrid` `feature/oos-merge` at `b43275e944` (#8559). Earlier bases `71993ddb63`, then `d25c9e8d20` (#8638)
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

Recorded 2026-11-19, Asia/Seoul.

- Docs: `main` pushed at `341282e`, then `f27cad9` after the source rebase. The public `verification.md` matched the local file (SHA-256).
- Source: `vk` `CBRD-27841-drop-repl-oos-delete` = `1d86f1d31b4a30efead5e789ab8bf03f357c4d3f`. `feature/oos-merge` moved to `d25c9e8d20` (#8638) during the work; the patch was rebased unchanged (range-diff `=`).
- PR: [#8646](https://github.com/CUBRID/cubrid/pull/8646), draft, base `feature/oos-merge`, assignee `vimkim`. The live body equals `pr-body.md` (SHA-256 of the text without a trailing newline: `3ed738eabacc273bb44960c2376746f3abf7edf87334574e903e3fdc594da562`).
- TC PRs opened by TC Branch Sync, empty: [cubrid-testcases#4342](https://github.com/CUBRID/cubrid-testcases/pull/4342), [cubrid-testcases-private-ex#5033](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5033). `cubrid-pr-tc-base-check` passed for both.
- CI: `/run all` at 2026-11-19T09:57:40Z ([comment](https://github.com/CUBRID/cubrid/pull/8646#issuecomment-7005770190)), run [44501180486](https://github.com/CUBRID/cubrid/actions/runs/44501180486), six `gha-ci` contexts pending at pickup. `cubrid-ci-watch` request 77.
- JIRA: CBRD-27841 description published from `my-cubrid-jira` `2ae28ed`; the live description equals the dry-run payload. Summary, status and assignee unchanged.
