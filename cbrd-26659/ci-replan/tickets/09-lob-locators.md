# 09: Validate external LOB locator and copy independence

**What to build:** Public LOB cases and private file-lifecycle phases preserve independently known external contents and prove legal locator demotion/copy behavior without confusing adjacent large VARBIT with locator coverage.

**Blocked by:** 01, 02.

**Status:** ready-for-agent

Definition approved 2026-10-08; testcase implementation is a later phase.

**Parent:** CBRD-26659.

**Coverage and prior art:** R08 and relevant type/copy behavior. Reuse P02 and accepted LOB-locator ADR; legacy max-column errors are negative controls only.

## Acceptance criteria

- [ ] Reuse neighbor/copy checks but add a legal locator-heavy or accepted-policy fixture whose physical discriminator identifies actual locator demotion. Independently derive legal row/stub/locator sizes.
- [ ] Compare independently prepared BLOB/CLOB content and every copied value after deleting/dropping the source; keep external-file lifecycle controlled by the shell case where SQL cannot own it safely.
- [ ] Ensure copied content survives the relevant source cleanup without assuming OOS owns external LOB deletion. Capture actual path/ownership constraints and restore/delete only fixture-owned files.
- [ ] Retain max-column rejection and sparse-success compatibility as qualified controls, avoiding duplicated legacy workload or false successful locator credit.
- [ ] If a required current route hits the noted workspace/external-LOB baseline defect, preserve the intended oracle and explicit issue/capability disposition. Do not silently replace it with neighboring VARBIT placement.

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
