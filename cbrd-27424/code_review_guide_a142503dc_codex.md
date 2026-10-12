# PR #7925 code review guide at `a142503dc`

This guide explains every changed function, method, class, struct, public declaration, force flag, and test definition in the net PR diff. Its purpose is to help a reviewer understand the change and where to inspect it; it is not a new standards/spec review or a claim that all CI failures have been diagnosed.

- **Exact local guide HEAD:** `a142503dc1a6f85b498a425aa58d6a78136ccc6b`.
- **Fixed base / merge-base:** `fb567a629cdb390fff920542173fa36f454c74a0`.
- **Previously triggered CI HEAD:** `f037616cd17af92e1226afcde80fd2a6fff9121d`. Production source is identical between that CI head and this local head. The final local commit repairs the collection-test oracle and benchmark license header; intervening changes remove internal explanatory docs from the engine tree. CI conclusions must still cite the executed commit. See [the exact executed-head CI report](ci_analysis_report_f037616cd_codex.md) and [the current published-head evidence warning](ci_analysis_report_91bfde02e_codex.md).
- **Source worktree:** `/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa`.
- **Coverage:** 11 changed files, 74 file/symbol occurrences, and 34 concrete GoogleTest cases across two new test binaries. The moved `heap_oos_column_plan` has a deleted occurrence in `heap_file.c` and an added/extended occurrence in `heap_oos.hpp`; shared declarations and definitions are also listed separately so no file-level API change disappears.
- **Machine-readable counterpart:** [symbol inventory](code_review_inventory_a142503dc_codex.json).

