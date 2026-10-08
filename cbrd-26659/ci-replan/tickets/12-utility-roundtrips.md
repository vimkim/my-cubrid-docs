# 12: Validate utility and backup round trips

**What to build:** Compact private shell fixtures retain independently modeled values and schema through supported unload/load/compact and backup/restore/check operations, with route-specific OOS evidence.

**Blocked by:** 02.

**Status:** ready-for-agent

Definition approved 2026-10-08; testcase implementation is a later phase.

**Parent:** CBRD-26659.

**Coverage and prior art:** R25/R26. Borrow existing utility/backup mechanisms while replacing huge fixtures, count-only oracles and weak exit-code handling.

## Acceptance criteria

- [ ] Use a compact distinct single/multichunk and useful LOB-neighbor model. Assert all selected values/schema before and after each operation, with exact independent expectations rather than agreement of two possibly wrong databases.
- [ ] Check every unload/load/compact/backup/restore/diagdb/checkdb command succeeds as intended and produces parseable complete artifacts. Return codes beyond1, empty output and warnings never certify success.
- [ ] Prove source and successful destination OOS state for each claimed physical route. Select SA/CS/workspace variants only for distinct accepted behavior; successful SA logical reads with zero OOS are not placement coverage.
- [ ] Keep CBRD-27424 workspace demotion and any route-specific defects explicit. No-logging load/read does not promise WAL recoverability or logged stamp uniqueness.
- [ ] Carry exact acknowledged contents through a destructive restore phase in an owned disposable database. Keep dependent operations independently named and end the attempt if their prerequisite fails.
- [ ] Use current owner/SHOW/checkdb facilities; database-wide spacedb OOS-row separation is a separate proposal, not a prerequisite. Record the actual operation/profile costs and cleanup footprint.

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
