# CUBRID project vocabulary

Canonical domain vocabulary for the design notes in this repository.

## Out-of-row overflow storage

**OOS chain identity**:
The identity of one particular stored out-of-row value, distinct from the storage address that may later be reused for another value. Matching identity does not establish permission to reclaim that value.
_Avoid_: Reclamation eligibility when referring only to identity matching

**OOS reclamation eligibility**:
The condition that an out-of-row value may be removed without invalidating a value still required by transaction visibility, rollback, or recovery. This is distinct from correctly identifying the value to remove.
_Avoid_: Identity safety when referring to permission to reclaim

## OOS testcase campaign

**Campaign acceptance**:
The state in which every requirement traces to executed cases with OOS-path evidence and all coverage families are accounted for. Documented engine failures may remain.
_Avoid_: Engine acceptance, feature acceptance, done

**Engine acceptance**:
Merge readiness of the OOS feature itself. Not a goal of the testcase campaign.
_Avoid_: Campaign acceptance

**Delivery gap**:
A required case that was not written, or was not executed within budget.
_Avoid_: Gap, missing test, skipped

**Capability gap**:
A requirement the harness, instrumentation or pinned engine cannot reach or observe.
_Avoid_: Gap, unsupported, blocked

**Specification gap**:
A requirement whose authoritative expected behavior is unclear or disputed.
_Avoid_: Gap, open question, TBD

**Engine defect**:
A campaign finding attributed to the engine with supporting evidence. Distinct from an unexplained failure.
_Avoid_: Bug, failure, known issue

**Requirement ID**:
The stable identifier of one campaign requirement. Issued once, never renumbered or reused; only its citation, status and observations change.
_Avoid_: Test ID, scenario number, case number

**Normative citation**:
The single source a requirement cites for its required behavior, with the pinned revision and content hash: a context heading, an ADR, or an explicitly accepted CBRD design.
_Avoid_: Reference, link, source behavior

**Coverage family**:
One of the eight mandatory groupings every requirement belongs to and every coverage matrix must show.
_Avoid_: Category, area, suite, module

**Assertable requirement**:
A requirement whose expected behavior is fixed by an oracle justified independently of the engine's output and asserted by its cases.
_Avoid_: Testable, passing, green

**Observation-only requirement**:
A requirement whose behavior at the pinned engine is recorded because its acceptance is not established; it is never asserted as correct.
_Avoid_: Soft assertion, warning, informational test

**OOS-path evidence**:
Proof that a case's intended out-of-row path executed, recorded separately from the case's outcome.
_Avoid_: Coverage, activation, large input, DISK_SIZE

**Outcome**:
The result of one executed attempt: PASS, FAIL, SKIP with reason, UNSUPPORTED, or BLOCKED.
_Avoid_: OK, NOK, status, result, green, red

**Campaign manifest**:
The per-invocation record of invocation identity, expected and executed cases, outcomes, OOS-path evidence status and outstanding coverage.
_Avoid_: Run log, summary, report, results file

**Failure of proof**:
A mismatch between a manifest's expected case identities or counts and what was discovered or executed; never a pass.
_Avoid_: Infrastructure failure, flaky run, harness error

**Coverage matrix**:
The cross-invocation aggregation of requirement, case, configuration, run, OOS-path evidence and finding, with flakiness, known-issue link and attribution kept apart.
_Avoid_: Test matrix, results table, dashboard

**Attempt record**:
The compact per-attempt record kept indefinitely, pointing at the attempt's replay bundle.
_Avoid_: Result, run, log

**Replay bundle**:
The bulky per-attempt evidence set whose every item is marked present, missing or not applicable.
_Avoid_: Artifacts, logs, dump, evidence folder

**Accepted exclusion**:
A dated coverage-matrix entry by which the user, and only the user, converts incomplete coverage into an accepted deferral.
_Avoid_: Skip, waiver, deferral, exemption

**Flagged promotion**:
An answer promotion whose case touches a Specification gap or an observed-versus-normative disagreement, requiring the user's sign-off.
_Avoid_: Review, approval, sign-off (for unflagged promotions)

**Negative control**:
A deliberately wrong result that a checking mechanism must detect, kept outside the regression answers.
_Avoid_: Negative test, failing test, expected failure
