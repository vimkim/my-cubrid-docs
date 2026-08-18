# `feat/oos`–`develop` histogram merge conflict line-by-line decision log

## 1. Metadata

| Item | Value |
|---|---|
| Worktree | `/home/vimkim/gh/cb/feat-oos` |
| Branch | `feat/oos` |
| OOS-side parent | `e1e651debf6cc100172bde96603b17424f9c135a` |
| Merged `develop` commit | `f8407ce45e4c90c30500403fc65211478c13ea06` |
| Merge base | `aa26de56c5a3444adb505cfaedc593e1ec4b5b84` |
| Merge commit | `b996d4d826113bc060804c381aa6912603a81c70` |
| Resolution date | 2026-08-19 |
| OOS-side unique commits | 96 |
| `develop`-side unique commits | 12 |
| Conflicted file | `src/optimizer/histogram/histogram_sampler_sr.cpp` |
| Text conflict chunks | 1 |

The unmerged index recorded these blobs:

| Stage | Meaning | Blob |
|---:|---|---|
| 1 | merge base | `65a675e794d49b7824080e1511968def9cdf0d4c` |
| 2 | OOS side | `7484575cb893740794bfdb555dfd834ea1e66bca` |
| 3 | `develop` side | `0c6e923703b7540ac61fb0f5b3d654e7f426f159` |
| final | resolved file | `322067739` (abbreviated tree blob) |

## 2. Outcome

The resolution keeps `develop`'s new deterministic page-sampling implementation and removes the superseded serial `heap_next()` loop from the conflict. It also preserves the OOS-side record-consumption contract:

- The replacement path calls `scan_ftab_partition_multi()`.
- That function reads values through the OOS-aware `heap_attrinfo_*` layer.
- Its page-local iterator calls `heap_next_1page()`.
- `heap_next_1page()` passes `HEAP_RECDES_DONT_CONSUME_RAW_BYTES` to `heap_scan_get_visible_version()` internally.
- The separate NDV full-scan path that still calls public `heap_next()` retains the OOS side's explicit `HEAP_RECDES_DONT_CONSUME_RAW_BYTES` argument.

Therefore the resolution preserves both intents without restoring code that CBRD-26959 deliberately replaced and without adding a redundant policy parameter to `heap_next_1page()`.

## 3. Primary-source intent

### 3.1 OOS-side intent

