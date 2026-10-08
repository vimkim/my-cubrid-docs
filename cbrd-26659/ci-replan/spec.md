# CBRD-26659: developer-owned OOS regression specification

Date: 2026-10-08 (Asia/Seoul). Status: ready-for-agent specification; implementation is not authorized by this planning phase. Parent: CBRD-26659. Work tracker: 109. The agreed direction includes local optdebug validation, separate informal SQL/shell runtime guidance, a passing delivered set, and explicit ordinary-HA follow-up coverage.

## Problem Statement

Developers now create and validate both public SQL and private shell regression cases. CBRD-26659's previous description and adversarial campaign reflect older responsibilities, storage layouts and acceptance rules. Existing logical answers, closed issues and registered unit tests do not establish that a delivered testcase exercises current OOS behavior or passes through the actual regression runner.

Developers need a small useful delivery that preserves intended values and lifetime behavior, follows both testcase repositories' conventions, and gives reviewers honest evidence of coverage, defects, cleanup and execution cost. SQL and shell run separately. Roughly ten minutes for each is guidance for avoiding unnecessary cost, rather than a hard acceptance threshold.

## Solution

Use the researched behavior coverage inventory to reuse or strengthen existing cases and add missing observable behavior. Deliver deterministic single-session checks through public SQL; use private shell for physical diagnostics, lifecycle, utilities, configuration and coordinated sessions. Validate both selected sets locally with the existing native focused runner, initially using optdebug.

Start with one SQL value-copy case and one shell owner-file creation/DROP case, each completing discovery, reviewed expectations, execution, verdict evidence and cleanup. Subsequent slices deliver complete behavior groups. The final slice runs the complete selected SQL set and shell set separately and reports actual timings and explicit coverage dispositions.

Correct failing reproducers, accepted implementation gaps and unreachable internal behavior remain visible without verified-coverage credit. Ordinary HA replication is an agreed follow-up gap because its local topology and transport are not prepared. This specification does not turn the selected passing set into a claim that all OOS requirements or the full company corpus pass.

## User Stories

1. As a developer, I want one behavior inventory linked to accepted requirements and live issues, so that I can distinguish obligations from historical proposals.
2. As a developer, I want current implementation differences recorded separately from issue status, so that closed tickets do not conceal missing behavior.
3. As a developer, I want existing C++ tests and their internal seams accounted for, so that external coverage does not duplicate or overclaim unit evidence.
4. As a developer, I want to reuse existing SQL and shell cases where their assumptions remain valid, so that the delivery stays small and maintainable.
5. As a developer, I want one SQL case to pass end to end first, so that I can trust discovery, JDBC execution and expected-answer comparison.
6. As a developer, I want one shell case to pass end to end first, so that I can trust physical observation, verdict handling and resource cleanup.
7. As a developer, I want distinguishable values across single and multiple chunks, so that reordering, truncation or cross-row substitution cannot hide behind equal lengths.
8. As a developer, I want profitable-floor, NULL, empty and many-attribute checks, so that representation boundaries preserve intended values and placement.
9. As a developer, I want storage priorities and policy DDL checked independently, so that correct logical output does not conceal incorrect demotion order.
10. As a developer, I want INSERT, copy, UPDATE, DELETE and inline/OOS transitions covered, so that every supported write path preserves the intended row model.
11. As a developer, I want commit, rollback, savepoint and rejected DML to preserve the intended pre-image or post-image, so that partial changes cannot pass.
12. As a developer, I want constraints and triggers checked with truthful path qualifications, so that client-template bypass is not mistaken for OOS insertion.
13. As a developer, I want heap/index projections, relational reads and raw consumers checked, so that each claimed read path returns the full logical values.
14. As a developer, I want schema and supported partition transformations checked, so that rewrites preserve data and destination ownership is separately observable.
15. As a developer, I want external LOB locators and copied content checked after source destruction, so that locator demotion and copy independence are actually tested.
16. As a developer, I want acknowledged committed data to survive a real crash, so that graceful restart is not substituted for crash durability.
17. As a developer, I want uncommitted writes undone after a crash, so that recovered rows match the independently journaled transaction model.
18. As a developer, I want real sessions to retain intended old snapshots while writers proceed, so that internal simulated snapshots are supplemented by external evidence.
19. As a developer, I want observable reclaim and survivor safety checked with eligibility and quiescence, so that a racing zero statistic cannot certify successful cleanup.
20. As a developer, I want owned OOS files positively identified before DROP, so that empty diagnostic output cannot falsely prove file removal.
21. As a developer, I want utility and backup round trips to preserve exact values, so that row counts and successful process startup are not the only assertions.
22. As a developer, I want OOS-specific TDE/WAL attribution and correct recovered values, so that heap-only traces do not receive OOS encryption credit.
23. As a reviewer, I want expected results derived before actual output is accepted, so that current defects are not copied into golden answers.
24. As a reviewer, I want logical SQL and physical shell evidence credited separately, so that a matching companion fixture is not described as observation of the actual SQL run.
25. As a reviewer, I want exact executed identities, passing artifacts and cleanup evidence, so that exit zero or a skipped branch cannot establish coverage.
26. As a CI integrator, I want separate local whole-suite timings with the actual configuration recorded, so that I can assess cost without an assumed company-CI speedup.
27. As a reviewer, I want HA, CDC, engine defects and internal-only gaps explicit, so that the delivered passing set remains useful without concealing unsupported claims.

