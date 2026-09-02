# Proposed Architecture for the CUBRID Page Buffer Maintainer Guide

> Historical planning record. This proposal was confirmed on 2026-09-01 and became [`spec.md`](./spec.md) in this directory; the guide it describes now lives under `code-analysis/page-buffer-presentation/`. Links below were rewritten when the file moved here.

This proposal replaces the 1,059-line monolith with a small English document set that supports three distinct jobs: learning the Module, working on a change, and diagnosing a symptom. It preserves `page-buffer-teaching-material.md` as the stable guide entry, gives every concept one canonical explanation, and keeps exhaustive evidence outside the learning path.

The design is confirmed and ready to become a specification through `/to-spec`. It does not authorize rewriting the guide yet.

## Decision sources

- Canonical terminology: [`CONTEXT.md`](../../code-analysis/page-buffer-presentation/CONTEXT.md)
- Document-set decision: [`docs/adr/0001-split-guide-by-reading-mode.md`](../../code-analysis/page-buffer-presentation/docs/adr/0001-split-guide-by-reading-mode.md)
- English-only authoring decision: [`docs/adr/0002-author-the-document-set-in-english.md`](../../code-analysis/page-buffer-presentation/docs/adr/0002-author-the-document-set-in-english.md)
- Current authoring contract: [`maintainer-guide-notes.md`](../../code-analysis/page-buffer-presentation/maintainer-guide-notes.md)
- Evidence and source reconciliation: [`source-inventory.md`](../../code-analysis/page-buffer-presentation/source-inventory.md)
- Current uncertainty registry: [`unresolved-or-version-sensitive-findings.md`](../../code-analysis/page-buffer-presentation/unresolved-or-version-sensitive-findings.md)
- Monolith to migrate: [`page-buffer-teaching-material.md`](../../code-analysis/page-buffer-presentation/page-buffer-teaching-material.md)

## Audience and completion model

The target maintainer is a senior C/C++ systems engineer who understands basic database storage, buffer pools, and WAL but has no assumed knowledge of CUBRID source structure or page-buffer protocols.

Core completion means the reader can:

1. draw and explain the `VPID → BCB → frame → PAGE_PTR` object and lifetime model;
2. trace one successful fix and matching release in the pinned source;
3. trace one representative caller and separate Module guarantees from caller obligations;
4. reason about dirty-generation/WAL behavior and victim eligibility;
5. produce a change-impact plan naming the interface family, state owner, invariant, failure unwind, representative caller, and verification seam.

Advanced completion adds ordered access, replacement progress, recovery and lifecycle, specialized interfaces, and fault-sensitive proof obligations. The document set does not equate reading completion with maintainer readiness: the core source exercises are self-checkable, while a real change-impact plan requires review by another maintainer.

## Current-state diagnosis

The monolith contains strong source-backed material, but its delivery model obscures that material:

- 1,059 lines contain 15 second-level headings, 78 third-level headings, 164 table rows, 235 bullet rows, and 41 Markdown links;
- conceptual onboarding, source lookup, safe-change procedure, debugging, verification, hazards, first-week exercises, and reference material compete in one reading surface;
- readers meet Module/Interface vocabulary, seams, broad source ranges, and pool topology before completing one concrete page journey;
- the pool diagram precedes the six-object model needed to interpret it;
- mutation, durability, and replacement share one chapter even though the guide teaches them as independent state dimensions;
- fix debt, pointer lifetime, evidence limits, source navigation, and verification recur in multiple sections without one canonical owner;
- broad line ranges provide routing but do not teach how to trace one bounded behavior;
- the first-week path repeats the main explanation instead of embedding practice at the point of prerequisite knowledge;
- the hazard summary duplicates a status registry that can change independently;
- all six SVGs are used, but four contain Korean text and several overlap in explanatory purpose.

The redesign therefore preserves the evidence and explanations while changing their order, ownership, and reading routes. It does not treat shorter prose or a larger number of files as sufficient by themselves.

