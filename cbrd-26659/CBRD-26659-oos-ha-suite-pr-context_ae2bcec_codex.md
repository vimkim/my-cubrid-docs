# CBRD-26659 OOS HA suite publication context

Prepared: 2026-10-28 (Asia/Seoul). Agent: `codex`.

## Source and destination

- Source/target repository: `CUBRID/cubrid-testcases-private`.
- Source branch: `tc/pr-8128`.
- Source commit: `ae2bcec1f6a68fb76e90c0a9d50fec4b3463ca51`.
- Base/integration branch: `develop`, observed commit `c4be1ea3`.
- Proposed title: `[CBRD-26659] Move OOS HA cases to the HA shell suite`.
- Operation: create one **draft** TC PR, assigned to `vimkim`.
- At preparation no open PR matched this repository/head, and no published
  `tc/pr-8128` branch was observed. Recheck both before publication.
- Related Engine PR: <https://github.com/CUBRID/cubrid/pull/8128>.
- Existing private-ex TC PR: <https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365>.
- Engine input: `e3589ae42d42b04eb020e1ae43e165b01d31b12a`, exact CI optdebug build.
- Existing private-ex exclusion: `02d023932b8aa39b2807cc6a77d72f3d58e231d6`, already pushed.

## Saved review files

- Docs repository: `vimkim/my-cubrid-docs`.
- Docs task branch: `docs/oos-ha-histogram-20261028`.
- Docs integration branch: `main`.
- Body: `cbrd-26659/CBRD-26659-oos-ha-suite-pr-body_ae2bcec_codex.md`.
- Context: `cbrd-26659/CBRD-26659-oos-ha-suite-pr-context_ae2bcec_codex.md`.
- Runtime report: `cbrd-26659/CBRD-26659-tc-runtime-histogram_20261028_codex.md`.
- Supporting render assets: `cbrd-26659/assets/tc-runtime-20261028/{oos-histogram,all-suites-histogram}.png`.
- Index: `cbrd-26659/README.md`.

The two images render the report. Raw downloads, case inventories, CSV exports,
interactive HTML, regeneration scripts, native attempts and their logs remain
outside Git. The report records sufficient inputs and concise results.

## Exact proposed publication operations

1. Revalidate the current source commit, clean worktree, base and absence of a
   matching PR. Preserve the six entry files, five helpers and two metadata files.
2. Rebase the docs task onto current local `main`; check incoming history and
   links, then fast-forward it into `main`. Push docs `main` to `origin`, preserving
   all unrelated changes and other worktrees. Include any final execution-record
   commit from this same publication attempt.
3. Push source `ae2bcec1f6a68fb76e90c0a9d50fec4b3463ca51` to the new
   `CUBRID/cubrid-testcases-private:tc/pr-8128` head for this TC PR.
4. Create one draft PR from `tc/pr-8128` to `develop`, assigned to `vimkim`, with
   the exact reviewed title and body. Reuse an already matching PR instead of
   creating a duplicate. Record and verify the final PR URL and body fingerprint.

No Engine source push, existing PR description/title update, TC PR merge/closure,
branch deletion or second CI trigger is proposed. The existing CI run
<https://github.com/CUBRID/cubrid/actions/runs/40692318846> tests the private-ex
exclusion, not this third repository. It completed FAILURE in 42m28s. Both builds, SQL and medium passed. Shell recorded 3,528 PASS, 1 FAIL and 30 SKIP; the unmodified `temp_enc_06` failed its output comparison. No follow-up fix or rerun occurred.

## Verification and remaining limits

- All eleven imported implementation files preserve SHA-256 and mode.
- Bash/Perl syntax passes; four active entries and two disabled entries are present.
- Native final selection: 2 PASS, 2 FAIL, 0 SKIP. Async and failover pass; queue
  and replication fail. The initial full attempt was 1 PASS, 3 FAIL.
- Replication in a separate new-path attempt passes; an original-path async
  control passes. These results do not isolate the cause of variable failures.
- No engine/testcase repair or expectation relaxation was made. No full HA job ran.
- Heavy cutoff remains a tentative 20 seconds. Thirty-eight currently active
  non-HA OOS cases exceed it in run40643373124. No heavy relocation was performed.

Existing public TC PR #3688 and private-ex TC PR #4365 remain OPEN. Their unresolved merge disposition remains a TC Merge Gate dependency. The checks API reported no branch-required checks, so no missing gate is presented as a passing gate.

This context records a proposal, not approval. Establish publication authorization
from the conversation after the user can review the saved files. Capture the
reviewed body fingerprint when confirmed publication begins.
