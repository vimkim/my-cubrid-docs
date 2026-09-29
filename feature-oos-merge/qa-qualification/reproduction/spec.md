# Bounded OOS QA reproduction contract

Status: Confirmed by the user (`yes`) on 2026-09-29; initial build/reproduction batch authorized.
Work item: 217. Date: 2026-09-29.
Decision history: [review.md](review.md). Vocabulary: [CONTEXT.md](CONTEXT.md).

## Objective and boundaries

Reproduce S04 (`cbrd_26354`) under pinned local conditions and distinguish original cardinality symptoms,
other assertion differences, setup failures and missing proof. Acquire available R01 evidence independently.
Direct OOS effects and indirect integration effects are candidates; neither branch identity nor a differential
test result establishes OOS causality. Missing upstream repairs, environment differences and expectation
differences retain separate labels.

This batch prepares exact-source builds and executes diagnostic reproduction. Engine repairs, tracked testcase
changes, answer rewrites, develop synchronization, publication and an RQG runtime campaign are separate work.
Existing integration worktree/installation, dirty AGENTS.md, context repository changes and unrelated CTP edits
are preserved.

## Pins and build topology

| Role | Engine revision | Dedicated worktree (proposed unused path) |
|---|---|---|
| Feature | `1ec35f86c5e43b9ca86d81e202c68899f8ce4f21` | `/home/vimkim/gh/cb/oos-qa-feature-1ec35f8` |
| Develop comparator | `e1c3db19800a0170942cec8b23cac4705efbb6e3` | `/home/vimkim/gh/cb/oos-qa-develop-e1c3db1` |

Verify unused paths/ref names and create dedicated pinned worktrees; preserve all existing worktrees. Each
gets its own build directory and installation. Use the live cubrid-build workflow with the same `debug_gcc`
preset, compiler and effective flags/options. Inspect preset configuration and retain CMake cache/compile/build
records. Record legitimate revision differences such as version labels and pinned submodules. Do not adopt
the current develop installation or equate a matching generated version header with binary provenance.

Build through the live preparation/configure/build recipes. Do not run build-test or unrelated CTest suites.
No engine changes belong to this phase. If an exact-source build fails, preserve its first error and classify
the dependency; repairs or substitutions are not implicit.

## Case, runner and environment

- Supporting private corpus: `1274a4d6462a3d5ae5daeb004e042f89496991d8`.
- Exact case: `shell/_25_unstable/_40_guava/cbrd_26354/cases/cbrd_26354.sh` and its 20 original answers.
- QA deployed corpus/helper SHA remains unknown. Representative queries and expected cards match archived QA;
  claims remain pinned-local comparison reproduction, not complete QA environment equivalence.
- Use cubrid-test-shell-run and cubrid-common's focused contract. Preflight installed source identity, runner
  version/hash, resolved tools/JDK, containment, selected corpus identity/dirt and available storage.
- Execute `TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell -c <attempt-conf>` with one slot and
  `scenario_disk=on`, exact-case list, file feedback, updates/continuation/retries disabled. CTP supplies assets;
  no legacy-runner fallback is implicit.
- Use the same captured CTP base asset snapshot, including recorded pre-existing local modifications, on both
  builds. Observation helper additions are identical, separately diffed and hashed. Preserve source CTP assets.
- Copy engine installation/CTP/HOME for each invocation and rewrite all installation-bound runtime paths.
  Create a fresh empty attempt registry and a fresh testcase DB; preserve any copied registry separately.
- Match effective locale/configuration/ports across revisions and record them. Retain existing policy from the
  inspected shell configuration; do not tune statistics, optimizer or buffer settings to make failures disappear.
- Run sequentially on the same host. Record host/compiler/system state and config differences from known QA
  information. Containment must isolate the testcase's service/process/cleanup operations.

## Initial batch and budget

Run up to three fresh attempts per revision, six total, in paired order:

1. Feature pristine, develop pristine.
2. Feature observation, develop observation.
3. Feature observation, develop observation.

Every attempt executes all 20 subcases. Retain earlier failures/inconclusive attempts. Timeout is 1200 seconds
per attempt, including diagnostics; automatic retries are zero. Before engine execution, identity or containment
failure stops preparation. Stop repeated identical setup failures (two occurrences) and report them. Cores,
timeouts and missing artifacts remain distinct outcomes; cleanup targets only the owned contained attempt.

Release builds, additional attempts, reduced workloads and causal intervention experiments require a follow-up
decision based on the retained initial evidence; they are not hidden retries inside this batch.

## Observation methods

Pristine attempts use the tracked testcase and captured base CTP assets unchanged. Observation attempts use a
disposable, recorded testcase overlay with file-copy additions only, retaining original SQL, hints, statistics
updates, comparisons, answers and cleanup. Copy diagnostics outside the testcase's cleanup scope:

