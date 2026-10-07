# 02: Remove marker and enforce publication boundaries

**What to build:** Prepared rows require no special record type, while temporary
references are rejected at logical storage and actual heap-row export boundaries.

**Blocked by:** 01 Explicit-owner prepared-row access.

**Status:** claimed

- [ ] REC_OOS_PENDING is absent from source and current tests; no replacement type or shared descriptor field.
- [ ] Ownerless finalization and logical heap writes reject copied temporary placeholders and accept legitimate disk references.
- [ ] Storage validation checks bounds and uses class representation without a new legacy sentinel requirement.
- [ ] Actual LC_FETCH producers reject residual OOS before publishing descriptor/count; release checks prove rejection.
- [ ] Root metadata, no-content descriptors, incoming replication and error payloads retain supported behavior.
- [ ] Generic descriptor packing retains baseline arbitrary-byte behavior.
- [ ] Configured debug build/CTest, focused boundary checks and real server-loader fixture have recorded verdicts.
- [ ] Standards and Spec review is completed against the pinned PR head; findings are resolved or explicitly documented.
- [ ] Meaningful source changes and verification artifacts are locally committed; unrelated changes preserved.

## Comments

2026-10-07: Task 01 completed at c73f01c1d. Claimed by codex-pr7927-resume.
