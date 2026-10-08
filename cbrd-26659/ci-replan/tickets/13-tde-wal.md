# 13: Validate OOS TDE attribution and WAL behavior

**What to build:** A compact private shell TDE fixture identifies the owned OOS file and intended encryption policy, checks relevant WAL classifications and exact values through lifecycle operations, and reports any remaining ciphertext gap.

**Blocked by:** 02.

**Status:** ready-for-agent

Definition approved 2026-10-08; testcase implementation is a later phase.

**Parent:** CBRD-26659.

**Coverage and prior art:** R27. Strengthen current tbl_enc_08/14 and log_enc_04 mechanisms; heap-only file_enc expectations are supporting coexistence evidence.

## Acceptance criteria

- [ ] Prepare owned keys/configuration and demonstrate the required optdebug branch actually executes. A legacy write_ok/skip fallback is not a selected passing case.
- [ ] Cover encrypted lazy OOS-file creation and encryption of an existing OOS file with exact owned-file attribution and intended algorithm; volatile-ID removal must not erase the identity correlation being asserted.
- [ ] Check relevant RVOOS_INSERT/DELETE user-data-bearing WAL classification/encryption evidence with independently reviewed expectations, then verify exact logical values after the supported lifecycle/restart operation.
- [ ] Distinguish algorithm metadata, WAL flags, actual encrypted bytes and recovery. If no product-level ciphertext inspection establishes plaintext absence, keep that capability gap explicit rather than claim full encryption proof.
- [ ] Restore owned TDE/configuration state and remove only owned keystore/database/log resources, including timeout/error paths. Record the required configuration and its actual local cost.

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
