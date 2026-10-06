# PR #7925 published-head CI evidence warning

Analysis date: 2026-10-07 KST. Published head: `91bfde02e5699a2aaa0c5d549d7ef4d418c8bdb8`. PR: [#7925](https://github.com/CUBRID/cubrid/pull/7925). Local guide head is the newer, unpublished `a142503dc1a6f85b498a425aa58d6a78136ccc6b`.

**This exact-head snapshot supports no regression or root-cause conclusion.** None of the three requested regression suites has an observed run at this published commit. The older triggered run is analyzed independently in [the historical exact-commit report](ci_analysis_report_f037616cd_codex.md); its outcomes are not current-head verdicts.

## Observation outcome

One delegated `cubrid-ci status --json` snapshot was fetched at `2026-10-06T17:17:16+00:00`. One collection of its pinned head completed with exit 3 and a validated `incomplete` terminal observation. Collector: `cubrid-ci 0.2.0 (16d7252122d1, release)`.

| Requested suite | State | Test verdict | Acquired shards |
| --- | --- | --- | --- |
| `test_medium` | `not_observed` | Unknown | None attempted |
| `test_sql` | `not_observed` | Unknown | None attempted |
| `test_shell` | `not_observed` | Unknown | None attempted |

There is no shard acquisition ledger entry because no exact-head run was selected. This is distinct from an interrupted download, a failed testcase, a failed CI job, or a passing suite. The command's structured `errors` array is empty. No binary collection was requested; zero of the configured 536,870,912-byte budget was consumed, leaving all of it available. Missing binaries are therefore unrequested, not evidence of provider absence or budget exhaustion.

## Retained and validated evidence

The v2 command and manifest match. The unique v1 observation request/result pair validates against the matching collector schemas, agrees on repository, PR, full commit, options and requested suite set, and records outcome `incomplete`.

```text
/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/91bfde02e5699a2aaa0c5d549d7ef4d418c8bdb8/manifest.json
/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/91bfde02e5699a2aaa0c5d549d7ef4d418c8bdb8/observations/20261006T171811.107146833Z-651959-0/request.json
/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/91bfde02e5699a2aaa0c5d549d7ef4d418c8bdb8/observations/20261006T171811.107146833Z-651959-0/result.json
```

There are no completed suite summaries, failure metadata, or raw testcase files for this observation. The executable report-mode gate returns `warning`, with comparison scope `none`. The [validation receipt](ci_f037616cd/validation.json) includes this observation separately from the complete historical and base observations.

## Unknowns and next steps

The snapshot does not establish the regression verdict at this published head or at the newer local head. It does not support attribution of a failing testcase to either newer revision. A regression run for the intended published commit, followed by exact-commit terminal collection, would supply that evidence. Publication and CI triggering were not part of this analysis request.

The user-requested analysis of the run already triggered is available for tested `f037616cd17af92e1226afcde80fd2a6fff9121d`, with its own independently validated full evidence and exact merge-base comparison. Refer to that report for its three shell failures and the limits on their attribution.
