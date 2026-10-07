# PR7927 simplification code review

Reviewed source `4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c` against the fixed
starting point `6b53181d31d6d6d2615b18b4f914623bb017d7c4`.
Command: `git diff 6b53181d31d6d6d2615b18b4f914623bb017d7c4...HEAD`.
Commits: `ae36758cc`, `b039873fd`, `4be72fc20`.

The [refinement spec](../../.scratch/pr7927-review-simplification/spec.md) and
[approved design](no-record-type-design.md) were supplied to the Spec reviewer.
Standards and Spec ran independently in parallel. Both performed read-only
inspection; runtime results are in the [verification record](review-simplification.md).

## Standards

**0 findings.** The changes follow the applicable documented rules:

- `heap_oos.cpp` catches allocation failures immediately and translates them
  into CUBRID errors, as required by personal `CUBRID.md`.
- `locator_sr.c` keeps the new C++ helper inside GNU-indent protection and
  retains `THREAD_ENTRY *thread_p` as its first parameter.
- The test split follows the parent unit-tests rule of one test file per logical
  area and the OOS instructions' explicit GoogleTest exception.

No actionable baseline smells emerged. The finalizer's local `pending_value`
groups related facts without introducing a public abstraction; the contiguous
request collection serves the existing batch interface. Result addresses are
borrowed after collection ends.

The private `decode_stub` seam has two actual callers. Each obtains its stub
through the existing bounds checker, whose failure contract clears the output
pointer; decoding reports that failure through the established corruption error.

The locator helper centralizes adaptation and finalization ordering while
retaining received-owner and converted-view lifetime in INSERT/UPDATE. Its
parameters carry those existing lifetime requirements.

The shared SQL header follows the existing static-helper convention. Empty
derived fixtures preserve separately named GoogleTest suites while inheriting
common setup and cleanup; no Refused Bequest concern was identified.

Sources: personal CUBRID policy, source/storage/transaction instructions,
parent unit-tests guidance and the OOS GoogleTest exception. Fowler smell
heuristics were applied subject to those documented rules.

## Spec

**0 findings.** The refinement satisfies the three selected tasks:

- Finalization groups each current-view patch location, payload and insertion
  result. Result addresses are borrowed after collection finishes; validation
  and batch insertion precede every patch. Failure state, publication handling
  and compact-buffer reuse remain intact.
- The shared locator handoff runs after destination routing. Caller-local owners
  remain alive through heap/index processing; moving UPDATE still forwards its
  owner to INSERT. Copy-area exclusions and ownerless replication behavior
  are preserved.
- Independently verified **40/40 original test bodies are byte-identical**:
  four SHOW cases remain and 36 cases move to deferred-write verification.
  Shared helpers retain the real database fixture; CMake preserves serial
  execution and gives the longer workload its 180-second timeout.

Disk decoding retains the previous parser's bounds, length and identity
validation. Owner resolution still validates prepared state, allocation, index
and payload length. Shared descriptor layout, record types, generic packing,
storage/export guards and loader latch ordering are unchanged.

No missing implementation requirement, scope creep or incorrect-looking
behavior was identified. The parent verification subsequently passed the final
configured debug suite: 36/36 CTest entries.

Final findings: Standards 0; Spec 0. Neither axis has an outstanding issue.
