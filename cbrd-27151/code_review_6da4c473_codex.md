# CBRD-27151 / PR #7785 Code Review

- PR: [CUBRID/cubrid#7785](https://github.com/CUBRID/cubrid/pull/7785) — `[CBRD-27151] Reduce DROP/TRUNCATE commit cost with sector-level bulk file destroy`
- Ticket: [CBRD-27151](http://jira.cubrid.org/browse/CBRD-27151)
- Review date: 2026-09-23 (Asia/Seoul)
- Pinned PR head: `6da4c47387108c53e8c3c354c4e4b0ca706d4bb4`
- Fixed point: live `origin/develop` at `0320a768b09bda9e58e93875398450b0580c8e22`
- Merge-base: `f8f5b4401552679e347cd594d8d8f3a1600f1d07`
- Diff: `git diff origin/develop...HEAD -- src/storage/file_manager.c src/storage/page_buffer.c src/storage/page_buffer.h`
- Commit range: `git log origin/develop..HEAD --oneline` (7 commits, `e3ff1a6e1` through `6da4c4738`)

## Evidence inspected

- Authoritative ticket text from `cubrid-jira search CBRD-27151`, including the specification and acceptance criteria.
- Live PR body, seven commits, three changed files, all inline review threads, review summaries, discussion comments, review requests, and status checks.
- Applicable guidance: `/home/vimkim/my-cubrid/CUBRID.md`, repository `AGENTS.md`, `src/AGENTS.md`, `src/storage/AGENTS.md`, `CONTRIBUTING.md`, `src/storage/docs/buffer-io-durability.md`, and `src/storage/docs/disk-file-space.md`.
- Full three-dot diff and relevant surrounding implementations in `file_manager.c`, `page_buffer.c`, `file_io.c`, and the page-buffer flush/latch paths.
- Earlier checkpoint/recovery analysis at `cbrd-27151/CBRD-27151-bulk-destroy-recovery-metadata_93f11fb3f_claude.md`, independently revalidated against the current head. The prior header/file-table durability defect is addressed by `f8bab897c`: resident metadata pages are now flushed with WAL before discard.
- Linked testcase PRs: public `cubrid-testcases#3441` is empty; private `cubrid-testcases-private-ex#4089` only changes TDE shell expectations and scripts. Neither adds deterministic crash/reuse coverage for the two paths below.

## Validation performed

- Confirmed the worktree started and remained clean at pinned head `6da4c47387108c53e8c3c354c4e4b0ca706d4bb4`.
- Fetched and resolved the live `develop` ref; confirmed a non-empty three-file three-dot diff and pinned the merge-base above.
- `git diff --check origin/develop...HEAD`: pass.
- Live checks: `code-style`, `cppcheck`, `license`, `memory-monitor-check`, `pr-style`, CircleCI `build`, and CircleCI `build_debug` pass. `Check TC PRs` fails only because the two linked testcase PRs remain open/draft.
- No local build or runtime crash test was run. The findings are concurrency/source-trace findings; the linked tests do not exercise them, and a compile would not validate their ordering guarantees.

## Standards

**Pass — 0 findings.**

No documented-standard violation was found in the changed hunks. The new fixes in `src/storage/file_manager.c:4201-4218` and `:4221-4226` have matching unfix paths and use the WAL-aware flush entry point. Cleanup remains centralized at `:4305-4317`. The C additions preserve project comment/naming/include conventions, and the live style/cppcheck jobs pass.

No actionable Fowler-baseline smell was confirmed. The declaration/implementation/caller spread across `page_buffer.h`, `page_buffer.c`, and `file_manager.c` is the normal page-buffer interface seam rather than Shotgun Surgery.

## Spec

### [P1] `NEW_PAGE` reuse does not wait for an already-running stale flush

The ticket requires: **“진행 중인 flush가 있으면 완료를 기다린 뒤 무효화하여, 죽은 페이지가 재사용된 섹터를 뒤늦게 덮어쓰는 일이 없도록 한다.”**

After crash recovery re-materializes an old file page, a later sector reuse can find that stale BCB in `pgbuf_fix(NEW_PAGE)`. The new branch at `src/storage/page_buffer.c:2517-2531` clears `DIRTY` and reinitializes the frame but never checks `pgbuf_bcb_is_flushing()` or joins the flush-waiter protocol. This is materially different from the destroy-side path at `:3528-3540`.

The flush implementation proves the race: `pgbuf_bcb_flush_with_wal()` marks the BCB flushing and copies the old image while holding the BCB mutex, then releases the mutex at `src/storage/page_buffer.c:10843-10884`; the physical write occurs later at `:10934-10935`. During that unlocked interval, `NEW_PAGE` can acquire the page latch and initialize the frame while the old snapshot still has permission to write to the now-reallocated sector. The destroy-side wait cannot cover this BCB because recovery creates it after the completed runtime discard.

The reuse path must wait for `FLUSHING` to clear before handing the BCB to the new owner or reinitializing it.

### [P1] Fixed-page timeout abandons discard but still permits sector unreserve

The ticket requires both **“버퍼에 상주하는 페이지만 골라 dirty 상태를 해제하고 무효화(discard)한다”** and the late-write exclusion quoted above.

At `src/storage/page_buffer.c:3501-3515`, a page that remains fixed for roughly one second takes a release fallback that clears `DIRTY` and returns while leaving the BCB fixed, valid, and accessible to its existing holder. `pgbuf_discard_pages_of_sectors()` has a `void` result, so `file_destroy()` cannot detect this incomplete discard: it continues after `src/storage/file_manager.c:4228` and unreserves the sectors at `:4294-4295`.

An existing write holder can continue changing the old page, mark it dirty again, and later flush into a sector that has already been handed to another file. The later `NEW_PAGE` neutralization cannot establish safety while that old holder remains active. If `fcnt > 0` is truly forbidden by the caller's exclusivity contract, an invariant failure must not be converted into a successful destroy; the function should keep waiting or report failure so unreserve cannot proceed.

## Final decision

**COMMENT** — two actionable correctness/spec findings. Per the requested workflow, this is not submitted as `REQUEST_CHANGES`.

- GitHub review: [review #5288672784](https://github.com/CUBRID/cubrid/pull/7785#pullrequestreview-5288672784)
- Review state: `COMMENTED`

Standards: 0 findings (pass); Spec: 2 findings (worst: P1 — old buffered writes can outlive sector ownership).
