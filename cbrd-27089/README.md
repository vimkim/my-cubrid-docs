# CBRD-27089: destination-owned OOS writes

[PR #7927](https://github.com/CUBRID/cubrid/pull/7927) writes OOS values after choosing
the destination heap. Earlier work is recorded under
[PR #7600](https://github.com/CUBRID/cubrid/pull/7600).

Start with the Korean reviewer guide, then the approved design. The design removes
`REC_OOS_PENDING`, keeps the shared `RECDES` layout, and retains compact-buffer reuse
and in-place finalization. For the remaining medium failures, read the local
diagnosis and bestspace assessment: the `f3144ab` / `fb567a6` comparison reproduces
three ordering differences, but their upstream cause remains unconfirmed.

Index updated: **2026-10-08 (Asia/Seoul)**. Documents retain their recorded source
revisions and verification limits; dates below describe each document's history.

## PR7927 design and reviewer documents

Read these for the implementation, its design constraints, and reviewer explanations.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [Korean reviewer guide](review-guide-ko.md) | Full PR flow, class lifetimes, source navigation and testcase decisions | 2026-10-07 | 2026-10-07 | Explain and independently verify the final PR7927 reviewer deliverables |
| [Approved design](design/no-record-type-design.md) | Row ownership, payload indices, value readers and storage/export guards | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [Partition INSERT call flow (fb567a629)](CBRD-27089-partition-insert-call-flow_fb567a629_codex.md) | Baseline destination selection and the actual heap-insert sequence | 2026-10-06 | 2026-10-06 | Preserve ticket context, navigation and verification evidence |
| [Review simplifications](design/review-simplification.md) | Finalizer, locator and test refinements with verification at 4be72fc | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [Reviewer feedback and reply drafts](design/reviewer-comments-aecce0e.md) | Partial UPDATE costs, baseline attribution and reuse guarantees | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [Published PR body (4be72fc)](CBRD-27089-owner-index-pr-body_4be72fc_codex.md) | Published purpose, implementation and verification summary | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [PR publication context (4be72fc)](CBRD-27089-owner-index-pr-context_4be72fc_codex.md) | Source identity, claim reconciliation and verified publication result | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |

## PR7927 verification and medium diagnosis

Local checks are scoped to their pinned revisions and remain separate from remote CI results.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [Native medium diagnosis (f3144ab / fb567a6)](medium-local-diagnosis/report.md) | 558-case head/base comparison, heap placement and remaining causal gap | 2026-10-07 | 2026-10-07 | Explain reproduced ordering and the remaining causal boundary |
| [Bestspace assessment (Korean)](PR7927-medium-bestspace-divergence-ko.md) | Reusable heap state and page selection evidence with causal limits | 2026-10-08 | 2026-10-08 | Share the evidence-backed assessment and its remaining causal limits with PR readers |
| [Testcase assessment](testcase-assessment/assessment.md) | Failure contracts, justified partition-loader correction and native results | 2026-10-07 | 2026-10-07 | Assess selected PR7927 failures without weakening existing contracts |
| [Owner-index implementation verification](design/no-record-type-verification.md) | Build, CTest, loader and boundary checks at 6b53181d3 | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [Owner-index implementation review](design/no-record-type-review.md) | Standards/Spec findings and corrections at 6b53181d3 | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [Simplification review](design/review-simplification-review.md) | Standards/Spec review of finalizer, locator and tests at 4be72fc | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |

## Historical reports and design alternatives

These explain earlier decisions. Older marker, raw-pointer and routing-probe designs are superseded as implementation guidance; historical CI results apply only to their recorded revisions.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [CI failure attribution (aecce0e)](ci_analysis_report_aecce0e_codex.md) | Exact-head loader, CDC and medium failure evidence and attribution limits | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [Deferred-write acceptance record](CBRD-27089-deferred-write_be7c01a_codex.md) | Original deferred-write design and acceptance through 2026-09-15 | 2026-09-11 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [Prepared-row explanation (9232f11)](CBRD-27089-prepared-row-explained_9232f11_codex.md) | Earlier prepare/destination/finalize architecture and ownership rationale | 2026-10-06 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [PR7600 ownership fix (b871ea3)](CBRD-27089-oos-chain-owner-b871ea3_codex.md) | Earlier partition-heap ownership fix, regressions and verification | 2026-09-04 | 2026-09-04 | Preserve ticket context, navigation and verification evidence |
| [Routing-probe alternative research](design/probe-rebuild-research-b871ea386-codex.md) | Effective-key adapter proposal, feasibility and proof obligations | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [Withdrawn inline RECDES POC](CBRD-27089-inline-recdes-poc_b81d943d2_codex.md) | Alternative implementation, bounded checks and decision limits | 2026-10-06 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [PR7600 teaching book](teaching/report.md) | Consolidated explanation of partition routing, OOS ownership and the diff | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
