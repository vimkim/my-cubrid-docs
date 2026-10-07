# PR7927 temporary OOS stub design interview

Current outcome 2026-10-07: unchanged shared RECDES, existing borrowed owner and
validated payload indices accepted and implemented at `6b53181d3`.
[Current entry](../README.md), [verification](no-record-type-verification.md) and
[resolved task map](../../.scratch/pr7927-oos-review-cleanup/map.md) supersede
older proposals in this dated interview.

## Remove the pending record type — interview reopened 2026-10-07

Work tracker: 281. Source pin: `aecce0e1216a813771621c13112c8f27d43df22e`,
branch `feat/oos-deferred-write`, worktree
`/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write`. The user invoked
`grill-with-docs` and explicitly requires removing the new record type:
"I do not want to add new rec type." This supersedes the October 6 permission
to retain `REC_OOS_PENDING`. The earlier compact-record reuse, in-place
finalization, destination-owned writes, and common memory/disk access decisions
remain the starting constraints. The user approved the final replacement design,
test seams and task breakdown on 2026-10-07. Implementation is authorized;
remote publication is not.

Source facts at the pin:

- `storage_common.h:221` defines the local descriptor marker separately from
  the existing record types. `heap_attrinfo_prepare_record` sets it on every
  successful preparation, including rows without selected OOS values.
- `heap_oos_value_ref::encode_memory` stores a payload address in the third
  field of a null-head temporary stub. `decode` uses the descriptor marker to
  permit interpreting that field as a memory pointer (`heap_oos.cpp:56–112`).
  Removing that check alone would permit raw incoming bytes to supply a memory
  address. A null head by itself cannot authorize memory access.
- `heap_pending_record` already owns the compact buffer and retained values,
  but its payload vector currently has no attribute-location lookup or
  finalization-state API (`heap_pending_record.hpp:32–61`). Its move constructor
  preserves the underlying allocations.
- The marker also selects finalization (`heap_oos.cpp:139`), rejects heap
  insertion/update (`heap_file.c:25141,25573`), and rejects transport packing
  (`record_descriptor.cpp:329`). Each responsibility needs a replacement.
- The bulk loader queues the owners and finalizes before latching bulk heap
  pages (`load_server_loader.cpp:739–766`, `locator_sr.c:14184–14193`). Owner
  lifetime, retained-byte accounting, and this latch ordering must survive.
- Payload-list emptiness is not a complete state test: inline-only prepared
  rows still need the per-row OOS publication reset, and successfully finalized
  owners currently retain their payload allocations until destruction. Preserve
  logical-row publication reset separately from whether any values need insertion.
- Explicit owner propagation reaches routing and duplicate probes, including
  grouped Resolve, composite-key size/value helpers, and the separate cache
  created for a function-index expression. Binding only the main attribute cache
  would miss that expression path. Post-finalization index writers can keep their
  ordinary disk-only access contract.

Accepted direction on 2026-10-07: keep shared `RECDES` unchanged and pass the
existing row owner explicitly to prepared-row consumers. Pending-aware attribute
access receives a borrowed owner argument and obtains memory values from its
retained payloads. Ordinary fetched and received records use disk references.
Finalization takes the owner and current descriptor view, writes into the
selected destination, and replaces the same stub fields in place. A pending
placeholder must remain invalid as a stored OOS reference, and storage/transport
checks must reject it without a new record type. Exact placeholder encoding,
owner bookkeeping and transport validation remain downstream proof obligations
or decisions; this acceptance is not final shared-understanding confirmation.

### Round 1 frontier

