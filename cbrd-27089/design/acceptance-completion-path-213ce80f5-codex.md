# PR7600 acceptance blockers and recommended completion path

Date: 2026-09-09. Local routing revision: `213ce80f54dc54130fcef22e616cb28f4835f6d5`; original PR baseline: `b871ea386d2c5419b7abae07dda58b9b7f36377a`.

Initial investigation scope: read-only source, GitHub and JIRA investigation plus documentation. Existing test evidence is cited, not rerun. Subsequently, the user explicitly authorized posting the dependency explanation on CBRD-27237; that comment was published and verified as recorded below. No engine changes, integration, experiments or gate waivers were performed.

## Decision state

Agreed and unchanged: retain independent final-record routing and early/final owner agreement; defer destination reuse; keep ticket 05 and ticket 06 runtime acceptance open; ticket 07 cannot declare acceptance with either unresolved. Ticket 04 is complete; ticket 06's measurement delivery is complete, not its runtime gate.

**Accepted and clarified by the user on 2026-09-09:** keep the routing change blocked pending a fix specifically for **CBRD-27237**, which the user expects soon. Do not assume CBRD-27230 will resolve it, or that the forthcoming fix requires CBRD-26950; inspect the actual patch and its dependencies when available. Do not integrate PR #7695 as if it fixed ticket 05. Separately scoped repair-design work is deferred, not authorized.

The user approved making the existing `OosRealVacuum.RolledBackUpdateKeepsCommittedOosAfterVacuum` regression a required acceptance test for that fix. Passing it is necessary but does not close the broader ticket 05 lifecycle gate. The expected arrival is user-provided planning information, not a verified delivery date or a claim that a patch is already available.

The user confirmed the recommended dependency wait. This decision round is settled. Repair mechanism, implementation, integration, and experiment authorization remain downstream decisions, not implicitly granted here. No automatic monitoring is started. External coordination is limited to the specifically authorized comment below. Reopen the investigation when a concrete lifecycle-fix patch is available or the user requests a different path; gate closure still requires the evidence below.

## Published dependency explanation

On 2026-09-09, at the user's explicit request, posted and read back [CBRD-27237 comment 4776296](http://jira.cubrid.org/browse/CBRD-27237?focusedCommentId=4776296&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-4776296). It explains the repeated baseline/candidate rollback-vacuum failure, why CBRD-27237 must precede CBRD-27089's final lifecycle acceptance (not the start of routing implementation), and the required regression plus broader lifecycle checks. It preserves the separate runtime gate and does not assume CBRD-27230 supplies the fix. No issue description, status or dependency link was changed.

## Remaining acceptance blockers

| Gate | Evidence and limit | Required closure |
| --- | --- | --- |
| Ticket 05: SERVER lifecycle | The rollback-survival regression fails on both original and candidate engines. It is a lower-layer heap/OOS case, not partition-routing proof. | A lifecycle repair plus the complete required partitioned concurrency, movement, rollback, recovery and vacuum evidence on identified revisions. |
| Ticket 06: runtime | Interleaved timings are inconclusive on the loaded host. CPU attribution found approximately +0.689% whole-process instructions for small inline partitioned inserts; this is not a measured runtime regression percentage or a passed gate. | Controlled, matched baseline/candidate measurements meeting the existing spec, with correct values and ownership. |
| Ticket 07: integrated acceptance | Earlier green subsets cannot substitute for either open gate or final-revision evidence. | Full requirement/evidence matrix, final revision review and applicable verification after both gates close. |

Prior evidence: [lifecycle reproduction](tickets04-07-lifecycle-blocker-b871ea386-codex.md), [interleaved timing](ticket06-interleaved-b871ea386-codex.md), [CPU attribution](ticket06-cpu-attribution-b871ea386-codex.md), [accepted final-routing retention](destination-reuse-review-213ce80f5-codex.md). The older lifecycle report's ticket 04/06 progress statements are historical, not current status.

## Upstream investigation

Live GitHub inspection and JIRA refresh on the date above, before the user's dependency clarification. Preserve this historical snapshot; it does not establish that CBRD-27230 will deliver the forthcoming CBRD-27237 fix:

