# Redesign the CUBRID Page Buffer Maintainer Guide

Status: ready-for-agent

## Problem Statement

Senior systems engineers who are new to CUBRID need to understand and safely maintain the page-buffer Module, but the current guide makes that harder than necessary. Its 1,059 lines combine conceptual onboarding, source navigation, maintenance workflow, symptom diagnosis, verification strategy, known hazards, first-week exercises, and reference material in one surface. Readers encounter dense terminology, broad source ranges, and object topology before they complete one concrete page journey. Core concepts such as ownership debt, pointer lifetime, evidence boundaries, source routing, and verification are repeated without one canonical explanation, while mutation, durability, and replacement are coupled in a single chapter despite being independent state dimensions.

The source-backed content is valuable and must not be discarded. The problem is its information architecture: linear learning, issue-time lookup, advanced mechanisms, and evidence catalogs have different prerequisites and reading modes, yet currently compete in one document. The redesign must preserve the pinned evidence and every useful maintainer obligation while making the reader journey progressive, task-oriented, source-traceable, and verifiable.

## Solution

Replace the monolith with an English document set organized around three reader intents: learn the Module, work on a change, and diagnose a symptom. Preserve the existing guide filename as a stable guide entry. Give each concept one canonical explanation, route operational material through maintainer playbooks, isolate advanced mechanisms behind explicit prerequisites, and retain exhaustive provenance and uncertainty in the existing evidence references.

The target maintainer is a senior C/C++ systems engineer who understands basic database storage, buffer pools, and WAL but has no assumed knowledge of CUBRID source structure or page-buffer protocols. The learning path follows one page journey from caller intent through acquisition, use or mutation, release, generation flush, victim eligibility, and frame reuse.

### Deliverable topology

| Path | Title and role | Prerequisite | Required navigation |
|---|---|---|---|
| `page-buffer-teaching-material.md` | **CUBRID Page Buffer Maintainer Guide** — stable guide entry and route selector | Target-reader baseline | Learn, change, diagnose, verify, source lookup, evidence status, advanced route |
| `learning/01-contract-and-objects.md` | **Contract and Objects: What a Fix Actually Gives You** | Target-reader baseline | Entry, next core page, source map, invariant index |
| `learning/02-fix-hold-release.md` | **Fix, Hold, and Release: Borrowing a Resident Page** | Core page 1 | Previous/next, acquisition advanced page |
| `learning/03-caller-completes-correctness.md` | **Caller Completes Correctness: From Access to Logged Mutation** | Core page 2 | Previous/next, acquisition and recovery advanced pages |
| `learning/04-flush-one-generation.md` | **Flush One Generation: WAL, DWB, and Concurrent Re-dirty** | Core page 3 | Previous/next, uncertainty registry, recovery advanced page |
| `learning/05-replace-one-frame.md` | **Replace One Frame: Eligibility Before Policy** | Core pages 2 and 4 | Previous/next, replacement advanced page |
| `learning/06-maintainer-capstone.md` | **Maintainer Capstone: Defend a Safe Change** | Core pages 1–5 | Previous, applied path, playbooks, advanced route |
| `playbooks/change-safely.md` | **Change the Module Safely** | Core pages 1 and 2 for interpretation | Invariant index, source map, verification playbook, canonical concept pages |
| `playbooks/debug-by-symptom.md` | **Diagnose Page-buffer Symptoms** | None for routing | Source map, canonical concept pages, verification playbook, uncertainty IDs |
| `playbooks/verify-a-change.md` | **Verify at the Risk Boundary** | A stated behavior and risk | Change playbook, evidence references, uncertainty registry, proof-obligation page |
| `advanced/acquisition-concurrency.md` | **Acquisition Concurrency and Multi-page Ownership** | Core page 2 | Core invariants and relevant evidence |
| `advanced/replacement-progress.md` | **Replacement Policy and Background Progress** | Core pages 4 and 5 | Core eligibility explanation and relevant evidence |
| `advanced/recovery-and-lifecycle.md` | **Recovery, Allocation State, and Module Lifecycle** | Core pages 3 and 4 | Core caller/durability explanations and relevant evidence |
| `advanced/specialized-interfaces.md` | **Specialized Interfaces and Approximate Observability** | Core pages 1 and 2 | Interface-family routing and complete external inventory |
| `advanced/failure-and-proof-obligations.md` | **Failure Unwind and Open Proof Obligations** | All core pages plus mechanism-specific advanced prerequisites | Uncertainty IDs, verification playbook, canonical mechanisms |
| `reference/source-map.md` | **Source and Caller Map** | None | Bounded learning traces, playbooks, external API inventory |
| `reference/invariant-index.md` | **Maintainer Invariant Index** | None | Canonical explanations, playbooks, verification risks |

