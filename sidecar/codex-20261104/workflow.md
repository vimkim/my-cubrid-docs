# Sidecar design workflow

Date is 2026-11-04, Asia/Seoul. This run contributes to work item 772 from
`sidecar-codex`, at CUBRID commit `e64a04a79a5842827a124b3f8313516d0da2594c`.
The other Sidecar session and its untracked documents remain separate.

The deliverable for this run is a source-grounded design, an independently
challenged POC plan, and an executable project verification skill. The engine
POC starts only after the user's design and plan approval, as required by
`HANDOFF.md`. Passing a storage model does not satisfy engine acceptance.

## Figure-it-out phases

- [x] Read the Principles section of the **poteto-mode** skill.
- [x] Phase A: Frame.
- [x] Phase B: Design the workflow.
- [x] Phase C: Run the loop.
- [x] Phase D: Keep the audit trail. The independent audit is complete.
- [ ] Phase E: Verify and hand back. Verification is complete. Delivery is the final reply, and design agreement remains pending.

The done predicate for the approval package has six parts.

1. Pin source evidence for projection, MVCC, vacuum, recovery, HA, and consumers.
2. Compare at least two structurally distinct designs against the constraints.
3. Select one design and document its lifecycle, interface, and failure rules.
4. Run adversarial source probes or models and resolve every demonstrated issue.
5. Run the formal skill, break real source in isolation, detect the change, and
   return to the baseline result.
6. Commit the reviewable artifacts and present one concrete approval decision.

## Throughput checkpoint

- [x] **Blocking first steps.** Inspect checkout and handoff. Ground lifetime,
  projection, transport, and WAL before selecting a design. Preserve Gate 1.
- [x] **Independent workstreams.** Three read-only explorers write to separate
  scratch files. Two design candidates write to separate directories. The
  formal-check owner writes only its project skill directory.
- [x] **Shared mutable state.** The coordinator alone writes the final design,
  plan, tracker notes, and this run's decision log. The other Sidecar session's
  files and ledger status remain untouched.
- [x] **Smallest safe decomposition.** One coordinator synthesizes the design.
  One owner implements the bounded verification check. No engine work or
  performance measurement occurs before approval.

## How and swarm steps

- [x] Frame.
- [x] Fan out.
- [x] Aggregate.
- [x] Report.

Partition the grounding by lifecycle, transport, and projection. Require an
artifact for each slice. A missing slice is a gap, not a pass.

## Architect steps

- [x] Ground.
- [x] Sketch.
- [ ] Agree. Pending the handoff's explicit design and plan approval.
- [ ] Implement. Skip until explicit approval of the engine design and POC plan.
- [ ] Scrap. Skip unless the selected shape fails its stated constraints.

## Arena steps

- [x] Frame.
- [x] Fan out.
- [x] Cross-judge. Skip cross-vendor judging because the configured pool has only OpenAI models. Independent Astra and Terra adversarial reviews ran.
- [x] Pick.
- [x] Graft.
- [x] Verify.

Grade candidates on version and rollback lifetime, recoverable reclamation,
portable historical values, useful projected reads, unused-path isolation,
and a bounded POC that tests the hardest unknown first. The candidates receive
the same task and grounding. Their outputs remain independent until judging.

## Authoring or modifying a skill

- [x] Use your skill-authoring skill: **create-skill** in Cursor (built in), or Anthropic's `skill-creator` elsewhere. With neither, follow the Agent Skills format at agentskills.io.
- [x] Validate the skill: frontmatter has `name` and `description`, referenced files exist, cross-skill links resolve.
- [x] Test cases if structural. The real-source mutation, restoration, and safe-order controls passed.
- [x] Run **Opening a PR**. Skip remote publication. The handoff authorizes local commits and requires a separate push request.

## Execution order

1. Ground the existing engine and test the shared-lifecycle premise.
2. Generate distinct designs, independently score them, and synthesize one.
3. Build a bounded model of the existing fixed-slot recovery obligation.
4. Challenge the design with two independent reviewers and rerun their probes.
5. Finish the POC predicates, commands, exclusions, and stop conditions.
6. Validate documents and skill. Review comments and the entire diff. Commit.
7. Present the approval package. Preserve every unresolved engine claim as
   unverified until the POC actually runs.

The expected scope is one design package, one POC plan, one verification skill,
and one decision trail. The largest uncertainty is whether existing heap and
WAL machinery can own cold values without adding a second lifecycle protocol.
