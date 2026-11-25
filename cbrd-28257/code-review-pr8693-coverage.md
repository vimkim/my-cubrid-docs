# Coverage: CUBRID/cubrid#8693 @ `2a3d8b51475511d8e8e7f06e88e9f0cd54b0fe1f` (base `e23905d89ad8a49f17e7cff6eaef01a00de258fe`)

| Path / invariant | Primary | Second | Evidence | Result | Remaining |
|---|---|---|---|---|---|
| `src/storage/catalog_class.c` hunk (3268-3274): pointer advance, length, layout and bound bits unchanged | R-A | coordinator | `object_representation.h:1578-1602`; static check 0 new | cleared (L3) | none |
| Q1 (shared): every byte of an encoder-produced catalog row is written | R-A (opus) | R-B (sonnet), independent | Both: no unwritten byte (L3); head TC 0 fill hits (L5) | cleared | none |
| Callers `catcls_insert_instance` / `catcls_update_instance` / `catcls_update_class_stats` (3931/4261/4524) | R-A | R-B | source L3; insert and update exercised by the TC (L5); stats path not exercised | cleared (stats: L3 only) | optional TC T-2 |
| Readers (catalog decoder, heap attrinfo, update compare, checkdb) | R-B | — | `catalog_class.c:3438`, `heap_file.c:11788`, 4242; `checkdb` OK | cleared (L3/L4) | none |
| Recovery: redo/undo, MVCC header, vacuum | R-B | — | no format change; source L3 | cleared | none |
| HA / replication / compatibility | R-B | — | `need_replication=false`, `repl_info=NULL`, statement-based schema replication | not applicable (L3) | none |
| Storage / performance | R-A | — | memset ≤ 8 B per NULL fixed column on DDL | cleared (L2) | none |
| Other catalog writers outside the encoder | R-A | coordinator | `system_catalog.c:2905`, `474-485`; `xasl_to_stream.c:9211` | U-1 and U-2: separate pre-existing risks | separate JIRA issues |
| TC private-ex#5098 `cbrd_28257.sh` | R-B | V (execution) | base NOK 2/4 twice, head OK twice (L5); regex replay | detects the defect; T-1..T-3 non-blocking | none required |
| TC cubrid-testcases#4400 | coordinator | — | 0 files | empty draft | close at handoff after its "no unlanded changes" check |
| CI / static | coordinator | — | gha-ci build/medium pass; sql, sql_by_cci and shell pending; static check 0 new | partial (CI pending) | wait for CI before merge |

Not-applicable roles: Concurrency. The change is a single-threaded local buffer write inside an existing call, with no new shared state, latch or lock interaction, so it was folded into R-A's systems review.