HEAD source links are pinned to the exact local commit, but **this commit had not been published when the guide was written**, so those GitHub URLs may not resolve yet. Each HEAD entry also has a working local file link. Base GitHub links are independently pinned. The published CI production code can be inspected at [the executed commit](https://github.com/CUBRID/CUBRID/tree/f037616cd17af92e1226afcde80fd2a6fff9121d); do not substitute that commit for the repaired test oracle.

## The problem and the resulting behavior

The SA object-file loader and certain CSQL object routes build dirty workspace objects, serialize them, then force the resulting `RECDES` into storage. `tf_mem_to_disk` packs headers, fixed values, VOT entries, variable values, and permanent-reference fixups, but it does not invoke the heap attrinfo OOS planner. A correctly loaded large value could therefore remain inline on this route while the query-executor writer demoted the same value. The PR inserts OOS Demotion at the common SA force boundary, after the destination heap is selected, using the already serialized byte spans. [workspace serializer](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/object/transform_cl.c#L781), [workspace packing call](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_cl.c#L4374), [base INSERT dispatch](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L7331), [new force boundary](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.c:5097).

OOS stores a variable attribute’s **serialized value bytes** in one or more OOS chunk records, leaving a 24-byte OOS inline stub: head OOS OID, full length, and packed identity stamp. A variable-offset entry marks that stub as OOS-backed; HAS_OOS marks the record. The new demoter changes placement and the surrounding record layout, while preserving each variable payload’s original serialization. It does not introduce a new OOS file format, reassign object references, or recopy external LOB data. [new demoter](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/storage/heap_oos.cpp:1159), [existing stub parser](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/storage/heap_oos.cpp:443), [normative OOS layout](/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md:213).

## Read the route before individual functions

```text
SA loaddb: ldr_reset_context → workspace MOP / reserved OID
CSQL workspace INSERT or row-trigger UPDATE → dirty workspace object
                         ↓
locator_mem_to_disk → tf_mem_to_disk → LC_COPYAREA
                         ↓
xlocator_force / locator_force_for_multi_update
   INSERT: FROM_WORKSPACE flag      UPDATE: from_workspace=true
                         ↓
locator_insert_force / locator_update_force
   choose child partition and destination heap first
   partition movement → locator_move_record → destination INSERT
                         ↓
locator_oos_demote_workspace_record (SA_MODE only)
                         ↓
heap_oos_demote_workspace_record
   current representation + VOT spans → shared planner
   selected original byte spans → OOS inserts
   fresh compact record → caller-owned private buffer
                         ↓
existing heap/index force writes
   all persistent changes remain inside the existing force top operation
```

`ldr_reset_context` reuses a reserved workspace MOP for a forward reference or calls `db_create_internal` for a new object. Later, `locator_mflush_force` can change an originally queued INSERT into UPDATE when its permanent OID has already been assigned. This is why the PR must cover UPDATE, not merely INSERT. The normal force dispatcher owns an outer top operation; ignored errors add per-object top operations. New OOS insert writes execute inside those same boundaries. [SA loader reservation](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/loaddb/load_sa_loader.cpp#L4618), [flush operation conversion](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_cl.c#L4061), [force/rollback boundaries](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.c:7316).

The DB_VALUE writer still enters `heap_attrinfo_determine_disk_layout`, which is now a small adapter. Both routes feed the same `heap_oos_determine_disk_layout`. SERVER_MODE sees the locator adapter as a no-op. The CS/server loader still prepares OOS through its attrinfo transformation and migrates only its force-call options. Replication apply, query attrinfo force, and redistribution use the new zero-flag default. The provenance flag does not imply that every raw `RECDES` should be demoted. [shared planner](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/storage/heap_oos.cpp:1092), [mode adapter](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.c:4940), [server loader](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/loaddb/load_server_loader.cpp:737).

## Review invariants and the code that owns them

| Invariant | What to inspect |
|---|---|
| Selection policy is shared | DB_VALUE adapter fills metadata/sizes; workspace VOT spans fill the same plan. FORCE_OUTLINE still needs profitable size; PREFER_INLINE is a soft late-priority hint; ties retain descending plan index. |
| Input is a current-representation workspace record | The demoter verifies representation ID, fixed/VOT bounds, monotonic offsets and exact first/end spans. Old disk records are converted by existing object fetch/serialization before this helper. Small ordinary records use an early return and do not undergo the full VOT walk; the helper is not a general hostile-record parser. |
| Original serialized values stay intact | Selected spans are the exact `source->data` bytes submitted to OOS; unselected spans and fixed/bound bytes are memcpy’d. Compressed VARCHAR, JSON, collection representation and object references retain their existing encoding. |
| Destination heap owns each new chain | INSERT demotes after pruning; moving UPDATE propagates provenance to the destination insertion. The partitioned root used as an input target does not own child rows. |
| Source and output memory have separate lifetimes | The source belongs to the caller/copyarea. An unchanged result has NULL data. A successful allocated result is freed at force cleanup; the exported wrapper frees it on error. |
| Persistent rollback uses the existing top operation | Freeing a buffer does not undo chunks. Force failure aborts OOS, heap and index writes together; ignored errors abort their per-object boundary and continue. |
| OOS+REC_BIGONE is rejected before writing new chains | The reserved compact size includes MVCC header growth, is bounded by INT_MAX, and is tested against heap_is_big_length before publication/reset and insertion. If there are no selected OOS values, ordinary large/bigone behavior remains existing behavior. |
| CHN and MVCC space stay valid | The demoter preserves the source CHN, sets record flags/representation/width, uses the appropriate insert header, zero-initializes reserved memory, and leaves room for maximum MVCC header growth. |
| External LOB semantics are preserved | The demoter moves/copies already serialized locator bytes; it never repeats workspace/object serialization. Utility coverage checks unchanged existing BLOB/CLOB files during another attribute’s OOS transition. |
| Logging guarantees are scoped correctly | Successful no-logging storage/readback remains allowed. Logging-disabled operation does not promise crash recovery or identity-stamp uniqueness; the runtime logging state, not a startup parameter, determines that exception. |

The parser guards are preconditions/checks for the trusted workspace route, not a new compatibility converter. The wrapper skips root-class metadata and already HAS_OOS records; an already-marked record is not re-demoted or normalized. The planner only marks profitable variable spans, so no eligible values means source reuse even if the record remains large. Representation/cache and memory lifetimes should be reviewed separately from OOS transaction lifetime. [validation and reconstruction](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/storage/heap_oos.cpp:1159), [wrapper](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/storage/heap_oos.cpp:1331), [normative logging exception](/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md:262).

## Existing specification differences beyond this PR’s scope

The normative OOS context was last updated on 2026-09-22. It requires the derived **PG-style four-record heap target**, 4,060 bytes for the current 16KB layout, excluding heap unfill. Both base and this HEAD still use raw `DB_PAGESIZE/4` for the gate and stop estimate. This is an existing implementation conformance gap tracked by CBRD-27057, preserved during extraction, not a new target change in PR #7925. A test payload parameter of 4,060 does not prove target conformance because record overhead, serialization prefixes and FORCE_OUTLINE also affect that case. [normative target](/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md:100), [base planner](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L12844), [HEAD planner](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/storage/heap_oos.cpp:1116).

The accepted CBRD-27230 design changes UPDATE chain reuse and commit-conditional vacuum notification. The context describes it as accepted but not yet implemented; this PR creates fresh selected chains and does not implement reuse or replace vacuum’s existing behavior. SA eager cleanup, transaction rollback and partition ownership are in scope for preservation. The context separately records the CBRD-27237 rollback/vacuum defect; this guide does not attribute it to this PR or claim it is repaired here. Durable CDC/flashback OOS history is deferred by ADR-0005 from the 11.5 OOS merge. These are distinct projects, not implied outcomes of adding a workspace writer. [accepted ownership design](/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md:371), [known defect](/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md:447), [deferred history decision](/home/vimkim/gh/cubrid-oos-context/docs/adr/0005-defer-oos-history-from-the-11-5-merge.md).

The type-agnostic OOS rule includes external BLOB/CLOB **locator bytes**, not their external contents. This PR’s LOB test preserves existing permanent locators and files during a different attribute’s demotion. Its source explicitly acknowledges a separate fresh-workspace-LOB INSERT defect. Successful no-logging coverage remains narrower than logged rollback/recovery coverage. The benchmark adds a reproducible harness, not a demonstrated speedup. [accepted locator decision](/home/vimkim/gh/cubrid-oos-context/docs/adr/0002-oos-lob-locator-demotion.md), [LOB test](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:365), [benchmark](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/scripts/benchmark_workspace_oos.sh:19).

## CI findings that shape this review

The executed-head report compares GitHub Actions run `37463915181`, attempt 1, at `f037616cd` with run `36570256001`, attempt 1, at the exact merge-base `fb567a629`. The head recorded 975 passing medium cases, 17,471 passing SQL cases, and shell results of 3,256 pass / 3 fail / 30 skip (3,289 total). Both public and private testcase commits match across this comparison. Two shell failures, `cbrd_27064` and `cbrd_27075`, have the same failure families on the base and are consistent with the separate deferred CDC-history work; their precise error site in this run is not established. They are existing failures, not evidence that this workspace writer introduced them. The current published head has no observed run of these suites. [executed-head evidence and comparison](ci_analysis_report_f037616cd_codex.md), [published-head warning](ci_analysis_report_91bfde02e_codex.md).

`20683` is the remaining **review point**: head failed while base passed, with a `spacedb` used-space answer difference of 18.8M versus 18.5M in the primary volume. A bootstrap storage-footprint effect is a plausible hypothesis to check when reading the newly marked workspace force calls and their class/size guards. It is not an attributed defect: CTP revisions differ (`4d0043a` versus `44e3f97`), and the baseline CTP source object is unavailable, so the executed comparison is not fully controlled. The report explains the evidence and the unresolved attribution. Do not repair an expected answer or change the planner on the strength of this hypothesis alone. [20683 evidence and limits](ci_analysis_report_f037616cd_codex.md).

## Symbol-by-symbol explanations

Each entry answers **what it is**, **why it exists**, and **why this PR changes it**. A shared function’s declaration and definition have separate file occurrences. Existing declarations that do not change are recorded in the JSON alongside their changed definition for coverage; declaration-only changes, including defaults, are described explicitly. Inline fixture methods’ definition ranges include their signatures; they do not have separate out-of-line declarations.

### Changed-file map

| File | File-level purpose |
|---|---|
| [`src/loaddb/load_server_loader.cpp`](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/loaddb/load_server_loader.cpp) | Migrates the existing server loader’s individual insertion options to the force bitmask. |
| [`src/storage/heap_file.c`](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/storage/heap_file.c) | Replaces attrinfo-only sizing/selection with an adapter; removes two private helpers and relocates the plan struct. |
| [`src/storage/heap_oos.cpp`](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/storage/heap_oos.cpp) | Adds representation-based shared sizing/selection and byte-preserving workspace demotion; object_domain.h supports fixed-domain disk sizing and algorithm supports candidate sorting/min/max. |
| [`src/storage/heap_oos.hpp`](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/storage/heap_oos.hpp) | Exports the shared metadata/size plan and the two storage entry points with output ownership documented. |
| [`src/transaction/locator_sr.c`](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.c) | Adds heap_oos.hpp for the new storage call, the SA-only adapter, workspace provenance plumbing and force-flag call migrations. |
| [`src/transaction/locator_sr.h`](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.h) | Defines force option bits and changes the public insertion signature/default, retaining GNU-indent guards around C++ defaults. |
| [`unit_tests/oos/CMakeLists.txt`](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/CMakeLists.txt) | Registers and builds the utility-level GoogleTest target test_oos_workspace in the established SA_MODE test list. The executable links cubridsa/GTest and uses existing compile definitions/includes. A new CTest entry is RUN_SERIAL with TIMEOUT 240; each GoogleTest case owns its private database/registry instead of unittestdb. No function, struct, or CMake function/macro definition is added or changed. |
| [`unit_tests/oos/scripts/benchmark_workspace_oos.sh`](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/scripts/benchmark_workspace_oos.sh) | Adds a manual Release benchmark outside CTest: INSTALL OUTPUT LABEL [REPEATS], three repeats by default, with 100,000 rows of 48-byte payloads and 10,000 rows of 5,000-byte payloads. Each sample has a private database/configuration, uses real loaddb -S, records elapsed/user/system CPU CSV through /usr/bin/time, verifies values/row bounds, saves SHOW HEAP OOS output, deletes successful sample databases, and retains inputs/outputs/measurements. mkdir requires a new output directory. There are no shell function definitions; the loops and awk programs are top-level script logic. The final local commit corrects its license template. Merely adding the script establishes no measured performance claim. |
| [`unit_tests/oos/sql/CMakeLists.txt`](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/CMakeLists.txt) | Adds test_oos_sql_workspace_bytes to the registered SQL CTest entries and to the shared OOS_DB fixture-required, RUN_SERIAL, TIMEOUT 30 property group. The existing SQL source glob/target loop handles its build. No function, struct, or CMake function/macro definition is added or changed. |
| [`unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp`](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp) | Adds in-process byte/selection comparison coverage; existing SQL environment plus heap/workspace/primitive APIs provide independent writers and scope_exit provides decoded-collection cleanup. |
| [`unit_tests/oos/test_oos_workspace.cpp`](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp) | Adds real standalone utility coverage; filesystem/POSIX process headers support isolated execution and exact LOB evidence, and namespace fs aliases std::filesystem locally. |

### `src/storage/heap_file.c`

<a id="src-storage-heap-file-c-heap-attrinfo-get-record-payload-size"></a>

#### `heap_attrinfo_get_record_payload_size` — deleted (function)

**What:** The old private sizing helper computed each fixed or variable DB_VALUE column’s serialized size and returned their sum.

**Why it exists:** The old attrinfo-only OOS planner needed a payload total and a size for each demotion candidate.

**Why changed:** Its DB_VALUE sizing work is now performed while filling heap_oos_column_plan in heap_attrinfo_determine_disk_layout; the shared planner sums those sizes. Removing this helper removes the dependency of selection policy on HEAP_CACHE_ATTRINFO. Both its forward declaration and body disappear.

Source: [base L12719](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L12719).
<a id="src-storage-heap-file-c-heap-attrinfo-get-record-header-size"></a>

#### `heap_attrinfo_get_record_header_size` — deleted (function)

**What:** The old private helper selected one-, two-, or four-byte variable-offset entries and counted the record header, VOT, and fixed-attribute bound bitmap.

**Why it exists:** Demotion decisions need the whole inline record size, and moving values out of row can narrow the VOT.

**Why changed:** Its representation-based calculation moves to heap_oos_record_header_size in heap_oos.cpp, which accepts OR_CLASSREP and a payload size rather than an attrinfo object. Its declaration and definition are removed so both writers use one calculation.

Source: [base L12756](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L12756).
<a id="src-storage-heap-file-c-heap-oos-column-plan"></a>

#### `heap_oos_column_plan` — deleted (struct)

**What:** The former file-local plan held selection, the resulting head OOS OID, full serialized length, and chain identity stamp for one attribute.

**Why it exists:** The heap writer needs to connect the planner’s decision with the OOS insert result and the later inline stub.

**Why changed:** The type is relocated and extended in heap_oos.hpp. This deletion is a move, not removal of the concept: shared selection also needs the attribute metadata and already-known serialized disk size.

Source: [base L730](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L730).
<a id="src-storage-heap-file-c-heap-attrinfo-determine-disk-layout"></a>

#### `heap_attrinfo_determine_disk_layout` — modified (function)

**What:** The adapter from a heap attribute cache to the shared OOS plan. Its existing pointer-output signature and private declaration remain.

**Why it exists:** SQL/query-executor and other DB_VALUE writers still start from HEAP_CACHE_ATTRINFO rather than a serialized workspace record.

**Why changed:** It now fills each plan entry with last_attrepr plus tp_domain_disk_size for fixed attributes or pr_data_writeval_disk_size for variable values, then delegates to heap_oos_determine_disk_layout. The previous forced-selection, candidate sorting, gate, and offset-width calculation leave this function. This deliberately makes policy shared while preserving the existing DB_VALUE writer entry point.

Source: [HEAD L12706](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/storage/heap_file.c#L12706), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/storage/heap_file.c:12706), [base L12799](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L12799).

### `src/storage/heap_oos.hpp`

<a id="src-storage-heap-oos-hpp-heap-oos-column-plan"></a>

#### `heap_oos_column_plan` — added (struct)

**What:** Shared per-attribute state: attribute points to OR_ATTRIBUTE; disk_size is the existing serialized size; selected marks demotion; oid, length, and identity_stamp describe the newly inserted OOS value chain.

**Why it exists:** One plan must work for values measured through DB_VALUE and values measured from VOT spans without requiring either representation to be decoded.

**Why changed:** The file-local struct moves here and gains attribute=nullptr and disk_size=0. Existing defaults remain selected=false, OID_INITIALIZER, length=0, NULL_LSA. Callers supply all metadata and sizes before invoking the planner; returned OIDs and stamps are subsequently used to write the 24-byte stub.

Source: [HEAD L66](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/storage/heap_oos.hpp#L66), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/storage/heap_oos.hpp:66).
<a id="src-storage-heap-oos-hpp-heap-oos-determine-disk-layout"></a>

#### `heap_oos_determine_disk_layout` — added (function declaration)

**What:** The public declaration for metadata-and-size-based OOS selection; parameters expose representation, MVCC class state, a mutable plan, and references for offset width, inline size, and has_oos.

**Why it exists:** The DB_VALUE adapter in heap_file.c and workspace demoter in heap_oos.cpp need one policy boundary.

**Why changed:** It makes the extracted planner callable across translation units. There are no default parameters; input metadata and sizes must already be populated. Its definition and detailed policy are covered under heap_oos.cpp.

Source: [HEAD L76](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/storage/heap_oos.hpp#L76), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/storage/heap_oos.hpp:76).
<a id="src-storage-heap-oos-hpp-heap-oos-demote-workspace-record"></a>

#### `heap_oos_demote_workspace_record` — added (function declaration)

**What:** The public storage entry point for applying OOS Demotion to an already serialized, current-representation workspace record.

**Why it exists:** Locator force needs storage-layer work without owning the binary-layout implementation.

**Why changed:** The contract states that source bytes stay unchanged, result->data remains NULL when unchanged, and a new successful buffer belongs to the caller and must be freed with db_private_free. OOS writes belong to the caller’s existing force top operation. Its definition is covered under heap_oos.cpp.

Source: [HEAD L82](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/storage/heap_oos.hpp#L82), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/storage/heap_oos.hpp:82).

### `src/storage/heap_oos.cpp`

<a id="src-storage-heap-oos-cpp-heap-oos-record-header-size"></a>

#### `heap_oos_record_header_size` — added (function)

**What:** A private representation-based replacement for the deleted attrinfo header-size helper. It counts the MVCC/non-MVCC insert header, fixed bound bits, and VOT at the smallest fitting offset width.

**Why it exists:** Both writers must predict the same inline layout after demotion, including VOT width transitions.

**Why changed:** It removes the need for HEAP_CACHE_ATTRINFO, uses size_t for payload/header accounting, starts at OR_BYTE_SIZE, widens past OR_MAX_BYTE and OR_MAX_SHORT, and returns the header size. The planner recalculates after forced demotion and after the largest-first loop; the loop itself retains its initial header estimate to preserve base policy.

Source: [HEAD L1070](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/storage/heap_oos.cpp#L1070), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/storage/heap_oos.cpp:1070).
<a id="src-storage-heap-oos-cpp-heap-oos-determine-disk-layout"></a>

#### `heap_oos_determine_disk_layout` — added (function)

**What:** The shared selection policy over OR_CLASSREP and a vector of serialized column sizes. It returns selected entries, offset width, compact inline size, and whether any OOS value is selected.

**Why it exists:** A workspace record already contains serialized values, so selection should use metadata and byte lengths without creating DB_VALUE objects or duplicating SQL policy.

**Why changed:** It extracts the policy from heap_file.c: clear selection, sum payload, apply FORCE_OUTLINE only to variable values strictly larger than OR_OOS_INLINE_SIZE, then if the record plus MVCC growth exceeds the existing DB_PAGESIZE/4 gate, sort remaining candidates by ordinary-before-PREFER_INLINE, largest size first, then descending plan index. Demote until the conservative estimate fits or candidates run out, recompute the header, and translate candidate-vector bad_alloc into ER_OUT_OF_VIRTUAL_MEMORY. NULL values naturally fail the size floor; the DB_VALUE-specific null test is no longer needed.

Source: [HEAD L1091](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/storage/heap_oos.cpp#L1091), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/storage/heap_oos.cpp:1091).
<a id="src-storage-heap-oos-cpp-heap-oos-demote-workspace-record-internal"></a>

#### `heap_oos_demote_workspace_record_internal` — added (function)

**What:** The private byte-level implementation that validates a workspace RECDES, plans OOS Demotion, writes selected byte spans, and builds a fresh compact heap record.

**Why it exists:** Workspace serialization has already assigned references, copied LOB locators, and advanced CHN. Decoding and re-encoding every value adds cost and risks repeating side effects or changing a valid encoding.

**Why changed:** It measures variable values from adjacent VOT offsets, supplies fixed sizes from domains, and maps attribute array indices to variable locations. It keeps a small ordinary record unchanged before allocating per-row arrays; FORCE_OUTLINE bypasses this shortcut. If selected, it rejects OOS+REC_BIGONE before writes, resets publication, batches original byte spans through heap_oos_insert_serialized_values, copies fixed/bound bytes and unselected spans exactly, writes 24-byte OOS inline stubs, rewrites VOT/flags, preserves CHN, and reserves MVCC growth room. It never frees source storage or begins a new transaction boundary.

Source: [HEAD L1158](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/storage/heap_oos.cpp#L1158), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/storage/heap_oos.cpp:1158).
<a id="src-storage-heap-oos-cpp-heap-oos-demote-workspace-record"></a>

#### `heap_oos_demote_workspace_record` — added (function)

**What:** The exported guard and lifetime wrapper around the private demoter.

**Why it exists:** Locator needs a CUBRID error-return boundary around representation-cache acquisition and potentially throwing vector operations.

**Why changed:** It requires an empty result buffer, skips root-class metadata and records already marked HAS_OOS, acquires the current class representation, invokes the private helper, translates bad_alloc, always returns the representation to the cache, and frees any allocated result on error. On success, a NULL result means reuse source; a non-NULL result remains caller-owned. Transaction rollback, rather than this memory cleanup, undoes OOS writes.

Source: [HEAD L1330](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/storage/heap_oos.cpp#L1330), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/storage/heap_oos.cpp:1330).

### `src/transaction/locator_sr.h`

<a id="src-transaction-locator-sr-h-locator-force-flag"></a>

#### `LOCATOR_FORCE_FLAG` — added (enum)

**What:** A named set of independent insert-force behavior bits, combined into the int force_flags parameter.

**Why it exists:** Insert force already had three independent boolean options; workspace provenance adds a fourth choice that must compose with bulk and foreign-key behavior.

**Why changed:** It replaces the trailing positional booleans with explicit bit combinations and introduces FROM_WORKSPACE. This is a source-level API change in server/SA code; both public declaration and every affected caller in the diff are covered below.

Source: [HEAD L134](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/transaction/locator_sr.h#L134), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.h:134).
<a id="src-transaction-locator-sr-h-lc-force-flag-none"></a>

#### `LC_FORCE_FLAG_NONE` — added (enum member)

**What:** No optional insert-force behavior.

**Why it exists:** A zero value is needed for ordinary callers and conditional bit expressions.

**Why changed:** The new default parameter uses it, preserving the former false/false/false combinations.

Source: [HEAD L136](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/transaction/locator_sr.h#L136), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.h:136).
<a id="src-transaction-locator-sr-h-lc-force-flag-has-bu-lock"></a>

#### `LC_FORCE_FLAG_HAS_BU_LOCK` — added (enum member)

**What:** The transaction holds a BU_LOCK for bulk insertion.

**Why it exists:** Heap force distinguishes bulk operations when choosing locking/insertion behavior.

**Why changed:** It encodes the former has_BU_lock boolean; loader and multi-insert callers preserve their lock-derived value.

Source: [HEAD L137](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/transaction/locator_sr.h#L137), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.h:137).
<a id="src-transaction-locator-sr-h-lc-force-flag-dont-check-fk"></a>

#### `LC_FORCE_FLAG_DONT_CHECK_FK` — added (enum member)

**What:** Skip foreign-key rechecking at force time.

**Why it exists:** Some callers already validate foreign keys before force.

**Why changed:** It replaces the former dont_check_fk boolean; server loaddb retains its explicit skip and multi-insert preserves its argument.

Source: [HEAD L138](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/transaction/locator_sr.h#L138), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.h:138).
<a id="src-transaction-locator-sr-h-lc-force-flag-bulk-logging"></a>

#### `LC_FORCE_FLAG_BULK_LOGGING` — added (enum member)

**What:** Use page-granularity bulk logging for the insert.

**Why it exists:** The multi-insert optimization supplies a page watcher and a different logging mode.

**Why changed:** It replaces use_bulk_logging; only the existing bulk page insertion branch adds this bit.

Source: [HEAD L139](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/transaction/locator_sr.h#L139), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.h:139).
<a id="src-transaction-locator-sr-h-lc-force-flag-from-workspace"></a>

#### `LC_FORCE_FLAG_FROM_WORKSPACE` — added (enum member)

**What:** The RECDES came from workspace serialization and still needs force-time OOS Demotion.

**Why it exists:** Heap/query and replication writers must be distinguishable from the omitted SA workspace route.

**Why changed:** xlocator_force sets it for workspace INSERT, and partition moves propagate it to destination INSERT. The helper gates actual demotion on SA_MODE; merely setting this bit on SERVER_MODE does not run the new demoter.

Source: [HEAD L140](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/transaction/locator_sr.h#L140), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.h:140).
<a id="src-transaction-locator-sr-h-locator-insert-force"></a>

#### `locator_insert_force` — modified (function declaration)

**What:** The public declaration of the heap-and-index insert primitive.

**Why it exists:** Loader, locator, query-force and replication paths share the same insertion mechanism.

**Why changed:** The trailing has_BU_lock, dont_check_fk, use_bulk_logging=false parameters become int force_flags=LC_FORCE_FLAG_NONE. This default supplies the former all-false behavior for callers that omit it. The C++ declaration is wrapped with INDENT-OFF/ON so GNU indent preserves the default parameter.

Source: [HEAD L145](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/transaction/locator_sr.h#L145), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.h:145), [base L132](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.h#L132).

### `src/transaction/locator_sr.c`

<a id="src-transaction-locator-sr-c-locator-oos-demote-workspace-record"></a>

#### `locator_oos_demote_workspace_record` — added (function)

**What:** A private locator adapter that may redirect its local RECDES pointer to a newly demoted buffer.

**Why it exists:** Insert and update force need the same SA-only storage call and a simple unchanged-record result.

**Why changed:** In SA_MODE it invokes heap_oos_demote_workspace_record and redirects *recdes_p only on success with non-NULL output data. In SERVER_MODE it returns NO_ERROR without storage work. The caller retains workspace_recdes for cleanup; the source copyarea is never replaced or freed here.

Source: [HEAD L4939](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/transaction/locator_sr.c#L4939), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.c:4939).
<a id="src-transaction-locator-sr-c-locator-insert-force"></a>

#### `locator_insert_force` — modified (function)

**What:** The primitive that chooses the insertion heap, creates a heap operation context, writes the object, and maintains indexes and related force state.

**Why it exists:** Multiple higher-level writers need one place to enforce heap, partition and index insertion semantics.

**Why changed:** It decodes force_flags into the former three booleans plus from_workspace, adds an empty workspace_recdes, and invokes the SA demoter after partition_prune_insert has selected real_class_oid/real_hfid and before heap_create_insert_context. This ensures OOS chains belong to the destination heap. It frees the optional output at shared error2 cleanup on success or failure. Existing query/replication callers use zero flags and avoid new demotion.

Source: [HEAD L4982](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/transaction/locator_sr.c#L4982), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.c:4982), [base L4951](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L4951).
<a id="src-transaction-locator-sr-c-locator-update-force"></a>

#### `locator_update_force` — modified (function)

**What:** The private primitive for updating a forced object, including reserved-OID writes, instance indexes, class metadata, and possible partition movement.

**Why it exists:** A workspace flush may represent a logically new row as UPDATE because a forward reference has already reserved its permanent OID; row triggers also route SQL updates through workspace.

**Why changed:** Its private declaration gains bool from_workspace=false, preserving all unchanged callers; the definition takes the explicit final boolean. It allocates workspace_recdes, passes provenance through locator_move_record when pruning selects another child, and for an in-heap instance update demotes after pruning and before index/heap writes. Cleanup frees the optional buffer. Root-class metadata is excluded by the heap wrapper. An INSERT-only fix would miss both reserved OIDs and workspace UPDATE.

Source: [HEAD L5513](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/transaction/locator_sr.c#L5513), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.c:5513), [base L5464](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L5464).
<a id="src-transaction-locator-sr-c-locator-move-record"></a>

#### `locator_move_record` — modified (function)

**What:** The private UPDATE helper that inserts a row into the selected child partition and deletes it from its previous heap.

**Why it exists:** Changing a partition key may change the destination heap, requiring insertion and deletion rather than an in-place update.

**Why changed:** Both private declaration and definition gain a required final from_workspace boolean. Both destination insertion variants translate it to FROM_WORKSPACE or NONE, so demotion occurs in destination INSERT after ownership has been selected. It does not demote in the old child or introduce chain sharing between heaps.

Source: [HEAD L5410](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/transaction/locator_sr.c#L5410), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.c:5410), [base L5364](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L5364).
<a id="src-transaction-locator-sr-c-locator-force-for-multi-update"></a>

#### `locator_force_for_multi_update` — modified (function)

**What:** The copyarea handler for batches of instance UPDATE operations performed through the client/workspace path.

**Why it exists:** Multi-row workspace updates have shared unique-statistics and force bookkeeping distinct from single-row flushes.

**Why changed:** It adds an explicit true as locator_update_force’s final from_workspace argument. The already-existing need_locking=true remains the preceding boolean. This covers trigger-selected multi-row workspace UPDATE in SA; the SA_MODE adapter remains the effective mode gate.

Source: [HEAD L6695](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/transaction/locator_sr.c#L6695), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.c:6695), [base L6633](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L6633).
<a id="src-transaction-locator-sr-c-xlocator-force"></a>

#### `xlocator_force` — modified (function)

**What:** The normal workspace copyarea dispatcher for INSERT, UPDATE and DELETE, owning an outer force top operation and optional per-object top operations.

**Why it exists:** It turns dirty workspace records into persistent heap/index changes and supports ignored object errors.

**Why changed:** INSERT variants now pass FROM_WORKSPACE; UPDATE variants pass from_workspace=true. DELETE behavior stays as the existing code. New OOS writes therefore execute inside the existing outer top operation and, for filtered errors, the existing per-object rollback boundary. It also delegates multi-row updates to the separately changed handler.

Source: [HEAD L7315](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/transaction/locator_sr.c#L7315), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.c:7315), [base L7253](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L7253).
<a id="src-transaction-locator-sr-c-xlocator-repl-force"></a>

#### `xlocator_repl_force` — modified (function)

**What:** The replication apply copyarea dispatcher, including replica OOS handling and per-object apply errors.

**Why it exists:** Replication replays already prepared row/OOS state with its own publication and transaction handling.

**Why changed:** The insert call drops the former explicit false/false arguments and relies on force_flags=NONE. This is an API migration only: it does not label replica data as workspace-originated or run the new SA demoter. Its transaction and OOS fixup logic is outside the PR’s semantic change.

Source: [HEAD L7082](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/transaction/locator_sr.c#L7082), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.c:7082), [base L7020](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L7020).
<a id="src-transaction-locator-sr-c-locator-attribute-info-force"></a>

#### `locator_attribute_info_force` — modified (function)

**What:** The force path that starts from HEAP_CACHE_ATTRINFO, transforms DB_VALUEs to a record, then inserts or updates heap/index storage.

**Why it exists:** SQL/query execution already has DB_VALUE-based serialization and OOS preparation.

**Why changed:** Its insertion call omits the former false/false arguments and takes the new default NONE. It intentionally leaves FROM_WORKSPACE unset because its record has already passed the attrinfo writer and shared planner. Its UPDATE call keeps the new private default from_workspace=false.

Source: [HEAD L7647](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/transaction/locator_sr.c#L7647), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.c:7647), [base L7585](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L7585).
<a id="src-transaction-locator-sr-c-redistribute-partition-data"></a>

#### `redistribute_partition_data` — modified (function)

**What:** The existing internal partition-data redistribution routine that fetches rows and inserts them into the partition arrangement.

**Why it exists:** Partition DDL needs a specialized row-moving path preserving existing MVCC identity and storage semantics.

**Why changed:** Its insert call drops false/false and takes force_flags=NONE, preserving UPDATE_INPLACE_OLD_MVCCID. This is a call-signature migration; the PR’s workspace-provenance path is not added to redistribution. Do not confuse this routine with workspace UPDATE’s changed locator_move_record.

Source: [HEAD L12967](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/transaction/locator_sr.c#L12967), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.c:12967), [base L12906](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L12906).
<a id="src-transaction-locator-sr-c-locator-multi-insert-force"></a>

#### `locator_multi_insert_force` — modified (function)

**What:** The multi-record insert routine used by the server loader, with ordinary fallback and an optimized heap-page insertion branch.

**Why it exists:** Batch insertion can reduce per-row page and logging overhead while retaining individual-force fallbacks.

**Why changed:** It composes force_flags from the actual BU lock and dont_check_fk argument once. Ordinary/fallback calls use those bits; the watcher-assisted bulk-page branch adds BULK_LOGGING. None of these calls sets FROM_WORKSPACE because the server loader already transforms its DB_VALUEs. Its own public signature stays the same.

Source: [HEAD L14087](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/transaction/locator_sr.c#L14087), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/transaction/locator_sr.c:14087), [base L14026](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L14026).

### `src/loaddb/load_server_loader.cpp`

<a id="src-loaddb-load-server-loader-cpp-server-object-loader-flush-records"></a>

#### `server_object_loader::flush_records` — modified (method)

**What:** The cubload server loader method that forces the collected record batch, either individually for filtered errors/HA or through multi-insert.

**Why it exists:** Client-server loading prepares DB_VALUE-based records before force and needs lock, foreign-key, error-filter, and replication behavior preserved during batching.

**Why changed:** It creates force_flags=DONT_CHECK_FK plus HAS_BU_LOCK when held, and passes this bitmask in the individual insertion call. This exactly represents the previous has_BU_lock,true,false arguments. It is an API migration caused by locator_insert_force’s change; it does not add SA workspace demotion to this already-prepared server loader path.

Source: [HEAD L736](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/src/loaddb/load_server_loader.cpp#L736), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/src/loaddb/load_server_loader.cpp:736), [base L736](https://github.com/CUBRID/CUBRID/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/loaddb/load_server_loader.cpp#L736).

### `unit_tests/oos/test_oos_workspace.cpp`

<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest"></a>

#### `OosWorkspaceTest` — added (class)

**What:** The GoogleTest fixture for actual installed cubrid/csql utilities; each case owns a private temporary database, registry, configuration, command logs, deterministic payload, and sequence counter.

**Why it exists:** In-process db_execute tests alone cannot prove the standalone object-file loader took its real workspace route, and no-logging state must not contaminate another case.

**Why changed:** It adds isolated utility-level coverage of loader/workspace storage ownership and errors. root owns evidence; payload is deterministic 5,000-byte VARBIT data; sequence gives unique command filenames; created guards successful cleanup. Failed cases retain their directory and database for investigation.

Source: [HEAD L44](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L44), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:44).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-read"></a>

#### `OosWorkspaceTest::read` — added (method)

**What:** Reads an evidence file as binary into a string and records an expectation if opening fails.

**Why it exists:** Command output and LOB bytes must be inspectable without text normalization.

**Why changed:** It gives the new fixture a common reader for utility evidence and exact LOB snapshots.

Source: [HEAD L52](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L52), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:52).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-write"></a>

#### `OosWorkspaceTest::write` — added (method)

**What:** Writes generated SQL, object files, or configuration and asserts successful close.

**Why it exists:** Utility tests need literal fixtures and useful failure locations.

**Why changed:** It creates inputs under the private fixture directory; callers use ASSERT_NO_FATAL_FAILURE where continuation would be invalid.

Source: [HEAD L59](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L59), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:59).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-run"></a>

#### `OosWorkspaceTest::run` — added (method)

**What:** Executes an argv vector through fork/execvp, pipes a saved input file to stdin, captures stdout/stderr, and validates termination/output.

**Why it exists:** The fixture must call real utilities while controlling environment, timeouts, and expected rejection.

**Why changed:** The child alone sets its registry/configuration and LC_ALL=C, changes directory, and arms a 60-second alarm; the parent handles EINTR and waits. Defaults input="" and expected_error="" mean empty stdin and successful command. A nonempty expected_error requires nonzero exit plus a case-insensitive diagnostic match. Paths/SQL are never shell-interpolated.

Source: [HEAD L69](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L69), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:69).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-sql"></a>

#### `OosWorkspaceTest::sql` — added (method)

**What:** Runs csql in standalone mode as DBA with explicit transactions and line output.

**Why it exists:** Readable SQL assertions must go through the installed SA utility against the private database.

**Why changed:** It wraps run with -S, --no-auto-commit, and --line-output for the new utility fixture.

Source: [HEAD L136](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L136), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:136).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-load"></a>

#### `OosWorkspaceTest::load` — added (method)

**What:** Writes a loaddb object file and runs cubrid loaddb -S with optional arguments and an expected-error expression.

**Why it exists:** A SQL INSERT would not establish standalone object-file loader coverage.

**Why changed:** Default options={} and expected_error="" select ordinary successful loading; callers can request --no-logging or an error-control file and expected rejection. The case’s generated object file is retained with evidence if failure occurs.

Source: [HEAD L141](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L141), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:141).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-expect-chunks"></a>

#### `OosWorkspaceTest::expect_chunks` — added (method)

**What:** Extracts every Oos_num_recs field from SHOW HEAP OOS output and compares the ordered list of counts.

**Why it exists:** Logical value equality alone cannot prove OOS-path execution or detect orphan chunks.

**Why changed:** It checks explicit physical chunk-count observations, including before/after rollback sequences and partition ownership.

Source: [HEAD L152](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L152), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:152).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-check"></a>

#### `OosWorkspaceTest::check` — added (method)

**What:** Queries a value/row-count predicate and SHOW HEAP OOS, requiring VALUE_OK and an exact chunk count.

**Why it exists:** Each scenario needs both a logical oracle and independent OOS-path evidence.

**Why changed:** It packages these two assertions; rows is the expected count and chunks counts physical chunk records, not logical value chains. Empty-table rejection uses an explicit zero-row query instead of this SUM-based helper.

Source: [HEAD L164](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L164), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:164).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-seed-workspace"></a>

#### `OosWorkspaceTest::seed_workspace` — added (method)

**What:** Creates a primary-key table, chooses insert_execution_mode=0, inserts and commits a large VARBIT row, then verifies one OOS chunk.

**Why it exists:** Later rollback/error tests need a known committed workspace-produced baseline.

**Why changed:** It also exercises reserved-OID handling through a direct workspace INSERT rather than the default query executor.

Source: [HEAD L176](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L176), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:176).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-seed-references"></a>

#### `OosWorkspaceTest::seed_references` — added (method)

**What:** Creates an object-reference table and loads two mutually referring rows using forward/backward object-file references.

**Why it exists:** OID reservation can change a pending flush from INSERT to UPDATE.

**Why changed:** It proves permanent references and OOS values coexist before tests perform workspace updates and cleanup.

Source: [HEAD L184](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L184), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:184).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-seed-partitions"></a>

#### `OosWorkspaceTest::seed_partitions` — added (method)

**What:** Creates a two-child range-partitioned table and loads one large row into each child.

**Why it exists:** OOS writes must follow the destination heap rather than the input partitioned root.

**Why changed:** It requires one chunk per child, correct row values, and zero chunks owned by the partitioned root.

Source: [HEAD L192](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L192), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:192).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-lob-files"></a>

#### `OosWorkspaceTest::lob_files` — added (method)

**What:** Snapshots the paths and binary contents of all regular files under the fixture’s external LOB directory.

**Why it exists:** A value query alone would miss duplicated, replaced, or modified external LOB files.

**Why changed:** It provides an exact before/after filesystem oracle for workspace updates that demote another attribute.

Source: [HEAD L202](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L202), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:202).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-setup"></a>

#### `OosWorkspaceTest::SetUp` — added (method)

**What:** Creates a unique directory, isolated configuration, deterministic random VARBIT payload, LOB directory, and fresh 16KB-page database.

**Why it exists:** Each utility test must begin with independent persistent and no-logging state.

**Why changed:** It uses 32MB initial data/log volumes and marks created only after successful setup; generated data avoids string-compression ambiguity.

Source: [HEAD L215](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L215), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:215).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-teardown"></a>

#### `OosWorkspaceTest::TearDown` — added (method)

**What:** Deletes a successfully tested private database and directory; failed cases retain their evidence path.

**Why it exists:** Isolation needs cleanup, but a failing utility scenario needs its inputs, outputs, and database preserved.

**Why changed:** It handles partial setup with root/created guards, runs deletedb only for a successful case, and prints the retained path after failure.

Source: [HEAD L236](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L236), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:236).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-standaloneloaderstoresoos"></a>

#### `OosWorkspaceTest.StandaloneLoaderStoresOos` — added (test case)

**What:** A one-row real SA loaddb scenario.

**Why it exists:** The reported defect is missing OOS Demotion in the standalone object loader.

**Why changed:** It requires exact loaded VARBIT value and one physical OOS chunk, catching a successful but fully inline load.

Source: [HEAD L257](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L257), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:257).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-loaderrejectsoosbigonebutkeepsordinarybigone"></a>

#### `OosWorkspaceTest.LoaderRejectsOosBigoneButKeepsOrdinaryBigone` — added (test case)

**What:** A paired OOS+large-fixed record rejection and ordinary fixed-only REC_BIGONE acceptance scenario.

**Why it exists:** The demoter must reject unsupported coexistence without banning ordinary overflow records.

**Why changed:** It requires the first load to fail with a maximum-record diagnostic, leave zero rows/chunks, and the fixed-only load to succeed with correct value and zero OOS chunks.

Source: [HEAD L264](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L264), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:264).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-workspaceinsertusesreservedoid"></a>

#### `OosWorkspaceTest.WorkspaceInsertUsesReservedOid` — added (test case)

**What:** A direct workspace INSERT through seed_workspace.

**Why it exists:** An existing permanent/reserved OID may send a logically new object through update force.

**Why changed:** It adds a named regression requiring the row and OOS chain to be stored through the common workspace force route.

Source: [HEAD L278](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L278), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:278).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-loaderpreservesforwardandbackwardreferences"></a>

#### `OosWorkspaceTest.LoaderPreservesForwardAndBackwardReferences` — added (test case)

**What:** Two mutually referencing loaddb rows.

**Why it exists:** Demotion must preserve previously fixed permanent object references and handle reserved-OID UPDATE.

**Why changed:** It checks peer.id relationships, both large values, and exactly two OOS chunks.

Source: [HEAD L283](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L283), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:283).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-partitionsownseparateoosfiles"></a>

#### `OosWorkspaceTest.PartitionsOwnSeparateOosFiles` — added (test case)

**What:** Loads through a partitioned root and examines both children and root.

**Why it exists:** The destination heap is the OOS owner.

**Why changed:** It requires child-owned storage and a root count of zero through seed_partitions.

Source: [HEAD L288](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L288), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:288).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-insertrollbackreclaimsflushedchain"></a>

#### `OosWorkspaceTest.InsertRollbackReclaimsFlushedChain` — added (test case)

**What:** Flushes an uncommitted workspace INSERT using SELECT, observes storage, then rolls back.

**Why it exists:** A row that merely stayed pending in workspace would not test OOS rollback.

**Why changed:** It requires chunk counts 2 then 1 and preservation of the committed seed row/value.

Source: [HEAD L293](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L293), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:293).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-workspaceupdaterollbackcommitanddelete"></a>

#### `OosWorkspaceTest.WorkspaceUpdateRollbackCommitAndDelete` — added (test case)

**What:** Forces a two-row workspace UPDATE with a row trigger, then separately tests rollback, committed replacement, and DELETE.

**Why it exists:** Both multi-update provenance and existing SA eager cleanup must stay inside transaction semantics.

**Why changed:** It requires correct old values after rollback, replacement values after commit, stable two-chunk ownership, preserved references, and zero chunks after deletion.

Source: [HEAD L304](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L304), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:304).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-faileduniqueloadrollsbackwithoutorphans"></a>

#### `OosWorkspaceTest.FailedUniqueLoadRollsBackWithoutOrphans` — added (test case)

**What:** Loads a new row followed by a duplicate primary key without an ignored-error rule.

**Why it exists:** A failing batch must undo previously inserted row/OOS state.

**Why changed:** It expects a unique diagnostic and only the committed seed row and its one chunk afterward.

Source: [HEAD L320](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L320), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:320).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-filteredduplicateleavesnoorphanandcontinues"></a>

#### `OosWorkspaceTest.FilteredDuplicateLeavesNoOrphanAndContinues` — added (test case)

**What:** Ignores ER_BTREE_UNIQUE_FAILED (-670), rejects a duplicate row, then loads a valid later row.

**Why it exists:** The per-object top operation must undo only the failed row’s OOS work and allow continued loading.

**Why changed:** It requires both valid IDs, correct values, and two chunks rather than an orphan from the rejected duplicate.

Source: [HEAD L327](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L327), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:327).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-loaderhonorsstoragepolicy"></a>

#### `OosWorkspaceTest.LoaderHonorsStoragePolicy` — added (test case)

**What:** Exercises NULL/empty/small values, a small FORCE_OUTLINE value, unequal largest-first candidates, and a 50,000-byte multichunk value.

**Why it exists:** The new workspace route must use the same selection policy and storage behavior as DB_VALUE writers.

**Why changed:** It requires no OOS for the tiny table, one forced chunk, one largest-first chunk whose aggregate serialized size is just over 3,000 bytes, and four chunks for the multichunk case, while checking every logical value. This case does not independently test PREFER_INLINE; the byte fixture does.

Source: [HEAD L337](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L337), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:337).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-workspaceupdatepreservesexternallobfiles"></a>

#### `OosWorkspaceTest.WorkspaceUpdatePreservesExternalLobFiles` — added (test case)

**What:** Updates a separate VARBIT attribute while permanent BLOB/CLOB locators remain on the row.

**Why it exists:** OOS Demotion must preserve serialized external locators without recopying external LOB data.

**Why changed:** After trigger-selected rollback and commit it compares BLOB/CLOB values plus exact LOB file paths/bytes. It seeds LOBs through query execution because fresh workspace LOB INSERT has a separate pre-existing defect; it does not claim coverage of every locator-demotion combination.

Source: [HEAD L365](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L365), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:365).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-partitionmovementtransfersownership"></a>

#### `OosWorkspaceTest.PartitionMovementTransfersOwnership` — added (test case)

**What:** Changes a partition key through a trigger-selected workspace UPDATE.

**Why it exists:** The FROM_WORKSPACE marker must survive movement to the destination insertion.

**Why changed:** It requires zero chunks in the old child and two correct rows/chunks in the destination child, detecting OOS creation in the wrong heap or leaked source ownership.

Source: [HEAD L384](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L384), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:384).
<a id="unit-tests-oos-test-oos-workspace-cpp-oosworkspacetest-successfulnologgingloadstoresoos"></a>

#### `OosWorkspaceTest.SuccessfulNoLoggingLoadStoresOos` — added (test case)

**What:** Runs --no-logging SA loaddb on a fresh private database and reads back the large value.

**Why it exists:** Successful no-logging bulk loading remains supported under the accepted OOS logging exception.

**Why changed:** It requires the correct row and one chunk. It establishes successful storage/readback only; it does not establish crash recovery, failed-load rollback, or identity-stamp uniqueness without logging.

Source: [HEAD L393](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L393), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:393).
<a id="unit-tests-oos-test-oos-workspace-cpp-main"></a>

#### `main` — added (function)

**What:** The utility test binary’s GoogleTest entry point.

**Why it exists:** CTest needs an executable entry point that accepts GoogleTest filtering and reports its exit code.

**Why changed:** It initializes GoogleTest and runs this fixture’s cases; database lifetime belongs to each case, so it does not add the shared SQL server environment.

Source: [HEAD L400](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/test_oos_workspace.cpp#L400), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/test_oos_workspace.cpp:400).

### `unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp`

<a id="unit-tests-oos-sql-test-oos-sql-workspace-bytes-cpp-oosworkspacebytes"></a>

#### `OosWorkspaceBytes` — added (class)

**What:** The in-process GoogleTest fixture comparing a tf_mem_to_disk workspace record with the new demotion result, a DB_VALUE-based reference writer, and the query writer’s stored image.

**Why it exists:** CLI value/chunk counts cannot prove the demoter copied serialized spans exactly or selected the same columns at encoding/VOT boundaries.

**Why changed:** It tracks an optional private output RECDES and whether a test sysop is active. All demotion writes stay in that sysop and teardown aborts them; the table and transaction are also cleaned up. It uses the established OOS SQL fixture infrastructure.

Source: [HEAD L41](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L41), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:41).
<a id="unit-tests-oos-sql-test-oos-sql-workspace-bytes-cpp-oosworkspacebytes-teardown"></a>

#### `OosWorkspaceBytes::TearDown` — added (method)

**What:** Frees the optional demoted buffer, aborts the test sysop when started, aborts the transaction, drops the test table, and commits cleanup.

**Why it exists:** Reference serialization and actual demotion create OOS chains during each comparison, and ASSERT failures may stop the test early.

**Why changed:** The sysop flag and RECDES_INITIALIZER make cleanup safe after partial progress. Freeing memory and aborting persistent OOS writes are deliberately separate operations.

Source: [HEAD L47](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L47), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:47).
<a id="unit-tests-oos-sql-test-oos-sql-workspace-bytes-cpp-oosworkspacebytes-compare"></a>

#### `OosWorkspaceBytes::compare` — added (method)

**What:** Compares record HAS_OOS, each variable column’s OOS selection, and its payload read either from an inline span or an actual OOS chain.

**Why it exists:** Different inserted chains have different physical OIDs/stamps; useful equivalence is selection and payload, with exact bytes where serialization should match.

**Why changed:** domains supplies schema metadata for collection decoding. Default logical_collections=false requires exact serialized payload bytes for the workspace reference; true only for the independent query-writer comparison decodes set-like values and checks tp_value_compare==DB_EQ. SQL and workspace collection writers may include/omit an optional domain while representing the same value. This final oracle repair is in local a142503dc; selection equality and workspace byte checks remain strict.

Source: [HEAD L60](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L60), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:60).
<a id="unit-tests-oos-sql-test-oos-sql-workspace-bytes-cpp-oosworkspacebytes-compare-clear-values"></a>

