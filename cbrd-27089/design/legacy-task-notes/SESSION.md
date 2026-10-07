> Preserved source task note. [Current entry point](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/../../README.md).

> Historical snapshot, status updated 2026-10-07. This note describes the earlier
> deferred-write implementation and its original authorization. Current PR7927 work
> is tracked by items281/284/289 and the approved four-task map in
> `/home/vimkim/gh/my-cubrid-docs-pr7927-temporary-oos-stub/.scratch/pr7927-oos-review-cleanup/map.md`.
> Current documentation entry: `/home/vimkim/gh/my-cubrid-docs-pr7927-temporary-oos-stub/cbrd-27089/README.md`.
> Earlier HEAD/base, remaining tasks and publication permissions below are historical.

# Deferred OOS replacement session state

Goal: implement the user's deferred-write alternative in this worktree and publish a new draft PR. Work item117 is the durable umbrella. Source and draft publication already authorized.

Current phase: tickets 13 (INSERT), 14 (UPDATE/movement) and 15 (duplicate probes) are complete. Ticket 15 is committed as `5e0a30663453cc5a2fd29c7d4da328a1f1741ffd` on feat/oos-deferred-write. Eight new SQL tests pass; the full configured CTest suite passes 27/27 (SHOW SQL binary 27/27). Independent Standards/Spec reviews each report zero actionable findings. See [ticket 15 verification](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/evidence/ticket15-verification.md), including the baseline standalone old-outlined-key DELETE/index limitation. Remaining implementation slices include [16 — raw rows and redistribution](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/issues/16-raw.md) and [17 — loader](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/issues/17-loader.md); later verification, resource acceptance and draft publication remain outstanding.

Canonical map: [Replace early OOS routing with destination-owned deferred writes](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/map.md). Human decisions are recorded in the linked resolved tickets; no architecture decision remains pending. The synthesis asked for a test-boundary check and uses SQL-first testing with specialized loader/HA/recovery flows and focused failure/lifetime checks as its stated assumption unless the user corrects it.

Worktree: /home/vimkim/gh/cb/CBRD-27089-oos-deferred-write
Branch: feat/oos-deferred-write
Pinned base: f4299ac0cd777a2a964c1f197ae5ebf9841a4936
Current engine HEAD: 5e0a30663453cc5a2fd29c7d4da328a1f1741ffd
Target: CUBRID/CUBRID feat/oos; push source via vk (vimkim/cubrid). Detailed PR doc uses validated vimkim/my-cubrid-docs repo and cubrid-pr-create format/checker.

Bootstrap debug_gcc completed. Pinned CCI bd86063a is checked out; its build generated win/cci_version.h differences that must not be staged. Global UNIT_TESTS is OFF but UNIT_TEST_OOS is ON by default, so OOS binaries are already built. A fresh isolated run of test_oos_sql_show passed all4 existing tests; see evidence/baseline-show.json and baseline-show.xml. No preset changes were needed. This baseline suite does not contain the PR7600 ownership regression; the separate SQL probe reproduces that bug.

Baseline SQL reproduction completed: value_matches1 despite root OOS1chunk and p0none. See [baseline summary](/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write/.scratch/oos-deferred-write/evidence/baseline-summary.md). Private DB fixture preserved. No existing user DBs touched.

Tooling note: first bootstrap attempted shared justfile whose recipe-level justfile_directory ignored working-directory; stowing cubrid into the new target explicitly, then running local just prepare, fixed setup. Bootstrap then completed. Do not modify shared tooling or use the original worktree for subsequent engine edits.

Previous ADR chose early-key routing, but current user explicitly reopens that design and authorizes the broader replacement. Preserve disk-format scope and successful SQL/transaction semantics; no silent memory/type coverage downgrade. Research source assets committed separately at8d20de24a and af2359b42a; copies and links retained under research/.