## Implementation Decisions

- Deliver cases in the public SQL and private shell repositories. Existing C++ tests are researched prior art; no new C++ testcase family or engine implementation is included.
- Use the agreed OOS domain vocabulary and behavior inventory. Group overlapping issues into behavior assertions instead of producing one testcase per issue. Prefer reuse or strengthening before new cases.
- Choose checkouts using the current Git policy: create/reuse a sibling topic worktree when starting on main, develop or a feature branch; continue directly when already on another named task branch. Record the documented/agreed integration destination and recheck PR association before choosing any PR-specific testcase branch. The existing coordinating source task branch is used directly; preserve its unrelated submodule changes. Recheck testcase integration snapshots and instructions when implementation starts.
- Prepare a dedicated source-matching optdebug execution environment, matching JDBC and explicitly selected testcase roots. The current Debug installation is not the agreed validation configuration. Record source, dependencies, install, runner and testcase identities.
- Use existing product seams: SQL through the normal configured interface, server and utilities through private shell, and product diagnostics for physical observation. No new engine instrumentation or unit hooks are assumed.
- The initial public profile is optdebug with the company-compatible JDBC/16 KiB configuration. Shell records its page size, SA/CS mode and parameters for each behavior. Extra release or page-size modes need a concrete behavior reason; no automatic matrix or timing gate is imposed.
- Use distinguishable, noncompressed VARBIT patterns for physical-size baselines. Type/compression interaction gets separate fixtures. Derive serialized sizes and chunk expectations using the accepted layout, including the current 24-byte stub/header; logical length is not serialized record size.
- Preserve separate logical and physical evidence. Current public SQL golden comparison has no identified portable stable-field HEAP OOS assertion. A delivered shell companion proves its own paired fixture/configuration, with any interface differences explicit; it does not observe the actual public SQL invocation.
- Use positive owned-file/chunk evidence before destructive phases. Normalize volatile identifiers only where the intended invariant remains observable. Reject parse errors and empty expected fields.
- Treat crash durability, uncommitted recovery, snapshot visibility, rollback-after-vacuum and reclaim as distinct assertions. A shared fixture is acceptable only while phases remain independently named and asserted; failures stop dependent phases.
- Use attempt-owned installations, registries, configuration, files, logs and containment. Shell session barriers require acknowledgements and bounded completion predicates. Cleanup restores case-owned parameters and removes or terminates only owned resources.
- Preserve known engine defects with correct intended expectations. The physical target mismatch, abort/vacuum loss risk, missing commit notification/reuse, partition destination ownership and SA/workspace demotion each retain separate dispositions. Passing logical subsets do not close missing physical or lifetime contracts.
- Keep existing deferred CDC regressions enabled and visibly dispositioned under the accepted history ADR. This delivery must not alter their expectations or disable them to make the selected set green.
- Ordinary HA replication remains an explicit follow-up requirement. A future slice must first establish a contained local two-node topology and compatible transport, then prove independent replica values, OOS paths, verdicts, cleanup and timing. No HA exclusion is justified by an unmeasured time estimate.
- Build, download, copied-attempt preparation and verification overhead are recorded separately from runner elapsed time. Runner elapsed includes its own setup, fixture execution and normal cleanup. SQL and shell are never combined into a 600-second acceptance gate.

