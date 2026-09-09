# 05: Prove server-mode lifecycle correctness

**What to build:** Verified partitioned OOS write behavior under server concurrency, rollback, recovery, and vacuum interactions, rather than inferring these guarantees from standalone SQL tests.

**Blocked by:** 03 — Route UPDATEs and pending increments correctly.

**Status:** blocked

**Parent:** [Effective-key routing specification](../spec.md).

**Execution gate:** Server sessions, failure/recovery experiments, test execution, and scoped engine fixes require separate authorization. Use isolated test databases and existing project test mechanisms when authorized.

- [ ] Establish the same scenarios on the pinned baseline and candidate with recorded source/binary/build-mode provenance; SA results do not count as SERVER_MODE evidence.
- [ ] Verify concurrent old-version readers remain able to retrieve prior values during same-partition and partition-moving updates while the new values belong to the destination heap.
- [ ] Verify moved-update rollback restores the prior row/value behavior and leaves no durable wrong-owner OOS effects.
- [ ] Exercise appropriate committed/uncommitted recovery cases and verify logical values, partition placement, and storage ownership after recovery.
- [ ] Exercise vacuum interactions after relevant transactions/readers finish; preserve the baseline reclamation contract without changing vacuum algorithms or OOS-chain ownership rules.
- [ ] Use deterministically coordinated sessions and explicit observable expectations, avoiding sleep-based assumptions where the existing harness provides synchronization.
- [ ] Report baseline defects separately with evidence. Do not label a scenario passed merely because both revisions fail, or repair unrelated vacuum/recovery defects without a new scope decision.
- [ ] Reverify lifecycle scenarios affected by any scoped repair and retain enough reproduction information for the final integrated-revision gate.

**Completion evidence:** Reproducible server scenarios, session outcomes, ownership observations, recovery/vacuum checks, and a clear list of any unresolved baseline blockers. This ticket does not establish performance acceptance.

**Spec coverage:** User stories 17, 25–27, 31, 36–37; server MVCC, movement, rollback, recovery, and reclamation proof obligations.

## Comments

- 2026-09-09 (dependency clarification): User expects a fix specifically for CBRD-27237 soon and does not expect CBRD-27230 to resolve it. This supersedes the earlier combined dependency assumption. The existing `OosRealVacuum.RolledBackUpdateKeepsCommittedOosAfterVacuum` regression is a required acceptance test; the full lifecycle gate remains required. Inspect the actual fix's dependencies when available. No patch/date verified, tests run, or integration authorized by this clarification.

- 2026-09-09: User confirmed dependency waiting for the separate CBRD-27230/27237 lifecycle repair. Separate repair-design work is deferred. Ticket remains blocked; no engine changes, experiments, integration, monitoring or gate waiver authorized by this confirmation. See the accepted [completion path](../../../cbrd-27089/design/acceptance-completion-path-213ce80f5-codex.md).

- 2026-09-09: Read-only upstream audit found no available fix closing the rollback/vacuum blocker. PR #7695 protects chain identity but retains the unsafe forward walk; 27230/27237 remain open. Recommended dependency wait versus separately scoped repair-design work is awaiting user judgment. No integration, experiments or gate waiver performed. See [completion path](../../../cbrd-27089/design/acceptance-completion-path-213ce80f5-codex.md).

- 2026-09-08: User authorized tickets 04–07. Existing candidate real-vacuum tests pass 10/10. A new rollback-survival regression fails on both the candidate and exact-original engine `b871ea386`: original OOS contents are readable immediately after rollback, then unreadable after a committed-delete witness proves vacuum progress. This is a lower-layer heap/OOS test, not partition routing or crash-recovery coverage. The evidence matches the known CBRD-27237 baseline defect. No vacuum repair or gate waiver is authorized. Work item 82; [blocker report](../../../cbrd-27089/design/tickets04-07-lifecycle-blocker-b871ea386-codex.md).
