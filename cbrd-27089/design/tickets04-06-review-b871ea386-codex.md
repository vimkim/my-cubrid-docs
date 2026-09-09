# PR #7600 tickets04/06 — two-axis review

Review reference: original PR head `b871ea386d2c5419b7abae07dda58b9b7f36377a`. Because implementation was uncommitted at review time, reviewers used `git diff b871ea386d2c5419b7abae07dda58b9b7f36377a -- src unit_tests/oos/sql` rather than an empty three-dot comparison. Prior01–03 engine work was context; new04 tests and06 methodology were the review focus. No reviewer edited code or ran experiments.

## Standards

No non-tooling-enforced documented-standard violations found in the reviewed ticket04 tests, CMake timeout change, isolated runner, or ticket06 scripts.

One judgment-call finding: **possible Primitive Obsession**, low priority.

The cleanup tests use numeric failure scenarios with meanings reconstructed from conditionals; the benchmark uses an integer update tag for INSERT, unchanged-key UPDATE, and moving UPDATE. Named scenario/operation enums would make the matrix easier to audit. This is optional maintainability feedback, not an acceptance blocker; it remains a recorded improvement rather than an additional refactor.

Direct publication-container inspection and private codec substitution are intentional white-box contract checks, not Feature Envy. GoogleTest is established in this OOS suite; generic Catch2 guidance does not justify conversion. Large files are permitted by the repository.

Standards summary: **0 hard violations; 1 low-priority heuristic finding**.

## Spec

Initial review identified two P2 partial requirements:

1. Actual OOS payload serialization failure was not established by either the pre-serialization reset hook or the distinct effective-key fake codec. Ticket04 asks for OOS serialization/class/file lookup failure; the spec asks for each single-failure category.
2. Counting LOB copies during retry did not establish deletion or external-object lifetime. Readable original values and OOS counts alone could still hide leaked copied external files. Ticket04 requires no duplicate copy/delete behavior; the spec preserves LOB deletion/copying, metadata ownership, and retries.

Both findings were closed after additional evidence and independent re-review:

- [Actual payload malloc failures](ticket04-evidence/payload-allocation-cleanup.json) cover INSERT and moving UPDATE, exact OOM, rollback, ownership, and subsequent writes. This proves allocation failure during payload preparation, not arbitrary codec-return failures.
- [LOB lifetime observer](ticket04-evidence/lob-retry-lifetime.json) observes two copies and two logical deletions across two column attempts, exact restoration of the four original external paths/hashes after six aborts, no duplicate physical deletion within transaction intervals, and empty external inventory after teardown.

No additional scope creep or concrete ticket06 evidence defect was identified. The resource report appropriately qualifies its measurement scope and leaves runtime acceptance unmet.

Spec summary: **2 initial substantive findings, both closed; 0 remaining findings from this focused review**. This is not blanket acceptance: the known baseline vacuum failure and inconclusive runtime gate still block final integration.