## Information architecture

```text
page-buffer-teaching-material.md
│   stable guide entry and route selector
│
├── learning/
│   ├── 01-contract-and-objects.md
│   ├── 02-fix-hold-release.md
│   ├── 03-caller-completes-correctness.md
│   ├── 04-flush-one-generation.md
│   ├── 05-replace-one-frame.md
│   └── 06-maintainer-capstone.md
│
├── playbooks/
│   ├── change-safely.md
│   ├── debug-by-symptom.md
│   └── verify-a-change.md
│
├── advanced/
│   ├── acquisition-concurrency.md
│   ├── replacement-progress.md
│   ├── recovery-and-lifecycle.md
│   ├── specialized-interfaces.md
│   └── failure-and-proof-obligations.md
│
├── reference/
│   ├── source-map.md
│   └── invariant-index.md
│
├── source-inventory.md
├── unresolved-or-version-sensitive-findings.md
└── assets/
    └── SVGs displayed anywhere in the document set
```

The hierarchy separates reading mode, prerequisite level, and evidence depth. It does not split content merely because a section is long.

## Navigation contract

The guide entry exposes these primary links:

| Reader intent | Link text | Target |
|---|---|---|
| Linear onboarding | `Learn the module` | `./learning/01-contract-and-objects.md` |
| Review or modify code | `Work on a change` | `./playbooks/change-safely.md` |
| Investigate behavior | `Diagnose a symptom` | `./playbooks/debug-by-symptom.md` |
| Select evidence | `Verify a change` | `./playbooks/verify-a-change.md` |
| Locate source | `Find the source` | `./reference/source-map.md` |
| Check evidence status | `Check evidence and uncertainty` | `./source-inventory.md` and `./unresolved-or-version-sensitive-findings.md` |

Every page begins with a compact reader contract:

```text
Level: Core | Advanced | Playbook | Reference
Prerequisites: exact page links or target-reader baseline
Capability gained: one observable outcome
Source baseline: f799e05d77d5300c6ea5753b4a6cc7caee6d8912
Evidence used: applicable evidence labels and supporting references
```

Every learning page ends with:

1. one Predict–Locate–Explain understanding check;
2. a concise adjacent model answer;
3. previous and next learning links;
4. related playbook, advanced, and evidence links.

Pages do not reproduce the global table of contents. Playbooks and references link to canonical explanations instead of copying them.

## Guide entry

### `page-buffer-teaching-material.md` — CUBRID Page Buffer Maintainer Guide

**Purpose:** Route the reader. The guide entry explains the audience, outcomes, baseline, evidence vocabulary, learning duration, and three primary reading modes. It does not teach the page-buffer mechanism itself.

**Prerequisite:** Target-reader baseline only.

**Canonical content:**

- purpose and audience;
- core and advanced completion outcomes;
- half-day core, one-to-two-day applied, and first-week advanced expectations;
- the six evidence labels;
- route cards for learning, changing, diagnosing, verifying, source lookup, and evidence status;
- current pinned revision and update warning.

**Navigation:** Core route starts at `learning/01-contract-and-objects.md`. Operational routes go directly to the three playbooks. Advanced pages are listed as optional routes after core completion.

## Core learning path

### 1. `learning/01-contract-and-objects.md` — Contract and Objects: What a Fix Actually Gives You

**Maintainer question:** What does this Module own, and what exactly is “a page”?

**Prerequisite:** Target-reader baseline.

**Canonical content:** Module boundary; caller and dependency seams; `VPID`, BCB, frame, `PAGE_PTR`, global `fcnt`, and holder; borrowed lifetime; independent residency, ownership, concurrency, and durability axes; the successful-fix postcondition at a conceptual level.

**Source exercise:** Locate the six objects and identify their owners and lifetimes without reading the algorithms in file order.

**Understanding evidence:** Object/lifetime sketch plus an explanation of why fixed, resident, dirty, durable, flushed, evicted, and deallocated are not synonyms.

