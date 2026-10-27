# CBRD-27124 draft PR context

Preparation record. This file does not grant publication approval.

- Ticket: https://jira.cubrid.org/browse/CBRD-27124
- Agent: codex
- Operation: create
- SOURCE_COMMIT: `0d2a76e60f944be0ababe9c466766c553189fcda`
- Source tree: `7ba3a7225217f9dd7957478a28118973b9ab5aba`
- Base inspected: `2d925cb8685600135eb1fb1781811f6b45fdecb0` (`origin/develop`)
- Integration destination recorded from starting checkout: `develop`. No local engine merge is proposed.
- Target repository: `CUBRID/cubrid`
- Head repository: `vimkim/cubrid`; remote `vk`
- headRefName: `CBRD-27124-isolate-build-version`
- baseRefName: `develop`
- Proposed title: `[CBRD-27124] Isolate per-commit build version headers`
- Proposed state: draft; assignee `vimkim`
- Existing matching open PR: none at preparation
- Observed remote head: branch absent at preparation
- Docs branch: `docs/CBRD-27124-isolate-build-version`
- Docs integration branch: `main`
- Body: `cbrd-27124/CBRD-27124-build-version-pr-body_0d2a76e_codex.md`
- Context: `cbrd-27124/CBRD-27124-build-version-pr-context_0d2a76e_codex.md`
- Local verification report: `cbrd-27124/CBRD-27124-build-version-verification_0d2a76e_codex.md`
- Public explanation URL: none. The PR body contains all essential results.

## Proposed publication operations

1. Push exactly SOURCE_COMMIT to `vk`, branch `CBRD-27124-isolate-build-version`, after checking source and remote freshness.
2. Create a draft PR in `CUBRID/cubrid`, base `develop`, head `vimkim:CBRD-27124-isolate-build-version`, with the saved body and title. Assign `vimkim`.
3. Wait for testcase branch provisioning. No TC changes are required. Report the generated TC PRs to the human for closure. Do not merge or close them.
4. Check current-head comments and complete/required check views. Trigger `/run all` once, provided there is no current-head or active same-PR run. This runs Release and OptDebug builds and the three suites.
5. Wait for that run to finish. Report run URL, tested source SHA, per-build cache counts/rates, actual required checks, and TC Merge Gate. Do not fix, push again, or rerun CI after the result without human direction.

Docs remain locally committed on their task branch. No docs integration, docs push, or engine merge is proposed. Any later change to the reviewed source revision or body requires reconciliation under cubrid-pr-create.

## Verification record

- Debug configure/build/install passed. Standalone header-cache and Git refresh tests passed (Ninja/Make, regular/linked, paths with spaces, packed/loose refs with reflogs disabled, detached commits, same-revision branch switch).
- Empty commit B: `2b27027879e47ab88e3810e8a73cb718ba3599c9`, same source tree as SOURCE_COMMIT; 11 compilations, 7.572 seconds. No explicit configure invocation. Stable `version.h` bytes and mtime preserved; runtime and CPack versions agree.
- Empty commit D: `6b3aa2384f8cf5810fd808c78581072f4de5a9f5`, same source tree; 1,177 object outputs removed, source/header metadata preserved, build-only reconfigure. 1,166 hits and 11 misses (99.07%) in 7.820 seconds. Compile command database unchanged.
- No-op: 0 compilations in 1.629 seconds. ctest found no registered tests.
- Source checkout restored to the named topic branch and SOURCE_COMMIT. Temporary detached measurement commits are absent from PR history.
- Unrelated changes preserved in starting develop and the older CBRD-27124 analysis worktree.
- CI result: draft PR #8298 published; run 40487586838 in progress. See execution record below.

## Execution record

User confirmed the saved material and proposed operations with `yes` in this conversation.

- Publication attempt started: 2026-10-27T10:18:36.709793+00:00
- Approved body SHA-256: `51ed92e44b58087b72728e9481dbe659349255e494e6e1c63e4f559fe39e0634`
- Source, destination and draft status remain as proposed.
- Source push verified: `vimkim/cubrid:CBRD-27124-isolate-build-version` = SOURCE_COMMIT.
- Created draft PR: https://github.com/CUBRID/cubrid/pull/8298 (2026-10-27T10:18:47Z). Base `develop`, head repository `vimkim/cubrid`, headRefName as proposed; assignee `vimkim` verified.
- Published body bytes and SHA-256 match the saved approved body.
- Both testcase branches verified at latest develop; no TC changes. No active or completed same-head gha-ci run existed before trigger.
- Triggered `/run all` exactly once: https://github.com/CUBRID/cubrid/pull/8298#issuecomment-6439297216 . Tested head is SOURCE_COMMIT. Pickup verified: both build contexts and all three suite contexts point to https://github.com/CUBRID/cubrid/actions/runs/40487586838 . Terminal results pending.
- TC PRs: https://github.com/CUBRID/cubrid-testcases/pull/3897 and https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4588 . No TC edits. The agent will not merge or close these PRs.
