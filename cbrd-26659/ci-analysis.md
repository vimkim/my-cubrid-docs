# CBRD-26659 PR #8128 CI analysis

## Snapshot 2026-11-25: run 45578200568 attempt 1 (head `50f06c32ce`)

Analysis date: 2026-11-25 (Asia/Seoul). Reader: the PR #8128 author.

> **Warning report.** The exact-head evidence is incomplete. `cubrid-ci verify` returned
> `observation: incomplete`. The collector rejected the `test_sql` summary on an integrity
> check, so that suite has no validated summary. `report_mode.py` returned `warning`, with
> `regression_conclusions_allowed: false` and `comparison_scope: none`. No merge-base baseline
> exists. **This snapshot supports no regression or root-cause conclusion.** Section 4 gives
> triage hypotheses. Each hypothesis has a falsifier. No hypothesis is a CI verdict.

### 1. Result, scope, and next action

- **Run:** the full `/run` that the previous snapshot recommended. It ran after these changes:
  - The engine branch was synced to develop `e23905d89a` (merge commit `50f06c32ce`).
  - The OOS TCs on both `tc/pr-8128` branches were updated.
- **Change from the previous snapshot:** the validated failures went from 84 to 6.
  - `test_shell`: 43 → 3.
  - `test_sql_by_cci`: 41 → 3.
  - `test_medium`: passes 975/975 in both runs.
  - No OOS testcase fails.
- **Engine change:** in `src/`, the PR still adds only two things. Neither can change server
  behaviour.
  - A unit-test seam inside `#if defined(CUBRID_UNIT_TEST_ENABLED)`: `bridge_heap_oos_write_inline`
    in `heap_file.c`, +25 lines.
  - A two-line comment in `locator_sr.c`.

  `git diff e23905d89a..50f06c32ce` shows 9 files. The other 7 are in `unit_tests/oos/`.
- **Six failing cases.** Each one was merged to its TC repository's `develop` between
  2026-11-17 and 2026-11-25. This PR's TC branches change none of them.
- **Merge blockers:**
  - `gha-ci: test_shell` and `gha-ci: test_sql` are required checks, and both are red.
  - `Check TC PRs` fails because TC PRs #3688 and #4365 are open. Closing the TC PRs is
    deferred to the final handoff.
- **Recommended next action:** do **not** use `/run rerun` yet. The SQL diffs are
  deterministic plan and trace differences, so a rerun with the same build and testcases is
  expected to repeat them. Run the five non-registered cases locally on the installed head
  build to see whether they reproduce. A local failure would point to a develop-side issue for
  the owners of those testcases.

### 2. CI snapshot

| Suite | State | Verdict | Tests | Passed | Failed | Skipped | TC revision |
|---|---|---|---:|---:|---:|---:|---|
| `test_medium` | completed, validated | pass | 975 | 975 | 0 | 0 | public `1727bde9f` |
| `test_shell` | completed, validated | fail | 3731 | 3698 | 3 | 30 | private `4fdface37` |
| `test_sql_by_cci` | completed, validated | fail | 17931 | 17928 | 3 | 0 | public `1727bde9f` |
| `test_sql` | `collection_failed` | fail (status) | n/a | n/a | 3 (raw, unvalidated) | n/a | public `1727bde9f` |

- Run: <https://github.com/CUBRID/cubrid/actions/runs/45578200568>, attempt 1. Both builds passed.
- `test_sql` acquisition ledger: the integrity check failed. Shard 01's JUnit omits 19 testcases
  that its `summary_info` reports (3557 against 3538). The omitted testcases are nested
  `_05_plcsql` bug-fix cases. This is the same CTP nested-testcase JUnit omission as in the
  previous snapshot.
- The raw `collect/failed.list` from the gha-ci collect job lists 3 failures, all in shard 09.
  They are the same three paths that failed in `test_sql_by_cci`. This list is not validated.

### 3. Evidence scope

- PR head `50f06c32ce08b4d0f6bf6b200e16b152fb1620b1`. Target `develop` tip at collection
  `e23905d89a`, which is also the merge base.
- Collector `cubrid-ci`. Evidence directory:
  `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/50f06c32ce08b4d0f6bf6b200e16b152fb1620b1/`.
  Observation `20261125T122757.969116182Z-3904847-0`.
