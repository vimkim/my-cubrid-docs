# 04: Read durable history through flashback and restart

**What to build:** Users query accurate flashback history and resume supported CDC extraction after archive rollover and server restart/recovery.

**Blocked by:** 03: Preserve INSERT and UPDATE images through later changes.

**Status:** draft-for-review

- [ ] Flashback uses the same supported image decoding for INSERT/UPDATE/DELETE and trigger events.
- [ ] Delayed flashback after confirmed vacuum returns correct values; legacy unresolved OOS images produce checked errors.
- [ ] Retained historical data remains usable across archive rollover, compression on/off, clean restart and crash recovery.
- [ ] Rollback and interrupted image publication do not become committed historical changes.
- [ ] Cover 4KB/8KB/16KB layouts, multiple attributes/chunks and the established schema/archive availability contracts.
- [ ] Backup/restore of activated/current databases preserves format protection and extractable supported history.

## Context

Part of the confirmed CBRD-26939/PR #6864 contract. Use the feature specification and ADR-0004. This draft is not a published ready-for-agent ticket until the proposed seams and breakdown are reviewed.