#### `OosWorkspaceBytes::compare::<clear_values>` — added (lambda)

**What:** The scope_exit cleanup lambda for the two decoded collection DB_VALUEs in compare.

**Why it exists:** An ASSERT inside collection decoding can return early, and decoded collections may own allocated memory.

**Why changed:** It clears both initialized values on every exit from the decoding block. This accompanies the a142503dc logical-collection oracle repair, rather than a production serialization change.

Source: [HEAD L100](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L100), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:100).
<a id="unit-tests-oos-sql-test-oos-sql-workspace-bytes-cpp-oosworkspacebytes-check"></a>

#### `OosWorkspaceBytes::check` — added (method)

**What:** Builds one schema/value scenario, captures the query writer’s stored row, serializes a fetched workspace object, obtains a DB_VALUE reference, and demotes the same workspace source.

**Why it exists:** A single helper applies the two independent comparisons and source-preservation assertions consistently to many encodings.

**Why changed:** Default alter=nullptr selects a current-schema comparison against the stored query image; a supplied ALTER exercises old-disk/current-workspace conversion and omits the incompatible stored-image comparison. It checks exact workspace-reference payloads, optional logical query collections, OOS selection, final width/length, preserved CHN, and unchanged source bytes. It captures actual stored OOS payloads rather than making a second copy of the input.

