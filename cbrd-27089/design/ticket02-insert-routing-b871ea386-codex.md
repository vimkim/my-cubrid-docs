# Ticket 02 — effective-key INSERT routing

Date: 2026-09-08. Work-tracker: 75. Scope: [ticket 02](../../.scratch/pr7600-effective-key-routing/issues/02-route-partitioned-inserts.md), authorized after ticket 01. No commits or pushes. This is an INSERT milestone, not acceptance of the whole replacement.

Status: completed. Final formatting-only rebuild/rerun passed; `git diff --check` passes.

## Outcome

Partitioned INSERTs through `locator_attribute_info_force` now route from an owned effective key and perform a normal first-pass full-row transformation with the selected OOS owner. UPDATE retains the existing inline probe/rebuild. Final record routing, explicit-partition validation, representation patching, locks, index maintenance, and scan-cache selection remain.

The final routed class is checked against the early OOS owner **before** subclass locking or heap/index insertion. Disagreement returns an error through the ordinary statement failure path; already-written OOS chains are not redirected or manually deleted. Transactional rollback retains ownership of persistent cleanup.

Verification: 57 passing SA checks across SHOW/routing (20), storage (25), transactions (8), and OOS/bigone (4), plus two independently executed SQL reference comparisons. No runtime or allocation improvement is claimed. Server lifecycle, broader fault injection, UPDATE migration, and measurements remain later tickets.

## Implementation contracts

| Boundary | Contract and source |
|---|---|
| Owned effective key | [heap_attrinfo_get_insert_key](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/storage/heap_file.c:12113) locates the key by attribute ID. For an omitted key it invokes the existing default reader on a copied slot; otherwise it clones the assigned value. Neither operation initializes the original assignments. INSERT requires no pending `do_increment`; UPDATE is not routed through this helper. |
| Stored-value normalization | The primitive column-domain size/write/read methods run on that owned copy. Their scalar serialization is not a row image or fabricated partial record. This retains CHAR padding, string compression, codeset/collation, integer, and temporal encoding semantics. The reader produces an owned value. Scratch/allocation and intermediate values are cleared on success and error. There is no type-specific probe fallback. |
| Routing lifetime | [partition_prune_insert_by_attrinfo](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/query/partition.c:3795) uses the existing one-column context cache. Expression bindings point into its stable value slot, never a temporary stack value. The slot contents are cleared before return; the slot allocation survives successful context reuse. Existing wrappers destroy contexts on error; tests do not claim reuse of a destroyed context. |
| Shared selector | The effective-key adapter and record adapter share ticket 01's expression/matching selector and INSERT context/explicit-partition validation. The record adapter still decodes under the root representation and patches the destination representation. |
| First-pass destination | [heap_attrinfo_transform_to_disk_with_oos_owner](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/storage/heap_file.c:12903) supplies the destination owner while retaining the source cache's class identity and normal first-pass preparation. It does not use the second-pass “increments already applied” flag. |
| Final agreement | [locator_insert_force_internal](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/transaction/locator_sr.c:4996) checks the expected class after final routing and before insertion. Existing public force/copy-area interfaces delegate without new expectations, preserving other callers. |

Key-only preparation contains no LOB copy/delete, OOS insertion, or OOS publication reset. This is a source-level contract: the selected key types are the schema-validated integer/temporal/CHAR/VARCHAR types, and only their primitive codecs run. Unrelated LOB assignments are left to real row preparation. Broader LOB side-effect and failure-injection verification belongs to ticket 04; it is not inferred from SA row equality.

Dynamic defaults and auto-increment values are consumed after executor evaluation/assignment. The new helper does not re-evaluate a default expression or allocate another serial value. Omitted representation defaults use the existing representation reader. The source cache is not retargeted to the destination class merely to write OOS chains.

## What the tests establish

The approved seams are SQL execution plus SHOW OOS, and the single supporting effective-key routing interface. The latter uses independently owned candidate/reference attribute caches. The reference probe is allowed to initialize its own values; it never shares the candidate's mutable input.

