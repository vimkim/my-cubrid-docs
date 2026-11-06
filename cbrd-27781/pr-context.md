# PR draft context: CBRD-27781 / CBRD-27237 reclaim after finality

Draft PR created 2026-11-06: https://github.com/CUBRID/cubrid/pull/8434. Metadata for `pr-body.md`.

| Item | Value |
| --- | --- |
| Tickets | CBRD-27781 (primary), CBRD-27237 |
| Design | ADR-0008 "Reclaim OOS chains only after the delete is final", accepted 2026-11-05 (team lead, reported by the OOS owner); `cubrid-oos-context` branch `docs/adr-0008-reclaim-after-finality` (local, not merged) |
| Source commit | `2e32517bb` (five commits over the base: `62d0b35b6`, `3e8072f56`, `6ac2d7de6`, `9406a0f71`, `2e32517bb`), branch `CBRD-27781-postpone-commit` |
| Base | `feature/oos-merge` at `d52b1889e907abcf84190ec504dde3bc93de260d` (the PR #7990 head branch) |
| Source repository / push routing | `vimkim/cubrid` (`vk`) for the head branch; target `CUBRID/cubrid` base `feature/oos-merge` |
| Observed remote head | `vk/CBRD-27781-postpone-commit` at `2e32517bb` (pushed 2026-11-06 after review fixes) |
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
