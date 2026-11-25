# Code review: CUBRID/cubrid#8711 at bf5618f627

- **PR:** [CUBRID/cubrid#8711](https://github.com/CUBRID/cubrid/pull/8711), "[CBRD-28255] Count default values and the key header in the multi-column key buffer size" (author lht1199).
- **Companion TC PRs:** [cubrid-testcases#4418](https://github.com/CUBRID/cubrid-testcases/pull/4418) (`tc/pr-8711`, SQL case and answer) and [cubrid-testcases-private-ex#5114](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5114) (`tc/pr-8711`, shell case).
- **Goal:** Check that the new buffer-size estimate is an upper bound on every multi-column key that `heap_midxkey_key_get ()` and `heap_midxkey_key_generate ()` write, that passing the real buffer size to `or_init ()` changes nothing in release builds, and that the two TCs are sound regression guards.
- **Result:** No confirmed defect. Two independent reviewers found no reachable state where the key outgrows the buffer. Eight runtime probes on a local debug build of the head, which now asserts on any write past the buffer, completed with no assert and a clean `checkdb`.

## Snapshot

| Item | Value |
| --- | --- |
| Base | `6d8296b15c9694a7fc2c7920e539ec66d3d004aa` (develop) |
| Head | `bf5618f6275c4a1053b648b17b22786dca31bfcc` (merge of develop into `99e467e5d5778b43b0b9bd7c007df628e0f64019`) |
| Merge base | `6d8296b15c9694a7fc2c7920e539ec66d3d004aa` |
| Comparison | `git diff 6d8296b15c9694a7fc2c7920e539ec66d3d004aa bf5618f6275c4a1053b648b17b22786dca31bfcc` |
| Patch | `src/storage/heap_file.c`, +57/-31, sha256 `5933d8a3d6eeaea310469e939c4cd22e12f94c2a0a7fabee8230e19ce6546b6a`. Identical to the diff of `99e467e5d5` against its parent. |
| TC #4418 head | `d47276bbf0ee1e15229d05c4ec55f4ee7275aad7` |
| TC #5114 head | `d4a7bcab09684d34aa9b7017bf6757a0f2c3055c` |
| Snapshot date | 2026-11-25 KST. The base and head were rechecked as unchanged before publication. |

## Verdict and follow-up

- **Verdict:** `no-confirmed-findings`.
- **Follow-up review required:** no. The open items below are pre-existing or optional and do not block merging.
- **Formal approval readiness:**
  - Engine #8711 is ready for approval on code grounds.
  - TC #4418 and TC #5114 are ready for approval. The TC suggestions below are optional.
  - The PR approval gate (`cubrid-pr-approval-check`) reports `BLOCKED` on all three PRs. hornetmj has approved each one, and the review request to vimkim is still pending.
  - `TC Merge Gate / Check TC PRs` fails as designed while the TC PRs are open. It is resolved in the final merge handoff, not now.

## What changed

The multi-column key buffer is chosen from an estimate `midxkey_size`. When the estimate is above `DBVAL_BUFSIZE` (4096), a heap buffer of that size is allocated. Otherwise the caller's 4 KB stack buffer is used. `or_put_*` checks the end of the buffer only in debug builds (since CBRD-25960).

| Location | Change |
| --- | --- |
| [`heap_midxkey_attr_extra_size ()`](https://github.com/CUBRID/cubrid/blob/bf5618f6275c4a1053b648b17b22786dca31bfcc/src/storage/heap_file.c#L12728-L12742) (new) | For one key attribute, returns `default_value.val_length` when the record's representation lacks the attribute. Otherwise it returns the OOS value length, or 0. Present or absent is decided by `heap_midxkey_locate_record_attr ()`, the same function the key writer `heap_midxkey_get_value ()` uses. |
| [`heap_attrinfo_generate_key ()`](https://github.com/CUBRID/cubrid/blob/bf5618f6275c4a1053b648b17b22786dca31bfcc/src/storage/heap_file.c#L16470-L16480) | Adds `or_multi_header_size ()` and the per-attribute extra size. Looks the attribute up with `heap_locate_last_attrepr ()` rather than `heap_locate_attribute ()`. |
| [`heap_attrvalue_get_key ()`](https://github.com/CUBRID/cubrid/blob/bf5618f6275c4a1053b648b17b22786dca31bfcc/src/storage/heap_file.c#L16657-L16664) | Adds the header size, and the default length for attributes missing from the record. Before the change, those attributes counted as 0. |
| [`heap_midxkey_key_get ()`](https://github.com/CUBRID/cubrid/blob/bf5618f6275c4a1053b648b17b22786dca31bfcc/src/storage/heap_file.c#L16083), [`heap_midxkey_key_generate ()`](https://github.com/CUBRID/cubrid/blob/bf5618f6275c4a1053b648b17b22786dca31bfcc/src/storage/heap_file.c#L16294) | Take `buf_size` and pass it to `or_init ()` instead of `-1`. Both callers pass `MAX (midxkey_size, DBVAL_BUFSIZE)`. |

## Confirmed findings

None.

## Safety facts and effects outside the diff

The change affects every multi-column and function-index key built from a heap record: index build (serial, parallel and ONLINE), INSERT, UPDATE and DELETE, FK checks and actions, REPLACE and ON DUPLICATE KEY UPDATE, and checkdb. The key bytes, disk format, log records and catalog are unchanged.

| # | Safety fact | Owner | Evidence | Level |
| --- | --- | --- | --- | --- |
| S1 | The estimate and the writer pick the same attribute and the same default. The estimate passes the last-representation attribute to `heap_midxkey_locate_record_attr ()`, which matches by attribute id. The writer in `heap_midxkey_key_generate ()` passes `heap_locate_attribute ()`'s result, which has the same id, to the same function ([heap_file.c:16326](https://github.com/CUBRID/cubrid/blob/bf5618f6275c4a1053b648b17b22786dca31bfcc/src/storage/heap_file.c#L16326), [:12657](https://github.com/CUBRID/cubrid/blob/bf5618f6275c4a1053b648b17b22786dca31bfcc/src/storage/heap_file.c#L12657)). An attribute absent from the record therefore uses the last representation's `default_value` on both sides. This holds for dropped and re-added attributes, partitions, and subclasses. | R1, R2 independently | Source | 3 |
| S2 | No key value is longer than the bytes the estimate counts for it. Fixed scalar types write exactly their disk size. Strings omit only the NUL and alignment padding. Compressed strings are read and written still compressed. CHAR is read with the record's own domain, so it is not padded again. NUMERIC round-trips its stored header. | R1, R2 independently | Source (`object_primitive.c` readers and writers) | 3 |
| S3 | A domain change cannot leave old-representation rows whose key is longer than they are. CHAR or BIT precision changes, NUMERIC precision increases and every type change rewrite all rows (`execute_schema.c:11066-11068`, `locator_sr.c:14657`). A VARCHAR or VARBIT precision increase does not rewrite rows, but the key is sized from the value read with the record's domain. | R1, R2 | Source; probes P5 and P8 | 3–4 |
| S4 | The header count matches the writer. `heap_attrinfo_generate_key ()` uses `attr_info->num_values` and `heap_attrvalue_get_key ()` uses `n_atts`, the same counts the writers use. Function indexes use `attr_index_start + 1` in both. For a function index, the attribute loop also counts the function's argument columns, which only overestimates. | R1, R2 | Source | 3 |
| S5 | `MAX (midxkey_size, DBVAL_BUFSIZE)` is the real capacity. All 15 callers pass `char buf[DBVAL_BUFSIZE + MAX_ALIGNMENT]` aligned with `PTR_ALIGN`, so 4096 bytes are usable. The callers are in `query_executor.c` (2), `locator_sr.c` (10) and `btree_load.c` (3). | R2; R1 agrees | Source | 3 |
| S6 | A finite `or_init ()` size does not change release behaviour. Every write on the key path is a debug-only assert. The only runtime end checks are `or_put_varchar_internal` and the set writer, and neither is on the `index_writeval` path. | R2 | Source | 3 |
| S7 | Buffer ownership is unchanged. Allocation, the error-path free and `need_clear` all use the same `midxkey_size > DBVAL_BUFSIZE` test, and `midxkey_size` does not change after allocation. The larger estimate only moves keys near 4 KB from the stack buffer to the heap. | R1, R2 | Source | 3 |
| S8 | On the head debug build, every probe shape completes without an `or_put_*` bound assert, and `checkdb` stays clean. | Coordinator | Probes below | 5 |

**Not applicable, with reasons**

- **Concurrency:** the code reads the caller's record, a per-thread `attr_info` and immutable cached class representations. Each parallel build worker resets its own `attr_info` (`btree_sort.c:2070-2085`). The key buffers are stack arrays or private heap allocations.
- **Recovery:** no log record, undo or redo, or page layout changes.
- **HA:** the key encoding and the replication items are unchanged.

## Verification

### Local runtime probes (coordinator)

- Build: `debug_gcc` preset from the clean review worktree at `bf5618f627`, installed to a worktree-private prefix.
- Mode: SA (`csql -S`) in a disposable database `rv8711`.
- Pass condition: no assert or crash, and `cubrid checkdb -S rv8711` exits 0 after each probe.
- The head's `or_init ()` now carries the real buffer size, so any overrun on these paths fails the debug assert.

| Probe | Shape | Paths | Result |
| --- | --- | --- | --- |
| P1 | Jira case. `ADD COLUMN c VARCHAR(5000) DEFAULT repeat('x',4200)` on existing rows, then `CREATE INDEX (c, id)`, then UPDATE and DELETE of old rows. | generate_key, get_key | Pass |
| P2 | Key header only. 60 SMALLINT columns and a VARCHAR holding incompressible random strings of 3,850–3,990 chars (15 rows), with an index on all 61 columns. Then UPDATE, DELETE and INSERT…SELECT. | generate_key, get_key | Pass |
| P3 | Compressible strings. Two VARCHAR(20000) columns of 8,000–9,000 repeated chars, with index `(v1, v2, id)`, then UPDATE and DELETE. | Compressed path | Pass |
| P4b | Fixed CHAR defaults added after rows: CHAR(2048) ×2 and CHAR(100), with index `(ch, ch2, ch3, id)`, so the key is above 4 KB. Then UPDATE and DELETE. | Default path, CHAR | Pass |
| P5 | VARCHAR(10) widened to VARCHAR(5000) without a row rewrite, then a 4,500-char default column. Index `(v, c, id)`, then UPDATE and DELETE. | Mixed representations | Pass |
| P6 | Function index `(c, id, upper(a))` on a 4,300-char default column. | Function index | Pass |
| P7 | FK `(c, pid)` on a 4,200-char default column, then `ON DELETE CASCADE`. | FK check and action | Pass |
| P8 | R2's NUMERIC hypothesis. Six `NUMERIC(38,0) DEFAULT 1` columns added, then each changed to `NUMERIC`, with a 4,090-char incompressible VARCHAR. Index on all 7 columns, then UPDATE and DELETE. | NUMERIC domain change | Pass |

The base was not rebuilt locally, so these probes are not a local negative control. Base failure evidence comes from the PR's recorded runs and from TC reviewer R3's size arithmetic (see below).

### CI on the head

- `gha-ci` run [45519549478](https://github.com/CUBRID/cubrid/actions/runs/45519549478) built engine `bf5618f627` with `cubrid-testcases` at `d47276bbf0`, and `cubrid-testcases-private-ex` at the `tc/pr-8711` tip, which is `d4a7bcab09` (committed before the run).
- build (debug and release), test_sql, test_sql_by_cci, test_medium and test_shell all succeeded.
- Attempt 1 had one shell NOK, `shell/_06_issues/_26_2h/apis_1125`, a JDBC case unrelated to heap key building. It passed on the rerun (attempt 2).
- code-style, cppcheck, license and pr-style passed.

### TC review (R3)

- **Paths covered:**
  - `heap_attrinfo_generate_key ()`: serial, parallel (shell) and ONLINE builds, and the ADD FOREIGN KEY check.
  - `heap_attrvalue_get_key ()`: UPDATE, DELETE, ON DELETE CASCADE and SET NULL, checkdb (shell), DROP COLUMN, SET DEFAULT, function index and partition.
  - Each SQL case compares a covering index read with a heap read (`USING INDEX NONE`).
- **Compression trap avoided:** R3 ran LZ4 with the engine's acceptance rule over every long TC string. None is accepted for compression, so all are stored raw and do overflow the old estimate. A `repeat('a', 4200)` default would have compressed to a few dozen bytes and hidden the bug.
- **Answer file:** R3 recomputed it independently. The hashes and all 71 Case 10 rows match. Every SELECT is ordered, and no OIDs, timestamps or variable error text appear.
- **Shell conventions:** they match sibling cases (`cbrd_28322.sh`, `cbrd_28120.sh`), `finish` restores the configuration on every path, and `bash -n` and shellcheck are clean.

## Unverified risks and open questions

None of these is introduced by this PR or blocks it.

| ID | Item | Status |
| --- | --- | --- |
| R1-C1 | `heap_midxkey_get_oos_extra_size ()` returns `(int) ref.length ()` from a 64-bit length ([heap_file.c:12715](https://github.com/CUBRID/cubrid/blob/bf5618f6275c4a1053b648b17b22786dca31bfcc/src/storage/heap_file.c#L12715)). A corrupt OOS stub, or two OOS values near 1 GB in one key, could wrap `midxkey_size` negative and select the stack buffer. | Pre-existing (the OOS sum predates this PR). Source only. Possible follow-up: sum in 64 bits and treat an out-of-range length as corruption. |
| R1-C2 | `heap_midxkey_key_get ()` writes the function result with `func_domain->type`, while the estimate measures the value's own type. | Not shown reachable. Pre-existing. Cheapest check: an assert that the two types are equal, run under the function-index regressions. |
| U1 | Databases that still hold strings in the encoding used before string compression would get keys 4 bytes longer per long string. | Record header slack likely absorbs this, and base behaves the same. Unverified. |
| TC-S1 | The recorded base run stops at Case 1 or 2, so Cases 3–10 and the shell `t_inline` and `t_oos` checks were never shown to fail on their own. Case 10 overshoots the old estimate by only about 0–15 bytes. | Optional. Run those cases alone on base. |
| TC-S2 | No REPLACE or ON DUPLICATE KEY UPDATE case. | Optional. Low risk, because those paths build keys from the new, complete record. |
| TC-S3/S4 | Label shell verdict 5 when the parallel check is skipped on 2 or fewer cores, and note the 16 KB page assumption in the headers. | Optional nits. |

**Dropped candidates:**

- R2 H-NUM was rejected in source, because a NUMERIC precision increase rewrites every row. Probe P8 confirmed it by execution.
- R1 and R2 rejected compression, CHAR padding, alignment and header-count hypotheses with source evidence (S2–S4).

## Coverage

See [coverage.md](coverage.md). Every changed hunk has an owner. The shared question Q1, whether the key can exceed `MAX (midxkey_size, DBVAL_BUFSIZE)`, was answered "no" independently by R1 (opus) and R2 (sonnet).

**Limits:**

- The probes ran in SA mode on a debug build only. Release and CS runs come from CI and the PR author.
- There was no local base negative control.
- The backport notes in the PR (11.4 and earlier) were not reviewed.

## Reviews on the PR

- hornetmj approved #8711, #4418 and #5114, without a review body.
- The Greptile summary on `99e467e5d5` reports no blocking defect.
- No inline review comments.

## Budget

- Bounded default mode, with no hard cap enforced.
- Three reviewers: R1 opus, about 8.5 minutes; R2 sonnet, about 11 minutes; R3 sonnet, about 12 minutes. All finished within their 30–40 minute targets.
- The coordinator built the head, ran 8 probes, checked the CI logs and published.
- Per-agent token use is not attributable against the account quota, so usage beyond the subagent totals is unknown.

## Reviewer evidence

- [reviewers/r1-systems-storage.md](reviewers/r1-systems-storage.md): bound soundness, type encodings, overflow.
- [reviewers/r2-callers-or-buf.md](reviewers/r2-callers-or-buf.md): independent Q1, callers, `or_init`, ownership, N/A domains.
- [reviewers/r3-tc.md](reviewers/r3-tc.md): TC PR review.
- [probes/](probes/): probe SQL (P1, P4b, P8). P2–P7 are inlined in `p2.sql`.
