# Design review: reuse the early partition destination?

2026-09-09. Inspected source: `213ce80f54dc54130fcef22e616cb28f4835f6d5`. User authorized a design-only review, not implementation, experiments, or a validation waiver. Existing [ADR](../../../docs/adr/0001-pr7600-effective-key-routing.md) and specification remain unchanged.

## Recommendation

**Retain independent final record routing in this PR for now.** Destination reuse is technically plausible, but it is not a safe OID-substitution patch. The measured +0.689% whole-process instruction cost on small-inline INSERTs does not establish either an unacceptable runtime regression or the savings of a replacement. A second redesign currently has unresolved validation and metadata-lifetime obligations.

If the user wants to pursue reuse, the smallest *coherent candidate for specification* is an internal, operation-scoped routing result plus a finalization operation in the partition module. The finalizer must independently validate the serialized key and preserve representation handling; locator must still do locking, cache selection, index work and UPDATE movement. This is **proposed**, not proved, approved or implemented.

The codebase-design skill influenced this recommendation: keep partition semantics and result lifetime local to the partition module instead of teaching locator callers to coordinate a growing list of OIDs, representation IDs, booleans and borrowed pointers. The OOS specification requires correct per-heap ownership; it does not require two partition searches. Independent final routing is an accepted safeguard of this particular implementation.

## What final routing actually does

| Responsibility | Current source evidence | Reuse requirement |
|---|---|---|
| Load/reuse pruning context and distinguish root versus explicit child | `partition.c:3705` INSERT; `:3849` UPDATE | Preserve context provenance and explicit-child constraint, not just destination OID |
| Interpret serialized key under root representation | `partition.c:3635` temporarily patches root representation ID, decodes, then restores | Keep correct decoding and restoration on every failure |
| Evaluate expression and find matching partition | `partition.c:3494`, `:3648` | This is the work reuse seeks to remove; must replace its validation role explicitly |
| Patch final record to destination representation | `partition.c:3660` | Preserve target representation ID and the existing conditional patch semantics |
| Report destination heap and root class | `partition.c:3655`, `:3781`, `:3962` | Return valid HFID/root metadata, not stale or freed context pointers |
| Reject explicit-child mismatch | `partition.c:3771`, `:3951` | Revalidate or prove validity from the operation-scoped result |
| Reject early/final disagreement | `locator_sr.c:4996`, `:6020` | An independent proof is necessary; comparing a reused OID with itself is not validation |
| Lock destination and select partition scan cache/function-index predicates | `locator_sr.c:5005–5054` | Keep in locator at the existing stage |
| Refresh actual UPDATE source class/HFID and move if required | `locator_sr.c:6030–6068` | Keep separate from destination selection; input source may originate from unique-index pruning |
| Index/FK/heap work and transactional error handling | `locator_sr.c:6073` onward; INSERT `:5074` onward | Do not bypass by pretending the class is nonpartitioned |

Local source files: [partition.c](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/query/partition.c:3618), [locator_sr.c](/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/src/transaction/locator_sr.c:4984).

Important distinction: several responsibilities are **inside the routing helper**, while locking and movement are performed by its caller. Removing the helper requires preserving its effects; skipping the entire partitioned branch would additionally remove caller responsibilities.

## Why an OID alone is insufficient

The current early call in `locator_attribute_info_force` retains only `write_destination` for later agreement checking. Its early `pruned_hfid` is local to the selection block, and it requests no superclass output. Attribute routing clears its effective key before returning (`partition.c:3603`). When no context is supplied, the routing helper clears the temporary context before return (`:3791`, `:3973`). Context cleanup releases predicate/key state and possibly partition metadata (`:2813`).

Consequently, a raw `OR_PARTITION *` or pointer to the context-owned key cannot simply be carried into final force. A reuse result must own the facts it needs or have an explicit, proven retained-context lifetime. Copying numeric metadata avoids dangling pointers but does **not** prove schema freshness.

The full transformer still writes the source representation header (`heap_file.c:13031`) before final routing patches it. Destination OOS ownership and record representation identity are different concerns. Redirecting the OOS owner does not automatically produce a record with the destination representation ID.

## Candidate interface, not an implementation specification

Conceptual sequence:

```text
partition module: select from effective key → owned routing result
heap transformer: prepare/serialize once → record, OOS in selected heap
partition module: validate serialized key/result → finalize representation and destination outputs
locator: destination locks/caches → ordinary INSERT or UPDATE/move
```

The result would need a destination class/HFID, root and source/explicit-partition identity, applicable representation identities, and a key-equivalence witness or a rigorously proved preparation guarantee. Its lifetime is **one write attempt**, not the whole statement or shared pruning context. An error/retry must clear or invalidate it. Existing record-only callers would continue using record routing; that is a distinct caller contract, not a silent type-based fallback on optimized writes.

Prefer one partition-module finalization operation over caller-written representation patching. The result should not expose pointers into the source attribute cache, whose values may be normalized or incremented by the actual transformer.

This conceptual interface is not yet small enough to implement confidently: the witness and metadata-validity contract remain unresolved. Avoid inventing a cache-generation field or a boolean `already_pruned` without proving what it certifies.

