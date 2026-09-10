# 02: Extract OOS DELETE history after vacuum

**What to build:** A CDC consumer receives byte-correct DELETE before images after vacuum on an activated/current database, and encounters a checked error for unresolved legacy OOS history.

**Blocked by:** 01: Activate durable-history compatibility safely.

**Status:** draft-for-review

- [ ] Replace the reduced 50-row diagnostic fixture with fixed expected bytes and reliable observed-vacuum synchronization.
- [ ] Capture and publish a durable DELETE image while the original value remains protected, then extract exact identities/counts/bytes without live OOS dependencies.
- [ ] Use an owned expanded copy and preserve physical recovery records and caller buffers.
- [ ] Fail image construction/append through normal rollback and demonstrate no successful committed DELETE lacks required history.
- [ ] Legacy non-OOS history remains supported; unresolved legacy OOS history fails explicitly without slot reads, server crashes or silent event skipping.
- [ ] Cover all_in_cond=0/1 and more than one chunk; original DELETE failure turns green with vacuum enabled.

## Context

Part of the confirmed CBRD-26939/PR #6864 contract. Use the feature specification and ADR-0004. This draft is not a published ready-for-agent ticket until the proposed seams and breakdown are reviewed.
