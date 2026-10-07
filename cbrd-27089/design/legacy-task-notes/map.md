> Preserved source task note. [Current entry point](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/../../README.md).

> Historical snapshot, status updated 2026-10-07. This note describes the earlier
> deferred-write implementation and its original authorization. Current PR7927 work
> is tracked by items281/284/289 and the approved four-task map in
> `/home/vimkim/gh/my-cubrid-docs-pr7927-temporary-oos-stub/.scratch/pr7927-oos-review-cleanup/map.md`.
> Current documentation entry: `/home/vimkim/gh/my-cubrid-docs-pr7927-temporary-oos-stub/cbrd-27089/README.md`.
> Earlier HEAD/base, remaining tasks and publication permissions below are historical.

# Replace early OOS routing with destination-owned deferred writes

Label: wayfinder:map
Status: resolved
Tracker: local Markdown; child issues under issues/; Blocked by lists child numbers; claim uses Assignee and Status: claimed; resolution under Comments/Answer.

## Destination

Implement deferred OOS writes after destination-heap selection in a new sibling CUBRID worktree, verify the replacement for PR #7600, and publish a new draft PR against feat/oos through vimkim/cubrid.

## Notes

- Build contract: [Destination-owned deferred OOS writes](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/issues/12-spec.md), published as ready-for-agent. Refine the existing execution outlines with to-tickets before implementation.

- User explicitly authorized worktree creation, implementation, source/docs commits and pushes, and a new draft PR. Execution is part of this effort's destination; planning is a prerequisite, not a substitute for the requested implementation.
- Base: feat/oos f4299ac0cd777a2a964c1f197ae5ebf9841a4936, checked against live PR7600 and fetched upstream on 2026-09-10.
- New worktree: /home/vimkim/gh/cb/CBRD-27089-oos-deferred-write. Branch: feat/oos-deferred-write.
- Existing PR7600 branch and worktree remain separate. Do not close or rewrite PR7600 without an instruction.
- Consult wayfinder, grilling, domain-modeling, cubrid-oos-context, cubrid-build and cubrid-pr-create. Research tickets use background research agents and dedicated research branches.
- Source is compiled as C++17; preserve legacy formatting and use exact INDENT guards for added C++ in .c/.h. Existing C error conventions apply; the user permits C++ RAII for prepared-plan memory ownership (see the representation decision).
- Source tests and behavior requirements from PR7600 are evidence; its effective-key early routing implementation is not the new foundation.
- Human architecture choices must be answered in conversation. Do not turn recommendations into accepted decisions.
- Draft publication is authorized; readiness claims must match actual test results. Independent known baseline bugs must be documented, not silently claimed fixed.

## Decisions so far

- [Choose a viable representation for prepared OOS values](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/issues/01-preparation.md): existing pruning can read prepared inline bytes; representation costs and alternatives are documented.

- [Find safe finalization points in heap INSERT and UPDATE](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/issues/02-integration.md): UPDATE replication precedes the heap call; integration and producer exceptions are documented.

- [Select the layer that owns deferred OOS writes](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/issues/03-boundary.md): locator invokes a shared storage finalizer after destination selection and before UPDATE index/replication processing.

- [Select the prepared-row representation and memory tradeoff](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/issues/05-representation.md): use an owned prepared-value/payload plan with C++ RAII memory ownership; routing needs a prepared-value adapter.

- [Agree on preparation and failure ownership](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/issues/04-contract.md): a movable, non-copyable prepared-row owner uses RAII for memory; transaction rollback and explicit operation cleanup handle persisted writes and publication state.

- [Define which record producers enter deferred finalization](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/issues/06-producer-contract.md): cover all ordinary row producers, including loader and redistribution, with explicit replica, serial, and internal-record handling.

- [Set verification and resource acceptance for deferred writes](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/issues/07-verification.md): require full producer/correctness evidence and baseline memory measurements, prohibit full-inline temporary rows and finalization-only payload copies, and disclose unavailable checks.

## Not yet specified

- None currently identified; implementation, verification, and publication are charted as child tickets. Surface new questions if source or experiments expose an unresolved tradeoff.

## Out of scope

- Rewriting ordinary overflow storage, new disk layout or wire-format features without evidence that they are necessary.
- Closing, force-pushing or publishing edits to the existing PR7600 branch.
- Unrelated cleanup and unrelated OOS vacuum/recovery defects.

## Implementation progress

- [Defer SQL INSERT to the destination heap](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/issues/13-insert.md): implemented and reviewed; full configured CTest passes 27/27.

- [Defer UPDATE and partition movement](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/issues/14-update.md): implemented and reviewed; destination ownership and rollback tests pass, full configured CTest 27/27.

- [Make duplicate probes free of OOS writes](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/issues/15-probes.md): implemented and reviewed; eight new SQL tests pass and full configured CTest passes 27/27.

- [Ticket 17 verification](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/evidence/ticket17-verification.md): queued loader ownership, retained batching and latch-safe destination insertion implemented; loader regressions and 27/27 CTest pass.

- [Ticket 21 publication](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/issues/21-draft.md): complete at `be7c01a6d`; paired memory evidence published with draft [PR7927](https://github.com/CUBRID/cubrid/pull/7927).
- [Remaining remote verification and acceptance](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/issues/22-ci-acceptance.md): resolved for tested `512b361`; see the acceptance resolution below.
  Historical snapshot 2026-09-11: static checks/builds pass; SQL16/medium3 failures all reproduce
  on baseline with identical paired local results. Shell154506 is blocked on
  unstarted prerequisite154505; required-check applicability remains unknown.
  No replacement acceptance was claimed at that historical snapshot.

## Acceptance resolution — 2026-09-15 KST

V21-CI and V21-ACCEPT completed for tested512b361, parent38093ea. All25 CI
failures accounted for:24 independently reproduce on parent;1 intended invalid
partition rejection with rollback/live-chain cleanup/next-write proof. All paired
runs terminal. OptDebug parent104pages reproduces CI112-page threshold failure;
earlier Debug89/88 passes and variable CDC extraction results remain preserved.
Current35/35 CTest, real producer/transaction/recovery/HA/bootstrap and scoped
Valgrind evidence satisfy the accepted matrix.24 memory samples support accepting
the investigated7084/7596KiB loader growth cost for stable retained canonical
payloads; no new performance threshold or process-wide cap is implied.
Baseline failures remain failed CI. Existing subsystem scope limitations remain.
Detailed decision and evidence: my-cubrid-docs/cbrd-27089/
ci_analysis_report_512b361_codex.md and CBRD-27089-deferred-write_be7c01a_codex.md.
Earlier open/pending paragraphs are historical and superseded by this resolution.

Publication receipt: docs `87d41fd3e23c558bff9e79b097a0f3f64cde5b87` pushed and public report bytes verified through GitHub API. Source documentation-only commit `bffe13be29ccb8f11d1789cd002da9e03315fd93` is committed locally on feat/oos-deferred-write; remote tested engine remains512b361. Final Standards0/Spec0 blockers.
