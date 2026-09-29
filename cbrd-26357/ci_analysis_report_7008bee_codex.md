# CI Snapshot Warning: PR #7990 at `7008bee`

## Decision Boundary

This is an incomplete GitHub Actions snapshot. All requested regression suites were still running when collected. **This snapshot supports no regression, pass/fail, failure-attribution, or root-cause conclusion.**

## Identity

| Field | Value |
|---|---|
| Repository | `CUBRID/cubrid` |
| Pull request | [#7990 — CBRD-26357: Add out-of-row overflow storage](https://github.com/CUBRID/cubrid/pull/7990) |
| Exact commit | `7008beee0f145c5c5a4a6274e57bee7791f8f162` |
| Collected at | `2026-09-21T20:50:46.624205611Z` |
| Collector | `cubrid-ci 0.2.0 (4c6a8d344f09, release)` |
| Collection exit | `3` — requested evidence is unfinished |

The current-directory status snapshot, command result, and published manifest agree on the PR and full commit. The command result and manifest both validate as schema version 2.

## Suite State

| Suite | Collection state | CI state | Run | Attempt | Validated testcase counts |
|---|---|---|---:|---:|---|
| `test_medium` | `running` | `PENDING` | [35652206601](https://github.com/CUBRID/cubrid/actions/runs/35652206601) | 1 | Not available |
| `test_sql` | `running` | `PENDING` | [35652206601](https://github.com/CUBRID/cubrid/actions/runs/35652206601) | 1 | Not available |
| `test_shell` | `running` | `PENDING` | [35652206601](https://github.com/CUBRID/cubrid/actions/runs/35652206601) | 1 | Not available |

No suite had a complete summary, normalized failure record, testcase revision, or textual failure evidence at collection time. No suite is classified as passed or failed here.

## Observations

- **Observed:** `cubrid-ci status` discovered PR #7990 from `/home/vimkim/gh/cb/feature-oos-merge` and reported the exact published head above.
- **Observed:** all three current `gha-ci` suite statuses identified the same exact commit and the same Actions run.
- **Observed:** the collector pinned run `35652206601`, attempt 1 independently for each requested suite.
- **Observed:** the schema-v2 command result has `ok: false`, three `running` suite states, and no collection error records.
- **Observed:** the published manifest is semantically identical to the command result and validates against `manifest-v2.schema.json`.

## Unknowns

- Final CI verdicts and testcase counts for all three suites.
- Testcase repository revisions and paths selected by each shard.
- Whether any testcase will fail or error.
- Any relationship between eventual CI results and this pull request.

There are no inferences about regression or root cause because terminal textual evidence is not yet available.

## Required Action

After the existing run becomes terminal, perform a new user-requested snapshot collection for the same exact commit and analyze only its newly validated suite summaries and failure evidence. Do not treat this warning report as a stale-result substitute for that future collection.

## Evidence

- Manifest: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7990/7008beee0f145c5c5a4a6274e57bee7791f8f162/manifest.json`
- Command-result schema: `/home/vimkim/gh/cubrid-ci/schema/command-result-v2.schema.json`
- Manifest schema: `/home/vimkim/gh/cubrid-ci/schema/manifest-v2.schema.json`

No credentials, authorization headers, signed evidence-server URLs, or binary artifacts are included in this report.
