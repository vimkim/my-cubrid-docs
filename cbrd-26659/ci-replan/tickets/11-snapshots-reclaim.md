# 11: Validate real snapshot visibility and observable safe reclaim

**What to build:** Private shell coordinates acknowledged live sessions to prove old/new value visibility and survivor safety, then checks only reclaim progress that product observations can actually establish.

**Blocked by:** 02.

**Status:** ready-for-agent

Definition approved 2026-10-08; testcase implementation is a later phase.

**Parent:** CBRD-26659.

**Coverage and prior art:** R19 and observable R23 subset; R20/R21/R22 remain separately dispositioned. Borrow existing bounded-controller mechanisms without core-only verdicts.

## Acceptance criteria

- [ ] Select a documented isolation/snapshot mode and keep the real reader transaction open while a writer updates/deletes distinct OOS values. Acknowledge barriers, commits and reads; compare exact intended old and new values.
- [ ] Use condition-based waits with scenario-specific deadlines and a failing timeout verdict. Preserve session output/error/exit records; a blocked writer or terminated controller cannot become OK.
- [ ] For reclaim credit, prove eligibility and controlled quiescence plus positive prior OOS state, stable physical observations and exact live survivors. SHOW can undercount busy pages; a racing zero cannot establish cleanup.
- [ ] Where normal daemon/log progress supports a compact repeated-churn or restart-debt subset, assert the independently justified physical plateau/drain rather than unit-only cursor/hint behavior.
- [ ] Keep the correct UPDATE→ROLLBACK→vacuum→read oracle visible for CBRD-27237 and accepted CBRD-27230, without claiming immediate rollback covers it. Missing product trigger/completion or an observed engine failure remains an explicit disposition.
- [ ] Same-slot retry identity, forced latch loss and exact growth cursor/horizon internals require reachable deterministic evidence; otherwise retain their unit/capability gap without verified credit.

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
