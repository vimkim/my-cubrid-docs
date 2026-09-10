# 06: Verify the complete PR contract and costs

**What to build:** The integrated PR passes the original failing cases and broader relevant checks, with exact-commit CI evidence and measured durable-history costs.

**Blocked by:** 01, 02, 03, 04, 05.

**Status:** ready-for-agent

- [ ] Original cbrd_27064, historical CDC regression cbrd_27075, and bug_bts_4633 pass on the final integrated engine.
- [ ] Run appropriate local builds/tests and the lifecycle, legacy-history, failure-injection and historical-reader matrix; retain interpretable results.
- [ ] Measure supplemental-on/off WAL volume, serialization runtime and memory with representative incompressible OOS workloads.
- [ ] Review implementation against both repository standards and this specification; address findings before final publication.
- [ ] Collect CI for the final engine/testcase commits and analyze every remaining failure without substituting a narrower success criterion.
- [ ] Remove temporary instrumentation, preserve final regression artifacts, document activation/upgrade and actual old-reader enforcement, and leave the work tracker current.

## Context

Part of the confirmed CBRD-26939/PR #6864 contract. Use the feature specification and ADR-0004. User approved the ticket breakdown, dependencies and public test seams on 2026-09-08. See [feature specification](../spec.md).

## Comments

Ticket 01 has a local CCI companion commit `76b293743800620cc521fb818b9567b6ae19cad9`, based on the canonical pinned revision. Publish the companion before publishing an engine commit that references it. The existing nested CCI checkout was preserved; do not stage its unrelated older HEAD as the gitlink.

CDC portion implemented and locally verified at `7d97d4bf6`; companion CCI `268d152` published. Final original CDC regressions pass at testcase `a8d61f27443e3c8b56bcaf94b23a8b88dff9069a`; costs and matrix are in the [CDC report](../../../cbrd-26939/CBRD-26939-durable-cdc-history_68c6d0b_codex.md). Do not close this ticket: JDBC ticket05 and exact-head CI verification remain outstanding.
