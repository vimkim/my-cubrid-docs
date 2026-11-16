# Classify the test_sql LOG FATAL of PR 8504 run 43404071059

## Goal
The user's goal: know whether the new test_sql failure on PR CUBRID/cubrid#8504 (Sidecar POC-1) is a Sidecar defect,
a defect in the branch's local develop fixes, a pre-existing develop defect, or CI flakiness. If it is a code defect,
find its root cause. The user approved local reproduction on 2026-11-16. Sidecar P4 (HA) waits on this.

## What CI showed (read first)
- Report: /home/vimkim/gh/my-cubrid-docs/CBRD-28053/ci-43404071059-analysis.md, section 2.
- Evidence: /home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8504/f69816c0867895a0273e790eeb30dc8eef41d3f8
- test_sql shard 09 (534 cases) passed cases 1..398. Case 399 `sql/_36_guava/cbrd_27381/cases/cbrd_27381_03_datetime_types.sql`
  died with `LOG FATAL ERROR: log_fetch_from_archive`. The server wanted archive `basic_lgar000`, which did not exist.
  Restart recovery hit the same FATAL, so every later case failed and the shard hit the 2 h timeout.
- The server error log (basic_20261113_1916.err) is not in the evidence. Check the GitHub run's artifacts once
  (`gh run view 43404071059 --repo CUBRID/cubrid`, artifact list) before reproducing; report if it is absent.
- The previous run 43184757385 (head 84e24e39f4) passed the same case on shard 09 in 0.77 s. TC revision differed
  (previous 37de34d9e3, now 40cdeddd1d on tc/pr-8504).
- The case builds indexes on 8 DATE/TIME columns with `index_build_buffer_size=64K` and `index_sort_method=radix`.
  Values are far below sidecar_min_value_size (256). CI commit d3403c0533 sets sidecar_force_external=yes by default.

## Heads
- f69816c086: current sidecar-poc1 (failing run). Worktree /home/vimkim/gh/cb/sidecar-poc1, build dirs exist
  (build_preset_debug_gcc, build_preset_release_gcc). Untracked testdb_loaddb.log is never committed.
- 84e24e39f4: previous head (passing run). Five commits differ (diagdb, SA DELETE, midxkey x2, store insert undo).
- The branch also carries local develop fixes d514d5ea18 (commit waits for its commit record on disk) and
  7c5028d5bd (committed-snapshot walk). Both were in the passing run too, but they touch the log, so keep them as suspects.
- Develop merge base 173d92e454 is the baseline without Sidecar.

## Do
1. Get the exact shard 09 case order from the CI log in the evidence (or the run log). Write it to this directory.
2. On a debug build of f69816c086, run case 399 alone, then the cases before it that share the `basic` DB
   (at least the cbrd_27379 and cbrd_27381_01/02 cases, then a wider prefix of shard 09 if needed), with the
   cubrid-test-sql-run skill. Use the CI settings: sidecar_force_external=yes, and the CI's log/archive parameters
   (find them in the CI workflow or testtools config; note `log_max_archives` and archive removal). Repeat enough times
   to give a rate.
3. Whatever reproduces, keep the server error log and a core or stack of the `log_fetch_from_archive` caller.
   Name which code asked for the old LSA and why the LSA was older than the active log.
4. A/B: build 84e24e39f4 (and 173d92e454 if the cause is not Sidecar) in new detached worktrees, for example
   /home/vimkim/gh/cb/sidecar-logfatal-84e2 and /home/vimkim/gh/cb/sidecar-logfatal-base, and rerun what reproduced.
   Build only what the evidence needs. Remove worktrees you created at the end without force.
5. If nothing reproduces locally after a fair effort, say so with the rate and stop. Do not guess a cause.
6. A fix is allowed only as a local commit on a new branch from f69816c086 with a test that fails before it.
   Do not push any engine branch. Do not trigger CI.
7. Record steps, evidence labels (측정/추론/추측) and rates in decisions.md in this directory, and a Korean report at
   /home/vimkim/gh/my-cubrid-docs/CBRD-28053/ci-43404071059-logfatal.md. Commit and push my-cubrid-docs
   (force-add under .scratch; leave unrelated dirty files alone).
8. Final reply in Korean: classification, cause with evidence, repro rate per head, any local fix branch, report path.

## Rules
- Commit trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never commit HANDOFF.md or testdb_loaddb.log.
- Do not touch the stdb/crdb databases, other sessions' servers, uid 11123/11124 testdb, the develop demodb, CTP/HA processes.
- Stop only processes you start. No `pkill -f`. Daemons: stdin /dev/null, output to files. Never launch GUI programs.
- rm only literal paths or `${NAME:?}`. Keep free disk above 8 GB. No personal link host in shared material.
- No PR comments, no JIRA writes, no testcase answer edits.
