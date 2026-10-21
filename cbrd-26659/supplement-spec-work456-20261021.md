# CBRD-26659: OOS testcase supplementation specification

Status: ready-for-agent

Date: 2026-10-21, Asia/Seoul. Parent work item: 456.
Existing milestones: 457, 458, 459, 460, 461, 462.
The user confirmed shared understanding after Q1-Q6, then authorized this specification.
This document defines the revised supplementation scope. It does not report testcase execution or engine acceptance.

## Problem Statement

Existing OOS tests cover substantial SQL, shell, and C++ behavior, but their presence does not establish complete supplementation coverage.
The author needs a requirement-to-evidence inventory before adding tests or removing duplication.
The inventory must distinguish actual HAS_OOS records from records without HAS_OOS.
Schema eligibility, payload length, and table-level OOS statistics cannot establish an individual record's state.

Completed Work109 and Work401 provide useful prior evidence at their recorded revisions.
They do not establish current coverage for every supported operation, exact boundary, repeated storage workload, or large indexed OOS value.
Handover, SA-loaddb, and deferred-write results also belong to separate source revisions.
Combining those results without revalidation would conceal remaining failures or observation limits.

## Solution

Deliver one complete supplementation inventory and the missing tests across the six existing milestones.
Reuse sufficient existing tests before creating new cases.
Use ordinary SQL for observable statement behavior, native shell for lifecycle and physical observations, and C++ for contracts that those interfaces cannot establish.
Use existing seams before adding test helpers.

Classify applicable records by HAS_OOS set or clear, including relevant state transitions.
Remove small/large as a matrix axis. Keep size-dependent boundary tests where the contract requires them.
Verify large OOS PK/UNIQUE functionality. Performance qualification and HA remain deferred by explicit user direction.

Supplement completion requires every required test to be delivered and executed against an independent intended oracle.
Every result needs revision-specific evidence.
Reproducible engine defects may remain linked to separate fixes and recorded as failures.
Failed cases receive no passing-coverage credit.
Missing tests, unexecuted required cases, and unclear expected behavior prevent completion.

## User Stories

