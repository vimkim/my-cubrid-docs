# Ticket 06 — effective-key routing measurements

Status: resource benefit demonstrated; runtime acceptance remains inconclusive. This is not final integration acceptance.

## Provenance and method

Baseline: `b871ea386d2c5419b7abae07dda58b9b7f36377a`, original PR #7600, in `/home/vimkim/gh/cb/pr7600-original-baseline`.
Candidate: the same base plus the five engine-file changes from tickets 01–03, in `/home/vimkim/gh/cb/pr7600-measure-candidate`.
The engine diff SHA-256 is `3d978ff8134516d0ab26a809b6fd790bd289a6865476a215921c8fa5e6eea34a`.
Both use `release_gcc` (RelWithDebInfo, GCC, O2/NDEBUG), the same original CCI submodule commit, settings, and byte-for-byte identical benchmark source.
Each evidence JSON records revision, diff, library/binary/cache hashes, build log, private runtime and database paths, commands, outputs, and status.

The [retained harness](ticket06-evidence/test_oos_sql_pr7600_measure.cpp) executes real standalone SQL. It measures SQL compile/execute plus storage work; statement construction, setup, validation, commit/abort and shutdown are outside the interval. Both process CPU time and steady-clock elapsed time are recorded. Each batch is rolled back; committed UPDATE seeds are checked again afterward. These measurements do not model concurrent server MVCC/vacuum.

Nine workloads: 64,000-byte uncompressed VARBIT non-key payload; two 32,000-byte OOS candidates; 64-byte FORCE_OUTLINE; 4-byte inline; unchanged-key and partition-moving 32,000-byte UPDATE; large/small nonpartitioned controls; and a VARCHAR key routed by LENGTH. The data do not use string compression for large payloads.

Every batch verifies complete payload values and keys, root/child OOS ownership, and physical chunk counts. SHOW counts physical records/chunks, not logical value chains. The harness asserts its chosen lengths cannot straddle a chunk boundary due to the VARBIT length prefix. SA eager cleanup explains why UPDATE owner counts do not retain both old and new chains. The initial failed smoke fixtures are retained and are not performance evidence.

## Resource observations

Separate debugger runs use the same release binaries and workload. Debugger-wrapped times are never used as timing evidence. The [observer](ticket06-evidence/count-routing.gdb) counts transformations, column-writing attempts, routing, OOS batches and serialization. It tracks record-buffer malloc, OOS payload malloc, private allocations made under locator force, and copy-area **leases**, including their release and simultaneous live bytes.

These are scoped resource measurements, not process RSS or an exhaustive malloc profiler. Copy-area leases can come from a cache; leased bytes must not be called fresh malloc bytes. Untracked STL allocations, allocator metadata, and internal codec memcpy operations are not included. The explicit grown-record memcpy and probe serialization volumes are reported separately, not conflated.

Warm diagnostic repetition; each row below is **two writes**, not one:

| Workload | Full transforms A → B | Record-buffer malloc bytes A → B | Explicit grown-row memcpy bytes A → B | Tracked temporary peak A → B |
|---|---:|---:|---:|---:|
| large | 4 → 2 | 128120 → 0 | 128088 → 0 | 129596 → 96800 |
| multiple | 4 → 2 | 128144 → 0 | 128112 → 0 | 145992 → 96808 |
| small forced | 4 → 2 | 0 → 0 | 0 → 0 | 16680 → 16680 |
| small inline | 2 → 2 | 0 → 0 | 0 → 0 | 16680 → 16680 |
| unchanged UPDATE | 4 → 2 | 64112 → 0 | 64096 → 0 | 113896 → 97488 |
| moving UPDATE | 4 → 2 | 64112 → 0 | 64096 → 0 | 113896 → 97488 |
| nonpartitioned large | 2 → 2 | 0 → 0 | 0 → 0 | 96696 → 96696 |
| nonpartitioned small | 2 → 2 | 0 → 0 | 0 → 0 | 16384 → 16384 |
| string expression | 4 → 2 | 64144 → 0 | 64112 → 0 | 81224 → 64800 |

Final OOS payload serialization and insert-many batch counts are unchanged in each workload. Large: 128016 serialized bytes and two batches on both sides. Multiple: 128032 bytes and two batches. Integer effective keys add eight codec bytes for two rows; the string-expression case adds 32. Unchanged-key UPDATE adds 208 private-allocation bytes; string keys add 52. No tracked allocation/lease remains outstanding at batch end. These observations do not prove absence of every possible leak.

Both early and downstream routing remain counted. The candidate has no complete inline probe. Small inline rows still need one real transform, so they do not share the double-transform saving.

