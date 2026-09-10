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

2026-09-09 user decision: **retain independent final record routing for this PR; defer destination reuse**. Recorded in the [design review](../../../cbrd-27089/design/destination-reuse-review-213ce80f5-codex.md). Existing specification remains unchanged. This is not acceptance of a runtime regression or a waiver of the runtime/lifecycle gates; no engine work or further experiments authorized by this confirmation.

2026-09-09 cost attribution: [Hardware counters, sampled profiles and source accounting](../../../cbrd-27089/design/ticket06-cpu-attribution-b871ea386-codex.md) identify approximately +0.689% whole-process user instructions on small-inline INSERTs, versus +0.00054% on the nonpartitioned control. Eight counter and two profile runs pass correctness. Small-inline routing is once in the original versus twice in the candidate; full-row transforms and tracked allocations remain equal. Runtime regression magnitude remains unproved; no gate waiver or engine change. Recommend design review before attempting destination reuse or a no-OOS bypass.

2026-09-09 same-host follow-up: User authorized additional interleaved timing here. [52-run report](../../../cbrd-27089/design/ticket06-interleaved-b871ea386-codex.md): all correctness checks pass; small-inline CPU block estimates range from approximately -0.1% to +13.6%, and host load rose sharply. Runtime gate remains inconclusive/unmet, with no waiver. Recommend separately scoped small-inline cost attribution; no engine changes or new profiling were performed.

2026-09-09: [Paired measurement report](../../../cbrd-27089/design/ticket06-measurements-b871ea386-codex.md) and reproducible harness/observers delivered. Measurement work is resolved with an **inconclusive runtime acceptance result**, as permitted by this ticket; the benefit gate is not marked passed. Large OOS writes eliminate the full inline probe, record-buffer allocation, and grown-row copy while retaining final serialization/routing. Nine workloads pass logical/owner/rollback checks. ABBA timing plus larger pinned-CPU control repeats still show substantial between-process drift; small-inline slowdown remains suspected, not attributed or waived. Recommend a quieter-host rerun before accepting06 or changing the design. Tickets05/07 remain blocked; no push.


2026-09-10 diagnosis update: [Merged-head runtime diagnosis](../../../cbrd-27089/design/ticket06-runtime-diagnosis-988a4d2-codex.md) now reproduces the small-row regression beyond matching A/A noise envelopes. At engine head `988a4d2fa`, original inline INSERT CPU increases were +1.70% and +2.12%; a minimized key-only case repeated at +3.02% and +2.36%. All worker correctness checks passed. Whole-process counters show +1.093% instructions for partitioned inserts versus +0.015% for the nonpartitioned control; these counters support additional routing work but do not explain all timed runtime cost. This supersedes the earlier *inconclusive* small-row timing disposition for the measured cases, not the other workload evidence. Measurement delivery remains resolved; the performance acceptance checkbox remains unchecked. A renewed tradeoff decision is pending. No engine fix, final-route bypass, acceptance waiver, source commit or push was made.
