# CBRD-28271 PR draft context

Bookkeeping for the PR body in [pr-body.md](pr-body.md). This file is not uploaded.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | [CBRD-28271](https://jira.cubrid.org/browse/CBRD-28271) |
| Source commit | `fd7d071ed5c625612d6035a5028d99f74b0922d7` |
| Source repository / branch | `vimkim/cubrid` / `CBRD-28271` (remote `vk`) |
| Remote head at preparation | branch does not exist on `vk` (2026-11-25) |
| Base | `develop` at `bfb59bdd13` (the commit's parent; `origin/develop` tip on 2026-11-25) |
| Target repository | `CUBRID/cubrid` |
| Operation | `create` (no existing PR for head `CBRD-28271`); result PR #8736 |
| Proposed title | `[CBRD-28271] Check that a serial row fits before logging its redo` |
| PR state | new draft PR, assignee `vimkim` |

## Testcase change

| Field | Value |
| --- | --- |
| Repository | `CUBRID/cubrid-testcases-private-ex` |
| Local commit | `9dbb84c93` on local branch `CBRD-28271`, based on `origin/develop` `1c3d89914` |
| Path | `shell/_06_issues/_26_2h/cbrd_28271/cases/cbrd_28271.sh` |
| Destination | `tc/pr-<N>` created by `TC Branch Sync` after the engine PR opens |

## Verification evidence (2026-11-25)

- Manual repro, release builds `11.5.0.3059-bfb59bd`: without the fix, SA and server restart and `checkdb` stop with `LOG FATAL ERROR: log_rv_redo_record_sync ... vpid=(0, 3777), offset = 1, data_length = 766`; with the fix, both succeed and `sa` keeps `current_val` 1.
- Focused shell run (native cubrid-testkit, contained) of `cbrd_28271`, engine `fd7d071ed5`, TC `9dbb84c93`: debug_gcc pass (10/10 assertions, total=1 success=1 fail=0); release_gcc pass (same). An earlier attempt on TC `4b0ab00c1` failed because CTP `init.sh` has no `wait_until`; the TC now defines `wait_for`.
- Not run: the TC against the unfixed build through testkit (needs `--allow-commit-mismatch`), ctest.

## Static check (`cubrid-static-check bfb59bdd13 fd7d071ed5`, 2026-11-25)

| Check | New | Disposition |
| --- | --- | --- |
| cppcheck (high-signal rules) | 0 | - |
| clang-tidy (bugprone-*) | 0, incomplete | clang-tidy exited 1 on `src/query/serial.c` for both base and head; 1 head finding was not compared and its text was not reported. Not a known defect of this change. |
| Duplicated code (PMD CPD) | 0 | - |
| Function complexity (lizard) | `serial_update_serial_object` CCN 17 → 18, length 108 → 114 | Expected: one added `if`. Below the flag thresholds. |

## Proposed publication operations

1. Docs: rebase `cbrd-28271-pr-body` onto `main`, `git merge --ff-only`, push `main` to `origin` (files: `cbrd-28271/pr-body.md`, `cbrd-28271/pr-context.md`, `cbrd-28271/README.md`), remove the task worktree and branch.
2. Source push: `git push vk CBRD-28271` (commit `fd7d071ed5`).
3. Create a draft PR in `CUBRID/cubrid`: base `develop`, head `vimkim:CBRD-28271`, the proposed title, body from `cbrd-28271/pr-body.md`, assignee `vimkim`.
4. After `TC Branch Sync` creates `tc/pr-<N>` in `CUBRID/cubrid-testcases-private-ex`: apply TC commit `9dbb84c93` on `origin/tc/pr-<N>` and push to `origin tc/pr-<N>`.
5. Record the results below.

CI triggering is not part of these operations.

## Execution record

Confirmed by the user in the session on 2026-11-25 ("yes" to the listed operations). Attempt body fingerprint: sha256 `24d5c23d214f713cb2306918a396985b571605cc970bfc413737ab99e8ef3cf9`.

1. Docs: `c8dc88c` fast-forwarded onto `main` and pushed to `origin`.
2. Source: `git push vk CBRD-28271`; remote head verified `fd7d071ed5c625612d6035a5028d99f74b0922d7`.
3. PR: [CUBRID/cubrid#8736](https://github.com/CUBRID/cubrid/pull/8736) created as draft, base `develop`, head `vimkim:CBRD-28271` at `fd7d071ed5`, assignee `vimkim`, title as proposed. Uploaded body is byte-identical to `pr-body.md` (sha256 above).
4. TC: `TC Branch Sync` created `tc/pr-8736` (init commit `830675851`, no file changes) and draft TC PR [CUBRID/cubrid-testcases-private-ex#5146](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5146). TC commit `9dbb84c93` cherry-picked as `c954b8366` and pushed to `origin tc/pr-8736`; remote head verified. The TC PR title, body, and draft status are unchanged.
5. Not done: CI trigger, TC PR description update.

## Decisions

- 2026-11-25: The user kept the scope of this PR (the "1. 좋아" reply to the decision list). PR #8736 adds only the space check before the redo-only log. `NEXT VALUE` still fails when the row does not fit. The fallback and the relocated serial row (CBRD-28272) stay in CBRD-28292, as the PR body Remarks state. No source or body change follows from this decision.
- CI analysis of run 45567167574 treats a `NEXT VALUE` failure from lack of page space as the intended behavior. Other failures get a separate cause analysis.