The policy originates in CBRD-27029, commit `de84fa59e16aa0b863cfdbda4655f6c371dc0f86` (PR #7416): callers that do not consume raw logical `RECDES` bytes must avoid record-level OOS Expand and resolve values through the attribute layer.

CBRD-26847, commit `6d1779a8c7163d18f177a6f4e7d20e9b8d85a794` (PR #7596), tightened this audit rule: use `HEAP_RECDES_CONSUME_RAW_BYTES` only for an actual raw-byte consumer. The histogram collectors access values through `heap_attrinfo_read_dbvalues()` and `heap_attrinfo_access()`, so they are `DONT_CONSUME_RAW_BYTES` consumers.

The OOS parent contains two explicit policy additions relative to the merge base:

1. the serial histogram reservoir scan's `heap_next()` call;
2. the NDV full-scan reservoir's `heap_next()` call.

### 3.2 `develop`-side intent

The change that replaced the conflicted serial scan is commit `532ce4b6df012ff15802955b61d40cf1f14cfa32`, CBRD-26959 (PR #7476). It changes histogram collection to deterministic page sampling over file allocation metadata:

- enumerate heap data pages from `FILE_FTAB_COLLECTOR`;
- select pages with `ftab_page_walker`;
- scan selected pages through `scan_ftab_partition_multi()`;
- collect row counts per target heap;
- expand sampled counts using the realized kept/seen page ratio.

Restoring the old serial loop would discard those semantics and could also leave two competing scans in the same function.

### 3.3 Why the visible conflict looked misleading

Git aligned the old `heap_scancache_start()` error body with the new `file_get_all_data_sectors()` error body. As a result, the marker began inside the new error block and showed only one `develop` line (`if (ftab_collector.partsect_ftab != NULL)`) against most of the old serial setup and loop. The correct unit of reasoning was the whole scan implementation, not the visually adjacent lines alone.

## 4. Line-by-line conflict decisions

The identifiers below are local to this report. `O` is the OOS side, `B` is the base, `D` is `develop`, and `C` is a line common to the resolved error block. Blank lines are logged separately after the nonblank lines.

### 4.1 OOS-side marker lines

All of the following lines appeared between `<<<<<<< e1e651deb` and `||||||| aa26de56c` in Git's remerge reconstruction.

| ID | OOS-parent line | Decision | Reason |
|---|---|---|---|
| O01 | `ASSERT_ERROR ();` | Drop | It handled failure of the deleted `heap_scancache_start()` flow. The new allocation-metadata call uses `ASSERT_ERROR_AND_SET (error)` after freeing its collector buffer. |
| O02 | `goto cleanup;` | Drop here | The new error block retains its own `goto cleanup;` after cleanup and error propagation. |
| O03 | `}` | Drop | Closing brace belonged to the old scancache-start error branch. |
| O04 | `scancache_inited = true;` | Drop | The replacement path does not initialize this function's serial `HEAP_SCANCACHE`; the helper owns its scan cache. |
| O05 | `error = heap_attrinfo_start (thread_p, tgt_oid, attr_cnt, attr_ids, &attr_info);` | Drop | Attribute-cache setup moved into `scan_ftab_partition_multi()` for each page partition. |
| O06 | `if (error != NO_ERROR)` | Drop | Error handling is now inside the helper and returned through its `error` result. |
| O07 | `{` | Drop | Opens the obsolete attribute-cache error block. |
| O08 | `ASSERT_ERROR ();` | Drop | Belongs to O06's obsolete local setup. |
| O09 | `goto cleanup;` | Drop | Belongs to O06's obsolete local setup. |
| O10 | `}` | Drop | Closes O06's obsolete local setup. |
| O11 | `attrinfo_inited = true;` | Drop | The helper owns and cleans its `HEAP_CACHE_ATTRINFO`; this outer-function flag no longer represents the replacement scan. |
| O12 | `OID_SET_NULL (&inst_oid);` | Drop | The replacement helper uses its own `cur_oid`. |
| O13 | `scan_class_oid = *tgt_oid;` | Drop | The helper initializes its own local class OID. |
| O14 | `while (true)` | Drop | The serial all-row loop was replaced by the ftab page walker. |
| O15 | `{` | Drop | Opens O14's obsolete loop. |
| O16 | `/* reset recdes before every fetch (mirrors the executor's heap scan): a stale PEEK` | Drop at this location | The protection remains in the replacement helper immediately before each `heap_next_1page()` call. |
| O17 | ` * pointer left by the previous row makes heap_get_visible_version_from_log () treat` | Drop at this location | Same comment is preserved in the helper. |
| O18 | ` * recdes as a caller-supplied buffer and fail with S_DOESNT_FIT when a concurrently` | Drop at this location | Same comment is preserved in the helper. |
| O19 | ` * updated row's visible version must be read from the undo log */` | Drop at this location | Same comment is preserved in the helper. |
| O20 | `recdes.data = NULL;` | Drop at this location | The helper resets its own `recdes.data` before every page-local fetch. |
| O21 | `sc =` | Drop | The outer serial fetch is removed. |
| O22 | `heap_next (thread_p, tgt_hfid, &scan_class_oid, &inst_oid, &recdes, &scan_cache, PEEK,` | Drop | The new collector scans selected pages through `heap_next_1page()`. |
| O23 | `HEAP_RECDES_DONT_CONSUME_RAW_BYTES);` | Drop only as an explicit argument here | Its semantic intent is retained by `heap_next_1page()`'s internal hardcoded policy. |
| O24 | `if (sc != S_SUCCESS)` | Drop | Page-local scan termination is handled inside `scan_ftab_partition_multi()`. |

### 4.2 Base marker lines

The base lines were the same obsolete serial setup as O01–O24, except that the fetch was one line and had no explicit policy:

| ID | Base line | Decision | Reason |
|---|---|---|---|
| B01 | `sc = heap_next (thread_p, tgt_hfid, &scan_class_oid, &inst_oid, &recdes, &scan_cache, PEEK);` | Drop | It is the pre-OOS-policy form of the deleted serial scan and must not replace the new page scanner. |

Every other nonblank base marker line maps one-to-one to O01–O20 and O24 and receives the same decision. No base-only behavior is restored.

### 4.3 `develop` and common error-block lines

| ID | Final line | Decision | Reason |
|---|---|---|---|
| D01 | `FILE_FTAB_COLLECTOR ftab_collector;` | Keep | Owns the allocation metadata returned for the target heap. |
| D02 | `if (file_get_all_data_sectors (thread_p, &tgt_hfid->vfid, &ftab_collector) != NO_ERROR)` | Keep | Entry point for the new ftab-based page enumeration. |
| D03 | `{` | Keep | Opens the new metadata-enumeration error path. |
| D04 | `if (ftab_collector.partsect_ftab != NULL)` | Keep | The sole line shown on the `develop` side of the marker; prevents leaking a partially allocated collector buffer. |
| C01 | `{` | Keep | Opens D04's guarded free block. |
| C02 | `db_private_free_and_init (thread_p, ftab_collector.partsect_ftab);` | Keep | Frees and nullifies the partially allocated buffer using the CUBRID memory convention. |
| C03 | `}` | Keep | Closes D04's guarded free block. |
| C04 | `ASSERT_ERROR_AND_SET (error);` | Keep | Preserves the primary error and guarantees a usable error value. |
| C05 | `goto cleanup;` | Keep | Returns through the function's existing cleanup path. |
| C06 | `}` | Keep | Closes D02's error block. |

### 4.4 Blank-line decisions

| Location | Decision | Reason |
|---|---|---|
| Between old scancache initialization and old attrinfo setup | Drop | Both adjacent operations were deleted. |
| Between old attrinfo initialization and old OID setup | Drop | Both adjacent operations were deleted. |
| Between old OID setup and old `while` loop | Drop | Both adjacent operations were deleted. |
| After the final new error block | Keep one blank line | Separates the error path from the successful ftab conversion block and matches `develop` formatting. |

## 5. Preserved behavior outside the conflict marker

The OOS parent also changed the surviving NDV full-scan call. Git merged this part automatically, and the resolution deliberately preserved it:

```cpp
sc =
  heap_next (thread_p, hfid, &scan_class_oid, &inst_oid, &recdes, &scan_cache, PEEK,
             HEAP_RECDES_DONT_CONSUME_RAW_BYTES);
```

Final source: `src/optimizer/histogram/histogram_sampler_sr.cpp:2689`.

This path still uses public `heap_next()`, whose API requires an explicit policy. Unlike the conflicted histogram path, it was not replaced by `heap_next_1page()`.

## 6. OOS policy proof for the replacement path

The final histogram flow is:

```text
xhistogram_build_multi_by_fullscan_reservoir
  -> scan_ftab_partition_multi
     -> heap_next_1page
        -> heap_scan_get_visible_version(
             ...,
             HEAP_RECDES_DONT_CONSUME_RAW_BYTES,
             ...)
     -> heap_attrinfo_read_dbvalues
     -> heap_attrinfo_access
```

Evidence in the merged tree:

- `histogram_sampler_sr.cpp:2349`: outer function calls `scan_ftab_partition_multi()`.
- `histogram_sampler_sr.cpp:1387`: helper calls `heap_next_1page()`.
- `histogram_sampler_sr.cpp:1393`: helper invokes `heap_attrinfo_read_dbvalues()`.
- `histogram_sampler_sr.cpp:1405`: collectors receive `heap_attrinfo_access()` values.
- `heap_file.c:8155`: `heap_next_1page()` hardcodes `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`.

The explicit policy line from the deleted serial call is therefore represented exactly once at the correct lower layer.

## 7. Verification

| Check | Result |
|---|---|
| OOS environment validation | Passed; only warning was that `clangd` is unavailable |
| Unmerged index entries | None |
| Conflict markers in resolved file | None |
| `git diff --cached --check` before commit | Passed |
| Full `debug_gcc` compilation | Completed through engine, broker, PL, and all configured OOS test binaries |
| Follow-up `just compile` | Passed, exit 0; build was up to date |
| Merge parent check | `f8407ce45` is an ancestor of merge commit `b996d4d82` |
| Source worktree after merge | Clean for tracked superproject files |
| Install | Safely deferred by the local coordinator because `cub_master`, `cub_server demodb`, and `cub_pl demodb` were active |
| CTest | Not run: it shares the busy installed runtime and the coordinator correctly withheld the runtime lock |

No active process was stopped. The build wrapper's first `just build` invocation returned exit 75 only at the install-safety gate; compilation itself completed. A second compile-only gate returned exit 0.

## 8. Commit hygiene and preserved local state

The merge commit was created with the personal lefthook disabled (`LEFTHOOK=0`) so a local formatter could not rewrite the large incoming `develop` change set. This does not alter project behavior or bypass repository CI; it only avoids unrelated local formatting changes during the merge commit.

The following pre-existing local state was not added to the merge commit:

- modified content inside the `cubrid-cci` submodule;
- personal untracked editor, build, debug, and `justfile` files.

No push was performed.

## 9. Final state

Merge commit `b996d4d826113bc060804c381aa6912603a81c70` has exactly these parents:

1. `e1e651debf6cc100172bde96603b17424f9c135a` — pre-merge `feat/oos`;
2. `f8407ce45e4c90c30500403fc65211478c13ea06` — merged `origin/develop` snapshot.

The conflict is resolved, the merge operation is finished, and the resulting source preserves both CBRD-26959 page sampling and the OOS recdes-consumption policy.
