# CBRD-27424: standalone workspace OOS

[PR #7925](https://github.com/CUBRID/cubrid/pull/7925) supports OOS storage in standalone object loading and CSQL workspace writes.

Start with the [Korean reviewer guide](review-guide-pr7925-28b65d18a-ko.md), covering locally integrated `28b65d18a` and both completed review simplifications. It distinguishes the published PR HEAD `1c660d22e`, the pinned PR7927 dependency, and pending shared integration. Snapshot: 2026-10-07, Asia/Seoul.

The [orchestration record](../.scratch/pr7925-review-simplification/orchestration.md) preserves implementation decisions, earlier exact-revision receipts, independent reviews and the shared partition gate. Historical reports below retain their original revision scope; they do not establish current-head CI readiness.

The [PR #7927 dependency assessment](PR7925-PR7927-dependency_b755678cd_codex.md) distinguishes the independent original workspace fix from the current shared preparation/finalization implementation at `b755678cd`. Snapshot: 2026-10-08.

## File index

Dates for older unindexed files come from their Git history. Raw logs retain native formatting.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [PR7925-PR7927-dependency_b755678cd_codex.md](PR7925-PR7927-dependency_b755678cd_codex.md) | Original fix versus current PR7927 implementation dependency | 2026-10-08 | 2026-10-08 | Explain whether PR7927 must merge and the available alternatives |
| [CBRD-27424-sa-loaddb-diagnosis_f4299ac_codex.md](CBRD-27424-sa-loaddb-diagnosis_f4299ac_codex.md) | Historical standalone loader diagnosis at f4299ac | 2026-09-15 | 2026-09-15 | Explain the original missing OOS conversion path |
| [CBRD-27424-sa-workspace-oos_e24b458_codex.md](CBRD-27424-sa-workspace-oos_e24b458_codex.md) | Historical implementation and reproduction at e24b458 | 2026-09-11 | 2026-09-11 | Document standalone workspace OOS implementation |
| [CBRD-27424-workspace-oos-revert-rationale_a142503dc_codex.md](CBRD-27424-workspace-oos-revert-rationale_a142503dc_codex.md) | Historical direct-byte benchmark and restoration rationale | 2026-10-07 | 2026-10-07 | Explain the measured decision to restore attrinfo conversion |
| [README.md](README.md) | Ticket overview and file index | 2026-10-07 | 2026-10-08 | Help readers find the ticket documents and evidence |
| [ci-fix/pr-7925/index.md](ci-fix/pr-7925/index.md) | Historical local CI-repair index | 2026-09-15 | 2026-09-15 | Explain retained repair artifacts |
| [ci_analysis_report_e24b458_codex.md](ci_analysis_report_e24b458_codex.md) | Historical exact-revision CI analysis at e24b458 | 2026-09-15 | 2026-09-15 | Preserve CI evidence for the original implementation |
| [ci_analysis_report_fe1a918_codex.md](ci_analysis_report_fe1a918_codex.md) | Historical exact-revision CI analysis at fe1a918 | 2026-09-15 | 2026-09-15 | Assess CI after the Python dependency change |
| [code_review_1c660d22e_codex.md](code_review_1c660d22e_codex.md) | Published-head correctness and simplification review at 1c660d22e | 2026-10-07 | 2026-10-07 | Separate preserved behavior from optional ownership cleanup |
| [code_review_39d5e5e_fable.md](code_review_39d5e5e_fable.md) | Historical Standards/Spec review at 39d5e5e | 2026-09-18 | 2026-09-18 | Review merged OOS dependency compatibility |
| [code_review_d4a155a_fable.md](code_review_d4a155a_fable.md) | Historical Standards/Spec review at d4a155a | 2026-09-18 | 2026-09-18 | Record implementation review and follow-ups |
| [review-guide-evidence-28b65d18a/source-map.md](review-guide-evidence-28b65d18a/source-map.md) | Local-only immutable commit/path/line source lookups | 2026-10-07 | 2026-10-07 | Support guide claims without inventing unpublished source URLs |
| [review-guide-pr7925-28b65d18a-ko.md](review-guide-pr7925-28b65d18a-ko.md) | Current Korean guide for the locally integrated 28b65d18a tree | 2026-10-07 | 2026-10-07 | Help reviewers follow workspace OOS behavior and both simplifications |
