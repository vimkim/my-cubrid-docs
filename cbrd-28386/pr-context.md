# CBRD-28386 PR draft context

- Ticket: CBRD-28386
- SOURCE_COMMIT: `d16738b08f7b2a75bce2d23f58d34af6cd33c277`
- Source repository/branch: `vimkim/cubrid` `CBRD-28386` (remote `vk`); remote branch did not exist at preparation (2026-11-25)
- Base: `develop` (`ca39c2c6a4` at preparation)
- Target repository: `CUBRID/cubrid`
- Operation: create (no existing PR; `gh-pr-info` found none)
- Proposed title: `[CBRD-28386] Zero the bytes of catalog file records that no field covers`
- Docs task branch: `docs/cbrd-28386`; integration branch: `main`
- Body: `cbrd-28386/pr-body.md`; context: `cbrd-28386/pr-context.md`; detail: `cbrd-28386/verification-report.md` (not linked from the body)

## Proposed operations

1. Push `CBRD-28386` to `vk` (`github.com/vimkim/cubrid`).
2. Create a draft PR in `CUBRID/cubrid`: base `develop`, head `vimkim:CBRD-28386`, assignee `vimkim`, body `cbrd-28386/pr-body.md`.
3. Trigger `gha-ci` once with `/run all` after the TC baseline check, then wait and report.
4. Transition JIRA CBRD-28386 `Confirmed -> Develop`.

## Authorization

- 2026-11-25, in the session: the agent listed the decisions, and decision 1 was
  "push to `vk`, draft PR, `/run`, JIRA `Confirmed -> Develop`, approved together after review and commit".
  The user answered "1. yes 2. yes 3. CI에서는 어차피 안돌아간다. 4. 제외 5. 좋아."
- Decisions: no TC changes (2); the unit test stays opt-in (3); cleanup of existing databases is out of scope (4);
  `VPID` padding is recorded in Remarks only (5).

## Results

- 2026-11-25: pushed `CBRD-28386` to `vk`; remote head verified `d16738b08f7b2a75bce2d23f58d34af6cd33c277`.
- 2026-11-25: created draft PR [CUBRID/cubrid#8752](https://github.com/CUBRID/cubrid/pull/8752) (base `develop`, assignee `vimkim`).
  Body SHA-256 at upload: `6a239fb83954aa4455db58f6cee6e4085414ef7199e0e6fe0250e84a6b926cf4`; GitHub body matches the file.
- CI and JIRA results: see below.
