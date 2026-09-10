# CBRD-26659 — Requirement catalogue and traceability identity (ticket 12)

> Observed: 2026-09-10 (KST). Engine baseline: `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` (`origin/feat/oos`, ticket 11). Normative context: HEAD `f6543de680b91ae357466b72a983f982892859cd` plus the uncommitted working copy, sha256 `c9daf3c4ed25e16356ebf3c79c55f6bb7391d76c5664675a9aaf55cd5ac11698` (snapshot in [`ticket11-evidence/normative-snapshot/`](ticket11-evidence/normative-snapshot/)).
> Author: Claude Fable 5.1, session `session_01Wq38qC19cw3fGeq1oCFqjJ`, for the [Adversarial OOS testcase campaign](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/spec.md) ticket 12.
> Machine-readable source of truth: [`catalogue/requirements.json`](catalogue/requirements.json) and [`catalogue/scenario-map.json`](catalogue/scenario-map.json), validated by [`tools/check_campaign_records.py`](tools/check_campaign_records.py). The tables below are rendered from those files by [`tools/render_docs.py`](tools/render_docs.py); edit the JSON, not the tables.
> Companion: [traceability schemas](CBRD-26659-traceability-schemas_f4299ac_claude.md) (manifest, matrix, attempt record, replay bundle).

Vocabulary follows the [docs glossary](../../CONTEXT.md): Requirement ID, Normative citation, Coverage family, Assertable requirement, Observation-only requirement, OOS-path evidence, Capability gap, Specification gap, Engine defect, Delivery gap, Accepted exclusion, Flagged promotion, Outcome.

## 1. How to use this catalogue

An implementer picking up a case ticket looks up the requirement by ID and reads, in this order: the **statement** (what must hold, in normative wording), the **status** (whether the expectation may be asserted at the pin), the **authority note** (how to justify the oracle), the **pinned observation** (what ticket 11 saw the pinned engine do, which is evidence and never the expectation), and the **attack dimensions** (what the cases under this requirement must cover). Every case, manifest row, matrix row and report line cites at least one Requirement ID. The §6 scenarios of the normative context are mapped in section 8; they are a mandatory input, not the coverage ceiling.

## 2. Identity rules

**Requirement ID.** `OOS-<FAMILY>-<NN>` with family codes `REP` (Representation), `SQL` (SQL operations), `RD` (Read paths), `SCH` (Schema and utilities), `CL` (Concurrent lifetime), `DUR` (Durability), `OPS` (Operational features), `RES` (Resource pressure). IDs are issued once and never renumbered, reused or deleted. A requirement that turns out to be wrong is kept with an updated statement and status; a requirement that must move family is superseded by a new ID and its old entry says so. The family code in the ID records the family at issue time; the `family` field is authoritative.

**Normative citation.** Exactly one per requirement, of one of three kinds: a `context-heading` of `OOS-CONTEXT.md`, an `adr` (ADR-0001 to ADR-0004), or an `accepted-design` (an explicitly accepted CBRD design as recorded in the context: CBRD-27057, CBRD-26950, CBRD-27230, CBRD-26786, CBRD-26830, CBRD-26608). Every citation carries the pinned context revision `f6543de…` **and** the content hash of the cited document, because the 24-byte wording exists only in the uncommitted working copy and ADR-0004 is untracked (ticket 11 §3). When the pin moves, citations update; IDs do not.

**Status.** One of four values, with a fixed mapping to the glossary gap kinds and to the per-attempt outcome a case records at the pin:

| Requirement status | Meaning | Gap kind | Outcome cases record at the pin |
|---|---|---|---|
| `assertable` | Expected behavior fixed by an independently justified oracle | none | PASS or FAIL (SKIP with reason when deliberately omitted) |
| `observation-only` | Implemented behavior without established acceptance; recorded, never asserted as correct | none | PASS or FAIL on the logical checks; the observed behavior is written to the evidence, never to the answer |
| `UNSUPPORTED` | Accepted design absent at the pinned engine | Capability gap | UNSUPPORTED; engine output retained as evidence, never promoted |
| `BLOCKED` | Authority for the required behavior is unclear or disputed | Specification gap | BLOCKED; authority question recorded; unaffected cases proceed |