## Testing Decisions

- A good testcase checks intended external behavior with an independently reviewed row/transaction/schema model, plus relevant OOS evidence. Full-value equality and independently computed hashes catch tail corruption and substitution; lengths and counts are supporting checks.
- Start from the recovered INSERT SELECT case and the current positive owner-descriptor DROP mechanism. Reuse the historical durability case's value-checking approach while replacing obsolete physical sizes, weak readiness waits and overly broad process ownership.
- Representation, DML, transaction, read, schema/policy and LOB groups reuse the nine recovered pairs and current repository examples. Physically discriminating companion phases belong in shell where SQL golden output cannot express them portably.
- Recovery, snapshots, utilities and TDE borrow current repository lifecycle and diagnostic mechanisms. Generic core-only verdicts, fixed sleeps, warning-only checkdb failures, equality of two empty strings and count-only restores are insufficient.
- First prove that the runner actually discovers and executes the intended case, reports the right verdict, and detects a deliberate wrong expectation in a disposable validation attempt. Restore the reviewed real expectation and obtain the clean passing receipt; do not mutate tracked answers from observed output.
- Every later slice includes repository-conforming cases, reviewed expectations, exact executed identities, positive assertions, appropriate physical evidence, passing artifact verdicts, cleanup evidence and measured local time. Required skipped assertions are not passes.
- SHOW's conditional-latch scan can undercount busy pages. Exact physical claims need a controlled quiescent fixture and survivor checks. Chain identity, retry, allocation faults and internal cursor invariants stay explicit gaps without a reachable production control and discriminating oracle.
- TDE algorithm metadata and recovery-index classifications do not establish ciphertext or absence of plaintext leakage. Report the actual verified subset; retain the ciphertext-inspection gap if no product-level observation establishes it.
- Final validation freezes the complete delivered SQL and shell case lists and reconciles each against coverage. Execute both sets separately with the recorded native contained workflow, verifying exact positive counts, result artifacts and zero selected failures/skips. A focused local pass does not establish whole-corpus native/CTP equivalence or a company GHA pass.
- Record each suite's whole-run elapsed time and per-case timing where available. About ten minutes each is a guide for reviewing cost. If a useful group is expensive, record its actual cause and coverage benefit, optimize waste, and present any material coverage tradeoff rather than silently dropping it.

## Out of Scope

- Testcase implementation, builds, test execution, JIRA publication, external ticket creation, pushes and GHA runs during this planning/specification phase.
- Engine fixes, new product APIs, new C++ testcases and a continuation of the old adversarial campaign framework.
- Ordinary HA topology preparation, transport/failover/stress testing in this delivery; the follow-up gap is explicit.
- The deferred CDC/flashback OOS-history feature, future compression/cache/PEEK/INTERNAL-LOB redesigns and other unaccepted proposals.
- Guaranteed internal fault/retry/cursor coverage through ordinary SQL/shell without established controls.
- A hard ten-minute cutoff, combined SQL-plus-shell budget, eight-minute design target, mandatory company-worker resource replica or presumed CI speedup.
- Whole-company-corpus qualification or an implicit legacy CTP fallback. A separate local CTP comparison requires an explicit request.

## Further Notes

The evidence basis is the [agreed plan](plan.md), [single behavior table](coverage.md), [live issue inventory](issue-inventory.md), [accepted contract and current units](spec-and-unit-inventory.md), [public assets](public-sql-inventory.md), [private assets](private-shell-inventory.md), [local validation procedure](local-validation.md), [company compatibility context](ci-environment.md), [glossary](GLOSSARY.md) and [accepted direction](docs/adr/0001-developer-owned-ci-regressions.md).

Research is pinned to engine `fb567a629cdb390fff920542173fa36f454c74a0`; current runtimes and current testcase pass receipts are absent. Implementation must recheck those identities rather than silently substitute an updated engine. A recorded changed baseline is acceptable with coverage/expectation reconciliation.

The maintained local tracker stores a spec and one file per implementation ticket. This durable specification is mirrored there. The user approved the 14-ticket granularity/dependency breakdown on 2026-10-08. [Approved ticket definitions](implementation-tickets.md) are retained durably and mirrored into local issues with the configured ready-for-agent state. Execution follows genuine blocking edges; only the first SQL and shell tickets have no blockers. No parent JIRA issue is modified and no implementation is authorized by this planning phase.
