# Schema/DDL reviewer report (opus)

The coordinator saved this report from the reviewer's final message, because the harness blocked the subagent from writing the file. The raw outputs are in this directory.

## Pinned identity
- HEAD is 9ae07b9491b1393841ecb0f3579752a598bf68ec. The merge base is d52b1889e907abcf84190ec504dde3bc93de260d. The tree is clean.
- The binaries are the installed `build_preset_debug_gcc` (11.5.0.2789 debug). No file under `src/` or `msg/` is newer than the build.

## Inspected paths
- Parser: `csql_grammar.y`, `csql_lexer.l`, `keyword.c`, `parse_tree.h` and `parse_tree_cl.c`.
- `execute_schema.c`:
  - `do_resolve_oos_storage_flag`
  - `do_add_attribute`
  - `do_change_att_schema_only`
  - `build_attr_flag_change_property`
  - `build_attr_change_map`
  - `check_att_chg_allowed`
- `class_object.c`, `object_printer.cpp`, `unload_schema.c`, `storage_common.h` and `db_info.c`.
- Flag read-back, printing and HA text:
  - `object_representation_sr.c`
  - `transform_cl.c:2976,3113`
  - `catalog_class.c` (`catcls_filter_attflag`)
  - `execute_statement.c:17220`
- `unit_tests/oos/sql/test_oos_sql_storage.cpp`

## Invariants and safety facts (evidence level)
- **Keyword (5).** FORCE_INLINE is not reserved. It has flag 1 in `keyword.c` and appears in the `identifier` rule. A table and a column named `force_inline` worked.
- **Keyword table order (2).** `pt_find_keyword` sorts the table once, then binary-searches it.
- **Grammar conflicts (4).** bison 3.0.5 reports 839 S/R and 1534 R/R conflicts on base, and 842 and 1539 on head. The 206 conflict states are unchanged. The 8 new conflicts are on lookahead FORCE_INLINE, in the same states where FORCE_OUTLINE already conflicts. These are the generic conflicts that any non-reserved keyword adds.
- **Bitfield (2).** `attr_storage:3` holds the values 0..5.
- **Flag bit (2).** 0x4000 has no collision.
- **Persistence (5).** The flag is written as a full int and read back. The server honours it after loaddb.
- **Exclusive policy flag (3, plus 5 from probes).** When a column gains a flag, the whole mask is cleared first. When it loses a flag, only that bit is cleared.
- **Spec rules on policy change (5).** Every accepted rule in OOS-CONTEXT.md:109 holds in SHOW CREATE (probe p2). FORCE_OUTLINE and PREFER_* are rejected on fixed types. NOT NULL, DEFAULT, INVISIBLE, SET DEFAULT and RENAME COLUMN keep the flag.
- **Non-normal attributes (5).** CLASS, SHARED and VCLASS attributes reject every STORAGE clause.
- **Partitions (5).** The flag propagates on create, ADD, MODIFY, ADD PARTITION and REORGANIZE PARTITION. A 20,000-char incompressible FORCE_INLINE value logs -1393 for the partition class. A plain table logs nothing, because its value goes to OOS.
- **Subclasses (5).** Subclasses inherit the flag. A storage-only MODIFY propagates to them. A type change is still blocked by the hierarchy rule.
- **LIKE and CTAS (5).** LIKE copies the flag. CTAS applies an explicit column clause. Plain CTAS does not copy the flag, which matches how it handles other column options.
- **Error paths (3).** `build_attr_change_map` frees the domain on its new failure path. The returns in between are all error returns.
- **unloaddb/loaddb round trip (5).** 31 statements, 6 objects, 0 failed. SHOW CREATE and `;sc` output are identical for 13 tables, the partitions and the subclass.
- **SHOW CREATE re-parse (5).** 10/10 strings re-parse and print back identically.
- **pt_print_attr_def gap (3).** This PR does not make it worse. HA replicates `sql_user_text`.

## Commands and results
- Probes in `probes/` (p1, p2, p3, p5, p6, p9) have matching `*.out` files.
- `roundtrip/` holds the unload, loaddb and show diff outputs. The diff is empty.
- `bison/` holds the conflict summaries.
- `unittest/test_oos_sql_storage.out` shows 43/43 passed.
- p7 and p8 are invalid probes, because `repeat('x',20000)` compresses below the limit.

## Candidate findings
- Reproduced: none.
- Source-only: none.
- Notes (not defects):
  - **N1.** No unit test covers partition or subclass propagation, or unloaddb/loaddb. The probes above cover them.
  - **N2.** The new enum members lack the trailing comments their siblings have. The comment on `PT_ATTR_STORAGE_DEFAULT` was removed. Style only.
  - **N3.** `catcls_filter_attflag` does not expose OOS policy flags in `db_attribute`. This predates the PR and is not made worse.

## Coverage
Complete for the assigned scope. Not covered:
- An HA runtime check. Only a source argument was made.
- Release and Windows builds.
- CS mode. The DDL paths are client-side code shared with SA mode.