Q1 — ACCEPTED by the user's "yes" after the concrete owner-argument explanation:
Should the shared `RECDES` layout remain unchanged as well, with
prepared-row consumers receiving the existing owner explicitly?
Recommendation: yes. This confines the new preparation contract to callers that
actually process a prepared row, at the cost of passing the owner through routing,
duplicate probes, and their attribute/key helpers. Adding a transient field to
`RECDES` would preserve some signatures but extend initialization/copy/lifetime
obligations across generic storage descriptors. The exact affected source seams
were checked by two read-only source investigations; this is static feasibility,
not runtime proof. The main seams are `locator_insert_force`/`update_force`/
`move_record`, `partition_find_partition_for_record`, `heap_attrinfo_read_dbvalues`,
`heap_attrvalue_get_key`, `heap_midxkey_get_oos_extra_size`, grouped Resolve, and
`heap_eval_function_index`. The existing owner is available at the prepare-side
callers in locator force, duplicate probes, redistribution, and server loaddb.

No ADR is created for the unsettled, reversible implementation choice. The
repository's canonical vocabulary remains in `CONTEXT.md` as required by its
domain-doc layout.

### Resume and source investigations — 2026-10-07

The user resumed items 281 and 284 with three goals: remove the record type,
establish one current documentation entry point while preserving historical
verification, and assess the two current-head Greptile comments. After design
agreement, the user requests local specification/tickets, implementation,
appropriate verification and two-axis review. Remote replies remain local drafts.

The user first asked what "owner context" means and requested concrete
implementation-design details. After that explanation, the user answered "yes"
to explicit owner arguments with unchanged `RECDES`. The argument refers to the
existing row owner; it is not a new field in shared `RECDES`. The
[concrete proposal](no-record-type-design.md) records payload-index lookup,
reader propagation, current-view finalization and the open transport contract.
Three read-only investigations inspected representation, reviewer feedback and
documentation navigation. They made no source changes or runtime claims.

The [comment assessment and draft replies](reviewer-comments-aecce0e.md)
distinguish newly added client adaptation work from existing server fresh-chain
UPDATE behavior. Unchanged-chain reuse is not a safe isolated optimization under
the current vacuum/replication design. That disposition is source-backed; total
performance impact remains unmeasured.

Documentation cleanup will add a single current index, label pin-specific
narratives and old task entry points as historical, and retain their evidence.
The source-local ignored `.scratch/oos-deferred-write/` includes database/core
artifacts and must be preserved; its stale session/map are not the new tracker.
The configured durable tracker is the docs repository's local Markdown.
The exact-head CI/review package at docs commit `71bcfef` is on a separate clean
branch and should be reused, not recreated or treated as already present here.

### Round 2 frontier

Q2 — ACCEPTED by the user's "I approve": accept heap-row checks at the actual
`LC_FETCH` export boundaries while preserving generic packing semantics?
Recommendation: yes. Production rows use `LC_COPYAREA`, not
`record_descriptor::pack`. The three server row producers already request OOS
Expand and know the class; reject residual OOS fields before publishing a
non-root row descriptor. Preserve root metadata, no-content descriptors,
replication OOS payloads and error replies. Logical heap INSERT/UPDATE and
ownerless finalization separately validate stored references against the class
representation. No new descriptor field/type or legacy sentinel requirement is
needed. The concrete proposal records exact source evidence and the replacement
test seam.

For final shared-understanding confirmation, propose the existing SQL/owner/
replication tests, release boundary rejection checks and real server-loader
fixture, followed by two-axis review. The proposed four tasks are explicit-owner
access, marker removal with publication guards, current-revision reviewer
dispositions/local replies, and one current documentation entry point. Their
dependencies are recorded in the [proposal](no-record-type-design.md). These
test seams and task granularity were approved with the final design. The
[spec](../../.scratch/pr7927-oos-review-cleanup/spec.md) and separate tickets are
now published in the configured local Markdown tracker. Explicit-owner access
is claimed first. The design frontier is closed; implementation proceeds under
the user's original staged-workflow authorization.

The dated sections below are historical interview and implementation records.
Their earlier permission to retain `REC_OOS_PENDING` is superseded by the opening
section. Their verification claims apply only to their recorded revisions.

## Simplification interview reopened — 2026-10-06

