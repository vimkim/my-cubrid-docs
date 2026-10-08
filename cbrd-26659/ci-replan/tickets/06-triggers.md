# 06: Validate trigger outcomes with explicit OOS path limits

**What to build:** Public trigger cases prove intended log/mirror, rejection and row outcomes while distinguishing an OOS-positive pre-trigger fixture from client-template writes that bypass OOS.

**Blocked by:** 01, 02.

**Status:** ready-for-agent

Definition approved 2026-10-08; testcase implementation is a later phase.

**Parent:** CBRD-26659.

**Coverage and prior art:** Trigger subset of R12. Conditional reuse of P09 with current source-path reconciliation.

## Acceptance criteria

- [ ] Reuse the pre-trigger fixture and independently model AFTER UPDATE log/mirror effects, BEFORE UPDATE rejection, unchanged rejected values and subsequent valid writes.
- [ ] Keep trigger log rows and final values deterministic and ordered; restore/drop every trigger, mirror and helper even after error paths.
- [ ] Reconcile current trigger/client-template source behavior before crediting triggered INSERT. A correct triggered value with no physical OOS evidence receives logical trigger credit only.
- [ ] Link any matching shell baseline evidence and disclose that it is a separate fixture execution. Do not invent a new engine seam or revise the intended trigger semantics to obtain placement credit.

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

Dependency clarification: the shell starter supplies the positive pre-trigger OOS witness required by this slice. This corrects a missing prerequisite without changing behavior scope.
