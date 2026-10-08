# 08: Validate schema and storage-policy rewrites

**What to build:** Public DDL checks and discriminating shell placement/owner phases preserve intended data and metadata across schema and storage-policy changes, with partition defects visibly dispositioned.

**Blocked by:** 01, 02.

**Status:** ready-for-agent

Definition approved 2026-10-08; testcase implementation is a later phase.

**Parent:** CBRD-26659.

**Coverage and prior art:** R06, R14 and supported R15 subset. Recover the schema report and use accepted storage-policy units/contracts.

## Acceptance criteria

- [ ] Port compact reorder/add/drop/default/type/precision/nullability and OOS-attribute-drop checks; failed ALTER preserves the prior schema and exact data.
- [ ] Cover accepted CREATE/LIKE/MODIFY/CHANGE/reset behavior for DEFAULT, PREFER_INLINE and FORCE_OUTLINE, including soft-priority fallback and profitable-size controls.
- [ ] Check intended rejection of explicit policies on current fixed/class/shared/view domains. Do not require proposed FORCE_INLINE, fixed DEFAULT exceptions or variable fixed BIT as existing behavior.
- [ ] Use unequal independently derived candidates for policy selection; document the normative context FORCE_OUTLINE omission separately from the accepted CBRD-26067 contract.
- [ ] Deliver physical phases for rewrite/placement claims and owner evidence for supported partition creation/routing/movement. Logical partition equality cannot establish the destination-chain owner.
- [ ] Keep CBRD-27089 destination ownership separately dispositioned unless the exact-source correct regression passes. No workaround or engine fix is included; any selected passing subset states its narrower coverage.

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