**Navigation:** Previous is the guide entry. Next is `02-fix-hold-release.md`. Related references are `reference/source-map.md` and `reference/invariant-index.md`.

### 2. `learning/02-fix-hold-release.md` — Fix, Hold, and Release: Borrowing a Resident Page

**Maintainer question:** What becomes true after fix, and what debt must be repaid?

**Prerequisite:** Page 1.

**Canonical content:** Fetch intent; latch mode versus wait condition; normal resident hit; cold-miss convergence; expected non-acquisition; latch grant; global and per-thread ledgers; nested ownership; release variants; pointer lifetime. Lock-free internals, promotion, and ordered watchers are only named and linked.

**Source exercise:** Trace one normal hit, the miss convergence point, and the matching unfix. Mark where identity is rechecked and where ownership debt becomes committed.

**Understanding evidence:** Annotated fix/unfix call path and debt ledger.

**Navigation:** Previous is page 1. Next is `03-caller-completes-correctness.md`. Advanced continuation is `advanced/acquisition-concurrency.md`.

### 3. `learning/03-caller-completes-correctness.md` — Caller Completes Correctness: From Access to Logged Mutation

**Maintainer question:** What remains the caller’s responsibility after successful acquisition?

**Prerequisite:** Page 2.

**Canonical content:** One representative heap mutation from fetch/latch choice through page validation, mutation, logging, page LSA, dirtying, and release; short B-tree contrast for restart/promotion without teaching those internals; allocation knowledge versus `NEW_PAGE`; page latch versus transaction lock.

**Source exercise:** Trace the representative heap caller end to end, including every error exit. Label Module guarantees and caller obligations separately.

**Understanding evidence:** Two-column contract ledger showing what the Module provides and what the caller completes.

**Navigation:** Previous is page 2. Next is `04-flush-one-generation.md`. Related advanced pages are `advanced/acquisition-concurrency.md` and `advanced/recovery-and-lifecycle.md`.

### 4. `learning/04-flush-one-generation.md` — Flush One Generation: WAL, DWB, and Concurrent Re-dirty

**Maintainer question:** How does one dirty generation cross the WAL and page-write boundaries safely?

**Prerequisite:** Page 3.

**Canonical content:** Write permission versus recoverability versus propagation; page LSA and `oldest_unflush_lsa`; stable snapshot; DIRTY/FLUSHING split; WAL gate; TDE/DWB/direct-write boundary; concurrent re-dirty; ordinary success and rollback requirements. Runtime evidence appears only as bounded cards.

**Source exercise:** Trace snapshot, WAL force, write submission, completion, concurrent re-dirty, and ordinary failure rollback.

**Understanding evidence:** Generation timeline that explains why successful old-generation completion may leave the resident BCB dirty.

**Navigation:** Previous is page 3. Next is `05-replace-one-frame.md`. Related evidence is the uncertainty registry; related advanced material is `advanced/recovery-and-lifecycle.md`.

### 5. `learning/05-replace-one-frame.md` — Replace One Frame: Eligibility Before Policy

**Maintainer question:** When may a frame be reused, and which decisions are merely policy?

**Prerequisite:** Pages 2 and 4.

**Canonical content:** Hard victim predicates; final identity and ownership revalidation; clean/not-flushing requirement; eligibility versus LRU placement and quota policy; revocable direct-victim assignment at a conceptual level; victimization versus invalidation versus logical deallocation.

**Source exercise:** Trace one candidate through eligibility and final recheck, then identify which later choices could change without weakening caller ownership.

**Understanding evidence:** Predicate-versus-policy table and one counterexample showing why `fcnt == 0` alone is insufficient.

**Navigation:** Previous is page 4. Next is `06-maintainer-capstone.md`. Advanced continuation is `advanced/replacement-progress.md`.

### 6. `learning/06-maintainer-capstone.md` — Maintainer Capstone: Defend a Safe Change

**Maintainer question:** Can the reader connect interface behavior, state ownership, invariants, callers, failure cleanup, and verification?

