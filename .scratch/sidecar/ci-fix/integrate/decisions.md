# Decisions: integrate the five Sidecar CI fixes (PR 8504)

Goal: PR CUBRID/cubrid#8504 (Sidecar POC-1) has its CI fixes integrated on both branches, with checks recorded and
scratch worktrees cleaned. Briefs: `brief.md` (integration, 2026-11-13) and `finish-brief.md` (finish, 2026-11-17).

Labels: measured (a command output kept here or in the named file), inferred (from file times or a gate in the brief).

## The five commits

| Fix branch commit | sidecar-poc1 | sidecar | Subject |
| --- | --- | --- | --- |
| e1098a7f40 | e1098a7f40 (fast-forward) | 9351022722 | diagdb dumps a heap's store with its owner, not as a class heap |
| e2e5a98b78 | 46da45a37f | dbf6d36b20 | an SA_MODE DELETE reads its old record expanded (cbrd_25122) |
| 0149d9e633 | 6042e9a0ac | c7c2f0312a | a multi-column key fails when a value read fails, not takes NULL |
| a207a0ecd9 | 176cfd07cd | 62dd08a657 | size a multi-column key buffer for the values of a record with refs |
| 17c355d22c | f69816c086 | 539ab8ae8d | the undo of a store insert gives the page's space to the store's bestspace (cbrd_24771) |

- Measured: `git cherry sidecar-poc1 sidecar-fix-btree-del 84e24e39f4` marks all four btree-del commits `-` (same
  patch-id in sidecar-poc1). e1098a7f40 is an ancestor of sidecar-poc1. `git cherry sidecar sidecar-poc1 84e24e39f4`
  marks all five `-`, so `sidecar` carries the same patches.

## Heads

- sidecar-poc1: f69816c086 = 84e24e39f4 + the five fixes, linear. Pushed to vk/sidecar-poc1 (measured:
  `vk/sidecar-poc1` = f69816c086).
- sidecar: 539ab8ae8d = 7c5028d5bd + the five fixes, cherry-picked in worktree /home/vimkim/gh/cb/sidecar-int. Local
  only, never pushed.

## Step 1 to 4: sidecar-poc1 (first integration agent, 2026-11-13)

That agent left no decisions file. The record below comes from its outputs in this directory and in `~/tk`.

- Debug build (debug_gcc, UNIT_TEST_SIDECAR=ON): `build_preset_debug_gcc/bin/cub_server` 14:38, after the head commit
  at 14:33 (inferred from file times). Release build (release_gcc): `build_preset_release_gcc/bin/cub_server` 16:36,
  and `.env` now selects release_gcc (inferred from file times; the -Werror result itself was not kept).
- Native testkit shell, tc/pr-8504 btree-del worktree, install sidecar-poc1/debug_gcc (measured, `~/tk/int1..int4/run.log`):
  bug_xdbms4309 `[OK]`, _01_show_heap_header `[OK]`, cbrd_25122 `[OK]`, cbrd_24771 `[OK]`. Each `verify.txt` says
  `FAIL: total case count is 22, expected 1`. The helper counts the 21 skipped cases of the selection, so this line is
  not the case verdict (see follow-ups).
- P1c (`p1c-run.out`, measured): 463 passed, 3 failed. The three failures are all `sp_keeps_no_store_page`.
- Push and CI: `git push vk sidecar-poc1` (f69816c086), one `/run all`, gha-ci run 43404071059.

### The sp_keeps_no_store_page flake

The case first checks that rows 1 and 2 are on different hot pages. If they share a page, develop's own same-page
hang (tracker 815) decides the test, so the case is not about Sidecar then. In the P1c run they landed on one page
(`['1\t705', '2\t705']`) and the next two checks failed with it. Reruns (measured): `spk-rerun1.out` and
`spk-rerun2.out` 5/5 pass (pages 705 and 710, 705 and 709); `spk-rerun3.out` fails the same way (705 and 705). The same
failure was seen before the five commits (finish brief). Verdict: a placement-flaky precondition, not a regression
of the five fixes.

## CI result: run 43404071059 on f69816c086

https://github.com/CUBRID/cubrid/actions/runs/43404071059, completed 2026-11-13T12:16:49Z, conclusion failure
(measured with `gh run view`). Per suite (from the finish brief and the linked analyses):

- medium: pass.
- shell: 25 expected-output failures, not fixed by user decision. The 4 Sidecar shell cases (bug_xdbms4309,
  _01_show_heap_header, cbrd_25122, cbrd_24771) now pass.
- test_sql shard 09: LOG FATAL, develop defect CBRD-28058 (`CBRD-28053/ci-43404071059-logfatal.md`).
- sql_by_cci: 38 failures, output format or plan text only (not an accepted suite for this PR).
- A local-only cub_cas crash seen while reproducing shard 09 is a develop client ping defect
  (`CBRD-28053/cascrash-column-name-serial-03.md`).

## Step 5: sidecar checks in /home/vimkim/gh/cb/sidecar-int (2026-11-17)

- Build: `direnv exec . just build-and-install` (debug_gcc, UNIT_TEST_SIDECAR=ON in the cache) recompiled nothing, so
  the existing build and install were already at 539ab8ae8d (measured).
- Work environment: `cub-workenv init --no-db`, port 41386, `sidecar_force_external=no` in `[common]` as in sidecar-poc1.
  The scripts set CUBRID_SIDECAR_FORCE_EXTERNAL per session. Only paths and port differ from the original runs.
- test_sidecar: All tests passed (2686 assertions in 16 test cases) (measured).
- check_diagdb.sh: 8/8 PASS (measured).
- check_index_keys.sh: 12/12 PASS, force_external yes and no, csql -S and -C (measured).
- check_store_rollback.sh: 6/6 PASS. csql -C store pages 14 in rounds 1 to 10; csql -S 10 in rounds 1 to 5, then 14
  (one 4-page extension), within the script's bound (measured).
- Output: `sidecar-int-checks.txt` in this directory.

## Step 6: cleanup

- `git worktree remove` without force refused all three worktrees with "working trees containing submodules cannot
  be moved or removed". `git status --porcelain` was empty in each.
- The brief allowed `--force` only when no process uses the path. Shells and idle Claude sessions (the herdr tabs of
  the fix work, and this session in sidecar-int) had their cwd there, so the user was asked and chose to force-remove
  all three without closing any tab.
- Removed: worktrees /home/vimkim/gh/cb/sidecar-fix-diagdb and /home/vimkim/gh/cb/sidecar-fix-btree-del with their
  installs under ~/.cub/install, then /home/vimkim/gh/cb/sidecar-int and ~/.cub/install/sidecar-int last, after this
  file was committed. Branches sidecar, sidecar-fix-diagdb (e1098a7f40) and sidecar-fix-btree-del (17c355d22c) are kept.
- No CUBRID server or master of these installs was running (checked with `ps`). The check scripts stopped their own
  servers.
- work-tracker #951 and #952 closed as done with notes that name the integrated commits.

## Follow-ups

- Make the sp_keeps_no_store_page setup deterministic, so rows 1 and 2 always land on different hot pages instead of
  depending on placement.
- Other whole-heap walkers (compactdb, checkdb, the capacities dump) may meet a store as a FILE_HEAP of the owner's
  class and may need the diagdb treatment.
- Store growth: a rolled-back store slot is never reused (a store slot is used once), so each rolled-back value keeps
  its 4-byte slot even though the page space now returns to bestspace.
- The testkit verify helper counts skipped cases (`total case count is 22, expected 1` on a single-case run).
