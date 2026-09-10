# PR #7600 — Spec review

Reviewed 2026-09-09 at `988a4d2fa258222aef792a2a6afde9641b8c5228`, against base `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`, including the uncommitted vacuum test. The effective-key specification and accepted ADR supersede the older two-pass implementation description in the PR/JIRA. Exact local specification and historical evidence snapshots are retained in [specification-snapshots.json](evidence/specification-snapshots.json).

**Three unmet acceptance gates; no newly confirmed routing regression or scope creep.**

1. **Server lifecycle acceptance remains incomplete.** Specification line 91 requires “server-mode coverage for concurrent old-version readers, moved-update rollback, and OOS lifecycle interactions with vacuum/recovery.” Ticket 05 remains blocked. The uncommitted test directly inserts chains and calls heap update; it does not exercise partition routing or destination ownership. Its fresh run fails after successful pre-vacuum readback and a successful committed-delete progress witness: the original OOS read returns `-2`. This is consistent with the previously recorded baseline CBRD-27237 failure. It must not be reported as a newly introduced routing defect. The user directed that a failing test be skipped for commit.

2. **The performance acceptance gate remains unmet.** Specification line 95 says: “Inconclusive measurements do not prove the gate passed.” The saved 52-run interleaved report explicitly remains inconclusive. Allocation/copy savings and passing logical checks do not establish absence of control-workload regressions. Retaining final routing follows the accepted ADR and is not scope creep. No fresh benchmark was run in this review.

3. **Final integrated acceptance is not demonstrated.** Specification line 79 requires complete key coverage, semantic equivalence, cleanup, and useful measured savings. Ticket 07 requires evidence reconciled to the integrated revision. Freshly rebuilding merged HEAD and passing all 32 SQL tests improves the evidence, but does not close the server, recovery, failure-matrix, and performance obligations. Historical `b871ea386`/`213ce80f5` evidence is not an integrated acceptance result.

Independent source tracing found no additional demonstrable implementation defect. The key helper owns its temporary value, reads defaults/old representations, applies increments to the copy, and uses the existing scalar codec. Routing clears stable context slots, retains explicit-partition validation and final destination agreement checks, and keeps source identity separate from OOS ownership. A suspected MVCC reevaluation conflict was rejected: this optimized path supplies `old_recdes`, while the reevaluation branch requires `oldrecdes == NULL`.

These are acceptance limitations, not three newly introduced engine bugs. See [verification](verification.md) for execution scope and dependency provenance.
