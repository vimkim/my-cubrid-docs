# CI Build Failure Analysis: PR #7925 at `e24b458`

## Executive Summary

CircleCI job 154424 fails during release CMake configuration because the new OOS CLI regression unconditionally requires Python 3. This is directly introduced by PR #7925, not an observed engine compilation or runtime failure.

## CI Snapshot

- PR: https://github.com/CUBRID/cubrid/pull/7925
- Exact revision: `e24b458bfea4d49cc763328c055c5c5374694b06`
- Job: https://app.circleci.com/pipelines/github/CUBRID/cubrid/37046/workflows/8461c1f9-e35a-48bd-b4a0-157cacd294db/jobs/154424
- Job name: `build`; workflow: `build_test`; failed step: `Build (release)`; exit code: 1.
- Scope: the supplied build job only. Runtime suites and other checks were not collected; no runtime pass/failure counts are inferred.

## Root-Cause Analysis

Observed log:

```text
Could NOT find Python3 (missing: Python3_EXECUTABLE Interpreter)
Interpreter: Wrong major version for the interpreter "/usr/bin/python"
unit_tests/oos/CMakeLists.txt:133 (find_package)
[FATAL] Configuring failed
```

The patch adds `find_package(Python3 REQUIRED COMPONENTS Interpreter)` solely to register `test_oos_workspace_cli`. The CI configuration uses `cubridci/cubridci:develop` and fails to discover a suitable interpreter. Local Python availability masked this build prerequisite. The log proves discovery failure, not the absence of every possible interpreter at every path.

## Recommended Actions

Decouple the Python-based CLI regression from mandatory engine configuration. One concrete approach is a dedicated test option: when enabled, require a compatible Python and register the test; normal builds without that optional integration test should configure without Python. Keep the regression explicitly enabled in its validation environment and report whether it ran, rather than silently treating an omitted test as a pass.

Alternatives are provisioning compatible Python in the CI build image, or porting the regression to existing shell tooling. The former adds a build-environment dependency; the latter is a larger test rewrite. The current script uses `subprocess.run(text=True)`, so Python 3.7 or newer is required unless that invocation is adapted.

Before publishing a correction, verify configuration both without Python and with the regression explicitly enabled, run the retained regression with Python, and rebuild. A source fix has not been applied or pushed during this diagnosis.

## Evidence and Limitations

Read-only CircleCI API fallback was used because the installed collector supports runtime suites rather than a standalone build-job command. Job metadata verifies repository, PR branch, full revision, job number and supplied workflow ID.

Evidence: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27424/e24b458/api-build-154424/job.json` and `step-5.log`. The configure failure is definitive; no engine runtime regression is established by this job. No CI rerun or remote mutation was performed.
