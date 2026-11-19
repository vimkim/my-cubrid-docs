# CBRD-28023 PR draft context

Prepared 2026-11-19 (Asia/Seoul). This file records the proposal. It is not an approval record.

## Source and target

| Item | Value |
| --- | --- |
| Ticket | CBRD-28023 |
| Source commit | `9551b59ed032ed4aac572427be9766b0445fcd61` |
| Source repository and branch | `vimkim/cubrid` (remote `vk`), `CBRD-28023-oos-file-type-name` |
| Observed remote head | Branch absent on `vk` (2026-11-19 `git ls-remote`) |
| Base | `CUBRID/cubrid` `feature/oos-merge`, tip `71993ddb63` (source commit's parent) |
| Target repository | `CUBRID/cubrid` |
| Operation | `create` (no PR with CBRD-28023 in its title on 2026-11-19) |
| Proposed title | `[CBRD-28023] Rename the diagdb OOS file type to OOS` |

## Testcase change

| Item | Value |
| --- | --- |
| Repository | `CUBRID/cubrid-testcases-private-ex` |
| Local branch | `CBRD-28023-oos-file-type-name`, commit `11ffb00ae522441c09940fd708951c57e78b3a86` |
| Base | `origin/feature/oos-merge` `9b3455bd2` |
| Files | `shell/_36_damson/cbrd_23608_tde/tbl_enc_08/cases/result.answer`, `shell/_36_damson/cbrd_23608_tde/tbl_enc_14/cases/result.answer`, `shell/_06_issues/_26_1h/cbrd_26527/cases/cbrd_26527.sh` (comments only) |
| `CUBRID/cubrid-testcases` | No change. `origin/feature/oos-merge` `5720a6a24` has no old string |

## Documents

| Item | Value |
| --- | --- |
| Docs task branch | `CBRD-28023-pr-draft` |
| Docs integration branch | `main` |
| Body | `cbrd-28023/pr-body.md` |
| Context | `cbrd-28023/pr-context.md` |
| Detailed explanation | None |

## Proposed publication operations

1. Docs: rebase `CBRD-28023-pr-draft` onto local `main`, merge with `git merge --ff-only`, and push `main` to `origin` (`vimkim/my-cubrid-docs`). Files: `cbrd-28023/README.md`, `cbrd-28023/pr-body.md`, `cbrd-28023/pr-context.md`.
2. Source: `git push -u vk CBRD-28023-oos-file-type-name` at the source commit above.
3. PR: create a draft PR in `CUBRID/cubrid` from `vimkim:CBRD-28023-oos-file-type-name` into `feature/oos-merge`, with the proposed title, `cbrd-28023/pr-body.md` as the body, and assignee `vimkim`.
4. TC: TC Branch Sync creates `tc/pr-<N>` in both testcase repositories from `feature/oos-merge` and adds an empty init commit. In `cubrid-testcases-private-ex`, cherry-pick `11ffb00ae` onto `origin/tc/pr-<N>` and push it to `origin` as a fast-forward. Keep both TC PRs open until the final merge handoff.

## Name choice

The issue suggested `OUT_OF_ROW_OVERFLOW_STORAGE` as an example and left the final string to analysis. `OOS` was chosen because:

- The other `file_type_to_string` names drop the `FILE_` prefix from the enum.
- diagdb already prints `OOS for HFID`, SQL has `SHOW HEAP OOS`, and CBRD-27350 plans an `OOS` row in `cubrid spacedb`. CBRD-28023 asks to align with CBRD-27350.
- The `diagdb -d2` file list pads the type to 22 characters (`%-22s`). The longest other name has 21. A 27-character name shifts its row.

Switching to the long form later is one engine line and two answer lines.

## Verification (2026-11-19)

| Check | Result |
| --- | --- |
| Build and install, `debug_gcc` preset | Pass at the source commit |
| `cubrid diagdb -d1` on a database with an out-of-row 20,000-byte value | Prints `type = OOS` and `OOS for HFID` |
| `cubrid diagdb -d2` | `OOS` row aligned with the other rows |
| `tbl_enc_08`, `tbl_enc_14` with native cubrid-testkit under containment | Each total 1, success 1, fail 0. Engine `9551b59`, testcases `11ffb00ae` |
| Old string in engine tree and `cubrid-testcases-private-ex` branch | None |

The optional `cubrid-static-check` run was skipped. The change replaces one string literal.

## Conversation record

- 2026-11-19: the operator's kickoff limits this run to local commits and this draft. It says not to push any branch and not to open any PR. Publication needs the user's confirmation after review.
