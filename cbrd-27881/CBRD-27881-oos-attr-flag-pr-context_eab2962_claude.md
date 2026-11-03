# CBRD-27887 oos-attr-flag PR draft context

- Ticket: CBRD-27887 (sub-task of CBRD-27881)
- SOURCE_COMMIT: eab296286879e9b7ce2bef8e6f5d3f6fd28459cb
- Agent: claude
- Source repository and branch: vimkim/cubrid, `CBRD-27881-oos-attr-flag`
- Base: `feature/oos-merge` (tip dcbf09e4f2 at preparation)
- Observed remote head before publication: branch absent on `vk` (new PR)
- Target repository: CUBRID/CUBRID
- Operation: create
- Proposed title: `[CBRD-27887] Share one flag change helper in build_attr_change_map`
- Docs task branch: `docs/CBRD-27881-oos-refactor`; integration branch: `main`
- Body: `cbrd-27881/CBRD-27881-oos-attr-flag-pr-body_eab2962_claude.md`
- Context: `cbrd-27881/CBRD-27881-oos-attr-flag-pr-context_eab2962_claude.md`
- No explanation document.

## Proposed operations

1. Push `CBRD-27881-oos-attr-flag` to the `vk` remote (github.com/vimkim/cubrid), no force.
2. `gh pr create --repo CUBRID/CUBRID --draft --base feature/oos-merge --head vimkim:CBRD-27881-oos-attr-flag --assignee vimkim --title "<title>" --body-file <body>`, no earlier than 05:57 KST (PR 5 opens at 04:57).
3. After the tc branch sync, `cubrid-pr-tc-base-check-oos --pr N`, then one `/run all`.
4. Keep docs commits local on the task branch; integrate into `main` and push during the CBRD-27881 final write-up.

## Authorization

The user wrote on 2026-11-03 at about 00:20 KST, before going to sleep:
"만약 좋은 후보가 나오면, draft PR을 생성해줘. 1시간마다 하나씩만 생성하고, subagent로 코드리뷰를 마친 뒤 고칠 점이 없으면 /run all 을 날려줘."
At 02:01 the user suggested one CBRD-27881 sub-task per PR; CBRD-27887 was created for this PR.

## Verification evidence before publication

- Owner (sonnet): 768-combination truth table over the real extracted code with 4 helper mutations failing; 44/44 OOS ctest before and after; csql ALTER output byte-identical between base and new builds.
- Review lane (opus, independent): PASS at 16042337. Re-extracted the harness inputs (byte-identical), confirmed the full enum domain, reran 768/768 equal, added 4 call-site mutations (all fail); SA/CS `-fsyntax-only -Wall -Wextra` clean; GNU indent unchanged; no open PR touches execute_schema.c. Nits: stale "below" in the helper comment (applied); `else if (was_set)` and a value-returning form (declined, taste).
- Gate lane (sonnet, independent): PASS at 16042337. Recompile with ccache disabled, 0 warnings; 44/44 OOS ctest; own csql script, 35/35 catalog steps match intent.
- Coordinator: comment fix, re-keyed and shortened subject (eab29628); GNU indent unchanged; rebuilt with 0 warnings.

## Execution record

- 05:58 KST: published with scratchpad/publish_pr.sh: pushed to `vk` (remote head eab296286879e9b7ce2bef8e6f5d3f6fd28459cb); created draft PR https://github.com/CUBRID/cubrid/pull/8372 (assignee vimkim); remote body matches the body file apart from trailing blank lines; TC branch sync SUCCESS; `cubrid-pr-tc-base-check-oos --pr 8372` exit 0; posted `/run all` (https://github.com/CUBRID/cubrid/pull/8372#issuecomment-6588339739); gha-ci run https://github.com/CUBRID/cubrid/actions/runs/41524420422 picked up all five contexts.
- 08:58 KST: reworded the test_sql coverage sentence in the PR body to state only verified facts (cases exist and passed; path coverage not checked), after the trail review flagged it as inferred. GitHub body was unchanged before the edit.
