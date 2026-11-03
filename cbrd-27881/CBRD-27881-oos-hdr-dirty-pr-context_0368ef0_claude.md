# CBRD-27885 oos-hdr-dirty PR draft context

- Ticket: CBRD-27885 (sub-task of CBRD-27881)
- SOURCE_COMMIT: 0368ef04aa781fb7b6a97180155392b693b5256e
- Agent: claude
- Source repository and branch: vimkim/cubrid, `CBRD-27881-oos-hdr-dirty`
- Base: `feature/oos-merge` (tip dcbf09e4f2 at preparation)
- Observed remote head before publication: branch absent on `vk` (new PR)
- Target repository: CUBRID/CUBRID
- Operation: create
- Proposed title: `[CBRD-27885] Share one unlogged header-dirty helper in oos_file`
- Docs task branch: `docs/CBRD-27881-oos-refactor`; integration branch: `main`
- Body: `cbrd-27881/CBRD-27881-oos-hdr-dirty-pr-body_0368ef0_claude.md`
- Context: `cbrd-27881/CBRD-27881-oos-hdr-dirty-pr-context_0368ef0_claude.md`
- No explanation document.

## Proposed operations

1. Push `CBRD-27881-oos-hdr-dirty` to the `vk` remote (github.com/vimkim/cubrid), no force.
2. `gh pr create --repo CUBRID/CUBRID --draft --base feature/oos-merge --head vimkim:CBRD-27881-oos-hdr-dirty --assignee vimkim --title "<title>" --body-file <body>`, no earlier than 03:55 KST (PR 3 opens at 02:55).
3. After the tc branch sync, `cubrid-pr-tc-base-check-oos --pr N`, then one `/run all`.
4. Keep docs commits local on the task branch; integrate into `main` and push during the CBRD-27881 final write-up.

## Authorization

The user wrote on 2026-11-03 at about 00:20 KST, before going to sleep:
"만약 좋은 후보가 나오면, draft PR을 생성해줘. 1시간마다 하나씩만 생성하고, subagent로 코드리뷰를 마친 뒤 고칠 점이 없으면 /run all 을 날려줘."
At 02:01 the user suggested one CBRD-27881 sub-task per PR; CBRD-27885 was created for this PR.

## Verification evidence before publication

- Owner (sonnet): 44/44 OOS ctest after the change (the first baseline run was invalid after a load-induced timeout; the rerun was 44/44). gdb hits at three of four sites from existing tests; the sync-scan site only with a forced condition.
- Review lane (opus, independent): PASS at 0e5b1be4. Equivalence at all four sites, SA and SERVER `-fsyntax-only -Wall -Wextra` clean, astyle unchanged, clean 3-way merges with #8330, #8299, and #8367. Nit: the site comment "update header stats" was inaccurate.
- Gate lane (sonnet, independent): PASS at 0e5b1be4. Recompile with ccache disabled, 0 warnings; 44/44 OOS ctest, no timeouts.
- Coordinator: removed the inaccurate site comment and re-keyed the subject to CBRD-27885 (0368ef04); rebuilt with 0 oos_file.cpp warnings.

## Execution record

- 03:56 KST: published with scratchpad/publish_pr.sh: pushed to `vk` (remote head 0368ef04aa781fb7b6a97180155392b693b5256e); created draft PR https://github.com/CUBRID/cubrid/pull/8370 (assignee vimkim); remote body matches the body file apart from trailing blank lines; TC branch sync SUCCESS; `cubrid-pr-tc-base-check-oos --pr 8370` exit 0; posted `/run all` (https://github.com/CUBRID/cubrid/pull/8370#issuecomment-6585673619); gha-ci run https://github.com/CUBRID/cubrid/actions/runs/41505512903 picked up all five contexts.
- 05:57 KST: corrected the diff size in the PR body (17/28 → 16/27, the actual shortstat at 0368ef04) with gh pr edit; GitHub body was unchanged before the edit.