Source: [HEAD L121](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L121), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:121).
<a id="unit-tests-oos-sql-test-oos-sql-workspace-bytes-cpp-oosworkspacebytes-tinynullandemptyvalues"></a>

#### `OosWorkspaceBytes.TinyNullAndEmptyValues` — added (test case)

**What:** An ordinary row containing NULL, empty VARCHAR, and empty VARBIT.

**Why it exists:** Zero-length and unprofitable values must avoid unnecessary OOS work.

**Why changed:** It compares unchanged logical/serialized payloads and selection against both writers.

Source: [HEAD L218](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L218), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:218).
<a id="unit-tests-oos-sql-test-oos-sql-workspace-bytes-cpp-oosworkspacebytes-largestfirstandpreferinline"></a>

#### `OosWorkspaceBytes.LargestFirstAndPreferInline` — added (test case)

**What:** A 3,500-byte PREFER_INLINE candidate with 3,000- and 600-byte ordinary candidates.

**Why it exists:** The largest value may need to stay inline because the soft policy puts ordinary candidates first.

**Why changed:** It requires identical per-column selection and payloads across the shared workspace/DB_VALUE planners and stored query image.

Source: [HEAD L223](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L223), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:223).
<a id="unit-tests-oos-sql-test-oos-sql-workspace-bytes-cpp-oosworkspacebytes-equalsizetie"></a>

