# PR7927 remote acceptance record

## Identity and scope

- PR: https://github.com/CUBRID/cubrid/pull/7927
- Engine: `be7c01a6d2d05d461cb1e5b6e0127c15ffb1950b`.
- Comparison baseline: `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`.
- SQL/medium testcase source: `CUBRID/cubrid-testcases` at `b10727db4b9fd1b52aed49330634a3395d532048`.
- Local testcase checkout: `/home/vimkim/temp/pr7927-testcases-b10727d`; original testcase checkout remains unchanged.
- Source worktree: `/home/vimkim/gh/cb/CBRD-27089-oos-deferred-write`; branch `feat/oos-deferred-write`. Existing dirty generated CCI files excluded.
- Durable work item: 117. Contract: local `.scratch/oos-deferred-write/issues/22-ci-acceptance.md` and parent `12-spec.md`.

## Current stage

Attribution completed: all 19 SQL/medium failures reproduce on the baseline, with byte-identical paired local outputs. Acceptance remains open pending shell execution and final matrix reconciliation. Implementation and scoped commits are authorized by the implement request; no new CI comment has been posted by this session.

## Remote attempts

- Medium154504: 975 tests, 972 success, 3 failure, zero error/unknown/skipped.
- SQL154502: 17,459 tests, 17,443 success, 16 failure, zero error/unknown/skipped.
- Shell154506: workflow job is blocked on download-build154505 (`not_running`, no start time). Exact workflow and pipeline metadata prove the same engine SHA. Shell testcase revision is not established because checkout has not executed.
- GitHub Actions34576869752: five static checks succeeded. CircleCI release154503 and debug154501 succeeded.
- Required branch-check applicability resolved 2026-09-11 09:00 UTC: branch metadata disables protection and lists no required checks; effective branch rules are empty. Ruleset2956843 applies only to cubvec/*, not feat/oos. Initial protection-endpoint404 retained in evidence history. Task-required runtime suites remain mandatory.
- Existing `/run all`: https://github.com/CUBRID/cubrid/pull/7927#issuecomment-5631371023. Do not duplicate while prerequisite is pending.

## Evidence

- Collector: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/be7c01a/`.
- Separate GitHub/CircleCI API evidence: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27089/be7c01a-api-20260911/`.
- Local attempts, selection and configurations: `/home/vimkim/.cache/codex/pr7927-be7c01a/`.

## Next action

Monitor existing download-build154505 and shell154506; once they run, collect the exact testcase revision and classify their results. GitHub-enforced check applicability is resolved; no such checks apply to feat/oos, and the specification still requires shell evidence. No new engine fix is indicated by the 19 baseline-equivalent failures. See [snapshot report](../../ci_analysis_report_be7c01a_codex.md) and [paired comparisons](local-verification.json). Final configured CTest:27/27,137.15s; source change is verification documentation only.
