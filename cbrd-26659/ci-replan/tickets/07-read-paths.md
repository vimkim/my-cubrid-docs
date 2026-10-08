# 07: Validate supported relational and raw read paths

**What to build:** Public query regressions return identical independently modeled complete values through the intended heap/index and relational paths, with explicit plan/path and paired-fixture evidence.

**Blocked by:** 01, 02.

**Status:** ready-for-agent

Definition approved 2026-10-08; testcase implementation is a later phase.

**Parent:** CBRD-26659.

**Coverage and prior art:** R13 and supported R07 type interaction. Existing read units and generic repository queries are path seeds, not automatic OOS coverage.

## Acceptance criteria

- [ ] Cover inline-only and OOS projections, supported heap/index or forced scan alternatives, CTAS/views, joins/subqueries, sort/group/aggregate and multicolumn-index interactions with a small shared row model.
- [ ] Use stable complete values/digests and a unique ordering key; prefix-only equality and tied ORDER BY results are insufficient. Derive expected relational row sets outside observed engine output.
- [ ] For a claimed access path, retain supported plan/source evidence and the actual execution conditions; forcing syntax must follow current repository conventions.
- [ ] Deliver a paired shell fixture with positive OOS state where needed, preserving the same values/schema/configuration and disclosing protocol differences. Do not call this observation of the actual public SQL run.
- [ ] Distinguish SQL copy/read coverage from real utility raw consumers, which belong to ticket 12. The source-current raw-fetch expansion fix does not by itself establish end-to-end utility coverage.

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
