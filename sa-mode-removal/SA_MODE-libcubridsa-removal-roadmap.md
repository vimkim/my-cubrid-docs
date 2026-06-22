# SA_MODE & libcubridsa Removal Roadmap

Date: 2026-06-22

## Executive Summary

This roadmap proposes removing `SA_MODE` as a compile-time mode and eventually removing the `libcubridsa` build artifact. The goal is not to remove administrative workflows. The goal is to eliminate a third engine-management axis that increases maintenance cost, test matrix size, and behavioral divergence from `SERVER_MODE`/`CS_MODE`.

The user-facing `-S`/`--SA-mode` option can remain during migration as a compatibility surface. Internally, workflows should move to non-`SA_MODE` execution paths. For throughput-sensitive administrative workflows, replacement paths must complete within `1.2x` of current SA-mode elapsed time under comparable conditions.

## Problem Statement

CUBRID currently has three major compile-time execution modes:

| Mode | Role |
|------|------|
| `SERVER_MODE` | Server process execution |
| `CS_MODE` | Client-side execution that connects to server |
| `SA_MODE` | Standalone in-process execution for selected admin/client workflows |

`SA_MODE` creates a separate build and behavior surface:

- code guarded by `#if defined(SA_MODE)` or `SERVER_MODE || SA_MODE`
- separate `sa/CMakeLists.txt` source lists
- standalone utility linkage through `libcubridsa`
- behavior differences in boot, transaction, locking, loading, storage, and utility code
- additional CI/build/test coverage burden

A local source scan in the current develop tree found roughly 400+ `SA_MODE` conditional references across 140+ files. This is enough to treat `SA_MODE` as a significant maintenance axis, not a small compatibility flag.

## Key Terms

| Term | Meaning |
|------|---------|
| Fast admin operation | An admin workflow that must stay practically fast for database maintenance. |
| Offline admin operation | A workflow that genuinely requires direct database-file access without a running or temporary server. This must be justified per command. |
| Standalone option | The `-S`/`--SA-mode` CLI compatibility surface. It does not by itself prove offline execution is required. |
| SA_MODE removal | Removing `SA_MODE` as a compile-time macro and build-management axis. |
| libcubridsa removal | Removing the standalone library/build target after utilities no longer depend on it. |

## Non-Goals

- Do not remove admin utilities such as `loaddb`, `unloaddb`, `compactdb`, `checkdb`, `backupdb`, or `vacuumdb`.
- Do not immediately break scripts that pass `-S`/`--SA-mode`.
- Do not assume all `-S` workflows require true offline execution.
- Do not claim SA mode has no MVCC. Some runtime paths differ, but MVCC code is still compiled into broad SA-related storage/transaction paths.
- Do not remove safety requirements for recovery, repair, backup, TDE, or direct file operations.

## Current SA-Exposed Admin Surface

The current utility option surface exposes `SA-mode` and `CS-mode` choices for many commands. Known candidates include:

| Workflow | Current SA exposure | Initial classification |
|----------|---------------------|------------------------|
| `loaddb` | `-S`/`--SA-mode`, `-C`/`--CS-mode`; separate SA/server load paths | First migration pilot |
| `unloaddb` | `-S`/`--SA-mode`, `-C`/`--CS-mode` | Throughput-sensitive |
| index build during load | triggered from load index file path | Part of `loaddb` pilot |
| `compactdb` | `-S`/`--SA-mode`, `-C`/`--CS-mode` | Throughput/safety mixed |
| `vacuumdb` | `-S`/`--SA-mode`, `-C`/`--CS-mode` | Maintenance-sensitive |
| `checkdb` | `-S`/`--SA-mode`, `-C`/`--CS-mode` | Safety/correctness first |
| `backupdb` | `-S`/`--SA-mode`, `-C`/`--CS-mode` | Safety/failure recovery first |
| `addvoldb`/`delvoldb` | `-S`/`--SA-mode`, `-C`/`--CS-mode` | Safety/failure recovery first |
| `spacedb` | `-S`/`--SA-mode`, `-C`/`--CS-mode` | Likely easy CS-compatible candidate |
| `cleanfiledb` | `-S`/`--SA-mode`, `-C`/`--CS-mode` | Requires offline/safety review |
| `csql` | `-S`/`--SA-mode`, `-C`/`--CS-mode` | Compatibility-sensitive |
| `paramdump` | `-S`/`--SA-mode`, `-C`/`--CS-mode` | Likely easy CS-compatible candidate |
| TDE utility | `-S`/`--SA-mode`, hidden/explicit CS path | Security/safety review |

