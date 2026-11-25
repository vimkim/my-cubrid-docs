# CI analysis: PR #8632 at `7544aced71` (warning report)

> **This snapshot does not support a regression or root-cause conclusion.**
> The head observation is `incomplete`. The `test_sql` evidence failed the
> collector integrity check, and the merge-base baseline is `unavailable`
> because its CI run is still running. `report_mode.py` permits only a warning
> report (`mode: warning`, `regression_conclusions_allowed: false`,
> `comparison_scope: none`). The attributions below are labeled inferences
> and are not verdicts.

## Result

- **Red regression suites:** `test_shell` (2 failures), `test_sql_by_cci`
  (3 failures, optional suite), and `test_sql` (CI FAILURE, evidence not
  validated). `test_medium` passes (975/975).
- **PR relation of every validated failure: `unlikely` (inference, medium
  confidence).** The PR adds `oos_trigger_threshold`. Its default value `0`
  keeps the earlier automatic OOS target, and CI runs with the default. Each
  failing testcase also fails with the identical signature on other PRs that
  do not contain this change.
- **Shell failures (`cbrd_27744_sa`, `cbrd_27650`): probable develop change.**
  The same PR source diff on base `424cab5ef6` (head `dc1b83a33b`, runs
  45549760101 and 45567806032) passed both testcases. The testcase files were
  byte-identical. On base `cbed1d5707` both fail. PRs #8735 and #8736 on base
  `bfb59bdd13` pass both. PR #8128 on base `e23905d89a` fails both with the
  identical signatures. Inference: a change in `bfb59bdd13..e23905d89a`
  (8 develop commits) is the probable cause. `cubrid-tcr` verdict: `no_match`.
- **`test_sql_by_cci` failures (`cbrd_26795`, `cbrd_27748`, `cbrd_28121`):
  answer drift on develop.** `cubrid-tcr` verdict: `known_job` (rule
  `sql-by-cci-every-branch-20270108`, no tracking issue). The same three
  diffs occur on PRs #8128, #8735, and #8736. The unvalidated raw `test_sql`
  JUnit of this run shows the same three testcases failing.
- **TC gate (separate from regression):** `github-actions: Check TC PRs` fails
  with `TC Merge Gate FAILED — TC changes are not on TC develop yet`. This is
  expected while TC isolation holds. Finalize it at the final merge handoff.
- **Rerun:** do not rerun automatically. The shell failures are not `known`
  and have no verified flaky history. They reproduce on newer develop bases,
  so a `/run rerun 45598259772` will probably fail again.
