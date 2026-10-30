# PR 7990 R5 PR publication context

This file records a publication proposal before the ticket exists. It does not grant permission.

## Source and target

- Ticket is not issued. The body uses the placeholder `CBRD-XXXXX`. The JIRA draft is `issues/CBRD-XXXXX-oos-relocation-forward-slot-undo_dcbf09e_claude.md` in `vimkim/my-cubrid-jira`. It is a local task commit and is not yet on `main`.
- Duplicate search on 2026-10-30 found no ticket for this heap forward-slot defect. CBRD-27781 covers OOS chunk slots, and CBRD-27237 covers rolled-back UPDATE chains.
- Proposed ticket: type Sub-task, parent [CBRD-26583](https://jira.cubrid.org/browse/CBRD-26583), the same placement as R1 (CBRD-27827). Proposed summary is the draft's H1, `[OOS] relocation 행의 vacuum 취소가 다른 트랜잭션이 재사용한 슬롯을 덮어써 DB가 손상된다`. A read-only `cubrid-jira create --dry-run` with these fields converted the draft without error.
- Source repository is `vimkim/cubrid`. Current local branch is `pr7990-hornet-r5`.
- Source commit is `c05abc8b4559ff1fa5db54f2a646d866f37156fc`. Its message uses the placeholder prefix `[CBRD-26357]`.
- Source remote is `vk`. No push to the organization repository is proposed.
- Target repository is `CUBRID/cubrid`. Base branch is `feature/oos-merge`.
- Observed base commit is `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`, fetched on 2026-10-30. The source commit's parent is this base.
- No R5 branch exists on `vk`. No open PR to `feature/oos-merge` matches R5. The open fork PRs to that base are 8330, 8299 and 8128.
- Operation is create a new draft PR. Proposed assignee is `vimkim`.
- Proposed title is `[CBRD-XXXXX] Fix vacuum undo that overwrites a reused forward slot`.
- No existing PR title, body fingerprint or draft state applies.

## Revision after ticket issuance

- Issuing the ticket changes the source identity. The branch is renamed to `CBRD-NNNNN-oos-relocation-forward-slot`, and the commit message prefix changes from `[CBRD-26357]` to the new key. The code diff does not change, so the commit SHA changes and these files are superseded.
- Prepare new body and context files under `cbrd-NNNNN/` named by the new source commit. Change only the JIRA URL and title key in the body unless the reviewed text changes. Return the new files for review before publication.
- Rename the JIRA draft to `issues/CBRD-NNNNN-oos-relocation-forward-slot-undo_dcbf09e_claude.md`, remove its draft wording in `README.md`, and upload it to the new issue description only after its own review and approval.

## Material

- Agent is `claude`.
- Docs task branch is `docs/pr7990-hornet-r5-pr-20261030`. Integration branch is `main`.
- Body is `cbrd-26357/CBRD-XXXXX-oos-relocation-forward-slot-pr-body_c05abc8_claude.md`.
- Context is `cbrd-26357/CBRD-XXXXX-oos-relocation-forward-slot-pr-context_c05abc8_claude.md`.
- The index is `cbrd-26357/README.md`. The shared checklist is `cbrd-26357/PR-7990-hornetmj-review-checklist_20261029_codex.md`.
- No separate public explanation is linked by the body. The JIRA issue contains the reproduction steps, the reproduction-only hook and the driver.
- JIRA notes task branch is `docs/pr7990-r5-issue-20261030` in `vimkim/my-cubrid-jira`. Initial task commit is `cd1bd26`. Its incoming paths are the issue draft and `README.md`.
- Rediscover checkout paths with `git worktree list` when resuming.

## Evidence and limits

- Baseline engine is `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`.
- Commit `c05abc8b4` changes only `src/query/vacuum.c`: six lines added and two removed in the `REC_RELOCATION` branch of `vacuum_heap_record`.
- Pre-fix runs used the baseline plus a local reproduction hook. Debug abort, release abort and release crash each placed committed id 1000 in the vacuumed forward slot. Debug failed the `slotted_page.c:1969` assertion during abort and every restart. Release logged page 707 corruption and then the `spage_compact` FATAL, both after abort and after restart recovery.
- Post-fix runs used the fix plus the same hook. Debug and release abort and crash runs preserved every committed row through the index and heap paths. Vacuum retry reduced the victim's OOS records to zero. SA `checkdb` passed on all four databases.
- Debug CTest at `c05abc8b4` without the hook passed 44 of 44 configured tests.
- The hook widens the window to as much as 120 seconds. Real-world frequency is unmeasured. Multi-chunk OOS delete failure, DONT_REUSE_OID tables and HA replication are untested.
- The hook and driver are not publishable regression tests. The PR adds no automated test. Company CI has not been triggered for this change.

## Proposed operations, in order and each needing approval

1. Ticket: create the Sub-task with the fields above and the reviewed JIRA draft as its description, using `cubrid-jira create` with `--yes`. Read it back.
2. Source: rename the local branch, reword only the commit message prefix, rebuild and recheck that the diff is unchanged. Prepare the revised body and context and return them for review.
3. Docs and JIRA notes: rebase each task onto its current local `main`, fast-forward merge and push `main` to its configured origin.
4. Push only `CBRD-NNNNN-oos-relocation-forward-slot` at the reviewed source commit to `vk` with a normal push. Stop on an unexpected remote tip. Do not push the reproduction branches `pr7990-hornet-r5-repro` and `pr7990-hornet-r5-fixed-repro`.
5. Create one draft PR in `CUBRID/cubrid` with head `vimkim:CBRD-NNNNN-oos-relocation-forward-slot`, base `feature/oos-merge`, the approved title and the exact reviewed body, and assign `vimkim`. Do not change PR 7990, post review replies, resolve threads or request reviewers.
6. A company CI trigger is a separate operation that needs its own approval.
7. Read back the PR repository, head, base, draft state, assignee, title and body, and record the results here.

## Approval state

On 2026-10-30 the user approved preparing the duplicate search, the JIRA draft and this PR body draft. Ticket issuance, branch rename, fork push and PR creation need separate approval after review.
