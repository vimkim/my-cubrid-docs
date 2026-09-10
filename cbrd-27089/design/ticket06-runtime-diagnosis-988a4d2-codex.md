# PR7600 small-row runtime diagnosis — 988a4d2 / Codex

Measured on 2026-09-10. **The small non-OOS INSERT slowdown is reproducible on the merged PR head. The performance acceptance gate remains open.** No engine fix, source commit or acceptance waiver was made. The failing vacuum test remains uncommitted.

## Controlled comparison and feedback loop

Candidate: unmodified engine at `988a4d2fa258222aef792a2a6afde9641b8c5228`. Control: that same head with the effective-key commit's engine changes reversed, preserving the preceding per-heap ownership fix and merged base. The associated test/CMake changes were reversed to compile against the old API. Both use pinned CCI `bd86063a5bd481f0e22bf07c8a76bf736f86443a`, GCC 11.5.0, and matching RelWithDebInfo compilation (`-O2 -ggdb3 -DNDEBUG -finline-functions`). Source diffs, build configuration and artifact hashes are retained in [evidence](ticket06-evidence/diagnosis-20260910/README.md).

The agent-runnable loop executes actual standalone SQL INSERTs in private databases. Four live workers alternate partitioned/nonpartitioned A/B batches in ABBA/BAAB order on CPU 6. Process-local ASLR disabling and matching A/A calibration reduce layout/order noise. Every observation is retained. Timing excludes SQL construction, handshakes, assertions and rollback. Workers validate values, counts, physical OOS ownership and rollback. CPU and elapsed-time lower bounds must exceed the full symmetric A/A envelope for RED. Intervals are descriptive 99% grouped bootstrap intervals, not a guarantee against all host bias.

The minimized loop takes approximately 8.5 seconds. Its exact executed command and output are in the evidence README. Exit 1 denotes the performance regression; all worker correctness tests passed.

## Reproduction and minimization

Starting with `(id INT, k INT, a BIT VARYING)` and a four-byte inline payload, remove the payload column first, then remove id. Re-run matching A/A and A/B after each change. The final data table is `(k INT)` with two range partitions and repeated `INSERT ... VALUES (11)`. A batch of 256 rows is retained for measurement resolution; this is a minimized schema, not a claim that every batch/control parameter is logically indispensable. Removing partitioning leaves a smaller shared slowdown, so it is an explanatory control rather than an all-green negative control.

| Case | Partitioned CPU change | Descriptive interval | Nonpartitioned CPU change | Verdict |
|---|---:|---:|---:|---|
| Original inline case, run 1 | +1.70% | [+1.33%, +2.04%] | +1.47% | RED |
| Original inline case, run 2 | +2.12% | [+1.78%, +2.45%] | +1.19% | RED |
| Remove binary payload | +1.21% | [+0.51%, +1.95%] | +1.27% | RED |
| Remove id; key only, run 1 | +3.02% | [+2.81%, +3.23%] | +0.72% | RED |
| Key only, run 2 | +2.36% | [+2.09%, +2.65%] | +0.75% | RED |

Elapsed-time verdicts agree with CPU verdicts. Matching A/A symmetric CPU noise factors were 1.010026 for the original merged-head case, 1.004467 without the payload, and 1.004502 for the key-only case. The key-only partition/nonpartition ratio was +2.29% and +1.60%, with intervals above zero in both repeats. This does not justify subtracting the entire nonpartitioned difference from the user-visible slowdown.

## Ranked hypotheses and probes

The following predictions were presented before counter probes:

1. Additional effective-key preparation/early routing causes extra work: partitioned inserts should gain substantially more instructions than nonpartitioned inserts.
2. Shared execution or code-layout effects contribute: nonpartitioned inserts should gain instructions or cycles per instruction.
3. Measurement bias dominates: equivalent-engine A/A runs should show a similar difference, or reversal of execution order should reverse the result.

A separate perf-stat ABBA comparison used the key-only harness, 196 repetitions of 256 rows per process, CPU 6 and fixed process-local ASLR. All eight processes passed. [Raw counters and ratios](ticket06-evidence/diagnosis-20260910/counters/summary.json) cover the **whole SQL test process**, including initialization, verification and rollback, not only timed INSERT calls.

| Workload | Instructions | Cycles | Cycles per instruction |
|---|---:|---:|---:|
| Partitioned key-only | +1.093% | +1.873% | +0.772% |
| Nonpartitioned key-only | +0.015% | +0.572% | +0.557% |

Hypothesis 1 is supported for additional work; hypothesis 2 is supported for a smaller execution-cost contribution without meaningful extra instruction count in the nonpartitioned path. The exact microarchitectural cause of that contribution is unresolved. Hypothesis 3 alone does not explain repeated timing RED beyond matching A/A envelopes and the partition-specific instruction increase. These observations do not prove one function accounts for the entire measured regression.

Source corroboration: `src/transaction/locator_sr.c:7773` routes partitioned operations by attrinfo before full row preparation, then calls final force with the expected destination. The nonpartitioned branch retains the ordinary transformation wrapper. This is consistent with the accepted retained-final-route design and the earlier [instruction attribution](ticket06-cpu-attribution-b871ea386-codex.md). No final routing was bypassed as a diagnostic shortcut.

## Decision and remaining work

The [accepted ADR](../../docs/adr/0001-pr7600-effective-key-routing.md) explicitly says that a reproducible slowdown beyond measured noise on small non-OOS or nonpartitioned controls requires a new tradeoff decision. This condition is now met. A concrete choice is required: accept the measured small-row cost for the previously demonstrated reduction in temporary work on OOS rows, or reopen the design/optimization work while retaining correctness requirements. Removing final independent routing, destination reuse, and a broad preparation split are not silently authorized fixes.

Recommendation: keep the performance gate open and reopen optimization/design work before accepting the cost. The evidence does not establish an optimal replacement design. A scoped optimization must pass this key-only regression loop and the original inline loop, plus semantic/ownership tests; an instruction-count improvement alone will not close the gate.

Optional unused two-pass API/test-duplication cleanup is deferred until this direction is settled, so it cannot obscure the measured comparison or be presented as a performance fix. The CBRD-27237 issue remains open and its local worktree has no engine fix; server lifecycle/vacuum and integrated acceptance remain blocked by that separate dependency. No repair of that unrelated defect was attempted.

## State and reproducibility

The original review and PR summary comment remain published. This diagnosis is retained locally; no new PR comment or push was performed in this resumed no-push work item. The user's source tree was preserved, including the uncommitted failing vacuum regression and CCI drift. Fresh diagnostic worktrees use the correct pin and isolate all new harnesses. Diagnostic-only scripts and canonical harnesses live in the clearly marked evidence directory; there are no temporary engine logs or production source probes. The regression remains RED: Phase 5 fix verification and Phase 6 successful-repro closure are not claimed.
