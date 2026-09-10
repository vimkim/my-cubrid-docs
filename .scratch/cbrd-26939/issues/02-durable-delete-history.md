# 02: Extract OOS DELETE history after vacuum

**What to build:** A CDC consumer receives byte-correct DELETE before images after vacuum on an activated/current database, and encounters a checked error for unresolved legacy OOS history.

**Blocked by:** 01: Activate durable-history compatibility safely.

**Status:** resolved

- [x] Replace the reduced 50-row diagnostic fixture with fixed expected bytes and reliable observed-vacuum synchronization.
- [x] Capture and publish a durable DELETE image while the original value remains protected, then extract exact identities/counts/bytes without live OOS dependencies.
- [x] Use an owned expanded copy and preserve physical recovery records and caller buffers.
- [x] Fail image construction/append through normal rollback and demonstrate no successful committed DELETE lacks required history.
- [x] Legacy non-OOS history remains supported; unresolved legacy OOS history fails explicitly without slot reads, server crashes or silent event skipping.
- [x] Cover all_in_cond=0/1 and more than one chunk; original DELETE failure turns green with vacuum enabled.

## Context

Part of the confirmed CBRD-26939/PR #6864 contract. Use the feature specification and ADR-0004. User approved the ticket breakdown, dependencies and public test seams on 2026-09-08. See [feature specification](../spec.md).

## Comments

CDC byte-value regression added in the separate implementation worktree. RED at ticket-1 engine: public SHOW HEAP OOS reports 90 records before vacuum and zero after; CDC extraction fails with rc=-10 before returning DELETE images. Evidence: cdc.rQS8mn under the local cubrid-history cache.

## Completion evidence

Implemented in `7d97d4bf63ee375da5fa6f6d2e4c1985f084532a` on `CBRD-26939-oos-cdc`, draft PR #7897 against `feat/oos`. CCI companion `268d15262d329ca48a6e6202cc38df1de11fb7b0` is published and fetchable through the canonical submodule URL.

See [final CDC implementation and verification report](../../../cbrd-26939/CBRD-26939-durable-cdc-history_68c6d0b_codex.md). Original CDC regressions pass (`regressions.Mq331X`); fixed-byte lifecycle, legacy/malformed rejection, 12 failure combinations, trigger/partition, crash/backup, and page-size/compression checks are recorded there. Trigger I/U may use existing full-row storage; separate seeded OOS DELETE+trigger coverage verifies OOS reclamation directly. Standards and Spec reviews have no remaining CDC blockers. Final configured tests had one 60-second server-test timeout; its isolated fixture/test rerun passed in 37 seconds. Independent JDBC ticket05 and complete-PR CI integration ticket06 remain open.
