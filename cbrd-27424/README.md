# CBRD-27424: standalone workspace OOS

Last modified: 2026-10-16 (Asia/Seoul).

[PR #7925](https://github.com/CUBRID/cubrid/pull/7925) supports OOS storage in standalone object loading and CSQL workspace writes.

Start with the [Korean reviewer guide](review-guide-pr7925-28b65d18a-ko.md), covering locally integrated `28b65d18a` and both completed review simplifications. It distinguishes the published PR HEAD `1c660d22e`, the pinned PR7927 dependency, and pending shared integration. Snapshot: 2026-10-07, Asia/Seoul.

The [orchestration record](../.scratch/pr7925-review-simplification/orchestration.md) preserves implementation decisions, earlier exact-revision receipts, independent reviews and the shared partition gate. Historical reports below retain their original revision scope; they do not establish current-head CI readiness.

Read the [accessible Korean explanation](PR7925-PR7927-dependency_b755678cd_ko.md) for why the original fix can stand alone and the current implementation uses PR #7927. The [detailed dependency assessment](PR7925-PR7927-dependency_b755678cd_codex.md) retains source comparisons and historical evidence. Both cover `b755678cd`; snapshot: 2026-10-08.

The latest [full CI report for run 38861566581](ci_analysis_report_b755678cd_run38861566581_codex.md) covers unchanged engine `b755678cd` with both updated TC heads. Medium passes 975/975 and SQL passes 17,471/17,471. Shell records three failures and 30 skips. Actual dependency integration and human TC disposition remain pending. Snapshot: 2026-10-16, Asia/Seoul.

이전 TC 수정 전 결과는 [run 37747856853 분석](ci_analysis_report_b755678cd_run37747856853_codex.md)에 보존한다. Medium 3건·shell 4건을 평가한 과거 기록이다. Snapshot: 2026-10-15, Asia/Seoul.

The [SA inline-row review assessment](review-comment-4257963742_b755678cd_ste.md) explains review comment 4257963742 in plain English. It separates confirmed source behavior, the reviewer's experiments, preservation requirements, and the benefits and costs of accepting the proposed change. Snapshot: 2026-10-16.

## File index

Dates for older unindexed files come from their Git history. Raw logs retain native formatting.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [ci_analysis_report_b755678cd_run38861566581_codex.md](ci_analysis_report_b755678cd_run38861566581_codex.md) | Full run after TC updates, three shell failures, exact-baseline comparison | 2026-10-16 | 2026-10-16 | Record the requested full CI result before the SA review change |
| [review-comment-4257963742_b755678cd_ste.md](review-comment-4257963742_b755678cd_ste.md) | SA inline-row review, source evidence, and tradeoffs | 2026-10-16 | 2026-10-16 | Assess the review before changing the accepted preservation contract |
| [PR7925-PR7927-dependency_b755678cd_ko.md](PR7925-PR7927-dependency_b755678cd_ko.md) | 쉬운 한글 설명: 독립 수정 가능성과 현재 구현의 의존성 | 2026-10-08 | 2026-10-08 | PR7927을 먼저 통합하는 이유와 대안을 리뷰어에게 설명 |
| [PR7925-PR7927-dependency_b755678cd_codex.md](PR7925-PR7927-dependency_b755678cd_codex.md) | Original fix versus current PR7927 implementation dependency | 2026-10-08 | 2026-10-08 | Explain whether PR7927 must merge and the available alternatives |
| [CBRD-27424-sa-loaddb-diagnosis_f4299ac_codex.md](CBRD-27424-sa-loaddb-diagnosis_f4299ac_codex.md) | Historical standalone loader diagnosis at f4299ac | 2026-09-15 | 2026-09-15 | Explain the original missing OOS conversion path |
| [CBRD-27424-sa-workspace-oos_e24b458_codex.md](CBRD-27424-sa-workspace-oos_e24b458_codex.md) | Historical implementation and reproduction at e24b458 | 2026-09-11 | 2026-09-11 | Document standalone workspace OOS implementation |
| [CBRD-27424-workspace-oos-revert-rationale_a142503dc_codex.md](CBRD-27424-workspace-oos-revert-rationale_a142503dc_codex.md) | Historical direct-byte benchmark and restoration rationale | 2026-10-07 | 2026-10-07 | Explain the measured decision to restore attrinfo conversion |
| [README.md](README.md) | Ticket overview and file index | 2026-10-07 | 2026-10-16 | Help readers find the ticket documents and evidence |
| [ci-fix/pr-7925/index.md](ci-fix/pr-7925/index.md) | Historical local CI-repair index | 2026-09-15 | 2026-09-15 | Explain retained repair artifacts |
| [ci_analysis_report_e24b458_codex.md](ci_analysis_report_e24b458_codex.md) | Historical exact-revision CI analysis at e24b458 | 2026-09-15 | 2026-09-15 | Preserve CI evidence for the original implementation |
| [ci_analysis_report_fe1a918_codex.md](ci_analysis_report_fe1a918_codex.md) | Historical exact-revision CI analysis at fe1a918 | 2026-09-15 | 2026-09-15 | Assess CI after the Python dependency change |
| [code_review_1c660d22e_codex.md](code_review_1c660d22e_codex.md) | Published-head correctness and simplification review at 1c660d22e | 2026-10-07 | 2026-10-07 | Separate preserved behavior from optional ownership cleanup |
| [code_review_39d5e5e_fable.md](code_review_39d5e5e_fable.md) | Historical Standards/Spec review at 39d5e5e | 2026-09-18 | 2026-09-18 | Review merged OOS dependency compatibility |
| [code_review_d4a155a_fable.md](code_review_d4a155a_fable.md) | Historical Standards/Spec review at d4a155a | 2026-09-18 | 2026-09-18 | Record implementation review and follow-ups |
| [review-guide-evidence-28b65d18a/source-map.md](review-guide-evidence-28b65d18a/source-map.md) | Local-only immutable commit/path/line source lookups | 2026-10-07 | 2026-10-07 | Support guide claims without inventing unpublished source URLs |
| [review-guide-pr7925-28b65d18a-ko.md](review-guide-pr7925-28b65d18a-ko.md) | Current Korean guide for the locally integrated 28b65d18a tree | 2026-10-07 | 2026-10-07 | Help reviewers follow workspace OOS behavior and both simplifications |

## Integrated analysis and decisions

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [PR7925 b755 / run 37747856853 CI 분석](ci_analysis_report_b755678cd_run37747856853_codex.md) | TC 수정 전 7개 실패, exact-base 비교 한계, ORDER BY·partition TC 적용성·후속 담당 | 2026-10-15 | 2026-10-15 | 실제 OOS 통합을 위한 당시 HEAD 실패 처분과 재검증 범위 확정 |
| [CBRD-27424: restore the attrinfo workspace OOS implementation](CBRD-27424-workspace-oos-restoration_1c660d22e_codex.md) | Restored workspace behavior and matched benchmark results | 2026-10-07 | 2026-10-13 | Record implementation checks and restoration evidence |
| [PR7925 / 28b65d18a CI 수집 중단 보고서](ci_analysis_report_28b65d18a_codex.md) | Pinned CI counts, failures, provenance and attribution limits | 2026-10-08 | 2026-10-13 | Preserve exact-revision verification and its limits |
| [PR #7925 published-head CI evidence warning](ci_analysis_report_91bfde02e_codex.md) | Pinned CI counts, failures, provenance and attribution limits | 2026-10-07 | 2026-10-13 | Preserve exact-revision verification and its limits |
| [PR #7925: attribution of the triggered CI failures](ci_analysis_report_f037616cd_codex.md) | Pinned CI counts, failures, provenance and attribution limits | 2026-10-07 | 2026-10-13 | Preserve exact-revision verification and its limits |
| [Exact-commit failure excerpts](ci_f037616cd/failure_excerpts.md) | Compact decisive excerpts supporting CI attribution | 2026-10-07 | 2026-10-13 | Substantiate the report with bounded original diagnostics |
| [PR #7925 code review guide at `a142503dc`](code_review_guide_a142503dc_codex.md) | Changed symbols, invariants, tests and reviewer navigation | 2026-10-07 | 2026-10-13 | Help reviewers follow the exact implementation revision |
