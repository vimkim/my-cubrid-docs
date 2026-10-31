# CBRD-XXXXX PR publication context (R2, before ticket issuance)

This file records a publication proposal. It does not grant permission.

## Source and target

- Ticket is not issued yet. The proposal is a Sub-task of [CBRD-26583](https://jira.cubrid.org/browse/CBRD-26583), the same placement as R1 (CBRD-27827) and R5 (CBRD-27858), assigned to `vimkim`.
- On 2026-10-31 a JQL search under CBRD-26583 and over the last 14 days of vacuum, OOS and deadlock issues found no R2 ticket. [CBRD-27723](https://jira.cubrid.org/browse/CBRD-27723), which PR 8235 fixes, is a different deadlock.
- Source repository is `vimkim/cubrid`. Source branch is `review/pr7990-hornet-r2`. It will be renamed `CBRD-NNNNN-oos-vacuum-heap-header-wait` after ticket issuance.
- Source commit is `b5d53109a3404aa7c3c68fc865ccb47551b139bf`. Its parent is the test commit `e1d0aa65a`, whose parent is the base `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`. Both commits use the placeholder prefix `[CBRD-26357]`. A reword after ticket issuance changes only the commit messages, so the trees and test results stay valid.
- Source remote is `vk`. No push to the organization repository is proposed.
- Target repository is `CUBRID/cubrid`. Base branch is `feature/oos-merge`. Observed base commit is `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`, fetched on 2026-10-31.
- No R2 branch exists on `vk`. The open fork PRs to that base are 8348, 8347, 8330, 8299 and 8128, none for R2.
- Operation is create a new draft PR. Proposed assignee is `vimkim`.
- Proposed title is `[CBRD-XXXXX] Fix vacuum latch cycle with heap page allocation`.

## Material

- Agent is `claude`.
- Docs task branch is `docs/pr7990-hornet-r2-20261031`. Integration branch is `main`.
- Body is `cbrd-26357/CBRD-XXXXX-oos-vacuum-heap-header-wait-pr-body_b5d5310_claude.md`. Context is this file. After ticket issuance both move to `cbrd-NNNNN/` with the real key and the reworded commit's short SHA.
- No separate public explanation is linked by the body. The JIRA description carries the reproduction steps and the test diff.
- The JIRA report draft is `issues/CBRD-XXXXX-oos-vacuum-heap-header-wait_dcbf09e_claude.md` in `vimkim/my-cubrid-jira`, with its index `README.md`. Notes task branch is `docs/pr7990-r2-issue-20261031`.
- The analysis report is `cbrd-26357/PR-7990-R2-vacuum-heap-header-deadlock_dcbf09e_codex.md`. The shared checklist is `cbrd-26357/PR-7990-hornetmj-review-checklist_20261029_codex.md`.
- Rediscover checkout paths with `git worktree list` when resuming.

## Evidence and limits

- Before the fix, the new test failed: vacuum held the last heap page while it queued on the heap header that the test held.
- A one-off run that called the real `heap_alloc_new_pages` in that state waited about 316 seconds, then got `ER_PAGE_LATCH_TIMEDOUT`. The debug build stopped at the `assert (0)` in `pgbuf_timed_sleep`. That code is not in the commits.
- After the fix, the new test passed. All 44 configured CTest tests passed in debug. All 44 also passed with R5's `628857607` applied on top, without committing it.
- Not run: `REC_RELOCATION` contention, release build, SQL-level INSERT, DELETE and vacuum load.

## Proposed operations

These need explicit approval in two steps.

Ticket step:

1. Create a Sub-task under CBRD-26583 with assignee `vimkim`, the report title as summary and the report as description. Show the `cubrid-jira create` dry-run first.
2. Rename the local source branch to `CBRD-NNNNN-oos-vacuum-heap-header-wait` and reword both commit prefixes to `[CBRD-NNNNN]`.
3. Rename the report and these drafts to the real key, move the drafts to `cbrd-NNNNN/`, and add a `cbrd-NNNNN/README.md` index.

Publication step:

1. Rebase the docs task onto current local `main`, fast-forward merge and push `main` to its configured origin.
2. Do the same for the JIRA notes task.
3. Push only `CBRD-NNNNN-oos-vacuum-heap-header-wait` to `vk` with a normal push.
4. Create one draft PR in `CUBRID/cubrid` with head `vimkim:CBRD-NNNNN-oos-vacuum-heap-header-wait`, base `feature/oos-merge`, the proposed title, the reviewed body and assignee `vimkim`.

Not proposed: changes to PR 7990, review replies, thread resolution, reviewer requests, or a company CI trigger.
