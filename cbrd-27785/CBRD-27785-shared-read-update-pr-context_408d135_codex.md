# CBRD-27785 PR #8299 update proposal

Prepared: 2026-10-28, Asia/Seoul. Agent: `codex`.
This file records a publication proposal. It does not grant publication permission.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785) |
| Follow-up | [CBRD-27816](https://jira.cubrid.org/browse/CBRD-27816), Sub-task of CBRD-26978, relates to CBRD-27785 |
| Operation | Update existing PR [#8299](https://github.com/CUBRID/cubrid/pull/8299) |
| Target repository | `CUBRID/CUBRID` |
| Source repository and remote | `vimkim/cubrid`, `vk` |
| Source push branch | `CBRD-27785-oos-read-performance` |
| Local preparation branch | `CBRD-27785-shared-path-pr` |
| SOURCE_COMMIT | `408d1352941e9d28a88b4d5c899bacf34e2ec1a0` |
| Observed remote source head | `bcb900d1696756a120ec0a2b7885c212f71ebc07` |
| Base | `feature/oos-merge`, observed `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| Existing PR state | Open, draft; retain draft status |
| Existing title | `[CBRD-27785] Reduce CPU overhead for inline heap reads` |
| Proposed replacement title | `[CBRD-27785] Reduce heap read and UPDATE CPU overhead` |
| Original body SHA-256 | `72209fca6a2339f85678c825de913635f32d5108f3b4741ece9fa753d37bdc5e` |

The proposal adds one linear commit after the observed remote PR head.
All engine sources equal measured implementation `02df4d9fe2d1f24168a18eda8d8be216e2c4ed99`.
The previous PR benchmark and SQL tests remain. Focused correctness passed 15/15 in 26.38 seconds.
The production build and installation completed with every UNIT_TEST option OFF.
Eight SERVER_MODE/SA_MODE compile commands include O2, NDEBUG and frame pointers without test hooks.
Installed binary hashes and build IDs were recorded in the new PR verification artifacts.
No new performance run on this PR binary is claimed. The historical +2% robustness gate remains unmet.
The author accepts the currently observed approximately +5% for this integration and defers residual work to CBRD-27816.

## Saved material

Docs repository: `vimkim/my-cubrid-docs`.
Task branch: `docs/CBRD-27785-pr8299-update`. Integration branch: `main`.

- Body: [CBRD-27785-shared-read-update-pr-body_408d135_codex.md](CBRD-27785-shared-read-update-pr-body_408d135_codex.md)
- Explanation: [CBRD-27785-shared-read-update_408d135_codex.md](CBRD-27785-shared-read-update_408d135_codex.md)
- Context: this file. Index: [README.md](README.md).
- Public explanation URL: <https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27785/CBRD-27785-shared-read-update_408d135_codex.md>

JIRA notes repository: `vimkim/my-cubrid-jira`.
Task branch: `docs/CBRD-27816-update-followup`. Integration branch: `main`.
Local commit `3ae9edc` records the already-created follow-up and its README entry.
Report: `issues/CBRD-27816-ordinary-update-residual-cost_02df4d9_codex.md`.
The issue was created and its parent, description, type and Relates link were read back.
Do not create it again or overwrite CBRD-27785's description in this proposal.

## Proposed publication operations

After the user reviews these files, request one confirmation for the following operations:

1. Verify the current PR head, base, title, body fingerprint and source ancestry. Reconcile any external change before publication.
2. Push `408d1352941e9d28a88b4d5c899bacf34e2ec1a0` to `vk:CBRD-27785-oos-read-performance` with a normal fast-forward push. Do not merge or push `feature/oos-merge`.
3. Rebase and fast-forward the docs task branch into its current `main`, then push `origin/main`. Include these three files, their index and concise publication records. Preserve the separate investigation branch and its raw evidence.
4. Rebase and fast-forward the JIRA notes task branch into its current `main`, then push `origin/main`. Include only the CBRD-27816 report and README update. No additional live JIRA description write is proposed.
5. Verify that the public explanation matches the reviewed file. Update PR #8299 with the exact reviewed body and replacement title. Retain its draft status, base and assignee.
6. Trigger CUBRID CI once for this pushed PR revision, wait for completion and report the exact run and TC Merge Gate result. Stop before follow-up fixes or reruns.
7. Record verified publication results and clean up only integrated documentation worktrees without force. Preserve source checkouts, databases, binaries and raw artifacts.

No testcase repository changes are required for this source update; the added native tests are already in the source PR.
TC PRs [public #3898](https://github.com/CUBRID/cubrid-testcases/pull/3898) and [private #4589](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4589) were open on inspection.
The human closes them if no TC changes are required. The agent does not merge, close or delete TC branches.

The new follow-up creation is complete. Source push, documentation integration/push, PR title/body update and CI remain unexecuted pending review confirmation.
The original CBRD-27785 investigation report was updated locally at docs commit `4d7a149`; that separate branch is outside these publication operations.
