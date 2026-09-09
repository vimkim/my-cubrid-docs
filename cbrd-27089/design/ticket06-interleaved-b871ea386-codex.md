# Ticket 06: same-host interleaved timing follow-up

2026-09-09. User authorized rerunning measurements on this machine. No engine changes, rebuilds, CPU-governor changes, process interference, commits, or pushes were made in this follow-up.

## Outcome

All **52 process runs** passed their logical-value, physical OOS chunk ownership, and rollback checks. The **runtime no-regression gate remains inconclusive and unmet**. Small-inline overhead remains a concern, but neither a precise slowdown nor equivalence is established. Existing allocation/copy savings remain separate evidence; these timing runs did not repeat allocation diagnostics.

The machine was initially lightly loaded, but one-minute system load rose from **2.64 to 64.93** during the fixed run plan. This is not a CPU-utilization percentage and does not establish the cause of individual slow samples. CPU pinning did not provide an exclusive core. No slow observations were discarded, and the plan was not stopped when a favorable result appeared.

## Provenance and method

- Baseline: `b871ea386d2c5419b7abae07dda58b9b7f36377a`, `pr7600-original-baseline`; no engine diff.
- Candidate: the same base in `pr7600-measure-candidate`, engine diff SHA-256 `3d978ff8134516d0ab26a809b6fd790bd289a6865476a215921c8fa5e6eea34a`.
- Both retain baseline-pinned CCI `bd86063a5bd481f0e22bf07c8a76bf736f86443a`, release configuration and SA_MODE SQL harness. Each run verifies executable, engine-library and test-source hashes against the earlier accepted diagnostic provenance. No debugger wraps timing.
- This is the **pre-format measured candidate**, not an exact benchmark of final main commit `213ce80f54dc54130fcef22e616cb28f4835f6d5`. The [earlier report](ticket06-measurements-b871ea386-codex.md) records the whitespace-only distinction. Final integrated-revision acceptance still needs its own affected comparisons.
- Four control blocks, alternating **ABBA / BAAB / ABBA / BAAB**; each block runs all three controls, rotating their order. Each letter is a fresh process and private database. A = baseline; B = candidate.
- Controls: 1,024 statements/sample, two warmups, eleven retained samples/process; 48 processes total. Full nine-workload matrix: ABBA, 128 statements/sample, two warmups, nine retained samples/workload/process; four more processes.
- CPU affinity: logical CPU 6, whose SMT sibling is 46. Read-only inspection found governor `performance`; neither sibling exclusivity nor stable frequency was established. The orchestrator and evidence collection are outside the timed SQL batches.
- SQL compile/execute and storage are timed; SQL text construction, seed setup, verification, and rollback are outside the timed interval. Both process CPU and elapsed time are retained. This is not an isolated routing-function microbenchmark or a server concurrency/vacuum test.
- Private fixtures remain under the existing `.artifacts/pr7600-independent-RjRhFS` directory on `/home`. Shared databases were not touched. Total process-plan duration: approximately 343 seconds.

## Small-row controls

Each entry is candidate/baseline, computed from geometric means of the two **process medians** on each side of one balanced block. Greater than 1 means more time. The final column is descriptive only, **not a confidence bound or an acceptance statistic**. Within-process repetitions are not treated as independent process runs.

| Metric / workload | Block 0 | Block 1 | Block 2 | Block 3 | Geometric mean |
|---|---:|---:|---:|---:|---:|
| CPU, small inline | 1.0075 | 1.0619 | 0.9986 | 1.1355 | 1.0495 |
| CPU, nonpartitioned small | 1.0154 | 1.0055 | 0.9517 | 1.0344 | 1.0012 |
| CPU, small FORCE_OUTLINE | 0.9887 | 0.9721 | 0.9872 | 0.9770 | 0.9812 |
| Elapsed, small inline | 1.0068 | 1.0610 | 0.9800 | 1.1386 | 1.0449 |
| Elapsed, nonpartitioned small | 1.0152 | 1.0067 | 0.9772 | 1.0347 | 1.0082 |
| Elapsed, small FORCE_OUTLINE | 0.9894 | 0.9716 | 0.9868 | 0.9757 | 0.9808 |

Small inline does not establish a repeatable fixed overhead: the four CPU estimates range from approximately -0.1% to +13.6%. However, the low-load BAAB block also suggests overhead (+6.2%); high machine load alone cannot dismiss the concern. Nonpartitioned-small estimates span -4.8% to +3.4%, demonstrating substantial comparison variability even in the control. Small FORCE_OUTLINE is consistently modestly faster in these blocks, but that does not approve the small-inline case.

