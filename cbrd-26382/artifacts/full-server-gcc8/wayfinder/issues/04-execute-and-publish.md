# Execute and Publish the Full-Binary Follow-up

Type: hand
Status: claimed (waiting for stable-PC continuation)
Blocked by: Version Provenance, Rocky 8 Build Reproducibility, SQL and PMU Oracle

## Objective

Build QA-2029 and scope-exit A/B/C, run the accepted SQL and PMU protocols,
analyze final `cub_server` ELF layout including hot functions and `log_Gl`, then
publish the evidence-backed report and verified CBRD-26382 follow-up comment.

## Completion evidence

- Reproducible build manifests and binary hashes for all four states.
- Five-run QA reconstruction plus randomized A/B/C timing samples.
- Correctness, cardinality, and plan checks.
- Final-ELF section/symbol/disassembly/unwind/cache-line analysis.
- PMU counter comparison tied to tested layout hypotheses.
- Committed and pushed `my-cubrid-docs` report URL.
- JIRA comment id and verified comment body containing that URL.

## Answer

Rocky 8/GCC 8/system-JDK-8 builds and the current shared-host 180-sample timing matrix are complete. The normalized build
produced B/A `0.897228` (B 10.28% faster; 60/60 paired rounds), the opposite of the QA report, while C/B was `1.003011`
with a CI crossing 1.0. Final ELF analysis shows B/C query `.text`, hot-function layout, and `log_Gl` layout are identical;
forced `noexcept` changes EH metadata only.

The shared host repeatedly ran 70–150 foreign `cc1plus` processes, inflating 18–20 second samples to 32–37 seconds. Those
runs were gated and excluded, but PMU and the QA-exact build reproduction must move to a stable PC. Handoff commit:
`cdf79d70450cd40504997b03f5433ec6dd443dbd`.

Remaining: QA exact `build.sh build` provenance/package, stable-PC reproduction of the reported slowdown, PMU/profile,
final report, and verified JIRA comment.

[Back to map](../map.md)
