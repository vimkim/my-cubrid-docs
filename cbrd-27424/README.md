# CBRD-27424: standalone workspace OOS

[PR #7925](https://github.com/CUBRID/cubrid/pull/7925) supports OOS storage in standalone object loading and CSQL workspace writes.

Start with the [Korean reviewer guide](review-guide-pr7925-28b65d18a-ko.md), covering locally integrated `28b65d18a` and both completed review simplifications. It distinguishes the published PR HEAD `1c660d22e`, the pinned PR7927 dependency, and pending shared integration. Snapshot: 2026-10-07, Asia/Seoul.

The [orchestration record](../.scratch/pr7925-review-simplification/orchestration.md) preserves implementation decisions, earlier exact-revision receipts, independent reviews and the shared partition gate. Historical reports below retain their original revision scope; they do not establish current-head CI readiness.

## File index

Dates for older unindexed files come from their Git history. Raw logs retain native formatting.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [CBRD-27424-sa-loaddb-diagnosis_f4299ac_codex.md](CBRD-27424-sa-loaddb-diagnosis_f4299ac_codex.md) | Historical standalone loader diagnosis at f4299ac | 2026-09-15 | 2026-09-15 | Explain the original missing OOS conversion path |
| [CBRD-27424-sa-workspace-oos_e24b458_codex.md](CBRD-27424-sa-workspace-oos_e24b458_codex.md) | Historical implementation and reproduction at e24b458 | 2026-09-11 | 2026-09-11 | Document standalone workspace OOS implementation |
| [CBRD-27424-workspace-oos-revert-rationale_a142503dc_codex.md](CBRD-27424-workspace-oos-revert-rationale_a142503dc_codex.md) | Historical direct-byte benchmark and restoration rationale | 2026-10-07 | 2026-10-07 | Explain the measured decision to restore attrinfo conversion |
| [README.md](README.md) | Ticket overview and file index | 2026-10-07 | 2026-10-07 | Help readers find the ticket documents and evidence |
| [ci-fix/pr-7925/index.md](ci-fix/pr-7925/index.md) | Historical local CI-repair index | 2026-09-15 | 2026-09-15 | Explain retained repair artifacts |
| [ci-fix/pr-7925/verified-local.diff](ci-fix/pr-7925/verified-local.diff) | Historical verified local source patch | 2026-09-15 | 2026-09-15 | Preserve the exact reviewed repair |
| [ci_analysis_report_e24b458_codex.md](ci_analysis_report_e24b458_codex.md) | Historical exact-revision CI analysis at e24b458 | 2026-09-15 | 2026-09-15 | Preserve CI evidence for the original implementation |
| [ci_analysis_report_fe1a918_codex.md](ci_analysis_report_fe1a918_codex.md) | Historical exact-revision CI analysis at fe1a918 | 2026-09-15 | 2026-09-15 | Assess CI after the Python dependency change |
| [code_review_1c660d22e_codex.md](code_review_1c660d22e_codex.md) | Published-head correctness and simplification review at 1c660d22e | 2026-10-07 | 2026-10-07 | Separate preserved behavior from optional ownership cleanup |
| [code_review_39d5e5e_fable.md](code_review_39d5e5e_fable.md) | Historical Standards/Spec review at 39d5e5e | 2026-09-18 | 2026-09-18 | Review merged OOS dependency compatibility |
| [code_review_d4a155a_fable.md](code_review_d4a155a_fable.md) | Historical Standards/Spec review at d4a155a | 2026-09-18 | 2026-09-18 | Record implementation review and follow-ups |
| [evidence/workspace-oos-benchmark-2026-10-06/after-large-0-check.txt](evidence/workspace-oos-benchmark-2026-10-06/after-large-0-check.txt) | Historical workspace OOS benchmark artifact | 2026-09-10 | 2026-10-07 | Preserve measurement inputs, observations and verification |
| [evidence/workspace-oos-benchmark-2026-10-06/after.csv](evidence/workspace-oos-benchmark-2026-10-06/after.csv) | Historical workspace OOS benchmark artifact | 2026-10-07 | 2026-10-07 | Preserve measurement inputs, observations and verification |
| [evidence/workspace-oos-benchmark-2026-10-06/before-large-0-check.txt](evidence/workspace-oos-benchmark-2026-10-06/before-large-0-check.txt) | Historical workspace OOS benchmark artifact | 2026-09-10 | 2026-10-07 | Preserve measurement inputs, observations and verification |
| [evidence/workspace-oos-benchmark-2026-10-06/before.csv](evidence/workspace-oos-benchmark-2026-10-06/before.csv) | Historical workspace OOS benchmark artifact | 2026-10-07 | 2026-10-07 | Preserve measurement inputs, observations and verification |
| [evidence/workspace-oos-benchmark-2026-10-06/verification.json](evidence/workspace-oos-benchmark-2026-10-06/verification.json) | Historical workspace OOS benchmark artifact | 2026-10-07 | 2026-10-07 | Preserve measurement inputs, observations and verification |
| [review-guide-evidence-28b65d18a/build_evidence.py](review-guide-evidence-28b65d18a/build_evidence.py) | Reproduce pinned source references, coverage and case audit | 2026-10-07 | 2026-10-07 | Make source and runtime evidence independently inspectable |
| [review-guide-evidence-28b65d18a/cleanup-doctor.log](review-guide-evidence-28b65d18a/cleanup-doctor.log) | Read-only workenv and inaccessible-PID observation | 2026-10-07 | 2026-10-07 | Explain why integration-worktree cleanup is deferred |
| [review-guide-evidence-28b65d18a/context.json](review-guide-evidence-28b65d18a/context.json) | Dated PR, JIRA and all three GitHub comment streams | 2026-10-07 | 2026-10-07 | Distinguish published metadata from local source scope |
| [review-guide-evidence-28b65d18a/coverage.json](review-guide-evidence-28b65d18a/coverage.json) | All 27 changed files mapped to authoritative guide sections | 2026-10-07 | 2026-10-07 | Prevent substantial diff coverage gaps |
| [review-guide-evidence-28b65d18a/ctest-results.json](review-guide-evidence-28b65d18a/ctest-results.json) | Current 38 CTests and 374 GoogleTest case identities | 2026-10-07 | 2026-10-07 | Audit the actual rebased-revision execution |
| [review-guide-evidence-28b65d18a/integration-receipt.json](review-guide-evidence-28b65d18a/integration-receipt.json) | Approved source rebase/FF, tree equality and preserved CCI digest | 2026-10-07 | 2026-10-07 | Record local promotion and unpublished source state |
| [review-guide-evidence-28b65d18a/rebased-build.log](review-guide-evidence-28b65d18a/rebased-build.log) | Raw successful Debug build/install receipt at 28b65d18a | 2026-10-07 | 2026-10-07 | Preserve actual build verification |
| [review-guide-evidence-28b65d18a/rebased-ctest.log](review-guide-evidence-28b65d18a/rebased-ctest.log) | Raw verbose 38/38 CTest execution receipt | 2026-10-07 | 2026-10-07 | Preserve verdicts and actual case execution |
| [review-guide-evidence-28b65d18a/source-map.md](review-guide-evidence-28b65d18a/source-map.md) | Local-only immutable commit/path/line source lookups | 2026-10-07 | 2026-10-07 | Support guide claims without inventing unpublished source URLs |
| [review-guide-evidence-28b65d18a/source-references.json](review-guide-evidence-28b65d18a/source-references.json) | Machine-readable source locations at HEAD and merge-base | 2026-10-07 | 2026-10-07 | Verify exact source lines and snippets |
| [review-guide-evidence-28b65d18a/verification.json](review-guide-evidence-28b65d18a/verification.json) | Final source, document and runtime validation receipt | 2026-10-07 | 2026-10-07 | Record delivered-guide verification and its limits |
| [review-guide-evidence-28b65d18a/verify_guide.py](review-guide-evidence-28b65d18a/verify_guide.py) | Check guide links, source revisions, coverage and index | 2026-10-07 | 2026-10-07 | Make final documentation verification reproducible |
| [review-guide-pr7925-28b65d18a-ko.md](review-guide-pr7925-28b65d18a-ko.md) | Current Korean guide for the locally integrated 28b65d18a tree | 2026-10-07 | 2026-10-07 | Help reviewers follow workspace OOS behavior and both simplifications |