| Coverage | Decisive observation |
|---|---|
| All 13 legal key types | SMALLINT, INTEGER, BIGINT, DATE, TIME, TIMESTAMP/TIMESTAMPTZ/TIMESTAMPLTZ, DATETIME/DATETIMETZ/DATETIMELTZ, CHAR, VARCHAR. The focused default test uses exact LIST literals plus a separate NULL partition, avoiding a two-bucket hash collision as its sole oracle. Candidate/reference destination OID and HFID agree, and source assignments remain uninitialized. |
| Assigned CHAR | Catalog attribute ID identifies the key despite physical cache ordering. Assigned value bytes, size, and state remain unchanged. Padded CHAR routing agrees with an independent record probe. |
| SQL values and HASH | Assigned, omitted, and NULL rows for every legal key type retain expected stored values and per-child owner counts. A separate pinned-engine SQL batch reproduces the same observations. |
| RANGE/LIST/HASH expressions | Existing `id+1`, `ABS(id)`, boundary/NULL cases remain; nested `LOWER(SUBSTRING(id,1,1))` and compressed `CHAR_LENGTH(id)` exercise string expression evaluation. Multirow alternating destinations expose stale-value bindings. These are representative expression families, not an enumeration of infinitely many SQL expressions. General support comes from retaining the existing binder/evaluator. |
| Dynamic/generated/coerced values | CURRENT_DATE default equals an explicit same-statement expected date, avoiding a midnight comparison race. AUTO_INCREMENT(9,1) crosses the p0/p1 boundary once; string `'11'` converts into the integer key. |
| Explicit collation | `utf8_en_ci` routes `BETA`, `AlPhA`, and `beta` to their case-insensitive LIST destinations, with owner counts 1/2. |
| OOS-backed key and multiple values | A FORCE_OUTLINE string key, 64-byte forced VARBIT, and ordinary 6,000-byte uncompressed VARBIT yield three OOS chunk records in each owning child and none in the root. Logical key and payload equality are independently asserted. |
| Compressed key | 2,999/3,000-character VARCHAR values route by decoded character length, round-trip intact, and retain two chunk records per child including the payload. |
| Rejection and cleanup | Existing missing-partition, direct-partition, NULL rejection, failed-batch rollback, and subsequent-statement recovery remain. Partitioned OOS-plus-bigone is rejected with the existing error and no OOS file; the same oversized fixed BIT row without an OOS value still succeeds. |
| UPDATE/nonpartitioned regressions | Original routing/movement tests, storage policies, transaction tests, and bigone tests still pass. This does not migrate UPDATE to effective-key routing. |

The tests establish SQL-observable normalization and routing equivalence for these cases, not bitwise equality of every possible internal DB_VALUE representation. The final destination safeguard also fails closed if an untested normalization discrepancy is encountered. Its artificial-disagreement branch was source-reviewed, not fault-injected in this milestone.

## Build and reproducible evidence

Baseline HEAD: `b871ea386d2c5419b7abae07dda58b9b7f36377a`, plus the completed ticket-01 prefactor. Candidate: that HEAD and the current uncommitted engine/test diff. Pre-existing CCI/submodule and unrelated work were preserved. JSON artifacts capture HEAD, the actual complete source/test diff, binary/library hashes, configuration hash, commands, output, and private fixture paths.

Build mode: debug_gcc. The personal local `direnv exec . just build` workflow compiled/linked and installed SA and server targets. These runtime tests are **SA_MODE**, not server MVCC/vacuum/recovery tests.

The [isolated runner](ticket01-evidence/run-isolated.py) creates private configuration and database directories. The shared/default database is untouched. The configured unqualified `build-test` fixture embeds shared paths and destructive cleanup, so selected test executables were run against private fixtures instead. Temporary evidence/fixtures are retained, not deleted.

