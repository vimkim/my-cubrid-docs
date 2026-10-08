# CBRD-26659 documentation

Last modified: 2026-10-08 (Asia/Seoul).

Start with the current proposed plan and behavior coverage table. Developers now create and validate public SQL and private shell cases locally, initially using optdebug. SQL and shell timing is separate; roughly ten minutes each is informal guidance. The direction and HA follow-up gap are agreed; the 14-ticket granularity/dependency breakdown is approved. No testcase implementation or external publication belongs to this planning phase.

The coordinating engine branch has no associated PR at source `fb567a629cdb390fff920542173fa36f454c74a0`. Research inspected testcase integration snapshots named `tc/pr-7990` (and private `tc/pr-7925`); those supply integration context. They are not a PR for this planning branch.

The `campaign/` documents are historical evidence. They describe older engine/runner/layout decisions and cannot establish current passing coverage. Their supporting artifacts remain linked from the relevant report; no historical cleanup is included here.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [plan.md](ci-replan/plan.md) | Agreed direction, sequence and approved-ticket boundary | 2026-10-08 | 2026-10-08 | Review the developer-owned local regression plan |
| [spec.md](ci-replan/spec.md) | Agreed external behavior, decisions and validation contract | 2026-10-08 | 2026-10-08 | Turn the settled plan into an implementation specification |
| [implementation-tickets.md](ci-replan/implementation-tickets.md) | Approved 14-ticket breakdown and genuine blocking edges | 2026-10-08 | 2026-10-08 | Sequence independently verifiable testcase delivery |
| [coverage.md](ci-replan/coverage.md) | 31 evidence-linked behavior and disposition rows | 2026-10-08 | 2026-10-08 | Connect expected behavior to SQL/shell actions and gaps |
| [issue-inventory.md](ci-replan/issue-inventory.md) | Live hierarchy, linked defects and curated 150-issue ledger | 2026-10-08 | 2026-10-08 | Replace stale issue assumptions with bounded live evidence |
| [spec-and-unit-inventory.md](ci-replan/spec-and-unit-inventory.md) | Accepted contract, exact source and all 29 binaries / 302 tests | 2026-10-08 | 2026-10-08 | Identify conformance and external observability gaps |
| [public-sql-inventory.md](ci-replan/public-sql-inventory.md) | Nine recovered pairs, integration differences and reuse limits | 2026-10-08 | 2026-10-08 | Select useful SQL assets without inheriting historical passes |
| [private-shell-inventory.md](ci-replan/private-shell-inventory.md) | OOS shell assets, lifecycle mechanisms and oracle limitations | 2026-10-08 | 2026-10-08 | Design compact shell coverage using current conventions |
| [local-validation.md](ci-replan/local-validation.md) | Local environment, prerequisites and future verdict/timing procedure | 2026-10-08 | 2026-10-08 | Make later local validation reproducible and reviewable |
| [ci-environment.md](ci-replan/ci-environment.md) | Company runner configuration and compatibility context | 2026-10-08 | 2026-10-08 | Check future integration conventions without a GHA gate |
| [GLOSSARY.md](ci-replan/GLOSSARY.md) | Terms for delivery, configurations and verified coverage | 2026-10-08 | 2026-10-08 | Separate this delivery from historical campaign terminology |
| [0001-developer-owned-ci-regressions.md](ci-replan/docs/adr/0001-developer-owned-ci-regressions.md) | Accepted developer ownership and local separate timing guidance | 2026-10-08 | 2026-10-08 | Record the settled direction and superseded budget assumptions |
| [CBRD-26659-engine-baseline_f4299ac_claude.md](campaign/CBRD-26659-engine-baseline_f4299ac_claude.md) | Historical engine pin and boundary derivation | 2026-09-10 | 2026-09-14 | Establish the old campaign source and layout |
| [CBRD-26659-injection-site-validation_f4299ac_claude.md](campaign/CBRD-26659-injection-site-validation_f4299ac_claude.md) | Historical instrumented fault-site analysis | 2026-09-12 | 2026-09-14 | Validate old campaign injection reachability |
| [CBRD-26659-manifest-matrix-replay-tooling_f4299ac_claude.md](campaign/CBRD-26659-manifest-matrix-replay-tooling_f4299ac_claude.md) | Historical manifest/replay mechanisms and limitations | 2026-09-11 | 2026-09-21 | Record old campaign evidence tooling |
| [CBRD-26659-private-tracer-bullet_f4299ac_claude.md](campaign/CBRD-26659-private-tracer-bullet_f4299ac_claude.md) | Historical first shell case and verdict evidence | 2026-09-11 | 2026-09-14 | Prove the old private runner path |
| [CBRD-26659-public-tracer-bullet_f4299ac_claude.md](campaign/CBRD-26659-public-tracer-bullet_f4299ac_claude.md) | Historical first SQL case and verdict evidence | 2026-09-10 | 2026-09-14 | Prove the old public runner path |
| [CBRD-26659-repin-without-unit-test-seams_f4299ac_claude.md](campaign/CBRD-26659-repin-without-unit-test-seams_f4299ac_claude.md) | Historical production-build repin and seam differences | 2026-09-14 | 2026-09-14 | Distinguish instrumentation from product evidence |
| [CBRD-26659-representative-timings-tier-placement_f4299ac_claude.md](campaign/CBRD-26659-representative-timings-tier-placement_f4299ac_claude.md) | Historical measured costs and unmeasured projections | 2026-09-18 | 2026-09-21 | Identify old campaign runtime costs |
| [CBRD-26659-requirement-catalogue_f4299ac_claude.md](campaign/CBRD-26659-requirement-catalogue_f4299ac_claude.md) | Historical requirement catalog and scope | 2026-09-10 | 2026-09-10 | Map the old campaign requirements |
| [CBRD-26659-sql-operations_f4299ac_claude.md](campaign/CBRD-26659-sql-operations_f4299ac_claude.md) | Historical SQL case/oracle and operation evidence | 2026-09-15 | 2026-09-21 | Explain the old public DML delivery |
| [CBRD-26659-ticket13-independent-review_f4299ac_claude.md](campaign/CBRD-26659-ticket13-independent-review_f4299ac_claude.md) | Historical public tracer review | 2026-09-11 | 2026-09-11 | Review old SQL discovery and expectations |
| [CBRD-26659-ticket14-independent-review_f4299ac_claude.md](campaign/CBRD-26659-ticket14-independent-review_f4299ac_claude.md) | Historical private tracer review | 2026-09-11 | 2026-09-11 | Review old shell assertions and cleanup |
| [CBRD-26659-ticket17-independent-review_f4299ac_claude.md](campaign/CBRD-26659-ticket17-independent-review_f4299ac_claude.md) | Historical timing review | 2026-09-18 | 2026-09-18 | Separate measured runtime from extrapolation |
| [CBRD-26659-ticket19-independent-review_f4299ac_claude.md](campaign/CBRD-26659-ticket19-independent-review_f4299ac_claude.md) | Historical SQL operations review | 2026-09-15 | 2026-09-15 | Review old DML coverage and limits |
| [CBRD-26659-traceability-schemas_f4299ac_claude.md](campaign/CBRD-26659-traceability-schemas_f4299ac_claude.md) | Historical traceability and evidence schema rationale | 2026-09-10 | 2026-09-21 | Explain old evidence records |
| [oos-schema-change-report.md](oos-schema-change/oos-schema-change-report.md) | Historical schema-change scenario and limits | 2026-06-29 | 2026-06-29 | Investigate OOS schema transformations |
| [01-sql-value-copy.md](ci-replan/tickets/01-sql-value-copy.md) | Prove one SQL value-copy case end to end | 2026-10-08 | 2026-10-08 | Define an approved complete testcase-delivery slice |
| [02-shell-owner-drop.md](ci-replan/tickets/02-shell-owner-drop.md) | Prove one shell OOS owner-file lifecycle case end to end | 2026-10-08 | 2026-10-08 | Define an approved complete testcase-delivery slice |
| [03-representation-chunks.md](ci-replan/tickets/03-representation-chunks.md) | Validate representation and discriminating chunk boundaries | 2026-10-08 | 2026-10-08 | Define an approved complete testcase-delivery slice |
| [04-dml-transitions.md](ci-replan/tickets/04-dml-transitions.md) | Validate UPDATE and DELETE state transitions | 2026-10-08 | 2026-10-08 | Define an approved complete testcase-delivery slice |
| [05-transactions-errors.md](ci-replan/tickets/05-transactions-errors.md) | Validate transaction and rejected-DML atomicity | 2026-10-08 | 2026-10-08 | Define an approved complete testcase-delivery slice |
| [06-triggers.md](ci-replan/tickets/06-triggers.md) | Validate trigger outcomes with explicit OOS path limits | 2026-10-08 | 2026-10-08 | Define an approved complete testcase-delivery slice |
| [07-read-paths.md](ci-replan/tickets/07-read-paths.md) | Validate supported relational and raw read paths | 2026-10-08 | 2026-10-08 | Define an approved complete testcase-delivery slice |
| [08-schema-storage.md](ci-replan/tickets/08-schema-storage.md) | Validate schema and storage-policy rewrites | 2026-10-08 | 2026-10-08 | Define an approved complete testcase-delivery slice |
| [09-lob-locators.md](ci-replan/tickets/09-lob-locators.md) | Validate external LOB locator and copy independence | 2026-10-08 | 2026-10-08 | Define an approved complete testcase-delivery slice |
| [10-crash-recovery.md](ci-replan/tickets/10-crash-recovery.md) | Validate committed crash durability and uncommitted undo | 2026-10-08 | 2026-10-08 | Define an approved complete testcase-delivery slice |
| [11-snapshots-reclaim.md](ci-replan/tickets/11-snapshots-reclaim.md) | Validate real snapshot visibility and observable safe reclaim | 2026-10-08 | 2026-10-08 | Define an approved complete testcase-delivery slice |
| [12-utility-roundtrips.md](ci-replan/tickets/12-utility-roundtrips.md) | Validate utility and backup round trips | 2026-10-08 | 2026-10-08 | Define an approved complete testcase-delivery slice |
| [13-tde-wal.md](ci-replan/tickets/13-tde-wal.md) | Validate OOS TDE attribution and WAL behavior | 2026-10-08 | 2026-10-08 | Define an approved complete testcase-delivery slice |
| [14-complete-local-validation.md](ci-replan/tickets/14-complete-local-validation.md) | Validate the complete delivered SQL and shell sets locally | 2026-10-08 | 2026-10-08 | Define an approved complete testcase-delivery slice |
