# Inner Table

Inner Table is an independent Codex design for storing large CUBRID column
values outside the hot heap row. Each parent class gets a hidden ordinary MVCC
chunk relation with a unique chunk index. The hot row names each value by a
logical value ID, not by a page or slot address. One row column owns each
value, and an ordinary MVCC DELETE retires it. Complete logical WAL images
carry values to HA, CDC and flashback, so those consumers never read live
chunks.

Last modified: 2026-11-10, Asia/Seoul.

## Name and relation to other projects

The user renamed this project from `sidecar-codex` to Inner Table on
2026-11-09. The documents below were written on 2026-11-04 under the old name
and still say "Sidecar". In them, "Sidecar" means this design. They also cite
work item 772, `/home/vimkim/gh/cb/sidecar-codex` and branch `sidecar-codex`.
Those paths and names are kept as recorded. The current names are:

- Engine worktree `/home/vimkim/gh/cb/inner-table`, branch `inner-table`, based
  on CUBRID `develop` `e64a04a79`. No PR exists.
- Work-tracker item 867.

The Claude design in [../sidecar/README.md](../sidecar/README.md) is a
separate project with the same goal. It stores each value as an ordinary heap
record in a per-heap store file and points to it by store OID. The two
designs share the premise that a value should follow the ordinary MVCC
lifecycle instead of a private OOS lifecycle. They differ in addressing,
history transport and engine footprint.

The documents first lived on the unmerged docs branch `sidecar-codex-design`,
in `sidecar/codex-20261104/` (commits `12b1d0d` and `e26de5a`). The engine
skill `verify-sidecar-protocol` cites `12b1d0d` as its design basis.

## Documents

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [design.md](design.md) | Proposed storage, ownership, history, and integration contracts | 2026-11-04 | 2026-11-04 | Obtain an explicit design decision before engine implementation |
| [poc-plan.md](poc-plan.md) | Phases, planned acceptance CLI, metrics, and stop conditions | 2026-11-04 | 2026-11-04 | Make POC success falsifiable |
| [grounding.md](grounding.md) | Exact-revision engine architecture and constraints | 2026-11-04 | 2026-11-04 | Keep design claims tied to source |
| [verification.md](verification.md) | Bounded slot-undo model result, mutation checks, and limits | 2026-11-04 | 2026-11-04 | Explain what the executable formal skill establishes |
| [formal-verification.md](formal-verification.md) | Expanded protocol results, repaired verification gaps, and finite limits | 2026-11-04 | 2026-11-04 | Explain the deeper checks before engine approval |
| [formal-workflow.md](formal-workflow.md) | Completion predicate and independent model ownership | 2026-11-04 | 2026-11-04 | Make the new verification phase reviewable |
| [review.md](review.md) | Independent review, evidence, corrections, and unverified obligations | 2026-11-04 | 2026-11-10 | Expose what still needs engine proof |
| [workflow.md](workflow.md) | Run scope, phases, gates, and parallel ownership | 2026-11-04 | 2026-11-04 | Preserve the approved execution boundary |

[decisions.tsv](decisions.tsv) is the retained audit trail. It records the
choices behind this package. Temporary candidate drafts, transcripts, raw TLC
output, and downloads remain outside Git. [probes/visibility.py](probes/visibility.py)
is the visibility probe that [review.md](review.md) runs. The committed engine
skills can regenerate their models and replay evidence.
