# CBRD-26659 private bot TC PR update proposal

Prepared: 2026-10-10 (Asia/Seoul). Agent: codex. Work item: 314. Status: approved public/private TC head pushes and exact reviewed description updates completed; separately requested full CI pickup verified.

## Identity and freshness baseline

- Ticket: CBRD-26659; coordinating engine PR: [CUBRID/cubrid#8128](https://github.com/CUBRID/cubrid/pull/8128), head `a5da823b2a84e95b4b22d48abe4a3f9fd601c176`.
- SOURCE_COMMIT: `27db3d6b6d966056de474af277ee40735190f00c`; source and target repository: `CUBRID/cubrid-testcases-private-ex`; source branch: `tc/pr-8128`; push remote: `origin`.
- Existing PR: [CUBRID/cubrid-testcases-private-ex#4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365); operation: update. State: open, draft; preserve its title, assignees and draft status.
- Existing title: `[CBRD-26659] Draft: TC changes for PR CUBRID/cubrid#8128`; no title change is proposed.
- Base: `feature/oos-merge`, freshly fetched at `c4b9d482fbd491a68510b2552df2c3cac91911fc`; included in SOURCE_COMMIT.
- Observed remote PR head before publication: `b383bca5b6fc1315b85beef7b8c3c4db5f8dc6fd`, the bot's initialization commit.
- Original decoded GitHub body SHA-256: `45f7617d999bca5cd772dfc02fdfe169264351ad7db995feddae266b7fc8d1f9`. Compare UTF-8 bytes without adding a newline.
- SOURCE_COMMIT parents: the observed bot head and validated task payload `f5fc1fa815fbc6eec71135f506e377c0b1096da3`. Whole Git tree `7e04d69648daad2b8353f53a1a4a48aa40d37ae8` is identical to the payload; bot history is retained without force.

## Saved material

- Body: `cbrd-26659/CBRD-26659-oos-shell-regressions-pr-body_27db3d6_codex.md`.
- Context: `cbrd-26659/CBRD-26659-oos-shell-regressions-pr-context_27db3d6_codex.md`.
- Companion [public context](CBRD-26659-oos-sql-regressions-pr-context_1a556a0_codex.md) specifies public SOURCE_COMMIT and the exact combined publication operations. One confirmation can cover both.
- Docs task branch: `docs/oos-tc-8128`; integration branch: `main`. No external explanation URL and no docs push are proposed. Original historical source bodies remain preserved.

## Exact combined publication operations

1. Recheck both saved bodies, their material checks, source commits, current remote heads/bodies/PR state and latest feature-base inclusion. Preserve unrelated files. If remote/body/source changes outside this attempt, reconcile and return for review.
2. Push public `tc/pr-8128` at `1a556a0752073aaad573bf87d53f3eb75f398138` to `CUBRID/cubrid-testcases` through `origin`, and private `tc/pr-8128` at `27db3d6b6d966056de474af277ee40735190f00c` to `CUBRID/cubrid-testcases-private-ex` through its `origin`. Both updates are fast-forwards from the observed bot commits; never force or update a base branch.
3. Update only the descriptions of public PR3688 and private PR4365 with their respective saved body files, unchanged. Preserve existing titles, assignees and draft/ready state. Do not create duplicate PRs.
4. Verify both remote heads and exact published body bytes, and record the results in the contexts. Commit the four selected body/context files and README index, including final execution-record updates, then rebase and fast-forward integrate this docs task into local `main`. Audit incoming selection and links, preserve useful local material and safely remove only the merged docs task worktree/branch.
5. Retain both `tc/pr-8128` worktrees/branches and the original validated task snapshots for teammate review. No engine push/body update, docs push, manual CI request, PR merge/close, base-branch merge, remote branch deletion or JIRA publication is proposed.

Confirmation would authorize only these TC head pushes and description updates as an exception to the prior no-push instruction. Publication of the engine coordinator and automatic TC branch creation already completed in the preceding approved phase; local docs main is clean at `d89dd734291a01d6fc008d3c14ee607a3b35f03d` before this new task.

## Evidence and limits

All 44 changed private paths retain their Git blob and mode from the original payload. All 40 selected qualification inputs match the frozen accepted contract in live files and committed blobs. The original source snapshot and all native verdict, independent expectation and cleanup evidence remain unchanged. Source whitespace checks pass. The preexisting untracked Rope database in the original integration worktree is preserved at SHA-256 `f352869ac4fb4eea61fe83e15c7679976f16c7189ecff70005910fa586f62545`; the new TC worktree is clean. There was no new native execution or timing run for the history-only integration.

The full payload contains 18 shell entrypoints; the prior passing selected result covers 14. `partition_owner`, `snapshots_reclaim`, `cbrd_27237_rollback_vacuum` and `utility_sa_physical` remain failing or inconclusive reproducers in normal discovery paths. The proposed update publishes those known limitations explicitly and does not claim whole-corpus or company-CI success. Full CI still needs an explicit disposition of these four cases and the public failing partition case. No expectations were weakened or cases silently disabled.

This context records a proposal, not an approval token. The conversation must establish confirmation of these saved descriptions and operations before publishing.

## Verified execution results

- The user confirmed both prepared TC head pushes after reviewing the combined operation proposal, then separately instructed one `/run all` on engine draft PR8128. No follow-up fix, push or rerun was requested.
- Private `origin/tc/pr-8128` was fast-forward pushed and verified at `27db3d6b6d966056de474af277ee40735190f00c`. [Private PR4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365) now reports that head, base `feature/oos-merge` and 44 changed files.
- The reviewed private body was uploaded unchanged. Published UTF-8 SHA-256: `bb2bbe9343b602887d731b29212defa0c28d5c250776838883c48ef534d17eab`; original title, assignees and open/draft status were preserved.
- Public `origin/tc/pr-8128` and [PR3688](https://github.com/CUBRID/cubrid-testcases/pull/3688) were verified at `1a556a0752073aaad573bf87d53f3eb75f398138`, with 34 changed files and the exact reviewed public body; see its companion context.
- `cubrid-pr-tc-base-check --pr 8128` passed for both published heads against the latest fetched corresponding `feature/oos-merge` tips. Engine head remained `a5da823b2a84e95b4b22d48abe4a3f9fd601c176`; no prior same-PR gha-ci run or `/run` request existed.
- Posted one bare [`/run all` comment](https://github.com/CUBRID/cubrid/pull/8128#issuecomment-6096391890). [gha-ci run38043651879](https://github.com/CUBRID/cubrid/actions/runs/38043651879) was picked up: both build contexts and SQL/shell/medium contexts pointed to this one run and were pending at the initial pickup observation. This is a historical pickup receipt; consult the run for later or terminal results.
- The full run includes the published payload unchanged, including the five retained failing/inconclusive normal-discovery reproducers. The user's explicit request selected that full scope; none were silently disabled, relocated or given weaker expectations.
- Local docs integration covers these verified publication records, the four saved body/context files and the curated README. No docs remote push, PR merge/close, base merge, remote deletion or JIRA publication was performed. Source TC worktrees and original snapshots remain available for teammate review; the original unrelated Rope and CCI changes remain preserved.
