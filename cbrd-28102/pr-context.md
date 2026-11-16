# CBRD-28102 PR draft context

Resume and publication bookkeeping for `pr-body.md`. Published as PR #8565.

## Source and target

- Ticket: [CBRD-28102](https://jira.cubrid.org/browse/CBRD-28102)
- Source commit: `436d1cd5bbe14bc09e7cd2e7f6e327972034b0f8`
- Source repository/branch: `vimkim/cubrid` `CBRD-28102-sysop-postpone`
- Observed remote head: branch does not exist on `vk` (2026-11-16)
- Base: `CUBRID/cubrid` `develop`, merge base `666bb10ae673c666c18aa9ae58dda59c9df59fdf`
- Target repository: `CUBRID/cubrid`
- Operation: create (no existing PR found for CBRD-28102)
- Proposed title: `[CBRD-28102] Run the postpone that precedes a system operation`

## Testcase

- Repository: `cubrid/cubrid-testcases-private-ex`, base `develop` `9c12c9185`
- Local branch `tc/CBRD-28102`, commit `45ad935ed`, file `shell/_40_guava/cbrd_28102/cases/cbrd_28102.sh`
- Rename to `tc/pr-<PR number>` after the engine PR exists. TC PR operations are not part of this proposal.

## Docs

- Task branch: `docs/CBRD-28102-pr-body`; integration branch: `main`
- Files: `cbrd-28102/pr-body.md`, `cbrd-28102/pr-context.md`, `cbrd-28102/README.md`

## Proposed operations

1. Push `CBRD-28102-sysop-postpone` (`436d1cd5bb`) to `vk` (`github.com/vimkim/cubrid`).
2. Create a draft PR in `CUBRID/cubrid`, base `develop`, head `vimkim:CBRD-28102-sysop-postpone`, with the title above, body `cbrd-28102/pr-body.md`, assignee `vimkim`.
3. Rebase `docs/CBRD-28102-pr-body` onto `main`, fast-forward `main`, push `main` to `origin`, including a final execution-record commit.

## Static check

`cubrid-static-check 666bb10ae6..436d1cd5bb`: cppcheck 0, clang-tidy 0, CPD 0. lizard: `log_do_postpone` length 242 to 245 (+3, comment lines), CCN 69 unchanged. No defect.

## Verification evidence (2026-11-16)

- Commit path, `postpone_cache_size=4`: unfixed 10/11 (183|13320 not run), fixed 11/11.
- Recovery, kill at `log_postpone_cache::do_postpone` before any run postpone: unfixed 10/11, fixed 11/11; `LOG_DUMMY_CRASH_RECOVERY` present.
- Recovery, kill after the first run postpone was flushed (`log_append_run_postpone` second hit, `logpb_force_flush_pages`): unfixed 10/11 (second postpone 184|256 not run), fixed 11/11.
- Slot 1|651 #4: unfixed `MARKDELETED`, fixed `DELETED_WILL_REUSE`.
- Shell TC, native testkit focused run: unfixed (`666bb10`) Case 2 NOK 10/11; fixed (`436d1cd`) Case 1 and 2 OK. The `testkit-focused.py verify` helper reported "total case count is 22, expected 1" in every attempt because testkit counts 21 macro-skipped cases of the corpus in its total; the case verdicts above come from `test_local.log` and `run.log`.

## Execution record

Confirmation: the user replied "yes" on 2026-11-16 to the three proposed operations above.

- Body fingerprint for this attempt: sha256 `9d8f9bad8135de9cd2271dd5b650aaad6a6771d5c2bd12ea512665962f930140`; material checker passed before the push and before the create.
- Source push: `vk` `CBRD-28102-sysop-postpone` created at `436d1cd5bbe14bc09e7cd2e7f6e327972034b0f8` (verified with `git ls-remote`).
- Draft PR: https://github.com/CUBRID/cubrid/pull/8565, base `develop`, head `vimkim:CBRD-28102-sysop-postpone` at `436d1cd5bb`, draft, open, assignee `vimkim`. The decoded GitHub body equals `pr-body.md` byte for byte (same sha256).
- Docs integration: this commit, rebased onto `main` and fast-forwarded, then `main` pushed to `origin`.
- Pending, not authorized in this proposal: rename the TC branch to `tc/pr-8565`, push it, and open the TC PR.
