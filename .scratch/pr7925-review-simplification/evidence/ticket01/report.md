# PR #7925 ticket 01 implementation evidence

Status: ticket 01 is complete in two scoped local commits. Final-revision verification and both independent review axes passed. No production change or prerequisite integration.

## Source identities

- Worktree: `/home/vimkim/gh/cb/pr7925-01-stored-rows`
- Branch: `task/pr7925-01-stored-rows`
- Pinned starting revision: `1c660d22e4340ee707336ad08c8b4bf4b69744de`
- Whole-PR integration baseline: `fb567a629cdb390fff920542173fa36f454c74a0`
- Initial implementation commit: `ba308c529a65d25f64897f7733ff167e2f6c1745`.
- Final repair commit: `625b193745959d0ab047f26f4354e9aacb48160d`, parent `ba308c529a65d25f64897f7733ff167e2f6c1745`. Both commits touch only the same comparison test file.
- Final comparison source SHA-256: `adc506598e3e69e4346e2392611b95cb00dbda8c060f9e3260e42f90c305feb6`
- Initial committed source SHA-256: `47d255544271f2217b73796ca980e154bba056d0e5bea04cb8aed304603bef4a`
- Pre-format verification source SHA-256: `51aaa67b348a9e60b5d6b852d78802f07f8b664066ee6365e51fc35dca584d90`. The commit hook changed only indentation/continuation alignment; `git diff -w --exit-code` proved that the formatter diff contains no other change.
- `gh-pr-info` in the task worktree returned no PR for the task branch; `AGENTS.user.md` was absent.
- No CBRD-27089 change was integrated. Production code is byte-for-byte unchanged from the pinned ticket base. The original PR production delta remains in `whole-pr-production.diff`.

## Acceptance mapped to evidence

| Ticket requirement | Implementation and proof |
| --- | --- |
| Two real writes and OID capture | The SQL INSERT and commit remain; attribute values are put into a fresh workspace object, flushed with `locator_flush_instance`, and committed. Both rows are captured by OID through the same `heap_get_visible_version` helper. Returned bytes are copied before ending each heap scan cache. |
| Remove extra serialization and conversion cleanup | No `tf_mem_to_disk`, 1 MiB scratch buffer, reference record conversion, `record_descriptor`, or test-owned system operation remains. Ordinary transaction abort, DROP TABLE, and commit remain in `TearDown`. |
| Preserve 21 cases | All eight named scenarios and the same 13 parameter values remain. The baseline receipt proves all 21 executed before refactoring; the final receipts prove final execution. |
| Independent expected values | Each fixture has a SQL predicate describing its expected stored values. The helper requires exactly two rows total and exactly two matching the predicate. VARBIT predicates cast `REPEAT` to BIT VARYING; JSON compares complete canonical values with `JSON_PRETTY`, including array order. |
| Independent OOS placement | Every variable column has an explicit expected selection. Expectations are expressed in variable-column declaration order, then mapped through that stored row's representation metadata to its VOT location. Record-level HAS_OOS and expected offset width are also checked on both rows. The final repair groups selections, offset width, and optional first encoded size into one fixture-local `storage_expectation`; old/current rows have distinct values. |
| Small, NULL, empty, storage priority and equal-size behavior | Tiny/NULL/empty values remain inline. LargestFirstAndPreferInline expects a inline and b/c OOS-backed. EqualSizeTie expects a OOS-backed and b inline under the existing storage-index tiebreak. FORCE_OUTLINE, compressed VARCHAR/JSON, wide layouts and collection cases remain. |
| Collections and layout | Collections are decoded with their schema domain and compared logically, allowing optional domain encoding. All other same-representation cases compare serialized attribute payloads and record-body lengths after subtracting each MVCC header. Offset width has a fixture-specific literal expectation. |
| All 13 encoding boundaries | Each boundary checks exact logical values, a literal expected encoded size for column a (inline entry length or OOS full length), expected per-column OOS placement, expected two-byte offsets, and equality of the two record-body sizes. The payload bytes are compared across the two actual write paths. Thus the encoded-size oracle covers each parameter independently while record-body size equality checks consistent layout between the two writes without assuming identical MVCC headers. |
| Old representation | The original committed SQL row retains its old representation; the workspace row uses the new representation. Their masked representation IDs must differ. Both retain the original exact 5,000-byte VARBIT value and added default `'new attribute'`; `BIT_LENGTH(a)=40000` and a's 5,008-byte serialized length are asserted. a is OOS-backed in both; the added b is inline in the current workspace row. No old/current raw layout equality is required. |
| Preserve 13 loader/workspace cases | `unit_tests/oos/test_oos_workspace.cpp` is unchanged; its working file and base hashes match. The baseline and final receipts count executed cases, including references, reserved OIDs, rollback, filtered duplicates, external LOB filenames/content, policy, multi-chunk values, ordinary/OOS bigone behavior, partition scenarios and successful no-logging loading. |
| Production invariance | `git diff 1c660d22e -- src` is empty. No ownership interface, allocation policy, partition selection, memory release order, force flags, or logging contract is changed by this ticket. No benchmark is needed for a test-only change. |
| Standards and Spec review | Self-review checked the applicable GoogleTest exception, existing brace/indent style, cleanup lifetimes, fixture expectations, approved seam, and all ticket criteria. The coordinator conducted independent Standards and Spec review on the first scoped commit: no hard standards breaches and no spec gaps were reported. A low-severity Data Clumps finding was addressed by grouping storage expectations; the coordinator reported zero findings on both final review axes at `625b193745959d0ab047f26f4354e9aacb48160d`. Whole-PR production and test delta against `fb567a629` was inspected and saved separately. |

