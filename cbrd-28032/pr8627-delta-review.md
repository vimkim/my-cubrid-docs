# CUBRID/cubrid PR #8627 (`CBRD-28032`) delta review: `538d15e954..02a3697367`

Goal: re-review the fix that `xmilex-git` pushed in reply to the `CHANGES_REQUESTED` review on `538d15e954` ([reply](https://github.com/CUBRID/cubrid/pull/8627#issuecomment-7161006139)), together with the companion regression testcase in [CUBRID/cubrid-testcases#4318](https://github.com/CUBRID/cubrid-testcases/pull/4318).

**Result:** the replay OID-buffer overflow (the blocking item) is fixed. A debug server was run on the new head with the harness that crashed `538d15e954`. The new fallback branch ran, no slice was copied past its buffer, and every result matched the baseline. The two non-blocking suggestions (immediate reporting of deadlock and out-of-memory errors, and the regression TC) are also done.

## 1. Snapshot, verdict, and follow-up

| Item | Value |
| --- | --- |
| Review date (`Asia/Seoul`) | 2026-11-25 |
| PR | [CUBRID/cubrid#8627](https://github.com/CUBRID/cubrid/pull/8627) (author `xmilex-git`, base `develop`) |
| Comparison | `git diff 538d15e9545c9d3f91833988d598996ead15320a 02a369736759612f75630dab0a6549c5267299b6` (one commit, its parent is the previous reviewed head) |
| Previous reviewed head | `538d15e9545c9d3f91833988d598996ead15320a` (review state `CHANGES_REQUESTED`) |
| Reviewed head | `02a369736759612f75630dab0a6549c5267299b6` |
| PR base / merge base | `8b6334edc8c3dde56d1765eaf28e3651557b5bed` / `8b6334edc8c3dde56d1765eaf28e3651557b5bed` |
| Patch SHA-256 | `a6ec836cfa12ea525e7f7b04afe8d2f71324dc1f15994b1814799ba27150a48e` |
| Changed paths | `src/query/query_executor.c` (+3/-3), `src/query/scan_manager.c` (+4/-1) |
| Testcase PR | [CUBRID/cubrid-testcases#4318](https://github.com/CUBRID/cubrid-testcases/pull/4318) head `2c54a38f66e3fee9fb8b98dcf0dc97e7f0752e36`, files `sql/_36_guava/cbrd_28032/{cases,answers}/cbrd_28032_batch_join_held_rows.*` |
| **Verdict** | **`no-confirmed-findings`** |
| **Follow-up review required** | **no**. The blocking item is fixed and the fix ran on a debug server. No material unverified risk remains in the delta. |

Earlier snapshots: [pr8627-review.md](pr8627-review.md) (head `b52b26697c`; `F-1` and `F-2`, fixed before `772b4695b3`). The `772b4695b3..538d15e954` delta review is in the [PR review of 2026-11-25](https://github.com/CUBRID/cubrid/pull/8627#pullrequestreview-6055827881).

## 2. Delta items

### 2.1 Replay OID-buffer overflow (blocking on `538d15e954`): fixed

**The defect.** A correlated-subquery batch collects the OIDs of a held row with one scan, closes that scan, and later replays the row with a newly opened scan. Closing a scan returns its OID buffer to the server-wide pool, and the new scan can get a different buffer from the pool. `scan_alloc_iscan_oid_buf_list ()` reuses a pooled buffer when its capacity is enough for the *current* `index_scan_oid_buffer_size`. So after the parameter is lowered (`PRM_USER_CHANGE`), the pool can contain both large and small buffers. Collection could then fill 5,000 OIDs into a 32,768-OID buffer, and the replay could get a new 4,086-OID buffer. `scan_index_take_nl_slice ()` then ran `memcpy` past the end of it (debug: assert; release: a silent heap overflow of 7,312 bytes).

**The fix** ([`scan_manager.c` L6906-L6916](https://github.com/CUBRID/cubrid/blob/02a369736759612f75630dab0a6549c5267299b6/src/query/scan_manager.c#L6906-L6916)): in the `S_BEFORE` branch of `scan_next_index_scan ()`, the slice is used only if `nl_slice_cnt <= oid_list->capacity`. Otherwise the slice is dropped (`nl_slice_cnt = -1`) and the scan calls `call_get_next_index_oidset (..., true)`.

Safety facts checked against the source at `02a3697367`:

- **One consumer covers both batches.** `scan_next_index_scan ()` is the only reader of `nl_slice*`. The fields at `scan_manager.h:499-501` only mirror the layout. The join batch sets the slice in `qexec_nl_batch_open_row ()` ([L13224-L13229](https://github.com/CUBRID/cubrid/blob/02a369736759612f75630dab0a6549c5267299b6/src/query/query_executor.c#L13224-L13229)) and the subquery batch in `qexec_sq_batch_give_slice ()` ([L14508-L14518](https://github.com/CUBRID/cubrid/blob/02a369736759612f75630dab0a6549c5267299b6/src/query/query_executor.c#L14508-L14518)). Both reach the new check.
- **The fallback is the baseline path.** The `else` branch is the call that every index scan without a batch makes. A slice is given only for a row whose collection was `complete` (all its OIDs in one buffer). Thus the dropped slice has no partial index cursor to continue from, and the scan reads the key again from its start. The collect and the replay run in the same statement and use the same MVCC snapshot, so the re-read returns the same OIDs. Without the slice, the read-ahead fields (`ahead_next`, `ahead_distance`) keep the values from the scan reset, so the only effect is that the join's page hints for that row are not used.
- **Boundaries.** `capacity` counts OIDs (`btree.h:448`), and so does `nl_slice_cnt`. `nl_slice_cnt == capacity` fills the buffer exactly, which is safe. `nl_slice_cnt == 0` still goes to `scan_index_take_nl_slice ()` and returns `S_END`. When `nl_slice_cnt < 0` (no slice), `&&` stops the evaluation first, so `oid_list` is not dereferenced for covering scans (`oid_list == NULL`). A slice is given only after `scan_index_nl_batch_ok ()` has required `oid_list != NULL` and a scan that is not covering. The replay uses the same XASL spec, so coverage cannot change between the collect and the replay. `scan_index_take_nl_slice ()` dereferenced `oid_list` already before this delta, so the check adds no new NULL dereference.
- **Repeated re-reads.** Each slice is used once: the giver sets the slice for one row and then sets `slice_cnt = -1` (and the join clears `nl_slice_cnt` after the row). The fallback branch also clears it. A later row gets a new slice and is checked again.
- **The other direction is still guarded.** `bb996f6e43` handles a replay buffer that is larger than the collection buffer in `scan_index_nl_batch_collect ()` (`oids_count > room`). That code did not change.

**Runtime verification (coordinator, debug server).** The `debug_gcc` build of `02a3697367` was installed and server `tdb` was started with `index_scan_oid_buffer_size=256K`. This is the same harness that gave two SIGABRT cores (`assert (count <= isidp->oid_list->capacity)`) on `538d15e954` in the previous review. The steps were:

1. A 6-way index join filled the pool with large buffers.
2. `set system parameters 'index_scan_oid_buffer_size=1K'`.
3. Four concurrent `csql -C` sessions ran for 60 s. Two ran 6-way index joins (3,000 statements each). Two ran the target statement (300 statements each, with `memoize_memory_limit=0`):

   ```sql
   select /*+ recompile ordered use_nl no_parallel_scan */ count(*) from o, x
   where x.k = o.a and x.v <= (select /*+ no_subquery_cache */ max(b.v) from b where b.k = x.k);
   ```

   Here `b` has 5,000 OIDs for each key.
4. gdb was attached in batch mode with conditional breakpoints on the new fallback line (`scan_manager.c:6914`, only when `nl_slice_cnt > oid_list->capacity`), on the slice-take line (`6910`, only when `nl_slice_cnt >= 1000`), and on the `take` assert line (`6637`, only when `count > capacity`).

| Check | Result |
| --- | --- |
| Fallback taken (slice larger than the replay buffer) | **2 times**, `slice_cnt=5000` with a replay buffer of `cap=4086`. The pool then held both 4,086- and 8,192-OID buffers. |
| Slice taken normally (`>= 1000` OIDs, in capacity) | 352 times |
| Copy past the buffer (`count > capacity` in `scan_index_take_nl_slice ()`) | **0** |
| Target results | 600 of 600 are `1`, which equals the `USING INDEX NONE` baseline (`1`) |
| Join results | 6,000 of 6,000 are `0` (no change) |
| Server | stayed up; no new core file; no assert in the server error log |

### 2.2 Deadlock, out-of-memory and interrupt errors are not deferred or cleared: done

The delta makes three sites use `qexec_is_value_error ()` ([L1679-L1684](https://github.com/CUBRID/cubrid/blob/02a369736759612f75630dab0a6549c5267299b6/src/query/query_executor.c#L1679-L1684)). That function returns false for `NO_ERROR`, `ER_INTERRUPTED`, `ER_LK_UNILATERALLY_ABORTED` and `ER_OUT_OF_VIRTUAL_MEMORY`. The three sites are:

| Site | Before | After |
| --- | --- | --- |
| `qexec_nl_batch_defer_error ()` [L12827](https://github.com/CUBRID/cubrid/blob/02a369736759612f75630dab0a6549c5267299b6/src/query/query_executor.c#L12827) (an error from a read-ahead of the outer is kept until the held rows are joined; it is dropped if LIMIT, ROWNUM or EXISTS ends the statement first) | kept everything except `ER_INTERRUPTED` | keeps only value errors |
| `qexec_nl_batch_add ()` [L13165](https://github.com/CUBRID/cubrid/blob/02a369736759612f75630dab0a6549c5267299b6/src/query/query_executor.c#L13165) (an index collect fails: the error is cleared and the row path reads the index again) | cleared everything except `ER_INTERRUPTED` | clears only value errors |
| `qexec_sq_batch_add ()` [L14335](https://github.com/CUBRID/cubrid/blob/02a369736759612f75630dab0a6549c5267299b6/src/query/query_executor.c#L14335) (the subquery scan fails to open, start or collect) | cleared everything except `ER_INTERRUPTED` | clears only value errors |

- `ER_LK_UNILATERALLY_ABORTED` (-72) is the error that a deadlock victim receives (`lock_manager.c:2726`). It is now returned at once on all three paths, so a LIMIT or a re-read that succeeds cannot hide the server-side abort.
- A lock timeout or a deadlock timeout (`ER_LK_OBJECT_TIMEOUT_*`, `ER_LK_OBJECT_DL_TIMEOUT_*`, `lock_manager.c:2660`) does not abort the transaction. It is still deferred. This is correct: the error is raised again when the row path reaches the row, and it is dropped only when the statement ends before that row. A statement without a batch would not have read that row.
- There is one change in behavior that is not in the reply. Before this delta, if `qexec_sq_batch_add ()` failed to `malloc` its own `b->oids` buffer, the error was cleared and the subquery ran without a batch. Now the statement fails with `ER_OUT_OF_VIRTUAL_MEMORY`. The join batch already failed this way when its own buffers could not be allocated (`qexec_nl_batch_add ()` L13106-L13133), so the two batches are now consistent. This is not a defect.
- Runtime: a deadlock or OOM injection was not run. The author also checked this only in the code. The classification is three call sites of an existing predicate, and its error codes were checked against the lock manager. Evidence level: source.

### 2.3 Regression TC `cbrd_28032_batch_join_held_rows.sql` (#4318): the four scenarios are covered

| Claimed scenario | Statements in the case | Expected answer |
| --- | --- | --- |
| 1. Duplicate rows (a join step whose keys memoize holds, with a subquery batch) | `hr_n` × `hr_c` with a correlated `max()` in the select list; total and grouped counts | `48`; `16` rows for each of keys 1-3; `48` |
| 2. The error of an outer row that LIMIT, EXISTS or ROWNUM does not reach | `10 / (o.k - 2)` on outer row `k = 2`, while the rows of `k = 1` fill `LIMIT 3`, `EXISTS` and `rownum <= 3`; the same join read to its end | `3, 1, 1`; `1`; `3, 1, 1`; then `Error:-539` |
| 3. An error that CASE or OR keeps from a subquery key | `CASE WHEN i.denom <> 0 ...` and `o.flag = 0 OR ...` with `100 / i.denom` and `cast(i.bad as int)` | 4 statements, each 3 rows, no error |
| 4. Repeated scan of a hierarchical query | `CONNECT BY prior id = pid` with `SET TRACE ON` | `8000, 12000` (4,000 roots, each with one child); the `CONNECTBY` index scan has no `bitmap heap lookup` line |

The TC has no case for the replay overflow (2.1). That defect needs a runtime parameter change and a pool that holds buffers of mixed sizes when the replay opens, so it cannot be made deterministic in a SQL TC. Section 2.1 gives the runtime evidence for it.

## 3. Coverage and limits

- Coverage: both changed hunks and the code around them were read: all `nl_slice*` producers and consumers, the OID-buffer pool `scan_alloc_iscan_oid_buf_list ()`, the scan open and close, `scan_index_nl_batch_ok ()`, `scan_index_nl_batch_collect ()`, the error paths of both batches, and the lock manager error codes. The TC case and answer files were read at `2c54a38f66`. The 26 other files in #4318 (answer refreshes from earlier commits) are outside this delta.
- The coordinator did the review without subagents because the delta is two hunks. There is no independent second reviewer. Budget: within the coordinator's default bounded mode. Usage was not metered.
- Not run: deadlock or OOM fault injection (2.2), a release build of the overflow harness (the overflow does not happen because the copy is not made), and the #4318 TC locally (the author reports CTP 545/545 and failures on `772b4695b3`). The CI result of the author's `/run all` is outside this code review.
- PR movement: the head was `02a3697367` when this report was written. It is checked again before the comment and the approval are published.
