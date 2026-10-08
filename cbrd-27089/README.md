# CBRD-27089 / PR7927

Current entry point, updated 2026-10-08. The approved local design removes
`REC_OOS_PENDING` without another record type or a shared `RECDES` layout change.
Destination-owned writes, compact-buffer reuse and in-place finalization remain.
The no-record-type implementation, scoped verification, review and documentation cleanup are complete locally. The original task map records four resolved tasks. The subsequent [review simplification](design/review-simplification.md) records the selected finalizer, locator and test-organization refinements.

| Read next | Purpose |
| --- | --- |
| [Bestspace assessment (Korean)](PR7927-medium-bestspace-divergence-ko.md) | Why the three ordering differences point to reusable heap state and bestspace selection, with the unconfirmed causal boundary |
| [Native medium diagnosis at f3144ab / fb567a6](medium-local-diagnosis/report.md) | Reproduced 558-case head/base ordering split, matched inputs, plans, OIDs, insertion boundary and remaining causal gap |
| [Korean reviewer guide](review-guide-ko.md) | Full PR prepare/destination/finalize flow, class lifetimes, symbol navigation and testcase decisions |
| [Testcase assessment](testcase-assessment/assessment.md) | Selected failure contracts, justified partition-loader testcase correction, exact native results and remaining limits |
| [Published PR body](CBRD-27089-owner-index-pr-body_4be72fc_codex.md) and [publication context](CBRD-27089-owner-index-pr-context_4be72fc_codex.md) | PR7927 body published unchanged for remote `4be72fc20`; exact body, title and ready status verified |
| [Current design](design/no-record-type-design.md) | Existing row owner, payload indices, explicit reader arguments, storage/export guards |
| [Latest simplification verification](design/review-simplification.md), [original no-record-type verification](design/no-record-type-verification.md) and [its two-axis review](design/no-record-type-review.md) | Exact local revisions, commands, results and limits |
| [Reviewer dispositions and Korean reply drafts](design/reviewer-comments-aecce0e.md) | The two requested comments, baseline attribution and reuse guarantees |
| [Approved spec](../.scratch/pr7927-oos-review-cleanup/spec.md) and [four-task map](../.scratch/pr7927-oos-review-cleanup/map.md) | Dependencies, acceptance criteria and task status |
| [Interview and decisions](design/temporary-oos-stub-interview.md) | Historical rounds followed by accepted 2026-10-07 decisions |
| [Canonical vocabulary](../CONTEXT.md) | Destination heap, pending OOS value, OOS value reference and finalization |