1. As an author, I want existing Work109 and Work401 evidence preserved, so that supplementation extends completed work without rewriting its historical claims.
2. As a reviewer, I want every supported OOS-relevant operation inventoried, so that familiar fixtures do not define the entire coverage population.
3. As a developer, I want actual record flags observed, so that table policies and large payloads cannot masquerade as HAS_OOS evidence.
4. As a developer, I want mixed-record heaps checked, so that one record's OOS state cannot be attributed to every row.
5. As a developer, I want stored records inspected before Expand, so that materialized copies cannot erase the state under test.
6. As a reviewer, I want applicable input and output states recorded, so that INSERT results and UPDATE transitions have explicit coverage.
7. As a reviewer, I want DELETE absence distinguished from a clear flag, so that a missing row cannot become a false control.
8. As a reviewer, I want logical results and physical evidence recorded separately, so that companion fixtures receive only their actual proof.
9. As a developer, I want valid storage-policy syntax tested, so that supported statements retain their intended behavior.
10. As a developer, I want malformed and conflicting policy clauses rejected, so that syntax errors have explicit regression coverage.
11. As a developer, I want policy eligibility checked by domain and context, so that semantic rejection differs from grammar rejection.
12. As a developer, I want failed schema changes to preserve data and metadata, so that rejection cannot conceal partial modification.
13. As a developer, I want policy defaults, omission, reset, and copying tested, so that schema transformations preserve accepted policy semantics.
14. As an operator, I want SHOW arguments, objects, and permissions checked, so that diagnostic behavior has positive and negative controls.
15. As an operator, I want utility roundtrips to preserve policies and values, so that readable output cannot conceal lost storage metadata.
16. As a developer, I want supported identifier and clause contexts inventoried, so that new policy tokens preserve accepted naming behavior.
17. As a user, I want heap and index reads to return complete values, so that either record state preserves query results.
18. As a user, I want copy and multirow writes to preserve their models, so that OOS state does not corrupt transferred values.
19. As a user, I want supported MERGE, REPLACE, and duplicate-key UPDATE paths checked, so that alternative writes receive explicit coverage.
20. As a user, I want applicable constraints and ordinary FK actions checked, so that record representation does not change relational integrity.
21. As a user, I want applicable set operations checked, so that full OOS values retain their comparison semantics.
22. As a user, I want commit, rollback, and savepoints checked, so that failures preserve the intended transaction state.
23. As a user, I want schema rewrites checked, so that column changes preserve surviving values and accepted policies.
24. As a developer, I want partition destinations checked physically, so that correct values do not conceal ownership in the wrong heap.
25. As a user, I want LOB locators and payloads distinguished, so that OOS checks do not overclaim external LOB lifecycle coverage.
26. As a maintainer, I want the complete C++ inventory mapped, so that existing internal contracts remain visible during supplementation.
27. As a maintainer, I want batching and Expand-avoidance assertions retained, so that equal SQL answers cannot erase useful internal proof.
28. As a maintainer, I want bounds and fault-handling tests retained, so that ordinary valid SQL does not replace unreachable error controls.
29. As a maintainer, I want identity and reclamation contracts distinguished, so that a matching chain identity cannot imply safe deletion.
30. As a maintainer, I want every proposed deletion mapped to a verified replacement, so that SQL deduplication preserves the original contract.
31. As a maintainer, I want distinct SA and CS behavior preserved, so that different cleanup and ownership contracts remain tested.
32. As a reviewer, I want registered and executed C++ cases reconciled, so that declaration counts cannot become passing-test evidence.
33. As a developer, I want every introduced limit and unit inventoried, so that boundary coverage has a complete obligation list.
34. As a developer, I want exact or next-representable boundary neighbors tested, so that alignment cannot invalidate a limit-plus-one claim.
35. As a developer, I want the accepted physical demotion target tested, so that implementation differences remain visible failures.
36. As a developer, I want profitability and chunk boundaries checked, so that value length and serialized length remain distinct.
37. As a developer, I want offset-width and residual-record boundaries checked, so that multiple stubs cannot bypass layout limits.
38. As a user, I want oversized rejected writes to preserve prior state, so that errors do not leave partial rows or orphan chains.
39. As a developer, I want key-overflow transitions distinguished from rejection, so that B-tree representation changes retain the correct oracle.
40. As a reviewer, I want impractical-limit guard tests labeled precisely, so that they cannot claim full-size storage execution.
41. As an operator, I want repeated INSERT/DELETE workloads tested, so that storage use can be compared at equal live data.
42. As an operator, I want repeated INSERT/UPDATE/DELETE workloads tested, so that replacement and deletion expose avoidable growth.
43. As a user, I want exact survivors checked through churn, so that space recovery cannot conceal lost or substituted data.
44. As a user, I want old readers and abort paths protected, so that reclamation follows transaction visibility and recovery safety.
45. As an operator, I want chunk deletion and page return measured separately, so that drained chunks cannot falsely prove reclaimed pages.
46. As an operator, I want safe reclaim before unnecessary sector growth checked, so that missed hints cannot justify permanent growth.
47. As an operator, I want fragmentation trends compared with equivalent fresh heaps, so that aggregate slack has a meaningful reference.
48. As a developer, I want restart and lost-hint scenarios checked where applicable, so that reclaim obligations survive process state loss.
49. As a reviewer, I want required churn exercised independently of earlier failures, so that an unexecuted workload cannot count as completed.
50. As a user, I want the indexed attribute itself verified as OOS-backed, so that adjacent payloads cannot substitute for large-key coverage.
51. As a user, I want PK/UNIQUE creation before and after population checked, so that both maintenance and build paths work.
52. As a user, I want applicable large-key reads and writes checked, so that full key values survive lookup, ordering, replacement, and deletion.
53. As a user, I want duplicate, NULL, and rollback behavior checked, so that large keys preserve supported constraint semantics.
54. As a reviewer, I want supported key combinations and rejected combinations distinguished, so that unsupported domains do not receive false credit.
55. As a reviewer, I want exact engine, installation, and testcase identities recorded, so that separate branch results cannot become combined acceptance.
56. As a reviewer, I want intended results derived independently, so that observed defects cannot become new golden answers.
57. As a reviewer, I want verdict mechanisms checked with disposable wrong expectations, so that successful process exit cannot conceal missing assertions.
58. As an author, I want required cases and artifacts reconciled, so that selected skips and missing execution remain explicit delivery gaps.
59. As an author, I want engine failures linked to their repairs, so that test delivery and passing coverage remain separate claims.
60. As an author, I want performance and HA deferrals explicit, so that functional completion cannot imply either deferred qualification.