The process-level distributions show why block averages alone are insufficient. Small-inline CPU milliseconds, median (MAD), in actual execution order:

| Block / order | Process 1 | Process 2 | Process 3 | Process 4 |
|---|---:|---:|---:|---:|
| 0 / ABBA | 86.169 (0.879) | 83.967 (1.138) | 86.874 (1.694) | 83.398 (0.397) |
| 1 / BAAB | 89.649 (0.842) | 81.729 (1.029) | 83.001 (0.800) | 85.330 (0.947) |
| 2 / ABBA | 88.580 (2.459) | 88.693 (0.715) | 160.381 (13.841) | 161.037 (16.517) |
| 3 / BAAB | 105.918 (9.193) | 82.902 (1.108) | 85.084 (0.940) | 85.871 (1.025) |

In block 2, both implementations' later process medians nearly double. In block 3, the two candidate processes themselves differ substantially. Process CPU time removes time descheduled but does not remove frequency, shared-resource, or other execution-rate variability. These observations do not identify the causal mechanism.

## Full matrix

Elapsed milliseconds, median (MAD), 128 statements per retained sample:

| Workload | A1 | B1 | B2 | A2 |
|---|---:|---:|---:|---:|
| large | 75.786 (1.668) | 78.052 (1.169) | 76.372 (0.750) | 77.426 (0.490) |
| multiple | 80.844 (1.205) | 79.987 (0.660) | 79.846 (2.280) | 87.430 (2.288) |
| small FORCE_OUTLINE | 10.952 (0.330) | 11.377 (0.215) | 11.372 (0.116) | 12.466 (0.199) |
| small inline | 10.708 (0.157) | 10.786 (0.313) | 10.958 (0.152) | 11.502 (0.286) |
| unchanged UPDATE | 57.110 (0.272) | 55.691 (0.471) | 55.478 (0.621) | 62.397 (1.771) |
| moving UPDATE | 64.773 (1.021) | 62.213 (0.800) | 62.899 (0.666) | 70.094 (1.224) |
| nonpartitioned large | 76.331 (0.946) | 74.865 (0.896) | 76.313 (1.021) | 84.019 (2.399) |
| nonpartitioned small | 10.002 (0.062) | 9.877 (0.338) | 9.805 (0.383) | 10.910 (0.090) |
| string expression | 48.613 (0.387) | 44.486 (0.667) | 45.831 (1.071) | 52.046 (1.126) |

Baseline drift is again visible, including nonpartitioned controls. These values support reporting workload behavior, not a pooled general speedup. CPU distributions for every workload are reproducible from the summarizer and retained raw samples.

## Evidence and reproduction

- [Fixed-plan runner](ticket06-evidence/repeat-interleaved.py): refuses an existing output directory; do not delete prior evidence to rerun. Choose a new output directory for a future run.
- [Manifest](ticket06-evidence/interleaved-20260909/manifest.json): all 52 commands, timestamps, before/after load, exit status, run order, runner hash and complete console outputs.
- Per-process JSON files in [the evidence directory](ticket06-evidence/interleaved-20260909/) additionally record source diffs, binary/library/test hashes, affinity, private fixture paths and all samples including warmups.
- [Summarizer](ticket06-evidence/summarize-interleaved.py): run with `python3`; requires every planned process to succeed, exact sample counts/order, expected row counts, pinned affinity and matching binary provenance before reporting results. No timing outlier filter.

## Decision and next step

Do **not** mark runtime acceptance green or waive the suspected small-inline regression. No design or engine change is justified solely by this noisy average. The known server lifecycle blocker is unchanged; these SA measurements cannot resolve it.

Recommended next work is a **narrow cost-attribution investigation of small-inline routing**, separating key preparation/codec work and retained routing from SQL/heap overhead, with any profiling/instrumentation authorized separately. This may explain whether there is avoidable added work even when end-to-end timing remains noisy. It is not a substitute for eventual controlled timing on the final candidate. No profiler, extra engine instrumentation, fallback, or preparation refactor was started here.

Subsequent user-authorized next step: [CPU attribution report](ticket06-cpu-attribution-b871ea386-codex.md) now records stable additional instruction work and the extra small-inline routing pass. Runtime acceptance is still not established.
