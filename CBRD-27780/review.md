# PR 8402 review: TDE page deallocation and reuse

The goal is to review whether encrypted page contents remain protected through deallocation, buffer reuse, and recovery. The pinned review found no independently reproduced database defect, but two material recovery risks remain. The verdict is **incomplete** and follow-up review is required before relying on the change's recovery safety.

## Snapshot and verdict

- PR: [CUBRID/cubrid #8402](https://github.com/CUBRID/cubrid/pull/8402), CBRD-27780. The issue requires that deallocated encrypted pages and reused buffers do not write old plaintext to data volumes or the double-write buffer. The PR also addresses recovery of the TDE flag.
- Base: `063d84e537cbde1a359f369aabb510b01fe68a00` on `develop`. Head: `35eeb2b05cf9732638207f5011c1eb9d53cd8faa` on `YeunjunLee/cubrid:CBRD-27780`. Merge base equals base. Comparison: `git diff --no-ext-diff --binary 063d84e537cbde1a359f369aabb510b01fe68a00 35eeb2b05cf9732638207f5011c1eb9d53cd8faa`.
- Patch SHA-256: `cf37a1a3ad75712bf115d368831651678ae3c200fe165273b5c33805950057e2`. The five changed paths are listed in [coverage.md](coverage.md).
- GitHub metadata was rechecked at approximately 2026-11-11 10:50 UTC. Both remote SHAs still matched. The parent rechecks these refs before publication.
- Confirmed findings: **0**. This does not establish that the PR is safe to merge. No integrated failure reproduction or coordinator replay of an integrated failure was completed.

## Unverified recovery risks

### R1: Rollback may restore a reused file-table page whose contents were cleared

When every entry in a separate partial-sector table page fits in the file header, [`file_table_move_partial_sectors_to_header`](https://github.com/CUBRID/cubrid/blob/35eeb2b05cf9732638207f5011c1eb9d53cd8faa/src/storage/file_manager.c#L4793) copies and logs the entries in the header, unlinks the table page, and deallocates it for reuse by the same allocation. The deallocation undo stores page identity, type, and flags, but not its old body. [`pgbuf_fix(NEW_PAGE)`](https://github.com/CUBRID/cubrid/blob/35eeb2b05cf9732638207f5011c1eb9d53cd8faa/src/storage/page_buffer.c#L2527) now clears the body, and [`file_alloc`](https://github.com/CUBRID/cubrid/blob/35eeb2b05cf9732638207f5011c1eb9d53cd8faa/src/storage/file_manager.c#L5438) logs a clear before the initializer.

A source-supported schedule is a crash after this clear record becomes durable and before the initializer's redo record or the atomic system operation completes. Redo can clear the old table contents, while subsequent undo can restore the header link and page type without restoring those contents. R2 can interrupt recovery before this outcome becomes observable. If reached, the lost table data could corrupt allocation metadata. The extra pre-initializer clear is absent from the pinned base; other, later overwrite windows may be pre-existing and are not attributed here. This is a source-level candidate, not a demonstrated database failure.

A retained helper probe compiles the pinned clear-redo, new-page-undo, and deallocation-undo-compensation function bodies. It observed preserved payload without clear and lost payload with clear while restoring the type. The probe stubs page dirtying, page-type setting, and surrounding runtime types. It does not run allocation, actual page fixing, log dispatch, durability, rollback, a base binary, or a database. The coordinator reran that same helper and obtained the same two results; this demonstrates the selected byte transformations only. The parent independently replayed the helper. A full page-reuse and crash reproduction is still required before treating R1 as a defect.

### R2: Clear-record undo may reject a page with unknown type

The new `RVPGBUF_CLEAR_NEW_PAGE` is a physical undo-redo record registered with `pgbuf_rv_new_page_undo` in [`recovery.c`](https://github.com/CUBRID/cubrid/blob/35eeb2b05cf9732638207f5011c1eb9d53cd8faa/src/transaction/recovery.c#L880). If allocation is interrupted after clear logging and before initialization sets the page type, or if later initialization undo has already reset the type, the record's target can be `PAGE_UNKNOWN`. The ordinary rollback path calls [`pgbuf_fix` with `OLD_PAGE`](https://github.com/CUBRID/cubrid/blob/35eeb2b05cf9732638207f5011c1eb9d53cd8faa/src/transaction/log_manager.c#L7455). [`pgbuf_fix`](https://github.com/CUBRID/cubrid/blob/35eeb2b05cf9732638207f5011c1eb9d53cd8faa/src/storage/page_buffer.c#L2584) rejects that type, asserting in debug builds and returning an error in release builds. The source trace indicates recovery may fail or skip the intended undo; the actual outcome requires an integrated run.

An existing exact-head PR comment reports a debug reproduction using a breakpoint at a page initializer, a forced log flush, and a server crash. Its raw output and complete SQL environment were not available to this review. It is third-party reported evidence, not an independent reproduction. Run a controlled head and base comparison on isolated resources to decide R2 and observe both debug and release behavior.

## Other safety evidence

- Normal `file_alloc` retains its write latch from NEW_PAGE clearing through the initializer and TDE flag update. The foreign-flusher admission check defers flushing a page held by another writer. The owning thread can explicitly flush its own write-latched page, so latch ownership alone does not exclude that case. The inspected initializers did not invoke such a flush. Both concurrency and recovery reviewers reached the foreign-flush conclusion independently; this is not a full interleaving or crash proof.
- A retained seven-case helper probe executes the pinned safe-flush decision function with stubbed ownership checking, dirty and flushing state, holder lookup, flush I/O, waiting, and flag updates. The coordinator reran it and all seven cases passed. It tests admission decisions under those supplied states, not actual threads, I/O, or page-latch integration.
- In source, runtime deallocation and its redo preserve the TDE flag, and the flush path selects encryption from that flag. The clear record and later TDE update have WAL paths. No encrypted on-disk marker test or crash-order test was run here.
- Both current `pgbuf_copy_from_area` production callers copy the entire page, so source inspection did not find an active partial-write regression caused by the new clear. PAGE_FTAB redo, allocation callbacks, HA/CDC overflow readers, and temporary-page handling were reviewed in source only. No HA, CDC, temporary spill, or encryption workload was run.

## Verification and limitations

The pinned objects, merge base, full binary-capable patch, changed-path inventory, and patch hash were obtained using Git. Source analysis covered all five changed files and material callers. [Coverage](coverage.md) records ownership and gaps. The supplied worktree-specific guidance was applied; `gh-pr-info` on the starting `develop` checkout returned multiple historical matches, so the target PR was resolved explicitly through the GitHub connector. The local `develop` checkout had unrelated modified submodules and untracked files, which were preserved.

The coordinator created a detached worktree at the pinned head. `debug_gcc` configuration completed successfully with CCI submodule `df47f014731e977263b25cb5ea53dc6d0846328a` and a dedicated installation path. The subsequent CMake build and installation had not completed when checked. The coordinator stopped it, exit 130, after observing the Gradle sub-build succeed and other build steps still active. The engine build and installation are **not verified**. No database was created, no engine runtime or crash test was started, and no CI was triggered. Raw build output remains in `evidence/build-command.log`.

The previous coordinator turn was interrupted or withheld by the environment. This continuation used the existing specialist reports and available evidence, without restarting assignments or starting failure injection. The parent coordinator handles documentation publication and the PR summary. [Handoff](handoff.md) gives the next checks and their isolation requirements.

## Budget and reviewer disposition

Bounded allocation was four specialist seats at 12 minutes each, with an 8-minute checkpoint and a 20 agent-minute coordinator reservation, for a 68 agent-minute target. Specialists used `gpt-6.1-sol` and `gpt-6.1-terra` at `xhigh`; no retries or nested agents were used. Targets were not hard enforced. The account display showed 93% weekly allowance remaining near 10:40 UTC, but no per-agent usage or reliable complete coordinator usage was available. Exact budget compliance and overshoot are therefore unverifiable.

The concurrency, storage, recovery, and systems reports are retained under `reviewers/`. Storage and recovery independently raised R1; storage, recovery, and systems raised R2. They are consolidated by root cause above. No material candidate was dropped as disproven. The partial-write hypothesis was bounded by its two current full-page callers. The suspected foreign-thread flush during the write-latched interval was bounded by source and the helper probe. Neither result establishes all execution schedules.


Review date is 2026-11-11 in Asia/Seoul. The parent coordinator independently replayed both retained helper probes. Raw logs, the manifest, specialist notes, and build artifacts remain in the local run directory `/home/vimkim/temp/pr-reviews-20261111-8454-4737-8402/8402`. The evidence and limitations needed to assess this report are stated above.

The parent rechecked the PR base and head through the GitHub connector at 2026-11-11 10:54 UTC. Both still matched this snapshot.