- Testcase provenance, read from the shard summaries:
  - Public `tc/pr-8128` at `1727bde9f`.
  - Private `tc/pr-8128` at `4fdface37`.

  The gha-ci collect job resets every shard to the planned TC commit. The private branch
  moved to `ea0c49b61` after the run, and that move does not affect this run.
- **Baseline: unavailable.** `cubrid-ci collect-base` resolved merge base `e23905d89a` and
  found no gha-ci status on it (`not_observed` for all four suites). None of the last 12
  develop commits has a gha-ci test status.
- **History: unavailable.** `cubrid-tcc 0.3.0 sync-data --run 45578200568 --suite test_shell`
  imported 0 observations and reported 3 unavailable files. `history` returned
  `UNKNOWN_HISTORY` with no occurrence for every failing case except one: `cbrd_26795` has
  PASS occurrences from October, on older TC revisions.

### 4. Failure inventory and triage hypotheses

| Suite | Testcase | Observed signature | `cubrid-tcr` | TC origin |
|---|---|---|---|---|
| shell | `shell/_06_issues/_26_2h/cbrd_27780/cases/cbrd_27780.sh` | checks 2 and 4: `S1HEAP=2` found in plaintext | `known`, rule `cbrd-28257-catalog-leak-s1-written` (CBRD-28257) | private #5015, 2026-11-20 |
| shell | `shell/_06_issues/_26_2h/cbrd_27744_sa/cases/cbrd_27744_sa.sh` | checks 13 and 14: `sa_crash serial after recovery: expected '140001 2147483647 1', got '1 2147483647 1'`; ids `1 70001` instead of `1 210001` | `no_match` | private #4809, 2026-11-24 |
| shell | `shell/_06_issues/_26_2h/cbrd_27650/cases/cbrd_27650.sh` | check 35: `S5: other sessions on the worker of dq at the failure: d1, expected none` | `no_match` | private #4876, 2026-11-17 |
| cci, sql | `sql/_36_guava/cbrd_26795/cases/cbrd_26795.sql` | `show trace` prints an extra `(oos time: ?, fetch: ?, ioread: ?)` on `SCAN (table: dba.px_wide_t)` | cci `known_job` | public #4272, 2026-11-25 |
| cci, sql | `sql/_36_guava/cbrd_27748/cases/cbrd_27748.sql` | the plan uses a direct `iscan` outer and `skip ORDER BY` instead of `temp(sort limit)` | cci `known_job` | public #4051, 2026-11-23 |
| cci, sql | `sql/_36_guava/cbrd_28121/cases/cbrd_28121.sql` | the plan omits `skip order by: true` | cci `known_job` | public #4229, 2026-11-23 |

The cci `known_job` verdicts come from rule `sql-by-cci-every-branch-20270108`. That rule covers
the whole optional `sql_by_cci` job. It does not explain these SQL diffs.

- **H1: develop-side failures, not PR-caused.** The PR source diff cannot reach the server
  paths that these cases exercise. Every failing case was last changed on TC develop within
  the last nine days.
  - *Falsifier:* the same TC revisions pass on a develop build at `e23905d89a` without the
    PR's unit-test seam.
- **H2: `cbrd_27744_sa` needs a develop fix that is newer than the merge base.** Develop commit
  `cbed1d5707` [CBRD-28073] ("Keep serial row storage form in NEXT VALUE") is after
  `e23905d89a`. The failure is a serial value lost after SA crash recovery. Confidence: low.
  - *Falsifier:* the case still fails on develop `cbed1d5707` or later.
- **H3: the three SQL plan and trace diffs come from develop changes that interact with each
  other.** `cbrd_27748` and `cbrd_28121` disagree about `skip order by` in opposite
  directions. `cbrd_26795` does not expect the OOS trace segment on a wide table. Open
  public TC PR #4323 [CBRD-28184] updates the trace answers of 198 SQL cases. It was not checked
  whether that PR covers `cbrd_26795`.
  - *Falsifier:* the cases pass on a develop build at the merge base with TC `1727bde9f`.
- **H4: `cbrd_27650` check 35 is a session-to-worker timing observation.** There is no history
  to support or reject flakiness.
  - *Falsifier:* a local repeat on the same build passes or fails consistently.

