# CBRD-27881 oos-dead-code PR draft context

- Ticket: CBRD-27881
- SOURCE_COMMIT: 39720850512a011204609053b559946f39055fd0
- Agent: claude
- Source repository and branch: vimkim/cubrid, `CBRD-27881-oos-dead-code`
- Base: `feature/oos-merge` (tip dcbf09e4f2 at preparation)
- Observed remote head before publication: branch absent on `vk` (new PR)
- Target repository: CUBRID/CUBRID
- Operation: create
- Proposed title: `[CBRD-27881] Remove dead OOS stats and bridge code`
- Docs task branch: `docs/CBRD-27881-oos-refactor`; integration branch: `main`
- Body: `cbrd-27881/CBRD-27881-oos-dead-code-pr-body_3972085_claude.md`
- Context: `cbrd-27881/CBRD-27881-oos-dead-code-pr-context_3972085_claude.md`
- No explanation document.

## Proposed operations

1. Push `CBRD-27881-oos-dead-code` to the `vk` remote (github.com/vimkim/cubrid), no force.
2. `gh pr create --repo CUBRID/CUBRID --draft --base feature/oos-merge --head vimkim:CBRD-27881-oos-dead-code --assignee vimkim --title "<title>" --body-file <body>`.
3. Keep docs commits local on the task branch; integrate into `main` and push during the CBRD-27881 final write-up.

## Authorization

The user wrote on 2026-11-03 at about 00:20 KST, before going to sleep:
"만약 좋은 후보가 나오면, draft PR을 생성해줘. 1시간마다 하나씩만 생성하고, subagent로 코드리뷰를 마친 뒤 고칠 점이 없으면 /run all 을 날려줘."
This pre-authorizes the source push and draft PR creation above without a further review stop.

## Verification evidence before publication

- Review lane (opus, independent): PASS at 2d60420259db, four optional nits. Three nits were applied in the amend to 3972085 (wrapped commit body, retitled, removed a stale comment).
- Gate lane (sonnet, independent): PASS at 2d60420259db, 44/44 OOS ctest, build without warnings on the changed files.
- Coordinator: rebuilt and reran `test_oos` at 3972085 (comment-only delta), passed.

## Execution record

- 00:53 KST: pushed `CBRD-27881-oos-dead-code` to `vk`; remote head 39720850512a011204609053b559946f39055fd0.
- 00:53 KST: created draft PR https://github.com/CUBRID/cubrid/pull/8367 (assignee vimkim). Remote body equals the body file except one trailing newline. Body SHA-256 5553ca024cf64896decb3ad05df5e2fca342011041e13b286399cd6886175539.
- 00:55 KST: `cubrid-pr-tc-base-check-oos --pr 8367` exit 0; posted `/run all` (https://github.com/CUBRID/cubrid/pull/8367#issuecomment-6581645792); gha-ci run https://github.com/CUBRID/cubrid/actions/runs/41476373316 picked up all five contexts.
- 02:08 KST: on the user's suggestion, created sub-task CBRD-27882 under CBRD-27881 and changed the PR title prefix and the body's JIRA link to CBRD-27882 (gh pr edit; body was unchanged on GitHub before the edit). Commit messages keep [CBRD-27881]; squash merge uses the PR title.
