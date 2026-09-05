# What `cubrid backupdb -l 0` actually does

## Verdict

`-l 0` selects a **full physical database backup**; it is also the default when `-l` is omitted. For each ordinary permanent CUBRID volume, the backup path reads every page from the volume file directly, without loading those pages through the page buffer. In that narrow sense it is a sequential disk-to-backup copy.

It is **not** a raw copy of the whole disk, and it is not “just copy bytes with no extra work.” It copies the database's volume files plus the control/key/log material needed by CUBRID restore into a structured backup stream. It excludes external LOB files, handles temporary-purpose volumes specially, performs consistency checking by default, establishes checkpoint/flush conditions, packages page identifiers and file headers, compresses by default, copies required recovery logs, and synchronizes the finished backup.

## Shared Scenario

The scenario is a full physical backup of a running database: `cubrid backupdb -C -l 0 dbname` with otherwise default options. The question is whether “full” means a raw disk clone and what work surrounds the volume reads.

The checked-out manual says level 0 includes all database pages (`en/admin/backup.inc:165-179`), but also says external LOB data is not included (`en/admin/backup.inc:6`). It documents default compression (`en/admin/backup.inc:107-111,195-200`) and the optional consistency-check bypass (`en/admin/backup.inc:95-99`).

## CUBRID Trace

1. **CLI setup and pre-check.** `backupdb()` parses `-l`; the default is `FILEIO_BACKUP_FULL_LEVEL`, whose enum value is 0 (`src/executables/util_admin.c:136-150`, `src/storage/file_io.h:95-102`). Unless `--no-check` is passed, it asks `boot_check_db_consistency()` to check the file tracker, all heaps, catalog consistency, all B-trees, and class names before backup (`src/executables/util_cs.c:181-188,294-306`). Therefore a default level-0 command can perform substantial logical I/O before the physical copy begins.

2. **Server backup entry.** The request reaches `xboot_backup()` and then `logpb_backup()` (`src/transaction/boot_sr.c:3929-3963`). The server rejects overlapping backups. For an online full backup, it forces a checkpoint completed after backup entry, waits for an existing checkpoint when needed, and blocks checkpoint execution while it captures the starting checkpoint state (`src/transaction/log_page_buffer.c:7602-7703,7785-7904`).

3. **Full-level selection.** Level 0 sets the backup start LSA to NULL and keeps `isincremental == false`; levels 1 and 2 instead load a prior backup LSA and enable updated-page filtering (`src/transaction/log_page_buffer.c:7906-7947`).

4. **Per-volume preparation.** For every ordinary permanent volume, `logpb_backup_for_volume()` sets the volume checkpoint, flushes log pages, flushes all unfixed dirty pages for that volume, and synchronizes the double-write buffer. Only then does it call `fileio_backup_volume()` (`src/transaction/log_page_buffer.c:7463-7558`). The backup is still described as “fuzzy”: transactions can continue and the copied volume may contain uncommitted or differently timed page images; recovery logs make the restore consistent.

5. **The physical read.** `fileio_backup_volume()` opens the named volume read-only, obtains its file size, and calculates the page count from that size (`src/storage/file_io.c:8260-8372`). In the single-reader path it scans page IDs from 0 to `from_npages - 1` and uses `pread()` in server mode (`src/storage/file_io.c:8428-8472,8763-8838`). Because level 0 passes `is_only_updated_pages == false`, every page read is emitted; it does not consult page allocation state to omit free database pages. It is a volume-file scan, not a block-device clone: filesystem metadata, unrelated files, free filesystem space, and disk slack are not copied. For a raw-device-backed CUBRID volume, the code limits the read to CUBRID's reported logical volume page count (`src/storage/file_io.c:8345-8354`).

6. **Structured output, not `cp`.** Each source file gets a backup file header. Each data chunk carries a page identifier; default LZ4 compression may transform it before buffered writes (`src/storage/file_io.c:8374-8385,8464-8497,7799-7833`). The backup itself has a CUBRID magic/version/database/checkpoint header (`src/storage/file_io.c:7170-7253`) and an end marker; the destination is synchronized before success (`src/storage/file_io.c:7345-7418`). Parallel reader threads may perform the scan.