### 5. Actions

1. Run `cbrd_27744_sa`, `cbrd_27650`, `cbrd_26795`, `cbrd_27748` and `cbrd_28121` locally on
   the installed head build `50f06c32ce`. Use the focused native runners.
2. If they reproduce, report them to the owners of the respective develop TCs or engine
   changes. Then decide whether to wait for develop fixes and sync again before one
   `/run rerun 45578200568`.
3. Keep TC PRs #3688, #4365 and #5121 open until the final handoff.

## Snapshot 2026-11-25: run 45384316698 attempt 1 (head `b2440c26ed`)

Analysis date: 2026-11-25 (Asia/Seoul). Reader: the PR #8128 author.

> **Warning report.** The exact-head evidence is incomplete. `cubrid-ci verify` returned
> `observation: incomplete`, and the `test_sql` suite has no validated summary because the
> collector rejected it on an integrity check. `report_mode.py` permits only `warning`, with
> `regression_conclusions_allowed: false` and `comparison_scope: none`. **This snapshot supports no
> regression or root-cause conclusion.** Section 5 lists triage hypotheses. Each hypothesis has
> a falsifier. None of them is a CI verdict.

### 1. Result, scope, and next action

- **Engine change:** It cannot change server behaviour. In `src/`, the PR adds only a
  unit-test seam inside `#if defined(CUBRID_UNIT_TEST_ENABLED)` (`heap_file.c`, +25) and a
  two-line comment (`locator_sr.c`, +2). The other changes are in `unit_tests/oos/`.
- **Validated failures:** 84 in total. `test_shell` has 41 failures and 2 errors. `test_sql_by_cci`
  has 41 failures. `test_medium` passes 975/975. `test_sql` has no validated verdict.
- **Two triage groups.** Both are hypotheses (section 5):
  - **A: engine/TC version skew (53 validated failures).** `tc/pr-8128` was synced to TC
    `develop` as of 2026-11-24 18:36 KST. The engine head is based on develop `79eab331e5`
    (2026-11-23 15:41 KST). Each of the 55 failing non-OOS cases has a TC revision on
    `tc/pr-8128` that pairs with an engine commit not present in `b2440c26ed`.
  - **B: OOS testcase expectations predate develop's OOS (31 validated failures).** The
    OOS cases last passed on engine `e3589ae42d` (2026-10-27). Three OOS engine changes landed
    after that commit: CBRD-27781, CBRD-27259 and CBRD-27230.
- **Merge-base baseline:** run 45204898246 on `79eab331e5` (`partial_exact`). It has
  **0** shell failures and **2** cci failures. None of the 84 head failures appears in the baseline.
  The baseline used older TC `develop` revisions, so this comparison does not isolate the engine.
- **Recommended next action:** Do **not** use `/run rerun`. A rerun uses the same build and
  the same testcases, so the skew stays. Instead:
  1. Bring the engine branch up to the current develop tip (`bfb59bdd13` or later).
  2. Update the OOS cases on both `tc/pr-8128` branches (section 6).
  3. Trigger one full `/run` through `cubrid-ci-trigger`.

  Steps 1 and 3 push code and post a CI command, so they need approval.

### 2. CI snapshot

