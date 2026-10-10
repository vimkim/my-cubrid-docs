# CBRD-26659 testcase PR proposal

Prepared: 2026-10-10 (Asia/Seoul). Agent: codex. Parent implementation work item: 306; integration/publication work item: 314. Status: bodies ready for human review; no remote publication yet.

## Identity and proposed destination

- Ticket: CBRD-26659.
- SOURCE_COMMIT: `c94961578dc43bfe05a74591d52dff30d44a43d3`.
- Source repository: `vimkim/cubrid-testcases`; source branch: `task/oos-regressions-public`; push remote: `vk`.
- Target repository: `CUBRID/cubrid-testcases`; base branch: `feature/oos-merge`.
- Observed base commit after fetch: `bdba62aee0faec05abdd861518824c69b6c1b3c5`; current task has no commits behind this base.
- Observed source remote branch: absent on 2026-10-10. No existing PR matches this source repository, branch and base; operation: create.
- Proposed title: `[CBRD-26659] Add OOS SQL regression coverage`.
- Proposed state: draft; default assignee: `vimkim`. No reviewers are assigned automatically; the user will obtain teammate review.
- Coordinating engine branch has no PR. Existing bot TC PRs for engine PR7925/7927 are unrelated and are preserved.

## Saved material

- Body: `cbrd-26659/CBRD-26659-oos-sql-regressions-pr-body_c949615_codex.md`; upload exactly these UTF-8 bytes after reviewed-body confirmation.
- Context: `cbrd-26659/CBRD-26659-oos-sql-regressions-pr-context_c949615_codex.md`.
- No extra explanation or public docs link is proposed. Both bodies stand alone; no docs remote push is needed for links.
- Docs task branch: `docs/oos-tc-prs`; integration branch: `main`.
- Previously approved delivery docs were rebased and merged into local main at `06b17d611421a20787b1a4d6249d6e7cbaaeaea0`; their old task worktree/branch were safely removed.

## Exact proposed publication operations

1. Recheck this source commit, fresh remote base/head, unrelated-file preservation and the saved body bytes. Apply the PR material checker read-only.
2. Push only `task/oos-regressions-public` at `c94961578dc43bfe05a74591d52dff30d44a43d3` to `vimkim/cubrid-testcases` through `vk`, without force and without updating a testcase base branch.
3. Create a draft PR in `CUBRID/cubrid-testcases`, head `vimkim:task/oos-regressions-public`, base `feature/oos-merge`, the proposed title above, saved body unchanged and assignee `vimkim`.
4. Record verified URL/head/base/body fingerprint in this context after publication. User confirmation covers local docs task commits for both PR bodies/contexts and the README index, their approved rebase/fast-forward integration into local `main`, and final execution-record updates and safe docs task cleanup.
5. Retain both testcase integration worktrees/branches for human review. No testcase PR merge/close/deletion, base-branch merge, engine edit/push, JIRA publication or manual CI trigger is proposed.

## Evidence and limits

The body summarizes the accepted 2026-10-08 exact-commit native qualification and separate Standards/Spec closures. Testcase bytes are unchanged. Full delivered branch diffs include retained failing or inconclusive reproducer cases outside the passing selection; the body makes that distinction explicit. Review documentation is retained under `cbrd-26659/ci-replan/delivery/14-complete-local-validation.md` and `final-review-cleanup.md`; immutable local receipts remain external and are not publication material.

This context records a proposal, not an approval token. Explicit reviewed-body confirmation must come from the conversation before publishing.
