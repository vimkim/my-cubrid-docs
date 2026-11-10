# CBRD-27259 PR body revision 3 context

Prepared 2026-11-09 by another session; recorded and published 2026-11-11 (Asia/Seoul). Revision 2 and its record are in [pr-context-rev2.md](pr-context-rev2.md).

## Source and target

| Item | Value |
| --- | --- |
| Ticket | CBRD-27259 |
| Source commit | `6d6a01ef4599685d915e5183baf5d371feef42b4` (PR head; `abd2136f5` rejects every user-class record that would become `REC_BIGONE`, replacing the revision 2 notification) |
| Source repository and branch | `vimkim/cubrid`, `CBRD-27259-storage-force-inline` |
| Observed remote head | `6d6a01ef4599685d915e5183baf5d371feef42b4` (2026-11-11) |
| Base | `CUBRID/cubrid` `feature/oos-merge` (PR mergeable state on 2026-11-11: CONFLICTING) |
| Target repository | `CUBRID/cubrid` |
| Operation | `update` of https://github.com/CUBRID/cubrid/pull/8416 (open, ready for review) |
| Existing title | `[CBRD-27259] Add STORAGE FORCE_INLINE and fixed-type STORAGE DEFAULT` (unchanged) |
| Original GitHub body SHA-256 | `2ac1b9ffb6e4521cf466ef11b4c204293a08788d9f768891ba6a9d3c00415a23` (equal to `pr-body-rev2.md`) |

## Documents

| Item | Value |
| --- | --- |
| Docs task branch | `docs/CBRD-27259-pr-rev3` |
| Docs integration branch | `main` |
| Body | `cbrd-27259/pr-body-rev3.md` |
| Context | `cbrd-27259/pr-context-rev3.md` |

## Publication operations

1. Docs: rebase `docs/CBRD-27259-pr-rev3` onto local `main`, merge with `git merge --ff-only`, and push `main` to `origin`. Files: `cbrd-27259/README.md`, `cbrd-27259/pr-body-rev3.md`, `cbrd-27259/pr-context-rev3.md`.
2. PR: `gh pr edit 8416 --repo CUBRID/cubrid --body-file cbrd-27259/pr-body-rev3.md`, with no title, base, status, or source change.

## Open items

- The TC bullet still says the TC impact will follow the CI results. On 2026-11-11, run 42770278025 had `test_shell` and `test_medium` pass and `test_sql_by_cci` (7 shards) and `test_sql` shard 09 fail; run 42818558435 (`test_sql`) was queued. The `test_sql_by_cci` failures are not yet compared with the known `feature/oos-merge` failures (CBRD-28013).
- The PR conflicts with `feature/oos-merge`.

## Conversation record

- 2026-11-10: the user approved finishing and publishing revision 3 ("좋아. 승인"). The TC bullet was published unchanged because CI was not complete; the body describes the code at the PR head, and the live body described the replaced notification behavior.
