# Sidecar CI fix: DELETE cannot find its index key (cbrd_25122), plus spacedb growth (cbrd_24771)

## Goal
The user's goal: PR #8504 shell failures caused by Sidecar must be fixed before P4. This tab owns the btree DELETE case
and, second, the low-confidence space case.

## Cases
1. shard 03 `shell/_06_issues/_24_2h/cbrd_25122/cases/cbrd_25122.sh`: csql DELETE core, `assert_release (false)` "Key/oid
   should be found" at btree.c:36823 (btree_key_delete_remove_object <- btree_delete_internal <- btree_physical_delete <-
   locator_add_or_remove_index_internal <- locator_delete_force). Table `t_c (c_a char(255), ...)`, index on
   (c_a, c_b, c_c, c_d), `delete from t_c where c_a='a' and c_b=2 and c_c is not null`. Passed 194 times on develop.
   Guess: the key for the delete is built from an externalized value read wrongly (store ref, not the value).
2. After case 1: shard 11 `shell/_06_issues/_23_1h/cbrd_24771/cases/cbrd_24771.sh` case 22: spacedb 82.0M -> 83.0M after
   repeated unique-violation rollbacks (Num_pages checks all OK). Decide whether the store file grows (Sidecar defect:
   rolled-back store rows not reused) or it is a fixed one-time allocation/rounding. Fix only if it is a defect.
   Commit each fix separately.

## Context
- Sidecar POC (epic Csidecar-fix-btree-delD-28053, POC-1) stores large column values in a per-heap MVCC store file. Design docs:
  /home/vimkim/gh/my-cubrid-docs/sidecar/. Code: src/storage/sidecar.cpp plus hooks in heap_file.c, locator_sm.c.
- PR CUsidecar-fix-btree-delID/cubrid#8504 (head vk/sidecar-poc1 84e24e39f4 = Sidecar + develop 173d92e454 + CI-only commit d3403c0533 that
  sets hidden parameter sidecar_force_external default true). gha-ci run 43184757385 failed these shell cases.
- CI analysis: /home/vimkim/gh/my-cubrid-docs/Csidecar-fix-btree-delD-28053/ci-43184757385-analysis.md (read your rows first).
- Testcases come from branch tc/pr-8504 of the testcase repos. Run them locally with the cubrid-test-shell-run skill.

## Where
- Your worktree: /home/vimkim/gh/cb/sidecar-fix-btree-del (branch sidecar-fix-btree-del, at 84e24e39f4). Build there with the cubrid-build skill (debug_gcc).
  Use your own install, `cub-workenv init` with a free port, and your own db.
- Notes: write decisions and evidence to /home/vimkim/gh/my-cubrid-docs/.scratch/sidecar/ci-fix/btree-del/decisions.md (create it). Commit and push my-cubrid-docs without asking.

## Do
1. Reproduce on a debug build with sidecar_force_external=yes. Then run with =no. If it does not reproduce, stop and report.
2. Find the root cause (first place the system goes wrong). Fix it in the Sidecar code, not the testcase.
   If the cause is a develop defect that Sidecar only exposes, stop and report before fixing.
3. Add or extend a focused check (unit test in test_sidecar or a P1c scenario under
   /home/vimkim/gh/my-cubrid-docs/.scratch/sidecar/) that fails before the fix and passes after.
4. Rerun the failing testcases plus the P1c unit_tests. Commit on sidecar-fix-btree-del (local commits authorized, message
   "[Sidecar] ...", trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`). Do NOT push any engine branch,
   do NOT rerun CI, do NOT change testcase answer files.
5. Final reply: cause, fix commit, checks with results, what is not covered.

## Rules
- Do not touch /home/vimkim/gh/cb/sidecar (24h stress running, db stdb, install), /home/vimkim/gh/cb/sidecar-poc1,
  the other fix worktree, .scratch/sidecar/p3-stress/full, other sessions servers, uid 11123/11124 testdb, CTP/HA.
- Stop only processes you start. No `pkill -f`. Daemons: stdin /dev/null, output to files.
- rm only literal paths or `${NAME:?}`. Free disk > 8 GB. No personal link host in shared material.
- C++ in legacy .c/.h needs INDENT-OFF/ON. Reply to the user in Korean, short declarative sentences, labels 측정/추론/추측.
