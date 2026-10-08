# 05: Validate transaction and rejected-DML atomicity

**What to build:** Public cases prove that commit, rollback, savepoints and rejected writes preserve the independently intended rows and schema, including legal and illegal OOS/bigone neighbors.

**Blocked by:** 01.

**Status:** ready-for-agent

Definition approved 2026-10-08; testcase implementation is a later phase.

**Parent:** CBRD-26659.

**Coverage and prior art:** R10, R11 and constraint subset of R12. P07/P08 and current transaction/bigone units are prior art.

## Acceptance criteria

- [ ] Reuse transaction/constraint cases and add INSERT/UPDATE/DELETE rollback, multichunk pre-images, savepoint preservation and successful follow-up writes after rejection.
- [ ] Check PK/secondary UNIQUE, NOT NULL and supported CHECK failures with intended statement-level cancellation and untouched survivor values; keep a positive eligible fixture separate from NULL-only failures.
- [ ] Include rejected OOS-plus-bigone INSERT and UPDATE with no partial change, ordinary non-OOS bigone success and a legal residual slotted-record control. Derive the intended error symbol and expected state before execution.
- [ ] Review current symbolic/numeric error identity and effective client/unique-error configuration against the pinned source. CBRD-27403 and old -1375/-1382 answers are historical drift, not approved expectations for the current source.
- [ ] Credit immediate single-session atomicity only. Aborted UPDATE followed by vacuum remains R20/CBRD-27237 and cannot be closed by this ticket.

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
