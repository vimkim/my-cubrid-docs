# Canonical CUBRID Page-buffer Question Bank

Status: ready-for-agent

## Problem Statement

The page-buffer maintainer guide now gives senior engineers a readable, source-traceable learning path, but it does not provide a first-class retrieval route. Each Core page contains one Understanding check, while the reusable question material remains fragmented across four corpora: a 38-question teaching bank, a 55-question adversarial bank with separate answers, a 24-question historical Korean workbook, and planned/executed quiz material. The current guide directory therefore cannot support systematic rehearsal, source-tracing review, or misconception-driven follow-up without sending readers into legacy trees with different structures, vocabularies, revisions, and evidence boundaries.

Copying those banks wholesale would create a second tutorial, duplicate canonical explanations, inherit invalid or incomplete anchors, mix `f799e05` with `e6ed61e`, expose answers during retrieval, import cross-database baselines, and leave the aggregate validator unaware of the new pages. The migration must instead select, deduplicate, revalidate, route, and account for every legacy item while preserving the original evidence trees and reader notes.

## Solution

Add a CUBRID-only Question bank as a fifth reader mode within the existing maintainer-guide directory. The bank is an Evidence reference for self-study retrieval and source tracing, not a scored exam or parallel learning path. It has one landing page and four routes—Core, Advanced, maintenance scenarios, and Applied exercises—with prompts and answers on companion pages joined by immutable `PGBUF-QB-*` identifiers.

Seed the canonical bank from the 38-question English teaching bank, merge distinct senior-maintainer coverage from the 55-question adversarial pair, revalidate useful historical workbook material against pinned CUBRID `f799e05`, and convert four executed quiz families into English documentation cards linked to their existing artifacts. Preserve raw Reader question intake unchanged and promote only source-validated questions. Exclude PostgreSQL/MySQL comparison questions from canonical routes.

Every source item receives a Question disposition. Aggregate validation discovers every Question-bank page and enforces reader-visible structure, prompt/answer pairing, controlled vocabulary, identifier integrity, disposition completeness, links, language, assets, Copyparty source compatibility, HTTP reachability, and available live-DOM behavior.

## Confirmed Domain and Decisions

- The Target maintainer, Core maintainer, Advanced maintainer, Question bank, Core retrieval question, Advanced retrieval question, Applied exercise, Canonical question, Canonical question ID, Retrieval mode, Reader question intake, and Question disposition meanings are owned by `code-analysis/page-buffer-presentation/CONTEXT.md`.
- `docs/adr/0003-separate-question-prompts-from-answers.md` owns the durable page/identifier architecture.
- Primary purpose: self-study retrieval, with searchable reference as a secondary use.
- Completion split: Core rehearsal is the expected route; Advanced and scenario routes are optional and task-selected.
- Migration means a complete disposition audit, not wholesale preservation.
- Scope is documentation only. Executable quiz infrastructure, scoring, and learner-progress tracking remain outside this effort.
- Explanatory prose is English; canonical CUBRID identifiers remain English.
- CUBRID source claims are pinned to `f799e05d77d5300c6ea5753b4a6cc7caee6d8912`.
- Coverage and nonduplication determine final question count. No numeric quota is a completion gate.

## Deliverable Topology

| Path | Title and role | Prerequisite | Required navigation |
|---|---|---|---|
| `questions/README.md` | **Page-buffer Question Bank** — route selector, use instructions, evidence boundary, and route index | Guide reader contract | Guide entry; all four prompt routes; all four answer routes; migration audit |
| `questions/core.md` | **Core Retrieval Prompts** — ordered rehearsal mapped to six Core pages | Relevant Core page before attempting its group | Companion answers; each Core page; entry; Advanced prompts |
| `questions/core-answers.md` | **Core Retrieval Answers** — evidence-aware answers paired by canonical ID | Attempt the corresponding prompt | Prompt anchor; canonical Core explanation; source/evidence reference |
| `questions/advanced.md` | **Advanced Retrieval Prompts** — optional mechanism and proof-boundary questions mapped to five Advanced pages | Declared Core and Advanced prerequisites per group | Companion answers; each Advanced page; scenario prompts |
| `questions/advanced-answers.md` | **Advanced Retrieval Answers** — pinned mechanism/policy/proof answers | Attempt the corresponding prompt | Prompt anchor; canonical Advanced explanation; registry/source references |
| `questions/maintenance-scenarios.md` | **Maintenance Scenario Prompts** — review, diagnosis, failure, and evidence-selection packets | Route-specific Core/Advanced prerequisites | Companion answers; three playbooks; uncertainty registry |
| `questions/maintenance-scenarios-answers.md` | **Maintenance Scenario Answers** — ledgers, decision paths, and proof boundaries | Attempt the corresponding scenario | Prompt anchor; relevant playbook; canonical explanation; registry IDs |
| `questions/applied-exercises.md` | **Applied Exercise Prompts** — four documentation cards derived from executed same-revision quiz families | Core page mapped by each card | Companion answers; exact external quiz/experiment artifacts; verification playbook |
| `questions/applied-exercises-answers.md` | **Applied Exercise Answers** — expected reasoning and bounded runtime interpretation | Attempt the corresponding exercise | Prompt anchor; accepted artifacts/receipts; canonical explanation |
| `questions/migration-audit.md` | **Question-bank Migration Audit** — complete legacy-to-canonical disposition ledger | None; authoring reference | Source banks; canonical destinations; Reader question intake |

