# CBRD-27827 PR publication context

This file records a publication proposal. It does not grant permission.

## Source and target

- Ticket is [CBRD-27827](https://jira.cubrid.org/browse/CBRD-27827). It was created as Correct Error and read back on 2026-10-29. On 2026-10-30 it was converted to a Sub-task of OOS M2, CBRD-26583, after the user approved the concrete target and type change. Status remained Open.
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

The user confirmed the saved body and listed publication operations in the conversation on 2026-10-29. The same message requested a separate investigation and repair of broken JIRA rendering. That repair did not revoke R1 publication approval. This record does not grant permission for future operations.

## Publication results, 2026-10-29

- The docs task was rebased onto the current local main, checked across its five retained paths, merged by fast-forward and pushed to `vimkim/my-cubrid-docs:main` at `84658d1b8673607da5b8a3e250e8c3a34468a519`.
- The JIRA notes task was merged by fast-forward and pushed to `vimkim/my-cubrid-jira:main` at `0f41cc4bc65b35a160b45953e3ae1eeb35679c3d`. Incoming paths were only the issue report and README.
- A normal push published the reviewed source commit to `vimkim/cubrid:CBRD-27827-oos-insert-header-wait`. The remote SHA was read back and matched `4db11c5f12f9c67134aad7f547df8704d1e5c591`.
- Created [CUBRID/cubrid PR 8330](https://github.com/CUBRID/cubrid/pull/8330) as a draft, assigned to `vimkim`, targeting `feature/oos-merge`. Title, source repository, branch, commit, base, draft status and assignee were read back and matched the proposal.
- Published body SHA256 is `0e59fe52a0198c67bed2525fb3f0713e1cc53c415adf83ea1b561a164eb0e3ee`, identical to the approved file including its final newline.
- The feature testcase baseline check passed for both automatically created `tc/pr-8330` branches. Public tip was `70db22a1c99dbbaa27fa1438c8967effdfcad551`; private tip was `75a02020e19be4bfc64e47f7c7a3d5c2b02d7676`. Each equaled the fetched feature baseline. No testcase branches were changed by this agent.
- The fresh activity snapshot contained no `/run` comment or gha-ci commit statuses. Posted one approved [`/run all`](https://github.com/CUBRID/cubrid/pull/8330#issuecomment-6493562314). Both build contexts and SQL, medium and shell contexts became PENDING and pointed to [gha-ci run 40853451200](https://github.com/CUBRID/cubrid/actions/runs/40853451200). The PR head remained the reviewed `4db11c5f1`. No stable required gha-ci context was missing at pickup; this does not establish a passing result.
- The live `gh pr checks --required` view returned exit 1 with `no required checks reported on the 'CBRD-27827-oos-insert-header-wait' branch`. The five observed gha-ci statuses were checked separately. CI completion and team review remain pending.

## JIRA rendering repair

- The user reported that the JIRA web issue body was broken. Two independent agents traced this to the literal `{code}` inside the embedded Python f-string, which Jira interprets as the closing code macro.
- The `cubrid-jira` candidate uses a noformat block when code contains that marker and rejects a fenced block containing both closing markers before publication. Syntax highlighting is lost for this block. The original Markdown and Python were preserved.
- A related readback regression removed indentation from a code block at the start of a document. The candidate preserves leading indentation and trims only boundary newlines.
- Candidate commits are `43cb00d`, `7482a69`, `55200fd` and `3f282aa`. All 297 default tests passed. A fresh independent audit passed 112 focused tests and found no blockers.
- The real Jira preview first reproduced the broken Python and swallowed Expected Result heading. After conversion, both were intact. One authorized live description update was then read back through `fields.description` and `renderedFields.description`: the complete Python text matched the original and the Expected Result heading and following body were preserved.
- Original issue Markdown SHA256 remained `c88fe7ff5adee90d81101750c36d1fad91d5b5f581b3e1f09e1de5a2fdba31e0`. No issue summary, assignment, priority or workflow state was changed.
- On 2026-10-30 the user approved CLI integration, push and installation. The clean task was rebased onto unchanged main `5d70fc6` and all 297 default tests passed again. The approved tip `3f282aae346368cae982354777b40cd17ddf402f` was merged by fast-forward, pushed to `vimkim/cubrid-jira:main` and installed through the CLI repository's sync recipe.
- The installed package's converter bytes matched main. The installed CLI dry-run matched the verified issue payload exactly; leading code indentation and rejection of both closing markers also passed. A fresh read of the live issue confirmed the original Python and Expected Result heading/body remained intact. No additional live description write was needed.
- The merged CLI task worktree and local branch were removed without force. Only disposable uv and Python caches were present; evidence was preserved separately. CLI main is clean and work item `617` is complete.

## JIRA parent conversion, 2026-10-30

- The user asked to place R1 under OOS M2 and confirmed the proposed conversion. A live check identified [CBRD-26583](https://jira.cubrid.org/browse/CBRD-26583) as `[OOS] [EPIC] [M2] 마일스톤 2`, type Development Subject, with 46 existing subtasks before conversion.
- After recording the current Correct Error issue with no parent, one conversion used the CLI's Convert wizard. A direct issue GET verified type Sub-task and parent CBRD-26583.
- Issue key and numeric ID, summary, raw description, status Open, priority, assignee and issue links matched the pre-conversion snapshot. The live rendered description still preserved the complete original Python and Expected Result heading/body.
- The source branch, PR number 8330 and approved PR body were not edited. The parent relationship organizes the work under M2 while each engine fix retains its independent company PR and CI.

## CI inventory update, 2026-10-30

- The reviewed head's release/debug builds, SQL and medium statuses passed. Shell failed in [run 40853451200](https://github.com/CUBRID/cubrid/actions/runs/40853451200).
- Failed shard shell 05 recorded exactly one NOK case, `cubrid-testcases-private-ex/shell/_36_damson/cbrd_23608_tde/temp_enc_06/cases/temp_enc_06.sh`. The collect job reported `shell: 1 failed`.
- The user identified `temp_enc_06` as a well-known flaky case. That classification comes from the user; the match to this run's sole failing case was checked directly in its logs.
- Separate investigation of this failure as a suspected R1 regression is not a prerequisite for starting R5. The actual shell FAILURE status remains recorded. No CI rerun, merge-gate override, review request or source merge was performed.
