# 01: Activate durable-history compatibility safely

**What to build:** An operator can create a current-format database or explicitly activate an existing database offline, preserve data, and observe the correct old-engine rejection and inactive-database behavior.

**Blocked by:** None (can start immediately).

**Status:** draft-for-review

- [ ] Fresh databases establish the current compatibility level without a second activation step; an actual baseline engine rejects opening them before recovery.
- [ ] Existing inactive databases open under the fixed engine without an implicit compatibility change and preserve existing data.
- [ ] Explicit activation requires clean shutdown, is one-way and preserves current data and readable non-OOS history.
- [ ] Compatibility state is durably established before new-format emission is allowed; interruption yields a safe, recoverable state.
- [ ] Backup/restore and lifecycle utilities validate inactive/current compatibility; upgraded HA/log-reader rollout and enforcement limits are explicit.
- [ ] Writes requiring durable OOS images cannot silently use legacy publication on an inactive database; expose an activation-required error.
- [ ] The public lifecycle behavior is tested with a real baseline binary, not just assertions on numeric compatibility constants.

## Context

Part of the confirmed CBRD-26939/PR #6864 contract. Use the feature specification and ADR-0004. This draft is not a published ready-for-agent ticket until the proposed seams and breakdown are reviewed.