Work tracker: 279. Source baseline: `feat/oos-deferred-write`, `b5b5eacbb`, in
`/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write`. The user requests
`grill-with-docs` because the delivered implementation remains too complicated.
The implementation and verification history below does not establish acceptance
of its readability. The user confirmed the implementation summary with "okay";
the agreed simplification is committed as `aecce0e1216a813771621c13112c8f27d43df22e`
in the existing source worktree.

The existing in-place finalization and common memory/disk access decisions remain
accepted unless explicitly revised. `REC_OOS_PENDING` is an implementation choice;
removing it is not an accepted decision. Existing canonical terms remain in the
repository's `CONTEXT.md`; no new terminology or ADR has been ratified.

Round 1 resolved — user answered "1 yes 2 yes":

1. What should win when a shorter patch conflicts with a simpler caller contract?
   Accepted: minimize the state and ordering obligations a caller must
   understand; assess the result with one explainable prepare/read/finalize flow.
   A small owner object is acceptable if it reduces caller coordination.
2. Are compact-record reuse, in-place stub replacement, and common memory/disk
   access fixed constraints for this simplification, or open to reconsideration?
   Accepted: retain compact-record reuse, in-place stub replacement, and common
   memory/disk access as constraints of this simplification.

Read-only delegated investigation found separate record/payload ownership,
nullable eager/deferred serialization, and a metadata/record rescan during
finalization. The loader shares retained payload ownership across queued rows;
consolidating ownership must preserve queue memory accounting and lifetimes.
`REC_OOS_PENDING` currently authorizes memory-reference decoding, selects
finalization, and prevents transport/storage of pending records. Its removal
requires replacing all three responsibilities, not merely changing a stub tag.

Round 2 resolved — user answered "yes":

3. May already-inline workspace records remain inline through routing and undergo
   OOS conversion only after the destination is known, while DB_VALUE producers
   continue using compact pending records? Accepted: yes, provided both
   paths share the applicable conversion logic and destination-owned write rules.
   This does not permit rebuilding an already-prepared compact record. Determine
   the exact integration ownership of PR7925 separately; no related-PR edits are
   authorized by this question.

Evidence: current `locator_prepare_client_row` (`locator_sr.c:6640`) adapts client
records before routing through `heap_prepare_oos_record` (`heap_file.c:13291`).
Related PR7925's `locator_oos_demote_workspace_record` (`locator_sr.c:4946` in
`CBRD-27424-oos-loaddb-sa`) instead converts SA workspace records after routing,
preserving CHN and avoiding repeated LOB copying. The two PRs have not been tested
together. This establishes an alternative to investigate, not proven equivalence
across all incoming-record paths.

Round 3 — ownership direction accepted after clarification:

4. Should each prepared row own its compact record and retained OOS payloads as
   one movable unit, including when queued by the loader? The user initially
   did not understand the loader/payload-pool terminology and requested Socratic
   dialogue. After explaining that the current shared list saves its length to
   release only a failed row's newly retained values, the user answered
   "아하 그러면 나쁘지 않지." This accepts the direction of keeping a row and its
   retained values together so discarding the row releases both. It does not yet
   settle the full owner API or whether the owner performs finalization.
   Proposed boundary:
   ordinary readers keep a borrowed RECDES view, and the owner handles lifetime
   and pending-entry bookkeeping. The tradeoff is per-row ownership metadata
   instead of the loader's shared payload pool. This is a proposed ownership
   boundary, not approval of a general row framework or a specific class API.
   Exact copyarea integration and finalization plumbing remain under inspection.

Current loader evidence (`load_server_loader.cpp:741–771`): callers save a payload
pool mark, prepare a separate record, push that record into the queue, discard
payloads back to the mark if queue insertion fails, and account separately for
record and payload memory. A consolidated owner should make failed queue insertion
clean up the whole row while preserving the queue's retained-memory bound.

