# Sidecar protocol verification workflow

The user requested deeper TLA+ checks with subagents before engine work on
2026-11-04, Asia/Seoul. This extends work item 772. Engine implementation,
integration, and publication remain behind the earlier approval gates.

The data shape is a set of bounded transition systems for value lifetime,
durable historical records, and physical undo resources. A model describes
the proposed protocol. It is not a verified implementation of the engine.

## Figure-it-out phases

- [x] Read the Principles section of the **poteto-mode** skill.
- [x] Phase A: Frame.
- [x] Phase B: Design the workflow.
- [x] Phase C: Run the loop.
- [x] Phase D: Keep the audit trail.
- [x] Phase E: Verification completed; the report is ready for chat handoff.

## Architect and arena steps

- [x] Ground. Reuse the exact-revision grounding and inspect its open limits.
- [x] Sketch.
- [x] Agree. Proceed with verification under the user's new request.
- [x] Implement. This means verification artifacts only.
- Scrap was not needed; the chosen shape represented the bounded protocol.

- [x] Frame.
- [x] Fan out.
- [x] Cross-judge. No cross-vendor model is configured. Record this limitation.
- [x] Pick.
- [x] Graft.
- [x] Verify.

## Swarm steps

- [x] Frame.
- [x] Fan out.
- [x] Aggregate.
- [x] Report written; chat handoff follows.

Partition coverage by value lifetime, history and replication, and undo
resources. Each owner has disjoint files. Independent reviewers read the
actual models, run controls, and challenge assumptions and atomic steps.

## Throughput checkpoint

- [x] **Blocking first steps.** Inspect current branches, preserve untracked
  handoff, choose properties and model contracts before writers fan out.
- [x] **Independent workstreams.** Separate models and configuration files
  can be built concurrently after the architecture sketch.
- [x] **Shared mutable state.** The common runner had one designated writer
  at a time; ownership passed from `runner_owner` to the coordinator. The
  coordinator writes final coverage, design revisions, report, and trail.
- [x] **Smallest safe decomposition.** Prefer independently checkable finite
  models over a state space too large to finish. State shared assumptions
  explicitly and do not infer a composition proof from separate passes.

## Completion predicate

1. Every declared safe configuration completes exhaustive TLC exploration
   without an invariant, temporal-property, or nonterminal deadlock failure.
2. Every unsafe control produces its named property violation. A parse error,
   timeout, bound interruption, or unrelated failure is not a successful control.
3. Independent review finds no unresolved mismatch between the proposal,
   modeled atomic steps, declared assumptions, and reported coverage.
4. Larger finite configurations finish, or are explicitly inconclusive.
   An inconclusive required configuration prevents claiming the predicate met.
5. Reproduction is one command with a pinned checker and machine-readable
   results. The real legacy-vacuum finding remains separately reported.
6. Preserve counterexamples and revise the proposed protocol when a genuine
   design error is found. Never weaken a safety property to manufacture a pass.

Finite completion means no violation under the recorded model, assumptions,
and bounds. It does not prove arbitrary database size, implementation
refinement, performance, encryption, or full regression correctness.

## Architecture and review decisions

Independent Astra and Terra sketches both selected three focused transition
systems and a small boundary model. The boundary imports actual history
predicates; it records lifetime and physical undo as correspondences and
assumptions. It does not prove their general composition or action refinement.
Separate owners wrote disjoint directories. Independent reviewers reproduced
the resource, rollback-prefix, cleanup-progress, historical-decoding, and
recovery-completion gaps. Model owners repaired them, with separate reviewers
rechecking the results. Fresh repair owners handled lifetime, undo, and the
final boundary completion gaps. The history owner revised its model while an
independent reviewer checked it. Transaction atomicity also has explicit
controls.

The common runner has an independent required-profile inventory and rejects
empty initial domains, incomplete searches, and unrelated failures. An initial
qualification attempt was stopped after the empty-domain verdict gap. A later
117-case attempt was superseded after the boundary cleanup gaps; it is not
counted as final qualification. The final matrix includes the added controls
and witnesses.

The no-comments pass accepted three comment deletions and a rename to
`UndoLogicalChunk`, making the logical/physical boundary explicit. No
suppressions or outside-rule keeps were found. Deslop is unavailable in this
harness; the coordinator reviews the staged diff directly.

## Completed predicate

The final 121-case qualification completed with 14 exhausted safe searches,
68 named unsafe controls, and 39 named reachability witnesses. It includes
every quick case. Independent result/hash audits passed. The completion
predicate is met for these models, bounds, and assumptions; engine
implementation approval and the separately reported legacy finding remain
open. See [the final report](formal-verification.md) for the exact receipt.
