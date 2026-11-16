# Classify the cub_cas crash on column_name_serial_03.sql seen in local shard 09 runs

## Goal
The user's goal: know whether the cub_cas crash on `sql/_33_elderberry/cbrd_24141/cases/column_name_serial_03.sql`
is a Sidecar defect on PR CUBRID/cubrid#8504 (head f69816c086), a develop defect, or an artifact of the local setup.
If it is a code defect, find its root cause. The user approved this investigation on 2026-11-16.

## What is known
- Found as a side result of the LOG FATAL work. Read
  /home/vimkim/gh/my-cubrid-docs/.scratch/sidecar/ci-fix/logfatal/decisions.md (runs lf3, lf4; lines near 40 and 140)
  and /home/vimkim/gh/my-cubrid-docs/CBRD-28053/ci-43404071059-logfatal.md line 78.
- lf3 (512M log) and lf4 (20M log) both ran shard 09 cases 1..399 on the f69816c086 debug install. Both had case 122
  NOK with a cub_cas crash and an empty core file. lf4 had 3 more NOK cases that nobody examined.
- CI shard 09 (run 43404071059) passed case 122.
- The attempt directories under ~/tk were deleted, so the run logs are gone. Rerun.
- Setup deviation (suspect): the debug install `~/.cub/install/sidecar-poc1/debug_gcc` has no JDBC jar, so the tools copy
  `cubrid-jdbc-11.4.0.0088.jar` from another local install. A driver from another build may not match the broker.
- CI sets sidecar_force_external=yes by default (commit d3403c0533). The debug install's conf may differ; check it.

## Tools
Reuse /home/vimkim/gh/my-cubrid-docs/.scratch/sidecar/ci-fix/logfatal/tools (mkattempt.sh, runattempt.sh) and
shard09-order.tsv. Copy them into this directory if you change them. Attempt dirs go to ~/tk/cc<N>.

## Do
1. Run case 122 alone, then with its shard 09 prefix (cases 1..122), on the f69816c086 debug install. Repeat for a rate.
   Make cores land somewhere you can read (`ulimit -c`, core_pattern, or gdb on the cas) and keep the broker and cas logs.
2. Try a JDBC jar that matches the install (build it from the sidecar-poc1 worktree, or use the matching version from a
   develop install of the same version). If the crash goes away, the classification is "local setup" and you stop there
   after one confirming repeat.
3. If the crash stays, get the cub_cas stack. Run the same on the develop merge base 173d92e454 (new detached worktree
   /home/vimkim/gh/cb/sidecar-cascrash-base) and compare. Also try sidecar_force_external=no on the head.
4. Look at the 3 other lf4 NOK cases only if they share the cause.
5. A fix is allowed only as a local commit on a new branch from f69816c086, with a test that fails before it.
   Do not push any engine branch. Do not trigger CI.
6. Record steps, labels (측정/추론/추측) and rates in decisions.md in this directory and a Korean report at
   /home/vimkim/gh/my-cubrid-docs/CBRD-28053/cascrash-column-name-serial-03.md. Commit and push my-cubrid-docs
   (force-add under .scratch; no large logs, quote only the lines needed; leave unrelated dirty files alone).
7. Clean up at the end: the ~/tk/cc* dirs you made, and any worktree and install you made. Use literal paths.
   If a worktree with submodules refuses removal, `git worktree remove --force` on that worktree is approved after you
   confirm `git status` is clean and no process uses it.
8. Final reply in Korean: classification, cause with evidence, rate per head and setup, report path, what you removed.

## Rules
- Commit trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never commit HANDOFF.md or testdb_loaddb.log.
- Do not reinstall into `~/.cub/install/sidecar-poc1/*`: another session may run a testdb server on it. Work on copies.
- Do not touch the stdb/crdb databases, other sessions' servers, uid 11123/11124 testdb, the develop demodb, CTP/HA processes.
- Stop only processes you start. No `pkill -f`. Daemons: stdin /dev/null, output to files. Never launch GUI programs.
- rm only literal paths or `${NAME:?}`. Keep free disk above 8 GB. No personal link host in shared material.
- No PR comments, no JIRA writes, no testcase answer edits.