The existing `source-inventory.md` remains the provenance, reconciliation, coverage, and evidence-routing authority. The existing `unresolved-or-version-sensitive-findings.md` remains the sole status registry for hazards, candidates, inference, historical findings, and open questions.

### Core page responsibilities

1. **Contract and Objects** owns the Module boundary, caller/dependency seams, `VPID`, BCB, frame, `PAGE_PTR`, global `fcnt`, holder, borrowed lifetime, the four independent state axes, and the conceptual successful-fix postcondition. Its understanding evidence is an object/lifetime sketch and a distinction among fixed, resident, dirty, durable, flushed, evicted, and deallocated.
2. **Fix, Hold, and Release** owns fetch intent, latch mode versus wait condition, normal hit, miss convergence, expected non-acquisition, latch grant, the global and per-thread ledgers, nested ownership, release variants, and pointer lifetime. Lock-free internals, promotion, and ordered watchers are named and linked rather than taught here. Its understanding evidence is an annotated call path and debt ledger.
3. **Caller Completes Correctness** owns one representative heap mutation from fetch/latch choice through page validation, mutation, logging, page LSA, dirtying, release, and every error exit. It includes a short B-tree contrast, allocation knowledge versus `NEW_PAGE`, and page latch versus transaction lock. Its understanding evidence is a two-column Module-versus-caller contract ledger.
4. **Flush One Generation** owns write permission versus recoverability versus propagation, page LSA, `oldest_unflush_lsa`, stable snapshots, DIRTY/FLUSHING separation, the WAL gate, TDE/DWB/direct-write boundaries, concurrent re-dirty, ordinary success, and rollback. Its understanding evidence is a generation timeline explaining why an old-generation flush may finish while the resident BCB remains dirty.
5. **Replace One Frame** owns the hard victim predicates, final identity and ownership revalidation, clean/not-flushing requirements, eligibility versus selection policy, conceptual direct-victim revocation, and the distinction among victimization, invalidation, and logical deallocation. Its understanding evidence is a predicate-versus-policy table and a counterexample showing why `fcnt == 0` is insufficient.
6. **Maintainer Capstone** owns the change-impact template, review rubric, applied-path handoff, and two source-grounded review packets. The reader completes either the `VS-11` ownership packet or the `VS-12` durability packet while preserving candidate status and documenting behavior, owners, state, guards, invariants, unwind, caller impact, test seam, and remaining uncertainty.

### Playbook responsibilities

1. **Change the Module Safely** consolidates the interface statement, owner and seam map, invariant selection, acquisition-before-early-return audit, representative caller audit, contract-versus-policy split, CUBRID source-formatting constraints, negative paths, evidence trail, and close-out questions.
2. **Diagnose Page-buffer Symptoms** routes fix/holder leaks, latch or load waits, residency corruption, victim pressure, persistent dirty state, WAL/DWB/flush failures, stale ordered-access pointers, and misleading SHOW/statistics output to the correct state owner, source region, evidence boundary, and next probe.
3. **Verify at the Risk Boundary** owns the risk-to-test matrix spanning compile/focused unit evidence, representative caller regression, concurrency, fault injection, controlled pressure, and crash/recovery. It uses standard CMake, `ctest`, and project-provided test concepts and requires configuration, instrumentation, and untested-boundary disclosure.

