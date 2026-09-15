# CBRD-27424: standalone loaddb OOS diagnosis

Date: 2026-09-11. Work item: 130. Status: shared standalone workspace fix implemented and verified locally; work item complete.

## Reproduced result

Worktree: `/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa`.
Source: `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`.
Build: GCC debug, CUBRID `11.5.0.2648-f4299ac`, installed specifically for this worktree.
Each ordinary-mode comparison loads the same deterministic 5,000-byte VARBIT into one row of a fresh one-column table. Exact equality checks run after commit in another connection. `;oos_stats` supplies physical live-chunk counts; neither row count nor `DISK_SIZE` substitutes for physical evidence.

| Route | Exact value equality | Live OOS chunk records |
|---|---|---:|
| `loaddb -S` | Pass | **0** |
| Ordinary INSERT through `csql -S` | Pass | 1 |
| Ordinary INSERT through `csql -C` | Pass | 1 |
| `loaddb -C` | Pass | 1 |
| `loaddb -S --no-logging`, separate disposable DB | Pass | **0** |
| SA loader with two mutually referencing numbered objects | Pass, including referenced IDs | **0** |
| SA loader into two range partitions | Pass for both values; IDs routed to both partitions | **0 in each partition** |

**CSQL qualification:** `SET SYSTEM PARAMETERS 'insert_execution_mode=0'` followed by INSERT and COMMIT selects workspace writes in `csql -S`. This produces **zero OOS records** with exact logical value equality, and debugger counters show one workspace serialization and no planner/OOS insert calls. Ordinary CSQL INSERT is unaffected; standalone execution itself does not determine whether OOS demotion occurs. A preceding experiment with `INSERT_MODE(0)` as a hint still took the query-executor path, so that hint run is not evidence of workspace-path behavior.

## Feedback loop

Run from the source worktree with its matching installed binaries:

```sh
direnv exec . python3 .scratch/cbrd27424/repro.py --matrix
direnv exec . python3 .scratch/cbrd27424/repro.py
direnv exec . python3 .scratch/cbrd27424/repro.py --size 16
```

The first command exits 1 in 18.06 seconds, reporting only `load_sa` as failing among the four ordinary routes. The second repeats the standalone failure in 7.58 seconds. The 16-byte negative control exits 0 in 7.79 seconds: its value is intact and no OOS storage is expected or observed. The fixture has no index, object reference, second attribute, second row, or special loader option; the large eligible value and SA object-loading route are sufficient.

These are personal local reproduction commands, not organization build instructions. The harness requires Python with `Random.randbytes`, the installed `cubrid`/`csql` on PATH, and this revision's `;oos_stats` extension. It owns a private registry/configuration/port under `.scratch/cbrd27424/runtime`, serializes SA and CS access, and stops the database server it starts. It retains fixtures and command output for investigation. Its size switch is intended for the demonstrated 16-byte control and 5,000-byte failure, not threshold-boundary certification.

## Discriminating debugger evidence

GDB command file: `.scratch/cbrd27424/trace.gdb`. Launch with `gdb -nx` and debuginfod disabled. Use `cub_admin loaddb` to debug the utility process directly; debugging the `cubrid` launcher without following its child misses the actual loader.

| Probe | SA object loader | Ordinary CSQL SA INSERT | CSQL SA with `insert_execution_mode=0` |
|---|---:|---:|---:|
| `tf_mem_to_disk` | 1 | 0 | 1 |
| `heap_attrinfo_determine_disk_layout` | 0 | 1 | 0 |
| `oos_insert_many` | 0 | 1 | 0 |
| `heap_insert_logical` | 1 | 1 | 1, for OID reservation |

Loader stack:

```text
ldr_flush
  ws_intern_instances
    locator_flush_all_instances
      locator_mflush -> locator_mem_to_disk -> tf_mem_to_disk
      locator_mflush_force -> locator_force -> xlocator_force
        locator_insert_force -> heap_insert_logical
```

Ordinary CSQL SA INSERT stack:

```text
qexec_execute_insert
  locator_attribute_info_force
    locator_allocate_copy_area_by_attr_info
      heap_attrinfo_transform_to_disk
        heap_attrinfo_transform_to_disk_internal
          heap_attrinfo_determine_disk_layout
          oos_insert_many (through OOS helpers)
    locator_insert_force -> heap_insert_logical
```