- Original CSQL output before normalization.
- Trimmed unmasked plan before `.raw` deletion.
- Cardinality-restored normalized input supplied to the original comparison.
- Setup/create/start logs and effective engine configuration.

Separately instrument the copied CTP `compare_result_between_files` helper to delegate original comparisons
unchanged. An exact S04 case/final-answer guard invokes diagnostics only after comparison 20 has returned and
before testcase cleanup. Preserve original return status, stdout/stderr and verdict semantics. Do not append new
original testcase assertions. Record overlay/helper diffs and hashes; the runner's patched verdict remains visible.

The additional CSQL session captures stored statistics before queries, then executes read-only data probes:

```sql
;info stats t1
;info stats t2
SET OPTIMIZATION LEVEL 1;
SELECT COUNT(*),
       COUNT(DISTINCT col1), COUNT(DISTINCT col2), COUNT(DISTINCT col3),
       COUNT(DISTINCT col4), COUNT(DISTINCT col5), COUNT(DISTINCT col6), COUNT(DISTINCT col7),
       COUNT(col1), COUNT(col2), COUNT(col3), COUNT(col4), COUNT(col5), COUNT(col6), COUNT(col7)
FROM t1;
SELECT COUNT(*), COUNT(DISTINCT col1), COUNT(DISTINCT col2), COUNT(col1), COUNT(col2)
FROM t2;
```

Setup SQL predicts t1=100000 rows, NDVs (col1–7)=100000,100000,10,4,2,100,500; t2=500 rows,
NDVs (col1–2)=500,500. Non-null counts should equal table row counts. These predictions are independent of
the observed engine output; compare stored estimates with actual data without refreshing statistics.
Original optimization level 514 generates plans without executing queries; these probes verify setup data,
not every original query's logical result. Diagnostic output/status/completeness is recorded separately and
cannot convert an original NOK or missing proof into PASS.

## Evidence and symptom assertions

Prove native exact-case dispatch/completion and verdict-bearing artifacts with the focused helper; exit zero
alone is insufficient. Keep subcase differences as well as total verdict counts.

| Target | Preserved expectation | Archived QA actual | Required interpretation |
|---|---:|---:|---|
| Case 16, swapped driving side, ordered nested-loop, LIMIT 10,1 | card 55 | 11 | Record independently whether the same query/plan assertion and number are reproduced. |
| Case 18, NO_USE_HASH, LIMIT 200000 | card 200000 | 99986 | Record independently whether the same uncapped-LIMIT assertion and number are reproduced. |

Do not treat plan cardinality as an expected returned-row count. Preserve query/plan-path identity and explain
setup/statistics observations. Different actual cards are related assertion observations, not silently called
an exact numeric QA replay. Formatting-only failures, a different plan path, setup errors and incomplete
diagnostics do not close the target reproduction claim.

Feature failure/develop pass establishes a local differential. Both failing, neither failing, unstable outcomes
or inconclusive attempts are retained with their limits; none establishes OOS causality. A later narrowed
feedback loop must reproduce the original symptom before causal hypotheses or code repair. Apply
diagnosing-bugs at execution: this document describes a planned loop, not an already-proved red-capable one.

## Retention

Use `/home/vimkim/tmp/oos-qa-reproduction-1ec35f8/` with a distinct directory per attempt. Retain manifests,
revision/submodule/tool/binary hashes, build records and pointers, effective settings, captured asset dirt,
expected-case list, commands/output/status, native result/feedback/XML logs, raw/trimmed/normalized plans,
diagnostic output and available engine crash reports. Retain copied installation/CTP trees and incomplete
attempts until the user requests cleanup. Redact credentials from displayed/published excerpts.

The testcase still deletes its DB normally. This method does not promise a consistent DB/WAL snapshot.
Original failure signatures and proof gaps remain in compact per-attempt records even if later work succeeds.

## R01 evidence lane

Preserve existing stack/listing evidence and an acquisition manifest for original vacuum core 574686 plus
reader core 575361, matching executable/libraries, same-point DB/volumes/WAL, original testcase/helpers,
corpus SHA, grammar/seed/generated workload and relevant configuration. Missing develop RQG remains unknown.

The saved core links are issue-report endpoints and are not retrieval actions. Current QA credential environment
is absent; no live fetch was attempted. A read-only testcase-view URL exists, but archive access is not established.
When access becomes available, retrieve read-only evidence through its supported route; do not send messages
to others, invoke report-creation endpoints, invent workload assets or start RQG. A runnable R01 method is a
later decision after prerequisites are established. R01 access gaps do not prevent the agreed S04 batch.
