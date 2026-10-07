# PR7927 owner-index implementation verification

Date: 2026-10-07. Source worktree:
`/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write`, branch
`feat/oos-deferred-write`, local HEAD
`6b53181d31d6d6d2615b18b4f914623bb017d7c4`.
Remote PR head remains `aecce0e1216a813771621c13112c8f27d43df22e`; baseline
`fb567a629cdb390fff920542173fa36f454c74a0`. No remote publication or CI was run.

| Check | Result | Evidence |
| --- | --- | --- |
| Debug configure, build/install | PASS | [Configure](no-record-type-evidence/debug-configure.log), [post-format build](no-record-type-evidence/debug-build.log) |
| Full configured debug CTest | PASS 35/35; 270.89 seconds; SQL-show 49.07 seconds | [Full log](no-record-type-evidence/debug-ctest.log) |
| Focused owner/storage/export/generic packing | PASS 3/3 CTest entries with four selected GoogleTests | [Boundary log](no-record-type-evidence/debug-boundaries-test.log) |
| Eager cleanup, real vacuum and both prefetch directions after review fixes | PASS 5/5 CTest entries | [Review-fix log](no-record-type-evidence/review-fixes-test.log) |
| Assertions-disabled build/install and focused boundary/prefetch checks | PASS 3/3 CTest entries with five selected GoogleTests,19.11 seconds | [Build](no-record-type-evidence/release-build.log), [test](no-record-type-evidence/release-test.log), [NDEBUG proof](no-record-type-evidence/release-ndebug.json) |
| Real client/server loader | PASS 600 bulk rows, 9MiB row, 800 partitioned rows, invalid-child rejection and later load | [Fixture verdict](no-record-type-evidence/loader-green.log), [native result logs](no-record-type-evidence/loader-green/partition-root.log) |
| Standards and Spec review | Zero remaining findings on each axis | [Independent review and corrections](no-record-type-review.md) |
| Removed marker and baseline generic/shared descriptors | PASS; no marker matches; files equal baseline | [Source-contract proof](no-record-type-evidence/source-contract.json) |

The final full suite ran after all behavior changes were built. The commit hook
then normalized five lines of fixture indentation; the final post-format build
and installation also pass. This formatting-only change does not alter the
verified behavior. No test assertion was removed to obtain the result. Raw native/CTest log whitespace
is preserved with an attribute scoped to this evidence directory; source and
Markdown diff checks retain their normal rules.

## Failed reproductions and corrections

- [Owner RED](no-record-type-evidence/owner-red-test.log): a reader without the owner originally accepted temporary memory; the owner-index checks make it fail safely.
- [Export RED](no-record-type-evidence/export-red-test.log): the actual fetch-publication helper originally accepted a temporary row and changed its descriptor/count. The guard rejects before publication.
- [Prefetch RED](no-record-type-evidence/prefetch-red-test.log): an inherited raw neighbor path published a persisted OOS row. Final tests cover both directions: OOS neighbors are skipped and inline neighbors still appear.
- [Loader RED](no-record-type-evidence/loader-red.log) and [partition error](no-record-type-evidence/loader-red-partition.log): the per-row fallback omitted the queued owner; bulk and 9MiB checks passed before the partitioned load failed with error `-1383`. The fallback now forwards that owner.
- [Initial full suite](no-record-type-evidence/debug-first-ctest.log): 32/35; two synthetic fixtures used representation 0/short VOTs despite borrowing db_user metadata, and SQL-show exceeded its 90-second cap. Fixtures now match the borrowed representation/VOT; the enlarged expected-error suite has a bounded 180-second timeout. Final 35/35 includes these corrected fixtures.

The loader fixture produced its PASS verdict after checking 600 20KB values,
one 9MiB value,400 rows in each child, unchanged 800-row count after invalid-child
rejection, and a successful subsequent 30KB value. The task-owned server was
stopped and its receipted internal database deleted; preexisting registrations
were preserved. Native server and master lifecycle logs are retained.

The selected master vanished between separate startup/client commands, so the
successful fixture kept an owned foreground master alive. The fixture Python
process passed; the supervising shell returned 1 during its shutdown trap because
a normal foreground master shutdown returns 1. A separate
[native shutdown probe](no-record-type-evidence/master-shutdown-verdict.log)
confirmed shutdown-command exit 0 and master-wait exit 1 without a database.
[Final doctor](no-record-type-evidence/final-doctor.log) confirms the selected
instance is ready with the original registrations and no task server observed.
This lifecycle return is distinguished from the loader fixture verdict.

## Reproduction commands

Project commands corresponding to the selected personal build workflow:

```sh
cmake --preset debug_gcc
cmake --build --preset debug_gcc --target install
ctest --test-dir build_preset_debug_gcc --output-on-failure --verbose
```

Use the prepared worktree's dedicated installation/configuration/registry/TMP
selection for native DB work. The assertions-disabled verification uses the
separate `/home/vimkim/gh/cb/pr7927-publication-release` worktree at the same
source HEAD with preset `release_gcc` (RelWithDebInfo with `-DNDEBUG`). This is a
safety check, not a performance measurement.

```sh
GTEST_FILTER=OosSqlShow.PendingReferencesResolveAndFinalizeInPlace:OosSqlShow.FinalizationResetsPublicationOnceAndFailureCannotRetry:OosSqlShow.SerializedPreparationPreservesMvccAndOutlivesSource:OosSqlShow.PrefetchSkipsUnexpandedOosNeighbors:OosSqlPacking.GenericDescriptorsPreserveArbitraryBytes \
  ctest --test-dir build_preset_release_gcc -R '^test_oos_sql_show$' --output-on-failure
```

## Limits and preserved work

No UPDATE timing benchmark, unchanged-chain reuse implementation, new runtime
vacuum-reuse experiment, full HA-loader/crash-recovery qualification or company
regression run is claimed. Existing replication group/failure and vacuum tests
are included in configured CTest. Historical CI does not establish new-head
qualification; unresolved medium-ordering attribution remains work item 242.

Original dirty CCI generated files and JDBC checkout are preserved in the source
worktree. Historical docs/evidence and source private DB/core fixtures remain;
only the newly created, receipted internal loader database is subject to test
cleanup. The release verification worktree/build is retained for inspection.
The established loader fixture is
`value-ref-evidence/check-server-loader.py DATABASE ARTIFACT_DIRECTORY`;
[the local supervisor](no-record-type-evidence/run-loader.sh) preserves the exact
successful invocation and shutdown-return caveat. Its database prerequisite was
prepared through the native workenv lifecycle.

Remote replies remain [local Korean drafts](reviewer-comments-aecce0e.md).