**Prerequisite:** Pages 1–5.

**Canonical content:** Change-impact template; two review packets; review rubric; transition into the applied path.

**Source exercise:** Complete either the `VS-11` ownership packet or the `VS-12` durability packet while preserving its candidate status. The artifact must state behavior, owners, state, guards, invariants, unwind, caller impact, test seam, and remaining uncertainty.

**Understanding evidence:** Reviewed change-impact plan. Completing both packets prepares the reader for advanced work.

**Navigation:** Previous is page 5. Next choices are the applied path, a relevant playbook, or the advanced route.

## Maintainer playbooks

### `playbooks/change-safely.md` — Change the Module Safely

**Purpose:** Turn an issue or proposed diff into an interface statement, ownership map, invariant set, caller audit, negative-path review, and evidence plan.

**Prerequisites:** Pages 1 and 2 for meaningful use; the guide entry may still route urgent readers here.

**Canonical content:** The current eight-step change workflow; early-return resource ledger; contract-versus-policy test; caller-family routing; legacy indentation warning; change-description evidence trail; close-out questions.

**Links:** `reference/invariant-index.md`, `reference/source-map.md`, `verify-a-change.md`, and the canonical learning page for each touched concept.

### `playbooks/debug-by-symptom.md` — Diagnose Page-buffer Symptoms

**Purpose:** Route an observed symptom to the correct wait class, state owner, source region, evidence boundary, and next probe.

**Prerequisites:** None for routing; canonical explanations are linked for interpretation.

**Canonical content:** Fix/holder leak; latch or load wait; residency corruption; no victim; persistent dirty state; WAL/DWB/flush failure; stale ordered-access pointer; misleading SHOW/statistics output.

**Links:** `reference/source-map.md`, relevant core or advanced pages, `verify-a-change.md`, and `unresolved-or-version-sensitive-findings.md` IDs where applicable.

### `playbooks/verify-a-change.md` — Verify at the Risk Boundary

**Purpose:** Select the weakest sufficient evidence that actually exercises the risk: compile/focused unit, representative caller, concurrency, fault injection, controlled pressure, or crash/recovery.

**Prerequisites:** The interface behavior and risk must already be stated.

**Canonical content:** Risk-to-test matrix; standard CMake, `ctest`, and project-provided test concepts; controlled configuration; instrumentation limits; runtime-evidence card template; untested-boundary disclosure.

**Links:** `change-safely.md`, `source-inventory.md`, the uncertainty registry, and advanced proof-obligation material.

## Advanced path

### `advanced/acquisition-concurrency.md` — Acquisition Concurrency and Multi-page Ownership

**Prerequisite:** Learning page 2.

**Purpose:** Explain lock-free READ hits, memory-ordering dependence, VPID-keyed load serialization, latch queues, blocking promotion, ordered watchers, release/reorder/refix, and stale-observation revalidation.

**Core invariant extended:** Identity revalidation, ownership debt, positive-`fcnt` reuse exclusion, and borrowed-pointer lifetime.

### `advanced/replacement-progress.md` — Replacement Policy and Background Progress

**Prerequisites:** Learning pages 4 and 5.

**Purpose:** Explain private/shared LRUs, zones, quotas, candidate queues, direct victims, flush/post-flush coordination, and the disabled AOUT caveat without elevating policy to contract.

**Core invariant extended:** Eligibility remains correctness while selection and progress mechanisms remain policy.

### `advanced/recovery-and-lifecycle.md` — Recovery, Allocation State, and Module Lifecycle

**Prerequisites:** Learning pages 3 and 4.

**Purpose:** Explain checkpoint boundaries, recovery fetch and page-LSA idempotence, initialization/finalization ordering, invalidation versus deallocation, temporary modes, and boot/shutdown dependency order.

**Core invariant extended:** Caller completion, WAL ordering, identity lifetime, and recovery idempotence.

### `advanced/specialized-interfaces.md` — Specialized Interfaces and Approximate Observability

