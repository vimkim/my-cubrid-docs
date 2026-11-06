# Coverage: PR #8416 @ 9ae07b9491b1

| Path group | Invariant | Primary | Secondary | Result | Remaining |
|---|---|---|---|---|---|
| heap_file.c, heap_oos.cpp/.hpp | FORCE_INLINE never demoted; -1388/-1393 split; error state preserved | systems | storage-recovery (Q1) | complete. R1 and R2 confirmed, no wrong accept or reject | delta after fix |
| object_representation_sr.c/.h, storage_common.h | flags read correctly | storage-recovery | systems, schema | complete, cleared | |
| error_code.h, cubrid.msg | numbering and argument order | systems | | complete, cleared | |
| db_info.c, dbi.h, dbi_compat.h | API consistency | systems | | complete, cleared | |
| parser/* | keyword and grammar | schema | | complete, cleared (bison counts) | |
| execute_schema.c, class_object.c | accepted ALTER rules | schema | | complete, cleared (level 5) | |
| object_printer.cpp, unload_schema.c | round trip | schema | | complete, cleared (level 5) | |
| recovery/vacuum | layout not re-run; no report during recovery | storage-recovery | | complete (source plus one crash run) | |
| HA | DDL text, row apply, compatibility | ha-concurrency | systems | source only | U4, HA pair run |
| concurrency | latches, schema lock, counters | ha-concurrency | | source plus gdb on INSERT | U3 latch mode |
| unit tests | tests match spec | schema, systems | | complete | N1: no partition or round-trip unit test |

Shared challenge Q1: systems (opus) and storage-recovery (sonnet) answered independently. Both answered "no FORCE_INLINE value goes to OOS; no wrong accept or reject".

Not applicable: older-binary compatibility. The OOS format is unreleased and guarded by `disk_check_storage_format`.