| Candidate | Observed state | Does it close ticket 05? |
| --- | --- | --- |
| [CBRD-26950 / PR #7695](https://github.com/CUBRID/cubrid/pull/7695) | Open, unmerged; head `c09d6c6d957258f679ecef744b64238c6e2c38b0`, targets `feat/oos`; JIRA Develop, unresolved. | No. Adds page-LSA identity stamps; retains abort-unsafe forward-walk reclamation. |
| [CBRD-27230](http://jira.cubrid.org/browse/CBRD-27230) | Open, unresolved; updated August 14. Planned commit-conditional OOS notification and removal of forward walk, with UPDATE reuse and replication changes. | Related planned redesign, not an available verified patch; no longer the assumed completion dependency. |
| [CBRD-27237](http://jira.cubrid.org/browse/CBRD-27237) | Open, unresolved; updated August 14. Describes deletion of an aborted UPDATE's restored chain. | Exact baseline defect; no indexed fixing PR/commit found. |
| [OOS integration PR #7803](https://github.com/CUBRID/cubrid/pull/7803) | Open, unmerged, not draft according to live metadata; head `52db017fd33ffd042c35558006cce71ad5aa17f5`, targets `develop`. | No. Body lists 27230/27237 as blockers; source still uses forward walk. |
| [History PR #7897](https://github.com/CUBRID/cubrid/pull/7897) | Open, unmerged; head `68c6d0b31322e1cf4eacda03f58ed56be8cdde39`, targets `feat/oos`. | No. History work retains the relevant forward walk. |
| Current `feat/oos` | `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` | Still invokes forward-walk reclamation. |

Search coverage: exact GitHub PR searches for 27230 and 27237 (only #7803 mentioning 27230; none for 27237), indexed commit searches for both (zero matches), broader OOS UPDATE/rollback candidates above, and direct feature-branch source inspection. This is not proof that no unpublished/private work exists. JIRA has an assignee, but an active delivery plan or ETA was not established; no one was contacted.

### Identity is not deletion eligibility

In PR #7695, the [vacuum caller](https://github.com/CUBRID/cubrid/blob/c09d6c6d957258f679ecef744b64238c6e2c38b0/src/query/vacuum.c#L3614) still dispatches to the [forward-walk helper](https://github.com/CUBRID/cubrid/blob/c09d6c6d957258f679ecef744b64238c6e2c38b0/src/query/vacuum_oos.cpp#L268), which extracts old chain references from UPDATE undo data. The [deletion identity check](https://github.com/CUBRID/cubrid/blob/c09d6c6d957258f679ecef744b64238c6e2c38b0/src/storage/oos_file.cpp#L3212) rejects a different chain identity, not a still-required matching identity.

Counterexample: commit value A; UPDATE to B; abort; rollback restores A's original chain reference. The undo reference and restored live reference identify the same A chain. Identity equality therefore permits the problematic deletion. This conclusion is source-based reasoning supported by the existing local reproduction, not a new run against #7695. See the [canonical vocabulary](../../CONTEXT.md) distinction between chain identity and reclamation eligibility.

The latest 26950 design uses an **8-byte page-LSA stamp and 24-byte stub/header**, not the historical 4-byte generation / 20-byte proposal still present in older notes. Its branch diverges from PR7600: comparison reports six commits ahead and two behind, merge base `2940b1cfbc3c2d4d0fac3f9244a960350debd380`. It is not a successor already containing the routing work. Storage format, demotion thresholds, vacuum APIs and replication changes require explicit integration and fresh evidence. Historical context was not silently rewritten.

## Completion path and trade-offs

1. **Freeze routing behavior and preserve the red regression.** Keep ticket 05 blocked and ticket 06 runtime acceptance unmet. Do not replace the independent final route to chase an unproven timing benefit.
2. **Accepted: wait specifically for the CBRD-27237 fix.** The user expects it soon; no exact date or patch revision is established. When available, review its actual mechanism and dependencies rather than assuming the 26950 → 27230 sequence. Resume verification only with the required approval and a concrete abort-safety fix, not merely a related issue-status change. This minimizes duplicate reclamation work and routing scope creep. No automatic monitoring or assignee messaging is authorized by this document.
3. **If delay is unacceptable: separately scoped repair design.** First establish overlap with existing work through authorized coordination, then define the smallest abort-safe repair and its tests. A transaction-finished check is not a commit check. A blanket skip of UPDATE reclamation is not an acceptable fix without addressing leaked chains. Full 27230 includes reuse, notification, replication and recovery obligations; it is not a small routing adjustment. Investigate a narrow commit-eligibility guard against the notification redesign without assuming either is proven or implementable cheaply.
4. **After explicit integration/test approval:** pin exact repaired baseline and candidate revisions with the same lifecycle dependency and build configuration. First demonstrate restored-chain survival and committed obsolete-chain reclamation. Then complete the ticket 05 partitioned SERVER matrix; a green minimal reproduction alone does not close the ticket.
5. **Re-establish ticket 06 evidence.** Use a controlled host and matched builds, retaining existing final routing. A 24-byte format integration affects layout/demotion and invalidates treating previous 16-byte-format measurements as final evidence. Archive old evidence rather than relabeling it. Instruction counts alone cannot satisfy the runtime gate.
6. **Finish ticket 07 only on the integrated revision.** Reconcile all spec obligations and remaining proof gaps; rerun affected checks, review the final delta, and report acceptance only if both lifecycle and performance requirements are satisfied. Commit/push/PR publication remains separately authorized.

## Unresolved proof obligations

- No live or MVCC-required chain can be reclaimed after full abort, statement rollback, savepoint rollback, or recovery of an uncommitted update.
- Committed obsolete chains still become reclaimable after relevant readers finish; an abort fix must not silently turn deletion into permanent leakage.
- Notification/log ordering, atomicity, crash redo/undo, vacuum retries, and slot/page identity protection must compose correctly. Transaction completion alone does not distinguish commit from abort.
- Same-partition and moving UPDATE preserve prior-reader values, destination ownership, restored source values and recovery behavior; replication-facing changes require their own contract evidence.
- Exact integrated code/build provenance must match lifecycle and performance results. Neither upstream pass claims nor existing local partial passes prove the new combination.

These are acceptance obligations and future investigation targets, not claims that the proposed lifecycle design already satisfies them.