The next Socratic question asked whether this unit should only manage memory
lifetime or also perform destination-owned writes and stub replacement. The user
answered "최대한 간단하게 가자." Treat this as delegation of the routine interface
choice under the agreed simplicity objective. Choose the smaller lifetime-only
owner first: reuse the existing finalizer and common value reader, retaining
the finalizer's schema/record scan rather than adding stored patch metadata and
new context plumbing. This deliberately limits the first simplification; it is
not a claim that every existing abstraction is necessary.

Implementation summary confirmed by the user:

- One row owner keeps its compact record and selected serialized OOS values
  alive together; ordinary reads use the existing RECDES and common value access.
- The loader queues the same owner and accounts for its retained bytes, removing
  shared-pool rollback marks and paired lifetime management.
- Existing finalization writes into the selected destination and patches the
  compact record in place. Preserve its storage/transport provenance checks;
  removing REC_OOS_PENDING is not a simplification requirement.
- Already-inline workspace rows can route before conversion. Implement the
  agreed conversion boundary in this task's worktree, checking PR7925 overlap
  without editing or publishing that separate branch.
- Preserve existing supported paths, rollback/LOB/header behavior and bulk latch
  ordering. Validate the simplified code before claiming completion.

Implemented result:

- `heap_pending_record` replaces the payload-only owner. It owns the existing
  `record_descriptor` plus selected serialized values, supports allocation-stable
  moves, and reports their combined memory use. Failed preparation or enqueueing
  is cleaned by destroying the row; callers no longer save shared-pool positions.
- DB_VALUE force and duplicate probes prepare directly into this owner instead
  of using LC_COPYAREA as temporary allocation. Redistribution and loader queues
  use the same lifetime model. Common readers and the existing finalizer remain.
- Copy-area insert/update passes its input origin through partition movement;
  conversion occurs after destination selection, in both server and standalone
  paths. Stored OOS references arriving in copy areas still get fresh
  destination-owned chains. The input representation ID is restored after routing
  to preserve the caller's image without copying its large values before routing.
- PR7925's separate branch is unchanged. Its SA workspace conversion overlaps
  this destination conversion and must be reconciled once when integrating the
  branches; no combined-PR runtime verification is claimed.
- Initial local verification exposed an invalid empty-record assertion, corrected
  by initializing the row descriptor before preparation. A CMake compiler-change
  cache reset also dropped unit-test options and left old test executables; a
  second configuration with the same debug_gcc preset restored the options.
  Both issues were resolved before the successful verification below.

Further source evidence: ordinary DB_VALUE force paths use LC_COPYAREA only as
temporary record allocation (`locator_sr.c:7800–7845`), so a record owner could
remove that bookkeeping. Finalization still needs a deliberate interface choice:
keeping its RECDES-only interface retains the metadata rescan, whereas using
per-row pending-entry metadata requires passing that context to the post-routing
write boundary. Absolute patch pointers are unsafe across MVCC header changes
(`locator_sr.c:5920`, `object_representation_sr.c:4424–4434`); VOT locations or
body-relative offsets can preserve the in-place constraint without caller repair.

Verification of the working tree subsequently committed as `aecce0e12`:

- Debug GCC build/install succeeded with unit-test instrumentation enabled.
  [Configuration](value-ref-evidence/simplification-configure.txt),
  [build](value-ref-evidence/simplification-build.txt).
- Configured CTest: **35/35 passed**, 212.16 seconds. The SQL show suite includes
  the new internal-workspace partition INSERT/movement case. The common-read
  test now destroys the complete pending-row owner before reading copied finalized
  record bytes, proving that persisted references no longer depend on retained
  memory. [CTest output](value-ref-evidence/simplification-ctest.txt).
- Real server loader: 600 × 20KB values, one 9MiB value, 800 partitioned rows
  split 400/400, incorrect-child rejection, and a successful subsequent load.
  Reused `value-ref-evidence/check-server-loader.py` against fresh task-owned
  database `oos_simple279`; stopped and deleted the database afterward.
  [Loader output and cleanup](value-ref-evidence/simplification-server-loader.txt).
