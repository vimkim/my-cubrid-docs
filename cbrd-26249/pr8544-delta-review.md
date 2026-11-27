# Delta Code Review — CUBRID/cubrid#8544 (`[CBRD-26249]`)

- **Review date (`Asia/Seoul`):** `2026-11-26` (snapshot synced `2026-11-27`)
- **Jira:** [CBRD-26249](https://jira.cubrid.org/browse/CBRD-26249) · Prior review: [pr8544-review.md](pr8544-review.md)
- **Verdict:** **`no-confirmed-findings`** (`Follow-up review required: no`, `APPROVE` recommended)

## Snapshot

| Field | Value |
|---|---|
| Repository | `CUBRID/cubrid`, PR [CUBRID/cubrid#8544](https://github.com/CUBRID/cubrid/pull/8544) (`hornetmj`, `CBRD-26249-delvoldb-last` → `develop`) |
| Comparison | `git diff --binary --no-ext-diff --no-textconv 435b0b70059a3fb650fc18f148db4930a345ba04 8fe6fdcb379aa9031ac5b11d37921a7b7dd71f42` |
| Base = merge base | `435b0b70059a3fb650fc18f148db4930a345ba04` |
| Head | `8fe6fdcb379aa9031ac5b11d37921a7b7dd71f42` |
| Patch | sha256 `870110da008e9635dcb28e7fb2640d458c02d01b919aade688dcd958720c9899` (25 files, `+1,156/-128`) |
| Locally built & runtime-tested snapshot | Base `2de1681185df78fecc7b66e24e328f1f2e8468a3` → head `f0d47c1709bb008cc3826f15febd16592161cdcf` (sha256 `c4b3b52c2f1d55312308e3aa6181958dd3e951f956a987928f0dac37aea92bd4`). Commit `8fe6fdcb37` is a conflict-free `develop` merge with **zero PR-diff hunk changes** relative to `f0d47c1709` (only the `src/communication/network_interface_cl.c` git blob index changed due to unrelated `develop` work). |
| Delta commits since prior review (`e54b7611e6`) | `5c68ac6b97` (merge), `054ee97eab` (F2), `a51361a868` (F1), `257bab3303` (F3), `8d31bf076b` (U-R2), `f0d47c1709` (merge), `8fe6fdcb37` (conflict-free `develop` merge) |
| Linked TC PRs | [CUBRID/cubrid-testcases#4210](https://github.com/CUBRID/cubrid-testcases/pull/4210) (`2d223ee00e`, 0 files changed); [CUBRID/cubrid-testcases-private-ex#4918](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4918) (`4c10a3009e`, 2 files changed) |

## Resolution of Prior Findings & Rebase

1. **F1 (`a51361a868`, `disk_delete_volume_rollback`):** In `src/storage/disk_manager.c`, when the link of the previous permanent volume differs from `fileio_get_volume_label (volid, PEEK)`, it is repaired with an unlogged `disk_set_link(..., false, DISK_FLUSH)` before `logpb_recreate_volume_info`. Because `log_skip_logging` is a no-op, the page LSA stays `>= CLR LSA` (preventing CLR redo from reverting it), and `logpb_checkpoint` synchronizes all dirty pages before advancing the checkpoint LSA. Verified on `f0d47c1709` across all 4 combinations (`MODE={restart,crash} x KEEP_OLD={0,1}`), including deleting `_vinf` afterward to confirm `spacedb -S` and `checkdb -S` succeed purely from the repaired on-disk link (`rc=0`).
2. **F2 (`054ee97eab`, `disk_delete_volume_extension`):** Logs `RVPGBUF_FLUSH_PAGE` undo for `(prev_volid, DISK_VOLHEADER_PAGE)` immediately before `disk_set_link(..., NULL_VOLID, ...)`. On rollback, `prev_volid`'s restored header is flushed before `boot_Db_parm` is reverted to `n`. Verified on `f0d47c1709` by re-pinning gdb to `pgbuf_rv_flush_page` and end-of-undo `pgbuf_flush_all` (`src/transaction/log_recovery.c:5385`): all 4 combinations (`DWB={off,on} x KILL_POINT={1,2}`) recovered cleanly on subsequent restarts without manual repair (`rc=0`).
3. **F3 (`257bab3303`, `delvoldb`):** Adds `DELVOLDB_MSG_FILE_LEFT = 37` in `msg/{en_US,ko_KR}.utf8/utils.msg` and `src/executables/utility.h`. After `db_shutdown()` and `DELVOLDB_MSG_DONE`, checks `access(info.vol_fullname, F_OK) == 0` and prints the leftover file path via `PRINT_AND_LOG_ERR_MSG`. `msgcat_message` lazily reopens the catalog and `util_log_write_errstr` has no `er_*` dependency. Verified on `f0d47c1709` in both `-i` and interactive (no `-i`) modes on both `debug_gcc` and `release_gcc` (`rc=0`, leftover path on `stderr`, `checkdb` `rc=0`).
4. **U-R2 (`8d31bf076b`, `disk_delete_volume_extension`):** Calls `(void) dwb_synchronize(thread_p, fileio_get_volume_descriptor(prev_volid), NULL)` after cutting the link, forcing `dwb_flush_force` (DWB on) or `fsync` (DWB off) before sysop commit and unlink.
5. **Rebase & Renumbering (`5c68ac6b97`, `f0d47c1709`, `8fe6fdcb37`):** `RVDK_DELETE_VOLUME = 146`, `RV_fun` has 147 contiguous aligned entries (0..146), `ER_DISK_CANNOT_DELETE_VOLUME = -1423`, `ER_LAST_ERROR = -1424`, and `cubrid.msg` (en/ko) set 5 is contiguous 1..1424. Commit `8fe6fdcb37` cleanly merged `develop` (`435b0b7005`) with zero changes to any PR hunk.

## Linked Testcase PRs & CI Status

- `CUBRID/cubrid-testcases#4210` (`2d223ee00e`) carries no changed files and was updated with `develop`.
- `CUBRID/cubrid-testcases-private-ex#4918` (`4c10a3009e`) updates the administrator utility list expectation (`bug_bts_15912`) to include `delvoldb` and adds a new shell testcase covering refusals (non-last, volume 0, prompt cancel), last temporary/data volume deletion and volid reuse, debug fault-injection crash recovery (FI 100003/100004), `restoredb` replay, non-writable directory leftover-path reporting (F3), and debug `restoredb -u` relocation (F1). It passed locally at `f0d47c1709` / `14c89976cf` on both `debug_gcc` (25/25 checks) and `release_gcc` (15/15 checks, FI cases skipped), and both testcases passed in CI run `45767654652` (prior to the `develop` merge, where 123 unrelated failures came from stale `tc/pr-8544` bases).
- After merging `develop` into `#8544`, `#4210`, and `#4918`, CI run `45848256460` on `8fe6fdcb37` passed `build (debug)`, `build (release)`, `test_medium`, `test_sql`, `test_sql_by_cci`, and all PR static checks (`code-style`, `cppcheck`, `license`, `memory-monitor-check`, `pr-style`). `gha-ci: test_shell` and `Check TC PRs` remain failing on GitHub and must be checked separately before merge.

## Verification Summary & Residual Risks

- **Builds & static check:** Local `debug_gcc` (`exit 0`), local `release_gcc` (`exit 0`), and `cubrid-static-check` (`0` new `cppcheck`, `clang-tidy`, or `PMD CPD` defects; pre-existing `util_front.c` compile-db gap) at `f0d47c1709`, plus CI `build (debug)` and `build (release)` pass at `8fe6fdcb37`.
- **Runtime checks (`f0d47c1709`):** F1 4-mode replay + `_vinf`-deleted link-walk test, F2 4-mode gdb double-crash replay, F3 `-i`/interactive replay on `debug_gcc` and `release_gcc`, author v4 suite (`crash`/`restore`/`incremental`/`server-recovery` pass on `debug_gcc`, `restore` passes on `release_gcc`, `basic` 16/17 with known stale v4 EOF expectation), and the private shell TC (`debug_gcc` 25/25, `release_gcc` 15/15).
- **Residual low-impact risks / nits (non-blocking):** `R-D1` (P4, source-only: torn `dwb_write_block` during rollback recovery under DWB on), `R-D2` (P4, source-only: OS write reordering on power loss during DWB-off undo), `N-1` (ignored `dwb_synchronize` return matching `boot_dbparm_*`), `SYS-D1` (`FAILURE:` prefix in utility log for non-fatal leftover-file notice), `SYS-D2` (header path vs mounted label check), and carried-over `U-C2` / `U-ST1` / `U-ST3` / `U-NL`.
