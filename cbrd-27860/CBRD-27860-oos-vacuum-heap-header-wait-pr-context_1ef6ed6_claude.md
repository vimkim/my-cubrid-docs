# CBRD-27860 PR publication context

This file records a publication proposal. It does not grant permission.

## Source and target

- Ticket is [CBRD-27860](https://jira.cubrid.org/browse/CBRD-27860). It was created on 2026-10-31 as a Sub-task of [CBRD-26583](https://jira.cubrid.org/browse/CBRD-26583), the same placement as R1 (CBRD-27827) and R5 (CBRD-27858), and assigned to `vimkim`. Status is Open. Priority is Minor, the default.
- Source repository is `vimkim/cubrid`.
- Source branch is `CBRD-27860-oos-vacuum-heap-header-wait`. It was renamed from `review/pr7990-hornet-r2` after ticket creation.
- Source commit is `1ef6ed6125eb6028c06b0e05282dc0041bde3f48`. Its parent is the test commit `7e48b1dac`, whose parent is the base. They replace `b5d53109a` and `e1d0aa65a`, which had the placeholder prefix `[CBRD-26357]`. Only the commit message prefix changed. Trees, authors and parent structure are identical, so the build, reproduction and CTest results apply unchanged.
- Source remote is `vk`. No push to the organization repository is proposed.
- Target repository is `CUBRID/cubrid`. Base branch is `feature/oos-merge`.
- Observed base commit is `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`, fetched on 2026-10-31.
- No R2 branch exists on `vk`. The open fork PRs to that base are 8348, 8347, 8330, 8299 and 8128, none for R2.
- Operation is create a new draft PR. Proposed assignee is `vimkim`.
- Proposed title is `[CBRD-27860] Fix vacuum latch cycle with heap page allocation`.
- No existing PR title, body fingerprint or draft state applies.

## Material

- Agent is `claude`.
- Docs task branch is `docs/pr7990-hornet-r2-20261031`. Integration branch is `main`.
- Body is `cbrd-27860/CBRD-27860-oos-vacuum-heap-header-wait-pr-body_1ef6ed6_claude.md`. It equals the reviewed placeholder draft except for the JIRA URL key.
- Context is this file. The ticket index is `cbrd-27860/README.md`.
- Superseded placeholder drafts remain in `cbrd-26357/` and are marked as superseded in `cbrd-26357/README.md`. The analysis report is `cbrd-26357/PR-7990-R2-vacuum-heap-header-deadlock_dcbf09e_codex.md`. The shared checklist is `cbrd-26357/PR-7990-hornetmj-review-checklist_20261029_codex.md`.
- No separate public explanation is linked by the body. The ticket contains the reproduction steps and the test diff.
- The JIRA report is `issues/CBRD-27860-oos-vacuum-heap-header-wait_dcbf09e_claude.md` in `vimkim/my-cubrid-jira`, with its index `README.md`. Notes task branch is `docs/pr7990-r2-issue-20261031`.
- Rediscover checkout paths with `git worktree list` when resuming.

## Ticket creation record, 2026-10-31

- Before creation, JQL searches under CBRD-26583 and over 14 days of vacuum, OOS and deadlock issues showed no R2 ticket. A recheck of sub-tasks created in the last day found only CBRD-27858. The shared link check passed.
- A dry-run with type Sub-task, parent CBRD-26583, assignee `vimkim`, the summary and the Markdown description resolved one `POST /rest/api/2/issue`. The live create returned CBRD-27860.
- Read-back matched the summary, type, parent, assignee and status. The stored description equaled the dry-run conversion exactly, 16018 characters, and the test diff block is intact.
- The description source file SHA256 is `1114e208bbd1b0b5826365d62dd90c752f9e87562553273f0c92ace6b909907f`. The renamed notes file has the same hash.

## Evidence and limits

- Baseline engine is `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`.
- Before the fix, the new test failed: vacuum held the last heap page while it queued on the heap header that the test held.
- A one-off run that called the real `heap_alloc_new_pages` in that state waited about 316 seconds, then got `ER_PAGE_LATCH_TIMEDOUT`. The debug build stopped at the `assert (0)` in `pgbuf_timed_sleep`. That code is not in the commits.
- After the fix, the new test passed. All 44 configured CTest tests passed in debug. All 44 also passed with R5's `628857607` applied on top, without committing it.
- Not run: `REC_RELOCATION` contention, release build, SQL-level INSERT, DELETE and vacuum load.

## Proposed operations

The ticket step is done. The publication step needs explicit approval:

1. Rebase the docs task onto current local `main`, audit every incoming path, fast-forward merge and push `main` to its configured origin.
2. Apply the same rebase, audit, fast-forward merge and push to the JIRA notes task. Its incoming paths are only the issue report and `README.md`. The live ticket already has the report; no JIRA rewrite, reassignment or workflow transition is proposed.
3. Push only `CBRD-27860-oos-vacuum-heap-header-wait` at `1ef6ed6125eb6028c06b0e05282dc0041bde3f48` to `vk` with a normal push. Stop on an unexpected remote tip.
4. Create one draft PR in `CUBRID/cubrid` with head `vimkim:CBRD-27860-oos-vacuum-heap-header-wait`, base `feature/oos-merge`, the proposed title, the exact reviewed body and assignee `vimkim`.

Not proposed: changes to PR 7990, review replies, thread resolution, reviewer requests, or a company CI trigger.
