# CBRD-27785 PR publication proposal

Prepared: 2026-10-27, Asia/Seoul. Agent: `codex`.
This file records the reviewed proposal and verified publication results.
It does not authorize later source or text changes.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785) |
| Operation | Create a draft PR |
| Target repository | `CUBRID/CUBRID` |
| Source repository | `vimkim/cubrid` |
| Source branch | `CBRD-27785-oos-read-performance` |
| SOURCE_COMMIT | `bcb900d1696756a120ec0a2b7885c212f71ebc07` |
| Base branch | `feature/oos-merge` |
| Observed local and remote base | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| Observed remote source branch | Absent on 2026-10-27 |
| Matching open PR | None found for the exact source and base on 2026-10-27 |
| Proposed title | `[CBRD-27785] Reduce CPU overhead for inline heap reads` |
| Proposed assignee | `vimkim` |

The source is clean and contains four task commits: the benchmark, fixed-column
read changes, variable-column read changes, and client installation validation.
Local spec and implementation receipts remain on the separate planning branch
`CBRD-27785-oos-performance`; they are excluded from the publication history.

## Saved review material

Docs repository: `vimkim/my-cubrid-docs`.
Task branch: `docs/CBRD-27785-oos-read-performance`. Integration branch: `main`.

- Body: [CBRD-27785-oos-read-performance-pr-body_bcb900d_codex.md](CBRD-27785-oos-read-performance-pr-body_bcb900d_codex.md)
- Explanation: [CBRD-27785-oos-read-performance_bcb900d_codex.md](CBRD-27785-oos-read-performance_bcb900d_codex.md)
- Index: [README.md](README.md)
- Public explanation URL: <https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27785/CBRD-27785-oos-read-performance_bcb900d_codex.md>

JIRA notes repository: `vimkim/my-cubrid-jira`.
Task branch: `docs/CBRD-27785-oos-performance`. Integration branch: `main`.
Report: `issues/CBRD-27785-oos-performance-regression_dcbf09e_codex.md`.
The report includes the initial investigation and the final implementation results.

## Proposed operations

One explicit confirmation is requested for these operations after review:

1. Rebase the source task branch onto the current local `feature/oos-merge`,
   review the resulting diff, run proportionate checks, and merge locally with
   fast-forward; use squash only if rebase and fast-forward are impractical.
   Preserve the reviewed source branch until its remote push is verified.
2. Rebase and integrate the docs task branch into its current `main`, then push
   `main` to its configured origin. Include these four documents and any concise
   publication execution record with the corresponding index update.
3. Rebase and integrate the JIRA notes task branch into its current `main`, then
   push `main` to its configured origin. Include only the specified report and
   any necessary concise publication record. Publish notes before the live update.
4. Push the reviewed source branch to `vk`, the `vimkim/cubrid` fork. Create a
   **draft** PR against `CUBRID/CUBRID:feature/oos-merge`, with the saved body,
   proposed title, and `vimkim` assignment. Publish the linked explanation first.
5. Replace only CBRD-27785's description with the specified reviewed report through
   `cubrid-jira`, after checking the current issue and dry-run target. Preserve
   issue type, priority, assignee, and status.
6. Verify each result and remove only merged task worktrees/branches with ordinary
   no-force Git cleanup. Preserve plans, raw evidence, databases, builds and logs.

This proposal does not include pushing `feature/oos-merge`, changing PR #7990,
posting review comments, or triggering additional company CI.
If the source commit, body, explanation, base, or operation list changes,
reconcile the material and return it for review before publication.

## Verification and resume boundary

Both implementation tickets and the Standards/Spec reviews are complete.
The concrete benchmark client identity finding was fixed and reviewed at the
stated source revision. Final matching-client forward and reverse comparisons
pass the class 1 +2% instruction budget. Engine and C++ test blobs match the
measured `e77ffbf0e3c4a2dcf1f3a918bafcabf91ac136cd` build; source publication
cherry-picks changed commit identities, without changing those blobs.

At preparation, no remote writes or merge into the local feature destination had
been performed. The verified publication results are recorded below. Rediscover
local worktrees through Git when resuming; this record does not authorize future
source or text changes.

## Publication results — 2026-10-27

The user confirmed the saved material and listed operations in the conversation
with “응 만들어줘.” The reviewed source and publication text were unchanged.

- Draft PR: [CUBRID/CUBRID #8299](https://github.com/CUBRID/cubrid/pull/8299).
  Title, exact body, draft status, `vimkim` assignment, source repository/branch,
  head `bcb900d1696756a120ec0a2b7885c212f71ebc07`, and base `feature/oos-merge`
  were verified after creation. GitHub reported the PR as mergeable.
- The source was rebased without changes and fast-forwarded into the local
  `feature/oos-merge`. The fork branch was pushed and its remote SHA verified.
  The organization feature branch remained at `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`.
- Docs commit `ab91eaa3da360b2da824bbd005e04d9692afb054` was fast-forwarded
  into docs `main` and pushed. The explanation at the recorded public URL was
  fetched and matched the approved file byte for byte before PR creation.
- JIRA notes commit `b8f0130b87b6be22d40329cc19c1acacdd1d931a` was fast-forwarded
  into notes `main` and pushed before the live description update.
- CBRD-27785's description was updated from the reviewed report. CLI read-back
  confirmed the final results. Status `Open`, priority `Minor`, type `Sub-task`,
  and assignee `Daehyun Kim` were preserved.

| Published material | SHA-256 |
| --- | --- |
| PR body | `72209fca6a2339f85678c825de913635f32d5108f3b4741ece9fa753d37bdc5e` |
| Explanation | `b5c51e749379b71898e1a4a87208d91e51af24e13c72bcfff4ecc8e0e6313e30` |
| JIRA report | `0014540f07ad8818847eac2d220206e24d2a270496c8823a117ee9d525a04a21` |

No additional company CI was triggered. Class 2/3 and UPDATE/I/O performance
remain follow-ups. Raw evidence, databases, logs, installations, and the separate
planning branch are retained. Earlier worker cleanup was limited by Git's
submodule worktree restriction; no force cleanup was used.
