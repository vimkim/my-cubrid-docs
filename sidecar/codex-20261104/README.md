# Sidecar approval package

Prepared on 2026-11-04, Asia/Seoul, for work item 772. This independent Codex
contribution stops at the handoff's design and POC-plan approval gate. The
engine has not changed. The source skills live on `sidecar-codex`. The
expanded protocol suite checks the proposed design; the earlier heap-vacuum result remains a separate finding.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [design.md](design.md) | Proposed storage, ownership, history, and integration contracts | 2026-11-04 | 2026-11-04 | Obtain an explicit design decision before engine implementation |
| [poc-plan.md](poc-plan.md) | Phases, planned acceptance CLI, metrics, and stop conditions | 2026-11-04 | 2026-11-04 | Make POC success falsifiable |
| [grounding.md](grounding.md) | Exact-revision engine architecture and constraints | 2026-11-04 | 2026-11-04 | Keep design claims tied to source |
| [verification.md](verification.md) | Bounded slot-undo model result, mutation checks, and limits | 2026-11-04 | 2026-11-04 | Explain what the executable formal skill establishes |
| [formal-verification.md](formal-verification.md) | Expanded protocol results, repaired verification gaps, and finite limits | 2026-11-04 | 2026-11-04 | Explain the deeper checks before engine approval |
| [formal-workflow.md](formal-workflow.md) | Completion predicate and independent model ownership | 2026-11-04 | 2026-11-04 | Make the new verification phase reviewable |
| [review.md](review.md) | Independent review, evidence, corrections, and unverified obligations | 2026-11-04 | 2026-11-04 | Expose what still needs engine proof |
| [workflow.md](workflow.md) | Run scope, phases, gates, and parallel ownership | 2026-11-04 | 2026-11-04 | Preserve the approved execution boundary |

[decisions.tsv](decisions.tsv) is the retained audit trail. It records the
choices behind this package. Temporary candidate drafts, transcripts, raw TLC
output, and downloads remain outside Git. The committed source skill can
regenerate its model and replay evidence.
