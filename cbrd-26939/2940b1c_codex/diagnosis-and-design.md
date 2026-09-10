# CBRD-26939: CDC/OOS diagnosis and proposed design

Date: 2026-09-08. Engine: `2940b1cfbc3c2d4d0fac3f9244a960350debd380`. Work item: **70**.
Status update: round 1 accepted durable supplemental images, new-history guarantees with explicit errors for unreconstructible legacy OOS history, and separate bug_bts_4633 diagnosis. Current decisions: [ADR-0004](../../../cubrid-oos-context/docs/adr/0004-durable-oos-supplemental-images.md). Architecture Q1–Q9, including failure handling, reader restrictions and offline activation/fresh-database policy, is now confirmed. The concrete specification, test seams and six-ticket breakdown are drafted in the local tracker for review. The proposal and pending questions below preserve the pre-interview diagnosis snapshot. DELETE failure is reproduced and vacuum dependency experimentally confirmed. No engine changes, commits, pushes, or CI comments made.

## Finding

CDC can read a valid retained WAL image whose OOS payload has already been reclaimed. Disabling vacuum makes the reduced failing workload pass; restoring vacuum makes it fail again. Current supplemental logging preserves physical OOS references, whereas asynchronous CDC materialization uses live OOS storage. This is the lifetime gap described by [CBRD-26939](http://jira.cubrid.org/browse/CBRD-26939), verified on this PR head with a local reproduction.

The scope is more precise than “the remaining two tests are CDC”: [GHA run 34186373809](https://github.com/CUBRID/cubrid/actions/runs/34186373809) fails `cbrd_27064` and `bug_bts_4633`. The latter is a distinct observed crash and has not been locally reproduced or attributed. `cbrd_27075` was in earlier failure lists but is absent from this latest list; that does not prove its underlying CDC risk is fixed.

## Evidence identity

- PR [6864](https://github.com/CUBRID/cubrid/pull/6864), `feat/oos`, matches the worktree SHA above.
- GHA collect job `101943866056` verifies engine SHA and testcase SHA `01af62db73351ea3fdb445ccd03a19c39084d1cc` across all 50 shards. Its workflow SHA `69c3094` is not the engine SHA.
- Local install reports `11.5.0.2634-2940b1c`, debug, built September 4. Copied privately from `/home/vimkim/.cub/install/oos-storage/debug_gcc`.
- Testcase checkout `/home/vimkim/gh/tc/cubrid-testcases-private-ex-tc-pr-6864` is clean at the tested testcase SHA.
- Normative OOS context: `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md`, last updated August 28. Live JIRA lookup reports Open/Unresolved; design is explicitly TBD. Its prior analysis used `725a32c` and did not contain a local reproduction.

## Current failures

| Test | Current GHA symptom | Assessment |
|---|---|---|
| `cbrd_27064` | INSERT passes; DELETE 16/700; UPDATE 3/2400; extraction `rc=-10`; corruption count 0 | OOS/CDC failure reproduced locally; vacuum dependency confirmed |
| `bug_bts_4633` | Script prints OK, but CTP detects a `cub_server` core in `log_get_undo_record`, reached through `heap_get_visible_version_from_log` and heap scan | JDBC concurrency with integer-only tables; separate MVCC undo-read crash path, root cause unresolved |

The raw GHA XML and extracted failure text are retained in this directory. The `bug_bts_4633` core summary is the reason its script-level OK is not a pass. It cannot be dismissed as a cleanup error or attributed to CDC from this evidence.

## Reproduction and minimization

Initial full testcase run used copied fixtures, loopback as the private host address, and retained diagnostic files. It exited 1, INSERT passed, DELETE returned rc=-10 with 0/700 extracted. Server failures contaminated subsequent UPDATE execution, so that result is not an independent UPDATE reproduction. CTP core processing made this original run take about 225 seconds. The extracted DELETE stack was saved before CTP cleanup removed the core files.

Reduced scenario: one 16,000-byte uncompressed VARBIT source value; insert target rows before the CDC start point; establish CDC with `all_in_cond=1`; delete target rows; release the extractor to drain its backlog. Fresh database for each run, 4KB data/log pages, supplemental logging enabled, log compression disabled, large archive limit. Original shell-driven autocommit behavior is retained. No UPDATE phase, unrelated INSERT extraction phase, or payload-size sweep remains.

| Variant | Result |
|---|---|
| DELETE only, original size sweep, 700 rows | RED, 56/700, rc=-10 |
| Single size, 700 rows | RED, 18/700, rc=-10 |
| Single size, 50 rows | RED, 11/50, rc=-10 |
| 1, 10, 25, 40, 49 rows, separate runs | GREEN |
| 50 rows, repeat | RED, 14/50, rc=-10 |
| 50 rows, vacuum disabled | GREEN, 50/50, rc=0 |
| 50 rows, vacuum restored | RED, 10/50, rc=-10 |

All reported corruption counts are zero. Fifty is the smallest failing row count observed in this setup; this is not a portable engine threshold. Successful extracted counts vary with scheduling. The reduced run completes in tens of seconds, with existing sleeps and connection-error handling still contributing to latency. It is a useful repeatable loop, but further deterministic synchronization and runtime reduction would improve the regression test. Payload bytes originate from urandom; a fixed byte fixture is still needed for exact-value regression coverage.

Executed commands (use a fresh final label for another attempt):

```bash
REPRO_ROWS=50 REPRO_VACUUM_DISABLE=yes bash /home/vimkim/.cache/codex/cbrd-26939-2940b1c/enter.sh no-vacuum-50
REPRO_ROWS=50 REPRO_VACUUM_DISABLE=no bash /home/vimkim/.cache/codex/cbrd-26939-2940b1c/enter.sh vacuum-restored-50
```

Restored-vacuum output:

```text
EXTRACT_ERROR: rc=-10 target=10
TARGET_COUNT: 10/50 type=2
EXTRACTOR_RC=1 (124=hang/timeout)
CORRUPTION=0  TARGET_COUNT=10/50
```

The runner uses user/mount/PID/IPC/network namespaces, private `/tmp` to hide Unix sockets, loopback-only name resolution, a private install/database registry/CTP copy, and namespace teardown for cleanup. This addresses the documented prior incident where a local test stopped the user's host master. Do not replace it with an unisolated CTP invocation. The saved scripts depend on the private installation path; they are diagnosis artifacts, not a portable checked-in regression test.

## Hypotheses and discrimination

1. Vacuum reclaims the payload before CDC materializes it. Prediction: disabling vacuum turns the same workload green. **Observed**, with failure returning after restoration.
2. CDC reconstructs an incorrect OOS stub from WAL independent of reclamation. Prediction: failure persists without vacuum. **Not observed** in the control; de-prioritized rather than universally disproven.
3. OOS writes corrupt live chains independently of CDC. Prediction: ordinary pre-delete reads also fail, including without vacuum. Not independently probed; control and the crash path make it less likely as the primary explanation here.

## Source chain at this commit

- `heap_delete_logical`, `src/storage/heap_file.c:24832`: emits the supplemental DML record referencing `supp_undo_lsa`.
- `heap_delete_home`, `src/storage/heap_file.c:23270`: writes a supplemental copy of the built heap recdes for the MVCC home path.
- `log_append_supplemental_undo_record`, `src/transaction/log_manager.c:4999`: copies record type and raw bytes. It does not expand OOS values.
- `cdc_get_recdes`, `src/transaction/log_manager.c:11414`: reconstructs the record from the referenced WAL entry.
- `cdc_make_dml_loginfo`, `src/transaction/log_manager.c:13040`: passes the undo recdes into `heap_attrinfo_read_dbvalues`.
- `heap_attrvalue_read_oos_inline`, `src/storage/heap_file.c:10487`: resolves the OOS stub using storage.
- Saved local stack: `cdc_make_dml_loginfo(CDC_DELETE)` → attribute reading → `oos_read` → `oos_read_within_page` → `pgbuf_fix_debug(OLD_PAGE)` at `page_buffer.c:2487`. That assertion is in the `PAGE_UNKNOWN`/deallocated-page branch. This is source-plus-core evidence, not a newly traced per-OID delete/read timeline.
- `vacuum_heap_oos_delete_within_sysop`, `src/query/vacuum_oos.cpp:464`: extracts OOS OIDs from vacuumed records and deletes their chains. UPDATE history additionally has the forward-walk path.
- `cdc_min_log_pageid_to_keep`, `src/transaction/log_manager.c:14166`, and `log_page_buffer.c:6114`: consumer start LSA constrains archive deletion. This does not pin OOS values.
- `flashback.c:952` and `:962`: flashback shares `cdc_get_recdes` and `cdc_make_dml_loginfo`. Flashback impact is source-based; not yet reproduced here.

## Proposed architecture — NOT an accepted ADR

Required invariant: every supported CDC/flashback before/after image is materializable from retained history after heap/OOS vacuum, without touching reclaimed or ambiguously reused OOS slots. Missing data must never be silently skipped or substituted with NULL.

**Recommend durable expanded images in supplemental logging, only where OOS-backed images require them.** Preserve physical recovery undo/redo and its OOS stubs. Keep vacuum reclamation independent of consumer delay.

| Design | Benefit | Cost/constraint |
|---|---|---|
| Durable supplemental images (recommended) | Historical extraction reads WAL; normal OOS reclamation proceeds; supports disconnected consumers within retained history | Extra serialization, memory, and WAL bytes for eligible images; encoding/reader compatibility and error propagation need explicit design |
| Retain OOS chains | Potentially avoids duplicate payload logging | Must persist and recover a safe horizon, include flashback and disconnected consumers, and define space bounds; current OOS reclaim design becomes consumer-dependent |
| Hybrid | Can trade WAL against retained OOS space | Requires both lifetime protocols and crash-safe transitions; disproportionate complexity for the first implementation |

Implementation shape to review:

1. Give the record-expansion module an owned-copy operation usable by supplemental logging. Reuse its VOT/value reconstruction logic, currently concentrated in `heap_oos.cpp`; callers should not reconstruct attributes individually or mutate the recovery image. The current public helper takes `HEAP_GET_CONTEXT`, so ownership and buffer allocation need deliberate adaptation.
2. Capture the before image while the old value is protected and before destructive/eager cleanup; capture the after image before it can become reclaimable. Cover INSERT, UPDATE, DELETE, triggers, relocation, partition-related logical paths, and applicable SA/non-MVCC behavior.
3. Publish image LSAs and the associated DML supplemental record only through a checked operation. Propagate expansion/allocation/append errors so a transaction cannot report success with incomplete required history. Audit current ignored return values and the void supplemental append helper.
4. Let `cdc_get_recdes` decode the new self-contained image for both undo and redo, shared by CDC and flashback. The existing undo branch handles supplemental raw records; the redo switch currently lacks the equivalent entry. Merely changing the writer is insufficient.
5. Decide whether to extend the existing raw supplemental image representation or add an explicit image kind/version. Do not claim backward reader compatibility merely because the byte payload looks like a recdes. Existing enum values must stay stable.
6. Define a checked policy for historical OOS stubs without durable images. Matching OID and length does not prove identity after slot reuse. Removing assertions alone would prevent some crashes but would not restore missing values or prevent silent wrong-value extraction.

The lower bound on extra uncompressed payload bytes is approximately the captured OOS payload per image: one image for INSERT/DELETE, two for UPDATE when both sides are OOS-backed. Whole expanded-record storage also includes other columns and headers. This is an estimate, not a measured benchmark. Existing supplemental compression may reduce it; tests deliberately use incompressible VARBIT. No extra supplemental images should be emitted when supplemental logging is disabled.

## Decisions awaiting the user

1. Should this effort also diagnose/fix the currently failing `bug_bts_4633`, or focus on CDC/OOS and retain `cbrd_27075` as regression coverage? Asked after discovering the current GHA failure set.
2. Must the fixed engine consume OOS history written before the fix, or may supported history start at an upgrade cutoff? Recommendation: durable new images plus explicit failure for old images that cannot be safely reconstructed. Historical support would require a separate WAL-based reconstruction investigation; reading whatever occupies an old OOS OID is not acceptable.

These are product/compatibility decisions, not permission requirements from a skill. The proposal remains unaccepted until settled.

## Acceptance tests for implementation

- Convert the reduced loop into a deterministic fixture and verify byte-identical before/after payloads and exact DML identities/counts; counts alone are insufficient.
- Run delayed extraction after confirmed vacuum on fresh DBs; ensure the extracted records carry no live OOS dependency.
- Independently cover INSERT followed by later UPDATE/DELETE, UPDATE, DELETE, `all_in_cond=0/1`, single/multiple OOS attributes, and multi-chunk values.
- Exercise 4KB, 8KB, 16KB pages, log compression on/off, archive rollover, restart/recovery, rollback, triggers and shared flashback decoding.
- Check supplemental-off behavior and measure WAL/memory/runtime overhead.
- Run full original `cbrd_27064` and historical `cbrd_27075` in isolation; local debug and appropriate broader tests. New CI verification requires the eventual updated engine commit.
- Investigate `bug_bts_4633` independently if included in scope. Passing CDC tests cannot close that failure.

No source instrumentation was added. Existing user work and submodule differences remain untouched. No engine fix has been implemented or verified yet.
