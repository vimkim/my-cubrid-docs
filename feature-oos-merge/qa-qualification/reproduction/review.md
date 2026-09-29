# OOS QA reproduction interview

Status: Rounds 1–3 accepted; final shared understanding confirmed by the user (`yes`).
Work item: 217. Interview date: 2026-09-29.

## Authority and evidence

- User handoff: [handoff.md](handoff.md).
- Retained reports: `/home/vimkim/gh/my-cubrid-docs/feature-oos-merge/qa-qualification/README.md`.
- OOS specification: `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md` and applicable accepted ADRs.
- Integration policy: [published integration contract](../README.md#integration-contract).
- Vocabulary: [CONTEXT.md](CONTEXT.md).

This is a session decision record, not a replacement OOS specification or another QA analysis report.
Tests, builds, engine/testcase changes and answer rewrites remain outside execution authority until the
complete reproduction method is agreed and the user confirms shared understanding.

## Round 1 — accepted

User response: `1 - recommended / 2 - recommended / 3 - as recommended`.

1. S04 (`cbrd_26354`) is the first runtime target to design. R01 (`dead_data_03_big_record`) is an
   evidence-acquisition lane. Selecting R01 does not authorize an invented substitute workload.
2. Investigate direct OOS effects and indirect effects of OOS integration. Separate cause labels:
   direct, indirect, missing upstream repair, environment difference, expectation difference and unresolved.
   Feature-only failure alone does not prove OOS causality.
3. Compare original feature `1ec35f86c5e43b9ca86d81e202c68899f8ce4f21` against original develop QA baseline
   `e1c3db19800a0170942cec8b23cac4705efbb6e3` before any synchronized-baseline comparison. Each build uses
   a fresh database and the same selected testcase/configuration; preserve both source identities.

## Round 2 — accepted

User response: `all recommended` (Q4–Q8).

4. Use pinned local private corpus `1274a4d6462a3d5ae5daeb004e042f89496991d8` first. Describe outcomes as
   a comparison reproduction under pinned local conditions, not exact QA environment replay; QA deployment
   corpus/helper identity remains unknown.
5. Build both exact original engine revisions separately on the same host with matched GCC/debug_gcc
   settings. Execute native shell in one contained slot with fresh databases per attempt and identical
   effective configuration/CTP asset snapshot. Consider release extension only after debug results.
6. First attempt for each revision runs the pristine testcase. Later observation attempts may use a
   disposable overlay patch that only copies diagnostics. Preserve SQL, hints, statistics updates, comparisons,
   answers and cleanup. Record pristine and patched verdicts separately; tracked testcase files stay untouched.
7. Run all 20 subcases and judge cases 16/18 individually. Preserve expected cards 55/200000. Actual
   11/99986 matches the archived numeric symptoms; other values are separate observations of the same
   assertion. Setup failures, different plan paths and formatting-only differences do not prove reproduction.
   Feature failure plus develop success establishes a local differential, not OOS causality by itself.
8. Initial budget is at most three attempts per revision, six total: first pristine and later observation
   attempts. Each uses fresh DB/attempt. Timeout is 1,200 seconds per attempt; automatic retries are disabled.
   Retain timeout/core/missing-evidence outcomes separately and stop execution on repeated identical setup failure.

### Round 2 — build topology clarification

User requested different worktrees for CUBRID builds. Use two dedicated worktrees pinned respectively
to `1ec35f86c5e43b9ca86d81e202c68899f8ce4f21` and
`e1c3db19800a0170942cec8b23cac4705efbb6e3`. Each has its own build directory and installation.
Preserve the current integration worktree and its existing installation; do not switch or rebuild it as
one of the comparator environments. Keep GCC/debug settings and asset snapshots matched across the two.

## Known method prerequisites

- Local supporting private corpus is `1274a4d6462a3d5ae5daeb004e042f89496991d8`; deployed QA corpus SHA
  remains unknown. Exact QA replay and reproduction with the supporting corpus must be distinguished.
- S04 has 20 subcases and retains numeric top-level cardinality deliberately. Cases 16 and 18 show
  expected/actual `55/11` and `200000/99986` in archived QA evidence. All existing assertions stay intact.
- S04 creates 100,000-row t1 and 500-row t2, updates t1 statistics with fullscan and t2 statistics without
  fullscan, and runs subcases in separate CSQL sessions. Its cleanup deletes temporary raw plans and logs.
- Focused native shell execution requires containment, one slot, a disposable scenario overlay, copied
  engine/CTP/home, exact-case dispatch and verdict-bearing artifacts. Engine/testcase provenance is recorded.
- R01 local evidence currently consists of stack and archive-listing text; exact workload, seed, core memory
  and WAL bundles are missing. Develop has no completed RQG comparator.
- R01 saved core links open an issue-report endpoint, not an archive download. Do not invoke that endpoint
  to acquire evidence. The read-only testcase-view URL is known, but the current session lacks both QA
  credential environment values; no live fetch was attempted. Archive-access routing remains unresolved.
- S04's native worker captures case files after execution, so `case_logs=all` cannot retain already-deleted
  plans. The runner supports explicitly recorded disposable `case_patch_dir` overlays; whether to allow a
  copy-only observation overlay is a pending user decision.
- The live shell configuration timeout is 1,200 seconds. The focused helper overrides retries to zero and
  slot count to one. Existing CTP assets have local modifications; their exact hashes/diff must be recorded
  and the same asset snapshot used across comparisons.
- Existing develop worktree/install identities do not match `e1c3db1`. The feature debug version label
  matches `1ec35f8`, but source/install equivalence and actual build configuration require verification.
  Matched comparison builds should be pinned separately; none has been launched in this interview.

## Round 3 — accepted

User response: `all recommended` (Q9–Q10).

9. In observation attempts, add a bounded separate read-only CSQL session after all 20 original comparisons
   and before cleanup. Instrument only the attempt's copied CTP helper; preserve every original comparison's
   output, return status and verdict. Fetch stored statistics first, then execute row/NDV/null counts at
   optimization level 1. Keep diagnostic completeness separate from testcase verdict. This explicitly extends
   the accepted observation scope beyond copying files; the testcase overlay itself remains copy-only.
10. Retain every original, observed and incomplete attempt at
    `/home/vimkim/tmp/oos-qa-reproduction-1ec35f8/` until user-requested cleanup. Retain identity/build/config/helper
    provenance, raw plans, native verdicts, diagnostics and available crash evidence. Preserve testcase DB cleanup;
    consistent DB/WAL snapshot retention is not guaranteed by this method.

## Final confirmation — accepted

User response: `yes`. The complete `spec.md` contract is accepted, including preparation of two separate
worktrees, matched builds and the initial S04 reproduction batch. Execution is now authorized within that scope.

## Confirmation history

- All initial S04 method decisions are settled. Present `spec.md` as the complete execution contract and obtain
  final confirmation of shared understanding before preparing worktrees, building or executing the runtime batch.
- R01 runtime prerequisites remain deferred: archive-access route -> matching binary/core/DB/WAL and corpus/seed
  availability -> a separately agreed reproduction method. No RQG runtime belongs to the initial S04 batch.

## Round 3 method detail — accepted

Q9 proposes a separate bounded diagnostic CSQL session after comparison 20 and before original cleanup,
only in observation attempts. The copied CTP helper delegates every comparison unchanged and records
original output/return/verdict semantics. An exact S04 guard invokes diagnostics only after its final comparison.
This is an explicit addition to the copied harness, separate from the already accepted copy-only testcase overlay.

The session first captures `;info stats t1` and `;info stats t2`, then uses optimization level 1 to execute
read-only counts/NDVs/null counts. The original testcase uses level 514 (detailed plan without query execution),
so its plan assertions alone do not verify logical query outputs. Source setup predicts t1=100000 rows,
NDVs (col1–7)=100000,100000,10,4,2,100,500; t2=500 rows, NDVs (col1–2)=500,500. Compare actual data
with these predictions and recorded statistics; do not refresh the statistics to make an estimate match.
Record diagnostic status separately from all original testcase verdicts; diagnostic failure is missing proof,
not a replacement assertion or a PASS. Keep collection within the existing 1200-second attempt deadline.

Q10 proposes retaining every pristine/observation/incomplete attempt under
`/home/vimkim/tmp/oos-qa-reproduction-1ec35f8/`, with an attempt manifest, pinned identities and hashes,
build/effective config/asset provenance, commands/status, native verdict artifacts, copied raw/trimmed/normalized
plans, diagnostic output and available engine crash evidence. Preserve all generated evidence until the user
requests cleanup. Copied install/CTP trees are included; approximate six-copy cost is 2.9 GiB before DB/logs/builds.
The testcase's normal DB cleanup remains intact; a consistent database/WAL snapshot is not promised by this
method. Build logs/manifests remain in the two dedicated worktrees with stable pointers from attempts.

Routine documentation uses this scratch directory for decisions/specification and the root CONTEXT.md only
for settled glossary terms. An ADR is created only if a later decision meets the domain-modeling criteria.

## Bounded execution result — 2026-09-29

Work item 218: separate exact-source debug_gcc builds completed, then all six agreed S04 attempts completed.
Feature case16/18=11/99986 in 3/3 attempts; develop=11/100000 in 3/3. All20 subcases executed per attempt;
feature3OK/17NOK, develop7OK/13NOK. Observation setup row/NDV/non-null probes passed in all4 sessions.
Heap objects/pages, NDVs and B-tree cardinalities matched, but some index page counts varied.
Native focused verification failed because discovery counted21 out-of-selection macro skips; all six JUnit
XML files also contained invalid UTF-8 bytes. Original artifacts and proof gaps were preserved unchanged.
R01 acquisition prerequisites remain unavailable; no RQG run or repair/answer rewrite was performed.
Full report: `/home/vimkim/gh/my-cubrid-docs/feature-oos-merge/qa-qualification/s04-reproduction_1ec35f8_codex.md`.
Retained artifacts: `/home/vimkim/tmp/oos-qa-reproduction-1ec35f8/summary.json` and per-attempt trees.