Column-writing attempts equal full-row transforms in all these diagnostic batches: no natural buffer retry was observed. Ticket04 separately forces and verifies retry behavior; those fault-injected timings are not part of the performance comparison.

[Resource summarizer](ticket06-evidence/summarize-resources.py) validates successful executions and no observation errors. Accepted resource inputs: [baseline](ticket06-evidence/baseline-diagnostic-final.json) and [candidate](ticket06-evidence/candidate-diagnostic-final.json), both rerun with the identical final observer, whose complete contents and hash are embedded in each JSON. An earlier candidate observation could not read an optimized-out scalar; it is retained as an invalid diagnostic attempt, not silently counted as zero.

## Timing and noise

First sequence: A1, B1, B2, A2; 128 statements/sample; two warmups and nine retained samples per workload per process. Times are milliseconds, median (median absolute deviation):

| Workload | A1 | B1 | B2 | A2 |
|---|---:|---:|---:|---:|
| large | 74.650 (0.760) | 64.784 (0.570) | 74.105 (1.105) | 65.392 (0.832) |
| multiple | 80.309 (1.014) | 66.992 (0.912) | 74.601 (0.918) | 67.939 (0.704) |
| small forced | 11.478 (0.170) | 11.716 (0.205) | 11.076 (0.297) | 9.683 (0.144) |
| small inline | 10.260 (0.081) | 11.400 (0.214) | 10.389 (0.260) | 8.971 (0.034) |
| unchanged UPDATE | 54.493 (0.219) | 53.198 (0.946) | 52.821 (0.776) | 48.323 (0.327) |
| moving UPDATE | 64.058 (0.969) | 62.581 (0.920) | 61.290 (1.191) | 54.944 (1.200) |
| nonpartitioned large | 78.810 (1.375) | 74.202 (0.663) | 74.851 (0.332) | 62.455 (0.536) |
| nonpartitioned small | 10.172 (0.130) | 9.231 (0.147) | 10.014 (0.131) | 8.281 (0.196) |
| string expression | 45.202 (0.529) | 46.645 (2.292) | 43.650 (1.205) | 39.600 (1.083) |

Between-process drift substantially exceeds within-process MAD. Pooling these into a single claimed speedup/slowdown would be misleading.

The [control repeat](ticket06-evidence/repeat-controls.py) pins CPU 6, uses 1024 statements/sample, two warmups and eleven samples in ABBA order:

| Control | A1 | B1 | B2 | A2 |
|---|---:|---:|---:|---:|
| small inline | 80.123 (1.038) | 82.571 (1.127) | 87.429 (0.440) | 82.915 (1.381) |
| nonpartitioned small | 72.500 (1.349) | 78.448 (1.801) | 76.266 (1.203) | 80.222 (1.152) |
| small forced | 90.928 (2.833) | 92.429 (1.913) | 89.317 (1.349) | 96.685 (0.663) |

Small inline remains a suspected regression; the other controls also drift or change ordering. CPU pinning alone did not make the environment sufficiently stable to assert equivalence or attribute a precise slowdown. No repeatable regression has been waived. Raw CPU times remain in every sample alongside elapsed time.

## Acceptance and next proof

- Mechanism/resource benefit: demonstrated for large OOS-producing writes; smaller/inline/control cases reported separately.
- Logical values, ownership and rollback during these measurements: passed.
- Runtime no-regression gate: **inconclusive, unmet**, not green by default. Repetition on a quieter host or additional interleaved process-level samples remains needed.
- Whole-process peak and exhaustive copying: not measured; reported metrics have the explicit scope above.
- Server lifecycle: still blocked by CBRD-27237, independently of these results.
- No engine change, fallback, downstream-routing removal, or design waiver was made for measurement. Final integrated-revision acceptance requires affected comparisons to be repeated.

Handoff formatting note: the main branch commit hook later normalized whitespace in the previously changed engine signatures/calls. The post-format engine diff hash is `8ccb237954a348b5bef6f1b653dbe44e31816ba5c21d3b856f0d0c33684a215c`. Whitespace-insensitive contents are unchanged; the benchmark worktree, binaries and recorded measurement hash above were not rewritten. These measurements identify the pre-format candidate exactly, not an unmeasured final integration revision.

2026-09-09 follow-up: [52 additional same-host interleaved runs](ticket06-interleaved-b871ea386-codex.md) all passed correctness checks, but runtime acceptance remains inconclusive. Small-inline CPU block ratios range from 0.9986 to 1.1355; system load rose from 2.64 to 64.93. No slowdown was waived. The follow-up recommends scoped cost attribution rather than more unqualified averaging.