Boundary input → serialized-size oracle:

| Input bytes | Serialized bytes |
| ---: | ---: |
| 20 | 24 |
| 21 | 24 |
| 24 | 28 |
| 25 | 28 |
| 244 | 252 |
| 248 | 256 |
| 252 | 260 |
| 3800 | 3808 |
| 4040 | 4048 |
| 4060 | 4068 |
| 32760 | 32768 |
| 32768 | 32776 |
| 65536 | 65544 |

These are literal worked encoding expectations, not calls to the production size calculator. The 20- and 21-byte inputs occupy 24 bytes and do not shrink when replaced by a 24-byte OOS inline stub, so they remain inline. Later boundary fixtures exceed that size and FORCE_OUTLINE selects a. The forced 65,536-byte case in the named suite explicitly requires one-byte offsets after demotion; the wide 71-variable-column fixture requires two-byte offsets. No comparison assumes that committed MVCC headers are identical.

## Commands and results

All source commands ran in the task worktree. Evidence files are under this report's directory.

```sh
just -f /home/vimkim/my-cubrid/cubrid-justfiles/justfile -d . prepare-build
cmake --list-presets=configure
direnv exec . just configure
direnv exec . just build
direnv exec . sh -c 'cub-workenv init --worktree "$PWD" --install "$CUBRID" --preset "$PRESET_MODE" --no-db'
direnv exec . just configure
direnv exec . just --justfile /home/vimkim/tmp/pr7925-ticket01-evidence/ctest.just selected '^test_oos_(sql_workspace_bytes|workspace)$'
```

The default live `debug_gcc` preset was selected. Initial configure/build/install passed. Initial build-only configuration had no registry; explicit `--no-db` initialization created this worktree's unique registry/environment but no database, then configuration captured those values for the CTest fixtures. The baseline focused selection passed 4/4 CTests, executing 21 comparison and 13 real utility/workspace cases (34/34 passed).

After the final JSON expectation change:

```sh
direnv exec . just build
direnv exec . env GTEST_FILTER=OosWorkspaceBytes.CompressedStringAndJson just --justfile /home/vimkim/tmp/pr7925-ticket01-evidence/ctest.just selected '^test_oos_sql_workspace_bytes$'
direnv exec . just --justfile /home/vimkim/tmp/pr7925-ticket01-evidence/ctest.just selected '^test_oos_(sql_workspace_bytes|workspace)$'
direnv exec . env GTEST_OUTPUT=xml:/home/vimkim/tmp/pr7925-ticket01-evidence/gtest-full/ just --justfile /home/vimkim/tmp/pr7925-ticket01-evidence/ctest.just selected '^(oos_|test_oos|test_byte_span_writer)'
```

