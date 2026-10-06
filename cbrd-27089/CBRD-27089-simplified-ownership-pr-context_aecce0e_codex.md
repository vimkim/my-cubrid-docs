# PR 7927 publication context

- Ticket: CBRD-27089
- Source commit: aecce0e1216a813771621c13112c8f27d43df22e
- Agent: codex
- Source: vimkim/cubrid, feat/oos-deferred-write
- Base: CUBRID/cubrid, feature/oos-merge
- Observed remote head: b5b5eacbbe2e62e1672f423574fd5a30e0b3320a
- Target: https://github.com/CUBRID/cubrid/pull/7927
- Operation: update existing body; preserve title and draft status
- Title: [CBRD-27089] Defer OOS writes until destination heap selection
- State: OPEN, draft
- Original body SHA-256: 77f8a18bd3c17a3f96726b9edecbd83fe9900c8bb6b67a7eb1776ba9c0f243dd
- Published material SHA-256: c404b1756f7382ac97024bdd276d9d04ff8e08f06ea8d958468a0d1ea1669424
- Docs branch: docs/pr7927-temporary-oos-stub; integration branch: main
- Body: cbrd-27089/CBRD-27089-simplified-ownership-pr-body_aecce0e_codex.md
- Context: cbrd-27089/CBRD-27089-simplified-ownership-pr-context_aecce0e_codex.md

## Authorized operations

User explicitly requested: push the PR (force push if needed), trigger CI, update PR body.
Push the source commit to vimkim/cubrid feat/oos-deferred-write; normal fast-forward suffices.
Update PR 7927 with the saved body. Post one /run all after activity and testcase baseline checks.
Keep docs locally committed; no docs push or local integration is part of this request.

## Results

Both testcase branches contain their latest feature/oos-merge baseline.
Source push completed as a normal fast-forward; remote PR head verified as the source commit.
PR body uploaded and exact text verified; title and draft status preserved.
CI operation: `/run all`
Receipt: https://github.com/CUBRID/cubrid/pull/7927#issuecomment-6016308476
Requested at: 2026-10-06T12:31:56Z
Tested PR head: aecce0e1216a813771621c13112c8f27d43df22e
Pickup verified: release/debug build, test_sql, test_shell, test_medium all PENDING
and linked to https://github.com/CUBRID/cubrid/actions/runs/37463919574.
All four stable required gha-ci contexts are present; terminal results not awaited.
Live required-check query reports no required checks configured for this branch.
