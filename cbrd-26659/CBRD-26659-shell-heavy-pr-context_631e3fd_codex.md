# CBRD-26659 shell_heavy publication context

Prepared: 2026-10-29, Asia/Seoul. Agent: `codex`.

## Scope and source identities

The user requested a persistent TODO checklist and selected passing shell cases
over 20 seconds as the first migration. This preparation separates the 38 cases
without changing their assertions, expected values, bytes, or modes. Historical
failures, three previously disabled slow PASS cases, and HA cases stay separate.

| Change | Repository and local branch | Commit | Publication target |
| --- | --- | --- | --- |
| Heavy import | `vimkim/cubrid-testcases-private-ex`, local `CBRD-26659-oos-shell-heavy` | `631e3fd3cbc202cec45b56ae6cec7e4f1c86e2f1` | New fork head `tc/pr-8128`, draft PR into `CUBRID/cubrid-testcases-private-ex:feature/oos-merge` |
| Regular exclusion | `CUBRID/cubrid-testcases-private-ex:tc/pr-8128` | `a229e1978abc4cc6c280783703c03f75524c0f05` | Existing [PR #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365) |

The import starts at feature base `75a02020e19be4bfc64e47f7c7a3d5c2b02d7676`.
The original source and observed organization remote head are
`02d023932b8aa39b2807cc6a77d72f3d58e231d6`. The personal fork exists and the
authenticated user has push permission. No fork `tc/pr-8128` head or matching
open PR was observed during preparation. Recheck before publication.

The organization and fork heads deliberately share the authoritative
`tc/pr-8128` name in different repositories. The two diffs are independent against
`feature/oos-merge`. They do not require an extra Engine carrier PR or a PR based
on the bot-managed testcase head. Both testcase PRs still need human review and
integration. Do not merge, close, or delete either testcase branch.

Engine [PR #8128](https://github.com/CUBRID/cubrid/pull/8128) remains at
`e3589ae42d42b04eb020e1ae43e165b01d31b12a` in
`vimkim/cubrid:CBRD-26659-oos-testcases-handover`, targeting `feature/oos-merge`.
Public SQL [PR #3688](https://github.com/CUBRID/cubrid-testcases/pull/3688) remains
at `45e21ad799d82ebadc04a93c7d2f69517d53bf39` and is outside the change.

## Files for human review

- Docs repository: `vimkim/my-cubrid-docs`.
- Docs task branch: `docs/cbrd-26659-status-ko-20261029`; integration: `main`.
- New title: `[CBRD-26659] Move passing OOS cases to shell_heavy`.
- New PR body: `cbrd-26659/CBRD-26659-shell-heavy-pr-body_631e3fd_codex.md`.
- Existing PR body: `cbrd-26659/CBRD-26659-shell-heavy-exclusion-pr-body_a229e19_codex.md`.
- This context: `cbrd-26659/CBRD-26659-shell-heavy-pr-context_631e3fd_codex.md`.
- Checklist: `cbrd-26659/CBRD-26659-todo-checklist_20261029_codex.md`.
- Existing status report: `cbrd-26659/CBRD-26659-status-report_20261029_e3589ae_codex.md`.
- Supporting verifier: `cbrd-26659/tools/verify-heavy-transfer.py`.
- Ticket index: `cbrd-26659/README.md`.

The existing status report's local commit `83b2eaf` is part of this docs branch
and has not entered `main`. Include it in the incoming-history review. The
verifier is retained so the paired imports, exclusions, and preservation checks
can be repeated. Logs, raw downloads, scratch scripts, native attempts, and
generated exports remain outside Git.

## Existing PR freshness

- Target: `CUBRID/cubrid-testcases-private-ex#4365`.
- Existing title: `[CBRD-26659] Draft: TC changes for PR CUBRID/cubrid#8128`.
- Existing state: OPEN, ready for review; preserve both.
- Head/base: organization `tc/pr-8128` to `feature/oos-merge`.
- Observed remote head: `02d023932b8aa39b2807cc6a77d72f3d58e231d6`.
- Original decoded UTF-8 body SHA-256, with no appended newline:
  `7af46c51dd40ebf5738bebfb8678365d10d3d1eac74335e4d7f8ec8c26b90bcd`.

The revised body preserves the existing Purpose. Implementation reflects the
paired heavy exclusion and HA split. Remarks distinguish historical CI from
the pending qualification of the new regular selection. A changed source,
destination, or body requires reconciliation before publication.

## Verification

- 38 candidate entries came from one CI observation,
  [run 40643373124](https://github.com/CUBRID/cubrid/actions/runs/40643373124),
  private TC `479035a45f06545db1974e1369e88000fb98a89a`, Engine `e3589ae`.
  They all passed and took strictly more than 20 seconds in that run.
- Static source closure is 38 entries and 34 support files. All 72 imported
  files match the original source bytes and Git modes. The 38 archived entries
  match too; remaining 31 inventory entries, all 70 prior exclusions, and
  original support remain unchanged. The 70 files include 66 older disabled
  cases and four HA exclusions.
- All four original TDE companion files remain. In particular, the disabled
  `cbrd_26659_tde_storage` reproducer still reaches its original observer and AWK
  helper. The independent heavy import includes its own complete support closure.
- All 55 imported Bash files passed syntax checks. Static discovery finds
  exactly 38 new OOS heavy entries and 31 remaining OOS regular entries.
  Heavy's complete preexisting-plus-new category has 138 entries; the focused
  native run selects only the new 38.
- The original default loaded install was `1ef86a7` and failed identity
  preflight. No mismatch exception was used. New disposable CUBRID and CTP
  copies of the retained exact `e3589ae` optdebug CI artifact passed preflight;
  containment is available. The source's preexisting CCI/JDBC dirt is preserved.
- The relocated `utility_sa` smoke attempt passed 1/1 with no failures or skips.
- Full verification of 38 relocated cases completed serially with
  `TESTKIT_NATIVE=shell`, `TESTKIT_CONTAIN=1`, `scenario_disk=on`, file feedback,
  no updates, retry, or continuation, and a 120-second timeout per testcase.
  The result is **38 PASS, 0 FAIL, 0 SKIP**. Exact dispatch and completion sets,
  assertions, summary and XML passed the focused verifier. All 38 unique XML
  testcase records have no failure, error, or skip; every recorded duration is
  below 120 seconds, from 8.606 to 58.963 seconds. This is one local native
  observation, not a speed comparison with CI. Selection retains the original
  CI-based 20-second criterion rather than reclassifying cases by host timings.
- Execution started from the transferred working files before the local TC
  commit was recorded. The attempt identities preserve that fact, the exact
  input hashes and patch. Static checks before and after execution bind all
  72 unchanged files and modes to committed heavy `631e3fd`; Git metadata
  changes did not change the executed testcase material.
- The unmodified vendor `LICENSE.MIT` line 1 has a trailing space at the pinned
  source. Full `git diff --check` flags that imported line. Its original bytes
  are preserved; the check passes with that exact vendor license excluded.
- Current `gha-ci` does not include `shell_heavy`. Native execution does not
  establish the QA heavy job's schedule, ownership, or whole-corpus qualification.
- The new fork PR has not been created. Its association with the automated TC
  Merge Gate is unverified; report the actual gate state after publication.

The read-only verifier accepts `--regular` and `--heavy` checkout arguments.
It compares actual files with the pinned Git source, not cached observations.

## Exact proposed publication operations

1. Reread the reviewed body files and checklist. Verify source commits, clean
   task worktrees, current remote refs, original body fingerprint and absence of
   an already matching fork PR. Record the reviewed body fingerprints.
2. Rebase the docs task on current local `main`. Audit every incoming commit and
   path, validate links/material, fast-forward into clean `main`, and push docs
   `main` to `origin`. Include final execution-record commits under the same
   approval and preserve other worktrees and local material.
3. Push heavy `631e3fd3cbc202cec45b56ae6cec7e4f1c86e2f1` to
   `vimkim/cubrid-testcases-private-ex:tc/pr-8128`. Create one draft PR against
   `CUBRID/cubrid-testcases-private-ex:feature/oos-merge`, assigned to `vimkim`,
   with the exact reviewed title/body. Reuse an already matching PR rather
   than duplicate it. Verify its head and body.
4. After the heavy draft is verified, push regular exclusion
   `a229e1978abc4cc6c280783703c03f75524c0f05` to organization
   `CUBRID/cubrid-testcases-private-ex:tc/pr-8128`. Upload the exact reviewed
   existing-PR body. Preserve its title and ready/open state. Verify both.
5. Trigger exactly one normal qualification CI on Engine PR #8128 after the
   testcase pushes. Wait for its terminal result and report suite verdicts,
   the run URL and any testcase merge blockers. This CI validates the regular
   selection; it does not execute the heavy category.
6. Update the checklist and this context with verified publication and CI
   results, integrate/push those docs records under the same approval, then
   stop. No follow-up fix, push or rerun follows a CI failure without direction.

No Engine or public SQL source push, TC merge/closure, remote branch deletion,
force push, QA messaging, or general heavy-CI implementation is proposed.
The GitHub app cannot read the private personal fork, while authenticated `gh`
can. Use the existing authenticated CLI for fork publication if app access
remains unavailable. This is a capability fallback, not a request to alter
permissions or create another fork.

This context proposes operations. Publication still requires the user's
confirmation after the completed files are available for review.

## Publication result, 2026-10-29

The user replied `yes` after the completed files and exact operations were
presented. The preparation sections above preserve the reviewed snapshot.

- Rebased the two docs commits onto current local `main` without conflicts.
  Both approved body fingerprints were unchanged. The rebased commits are
  `218e226` and `4117e83`; fast-forwarded and pushed docs `main` at
  `4117e83d8898eb3e4ad47ddca593ab23cb8e785b`.
- Pushed heavy source `631e3fd3cbc202cec45b56ae6cec7e4f1c86e2f1` to
  `vimkim/cubrid-testcases-private-ex:tc/pr-8128` and verified its remote SHA.
- Created [draft heavy PR #4627](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4627),
  personal-fork `tc/pr-8128` to organization `feature/oos-merge`, assigned to
  `vimkim`. The title and OPEN/draft state match the proposal. Its 74 changed
  files are the 72 imported implementation files, manifest and README.
- Verified the new PR body equals the approved file, SHA-256
  `b0a02477bebf20d18669cbd7b70032f1c540a872f27be9c2db9cd293d3ed6412`.
- Pushed regular exclusion `a229e1978abc4cc6c280783703c03f75524c0f05` to
  `CUBRID/cubrid-testcases-private-ex:tc/pr-8128` and uploaded the exact approved
  PR #4365 body. Verified the published head, title and OPEN/ready state.
  The body SHA-256 is
  `556fac919d9d1edb0d48c85b3f139028b768f88a331641ea260fa0ac59f6f8bc`.
- The post-push feature-baseline check passed in both testcase repositories.
  Public TC is `45e21ad799d82ebadc04a93c7d2f69517d53bf39`; private TC is
  `a229e1978abc4cc6c280783703c03f75524c0f05`.
- After verifying that the old linked run was terminal and no competing
  command appeared, posted exactly one
  [`/run all` comment](https://github.com/CUBRID/cubrid/pull/8128#issuecomment-6491066013).
  All five gha-ci contexts pointed to the new
  [run 40837919358](https://github.com/CUBRID/cubrid/actions/runs/40837919358),
  attempt 1, Engine `e3589ae42d42b04eb020e1ae43e165b01d31b12a`.
- CI is pending at this checkpoint. Its result is not yet PASS. It qualifies
  the regular selection and does not execute the heavy category.

No Engine/public SQL push, TC merge/closure, branch deletion, extra CI trigger,
follow-up fix, or expectation change occurred. Heavy scheduling and actual
TC review/merge remain unfinished. The required-check query reports no required
checks for this Engine branch; this does not make the open TC PRs completed.

## Terminal CI result and evidence limits

[Run 40837919358](https://github.com/CUBRID/cubrid/actions/runs/40837919358),
attempt 1, completed with GitHub conclusion **SUCCESS** at
2026-10-29 09:37:42 UTC (18:37:42 Asia/Seoul). All 50 shell, 10 SQL and one
medium shard succeeded. The five commit contexts, debug build, release build,
shell, SQL and medium, all report SUCCESS and link to this same run.

The plan and retained shard identities confirm Engine
`e3589ae42d42b04eb020e1ae43e165b01d31b12a`, public TC
`45e21ad799d82ebadc04a93c7d2f69517d53bf39`, and organization private TC
`a229e1978abc4cc6c280783703c03f75524c0f05`. The cached debug artifact's producer
is run `40472072791`, attempt 1, for that same Engine commit; this is not a new
Engine build or a different tested source. The CI did not use the personal
fork's heavy head.

| Suite | GitHub CI | Exact-run artifact verification |
| --- | --- | --- |
| shell | SUCCESS | 3,521 planned; 3,491 PASS, 0 FAIL, 0 error, 30 SKIP, 0 unrun |
| medium | SUCCESS | 975 planned; 975 PASS, 0 FAIL, 0 error, 0 SKIP, 0 unrun |
| SQL | SUCCESS | Incomplete: workflow and JUnit counts disagree in shard 01; no certified total PASS count |

`cubrid-ci collect 8128 --commit e3589ae42d42b04eb020e1ae43e165b01d31b12a`
collected all three suite statuses from this exact run. It accepted shell and
medium artifacts, but exited 4 with an integrity error for SQL:
`result identity mismatch: shard 01 workflow result and JUnit counts disagree`.
This is an evidence-collection failure despite the successful GitHub verdict.

[SQL shard 01](https://github.com/CUBRID/cubrid/actions/runs/40837919358/job/123327783700)
reports `assigned 3533 / run 3533 / failed 0 / skipped 0` in its executed verdict.
Its retained `shard.done` assigns 3,533 cases, while `summary_info` and actual
JUnit testcase elements both contain 3,531. Across the ten SQL shards, assigned
counts total 17,655 and JUnit testcase elements total 17,653. The source of the
two-count difference is not established. Do not call it an Engine/TC failure,
infer which cases are missing, or certify complete SQL coverage from this run.
The checklist records this discrepancy as a separate unfinished follow-up.

The verified shell plan is 38 entries smaller than the prior 3,559-entry plan,
consistent with the transfer manifest. The 31 remaining OOS regular entries
and the 38 excluded/heavy entries are also verified by the retained static
verifier. Actual CI XML contains exactly those 31 OOS regular paths, each PASS
with no skip, failure or error, and contains none of the 38 transferred paths.
The heavy category's execution evidence remains the separate native
38 PASS, 0 FAIL, 0 SKIP run; ordinary CI does not run `shell_heavy`.

Both TC PR heads and approved body bytes were rechecked after CI. Heavy #4627
is OPEN/draft at `631e3fd`; regular #4365 is OPEN/ready at `a229e19`. Neither was
merged or closed. The final required-check query again reports no required
checks on this feature branch. A named failed TC Merge Gate or automatic gate
association for the fork PR is therefore not established. Human TC review and
merge, QA heavy scheduling, historical failures, older slow PASS cases and HA
follow-ups remain unfinished.

No second CI trigger, rerun, repair, source/TC push, PR body rewrite, TC merge,
closure or branch deletion followed this result. Final result records are
integrated into docs `main` under the same publication approval.

## SQL accounting follow-up, 2026-10-30

The [focused SQL count investigation](CBRD-26659-sql-count-discrepancy_20261030_run40837919358_codex.md)
identifies the two text-only paths under `cbrd-27556`. Exact CTP classes reproduce
an aggregate/JUnit traversal defect when a category contains both direct cases
and nested case categories. A layout-only control retains all three seeded
results. This explains how one result generation can produce the observed
two-count difference without stale data or mixed acquisition being necessary.

The investigation is complete; repair is not. The original SQL collection stays
`collection_failed`, and no complete SQL PASS count is certified. The probe does
not independently establish the historical two cases' full execution or PASS.
No CI rerun, Engine/TC/CTP repair or PR body change followed this investigation.