The build/install and the targeted complete-JSON-value check passed. The focused selection passed 4/4 CTests with all 21 comparison and 13 utility/workspace cases executed and passed. The pre-format full suite passed 37/37 CTests and 336/336 executed GoogleTest cases, with zero failures, skips or disabled cases. That full receipt and its 31 XML files are preserved under `oos-full-before-formatting.log` and `gtest-before-formatting/`.

The hook's formatting changes were committed, then `direnv exec . just build` built and installed commit `ba308c529a65d25f64897f7733ff167e2f6c1745`; `build-committed.log` records that success. Its full suite passed 37/37 CTests and 336/336 GoogleTest cases with zero failures, skips or disabled cases, in 285.46 seconds. That exact-commit receipt is preserved separately in `oos-full-ba308c529.log`, `gtest-ba308c529/`, and `case-receipts-ba308c529.json`.

The independent Standards review requested a small expectation value. The second commit groups each fixture's OOS selections, offset width and optional first encoded size, with distinct SQL/workspace expectations for schema evolution. All predicates and assertion values remain the same. The normal-row helper overload shares a single expectation; the boundary fixtures no longer pass unused schema-change arguments. Before this commit, the repository formatter reported `Unchanged`, then the build/install passed. The pre-commit hook also reported `Unchanged`.

```sh
bash .github/workflows/codestyle.sh unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp
git diff --check
direnv exec . just build
git add -- unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp
git commit -m '[CBRD-27424] Group stored-row storage expectations'
direnv exec . just build
direnv exec . just --justfile /home/vimkim/tmp/pr7925-ticket01-evidence/ctest.just selected '^test_oos_(sql_workspace_bytes|workspace)$'
direnv exec . env GTEST_OUTPUT=xml:/home/vimkim/tmp/pr7925-ticket01-evidence/gtest-full/ just --justfile /home/vimkim/tmp/pr7925-ticket01-evidence/ctest.just selected '^(oos_|test_oos|test_byte_span_writer)'
```

`build-repair-committed.log`, `focused-repair-final.log`, `oos-full-final.log`, and `gtest-full/` belong to final commit `625b193745959d0ab047f26f4354e9aacb48160d`. The final focused selection passed 4/4 CTests in 120.90 seconds, with all 21 comparison cases and all 13 utility/workspace cases executed and passed. The final full selection passed 37/37 CTests in 285.66 seconds and 336/336 executed GoogleTest cases, with zero failures, skips, or disabled cases across 31 XML receipts. The coordinator independently passed its final integration focused selection at the same commit with 21+13 XML case counts. `run-identities.json` explicitly associates each source revision/hash with its own receipts.

`ctest.just` is an evidence-only filtered form of the live `core::ctest` recipe. It preserves the socket preflight, selected build directory, verbose failure reporting, and `installation-use 300` lock. The live recipe has no filter argument. The full selection discovers all 37 configured OOS CTests, including every OOS database setup/cleanup fixture and the real installed-utility fixture.

## Failed implementation iterations

All failures were preserved and corrected, without changing production or weakening expectations:

- `build-refactor.log`: the heap-read API expects a mutable class-OID pointer; the helper now passes a local OID copy.
- `comparison-refactor.log`: new storage assertions initially assumed declaration order equaled storage order; VARBIT equality predicates also needed explicit casts because `REPEAT` returns VARCHAR.
- `comparison-refactor-2.log`: an unmasked representation-ID macro included record/MVCC metadata bits. The helper now uses `OR_GET_MVCC_REPID`.
- `comparison-refactor-3.log`: the initial equal-size oracle named the wrong declared column; source review confirmed the storage-index tiebreak and the fixed oracle selects a. `LENGTH(a)` did not express the intended bit count; the final predicate uses the source-verified `BIT_LENGTH(a)=40000`, preserving exact payload/default/placement checks. `bit-length-source-receipt.txt` records parser/operator dispatch and the VARBIT-specific `db_get_bit` length extraction at the final commit.
- `focused-before-json-strengthening.log`: all 34 cases passed before the final JSON predicate was tightened to require the complete canonical value and array order. This is additional evidence; final acceptance uses the final source hash and final runs.
- `build-expectation-repair.log`: the first grouped-value draft used an empty aggregate default for a nested expectation type; the compiler rejected that default. A normal-row helper overload now forwards the same complete expectation to both rows, avoiding an empty/default expectation. The final formatted draft built successfully in `build-expectation-repair-final.log`.
- The first commit attempt was rejected because its pre-commit hook auto-formatted 13 lines with AStyle. `commit-hook-formatting.diff` preserves the understood indentation-only changes. After re-staging, the hook reported the source unchanged and the commit succeeded; see `commit.log`. The committed revision was then rebuilt and its full suite rerun for exact source attribution.

