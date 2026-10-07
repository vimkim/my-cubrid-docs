# 02: Simplify converted-record memory ownership

**What to build:** Standalone workspace INSERT and UPDATE should keep converted record bytes alive through heap/index processing and release their temporary memory on every successful or failing return under one clear ownership rule. Use suitable ownership supplied by CBRD-27089 where possible; add a private conversion owner only when it is still needed and makes the resulting code easier to review.

**Blocked by:** External prerequisite CBRD-27089 / PR #7927: its accepted write/ownership interface must be available on the chosen implementation base. Ticket 01 is not a blocker. Final partition acceptance additionally requires the dependency's integration into the shared integration branch.

**Status:** claimed

Local implementation and private verification are complete. Final shared-branch
partition acceptance remains pending; the ticket is not resolved yet.

- [x] Identify and record the accepted CBRD-27089 revision and interface used by this task. Reuse an existing owner if it already manages the workspace conversion buffer; do not add a duplicate owner or preparation path.
- [x] If a separate owner remains necessary, keep the record description and cached copyarea together in one private, non-copyable owner with non-throwing automatic memory cleanup. INSERT and UPDATE follow the same lifetime rule on all exits.
- [x] Preserve current copyarea allocation, buffer reuse, and allocator error propagation. Do not substitute the generic owning record descriptor or broaden this task into allocator repairs. Review any change in the release order of independent scratch buffers.
- [x] Keep converted bytes valid while heap/index processing uses them. Keep the active record pointer separate, redirect it only after successful conversion, and never restore it from the owner destructor after another path has legitimately replaced it.
- [x] Keep the original workspace bytes and header when no demotion is selected, release unused conversion memory promptly, and preserve CHN, metadata exclusions, and already-converted-record behavior. Owner initialization must remain compatible with existing error jumps and legacy formatting.
- [x] Preserve external BLOB/CLOB filenames and contents and their existing copy behavior. Keep the accepted OOS eligibility of serialized locator bytes; do not confuse avoiding another LOB-file copy with excluding locator bytes from OOS.
- [x] Keep temporary-memory cleanup separate from database rollback. OOS creation or finalization and heap/index writes stay within the existing transaction/system-operation scope, including filtered-error handling; the owner releases memory only.
- [x] Preserve accepted force flags and workspace-origin propagation, reserved OIDs, object references, existing storage policy, multi-chunk values, OOS+bigone rejection, ordinary non-OOS bigone support, and successful no-logging loading.
- [x] Preserve ordinary SQL, CS loader, replication, and existing workspace UPDATE/DELETE behavior. Add no partition-selection algorithm or general destination-heap/OOS ownership repair; those belong to CBRD-27089.
- [x] Verify successful and failing INSERT/UPDATE through existing callers, including rollback, ignored duplicate-key continuation, no leftover OOS data under the logged-operation contract, and all 13 real loader/workspace scenarios. Keep all 21 comparison scenarios available, whether or not ticket 01 has been completed.
- [ ] Build and run focused existing tests during the change, then the configured OOS CTests at the final revision. After prerequisite integration, rerun the partition cases against the combined revision and record both source identities; attribute routing failures to their owning issue.
- [x] If allocation or release behavior changes, record proportionate small-row and OOS loader measurements under the same configuration and investigate a reproducible regression beyond noise. No runtime improvement or new no-logging failure-recovery guarantee is claimed.
- [x] Complete Standards and Spec review and make a focused local commit. If the dependency already removes the ownership problem, record the evidence without adding a redundant owner; if an added owner makes review harder, retain the current arrangement and explain the result.

## Context

The [approved specification](../spec.md) is the complete behavior contract.
The user approved this task and its external dependency on 2026-10-07.
The starting PR #7925 revision is `1c660d22e4340ee707336ad08c8b4bf4b69744de`,
with integration baseline `fb567a629cdb390fff920542173fa36f454c74a0`.

