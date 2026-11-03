# CBRD-27881 oos-test-helpers PR draft context

- Ticket: CBRD-27881
- SOURCE_COMMIT: 9f7e5c1d01c13c1f2cab4d80928e27a87cb59240
- Agent: claude
- Source repository and branch: vimkim/cubrid, `CBRD-27881-oos-test-helpers`
- Base: `feature/oos-merge` (tip dcbf09e4f2 at preparation)
- Observed remote head before publication: branch absent on `vk` (new PR)
- Target repository: CUBRID/CUBRID
- Operation: create
- Proposed title: `[CBRD-27881] Share one OOS test helper header`
- Docs task branch: `docs/CBRD-27881-oos-refactor`; integration branch: `main`
- Body: `cbrd-27881/CBRD-27881-oos-test-helpers-pr-body_9f7e5c1_claude.md`
- Context: `cbrd-27881/CBRD-27881-oos-test-helpers-pr-context_9f7e5c1_claude.md`
- No explanation document.

## Proposed operations

1. Push `CBRD-27881-oos-test-helpers` to the `vk` remote (github.com/vimkim/cubrid), no force.
2. `gh pr create --repo CUBRID/CUBRID --draft --base feature/oos-merge --head vimkim:CBRD-27881-oos-test-helpers --assignee vimkim --title "<title>" --body-file <body>`, no earlier than 01:53 KST (one new PR per hour; PR 8367 opened at 00:53).
3. After the tc branch sync, `cubrid-pr-tc-base-check-oos --pr N`, then one `/run all`.
4. Keep docs commits local on the task branch; integrate into `main` and push during the CBRD-27881 final write-up.

## Authorization

The user wrote on 2026-11-03 at about 00:20 KST, before going to sleep:
"만약 좋은 후보가 나오면, draft PR을 생성해줘. 1시간마다 하나씩만 생성하고, subagent로 코드리뷰를 마친 뒤 고칠 점이 없으면 /run all 을 날려줘."
This pre-authorizes the operations above without a further review stop.

## Verification evidence before publication

- Owner (sonnet): 44/44 OOS ctest at base and at 2a32981; per-helper token comparison.
- Coordinator: rebuilt the series to fb8eccd (dropped the `vacuum.h` include that only `run_vacuum` used; wrapped messages); build OK.
- Review lane (opus, independent): PASS at fb8eccd. Compiled all 34 OOS test files in SA, SERVER, CS, and SQL configurations, with and without NDEBUG, and with #8128 or #8299 applied. Two optional nits.
- Gate lane (sonnet, independent): PASS at fb8eccd. 28 test TUs recompiled with ccache disabled, 0 warnings; 44/44 OOS ctest.
- Coordinator: applied both nits (header comment trimmed, commit wording) to 9f7e5c1; comment and message only; rebuilt.

## Execution record

- 01:54 KST: pushed `CBRD-27881-oos-test-helpers` to `vk`; remote head 9f7e5c1d01c13c1f2cab4d80928e27a87cb59240.
- 01:54 KST: created draft PR https://github.com/CUBRID/cubrid/pull/8368 (assignee vimkim); remote body matches the body file apart from trailing blank lines.
- 01:56 KST: `cubrid-pr-tc-base-check-oos --pr 8368` exit 0; posted `/run all` (https://github.com/CUBRID/cubrid/pull/8368#issuecomment-6583006093); gha-ci run https://github.com/CUBRID/cubrid/actions/runs/41486278667 picked up all five contexts.
- 02:08 KST: on the user's suggestion, created sub-task CBRD-27883 under CBRD-27881 and changed the PR title prefix and the body's JIRA link to CBRD-27883 (gh pr edit; body was unchanged on GitHub before the edit). Commit messages keep [CBRD-27881]; squash merge uses the PR title.
