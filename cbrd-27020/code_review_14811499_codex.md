# Code Review: CBRD-27020 / PR #7604

| Item | Value |
|---|---|
| Ticket | [CBRD-27020](http://jira.cubrid.org/browse/CBRD-27020) — SHOW INDEX CAPACITY parallelize |
| Pull request | [CUBRID/cubrid#7604](https://github.com/CUBRID/cubrid/pull/7604) — `[CBRD-27020] Parallelize SHOW INDEX CAPACITY` |
| Review date | 2026-09-23 (Asia/Seoul) |
| Pinned head | `14811499e4f73b5b26ad74753df0e66866c655c1` |
| Live fixed point | `origin/develop` = `0320a768b09bda9e58e93875398450b0580c8e22` |
| Merge-base | `a0c1b6c4157fd58b241123270b06c74b019b2027` (also the PR's recorded base OID) |
| Exact comparison | `git diff origin/develop...HEAD` |
| Diff | `src/storage/btree.c`, 672 insertions and 6 deletions |
| Final decision | **COMMENT** |
| Published review | [COMMENTED review #5288632280](https://github.com/CUBRID/cubrid/pull/7604#pullrequestreview-5288632280), submitted against the pinned head |

## Scope and evidence

The review kept the source worktree unchanged and used the live PR head and live `origin/develop` ref. The three-dot comparison resolves to the PR's recorded base commit, so the reviewed patch is the complete PR patch rather than changes added to `develop` after the PR branch point.

Evidence inspected:

- Personal CUBRID policy: `/home/vimkim/my-cubrid/CUBRID.md`.
- Applicable repository guidance: `AGENTS.md`, `src/AGENTS.md`, `src/storage/AGENTS.md`, and `CONTRIBUTING.md`.
- Authoritative issue fetched with `cubrid-jira search CBRD-27020`: `/home/vimkim/.local/share/cubrid-jira/issues/CBRD-27020.md`.
- PR title/body, changed files, full commit metadata, review requests, issue comments, all seven review threads, prior reviews, and current checks/statuses.
- The complete three-dot diff and relevant surrounding implementation in `btree.c`, including the unchanged serial capacity traversal.
- Related worker/perfmon behavior in `perf_monitor.c`, `px_worker_manager.cpp`, `px_callable_task.*`, `thread_entry_task.cpp`, and the existing parallel heap-capacity implementation.
- Linked testcase PRs `cubrid-testcases#3184` and `cubrid-testcases-private-ex#3810`; both are open drafts with no changed files.

Commit list reviewed:

```text
14811499e Merge remote-tracking branch 'upstream/develop' into index-capacity-parallel
80afb2b24 [CBRD-27020] Correct the parallel capacity comments
2658fcf7b [CBRD-27020] Rename btree_capacity_reduce to btree_capacity_run_workers
535a2501b [CBRD-27020] Take the worker's prefix length from the gleaned index config
3b89dd875 [CBRD-27020] Read the root's node header through the root header
3bbe39d27 [CBRD-27020] Decline parallel capacity when the page-count probe fails
339dd410c [CBRD-27020] Report the capacity reducer's real failure cause
1d43e3ab3 [CBRD-27020] Leave the capacity workers' pool entry clean
2710c7900 [CBRD-27020] Merge the two capacity accumulators into one template
893dcedfe [CBRD-27020] Shape the capacity dispatcher like heap_get_capacity
61980aee1 [CBRD-27020] Let the first capacity worker error win
c15146adb Merge remote-tracking branch 'upstream/develop' into index-capacity-parallel
7c48a08c7 [CBRD-27020] Detect a failed root key-domain glean in the capacity dispatcher
9d1a6689f [CBRD-27020] Tell a real capacity failure apart from declining parallelism
d83de10d3 Merge remote-tracking branch 'upstream/develop' into index-capacity-parallel
26e62d00b [CBRD-27020] Correct the capacity dispatcher's safety comment
955dd62a9 [CBRD-27020] Keep the capacity reducer free of C++ exceptions
9637f04ef [CBRD-27020] Tell a real capacity failure apart from declining parallelism
e84bd0c2b [CBRD-27020] Match the serial capacity path on page checks and averages
800e435cf [CBRD-27020] Give the capacity workers their own perfmon buffer
aff7c71fa Parallelize SHOW INDEX CAPACITY
```

## Validation

- `git rev-parse HEAD origin/pr/7604` confirmed both refs at `14811499e4f73b5b26ad74753df0e66866c655c1` before and after review.
- `git diff --check origin/develop...HEAD` passed.
- Exact-head GitHub checks passed for license, PR style, code style, cppcheck, and memory-monitor checks.
- Exact-head build and regression statuses passed for debug build, release build, SQL, medium, and shell suites. CircleCI build/build_debug/test_sql/test_medium and GitHub Actions build/test statuses were successful.
- The merge gate remains blocked only because the two linked testcase PRs are still open drafts; the testcase PRs contain no file changes. One CircleCI `download-build` context is recorded as failed even though the downstream CircleCI build and test contexts passed.
- No local compile or runtime experiment was run because this fresh review worktree had no configured build directory; exact-head CI results and targeted source inspection were used instead.
- Source worktree status remained clean; no source file was edited or checked out/reset.

## Standards

### S1. Legacy `.c` C++ guard/comment form is not followed

- **Severity:** Low
- **Classification:** Hard documented-standard violation, directly actionable
- **Evidence:** `src/storage/btree.c:10092-10096`, `src/storage/btree.c:10221-10225`, `src/storage/btree.c:10264-10267`, and `src/storage/btree.c:9985-10012`

The three newly added C++ regions use `// *INDENT-OFF*` / `// *INDENT-ON*`. The personal CUBRID policy requires C++ syntax added to legacy `.c` files to use the exact block-comment markers `/* *INDENT-OFF* */` and `/* *INDENT-ON* */`; the repository root guidance also requires block comments in C files. The new template beginning at line 9985 is C++-specific syntax and has no guard at all.

Replace the three marker pairs with the mandated block-comment form and bracket the template with the same markers. The repository code-style check passed, so this review finding is not duplicating an automated failure.

### S2. Parallel finalization duplicates the serial average formulas

- **Severity:** Low
- **Classification:** Judgement call — possible Duplicated Code
- **Evidence:** `src/storage/btree.c:10053-10072` duplicates the formula set at `src/storage/btree.c:9896-9915`

The parallel reducer repeats `avg_val_per_*`, `avg_*_len`, `avg_pg_key_cnt`, and both free-space-average formulas from the serial finalization. This leaves two places that must remain behaviorally aligned. A shared finalization helper could reduce drift, while accepting explicit INT64 key/record-length numerators so the parallel path's intentional precision behavior remains visible. This is an optional design improvement, not a correctness blocker.

## Spec

### P1. Perfmon buffer OOM is swallowed and restores the race the requirement intends to remove

- **Severity:** Medium
- **Classification:** Required behavior implemented incorrectly
- **Evidence:** `src/storage/btree.c:10121-10134`; supporting behavior at `src/base/perf_monitor.c:3436-3458` and `src/base/perf_monitor.c:1079-1104`

The ticket requires that, when `on_trace` is enabled, every worker has its own perfmon buffer (JIRA line 39), and it lists memory exhaustion among failures to propagate (JIRA line 65). `perfmon_initialize_parallel_stats()` reports allocation failure as `ER_OUT_OF_VIRTUAL_MEMORY` and leaves `m_uses_px_stats` false. The new worker code then explicitly clears that error and continues.

As its own comment notes, workers then fall back to the caller's shared `pstat_Global.tran_stats[]`. Those updates are non-atomic, reintroducing the data race this part of CBRD-27020 is intended to prevent. Treat initialization failure as the worker's first `ER_OUT_OF_VIRTUAL_MEMORY`, stop that scan, and propagate it through the existing worker-failure channel.

No other missing requirement, incorrect behavior, or scope creep was found. In particular, the dispatcher/fallback split, serial dump path, root-latch lifetime, dynamic root-child claiming, worker join/reduction, decline cases, key-domain failure handling, and SA/CS serial behavior match the fetched ticket description.

## Final decision

The head was not approved because P1 is a correctness/spec issue and S1 is a directly actionable documented-standard violation. A concise Korean `COMMENT` review was published as [review #5288632280](https://github.com/CUBRID/cubrid/pull/7604#pullrequestreview-5288632280), state `COMMENTED`, commit `14811499e4f73b5b26ad74753df0e66866c655c1`.

**Summary: Standards 2 findings (worst: Low, hard guard/comment-form violation); Spec 1 finding (worst: Medium, perfmon OOM restores a shared-counter race).**
