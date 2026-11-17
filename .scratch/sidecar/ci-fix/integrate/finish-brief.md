# Finish the integration of the five Sidecar CI fixes

## Goal
The user's goal: PR CUBRID/cubrid#8504 (Sidecar POC-1) has its CI fixes integrated on both branches, with checks
recorded and scratch worktrees cleaned. The first integration agent pushed sidecar-poc1 (f69816c086) and triggered CI,
but stopped before finishing the items below. Read brief.md in this directory first, then p1c-run.out and spk-rerun*.out.

## State
- Local branch `sidecar` at 539ab8ae8d in worktree /home/vimkim/gh/cb/sidecar-int (preset debug_gcc). It holds the five
  fixes cherry-picked on 7c5028d5bd. Whether its debug build and checks ran is not confirmed. Never push `sidecar`.
- P1c on sidecar-poc1: 463/466. The 3 failures are sp_keeps_no_store_page. It is a placement-flaky precondition
  (rows on one hot page hit the develop hang, tracker 815). It failed the same way before the five commits, and 2 of
  3 reruns passed (spk-rerun1..3.out).
- CI run 43404071059 on f69816c086: medium pass. shell 25 expected-output failures (not fixed by user decision). The 4
  Sidecar shell cases now pass. test_sql shard 09 LOG FATAL is develop defect CBRD-28058
  (/home/vimkim/gh/my-cubrid-docs/CBRD-28053/ci-43404071059-logfatal.md). sql_by_cci 38 failures are output format
  or plan text only. A local-only cub_cas crash is a develop client ping defect
  (/home/vimkim/gh/my-cubrid-docs/CBRD-28053/cascrash-column-name-serial-03.md).

## Do
1. In /home/vimkim/gh/cb/sidecar-int, build debug with the cubrid-build skill if the build is not at HEAD 539ab8ae8d.
   Run test_sidecar and the three check scripts (check_diagdb.sh, check_index_keys.sh, check_store_rollback.sh in
   ../diagdb and ../btree-del). Adapt only paths and port.
2. If all pass, remove the worktree /home/vimkim/gh/cb/sidecar-int and its install ~/.cub/install/sidecar-int (literal
   paths). Keep branch `sidecar`. `git worktree remove --force` is approved only for a submodule refusal after you
   confirm `git status` is clean and no process uses the path. Keep the worktree if anything fails, and report.
3. Remove worktrees /home/vimkim/gh/cb/sidecar-fix-diagdb and /home/vimkim/gh/cb/sidecar-fix-btree-del the same way,
   after confirming each branch's commits are in sidecar-poc1 (by patch-id or subject). Keep their branches.
   Do not close any herdr tab.
4. Write decisions.md in this directory: the integration steps, heads, checks and results, the CI result summary
   above, the spk flake and these follow-ups: make the spk setup deterministic; other whole-heap walkers (compactdb,
   checkdb, capacities dump) may need the diagdb treatment; store growth because a rolled-back store slot is never
   reused; the testkit verify helper counts skipped cases.
5. Replace the Status line of /home/vimkim/gh/my-cubrid-docs/CBRD-28053/pr-context.md with a dated line for head
   f69816c086 and run 43404071059, and keep the old line as "Previous status".
6. Close work-tracker items #951 and #952 with a note naming the integrated commits.
7. Commit and push my-cubrid-docs (force-add under .scratch; leave unrelated dirty files alone).
8. Final reply in Korean: checks and results, what was removed, the docs commit.

## Rules
- Commit trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never commit HANDOFF.md or testdb_loaddb.log.
- No engine push, no CI, no PR comments, no JIRA writes, no testcase edits.
- Do not touch the stdb/crdb databases, other sessions' servers, uid 11123/11124 testdb, the develop demodb, CTP/HA processes.
- Stop only processes you start. No `pkill -f`. Daemons: stdin /dev/null, output to files. Never launch GUI programs.
- rm only literal paths or `${NAME:?}`. Keep free disk above 8 GB. No personal link host in shared material.