## Implementation Decisions

- Reuse Work456 and milestones 457-462. Preserve completed Work109 and Work401. Keep wider integration and readiness in their existing work.
- Build the inventory first. For each operation, record support, intended behavior, applicable record states, existing assertions, evidence, and remaining obligations.
- HAS_OOS classification belongs to individual stored records. Record relevant states before and after an operation. Explain genuinely inapplicable cells.
- Prefer user-level SQL for statement contracts. Use native shell when sessions, utilities, physical ownership, recovery, or cleanup require orchestration.
- Reuse direct stored-record C++ observations for internal contracts or observations that product interfaces cannot establish safely.
- Treat diagnostic physical-slot scans as observations with identity and visibility limits. Validate their relationship to the intended logical row before crediting coverage.
- Cover accepted storage policies, including persistence and nonretroactive ALTER behavior. Use accepted issue decisions where the canonical context omits an established contract.
- Give each C++ case a retain, add, migrate, or remove disposition. A removal needs a verified equivalent replacement for its actual assertions and required execution behavior.
- Preserve internal-only assertions and distinct SA lifecycle behavior. Matching SQL text or matching value output alone does not establish redundancy.
- Enumerate limits before adding cases. Separate byte length, serialized length, record capacity, chunk capacity, offset width, and B-tree representation transitions.
- For impractical resource maxima, record guard-test coverage and its limits. Do not claim that a crafted descriptor stored a full-size value.
- Derive error expectations from accepted error identity and the inspected revision. Preserve atomicity, previous values, metadata, and ownership after rejection.
- Preserve the accepted SA prepared-row contract. Values, meaningful headers and CHN, ownership, policies, transactions, and buffer lifetime matter. Unused padding identity is superseded.
- Existing handover and SA fixes remain revision-specific dependencies. Revalidate affected contracts after actual integration. A pass on another branch does not update this baseline.
- Split storage scenarios so one known failure does not silently prevent required workloads. Recreate safe fixtures instead of continuing with invalid assumptions.
- Define reclamation observations around transaction completion, reader release, and acknowledged vacuum progress. A fixed sleep alone does not prove eventual return.
- Compare storage states at equivalent live data. Attribute OOS pages, chunk bytes, heap storage, index storage, and volume observations separately.
- Use a fresh equivalent heap as the packing reference. Aggregate unused bytes are a slack indicator, not an exact per-page fragmentation measurement.
- Verify the indexed value's OOS representation for PK/UNIQUE functionality. Do not substitute an unindexed OOS payload or an index-overflow file.
- Preserve the existing initial Linux, 16 KiB, optdebug functional profile. Add another mode only for a concrete contract or execution-path reason.
- Keep SQL and shell timing separate as operational cost information. Existing informal timing guides do not create a hard cutoff or a performance verdict.
- Use attempt-owned databases, registries, configurations, files, and processes. Cleanup must preserve unrelated resources and original worktree changes.
- Keep bulky execution artifacts outside tracked documentation. Retain concise results, exact identities, independent oracles, and links needed to substantiate the conclusions.
- Apply existing Git, source/TC publication, review, and CI rules during implementation. This specification grants no additional merge, closure, or deployment authority.

