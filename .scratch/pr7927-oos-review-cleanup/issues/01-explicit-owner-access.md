# 01: Explicit-owner prepared-row access

**What to build:** Prepared rows use their existing owner to resolve pending OOS
values across routing and key evaluation, then finalize into the destination
without rebuilding the compact buffer or depending on encoded memory addresses.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] Shared RECDES layout stays unchanged; no replacement record type or registry.
- [x] Placeholders use validated owner-local indices; missing/wrong owner and invalid index/length fail safely.
- [x] Scalar/grouped reads, composite/function keys, duplicate probes and movement forward the owner correctly.
- [x] Current-view finalization preserves compact allocation and in-place patching across MVCC header growth.
- [x] Owner moves, payload lifetime and loader retained-byte accounting remain correct.
- [x] Inline-only, repeated and failed finalization preserve publication and rollback guarantees.
- [x] Focused ownership and SQL checks pass; source changes are locally committed.

## Comments

2026-10-07: Claimed by codex-pr7927-resume. The existing marker may remain only
as a migration guard until task 02; no replacement type is introduced.

## Answer

Source commit c73f01c1d implements explicit-owner reads, owner-local indices and
current-view finalization. The missing-owner test failed on the old decoder as
expected; the SQL show binary passed, then the three extended ownership/MVCC/
publication cases passed after the final additions. Debug build/install passed.
The existing marker remains only until task 02. Unrelated CCI/JDBC changes remain.
