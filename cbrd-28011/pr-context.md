# CBRD-28011 PR draft context

- Ticket: CBRD-28011 (sub-task of CBRD-26978; request: CUBRID/cubrid#7990 comment 6625292994)
- SOURCE_COMMIT: a4fec6f8e26a36834c3dde4df0ed0af5ecc6d914
- Source: vimkim/cubrid branch `CBRD-28011-oos-sql-trace` (remote branch absent at preparation, 2026-11-11)
- Base: CUBRID/cubrid `feature/oos-merge` at 67220b7e230ff1587ba5940001d72e10477a1fc4
- Target: CUBRID/cubrid, operation `create` (no existing PR for this head)
- Proposed title: `[CBRD-28011] Show OOS reads separately in SQL trace`
- Docs task branch: `docs/CBRD-28011-pr-body`; integration branch: `main`
- Paths: `cbrd-28011/pr-body.md`, `cbrd-28011/pr-context.md`, `cbrd-28011/README.md`
- Scheduling: authorized follow-up, not an agreed mandatory #7990 merge gate.

## Proposed operations

1. Rebase `docs/CBRD-28011-pr-body` onto local `main`, fast-forward merge, push `main` to origin.
2. Push source branch `CBRD-28011-oos-sql-trace` to `vk`.
3. Create draft PR vimkim:CBRD-28011-oos-sql-trace -> CUBRID/cubrid:feature/oos-merge with the body file unchanged, assigned to `vimkim`.

Not included: CI trigger, TC PR edits, JIRA updates, reviewer messages.

## Publication record (2026-11-11)

- Body fingerprint (sha256 prefix): 6aae2ef8d7dee573.
- Op 1 (docs merge/push) deferred: docs `main` checkout had unrelated uncommitted changes.
- Op 2 done: `vk/CBRD-28011-oos-sql-trace` = a4fec6f8e26a36834c3dde4df0ed0af5ecc6d914.
- Op 3 done: draft PR https://github.com/CUBRID/cubrid/pull/8491, assigned to vimkim.

## Revision 2 (body update proposal, 2026-11-11)

- Operation: update existing PR #8491 body only; title and draft status unchanged; no source push.
- Remote body before update equals revision 1 (`b961c46:cbrd-28011/pr-body.md`).
- Changes: release-build OOS fetch composition (measured: 3 fetches for one chunk, +1 per chunk; 800 for 200 rows x 2 chunks), debug-build numbers kept for contrast, TC reference CUBRID/cubrid-testcases#4148 (local native run PASS).
