# 04: Validate UPDATE and DELETE state transitions

**What to build:** Compact public DML regressions preserve exact values and survivors across inline/OOS, size and NULL transitions, with paired shell evidence for any claimed physical transition.

**Blocked by:** 01, 02.

**Status:** ready-for-agent

Definition approved 2026-10-08; testcase implementation is a later phase.

**Parent:** CBRD-26659.

**Coverage and prior art:** R09 and DML aspects of R01/R05. Reuse P05/P06; accepted chain-reuse gap R21 remains distinct.

## Acceptance criteria

- [ ] Reuse and reduce existing UPDATE/DELETE cases with inline-to-large, large-to-inline, single-to-multiple chunks, shrink/grow, NULL/empty, repeated writes, predicate/join/subquery UPDATE and delete/truncate/reinsert controls.
- [ ] Use a row/column model that checks every affected value and untouched survivor with ordered exact outputs and independent digests. Distinct source rows must not alias or interchange.
- [ ] For physical transition claims, deliver the appropriate shell companion phase before cleanup and compare the intended state under recorded configuration. Value equality alone does not prove re-inlining or reclamation.
- [ ] Include inline-only attribute assignment, equal-value assignment and genuinely unassigned OOS attributes as distinct logical operations. Do not freeze always-new-chain behavior into golden expectations.
- [ ] Record CBRD-27230 reuse/commit-notification as an accepted unimplemented contract unless exact-source physical evidence closes it. Immediate DML success receives no ownership/reclaim credit.

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
