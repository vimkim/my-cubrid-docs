# 06: Verify the complete PR contract and costs

**What to build:** The integrated PR passes the original failing cases and broader relevant checks, with exact-commit CI evidence and measured durable-history costs.

**Blocked by:** 01, 02, 03, 04, 05.

**Status:** draft-for-review

- [ ] Original cbrd_27064, historical CDC regression cbrd_27075, and bug_bts_4633 pass on the final integrated engine.
- [ ] Run appropriate local builds/tests and the lifecycle, legacy-history, failure-injection and historical-reader matrix; retain interpretable results.
- [ ] Measure supplemental-on/off WAL volume, serialization runtime and memory with representative incompressible OOS workloads.
- [ ] Review implementation against both repository standards and this specification; address findings before final publication.
- [ ] Collect CI for the final engine/testcase commits and analyze every remaining failure without substituting a narrower success criterion.
- [ ] Remove temporary instrumentation, preserve final regression artifacts, document activation/upgrade and actual old-reader enforcement, and leave the work tracker current.

## Context

Part of the confirmed CBRD-26939/PR #6864 contract. Use the feature specification and ADR-0004. This draft is not a published ready-for-agent ticket until the proposed seams and breakdown are reviewed.
