# Develop heap batch reservation model

`DevelopHeapReservation.tla` models one heap batch allocation racing one vacuum worker on CUBRID develop `2362424f25bcebd1bd9733bddd59a993e2852ac5`. It answers which states an existing heap page P can be in when the batch reserves a new sector. [develop-applicability.md](../develop-applicability.md) gives the CBRD-27945 verdict that uses these results.

## Run the check

Pass `--repo` a CUBRID clone that contains commit `2362424f25bcebd1bd9733bddd59a993e2852ac5`. The check needs Python 3.9 or later, Java 8 or later, and `~/.cache/tlaplus/tla2tools-1.7.4.jar`. The output path must not exist.

```sh
python3 -B cbrd-27945/develop-heap-reservation/run.py --repo <cubrid-clone> --out cbrd-27945/develop-heap-reservation/runs/<new-dir> --self-test
```

The run takes about 30 seconds. `run.py` reads the source files from the Git object at `--rev` (default: the pinned commit), not from the working tree.

| Exit | Meaning |
| --- | --- |
| 0 | Every verdict matches `EXPECTED`, and with `--self-test` every source mutation is caught. |
| 1 | A verdict differs from `EXPECTED`, or a self-test mutation is not caught. |
| 2 | Source drift (a required marker is missing or out of order), a TLC error, or a missing tool. |

`<out>/results.json` records the extracted facts, each marker's line, file hashes, every verdict with its state count, and the self-test outcome. Each case directory keeps the generated `.cfg` files and raw TLC logs.

## Source facts

`run.py` derives these model constants from source text. A changed order turns a fact FALSE, and the verdicts then differ from `EXPECTED`.

| Constant | Source evidence |
| --- | --- |
| `BatchHoldsHeapHeader` | `heap_alloc_new_pages` fixes the heap header WRITE, starts a sysop, calls `file_alloc_multiple`, commits, then unfixes the header (`src/storage/heap_file.c:27708-27812`). |
| `PostponeBeforeHeaderUnfix` | `heap_remove_page_on_vacuum` calls `file_dealloc`, then `log_sysop_commit`, then unfixes the heap header (`src/storage/heap_file.c:3579-3600`). `log_sysop_commit_internal` calls `log_sysop_do_postpone` (`src/transaction/log_manager.c:3973`). |
| `Batch` bound | `ALLOC_BATCH_SIZE = 4` (`src/storage/bestspace.hpp:77`). The request is `ALLOC_BATCH_SIZE - num_candidates` (`src/storage/bestspace.cpp:1067`). |
| `SectorPages` | `DISK_SECTOR_NPAGES 64` (`src/storage/storage_common.h:109`). |

`--self-test` makes three mutations on a scratch copy of the source text and confirms that each one changes a verdict. The mutations unfix the heap header before the batch, unfix the vacuum heap header before the sysop commit, and drop the postpone call from `log_sysop_commit_internal`. The self-test also deletes the `file_perm_expand` call and confirms that the runner reports drift.

## Action map

| Model action | Source |
| --- | --- |
| `AllocFixHeapHeader` | `heap_alloc_new_pages`, ordered fix of the heap header WRITE (`heap_file.c:27708`) |
| `AllocFixFileHeader` | `file_alloc_multiple`, file header WRITE for the whole batch (`file_manager.c:5596`) |
| `AllocUserPage` | `file_perm_alloc` with `FILE_ALLOC_USER_PAGE`: expand at `n_page_free == 0`, else take a bit in the first partial sector and remove the sector when it fills (`file_manager.c:5190-5306`) |
| `AllocProbeFullTable` | `file_table_add_full_sector`, `file_extdata_find_not_full` (`file_manager.c:5044`) |
| `AllocTablePage` | recursive `file_perm_alloc` with `FILE_ALLOC_TABLE_PAGE_FULL_SECTOR`, `file_table_append_full_sector_page`, then the pending sector insert (`file_manager.c:5062`, `5259-5310`) |
| `Reserve` | `file_perm_expand`: `disk_reserve_sectors`, new sectors appended to the partial table, own committed sysop (`file_manager.c:4681-4739`) |
| `AllocReleaseFileHeader` | `file_alloc_multiple` exit, `log_sysop_attach_to_outer`, unfix (`file_manager.c:5640-5650`) |
| `AllocLinkCommitRelease` | `heap_alloc_new_pages` chain links, stats, sysop commit, heap header unfix (`heap_file.c:27749-27812`) |
| `VacEmptyPage` | `vacuum_heap_page` removes the last record of a reusable heap page (`vacuum.c:1853`) |
| `VacFixHeapHeader`, `VacGetHeapHeader` | `heap_remove_page_on_vacuum` ordered fix (`heap_file.c:3384`); `pgbuf_ordered_fix_release` conditional try, zero-wait failure, or unfix, unconditional wait and refix (`page_buffer.c:12520-12935`) |
| `VacGates` | refix recheck, `pgbuf_has_prevent_dealloc`, `pgbuf_has_any_waiters`, neighbor fixes (`heap_file.c:3384-3470`) |
| `VacGiveUp`, `OtherInsertIntoP` | failed removal returns P to bestspace with `heap_add_bestpage` (`vacuum.c:1879`) |
| `VacUnlink`, `VacFileDealloc` | header stats and neighbor links, `file_dealloc` appends the `RVFL_DEALLOC` postpone (`heap_file.c:3473-3579`, `file_manager.c:6167`) |
| `VacCommit` with `FreeP` | `log_sysop_commit` runs the postpone: `file_rv_dealloc_internal` fixes the file header WRITE and calls `file_perm_dealloc` (`file_manager.c:6628-6652`, `6350-6474`) |
| `VacReleaseHeader` | heap header unfix after the commit (`heap_file.c:3600`) |
| `VacLatePostpone` | model-only control used when `PostponeBeforeHeaderUnfix` is FALSE |

