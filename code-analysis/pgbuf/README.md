# CUBRID page-buffer analyses

Created: 2026-10-02. Last modified: 2026-10-21 (Asia/Seoul).

This collection moved from `pgbuf-analysis/` on 2026-10-21. Historical analyses
and proposals retain their original source revision and verification scope.
The move does not revalidate old claims against the current engine.

Start with the [Korean presentation](f799e05_claude/CUBRID_PAGE_BUFFER_PRESENTATION_KO.md),
the [e6ed61e87 overview](e6ed61e_claude/00-overview.md), or the
[offline self-study route](teach-course/README.md). The original
[5cd4f860e HTML report](cubrid-page-buffer-report_5cd4f860e_claude.html) accompanies
the original fact sheets and defect analysis below.

Related reports keep their established paths:

- [Page-buffer field guide, f799e05](../page-buffer-subsystem-centered-on-the-complete-lifecycle-and-cal/f799e05_codex/index.html).
- [Markdown companion](../page-buffer-subsystem-centered-on-the-complete-lifecycle-and-cal/f799e05_codex/notion/page-buffer-guide.md).
- [Seminar repository and migration notice](../page-buffer-presentation/README.md).

## Markdown documents

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [report-2026-10-02.md](report-2026-10-02.md) | Page-buffer improvement candidates and measurement limits | 2026-10-02 | 2026-10-21 | Preserve revision-specific analysis and decisions for reviewers |
| [pgbuf-defects-report_5cd4f860e_claude.md](pgbuf-defects-report_5cd4f860e_claude.md) | Source-backed defects found in the 5cd4f860e analysis | 2026-08-06 | 2026-10-21 | Explain defect mechanisms and their consequences |
| [e6ed61e_claude/00-overview.md](e6ed61e_claude/00-overview.md) | Subsystem overview, terminology, and reading route | 2026-08-18 | 2026-10-21 | Orient readers to the e6ed61e87 page-buffer design |
| [e6ed61e_claude/01-structures.md](e6ed61e_claude/01-structures.md) | Structures, constants, memory layout, and initialization | 2026-08-18 | 2026-10-21 | Explain the state managed by the page buffer |
| [e6ed61e_claude/02-fix-unfix-latch.md](e6ed61e_claude/02-fix-unfix-latch.md) | Fix/unfix acquisition paths and latch protocol | 2026-08-18 | 2026-10-21 | Explain page ownership and concurrent access |
| [e6ed61e_claude/03-lru-victim-quota.md](e6ed61e_claude/03-lru-victim-quota.md) | LRU zones, victims, quotas, and AOUT | 2026-08-18 | 2026-10-21 | Explain replacement policy and its trade-offs |
| [e6ed61e_claude/04-flush-wal-daemons.md](e6ed61e_claude/04-flush-wal-daemons.md) | Dirty pages, flushing, WAL, and checkpoint daemons | 2026-08-18 | 2026-10-21 | Explain the durability and writeback boundaries |
| [e6ed61e_claude/05-ordered-fix-dealloc.md](e6ed61e_claude/05-ordered-fix-dealloc.md) | Ordered fix, watchers, deallocation, and VPID locks | 2026-08-18 | 2026-10-21 | Explain ordering and page-identity protection |
| [e6ed61e_claude/06-misc-observability.md](e6ed61e_claude/06-misc-observability.md) | Integration paths, counters, and diagnostics | 2026-08-18 | 2026-10-21 | Connect the core lifecycle to operational behavior |
| [e6ed61e_claude/07-qa-workbook.md](e6ed61e_claude/07-qa-workbook.md) | Questions and model answers about the subsystem | 2026-08-18 | 2026-10-21 | Support source-level design review and learning |
| [e6ed61e_claude/08-page-buffer-new-plan.md](e6ed61e_claude/08-page-buffer-new-plan.md) | Historical page_buffer_new.cpp reimplementation proposal | 2026-08-18 | 2026-10-21 | Record the proposed interface and implementation sequence |
| [e6ed61e_claude/09-issue-proposals.md](e6ed61e_claude/09-issue-proposals.md) | Revision-specific defect and improvement proposals | 2026-08-18 | 2026-10-21 | Explain candidate follow-up work and priorities |
| [e6ed61e_claude/10-CBRD-27263-repro-proof-and-solutions.md](e6ed61e_claude/10-CBRD-27263-repro-proof-and-solutions.md) | Instrumented deallocation-counter observations and solution comparison | 2026-08-18 | 2026-10-21 | Substantiate the CBRD-27263 accounting problem |
| [e6ed61e_claude/research/lockfree-fix-origin.md](e6ed61e_claude/research/lockfree-fix-origin.md) | Lock-free fix history, motivation, and reversion costs | 2026-08-19 | 2026-10-21 | Evaluate the origin and trade-offs of the fast path |
| [e6ed61e_claude/research/prevent-dealloc-necessity.md](e6ed61e_claude/research/prevent-dealloc-necessity.md) | Consumers and correctness role of prevent-dealloc protection | 2026-08-19 | 2026-10-21 | Assess whether the protection can be simplified safely |
| [f799e05_claude/README.md](f799e05_claude/README.md) | Presentation and evidence-corpus reading route | 2026-09-01 | 2026-10-21 | Guide readers through the f799e05 seminar package |
| [f799e05_claude/CUBRID_PAGE_BUFFER_PRESENTATION_KO.md](f799e05_claude/CUBRID_PAGE_BUFFER_PRESENTATION_KO.md) | Korean presentation, caller contracts, and reviewer Q&A | 2026-09-01 | 2026-10-21 | Explain the page lifecycle to teammates |
| [f799e05_claude/analysis/README.md](f799e05_claude/analysis/README.md) | Navigation for the source and runtime evidence notes | 2026-09-01 | 2026-10-21 | Connect presentation claims to detailed evidence |
| [f799e05_claude/analysis/monitoring/runtime-path-monitoring.md](f799e05_claude/analysis/monitoring/runtime-path-monitoring.md) | Instrumented whole-pool SQL path counts and findings | 2026-09-01 | 2026-10-21 | Distinguish observed page-buffer behavior from source inference |
| [f799e05_claude/analysis/research/api-inventory.md](f799e05_claude/analysis/research/api-inventory.md) | Public interfaces, types, caller obligations, and hazards | 2026-09-01 | 2026-10-21 | Explain how callers use the page-buffer interface |
| [f799e05_claude/analysis/research/caller-use-cases.md](f799e05_claude/analysis/research/caller-use-cases.md) | Heap, B-tree, recovery, vacuum, and daemon call paths | 2026-09-01 | 2026-10-21 | Connect subsystem contracts to their callers |
| [f799e05_claude/analysis/research/evidence-reuse.md](f799e05_claude/analysis/research/evidence-reuse.md) | Audited claims and historical runtime-evidence limits | 2026-09-01 | 2026-10-21 | Bound reuse of earlier evidence at the same revision |
| [f799e05_claude/analysis/research/internal-mechanisms.md](f799e05_claude/analysis/research/internal-mechanisms.md) | BCB, hash, latch, holder, flush, and replacement invariants | 2026-09-01 | 2026-10-21 | Explain the internal state machines and synchronization |
| [f799e05_claude/analysis/research/pedagogy-plan.md](f799e05_claude/analysis/research/pedagogy-plan.md) | Presentation structure, explanation sequence, and coverage rationale | 2026-09-01 | 2026-10-21 | Document the teaching design of the retained presentation |
| [f799e05_claude/analysis/research/qa-answers.md](f799e05_claude/analysis/research/qa-answers.md) | Source-grounded answers to 55 design and review questions | 2026-09-01 | 2026-10-21 | Support review, debugging, and presentation follow-up |
| [f799e05_claude/analysis/research/qa-questions.md](f799e05_claude/analysis/research/qa-questions.md) | 55 source-anchored questions for the presentation | 2026-09-01 | 2026-10-21 | Define the questions answered by the companion answer bank |
| [f799e05_claude/analysis/research/scope.md](f799e05_claude/analysis/research/scope.md) | Audience, included scope, exclusions, and evidence policy | 2026-09-01 | 2026-10-21 | Define the retained presentation and analysis scope |
| [research/bcb-latch-diagnostics_a9f075586_codex.md](research/bcb-latch-diagnostics_a9f075586_codex.md) | BCB latch owner tracking and indefinite-wait diagnostics | 2026-10-07 | 2026-10-21 | Assess diagnostic API feasibility and lifetime risks |
| [research/cubrid-flush-wal-dwb.md](research/cubrid-flush-wal-dwb.md) | Dirty-page, WAL, checkpoint, and DWB source analysis | 2026-08-06 | 2026-10-21 | Substantiate the original durability explanation |
| [research/cubrid-lru-victim.md](research/cubrid-lru-victim.md) | LRU, private/shared lists, quotas, and victim selection | 2026-08-06 | 2026-10-21 | Substantiate the original replacement-policy explanation |
| [research/cubrid-structs-fix.md](research/cubrid-structs-fix.md) | Structures and fix/unfix lifecycle at 5cd4f860e | 2026-08-06 | 2026-10-21 | Substantiate the original ownership and latch explanation |
| [research/innodb-bufpool.md](research/innodb-bufpool.md) | Revision-specific InnoDB buffer-pool comparison | 2026-08-06 | 2026-10-21 | Compare responsibilities and synchronization with CUBRID |
| [research/postgres-bufmgr.md](research/postgres-bufmgr.md) | Revision-specific PostgreSQL buffer-manager comparison | 2026-08-06 | 2026-10-21 | Compare responsibilities and synchronization with CUBRID |
| [teach-course/README.md](teach-course/README.md) | Offline lesson route and supporting-file responsibilities | 2026-10-21 | 2026-10-21 | Make the retained course usable without session records |
| [teach-course/MISSION.md](teach-course/MISSION.md) | Course goals, pinned scope, and reader outcomes | 2026-09-01 | 2026-10-21 | Define the page-buffer explanation and rehearsal goals |
| [teach-course/RESOURCES.md](teach-course/RESOURCES.md) | Pinned source links, contract cards, and related analyses | 2026-09-01 | 2026-10-21 | Connect self-study materials to their evidence |
| [teach-course/reference/pgbuf-question-bank.md](teach-course/reference/pgbuf-question-bank.md) | 38 progressive questions with visible model answers | 2026-09-01 | 2026-10-21 | Support source-backed self-study and presentation rehearsal |
