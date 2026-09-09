# 03: Route UPDATEs and pending increments correctly

**What to build:** Same-partition and partition-moving updates through effective-key routing, including unchanged keys and pending INCR/DECR, with exactly-once real mutations and new OOS values owned by the destination heap.

**Blocked by:** 02 — Route partitioned INSERTs without a full-row probe.

**Status:** resolved — work-tracker 77, codex-pr7600-ticket03

**Parent:** [Effective-key routing specification](../spec.md).

**Execution gate:** Engine work, test execution, experiments, commits, and pushes await separate authorization. Completion is a functional milestone, not final acceptance before tickets 04–07.

The user authorized implementation and scoped testing of ticket 03 only on 2026-09-08. No later tickets, commits, or pushes are authorized by this request.

- [x] Add failing behavioral cases first for unchanged-key updates, ordinary arithmetic key changes, and dedicated pending INCR/DECR; verify both row values and destination ownership after implementation.
- [x] Read an uninitialized key from the old record supplied by the existing write path, using its representation and missing-attribute default rules; do not substitute another version or reevaluate upstream defaults.
- [x] Apply a pending increment to the temporary key only; leave the actual pending assignment intact for the real first-pass transformer. Cover supported integer widths, boundary crossings, overflow/underflow-to-zero behavior, and retries without double or skipped real increments.
- [x] Preserve complete legal-key type/expression support for UPDATE, including string-domain behavior and old OOS-backed key values; no silent fallback to the full inline probe.
- [x] Retain original cache identity, downstream root/child discovery, representation patching, locking, scan caches, index handling, and cross-partition row movement. Assert early/final destination agreement through observable results or the approved routing seam.
- [x] Preserve global LOB preparation and copy/delete state through written and unchanged LOB updates. Key-only preparation must not trigger that lifecycle.
- [x] Verify new OOS values follow the destination heap for moved updates and remain associated with the same heap for unmoved updates. Do not introduce cross-version OOS-chain reuse or prematurely remove old values.
- [x] Preserve ordinary nonpartitioned updates and reuse of routing contexts; keep separate duplicate-key probe behavior intact.
- [x] Record semantic coverage and remaining failure/server/measurement gates explicitly. Do not claim SA-only success proves concurrent-reader, recovery, or vacuum behavior.

**Completion evidence:** INSERT/UPDATE candidate path complete across legal keys, exactly-once mutation results, old/default representation coverage, moved-row ownership checks, and continued baseline behavior on unaffected paths.

**Spec coverage:** User stories 15–21, 23, 28–30, 36–37; old-value, increment, LOB-locality, and movement contracts.

## Answer

Implemented effective-key UPDATE routing and destination-owned first-pass transformation; preserved final record routing with an agreement guard. Fixed a context-owned stale-key assumption exposed by duplicate-key UPDATE (also present for REPLACE in the frozen ticket-02 INSERT adapter) without changing the independent duplicate probes.

[Implementation, source evidence, test results, and limitations](../../../cbrd-27089/design/ticket03-update-routing-b871ea386-codex.md).

Verification: 72/72 selected SA tests; all 13 key types; old OOS/schema/default cases; LOB movement/readback/rollback; all three integer widths and limit behavior; debugger-forced INT INCR/DECR retries after the first real mutation; independent SQL equivalence. No server lifecycle, broad fault-cleanup, or performance acceptance is claimed. Parent spec remains unchanged; tickets 04–07 are unstarted. No commits or pushes.

## Comments

- 2026-09-08: User authorized implementation of ticket 03 only, then requested continuation. Work 77 claimed and completed by codex-pr7600-ticket03.
- Failed tests, the frozen ticket-02 REPLACE failure, and the corrected compressed-key test expectation remain recorded in the evidence report; no failure was silently discarded.
