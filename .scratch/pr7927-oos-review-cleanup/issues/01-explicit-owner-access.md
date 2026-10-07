# 01: Explicit-owner prepared-row access

**What to build:** Prepared rows use their existing owner to resolve pending OOS
values across routing and key evaluation, then finalize into the destination
without rebuilding the compact buffer or depending on encoded memory addresses.

**Blocked by:** None (can start immediately).

**Status:** claimed

- [ ] Shared RECDES layout stays unchanged; no replacement record type or registry.
- [ ] Placeholders use validated owner-local indices; missing/wrong owner and invalid index/length fail safely.
- [ ] Scalar/grouped reads, composite/function keys, duplicate probes and movement forward the owner correctly.
- [ ] Current-view finalization preserves compact allocation and in-place patching across MVCC header growth.
- [ ] Owner moves, payload lifetime and loader retained-byte accounting remain correct.
- [ ] Inline-only, repeated and failed finalization preserve publication and rollback guarantees.
- [ ] Focused ownership and SQL checks pass; source changes are locally committed.

## Comments

2026-10-07: Claimed by codex-pr7927-resume. The existing marker may remain only
as a migration guard until task 02; no replacement type is introduced.