The four prompt/answer pairs are reader-facing Question-bank routes. The migration audit is an Evidence reference for documentation maintainers. All ten pages are discovered by the aggregate validator.

## Reader-facing Page Contract

Every Question-bank page begins with:

- `Level`: Question bank plus route (`Core`, `Advanced`, `Maintenance scenarios`, `Applied exercises`, or `Migration reference`);
- prerequisites;
- one observable capability gained;
- full pinned source baseline;
- canonical evidence labels used;
- a link to the companion page or, for the landing/audit pages, their owned routes.

The landing page explains the retrieval loop: attempt without the answer page, inspect the named source regions, write the requested artifact, compare with the matching answer, and follow the canonical guide link when reasoning differs. It explicitly states that completing questions is not a score or production-readiness certification.

## Canonical Prompt Schema

Each prompt is one H3 heading and uses this exact field vocabulary:

```markdown
### PGBUF-QB-NNN — Question title

- **Route:** Core | Advanced | Maintenance scenario | Applied exercise
- **Retrieval mode:** Explain | Trace | Scenario | Proof obligation
- **Prerequisite:** linked guide page or stated route prerequisite
- **Capability tested:** one observable reader artifact
- **Inspect:** one or more exact pinned-source ranges or linked evidence artifacts

**Question:** Reader-facing prompt.
```

Rules:

- A Canonical question ID is unique, immutable, zero-padded, and never reused.
- Canonical order is editorial, not identity. Moving a question does not change its ID.
- No canonical ID may equal the legacy adversarial form `PGBUF-QNNN`.
- Prompt titles are concise and do not function as identity.
- `Inspect` is a lead, not an embedded answer. Source claims use exact `path:start-end` ranges; applied runtime prompts may link exact artifacts instead.
- The Capability tested field names a reviewable artifact such as an object map, call trace, debt ledger, state timeline, predicate table, exit audit, failure packet, or evidence card.
- Questions link to prerequisites but do not restate the canonical explanation.

## Canonical Answer Schema

Each answer uses the same H3 ID/title and this exact field vocabulary:

```markdown
### PGBUF-QB-NNN — Question title

- **Evidence:** one or more canonical evidence labels
- **Canonical guide:** links to the owning explanation or playbook
- **Source anchors:** exact pinned-source ranges and/or exact evidence artifacts
- **Confidence/limit:** what the answer establishes and what remains unproved

**Model answer:** Sufficient answer for evaluating the response.

**Why:** The governing invariant, decisive transition, ownership ledger, or evidence boundary.
```

Rules:

- Prompt and answer IDs/titles pair one-to-one within the same route.
- Answers remain visible and linkable; do not hide them in `<details>`.
- Answers are sufficient to evaluate reasoning but do not duplicate a complete tutorial. Link the Canonical explanation for full teaching.
- Use only Interface contract, Verified mechanism, Implementation policy, Inference, Runtime observation, and Historical evidence.
- Runtime answers name revision, build, configuration, workload, observation, supported conclusion, unsupported conclusion, and accepted receipt, either inline or through an exact linked evidence card.
- Candidate/historical questions route to `VS-*` status instead of copying mutable status prose.
- Historical `e6ed61e` or `5cd4f860e` material becomes current only after pinned-source revalidation; otherwise it remains Historical evidence or is excluded.

## Route Responsibilities

### Core retrieval

Organize prompts in the six Learning-page order. Cover the minimum distinct capability set:

