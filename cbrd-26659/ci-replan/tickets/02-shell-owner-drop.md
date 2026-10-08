# 02: Prove one shell OOS owner-file lifecycle case end to end

**What to build:** A compact private shell regression positively identifies an owned OOS file before DROP, checks its removal and an independent survivor, and proves the native verdict and cleanup path.

**Blocked by:** None (can start independently after approval).

**Status:** ready-for-agent

Definition approved 2026-10-08; testcase implementation is a later phase.

**Parent:** CBRD-26659.

**Coverage and prior art:** R16 observable diagnostic subset and R24; physical companion baseline for R01. Current cbrd_26527 is prior art, not a ready-made narrow case.

## Acceptance criteria

- [ ] Prepare or reuse a verified clean optdebug install in a disposable contained attempt. This ticket does not depend on the SQL ticket or its JDBC preparation; record actual source/install/configuration identity.
- [ ] Reduce the current owner-descriptor DROP mechanism to an inline-only no-file control, deliberately eligible distinct VARBIT writes, positive class/OOS-file/chunk evidence, DROP and a surviving-table value control. Check each utility and DML exit status.
- [ ] Match diagnostic fields by names and class identity, retain relevant file ownership before DROP, and fail on missing/empty/error parses. A failed post-DROP command is never evidence that a file disappeared.
- [ ] Use bounded startup/readiness and process ownership under containment; explicitly prove normal and failed-attempt cleanup. Do not copy the historical broad PID-kill scope or large default fixtures.
- [ ] Demonstrate an intentionally wrong assertion or empty parse produces a failed artifact verdict in a disposable validation attempt; restore the real assertion and prove an actual non-skip pass.
- [ ] Record the matching SQL-fixture parameters, source, page/mode and any interface difference. This proves the shell fixture, not physical observation of the separate public SQL run; expose only a small reusable observer if later cases need it.

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