### Advanced page responsibilities

1. **Acquisition Concurrency and Multi-page Ownership** extends identity revalidation, ownership debt, positive-`fcnt` reuse exclusion, and borrowed-pointer lifetime through lock-free READ hits, memory ordering, VPID-keyed load serialization, latch queues, blocking promotion, ordered watchers, release/reorder/refix, and stale-observation revalidation.
2. **Replacement Policy and Background Progress** extends eligibility-versus-policy reasoning through private/shared LRUs, zones, quotas, candidate queues, direct victims, flush/post-flush coordination, daemons, and the disabled AOUT caveat.
3. **Recovery, Allocation State, and Module Lifecycle** extends caller completion, WAL ordering, identity lifetime, and recovery idempotence through checkpoint boundaries, recovery fetch, page-LSA gates, initialization/finalization, invalidation/deallocation, temporary modes, and boot/shutdown ordering.
4. **Specialized Interfaces and Approximate Observability** routes simple fix, scan-copy, area-copy, diagnostics, SHOW, statistics, daemon hooks, and other narrow owner protocols without reproducing the complete API inventory. It teaches that approximate snapshots do not authorize correctness decisions.
5. **Failure Unwind and Open Proof Obligations** teaches how to analyze source-visible exceptional paths without upgrading them into defect claims. It indexes `VS-*` entries, names the fault or schedule required for each, and links to the sole current status in the uncertainty registry.

### Migration dispositions

| Current monolith content | Destination | Disposition |
|---|---|---|
| Opening description and Contents | Guide entry | Rewrite around audience, outcomes, baseline, and route selection; remove the 14-section monolith table of contents |
| Start here | Core page 1 and guide-entry evidence legend | Rewrite the successful-fix contract around the target maintainer; move evidence vocabulary to the entry |
| Module, Interface, and seams | Core page 1, change playbook, source map | Condense the boundary model; move owner/seam audit to the playbook and interface-family catalog to the source map |
| Source-tree orientation | Learning exercises and source map | Remove the standalone file-order lesson; distribute bounded traces and move broad source ranges/caller catalogs to the source map |
| Core object and state model | Core page 1 | Put the six-object model before pool topology and replace Korean visuals |
| Acquisition Interface | Core page 2 and advanced acquisition | Keep normal choices and convergence in core; move fast-path and unusual protocol detail to advanced material |
| Ownership and concurrency | Core page 2 and advanced acquisition | Keep ledgers, debt, and pointer lifetime in core; move promotion, queue behavior, and ordered access to advanced material |
| Mutation, durability, and replacement | Core pages 3, 4, and 5 | Split caller mutation, generation flush, and frame replacement; remove repeated definitions |
| Maintainer invariants | Canonical learning pages and invariant index | Introduce each invariant where first needed; keep one-sentence indexed reminders only |
| How to change safely | Change playbook | Consolidate the complete workflow and remove duplicates elsewhere |
| Debugging playbooks | Debug playbook | Preserve symptom routing and replace repeated explanations with canonical links |
| Verification strategy | Verification playbook and evidence cards | Preserve the risk ladder; move experiment claims into bounded cards or evidence-reference links |
| Known hazards and evidence boundaries | Failure/proof page and uncertainty registry | Remove the copied status summary; retain routing and proof-method teaching |
| First-week maintainer path | Learning exercises, capstone, and guide-entry duration | Remove calendar/day framing; integrate exercises where prerequisite knowledge is taught |
| Compact glossary | Core page 1 and domain glossary | Teach page-buffer objects in context and avoid a duplicate general glossary |
| Deep references | Guide entry and source map | Replace the flat list with intent-based routing |
| Symptom-to-source index | Debug playbook and source map | Keep one canonical source-routing table |
| Before you close an issue | Change/verification playbooks and capstone rubric | Consolidate into change-impact and evidence workflows |