1. object identity, BCB/frame/`PAGE_PTR`, borrowed lifetime, and independent state axes;
2. fetch intent, latch mode versus condition, hit/miss convergence, load ownership, VPID recheck, holder/`fcnt`, nested debt, and release;
3. caller-completed correctness, page latch versus transaction lock, `NEW_PAGE`, logged mutation, page LSA, dirtying, watcher transfer, and all-exit cleanup;
4. write permission versus recoverability versus propagation, dirty generations, WAL gate, DWB/direct boundary, re-dirty, and flush rollback;
5. victim safety predicates, eligibility versus policy, frame identity reuse, and distinctions among unfix, flush, invalidation, victimization, and deallocation;
6. change-impact and evidence-boundary synthesis.

Core questions favor Explain, Trace, and compact Scenario work. The Core, Advanced, and Maintenance-scenario routes collectively answer every source-validated concern recorded in `questions-b4179ee/questions.md` without editing that intake file.

### Advanced retrieval

Organize prompts by the five Advanced pages. Cover distinct material from the adversarial pair and revalidated historical workbook:

- lock-free READ hit, memory-order proof, VPID-keyed load serialization, promotion, queues, ordered release/reorder/refix, and stale-observation revalidation;
- private/shared LRUs, zones, quota, candidate queues, direct-victim handoff/revocation, post-flush generation checks, daemon ownership, and AOUT's pinned/default caveat;
- recovery fetch modes, page-LSA idempotence, checkpoint selectivity, allocation/deallocation ownership, bypass-write coherence, and lifecycle order;
- simple/scan-copy/area-copy interfaces, temporary-page protocols, metadata setters, SHOW/statistics, and approximate observations;
- source-visible exceptional paths, reachability, surviving state, impact, current status, required schedules, fault seams, and evidence promotion.

Policy remains labeled policy. Candidate and historical material links current status rather than restating it.

### Maintenance scenarios

Use task packets rather than explanation recall. Include scenarios for:

- changing an Interface or policy without losing callers;
- auditing a new early return and every acquired state ledger;
- diagnosing holder/fix debt, latch waits, duplicate residency, persistent DIRTY/FLUSHING, victim pressure, stale ordered-access observations, and misleading counters;
- choosing among regression, controlled schedule, fault injection, pressure, and crash/recovery seams;
- distinguishing source-visible control flow, reachability, surviving state, production impact, and target-branch status for `VS-10` through `VS-16` without asserting defects.

Scenario answers must produce a decision path or review artifact and route to playbooks/canonical explanations.

### Applied exercises

Create four prompt/answer documentation cards from the executed `FIELD/quiz/quiz-1` through `quiz-4` families:

1. cold miss versus warm reuse and counter limits;
2. holder/global fix accounting, conditional acquisition, and latch-versus-lock boundaries;
3. covered/non-covered caller paths, cleanup, ordered refix, and recovery LSA;
4. dirty generation, page/log LSAs, WAL, re-dirty, victim predicates, and runtime proof limits.

Each card links the existing `quiz.md`, `answer.md`, SQL, JSON, and accepted `rebind-quiz*` receipt where available. Do not copy shell runners, SQL, raw receipts, database setup, or personal paths into the guide. Organization-facing guidance uses standard CMake, `ctest`, and project-provided concepts only.

## Migration Sources and Complete Disposition Contract

`questions/migration-audit.md` contains one row per source item with:

| Field | Meaning |
|---|---|
| Source set | `TEACH`, `ADV`, `HIST`, `PLAN`, `EXEC`, `GRILL`, or `READER` |
| Legacy item | Stable legacy ID when present; otherwise an audit-assigned positional ID |
| Short topic | Enough wording to identify the original prompt |
| Disposition | Retained, Merged, Rewritten, Superseded, or Excluded |
| Canonical destination | `PGBUF-QB-*` or `—` |
| Rationale/evidence action | Deduplication, revalidation, historical boundary, out-of-scope reason, or executed descendant |

Required source populations:

| Source set | Authority | Required count |
|---|---|---:|
| `TEACH` | `../../pgbuf-analysis/teach-course/reference/pgbuf-question-bank.md` | 38 |
| `ADV` | `../../pgbuf-analysis/f799e05_claude/analysis/research/qa-questions.md` plus paired answers | 55 |
| `HIST` | `../../pgbuf-analysis/e6ed61e_claude/07-qa-workbook.md` | 24 |
| `PLAN` | lifecycle report `research/packets/experiments-and-quizzes.md` planned quiz prompts | 27 |
| `EXEC` | lifecycle report `quiz/quiz-{1,2,3,4}/{quiz,answer}.md` | 17 |
| `GRILL` | lifecycle report packet live-grill seed bank | 12 |
| `READER` | `questions-b4179ee/questions.md` | 16 |