- Project formatters were idempotent and `git diff --check` passed. Source changes
  are committed; original `cubrid-cci`, `cubrid-jdbc`, and `repro.sh` changes remain
  untouched. No remote push or local integration merge performed.

Limits: the separate PR7925 branch was inspected but not merged or tested together
with this revision. Full SQL/shell/medium CI and HA qualification were not run.
These local checks establish the simplification's tested behavior, not complete
OOS merge readiness. The source integration base remains `feature/oos-merge` at
`fb567a629cdb390fff920542173fa36f454c74a0`.

The sections below retain the earlier interview and implementation history.

Status: design direction and common read contract agreed; awaiting final shared-understanding confirmation before implementation. Exact encoding/provenance are implementation proof obligations. Design discussion only; no engine implementation authorized by this interview.
Work tracker: 276. Source inspected: `feat/oos-deferred-write`, `9232f111a`.

## User objective

Replace `heap_prepared_row` with an ordinary RECDES layout, temporary OOS inline stubs and retained values. Read retained values when routing needs them, then insert into the selected destination heap's OOS file. Minimize total code and reviewer effort.

The earlier full-inline destination-write POC (work item 271) was withdrawn and removed. This is a different proposal. Existing source submodule changes and untracked `repro.sh` are preserved.

## Source facts

- `src/query/partition.c:3508`: pruning uses `heap_attrinfo_read_dbvalues` unless the prepared-row override is supplied. Shared decoder support could remove that override.
- `src/storage/heap_file.c:11077`: single-attribute OOS Resolve currently reads a persisted chain into scratch or owned memory. Borrowed pending bytes need a defined ownership contract.
- `src/storage/heap_oos.cpp:465`: NULL head OOS OID is rejected; it cannot simply become an implicitly trusted memory pointer marker.
- `src/storage/heap_file.c:11384`, `src/storage/heap_oos.cpp:516`: grouped prefetch bypasses the single-attribute resolver. It also needs pending handling or a deliberate bypass.
- `src/storage/heap_file.c:15615`: pre-finalization composite index key construction uses prepared values to size keys; a compact RECDES length alone is insufficient.
- `src/transaction/locator_sr.c:5063`: INSERT finalizes after partition selection; destination is already known there.
- `src/transaction/locator_sr.c:14125`: bulk loaddb finalizes retained rows before bulk heap page latching to avoid heap-header/data-page latch interaction.
- Actual branch and normative specification use a 24-byte persisted OOS inline stub. Proposed transient encoding must not change that persisted layout.

## Proposed vocabulary (not yet ratified)

- Pending OOS value: an attribute value selected for OOS whose storage destination has not yet been materialized.
- Pending OOS stub: the temporary representation referring to that value before a stored chain exists.
- Suggested implementation owner name: `heap_pending_oos_values`. Retain only selected serialized values; ordinary attributes remain in the RECDES.

Update canonical `CONTEXT.md` only after terminology is agreed. No ADR yet: encoding, scope and alternatives remain open.

## Round 1 frontier

1. Self-contained access: superseded by the agreed uniform memory/disk reference direction. User clarified a mandatory constraint: reuse the built RECDES and overwrite its OOS inline stubs in place with real OOS references. This is feasible with either accessor design and does not settle pointer versus context. Recommend self-contained access conditionally on an enforceable trusted transient-record boundary.
2. Replacement scope: ACCEPTED by user Q2 "yes": replace prepared-row use across existing supported PR paths, including UPDATE movement, duplicate probes, loader and HA.

## Subsequent questions and proof obligations

Exact encoding and transient trust boundary depend on question 1; sequencing depends on scope. Investigate stable payload ownership across vector moves, RECDES copying, retries, LOB exactly-once effects, grouped reads, key sizing, partial insertion rollback and publication/replication. These correctness facts are the agent's work, not questions asking the user to relax safety.