7. **Multithreaded volume pipeline.** In server mode, omitted `-t` means 0/auto and resolves to the machine's CPU count, capped by `NUM_NORMAL_TRANS`; an explicit count is additionally capped at the CPU count. The count includes one writer, so `-t 4` means up to three worker readers plus the calling thread acting as the sole writer (`src/storage/file_io.h:59,392-420`; `src/storage/file_io.c:6665-6728,8407-8425`). Readers claim sequential page IDs, read and enqueue pages, then compress outside the shared mutex. The writer drains ready queue entries in page order into one backup stream (`src/storage/file_io.c:7854-8025,8061-8191,8201-8238`). Consequently this is mainly CPU/pipeline parallelism, not parallel disk copying: compression can run concurrently in several workers and overlap serialized I/O, but both the source `pread()` and destination write execute while holding the shared thread-info mutex, so the read and write calls themselves do not overlap. Volumes are also processed one at a time, and after data volumes the code forces `num_threads = 1` for log copying (`src/transaction/log_page_buffer.c:8158-8237`). In standalone mode, initialization always selects one thread; `-t > 1` is warned as ignored (`src/executables/util_cs.c:203-207`; `src/storage/file_io.c:6714-6716`; `msg/en_US.utf8/utils.msg:288-289`).

8. **Included and excluded material.** The loop includes the TDE key file by default (or writes it separately with `-k`), the volume-info file, and every permanent database volume. Temporary-purpose volumes are an exception: only their system pages are saved (`src/transaction/log_page_buffer.c:7494-7515,8144-8227`). After data volumes, it copies required archive logs, log-info, and always the active log, then updates backup metadata and the level-0 LSA (`src/transaction/log_page_buffer.c:8232-8364`; archive loop at `src/transaction/log_page_buffer.c:10894-10931`). External LOB files are outside database volumes and must be backed up separately, as the manual warns.

Operationally, if the concern is runtime cost: `--no-check` avoids the broad pre-backup consistency traversal, and `--no-compress` avoids compression CPU, but neither changes level 0 into a raw disk copy nor avoids the full ordinary-volume page scan and recovery-consistency work.

## PostgreSQL and MySQL

| Engine mechanism | Mapping | Relevant difference |
|---|---|---|
| CUBRID level-0 `backupdb` | Exact subject | Scans every page of ordinary permanent volume files, after per-volume flush preparation, into a CUBRID backup archive with needed logs. |
| PostgreSQL full `BASE_BACKUP` / `pg_basebackup` | Partial analogy | Also enters backup mode/checkpoints and reads files directly while the server runs (`src/backend/backup/basebackup.c:234-356,982-1065`). It recursively packages selected PGDATA/tablespace files, deliberately excluding items such as temporary relations and `pg_wal` contents (`basebackup.c:1176-1240,1330-1406`), rather than scanning fixed-size CUBRID volumes page by page. The surveyed client/server base-backup path has no CUBRID-like parallel reader-count option; `pg_basebackup` can stream WAL concurrently in a separate process/thread (`src/bin/pg_basebackup/pg_basebackup.c:612-740`). |
| MySQL InnoDB Clone | Partial analogy | It is a physical online copy, but its consistency protocol is explicitly staged: file copy, changed-page copy, then redo copy (`storage/innobase/clone/clone0snapshot.cc:176-203`). Multiple clone tasks reserve and process distinct chunks, with an implementation maximum of 128 tasks (`storage/innobase/include/clone0desc.h:51`; `storage/innobase/clone/clone0clone.cc:1032-1105`; `storage/innobase/clone/clone0copy.cc:1365-1448`). This differs from CUBRID's ordered reader/compressor-to-single-writer pipeline. |

## Runtime Probe

No runtime probe was useful for the central question. The branch condition (`isincremental == false`), complete page loop, file-size bound, checkpoint/flush calls, and packaging calls directly establish the behavior. A black-box backup would confirm output size and timing but would not distinguish all of those internal steps without instrumentation. No source or database state was changed.

## Unknowns

The exact wall-clock split among the default consistency check, checkpoint/flush, source reads, compression, and destination writes is workload- and storage-dependent. A performance question for a particular database would require timing with the same database and destination, comparing the defaults against `--no-check` and/or `--no-compress`.

## Source Revisions

- CUBRID: `/home/vimkim/gh/cb/develop`, branch `develop`, `WORKTREE` based on `cd593bcf2d8643b4698f1cb311c4c23af23a9d57`. The worktree had unrelated changes (`cubrid-cci`, `PLAN.md`, `insert.sql`, `test.sh`); the traced engine files were not modified.
- CUBRID manual: `/home/vimkim/gh/cubrid-manual`, branch `develop`, `3b6ae97bfbdc664b010ffa933ded5a05b291ae03` (`v11.3-177-g3b6ae97b`).
- PostgreSQL: `/home/vimkim/gh/pg/postgres`, `fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc`.
- MySQL: `/home/vimkim/gh/mysql/mysql-server`, `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`.