The audit therefore accounts for 189 source items. If factual inspection proves a stated count wrong, correct the spec/audit together and document the evidence; do not fabricate or omit rows to satisfy the number.

Disposition rules:

- Retained: one source item maps substantially to one Canonical question after current formatting/evidence work.
- Merged: this item contributes to a Canonical question that also absorbs overlapping items.
- Rewritten: the distinct question survives but wording, task, or answer changes materially for the current route/evidence contract.
- Superseded: a later executed or stronger item replaces this source item.
- Excluded: outside CUBRID scope, duplicate without additional capability, unsupported on the pinned baseline, or unsuitable as a Canonical question; rationale is mandatory.
- All `PLAN` prompts with executed descendants identify those descendants; planned results never become Runtime observations.
- Cross-database questions are Excluded from canonical routes and link their existing comparison evidence in the rationale.
- The raw Reader question intake remains untouched and linked. Every `READER` row maps to a Canonical answer; overlapping reader wording may be Merged, but none is silently excluded.

## Navigation and Canonical Ownership

- Add Question bank to the Guide entry's intent table.
- Add one `Practice this route` link from each Learning page to the matching Core prompt fragment.
- Add one `Practice this route` link from each Advanced page to its Advanced prompt fragment.
- Route `change-safely.md`, `debug-by-symptom.md`, and `verify-a-change.md` to the relevant Maintenance-scenario fragments.
- The Question-bank landing page links the Guide entry, all prompt and answer pages, and migration audit.
- Prompt pages link companion answers without placing answer text on the prompt page.
- Answer pages link each prompt anchor and Canonical guide owner.
- Existing canonical explanations remain authoritative. Question answers evaluate and route; they do not become second tutorials.
- Existing evidence trees and `questions-b4179ee/` are read-only inputs and are not moved, rewritten, or deleted.

## Validation Contract

Extend the one aggregate entry point, `node scripts/check-maintainer-guide.mjs`, so its shared discovery seam includes every Markdown page recursively under `questions/` in addition to the existing Guide entry, Learning, playbook, Advanced, and reference pages.

All existing lower-level gates apply to Question-bank pages: Copyparty Markdown source compatibility, relative links and fragments, English prose, SVG ownership/orphan rules, Copyparty HTTP, and available live-DOM checks.

Add focused Question-bank structural validation and tests that prove:

1. exactly the approved ten Question-bank page paths exist;
2. every prompt has all required prompt fields and a recognized route/mode;
3. every answer has all required answer fields and at least one canonical evidence label;
4. canonical IDs match `PGBUF-QB-[0-9]{3}`, are globally unique on prompt pages, and are not legacy `PGBUF-Q[0-9]{3}` IDs;
5. each route's prompt/answer ID and title sets pair exactly one-to-one;
6. no canonical ID appears in more than one prompt route;
7. every canonical question has at least one migration-audit source row, except an explicitly identified new synthesis question whose audit row uses source set `NEW` if the implementation introduces one; prefer source-backed migration over unnecessary `NEW` items;
8. migration rows use controlled source/disposition values and nonempty rationale;
9. source populations equal the factually verified counts and every required legacy ID/position appears exactly once;
10. `questions-b4179ee/question-02.md` remains byte-for-byte unchanged;
11. the Guide entry, every Learning page, every Advanced page, and all three playbooks expose their required Question-bank navigation;
12. no Question-bank page contains Korean prose, cross-database Canonical questions, personal absolute paths, personal `justfile` workflow, `runtime proof`, or unsupported current-defect wording.

Semantic correctness of a cited range remains a source/spec review gate. Automated syntax cannot prove the meaning of source code.

## Source and Evidence Rules

- Verify implementation claims with `git show f799e05:<path>` or a clean matching worktree, not the current development checkout.
- Correct known teaching-bank anchor issues during migration: object/PAGE_PTR evidence, hit/miss convergence, ordered watcher mechanics, recovery page-LSA gate, `oldest_unflush_lsa`, TDE/DWB/WAL order, pressure behavior, and counter provenance.
- Use `source-inventory.md` for reconciled ranges, accepted receipts, and conflict resolution.
- Use `unresolved-or-version-sensitive-findings.md` as the sole mutable status source for `VS-*` material.
- Use exact repo-relative links for local evidence. Reader-facing files contain no `/home/...` paths.
- Cross-database content may appear only in migration rationales or links to existing evidence, never as a Canonical question.
- Existing no-eviction runtime evidence cannot establish replacement schedule, direct victims, fairness, or actual victimization.
- Existing backup/checkpoint observations cannot establish crash redo, per-page WAL-before-data completion, DWB recovery, torn-page protection, or home-page persistence.

