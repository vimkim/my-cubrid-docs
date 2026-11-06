# Review manifest: CUBRID PR 8434

- Repository: github.com/CUBRID/cubrid, local worktree /home/vimkim/gh/cb/CBRD-27781-postpone-commit
- Request: team-lead asked for a cubrid-code-review run on PR 8434. The review is read-only and nothing is published.
- Comparison: PR merge base to head
  - base (origin/feature/oos-merge): d52b1889e907abcf84190ec504dde3bc93de260d
  - merge base: d52b1889e907abcf84190ec504dde3bc93de260d
  - head: 3e8072f5681854a0b345c33adf5096b226fa2ce3 (2 commits: 62d0b35b6, 3e8072f56)
  - command: `git diff d52b1889e907abcf84190ec504dde3bc93de260d 3e8072f5681854a0b345c33adf5096b226fa2ce3`
  - patch: evidence/pr.patch, sha256 ed2ce918c8bb528b882b6a696ade68cbdb7bf0a81eae0eb1003dac2cfcb8a08a (5173 lines)
  - files: evidence/files.txt (36 paths: 35 modified, 1 added). No renames, binaries, or submodules.
  - snapshot time: 2026-11-06. `gh-pr-info` reported headRefOid 3e8072f5 (state OPEN) at the end of the review.
- Specification: /home/vimkim/gh/cubrid-oos-context/docs/adr/0008-reclaim-oos-chains-after-the-delete-is-final.md (accepted 2026-11-05)
- PR body: /home/vimkim/gh/my-cubrid-docs/cbrd-27781/pr-body.md
- Policies: /home/vimkim/my-cubrid/CUBRID.md, AGENTS.override.md. AGENTS.user.md is not present.
- Budget mode: strict (the skill default). This harness cannot hard-enforce the per-agent ceilings of 5% of weekly or 10% of daily allowance. A budget question went to team-lead and received no answer during the run. For that reason, no specialist reviewer agents were launched. The coordinator did the whole review alone.
- Planned agents: none launched. The coverage table records the roles as coordinator-covered.
- Usage: unmeasured. No per-agent telemetry is available.
- Verification resources: none. No build, ctest, or runtime check was run.

## Update: best-effort budget authorized (team-lead relayed the user's choice (a))

- Mode: best effort. Up to 5 specialist reviewers, no hard cap, possible overshoot. Usage targets are prompt-level only and not enforced.
- Agents launched (3). HA is folded into Systems and judged not applicable; Storage is combined with Systems.
  - recovery (opus): recovery interleavings, R1 owner. Sole owner of the build and runtime probe, in its own detached worktree under the scratchpad.
  - concurrency (sonnet): latch/race/vacuum interactions. Independent second seat on R1, source-only.
  - systems-storage (sonnet): C/C++ correctness of oos_file.cpp, heap_oos.cpp, log_append explicit MVCCID, chunk layout, error paths. Source-only.
- Shared challenge: R1 (explicit-MVCCID block oldest lowering vs vacuum ordering), owned by recovery (opus) and concurrency (sonnet).

## Run 2: specialist pass (coordinator review-8434b, 2026-11-06 15:45 KST)

The earlier "Update" section planned three agents. They produced no output (the reviewer directories were empty at 15:45). This run replaces that plan.

- Scope recheck: `gh-pr-info` at 15:45 reported headRefOid 3e8072f5681854a0b345c33adf5096b226fa2ce3, state OPEN, base feature/oos-merge. `origin/feature/oos-merge` = merge base = d52b1889e907abcf84190ec504dde3bc93de260d. `git diff d52b188..3e8072f | sha256sum` = ed2ce918c8bb528b882b6a696ade68cbdb7bf0a81eae0eb1003dac2cfcb8a08a (matches evidence/pr.patch).
- Additional scope: the uncommitted R1 fix in the lead's worktree (HEAD 3e8072f56; 3 files: src/query/vacuum.c, src/transaction/log_append.cpp, unit_tests/oos/test_oos_real_vacuum_server.cpp; no untracked files). Saved as evidence/r1-fix-worktree.patch, sha256 b22b31c5a388dbb2bc67c191476ee8e368eb5b5143bb4c149e8feeeca47a7853.
- Read-only source snapshots (git archive of src/ and unit_tests/oos, write-protected) in the coordinator scratchpad `/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-CBRD-27781-postpone-commit/a6146255-f5a6-40d9-9547-8addb0027078/scratchpad/`: `head-3e8072f/`, `base-d52b188/`, `head-plus-r1fix/` (head + the fix patch; byte-identical to the worktree files).
- Constraints from team-lead: read-only. No engine edits, no builds, no ctest, no servers, no commits, pushes, PR comments, CI, or publication to my-cubrid-docs main. Evidence is therefore source-only (level 2-3); execution checks are written as proposals.
- Budget mode: best effort, authorized by the user through team-lead ("up to 5 specialist reviewer agents, no hard cap"). Per-agent target: one bounded assignment, about 45 min wall time, no nested agents, no retries. Total envelope: 5 specialists + coordinator adjudication. Usage is not measured; no hard enforcement exists; overshoot is possible.
- Models: pstack `interrogate reviewers: opus, sonnet` (~/.claude/rules/pstack-models.md).

| Agent | Model | Assignment | Output |
|---|---|---|---|
| r1fix | opus | Review the uncommitted R1 fix; independently test the dropped-file safety claim; find other code that assumes an MVCC record's MVCCID >= its block's oldest_visible_mvccid. Shared Q1, Q2. | reviewers/r1fix/report.md |
| recovery | opus | log_do_postpone LSA_LE, postpone rerun, crash interleavings, restart-time notify append, RVOOS_* recovery handlers, fail-stop. Shared Q2. | reviewers/recovery/report.md |
| concurrency | sonnet | Latch order, vacuum worker/reclaimer races, snapshot safety of A', class-lock lifetime vs drop. Shared Q1. | reviewers/concurrency/report.md |
| systems-storage | sonnet | oos_file.cpp chunk layout/reclaimer/insert, slotted page and page-buffer use, heap_oos.cpp, vacuum_oos.cpp, C/C++ ownership, exceptions, payload packing. | reviewers/systems-storage/report.md |
| ha | sonnet | log_applier.c, RVREPL_*, CDC/flashback/log dump consumers of the changed records and rcvindex renumbering. | reviewers/ha/report.md |

Shared questions:
- Q1 (r1fix opus, concurrency sonnet): without the header lowering, is dropped-file cleanup still safe for a pending RVOOS_NOTIFY_VACUUM?
- Q2 (r1fix opus, recovery opus; reduced model diversity): what happens to the vacuum block state when restart recovery reruns RVOOS_UPDATE_DROP_POSTPONE and appends RVOOS_NOTIFY_VACUUM?
