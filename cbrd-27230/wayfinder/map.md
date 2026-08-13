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

(none yet)

## Not yet specified

- **OOS update log record shape** — fields, redo/undo kinds, idempotency under vacuum block retry, LSA sequencing vs replication logs; interplay with the deferred "move `oos_insert` to `attrinfo_force`" idea (OOS-CONTEXT Optimization Idea B). Graduates after the architecture locks.
- **Write-path mechanics of reuse** — where "attribute assigned" is known (`heap_attrinfo_set_uninitialized` and friends), and how the old OOS inline stub is carried into the new record version without an `oos_read`. Graduates after the architecture locks.
- **Spec fallout** — rewording of the ownership invariant in OOS-CONTEXT.md, and new §6 test scenarios (reuse visible across versions, vacuum after dedup'd update chains, crash mid-update-with-reuse). Graduates when the spec is drafted.

## Out of scope

- **Content-equality dedup** (attribute assigned but value equal) — ruled out at charting; requires the read+compare the feature wants to avoid. May be a future ticket outside this map.
- **Cross-row value dedup / compression** — different features entirely (compression is deferred to type-layer per CTO direction).
- **Implementing the dedup** on this branch — the destination is the spec; implementation follows as ordinary work.
- **The CBRD-26950 fix itself** — separate high-priority effort; this map only consumes its locked design (see the capture ticket).