#### `OosWorkspaceBytes.EqualSizeTie` — added (test case)

**What:** Two equally sized 2,200-byte ordinary candidates.

**Why it exists:** A stable tie rule avoids writer-dependent selection.

**Why changed:** It checks that the descending attribute-index tie behavior remains shared.

Source: [HEAD L229](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L229), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:229).
<a id="unit-tests-oos-sql-test-oos-sql-workspace-bytes-cpp-oosworkspacebytes-offsetwidthshrinksafterforceddemotion"></a>

#### `OosWorkspaceBytes.OffsetWidthShrinksAfterForcedDemotion` — added (test case)

**What:** A forced 65,536-byte VARBIT next to a tiny value.

**Why it exists:** The input’s wide VOT can shrink after most bytes move out of row.

**Why changed:** It compares compact offset width/length and exact payload bytes after forced demotion.

Source: [HEAD L234](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L234), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:234).
<a id="unit-tests-oos-sql-test-oos-sql-workspace-bytes-cpp-oosworkspacebytes-compressedstringandjson"></a>

#### `OosWorkspaceBytes.CompressedStringAndJson` — added (test case)

**What:** Forced VARCHAR and JSON values plus a large VARBIT.

**Why it exists:** Serialized byte length, rather than text length or a fresh type conversion, must drive selection.