This inventory must be completed before deleting the build target.

## Compatibility Policy

`-S`/`--SA-mode` should be treated as a compatibility option, not as a permanent implementation contract.

During migration:

1. Continue accepting `-S` where existing scripts may depend on it.
2. Route `-S` to a non-`SA_MODE` implementation where possible.
3. Emit a deprecation warning once behavior is stable:

   ```text
   --SA-mode is deprecated and now uses the server-backed admin path.
   ```

4. Preserve true offline behavior only for commands where it is proven necessary.
5. Remove or hide `-S` only after release-note coverage and compatibility period.

## Performance Gate

For throughput-sensitive workflows, replacement paths must satisfy:

```text
replacement_elapsed_time <= current_SA_elapsed_time * 1.2
```

This gate applies to:

- `loaddb`
- `unloaddb`
- index creation during load
- `compactdb`
- vacuum-like maintenance workloads where elapsed time is the main admin concern

This gate does not override correctness or recovery safety. For `checkdb`, repair-like operations, backup, TDE, volume changes, and recovery-adjacent utilities, correctness, exclusive access, and failure behavior are stronger acceptance criteria than raw speed.

Measurements must include total user-visible elapsed time, including startup/connect/setup costs.

## Pilot: loaddb

`loaddb` should be the first migration candidate.

Reasons:

- It is a high-value admin workflow.
- It is performance-sensitive.
- It already has standalone and server loading concepts.
- It includes object loading and index creation, both important for evaluating whether non-SA paths can replace SA paths.
- It gives a concrete acceptance test before attempting broader removal.

### loaddb Acceptance Criteria

Functional:

- schema load behavior remains compatible
- object load result is equivalent
- index file execution remains compatible
- error reporting remains close enough for scripts and operators
- interrupted load recovery behavior is documented and tested
- resulting database passes consistency checks

Performance:

- total elapsed time is `<= SA * 1.2`
- object loading phase is measured separately
- index creation phase is measured separately
- peak memory and log volume are recorded

Benchmark datasets:

| Dataset | Purpose |
|---------|---------|
| Small | Captures startup/setup overhead and script compatibility |
| Medium | Represents normal admin load workflow |
| Large | Exposes throughput, memory, logging, and index build behavior |

## Migration Phases

### Phase 0: Inventory and Baseline

Deliverables:

- complete list of `SA_MODE` macro sites
- complete list of `libcubridsa` consumers
- utility-by-utility behavior classification
- baseline benchmark results for current SA mode and CS mode

Classification buckets:

| Bucket | Meaning |
|--------|---------|
| CS-compatible | Can directly use existing CS/server path |
| Needs server optimization | Can use server path but must be optimized to meet `SA * 1.2` |
| Needs offline review | May require direct file access or exclusive offline semantics |
| Obsolete/deprecate | Existing SA behavior can be removed or folded into another workflow |

### Phase 1: loaddb Pilot

Deliverables:

- make `loaddb -S` executable without `SA_MODE`-specific behavior, or provide a compatibility alias to non-SA path
- benchmark small/medium/large datasets
- close the gap until total elapsed time is `<= SA * 1.2`
- document behavior differences
- add CI/regression coverage for the replacement path

Exit criteria:

- `loaddb` no longer requires `SA_MODE`
- performance gate passes
- resulting DB consistency is verified

### Phase 2: Low-Risk Utility Migration

Likely candidates:

- `paramdump`
- `spacedb`
- read-only `csql` use cases
- `unloaddb` if CS path already satisfies the performance gate

Deliverables:

- remove utility-level `SA_MODE` branches where behavior maps cleanly to CS/server paths
- preserve `-S` as compatibility alias
- add targeted tests for option compatibility and output compatibility

Exit criteria:

- low-risk utilities no longer need `libcubridsa`
- no meaningful behavior drift from previous `-S` usage

### Phase 3: Throughput-Sensitive Maintenance

Candidates:

- `unloaddb`
- `compactdb`
- manual/startup vacuum-related workflows
- index build paths outside the initial `loaddb` pilot

Deliverables:

- benchmark each workflow against current SA baseline
- optimize server/client paths where needed
- preserve exclusive/safe execution semantics where required
- document any intentional behavior changes

Exit criteria:

- each migrated workflow is within `SA * 1.2`, or has an explicit exception approved for safety/correctness reasons

### Phase 4: Safety-Critical and Offline Review

