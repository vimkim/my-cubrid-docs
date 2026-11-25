# R3 testcase review: CUBRID/cubrid#8711 and TC PRs cubrid-testcases#4418, cubrid-testcases-private-ex#5114

Reviewer: R3 (TC reviewer). Read-only: no repository modified, nothing pushed or posted, no server run.
(One disclosure: early on I ran `git fetch -q origin` in `/home/vimkim/gh/cubrid-testcases/develop`. The reflog of `origin/develop` shows no entry from it, so it appears to have moved no ref. I ran nothing else that writes to a repository.)

Pinned scope: engine head bf5618f6 (feature commit 99e467e5d), base 6d8296b15c; #4418 head d47276bbf; #5114 head d4a7bcab0.

## Verdict

| PR | Blocking defects | Readiness |
|---|---|---|
| #4418 (`sql/_13_issues/_26_2h/cases/cbrd_28255.sql` + `answers/cbrd_28255.answer`) | none | Ready for approval, subject to the coordinator's local replay on the head build (see "Not verified") |
| #5114 (`shell/_06_issues/_26_2h/cbrd_28255/cases/cbrd_28255.sh`) | none | Ready for approval, same condition |

Both TCs exercise the fixed paths with keys far above the old estimate (default of 4,200 to 5,000 bytes, OOS 9,000 bytes), use incompressible strings (checked below), and follow sibling conventions. The findings below are non-blocking suggestions and nits.

## 1. Do the tests exercise the fixed paths, and would they fail on base?

### 1.1 Compression check (the main trap)

The engine compresses a VARCHAR value of 255 bytes or more with LZ4. It keeps the compressed form only if `compressed_length < str_length - 8` (`src/object/object_primitive.c`, `pr_data_compress_string`, and `OR_MINIMUM_STRING_LENGTH_FOR_COMPRESSION` 255 in `src/base/object_representation.h:1490`). A repetitive default such as `repeat('a', 4200)` would shrink to a few dozen bytes on disk and in the key, so it would not overflow the old buffer. Both TCs avoid this with random letters and digits (SQL file line 37, shell lines 16 and 64 to 73).

I verified this with `LZ4_compress_default` from the system `liblz4`, using the same acceptance rule as the engine (scratch scripts in `.../review-8711/r3work/`):

| String | Length | LZ4 output | Result |
|---|---|---|---|
| SQL `c` default (lines 39 to 81, extracted) | 4200 | 4218 | stored raw |
| SQL `c2` default (lines 85 to 88) | 300 | 303 | stored raw |
| SQL `v` of rows 3 and 4 (`SHA2` hex, 7 x 128) | 896 | 901 | stored raw |
| SQL Case 10 `v`, all 71 lengths 3850 to 3990 (`SHA2` hex) | 3850..3990 | +17 each | stored raw |
| Shell `rnd_str` (gawk 5.1, seeds 1 to 6): 4200, 5000, 3900, 3900, 9000, 9000 | as named | 4218, 5021, 3917, 3917, 9037, 9037 | stored raw |

So the keys really are about default length + header, and the TC data reach the sizes the comments claim.

### 1.2 Coverage by fixed path