The ranked hypotheses were missing transformation, planner rejection of the loader representation, and post-insert loss of OOS chains. The first is confirmed: the planner is never called by the failing route. This rules out the latter two for the minimal case. The existing research report's source explanation is now backed by a runtime reproduction on the destination revision.

## Agreed repair scope

The user selected option A for both decisions on 2026-09-11:

1. Keep the fix independent on `f4299ac0c`, using existing OOS interfaces, and separately verify compatibility with PR #7695.
2. Repair the shared **standalone workspace write route**, covering both SA loaddb and CSQL workspace writes.

Proposed implementation constraints:

- Reuse the existing OOS attribute transformer for incoming workspace records; do not implement a second demotion policy in the workspace serializer.
- Explicitly identify the workspace-force caller so already-transformed SQL/server-loader/replication records are not demoted again. Exclude schema records.
- Perform transformation after the actual partition class and heap are selected. OOS ownership must belong to that heap; creating chains on a partition root before pruning is incorrect.
- Cover force INSERT and force UPDATE of an already-reserved OID. Preserve incoming object references, representation, and cache-coherency metadata.
- Enclose transformation and heap/index writes in the existing `xlocator_force` top operation, including per-object error-filter top operations. An OOS side effect outside that scope would survive a later failure incorrectly.
- Preserve external LOB locator semantics when decoding/re-encoding a record; do not copy an already-materialized LOB a second time.
- Keep transformation buffers local and explicitly release them on all success/error paths. Do not overwrite caller copy-area storage with a longer record.
- Preserve no-logging support. Its documented recovery exception is not a promise of rollback after a failed no-logging load. Do not introduce stale-reference retries that rely on identity uniqueness when logging is off.

The normative context is dated 2026-09-09 and specifies the accepted 24-byte identity-stamp layout and four-record physical target. This base still has the 16-byte stub and historical quarter-page planner gate. Those are existing conformance gaps; this loader diagnosis neither changes the specification nor silently imports their separate fixes. The 5,000-byte fixture avoids depending on either boundary difference.

## Implementation and verification

The original engine passed **27/27 configured CTest tests** before changes. The final GCC debug build and configured CTest suite pass **28/28 tests in 176.16 seconds**, including the new CLI regression in 62.86 seconds. The retained CLI regression first failed on the original loader with exact value equality but zero physical OOS chunks (`regression-red.log`).

### Implemented boundary

`locator_demote_workspace_record` decodes an incoming SA workspace record and calls the existing heap attribute transformer with `LOB_FLAG_EXCLUDE_LOB`. It skips schema records, already-transformed records, and classes with no variable attributes. If no OOS attribute is selected, it retains the original workspace bytes. If demotion occurs, it preserves the incoming CHN and uses a separately owned copyarea through the heap/index force operation.

The workspace caller is identified explicitly at force INSERT, force UPDATE (including reserved OIDs), and multi-row UPDATE. Partition movement forwards that identity to the destination insertion. Demotion runs after partition selection and inside the existing caller top operation; both ordinary transaction rollback and per-object filtered errors undo its OOS side effects. Each exit releases the temporary copyarea. SERVER-mode behavior remains unchanged, and no OOS disk layout or planner policy is changed.

### Retained regression

`unit_tests/oos/scripts/test_workspace_oos.py` is registered as `test_oos_workspace_cli` in the OOS CTest suite. It creates a private registry and disposable database, fixes the database page size to 16 KiB, uses deterministic VARBIT values, and checks exact reads plus live physical OOS chunk counts.

Covered cases:

- Standalone object loading and CSQL workspace INSERT through reserved OIDs.
- Forward/backward object references and partition-local OOS ownership.
- Flushed INSERT rollback; triggered workspace multi-row UPDATE rollback, commit, and DELETE cleanup.
- Whole-load unique-index failure rollback, plus filtered duplicate-key continuation without an orphan chain.
- Null, empty and small inline values; FORCE_OUTLINE; largest-first selection; a 50,000-byte four-chunk value.
- Workspace partition movement, existing external BLOB/CLOB preservation across demotion and rollback, and successful no-logging load/read.

The original four-mode diagnostic passes in **17.48 seconds** after the fix: SA loader, ordinary SA INSERT, ordinary CS INSERT, and CS loader each store one live OOS chunk and return the exact input value (`matrix-final.log`).