Repeated successful-fix postconditions, ownership-debt warnings, pointer-lifetime warnings, revision cautions, source maps, caller lists, verification checklists, and close-out checklists are condensed into their canonical owners. The opening, object order, normal acquisition trace, representative caller, generation model, replacement gate, displayed SVG text, and navigation are rewritten. Presentation timing, speaker/course framing, day labels, exhaustive catalogs, quota formulas, daemon cadence, copied hazard statuses, full historical count lists, dedicated cross-database chapters, duplicate glossaries, and duplicate explanations leave the core route. Retired wording remains recoverable from Git history; no parallel legacy monolith is retained.

### Visual deliverables

| Final asset | Canonical owner | Required treatment |
|---|---|---|
| `assets/object-ownership-map.svg` | Core page 1 | Replace and simplify the current pool map with English labels |
| `assets/state-axes.svg` | Core page 1 | Redraw in English using confirmed vocabulary |
| `assets/fix-contract.svg` | Core page 2 | Retain conceptual design after wording and evidence review |
| `assets/ownership-ledgers.svg` | Core page 2 | Create a global-`fcnt` versus thread-holder debt visual |
| `assets/durability-chain.svg` | Core page 4 | Retain responsibility lanes and integrate concurrent re-dirty generation |
| `assets/victim-eligibility.svg` | Core page 5 | Create a hard-predicate gate before replaceable policy choices |

The current latch-state, pool-map, and WAL-flush assets are removed after their useful content has a canonical owner. An English latch-transition visual may remain only if the advanced acquisition page demonstrably needs it. All displayed SVGs live in the root asset directory; the guide entry uses a same-directory asset link and nested pages use a one-level parent link. Validation resolves the destination rather than enforcing one literal link prefix.

### Delivery dependencies

1. Update the page-buffer documentation contract before changing content. The contract must reflect English-only authoring, the document-set topology, root asset ownership, and document-set validation.
2. Deepen validation before migrating content. The asset checker must discover the whole document set, and deterministic relative-link validation must exist.
3. Create every page skeleton and all navigation before prose migration, establishing headers, prerequisites, previous/next links, and canonical owners without competing destinations.
4. Write the six core pages and six core visuals in page-journey order. Each later core page depends on the vocabulary and contracts introduced earlier.
5. Write the two compact references and three playbooks only after stable core anchors exist.
6. Write the five advanced pages after their listed core prerequisites and supporting references exist.
7. Replace the monolith with the guide entry only after every migrated section has a canonical destination.
8. Remove unused assets and duplicated content only after the migration and asset-usage audits prove they are unneeded.
9. Run the full document-set validation and coverage audit last. Completion depends on every syntax, link, rendering, evidence, learning, and migration gate passing.

These edges are mandatory inputs to `/to-tickets`; tickets must be tracer bullets with explicit blockers rather than one ticket per directory.

## User Stories