**Prerequisites:** Learning pages 1 and 2.

**Purpose:** Route simple fix, scan-copy, area-copy, diagnostics, SHOW, statistics, daemon hooks, and other narrow owner protocols. It does not reproduce the complete API inventory.

**Core invariant extended:** Specialized interfaces stay inside their owner protocols; approximate snapshots do not authorize correctness decisions.

### `advanced/failure-and-proof-obligations.md` — Failure Unwind and Open Proof Obligations

**Prerequisite:** All core pages. Relevant advanced mechanism pages are prerequisites for their own cases.

**Purpose:** Teach how to analyze source-visible exceptional paths without turning them into defect claims. It indexes `VS-*` entries, names the required fault or schedule, and links to the sole current status in the uncertainty registry.

**Core invariant extended:** Every acquired resource and state transition has an explicit success, retry, and failure argument.

## Compact references

### `reference/source-map.md` — Source and Caller Map

**Purpose:** Own broad `page_buffer.h/.c` regions, representative heap/B-tree/file/log/recovery/boot callers, interface-family routing, and symptom-to-source lookup.

**Boundary:** It provides navigation, not mechanism explanations. Learning and advanced pages own bounded traces; the complete API inventory remains external evidence.

### `reference/invariant-index.md` — Maintainer Invariant Index

**Purpose:** Provide stable invariant names, one-sentence statements, and links to canonical explanations, playbooks, and verification risks.

**Boundary:** It does not reproduce the full argument or source trace behind an invariant.

### Existing evidence references

[`source-inventory.md`](../../code-analysis/page-buffer-presentation/source-inventory.md) remains the provenance, reconciliation, evidence-routing, and coverage authority. [`unresolved-or-version-sensitive-findings.md`](../../code-analysis/page-buffer-presentation/unresolved-or-version-sensitive-findings.md) remains the sole status registry for hazards, candidates, inference, historical findings, and open questions.

## Evidence contract

The guide entry defines six labels: Interface contract, Verified mechanism, Implementation policy, Inference, Runtime observation, and Historical evidence. Their canonical definitions remain in [`CONTEXT.md`](../../code-analysis/page-buffer-presentation/CONTEXT.md).

Evidence placement follows these rules:

- each page identifies the pinned baseline and the labels it uses;
- implementation-specific claims carry nearby exact source anchors;
- broad line-range catalogs live only in `reference/source-map.md`;
- provenance and conflict resolution live only in `source-inventory.md`;
- changing hazard status occurs only in the uncertainty registry;
- runtime cards state revision/build/workload, observation, supported conclusion, unsupported conclusion, and receipt;
- historical counts appear only when the number itself teaches an evidence boundary;
- PostgreSQL and InnoDB appear only as brief, late contrast callouts linked to existing comparison evidence.

## Visual architecture

The core path uses six visuals. Each visual shows one relationship that would be materially harder to understand from prose or a short table.

| Final asset | Canonical page | Action from current assets |
|---|---|---|
| `assets/object-ownership-map.svg` | Learning page 1 | Replace and simplify `pool-map.svg`; use English labels |
| `assets/state-axes.svg` | Learning page 1 | Redraw in English using the confirmed evidence vocabulary |
| `assets/fix-contract.svg` | Learning page 2 | Retain the conceptual design after wording and evidence review |
| `assets/ownership-ledgers.svg` | Learning page 2 | Create a new global-`fcnt` versus thread-holder debt visual |
| `assets/durability-chain.svg` | Learning page 4 | Retain the responsibility lanes and integrate the useful concurrent re-dirty generation from `wal-flush.svg` |
| `assets/victim-eligibility.svg` | Learning page 5 | Create a new hard-predicate gate before replaceable policy choices |

`latch-state.svg`, `pool-map.svg`, and `wal-flush.svg` are removed after their useful content has a canonical owner. An English latch-transition SVG may be retained only if `advanced/acquisition-concurrency.md` demonstrably needs it.

