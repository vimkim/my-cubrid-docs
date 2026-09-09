# Ticket 01 — routing characterization and shared selection

Date: 2026-09-08. Work-tracker: 74. Scope: [ticket 01](../../.scratch/pr7600-effective-key-routing/issues/01-characterize-and-share-routing.md) only.

Status: completed. The pinned implementation and final prefactor both pass the same 43 checks. No effective-key production path was introduced.

## What changed

The engine change is a private extraction in [partition.c](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/query/partition.c:3475). Expression evaluation, NULL comparison selection, partition matching, exactly-one-match validation, and destination lookup now live in `partition_find_partition_for_expr`. The existing record adapter calls that helper; neither the inline probe/rebuild nor any effective-key production path was replaced.

The record adapter retains attribute-cache initialization, record decoding under the root representation, restoration of the original representation after decoding, destination OID/HFID publication, the destination representation patch, and value cleanup. INSERT/UPDATE wrappers retain root discovery, explicit-partition checks, superclass reporting, and context ownership. No storage, locator, executor, public-header, OOS policy, or on-disk-format changes were made. See [record adapter](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/query/partition.c:3551), [INSERT wrapper](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/query/partition.c:3641), and [UPDATE wrapper](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/query/partition.c:3748).

Five characterization tests extend the existing [SQL/SHOW OOS suite](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/unit_tests/oos/sql/test_oos_sql_show.cpp:482). Its CTest timeout is now 120 seconds because deliberate rejection cases can collect expensive diagnostic stacks in debug builds. Other test timeouts are unchanged. No internal testing interface, mock, or production instrumentation was added.

## Seam and ownership contract

The tested seam is the already approved SQL execution plus SHOW OOS inspection interface. Tests assert independently specified logical values, physical partition placement, statement error codes, transaction outcomes, and owner-file record counts. The 64-byte uncompressed FORCE_OUTLINE payload has one OOS chunk record per stored row, allowing exact counts independently of ordinary demotion thresholds.

The extracted helper is private, not a new public effective-key interface:

- Input: a loaded pruning context with a bound, readable partition-key value, the existing evaluation instance OID, and the existing class/thread context.
- Result: one borrowed `OR_PARTITION` belonging to that context, written only on success and consumed before context cleanup.
- Evaluation may populate expression caches. The helper does not transfer value ownership, decode a record, patch a record header, validate an explicitly named partition, or clear caller-owned values.
- No second interpretation of expression, range/list/hash, NULL, or match-count semantics was introduced. A later effective-key adapter must reuse this selection logic and meet its binding/lifetime contract; that adapter is **not implemented here**.

### Context reuse: the exact claim

Alternating rows in a multirow INSERT use the statement's routing context; the valid-then-invalid list batch reaches a routing error after successfully routing an earlier row. The subsequent valid statement demonstrates recovery after failure, **not continued operation on the same live context after failure**. The existing INSERT/UPDATE wrappers clear the context on error. Continuing with a cleared context as though it were still loaded is not the retained contract.

The lifetime argument combines these SQL outcomes with unchanged source ownership: `fetch_peek_dbval` caches pointers into attribute-value slots; clearing DB values clears their contents without freeing those slots; ordinary successful reuse reads the next row into the same owned slots. On context destruction, the partition predicate is released before the attribute cache. This extraction introduces no temporary key pointer into that structure. See [fetch caching](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/query/fetch.c:4002), [value clearing](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/storage/heap_file.c:10320), and [context destruction](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/query/partition.c:2808).

## Reference observations

All rows below passed against the pinned engine before extraction and the final extracted version.

| Case | Independently specified observation |
|---|---|
| RANGE(id), boundary 10 | Keys `9,NULL` and their distinct payloads are in p0; `10,11` are in p1. Root has no OOS file; child OOS counts are 2/2. |
| LIST(ABS(id)) | Keys `-1,-3` belong to the list `(1,3)`; `-2,NULL` belong to `(2,NULL)`. The expression result, not the negative raw key, selects the list. |
| Failed list batch | A valid `-1` row followed by missing key `4` returns `ER_PARTITION_NOT_EXIST` (-891). After rollback the original four payloads and 2/2 ownership survive. A later `-2` insert succeeds, giving child counts 2/3. |
| HASH(id), two partitions | Literal keys `0,NULL` are in p0; two distinct rows with key `1` are in p1; counts 2/2. Tests use fixed examples, not a second implementation of the hash algorithm. |
| RANGE(id+1), boundaries 10/20 | Key 8 fits p0; key 9 fits p1. A direct p0 INSERT succeeds for 8. Key 19 has no destination on INSERT or UPDATE, returning -891. |
| Explicit-partition validation | Direct p0 INSERT with key 9 and direct p0 UPDATE from 8 to 9 return `ER_INVALID_DATA_FOR_PARTITION` (-1109). Rollback preserves the original payloads and child counts 1/1. |
| Root-targeted UPDATE | Updating both keys by +1 moves the former p0 row to p1 and retains the sibling row's payload. p0 is empty with an existing, empty OOS file; p1 has both rows/two OOS records; root still has no OOS file. |
| LIST without NULL member | NULL INSERT returns -891, stores no row, and creates no OOS file for root or either child. A subsequent key 2 INSERT succeeds under p1 only. |