1. As a target maintainer, I want the guide to state what knowledge it assumes, so that I can identify prerequisites before beginning.
2. As a target maintainer, I want a stable guide entry, so that existing bookmarks lead to the redesigned material.
3. As a target maintainer, I want to choose between learning, changing, diagnosing, verifying, and source lookup, so that I can follow the route matching my immediate task.
4. As a target maintainer, I want a finite learning path, so that I know what core competence requires.
5. As a target maintainer, I want advanced material explicitly separated, so that specialized mechanisms do not overload the core journey.
6. As a core maintainer, I want observable completion outcomes, so that finishing pages is not mistaken for understanding.
7. As an advanced maintainer, I want prerequisite links for deep mechanisms, so that advanced explanations can rely on established vocabulary.
8. As a maintainer under time pressure, I want direct playbook routes, so that I do not reread onboarding material to act on an issue.
9. As a reader, I want every page to state its level, prerequisites, capability, baseline, and evidence, so that I can interpret it correctly in isolation.
10. As a reader, I want previous and next links on learning pages, so that the page journey remains obvious.
11. As a reader, I want related playbook and evidence links at the point of need, so that deeper lookup does not interrupt the core explanation.
12. As a reader, I want one canonical explanation per concept, so that repeated summaries cannot drift apart.
13. As a reader, I want the object model before the pool topology, so that diagrams use vocabulary I already understand.
14. As a core maintainer, I want to distinguish VPID, BCB, frame, PAGE_PTR, global fix count, and holder, so that I do not call different lifetimes “the page.”
15. As a core maintainer, I want to distinguish residency, ownership, concurrency, and durability, so that I do not collapse independent states.
16. As a core maintainer, I want to understand the successful-fix postcondition, so that I know what the Module guarantees.
17. As a core maintainer, I want to understand borrowed pointer lifetime, so that I do not use page-local observations after ownership ends.
18. As a core maintainer, I want one normal hit trace before fast-path details, so that optimization does not obscure the contract.
19. As a core maintainer, I want hit and miss paths shown converging, so that I separate preparation from caller-visible success.
20. As a core maintainer, I want expected non-acquisition distinguished from failure, so that conditional and specialized protocols remain correct.
21. As a core maintainer, I want global and per-thread ownership ledgers compared, so that nested debt and victim exclusion remain distinct.
22. As a core maintainer, I want release variants explained in one place, so that every successful acquisition receives one matching release.
23. As a core maintainer, I want one representative heap mutation traced end to end, so that I see what the caller must complete.
24. As a core maintainer, I want Module guarantees separated from caller obligations, so that fix success is not confused with page-type, logging, or durability correctness.
25. As a core maintainer, I want page latch distinguished from transaction lock, so that physical consistency and logical conflict are not conflated.
26. As a core maintainer, I want allocation knowledge distinguished from page-buffer materialization, so that `NEW_PAGE` is not treated as allocation.
27. As a core maintainer, I want write permission, recoverability, and propagation separated, so that dirty, commit, flush, and durability are not synonyms.
28. As a core maintainer, I want the two page-buffer LSA roles explained, so that checkpoint lower bounds and page-image recency remain distinct.
29. As a core maintainer, I want flush described as one copied generation, so that concurrent re-dirty behavior is understandable.
30. As a core maintainer, I want ordinary flush rollback obligations identified, so that early error returns can be reviewed safely.
31. As a core maintainer, I want DWB and direct-write completion boundaries labeled precisely, so that a flush event is not overclaimed as home-page persistence.
32. As a core maintainer, I want victim eligibility taught before selection policy, so that correctness predicates are not weakened during tuning.
33. As a core maintainer, I want frame reuse distinguished from invalidation and deallocation, so that cache and logical allocation actions remain separate.
34. As a core maintainer, I want a counterexample to `fcnt == 0` sufficiency, so that I remember the complete victim predicate.
35. As a core maintainer, I want a source-grounded capstone, so that I can demonstrate connected maintenance reasoning.
36. As a core maintainer, I want capstone candidates to retain their uncertainty status, so that review practice does not manufacture defect claims.
37. As a reviewer, I want a standard change-impact artifact, so that interface behavior, owners, invariants, unwind, caller impact, and evidence are all visible.
38. As a reviewer, I want another maintainer to review real change-impact plans, so that self-check exercises are not treated as production readiness.
39. As a maintainer changing code, I want one safe-change playbook, so that duplicated checklists cannot omit a negative path.
40. As a maintainer changing code, I want contract changes separated from policy changes, so that review and tests match the actual change.
41. As a maintainer changing code, I want every early return audited against already acquired state, so that failure unwind remains complete.
42. As a maintainer changing legacy source, I want CUBRID formatting constraints included, so that semantic work does not create indentation-only churn.
43. As a debugger, I want waits classified by resource and owner, so that latch, load, victim, flush, and transaction waits are not conflated.
44. As a debugger, I want symptom routing to link to canonical mechanisms, so that playbooks remain concise and accurate.
45. As a debugger, I want approximate metrics labeled, so that counters guide investigation without authorizing mutation or deallocation.
46. As a verifier, I want risk mapped to the weakest sufficient evidence, so that tests prove the changed behavior without unrelated cost.
47. As a verifier, I want concurrency claims to require controlled schedules, so that aggregate counters are not misused as concurrency proof.
48. As a verifier, I want cleanup claims to require fault injection when appropriate, so that source-visible branches are exercised at the owned state boundary.
49. As a verifier, I want replacement claims to require controlled pressure, so that a no-eviction trace cannot prove victim behavior.
50. As a verifier, I want durability claims to define crash and persistence boundaries, so that clean shutdown or backup evidence is not overextended.
51. As an advanced maintainer, I want lock-free acquisition taught after the normal contract, so that memory-order reasoning has a stable invariant base.
52. As an advanced maintainer, I want ordered release/reorder/refix explained with stale-observation rules, so that multi-page fixes remain safe.
53. As an advanced maintainer, I want replacement quotas and queues labeled as policy, so that version-sensitive mechanisms are not taught as interface guarantees.
54. As an advanced maintainer, I want AOUT’s analyzed default state stated, so that CUBRID is not inaccurately summarized as using 2Q.
55. As an advanced maintainer, I want checkpoint and redo tied to core LSA concepts, so that recovery is an extension rather than a disconnected chapter.
56. As an advanced maintainer, I want lifecycle ordering explained at dependency seams, so that initialization and finalization changes are reviewed end to end.
57. As an advanced maintainer, I want specialized interfaces grouped by owner protocol, so that narrow helpers are not promoted into general conveniences.
58. As an advanced maintainer, I want proof obligations linked to one status registry, so that current and historical findings cannot drift.
59. As an evidence-conscious reader, I want Interface contract distinguished from Verified mechanism, so that internal behavior is not mistaken for a stable promise.
60. As an evidence-conscious reader, I want Implementation policy distinguished from mechanism and invariant, so that tuning choices remain replaceable.
61. As an evidence-conscious reader, I want Inference clearly labeled, so that plausible explanations are not presented as guarantees.
62. As an evidence-conscious reader, I want Runtime observation tied to revision, build, configuration, and workload, so that lab events are not universalized.
63. As an evidence-conscious reader, I want Historical evidence clearly separated, so that old findings require revalidation.
64. As an evidence maintainer, I want broad source catalogs owned by one source map, so that line ranges have one update surface.
65. As an evidence maintainer, I want provenance and conflict resolution to remain in the source inventory, so that teaching pages stay readable.
66. As an evidence maintainer, I want hazard status changed only in the uncertainty registry, so that copied summaries cannot become stale.
67. As a reader, I want runtime cards to state what they do and do not prove, so that observations teach evidence boundaries.
68. As a reader, I want cross-database comparisons used only after CUBRID mechanisms, so that analogies do not replace local understanding.
69. As a visual learner, I want the object graph diagrammed, so that non-linear ownership and indexing relationships are clear.
70. As a visual learner, I want independent state axes diagrammed, so that coincident transitions are not collapsed.
71. As a visual learner, I want hit/miss convergence diagrammed, so that different preparation paths share one success contract.
72. As a visual learner, I want global and per-thread ledgers diagrammed, so that related accounting roles remain distinct.
73. As a visual learner, I want durability lanes and re-dirty timing diagrammed, so that ordering and generations are visible.
74. As a visual learner, I want victim eligibility before policy diagrammed, so that correctness gates precede tuning.
75. As an English reader, I want all authored prose and displayed visual text in English, so that language switching does not add cognitive load.
76. As a reader using Copyparty, I want every page, link, and visual to render correctly, so that navigation is dependable.
77. As a documentation maintainer, I want the entire document set validated through one discovery seam, so that newly added pages cannot escape checks.
78. As a documentation maintainer, I want every displayed SVG owned by the root asset directory, so that the guide remains self-contained.
79. As a documentation maintainer, I want unused SVGs rejected, so that retired visuals do not become stale evidence.
80. As a documentation maintainer, I want every migrated monolith section accounted for, so that restructuring does not silently lose source-backed knowledge.
81. As a documentation maintainer, I want links to external evidence resolved, so that deep references remain usable after the split.
82. As a documentation maintainer, I want the stable guide entry replaced only after destination pages exist, so that readers never encounter broken routes.
83. As a documentation maintainer, I want the old monolith retired rather than duplicated, so that content has one maintenance surface.
84. As a documentation maintainer, I want reader outcomes audited in addition to syntax, so that a technically valid document set is not mistaken for an effective guide.