[CBRD-27089](https://jira.cubrid.org/browse/CBRD-27089) and
[PR #7927](https://github.com/CUBRID/cubrid/pull/7927) own the prerequisite.
Before claiming this task, verify that its accepted interface is available on
the chosen base. A PR being open or a historical test pass alone does not prove
that this prerequisite is satisfied. Selecting the prerequisite revision and
verifying its availability are preparation for this task, not permission to
merge the source branches or implement the prerequisite here.

Ticket 01 changes the tests, not the production interface required here, so it
does not gate this task. Prefer working 01 first for review convenience without
turning that preference into a false blocking edge.

Local source edits and verification are the deliverable. Push, CI triggering,
remote publication, and integration merges remain separate actions.


## Comments

2026-10-07: Not claimed or dispatched. PR #7927 remains open/unmerged at
`4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c`; its accepted `heap_pending_record`
interface is absent from the authorized private base. Ticket 01 has been
resolved independently. A read-only combination preview found conflicts in
loader and locator force interfaces. The coordinator must obtain the base
integration decision described in [orchestration.md](../orchestration.md),
verify the accepted interface on that base, then assign this ticket to a new
`fork_turns=none` agent. No prerequisite code was copied or merged.


2026-10-07: Private combination authorized by the user. Accepted dependency
`4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c` is now an ancestor of the chosen base
`b59f243fd0f30bb94344558ffa1755c37c43d2d4`; its storage owner implementation is
unchanged. Claimed for new clean-context agent `/root/ticket02`, branch
`task/pr7925-02-record-owner`, worktree
`/home/vimkim/gh/cb/pr7925-02-record-owner`. The coordinator's combined build
passed, and the focused raw copy-area/failing-update checks passed after the
integration-only origin correction. Final committed-base build/full focused
verification is in progress; the agent must establish its own baseline before
source edits. Shared-branch partition acceptance remains deferred.


2026-10-07 final private result: commits `9ba5e42ad6dfaa74cc9062f6fe55a459ba088924`
and `1932b3ec3d1b83bec83b7de1a6dd482f3a03b63d` are privately integrated on
`review/pr7925-combined`. The accepted prerequisite remains exact `4be72fc20`.
The same ticket implementer removed redundant eager conversion and addressed the
whole-spec no-demotion finding without adding an owner or modifying storage code.
Final source/owned CCI are clean. Both final review axes have zero source findings.
The full suite passes 38/38 CTests and 374/374 actual GoogleTests, with zero
failures/skips/disabled. Coordinator independently passes all 70 focused cases
(21 comparison, 13 loader/workspace, 36 dependency), and audits their identities.

The unchecked build/integration criterion is locally verified, including private
partition cases and both source identities. Its final shared-integration portion
remains unmet: PR #7927 is still open, and `feature/oos-merge` remains unchanged
at `fb567a629cdb390fff920542173fa36f454c74a0`. Recheck the actual squash merge,
transplant only this task's post-`4be72fc20` series onto the approved new base,
and rerun the relevant combined partition checks before resolving this ticket.
No shared/source promotion, push or CI is authorized by this result.

## Local result

- Accepted `heap_pending_record` received ownership covers the required lifetime;
  no separate private owner is needed. Active-pointer selection remains separate
  from memory ownership, and memory cleanup remains separate from database undo.
- Current inline standalone workspace input keeps its original descriptor/header;
  unused local record memory is released promptly after the accepted publication
  transition. Old/OOS/supplied-owner/server inputs keep accepted adaptation.
- Copyarea cache/scratch allocation and error propagation remain; only redundant
  workspace conversion disappears. CHN, LOB handling, force flags/origin and all
  existing scenarios are retained, with final private checks and source review.
- Three-sample debug small/OOS measurements show no reproducible regression within
  observed spread. No speed improvement or broader qualification is claimed.
- [Final report](../evidence/ticket02/report.md),
  [verification](../evidence/ticket02/verification-final.json),
  [measurements](../evidence/ticket02/benchmark-summary-final.json), and
  [retained inventory](../evidence/ticket02/retained-inventory.json) map the criteria
  to exact revisions and receipts. Remaining shared acceptance is explicit above.

Task worktree/branch, install, benchmark/failed databases, logs, TMP and allocation
are retained. Doctor reports seven unconfirmed socket entries and inaccessible
host PIDs; no inactivity/disposal claim or destructive cleanup was made.