Implementation requires explicit confirmation of shared design understanding under the invoked grilling skill. No build, DB experiment, push or PR modification performed.

## Accepted in-place finalization constraint

Serialize inline attributes once into the compact RECDES and reserve exactly one 24-byte field per selected OOS value. Once destination insertion returns the real chain references, overwrite those same fields with head OOS OID, full serialized length and identity stamp. Finalization must not reserialize ordinary attributes, allocate a replacement record or change its length or VOT offsets. Existing partition representation-ID changes are distinct from rebuilding the record.

This constraint applies to finalization of the pending record, not all subsequent heap-layer MVCC/header manipulation. The current `heap_prepared_row::finalize` already demonstrates an in-place 24-byte overwrite (`src/storage/heap_file.c:14367`); the proposed change removes the larger owner/API design around it.

## Rebuild and PR update direction

User suggested starting over from `feature/oos-merge` and force-pushing rather than reworking the prepared-row implementation. Favor a fresh sibling source worktree from that integration branch while preserving the existing worktree/branch and its unrelated modifications for comparison. Implementation still follows shared-design confirmation; publication follows verification. Use an explicit expected-old-head lease so concurrent remote work is not overwritten.

Live read-only checks: PR7927 targets `feature/oos-merge`; its head is `vimkim/cubrid:feat/oos-deferred-write` at `9232f111a7e7b6c71dbfa451db2812ae14766041`, routed through `vk`. Remote `origin/feature/oos-merge` matches local base at `fb567a629cdb390fff920542173fa36f454c74a0`. Recheck these before implementation/publication. No branch reset or push performed.

## Round 2 frontier: transient descriptor provenance

Historical Q3 (superseded by the union proposal, not separately accepted): allow an in-memory-only discriminator in the existing `RECDES.type`, while preserving the descriptor structure, the allocated record buffer, length and VOT? Recommend yes. A locally prepared pending record may use a NULL-head/length/accessor temporary field and shared readers branch on the trusted descriptor discriminator. After successful destination insertion, overwrite the same 24-byte fields with ordinary chain references and restore the normal descriptor type before heap storage. Encoding details remain to be verified.

Source evidence: `storage_common.h:226` has INT16 type; persisted slotted-page type is four bits (`slotted_page.h:90`). Pruning leaves type intact. Current INSERT normalizes type only after finalization (`locator_sr.c:5086`). UPDATE movement passes the descriptor through to destination INSERT. Copies preserve type.

Correctness obligations: locator copy-area macros do not initialize type (`locator.h:55`, `75`), so initialize it per incoming row; prohibit transient descriptors through generic pack/unpack (`record_descriptor.cpp:327`, `334`) or physical storage; leave persistent NULL-reference validation intact. Stable allocated payload addresses, owner lifetime and bulk retained-byte accounting remain mandatory. No global pointer registry is needed if descriptor provenance is enforced. This is source-supported feasibility, not executed proof.

## User steering: discriminated memory/disk reference

User challenges situational decoder behavior and proposes a discriminated union exposing one OOS value-access interface regardless of memory or disk storage. Favor this direction: decode the packed field once into a proposed `heap_oos_value_ref` with explicit memory and disk alternatives. Expose one `read_into` contract so callers share copying, error and value-decoding behavior. Keep `oos_read` as the physical disk-chain reader; the memory alternative copies retained serialized bytes into the requested destination.

This supersedes Q3 as a choice of making callers inspect `RECDES.type`. Such a field could still be an internal provenance mechanism, but it is not a required user-facing interface or an accepted encoding decision. A discriminated union centralizes representation dispatch; it does not by itself establish validity/lifetime of a memory accessor decoded from bytes. Resolve that inside construction/validation rather than spreading state tests through partitioning and indexes.