The same patch applies cleanly to PR #7695 head `eaf1165bbc76d5f22b6ff34f08ccd8deca0c11b4`. An isolated worktree at `/home/vimkim/gh/cb/CBRD-27424-compat-7695` was built and installed with GCC debug. Its complete CLI regression passes all 12 scenarios, including no-logging, with newly created databases using that revision's identity-stamp layout (`compat-regression-final.log`). The added/deleted source lines and regression file are identical on both revisions. This verifies compilation and focused runtime compatibility; it does not claim the full #7695 test suite or CI was run.

### Separate baseline LOB defect

Creating fresh BLOB/CLOB values with `insert_execution_mode=0` leaves a locator pointing to a missing external file after commit. This was reproduced on both the patched build and the independent unmodified `f4299ac0c` build (`oos-baseline-f4299ac0c`); a 16-byte inline VARBIT control also fails, without any OOS demotion. Evidence: `lob-baseline.log`, `lob-control.log`, and the first `regression-final.log` attempt. This is not attributed to the OOS patch and is not repaired here.

The retained LOB regression seeds permanent locators through ordinary query-executor INSERT, then triggers workspace UPDATE to demote the other attribute. It verifies exact LOB reads and identical file names and bytes before/after rollback and commit. This proves existing LOB ownership preservation; it does not claim fresh workspace LOB creation is repaired.

### Review and formatting

**Standards:** no documented standards violations. The reviewer noted optional duplication in the OOS-statistics regex assertions; this is not a correctness blocker.

**Spec:** no concrete engine defect. The review requested external LOB, filtered-error continuation, and PR #7695 compatibility evidence. All three now have passing runtime evidence. The final test review found no concrete defect. The LOB coverage preserves inline external locators while another attribute demotes; it does not claim exhaustive coverage of OOS-demoted LOB locators.

GNU indent initially moved an adjacent multiline declaration across a new `INDENT-OFF` guard in a scratch copy. A blank separator prevents that formatter bug. New lines were aligned with GNU indent; existing indentation was preserved. Both changed engine files now match formatter output exactly. No temporary engine instrumentation was added.

## Evidence locations

All paths below are relative to the source worktree:

- `.scratch/cbrd27424/repro.py`: runnable physical-storage and logical-value oracle.
- `.scratch/cbrd27424/runtime/trace_load_sa.out`: confirmed loader stacks and counters.
- `.scratch/cbrd27424/runtime/trace_sql_normal.out`: ordinary CSQL SA stacks and counters.
- `.scratch/cbrd27424/runtime/trace_sql_workspace_param.out`: actual CSQL workspace route.
- `.scratch/cbrd27424/runtime/edges_refs_verify.out`: forward/backward reference baseline.
- `.scratch/cbrd27424/runtime/edges_parts_verify.out`: partition baseline.
- `.scratch/cbrd27424/runtime/nolog_verify.out`: no-logging baseline.
- `.scratch/cbrd27424/runtime/extra_equality.out`: post-commit exact value checks for CSQL workspace INSERT and both partitioned rows.
- `.scratch/cbrd27424/baseline-build-test.log`: passing configured test-suite baseline, 27/27.

The earlier static/history analysis remains at `/home/vimkim/gh/cb/oos-no-loaddb/docs/research/CBRD-26950-loaddb-oos-bypass_eaf1165_codex.md`. Do not delete that worktree while relying on its uncommitted report.

## Final verification artifacts

- `.scratch/cbrd27424/regression-red.log`: retained CLI regression failing before the patch.
- `.scratch/cbrd27424/build-test-final.log`: final configured build/test run.
- `.scratch/cbrd27424/matrix-final.log`: all four ordinary modes green.
- `.scratch/cbrd27424/compat-bootstrap.log` and `compat-build-final.log`: independent build on PR #7695 head.
- `.scratch/cbrd27424/compat-regression-final.log`: all 12 focused compatibility scenarios green.
- `.scratch/cbrd27424/lob-existing.log`: existing BLOB/CLOB file ownership preserved.
- `.scratch/cbrd27424/lob-baseline.log` and `lob-control.log`: separate fresh-workspace-LOB failure on original source and inline control.
- `.scratch/cbrd27424/repro_fresh_workspace_lob.py`: isolated reproduction for the separate LOB defect; run against either build's environment.

Diagnostic scripts/logs remain in the clearly marked scratch directory. The original handoff and research worktree were preserved. No commits, pushes, PR publication, or JIRA updates were performed.
