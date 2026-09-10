# 04: Read durable history through flashback and restart

**What to build:** Users query accurate flashback history and resume supported CDC extraction after archive rollover and server restart/recovery.

**Blocked by:** 03: Preserve INSERT and UPDATE images through later changes.

**Status:** resolved

- [x] Flashback uses the same supported image decoding for INSERT/UPDATE/DELETE and trigger events.
- [x] Delayed flashback after confirmed vacuum returns correct values; legacy unresolved OOS images produce checked errors.
- [x] Retained historical data remains usable across archive rollover, compression on/off, clean restart and crash recovery.
- [x] Rollback and interrupted image publication do not become committed historical changes.
- [x] Cover 4KB/8KB/16KB layouts, multiple attributes/chunks and the established schema/archive availability contracts.
- [x] Backup/restore of activated/current databases preserves format protection and extractable supported history.

## Context

Part of the confirmed CBRD-26939/PR #6864 contract. Use the feature specification and ADR-0004. User approved the ticket breakdown, dependencies and public test seams on 2026-09-08. See [feature specification](../spec.md).

## Completion evidence

Implemented in `7d97d4bf63ee375da5fa6f6d2e4c1985f084532a` on `CBRD-26939-oos-cdc`, draft PR #7897 against `feat/oos`. CCI companion `268d15262d329ca48a6e6202cc38df1de11fb7b0` is published and fetchable through the canonical submodule URL.

See [final CDC implementation and verification report](../../../cbrd-26939/CBRD-26939-durable-cdc-history_68c6d0b_codex.md). Original CDC regressions pass (`regressions.Mq331X`); fixed-byte lifecycle, legacy/malformed rejection, 12 failure combinations, trigger/partition, crash/backup, and page-size/compression checks are recorded there. Trigger I/U may use existing full-row storage; separate seeded OOS DELETE+trigger coverage verifies OOS reclamation directly. Standards and Spec reviews have no remaining CDC blockers. Final configured tests had one 60-second server-test timeout; its isolated fixture/test rerun passed in 37 seconds. Independent JDBC ticket05 and complete-PR CI integration ticket06 remain open.
