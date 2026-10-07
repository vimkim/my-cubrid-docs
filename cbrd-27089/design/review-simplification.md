# PR7927 review simplification

Work-tracker 293; user selected all three architecture candidates on 2026-10-07.
The [approved design](no-record-type-design.md) remains the contract; see the
[new task spec](../../.scratch/pr7927-review-simplification/spec.md) and
[three-task map](../../.scratch/pr7927-review-simplification/map.md).

## Changes

The OOS finalizer now keeps each retained payload span, insertion result and
current-view patch location together. It builds the contiguous insertion batch
only after collection finishes, so result pointers cannot be invalidated by
collection growth. The batch adapter remains required by existing physical OOS
insertion. Every insertion must succeed before any stub is patched. This drops
one separate bookkeeping allocation; it adds no row or payload copy.

A private stub decoder serves the existing public Resolve interface and the
finalizer after bounded field location. Disk decoding reads the already-checked
stub directly instead of locating and parsing it again. The disk-only parser
keeps its existing corruption-output contract. The key-size probe's preliminary
check remains because it silently filters malformed fields before the error-
reporting decoder; deleting it would alter error behavior.

INSERT and nonmoving UPDATE share locator adaptation, owner selection and
finalization after destination routing. Received owners and converted descriptor
views still live in their enclosing calls. Moving UPDATE still forwards its
owner to destination INSERT. No owner is retained in caches or shared RECDES.

The SHOW diagnostics module shrinks from 2052 to 274 lines and retains its four
original cases. A focused deferred-write SQL module contains the 35 write fixture
cases and the generic packing case. Shared helpers provide only table cleanup,
SHOW column identities, integer observations and result positioning used by both;
large-integer and NULL observations remain local to diagnostics. This improves
review locality rather than reducing the amount of required verification.

## Verification

Starting source: `6b53181d31d6d6d2615b18b4f914623bb017d7c4`.
PR integration baseline: `fb567a629cdb390fff920542173fa36f454c74a0`.
Final source revision: `4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c`.
The three local commits are `ae36758cc` (finalizer), `b039873fd` (locator handoff)
and `4be72fc20` (test organization). The [evidence manifest](review-simplification-evidence/manifest.json)
pins source revisions, verdicts, file sizes and SHA-256 hashes.

- Finalizer debug build/install: pass; four selected ownership/publication/failure
  GoogleTests pass, with three CTest entries including setup/cleanup (36.39s).
- Locator debug build/install: pass; seven selected routing/movement/loader-owner/
  failure GoogleTests pass, with three CTest entries including setup/cleanup (7.88s).
- [Relocation](review-simplification-evidence/test-relocation.json): all 40 original
  test bodies match byte for byte; four diagnostics retain their identities,
  35 write cases map from `OosSqlShow` to
  `OosSqlDeferredWrite`, and `OosSqlPacking` keeps its identity.
- Both SQL modules pass: four diagnostic and 36 relocated GoogleTests, four CTest
  entries including setup/cleanup (58.90s).
- [Registration](review-simplification-evidence/ctest-registration.json): new SQL
  module uses `OOS_DB`, `RUN_SERIAL`, 180s; diagnostics return to the existing
  30s timeout. Historical SHOW filters remain historical.
- [Final configured debug suite](review-simplification-evidence/final-ctest.log):
  36/36 CTest entries pass (245.43s), including the database fixture lifecycle.
- [Independent two-axis review](review-simplification-review.md): Standards 0,
  Spec 0. The Spec reviewer independently reproduced the 40-body comparison.
- [Source contract](review-simplification-evidence/source-contract.json): shared
  storage/descriptor files equal the PR baseline; the removed record marker is
  absent from source and tests. Original CCI/JDBC changes remain untouched.

The initial architecture count of 39 covered fixture cases only. Complete
relocation accounting includes the separate generic packing case: 40 total.
Historical build/test and reviewer evidence remains unchanged.

The final debug build used the worktree's `debug_gcc` preset, then installed it.
Equivalent CMake commands are `cmake --preset debug_gcc`,
`cmake --build build_preset_debug_gcc --parallel`, and
`cmake --install build_preset_debug_gcc`. The raw configure/build logs retain the
actual preset environment. Both SQL modules were selected with
`ctest --test-dir build_preset_debug_gcc --output-on-failure --verbose -R '^test_oos_sql_(show|deferred_write)$'`;
the final suite omitted `-R`. CTest provided setup/cleanup in both runs.
The focused pre-relocation filters are recorded in their logs and map through
the relocation record above.

## Scope

These are refinements of the completed no-record-type implementation. Destination
ownership, compact allocation reuse, 24-byte in-place finalization, payload lifetime,
validated owner-local indices and logical storage/export protections remain.
Shared RECDES and persisted formats remain unchanged. Fresh-chain UPDATE,
MVCC/vacuum ownership, replication grouping, legacy eager serialization and
loader latch ordering retain their approved behavior. No benchmark, assertions-
disabled rerun, real server-loader rerun, company CI or remote publication is
claimed for this follow-up; earlier results remain pinned historical evidence.
