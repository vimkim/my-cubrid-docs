# PR #7925 simplification orchestration

Work-tracker: 292; actor `codex-pr7925-architecture`.
Started: 2026-10-07. Contract: [spec](spec.md), [map](map.md), and
`/home/vimkim/tmp/handoff-pr7925-implement-spec-odikcelg.md`.

## Verified starting state

- PR #7925 is open in `CUBRID/cubrid`, head repository `vimkim/cubrid`, branch
  `CBRD-27424-oos-loaddb-sa`, head `1c660d22e4340ee707336ad08c8b4bf4b69744de`,
  target `feature/oos-merge`. Local source agrees; unrelated dirty
  `cubrid-cci/win/cci_version.h` remains preserved.
- Private integration branch `review/pr7925-simplification` is based on that
  exact head, in `/home/vimkim/gh/cb/pr7925-simplification-integration`.
  `gh-pr-info` finds no associated PR, as expected.
- Whole-PR review baseline remains `fb567a629cdb390fff920542173fa36f454c74a0`.
  The existing `feature-oos-merge` worktree now has unrelated changes in
  `AGENTS.md` and its CCI submodule; it is preserved and is not an integration
  destination for this session.
- Documentation branch `docs/pr7925-orchestration` is based on current docs
  `main` at `4e35909b2ed0791b45726829792dec4f52f4ed03`, in
  `/home/vimkim/gh/my-cubrid-docs-pr7925-orchestration`.

## Graph and dispatch

The selected set is exactly 01 and 02. There is no edge between them and no
cycle. 01 has no blockers. 02 has one external prerequisite. Comments and all
current ticket bodies were reread before dispatch.

| Ticket | Agent | Branch and worktree | Base | State |
| --- | --- | --- | --- | --- |
| 01 | `/root/ticket01`, `fork_turns=none` | `task/pr7925-01-stored-rows`; `/home/vimkim/gh/cb/pr7925-01-stored-rows` | `1c660d22e4340ee707336ad08c8b4bf4b69744de` | Resolved at `625b193745959d0ab047f26f4354e9aacb48160d`; privately integrated, final checks/reviews passed |
| 02 | Not dispatched | Not allocated | No authorized prerequisite-containing base selected | Externally blocked; ready-for-agent describes specification completeness only |

The implementer owns only 01. The coordinator owns scheduling, tracker edits,
private linear integration, evidence review and overall status. Any replacement
or repair assignment remains scoped to its originating ticket.

## External prerequisite evidence

Live GitHub query finds PR #7927 open and unmerged, head repository
`vimkim/cubrid`, branch `feat/oos-deferred-write`, head
`4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c`, target `feature/oos-merge`.
Live JIRA CBRD-27089 is Develop / Unresolved. Its historical description is
subordinate to the approved current design for interface selection.

The accepted local design and its latest scoped refinement use
`heap_pending_record` for the compact record and retained serialized payloads.
Locator INSERT/nonmoving UPDATE use an enclosing received owner and converted
borrowed view; moving UPDATE forwards its owner to destination INSERT. Sources:
`cbrd-27089/design/no-record-type-design.md` and `review-simplification.md`.
The candidate accepted interface revision is the current `4be72fc20` above.

That revision is not an ancestor of PR #7925, and its interface is absent on the
private integration base. An open PR or separate dependency worktree does not
satisfy ticket 02. No source-branch merge, prerequisite copy or partition repair
has been performed. Independently ready 01 is now complete. The precise base/integration decision
for 02 is recorded below. Final partition acceptance still
requires prerequisite inclusion in the shared integration branch.

A read-only `git merge-tree --write-tree --name-only --messages` preview of the
two pinned heads reports conflicts in `src/loaddb/load_server_loader.cpp`,
`src/transaction/locator_sr.c` and `src/transaction/locator_sr.h`. It did not
change a branch or checkout. Selecting a combined base requires explicit
authorization and careful adaptation of the force interfaces; a separate open
dependency branch cannot be treated as completed integration.

## Ticket 01 result and verification

The inspected one-file commits are `ba308c529a65d25f64897f7733ff167e2f6c1745`
and `625b193745959d0ab047f26f4354e9aacb48160d`. Both were rebased onto the
then-current private integration tip (no-op) and fast-forwarded privately.
The final comparison source SHA-256 is
`adc506598e3e69e4346e2392611b95cb00dbda8c060f9e3260e42f90c305feb6`.
The entire simplification changes only
`unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp`; production and the
whole-PR production delta are unchanged. The eight named comparisons, thirteen
boundary parameters and thirteen real loader/workspace cases are preserved.