## Implementation Decisions

- Author the complete redesigned document set in English. Korean translation is outside this implementation.
- Treat the pinned CUBRID revision `f799e05d77d5300c6ea5753b4a6cc7caee6d8912` as the authority for source claims. Revalidate symbols, control flow, callers, and anchors before describing another revision.
- Preserve the stable guide entry as a route selector rather than a compressed tutorial.
- Implement exactly six ordered core learning pages, three maintainer playbooks, five advanced pages, and two compact references. Existing evidence references retain their current authority.
- Organize the core around the page journey rather than source-file order.
- Keep the target maintainer, core maintainer, advanced maintainer, learning path, maintainer playbook, evidence reference, guide entry, canonical explanation, understanding check, capstone review, and applied path meanings aligned with the domain glossary.
- Give every page a reader contract containing level, prerequisites, one observable capability, source baseline, and evidence used.
- Give every learning page one Predict–Locate–Explain understanding check, an adjacent model answer, previous/next navigation, and related operational/evidence links.
- Make each concept’s mental model and representative source path canonical in one page. Playbooks provide decisions and actions; references provide routing and catalogs; neither reproduces the explanation.
- Define six evidence labels: Interface contract, Verified mechanism, Implementation policy, Inference, Runtime observation, and Historical evidence.
- Put exact source anchors beside implementation-specific claims. Keep broad source catalogs in the source map and provenance/conflict resolution in the source inventory.
- Keep the uncertainty registry as the sole mutable status authority for candidates, historical findings, and open questions. Other pages route by ID.
- Format runtime evidence as bounded cards containing revision/build/workload, observed event, supported conclusion, unsupported conclusion, and accepted receipt.
- Use historical numbers only when the number itself teaches an evidence boundary. Never use historical counts as test or performance oracles.
- Use PostgreSQL and InnoDB only as brief, late contrast callouts linked to existing comparison evidence. Do not add a dedicated core comparison page.
- Use visuals only for object relationships, independent axes, converging flows, dual ledgers, durability timing, and eligibility gates. Keep line numbers, large function catalogs, policy formulas, and paragraphs out of SVGs.
- Require English text, meaningful alt text, explanatory surrounding prose, a responsive view box, inactive content, and non-color-only meaning for every displayed SVG.
- Keep displayed SVGs in one root asset seam. Validate their resolved destination so nested pages can link back to the same assets without duplication.
- Consolidate the old monolith according to the migration table. Do not retain a parallel legacy copy.
- Preserve exhaustive API inventories, raw receipts, deep catalogs, and historical question banks as linked evidence rather than copying them into the redesigned pages.
- Preserve the separation between CUBRID Module guarantees and caller responsibilities at heap, B-tree, file, log, DWB, recovery, and lifecycle seams.
- Use standard CMake, `ctest`, and project-provided test concepts in organization-facing text. Personal convenience commands are not project workflow.
- Preserve existing CUBRID source indentation guidance in the safe-change playbook without changing engine source as part of this documentation work.
- Update the documentation contract and validation contract before content migration so future work follows the new English, multi-page rules.
- Establish every page skeleton, canonical owner, and navigation edge before moving prose.
- Implement core pages in prerequisite order, then references/playbooks, then advanced pages, then replace the monolith, then remove duplicates and unused assets.
- Preserve unrelated worktree changes and do not edit separate teaching-course or evidence trees.