## Testing Decisions

A useful test checks an independently defined user or module contract.
It uses distinguishable values and verifies complete relevant values, state, errors, or ownership.
Lengths, counts, exit status, and table-level diagnostics provide supporting evidence. They cannot replace the intended contract.

### Existing verification seams

| Contract | Preferred existing seam | Required evidence |
| --- | --- | --- |
| SQL syntax, semantic rejection, DML, queries, schema, constraints | Normal SQL interface and native SQL runner | Exact expected values or errors, preserved state, selected-case verdicts |
| Record HAS_OOS classification | Validated product record diagnostics or existing stored-record C++ integration seam | Individual logical identity, stored-form flag, record type, transaction/visibility context |
| Sessions, physical ownership, utilities, recovery, storage lifecycle | Contained native shell with product diagnostics | Acknowledged schedule, exact values, owned physical state, artifacts, cleanup |
| Parsing bounds, identities, dispatch, fault controls, internal reclaim contracts | Existing OOS C++ unit/integration targets | Specific module assertions, expected/actual case identities, native test artifacts |

These seams retain the SQL/shell/C++ split confirmed during the interview.
No new production observation API is assumed.
Record diagnostics are candidate observers until a focused runtime check proves their intended use.

### Milestone acceptance

| Existing work item | Completion condition |
| --- | --- |
| 458 | Enumerate supported OOS-relevant operation families. Account for all applicable HAS_OOS and clear-flag cells, relevant transitions, exact existing tests, intended oracles, receipts, and gaps. Include mixed-record controls and explicit inapplicability reasons. |
| 457 | Close the inventoried syntax, semantics, SHOW, and utility-policy obligations with executed positive/negative cases. Distinguish rejection stages and verify preserved schema/data on failure. |
| 459 | Account for all relevant C++ tests. Execute required retained/new tests. Remove duplication only with verified replacement assertions, while preserving internal and execution-mode contracts. |
| 460 | Account for introduced limits and units. Execute accepted at-limit/over-limit methods, expected errors or transitions, and atomicity checks. State guard-only and alignment limits explicitly. |
| 461 | Execute required repeated-write, reclaim, reuse, restart, and adversarial scenarios with exact survivor models. Compare physical observations at equal live data and against fresh equivalents. Keep observed engine failures and unexecuted dependent phases distinct. |
| 462 | Execute supported large OOS PK/UNIQUE build and maintenance paths, relevant queries, duplicate/NULL rules, and failure/rollback checks. Prove that the indexed attribute is OOS-backed. Issue no performance qualification claim. |

### Common verification rules

- Reconcile every required case against the executed selection and verdict-bearing artifacts. Missing or skipped required execution is not a pass.
- Preserve separate PASS, FAIL, unsupported, and inapplicable dispositions. A support claim needs evidence at the recorded revision.
- A capability or specification gap that prevents a required test still blocks supplement completion unless the user explicitly changes the scope.
- Record reproducible engine defects as failures with exact scenarios and repair links. Preserve intended oracles rather than copying actual defective output.
- Check important verdict mechanisms with disposable negative controls. Keep those controls outside committed expected answers.
- Verify complete values and survivor ownership through destructive phases. Empty output, matching counts, or a zero process status cannot establish success alone.
- Require relevant physical proof for OOS claims. A companion fixture proves its own execution, not the actual SQL invocation elsewhere.
- Check new and retained internal boundaries through module contracts. Avoid tests that only reproduce implementation control flow.
- Preserve the current expected target, rollback/vacuum, page-return, partition-owner, and SA physical regressions until fresh evidence changes their outcomes.
- Keep correct failure oracles active when implementation differs from accepted requirements. Do not hide known failures inside a passing selection.
- Keep heap-record OOS storage separate from B-tree key overflow and external LOB storage. Attribute each claim to the observed subsystem.
- Before final qualification, freeze source, installation, dependency, runner, configuration, testcase, and expected-case identities.
- Run SQL, shell, and configured C++ selections through their maintained native workflows. Reconcile their artifacts separately.
- Apply the existing single-CI-cycle rule after authorized implementation publication. Report the run result and merge gates, then stop for human direction.

