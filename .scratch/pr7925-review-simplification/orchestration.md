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
| 01 | `/root/ticket01`, `fork_turns=none` | `task/pr7925-01-stored-rows`; `/home/vimkim/gh/cb/pr7925-01-stored-rows` | `1c660d22e4340ee707336ad08c8b4bf4b69744de` | Claimed; implementation and verification in progress |
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
has been performed. Complete independently ready 01 before presenting the
precise base/integration decision for 02. Final partition acceptance still
requires prerequisite inclusion in the shared integration branch.

## Verification and remaining gates

01 will use `debug_gcc` through live preset-aware prepare/configure/build/install
and protected CTest recipes. Required observations are all 21 comparison cases,
all 13 real loader/workspace cases, and final configured OOS CTests including
the real utility fixture. Historical passes are not counted as this run.
Executed receipts and acceptance mapping are pending.

After implementation, inspect scoped commits, rebase onto the current private
integration tip and fast-forward privately. Review Standards and Spec against
the pinned starting head, and inspect the whole-PR delta against the review
baseline. Preserve unrelated source and docs worktrees and useful evidence.

Existing PR/shared/default branch promotion requires the recorded user
confirmation. Dependency selection does not authorize merging PR #7927 into
existing source branches. Push, external publication and CI require separate
authorization. Parent spec is unchanged and remains unresolved; item 292 stays
unfinished while ticket 02 or required review remains outstanding.