## Testing Decisions

- The highest test seam is the complete maintainer-guide document set. One aggregate validation entry point must discover the guide entry, all learning pages, all playbooks, all advanced pages, and all compact references so a new page cannot silently escape checks.
- The aggregate seam may orchestrate focused subchecks, but page discovery must have one source of truth shared by asset, link, language, and Markdown validation.
- Extend the existing asset-validation prior art from one guide file to the complete document set. It must resolve image targets, require ownership by the root asset seam, require existence and `viewBox`, reject active content, and reject orphan SVGs.
- Add deterministic relative-link validation at the document-set seam. It must cover links among new pages and links to evidence outside the directory.
- Run the established Copyparty Markdown source checker against every changed document-set Markdown file.
- Scan authored Markdown and SVG text for unintended Korean prose. Canonical source identifiers and non-prose byte content are not failures.
- Request every guide page and displayed SVG through the local Copyparty server.
- When browser automation is available, inspect rendered DOM state and require every image to have nonzero natural dimensions and the page to contain no render error. When it is unavailable, report that gate as unavailable rather than claiming it passed.
- Verify each SVG’s accessibility contract: meaningful alt text, surrounding explanation, and meaning that does not depend on color alone.
- Audit all six final core visuals against their declared canonical pages and verify that retired assets have no remaining references before removal.
- Audit every monolith section against the migration table. Every item must be demonstrably moved, condensed, rewritten, or deliberately removed.
- Audit the final content against audience assumptions, core and advanced completion outcomes, exact page prerequisites, canonical ownership, evidence labels, runtime-card boundaries, visual roles, and Predict–Locate–Explain exercises.
- Good documentation tests assert reader-visible behavior: discoverable routes, resolved links, valid rendering, evidence labeling, canonical ownership, and preserved coverage. They do not pin incidental prose wrapping or internal script implementation.
- Use the existing single-file asset checker and Copyparty checker as prior art, deepening their seam instead of replacing them with unrelated validators.
- A documentation-only implementation does not require rebuilding the CUBRID engine. If implementation changes or strengthens a runtime/source claim, apply the verification playbook at that claim’s actual risk boundary.
- Core completion exercises remain source-based. The applied path requires one controlled caller regression or narrow runtime probe on the target revision; concurrency, pressure, fault-injection, and crash work becomes mandatory only for claims in those areas.
- Complete validation only after the guide entry replacement and asset cleanup, because earlier checks cannot prove final migration completeness or orphan absence.
- Inspect the final diff and preserve unrelated user changes.

