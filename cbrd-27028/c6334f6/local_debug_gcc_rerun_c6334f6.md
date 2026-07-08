# Local `debug_gcc` Rerun for PR #7415 / `c6334f6`

Date: 2026-07-08 KST

Worktree: `/home/vimkim/gh/cb/oos-m2-plan1-file-oos-utilities`

Source HEAD: `c6334f6a69a1`

Build preset: `debug_gcc`

Local install note: the installed binaries were rebuilt at 2026-07-08 16:54 KST, but `cubrid_rel` still reported stale generated metadata `11.5.0.2367-36c6ffd`. `file_manager.c.o` was newer than `src/storage/file_manager.c`, so the PR source was compiled into the debug build.

## Question

Compared to the pre-PR behavior, did PR #7415 change the failure from an assertion/core-dump style utility failure into normal output diffs?

Yes for the PR-relevant utility paths. PR #7415 changed `FILE_OOS` handling in `src/storage/file_manager.c`:

- `file_header_dump_descriptor()`: `FILE_OOS` no longer asserts; it prints `OOS file`.
- `file_tracker_get_and_protect()`: `FILE_OOS` no longer asserts during interruptible tracker iteration; it is skipped because owner class metadata is not available yet.
- `file_tracker_item_spacedb()`: `FILE_OOS` no longer `assert_release(false)`; pages are folded into `SPACEDB_HEAP_FILE`.

Before this PR, debug builds could hit `assert(false)` / `assert_release(false)` when generic utility code encountered `FILE_OOS`. After this PR, the local failing TCs reached CTP comparison points and produced answer/output mismatches.

## Local Run Command

Each TC was run sequentially with:

```bash
just shell-debug <test-directory>
```

Captured summary:

```text
tbl_enc_14      status=1 duration=37s
bug_bts_9836   status=1 duration=140s
bigPageSize    status=1 duration=236s
cbrd_20145_1   status=1 duration=44s
bug_bts_14120  status=1 duration=43s
cbrd_22803     status=1 duration=63s
tbl_enc_08     status=1 duration=37s
cbrd_26527     status=1 duration=80s
```

No `coredumpctl` entry and no local `core*` file were found for the run window.

## Result Comparison

| TC | Local `debug_gcc` result | Matches CI failure class? | Core/assert evidence? |
| --- | --- | --- | --- |
| `tbl_enc_14` | `result.log` lacks answer-side `MULTIPAGE_OBJECT_HEAP` / `Overflow for HFID`. | Yes. | No. |
| `bug_bts_9836` | Cases 2 and 3 add OOS error codes `-1378,-1380,-1381` in `call_stack_dump_activation_list`. | Yes. | No. |
| `bigPageSize` | First CTP attempt reproduced CI-style `cl`/`bl` LOB `file:` locator mismatch. A later retry overwrote the final `.result` with a `loaddb` `Server no longer responding` diff. | First attempt yes; final local retry differs. | No core found. |
| `cbrd_20145_1` | `MNT_SERVER_COPY_STATS` receive size differs: `86400` vs `90864`. | Yes. | No. |
| `bug_bts_14120` | Server `call_stack_dump_activation_list` adds OOS error codes `-1378,-1380,-1381`. | Yes. | No. |
| `cbrd_22803` | Debug answer uses `test1_debug.answer` / `test2_debug.answer`; counters differ more broadly than CI release by exact page-buffer values. | Same exact-counter drift class, not same numeric diff. | No. |
| `tbl_enc_08` | `result.log` lacks answer-side `vfid`, `MULTIPAGE_OBJECT_HEAP`, and `Overflow for HFID`. | Yes. | No. |
| `cbrd_26527` | Cases 1-3 pass; Case 4 cannot extract `MULTIPAGE_OBJECT_HEAP` HFID for `dba.tbl`. | Yes. | No. |

## `bigPageSize` and PR #7416

PR #7416 (`https://github.com/CUBRID/cubrid/pull/7416`) is an OOS raw-record expansion fix. It threads `HEAP_OOS_EXPAND_POLICY` through heap/locator APIs and changes `locator_lock_and_return_object()` so raw records shipped via `LC_COPYAREA` are fetched with `HEAP_WITH_OOS_EXPAND`.

That PR may fix TCs where inline OOS OID slots leak through raw `RECDES` paths, including some `unloaddb`/copy-area style failures. However, the `bigPageSize` failure observed in CircleCI job 135930 and in the first local `debug_gcc` attempt was different:

```text
cl : file:.../ces_700/...  vs  file:.../ces_052/...
bl : file:.../ces_573/...  vs  file:.../ces_295/...
```

The row data matched; only volatile LOB locator strings differed. PR #7416 does not change `bigPageSize.sh` and does not visibly normalize LOB locator strings. Therefore, do not assume PR #7416 fixes this exact `bigPageSize` mismatch without running the TC on PR #7416.

## Conclusion

For the PR #7415 utility cases, the behavior changed from potential `FILE_OOS` assertion/fatal paths to ordinary output mismatches. The local `debug_gcc` rerun supports the original CI classification:

- `tbl_enc_08`, `tbl_enc_14`, `cbrd_26527`: OOS-vs-legacy-overflow testcase assumptions.
- `bug_bts_9836`, `bug_bts_14120`: answer files missing OOS error codes.
- `cbrd_20145_1`, `cbrd_22803`: exact runtime counter/stat output drift.
- `bigPageSize`: still best treated as a separate LOB locator determinism/testcase issue unless PR #7416 is proven by a direct rerun.
