# CBRD-26659 public bot TC PR update proposal

Prepared: 2026-10-10 (Asia/Seoul). Agent: codex. Work item: 314. Status: approved public/private TC head pushes and exact reviewed description updates completed; separately requested full CI pickup verified.

## Identity and freshness baseline

- Ticket: CBRD-26659; coordinating engine PR: [CUBRID/cubrid#8128](https://github.com/CUBRID/cubrid/pull/8128), head `a5da823b2a84e95b4b22d48abe4a3f9fd601c176`.
- SOURCE_COMMIT: `1a556a0752073aaad573bf87d53f3eb75f398138`; source and target repository: `CUBRID/cubrid-testcases`; source branch: `tc/pr-8128`; push remote: `origin`.
- Existing PR: [CUBRID/cubrid-testcases#3688](https://github.com/CUBRID/cubrid-testcases/pull/3688); operation: update. State: open, draft; preserve its title, assignees and draft status.
- Existing title: `[CBRD-26659] Draft: TC changes for PR CUBRID/cubrid#8128`; no title change is proposed.
- Base: `feature/oos-merge`, freshly fetched at `bdba62aee0faec05abdd861518824c69b6c1b3c5`; included in SOURCE_COMMIT.
- Observed remote PR head before publication: `003d9e2d619ea2293096d9ce2298d9e72286961c`, the bot's initialization commit.
- Original decoded GitHub body SHA-256: `45f7617d999bca5cd772dfc02fdfe169264351ad7db995feddae266b7fc8d1f9`. Compare UTF-8 bytes without adding a newline.
- SOURCE_COMMIT parents: the observed bot head and validated task payload `c94961578dc43bfe05a74591d52dff30d44a43d3`. Whole Git tree `08b89a48fadc55d20d22dcb653794dc45cef9e77` is identical to the payload; bot history is retained without force.

## Saved material

- Body: `cbrd-26659/CBRD-26659-oos-sql-regressions-pr-body_1a556a0_codex.md`.
- Context: `cbrd-26659/CBRD-26659-oos-sql-regressions-pr-context_1a556a0_codex.md`.
- Companion [private context](CBRD-26659-oos-shell-regressions-pr-context_27db3d6_codex.md) specifies private SOURCE_COMMIT and PR identity. One confirmation can cover the combined operations below.
- Docs task branch: `docs/oos-tc-8128`; integration branch: `main`. No external explanation URL and no docs push are proposed. Original historical source bodies remain preserved.

## Exact combined publication operations

1. Recheck both saved bodies, their material checks, source commits, current remote heads/bodies/PR state and latest feature-base inclusion. Preserve unrelated files. If remote/body/source changes outside this attempt, reconcile and return for review.
2. Push public `tc/pr-8128` at `1a556a0752073aaad573bf87d53f3eb75f398138` to `CUBRID/cubrid-testcases` through `origin`, and private `tc/pr-8128` at `27db3d6b6d966056de474af277ee40735190f00c` to `CUBRID/cubrid-testcases-private-ex` through its `origin`. Both updates are fast-forwards from the observed bot commits; never force or update a base branch.
3. Update only the descriptions of public PR3688 and private PR4365 with their respective saved body files, unchanged. Preserve existing titles, assignees and draft/ready state. Do not create duplicate PRs.
4. Verify both remote heads and exact published body bytes, and record the results in the contexts. Commit the four selected body/context files and README index, including final execution-record updates, then rebase and fast-forward integrate this docs task into local `main`. Audit incoming selection and links, preserve useful local material and safely remove only the merged docs task worktree/branch.
5. Retain both `tc/pr-8128` worktrees/branches and the original validated task snapshots for teammate review. No engine push/body update, docs push, manual CI request, PR merge/close, base-branch merge, remote branch deletion or JIRA publication is proposed.

Confirmation would authorize only these TC head pushes and description updates as an exception to the prior no-push instruction. Publication of the engine coordinator and automatic TC branch creation already completed in the preceding approved phase; local docs main is clean at `d89dd734291a01d6fc008d3c14ee607a3b35f03d` before this new task.

## Evidence and limits

All 34 changed public paths retain their Git blob and mode from the original payload. All 32 selected qualification inputs match the frozen accepted contract in live files and committed blobs. The original source snapshot and all native verdict, independent expectation and cleanup evidence remain unchanged. Source whitespace checks pass; native answer formatting is preserved exactly. There was no new native execution or timing run for the history-only integration.

The full payload contains 17 SQL/answer pairs; the prior passing selected result covers 16. `cbrd_26659_oos_partition.sql` remains a correct failing reproducer in normal discovery paths. The proposed update publishes that known limitation explicitly and does not claim whole-corpus or company-CI success. Full CI still needs an explicit disposition of this SQL case and the four private failing/inconclusive reproducers. No expectations were weakened or cases silently disabled.

This context records a proposal, not an approval token. The conversation must establish confirmation of these saved descriptions and operations before publishing.

## Verified execution results

- The user confirmed both prepared TC head pushes after reviewing the combined operation proposal, then separately instructed one `/run all` on engine draft PR8128. No follow-up fix, push or rerun was requested.
- Public `origin/tc/pr-8128` was fast-forward pushed and verified at `1a556a0752073aaad573bf87d53f3eb75f398138`. [Public PR3688](https://github.com/CUBRID/cubrid-testcases/pull/3688) now reports that head, base `feature/oos-merge` and 34 changed files.
- The reviewed public body was uploaded unchanged. Published UTF-8 SHA-256: `1af702e148a30c4badaf6b1e5b0a3aeb7fde771774beec6a99a6015b5bd0966c`; original title, assignees and open/draft status were preserved.
- Private `origin/tc/pr-8128` and [PR4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365) were verified at `27db3d6b6d966056de474af277ee40735190f00c`, with 44 changed files and the exact reviewed private body; see its companion context.
- `cubrid-pr-tc-base-check --pr 8128` passed for both published heads against the latest fetched corresponding `feature/oos-merge` tips. Engine head remained `a5da823b2a84e95b4b22d48abe4a3f9fd601c176`; no prior same-PR gha-ci run or `/run` request existed.
- Posted one bare [`/run all` comment](https://github.com/CUBRID/cubrid/pull/8128#issuecomment-6096391890). [gha-ci run38043651879](https://github.com/CUBRID/cubrid/actions/runs/38043651879) was picked up: both build contexts and SQL/shell/medium contexts pointed to this one run and were pending at the initial pickup observation. This is a historical pickup receipt; consult the run for later or terminal results.
- The full run includes the published payload unchanged, including the five retained failing/inconclusive normal-discovery reproducers. The user's explicit request selected that full scope; none were silently disabled, relocated or given weaker expectations.
- Local docs integration covers these verified publication records, the four saved body/context files and the curated README. No docs remote push, PR merge/close, base merge, remote deletion or JIRA publication was performed. Source TC worktrees and original snapshots remain available for teammate review.