## Delivery Dependencies

1. Record the confirmed domain and ADR before spec/tickets. Complete.
2. Extend the authoring/validation contract and add red aggregate/structure tests before adding Question-bank pages.
3. Create all ten page shells, reader contracts, navigation, and prompt/answer schema examples before content migration.
4. Migrate Core prompts/answers and their source dispositions first because every later route depends on Core vocabulary.
5. Migrate Advanced and Maintenance-scenario routes after Core anchors stabilize; they may proceed independently after that boundary.
6. Migrate Applied exercises after schema/navigation exist and exact executed artifacts/receipts have been inventoried.
7. Complete the 177-item migration audit only after all four routes have final canonical IDs; audit rows may be accumulated earlier, but completion depends on every destination existing.
8. Integrate Guide/Learning/Advanced/playbook links only after destination fragments are stable.
9. Run full aggregate validation, Copyparty HTTP, available live-DOM validation, migration completeness audit, and two-axis Standards/Spec review last.

These edges are mandatory inputs to the ticket breakdown.

## User Stories

1. As a Target maintainer, I want a Question-bank route from the Guide entry so I can rehearse without searching legacy trees.
2. As a Core maintainer, I want questions grouped by the six Learning pages so prerequisite order remains visible.
3. As an Advanced maintainer, I want optional mechanism questions grouped by Advanced owner so policy detail does not overload Core.
4. As a maintainer changing code, I want scenario packets that produce ledgers, traces, and verification decisions rather than recall alone.
5. As a reader, I want prompts separated from answers so I can attempt retrieval before seeing the model response.
6. As a reader, I want immutable IDs and direct prompt/answer links so references survive editorial reordering.
7. As a reader, I want every answer to state evidence and limitations so source structure is not mistaken for runtime proof.
8. As a reader, I want answers linked to Canonical explanations so the bank does not fork the guide.
9. As a documentation maintainer, I want every legacy item dispositioned so deduplication cannot silently discard useful coverage.
10. As a documentation maintainer, I want all Question-bank pages discovered by the aggregate gate so new pages cannot escape checks.
11. As an evidence maintainer, I want historical and candidate status routed to their owners so copied answers cannot drift.
12. As the author of Reader question intake, I want my raw questions preserved while validated answers become reusable Canonical questions.

## Testing Decisions

- Build tests around reader-visible contracts rather than exact answer prose.
- Test schema, identifiers, pairing, routes, evidence labels, migration populations, navigation, and forbidden boundary violations.
- Keep page discovery as one aggregate source of truth used by Markdown, link, language, asset, HTTP, and DOM gates.
- Add fixture-based negative tests showing aggregate discovery catches a broken Question-bank link and Korean prose.
- Add focused negative tests for duplicate IDs, missing paired answers, missing required fields, invalid modes/evidence labels, incomplete migration populations, and mutation of Reader question intake.
- Run `node --test scripts/*.test.mjs`, `node scripts/check-maintainer-guide.mjs`, the Copyparty source checker for every changed Markdown page, Copyparty HTTP for all discovered pages/assets, and `git diff --check`.
- If Playwright remains unavailable, report live DOM as unavailable rather than passing.
- No CUBRID engine build or runtime workload is required unless implementation strengthens a source/runtime claim beyond existing pinned evidence.
- Finish with independent Standards and Spec reviews against the pre-implementation fixed point.

## Out of Scope

- Executable quiz runners, copied SQL, database creation/deletion, scoring, certification, or learner-state tracking.
- Korean translation.
- Canonical PostgreSQL/MySQL comparison questions.
- Moving, editing, or deleting legacy evidence banks, concrete quiz artifacts, receipts, or Reader question intake.
- Reproducing complete legacy answers or teaching explanations verbatim.
- Changing `VS-*` status or claiming current defects without required evidence.
- Describing a CUBRID revision other than the pinned baseline without a separate revalidation effort.
- Adding new diagrams solely for the Question bank; its important relationships already have Canonical visuals.