The runtime C++ tagged union is distinct from the packed 24-byte record representation: do not memcpy an ABI-sized union or std::variant into the stub. Existing persisted layout remains OID/length/stamp. Pending packed encoding can use a reserved representation only after invalid/corrupt disk and incoming bytes are prevented from constructing a trusted memory reference. Finalization converts each pending packed field to the existing disk representation in place.

Revised Q3 recommendation: put the memory/disk union and common read operation at the heap attribute-access seam, preserve disk-only `oos_read`, and keep partition/index callers representation-agnostic. This scope avoids rewriting physical OOS storage APIs while solving the two real access modes. Exact tag encoding and memory-owner mechanics remain implementation design facts to investigate.

### Round 3 frontier: common access contract

Q4: ACCEPTED by user "yes". Should both alternatives expose the same copy-into-caller-buffer operation rather than memory returning borrowed bytes and disk returning allocated bytes? Recommend yes for initial redesign: use caller scratch where available and preserve the existing DB_VALUE copy/free contract. This keeps representation and ownership branching out of callers. Direct borrowed access can be considered later only if measurements justify complicating that contract.

Source investigation confirms the proposed union can stay at heap Resolve, with size inspection, single reads and grouped reads consuming it. Grouped disk reads should preserve batching. No compilation/runtime experiment performed.

## Shared-understanding summary confirmed by user

- Build from the current `feature/oos-merge` in a fresh sibling worktree; preserve the existing PR worktree for comparison.
- Build one compact RECDES with ordinary inline values and fixed-size pending OOS stubs; retain only selected serialized OOS values in a small owner (suggested name `heap_pending_oos_values`).
- Use an explicit memory/disk reference with one size/read-into-buffer interface at heap attribute access. Keep storage-level `oos_read` disk-only. Partition, duplicate/index and grouped readers use this common abstraction.
- After destination selection, insert pending values into that heap's OOS file and overwrite the same stub fields in place with real OID/length/stamp. Preserve record buffer, length and offsets during finalization.
- Replace prepared-row machinery across the current PR's supported paths, preserving serialization/LOB effects, ownership/rollback/replication and bulk-latch ordering.
- Prove trusted construction and stable owner lifetime centrally. Do not let disk/client bytes directly authorize memory dereferences or let pending stubs reach storage/transport. Select the smallest correct internal encoding; reopen discussion if it requires broad descriptor/API changes or loses the intended simplicity.
- Build and run proportionate focused/regression checks, review total diff against integration base, and commit the replacement before remote PR-head replacement. Use an expected-head force-with-lease; no remote mutation during this design interview.

No architectural decision record is needed yet: no persisted format is changed and encoding remains a reversible implementation choice. Canonical vocabulary now records the resolved memory-versus-stored OOS concepts in `CONTEXT.md`.

## Implementation in progress

The user confirmed the shared-understanding summary and authorized implementation. The replacement is being built in `/home/vimkim/gh/cb/CBRD-27089-oos-value-ref`, branch `CBRD-27089-oos-value-ref`, from `fb567a629cdb390fff920542173fa36f454c74a0`. The original worktree and PR head remain preserved.

The implementation uses `heap_pending_oos_values` for payload ownership and `heap_oos_value_ref` for memory/disk dispatch. Partition and index callers retain their ordinary RECDES interfaces. A local-only descriptor type permits pending stub decoding; incoming copy areas initialize a normal type, and storage/transport boundaries reject pending records. Finalization inserts all pending values before changing the existing stub slots. Verification is in progress; no remote replacement has occurred.

## Verified replacement

Source commit `f578cd0d0078eb026930380144ad503ab81bd040` passes the debug build and35/35 configured tests. A real server-loader fixture verifies retained payload lifetime across600 rows, an oversized9MiB row,800 partitioned rows, wrong-child rejection and next-load usability. See `value-ref-evidence/` for the fixture and captured results, and `value-ref-review.md` for review findings and resolutions. The source diff against the integration base is780 added/81 removed lines, compared with1152/311 in the previous PR design.