- **Next action:** wait for the merge-base run
  [45644791295](https://github.com/CUBRID/cubrid/actions/runs/45644791295) on
  `cbed1d5707`, then run `cubrid-ci collect-base` and `verify` again. If the
  baseline shows the same five signatures, record them as develop issues
  (see the JIRA candidates below) and rerun or re-trigger only after a fix or
  an approved known-issue rule.

## CI snapshot

Observed 2026-11-25T15:55Z (UTC). Run
[45598259772](https://github.com/CUBRID/cubrid/actions/runs/45598259772),
attempt 1, triggered by `/run all` at 2026-11-25T10:46:57Z
(`cubrid-ci-watch` request 104). There were no `/run rerun` comments for this
head.

| Suite | CI state | Collection | Verdict | Counts (planned / run / passed / failures / errors / skipped) |
|---|---|---|---|---|
| `test_medium` | SUCCESS | completed, validated | pass | 975 / 975 / 975 / 0 / 0 / 0 |
| `test_shell` | FAILURE | completed, validated | fail | 3702 / 3672 / 3670 / 2 / 0 / 30 |
| `test_sql` | FAILURE | `collection_failed` (integrity) | no validated verdict | unknown |
| `test_sql_by_cci` | FAILURE | completed, validated | fail | 17907 / 17907 / 17904 / 3 / 0 / 0 |

Other checks on the pinned head: `build (debug)` and `build (release)` pass.
`code-style`, `cppcheck`, `license`, and `memory-monitor-check` pass.
`Check TC PRs` fails (TC gate, above).

## Evidence scope

- PR: [CUBRID/cubrid#8632](https://github.com/CUBRID/cubrid/pull/8632),
  `[CBRD-28062] Make the OOS trigger threshold configurable`, base `develop`.
- Pinned head: `7544aced71efa25c39a7ae967febbe308d975d89`. The shard build
  provenance of all validated suites records this Engine SHA.
- Testcase revisions: `cubrid-testcases` `5862efae387c454231ce8b264e6c21a9ee281f53`
  (`tc/pr-8632`, for medium, sql, and sql_by_cci);
  `cubrid-testcases-private-ex` `a02fa4d523bd35195f969a6e3bcf8844042fde2b`
  (`tc/pr-8632`, for shell).
- Collector: `cubrid-ci 0.2.0 (00205d576de0, release)`, with `verify`.
  Collection exit `4` (integrity failure in `test_sql`), verify exit `3`.
- Head observation:
  `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8632/7544aced71efa25c39a7ae967febbe308d975d89/observations/20261125T155538.476983951Z-1809446-0`.
- Assessment: `identity: established`, `observation: incomplete`,
  `manifest: validated`, `requested_summaries: partial`, `baseline: unavailable`.
- Other tools: `cubrid-tcr 0.1.0`, `cubrid-tcc 0.3.0`, `cubrid-jira-dup`.

### Acquisition ledger

All 10 `test_sql` shards (`00` to `09`) are `retained`. A retained shard is
raw evidence, not a suite verdict. The binary budget was not used
(0 of 536,870,912 bytes).

### Structured diagnostic (`test_sql`)

`kind: integrity`, `diagnostic: identity_or_integrity`: "shard 01 JUnit omits
19 testcases that summary_info reports (summary_info 3557/0/0, JUnit
3538/0/0 passed/failed/skipped)". The omitted cases are all under
`sql/_05_plcsql/_01_testspec/_05_bug_fix/` (`cbrd-27500`, `cbrd-27556`,
`cbrd-27584`, `cbrd-27633`, `cbrd-27634`, `cbrd-27742`, `cbrd-27927`). The
earlier analysis of head `dc1b83a33b` ([ci-analysis.md](ci-analysis.md))
recorded the same check failure on 33 other commits, including develop
commits.

Context only (unvalidated raw evidence): the raw shard 09 JUnit lists three
failures, `cbrd_26795.sql`, `cbrd_27748.sql`, and `cbrd_28121.sql`. The other
nine shard files list no failures. This does not give a `test_sql` verdict.

## Failure inventory

Head failures: 5 validated (2 shell, 3 sql_by_cci). Baseline classification
is `uncomparable` for all 5 because the baseline is unavailable.
`also_observed_on_base`: 0. `additional_on_head`: 0. `base_only`: 0.

| # | Suite | Testcase | Result | Observed signature | Baseline | tcr verdict | PR relation | Confidence |
|---|---|---|---|---|---|---|---|---|
| 1 | `test_shell` (shard 19) | `shell/_06_issues/_26_2h/cbrd_27744_sa/cases/cbrd_27744_sa.sh` | failure | NOK 13 `sa_crash serial after recovery: expected '140001 2147483647 1', got '1 2147483647 1'`; NOK 14 `sa_crash ids: expected '1 210001', got '1 70001'` | uncomparable | `no_match` | unlikely | medium |
| 2 | `test_shell` (shard 46) | `shell/_06_issues/_26_2h/cbrd_27650/cases/cbrd_27650.sh` | failure | NOK 35 `S5: other sessions on the worker of dq at the failure: d1, expected none` | uncomparable | `no_match` | unlikely | medium |
| 3 | `test_sql_by_cci` (shard 09) | `sql/_36_guava/cbrd_26795/cases/cbrd_26795.sql` | failure | `show trace` adds `(oos time: ?, fetch: ?, ioread: ?)` to the `SCAN (table: dba.px_wide_t)` and `px_rnd_t` lines | uncomparable | `known_job` | unlikely | medium |
| 4 | `test_sql_by_cci` (shard 09) | `sql/_36_guava/cbrd_27748/cases/cbrd_27748.sql` | failure | plan: outer `iscan` with `/* ---> skip ORDER BY */` instead of `temp(sort limit)` | uncomparable | `known_job` | unlikely | medium |
| 5 | `test_sql_by_cci` (shard 09) | `sql/_36_guava/cbrd_28121/cases/cbrd_28121.sql` | failure | trace lacks `skip order by: true` | uncomparable | `known_job` | unlikely | medium |

The expected file for rows 3 to 5 is the `.answer` file (no `.answer_cci`
exists), per the message's `** Expected :` line. The tested answer blobs equal
the current `origin/develop` blobs of `cubrid-testcases` (`6511d237`,
`7b53582d`, `fc5fe9f2`).

### Known-issue check (`cubrid-tcr 0.1.0`)

`cubrid-tcr --json check --ci-attempt <suite dir> --record` for `test_shell`
and `test_sql_by_cci`:

- Rows 1 and 2: `no_match`, "no rule matched". `record.result:
  no_single_match`, no candidates. Its history counts are 0 failures and
  0 passes.
- Rows 3 to 5: `known_job`, rule `sql-by-cci-every-branch-20270108` (no
  issue, not expired). Its `not_covered` text says the job "also fails on
  develop". Per the label rule, each symptom still needs analysis (below).

### Duplicate JIRA check (`cubrid-jira-dup candidate-find --json`)

These are suggestions, not confirmed duplicates.

| Failure | Top candidates |
|---|---|
| `cbrd_27744_sa` | CBRD-27991 (Open, serial cache and NEXT_VALUE plan survive a CREATE/ALTER SERIAL rollback), CBRD-27744 (Resolved, the original fix), CBRD-27641 (Confirmed), CBRD-20051 (Open) |
| `cbrd_27650` | CBRD-28347 (Open, connection worker wake-up), CBRD-27650 (Resolved, the original fix), CBRD-27343 (Resolved) |
| `cbrd_26795` | CBRD-28074 (Confirmed, OOS time in parallel heap scan trace), CBRD-28011 (Resolved, split heap and OOS read cost in SQL trace) |
| `cbrd_27748` | CBRD-28105 (Closed, LEFT OUTER JOIN ORDER BY LIMIT), CBRD-27748 (Resolved), CBRD-27928 (Open) |
| `cbrd_28121` | CBRD-28121 (Resolved), CBRD-26258 (Closed, skip ORDER BY for joins), CBRD-27928 (Open) |

No candidate is an active issue that describes these exact signatures.

## Bounded attribution

### A. The PR change is inactive under the CI configuration

- **Observed:** the PR source diff against merge base `cbed1d5707` adds
  `PRM_ID_OOS_TRIGGER_THRESHOLD` (default `0`),
  `heap_oos_check_trigger_threshold ()` at restart, createdb, and emergency
  patch, and a `class_oid` argument to `heap_oos_inline_target_size ()`. When
  the threshold is `0`, `heap_oos_inline_target_size ()` returns
  `heap_oos_auto_inline_target_size ()`, which is the earlier computation.
  No testcase at the tested revisions sets `oos_trigger_threshold`, except the
  `cbrd_26111` paramdump answers.
- **Inference:** the record layout, serial handling, connection handling, and
  optimizer paths in the failing testcases run as they do on develop.
- **Unknown:** whether the restart-time check changes timing in
  `cbrd_27744_sa` recovery. It only reads a parameter and compares two values.
- **Falsifier:** the validated merge-base run passes a testcase that fails on
  this head with the same testcase revision.

### B. Shell failures: probable develop change in `bfb59bdd13..e23905d89a`

- **Observed:** these runs used the same testcase blobs (`cbrd_27744_sa.sh`
  `ca79025d6d`, `cbrd_27650.sh` `1eb5946852`):

  | Engine (PR, head) | Merge base | `cbrd_27744_sa` | `cbrd_27650` |
  |---|---|---|---|
  | #8632 `dc1b83a33b` (runs 45549760101, 45567806032) | `424cab5ef6` | pass | pass |
  | #8735 `b6c1823f54`, #8736 `fd7d071ed5` | `bfb59bdd13` | pass | pass |
  | #8730 `9b0a11e189` | other | pass | fail (NOK 6, different symptom) |
  | #8128 `50f06c32ce` | `e23905d89a` | fail (same NOK 13/14) | fail (same NOK 35) |
  | #8632 `7544aced71` (this run) | `cbed1d5707` | fail | fail |

  The PR's `src/` diff is line-identical at `dc1b83a33b` and `7544aced71`.
  The fixes for CBRD-27744 (`44e9290f38`) and CBRD-27650 (`39bc4efd8d`) are in
  every listed base that contains `e23905d89a`.
- **Inference:** a develop commit between `bfb59bdd13` and `e23905d89a`
  changed the behavior. The 8 commits are CBRD-28321, CBRD-28160, CBRD-28342,
  CBRD-28288 (connection worker statistics baseline), CBRD-27697 (validate
  client-supplied counts in request handlers), CBRD-27640, CBRD-27562 (no
  system operation for temporary sector reservation or volume growth), and
  CBRD-26191. CBRD-28288 is a plausible candidate for `cbrd_27650`, and
  CBRD-27562 is a plausible candidate for the `cbrd_27744_sa` standalone
  recovery. This is not verified.
- **Unknown:** whether the failures are deterministic. Chronicle has no
  history for these testcases (`UNKNOWN_HISTORY`, `never_observed`). Only two
  failing runs on the newer bases are known.
- **Falsifier:** run 45644791295 on `cbed1d5707` passes both testcases, or a
  focused local run of develop `e23905d89a` passes them repeatedly.
- **Next action:** collect the merge-base baseline when run 45644791295
  completes. If it fails with the same signatures, open a develop issue after
  the user confirms the duplicate check, and bisect the 8 commits with
  `cubrid-test-shell-run`.

### C. `test_sql_by_cci` (and raw `test_sql`): answer drift on develop

- **Observed:** the three diffs are identical on PRs #8128 (`50f06c32ce`),
  #8735, and #8736, whose engine changes are unrelated to OOS parameters. The
  raw `test_sql` JUnit of this run and of #8735 and #8736 lists the same three
  testcases as failures. The `cbrd_26795` answer changed on 2026-11-25
  (`313d208b8`) and contains no `oos time` line. The `cbrd_27748` and
  `cbrd_28121` answers changed on 2026-11-23.
- **Inference:** the develop engine output and the develop answers disagree.
  For `cbrd_26795`, the engine prints the OOS trace part that CBRD-28011 added
  when the scanned table has OOS columns. For `cbrd_27748` and `cbrd_28121`,
  the optimizer now chooses skip ORDER BY in a different set of plans. The
  specific commits are unknown.
- **Falsifier:** the validated merge-base `test_sql_by_cci` run passes these
  testcases.
- **Next action:** after the baseline confirms the drift, update the answers
  through a testcase PR or open an issue for the engine output. This is
  separate follow-up work and does not waive the CI requirement for this PR.

## Baseline comparison

- `cubrid-ci collect-base` (exit `3`) and `verify` (exit `3`): `baseline:
  unavailable`.
- Selection: head ref `CBRD-28062-oos-param`, head SHA `7544aced71`, target
  `develop` tip `cbed1d5707a556e2f2a57dde2b0c77f779968dc8`, exact merge base
  `cbed1d5707a556e2f2a57dde2b0c77f779968dc8` (the target tip is the merge
  base), observed 2026-11-25T15:56:13Z.
- All four suites of run 45644791295 (attempt 1) were `running` / `PENDING`.
- Baseline observation:
  `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/cbed1d5707a556e2f2a57dde2b0c77f779968dc8/observations/20261125T155812.532425880Z-1868232-0`.
- No exact comparison is possible. The other-PR evidence in section B and C
  is context, not a baseline.

## Testcase history (`cubrid-tcc 0.3.0`)

- `sync-data --run 45598259772 --suite test_shell --revisit-limit 0`: exit 0,
  0 inserted snapshots, 3 unavailable files, 2985 runs still missing (a
  `--missing` drain is a maintenance gap).
- `history` for both shell testcases: `UNKNOWN_HISTORY`, `not_indexed`,
  `never_observed`, `suite_last_sync` 2026-11-25T15:27:03Z. Shell evidence
  lists failures only, so missing passes say nothing about stability.
- `test_sql_by_cci`: Chronicle answers `unsupported_suite`; history is
  unavailable.
- No flakiness claim is supported.

## Actions

1. When run 45644791295 completes, run `cubrid-ci collect-base` and `verify`
   again, then extend this report with the exact comparison.
2. If the baseline confirms the shell signatures, confirm a JIRA duplicate
   with the user (candidates above), then bisect `bfb59bdd13..e23905d89a`
   locally.
3. Track the three SQL answer drifts as develop testcase or engine follow-up
   work.
4. Do not rerun automatically. Rerun or re-trigger after develop fixes land
   and the PR is rebased, or after the user approves a known-issue rule.
5. Keep the TC PRs open until the final merge handoff (`/cubrid-pr-merge 8632`).

## Evidence files

- Head bundle: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8632/7544aced71efa25c39a7ae967febbe308d975d89/providers/github-actions/runs/45598259772/attempts/1/`
  (`test_shell/failures/*/{message,diff}.txt`,
  `test_sql_by_cci/failures/*/{message,diff}.txt`, `test_sql/raw/shards/*/`).
- Context bundles: the `pr-8128`, `pr-8730`, `pr-8735`, and `pr-8736` folders
  in the same evidence root.
- Machine summary:
  `~/.local/state/cubrid-pr-flow/runs/pr-8632-7544aced71-req-104-analysis-summary.json`.
