# Common brief: specialist review of CUBRID PR 8434

## Goal

Find real defects in CUBRID PR https://github.com/CUBRID/cubrid/pull/8434 (CBRD-27781). The PR implements ADR-0008: an OOS chunk delete is never undone. The unit that decides a chain is dead logs a reclaim intent as a postpone. The OOS reclaimer deletes the chunks with redo-only records after that unit commits. An MVCC UPDATE logs a drop postpone; after commit, the postpone appends `RVOOS_NOTIFY_VACUUM` under the UPDATE's MVCCID (given explicitly, because `logtb_complete_mvcc` cleared it), and vacuum reclaims the chains when no snapshot is older than that MVCCID. The forward-walk and the LSA reclaim gate are removed. A separate commit changes `log_do_postpone` from `LSA_LT` to `LSA_LE`.

## Pinned scope

- Repository: github.com/CUBRID/cubrid. Local git: `/home/vimkim/gh/cb/CBRD-27781-postpone-commit`.
- Base = merge base: `d52b1889e907abcf84190ec504dde3bc93de260d` (origin/feature/oos-merge).
- Head: `3e8072f5681854a0b345c33adf5096b226fa2ce3` (commits 62d0b35b6, 3e8072f56).
- Patch: `/home/vimkim/gh/my-cubrid-docs/cbrd-27781/code-review-pr8434-3e8072f/evidence/pr.patch` (sha256 ed2ce918c8bb528b882b6a696ade68cbdb7bf0a81eae0eb1003dac2cfcb8a08a). File list: `evidence/files.txt` in the same directory.
- Uncommitted R1 fix (lead's worktree, on top of head): `evidence/r1-fix-worktree.patch` (sha256 b22b31c5a388dbb2bc67c191476ee8e368eb5b5143bb4c149e8feeeca47a7853).
- Read-only source snapshots (src/ and unit_tests/oos only). Use these for grep and reading:
  - head: `/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-CBRD-27781-postpone-commit/a6146255-f5a6-40d9-9547-8addb0027078/scratchpad/head-3e8072f/`
  - base: `/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-CBRD-27781-postpone-commit/a6146255-f5a6-40d9-9547-8addb0027078/scratchpad/base-d52b188/`
  - head + R1 fix: `/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-CBRD-27781-postpone-commit/a6146255-f5a6-40d9-9547-8addb0027078/scratchpad/head-plus-r1fix/`
  - Other paths: `git -C /home/vimkim/gh/cb/CBRD-27781-postpone-commit show <sha>:<path>`. `origin/develop` is available for comparison with the pre-OOS engine.
- Do not read the lead's worktree files directly to establish head behavior: the worktree is dirty with the R1 fix.
- Cite line numbers from the head snapshot. For lines that differ in the fix, say "head+fix" and cite that snapshot.

## Context

- Specification: `/home/vimkim/gh/cubrid-oos-context/docs/adr/0008-reclaim-oos-chains-after-the-delete-is-final.md`. Wider OOS context: `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md` (read only the sections you need).
- PR body (Korean): `/home/vimkim/gh/my-cubrid-docs/cbrd-27781/pr-body.md`.
- Earlier coordinator-only report (source-only, no execution): `/home/vimkim/gh/my-cubrid-docs/cbrd-27781/code-review-pr8434-3e8072f/report.md`. Read your assigned code first. Read that report only after you form your own view, and do not treat its conclusions as established.
- Reviewer method: read `/home/vimkim/.claude/skills/cubrid-code-review/references/reviewers.md` (shared method, your role section, and the candidate finding record). Follow it.
- Most CUBRID `.c` files compile as C++. The server build is SERVER_MODE; SA_MODE (standalone) also exists. Debug builds keep `assert`; release builds keep `assert_release`.

## Already known (do not report as new)

- cppcheck false positive on fprintf argument counts at src/storage/oos_file.cpp:4012/4016.
- CBRD-27858 (heap forward slot reuse under vacuum sysop undo).
- CBRD-27925 (READ-latch hint loss).
- The pre-existing debug assert on `tran_start_postpone_lsa` in `log_rv_analysis_sysop_end`.
- R1 itself (the head's header-oldest lowering in `prior_update_header_mvcc_info`) is known. The r1fix reviewer owns the fix review. Others report R1-related issues only if they find a different root cause.

## Hard constraints

- Read-only. Do not edit any engine or test source. Do not build, run ctest, start servers, or create databases. Do not commit, push, post PR comments, trigger CI, or publish anything.
- Do not spawn agents. Do not use the Agent tool.
- Write only inside your own output directory: `/home/vimkim/gh/my-cubrid-docs/cbrd-27781/code-review-pr8434-3e8072f/reviewers/<your-name>/`. You may save a probe source file there (for example a proposed gtest), but do not run it.
- Execution is not available in this pass. Your strongest evidence is level 3 (a complete path argument). For each candidate, give the cheapest decisive check that the coordinator or the lead can run later (for example, a gtest in unit_tests/oos and the assertion that would fire).

## Budget

Best effort, no hard cap. Target: about 45 minutes of wall time and a bounded reading scope. If you reach the target with work left, stop, write what you have, and mark coverage `partial` with the remaining questions.

## Output

Write `report.md` in your output directory with these sections:

1. Pinned identity (base, head, and fix patch hash if you used it).
2. Assigned paths and paths actually inspected.
3. Invariants checked, each with its safety fact, source locations, evidence level, and status (cleared, unproven, violated).
4. Candidate findings, each with the candidate record fields from reviewers.md: ID, proposed priority (P0-P3), failure statement, file:line, preconditions, actors and schedule (or durable state before and after a crash), violated invariant, source argument, attribution to this PR (introduced, exposed, or pre-existing; compare the base snapshot and, when useful, origin/develop), impact, fix direction, evidence level, disproof attempts, and the cheapest decisive check.
5. Rejected hypotheses and cleared risks, with the evidence.
6. Shared-question answer (if you have one), written before you read anyone else's view.
7. Unresolved questions.
8. Coverage status: `complete`, `partial`, or `blocked`, with the reason. Budget status.

Your final message must be a short summary: the top candidates with file:line and priority, your shared-question answer, and the report path. The coordinator reads the report file for detail.
