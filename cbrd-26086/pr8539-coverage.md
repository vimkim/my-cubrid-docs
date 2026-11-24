# Coverage for CUBRID/cubrid#8539 ([CBRD-26086])

Pinned head `101106d2eebc4c49b63b6c9c1d31a2db45978c57`, merge base `5962ff2901c8e74fd941f1aa7df697de4ed10697`.

Every changed path is covered:
- [`src/storage/disk_manager.c`](https://github.com/CUBRID/cubrid/blob/101106d2eebc4c49b63b6c9c1d31a2db45978c57/src/storage/disk_manager.c), [`src/storage/disk_manager.h`](https://github.com/CUBRID/cubrid/blob/101106d2eebc4c49b63b6c9c1d31a2db45978c57/src/storage/disk_manager.h) (Systems/Storage primary, Storage/Recovery secondary);
- [`src/transaction/boot_sr.c`](https://github.com/CUBRID/cubrid/blob/101106d2eebc4c49b63b6c9c1d31a2db45978c57/src/transaction/boot_sr.c) (both, split by concern).

There are no renames, deletions, submodule changes or binary files.

| Source or boundary | Owner (model) | Invariant | Evidence | Result | Remaining action |
|---|---|---|---|---|---|
| `disk_manager.c/h` `disk_is_permanent_volume_file`: buffer, read size, `file_io` contracts, header layout | Systems/Storage (`opus`) | Header read is correct and an error means "leave the file" | Source; static leads cleared; fcntl/classifier models | Holds | none |
| `boot_sr.c` `boot_get_temp_volid_from_name`, path derivation, `opendir`/`readdir`, fallback loop, `errno`, `S_ISREG`, platforms | Systems/Storage (`opus`) | Only exact temp-volume names with `volid > last_volid` | name_probe (42 cases), readdir_probe; runtime temppath/gap | Holds | none |
| `boot_sr.c` entry points (restart 2568, shutdown 3098, deletedb 5343) and initialisation state | Storage/Recovery (`sonnet`) | `disk_Cache`, `boot_Db_parm` and mounted volumes are valid when called | Source F3–F5; runtime stop/crash/deletedb/SA | Holds | none |
| `boot_Db_parm` `temp_nvols`/`temp_last_volid` reset and persistence | Storage/Recovery (`sonnet`) | Consistent volid selection after stop/crash | Readers grep; runtime tracked/stop | Holds | none |
| Buffer invalidation and dismount | Storage/Recovery (`sonnet`) | No live page or descriptor references a removed file | Source H7/H8 | Holds (same as base) | none |
| Crash/recovery ordering, crash mid-cleanup | Storage/Recovery (`sonnet`) | Recovery completes before cleanup; cleanup is idempotent | Source F5/H6; runtime crash cases | Holds | none |
| **Shared challenge:** permanent-volume safety from classification to unlink (identity + lock) | **Both, independently** (`opus`, `sonnet`) | No permanent volume of any DB is deleted, and no own lock is released | Both found the lock gap independently (SS-1, SR-1). Coordinator replay ss1/sr1 at level 5 | **Fails, F1 (P3)**. SS-2 (link → own lock release) unverified, P4 | Author fix or explicit acceptance; delta review (see [pr8539-handoff.md](pr8539-handoff.md)) |
| Lifecycle concurrency (other processes, daemons at shutdown) | Storage/Recovery (`sonnet`) | No concurrent use of a removed file | H8, H13; `locked.sh` | Holds except F1 | none |
| HA | Storage/Recovery (`sonnet`) | — | Temp volume add/remove is not logged or replicated | Not applicable | none |
| Standards (indent markers, function reuse, C++ in `.c`), spec conformance (JIRA AC: all temp files removed at start/stop) | Coordinator | Repo and personal policy; JIRA AC | Diff review; 8+1 author cases | Conforms. The PR comment/table overstate the lock protection (F1 fix c) | Fix the comment |
| Production verification | Coordinator | — | Build, author suite, locked/SA probe, F1 replays | Done | Release build, TDE and base contrast not run (optional) |

Missing independent challenge: none. The shared question had two seats on different models.
