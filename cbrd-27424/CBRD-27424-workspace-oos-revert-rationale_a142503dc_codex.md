# PR #7925: rationale for restoring the original workspace OOS implementation

Date: 2026-10-07. Issue: [CBRD-27424](https://jira.cubrid.org/browse/CBRD-27424). PR: [CUBRID/cubrid#7925](https://github.com/CUBRID/cubrid/pull/7925).

The user has decided to restore the workspace OOS implementation from `90f3bd79e`. The later direct serialized-byte revision did not demonstrate a performance benefit in the recorded Release benchmark: the large-load median increased from **5.11 to 5.66 seconds elapsed (+10.8%)**, and from **3.47 to 4.03 seconds user + system CPU (+16.1%)**. Restoring the earlier implementation is a conservative decision based on those observations and the additional implementation surface, rather than a claim that the slowdown's internal cause has been proven.

This report records the decision and its evidence. It does not execute the source revert or report post-revert test or performance results. The source HEAD at publication preparation is `a142503dc1a6f85b498a425aa58d6a78136ccc6b`.

## What the benchmark compared

| Role | Exact source revision | Behavior |
|---|---|---|
| Measured baseline; intended restoration reference | [`90f3bd79eecec3344b3b745d82c516a46d073667`](https://github.com/CUBRID/cubrid/commit/90f3bd79eecec3344b3b745d82c516a46d073667) | Workspace OOS support already exists. The SA locator helper reads serialized records through heap attrinfo/`DB_VALUE` and reuses the existing disk/OOS converter. GoogleTest conversion is already included. |
| Measured candidate source | [`f037616cd17af92e1226afcde80fd2a6fff9121d`](https://github.com/CUBRID/cubrid/commit/f037616cd17af92e1226afcde80fd2a6fff9121d) | Demotes serialized workspace value spans directly, with a shared representation/size planner and compact-record reconstruction. |
| Current PR HEAD | [`a142503dc1a6f85b498a425aa58d6a78136ccc6b`](https://github.com/CUBRID/cubrid/commit/a142503dc1a6f85b498a425aa58d6a78136ccc6b) | Production source is identical to `f037616cd`; intervening changes remove internal Markdown and repair a collection test expectation and the benchmark license. This HEAD was not a separate historical benchmark sample. |
| PR merge-base, not measured in this experiment | [`fb567a629cdb390fff920542173fa36f454c74a0`](https://github.com/CUBRID/cubrid/commit/fb567a629cdb390fff920542173fa36f454c74a0) | OOS integration base for PR #7925, targeting `feature/oos-merge`. |

**This is a comparison between two implementations within PR #7925. It is not a measurement of the total PR cost relative to its merge-base.** Restoring `90f3bd79e` retains the original fix that makes standalone loader and workspace writes use OOS; it does not restore the omission present before that fix.

The original CSV identifies the candidate as `raw-record`. The contemporaneous [publication snapshot](https://github.com/CUBRID/cubrid/blob/f037616cd17af92e1226afcde80fd2a6fff9121d/docs/workspace-oos-mode-comparison.md#publication-validation-snapshot) associates those measurements with the source committed as `f037616cd`. The CSV itself contains no binary-to-commit attestation. That distinction is preserved in the [verification record](evidence/workspace-oos-benchmark-2026-10-06/verification.json).

## Workloads and method

The recorded experiment used Release installations, fresh databases for every sample, and three sequential runs per workload and implementation. `/usr/bin/time` measured only `cubrid loaddb -S`; database creation, fixture generation, post-load verification and deletion were outside the timed command. CPU means user time plus system time.

| Workload | Rows | VARBIT payload per row | Object-file bytes | Input verification |
|---|---:|---:|---:|---|
| Small | 100,000 | 48 bytes | 10,588,910 | Before/after fixture SHA-256 matches |
| Large | 10,000 | 5,000 bytes | 100,088,910 | Before/after fixture SHA-256 matches |

The harness uses deterministic payload generation, a private database registry and configuration, 16 KiB database pages, a 128 MiB data buffer and a 32 MiB log buffer. Both sample databases use the same schema, `bench(id INTEGER, v BIT VARYING)`. See the [pinned benchmark script](https://github.com/CUBRID/cubrid/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/scripts/benchmark_workspace_oos.sh).

The preserved CSVs are unmodified copies of local evidence:

- [Before: `90f3bd79e`](evidence/workspace-oos-benchmark-2026-10-06/before.csv), originally `build_preset_release_gcc/benchmark-shell-before/results.csv` in the source worktree.
- [After: `raw-record`](evidence/workspace-oos-benchmark-2026-10-06/after.csv), originally `build_preset_release_gcc/benchmark-shell-after/results.csv`.
- [Verification record](evidence/workspace-oos-benchmark-2026-10-06/verification.json): CSV and fixture hashes, recomputed medians, saved value-check outcomes and OOS statistics.

## Recorded results

All values below are seconds. Each triple preserves the CSV's sample order.

| Workload | Baseline elapsed | Candidate elapsed | Baseline user + system CPU | Candidate user + system CPU |
|---|---|---|---|---|
| Small | 2.17, 2.16, 2.13 | 2.13, 2.16, 2.12 | 1.04, 1.03, 1.01 | 1.00, 1.03, 1.00 |
| Large | 5.15, 5.05, 5.11 | 5.66, 5.60, 5.86 | 3.50, 3.44, 3.47 | 3.89, 4.03, 4.07 |

| Workload | Median elapsed, before → after | Change | Median CPU, before → after | Change |
|---|---|---:|---|---:|
| Small | 2.16 → 2.13 | −1.4% | 1.03 → 1.00 | −2.9% |
| Large | 5.11 → 5.66 | **+10.8%** | 3.47 → 4.03 | **+16.1%** |

For the large workload, every candidate elapsed sample exceeds every baseline elapsed sample; the same is true for CPU. That makes the recorded increase more substantial than a single slow sample. Three runs still do not provide a controlled statistical or causal attribution.

Reinspection on 2026-10-07 confirmed that all twelve saved post-load checks report `VALUE_OK`, with no `ERROR:` or `VALUE_BAD` marker in their schema, loader or check outputs. This checks the expected row count, ID endpoints and exact payload equality.

All six large-load samples also report the same physical OOS statistics: **10,000 OOS chunk records**, `Oos_recs_sumlen=50,320,000`, 3,335 OOS user pages and `Oos_physical_bytes=54,507,240`. `Oos_recs_sumlen` includes chunk headers and is not the raw payload length. Representative complete outputs are preserved [before](evidence/workspace-oos-benchmark-2026-10-06/before-large-0-check.txt) and [after](evidence/workspace-oos-benchmark-2026-10-06/after-large-0-check.txt), with trailing spaces removed for documentation; the verification JSON records both the original-output hashes and exported-file hashes. These observations rule out a simple explanation that one side skipped OOS storage or loaded fewer rows in this fixture; they do not identify the CPU hotspot.

## Why restore the earlier implementation

The direct-byte revision was intended to avoid the workspace record's `DB_VALUE` round trip while retaining the existing storage behavior. The measured large-load result does not support a performance justification for keeping it. The small-load difference is modest and does not offset the observed large-value cost for the workload motivating the change.

The earlier implementation already provides the requested standalone OOS behavior through the existing heap attrinfo transformation. Its locator helper applies conversion after destination heap selection, preserves CHN and existing external LOB locators, and keeps OOS and heap/index changes inside the force top operation. See the [original helper](https://github.com/CUBRID/cubrid/blob/90f3bd79eecec3344b3b745d82c516a46d073667/src/transaction/locator_sr.c#L4930).

The later revision adds a serialized-record demoter and exports its planning API while extracting the planner from the heap attribute path. This adds record-layout validation, byte-span planning, buffer ownership and reconstruction responsibilities. Those responsibilities can be correct, but the recorded evidence does not show the intended performance payoff. The user's decision is to keep the original functional fix and withdraw this additional revision from the current PR. A future optimization can be evaluated separately with controlled measurements and profiling.

This rationale does not claim a correctness defect in direct demotion. The current local repair evidence records 37/37 CTests passing, including all 13 loader/workspace cases and 21 comparison cases. The collection test repair recognizes an existing encoding difference between workspace and ordinary SQL writers while preserving logical collection equality. Passing those tests and demonstrating a performance benefit are separate claims. The [published review guide](https://github.com/vimkim/my-cubrid-docs/blob/e632f30a5abfb7ec9133c2cdbaba9262f87068fa/cbrd-27424/code_review_guide_a142503dc_codex.md) explains the implementation and comparison coverage; the local successful repair transcript is `/tmp/pr7925-repair-ctest.log`.

## Scope of the planned revert

Use `90f3bd79e` as the production restoration reference, and implement the reversal as a new scoped commit on the existing task branch. Preserve the original workspace OOS support, GoogleTest conversion, force flags, object-reference handling, CHN, destination heap ownership, rollback and successful no-logging loading.

The production difference between `90f3bd79e` and `a142503dc` is confined to:

- `src/storage/heap_file.c`: restore the original attrinfo planner and its private plan representation.
- `src/storage/heap_oos.cpp` and `heap_oos.hpp`: withdraw the direct workspace demoter and APIs introduced for it.
- `src/transaction/locator_sr.c`: restore attrinfo conversion, copyarea ownership and corresponding caller cleanup.

Review subsequent coverage separately. Retain the loader OOS+bigone rejection/ordinary-bigone control where applicable and the independent benchmark with its repaired license. Adapt tests that call the withdrawn raw-only helper or document why a particular comparison ceases to apply; generic value, selection, rollback and ownership checks must remain meaningful. The exact configured test count may therefore change.

A blind branch reset or whole-commit reversal would mix these decisions with later test repairs and already removed Markdown. Preserve branch history, unrelated `cubrid-cci` changes and subsequent useful coverage. If the branch advances, inspect its new changes before applying the restoration reference.

The existing CBRD-27057 threshold difference remains outside this reversal: both implementations use `DB_PAGESIZE/4`, while the normative OOS context updated 2026-09-22 requires a derived four-record heap target. Restoring the earlier implementation is not a claim that this separate conformance gap is repaired.

## Evidence limits and validation after the revert

The historical experiment has only three sequential samples per side. Its retained evidence does not document randomized/interleaved execution, CPU affinity, exclusive host use, compiler flags beyond the reported Release mode, profiler samples or complete installation provenance. The increased user + system CPU suggests additional CPU cost in those runs, but does not establish which function caused it or exclude scheduling, instrumentation or build-environment differences.

No benchmark against the PR merge-base is present in these CSVs. No new benchmark or build was run to write this report. Neither restoring the earlier implementation nor its expected timing recovery has yet been verified.

The implementation follow-up should:

1. Build the restored implementation and run its configured OOS CTests, including loader/workspace correctness, rollback, filtered errors, partition movement, references, LOB preservation and successful no-logging loading.
2. Reuse identical fixtures and matched Release build settings to compare the restored implementation with the current direct-byte source. Prefer additional alternating samples under comparable host load. Preserve elapsed and user/system CPU separately, source revisions, install identities and OOS placement evidence.
3. Record the new results without assuming that historical timings will reproduce. Reassess the performance rationale if the increase disappears under matched conditions.
4. Review and commit the scoped reversal, then publish the source change and run CI when authorized. The report does not attribute or resolve the existing shell CI failures.

For reproduction, use the retained [benchmark script](https://github.com/CUBRID/cubrid/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/scripts/benchmark_workspace_oos.sh) with separately built installations. Output directories must be new:

```bash
bash benchmark_workspace_oos.sh /path/to/restored-release /path/to/new-restored-results restored-COMMIT 3
bash benchmark_workspace_oos.sh /path/to/direct-byte-release /path/to/new-direct-results direct-COMMIT 3
```

## Tracked delivery and next action

Work-tracker item **285** covers this report, its evidence, documentation commit/push and a summary comment linking the report on PR #7925. Item **286** covers the subsequent source restoration and verification; it follows publication of this rationale. Parent item **267** remains the broader PR-readiness record and is not completed by this report.

The `ask-matt` route is **continue in the current session → `/implement` for the scoped reversal**, using the published rationale as the implementation brief and `track-work` item 286 as the durable execution record. The desired behavior and restoration reference are decided; another design interview or a multi-ticket orchestration flow is unnecessary for this step. Performance root-cause work through `diagnosing-bugs` can be a separate follow-up if the direct-byte approach is revisited.

## Restoration follow-up, 2026-10-07

The requested restoration is implemented as new source commit `1c660d22e`, with all four production files byte-identical to `90f3bd79e`. Debug and matched optimized Release builds passed; the full configured CTest run passed 37/37, retaining all 21 comparison cases and 13 workspace/loader cases. Five alternating benchmark pairs show restored large-load medians 9.1% lower for elapsed time and 11.6% lower for user + system CPU; every large pair uses less CPU. Shared-host variability and the inherited allocation-exception review finding are recorded in the [restoration and verification report](CBRD-27424-workspace-oos-restoration_1c660d22e_codex.md). The historical measurements and limits above remain the record of the earlier experiment.
