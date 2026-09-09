# PR7600 — locally committed blocked handoff

Date: 2026-09-09. **Routing implementation handed off; feature acceptance blocked. No push.**

The user explicitly approved finishing the routing review and local commit handoff while leaving CBRD-27237 lifecycle verification and runtime acceptance unresolved. This is not a waiver or a narrower definition of full feature completion.

## Source and scope

- Source worktree: `/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos`.
- PR #7600 head used as review base: `b871ea386d2c5419b7abae07dda58b9b7f36377a`.
- Local implementation commit: **`213ce80f54dc54130fcef22e616cb28f4835f6d5`**, one commit ahead of that base.
- Five-file engine diff SHA-256: `8ccb237954a348b5bef6f1b653dbe44e31816ba5c21d3b856f0d0c33684a215c`.
- [Specification](../../.scratch/pr7600-effective-key-routing/spec.md) SHA-256 unchanged: `dfa82a53337a2cf85c9d18bfe3707d99670a6e7070320a97fc3183b50c01f31f`.

The routing commit replaces the scoped full inline row probe with effective-key routing and a normal owner-aware first-pass transformation. It retains independent final-record routing, representation handling, validation, locks, scan caches, indexes and movement. No CBRD-27237 repair is included. No new engine changes or database experiments were made for this handoff.

## Review and evidence

- [Two-axis review](routing-review-213ce80f5-codex.md): no new routing implementation defects or scope creep; one optional Standards duplication suggestion; three Spec acceptance limitation groups retained.
- [Requirement matrix](ticket07-preliminary-evidence-matrix-213ce80f5-codex.md): all 37 user stories, 15 implementation decisions, 14 testing decisions and 64 checklist ordinals mapped to evidence, exact revision families, gaps and revalidation.
- [Cleanup report](ticket04-cleanup-b871ea386-codex.md): bounded failure and LOB lifetime proofs; 32 post-format SA routing/cleanup tests pass. The combined configured-suite result remains 24/25 after infrastructure-only reruns, not all green.
- [Resource measurements](ticket06-measurements-b871ea386-codex.md), [interleaved timings](ticket06-interleaved-b871ea386-codex.md), [CPU attribution](ticket06-cpu-attribution-b871ea386-codex.md): scoped allocation/copy savings demonstrated; runtime acceptance inconclusive. Measurements identify the pre-format candidate, not the future dependency-integrated revision.
- [Completion path](acceptance-completion-path-213ce80f5-codex.md): wait specifically for CBRD-27237, not an assumed CBRD-27230 fix; includes the user-authorized published JIRA dependency explanation.

This handoff uses previously recorded test results; it does not claim they were rerun during review. Source/document consistency and staged-content checks are not database verification.

## What remains blocked

1. **Ticket 05:** the existing baseline/candidate rollback-vacuum regression fails. A fix specifically for CBRD-27237 is expected by the user but is not present in this worktree. Passing that regression must be followed by committed obsolete-chain reclamation and the complete partitioned SERVER old-reader, movement, rollback, recovery and vacuum evidence.
2. **Ticket 06 runtime acceptance:** unresolved small-inline timing concern. Instruction counts are not elapsed/CPU-time acceptance. Keep final routing; no fallback, broad preparation split or destination reuse is approved.
3. **Ticket 07:** final integrated revision and evidence are absent. The matrix retains additional proof limits for multiply-invalid statements, distinct final heap-write failures and induced early/final disagreement cleanup. Existing ticket 04 completion is a bounded milestone, not exhaustive failure proof.

Tickets remain in their recorded states. No acceptance gate is changed or closed by this handoff.

## Preserved uncommitted source changes

The source worktree is intentionally not clean: changed `cubrid-cci`, the separate rollback regression, `.artifacts/`, prompts and the reproduction script remain untouched and unstaged. They must not be swept into a routing commit or removed to make status appear clean.

The exact uncommitted regression diff is archived as [CBRD-27237 rollback/vacuum regression patch](ticket05-evidence/CBRD-27237-rollback-vacuum-regression-213ce80f5.patch). This makes the required test portable without silently adding unrelated lifecycle work to the routing source commit. Its saved results remain in [ticket 05 evidence](ticket05-evidence/). The patch is test-only, still red on the recorded baseline/candidate, and must be reviewed/rebased against the actual fix; it was not applied to another tree in this handoff.

Evidence caches (`__pycache__`), raw private databases, cores and profiler binaries are not part of the documentation commit. The retained JSON, SQL, diagnostic scripts, reports and relevant design authority are included. Raw fixture/profiler paths in JSON are local evidence locations, not promises of portability; missing runtime files must be regenerated only with authorization.

Artifact validation: 206 saved JSON files parse, the new review/handoff/matrix local links resolve, and the archived regression patch SHA-256 `14819d079d5f67d02ef0d6e063a43ab5464b04b63e26f8af3b58f136b52e22ee` equals the current source diff. Staged whitespace checking reports two intentionally preserved raw-evidence warnings: a historical SQL input's terminal blank line and a unified diff's blank context line. Rewriting either would change the retained input/patch bytes; authored documentation/scripts pass the check with those two evidence files excluded. No engine indentation was changed.

## Resume procedure

1. Identify the exact CBRD-27237 patch and review its actual dependencies and rollback/reclamation semantics. Do not infer its presence from an issue status or combine it automatically with 27230/26950.
2. With integration and verification approval, pin matched repaired baseline/candidate builds and revalidate the regression, required SERVER scenarios and affected failure proofs. Preserve earlier red evidence.
3. Re-establish the runtime gate on controlled matched builds, then perform final integrated review and reconcile the entire matrix. Report any remaining gap explicitly.
4. Publish or push only after a separate user request. This local handoff does not authorize either.
