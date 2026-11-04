# Sidecar approval package

Prepared on 2026-11-04, Asia/Seoul, for work item 772. This independent Codex
contribution stops at the handoff's design and POC-plan approval gate. The
engine has not changed. The source verification skill is committed on
`sidecar-codex` at `bbc5a3113d89d7cdd0cc828e84499d048308a160`.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [design.md](design.md) | Proposed storage, ownership, history, and integration contracts | 2026-11-04 | 2026-11-04 | Obtain an explicit design decision before engine implementation |
| [poc-plan.md](poc-plan.md) | Phases, planned acceptance CLI, metrics, and stop conditions | 2026-11-04 | 2026-11-04 | Make POC success falsifiable |
| [grounding.md](grounding.md) | Exact-revision engine architecture and constraints | 2026-11-04 | 2026-11-04 | Keep design claims tied to source |
| [verification.md](verification.md) | Bounded slot-undo model result, mutation checks, and limits | 2026-11-04 | 2026-11-04 | Explain what the executable formal skill establishes |
| [review.md](review.md) | Independent review, evidence, corrections, and unverified obligations | 2026-11-04 | 2026-11-04 | Expose what still needs engine proof |
| [workflow.md](workflow.md) | Run scope, phases, gates, and parallel ownership | 2026-11-04 | 2026-11-04 | Preserve the approved execution boundary |

[decisions.tsv](decisions.tsv) is the retained audit trail. It records the
choices behind this package. Temporary candidate drafts, transcripts, raw TLC
output, and downloads remain outside Git. The committed source skill can
regenerate its model and replay evidence.