**Why changed:** It compares compressed-string and JSON payloads as bytes, demonstrating the demoter does not recompress or reserialize them.

Source: [HEAD L240](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L240), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:240).
<a id="unit-tests-oos-sql-test-oos-sql-workspace-bytes-cpp-oosworkspacebytes-collectionserializedbytes"></a>

#### `OosWorkspaceBytes.CollectionSerializedBytes` — added (test case)

**What:** A forced SEQUENCE OF INTEGER plus a large VARBIT.

**Why it exists:** Collections have multiple valid serialized forms, while the demoter must retain the workspace form exactly.

**Why changed:** The workspace-reference comparison remains byte-exact; the independent query comparison uses the final repaired logical collection oracle. Different optional domain bytes alone no longer fail the test.

Source: [HEAD L246](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L246), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:246).
<a id="unit-tests-oos-sql-test-oos-sql-workspace-bytes-cpp-oosworkspacebytes-widevotandmanyattributes"></a>

#### `OosWorkspaceBytes.WideVotAndManyAttributes` — added (test case)

**What:** One forced large VARBIT and seventy additional variable columns alternating NULL and tiny values.

**Why it exists:** Many VOT entries affect alignment and offset width independently of the largest payload.

**Why changed:** It checks attribute-location mapping, fixed/header accounting, null spans, canonical output layout, and exact source payload preservation.

