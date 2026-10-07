# 03: Separate write verification from SHOW diagnostics

Status: resolved
Blocked by: 01, 02 (final integration verification)

What to build: Separate write verification from SHOW diagnostics while preserving the approved destination-owned OOS behavior.

- [x] Four original SHOW cases remain; all 36 other cases including generic packing are relocated with identical test bodies/assertions.
- [x] Share only statistics/fixture helpers needed by both; preserve the real OOS_DB seam, serial execution and appropriate timeouts.
- [x] Record old-to-new test/filter mapping, compile/install, run both SQL modules and complete the configured suite.
- [x] Final Standards and Spec reviews pass; source and meaningful documentation changes are locally committed; unrelated changes remain untouched.

## Answer

Local source commit `4be72fc20`. Debug configure/build/install passed. Both SQL
modules passed all 40 GoogleTests in four CTest entries (58.90s); the full configured
suite passed 36/36 entries (245.43s). Original test bodies are byte-identical.
Independent Standards and Spec reviews each found zero issues. Evidence and
documentation are committed with this resolved task; original CCI/JDBC changes
remain untouched. See the [verification record](../../../cbrd-27089/design/review-simplification.md).
