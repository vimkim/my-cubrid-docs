# Wayfinder Map — CBRD-27230 OOS UPDATE dedup

- label: `wayfinder:map`
- ticket: [CBRD-27230 [OOS] 변경 없는 OOS 값 중복 적재 방지](http://jira.cubrid.org/browse/CBRD-27230) (sub-task of CBRD-26978 OOS TODO epic)
- tracker: local markdown — tickets live in [`tickets/`](./tickets/); a ticket's `blocked-by` field holds the blocking edges; `assignee` is the claim; the frontier is every open ticket with empty `assignee` whose `blocked-by` tickets are all closed.
- charted: 2026-08-13 (worktree `CBRD-27230-oos-update-dedup` @ `725a32c6e` = `feat/oos` tip)

## Destination

A locked, JIRA-ready Korean design spec for CBRD-27230 — OOS UPDATE dedup: reuse existing OOS value chains for attributes **not assigned** by the UPDATE, with the cleanup architecture decided (OOS update log preferred) and its vacuum / crash-recovery / MVCC / replication safety verified on paper against `feat/oos`. The map ends when the spec is reviewed by the dev and uploaded to CBRD-27230, replacing its current 작성 중 description. Implementation is post-map work, not part of this effort.

## Notes

- **Skills every session must consult**: `cubrid-oos-context` (always, before anything); `grilling` + `domain-modeling` for HITL tickets; `cubrid-jira` for live ticket state (CLI currently missing — REST fallback: `curl http://jira.cubrid.org/rest/api/2/issue/CBRD-27230`); `cubrid-jira-issue-write` for the final spec.
- **Standing preference (team leader)**: prefer **option 2 — OOS update log** (vacuum cleans up chains when it encounters the log). Option 1 (generation-id comparison inside vacuum heap & forward-walk) is considered conceptually verbose and hard to maintain. Verify option 2 first; fall back only with evidence.
- **Verification depth**: paper verification against the actual `feat/oos` code. A prototype is an escape hatch if analysis hits a genuinely undecidable point, not a scheduled stop.
- **"Unchanged" semantics (decided)**: an attribute is unchanged iff it is **not assigned in the UPDATE statement**. No content-equality comparison (that would cost the `oos_read` the feature exists to avoid).
- **CBRD-26950 posture**: the generation identity stamp is a separate, high-priority effort owned by the same dev. This map designs in parallel; only final spec assembly waits for the locked 26950 design.
- **Language**: English for map/tickets/findings; Korean (English headers) for the final JIRA spec.
- **Research findings** land as markdown files under [`findings/`](./findings/), linked from their ticket (local-tracker adaptation of the research-branch convention).
- Key baseline facts: `heap_attrinfo_insert_to_oos` always allocates fresh chains; the vacuum forward-walk **relies** on old/new head-OID disjointness; SA_MODE eager delete (`heap_oos_delete_unreferenced`) already does an old∩new sharing check; ownership invariant to be superseded: "each OOS value chain is owned by exactly one logical heap-record version".

## Decisions so far

<!-- one line per closed ticket: gist + link -->

- [T1 — PG TOAST unchanged-value reuse on UPDATE](./tickets/T1-pg-toast-unchanged-value-reuse.md) — PG reuses via an 18-byte pointer `memcmp`, needs no generation id and no update log: the newest version owns the chunks and deletion is decided at UPDATE time with both images in hand. OOS's missing piece is exactly that decision persisted for vacuum — i.e. option 2's update log; stamp equality (option 1) says "delete" precisely when it must not.
- [T2 — OOS replication replay under chain reuse](./tickets/T2-oos-replication-replay-under-chain-reuse.md) — repl log ships no values, only `RVREPL_OOS_INSERT` LSA pointers the replica replays via its own `oos_insert`; today unassigned OOS attributes re-ship every UPDATE. Naive dedup breaks HA **loudly** (item-count vs stub-count mismatch stops apply) — the protocol needs a per-reused-attribute marker item + replica fixup from its own previous row version, and replica-side vacuum needs the same sharing protection as the master.
- [T3 — Cleanup paths under chain reuse](./tickets/T3-cleanup-paths-under-chain-reuse.md) — only the vacuum forward-walk breaks (silent data loss on reused chains); SA_MODE eager delete is already correct. **Option 1 refuted**: a reused chain has the same (head OID, generation) in undo image and live stub, so equality fires exactly when deleting is wrong. **Option 2 sound and simpler**: reuse the existing emitter-less `RVOOS_NOTIFY_VACUUM` record, remove the forward-walk entirely; pin two things — log appended *before* the heap update record, emission commit-conditional. Dedup needs **no** generation id; CBRD-26950 stays orthogonal.
- [T7 — Report the forward-walk rollback exposure as CBRD-27237](./tickets/T7-forward-walk-rollback-exposure.md) — analysis-only bug report written, grill-verified, and uploaded to [CBRD-27237](http://jira.cubrid.org/browse/CBRD-27237): the current forward-walk deletes a rolled-back UPDATE's old chains, which the restored live record still references. Option 2's commit-conditional emission fixes it for free — a tiebreaker input to the architecture decision.
- [T4 — Lock the cleanup architecture](./tickets/T4-lock-cleanup-architecture.md) — **option 2 locked** (all five contract clauses decided): notify record `RVOOS_NOTIFY_VACUUM` with `(head OOS OID, expected generation)` pairs, emitted as a commit-time postpone action registered before the heap update record; vacuum consumes per-record-sysop; forward-walk removed, DELETE untouched; CBRD-26950 is a hard prerequisite (sole source of retry idempotency); ownership invariant superseded (newest-version ownership, undo images never a deletion source); replication changes live in the same spec.

## Not yet specified

- **Test scenarios for the spec** — new OOS-CONTEXT §6 entries: reuse visible across versions, vacuum after dedup'd UPDATE, crash mid-update-with-reuse, rollback-then-vacuum (the CBRD-27237 case), HA replay of a deduped UPDATE. Graduates as part of drafting T6.

(The update-log record shape, replication protocol placement, and ownership-invariant wording graduated into the T4 resolution; write-path mechanics graduated into T8.)

## Out of scope

- **Content-equality dedup** (attribute assigned but value equal) — ruled out at charting; requires the read+compare the feature wants to avoid. May be a future ticket outside this map.
- **Cross-row value dedup / compression** — different features entirely (compression is deferred to type-layer per CTO direction).
- **Implementing the dedup** on this branch — the destination is the spec; implementation follows as ordinary work.
- **The CBRD-26950 fix itself** — separate high-priority effort; this map only consumes its locked design (see the capture ticket).
- **AS-IS defect found by T2** (not dedup work): the DELETE path can emit OOS repl items from a stale `thread_p->oos_oids` at the known `locator_add_or_remove_index` refactoring site, draining an empty LSA queue into an assert — deserves its own JIRA bug, independent of this map.
