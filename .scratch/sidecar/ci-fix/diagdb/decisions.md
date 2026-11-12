# Sidecar CI fix: diagdb (bug_xdbms4309)

Worktree /home/vimkim/gh/cb/sidecar-fix-diagdb, branch sidecar-fix-diagdb, base 84e24e39f4, debug_gcc.
Fix commit e1098a7f40 `[Sidecar] diagdb dumps a heap's store with its owner, not as a class heap`. Not pushed.

## Reproduction (measured)

The bug_xdbms4309 steps in SA mode (`repro.sh` in the session scratch, same SQL as the case):

- sidecar_force_external=yes: `diagdb -d 9 --dump-records` exits 254 with
  `heap_file.c:2369: heap_classrepr_get ... Assertion 'false' failed`. Verdict NOK.
- sidecar_force_external=no: exits 0, 100 "hello kitty" lines. Verdict OK.
- With yes, createdb already gives `_db_query_spec` a store (two FILE_HEAP files with class OID 0|193|13). The crash is
  in that store, not in foo, whose 11-byte values stay inline.

## Root cause (measured + code)

`file_tracker_dump_all_heap ()` calls `heap_dump ()` for every FILE_HEAP and FILE_HEAP_REUSE_SLOTS file.
`heap_sidecar_create_store ()` makes the store a FILE_HEAP whose descriptor carries the hot heap's class OID. So
`heap_dump ()` read the store's value records with `heap_attrinfo_read_dbvalues ()` as objects of that class; the
representation id read from a value record is garbage (8388607) and `heap_classrepr_get ()` asserts.

This is a Sidecar defect, not a develop one: develop has no FILE_HEAP whose records are not objects of its class.
It does not need force_external. Before the fix, `check_diagdb.sh` crashes with force_external=no too, because a
4.5 KB value goes to the store under the default policy (`check-before.txt`).

## Fix

`heap_dump ()` returns at once when `heap_sidecar_get_owner ()` says the file is a store. The owner's dump adds a
`SIDECAR STORE FILE INFORMATION FOR HEAP FILE` section with `file_dump ()` of the store, like the overflow file.
One dump block per class heap again, so diagdb's heap blocks pair with class names as before.

Rejected: skipping stores in `file_tracker_item_dump_heap ()` (file_manager.c). Same output, but every other
`heap_dump ()` caller would still crash on a store, and the store would vanish from the dump.

## Checks

- `check_diagdb.sh` (this directory): diagdb -d 9 with and without --dump-records, force_external yes and no, a
  catalog store and a user table store. Before the fix 5 FAIL (`check-before.txt`), after 8/8 PASS (`check-after.txt`).
- test_sidecar (UNIT_TEST_SIDECAR=ON, the P1c `unit_tests` scenario's binary): All tests passed (2686 assertions in
  16 test cases).
- Native testkit shell, tc/pr-8504 at 37de34d9e, engine 84e24e39f4 + the fix, attempts under ~/tk:
  - dg1 bug_xdbms4309: `[OK]`.
  - dg2 _01_show_heap_header: `[OK]` (CI failed it at the 34th heap).
  - dg3 cbrd_26527: `[NOK]`, Cases 1-3 OK, Case 4 "Failed to extract MULTIPAGE HFID", same as CI.
  - The focused verify helper reports FAIL on all three: "total case count is 22, expected 1". testkit counts 21
    SKIP_BY_MACRO cases from the corpus scan in the total. Each attempt dispatched exactly the one selected case.

## cbrd_26527 is not this bug (measured)

SA run of its table (10 x char(2048), compression off): with force_external yes and no, the values go to a store
(HEAP of 430 / 390 pages, `dba.tbl`) and `MULTIPAGE_OBJECT_HEAP` count is 0. The case needs a row larger than a
page to create an overflow file; Sidecar moves the values out of the row first. The diff is a heap layout change
from Sidecar's write policy, not only from force_external, and not a diagdb failure. Cases 2 and 3 (drop reclaims
the pages, store included) pass. Owner decision needed: testcase expectation under Sidecar, or a policy exception.

## Not covered

- `diagdb` dump of the store's records themselves (`--dump-records` prints the owner's objects with values read
  through the store, not the store pages).
- Other whole-database heap walkers (`file_tracker_dump_all_heap_capacities`, compactdb, checkdb) were not audited
  for the same assumption here.
- No CI rerun, per brief.
