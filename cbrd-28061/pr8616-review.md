# PR #8616 code review — CBRD-28061

Goal: review [CUBRID/cubrid#8616](https://github.com/CUBRID/cubrid/pull/8616) ("Bring back the contents of the first partial table page when the allocation that reused it is rolled back") and decide whether to approve.

**Result:** no confirmed defect. The saved page body is logged before the page is overwritten, restored by both the undo and the compensation redo, and older records without a body keep their behavior. The new testcase passed on a debug build of the exact head in CI, and that run includes the forced runtime rollback and the crash and restart. **Recommendation: approve.** The only failing check is `TC Merge Gate / Check TC PRs`, which is expected while TC PR #4996 is still open.

## Snapshot

| Item | Value |
| --- | --- |
| Repository / PR | CUBRID/cubrid #8616, author YeunjunLee, base `develop` |
| Base | `cf9ef288818d7bb8059606ae78edffa1dcbe942d` |
| Head | `7ef2e1115b01b32dda65e84233c2bd381f0e7ecb` |
| Merge base | `cf9ef288818d7bb8059606ae78edffa1dcbe942d` |
| Comparison | `git diff cf9ef288818d7bb8059606ae78edffa1dcbe942d 7ef2e1115b01b32dda65e84233c2bd381f0e7ecb` |
| Patch SHA-256 | `864eefbbec406ed36364e2f25f674566e3ce75a743b12c4bc8b640f14f04f8a0` |
| Snapshot | 2026-11-23T05:42:39Z. Head and base rechecked unchanged at 2026-11-23 14:52 KST |
| Linked testcase | CUBRID/cubrid-testcases-private-ex #4996, `tc/pr-8616` at `6fe39000e69dd9182a99fe74ed2551eca92354ab` (open) |
| Changed paths | `src/base/fault_injection.c`, `src/base/fault_injection.h`, `src/storage/file_manager.c`, `src/storage/page_buffer.c`, `src/storage/page_buffer.h` (+91 / −10). No renames, deletions, submodules, or binaries |

## Verdict and follow-up

- **Verdict:** `no-confirmed-findings`
- **Follow-up review required:** no. The configurations that were not exercised (listed below) are covered by source arguments that use code paths shared with other record types. Running them would add evidence, but nothing has to be done before merge.
- **Merge prerequisites outside code review:** this approval, then the TC finalization (merge TC PR #4996 into TC `develop` and rerun `Check TC PRs`).

## Confirmed findings

None.

## What changed and why it is safe

### The bug

`file_table_move_partial_sectors_to_header ()` ([file_manager.c:4723](https://github.com/CUBRID/cubrid/blob/7ef2e1115b01b32dda65e84233c2bd381f0e7ecb/src/storage/file_manager.c#L4723)) moves every sector of the first partial table page into the file header. It then deallocates that page and hands it to the same allocation as the new page. The old `RVPGBUF_DEALLOC` undo restored only the page type and the TDE flags. When the allocation's system operation rolled back, the table page came back holding the new page's body, so the partial table pointed at garbage.

### The fix

1. A new mode `PGBUF_DEALLOC_SAVE_CONTENTS` (= 2) appends the full `DB_PAGESIZE` body as a second undo crumb ([page_buffer.c:16206](https://github.com/CUBRID/cubrid/blob/7ef2e1115b01b32dda65e84233c2bd381f0e7ecb/src/storage/page_buffer.c#L16206), [:16252](https://github.com/CUBRID/cubrid/blob/7ef2e1115b01b32dda65e84233c2bd381f0e7ecb/src/storage/page_buffer.c#L16252)). The body is copied while the page is still write-fixed and before `file_alloc ()` initializes it. Only the partial-table-to-header path uses this mode ([file_manager.c:4844](https://github.com/CUBRID/cubrid/blob/7ef2e1115b01b32dda65e84233c2bd381f0e7ecb/src/storage/file_manager.c#L4844)).
2. `pgbuf_rv_dealloc_restore_contents ()` ([:16307](https://github.com/CUBRID/cubrid/blob/7ef2e1115b01b32dda65e84233c2bd381f0e7ecb/src/storage/page_buffer.c#L16307)) restores the body when `rcv->length` is `sizeof (PGBUF_DEALLOC_UNDO_DATA) + DB_PAGESIZE`. When the length is the old 8 bytes it does nothing.
3. The undo ([:16329](https://github.com/CUBRID/cubrid/blob/7ef2e1115b01b32dda65e84233c2bd381f0e7ecb/src/storage/page_buffer.c#L16329)) restores the body and copies the whole undo payload into its `RVPGBUF_COMPENSATE_DEALLOC` record ([:16364](https://github.com/CUBRID/cubrid/blob/7ef2e1115b01b32dda65e84233c2bd381f0e7ecb/src/storage/page_buffer.c#L16364)). The compensation redo ([:16379](https://github.com/CUBRID/cubrid/blob/7ef2e1115b01b32dda65e84233c2bd381f0e7ecb/src/storage/page_buffer.c#L16379)) restores the body as well.
4. Two debug-only fault injection codes (200002 FAIL, 200003 HOLD) are armed only on the user-page reuse branch and reset at the common exit of `file_alloc ()`.

### Safety facts

| # | Fact that makes the change safe | Evidence | Level |
| --- | --- | --- | --- |
| S1 | The body is captured before it is overwritten. `log_append_undoredo_crumbs` copies the crumbs into owned log-node memory synchronously, so no borrowed page pointer survives the call | `prior_lsa_alloc_and_copy_crumbs` in log_append.cpp (allocation reviewer). The dealloc is called before the `NEW_PAGE` fix and `f_init` in `file_alloc ()` | source |
| S2 | `memcpy (pgptr, …, DB_PAGESIZE)` covers only the page body. `PAGE_PTR` points past `FILEIO_PAGE_RESERVED`, so the restored ptype, pflag and LSA are not overwritten | `DB_PAGESIZE` is `db_User_page_size` (storage_common.h:101). ptype and pflag are set through `prv` before the copy | source |
| S3 | Redo of the dealloc with offset 2 behaves like `KEEP`: it sets `PAGE_UNKNOWN` and does not clear the body | `pgbuf_rv_dealloc_redo` checks only `== PGBUF_DEALLOC_CLEAR_CONTENTS` ([:16284](https://github.com/CUBRID/cubrid/blob/7ef2e1115b01b32dda65e84233c2bd381f0e7ecb/src/storage/page_buffer.c#L16284)) | source |
| S4 | The undo asserts `ptype == PAGE_UNKNOWN`, and this holds on the runtime rollback path. Records logged after the dealloc are undone first, and `RVHF_NEWPAGE` (heap init, [heap_file.c:3065](https://github.com/CUBRID/cubrid/blob/7ef2e1115b01b32dda65e84233c2bd381f0e7ecb/src/storage/heap_file.c#L3065)) and `RVPGBUF_NEW_PAGE` (file_manager.c:5345) both undo through `pgbuf_rv_new_page_undo`, which sets `PAGE_UNKNOWN`. `RVPGBUF_INIT_NEW_PAGE` is `RCV_IS_NOTHING_TO_UNDO` and is skipped. The full-body copy then overwrites whatever the init left | recovery.c:261, recovery.h `RCV_IS_NOTHING_TO_UNDO`; exercised by the TC's FAIL case | source + runtime |
| S5 | Large undo and compensation payloads are handled generically: the undo data is unzipped in `log_rollback_record` (log_manager.c:7505, unzip buffer sized `IO_PAGESIZE` > 8 + `DB_PAGESIZE`), and the compensation passes through the same zip and redo machinery that B-tree records already use | log_manager.c:7543–7578 | source |
| S6 | Compatibility with old logs: records written before this change have length 8, so neither restore path does anything. The removed `assert (rcv->length == sizeof …)` lines are replaced by the length dispatch | `pgbuf_rv_dealloc_restore_contents` | source |
| S7 | Other consumers of the records: `RVPGBUF_DEALLOC` and `RVPGBUF_COMPENSATE_DEALLOC` have no dump function (recovery.c:796–807), and `git grep` finds no other reader of `PGBUF_DEALLOC_UNDO_DATA`. HA, CDC and the log appliers do not decode these page-level records | `git grep` at head | source |
| S8 | Ordering against the file header: the header link-change record comes before the dealloc, so the undo restores the table page body before the header link that reaches it is restored. The file-header write latch is held from `file_alloc` :5387 until the sysop ends, so no other thread can observe the intermediate state | allocation reviewer, file_manager.c:4779–4847, 5387, 5534–5545 | source |
| S9 | After a committed allocation, the inner records are not undone physically. A later transaction rollback runs the logical undo of `RVFL_ALLOC`, and by then the header already owns the moved sectors, so the old table body is not needed | `file_alloc` sysop end | source |
| S10 | The FI state machine arms only in the reuse branch, does not leak into the next allocation, and compiles out under `NDEBUG` (`FI_SET`/`FI_RESET` are empty and `FI_TEST` is `(NO_ERROR)`, fault_injection.h:39–44). `fi_state` and the HOLD block sit inside `#if !defined (NDEBUG)` | `fi_probe.py` replay (below) | runtime (unit) |
| S11 | Log volume grows by one page, only once per emptied first partial table page. File table pages are never TDE-encrypted, so logging the body in plaintext exposes no user data | PR remarks; ftab pages hold sector entries only | source |

## Coverage and verification

| Owner | Paths | Invariant | Result |
| --- | --- | --- | --- |
| Allocation reviewer (gpt-6.1-sol, high) | file_manager.c, fault_injection.c/h | Capture before overwrite, latch and error paths, FI lifecycle, nesting | No finding. Report: allocation.md in the run directory |
| Recovery reviewer (gpt-6.2-sol, high) | page_buffer.c/h | Body boundaries, undo/CLR/redo, legacy records, consumers | **No report produced.** The coordinator (Claude Opus 5.5) took over this scope by source inspection (S2–S7) |
| Coordinator | all 5 paths, TC #4996 | CI and TC identity, runtime evidence, adjudication | Done |

Shared challenge: *is the page body saved before it is overwritten, and restored before later file-table undo reads it?* The allocation reviewer answered yes (S1, S8) independently. Because the recovery seat dropped out, the second answer came from the coordinator, who had already read the first. That is not a fully independent second check.

Checks run:

| Check | Revision / config | Result |
| --- | --- | --- |
| CI `gha-ci` run [44340772709](https://github.com/CUBRID/cubrid/actions/runs/44340772709): build debug and release, test_shell, test_sql, test_medium, test_sql_by_cci | engine `7ef2e11…`, TC `6fe3900…` (= current #4996 head, compare `identical`) | all pass. test_shell: 3604 passed, 0 failed, 30 skipped |
| New TC `shell/_06_issues/_26_2h/cbrd_28061/cases/cbrd_28061.sh` | debug build (`build_mode: debug`), shard 33 | pass (21.9 s). It covers the FAIL (runtime rollback) case and the HOLD → kill → restart case, then checks for an empty heap, a successful reinsert, and `checkdb` |
| `python3 fi_probe.py`: compiles the pinned production `fi_set/fi_reset/fi_test/fi_state/fi_handler_fail` and checks disabled gate, arm, fail, reset, rearm | head | PASS |
| Local `cubrid-build` debug_gcc | head | **failed in an unchanged file** `src/broker/cas_cgw_odbc.c:1890` (`toupper` not declared, missing `<cctype>` with this toolchain). The PR does not touch this file, CI debug and release builds pass, and the failure is not attributable to the PR |
| `TC Merge Gate / Check TC PRs` | — | fail: "TC changes are not on TC develop yet". Expected until TC finalization |

Not exercised:

- A crash during the rollback itself, after the CLR is written, so that the compensation redo runs at restart. Source: S3 and S5.
- Page sizes other than the CI default, and the zip branch for the 8 KB+ undo payload. Source: S5.
- TDE-encrypted files. The page that gets reused is an ftab page, which is never encrypted.
- I did not run the TC against `develop` to confirm that it fails there. The PR description reports failure on develop for all three cases, in both debug and release.

## Unverified risks and dropped candidates

- No material unverified risk.
- Dropped candidates (coordinator): (a) "the undo assert `ptype == PAGE_UNKNOWN` fails after `f_init` set `PAGE_HEAP`" was disproven by S4. (b) "redo with offset 2 clears the body" was disproven by S3. (c) "the FAIL hook outside `#if !defined (NDEBUG)` changes release behavior" was disproven by S10.
- Allocation reviewer: no candidates raised. Recovery reviewer: no report.
- Pre-existing, unrelated: the `cas_cgw_odbc.c` missing include (local toolchain only).

## Approval gate (at 2026-11-23 14:52 KST)

```
CUBRID/cubrid#8616
hornetmj APPROVED
vimkim no review (pending request)
BLOCKED
```

The PR is blocked only on vimkim's review. hornetmj approved at head `7ef2e11`. TC PR #4996 is approved by hornetmj at `6fe3900`.

## Budget accounting

- Mode: bounded (no user limit). No hard cap was enforced.
- Planned: 2 specialist seats at 7 min each plus a 9 min coordinator reserve (16 min envelope). Actual: 1 specialist report. The recovery seat ended without a report and was not restarted. Coordinator work continued in a second session, which exceeded the 16 min wall-clock target. Token usage is unknown, because no per-agent telemetry is available.