## Memory and database cleanup

The removed system operation existed only to undo OOS value chains created by the deleted third conversion. It is not replaced by memory cleanup or another rollback operation. Captured row/attribute buffers are ordinary temporary memory; fixture transaction/table cleanup and CTest-owned database cleanup retain their existing roles. Successful no-logging loading is retained, without claiming failed-unlogged rollback or crash-recovery guarantees.

Only this ticket's source worktree and its fresh CCI clone were used. The build regenerated that clone's tracked `cubrid-cci/win/cci_version.h`; the exact diff is saved as `generated-cci-version.diff`. It was restored before the first commit. Subsequent committed-revision builds left the CCI clone clean; no further restoration was necessary. The original source worktree's dirty CCI files and every other worktree are preserved.

Build/install/workenv metadata and disposable artifacts remain available for coordinator inventory; no source worktree or branch is removed by this ticket. The selected install is `/home/vimkim/.cub/install/pr7925-01-stored-rows/debug_gcc`, registry is `<task-worktree>/.cub-workenv/databases`, and socket directory is `/tmp/cwe-1000/b0aa9ef095a4`. See `workenv-state.json`, `workenv-status.txt`, and the final cleanup inventory for exact retained paths. No unrelated process, IPC, or database cleanup is performed.

The final registry has no database entries. The remaining `unittestdb`, `oosnologdb` and `oosrecoverydb` directories contain only empty `lob` directories; the complete `.cub-workenv` inventory contains six regular files, no symlinks and no data/log/LOB payload files. The state, environment, registry, both configuration files and lock are copied to `workenv-final/` with hashes in `workenv-saved-files.json`. No mount within the task worktree was found by the recorded mount inspection. No registered external/mixed database reference was found; this does not assert ownership of unregistered external paths.

`owned-process-inspection.json` found zero matching readable current-user process candidates and zero TCP/Unix listener matches for the selected ports/TMP path. Two same-user process environments were inaccessible (`sd-pam` and `sshd`); `cub-workenv doctor` additionally reported 2,399 inaccessible host PIDs and warns that absence of owner evidence is not proof of inactivity. The inventory preserves this uncertainty rather than asserting disposal eligibility. No process was stopped or socket/IPC removed.

`ignored-artifact-provenance.json` distinguishes the newly generated build/Gradle artifacts, explicit `--no-db` workenv artifacts, prepared `.env`, and AStyle backup from prepare-build symlink references to personal configuration. The external symlink targets are retained. `cleanup-inventory.json`, `workenv-filesystem-inventory.json`, and `retained-paths.json` record the final paths/state. `prepared-env-file` and both formatter backups preserve useful local files outside the repository. The coordinator alone may inspect and remove the merged ticket worktree/branch; install, short TMP and allocation are retained separately.

Final administrative inspection commands:

```sh
direnv exec . cub-workenv env --worktree "$PWD"
direnv exec . cub-workenv doctor --worktree "$PWD"
git status --short --untracked-files=all
git status --short --ignored
git -C cubrid-cci status --short
ss -ltnp | rg ':(41038|41039)([[:space:]]|$)'
ss -xlpn | rg '/tmp/cwe-1000/b0aa9ef095a4'
```

The `ss` filters had no matches (normal search exit 1). A mistaken preliminary `cub-workenv status` command exited 2 because this live CLI exposes `env` and `doctor`; it performed no mutation and is preserved in `workenv-status-unsupported.log`. The supported `env` and read-only `doctor` commands both returned 0. Final engine and owned CCI Git status are empty.

## Limits

Passing the retained partition scenarios on this pinned PR implementation does not establish acceptance against CBRD-27089's future accepted interface. The coordinator must rerun them after the dependency is included, recording both source identities. No dependency integration, partition repair, production ownership cleanup, push, CI trigger, publication, or integration merge is part of this ticket.
