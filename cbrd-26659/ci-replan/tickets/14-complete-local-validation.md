# 14: Validate the complete delivered SQL and shell sets locally

**What to build:** A final reproducible local receipt reconciles every delivered case with coverage, proves the complete SQL set and shell set pass with correct expectations, and reports separate whole-suite timing and remaining gaps.

**Blocked by:** 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13.

**Status:** ready-for-agent

Definition approved 2026-10-08; testcase implementation is a later phase.

**Parent:** CBRD-26659.

**Coverage and prior art:** All delivered subsets from tickets 01–13; all 31 inventory dispositions, including agreed HA and deferred CDC boundaries.

## Acceptance criteria

- [ ] Freeze exact delivered SQL and shell case lists from reviewed task revisions and reconcile every list entry and asserted coverage item. Tickets 01/02 are prerequisites transitively through later tickets and remain included in this validation.
- [ ] Recheck source/install/dependency/runner identities and explicitly recorded optdebug/JDBC/page/mode/parameter settings. Additional selected configurations are named and justified; no automatic release/page-size matrix is invented.
- [ ] Run the entire selected SQL set and entire selected shell set separately with the native contained workflow. For several invocations, verify every group and report elapsed sums plus invocation count; do not extrapolate from a representative sample.
- [ ] Verify exact positive executed identities and verdict-bearing summaries/results/logs, every required assertion, zero selected failures/skips and owned cleanup. Include relevant failure/negative-control history without pretending it belongs to the clean final pass.
- [ ] Report SQL whole elapsed and shell whole elapsed separately from body timers and preparation/build/download overhead. About 10 minutes per suite is informal guidance; any expensive useful group has its measured cause, optimization and coverage tradeoff documented.
- [ ] Audit repository discovery/helpers/answers/configuration against company conventions. Report remaining native/CTP compatibility limits without running GHA or an implicit CTP fallback; this receipt does not claim the full company corpus is green.
- [ ] Publish an evidence-linked delivery report with exact testcase commits, immutable local evidence identities, pass/skip/failure counts, timing and cleanup. Update all 31 coverage dispositions truthfully; preserve HA, CDC, engine-defect and internal-only gaps.

## Required delivery evidence

- [ ] The delivered cases follow each affected repository's current discovery, helper, answer-format and cleanup conventions; changes are scoped to this behavior and preserve unrelated work.
- [ ] Expected values, errors and assertions are reviewed against an independent fixture/transaction/schema model before accepting actual output; result capture is not golden-answer generation.
- [ ] Each claimed OOS path has positive applicable evidence. Public logical and paired-shell physical claims stay separate, and unsupported ownership, retry, recovery or reclaim claims remain explicit gaps.
- [ ] Validate with the selected local native contained runner and retain exact positive executed identities, source/install/testcase/runner/configuration evidence and passing verdict artifacts; exit0 or a required skip is insufficient.
- [ ] Demonstrate fixture, session, process, database/file and parameter cleanup, including failed/timeout attempts, with ownership boundaries recorded.
- [ ] Record measured testcase and whole-invocation time including runner/test setup and normal cleanup. Unmeasured values and historical projections are labeled; SQL/shell costs stay separate with no hard cutoff.
- [ ] Update the behavior coverage with delivered case/phase identifiers, independent expected result, actual proof scope, local evidence/timing and remaining defect/capability dispositions.

## Evidence context

[Agreed specification](../spec.md), [behavior coverage](../coverage.md), [local validation](../local-validation.md), and the linked current public/private/unit inventories govern this ticket. No engine fix, external publication or GHA run is included.
