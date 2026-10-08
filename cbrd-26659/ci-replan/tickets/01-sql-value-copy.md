# 01: Prove one SQL value-copy case end to end

**What to build:** A compact public INSERT SELECT regression preserves independently modeled source and copied values through the real SQL runner, with complete discovery, answer, cleanup and timing evidence.

**Blocked by:** None (can start independently after approval).

**Status:** ready-for-agent

Definition approved 2026-10-08; testcase implementation is a later phase.

**Parent:** CBRD-26659.

**Coverage and prior art:** R01; a small R05 single/multichunk subset. Historical P03 is prior art, with current expectations independently recalculated.

## Acceptance criteria

- [ ] Prepare a source-matching optdebug install and disposable execution environment with matching JDBC, explicitly bind the chosen public task worktree, and record the effective JDBC/16 KiB profile. Follow the current checkout rule: use the existing named source task checkout directly. Preserve unrelated source/submodule changes and its ready Debug host environment; use the correctly selected optdebug install for contained validation.
- [ ] Reuse the recovered INSERT SELECT structure with a small ordered row set and distinct single/multichunk patterns. Include independently modeled row-by-row equality and copied values that remain correct after source deletion; derive changed totals before execution.
- [ ] Check copied fixture and expected-answer discovery and exact positive execution identities. Prove a wrong expectation is rejected in an isolated disposable attempt, then obtain the clean passing receipt without rewriting the reviewed answer from actual output.
- [ ] Record the SQL logical claim and its physical-observation limit. Supply the exact fixture/configuration description for the shell companion; SQL success alone receives no physical-placement credit.
- [ ] Hand back the minimal reusable local execution procedure and source/install/JDBC identities so later SQL slices can run without another setup-only ticket.

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