Prior art includes the existing policy DDL, read/write, schema, utility, bigone, chunk-neighbor, JDBC, crash, and snapshot fixtures.
The existing C++ inventory contributes stored-record, dispatch, bounds, identity, allocation, and reclaim contracts.
Historical receipts are reusable evidence only within their recorded scope and revision. Static testcase counts are not passing receipts.

## Out of Scope

- Small/large RECDES as a matrix classification axis. Size-dependent boundary tests remain included.
- Performance benchmarks, non-OOS baseline selection, throughput or latency qualification, and regression thresholds. The user deferred these explicitly.
- HA topology, transport, replication, failover, and replicated PK/FK scenarios under Work463. Ordinary single-node FK behavior remains applicable to the operation inventory.
- Production OOS feature repairs, competing source integrations, and new production observation APIs. Existing defects retain separate repair work.
- Perfect packing, across-page compaction, or operating-system volume-file shrink as invented storage requirements.
- Reopening deferred CDC/flashback history or changing its visible regressions to obtain passing results.
- A full release/platform matrix, whole-company-corpus qualification, or an implicit legacy-runner fallback.
- Testcase implementation, builds, test execution, source publication, CI triggers, JIRA publication, or remote issue creation in this specification phase.
- Agent merge/closure of TC PRs, deployment, or changes to existing authorization boundaries.

## Further Notes

The user confirmed Q1-Q6 and the final shared-understanding summary on 2026-10-21.
The original intake remains unchanged. The later decisions govern this supplement.
The local tracker uses one effort directory with a specification and, after the separate ticket-planning step, one file per implementation ticket.
This selected specification has an identical local-tracker mirror. Existing work-tracker IDs remain the durable progress references.

The [current inventory and accepted decisions](supplement-inventory-work456-20261021.md) record exact source/TC heads, observation routes, prior receipts, and known limitations.
The inspected handover source is `1ef86a7efa34002e971b1b30bcf5d451e9db441b`.
Public TC is `df8596dd999e825b1ec9812a735bbe01e50ac715`, and private TC is `5c9d8de1a916ae0acbddc8409770b51fd31da13b`.
SA and deferred-write branches remain separate in that inventory. Recheck live identities before implementation.
The static inventory found a broken compile-database link and unset build preset. Execution readiness must be established through the maintained build workflow.

Required behavior follows the complete normative OOS specification, last updated 2026-10-08.
Its read fingerprint is `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`.
Accepted policy decisions in [CBRD-26067](https://jira.cubrid.org/browse/CBRD-26067) and [CBRD-26979](https://jira.cubrid.org/browse/CBRD-26979) supplement the documented policy contract.
Use the current 24-byte stub and symbolic profitability rule rather than obsolete literal sizes.

Supporting evidence:

- [Earlier developer-owned specification, Work109](ci-replan/spec.md)
- [Existing behavior coverage and dispositions](ci-replan/coverage.md)
- [Existing unit inventory](ci-replan/spec-and-unit-inventory.md)
- [Completed Work401 additions and remaining proof](coverage-additions-work401-20261016.md)
- [Accepted SA prepared-row decision](../cbrd-27424/sa-inline-preservation-decision-20261017.md)
- [Recovered SA CI evidence](../cbrd-27424/ci_analysis_report_6a487cdb6_collector_recovery_codex.md)
- [Repository vocabulary](../CONTEXT.md)

No parent JIRA issue or remote testcase PR is modified by publishing this specification to the local tracker.
