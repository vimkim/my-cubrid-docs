# CBRD-26382 GCC 8 Full-Binary Follow-up

## Destination

Produce a source-reproducible Rocky Linux 8/GCC 8 experiment that separates the
reported QA version delta from the causal effect of PR #6636, decides whether
forced destructor `noexcept` changes the SQL latency through final-binary layout,
and publishes the evidence in `my-cubrid-docs` and CBRD-26382.

## Confirmed decisions

- Build matrix: `QA-2029` (`000a465c8`), `scope-exit-A` (`6146cdb6a`),
  `scope-exit-B` (`8fd3ca03e`), and `scope-exit-C` (B plus destructor-only
  forced `noexcept`).
- Attribution: `QA-2029` versus B reconstructs the reported version delta;
  A versus B isolates PR #6636; B versus C isolates the destructor exception
  specification.
- Build normalization: identical Rocky Linux 8/GCC 8.5 toolchain, `/src` and
  `/out` container paths, sequential clean builds, no shared compiler cache.
- Measurement: preserve the five-run trace-off QA view and add randomized,
  CPU-pinned repeated measurements with PMU counters.
- Publication: create a new report commit and add a new verified JIRA comment;
  preserve the earlier exploratory report and comment.

## Route

1. [Version Provenance](issues/01-version-provenance.md) — resolved research.
2. [Rocky 8 Build Reproducibility](issues/02-rocky8-build-reproducibility.md) — resolved research.
3. [SQL and PMU Oracle](issues/03-sql-pmu-oracle.md) — resolved research.
4. [Execute and Publish the Full-Binary Follow-up](issues/04-execute-and-publish.md) — claimed hand ticket; transferred to a stable PC.

The three research blockers are resolved. The execution ticket is the only
non-research ticket and carries the accepted plan through publication. A portable handoff and compact evidence bundle were
published at `cdf79d70450cd40504997b03f5433ec6dd443dbd`; work is waiting for the stable-PC reproduction.

## Evidence contract

- Every build records source SHA, submodule SHAs, patch digest, compiler and
  linker versions, flags, build ID, and hashes of analyzed binaries.
- Correctness requires identical `db_class` cardinality, result, and plan
  topology before latency comparisons are interpreted.
- A regression or improvement requires at least a 5% median effect with a
  paired bootstrap confidence interval excluding 1.0, low within-variant
  dispersion, and consistent direction across independent series.
- Binary-layout claims must be backed by final `cub_server` ELF section,
  symbol, disassembly, unwind metadata, and cache-line-offset evidence.
- Cache claims must be backed by PMU counters. Address movement alone proves
  layout change, not a cache-miss mechanism.

## Notes

This Wayfinder effort explicitly carries execution beyond planning because the
user requested builds, measurements, report publication, push, and JIRA update.
The historical worktrees do not contain the personal `justfile` environment;
the controlled container build therefore uses the repository's historical
`build.sh` while preserving the exact requested GCC 8 toolchain.
