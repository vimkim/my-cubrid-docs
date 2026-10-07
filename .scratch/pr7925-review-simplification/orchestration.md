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
| 02 | `/root/ticket02`, `fork_turns=none` | `task/pr7925-02-record-owner`; `/home/vimkim/gh/cb/pr7925-02-record-owner` | `b59f243fd0f30bb94344558ffa1755c37c43d2d4`, contains accepted `4be72fc20` | Claimed; first commit `9ba5e42ad` privately integrated; whole-spec review repair and final verification active |

Each implementer owns only its assigned ticket. The coordinator owns scheduling, tracker edits,
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

Initially that revision was not an ancestor of PR #7925, and its interface
was absent on the original private integration base. An open PR or separate dependency worktree does not
satisfy ticket 02. No existing source branch was changed, and no partition repair was made
here. The later authorized private combination is recorded below. Independently ready 01 is now complete. The precise base/integration decision
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

## Approved private combination and ticket 02 preparation

The user authorized combining the pinned PR #7927 revision
`4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c` with the retained PR #7925 changes,
resolving conflicts and then assigning 02 to a new clean-context agent.
That approval covers private integration only. Item 292 is active again.

The original `review/pr7925-simplification` remains at `625b193745`.
The same integration worktree now checks out `review/pr7925-combined`.
An exact-tree snapshot of final PR #7925 (`1c660d22e`) over the common baseline
was made as `15d0b0d95ac620a7c5a8fb00322d896b914777c8`; its tree equals the
original final implementation. This avoids replaying withdrawn intermediate
implementations. Both ticket 01 commits were replayed separately. The private
series was then rebased onto `4be72fc20`, resolving loader/locator conflicts.
The first completed combination is `29ea2ed13`; baseline verification exposed an origin-handling integration regression.

Conflict resolution preserves the accepted destination routing and pending
owner arguments, plus PR #7925 force flags and workspace-origin propagation.
The original workspace conversion helper and force flags were initially
retained alongside the prerequisite received owner. Suppressing that owner
for standalone copy-area inputs proved incorrect: such inputs may already
contain stored references and still need destination-owned chains. The
existing raw copy-area test reproduced input mutation and wrong ownership
in 3.27 seconds. Removing that suppression restored the prerequisite path;
raw copy-area plus failing workspace UPDATE checks then passed 3/3 CTests
in 3.25 seconds. No assertions or prerequisite code were changed.
No partition-selection algorithm or prerequisite storage implementation was
changed. Comparison source bytes equal ticket 01's final hash.

The correction is scoped commit `b59f243fd0f30bb94344558ffa1755c37c43d2d4`.
This is the frozen ticket 02 base, with committed-base verification active.
Its storage sources equal `4be72fc20`; comparison source equals final 01.
Ticket 02 is claimed for a new clean-context agent on its own worktree, which
must establish its own baseline before implementation. The agent owns only
the ownership simplification and its verification.
Final partition acceptance still requires prerequisite inclusion in the shared
integration branch. Private combined results are interim evidence.

## Following a future PR #7927 squash merge

PR #7927 is expected to be squash merged into `feature/oos-merge`. Preserve
`4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c` as the exact dependency boundary.
Every private PR #7925 implementation/test/ownership commit follows that
boundary. Once the actual squash commit is available, transplant **only this
post-boundary series** onto the approved updated integration base:

```sh
git rebase --onto <approved-updated-feature-tip> 4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c <private-task-branch>
```

Use a separate review branch/worktree and retain the tested private result
until the transplant is verified. Do not replay the prerequisite's individual
commits. If the squash tree preserves the selected dependency code, ancestry
changes alone should not add substantive conflict; later dependency or shared
changes may require reconciliation. Inspect the task-only diff against the
actual new base and rerun appropriate checks before source promotion.
This procedure does not authorize that promotion in advance.

After 02, the full selected specification still requires final Standards and
Spec review and final combined verification. Existing PR/shared/default branch
promotion requires a separate confirmation; push, external publication and CI
require separate authorization. Parent spec is unchanged and unresolved.


## Frozen-base verification and active work

