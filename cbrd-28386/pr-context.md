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
- 2026-11-25: TC Branch Sync created [cubrid-testcases#4461](https://github.com/CUBRID/cubrid-testcases/pull/4461) and [cubrid-testcases-private-ex#5162](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5162); no TC changes are needed, keep both open until the merge handoff. `cubrid-pr-tc-base-check --pr 8752` passed.
- 2026-11-25T11:59Z: posted `/run all` ([comment](https://github.com/CUBRID/cubrid/pull/8752#issuecomment-7161763552)); gha-ci run [45609432740](https://github.com/CUBRID/cubrid/actions/runs/45609432740) attempt 1 picked up all six contexts; `cubrid-ci-watch` request #107.
- 2026-11-25: JIRA CBRD-28386 transitioned `Confirmed -> Develop` (`Start Develop`).
- 2026-11-25T17:22Z: CI run [45609432740](https://github.com/CUBRID/cubrid/actions/runs/45609432740) finished with `failure`.
  - `build (debug)`, `build (release)`, `test_medium`: pass.
  - `test_sql` (shard 09) and `test_sql_by_cci` (shard 09): 3 failures each, the same cases:
    `sql/_36_guava/cbrd_26795`, `sql/_36_guava/cbrd_27748`, `sql/_36_guava/cbrd_28121`.
    The same three cases fail on unrelated PRs: #8753 (run 45615415274, latch change) and the
    runs analyzed in `cbrd-28271/ci-analysis.md`, `cbrd-28094/ci-analysis.md`, `CBRD-28062/ci-analysis-7544aced71.md`.
    The diffs are in plan and trace output (`skip order by`, `oos time`), not in catalog data.
  - `test_shell`: 2 failures.
    - `shell/_06_issues/_26_2h/cbrd_27744_sa` (shard 23): checks 13 and 14, `expected '140001 2147483647 1', got '1 2147483647 1'`.
      The same values are a known develop regression, bisected to `e74826c46c` [CBRD-27562] in `cbrd-28271/ci-analysis.md`.
      That commit is in this PR's base. It also failed on 8 other recent runs.
    - `shell/_06_issues/_26_2h/cbrd_27937` (shard 40): `scenario 1: vacuum did not remove the relocated row: Num_relocated_recs=1`.
      It also failed on 3 other recent runs (45598914244, 45599229348, 45599541635). The check is on heap vacuum, not on catalog records.
  - Assessment (inference, no local rerun): all 5 failures are unrelated to this change.
  - `Check TC PRs` (TC Merge Gate): fails, as expected while TC PRs #4461 and #5162 are open.
  - Stopped after this run as the standing rule requires. No rerun, no follow-up push.

## Refresh onto develop (2026-11-26)

- Trigger: CBRD-28395 (`cbrd_27744_sa`) was resolved by the TC fix `CUBRID/cubrid-testcases-private-ex#5007` (`17566b7ee1`); not an engine defect.
  The `_36_guava` SQL answers were fixed by `cubrid-testcases#4474` and `#4475`.
- Why rebase instead of a TC-only sync plus `/run rerun`: the engine head was 17 commits behind develop, and newly merged TCs pair with engine commits missing from it (for example #5007 needs CBRD-28032 `59e357e086`).
- User approved the rebase, the `--force-with-lease` push, the TC syncs and one `/run all` in this session ("yes", then "yes" for the force-push).
- Engine: rebased onto develop `6f5ac7a9f9`; `855012ce0ae534c1a6bc8cb1bdcbcc106e2799da` force-pushed to `vk/CBRD-28386` with lease `d16738b08f`. Range-diff: patch unchanged.
- TC: merged develop into `tc/pr-8752` (public `517b82ddd`, private `b01b30c90`), regular push. `cubrid-pr-tc-base-check --pr 8752`: PASS.
- 2026-11-26T09:31:15Z: posted `/run all` ([comment](https://github.com/CUBRID/cubrid/pull/8752#issuecomment-7188100703)); gha-ci run [45792736707](https://github.com/CUBRID/cubrid/actions/runs/45792736707) attempt 1 picked up all six contexts; `cubrid-ci-watch` request #122.
- Residual risk: `cbrd_27780` (CBRD-28257, fix PR #8693 still open) fails intermittently on other runs.
- 2026-11-26T14:38Z: run [45792736707](https://github.com/CUBRID/cubrid/actions/runs/45792736707) finished with `failure`.
  - Pass: `build (debug)`, `build (release)`, `test_medium`, `test_sql`, `test_sql_by_cci`. The 3 `_36_guava` SQL cases now pass.
  - `test_shell`: 30 failed (`tc/pr-8752@b01b30c90`), all unclassified in `cubrid-tcr`.
    - 29 cases (answer diffs and `Internal Error` checks, e.g. `bug_bts_8375`, `issue_12506_show_heap_header/*`, `_08_I18N/_02_msg_lang/*`):
      the same 30-case set failed on four unrelated PRs triggered in the same window on develop `6f5ac7a9f9`
      (#8632 run 45790454567, #8654 run 45790935511, #8757 run 45791640273, #8754 run 45792059278).
      Later runs on other PRs (#8660, #8710, #8538) failed only `cbrd_25637_recovery`. Inference: a transient CI or environment fault in that window, not this change.
    - `shell/_40_guava/cbrd_25637/cbrd_25637_recovery` (core file): fails on nearly every recent run. Its TC (private-ex #5127) is on develop,
      but the engine PR it seems to need, #8725 [CBRD-28361], is still open. Inference: develop-side blocker.
  - `cbrd_27744_sa`, `cbrd_27937`, `cbrd_27780` passed.
  - `Check TC PRs` (TC Merge Gate) still fails while the TC PRs are open, as expected.
  - Stopped after this run as the standing rule requires.

## Second refresh onto develop (2026-11-28)

- Trigger: `cbrd_25637_recovery` fixed on develop by #8787 (`bcb0759333`); Commander approved resuming.
- Engine: rebased onto develop `08f8185500`. Conflict in `unit_tests/CMakeLists.txt` (develop added `UNIT_TEST_WORKER_POOL_ELASTIC` next to this PR's `UNIT_TEST_SYSTEM_CATALOG`); kept both. `dfdcbd4e480a7a3314047282eba35574f3acb623` pushed with `--force-with-lease` (lease `855012ce0a`).
- Local checks: debug build and install pass; `ctest` 76/77 with `test_catalog_record_gaps` passing. `test_oos_real_vacuum_latch_timeout_retry` timed out under parallel load and passed alone in 19 s, as before.
- TC: develop merged into `tc/pr-8752` (public `98b5438bc`, private `43802d098`); `cubrid-pr-tc-base-check --pr 8752`: PASS.
- 2026-11-28T07:25:11Z: posted `/run all` ([comment](https://github.com/CUBRID/cubrid/pull/8752#issuecomment-7235927452)); gha-ci run [46121128471](https://github.com/CUBRID/cubrid/actions/runs/46121128471) attempt 1 picked up all six contexts; `cubrid-ci-watch` request #130.
- CI result: run [46121128471](https://github.com/CUBRID/cubrid/actions/runs/46121128471) passed all six gha-ci contexts (`cubrid-ci-watch` #130 closed `success`). `Check TC PRs` fails as expected while TC PRs #4461 and #5162 are open.
- Approval gate: `cubrid-pr-approval-check --repo CUBRID/cubrid --pr 8752` PASS (`hornetmj` APPROVED, `lht1199` APPROVED).
- `pr-final-merge-handoff plan --pr 8752`: `review_ready: false`. Blockers: 2 unresolved Greptile P2 threads, and the squash message (supplied at `/cubrid-pr-merge`).
  - `PRRT_kwDOAxqu78675FDZ` (`test_catalog_record_gaps.cpp`): the test does not guard the zeroing of the unused second directory item, because `catalog_add_class_info` later writes the class-info item into that slot. Code check confirms it: a test-coverage gap, not an engine defect. The fix still keeps the first `RVCT_INSERT` image clean.
  - `PRRT_kwDOAxqu78675FDe` (`unit_tests/system_catalog/CMakeLists.txt`): the fixture scripts use `CUBRID` and `PATH` captured at configure time. Robustness of the opt-in test only.
  - Waiting for the user to decide: reply and resolve, or change the test (new push and CI).
