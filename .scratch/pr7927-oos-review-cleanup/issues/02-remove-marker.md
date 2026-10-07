# 02: Remove marker and enforce publication boundaries

**What to build:** Prepared rows require no special record type, while temporary
references are rejected at logical storage and actual heap-row export boundaries.

**Blocked by:** 01 Explicit-owner prepared-row access.

**Status:** resolved

- [x] REC_OOS_PENDING is absent from source and current tests; no replacement type or shared descriptor field.
- [x] Ownerless finalization and logical heap writes reject copied temporary placeholders and accept legitimate disk references.
- [x] Storage validation checks bounds and uses class representation without a new legacy sentinel requirement.
- [x] Actual LC_FETCH producers reject residual OOS before publishing descriptor/count; raw optional prefetch skips OOS neighbors; release checks prove rejection.
- [x] Root metadata, no-content descriptors, incoming replication and error payloads retain supported behavior.
- [x] Generic descriptor packing retains baseline arbitrary-byte behavior.
- [x] Configured debug build/CTest, focused boundary checks and real server-loader fixture have recorded verdicts.
- [x] Standards and Spec review is completed against the pinned PR head; findings are resolved or explicitly documented.
- [x] Meaningful source changes and verification artifacts are locally committed; unrelated changes preserved.

## Comments

2026-10-07: Task 01 completed at c73f01c1d. Claimed by codex-pr7927-resume.

2026-10-07 review addendum: loader per-row fallback was missing its queued owner;
real partitioned loading reproduced the failure. The inherited raw prefetch path
also bypassed expanding locator producers; a direct engine test reproduced OOS
neighbor publication. Both are corrected within the approved lifetime/export
contract. Synthetic vacuum fixtures now use their borrowed class representation;
the enlarged expected-error SQL suite has a bounded180-second debug timeout.

## Answer

2026-10-07: Implemented and reviewed at source `6b53181d31d6d6d2615b18b4f914623bb017d7c4`.
Marker absent; shared storage and generic descriptor files equal the baseline.
Debug build/install, configured 35/35 CTest, focused fixes, assertions-disabled
boundary/prefetch tests and real server-loader fixture pass. Both review axes
have zero remaining findings. [Verification](../../../cbrd-27089/design/no-record-type-verification.md)
records failed reproductions, corrections, command identities and limits.
Unrelated CCI/JDBC changes remain preserved. Tasks 03/04 may complete.
