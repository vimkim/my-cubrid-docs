# CBRD-27259 PR body revision 4 context

Prepared and published 2026-11-11 (Asia/Seoul). Revision 3 and its record are in [pr-context-rev3.md](pr-context-rev3.md).

## Source and target

| Item | Value |
| --- | --- |
| Ticket | CBRD-27259 |
| Source commit | `89496263e` (test fix on top of merge `5d7cdcb68`, which brought in `feature/oos-merge` and moved the record-size message to 1396) |
| Source repository and branch | `vimkim/cubrid`, `CBRD-27259-storage-force-inline` |
| Base | `CUBRID/cubrid` `feature/oos-merge` (MERGEABLE after `5d7cdcb68`) |
| Target | update of https://github.com/CUBRID/cubrid/pull/8416 (open, ready for review); title unchanged |
| Original GitHub body | revision 3 (`pr-body-rev3.md`; the live text differed only by GitHub's dropped trailing blank line) |

## Changes from revision 3

- Message 1388 is now 1396 after the base renumbering.
- New remark: the rejection also applies to `loaddb`, so `unloaddb` then `loaddb` of a database that holds `REC_BIGONE` rows rejects those rows; `test_oos_workspace` now expects that.
- The TC bullet links the TC PRs (cubrid-testcases #4046, cubrid-testcases-private-ex #4753). The CI result is still open.

## Operations

1. Docs: task branch `docs/CBRD-27259-pr-rev4`, fast-forward into `main`, push. Files: `cbrd-27259/README.md`, `cbrd-27259/pr-body-rev4.md`, `cbrd-27259/pr-context-rev4.md`.
2. PR: `gh pr edit 8416 --repo CUBRID/cubrid --body-file cbrd-27259/pr-body-rev4.md`.

## Conversation record

- 2026-11-11: the user approved option (a) for the loader test, the source push, `/run all`, and the body update ("yes").
- `/run all` was not posted: another session posted `/run all` at 2026-11-10T16:07:59Z (run 42851484010, watch #11), and a new `/run` would cancel it. That decision went back to the user.
