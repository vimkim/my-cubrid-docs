# 02: Simplify converted-record memory ownership

**What to build:** Standalone workspace INSERT and UPDATE should keep converted record bytes alive through heap/index processing and release their temporary memory on every successful or failing return under one clear ownership rule. Use suitable ownership supplied by CBRD-27089 where possible; add a private conversion owner only when it is still needed and makes the resulting code easier to review.

**Blocked by:** External prerequisite CBRD-27089 / PR #7927: its accepted write/ownership interface must be available on the chosen implementation base. Ticket 01 is not a blocker. Final partition acceptance additionally requires the dependency's integration into the shared integration branch.

**Status:** ready-for-agent

- [ ] Identify and record the accepted CBRD-27089 revision and interface used by this task. Reuse an existing owner if it already manages the workspace conversion buffer; do not add a duplicate owner or preparation path.
- [ ] If a separate owner remains necessary, keep the record description and cached copyarea together in one private, non-copyable owner with non-throwing automatic memory cleanup. INSERT and UPDATE follow the same lifetime rule on all exits.
- [ ] Preserve current copyarea allocation, buffer reuse, and allocator error propagation. Do not substitute the generic owning record descriptor or broaden this task into allocator repairs. Review any change in the release order of independent scratch buffers.
- [ ] Keep converted bytes valid while heap/index processing uses them. Keep the active record pointer separate, redirect it only after successful conversion, and never restore it from the owner destructor after another path has legitimately replaced it.
- [ ] Keep the original workspace bytes and header when no demotion is selected, release unused conversion memory promptly, and preserve CHN, metadata exclusions, and already-converted-record behavior. Owner initialization must remain compatible with existing error jumps and legacy formatting.
- [ ] Preserve external BLOB/CLOB filenames and contents and their existing copy behavior. Keep the accepted OOS eligibility of serialized locator bytes; do not confuse avoiding another LOB-file copy with excluding locator bytes from OOS.
- [ ] Keep temporary-memory cleanup separate from database rollback. OOS creation or finalization and heap/index writes stay within the existing transaction/system-operation scope, including filtered-error handling; the owner releases memory only.
- [ ] Preserve accepted force flags and workspace-origin propagation, reserved OIDs, object references, existing storage policy, multi-chunk values, OOS+bigone rejection, ordinary non-OOS bigone support, and successful no-logging loading.
- [ ] Preserve ordinary SQL, CS loader, replication, and existing workspace UPDATE/DELETE behavior. Add no partition-selection algorithm or general destination-heap/OOS ownership repair; those belong to CBRD-27089.
- [ ] Verify successful and failing INSERT/UPDATE through existing callers, including rollback, ignored duplicate-key continuation, no leftover OOS data under the logged-operation contract, and all 13 real loader/workspace scenarios. Keep all 21 comparison scenarios available, whether or not ticket 01 has been completed.
- [ ] Build and run focused existing tests during the change, then the configured OOS CTests at the final revision. After prerequisite integration, rerun the partition cases against the combined revision and record both source identities; attribute routing failures to their owning issue.
- [ ] If allocation or release behavior changes, record proportionate small-row and OOS loader measurements under the same configuration and investigate a reproducible regression beyond noise. No runtime improvement or new no-logging failure-recovery guarantee is claimed.
- [ ] Complete Standards and Spec review and make a focused local commit. If the dependency already removes the ownership problem, record the evidence without adding a redundant owner; if an added owner makes review harder, retain the current arrangement and explain the result.

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