PR [CUBRID/cubrid#8128](https://github.com/CUBRID/cubrid/pull/8128) targets `develop`. The head ref is
`CBRD-26659-oos-testcases-handover` at `b2440c26ed17b7f246b027724d439a797acf2e1c`. The run is
[45384316698](https://github.com/CUBRID/cubrid/actions/runs/45384316698), attempt 1.

| Suite | Commit status | Collection | Summary | Counts (planned/run/passed/fail/err/skip) |
| --- | --- | --- | --- | --- |
| test_medium | SUCCESS | completed | validated | 975/975/975/0/0/0 |
| test_shell | FAILURE | completed | validated | 3714/3684/3641/41/2/30 |
| test_sql | FAILURE | **collection_failed** (integrity) | absent | no validated counts |
| test_sql_by_cci | FAILURE | completed | validated | 17910/17910/17869/41/0/0 |

Other checks: `build (debug)` and `build (release)` succeeded. `code-style` and `cppcheck` succeeded.
`github-actions: Check TC PRs` (TC Merge Gate) reports **FAILURE**. This gate result is expected
while the TC PRs stay open, and it is separate from the regression results (section 7).

### 3. Evidence scope

- Collector: `cubrid-ci 0.2.0 (00205d576de0, release)`. `verify` exit 3, with `identity: established`,
  `manifest: validated`, `requested_summaries: partial` and `result_matches_observation: true`.
- Evidence root:
  `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/b2440c26ed17b7f246b027724d439a797acf2e1c`.
  Observation: `observations/20261125T072410.767079128Z-2961939-0`.
- Build provenance: every validated shard's `build.sha` is `b2440c26ed`. Shell ran a debug build
  and cci ran a release build.
- Testcase revisions:
  - Private shell: `7ff8ef631505` on `tc/pr-8128`. This is the tip of
    [private-ex#4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365).
  - Public SQL/cci: `662c4581d26f` on `tc/pr-8128`. This is the tip of
    [cubrid-testcases#3688](https://github.com/CUBRID/cubrid-testcases/pull/3688).
- `test_sql` diagnostic (`kind: integrity`): "result identity mismatch: shard 01 JUnit omits 19
  testcases that summary_info reports (summary_info 3556/1/0, JUnit 3537/1/0)". The 19 omitted
  testcases are all under nested directories `sql/_05_plcsql/_01_testspec/_05_bug_fix/cbrd-*/cases/`.
  This matches the CTP nested-testcase JUnit defect that
  [CBRD-26659-sql-count-discrepancy_20261030_run40837919358_codex.md](CBRD-26659-sql-count-discrepancy_20261030_run40837919358_codex.md)
  reproduced. The raw `test_sql` JUnit is retained, but it is **unvalidated**. Section 4c lists it as a
  lead only.
- Tools: `cubrid-tcr 0.1.0` and `cubrid-tcc 0.3.0`. Chronicle synced this run for `test_shell` and
  `test_sql` (`--revisit-limit 0`). `test_sql_by_cci` has no Chronicle suite.

### 4. Failure inventory

Labels used below:

- `cubrid-tcr`: the verdict from `cubrid-tcr check --ci-attempt ... --record`.
- `Base`: the result for the same path in merge-base run 45204898246. In that run,
  `add` means the path did not fail.
- `Skew commit`: the engine commit that pairs with the case's latest TC revision on `tc/pr-8128`.
  This commit is **missing** from `b2440c26ed`. It is a hypothesis input, not a verdict.

Counts: 84 validated head failures. `also_observed_on_base` = 0. `additional_on_head` = 84, but
with different TC revisions (see section 6). `base_only` = 2 (cci: `cbrd_28202.sql`, `cbrd_27752.sql`).

#### 4a. test_shell (43: 41 failures and 2 errors). `cubrid-tcr`: `no_match` for all 43.

**Group A: non-OOS (18)**

| Testcase | Result | Observed signature | Skew commit (missing) | Chronicle history |
| --- | --- | --- | --- | --- |
| `_06_issues/_26_1h/cbrd_26942/cases/cbrd_26942.sh` | fail | no `Transaction lock` entry in lockdb | CBRD-27710 `2da821f3b9` (TC `c142d2069`) | none |
| `_06_issues/_26_2h/cbrd_27744/cases/cbrd_27744.sh` | fail | serial ids issued twice | CBRD-27744 `44e9290f38` | none |
| `_06_issues/_26_2h/cbrd_27744_sa/cases/cbrd_27744_sa.sh` | fail | serial value mismatch | CBRD-27744 `44e9290f38` | none |
| `_06_issues/_26_2h/cbrd_27581/cases/cbrd_27581.sh` | **error** | `NOK timeout` (1203 s) | CBRD-27581 `1bdecddb89` | none |
| `_06_issues/_26_2h/cbrd_28061/cases/cbrd_28061.sh` | fail | insert did not reuse first partial page | CBRD-28061 `9ad04814b0` | none |
| `_40_guava/cbrd_27344/cases/cbrd_27344.sh` | fail | `lock_timeout_in_secs=-1` parameter check | CBRD-27344 `a5f5ac2059` | none |
| `_06_issues/_11_2h/bug_bts_5423/cases/bug_bts_5423.sh` | fail | case 6 NOK | CBRD-27344 `a5f5ac2059` (TC `07af85a51`) | 12 F / 474 P (develop 10) |
| `_40_guava/cbrd_26111/cases/cbrd_26111.sh` | fail | cases 1–2 NOK | CBRD-27344 `a5f5ac2059` (TC `07af85a51`) | 20 F / 315 P (develop) |
| `_40_guava/cbrd_27579_sa/cases/cbrd_27579_sa.sh` | **error** | trigger SP action error | CBRD-27579 `4b0fe300b1` | none |
| `_40_guava/cbrd_27579_javasp/cases/cbrd_27579_javasp.sh` | fail | case 1 NOK | CBRD-27579 `4b0fe300b1` | none |
| `_40_guava/cbrd_27789/cases/cbrd_27789.sh` | fail | UPDATE not refused (300 rows) | CBRD-27579 `4b0fe300b1` (TC `8c7d7c74f`) | none |
| `_40_guava/cbrd_26076/cbrd_26076_block/cases/cbrd_26076_block.sh` | fail | trigger PL block action error | CBRD-27579 `4b0fe300b1` (TC `8c7d7c74f`) | 4 F / 4 P (develop) |
| `_06_issues/_17_1h/cbrd_20149_filter/cases/cbrd_20149_filter.sh` | fail | case 1 NOK | CBRD-27579 `4b0fe300b1` (TC `8c7d7c74f`) | 29 F / 469 P (develop) |
| `_40_guava/cbrd_27752/cases/cbrd_27752.sh` | fail | T2 never waited for T1 self-lock | CBRD-27710 `2da821f3b9` (TC `c142d2069`) | none |
| `_40_guava/cbrd_26503/cases/cbrd_26503.sh` | fail | TP6 lock wait mismatch | CBRD-27710 `2da821f3b9` (TC `c142d2069`) | none |
| `_39_fig_cake/cbrd_24479/cases/cbrd_24479.sh` | fail | case 1 NOK | CBRD-27710 `2da821f3b9` (TC `c142d2069`) | 12 F / 472 P (develop 10) |
| `_40_guava/cbrd_27171/cases/cbrd_27171.sh` | fail | extraction plan mismatch, cases 7 and 10 | CBRD-28076 `ff275bd0c7` (TC `bc45b64b1`) | 6 F / 326 P (develop) |
| `_24_apricot/_01_cursor_holdability/_01_cursor_functional/cases/_01_cursor_functional.sh` | fail | case 1 NOK | APIS-1106 `e3bbe664b5` (JDBC submodule; TC `ea99bac92`) | 4 F / 479 P (develop) |

**Group B: OOS cases added by this PR (25)**. All are under `shell/_40_guava/`. Chronicle shows 11 earlier
PASS results on PR #8128 when the PR targeted `feature/oos-merge` (engine `c4c4f5c5ed`/`e3589ae42d`,
October 26–29). `record_keys` also has 1 earlier failure.

| Testcase (`cbrd_26659_*`) | Observed signature |
| --- | --- |
| `owner_drop`, `read_paths` | `wrong file/chunk/slot model: expected [1,6,57372]`, observed `oos_recs_sumlen` 57420 |
| `schema_cs` | expected `[1,2,9664]`, observed 9680 |
| `representation_chunks` | expected `[1,1,3032]`, observed 3040 |
| `lob_locators` | expected `[1,2,264]`, observed 280 |
| `partition_owner` | `destination ownership mismatch`, plus expected `[1,1,5032]` and observed 5040 |
| `fk_key_single_noaction`, `fk_key_single_delete_null`, `fk_key_composite_noaction`, `fk_key_composite_default`, `fk_key_composite_cascade_block`, `fk_payload_single_cascade_block`, `fk_payload_composite_cascade`, `fk_payload_composite_restrict`, `fk_payload_composite_delete_null`, `fk_payload_composite_update_null` | `FK model/state/ownership assertion failed` (physical row/owner snapshot mismatch) |
| `alt_duplicate_select`, `alt_duplicate_set`, `alt_duplicate_values`, `alt_merge`, `alt_replace_values` | `Alternative write model/state assertion failed` |
| `schema_policy` | `invalid explicit fixed policy unexpectedly accepted` |
| `transactions` | record size 17548 exceeds the maximum record size (16236) after OOS movement |
| `snapshot_visibility` | controller exit 1 (`oos11.controller.log`) |
| `record_keys` | `oos_record_boundaries/controller.sh:10: exit=1` |

#### 4b. test_sql_by_cci (41 failures). `cubrid-tcr`: `known_job` for all 41.

All 41 failures match rule `sql-by-cci-every-branch` (job contains `sql_by_cci`, no issue, expires
2026-12-09, **flagged "expires within 14 days"**). Under the known-job rule, a symptom outside the rule
still needs analysis. The 6 OOS cases are new testcases, so the rule does not explain them.

- **Group A: non-OOS (35)**. Each case's latest TC revision since base TC `2a0df3c51` pairs with a missing
  engine commit:
  - CBRD-28076 `ff275bd0c7` (TC `6b13269a3`): `bug_bts_4711`, `_t4_10_keylimit_1`, `dnf`,
    `cbrd_25447`, `cbrd_26266`, `cbrd_26900`, `cbrd_27306`, `cbrd_27855`, `cbrd_28076`.
  - CBRD-27748 `30eb0c4b8b` (TC `98b4755b9`): `bug_bts_4813`, `20567_limit_1`,
    `20567_limit_{DELETE,UPDATE}_hostvar`, `20567_limit_SELECT_hostvar_{1,2}`, `cbrd_27748`.
  - CBRD-27579 `4b0fe300b1` (TC `db73ab791`): `26_recursive_function`, `cbrd_26165`,
    `cbrd_27299_plcsql`, `cbrd_27579_{loop,rule1,rule2,rule3,rule3_trigger,view_replaced_sp}`.
  - Missing ticket fixes: `cbrd_27744` (`44e9290f38`), `cbrd_27820`/`cbrd_27820_1` (`4f35d3d541`),
    `cbrd_28078` (`c84275722d`), `cbrd_28104` (`051a19c358`), `cbrd_28174` (`0e6413111d`),
    `cbrd_28295` (`19d1d8e1d9`), `cbrd_28173` (`fde470c3a0`), `cbrd_28193` (`131af8f86e`),
    `cbrd_28246` (`8e052e99c5`).
- **Group B: OOS (6)**, all in `sql/_36_guava/cbrd_26659/cases/`:
  - `oos_policy_syntax`, `oos_storage_policy`: `create table ...(c int storage default)` is
    expected to fail with `-493`/`-495`. It now succeeds (`0`), and `bit(128) storage default`
    returns `-494`.
  - `oos_schema`: expected `-495`, observed `-1046`.
  - `oos_sql05_bigone`: the insert of a 17500-byte fixed payload returns `Error:-1397`, so the row
    count is 0 instead of 1.
  - `oos_sql07_read_paths`: numeric scale prints `40.0` instead of `40.00`. This is a CCI formatting
    difference.
  - `oos_dml_forms`: one extra blank result line. This is a CCI formatting difference.

#### 4c. test_sql: unvalidated lead (not counted)

The raw retained JUnit (unvalidated) lists 40 failures and **2 `core file found` errors**
(`_36_guava/cbrd_27579/cases/cbrd_27579_rule1.sql` and `_36_guava/cbrd_27748/cases/cbrd_27748.sql`).
The other entries largely match the cci list. The raw list also shows that:

- 4 OOS cases fail under CSQL too (`policy_syntax`, `schema`, `sql05_bigone`, `storage_policy`).
- `oos_dml_forms` and `oos_sql07_read_paths` do **not** appear in it. This is consistent with a
  CCI-only formatting difference.
- `cbrd_27762.sql` appears only here. It has no TC change since the base TC, and its cause is unknown.

These lines are leads only. No `test_sql` verdict is claimed.

### 5. Triage hypotheses (not CI conclusions)

#### H-A: engine/TC version skew. PR relation: `unlikely`. Confidence: high.

- Observed facts:
  - TC branch `tc/pr-8128` (private `7ff8ef6315`, public `662c4581d2`) contains TC `develop`
    up to 2026-11-24 18:36 KST (private merge base `07af85a51`, public `36ccc6914`).
  - The engine head's base is `79eab331e5` (2026-11-23 15:41 KST). `origin/develop` is 42
    commits ahead (tip `bfb59bdd13`).
  - Every Group A case's latest TC revision pairs with a develop engine commit that is not
    an ancestor of `b2440c26ed` (verified with `git merge-base --is-ancestor`).
  - The merge-base run, with older TC revisions, showed 0 shell failures.
  - The PR's `src/` diff has no runtime effect.
- Inference: The failing cases test behaviour that the PR head does not have yet.
- Unknown: whether develop at `bfb59bdd13` passes these cases. No `gha-ci` status is attached
  to recent develop commits.
- Falsifier: After the engine branch reaches the develop tip with the same TC revisions,
  a Group A case still fails.
- Next action: Bring the engine branch up to develop. This needs push approval.

#### H-B: OOS TC expectations predate develop's OOS engine. PR relation: `direct` (the PR's own TCs). Confidence: high for the size model, medium for the rest.

- Observed facts:
  - The OOS cases passed 11 times on engine `e3589ae42d` and earlier.
  - Three OOS commits on `feature/oos-merge` came after `e3589ae42d` and reached develop through the
    OOS merge `68a9c7766f` (#7990, 2026-11-20):
    - CBRD-27781 [#8434](https://github.com/CUBRID/cubrid/pull/8434) `e1ba4675f2` adds
      `LOG_LSA next_chunk_stamp` (8 bytes) to `struct oos_record_header`
      (`src/storage/oos_file.hpp:37` at `79eab331e5`), and makes reclaim wait until the delete is final.
    - CBRD-27259 [#8416](https://github.com/CUBRID/cubrid/pull/8416) `c793adf908` adds STORAGE
      FORCE_INLINE and fixed-type STORAGE DEFAULT.
    - CBRD-27230 [#8559](https://github.com/CUBRID/cubrid/pull/8559) `b43275e944` makes UPDATE reuse
      unassigned OOS chains.
  - The size deltas match exactly 8 bytes per chunk: 57420−57372 = 48 = 6×8; 280−264 = 16 = 2×8;
    9680−9664 = 16 = 2×8; 3040−3032 = 8; 5040−5032 = 8.
  - Fixed-type `storage default` is now accepted (`0` instead of `-493`/`-495`). This is the
    behaviour that CBRD-27259 introduces.
- Inference:
  - Size models (owner_drop, read_paths, schema_cs, representation_chunks, lob_locators,
    partition_owner): the TC expectations are stale for the new header.
  - Policy answers (policy_syntax, storage_policy, schema_policy, schema): the expected errors are
    stale for CBRD-27259.
  - FK and alt-write model/state assertions: these likely encode the immediate-reclaim and
    no-reuse model that CBRD-27781 and CBRD-27230 replaced. This is not verified per case.
  - `transactions`, `sql05_bigone` (`-1397`/record too large), `snapshot_visibility`,
    `record_keys`, `partition_owner` ownership: the cause is **unknown**. These may be TC geometry
    that the new header pushed past the page limit, or an engine contract difference. They need a
    focused native run on the develop engine.
- Falsifier: A focused native run of a size-model case on develop `79eab331e5` observes the old
  sum. Or the FK/alt diffs show OOS chain ownership violations, not timing or reuse differences.
- Next action: For each case, decide between updating the TC and reporting an engine issue,
  using `cubrid-test-shell-run` / `cubrid-test-sql-run` on the develop engine. Then add
  `.answer_cci` for the two CCI-only diffs.

#### test_sql collection integrity: collector/CTP limitation. Not a regression signal.

- Next action: None for the PR. The nested-testcase JUnit omission is the known CTP defect.
  A future CI run produces the same mismatch until CTP is fixed.

### 6. Baseline comparison

- Pins: PR 8128, head `b2440c26ed`, target `develop` (`79eab331e5` recorded by the collector),
  merge base `79eab331e5` (`git merge-base --all`). Observed 2026-11-25T07:24:55Z.
- Baseline run [45204898246](https://github.com/CUBRID/cubrid/actions/runs/45204898246) attempt 1.
  `verify`: `baseline: partial_exact`. Medium, shell and cci are validated. `test_sql` is absent.

| Suite | Base counts (planned/passed/fail/err/skip) | Base TC revision | Head TC revision |
| --- | --- | --- | --- |
| test_medium | 975/975/0/0/0 | public `2a0df3c51f` (`develop`) | public `tc/pr-8128` |
| test_shell | 3673/3643/0/0/30 | private `a00a243a53` (`develop`, 2026-11-23 15:40) | private `7ff8ef6315` (+16 commits) |
| test_sql_by_cci | 17862/17860/2/0/0 | public `2a0df3c51f` (2026-11-23 14:59) | public `662c4581d2` (+21 commits) |

- Base-only failures (cci): `sql/_13_issues/_26_2h/cases/cbrd_28202.sql` and
  `sql/_36_guava/cbrd_27752/cases/cbrd_27752.sql`.
- Limitation: The TC inputs differ, because the base TC is an ancestor of the head TC. The gate is
  `comparison_scope: none`. Therefore "additional_on_head" does not attribute any failure to the engine diff.

### 7. Companion TC PR status (2026-11-25)

| PR | State | Head | Tip | Size | Notes |
| --- | --- | --- | --- | --- | --- |
| [cubrid-testcases#3688](https://github.com/CUBRID/cubrid-testcases/pull/3688) | OPEN, draft | `tc/pr-8128` → develop | `662c4581d2` (2026-11-24 "Reapply PR #8128 OOS SQL testcases on develop") | 60 files, +6472 | Tested by this run (cci shards) |
| [cubrid-testcases-private-ex#4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365) | OPEN, ready | `tc/pr-8128` → develop | `7ff8ef6315` (2026-11-24 "Reapply PR #8128 OOS shell testcases on develop") | 237 files, +44978 | Tested by this run (shell shards) |
| [cubrid-testcases-private-ex#5121](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5121) | OPEN, draft | `CBRD-26659-oos-shell-heavy` → develop | `b9e6b81b2a` | 74 files, +33443 | Moves 38 passing OOS cases into `shell_heavy`; based on evidence from engine `e3589ae`. Not exercised by `gha-ci`. |

TC Merge Gate (`Check TC PRs`) is FAILURE because these PRs are open. Per the testcase lifecycle,
this result is deferred to the final merge handoff. It is not a regression failure, and the PRs stay
open. The #5121 heavy cases were validated on `e3589ae` only. They probably carry the same H-B
staleness for develop's OOS format.

### 8. Prioritized actions

1. **(Approval needed: push.)** Bring the PR branch `CBRD-26659-oos-testcases-handover` up to the
   current develop tip (rebase, or merge develop). This removes Group A (53 validated failures)
   if H-A holds.
2. **(Local, then TC push.)** Run the Group B OOS cases natively against the develop engine. Then:
   - Update the size models (+8 B per chunk).
   - Update the policy answers for CBRD-27259.
   - Update the FK/alt models for deferred reclaim and chain reuse.
   - Add `.answer_cci` for `oos_dml_forms` and `oos_sql07_read_paths`.
   - Triage `transactions`, `sql05_bigone`, `snapshot_visibility`, `record_keys` and
     `partition_owner` ownership before deciding between a TC change and an engine issue.

   Apply the same review to #5121.
3. **(Approval needed: `/run`.)** After steps 1–2, trigger **one full `/run`** with `cubrid-ci-trigger`.
   `/run rerun 45384316698` is not recommended, because it reuses the same build and testcases.
4. Follow-up outside this PR:
   - Rule `sql-by-cci-every-branch` expires on 2026-12-09. Extend or retire it.
   - The CTP nested-testcase JUnit omission keeps `test_sql` collection unvalidated.

### 9. Evidence files

- Head bundle: `<evidence root>/providers/github-actions/runs/45384316698/attempts/1/{test_medium,test_shell,test_sql_by_cci}/summary.json`.
  Failure texts are in `failures/<stable_id>/{message.txt,diff.txt}`. Raw `test_sql` shards are under
  `test_sql/raw/shards/*/linux_sql_64bit_optdebug.xml` (unvalidated).
- Baseline bundle:
  `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/79eab331e54349812e98cace6d0aeaeebf123d95/providers/github-actions/runs/45204898246/attempts/1/`.
- `cubrid-tcr` check output was recorded with `--record`. No signature matched (shell: `no_match`
  ×43; cci: `known_job` ×41).
- Not run: `cubrid-jira-dup`. No failure was classified as a new-bug candidate under the warning gate.