Source: [HEAD L252](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L252), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:252).
<a id="unit-tests-oos-sql-test-oos-sql-workspace-bytes-cpp-oosworkspacebytes-olddiskrepresentationisconvertedbeforeworkspaceserialization"></a>

#### `OosWorkspaceBytes.OldDiskRepresentationIsConvertedBeforeWorkspaceSerialization` — added (test case)

**What:** Reads a row written before an ALTER adds a defaulted attribute, then serializes/demotes its current workspace form.

**Why it exists:** The new demoter intentionally accepts only current-representation workspace records.

**Why changed:** It verifies that existing object fetch/serialization performs schema conversion before demotion; the old stored query image is deliberately not compared against the new schema.

Source: [HEAD L264](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L264), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:264).
<a id="unit-tests-oos-sql-test-oos-sql-workspace-bytes-cpp-oosworkspacesizeboundary"></a>

#### `OosWorkspaceSizeBoundary` — added (class)

**What:** A parameterized fixture inheriting OosWorkspaceBytes and WithParamInterface<int>, with no added methods or fields.

**Why it exists:** The same byte-preservation oracle should run over multiple profitable-size and encoding/VOT boundaries.

**Why changed:** It reuses setup-free comparison and teardown behavior while supplying one payload byte count per runtime case.

Source: [HEAD L270](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L270), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:270).
<a id="unit-tests-oos-sql-test-oos-sql-workspace-bytes-cpp-oosworkspacesizeboundary-serializedsizesmatchvaluesizes"></a>

#### `OosWorkspaceSizeBoundary.SerializedSizesMatchValueSizes` — added (test template)

**What:** The parameterized test body for a forced VARBIT of GetParam() bytes, a 200-byte VARBIT, and a 255-character VARCHAR beside a fixed integer.

