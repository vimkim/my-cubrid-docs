# 01: Activate durable-history compatibility safely

**What to build:** An operator can create a current-format database or explicitly activate an existing database offline, preserve data, and observe the correct old-engine rejection and inactive-database behavior.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] Fresh databases establish the current compatibility level without a second activation step; an actual baseline engine rejects opening them before recovery.
- [x] Existing inactive databases open under the fixed engine without an implicit compatibility change and preserve existing data.
- [x] Explicit activation requires clean shutdown, is one-way and preserves current data and readable non-OOS history.
- [x] Compatibility state is durably established before new-format emission is allowed; interruption yields a safe, recoverable state.
- [x] Backup/restore and lifecycle utilities validate inactive/current compatibility; upgraded HA/log-reader rollout and enforcement limits are explicit.
- [x] Writes requiring durable OOS images cannot silently use legacy publication on an inactive database; expose an activation-required error.
- [x] The public lifecycle behavior is tested with a real baseline binary, not just assertions on numeric compatibility constants.

## Context

Part of the confirmed CBRD-26939/PR #6864 contract. Use the feature specification and ADR-0004. User approved the ticket breakdown, dependencies and public test seams on 2026-09-08. See [feature specification](../spec.md).

## Answer

Implemented in engine commit `9960c7fc6` on `CBRD-26939-oos-cdc` after merge `f4299ac0c`, with CCI companion `76b293743800620cc521fb818b9567b6ae19cad9`. Linux only, as confirmed by the user. The new offline activation utility, durable compatibility fence, inactive OOS-write guard, and backup/reader compatibility behavior satisfy this ticket. Full durable OOS image publication remains in subsequent tickets.

Validation: build passed; all 27 configured tests passed; complete public lifecycle and syscall fault matrix passed at 4KB, 8KB, and 16KB data/log page sizes against an actual baseline engine. Standards and Spec reviews have no outstanding findings. See [verification evidence](../../../cbrd-26939/2940b1c_codex/ticket-01-verification.md). Published as draft PR #7897 targeting `feat/oos`; ticket 02 is unblocked.

## Branch correction

At the user's request, moved unchanged commit `9960c7fc6` to branch/worktree `CBRD-26939-oos-cdc`. Restored local `feat/oos` to `f4299ac0c` with a keep reset, preserving unrelated local files and nested submodule edits. Future implementation belongs in `/home/vimkim/gh/cb/CBRD-26939-oos-cdc`. Draft PR: https://github.com/CUBRID/cubrid/pull/7897 (base `feat/oos`). Fresh recursive submodule checkout succeeded through the configured canonical URLs.
