# Code Review — CUBRID/cubrid#8776 + Linked TC PRs (CBRD-27370)

**Goal.** Review `[CBRD-27370] Count a WRITE fix on an own READ-latched page instead of resetting the fix count to 1` and its linked testcase PRs (`cubrid-testcases#4499`, `cubrid-testcases-private-ex#5194`). Scope:
- Pre-CAS contract check (`er_log_debug` + `assert_release`) and single-read safety claim in `pgbuf_latch_bcb_upon_fix()` (`src/storage/page_buffer.c`).
- Sub-case 2-2 sole-holder `new_impl.impl.fcnt++` accounting, multi-reader conditional/unconditional paths, `holder->perf_stat` / unfix / wakeup invariants, and `NDEBUG` vs `!NDEBUG` (`SERVER_MODE` / `SA_MODE`) behavior.
- Header/API contract documentation in `src/storage/page_buffer.h` and `src/storage/page_buffer.c`, caller impact across storage/recovery/vacuum, and linked testcase PR status.

**Most consequential result.** **No confirmed defects (`APPROVE`).** Changing `new_impl.impl.fcnt = 1` to `new_impl.impl.fcnt++` at [`src/storage/page_buffer.c#L7118`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/storage/page_buffer.c#L7118) fixes the `CBRD-26425` (`58cef8e01`) fix-count desynchronization, and adding the pre-CAS `er_log_debug` + `assert_release (request_mode != PGBUF_LATCH_WRITE)` guard at [`src/storage/page_buffer.c#L7020-L7029`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/storage/page_buffer.c#L7020-L7029) restores pre-rework `!NDEBUG` contract enforcement while preserving `er_errid()` in `NDEBUG` builds. Both `debug_gcc` (`1779/1779`) and `release_gcc` (`1681/1681`, `-Werror -DNDEBUG`) builds compiled cleanly with zero warnings on `page_buffer.c`/`page_buffer.h`, `cubrid-static-check` reported zero new issues, GNU `indent -l120 -lc120` produced zero diff, and real-code `SA_MODE` probes verified the exact fix-count, latch-mode, assertion, and error-state behavior in both Debug and Release builds. Both linked TC PRs (`#4499`, `#5194`) are empty drafts (`changedFiles=0`).

| Item | Value |
|---|---|
| Engine PR | https://github.com/CUBRID/cubrid/pull/8776 (`OPEN`, non-draft, author `hornetmj`) |
| Base / Head / Merge-Base | `435b0b70059a3fb650fc18f148db4930a345ba04` / `0e29ef5cc43666e0220f7e917daddc41d76af749` / `435b0b70059a3fb650fc18f148db4930a345ba04` |
| Comparison | `git diff 435b0b70059a3fb650fc18f148db4930a345ba04 0e29ef5cc43666e0220f7e917daddc41d76af749` (`sha256` `2ecf8bfb611c02f18c1f73a28d1279ca1bc27bfcbd5e26d36d946f26993c8a53`); `src/storage/page_buffer.c` (`+32/-5`), `src/storage/page_buffer.h` (`+1/-0`) |
| Linked Public TC PR | https://github.com/CUBRID/cubrid-testcases/pull/4499 (`OPEN`, `DRAFT`, `tc/pr-8776`, head `054b3415c9649e08586af8693b7eb2227ddcde99`, `changedFiles=0`) |
| Linked Private TC PR | `CUBRID/cubrid-testcases-private-ex#5194` (private, `OPEN`, `DRAFT`, `tc/pr-8776`, head `d5853380d7ac5d7ccdb5e63f06c78c110a2db991`, `changedFiles=0`) |
| Snapshot | `2026-11-27 12:55 KST` (rechecked unchanged at `2026-11-27 13:17 KST`) |

---

## Verdict and Follow-up

- **Verdict:** `no-confirmed-findings` (GitHub review recommendation: **`APPROVE`**)
- **Follow-up review required:** `no` — all changed hunks, concurrency/recovery invariants, 4-variant compilation, static checks, formatting, and Debug/Release `SA_MODE` probes completed without confirmed PR-introduced defects.

---

## Confirmed Findings

None (`0` confirmed defects introduced or exposed by `CUBRID/cubrid#8776`).

---

## Safety Facts and Effects Outside the Diff

| # | Safety Fact | Source Locations | Evidence Level | Tested / Conditions |
|---|---|---|---|---|
| S1 | **Single-read pre-CAS check:** Because `bufptr->mutex` is held and `holder != NULL` ensures `fcnt >= holder->fix_count >= 1`, neither lock-free `pgbuf_lockfree_fix_ro` / `pgbuf_lockfree_unfix_ro` (which only adjust `fcnt` without changing `latch_mode` or dropping `fcnt` to `0`) nor mutex-protected latch-mode writers can transition `latch_mode` between line 7021 and line 7037. `buf_lock_acquired == true` always starts with `latch_mode == PGBUF_NO_LATCH` and `holder == NULL`. | [`page_buffer.c#L7016-L7029`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/storage/page_buffer.c#L7016-L7029), [`#L8445-L8470`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/storage/page_buffer.c#L8445-L8470), [`#L8536-L8558`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/storage/page_buffer.c#L8536-L8558), [`#L9208-L9212`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/storage/page_buffer.c#L9208-L9212) | **4** | Source trace of every `atomic_latch` writer + Debug `SA_MODE` probe (`r2w`: logged `0\|0` at `:7023`, aborted via `SIGABRT` at `:7028`). |
| S2 | **`NDEBUG` error-state preservation on `assert_release`:** In release builds, `assert_release` calls `er_set (ER_NOTIFICATION_SEVERITY, ..., ER_FAILED_ASSERTION, ...)`. Inside `er_set_internal()`, `ER_NOTIFICATION_SEVERITY` pushes/pops a temporary error stack frame when a prior error is active and calls `crt_error.clear_error ()` when none is active, leaving `er_errid()` untouched. | [`error_manager.h#L189-L190`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/base/error_manager.h#L189-L190), [`error_manager.c#L1480-L1484`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/base/error_manager.c#L1480-L1484), [`#L1584-L1595`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/base/error_manager.c#L1584-L1595) | **4** | Release `SA_MODE` probes (`r2w`, `r1w`, `r2w_cond`) confirmed `er_errid=0` at every step while logging `DEBUG` (`:7023`) and `NOTIFICATION CODE = -588` (`:7028`) to the server error log. |
| S3 | **Sub-case 2-2 sole-holder `fcnt++` lockstep, `perf_stat`, and unfix/wakeup:** `atomic_latch.impl.fcnt` is a 32-bit `int32_t` matching `int holder->fix_count`. Incrementing `new_impl.impl.fcnt++` (`:7118`) alongside `holder->fix_count++` (`:7201`) keeps `fcnt == holder->fix_count`, preserves `waiter_exists`, sets `hold_has_write_latch = 1` (`PERF_HOLDER_LATCH_MIXED` on unfix), routes subsequent unfixes off `pgbuf_lockfree_unfix_ro`, and wakes waiters via `pgbuf_wakeup_reader_writer()` only when `fcnt` reaches `0`. | [`page_buffer.c#L487-L496`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/storage/page_buffer.c#L487-L496), [`#L7113-L7119`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/storage/page_buffer.c#L7113-L7119), [`#L7201-L7206`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/storage/page_buffer.c#L7201-L7206), [`#L7383-L7555`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/storage/page_buffer.c#L7383-L7555) | **4** | Release `SA_MODE` probes verified `r2w` (`global_fcnt` `1->2->3->2->1->0`, `latch` `1->1->2->2->2->0`), `r1w` (`1->2->1->0`), `r2w_cond` (`1->2->3->2->1->0`), and `promote` control (`1->2->2->1->0`, zero `CODE=-588`). |
| S4 | **Format specifiers, headers, and build boundaries:** `VPID_AS_ARGS(&bufptr->vpid)` promotes `(short, int32_t)` to `(int, int)`, matching `%d\|%d` in `er_log_debug`. The header note above `#if !defined(NDEBUG)` covers both debug and release `pgbuf_fix` declarations; lines `7020-7029` sit outside `#if defined(SERVER_MODE)` and build in both `SERVER_MODE` and `SA_MODE`. | [`dbtype_def.h#L957-L976`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/compat/dbtype_def.h#L957-L976), [`page_buffer.h#L290-L346`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/storage/page_buffer.h#L290-L346) | **4** | `debug_gcc` (`1779/1779`) and `release_gcc` (`1681/1681`, `-Werror -DNDEBUG`) compiled `page_buffer.c` with 0 warnings/errors; 4-variant `-fsyntax-only` passed (`rc=0`). |
| S5 | **Caller & recovery/vacuum audit:** Audited `pgbuf_fix` / `pgbuf_ordered_fix` / `pgbuf_promote_read_latch` callers across `heap_file.c`, `btree.c`, `file_manager.c`, `disk_manager.c`, `overflow_file.c`, `oos_file.cpp`, `slotted_page.c`, `bestspace.cpp`, `vacuum.c`, `vacuum_oos.cpp`, `log_recovery.c`, and `log_applier.c`. No reachable path holds a READ fix and calls ordinary `pgbuf_fix(..., PGBUF_LATCH_WRITE, ...)` on the same page. | Storage, query, and transaction callers | **3** (source) + **CI** | `test_sql`, `test_medium`, and `test_sql_by_cci` passed on CI run `45880054266` at `0e29ef5cc4`. |

---

## Verification & Coverage Summary

- **Builds & Static Checks (`0e29ef5cc4`):**
  - `debug_gcc` full build+install: `1779/1779` targets succeeded (`0` warnings/errors on `src/storage/page_buffer.c` / `page_buffer.h`).
  - `release_gcc` (`-Werror -DNDEBUG`) full build+install: `1681/1681` targets succeeded (`0` warnings/errors on `src/storage/page_buffer.c` / `page_buffer.h`).
  - `cubrid-static-check` (`435b0b7005..0e29ef5cc4`): `exit=0` — `0` new cppcheck, `0` new clang-tidy (`bugprone-*`), `0` new PMD CPD clones, `0` complexity flags (`pgbuf_latch_bcb_upon_fix` CCN `43 -> 46`, length `337 -> 358`).
  - GNU `indent -l120 -lc120` on both changed files: `0` lines of diff.
  - `ctest` (`debug_gcc`, run without `cub-workenv init` so `$CUBRID`/`$CUBRID_DATABASES` were unset): 5 environment-free OOS unit tests passed; DB-dependent OOS tests did not run. No `unit_tests/page_buffer/` suite exists in the repository.
- **Real-Code `SA_MODE` Probes (`0e29ef5cc4`, `er_log_debug=yes`):**
  - **Debug (`debug_gcc`):**
    - `READ x2 -> WRITE`: `holder_fix_count=2`, `global_fcnt=2`, `latch=1` -> logged `pgbuf_latch_bcb_upon_fix: WRITE fix on page 0|0 this thread holds READ-latched` (`:7023`) and aborted immediately via `Assertion 'request_mode != PGBUF_LATCH_WRITE' failed.` at `src/storage/page_buffer.c:7028` (`SIGABRT`).
    - `pgbuf_promote_read_latch` control (`READ x2 -> promote -> UNFIX x2`): `promote rc=0`, `holder_fix_count` `1 -> 2 -> 2 -> 1 -> (nil)`, `global_fcnt` `1 -> 2 -> 2 -> 1 -> 0`, `latch` `1 -> 1 -> 2 -> 2 -> 0`, `er_errid=0`, exited normally.
  - **Release (`release_gcc`):**
    - `READ x2 -> WRITE -> UNFIX x3`: `global_fcnt` `1 -> 2 -> 3 -> 2 -> 1 -> 0`, `latch` `1 -> 1 -> 2 -> 2 -> 2 -> 0`, `pointers equal: yes`, `er_errid=0` at every step; server error log recorded `DEBUG` (`:7023`) and `NOTIFICATION CODE = -588` (`:7028`).
    - `READ x1 -> WRITE -> UNFIX x2`: `global_fcnt` `1 -> 2 -> 1 -> 0`, `latch` `1 -> 2 -> 2 -> 0`, `er_errid=0`.
    - `READ x2 -> WRITE (conditional) -> UNFIX x3`: `global_fcnt` `1 -> 2 -> 3 -> 2 -> 1 -> 0`, `latch` `1 -> 1 -> 2 -> 2 -> 2 -> 0`, `er_errid=0`.
    - `pgbuf_promote_read_latch` control: `promote rc=0`, `global_fcnt` `1 -> 2 -> 2 -> 1 -> 0`, `latch` `1 -> 1 -> 2 -> 2 -> 0`, `er_errid=0`, zero `CODE = -588` notifications.
- **HA Domain:** Marked Not Applicable (in-memory BCB latch accounting only; zero WAL, replication, or on-disk format changes; `log_applier.c` audited for caller safety).
- **CI at `0e29ef5cc4` (`run 45880054266` / `github-checks`):** `license`, `pr-style`, `code-style`, `cppcheck`, `memory-monitor-check`, `Greptile Review`, `build (debug)`, `build (release)`, `test_medium`, `test_sql`, and `test_sql_by_cci` all passed; `TC Merge Gate / Check TC PRs` failed while empty draft TC PRs remain open, and `gha-ci: test_shell` failed on develop-wide `CBRD-24777` volume-size mismatches plus one unrelated case reported as passing locally.

---

## Linked Testcase PRs (`cubrid-testcases#4499` & `cubrid-testcases-private-ex#5194`)

- **Status:** Both `cubrid-testcases#4499` and `cubrid-testcases-private-ex#5194` are empty `DRAFT` PRs (`changedFiles=0`, branch `tc/pr-8776`).
- **Assessment:** Neither TC PR adds test files. The PR description explains that no SQL execution path triggers ordinary `pgbuf_fix(..., PGBUF_LATCH_WRITE)` while holding a READ latch and asks reviewers whether a Catch2 unit test is needed. Because `unit_tests/` currently has no `page_buffer` suite, keeping the standalone probe or adding a Catch2 unit test is an optional non-blocking suggestion rather than a defect.

---

## Pre-Existing Issues Observed (Outside PR #8776 Scope)

Two independent specialist reviewers (`review-sys` and `review-conc`) converged on the following **pre-existing** issues in `pgbuf_latch_bcb_upon_fix()` (inherited from `58cef8e01` / `58cef8e01~1`, not introduced by PR #8776):
1. **Conditional latch refusal sets `waiter_exists = true` without queueing a waiter (`P2`, pre-existing in `58cef8e01`):** At [`src/storage/page_buffer.c#L7130`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/storage/page_buffer.c#L7130) (Sub-case 2-2 conditional) and [`#L7146`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/storage/page_buffer.c#L7146) (Case 3), `new_impl.impl.waiter_exists = true` is committed via CAS even when `condition == PGBUF_CONDITIONAL_LATCH` returns `ER_FAILED` at `#L7261-L7295` without enqueuing a waiter. While active holders remain, lock-free READ paths (`#L8462`, `#L8543`) are disabled, new non-holder READ fixes block/fail behind the phantom bit, and `PGBUF_VOID_ZONE` LRU placement (`#L7426`) is skipped when `fcnt` reaches `0` before `pgbuf_wakeup_reader_writer()` clears it. (Previously deferred in `3f48168311` `CBRD-28163`; recommended for a separate fix.)
2. **Blocked wake-up `holder->perf_stat` initialization (`P3`, pre-existing):** At [`src/storage/page_buffer.c#L7156`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/storage/page_buffer.c#L7156) and [`#L7308-L7328`](https://github.com/CUBRID/cubrid/blob/0e29ef5cc43666e0220f7e917daddc41d76af749/src/storage/page_buffer.c#L7308-L7328), `holder->perf_stat` sets only one latch bit without clearing the opposite bit on recycled/`malloc`'d `PGBUF_HOLDER` entries and uses the pre-sleep `buf_is_dirty` snapshot.
3. **Contract-violation `NDEBUG` corner cases (`58cef8e01~1` / `58cef8e01`):** Sole-holder Sub-case 2-2 does not check `next_wait_thrd->wait_for_latch_promote`; unconditional Sub-case 2-2 wait failure drops the caller's original READ fixes without restoring them (accurately documented by PR #8776 at `#L7122-L7125`); `pgbuf_unlatch_bcb_upon_unfix` decrements `fcnt` (`#L7383`) before checking `holder_status != NO_ERROR` (`#L7406`).