**Why it exists:** Eligibility uses serialized disk size, and length prefixes/VOT sizes change near small and large encoding boundaries.

**Why changed:** It calls the same check helper for all thirteen parameters; it does not assume the nominal VARBIT payload length equals its serialized span length.

Source: [HEAD L274](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L274), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:274).
<a id="unit-tests-oos-sql-test-oos-sql-workspace-bytes-cpp-encodingandvotboundaries"></a>

#### `EncodingAndVotBoundaries` — added (test instantiation)

**What:** The registration of thirteen SerializedSizesMatchValueSizes cases with values 20,21,24,25,244,248,252,3800,4040,4060,32760,32768,65536.

**Why it exists:** A TEST_P declaration is not runnable without concrete instantiations, and boundary coverage needs an explicit finite inventory.

**Why changed:** It makes each chosen size a real GoogleTest case. The guide lists the runtime names and size purpose below; 4060 is a tested value, not a claim that this HEAD implements the normative 4060-byte record target.

Source: [HEAD L280](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L280), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:280).
<a id="unit-tests-oos-sql-test-oos-sql-workspace-bytes-cpp-main"></a>

#### `main` — added (function)

**What:** The byte-comparison binary’s GoogleTest entry point with the existing SqlServerEnv global environment.

**Why it exists:** The comparison calls engine/client APIs directly and therefore needs the established in-process SQL database initialization.

**Why changed:** It initializes GoogleTest, installs SqlServerEnv, and runs the cases; it differs from the utility binary because that binary launches separate processes with private databases.

Source: [HEAD L283](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L283), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:283).

### Concrete parameterized cases

`EncodingAndVotBoundaries/OosWorkspaceSizeBoundary.SerializedSizesMatchValueSizes/N` denotes each actual GoogleTest case. All thirteen exist to run the same exact-span/reference-selection oracle at different serialized-length and VOT transitions; nominal payload size is not a direct OOS eligibility oracle.

| Runtime suffix | VARBIT payload bytes | Why this case exists and is added |
|---|---:|---|
| `/0` | 20 | Small serialized value near the 24-byte stub profitability floor; prefixes can make serialized size differ from payload size. |
| `/1` | 21 | Adjacent small-value encoding case near that floor. |
| `/2` | 24 | Nominal payload equals stub size; selection still uses the whole serialized span. |
| `/3` | 25 | Nominal payload just above the stub floor. |
| `/4` | 244 | Small-length/VOT neighborhood with other columns and header overhead included. |
| `/5` | 248 | Adjacent one-/two-byte offset neighborhood. |
| `/6` | 252 | Adjacent small serialized-length boundary. |
| `/7` | 3800 | Several-kilobyte span with fixed and other variable attributes alongside it. |
| `/8` | 4040 | Near the existing gate after accounting for record overhead. |
| `/9` | 4060 | Another near-gate payload; FORCE_OUTLINE applies independently of the gate. |
| `/10` | 32760 | Large offset/serialized-length neighborhood. |
| `/11` | 32768 | Adjacent wide-offset case. |
| `/12` | 65536 | Wide source VOT, multichunk payload, and compact output after forced demotion. |

These are boundary samples verified against the two writers, not independent hard-coded expectations that a particular nominal size must demote. The independently meaningful assertions are selection equality, exact workspace payload bytes, query logical collection equality, compact width/length, CHN preservation, and unchanged input.

## Build registration and benchmark files

### `unit_tests/oos/CMakeLists.txt` — modified

Registers and builds the utility-level GoogleTest target test_oos_workspace in the established SA_MODE test list. The executable links cubridsa/GTest and uses existing compile definitions/includes. A new CTest entry is RUN_SERIAL with TIMEOUT 240; each GoogleTest case owns its private database/registry instead of unittestdb. No function, struct, or CMake function/macro definition is added or changed.

Source: [pinned HEAD](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/CMakeLists.txt), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/CMakeLists.txt).

### `unit_tests/oos/sql/CMakeLists.txt` — modified

Adds test_oos_sql_workspace_bytes to the registered SQL CTest entries and to the shared OOS_DB fixture-required, RUN_SERIAL, TIMEOUT 30 property group. The existing SQL source glob/target loop handles its build. No function, struct, or CMake function/macro definition is added or changed.

Source: [pinned HEAD](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/sql/CMakeLists.txt), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/sql/CMakeLists.txt).

### `unit_tests/oos/scripts/benchmark_workspace_oos.sh` — added

Adds a manual Release benchmark outside CTest: INSTALL OUTPUT LABEL [REPEATS], three repeats by default, with 100,000 rows of 48-byte payloads and 10,000 rows of 5,000-byte payloads. Each sample has a private database/configuration, uses real loaddb -S, records elapsed/user/system CPU CSV through /usr/bin/time, verifies values/row bounds, saves SHOW HEAP OOS output, deletes successful sample databases, and retains inputs/outputs/measurements. mkdir requires a new output directory. There are no shell function definitions; the loops and awk programs are top-level script logic. The final local commit corrects its license template. Merely adding the script establishes no measured performance claim.

Source: [pinned HEAD](https://github.com/CUBRID/CUBRID/blob/a142503dc1a6f85b498a425aa58d6a78136ccc6b/unit_tests/oos/scripts/benchmark_workspace_oos.sh), [local HEAD](/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa/unit_tests/oos/scripts/benchmark_workspace_oos.sh).

## Suggested reviewer path and validation scope

1. Start with `LOCATOR_FORCE_FLAG` and the private `locator_update_force` declaration. Confirm the all-zero public insert default and private update `from_workspace=false` preserve unmarked callers.
2. Follow `xlocator_force` into INSERT, reserved-OID UPDATE and multi-update. Check mode gating, pruning order, partition movement, and the existing rollback boundaries.
3. Read the shared planner next to the deleted base planner. Separate representation/sizing extraction from selection behavior; confirm the conservative in-loop header estimate and tie order stay intentional.
4. Walk the byte demoter from validation through plan construction, pre-write bigone rejection, OOS publication, direct byte-span inserts, record assembly and cleanup. Review source, cache, output-buffer, and persistent-chain lifetimes separately.
5. Read `OosWorkspaceBytes::compare` before its tests. Exact bytes remain required against the workspace-derived reference; query collections compare decoded values because optional domain encoding can differ. Confirm the test still checks OOS selection and source immutability.
6. Read the real utility fixture and its cases for evidence of actual SA loading, reserved references, filtered/full rollback, partitions, LOB files, multichunk storage and successful no-logging loading. Remember `Oos_num_recs` counts physical chunks, so a multichunk value can contribute more than one.
7. Use the separate CI report to assess failed-TC attribution at `f037616cd`. The local test-oracle/header repair cannot retrospectively change the outcome of a run executed at the earlier commit.

For a configured and installed CUBRID build with the OOS test options enabled, the two new CTest entries are directly addressable without personal tooling:

```sh
ctest --test-dir <build-directory> --output-on-failure \
  -R '^(test_oos_workspace|test_oos_sql_workspace_bytes)$'
```

The utility binary requires installed `cubrid` and `csql` from the intended build on PATH and a usable library/configuration environment. The SQL byte binary uses the existing `OOS_DB` fixture. A green focused run shows these routes and oracles passed on that build; it does not establish whole-corpus equivalence, HA/replication correctness, or deferred feature conformance.

## Completeness and evidence limits

The inventory was built from the exact eleven-file `git diff fb567a629cdb390fff920542173fa36f454c74a0 a142503dc1a6f85b498a425aa58d6a78136ccc6b` and checked against every diff hunk. All changed production function bodies, deleted helpers, moved type occurrences, changed public/private declarations, five force bits, both new test fixture classes and their helpers, the derived parameter fixture, cleanup lambda, all test definitions/instantiations, both `main` functions, two CMake files and the benchmark are represented. GNU formatting guards and the added include are accounted for by their owning declarations/file; they do not define extra functions. There are no new/deleted production methods hidden behind a class rename.

The JSON contains separate base/head declaration and definition ranges, statuses, explanations and concrete runtime test identities. It is a manually audited lexical inventory, not a compiler AST dump. Generated GoogleTest implementation classes/functions are represented by their defining TEST_F/TEST_P macros and concrete runtime instances rather than their framework-generated names. This avoids inflating coverage with implementation details of GoogleTest while preserving every authored test case.

Earlier CBRD-27424 notes describe a previous decode/re-encode candidate and a Python CLI harness; they are historical supporting evidence, not the current implementation. This HEAD uses original serialized spans and GoogleTest utility coverage. Engine-internal explanatory docs removed after the CI commit are not recreated here; the durable review material lives in this documentation repository. [historical design note](CBRD-27424-sa-workspace-oos_e24b458_codex.md).
