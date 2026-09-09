# PR7600 routing change — blocked-handoff review

Date: 2026-09-09. User authorized review and a locally committed **blocked handoff**, not CBRD-27237 implementation, integration, experiments, full acceptance or push.

Pinned diff: `git diff b871ea386d2c5419b7abae07dda58b9b7f36377a...213ce80f54dc54130fcef22e616cb28f4835f6d5`.

Commit list: `213ce80f5 [CBRD-27089] Route partitioned OOS writes by effective key and verify cleanup`.

Seven changed files: five engine files plus the SQL test CMake file and `test_oos_sql_show.cpp`. The uncommitted rollback/vacuum regression is not in this diff. Base ref and nonempty diff were verified before dispatching independent Standards and Spec reviewers. Both reviewed read-only; no new tests or experiments ran.

Spec source: [effective-key specification](../../.scratch/pr7600-effective-key-routing/spec.md). Supporting proof inventory: [preliminary matrix](ticket07-preliminary-evidence-matrix-213ce80f5-codex.md). Standards sources: source repository root `AGENTS.md`, `src/AGENTS.md`, `src/query/AGENTS.md`, `src/storage/AGENTS.md`, `src/transaction/AGENTS.md`, `unit_tests/AGENTS.md`, with existing OOS GoogleTest conventions and repository rules taking precedence over generic smell heuristics. Tooling-enforced checks are excluded from the human Standards axis.

## Standards

No non-tooling-enforced documented-standard violations found in `b871ea386...213ce80f5`. Engine changes retain explicit cleanup and C-style error returns; compatibility wrappers preserve existing interfaces and therefore are not “Middle Man” findings. The intentionally large source files are not a smell under this repository's rules.

One optional, non-blocking heuristic:

- **Possible Duplicated Code:** `unit_tests/oos/sql/test_oos_sql_show.cpp:703` and `:1421` repeat the same 13-entry `const char *columns[]` matrix, beginning `"SMALLINT DEFAULT 11", "INTEGER DEFAULT 11", "BIGINT DEFAULT 2147483648"`, plus the same default-expression extraction and CHAR-padding special case. Sharing only this test-case data would prevent INSERT and UPDATE coverage from drifting while keeping their independent behavior checks explicit. This is a maintenance suggestion, not a required handoff change.

Summary: **0 hard violations; 1 optional low-severity duplication finding.** Read-only review; no experiments or modifications.

## Spec

No new implementation defect or scope creep identified in `b871ea386...213ce80f5`. Source inspection supports temporary-key ownership, supplied-old/default reads, dedicated increment preservation, destination-only OOS override, shared expression matching, and retained final routing/representation handling. Destination disagreements are rejected before final heap/index mutation (`locator_sr.c:4996`, `:6021`).

Three acceptance limitations remain; none prevents the explicitly authorized **blocked handoff**:

1. **Lifecycle gate — failed/incomplete.** Testing Decision 9 requires “server-mode coverage for concurrent old-version readers, moved-update rollback, and OOS lifecycle interactions with vacuum/recovery.” The saved baseline/candidate rollback-vacuum regression fails; direct partitioned SERVER visibility/recovery coverage remains incomplete. This is an attributed baseline defect and missing proof, not a newly identified routing defect. CBRD-27237 must be evaluated separately; passing its regression alone will not close ticket 05.
2. **Runtime gate — unmet.** Testing Decision 13 says “Inconclusive measurements do not prove the gate passed.” Resource savings and instruction counts do not establish acceptable runtime. The retained measurements cover pre-format candidate P, not a future dependency-integrated revision. Ticket 06 remains open for acceptance.
3. **Failure-proof coverage — partial.** Testing Decision 10 requires “each single-failure category and selected multiply-invalid statements”; Decision 3 requests “final heap/index failure coverage.” The matrix locates index/preparation/codec failures but no dedicated multiply-invalid statement or distinct final heap-write failure evidence. Implementation Decision 11 requires routing disagreement to trigger “cleanup and investigation”; guards exist, but induced-disagreement cleanup remains unverified. Preserve these explicit revalidation obligations rather than presenting ticket 04's completed checklist as exhaustive proof.

Summary: **0 new code defects or scope-creep findings; 3 known acceptance limitation groups.** Most severe: failed rollback/vacuum lifecycle safety. No tests or experiments were run.

## Disposition

Retain the current routing implementation and final routing without an optional test-data refactor. No corrective engine commit is warranted by this review. Existing implementation commit `213ce80f5` is the source handoff; the accompanying documentation commit records the evidence and blockers. Do not call this a review of a CBRD-27237 fix or a final integrated acceptance review.

Standards: 0 hard violations, 1 optional low-severity duplication heuristic. Spec: 0 new code defects/scope creep, 3 acceptance limitation groups; failed lifecycle safety is the most severe Spec limitation.
