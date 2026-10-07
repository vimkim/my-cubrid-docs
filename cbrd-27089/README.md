# CBRD-27089 / PR7927

Current entry point, updated 2026-10-07. The approved local design removes
`REC_OOS_PENDING` without another record type or a shared `RECDES` layout change.
Destination-owned writes, compact-buffer reuse and in-place finalization remain.
Implementation, scoped verification, review and documentation cleanup are complete locally. The task map records all four resolved tasks.

| Read next | Purpose |
| --- | --- |
| [Current design](design/no-record-type-design.md) | Existing row owner, payload indices, explicit reader arguments, storage/export guards |
| [Current verification](design/no-record-type-verification.md) and [two-axis review](design/no-record-type-review.md) | Exact local revision, commands, results and limits |
| [Reviewer dispositions and Korean reply drafts](design/reviewer-comments-aecce0e.md) | The two requested comments, baseline attribution and reuse guarantees |
| [Approved spec](../.scratch/pr7927-oos-review-cleanup/spec.md) and [four-task map](../.scratch/pr7927-oos-review-cleanup/map.md) | Dependencies, acceptance criteria and task status |
| [Interview and decisions](design/temporary-oos-stub-interview.md) | Historical rounds followed by accepted 2026-10-07 decisions |
| [Canonical vocabulary](../CONTEXT.md) | Destination heap, pending OOS value, OOS value reference and finalization |

The [PR](https://github.com/CUBRID/cubrid/pull/7927) remote head was observed as
`aecce0e1216a813771621c13112c8f27d43df22e`, baseline
`fb567a629cdb390fff920542173fa36f454c74a0`. Local follow-up commits and verification
are listed separately. Work-tracker 281 covers the completed design; 289 covers
implementation; 284 covers documentation and comments. No remote replies have been
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