Ticket 11's baseline record wrote "cases take the BLOCKED outcome" for the accepted-but-unimplemented findings (a, d, e, f). This catalogue refines that per ticket 12's criterion: those are `UNSUPPORTED` requirements (the tested build lacks the capability, which is the spec's definition of UNSUPPORTED), while `BLOCKED` is reserved for Specification gaps. Both are non-pass and both stay visible in the matrix; only the word changes.

## 3. Authority policy, encoded per requirement

Each requirement carries `authority.policy`, which encodes the three policies accepted in the [specification-authority decision](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/issues/10-specification-authority.md):

| Policy | Rule | Used by status |
|---|---|---|
| `assert` | The expectation is an exact whole value, a transaction-state model or a documented guarantee, justified before the engine is consulted. Explicitly accepted superseding decisions govern over historical wording. | assertable |
| `assert-after-eligibility` | Physical reclamation expectations are asserted only after proving the page or chunk is eligible (empty, a data page, non-legacy file, no active writer behind the LSA gate) and safe (no snapshot, rollback or recovery still needs it). Before eligibility, release is a failure candidate; after eligibility, non-release within the bounded wait is a failure candidate. Never an unconditional zero-page assertion. | assertable |
| `observe` | Undocumented or unaccepted implemented behavior is recorded at the tested revision and never asserted as correct. Logical correctness and error paths around it are still asserted. | observation-only |
| `withhold` | No expectation is fixed. Engine output is retained as evidence and never promoted to an answer. Universal value-integrity, rollback and visibility checks continue under the related assertable requirements. | BLOCKED, UNSUPPORTED |

Promotion rule that follows: an answer promotion for a case that touches a `BLOCKED` requirement, an `observation-only` requirement, or any observed-versus-normative disagreement is a **Flagged promotion** and needs the user's sign-off; unflagged promotions need independent agent review only.

<!-- BEGIN GENERATED: policy -->
| Policy | Count | Requirements |
|---|---|---|
| assert | 42 | `OOS-REP-01`, `OOS-REP-02`, `OOS-REP-04`, `OOS-REP-06`, `OOS-REP-07`, `OOS-REP-08`, `OOS-REP-09`, `OOS-REP-10`, `OOS-REP-11`, `OOS-SQL-01`, `OOS-SQL-02`, `OOS-SQL-05`, `OOS-SQL-06`, `OOS-RD-01`, `OOS-RD-02`, `OOS-RD-03`, `OOS-SCH-01`, `OOS-SCH-02`, `OOS-SCH-03`, `OOS-SCH-04`, `OOS-SCH-05`, `OOS-CL-01`, `OOS-CL-03`, `OOS-CL-04`, `OOS-CL-09`, `OOS-CL-10`, `OOS-CL-11`, `OOS-CL-13`, `OOS-DUR-01`, `OOS-DUR-02`, `OOS-DUR-03`, `OOS-DUR-04`, `OOS-DUR-05`, `OOS-DUR-06`, `OOS-DUR-08`, `OOS-OPS-01`, `OOS-OPS-02`, `OOS-OPS-04`, `OOS-RES-01`, `OOS-RES-02`, `OOS-RES-03`, `OOS-RES-04` |
| assert-after-eligibility | 3 | `OOS-CL-02`, `OOS-CL-05`, `OOS-CL-06` |
| observe | 5 | `OOS-REP-12`, `OOS-SQL-03`, `OOS-SCH-06`, `OOS-OPS-06`, `OOS-RES-05` |
| withhold | 12 | `OOS-REP-03`, `OOS-REP-05`, `OOS-REP-13`, `OOS-REP-14`, `OOS-SQL-04`, `OOS-SQL-07`, `OOS-CL-07`, `OOS-CL-08`, `OOS-CL-12`, `OOS-DUR-07`, `OOS-OPS-03`, `OOS-OPS-05` |
<!-- END GENERATED: policy -->

## 4. Summary by coverage family

All eight mandatory families are present. Counts are by requirement, not by case.

<!-- BEGIN GENERATED: summary -->
| Family | Requirements | assertable | observation-only | UNSUPPORTED | BLOCKED |
|---|---|---|---|---|---|
| Representation | 14 | 9 | 1 | 2 | 2 |
| SQL operations | 7 | 4 | 1 | 1 | 1 |
| Read paths | 3 | 3 | 0 | 0 | 0 |
| Schema and utilities | 6 | 5 | 1 | 0 | 0 |
| Concurrent lifetime | 13 | 10 | 0 | 1 | 2 |
| Durability | 8 | 7 | 0 | 0 | 1 |
| Operational features | 6 | 3 | 1 | 2 | 0 |
| Resource pressure | 5 | 4 | 1 | 0 | 0 |
| **Total** | 62 | 45 | 5 | 6 | 6 |
<!-- END GENERATED: summary -->

## 5. Catalogue

Each family lists its requirements as a table, then each requirement in full. `Seam` is the specification's placement (public CTP SQL runner, private CTP shell runner, or either); a case ticket may record a deviation in the matrix row.

<!-- BEGIN GENERATED: requirements -->
#### Representation

| ID | Title | Status | Policy | Seam | Citation |
|---|---|---|---|---|---|
| `OOS-REP-01` | Records at or below the gate stay inline | assertable | assert | public-sql | context-heading: §1 Trigger Conditions — Largest-First Demotion (CBRD-26776; physical target CBRD-27057), step 1 (record gate) |
| `OOS-REP-02` | Largest-first demotion above the gate | assertable | assert | public-sql | context-heading: §1 Trigger Conditions — Largest-First Demotion (CBRD-26776; physical target CBRD-27057), step 3 (largest-first loop) |
| `OOS-REP-03` | Four-record physical target (CBRD-27057) | UNSUPPORTED | withhold | public-sql | accepted-design: CBRD-27057 four-record physical target — spec note (2026-07-13) and §1 Trigger Conditions — Largest-First Demotion (CBRD-26776; physical target CBRD-27057) |
| `OOS-REP-04` | Eligibility floor where pinned and normative agree | assertable | assert | public-sql | context-heading: §1 Trigger Conditions — Largest-First Demotion (CBRD-26776; physical target CBRD-27057), step 2 (eligibility) |
| `OOS-REP-05` | 24-byte identity layout (CBRD-26950) | UNSUPPORTED | withhold | either | accepted-design: CBRD-26950 identity layout — Identity layout reconciliation (2026-09-09), §2 Record Binary Layout and §2 Multi-Chunk OOS Chain |
| `OOS-REP-06` | Type-agnostic eligibility including LOB locators (ADR-0002) | assertable | assert | public-sql | adr: ADR-0002 BLOB/CLOB locator columns remain OOS-demotable (type-agnostic eligibility) |
| `OOS-REP-07` | Multi-chunk value chains | assertable | assert | public-sql | context-heading: §2 Multi-Chunk OOS Chain |
| `OOS-REP-08` | OOS + bigone rejection (CBRD-26937) | assertable | assert | public-sql | context-heading: §1 OOS + bigone Rejection (CBRD-26937) |
| `OOS-REP-09` | NULL and empty eligible values | assertable | assert | public-sql | context-heading: §1 Trigger Conditions — Largest-First Demotion (CBRD-26776; physical target CBRD-27057), step 2 (eligibility) |
| `OOS-REP-10` | Many OOS-backed attributes in one record | assertable | assert | public-sql | context-heading: §2 Record Binary Layout |
| `OOS-REP-11` | Inline and OOS transitions across writes | assertable | assert | public-sql | context-heading: §1 Trigger Conditions — Largest-First Demotion (CBRD-26776; physical target CBRD-27057) |
| `OOS-REP-12` | Placement hints: logical correctness only | observation-only | observe | public-sql | context-heading: §5 Proposed Design Discussions — Per-column inline preference (CBRD-26912, proposed) |
| `OOS-REP-13` | Placement-hint policy authority | BLOCKED | withhold | public-sql | context-heading: §5 Proposed Design Discussions — Per-column inline preference (CBRD-26912, proposed) |
| `OOS-REP-14` | Stub-size terminology: 16, 20 or 24 bytes | BLOCKED | withhold | either | context-heading: §5 Limitations (Milestone 1) — Bulk-externalize row (profitable threshold wording) |

**`OOS-REP-01` — Records at or below the gate stay inline** (assertable, assert)  
A heap record whose serialized size does not exceed the OOS inline target is stored entirely inline: no attribute is demoted, HAS_OOS stays clear, and a class that has never demoted a value has no OOS file.

- Authority: Assertable only where the pinned gate (DB_PAGESIZE/4) and the normative four-record target agree. Schema-A BIT VARYING N ≤ 939 / 1,963 / 4,011 (4/8/16 KiB) stays inline under both; the band above is OOS-REP-03.
- Pinned observation (ticket 11): Pinned gate 1,014 / 2,038 / 4,086 B versus normative 988 / 2,012 / 4,060 B (ticket 11 §5.1). No OOS file is created until the first demotion (Has_oos_file 0).
- Attack dimensions: 4, 8 and 16 KiB pages; one and many variable columns; NULL and empty eligible values; VOT 1-to-2-byte transition (schema A: N = 92)
- Related: `OOS-REP-03`, `OOS-REP-09`

**`OOS-REP-02` — Largest-first demotion above the gate** (assertable, assert)  
When a record exceeds the OOS inline target, eligible variable values are demoted one at a time in descending size until the record is at or below the target or candidates are exhausted; smaller eligible values may remain inline, and every value reads back exactly.

- Authority: Assertable above both gates (schema-A N ≥ 964 / 1,988 / 4,036). The number of demoted values is observable per class through SHOW HEAP OOS chunk counts on an isolated table; per-attribute placement needs a paired debug or instrumented run. At the pin the SQL INSERT path writes no oos.log line (ticket 11 §6).
- Pinned observation (ticket 11): Order and early stop implemented in heap_attrinfo_determine_disk_layout; the stop compares against the pinned gate, not the normative target.
- Attack dimensions: two unequal eligible columns (only the largest demoted); equal-size ties; candidates exhausted above the target; over-demotion by one value near a VOT width boundary (conservative estimate); bulk insert of varying sizes
- Related: `OOS-REP-03`, `OOS-SQL-01`

**`OOS-REP-03` — Four-record physical target (CBRD-27057)** (UNSUPPORTED, withhold)  
The record gate and the demotion stop use the PG-style four-record physical target derived from heap_nonheader_page_capacity(), excluding heap unfill: 988 / 2,012 / 4,060 B at 4 / 8 / 16 KiB.

- Authority: Accepted design absent at the pin. Cases in the disputed band take the UNSUPPORTED outcome; their engine output is retained as evidence and never promoted to an answer. Ticket 11 recorded this as a Capability gap of the pinned engine.
- Accepted design absent at the pin: CBRD-27057 four-record physical target (heap_oos_inline_target_size)
- Pinned observation (ticket 11): heap_file.c:12350 and :12383 compare against DB_PAGESIZE / 4; heap_oos_inline_target_size does not exist. Disputed band schema-A N in [940, 963] / [1,964, 1,987] / [4,012, 4,035] stays inline at the pin.
- Attack dimensions: both sides of the normative boundary at each page size; unfill-independence
- Related: `OOS-REP-01`, `OOS-REP-02`

**`OOS-REP-04` — Eligibility floor where pinned and normative agree** (assertable, assert)  
A variable value whose serialized size is at or below 16 B is never demoted, and a variable value whose serialized size exceeds 24 B is a demotion candidate whenever its record exceeds the gate.

- Authority: Both floors agree outside the [17, 24] B serialized band. For BIT VARYING that is logical N ≤ 15 (never demoted) and N ≥ 24 (candidate). The band N in [16, 23] is OOS-REP-05.
- Pinned observation (ticket 11): 15-byte value stays inline; 16-, 23- and 24-byte values are demoted (Oos_recs_sumlen 36 / 40 / 44). Normatively only the 24-byte value may be demoted.
- Attack dimensions: fixed BIT column pushes the record over the gate so only the small variable value is a candidate; 4, 8 and 16 KiB
- Related: `OOS-REP-05`

**`OOS-REP-05` — 24-byte identity layout (CBRD-26950)** (UNSUPPORTED, withhold)  
The OOS inline stub is 24 bytes (head OOS OID, full length, packed identity stamp), each chunk header is 24 bytes with a raw LOG_LSA stamp captured under the write latch, the eligibility floor is strictly greater than 24 B, and deletes are identity-checked against the stamp.

- Authority: Accepted design absent at the pin (PR #7695 unmerged). Physical expectations that depend on the 24-byte layout are withheld; their cases take the UNSUPPORTED outcome. Universal value-correctness checks continue under OOS-CL-04.
- Accepted design absent at the pin: CBRD-26950 identity layout (24-byte stub and chunk header, identity-checked delete)
- Pinned observation (ticket 11): OR_OOS_INLINE_SIZE = 16 (object_representation.h:466); oos_record_header is 16 B (oos_file.hpp:28-33); oos_delete takes no expected identity. Boundaries shift by 8 B: single-chunk max 16,288 pinned vs 16,280 normative at 16 KiB; eligibility band N in [16, 23] demoted at the pin.
- Attack dimensions: eligibility band N in [16, 23]; single-to-multi chunk boundary under a 24-byte header; OOS + bigone rejection threshold under a 24-byte stub; stamp uniqueness across slot reuse with logging enabled
- Expected engine findings: CBRD-26950
- Related: `OOS-REP-04`, `OOS-REP-07`, `OOS-REP-08`, `OOS-CL-04`

**`OOS-REP-06` — Type-agnostic eligibility including LOB locators (ADR-0002)** (assertable, assert)  
Eligibility depends only on the value being variable-length and larger than the floor; BLOB/CLOB locator values demote like any other variable value with LOB copy semantics preserved, and deleting or vacuuming a demoted locator never removes the external LOB payload.

- Authority: Whole-value equality per type. String types are compressed and unsuitable for size boundaries; use them for correctness, not for boundary arithmetic.
- Attack dimensions: BIT VARYING, VARCHAR (compressed and uncompressed), VARNCHAR, JSON, SET/MULTISET/SEQUENCE, BLOB/CLOB locators; character sets and collations; many locator columns (bug_xdbms3693 shape); INSERT ... SELECT copying of LOB rows; stub-writer S_DOESNT_FIT retry after locator size drift
- Related: `OOS-REP-02`

**`OOS-REP-07` — Multi-chunk value chains** (assertable, assert)  
A value larger than one page's maximum single-chunk payload is stored as a chain of chunk records, inserted tail first, and is read back complete and byte-identical; total_data_length excludes every chunk header.

- Authority: Assert value equality and, on an isolated table, the chunk count from SHOW HEAP OOS. The exact split boundary is pinned-layout specific (16-byte header); the normative 24-byte boundary is OOS-REP-05.
- Pinned observation (ticket 11): Largest single-chunk N = 3,995 / 8,091 / 16,283; two chunks from N = 3,996 / 8,092 / 16,284 (Oos_num_recs 2, Oos_num_user_pages 3).
- Attack dimensions: one byte either side of the split; three or more chunks (50 KiB+); mixed single- and multi-chunk values in one table; distinct byte pattern per chunk to detect cross-row mixing
- Related: `OOS-REP-05`, `OOS-DUR-01`

**`OOS-REP-08` — OOS + bigone rejection (CBRD-26937)** (assertable, assert)  
An INSERT or UPDATE whose record would still exceed heap_Maxslotted_reclength after demotion while containing an OOS inline stub is rejected with ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE before any chunk is written; no row is stored and no OOS value chain is created. A non-OOS bigone record, or an OOS-backed record left between the target and the bigone threshold, succeeds.

- Authority: Assert the rejection, the absence of the row and the absence of an OOS file or new chunks. Expected-error answers use the pinned error code and message text (ticket 11 §4 g); the context's -1375 is drift, reported to the context maintainer.
- Pinned observation (ticket 11): Error code is -1382 at the pin (error_code.h:1782); message reports 'size (N bytes) still exceeds the maximum record size (M bytes)'. Schema B: largest accepted F = 3,888 / 7,984 / 16,176; smallest rejected F = 3,889 / 7,985 / 16,177 with a 16-byte stub.
- Attack dimensions: fixed BIT(n) plus one OOS-backed column; many small (≤ floor) variable values; UPDATE that grows a fixed column past the threshold; non-OOS bigone control
- Related: `OOS-REP-05`

**`OOS-REP-09` — NULL and empty eligible values** (assertable, assert)  
A NULL or zero-length value in an OOS-eligible column is never demoted and reads back as NULL or as the empty value.

- Authority: Follows from eligibility requiring a serialized size above the floor. Assert on records that otherwise exceed the gate so demotion of siblings is exercised.
- Attack dimensions: NULL beside demoted siblings; empty BIT VARYING and empty VARCHAR beside demoted siblings; UPDATE to NULL and back
- Related: `OOS-REP-01`

**`OOS-REP-10` — Many OOS-backed attributes in one record** (assertable, assert)  
A record may carry many OOS inline stubs (ten or more); HAS_OOS is set once, each demoted attribute's VOT entry carries IS_OOS, and every value reads back exactly.

- Authority: Flags are observable only through debug or diagnostic channels; the SQL seam asserts values and chunk counts. An OOS-bearing record never reaches 4-byte VOT entries (structural exclusion, ticket 11 §5.1).
- Attack dimensions: 10+ demoted attributes; VOT 1-to-2-byte width transition; fixed and variable columns interleaved; bound-bit bytes with 32+ fixed columns
- Related: `OOS-REP-02`

**`OOS-REP-11` — Inline and OOS transitions across writes** (assertable, assert)  
An attribute's representation may move between inline and OOS on each INSERT or UPDATE as the record size crosses the target; the logical value is never affected by the transition.

- Authority: Assert values across grow/shrink sequences; placement changes are evidence, not the oracle.
- Attack dimensions: grow a value past the gate then shrink it below; change a sibling so a previously inline value becomes the largest candidate; repeated transitions on one row
- Related: `OOS-SQL-02`

**`OOS-REP-12` — Placement hints: logical correctness only** (observation-only, observe)  
With STORAGE PREFER_INLINE or STORAGE FORCE_OUTLINE declared on a column, values read back exactly, DDL and DML error paths behave, and the record stays valid; where a value is placed is recorded as an implementation observation.

- Authority: Ticket 10 policy 2: implemented behavior without established acceptance gets logical-correctness and error-path tests; placement is observed, never asserted. Coverage scope is a pending decision request from ticket 11 §9.
- Pinned observation (ticket 11): Grammar accepts both hints (csql_grammar.y:10574-10582); FORCE_OUTLINE bypasses the record gate (a 40-byte value in a small record was demoted).
- Attack dimensions: PREFER_INLINE column as largest candidate; FORCE_OUTLINE on a small value; hint on a column that is not variable-length (error path); ALTER adding and removing the hint
- Related: `OOS-REP-13`

**`OOS-REP-13` — Placement-hint policy authority** (BLOCKED, withhold)  
Whether PREFER_INLINE ordering and the FORCE_OUTLINE gate bypass are required behavior is undecided; no placement expectation is fixed for either hint.

- Authority: Source existence does not establish acceptance (ticket 10). The gap stays visible in the matrix and does not block OOS-REP-12.
- Authority question: Is CBRD-26912 (STORAGE PREFER_INLINE) accepted, and is STORAGE FORCE_OUTLINE an accepted design at all? If accepted, what exact ordering and bypass semantics are required?
- Pinned observation (ticket 11): Both hints implemented beyond accepted policy (ticket 11 §4 b).
- Related: `OOS-REP-12`

**`OOS-REP-14` — Stub-size terminology: 16, 20 or 24 bytes** (BLOCKED, withhold)  
Residual context statements still give the profitable demotion threshold as strictly greater than 16 B (§5 Limitations row for CBRD-26776) while the accepted layout fixes the OOS inline stub, chunk header and floor at 24 B, and the invariants research met a 20-byte generation-stub draft; the single normative size must be confirmed.

- Authority: Mixed-era statement from the invariants research (stub-size terminology). Expectations in the 17-24 B serialized band are withheld (OOS-REP-05); outside the band OOS-REP-04 applies.
- Authority question: Confirm that every remaining 16-byte and 20-byte statement is historical, that 24 B is the single normative stub, chunk-header and floor size, and that the pinned 16-byte constant is a conformance gap rather than an alternative accepted layout.
- Pinned observation (ticket 11): OR_OOS_INLINE_SIZE = 16 and a 16-byte chunk header at the pin (ticket 11 §4 d, e).
- Related: `OOS-REP-04`, `OOS-REP-05`

#### SQL operations

| ID | Title | Status | Policy | Seam | Citation |
|---|---|---|---|---|---|
| `OOS-SQL-01` | INSERT then SELECT returns the exact value | assertable | assert | public-sql | context-heading: §3 INSERT |
| `OOS-SQL-02` | UPDATE correctness | assertable | assert | public-sql | context-heading: §3 UPDATE (Always New OID — M1) |
| `OOS-SQL-03` | M1 always-new-chain on UPDATE (current behavior) | observation-only | observe | either | context-heading: §3 UPDATE (Always New OID — M1) — Current implementation |
| `OOS-SQL-04` | UPDATE chain reuse and commit-conditional cleanup (CBRD-27230) | UNSUPPORTED | withhold | either | accepted-design: CBRD-27230 UPDATE chain reuse — spec note (2026-08-13) and §3 UPDATE superseding ownership invariant |
| `OOS-SQL-05` | DELETE semantics | assertable | assert | either | context-heading: §3 DELETE |
| `OOS-SQL-06` | Transaction atomicity and undo correctness | assertable | assert | public-sql | context-heading: §4 Recovery & Replication Invariants, invariant 2 (Undo correctness) |
| `OOS-SQL-07` | Deferred-reuse text versus the accepted CBRD-27230 design | BLOCKED | withhold | either | context-heading: §5 Optimization Ideas — A. Update OOS value-chain reuse (CBRD-26516) and Milestones (M3 cancelled) |

**`OOS-SQL-01` — INSERT then SELECT returns the exact value** (assertable, assert)  
An inserted OOS-backed row reads back with every attribute byte-identical to the inserted value, for single rows and bulk inserts of varying sizes.

- Authority: Exact whole-value equality justified before the engine runs; DISK_SIZE supports the arithmetic but is not a placement oracle. Pair with activation evidence.
- Attack dimensions: single row; 100+ rows of varying sizes; 1000+ rows all OOS-backed; INSERT ... SELECT; prepared INSERT with host variables; inline comparator row
- Related: `OOS-REP-02`

**`OOS-SQL-02` — UPDATE correctness** (assertable, assert)  
After an UPDATE of an OOS-backed attribute, or of an inline attribute in an OOS-backed record, the updater and every later reader see the exact new value; repeated updates leave the final value correct.

- Authority: Universal value correctness independent of the physical design; chain ownership is OOS-SQL-03 and OOS-SQL-04.
- Attack dimensions: single-chunk to multi-chunk and back; 50+ repeated updates on one row; UPDATE of only an inline attribute; UPDATE via prepared statement; UPDATE with subquery reading the same OOS value
- Related: `OOS-SQL-03`, `OOS-SQL-04`, `OOS-REP-11`

**`OOS-SQL-03` — M1 always-new-chain on UPDATE (current behavior)** (observation-only, observe)  
At the pin every UPDATE allocates fresh OOS value chains and head OOS OIDs for the new record version, even for attributes the statement did not assign.

- Authority: Historical and current-implementation behavior superseded on paper by CBRD-27230. Record chunk-count growth as an observation; never promote it as required behavior (scenario 2.2 wording is M1-era).
- Pinned observation (ticket 11): heap_attrinfo_insert_to_oos always allocates fresh chains; the vacuum forward-walk relies on old/new head-OID disjointness.
- Attack dimensions: UPDATE of an inline attribute only; UPDATE assigning the same value
- Related: `OOS-SQL-04`

**`OOS-SQL-04` — UPDATE chain reuse and commit-conditional cleanup (CBRD-27230)** (UNSUPPORTED, withhold)  
UPDATE reuses the OOS value chains of attributes the statement does not assign; dropped chains are announced by a commit-conditional RVOOS_NOTIFY_VACUUM record consumed by vacuum; the forward-walk is removed; DELETE and the SA_MODE eager path are unchanged.

- Authority: Accepted design absent at the pin. Reuse and notify-record expectations are withheld; rollback-survival correctness continues under OOS-CL-03.
- Accepted design absent at the pin: CBRD-27230 UPDATE chain reuse with RVOOS_NOTIFY_VACUUM cleanup
- Pinned observation (ticket 11): Forward walk present (vacuum_oos.cpp:154, :275); no notify emitter (recovery.c:899, mvcc.h:268 reserve the record).
- Attack dimensions: unassigned attribute keeps its head OID; notify record only on commit; forward-walk absence
- Expected engine findings: CBRD-27237
- Related: `OOS-SQL-03`, `OOS-CL-03`, `OOS-OPS-03`

**`OOS-SQL-05` — DELETE semantics** (assertable, assert)  
A deleted OOS-backed row is gone for the deleter and for later readers; the deleted record keeps its stubs and its value chains are not removed at delete time in MVCC mode, so the table stays reusable and earlier snapshots can still read the value.

- Authority: Logical checks on the SQL seam; 'chains not removed at delete time' is assertable through SHOW HEAP OOS chunk counts in client-server mode only, because the standalone eager path deletes synchronously (ticket 11 §6).
- Pinned observation (ticket 11): Standalone DELETE dropped Oos_num_recs to 0 immediately while pages stayed allocated (LSA-gate deferral).
- Configuration scope: Physical deferral applies to client-server (MVCC) mode; standalone mode deletes eagerly.
- Attack dimensions: single row; DELETE all then re-INSERT; DELETE with WHERE on an OOS column; TRUNCATE comparator
- Related: `OOS-CL-02`, `OOS-CL-11`

**`OOS-SQL-06` — Transaction atomicity and undo correctness** (assertable, assert)  
ROLLBACK, savepoint rollback and statement failure restore the previous record as-is, including its OOS inline stubs whose head OIDs still reference live chains; no partial effect and no orphan chain remains from the aborted work.

- Authority: Exact original values after rollback; constraint and trigger failures are the statement-failure dimension. Orphan-chain cleanup eventuality is OOS-CL-02.
- Attack dimensions: INSERT + UPDATE then ROLLBACK; UPDATE of an OOS-backed attribute then ROLLBACK; ROLLBACK TO SAVEPOINT across OOS writes; unique/PK/NOT NULL violation on an OOS row; trigger raising an error after an OOS write; multi-row statement failing part way
- Related: `OOS-CL-03`, `OOS-DUR-02`

**`OOS-SQL-07` — Deferred-reuse text versus the accepted CBRD-27230 design** (BLOCKED, withhold)  
§5 Optimization Ideas A and the Milestones section still describe UPDATE value-chain reuse as a cancelled-M3 future improvement not in M2, while the 2026-08-13 spec note records CBRD-27230 as an accepted design and M2 as the umbrella for all remaining OOS work; whether reuse is a merge-gating conformance item is undecided.

- Authority: Mixed-era statement from the invariants research (deferred reuse text). Decides whether OOS-SQL-04's UNSUPPORTED status is a merge gate or an accepted deferral; either way the pin's behavior is never promoted as the answer.
- Authority question: Is CBRD-27230 UPDATE chain reuse required for feat/oos conformance before merge, or deferred to a later milestone? Should Optimization Idea A and the M3 milestone text be rewritten to point at the accepted design?
- Related: `OOS-SQL-04`, `OOS-CL-08`

#### Read paths

| ID | Title | Status | Policy | Seam | Citation |
|---|---|---|---|---|---|
| `OOS-RD-01` | Every read path returns the complete OOS value | assertable | assert | public-sql | context-heading: §3 SELECT (OOS Resolve) |
| `OOS-RD-02` | Old-version reads reconstruct through undo stubs | assertable | assert | private-shell | context-heading: §4 Recovery & Replication Invariants, invariant 2 (Undo correctness) |
| `OOS-RD-03` | Raw-byte consumers receive expanded records (ADR-0003) | assertable | assert | either | adr: ADR-0003 OOS record expansion is opt-in for raw-byte consumers |

**`OOS-RD-01` — Every read path returns the complete OOS value** (assertable, assert)  
Every SQL read path that consumes an OOS-backed attribute obtains the complete OOS value: heap scans, index scans, joins, prepared statements, aggregates and functions, constraint and trigger evaluation, and attribute-level reads that touch one column.

- Authority: Exact whole-value equality per path; operation success alone does not prove Resolve routing, so pair each path with activation evidence where the path is claimed as OOS coverage.
- Attack dimensions: heap scan; index scan on a non-OOS key projecting the OOS column; join on inline keys projecting OOS values from both sides; prepared statement with host variables; GROUP BY / aggregate over OOS values; constraint and trigger reading the OOS value; SELECT of only the inline columns (no OOS I/O expected; observation)
- Related: `OOS-RD-03`

**`OOS-RD-02` — Old-version reads reconstruct through undo stubs** (assertable, assert)  
A reader whose snapshot predates another session's UPDATE or DELETE reads the exact old value, reconstructed through prev_version_lsa, the undo record's stubs and oos_read, whether the writer is uncommitted or committed.

- Authority: Needs two sessions with acknowledged barriers (ticket 05). Value survival is the oracle; cleanup afterwards is OOS-CL-02.
- Attack dimensions: uncommitted UPDATE visible only to the updater; committed UPDATE with an earlier reader snapshot; deleted row still visible to an earlier snapshot; multi-chunk old version
- Related: `OOS-CL-01`

**`OOS-RD-03` — Raw-byte consumers receive expanded records (ADR-0003)** (assertable, assert)  
Every path that consumes raw record bytes (client copy-area fetch, unloaddb, compactdb, partition redistribution, catalog updates, re-insertion into another heap) receives fully expanded records; no OOS inline stub leaks to an OOS-unaware consumer.

- Authority: Assert logical output of each consumer (unload file contents, compacted table values, moved partition rows). CBRD-26948 is an expected finding to re-verify at the pin, not to assume.
- Pinned observation (ticket 11): locator_sr.c:2337 expands copy-area records at the pin (research report); unloaddb/compactdb leak status unverified.
- Attack dimensions: unloaddb of OOS tables; compactdb; ALTER ... PARTITION redistribution; CREATE TABLE AS SELECT / INSERT ... SELECT; catalog class statistics update
- Expected engine findings: CBRD-26948
- Related: `OOS-SCH-04`

#### Schema and utilities

| ID | Title | Status | Policy | Seam | Citation |
|---|---|---|---|---|---|
| `OOS-SCH-01` | OOS file lifecycle: at most one per heap, removed with the heap | assertable | assert | private-shell | context-heading: §4 Recovery & Replication Invariants, invariant 6 (OOS file <-> heap file 1:1) |
| `OOS-SCH-02` | Schema evolution preserves OOS values | assertable | assert | public-sql | context-heading: §3 SELECT (OOS Resolve) |
| `OOS-SCH-03` | loaddb writes correct OOS-backed rows, including no-logging mode | assertable | assert | private-shell | context-heading: §2 Multi-Chunk OOS Chain — Accepted logging policy (2026-09-09) |
| `OOS-SCH-04` | compactdb and checkdb on OOS tables | assertable | assert | private-shell | adr: ADR-0003 OOS record expansion is opt-in for raw-byte consumers |
| `OOS-SCH-05` | backup and restore preserve OOS values | assertable | assert | private-shell | context-heading: §4 Recovery & Replication Invariants, invariant 1 (WAL completeness) |
| `OOS-SCH-06` | Space accounting of OOS files (CBRD-27350) | observation-only | observe | private-shell | context-heading: §5 Known Bugs — spacedb/diagdb can't see OOS space |

**`OOS-SCH-01` — OOS file lifecycle: at most one per heap, removed with the heap** (assertable, assert)  
Each heap file has at most one OOS file, lazily created on first demotion and recorded in the heap header; destroying the heap (DROP TABLE, and TRUNCATE which recreates the heap) leaves no orphan OOS file.

- Authority: Observable through SHOW HEAP OOS (Has_oos_file) and diagdb -d 1 / -d 2 owner descriptors. The DROP cleanup is the resolved CBRD-26608 design; the context has no explicit TRUNCATE sentence, so the TRUNCATE expectation is derived from invariant 6 and noted as such.
- Pinned observation (ticket 11): FILE_OOS owner descriptor 'CLASS_OID … OOS for HFID …' printed by diagdb -d 1 at the pin.
- Attack dimensions: DROP TABLE with single- and multi-chunk values; TRUNCATE then re-insert; DROP inside a rolled-back transaction; DROP concurrent with checkdb (narrow race noted in §5; observation)
- Related: `OOS-SCH-06`

**`OOS-SCH-02` — Schema evolution preserves OOS values** (assertable, assert)  
After ALTER TABLE (add, drop, modify or rename a column, change a type, add or drop an index, partition changes) every OOS-backed value reads back exactly and the resulting records are valid.

- Authority: Universal value correctness across rewrites; the rewrite side applies the write rules of OOS-REP-02.
- Attack dimensions: ADD COLUMN with default beside OOS values; DROP COLUMN of an OOS-backed column; MODIFY type of an OOS-backed column; ADD INDEX on inline key of an OOS table; ALTER ... ADD PARTITION / REORGANIZE
- Related: `OOS-RD-03`

**`OOS-SCH-03` — loaddb writes correct OOS-backed rows, including no-logging mode** (assertable, assert)  
Rows loaded with loaddb read back exactly; with logging disabled the values remain correct while stamp-uniqueness and recovery guarantees are not asserted, per the accepted no-logging exception.

- Authority: Assert values in both modes; recovery after a no-logging load is recorded as observation only.
- Attack dimensions: loaddb of an unloaded OOS table; loaddb --no-logging; load across page sizes
- Related: `OOS-RD-03`, `OOS-DUR-01`

**`OOS-SCH-04` — compactdb and checkdb on OOS tables** (assertable, assert)  
checkdb passes on a consistent database holding OOS files, and compactdb preserves every OOS-backed value; utility exit status is asserted explicitly.

- Authority: Utility exit status plus value equality after the utility; the private DROP-reclaim pattern (extract identifier, fail explicitly) is the model.
- Attack dimensions: checkdb after DELETE and vacuum; compactdb with mixed inline/OOS rows; checkdb standalone versus client-server
- Expected engine findings: CBRD-26948
- Related: `OOS-RD-03`

**`OOS-SCH-05` — backup and restore preserve OOS values** (assertable, assert)  
A database restored from a full or incremental backup returns every committed OOS-backed value exactly and its OOS files remain consistent (checkdb passes).

- Authority: Durability of committed state through the backup path; assert values and checkdb exit status.
- Attack dimensions: full backup and restore; incremental backup after OOS updates; restore to a different directory; backup of an encrypted OOS database (with OOS-OPS-04)
- Related: `OOS-DUR-01`

**`OOS-SCH-06` — Space accounting of OOS files (CBRD-27350)** (observation-only, observe)  
spacedb and diagdb output for OOS storage is recorded as observed: at the pin OOS files are folded into the HEAP category and attributed to classes only through diagdb owner descriptors.

- Authority: QA tooling ask, not required OOS behavior; record what the tools print so the expected finding CBRD-27350 stays visible.
- Pinned observation (ticket 11): spacedb -S -p reports 53 heap files where 45 are heaps and 8 are OOS files (ticket 11 §6).
- Attack dimensions: spacedb totals before and after OOS inserts; diagdb -d 2 OOS file listing
- Expected engine findings: CBRD-27350
- Related: `OOS-SCH-01`

#### Concurrent lifetime

| ID | Title | Status | Policy | Seam | Citation |
|---|---|---|---|---|---|
| `OOS-CL-01` | Snapshot survival across update, delete and vacuum | assertable | assert | private-shell | context-heading: §4 Vacuum + OOS (IMPLEMENTED — CBRD-26668, PR #6986 merged) |
| `OOS-CL-02` | Dead-version chains are reclaimed by vacuum once no reader needs them | assertable | assert-after-eligibility | private-shell | context-heading: §4 Vacuum + OOS (IMPLEMENTED — CBRD-26668, PR #6986 merged) |
| `OOS-CL-03` | Rollback survival against vacuum (CBRD-27237) | assertable | assert | private-shell | context-heading: §4 Recovery & Replication Invariants, invariant 2 (Undo correctness) |
| `OOS-CL-04` | Live data survives slot reuse and vacuum retry (CBRD-26950) | assertable | assert | private-shell | context-heading: §4 Vacuum + OOS (IMPLEMENTED — CBRD-26668, PR #6986 merged) |
| `OOS-CL-05` | Empty-page reclaim invariant (CBRD-26786) | assertable | assert-after-eligibility | private-shell | accepted-design: CBRD-26786 empty-page reclaim invariant — spec note (2026-08-28) and §4 Vacuum + OOS |
| `OOS-CL-06` | No unjustified OOS file growth under churn | assertable | assert-after-eligibility | private-shell | accepted-design: CBRD-26786 empty-page reclaim invariant — spec note (2026-08-28) and §4 Vacuum + OOS |
| `OOS-CL-07` | Reclamation domain and eventuality bound | BLOCKED | withhold | private-shell | accepted-design: CBRD-26786 empty-page reclaim invariant — spec note (2026-08-28) and §4 Vacuum + OOS |
| `OOS-CL-08` | Chain ownership wording: no cross-version sharing versus borrowed references | BLOCKED | withhold | either | context-heading: Writing Conventions — ownership statement |
| `OOS-CL-09` | Cancellation and disconnect during OOS writes | assertable | assert | private-shell | context-heading: §4 Recovery & Replication Invariants, invariant 2 (Undo correctness) |
| `OOS-CL-10` | Concurrent DDL against OOS DML | assertable | assert | private-shell | context-heading: §3 SELECT (OOS Resolve) |
| `OOS-CL-11` | Standalone eager cleanup keeps post-image chains | assertable | assert | private-shell | context-heading: §4 Vacuum + OOS (IMPLEMENTED — CBRD-26668, PR #6986 merged), path 3 (Eager, non-MVCC / SA_MODE) |
| `OOS-CL-12` | Accepted eager-cleanup and silent-skip policy (CBRD-26950) | UNSUPPORTED | withhold | private-shell | accepted-design: CBRD-26950 accepted eager-cleanup policy — §2 Multi-Chunk OOS Chain, Accepted eager-cleanup policy (2026-09-09) |
| `OOS-CL-13` | Bestspace sync tolerates concurrent page deallocation (ADR-0001) | assertable | assert | private-shell | adr: ADR-0001 OOS pages use a non-numerable file enumerated by a sector-bitmap scan |

**`OOS-CL-01` — Snapshot survival across update, delete and vacuum** (assertable, assert)  
A reader that established its snapshot by a real read keeps reading the exact old value while another session updates or deletes the row and vacuum runs; the old value is never lost before the reader releases.

- Authority: Schedule family 'snapshot survival' (ticket 05) with acknowledged barriers and observed vacuum progress. Value survival is the oracle here; post-release cleanup is OOS-CL-02.
- Attack dimensions: reader vs UPDATE then vacuum; reader vs DELETE then vacuum; multi-chunk old value; two readers with different snapshots
- Related: `OOS-RD-02`, `OOS-CL-02`

**`OOS-CL-02` — Dead-version chains are reclaimed by vacuum once no reader needs them** (assertable, assert-after-eligibility)  
The OOS value chains owned by dead record versions are deleted by vacuum after every snapshot that could read them has ended; no chain is deleted earlier and no chain is permanently orphaned.

- Authority: Assert chunk-count decrease only after proving eligibility (no active snapshot older than the delete) and safety (vacuum processed the block, observed progress). Before eligibility, a decrease is a failure candidate; after eligibility, absence of decrease within the bounded wait is a failure candidate.
- Attack dimensions: UPDATE old chain reclaimed after reader release; DELETE chain reclaimed; aborted UPDATE's new chains reclaimed; vacuum progress witness and deadline
- Related: `OOS-CL-01`, `OOS-CL-05`

**`OOS-CL-03` — Rollback survival against vacuum (CBRD-27237)** (assertable, assert)  
After an UPDATE of an OOS-backed attribute is rolled back, the restored value remains exact after vacuum has processed the aborted transaction's log records.

- Authority: Universal rollback correctness independent of the physical design; expected to FAIL at the pin as Engine defect CBRD-27237. A known bug remains a failure.
- Pinned observation (ticket 11): Forward-walk acts on undo-image content with no commit/abort filter (analysis-based, no runtime repro recorded in the context).
- Attack dimensions: multi-chunk UPDATE, ROLLBACK, vacuum, verify; savepoint rollback variant; crash-induced rollback variant
- Expected engine findings: CBRD-27237
- Related: `OOS-SQL-04`, `OOS-SQL-06`

**`OOS-CL-04` — Live data survives slot reuse and vacuum retry (CBRD-26950)** (assertable, assert)  
After vacuum frees an OOS slot and another row's chain reuses that slot, a vacuum retry (worker pause, mid-block error or crash recovery re-running the block) never deletes the new owner's chunk; the complete value survives.

- Authority: Universal correctness (vacuum never deletes live data); expected to FAIL at the pin as Engine defect CBRD-26950. The identity-stamp mechanism itself is OOS-REP-05 (UNSUPPORTED).
- Pinned observation (ticket 11): oos_chunk_exists checks occupied, not mine; header has no identity stamp.
- Attack dimensions: prove reclamation and reuse of the targeted slot; force block retry; multi-chunk new owner
- Expected engine findings: CBRD-26950
- Related: `OOS-REP-05`, `OOS-CL-12`

**`OOS-CL-05` — Empty-page reclaim invariant (CBRD-26786)** (assertable, assert-after-eligibility)  
Every fully emptied OOS data page is eventually returned to the file manager, and an OOS file reserves a new sector only when no safely reclaimable empty page exists; pages whose last writer may still be a live undo source are deferred, and deferral ends when that writer finishes.

- Authority: Ticket 10 policy 3: assert page release only after proving the page is empty, is a data page (not the header page), belongs to a non-legacy file, and passes the LSA gate (no active writer). Never use an unconditional zero-page assertion. Ticket 11 found the mechanisms present at the pin (conforming).
- Pinned observation (ticket 11): oos_reclaim_lsa_gate_passes, oos_reclaim_empty_pages, oos_reclaim_sweep_step and oos_alloc_page_with_reclaim exist at the pin; after a standalone DELETE, Oos_num_user_pages stayed at 2 (deferral).
- Attack dimensions: empty page with deleter committed; empty page with active deleter, then abort; refilled page; interrupted sweep and boot-rule lap after crash; growth-gate sweep at the single growth point
- Related: `OOS-CL-02`, `OOS-CL-06`, `OOS-CL-07`

**`OOS-CL-06` — No unjustified OOS file growth under churn** (assertable, assert-after-eligibility)  
Under sustained insert/delete churn with reclaimable empty pages available, the OOS file does not reserve new sectors while a safely reclaimable page exists.

- Authority: Progress witness: page counts from SHOW HEAP OOS over time with eligibility established; the bound on 'eventually' is a Specification gap (OOS-CL-07) so the case records the observed lag rather than asserting a fixed bound.
- Attack dimensions: steady-state churn at each page size; churn with a long-lived reader deferring pages; churn after crash (hint loss)
- Related: `OOS-CL-05`, `OOS-CL-07`

**`OOS-CL-07` — Reclamation domain and eventuality bound** (BLOCKED, withhold)  
The exact domain of 'every fully emptied OOS data page is eventually returned' is not fixed: the header page, legacy numerable files, safely deferred pages and the time bound of 'eventually' need authoritative wording.

- Authority: Mixed-era statement from the invariants research (unconditional reclamation). Until answered, physical page-count expectations are withheld except where eligibility and safety are proven per OOS-CL-05.
- Authority question: Which pages are inside the reclaim guarantee (data pages only; header page excluded; legacy numerable files excluded?), and what progress witness or time bound makes 'eventually' testable? Is an implementation's sticky-page or legacy-file exception an accepted specification exception?
- Related: `OOS-CL-05`, `OOS-CL-06`

**`OOS-CL-08` — Chain ownership wording: no cross-version sharing versus borrowed references** (BLOCKED, withhold)  
The Writing Conventions still require stating that value chains are never shared across record versions, while the accepted CBRD-27230 ownership invariant allows older versions to hold borrowed references; which statement governs at the pin is undecided.

- Authority: Mixed-era statement from the invariants research. Ownership assertions are withheld; value correctness continues under OOS-CL-01 and OOS-CL-03.
- Authority question: Which ownership statement is normative at the pin, and should the Writing Conventions be updated to the superseding invariant with an explicit 'effective once implemented' qualifier?
- Related: `OOS-SQL-04`

**`OOS-CL-09` — Cancellation and disconnect during OOS writes** (assertable, assert)  
A statement cancelled or a session disconnected during an OOS INSERT, UPDATE or DELETE leaves no partial effect: the transaction is rolled back, values of other rows are intact, and the aborted work's chains become eligible for cleanup.

- Authority: Assert transaction state and values; cleanup eventuality per OOS-CL-02.
- Attack dimensions: kill the client mid multi-chunk INSERT; query cancel during bulk UPDATE; disconnect with an open savepoint
- Related: `OOS-SQL-06`, `OOS-CL-02`

**`OOS-CL-10` — Concurrent DDL against OOS DML** (assertable, assert)  
ALTER, DROP or TRUNCATE running concurrently with OOS reads and writes yields either exact values or the standard DDL/lock error; no crash, no stub leak and no corrupted value.

- Authority: Universal correctness or explicit error; specific lock-ordering expectations are not fixed by the context.
- Attack dimensions: DROP while a reader holds a snapshot; ALTER ADD COLUMN during bulk OOS inserts; TRUNCATE versus concurrent UPDATE
- Related: `OOS-SCH-01`, `OOS-SCH-02`

**`OOS-CL-11` — Standalone eager cleanup keeps post-image chains** (assertable, assert)  
In standalone (non-MVCC) mode old chains are deleted synchronously at UPDATE or DELETE time, and any chain the post-image still references is kept; values read back exactly.

- Authority: Value correctness plus chunk-count decrease observable immediately in standalone mode (ticket 11 §6).
- Pinned observation (ticket 11): heap_oos_delete_unreferenced (heap_oos.cpp:425); standalone DELETE dropped Oos_num_recs to 0.
- Configuration scope: Standalone mode only.
- Attack dimensions: UPDATE of one of two OOS-backed attributes; DELETE then re-INSERT in standalone
- Related: `OOS-SQL-05`, `OOS-CL-12`

**`OOS-CL-12` — Accepted eager-cleanup and silent-skip policy (CBRD-26950)** (UNSUPPORTED, withhold)  
Vacuum treats an absent or reused head as a successful silent skip; eager reclamation completes the DML and emits a diagnostic when cleanup is skipped, leaving no stray error in the error stack; malformed heads and operational failures remain errors.

- Authority: Accepted policy whose implementation and regression verification are pending the PR repair; diagnostic and error-stack expectations are withheld at the pin.
- Accepted design absent at the pin: CBRD-26950 eager-cleanup diagnostic policy
- Related: `OOS-CL-04`, `OOS-CL-11`

**`OOS-CL-13` — Bestspace sync tolerates concurrent page deallocation (ADR-0001)** (assertable, assert)  
OOS free-space sampling enumerates data pages from the sector bitmap and tolerates pages deallocated by concurrent vacuum during the walk; inserts under concurrent reclaim never fail or crash because a sampled page disappeared.

- Authority: Observable as insert success under concurrent reclaim; the ADR's skipped-page counter is not implemented at the pin, so the count is not an oracle.
- Pinned observation (ticket 11): Non-numerable migration landed inside PR #7617 and is present at the pin; legacy numerable files skip reclaim.
- Attack dimensions: inserts racing vacuum reclaim; bestspace sync after crash
- Related: `OOS-CL-05`

#### Durability

| ID | Title | Status | Policy | Seam | Citation |
|---|---|---|---|---|---|
| `OOS-DUR-01` | Committed OOS writes survive a crash | assertable | assert | private-shell | context-heading: §4 Recovery & Replication Invariants, invariant 1 (WAL completeness) |
| `OOS-DUR-02` | Uncommitted OOS writes are undone by recovery | assertable | assert | private-shell | context-heading: §4 Recovery & Replication Invariants, invariant 1 (WAL completeness) |
| `OOS-DUR-03` | Interrupted COMMIT is all or nothing | assertable | assert | private-shell | context-heading: §4 Recovery & Replication Invariants, invariant 1 (WAL completeness) |
| `OOS-DUR-04` | Insert-side atomicity between chunk writes and heap publication | assertable | assert | private-shell | context-heading: §3 INSERT |
| `OOS-DUR-05` | Delete-side atomicity of vacuum chunk deletes | assertable | assert | private-shell | context-heading: §4 Vacuum + OOS (IMPLEMENTED — CBRD-26668, PR #6986 merged) — crash mid-delete |
| `OOS-DUR-06` | Repeated recovery interruption | assertable | assert | private-shell | context-heading: §4 Recovery & Replication Invariants, invariant 1 (WAL completeness) |
| `OOS-DUR-07` | Corruption detection guarantees for OOS pages and logs | BLOCKED | withhold | private-shell | context-heading: §4 Recovery & Replication Invariants |
| `OOS-DUR-08` | Bestspace hints recover after a crash | assertable | assert | private-shell | context-heading: §2 Best Page Policy (3-Tier Bestspace — M2, CBRD-26658) |

**`OOS-DUR-01` — Committed OOS writes survive a crash** (assertable, assert)  
Committed INSERT, UPDATE and DELETE of OOS-backed rows, including multi-chunk values, are present with exact values after kill -9 and restart.

- Authority: Use the verified durable-commit configuration and the external operation journal (ticket 05); assert against acknowledged commits.
- Attack dimensions: committed INSERT then crash; committed multi-chunk (50 KiB+) then crash; committed UPDATE and DELETE then crash; crash immediately after the commit acknowledgement
- Related: `OOS-DUR-02`, `OOS-REP-07`

**`OOS-DUR-02` — Uncommitted OOS writes are undone by recovery** (assertable, assert)  
After a crash, transactions proven uncommitted leave no effect: uncommitted inserts are gone and uncommitted updates restore the original value through the undo record's stubs; mixed committed and uncommitted work recovers to the permitted state.

- Authority: Evaluate against permitted transaction states from the journal, not against 'every missing acknowledgement was a rollback'.
- Attack dimensions: uncommitted INSERT; uncommitted UPDATE (original value restored); mixed committed/uncommitted in one crash; orphan chains of undone work eventually reclaimed (OOS-CL-02)
- Related: `OOS-DUR-01`, `OOS-SQL-06`

**`OOS-DUR-03` — Interrupted COMMIT is all or nothing** (assertable, assert)  
A COMMIT whose acknowledgement was lost recovers either wholly committed or wholly rolled back, consistent with transaction ordering; partial application of an OOS-backed row is forbidden.

- Authority: Transaction-state model with explicit outcome uncertainty preserved in the attempt record.
- Attack dimensions: crash during commit of a multi-row OOS transaction; crash during commit with mixed inline and OOS rows
- Related: `OOS-DUR-01`

**`OOS-DUR-04` — Insert-side atomicity between chunk writes and heap publication** (assertable, assert)  
Both the heap insert and every OOS chunk insert are logged, so a crash or injected interruption between chunk insertion and heap publication leaves no dangling stub and no permanently orphaned chain after recovery.

- Authority: Assert no dangling stub (values readable or row absent) and transaction correctness; orphan eventuality per OOS-CL-02. Interruption sites need ticket 16 validation.
- Attack dimensions: crash after the tail chunk, before the head chunk; crash after all chunks, before heap publication; injected failure in oos_insert_many after some publications
- Related: `OOS-DUR-05`, `OOS-RES-01`

**`OOS-DUR-05` — Delete-side atomicity of vacuum chunk deletes** (assertable, assert)  
Each chunk delete is logged within a system operation, so a crash mid-delete leaves OOS state atomic with the heap reclamation after recovery.

- Authority: Assert values of surviving rows and checkdb consistency after recovery; retry idempotency is OOS-CL-04.
- Attack dimensions: crash during forward-walk delete of a multi-chunk chain; crash during within-sysop delete
- Related: `OOS-CL-04`

**`OOS-DUR-06` — Repeated recovery interruption** (assertable, assert)  
Crashing again during recovery and recovering once more ends in a state consistent with the permitted transaction states; recovery is restartable.

- Authority: Schedule family 'interrupted recovery' (ticket 05); reaching and acknowledging the recovery phase may be a Capability gap at run time.
- Attack dimensions: crash during redo of OOS inserts; crash during undo of OOS updates; two consecutive interruptions
- Related: `OOS-DUR-02`

**`OOS-DUR-07` — Corruption detection guarantees for OOS pages and logs** (BLOCKED, withhold)  
The context documents no detection or recovery guarantee for corrupted OOS pages or OOS log records; no expectation is fixed for copied-image corruption cases.

- Authority: Ticket 06: corruption cases are judged against documented guarantees only; arbitrary corruption implies no unconditional recovery promise. Record observed behavior; assert nothing.
- Authority question: What detection (checkdb, page checksum, stub/chain validation) and recovery behavior is guaranteed for a corrupted OOS page, chunk header or OOS log record?
- Related: `OOS-SCH-04`

**`OOS-DUR-08` — Bestspace hints recover after a crash** (assertable, assert)  
Free-space hints are non-logged; after a crash, inserts continue to succeed and the sync scanner rediscovers free space.

- Authority: Assert functional success (inserts and exact values after crash); page reuse quantity belongs to OOS-CL-06.
- Attack dimensions: crash then heavy inserts; crash with a nearly full OOS file
- Related: `OOS-CL-06`

#### Operational features

| ID | Title | Status | Policy | Seam | Citation |
|---|---|---|---|---|---|
| `OOS-OPS-01` | HA replication: value equality and ordering | assertable | assert | private-shell | context-heading: §4 Replication Notes |
| `OOS-OPS-02` | HA rollback, applier restart and lag | assertable | assert | private-shell | context-heading: §4 Recovery & Replication Invariants, invariant 5 (Replication log completeness) |
| `OOS-OPS-03` | HA marker item for reused attributes (CBRD-27230) | UNSUPPORTED | withhold | private-shell | accepted-design: CBRD-27230 UPDATE chain reuse — spec note (2026-08-13), replication marker item |
| `OOS-OPS-04` | TDE covers OOS pages (CBRD-26830) | assertable | assert | private-shell | accepted-design: CBRD-26830 TDE applied to OOS pages — §5 Known Bugs (DONE on feat/oos, commit 138f624964) |
| `OOS-OPS-05` | Durable OOS supplemental images for CDC and flashback (ADR-0004) | UNSUPPORTED | withhold | private-shell | adr: ADR-0004 Preserve OOS historical values in supplemental images |
| `OOS-OPS-06` | CDC and flashback over OOS rows at the pin | observation-only | observe | private-shell | context-heading: §5 Known Bugs — CDC flashback OOS-stub Resolve (missing feature) |

**`OOS-OPS-01` — HA replication: value equality and ordering** (assertable, assert)  
INSERT, UPDATE, DELETE and multi-chunk operations on OOS-backed rows are replicated so the replica holds equal logical values in the same transaction order; OOS OIDs on the replica may differ from the master.

- Authority: Compare values and ordering on both nodes; never compare physical OIDs.
- Attack dimensions: INSERT / UPDATE / DELETE replicated (scenarios 8.1-8.3); multi-chunk replicated (8.4); mixed transaction with inline and OOS rows
- Related: `OOS-OPS-02`

**`OOS-OPS-02` — HA rollback, applier restart and lag** (assertable, assert)  
Rolled-back transactions leave no effect on the replica; an applier restarted mid-stream resumes to an equal state; replication lag never yields a partially applied OOS row.

- Authority: Assert equality after catch-up with bounded waits; applier internals are not read directly.
- Attack dimensions: ROLLBACK of a multi-chunk UPDATE; applier restart during a large transaction; catch-up after lag
- Related: `OOS-OPS-01`

**`OOS-OPS-03` — HA marker item for reused attributes (CBRD-27230)** (UNSUPPORTED, withhold)  
Replication carries a per-reused-attribute marker item with replica-side fixup once UPDATE chain reuse is implemented.

- Authority: Accepted design absent at the pin; withheld with OOS-SQL-04.
- Accepted design absent at the pin: CBRD-27230 replication marker item and replica-side fixup
- Related: `OOS-SQL-04`

**`OOS-OPS-04` — TDE covers OOS pages (CBRD-26830)** (assertable, assert)  
For a TDE-encrypted class, OOS pages hold no plaintext payload on disk (data volumes, log, backup); a lazily created OOS file inherits the class algorithm before its VFID is published; altering encryption applies to an existing OOS file; decrypted reads return exact values.

- Authority: Combine ciphertext evidence (recognizable non-compressible payload absent from raw pages) with correct decrypted reads and proof that the targeted pages were written.
- Attack dimensions: encrypted class, first demotion creates the OOS file; ALTER ... ENCRYPT on a class with an existing OOS file; backup image scan; log scan for RVOOS_INSERT payloads
- Related: `OOS-SCH-05`

**`OOS-OPS-05` — Durable OOS supplemental images for CDC and flashback (ADR-0004)** (UNSUPPORTED, withhold)  
CDC and flashback reconstruct before and after images of OOS-backed rows after vacuum reclaimed the chains; image-recording failure fails the write; unreconstructible legacy OOS images produce an explicit error; activation is offline and one-way.

- Authority: Accepted direction, not implemented at the pin; historical-value scenarios stay blocked conformance requirements until the design is verified on the pinned engine.
- Accepted design absent at the pin: CBRD-26939 durable OOS supplemental images (ADR-0004)
- Attack dimensions: history after vacuum; write failure rolls back; legacy image explicit error; offline activation and restore
- Related: `OOS-OPS-06`

**`OOS-OPS-06` — CDC and flashback over OOS rows at the pin** (observation-only, observe)  
What CDC extraction and flashback emit for OOS-backed rows at the pin (unresolved stubs, errors or values) is recorded as observed and never asserted as correct.

- Authority: Observation for ticket 29; the accepted behavior is OOS-OPS-05.
- Attack dimensions: CDC extraction of INSERT/UPDATE/DELETE with OOS values; flashback of an OOS row before and after vacuum
- Related: `OOS-OPS-05`

#### Resource pressure

| ID | Title | Status | Policy | Seam | Citation |
|---|---|---|---|---|---|
| `OOS-RES-01` | Allocation failure during value construction, expansion and cleanup | assertable | assert | private-shell | context-heading: §4 Recovery & Replication Invariants, invariant 3 (No orphan OOS value chains after update) |
| `OOS-RES-02` | I/O errors and bounded-volume exhaustion | assertable | assert | private-shell | context-heading: §4 Recovery & Replication Invariants, invariant 1 (WAL completeness) |
| `OOS-RES-03` | Failures during rollback, vacuum, reclamation and recovery retry | assertable | assert | private-shell | context-heading: §4 Vacuum + OOS (IMPLEMENTED — CBRD-26668, PR #6986 merged) |
| `OOS-RES-04` | Values and invariants hold under sustained concurrent churn | assertable | assert | private-shell | context-heading: §4 Recovery & Replication Invariants |
| `OOS-RES-05` | Degradation observations | observation-only | observe | private-shell | context-heading: §5 Limitations (Milestone 1) — Ordered fix deadlock risk |

**`OOS-RES-01` — Allocation failure during value construction, expansion and cleanup** (assertable, assert)  
An allocation failure while building, expanding or cleaning OOS values fails the statement with an explicit error, leaves the transaction correct (rolled back or continued per its semantics), creates no orphan chain and never crashes the server.

- Authority: Injected via validated sites (ticket 16) with fired acknowledgements and a fault-disabled control; eligible cleanup afterwards per OOS-CL-05.
- Attack dimensions: bad_alloc on next-OID publication (existing unit-test seam if a trigger path exists); allocation failure during oos_read expansion; allocation failure during vacuum delete
- Related: `OOS-DUR-04`

**`OOS-RES-02` — I/O errors and bounded-volume exhaustion** (assertable, assert)  
Data or log I/O errors and volume exhaustion during OOS insert, delete or reclaim yield an explicit error and transaction correctness; after the fault is removed the database recovers or continues with exact values.

- Authority: Bounded test filesystems on disposable resources only; verify recovery or the expected explicit error, then value integrity.
- Attack dimensions: disk full during a multi-chunk INSERT; log volume full during commit of OOS writes; I/O error during reclaim; fault removed then recovery
- Related: `OOS-DUR-02`

**`OOS-RES-03` — Failures during rollback, vacuum, reclamation and recovery retry** (assertable, assert)  
A failure injected during rollback, vacuum, reclamation or a recovery retry never deletes live data, never leaves a permanent orphan, and retried cleanup is idempotent.

- Authority: Universal correctness under retry; expected engine finding CBRD-26950 on the retry path.
- Attack dimensions: mid-block vacuum error then retry; reclaim sweep interrupted; recovery retry after injected failure
- Expected engine findings: CBRD-26950
- Related: `OOS-CL-04`

**`OOS-RES-04` — Values and invariants hold under sustained concurrent churn** (assertable, assert)  
Under sustained concurrent inserts, updates, deletes and vacuum, every row's value stays exact, rows never mix values, and visibility, atomicity and durability invariants continue to hold.

- Authority: Randomized workloads with recorded seeds and operation traces; oracle is an independent model of expected values per row.
- Attack dimensions: different sessions updating different rows simultaneously (scenario 6.3); mixed single/multi-chunk churn; churn with vacuum active and a long reader
- Related: `OOS-CL-06`

**`OOS-RES-05` — Degradation observations** (observation-only, observe)  
Latency, latch contention, ordered-fix deadlock risk, unloaddb slowdown (CBRD-26458) and needless OOS expansion on cheap paths are measured and recorded; none is asserted as a fixed bound.

- Authority: The context lists deadlock handling as a cancelled milestone and unloaddb slowdown as a known regression; record measurements so CBRD-26458 stays visible.
- Attack dimensions: unloaddb time versus inline comparator; insert latency under page hotspot; deadlock/lock-timeout counts under churn
- Expected engine findings: CBRD-26458
- Related: `OOS-RES-04`
<!-- END GENERATED: requirements -->

## 6. Accepted-but-unimplemented designs at the pin

These appear as `UNSUPPORTED` requirements and are never omitted from the matrix. Their cases record UNSUPPORTED at the pin with the engine's output retained as evidence. Universal correctness checks that do not depend on the physical design continue under the related assertable requirements (for example OOS-CL-03 and OOS-CL-04, whose expected engine findings are CBRD-27237 and CBRD-26950).

<!-- BEGIN GENERATED: unimplemented -->
| ID | Title | Status | Accepted design | Pinned observation |
|---|---|---|---|---|
| `OOS-REP-03` | Four-record physical target (CBRD-27057) | UNSUPPORTED | CBRD-27057 four-record physical target (heap_oos_inline_target_size) | heap_file.c:12350 and :12383 compare against DB_PAGESIZE / 4; heap_oos_inline_target_size does not exist. Disputed band schema-A N in [940, 963] / [1,964, 1,987] / [4,012, 4,035] stays inline at the pin. |
| `OOS-REP-05` | 24-byte identity layout (CBRD-26950) | UNSUPPORTED | CBRD-26950 identity layout (24-byte stub and chunk header, identity-checked delete) | OR_OOS_INLINE_SIZE = 16 (object_representation.h:466); oos_record_header is 16 B (oos_file.hpp:28-33); oos_delete takes no expected identity. Boundaries shift by 8 B: single-chunk max 16,288 pinned vs 16,280 normative at 16 KiB; eligibility band N in [16, 23] demoted at the pin. |
| `OOS-SQL-04` | UPDATE chain reuse and commit-conditional cleanup (CBRD-27230) | UNSUPPORTED | CBRD-27230 UPDATE chain reuse with RVOOS_NOTIFY_VACUUM cleanup | Forward walk present (vacuum_oos.cpp:154, :275); no notify emitter (recovery.c:899, mvcc.h:268 reserve the record). |
| `OOS-CL-12` | Accepted eager-cleanup and silent-skip policy (CBRD-26950) | UNSUPPORTED | CBRD-26950 eager-cleanup diagnostic policy | — |
| `OOS-OPS-03` | HA marker item for reused attributes (CBRD-27230) | UNSUPPORTED | CBRD-27230 replication marker item and replica-side fixup | — |
| `OOS-OPS-05` | Durable OOS supplemental images for CDC and flashback (ADR-0004) | UNSUPPORTED | CBRD-26939 durable OOS supplemental images (ADR-0004) | — |
<!-- END GENERATED: unimplemented -->

## 7. Specification-gap requirements and their authority questions

The four mixed-era statements identified by the [invariants research](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/issues/02-baseline-invariants.md) (cross-version sharing wording, deferred reuse text, stub-size terminology, unconditional reclamation) are `BLOCKED` requirements, plus two further gaps raised by the [specification-authority](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/issues/10-specification-authority.md) and [fault-injection](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/issues/06-fault-injection.md) decisions (placement-hint acceptance, corruption guarantees). Each question goes to the context maintainer through the map; the campaign never edits the normative context.

<!-- BEGIN GENERATED: spec-gaps -->
| ID | Title | Topic | Authority question |
|---|---|---|---|
| `OOS-REP-13` | Placement-hint policy authority | placement-hint-acceptance | Is CBRD-26912 (STORAGE PREFER_INLINE) accepted, and is STORAGE FORCE_OUTLINE an accepted design at all? If accepted, what exact ordering and bypass semantics are required? |
| `OOS-REP-14` | Stub-size terminology: 16, 20 or 24 bytes | stub-size-terminology | Confirm that every remaining 16-byte and 20-byte statement is historical, that 24 B is the single normative stub, chunk-header and floor size, and that the pinned 16-byte constant is a conformance gap rather than an alternative accepted layout. |
| `OOS-SQL-07` | Deferred-reuse text versus the accepted CBRD-27230 design | deferred-reuse-text | Is CBRD-27230 UPDATE chain reuse required for feat/oos conformance before merge, or deferred to a later milestone? Should Optimization Idea A and the M3 milestone text be rewritten to point at the accepted design? |
| `OOS-CL-07` | Reclamation domain and eventuality bound | unconditional-reclamation | Which pages are inside the reclaim guarantee (data pages only; header page excluded; legacy numerable files excluded?), and what progress witness or time bound makes 'eventually' testable? Is an implementation's sticky-page or legacy-file exception an accepted specification exception? |
| `OOS-CL-08` | Chain ownership wording: no cross-version sharing versus borrowed references | cross-version-sharing-wording | Which ownership statement is normative at the pin, and should the Writing Conventions be updated to the superseding invariant with an explicit 'effective once implemented' qualifier? |
| `OOS-DUR-07` | Corruption detection guarantees for OOS pages and logs | corruption-guarantees | What detection (checkdb, page checksum, stub/chain validation) and recovery behavior is guaranteed for a corrupted OOS page, chunk header or OOS log record? |
<!-- END GENERATED: spec-gaps -->

## 8. Section 6 scenario traceability

Every scenario of the normative context's §6 Test Scenarios (36 at the pinned hash) maps to at least one Requirement ID; no exclusion was needed. Notes mark where the scenario's own wording is superseded or partly UNSUPPORTED at the pin.

<!-- BEGIN GENERATED: scenarios -->
| §6 scenario | Title | Requirement IDs | Exclusion | Note |
|---|---|---|---|---|
| 1.1 | Insert + Select consistency | `OOS-SQL-01`, `OOS-REP-02` | — | DISK_SIZE verifies size arithmetic only; it is not a placement oracle. |
| 1.2 | Non-trigger verification | `OOS-REP-01` | — | Assertable only below both gates; the disputed band is OOS-REP-03. |
| 1.3 | Largest-first demotion (discriminating test for CBRD-26776) | `OOS-REP-02` | — | The scenario's debug oos.log evidence is unavailable at the pin for the SQL INSERT path (ticket 11 §6); use SHOW HEAP OOS chunk counts on an isolated table or an instrumented run. |
| 1.4 | Bulk insert | `OOS-SQL-01`, `OOS-REP-02` | — |  |
| 2.1 | OOS-backed attribute value change | `OOS-SQL-02`, `OOS-CL-02` | — | Eventual cleanup of the old chain is assert-after-eligibility. |
| 2.2 | Inline attribute change | `OOS-SQL-03`, `OOS-SQL-04` | — | The scenario's M1 wording (new chains for every version) is current behavior recorded as observation; the accepted CBRD-27230 reuse is UNSUPPORTED at the pin. |
| 2.3 | Repeated updates | `OOS-SQL-02` | — |  |
| 3.1 | Delete + verify gone | `OOS-SQL-05` | — |  |
| 3.2 | Delete all + reinsert | `OOS-SQL-05` | — |  |
| 4.1 | Atomicity (ROLLBACK) | `OOS-SQL-06` | — |  |
| 4.2 | UPDATE ROLLBACK | `OOS-SQL-06`, `OOS-CL-03` | — | The vacuum-after-rollback extension is OOS-CL-03 (expected finding CBRD-27237). |
| 4.3 | Durability | `OOS-DUR-01` | — |  |
| 4.4 | Isolation (MVCC) | `OOS-RD-02` | — |  |
| 5.1 | Committed INSERT redo | `OOS-DUR-01` | — |  |
| 5.2 | Uncommitted INSERT undo | `OOS-DUR-02` | — |  |
| 5.3 | Uncommitted UPDATE undo | `OOS-DUR-02` | — |  |
| 5.4 | Mixed committed/uncommitted | `OOS-DUR-01`, `OOS-DUR-02` | — |  |
| 5.5 | Multi-chunk crash recovery | `OOS-DUR-01`, `OOS-REP-07` | — |  |
| 6.1 | UPDATE visibility | `OOS-RD-02` | — |  |
| 6.2 | DELETE visibility | `OOS-RD-02`, `OOS-SQL-05` | — |  |
| 6.3 | Concurrent multi-UPDATE | `OOS-RES-04` | — |  |
| 7.1 | Large value (>16KB) | `OOS-REP-07` | — |  |
| 7.2 | Multi-chunk update | `OOS-REP-07`, `OOS-SQL-02` | — |  |
| 7.3 | Mixed sizes | `OOS-REP-07` | — |  |
| 8.1 | INSERT replicated correctly to slave | `OOS-OPS-01` | — |  |
| 8.2 | UPDATE replicated correctly to slave | `OOS-OPS-01` | — |  |
| 8.3 | DELETE replicated correctly to slave | `OOS-OPS-01` | — |  |
| 8.4 | Multi-chunk operations replicated correctly to slave | `OOS-OPS-01` | — |  |
| 9.1 | Record gate boundary | `OOS-REP-01`, `OOS-REP-02`, `OOS-REP-03` | — | The scenario's 4,060 B boundary is the normative target, UNSUPPORTED at the pin (gate is 4,086 B); assert only outside the disputed band. |
| 9.2 | Column eligibility floor | `OOS-REP-04`, `OOS-REP-05` | — | The scenario's 24 B floor is UNSUPPORTED at the pin (16 B); assert only for values at or below 16 B serialized. |
| 9.3 | NULL values | `OOS-REP-09` | — |  |
| 9.4 | Empty values | `OOS-REP-09` | — |  |
| 9.5 | Many OOS-backed attributes | `OOS-REP-10` | — |  |
| 9.6 | OOS + bigone rejection (CBRD-26937) | `OOS-REP-08` | — | The scenario's error code -1375 is context drift; the pinned code is -1382 (ticket 11 §4 g). |
| 10.1 | Bulk 1000+ rows | `OOS-SQL-01` | — |  |
| 10.2 | Repeated updates 50+ | `OOS-SQL-02` | — |  |
<!-- END GENERATED: scenarios -->

## 9. Context-drift notes (not requirements)

Reported to the context maintainer; none changes an expectation on its own.

- `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` is **-1382** at the pin; the context (§1 and §6 scenario 9.6) says -1375. Expected-error answers use the pinned code and text (ticket 11 §4 g).
- The reclaim invariant's "pending merge to `feat/oos`" note is stale for the pin: the mechanisms are present (ticket 11 §4 c).
- Scenario 1.3 says to confirm largest-first demotion through the debug `oos.log` `oos_insert … src.size=` line; at the pin the SQL INSERT path uses `oos_insert_many`, which writes no debug line (ticket 11 §6). Activation evidence for public cases comes from SHOW HEAP OOS chunk counts on an isolated table or from instrumented runs.
- §5 says no release-build tool proves a row went OOS; `SHOW HEAP OOS OF <class>` and `diagdb -d 1` owner descriptors exist at the pin and prove per-class placement (per-attribute placement remains debug/instrumentation only).
- The §5 Limitations row for CBRD-26776 still says "strictly greater than 16B"; that wording is the `OOS-REP-14` Specification gap.

## 10. Change control

- **Adding a requirement:** append the next number in its family; fill every field; run `python3 tools/check_campaign_records.py` and `python3 tools/render_docs.py`; commit JSON and rendered document together.
- **Moving the pin:** a recorded decision on the map. Update `pin` and every citation's `revision` and `content_hash`; re-verify each `pinned_observation`; IDs never change.
- **A new design choice or an answered authority question:** reopens the map with a decision ticket (spec Reopening rule). The catalogue then changes a status, never an ID.
- **Accepted exclusions** live in the coverage matrix, not here, and only the user writes them.

## 11. Ticket 12 criteria checklist

| Criterion | Where met |
|---|---|
| Stable ID, exactly one citation with pinned revision and hash, one of eight families, status among assertable / observation-only / BLOCKED / UNSUPPORTED | §2, `requirement.schema.json`, checker checks `id-*`, `one-citation`, `citation-*`, `eight-families`, `status-*` |
| Every §6 scenario maps to a requirement or a reasoned exclusion | §8, `scenario-map.json`, checker `scenario-*` |
| Accepted-but-unimplemented designs appear as BLOCKED or UNSUPPORTED (CBRD-27230, ADR-0004/CBRD-26939, CBRD-27057, CBRD-26950) | §6, checker `accepted-unimplemented` |
| Mixed-era statements listed as Specification-gap requirements with the authority question | §7, checker `mixed-era` |
| Authority policy encoded per requirement (assert / assert-after-eligibility / observe / withhold) | §3, checker `status-policy`, `reclamation-policy` |
| Manifest, matrix, attempt-record and replay-bundle schemas | companion document and `schemas/` |
| Vocabulary committed on its own; catalogue and schemas committed in the campaign folder | docs repository history |
