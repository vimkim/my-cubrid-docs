# 15: Ship advanced recovery and lifecycle

**What to build:** Give an advanced maintainer a connected explanation of recovery, allocation state, checkpoint boundaries, and page-buffer lifecycle ordering grounded in the core caller and durability contracts.

**Blocked by:** 12: Ship symptom-driven diagnosis

**Status:** ready-for-agent

- [ ] Checkpoint is explained as selective page-buffer flushing plus log/filesystem/metadata boundaries rather than “flush every page.”
- [ ] Recovery fetch mode, page-LSA comparison, redo application, LSA update, dirtying, and release preserve idempotence.
- [ ] Initialization, daemon gating, recovery, shutdown, log finalization, and page-buffer finalization are ordered at their dependency seams.
- [ ] Invalidation, victimization, and logical deallocation remain distinct.
- [ ] Temporary and recovery-specific modes are kept inside their owner protocols.
- [ ] Allocation decisions remain owned by file/disk/recovery callers rather than page-buffer materialization.
- [ ] Exact pinned-source anchors cover representative checkpoint, redo, boot, and shutdown paths.
- [ ] Crash and persistence claims remain bounded by the available evidence.
- [ ] The page links back to canonical caller, generation, identity, and idempotence explanations.
- [ ] Aggregate validation passes for this advanced route.
