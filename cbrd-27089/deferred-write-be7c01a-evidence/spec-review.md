# Ticket 21 — Spec review

Reviewed `git diff f4299ac0cd777a2a964c1f197ae5ebf9841a4936...HEAD`, ending at `ab3d8d645f1496892fac188f6f9313bf0c41914b`, against `issues/12-spec.md`, `issues/21-draft.md` and the producer/verification evidence from tickets 13–20. Read-only source review; no new runtime pass is claimed by this report.

No actionable implementation findings or scope creep identified.

The production diff implements destination routing from owned canonical values, INSERT finalization before heap insertion, UPDATE finalization before index/replication consumers, and forwarding the same owner during movement. Probe adapters avoid OOS persistence. Raw rows and redistribution preserve serialized values and copied MVCC headers. Loader rows own retained payloads and account for them independently of physical packing; bulk finalization precedes heap-page latching. Replica groups retain OID fixup and atomic rollback, while serial/internal/address paths retain complete-record compatibility.

The retained complete-record MVCC assignment helper is not an ordinary-producer migration gap: attribute UPDATE supplies its old record, bypassing the reevaluation branch; raw and multi-update callers supply no reevaluation context. Borrowed OOS buffers/output slots are stable after sizing, and finalization introduces no second owned payload copy. Allocation errors are contained at the new allocation boundaries.

Acceptance remains distinct from this code review. The spec requires: “run the required checks before describing the replacement as verified” and “Unavailable checks may be disclosed in the authorized draft, but remain outstanding verification.” Ticket 21 must publish the final exact-revision results and paired memory evidence, identify historical evidence explicitly, and track any unavailable required checks concretely. Earlier configured CTest, HA, transaction/recovery and memory passes do not alone certify the final published revision. Existing baseline undefined-value/vacuum limitations and standalone-loader OOS limitations must remain visible within their documented scope.

Review total: **0 actionable Spec-axis code findings**. Final runtime verification and publication-material completion are owned by the parent task.

Incremental re-review: `git diff HEAD` plus the new `README.verification.md` inspected before the ticket21 commit. INDENT guards change no engine behavior; `LoaderFixture.isolate_runtime` preserves the extracted HA/transaction setup. The verification guide accurately separates external runners, CTest and pending remote checks. **0 additional findings.**
