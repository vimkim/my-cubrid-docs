# PR7600 timing diagnosis — reproduced; design decision pending

This directory retains the 2026-09-10 Phase 1 feedback-loop work. It is diagnostic evidence, not an acceptance waiver. The working PR remains at `988a4d2fa`; its failing vacuum test stays uncommitted.

## Feedback loop

`stream-loop.py` runs the same SQL fixture against two release engines in private databases. Four live workers (A/B × partitioned/nonpartitioned) alternate short batches on CPU 6. Handshakes and SQL value/physical-owner/rollback assertions are outside the timed interval. Four warmup batches precede retained samples. ABBA/BAAB orders alternate, as does workload order. Every sample is retained; there is no outlier exclusion. The script records source diffs, binary/library/harness hashes, CCI revision, mappings, sample output, and final GTest process status.

Fixed-layout runs use `setarch x86_64 -R` only for these test processes. They do not change global ASLR, frequency policy, CPU scheduling of other users, or shared databases. A/A calibration uses the identical baseline engine on both sides. Ratios are geometric means across paired blocks. The descriptive 99% bootstrap intervals resample groups of four consecutive blocks, with fixed random seed 7600; they do not account for every possible host/process bias.

The current calibrated verdict is RED only if both CPU and elapsed-time lower bounds for small-inline INSERTs exceed the symmetric noise factor from matching A/A calibration: max(upper bound, 1/lower bound, 1). GREEN_WITHIN_AA_RESOLUTION means the entire interval fits within the A/A envelope; it is a diagnostic resolution statement, not full feature acceptance. Other results are INCONCLUSIVE. Nonpartitioned results are reported separately: a shared slowdown is not automatically subtracted away as noise. Calibration requires matching measurement settings and baseline binary/library/harness/CCI identities. The symmetric envelope includes persistent A/A side bias; the interval need not contain 1.

Example already executed (output directories are never overwritten; use a new output basename for each rerun):

```bash
python3 stream-loop.py stream-ab-fixed96-1 \
  --fixtures /tmp/pr7600-stream-ab-fixtures --no-aslr --blocks 96 \
  --calibration stream-aa-fixed96/manifest.json
```

Its timed loop took 14.07 seconds. It returned RED / exit 1: small-inline CPU B/A 1.027165, interval [1.023322, 1.030914]; elapsed B/A 1.027047, interval [1.023179, 1.030841]. A repeat (`stream-ab-fixed96-2`) also returned RED: CPU B/A 1.019425, interval [1.013955, 1.024549]. All four worker processes in each run completed their SQL checks. The nonpartitioned workload also slowed; these results alone do not attribute the difference to the extra routing pass.

These runs use the preserved historical `b871ea386` baseline and pre-format candidate from ticket 06. Rebuilding after adding the interactive harness left the original measurement executable, engine library and original harness hashes unchanged on both sides. Exact merged-head measurements have now completed, using `pr7600-timing-base988` (HEAD `988a4d2fa` with only the effective-key commit's five-file engine diff reversed) and `pr7600-timing-head988` (unmodified engine at that HEAD), both at pinned CCI `bd86063`.

## Failed attempts retained

- `first/`: 24 fresh-process timing runs. Small-inline CPU block ratios 1.031015, 1.013258, 1.010614; same-side drift envelope 1.078291. INCONCLUSIVE.
- `stream-aa1/` and `stream-ab1/`: live workers, normal ASLR. A/A nonpartitioned bias prevents naive interpretation.
- `stream-aa-fixed1/` and `stream-ab-fixed1/`: process-local ASLR disabled; 48 blocks. No calibrated verdict yet.
- `stream-aa-fixed96/`: 96-block A/A calibration. Inline CPU interval [0.995987, 1.006175]; elapsed [0.995860, 1.006119]. The nonpartitioned A/A effect is itself biased, which is why this calibration certifies only the inline diagnostic envelope.

The verdict logic was refined while constructing the loop, before engine hypotheses or fixes. Earlier manifests retain the script hash and verdict produced at their execution; rerunning the current classifier is not a rewrite of those historical observations. No engine optimization has been applied at this stage.

## Completed merged-head diagnosis

See [diagnosis report](../../ticket06-runtime-diagnosis-988a4d2-codex.md) for results, hypotheses, limits and the pending decision. Both matched builds use the pinned CCI commit and identical diagnostic harnesses. The control reverses the effective-key change only, retaining the earlier per-heap ownership fix and merged base. Its associated SQL test/CMake changes were also reversed after the first build exposed references to removed APIs; no production compatibility shims were added.

The key-only regression command already executed twice (new output directory required on rerun):

```bash
python3 stream-loop.py minimal-ab96-repeat \
  --fixtures /tmp/pr7600-head988-ab-fixtures --no-aslr --blocks 96 \
  --baseline pr7600-timing-base988 --candidate pr7600-timing-head988 \
  --binary test_oos_sql_pr7600_minimal \
  --calibration minimal-aa96/manifest.json
```

Output: `RED`, exit 1, CPU ratio 1.023636 [1.020872, 1.026468], elapsed ratio 1.023671 [1.020836, 1.026540], loop 8.51 seconds. All SQL correctness assertions passed. The preceding run was also RED (CPU ratio 1.030198).

`counters/` holds separate whole-process perf measurements in ABBA order, 196 repetitions of 256 inserts, process-local fixed ASLR and CPU 6. These counts include setup, checks and rollback and cannot substitute for timed INSERT results. Invalid initial labels containing underscores were rejected before tests; their logs are retained.

All added harnesses are diagnostic-only: canonical copies live here, with build copies in explicitly named measurement worktrees. They are untracked and are not proposed production tests. There is no engine instrumentation or engine optimization to remove. No source changes were made in the user's working tree.
