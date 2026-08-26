# Execute and Publish the Full-Binary Follow-up

Type: task
Status: resolved
Assignee: codex-stable-pc
Blocked by: Version Provenance, Build Reproducibility, SQL and PMU Oracle

## Objective

Build QA-2029 and scope-exit A/B/C, run the accepted SQL and PMU protocols,
analyze final installed server ELF layout including the `libcubrid.so` hot functions and `log_Gl`, then
publish the evidence-backed report and verified CBRD-26382 follow-up comment.

## Completion evidence

- Reproducible build manifests and binary hashes for all four states.
- QA/B directional reconstruction plus ordered/reversed A/B/C timing samples.
- Correctness, cardinality, and plan checks.
- Final-ELF section/symbol/disassembly/unwind/cache-line analysis.
- PMU counter comparison tied to tested layout hypotheses.
- Committed and pushed `my-cubrid-docs` report URL.
- JIRA comment id and verified comment body containing that URL.

## Answer

The stable-PC execution is complete. QA-2029/A/B/C were built sequentially with the current
`cubridci/cubridci:develop` CentOS 6.10 image and devtoolset-8 GCC 8.3.1, using an explicit repository
`./build.sh -m release ... build`. All four CMake caches prove `RelWithDebInfo`, `-O2 -g -DNDEBUG`; the resulting binaries
were run on Rocky Linux 8.10. The mutable image tag and missing historical QA package mean byte identity with the original
QA binaries is not claimed.

QA-2029 and B have 20 accepted samples each. B is `+1.464%` slower by mean with a 100,000-bootstrap 95% CI of
`+1.039%` to `+1.899%`. This reproduces the QA direction, but not the original `+10.56%` magnitude and not the Wayfinder's
predeclared 5% causal-effect gate. The workload produced zero physical read bytes and zero major faults in all 40 I/O
matrix runs; elapsed time versus server migration has only `r=0.085` correlation.

A→B changes the query hot-function phase by 16 bytes. Expanded A/B central PMU groups (5 repetitions) show IPC `-1.519%`,
MITE uops/query `+12.664%`, and a changed DSB/MITE supply path. Top-down L1/L2 prevents over-attribution: front-end bound
falls from `5.73%` to `3.85%`, while core bound rises from `10.58%` to `13.48%`. The slowdown is therefore a final-layout
pipeline-balance effect whose last hardware-resource link remains open, not a proven DSB-miss-only mechanism. The profile
confirms that the workload spends its cycles in the shifted query executor and scan functions. B/C have identical hot
addresses and bytes; forced destructor `noexcept` does not improve timing consistently, and `log_Gl` remains B/C-identical.

Compact evidence is under [`stable-pc-cubridci/`](../../stable-pc-cubridci/). The report and evidence were pushed in
[`afe5f11`](https://github.com/vimkim/my-cubrid-docs/commit/afe5f11), and the retained, post-publication-verified JIRA
comment is
[`4776011`](http://jira.cubrid.org/browse/CBRD-26382?focusedCommentId=4776011&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-4776011).
The follow-up explanation in
[`1e2631f`](https://github.com/vimkim/my-cubrid-docs/commit/1e2631f) adds the exact 7-byte→8-byte→16-byte link chain,
expanded 110-run PMU/Top-down evidence, and an SVG. JIRA comment `4776011` was updated in place and re-fetched to verify
the new summary and immutable document URL:
[`CBRD-26382-scope-exit-frontend-causal-chain_codex.md`](../../../../CBRD-26382-scope-exit-frontend-causal-chain_codex.md).

[Back to map](../map.md)
