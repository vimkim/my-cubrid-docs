# 10: Validate committed crash durability and uncommitted undo

**What to build:** Private shell cases journal acknowledged transaction outcomes, crash a contained owned server and verify exact recovered committed contents and undone uncommitted changes through separately asserted scenarios.

**Blocked by:** 02.

**Status:** ready-for-agent

Definition approved 2026-10-08; testcase implementation is a later phase.

**Parent:** CBRD-26659.

**Coverage and prior art:** R17/R18. Reuse historical durability value-checking mechanisms and current recovery units, replacing obsolete layout/process assumptions.

## Acceptance criteria

- [ ] Use distinct single/multichunk committed values and externally recorded commit acknowledgement. Prove OOS activation before the crash; verify every committed row exactly after bounded restart.
- [ ] In a separately named scenario, keep a persistent transaction open after an acknowledged uncommitted INSERT/UPDATE/DELETE barrier, crash, and verify absent inserts plus restored committed pre-images.
- [ ] Use a fresh transaction journal to define uncertain acknowledgement handling before running; never classify an unacknowledged commit according to whichever state recovery returns.
- [ ] Crash only owned processes under disposable containment. Capture signal/exit behavior, bounded server readiness, recovery evidence and the correct restored state; a graceful restart is not the crash scenario.
- [ ] Total REDO activity or flushed-page survival does not prove a particular OOS recovery index replayed. Obtain discriminating OOS-specific replay evidence where available, or report crash durability and the narrower replay gap separately.
- [ ] A failed scenario stops its dependent phases and preserves evidence; do not copy the long historical campaign harness wholesale or permit a missing diagnostic branch to report a required pass.

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
