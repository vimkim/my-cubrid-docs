# Work456: OOS supplementation inventory

Date: 2026-10-21, Asia/Seoul. Audience: the author planning Work456 and its six supplementation milestones.

The question is which requested tests already exist and what still needs a completion rule.
Syntax and semantic tests already exist. The main uncovered dimensions are the systematic operation/HAS_OOS matrix, some grammar and utility cases, exact limits, repeated storage workloads, and large indexed OOS values.
This is a static inventory. No build, database, testcase, or CI run was started for this report.
The user answered Q1-Q6. Final shared-understanding confirmation remains pending.
This report does not authorize implementation or claim that Work458 is complete.

## Evidence identities

| Component | Inspected revision | Evidence limit |
| --- | --- | --- |
| Handover engine, PR8128 | `1ef86a7efa34002e971b1b30bcf5d451e9db441b` | Pre-existing dirty `cubrid-cci` was preserved. |
| Public TC, `tc/pr-8128`, PR3688 | `df8596dd999e825b1ec9812a735bbe01e50ac715` | Clean published checkout. |
| Private TC, `tc/pr-8128`, PR4365 | `5c9d8de1a916ae0acbddc8409770b51fd31da13b` | Clean published checkout, including Work401 additions. |
| SA-loaddb fix, PR7925 | `6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f` | Separate branch with its own local and CI evidence. |
| Deferred-write dependency, PR7927 | `4a4d069c21fc19f14337efceca512b726724ecd8` | Separate branch. Earlier results do not qualify this newer head. |
| Shared destination, `feature/oos-merge` | `fb567a629cdb390fff920542173fa36f454c74a0` | Does not contain the three source heads above. |