| Suite | Evidence |
|---|---|
| SHOW/routing, 20/20 | [final-show.json](ticket02-evidence/final-show.json); [final formatting-only rerun](ticket02-evidence/final-formatted-show.json) |
| Storage, 25/25 | [final-storage.json](ticket02-evidence/final-storage.json) |
| Transactions, 8/8 | [final-txn.json](ticket02-evidence/final-txn.json) |
| OOS/bigone, 4/4 | [final-bigone.json](ticket02-evidence/final-bigone.json) |
| 13-type paired SQL | [reference](ticket02-evidence/reference-legal-csql-alias.json), [final candidate](ticket02-evidence/final-legal-csql.json), [SQL](ticket02-evidence/legal-key-reference.sql) |
| Additional INSERT contracts | [reference](ticket02-evidence/reference-extra-csql.json), [candidate](ticket02-evidence/candidate-extra-csql.json), [SQL](ticket02-evidence/insert-contract-reference.sql) |

Both paired SQL outputs compare identically after removing only reported execution-time numbers (`[0-9]+\.[0-9]+ sec`). Rows, values, errors, partition placement, and SHOW columns are not normalized away. This is a functional comparison, not a timing comparison.

The independent reference library was frozen **before** the effective-key implementation at `/tmp/pr7600-ticket02-reference-ROZTUX/libcubridsa.so.11.5`, SHA-256 `266c72980f5718173eb59c546c16120dfe4a271de8927788c32b2dbfd5d2f4e0`. CSQL loads `libcubridsa.so`; the runner validates that the reference's unversioned alias resolves to this pinned library. Current CSQL and the frozen library run the same retained SQL on independent databases. No engine reset, patched reference algorithm, or mock implementation was used.

### Failed attempts and attribution

- [Clean red](ticket02-evidence/red-default-server-scope.json): omitted DEFAULT 11 could not route through the initially unimplemented effective-key interface; independent record routing passed. [Green](ticket02-evidence/green-default.json) followed the implementation.
- Earlier `red-default.json` also crashed during cleanup because the direct SA test used client allocation mode for server internals. The harness now scopes server allocation correctly. This is not attributed to the reference engine.
- `assigned-char.json` and `assigned-char-padded.json` assigned the value to the wrong physical cache slot. Catalog-ID lookup fixed the harness; [corrected test](ticket02-evidence/assigned-char-key-id.json) passes. Those failed attempts establish **no historical CHAR/LIST rule**.
- `reference-legal-sql.json` could not start the new test executable with the old library because the new routing symbol was absent. It is not a functional comparison.
- `reference-legal-csql.json` lacked the unversioned reference-library alias and must **not** be counted as an independent reference. The valid replacement is `reference-legal-csql-alias.json`; the runner now checks this prerequisite.

## Review and remaining gates

### Standards

Independent review found no hard documented-standard violations. One low-severity duplication heuristic remains in the three focused paired-routing tests; their setup/comparison could be consolidated later. It is not an engine correctness finding. The stale internal parameter comment was corrected. New-test indentation was corrected without reformatting unrelated source.

### Spec

Independent review identified the missing early/final disagreement guard and insufficiently discriminating normalization coverage. Both were addressed and re-reviewed; no actionable ticket-02 blocker remained, conditional on final successful verification. Final SQL/tests passed as recorded above.

Structurally, the claimed INSERT path no longer constructs a full inline probe. A scalar codec round trip, OOS payload serialization, and real record-buffer retries still exist. Allocation/copy counts, runtime benefit, and control-workload regressions have **not** been measured. Retaining the old UPDATE path is deliberate, not silent fallback for an INSERT type.

Next is ticket 03 (UPDATE/unchanged keys/INCR-DECR), with separate authorization. Tickets 04–07 retain fault-cleanup, server lifecycle, measurements, and integration gates. No permission to ship, commit, push, or start those tickets is inferred from completion of this milestone.

Parent spec is unchanged: SHA-256 `dfa82a53337a2cf85c9d18bfe3707d99670a6e7070320a97fc3183b50c01f31f`.