Candidates:

- `checkdb`
- repair-like checks
- `backupdb`
- `addvoldb`/`delvoldb`
- `cleanfiledb`
- TDE key operations
- restore/recovery-adjacent operations, if any depend on SA linkage

Deliverables:

- identify which operations genuinely require offline access
- define replacement semantics for exclusive access
- verify failure atomicity and recovery behavior
- decide whether any small non-SA offline helper is needed

Exit criteria:

- no safety-critical workflow depends on broad `SA_MODE`
- any remaining offline requirement is narrow, explicit, and not implemented as a full third engine mode

### Phase 5: Remove SA_MODE Macro

Deliverables:

- delete obsolete `#if defined(SA_MODE)` branches
- simplify `SERVER_MODE || SA_MODE` checks
- update headers that currently require one of `SERVER_MODE` or `SA_MODE`
- remove SA-specific boot/transaction/storage/client special cases
- keep compatibility option parsing as needed, but without compiling an SA engine variant

Exit criteria:

- source builds without defining `SA_MODE`
- all migrated utility tests pass
- CI no longer needs an SA-mode build variant

### Phase 6: Remove libcubridsa Build Target

Deliverables:

- remove `sa/CMakeLists.txt` target linkage for `libcubridsa`
- move remaining utility targets to appropriate CS/server-backed targets
- remove duplicated source lists that existed only for SA builds
- update packaging/install scripts
- update documentation and release notes

Exit criteria:

- no binary links against `libcubridsa`
- no build configuration defines `SA_MODE`
- user-facing admin workflows have documented replacement behavior

## Test Strategy

### Build Tests

- normal server build
- client utility build
- package build
- no remaining `SA_MODE` compile definitions
- no accidental references to removed SA-only symbols

### Functional Tests

For each migrated utility:

- option parsing compatibility
- `-S` compatibility behavior
- output format compatibility where scripts may parse output
- error behavior for common failure cases
- interruption/cancel behavior
- DB consistency after successful completion
- DB consistency after failure/interruption where relevant

### Performance Tests

For each throughput-sensitive workflow:

- current SA baseline
- current CS/server baseline
- replacement path benchmark
- small/medium/large datasets
- elapsed time
- CPU
- peak memory
- I/O volume
- log volume

### Safety Tests

For safety-critical workflows:

- server already running
- server not running
- exclusive access required
- permission failure
- disk full
- interrupted process
- crash/restart recovery
- encrypted database/TDE cases where applicable

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Replacement path is slower than `SA * 1.2` | Admin workflows regress | Pilot with `loaddb`; optimize before broad removal |
| `-S` scripts break | User compatibility issue | Keep option as alias during migration |
| Offline semantics are accidentally removed | Data safety issue | Require per-command offline review |
| Safety-critical operations change failure behavior | Recovery/data risk | Treat safety workflows separately from throughput workflows |
| Hidden `libcubridsa` dependency remains | Build removal blocked | Phase 0 consumer inventory |
| Tests miss behavior drift | Regression risk | Add utility-level compatibility and failure tests |

## Decision Points

1. Is `loaddb` accepted as the pilot workflow?
2. Which benchmark datasets are representative enough for the `SA * 1.2` gate?
3. Which commands truly require offline execution?
4. How long should `-S` remain as a compatibility alias?
5. Are any workflows allowed to exceed `SA * 1.2` for safety/correctness reasons?
6. Is a narrow offline helper acceptable if broad `SA_MODE` is removed?

## Proposed Review Milestones

| Milestone | Review Output |
|-----------|---------------|
| M0: Inventory complete | list of SA sites, utility consumers, risk classification |
| M1: loaddb pilot complete | benchmark report and compatibility notes |
| M2: low-risk utilities migrated | tests and option compatibility report |
| M3: throughput workflows migrated | performance report against `SA * 1.2` |
| M4: safety workflows reviewed | offline/safety decision record |
| M5: `SA_MODE` removed | source/build simplification report |
| M6: `libcubridsa` removed | packaging and release-note update |

## Recommended First Actions

1. Generate an authoritative `SA_MODE` reference list from the current develop branch.
2. Generate a `libcubridsa` consumer list from CMake targets and installed binaries.
3. Build a `loaddb` benchmark fixture with small/medium/large datasets.
4. Compare current SA and CS/server load paths.
5. Decide whether `loaddb -S` can become a compatibility alias for the non-SA path.
6. Start deleting `SA_MODE` branches only after the pilot passes the performance and compatibility gate.
