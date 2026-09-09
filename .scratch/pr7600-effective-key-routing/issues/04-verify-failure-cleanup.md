# 04: Prove failure cleanup and unaffected write behavior

**What to build:** Reliable rejection, rollback, and subsequent writes when partitioned preparation fails, preserving buffers, LOB lifecycle, OOS publication state, and unrelated write behavior.

**Blocked by:** 03 — Route UPDATEs and pending increments correctly.

**Status:** resolved

**Parent:** [Effective-key routing specification](../spec.md).

**Execution gate:** Test/failure-injection execution and any scoped repairs require separate implementation authorization. Do not modify the parent spec or broaden scope to unrelated baseline defects.

- [x] Exercise invalid routing, effective-key preparation failure, OOS serialization/class/file lookup failure, partial OOS publication, and final heap/index failure through existing appropriate test seams.
- [x] Reuse existing server publication-failure tests and SQL rollback prior art. Add focused assertions only where the approved seams lack the new behavior; do not create a new general failure-injection framework.
- [x] Show key-only routing makes no persistent writes or publication reset; real OOS preparation retains the paired publication-state reset and failure cleanup contract.
- [x] Verify original cached assignments and reusable routing contexts remain valid after failure; temporary values/buffers are released and no binding points to freed or previous-row data.
- [x] Verify rollback and subsequent valid operations leave no durable partial OOS/heap effects. Buffer release is not evidence that logged storage was undone; inspect stored results and owner-file behavior.
- [x] Cover written/unchanged LOBs, inline/demoted locators, buffer-growth retries, failures during real transformation, and OOS-plus-big-record rejection without duplicate copy/delete behavior.
- [x] Preserve expected single-failure errors. For multiple independent errors, allow the accepted precedence difference while requiring an appropriate error and correct cleanup.
- [x] Preserve nonpartitioned writes, REPLACE, and duplicate-key UPDATE behavior, including the existing OOS-suppressed duplicate probes.
- [x] Distinguish new defects from reproducible baseline failures. Correct only defects within the authorized design scope; report blockers and reopen decisions rather than silently waive a gate.

**Completion evidence:** Per-failure scenario results, transaction/owner observations, subsequent-write checks, and explicit revision/build-mode provenance. Any resulting behavioral changes invalidate affected earlier measurements for final acceptance.

**Spec coverage:** User stories 21, 24–25, 28–33, 36–37; cleanup, publication, error policy, and unchanged-path requirements.

## Comments

- 2026-09-08: User authorized all remaining tickets 04–07, including isolated failure/recovery tests and measurements, scoped repairs, final review, and a local feature commit; no push. Work item 82. Starting existing SERVER_MODE publication checks before extending missing assertions. Shared databases remain out of scope.

## Answer

2026-09-09: [Cleanup report](../../../cbrd-27089/design/ticket04-cleanup-b871ea386-codex.md). Eight injected preparation failures, failed context reuse/publication preservation, scalar codec write/read cleanup, actual payload malloc failure, final index rejection, and LOB copy/delete/retry/external-file lifetime checks pass. All32 SHOW/routing tests and other configured SQL binaries pass. All25 configured binaries were exercised using private fixtures; three path-length startup failures pass with private short socket directories. The only remaining failing binary is the known baseline rollback/vacuum regression, retained for05/07. Two spec-review gaps were closed and re-reviewed; no engine repair or gate waiver.
