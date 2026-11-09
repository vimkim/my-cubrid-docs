# PR draft context: CBRD-27781 / CBRD-27237 reclaim after finality

Draft PR created 2026-11-06: https://github.com/CUBRID/cubrid/pull/8434. Metadata for `pr-body.md`.

| Item | Value |
| --- | --- |
| Tickets | CBRD-27781 (primary), CBRD-27237 |
| Design | ADR-0008 "Reclaim OOS chains only after the delete is final", accepted 2026-11-05 (team lead, reported by the OOS owner); `cubrid-oos-context` branch `docs/adr-0008-reclaim-after-finality` (local, not merged) |
| Source commit | `0034bc2fb` (seven commits over the base: `d103d8b3d`, `c255c7c3b`, `f722cdd83`, `c2e93c66e`, `e1d5bb60d`, `b6bcc09c6`, `0034bc2fb`), branch `CBRD-27781-postpone-commit`; rebased 2026-11-09 |
| Base | `feature/oos-merge` at `95ff126a8464179a2fab3092b6f56468528ab954` (includes CBRD-27933 #8417) |
| Source repository / push routing | `vimkim/cubrid` (`vk`) for the head branch; target `CUBRID/cubrid` base `feature/oos-merge` |
| Observed remote head | `vk/CBRD-27781-postpone-commit` at `0034bc2fb` (force-pushed 2026-11-09 after the rebase) |
| Operation | draft PR #8434 created (approved 2026-11-06) |
| Proposed title | `[CBRD-27781] Reclaim OOS chains only after the delete is final` |
| Assignee | vimkim (default for creation) |
| Merge order (user decision 2026-11-05) | finish and verify this fix, then merge PR #7990 to develop |

## Operations (all approved and done 2026-11-06)

1. Integrate this docs task branch `docs/CBRD-27781-postpone-commit` into `my-cubrid-docs` `main` and push.
2. Push `CBRD-27781-postpone-commit` to `vk`.
3. Create the draft PR from `pr-body.md`, base `feature/oos-merge`.
4. Locally merge into `feature/oos-merge` (fast-forward after rebase) — separate approval under the user's Git workflow.

## Evidence locations

- Engine tests, TLA+ results, performance measurements: see `pr-body.md` Remarks and `perf.md` in this directory.
- TLA+ check update: `my-cubrid-formal-verification-skills` branch `adr0008-reclaim-after-finality` (local).
