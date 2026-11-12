# btree-del tab: decisions and evidence

Goal: the PR #8504 shell failures that Sidecar causes are fixed before P4. This tab owns cbrd_25122 (DELETE cannot find its index key) and cbrd_24771 (spacedb growth).

Worktree `/home/vimkim/gh/cb/sidecar-fix-btree-del`, branch `sidecar-fix-btree-del`, base `84e24e39f4`. Debug build `debug_gcc`, own install and workenv (port 41350). Testcases from `tc/pr-8504` (`37de34d9e`), worktree `/home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8504-btree-del`.

## Commits

| Commit | Subject |
|---|---|
| `e2e5a98b78` | an SA_MODE DELETE reads its old record expanded (cbrd_25122) |
| `0149d9e633` | a multi-column key fails when a value read fails, not takes NULL |
| `a207a0ecd9` | size a multi-column key buffer for the values of a record with refs |
| `17c355d22c` | the undo of a store insert gives the page's space to the store's bestspace (cbrd_24771) |

## D1. cbrd_25122 reproduces only with the store in use

- Measured: the testcase's SQL in `csql -S`, `sidecar_force_external=yes`, base build: core at `btree.c:36823` on the first DELETE. Same SQL with `=no`: PASS.
- Measured (gdb): the delete key is `{NULL, 2, 1, 1}`. The row is `('a', 2, 1, 1)`. `c_a` came back NULL.
- Measured: `csql.err` has `ER_SIDECAR_DANGLING_REF` (-1396) for store record `1|836|47` just before the assert, and the slotted page logs the slot as empty.

## D2. Root cause of cbrd_25122: the SA_MODE delete removes the store records before the index keys are read

- Code: `locator_delete_force_internal ()` calls `heap_delete_logical ()` before `locator_add_or_remove_index ()` for an MVCC class. In SA_MODE `heap_delete_logical ()` sets `is_mvcc_op = false`, so the hot record and, through the plan, its store records are deleted physically.
- Code: the DELETE read its old record as stored (`stored_form`), so `copy_recdes` holds refs. The index keys read after the delete go through refs to records that are gone.
- Measured: a single-column index (`t_s`) fails with -1396 as an error. A multi-column index fails silently: `heap_midxkey_key_get ()` dropped the error of `heap_midxkey_get_value ()` and wrote NULL.
- Code: SERVER_MODE is safe. Its MVCC delete only stamps the store records, and they stay readable.
- Code: UPDATE is safe. `locator_update_force ()` updates the index (`locator_sr.c:6504`) before the heap (`:6562`). Measured: an SA UPDATE of the indexed column passed.
- Not a develop defect. develop reads `copy_recdes` as a full copy, so the order does not matter there.
- Fix (`e2e5a98b78`): `stored_form` is false outside SERVER_MODE.
- Second fix (`0149d9e633`): the two midxkey builders return NULL when a value read fails, so a later store read failure is an error, not a wrong key. Their callers free a key buffer they allocated.

## D3. Found on the way: the multi-column key buffer overflows for a record with refs

- Measured: with the D2 fix in, `csql -C`, a table `(a varchar(9000), b int)` with index `(a, b)` and 6000-byte values. The DELETE crashed the server. gdb: SIGSEGV in `heap_midxkey_get_value`, frames above it are `0x7878787878787878` (`'x'`), so the stack was overwritten by the value. An UPDATE of a non-key column crashed the same way. CREATE INDEX passed.
- Code: `heap_attrvalue_get_key ()` and `heap_attrinfo_generate_key ()` size the buffer by `recdes->length`. A record with refs holds 16 bytes per large value, so 4096 bytes of stack were used for a 6000-byte key.
- Same family as cbrd_25122 (a key built from a stored-form record), not in CI. Fixed because it is a memory-safety crash in SERVER_MODE that the CI-only default `force_external=yes` and any value above the inline target can hit.
- Fix (`a207a0ecd9`): `heap_midxkey_record_size ()` returns the expanded length (`sidecar_expanded_length ()`) for a record with refs.

## D4. cbrd_24771 is a Sidecar defect: the store does not reuse rolled-back space

