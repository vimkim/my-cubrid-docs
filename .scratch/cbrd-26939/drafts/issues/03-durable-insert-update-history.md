# 03: Preserve INSERT and UPDATE images through later changes

**What to build:** A delayed consumer extracts the original INSERT value and each UPDATE before/after pair even after later writes and vacuum reclaim all corresponding chains.

**Blocked by:** 02: Extract OOS DELETE history after vacuum.

**Status:** draft-for-review

- [ ] New durable supplemental images are supported as both before and after images through the shared reader.
- [ ] INSERT followed by UPDATE/DELETE and repeated UPDATE yield exact historical values and transaction/event identities.
- [ ] Cover multiple OOS-backed attributes, single/multiple chunks and payload changes of identical length.
- [ ] Trigger, relocation, partition and applicable eager/non-MVCC write paths satisfy the same publication contract.
- [ ] Construction and publication failures on either side fail the write and preserve normal rollback behavior.
- [ ] Supplemental logging disabled emits no extra supplemental images and retains existing supported write behavior.

## Context

Part of the confirmed CBRD-26939/PR #6864 contract. Use the feature specification and ADR-0004. This draft is not a published ready-for-agent ticket until the proposed seams and breakdown are reviewed.
