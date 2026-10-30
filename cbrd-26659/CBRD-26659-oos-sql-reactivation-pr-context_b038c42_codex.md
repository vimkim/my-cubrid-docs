# CBRD-26659 SQL reactivation PR description proposal

Created and last modified: 2026-10-30, Asia/Seoul. This is a saved proposal, not publication authorization.

## Source and destination

- Ticket: CBRD-26659. Agent: codex.
- Source repository: `CUBRID/cubrid-testcases`.
- Source branch: `tc/pr-8128`; base: `feature/oos-merge`.
- SOURCE_COMMIT: `b038c424b6a8d078671132e2369040493a5fc1f6`. Observed remote head is the same commit.
- Target: https://github.com/CUBRID/cubrid-testcases/pull/3688. Operation: update existing description only.
- Existing title: `[CBRD-26659] Draft: TC changes for PR CUBRID/cubrid#8128`. No title change is proposed.
- Existing state: `OPEN`, isDraft `false`. Preserve it.
- Original GitHub body SHA-256 over decoded UTF-8 without added newline: `bb57c187e660bd86120ac27baff11c4d54eb8973777001efc2f4c130d12a7d92`.
- JIRA was read through `cubrid-jira search CBRD-26659`; its existing developer TC scope remains broader than these three restored cases. No JIRA write is proposed.

## Saved files and proposed operations

- Docs repository: `vimkim/my-cubrid-docs`.
- Docs branch: `docs/cbrd-26659-sql-restore-20261030`; integration branch: `main`.
- Body: `cbrd-26659/CBRD-26659-oos-sql-reactivation-pr-body_b038c42_codex.md`.
- Context: `cbrd-26659/CBRD-26659-oos-sql-reactivation-pr-context_b038c42_codex.md`.
- Analysis: `cbrd-26659/CBRD-26659-sql3-restoration_20261030_b038c42_codex.md`.
- Also integrate the revised original SQL reproduction report, checklist, ticket README, historical proof script and new restoration proof script. These eight selected paths include the final CI execution-record edits.
- After explicit review approval, rebase the docs branch onto clean current `main`, audit all incoming paths/history and links, fast-forward merge and push configured `origin/main`, then remove only this merged docs task checkout and local branch after preserving local material.
- Update only PR #3688's description with the reviewed body file, unchanged. Recheck source head, original body fingerprint and material validation immediately before publishing.
- No new PR, title/state change, TC merge/close/delete, Engine push or another CI run is proposed.
- The two tested TC commits have already been pushed under the user's standing TC-head authorization. They are not pending publication in this proposal.

## Evidence and remaining state

The native restoration proof verifies three real PASS results, 28 active pairs, zero disabled pairs, four exact error-number changes, unchanged SQL/other expectations, original NOK history and real 120-second guard interruption. The old guard explanation was corrected after live observations; the wrapper remained unchanged. Native process cleanup is observed for all three cases; live namespace inode evidence is limited to the latter two.

CI [41031622190](https://github.com/CUBRID/cubrid/actions/runs/41031622190), attempt 1, finished FAILURE after one trigger. Build debug/release, medium and SQL contexts report SUCCESS; shell reports FAILURE. Validated shell evidence contains 3,490 passes, one failure and 30 skips. Medium has 975 passes. The shell failure is `cbrd_25977-16`, whose expected worker list `2,3,4` differs from observed `2,4`. Its cause and PR relation remain unknown.

SQL collection remains `collection_failed` because shard 01 planned 3,533 cases but summary/JUnit contain 3,531. Retained shard 09 raw evidence independently reconciles 468 cases, including all 28 OOS paths and the three restored PASS observations. This does not certify the whole SQL suite. The body and report record the terminal result and this limit. No follow-up source/testcase edit, push or CI rerun was performed.

Before this review handoff, the remote PR head and original body fingerprint were read again and remained equal to the source identity and original fingerprint above. Publication must check them again after approval. Human TC review/merge, the remaining historical shell failures, long cases, HA and overall Work456 remain incomplete.