Documented SQL expectations came from the local manual, checkout `3b6ae97b`: [range/NULL rules](/home/vimkim/gh/cubrid-manual/en/sql/partition.rst:117), [hash/NULL rules](/home/vimkim/gh/cubrid-manual/en/sql/partition.rst:145), [list/NULL rules](/home/vimkim/gh/cubrid-manual/en/sql/partition.rst:185), and [direct-partition validation](/home/vimkim/gh/cubrid-manual/en/sql/partition.rst:315). Runtime ownership and pinned hash destinations are established by the actual SQL assertions, not by extrapolating the manual.

## Build, fixture, and evidence

Source baseline: `b871ea386d2c5419b7abae07dda58b9b7f36377a`. The final candidate is that HEAD plus the uncommitted three-file engine/test diff. Every JSON report records the actual HEAD, complete `src`/`unit_tests` diff, source status, CCI submodule revision, test-binary and installed SA-library SHA-256, CMake-cache SHA-256, command, exit code, and output. The pre-existing different CCI submodule revision was preserved and recorded rather than silently reset. The original engine source was unchanged during baseline characterization.

Build: `debug_gcc`, using the worktree's personal `direnv exec . just build` workflow. The full build compiled/linked both SA and server targets. These are **SA SQL execution results**, not server MVCC, vacuum, crash-recovery, sanitizer, or performance results.

Each invocation of [run-isolated.py](ticket01-evidence/run-isolated.py) creates a fresh private database directory and copied configuration, runs the existing fixture setup and test binary, and retains that directory, logs, and GTest XML. Candidate and reference therefore do not share a mutable attribute cache, OOS file, or database. No network server is started. Shared/default databases were not touched. Retained temporary paths are listed in each JSON; none were deleted.

Safety deviation: the unqualified `just build-test` recipe was not run. Its CTest fixture embeds shared CUBRID/config/database paths at configure time and its cleanup calls `deletedb`; environment overrides alone do not isolate those embedded paths. Verification ran the same selected test executables with private fixtures instead. No fixture-rewrite or broader test-runner redesign was included in this engine ticket. See [fixture commands](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/unit_tests/oos/CMakeLists.txt:65).

| Suite | Baseline | First prefactor | Final candidate |
|---|---|---|---|
| SHOW + routing | [10/10](ticket01-evidence/baseline-complete.json) | [10/10](ticket01-evidence/after-complete.json) | [10/10](ticket01-evidence/final-complete.json) |
| Storage policies | [25/25](ticket01-evidence/baseline-final-storage.json) | [25/25](ticket01-evidence/after-storage.json) | [25/25](ticket01-evidence/final-storage.json) |
| Transactions | [8/8](ticket01-evidence/baseline-final-txn.json) | [8/8](ticket01-evidence/after-txn.json) | [8/8](ticket01-evidence/final-txn.json) |

This is test-first **characterization followed by behavior-preserving refactoring**, not a new-behavior red/green claim. No baseline functional failures were encountered; expected negative SQL results are explicit passing assertions. Earlier incremental `baseline-range/list/hash/validation` evidence is retained. Test durations are diagnostic only; these runs are not paired performance measurements.

## Standards

Independent review initially identified one low-severity convention discrepancy: the new helper did not put `THREAD_ENTRY *` first, as required by `src/query/AGENTS.md`. It now does, receives the same `pinfo->thread_p` as before, and uses that value for evaluation. The reviewer confirmed closure. No outstanding standards findings or actionable heuristic smells.

## Spec

Independent review found no implementation defects or unauthorized scope expansion. It required explicit documentation of context destruction on failure versus reuse after failure, and completed before/after evidence. Both are now recorded above. Broader key coverage and the effective-key adapter are later-ticket obligations, not implemented behavior here.

Review summary: standards — 0 outstanding findings; specification — 0 implementation findings, verification complete. Reviews used the uncommitted diff against the pinned HEAD because no commit was authorized or created. `git diff --check` passes. Parent-spec SHA-256 remains `dfa82a53337a2cf85c9d18bfe3707d99670a6e7070320a97fc3183b50c01f31f`.

## Remaining design obligations

Ticket 02 still needs to prove stored-value-equivalent temporary keys across all legal types, defaults, domain conversion, CHAR padding/collation, representations, and expression bindings, and add correct first-pass destination-aware serialization. Later tickets cover UPDATE/INCR/DECR, LOB/error cleanup, server lifecycle, and measured benefit. Those are not waived by this baseline.

The private extraction is preparation for that work, not a demonstrated optimization. The whole inline probe, second serialization when OOS demotion occurs, and downstream record routing remain in place. No performance benefit or complete effective-key correctness is claimed. Parent spec unchanged; no commit, push, or ticket-02 implementation performed.
