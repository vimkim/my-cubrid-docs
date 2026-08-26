# Context: CBRD-26382 GCC 8 Full-Binary Follow-up

## Glossary

### QA-2029 reference

The source commit `000a465c8`, mapped to `11.5.0.2029` by CUBRID's build-number
algorithm. It is the best available source reconstruction of the QA baseline,
not an archived QA package with a preserved manifest.

### scope-exit-A

Commit `6146cdb6a`, version `11.5.0.2030`, the direct first parent of PR #6636.
It contains the original `std::function`-based `scope_exit` implementation.

### scope-exit-B

Commit `8fd3ca03e`, version `11.5.0.2031`, containing PR #6636 with conditional
exception specifications.

### scope-exit-C

The scope-exit-B tree plus one uncommitted, digest-recorded experiment patch
that changes only the destructor to unconditional `noexcept`. Keeping B's HEAD
avoids adding a new commit/version string as a binary-layout confounder.

### QA reconstruction comparison

`QA-2029` versus scope-exit-B. This matches the reported numeric versions but
contains both CBRD-26266 and CBRD-26382, so it cannot attribute the delta to the
scope-exit refactor alone.

### PR attribution comparison

scope-exit-A versus scope-exit-B. These are adjacent commits and isolate the
two files changed by PR #6636.

### noexcept attribution comparison

scope-exit-B versus scope-exit-C. Source, version metadata, and build conditions
are held constant except for the destructor exception specification.

### Unlucky binary layout

A build-wide performance effect where semantically cold metadata changes shift
hot code or globals into a more or less favorable alignment, cache set, branch
placement, or translation-page position. It is a hypothesis until final-binary
addresses and relevant hardware counters move coherently with latency.

### `log_Gl`

The global log-manager state whose final address, size, alignment, neighboring
symbols, page offset, and cache-line occupancy are inspected. A stable source
definition does not imply a stable final ELF address.

## Invariants

- Use the same historical submodule pins for all adjacent A/B/C builds.
- Mount every source tree at `/src` and every output root at `/out`.
- Do not share ccache state across variants.
- Preserve unstripped binaries before any packaging or stripping.
- Never infer causality from one five-run mean or from symbol movement alone.