All displayed assets live in the root `assets/` directory. The guide entry references `./assets/<name>.svg`; pages one directory below reference `../assets/<name>.svg`. The asset checker must validate the resolved asset directory instead of requiring the literal `./assets/` prefix. Every asset needs a `viewBox`, inactive content, non-color-only meaning, meaningful alt text, and explanatory surrounding prose.

## Migration map from the monolith

| Current section | Canonical destination | Treatment |
|---|---|---|
| Opening description and Contents | Guide entry | Rewrite as audience, outcomes, baseline, and route selection; remove the 14-section monolith TOC |
| 1. Start here | Learning page 1; guide entry evidence legend | Rewrite the successful-fix contract around the target reader; move evidence vocabulary to the entry |
| 2. Module, Interface, and seams | Learning page 1; change playbook; source map | Condense Module boundary into page 1; move owner/seam audit to the playbook; move interface-family catalog to the source map |
| 3. Source-tree orientation | Learning exercises; source map | Remove the standalone file-order lesson; distribute bounded traces and move broad ranges/caller catalogs to the source map |
| 4. Core object and state model | Learning page 1 | Rewrite as the first page-journey model before source topology; replace Korean visuals |
| 5. Acquisition Interface | Learning page 2; advanced acquisition | Keep normal caller choices and convergence in core; move fast-path and unusual protocol detail to advanced material |
| 6. Ownership and concurrency | Learning page 2; advanced acquisition | Keep ledgers, debt, and pointer lifetime in core; move promotion, queue behavior, and ordered access to advanced material |
| 7. Mutation, durability, and replacement | Learning pages 3, 4, and 5 | Split the overloaded section into caller mutation, generation flush, and frame replacement; remove repeated definitions |
| 8. Maintainer invariants | Canonical learning pages; invariant index | Introduce each invariant where first needed; keep only one-sentence indexed reminders in the reference |
| 9. How to change safely | `playbooks/change-safely.md` | Consolidate the complete change workflow and remove its duplicates elsewhere |
| 10. Debugging playbooks | `playbooks/debug-by-symptom.md` | Preserve symptom routing, replace repeated explanations with canonical links |
| 11. Verification strategy | `playbooks/verify-a-change.md`; evidence cards | Preserve the risk ladder; move experiment claims into bounded evidence cards or source inventory links |
| 12. Known hazards and evidence boundaries | Advanced failure page; uncertainty registry | Delete the copied status summary; retain only routing and proof-method teaching |
| 13. First-week maintainer path | Learning-page exercises; capstone; guide-entry duration | Remove calendar/day framing; integrate each exercise where its prerequisite is taught |
| 14. Compact glossary | Learning page 1; `CONTEXT.md` | Teach page-buffer objects in context; keep authoring vocabulary in `CONTEXT.md`; do not maintain a duplicate general glossary |
| 14. Deep references | Guide entry; source map | Replace the flat list with intent-based routing |
| 14. Symptom-to-source index | Debug playbook; source map | Keep one canonical source-routing table and link to it from the playbook |
| 14. Before you close an issue | Change and verification playbooks; capstone rubric | Consolidate into the change-impact and evidence workflow |

The migration removes repeated prose, not source-backed knowledge. Specialized mechanisms move to advanced pages; exhaustive catalogs and receipts remain in evidence documents; retired wording remains recoverable from Git history rather than a parallel legacy file.

## Content to condense, rewrite, or remove

### Condense

- repeated successful-fix postconditions;
- repeated ownership-debt and pointer-lifetime warnings;
- repeated revision/evidence cautions;
- repeated source maps and caller lists;
- repeated verification and close-out checklists.

### Rewrite

- the opening around observable maintainer outcomes;
- the object model before the pool topology;
- acquisition around one normal trace before fast paths;
- caller responsibility around one end-to-end heap mutation;
- durability around one copied generation and concurrent re-dirty;
- replacement around a hard eligibility gate before policy;
- all displayed SVG text in English;
- all navigation around reader intent rather than section number.

