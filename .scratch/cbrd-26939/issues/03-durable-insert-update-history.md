# 03: Preserve INSERT and UPDATE images through later changes

**What to build:** A delayed consumer extracts the original INSERT value and each UPDATE before/after pair even after later writes and vacuum reclaim all corresponding chains.

**Blocked by:** 02: Extract OOS DELETE history after vacuum.

**Status:** resolved

- [x] New durable supplemental images are supported as both before and after images through the shared reader.
- [x] INSERT followed by UPDATE/DELETE and repeated UPDATE yield exact historical values and transaction/event identities.
- [x] Cover multiple OOS-backed attributes, single/multiple chunks and payload changes of identical length.
- [x] Trigger, relocation, partition and applicable eager/non-MVCC write paths satisfy the same publication contract.
- [x] Construction and publication failures on either side fail the write and preserve normal rollback behavior.
- [x] Supplemental logging disabled emits no extra supplemental images and retains existing supported write behavior.

## Context

Part of the confirmed CBRD-26939/PR #6864 contract. Use the feature specification and ADR-0004. User approved the ticket breakdown, dependencies and public test seams on 2026-09-08. See [feature specification](../spec.md).

## Completion evidence

Implemented in `7d97d4bf63ee375da5fa6f6d2e4c1985f084532a` on `CBRD-26939-oos-cdc`, draft PR #7897 against `feat/oos`. CCI companion `268d15262d329ca48a6e6202cc38df1de11fb7b0` is published and fetchable through the canonical submodule URL.

See [final CDC implementation and verification report](../../../cbrd-26939/CBRD-26939-durable-cdc-history_68c6d0b_codex.md). Original CDC regressions pass (`regressions.Mq331X`); fixed-byte lifecycle, legacy/malformed rejection, 12 failure combinations, trigger/partition, crash/backup, and page-size/compression checks are recorded there. Trigger I/U may use existing full-row storage; separate seeded OOS DELETE+trigger coverage verifies OOS reclamation directly. Standards and Spec reviews have no remaining CDC blockers. Final configured tests had one 60-second server-test timeout; its isolated fixture/test rerun passed in 37 seconds. Independent JDBC ticket05 and complete-PR CI integration ticket06 remain open.
