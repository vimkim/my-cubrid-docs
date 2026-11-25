# CI analysis: PR #8632 at `dc1b83a33b` (warning report)

> **This snapshot does not support a regression or root-cause conclusion.**
> The `cubrid-ci` observation is `incomplete`: the `test_sql` evidence failed
> its integrity check, and no merge-base baseline exists. `report_mode.py`
> permits only a warning report (`mode: warning`,
> `regression_conclusions_allowed: false`, `comparison_scope: none`).

## Result

- **Red regression suite:** `gha-ci: test_shell` has one failure:
  `shell/_06_issues/_26_2h/cbrd_27780/cases/cbrd_27780.sh` (NOK 2 and NOK 4,
  `S1HEAP=2`). Its suite evidence is validated. `cubrid-tcr` gives the verdict
  `known` with rule `cbrd-28257-catalog-leak-s1-written`
  ([CBRD-28257](https://jira.cubrid.org/browse/CBRD-28257), Confirmed,
  unresolved). Report label: "Known issue, not caused by this PR."
- **Collection gap:** CI reports `gha-ci: test_sql` as SUCCESS. The collector
  rejected its evidence: the shard 01 JUnit file omits 19 PL/CSQL testcases
  that `summary_info` reports. The same check failure occurs on 33 other
  commits, including develop commits, so it is not specific to this PR. This
  is context only, not a verdict on this PR.
- **TC gate (separate from regression):** `github-actions: Check TC PRs`
  fails with `TC Merge Gate FAILED — TC changes are not on TC develop yet`.
  TC PRs [cubrid-testcases#4329](https://github.com/CUBRID/cubrid-testcases/pull/4329)
  and [cubrid-testcases-private-ex#5017](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5017)
  are open. This is expected while isolation holds. Finalize it at the final
  merge handoff under the testcase lifecycle.
- **Next action:** Rerun only the failed `test_shell` job of run
  [45549760101](https://github.com/CUBRID/cubrid/actions/runs/45549760101)
  through `cubrid-ci-trigger` (`/run rerun 45549760101`). The known CBRD-28257
  leak is intermittent (`notes` id 9 in `cubrid-tcr`). A pre-existing
  signature does not waive the CI requirement.

## CI snapshot

Observed 2026-11-25T06:29Z (UTC). Run `45549760101`, attempt 1.

| Suite | CI state | Collection | Verdict | Counts (planned / run / passed / failures / errors / skipped) |
|---|---|---|---|---|
| `test_medium` | SUCCESS | completed, validated | pass | 975 / 975 / 975 / 0 / 0 / 0 |
| `test_sql` | SUCCESS | `collection_failed` (integrity) | no validated verdict | unknown (see diagnostics) |
| `test_shell` | FAILURE | completed, validated | fail | 3689 / 3659 / 3658 / 1 / 0 / 30 |
| `test_sql_by_cci` | SUCCESS | completed, validated | pass | 17884 / 17884 / 17884 / 0 / 0 / 0 |

Other checks on the head: `build (debug)`, `build (release)`, `code-style`,
`cppcheck`, `license`, `memory-monitor-check`, and `pr-style` are SUCCESS.
`Re-check stale verdicts` is SKIPPED. `Check TC PRs` is FAILURE (TC gate,
above). The CircleCI contexts have no status for this head.

## Evidence scope

| Item | Value |
|---|---|
| PR | [CUBRID/cubrid#8632](https://github.com/CUBRID/cubrid/pull/8632), "[CBRD-28062] Make the OOS trigger threshold configurable", base `develop` |
| Head (engine) | `dc1b83a33b20023796e8962a35a1a773258a75aa` (all `test_shell` shards build this SHA) |
| Testcase revisions | shell: `27e25229e535a188827eda35ff4d8282ae2c6aaa` (tc/pr-8632 tip, "Update cbrd_26111 paramdump answers for oos_trigger_threshold"); medium and sql_by_cci: `ed4297e43516540a1b7774ebef444baaf2482e26` |
| Collector | `cubrid-ci 0.2.0 (00205d576de0, release)`, `verify` available |
| Collect exit / verify exit | `4` (integrity) / `3` (incomplete) |
| Assessment | identity `established`, observation `incomplete`, manifest `validated`, requested summaries `partial`, baseline `unavailable` |
| Evidence directory | `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8632/dc1b83a33b20023796e8962a35a1a773258a75aa` |
| Observation | `observations/20261125T062945.347197587Z-1927641-0`, outcome `incomplete` |
| Binary budget | 512 MiB configured, 0 bytes consumed; it did not limit the collection |

### Acquisition ledger

All requested shards are `retained`: `test_medium` 1, `test_shell` 50,
`test_sql` 10, and `test_sql_by_cci` 10. No shard is `failed` or
`not_attempted`. Retained raw files for `test_sql` are not a suite verdict.

### Structured diagnostic (`test_sql`)

`kind: integrity`, `diagnostic: identity_or_integrity`: "shard 01 JUnit omits
19 testcases that summary_info reports (summary_info 3557/0/0, JUnit 3538/0/0
passed/failed/skipped)". The omitted cases are under
`sql/_05_plcsql/_01_testspec/_05_bug_fix/` (`cbrd-27500`, `cbrd-27556` ×5,
`cbrd-27584` ×2, `cbrd-27633` ×6, `cbrd-27634` ×2, `cbrd-27742` ×2,
`cbrd-27927`).

Observed context: the local `cubrid-ci` store has the same "shard 01 JUnit
omits N testcases" diagnostic for 33 other commits. The same 19-case count
(3557/3538) also appears on develop commit `30eb0c4b8b` (2026-11-24) and on
PR #8514. Inference: the mismatch comes from the CI result artifacts or the
collector's strictness, not from this PR. Falsifier: the diagnostic does not
appear on a develop run of the same testcase revision. Both result sets
report 0 failures, but `test_sql` has no validated verdict in this report.

## Failure inventory

| Suite | Testcase | Result | Observed signature | Baseline | Category | PR relation | Confidence |
|---|---|---|---|---|---|---|---|
| `test_shell` | `shell/_06_issues/_26_2h/cbrd_27780/cases/cbrd_27780.sh` (shard 29) | failure | `cbrd_27780-2 : NOK scenario 1: rows written: found in plaintext in the data volumes: S1HEAP=2`; `cbrd_27780-4 : NOK scenario 1: pages deallocated: found in plaintext in the data volumes: S1HEAP=2` | `uncomparable` (no baseline) | known issue CBRD-28257 | `unlikely` | medium (warning mode, no baseline) |

Totals: 1 head failure. 0 shared, 0 additional on head, 1 uncomparable,
0 base-only.

### Known-issue check (`cubrid-tcr 0.1.0`)

`cubrid-tcr --json check --ci-attempt <test_shell dir> --record` gives
verdict `known`. Hit: rule `cbrd-28257-catalog-leak-s1-written` →
CBRD-28257, reason "CBRD-28257 is Confirmed and unresolved", fix commits:
none. The rule's `not_covered` text excludes Check 1 syntax errors, Check 3/5
page-count mismatches, Check 4-only large leaks (for example
`S1HEAP=66499`), and Check 6/9/13 TDE regressions. This failure is NOK 2
plus NOK 4 with `S1HEAP=2`, and checks 1, 3, 5–14 are OK, so the rule covers
it. `record.result`: `no_occurrence`, because Chronicle has no failed
occurrence for run 45549760101 shard 29.

`cubrid-tcr` note 9 (2026-11-23) states that CBRD-28257 comes from
`catcls_put_or_value_into_buffer()` skipping NULL fixed fields on an
uninitialized `malloc()` buffer, and that Check 2+4 `S1HEAP=1/2` leaks became
frequent after the OOS merge `68a9c7766f` (42 post-OOS runs). This is history
context. It does not prove the cause of this occurrence.

Testcase source: `git show 27e25229e5:shell/_06_issues/_26_2h/cbrd_27780/cases/cbrd_27780.sh`
exists locally. Scenario 1 writes `s1_heap (a char(2000) storage force_inline) encrypt`
and checks with `check_no_plain` that the `S1HEAP` markers do not appear in
plaintext in the data volumes.

### Duplicate JIRA check (`cubrid-jira-dup candidate-find --json`)

- `cbrd_27780` plaintext leak: top candidate **CBRD-28257** ("[TDE] 시스템
  카탈로그 행의 NULL 고정 길이 필드에 서버 메모리의 이전 내용이 남아, 암호화
  테이블의 데이터가 평문으로 디스크에 기록된다", Confirmed). Other candidates
  are CBRD-27780 (Resolved, the original TDE fix) and CBRD-28194 (Resolved).
  No new issue is needed.
- `test_sql` JUnit omission: the candidates are only the PL/CSQL feature
  issues the omitted cases test (CBRD-27742, CBRD-27927, CBRD-27500,
  CBRD-27584, all Resolved). No issue tracks the CI artifact mismatch. This
  is a collector or CI-reporting concern, not a product bug candidate.

## Bounded attribution

Every statement in this section is bounded by warning mode.

**Group A: `cbrd_27780` NOK 2/4, `S1HEAP=2`.**

- Observed: the signature matches the approved rule for CBRD-28257, and the
  JIRA duplicate search ranks CBRD-28257 first.
- Inference: this is the known catalog-buffer plaintext leak, not a defect
  of the `oos_trigger_threshold` change. The PR touches `heap_file.c` and
  `heap_oos.cpp`, but `s1_heap` uses `STORAGE FORCE_INLINE`, and the leak
  site named in CBRD-28257 is in the catalog path.
- Unknowns: no baseline run on merge base `424cab5ef6`. No Chronicle history
  for this testcase (not indexed).
- Falsifier: a rerun of the same head fails with a signature that the rule's
  `not_covered` text describes (for example Check 4-only large `S1HEAP`
  counts), or the failure appears on every rerun of this head and never on
  develop.
- Next action: rerun the failed `test_shell` job. If it fails again with the
  same signature, record the occurrence on CBRD-28257.

**Group B: `test_sql` collection integrity.** This group has no testcase
failure and no causal claim. Next action: report the recurring JUnit
omission for `cubrid-ci` or CI artifact maintenance (separate work, not a
PR #8632 blocker per the CI status).

## Baseline comparison

`cubrid-ci collect-base` resolved target `develop` =
merge base = `424cab5ef64aaa5299b4e5f9267c0ee105ba9f4e` (observed
2026-11-25T06:30:17Z, mode `exact_commit_links`, coverage: all paginated
exact-commit statuses and check runs, no repository-wide workflow scan). It
found no candidate runs. All four suites are `not_observed` (exit 3), and
`verify` gives baseline `unavailable`. **No merge-base comparison is
possible.** Every head failure is `uncomparable`.

## Testcase history (`cubrid-tcc 0.3.0`)

- `cubrid-tcc sync-data --run 45549760101 --suite test_shell --revisit-limit 0`
  ran with 0 observations, 0 inserted snapshots, and 3 unavailable files. The
  run's shell failure is not indexed.
- `cubrid-tcc history shell/_06_issues/_26_2h/cbrd_27780/cases/cbrd_27780.sh --suite test_shell`
  gives `UNKNOWN_HISTORY` (`not_indexed`, `not_indexed_reason: never_observed`,
  `suite_last_sync` 2026-11-25T06:26:25Z). Coverage window: 2026-10-14 to
  2026-11-25, `discovery_complete: false`, 2988 missing runs.
- Gap: a window sync (`--since 2026-10-14T02:21:37Z --until 2026-11-25T06:00:07Z --suite shell`)
  is maintenance for the user. It was not run.
- Earlier failures are therefore unknown from Chronicle. The `cubrid-tcr`
  note (42 post-OOS runs with Check 2+4 `S1HEAP=1/2`) is the only recurrence
  context. Shell evidence lists failures only, so flakiness cannot be shown
  from Chronicle.

## Actions

1. Rerun the failed `test_shell` job of run 45549760101 through
   `cubrid-ci-trigger` (`/run rerun 45549760101`). Then analyze the new
   attempt again.
2. Keep the TC PRs open. Finalize the TC gate only at the final engine merge
   handoff.
3. Separate follow-up: report the recurring `test_sql` shard 01 JUnit
   omission (PL/CSQL `_05_bug_fix` cases) for `cubrid-ci` or CI artifact
   maintenance.
4. Separate follow-up (user maintenance): run the Chronicle shell window sync
   to make `cbrd_27780` history available.

## Evidence files

- Head result and verification: `cubrid-ci` evidence directory above, run
  `45549760101`, attempt 1, suite summaries under
  `providers/github-actions/runs/45549760101/attempts/1/<suite>/summary.json`.
- Failure files:
  `.../test_shell/failures/shell_06_issues_26_2h_cbrd_27780_cases_cbrd_27780_sh-9b5694291f/{message.txt,diff.txt,metadata.json}`.
- Baseline selection: the `collect-base` result (merge base `424cab5ef6`, no
  candidates).
