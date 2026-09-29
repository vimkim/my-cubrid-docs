# CI Snapshot Warning: PR #7990 at `b8f3c48`

## Decision Boundary

This report records the latest completed `gha-ci` evidence returned for CUBRID PR #7990 at its pinned head. **This snapshot supports no regression or root-cause conclusion.** The collection cannot be validated as one append-only invocation because it has no collection observation, and each suite's raw evidence index fails the current schema.

The retained summaries enumerate nine testcase failures. Two of those paths are independently covered by the accepted OOS project decision that they remain enabled and visibly failing. That policy context does not validate the collected signatures. The other seven failures remain unclassified: this report does not label them actionable regressions, flaky infrastructure, or stale expected outputs.

The analyzer safety boundary returned:

```json
{"mode":"warning","regression_conclusions_allowed":false}
```

Because this warning report cannot establish a genuine actionable failure, the requested follow-on `diagnosing-bugs` workflow was not invoked.

## Identity

| Field | Value |
|---|---|
| Repository | `CUBRID/cubrid` |
| Pull request | [#7990 — CBRD-26357: Add out-of-row overflow storage](https://github.com/CUBRID/cubrid/pull/7990) |
| Exact PR head | `b8f3c4807470dbeb30b5113acb7dd99d2340347c` |
| Collected at | `2026-09-25T05:36:19.725882367Z` |
| Collector | `cubrid-ci 0.2.0 (31bd609fda78, release)` |
| Collection exit | `0` |
| Evidence directory | `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7990/b8f3c4807470dbeb30b5113acb7dd99d2340347c` |

The one status snapshot, saved command result, and manifest agree on repository, PR, full commit, requested suite set, suite states, run IDs, and attempts. The command result and manifest validate as schema version 2.

## Observation Outcome

No `observations/` directory exists under the returned evidence directory. Therefore there is no unique terminal observation whose request establishes the exact invocation and whose result equals the saved command result. Per the analyzer contract, the retained bundle is unvalidated raw evidence even though the collection command exited successfully.

A second validation failure exists in every suite: each `raw/index.json` is missing the required `summary_sha256` field and fails `/home/vimkim/gh/cubrid-ci/schema/raw-evidence-index-v2.schema.json`.

The installed collector identifies commit `31bd609fda78`. The local `cubrid-ci` source and schemas are at `45944012aaaa4ba985f22775cf715bbcdf121f78`, whose implementation contains append-only observations and `summary_sha256`. This is direct evidence of collector/schema version skew; it is not evidence about any testcase's cause.

## Suite State

These are the states and internally reconciled counts declared by the manifest and retained summaries. They are not promoted to validated failure attribution because the observation and raw-index checks failed.

| Suite | Manifest state | CI state | Run / attempt | Summary verdict | Counts (`planned/run/pass/fail/error/skip/unrun`) |
|---|---|---|---|---|---|
| `test_medium` | `completed` | `SUCCESS` | [35856612204](https://github.com/CUBRID/cubrid/actions/runs/35856612204) / 1 | `pass` | `975/975/975/0/0/0/0` |
| `test_shell` | `completed` | `FAILURE` | [35862521701](https://github.com/CUBRID/cubrid/actions/runs/35862521701) / 1 | `fail` | `11/11/3/8/0/0/0` |
| `test_sql` | `completed` | `FAILURE` | [35862521701](https://github.com/CUBRID/cubrid/actions/runs/35862521701) / 1 | `fail` | `131/131/130/1/0/0/0` |

The retained summaries identify these testcase revisions:

- `test_medium` and `test_sql`: `cubrid-testcases` commit `6add917dd3ddf1bbad3a70320a86f97f6a726b9f`, branch label `tc/pr-7990`.
- `test_shell`: `cubrid-testcases-private-ex` commit `cebbd0884cd2cef8134fe99ec754ffded186327a`, branch label `tc/pr-7990`.

## Acquisition Ledger

No validated invocation acquisition ledger is available because the terminal observation is absent. The following retained-file facts were checked locally:

| Suite | Summary schema | Raw index schema | Failure metadata/files | Acquisition classification |
|---|---|---|---|---|
| `test_medium` | Valid v2 | Invalid: missing `summary_sha256` | No failures declared | Unknown; cannot mark retained/failed/not-attempted without the observation ledger |
| `test_shell` | Valid v2 | Invalid: missing `summary_sha256` | 8 metadata records validate; declared messages and diffs exist | Unknown; cannot mark retained/failed/not-attempted without the observation ledger |
| `test_sql` | Valid v2 | Invalid: missing `summary_sha256` | 1 metadata record validates; declared message and diff exist | Unknown; cannot mark retained/failed/not-attempted without the observation ledger |

All three retained summary count equations reconcile, and the number of failure records equals `failures + errors`. Those local checks do not replace the missing observation or invalid raw indexes.

## Retained Failure Inventory

The following inventory is transcribed once from the schema-valid summaries. The observed-diff column describes retained text only; it is not a root-cause conclusion.

| Suite | Testcase | Retained diff indication | Classification permitted by this snapshot |
|---|---|---|---|
| `test_shell` | `shell/_06_issues/_15_1h/bug_bts_15912/cases/bug_bts_15912.sh` | Utility listing differs at `upgradedb` | Unknown |
| `test_shell` | `shell/_06_issues/_15_1h/bug_bts_16378/cases/bug_bts_16378.sh` | Log-header output differs at `System_metadata_version` | Unknown |
| `test_shell` | `shell/_06_issues/_25_1h/cbrd_25478/cases/cbrd_25478.sh` | Four log-header comparisons differ at `System_metadata_version` | Unknown |
| `test_shell` | `shell/_32_features_930/issue_12504_show_log_header/_01_show_log_header/_01_basic_log/cases/_01_basic_log.sh` | Output differs at `System_metadata_version` | Unknown |
| `test_shell` | `shell/_32_features_930/issue_12504_show_log_header/_01_show_log_header/_02_relative_path/_01_csql/cases/_01_csql.sh` | Output differs at `System_metadata_version` | Unknown |
| `test_shell` | `shell/_32_features_930/issue_12504_show_log_header/_01_show_log_header/_03_absolute_path/_01_self_log/cases/_01_self_log.sh` | Output differs at `System_metadata_version` | Unknown |
| `test_shell` | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | Subchecks 2 and 3 report `NOK` | **Project policy declares visible failure intentional; collected signature remains unvalidated** |
| `test_shell` | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | Subcheck 1 reports `NOK` | **Project policy declares visible failure intentional; collected signature remains unvalidated** |
| `test_sql` | `sql/_33_elderberry/cbrd_23844/cbrd_24337/cases/cbrd_24337.sql` | Expected `Error:-494`; retained actual says `Error:-493` | Unknown |

The independent CDC policy source is `/home/vimkim/gh/cubrid-oos-context/docs/adr/0005-defer-oos-history-from-the-11-5-merge.md`: ADR-0005 says the `cbrd_27064` and `cbrd_27075` cases must remain enabled and visibly failing after durable OOS history is deferred. This is a scope decision, not a diagnosis derived from this CI bundle.

## Binary-Budget Limitations

No validated observation budget accounting or `binary-inventory.json` is available. The saved command result does not establish binary collection options, so this report makes no claim that binaries were requested, exhausted, excluded, or absent at the provider.

## Structured Diagnostics

- Collector setup health check: healthy.
- Collection command: terminal, exit `0`, structured `errors: []`.
- Identity: established at the full PR head above.
- Manifest: schema-valid and consistent with the command result.
- Requested summaries: all three present and schema-valid.
- Observation: unvalidated because the entire append-only observation directory is absent.
- Raw evidence indexes: all three schema-invalid because `summary_sha256` is absent.
- Report mode: `warning`; regression conclusions are disallowed.

## Unknowns

- Whether each retained failure record belongs to the exact collection invocation rather than pre-existing immutable output at the same bundle path.
- Whether the retained raw files are complete and digest-bound to their corresponding summaries.
- Whether any of the seven non-CDC differences is a genuine PR regression, a stale expected output, or infrastructure/test flakiness.
- Whether the two CDC signatures exactly match the intentionally unsupported durable-history behavior; only their path-level policy status is established.
- Which exact testcase, if any, should enter the follow-on diagnosis workflow.

## Required Actions

1. Rebuild or reinstall `cubrid-ci` from the current local source commit `45944012aaaa4ba985f22775cf715bbcdf121f78` (or a later compatible release) so it emits append-only observations and schema-valid raw indexes.
2. In a new analyzer invocation, take one new status snapshot and one collection for PR #7990's then-current exact head. Evidence collection reads the existing run and does not trigger CI.
3. Only after that bundle validates, classify all failures by observed signature and PR relation. If a genuine actionable failure remains, invoke `diagnosing-bugs` for that exact testcase and stop before a fix.

## Evidence Files

- Saved collector result: `/home/vimkim/tmp/cubrid-ci-analysis.FOi3Lp/result.json`
- Manifest: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7990/b8f3c4807470dbeb30b5113acb7dd99d2340347c/manifest.json`
- Medium summary: `providers/github-actions/runs/35856612204/attempts/1/test_medium/summary.json`
- Shell summary: `providers/github-actions/runs/35862521701/attempts/1/test_shell/summary.json`
- SQL summary: `providers/github-actions/runs/35862521701/attempts/1/test_sql/summary.json`
- Analyzer assessment: `/home/vimkim/tmp/cubrid-ci-analysis.FOi3Lp/assessment.json`
- Current schemas: `/home/vimkim/gh/cubrid-ci/schema/`
- OOS decision record: `/home/vimkim/gh/cubrid-oos-context/docs/adr/0005-defer-oos-history-from-the-11-5-merge.md`

No source code, testcase, expected output, CI run, or remote state was changed. The report is intentionally uncommitted and unpushed.
