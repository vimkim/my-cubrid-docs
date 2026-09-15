# PR #7925: optional Python CLI test repair

## Identity and scope

PR: https://github.com/CUBRID/cubrid/pull/7925
Head: `e24b458bfea4d49cc763328c055c5c5374694b06`; branch `CBRD-27424-oos-loaddb-sa`; base `feat/oos`.
Source: `/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa`. Only pre-existing untracked HANDOFF.md at start.
Stage: pushed-awaiting-ci. Approved publication and one trigger completed; no further fix/push/retrigger authorization.
Scope is the build dependency failure only. Runtime suites and other checks are not assessed. CTP roots are unset in the loaded environment; this repair uses CMake and the existing installed CLI regression, so no CTP repository is required or changed.

## Failure inventory

| Check | Job/step | Tested revision | Result | Disposition |
|---|---|---|---|---|
| CircleCI build | 154424 / Build (release), workflow 8461c1f9-e35a-48bd-b4a0-157cacd294db | e24b458bfea4d49cc763328c055c5c5374694b06 | CMake cannot find Python3; required at unit_tests/oos/CMakeLists.txt:133 | analyzed |

Evidence: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27424/e24b458/api-build-154424/`.
Cause: unconditional Python dependency introduced by the new CLI test. Confidence: high, directly observed. Local Python availability masked it.

## Approved proposal

User: "Make the Python CLI regression explicitly optional for normal builds, require compatible Python when enabled, and preserve its assertions. Verify configuration without Python and run the enabled regression locally. Show the verified diff before pushing."

Change only `unit_tests/oos/CMakeLists.txt`: add `UNIT_TEST_OOS_WORKSPACE_CLI` default OFF; when ON require Python 3.7+ and register the existing test unchanged. Print an explicit disabled-test status otherwise.
Verification: reproduce configure failure with CMake Python discovery disabled; normal configuration with discovery disabled passes after change; explicit test enablement with disabled discovery still fails; enabled compatible Python registers and executes the unchanged regression. Build through the existing local workflow. No testcase answer/assertion edits.

## History

- Initial diagnosis retained in `../../ci_analysis_report_e24b458_codex.md` (report at ticket root).

## Local validation — 2026-09-11

- Only source edit: unit_tests/oos/CMakeLists.txt. Python script/assertions unchanged; git diff --check passes.
- Attempts 01–04: old required package fails with CMAKE_DISABLE_FIND_PACKAGE_Python3=TRUE; new default OFF passes and registers zero CLI tests; explicit ON with disabled discovery fails; ON with Python 3.14.3 passes (minimum 3.7).
- Attempt 05: build/install succeeded; CTest 27/28, 156.15 sec. CLI failed during final no-logging DB createdb. Engine error -9 reports insufficient /tmp volume space (required 445906 KB vs available 363169 KB). Failure DB/core retained at /tmp/cubrid-workspace-oos-kon2j9f5.
- Attempt 06: same binaries/script, TMPDIR on /home with available space; focused CTest 1/1, 60.74 sec, all 12 scenarios passed. No new engine hypothesis or assertion edit required.
- Logs: source worktree .scratch/cbrd27424/ci-fix-01-before-no-python.log through ci-fix-06-cli-home-tmp.log; successful CTest output copied alongside logs.
- Current result is 27 other tests passed plus focused CLI pass, not a fresh single 28/28 run. No new CI run/push.
- User added report expansion: local draft ../../CBRD-27424-sa-workspace-oos_e24b458_codex.md covers workspace semantics, loader/CSQL route decisions, costs, alternatives, chosen boundary, implementation invariants, complete previously verified standalone shell and extended regression instructions. Original published report preserved in isolated docs publication checkout.
- Publication requires user review. Intended source destination: vimkim/cubrid branch CBRD-27424-oos-loaddb-sa (PR #7925); docs destination if authorized: vimkim/my-cubrid-docs main via isolated checkout, only revised report. Do not push unrelated canonical docs history. No commit/push/comment issued.

Verified patch SHA-256: `2cc8484da25a6f2dfcc094336245c676e3dfca48df81c01e977766bcaf8d2304`.

## Approved publication — 2026-09-11

User approved publication of the reviewed source fix and expanded report, PR report-link and verification-note updates, one `/run all` trigger, and exact-head CI monitoring. Additional fixes or pushes require renewed approval.

- Reviewed source patch matched SHA-256 `2cc8484da25a6f2dfcc094336245c676e3dfca48df81c01e977766bcaf8d2304`; regression script unchanged.
- Source commit `fe1a918f9a31e8586e8160da4f7341978514538b`, pushed to `https://github.com/vimkim/cubrid` branch `CBRD-27424-oos-loaddb-sa`. Only `unit_tests/oos/CMakeLists.txt` changed. Pre-push base freshness check passed.
- Report bytes SHA-256 `8b2a2d80132618811ca7c1dee451ec2b0d541d7cd1379b8bbbf0574274f69a5b`, published as docs commit `453f22daf1fc17e0dbf311be37d2ef6f6ac63f3b` to `https://github.com/vimkim/my-cubrid-docs` main. Isolated checkout fast-forwarded from 157b2dd to existing remote 0762d33 first; only reviewed report in new commit. Preserved approved bytes including a harmless trailing blank line flagged by diff --check.
- PR body updated and exact readback verified. Pinned report link to docs commit; preserved historical 28/28 versus latest 27/28 + focused pass; report's local-review status text identified as historical in PR body.
- Trigger https://github.com/CUBRID/cubrid/pull/7925#issuecomment-5631980552, body `/run all`, 2026-09-11T08:55:35Z; PR head before/after equals source commit above. No intervening comments between pre-push and trigger; no duplicate new-head request.
- New-head CircleCI workflow `de7dcc61-a984-430e-b67f-890898f40108`: build 154535 and build_debug 154536 running at first observation. SQL/medium/shell pending discovery.
- Classic branch protection request returned 404; branch rules endpoint returned a response retained in evidence. Required-check visibility remains limited until reconciled.
- CTP roots unset; candidate local test worktrees exist under /home/vimkim/gh/tc but no reproduction or testcase mutation is authorized in this publication phase. Resolve exact CI testcase identities from collected results if needed.
- Old head build_debug 154421 also observed failed and download-build 154425 succeeded; these are historical, not current-head results.

