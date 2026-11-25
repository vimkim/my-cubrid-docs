# CBRD-28094 PR draft context

Resume metadata for the PR body draft. This file is not uploaded.

## Source

| Field | Value |
| --- | --- |
| Ticket | [CBRD-28094](https://jira.cubrid.org/browse/CBRD-28094) |
| Source commit | `f64df11ae676aa2b840b8a996e7d87c810763789` |
| Source branch | `CBRD-28094-debug-log-format-args` (local only) |
| Pre-rebase commit | `214cf3be0ac86636622755f7b0fdd98b658292b9` on `e64a04a79a` (`git range-diff`: identical patch) |
| Base | `develop` at `bfb59bdd13` (`origin/develop`, fetched 2026-11-25) |
| Source push remote | `vk` = `github.com/vimkim/cubrid` |
| Observed remote head | Branch does not exist on `vk` (checked 2026-11-25) |
| Existing PR | None found in `CUBRID/cubrid` for `CBRD-28094` (checked 2026-11-25) |

## Target

| Field | Value |
| --- | --- |
| Target repository | `CUBRID/cubrid` |
| Operation | `create` |
| Proposed title | `[CBRD-28094] Fix format arguments in 16 debug-log calls` |
| Head | `vimkim:CBRD-28094-debug-log-format-args` |
| Base | `develop` |
| Status | Draft |
| Assignee | `vimkim` |

## Documents

| Role | Path |
| --- | --- |
| PR body | `cbrd-28094/pr-body.md` |
| Context | `cbrd-28094/pr-context.md` |
| Explanation | None |
| Docs task branch | `cbrd-28094-pr-body` |
| Docs integration branch | `main` (`origin` = `github.com/vimkim/my-cubrid-docs`) |

## Verification evidence (2026-11-25, source `f64df11ae6`)

- Clean `debug_gcc` build (GCC 11.5.0): success, no new warnings in touched files.
- Temporary `format (printf, ...)` attributes on `_er_log_debug` (3,4),
  `proxy_log_write` (3,4), and a prototype of `cubrid_log_tracelog` (6,7);
  keep-going build (`-k 0`; `-Werror=format-security` stops unrelated TUs).
  - Baseline (touched files restored to `develop`): all 16 sites report
    argument-count or argument-kind warnings; 171 call lines report
    `LOG_TDES*` for `trid=%d`.
  - Patched: 0 warnings of these kinds (`too many arguments`,
    `expects a matching`, `unknown conversion`, `LOG_TDES*`, `LOG_LSA`,
    `wchar_t*`). Width-only `%d` versus 64-bit warnings remain (CBRD-28100).
  - Temporary attributes removed; worktree equals `HEAD`.
- `ctest`: 69/70 passed. `test_oos_real_vacuum_latch_timeout_retry` timed
  out during the full run at host load average about 80; it passed 5 of 5
  isolated reruns (about 17 s each).
- `cubrid-static-check bfb59bdd13..f64df11ae6`: cppcheck 0, clang-tidy
  (bugprone) 0, new clones 0, complexity flags 0 (15 functions, length +1
  at most). No dispositions needed.

## Proposed publication operations (require explicit confirmation)

1. Docs: rebase `cbrd-28094-pr-body` onto `main`, `git merge --ff-only`,
   push `main` to `origin`, remove the docs task worktree and branch.
2. Source: `git push vk CBRD-28094-debug-log-format-args` (new branch, no force).
3. GitHub: `gh pr create --draft --repo CUBRID/cubrid --base develop
   --head vimkim:CBRD-28094-debug-log-format-args` with the proposed title,
   `cbrd-28094/pr-body.md` as the body, and assignee `vimkim`.

## Publication record

Not started.
