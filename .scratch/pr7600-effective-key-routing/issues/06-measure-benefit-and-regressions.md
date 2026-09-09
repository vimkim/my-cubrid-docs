# 06: Measure resource savings and regression risk

**What to build:** A reproducible comparison showing whether effective-key routing removes useful temporary allocation/copying work without hiding small-row or nonpartitioned regressions.

**Blocked by:** 03 — Route UPDATEs and pending increments correctly.

**Status:** resolved

**Parent:** [Effective-key routing specification](../spec.md).

**Execution gate:** Instrumentation, benchmarks, and database experiments require separate authorization. This ticket records evidence; it cannot approve a slowdown or relax the spec by itself.

- [x] Compare baseline `b871ea386d2c5419b7abae07dda58b9b7f36377a` and an identified candidate revision using equivalent build configuration, settings, data, instrumentation, and workload distributions.
- [x] Include large uncompressed non-key payloads, multiple OOS candidates, small FORCE_OUTLINE payloads, small inline rows, unchanged-key updates, moved updates, and nonpartitioned controls; exercise integer and string/expression keys.
- [x] Collect temporary allocation bytes/peak, copied bytes, full-row transformation/retry counts, OOS payload serialization bytes, OOS insert counts, routing invocations, CPU time, and elapsed time. These are diagnostic measurements, not brittle functional test assertions.
- [x] Demonstrate that the optimized path eliminates the temporary complete inline row, not merely renames the probe or moves equivalent full-row work elsewhere.
- [x] Verify logical values and correct OOS ownership during measurement; invalid results cannot support a performance claim.
- [x] Record warmup, repetitions, noise estimation, per-workload distributions, and reproducibility details. Repeat suspected regressions and do not hide them in an aggregate average.
- [x] Distinguish key-only serialization and final OOS payload work from eliminated whole-row work; retained downstream routing and its potential OOS-key reads remain counted.
- [ ] Demonstrate measurable temporary allocation/copying savings on OOS-producing writes. Flat runtime is acceptable; a reproducible slowdown beyond measured noise on small non-OOS/nonpartitioned controls requires renewed user approval. Disclose other repeatable regressions as explicit trade-offs too.
- [x] Treat inconclusive evidence, insufficient savings, or regressions as unmet gates. Do not eliminate downstream routing, add a silent fallback, or widen preparation refactoring without reopening design.
- [x] Preserve inputs and methodology so ticket 07 can repeat affected comparisons on the final integrated revision.

**Completion evidence:** Paired resource/timing report, candidate provenance, correctness checks, per-workload acceptance assessment, and any requested design-owner decisions. Measurements can be completed with a failed acceptance result; shipping remains blocked.

**Spec coverage:** User stories 34–35, 37; measurement counters, workload matrix, noise handling, and benefit/reopening policy.

## Comments

- 2026-09-09: User explicitly authorized independent tickets 04 and 06 while retaining CBRD-27237 as a blocker for 05/07. Preparing equivalent release builds in `pr7600-original-baseline` and `pr7600-measure-candidate`; both use the baseline-pinned CCI submodule. Candidate engine diff matches the main worktree exactly (SHA-256 `3d978ff8134516d0ab26a809b6fd790bd289a6865476a215921c8fa5e6eea34a`). No measurements or acceptance conclusion yet.

## Answer

2026-09-09: [Paired measurement report](../../../cbrd-27089/design/ticket06-measurements-b871ea386-codex.md) and reproducible harness/observers delivered. Measurement work is resolved with an **inconclusive runtime acceptance result**, as permitted by this ticket; the benefit gate is not marked passed. Large OOS writes eliminate the full inline probe, record-buffer allocation, and grown-row copy while retaining final serialization/routing. Nine workloads pass logical/owner/rollback checks. ABBA timing plus larger pinned-CPU control repeats still show substantial between-process drift; small-inline slowdown remains suspected, not attributed or waived. Recommend a quieter-host rerun before accepting06 or changing the design. Tickets05/07 remain blocked; no push.
