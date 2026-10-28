# CBRD-26659 PR #8128 runtime body refresh

Prepared: 2026-10-29 (Asia/Seoul). Agent: `codex`.

## Target and source snapshot

- Operation: update the body of <https://github.com/CUBRID/cubrid/pull/8128>.
- Target repository: `CUBRID/cubrid`.
- Source repository: `vimkim/cubrid`.
- Source/head branch: `CBRD-26659-oos-testcases-handover`.
- Local source and observed remote head: `e3589ae42d42b04eb020e1ae43e165b01d31b12a`.
- Base: `feature/oos-merge`.
- Existing title: `[CBRD-26659] Initialize OOS testcase review`.
- Existing state: OPEN, ready for review (`isDraft=false`). Preserve both.
- Original GitHub body SHA-256: `6e193b6aae94290c5aa8120f70b9780cdedd9cd533f1195859e77b08959c817d`.
- Read the decoded body without appending a newline for the freshness check.
- Source checkout has preexisting CCI/JDBC dirt. This body-only task preserves it.

## Saved files

- Docs repository: `vimkim/my-cubrid-docs`.
- Task branch: `docs/pr8128-runtime-body-20261029`.
- Integration branch: `main`.
- Body: `cbrd-26659/CBRD-26659-oos-ci-runtime-refresh-20261029-pr-body_e3589ae_codex.md`.
- Context: `cbrd-26659/CBRD-26659-oos-ci-runtime-refresh-20261029-pr-context_e3589ae_codex.md`.
- Index: `cbrd-26659/README.md`.
- No new explanation, supporting asset, raw download or testcase inventory is retained in Git.

## Proposed publication operations

1. Reread the saved body after user review. Validate its current content and record its fingerprint.
2. Verify that local source and PR head still equal `e3589ae42d42b04eb020e1ae43e165b01d31b12a`.
3. Verify the original body fingerprint, title, base, source repository/branch and ready/open state.
4. Rebase the docs task onto current local `main`. Audit the incoming history and links.
   Fast-forward merge into a clean `main` checkout and push docs `main` to `origin`.
5. Upload the exact reviewed body to PR #8128. Preserve title and ready/open state.
6. Verify the published body bytes and record the result in this context.
   Integrate and push that execution-record commit under the same approval.
   Preserve valuable files before removing this merged docs task worktree and local branch.

No source/TC push, PR #7990 body update, existing title/status change, CI trigger,
TC migration, TC PR merge/closure or TC branch deletion is proposed.
The earlier approval for HA draft PR #1666 did not include existing PR body updates.
This is a new review proposal, not a stored permission token.

## Scope of the body edit

The current branch's PR is #8128. Its Remarks still compare the earlier 47m14 and
57m full executions and call the latest #7990 result a partial rerun. This proposal
uses the newly completed full run instead. The #7990 body remains outside this update.

Purpose, public SQL counts and the Engine implementation bullet retain their
current wording. Private execution selection now distinguishes 69 regular-CI
entries, 66 previously disabled entries and four excluded HA entries.
The separate HA draft PR #1666 has four enabled cases and two disabled reproducers.
No testcase selection or threshold changes occur in this wording task.

## Evidence and limits

- Baseline: [run40738391553](https://github.com/CUBRID/cubrid/actions/runs/40738391553),
  Engine `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`, public TC
  `70db22a1c99dbbaa27fa1438c8967effdfcad551`, private TC
  `75a02020e19be4bfc64e47f7c7a3d5c2b02d7676`.
- OOS TC including run: [run40692318846](https://github.com/CUBRID/cubrid/actions/runs/40692318846),
  Engine `e3589ae42d42b04eb020e1ae43e165b01d31b12a`, public TC
  `45e21ad799d82ebadc04a93c7d2f69517d53bf39`, private TC
  `02d023932b8aa39b2807cc6a77d72f3d58e231d6`.
- Both attempt 1, full selection, CTP `ef6712ab450a9c8a6b5bf41d605b1683bd60a3a2`,
  reused debug artifacts and 50 shell / 10 SQL / 1 medium shards.
- Baseline wall 2650s (44m10); OOS-side wall 2548s (42m28), difference -102s.
- Medium spans 184s→197s; SQL 843s→821s; shell 2456s→2376s.
  Spans are first shard start through last shard end, not summed suite time.
- Shell cumulative shard time 99,116s→101,686s, +2570s (+2.59%).
- Baseline shell: 3459 PASS / 1 FAIL / 30 SKIP. OOS-side shell: 3528 PASS / 1 FAIL / 30 SKIP.
- SQL 17,630 and 17,655 cases respectively all PASS. Medium 975/975 PASS in both.
- No planned case is unaccounted for. Shell plan sets differ only by the added 69 OOS entries.
  Actual SQL result identities differ only by 25 added OOS cases; medium identities match.
- Failures are `parameter_combine` on baseline and `temp_enc_06` on OOS side.
  No failure cause or relation to OOS is established by this timing comparison.
- One run per side with different Engine revisions, builds, failed cases and scheduling.
  This is an elapsed-time observation, not an isolated causal testcase cost or speedup.
- Heavy migration remains unperformed. Twenty seconds remains a tentative cutoff.
- Historical 47m14→57m material is retained at its original revision and date.

Raw API responses, job/stamp/status/summary evidence, provenance logs, reproducible
collectors and the original decoded body snapshot remain outside Git.

## Publication result

- The user confirmed the saved material and listed operations after the review handoff.
- Published and verified at 2026-10-29 03:53:38 (Asia/Seoul).
- Updated only the body of <https://github.com/CUBRID/cubrid/pull/8128>.
- The decoded GitHub body matches the reviewed body file byte for byte.
- Reviewed and published body SHA-256: `fe16afba3aa83ef50068b489e0eb3114353701403c7e25bc666f70e30be37d58`.
- Before the write, the source head and original body fingerprint matched the preparation snapshot.
- The title, `feature/oos-merge` base, source repository/branch, source head
  `e3589ae42d42b04eb020e1ae43e165b01d31b12a`, OPEN state and ready state remain unchanged.
- The material checker passed immediately before the write.
- Docs preparation commit `86371992fec7bb7feace1384e34fc57ee9603549` was rebased onto local `main`,
  fast-forward merged and pushed to `origin/main`; the remote tip was verified.
- This context and its index record the publication result under the same approved operations.
- No source/TC push, CI trigger, PR #7990 body update, TC PR merge/closure or TC branch deletion occurred.
- Preexisting CCI/JDBC changes remain outside this task.