The exact committed base `b59f243fd0f30bb94344558ffa1755c37c43d2d4` built and
installed successfully. Its final focused selection executed all 70 requested
GoogleTests: 36/36 dependency and 21/21 comparison passed; 9/13 utility cases
passed. Four utility cases failed exact OOS chunk-count assertions after UPDATE:
reference preservation, rollback/commit/delete, external LOB UPDATE, and
partition movement. Their value/reference predicates passed. Five CTests ran;
four passed, with test_oos_workspace failing (193.62s).

The ticket 02 agent identified possible duplicate conversion on UPDATE:
the legacy eager workspace helper runs before the prerequisite received-owner
preparation/finalization. Removing redundant conversion is within 02; chain
reuse and general partition repair remain excluded. The agent will establish
its own baseline and verify the unchanged assertions before attribution. This
checkpoint claims no combined full-suite pass.

[Combined-base evidence](evidence/combined-base/source-contract.json) preserves
source identities, build/formatter logs, the first raw-copyarea red receipt,
its origin-repair green receipt, the failed broader baseline and actual XML
case counts. Failing fixture data remains under the paths printed by its logs.
The agent source/worktree and all original user worktrees remain separate.


A [temporary-object transplant check](evidence/combined-base/equal-tree-squash-transplant.json)
simulated one dependency squash with exactly the `4be72fc20` tree over the
common baseline. Replaying the four post-boundary commits through `b59f243fd`
produced zero conflicts and the exact private tree, with no dependency commits
replayed. No source/ref/worktree was changed. Actual later source changes still
require their own comparison and verification.


## Ticket 02 first fixed point and whole-spec review repair

Ticket 02 reproduced the same frozen-base result: 66/70 cases passed with the
same four utility count failures. Commit `9ba5e42ad6dfaa74cc9062f6fe55a459ba088924`
removes the redundant eager workspace converter, its separate descriptor/copyarea
and manual frees. It uses the existing received owner, and preserves explicit
workspace-flag semantics with the shared preparation path. The storage sources,
tests and public force interface are unchanged by this commit.

All four previously failing utility cases and four ownership/header/error
controls passed (8/8 GoogleTests, 4/4 CTests). Exact-commit build/install passed.
The implementer rebased onto private `b59f243fd` (no-op), and the coordinator
fast-forwarded `review/pr7925-combined` to that exact commit. Final runtime
acceptance is pending; the first full-suite run is in progress.

Initial same-configuration measurements use three samples each: small-row
elapsed/user CPU medians changed from 3.92/2.51s to 3.47/2.22s, and OOS medians
from 7.40/4.63s to 7.72/4.74s. Ranges overlap; no runtime improvement is claimed.
Raw data and methodology are in [initial evidence](evidence/ticket02-initial/report.md).
These measurements concern `9ba5e42ad`; a subsequent memory-lifetime repair
requires its own proportionate verification.

Independent whole-spec reviewers inspected all eight retained files against
accepted dependency boundary `4be72fc20`, separating inherited prerequisite
changes from original-head simplification and whole-PR context:

- [Standards](evidence/whole-review-round-1/standards.md): zero documented breaches
  and zero actionable judgment findings.
- [Spec](evidence/whole-review-round-1/spec.md): one resulting no-demotion
  conformance gap, inherited through the combined adaptation. Inline workspace
  inputs should retain their active original descriptor/header and promptly
  release unused local conversion memory. No allocator-policy finding or scope
  creep is asserted.

The same ticket 02 implementer owns this repair. It must preserve necessary
adaptation for old representations and existing OOS references, supplied owner
lifetimes, and finalizer/publication semantics. No storage-interface redesign or
new serialization/testing seam is authorized. The parent spec remains unchanged,
and final shared partition acceptance remains gated by actual prerequisite
inclusion. No ticket or whole-spec completion is claimed at this checkpoint.

A [five-commit equal-tree squash simulation](evidence/ticket02-initial/equal-tree-squash-transplant-9ba5e42ad.json)
replayed only the post-`4be72fc20` series through `9ba5e42ad`: zero conflicts,
identical final tree, zero prerequisite commits replayed. It changed no refs or
worktrees. Actual later dependency/shared changes still require verification.