- Measured (`space24771.sh`, the testcase's steps with per-round probes, base fix build): hot heap stays at 13 pages, the store grows 10, 14, 14, 18, 22 ... 66 pages over 20 rounds (10 `-C`, 10 `-S`). `spacedb` goes 82.0M to 83.0M at the last `-S` round, as in CI. With `force_external=no` the table has no store and nothing grows.
- Measured: the native shell run of cbrd_24771 before the fix: cases 1 to 21 OK, case 22 NOK (`~/tk/bd2`), as in CI.
- Code: `heap_rv_undo_insert ()` deletes the store record but adds the page to no bestspace. Its comment says why: the store HFID was not reachable without fixing the hot header under the store page (I-7).
- Fix (`17c355d22c`): `sidecar_undo_store ()` finds the store, and the undo calls `heap_add_bestpage ()` on it. `heap_add_bestpage ()` only looks the bestspace up, it fixes no page.
  - SERVER_MODE reads the class HFID cache (`heap_get_hfid_if_cached`) and the store cache. No page is fixed under the store page, so I-7 holds.
  - SA_MODE: measured that the cache lookup misses (gdb, `cached = false`, then the store cache too). Code: `lock_has_lock_on_object ()` returns 1 outside SERVER_MODE, so `sidecar_store_for ()` takes its SCH_M branch and never caches a store. SA_MODE reads the hot header instead. There is no other thread to wait on a latch, so this adds no deadlock (inferred from the single-threaded SA model).
  - Tried and reverted: filling the class HFID cache in `sidecar_store_for ()`. It did not change the SA result (measured 10 to 46 pages), because the store cache was the miss.
- Measured after the fix: the testcase steps keep the store at 10 pages for 18 of 20 rounds, then 14 and 18. `spacedb` stays 82.0M.

## D5. What remains of the store growth is the one-use slot rule

- Measured (`show slotted page header` after 20 rounds): store pages hold 1 to 2 records and up to 1,892 slots.
- Code and design: a store slot holds one record in its life (`heap_rv_undo_insert ()` uses `spage_delete`, design decision "non-reuse store", `sidecar/decisions.tsv` 2026-11-04T11:22:51Z). Each rolled-back value keeps a 4-byte slot.
- Inferred: the store still grows, at about 4 bytes per rolled-back value instead of the value's size. Not changed here. It is a design decision, not this defect.

## D6. The focused checks

- `check_index_keys.sh` (this directory): t_c (the cbrd_25122 shape), t_s (single-column), t_b (6000-byte two-column key, DELETE and UPDATE), t_p (partition key), `force_external=yes/no` x `csql -S/-C`, with checkdb.
  - Measured base `84e24e39f4`: 8 of 12 FAIL (`keys-before.txt`).
  - Measured on `17c355d22c`: 12 of 12 PASS (`keys-after.txt`).
  - `force_external=no` fails on base too, because 6000-byte values go to the store by the inline-target policy.
- `check_store_rollback.sh`: 10 rounds of 200 store values rolled back by a unique violation, `csql -C` and `-S`. Pass when rounds 2 to 10 grow the store by at most one 4-page extension.
  - Measured on `a207a0ecd9` (before the store fix): FAIL, store 14 to 50 pages (`-C`) and 10 to 46 (`-S`) (`store-before.txt`).
  - Measured on `17c355d22c`: PASS, 14 to 14 (`-C`) and 10 to 14 (`-S`) (`store-after.txt`).
- `space24771.sh` and `space24771.txt`: the cbrd_24771 steps with per-round hot pages, store pages and spacedb, before and after the store fix.
- The P1c harness (`p1c/run_p1c.py`) is fixed to `/home/vimkim/gh/cb/sidecar`, which this tab must not touch, so the checks are standalone scripts that take the worktree as an argument. Its `unit_tests` scenario is `build_preset_debug_gcc/bin/test_sidecar`. Measured on `17c355d22c` (built with `-DUNIT_TEST_SIDECAR=ON`): all tests passed, 2,686 assertions in 16 test cases.

## D7. The native shell runs

- `testkit-focused.py verify` reports FAIL for every attempt with "total case count is 22, expected 1". The corpus has 21 cases skipped by the `LINUX_NOT_SUPPORTED` macro, and the summary counts them. The verdicts below come from `run.log`, `test-shell.xml` and the testcase's own result lines (`shell-runs.txt`).
- `~/tk/bd1`, cbrd_25122 on `a207a0ecd9`: OK, 18 of 18 assertions.
- `~/tk/bd2`, cbrd_24771 on `a207a0ecd9`: NOK, case 22 only, as in CI.
- `~/tk/bd3`, cbrd_25122 on `17c355d22c`: OK, 18 of 18.
- `~/tk/bd4`, cbrd_24771 on `17c355d22c`: OK, 22 of 22.

## Not covered

- No release build of the four commits. No CI rerun (not allowed by the brief).
- The one-use store slot still grows the store under many rollbacks (D5).
- SERVER_MODE undo misses the store when the class HFID cache or the store cache has no entry, for example a class created in the same transaction. That rollback leaves its store pages unused, as before the fix.
- The other shell failures of run 43184757385 belong to other tabs.
