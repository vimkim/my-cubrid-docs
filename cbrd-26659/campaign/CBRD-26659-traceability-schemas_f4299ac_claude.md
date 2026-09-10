# CBRD-26659 — Traceability record schemas: manifest, matrix, attempt record, replay bundle (ticket 12)

> Observed: 2026-09-10 (KST). Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`; normative context `f6543de` + sha256 `c9daf3c4…` (ticket 11).
> Author: Claude Fable 5.1, session `session_01Wq38qC19cw3fGeq1oCFqjJ`, for the [Adversarial OOS testcase campaign](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/spec.md) ticket 12.
> Machine-readable source of truth: [`schemas/*.schema.json`](schemas/) (JSON Schema 2020-12 subset), with one valid example per record under [`schemas/examples/valid/`](schemas/examples/valid/) and negative controls under [`schemas/examples/invalid/`](schemas/examples/invalid/). The field tables below are rendered from the schemas by [`tools/render_docs.py`](tools/render_docs.py); edit the schemas, not the tables.
> Companion: [requirement catalogue](CBRD-26659-requirement-catalogue_f4299ac_claude.md).

Vocabulary follows the [docs glossary](../../CONTEXT.md): Campaign manifest, Coverage matrix, Attempt record, Replay bundle, OOS-path evidence, Failure of proof, Accepted exclusion, Outcome, Delivery gap, Capability gap, Specification gap, Engine defect.

## 1. Records and how they relate

```text
requirement (catalogue) ──cited by──> case ──run under──> configuration ──in──> run (campaign manifest, one per invocation)
                                                                                    │
                                                                                    ├── per case: outcome + OOS-path evidence status + attempts
                                                                                    │
                                                              attempt record (compact, kept forever) ──points at──> replay bundle (bulky, retention-ruled)
                                                                                    │
coverage matrix (cross-invocation) ── one row per (requirement, case, configuration): run, OOS-path evidence, finding,
                                        flakiness, ticket link (known_issue), attribution; plus dated accepted exclusions written only by the user
```

- The **campaign manifest** is the per-invocation record and the unit of execution proof. Ticket 13 and 14 write one by hand; ticket 15's wrappers generate them.
- The **coverage matrix** is the cross-invocation aggregation keyed by Requirement ID. Tooling merges manifests into rows; a later pass never erases an earlier failure; accepted exclusions are hand-written by the user only.
- The **attempt record** is compact and kept indefinitely for every attempt (original, rerun, minimized, reproduction).
- The **replay bundle** index lists every specification item with a state of present, missing or not-applicable; a bundle with a missing item is never called complete.

## 2. Shared vocabulary used by every record

| Field vocabulary | Values | Rule |
|---|---|---|
| Outcome (per executed attempt) | `PASS`, `FAIL`, `SKIP`, `UNSUPPORTED`, `BLOCKED` | Fixed taxonomy from the reproduction decision. SKIP carries a reason. A skip recorded as OK, an unfired hook or an unreached phase never maps to PASS. A documented Engine defect still records FAIL. |
| OOS-path evidence status | `proven`, `reused`, `missing`, `not-applicable` | Separate from the outcome. `reused` requires applicability (fixture, execution path, engine configuration, conditions, source manifest). Logical success with `missing` evidence is not OOS coverage. |
| Gap kind (matrix finding) | `none`, `Delivery gap`, `Capability gap`, `Specification gap`, `Engine defect` | Glossary terms, used exactly. `none` only for PASS with proven or reused evidence. |
| Attribution target | `unknown`, `engine`, `harness`, `instrumentation`, `setup`, `specification` | Separate from the outcome. `engine` requires evidence; an unexplained failure stays `unknown`. |
| Proof verdict (manifest) | `proven`, `failure-of-proof` | Any mismatch between expected and discovered/executed cases or assertion counts is a failure of proof, never a pass. |
| Replay item state | `present`, `missing`, `not-applicable` | Missing evidence is recorded as missing with a note. |

Identities used everywhere: engine baseline commit plus library hashes (a build directory is not proof), testcase repository/branch/commit/base commit, context revision plus content hash, catalogue hash, page size (4096/8192/16384), build mode (release/debug), run mode (standalone/client-server), services with ownership, instrumentation identity (null for unmodified runs), seed and generator version (null for fixed workloads).

## 3. Rules the schemas enforce, and rules tooling must add

Enforced by schema (checked by the negative controls):

- Conditional rules (`if`/`then`) are not visible in the field tables of sections 4 to 8; this list is their reference.
- Outcome outside the taxonomy is rejected; SKIP without a reason is rejected; a case with no outcome must carry an `outstanding` reason.
- A manifest without the context content hash is rejected; storage roots outside `/home` are rejected.
- `reused` evidence without applicability is rejected.
- A matrix row without separate `flakiness`, `known_issue` and `attribution` fields is rejected; a `deterministic_claim` with fewer than three consecutive fresh-fixture reproductions is rejected; `engine` attribution without evidence is rejected.
- An accepted exclusion without a date, or with `accepted_by` other than `user`, is rejected.
- An attempt whose deadline was reached cannot record PASS; derived attempts (rerun, minimized, reproduction) must name their parent.
- A replay bundle that omits a specification item, uses an unknown item state, marks an item present without a path, or marks it missing without a note is rejected.

Tooling (ticket 15) must add what a schema cannot express:

- Merge by Requirement ID; append to `finding.history`; set `ever_failed` monotonically; never drop a row because a later invocation passed.
- Never write `accepted_exclusions`; preserve entries verbatim.
- Compare `expected` with `discovered` and `executed`; write every mismatch and set `proof.verdict` to `failure-of-proof`.
- Map runner results (SQL result-versus-answer, shell ok/nok/SKIP) onto the taxonomy; never map a skip, an unfired hook or an unreached phase to PASS.
- Apply retention classes (success bulky seven days; failure through triage plus thirty days; compact records and minimized reproducers kept) and stop admitting work at the storage limit instead of deleting unresolved evidence.
- Verify `complete` in a bundle equals "no item is missing".

## 4. Campaign manifest

<!-- BEGIN GENERATED: schema-manifest -->
**CBRD-26659 campaign manifest (one per invocation)** — The per-invocation record that turns a launcher exit code into execution proof. It names the invocation identity, the expected case identities and counts, what was discovered and executed, the proof verdict, and per case its outcome, OOS-coverage evidence status, attempt bundles and outstanding coverage. The coverage matrix aggregates manifests; a manifest never aggregates.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schema_version` | const `1` | yes |  |
| `manifest_id` | string `^[A-Za-z0-9._:-]+$` | yes | Unique invocation identity, cited by matrix rows and attempt records. |
| `producer` | object | yes | Who wrote the manifest: a person (ticket 13/14 hand-written records) or the ticket 15 wrapper. |
| `producer.kind` | enum: `hand-written`, `wrapper` | yes |  |
| `producer.name` | string | yes |  |
| `producer.version` | string/null | yes |  |
| `invocation` | object | yes | Invocation identity. Every field is recorded for every run; nothing is inherited from the environment. |
| `invocation.started_at` | string `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z\|[+-][0-9]{2}:[0-9]{2})$` | yes |  |
| `invocation.ended_at` | string `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z\|[+-][0-9]{2}:[0-9]{2})$` | yes |  |
| `invocation.tier` | enum: `fast`, `scheduled`, `extended` | yes | Execution tier from the budget decision. |
| `invocation.caps` | object | yes |  |
| `invocation.caps.invocation_seconds` | integer | yes |  |
| `invocation.caps.per_case_seconds` | integer | yes |  |
| `invocation.caps.invocation_cap_reached` | boolean | yes | True when the invocation cap ended the bounded attempt; unfinished work is then listed under outstanding_coverage. |
| `invocation.resources` | object | yes |  |
| `invocation.resources.cpus` | integer | yes |  |
| `invocation.resources.memory_gib` | number | yes |  |
| `invocation.resources.storage_gib` | number | yes |  |
| `invocation.resources.storage_root` | string `^/home/` | yes | Fixtures, logs and cores live under /home. |
| `invocation.engine` | object | yes | Pinned engine identity proven by binary, not by build directory. |
| `invocation.engine.baseline_commit` | string `^[0-9a-f]{40}$` | yes |  |
| `invocation.engine.worktree` | string | yes |  |
| `invocation.engine.modified` | boolean | yes | False for the unmodified pinned worktree; true for the instrumentation worktree (then instrumentation is not null). |
| `invocation.engine.install_prefix` | string | yes |  |
| `invocation.engine.version_string` | string | yes | cubrid_rel output with CUBRID, PATH and LD_LIBRARY_PATH pointed at the install under test. |
| `invocation.engine.library_hashes` | object | yes |  |
| `invocation.engine.library_hashes.libcubrid.so` | string `^sha256:[0-9a-f]{64}$` | yes |  |
| `invocation.engine.library_hashes.libcubridsa.so` | string `^sha256:[0-9a-f]{64}$` | yes |  |
| `invocation.testcase` | object | yes |  |
| `invocation.testcase.repository` | enum: `testcases`, `testcases-private-ex` | yes |  |
| `invocation.testcase.branch` | string | yes |  |
| `invocation.testcase.commit` | string `^[0-9a-f]{40}$` | yes |  |
| `invocation.testcase.base_commit` | string `^[0-9a-f]{40}$` | yes | The verified origin/develop tip the campaign branch was based on. |
| `invocation.testcase.worktree` | string | yes |  |
| `invocation.context` | object | yes | Normative specification identity: committed revision plus content hash of the working copy the requirement IDs cite. |
| `invocation.context.revision` | string `^[0-9a-f]{40}$` | yes |  |
| `invocation.context.content_hash` | string `^sha256:[0-9a-f]{64}$` | yes |  |
| `invocation.context.snapshot` | string | yes |  |
| `invocation.catalogue` | object | yes | The requirement catalogue revision whose IDs this manifest cites. |
| `invocation.catalogue.path` | string | yes |  |
| `invocation.catalogue.hash` | string `^sha256:[0-9a-f]{64}$` | yes |  |
| `invocation.page_size` | enum: `4096`, `8192`, `16384` | yes | createdb --db-page-size of every database the invocation created. |
| `invocation.build_mode` | enum: `release`, `debug` | yes |  |
| `invocation.run_mode` | enum: `standalone`, `client-server` | yes |  |
| `invocation.services` | array of object | yes | Every service the invocation started or depended on, with ownership. |
| `invocation.services[].kind` | enum: `cub_master`, `cub_server`, `broker`, `ha-master`, `ha-slave`, `ha-replica`, `cdc-consumer`, `other` | yes |  |
| `invocation.services[].identity` | string | yes | Database name, port or process name that identifies the instance. |
| `invocation.services[].port` | integer/null | no |  |
| `invocation.services[].owned` | boolean | yes | True when the scenario created it and may crash or clean it. |
| `invocation.instrumentation` | object/null | yes | Null for unmodified-engine runs. Instrumented runs are separate configurations and carry patch and build identity. |
| `invocation.instrumentation.worktree` | string | yes |  |
| `invocation.instrumentation.patch_id` | string | yes |  |
| `invocation.instrumentation.patch_hash` | string `^sha256:[0-9a-f]{64}$` | yes |  |
| `invocation.instrumentation.build_hash` | string `^sha256:[0-9a-f]{64}$` | yes |  |
| `invocation.instrumentation.fault_disabled_control_manifest` | string/null | yes | Path of the manifest of the fault-disabled control run, or null when not yet run (then no fault coverage is claimed). |
| `invocation.seed` | object/null | yes | Null for fixed deterministic workloads. A seed alone never reconstructs a concurrent execution; the trace lives in the replay bundle. |
| `invocation.seed.value` | integer/string | yes |  |
| `invocation.seed.generator` | string | yes |  |
| `invocation.seed.generator_version` | string | yes |  |
| `invocation.runner` | object | yes |  |
| `invocation.runner.kind` | enum: `ctp-sql`, `ctp-shell` | yes |  |
| `invocation.runner.ctp_fingerprint` | string | yes | Artifact fingerprint of the external CTP install (it is not a Git checkout). |
| `invocation.runner.command` | string | yes |  |
| `invocation.runner.scenario_selection` | string | yes | The explicit scenario path or list given to CTP. |
| `expected` | object | yes | Declared before the run: the case list and counts the run must reproduce. |
| `expected.case_list` | string | yes |  |
| `expected.case_list_hash` | string `^sha256:[0-9a-f]{64}$` | yes |  |
| `expected.case_count` | integer | yes |  |
| `expected.assertion_count` | integer/null | yes | Null when the seam cannot pre-count assertions; then the proof compares executed assertions against per-case declarations. |
| `discovered` | object | yes |  |
| `discovered.case_count` | integer | yes |  |
| `discovered.case_names` | array of string | yes |  |
| `executed` | object | yes |  |
| `executed.case_count` | integer | yes |  |
| `executed.assertion_count` | integer | yes |  |
| `proof` | object | yes | Comparison of expectation with discovery and execution. Any mismatch is a failure of proof, never a pass. |
| `proof.verdict` | enum: `proven`, `failure-of-proof` | yes |  |
| `proof.launcher_exit_status` | integer/null | yes |  |
| `proof.setup_log` | string/null | yes |  |
| `proof.mismatches` | array of object | yes |  |
| `proof.mismatches[].kind` | enum: `case-not-discovered`, `case-not-executed`, `unexpected-case`, `assertion-count-mismatch`, `setup-log-error`, `launcher-exit-mismatch`, `skip-recorded-as-ok` | yes |  |
| `proof.mismatches[].detail` | string | yes |  |
| `cases` | array of object | yes |  |
| `cases[].case` | object | yes |  |
| `cases[].case.repository` | enum: `testcases`, `testcases-private-ex` | yes |  |
| `cases[].case.path` | string | yes | Repository-relative path of the case file or case directory. |
| `cases[].case.name` | string | yes |  |
| `cases[].requirements` | array of string `^OOS-(REP\|SQL\|RD\|SCH\|CL\|DUR\|OPS\|RES)-[0-9]{2}$` | yes |  |
| `cases[].outcome` | enum: `PASS`, `FAIL`, `SKIP`, `UNSUPPORTED`, `BLOCKED` or null | yes | Null only when the case was not executed; then outstanding is not null. |
| `cases[].skip_reason` | string/null | yes | Required text when outcome is SKIP. |
| `cases[].assertions` | object | yes |  |
| `cases[].assertions.expected` | integer/null | yes |  |
| `cases[].assertions.executed` | integer | yes |  |
| `cases[].assertions.failed` | integer | yes |  |
| `cases[].oos_evidence` | object | yes |  |
| `cases[].oos_evidence.status` | enum: `proven`, `reused`, `missing`, `not-applicable` | yes | proven: activation evidence captured in this run. reused: matching evidence from another run with recorded applicability. missing: logical checks ran without OOS-path evidence (not OOS coverage). not-applicable: the case asserts a non-activation property (for example a rejection). |
| `cases[].oos_evidence.channel` | enum: null, `show-heap-oos`, `diagdb-owner-descriptor`, `debug-oos-log`, `instrumentation-counter`, `injection-acknowledgement`, `unit-test-seam`, `other` | yes |  |
| `cases[].oos_evidence.reference` | string/null | yes | Path (and hash where bulky) of the captured evidence. |
| `cases[].oos_evidence.applicability` | object/null | yes | Required content when status is reused: what must match for the evidence to transfer. |
| `cases[].oos_evidence.applicability.fixture` | string | yes |  |
| `cases[].oos_evidence.applicability.execution_path` | string | yes |  |
| `cases[].oos_evidence.applicability.engine_configuration` | string | yes |  |
| `cases[].oos_evidence.applicability.conditions` | string | yes |  |
| `cases[].oos_evidence.applicability.source_manifest` | string | yes |  |
| `cases[].attempts` | array of object | yes |  |
| `cases[].attempts[].attempt_id` | string | yes |  |
| `cases[].attempts[].attempt_record` | string | yes |  |
| `cases[].attempts[].bundle` | string/null | yes |  |
| `cases[].attempts[].bundle_hash` | string `^sha256:[0-9a-f]{64}$` or null | yes |  |
| `cases[].outstanding` | object/null | yes |  |
| `cases[].outstanding.reason` | enum: `cap-reached`, `not-discovered`, `not-written`, `admission-refused`, `prerequisite-missing`, `infrastructure-unavailable` | yes |  |
| `cases[].outstanding.detail` | string | yes |  |
| `outstanding_coverage` | object | yes | What this invocation did not cover. A reached cap never waives it. |
| `outstanding_coverage.cases_not_executed` | array of string | yes |  |
| `outstanding_coverage.configurations_not_run` | array of string | yes |  |
| `outstanding_coverage.requirements_without_executed_case` | array of string `^OOS-(REP\|SQL\|RD\|SCH\|CL\|DUR\|OPS\|RES)-[0-9]{2}$` | yes |  |
| `outstanding_coverage.note` | string/null | yes |  |
| `answer_promotions` | array of object | yes | CTP result-to-answer workflow per case: the first-run result is a candidate until reviewed. |
| `answer_promotions[].case` | string | yes |  |
| `answer_promotions[].action` | enum: `candidate`, `promoted`, `retained-as-failure-evidence` | yes |  |
| `answer_promotions[].flagged_for_user` | boolean | yes | True when the case touches a Specification gap or an observed-versus-normative disagreement; the user signs off. |
| `answer_promotions[].review_note` | string/null | yes |  |
| `answer_promotions[].reviewer` | string/null | yes |  |
<!-- END GENERATED: schema-manifest -->

## 5. Coverage matrix

<!-- BEGIN GENERATED: schema-matrix -->
**CBRD-26659 coverage matrix** — The cross-invocation aggregation keyed by requirement ID. Each row is one (requirement, case, configuration) chain: requirement, case, configuration, run, OOS-path evidence, finding, with flakiness, known-issue link and attribution as separate fields. A later pass never erases an earlier failure; accepted exclusions are dated entries only the user may add. Rows are merged from manifests by tooling; exclusions are never written by tooling.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schema_version` | const `1` | yes |  |
| `generated_at` | string `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z\|[+-][0-9]{2}:[0-9]{2})$` | yes |  |
| `catalogue` | object | yes |  |
| `catalogue.path` | string | yes |  |
| `catalogue.hash` | string `^sha256:[0-9a-f]{64}$` | yes |  |
| `rows` | array of object | yes |  |
| `rows[].row_id` | string | yes |  |
| `rows[].requirement` | string `^OOS-(REP\|SQL\|RD\|SCH\|CL\|DUR\|OPS\|RES)-[0-9]{2}$` | yes |  |
| `rows[].family` | enum: `Representation`, `SQL operations`, `Read paths`, `Schema and utilities`, `Concurrent lifetime`, `Durability`, `Operational features`, `Resource pressure` | yes |  |
| `rows[].case` | object or null | yes | Null when no case exists yet for the requirement (Delivery gap row). |
| `rows[].case.repository` | enum: `testcases`, `testcases-private-ex` | yes |  |
| `rows[].case.path` | string | yes |  |
| `rows[].case.name` | string | yes |  |
| `rows[].configuration` | object or null | yes |  |
| `rows[].configuration.page_size` | enum: `4096`, `8192`, `16384` | yes |  |
| `rows[].configuration.build_mode` | enum: `release`, `debug` | yes |  |
| `rows[].configuration.run_mode` | enum: `standalone`, `client-server` | yes |  |
| `rows[].configuration.instrumentation_id` | string/null | yes |  |
| `rows[].configuration.services` | array of string | yes |  |
| `rows[].run` | object or null | yes |  |
| `rows[].run.manifest_id` | string | yes |  |
| `rows[].run.manifest_path` | string | yes |  |
| `rows[].run.manifest_hash` | string `^sha256:[0-9a-f]{64}$` | yes |  |
| `rows[].run.engine_commit` | string `^[0-9a-f]{40}$` | yes |  |
| `rows[].run.testcase_commit` | string `^[0-9a-f]{40}$` | yes |  |
| `rows[].run.context_content_hash` | string `^sha256:[0-9a-f]{64}$` | yes |  |
| `rows[].oos_evidence` | object | yes |  |
| `rows[].oos_evidence.status` | enum: `proven`, `reused`, `missing`, `not-applicable` | yes |  |
| `rows[].oos_evidence.channel` | enum: null, `show-heap-oos`, `diagdb-owner-descriptor`, `debug-oos-log`, `instrumentation-counter`, `injection-acknowledgement`, `unit-test-seam`, `other` | yes |  |
| `rows[].oos_evidence.reference` | string/null | yes |  |
| `rows[].oos_evidence.applicability` | object/null | yes |  |
| `rows[].oos_evidence.applicability.fixture` | string | yes |  |
| `rows[].oos_evidence.applicability.execution_path` | string | yes |  |
| `rows[].oos_evidence.applicability.engine_configuration` | string | yes |  |
| `rows[].oos_evidence.applicability.conditions` | string | yes |  |
| `rows[].oos_evidence.applicability.source_manifest` | string | yes |  |
| `rows[].finding` | object | yes | Outcome history and classification. latest never overwrites history; ever_failed is monotonic. |
| `rows[].finding.latest_outcome` | enum: `PASS`, `FAIL`, `SKIP`, `UNSUPPORTED`, `BLOCKED` or null | yes | Null when no attempt exists yet (Delivery gap). |
| `rows[].finding.ever_failed` | boolean | yes |  |
| `rows[].finding.history` | array of object | yes |  |
| `rows[].finding.history[].manifest_id` | string | yes |  |
| `rows[].finding.history[].attempt_id` | string | yes |  |
| `rows[].finding.history[].outcome` | enum: `PASS`, `FAIL`, `SKIP`, `UNSUPPORTED`, `BLOCKED` | yes | Fixed per-attempt taxonomy. |
| `rows[].finding.history[].at` | string `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z\|[+-][0-9]{2}:[0-9]{2})$` | yes |  |
| `rows[].finding.gap_kind` | enum: `none`, `Delivery gap`, `Capability gap`, `Specification gap`, `Engine defect` | yes | Glossary classification of a non-pass. 'none' only when the latest outcome is PASS with proven or reused OOS evidence. |
| `rows[].finding.summary` | string/null | yes |  |
| `rows[].flakiness` | object | yes | Separate from the outcome: counts and reproduction status. |
| `rows[].flakiness.attempts` | integer | yes |  |
| `rows[].flakiness.failures` | integer | yes |  |
| `rows[].flakiness.intermittent` | boolean | yes |  |
| `rows[].flakiness.consecutive_fresh_fixture_reproductions` | integer | yes |  |
| `rows[].flakiness.deterministic_claim` | boolean | yes | May be true only with three or more consecutive fresh-fixture reproductions, all recorded. |
| `rows[].known_issue` | object | yes |  |
| `rows[].known_issue.ticket` | string/null `^CBRD-[0-9]+$` | yes |  |
| `rows[].known_issue.relation` | enum: `none`, `reproduces`, `related`, `blocked-by` | yes |  |
| `rows[].attribution` | object | yes | Separate from the outcome. An unexplained failure stays 'unknown'; 'engine' requires evidence. |
| `rows[].attribution.target` | enum: `unknown`, `engine`, `harness`, `instrumentation`, `setup`, `specification` | yes |  |
| `rows[].attribution.evidence` | string/null | yes |  |
| `rows[].attribution.note` | string/null | yes |  |
| `rows[].attempt_records` | array of string | yes |  |
| `accepted_exclusions` | array of object | yes |  |
| `accepted_exclusions[].requirement` | string `^OOS-(REP\|SQL\|RD\|SCH\|CL\|DUR\|OPS\|RES)-[0-9]{2}$` | yes |  |
| `accepted_exclusions[].date` | string `^[0-9]{4}-[0-9]{2}-[0-9]{2}$` | yes |  |
| `accepted_exclusions[].reason` | string | yes |  |
| `accepted_exclusions[].accepted_by` | const `user` | yes |  |
| `accepted_exclusions[].scope` | string/null | yes | Which cases or configurations the exclusion covers when not the whole requirement. |
| `accepted_exclusions[].proposed_in` | string/null | yes | Report or ticket where an agent proposed the exclusion. |
<!-- END GENERATED: schema-matrix -->

## 6. Attempt record

<!-- BEGIN GENERATED: schema-attempt-record -->
**CBRD-26659 attempt record (compact, one per attempt)** — The compact record kept for every attempt, original or derived, forever. It carries identity, outcome, evidence status, ownership, deadlines and cleanup, and points at the bulky replay bundle. Original attempts, reruns, minimized derivatives and reproduction runs are linked through parent_attempt and finding_id; none replaces another.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schema_version` | const `1` | yes |  |
| `attempt_id` | string `^[A-Za-z0-9._:-]+$` | yes |  |
| `kind` | enum: `original`, `rerun`, `minimized`, `reproduction` | yes | original: first attempt of a scenario in an invocation. rerun: same workload again. minimized: reduced derivative that must keep both the failure and the OOS path. reproduction: fresh-fixture run counted toward a deterministic claim. |
| `parent_attempt` | string/null | yes | Required for rerun, minimized and reproduction attempts. |
| `finding_id` | string/null | yes | Groups attempts of one scenario/finding across invocations. |
| `case` | object | yes |  |
| `case.repository` | enum: `testcases`, `testcases-private-ex` | yes |  |
| `case.path` | string | yes |  |
| `case.name` | string | yes |  |
| `requirements` | array of string `^OOS-(REP\|SQL\|RD\|SCH\|CL\|DUR\|OPS\|RES)-[0-9]{2}$` | yes |  |
| `manifest_id` | string | yes |  |
| `configuration` | object | yes |  |
| `configuration.page_size` | enum: `4096`, `8192`, `16384` | yes |  |
| `configuration.build_mode` | enum: `release`, `debug` | yes |  |
| `configuration.run_mode` | enum: `standalone`, `client-server` | yes |  |
| `configuration.instrumentation_id` | string/null | yes |  |
| `configuration.seed` | integer/string/null | yes |  |
| `started_at` | string `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z\|[+-][0-9]{2}:[0-9]{2})$` | yes |  |
| `ended_at` | string `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z\|[+-][0-9]{2}:[0-9]{2})$` | yes |  |
| `deadline` | object | yes | Every barrier and recovery wait has a deadline; a timeout captures evidence and never reports success. |
| `deadline.seconds` | integer | yes |  |
| `deadline.reached` | boolean | yes |  |
| `deadline.evidence_captured_on_timeout` | boolean/null | yes | Null when the deadline was not reached. |
| `outcome` | enum: `PASS`, `FAIL`, `SKIP`, `UNSUPPORTED`, `BLOCKED` | yes | Fixed per-attempt taxonomy. |
| `skip_reason` | string/null | yes |  |
| `assertions` | object | yes |  |
| `assertions.executed` | integer | yes |  |
| `assertions.failed` | integer | yes |  |
| `expected_versus_actual` | string/null | yes | Path of the expected-versus-actual comparison (CTP result/answer diff or shell assertion log). |
| `oos_evidence` | object | yes |  |
| `oos_evidence.status` | enum: `proven`, `reused`, `missing`, `not-applicable` | yes |  |
| `oos_evidence.channel` | enum: null, `show-heap-oos`, `diagdb-owner-descriptor`, `debug-oos-log`, `instrumentation-counter`, `injection-acknowledgement`, `unit-test-seam`, `other` | yes |  |
| `oos_evidence.reference` | string/null | yes |  |
| `oos_evidence.applicability` | object/null | yes |  |
| `oos_evidence.applicability.fixture` | string | yes |  |
| `oos_evidence.applicability.execution_path` | string | yes |  |
| `oos_evidence.applicability.engine_configuration` | string | yes |  |
| `oos_evidence.applicability.conditions` | string | yes |  |
| `oos_evidence.applicability.source_manifest` | string | yes |  |
| `barriers` | array of object | yes | Acknowledged phases in schedule order; an unreached target phase never satisfies a schedule. |
| `barriers[].name` | string | yes |  |
| `barriers[].participant` | string | yes |  |
| `barriers[].acknowledged` | boolean | yes |  |
| `barriers[].at` | string `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z\|[+-][0-9]{2}:[0-9]{2})$` or null | yes |  |
| `injections` | array of object | yes | One entry per armed fault; an unfired hook provides no coverage. |
| `injections[].site` | string | yes |  |
| `injections[].target_operation` | string | yes |  |
| `injections[].occurrence_count` | integer | yes |  |
| `injections[].requested_action` | string | yes |  |
| `injections[].fired` | boolean | yes |  |
| `injections[].acknowledgement` | string/null | yes | Path of the fired-site acknowledgement evidence. |
| `resources_owned` | object | yes | Only these may be crashed or cleaned by the attempt. |
| `resources_owned.databases` | array of string | yes |  |
| `resources_owned.processes` | array of string | yes |  |
| `resources_owned.ports` | array of integer | yes |  |
| `resources_owned.directories` | array of string `^/home/` | yes |  |
| `cleanup` | object | yes |  |
| `cleanup.performed` | boolean | yes |  |
| `cleanup.scope_verified` | boolean | yes | True when cleanup was checked to touch only resources_owned. |
| `cleanup.evidence_preserved_first` | boolean/null | yes |  |
| `cleanup.evidence` | string/null | yes |  |
| `bundle` | object/null | yes | Null only for a PASS whose bulky artifacts expired; the attempt record itself is kept. |
| `bundle.path` | string | yes |  |
| `bundle.hash` | string `^sha256:[0-9a-f]{64}$` | yes |  |
| `reproduction` | object/null | yes |  |
| `reproduction.fresh_fixture` | boolean | yes |  |
| `reproduction.consecutive_reproductions_so_far` | integer | yes |  |
| `reproduction.failure_reproduced` | boolean | yes |  |
| `notes` | string/null | yes |  |
<!-- END GENERATED: schema-attempt-record -->

## 7. Replay bundle index

<!-- BEGIN GENERATED: schema-replay-bundle -->
**CBRD-26659 replay bundle index (one per attempt)** — The index of one attempt's bulky evidence under the campaign's /home storage. Every item the specification lists is present in the index with a state: present, missing, or not-applicable. Missing evidence is recorded as missing; a bundle with missing items is never described as complete. Bundles are referenced from attempt records and matrix rows by path and hash.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schema_version` | const `1` | yes |  |
| `bundle_id` | string `^[A-Za-z0-9._:-]+$` | yes |  |
| `attempt_id` | string | yes |  |
| `created_at` | string `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z\|[+-][0-9]{2}:[0-9]{2})$` | yes |  |
| `root_path` | string `^/home/` | yes | Bundle directory under /home; the temporary filesystem is unsuitable. |
| `total_bytes` | integer | yes |  |
| `complete` | boolean | yes | True only when no item is in state missing. |
| `items` | object | yes | One entry per specification item. |
| `items.workload` | object | yes | Exact SQL/workload files as executed. |
| `items.workload.state` | enum: `present`, `missing`, `not-applicable` | yes |  |
| `items.workload.path` | string/null | yes | Bundle-relative path; required when present. |
| `items.workload.hash` | string `^sha256:[0-9a-f]{64}$` or null | yes |  |
| `items.workload.note` | string/null | yes | Why an item is missing or not applicable. |
| `items.seed_and_generator_version` | object | yes | Seed value, generator name and version; not-applicable for fixed deterministic workloads. |
| `items.seed_and_generator_version.state` | enum: `present`, `missing`, `not-applicable` | yes |  |
| `items.seed_and_generator_version.path` | string/null | yes | Bundle-relative path; required when present. |
| `items.seed_and_generator_version.hash` | string `^sha256:[0-9a-f]{64}$` or null | yes |  |
| `items.seed_and_generator_version.note` | string/null | yes | Why an item is missing or not applicable. |
| `items.session_and_barrier_trace` | object | yes | Ordered operations and acknowledged phase schedule; not-applicable for single-session cases. |
| `items.session_and_barrier_trace.state` | enum: `present`, `missing`, `not-applicable` | yes |  |
| `items.session_and_barrier_trace.path` | string/null | yes | Bundle-relative path; required when present. |
| `items.session_and_barrier_trace.hash` | string `^sha256:[0-9a-f]{64}$` or null | yes |  |
| `items.session_and_barrier_trace.note` | string/null | yes | Why an item is missing or not applicable. |
| `items.injection_acknowledgements` | object | yes | Site, target operation, occurrence count, requested action and fired acknowledgement per fault; not-applicable without instrumentation. |
| `items.injection_acknowledgements.state` | enum: `present`, `missing`, `not-applicable` | yes |  |
| `items.injection_acknowledgements.path` | string/null | yes | Bundle-relative path; required when present. |
| `items.injection_acknowledgements.hash` | string `^sha256:[0-9a-f]{64}$` or null | yes |  |
| `items.injection_acknowledgements.note` | string/null | yes | Why an item is missing or not applicable. |
| `items.engine_identity` | object | yes | Baseline commit, version string, library hashes. |
| `items.engine_identity.state` | enum: `present`, `missing`, `not-applicable` | yes |  |
| `items.engine_identity.path` | string/null | yes | Bundle-relative path; required when present. |
| `items.engine_identity.hash` | string `^sha256:[0-9a-f]{64}$` or null | yes |  |
| `items.engine_identity.note` | string/null | yes | Why an item is missing or not applicable. |
| `items.testcase_identity` | object | yes | Repository, branch, commit, base commit. |
| `items.testcase_identity.state` | enum: `present`, `missing`, `not-applicable` | yes |  |
| `items.testcase_identity.path` | string/null | yes | Bundle-relative path; required when present. |
| `items.testcase_identity.hash` | string `^sha256:[0-9a-f]{64}$` or null | yes |  |
| `items.testcase_identity.note` | string/null | yes | Why an item is missing or not applicable. |
| `items.specification_identity` | object | yes | Context revision, content hash, catalogue hash. |
| `items.specification_identity.state` | enum: `present`, `missing`, `not-applicable` | yes |  |
| `items.specification_identity.path` | string/null | yes | Bundle-relative path; required when present. |
| `items.specification_identity.hash` | string `^sha256:[0-9a-f]{64}$` or null | yes |  |
| `items.specification_identity.note` | string/null | yes | Why an item is missing or not applicable. |
| `items.build_and_configuration_identity` | object | yes | Build mode, configure options, page size, run mode, cubrid.conf and broker configuration as used. |
| `items.build_and_configuration_identity.state` | enum: `present`, `missing`, `not-applicable` | yes |  |
| `items.build_and_configuration_identity.path` | string/null | yes | Bundle-relative path; required when present. |
| `items.build_and_configuration_identity.hash` | string `^sha256:[0-9a-f]{64}$` or null | yes |  |
| `items.build_and_configuration_identity.note` | string/null | yes | Why an item is missing or not applicable. |
| `items.instrumentation_identity` | object | yes | Patch id and hash, build hash, fault-disabled control reference; not-applicable for unmodified runs. |
| `items.instrumentation_identity.state` | enum: `present`, `missing`, `not-applicable` | yes |  |
| `items.instrumentation_identity.path` | string/null | yes | Bundle-relative path; required when present. |
| `items.instrumentation_identity.hash` | string `^sha256:[0-9a-f]{64}$` or null | yes |  |
| `items.instrumentation_identity.note` | string/null | yes | Why an item is missing or not applicable. |
| `items.fixture_identity` | object | yes | Database names, createdb parameters, fixture generation inputs. |
| `items.fixture_identity.state` | enum: `present`, `missing`, `not-applicable` | yes |  |
| `items.fixture_identity.path` | string/null | yes | Bundle-relative path; required when present. |
| `items.fixture_identity.hash` | string `^sha256:[0-9a-f]{64}$` or null | yes |  |
| `items.fixture_identity.note` | string/null | yes | Why an item is missing or not applicable. |
| `items.expected_versus_actual` | object | yes | Expected output, actual output and the comparison. |
| `items.expected_versus_actual.state` | enum: `present`, `missing`, `not-applicable` | yes |  |
| `items.expected_versus_actual.path` | string/null | yes | Bundle-relative path; required when present. |
| `items.expected_versus_actual.hash` | string `^sha256:[0-9a-f]{64}$` or null | yes |  |
| `items.expected_versus_actual.note` | string/null | yes | Why an item is missing or not applicable. |
| `items.logs` | object | yes | Server, client, CTP and utility logs; debug oos.log where produced. |
| `items.logs.state` | enum: `present`, `missing`, `not-applicable` | yes |  |
| `items.logs.path` | string/null | yes | Bundle-relative path; required when present. |
| `items.logs.hash` | string `^sha256:[0-9a-f]{64}$` or null | yes |  |
| `items.logs.note` | string/null | yes | Why an item is missing or not applicable. |
| `items.cores` | object | yes | Core files with matching binaries noted; not-applicable when no process crashed. |
| `items.cores.state` | enum: `present`, `missing`, `not-applicable` | yes |  |
| `items.cores.path` | string/null | yes | Bundle-relative path; required when present. |
| `items.cores.hash` | string `^sha256:[0-9a-f]{64}$` or null | yes |  |
| `items.cores.note` | string/null | yes | Why an item is missing or not applicable. |
| `items.replay_command_with_prerequisites` | object | yes | The command that replays the attempt and the prerequisites (install, databases, services) it assumes. |
| `items.replay_command_with_prerequisites.state` | enum: `present`, `missing`, `not-applicable` | yes |  |
| `items.replay_command_with_prerequisites.path` | string/null | yes | Bundle-relative path; required when present. |
| `items.replay_command_with_prerequisites.hash` | string `^sha256:[0-9a-f]{64}$` or null | yes |  |
| `items.replay_command_with_prerequisites.note` | string/null | yes | Why an item is missing or not applicable. |
| `uncommitted_snapshots` | array of object | yes | Source or specification snapshots kept when a commit alone does not identify the input. |
| `uncommitted_snapshots[].what` | string | yes |  |
| `uncommitted_snapshots[].path` | string | yes |  |
| `uncommitted_snapshots[].hash` | string `^sha256:[0-9a-f]{64}$` | yes |  |
| `retention` | object | yes |  |
| `retention.class` | enum: `success-bulky`, `failure`, `minimized-reproducer` | yes | success-bulky: seven days. failure: through triage plus thirty days. minimized-reproducer: kept. |
| `retention.expires_on` | string `^[0-9]{4}-[0-9]{2}-[0-9]{2}$` or null | yes |  |
| `retention.hold_reason` | string/null | yes | Set when an unresolved finding still needs the bundle past its expiry. |
| `minimization` | object/null | yes | Set on minimized derivatives; both the failure and the relevant OOS path must remain. |
| `minimization.derived_from` | string | yes |  |
| `minimization.failure_preserved` | boolean | yes |  |
| `minimization.oos_path_preserved` | boolean | yes |  |
| `minimization.reduction` | string | yes | What was reduced: rows, operations, values, participants. |
<!-- END GENERATED: schema-replay-bundle -->

## 8. Catalogue and scenario-map schemas

<!-- BEGIN GENERATED: schema-requirement -->
**CBRD-26659 requirement catalogue** — The requirement catalogue every case, manifest row, matrix row and report line cites. One file, one pin, many requirements. IDs are stable forever; citations, statuses and observations are updated in place.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schema_version` | const `1` | yes |  |
| `pin` | object | yes | Ticket 11 identities every citation carries. Changing the pin is a recorded decision, never an edit. |
| `pin.engine_baseline` | string `^[0-9a-f]{40}$` | yes | Campaign engine baseline commit on feat/oos. |
| `pin.context_repository` | string | yes |  |
| `pin.context_revision` | string `^[0-9a-f]{40}$` | yes | Committed HEAD of the normative context repository at pin time. |
| `pin.content_hashes` | object | yes | sha256 of each cited document's working copy at pin time (the 24-byte wording exists only in the uncommitted copy). |
| `pin.content_hashes.*` | string `^sha256:[0-9a-f]{64}$` | no | keyed entries |
| `pin.snapshot` | string | yes | Repository-relative path of the archived normative snapshot. |
| `pin.baseline_record` | string | yes | Repository-relative path of the ticket 11 baseline record. |
| `requirements` | array of object | yes |  |
| `requirements[].id` | string `^OOS-(REP\|SQL\|RD\|SCH\|CL\|DUR\|OPS\|RES)-[0-9]{2}$` | yes | Stable identity. The family code is fixed at issue time and never renumbered or reused. |
| `requirements[].title` | string | yes |  |
| `requirements[].statement` | string | yes | The required behavior in normative wording, independent of the pinned engine's output. |
| `requirements[].family` | enum: `Representation`, `SQL operations`, `Read paths`, `Schema and utilities`, `Concurrent lifetime`, `Durability`, `Operational features`, `Resource pressure` | yes |  |
| `requirements[].seam` | enum: `public-sql`, `private-shell`, `either` | yes | Where the spec places the cases: CTP SQL runner (public), CTP shell runner (private), or either. |
| `requirements[].citation` | object | yes | Exactly one normative citation: a context heading, an ADR, or an explicitly accepted CBRD design, with the pinned revision and content hash. |
| `requirements[].citation.kind` | enum: `context-heading`, `adr`, `accepted-design` | yes |  |
| `requirements[].citation.document` | enum: `OOS-CONTEXT.md`, `ADR-0001`, `ADR-0002`, `ADR-0003`, `ADR-0004` | yes |  |
| `requirements[].citation.source` | string | yes | Heading, ADR title, or CBRD design plus the context passage that records its acceptance. |
| `requirements[].citation.revision` | string `^[0-9a-f]{40}$` | yes |  |
| `requirements[].citation.content_hash` | string `^sha256:[0-9a-f]{64}$` | yes |  |
| `requirements[].status` | enum: `assertable`, `observation-only`, `BLOCKED`, `UNSUPPORTED` | yes | assertable: expectation fixed and asserted. observation-only: recorded, never asserted as correct. BLOCKED: Specification gap. UNSUPPORTED: accepted design absent at the pin (Capability gap). |
| `requirements[].gap_kind` | enum: null, `Capability gap`, `Specification gap` | yes |  |
| `requirements[].authority` | object | yes |  |
| `requirements[].authority.policy` | enum: `assert`, `assert-after-eligibility`, `observe`, `withhold` | yes | assert: independently justified expectation. assert-after-eligibility: assert only after proven reclamation eligibility and safety. observe: record, never assert. withhold: no expectation fixed; engine output never promoted. |
| `requirements[].authority.note` | string | yes |  |
| `requirements[].authority_question` | string/null | yes | Required for BLOCKED: the question the context maintainer must answer. |
| `requirements[].accepted_design` | string/null | yes | Required for UNSUPPORTED: the accepted CBRD design or ADR that is absent at the pin. |
| `requirements[].specification_gap_topic` | string/null `^[a-z0-9-]+$` | yes |  |
| `requirements[].pinned_observation` | string/null | yes | What the pinned engine does, from ticket 11. Observation, never the expectation. |
| `requirements[].configuration_scope` | string/null | yes | Configurations the requirement applies to when not all (for example client-server only). |
| `requirements[].attack_dimensions` | array of string | yes | Adversarial dimensions case tickets must cover under this requirement. |
| `requirements[].expected_engine_findings` | array of string `^CBRD-[0-9]+$` | yes | Engine defects the campaign expects to surface here; a documented Engine defect still records the FAIL outcome. |
| `requirements[].related` | array of string `^OOS-(REP\|SQL\|RD\|SCH\|CL\|DUR\|OPS\|RES)-[0-9]{2}$` | yes |  |
<!-- END GENERATED: schema-requirement -->

<!-- BEGIN GENERATED: schema-scenario-map -->
**CBRD-26659 section 6 scenario traceability map** — Maps every scenario of the normative context's section 6 (Test Scenarios) to requirement IDs or to an explicit, reasoned exclusion. Section 6 is a mandatory traceability input, not the coverage ceiling.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schema_version` | const `1` | yes |  |
| `source` | object | yes |  |
| `source.document` | const `OOS-CONTEXT.md` | yes |  |
| `source.section` | string | yes |  |
| `source.revision` | string `^[0-9a-f]{40}$` | yes |  |
| `source.content_hash` | string `^sha256:[0-9a-f]{64}$` | yes |  |
| `scenarios` | array of object | yes |  |
| `scenarios[].scenario` | string `^[0-9]+\.[0-9]+$` | yes |  |
| `scenarios[].title` | string | yes |  |
| `scenarios[].requirements` | array of string `^OOS-(REP\|SQL\|RD\|SCH\|CL\|DUR\|OPS\|RES)-[0-9]{2}$` | yes |  |
| `scenarios[].exclusion` | object/null | yes |  |
| `scenarios[].exclusion.reason` | string | yes |  |
| `scenarios[].note` | string/null | yes | Where the scenario's own wording is superseded or partly UNSUPPORTED at the pin. |
<!-- END GENERATED: schema-scenario-map -->

## 9. Validation and examples

```bash
cd /home/vimkim/gh/my-cubrid-docs/cbrd-26659/campaign
python3 tools/check_campaign_records.py      # catalogue rules, scenario coverage, schema structure, examples, negative controls, document freshness
python3 tools/render_docs.py                 # re-render the generated blocks of both documents after editing JSON
```

The checker needs only the Python standard library; `tools/minischema.py` implements the JSON Schema subset the schemas use (type, properties, required, additionalProperties, enum, const, items, min/max, pattern, allOf/anyOf/oneOf/not, if/then/else, same-document `$ref`). A full validator such as `python3 -m jsonschema` may be substituted. Example records are shaped like the ticket 13 tracer bullet and are marked `EXAMPLE` in every identifier; the one accepted exclusion in `matrix.example.json` is a shape example, not a decision. Each negative control plants exactly one defect named in its file name and must be rejected; the checker fails if any control is accepted.

## 10. Ticket 12 criteria checklist

| Criterion | Where met |
|---|---|
| Manifest schema: invocation identity (engine, testcase and context revisions with hash, page size, build mode, services, instrumentation identity, seed and generator version), expected case identities and counts, per case outcome, OOS-coverage evidence status, bundle links and outstanding coverage | §4, `manifest.schema.json`, checker `manifest-*` |
| Matrix schema: requirement, case, configuration, run, OOS-path evidence, finding, plus separate flakiness, known-issue link and attribution fields, and dated accepted-exclusion entries only the user may add | §5, `matrix.schema.json`, checker `matrix-*` |
| Attempt-record and replay-bundle content lists follow the spec's Outcomes, replay and minimization section, including "missing" as a recordable state per item | §6, §7, checker `replay-items`, `replay-item-state` |
| Committed in the campaign folder; vocabulary committed on its own | docs repository history |