## Fixtures and verdicts

Each case starts with P allocated and holding its last deleted record, and with the full-sector table saturated unless noted. Every case also runs `TypeOK`, `PartialSectorsHaveFreeBits`, `Accounting`, and `ReserveOnlyWithoutFreeBits`. All four hold in every case.

| Case | Layout | Batch | Purpose |
| --- | --- | --- | --- |
| `A1_partial_batch1` | P in S0, the only partial sector, 1 free bit | 1 | recursive reservation from the last free bit |
| `A4_partial_batch4` | same as A1 | 4 | larger batch |
| `B1_full_batch1` | S0 has 1 free bit, P in full sector S1 | 1 | P's sector leaves the full table when freed |
| `B2_full_batch2` | same as B1 | 2 | larger batch |
| `O1_outer_expand` | no free bit, P in full sector S1 | 1 | expansion in the outer user allocation, no recursion |
| `R1_table_room` | as A1 with one full-table slot | 1 | no recursion, no reservation |
| `M1_no_header_hold` | as A1, `BatchHoldsHeapHeader = FALSE` | 1 | model-only control |
| `M2_late_postpone` | as A1, `PostponeBeforeHeaderUnfix = FALSE` | 1 | model-only control |

PASS means the invariant holds in every reachable state. FAIL means TLC found a state that breaks it.

| Invariant | A1 | A4 | B1 | B2 | O1 | R1 | M1 | M2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `NoReserveWhileUnlinkable` | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | PASS |
| `NoReserveWhileUnlinkedNotFree` | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | FAIL |
| `NoReserveWhilePhysicallyEmpty` | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | FAIL |
| `NoRecursiveReserveWhilePhysicallyEmpty` | FAIL | FAIL | FAIL | FAIL | PASS | PASS | FAIL | FAIL |
| `NoOuterReserveWhilePhysicallyEmpty` | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | PASS |
| `ReclaimFirstAvoidsReservation` | PASS | FAIL | PASS | FAIL | PASS | PASS | PASS | PASS |
| `NoReservation` | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | FAIL |
| `NoCompletedRun` | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |

`NoCompletedRun` failing everywhere shows that both actors can finish, so the other results are not vacuous. `ReclaimFirstAvoidsReservation` asks whether a run that frees P before the batch takes the heap header never reserves.

## Read a trace as a chart

The statechart skill draws the A1 state graph and the shortest path for each broken rule. Run it with a new output folder:

```sh
cp cbrd-27945/develop-heap-reservation/{DevelopHeapReservation.tla,statechart-A1.cfg} <scratch>/
<statechart skill>/scripts/statechart <scratch>/DevelopHeapReservation.tla --config <scratch>/statechart-A1.cfg \
  --view cbrd-27945/develop-heap-reservation/statechart-view.mjs --out <scratch>/out
```

The chart hides the terminal stutter step.

## Bounds and omissions

The model has one heap file, one batch, one vacuum worker, one candidate page P, and at most the sectors that one batch reserves. Each reservation adds one sector. Native expansion can add more sectors, which only adds free bits after the reservation point. Bestspace's search is abstract: the batch starts after the search missed P.

The model leaves out these paths:

- the full-table page merge in `file_perm_dealloc`;
- `file_table_move_partial_sectors_to_header`;
- a partial table with no room, which makes `file_perm_dealloc` allocate a partial-table page;
- error, abort, crash, and recovery paths, including undo of the batch;
- other heap writers besides one optional insert into P;
- non-reusable heaps (`FILE_HEAP`), where vacuum never tries to remove a page;
- compactdb's `xheap_reclaim_addresses`, which frees heap pages at transaction commit under an exclusive class lock (`heap_file.c:5800-5961`).

`NoReserveWhileUnlinkable` restates `BatchHoldsHeapHeader`: when the allocator holds the heap header, `CanUnlinkNow` is false at every reservation. Its value is that M1 and the self-test show the dependency. `NoReserveWhilePhysicallyEmpty` and its two variants show reachability only, because fresh pages and batch mates are also empty and allocated at a reservation.

`run.py` checks the postpone timing as text. It confirms that `log_sysop_commit_internal` calls `log_sysop_do_postpone`, not that the `RVFL_DEALLOC` postpone belongs to vacuum's own sysop. An independent review confirmed that by reading `log_append_postpone` and the absence of `log_sysop_attach_to_outer` in `heap_remove_page_on_vacuum`. The self-test mutations run on `A1_partial_batch1` only.

A model result is evidence about these bounds only. It does not replace native execution.