## Three validation choices

1. **Blind reuse:** trust the early key and destination, patch representation, skip final decode/search. It saves the most routing work but removes runtime disagreement detection. Equivalence tests alone are not the same safeguard. Not recommended for this PR.
2. **Validated reuse:** independently decode the final stored key, prove it equivalent to the retained early key under the same expression/metadata, and reuse the destination without expression evaluation/search. More conservative, but retains decoding and adds witness ownership/comparison costs. For an OOS-backed key, decoding may still read OOS. Its net benefit has not been measured.
3. **Existing final route:** decode, evaluate and match independently, then compare destinations. Already implemented and covered. Retain pending a demonstrated need and a complete replacement proof.

For validated reuse, generic SQL-value equality is **not yet a proof** of identical results for every allowed partition expression. A comparator/canonical encoding must be specified for all legal key domains, including NULL, padding, collation, numeric conversion, defaults and INCR/DECR. A hash alone cannot be the correctness proof. A stricter exact-key check can also reject a changed key that still maps to the same partition, whereas current destination agreement would accept it; successful-path equivalence must be established, not assumed.

## UPDATE and preparation constraints

The general UPDATE force has a reevaluation path that can modify `new_recdes` when `oldrecdes == NULL` (`locator_sr.c:5836` vicinity). However, **do not misclassify that as a demonstrated post-routing mutation in the currently scoped path**: `locator_attribute_info_force` fetches or accepts the old record first (`:7688`), passes its address to early routing and then to final UPDATE force (`:7825`). The null-old-record reevaluation branch is therefore distinct for ordinary scoped UPDATEs. A reusable result must preserve this restriction instead of accidentally authorizing wider callers.

The transformer fills uninitialized values before layout (`heap_file.c:13498`) but applies pending fixed-column increments in the column writer (`:13145` vicinity). Thus, “layout is done” is not synonymous with “every effective key is finalized.” LOB preparation and retry behavior also remain stateful. Any alternative that routes inside or after preparation must state exactly which values are ready and whether increments have been applied.

## Proof obligations before specification can approve reuse

- **Key correspondence:** retained effective key and actual serialized key produce the same partition-expression result for every legal key and success path; source assignments remain unchanged by early preparation.
- **Independent validation:** state what failure finalization can detect that early selection alone cannot. Preserve error behavior and logged OOS rollback if correspondence fails.
- **Representation correctness:** root decode identity, restored original identity on failure, and final destination identity are preserved without rewriting unrelated MVCC/header bits.
- **Metadata stability:** prove the class/schema locking and cache-lifetime contract covering selection, serialization and finalization. This review inspected context loading/cleanup, but did not prove all DDL invalidation and caller-lock paths. Existing late subclass locking must not be treated as that missing proof.
- **Attempt identity:** no stale result reused across rows, duplicate-key probes, retries, UPDATE source refresh, or reevaluation. NULL-context callers must be handled safely.
- **Force equivalence:** explicit child rejection, root outputs, destination locks, scan caches, function indexes, uniqueness/FK errors and cross-partition movement retain their current behavior.
- **Net benefit:** measure the whole proposed finalizer, including witness allocation/cleanup and OOS-key reads. Do not count the current entire early-route sample share as guaranteed recoverable runtime.

## Alternative: avoid early routing for proven non-OOS rows

This targets the measured small-inline case without removing final validation. But the trustworthy `has_oos` decision currently lives inside `heap_attrinfo_transform_to_disk_internal`, after uninitialized-value preparation and before OOS insertion (`heap_file.c:13510–13548`). Locator does not presently receive a side-effect-free certificate before choosing the owner.

A reusable layout/preparation result could allow ordinary non-OOS rows to serialize and route once, while OOS rows select an owner before writing chains. It must retain the layout rather than recompute it, preserve LOB/publication cleanup and correctly handle pending increments. This reopens the preparation/serialization design; a heuristic on caller payload lengths or schema thresholds is not an adequate substitute. It is not an approved fallback or a smaller proven patch.

## Verification plan if the user chooses a follow-up

No tests or experiments were run for this review. Before implementation, revise the spec and add explicit tests through the actual selection/final-force interface for:

- deliberately changed final keys/destinations and explicit-child mismatch;
- same-partition versus moved UPDATE, root/child representation differences, and cached versus temporary contexts;
- defaults, NULL, all legal key types, INCR/DECR and conversion boundaries;
- context clearing, sequential rows and duplicate-key probes to catch stale results;
- post-OOS errors, rollback, retries, LOB lifetime, indexes/FK errors and destination-lock failures;
- record-only callers and UPDATE reevaluation remaining on their established contracts;
- scoped route/codec/allocation counts plus paired final-revision timing for small inline, FORCE_OUTLINE, OOS keys, large values and nonpartitioned controls.

## Decision state

Confirmed by the user on 2026-09-09: **retain independent final record routing for this PR and defer destination reuse**. This reaffirms the existing specification and ADR; it does not approve a replacement interface, engine edits, more experiments, or a performance waiver. The reuse candidates and proof obligations above remain deferred proposals. Runtime and server lifecycle acceptance obligations remain open.