The normative source is `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md`, last updated 2026-10-08.
The complete file was read with unchanged SHA-256 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`.
Its accepted requirements govern expectations. Source establishes implementation at the listed revision.
Live JIRA lookup reports CBRD-26659 as Develop, Minor, unresolved, assigned to Daehyun Kim.

Source navigation works through text search.
The source environment check reports unset `PRESET_MODE` and a broken `compile_commands.json` link to `build_preset_debug_gcc/compile_commands.json`.
Those findings limit build and language-server readiness. They do not prevent this static inventory.
Before native execution, select and verify a source-matching build through the maintained build workflow.

## Completed work remains completed

[Work109's specification](ci-replan/spec.md) covers the earlier developer-owned SQL and shell delivery.
Its initial profile is Linux, 16 KiB, optdebug. SQL and shell timing guides are separate and informal.
It excluded new C++ families and performance qualification from that earlier scope.
Work456 adds C++ supplementation and storage efficiency to the earlier scope.
The original intake requested indexed-value performance. The user deferred performance comparison and thresholds on 2026-10-21, retaining large OOS PK/UNIQUE functionality.

[Work401](coverage-additions-work401-20261016.md) delivered four shell additions and dispositions for 29 incomplete or failed matrix rows.
Its passing evidence is 19 cases and a separate one-case sentinel invocation, with zero skips in each.
It is not one 20-case run. Four intended regressions still fail at their recorded revision.
The latest handover CI used private TC `9a075340f`, before the Work401 additions. It cannot qualify the later additions.

## Six-area inventory

| Work item | Existing evidence | Supplement still needed |
| --- | --- | --- |
| 457: syntax, semantics, SHOW, utilities | Policy CREATE/LIKE/MODIFY/CHANGE/reset cases, invalid type/context cases, metadata checks, and both SHOW permission checks. | Enumerate malformed/duplicate clauses, supported domains and contexts, SHOW argument/object/hierarchy behavior, and policy preservation through utility roundtrips. |
| 458: operations and record HAS_OOS matrix | 18 dedicated public OOS SQL cases and paired physical shell cases cover many reads, writes, constraints, schema changes, and utilities. | Map every supported OOS-relevant operation to actual HAS_OOS records and records without HAS_OOS. Record applicable input/output states and transitions. Attach flag evidence, exact assertions, and revision-specific receipts. Small/large is not a matrix axis. |
| 459: C++ gaps and SQL duplication | 29 registered OOS binaries contain 302 test declarations. The subtree is unchanged from the older inventory. Internal assertions cover dispatch, bounds, identities, allocation faults, page counts, and reclaim controls. | Record retain/add/migrate/remove per case. A removed case needs an equivalent verified replacement in the required execution mode. No removal is justified by matching SQL text alone. |
| 460: limits and limit+1 | Existing cases cover the serialized 24-byte floor and next aligned value, chunk capacity and its successor, VOT neighbors, and broad bigone acceptance/rejection. | Inventory all introduced limits and units. Add exact missing boundaries, distinguish aligned successors from one byte, and separate overflow transitions from rejected maxima. |
| 461: efficiency, reclaim, fragmentation, churn | Chunk-drain, survivor, snapshot, reclaim, and internal growth-sweep cases exist. The correct product page-return assertion still fails in retained evidence. | Execute repeatable INSERT/DELETE and INSERT/UPDATE/DELETE workloads independently of earlier failing assertions. Measure page return, reuse, growth, and packing trends at equal live data. Define the observation and completion rules. |
| 462: large OOS PK/UNIQUE functionality | Existing read and constraint fixtures use narrow integer keys beside OOS payloads. SA loader timing covers a different workload. | Index the OOS-backed value itself. Verify supported key combinations and applicable create/build, read/write, duplicate, NULL, error/rollback, and value-preservation behavior. Performance comparison and thresholds are deferred. |

The bounded search found no dedicated MERGE, REPLACE, duplicate-key UPDATE, foreign-key/cascade, or full-payload set-operation coverage in the current OOS SQL directory.
Q3 accepts these families into the supported OOS-relevant operation inventory. Reuse sufficient tests from the wider repository when found.
This bounded search does not claim absence from the whole testcase repository.

The accepted [CBRD-26067](https://jira.cubrid.org/browse/CBRD-26067) and [CBRD-26979](https://jira.cubrid.org/browse/CBRD-26979) contracts define FORCE_OUTLINE placement, eligibility, DDL, policy persistence, and nonretroactive ALTER.
Their omission from the canonical context is a documentation-completeness gap, rather than an absence of accepted behavior.
Older ticket text uses a 16-byte floor. Apply the symbolic profitability rule with the current accepted 24-byte stub.
FORCE_INLINE remains a separate follow-up and is not current supported syntax.

## Decisive source and testcase references

Paths in this section are relative to the repositories and revisions in the identity table.

- Public `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_storage_policy.sql:8` covers policy DDL. Lines 26-49 cover invalid domains and contexts.
- Private `shell/_40_guava/cbrd_26659_schema_policy/cases/cbrd_26659_schema_policy.sh:178` checks policy metadata. Lines 194-226 check rejected ALTER preservation and physical policy behavior.
- Private `shell/_40_guava/cbrd_26659_jdbc_storage/cases/cbrd_26659_jdbc_storage.sh:32` separates actual JDBC values from CSQL physical and SHOW permission observations.
- Private `shell/_40_guava/oos_utility/utility_roundtrip.sh:110` uses default policies. Its current schema oracle does not establish a PREFER_INLINE/FORCE_OUTLINE roundtrip.
- Source `unit_tests/oos/sql/test_oos_sql_crud.cpp:224` asserts batching counters. `test_oos_sql_visible_version.cpp:51` checks direct fetch behavior, while line 99 checks UPDATE without whole-row Expand.
- Source `unit_tests/oos/test_oos_real_vacuum_server.cpp:788` tests exact stored chunk capacity and its successor. Its helper appends a NUL, which affects the input-to-stored-length calculation.
- Source `src/storage/heap_file.c:12840` and line 12873 still use the raw quarter-page gate. The accepted 16 KiB target is 4060 bytes. Preserve this conformance difference.
- Source `src/storage/btree_load.h:162` describes the in-page key threshold. `src/storage/btree.c:17315` selects overflow storage. This is a B-tree representation transition, not an OOS value rejection maximum.

## Current fixes and physical evidence

Handover, SA-loaddb, and deferred-write results belong to separate source revisions.
The [accepted SA decision](../cbrd-27424/sa-inline-preservation-decision-20261017.md) preserves values, meaningful headers and CHN, policies, ownership, transactions, and buffer lifetime.
It supersedes complete original-byte and unused-padding identity. Do not restore that superseded oracle while deduplicating tests.
The [recovered SA CI report](../cbrd-27424/ci_analysis_report_6a487cdb6_collector_recovery_codex.md) resolves the old collector limitation and records six shell failures.
Combined source acceptance remains separate from these branch-specific results and from Work456 supplementation.

SHOW reports allocated OOS pages and aggregate scanned chunk statistics.
Its derived unused bytes are aggregate slack. They do not establish per-page free-space distribution or exact fragmentation.
Returning an empty OOS page to the file manager does not imply truncating an operating-system volume file.
The specification does not require across-page compaction.

For Work462, prove that the indexed attribute itself is OOS-backed.
A record flag alone does not identify which attribute has a stub when several attributes are eligible.
OOS heap chains and B-tree overflow-key files need separate measurements.

### Per-record HAS_OOS observation

Current source names the bit `OR_RECORD_FLAG_HAS_OOS`, with value `0x08`, in `src/base/object_representation_constants.h:158`.
`OR_RECORD_HAS_OOS(recdes.data)` and `heap_recdes_contains_oos` inspect a stored-form record.
The existing integration seam in `unit_tests/oos/sql/test_oos_sql_visible_version.cpp:51` executes SQL and obtains real records through `heap_scanrange_next`.
It can support per-record assertions without new product instrumentation.

The product diagnostic hint `SELECT_RECORD_INFO` exposes `t_flags` alongside ordinary attributes.
The source path is `src/parser/parse_tree.c:126`, `src/parser/name_resolution.c:5889`, and `src/storage/heap_file.c:20710`.
This is static evidence of a candidate observer. The query has not been executed for this inventory.
Diagnostic scans inspect physical slots and can bypass ordinary visible-version filtering.
Correlate logical identity, record type, and transaction state before crediting a current logical row.
Expanded copies clear HAS_OOS, so inspect the stored representation.
Table-level SHOW statistics do not establish an individual record's flag.
After DELETE, an absent row is not a record with a clear flag.

## Accepted completion rule and scope decisions

The user accepted Q1 on 2026-10-21.
Work456 can complete when every required test in the six agreed areas is delivered and executed against an independent intended oracle.
Each result needs revision-specific evidence.
Reproducible engine defects may remain linked to separate fixes and recorded as failures.
Failed cases receive no passing-coverage credit.
Missing tests, unexecuted required cases, and unclear expected behavior still prevent completion.
If an earlier failure prevents required churn from running, that churn remains a delivery gap.

| Decision | User response on 2026-10-21 | Accepted scope |
| --- | --- | --- |
| Q2: record classification | Replace the size proposal. | Classify actual records by HAS_OOS set or clear. Remove small/large as a matrix axis. |
| Q3: operation population | Yes. | Enumerate all supported OOS-relevant families and account for every applicable record-state cell. Explain inapplicable combinations. |
| Q4: boundary methods | Yes. | Use exact byte limit/+1 where possible and the next representable serialized size under alignment. Impractical maxima may use C++ guard tests without full-size storage credit. |
| Q5: storage assessment | Yes. | Assert survivor correctness, eligible page return, and reclaim before unnecessary sector growth. Compare repeated-workload space and fragmentation trends with equivalent fresh heaps. |
| Q6: performance comparison | No. Defer it. | Verify large OOS PK/UNIQUE functional behavior only. Baseline selection, throughput/latency comparison, and regression thresholds are deferred. |

### User-approved exclusion

On 2026-10-21, the user removed performance qualification from the scope required to complete this supplement.
The original performance request remains preserved in the intake.
Functional PASS does not establish performance PASS. Future performance work needs its own acceptance decision.
Removing the small/large matrix axis does not remove size-dependent boundary cases from Work460.

Final shared-understanding confirmation remains pending before specification or implementation.
HA Work463 remains deferred. Work371 remains the separate integration/readiness effort.
No new testcase tickets, expected-answer changes, source integration, publication, or CI trigger occurred in this planning phase.
