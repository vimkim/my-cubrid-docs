# Ticket 07 — preliminary requirement-to-evidence matrix

Date: 2026-09-09. **Preliminary, not acceptance.** Documentation-only audit of existing source and recorded results; no engine edits, test runs, experiments, ticket closures, commits, pushes, or gate waivers.

Authority: [SPEC], [ADR], and the [clarified completion path](acceptance-completion-path-213ce80f5-codex.md).

The acceptance decision remains blocked: ticket 05 has a reproduced baseline rollback/vacuum defect and incomplete partitioned SERVER evidence; ticket 06 has demonstrated scoped resource savings but an **inconclusive, unmet runtime gate**. Ticket 07 requires one integrated-revision evidence set and final review. Final record routing remains unchanged. Wait specifically for CBRD-27237; do not assume CBRD-27230 supplies its fix or that CBRD-26950 is necessarily its prerequisite.

## How to read this matrix

- **Supported** means the cited source and recorded observations support the stated, bounded behavior on the identified revision. It never means all possible inputs or the future integrated revision passed.
- **Partial** means relevant evidence exists but is narrower than the whole requirement, or contains an explicitly unverified branch.
- **Failed** means saved observations contradict the required behavior.
- **Missing** means this audit has not located adequate evidence; it is not proof that no such test exists anywhere.
- **Unmet** means an acceptance decision cannot pass from the evidence, including inconclusive timing.
- **Policy** means an accepted constraint, not a runtime test result.

Every numbered spec requirement has its own row. Ticket checklist items have stable audit IDs in their original order and cross-reference those rows; original checklist marks are not changed. All rows inherit **R0** (final provenance and change-impact audit), even when not repeated in the last column. A row's evidence ID resolves to its report/raw artifacts and revision in the registers below.

## Revision and evidence provenance

| ID | Exact source identity / mode | Applicability |
| --- | --- | --- |
| B | Original PR head `b871ea386d2c5419b7abae07dda58b9b7f36377a` | Original engine; tests may be overlaid. Not identical to later ticket-01/ticket-02 frozen libraries. |
| C1 | B plus ticket-01 prefactor; per-run complete diff in E1 | Debug SA characterization. No effective-key production route yet. |
| C2 | B plus tickets 01–02; per-run complete diff in E2 | Debug SA INSERT milestone; historical helper name `heap_attrinfo_get_insert_key` is superseded by C3. |
| C3 | B plus tickets 01–03; per-run complete diff in E3 | Debug SA complete INSERT/UPDATE routing. Candidate library SHA-256 `6d5eb8e51466a5931d047bc518f80464e9dc6d75f27b4757762138e1ca01bc14`. |
| P | B plus five engine-file changes; engine-diff SHA-256 `3d978ff8134516d0ab26a809b6fd790bd289a6865476a215921c8fa5e6eea34a` | Pre-format routing implementation. E4 varies test overlays/builds; E6–E8 use matched release SA builds. |
| F | Current HEAD `213ce80f54dc54130fcef22e616cb28f4835f6d5`; engine-diff SHA-256 against B `8ccb237954a348b5bef6f1b653dbe44e31816ba5c21d3b856f0d0c33684a215c` | Current source inspected; no engine dirt. E4F was run immediately before this commit, so JSON HEAD still says B with the formatted diff. Do not relabel it a post-commit full-suite run. |
| I | Future baseline/candidate including the actual CBRD-27237 repair | **Not yet identified or tested.** No existing artifact has this identity. |

Current spec SHA-256 checked during this audit: `dfa82a53337a2cf85c9d18bfe3707d99670a6e7070320a97fc3183b50c01f31f`. Current engine diff hash matches F above. The uncommitted red regression in `unit_tests/oos/test_oos_real_vacuum_server.cpp`, changed CCI submodule, user files and artifacts remain untouched.

Evidence JSON `source_revision` alone is insufficient: most runs say B because the implementation was an uncommitted diff. Resolve **HEAD + embedded diff + test source + engine library/binary hashes + build mode + configuration** together. The reference frozen before ticket 02 includes ticket 01 and has library hash `266c72980f5718173eb59c546c16120dfe4a271de8927788c32b2dbfd5d2f4e0`; the frozen pre-ticket-03 reference includes ticket 02 and has hash `f5b382475d6e6752d61ac1e1c9a136c8db117039e66a7b5b04b2c0d85143fc36`. Neither should be called an untouched B binary.

### Evidence register

