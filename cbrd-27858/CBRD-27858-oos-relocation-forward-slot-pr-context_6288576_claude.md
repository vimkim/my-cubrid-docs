# CBRD-27858 PR publication context

This file records a publication proposal. It does not grant permission.

## Source and target

- Ticket is [CBRD-27858](https://jira.cubrid.org/browse/CBRD-27858). It was created on 2026-10-30 as a Sub-task of [CBRD-26583](https://jira.cubrid.org/browse/CBRD-26583), the same placement as R1 (CBRD-27827), and assigned to `vimkim`. Status is Open. Priority is Minor, the default.
- Source repository is `vimkim/cubrid`.
- Source branch is `CBRD-27858-oos-relocation-forward-slot`. It was renamed from `pr7990-hornet-r5` after ticket creation.
- Source commit is `628857607265880ef7bbdda4973b1b6f06e8b797`. It replaces `c05abc8b4559ff1fa5db54f2a646d866f37156fc`, which had the placeholder prefix `[CBRD-26357]`. Only the commit message prefix changed. Tree and parent are identical, so the build, reproduction and CTest results of `c05abc8b4` apply unchanged.
- Source remote is `vk`. No push to the organization repository is proposed.
- Target repository is `CUBRID/cubrid`. Base branch is `feature/oos-merge`.
- Observed base commit is `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`, fetched on 2026-10-30. The source commit's parent is this base.
- The source branch is absent on `vk`. No PR mentions CBRD-27858. The open fork PRs to that base are 8330, 8299 and 8128, none for R5.
- Operation is create a new draft PR. Proposed assignee is `vimkim`.
- Proposed title is `[CBRD-27858] Fix vacuum undo that overwrites a reused forward slot`.
- No existing PR title, body fingerprint or draft state applies.

## Material

- Agent is `claude`.
- Docs task branch is `docs/pr7990-hornet-r5-pr-20261030`. Integration branch is `main`.
- Body is `cbrd-27858/CBRD-27858-oos-relocation-forward-slot-pr-body_6288576_claude.md`. It equals the reviewed placeholder draft except for the JIRA URL key.
- Context is `cbrd-27858/CBRD-27858-oos-relocation-forward-slot-pr-context_6288576_claude.md`. The ticket index is `cbrd-27858/README.md`.
- Superseded placeholder drafts remain in `cbrd-26357/` and are marked as superseded in `cbrd-26357/README.md`. The shared checklist is `cbrd-26357/PR-7990-hornetmj-review-checklist_20261029_codex.md`.
- No separate public explanation is linked by the body. The ticket contains the reproduction steps, the reproduction-only hook and the driver.
- The JIRA report is `issues/CBRD-27858-oos-relocation-forward-slot-undo_dcbf09e_claude.md` in `vimkim/my-cubrid-jira`, with its index `README.md`. Notes task branch is `docs/pr7990-r5-issue-20261030`, commits `cd1bd26` and `00bda65`.
- Rediscover checkout paths with `git worktree list` when resuming.

## Ticket creation record, 2026-10-30

- Before creation, a JQL search under CBRD-26583 showed no new R5 ticket. The shared link check passed.
- A dry-run with type Sub-task, parent CBRD-26583, assignee `vimkim`, the summary and the Markdown description resolved one `POST /rest/api/2/issue`. The live create returned CBRD-27858.
- Read-back matched the summary, type, parent, assignee and status. The stored description equaled the dry-run conversion exactly, 24516 characters.
- The rendered description showed all 15 headings. The hook diff and the driver code blocks matched their source files exactly.
- The description source file SHA256 is `3c037c1a46d2ed30bb20b134d955b680238f2f950d0610218be2f987e6b21d48`. The renamed notes file has the same hash.

## Evidence and limits

- Baseline engine is `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`.
- The source commit changes only `src/query/vacuum.c`: six lines added and two removed in the `REC_RELOCATION` branch of `vacuum_heap_record`.
- Pre-fix runs used the baseline plus a local reproduction hook. Debug abort, release abort and release crash each placed committed id 1000 in the vacuumed forward slot. Debug failed the `slotted_page.c:1969` assertion during abort and every restart. Release logged page 707 corruption and then the `spage_compact` FATAL, both after abort and after restart recovery.
- Post-fix runs used the fix plus the same hook. Debug and release abort and crash runs preserved every committed row through the index and heap paths. Vacuum retry reduced the victim's OOS records to zero. SA `checkdb` passed on all four databases.
- Debug CTest without the hook passed 44 of 44 configured tests.
- The hook widens the window to as much as 120 seconds. Real-world frequency is unmeasured. Multi-chunk OOS delete failure, DONT_REUSE_OID tables and HA replication are untested.
- The hook and driver are not publishable regression tests. The PR adds no automated test. Company CI has not been triggered for this change.

## Proposed publication operations

1. Recheck the source commit, source cleanliness, base and absence of a duplicate PR. Reconcile any source or destination change before publication.
2. Rebase the docs task onto current local `main`, audit every incoming path, fast-forward merge and push `main` to its configured origin.
3. Apply the same rebase, audit, fast-forward merge and push to the JIRA notes task. Its incoming paths are only the issue report and `README.md`. The live ticket already has the report; no JIRA rewrite, reassignment or workflow transition is proposed.
4. Push only `CBRD-27858-oos-relocation-forward-slot` at `628857607265880ef7bbdda4973b1b6f06e8b797` to `vk` with a normal push. Stop on an unexpected remote tip. Do not push `pr7990-hornet-r5-repro` or `pr7990-hornet-r5-fixed-repro`.
5. Create one draft PR in `CUBRID/cubrid` with head `vimkim:CBRD-27858-oos-relocation-forward-slot`, base `feature/oos-merge`, the proposed title, the exact reviewed body and assignee `vimkim`. Do not change PR 7990, post review replies, resolve threads or request reviewers.
6. Read back the PR repository, head, base, draft state, assignee, title and body. Record the results here.
7. A company CI trigger is a separate operation that needs its own approval.

## Approval state

On 2026-10-30 the user approved the duplicate search and drafts, then ticket issuance with the local branch rename and commit reword. The user then confirmed the saved body and publication operations 1 to 6 above. A company CI trigger was not approved. This record does not grant permission for future operations.

## Publication results, 2026-10-30

- Before the remote writes, the body SHA256 was `bf32dc3e2e77b0bc4412941abad5470a41658b6ac960599ac8362ba02f3efd72` and the material check passed. Local source HEAD was `628857607265880ef7bbdda4973b1b6f06e8b797`. The `vk` branch and a matching PR were absent. The base was still `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`.
- Docs `main` had gained three concurrent R6 commits that changed the shared checklist and `cbrd-26357/README.md`. The rebase stopped on those two files, so it was aborted and the task was squash-merged. The resolution kept the R6 text and changed only the R5 status sentences and index rows. The body, context and ticket README equaled the task branch files. Docs `main` was pushed at `350d0ae`.
- JIRA notes `main` had gained a concurrent CBRD-27841 README entry. The same squash fallback kept both entries. The issue report SHA256 stayed `3c037c1a46d2ed30bb20b134d955b680238f2f950d0610218be2f987e6b21d48`. Notes `main` was pushed at `0378cdb`.
- A normal push created `vimkim/cubrid:CBRD-27858-oos-relocation-forward-slot`. The remote SHA was read back and matched `628857607265880ef7bbdda4973b1b6f06e8b797`. The reproduction branches were not pushed.
- Created [CUBRID/cubrid PR 8348](https://github.com/CUBRID/cubrid/pull/8348) as a draft. Read-back showed head `vimkim/cubrid:CBRD-27858-oos-relocation-forward-slot` at `628857607265880ef7bbdda4973b1b6f06e8b797`, base `feature/oos-merge`, state OPEN, assignee `vimkim` and the proposed title.
- The published body equals the approved file exactly. Its SHA256 is `bf32dc3e2e77b0bc4412941abad5470a41658b6ac960599ac8362ba02f3efd72`.
- No CI trigger, review reply, thread resolution, reviewer request or PR 7990 change was made. Company CI and team review remain pending.