| Path | SQL (#4418) | Shell (#5114) |
|---|---|---|
| `heap_attrinfo_generate_key`, serial index build | Cases 1, 2, 4, 10 (lines 91, 97, 109, 169) | verdicts 1, 7 to 18 |
| same, parallel build | not covered | verdicts 5 and 6 (line 133 threshold 80, lines 176 to 201; degree 2) |
| same, ONLINE | Case 3 (line 103) | not covered |
| same, ADD FOREIGN KEY check | Case 7 (line 135), and again in Case 9 (line 149) | not covered |
| `heap_attrvalue_get_key`, UPDATE of an old row | Case 5 (line 115) | verdict 3 and the per-table loop (line 257) |
| same, DELETE of an old row | Case 6 (line 123) | verdict 3 and the loop |
| same, FK ON DELETE CASCADE / SET NULL | Cases 8 and 9 (lines 139, 150) | not covered |
| same, checkdb (`locator_check_btree_entries`, `src/transaction/locator_sr.c:11968`) | not coverable in SQL | verdicts 2, 4, 6 and every loop verdict (lines 108 to 125) |
| `csql -S` (standalone) | not coverable | verdicts 1 to 4 |
| REPLACE / ODKU | not covered | not covered |

Size classes covered:

- Stack buffer, default above 4096, old record tiny: SQL Cases 1 to 3 and shell verdict 1. The overshoot is above 100 bytes, so detection on base does not depend on stack layout.
- Heap buffer with an OOS value: SQL Case 4 (row 7 holds `c` of 4,200 bytes, which the 16 KB-page OOS policy demotes) and shell `t_oos` (v of 9,000 bytes, overshoot about 4,200).
- Inline 3,900-byte row: shell `t_inline`.
- Key header only, no ADD COLUMN: SQL Case 10 only.
- Several representations: SQL Case 4 (rows 1 to 6 in the old representation, row 7 in the next), shell `t_drop` and `t_setdef`.
- Function index: shell `t_func`. Partition: shell `t_part`, with both partitions passed to checkdb (lines 242 to 249).

The "compare index to heap" design is good: every case prints the covering-index read (the plan block shows `(covers)`) and the `USING INDEX NONE` heap read, and the answer pins both to the same values (for example answer lines 25 to 51).

### 1.3 Would they fail on base?

- SQL Cases 1 to 4: yes. The PR reports NOK on a617e19b7 (debug: Case 1 key of 4,195 characters, Case 2 CREATE INDEX crash). In a release build the CREATE INDEX of Case 1 itself overflows by more than 100 bytes. Any wrong key or crash changes the answer.
- Shell: yes for verdicts 1, 3, 5 to 18. The PR reports NOK 17 (debug) and NOK 7 (release).
- Limitation of the recorded negative control: on base the SQL run stops at Case 1 or 2 (server crash), so the later Cases 3 to 10 are never shown to fail on their own. Their independence is argued, not measured. See suggestion S1.
- Case 10 is the thinnest negative control. Arithmetic from the source (not measured):
  - `heap_oos_inline_target_size` is about 4,056 bytes on the default 16 KB page (`heap_file.c:14267 to 14279`), and the demotion test adds a 16-byte MVCC reserve (`heap_file.c:14375`). An inline row of this schema (60 SMALLINT + VARCHAR) therefore stays under about 4,040 bytes, and its key is only about 41 to 49 bytes longer, so it cannot pass 4,096.
  - The rows with v above about 3,890 hex digits are OOS rows. On base their estimate is stub record (24-byte stub included) + full OOS length, so the overshoot is about 0 to 15 bytes: stack for estimates below 4,096, heap otherwise.
  - The PR measured a crash for this shape, and a heap overshoot is normally caught by glibc at `free()`. So the result is credible, but it depends on allocator behaviour, and the comment "rows of 4KB or less" (SQL lines 158 to 161 and 168) describes a case that does not arise at the default page size. See N3.

## 2. Answer-file correctness and determinism (#4418)

I recomputed the data independently (Python, `-I`):

- MD5 of the `c` default (40bfcb08...), `c2` default (e4e09518...) and `'small'` (eb5c1399...) match the answer.
- MD5 of `v` for rows 3 and 4 matches the answer (a9874682..., c57e77b6...). CUBRID `SHA2` returns upper-case hex; with upper-case digests my values equal the answer.
- All 71 rows of Case 10 (s00, `CHAR_LENGTH(v)`, MD5 of the `CONCAT_WS`) match the answer in both blocks (answer lines 404 to 474 and the duplicate heap block); both blocks are identical and sorted by s00. s00 is distinct for all n (7919 and 30000 are coprime), so ORDER BY is total.
- Row sets after Cases 5 to 9 trace correctly by hand: {1,3,5,6,7,12,14}, then {3,5,6,7,12,14}, then {3,6,7,12,14} after CASCADE, then {3,7,12,14} plus one all-NULL child after SET NULL. `p28255` shows {3,6,7,12,14} then {3,7,12,14}.

Determinism:

- Every SELECT has ORDER BY, or is an index scan the plan shows already ordered (answer line 113 "skip ORDER BY"). The NULL-id row sorts first (answer line 386).
- No OIDs, timestamps, variable error text, or per-run values appear. Plan blocks are digit-masked by CTP (`i?_c_id`, `term[?]`, `cost: ? card ?`).
- Cleanup: `DROP TABLE IF EXISTS` at the start (line 29) and the child-first drops at the end (lines 174 to 176). A failed earlier run is tolerated.
- Runtime: 7 + 71 rows, five index builds, a few statements. Seconds.
- Environment: serial index build is assumed (tables far below the 2048-page default `parallel_index_build_page_threshold`, `system_parameter.c:5250`); the 4,096-byte constant `DBVAL_BUFSIZE` does not depend on page size; the OOS demotion of `c` and of the updated rows depends on the 16 KB default page, but those rows trip the old code either way. No CS/SA dependence (CS only).
- Plan lines pin `temp(order by)` vs `iscan` shapes (answer lines 33 to 42, 69 to 78, 105 to 113, 140 to 149, and Case 10). They prove "covering", which is the point, but they are the part most likely to need a future answer revision when the optimizer changes. Same practice as the sibling `--@queryplan` cases, so only a remark.

## 3. Shell TC conventions (#5114)

Compared with `cbrd_28322.sh`, `cbrd_28120.sh` and `cbrd_27151.sh` (origin/develop) and `CTP/shell/init_path/init.sh` (`/home/vimkim/gh/ctp/cubrid-testtools`):

- Header `:<<'DESCRIPTION'`, `. $init_path/init.sh`, `init test`, local `db=db28255`, `cubrid_createdb --db-volume-size=20M --log-volume-size=20M` from inside `$db`, `cleanup` = server stop, `deletedb < /dev/null`, `rm -rf $db`, `rm -f *.log`, `finish`. All match the siblings. Files are mode 100644, LF only, newline at end, `bash -n` clean, shellcheck shows only the expected SC2154, SC2046 and SC2164.
- `abort_test` (lines 56 to 62) calls `write_nok`, `cleanup`, `finish`, `exit 1`. Same pattern as `abort_tc` in `cbrd_28322.sh`.
- `write_nok <file>` cats the file into the result (init.sh lines 602 to 627), as used here (lines 91 to 92 and 122 to 123). `write_ok "<label>"` as used is valid.
- Parameters: `change_db_parameter` appends to `cubrid.conf` and `finish` restores it (init.sh `change_db_parameter`, `restore_all_conf`), including on every `abort_test` path. `parallel_index_build_page_threshold` accepts 80 (range 0 to INT_MAX, `system_parameter.c:5250`). `auto_restart_server=no` keeps a crashed server down so cleanup can delete the database. `init test` itself does `cubrid service stop` and `pkill cub`.
- Checkdb result check (lines 108 to 125): `cubrid checkdb` exits non-zero on inconsistency (`src/executables/util_cs.c`, error_exit path) and the script also greps `error` (the inconsistency message contains `error_log_file`). The per-table form runs `btree_check_by_class_oid` and `locator_check_by_class_oid` (`boot_sr.c`, `xboot_checkdb_table`), i.e. the heap-versus-index key comparison. Good. It first checks the index count (line 112), so a missing index cannot pass silently.
- Parallel proof (lines 193 to 200): the build summary `btree_sort: ... parallel N` is written by `_er_log_debug` "regardless of er_log_debug" (`btree_sort.c:1111, 1135`), so it is present in release builds. The degree rule is `floor(log2(pages/threshold)) + 2`, capped by cores and `n_sects` (`btree_sort.c:1735 to 1860`). About 120 pages over threshold 80 gives degree 2 with two sectors, so the `parallel [2-9]` pattern is safe (no two-digit degree). The guard `nproc -gt 2` matches the engine's `core_count <= 2 -> serial`.
- No hard-coded ports or absolute paths; `$CUBRID/log/server/${db}_[0-9]*.err` is the standard server error log.
- Order of modes is right: the standalone phase (verdicts 1 to 4) runs before `cubrid server start` (line 174); the client-server checkdb and csql afterwards.
- Runtime estimate: one 20 MB database, 600-row parallel build, about 10 checkdb runs. A minute or two.
- Debug/release tolerance: nothing asserts a build-dependent message; verdicts are exit codes, `ERROR` absence and checkdb.

## 4. Commit hygiene

- #4418: `0c1415aa1` bot init, `c01b3c9a5` TC commit (message with Purpose/Implementation/Remarks), `d47276bbf` "Merge branch 'develop' into tc/pr-8711". #5114: `73e19f818` bot init, `c31e37004` TC commit, `89c11d2c4` follow-up "Check the partitions of t_part with cubrid checkdb", `d4a7bcab0` merge of develop. Merges and fix-up commits inside `tc/pr-*` branches are normal here (squash-merged; origin/develop titles look like `[CBRD-28322] ... (#4419)`).
- Placement and names follow the ticket pattern: `sql/_13_issues/_26_2h/cases/cbrd_28255.sql`, `.../answers/cbrd_28255.answer`, `shell/_06_issues/_26_2h/cbrd_28255/cases/cbrd_28255.sh`, matching `cbrd_28295.sql` and `cbrd_28322/cases/cbrd_28322.sh`. No stray files (each PR changes exactly the files above).
- Both PR titles still read "[CBRD-28255] Draft: TC changes for PR CUBRID/cubrid#8711" with the bot body; retitle to a descriptive squash title before merge (several merged TC PRs kept "Draft:", so this is only a nit).

## Findings

### Blocking defects
None.

### Non-blocking suggestions
- S1. Prove the later cases fail independently on base. On base the SQL run dies in Case 1 or 2, so Cases 3 to 10 were never shown to fail by themselves (answer-diff only). Suggest a one-off on the base build: run Case 10 alone (SQL lines 158 to 172 on a fresh database) and shell verdicts for `t_inline`/`t_oos`; ideally also a build with only `heap_attrvalue_get_key` reverted, to show Cases 5, 6, 8, 9 trip it. Cheap for the coordinator, no change to the TC needed.
- S2. REPLACE and ON DUPLICATE KEY UPDATE are listed as affected paths in the PR but no statement drives them. Their key generation is on the new record (`qexec_remove_duplicates_for_replace`, `query_executor.c:18148`; `qexec_oid_of_duplicate_key_update`, `:18378`), which is complete, and the old-row delete/update that follows reuses the DELETE/UPDATE paths of Cases 5 and 6. Risk is low; one `REPLACE INTO` or `INSERT ... ON DUPLICATE KEY UPDATE` against a UNIQUE `(c, id)` index on an old row would close the claim.
- S3. Shell verdict 5 silently drops the parallel assertion on hosts with 2 or fewer cores (line 196) but still prints OK. Put "parallel check skipped, N cores" in the label so a result file shows it.
- S4. Both TCs depend on the default 16 KB page for the OOS demotion points (shell `t_inline` 3,900-byte row stays inline with a margin of about 100 bytes to the ~4,040 limit; SQL row 7 and the updated rows go OOS). Say so in the header comment, or accept it as the CI default.

### Nits
- N1. SQL header lines 12 to 13 describe the debug-build failure ("key cut short and changed", "CREATE INDEX of Case 2 crashed"). On a release build Case 1 itself crashes. Add "on a debug build".
- N2. Shell line 200: the OK label embeds `sorter ..., N records, M runs flushed, buffer B pages` from the server log, so the result line varies between runs and builds. Harmless; cosmetic.
- N3. SQL lines 158 to 161 and 168 and the PR text ("rows of 4KB or less") do not hold at the default page size, because rows with v above about 3,890 digits are OOS (see 1.3). The sweep of 71 lengths still reaches the boundary whatever the exact numbers, so coverage is unaffected.
- N4. Awk `rand()` sequences differ between gawk, mawk and BSD awk (line 67 to 72). No assertion depends on the content, and any random 62-symbol string is LZ4-incompressible, so this is fine; a one-line comment would make that explicit.
- N5. Commit author name differs between the TC commit ("Lim Hyeongtae") and the merge commit ("Hyeongtae LIM"), same e-mail. Cosmetic.

## Not verified

- I ran no server and no CTP, so I did not re-derive the answer by execution. Content of the answer was checked independently by recomputation (section 2); plan blocks and the "0"/"N" row counts were checked by reading and hand-tracing only.
- Both TCs were validated by the author against 99e467e5d on an earlier develop (a617e19b7 and 19d1d8e1d). The head under review (bf5618f6, base 6d8296b15c) contains later develop merges (for example CBRD-28322 and CBRD-28063). A replay of both TCs on the head build, including `sql/_13_issues/_26_2h` and the shell case on a debug and a release build, is the remaining gate; that is the coordinator's step.
