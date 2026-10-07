# PR7927 CI snapshot — 4be72fc20

**Warning: the selected head collection is incomplete. No regression or root-cause conclusion is supported by this snapshot.**

PR: [CUBRID/cubrid #7927](https://github.com/CUBRID/cubrid/pull/7927).
Pinned Engine commit: `4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c`.
Status snapshot: `2026-10-07T08:39:22+00:00`.
Head collection: `2026-10-07T08:39:27.040469775Z`.
Collector: `cubrid-ci 0.2.0 (16d7252122d1, release)`.
Work-tracker: 242. Agent: codex.
This report is an uncommitted local analysis draft in `docs/pr7927-ci-4be72fc`.

## Observation outcome

One delegated status command and one exact-head collection were executed, without
`--wait`. Collection exited 3 because all requested suites were `running`.
The command result and manifest agree exactly. Their schema-v2 identity and the
matching schema-v1 request/result observation pair validate against schema source
`16d7252122d185dc8866c99598644dd974044bd2`, matching the executed binary.
The unique head observation is `20261007T083925.878474303Z-428207-0` and its
terminal outcome is `incomplete`.

The executable report-mode gate returns `warning`, with comparison scope `none`
and regression conclusions disabled. No completed head summaries, failure records,
or testcase counts are available. Unknown counts are not zero counts.

## Requested suites and acquisition ledger

| Suite | Collector state | Execution | Terminal verdict / counts | Acquisition |
| --- | --- | --- | --- | --- |
| test_medium | running | [37595050033, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/37595050033) | unknown | not_attempted |
| test_sql | running | [37595050033, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/37595050033) | unknown | not_attempted |
| test_shell | running | [37595050033, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/37595050033) | unknown | not_attempted |

The validated terminal observation has an empty acquisition ledger. No named
shards or response sets were acquired, retained or failed during this head
collection. Shard identities and counts are unknown; `not_attempted` describes
collection, not test execution. No acquisition endpoint, stage failure, response
consumption or diagnostic was reported.

Both build contexts and all three suite contexts were pending and linked to the
same new run at pickup verification (`2026-10-07T08:39:13.362347+00:00`). All stable
required gha-ci contexts were present. The separate live
`gh pr checks --required` query returned exit 1 with
“no required checks reported on the 'feat/oos-deferred-write' branch”. That query
provides no configured required-check list; it does not establish a passing gate.

## Binary budget and diagnostics

Binary acquisition was disabled. The head observation records configured budget
536,870,912 bytes, consumed 0, remaining 536,870,912, and no artifact transfers.
No binary download was attempted; there is no provider-absence or budget-exhaustion
conclusion. The head result has an empty structured error list. An unfinished run
is not a collector integrity failure or a testcase failure.

## Exact merge-base acquisition

One `cubrid-ci collect-base` invocation exited 0. Its returned schema-v3 manifest
and command result, uniquely matching schema-v2 request/result observation, all
completed suite summaries/raw indexes/failure records, per-shard Engine identity,
counts, and raw lengths/digests validate independently. The new baseline observation
is `20261007T084538.848699936Z-435175-0`; collection time is
`2026-10-07T08:45:39.163359795Z`. The result is `validated_exact`.

- Pinned head: `4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c`.
- Target: `feature/oos-merge` at `fb567a629cdb390fff920542173fa36f454c74a0`.
- Exact merge base: `fb567a629cdb390fff920542173fa36f454c74a0`.
- Relationship observed: `2026-10-07T08:39:49.900904685Z`.
- Discovery coverage: all paginated exact-commit statuses and check runs, without
  a repository-wide workflow scan. The selected execution is
  [36570256001, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/36570256001).
  Its PR7990 title and workflow SHA are context; each consumed Engine build is
  independently proven to be the exact merge base, in Debug mode.

| Baseline suite | Verdict | Tests | Passed | Failures | Errors | Skipped | Planned / run / unrun |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| test_medium | pass | 975 | 975 | 0 | 0 | 0 | 975 / 975 / 0 |
| test_sql | pass | 17471 | 17471 | 0 | 0 | 0 | 17471 / 17471 / 0 |
| test_shell | fail | 3289 | 3254 | 5 | 0 | 30 | 3289 / 3259 / 0 |

All 61 baseline shards are retained (1 medium, 10 SQL, 50 shell). All 780 indexed
raw files validate by length and SHA-256 (27,872,236 file bytes), and the five shell
failure metadata/message/diff records reconcile. These file bytes are an integrity
inventory, not a claim about network-response consumption. No baseline binaries
were requested; its binary budget consumption is zero.

Baseline public testcase revision: `bdba62aee0faec05abdd861518824c69b6c1b3c5`.
Baseline private testcase revision: `c4b9d482fbd491a68510b2552df2c3cac91911fc`.
The trigger preflight observed these same tips on both PR7927 testcase branches;
actual consumed head testcase/build/CTP/configuration provenance remains unknown
until head summaries validate. Affected-case source equality and input equivalence
have not been assessed because there is no terminal head failure inventory.

The report-mode gate was rerun with `baseline=validated_exact` and remains
`warning` with comparison scope `none`. Baseline failures have not been classified
as shared, additional, or baseline-only against this unfinished head. No baseline
pass or failure substitutes for an unknown head verdict.

## Unknowns and next actions

- Obtain a new terminal exact-head snapshot after run 37595050033 finishes; do not
  rerun CI merely to obtain evidence. Validate the new collection independently.
- Then compare exact paths and signatures against validated merge-base evidence,
  preserving testcase, build, CTP and configuration provenance. Matching signatures
  establish prior observation only; additional head failures require attribution.
- Retain the broader item242 ordering-preservation question. Its older aecce0e
  conclusions are historical and do not establish this head's behavior.
- PR7925 integration qualification is outside this CI snapshot and remains unknown.

## Evidence inventory

- [Status snapshot](ci_analysis_evidence_4be72fc_codex/status.json),
  [exact-head result](ci_analysis_evidence_4be72fc_codex/result.json),
  [validation receipt](ci_analysis_evidence_4be72fc_codex/head-validation.json).
- [Report-mode assessment](ci_analysis_evidence_4be72fc_codex/assessment.json) and
  [gate result](ci_analysis_evidence_4be72fc_codex/report-mode.json).
- [Exact merge-base result](ci_analysis_evidence_4be72fc_codex/base-result.json),
  [independent baseline validation](ci_analysis_evidence_4be72fc_codex/base-validation.json),
  and [validation script](ci_analysis_evidence_4be72fc_codex/validate-baseline.py).
- Immutable selected head [request](ci_analysis_evidence_4be72fc_codex/head-observation-request.json)
  / [terminal result](ci_analysis_evidence_4be72fc_codex/head-observation-result.json), and baseline
  [request](ci_analysis_evidence_4be72fc_codex/base-observation-request.json)
  / [terminal result](ci_analysis_evidence_4be72fc_codex/base-observation-result.json).
- [Single trigger receipt](ci_analysis_evidence_4be72fc_codex/receipt.json) and
  [pickup verification](ci_analysis_evidence_4be72fc_codex/pickup.json).
- Collector-owned head evidence directory: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7927/4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c`.
  Matching request/result observation: `observations/20261007T083925.878474303Z-428207-0`.
  No completed head suite summary or testcase-source inspection is represented here.

- Collector-owned baseline evidence directory: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/fb567a629cdb390fff920542173fa36f454c74a0`.
  Selected summary paths, testcase revisions and file-integrity receipt are listed
  in the independent baseline validation file. These suites are baseline evidence,
  not completed head evidence.
