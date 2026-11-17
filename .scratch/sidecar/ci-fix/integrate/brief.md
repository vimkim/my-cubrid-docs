# Integrate the five Sidecar CI fixes into sidecar-poc1 and sidecar, push, run CI once

## Goal
The user's goal: PR CUBRID/cubrid#8504 (Sidecar POC-1) shell failures caused by Sidecar are fixed; get a new CI result.
The user approved (2026-11-13): integrate, push vk/sidecar-poc1, one `/run all`.

## Commits (all on top of 84e24e39f4 = current sidecar-poc1 head)
- branch sidecar-fix-diagdb: e1098a7f40 (diagdb dumps a store with its owner).
- branch sidecar-fix-btree-del: e2e5a98b78, 0149d9e633, a207a0ecd9, 17c355d22c (SA DELETE expanded read, midxkey error,
  midxkey buffer size, store insert undo returns space to bestspace).
- Evidence: /home/vimkim/gh/my-cubrid-docs/.scratch/sidecar/ci-fix/{diagdb,btree-del}/decisions.md and their check scripts
  (check_diagdb.sh, check_index_keys.sh, check_store_rollback.sh).

## Do
1. In worktree /home/vimkim/gh/cb/sidecar-poc1 (branch sidecar-poc1, clean except untracked testdb_loaddb.log, which is never
   committed): fast-forward to sidecar-fix-diagdb, then cherry-pick the four btree-del commits in order (or rebase that branch
   onto it and fast-forward). Linear history, no merge commit.
2. Build debug (debug_gcc, UNIT_TEST_SIDECAR=ON as in .scratch/sidecar/pr-sync/decisions.md) and release (release_gcc, GCC 11.5,
   -Werror) with the cubrid-build skill. Note a preset switch rewrites .env, so run checks on one preset at a time.
3. On the debug install: test_sidecar unit tests, the three check scripts (adapt paths to this worktree; workenv port 41324,
   sidecar_force_external=no in conf, scenarios set yes per session as the scripts do), and the shell cases bug_xdbms4309,
   _01_show_heap_header, cbrd_25122, cbrd_24771 with the cubrid-test-shell-run skill against testcases branch tc/pr-8504
   (worktrees already exist: /home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8504-diagdb and tc-pr-8504-btree-del; read-only).
   Then the P1c run: pr-sync/tools/run_p1c_here.py (see pr-sync/decisions.md), expect all pass.
4. If everything passes: `git push vk sidecar-poc1` (fast-forward only). Then trigger CI once with the cubrid-ci-trigger skill
   (`/run all` on PR 8504) and register monitoring with cubrid-ci-watch (suites shell, sql, medium; sql_by_cci is not accepted).
   If anything fails, stop before push and report.
5. Local branch `sidecar` (not checked out anywhere; /home/vimkim/gh/cb/sidecar is on sidecar-stress and its 24h stress is
   finished): create a temporary worktree /home/vimkim/gh/cb/sidecar-int on branch sidecar, cherry-pick the five commits,
   resolve conflicts (sidecar lacks the develop merge), build debug and run test_sidecar plus the three check scripts.
   Do NOT push `sidecar`. Remove the temporary worktree afterwards without force (keep it if anything failed).
6. Record steps and evidence in /home/vimkim/gh/my-cubrid-docs/.scratch/sidecar/ci-fix/integrate/decisions.md, update
   /home/vimkim/gh/my-cubrid-docs/CBRD-28053/pr-context.md status line; commit and push my-cubrid-docs (force-add under .scratch
   as the other tabs did; leave unrelated dirty files alone).
7. Final reply: new heads (sidecar-poc1, sidecar), checks and results, CI run URL and watch id.

## Rules
- Commit trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never commit HANDOFF.md or testdb_loaddb.log.
- Do not touch the stdb/crdb databases, other sessions' servers, uid 11123/11124 testdb, CTP/HA processes.
- Stop only processes you start. No `pkill -f`. Daemons: stdin /dev/null, output to files.
- rm only literal paths or `${NAME:?}`. Free disk > 8 GB. No personal link host in shared material (PR, JIRA).
- No second /run. Do not edit testcase answer files. Do not post PR comments other than the one `/run all`.
