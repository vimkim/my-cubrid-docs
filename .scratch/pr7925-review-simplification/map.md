# PR #7925 review simplification: approved task map

Approved: 2026-10-07, user response "yes" to the two-ticket breakdown.
Work-tracker: 292
Contract: [approved specification](spec.md)

| Ticket | What it delivers | Blocked by | Status |
| --- | --- | --- | --- |
| [01: Simplify SQL/workspace comparison tests](issues/01-simplify-stored-row-comparison.md) | Two real stored rows and independent expected results, with the extra conversion and its rollback machinery removed. | None. | resolved |
| [02: Simplify converted-record memory ownership](issues/02-simplify-converted-record-ownership.md) | One clear memory lifetime across successful/failing workspace INSERT and UPDATE, fitting the accepted prerequisite interface. | External CBRD-27089 / PR #7927 accepted write/ownership interface available on the chosen base. | claimed |

## Work order and dependencies

Start with 01. It can run against the current production implementation and has
no dependency on 02 or CBRD-27089. Its small stored-row capture cleanup is part of
the same verifiable task rather than a separate preparation slice.

02 can be claimed once its external interface prerequisite has been verified.
It does not depend on 01. Working 01 first is a review preference, not a blocking
edge. Final partition acceptance follows integration of CBRD-27089 into the
shared integration branch; the partition fix remains outside these tickets.

`ready-for-agent` means a ticket is fully specified. It does not waive its
blocking edges. Record the accepted prerequisite revision when the external
dependency is satisfied, and keep verification tied to the actual combined
source revision.

The parent specification remains unchanged. This publication creates two local
tickets and their map; neither source implementation nor new runtime test
results are claimed. Local integration, pushing, CI, and remote publication are
separate actions.

Execution state, evidence and unresolved prerequisites are recorded in
[orchestration.md](orchestration.md). The initial dispatch gate required its interface on an authorized base. The
approved private combination and current verification are recorded below.


2026-10-07 execution checkpoint: 01 is resolved at `625b193745`, with final
37/37 CTests and 336/336 GoogleTests and zero findings on both review axes.
02 remains externally blocked and unclaimed. See the orchestration record for
the exact base decision; the parent contract remains unchanged and unfinished.


2026-10-07 continuation: private prerequisite combination approved and frozen
at `b59f243fd0f30bb94344558ffa1755c37c43d2d4`. The accepted owner interface is
present; 02 is claimed for its own new clean-context agent/worktree. Shared
integration acceptance remains an external gate, with future squash-transplant
procedure recorded in orchestration.md.


2026-10-07 final private checkpoint: both selected implementations are integrated
at `1932b3ec3d1b83bec83b7de1a6dd482f3a03b63d` on `review/pr7925-combined`, using
accepted prerequisite `4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c`. Full 38/38 CTests
and 374/374 actual GoogleTests pass, and coordinator 70/70 focused cases pass,
with no failures/skips/disabled. Final whole-spec Standards and Spec reviews have
zero remaining source findings. 01 remains resolved. 02 remains claimed with
local implementation/verification complete and final shared partition acceptance
pending. The parent spec and work item 292 remain unfinished until that external
gate is satisfied; existing source/shared/default branches are unchanged.
