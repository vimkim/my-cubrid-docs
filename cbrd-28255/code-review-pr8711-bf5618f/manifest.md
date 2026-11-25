# Review manifest — CUBRID/cubrid#8711
- Request: cubrid-code-review of PR #8711 + TC PRs cubrid-testcases#4418, cubrid-testcases-private-ex#5114; publish report + Korean comment; no formal review, no CUBRID push, no CI trigger.
- Comparison: merge-base..head. `git diff 6d8296b15c9694a7fc2c7920e539ec66d3d004aa bf5618f6275c4a1053b648b17b22786dca31bfcc`
  - base (develop) 6d8296b15c9694a7fc2c7920e539ec66d3d004aa; merge-base = base; head bf5618f6275c4a1053b648b17b22786dca31bfcc
  - feature commit 99e467e5d5778b43b0b9bd7c007df628e0f64019 (identical diff to merge-base..head)
  - patch sha256 5933d8a3d6eeaea310469e939c4cd22e12f94c2a0a7fabee8230e19ce6546b6a; 1 path: src/storage/heap_file.c (+57/-31)
  - TC: cubrid-testcases tc/pr-8711 d47276bbf0ee1e15229d05c4ec55f4ee7275aad7; private-ex tc/pr-8711 d4a7bcab09684d34aa9b7017bf6757a0f2c3055c
- Snapshot time: 2026-11-25
- Source checkout: /home/vimkim/gh/cb/CBRD-28255 (clean, at head; cubrid-role=review)
- Policy: /home/vimkim/my-cubrid/CUBRID.md; repo AGENTS.md
- Spec: PR body + CBRD-28255 (JIRA).
- Budget: bounded default mode. No hard cap enforced. Envelope: 3 reviewers (~40 min / bounded scope each) + coordinator reservation for build, local TC replay, adjudication, publication.
- Agents (pstack interrogate reviewers: opus, sonnet):
  - R1 systems+storage (opus): bound soundness Q1, type encodings — reviewers/r1.md
  - R2 systems+callers+concurrency/recovery/HA applicability (sonnet): Q1 independent seat, caller buffer contracts, or_init semantics — reviewers/r2.md
  - R3 TC reviewer (sonnet): TC PR content/determinism/coverage — reviewers/r3.md
- Coordinator owns builds and runtime checks (debug build in the review worktree).

## Actual run (recorded after completion)
- R1 opus ~8.5 min, 65 tool calls, coverage partial (source-only by brief; coordinator executed its probes 1–4).
- R2 sonnet ~11 min, 85 tool calls, coverage complete at source level.
- R3 sonnet ~12 min, 65 tool calls, TC review complete (no TC execution by brief).
- Retries: 0. Hard cap: none enforced.
- Coordinator: debug_gcc build of head at worktree-private install; SA probes P1–P8 in disposable DB `rv8711`; CI log inspection of run 45519549478 (attempts 1–2); approval-gate check on #8711/#4418/#5114 (all BLOCKED: vimkim pending).
