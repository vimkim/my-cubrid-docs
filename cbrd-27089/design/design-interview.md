# PR 7600 design interview

Status: interview complete. The user's invocation of `to-spec` after the final summary confirms shared understanding and authorizes specification synthesis. Implementation and experiments remain unauthorized.

Specification published to the configured local tracker: [effective-key routing spec](../../.scratch/pr7600-effective-key-routing/spec.md), `Status: ready-for-agent`. The user confirmed the proposed SQL, existing failure-injection, and conditional focused effective-key routing test seams with “cnofirm.” No execution authorization is implied.

Evidence: [source research at b871ea386](probe-rebuild-research-b871ea386-codex.md).

## Confirmed user constraints

- Investigate facts rather than asking the user to supply source knowledge.
- Compare narrow effective-key routing against retaining the probe and splitting preparation/serialization.
- Recommend defaults with trade-offs and record decisions as agreed.
- No engine edits or experiments. Prepare for specification only after decisions are settled and shared understanding is confirmed.

## Decision tree

- D1: What benefit justifies replacing the existing path? ACCEPTED: measurable benefit with maintainability constraints.
  - D3: Choose scope/design: ACCEPTED narrow effective-key routing, conditional on correctness and benefit gates.
    - D4: ACCEPTED complete legal-key coverage on the scoped path; no silent type-dependent fallback.
    - D5: ACCEPTED preserve downstream routing initially; reopen if its cost defeats acceptance.
  - D6: ACCEPTED measured temporary allocation/copying savings may suffice with flat runtime; no reproducible control-workload slowdown beyond measured noise without renewed approval.
- D2: Compatibility when one statement contains multiple independent errors. ACCEPTED: precedence may differ; successful results, single-failure errors, and transactional correctness are preserved.
  - D7: Failure validation follows accepted D2/D3: single-failure errors and transaction cleanup preserved; key-only routing must not perform persistent writes. Detailed checks are proof obligations, not choices to relax correctness.
- D8: CONFIRMED by the user's invocation of `to-spec` after the final summary. D1–D7 policies settled; proof obligations below remain unproven and must enter the specification.

## Round 1 frontier

### Q1 / D1: Benefit required to justify replacement

Accepted by the user's “as recommended” response to Q1/Q2: treat this as a performance optimization with maintainability constraints. Require demonstrated reduction in temporary full-row allocation/copying on OOS-producing writes plus an acceptable measured runtime profile. Architectural neatness alone is insufficient; retain the existing probe if the candidate adds complexity without useful benefit. Numeric tolerances and workloads are later decisions, not assumed here.

Alternative: prioritize a clearer lifecycle/interface even if performance is approximately unchanged. This makes a broader preparation split more plausible but enlarges the design and validation scope.

### Q2 / D2: Error precedence compatibility

Scenario: the partition key matches no partition, while another attribute would independently fail during record preparation. Earlier routing might change which error is reported first.

Accepted by the user's “as recommended” response to Q1/Q2: preserve successful results, ownership, transactional cleanup, and the appropriate error when only one failure exists; allow different precedence when multiple independent errors coexist. Do not require the old ordering merely to preserve which of several errors appears first.

## Round 2 frontier

### Q3 / D3: Candidate to take into specification

Accepted by the user's “yes” to Q3: specify narrow effective-key routing, preserving per-heap OOS ownership and leaving global preparation/LOB handling unchanged. Keep the existing probe as the comparison baseline and do not ship the candidate unless correctness and benefit gates are met. Defer a full preparation/serialization split unless key-only routing requires enough duplicated semantics or special cases to undermine its maintainability advantage; that finding would reopen the design choice rather than authorize scope expansion.

Alternatives: retain the current implementation and seek baseline measurement approval before specifying a replacement; or choose the broader preparation split now and accept its larger validation scope. This round authorizes only a design direction, not experiments or engine edits. Coverage/fallback policy, downstream routing, workload tolerances, and detailed failure expectations are subsequent decisions dependent on this choice.

## Proof obligations (facts/tests, not user preferences)

- Effective routing key equals the value seen through the stored-record decoder across legal types, expressions, defaults, old representations, and pending increments.
- Temporary key processing does not mutate original assignments or leave cached expression pointers dangling.
- Real increments and LOB operations retain exactly-once behavior through retries and failures.
- Early and final routing destinations agree; final lock/cache/representation/movement behavior is preserved.
- No durable partial effects after failure; OOS publication state remains correct.
- Measure large-row benefit and small non-OOS overhead; no performance result is currently available.

Architectural direction recorded in [ADR 0001](../../docs/adr/0001-pr7600-effective-key-routing.md). No new glossary term has yet been ratified in this interview; record resolved terminology using the repository's domain-doc convention when needed.

## Round 3 frontier

### Q4 / D4: Coverage

Accepted by the user's “as recommended” response to Q4–Q6: target all legal partition-key types and expressions on the scoped locator write path. If equivalence cannot be established, stop and reopen scope rather than silently retaining a type-dependent fallback. Keep REPLACE/ODKU duplicate probes outside this optimization; no claim of removing every probe everywhere.

Alternative: ship an explicitly limited fast path (for example integer keys), retaining the old probe for other keys. Smaller initial proof surface, but two permanent paths and narrower benefit.

### Q5 / D5: Final routing

Accepted by the user's “as recommended” response to Q4–Q6: preserve downstream record-based routing and surrounding validation/locking/cache/representation/movement behavior for the initial change. If its measured cost defeats acceptance, reopen the design rather than automatically expand the force interface.

Alternative: carry a validated routing result through force now, separating selection from required finalization. Removes repeat selection but broadens the refactor and validation surface.

### Q6 / D6: Benefit and workload gate

Accepted by the user's “as recommended” response to Q4–Q6: accept proven elimination of full inline temporary records and measurable temporary allocation/copying savings on OOS-producing writes even if elapsed time is approximately unchanged, provided repeated measurements show no reproducible slowdown beyond measured noise on small non-OOS and nonpartitioned controls. A runtime improvement is welcome, not mandatory; any repeatable slowdown requires an explicit trade-off decision before acceptance.

Use the source-driven matrix: large uncompressed non-key payloads, small forced-outline values, small inline rows, unchanged-key updates, moved updates, and nonpartitioned controls. Include integer and string/expression keys. Benchmark methodology must estimate noise and report per-workload results rather than hide a regression in an aggregate average. These are future measurements; no experiment is authorized now.

Alternative: require an elapsed-time/throughput improvement too; allocation savings alone would not justify replacement.

## Round 4: final confirmation and specification inputs

The user confirmed the combined D1–D7 summary by proceeding to `to-spec`. This authorizes specification, not implementation. The specification must include:

- Source baseline and exact locator write-path scope; duplicate-key probes and global LOB lifecycle excluded from refactoring.
- Effective-key ownership/lifetime contract, defaults/old representations, stored-domain normalization, and clone-versus-real INCR application.
- Destination-aware first-pass transformation and preserved downstream routing, locks, caches, representation handling, and movement.
- All legal key types/expressions covered; inability to prove equivalence reopens design rather than narrowing scope silently.
- Failure matrix with accepted multi-error precedence flexibility and unchanged correctness/cleanup requirements.
- Differential semantic tests, SA and SERVER_MODE coverage, allocation/copying counters, repeated timing methodology, and control workloads.
- Explicit stop/reopen gates for excessive semantic duplication, routing disagreement, missing coverage, insufficient benefit, and repeatable regression.

The key-only codec/normalization strategy remains a proposal to detail and prove in specification and tests, not a completed implementation. No engine edits or experiments have occurred in this interview.