## Out of Scope

- Describing a CUBRID revision other than `f799e05d77d5300c6ea5753b4a6cc7caee6d8912` without a separate revalidation effort.
- Translating the redesigned document set into Korean.
- Reproducing the complete API inventory, raw runtime receipts, exhaustive source catalogs, historical question banks, or full comparator internals.
- Establishing production defects from source-visible candidates or changing `VS-*` status without the required runtime or source proof.
- Teaching heap, B-tree, logging, DWB, file management, vacuum, checkpoint, or recovery as independent subsystems beyond the seams needed to complete page-buffer reasoning.
- Adding a dedicated PostgreSQL or InnoDB comparison chapter to the core route.
- Changing CUBRID engine behavior, source formatting, or tests as part of the documentation redesign.
- Presenting personal `justfile` commands as CUBRID organization workflow.
- Editing the separate live teaching-course, monitoring, report, or evidence trees.
- Preserving a second legacy copy of the monolithic guide.
- Tracking individual learner progress in the general maintainer guide.
- Treating self-completed exercises as sufficient evidence of production readiness.

## Further Notes

- The confirmed architecture is the authoritative design input: [`maintainer-guide-architecture.md`](../../code-analysis/page-buffer-presentation/maintainer-guide-architecture.md).
- Canonical terminology lives in [`CONTEXT.md`](../../code-analysis/page-buffer-presentation/CONTEXT.md).
- The reading-mode split and English-only decisions are recorded in the page-buffer documentation ADRs.
- The pinned evidence reconciliation and uncertainty registry remain authoritative and must be read before strengthening claims.
- The existing page-buffer directory instructions still describe Korean, single-file authoring. Updating those instructions and authoring notes is the first implementation dependency, not an optional cleanup.
- The current single-file asset command is not sufficient acceptance evidence for this specification.
- This specification is ready for `/to-tickets`. Ticket boundaries must follow tracer bullets and preserve the mandatory blocking edges in the Solution section.