Next action: monitor current head's build prerequisites, all three requested runtime suites and miscellaneous checks; collect abnormal results read-only and request approval before any repair.

### Trigger pickup and first monitor snapshot

Pipeline 37077 (`69ea58d8-e8e5-4626-856b-d79475d5f02c`) was API-triggered by cubridci at 08:55:43Z for exact head fe1a918f9. Workflow `38d3650d-a5f2-4d44-a12a-d9715f9727f2`: release 154542, debug 154537, SQL 154538, medium 154539, download-build 154540, shell 154541. Runtime jobs are present but blocked by prerequisites; this is confirmed pickup, not a missing trigger.

All five GitHub checks passed in Actions run 34581515941. Runtime collector 0.1.0 returned expected unavailable exit 3 for each pinned suite while queued. API monitor stores timestamped GitHub/CircleCI snapshots under `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-27424/fe1a918/api-monitor/`.

Branch metadata confirms `feat/oos` is unprotected, with enforcement off and empty required status contexts/checks; the branch rules endpoint returned []. The earlier protection 404 therefore does not leave an unresolved required-check permissions ambiguity. All requested build/runtime jobs and discovered miscellaneous checks still require terminal assessment.

09:06:37Z snapshot: push workflow build 154535 and debug 154536 passed; triggered workflow build 154542 and debug 154537 passed. SQL 154538 and medium 154539 running. Shell 154541 blocked behind download-build 154540 (not_running). Original Python build failure is remotely resolved on this head; full runtime validation remains pending.

## Runtime outcome and decision boundary — 2026-09-11 09:38 UTC

- Medium 154539: 975/975 success; failure/error/unknown/skipped all zero.
- SQL 154538: 17459 total, 17443 success, 16 failures, error/unknown/skipped all zero. Completed collector bundle retained at ticket/fe1a918/test_sql, including 127 text artifacts, 5 failed-action logs, 32 exact-revision case/answer sources; all source bytes verified against Git commit b10727db4b9fd1b52aed49330634a3395d532048.
- All 16 SQL failure messages exactly match PR #7927 job 154502 on be7c01a at the same testcase revision. Existing baseline f4299ac paired-reproduction evidence validated. Categories: 13 plan/trace, 2 OOS size-limit, 1 catalog-count. Strong baseline-related inference; no new local reproduction of this candidate, no waiver of failed CI.
- Full inventory and recommended actions: ../../ci_analysis_report_fe1a918_codex.md (local only, not authorized for additional publication).
- download-build 154540 still not_running without start time; shell 154541 blocked. Queue cause unknown. No new trigger permitted.
- Recommended decision: accept baseline-matching SQL failures outside this focused dependency repair while keeping shell monitoring open, or authorize a separate investigation/proposal. No further fix/push undertaken.

Review question submitted: accept the 16 baseline-matching SQL failures outside this focused repair, or investigate further read-only before deciding. No answer yet. Monitor process is source `.scratch/cbrd27424/monitor_published.py`, exec session 32006; it writes snapshots every ~50 seconds and has a bounded 180-iteration lifetime. Do not assume it runs indefinitely: inspect the process/session and latest snapshot on resume, then resume read-only monitoring as necessary. Latest observed snapshot 09:39:21Z still has download-build not_running and shell blocked. Goal and tracker remain open; no claim of full CI completion.

Continuation audit 1 (09:41 UTC): prior turn made publication/collection progress. Revalidated live monitor session 32006, exact PR head fe1a918f9, and workflow 38d3650d; download-build154540 remains not_running with null start, shell154541 blocked. Pending SQL scope question has no answer. Inspected pinned .circleci/config.yml: workflow uses build-debug-node named download-build (lines691–695), executor cubrid-build-node on self-hosted resource_class cubrid/ramdisk (lines61–64). This narrows operator triage to that resource queue without claiming an offline runner. Same external prerequisite and user decision remain outstanding; no additional edits/pushes/triggers.

## Blocked audit — 2026-09-11 09:42:38 UTC

The same external prerequisite and pending SQL disposition have persisted across the publication turn and two automatic continuations. Latest direct API check confirms exact PR head fe1a918f9; download-build154540 remains not_running with no start time, shell154541 blocked. No reply to the SQL scope question has arrived. Prior continuation was a verified wait plus configuration evidence, not an execution of shell.

Goal/tracker marked blocked, not complete: further meaningful progress requires cubrid/ramdisk job assignment/execution or user input authorizing/accepting SQL follow-up. No source/test/CI configuration change, push or retrigger is authorized. Local poller stopped to avoid unattended duplicate monitoring; remote CircleCI workflow/jobs were not canceled. Evidence remains intact. Resume by rechecking PR head and workflow 38d3650d-a5f2-4d44-a12a-d9715f9727f2; collect shell only once it actually executes. Source/report publication and PR update remain complete.