The original [PR](https://github.com/CUBRID/cubrid/pull/7927) comment assessment used
`aecce0e1216a813771621c13112c8f27d43df22e`, baseline
`fb567a629cdb390fff920542173fa36f454c74a0`. On 2026-10-07 the remote was subsequently
observed at `6b53181d31d6d6d2615b18b4f914623bb017d7c4`; the publication snapshot then matched
`4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c`, and its approved publication body is live. The newer [native medium diagnosis](medium-local-diagnosis/report.md) pins published head `f3144ab4b72fc2bf73f115c9da1cf193c756457a` against `fb567a629cdb390fff920542173fa36f454c74a0`: missing fixed predecessors explain the earlier native/CI gap, and reusable heap placement explains the observed presentation split. The first upstream heap-state divergence remains open in tracker 242. Their revision-specific evidence is recorded separately.
Work-tracker 281 covers the completed design; 289 covers
implementation; 284 covers documentation and comments; 293 covers the review simplifications. No remote replies have been
posted by this follow-up.

## Historical evidence

These documents remain available with their original revision identities and
verification limits. Their marker/raw-pointer and older architecture explanations
are superseded as current guidance.

- [Exact aecce0e CI report](ci_analysis_report_aecce0e_codex.md) and [symbol review package](review-aecce0e/README.md): reused from the separately committed exact-head package. CI failures and attribution limits are historical evidence, not new local verification.
- [Deferred-write acceptance through 2026-09-15](CBRD-27089-deferred-write_be7c01a_codex.md), [its explanation at bffe13b](CBRD-27089-deferred-write_bffe13b_claude.md), and [9232f11 implementation explanation](CBRD-27089-prepared-row-explained_9232f11_codex.md).
- [Value-reference verification](design/value-ref-review.md) and [older CI acceptance ledger](ci-fix/pr-7927/index.md).
- [PR7600 teaching book](teaching/README.md), [reviewer walkthrough](reviewer-walkthrough-479cd960-codex/README.md), [work map](../.scratch/pr7600-effective-key-routing/map.md) and [scoped ADR](../docs/adr/0001-pr7600-effective-key-routing.md): effective-key routing history, with its original unmet acceptance gates preserved.
- [Withdrawn full-inline POC](CBRD-27089-inline-recdes-poc_b81d943d2_codex.md) and [interview](../.scratch/pr7927-oos-insert-poc/map.md): its worktree/branch was removed; its bounded results remain historical.
- [878f18b CI report](ci_analysis_report_878f18b_codex.md): unavailable collector/repair links have their original paths recorded in the [evidence inventory](design/unavailable-878f18b-evidence.json).

The source worktree's old `.scratch/oos-deferred-write` notes are labeled historical; [text snapshots and provenance](design/legacy-task-notes/SESSION.md) are retained here.
Private database/core fixtures and prior evidence are preserved. New task status
lives in the approved four-task map above.

## Repository file index

Dates below use the Git creation and modification dates for each path in Asia/Seoul. Historical evidence retains its original contents and revision limits.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [PR7927-medium-bestspace-divergence-ko.md](PR7927-medium-bestspace-divergence-ko.md) | Korean provisional bestspace/reusable-heap attribution for the three medium ordering failures | 2026-10-08 | 2026-10-08 | Share the evidence-backed assessment and its remaining causal limits with PR readers |
| [CBRD-27089-deferred-write_be7c01a_codex.md](CBRD-27089-deferred-write_be7c01a_codex.md) | [CBRD-27089] Destination-owned deferred OOS writes | 2026-09-11 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [CBRD-27089-deferred-write_bffe13b_claude.md](CBRD-27089-deferred-write_bffe13b_claude.md) | [CBRD-27089] Destination-owned deferred OOS write — 해설 | 2026-09-18 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [CBRD-27089-inline-recdes-poc_b81d943d2_codex.md](CBRD-27089-inline-recdes-poc_b81d943d2_codex.md) | 목적지 선택 뒤 OOS를 기록하는 inline RECDES POC | 2026-10-06 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [CBRD-27089-oos-chain-owner-b871ea3_codex.md](CBRD-27089-oos-chain-owner-b871ea3_codex.md) | [CBRD-27089] Keep OOS value chains with the pruned partition heap | 2026-09-04 | 2026-09-04 | Preserve ticket context, navigation and verification evidence |
| [CBRD-27089-oos-chains-follow-pruned-partition_2ed0e60_claude.md](CBRD-27089-oos-chains-follow-pruned-partition_2ed0e60_claude.md) | [CBRD-27089] Write OOS value chains to the pruned partition's heap | 2026-08-03 | 2026-08-03 | Preserve ticket context, navigation and verification evidence |
| [CBRD-27089-owner-index-pr-body_4be72fc_codex.md](CBRD-27089-owner-index-pr-body_4be72fc_codex.md) | Revision-specific documentation and supporting context | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [CBRD-27089-owner-index-pr-context_4be72fc_codex.md](CBRD-27089-owner-index-pr-context_4be72fc_codex.md) | PR7927 owner-index publication context | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [CBRD-27089-partition-insert-call-flow_fb567a629_codex.md](CBRD-27089-partition-insert-call-flow_fb567a629_codex.md) | 파티션 INSERT는 부모와 자식에서 heap insert를 각각 호출하는가? | 2026-10-06 | 2026-10-06 | Preserve ticket context, navigation and verification evidence |
| [CBRD-27089-pr-body_9232f11_codex.md](CBRD-27089-pr-body_9232f11_codex.md) | Revision-specific documentation and supporting context | 2026-10-06 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [CBRD-27089-prepared-row-explained_9232f11_codex.md](CBRD-27089-prepared-row-explained_9232f11_codex.md) | PR #7927 — 목적지 heap을 정한 뒤 OOS 값을 기록하는 이유와 구현 | 2026-10-06 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [CBRD-27089-simplified-ownership-pr-body_aecce0e_codex.md](CBRD-27089-simplified-ownership-pr-body_aecce0e_codex.md) | Revision-specific documentation and supporting context | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [CBRD-27089-simplified-ownership-pr-context_aecce0e_codex.md](CBRD-27089-simplified-ownership-pr-context_aecce0e_codex.md) | PR 7927 publication context | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [CBRD-27089-value-ref-pr-body_f578cd0_codex.md](CBRD-27089-value-ref-pr-body_f578cd0_codex.md) | Revision-specific documentation and supporting context | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [CBRD-27089-value-ref-pr-context_f578cd0_codex.md](CBRD-27089-value-ref-pr-context_f578cd0_codex.md) | PR7927 replacement description review | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [PR-7600-report_ee2cb7b_claude.md](PR-7600-report_ee2cb7b_claude.md) | PR #7600 코드 리뷰 보고서 | 2026-08-14 | 2026-08-14 | Preserve ticket context, navigation and verification evidence |
| [README.md](README.md) | Ticket overview and file index | 2026-10-07 | 2026-10-08 | Help readers find ticket documents and evidence |
| [ci-fix/pr-7927/index.md](ci-fix/pr-7927/index.md) | PR7927 remote acceptance record | 2026-09-11 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [ci-fix/pr-7927/review.md](ci-fix/pr-7927/review.md) | Ticket22 two-axis review | 2026-09-11 | 2026-09-11 | Preserve ticket context, navigation and verification evidence |
| [ci_analysis_report_34a9072_claude.md](ci_analysis_report_34a9072_claude.md) | CI Analysis: PR #7927 at `34a9072` (CBRD-27089) | 2026-09-23 | 2026-09-23 | Preserve ticket context, navigation and verification evidence |
| [ci_analysis_report_34a9072_codex.md](ci_analysis_report_34a9072_codex.md) | PR #7927 CI evidence warning — `34a9072a` | 2026-09-29 | 2026-09-30 | Preserve ticket context, navigation and verification evidence |
| [ci_analysis_report_512b361_codex.md](ci_analysis_report_512b361_codex.md) | CI Failure Analysis: PR #7927 at `512b361` | 2026-09-15 | 2026-09-15 | Preserve ticket context, navigation and verification evidence |
| [ci_analysis_report_878f18b_codex.md](ci_analysis_report_878f18b_codex.md) | CI Failure Analysis: PR #7927 at `878f18b` | 2026-09-15 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [ci_analysis_report_aecce0e_codex.md](ci_analysis_report_aecce0e_codex.md) | PR #7927 CI failure attribution — aecce0e12 | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [ci_analysis_report_b871ea3_codex.md](ci_analysis_report_b871ea3_codex.md) | CI Failure Analysis: PR #7600 at `b871ea3` | 2026-09-04 | 2026-09-04 | Preserve ticket context, navigation and verification evidence |
| [ci_analysis_report_be7c01a_codex.md](ci_analysis_report_be7c01a_codex.md) | CI Failure Analysis: PR #7927 at `be7c01a` | 2026-09-11 | 2026-09-11 | Preserve ticket context, navigation and verification evidence |
| [code_review_290aa50_opus.md](code_review_290aa50_opus.md) | Code Review: PR #7927 at `290aa50` (CBRD-27089) | 2026-09-23 | 2026-09-23 | Preserve ticket context, navigation and verification evidence |
| [deferred-write-512b361-evidence/review.md](deferred-write-512b361-evidence/review.md) | Integration review | 2026-09-15 | 2026-09-15 | Preserve ticket context, navigation and verification evidence |
| [deferred-write-be7c01a-evidence/spec-review.md](deferred-write-be7c01a-evidence/spec-review.md) | Ticket 21 — Spec review | 2026-09-11 | 2026-09-11 | Preserve ticket context, navigation and verification evidence |
| [deferred-write-be7c01a-evidence/standards-review.md](deferred-write-be7c01a-evidence/standards-review.md) | Ticket 21 standards review | 2026-09-11 | 2026-09-11 | Preserve ticket context, navigation and verification evidence |
| [design/acceptance-completion-path-213ce80f5-codex.md](design/acceptance-completion-path-213ce80f5-codex.md) | PR7600 acceptance blockers and recommended completion path | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [design/blocked-handoff-213ce80f5-codex.md](design/blocked-handoff-213ce80f5-codex.md) | PR7600 — locally committed blocked handoff | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [design/design-interview.md](design/design-interview.md) | PR 7600 design interview | 2026-09-10 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [design/destination-reuse-review-213ce80f5-codex.md](design/destination-reuse-review-213ce80f5-codex.md) | Design review: reuse the early partition destination? | 2026-09-10 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [design/legacy-task-notes/SESSION.md](design/legacy-task-notes/SESSION.md) | Deferred OOS replacement session state | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [design/legacy-task-notes/map.md](design/legacy-task-notes/map.md) | Replace early OOS routing with destination-owned deferred writes | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [design/no-record-type-design.md](design/no-record-type-design.md) | PR7927 destination-owned OOS writes without a temporary record type | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [design/no-record-type-review.md](design/no-record-type-review.md) | PR7927 local follow-up code review | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [design/no-record-type-verification.md](design/no-record-type-verification.md) | PR7927 owner-index implementation verification | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [design/probe-rebuild-research-b871ea386-codex.md](design/probe-rebuild-research-b871ea386-codex.md) | PR #7600: remove full-row routing probes without changing OOS ownership | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [design/review-fix-interview_d08a169_claude.md](design/review-fix-interview_d08a169_claude.md) | PR #7927 review-fix design interview | 2026-09-18 | 2026-09-18 | Preserve ticket context, navigation and verification evidence |
| [design/review-simplification-review.md](design/review-simplification-review.md) | PR7927 simplification code review | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [design/review-simplification.md](design/review-simplification.md) | PR7927 review simplification | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [design/reviewer-comments-aecce0e.md](design/reviewer-comments-aecce0e.md) | PR7927 partial UPDATE feedback assessment | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [design/routing-review-213ce80f5-codex.md](design/routing-review-213ce80f5-codex.md) | PR7600 routing change — blocked-handoff review | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [design/temporary-oos-stub-interview.md](design/temporary-oos-stub-interview.md) | PR7927 temporary OOS stub design interview | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [design/ticket01-routing-prefactor-b871ea386-codex.md](design/ticket01-routing-prefactor-b871ea386-codex.md) | Ticket 01 — routing characterization and shared selection | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [design/ticket02-insert-routing-b871ea386-codex.md](design/ticket02-insert-routing-b871ea386-codex.md) | Ticket 02 — effective-key INSERT routing | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [design/ticket03-update-routing-b871ea386-codex.md](design/ticket03-update-routing-b871ea386-codex.md) | Ticket 03: effective-key UPDATE routing | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [design/ticket04-cleanup-b871ea386-codex.md](design/ticket04-cleanup-b871ea386-codex.md) | Ticket 04 — failure cleanup verification | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [design/ticket06-cpu-attribution-b871ea386-codex.md](design/ticket06-cpu-attribution-b871ea386-codex.md) | Ticket 06: small-inline CPU work attribution | 2026-09-10 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [design/ticket06-evidence/diagnosis-20260910/README.md](design/ticket06-evidence/diagnosis-20260910/README.md) | Section entry point and navigation | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [design/ticket06-interleaved-b871ea386-codex.md](design/ticket06-interleaved-b871ea386-codex.md) | Ticket 06: same-host interleaved timing follow-up | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [design/ticket06-measurements-b871ea386-codex.md](design/ticket06-measurements-b871ea386-codex.md) | Ticket 06 — effective-key routing measurements | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [design/ticket06-runtime-diagnosis-988a4d2-codex.md](design/ticket06-runtime-diagnosis-988a4d2-codex.md) | PR7600 small-row runtime diagnosis — 988a4d2 / Codex | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [design/ticket07-preliminary-evidence-matrix-213ce80f5-codex.md](design/ticket07-preliminary-evidence-matrix-213ce80f5-codex.md) | Ticket 07 — preliminary requirement-to-evidence matrix | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [design/tickets04-06-review-b871ea386-codex.md](design/tickets04-06-review-b871ea386-codex.md) | PR #7600 tickets04/06 — two-axis review | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [design/tickets04-07-lifecycle-blocker-b871ea386-codex.md](design/tickets04-07-lifecycle-blocker-b871ea386-codex.md) | Tickets 04–07: baseline lifecycle blocker | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [design/value-ref-review.md](design/value-ref-review.md) | PR7927 value-reference redesign review | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [review-988a4d2-codex/README.md](review-988a4d2-codex/README.md) | Section entry point and navigation | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [review-988a4d2-codex/spec.md](review-988a4d2-codex/spec.md) | PR #7600 — Spec review | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [review-988a4d2-codex/standards.md](review-988a4d2-codex/standards.md) | PR #7600 — Standards review | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [review-988a4d2-codex/verification.md](review-988a4d2-codex/verification.md) | PR #7600 — execution and worktree review | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [review-aecce0e/README.md](review-aecce0e/README.md) | Section entry point and navigation | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [review-aecce0e/code_review_guide.md](review-aecce0e/code_review_guide.md) | PR #7927 code review guide — aecce0e12 | 2026-10-07 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [review-d08a169-claude/README.md](review-d08a169-claude/README.md) | Section entry point and navigation | 2026-09-18 | 2026-09-18 | Preserve ticket context, navigation and verification evidence |
| [review-d08a169-claude/spec.md](review-d08a169-claude/spec.md) | PR #7927 — Spec review | 2026-09-18 | 2026-09-18 | Preserve ticket context, navigation and verification evidence |
| [review-d08a169-claude/standards.md](review-d08a169-claude/standards.md) | PR #7927 — Standards review | 2026-09-18 | 2026-09-18 | Preserve ticket context, navigation and verification evidence |
| [review-guide-ko.md](review-guide-ko.md) | Korean full-PR reviewer guide with exact revisions, symbol sections and testcase decisions | 2026-10-07 | 2026-10-07 | Explain and independently verify the final PR7927 reviewer deliverables |
| [reviewer-walkthrough-479cd960-codex/README.md](reviewer-walkthrough-479cd960-codex/README.md) | Section entry point and navigation | 2026-09-10 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [reviewer-walkthrough-479cd960-codex/authoring/function-research.en.md](reviewer-walkthrough-479cd960-codex/authoring/function-research.en.md) | PR #7600: production function research | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [reviewer-walkthrough-479cd960-codex/authoring/reviewer-guide.en.md](reviewer-walkthrough-479cd960-codex/authoring/reviewer-guide.en.md) | PR #7600 — route the row before choosing its OOS owner | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [reviewer-walkthrough-479cd960-codex/authoring/reviewer-guide.ko.md](reviewer-walkthrough-479cd960-codex/authoring/reviewer-guide.ko.md) | PR #7600 — 레코드를 보낼 곳을 먼저 결정한다 | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [reviewer-walkthrough-479cd960-codex/authoring/start-here.en.md](reviewer-walkthrough-479cd960-codex/authoring/start-here.en.md) | PR #7600: choose the partition before writing OOS data | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [reviewer-walkthrough-479cd960-codex/authoring/start-here.ko.md](reviewer-walkthrough-479cd960-codex/authoring/start-here.ko.md) | PR #7600: OOS 값을 쓰기 전에 파티션을 고른다 | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [reviewer-walkthrough-479cd960-codex/evidence/brand-rules.md](reviewer-walkthrough-479cd960-codex/evidence/brand-rules.md) | Warp Brand System | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [reviewer-walkthrough-479cd960-codex/evidence/brand.md](reviewer-walkthrough-479cd960-codex/evidence/brand.md) | Revision-specific documentation and supporting context | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [reviewer-walkthrough-479cd960-codex/evidence/fact-check.md](reviewer-walkthrough-479cd960-codex/evidence/fact-check.md) | Source and claim audit | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [reviewer-walkthrough-479cd960-codex/functions.en.md](reviewer-walkthrough-479cd960-codex/functions.en.md) | PR #7600 — function inventory and direct calls | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [reviewer-walkthrough-479cd960-codex/review.en.md](reviewer-walkthrough-479cd960-codex/review.en.md) | PR #7600 — route the row before choosing its OOS owner | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [reviewer-walkthrough-479cd960-codex/review.ko.md](reviewer-walkthrough-479cd960-codex/review.ko.md) | PR #7600 — 레코드를 보낼 곳을 먼저 결정한다 | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [reviewer-walkthrough-479cd960-codex/start-here.en.md](reviewer-walkthrough-479cd960-codex/start-here.en.md) | PR #7600: choose the partition before writing OOS data | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [reviewer-walkthrough-479cd960-codex/start-here.ko.md](reviewer-walkthrough-479cd960-codex/start-here.ko.md) | PR #7600: OOS 값을 쓰기 전에 파티션을 고른다 | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/MISSION.md](teaching/MISSION.md) | Mission: Understand and evaluate PR #7600 | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/NOTES.md](teaching/NOTES.md) | Teaching notes | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/README.md](teaching/README.md) | Section entry point and navigation | 2026-09-10 | 2026-10-07 | Preserve ticket context, navigation and verification evidence |
| [teaching/RESOURCES.md](teaching/RESOURCES.md) | PR #7600 Learning Resources | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/chapters/01-foundations.md](teaching/chapters/01-foundations.md) | 1. From a SQL table to a stored record | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/chapters/02-oos-and-the-bug.md](teaching/chapters/02-oos-and-the-bug.md) | 2. Why correct SELECT results can conceal wrong ownership | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/chapters/03-the-two-pass-contract.md](teaching/chapters/03-the-two-pass-contract.md) | 3. Build a probe, choose the partition, then store the value | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/chapters/04-layout-and-side-effects.md](teaching/chapters/04-layout-and-side-effects.md) | 4. How suppression and exactly-once effects work | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/chapters/05-probes-errors-and-lifecycle.md](teaching/chapters/05-probes-errors-and-lifecycle.md) | 5. Duplicate probes, errors and lifetime | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/chapters/06-annotated-diff.md](teaching/chapters/06-annotated-diff.md) | 6. Every changed line, in its source context | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/chapters/07-tests-and-observations.md](teaching/chapters/07-tests-and-observations.md) | 7. Read the regression as a specification | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/chapters/08-design-and-review.md](teaching/chapters/08-design-and-review.md) | 8. Explain the design, then challenge it | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/chapters/09-answers.md](teaching/chapters/09-answers.md) | 9. Answers and teach-back rubric | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/chapters/10-source-map.md](teaching/chapters/10-source-map.md) | 10. Source map and evidence ledger | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/evidence/content-audit.md](teaching/evidence/content-audit.md) | Content and presentation audit — 2026-09-08 | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/learning-progress.md](teaching/learning-progress.md) | PR 7600 learning progress | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/learning-records/0001-range-boundary-selection.md](teaching/learning-records/0001-range-boundary-selection.md) | Correct partition selection at the range boundary | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/learning-records/0002-partition-selects-heap.md](teaching/learning-records/0002-partition-selects-heap.md) | Partition selection determines the row's heap | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/learning-records/0003-ownership-and-ordering-question.md](teaching/learning-records/0003-ownership-and-ordering-question.md) | Ownership mapping and an ordering alternative | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/lessons/0001-selecting-a-partition.md](teaching/lessons/0001-selecting-a-partition.md) | Lesson 0001: Which partition receives the row? | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/lessons/0002-partition-heap.md](teaching/lessons/0002-partition-heap.md) | Lesson 0002: A partition has a heap | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/lessons/0003-heap-oos-ownership.md](teaching/lessons/0003-heap-oos-ownership.md) | Lesson 0003: The heap's optional OOS file | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/lessons/0004-what-pruning-reads.md](teaching/lessons/0004-what-pruning-reads.md) | Lesson 0004: Full-record interface, single-attribute dependency | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/lessons/0005-effective-key-write-journey.md](teaching/lessons/0005-effective-key-write-journey.md) | One INSERT, one moving UPDATE: choose the owner before building the row | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/report.md](teaching/report.md) | PR 7600 teaching book | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [teaching/scope.md](teaching/scope.md) | Analysis Scope | 2026-09-10 | 2026-09-10 | Preserve ticket context, navigation and verification evidence |
| [testcase-assessment/assessment.md](testcase-assessment/assessment.md) | PR7927 failure contracts, justified partition fix, native verification and limits | 2026-10-07 | 2026-10-07 | Assess selected PR7927 failures without weakening existing contracts |
| [medium-local-diagnosis/report.md](medium-local-diagnosis/report.md) | Local native medium diagnosis for exact f3144ab / fb567a6 | 2026-10-07 | 2026-10-07 | Explain reproduced ordering and the remaining causal boundary |
