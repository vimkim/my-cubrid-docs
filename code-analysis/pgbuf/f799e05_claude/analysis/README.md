# CUBRID page-buffer analysis materials

Created: 2026-09-01. Last modified: 2026-10-21 (Asia/Seoul).

These English evidence notes support the
[Korean presentation](../CUBRID_PAGE_BUFFER_PRESENTATION_KO.md). Primary source
revision: `f799e05d77d5300c6ea5753b4a6cc7caee6d8912`. Runtime monitoring used the
logging-only probe commit identified in its report. Historical evidence keeps
its original limits; the expanded interface catalog does not inherit an older
report's readiness verdict.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [monitoring/runtime-path-monitoring.md](monitoring/runtime-path-monitoring.md) | Instrumented whole-pool SQL path counts and findings | 2026-09-01 | 2026-10-21 | Distinguish observed page-buffer behavior from source inference |
| [research/api-inventory.md](research/api-inventory.md) | Public interfaces, types, caller obligations, and hazards | 2026-09-01 | 2026-10-21 | Explain how callers use the page-buffer interface |
| [research/caller-use-cases.md](research/caller-use-cases.md) | Heap, B-tree, recovery, vacuum, and daemon call paths | 2026-09-01 | 2026-10-21 | Connect subsystem contracts to their callers |
| [research/evidence-reuse.md](research/evidence-reuse.md) | Audited claims and historical runtime-evidence limits | 2026-09-01 | 2026-10-21 | Bound reuse of earlier evidence at the same revision |
| [research/internal-mechanisms.md](research/internal-mechanisms.md) | BCB, hash, latch, holder, flush, and replacement invariants | 2026-09-01 | 2026-10-21 | Explain the internal state machines and synchronization |
| [research/pedagogy-plan.md](research/pedagogy-plan.md) | Presentation structure, explanation sequence, and coverage rationale | 2026-09-01 | 2026-10-21 | Document the teaching design of the retained presentation |
| [research/qa-answers.md](research/qa-answers.md) | Source-grounded answers to 55 design and review questions | 2026-09-01 | 2026-10-21 | Support review, debugging, and presentation follow-up |
| [research/qa-questions.md](research/qa-questions.md) | 55 source-anchored questions for the presentation | 2026-09-01 | 2026-10-21 | Define the questions answered by the companion answer bank |
| [research/scope.md](research/scope.md) | Audience, included scope, exclusions, and evidence policy | 2026-09-01 | 2026-10-21 | Define the retained presentation and analysis scope |

The [monitoring report](monitoring/runtime-path-monitoring.md) links the retained
driver and explains its generated raw output. Rendering assets are linked from
the presentation; the [topic index](../../README.md) lists the complete corpus.