### Remove from the core route

- presentation timing, speaker or course framing, and first-week day labels;
- exhaustive interface and source-region catalogs;
- internal quota formulas and daemon cadence;
- copied hazard status summaries;
- full historical experiment number lists;
- dedicated cross-database comparison chapters;
- duplicate glossaries and duplicate model explanations.

## Understanding and applied evidence

Each core page uses one Predict–Locate–Explain exercise with an adjacent model answer. Answers explain the evidence boundary rather than only naming a symbol.

Core completion is source-based and does not require a prepared runtime environment. The applied path requires one controlled caller regression or narrow runtime probe on the maintainer’s target revision. Concurrency, pressure, fault-injection, and crash experiments become mandatory only when the maintained behavior or claim crosses those boundaries. Historical counts are never expected oracles.

The capstone offers two review packets:

- ownership cleanup around `VS-11`;
- durability cleanup around `VS-12`.

The packet must preserve candidate status and identify what evidence would be needed to establish reachability and impact.

## Implementation sequence for `/to-spec`

The specification should preserve these dependency edges:

1. **Update the document contract.** Reconcile `AGENTS.md` and `maintainer-guide-notes.md` with English-only authoring, the document-set paths, root asset ownership, and document-set validation.
2. **Deepen validation seams.** Extend the asset checker to discover the whole document set and add deterministic relative-link validation before content migration.
3. **Create all page skeletons and navigation.** Establish paths, headers, prerequisites, previous/next links, and canonical owners together so migration never creates competing destinations.
4. **Write core pages and core SVGs.** Work in page-journey order because each later page depends on earlier vocabulary.
5. **Write compact references and playbooks.** These may link to stable core anchors once the core exists.
6. **Write advanced pages.** Preserve the core/advanced boundary and route exhaustive evidence outward.
7. **Replace the monolith with the guide entry.** Do this only after every migrated section has a canonical destination.
8. **Remove unused assets and duplicated content.** Use the migration map and an asset-usage audit.
9. **Run the full verification and coverage audit.** Syntax, links, rendering, evidence labels, learning outcomes, and migration completeness must all pass.

This sequence should become tracer-bullet tickets with explicit blocking edges rather than one ticket per directory.

## Required verification after implementation

The specification must make these gates executable and unambiguous:

1. Run the asset checker across `page-buffer-teaching-material.md`, `learning/*.md`, `playbooks/*.md`, `advanced/*.md`, and `reference/*.md`.
2. Run the Copyparty Markdown checker against every changed document-set Markdown file.
3. Resolve every changed relative link, including links to evidence outside this directory.
4. Require every displayed SVG to resolve inside the root `assets/` directory, contain a `viewBox`, and contain no active content.
5. Require every SVG in `assets/` to be displayed by at least one document-set page.
6. Search the authored document set and SVG text for unintended Korean prose.
7. Request every page and displayed SVG through the local Copyparty server.
8. When browser automation is available, inspect the rendered DOM and require every image to have nonzero natural dimensions and no render error.
9. Audit every current monolith section against the migration map: each item must be moved, condensed, rewritten, or deliberately removed.
10. Audit the final pages against audience assumptions, core and advanced outcomes, page prerequisites, evidence labels, canonical ownership, visual plan, and Predict–Locate–Explain checks.

The existing single-file command in `AGENTS.md` is insufficient for this architecture and must be replaced by document-set-aware commands during implementation.

## Non-goals

- Describing a revision other than `f799e05d77d5300c6ea5753b4a6cc7caee6d8912` without revalidation.
- Translating the document set into Korean.
- Reproducing the complete API inventory, raw runtime receipts, or historical question banks.
- Proving unresolved production defects from source-visible candidates.
- Teaching heap, B-tree, logging, DWB, or recovery as independent subsystems.
- Presenting personal `justfile` commands as CUBRID organization workflow.
- Editing the separate live teaching-course and evidence trees during this redesign.
