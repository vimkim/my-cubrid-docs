# CBRD-26382 GCC 8 Full-Binary Follow-up

## Destination

Produce a source-reproducible QA-CI-family GCC 8 build and Rocky Linux 8 runtime experiment that separates the
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
- Build normalization: identical current `cubridci/cubridci:develop` CentOS 6.10/devtoolset-8 GCC 8.3.1 image,
  explicit release/`RelWithDebInfo`, `/src` and `/out` container paths, sequential clean builds, and disabled compiler
  cache. The mutable tag is fully resolved and recorded; equivalence to the unavailable historical image is not assumed.
- Measurement: preserve the five-run trace-off QA view and add repeated measurements with PMU counters. Because QA did
  not pin one CPU, server and client migrate freely inside the stable host's P-core set rather than using a single-CPU
  pinned matrix.
- Publication: create a new report commit and add a new verified JIRA comment;
  preserve the earlier exploratory report and comment.

## Route

1. [Version Provenance](issues/01-version-provenance.md) — resolved research.
2. [Rocky 8 Build Reproducibility](issues/02-rocky8-build-reproducibility.md) — resolved research.
3. [SQL and PMU Oracle](issues/03-sql-pmu-oracle.md) — resolved research.
4. [Execute and Publish the Full-Binary Follow-up](issues/04-execute-and-publish.md) — resolved; report and verified
   JIRA comment published.

The three research blockers are resolved. The execution ticket carries the accepted plan through publication. The stable
PC rebuilt all four states in the QA CI-family CentOS 6/devtoolset-8 environment, ran them on Rocky 8, and completed timing,
plan, I/O, scheduler, PMU, profile, and final-ELF analysis. Its directional effect is below the predeclared 5% magnitude
gate, so the report explicitly distinguishes directional reproduction from reproduction of the full QA magnitude.
The committed report is at `afe5f11`, and the verified CBRD-26382 follow-up is comment `4776011`.

## Evidence contract

- Every build records source SHA, submodule SHAs, patch digest, compiler and
  linker versions, flags, build ID, and hashes of analyzed binaries.
- Correctness requires identical `db_class` cardinality, result, and plan
  topology before latency comparisons are interpreted.
- A causal regression or improvement claim requires at least a 5% median effect with a
  paired bootstrap confidence interval excluding 1.0, low within-variant
  dispersion, and consistent direction across independent series.
- Binary-layout claims must be backed by final installed server ELF section,
  symbol, disassembly, unwind metadata, and cache-line-offset evidence.
- Cache claims must be backed by PMU counters. Address movement alone proves
  layout change, not a cache-miss mechanism.

The stable-PC B/QA effect has a confidence interval excluding 1.0 but is only `+1.464%` by mean, so it does not satisfy the
5% magnitude clause. It is reported as a statistically separated directional reproduction. Expanded Top-down evidence
shows the lost slots are core-bound rather than front-end-bound, so the final-link/pipeline-layout class is the leading
explanation while the exact microarchitectural resource and the entire `+10.56%` QA effect remain unproved.

## Notes

This Wayfinder effort explicitly carries execution beyond planning because the
user requested builds, measurements, report publication, push, and JIRA update.
The historical worktrees do not contain the personal `justfile` environment;
the controlled container build therefore uses the repository's historical
`build.sh` while preserving the exact requested GCC 8 toolchain.
