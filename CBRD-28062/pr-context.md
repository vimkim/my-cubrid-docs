# CBRD-28062 PR draft context

Not uploaded. Resume metadata for the PR body in `pr-body.md`.

| Field | Value |
| --- | --- |
| Ticket | CBRD-28062 |
| SOURCE_COMMIT | `49d8df0dd5f4f6d6fc3ecd7ff94f87328ed02fc5` |
| Source | `vimkim/cubrid` branch `CBRD-28062-oos-param` (push remote `vk`) |
| Observed remote head | branch absent on `vk` (2026-11-19) |
| Target | `CUBRID/cubrid`, base `feature/oos-merge` (`e262e79fab`, includes PR #8416 squash `c793adf908`) |
| Operation | create (no existing PR for this head) |
| Proposed title | `[CBRD-28062] Make the OOS trigger threshold configurable` |
| Docs branch | `docs/CBRD-28062` → `main` |
| Body | `CBRD-28062/pr-body.md` |

## Proposed operations

1. Integrate docs branch `docs/CBRD-28062` into `main` (rebase, `--ff-only`) and push `main` to `origin`.
2. Push source branch `CBRD-28062-oos-param` at `SOURCE_COMMIT` to `vk`.
3. Create a draft PR: `--repo CUBRID/cubrid --base feature/oos-merge --head vimkim:CBRD-28062-oos-param --assignee vimkim`.

## Authorization

Standing instruction from the user on 2026-11-19 (Asia/Seoul), after the agent listed push + PR, spec merge, and the performance sweep as remaining work: "다 진행하자."

## Static check (cubrid-static-check e262e79fab..49d8df0dd5)

| Check | New |
| --- | --- |
| cppcheck (high-signal) | 0 |
| clang-tidy (bugprone-*) | 0 |
| PMD CPD duplicates | 0 |
| lizard | `heap_manager_initialize` CCN 4→7, `heap_oos_inline_target_size` CCN 1→2; below flag thresholds |

Disposition: nothing to fix.

## Verification evidence

- debug_gcc configure/build/install and ctest 67/67 pass at `SOURCE_COMMIT`, run under the worktree's own environment on 2026-11-19.
- Pre-rebase commit `7ecfbbf1a9` (on PR #8416 head `fba87586b8`) passed native CS/SA INSERT, CS/SA loaddb, and checkdb on 2026-11-16 (Work #982). Rebase changed only the parameter's enum/array position.

## Execution record

- Body fingerprint at review: `e220c6a6536895344683cf550f623d1212ff56f6de1ecfbd579b8d3fc5451e46`
- 2026-11-19: docs `main` pushed at `763b528`.
- 2026-11-19: `vk/CBRD-28062-oos-param` pushed; remote head equals `SOURCE_COMMIT`.
- 2026-11-19: draft PR https://github.com/CUBRID/cubrid/pull/8632 created (base `feature/oos-merge`, assignee `vimkim`). Decoded body equals `pr-body.md` (1,706 characters).

## Revision 2 (2026-11-19, not yet published)

| Field | Value |
| --- | --- |
| SOURCE_COMMIT | `44dab49185` (full: 44dab49185a64f2417b7b8d1ae7d9d4e33335654) |
| Observed remote head | `49d8df0dd5` on `vk/CBRD-28062-oos-param` |
| Operation | update PR #8632 body (title unchanged, stays draft until gha-ci is green) |
| Original GitHub body SHA-256 | `e220c6a6536895344683cf550f623d1212ff56f6de1ecfbd579b8d3fc5451e46` |
| Body SHA-256 at review | `c5151c67fb0a25cfeda173cc6e7409c67c37e781c6efc9690d71a970e27778e7` |

Changes: lower bound raised to the automatic target after an independent review reproduced the CBRD-28035 serial leak with a 64B threshold; interim performance evidence from the CBRD-27788 upper-bound build; CS INSERT and CS loaddb placement check.

Proposed operations: push `44dab49185` to `vk/CBRD-28062-oos-param` (fast-forward); post `/run all`, which cancels the running gha-ci run 44469955870 on the old head; update the PR body; integrate this docs branch and cubrid-oos-context branch `CBRD-28062-lower-bound` into their `main` and push.

### Revision 2 execution record

- 2026-11-19: user confirmed operations 1-4 ("1. yes 2. yes 3. yes 4. yes").
- `vk/CBRD-28062-oos-param` fast-forwarded `49d8df0dd5..44dab49185`; remote head equals `SOURCE_COMMIT`.
- Docs `main` pushed at `fc4c933`; cubrid-oos-context `main` pushed at `bcb834f`.
- PR #8632 body updated; decoded body equals `pr-body.md`. Title and draft status unchanged.
- TC baseline check failed after the base moved to `71993ddb63` (new TCs pair with engine fixes the head lacks). User chose to run as is.
- `/run all` posted at 2026-11-19T06:38:46Z (https://github.com/CUBRID/cubrid/pull/8632#issuecomment-7001812055); gha-ci run 44473683521 picked it up; previous run 44469955870 cancelled. cubrid-ci-watch request 73.

## Revision 3 (2026-11-19, not yet published)

| Field | Value |
| --- | --- |
| SOURCE_COMMIT | `2395d5a8f6b2eda8b051bee248a541187630651f` |
| Observed remote head | `44dab49185` on `vk/CBRD-28062-oos-param` |
| Operation | update PR #8632 body (title unchanged, stays draft) |
| Live GitHub body SHA-256 before update | `c5151c67fb0a25cfeda173cc6e7409c67c37e781c6efc9690d71a970e27778e7` |
| Body SHA-256 at review | `b41dcb06a7a06e2a01cd67abefafa959731d2373c6cbe2d30dfbafd1c3aaea22` |

Changes: systemic review fixes (system classes keep the automatic target; range check skipped during restore; no size units), new test `test_oos_trigger_threshold_system`, 8KiB range, follow-up issues CBRD-28266/28267/28268.

## Revision 4 (2026-11-19, proposed)

- Source head unchanged: `2395d5a8f6b2eda8b051bee248a541187630651f`. PR state: open, ready for review.
- Original GitHub body SHA-256 (decoded, no trailing newline): `ab240972249964d1e3ef05ecddace47376765be79f93fffd8e4bde624b3d94a5`.
- Changes: Implementation states that `str_to_uint64` ignores trailing characters (`8192K` reads as 8192), tracked in CBRD-28267 (Greptile comment 4627581508). Remarks replaces the pending-sweep line with the sweep result and links `CBRD-28062/perf-sweep.md`.
- Proposed operations: (1) ff-merge docs branch `docs/CBRD-28062-perf-sweep` into my-cubrid-docs `main` and push; (2) update the PR #8632 body only; (3) reply to Greptile comment 4627581508 with the text in the session.