| ID | Saved evidence and observations | Revision / limits |
| --- | --- | --- |
| E1 | [Ticket 01](ticket01-routing-prefactor-b871ea386-codex.md): baseline/final SHOW 10, storage 25, transactions 8; range/list/hash, NULL, explicit child rejection and owner counts | B versus C1, debug SA; characterization, not optimization or SERVER proof |
| E2 | [Ticket 02](ticket02-insert-routing-b871ea386-codex.md): 20 SHOW/routing, 25 storage, 8 transaction, 4 bigone; [13-type SQL reference](ticket02-evidence/reference-legal-csql-alias.json), [candidate](ticket02-evidence/final-legal-csql.json), [extra INSERT reference](ticket02-evidence/reference-extra-csql.json), [candidate](ticket02-evidence/candidate-extra-csql.json) | C1 frozen reference versus C2; debug SA. Discriminating LIST default seam supplements HASH SQL. Failed alias/missing-symbol attempts are explicitly excluded. |
| E3 | [Ticket 03](ticket03-update-routing-b871ea386-codex.md): 28 SHOW/routing, 25 storage, 8 transaction, 4 bigone, 7 nonpartitioned UPDATE/DELETE; [UPDATE differential](ticket03-evidence/verified-update-contracts.json), [reference](ticket03-evidence/reference-update-contracts.json); [duplicate reference](ticket03-evidence/probe-reference-duplicate-context.json), [candidate](ticket03-evidence/verified-duplicate-context.json); [forced INT retries](ticket03-evidence/incr-decr-buffer-retry.json) | C3 debug SA, with distinct C1/C2 reference libraries identified above. Historical-record seam is not a physical old child-row test. |
| E4 | [Ticket 04](ticket04-cleanup-b871ea386-codex.md): [eight preparation cases](ticket04-evidence/four-preparation-failures.json), [codec cleanup](ticket04-evidence/codec-failure-cleanup.json), [publication preservation](ticket04-evidence/routing-failure-publication.json), [actual payload allocation failure](ticket04-evidence/payload-allocation-cleanup.json), [LOB/index failure](ticket04-evidence/lob-index-cleanup.json), [LOB retry/inventory](ticket04-evidence/lob-retry-lifetime.json) | P, debug SA. Two actual payload malloc failures are not arbitrary payload-codec-return failures. LOB observer verifies two copies/deletions across two attempts and six restored abort inventories. |
| E4S | [Publication](ticket04-evidence/candidate-publication.json): 11 SERVER cases. [Configured-suite ledger](ticket04-evidence/configured-suite-results.json): 21/25 binaries pass initially; three startup-only failures subsequently pass with [short server socket](ticket04-evidence/short-socket-full-server.json), [delete](ticket04-evidence/short-socket-full-delete-server.json), [file removal](ticket04-evidence/short-socket-full-remove-file-server.json) | P debug, mixed SA/SERVER binaries. Combined result 24/25, **not all green**. Broad existing server suites do not by themselves map to the required partitioned lifecycle scenarios. |
| E4F | [Formatted routing/cleanup](ticket04-evidence/formatted-routing-cleanup.json): all 32 named tests pass, exit 0 | F engine content, debug SA; library hash `99dc234eb8dac5c1c161d358ee0aacb8b1dc83ba6c8022e707070802989b8225`. Not a complete formatted-suite or release measurement run. |
| E5 | [Lifecycle report](tickets04-07-lifecycle-blocker-b871ea386-codex.md); [native baseline failure](ticket05-evidence/baseline-native-rollback-vacuum.json), [candidate repeat](ticket05-evidence/candidate-rollback-vacuum-repeat.json), other repetitions in [directory](ticket05-evidence/) | B and routing candidate debug SERVER. Original OOS read succeeds after abort then fails with -2 after committed-delete vacuum witness; test process traps on assertion. Does not use partition routing. |
| E6 | [Resource/timing report](ticket06-measurements-b871ea386-codex.md); [baseline diagnostic](ticket06-evidence/baseline-diagnostic-final.json), [candidate diagnostic](ticket06-evidence/candidate-diagnostic-final.json), [harness](ticket06-evidence/test_oos_sql_pr7600_measure.cpp), [observer](ticket06-evidence/count-routing.gdb) | B/P matched release SA. Library hashes `da01bbee3f0e0045b1671dd3a5d25c3be56f5360c91709357125d4fa57364556` / `670b6018e45c0985e1f319af833f3936dd788446e2c5faba648126bdbaf167c5`. Nine workloads; scoped counters, not exhaustive process allocations. |
| E7 | [Interleaved report](ticket06-interleaved-b871ea386-codex.md), [52-run manifest](ticket06-evidence/interleaved-20260909/manifest.json) | B/P release SA; correctness passes as recorded, shared-host CPU/elapsed comparisons inconclusive; no outlier deletion |
| E8 | [CPU attribution](ticket06-cpu-attribution-b871ea386-codex.md), [raw summaries/runs](ticket06-evidence/cpu-attribution-20260909/) | Same B/P release binaries; +0.689% whole-process user instructions in small inline control, **not +0.689% runtime**; 8 counter/2 sampled-profile runs |
| E9 | [Focused standards/spec review](tickets04-06-review-b871ea386-codex.md), earlier reviews in E1/E2 | Pre-format working diff, focus 04/06 with 01–03 context; two evidence findings closed, optional numeric-tag maintainability suggestion remains. Not a final integrated all-spec review. |
| E10 | [Final-route retention](destination-reuse-review-213ce80f5-codex.md), [completion path](acceptance-completion-path-213ce80f5-codex.md), [published dependency comment](http://jira.cubrid.org/browse/CBRD-27237?focusedCommentId=4776296&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-4776296) | Accepted decisions and dated investigation, not runtime evidence; no new upstream status query in this audit |

This audit inspected the reports and representative raw JSON: E4F's 32 named successes; E4 payload/LOB diagnostics; E4S publication and suite ledger; E5 baseline/candidate assertion failure; E6 raw counter records. E1–E3 differential and E7/E8 aggregate conclusions are supported by their retained reports/artifacts, but their entire comparison pipelines were **not rerun** here. A link is not a new execution or independent verification of every sample.

### Source register (F, current local source)

| ID | Source contract inspected |
| --- | --- |
| S1 | [Effective key](../../../cb/CBRD-27089-has-oos-but-no-oos/src/storage/heap_file.c:12117): supplied-old-record reader / omission / assigned clone, temporary increment, scalar codec, explicit cleanup |
| S2 | [Attribute router](../../../cb/CBRD-27089-has-oos-but-no-oos/src/query/partition.c:3571): stable context slot, old value cleared, shared selector, copied destination, key cleared; [record router](../../../cb/CBRD-27089-has-oos-but-no-oos/src/query/partition.c:3618): root decode, representation restoration and destination patch |
| S3 | [Attribute-force dispatch](../../../cb/CBRD-27089-has-oos-but-no-oos/src/transaction/locator_sr.c:7767): early route, first-pass destination, retained final force; [INSERT guard](../../../cb/CBRD-27089-has-oos-but-no-oos/src/transaction/locator_sr.c:4990), [UPDATE guard](../../../cb/CBRD-27089-has-oos-but-no-oos/src/transaction/locator_sr.c:6014): agreement before locks/movement/write |
| S4 | [Owner-aware first pass](../../../cb/CBRD-27089-has-oos-but-no-oos/src/storage/heap_file.c:12928): original cache retained, increments-already-applied false; [LOB preparation](../../../cb/CBRD-27089-has-oos-but-no-oos/src/storage/heap_file.c:12217), [payload writer](../../../cb/CBRD-27089-has-oos-but-no-oos/src/storage/heap_file.c:12705) |
| S5 | [SQL tests](../../../cb/CBRD-27089-has-oos-but-no-oos/unit_tests/oos/sql/test_oos_sql_show.cpp:506): 32 tests, including 13-type tables, historical record seam, source-state assertions, failure and ownership checks |
| S6 | [Uncommitted regression](../../../cb/CBRD-27089-has-oos-but-no-oos/unit_tests/oos/test_oos_real_vacuum_server.cpp:831): original chain readable before vacuum; distinct committed-delete witness allocated before UPDATE; original chain must remain readable afterward |

Source links are local-workspace navigation aids; immutable identity is F plus the explicitly noted test-only dirt, not a promise that line numbers survive a future integration.

## Revalidation obligations after CBRD-27237

| ID | Required future work (not authorized or executed here) |
| --- | --- |
| R0 | Inspect exact fix, dependencies and diff; pin repaired baseline and routing candidate with matching builds/configuration, hashes and test overlays. Determine which old evidence survives; do not silently include 27230 or format changes. |
| R1 | Rerun affected full SQL/routing, storage, transaction, bigone and nonpartitioned suites; retain exact values, errors and owner observations. Cover legal types and targeted operations on the integrated engine. |
| R2 | Revalidate supplied-old/default values, scalar equivalence, increments and forced retries, contexts and representation IDs; map any normalization/representation changes to discriminating tests. |
| R3 | Revalidate preparation/publication failure, payload allocation, LOB retry/external inventories, index/write cleanup and subsequent operations. Resolve the explicit failure-evidence gaps below rather than assume generic success covers them. |
| R4 | Required CBRD-27237 regression first, plus proof committed obsolete chains are still reclaimed. Then complete partitioned SERVER same/moving UPDATE old-reader visibility, moved rollback, committed/uncommitted recovery and vacuum, with deterministic coordination and values/owners. A passing regression alone does not close ticket 05. |
| R5 | Repeat affected paired resource and CPU/elapsed measurements on controlled matched builds; retain nine workloads, small/nonpartitioned controls, noise and raw distributions. Timing must meet the existing spec; counters alone cannot waive it. |
| R6 | Final integrated standards/spec review; reconcile every row and ticket requirement to final provenance, maintain full scope, and report blocked/unmet if any required proof remains missing. |

If the fix changes stub size, on-disk layout, demotion behavior or replication contracts, explicitly approve and test that integration scope. Existing 16-byte-format measurements cannot validate a new format. If the fix does not touch these, do not presume such migration is required. Regardless of mechanism, rollback safety and eventual obsolete-chain reclamation must both hold.

## User stories — all 37

| ID | Requirement | Evidence / tested revision | Assessment and gap | Revalidate |
| --- | --- | --- | --- | --- |
| US01 | Same INSERT destination | E1/E2, E4F; B/C1/C2/F; S2/S3 | Supported sampled routes, not I | R1 |
| US02 | OOS belongs to destination heap | E2/E3/E4F, E6; C2/C3/F/B/P | Supported owner counts; partition lifecycle safety remains partial | R1/R4 |
| US03 | RANGE boundary equality | E1, E4F; B/C1/F | Supported keys around boundary 10 | R1 |
| US04 | LIST and HASH | E1/E2/E3/E4F; B/C1/C2/C3/F | Supported route examples and type matrix; not every type × partition mode combination | R1/R2 |
| US05 | Existing expression semantics | S2; E1–E3/E4F | Supported ABS, id+1, nested string and compressed-key expressions; shared evaluator source | R1/R2 |
| US06 | All legal key types, no fallback | S1/S3; E2/E3/E4F, C2/C3/F | 13 type families exercised; no type fallback in dispatch. All values/collations are not exhaustively tested | R1/R2 |
| US07 | NULL placement/rejection | E1/E2/E3/E4F | Supported HASH/RANGE/LIST acceptance and LIST missing-NULL rejection | R1 |
| US08 | Explicit partition validation | E1/E4F; S2/S3 | Supported successful/rejected child INSERT and UPDATE | R1 |
| US09 | Missing destination errors | E1/E4/E4F | Supported -891 and later successful operations | R1/R3 |
| US10 | Omitted INSERT defaults | E2/E4F; S1 | Supported 13-type LIST defaults and unchanged assignment slots | R1/R2 |
| US11 | Dynamic/generated values once | E2/E4F; S1/S5 | Partial: AUTO_INCREMENT boundary and CURRENT_DATE equality pass; stable CURRENT_DATE alone cannot detect reevaluation. Source consumes assigned value; not a general evaluation-count proof | R2 |
| US12 | Column-domain conversion | E2/E3/E4F; S1 | Supported '11'→INT, CHAR and codec/domain cases; not exhaustive conversion errors | R1/R2/R3 |
| US13 | CHAR padding/collation | E2/E3/E4F | Supported assigned CHAR unchanged, LIST padding and utf8_en_ci cases; all collation combinations not established | R2 |
| US14 | Temporal variants | E2/E3/E4F | Supported DATE/TIME, TIMESTAMP/TZ/LTZ, DATETIME/TZ/LTZ values; not comprehensive DST/timezone transitions | R2 |
| US15 | Unchanged UPDATE uses old row | E3/E4F; S1/S3 | Supported supplied-record route and unchanged OOS-key SQL; concurrent version provenance not yet demonstrated | R2/R4 |
| US16 | Old representation/missing attribute | E3/E4F; S1/S5 | Supported historical serialized-record seam; explicitly not a physically stored pre-partition child row | R2/R4 |
| US17 | Key-changing movement | E1/E3/E4F/E6; S3 | Supported SA movement/owners; SERVER lifecycle partial | R1/R4 |
| US18 | Ordinary arithmetic | E3/E4F | Supported integer-width arithmetic separately from dedicated increments | R1/R2 |
| US19 | INCR/DECR once | E3/E4F; S1/S4 | Supported source pending-state preservation, actual row values, forced INT retries; not every width under forced retry | R2 |
| US20 | Increment limits | E3/E4F | Supported three integer widths and overflow/underflow-to-zero, not generic arithmetic substitution | R2 |
| US21 | LOB copy/delete lifecycle | E3/E4/E4F; S4 | Supported tested inline/demoted, written/unchanged, retry and abort inventory cases; broader SERVER lifecycle partial | R3/R4 |
| US22 | Small FORCE_OUTLINE ownership | E1–E4F/E6 | Supported 64-byte payload cases with child-only ownership | R1/R5 |
| US23 | Large/multiple external values | E2/E3/E4F/E6 | Supported uncompressed multi-chunk/non-key payloads and multiple attributes; not every layout | R1/R5 |
| US24 | OOS+bigone rejected before insert | E2/E3/E4F, S5 | Supported error and no OOS file; non-OOS oversized control succeeds | R1/R3 |
| US25 | Rollback preserves values/ownership | E3/E4 SA passes; E5 B/candidate SERVER fails | **Failed broader lifecycle guarantee** after vacuum; immediate SA rollback is insufficient | R3/R4 |
| US26 | Concurrent old readers | E4S generic suites, E3 SA | **Missing direct partitioned same/moving UPDATE old-reader evidence**; existing suites alone insufficient | R4 |
| US27 | Recovery/vacuum safety | E5 | **Failed vacuum; missing complete scoped recovery matrix** | R4 |
| US28 | Nonpartitioned behavior | E1–E4S/E6/E7 | Supported functional controls; runtime comparison still not accepted | R1/R5 |
| US29 | REPLACE/duplicate UPDATE | E3/E4F; S2/S3 | Supported independent probe reference; stale context-key defect corrected in C3. Does not claim duplicate probes removed | R1/R2 |
| US30 | Context lifetime across rows | E1/E3/E4/E4F; S2 | Supported alternating/invalid/recovery and duplicate contexts. Wrapper error destroys context; no claim of reusing a destroyed context | R2/R3 |
| US31 | Failure resource ownership | E4/E4S/E6; S1/S4 | Partial overall: bounded failure/observer proofs, not exhaustive allocation campaign; SERVER lifecycle still failed | R3/R4 |
| US32 | Single-failure errors | E1/E4/E4F | Supported selected routing/OOM/index/bigone errors; every possible error category not established | R3 |
| US33 | Multi-error precedence may differ | SPEC/ADR policy; E4 | Policy accepted; **dedicated independently multiply-invalid statement evidence not located** in audited tests | R3 |
| US34 | Useful allocation/copy savings | E6 B/P | Supported scoped large-row savings; not I, not total RSS/all copying | R5 |
| US35 | Separate small/nonpartitioned controls | E6/E7/E8 B/P | Controls measured separately; runtime acceptance **unmet**, not waived by instruction counts | R5 |
| US36 | Behavior-level interfaces | S5/S6; E1–E5 | Supported SQL/SHOW and focused routing/failure seams; diagnostics intentionally separate from functional assertions | R1/R3/R4/R6 |
| US37 | Escalate failed gates | E5–E10; current ticket states | Policy followed: failed lifecycle and inconclusive timing disclosed; no final acceptance | R6 |

## Implementation decisions — all 15

| ID | Requirement | Evidence / revision | Assessment and gap | Revalidate |
| --- | --- | --- | --- | --- |
| ID01 | Scoped attribute-force, per-heap owner, no format/SQL change | S1–S4 F; E2/E3/E6 | Supported five engine-file delta and owner tests; actual dependency diff still unknown | R1/R6 |
| ID02 | Owned temporary key, assignments/side effects untouched | S1/S2 F; E2/E3/E4 | Supported source-state, publication and cleanup tests; no complete allocator-failure proof | R2/R3 |
| ID03 | Stored-decoder-equivalent scalar key | S1 F; E2/E3/E4F | Supported codec reuse and discriminating examples; mathematical equivalence for all domain values not proved by test enumeration | R2 |
| ID04 | Complete legal families and partition modes; no fallback | S1/S3 F; E2/E3/E4F | Supported 13 families and shared selector; cross-product limitations in US04/06/13/14 remain explicit | R1/R2 |
| ID05 | Evaluated defaults/generated assignments; supplied old representation | S1 F; E2/E3/E4F | Source and bounded seam support; US11/15/16 limitations | R2/R4 |
| ID06 | Pending increment only on temp; real first pass once incl. retry | S1/S4 F; E3/E4F | Supported normal widths and forced INT retries; not all retry combinations | R2 |
| ID07 | Shared matching, explicit/root outputs, stable bindings | S2 F; E1/E3/E4/E4F | Supported source and SQL/seam results; metadata/concurrency interaction not established by SA | R2/R4 |
| ID08 | First-pass destination override, source identity retained | S3/S4 F; E3/E4F | Supported false already-applied flag, unchanged source cache, final owner | R2/R3 |
| ID09 | One full-row transform; retain payload/retries/copyarea | S3 F; E6 B/P | Supported diagnostic counts and structure, not elimination of retries or all copying | R5 |
| ID10 | LOB preparation remains local to real transform | S1/S4 F; E3/E4 | Supported tested locator lifecycle/inventories, no source-class retarget | R3/R4 |
| ID11 | Retain final route/representation/locks/index/move; reject disagreement | S2/S3 F; E1/E3/E4F/E10 | Successful agreement and source guard supported. Artificial disagreement cleanup branch not fault-injected; concurrency/locks need SERVER evidence | R2/R3/R4 |
| ID12 | Buffer/publication/transaction cleanup, no ad hoc chain delete | S1/S4 F; E4/E4S/E6 | Supported bounded cleanup; lifecycle guarantee contradicted by E5 baseline defect | R3/R4 |
| ID13 | Single errors, multi-error policy, pre-insert bigone rejection | E1/E2/E4/E4F; S5 | Partial: selected single errors/rejection pass; multi-error evidence gap US33 | R3 |
| ID14 | Nonpartitioned/duplicate probes and unrelated entry points unchanged | S3 F; E3/E4F/E6 | Supported scoped source/SQL; not blanket validation of every unrelated API | R1/R6 |
| ID15 | All gates required; reopen, no automatic split/final-route removal | SPEC/ADR/E10 | Policy retained; overall acceptance **unmet** | R6 |

## Testing decisions — all 14

| ID | Requirement | Evidence / revision | Assessment and gap | Revalidate |
| --- | --- | --- | --- | --- |
| TD01 | SQL/SHOW seam: values, placement, owners, errors, transactions | S5; E1–E4F | Supported; SHOW counts chunks, not logical chains. Row equality alone not used as ownership proof | R1 |
| TD02 | Extend existing ownership/rollback/storage/publication tests | E1–E4S | Supported prior-art reuse; SA explicitly separated from SERVER | R1/R4 |
| TD03 | Existing failure hooks plus routing/final write failures | E4/E4S | Partial: real payload malloc and final index failures established; not arbitrary payload-codec returns or distinct final heap-write failure | R3 |
| TD04 | One effective-key differential seam; normalized result/state | S5; E2/E3/E4F | Supported independent caches and route OID/HFID; exact LIST defaults avoid hash collision as sole oracle; no bitwise DB_VALUE claim | R2 |
| TD05 | Independent mutable inputs/fixtures and preserved reference | E1/E2/E3 | Supported documented frozen libraries and cache separation; final pair I still absent | R0/R2 |
| TD06 | Full routing matrix incl. NULL, expressions, OOS string, alternating context | E1–E3/E4F | Supported stated scenarios; type-family tests are not exhaustive legal expression/collation enumeration | R1/R2 |
| TD07 | Defaults/generated/old/arith/INCR/DECR/limits/retry | E2/E3/E4F | Partial at full breadth: US11/16/19 caveats; no new execution here | R2 |
| TD08 | Storage/LOB/same+moved/bigone/rollback matrix and owners | E2/E3/E4/E6 | Supported SA scenarios, partial lifecycle scope after vacuum | R1/R3/R4 |
| TD09 | Partitioned SERVER MVCC, movement rollback, recovery/vacuum; attribute baseline failures | E4S/E5/E10 | Attribution supported; **required successful lifecycle matrix missing/failed** | R4 |
| TD10 | Each failure category, selected multi-invalid, cleanup and next writes | E4/E4S/E4F | Partial: source-state and bounded failures pass; multi-invalid and broader failure categories require explicit disposition, not checklist inference | R3 |
| TD11 | Separate diagnostic counters, bytes/peak/copies/routes/CPU/elapsed | E6/E8 B/P | Supported scoped measurements. OOS insert-many batches are not total chunks; leases not fresh malloc; no all-process allocation accounting | R5 |
| TD12 | Matched paired workloads, warmup/repetition/noise/distributions | E6/E7/E8 B/P | Supported methodology and saved controls; no final-I pair or stable runtime outcome | R5 |
| TD13 | Eliminate whole probe, useful savings, resolve runtime regressions | E6 supported mechanism; E7/E8 timing | **Unmet overall**: runtime uncertainty; counters do not establish no slowdown | R5/R6 |
| TD14 | Execution needs approval; preserve full scope, test-first slices | Ticket history E1–E4/E10 | Policy/history supported; this document authorizes no runs | R6 |

## Ticket checklist crosswalk

Each suffix is the original checklist item's ordinal, not a new ticket. Evidence, revision, gap and revalidation are inherited from the listed matrix rows; the final column identifies any ticket-specific limit. This crosswalk does not toggle the tickets' marks.

| Checklist ID | Mapped requirements | Additional assessment |
| --- | --- | --- |
| T01.1 | TD05, R0 | B/C1 characterization identities in E1 |
| T01.2 | US01, US03–09, TD01 | E1 reference observations |
| T01.3 | TD01–04 | SQL plus approved focused seam |
| T01.4 | ID07, ID11 | C1 extraction preserved record adapter |
| T01.5 | TD05 | Independent caches and databases |
| T01.6 | US30, ID07 | Error destroys context; later statement is recovery |
| T01.7 | ID09, TD05 | Probe deliberately retained during C1 only |
| T01.8 | US37, TD09 | No C1 functional baseline failure; later E5 retained |
| T02.1 | TD01, TD04–05, TD14 | E2 red/green and frozen reference |
| T02.2 | US10–13, ID02–05 | US11 evaluation-proof limit |
| T02.3 | US03–09, US13–14, ID04 | Type family versus full input-space distinction |
| T02.4 | ID03, ID09, ID15 | Scalar only; full probe removed from scoped INSERT |
| T02.5 | ID02, ID07, ID10, ID12 | Source plus E4 publication proof |
| T02.6 | ID08, ID06 | Normal first pass, not rebuild contract |
| T02.7 | ID11, US08, US17 | Source guard, not injected disagreement proof |
| T02.8 | US22–24, TD08 | SQL ownership/storage coverage |
| T02.9 | ID09, US28, TD11 | Copyarea retained; counts in E6 |
| T02.10 | ID14, US29 | C2 UPDATE retained; C3 later transitions it |
| T03.1 | US15, US18–20, TD14 | E3 red/green retained |
| T03.2 | US15–16, ID05 | Supplied historical seam, not physical child proof |
| T03.3 | US19–20, ID06 | Forced retries limited to INT |
| T03.4 | US06, US13–16, ID04 | 13-family UPDATE/list coverage and SQL reference |
| T03.5 | ID08, ID11, US17 | SERVER lock/visibility proof still R4 |
| T03.6 | US21, ID10 | E4 strengthens E3 LOB evidence |
| T03.7 | US02, US17, ID01 | SA placement supported; old-value safety E5 fails |
| T03.8 | US28–30, ID14 | Duplicate retained-context fix included |
| T03.9 | US37, TD09, TD13 | Milestone not overall acceptance |
| T04.1 | US31–33, TD03, TD10 | Partial broader failure evidence despite checked item |
| T04.2 | TD02–03 | Existing hooks/server publication; no general framework |
| T04.3 | ID02, ID12 | E4 seeded publication preservation and reset failures |
| T04.4 | US30–31, ID02, ID07 | Codec output/source/context checks |
| T04.5 | US25, US31, TD10 | SA owner/next-write proof; SERVER post-vacuum fails |
| T04.6 | US21, US24, TD08 | Actual LOB retry and inventories in E4 |
| T04.7 | US32–33, ID13 | Multi-invalid evidence not located |
| T04.8 | US28–29, ID14 | Nonpartitioned/duplicate suites |
| T04.9 | US37, TD09 | E5 attribution; no incidental repair |
| T05.1 | TD05, TD09, R0 | Paired minimal regression exists, not full paired lifecycle matrix |
| T05.2 | US26, TD09 | Missing scoped concurrent old-reader evidence |
| T05.3 | US17, US25, TD09 | SA proof not SERVER moved-rollback closure |
| T05.4 | US27, TD09 | Missing scoped committed/uncommitted recovery matrix |
| T05.5 | US27, TD09 | E5 fails; fix needed |
| T05.6 | TD09, R4 | Witness proves vacuum progress, not deterministic multi-session matrix |
| T05.7 | US37, TD09 | Baseline attribution documented though original checkbox remains open |
| T05.8 | R0, R4, R6 | I and revalidation absent |
| T06.1 | TD12, R0 | Matched B/P pair, not I |
| T06.2 | US22–23, US35, TD12 | Nine workloads plus controls |
| T06.3 | TD11 | Scoped bytes/counts, not exhaustive allocations |
| T06.4 | ID09, TD13 | Full-probe elimination demonstrated |
| T06.5 | TD01, TD08, TD12 | Values/owners checked during measurement |
| T06.6 | US35, TD12 | Per-process drift retained, no pooled acceptance |
| T06.7 | ID09, ID11, TD11 | Both routes and key/payload work retained in accounting |
| T06.8 | US34–35, TD13 | Resource benefit supported; compound runtime gate unmet |
| T06.9 | US37, ID15, TD13 | Inconclusive treated as unmet |
| T06.10 | TD12, R0, R5 | Retained methodology requires final revision reruns |
| T07.1 | R0, R6 | Final integrated revision/binaries absent |
| T07.2 | US01–37, ID01–15, TD01–14 | This preliminary matrix maps all; final authoritative closure absent |
| T07.3 | US06, ID03–04, ID09 | Source and sampled coverage; final I untested |
| T07.4 | US10–21, US30–31, ID02–08, ID10–12 | Cross-revision bounded proofs, remaining gaps above |
| T07.5 | US02, US08, US17, US25–27, ID11–12 | SERVER lifecycle and integrated final-force proof incomplete |
| T07.6 | TD08–13, R0 | Cannot combine SA and SERVER/mixed revisions into all-green |
| T07.7 | E9, R6 | Focused prior reviews not final integrated two-axis review |
| T07.8 | US34–35, ID15, TD13 | Runtime gate open; baseline defect still blocks acceptance |
| T07.9 | US37, E10, R6 | Preliminary unmet-gate report, not final acceptance recommendation |
| T07.10 | TD14, E10 | Spec unchanged; no ticket closure or publication in this task |

## Scope constraints and unnumbered requirements

| Requirement from Problem/Solution/Out of Scope/Further Notes | Evidence / gap | Revalidation |
| --- | --- | --- |
| Improve redundant temporary work without assuming baseline is slow | E6 proves scoped resource savings; E7/E8 do not prove baseline performance defect or candidate runtime acceptance | R5 |
| Preserve per-heap ownership; no shared files/new SQL/new format | Five-file routing delta F; owner tests E2–E4F. Future repair format dependencies unknown | R0/R1/R6 |
| No global preparation split, LOB relocation or broad force redesign | S1–S4 and E10 retain local key preparation and real-transform side effects | R0/R6 |
| Do not remove final routing or all duplicate probes | S2/S3, E3 and accepted retention decision | R0/R1/R6 |
| Do not change policy/threshold/compression/reuse/vacuum/replication incidentally | Routing diff limited to five files; preserves existing serializer policy, no new shared-chain cleanup. Dependency repair needs explicit independent scope | R0/R6 |
| Do not silently narrow legal coverage or repair baseline defects in routing task | ID04/15, E5/E10; type test limitations remain disclosed, not waivers | R2/R4/R6 |
| Ready-for-agent/ticket resolved is not execution or shipping permission | Spec/ticket execution gates; this audit uses only saved results and read-only source | R6 |
| Preserve final copyarea/attrinfo and ordinary buffer/payload work | S3/S4, E6; no claim those costs disappear | R2/R5 |
| Build and test commands must preserve private fixtures and provenance | Retained runner and E4 socket correction; no commands executed here that start a database. Revalidate scripts, debugger locations and paths before any authorized rerun | R0–R5 |

## Principal proof gaps, not new implementation instructions

1. **Lifecycle blocker:** E5 contradicts the required post-rollback survival guarantee. The expected CBRD-27237 fix must be reviewed and pass the retained regression and eventual committed-chain reclamation checks. The full partitioned old-reader/movement/recovery/vacuum matrix remains necessary afterward.
2. **Runtime gate:** large-value allocation/copy savings do not answer small-inline runtime uncertainty. E8's instruction count is narrower than runtime; final routing retention is not a slowdown waiver.
3. **Revision gap:** post-format E4F is one 32-test SA binary, not an all-green final suite. Pre-format measurements and milestone results cannot simply be renamed F or I. E4S remains 24/25 even after startup-only reruns.
4. **Failure breadth:** the audit found exact routing/OOM/index/bigone failures and genuine payload malloc/LOB lifetime observations. It did not locate dedicated independently multiply-invalid statements, an artificial early/final disagreement cleanup run, a distinct final heap-write failure, or arbitrary real payload-codec-return failure coverage. These are evidence limits, not newly diagnosed engine defects. Map each to the spec's required failure categories before final acceptance; do not assume a checked ticket establishes every branch.
5. **Semantic proof breadth:** the tests cover all listed legal type families, including discriminating LIST defaults and source-state preservation, but not every type × partition mode × collation × timezone transition. CURRENT_DATE equality alone is not an evaluation-count oracle. Combine the source contracts with appropriately discriminating tests; do not demand an impossible enumeration or silently downgrade complete legal support.
6. **Historical/source-version seam:** the missing historical key test deliberately supplies serialized bytes captured before adding the key. It does not establish how ALTER redistributes physically existing partition rows or how concurrent old versions behave. Those are separate observations.
7. **Review gap:** earlier focused standards/spec review closed two concrete evidence issues, but did not review a future integrated repair or certify all 66 requirements. Final review remains R6.

The normative OOS context (last updated 2026-09-08) supplies per-heap ownership, rollback/MVCC value survival and LOB-locality requirements. Its dated narrative connecting 27230 to 27237 is not the chosen delivery dependency after the user's clarification. This audit does not alter that context or require the broad 27230 architecture in PR7600. Existing branch failures are conformance gaps, not permitted behavior.

## Handoff

Document-only validation checked 37 unique US rows, 15 unique ID rows, 14 unique TD rows, all 64 checklist ordinals across tickets 01–07, and 55 local link targets. The spec hash remains unchanged; the engine has no diff against current HEAD. These checks establish matrix coverage/link integrity, not requirement satisfaction or new runtime results.

This document completes only the requested preliminary mapping. Tickets and spec remain unchanged. No final acceptance percentage is reported: many rows have bounded historical support but all require final provenance, and two independent acceptance gates remain open. Resume with R0 when a concrete CBRD-27237 patch is available and the relevant review/integration/verification work is authorized.

[SPEC]: ../../.scratch/pr7600-effective-key-routing/spec.md
[ADR]: ../../docs/adr/0001-pr7600-effective-key-routing.md
