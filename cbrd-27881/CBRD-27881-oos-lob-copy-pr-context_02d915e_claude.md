# CBRD-27881 oos-lob-copy PR draft context

- Ticket: CBRD-27884 (sub-task of CBRD-27881)
- SOURCE_COMMIT: 02d915e3d930cc842a00ace2cd693720d6316429 (same tree as 66668f2; commit subject changed to the subtask key)
- Agent: claude
- Source repository and branch: vimkim/cubrid, `CBRD-27881-oos-lob-copy`
- Base: `feature/oos-merge` (tip dcbf09e4f2 at preparation)
- Observed remote head before publication: branch absent on `vk` (new PR)
- Target repository: CUBRID/CUBRID
- Operation: create
- Proposed title: `[CBRD-27884] Share one LOB copy helper in heap attribute writers`
- Docs task branch: `docs/CBRD-27881-oos-refactor`; integration branch: `main`
- Body: `cbrd-27881/CBRD-27881-oos-lob-copy-pr-body_02d915e_claude.md`
- Context: `cbrd-27881/CBRD-27881-oos-lob-copy-pr-context_02d915e_claude.md`
- No explanation document.

## Proposed operations

1. Push `CBRD-27881-oos-lob-copy` to the `vk` remote (github.com/vimkim/cubrid), no force.
2. `gh pr create --repo CUBRID/CUBRID --draft --base feature/oos-merge --head vimkim:CBRD-27881-oos-lob-copy --assignee vimkim --title "<title>" --body-file <body>`, no earlier than 02:54 KST (PR 8368 opened at 01:54).
3. After the tc branch sync, `cubrid-pr-tc-base-check-oos --pr N`, then one `/run all`.
4. Keep docs commits local on the task branch; integrate into `main` and push during the CBRD-27881 final write-up.

## Authorization

The user wrote on 2026-11-03 at about 00:20 KST, before going to sleep:
"만약 좋은 후보가 나오면, draft PR을 생성해줘. 1시간마다 하나씩만 생성하고, subagent로 코드리뷰를 마친 뒤 고칠 점이 없으면 /run all 을 날려줘."
This pre-authorizes the operations above without a further review stop.

## Verification evidence before publication

- Owner (sonnet): 44/44 OOS ctest at base and at ace9dec6; gdb breakpoint hits from both callers; token equivalence script.
- Review lane (opus, independent): PASS at ace9dec6. Token equivalence of both originals and the helper; SA and SERVER `-fsyntax-only -Wall -Wextra` clean; GNU indent unchanged; #8299 merges cleanly; #8350 adds functions at the same location (one trivial conflict for whichever lands second). One nit on the helper Note wording.
- Gate lane (sonnet, independent): PASS at ace9dec6. Real recompile with ccache disabled, 0 warnings; 44/44 OOS ctest; gdb shows one helper hit from each caller in `OosSqlDeferredWrite.LobPreparationPreservesSourceAndDestinationValues`.
- Coordinator: applied the Note wording nit to 66668f2 (comment only); rebuilt with 0 heap_file.c warnings.

## Execution record

- 02:55 KST: pushed `CBRD-27881-oos-lob-copy` to `vk`; remote head 02d915e3d930cc842a00ace2cd693720d6316429.
- 02:55 KST: created draft PR https://github.com/CUBRID/cubrid/pull/8369 (assignee vimkim); remote body matches the body file apart from trailing blank lines.
- 02:57 KST: `cubrid-pr-tc-base-check-oos --pr 8369` exit 0; posted `/run all` (https://github.com/CUBRID/cubrid/pull/8369#issuecomment-6584347040); gha-ci run https://github.com/CUBRID/cubrid/actions/runs/41495947206 picked up all five contexts.