The third converter reference and its cleanup are removed. Two real stored
rows retain independent expected values, per-attribute OOS selections, offset
widths, literal encoding boundaries, decoded collection comparisons and
MVCC-adjusted record sizes. The old/current representation scenario requires
the exact original value, added default and actual storage placement.

| Verification at final commit | Result | Evidence |
| --- | --- | --- |
| Ticket debug_gcc build/install and formatter | PASS; formatter unchanged | [Report](evidence/ticket01/report.md), [verification](evidence/ticket01/verification-final.json) |
| Ticket focused CTests | 4/4; 21 comparison + 13 utility/workspace cases | [Receipt](evidence/ticket01/focused-repair-final.log) |
| Ticket full configured OOS selection | 37/37 CTests; 336/336 GoogleTests in 31 XML files; zero failures/skips/disabled | [Receipt](evidence/ticket01/oos-full-final.log), [case audit](evidence/ticket01/case-receipts.json) |
| Private integration build/install | PASS | [Build receipt](evidence/integration/pr7925-integration-build-final-625b19374.log) |
| Private integration focused CTests | 4/4; same 21+13 cases; zero failures/skips/disabled | [Verification](evidence/integration/verification.json) |
| Coordinator source/receipt audit | PASS; requested case identities match baseline | [Audit](evidence/coordinator-verification.json) |

Earlier receipts and failed test-authoring iterations are preserved separately
and are not substituted for the final committed-revision results. All exact
commands, revisions and acceptance mappings are in the ticket report.

## Independent review

Standards and Spec reviewers were separate fresh contexts
`/root/review01_standards` and `/root/review01_spec`. Standards initially raised
one small grouping suggestion; the same ticket implementer addressed it in
`625b193745`. Final Standards has zero documented breaches and zero remaining
judgment findings. Final Spec has zero findings. Both final reviews concern
01; their pending-runtime observation at review time is resolved by the final
receipts above. No whole-spec completion is claimed.

- [Initial Standards review](evidence/review-round-1/standards.md)
- [Initial Spec review](evidence/review-round-1/spec.md)
- [Final Standards review](evidence/review-final/standards.md)
- [Final Spec review](evidence/review-final/spec.md)

## Retained state and cleanup

Both private engine worktrees are clean at `625b193745`. Original PR #7925
remains at `1c660d22e`, with its unrelated dirty CCI header preserved. PR #7927
and the shared target worktrees are unchanged. Documentation edits are scoped
to `docs/pr7925-orchestration`; the parent specification's blob remains
`89a4c2d242e9fc0bcb5580971370b359d28a6b79`.

The merged ticket worktree/branch remain because cleanup inspection records
uncertain process ownership. The host
[database-lifetime policy](/home/vimkim/gh/cubrid-workenv/docs/database-lifetime.md)
requires stopping cleanup when process ownership cannot be established.
The registry is empty and owned DB directories contain only empty LOB
directories; no matching readable current-user process/listener was found,
but inaccessible environments/PIDs prevent a claim of disposal eligibility.
The workenv files, ignored-artifact provenance and inventories are preserved
under [ticket evidence](evidence/ticket01/report.md). No process, IPC, socket,
install, TMP or allocation was removed. The private integration and docs
worktrees remain reviewable.

## Required decision for ticket 02

Authorize use of the pinned PR #7927 revision
`4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c` as a **private combined base**, with
linear rebase and conflict resolution of PR #7925's retained changes and the
completed 01 commits. This is the recommended next step, subject to the user's
base decision. The expected conflicts are loader/locator force interfaces;
the accepted ownership and workspace-origin behavior must be preserved.
The coordinator will record the original heads and resulting combined commit,
verify that `heap_pending_record` is actually present, and then dispatch 02 to
its own new clean-context agent and worktree. If a different accepted base is
chosen, record its identity before dispatch.

The handoff explicitly says: “Do not copy the partition fix into this PR or
interpret this dependency declaration as permission to merge the source
branches.” That gate is why the base decision needs confirmation. Permission
for this private combination would not promote either existing PR branch or
the shared/default branches. Final partition acceptance still requires the
prerequisite in the shared integration branch; private passes are interim.

Ticket 02 is unclaimed and has no assigned agent or worktree. Item 292 remains
unfinished and awaits this decision. After 02, the full selected specification
still requires final Standards and Spec review and final combined verification.
Existing PR/shared/default branch promotion requires a separate confirmation;
push, external publication and CI require separate authorization. Parent spec
is unchanged and unresolved.
