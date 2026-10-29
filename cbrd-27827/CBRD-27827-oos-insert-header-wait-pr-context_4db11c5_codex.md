# CBRD-27827 PR publication context

This file records a publication proposal. It does not grant permission.

## Source and target

- Ticket is [CBRD-27827](https://jira.cubrid.org/browse/CBRD-27827). It was created as Correct Error and read back on 2026-10-29. The default live status is Open; no assignment, priority change or transition was requested.
- Source repository is `vimkim/cubrid`.
- Source branch is `CBRD-27827-oos-insert-header-wait`.
- Source commit is `4db11c5f12f9c67134aad7f547df8704d1e5c591`.
- Source remote is `vk`. No push to the organization repository is proposed.
- The source branch was renamed from `review/pr7990-hornet-r1` after ticket creation. The two source commits are unchanged.
- Target repository is `CUBRID/cubrid`.
- Base branch is `feature/oos-merge`.
- Observed base commit is `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`, fetched on 2026-10-29.
- The proposed source branch is absent on `vk`. No matching PR exists.
- Operation is create a new draft PR. Proposed assignee is `vimkim`.
- Proposed title is `[CBRD-27827] Fix concurrent OOS insert failures`.
- No existing PR title, body fingerprint or draft state applies.

## Material

- Agent is `codex`.
- Docs task branch is `docs/pr7990-hornet-review-20261029`. Integration branch is `main`.
- Body is `cbrd-27827/CBRD-27827-oos-insert-header-wait-pr-body_4db11c5_codex.md`.
- Context is `cbrd-27827/CBRD-27827-oos-insert-header-wait-pr-context_4db11c5_codex.md`.
- The ticket index is `cbrd-27827/README.md`.
- The shared checklist and its index are `cbrd-26357/PR-7990-hornetmj-review-checklist_20261029_codex.md` and `cbrd-26357/README.md`.
- No separate public explanation is linked by the body. The ticket contains the reproducible input, script, failure and limits.
- The JIRA report is `issues/CBRD-27827-oos-concurrent-insert-header-wait_dcbf09e_codex.md` in `vimkim/my-cubrid-jira`. Its index is `README.md`.
- JIRA notes task branch is `docs/CBRD-27827-oos-insert-wait`. Integration branch is `main`. Initial task commit is `0f41cc4`.
- Rediscover checkout paths with `git worktree list` when resuming.

## Evidence and limits

- Baseline engine is `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`.
- Commit `3c39a813a` adds the manual CS regression script. Commit `4db11c5f1` removes seven lines of the engine wait override.
- The fixed workload ran at `3c39a813a` with the seven-line fix in the working tree. Its saved engine diff equals the committed diff in `4db11c5f1`. No engine code changed after verification.
- The first baseline workload round failed at the ownership assertion. The fixed workload passed ten rounds, with 120000 checked rows and OOS records.
- Focused CTest passed 4/4, consisting of two fixtures and two binaries with 23 plus 11 GoogleTests.
- The first CTest attempt failed at fixture setup because configuration captured an empty DB registry before workenv initialization. The initialized environment was reconfigured and the same selected tests passed.
- Release, mixed DELETE/vacuum and preexisting caller zero-wait policies remain untested.
- The regression is manual and timing dependent. Company CI has not been triggered for this new PR.
- Company gha-ci is available for a fork-head company PR with this feature base. Its testcase baselines must pass the current check before any requested trigger.

## Proposed publication operations

1. Recheck the source commit, source cleanliness, base and absence of a duplicate PR. Reconcile any source or destination change before publication.
2. Rebase the reviewed docs task onto current local `main`, validate all incoming retained paths, and merge by fast-forward. Use the documented squash fallback only if necessary. Push docs `main` to its configured origin. This includes the checklist history, PR body/context/index and any final publication record confined to those retained paths.
3. Apply the same reviewed rebase, validation, local merge and push procedure to the JIRA notes task. Only the issue report and README are incoming paths. The live ticket already contains the report; no JIRA rewrite, reassignment or workflow transition is proposed.
4. Push only `CBRD-27827-oos-insert-header-wait` at the reviewed source commit to `vk` in `vimkim/cubrid`. Use a normal push. Stop on an unexpected remote tip.
5. Create one draft PR in `CUBRID/cubrid` with head `vimkim:CBRD-27827-oos-insert-header-wait`, base `feature/oos-merge`, the approved title, the exact reviewed body, and assignee `vimkim`. Do not initialize a native stack, merge source code, change PR7990, post review replies, resolve threads or request a reviewer in this operation.
6. If the user approves the CI operation together with publication, validate fresh activity and feature testcase baselines under cubrid-ci-trigger, then post one `/run all` on the new company PR and verify pickup. An active run, a missing/stale testcase baseline or a changed source requires the skill's specified handling. This proposal does not authorize unrelated testcase changes.
7. Read back the PR repository, head, base, draft state, assignee, title and body. Record the actual operation results. Preserve the source worktree and test DB for later review. Clean only document worktrees that were successfully integrated, after preserving valuable local material.

## Approval state

The conversation authorizes R1 work and ticket creation. PR publication requires explicit confirmation after this body and these operations are available for review under cubrid-pr-create. No approval is stored in this file.
