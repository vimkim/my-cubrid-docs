# 03: Validate representation and discriminating chunk boundaries

**What to build:** Public logical checks and narrow delivered shell observers establish profitable-value, largest-first and chunk behavior with distinct bytes and independent physical expectations.

**Blocked by:** 01, 02.

**Status:** ready-for-agent

Definition approved 2026-10-08; testcase implementation is a later phase.

**Parent:** CBRD-26659.

**Coverage and prior art:** R02, profitable-floor subset of R03, R04, R05 and relevant R07 types. P01/P04 and current boundary/identity units are prior art.

## Acceptance criteria

- [ ] Derive serialized value lengths, record overhead and chunk boundaries independently for the chosen layout. Use the current 24-byte stub/header, not old 16-byte checker sums or nominal string length.
- [ ] Cover unequal candidates where one demotion suffices, inline controls, NULL/empty, non-byte-aligned VARBIT, many attributes/VOT-width transitions and distinct head/middle/tail chunk patterns. Do not assert an unspecified equal-size tie order.
- [ ] Deliver quiescent discriminating physical phases using the shell observer: independently expected selected serialized sum and count, not only some positive OOS state. Keep fixture/interface and public-logical versus shell-physical records separate.
- [ ] Exercise the strict profitability floor with the accepted FORCE_OUTLINE mechanism where needed, independently of the disputed ordinary gate.
- [ ] Preserve the accepted 4,060-byte target/current raw-quarter mismatch under CBRD-27057. Keep the correct desired boundary fixture/oracle visible outside the passing-credit claim; no source-gate blessing or engine fix belongs here.
- [ ] Remove redundant bulk-size levels only where they add no distinct behavior; preserve positive and negative boundary controls.

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
